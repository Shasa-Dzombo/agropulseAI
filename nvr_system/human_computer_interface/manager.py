# Advanced Human-Computer Interface Manager

import logging
from .ar_integration.ar_server import ARServer
from .gestural_control.manager import GestureManager

logger = logging.getLogger(__name__)

class HCIManager:
    def __init__(self, config):
        self.config = config.get('hci', {})
        self.is_enabled = self.config.get('enabled', False)
        self.ar_server = ARServer(self.config.get('ar', {}))
        self.gesture_manager = GestureManager(self.config.get('gestures', {}))
        logger.info(f"HCI Manager initialized. Enabled: {self.is_enabled}")

    async def start(self):
        if not self.is_enabled: return
        await self.ar_server.start()
        await self.gesture_manager.start()

    async def stop(self):
        if not self.is_enabled: return
        await self.ar_server.stop()
        await self.gesture_manager.stop()
