# C&C API Server
# Provides the web interface and API for the Global Command & Control center.

import logging
import uvicorn
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

logger = logging.getLogger(__name__)

class CncAPIServer:
    def __init__(self, cnc_system):
        self.cnc = cnc_system
        self.config = self.cnc.config.get('api', {})
        
        self.app = FastAPI(title="AgroPulse C&C API")
        self.templates = Jinja2Templates(directory="cnc_web_ui/templates")
        self.app.mount("/static", StaticFiles(directory="cnc_web_ui/static"), name="static")

        # UI Routes
        self.app.add_api_route("/", self.serve_dashboard, methods=["GET"])
        
        # API Routes
        self.app.add_api_route("/api/global_status", self.get_global_status, methods=["GET"])

    async def serve_dashboard(self, request: Request):
        return self.templates.TemplateResponse("dashboard.html", {"request": request})

    async def get_global_status(self):
        status = self.cnc.dashboard_manager.get_current_global_status()
        return status

    async def start(self):
        logger.info("Starting C&C API Server...")
        self.server_task = asyncio.create_task(
            uvicorn.run(
                self.app,
                host=self.config.get('host', '0.0.0.0'),
                port=self.config.get('port', 9000),
                log_level="info"
            )
        )

    async def stop(self):
        logger.info("Stopping C&C API Server...")
        if self.server_task:
            self.server_task.cancel()
