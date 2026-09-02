"""
🌿 Greenhouse Facilities API

FastAPI endpoints for greenhouse/growing facility management, climate control, and production operations.

Endpoints:
- GET /farms - List greenhouse facilities with pagination
- POST /farms - Create new greenhouse facility
- GET /farms/{farm_id} - Get facility details
- PATCH /farms/{farm_id} - Update facility
- DELETE /farms/{farm_id} - Delete facility
- GET /farms/nearby - Find nearby facilities
- GET /farms/search - Search greenhouse facilities
- GET /farms/statistics - Facility statistics
- GET /farms/{farm_id}/fields - Get growing zones
- POST /farms/{farm_id}/fields - Create growing zone
- GET /farms/{farm_id}/plantings - Get crop plantings
- POST /farms/{farm_id}/verify - Verify facility
- GET /farms/{farm_id}/weather - Current weather, agricultural alerts, and disease-pressure risk

Note: 'farms' endpoint maintained for API compatibility, but represents greenhouse facilities.

Author: AgroPulse Engineering Team
"""

import asyncio
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from app.db_config import get_production_db_dependency
from app.repositories.farm import FarmRepository
from app.api.auth import get_current_user
from app.schemas.drone import WeatherSnapshotOut, DiseasePressureOut, AgriculturalAlertOut
from app.services.weather_service import get_openweather_client, fetch_weather_snapshot, assess_disease_pressure


router = APIRouter(prefix="/farms", tags=["Greenhouse Facilities"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class FarmCreateRequest(BaseModel):
    """Create greenhouse facility request."""
    name: str = Field(..., min_length=1, max_length=200, description="Facility/greenhouse name")
    description: Optional[str] = Field(None, description="Facility description")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    altitude: Optional[float] = Field(None, description="Altitude in meters")
    size_acres: float = Field(..., gt=0, description="Total facility size in acres")
    county: str = Field(..., max_length=100, description="County location")
    sub_county: Optional[str] = Field(None, description="Sub-county location")
    ward: Optional[str] = None
    village: Optional[str] = None
    farm_type: Optional[str] = None
    primary_crop: Optional[str] = None
    soil_type: Optional[str] = None
    water_source: Optional[str] = None
    irrigation_type: Optional[str] = None
    has_irrigation: bool = False
    boundary_geojson: Optional[dict] = None


class FarmUpdateRequest(BaseModel):
    """Update farm request."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    size_acres: Optional[float] = Field(None, gt=0)
    primary_crop: Optional[str] = None
    soil_type: Optional[str] = None
    water_source: Optional[str] = None
    irrigation_type: Optional[str] = None
    has_irrigation: Optional[bool] = None
    organic_certified: Optional[bool] = None
    gap_certified: Optional[bool] = None


class FarmListResponse(BaseModel):
    """Farm list response."""
    id: int
    uuid: UUID
    name: str
    county: str
    size_acres: float
    primary_crop: Optional[str] = None
    latitude: float
    longitude: float
    is_active: bool
    verification_status: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class FarmDetailResponse(BaseModel):
    """Detailed farm response."""
    id: int
    uuid: UUID
    owner_id: int
    name: str
    description: Optional[str]
    farm_code: Optional[str]
    
    # Location
    latitude: float
    longitude: float
    altitude: Optional[float]
    county: str
    sub_county: Optional[str]
    ward: Optional[str]
    village: Optional[str]
    
    # Size
    size_acres: float
    size_hectares: Optional[float]
    cultivated_area_acres: Optional[float]
    
    # Farm details
    farm_type: Optional[str]
    primary_crop: Optional[str]
    soil_type: Optional[str]
    soil_ph: Optional[float]
    
    # Water
    water_source: Optional[str]
    irrigation_type: Optional[str]
    has_irrigation: bool
    
    # Certifications
    organic_certified: bool
    gap_certified: bool

    # Status
    is_active: bool
    verification_status: str
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class NearbyFarmsRequest(BaseModel):
    """Nearby farms search request."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radius_km: float = Field(10.0, ge=0.1, le=100)
    limit: int = Field(50, ge=1, le=100)


class FieldCreateRequest(BaseModel):
    """Create field request."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    size_acres: float = Field(..., gt=0)
    soil_type: Optional[str] = None
    boundary_geojson: Optional[dict] = None


class FieldResponse(BaseModel):
    """Field response."""
    id: int
    uuid: UUID
    farm_id: int
    name: str
    size_acres: float
    soil_type: Optional[str]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class PaginatedFarmsResponse(BaseModel):
    """Paginated farms response."""
    items: List[FarmListResponse]
    total: int
    page: int
    page_size: int
    pages: int


class FarmStatisticsResponse(BaseModel):
    """Farm statistics response."""
    total_farms: int
    active_farms: int
    verified_farms: int
    organic_certified: int
    irrigated_farms: int
    total_area_acres: float
    average_size_acres: float
    county_breakdown: dict
    crop_distribution: dict


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def check_farm_access(current_user: dict, farm_user_id: int):
    """Check if user can access farm."""
    if current_user['role'] not in ['admin', 'agronomist', 'superuser']:
        if current_user['id'] != farm_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("", response_model=PaginatedFarmsResponse)
async def list_farms(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    county: Optional[str] = None,
    crop: Optional[str] = None,
    min_size: Optional[float] = None,
    max_size: Optional[float] = None,
    organic_only: bool = False,
    verified_only: bool = False,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    List farms with pagination and filters.
    
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **county**: Filter by county (optional)
    - **crop**: Filter by primary crop (optional)
    - **min_size**: Minimum farm size in acres (optional)
    - **max_size**: Maximum farm size in acres (optional)
    - **organic_only**: Show only organic certified (default: false)
    - **verified_only**: Show only verified farms (default: false)
    """
    farm_repo = FarmRepository(db)
    
    # Build filters
    filters = {}
    if organic_only:
        filters['organic_certified'] = True
    if verified_only:
        filters['verification_status'] = 'verified'
    if county:
        filters['county'] = county
    if crop:
        filters['primary_crop'] = crop
    
    # Get farms
    skip = (page - 1) * page_size
    
    if min_size is not None or max_size is not None:
        farms = farm_repo.get_by_size_range(
            min_acres=min_size or 0,
            max_acres=max_size or 999999,
            skip=skip,
            limit=page_size
        )
        total = len(farms)  # Approximate
    else:
        farms = farm_repo.filter(filters, skip=skip, limit=page_size)
        total = farm_repo.count(filters)
    
    return PaginatedFarmsResponse(
        items=farms,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.post("", response_model=FarmDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_farm(
    request: FarmCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Create new farm.
    
    - **name**: Farm name (required)
    - **latitude**: Latitude coordinate (required)
    - **longitude**: Longitude coordinate (required)
    - **size_acres**: Farm size in acres (required)
    - **county**: County location (required)
    - Other fields are optional
    """
    farm_repo = FarmRepository(db)
    
    # Convert acres to hectares
    size_hectares = request.size_acres * 0.404686
    
    farm = farm_repo.create(
        owner_id=current_user['id'],
        name=request.name,
        description=request.description,
        latitude=request.latitude,
        longitude=request.longitude,
        altitude=request.altitude,
        size_acres=request.size_acres,
        size_hectares=size_hectares,
        county=request.county,
        sub_county=request.sub_county,
        ward=request.ward,
        village=request.village,
        farm_type=request.farm_type,
        primary_crop=request.primary_crop,
        soil_type=request.soil_type,
        water_source=request.water_source,
        irrigation_type=request.irrigation_type,
        has_irrigation=request.has_irrigation,
        boundary_geojson=request.boundary_geojson,
        verification_status='pending'
    )
    
    return farm


@router.get("/nearby", response_model=List[FarmListResponse])
async def find_nearby_farms(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(10.0, ge=0.1, le=100),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Find farms near a location using PostGIS.
    
    - **latitude**: Center point latitude
    - **longitude**: Center point longitude
    - **radius_km**: Search radius in kilometers (default: 10km, max: 100km)
    - **limit**: Maximum results (default: 50, max: 100)
    
    Returns farms within the specified radius, ordered by distance.
    """
    farm_repo = FarmRepository(db)
    
    farms = farm_repo.get_by_location(
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        skip=0,
        limit=limit
    )
    
    return farms


@router.get("/search", response_model=List[FarmListResponse])
async def search_farms(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Search farms by name or description.
    
    - **q**: Search query (min 2 characters)
    - **limit**: Maximum results (default: 20, max: 100)
    """
    farm_repo = FarmRepository(db)
    farms = farm_repo.search_farms(q, skip=0, limit=limit)
    
    return farms


@router.get("/statistics", response_model=FarmStatisticsResponse)
async def get_farm_statistics(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Get farm statistics.
    
    Requires admin or agronomist role.
    """
    if current_user['role'] not in ['admin', 'agronomist', 'superuser']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or agronomist access required"
        )
    
    farm_repo = FarmRepository(db)
    stats = farm_repo.get_farm_statistics()
    county_breakdown = farm_repo.get_county_breakdown()
    crop_distribution = farm_repo.get_crop_distribution()
    
    return FarmStatisticsResponse(
        **stats,
        county_breakdown=county_breakdown,
        crop_distribution=crop_distribution
    )


@router.get("/{farm_id}", response_model=FarmDetailResponse)
async def get_farm(
    farm_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Get farm details by ID.
    
    Users can access their own farms.
    Admins and agronomists can access any farm.
    """
    farm_repo = FarmRepository(db)
    farm = farm_repo.get_by_id(farm_id)
    
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found"
        )
    
    check_farm_access(current_user, farm.owner_id)

    return farm


class FarmWeatherOut(BaseModel):
    """Current weather for a farm's location, plus agricultural alerts and
    disease-pressure risk - see app.services.weather_service. Advisory only."""
    farm_id: int
    current: WeatherSnapshotOut
    disease_pressure: DiseasePressureOut
    agricultural_alerts: List[AgriculturalAlertOut] = []


@router.get("/{farm_id}/weather", response_model=FarmWeatherOut)
async def get_farm_weather(
    farm_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Current weather, agricultural alerts (frost/heat/drought/flood/wind),
    and disease-pressure risk for a farm's location, via OpenWeatherMap.
    """
    farm_repo = FarmRepository(db)
    farm = farm_repo.get_by_id(farm_id)

    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")

    check_farm_access(current_user, farm.owner_id)

    client = get_openweather_client()
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Weather service is not configured")

    weather = await fetch_weather_snapshot(client, farm.latitude, farm.longitude)
    if weather is None:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch current weather")

    forecast = await asyncio.to_thread(client.get_5day_forecast, farm.latitude, farm.longitude)
    alerts = await asyncio.to_thread(client.get_agricultural_alerts, farm.latitude, farm.longitude, weather, forecast)
    disease_pressure = assess_disease_pressure(weather)

    return FarmWeatherOut(
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
        disease_pressure=DiseasePressureOut(
            risk_level=disease_pressure.risk_level,
            indicators=disease_pressure.indicators,
        ),
        agricultural_alerts=[
            AgriculturalAlertOut(
                alert_type=a.alert_type,
                severity=a.severity,
                description=a.description,
                recommendations=a.recommendations,
            )
            for a in alerts
        ],
    )


@router.patch("/{farm_id}", response_model=FarmDetailResponse)
async def update_farm(
    farm_id: int,
    request: FarmUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Update farm details.
    
    Users can update their own farms.
    Admins can update any farm.
    """
    farm_repo = FarmRepository(db)
    farm = farm_repo.get_by_id(farm_id)
    
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found"
        )
    
    check_farm_access(current_user, farm.owner_id)
    
    # Filter out None values
    update_data = {k: v for k, v in request.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data to update"
        )
    
    # Update size_hectares if size_acres changed
    if 'size_acres' in update_data:
        update_data['size_hectares'] = update_data['size_acres'] * 0.404686
    
    updated_farm = farm_repo.update(farm, **update_data)
    
    return updated_farm


@router.delete("/{farm_id}")
async def delete_farm(
    farm_id: int,
    permanent: bool = Query(False),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Delete farm (soft delete by default).
    
    - **permanent**: Permanent delete (requires admin)
    
    Users can delete their own farms.
    Admins can delete any farm.
    """
    farm_repo = FarmRepository(db)
    farm = farm_repo.get_by_id(farm_id)
    
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found"
        )
    
    check_farm_access(current_user, farm.owner_id)
    
    if permanent and current_user['role'] not in ['admin', 'superuser']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for permanent deletion"
        )
    
    success = farm_repo.delete(farm, soft=not permanent)
    
    return {
        "message": "Farm deleted successfully",
        "permanent": permanent
    }


@router.get("/{farm_id}/fields", response_model=List[FieldResponse])
async def get_farm_fields(
    farm_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Get all fields for a farm.
    
    Users can access their own farm's fields.
    Admins and agronomists can access any farm's fields.
    """
    farm_repo = FarmRepository(db)
    farm = farm_repo.get_by_id(farm_id)
    
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found"
        )
    
    check_farm_access(current_user, farm.owner_id)
    
    fields = farm_repo.get_fields(farm_id)
    
    return fields


@router.post("/{farm_id}/fields", response_model=FieldResponse, status_code=status.HTTP_201_CREATED)
async def create_field(
    farm_id: int,
    request: FieldCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Create new field in a farm.
    
    - **name**: Field name (required)
    - **size_acres**: Field size in acres (required)
    - Other fields are optional
    """
    from app.models.database import Field
    
    farm_repo = FarmRepository(db)
    farm = farm_repo.get_by_id(farm_id)
    
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found"
        )
    
    check_farm_access(current_user, farm.owner_id)

    # Note: unlike Farm, the Field model has no size_hectares column - don't
    # pass one to the constructor (it would reject the unknown kwarg).
    field = Field(
        farm_id=farm_id,
        name=request.name,
        description=request.description,
        size_acres=request.size_acres,
        soil_type=request.soil_type,
        boundary_geojson=request.boundary_geojson
    )
    
    db.add(field)
    db.commit()
    db.refresh(field)
    
    return field


@router.get("/{farm_id}/plantings")
async def get_farm_plantings(
    farm_id: int,
    active_only: bool = True,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Get crop plantings for a farm.
    
    - **active_only**: Show only active plantings (default: true)
    """
    farm_repo = FarmRepository(db)
    farm = farm_repo.get_by_id(farm_id)
    
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found"
        )
    
    check_farm_access(current_user, farm.owner_id)
    
    if active_only:
        plantings = farm_repo.get_active_plantings(farm_id)
    else:
        from app.models.database import CropPlanting
        plantings = db.query(CropPlanting).filter(
            CropPlanting.farm_id == farm_id,
            CropPlanting.is_deleted == False
        ).all()
    
    return {
        "farm_id": farm_id,
        "total_plantings": len(plantings),
        "plantings": plantings
    }


@router.post("/{farm_id}/verify")
async def verify_farm(
    farm_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Verify a farm.
    
    Requires admin or agronomist role.
    """
    if current_user['role'] not in ['admin', 'agronomist', 'superuser']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or agronomist access required"
        )
    
    farm_repo = FarmRepository(db)
    farm = farm_repo.verify_farm(farm_id)
    
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found"
        )
    
    return {
        "message": "Farm verified successfully",
        "farm_id": farm_id,
        "verification_status": farm.verification_status
    }
