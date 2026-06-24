"""
📡 IoT API

FastAPI endpoints for IoT device management, sensor data, and weather monitoring.

Endpoints:
- GET /iot/devices - List IoT devices
- POST /iot/devices - Register new device
- GET /iot/devices/{device_id} - Get device details
- PATCH /iot/devices/{device_id} - Update device
- DELETE /iot/devices/{device_id} - Delete device
- POST /iot/devices/{device_id}/activate - Activate device
- POST /iot/devices/{device_id}/deactivate - Deactivate device
- POST /iot/sensor-data - Record sensor data
- GET /iot/sensor-data - Query sensor data
- GET /iot/sensor-data/latest - Get latest readings
- GET /iot/sensor-data/statistics - Data statistics
- POST /iot/weather - Record weather data
- GET /iot/weather - Query weather records
- GET /iot/weather/forecast - Get weather forecast
- POST /iot/irrigation/control - Control irrigation
- GET /iot/irrigation/status - Get irrigation status

Author: AgroPulse Engineering Team
"""

from datetime import datetime, timedelta
from typing import Optional, List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
from decimal import Decimal

from app.db_config import get_production_db_dependency
from app.api.auth import get_current_user


router = APIRouter(prefix="/iot", tags=["IoT"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class DeviceRegisterRequest(BaseModel):
    """Register IoT device request."""
    farm_id: int
    device_name: str = Field(..., min_length=3, max_length=200)
    device_type: str = Field(..., pattern="^(sensor|weather_station|camera|irrigation_controller|soil_probe|drone)$")
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    serial_number: Optional[str] = None
    mac_address: Optional[str] = None
    firmware_version: Optional[str] = None
    location_description: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class DeviceUpdateRequest(BaseModel):
    """Update device request."""
    device_name: Optional[str] = Field(None, min_length=3, max_length=200)
    location_description: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    firmware_version: Optional[str] = None
    maintenance_notes: Optional[str] = None


class DeviceListResponse(BaseModel):
    """Device list response."""
    id: int
    uuid: str
    farm_id: int
    device_name: str
    device_type: str
    status: str
    last_seen: Optional[datetime]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class DeviceDetailResponse(BaseModel):
    """Detailed device response."""
    id: int
    uuid: str
    farm_id: int
    device_name: str
    device_type: str
    model: Optional[str]
    manufacturer: Optional[str]
    serial_number: Optional[str]
    mac_address: Optional[str]
    firmware_version: Optional[str]
    
    # Location
    location_description: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    
    # Status
    status: str
    is_active: bool
    last_seen: Optional[datetime]
    battery_level: Optional[float]
    signal_strength: Optional[int]
    
    # Maintenance
    maintenance_notes: Optional[str]
    last_maintenance: Optional[datetime]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SensorDataRequest(BaseModel):
    """Record sensor data request."""
    device_id: int
    sensor_type: str = Field(..., pattern="^(temperature|humidity|soil_moisture|soil_ph|light|co2|rainfall|wind_speed)$")
    value: float
    unit: str = Field(..., max_length=50)
    timestamp: Optional[datetime] = None


class SensorDataResponse(BaseModel):
    """Sensor data response."""
    id: int
    uuid: str
    device_id: int
    sensor_type: str
    value: float
    unit: str
    timestamp: datetime
    
    class Config:
        from_attributes = True


class LatestReadingsResponse(BaseModel):
    """Latest sensor readings response."""
    device_id: int
    device_name: str
    readings: List[dict]
    last_updated: datetime


class SensorStatisticsResponse(BaseModel):
    """Sensor data statistics response."""
    device_id: int
    sensor_type: str
    count: int
    min_value: float
    max_value: float
    avg_value: float
    latest_value: float
    unit: str
    period_start: datetime
    period_end: datetime


class WeatherDataRequest(BaseModel):
    """Record weather data request."""
    farm_id: int
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    rainfall: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[str] = None
    pressure: Optional[float] = None
    uv_index: Optional[float] = None
    cloud_cover: Optional[int] = Field(None, ge=0, le=100)
    timestamp: Optional[datetime] = None


class WeatherDataResponse(BaseModel):
    """Weather data response."""
    id: int
    uuid: str
    farm_id: int
    temperature: Optional[float]
    humidity: Optional[float]
    rainfall: Optional[float]
    wind_speed: Optional[float]
    wind_direction: Optional[str]
    pressure: Optional[float]
    uv_index: Optional[float]
    cloud_cover: Optional[int]
    timestamp: datetime
    
    class Config:
        from_attributes = True


class WeatherForecastResponse(BaseModel):
    """Weather forecast response."""
    farm_id: int
    forecast_date: datetime
    temperature_high: float
    temperature_low: float
    precipitation_chance: int
    conditions: str
    wind_speed: float
    humidity: int


class IrrigationControlRequest(BaseModel):
    """Irrigation control request."""
    device_id: int
    action: str = Field(..., pattern="^(start|stop|schedule)$")
    duration_minutes: Optional[int] = Field(None, ge=1, le=1440)
    scheduled_time: Optional[datetime] = None
    zone: Optional[str] = None


class IrrigationStatusResponse(BaseModel):
    """Irrigation status response."""
    device_id: int
    status: str
    is_running: bool
    current_zone: Optional[str]
    started_at: Optional[datetime]
    estimated_completion: Optional[datetime]
    water_usage_liters: Optional[float]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def check_device_access(current_user: dict, device_farm_id: int, db: Session):
    """Check if user can access device."""
    from app.repositories.farm import FarmRepository
    
    if current_user['role'] in ['admin', 'superuser']:
        return True
    
    farm_repo = FarmRepository(db)
    farm = farm_repo.get_by_id(device_farm_id)
    
    if not farm or farm.user_id != current_user['id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )


# ============================================================================
# DEVICE ENDPOINTS
# ============================================================================

@router.get("/devices", response_model=List[DeviceListResponse])
async def list_devices(
    farm_id: Optional[int] = None,
    device_type: Optional[str] = None,
    active_only: bool = True,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    List IoT devices with filters.
    
    - **farm_id**: Filter by farm (optional)
    - **device_type**: Filter by type (optional)
    - **active_only**: Show only active devices (default: true)
    """
    from app.models.database import IoTDevice
    
    query = db.query(IoTDevice).filter(IoTDevice.is_deleted == False)
    
    # Access control
    if current_user['role'] not in ['admin', 'superuser']:
        from app.models.database import Farm
        user_farm_ids = db.query(Farm.id).filter(
            Farm.user_id == current_user['id'],
            Farm.is_deleted == False
        ).all()
        farm_ids = [fid[0] for fid in user_farm_ids]
        query = query.filter(IoTDevice.farm_id.in_(farm_ids))
    
    if farm_id:
        query = query.filter(IoTDevice.farm_id == farm_id)
    
    if device_type:
        query = query.filter(IoTDevice.device_type == device_type)
    
    if active_only:
        query = query.filter(IoTDevice.is_active == True)
    
    devices = query.order_by(IoTDevice.created_at.desc()).all()
    
    return devices


@router.post("/devices", response_model=DeviceDetailResponse, status_code=status.HTTP_201_CREATED)
async def register_device(
    request: DeviceRegisterRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Register new IoT device.
    
    - **farm_id**: Farm ID (required)
    - **device_name**: Device name (required)
    - **device_type**: Type (sensor, weather_station, camera, etc.)
    - Other fields are optional
    """
    from app.models.database import IoTDevice
    from app.repositories.farm import FarmRepository
    
    # Verify farm access
    farm_repo = FarmRepository(db)
    farm = farm_repo.get_by_id(request.farm_id)
    
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found"
        )
    
    if farm.user_id != current_user['id'] and current_user['role'] not in ['admin', 'superuser']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Create device
    device = IoTDevice(
        farm_id=request.farm_id,
        device_name=request.device_name,
        device_type=request.device_type,
        model=request.model,
        manufacturer=request.manufacturer,
        serial_number=request.serial_number,
        mac_address=request.mac_address,
        firmware_version=request.firmware_version,
        location_description=request.location_description,
        latitude=request.latitude,
        longitude=request.longitude,
        status='registered',
        is_active=False
    )
    
    db.add(device)
    db.commit()
    db.refresh(device)
    
    return device


@router.get("/devices/{device_id}", response_model=DeviceDetailResponse)
async def get_device(
    device_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Get device details by ID.
    """
    from app.models.database import IoTDevice
    
    device = db.query(IoTDevice).filter(
        IoTDevice.id == device_id,
        IoTDevice.is_deleted == False
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    check_device_access(current_user, device.farm_id, db)
    
    return device


@router.patch("/devices/{device_id}", response_model=DeviceDetailResponse)
async def update_device(
    device_id: int,
    request: DeviceUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Update device details.
    """
    from app.models.database import IoTDevice
    
    device = db.query(IoTDevice).filter(
        IoTDevice.id == device_id,
        IoTDevice.is_deleted == False
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    check_device_access(current_user, device.farm_id, db)
    
    # Update fields
    update_data = {k: v for k, v in request.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data to update"
        )
    
    for key, value in update_data.items():
        setattr(device, key, value)
    
    device.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(device)
    
    return device


@router.delete("/devices/{device_id}")
async def delete_device(
    device_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Delete device (soft delete).
    """
    from app.models.database import IoTDevice
    
    device = db.query(IoTDevice).filter(
        IoTDevice.id == device_id,
        IoTDevice.is_deleted == False
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    check_device_access(current_user, device.farm_id, db)
    
    device.is_deleted = True
    device.deleted_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Device deleted successfully"}


@router.post("/devices/{device_id}/activate")
async def activate_device(
    device_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Activate IoT device.
    """
    from app.models.database import IoTDevice
    
    device = db.query(IoTDevice).filter(
        IoTDevice.id == device_id,
        IoTDevice.is_deleted == False
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    check_device_access(current_user, device.farm_id, db)
    
    device.is_active = True
    device.status = 'active'
    device.last_seen = datetime.utcnow()
    db.commit()
    
    return {
        "message": "Device activated successfully",
        "device_id": device_id
    }


@router.post("/devices/{device_id}/deactivate")
async def deactivate_device(
    device_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Deactivate IoT device.
    """
    from app.models.database import IoTDevice
    
    device = db.query(IoTDevice).filter(
        IoTDevice.id == device_id,
        IoTDevice.is_deleted == False
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    check_device_access(current_user, device.farm_id, db)
    
    device.is_active = False
    device.status = 'inactive'
    db.commit()
    
    return {
        "message": "Device deactivated successfully",
        "device_id": device_id
    }


# ============================================================================
# SENSOR DATA ENDPOINTS
# ============================================================================

@router.post("/sensor-data", response_model=SensorDataResponse, status_code=status.HTTP_201_CREATED)
async def record_sensor_data(
    request: SensorDataRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Record sensor data reading.
    
    - **device_id**: Device ID (required)
    - **sensor_type**: Type (temperature, humidity, soil_moisture, etc.)
    - **value**: Sensor value (required)
    - **unit**: Unit of measurement (required)
    - **timestamp**: Reading timestamp (optional, defaults to now)
    """
    from app.models.database import IoTDevice, SensorData
    
    # Verify device exists
    device = db.query(IoTDevice).filter(
        IoTDevice.id == request.device_id,
        IoTDevice.is_deleted == False
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    check_device_access(current_user, device.farm_id, db)
    
    # Create sensor data record
    sensor_data = SensorData(
        device_id=request.device_id,
        sensor_type=request.sensor_type,
        value=request.value,
        unit=request.unit,
        timestamp=request.timestamp or datetime.utcnow()
    )
    
    db.add(sensor_data)
    
    # Update device last_seen
    device.last_seen = datetime.utcnow()
    
    db.commit()
    db.refresh(sensor_data)
    
    return sensor_data


@router.get("/sensor-data", response_model=List[SensorDataResponse])
async def query_sensor_data(
    device_id: Optional[int] = None,
    sensor_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Query sensor data with filters.
    
    - **device_id**: Filter by device (optional)
    - **sensor_type**: Filter by sensor type (optional)
    - **start_date**: Start of date range (optional)
    - **end_date**: End of date range (optional)
    - **limit**: Maximum results (default: 100, max: 1000)
    """
    from app.models.database import SensorData, IoTDevice
    
    query = db.query(SensorData)
    
    if device_id:
        query = query.filter(SensorData.device_id == device_id)
        
        # Check access
        device = db.query(IoTDevice).filter(IoTDevice.id == device_id).first()
        if device:
            check_device_access(current_user, device.farm_id, db)
    
    if sensor_type:
        query = query.filter(SensorData.sensor_type == sensor_type)
    
    if start_date:
        query = query.filter(SensorData.timestamp >= start_date)
    
    if end_date:
        query = query.filter(SensorData.timestamp <= end_date)
    
    data = query.order_by(SensorData.timestamp.desc()).limit(limit).all()
    
    return data


@router.get("/sensor-data/latest", response_model=List[LatestReadingsResponse])
async def get_latest_readings(
    farm_id: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Get latest sensor readings for all devices.
    """
    from app.models.database import IoTDevice, SensorData
    from sqlalchemy import func
    
    # Get devices
    query = db.query(IoTDevice).filter(
        IoTDevice.is_deleted == False,
        IoTDevice.is_active == True
    )
    
    if farm_id:
        query = query.filter(IoTDevice.farm_id == farm_id)
        
        # Check access
        from app.repositories.farm import FarmRepository
        farm_repo = FarmRepository(db)
        farm = farm_repo.get_by_id(farm_id)
        if farm:
            check_device_access(current_user, farm_id, db)
    
    devices = query.all()
    
    results = []
    for device in devices:
        # Get latest reading for each sensor type
        latest_readings = db.query(
            SensorData.sensor_type,
            SensorData.value,
            SensorData.unit,
            func.max(SensorData.timestamp).label('timestamp')
        ).filter(
            SensorData.device_id == device.id
        ).group_by(
            SensorData.sensor_type,
            SensorData.value,
            SensorData.unit
        ).all()
        
        readings_list = [
            {
                "sensor_type": r[0],
                "value": r[1],
                "unit": r[2],
                "timestamp": r[3]
            }
            for r in latest_readings
        ]
        
        if readings_list:
            results.append(LatestReadingsResponse(
                device_id=device.id,
                device_name=device.device_name,
                readings=readings_list,
                last_updated=max(r["timestamp"] for r in readings_list)
            ))
    
    return results


@router.get("/sensor-data/statistics", response_model=List[SensorStatisticsResponse])
async def get_sensor_statistics(
    device_id: int,
    sensor_type: Optional[str] = None,
    hours: int = Query(24, ge=1, le=720),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Get sensor data statistics.
    
    - **device_id**: Device ID (required)
    - **sensor_type**: Filter by sensor type (optional)
    - **hours**: Hours of history (default: 24, max: 720)
    """
    from app.models.database import IoTDevice, SensorData
    from sqlalchemy import func
    
    # Verify device
    device = db.query(IoTDevice).filter(IoTDevice.id == device_id).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    check_device_access(current_user, device.farm_id, db)
    
    # Calculate time range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    # Build query
    query = db.query(
        SensorData.sensor_type,
        func.count(SensorData.id).label('count'),
        func.min(SensorData.value).label('min_value'),
        func.max(SensorData.value).label('max_value'),
        func.avg(SensorData.value).label('avg_value'),
        SensorData.unit
    ).filter(
        SensorData.device_id == device_id,
        SensorData.timestamp >= start_time,
        SensorData.timestamp <= end_time
    )
    
    if sensor_type:
        query = query.filter(SensorData.sensor_type == sensor_type)
    
    stats = query.group_by(SensorData.sensor_type, SensorData.unit).all()
    
    results = []
    for stat in stats:
        # Get latest value
        latest = db.query(SensorData.value).filter(
            SensorData.device_id == device_id,
            SensorData.sensor_type == stat[0]
        ).order_by(SensorData.timestamp.desc()).first()
        
        results.append(SensorStatisticsResponse(
            device_id=device_id,
            sensor_type=stat[0],
            count=stat[1],
            min_value=float(stat[2]),
            max_value=float(stat[3]),
            avg_value=float(stat[4]),
            latest_value=float(latest[0]) if latest else 0.0,
            unit=stat[5],
            period_start=start_time,
            period_end=end_time
        ))
    
    return results


# ============================================================================
# WEATHER ENDPOINTS
# ============================================================================

@router.post("/weather", response_model=WeatherDataResponse, status_code=status.HTTP_201_CREATED)
async def record_weather_data(
    request: WeatherDataRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Record weather data.
    
    - **farm_id**: Farm ID (required)
    - Weather parameters are optional
    - **timestamp**: Recording timestamp (optional, defaults to now)
    """
    from app.models.database import WeatherRecord
    from app.repositories.farm import FarmRepository
    
    # Verify farm access
    farm_repo = FarmRepository(db)
    farm = farm_repo.get_by_id(request.farm_id)
    
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found"
        )
    
    check_device_access(current_user, request.farm_id, db)
    
    # Create weather record
    weather = WeatherRecord(
        farm_id=request.farm_id,
        temperature=request.temperature,
        humidity=request.humidity,
        rainfall=request.rainfall,
        wind_speed=request.wind_speed,
        wind_direction=request.wind_direction,
        pressure=request.pressure,
        uv_index=request.uv_index,
        cloud_cover=request.cloud_cover,
        timestamp=request.timestamp or datetime.utcnow()
    )
    
    db.add(weather)
    db.commit()
    db.refresh(weather)
    
    return weather


@router.get("/weather", response_model=List[WeatherDataResponse])
async def query_weather_data(
    farm_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Query weather data.
    
    - **farm_id**: Farm ID (required)
    - **start_date**: Start of date range (optional)
    - **end_date**: End of date range (optional)
    - **limit**: Maximum results (default: 100, max: 1000)
    """
    from app.models.database import WeatherRecord
    
    check_device_access(current_user, farm_id, db)
    
    query = db.query(WeatherRecord).filter(WeatherRecord.farm_id == farm_id)
    
    if start_date:
        query = query.filter(WeatherRecord.timestamp >= start_date)
    
    if end_date:
        query = query.filter(WeatherRecord.timestamp <= end_date)
    
    records = query.order_by(WeatherRecord.timestamp.desc()).limit(limit).all()
    
    return records


@router.get("/weather/forecast")
async def get_weather_forecast(
    farm_id: int,
    days: int = Query(7, ge=1, le=14),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Get weather forecast (placeholder - integrate with weather API).
    
    - **farm_id**: Farm ID (required)
    - **days**: Forecast days (default: 7, max: 14)
    """
    from app.repositories.farm import FarmRepository
    
    farm_repo = FarmRepository(db)
    farm = farm_repo.get_by_id(farm_id)
    
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found"
        )
    
    check_device_access(current_user, farm_id, db)
    
    # TODO: Integrate with OpenWeatherMap, WeatherAPI, etc.
    # Placeholder response
    forecasts = []
    for i in range(days):
        forecasts.append(WeatherForecastResponse(
            farm_id=farm_id,
            forecast_date=datetime.utcnow() + timedelta(days=i),
            temperature_high=28.5,
            temperature_low=18.2,
            precipitation_chance=30,
            conditions="Partly cloudy",
            wind_speed=12.5,
            humidity=65
        ))
    
    return forecasts


# ============================================================================
# IRRIGATION CONTROL ENDPOINTS
# ============================================================================

@router.post("/irrigation/control")
async def control_irrigation(
    request: IrrigationControlRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Control irrigation system.
    
    - **device_id**: Irrigation controller ID (required)
    - **action**: Action (start, stop, schedule)
    - **duration_minutes**: Duration for start action (optional)
    - **scheduled_time**: Time for schedule action (optional)
    - **zone**: Irrigation zone (optional)
    """
    from app.models.database import IoTDevice
    
    # Verify device is irrigation controller
    device = db.query(IoTDevice).filter(
        IoTDevice.id == request.device_id,
        IoTDevice.device_type == 'irrigation_controller',
        IoTDevice.is_deleted == False
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Irrigation controller not found"
        )
    
    check_device_access(current_user, device.farm_id, db)

    from app.models.database import Alert, AlertSeverity, DeviceStatus

    if request.action == "start" and request.duration_minutes is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duration is required for start action"
        )

    now = datetime.utcnow()
    action_status = {
        "start": "running",
        "stop": "stopped",
        "schedule": "scheduled",
    }[request.action]

    is_running = request.action == "start"
    estimated_completion = (
        now + timedelta(minutes=request.duration_minutes)
        if request.action == "start" and request.duration_minutes
        else None
    )

    irrigation_state = {
        "status": action_status,
        "is_running": is_running,
        "current_zone": request.zone,
        "started_at": now.isoformat() if is_running else None,
        "estimated_completion": estimated_completion.isoformat() if estimated_completion else None,
        "duration_minutes": request.duration_minutes,
        "scheduled_time": request.scheduled_time.isoformat() if request.scheduled_time else None,
        "water_usage_liters": 0.0 if not request.duration_minutes else round(request.duration_minutes * 1.5, 2),
        "last_command_at": now.isoformat(),
        "last_command": request.action,
    }

    alert = Alert(
        alert_type="device",
        alert_category="irrigation_control",
        severity=AlertSeverity.INFO,
        title=f"Irrigation {request.action.title()} command",
        message=(
            f"Irrigation controller {device.device_name} received a {request.action} command"
            + (f" for zone {request.zone}" if request.zone else "")
        ),
        farm_id=device.farm_id,
        user_id=current_user["id"],
        device_id=device.device_id,
        triggered_by="manual",
        trigger_condition=request.action,
        trigger_value=str(request.duration_minutes or request.scheduled_time or request.zone or ""),
        metadata={"irrigation": irrigation_state},
    )
    db.add(alert)

    device.status = DeviceStatus.ONLINE if request.action != "stop" else DeviceStatus.OFFLINE
    device.last_seen_at = now
    device.last_data_at = now
    device.updated_at = now
    db.commit()

    return {
        "message": f"Irrigation {request.action} command sent",
        "device_id": request.device_id,
        "action": request.action,
        "duration_minutes": request.duration_minutes,
        "scheduled_time": request.scheduled_time,
        "zone": request.zone,
        "status": action_status,
        "timestamp": now.isoformat(),
    }


@router.get("/irrigation/status", response_model=IrrigationStatusResponse)
async def get_irrigation_status(
    device_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Get irrigation system status.
    
    - **device_id**: Irrigation controller ID (required)
    """
    from app.models.database import IoTDevice
    
    device = db.query(IoTDevice).filter(
        IoTDevice.id == device_id,
        IoTDevice.device_type == 'irrigation_controller',
        IoTDevice.is_deleted == False
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Irrigation controller not found"
        )
    
    check_device_access(current_user, device.farm_id, db)
    
    def _status_value(value: Any) -> Any:
        return value.value if hasattr(value, "value") else value

    def _parse_datetime(value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None

    def _parse_int(value: Any) -> Optional[int]:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    state = {}
    for attr in ("irrigation_status", "status_payload", "state", "metadata"):
        payload = getattr(device, attr, None)
        if isinstance(payload, dict):
            state = payload.get("irrigation") or payload
            break

    if not state:
        from app.models.database import Alert

        latest_alert = db.query(Alert).filter(
            Alert.device_id == device.device_id,
            Alert.alert_category == "irrigation_control"
        ).order_by(Alert.created_at.desc()).first()

        if latest_alert and isinstance(latest_alert.metadata, dict):
            state = latest_alert.metadata.get("irrigation") or latest_alert.metadata or {}

    device_status = str(_status_value(getattr(device, "status", "offline"))).lower()
    is_running = bool(state.get("is_running", state.get("running", device_status in {"running", "irrigating"})))
    started_at = _parse_datetime(state.get("started_at"))
    duration_minutes = _parse_int(state.get("duration_minutes") or state.get("duration"))
    estimated_completion = _parse_datetime(state.get("estimated_completion") or state.get("estimated_completion_at"))
    if not estimated_completion and started_at and duration_minutes:
        estimated_completion = started_at + timedelta(minutes=duration_minutes)

    return IrrigationStatusResponse(
        device_id=device_id,
        status=state.get("status") or ("running" if is_running else device_status),
        is_running=is_running,
        current_zone=state.get("current_zone") or state.get("zone"),
        started_at=started_at,
        estimated_completion=estimated_completion,
        water_usage_liters=state.get("water_usage_liters") or state.get("water_used_liters") or 0.0
    )
