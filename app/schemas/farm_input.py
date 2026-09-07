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


class FarmInputRecordUpdateRequest(BaseModel):
    """Partial update - correct a typo'd item name, wrong cost, wrong date,
    etc. Every field optional; only supplied ones change."""
    entry_type: Optional[str] = Field(None, pattern="^(purchase|application)$")
    category: Optional[str] = Field(None, pattern="^(seed|fertilizer|pesticide|labor|other)$")
    item_name: Optional[str] = Field(None, min_length=1, max_length=200)
    quantity: Optional[float] = Field(None, gt=0)
    unit: Optional[str] = Field(None, max_length=50)
    cost_ksh: Optional[Decimal] = Field(None, ge=0)
    notes: Optional[str] = None
    entry_date: Optional[date] = None


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
    """Partial update - covers both recording the actual harvest against an
    existing (expected-only) record and correcting any field of it (a typo
    in the crop name, a re-estimated expected yield, etc). Every field is
    optional; only the ones supplied are changed."""
    crop: Optional[str] = Field(None, min_length=1, max_length=100)
    season_label: Optional[str] = Field(None, min_length=1, max_length=50)
    planted_date: Optional[date] = None
    expected_yield_kg: Optional[float] = Field(None, gt=0)
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
    # Computed at read time from app.services.yield_estimation - never
    # persisted, so it always reflects the current reference data and the
    # farm's current size_acres. None when the crop isn't in the reference
    # table yet (see that module) - never a guessed number.
    estimated_yield_kg: Optional[float] = None
    estimate_source: Optional[str] = None

    class Config:
        from_attributes = True


class FarmYieldListResponse(BaseModel):
    items: List[FarmYieldRecordResponse]
