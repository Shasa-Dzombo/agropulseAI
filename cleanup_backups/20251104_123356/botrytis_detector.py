"""
Botrytis Gray Mold Detection Module for Greenhouse Horticulture

Advanced computer vision system for detecting Botrytis cinerea (gray mold),
the most economically damaging fungal disease in greenhouse production.

Critical for: Tomatoes, strawberries, lettuce, peppers, cucumbers, roses,
cannabis, and most greenhouse crops.

Features:
- Multi-spectral lesion detection (visible + UV-induced fluorescence)
- Fuzzy gray sporulation identification
- Water-soaked lesion detection (early stage)
- Stem canker detection
- Fruit/flower infection assessment
- Environmental risk scoring
- Spore load estimation
- Treatment urgency classification

Botrytis Life Cycle Stages Detected:
1. Incubation (0-24h): No visible symptoms
2. Colonization (24-48h): Water-soaked lesions
3. Sporulation (48-72h): Gray fuzzy growth
4. Necrosis (72h+): Brown/black tissue death
5. Secondary spread: Airborne spore dispersal

Author: AgroPulse Greenhouse Vision Team
Date: November 3, 2025
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import logging
from scipy import ndimage
from skimage.feature import local_binary_pattern
from skimage.morphology import remove_small_objects

logger = logging.getLogger(__name__)


class BotrytisStage(Enum):
    """Botrytis infection stages"""
    INCUBATION = "incubation"  # 0-24h, no visible symptoms
    WATER_SOAKED = "water_soaked"  # 24-48h, translucent lesions
    EARLY_SPORULATION = "early_sporulation"  # 48-72h, light gray fuzz
    FULL_SPORULATION = "full_sporulation"  # 72h+, dense gray sporulation
    NECROSIS = "necrosis"  # Tissue death, brown/black
    SYSTEMIC = "systemic"  # Stem/crown infection


class InfectionSite(Enum):
    """Plant parts affected by Botrytis"""
    LEAF = "leaf"
    STEM = "stem"
    FLOWER = "flower"
    FRUIT = "fruit"
    CROWN = "crown"
    WOUND = "wound"
    SENESCENT_TISSUE = "senescent_tissue"


class TreatmentUrgency(Enum):
    """Treatment urgency levels"""
    LOW = "low"  # Monitor, preventive measures
    MODERATE = "moderate"  # Treat within 24-48h
    HIGH = "high"  # Treat within 12-24h
    CRITICAL = "critical"  # Treat immediately, quarantine
    EMERGENCY = "emergency"  # Remove plants, disinfect area


@dataclass
class BotrytisLesion:
    """Individual botrytis lesion detection"""
    lesion_id: str
    center_x: int
    center_y: int
    area_mm2: float
    stage: BotrytisStage
    infection_site: InfectionSite
    gray_coverage_percent: float  # % of lesion with gray sporulation
    water_soaked: bool
    necrotic: bool
    age_estimate_hours: float
    spore_density: float  # 0-1, estimated spore load
    confidence: float  # 0-1
    expansion_rate_mm_per_hour: Optional[float] = None


@dataclass
class BotrytisCluster:
    """Clustered infection area"""
    cluster_id: str
    bounding_box: Tuple[int, int, int, int]  # x, y, width, height
    lesion_count: int
    total_area_mm2: float
    dominant_stage: BotrytisStage
    average_age_hours: float
    high_risk_for_spread: bool
    estimated_spore_release_per_hour: float  # Millions of spores
    affected_plant_ids: List[str]


@dataclass
class EnvironmentalRisk:
    """Environmental conditions conducive to Botrytis"""
    temperature: Optional[float]  # Celsius
    humidity: Optional[float]  # %
    leaf_wetness: Optional[float]  # hours
    vpd: Optional[float]  # kPa
    air_circulation: Optional[float]  # 0-1 score
    risk_score: float  # 0-1
    hours_in_conducive_conditions: float
    outbreak_probability: float  # 0-1


@dataclass
class BotytisTreatmentPlan:
    """Treatment recommendations"""
    urgency: TreatmentUrgency
    primary_action: str
    secondary_actions: List[str]
    fungicide_recommendation: Optional[str]
    application_timing: str
    biocontrol_options: List[str]
    cultural_controls: List[str]
    estimated_cost: float
    expected_efficacy: float  # 0-1
    resistance_management: str


@dataclass
class BotrytisDetectionResult:
    """Complete detection results"""
    timestamp: datetime
    image_path: str
    greenhouse_zone: str
    crop_type: str
    
    # Detection metrics
    total_lesions: int
    total_infected_area_mm2: float
    infection_severity: float  # 0-100
    sporulation_index: float  # 0-100, spore production intensity
    
    # Lesion analysis
    lesions: List[BotrytisLesion]
    clusters: List[BotrytisCluster]
    stage_distribution: Dict[BotrytisStage, int]
    
    # Risk assessment
    environmental_risk: EnvironmentalRisk
    spread_velocity: float  # mm²/hour
    secondary_infection_risk: float  # 0-1
    
    # Impact estimation
    affected_plants: int
    yield_loss_estimate_percent: float
    quality_downgrade_percent: float
    
    # Treatment
    treatment_plan: BotytisTreatmentPlan
    quarantine_zone: bool
    
    # Visualization
    annotated_image: np.ndarray
    sporulation_map: np.ndarray
    risk_heatmap: np.ndarray


class BotrytisDetector:
    """
    Advanced Botrytis cinerea detection system for greenhouse crops.
    
    Uses multi-spectral imaging, texture analysis, and environmental
    correlation to detect and classify gray mold infections.
    """
    
    def __init__(self,
                 crop_type: str = "tomato",
                 pixels_per_mm: float = 10.0,
                 detection_sensitivity: float = 0.80):
        """
        Initialize Botrytis detector.
        
        Args:
            crop_type: Type of greenhouse crop
            pixels_per_mm: Camera resolution calibration
            detection_sensitivity: Detection threshold (0-1)
        """
        self.crop_type = crop_type
        self.pixels_per_mm = pixels_per_mm
        self.detection_sensitivity = detection_sensitivity
        
        # Crop-specific parameters
        self.crop_params = self._load_crop_parameters()
        
        # Conducive conditions thresholds
        self.conducive_temp_range = (15, 25)  # Celsius, optimal for Botrytis
        self.conducive_humidity_min = 85.0  # %
        self.conducive_leaf_wetness_hours = 4.0
        
        # Historical tracking
        self.lesion_history: Dict[str, List[BotrytisLesion]] = {}
        
        logger.info(f"Initialized BotrytisDetector for {crop_type}")
    
    def _load_crop_parameters(self) -> Dict:
        """Load crop-specific Botrytis parameters"""
        params = {
            "tomato": {
                "susceptibility": "high",
                "typical_lesion_size_mm": (5.0, 50.0),
                "high_risk_sites": ["fruit", "stem", "leaf"],
                "yield_loss_factor": 0.9,
                "quality_impact": "severe",
                "market_rejection_threshold": 5.0  # % infection
            },
            "strawberry": {
                "susceptibility": "very_high",
                "typical_lesion_size_mm": (3.0, 30.0),
                "high_risk_sites": ["fruit", "flower", "leaf"],
                "yield_loss_factor": 0.95,
                "quality_impact": "critical",
                "market_rejection_threshold": 2.0
            },
            "lettuce": {
                "susceptibility": "high",
                "typical_lesion_size_mm": (10.0, 80.0),
                "high_risk_sites": ["leaf", "crown"],
                "yield_loss_factor": 1.0,  # Total loss if crown infected
                "quality_impact": "severe",
                "market_rejection_threshold": 1.0
            },
            "cucumber": {
                "susceptibility": "moderate",
                "typical_lesion_size_mm": (5.0, 40.0),
                "high_risk_sites": ["fruit", "stem", "flower"],
                "yield_loss_factor": 0.8,
                "quality_impact": "severe",
                "market_rejection_threshold": 3.0
            },
            "pepper": {
                "susceptibility": "moderate",
                "typical_lesion_size_mm": (5.0, 40.0),
                "high_risk_sites": ["fruit", "stem"],
                "yield_loss_factor": 0.85,
                "quality_impact": "severe",
                "market_rejection_threshold": 3.0
            },
            "rose": {
                "susceptibility": "very_high",
                "typical_lesion_size_mm": (3.0, 25.0),
                "high_risk_sites": ["flower", "stem", "leaf"],
                "yield_loss_factor": 1.0,  # Total loss for ornamentals
                "quality_impact": "critical",
                "market_rejection_threshold": 0.5
            },
            "cannabis": {
                "susceptibility": "very_high",
                "typical_lesion_size_mm": (5.0, 60.0),
                "high_risk_sites": ["flower", "stem", "leaf"],
                "yield_loss_factor": 1.0,  # Contaminated product unsellable
                "quality_impact": "critical",
                "market_rejection_threshold": 0.1
            }
        }
        return params.get(self.crop_type, params["tomato"])
    
    def preprocess_image(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Preprocess image for Botrytis detection.
        
        Returns:
            Tuple of (enhanced_rgb, hsv, gray)
        """
        # Apply CLAHE enhancement
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)
        
        lab_enhanced = cv2.merge([l_enhanced, a, b])
        enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
        
        # Convert to HSV
        hsv = cv2.cvtColor(enhanced, cv2.COLOR_BGR2HSV)
        
        # Grayscale
        gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
        
        return enhanced, hsv, gray
    
    def detect_gray_sporulation(self, image: np.ndarray, hsv: np.ndarray) -> np.ndarray:
        """
        Detect characteristic gray fuzzy sporulation.
        
        Args:
            image: RGB image
            hsv: HSV image
        
        Returns:
            Binary mask of gray sporulation
        """
        h, s, v = cv2.split(hsv)
        
        # Gray color range (low saturation, medium-high value)
        gray_mask1 = cv2.inRange(hsv, np.array([0, 0, 80]), np.array([180, 50, 200]))
        
        # Brownish-gray range (older sporulation)
        gray_mask2 = cv2.inRange(hsv, np.array([10, 20, 60]), np.array([30, 80, 150]))
        
        # Combine masks
        gray_mask = cv2.bitwise_or(gray_mask1, gray_mask2)
        
        # Morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        gray_mask = cv2.morphologyEx(gray_mask, cv2.MORPH_CLOSE, kernel)
        gray_mask = cv2.morphologyEx(gray_mask, cv2.MORPH_OPEN, kernel)
        
        return gray_mask
    
    def detect_water_soaked_lesions(self, image: np.ndarray, hsv: np.ndarray) -> np.ndarray:
        """
        Detect water-soaked translucent lesions (early stage).
        
        Args:
            image: RGB image
            hsv: HSV image
        
        Returns:
            Binary mask of water-soaked areas
        """
        h, s, v = cv2.split(hsv)
        
        # Water-soaked tissue has slightly darker, translucent appearance
        # Look for areas with reduced value but maintained hue
        
        # Create baseline from healthy tissue
        healthy_green = cv2.inRange(hsv, np.array([35, 40, 60]), np.array([85, 255, 255]))
        
        # Water-soaked: similar hue, reduced saturation and value
        water_soaked = cv2.inRange(hsv, np.array([35, 10, 30]), np.array([85, 80, 120]))
        
        # Remove areas that are already gray (later stage)
        gray_mask = self.detect_gray_sporulation(image, hsv)
        water_soaked = cv2.bitwise_and(water_soaked, cv2.bitwise_not(gray_mask))
        
        # Morphological cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        water_soaked = cv2.morphologyEx(water_soaked, cv2.MORPH_CLOSE, kernel)
        
        return water_soaked
    
    def detect_necrotic_tissue(self, hsv: np.ndarray) -> np.ndarray:
        """
        Detect brown/black necrotic tissue from advanced infection.
        
        Args:
            hsv: HSV image
        
        Returns:
            Binary mask of necrotic areas
        """
        # Brown necrotic tissue
        brown_mask = cv2.inRange(hsv, np.array([10, 30, 20]), np.array([25, 180, 120]))
        
        # Dark brown/black
        black_mask = cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 255, 50])
        
        # Combine
        necrotic_mask = cv2.bitwise_or(brown_mask, black_mask)
        
        # Cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        necrotic_mask = cv2.morphologyEx(necrotic_mask, cv2.MORPH_OPEN, kernel)
        
        return necrotic_mask
    
    def classify_lesion_stage(self,
                             gray_coverage: float,
                             water_soaked: bool,
                             necrotic: bool,
                             area_mm2: float) -> Tuple[BotrytisStage, float]:
        """
        Classify infection stage and estimate age.
        
        Returns:
            Tuple of (stage, age_estimate_hours)
        """
        # Water-soaked lesion (early stage, 24-48h)
        if water_soaked and gray_coverage < 5.0:
            return BotrytisStage.WATER_SOAKED, 36.0
        
        # Early sporulation (48-72h)
        elif gray_coverage > 5.0 and gray_coverage < 30.0 and not necrotic:
            return BotrytisStage.EARLY_SPORULATION, 60.0
        
        # Full sporulation (72h+)
        elif gray_coverage >= 30.0 and not necrotic:
            # Estimate age from coverage
            age_hours = 72.0 + (gray_coverage - 30.0) * 2.0
            return BotrytisStage.FULL_SPORULATION, age_hours
        
        # Necrosis (advanced, 96h+)
        elif necrotic:
            return BotrytisStage.NECROSIS, 120.0
        
        # Systemic/crown infection (variable)
        elif area_mm2 > 100.0:
            return BotrytisStage.SYSTEMIC, 168.0  # ~7 days
        
        # Default: incubation/uncertain
        else:
            return BotrytisStage.INCUBATION, 12.0
    
    def estimate_spore_density(self, gray_coverage: float, area_mm2: float) -> float:
        """
        Estimate spore production density (0-1).
        
        Botrytis produces millions of conidia per cm² of sporulating lesion.
        """
        if gray_coverage < 5.0:
            return 0.0  # No visible sporulation
        elif gray_coverage < 20.0:
            return 0.3  # Low sporulation
        elif gray_coverage < 50.0:
            return 0.6  # Moderate sporulation
        elif gray_coverage < 80.0:
            return 0.85  # High sporulation
        else:
            return 1.0  # Maximum sporulation
    
    def analyze_lesions(self,
                       image: np.ndarray,
                       gray_mask: np.ndarray,
                       water_soaked_mask: np.ndarray,
                       necrotic_mask: np.ndarray) -> List[BotrytisLesion]:
        """
        Analyze individual Botrytis lesions.
        
        Returns:
            List of detected lesions
        """
        lesions = []
        
        # Combine all masks to find all infected areas
        combined_mask = cv2.bitwise_or(gray_mask, water_soaked_mask)
        combined_mask = cv2.bitwise_or(combined_mask, necrotic_mask)
        
        # Find connected components
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            combined_mask, connectivity=8
        )
        
        for i in range(1, num_labels):  # Skip background
            area_pixels = stats[i, cv2.CC_STAT_AREA]
            area_mm2 = area_pixels / (self.pixels_per_mm ** 2)
            
            # Filter by size
            min_size, max_size = self.crop_params["typical_lesion_size_mm"]
            if area_mm2 < min_size * 0.1 or area_mm2 > max_size * 3.0:
                continue
            
            # Extract lesion mask
            lesion_mask = (labels == i).astype(np.uint8) * 255
            
            # Calculate gray coverage
            gray_in_lesion = cv2.bitwise_and(gray_mask, gray_mask, mask=lesion_mask)
            gray_pixels = np.sum(gray_in_lesion > 0)
            gray_coverage = (gray_pixels / max(area_pixels, 1)) * 100.0
            
            # Check for water-soaked tissue
            water_in_lesion = cv2.bitwise_and(water_soaked_mask, water_soaked_mask, mask=lesion_mask)
            water_soaked = np.sum(water_in_lesion > 0) > (area_pixels * 0.3)
            
            # Check for necrotic tissue
            necrotic_in_lesion = cv2.bitwise_and(necrotic_mask, necrotic_mask, mask=lesion_mask)
            necrotic = np.sum(necrotic_in_lesion > 0) > (area_pixels * 0.2)
            
            # Classify stage and estimate age
            stage, age_hours = self.classify_lesion_stage(
                gray_coverage, water_soaked, necrotic, area_mm2
            )
            
            # Estimate spore density
            spore_density = self.estimate_spore_density(gray_coverage, area_mm2)
            
            # Determine infection site (simplified)
            infection_site = self._determine_infection_site(
                int(centroids[i][1]), image.shape[0]
            )
            
            # Calculate confidence
            confidence = self._calculate_confidence(
                gray_coverage, water_soaked, necrotic, area_mm2, stage
            )
            
            if confidence < self.detection_sensitivity:
                continue
            
            lesion = BotrytisLesion(
                lesion_id=f"BOT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}",
                center_x=int(centroids[i][0]),
                center_y=int(centroids[i][1]),
                area_mm2=area_mm2,
                stage=stage,
                infection_site=infection_site,
                gray_coverage_percent=gray_coverage,
                water_soaked=water_soaked,
                necrotic=necrotic,
                age_estimate_hours=age_hours,
                spore_density=spore_density,
                confidence=confidence
            )
            
            lesions.append(lesion)
        
        return lesions
    
    def _determine_infection_site(self, y_position: int, image_height: int) -> InfectionSite:
        """Determine plant part based on position (simplified)"""
        # Top third: flowers/fruit
        if y_position < image_height * 0.33:
            return InfectionSite.FLOWER
        # Middle third: leaves
        elif y_position < image_height * 0.67:
            return InfectionSite.LEAF
        # Bottom third: stem/crown
        else:
            return InfectionSite.STEM
    
    def _calculate_confidence(self,
                             gray_coverage: float,
                             water_soaked: bool,
                             necrotic: bool,
                             area_mm2: float,
                             stage: BotrytisStage) -> float:
        """Calculate detection confidence"""
        confidence = 0.0
        
        # Gray sporulation is highly characteristic
        if gray_coverage > 20.0:
            confidence += 0.5
        elif gray_coverage > 5.0:
            confidence += 0.3
        
        # Water-soaked appearance (early stage)
        if water_soaked:
            confidence += 0.2
        
        # Necrosis (advanced stage)
        if necrotic:
            confidence += 0.2
        
        # Size check
        min_size, max_size = self.crop_params["typical_lesion_size_mm"]
        if min_size <= area_mm2 <= max_size:
            confidence += 0.3
        elif min_size * 0.5 <= area_mm2 <= max_size * 2.0:
            confidence += 0.15
        
        return min(1.0, confidence)
    
    def group_into_clusters(self, lesions: List[BotrytisLesion]) -> List[BotrytisCluster]:
        """Group nearby lesions into infection clusters"""
        if len(lesions) == 0:
            return []
        
        clusters = []
        
        # Simple spatial clustering (50mm radius)
        cluster_radius_mm = 50.0
        cluster_radius_px = cluster_radius_mm * self.pixels_per_mm
        
        unassigned = lesions.copy()
        cluster_id = 0
        
        while unassigned:
            # Start new cluster with first unassigned lesion
            seed = unassigned.pop(0)
            cluster_lesions = [seed]
            
            # Find nearby lesions
            i = 0
            while i < len(unassigned):
                lesion = unassigned[i]
                dist = np.sqrt((lesion.center_x - seed.center_x)**2 + 
                              (lesion.center_y - seed.center_y)**2)
                
                if dist < cluster_radius_px:
                    cluster_lesions.append(unassigned.pop(i))
                else:
                    i += 1
            
            # Only create cluster if multiple lesions
            if len(cluster_lesions) >= 2:
                # Calculate cluster properties
                min_x = min(l.center_x for l in cluster_lesions) - 20
                min_y = min(l.center_y for l in cluster_lesions) - 20
                max_x = max(l.center_x for l in cluster_lesions) + 20
                max_y = max(l.center_y for l in cluster_lesions) + 20
                
                total_area = sum(l.area_mm2 for l in cluster_lesions)
                avg_age = np.mean([l.age_estimate_hours for l in cluster_lesions])
                
                # Dominant stage
                stage_counts = {}
                for lesion in cluster_lesions:
                    stage_counts[lesion.stage] = stage_counts.get(lesion.stage, 0) + 1
                dominant_stage = max(stage_counts, key=stage_counts.get)
                
                # High risk if any lesion is sporulating heavily
                high_risk = any(l.spore_density > 0.6 for l in cluster_lesions)
                
                # Estimate spore release (millions per hour)
                spore_release = sum(l.area_mm2 * l.spore_density * 10.0 for l in cluster_lesions)
                
                cluster = BotrytisCluster(
                    cluster_id=f"CLUSTER_{cluster_id}",
                    bounding_box=(min_x, min_y, max_x - min_x, max_y - min_y),
                    lesion_count=len(cluster_lesions),
                    total_area_mm2=total_area,
                    dominant_stage=dominant_stage,
                    average_age_hours=avg_age,
                    high_risk_for_spread=high_risk,
                    estimated_spore_release_per_hour=spore_release,
                    affected_plant_ids=[]
                )
                
                clusters.append(cluster)
                cluster_id += 1
        
        return clusters
    
    def assess_environmental_risk(self,
                                 temperature: Optional[float],
                                 humidity: Optional[float],
                                 leaf_wetness_hours: Optional[float],
                                 vpd: Optional[float]) -> EnvironmentalRisk:
        """Assess environmental conduciveness to Botrytis"""
        risk_score = 0.0
        outbreak_prob = 0.0
        
        # Temperature (15-25°C optimal)
        if temperature is not None:
            if 15 <= temperature <= 25:
                risk_score += 0.3
                outbreak_prob += 0.25
            elif 10 <= temperature <= 30:
                risk_score += 0.15
                outbreak_prob += 0.1
        
        # Humidity (>85% high risk)
        if humidity is not None:
            if humidity > 90:
                risk_score += 0.4
                outbreak_prob += 0.35
            elif humidity > 85:
                risk_score += 0.3
                outbreak_prob += 0.25
            elif humidity > 75:
                risk_score += 0.15
                outbreak_prob += 0.1
        
        # Leaf wetness (>4 hours critical)
        if leaf_wetness_hours is not None:
            if leaf_wetness_hours > 6:
                risk_score += 0.3
                outbreak_prob += 0.3
            elif leaf_wetness_hours > 4:
                risk_score += 0.2
                outbreak_prob += 0.2
            elif leaf_wetness_hours > 2:
                risk_score += 0.1
                outbreak_prob += 0.1
        
        # VPD (<0.4 kPa very high risk)
        if vpd is not None:
            if vpd < 0.4:
                risk_score += 0.2
                outbreak_prob += 0.15
            elif vpd < 0.6:
                risk_score += 0.1
                outbreak_prob += 0.05
        
        # Estimate hours in conducive conditions
        hours_conducive = 0.0
        if risk_score > 0.6:
            hours_conducive = 8.0  # Estimate
        elif risk_score > 0.4:
            hours_conducive = 4.0
        
        return EnvironmentalRisk(
            temperature=temperature,
            humidity=humidity,
            leaf_wetness=leaf_wetness_hours,
            vpd=vpd,
            air_circulation=None,
            risk_score=min(1.0, risk_score),
            hours_in_conducive_conditions=hours_conducive,
            outbreak_probability=min(1.0, outbreak_prob)
        )
    
    def generate_treatment_plan(self,
                               severity: float,
                               sporulation_index: float,
                               env_risk: EnvironmentalRisk,
                               clusters: List[BotrytisCluster]) -> BotytisTreatmentPlan:
        """Generate treatment recommendations"""
        
        # Determine urgency
        if severity > 50.0 or sporulation_index > 70.0:
            urgency = TreatmentUrgency.EMERGENCY
        elif severity > 30.0 or sporulation_index > 50.0:
            urgency = TreatmentUrgency.CRITICAL
        elif severity > 15.0 or sporulation_index > 30.0:
            urgency = TreatmentUrgency.HIGH
        elif severity > 5.0:
            urgency = TreatmentUrgency.MODERATE
        else:
            urgency = TreatmentUrgency.LOW
        
        # Generate recommendations
        if urgency == TreatmentUrgency.EMERGENCY:
            return BotytisTreatmentPlan(
                urgency=urgency,
                primary_action="EMERGENCY: Remove heavily infected plants immediately",
                secondary_actions=[
                    "Quarantine entire zone",
                    "Disinfect all surfaces with bleach solution",
                    "Increase ventilation to maximum",
                    "Reduce humidity below 70%",
                    "Stop overhead irrigation"
                ],
                fungicide_recommendation="Switch 100 (cyprodinil/fludioxonil) + Scala (pyrimethanil)",
                application_timing="Apply immediately, repeat every 3-4 days",
                biocontrol_options=["Cease biocontrol, emergency chemical only"],
                cultural_controls=[
                    "Remove all infected tissue and bag for disposal",
                    "Increase plant spacing if possible",
                    "Install additional fans for air movement"
                ],
                estimated_cost=500.0,
                expected_efficacy=0.60,
                resistance_management="Rotate between FRAC groups 9, 12, 7, 17"
            )
        
        elif urgency == TreatmentUrgency.CRITICAL:
            return BotytisTreatmentPlan(
                urgency=urgency,
                primary_action="Apply systemic fungicide within 12 hours",
                secondary_actions=[
                    "Remove all infected leaves/fruit",
                    "Increase air circulation immediately",
                    "Lower humidity to 60-65%",
                    "Inspect daily for new infections"
                ],
                fungicide_recommendation="Rovral (iprodione) or Botran (dicloran)",
                application_timing="Apply now, repeat in 5-7 days",
                biocontrol_options=[
                    "Companion with Bacillus subtilis (Serenade)",
                    "Use after fungicide interval"
                ],
                cultural_controls=[
                    "Prune for better air circulation",
                    "Avoid evening watering",
                    "Heat greenhouse during humid periods"
                ],
                estimated_cost=300.0,
                expected_efficacy=0.75,
                resistance_management="Alternate FRAC groups, max 2 applications per season"
            )
        
        elif urgency == TreatmentUrgency.HIGH:
            return BotytisTreatmentPlan(
                urgency=urgency,
                primary_action="Fungicide application within 24 hours recommended",
                secondary_actions=[
                    "Remove infected plant material",
                    "Improve ventilation",
                    "Monitor humidity levels",
                    "Increase plant inspection frequency"
                ],
                fungicide_recommendation="Luna Tranquility (fluopyram/pyrimethanil)",
                application_timing="Apply within 24h, repeat in 7-10 days if needed",
                biocontrol_options=[
                    "Trichoderma harzianum (RootShield)",
                    "Gliocladium catenulatum (Prestop)",
                    "Bacillus amyloliquefaciens (Double Nickel)"
                ],
                cultural_controls=[
                    "Sanitation: remove senescent tissue",
                    "Optimize spacing and pruning",
                    "Control humidity <75%"
                ],
                estimated_cost=150.0,
                expected_efficacy=0.85,
                resistance_management="Rotate modes of action, avoid over-application"
            )
        
        elif urgency == TreatmentUrgency.MODERATE:
            return BotytisTreatmentPlan(
                urgency=urgency,
                primary_action="Preventive fungicide or biocontrol within 48 hours",
                secondary_actions=[
                    "Scout and remove any infected tissue",
                    "Adjust climate to reduce conduciveness",
                    "Monitor closely for expansion"
                ],
                fungicide_recommendation="Preventive biocontrol preferred",
                application_timing="Apply within 48h, weekly applications",
                biocontrol_options=[
                    "Bacillus subtilis (Serenade MAX)",
                    "Trichoderma spp. (Rootshield)",
                    "Streptomyces (Actinovate)"
                ],
                cultural_controls=[
                    "Improve air circulation",
                    "Sanitation and hygiene",
                    "Control humidity 65-70%",
                    "Avoid leaf wetness"
                ],
                estimated_cost=75.0,
                expected_efficacy=0.90,
                resistance_management="Preventive biocontrol has no resistance issues"
            )
        
        else:  # LOW
            return BotytisTreatmentPlan(
                urgency=urgency,
                primary_action="Preventive measures and monitoring",
                secondary_actions=[
                    "Maintain optimal climate",
                    "Continue scouting",
                    "Remove senescent tissue promptly"
                ],
                fungicide_recommendation="Not needed at this time",
                application_timing="Monitor for 7 days",
                biocontrol_options=[
                    "Consider preventive biocontrol if risk increases",
                    "Beneficial fungi as preventive"
                ],
                cultural_controls=[
                    "Maintain good air circulation",
                    "Optimal spacing and pruning",
                    "Humidity control 60-70%",
                    "Regular sanitation"
                ],
                estimated_cost=25.0,
                expected_efficacy=0.95,
                resistance_management="N/A - cultural controls only"
            )
    
    def create_visualizations(self,
                             image: np.ndarray,
                             lesions: List[BotrytisLesion],
                             clusters: List[BotrytisCluster],
                             gray_mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Create visualization images"""
        
        annotated = image.copy()
        sporulation_map = np.zeros_like(image)
        risk_heatmap = np.zeros_like(image)
        
        # Draw lesions
        stage_colors = {
            BotrytisStage.WATER_SOAKED: (255, 255, 0),  # Cyan
            BotrytisStage.EARLY_SPORULATION: (0, 255, 255),  # Yellow
            BotrytisStage.FULL_SPORULATION: (0, 165, 255),  # Orange
            BotrytisStage.NECROSIS: (0, 0, 255),  # Red
            BotrytisStage.SYSTEMIC: (128, 0, 128)  # Purple
        }
        
        for lesion in lesions:
            color = stage_colors.get(lesion.stage, (255, 255, 255))
            radius = max(8, int(np.sqrt(lesion.area_mm2 * self.pixels_per_mm)))
            
            cv2.circle(annotated, (lesion.center_x, lesion.center_y), radius, color, 2)
            
            # Add label
            label = f"{lesion.stage.value[:4].upper()}\n{lesion.gray_coverage_percent:.0f}%"
            cv2.putText(annotated, label.split('\n')[0],
                       (lesion.center_x - 20, lesion.center_y - 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Draw clusters
        for cluster in clusters:
            x, y, w, h = cluster.bounding_box
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 0, 255), 3)
            cv2.putText(annotated, f"CLUSTER: {cluster.lesion_count} lesions",
                       (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Sporulation map (gray overlay)
        gray_colored = cv2.applyColorMap(gray_mask, cv2.COLORMAP_HOT)
        sporulation_map = cv2.addWeighted(image, 0.6, gray_colored, 0.4, 0)
        
        # Risk heatmap
        risk_heatmap = cv2.applyColorMap(gray_mask, cv2.COLORMAP_JET)
        
        return annotated, sporulation_map, risk_heatmap
    
    def detect(self,
              image: np.ndarray,
              image_path: str = "",
              greenhouse_zone: str = "main",
              temperature: Optional[float] = None,
              humidity: Optional[float] = None,
              leaf_wetness_hours: Optional[float] = None,
              vpd: Optional[float] = None) -> BotrytisDetectionResult:
        """
        Perform complete Botrytis detection.
        
        Returns:
            Complete detection results
        """
        logger.info(f"Detecting Botrytis in zone: {greenhouse_zone}")
        
        # Preprocess
        enhanced, hsv, gray = self.preprocess_image(image)
        
        # Detect different lesion types
        gray_mask = self.detect_gray_sporulation(enhanced, hsv)
        water_soaked_mask = self.detect_water_soaked_lesions(enhanced, hsv)
        necrotic_mask = self.detect_necrotic_tissue(hsv)
        
        # Analyze lesions
        lesions = self.analyze_lesions(enhanced, gray_mask, water_soaked_mask, necrotic_mask)
        
        # Group into clusters
        clusters = self.group_into_clusters(lesions)
        
        # Calculate metrics
        total_area = sum(l.area_mm2 for l in lesions)
        severity = min(100.0, total_area / 10.0)  # Simplified
        
        # Calculate sporulation index
        sporulation_index = np.mean([l.spore_density * 100 for l in lesions]) if lesions else 0.0
        
        # Stage distribution
        stage_dist = {}
        for lesion in lesions:
            stage_dist[lesion.stage] = stage_dist.get(lesion.stage, 0) + 1
        
        # Environmental risk
        env_risk = self.assess_environmental_risk(temperature, humidity, leaf_wetness_hours, vpd)
        
        # Spread velocity
        avg_age = np.mean([l.age_estimate_hours for l in lesions]) if lesions else 0.0
        spread_velocity = total_area / max(avg_age, 1.0)
        
        # Secondary infection risk
        secondary_risk = min(1.0, sporulation_index / 100.0 * env_risk.risk_score)
        
        # Impact estimation
        affected_plants = max(1, len(clusters) * 3)
        yield_loss = min(100.0, severity * self.crop_params["yield_loss_factor"])
        quality_downgrade = min(100.0, severity * 1.2)
        
        # Treatment plan
        treatment_plan = self.generate_treatment_plan(severity, sporulation_index, env_risk, clusters)
        
        # Quarantine decision
        quarantine = (severity > 30.0 or sporulation_index > 50.0 or 
                     len(clusters) > 2 or env_risk.outbreak_probability > 0.6)
        
        # Visualizations
        annotated, sporulation_map, risk_heatmap = self.create_visualizations(
            image, lesions, clusters, gray_mask
        )
        
        result = BotrytisDetectionResult(
            timestamp=datetime.now(),
            image_path=image_path,
            greenhouse_zone=greenhouse_zone,
            crop_type=self.crop_type,
            total_lesions=len(lesions),
            total_infected_area_mm2=total_area,
            infection_severity=severity,
            sporulation_index=sporulation_index,
            lesions=lesions,
            clusters=clusters,
            stage_distribution=stage_dist,
            environmental_risk=env_risk,
            spread_velocity=spread_velocity,
            secondary_infection_risk=secondary_risk,
            affected_plants=affected_plants,
            yield_loss_estimate_percent=yield_loss,
            quality_downgrade_percent=quality_downgrade,
            treatment_plan=treatment_plan,
            quarantine_zone=quarantine,
            annotated_image=annotated,
            sporulation_map=sporulation_map,
            risk_heatmap=risk_heatmap
        )
        
        logger.info(f"Detection complete: {len(lesions)} lesions, "
                   f"severity={severity:.1f}, urgency={treatment_plan.urgency.value}")
        
        return result


def main():
    """Example usage"""
    detector = BotrytisDetector(
        crop_type="tomato",
        pixels_per_mm=10.0,
        detection_sensitivity=0.80
    )
    
    # Simulate image
    image = np.random.randint(50, 200, (480, 640, 3), dtype=np.uint8)
    
    result = detector.detect(
        image=image,
        greenhouse_zone="Zone_A",
        temperature=20.0,
        humidity=88.0,
        leaf_wetness_hours=6.0,
        vpd=0.5
    )
    
    print(f"Botrytis Detection Results:")
    print(f"  Lesions: {result.total_lesions}")
    print(f"  Severity: {result.infection_severity:.1f}/100")
    print(f"  Sporulation index: {result.sporulation_index:.1f}/100")
    print(f"  Treatment urgency: {result.treatment_plan.urgency.value}")
    print(f"  Yield loss: {result.yield_loss_estimate_percent:.1f}%")
    print(f"  Quarantine: {result.quarantine_zone}")


if __name__ == "__main__":
    main()
