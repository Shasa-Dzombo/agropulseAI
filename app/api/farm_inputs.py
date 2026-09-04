"""
Farm input log and yield tracking - v1, real and deliberately small.

Scope was set directly by the user: a chronological per-farm log of input
purchases (bought X, cost Y, on date Z) and applications (applied X to the
field on date Y) - one model for both, since that's how a farmer actually
thinks about "what happened this season", not two separate systems. Yield
tracking is a plain record (expected at planting, actual at harvest) with
no predictive modeling - there's no real historical yield data yet to model
from, and modeling off the drone NDVI pipeline would inherit that
pipeline's own accuracy caveats (see DroneImage.hasRealNir in the mobile
app / app/drones/flight/camera.py's green_channel_as_nir_placeholder).

Same access-control pattern as app/services/drone_ai_service.py: every
record is scoped to a farm the caller owns.
"""

from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db_config import get_production_db_dependency
from app.models.database import Farm, FarmInputRecord, FarmYieldRecord
from app.schemas.farm_input import (
    FarmInputListResponse, FarmInputRecordCreateRequest, FarmInputRecordResponse,
    FarmYieldListResponse, FarmYieldRecordCreateRequest, FarmYieldRecordResponse,
    FarmYieldRecordUpdateRequest,
)

router = APIRouter(prefix="/farms/{farm_id}", tags=["Farm Inputs & Yield"])


def _get_owned_farm_or_raise(db: Session, farm_id: int, user_id: int) -> Farm:
    farm = db.execute(
        select(Farm).where(Farm.id == farm_id, Farm.owner_id == user_id)
    ).scalar_one_or_none()
    if farm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found or you don't have permission")
    return farm


# ============================================================================
# INPUT LOG
# ============================================================================

@router.post("/inputs", response_model=FarmInputRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_input_record(
    farm_id: int,
    request: FarmInputRecordCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    _get_owned_farm_or_raise(db, farm_id, current_user["id"])
    record = FarmInputRecord(
        farm_id=farm_id,
        created_by_id=current_user["id"],
        entry_type=request.entry_type,
        category=request.category,
        item_name=request.item_name,
        quantity=request.quantity,
        unit=request.unit,
        cost_ksh=request.cost_ksh if request.entry_type == "purchase" else None,
        notes=request.notes,
        entry_date=request.entry_date,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/inputs", response_model=FarmInputListResponse)
async def list_input_records(
    farm_id: int,
    entry_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    _get_owned_farm_or_raise(db, farm_id, current_user["id"])
    query = select(FarmInputRecord).where(
        FarmInputRecord.farm_id == farm_id, FarmInputRecord.is_deleted == False,  # noqa: E712
    )
    if entry_type is not None:
        query = query.where(FarmInputRecord.entry_type == entry_type)
    records = db.execute(query.order_by(FarmInputRecord.entry_date.desc())).scalars().all()
    total_cost = sum((r.cost_ksh for r in records if r.cost_ksh is not None), Decimal("0"))
    return FarmInputListResponse(items=records, total_cost_ksh=total_cost)


@router.delete("/inputs/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_input_record(
    farm_id: int,
    record_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    _get_owned_farm_or_raise(db, farm_id, current_user["id"])
    record = db.execute(
        select(FarmInputRecord).where(FarmInputRecord.id == record_id, FarmInputRecord.farm_id == farm_id)
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Input record not found")
    record.soft_delete()
    db.commit()


# ============================================================================
# YIELD TRACKING
# ============================================================================

@router.post("/yields", response_model=FarmYieldRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_yield_record(
    farm_id: int,
    request: FarmYieldRecordCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    _get_owned_farm_or_raise(db, farm_id, current_user["id"])
    record = FarmYieldRecord(
        farm_id=farm_id,
        created_by_id=current_user["id"],
        crop=request.crop,
        season_label=request.season_label,
        planted_date=request.planted_date,
        expected_yield_kg=request.expected_yield_kg,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/yields", response_model=FarmYieldListResponse)
async def list_yield_records(
    farm_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    _get_owned_farm_or_raise(db, farm_id, current_user["id"])
    records = db.execute(
        select(FarmYieldRecord)
        .where(FarmYieldRecord.farm_id == farm_id, FarmYieldRecord.is_deleted == False)  # noqa: E712
        .order_by(FarmYieldRecord.planted_date.desc().nulls_last())
    ).scalars().all()
    return FarmYieldListResponse(items=records)


@router.patch("/yields/{record_id}", response_model=FarmYieldRecordResponse)
async def update_yield_record(
    farm_id: int,
    record_id: int,
    request: FarmYieldRecordUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    """Records the actual harvest against an existing (expected-only) yield
    record - the common second step after planting."""
    _get_owned_farm_or_raise(db, farm_id, current_user["id"])
    record = db.execute(
        select(FarmYieldRecord).where(FarmYieldRecord.id == record_id, FarmYieldRecord.farm_id == farm_id)
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Yield record not found")

    if request.actual_yield_kg is not None:
        record.actual_yield_kg = request.actual_yield_kg
    if request.harvest_date is not None:
        record.harvest_date = request.harvest_date
    if request.notes is not None:
        record.notes = request.notes

    db.commit()
    db.refresh(record)
    return record
