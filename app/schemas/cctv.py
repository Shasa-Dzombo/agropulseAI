from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class CCTVType(str, Enum):
    ESP32_CAM = "esp32_cam"
    RASPBERRY_PI_CAM = "raspberry_pi_cam"
    USB_CAMERA = "usb_camera"


class CCTVMode(str, Enum):
    SENTRY = "sentry"
    MICRO_FOCUS = "micro_focus"
    MULTISPECTRAL = "multispectral"
    EVENT_DRIVEN = "event_driven"


class CCTVCreate(BaseModel):
    device_id: str
    name: Optional[str] = None
    cctv_type: CCTVType
    mode: CCTVMode = CCTVMode.SENTRY
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    height_cm: Optional[float] = None
    has_nir_led: bool = False
    has_red_led: bool = False
    has_macro_lens: bool = False
    has_pir_sensor: bool = False
    has_environmental_sensors: bool = False


class CCTVResponse(CCTVCreate):
    id: int
    farm_id: int
    zone_id: Optional[int] = None
    status: str
    api_key: str
    battery_level: Optional[float] = None
    calibration_status: str
    last_ping: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class CCTVCaptureCreate(BaseModel):
    capture_mode: str  # scheduled, motion, manual
    image_data: Optional[str] = None  # Base64 encoded or URL
    
    # LED configuration
    nir_led_on: bool = False
    red_led_on: bool = False
    led_brightness: Optional[int] = None
    
    # Environmental data
    temperature_c: Optional[float] = None
    humidity_percent: Optional[float] = None
    ambient_light_lux: Optional[float] = None
    
    # Calibration readings
    target_brightness_nir: Optional[float] = None
    target_brightness_red: Optional[float] = None
    
    # On-device AI results
    triage_result: Optional[str] = None
    triage_confidence: Optional[float] = None
    anomaly_detected: bool = False
    
    raw_metadata: Optional[Dict[str, Any]] = None


class CCTVCaptureResponse(BaseModel):
    id: int
    cctv_id: int
    image_url: str
    capture_mode: str
    nir_led_on: bool
    red_led_on: bool
    temperature_c: Optional[float] = None
    humidity_percent: Optional[float] = None
    triage_result: Optional[str] = None
    triage_confidence: Optional[float] = None
    anomaly_detected: bool
    timestamp: datetime
    
    class Config:
        from_attributes = True


class CropHealthReading(BaseModel):
    id: int
    cctv_id: int
    health_score: float
    expected_health: Optional[float] = None
    health_status: str
    ndvi_proxy: Optional[float] = None
    stress_detected: bool
    stress_level: Optional[str] = None
    stress_type: Optional[str] = None
    crop_type: Optional[str] = None
    growth_stage: Optional[str] = None
    alert_generated: bool
    timestamp: datetime
    
    class Config:
        from_attributes = True


class VirtualMultispectralResult(BaseModel):
    """Result from Virtual Multispectral Sensor"""
    normalized_nir: float
    normalized_red: float
    ndvi_proxy: float
    health_score: float
    calibration_quality: float


class HealthAlert(BaseModel):
    """Smart alert from Sentry CCTV"""
    cctv_id: int
    device_name: str
    zone_name: str
    gps_location: Dict[str, float]
    alert_type: str
    expected_health: float
    current_health: float
    stress_level: str
    crop_type: str
    growth_stage: str
    message: str
    image_url: Optional[str] = None


class SentryScoutHandshakeCreate(BaseModel):
    """Initiate handshake when farmer responds to alert"""
    alert_id: int
    cctv_id: int
    health_reading_id: int
    scout_latitude: Optional[float] = None
    scout_longitude: Optional[float] = None


class SentryScoutHandshakeResponse(BaseModel):
    id: int
    cctv_id: int
    alert_id: int
    status: str
    alert_sent_at: datetime
    acknowledged_at: Optional[datetime] = None
    scout_arrived_at: Optional[datetime] = None
    distance_to_sentry_meters: Optional[float] = None
    diagnosis_completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CCTVCalibrationRequest(BaseModel):
    """Request to calibrate CCTV"""
    target_reflectance_known: float = 0.5  # Gray card reflectance
    target_brightness_nir: float
    target_brightness_red: float
    ambient_light: Optional[float] = None
    temperature: Optional[float] = None


class CCTVConfigUpdate(BaseModel):
    """Update CCTV configuration"""
    mode: Optional[CCTVMode] = None
    capture_interval_minutes: Optional[int] = None
    wake_on_motion: Optional[bool] = None
    power_mode: Optional[str] = None
    crop_type: Optional[str] = None
    growth_stage: Optional[str] = None
