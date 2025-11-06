"""
FastAPI Application Main Entry Point for Yield Estimation
=========================================================

This script is the main entry point for launching the FastAPI web server for the
yield estimation module. It brings together all the different components of the
API and configures the application.

Core Responsibilities:
----------------------
1.  **FastAPI App Initialization**:
    -   Creates the main `FastAPI` application instance.
    -   Sets metadata for the API such as the title, version, and description,
      which will be displayed in the auto-generated OpenAPI (Swagger) documentation.

2.  **Router Inclusion**:
    -   Imports the `APIRouter` from `api.endpoints`.
    -   Includes this router in the main application using `app.include_router`.
      This is how the `/predict` endpoint becomes part of the application.
    -   A prefix (`/yield-estimation`) and tags can be added to organize endpoints,
      which is especially useful in larger applications with multiple modules.

3.  **Logging Configuration**:
    -   Calls the `setup_logging` function to configure the application's logger.
      This ensures that all logs from the API (e.g., request logs, errors) are
      formatted and handled consistently.

4.  **CORS (Cross-Origin Resource Sharing) Middleware**:
    -   Adds `CORSMiddleware` to the application.
    -   This is a crucial security feature for web APIs. It is configured to
      allow requests from any origin (`allow_origins=["*"]`), which is common
      for public APIs, but can be restricted to specific domains for better
      security. It also specifies which HTTP methods and headers are allowed.

5.  **Server Execution (Uvicorn)**:
    -   The `if __name__ == "__main__":` block allows the server to be started
      directly by running this script.
    -   It uses `uvicorn`, a high-performance ASGI server, to run the FastAPI
      application.
    -   The host is set to `0.0.0.0` to make the server accessible from other
      machines on the network, and the port is set to `8001`.

This script provides a complete, production-ready setup for serving the yield
estimation API.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

# Adjust path to allow for root-level imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from app.computer_vision.yield_estimation.api import endpoints as yield_estimation_endpoints
from app.computer_vision.yield_estimation.utils.logging_config import setup_logging
from app.computer_vision.yield_estimation.utils.config import get_settings

def create_app() -> FastAPI:
    """
    Creates and configures the FastAPI application.
    """
    settings = get_settings()
    setup_logging(log_level=settings.log_level)

    app = FastAPI(
        title="AgroPulse - Yield Estimation API",
        version="1.0.0",
        description="API for running yield estimation models (detection, segmentation, regression)."
    )

    # --- Middleware ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allow all methods
        allow_headers=["*"],  # Allow all headers
    )

    # --- Routers ---
    app.include_router(
        yield_estimation_endpoints.router, 
        prefix="/yield-estimation", 
        tags=["Yield Estimation"]
    )

    @app.get("/", tags=["Root"])
    async def read_root():
        return {"message": "Welcome to the AgroPulse Yield Estimation API. Visit /docs for documentation."}

    return app

app = create_app()

if __name__ == "__main__":
    # This allows the script to be run directly, ensuring correct module resolution
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        
    # Re-import with the correct path context
    from app.computer_vision.yield_estimation.api import endpoints as yield_estimation_endpoints
    from app.computer_vision.yield_estimation.utils.logging_config import setup_logging
    from app.computer_vision.yield_estimation.utils.config import get_settings
    
    # Re-create app with correct context
    app = create_app()

    uvicorn.run(app, host="0.0.0.0", port=8001)
