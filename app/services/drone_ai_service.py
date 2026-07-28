"""
Drone AI Service - manual DJI ground-ingestion pipeline: images captured on a
manually-flown mission (DJI's own app over the RC, entirely outside this
system) are pushed in via ingest_captured_image() -> real NDVI/vegetation-index
and canopy-vigor analysis runs on each photo -> flight, imagery and analysis
persist to Postgres.

A manual flight can optionally carry a mission_plan (e.g. parsed from a KML
file via app.services.kml_mission_parser) purely as a reference/briefing aid:
each incoming photo's real GPS reading is matched to the nearest planned
waypoint to auto-fill tree_id when the caller doesn't supply one. Nothing
here drives a physical aircraft - the simulated and real MAVLink flight
backends that used to live under app/drones/flight/ were removed, since this
project's actual hardware is flown manually and neither backend was ever
reachable from it.
"""

import logging
import math
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional

import cv2
import numpy as np
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.drones.flight import _console  # noqa: F401 - must run before any drone_orchard_system import

from drone_orchard_system.multispectral_imaging import MultispectralImage, MultispectralProcessor

from app.drones.flight.backend import GPSCoordinate
from app.drones.flight.camera import green_channel_as_nir_placeholder
from app.models.drone import (
    DroneBackendType,
    DroneFlight,
    DroneFlightStatus,
    DroneImage,
    DroneImageAnalysis,
)
from app.models.user import Farm
from app.services.ai_service import aws_ai_service
from app.services._kindwise_client_loader import CropType, KindwiseAPIClient
from app.services.canopy_vigor_assessment import assess_canopy_vigor
from app.services.exif_gps import extract_gps_from_image_bytes
from app.services.kindwise_crop_mapping import map_farm_crop_type_to_kindwise
from app.services.kindwise_disease_service import get_kindwise_client, run_disease_detection
from app.services.plant_stress_assessment import assess_plant_stress
from app.services.weather_service import (
    assess_disease_pressure,
    assess_flight_conditions,
    fetch_weather_snapshot,
    get_openweather_client,
)

logger = logging.getLogger(__name__)


def _safe_float(value: float) -> Optional[float]:
    """NDVI/etc. can be NaN when process_multispectral_image() finds no
    positive-index pixels (it excludes them from the mean) - store as
    None/null rather than an invalid, unserializable NaN."""
    try:
        return None if math.isnan(value) else float(value)
    except TypeError:
        return None


async def _default_image_uploader(content: bytes, file_name: str, folder: str) -> str:
    return await aws_ai_service.upload_to_s3(content, file_name, folder=folder)


def _nearest_waypoint_tree_id(mission_plan: List[dict], latitude: float, longitude: float) -> Optional[str]:
    """Matches a real GPS reading to the closest reference waypoint in a
    manual flight's mission_plan (typically KML-derived - see
    app.services.kml_mission_parser), so a manually-flown photo gets the same
    tree_id a planned mission would have assigned. Returns None if the plan
    is empty or none of its waypoints carry a tree_id."""
    candidates = [wp for wp in mission_plan if wp.get("tree_id")]
    if not candidates:
        return None

    photo_point = GPSCoordinate(latitude, longitude, 0.0)
    nearest = min(
        candidates,
        key=lambda wp: photo_point.distance_to(GPSCoordinate(wp["latitude"], wp["longitude"], 0.0)),
    )
    return nearest["tree_id"]


class DroneAIService:
    def __init__(self, db: AsyncSession, image_uploader: Optional[Callable] = None):
        self.db = db
        self._upload = image_uploader or _default_image_uploader

    async def _apply_weather_context(self, flight: DroneFlight) -> None:
        """Real OpenWeatherMap conditions at the flight's home coordinates -
        advisory only (app.services.weather_service). Never raises and never
        blocks the mission: any failure here just leaves the weather_* columns
        None, same as a missing OPENWEATHER_API_KEY."""
        try:
            client = get_openweather_client()
            if client is None:
                return

            weather = await fetch_weather_snapshot(client, flight.home_latitude, flight.home_longitude)
            if weather is None:
                return

            conditions = assess_flight_conditions(weather)
            disease_pressure = assess_disease_pressure(weather)

            flight.weather_temperature_c = weather.temperature
            flight.weather_humidity_pct = weather.humidity
            flight.weather_wind_speed_ms = weather.wind_speed
            flight.weather_conditions = weather.description
            flight.weather_flight_suitable = conditions.suitable
            flight.weather_warnings = conditions.warnings
            flight.weather_disease_pressure = disease_pressure.risk_level
            flight.weather_checked_at = datetime.utcnow()
            await self.db.commit()
        except Exception:
            logger.exception("Weather context lookup failed for flight %s - proceeding without it", flight.id)
            await self.db.rollback()

    async def _process_and_persist_image(
        self, image: MultispectralImage, processor: MultispectralProcessor,
        flight_id: int, waypoint_index: int, tree_id: Optional[str],
        latitude: float, longitude: float, altitude: float,
        ground_sampling_distance_cm: Optional[float],
        rgb_url: Optional[str], nir_url: Optional[str],
        farmer_id: Optional[int] = None,
        run_disease_detection_for_mission: bool = False,
        kindwise_client: Optional[KindwiseAPIClient] = None,
        kindwise_crop_type: Optional[CropType] = None,
    ) -> DroneImage:
        """Called from the manual DJI-ingestion upload path
        (ingest_captured_image below) - the one real NDVI/stress/vigor/
        Kindwise pipeline every captured photo goes through."""
        drone_image = DroneImage(
            flight_id=flight_id,
            waypoint_index=waypoint_index,
            tree_id=tree_id,
            rgb_url=rgb_url,
            nir_url=nir_url,
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            ground_sampling_distance_cm=ground_sampling_distance_cm,
        )
        self.db.add(drone_image)
        await self.db.flush()

        indices = processor.process_multispectral_image(image)
        ndvi = _safe_float(indices.ndvi)
        stress = assess_plant_stress(indices)
        vigor = assess_canopy_vigor(image.rgb)
        self.db.add(DroneImageAnalysis(
            image_id=drone_image.id,
            ndvi=ndvi,
            gndvi=_safe_float(indices.gndvi),
            ndre=_safe_float(indices.ndre),
            savi=_safe_float(indices.savi),
            evi=_safe_float(indices.evi),
            health_status=indices.get_health_status().value if ndvi is not None else None,
            stress_level=stress.stress_level,
            stress_indicators=stress.stress_indicators,
            canopy_coverage_pct=vigor.coverage_pct,
            vigor_level=vigor.vigor_level,
            vigor_indicators=vigor.vigor_indicators,
            low_vigor_regions=vigor.low_vigor_regions,
        ))

        if run_disease_detection_for_mission:
            drone_image.diagnosis_id = await run_disease_detection(
                self.db, kindwise_client, kindwise_crop_type, image.rgb, rgb_url,
                farmer_id, latitude, longitude,
            )

        return drone_image

    async def start_manual_flight(
        self, farm_id: int, user_id: int, drone_id: str,
        home_latitude: float, home_longitude: float, home_altitude: float = 0.0,
        mission_plan: Optional[List[dict]] = None,
    ) -> DroneFlight:
        """The aircraft is flown manually (e.g. DJI's own app over the RC)
        entirely outside this system - images get pushed in afterward or live
        via ingest_captured_image(), typically from
        scripts/watch_and_upload_dji_images.py. Ownership of farm_id is
        checked by the caller (app/api/drones.py).

        mission_plan, when given (e.g. from app.services.kml_mission_parser),
        is a reference/briefing waypoint list only - nothing here flies it.
        Its per-waypoint tree_id values (if any) are used by
        ingest_captured_image() to auto-tag incoming photos by nearest
        real-GPS match."""
        flight = DroneFlight(
            farm_id=farm_id,
            requested_by_id=user_id,
            drone_id=drone_id,
            backend_type=DroneBackendType.MANUAL_INGEST,
            status=DroneFlightStatus.IN_PROGRESS,
            home_latitude=home_latitude,
            home_longitude=home_longitude,
            home_altitude=home_altitude,
            mission_plan=mission_plan,
            started_at=datetime.utcnow(),
        )
        self.db.add(flight)
        await self.db.commit()
        await self.db.refresh(flight)

        await self._apply_weather_context(flight)
        return flight

    async def ingest_captured_image(
        self, flight_id: int, user_id: int,
        rgb_bytes: bytes, nir_bytes: Optional[bytes], red_edge_bytes: Optional[bytes],
        tree_id: Optional[str] = None,
    ) -> DroneImage:
        """v1 uses DJI's companion consumer RGB JPG directly as rgb (no
        Blue/Green/Red band-stacking - that needs Addendum 3's real
        calibration first) and the raw, uncalibrated NIR/RedEdge band files
        directly when supplied - real signal, not yet radiometrically
        calibrated. Falls back to green_channel_as_nir_placeholder when no
        real NIR file is given, same honest degraded path LocalFileCameraBackend
        already uses."""
        flight = await self._get_owned_flight_or_raise(flight_id, user_id)
        if flight.backend_type != DroneBackendType.MANUAL_INGEST:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This flight is not a manual-ingest flight")
        if flight.status != DroneFlightStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Flight {flight_id} is not in progress (status={flight.status.value})",
            )

        rgb = cv2.imdecode(np.frombuffer(rgb_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if rgb is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not decode rgb image")

        if nir_bytes:
            nir = cv2.imdecode(np.frombuffer(nir_bytes, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
            if nir is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not decode nir image")
        else:
            nir = green_channel_as_nir_placeholder(rgb)

        red_edge = None
        if red_edge_bytes:
            red_edge = cv2.imdecode(np.frombuffer(red_edge_bytes, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
            if red_edge is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not decode red_edge image")

        gps = extract_gps_from_image_bytes(rgb_bytes)
        latitude = gps.latitude if gps else flight.home_latitude
        longitude = gps.longitude if gps else flight.home_longitude
        altitude = gps.altitude if gps and gps.altitude is not None else flight.home_altitude

        # Auto-tag by nearest reference waypoint only when we have a real
        # per-photo GPS reading (not the flight's home-coordinate fallback,
        # which would make every untagged photo "match" whichever waypoint
        # happens to be closest to home) and the caller didn't already say
        # which tree/plot this is.
        if tree_id is None and gps is not None and flight.mission_plan:
            tree_id = _nearest_waypoint_tree_id(flight.mission_plan, latitude, longitude)

        image = MultispectralImage(
            rgb=rgb,
            nir=nir,
            red_edge=red_edge,
            timestamp=time.time(),
            gps_latitude=latitude,
            gps_longitude=longitude,
            altitude=altitude,
            gimbal_pitch=-90.0,
            ground_sampling_distance=0.0,
        )

        count_result = await self.db.execute(
            select(func.count()).select_from(DroneImage).where(DroneImage.flight_id == flight_id)
        )
        waypoint_index = count_result.scalar_one()

        folder = f"drone-imagery/{flight_id}"
        _, rgb_buf = cv2.imencode(".jpg", rgb)
        rgb_url = await self._upload(rgb_buf.tobytes(), f"{waypoint_index}_rgb.jpg", folder)
        nir_url = None
        if nir_bytes:
            _, nir_buf = cv2.imencode(".jpg", nir)
            nir_url = await self._upload(nir_buf.tobytes(), f"{waypoint_index}_nir.jpg", folder)

        processor = MultispectralProcessor()
        drone_image = await self._process_and_persist_image(
            image, processor, flight_id, waypoint_index, tree_id,
            latitude, longitude, altitude, None, rgb_url, nir_url,
        )
        await self.db.commit()
        await self.db.refresh(drone_image)
        return drone_image

    async def complete_manual_flight(
        self, flight_id: int, user_id: int, status_value: str,
        error_message: Optional[str] = None, battery_end_pct: Optional[float] = None,
    ) -> DroneFlight:
        flight = await self._get_owned_flight_or_raise(flight_id, user_id)
        if flight.backend_type != DroneBackendType.MANUAL_INGEST:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This flight is not a manual-ingest flight")
        if flight.status != DroneFlightStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Flight {flight_id} is not in progress (status={flight.status.value})",
            )

        flight.status = DroneFlightStatus.COMPLETED if status_value == "completed" else DroneFlightStatus.ABORTED
        flight.completed_at = datetime.utcnow()
        flight.error_message = error_message
        flight.battery_end_pct = battery_end_pct
        await self.db.commit()
        await self.db.refresh(flight)
        return flight

    async def get_flight(self, flight_id: int, user_id: int) -> DroneFlight:
        return await self._get_owned_flight_or_raise(flight_id, user_id)

    async def list_flights(self, farm_id: int, user_id: int) -> List[DroneFlight]:
        result = await self.db.execute(
            select(Farm).where(Farm.id == farm_id, Farm.owner_id == user_id)
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found or you don't have permission")

        result = await self.db.execute(
            select(DroneFlight).where(DroneFlight.farm_id == farm_id).order_by(DroneFlight.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_flight_images(self, flight_id: int, user_id: int) -> List[DroneImage]:
        await self._get_owned_flight_or_raise(flight_id, user_id)
        result = await self.db.execute(
            select(DroneImage).where(DroneImage.flight_id == flight_id).order_by(DroneImage.waypoint_index)
        )
        return list(result.scalars().all())

    async def get_flight_analysis_summary(self, flight_id: int, user_id: int) -> Dict:
        await self._get_owned_flight_or_raise(flight_id, user_id)

        result = await self.db.execute(
            select(DroneImageAnalysis).join(DroneImage, DroneImage.id == DroneImageAnalysis.image_id)
            .where(DroneImage.flight_id == flight_id)
        )
        analyses = list(result.scalars().all())

        ndvis = [a.ndvi for a in analyses if a.ndvi is not None]
        histogram: Dict[str, int] = {}
        for a in analyses:
            if a.health_status:
                histogram[a.health_status] = histogram.get(a.health_status, 0) + 1

        coverages = [a.canopy_coverage_pct for a in analyses if a.canopy_coverage_pct is not None]
        vigor_histogram: Dict[str, int] = {}
        for a in analyses:
            if a.vigor_level:
                vigor_histogram[a.vigor_level] = vigor_histogram.get(a.vigor_level, 0) + 1

        return {
            "flight_id": flight_id,
            "image_count": len(analyses),
            "mean_ndvi": sum(ndvis) / len(ndvis) if ndvis else None,
            "min_ndvi": min(ndvis) if ndvis else None,
            "max_ndvi": max(ndvis) if ndvis else None,
            "health_status_histogram": histogram,
            "mean_canopy_coverage_pct": sum(coverages) / len(coverages) if coverages else None,
            "min_canopy_coverage_pct": min(coverages) if coverages else None,
            "max_canopy_coverage_pct": max(coverages) if coverages else None,
            "vigor_level_histogram": vigor_histogram,
        }

    async def _get_owned_flight_or_raise(self, flight_id: int, user_id: int) -> DroneFlight:
        result = await self.db.execute(
            select(DroneFlight).join(Farm, Farm.id == DroneFlight.farm_id)
            .where(DroneFlight.id == flight_id, Farm.owner_id == user_id)
        )
        flight = result.scalar_one_or_none()
        if flight is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flight not found or you don't have permission")
        return flight
