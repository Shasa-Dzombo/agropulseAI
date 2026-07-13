"""
Simulated flight backend - wraps drone_orchard_system.flight_controller's
DroneFlightController rather than reimplementing flight simulation. Used for
tests and CI, and as the default when no real hardware is configured.
"""

import asyncio
from datetime import datetime
from typing import AsyncIterator, List, Optional

from app.drones.flight import _console  # noqa: F401 - must run before any drone_orchard_system import

from drone_orchard_system.flight_controller import (
    DroneFlightController,
    DroneStatus,
    FlightPlan,
)

from app.drones.flight.backend import FlightBackend, GPSCoordinate, TelemetrySample, Waypoint


class SimulatedFlightBackend(FlightBackend):
    def __init__(self, drone_id: str, home: GPSCoordinate):
        self._controller = DroneFlightController(drone_id, home)
        self._waypoints: List[Waypoint] = []

    async def connect(self) -> None:
        return None  # nothing to connect to in simulation

    async def disconnect(self) -> None:
        return None

    async def upload_mission(self, waypoints: List[Waypoint]) -> None:
        self._waypoints = waypoints
        total_distance = 0.0
        previous = self._controller.home_location
        for wp in waypoints:
            total_distance += previous.distance_to(wp.gps)
            previous = wp.gps

        plan = FlightPlan(
            plan_id=f"{self._controller.drone_id}-mission",
            home_location=self._controller.home_location,
            waypoints=waypoints,
            orchard_rows=[],
            total_distance=total_distance,
            estimated_flight_time=max(len(waypoints) * 0.5, 1.0),
            battery_required=min(5.0 * max(len(waypoints), 1), 60.0),
            coverage_area=0.0,
            survey_date=datetime.utcnow(),
            weather_conditions={},
        )
        loaded = await asyncio.to_thread(self._controller.load_flight_plan, plan)
        if not loaded:
            raise RuntimeError("Simulated flight controller rejected the mission plan")

    async def arm_and_takeoff(self, target_altitude_m: float) -> None:
        ok = await asyncio.to_thread(self._controller.takeoff, target_altitude_m)
        if not ok:
            raise RuntimeError("Simulated takeoff failed")

    async def stream_telemetry(self) -> AsyncIterator[TelemetrySample]:
        self._controller.drone_status = DroneStatus.SURVEYING
        for i, waypoint in enumerate(self._waypoints):
            ok = await asyncio.to_thread(self._controller.navigate_to_waypoint, waypoint)
            if not ok:
                raise RuntimeError(f"Simulated navigation to waypoint {i} failed")

            telemetry = self._controller.get_telemetry()
            yield TelemetrySample(
                waypoint_index=i,
                latitude=telemetry["position"]["latitude"],
                longitude=telemetry["position"]["longitude"],
                altitude=telemetry["position"]["altitude"],
                heading=telemetry["heading"],
                ground_speed=waypoint.speed,
                battery_pct=telemetry["battery"]["percentage"],
                battery_voltage=telemetry["battery"]["voltage"],
                flight_mode=telemetry["flight_mode"],
                action=waypoint.action,
            )
            if waypoint.tree_id:
                self._controller.trees_surveyed += 1

    async def return_to_launch(self) -> None:
        ok = await asyncio.to_thread(self._controller.return_to_home)
        if not ok:
            raise RuntimeError("Simulated return-to-home failed")

    async def land(self) -> None:
        # return_to_home() already lands as part of RTH; only land explicitly
        # if the drone somehow isn't grounded yet (mirrors the real backend's
        # explicit land step).
        if self._controller.drone_status != DroneStatus.GROUNDED:
            ok = await asyncio.to_thread(self._controller.land)
            if not ok:
                raise RuntimeError("Simulated landing failed")

    def is_mission_complete(self) -> bool:
        return self._controller.drone_status == DroneStatus.GROUNDED

    @property
    def battery_percentage(self) -> float:
        return self._controller.battery.percentage
