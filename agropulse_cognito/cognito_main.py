# AgroPulse "Cognito" - Global Intelligence Engine
# Main application entry point.

import logging
import asyncio
from correlation_engine.manager import CorrelationEngineManager
from external_data_integrator.manager import ExternalDataIntegratorManager
from strategic_forecasting.manager import StrategicForecastingManager
from knowledge_graph.manager import KnowledgeGraphManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CognitoSystem:
    def __init__(self):
        logger.info("Initializing AgroPulse Cognito Global Intelligence Engine...")
        self.config = {} # Load from file
        
        self.correlation_engine = CorrelationEngineManager(self.config)
        self.ext_data_integrator = ExternalDataIntegratorManager(self.config)
        self.strategic_forecaster = StrategicForecastingManager(self.config)
        self.knowledge_graph = KnowledgeGraphManager(self.config)
        
        logger.info("Cognito System Initialized.")

    async def start(self):
        logger.info("Starting all Cognito services...")
        await self.knowledge_graph.start()
        await self.ext_data_integrator.start()
        await self.correlation_engine.start()
        await self.strategic_forecaster.start()
        logger.info("Cognito System is now running.")

    async def stop(self):
        logger.info("Stopping all Cognito services...")
        # Stop services in reverse order
        await self.strategic_forecaster.stop()
        await self.correlation_engine.stop()
        await self.ext_data_integrator.stop()
        await self.knowledge_graph.stop()
        logger.info("Cognito System has been shut down.")

async def main():
    system = CognitoSystem()
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
