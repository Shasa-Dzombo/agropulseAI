"""
AI Crop Health Diagnosis API (greenhouse/general use - not the drone pipeline,
see app/api/drones.py for that).

Rewritten 2026-08-31 to target Universe B (app.db_config /
app.models.database), same as app.api.auth and app.api.farms. The previous
version of this file used Universe A (app.auth / app.database /
app.models.diagnosis / app.models.permit) - a completely separate user base
with its own SECRET_KEY, so a token issued by the real, working
/auth/register or /auth/login (Universe B) was rejected outright by it. See
mobile/CHANGELOG.md 2026-08-31 for the full writeup.

Also drops the permit/blockchain payment gating for now - Flutterwave/M-Pesa
aren't configured in this environment, so there is no way to actually obtain
a permit. Diagnoses are unpaid/ungated until that's wired up; see the NOTE
above create_diagnosis.

Image storage is local disk (local_uploads/diagnoses/), not S3 - there's no
AWS configured either, and Claude vision (app/services/claude_ai_service.py)
already reads local file paths directly, so no S3/public-URL requirement.
"""

import os
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db_config import get_production_db_dependency
from app.api.auth import get_current_user
from app.models.database import Diagnosis
from app.services.claude_ai_service import claude_ai_service, ClaudeNotConfiguredError

router = APIRouter(prefix="/diagnoses", tags=["AI Crop Health Diagnosis"])

UPLOAD_DIR = os.path.join("local_uploads", "diagnoses")


class DiagnosisCreateRequest(BaseModel):
    image_urls: List[str]
    farm_id: Optional[int] = None
    user_symptoms: Optional[str] = None


class DiagnosisResponse(BaseModel):
    id: int
    uuid: uuid.UUID
    diagnosis_id: str
    status: str
    status_message: Optional[str] = None
    image_urls: List[str]
    primary_diagnosis: Optional[str] = None
    disease_category: Optional[str] = None
    confidence_score: Optional[float] = None
    severity_level: Optional[str] = None
    affected_area_percentage: Optional[float] = None
    alternative_diagnoses: Optional[list] = None
    immediate_actions: Optional[list] = None
    preventive_measures: Optional[list] = None
    model_version: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


def _run_claude_diagnosis(diagnosis: Diagnosis, db: Session, metadata: dict) -> None:
    """Runs the diagnosis synchronously and updates the row in place.

    A background task queue (Celery, per the original file's own comment)
    is the right long-term shape for this - a real photo-to-diagnosis call
    can take several seconds and shouldn't block the HTTP response. Kept
    synchronous for now to match how the rest of this dev environment runs
    (no worker process set up); revisit once one exists.
    """
    diagnosis.status = "processing"
    db.commit()

    try:
        import asyncio
        ai_result = asyncio.run(claude_ai_service.diagnose_crop_disease(
            image_urls=diagnosis.image_urls,
            metadata=metadata,
        ))
    except ClaudeNotConfiguredError as e:
        ai_result = {"success": False, "error": str(e)}
    except Exception as e:
        ai_result = {"success": False, "error": str(e)}

    if ai_result.get("success"):
        diagnosis.status = "completed"
        diagnosis.primary_diagnosis = ai_result.get("primary_diagnosis")
        diagnosis.disease_category = ai_result.get("category")
        diagnosis.confidence_score = ai_result.get("confidence_score")
        diagnosis.affected_area_percentage = ai_result.get("affected_area_percentage")
        diagnosis.severity_level = ai_result.get("severity_level")
        diagnosis.alternative_diagnoses = ai_result.get("alternative_diagnoses")
        diagnosis.immediate_actions = ai_result.get("treatment_recommendations")
        diagnosis.preventive_measures = ai_result.get("preventive_measures")
        diagnosis.model_version = ai_result.get("ai_model_version")
        if ai_result.get("processing_time_seconds") is not None:
            diagnosis.total_processing_time_ms = ai_result["processing_time_seconds"] * 1000
        diagnosis.completed_at = datetime.utcnow()
    else:
        diagnosis.status = "failed"
        diagnosis.status_message = ai_result.get("error", "Diagnosis failed")
        diagnosis.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(diagnosis)


@router.post("", response_model=DiagnosisResponse, status_code=status.HTTP_201_CREATED)
def create_diagnosis(
    request: DiagnosisCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    """
    Submit uploaded image(s) for AI crop disease diagnosis.

    NOTE: no payment/permit gating - see this file's module docstring.
    Call POST /diagnoses/upload-image first to get image_urls.
    """
    if not request.image_urls:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one image is required")

    metadata = {"user_symptoms": request.user_symptoms} if request.user_symptoms else {}

    diagnosis = Diagnosis(
        uuid=uuid.uuid4(),
        diagnosis_id=f"DX-{uuid.uuid4().hex[:12]}",
        user_id=current_user["id"],
        farm_id=request.farm_id,
        request_payload=request.model_dump(),
        permit_token_id="unpaid-dev",
        image_urls=request.image_urls,
        user_symptoms=request.user_symptoms,
        status="pending",
    )
    db.add(diagnosis)
    db.commit()
    db.refresh(diagnosis)

    _run_claude_diagnosis(diagnosis, db, metadata)

    return diagnosis


@router.get("/{diagnosis_id}", response_model=DiagnosisResponse)
def get_diagnosis(
    diagnosis_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    diagnosis = db.query(Diagnosis).filter(
        Diagnosis.id == diagnosis_id,
        Diagnosis.user_id == current_user["id"],
    ).first()

    if not diagnosis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagnosis not found")

    return diagnosis


@router.get("", response_model=List[DiagnosisResponse])
def list_diagnoses(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
    limit: int = 20,
    offset: int = 0,
):
    return (
        db.query(Diagnosis)
        .filter(Diagnosis.user_id == current_user["id"])
        .order_by(Diagnosis.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


@router.post("/upload-image")
def upload_diagnosis_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload an image for diagnosis. Saved to local disk - see this file's
    module docstring for why (no S3/AWS configured in this environment).
    Returns a path usable directly as an image_url in POST /diagnoses.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image")

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    extension = os.path.splitext(file.filename or "")[1] or ".jpg"
    unique_filename = f"{uuid.uuid4()}{extension}"
    destination = os.path.join(UPLOAD_DIR, unique_filename)

    with open(destination, "wb") as f:
        f.write(file.file.read())

    # Forward slashes even on Windows - this path round-trips through JSON
    # and back into claude_ai_service's file-open call, and backslashes are
    # an easy source of double-escaping bugs across that boundary.
    return {"success": True, "image_url": destination.replace(os.sep, "/"), "filename": unique_filename}
