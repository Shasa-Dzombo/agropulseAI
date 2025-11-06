# VR Network Client
# Communicates with the AgroPulse C&C server.

import logging
import asyncio
import websockets

logger = logging.getLogger(__name__)

class VRNetworkClient:
    def __init__(self, config):
        self.config = config
        self.endpoint = self.config.get('cnc_endpoint')
        self.websocket = None
        self.data_cache = {}

    async def connect(self):
        try:
            self.websocket = await websockets.connect(self.endpoint)
            logger.info(f"VR Network Client connected to {self.endpoint}.")
            asyncio.create_task(self._listen())
        except Exception as e:
            logger.error(f"Failed to connect VR Network Client: {e}")

    async def disconnect(self):
        if self.websocket:
            await self.websocket.close()
        logger.info("VR Network Client disconnected.")

    async def _listen(self):
        """Listens for real-time data updates from the C&C server."""
        while self.websocket and self.websocket.open:
            try:
                message = await self.websocket.recv()
                # In a real app, this would be a structured message (e.g., JSON)
                # For example: {"type": "global_status", "payload": {...}}
                # self.data_cache[message['type']] = message['payload']
            except websockets.exceptions.ConnectionClosed:
                break
        logger.info("VR network listener stopped.")

    def get_data(self, key):
        return self.data_cache.get(key, {})
