from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import importlib
import logging
import time
from app.config import settings
from app.database import engine, Base

logger = logging.getLogger(__name__)

# Each router is imported independently so a broken/incomplete one (e.g. one
# still missing dependencies) doesn't prevent the rest of the app - including
# routers unrelated to it - from starting. Failures are logged, not silenced.
_ROUTER_MODULES = [
    "auth", "farms", "sensors", "payments", "diagnoses", "optimization", "cctv",
    "advanced", "drones", "chamas", "farm_inputs",
]
routers = {}
for _module_name in _ROUTER_MODULES:
    try:
        routers[_module_name] = importlib.import_module(f"app.api.{_module_name}")
    except Exception as e:
        logger.warning(f"Router 'app.api.{_module_name}' failed to load and will be unavailable: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown events for AgroPulse Horticulture Platform
    """
    # Startup
    print("🌿 Starting AgroPulse Horticulture Backend...")
    print(f"Environment: {settings.ENVIRONMENT}")
    
    # Create database tables
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)
    
    print("✅ Database initialized")
    print(f"🌐 Server running on {settings.HOST}:{settings.PORT}")
    
    yield
    
    # Shutdown
    print("👋 Shutting down AgroPulse Horticulture Backend...")
    await engine.dispose()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    � AgroPulse - Smart Greenhouse & Horticulture Management Platform
    
    ## Greenhouse Intelligence Architecture
    
    Comprehensive monitoring and control for:
    - **Climate Control**: Real-time temperature, humidity, CO2, PAR light monitoring
    - **Hydroponic Systems**: pH, EC, water temperature tracking and alerts
    - **Disease Detection**: AI-powered greenhouse crop disease identification
    - **Environmental Optimization**: ML-driven climate setpoint recommendations
    
    ## Key Features
    
    ### 1. � Greenhouse Management
    - Multi-greenhouse facility tracking
    - Growing zone management (hydroponics, aeroponics, soil-based)
    - Environmental history and analytics
    - Automated climate alerts
    
    ### 2. 🌱 Crop Health Monitoring
    - ESP32 sensors for 24/7 greenhouse monitoring
    - Mobile phone for high-resolution disease imaging
    - AI diagnosis for greenhouse-specific diseases (powdery mildew, Botrytis, aphids)
    
    ### 3. 💳 Blockchain-Verified Pay-Per-Service
    - M-Pesa payment integration for growers
    - Automatic blockchain permit minting
    - Trustless, immutable payment receipts
    
    ### 4. 🤖 Cloud AI Diagnosis for Greenhouse Crops
    - AWS SageMaker for crop disease detection
    - Multi-image analysis
    - Treatment recommendations
    - 90%+ accuracy
    
    ### 4. ⚛️ Quantum-Optimized Scouting Plans
    - Amazon Braket quantum computing
    - Solves complex farm optimization problems
    - Maximizes risk coverage within budget
    - Optimal path planning
    
    ### 5. 💬 AI Chatbot Assistant
    - Natural language farm management
    - Proactive recommendations
    - Budget optimization advice
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


# Include routers (only those that imported successfully - see loader above)
if "auth" in routers:
    app.include_router(routers["auth"].router, prefix="/api/v1")
if "farms" in routers:
    app.include_router(routers["farms"].router, prefix="/api/v1")
if "sensors" in routers:
    app.include_router(routers["sensors"].router, prefix="/api/v1")
if "payments" in routers:
    app.include_router(routers["payments"].router, prefix="/api/v1")
if "diagnoses" in routers:
    app.include_router(routers["diagnoses"].router, prefix="/api/v1")
if "optimization" in routers:
    app.include_router(routers["optimization"].router, prefix="/api/v1")
if "cctv" in routers:
    app.include_router(routers["cctv"].router)  # CCTV router has its own prefix
if "advanced" in routers:
    app.include_router(routers["advanced"].router)  # Advanced features (blockchain, Chama, interventions)
if "drones" in routers:
    app.include_router(routers["drones"].router, prefix="/api/v1")
if "chamas" in routers:
    app.include_router(routers["chamas"].router, prefix="/api/v1")
if "farm_inputs" in routers:
    app.include_router(routers["farm_inputs"].router, prefix="/api/v1")


# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "🌾 Welcome to AgroPulse - Precision Agriculture as a Service",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }


# System info endpoint
@app.get("/api/v1/info")
async def system_info():
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "pricing": {
            "diagnosis": f"{settings.DIAGNOSIS_PRICE} KSh",
            "weekly_subscription": f"{settings.WEEKLY_SUBSCRIPTION} KSh",
            "monthly_subscription": f"{settings.MONTHLY_SUBSCRIPTION} KSh"
        },
        "features": [
            "Free ESP32-CAM alerts",
            "Pay-per-diagnosis (50 KSh)",
            "Blockchain-verified permits",
            "AWS AI-powered diagnosis",
            "Quantum-optimized scouting plans",
            "AI chatbot assistant",
            "M-Pesa payment integration",
            "🔐 Digital Health Passport (blockchain-anchored immutable records)",
            "📊 Chama-Scale Outbreak Prediction (community intelligence)",
            "💊 AI-Powered Intervention Optimization (ROI-ranked treatments)",
            "📱 Mobile Phone Sensor (99% accuracy with standard camera)"
        ],
        "advanced_features": {
            "blockchain_passport": {
                "description": "Immutable crop health records on Polygon blockchain",
                "use_cases": ["Premium pricing for buyers", "De-risked loans", "Export verification"],
                "cost": "~$0.02 per passport"
            },
            "chama_outbreak_prediction": {
                "description": "Community-wide disease cluster detection and proactive alerts",
                "use_cases": ["Early outbreak warning (3-7 days advance)", "At-risk farmer identification", "Preventative action"],
                "privacy": "GPS anonymized to 1km precision"
            },
            "intervention_optimizer": {
                "description": "AI-powered treatment recommendations with cost-benefit analysis",
                "use_cases": ["ROI-ranked treatment options", "Budget-aware recommendations", "Real-world efficacy data"],
                "example": "Option 1: Lambda-cyhalothrin (Cost: 1,200 KSh, ROI: 4.2×)"
            },
            "mobile_phone_sensor": {
                "description": "Transform any smartphone into precision diagnostic lab",
                "accuracy": "90% on-device (NPU), 99% with cloud confirmation",
                "features": ["Burst capture", "Super-resolution", "Stress-exaggeration model", "Quantum optimization"]
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
