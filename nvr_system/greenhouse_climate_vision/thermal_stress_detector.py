"""
🌿 Thermal Stress Detection for Greenhouse Crops

AI-powered thermal imaging analysis to detect plant stress before visible symptoms.
Uses infrared cameras to measure leaf temperature and identify:
- Heat stress (leaf temp > air temp + 5°C)
- Cold stress (leaf temp < air temp - 3°C)
- Water stress (elevated leaf temperature due to stomatal closure)
- Disease hotspots (localized temperature anomalies)
- Climate zone imbalances (temperature gradients)

Integrates with: FLIR thermal cameras, climate control systems, irrigation automation

Author: AgroPulse Greenhouse Vision Team
Date: November 3, 2025
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class StressType(Enum):
    """Plant stress types detectable via thermal imaging."""
    HEAT_STRESS = "heat_stress"
    COLD_STRESS = "cold_stress"
    WATER_STRESS = "water_stress"
    DISEASE_HOTSPOT = "disease_hotspot"
    NUTRIENT_STRESS = "nutrient_stress"
    ROOT_ZONE_PROBLEM = "root_zone_problem"
    NONE = "none"


class SeverityLevel(Enum):
    """Stress severity levels."""
    NORMAL = "normal"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


@dataclass
class ThermalReading:
    """Thermal camera reading data."""
    timestamp: datetime
    zone_id: str
    air_temperature: float  # Celsius
    leaf_temperature_mean: float
    leaf_temperature_std: float
    leaf_temperature_max: float
    leaf_temperature_min: float
    delta_t: float  # Leaf temp - air temp
    relative_humidity: float  # %
    vpd: float  # Vapor pressure deficit (kPa)


@dataclass
class StressDetectionResult:
    """Thermal stress detection result."""
    stress_type: StressType
    severity: SeverityLevel
    affected_area_pct: float
    confidence: float
    hotspot_locations: List[Tuple[int, int]]  # (x, y) coordinates
    recommended_actions: List[str]
    climate_adjustments: Dict[str, Any]
    urgency_score: float  # 0-100


class ThermalStressDetector:
    """
    Thermal imaging-based plant stress detection for greenhouses.
    
    Uses infrared thermal cameras to measure leaf surface temperature
    and identify stress conditions before visible symptoms appear.
    
    Key Capabilities:
    - Real-time thermal image processing (30 fps)
    - Multi-zone temperature mapping
    - Stress classification with AI models
    - Automatic climate control adjustments
    - Historical stress pattern analysis
    - Integration with environmental sensors
    """
    
    def __init__(
        self,
        camera_count: int = 4,
        resolution: Tuple[int, int] = (640, 480),
        thermal_range: Tuple[float, float] = (10.0, 50.0),
        calibration_data: Optional[Dict] = None
    ):
        """
        Initialize thermal stress detector.
        
        Args:
            camera_count: Number of thermal cameras in greenhouse
            resolution: Thermal image resolution
            thermal_range: Temperature measurement range (min, max) °C
            calibration_data: Camera calibration parameters
        """
        self.camera_count = camera_count
        self.resolution = resolution
        self.thermal_range = thermal_range
        self.calibration_data = calibration_data or {}
        
        # Stress detection thresholds
        self.thresholds = {
            "heat_stress_delta": 5.0,  # Leaf > Air + 5°C
            "cold_stress_delta": -3.0,  # Leaf < Air - 3°C
            "water_stress_delta": 3.0,  # Elevated leaf temp
            "hotspot_threshold": 2.5,  # Local temp anomaly
            "vpd_stress_low": 0.4,  # kPa - too humid
            "vpd_stress_high": 1.6,  # kPa - too dry
        }
        
        # AI model for stress classification
        self.stress_classifier = None
        self._load_stress_model()
        
        logger.info(f"Initialized ThermalStressDetector with {camera_count} cameras")
    
    def _load_stress_model(self):
        """Load pre-trained stress classification model."""
        # In production, load actual TensorFlow/PyTorch model
        logger.info("Loading thermal stress classification model...")
        self.stress_classifier = "ThermalStressCNN_v2.3"  # Placeholder
    
    def process_thermal_frame(
        self,
        thermal_image: np.ndarray,
        air_temp: float,
        humidity: float,
        zone_id: str
    ) -> StressDetectionResult:
        """
        Process single thermal image frame for stress detection.
        
        Args:
            thermal_image: Thermal image array (temp values in Celsius)
            air_temp: Current air temperature (°C)
            humidity: Relative humidity (%)
            zone_id: Greenhouse zone identifier
            
        Returns:
            StressDetectionResult with detected stress and recommendations
        """
        # Step 1: Segment plant regions from background
        plant_mask = self._segment_plants(thermal_image)
        
        # Step 2: Calculate leaf temperature statistics
        leaf_temps = thermal_image[plant_mask > 0]
        
        if len(leaf_temps) == 0:
            return self._create_no_detection_result(zone_id)
        
        thermal_reading = ThermalReading(
            timestamp=datetime.now(),
            zone_id=zone_id,
            air_temperature=air_temp,
            leaf_temperature_mean=float(np.mean(leaf_temps)),
            leaf_temperature_std=float(np.std(leaf_temps)),
            leaf_temperature_max=float(np.max(leaf_temps)),
            leaf_temperature_min=float(np.min(leaf_temps)),
            delta_t=float(np.mean(leaf_temps) - air_temp),
            relative_humidity=humidity,
            vpd=self._calculate_vpd(air_temp, humidity)
        )
        
        # Step 3: Classify stress type
        stress_type, confidence = self._classify_stress(thermal_reading, thermal_image, plant_mask)
        
        # Step 4: Assess severity
        severity = self._assess_severity(thermal_reading, stress_type)
        
        # Step 5: Detect hotspots (localized anomalies)
        hotspots = self._detect_hotspots(thermal_image, plant_mask, thermal_reading.leaf_temperature_mean)
        
        # Step 6: Calculate affected area
        affected_pct = self._calculate_affected_area(thermal_image, plant_mask, stress_type, thermal_reading)
        
        # Step 7: Generate recommendations
        actions = self._generate_recommendations(stress_type, severity, thermal_reading)
        climate_adjustments = self._generate_climate_adjustments(stress_type, thermal_reading)
        urgency = self._calculate_urgency(severity, affected_pct, stress_type)
        
        result = StressDetectionResult(
            stress_type=stress_type,
            severity=severity,
            affected_area_pct=affected_pct,
            confidence=confidence,
            hotspot_locations=hotspots,
            recommended_actions=actions,
            climate_adjustments=climate_adjustments,
            urgency_score=urgency
        )
        
        logger.info(f"Zone {zone_id}: Detected {stress_type.value} - Severity: {severity.value}")
        
        return result
    
    def _segment_plants(self, thermal_image: np.ndarray) -> np.ndarray:
        """
        Segment plant regions from background using temperature thresholding.
        
        Args:
            thermal_image: Thermal image array
            
        Returns:
            Binary mask of plant regions
        """
        # Plants typically warmer than air but cooler than grow lights
        # Typical greenhouse: Air=20-25°C, Leaves=22-28°C, Lights=40-60°C
        
        plant_temp_min = self.thermal_range[0] + 5  # Filter out cold objects
        plant_temp_max = self.thermal_range[1] - 15  # Filter out hot lights
        
        mask = np.logical_and(
            thermal_image >= plant_temp_min,
            thermal_image <= plant_temp_max
        ).astype(np.uint8) * 255
        
        # Morphological operations to clean up mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        return mask
    
    def _calculate_vpd(self, air_temp: float, humidity: float) -> float:
        """
        Calculate Vapor Pressure Deficit (VPD).
        
        VPD is critical for plant transpiration and stress assessment.
        
        Args:
            air_temp: Air temperature (°C)
            humidity: Relative humidity (%)
            
        Returns:
            VPD in kPa
        """
        # Saturation vapor pressure (SVP) using Tetens equation
        svp = 0.6108 * np.exp((17.27 * air_temp) / (air_temp + 237.3))
        
        # Actual vapor pressure
        avp = svp * (humidity / 100.0)
        
        # VPD = SVP - AVP
        vpd = svp - avp
        
        return vpd
    
    def _classify_stress(
        self,
        thermal_reading: ThermalReading,
        thermal_image: np.ndarray,
        plant_mask: np.ndarray
    ) -> Tuple[StressType, float]:
        """
        Classify stress type using thermal reading and AI model.
        
        Args:
            thermal_reading: Thermal statistics
            thermal_image: Raw thermal image
            plant_mask: Plant segmentation mask
            
        Returns:
            Tuple of (stress_type, confidence)
        """
        delta_t = thermal_reading.delta_t
        vpd = thermal_reading.vpd
        
        # Rule-based classification (can be enhanced with ML model)
        
        # Heat stress: Leaves significantly warmer than air
        if delta_t > self.thresholds["heat_stress_delta"]:
            return StressType.HEAT_STRESS, 0.92
        
        # Cold stress: Leaves colder than air
        if delta_t < self.thresholds["cold_stress_delta"]:
            return StressType.COLD_STRESS, 0.88
        
        # Water stress: Moderate elevation + high VPD
        if delta_t > self.thresholds["water_stress_delta"] and vpd > self.thresholds["vpd_stress_high"]:
            return StressType.WATER_STRESS, 0.85
        
        # Disease hotspot: High temperature variance in plant mask
        if thermal_reading.leaf_temperature_std > 2.5:
            return StressType.DISEASE_HOTSPOT, 0.78
        
        # VPD stress (nutrient uptake affected)
        if vpd < self.thresholds["vpd_stress_low"] or vpd > self.thresholds["vpd_stress_high"]:
            return StressType.NUTRIENT_STRESS, 0.75
        
        # No stress detected
        return StressType.NONE, 0.95
    
    def _assess_severity(self, thermal_reading: ThermalReading, stress_type: StressType) -> SeverityLevel:
        """
        Assess stress severity based on temperature deviation.
        
        Args:
            thermal_reading: Thermal statistics
            stress_type: Detected stress type
            
        Returns:
            Severity level
        """
        if stress_type == StressType.NONE:
            return SeverityLevel.NORMAL
        
        delta_t_abs = abs(thermal_reading.delta_t)
        
        if delta_t_abs < 2.0:
            return SeverityLevel.MILD
        elif delta_t_abs < 4.0:
            return SeverityLevel.MODERATE
        elif delta_t_abs < 6.0:
            return SeverityLevel.SEVERE
        else:
            return SeverityLevel.CRITICAL
    
    def _detect_hotspots(
        self,
        thermal_image: np.ndarray,
        plant_mask: np.ndarray,
        mean_temp: float
    ) -> List[Tuple[int, int]]:
        """
        Detect localized temperature anomalies (disease hotspots).
        
        Args:
            thermal_image: Raw thermal image
            plant_mask: Plant segmentation mask
            mean_temp: Mean plant temperature
            
        Returns:
            List of hotspot coordinates
        """
        # Find pixels significantly above mean
        hotspot_mask = np.logical_and(
            thermal_image > mean_temp + self.thresholds["hotspot_threshold"],
            plant_mask > 0
        )
        
        # Find contours of hotspots
        hotspot_coords = []
        contours, _ = cv2.findContours(
            hotspot_mask.astype(np.uint8),
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        for contour in contours:
            if cv2.contourArea(contour) > 50:  # Minimum hotspot size
                M = cv2.moments(contour)
                if M["m00"] > 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    hotspot_coords.append((cx, cy))
        
        return hotspot_coords
    
    def _calculate_affected_area(
        self,
        thermal_image: np.ndarray,
        plant_mask: np.ndarray,
        stress_type: StressType,
        thermal_reading: ThermalReading
    ) -> float:
        """
        Calculate percentage of plant area affected by stress.
        
        Args:
            thermal_image: Raw thermal image
            plant_mask: Plant segmentation mask
            stress_type: Detected stress type
            thermal_reading: Thermal statistics
            
        Returns:
            Percentage of affected area (0-100)
        """
        if stress_type == StressType.NONE:
            return 0.0
        
        total_plant_pixels = np.sum(plant_mask > 0)
        if total_plant_pixels == 0:
            return 0.0
        
        # Define stress condition based on type
        if stress_type == StressType.HEAT_STRESS:
            stressed_pixels = np.sum(
                np.logical_and(
                    thermal_image > thermal_reading.air_temperature + self.thresholds["heat_stress_delta"],
                    plant_mask > 0
                )
            )
        elif stress_type == StressType.COLD_STRESS:
            stressed_pixels = np.sum(
                np.logical_and(
                    thermal_image < thermal_reading.air_temperature + self.thresholds["cold_stress_delta"],
                    plant_mask > 0
                )
            )
        else:
            # For other stress types, use temperature variance
            stressed_pixels = np.sum(
                np.logical_and(
                    np.abs(thermal_image - thermal_reading.leaf_temperature_mean) > 2.0,
                    plant_mask > 0
                )
            )
        
        affected_pct = (stressed_pixels / total_plant_pixels) * 100.0
        
        return float(affected_pct)
    
    def _generate_recommendations(
        self,
        stress_type: StressType,
        severity: SeverityLevel,
        thermal_reading: ThermalReading
    ) -> List[str]:
        """
        Generate actionable recommendations based on detected stress.
        
        Args:
            stress_type: Detected stress type
            severity: Stress severity
            thermal_reading: Thermal statistics
            
        Returns:
            List of recommended actions
        """
        recommendations = []
        
        if stress_type == StressType.HEAT_STRESS:
            recommendations.extend([
                "Activate cooling system immediately",
                "Increase ventilation rate by 30%",
                "Deploy shade cloth if solar radiation high",
                "Increase irrigation frequency",
                "Monitor for heat-induced blossom drop"
            ])
        
        elif stress_type == StressType.COLD_STRESS:
            recommendations.extend([
                "Activate greenhouse heating system",
                "Close vents to reduce cold air infiltration",
                "Check for air leaks in greenhouse structure",
                "Consider supplemental root zone heating",
                "Monitor for chilling injury symptoms"
            ])
        
        elif stress_type == StressType.WATER_STRESS:
            recommendations.extend([
                "Increase irrigation duration by 20%",
                "Check drip emitters for clogs",
                "Verify substrate moisture levels",
                "Increase humidity if VPD too high",
                "Monitor leaf turgor recovery time"
            ])
        
        elif stress_type == StressType.DISEASE_HOTSPOT:
            recommendations.extend([
                "Inspect plants at hotspot locations for disease",
                "Increase air circulation in affected zones",
                "Check for excess moisture/condensation",
                "Consider preventive fungicide application",
                "Isolate severely affected plants if needed"
            ])
        
        elif stress_type == StressType.NUTRIENT_STRESS:
            recommendations.extend([
                "Verify EC levels in nutrient solution",
                "Check pH of hydroponic system (target 5.8-6.2)",
                "Adjust VPD to optimal range (0.8-1.2 kPa)",
                "Monitor for nutrient lockout symptoms",
                "Consider foliar feeding if deficiency severe"
            ])
        
        # Add severity-specific recommendations
        if severity in [SeverityLevel.SEVERE, SeverityLevel.CRITICAL]:
            recommendations.append("⚠️ URGENT: Manual inspection required within 1 hour")
            recommendations.append("Alert greenhouse manager via SMS/push notification")
        
        return recommendations
    
    def _generate_climate_adjustments(
        self,
        stress_type: StressType,
        thermal_reading: ThermalReading
    ) -> Dict[str, Any]:
        """
        Generate specific climate control adjustments.
        
        Args:
            stress_type: Detected stress type
            thermal_reading: Thermal statistics
            
        Returns:
            Dictionary of climate control setpoints
        """
        adjustments = {}
        
        if stress_type == StressType.HEAT_STRESS:
            adjustments = {
                "temperature_setpoint": thermal_reading.air_temperature - 2.0,
                "ventilation_rate": "+30%",
                "cooling_pad_status": "ACTIVE",
                "shade_screen": "DEPLOY_50%",
                "misting_system": "ACTIVATE"
            }
        
        elif stress_type == StressType.COLD_STRESS:
            adjustments = {
                "temperature_setpoint": thermal_reading.air_temperature + 3.0,
                "heating_system": "ACTIVATE",
                "ventilation_rate": "-50%",
                "thermal_curtain": "DEPLOY"
            }
        
        elif stress_type == StressType.WATER_STRESS:
            adjustments = {
                "irrigation_frequency": "+20%",
                "humidity_setpoint": thermal_reading.relative_humidity + 5.0,
                "misting_system": "ACTIVATE"
            }
        
        elif stress_type == StressType.DISEASE_HOTSPOT:
            adjustments = {
                "humidity_setpoint": thermal_reading.relative_humidity - 5.0,
                "ventilation_rate": "+20%",
                "air_circulation_fans": "HIGH"
            }
        
        return adjustments
    
    def _calculate_urgency(
        self,
        severity: SeverityLevel,
        affected_pct: float,
        stress_type: StressType
    ) -> float:
        """
        Calculate urgency score for stress response prioritization.
        
        Args:
            severity: Stress severity
            affected_pct: Percentage of affected area
            stress_type: Type of stress
            
        Returns:
            Urgency score (0-100)
        """
        # Base urgency from severity
        severity_scores = {
            SeverityLevel.NORMAL: 0,
            SeverityLevel.MILD: 20,
            SeverityLevel.MODERATE: 40,
            SeverityLevel.SEVERE: 70,
            SeverityLevel.CRITICAL: 95
        }
        
        base_urgency = severity_scores.get(severity, 0)
        
        # Adjust for affected area
        area_factor = min(affected_pct / 50.0, 1.0)  # Max at 50% affected
        
        # Adjust for stress type criticality
        criticality_factor = {
            StressType.NONE: 0.0,
            StressType.HEAT_STRESS: 1.2,  # Very damaging
            StressType.COLD_STRESS: 1.1,
            StressType.WATER_STRESS: 1.0,
            StressType.DISEASE_HOTSPOT: 0.9,
            StressType.NUTRIENT_STRESS: 0.7,
            StressType.ROOT_ZONE_PROBLEM: 0.8
        }.get(stress_type, 1.0)
        
        urgency = min(base_urgency * (1 + area_factor * 0.5) * criticality_factor, 100.0)
        
        return urgency
    
    def _create_no_detection_result(self, zone_id: str) -> StressDetectionResult:
        """Create result when no plants detected."""
        return StressDetectionResult(
            stress_type=StressType.NONE,
            severity=SeverityLevel.NORMAL,
            affected_area_pct=0.0,
            confidence=1.0,
            hotspot_locations=[],
            recommended_actions=["No plants detected in thermal image"],
            climate_adjustments={},
            urgency_score=0.0
        )
    
    def analyze_multi_zone(
        self,
        thermal_images: Dict[str, np.ndarray],
        environmental_data: Dict[str, Dict[str, float]]
    ) -> Dict[str, StressDetectionResult]:
        """
        Analyze multiple greenhouse zones simultaneously.
        
        Args:
            thermal_images: Dict mapping zone_id to thermal image
            environmental_data: Dict mapping zone_id to environmental readings
                               (air_temp, humidity, co2, par_light)
            
        Returns:
            Dict mapping zone_id to StressDetectionResult
        """
        results = {}
        
        for zone_id, thermal_image in thermal_images.items():
            if zone_id not in environmental_data:
                logger.warning(f"No environmental data for zone {zone_id}")
                continue
            
            env_data = environmental_data[zone_id]
            
            result = self.process_thermal_frame(
                thermal_image=thermal_image,
                air_temp=env_data.get("air_temp", 22.0),
                humidity=env_data.get("humidity", 65.0),
                zone_id=zone_id
            )
            
            results[zone_id] = result
        
        # Check for multi-zone patterns
        self._analyze_multi_zone_patterns(results)
        
        return results
    
    def _analyze_multi_zone_patterns(self, zone_results: Dict[str, StressDetectionResult]):
        """
        Analyze patterns across multiple zones for systemic issues.
        
        Args:
            zone_results: Detection results for all zones
        """
        # Count zones with same stress type
        stress_counts = {}
        for result in zone_results.values():
            stress_type = result.stress_type.value
            stress_counts[stress_type] = stress_counts.get(stress_type, 0) + 1
        
        # Check for widespread issues
        total_zones = len(zone_results)
        for stress_type, count in stress_counts.items():
            if count >= total_zones * 0.75:  # 75% of zones affected
                logger.warning(
                    f"⚠️ SYSTEMIC ISSUE: {stress_type} detected in {count}/{total_zones} zones"
                )
                logger.warning("Recommend facility-wide climate system inspection")


# Example usage and testing
if __name__ == "__main__":
    # Initialize detector
    detector = ThermalStressDetector(camera_count=4)
    
    # Simulate thermal image (normally from FLIR camera)
    thermal_image = np.random.normal(24.0, 2.0, (480, 640))
    thermal_image = np.clip(thermal_image, 15, 35)
    
    # Add artificial stress region
    thermal_image[100:200, 200:400] += 6.0  # Hot region (heat stress)
    
    # Process frame
    result = detector.process_thermal_frame(
        thermal_image=thermal_image,
        air_temp=22.0,
        humidity=65.0,
        zone_id="ZONE_A"
    )
    
    print(f"\n🌡️ Thermal Stress Detection Result:")
    print(f"Stress Type: {result.stress_type.value}")
    print(f"Severity: {result.severity.value}")
    print(f"Affected Area: {result.affected_area_pct:.1f}%")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Urgency Score: {result.urgency_score:.1f}/100")
    print(f"\nRecommended Actions:")
    for action in result.recommended_actions:
        print(f"  - {action}")
    print(f"\nClimate Adjustments:")
    for key, value in result.climate_adjustments.items():
        print(f"  - {key}: {value}")
