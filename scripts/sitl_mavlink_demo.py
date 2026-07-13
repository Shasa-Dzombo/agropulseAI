"""
Drives the real MAVLinkFlightBackend (app/drones/flight/mavlink_backend.py)
against a running ArduPilot SITL instance - the same code path used by the
production drone API, just pointed at simulated hardware instead of a real
flight controller.

Usage:
    1. In one terminal, start SITL:
         python -m dronekit_sitl copter
       Wait for it to print a line like "Ready to fly" - it exposes a
       MAVLink endpoint (default: 127.0.0.1:5760, TCP).

    2. In another terminal, run this script:
         python scripts/sitl_mavlink_demo.py [connection_string]
       Defaults to tcp:127.0.0.1:5760 if no connection string is given.
"""

import asyncio
import sys

sys.path.insert(0, ".")

from app.drones.flight.backend import GPSCoordinate, Waypoint
from app.drones.flight.mavlink_backend import MAVLinkFlightBackend


async def main():
    connection_string = sys.argv[1] if len(sys.argv) > 1 else "tcp:127.0.0.1:5760"
    print(f"Connecting to SITL at {connection_string} ...")

    home = GPSCoordinate(latitude=-35.363261, longitude=149.165230, altitude=584.0)  # SITL's default start location (Canberra)
    backend = MAVLinkFlightBackend(drone_id="SITL-DRONE", home=home, connection_string=connection_string, telemetry_hz=1.0)

    await backend.connect()
    print("Heartbeat received - connected to flight controller.")

    waypoints = [
        Waypoint(gps=GPSCoordinate(home.latitude + 0.0003, home.longitude, 30.0), action="take_photo", waypoint_id=0, tree_id="t0"),
        Waypoint(gps=GPSCoordinate(home.latitude + 0.0006, home.longitude, 30.0), action="take_photo", waypoint_id=1, tree_id="t1"),
        Waypoint(gps=GPSCoordinate(home.latitude + 0.0006, home.longitude + 0.0003, 30.0), action="fly_through", waypoint_id=2),
    ]

    print(f"Uploading mission ({len(waypoints)} waypoints) ...")
    await backend.upload_mission(waypoints)
    print("Mission uploaded. Arming and taking off to 30m ...")

    await backend.arm_and_takeoff(30.0)

    async for sample in backend.stream_telemetry():
        print(
            f"  waypoint {sample.waypoint_index} reached | "
            f"lat={sample.latitude:.6f} lon={sample.longitude:.6f} alt={sample.altitude:.1f}m | "
            f"heading={sample.heading:.0f} deg | battery={sample.battery_pct:.0f}% | action={sample.action}"
        )

    print("Mission complete. Returning to launch ...")
    await backend.return_to_launch()
    await backend.land()
    await backend.disconnect()

    print(f"Done. is_mission_complete={backend.is_mission_complete()}")


if __name__ == "__main__":
    asyncio.run(main())
