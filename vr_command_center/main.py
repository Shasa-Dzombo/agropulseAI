# AgroPulse "Helios" VR Command Center
# Main application entry point for the VR experience.

import logging
import asyncio
from vr_core.engine import VREngine
from soc_environment.scene_manager import VRSceneManager
from network_client.manager import VRNetworkClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HeliosVRSystem:
    def __init__(self):
        logger.info("Initializing AgroPulse Helios VR Command Center...")
        self.config = {
            'vr_sdk': 'openxr', # Placeholder
            'network': {'cnc_endpoint': 'ws://localhost:9000/ws'}
        }
        
        self.network_client = VRNetworkClient(self.config.get('network'))
        self.scene_manager = VRSceneManager(self)
        self.vr_engine = VREngine(self)
        
        logger.info("Helios VR System Initialized.")

    async def start(self):
        logger.info("Starting Helios VR System...")
        await self.network_client.connect()
        # The VR engine runs its own loop, so we just start it.
        self.vr_engine.run() 

    async def stop(self):
        logger.info("Stopping Helios VR System...")
        await self.network_client.disconnect()
        self.vr_engine.stop()
        logger.info("Helios VR System has been shut down.")

async def main():
    system = HeliosVRSystem()
    try:
        # In a real VR app, the lifecycle is managed differently,
        # but we'll simulate a long-running task.
        await system.start()
        while system.vr_engine.is_running:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutdown signal received.")
    finally:
        await system.stop()

if __name__ == "__main__":
    # This entry point is for simulation. A real VR app would be packaged.
    asyncio.run(main())
