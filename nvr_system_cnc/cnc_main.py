# AgroPulse Global Command & Control (C&C)
# Main application entry point for the C&C server.

import logging
import asyncio
from cnc_api.server import CncAPIServer
from cnc_federation_client.manager import CncFederationClientManager
from cnc_global_dashboard.manager import GlobalDashboardManager
from cnc_asset_tracking.manager import GlobalAssetTrackingManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CncSystem:
    def __init__(self):
        logger.info("Initializing AgroPulse Global Command & Control System...")
        # In a real app, config would be loaded from a file
        self.config = {
            'api': {'host': '0.0.0.0', 'port': 9000},
            'federation_client': {
                'nvr_clusters': [
                    {'name': 'site-alpha', 'api_endpoint': 'http://localhost:8000'},
                    {'name': 'site-beta', 'api_endpoint': 'http://localhost:8001'}
                ]
            }
        }
        
        self.federation_client = CncFederationClientManager(self.config.get('federation_client'))
        self.dashboard_manager = GlobalDashboardManager(self.federation_client)
        self.asset_manager = GlobalAssetTrackingManager(self.federation_client)
        self.api_server = CncAPIServer(self)
        
        logger.info("C&C System Initialized.")

    async def start(self):
        logger.info("Starting all C&C services...")
        await self.federation_client.start()
        await self.dashboard_manager.start()
        await self.api_server.start()
        logger.info("C&C System is now running.")

    async def stop(self):
        logger.info("Stopping all C&C services...")
        await self.api_server.stop()
        await self.dashboard_manager.stop()
        await self.federation_client.stop()
        logger.info("C&C System has been shut down.")

async def main():
    system = CncSystem()
    try:
        await system.start()
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutdown signal received.")
    finally:
        await system.stop()

if __name__ == "__main__":
    asyncio.run(main())
