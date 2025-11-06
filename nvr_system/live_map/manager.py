# Live Map Manager
# Manages map configurations and camera placements.

import logging

logger = logging.getLogger(__name__)

class LiveMapManager:
    def __init__(self, config, db_manager):
        self.config = config.get('live_map', {})
        self.db_manager = db_manager
        self.is_enabled = self.config.get('enabled', False)
        logger.info(f"Live Map Manager initialized. Enabled: {self.is_enabled}")

    async def get_maps(self):
        """Retrieves all configured maps."""
        if not self.is_enabled: return []
        return await self.db_manager.get_maps()

    async def get_map_details(self, map_id):
        """Retrieves map details including camera placements."""
        if not self.is_enabled: return None
        map_data = await self.db_manager.get_map_by_id(map_id)
        if map_data:
            map_data['cameras'] = await self.db_manager.get_camera_placements_for_map(map_id)
        return map_data

    async def save_map(self, name, image_path):
        """Saves a new map configuration."""
        return await self.db_manager.save_map(name, image_path)

    async def save_camera_placement(self, map_id, camera_id, x_coord, y_coord):
        """Saves or updates a camera's position on a map."""
        return await self.db_manager.save_camera_placement(map_id, camera_id, x_coord, y_coord)
