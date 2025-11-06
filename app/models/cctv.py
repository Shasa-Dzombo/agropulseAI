from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class CCTVType(str, enum.Enum):
    ESP32_CAM = "esp32_cam"
    RASPBERRY_PI_CAM = "raspberry_pi_cam"
    USB_CAMERA = "usb_camera"
    IP_CAMERA = "ip_camera"


class CCTVMode(str, enum.Enum):
    SENTRY = "sentry"  # Continuous monitoring
    MICRO_FOCUS = "micro_focus"  # Pest/disease detection
    MULTISPECTRAL = "multispectral"  # NDVI/health monitoring
    EVENT_DRIVEN = "event_driven"  # Motion-triggered


class CalibrationStatus(str, enum.Enum):
    PENDING = "pending"
    CALIBRATED = "calibrated"
    NEEDS_RECALIBRATION = "needs_recalibration"


class CCTV(Base):
    __tablename__ = "cctvs"
    
    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    
    device_id = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=True)
    cctv_type = Column(SQLEnum(CCTVType), nullable=False)
    mode = Column(SQLEnum(CCTVMode), default=CCTVMode.SENTRY)
    
    # Physical attributes
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    height_cm = Column(Float, nullable=True)  # Height above ground
    orientation = Column(Float, nullable=True)  # Compass degrees
    
    # Hardware capabilities
    has_nir_led = Column(Boolean, default=False)
    has_red_led = Column(Boolean, default=False)
    has_macro_lens = Column(Boolean, default=False)
    has_pir_sensor = Column(Boolean, default=False)
    has_environmental_sensors = Column(Boolean, default=False)
    
    # Power management
    is_solar_powered = Column(Boolean, default=True)
    battery_level = Column(Float, nullable=True)
    power_mode = Column(String(50), default="auto")  # auto, sleep, active
    
    # Calibration
    calibration_status = Column(SQLEnum(CalibrationStatus), default=CalibrationStatus.PENDING)
    calibration_target_reflectance = Column(Float, nullable=True)
    last_calibration = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    status = Column(String(50), default="active")
    api_key = Column(String(255), unique=True, nullable=False)
    firmware_version = Column(String(50), nullable=True)
    last_ping = Column(DateTime(timezone=True), nullable=True)
    last_wake = Column(DateTime(timezone=True), nullable=True)
    
    # Configuration
    capture_interval_minutes = Column(Integer, default=60)
    wake_on_motion = Column(Boolean, default=True)
    auto_calibrate = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    farm = relationship("Farm")
    zone = relationship("Zone")
    captures = relationship("CCTVCapture", back_populates="cctv")
    health_readings = relationship("CropHealthReading", back_populates="cctv")


class CCTVCapture(Base):
    __tablename__ = "cctv_captures"
    
    id = Column(Integer, primary_key=True, index=True)
    cctv_id = Column(Integer, ForeignKey("cctvs.id"), nullable=False)
    
    # Image data
    image_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    
    # Capture metadata
    capture_mode = Column(String(50), nullable=False)  # scheduled, motion, manual
    resolution = Column(String(20), nullable=True)
    
    # LED configuration used
    nir_led_on = Column(Boolean, default=False)
    red_led_on = Column(Boolean, default=False)
    led_brightness = Column(Integer, nullable=True)
    
    # Environmental data (from sensors)
    temperature_c = Column(Float, nullable=True)
    humidity_percent = Column(Float, nullable=True)
    ambient_light_lux = Column(Float, nullable=True)
    
    # Calibration data
    target_brightness_nir = Column(Float, nullable=True)
    target_brightness_red = Column(Float, nullable=True)
    
    # On-device AI results
    triage_result = Column(String(255), nullable=True)
    triage_confidence = Column(Float, nullable=True)
    anomaly_detected = Column(Boolean, default=False)
    
    # Processing metadata
    raw_metadata = Column(JSON, nullable=True)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    cctv = relationship("CCTV", back_populates="captures")


class CropHealthReading(Base):
    __tablename__ = "crop_health_readings"
    
    id = Column(Integer, primary_key=True, index=True)
    cctv_id = Column(Integer, ForeignKey("cctvs.id"), nullable=False)
    capture_id = Column(Integer, ForeignKey("cctv_captures.id"), nullable=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    
    # NDVI-proxy calculation (Virtual Multispectral)
    normalized_nir = Column(Float, nullable=True)
    normalized_red = Column(Float, nullable=True)
    ndvi_proxy = Column(Float, nullable=True)  # (NIR-Red)/(NIR+Red)
    
    # Health scoring
    health_score = Column(Float, nullable=False)  # 0.0 to 1.0
    expected_health = Column(Float, nullable=True)
    health_status = Column(String(50), nullable=True)  # healthy, stressed, critical
    
    # Crop context
    crop_type = Column(String(100), nullable=True)
    growth_stage = Column(String(100), nullable=True)
    
    # Stress indicators
    stress_detected = Column(Boolean, default=False)
    stress_level = Column(String(50), nullable=True)  # low, medium, high
    stress_type = Column(String(100), nullable=True)  # water, nutrient, pest, disease
    
    # Alert trigger
    alert_generated = Column(Boolean, default=False)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=True)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    cctv = relationship("CCTV", back_populates="health_readings")
    capture = relationship("CCTVCapture")
    farm = relationship("Farm")
    zone = relationship("Zone")
    alert = relationship("Alert")


class CCTVCalibration(Base):
    __tablename__ = "cctv_calibrations"
    
    id = Column(Integer, primary_key=True, index=True)
    cctv_id = Column(Integer, ForeignKey("cctvs.id"), nullable=False)
    
    # Calibration target data
    target_reflectance_known = Column(Float, nullable=False)
    target_brightness_nir = Column(Float, nullable=False)
    target_brightness_red = Column(Float, nullable=False)
    target_brightness_visible = Column(Float, nullable=True)
    
    # Calibration factors
    nir_correction_factor = Column(Float, nullable=False)
    red_correction_factor = Column(Float, nullable=False)
    
    # Environmental conditions during calibration
    ambient_light = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    
    # Quality metrics
    calibration_quality = Column(Float, nullable=True)  # 0.0 to 1.0
    is_active = Column(Boolean, default=True)
    
    calibrated_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    cctv = relationship("CCTV")


class SentryScoutHandshake(Base):
    __tablename__ = "sentry_scout_handshakes"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Sentry (CCTV) data
    cctv_id = Column(Integer, ForeignKey("cctvs.id"), nullable=False)
    health_reading_id = Column(Integer, ForeignKey("crop_health_readings.id"), nullable=False)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False)
    
    # Scout (Farmer) response
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    diagnosis_id = Column(Integer, ForeignKey("diagnoses.id"), nullable=True)
    
    # Handshake status
    status = Column(String(50), default="sentry_alert_sent")  # sentry_alert_sent, scout_acknowledged, scout_arrived, diagnosis_requested, diagnosis_completed
    
    # Timing
    alert_sent_at = Column(DateTime(timezone=True), server_default=func.now())
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    scout_arrived_at = Column(DateTime(timezone=True), nullable=True)
    diagnosis_completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Location verification
    scout_latitude = Column(Float, nullable=True)
    scout_longitude = Column(Float, nullable=True)
    distance_to_sentry_meters = Column(Float, nullable=True)
    
    # Relationships
    cctv = relationship("CCTV")
    health_reading = relationship("CropHealthReading")
    alert = relationship("Alert")
    user = relationship("User")
    diagnosis = relationship("Diagnosis")
