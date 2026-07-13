"""
Real flight backend - talks to actual flight-controller hardware over MAVLink
(ArduPilot/PX4) via pymavlink. Requires the `pymavlink` package and a real,
reachable flight controller; never used by tests (see simulated_backend.py).
"""

import asyncio
from typing import AsyncIterator, List, Optional

try:
    from pymavlink import mavutil, mavwp
except ImportError:
    mavutil = None
    mavwp = None

from app.drones.flight.backend import FlightBackend, GPSCoordinate, TelemetrySample, Waypoint


class MAVLinkFlightBackend(FlightBackend):
    def __init__(
        self,
        drone_id: str,
        home: GPSCoordinate,
        connection_string: str,
        telemetry_hz: float = 1.0,
        heartbeat_timeout_s: float = 30.0,
    ):
        if mavutil is None:
            raise RuntimeError(
                "pymavlink is not installed. Install it to use the real MAVLink "
                "flight backend (the simulated backend does not require it)."
            )
        self.drone_id = drone_id
        self.home = home
        self.connection_string = connection_string
        self.heartbeat_timeout_s = heartbeat_timeout_s
        self._telemetry_interval = 1.0 / telemetry_hz if telemetry_hz > 0 else 0.0
        self._master = None
        self._waypoints: List[Waypoint] = []
        self._mission_complete = False

    async def connect(self) -> None:
        self._master = await asyncio.to_thread(mavutil.mavlink_connection, self.connection_string)
        await asyncio.to_thread(self._master.wait_heartbeat, timeout=self.heartbeat_timeout_s)

    async def disconnect(self) -> None:
        if self._master is not None:
            await asyncio.to_thread(self._master.close)
            self._master = None

    async def upload_mission(self, waypoints: List[Waypoint]) -> None:
        self._waypoints = waypoints

        def _upload():
            mav = self._master.mav
            mavlink = self._master.mavlink

            loader = mavwp.MAVWPLoader()
            for i, wp in enumerate(waypoints):
                loader.add(
                    mavlink.MAVLink_mission_item_message(
                        self._master.target_system,
                        self._master.target_component,
                        i,
                        mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                        mavlink.MAV_CMD_NAV_WAYPOINT,
                        0, 1,
                        0, 0, 0, 0,
                        wp.gps.latitude, wp.gps.longitude, wp.gps.altitude,
                    )
                )

            self._master.waypoint_clear_all_send()
            self._master.waypoint_count_send(loader.count())
            for _ in range(loader.count()):
                msg = self._master.recv_match(type=["MISSION_REQUEST"], blocking=True, timeout=10)
                if msg is None:
                    raise RuntimeError("Timed out waiting for MISSION_REQUEST from flight controller")
                mav.send(loader.wp(msg.seq))

        await asyncio.to_thread(_upload)

    async def arm_and_takeoff(self, target_altitude_m: float) -> None:
        def _arm_and_takeoff():
            mavlink = self._master.mavlink
            self._master.mav.command_long_send(
                self._master.target_system, self._master.target_component,
                mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, 0, 0, 0, 0, 0, 0,
            )
            self._master.motors_armed_wait()
            self._master.mav.command_long_send(
                self._master.target_system, self._master.target_component,
                mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, 0, 0, 0, 0, target_altitude_m,
            )

        await asyncio.to_thread(_arm_and_takeoff)

    def _read_next_position_and_status(self) -> tuple:
        pos_msg = self._master.recv_match(type="GLOBAL_POSITION_INT", blocking=True, timeout=10)
        sys_msg = self._master.recv_match(type="SYS_STATUS", blocking=True, timeout=10)
        pos = pos_msg.to_dict() if pos_msg else {}
        sys_status = sys_msg.to_dict() if sys_msg else {}
        return pos, sys_status

    def _wait_for_waypoint_reached(self, index: int) -> None:
        while True:
            msg = self._master.recv_match(type=["MISSION_ITEM_REACHED"], blocking=True, timeout=60)
            if msg is None:
                raise RuntimeError(f"Timed out waiting for waypoint {index} to be reached")
            if msg.seq == index:
                return

    async def stream_telemetry(self) -> AsyncIterator[TelemetrySample]:
        for i, waypoint in enumerate(self._waypoints):
            await asyncio.to_thread(self._wait_for_waypoint_reached, i)
            pos, sys_status = await asyncio.to_thread(self._read_next_position_and_status)

            yield TelemetrySample(
                waypoint_index=i,
                latitude=pos.get("lat", 0) / 1e7,
                longitude=pos.get("lon", 0) / 1e7,
                altitude=pos.get("relative_alt", 0) / 1000.0,
                heading=pos.get("hdg", 0) / 100.0,
                ground_speed=((pos.get("vx", 0) ** 2 + pos.get("vy", 0) ** 2) ** 0.5) / 100.0,
                battery_pct=float(sys_status.get("battery_remaining", -1)),
                battery_voltage=sys_status.get("voltage_battery", 0) / 1000.0,
                flight_mode="auto",
                action=waypoint.action,
            )
            if self._telemetry_interval:
                await asyncio.sleep(self._telemetry_interval)

        self._mission_complete = True

    async def return_to_launch(self) -> None:
        def _rtl():
            mavlink = self._master.mavlink
            self._master.mav.command_long_send(
                self._master.target_system, self._master.target_component,
                mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH, 0, 0, 0, 0, 0, 0, 0, 0,
            )

        await asyncio.to_thread(_rtl)

    async def land(self) -> None:
        def _land():
            mavlink = self._master.mavlink
            self._master.mav.command_long_send(
                self._master.target_system, self._master.target_component,
                mavlink.MAV_CMD_NAV_LAND, 0, 0, 0, 0, 0, 0, 0, 0,
            )

        await asyncio.to_thread(_land)

    def is_mission_complete(self) -> bool:
        return self._mission_complete

#Connection func()