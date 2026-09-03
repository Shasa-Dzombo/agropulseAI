"""
Drone AI Service - manual DJI ground-ingestion pipeline: images captured on a
manually-flown mission (DJI's own app over the RC, entirely outside this
system) are pushed in via ingest_captured_image() -> real NDVI/vegetation-index
and canopy-vigor analysis runs on each photo -> flight, imagery and analysis
persist to Postgres.

A manual flight can optionally carry a mission_plan (e.g. parsed from a KML
file via app.services.kml_mission_parser) purely as a reference/briefing aid:
each incoming photo's real GPS reading is matched to the nearest planned
waypoint to auto-fill tree_id when the caller doesn't supply one. Nothing
here drives a physical aircraft - the simulated and real MAVLink flight
backends that used to live under app/drones/flight/ were removed, since this
project's actual hardware is flown manually and neither backend was ever
reachable from it.

Rewritten 2026-09-02 to target Universe B (app.db_config / app.models.database
- the real login/farm system, same as app.api.farms and app.api.diagnoses)
instead of Universe A's async app.database session and app.models.user.Farm.
The drone-specific tables (drone_flights, drone_images, drone_image_analyses,
drone_telemetry_logs) didn't move - they're plain tables in the same Postgres
database either way, just with their farm_id/requested_by_id/diagnosis_id
foreign keys repointed at the real farms/users/diagnoses tables (see
scripts/patch_drone_universe_b_fks.py). A sync Session works with any mapped
class regardless of which declarative Base defined it, so nothing here
needed to move onto Universe B's Base either.
"""

import logging
import math
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional

import cv2
import numpy as np
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.drones.flight import _console  # noqa: F401 - must run before any drone_orchard_system import

from drone_orchard_system.multispectral_imaging import MultispectralImage, MultispectralProcessor

from app.drones.flight.backend import GPSCoordinate
from app.drones.flight.camera import green_channel_as_nir_placeholder
from app.models.drone import (
    DroneBackendType,
    DroneFlight,
    DroneFlightStatus,
    DroneImage,
    DroneImageAnalysis,
)
from app.models.database import Farm
from app.services.canopy_overlay_rendering import render_vigor_overlay
from app.services.canopy_vigor_assessment import assess_canopy_vigor
from app.services.dji_gsd_estimation import estimate_ground_sampling_distance_cm
from app.services.exif_gps import extract_gps_from_image_bytes
from app.services.plant_stress_assessment import assess_plant_stress
from app.services.weather_service import (
    assess_disease_pressure,
    assess_flight_conditions,
    get_openweather_client,
)

logger = logging.getLogger(__name__)


def _safe_float(value: float) -> Optional[float]:
    """NDVI/etc. can be NaN when process_multispectral_image() finds no
    positive-index pixels (it excludes them from the mean) - store as
    None/null rather than an invalid, unserializable NaN."""
    try:
        return None if math.isnan(value) else float(value)
    except TypeError:
        return None


def _default_image_uploader(content: bytes, file_name: str, folder: str) -> str:
    """Real S3 upload (app.services.ai_service.AWSAIService.upload_to_s3) -
    that method is async (a blocking boto3 call wrapped in async def with no
    real concurrency benefit, same as the local/Supabase uploaders were
    before this rewrite), so it's bridged here with asyncio.run() rather than
    changing its signature - it's shared with other, still-Universe-A code
    this rewrite doesn't otherwise touch."""
    import asyncio
    from app.services.ai_service import aws_ai_service
    return asyncio.run(aws_ai_service.upload_to_s3(content, file_name, folder=folder))


def _nearest_waypoint_tree_id(mission_plan: List[dict], latitude: float, longitude: float) -> Optional[str]:
    """Matches a real GPS reading to the closest reference waypoint in a
    manual flight's mission_plan (typically KML-derived - see
    app.services.kml_mission_parser), so a manually-flown photo gets the same
    tree_id a planned mission would have assigned. Returns None if the plan
    is empty or none of its waypoints carry a tree_id."""
    candidates = [wp for wp in mission_plan if wp.get("tree_id")]
    if not candidates:
        return None

    photo_point = GPSCoordinate(latitude, longitude, 0.0)
    nearest = min(
        candidates,
        key=lambda wp: photo_point.distance_to(GPSCoordinate(wp["latitude"], wp["longitude"], 0.0)),
    )
    return nearest["tree_id"]


class DroneAIService:
    def __init__(self, db: Session, image_uploader: Optional[Callable] = None):
        self.db = db
        self._upload = image_uploader or _default_image_uploader

    def _apply_weather_context(self, flight: DroneFlight) -> None:
        """Real OpenWeatherMap conditions at the flight's home coordinates -
        advisory only (app.services.weather_service). Never raises and never
        blocks the mission: any failure here just leaves the weather_* columns
        None, same as a missing OPENWEATHER_API_KEY."""
        try:
            client = get_openweather_client()
            if client is None:
                return

            # fetch_weather_snapshot is an async wrapper (asyncio.to_thread)
            # around this same blocking call, for callers on an event loop -
            # this service is fully sync, so it calls the client directly.
            weather = client.get_current_weather(flight.home_latitude, flight.home_longitude)
            if weather is None:
                return

            conditions = assess_flight_conditions(weather)
            disease_pressure = assess_disease_pressure(weather)

            flight.weather_temperature_c = weather.temperature
            flight.weather_humidity_pct = weather.humidity
            flight.weather_wind_speed_ms = weather.wind_speed
            flight.weather_conditions = weather.description
            flight.weather_flight_suitable = conditions.suitable
            flight.weather_warnings = conditions.warnings
            flight.weather_disease_pressure = disease_pressure.risk_level
            flight.weather_checked_at = datetime.utcnow()
            self.db.commit()
        except Exception:
            logger.exception("Weather context lookup failed for flight %s - proceeding without it", flight.id)
            self.db.rollback()

    def _render_and_upload_overlay(
        self, rgb: np.ndarray, vigor, flight_id: int, waypoint_index: int,
        ground_sampling_distance_cm: Optional[float],
    ) -> Optional[str]:
        """Annotated copy of the photo (canopy boundary + low-vigor boxes +
        labels), uploaded alongside the raw bands. Returns None and logs on
        any failure - a rendering or upload problem must never cost the
        caller their actual image ingest, so this is deliberately
        best-effort, matching _apply_weather_context's contract."""
        try:
            overlay = render_vigor_overlay(
                rgb, vigor, ground_sampling_distance_cm=ground_sampling_distance_cm
            )
            ok, buf = cv2.imencode(".jpg", overlay)
            if not ok:
                logger.warning("Could not JPEG-encode the vigor overlay for flight %s image %s", flight_id, waypoint_index)
                return None
            return self._upload(
                buf.tobytes(), f"{waypoint_index}_overlay.jpg", f"drone-imagery/{flight_id}"
            )
        except Exception:
            logger.exception(
                "Vigor overlay render/upload failed for flight %s image %s - continuing without it",
                flight_id, waypoint_index,
            )
            return None

    def _process_and_persist_image(
        self, image: MultispectralImage, processor: MultispectralProcessor,
        flight_id: int, waypoint_index: int, tree_id: Optional[str],
        latitude: float, longitude: float, altitude: float,
        ground_sampling_distance_cm: Optional[float],
        rgb_url: Optional[str], nir_url: Optional[str],
        run_disease_detection_for_mission: bool = False,
        exclude_shaded_canopy: bool = False,
    ) -> DroneImage:
        """Called from the manual DJI-ingestion upload path
        (ingest_captured_image below) - the one real NDVI/stress/vigor
        pipeline every captured photo goes through.

        run_disease_detection_for_mission is accepted but not yet supported
        post-rewrite: the Kindwise disease-detection integration it used to
        call still creates Universe A Diagnosis rows (app.models.diagnosis),
        which nothing reads any more (the real diagnosis flow is
        app.api.diagnoses, Universe B). Wiring per-image drone disease
        detection to that instead is real, separate follow-up work - no
        caller currently passes True here (see app.api.drones.py), so this
        raises clearly instead of silently doing the wrong thing if that
        ever changes without the follow-up work being done first.
        """
        if run_disease_detection_for_mission:
            raise NotImplementedError(
                "Per-image drone disease detection isn't wired to Universe B yet - "
                "see this method's docstring."
            )

        drone_image = DroneImage(
            flight_id=flight_id,
            waypoint_index=waypoint_index,
            tree_id=tree_id,
            rgb_url=rgb_url,
            nir_url=nir_url,
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            ground_sampling_distance_cm=ground_sampling_distance_cm,
        )
        self.db.add(drone_image)
        self.db.flush()

        indices = processor.process_multispectral_image(image)
        ndvi = _safe_float(indices.ndvi)
        stress = assess_plant_stress(indices)
        vigor = assess_canopy_vigor(
            image.rgb,
            ground_sampling_distance_cm=ground_sampling_distance_cm,
            exclude_shaded_canopy=exclude_shaded_canopy,
        )
        overlay_url = self._render_and_upload_overlay(
            image.rgb, vigor, flight_id, waypoint_index, ground_sampling_distance_cm,
        )
        self.db.add(DroneImageAnalysis(
            image_id=drone_image.id,
            ndvi=ndvi,
            gndvi=_safe_float(indices.gndvi),
            ndre=_safe_float(indices.ndre),
            savi=_safe_float(indices.savi),
            evi=_safe_float(indices.evi),
            health_status=indices.get_health_status().value if ndvi is not None else None,
            stress_level=stress.stress_level,
            stress_indicators=stress.stress_indicators,
            canopy_coverage_pct=vigor.coverage_pct,
            vigor_level=vigor.vigor_level,
            vigor_indicators=vigor.vigor_indicators,
            low_vigor_regions=vigor.low_vigor_regions,
            total_canopy_area_m2=vigor.total_canopy_area_m2,
            overlay_url=overlay_url,
        ))

        return drone_image

    def start_manual_flight(
        self, farm_id: int, user_id: int, drone_id: str,
        home_latitude: float, home_longitude: float, home_altitude: float = 0.0,
        mission_plan: Optional[List[dict]] = None,
    ) -> DroneFlight:
        """The aircraft is flown manually (e.g. DJI's own app over the RC)
        entirely outside this system - images get pushed in afterward or live
        via ingest_captured_image(), typically from
        scripts/watch_and_upload_dji_images.py. Ownership of farm_id is
        checked by the caller (app/api/drones.py).

        mission_plan, when given (e.g. from app.services.kml_mission_parser),
        is a reference/briefing waypoint list only - nothing here flies it.
        Its per-waypoint tree_id values (if any) are used by
        ingest_captured_image() to auto-tag incoming photos by nearest
        real-GPS match."""
        flight = DroneFlight(
            farm_id=farm_id,
            requested_by_id=user_id,
            drone_id=drone_id,
            backend_type=DroneBackendType.MANUAL_INGEST,
            status=DroneFlightStatus.IN_PROGRESS,
            home_latitude=home_latitude,
            home_longitude=home_longitude,
            home_altitude=home_altitude,
            mission_plan=mission_plan,
            started_at=datetime.utcnow(),
        )
        self.db.add(flight)
        self.db.commit()
        self.db.refresh(flight)

        self._apply_weather_context(flight)
        return flight

    def ingest_captured_image(
        self, flight_id: int, user_id: int,
        rgb_bytes: bytes, nir_bytes: Optional[bytes], red_edge_bytes: Optional[bytes],
        tree_id: Optional[str] = None,
        ground_sampling_distance_cm: Optional[float] = None,
        exclude_shaded_canopy: bool = False,
    ) -> DroneImage:
        """v1 uses DJI's companion consumer RGB JPG directly as rgb (no
        Blue/Green/Red band-stacking - that needs Addendum 3's real
        calibration first) and the raw, uncalibrated NIR/RedEdge band files
        directly when supplied - real signal, not yet radiometrically
        calibrated. Falls back to green_channel_as_nir_placeholder when no
        real NIR file is given, same honest degraded path LocalFileCameraBackend
        already uses.

        ground_sampling_distance_cm (cm covered by one pixel) is optional and
        has no way to be derived from a plain JPEG - when supplied (e.g. from
        a known flight altitude + camera field of view), it's stored on the
        image and used to convert canopy-vigor region pixel areas into real
        m^2 (app.services.canopy_vigor_assessment); otherwise those stay
        unknown rather than a fabricated guess."""
        flight = self._get_owned_flight_or_raise(flight_id, user_id)
        if flight.backend_type != DroneBackendType.MANUAL_INGEST:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This flight is not a manual-ingest flight")
        if flight.status != DroneFlightStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Flight {flight_id} is not in progress (status={flight.status.value})",
            )

        rgb = cv2.imdecode(np.frombuffer(rgb_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if rgb is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not decode rgb image")

        if nir_bytes:
            nir = cv2.imdecode(np.frombuffer(nir_bytes, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
            if nir is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not decode nir image")
        else:
            nir = green_channel_as_nir_placeholder(rgb)

        red_edge = None
        if red_edge_bytes:
            red_edge = cv2.imdecode(np.frombuffer(red_edge_bytes, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
            if red_edge is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not decode red_edge image")

        # An explicitly-supplied value always wins; otherwise try to read it
        # out of the photo's own EXIF/XMP. Stays None when neither is
        # available, which just means areas are reported in pixels.
        if ground_sampling_distance_cm is None:
            ground_sampling_distance_cm = estimate_ground_sampling_distance_cm(rgb_bytes)

        gps = extract_gps_from_image_bytes(rgb_bytes)
        latitude = gps.latitude if gps else flight.home_latitude
        longitude = gps.longitude if gps else flight.home_longitude
        altitude = gps.altitude if gps and gps.altitude is not None else flight.home_altitude

        # Auto-tag by nearest reference waypoint only when we have a real
        # per-photo GPS reading (not the flight's home-coordinate fallback,
        # which would make every untagged photo "match" whichever waypoint
        # happens to be closest to home) and the caller didn't already say
        # which tree/plot this is.
        if tree_id is None and gps is not None and flight.mission_plan:
            tree_id = _nearest_waypoint_tree_id(flight.mission_plan, latitude, longitude)

        image = MultispectralImage(
            rgb=rgb,
            nir=nir,
            red_edge=red_edge,
            timestamp=time.time(),
            gps_latitude=latitude,
            gps_longitude=longitude,
            altitude=altitude,
            gimbal_pitch=-90.0,
            ground_sampling_distance=0.0,
        )

        waypoint_index = self.db.execute(
            select(func.count()).select_from(DroneImage).where(DroneImage.flight_id == flight_id)
        ).scalar_one()

        folder = f"drone-imagery/{flight_id}"
        _, rgb_buf = cv2.imencode(".jpg", rgb)
        rgb_url = self._upload(rgb_buf.tobytes(), f"{waypoint_index}_rgb.jpg", folder)
        nir_url = None
        if nir_bytes:
            _, nir_buf = cv2.imencode(".jpg", nir)
            nir_url = self._upload(nir_buf.tobytes(), f"{waypoint_index}_nir.jpg", folder)

        processor = MultispectralProcessor()
        drone_image = self._process_and_persist_image(
            image, processor, flight_id, waypoint_index, tree_id,
            latitude, longitude, altitude, ground_sampling_distance_cm, rgb_url, nir_url,
            exclude_shaded_canopy=exclude_shaded_canopy,
        )
        self.db.commit()
        self.db.refresh(drone_image)
        return drone_image

    def complete_manual_flight(
        self, flight_id: int, user_id: int, status_value: str,
        error_message: Optional[str] = None, battery_end_pct: Optional[float] = None,
    ) -> DroneFlight:
        flight = self._get_owned_flight_or_raise(flight_id, user_id)
        if flight.backend_type != DroneBackendType.MANUAL_INGEST:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This flight is not a manual-ingest flight")
        if flight.status != DroneFlightStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Flight {flight_id} is not in progress (status={flight.status.value})",
            )

        flight.status = DroneFlightStatus.COMPLETED if status_value == "completed" else DroneFlightStatus.ABORTED
        flight.completed_at = datetime.utcnow()
        flight.error_message = error_message
        flight.battery_end_pct = battery_end_pct
        self.db.commit()
        self.db.refresh(flight)
        return flight

    def get_flight(self, flight_id: int, user_id: int) -> DroneFlight:
        return self._get_owned_flight_or_raise(flight_id, user_id)

    def list_flights(self, farm_id: int, user_id: int) -> List[DroneFlight]:
        farm = self.db.execute(
            select(Farm).where(Farm.id == farm_id, Farm.owner_id == user_id)
        ).scalar_one_or_none()
        if farm is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found or you don't have permission")

        return list(self.db.execute(
            select(DroneFlight).where(DroneFlight.farm_id == farm_id).order_by(DroneFlight.created_at.desc())
        ).scalars().all())

    def list_flight_images(self, flight_id: int, user_id: int) -> List[DroneImage]:
        self._get_owned_flight_or_raise(flight_id, user_id)
        return list(self.db.execute(
            select(DroneImage).where(DroneImage.flight_id == flight_id).order_by(DroneImage.waypoint_index)
        ).scalars().all())

    def get_flight_analysis_summary(self, flight_id: int, user_id: int) -> Dict:
        self._get_owned_flight_or_raise(flight_id, user_id)

        analyses = list(self.db.execute(
            select(DroneImageAnalysis).join(DroneImage, DroneImage.id == DroneImageAnalysis.image_id)
            .where(DroneImage.flight_id == flight_id)
        ).scalars().all())

        ndvis = [a.ndvi for a in analyses if a.ndvi is not None]
        histogram: Dict[str, int] = {}
        for a in analyses:
            if a.health_status:
                histogram[a.health_status] = histogram.get(a.health_status, 0) + 1

        coverages = [a.canopy_coverage_pct for a in analyses if a.canopy_coverage_pct is not None]
        vigor_histogram: Dict[str, int] = {}
        for a in analyses:
            if a.vigor_level:
                vigor_histogram[a.vigor_level] = vigor_histogram.get(a.vigor_level, 0) + 1

        return {
            "flight_id": flight_id,
            "image_count": len(analyses),
            "mean_ndvi": sum(ndvis) / len(ndvis) if ndvis else None,
            "min_ndvi": min(ndvis) if ndvis else None,
            "max_ndvi": max(ndvis) if ndvis else None,
            "health_status_histogram": histogram,
            "mean_canopy_coverage_pct": sum(coverages) / len(coverages) if coverages else None,
            "min_canopy_coverage_pct": min(coverages) if coverages else None,
            "max_canopy_coverage_pct": max(coverages) if coverages else None,
            "vigor_level_histogram": vigor_histogram,
        }

    def _get_owned_flight_or_raise(self, flight_id: int, user_id: int) -> DroneFlight:
        flight = self.db.execute(
            select(DroneFlight).join(Farm, Farm.id == DroneFlight.farm_id)
            .where(DroneFlight.id == flight_id, Farm.owner_id == user_id)
        ).scalar_one_or_none()
        if flight is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flight not found or you don't have permission")
        return flight
