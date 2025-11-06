# AgroPulse "Hive" - AI Foundry
# Main application entry point for the MLOps platform.

import logging
import asyncio
from data_lake.manager import DataLakeManager
from model_foundry.manager import ModelFoundryManager
from synthetic_data.manager import SyntheticDataManager
from deployment_nexus.manager import DeploymentNexusManager
from web_ui.server import HiveAPIServer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HiveSystem:
    def __init__(self):
        logger.info("Initializing AgroPulse Hive AI Foundry...")
        # Config would be loaded from a dedicated file/service
        self.config = {
            'data_lake': {'storage_path': '/mnt/data_lake'},
            'model_foundry': {'gpu_devices': [0, 1]},
            'deployment_nexus': {'target_registry': 'docker.io/agropulse'},
            'api': {'host': '0.0.0.0', 'port': 10000}
        }
        
        self.data_lake = DataLakeManager(self.config.get('data_lake'))
        self.model_foundry = ModelFoundryManager(self.config.get('model_foundry'))
        self.synthetic_data = SyntheticDataManager(self.config.get('synthetic_data'))
        self.deployment_nexus = DeploymentNexusManager(self.config.get('deployment_nexus'))
        self.api_server = HiveAPIServer(self)
        
        logger.info("Hive System Initialized.")

    async def start(self):
        logger.info("Starting all Hive services...")
        await self.data_lake.start()
        await self.model_foundry.start()
        await self.api_server.start()
        logger.info("Hive System is now running.")

    async def stop(self):
        logger.info("Stopping all Hive services...")
        await self.api_server.stop()
        await self.model_foundry.stop()
        await self.data_lake.stop()
        logger.info("Hive System has been shut down.")

async def main():
    system = HiveSystem()
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
