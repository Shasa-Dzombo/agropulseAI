"""
Greenhouse Humidity & Condensation Analysis Module

Analyzes humidity distribution, condensation risk, and mold/disease potential
in controlled environment horticulture using thermal-visual fusion.

Features:
- Dewpoint mapping across greenhouse zones
- Condensation risk assessment (surfaces, leaves, fruit)
- Mold growth potential prediction
- Botrytis gray mold early detection
- VPD (Vapor Pressure Deficit) spatial mapping
- Microbial risk scoring
- Dehumidification system optimization

Author: AgroPulse Greenhouse Vision Team
Date: November 3, 2025
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CondensationRisk(Enum):
    """Condensation risk levels for greenhouse surfaces"""
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class MoldRiskLevel(Enum):
    """Mold growth potential levels"""
    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    SEVERE = "severe"


class SurfaceType(Enum):
    """Types of greenhouse surfaces analyzed"""
    PLANT_LEAF = "plant_leaf"
    FRUIT_SURFACE = "fruit_surface"
    GREENHOUSE_GLAZING = "greenhouse_glazing"
    STRUCTURAL_BEAM = "structural_beam"
    IRRIGATION_LINE = "irrigation_line"
    GROWING_MEDIUM = "growing_medium"
    FLOOR = "floor"
    UNKNOWN = "unknown"


@dataclass
class DewpointReading:
    """Dewpoint calculation for specific location"""
    x: int
    y: int
    temperature: float  # Celsius
    humidity: float  # Relative humidity %
    dewpoint: float  # Celsius
    condensation_risk: CondensationRisk
    surface_type: SurfaceType
    timestamp: datetime


@dataclass
class MoldRiskZone:
    """Zone with elevated mold growth potential"""
    zone_id: str
    center_x: int
    center_y: int
    area_pixels: int
    avg_temperature: float
    avg_humidity: float
    avg_dewpoint: float
    hours_at_risk: float  # Hours in conducive conditions
    mold_risk_level: MoldRiskLevel
    affected_crops: List[str]
    recommendations: List[str]


@dataclass
class CondensationEvent:
    """Detected condensation event"""
    event_id: str
    location_x: int
    location_y: int
    surface_type: SurfaceType
    severity: float  # 0-1
    duration_minutes: float
    affected_area_m2: float
    disease_risk: bool
    timestamp: datetime


@dataclass
class HumidityAnalysisResult:
    """Complete humidity and condensation analysis output"""
    timestamp: datetime
    greenhouse_zone: str
    
    # Environmental readings
    avg_air_temp: float
    avg_humidity: float
    avg_dewpoint: float
    avg_vpd: float  # kPa
    
    # Spatial distribution
    temp_uniformity: float  # Coefficient 0-1
    humidity_uniformity: float
    dewpoint_map: np.ndarray
    vpd_map: np.ndarray
    
    # Risk assessment
    condensation_events: List[CondensationEvent]
    mold_risk_zones: List[MoldRiskZone]
    overall_mold_risk: MoldRiskLevel
    disease_outbreak_probability: float  # 0-1
    
    # Recommendations
    dehumidification_needed: bool
    target_humidity: float
    air_circulation_score: float  # 0-100
    heating_recommendation: Optional[str]
    ventilation_recommendation: Optional[str]
    
    # Visualization
    condensation_heatmap: np.ndarray
    mold_risk_overlay: np.ndarray


class HumidityCondensationAnalyzer:
    """
    Analyzes humidity distribution and condensation risk in greenhouses.
    
    Uses thermal imaging, humidity sensors, and computer vision to detect
    moisture-related issues that can lead to fungal diseases like Botrytis.
    """
    
    def __init__(self, 
                 greenhouse_area_m2: float = 500.0,
                 crop_type: str = "tomato",
                 detection_sensitivity: float = 0.75):
        """
        Initialize humidity analyzer.
        
        Args:
            greenhouse_area_m2: Total greenhouse area
            crop_type: Type of crop being grown
            detection_sensitivity: Sensitivity for condensation detection (0-1)
        """
        self.greenhouse_area_m2 = greenhouse_area_m2
        self.crop_type = crop_type
        self.detection_sensitivity = detection_sensitivity
        
        # Crop-specific thresholds
        self.crop_thresholds = self._load_crop_thresholds()
        
        # Historical data for trend analysis
        self.history_dewpoint: List[float] = []
        self.history_vpd: List[float] = []
        self.condensation_history: List[CondensationEvent] = []
        
        # Mold growth model parameters
        self.mold_growth_threshold_hours = 4.0  # Hours of high humidity
        
        logger.info(f"Initialized HumidityCondensationAnalyzer for {crop_type}")
    
    def _load_crop_thresholds(self) -> Dict:
        """Load crop-specific humidity and disease thresholds"""
        thresholds = {
            "tomato": {
                "optimal_humidity": (60, 75),
                "optimal_vpd": (0.8, 1.2),
                "mold_risk_humidity": 85,
                "botrytis_risk_temp": (15, 25),
                "leaf_wetness_hours": 6
            },
            "lettuce": {
                "optimal_humidity": (50, 70),
                "optimal_vpd": (0.6, 1.0),
                "mold_risk_humidity": 80,
                "botrytis_risk_temp": (10, 20),
                "leaf_wetness_hours": 4
            },
            "cucumber": {
                "optimal_humidity": (65, 80),
                "optimal_vpd": (0.7, 1.1),
                "mold_risk_humidity": 90,
                "powdery_mildew_rh": 50,  # Can occur at lower RH
                "leaf_wetness_hours": 8
            },
            "pepper": {
                "optimal_humidity": (60, 75),
                "optimal_vpd": (0.8, 1.3),
                "mold_risk_humidity": 85,
                "anthracnose_risk_temp": (20, 30),
                "leaf_wetness_hours": 5
            },
            "strawberry": {
                "optimal_humidity": (55, 75),
                "optimal_vpd": (0.7, 1.2),
                "mold_risk_humidity": 85,
                "botrytis_risk_temp": (15, 25),
                "leaf_wetness_hours": 3  # Very susceptible
            },
            "basil": {
                "optimal_humidity": (50, 70),
                "optimal_vpd": (0.8, 1.2),
                "mold_risk_humidity": 80,
                "downy_mildew_rh": 85,
                "leaf_wetness_hours": 4
            }
        }
        return thresholds.get(self.crop_type, thresholds["tomato"])
    
    def calculate_dewpoint(self, temperature: float, humidity: float) -> float:
        """
        Calculate dewpoint temperature using Magnus formula.
        
        Args:
            temperature: Air temperature (Celsius)
            humidity: Relative humidity (%)
        
        Returns:
            Dewpoint temperature (Celsius)
        """
        a = 17.27
        b = 237.7
        
        alpha = ((a * temperature) / (b + temperature)) + np.log(humidity / 100.0)
        dewpoint = (b * alpha) / (a - alpha)
        
        return dewpoint
    
    def calculate_vpd(self, temperature: float, humidity: float) -> float:
        """
        Calculate Vapor Pressure Deficit (VPD).
        
        Args:
            temperature: Air temperature (Celsius)
            humidity: Relative humidity (%)
        
        Returns:
            VPD in kPa
        """
        # Saturation vapor pressure (Tetens equation)
        svp = 0.6108 * np.exp((17.27 * temperature) / (temperature + 237.3))
        
        # Actual vapor pressure
        avp = svp * (humidity / 100.0)
        
        # VPD
        vpd = svp - avp
        
        return vpd
    
    def assess_condensation_risk(self, 
                                  surface_temp: float, 
                                  air_temp: float, 
                                  humidity: float,
                                  surface_type: SurfaceType) -> CondensationRisk:
        """
        Assess condensation risk for a surface.
        
        Args:
            surface_temp: Surface temperature (Celsius)
            air_temp: Air temperature (Celsius)
            humidity: Relative humidity (%)
            surface_type: Type of surface
        
        Returns:
            CondensationRisk level
        """
        dewpoint = self.calculate_dewpoint(air_temp, humidity)
        temp_diff = surface_temp - dewpoint
        
        # Surface-specific thresholds
        if surface_type == SurfaceType.PLANT_LEAF:
            # Leaves are at high risk due to transpiration
            if temp_diff < -1.0:
                return CondensationRisk.CRITICAL
            elif temp_diff < 0.5:
                return CondensationRisk.HIGH
            elif temp_diff < 1.5:
                return CondensationRisk.MODERATE
            elif temp_diff < 3.0:
                return CondensationRisk.LOW
            else:
                return CondensationRisk.NONE
        
        elif surface_type == SurfaceType.FRUIT_SURFACE:
            # Fruit condensation increases disease risk
            if temp_diff < -0.5:
                return CondensationRisk.CRITICAL
            elif temp_diff < 1.0:
                return CondensationRisk.HIGH
            elif temp_diff < 2.0:
                return CondensationRisk.MODERATE
            elif temp_diff < 3.5:
                return CondensationRisk.LOW
            else:
                return CondensationRisk.NONE
        
        elif surface_type == SurfaceType.GREENHOUSE_GLAZING:
            # Glazing condensation drips onto plants
            if temp_diff < 0:
                return CondensationRisk.HIGH
            elif temp_diff < 1.0:
                return CondensationRisk.MODERATE
            elif temp_diff < 2.0:
                return CondensationRisk.LOW
            else:
                return CondensationRisk.NONE
        
        else:
            # Generic surface
            if temp_diff < 0:
                return CondensationRisk.HIGH
            elif temp_diff < 1.5:
                return CondensationRisk.MODERATE
            elif temp_diff < 3.0:
                return CondensationRisk.LOW
            else:
                return CondensationRisk.NONE
    
    def detect_condensation_events(self,
                                   thermal_image: np.ndarray,
                                   visual_image: np.ndarray,
                                   air_temp: float,
                                   humidity: float,
                                   surface_segmentation: np.ndarray) -> List[CondensationEvent]:
        """
        Detect active condensation events in the greenhouse.
        
        Args:
            thermal_image: Thermal image (temperature in Celsius)
            visual_image: RGB visual image
            air_temp: Ambient air temperature
            humidity: Ambient relative humidity
            surface_segmentation: Segmented surface types
        
        Returns:
            List of detected condensation events
        """
        events = []
        dewpoint = self.calculate_dewpoint(air_temp, humidity)
        
        # Find areas where surface temp is below dewpoint
        condensation_mask = thermal_image < (dewpoint - 0.5)
        
        # Apply morphological operations to clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        condensation_mask = cv2.morphologyEx(
            condensation_mask.astype(np.uint8), 
            cv2.MORPH_CLOSE, 
            kernel
        )
        
        # Find connected components
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            condensation_mask, connectivity=8
        )
        
        # Analyze each condensation region
        for i in range(1, num_labels):  # Skip background
            area = stats[i, cv2.CC_STAT_AREA]
            
            # Filter small noise
            if area < 50:
                continue
            
            # Get region properties
            mask = (labels == i).astype(np.uint8)
            region_temps = thermal_image[mask > 0]
            region_surface_types = surface_segmentation[mask > 0]
            
            avg_temp = np.mean(region_temps)
            severity = (dewpoint - avg_temp) / 5.0  # Normalize
            severity = np.clip(severity, 0, 1)
            
            # Determine dominant surface type
            surface_type = self._get_dominant_surface_type(region_surface_types)
            
            # Assess disease risk
            disease_risk = (
                severity > 0.6 and 
                surface_type in [SurfaceType.PLANT_LEAF, SurfaceType.FRUIT_SURFACE]
            )
            
            # Calculate affected area in m²
            pixels_per_m2 = (thermal_image.shape[0] * thermal_image.shape[1]) / self.greenhouse_area_m2
            affected_area = area / pixels_per_m2
            
            event = CondensationEvent(
                event_id=f"COND_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}",
                location_x=int(centroids[i][0]),
                location_y=int(centroids[i][1]),
                surface_type=surface_type,
                severity=severity,
                duration_minutes=10.0,  # Estimate based on monitoring interval
                affected_area_m2=affected_area,
                disease_risk=disease_risk,
                timestamp=datetime.now()
            )
            
            events.append(event)
        
        return events
    
    def _get_dominant_surface_type(self, surface_labels: np.ndarray) -> SurfaceType:
        """Get the most common surface type in a region"""
        if len(surface_labels) == 0:
            return SurfaceType.UNKNOWN
        
        # Get most frequent label
        values, counts = np.unique(surface_labels, return_counts=True)
        dominant_label = values[np.argmax(counts)]
        
        # Map to SurfaceType enum (assuming labels are integers)
        label_map = {
            0: SurfaceType.UNKNOWN,
            1: SurfaceType.PLANT_LEAF,
            2: SurfaceType.FRUIT_SURFACE,
            3: SurfaceType.GREENHOUSE_GLAZING,
            4: SurfaceType.STRUCTURAL_BEAM,
            5: SurfaceType.IRRIGATION_LINE,
            6: SurfaceType.GROWING_MEDIUM,
            7: SurfaceType.FLOOR
        }
        
        return label_map.get(dominant_label, SurfaceType.UNKNOWN)
    
    def assess_mold_risk(self,
                        temperature_map: np.ndarray,
                        humidity_map: np.ndarray,
                        hours_at_conditions: float = 4.0) -> List[MoldRiskZone]:
        """
        Assess mold growth risk across greenhouse zones.
        
        Args:
            temperature_map: Spatial temperature distribution
            humidity_map: Spatial humidity distribution
            hours_at_conditions: Hours the conditions have persisted
        
        Returns:
            List of zones with mold risk
        """
        risk_zones = []
        
        # Get crop-specific thresholds
        mold_risk_rh = self.crop_thresholds.get("mold_risk_humidity", 85)
        
        # Create risk map
        risk_mask = humidity_map > mold_risk_rh
        
        # For Botrytis, also check temperature range
        if "botrytis_risk_temp" in self.crop_thresholds:
            temp_min, temp_max = self.crop_thresholds["botrytis_risk_temp"]
            temp_risk = (temperature_map >= temp_min) & (temperature_map <= temp_max)
            risk_mask = risk_mask & temp_risk
        
        # Find risk zones
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        risk_mask = cv2.morphologyEx(risk_mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel)
        
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            risk_mask, connectivity=8
        )
        
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            
            if area < 100:  # Filter small regions
                continue
            
            # Get zone statistics
            mask = (labels == i)
            zone_temps = temperature_map[mask]
            zone_humidity = humidity_map[mask]
            
            avg_temp = np.mean(zone_temps)
            avg_humidity = np.mean(zone_humidity)
            avg_dewpoint = self.calculate_dewpoint(avg_temp, avg_humidity)
            
            # Determine mold risk level
            if avg_humidity > 90 and hours_at_conditions > 6:
                risk_level = MoldRiskLevel.SEVERE
            elif avg_humidity > 85 and hours_at_conditions > 4:
                risk_level = MoldRiskLevel.HIGH
            elif avg_humidity > 80 and hours_at_conditions > 3:
                risk_level = MoldRiskLevel.MODERATE
            elif avg_humidity > 75:
                risk_level = MoldRiskLevel.LOW
            else:
                risk_level = MoldRiskLevel.MINIMAL
            
            # Generate recommendations
            recommendations = self._generate_mold_recommendations(
                risk_level, avg_humidity, avg_temp
            )
            
            zone = MoldRiskZone(
                zone_id=f"MOLD_ZONE_{i}",
                center_x=int(centroids[i][0]),
                center_y=int(centroids[i][1]),
                area_pixels=area,
                avg_temperature=avg_temp,
                avg_humidity=avg_humidity,
                avg_dewpoint=avg_dewpoint,
                hours_at_risk=hours_at_conditions,
                mold_risk_level=risk_level,
                affected_crops=[self.crop_type],
                recommendations=recommendations
            )
            
            risk_zones.append(zone)
        
        return risk_zones
    
    def _generate_mold_recommendations(self, 
                                      risk_level: MoldRiskLevel,
                                      humidity: float,
                                      temperature: float) -> List[str]:
        """Generate actionable recommendations for mold prevention"""
        recommendations = []
        
        if risk_level in [MoldRiskLevel.SEVERE, MoldRiskLevel.HIGH]:
            recommendations.append("URGENT: Increase ventilation immediately")
            recommendations.append("Activate dehumidification system")
            recommendations.append("Increase heating by 2-3°C to lower RH")
            recommendations.append("Inspect plants for early disease symptoms")
            
            if temperature < 18:
                recommendations.append("Raise temperature to reduce condensation risk")
        
        elif risk_level == MoldRiskLevel.MODERATE:
            recommendations.append("Increase air circulation with HAF fans")
            recommendations.append("Monitor humidity closely over next 2 hours")
            recommendations.append(f"Target humidity: {self.crop_thresholds['optimal_humidity'][1]}%")
        
        elif risk_level == MoldRiskLevel.LOW:
            recommendations.append("Maintain current ventilation levels")
            recommendations.append("Continue routine monitoring")
        
        return recommendations
    
    def create_visualizations(self,
                             thermal_image: np.ndarray,
                             humidity_map: np.ndarray,
                             condensation_events: List[CondensationEvent],
                             mold_risk_zones: List[MoldRiskZone]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create visualization overlays for condensation and mold risk.
        
        Returns:
            Tuple of (condensation_heatmap, mold_risk_overlay)
        """
        height, width = thermal_image.shape
        
        # Create condensation heatmap
        condensation_heatmap = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Apply colormap to thermal image
        thermal_normalized = cv2.normalize(thermal_image, None, 0, 255, cv2.NORM_MINMAX)
        thermal_colored = cv2.applyColorMap(thermal_normalized.astype(np.uint8), cv2.COLORMAP_JET)
        condensation_heatmap = thermal_colored.copy()
        
        # Overlay condensation events
        for event in condensation_events:
            color = self._get_risk_color(event.severity)
            radius = max(10, int(np.sqrt(event.affected_area_m2) * 10))
            cv2.circle(condensation_heatmap, (event.location_x, event.location_y), 
                      radius, color, 2)
            cv2.putText(condensation_heatmap, f"{event.severity:.1f}", 
                       (event.location_x + 5, event.location_y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # Create mold risk overlay
        mold_risk_overlay = np.zeros((height, width, 3), dtype=np.uint8)
        humidity_normalized = cv2.normalize(humidity_map, None, 0, 255, cv2.NORM_MINMAX)
        humidity_colored = cv2.applyColorMap(humidity_normalized.astype(np.uint8), cv2.COLORMAP_AUTUMN)
        mold_risk_overlay = humidity_colored.copy()
        
        # Overlay mold risk zones
        for zone in mold_risk_zones:
            color = self._get_mold_risk_color(zone.mold_risk_level)
            cv2.circle(mold_risk_overlay, (zone.center_x, zone.center_y), 20, color, -1)
            cv2.putText(mold_risk_overlay, zone.mold_risk_level.value.upper(),
                       (zone.center_x - 30, zone.center_y + 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return condensation_heatmap, mold_risk_overlay
    
    def _get_risk_color(self, severity: float) -> Tuple[int, int, int]:
        """Get BGR color for risk severity (0-1)"""
        if severity > 0.8:
            return (0, 0, 255)  # Red
        elif severity > 0.6:
            return (0, 128, 255)  # Orange
        elif severity > 0.4:
            return (0, 255, 255)  # Yellow
        else:
            return (0, 255, 0)  # Green
    
    def _get_mold_risk_color(self, risk_level: MoldRiskLevel) -> Tuple[int, int, int]:
        """Get BGR color for mold risk level"""
        color_map = {
            MoldRiskLevel.MINIMAL: (0, 255, 0),  # Green
            MoldRiskLevel.LOW: (0, 255, 255),  # Yellow
            MoldRiskLevel.MODERATE: (0, 165, 255),  # Orange
            MoldRiskLevel.HIGH: (0, 69, 255),  # Red-Orange
            MoldRiskLevel.SEVERE: (0, 0, 255)  # Red
        }
        return color_map.get(risk_level, (128, 128, 128))
    
    def analyze(self,
               thermal_image: np.ndarray,
               visual_image: np.ndarray,
               air_temp: float,
               humidity: float,
               surface_segmentation: Optional[np.ndarray] = None,
               greenhouse_zone: str = "main") -> HumidityAnalysisResult:
        """
        Perform complete humidity and condensation analysis.
        
        Args:
            thermal_image: Thermal image (Celsius)
            visual_image: RGB visual image
            air_temp: Ambient air temperature
            humidity: Ambient relative humidity
            surface_segmentation: Optional surface type segmentation
            greenhouse_zone: Zone identifier
        
        Returns:
            Complete analysis results
        """
        logger.info(f"Analyzing humidity for zone: {greenhouse_zone}")
        
        # Create default segmentation if not provided
        if surface_segmentation is None:
            surface_segmentation = np.ones_like(thermal_image, dtype=np.uint8)
        
        # Calculate dewpoint and VPD maps
        dewpoint_map = np.zeros_like(thermal_image)
        vpd_map = np.zeros_like(thermal_image)
        humidity_map = np.full_like(thermal_image, humidity)  # Simplified
        
        for i in range(thermal_image.shape[0]):
            for j in range(thermal_image.shape[1]):
                temp = thermal_image[i, j]
                dewpoint_map[i, j] = self.calculate_dewpoint(temp, humidity)
                vpd_map[i, j] = self.calculate_vpd(temp, humidity)
        
        # Detect condensation events
        condensation_events = self.detect_condensation_events(
            thermal_image, visual_image, air_temp, humidity, surface_segmentation
        )
        
        # Assess mold risk
        mold_risk_zones = self.assess_mold_risk(
            thermal_image, humidity_map, hours_at_conditions=4.0
        )
        
        # Determine overall mold risk
        if mold_risk_zones:
            max_risk = max(zone.mold_risk_level for zone in mold_risk_zones)
            overall_mold_risk = max_risk
        else:
            overall_mold_risk = MoldRiskLevel.MINIMAL
        
        # Calculate disease outbreak probability
        disease_prob = self._calculate_disease_probability(
            humidity, air_temp, len(condensation_events), len(mold_risk_zones)
        )
        
        # Generate recommendations
        dehumidification_needed = humidity > self.crop_thresholds["mold_risk_humidity"]
        target_humidity = np.mean(self.crop_thresholds["optimal_humidity"])
        
        # Create visualizations
        condensation_heatmap, mold_risk_overlay = self.create_visualizations(
            thermal_image, humidity_map, condensation_events, mold_risk_zones
        )
        
        # Calculate uniformity
        temp_uniformity = 1.0 - (np.std(thermal_image) / (np.mean(thermal_image) + 1e-6))
        humidity_uniformity = 1.0 - (np.std(humidity_map) / (np.mean(humidity_map) + 1e-6))
        
        # Air circulation score
        air_circulation_score = self._calculate_air_circulation_score(
            temp_uniformity, humidity_uniformity
        )
        
        result = HumidityAnalysisResult(
            timestamp=datetime.now(),
            greenhouse_zone=greenhouse_zone,
            avg_air_temp=air_temp,
            avg_humidity=humidity,
            avg_dewpoint=np.mean(dewpoint_map),
            avg_vpd=np.mean(vpd_map),
            temp_uniformity=temp_uniformity,
            humidity_uniformity=humidity_uniformity,
            dewpoint_map=dewpoint_map,
            vpd_map=vpd_map,
            condensation_events=condensation_events,
            mold_risk_zones=mold_risk_zones,
            overall_mold_risk=overall_mold_risk,
            disease_outbreak_probability=disease_prob,
            dehumidification_needed=dehumidification_needed,
            target_humidity=target_humidity,
            air_circulation_score=air_circulation_score,
            heating_recommendation=self._generate_heating_recommendation(air_temp, humidity),
            ventilation_recommendation=self._generate_ventilation_recommendation(humidity),
            condensation_heatmap=condensation_heatmap,
            mold_risk_overlay=mold_risk_overlay
        )
        
        logger.info(f"Analysis complete: {len(condensation_events)} condensation events, "
                   f"{len(mold_risk_zones)} mold risk zones")
        
        return result
    
    def _calculate_disease_probability(self, 
                                      humidity: float,
                                      temperature: float,
                                      num_condensation: int,
                                      num_mold_zones: int) -> float:
        """Calculate probability of disease outbreak (0-1)"""
        prob = 0.0
        
        # Humidity contribution
        if humidity > 90:
            prob += 0.4
        elif humidity > 85:
            prob += 0.3
        elif humidity > 80:
            prob += 0.2
        
        # Temperature contribution (Botrytis optimal 15-25°C)
        if 15 <= temperature <= 25:
            prob += 0.2
        
        # Condensation contribution
        prob += min(0.3, num_condensation * 0.05)
        
        # Mold zone contribution
        prob += min(0.1, num_mold_zones * 0.02)
        
        return min(1.0, prob)
    
    def _calculate_air_circulation_score(self, 
                                        temp_uniformity: float,
                                        humidity_uniformity: float) -> float:
        """Calculate air circulation effectiveness score (0-100)"""
        # Good circulation means uniform conditions
        score = (temp_uniformity + humidity_uniformity) / 2.0 * 100
        return np.clip(score, 0, 100)
    
    def _generate_heating_recommendation(self, temperature: float, humidity: float) -> Optional[str]:
        """Generate heating system recommendation"""
        dewpoint = self.calculate_dewpoint(temperature, humidity)
        
        if humidity > 85 and temperature < 20:
            return f"Increase heating to {temperature + 3}°C to reduce relative humidity"
        elif dewpoint > temperature - 2:
            return "Increase heating by 2°C to prevent condensation"
        else:
            return None
    
    def _generate_ventilation_recommendation(self, humidity: float) -> Optional[str]:
        """Generate ventilation system recommendation"""
        if humidity > 90:
            return "URGENT: Open vents to maximum, activate exhaust fans"
        elif humidity > 85:
            return "Increase ventilation rate by 50%"
        elif humidity > 80:
            return "Increase ventilation rate by 25%"
        else:
            return None


def main():
    """Example usage of humidity analyzer"""
    # Initialize analyzer
    analyzer = HumidityCondensationAnalyzer(
        greenhouse_area_m2=500.0,
        crop_type="tomato",
        detection_sensitivity=0.75
    )
    
    # Simulate thermal and visual images
    thermal_image = np.random.uniform(18, 24, (480, 640)).astype(np.float32)
    visual_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    # Simulate environmental conditions
    air_temp = 22.0
    humidity = 85.0
    
    # Run analysis
    result = analyzer.analyze(
        thermal_image=thermal_image,
        visual_image=visual_image,
        air_temp=air_temp,
        humidity=humidity,
        greenhouse_zone="Zone_A"
    )
    
    print(f"Analysis complete for {result.greenhouse_zone}")
    print(f"Average VPD: {result.avg_vpd:.2f} kPa")
    print(f"Condensation events: {len(result.condensation_events)}")
    print(f"Mold risk zones: {len(result.mold_risk_zones)}")
    print(f"Overall mold risk: {result.overall_mold_risk.value}")
    print(f"Disease outbreak probability: {result.disease_outbreak_probability:.1%}")
    print(f"Air circulation score: {result.air_circulation_score:.1f}/100")


if __name__ == "__main__":
    main()
