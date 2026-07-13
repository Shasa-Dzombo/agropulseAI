"""
Drives the simulated flight backend directly (no DB, no API) and asserts on
real outcomes - unlike drone_orchard_system/test_drones.py, which has zero
assert statements and just prints hardcoded numbers.
"""

from app.drones.flight.backend import GPSCoordinate, Waypoint
from app.drones.flight.simulated_backend import SimulatedFlightBackend


def _waypoints():
    return [
        Waypoint(gps=GPSCoordinate(37.7751, -122.4194, 30.0), action="take_photo", waypoint_id=0, tree_id="t0"),
        Waypoint(gps=GPSCoordinate(37.7752, -122.4194, 30.0), action="take_photo", waypoint_id=1, tree_id="t1"),
        Waypoint(gps=GPSCoordinate(37.7753, -122.4194, 30.0), action="fly_through", waypoint_id=2),
    ]


async def test_mission_completes_and_lands():
    home = GPSCoordinate(37.77, -122.4, 100.0)
    backend = SimulatedFlightBackend("TEST-DRONE", home)
    waypoints = _waypoints()

    await backend.connect()
    await backend.upload_mission(waypoints)
    assert not backend.is_mission_complete()

    await backend.arm_and_takeoff(30.0)

    samples = [sample async for sample in backend.stream_telemetry()]
    assert len(samples) == len(waypoints)

    await backend.return_to_launch()
    await backend.land()
    await backend.disconnect()

    assert backend.is_mission_complete()


async def test_battery_strictly_decreases_across_waypoints():
    home = GPSCoordinate(37.77, -122.4, 100.0)
    backend = SimulatedFlightBackend("TEST-DRONE", home)
    waypoints = _waypoints()

    await backend.connect()
    await backend.upload_mission(waypoints)
    await backend.arm_and_takeoff(30.0)

    battery_readings = [sample.battery_pct async for sample in backend.stream_telemetry()]

    assert len(battery_readings) == len(waypoints)
    for earlier, later in zip(battery_readings, battery_readings[1:]):
        assert later <= earlier


async def test_telemetry_sample_has_one_entry_per_waypoint_with_correct_actions():
    home = GPSCoordinate(37.77, -122.4, 100.0)
    backend = SimulatedFlightBackend("TEST-DRONE", home)
    waypoints = _waypoints()

    await backend.connect()
    await backend.upload_mission(waypoints)
    await backend.arm_and_takeoff(30.0)

    samples = [sample async for sample in backend.stream_telemetry()]

    assert [s.waypoint_index for s in samples] == [0, 1, 2]
    assert [s.action for s in samples] == ["take_photo", "take_photo", "fly_through"]
