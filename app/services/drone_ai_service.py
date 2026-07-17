"""
Drone AI Service - orchestrates a real drone survey mission end to end:
fly the mission (real MAVLink hardware or the simulated backend) -> capture
imagery at each photo waypoint -> run NDVI/vegetation-index analysis -> persist
flight, telemetry, imagery and analysis to Postgres.
"""

import math
from datetime import datetime
from typing import Callable, Dict, List, Optional

import cv2
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.drones.flight import _console  # noqa: F401 - must run before any drone_orchard_system import

from drone_orchard_system.multispectral_imaging import MultispectralImage, MultispectralProcessor

from app.drones.flight.backend import GPSCoordinate, Waypoint
from app.drones.flight.factory import get_camera_backend, get_flight_backend
from app.models.drone import (
    DroneBackendType,
    DroneFlight,
    DroneFlightStatus,
    DroneImage,
    DroneImageAnalysis,
    DroneTelemetryLog,
)
from app.models.user import Farm
from app.services.ai_service import aws_ai_service


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


class DroneAIService:
    def __init__(self, db: AsyncSession, image_uploader: Optional[Callable] = None):
        self.db = db
        self._upload = image_uploader or _default_image_uploader

    async def plan_mission(
        self,
        farm_id: int,
        user_id: int,
        drone_id: str,
        home_latitude: float,
        home_longitude: float,
        home_altitude: float,
        target_altitude_m: float,
        backend_type: str,
        waypoints: List[dict],
    ) -> DroneFlight:
        flight = DroneFlight(
            farm_id=farm_id,
            requested_by_id=user_id,
            drone_id=drone_id,
            backend_type=DroneBackendType(backend_type),
            status=DroneFlightStatus.PLANNED,
            home_latitude=home_latitude,
            home_longitude=home_longitude,
            home_altitude=home_altitude,
            target_altitude_m=target_altitude_m,
            mission_plan=waypoints,
        )
        self.db.add(flight)
        await self.db.commit()
        await self.db.refresh(flight)
        return flight

    async def execute_mission(self, flight_id: int, user_id: int, mavlink_connection_string: Optional[str] = None) -> DroneFlight:
        flight = await self._get_owned_flight_or_raise(flight_id, user_id)

        if flight.status != DroneFlightStatus.PLANNED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Flight {flight_id} is not in a runnable state (status={flight.status.value})",
            )

        flight.status = DroneFlightStatus.IN_PROGRESS
        flight.started_at = datetime.utcnow()
        await self.db.commit()

        home = GPSCoordinate(flight.home_latitude, flight.home_longitude, flight.home_altitude)
        waypoints = [
            Waypoint(
                gps=GPSCoordinate(wp["latitude"], wp["longitude"], wp["altitude"]),
                action=wp.get("action", "fly_through"),
                hover_time=wp.get("hover_time", 0.0),
                speed=wp.get("speed", 10.0),
                gimbal_pitch=wp.get("gimbal_pitch", -90.0),
                photo_interval=wp.get("photo_interval", 0.0),
                waypoint_id=i,
                tree_id=wp.get("tree_id"),
            )
            for i, wp in enumerate(flight.mission_plan)
        ]

        backend_type = flight.backend_type.value
        backend = get_flight_backend(backend_type, flight.drone_id, home, mavlink_connection_string)
        local_image_dir = settings.DRONE_CAMERA_SOURCE_DIR if settings.DRONE_CAMERA_SOURCE == "local_files" else None
        camera = get_camera_backend(backend_type, local_image_dir=local_image_dir)
        processor = MultispectralProcessor()

        try:
            await backend.connect()
            await backend.upload_mission(waypoints)
            flight.battery_start_pct = getattr(backend, "battery_percentage", None)

            await backend.arm_and_takeoff(flight.target_altitude_m)

            async for sample in backend.stream_telemetry():
                self.db.add(DroneTelemetryLog(
                    flight_id=flight.id,
                    waypoint_index=sample.waypoint_index,
                    latitude=sample.latitude,
                    longitude=sample.longitude,
                    altitude=sample.altitude,
                    heading=sample.heading,
                    ground_speed=sample.ground_speed,
                    battery_pct=sample.battery_pct,
                    battery_voltage=sample.battery_voltage,
                    flight_mode=sample.flight_mode,
                ))

                if sample.action == "take_photo":
                    await self._capture_and_analyze(
                        camera, processor, waypoints[sample.waypoint_index], sample, flight.id
                    )

            await backend.return_to_launch()
            await backend.land()
            flight.battery_end_pct = getattr(backend, "battery_percentage", None)

            flight.status = DroneFlightStatus.COMPLETED
            flight.completed_at = datetime.utcnow()
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            flight.status = DroneFlightStatus.FAILED
            flight.error_message = str(e)
            flight.completed_at = datetime.utcnow()
            await self.db.commit()
            raise
        finally:
            await backend.disconnect()

        await self.db.refresh(flight)
        return flight

    async def _capture_and_analyze(self, camera, processor: MultispectralProcessor, waypoint: Waypoint, sample, flight_id: int) -> None:
        image = await camera.capture(waypoint, sample.altitude)

        rgb_url, nir_url = await self._upload_image_bands(image, flight_id, sample.waypoint_index)

        drone_image = DroneImage(
            flight_id=flight_id,
            waypoint_index=sample.waypoint_index,
            tree_id=waypoint.tree_id,
            rgb_url=rgb_url,
            nir_url=nir_url,
            latitude=sample.latitude,
            longitude=sample.longitude,
            altitude=sample.altitude,
            ground_sampling_distance_cm=image.ground_sampling_distance,
        )
        self.db.add(drone_image)
        await self.db.flush()

        indices = processor.process_multispectral_image(image)
        ndvi = _safe_float(indices.ndvi)
        self.db.add(DroneImageAnalysis(
            image_id=drone_image.id,
            ndvi=ndvi,
            gndvi=_safe_float(indices.gndvi),
            ndre=_safe_float(indices.ndre),
            savi=_safe_float(indices.savi),
            evi=_safe_float(indices.evi),
            health_status=indices.get_health_status().value if ndvi is not None else None,
        ))

    async def _upload_image_bands(self, image: MultispectralImage, flight_id: int, waypoint_index: int) -> tuple:
        folder = f"drone-imagery/{flight_id}"
        _, rgb_buf = cv2.imencode(".jpg", image.rgb)
        _, nir_buf = cv2.imencode(".jpg", image.nir)
        rgb_url = await self._upload(rgb_buf.tobytes(), f"{waypoint_index}_rgb.jpg", folder)
        nir_url = await self._upload(nir_buf.tobytes(), f"{waypoint_index}_nir.jpg", folder)
        return rgb_url, nir_url

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

        return {
            "flight_id": flight_id,
            "image_count": len(analyses),
            "mean_ndvi": sum(ndvis) / len(ndvis) if ndvis else None,
            "min_ndvi": min(ndvis) if ndvis else None,
            "max_ndvi": max(ndvis) if ndvis else None,
            "health_status_histogram": histogram,
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
