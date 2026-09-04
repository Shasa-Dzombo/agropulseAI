from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class FarmInputRecordCreateRequest(BaseModel):
    entry_type: str = Field(pattern="^(purchase|application)$")
    category: str = Field(pattern="^(seed|fertilizer|pesticide|labor|other)$")
    item_name: str = Field(min_length=1, max_length=200)
    quantity: Optional[float] = Field(None, gt=0)
    unit: Optional[str] = Field(None, max_length=50)
    # Purchase-specific - ignored for entry_type='application'.
    cost_ksh: Optional[Decimal] = Field(None, ge=0)
    notes: Optional[str] = None
    entry_date: date


class FarmInputRecordResponse(BaseModel):
    id: int
    farm_id: int
    entry_type: str
    category: str
    item_name: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    cost_ksh: Optional[Decimal] = None
    notes: Optional[str] = None
    entry_date: date
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FarmInputListResponse(BaseModel):
    items: List[FarmInputRecordResponse]
    total_cost_ksh: Decimal


class FarmYieldRecordCreateRequest(BaseModel):
    crop: str = Field(min_length=1, max_length=100)
    season_label: str = Field(min_length=1, max_length=50)
    planted_date: Optional[date] = None
    expected_yield_kg: Optional[float] = Field(None, gt=0)


class FarmYieldRecordUpdateRequest(BaseModel):
    """Recording the actual harvest against an existing (expected-only)
    yield record - the common second step after planting."""
    actual_yield_kg: Optional[float] = Field(None, gt=0)
    harvest_date: Optional[date] = None
    notes: Optional[str] = None


class FarmYieldRecordResponse(BaseModel):
    id: int
    farm_id: int
    crop: str
    season_label: str
    planted_date: Optional[date] = None
    expected_yield_kg: Optional[float] = None
    actual_yield_kg: Optional[float] = None
    harvest_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FarmYieldListResponse(BaseModel):
    items: List[FarmYieldRecordResponse]
