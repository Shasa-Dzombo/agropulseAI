from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"


class AlertCreate(BaseModel):
    farm_id: int
    zone_id: Optional[int] = None
    alert_type: str
    severity: AlertSeverity = AlertSeverity.MEDIUM
    description: Optional[str] = None
    image_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    confidence_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class AlertResponse(AlertCreate):
    id: int
    sensor_id: int
    status: AlertStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = Field(None, validation_alias="alert_metadata")

    class Config:
        from_attributes = True
        populate_by_name = True


class SensorDataCreate(BaseModel):
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    soil_moisture: Optional[float] = None
    light_intensity: Optional[float] = None
    raw_data: Optional[Dict[str, Any]] = None


class SensorDataResponse(SensorDataCreate):
    id: int
    sensor_id: int
    timestamp: datetime
    
    class Config:
        from_attributes = True


class SensorCreate(BaseModel):
    device_id: str
    sensor_type: str
    name: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class SensorResponse(SensorCreate):
    id: int
    farm_id: int
    status: str
    api_key: str
    last_ping: Optional[datetime] = None
    battery_level: Optional[float] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
