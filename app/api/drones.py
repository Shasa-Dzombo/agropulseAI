from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.db_config import get_production_db_dependency
from app.models.database import Diagnosis
from app.models.drone import DroneImageAnalysis
from app.models.database import Farm
from app.schemas.drone import (
    DroneFlightResponse, DroneImageResponse,
    DroneImageAnalysisResponse, FlightAnalysisSummary, DiseaseAnswer,
    FarmWeatherResponse, WeatherSnapshotOut, FlightConditionOut,
    DiseasePressureOut, AgriculturalAlertOut,
    CreateManualFlightRequest, CompleteFlightRequest, KmlWaypointsResponse, UpdateFlightRequest,
    KmlBoundaryResponse,
)
from app.api.auth import get_current_user
from app.config import settings
from app.services.drone_ai_service import DroneAIService
from app.services.kml_mission_parser import parse_kml_waypoints, parse_kml_boundary
from app.services.local_image_storage import save_image_locally
from app.services.supabase_image_storage import save_image_to_supabase
from app.services.weather_service import (
    assess_disease_pressure, assess_flight_conditions,
    get_openweather_client,
)

router = APIRouter(prefix="/drones", tags=["Drone Orchard Survey"])


def _build_service(db: Session) -> DroneAIService:
    """Uses local-disk or Supabase image storage per DRONE_IMAGE_STORAGE
    instead of the default real S3 uploader (e.g. no AWS credentials
    configured, or Supabase Storage preferred)."""
    if settings.DRONE_IMAGE_STORAGE == "local":
        return DroneAIService(db, image_uploader=save_image_locally)
    if settings.DRONE_IMAGE_STORAGE == "supabase":
        return DroneAIService(db, image_uploader=save_image_to_supabase)
    return DroneAIService(db)


def _build_disease_answer(diagnosis: Optional[Diagnosis]) -> Optional[DiseaseAnswer]:
    """Maps the real (Universe B) Diagnosis model's fields onto the lighter
    DiseaseAnswer shape. Not done via DroneImageResponse.model_validate()'s
    automatic from_attributes traversal - Diagnosis's field names
    (primary_diagnosis, disease_category, immediate_actions) don't match
    DiseaseAnswer's, so that would silently produce an all-defaults/empty
    answer instead of an error.

    immediate_actions/preventive_measures are plain List[str] here (see
    AIService.diagnose_crop_disease/analyze_drone_photo's schemas and
    app/api/diagnoses.py's _run_claude_diagnosis, which is what actually
    populates a Diagnosis row today) - not the priority/action dict shape
    this function used to assume back when it was written against the old,
    never-actually-wired Universe A model."""
    if diagnosis is None:
        return None

    top_actions = (diagnosis.immediate_actions or [])[:3]
    # estimated_count/count_notes/full_diagnosis are drone-analysis-only (see
    # DroneAIService.analyze_image) and have nowhere else to live on
    # Diagnosis - stashed in the otherwise-unused treatment_plan JSONB.
    # full_diagnosis is the untruncated text (primary_diagnosis is
    # VARCHAR(300) and gets cut off with an ellipsis for longer AI answers).
    plan = diagnosis.treatment_plan or {}

    return DiseaseAnswer(
        disease_name=plan.get("full_diagnosis") or diagnosis.primary_diagnosis,
        confidence=diagnosis.confidence_score,
        severity=diagnosis.severity_level,
        is_healthy=diagnosis.disease_category == "healthy",
        top_treatment_actions=top_actions,
        estimated_count=plan.get("estimated_count"),
        count_notes=plan.get("count_notes"),
    )


@router.post("/flights/parse-kml", response_model=KmlWaypointsResponse)
def parse_kml_mission(
    file: UploadFile = File(...),
    action: str = Form("take_photo"),
    default_altitude: float = Form(30.0),
    speed: float = Form(10.0),
    gimbal_pitch: float = Form(-90.0),
    current_user: dict = Depends(get_current_user),
):
    """
    Converts an uploaded .kml file's Placemarks into waypoints, one per
    Placemark's first coordinate, in document order (each Placemark's <name>
    becomes that waypoint's tree_id, when present). Does not create a flight
    or touch the DB - review/edit the returned waypoints, then attach them as
    mission_plan on POST /flights/manual for nearest-GPS photo auto-tagging.
    """
    kml_bytes = file.file.read()
    try:
        waypoints, warnings = parse_kml_waypoints(
            kml_bytes, action=action, default_altitude=default_altitude,
            speed=speed, gimbal_pitch=gimbal_pitch,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return KmlWaypointsResponse(waypoints=waypoints, warnings=warnings)


@router.post("/flights/parse-kml-boundary", response_model=KmlBoundaryResponse)
def parse_kml_boundary_endpoint(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Converts an uploaded .kml file's Polygon (or LineString) into a
    boundary shape - all vertices, unlike parse-kml above which keeps only
    one point per Placemark. Does not create or touch a flight - review the
    returned points, then attach as boundary_polygon on POST/PATCH
    /flights/manual|{flight_id}."""
    kml_bytes = file.file.read()
    try:
        points, warnings = parse_kml_boundary(kml_bytes)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return KmlBoundaryResponse(points=points, warnings=warnings)


@router.post("/flights/manual", response_model=DroneFlightResponse, status_code=status.HTTP_201_CREATED)
def create_manual_flight(
    flight_data: CreateManualFlightRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    """
    Start a flight that's being flown manually outside this system (e.g. DJI's
    own app over the remote controller). Status is IN_PROGRESS immediately;
    push captured photos in via POST /flights/{flight_id}/images as they're
    taken, then finish with POST /flights/{flight_id}/complete.

    mission_plan (optional, e.g. from POST /flights/parse-kml) is a
    reference/briefing waypoint list only - it is never flown by this system,
    but its tree_id values (if any) are used to auto-tag incoming photos by
    nearest real-GPS match.
    """
    farm = db.execute(
        select(Farm).where(Farm.id == flight_data.farm_id, Farm.owner_id == current_user["id"])
    ).scalar_one_or_none()
    if farm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found or you don't have permission",
        )

    service = _build_service(db)
    flight = service.start_manual_flight(
        farm_id=flight_data.farm_id,
        user_id=current_user["id"],
        drone_id=flight_data.drone_id,
        home_latitude=flight_data.home_latitude,
        home_longitude=flight_data.home_longitude,
        home_altitude=flight_data.home_altitude,
        mission_plan=[wp.model_dump() for wp in flight_data.mission_plan] if flight_data.mission_plan else None,
        boundary_polygon=[p.model_dump() for p in flight_data.boundary_polygon] if flight_data.boundary_polygon else None,
        survey_goals=flight_data.survey_goals,
        survey_notes=flight_data.survey_notes,
    )
    return DroneFlightResponse.model_validate(flight)


@router.post("/flights/{flight_id}/images", response_model=DroneImageResponse, status_code=status.HTTP_201_CREATED)
def upload_manual_flight_image(
    flight_id: int,
    rgb: UploadFile = File(...),
    nir: Optional[UploadFile] = File(None),
    red_edge: Optional[UploadFile] = File(None),
    tree_id: Optional[str] = Form(None),
    ground_sampling_distance_cm: Optional[float] = Form(None),
    exclude_shaded_canopy: bool = Form(False),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    """
    Push one captured photo (real DJI multispectral bands, or any RGB photo)
    onto an in-progress manual flight - analyzed and persisted immediately.
    nir/red_edge are optional real band files; if nir is omitted, NDVI falls
    back to the same green-channel placeholder LocalFileCameraBackend uses
    when no real NIR file exists (not real near-infrared data).

    ground_sampling_distance_cm (cm of ground covered by one pixel) is
    optional and usually unnecessary: when omitted it's derived from the
    photo's own EXIF/XMP metadata where the aircraft records enough to do so
    (app.services.dji_gsd_estimation). Supply it explicitly to override that,
    or when your files lack the required tags. When neither is available,
    analysis.total_canopy_area_m2 stays null and areas remain pixel counts
    rather than a fabricated estimate.

    exclude_shaded_canopy (default false) drops densely-shaded tree/hedge
    canopy before measuring, so coverage reflects open crop instead of every
    green thing in frame. Useful when a treeline or hedgerow is visible.
    It is a lighting-based heuristic, not a crop classifier - see
    app.services.crop_vegetation_filter for exactly what it can and cannot
    separate before relying on the difference it makes.
    """
    service = _build_service(db)
    rgb_bytes = rgb.file.read()
    nir_bytes = nir.file.read() if nir is not None else None
    red_edge_bytes = red_edge.file.read() if red_edge is not None else None

    image = service.ingest_captured_image(
        flight_id, current_user["id"], rgb_bytes, nir_bytes, red_edge_bytes,
        tree_id=tree_id, ground_sampling_distance_cm=ground_sampling_distance_cm,
        exclude_shaded_canopy=exclude_shaded_canopy,
    )

    # Queried directly by image_id rather than via image.analysis: image was
    # just built in this same request, and the selectin relationship isn't
    # guaranteed to be populated on a just-flushed/refreshed object - a fresh
    # query is simpler and safer than forcing a relationship (re)load.
    analysis_row = db.execute(
        select(DroneImageAnalysis).where(DroneImageAnalysis.image_id == image.id)
    ).scalar_one_or_none()

    return DroneImageResponse(
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
        diagnosis=None,
        analysis=DroneImageAnalysisResponse.model_validate(analysis_row) if analysis_row else None,
        captured_at=image.captured_at,
    )


@router.post("/flights/{flight_id}/complete", response_model=DroneFlightResponse)
def complete_manual_flight(
    flight_id: int,
    body: CompleteFlightRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    """Marks a manual-ingest flight COMPLETED or ABORTED."""
    service = DroneAIService(db)
    flight = service.complete_manual_flight(
        flight_id, current_user["id"], body.status,
        error_message=body.error_message, battery_end_pct=body.battery_end_pct,
    )
    return DroneFlightResponse.model_validate(flight)


@router.get("/flights", response_model=List[DroneFlightResponse])
def list_flights(
    farm_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    """List drone survey flights for a farm."""
    service = DroneAIService(db)
    flights = service.list_flights(farm_id, current_user["id"])
    return [DroneFlightResponse.model_validate(f) for f in flights]


@router.get("/flights/{flight_id}", response_model=DroneFlightResponse)
def get_flight(
    flight_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    """Get a single drone flight's status and details."""
    service = DroneAIService(db)
    flight = service.get_flight(flight_id, current_user["id"])
    return DroneFlightResponse.model_validate(flight)


@router.patch("/flights/{flight_id}", response_model=DroneFlightResponse)
def update_flight(
    flight_id: int,
    request: UpdateFlightRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    """Edit operational metadata (drone_id, target_altitude_m,
    boundary_polygon, survey_goals, survey_notes) - see
    DroneAIService.update_flight() for what's deliberately not editable."""
    service = DroneAIService(db)
    flight = service.update_flight(
        flight_id, current_user["id"],
        drone_id=request.drone_id, target_altitude_m=request.target_altitude_m,
        boundary_polygon=[p.model_dump() for p in request.boundary_polygon] if request.boundary_polygon else None,
        survey_goals=request.survey_goals, survey_notes=request.survey_notes,
    )
    return DroneFlightResponse.model_validate(flight)


@router.delete("/flights/{flight_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_flight(
    flight_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    """Hard delete - see DroneAIService.delete_flight()."""
    service = DroneAIService(db)
    service.delete_flight(flight_id, current_user["id"])


@router.delete("/flights/{flight_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_flight_image(
    flight_id: int,
    image_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    service = DroneAIService(db)
    service.delete_image(flight_id, image_id, current_user["id"])


@router.post("/flights/{flight_id}/images/{image_id}/analyze", response_model=DroneImageResponse)
def analyze_flight_image(
    flight_id: int,
    image_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    """On-demand deep AI read of one captured photo (see
    DroneAIService.analyze_image) - separate from the always-on, free NDVI/
    vigor analysis every photo already gets on upload. A real network call
    to the configured LLM_PROVIDER (~15-20s) and a real cost against it, so
    this is opt-in per photo rather than automatic. Steered by the flight's
    survey_goals/survey_notes (PATCH /flights/{flight_id} to set them) and
    the farm's own recent input/yield history.
    """
    service = DroneAIService(db)
    image = service.analyze_image(flight_id, image_id, current_user["id"])
    diagnosis = db.execute(select(Diagnosis).where(Diagnosis.id == image.diagnosis_id)).scalar_one_or_none()
    return DroneImageResponse(
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
        diagnosis=_build_disease_answer(diagnosis),
        analysis=DroneImageAnalysisResponse.model_validate(image.analysis) if image.analysis else None,
        captured_at=image.captured_at,
    )


@router.get("/flights/{flight_id}/images/{image_id}/rgb")
def get_image_rgb(
    flight_id: int,
    image_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    """Streams the actual captured photo - rgb_url is a backend-local
    file:// path (app/services/local_image_storage.py), unreachable from a
    phone directly, so this is the ownership-checked way to actually view
    one. Same Bearer-token auth as every other endpoint here - mobile's
    Image.network call passes it as a request header (see
    DroneImageCard/DroneRepository.imageUrl on the mobile side)."""
    service = DroneAIService(db)
    path = service.get_image_local_path(flight_id, image_id, current_user["id"])
    return FileResponse(path, media_type="image/jpeg")


@router.get("/flights/{flight_id}/images/{image_id}/overlay")
def get_image_overlay(
    flight_id: int,
    image_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    """Streams the annotated overlay (canopy boundary + low-vigor boxes) -
    see get_image_rgb's docstring, same idea. 404 when no overlay was
    rendered for this image (see DroneImageAnalysis.overlay_url)."""
    service = DroneAIService(db)
    path = service.get_overlay_local_path(flight_id, image_id, current_user["id"])
    return FileResponse(path, media_type="image/jpeg")


@router.get("/flights/{flight_id}/images", response_model=List[DroneImageResponse])
def list_flight_images(
    flight_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    """List captured aerial images for a flight."""
    service = DroneAIService(db)
    images = service.list_flight_images(flight_id, current_user["id"])
    # Built explicitly rather than DroneImageResponse.model_validate(image):
    # DiseaseAnswer isn't itself from_attributes-configured, so letting
    # model_validate try to auto-coerce a diagnosis row raises a
    # ValidationError - _build_disease_answer does the real field mapping
    # instead. One batched query for every referenced diagnosis rather than
    # one per image (most images have none - see DroneAIService.analyze_image,
    # the only thing that ever sets diagnosis_id).
    diagnosis_ids = [image.diagnosis_id for image in images if image.diagnosis_id]
    diagnoses_by_id = {}
    if diagnosis_ids:
        diagnoses_by_id = {
            d.id: d for d in db.execute(select(Diagnosis).where(Diagnosis.id.in_(diagnosis_ids))).scalars().all()
        }
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
            diagnosis=_build_disease_answer(diagnoses_by_id.get(image.diagnosis_id)),
            analysis=DroneImageAnalysisResponse.model_validate(image.analysis) if image.analysis else None,
            captured_at=image.captured_at,
        )
        for image in images
    ]


@router.get("/flights/{flight_id}/analysis", response_model=FlightAnalysisSummary)
def get_flight_analysis(
    flight_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    """Aggregate NDVI/health-status summary across all imagery captured on a flight."""
    service = DroneAIService(db)
    summary = service.get_flight_analysis_summary(flight_id, current_user["id"])
    return FlightAnalysisSummary(**summary)


@router.get("/weather", response_model=FarmWeatherResponse)
def get_farm_weather(
    farm_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    """
    Real current weather, UAV flight-suitability, and disease-pressure
    context for a farm - usable to check conditions before a mission is even
    planned (DroneFlightResponse.weather_* only populates once a mission has
    actually been executed). Uses the farm's latitude/longitude - unlike the
    Universe A version this replaced, Farm here (app.models.database.Farm)
    always has real coordinates set (required on POST /farms), so there's no
    separate geocode-a-place-name fallback to carry over.
    """
    farm = db.execute(
        select(Farm).where(Farm.id == farm_id, Farm.owner_id == current_user["id"])
    ).scalar_one_or_none()
    if farm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found or you don't have permission")

    client = get_openweather_client()
    if client is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OPENWEATHER_API_KEY is not configured")

    weather = client.get_current_weather(farm.latitude, farm.longitude)
    if weather is None:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch current weather from OpenWeatherMap")

    forecast = client.get_5day_forecast(farm.latitude, farm.longitude)
    alerts = client.get_agricultural_alerts(farm.latitude, farm.longitude, weather, forecast)

    conditions = assess_flight_conditions(weather)
    disease_pressure = assess_disease_pressure(weather)

    return FarmWeatherResponse(
        farm_id=farm.id,
        current=WeatherSnapshotOut(
            temperature_c=weather.temperature,
            feels_like_c=weather.feels_like,
            humidity_pct=weather.humidity,
            wind_speed_ms=weather.wind_speed,
            rainfall_mm=weather.rainfall,
            conditions=weather.description,
            observed_at=weather.timestamp,
        ),
        flight_conditions=FlightConditionOut(suitable=conditions.suitable, warnings=conditions.warnings),
        disease_pressure=DiseasePressureOut(risk_level=disease_pressure.risk_level, indicators=disease_pressure.indicators),
        agricultural_alerts=[
            AgriculturalAlertOut(
                alert_type=a.alert_type, severity=a.severity,
                description=a.description, recommendations=a.recommendations,
            )
            for a in alerts
        ],
    )
