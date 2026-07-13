"""
Backend selection for the drone survey pipeline. Real hardware is always an
explicit, per-mission opt-in (backend_type field) - never implicit - so tests
and CI never attempt to talk to a serial port or UDP endpoint.
"""

from typing import Literal, Optional

from app.drones.flight.backend import FlightBackend, GPSCoordinate
from app.drones.flight.camera import CameraBackend, SimulatedCameraBackend, RealCameraBackend

BackendType = Literal["simulated", "mavlink"]


def get_flight_backend(
    backend_type: BackendType,
    drone_id: str,
    home: GPSCoordinate,
    mavlink_connection_string: Optional[str] = None,
) -> FlightBackend:
    if backend_type == "mavlink":
        from app.drones.flight.mavlink_backend import MAVLinkFlightBackend
        if not mavlink_connection_string:
            raise ValueError("mavlink_connection_string is required for backend_type='mavlink'")
        return MAVLinkFlightBackend(drone_id, home, mavlink_connection_string)

    from app.drones.flight.simulated_backend import SimulatedFlightBackend
    return SimulatedFlightBackend(drone_id, home)


def get_camera_backend(backend_type: BackendType) -> CameraBackend:
    if backend_type == "mavlink":
        return RealCameraBackend()
    return SimulatedCameraBackend()
