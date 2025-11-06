from typing import Dict, Optional, Tuple
import numpy as np
from datetime import datetime, timedelta
from app.models.cctv import CCTV, CCTVCapture, CropHealthReading, CCTVCalibration
from app.models.sensor import Alert, AlertSeverity
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import math


class VirtualMultispectralService:
    """
    Implements the Virtual Multispectral Sensor logic
    Replaces expensive multispectral cameras with controlled LED illumination
    """
    
    def __init__(self):
        # Known reflectance values for common calibration targets
        self.CALIBRATION_TARGETS = {
            "gray_card": 0.50,
            "white_target": 0.90,
            "black_target": 0.05
        }
        
        # Crop health thresholds by growth stage
        self.HEALTH_THRESHOLDS = {
            "maize": {
                "seedling": {"min": 0.60, "max": 0.75},
                "vegetative": {"min": 0.70, "max": 0.85},
                "flowering": {"min": 0.75, "max": 0.90},
                "maturity": {"min": 0.60, "max": 0.80}
            },
            "tomato": {
                "seedling": {"min": 0.55, "max": 0.70},
                "vegetative": {"min": 0.65, "max": 0.80},
                "flowering": {"min": 0.70, "max": 0.85},
                "fruiting": {"min": 0.65, "max": 0.80}
            }
        }
    
    async def calculate_ndvi_proxy(
        self,
        leaf_brightness_nir: float,
        leaf_brightness_red: float,
        target_brightness_nir: float,
        target_brightness_red: float,
        target_reflectance: float = 0.50
    ) -> Dict[str, float]:
        """
        Calculate NDVI-proxy from LED reflectance measurements
        This is the core "Virtual Multispectral" algorithm
        
        Args:
            leaf_brightness_nir: Raw brightness of leaf under NIR LED
            leaf_brightness_red: Raw brightness of leaf under Red LED
            target_brightness_nir: Brightness of calibration target under NIR
            target_brightness_red: Brightness of calibration target under Red
            target_reflectance: Known reflectance of calibration target (0.0-1.0)
        
        Returns:
            Dictionary with normalized values and NDVI proxy
        """
        # Step 1: Normalize using calibration target
        # This removes lighting, distance, and sensor variations
        normalized_nir = (leaf_brightness_nir / target_brightness_nir) * target_reflectance
        normalized_red = (leaf_brightness_red / target_brightness_red) * target_reflectance
        
        # Step 2: Calculate NDVI-proxy
        # Standard NDVI formula: (NIR - Red) / (NIR + Red)
        denominator = normalized_nir + normalized_red
        
        if denominator == 0:
            ndvi_proxy = 0.0
        else:
            ndvi_proxy = (normalized_nir - normalized_red) / denominator
        
        # Step 3: Convert to health score (0.0 to 1.0)
        # NDVI typically ranges from -1 to +1
        # For vegetation, we expect 0.2 to 0.9
        # Map this to 0-1 health score
        health_score = max(0.0, min(1.0, (ndvi_proxy + 0.2) / 1.1))
        
        # Step 4: Calculate calibration quality
        # Check if readings are in expected range
        calibration_quality = self._assess_calibration_quality(
            normalized_nir, normalized_red, target_brightness_nir, target_brightness_red
        )
        
        return {
            "normalized_nir": round(normalized_nir, 4),
            "normalized_red": round(normalized_red, 4),
            "ndvi_proxy": round(ndvi_proxy, 4),
            "health_score": round(health_score, 4),
            "calibration_quality": round(calibration_quality, 4)
        }
    
    def _assess_calibration_quality(
        self,
        norm_nir: float,
        norm_red: float,
        target_nir: float,
        target_red: float
    ) -> float:
        """
        Assess the quality of calibration
        Returns value from 0.0 (poor) to 1.0 (excellent)
        """
        quality = 1.0
        
        # Check if target brightness is sufficient
        if target_nir < 50 or target_red < 50:
            quality *= 0.5  # Poor lighting
        
        # Check if normalized values are in reasonable range
        if norm_nir < 0.1 or norm_nir > 0.9:
            quality *= 0.7
        
        if norm_red < 0.05 or norm_red > 0.8:
            quality *= 0.7
        
        # Check signal-to-noise ratio
        snr = (target_nir + target_red) / 2
        if snr < 100:
            quality *= 0.8
        
        return quality
    
    async def interpret_health_score(
        self,
        health_score: float,
        crop_type: str,
        growth_stage: str,
        db: AsyncSession
    ) -> Dict[str, any]:
        """
        Interpret health score based on crop profile
        This is the "On-Chip Triage Model" logic
        """
        # Get expected thresholds
        thresholds = self.HEALTH_THRESHOLDS.get(
            crop_type.lower(),
            {"default": {"min": 0.65, "max": 0.85}}
        ).get(growth_stage.lower(), {"min": 0.65, "max": 0.85})
        
        expected_health = (thresholds["min"] + thresholds["max"]) / 2
        
        # Calculate deviation
        deviation = abs(health_score - expected_health) / expected_health
        
        # Determine status
        if health_score >= thresholds["min"] and health_score <= thresholds["max"]:
            status = "healthy"
            stress_level = "none"
            alert_required = False
        elif health_score < thresholds["min"]:
            if deviation < 0.15:
                status = "mild_stress"
                stress_level = "low"
                alert_required = True
            elif deviation < 0.30:
                status = "moderate_stress"
                stress_level = "medium"
                alert_required = True
            else:
                status = "severe_stress"
                stress_level = "high"
                alert_required = True
        else:
            # Unusually high health (might be measurement error)
            status = "check_calibration"
            stress_level = "none"
            alert_required = False
        
        # Determine likely stress type based on NDVI characteristics
        stress_type = self._determine_stress_type(health_score, expected_health)
        
        return {
            "status": status,
            "expected_health": expected_health,
            "health_score": health_score,
            "deviation_percent": round(deviation * 100, 1),
            "stress_level": stress_level,
            "stress_type": stress_type,
            "alert_required": alert_required,
            "message": self._generate_alert_message(
                status, health_score, expected_health, crop_type, growth_stage
            )
        }
    
    def _determine_stress_type(self, current: float, expected: float) -> Optional[str]:
        """Determine likely stress type from health score pattern"""
        if current >= expected * 0.85:
            return None
        elif current < expected * 0.50:
            return "severe_stress"  # Could be disease or severe water stress
        elif current < expected * 0.70:
            return "water_or_nutrient"  # Likely water or nutrient deficiency
        else:
            return "early_stress"  # Early detection
    
    def _generate_alert_message(
        self,
        status: str,
        current: float,
        expected: float,
        crop_type: str,
        growth_stage: str
    ) -> str:
        """Generate human-readable alert message"""
        if status == "healthy":
            return f"{crop_type.title()} in {growth_stage} stage is healthy."
        
        current_pct = int(current * 100)
        expected_pct = int(expected * 100)
        
        return (
            f"🚨 AgroPulse Alert: Stress detected in {crop_type.title()} ({growth_stage} stage). "
            f"Expected health: {expected_pct}%. Current health: {current_pct}%. "
            f"Please inspect and perform guided scan."
        )
    
    async def process_cctv_capture(
        self,
        capture: CCTVCapture,
        cctv: CCTV,
        db: AsyncSession
    ) -> Optional[CropHealthReading]:
        """
        Process a CCTV capture and generate health reading
        This is called when ESP32-CAM sends a capture
        """
        # Check if we have calibration data
        calibration = await self._get_active_calibration(cctv.id, db)
        
        if not calibration:
            print(f"CCTV {cctv.id} needs calibration")
            return None
        
        # Extract brightness values from capture
        if not capture.target_brightness_nir or not capture.target_brightness_red:
            print("Missing calibration target readings in capture")
            return None
        
        # Calculate NDVI proxy
        result = await self.calculate_ndvi_proxy(
            leaf_brightness_nir=capture.target_brightness_nir * 1.5,  # Placeholder: leaf is brighter
            leaf_brightness_red=capture.target_brightness_red * 0.8,  # Placeholder: leaf absorbs red
            target_brightness_nir=capture.target_brightness_nir,
            target_brightness_red=capture.target_brightness_red,
            target_reflectance=calibration.target_reflectance_known
        )
        
        # Get crop context from zone or farm
        crop_type = "maize"  # TODO: Get from zone/farm data
        growth_stage = "vegetative"  # TODO: Get from farm data
        
        # Interpret health score
        interpretation = await self.interpret_health_score(
            result["health_score"],
            crop_type,
            growth_stage,
            db
        )
        
        # Create health reading
        health_reading = CropHealthReading(
            cctv_id=cctv.id,
            capture_id=capture.id,
            farm_id=cctv.farm_id,
            zone_id=cctv.zone_id,
            normalized_nir=result["normalized_nir"],
            normalized_red=result["normalized_red"],
            ndvi_proxy=result["ndvi_proxy"],
            health_score=result["health_score"],
            expected_health=interpretation["expected_health"],
            health_status=interpretation["status"],
            crop_type=crop_type,
            growth_stage=growth_stage,
            stress_detected=interpretation["alert_required"],
            stress_level=interpretation["stress_level"],
            stress_type=interpretation["stress_type"],
            alert_generated=False
        )
        
        db.add(health_reading)
        await db.flush()
        
        # Generate alert if needed
        if interpretation["alert_required"]:
            await self._generate_smart_alert(
                cctv, health_reading, interpretation, capture, db
            )
        
        return health_reading
    
    async def _get_active_calibration(
        self,
        cctv_id: int,
        db: AsyncSession
    ) -> Optional[CCTVCalibration]:
        """Get active calibration for CCTV"""
        result = await db.execute(
            select(CCTVCalibration)
            .where(
                CCTVCalibration.cctv_id == cctv_id,
                CCTVCalibration.is_active == True
            )
            .order_by(CCTVCalibration.calibrated_at.desc())
        )
        return result.scalar_one_or_none()
    
    async def _generate_smart_alert(
        self,
        cctv: CCTV,
        health_reading: CropHealthReading,
        interpretation: Dict,
        capture: CCTVCapture,
        db: AsyncSession
    ):
        """Generate smart, actionable alert"""
        # Determine severity
        if interpretation["stress_level"] == "high":
            severity = AlertSeverity.HIGH
        elif interpretation["stress_level"] == "medium":
            severity = AlertSeverity.MEDIUM
        else:
            severity = AlertSeverity.LOW
        
        # Create alert
        alert = Alert(
            farm_id=cctv.farm_id,
            zone_id=cctv.zone_id,
            sensor_id=cctv.id,  # CCTV acts as sensor
            alert_type="health_stress_detected",
            severity=severity,
            description=interpretation["message"],
            image_url=capture.image_url,
            latitude=cctv.latitude,
            longitude=cctv.longitude,
            confidence_score=health_reading.health_score,
            metadata={
                "health_score": health_reading.health_score,
                "expected_health": health_reading.expected_health,
                "ndvi_proxy": health_reading.ndvi_proxy,
                "stress_type": health_reading.stress_type,
                "crop_type": health_reading.crop_type,
                "growth_stage": health_reading.growth_stage
            }
        )
        
        db.add(alert)
        await db.flush()
        
        # Link alert to health reading
        health_reading.alert_generated = True
        health_reading.alert_id = alert.id
        
        # TODO: Trigger push notification to farmer
        # TODO: Send chatbot message
        
        return alert
    
    def calculate_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calculate distance between two GPS coordinates in meters
        Using Haversine formula
        """
        R = 6371000  # Earth's radius in meters
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_phi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) *
             math.sin(delta_lambda / 2) ** 2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c


# Singleton instance
virtual_multispectral_service = VirtualMultispectralService()
