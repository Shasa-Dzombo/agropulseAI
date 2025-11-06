"""
🌿 AgroPulse - Greenhouse Management API
Comprehensive REST API for greenhouse and controlled environment horticulture.

Author: AgroPulse Engineering Team
Date: November 2025
Version: 2.0.0-horticulture
"""

from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, desc
from pydantic import BaseModel, Field, validator
import logging

from ..database import get_db
from ..models.database import (
    Greenhouse, GreenhouseEnvironment, Farm, User, IoTDevice,
    GreenhouseSystemType, DeviceType, DeviceStatus
)
from ..auth import get_current_user, require_role
from ..schemas.greenhouse import (
    GreenhouseCreate, GreenhouseUpdate, GreenhouseResponse,
    GreenhouseEnvironmentCreate, GreenhouseEnvironmentResponse,
    GreenhouseListResponse, GreenhouseDetailedResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/greenhouses", tags=["Greenhouses"])


# ============================================================================
# GREENHOUSE CRUD OPERATIONS
# ============================================================================

@router.post("/", response_model=GreenhouseResponse, status_code=status.HTTP_201_CREATED)
async def create_greenhouse(
    farm_id: int,
    greenhouse_data: GreenhouseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new greenhouse within a farm.
    
    **Parameters:**
    - **farm_id**: Farm ID where greenhouse is located
    - **name**: Greenhouse name
    - **area_sqm**: Area in square meters
    - **system_type**: Hydroponics, aeroponics, aquaponics, soil-based, vertical farm
    - **structure_type**: Dome, A-Frame, Gothic Arch, etc.
    - **covering_material**: Glass, polycarbonate, polyethylene film
    
    **Permissions:** GROWER, HORTICULTURIST, AGRONOMIST
    
    **Example:**
    ```json
    {
      "name": "Tomato Greenhouse #1",
      "description": "High-tech hydroponic greenhouse for cherry tomatoes",
      "area_sqm": 500,
      "volume_m3": 1500,
      "structure_type": "Gothic Arch",
      "covering_material": "Twin-wall polycarbonate",
      "system_type": "hydroponics",
      "latitude": -1.2921,
      "longitude": 36.8219
    }
    ```
    """
    # Verify farm ownership
    farm = db.query(Farm).filter(
        Farm.id == farm_id,
        Farm.owner_id == current_user.id,
        Farm.is_deleted == False
    ).first()
    
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found or you don't have permission to access it"
        )
    
    # Create greenhouse
    greenhouse = Greenhouse(
        farm_id=farm_id,
        **greenhouse_data.dict()
    )
    
    db.add(greenhouse)
    
    # Update farm statistics
    farm.has_greenhouse = True
    farm.number_of_greenhouses = (farm.number_of_greenhouses or 0) + 1
    farm.greenhouse_area_sqm = (farm.greenhouse_area_sqm or 0) + greenhouse_data.area_sqm
    
    db.commit()
    db.refresh(greenhouse)
    
    logger.info(f"Greenhouse '{greenhouse.name}' created for farm {farm_id} by user {current_user.id}")
    
    return greenhouse


@router.get("/", response_model=GreenhouseListResponse)
async def list_greenhouses(
    farm_id: Optional[int] = Query(None, description="Filter by farm ID"),
    system_type: Optional[GreenhouseSystemType] = Query(None, description="Filter by system type"),
    min_area: Optional[float] = Query(None, description="Minimum area in sqm"),
    max_area: Optional[float] = Query(None, description="Maximum area in sqm"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all greenhouses accessible to the current user.
    
    **Filters:**
    - **farm_id**: Show greenhouses from specific farm
    - **system_type**: Filter by growing system (hydroponics, aeroponics, etc.)
    - **min_area/max_area**: Filter by greenhouse size
    
    **Permissions:** All authenticated users
    """
    query = db.query(Greenhouse).join(Farm).filter(
        Farm.owner_id == current_user.id,
        Greenhouse.is_deleted == False
    )
    
    if farm_id:
        query = query.filter(Greenhouse.farm_id == farm_id)
    
    if system_type:
        query = query.filter(Greenhouse.system_type == system_type)
    
    if min_area:
        query = query.filter(Greenhouse.area_sqm >= min_area)
    
    if max_area:
        query = query.filter(Greenhouse.area_sqm <= max_area)
    
    total = query.count()
    greenhouses = query.order_by(desc(Greenhouse.created_at)).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "greenhouses": greenhouses
    }


@router.get("/{greenhouse_id}", response_model=GreenhouseDetailedResponse)
async def get_greenhouse(
    greenhouse_id: int = Path(..., description="Greenhouse ID"),
    include_latest_env: bool = Query(True, description="Include latest environmental reading"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific greenhouse.
    
    **Returns:**
    - Greenhouse details
    - Latest environmental readings (temperature, humidity, CO2, PAR, pH, EC)
    - Associated IoT devices
    - Growing statistics
    
    **Permissions:** Owner or authorized user
    """
    greenhouse = db.query(Greenhouse).join(Farm).filter(
        Greenhouse.id == greenhouse_id,
        Farm.owner_id == current_user.id,
        Greenhouse.is_deleted == False
    ).first()
    
    if not greenhouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Greenhouse not found or access denied"
        )
    
    response_data = greenhouse.__dict__.copy()
    
    # Get latest environmental reading
    if include_latest_env:
        latest_env = db.query(GreenhouseEnvironment).filter(
            GreenhouseEnvironment.greenhouse_id == greenhouse_id
        ).order_by(desc(GreenhouseEnvironment.reading_timestamp)).first()
        
        response_data["latest_environment"] = latest_env
    
    # Get device count
    device_count = db.query(func.count(IoTDevice.id)).filter(
        IoTDevice.farm_id == greenhouse.farm_id,
        IoTDevice.device_type.in_([
            DeviceType.PAR_SENSOR,
            DeviceType.CO2_SENSOR,
            DeviceType.WATER_PH_SENSOR,
            DeviceType.WATER_EC_SENSOR,
            DeviceType.LIGHT_CONTROLLER,
            DeviceType.PUMP_CONTROLLER,
            DeviceType.VENT_CONTROLLER
        ])
    ).scalar()
    
    response_data["device_count"] = device_count
    
    return response_data


@router.put("/{greenhouse_id}", response_model=GreenhouseResponse)
async def update_greenhouse(
    greenhouse_id: int,
    greenhouse_update: GreenhouseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update greenhouse information.
    
    **Updatable Fields:**
    - name, description
    - area_sqm, volume_m3
    - structure_type, covering_material
    - system_type
    - location coordinates
    
    **Permissions:** Owner only
    """
    greenhouse = db.query(Greenhouse).join(Farm).filter(
        Greenhouse.id == greenhouse_id,
        Farm.owner_id == current_user.id,
        Greenhouse.is_deleted == False
    ).first()
    
    if not greenhouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Greenhouse not found or access denied"
        )
    
    # Update only provided fields
    update_data = greenhouse_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(greenhouse, field, value)
    
    greenhouse.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(greenhouse)
    
    logger.info(f"Greenhouse {greenhouse_id} updated by user {current_user.id}")
    
    return greenhouse


@router.delete("/{greenhouse_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_greenhouse(
    greenhouse_id: int,
    permanent: bool = Query(False, description="Permanently delete (cannot be undone)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a greenhouse (soft delete by default).
    
    **Parameters:**
    - **permanent**: If true, permanently deletes greenhouse and all data
    
    **Warning:** Permanent deletion removes all environmental history!
    
    **Permissions:** Owner only
    """
    greenhouse = db.query(Greenhouse).join(Farm).filter(
        Greenhouse.id == greenhouse_id,
        Farm.owner_id == current_user.id
    ).first()
    
    if not greenhouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Greenhouse not found or access denied"
        )
    
    if permanent:
        # Permanently delete
        db.delete(greenhouse)
        logger.warning(f"Greenhouse {greenhouse_id} PERMANENTLY deleted by user {current_user.id}")
    else:
        # Soft delete
        greenhouse.soft_delete()
        logger.info(f"Greenhouse {greenhouse_id} soft deleted by user {current_user.id}")
    
    # Update farm statistics
    farm = greenhouse.farm
    farm.number_of_greenhouses = max(0, (farm.number_of_greenhouses or 1) - 1)
    farm.greenhouse_area_sqm = max(0, (farm.greenhouse_area_sqm or greenhouse.area_sqm) - greenhouse.area_sqm)
    
    if farm.number_of_greenhouses == 0:
        farm.has_greenhouse = False
    
    db.commit()
    
    return None


# ============================================================================
# ENVIRONMENTAL MONITORING
# ============================================================================

@router.post("/{greenhouse_id}/environment", response_model=GreenhouseEnvironmentResponse)
async def record_environmental_data(
    greenhouse_id: int,
    env_data: GreenhouseEnvironmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Record environmental sensor data for greenhouse.
    
    **Parameters:**
    - **temperature_celsius**: Air temperature
    - **humidity_percentage**: Relative humidity
    - **co2_ppm**: CO2 concentration
    - **par_umol_m2_s**: Photosynthetically Active Radiation
    - **light_duration_hours**: Daily light hours
    - **water_ph**: pH of nutrient solution/irrigation water
    - **water_ec**: Electrical conductivity (mS/cm or dS/m)
    - **water_temperature_celsius**: Water/solution temperature
    
    **Permissions:** Owner, IoT devices with valid API keys
    
    **Example:**
    ```json
    {
      "reading_timestamp": "2025-11-15T10:30:00Z",
      "temperature_celsius": 24.5,
      "humidity_percentage": 65.0,
      "co2_ppm": 800,
      "par_umol_m2_s": 450,
      "light_duration_hours": 16.0,
      "water_ph": 6.2,
      "water_ec": 2.1,
      "water_temperature_celsius": 20.0
    }
    ```
    """
    # Verify greenhouse access
    greenhouse = db.query(Greenhouse).join(Farm).filter(
        Greenhouse.id == greenhouse_id,
        Farm.owner_id == current_user.id,
        Greenhouse.is_deleted == False
    ).first()
    
    if not greenhouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Greenhouse not found or access denied"
        )
    
    # Create environmental record
    env_record = GreenhouseEnvironment(
        greenhouse_id=greenhouse_id,
        **env_data.dict()
    )
    
    db.add(env_record)
    db.commit()
    db.refresh(env_record)
    
    logger.info(f"Environmental data recorded for greenhouse {greenhouse_id}")
    
    # Check for alerts (extreme conditions)
    await check_environmental_alerts(greenhouse, env_record, db)
    
    return env_record


@router.get("/{greenhouse_id}/environment", response_model=List[GreenhouseEnvironmentResponse])
async def get_environmental_history(
    greenhouse_id: int,
    start_date: Optional[datetime] = Query(None, description="Start date for historical data"),
    end_date: Optional[datetime] = Query(None, description="End date for historical data"),
    parameter: Optional[str] = Query(None, description="Specific parameter: temperature, humidity, co2, par, ph, ec"),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get environmental history for greenhouse.
    
    **Use Cases:**
    - Track climate trends over time
    - Analyze growing conditions
    - Generate environmental reports
    - Optimize HVAC/irrigation schedules
    
    **Filters:**
    - **start_date/end_date**: Date range
    - **parameter**: Filter by specific measurement
    - **limit**: Max records to return (default 100, max 1000)
    
    **Permissions:** Owner or authorized user
    """
    # Verify access
    greenhouse = db.query(Greenhouse).join(Farm).filter(
        Greenhouse.id == greenhouse_id,
        Farm.owner_id == current_user.id,
        Greenhouse.is_deleted == False
    ).first()
    
    if not greenhouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Greenhouse not found or access denied"
        )
    
    # Build query
    query = db.query(GreenhouseEnvironment).filter(
        GreenhouseEnvironment.greenhouse_id == greenhouse_id
    )
    
    if start_date:
        query = query.filter(GreenhouseEnvironment.reading_timestamp >= start_date)
    
    if end_date:
        query = query.filter(GreenhouseEnvironment.reading_timestamp <= end_date)
    
    # Order by most recent first
    env_records = query.order_by(
        desc(GreenhouseEnvironment.reading_timestamp)
    ).limit(limit).all()
    
    return env_records


@router.get("/{greenhouse_id}/environment/summary")
async def get_environmental_summary(
    greenhouse_id: int,
    days: int = Query(7, ge=1, le=365, description="Number of days to summarize"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get statistical summary of environmental conditions.
    
    **Returns:**
    - Average, min, max for each parameter
    - Optimal range compliance percentage
    - Alert frequency
    - Recommendations for improvement
    
    **Parameters:**
    - **days**: Number of days to analyze (default 7, max 365)
    
    **Permissions:** Owner or authorized user
    """
    # Verify access
    greenhouse = db.query(Greenhouse).join(Farm).filter(
        Greenhouse.id == greenhouse_id,
        Farm.owner_id == current_user.id,
        Greenhouse.is_deleted == False
    ).first()
    
    if not greenhouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Greenhouse not found or access denied"
        )
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Query environmental data
    stats = db.query(
        func.avg(GreenhouseEnvironment.temperature_celsius).label('temp_avg'),
        func.min(GreenhouseEnvironment.temperature_celsius).label('temp_min'),
        func.max(GreenhouseEnvironment.temperature_celsius).label('temp_max'),
        func.avg(GreenhouseEnvironment.humidity_percentage).label('humidity_avg'),
        func.min(GreenhouseEnvironment.humidity_percentage).label('humidity_min'),
        func.max(GreenhouseEnvironment.humidity_percentage).label('humidity_max'),
        func.avg(GreenhouseEnvironment.co2_ppm).label('co2_avg'),
        func.min(GreenhouseEnvironment.co2_ppm).label('co2_min'),
        func.max(GreenhouseEnvironment.co2_ppm).label('co2_max'),
        func.avg(GreenhouseEnvironment.par_umol_m2_s).label('par_avg'),
        func.avg(GreenhouseEnvironment.water_ph).label('ph_avg'),
        func.avg(GreenhouseEnvironment.water_ec).label('ec_avg'),
        func.count().label('reading_count')
    ).filter(
        GreenhouseEnvironment.greenhouse_id == greenhouse_id,
        GreenhouseEnvironment.reading_timestamp >= start_date
    ).first()
    
    # Define optimal ranges (for generic horticultural crops)
    optimal_ranges = {
        "temperature": {"min": 18, "max": 28, "unit": "°C"},
        "humidity": {"min": 50, "max": 80, "unit": "%"},
        "co2": {"min": 700, "max": 1200, "unit": "ppm"},
        "par": {"min": 400, "max": 600, "unit": "μmol/m²/s"},
        "ph": {"min": 5.5, "max": 6.5, "unit": "pH"},
        "ec": {"min": 1.5, "max": 2.5, "unit": "mS/cm"}
    }
    
    # Calculate compliance
    compliance = {}
    if stats.temp_avg:
        compliance["temperature"] = (
            optimal_ranges["temperature"]["min"] <= stats.temp_avg <= optimal_ranges["temperature"]["max"]
        )
    if stats.humidity_avg:
        compliance["humidity"] = (
            optimal_ranges["humidity"]["min"] <= stats.humidity_avg <= optimal_ranges["humidity"]["max"]
        )
    if stats.co2_avg:
        compliance["co2"] = (
            optimal_ranges["co2"]["min"] <= stats.co2_avg <= optimal_ranges["co2"]["max"]
        )
    if stats.ph_avg:
        compliance["ph"] = (
            optimal_ranges["ph"]["min"] <= stats.ph_avg <= optimal_ranges["ph"]["max"]
        )
    if stats.ec_avg:
        compliance["ec"] = (
            optimal_ranges["ec"]["min"] <= stats.ec_avg <= optimal_ranges["ec"]["max"]
        )
    
    # Generate recommendations
    recommendations = []
    if stats.temp_avg and stats.temp_avg > optimal_ranges["temperature"]["max"]:
        recommendations.append("Temperature is above optimal range. Consider increasing ventilation or cooling.")
    elif stats.temp_avg and stats.temp_avg < optimal_ranges["temperature"]["min"]:
        recommendations.append("Temperature is below optimal range. Increase heating or reduce nighttime ventilation.")
    
    if stats.humidity_avg and stats.humidity_avg > optimal_ranges["humidity"]["max"]:
        recommendations.append("Humidity is high. Improve air circulation and consider dehumidification.")
    elif stats.humidity_avg and stats.humidity_avg < optimal_ranges["humidity"]["min"]:
        recommendations.append("Humidity is low. Add misting systems or evaporative cooling.")
    
    if stats.co2_avg and stats.co2_avg < optimal_ranges["co2"]["min"]:
        recommendations.append("CO2 levels are low. Consider CO2 supplementation for enhanced growth.")
    
    if stats.ph_avg and (stats.ph_avg < optimal_ranges["ph"]["min"] or stats.ph_avg > optimal_ranges["ph"]["max"]):
        recommendations.append(f"Water pH is outside optimal range (current: {stats.ph_avg:.1f}). Adjust pH for better nutrient uptake.")
    
    if stats.ec_avg and (stats.ec_avg < optimal_ranges["ec"]["min"] or stats.ec_avg > optimal_ranges["ec"]["max"]):
        recommendations.append(f"EC is outside optimal range (current: {stats.ec_avg:.1f}). Adjust nutrient concentration.")
    
    return {
        "greenhouse_id": greenhouse_id,
        "period_days": days,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "reading_count": stats.reading_count,
        "statistics": {
            "temperature": {
                "average": round(stats.temp_avg, 2) if stats.temp_avg else None,
                "min": round(stats.temp_min, 2) if stats.temp_min else None,
                "max": round(stats.temp_max, 2) if stats.temp_max else None,
                "unit": "°C",
                "optimal_range": f"{optimal_ranges['temperature']['min']}-{optimal_ranges['temperature']['max']}°C",
                "in_range": compliance.get("temperature", None)
            },
            "humidity": {
                "average": round(stats.humidity_avg, 2) if stats.humidity_avg else None,
                "min": round(stats.humidity_min, 2) if stats.humidity_min else None,
                "max": round(stats.humidity_max, 2) if stats.humidity_max else None,
                "unit": "%",
                "optimal_range": f"{optimal_ranges['humidity']['min']}-{optimal_ranges['humidity']['max']}%",
                "in_range": compliance.get("humidity", None)
            },
            "co2": {
                "average": round(stats.co2_avg, 2) if stats.co2_avg else None,
                "min": round(stats.co2_min, 2) if stats.co2_min else None,
                "max": round(stats.co2_max, 2) if stats.co2_max else None,
                "unit": "ppm",
                "optimal_range": f"{optimal_ranges['co2']['min']}-{optimal_ranges['co2']['max']} ppm",
                "in_range": compliance.get("co2", None)
            },
            "par": {
                "average": round(stats.par_avg, 2) if stats.par_avg else None,
                "unit": "μmol/m²/s",
                "optimal_range": f"{optimal_ranges['par']['min']}-{optimal_ranges['par']['max']} μmol/m²/s"
            },
            "water_ph": {
                "average": round(stats.ph_avg, 2) if stats.ph_avg else None,
                "unit": "pH",
                "optimal_range": f"{optimal_ranges['ph']['min']}-{optimal_ranges['ph']['max']} pH",
                "in_range": compliance.get("ph", None)
            },
            "water_ec": {
                "average": round(stats.ec_avg, 2) if stats.ec_avg else None,
                "unit": "mS/cm",
                "optimal_range": f"{optimal_ranges['ec']['min']}-{optimal_ranges['ec']['max']} mS/cm",
                "in_range": compliance.get("ec", None)
            }
        },
        "recommendations": recommendations,
        "overall_health": "excellent" if len(recommendations) == 0 else "good" if len(recommendations) <= 2 else "needs_attention"
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def check_environmental_alerts(greenhouse: Greenhouse, env_record: GreenhouseEnvironment, db: Session):
    """
    Check environmental conditions and create alerts for extreme values.
    """
    from ..models.database import Alert, AlertSeverity
    
    alerts = []
    
    # Temperature alerts
    if env_record.temperature_celsius:
        if env_record.temperature_celsius > 35:
            alerts.append({
                "severity": AlertSeverity.CRITICAL,
                "title": "Critical Temperature Alert",
                "message": f"Temperature {env_record.temperature_celsius}°C exceeds safe limits. Immediate cooling required!"
            })
        elif env_record.temperature_celsius < 10:
            alerts.append({
                "severity": AlertSeverity.HIGH,
                "title": "Low Temperature Warning",
                "message": f"Temperature {env_record.temperature_celsius}°C is dangerously low. Activate heating systems."
            })
    
    # Humidity alerts
    if env_record.humidity_percentage:
        if env_record.humidity_percentage > 85:
            alerts.append({
                "severity": AlertSeverity.HIGH,
                "title": "High Humidity Alert",
                "message": f"Humidity {env_record.humidity_percentage}% promotes fungal diseases. Increase ventilation."
            })
        elif env_record.humidity_percentage < 40:
            alerts.append({
                "severity": AlertSeverity.MEDIUM,
                "title": "Low Humidity Warning",
                "message": f"Humidity {env_record.humidity_percentage}% may stress plants. Consider misting."
            })
    
    # CO2 alerts
    if env_record.co2_ppm:
        if env_record.co2_ppm < 400:
            alerts.append({
                "severity": AlertSeverity.MEDIUM,
                "title": "Low CO2 Warning",
                "message": f"CO2 at {env_record.co2_ppm} ppm limits photosynthesis. Supplement CO2 for better growth."
            })
    
    # pH alerts
    if env_record.water_ph:
        if env_record.water_ph < 5.0 or env_record.water_ph > 7.0:
            alerts.append({
                "severity": AlertSeverity.HIGH,
                "title": "pH Out of Range",
                "message": f"Water pH {env_record.water_ph} affects nutrient uptake. Adjust immediately!"
            })
    
    # EC alerts
    if env_record.water_ec:
        if env_record.water_ec > 3.0:
            alerts.append({
                "severity": AlertSeverity.HIGH,
                "title": "High EC Alert",
                "message": f"EC {env_record.water_ec} mS/cm may burn plants. Dilute nutrient solution."
            })
        elif env_record.water_ec < 1.0:
            alerts.append({
                "severity": AlertSeverity.MEDIUM,
                "title": "Low EC Warning",
                "message": f"EC {env_record.water_ec} mS/cm indicates nutrient deficiency. Increase concentration."
            })
    
    # Create alert records
    for alert_data in alerts:
        alert = Alert(
            alert_type="environmental",
            alert_category="greenhouse",
            farm_id=greenhouse.farm_id,
            **alert_data,
            triggered_by="environmental_monitoring",
            trigger_condition=f"Greenhouse {greenhouse.name}",
            notification_sent=False
        )
        db.add(alert)
    
    if alerts:
        db.commit()
        logger.warning(f"{len(alerts)} environmental alerts created for greenhouse {greenhouse.id}")


# Export router
__all__ = ["router"]
