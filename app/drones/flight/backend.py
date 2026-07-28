"""
Shared flight-geometry types for the drone survey pipeline: GPS coordinates
and waypoints, re-exported from drone_orchard_system.flight_controller.

There is no FlightBackend abstraction anymore - autonomous mission flying
(both the simulated backend and the real MAVLink/ArduPilot/PX4 backend) was
removed, since this project's actual hardware is flown manually (DJI's own
app over the RC), never through this system. These types now exist only for:
app/drones/flight/camera.py's CameraBackend.capture() signature (still used
by tests), and the manual-ingest nearest-waypoint matching in
app/services/drone_ai_service.py (GPSCoordinate.distance_to against an
optional, KML-derived mission_plan - see app/services/kml_mission_parser.py).
"""

from app.drones.flight import _console  # noqa: F401 - must run before any drone_orchard_system import

from drone_orchard_system.flight_controller import GPSCoordinate, Waypoint, BatteryStatus

__all__ = [
    "GPSCoordinate",
    "Waypoint",
    "BatteryStatus",
]
