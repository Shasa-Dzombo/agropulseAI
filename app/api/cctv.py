from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from app.database import get_db
from app.auth import get_current_user, get_api_key_user
from app.models.user import User
from app.models.cctv import (
    CCTV, CCTVCapture, CropHealthReading,
    CCTVCalibration, SentryScoutHandshake, HandshakeStatus
)
from app.models.sensor import Alert
from app.schemas import cctv as cctv_schemas
from app.services.cctv_service import virtual_multispectral_service
from app.services.ai_service import ai_service
from app.services.notification_service import notification_service

router = APIRouter(prefix="/api/v1/cctv", tags=["CCTV"])


@router.post("", response_model=cctv_schemas.CCTVResponse, status_code=status.HTTP_201_CREATED)
async def register_cctv(
    cctv_data: cctv_schemas.CCTVCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new CCTV device (Sentry Stake)
    Supports both basic and advanced (NIR/Red LED) devices
    """
    # Verify user owns the farm
    from app.models.user import Farm
    result = await db.execute(
        select(Farm).where(
            Farm.id == cctv_data.farm_id,
            Farm.owner_id == current_user.id
        )
    )
    farm = result.scalar_one_or_none()
    
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found or access denied"
        )
    
    # Create CCTV device
    cctv = CCTV(
        farm_id=cctv_data.farm_id,
        zone_id=cctv_data.zone_id,
        device_serial=cctv_data.device_serial,
        latitude=cctv_data.latitude,
        longitude=cctv_data.longitude,
        has_nir_led=cctv_data.has_nir_led,
        has_red_led=cctv_data.has_red_led,
        nir_led_wavelength=cctv_data.nir_led_wavelength,
        red_led_wavelength=cctv_data.red_led_wavelength,
        has_macro_lens=cctv_data.has_macro_lens,
        has_pir_sensor=cctv_data.has_pir_sensor,
        has_environmental_sensor=cctv_data.has_environmental_sensor
    )
    
    db.add(cctv)
    await db.commit()
    await db.refresh(cctv)
    
    return cctv


@router.post("/{cctv_id}/capture", response_model=cctv_schemas.CCTVCaptureResponse)
async def submit_capture(
    cctv_id: int,
    capture_data: cctv_schemas.CCTVCaptureCreate,
    api_key_user: User = Depends(get_api_key_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a new capture from ESP32-CAM
    Processes virtual multispectral data if LEDs are present
    """
    # Verify CCTV exists
    result = await db.execute(select(CCTV).where(CCTV.id == cctv_id))
    cctv = result.scalar_one_or_none()
    
    if not cctv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CCTV not found"
        )
    
    # Create capture record
    capture = CCTVCapture(
        cctv_id=cctv_id,
        image_url=capture_data.image_url,
        nir_led_active=capture_data.nir_led_active,
        red_led_active=capture_data.red_led_active,
        target_brightness_nir=capture_data.target_brightness_nir,
        target_brightness_red=capture_data.target_brightness_red,
        ambient_temperature=capture_data.ambient_temperature,
        ambient_humidity=capture_data.ambient_humidity,
        ambient_light=capture_data.ambient_light,
        triage_result=capture_data.triage_result,
        triage_confidence=capture_data.triage_confidence
    )
    
    db.add(capture)
    await db.flush()
    
    # Process capture if it has multispectral data
    health_reading = None
    if cctv.has_nir_led and cctv.has_red_led:
        health_reading = await virtual_multispectral_service.process_cctv_capture(
            capture, cctv, db
        )
    
    await db.commit()
    await db.refresh(capture)
    
    # Build response
    response_data = {
        **capture.__dict__,
        "health_analysis": None
    }
    
    if health_reading:
        response_data["health_analysis"] = {
            "health_score": health_reading.health_score,
            "ndvi_proxy": health_reading.ndvi_proxy,
            "status": health_reading.health_status,
            "alert_generated": health_reading.alert_generated
        }
    
    return response_data


@router.post("/{cctv_id}/calibrate", response_model=cctv_schemas.CCTVCalibrationResponse)
async def calibrate_cctv(
    cctv_id: int,
    calibration_data: cctv_schemas.CCTVCalibrationRequest,
    api_key_user: User = Depends(get_api_key_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Auto-calibration endpoint
    ESP32-CAM captures reference target and sends brightness values
    """
    # Verify CCTV exists
    result = await db.execute(select(CCTV).where(CCTV.id == cctv_id))
    cctv = result.scalar_one_or_none()
    
    if not cctv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CCTV not found"
        )
    
    # Deactivate previous calibrations
    await db.execute(
        select(CCTVCalibration).where(
            CCTVCalibration.cctv_id == cctv_id,
            CCTVCalibration.is_active == True
        )
    )
    old_calibrations = (await db.execute(
        select(CCTVCalibration).where(
            CCTVCalibration.cctv_id == cctv_id,
            CCTVCalibration.is_active == True
        )
    )).scalars().all()
    
    for old_cal in old_calibrations:
        old_cal.is_active = False
    
    # Create new calibration
    calibration = CCTVCalibration(
        cctv_id=cctv_id,
        target_type=calibration_data.target_type,
        target_reflectance_known=calibration_data.target_reflectance_known,
        target_brightness_nir=calibration_data.target_brightness_nir,
        target_brightness_red=calibration_data.target_brightness_red,
        ambient_temperature=calibration_data.ambient_temperature,
        ambient_humidity=calibration_data.ambient_humidity,
        ambient_light=calibration_data.ambient_light,
        is_active=True
    )
    
    # Calculate correction factors
    if calibration_data.target_brightness_nir > 0:
        calibration.correction_factor_nir = (
            calibration_data.target_reflectance_known / calibration_data.target_brightness_nir
        ) * 255
    
    if calibration_data.target_brightness_red > 0:
        calibration.correction_factor_red = (
            calibration_data.target_reflectance_known / calibration_data.target_brightness_red
        ) * 255
    
    # Assess quality
    quality = virtual_multispectral_service._assess_calibration_quality(
        calibration.target_reflectance_known,
        calibration.target_reflectance_known * 0.8,
        calibration_data.target_brightness_nir,
        calibration_data.target_brightness_red
    )
    calibration.calibration_quality = quality
    
    db.add(calibration)
    
    # Update CCTV status
    cctv.is_calibrated = True
    cctv.last_calibration = datetime.utcnow()
    
    await db.commit()
    await db.refresh(calibration)
    
    return calibration


@router.get("/{cctv_id}/health", response_model=List[cctv_schemas.CropHealthReadingResponse])
async def get_health_readings(
    cctv_id: int,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get health readings from CCTV
    Returns latest NDVI-proxy measurements
    """
    # Verify access
    result = await db.execute(
        select(CCTV).where(CCTV.id == cctv_id)
    )
    cctv = result.scalar_one_or_none()
    
    if not cctv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CCTV not found"
        )
    
    # Get farm to check ownership
    from app.models.user import Farm
    result = await db.execute(
        select(Farm).where(
            Farm.id == cctv.farm_id,
            Farm.owner_id == current_user.id
        )
    )
    farm = result.scalar_one_or_none()
    
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get readings
    result = await db.execute(
        select(CropHealthReading)
        .where(CropHealthReading.cctv_id == cctv_id)
        .order_by(CropHealthReading.created_at.desc())
        .limit(limit)
    )
    readings = result.scalars().all()
    
    return readings


@router.post("/handshake/alert", response_model=cctv_schemas.SentryScoutHandshakeResponse)
async def initiate_handshake(
    handshake_data: cctv_schemas.SentryScoutHandshakeCreate,
    api_key_user: User = Depends(get_api_key_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Initiate Sentry-Scout Handshake
    Called when CCTV generates an alert
    """
    # Verify alert exists
    result = await db.execute(
        select(Alert).where(Alert.id == handshake_data.alert_id)
    )
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    # Create handshake
    handshake = SentryScoutHandshake(
        alert_id=handshake_data.alert_id,
        cctv_id=handshake_data.cctv_id,
        farmer_id=alert.farm.owner_id,
        status=HandshakeStatus.ALERT_SENT
    )
    
    db.add(handshake)
    await db.commit()
    await db.refresh(handshake)
    
    # TODO: Send push notification to farmer
    # TODO: Send chatbot message with GPS coordinates
    
    return handshake


@router.post("/handshake/{handshake_id}/acknowledge")
async def acknowledge_alert(
    handshake_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Farmer acknowledges alert
    Updates handshake status
    """
    result = await db.execute(
        select(SentryScoutHandshake).where(
            SentryScoutHandshake.id == handshake_id,
            SentryScoutHandshake.farmer_id == current_user.id
        )
    )
    handshake = result.scalar_one_or_none()
    
    if not handshake:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Handshake not found"
        )
    
    handshake.status = HandshakeStatus.ACKNOWLEDGED
    handshake.acknowledged_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": "Alert acknowledged", "status": "acknowledged"}


@router.post("/handshake/{handshake_id}/arrived")
async def mark_arrived(
    handshake_id: int,
    latitude: float,
    longitude: float,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Farmer arrives at location
    Verifies proximity to CCTV
    """
    result = await db.execute(
        select(SentryScoutHandshake).where(
            SentryScoutHandshake.id == handshake_id,
            SentryScoutHandshake.farmer_id == current_user.id
        )
    )
    handshake = result.scalar_one_or_none()
    
    if not handshake:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Handshake not found"
        )
    
    # Get CCTV location
    result = await db.execute(
        select(CCTV).where(CCTV.id == handshake.cctv_id)
    )
    cctv = result.scalar_one_or_none()
    
    # Calculate distance
    distance = virtual_multispectral_service.calculate_distance(
        latitude, longitude,
        cctv.latitude, cctv.longitude
    )
    
    # Verify within 50 meters
    if distance > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too far from CCTV location. Distance: {distance:.1f}m"
        )
    
    handshake.status = HandshakeStatus.FARMER_ARRIVED
    handshake.farmer_arrived_at = datetime.utcnow()
    handshake.arrival_distance_meters = distance
    
    await db.commit()
    
    return {
        "message": "Arrival confirmed",
        "distance_meters": round(distance, 1),
        "status": "farmer_arrived"
    }


@router.post("/handshake/{handshake_id}/diagnose")
async def complete_diagnosis(
    handshake_id: int,
    diagnosis_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Link phone diagnosis to CCTV alert
    Completes the Sentry-Scout Handshake
    """
    result = await db.execute(
        select(SentryScoutHandshake).where(
            SentryScoutHandshake.id == handshake_id,
            SentryScoutHandshake.farmer_id == current_user.id
        )
    )
    handshake = result.scalar_one_or_none()
    
    if not handshake:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Handshake not found"
        )
    
    handshake.status = HandshakeStatus.DIAGNOSIS_COMPLETED
    handshake.diagnosis_id = diagnosis_id
    handshake.diagnosis_completed_at = datetime.utcnow()
    
    await db.commit()
    
    return {
        "message": "Diagnosis completed",
        "status": "diagnosis_completed"
    }


@router.patch("/{cctv_id}/config", response_model=cctv_schemas.CCTVResponse)
async def update_cctv_config(
    cctv_id: int,
    config_update: cctv_schemas.CCTVConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update CCTV configuration
    Can change capture intervals, power modes, etc.
    """
    # Verify CCTV and ownership
    result = await db.execute(
        select(CCTV).where(CCTV.id == cctv_id)
    )
    cctv = result.scalar_one_or_none()
    
    if not cctv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CCTV not found"
        )
    
    from app.models.user import Farm
    result = await db.execute(
        select(Farm).where(
            Farm.id == cctv.farm_id,
            Farm.owner_id == current_user.id
        )
    )
    farm = result.scalar_one_or_none()
    
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Update fields
    if config_update.capture_interval_minutes is not None:
        cctv.capture_interval_minutes = config_update.capture_interval_minutes
    
    if config_update.battery_save_mode is not None:
        cctv.battery_save_mode = config_update.battery_save_mode
    
    if config_update.pir_wake_enabled is not None:
        cctv.pir_wake_enabled = config_update.pir_wake_enabled
    
    if config_update.alert_threshold is not None:
        cctv.alert_threshold = config_update.alert_threshold
    
    await db.commit()
    await db.refresh(cctv)
    
    return cctv


@router.get("/farm/{farm_id}", response_model=List[cctv_schemas.CCTVResponse])
async def list_farm_cctvs(
    farm_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all CCTV devices on a farm
    """
    # Verify farm ownership
    from app.models.user import Farm
    result = await db.execute(
        select(Farm).where(
            Farm.id == farm_id,
            Farm.owner_id == current_user.id
        )
    )
    farm = result.scalar_one_or_none()
    
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found or access denied"
        )
    
    # Get all CCTVs
    result = await db.execute(
        select(CCTV)
        .where(CCTV.farm_id == farm_id)
        .order_by(CCTV.created_at.desc())
    )
    cctvs = result.scalars().all()
    
    return cctvs


# ============================================================================
# IOT EXTENSIONS: Sentry-Scout-Chatbot Handshake Endpoints
# ============================================================================

@router.post("/alert", status_code=status.HTTP_202_ACCEPTED)
async def receive_sentry_alert(
    alert_packet: dict,
    db: AsyncSession = Depends(get_db),
    api_key_user: User = Depends(get_api_key_user)
):
    """
    Receive Sentry alert from IoT device and initiate handshake
    
    This endpoint is called by Sentry Stakes when they detect stress/pests.
    It orchestrates:
    1. Alert enrichment with farmer/crop data
    2. Push notification to mobile app
    3. Chatbot message (WhatsApp/Telegram)
    4. Handshake record creation
    
    Expected payload from ESP32:
    {
        "sentry_id": 1,
        "alert_type": "STRESS_DETECTED",
        "gps_location": {"latitude": -1.286389, "longitude": 36.817223},
        "health_data": {
            "expected_health": 0.75,
            "current_health": 0.50,
            "ndvi_proxy": 0.45,
            "stress_pattern": "edge"
        },
        "environmental_context": {...},
        "micro_pest_alert": {...},  // optional
        "accuracy_features": {...},
        "triage": {"result": "ALERT", "confidence": 0.88}
    }
    """
    sentry_id = alert_packet.get("sentry_id")
    
    if not sentry_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sentry_id is required in alert packet"
        )
    
    # Verify Sentry exists
    result = await db.execute(
        select(CCTV).where(CCTV.id == sentry_id)
    )
    sentry = result.scalars().first()
    
    if not sentry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sentry device #{sentry_id} not found"
        )
    
    # Handle alert and initiate handshake
    handshake_result = await notification_service.handle_sentry_alert(
        db, alert_packet, sentry_id
    )
    
    return {
        "status": "accepted",
        "message": "Sentry alert received. Handshake initiated.",
        **handshake_result
    }


@router.post("/handshake/{handshake_id}/scout-arrival", response_model=dict)
async def report_scout_arrival(
    handshake_id: int,
    arrival_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Report Scout (farmer) arrival at GPS location
    
    Mobile app calls this endpoint when farmer arrives at Sentry location.
    Verifies proximity (<50m) and updates handshake status.
    
    Expected payload:
    {
        "scout_gps_lat": -1.286389,
        "scout_gps_lon": 36.817223
    }
    """
    scout_lat = arrival_data.get("scout_gps_lat")
    scout_lon = arrival_data.get("scout_gps_lon")
    
    if scout_lat is None or scout_lon is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="scout_gps_lat and scout_gps_lon are required"
        )
    
    # Handle arrival
    result = await notification_service.handle_scout_arrival(
        db, handshake_id, scout_lat, scout_lon
    )
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"]
        )
    
    return result


@router.post("/handshake/{handshake_id}/diagnosis", response_model=dict)
async def submit_diagnosis_result(
    handshake_id: int,
    diagnosis_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit AI diagnosis result and close the handshake loop
    
    Called after high-fidelity scan is complete and AI diagnosis is ready.
    
    NEW: Integrates with advanced features (Core Ideas 5-7):
    - Creates blockchain Digital Health Passport (immutable record)
    - Triggers Chama outbreak analysis (if farmer is member)
    - Generates AI-optimized treatment recommendations
    
    Expected payload:
    {
        "disease": "Fall Armyworm",
        "confidence": 0.92,
        "treatment": "Apply BT-based biopesticide...",
        "severity": "moderate",
        "yield_loss_percent": 25,
        "capture_data": {
            "image": "<base64_or_ipfs_hash>",
            "stress_map": [...],
            "frames_stacked": 12,
            "temperature": 28.5,
            "humidity": 75.0,
            "gps_lat": -1.286389,
            "gps_lon": 36.817223
        },
        "field_info": {
            "field_id": 42,
            "crop_type": "maize",
            "area_hectares": 2.5
        },
        "create_blockchain_passport": true,  // optional, default true for confidence >= 0.90
        "chama_id": 15  // optional, if farmer is Chama member
    }
    """
    from app.services.blockchain_passport_service import blockchain_passport_service
    from app.services.chama_outbreak_service import chama_outbreak_service
    from app.services.intervention_optimizer_service import intervention_optimizer
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Handle diagnosis and send to farmer
    result = await notification_service.handle_diagnosis_result(
        db, handshake_id, diagnosis_data
    )
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"]
        )
    
    # ========================================================================
    # ADVANCED FEATURES INTEGRATION (Core Ideas 5-7)
    # ========================================================================
    
    confidence = diagnosis_data.get("confidence", 0.0)
    create_passport = diagnosis_data.get("create_blockchain_passport", confidence >= 0.90)
    
    # Core Idea 5: Create blockchain Digital Health Passport (if high confidence)
    blockchain_passport = None
    if create_passport and confidence >= 0.90:
        try:
            capture_data = diagnosis_data.get("capture_data")
            field_info = diagnosis_data.get("field_info")
            
            if capture_data and field_info:
                logger.info(f"🔗 Creating blockchain passport for diagnosis (confidence: {confidence:.2%})")
                
                blockchain_passport = await blockchain_passport_service.create_health_passport(
                    db=db,
                    diagnosis={
                        "disease": diagnosis_data.get("disease"),
                        "confidence": confidence,
                        "severity": diagnosis_data.get("severity"),
                        "treatment": diagnosis_data.get("treatment"),
                        "yield_loss_percent": diagnosis_data.get("yield_loss_percent", 0)
                    },
                    capture_data=capture_data,
                    farmer_id=current_user.id,
                    field_id=field_info.get("field_id")
                )
                
                logger.info(f"✅ Blockchain passport created: {blockchain_passport.get('passport_hash')}")
                
                # Add to result
                result["blockchain_passport"] = {
                    "passport_id": blockchain_passport.get("passport_id"),
                    "passport_hash": blockchain_passport.get("passport_hash"),
                    "permit_token_id": blockchain_passport.get("permit_token_id"),
                    "verification_url": blockchain_passport.get("verification_url"),
                    "message": "🔐 Your diagnosis is blockchain-verified and immutable."
                }
            else:
                logger.warning("⚠️ Skipping blockchain passport: missing capture_data or field_info")
        
        except Exception as e:
            logger.error(f"❌ Blockchain passport creation failed: {e}")
            result["blockchain_passport"] = {
                "status": "failed",
                "error": str(e)
            }
    
    # Core Idea 6: Analyze Chama outbreak patterns (if farmer is member)
    chama_id = diagnosis_data.get("chama_id")
    if chama_id and confidence >= 0.85:
        try:
            logger.info(f"📊 Analyzing Chama #{chama_id} outbreak patterns...")
            
            outbreak_analysis = await chama_outbreak_service.analyze_community_outbreaks(
                db=db,
                chama_id=chama_id,
                lookback_days=14
            )
            
            active_clusters = outbreak_analysis.get("active_clusters", [])
            at_risk = len(outbreak_analysis.get("at_risk_farmers", [])) > 0
            
            logger.info(f"✅ Chama analysis: {len(active_clusters)} active clusters")
            
            # Add to result
            result["community_intelligence"] = {
                "status": "analyzed",
                "active_clusters": len(active_clusters),
                "urgency_level": outbreak_analysis.get("spread_analysis", {}).get("urgency_level"),
                "at_risk": at_risk,
                "message": f"⚠️ {len(active_clusters)} disease clusters detected in your community." if active_clusters else "✅ No outbreak detected in your community."
            }
        
        except Exception as e:
            logger.error(f"❌ Chama outbreak analysis failed: {e}")
            result["community_intelligence"] = {
                "status": "failed",
                "error": str(e)
            }
    
    # Core Idea 7: Generate AI-optimized treatment recommendations
    field_info = diagnosis_data.get("field_info")
    if field_info:
        try:
            logger.info(f"💊 Generating treatment recommendations...")
            
            treatment_recs = await intervention_optimizer.recommend_interventions(
                db=db,
                diagnosis={
                    "disease": diagnosis_data.get("disease"),
                    "confidence": confidence,
                    "severity": diagnosis_data.get("severity"),
                    "estimated_yield_loss_percent": diagnosis_data.get("yield_loss_percent", 0)
                },
                crop_type=field_info.get("crop_type"),
                field_area_ha=field_info.get("area_hectares"),
                farmer_budget_ksh=diagnosis_data.get("farmer_budget_ksh"),
                preferences=diagnosis_data.get("treatment_preferences", {})
            )
            
            top_option = treatment_recs["treatment_options"][0] if treatment_recs["treatment_options"] else None
            
            logger.info(f"✅ Treatment recommendations generated: {len(treatment_recs['treatment_options'])} options")
            
            # Add to result
            result["treatment_recommendations"] = {
                "status": "optimized",
                "top_recommendation": {
                    "name": top_option.get("treatment_name"),
                    "cost_ksh": top_option.get("total_cost_ksh"),
                    "roi": top_option.get("roi"),
                    "efficacy": top_option.get("efficacy")
                } if top_option else None,
                "total_options": len(treatment_recs["treatment_options"]),
                "no_action_loss_ksh": treatment_recs["no_action_scenario"]["estimated_revenue_loss_ksh"],
                "message": f"💊 Best option: {top_option.get('treatment_name')} (ROI: {top_option.get('roi')}×)" if top_option else "No treatment options available"
            }
        
        except Exception as e:
            logger.error(f"❌ Treatment recommendation failed: {e}")
            result["treatment_recommendations"] = {
                "status": "failed",
                "error": str(e)
            }
    
    return result


@router.get("/handshake/{handshake_id}", response_model=cctv_schemas.SentryScoutHandshakeResponse)
async def get_handshake_status(
    handshake_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get status of Sentry-Scout handshake
    
    Used by mobile app to check handshake progress:
    - pending: Alert sent, waiting for Scout
    - scout_arrived: Farmer at location
    - scanning: High-fidelity scan in progress
    - diagnosis_complete: AI diagnosis sent to farmer
    """
    result = await db.execute(
        select(SentryScoutHandshake).where(SentryScoutHandshake.id == handshake_id)
    )
    handshake = result.scalars().first()
    
    if not handshake:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Handshake not found"
        )
    
    # Verify user has access (owns the Sentry)
    result = await db.execute(
        select(CCTV).where(CCTV.id == handshake.cctv_id)
    )
    sentry = result.scalars().first()
    
    if sentry and sentry.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return handshake


@router.get("/handshake", response_model=List[cctv_schemas.SentryScoutHandshakeResponse])
async def list_handshakes(
    status_filter: Optional[str] = None,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List Sentry-Scout handshakes for current user
    
    Query params:
    - status_filter: Filter by status (pending, scout_arrived, diagnosis_complete)
    - limit: Max number of results (default 20)
    """
    # Get user's Sentries
    result = await db.execute(
        select(CCTV.id).where(CCTV.user_id == current_user.id)
    )
    sentry_ids = [row[0] for row in result.fetchall()]
    
    if not sentry_ids:
        return []
    
    # Build query
    query = select(SentryScoutHandshake).where(
        SentryScoutHandshake.cctv_id.in_(sentry_ids)
    )
    
    if status_filter:
        query = query.where(SentryScoutHandshake.status == status_filter)
    
    query = query.order_by(SentryScoutHandshake.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    handshakes = result.scalars().all()
    
    return handshakes


@router.post("/micro-pest", status_code=status.HTTP_201_CREATED)
async def submit_micro_pest_detection(
    pest_data: dict,
    db: AsyncSession = Depends(get_db),
    api_key_user: User = Depends(get_api_key_user)
):
    """
    Submit micro-pest detection result from Sentry
    
    Called by Sentry Stakes when macro lens detects micro-pests (mites, aphids, thrips).
    Creates alert and capture record with pest metadata.
    
    Expected payload:
    {
        "sentry_id": 1,
        "capture_id": 123,  // optional
        "pest_detected": true,
        "pest_type": "mite",
        "pest_size_mm": 0.45,
        "pest_pixel_count": 8,
        "detection_confidence": 0.87,
        "macro_magnification": 10
    }
    """
    sentry_id = pest_data.get("sentry_id")
    
    if not sentry_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sentry_id is required"
        )
    
    # Create alert for pest detection
    alert = Alert(
        sensor_id=sentry_id,
        sensor_type="cctv",
        alert_type="PEST_DETECTED",
        severity="high" if pest_data.get("detection_confidence", 0) > 0.85 else "medium",
        message=f"Micro-pest detected: {pest_data.get('pest_type', 'unknown')} ({pest_data.get('pest_size_mm', 0):.2f}mm)",
        data=pest_data,
        created_at=datetime.utcnow()
    )
    
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    
    return {
        "status": "created",
        "alert_id": alert.id,
        "message": "Micro-pest detection recorded successfully"
    }


@router.post("/qubo-optimize", response_model=dict)
async def request_qubo_optimization(
    optimization_request: dict,
    db: AsyncSession = Depends(get_db),
    api_key_user: User = Depends(get_api_key_user)
):
    """
    Cloud QUBO optimization service for complex problems
    
    This endpoint implements the "Cloud Brain" in the Hybrid Two-Tiered model.
    Sentry Stakes escalate complex QUBO problems here when on-device
    Simulated Annealing is insufficient.
    
    Cloud uses:
    - AWS Braket: D-Wave quantum annealers or hybrid solvers
    - Azure Quantum: IonQ quantum computers or optimization services
    - Classical fallback: High-performance Simulated Annealing on GPU
    
    Expected payload:
    {
        "sentry_id": 1,
        "problem_type": "camera_optimization",
        "num_variables": 4,
        "Q_matrix": [
            [-2.0, -1.0, 0.0, 0.0],
            [-1.0, -3.0, 0.0, 0.0],
            [0.0, 0.0, 5.0, 3.0],
            [0.0, 0.0, 3.0, -5.0]
        ],
        "variable_names": ["angle_45deg", "exposure_150ms", "led_high", "burst_mode"],
        "complexity_score": 24.0
    }
    
    Returns:
    {
        "status": "optimized",
        "optimal_solution": [1, 1, 0, 1],  // Binary variables
        "objective_value": -9.5,
        "solver_used": "aws_braket_hybrid",
        "execution_time_ms": 450,
        "confidence": 0.98
    }
    """
    from app.services.quantum_service import quantum_service
    
    sentry_id = optimization_request.get("sentry_id")
    
    if not sentry_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sentry_id is required"
        )
    
    # Extract QUBO problem
    num_variables = optimization_request.get("num_variables", 0)
    Q_matrix = optimization_request.get("Q_matrix", [])
    variable_names = optimization_request.get("variable_names", [])
    complexity_score = optimization_request.get("complexity_score", 0.0)
    
    if not Q_matrix or num_variables == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Q_matrix and num_variables are required"
        )
    
    logger.info(f"☁️ Cloud QUBO Request from Sentry #{sentry_id}")
    logger.info(f"   Problem: {optimization_request.get('problem_type')}")
    logger.info(f"   Variables: {num_variables}, Complexity: {complexity_score}")
    
    # Solve QUBO using quantum service
    try:
        solution = await quantum_service.solve_qubo(
            Q_matrix=Q_matrix,
            num_variables=num_variables,
            problem_type=optimization_request.get("problem_type", "generic"),
            use_quantum=complexity_score > 30.0  # Use true quantum for complex problems
        )
        
        # Translate binary solution to human-readable format
        settings_map = {}
        for i, var_name in enumerate(variable_names):
            if i < len(solution["optimal_solution"]):
                settings_map[var_name] = solution["optimal_solution"][i]
        
        # Build response
        response = {
            "status": "optimized",
            "sentry_id": sentry_id,
            "optimal_solution": solution["optimal_solution"],
            "optimal_settings": settings_map,
            "objective_value": solution.get("objective_value", 0.0),
            "solver_used": solution.get("solver", "hybrid_quantum_classical"),
            "execution_time_ms": solution.get("execution_time_ms", 0),
            "confidence": 0.98,  # Cloud quantum has high confidence
            "message": "Optimal solution computed. Apply these settings for best performance.",
            "hardware_commands": {
                "camera_angle": 45 if settings_map.get("angle_45deg") == 1 else 0,
                "exposure_ms": 150 if settings_map.get("exposure_150ms") == 1 else 50,
                "led_brightness": 255 if settings_map.get("led_high") == 1 else 128,
                "burst_mode": settings_map.get("burst_mode") == 1
            }
        }
        
        logger.info(f"✅ QUBO solved: {solution.get('solver')} in {solution.get('execution_time_ms')}ms")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ QUBO optimization failed: {e}")
        
        # Fallback: Return reasonable default settings
        return {
            "status": "fallback",
            "sentry_id": sentry_id,
            "optimal_solution": [1, 1, 0, 1],  # Conservative defaults
            "solver_used": "fallback_heuristic",
            "execution_time_ms": 0,
            "confidence": 0.75,
            "message": "Quantum solver unavailable. Using fallback heuristic.",
            "error": str(e)
        }

