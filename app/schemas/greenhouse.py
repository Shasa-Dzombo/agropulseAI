"""
🌿 AgroPulse - Greenhouse Pydantic Schemas
Request/response models for greenhouse API endpoints.

Author: AgroPulse Engineering Team
Date: November 2025
Version: 2.0.0-horticulture
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from enum import Enum


# ============================================================================
# ENUMERATIONS
# ============================================================================

class GreenhouseSystemType(str, Enum):
    """Types of greenhouse growing systems."""
    HYDROPONICS = "hydroponics"
    AEROPONICS = "aeroponics"
    AQUAPONICS = "aquaponics"
    SOIL_BASED = "soil_based"
    VERTICAL_FARM = "vertical_farm"


class StructureType(str, Enum):
    """Greenhouse structure types."""
    DOME = "dome"
    A_FRAME = "a_frame"
    GOTHIC_ARCH = "gothic_arch"
    QUONSET = "quonset"
    GABLE = "gable"
    SAWTOOTH = "sawtooth"
    RETRACTABLE_ROOF = "retractable_roof"


class CoveringMaterial(str, Enum):
    """Greenhouse covering materials."""
    GLASS = "glass"
    POLYCARBONATE_TWIN_WALL = "polycarbonate_twin_wall"
    POLYCARBONATE_MULTI_WALL = "polycarbonate_multi_wall"
    POLYETHYLENE_FILM = "polyethylene_film"
    ACRYLIC = "acrylic"
    FIBERGLASS = "fiberglass"


# ============================================================================
# GREENHOUSE SCHEMAS
# ============================================================================

class GreenhouseBase(BaseModel):
    """Base greenhouse schema with common fields."""
    name: str = Field(..., min_length=1, max_length=200, description="Greenhouse name")
    description: Optional[str] = Field(None, description="Detailed description")
    area_sqm: float = Field(..., gt=0, description="Area in square meters")
    volume_m3: Optional[float] = Field(None, gt=0, description="Volume in cubic meters")
    structure_type: Optional[str] = Field(None, max_length=100, description="Structure type")
    covering_material: Optional[str] = Field(None, max_length=100, description="Covering material")
    system_type: Optional[GreenhouseSystemType] = Field(None, description="Growing system type")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude")
    altitude: Optional[float] = Field(None, description="Altitude in meters")

    class Config:
        use_enum_values = True


class GreenhouseCreate(GreenhouseBase):
    """Schema for creating a new greenhouse."""
    pass


class GreenhouseUpdate(BaseModel):
    """Schema for updating greenhouse (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    area_sqm: Optional[float] = Field(None, gt=0)
    volume_m3: Optional[float] = Field(None, gt=0)
    structure_type: Optional[str] = Field(None, max_length=100)
    covering_material: Optional[str] = Field(None, max_length=100)
    system_type: Optional[GreenhouseSystemType] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    altitude: Optional[float] = None

    class Config:
        use_enum_values = True


class GreenhouseResponse(GreenhouseBase):
    """Schema for greenhouse response."""
    id: int
    uuid: str
    farm_id: int
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    class Config:
        from_attributes = True


class GreenhouseDetailedResponse(GreenhouseResponse):
    """Detailed greenhouse response with additional data."""
    latest_environment: Optional["GreenhouseEnvironmentResponse"] = None
    device_count: int = 0

    class Config:
        from_attributes = True


class GreenhouseListResponse(BaseModel):
    """Paginated list of greenhouses."""
    total: int
    skip: int
    limit: int
    greenhouses: List[GreenhouseResponse]


# ============================================================================
# ENVIRONMENTAL DATA SCHEMAS
# ============================================================================

class GreenhouseEnvironmentBase(BaseModel):
    """Base schema for environmental data."""
    reading_timestamp: datetime = Field(..., description="Timestamp of sensor reading")
    temperature_celsius: Optional[float] = Field(None, ge=-50, le=60, description="Air temperature in °C")
    humidity_percentage: Optional[float] = Field(None, ge=0, le=100, description="Relative humidity %")
    co2_ppm: Optional[float] = Field(None, ge=0, le=5000, description="CO2 concentration in ppm")
    par_umol_m2_s: Optional[float] = Field(None, ge=0, le=3000, description="PAR in μmol/m²/s")
    light_duration_hours: Optional[float] = Field(None, ge=0, le=24, description="Daily light hours")
    water_ph: Optional[float] = Field(None, ge=0, le=14, description="Water pH")
    water_ec: Optional[float] = Field(None, ge=0, le=10, description="Electrical conductivity in mS/cm")
    water_temperature_celsius: Optional[float] = Field(None, ge=0, le=40, description="Water temperature in °C")


class GreenhouseEnvironmentCreate(GreenhouseEnvironmentBase):
    """Schema for recording environmental data."""
    
    @validator('reading_timestamp')
    def validate_timestamp(cls, v):
        """Ensure timestamp is not in the future."""
        if v > datetime.utcnow():
            raise ValueError("Reading timestamp cannot be in the future")
        return v
    
    @validator('water_ph')
    def validate_ph_range(cls, v):
        """Validate pH is in practical range for horticulture."""
        if v is not None and (v < 4.0 or v > 9.0):
            raise ValueError("pH must be between 4.0 and 9.0 for horticultural applications")
        return v


class GreenhouseEnvironmentResponse(GreenhouseEnvironmentBase):
    """Schema for environmental data response."""
    id: int
    greenhouse_id: int

    class Config:
        from_attributes = True


class EnvironmentalSummary(BaseModel):
    """Statistical summary of environmental conditions."""
    greenhouse_id: int
    period_days: int
    start_date: str
    end_date: str
    reading_count: int
    statistics: dict
    recommendations: List[str]
    overall_health: str  # excellent, good, needs_attention, critical


# ============================================================================
# CROP-SPECIFIC OPTIMAL RANGES
# ============================================================================

class CropOptimalRanges(BaseModel):
    """Optimal environmental ranges for specific crops."""
    crop_name: str
    temperature_range: dict = Field(..., description="Min/max temperature in °C")
    humidity_range: dict = Field(..., description="Min/max humidity %")
    co2_optimal: int = Field(..., description="Optimal CO2 in ppm")
    par_optimal: int = Field(..., description="Optimal PAR in μmol/m²/s")
    photoperiod_hours: float = Field(..., description="Daily light hours required")
    ph_range: dict = Field(..., description="Optimal pH range")
    ec_range: dict = Field(..., description="Optimal EC range in mS/cm")


# Predefined optimal ranges for common horticultural crops
CROP_OPTIMAL_CONDITIONS = {
    "tomato": CropOptimalRanges(
        crop_name="Tomato (Solanum lycopersicum)",
        temperature_range={"day": {"min": 21, "max": 27}, "night": {"min": 16, "max": 18}},
        humidity_range={"min": 60, "max": 80},
        co2_optimal=1000,
        par_optimal=500,
        photoperiod_hours=16,
        ph_range={"min": 5.5, "max": 6.5},
        ec_range={"min": 2.0, "max": 3.5}
    ),
    "lettuce": CropOptimalRanges(
        crop_name="Lettuce (Lactuca sativa)",
        temperature_range={"day": {"min": 18, "max": 24}, "night": {"min": 12, "max": 16}},
        humidity_range={"min": 50, "max": 70},
        co2_optimal=800,
        par_optimal=300,
        photoperiod_hours=12,
        ph_range={"min": 5.5, "max": 6.5},
        ec_range={"min": 1.2, "max": 2.0}
    ),
    "cucumber": CropOptimalRanges(
        crop_name="Cucumber (Cucumis sativus)",
        temperature_range={"day": {"min": 22, "max": 28}, "night": {"min": 18, "max": 20}},
        humidity_range={"min": 70, "max": 85},
        co2_optimal=1000,
        par_optimal=500,
        photoperiod_hours=14,
        ph_range={"min": 5.5, "max": 6.5},
        ec_range={"min": 2.2, "max": 3.0}
    ),
    "pepper": CropOptimalRanges(
        crop_name="Bell Pepper (Capsicum annuum)",
        temperature_range={"day": {"min": 22, "max": 28}, "night": {"min": 18, "max": 20}},
        humidity_range={"min": 60, "max": 75},
        co2_optimal=1000,
        par_optimal=500,
        photoperiod_hours=16,
        ph_range={"min": 5.8, "max": 6.5},
        ec_range={"min": 2.0, "max": 3.0}
    ),
    "strawberry": CropOptimalRanges(
        crop_name="Strawberry (Fragaria × ananassa)",
        temperature_range={"day": {"min": 20, "max": 26}, "night": {"min": 12, "max": 16}},
        humidity_range={"min": 60, "max": 80},
        co2_optimal=900,
        par_optimal=400,
        photoperiod_hours=12,
        ph_range={"min": 5.5, "max": 6.5},
        ec_range={"min": 1.0, "max": 1.8}
    ),
    "basil": CropOptimalRanges(
        crop_name="Basil (Ocimum basilicum)",
        temperature_range={"day": {"min": 22, "max": 28}, "night": {"min": 18, "max": 20}},
        humidity_range={"min": 60, "max": 75},
        co2_optimal=800,
        par_optimal=350,
        photoperiod_hours=14,
        ph_range={"min": 5.5, "max": 6.5},
        ec_range={"min": 1.0, "max": 1.6}
    ),
    "orchid": CropOptimalRanges(
        crop_name="Orchid (Phalaenopsis)",
        temperature_range={"day": {"min": 22, "max": 28}, "night": {"min": 18, "max": 22}},
        humidity_range={"min": 60, "max": 80},
        co2_optimal=600,
        par_optimal=200,
        photoperiod_hours=12,
        ph_range={"min": 5.5, "max": 6.5},
        ec_range={"min": 0.8, "max": 1.5}
    ),
    "cannabis": CropOptimalRanges(
        crop_name="Cannabis (Medical/Industrial)",
        temperature_range={"day": {"min": 22, "max": 28}, "night": {"min": 18, "max": 22}},
        humidity_range={"min": 40, "max": 60},
        co2_optimal=1200,
        par_optimal=600,
        photoperiod_hours=18,  # vegetative stage
        ph_range={"min": 5.8, "max": 6.5},
        ec_range={"min": 1.8, "max": 2.8}
    )
}


# Export all schemas
__all__ = [
    "GreenhouseSystemType",
    "StructureType",
    "CoveringMaterial",
    "GreenhouseBase",
    "GreenhouseCreate",
    "GreenhouseUpdate",
    "GreenhouseResponse",
    "GreenhouseDetailedResponse",
    "GreenhouseListResponse",
    "GreenhouseEnvironmentBase",
    "GreenhouseEnvironmentCreate",
    "GreenhouseEnvironmentResponse",
    "EnvironmentalSummary",
    "CropOptimalRanges",
    "CROP_OPTIMAL_CONDITIONS"
]
