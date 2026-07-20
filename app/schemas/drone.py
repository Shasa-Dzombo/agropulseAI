from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
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


class CreateFlightRequest(BaseModel):
    farm_id: int
    drone_id: str
    home_latitude: float
    home_longitude: float
    home_altitude: float = 0.0
    target_altitude_m: float = 30.0
    backend_type: str = Field("simulated", pattern="^(simulated|mavlink)$")
    mavlink_connection_string: Optional[str] = None
    enable_disease_detection: bool = False
    waypoints: List[WaypointIn] = Field(..., min_length=1)


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
    target_altitude_m: float
    disease_detection_enabled: bool = False
    # Yield placeholders - always null today, see app/models/drone.py.
    projected_yield_kg_per_hectare: Optional[float] = None
    yield_projection_model_version: Optional[str] = None
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
    captured_at: Optional[datetime] = None

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


class FlightAnalysisSummary(BaseModel):
    flight_id: int
    image_count: int
    mean_ndvi: Optional[float] = None
    min_ndvi: Optional[float] = None
    max_ndvi: Optional[float] = None
    health_status_histogram: Dict[str, int] = {}
