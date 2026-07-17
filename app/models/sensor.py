from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class SensorType(str, enum.Enum):
    ESP32_CAM = "esp32_cam"
    RASPBERRY_PI = "raspberry_pi"
    MOBILE_PHONE = "mobile_phone"


class SensorStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class AlertSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, enum.Enum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class Sensor(Base):
    __tablename__ = "sensors"
    
    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("app_farms.id"), nullable=False)
    device_id = Column(String(100), unique=True, index=True, nullable=False)
    sensor_type = Column(SQLEnum(SensorType), nullable=False)
    name = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    status = Column(SQLEnum(SensorStatus), default=SensorStatus.ACTIVE)
    api_key = Column(String(255), unique=True, nullable=False)
    last_ping = Column(DateTime(timezone=True), nullable=True)
    battery_level = Column(Float, nullable=True)
    firmware_version = Column(String(50), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    farm = relationship("Farm", back_populates="sensors")
    alerts = relationship("Alert", back_populates="sensor")
    sensor_data = relationship("SensorData", back_populates="sensor")


class Alert(Base):
    # "alerts" collides with Universe B's Alert table - namespaced like
    # User/Farm above.
    __tablename__ = "app_alerts"

    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("app_farms.id"), nullable=False)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False)
    
    alert_type = Column(String(100), nullable=False)  # yellow_spot, wilting, pest_detected
    severity = Column(SQLEnum(AlertSeverity), default=AlertSeverity.MEDIUM)
    status = Column(SQLEnum(AlertStatus), default=AlertStatus.PENDING)
    
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    confidence_score = Column(Float, nullable=True)
    alert_metadata = Column(JSON, nullable=True)

    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    farm = relationship("Farm", back_populates="alerts")
    zone = relationship("Zone", back_populates="alerts")
    sensor = relationship("Sensor", back_populates="alerts")
    diagnoses = relationship("Diagnosis", back_populates="alert")


class SensorData(Base):
    __tablename__ = "sensor_data"
    
    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False)
    
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    soil_moisture = Column(Float, nullable=True)
    light_intensity = Column(Float, nullable=True)
    
    raw_data = Column(JSON, nullable=True)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    sensor = relationship("Sensor", back_populates="sensor_data")
