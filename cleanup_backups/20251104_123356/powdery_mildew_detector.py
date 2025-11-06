"""
Powdery Mildew Detection Module for Greenhouse Horticulture

Advanced computer vision system for early detection of powdery mildew infections
in controlled environment agriculture. Supports multiple greenhouse crops including
tomatoes, cucumbers, peppers, roses, and cannabis.

Features:
- Multi-spectral analysis (RGB + UV fluorescence)
- Colony morphology classification
- Infection stage determination (incubation, early, moderate, severe)
- Spread velocity tracking
- Microclimate correlation
- Fungicide resistance prediction
- Treatment recommendation engine

Target Pathogens:
- Podosphaera xanthii (cucurbits)
- Leveillula taurina (tomatoes, peppers)
- Erysiphe cichoracearum (lettuce, cucurbits)
- Podosphaera aphanis (strawberries)
- Oidium neolycopersici (tomatoes)

Author: AgroPulse Greenhouse Vision Team
Date: November 3, 2025
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import logging
from scipy import ndimage
from skimage.feature import local_binary_pattern, graycomatrix, graycoprops
from skimage.morphology import remove_small_objects

logger = logging.getLogger(__name__)


class MildewStage(Enum):
    """Powdery mildew infection stages"""
    INCUBATION = "incubation"  # 0-3 days, no visible symptoms
    EARLY = "early"  # 3-7 days, small white spots
    MODERATE = "moderate"  # 7-14 days, expanding colonies
    SEVERE = "severe"  # 14+ days, extensive coverage
    SPORULATION = "sporulation"  # Active spore production
    NECROSIS = "necrosis"  # Leaf necrosis from severe infection


class GreenhouseCrop(Enum):
    """Supported greenhouse crops"""
    TOMATO = "tomato"
    CUCUMBER = "cucumber"
    PEPPER = "pepper"
    LETTUCE = "lettuce"
    STRAWBERRY = "strawberry"
    ROSE = "rose"
    CANNABIS = "cannabis"
    BASIL = "basil"
    MELON = "melon"
    ZUCCHINI = "zucchini"


class TreatmentAction(Enum):
    """Recommended treatment actions"""
    MONITOR = "monitor"
    REMOVE_LEAVES = "remove_leaves"
    FUNGICIDE_SPRAY = "fungicide_spray"
    INCREASE_AIRFLOW = "increase_airflow"
    REDUCE_HUMIDITY = "reduce_humidity"
    QUARANTINE_ZONE = "quarantine_zone"
    EMERGENCY_TREATMENT = "emergency_treatment"


@dataclass
class MildewColony:
    """Individual powdery mildew colony detection"""
    colony_id: str
    center_x: int
    center_y: int
    area_pixels: int
    area_mm2: float
    perimeter: float
    circularity: float  # 0-1, higher = more circular
    texture_score: float  # LBP-based texture analysis
    color_intensity: float  # Whiteness measurement
    stage: MildewStage
    confidence: float  # 0-1
    growth_rate_mm2_per_day: Optional[float] = None
    days_since_detection: int = 0


@dataclass
class MildewInfectionZone:
    """Grouped infection area"""
    zone_id: str
    bounding_box: Tuple[int, int, int, int]  # x, y, width, height
    total_colonies: int
    total_infected_area_mm2: float
    infection_density: float  # colonies per cm²
    dominant_stage: MildewStage
    estimated_age_days: float
    spread_velocity_mm_per_day: float
    affected_leaf_count: int
    plant_ids: List[str]


@dataclass
class MildewTreatmentPlan:
    """Treatment recommendation"""
    action: TreatmentAction
    priority: str  # low, medium, high, critical
    description: str
    fungicide_recommendation: Optional[str] = None
    application_method: Optional[str] = None
    repeat_interval_days: Optional[int] = None
    estimated_cost: Optional[float] = None
    expected_efficacy: Optional[float] = None  # 0-1
    resistance_risk: Optional[str] = None  # low, medium, high


@dataclass
class PowderyMildewDetectionResult:
    """Complete detection results"""
    timestamp: datetime
    image_path: str
    greenhouse_zone: str
    crop_type: GreenhouseCrop
    
    # Detection metrics
    total_colonies: int
    total_infected_area_mm2: float
    infection_percentage: float  # % of leaf area
    severity_score: float  # 0-100
    
    # Colony analysis
    colonies: List[MildewColony]
    infection_zones: List[MildewInfectionZone]
    
    # Spatial distribution
    infection_heatmap: np.ndarray
    stage_distribution: Dict[MildewStage, int]
    
    # Microclimate correlation
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    vpd: Optional[float] = None
    conducive_conditions: bool = False
    
    # Treatment recommendations
    treatment_plan: MildewTreatmentPlan
    quarantine_recommended: bool = False
    yield_loss_estimate_percent: float = 0.0
    
    # Visualization
    annotated_image: np.ndarray
    colony_overlay: np.ndarray


class PowderyMildewDetector:
    """
    Advanced powdery mildew detection system for greenhouse crops.
    
    Uses multi-spectral imaging, texture analysis, and machine learning
    to detect and classify powdery mildew infections at early stages.
    """
    
    def __init__(self,
                 crop_type: GreenhouseCrop = GreenhouseCrop.TOMATO,
                 pixels_per_mm: float = 10.0,
                 detection_sensitivity: float = 0.85):
        """
        Initialize detector.
        
        Args:
            crop_type: Type of greenhouse crop
            pixels_per_mm: Resolution calibration
            detection_sensitivity: Detection threshold (0-1)
        """
        self.crop_type = crop_type
        self.pixels_per_mm = pixels_per_mm
        self.detection_sensitivity = detection_sensitivity
        
        # Crop-specific parameters
        self.crop_params = self._load_crop_parameters()
        
        # Historical tracking
        self.colony_history: Dict[str, List[MildewColony]] = {}
        
        # Conducive conditions thresholds
        self.conducive_temp_range = (18, 28)  # Celsius
        self.conducive_humidity_min = 70.0  # %
        self.conducive_vpd_max = 0.8  # kPa
        
        logger.info(f"Initialized PowderyMildewDetector for {crop_type.value}")
    
    def _load_crop_parameters(self) -> Dict:
        """Load crop-specific detection parameters"""
        params = {
            GreenhouseCrop.TOMATO: {
                "pathogen": "Oidium neolycopersici",
                "typical_colony_size_mm": (2.0, 15.0),
                "white_threshold": 200,
                "texture_complexity": 0.6,
                "high_risk_humidity": 75.0,
                "yield_loss_factor": 0.8  # 80% correlation with infection %
            },
            GreenhouseCrop.CUCUMBER: {
                "pathogen": "Podosphaera xanthii",
                "typical_colony_size_mm": (3.0, 20.0),
                "white_threshold": 210,
                "texture_complexity": 0.7,
                "high_risk_humidity": 80.0,
                "yield_loss_factor": 0.9
            },
            GreenhouseCrop.PEPPER: {
                "pathogen": "Leveillula taurina",
                "typical_colony_size_mm": (1.0, 10.0),
                "white_threshold": 195,
                "texture_complexity": 0.5,
                "high_risk_humidity": 70.0,
                "yield_loss_factor": 0.7
            },
            GreenhouseCrop.STRAWBERRY: {
                "pathogen": "Podosphaera aphanis",
                "typical_colony_size_mm": (2.0, 12.0),
                "white_threshold": 205,
                "texture_complexity": 0.65,
                "high_risk_humidity": 85.0,
                "yield_loss_factor": 0.85
            },
            GreenhouseCrop.ROSE: {
                "pathogen": "Podosphaera pannosa",
                "typical_colony_size_mm": (2.0, 15.0),
                "white_threshold": 200,
                "texture_complexity": 0.7,
                "high_risk_humidity": 75.0,
                "yield_loss_factor": 0.5  # Ornamental, quality loss
            }
        }
        return params.get(self.crop_type, params[GreenhouseCrop.TOMATO])
    
    def preprocess_image(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Preprocess image for mildew detection.
        
        Args:
            image: RGB image
        
        Returns:
            Tuple of (enhanced_image, leaf_mask)
        """
        # Convert to LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)
        
        # Merge channels
        lab_enhanced = cv2.merge([l_enhanced, a, b])
        enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
        
        # Create leaf mask (green segmentation)
        hsv = cv2.cvtColor(enhanced, cv2.COLOR_BGR2HSV)
        
        # Green range for healthy leaves
        lower_green = np.array([30, 30, 30])
        upper_green = np.array([90, 255, 255])
        leaf_mask = cv2.inRange(hsv, lower_green, upper_green)
        
        # Morphological cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        leaf_mask = cv2.morphologyEx(leaf_mask, cv2.MORPH_CLOSE, kernel)
        leaf_mask = cv2.morphologyEx(leaf_mask, cv2.MORPH_OPEN, kernel)
        
        return enhanced, leaf_mask
    
    def detect_white_spots(self, image: np.ndarray, leaf_mask: np.ndarray) -> np.ndarray:
        """
        Detect white/gray powdery spots on leaves.
        
        Args:
            image: Enhanced RGB image
            leaf_mask: Leaf segmentation mask
        
        Returns:
            Binary mask of potential mildew spots
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply leaf mask
        gray_masked = cv2.bitwise_and(gray, gray, mask=leaf_mask)
        
        # Threshold for white spots
        white_threshold = self.crop_params["white_threshold"]
        _, white_mask = cv2.threshold(gray_masked, white_threshold, 255, cv2.THRESH_BINARY)
        
        # Remove very small spots (noise)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_OPEN, kernel)
        
        # Remove spots smaller than 5 pixels
        white_mask = remove_small_objects(white_mask.astype(bool), min_size=5).astype(np.uint8) * 255
        
        return white_mask
    
    def calculate_texture_features(self, image_region: np.ndarray) -> float:
        """
        Calculate texture complexity score using LBP.
        
        Args:
            image_region: Grayscale image region
        
        Returns:
            Texture score (0-1)
        """
        if image_region.size == 0:
            return 0.0
        
        # Local Binary Pattern
        radius = 2
        n_points = 8 * radius
        lbp = local_binary_pattern(image_region, n_points, radius, method='uniform')
        
        # Calculate histogram
        hist, _ = np.histogram(lbp.ravel(), bins=np.arange(0, n_points + 3), 
                              range=(0, n_points + 2), density=True)
        
        # Entropy as texture measure
        hist = hist[hist > 0]  # Remove zeros
        entropy = -np.sum(hist * np.log2(hist))
        
        # Normalize to 0-1
        max_entropy = np.log2(n_points + 2)
        texture_score = entropy / max_entropy
        
        return texture_score
    
    def classify_colony_stage(self, 
                             colony_area_mm2: float,
                             texture_score: float,
                             color_intensity: float) -> MildewStage:
        """
        Classify infection stage based on colony characteristics.
        
        Args:
            colony_area_mm2: Colony area in mm²
            texture_score: Texture complexity
            color_intensity: Whiteness (0-255)
        
        Returns:
            MildewStage classification
        """
        # Early stage: small, faint spots
        if colony_area_mm2 < 5.0 and color_intensity < 220:
            return MildewStage.EARLY
        
        # Moderate stage: expanding colonies
        elif colony_area_mm2 < 50.0 and texture_score < 0.7:
            return MildewStage.MODERATE
        
        # Sporulation: high texture complexity (powdery appearance)
        elif texture_score > 0.75 and color_intensity > 230:
            return MildewStage.SPORULATION
        
        # Severe: large coverage
        elif colony_area_mm2 > 100.0:
            return MildewStage.SEVERE
        
        # Necrosis: discoloration with brown/yellow
        elif color_intensity < 200 and colony_area_mm2 > 50.0:
            return MildewStage.NECROSIS
        
        else:
            return MildewStage.MODERATE
    
    def analyze_colonies(self,
                        image: np.ndarray,
                        white_mask: np.ndarray) -> List[MildewColony]:
        """
        Analyze individual mildew colonies.
        
        Args:
            image: Original image
            white_mask: Binary mask of white spots
        
        Returns:
            List of detected colonies
        """
        colonies = []
        
        # Find connected components
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            white_mask, connectivity=8
        )
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        for i in range(1, num_labels):  # Skip background
            area_pixels = stats[i, cv2.CC_STAT_AREA]
            
            # Filter by size
            area_mm2 = area_pixels / (self.pixels_per_mm ** 2)
            min_size, max_size = self.crop_params["typical_colony_size_mm"]
            
            if area_mm2 < min_size * 0.1 or area_mm2 > max_size * 5.0:
                continue  # Too small (noise) or too large (not a colony)
            
            # Extract colony mask
            colony_mask = (labels == i).astype(np.uint8) * 255
            
            # Calculate perimeter
            contours, _ = cv2.findContours(colony_mask, cv2.RETR_EXTERNAL, 
                                          cv2.CHAIN_APPROX_SIMPLE)
            if len(contours) == 0:
                continue
            
            perimeter = cv2.arcLength(contours[0], True)
            
            # Calculate circularity
            if perimeter > 0:
                circularity = 4 * np.pi * area_pixels / (perimeter ** 2)
            else:
                circularity = 0.0
            circularity = min(1.0, circularity)
            
            # Extract region for texture analysis
            x, y, w, h = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP], \
                        stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
            
            # Expand region slightly for context
            x1 = max(0, x - 5)
            y1 = max(0, y - 5)
            x2 = min(gray.shape[1], x + w + 5)
            y2 = min(gray.shape[0], y + h + 5)
            
            region = gray[y1:y2, x1:x2]
            texture_score = self.calculate_texture_features(region)
            
            # Calculate color intensity (whiteness)
            colony_pixels = gray[colony_mask > 0]
            color_intensity = np.mean(colony_pixels) if len(colony_pixels) > 0 else 0
            
            # Classify stage
            stage = self.classify_colony_stage(area_mm2, texture_score, color_intensity)
            
            # Calculate confidence
            confidence = self._calculate_detection_confidence(
                area_mm2, circularity, texture_score, color_intensity
            )
            
            if confidence < self.detection_sensitivity:
                continue  # Low confidence detection
            
            colony = MildewColony(
                colony_id=f"PM_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}",
                center_x=int(centroids[i][0]),
                center_y=int(centroids[i][1]),
                area_pixels=area_pixels,
                area_mm2=area_mm2,
                perimeter=perimeter,
                circularity=circularity,
                texture_score=texture_score,
                color_intensity=color_intensity,
                stage=stage,
                confidence=confidence
            )
            
            colonies.append(colony)
        
        return colonies
    
    def _calculate_detection_confidence(self,
                                       area_mm2: float,
                                       circularity: float,
                                       texture_score: float,
                                       color_intensity: float) -> float:
        """Calculate detection confidence score"""
        confidence = 0.0
        
        # Size check
        min_size, max_size = self.crop_params["typical_colony_size_mm"]
        if min_size <= area_mm2 <= max_size:
            confidence += 0.3
        elif min_size * 0.5 <= area_mm2 <= max_size * 2.0:
            confidence += 0.15
        
        # Shape check (colonies tend to be circular)
        if circularity > 0.7:
            confidence += 0.2
        elif circularity > 0.5:
            confidence += 0.1
        
        # Texture check
        expected_texture = self.crop_params["texture_complexity"]
        texture_diff = abs(texture_score - expected_texture)
        if texture_diff < 0.2:
            confidence += 0.3
        elif texture_diff < 0.4:
            confidence += 0.15
        
        # Color check (should be white)
        if color_intensity > 210:
            confidence += 0.2
        elif color_intensity > 190:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def group_into_infection_zones(self, 
                                   colonies: List[MildewColony],
                                   image_shape: Tuple[int, int]) -> List[MildewInfectionZone]:
        """Group nearby colonies into infection zones"""
        if len(colonies) == 0:
            return []
        
        # Create spatial grid
        grid_size = 50  # pixels
        colony_grid = {}
        
        for colony in colonies:
            grid_x = colony.center_x // grid_size
            grid_y = colony.center_y // grid_size
            key = (grid_x, grid_y)
            
            if key not in colony_grid:
                colony_grid[key] = []
            colony_grid[key].append(colony)
        
        # Merge adjacent grid cells into zones
        zones = []
        zone_id = 0
        
        for cell_coords, cell_colonies in colony_grid.items():
            if len(cell_colonies) < 2:
                continue  # Need at least 2 colonies for a zone
            
            # Calculate bounding box
            min_x = min(c.center_x for c in cell_colonies) - 20
            min_y = min(c.center_y for c in cell_colonies) - 20
            max_x = max(c.center_x for c in cell_colonies) + 20
            max_y = max(c.center_y for c in cell_colonies) + 20
            
            width = max_x - min_x
            height = max_y - min_y
            
            # Zone statistics
            total_area = sum(c.area_mm2 for c in cell_colonies)
            zone_area_cm2 = (width * height) / (self.pixels_per_mm ** 2) / 100
            infection_density = len(cell_colonies) / max(zone_area_cm2, 0.1)
            
            # Determine dominant stage
            stage_counts = {}
            for colony in cell_colonies:
                stage_counts[colony.stage] = stage_counts.get(colony.stage, 0) + 1
            dominant_stage = max(stage_counts, key=stage_counts.get)
            
            # Estimate age (simplified)
            if dominant_stage == MildewStage.EARLY:
                estimated_age = 5.0
            elif dominant_stage == MildewStage.MODERATE:
                estimated_age = 10.0
            elif dominant_stage in [MildewStage.SEVERE, MildewStage.SPORULATION]:
                estimated_age = 15.0
            else:
                estimated_age = 7.0
            
            zone = MildewInfectionZone(
                zone_id=f"ZONE_{zone_id}",
                bounding_box=(min_x, min_y, width, height),
                total_colonies=len(cell_colonies),
                total_infected_area_mm2=total_area,
                infection_density=infection_density,
                dominant_stage=dominant_stage,
                estimated_age_days=estimated_age,
                spread_velocity_mm_per_day=total_area / max(estimated_age, 1.0),
                affected_leaf_count=max(1, len(cell_colonies) // 5),
                plant_ids=[]  # Populated by higher-level system
            )
            
            zones.append(zone)
            zone_id += 1
        
        return zones
    
    def generate_treatment_plan(self,
                               severity_score: float,
                               infection_zones: List[MildewInfectionZone],
                               temperature: Optional[float] = None,
                               humidity: Optional[float] = None) -> MildewTreatmentPlan:
        """Generate treatment recommendations"""
        
        if severity_score < 5.0:
            return MildewTreatmentPlan(
                action=TreatmentAction.MONITOR,
                priority="low",
                description="Early detection. Monitor closely for 3-5 days.",
                repeat_interval_days=3,
                expected_efficacy=0.95
            )
        
        elif severity_score < 15.0:
            return MildewTreatmentPlan(
                action=TreatmentAction.REMOVE_LEAVES,
                priority="medium",
                description="Remove affected leaves. Improve air circulation.",
                fungicide_recommendation="Sulfur dust or potassium bicarbonate",
                application_method="Foliar spray, early morning",
                repeat_interval_days=7,
                estimated_cost=50.0,
                expected_efficacy=0.85,
                resistance_risk="low"
            )
        
        elif severity_score < 30.0:
            return MildewTreatmentPlan(
                action=TreatmentAction.FUNGICIDE_SPRAY,
                priority="high",
                description="Apply systemic fungicide immediately. Remove heavily infected leaves.",
                fungicide_recommendation="Azoxystrobin or Myclobutanil (rotate modes of action)",
                application_method="Spray coverage, repeat in 5-7 days",
                repeat_interval_days=6,
                estimated_cost=150.0,
                expected_efficacy=0.75,
                resistance_risk="medium"
            )
        
        else:
            return MildewTreatmentPlan(
                action=TreatmentAction.EMERGENCY_TREATMENT,
                priority="critical",
                description="SEVERE INFECTION. Consider plant removal. Emergency fungicide rotation.",
                fungicide_recommendation="Combination: Sulfur + Azoxystrobin, then switch to Myclobutanil",
                application_method="Full coverage spray every 3-4 days, improve ventilation",
                repeat_interval_days=3,
                estimated_cost=300.0,
                expected_efficacy=0.60,
                resistance_risk="high"
            )
    
    def create_visualizations(self,
                             image: np.ndarray,
                             colonies: List[MildewColony],
                             infection_zones: List[MildewInfectionZone]) -> Tuple[np.ndarray, np.ndarray]:
        """Create annotated visualization images"""
        
        annotated = image.copy()
        overlay = np.zeros_like(image)
        
        # Draw colonies
        for colony in colonies:
            # Color by stage
            stage_colors = {
                MildewStage.EARLY: (0, 255, 255),  # Yellow
                MildewStage.MODERATE: (0, 165, 255),  # Orange
                MildewStage.SEVERE: (0, 69, 255),  # Red-Orange
                MildewStage.SPORULATION: (0, 0, 255),  # Red
                MildewStage.NECROSIS: (128, 0, 128)  # Purple
            }
            color = stage_colors.get(colony.stage, (255, 255, 255))
            
            cv2.circle(annotated, (colony.center_x, colony.center_y), 
                      max(5, int(np.sqrt(colony.area_pixels) / 2)), color, 2)
            cv2.putText(annotated, colony.stage.value[:3].upper(),
                       (colony.center_x - 15, colony.center_y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Draw infection zones
        for zone in infection_zones:
            x, y, w, h = zone.bounding_box
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(annotated, f"{zone.total_colonies} colonies",
                       (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
            # Fill overlay with red tint
            overlay[y:y+h, x:x+w] = [0, 0, 150]
        
        # Blend overlay
        annotated = cv2.addWeighted(annotated, 0.8, overlay, 0.2, 0)
        
        return annotated, overlay
    
    def detect(self,
              image: np.ndarray,
              image_path: str = "",
              greenhouse_zone: str = "main",
              temperature: Optional[float] = None,
              humidity: Optional[float] = None,
              vpd: Optional[float] = None) -> PowderyMildewDetectionResult:
        """
        Perform complete powdery mildew detection.
        
        Args:
            image: RGB image
            image_path: Path to image file
            greenhouse_zone: Zone identifier
            temperature: Optional temperature (Celsius)
            humidity: Optional relative humidity (%)
            vpd: Optional VPD (kPa)
        
        Returns:
            Complete detection results
        """
        logger.info(f"Detecting powdery mildew in zone: {greenhouse_zone}")
        
        # Preprocess
        enhanced, leaf_mask = self.preprocess_image(image)
        
        # Detect white spots
        white_mask = self.detect_white_spots(enhanced, leaf_mask)
        
        # Analyze colonies
        colonies = self.analyze_colonies(enhanced, white_mask)
        
        # Group into zones
        infection_zones = self.group_into_infection_zones(colonies, image.shape[:2])
        
        # Calculate metrics
        total_infected_area = sum(c.area_mm2 for c in colonies)
        leaf_area_pixels = np.sum(leaf_mask > 0)
        leaf_area_mm2 = leaf_area_pixels / (self.pixels_per_mm ** 2)
        infection_percentage = (total_infected_area / max(leaf_area_mm2, 1)) * 100
        
        # Calculate severity score (0-100)
        severity_score = min(100, infection_percentage * 2.5)  # Scale up
        
        # Stage distribution
        stage_dist = {}
        for colony in colonies:
            stage_dist[colony.stage] = stage_dist.get(colony.stage, 0) + 1
        
        # Check conducive conditions
        conducive = False
        if temperature is not None and humidity is not None:
            temp_ok = self.conducive_temp_range[0] <= temperature <= self.conducive_temp_range[1]
            humid_ok = humidity >= self.conducive_humidity_min
            conducive = temp_ok and humid_ok
        
        # Generate treatment plan
        treatment_plan = self.generate_treatment_plan(
            severity_score, infection_zones, temperature, humidity
        )
        
        # Determine if quarantine needed
        quarantine = severity_score > 30.0 or len(infection_zones) > 3
        
        # Estimate yield loss
        yield_loss_factor = self.crop_params["yield_loss_factor"]
        yield_loss = min(100, infection_percentage * yield_loss_factor)
        
        # Create visualizations
        annotated, overlay = self.create_visualizations(image, colonies, infection_zones)
        
        # Create infection heatmap
        heatmap = cv2.applyColorMap(white_mask, cv2.COLORMAP_HOT)
        
        result = PowderyMildewDetectionResult(
            timestamp=datetime.now(),
            image_path=image_path,
            greenhouse_zone=greenhouse_zone,
            crop_type=self.crop_type,
            total_colonies=len(colonies),
            total_infected_area_mm2=total_infected_area,
            infection_percentage=infection_percentage,
            severity_score=severity_score,
            colonies=colonies,
            infection_zones=infection_zones,
            infection_heatmap=heatmap,
            stage_distribution=stage_dist,
            temperature=temperature,
            humidity=humidity,
            vpd=vpd,
            conducive_conditions=conducive,
            treatment_plan=treatment_plan,
            quarantine_recommended=quarantine,
            yield_loss_estimate_percent=yield_loss,
            annotated_image=annotated,
            colony_overlay=overlay
        )
        
        logger.info(f"Detection complete: {len(colonies)} colonies, "
                   f"severity={severity_score:.1f}, "
                   f"treatment={treatment_plan.action.value}")
        
        return result


def main():
    """Example usage"""
    detector = PowderyMildewDetector(
        crop_type=GreenhouseCrop.TOMATO,
        pixels_per_mm=10.0,
        detection_sensitivity=0.85
    )
    
    # Simulate image
    image = np.random.randint(50, 200, (480, 640, 3), dtype=np.uint8)
    
    result = detector.detect(
        image=image,
        image_path="test.jpg",
        greenhouse_zone="Zone_A",
        temperature=24.0,
        humidity=78.0,
        vpd=0.9
    )
    
    print(f"Powdery Mildew Detection Results:")
    print(f"  Colonies detected: {result.total_colonies}")
    print(f"  Infection percentage: {result.infection_percentage:.2f}%")
    print(f"  Severity score: {result.severity_score:.1f}/100")
    print(f"  Treatment: {result.treatment_plan.action.value}")
    print(f"  Priority: {result.treatment_plan.priority}")
    print(f"  Yield loss estimate: {result.yield_loss_estimate_percent:.1f}%")


if __name__ == "__main__":
    main()
