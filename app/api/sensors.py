from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List
from datetime import datetime
import secrets
from app.database import get_db
from app.models.sensor import Sensor, Alert, SensorData, AlertStatus
from app.models.user import Farm
from app.schemas.sensor import (
    SensorCreate, SensorResponse, AlertCreate, AlertResponse,
    SensorDataCreate, SensorDataResponse
)
from app.auth import verify_sensor_api_key, get_current_farmer
from app.models.user import User

router = APIRouter(prefix="/sensors", tags=["Greenhouse Sensors & Climate Monitoring"])


@router.post("", response_model=SensorResponse, status_code=status.HTTP_201_CREATED)
async def register_greenhouse_sensor(
    sensor_data: SensorCreate,
    greenhouse_id: int,
    current_user: User = Depends(get_current_farmer),
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new greenhouse sensor device (ESP32-CAM, CO2 sensor, PAR sensor, pH/EC meter).
    
    Supported sensor types:
    - ESP32-CAM: Visual crop monitoring with LED grow light compensation
    - MH-Z19B: CO2 concentration monitoring (0-5000 ppm)
    - PAR sensor: Photosynthetically active radiation measurement
    - pH/EC sensor: Hydroponic nutrient solution monitoring
    - DHT22: Temperature and humidity monitoring
    - DS18B20: Water temperature for hydroponic systems
    """
    # Verify greenhouse ownership
    result = await db.execute(
        select(Farm).where(Farm.id == greenhouse_id, Farm.owner_id == current_user.id)
    )
    greenhouse = result.scalar_one_or_none()
    
    if not greenhouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Greenhouse not found or you don't have permission"
        )
    
    # Generate unique API key
    api_key = f"greenhouse_{secrets.token_urlsafe(32)}"
    
    new_sensor = Sensor(
        farm_id=greenhouse_id,
        device_id=sensor_data.device_id,
        sensor_type=sensor_data.sensor_type,
        name=sensor_data.name,
        location=sensor_data.location,  # e.g., "Zone A - Row 3"
        latitude=sensor_data.latitude,
        longitude=sensor_data.longitude,
        api_key=api_key,
        status="active"
    )
    
    db.add(new_sensor)
    await db.commit()
    await db.refresh(new_sensor)
    
    return SensorResponse.model_validate(new_sensor)


@router.post("/alerts", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_greenhouse_alert(
    alert_data: AlertCreate,
    sensor: Sensor = Depends(verify_sensor_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new greenhouse climate alert from a sensor device.
    
    Alert types for greenhouses:
    - temperature_stress: Temperature outside optimal range
    - humidity_high: High humidity, condensation risk
    - co2_low: CO2 below optimal for photosynthesis
    - par_low: Insufficient PAR light intensity
    - ph_drift: pH outside optimal range (5.5-6.5)
    - ec_drift: EC outside optimal range
    - vpd_stress: Vapor Pressure Deficit stress
    - disease_detected: Visual disease symptoms (powdery mildew, botrytis, etc.)
    - pest_detected: Aphids, whiteflies, thrips, spider mites
    - nutrient_deficiency: Visual symptoms of N, P, K, Ca, Mg deficiency
    """
    # Update sensor's last ping
    sensor.last_ping = datetime.utcnow()
    
    new_alert = Alert(
        farm_id=alert_data.farm_id,
        zone_id=alert_data.zone_id,
        sensor_id=sensor.id,
        alert_type=alert_data.alert_type,
        severity=alert_data.severity,
        description=alert_data.description,
        image_url=alert_data.image_url,
        latitude=alert_data.latitude,
        longitude=alert_data.longitude,
        confidence_score=alert_data.confidence_score,
        metadata=alert_data.metadata,
        status="pending"
    )
    
    db.add(new_alert)
    await db.commit()
    await db.refresh(new_alert)
    
    # TODO: Send push notification to grower
    # TODO: Trigger automated climate control adjustments if configured
    
    return AlertResponse.model_validate(new_alert)


@router.get("/alerts", response_model=List[AlertResponse])
async def get_greenhouse_alerts(
    greenhouse_id: int,
    status: str = None,
    current_user: User = Depends(get_current_farmer),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all alerts for a specific greenhouse.
    
    Filter by status: pending, acknowledged, resolved, false_positive
    """
    # Verify greenhouse ownership
    result = await db.execute(
        select(Farm).where(Farm.id == greenhouse_id, Farm.owner_id == current_user.id)
    )
    greenhouse = result.scalar_one_or_none()
    
    if not greenhouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Greenhouse not found"
        )
    
    # Build query
    query = select(Alert).where(Alert.farm_id == greenhouse_id)
    
    if status:
        query = query.where(Alert.status == status)
    
    query = query.order_by(Alert.created_at.desc())
    
    result = await db.execute(query)
    alerts = result.scalars().all()
    
    return [AlertResponse.model_validate(alert) for alert in alerts]


@router.patch("/alerts/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_greenhouse_alert(
    alert_id: int,
    current_user: User = Depends(get_current_farmer),
    db: AsyncSession = Depends(get_db)
):
    """
    Acknowledge a greenhouse alert (grower has seen it and taken action)
    """
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    # Verify farm ownership
    result = await db.execute(
        select(Farm).where(Farm.id == alert.farm_id, Farm.owner_id == current_user.id)
    )
    farm = result.scalar_one_or_none()
    
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(alert)
    
    return AlertResponse.model_validate(alert)


@router.post("/data", response_model=SensorDataResponse, status_code=status.HTTP_201_CREATED)
async def log_sensor_data(
    data: SensorDataCreate,
    sensor: Sensor = Depends(verify_sensor_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Log sensor data (temperature, humidity, etc.) from IoT devices
    """
    # Update sensor's last ping
    sensor.last_ping = datetime.utcnow()
    
    sensor_data = SensorData(
        sensor_id=sensor.id,
        temperature=data.temperature,
        humidity=data.humidity,
        soil_moisture=data.soil_moisture,
        light_intensity=data.light_intensity,
        raw_data=data.raw_data
    )
    
    db.add(sensor_data)
    await db.commit()
    await db.refresh(sensor_data)
    
    return SensorDataResponse.model_validate(sensor_data)


@router.post("/ping")
async def sensor_ping(
    battery_level: float = None,
    sensor: Sensor = Depends(verify_sensor_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Simple ping endpoint for sensors to report they're alive
    """
    sensor.last_ping = datetime.utcnow()
    
    if battery_level is not None:
        sensor.battery_level = battery_level
    
    await db.commit()
    
    return {
        "status": "ok",
        "sensor_id": sensor.id,
        "timestamp": datetime.utcnow()
    }
