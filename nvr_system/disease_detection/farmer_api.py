"""
Farmer-Friendly Disease Detection API
======================================

REST API endpoint providing simple, actionable disease identification
for farmers and agricultural extension workers.

Features:
- Simple image upload (no technical knowledge required)
- Plain language disease descriptions
- Clear action priorities (urgent, recommended, optional)
- Economic impact estimates
- EPPO codes for regulatory compliance
- Offline capability with rule-based fallback

Usage:
    # Start API server
    python farmer_api.py
    
    # Upload image via POST
    curl -X POST http://localhost:8000/detect \
      -F "image=@diseased_leaf.jpg" \
      -F "crop=tomato" \
      -F "latitude=40.7" \
      -F "longitude=-74.0"

Author: AgroPulse Team
Date: November 2025
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
import cv2
import numpy as np
import io
from datetime import datetime

from .unified_disease_detector import (
    UnifiedDiseaseDetector,
    DetectionMode,
    UnifiedDiseaseResult,
    ConfidenceLevel
)
from .kindwise_api_client import CropType


# Initialize FastAPI app
app = FastAPI(
    title="AgroPulse Disease Detection API",
    description="Farmer-friendly crop disease identification with 288+ diseases",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for web frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global detector instance (initialized on startup)
detector: Optional[UnifiedDiseaseDetector] = None


# Response Models
class ActionItem(BaseModel):
    """Single actionable treatment step"""
    priority: int = Field(..., ge=1, le=3, description="1=Urgent, 2=Recommended, 3=Optional")
    action: str = Field(..., description="What to do")
    timing: str = Field(..., description="When to do it")
    materials: List[str] = Field(default_factory=list, description="What you need")
    cost_usd: Optional[float] = Field(None, description="Estimated cost")
    effectiveness: Optional[int] = Field(None, ge=0, le=100, description="Expected success rate %")


class DiseaseDetectionResponse(BaseModel):
    """Farmer-friendly disease detection response"""
    # Core identification
    disease_name: str = Field(..., description="Disease name in plain English")
    confidence: float = Field(..., ge=0, le=1, description="Detection confidence 0-1")
    confidence_label: str = Field(..., description="Very High, High, Moderate, or Low")
    
    # Disease details
    severity: str = Field(..., description="Minor, Moderate, Severe, or Critical")
    symptoms: List[str] = Field(..., description="Visible symptoms on plant")
    
    # Actions required
    urgent_actions: List[str] = Field(default_factory=list, description="Do these immediately")
    recommended_actions: List[ActionItem] = Field(default_factory=list, description="Treatment steps")
    
    # Impact
    economic_impact: str = Field(..., description="Expected yield/quality loss")
    spread_risk: str = Field(..., description="How fast disease spreads")
    
    # Additional info
    eppo_code: Optional[str] = Field(None, description="International disease code")
    is_quarantine: bool = Field(False, description="Requires regulatory notification")
    alternative_diseases: List[str] = Field(default_factory=list, description="Could also be...")
    
    # Metadata
    detection_method: str = Field(..., description="How disease was identified")
    processing_time_ms: int = Field(..., description="Analysis duration")
    timestamp: str = Field(..., description="When analysis was performed")
    
    # Farmer guidance
    next_steps: str = Field(..., description="What farmer should do next")


class HealthCheckResponse(BaseModel):
    """API health status"""
    status: str
    ai_available: bool
    local_detectors: int
    version: str
    timestamp: str


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    details: Optional[str] = None
    timestamp: str


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize detector on API startup"""
    global detector
    
    import os
    api_key = os.getenv("KINDWISE_API_KEY")
    
    detector = UnifiedDiseaseDetector(
        kindwise_api_key=api_key,
        mode=DetectionMode.AUTO,  # Smart routing
        enable_cache=True,
        confidence_threshold=0.7
    )
    
    print("✓ Farmer API started successfully")


# Endpoints
@app.get("/", response_model=Dict[str, str])
async def root():
    """API information"""
    return {
        "message": "AgroPulse Disease Detection API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Check API health and capabilities"""
    if not detector:
        raise HTTPException(status_code=503, detail="Detector not initialized")
    
    return HealthCheckResponse(
        status="healthy",
        ai_available=detector.ai_available,
        local_detectors=len(detector.rule_detectors),
        version="1.0.0",
        timestamp=datetime.now().isoformat()
    )


@app.post("/detect", response_model=DiseaseDetectionResponse)
async def detect_disease(
    image: UploadFile = File(..., description="Image of diseased plant part"),
    crop: str = Form(..., description="Crop type: tomato, potato, cucumber, etc."),
    latitude: Optional[float] = Form(None, description="GPS latitude (optional)"),
    longitude: Optional[float] = Form(None, description="GPS longitude (optional)"),
    variety: Optional[str] = Form(None, description="Crop variety (optional)")
):
    """
    Detect disease from uploaded image
    
    **Simple Usage:**
    1. Take clear photo of diseased leaf/stem/fruit
    2. Upload image with crop type
    3. Get instant diagnosis and treatment plan
    
    **Tips for best results:**
    - Use good lighting (natural daylight best)
    - Get close to symptoms (fill frame)
    - Focus clearly (not blurry)
    - Include both healthy and diseased tissue
    """
    if not detector:
        raise HTTPException(status_code=503, detail="Detector not initialized")
    
    # Validate crop type
    try:
        crop_type = CropType(crop.lower())
    except ValueError:
        valid_crops = [c.value for c in CropType]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid crop '{crop}'. Valid options: {', '.join(valid_crops)}"
        )
    
    # Read and decode image
    try:
        contents = await image.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="Could not decode image")
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Image processing error: {str(e)}")
    
    # Run detection
    try:
        result = detector.detect(
            image=img,
            crop_type=crop_type,
            latitude=latitude,
            longitude=longitude,
            variety=variety
        )
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="No disease detected. Image may be healthy or unclear."
            )
        
        # Convert to farmer-friendly response
        return _convert_to_api_response(result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection error: {str(e)}")


@app.post("/batch_detect")
async def batch_detect_diseases(
    images: List[UploadFile] = File(...),
    crops: List[str] = Form(...),
    latitudes: Optional[List[float]] = Form(None),
    longitudes: Optional[List[float]] = Form(None)
):
    """
    Batch detect multiple images at once
    Useful for processing multiple fields or plants simultaneously
    """
    if not detector:
        raise HTTPException(status_code=503, detail="Detector not initialized")
    
    if len(images) != len(crops):
        raise HTTPException(
            status_code=400,
            detail="Number of images must match number of crops"
        )
    
    # Process each image
    results = []
    for i, (image_file, crop_str) in enumerate(zip(images, crops)):
        try:
            # Validate crop
            crop_type = CropType(crop_str.lower())
            
            # Read image
            contents = await image_file.read()
            nparr = np.frombuffer(contents, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                results.append({"error": f"Could not decode image {i+1}"})
                continue
            
            # Get coordinates if provided
            lat = latitudes[i] if latitudes and i < len(latitudes) else None
            lon = longitudes[i] if longitudes and i < len(longitudes) else None
            
            # Detect
            result = detector.detect(img, crop_type, lat, lon)
            
            if result:
                results.append(_convert_to_api_response(result).dict())
            else:
                results.append({"error": "No disease detected"})
                
        except Exception as e:
            results.append({"error": str(e)})
    
    return {"results": results, "total": len(images), "timestamp": datetime.now().isoformat()}


def _convert_to_api_response(result: UnifiedDiseaseResult) -> DiseaseDetectionResponse:
    """Convert internal result to farmer-friendly API response"""
    
    # Determine next steps based on severity and confidence
    next_steps = _generate_next_steps(result)
    
    # Extract action items
    recommended_actions = []
    for treatment in result.treatments[:5]:  # Top 5 treatments
        recommended_actions.append(ActionItem(
            priority=treatment.get('priority', 2),
            action=treatment.get('action', 'Apply recommended treatment'),
            timing=treatment.get('timing', 'As soon as possible'),
            materials=treatment.get('materials', []),
            cost_usd=treatment.get('cost_usd'),
            effectiveness=treatment.get('effectiveness')
        ))
    
    return DiseaseDetectionResponse(
        disease_name=result.disease_name,
        confidence=result.confidence,
        confidence_label=result.confidence_level.value.replace('_', ' ').title(),
        severity=result.severity.value.title(),
        symptoms=result.symptoms[:10],  # Top 10 symptoms
        urgent_actions=result.urgent_actions,
        recommended_actions=recommended_actions,
        economic_impact=result.economic_impact or "Variable depending on management",
        spread_risk=result.spread_risk,
        eppo_code=result.eppo_code,
        is_quarantine=False,  # TODO: Check from EPPO database
        alternative_diseases=result.alternative_diagnoses[:3],
        detection_method=result.diagnostic_certainty,
        processing_time_ms=result.detection_time_ms,
        timestamp=result.timestamp.isoformat(),
        next_steps=next_steps
    )


def _generate_next_steps(result: UnifiedDiseaseResult) -> str:
    """Generate actionable next steps for farmer"""
    steps = []
    
    # Confidence-based guidance
    if result.confidence_level == ConfidenceLevel.VERY_HIGH:
        steps.append("✓ High confidence detection - proceed with treatment")
    elif result.confidence_level == ConfidenceLevel.LOW:
        steps.append("⚠️ Low confidence - consider consulting local agronomist")
    
    # Severity-based urgency
    if result.severity == DiseaseSeverity.CRITICAL:
        steps.append("🔴 URGENT: Immediate action required to prevent total crop loss")
    elif result.severity == DiseaseSeverity.SEVERE:
        steps.append("⚠️ Act within 24-48 hours to minimize damage")
    
    # Specific actions
    if result.urgent_actions:
        steps.append(f"Priority action: {result.urgent_actions[0]}")
    
    # Economic consideration
    if "100%" in result.economic_impact or "total loss" in result.economic_impact.lower():
        steps.append("💰 High economic risk - consider professional pest control service")
    
    # Quarantine check
    if result.eppo_code:
        steps.append("📋 Report to local agricultural extension office (EPPO-listed disease)")
    
    return " | ".join(steps) if steps else "Follow recommended treatments in priority order"


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            timestamp=datetime.now().isoformat()
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            details=str(exc),
            timestamp=datetime.now().isoformat()
        ).dict()
    )


# Run server
if __name__ == "__main__":
    import uvicorn
    
    print("Starting AgroPulse Farmer API...")
    print("=" * 60)
    print("API Documentation: http://localhost:8000/docs")
    print("Health Check: http://localhost:8000/health")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
