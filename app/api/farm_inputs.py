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

import asyncio
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
from app.services.weather_service import get_openweather_client, fetch_weather_snapshot
from app.services.yield_estimation import estimate_yield_kg

router = APIRouter(prefix="/farms/{farm_id}", tags=["Farm Inputs & Yield"])


def _get_owned_farm_or_raise(db: Session, farm_id: int, user_id: int) -> Farm:
    farm = db.execute(
        select(Farm).where(Farm.id == farm_id, Farm.owner_id == user_id)
    ).scalar_one_or_none()
    if farm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found or you don't have permission")
    return farm


def _to_yield_response(record: FarmYieldRecord, farm: Farm) -> FarmYieldRecordResponse:
    estimate = estimate_yield_kg(record.crop, farm.size_acres)
    return FarmYieldRecordResponse(
        id=record.id, farm_id=record.farm_id, crop=record.crop, season_label=record.season_label,
        planted_date=record.planted_date, expected_yield_kg=record.expected_yield_kg,
        actual_yield_kg=record.actual_yield_kg, harvest_date=record.harvest_date, notes=record.notes,
        created_at=record.created_at,
        estimated_yield_kg=estimate.estimated_yield_kg if estimate else None,
        estimate_source=estimate.source if estimate else None,
    )


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
    farm = _get_owned_farm_or_raise(db, farm_id, current_user["id"])
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
    return _to_yield_response(record, farm)


@router.get("/yields", response_model=FarmYieldListResponse)
async def list_yield_records(
    farm_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    farm = _get_owned_farm_or_raise(db, farm_id, current_user["id"])
    records = db.execute(
        select(FarmYieldRecord)
        .where(FarmYieldRecord.farm_id == farm_id, FarmYieldRecord.is_deleted == False)  # noqa: E712
        .order_by(FarmYieldRecord.planted_date.desc().nulls_last())
    ).scalars().all()
    return FarmYieldListResponse(items=[_to_yield_response(r, farm) for r in records])


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
    farm = _get_owned_farm_or_raise(db, farm_id, current_user["id"])
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
    return _to_yield_response(record, farm)


@router.get("/yields/{record_id}/tips", response_model=List[str])
async def get_yield_tips(
    farm_id: int,
    record_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    """Short, real, farmer-legible tips for this yield record - not
    generated from the yield estimate itself (that's just a reference-yield
    multiplication, it has no opinion). Two real sources, both already used
    elsewhere in this app:

    1. Current agricultural alerts (frost/heat/drought/flood/wind) from
       app.services.weather_service - the same ones GET /farms/{id}/weather
       already surfaces, just filtered to their recommendations.
    2. One rule over this farm's own input log: no fertilizer application
       logged since planting yet.

    No weather-season modelling, no ML - see app.services.yield_estimation
    for why that's deliberately out of scope for now.
    """
    farm = _get_owned_farm_or_raise(db, farm_id, current_user["id"])
    record = db.execute(
        select(FarmYieldRecord).where(FarmYieldRecord.id == record_id, FarmYieldRecord.farm_id == farm_id)
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Yield record not found")

    tips: List[str] = []

    client = get_openweather_client()
    if client is not None:
        weather = await fetch_weather_snapshot(client, farm.latitude, farm.longitude)
        if weather is not None:
            forecast = await asyncio.to_thread(client.get_5day_forecast, farm.latitude, farm.longitude)
            alerts = await asyncio.to_thread(client.get_agricultural_alerts, farm.latitude, farm.longitude, weather, forecast)
            for alert in alerts:
                if alert.recommendations:
                    tips.append(f"{alert.description} {alert.recommendations[0]}")

    since = record.planted_date
    if since is None and record.created_at is not None:
        since = record.created_at.date()
    fertilized = False
    if since is not None:
        fertilized = db.execute(
            select(FarmInputRecord.id).where(
                FarmInputRecord.farm_id == farm_id,
                FarmInputRecord.is_deleted == False,  # noqa: E712
                FarmInputRecord.category == "fertilizer",
                FarmInputRecord.entry_type == "application",
                FarmInputRecord.entry_date >= since,
            )
        ).first() is not None
    if not fertilized and record.crop.strip().lower() == "maize":
        tips.append("No fertilizer application logged yet this season - maize typically benefits from a nitrogen top-dress around 4-6 weeks after planting.")

    return tips
