"""
Shared flight-control interface for the drone orchard survey pipeline.

Two backends implement this interface: a simulated one (wraps
drone_orchard_system.flight_controller.DroneFlightController, used for tests
and CI) and a real one (talks to actual flight-controller hardware over
MAVLink). Callers depend only on this interface, never on a specific backend.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, List

from app.drones.flight import _console  # noqa: F401 - must run before any drone_orchard_system import

from drone_orchard_system.flight_controller import GPSCoordinate, Waypoint, BatteryStatus

__all__ = [
    "GPSCoordinate",
    "Waypoint",
    "BatteryStatus",
    "TelemetrySample",
    "FlightBackend",
]


@dataclass
class TelemetrySample:
    """One telemetry reading, captured after reaching a waypoint."""
    waypoint_index: int
    latitude: float
    longitude: float
    altitude: float
    heading: float
    ground_speed: float
    battery_pct: float
    battery_voltage: float
    flight_mode: str
    action: str


class FlightBackend(ABC):
    """Strategy interface for driving a mission, real or simulated."""

    @abstractmethod
    async def connect(self) -> None:
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        ...

    @abstractmethod
    async def upload_mission(self, waypoints: List[Waypoint]) -> None:
        ...

    @abstractmethod
    async def arm_and_takeoff(self, target_altitude_m: float) -> None:
        ...

    @abstractmethod
    def stream_telemetry(self) -> AsyncIterator[TelemetrySample]:
        """Fly the uploaded mission, yielding one TelemetrySample per waypoint reached."""
        ...

    @abstractmethod
    async def return_to_launch(self) -> None:
        ...

    @abstractmethod
    async def land(self) -> None:
        ...

    @abstractmethod
    def is_mission_complete(self) -> bool:
        ...
