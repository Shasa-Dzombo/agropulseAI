"""
Kindwise crop.health disease detection for drone-captured imagery. Wraps the
real, reusable KindwiseAPIClient (loaded via _kindwise_client_loader - see
that module for why a normal package import doesn't work) and turns a
successful identification into a real app.models.diagnosis.Diagnosis row -
usable by the rest of the app (farmer's diagnosis history etc.), not a
shadow copy on the drone tables.

Kindwise is a paid, rate-limited third-party API - only ever called when a
flight has disease_detection_enabled=True AND the farm's crop_type maps to
a Kindwise CropType. Any failure (bad image quality, rate limit, network,
missing API key) degrades gracefully: logs a reason and returns None -
never raises, never aborts the mission (same spirit as _safe_float()).
"""

import asyncio
import dataclasses
import logging
from datetime import datetime
from typing import Optional

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.diagnosis import Diagnosis, DiagnosisStatus, DiseaseCategory
from app.services._kindwise_client_loader import CropType, KindwiseAPIClient, KindwiseAPIResponse

logger = logging.getLogger(__name__)


def get_kindwise_client() -> Optional[KindwiseAPIClient]:
    """Returns None (and logs) if KINDWISE_API_KEY isn't configured, instead
    of letting the client's __init__ raise ValueError mid-mission."""
    if not settings.KINDWISE_API_KEY:
        logger.warning("KINDWISE_API_KEY not configured - disease detection disabled for this mission")
        return None

    client = KindwiseAPIClient(
        api_key=settings.KINDWISE_API_KEY,
        cache_dir=settings.KINDWISE_CACHE_DIR,
        timeout_seconds=settings.KINDWISE_TIMEOUT,
    )
    # MAX_REQUESTS_PER_MINUTE/MAX_REQUESTS_PER_DAY are read as self.X in
    # _check_rate_limit(), so instance overrides here take effect correctly.
    client.MAX_REQUESTS_PER_MINUTE = settings.KINDWISE_MAX_REQUESTS_PER_MINUTE
    client.MAX_REQUESTS_PER_DAY = settings.KINDWISE_MAX_REQUESTS_PER_DAY

    if settings.KINDWISE_BASE_URL:
        # IDENTIFY_ENDPOINT/HEALTH_CHECK_ENDPOINT are derived from BASE_URL
        # once at class-definition time, not recomputed per call - overriding
        # BASE_URL alone would silently leave requests hitting the old
        # endpoints, so all three must be set together.
        client.BASE_URL = settings.KINDWISE_BASE_URL
        client.IDENTIFY_ENDPOINT = f"{settings.KINDWISE_BASE_URL}/identification"
        client.HEALTH_CHECK_ENDPOINT = f"{settings.KINDWISE_BASE_URL}/health_check"

    return client


def _serialize_identification(ident) -> dict:
    d = dataclasses.asdict(ident)
    d["severity"] = ident.severity.value
    if ident.eppo_code is not None:
        d["eppo_code"] = dataclasses.asdict(ident.eppo_code)
    return d


async def run_disease_detection(
    db: AsyncSession,
    client: KindwiseAPIClient,
    crop_type: CropType,
    image_rgb: np.ndarray,
    rgb_url: Optional[str],
    farmer_id: int,
    latitude: float,
    longitude: float,
) -> Optional[int]:
    """Calls Kindwise (blocking, off the event loop), and if it produced a
    result, creates+flushes a Diagnosis row and returns its id. Returns
    None on any failure/skip - caller stores that as DroneImage.diagnosis_id."""
    try:
        response: Optional[KindwiseAPIResponse] = await asyncio.to_thread(
            client.identify_disease,
            image=image_rgb,
            crop_type=crop_type,
            latitude=latitude,
            longitude=longitude,
        )
    except Exception:
        logger.exception("Kindwise identify_disease call raised unexpectedly")
        return None

    if response is None:
        logger.info("Kindwise returned no result (image quality/rate-limit/network) - skipping diagnosis for this image")
        return None

    top1 = response.top1_disease
    metadata = {
        "source": "drone_survey",
        "crop_type_kindwise": crop_type.value,
        "image_quality_score": response.image_quality_score,
        "kindwise_model_version": response.model_version,
        "alternative_identifications": [_serialize_identification(i) for i in response.top3_diseases],
    }

    if top1 is None:
        diagnosis = Diagnosis(
            farmer_id=farmer_id,
            alert_id=None,
            permit_id=None,
            status=DiagnosisStatus.COMPLETED,
            image_urls=[rgb_url] if rgb_url else [],
            diagnosis_metadata=metadata,
            primary_diagnosis="No disease detected",
            category=DiseaseCategory.HEALTHY,
            confidence_score=None,
            ai_model_version=f"kindwise:{response.model_version}",
            processing_time_seconds=response.processing_time_ms / 1000.0,
        )
    else:
        metadata["economic_impact_text"] = top1.economic_impact
        metadata["spread_risk"] = top1.spread_risk
        diagnosis = Diagnosis(
            farmer_id=farmer_id,
            alert_id=None,
            permit_id=None,
            status=DiagnosisStatus.COMPLETED,
            image_urls=[rgb_url] if rgb_url else [],
            diagnosis_metadata=metadata,
            primary_diagnosis=top1.disease_name,
            # Kindwise's taxonomy doesn't map 1:1 to fungal/bacterial/viral/
            # pest - left null intentionally rather than guessed; raw name/
            # EPPO data is preserved in diagnosis_metadata above.
            category=None,
            confidence_score=top1.confidence,
            alternative_diagnoses=[_serialize_identification(i) for i in response.top3_diseases if i is not top1],
            severity_level=top1.severity.value,
            treatment_recommendations=[dataclasses.asdict(t) for t in top1.treatments],
            preventive_measures=[dataclasses.asdict(t) for t in top1.treatments if t.category in ("cultural", "biological")],
            ai_model_version=f"kindwise:{response.model_version}",
            processing_time_seconds=response.processing_time_ms / 1000.0,
        )

    diagnosis.completed_at = datetime.utcnow()
    db.add(diagnosis)
    await db.flush()
    return diagnosis.id
