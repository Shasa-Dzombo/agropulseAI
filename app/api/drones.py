from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.database import get_db
from app.models.diagnosis import Diagnosis, DiseaseCategory
from app.models.user import Farm, User
from app.schemas.drone import (
    CreateFlightRequest, DroneFlightResponse, DroneImageResponse,
    DroneImageAnalysisResponse, FlightAnalysisSummary, DiseaseAnswer,
)
from app.auth import get_current_farmer, get_current_user
from app.config import settings
from app.services.drone_ai_service import DroneAIService
from app.services.local_image_storage import save_image_locally
from app.services.supabase_image_storage import save_image_to_supabase

router = APIRouter(prefix="/drones", tags=["Drone Orchard Survey"])


def _build_service(db: AsyncSession) -> DroneAIService:
    """Uses local-disk or Supabase image storage per DRONE_IMAGE_STORAGE
    instead of the default real S3 uploader (e.g. no AWS credentials
    configured, or Supabase Storage preferred)."""
    if settings.DRONE_IMAGE_STORAGE == "local":
        return DroneAIService(db, image_uploader=save_image_locally)
    if settings.DRONE_IMAGE_STORAGE == "supabase":
        return DroneAIService(db, image_uploader=save_image_to_supabase)
    return DroneAIService(db)


def _build_disease_answer(diagnosis: Optional[Diagnosis]) -> Optional[DiseaseAnswer]:
    """Maps the real Diagnosis model's fields onto the lighter DiseaseAnswer
    shape. Not done via DroneImageResponse.model_validate()'s automatic
    from_attributes traversal - Diagnosis's field names (primary_diagnosis,
    confidence_score, severity_level, treatment_recommendations) don't match
    DiseaseAnswer's, so that would silently produce an all-defaults/empty
    answer instead of an error."""
    if diagnosis is None:
        return None

    treatments = diagnosis.treatment_recommendations or []
    top_actions = [
        t["action"] for t in treatments
        if isinstance(t, dict) and t.get("priority") in (1, 2) and t.get("action")
    ][:3]

    return DiseaseAnswer(
        disease_name=diagnosis.primary_diagnosis,
        confidence=diagnosis.confidence_score,
        severity=diagnosis.severity_level,
        is_healthy=diagnosis.category == DiseaseCategory.HEALTHY,
        top_treatment_actions=top_actions,
    )


@router.post("/flights", response_model=DroneFlightResponse, status_code=status.HTTP_201_CREATED)
async def create_mission(
    flight_data: CreateFlightRequest,
    current_user: User = Depends(get_current_farmer),
    db: AsyncSession = Depends(get_db),
):
    """
    Plan a drone orchard survey mission. Does not fly it - call
    POST /flights/{flight_id}/execute to run it.
    """
    result = await db.execute(
        select(Farm).where(Farm.id == flight_data.farm_id, Farm.owner_id == current_user.id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found or you don't have permission",
        )

    if flight_data.backend_type == "mavlink" and not flight_data.mavlink_connection_string:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="mavlink_connection_string is required when backend_type is 'mavlink'",
        )

    if flight_data.enable_disease_detection and not settings.KINDWISE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Disease detection requested but KINDWISE_API_KEY is not configured",
        )

    service = DroneAIService(db)
    flight = await service.plan_mission(
        farm_id=flight_data.farm_id,
        user_id=current_user.id,
        drone_id=flight_data.drone_id,
        home_latitude=flight_data.home_latitude,
        home_longitude=flight_data.home_longitude,
        home_altitude=flight_data.home_altitude,
        target_altitude_m=flight_data.target_altitude_m,
        backend_type=flight_data.backend_type,
        waypoints=[wp.model_dump() for wp in flight_data.waypoints],
        disease_detection_enabled=flight_data.enable_disease_detection,
    )
    return DroneFlightResponse.model_validate(flight)


@router.post("/flights/{flight_id}/execute", response_model=DroneFlightResponse)
async def execute_mission(
    flight_id: int,
    mavlink_connection_string: Optional[str] = Body(None, embed=True),
    current_user: User = Depends(get_current_farmer),
    db: AsyncSession = Depends(get_db),
):
    """
    Fly a planned mission: navigate the waypoints, capture imagery, run NDVI
    analysis, persist results. mavlink_connection_string is required only
    when the flight's backend_type is 'mavlink' (e.g. "udp:0.0.0.0:14550" or
    a serial device path) - ignored for the simulated backend.
    """
    service = _build_service(db)
    flight = await service.execute_mission(flight_id, current_user.id, mavlink_connection_string=mavlink_connection_string)
    return DroneFlightResponse.model_validate(flight)


@router.get("/flights", response_model=List[DroneFlightResponse])
async def list_flights(
    farm_id: int,
    current_user: User = Depends(get_current_farmer),
    db: AsyncSession = Depends(get_db),
):
    """List drone survey flights for a farm."""
    service = DroneAIService(db)
    flights = await service.list_flights(farm_id, current_user.id)
    return [DroneFlightResponse.model_validate(f) for f in flights]


@router.get("/flights/{flight_id}", response_model=DroneFlightResponse)
async def get_flight(
    flight_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single drone flight's status and details."""
    service = DroneAIService(db)
    flight = await service.get_flight(flight_id, current_user.id)
    return DroneFlightResponse.model_validate(flight)


@router.get("/flights/{flight_id}/images", response_model=List[DroneImageResponse])
async def list_flight_images(
    flight_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List captured aerial images for a flight."""
    service = DroneAIService(db)
    images = await service.list_flight_images(flight_id, current_user.id)
    # Built explicitly rather than DroneImageResponse.model_validate(image):
    # image.diagnosis is a raw Diagnosis ORM object, and DiseaseAnswer isn't
    # itself from_attributes-configured, so letting model_validate try to
    # auto-coerce it raises a ValidationError - _build_disease_answer does
    # the real field mapping instead.
    return [
        DroneImageResponse(
            id=image.id,
            flight_id=image.flight_id,
            waypoint_index=image.waypoint_index,
            tree_id=image.tree_id,
            rgb_url=image.rgb_url,
            nir_url=image.nir_url,
            latitude=image.latitude,
            longitude=image.longitude,
            altitude=image.altitude,
            ground_sampling_distance_cm=image.ground_sampling_distance_cm,
            diagnosis_id=image.diagnosis_id,
            diagnosis=_build_disease_answer(image.diagnosis),
            captured_at=image.captured_at,
        )
        for image in images
    ]


@router.get("/flights/{flight_id}/analysis", response_model=FlightAnalysisSummary)
async def get_flight_analysis(
    flight_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate NDVI/health-status summary across all imagery captured on a flight."""
    service = DroneAIService(db)
    summary = await service.get_flight_analysis_summary(flight_id, current_user.id)
    return FlightAnalysisSummary(**summary)
