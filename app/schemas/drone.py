from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime


class WaypointIn(BaseModel):
    latitude: float
    longitude: float
    altitude: float
    action: str = Field("fly_through", pattern="^(fly_through|hover|take_photo|rtl)$")
    hover_time: float = 0.0
    speed: float = 10.0
    gimbal_pitch: float = -90.0
    photo_interval: float = 0.0
    tree_id: Optional[str] = None


class KmlWaypointsResponse(BaseModel):
    """Result of parsing a .kml file into waypoints
    (app.services.kml_mission_parser). Reviewable, not auto-submitted - the
    caller edits/confirms these and then attaches them as mission_plan on
    CreateManualFlightRequest."""
    waypoints: List[WaypointIn]
    warnings: List[str] = []


class CreateManualFlightRequest(BaseModel):
    """No target altitude/backend - the aircraft is flown manually (e.g.
    DJI's own app over the RC), entirely outside this system. See
    DroneAIService.start_manual_flight().

    mission_plan is optional reference-only waypoints (e.g. parsed from a
    KML file via POST /flights/parse-kml) - nothing in this system flies
    them. Their tree_id values (if any) are used to auto-tag incoming
    photos by nearest real-GPS match; see
    DroneAIService.ingest_captured_image()."""
    farm_id: int
    drone_id: str
    home_latitude: float
    home_longitude: float
    home_altitude: float = 0.0
    mission_plan: Optional[List[WaypointIn]] = None


class CompleteFlightRequest(BaseModel):
    status: Literal["completed", "aborted"]
    error_message: Optional[str] = None
    battery_end_pct: Optional[float] = None


class DroneFlightResponse(BaseModel):
    id: int
    farm_id: int
    requested_by_id: int
    drone_id: str
    backend_type: str
    status: str
    home_latitude: float
    home_longitude: float
    home_altitude: float
    target_altitude_m: Optional[float] = None
    # Reference-only waypoints attached at flight start (e.g. KML-derived) -
    # used for nearest-GPS tree_id auto-tagging, not flown by this system.
    mission_plan: Optional[List[Dict[str, Any]]] = None
    disease_detection_enabled: bool = False
    # Yield placeholders - always null today, see app/models/drone.py.
    projected_yield_kg_per_hectare: Optional[float] = None
    yield_projection_model_version: Optional[str] = None
    # Real OpenWeatherMap conditions at execute_mission() time - advisory
    # only, null when OPENWEATHER_API_KEY is unset or the lookup failed.
    weather_temperature_c: Optional[float] = None
    weather_humidity_pct: Optional[int] = None
    weather_wind_speed_ms: Optional[float] = None
    weather_conditions: Optional[str] = None
    weather_flight_suitable: Optional[bool] = None
    # Optional, not List[str]=[] - the DB column is nullable and genuinely
    # stays None (not []) whenever weather wasn't fetched; from_attributes
    # validation of None against a non-Optional List[str] raises.
    weather_warnings: Optional[List[str]] = None
    weather_disease_pressure: Optional[str] = None
    weather_checked_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    battery_start_pct: Optional[float] = None
    battery_end_pct: Optional[float] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DiseaseAnswer(BaseModel):
    """Lightweight disease answer embedded on DroneImageResponse. Built from
    the real app.models.diagnosis.Diagnosis row - full detail (all treatment
    options, EPPO code, alternative diagnoses) is available via
    GET /diagnoses/{diagnosis_id}."""
    disease_name: Optional[str] = None
    confidence: Optional[float] = None
    severity: Optional[str] = None
    is_healthy: bool = False
    top_treatment_actions: List[str] = []


class DroneImageAnalysisResponse(BaseModel):
    image_id: int
    ndvi: Optional[float] = None
    gndvi: Optional[float] = None
    ndre: Optional[float] = None
    savi: Optional[float] = None
    evi: Optional[float] = None
    health_status: Optional[str] = None
    stress_level: Optional[str] = None
    stress_indicators: List[str] = []
    # Excess-Green-Index canopy coverage/vigor screening
    # (app.services.canopy_vigor_assessment) - a scouting cue, not a
    # diagnosis. Always computed, same as stress_level above.
    canopy_coverage_pct: Optional[float] = None
    vigor_level: Optional[str] = None
    vigor_indicators: List[str] = []
    low_vigor_regions: List[Dict[str, Any]] = []
    # Real m^2 - only non-null when the photo was uploaded with a known
    # ground_sampling_distance_cm; never a fabricated estimate.
    total_canopy_area_m2: Optional[float] = None
    # Annotated copy of the photo: canopy boundary traced, low-vigor areas
    # boxed in red, coverage/vigor/area labelled.
    overlay_url: Optional[str] = None

    class Config:
        from_attributes = True


class DroneImageResponse(BaseModel):
    id: int
    flight_id: int
    waypoint_index: int
    tree_id: Optional[str] = None
    rgb_url: Optional[str] = None
    nir_url: Optional[str] = None
    latitude: float
    longitude: float
    altitude: float
    ground_sampling_distance_cm: Optional[float] = None
    diagnosis_id: Optional[int] = None
    diagnosis: Optional[DiseaseAnswer] = None
    # NDVI/stress/canopy-vigor analysis for this specific photo (always
    # computed - see DroneImageAnalysisResponse). None only in the unlikely
    # case analysis hasn't been persisted yet for this image.
    analysis: Optional[DroneImageAnalysisResponse] = None
    captured_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FlightAnalysisSummary(BaseModel):
    flight_id: int
    image_count: int
    mean_ndvi: Optional[float] = None
    min_ndvi: Optional[float] = None
    max_ndvi: Optional[float] = None
    health_status_histogram: Dict[str, int] = {}
    mean_canopy_coverage_pct: Optional[float] = None
    min_canopy_coverage_pct: Optional[float] = None
    max_canopy_coverage_pct: Optional[float] = None
    vigor_level_histogram: Dict[str, int] = {}


class WeatherSnapshotOut(BaseModel):
    """Real current conditions from OpenWeatherMap (app.integrations.weather.openweather)."""
    temperature_c: float
    feels_like_c: float
    humidity_pct: int
    wind_speed_ms: float
    rainfall_mm: float
    conditions: str
    observed_at: datetime


class FlightConditionOut(BaseModel):
    """See app.services.weather_service.assess_flight_conditions - advisory only."""
    suitable: bool
    warnings: List[str] = []


class DiseasePressureOut(BaseModel):
    """See app.services.weather_service.assess_disease_pressure - a rule-based
    fungal-risk proxy, not a diagnosis or a trained model."""
    risk_level: str
    indicators: List[str] = []


class AgriculturalAlertOut(BaseModel):
    """From OpenWeatherMapClient.get_agricultural_alerts() - its own general
    thresholds (frost/heat/drought/flood/wind), distinct from and broader
    than the UAV-specific flight_conditions above."""
    alert_type: str
    severity: str
    description: str
    recommendations: List[str] = []


class FarmWeatherResponse(BaseModel):
    """Pre-planning weather check for a farm - usable before a mission even
    exists, unlike the weather_* fields on DroneFlightResponse which only
    populate once a mission has been executed."""
    farm_id: int
    current: WeatherSnapshotOut
    flight_conditions: FlightConditionOut
    disease_pressure: DiseasePressureOut
    agricultural_alerts: List[AgriculturalAlertOut] = []
