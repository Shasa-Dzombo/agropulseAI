# Mobile Unit Manager
# Dispatches and manages autonomous units like drones.

import logging
import asyncio
from .mavlink_client import MAVLinkClient

logger = logging.getLogger(__name__)

class MobileUnitManager:
    def __init__(self, config, db_manager, alert_manager):
        self.config = config.get('mobile_units', {})
        self.db_manager = db_manager
        self.alert_manager = alert_manager
        self.is_enabled = self.config.get('enabled', False)
        self.units = {}
        logger.info(f"Mobile Unit Manager initialized. Enabled: {self.is_enabled}")

    async def start(self):
        if not self.is_enabled: return
        for unit_id, unit_config in self.config.get('units', {}).items():
            if unit_config['type'] == 'drone':
                self.units[unit_id] = MAVLinkClient(unit_id, unit_config)
                asyncio.create_task(self.units[unit_id].connect())

    async def dispatch_unit_to_incident(self, unit_id, incident):
        """Dispatches a unit to the location of an incident."""
        if not self.is_enabled or unit_id not in self.units:
            logger.warning(f"Cannot dispatch unit {unit_id}. Not available or manager disabled.")
            return False
        
        unit = self.units[unit_id]
        # Get GPS coordinates for the incident (e.g., from camera's metadata)
        gps_coords = await self.db_manager.get_camera_gps(incident.camera_id)
        if not gps_coords:
            logger.error(f"Cannot dispatch drone for incident {incident.id}, no GPS data for camera.")
            return False

        logger.info(f"Dispatching unit '{unit_id}' to {gps_coords}.")
        success = await unit.fly_to(gps_coords['lat'], gps_coords['lon'], 50) # 50m altitude
        if success:
            await self.alert_manager.send_alert("MobileUnitManager", f"Drone {unit_id} dispatched to incident.")
        return success
