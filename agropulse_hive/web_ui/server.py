# Hive API Server

import logging
import uvicorn
from fastapi import FastAPI

logger = logging.getLogger(__name__)

class HiveAPIServer:
    def __init__(self, hive_system):
        self.hive = hive_system
        self.config = self.hive.config.get('api', {})
        self.app = FastAPI(title="AgroPulse Hive API")
        # Add API routes for submitting training jobs, checking status, etc.

    async def start(self):
        logger.info("Starting Hive API Server...")
        self.server_task = asyncio.create_task(
            uvicorn.run(
                self.app,
                host=self.config.get('host', '0.0.0.0'),
                port=self.config.get('port', 10000)
            )
        )

    async def stop(self):
        if self.server_task:
            self.server_task.cancel()
