"""
Downy Mildew Detection System for Greenhouse Horticulture

Detects and classifies infections caused by obligate oomycete pathogens (Peronospora spp.,
Pseudoperonospora spp., Plasmopara spp., Bremia lactucae) in controlled environment agriculture.

Downy mildew is distinct from powdery mildew:
- Appears as yellow/brown angular leaf spots on upper leaf surface
- White/purple/gray downy/fuzzy growth on underside of leaves
- Requires free moisture (water droplets or very high humidity)
- Systemic infection through vascular tissue
- Causes severe defoliation and yield loss in cucurbits, lettuce, basil, grapes

Major Economic Impact:
- Cucumbers: 30-50% yield loss in severe outbreaks
- Lettuce: Total crop loss possible, especially in baby leaf production
- Basil: Devastating to fresh-cut herb operations
- Grapes: Historic cause of European viticulture collapse (Plasmopara viticola)

Detection Challenges:
- Early symptoms subtle (slight yellowing)
- Sporulation on leaf underside requires imaging from below or leaf flipping
- Angular lesions follow leaf veins (vein-limited)
- Color varies by pathogen and host (white, purple, gray, brown)
- Confused with nutrient deficiency or senescence in early stages

Key Differentiators from Other Diseases:
- vs Powdery Mildew: Angular (not circular) lesions, underside sporulation, requires moisture
- vs Bacterial Spot: No raised lesions, no shot-hole effect
- vs Botrytis: No gray fuzzy sporulation, lesions confined to veins
- vs Nutrient Deficiency: Interveinal chlorosis but with sporulation
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Dict, Optional
import numpy as np
import cv2
from datetime import datetime


class DownyMildewStage(Enum):
    """Infection progression stages"""
    INCUBATION = "incubation"  # 0-3 days post infection, no visible symptoms
    CHLOROTIC = "chlorotic"  # 3-5 days, yellow/pale green spots on upper surface
    ANGULAR_LESION = "angular_lesion"  # 5-7 days, distinct angular lesions following veins
    EARLY_SPORULATION = "early_sporulation"  # 7-10 days, light sporulation on underside
    HEAVY_SPORULATION = "heavy_sporulation"  # 10-14 days, dense white/purple growth
    NECROTIC = "necrotic"  # 14+ days, brown/dead tissue, defoliation imminent
    SYSTEMIC = "systemic"  # Vascular infection, stunting, whole plant affected


class SporulationColor(Enum):
    """Characteristic colors of downy growth on leaf underside"""
    WHITE = "white"  # Pseudoperonospora cubensis (cucumber), Peronospora destructor (onion)
    PURPLE = "purple"  # Peronospora parasitica (brassicas), Bremia lactucae (lettuce)
    GRAY = "gray"  # Plasmopara viticola (grape), aged sporulation
    BROWN = "brown"  # Necrotic tissue, dead sporangia


class DownyMildewPathogen(Enum):
    """Major oomycete pathogens by host"""
    PSEUDOPERONOSPORA_CUBENSIS = "pseudoperonospora_cubensis"  # Cucumber, melon, squash
    PERONOSPORA_PARASITICA = "peronospora_parasitica"  # Cabbage, broccoli, radish
    BREMIA_LACTUCAE = "bremia_lactucae"  # Lettuce (37+ races, highly variable)
    PERONOSPORA_BELBAHRII = "peronospora_belbahrii"  # Basil (emerged 2001, devastating)
    PLASMOPARA_VITICOLA = "plasmopara_viticola"  # Grape (historical significance)
    PERONOSPORA_DESTRUCTOR = "peronospora_destructor"  # Onion, garlic
    PERONOSPORA_EFFUSA = "peronospora_effusa"  # Spinach
    UNKNOWN = "unknown"  # Cannot determine species from visual features alone


class LeafSurface(Enum):
    """Which leaf surface shows symptoms"""
    UPPER = "upper"  # Chlorotic lesions, angular spots
    LOWER = "lower"  # Sporulation, white/purple fuzzy growth
    BOTH = "both"  # Advanced infection visible from both sides


@dataclass
class AngularLesion:
    """Individual angular lesion on upper leaf surface"""
    bbox: Tuple[int, int, int, int]  # x, y, w, h
    area_mm2: float
    perimeter_mm: float
    angularity_score: float  # 0-1, how angular vs circular (1=perfectly angular)
    chlorosis_intensity: float  # 0-1, degree of yellowing
    vein_limited: bool  # True if lesion confined between leaf veins
    necrotic: bool  # True if tissue has died (brown)
    stage: DownyMildewStage
    confidence: float


@dataclass
class SporulationZone:
    """Sporulation on lower leaf surface"""
    bbox: Tuple[int, int, int, int]
    area_mm2: float
    color: SporulationColor
    density: float  # 0-1, density of sporulation (0=sparse, 1=confluent)
    sporangia_count_estimate: int  # Estimated number of sporangia (millions per cm²)
    corresponding_upper_lesion: Optional[AngularLesion]  # Matching lesion on upper surface
    stage: DownyMildewStage
    confidence: float


@dataclass
class SystemicInfection:
    """Whole-plant systemic infection indicators"""
    stunting_detected: bool
    leaf_curling: bool  # Downward curling characteristic of systemic infection
    vascular_discoloration: bool
    overall_chlorosis: bool  # Entire plant yellowing
    growth_reduction_percent: float  # Estimated compared to healthy plant
    estimated_days_since_infection: int


@dataclass
class DownyMildewCluster:
    """Group of lesions indicating spreading infection"""
    lesion_count: int
    total_area_mm2: float
    lesions: List[AngularLesion]
    sporulation_zones: List[SporulationZone]
    spread_rate_mm2_per_day: float  # Growth velocity
    vein_pattern: bool  # True if following vascular network
    secondary_infection_risk: float  # 0-1, probability of spreading to other plants


@dataclass
class EnvironmentalRiskFactors:
    """Climate conditions favoring downy mildew"""
    leaf_wetness_hours: float  # Hours of free moisture on leaves
    relative_humidity_percent: float
    temperature_celsius: float
    dew_formation: bool  # Dew events critical for sporulation
    overhead_irrigation: bool  # Splash irrigation increases risk
    poor_air_circulation: bool
    risk_score: float  # 0-1 overall risk
    optimal_for_pathogen: bool  # True if conditions perfect for outbreak


@dataclass
class DownyMildewTreatmentPlan:
    """Integrated management recommendations"""
    severity_level: str  # low, moderate, high, severe, catastrophic
    urgency_hours: int  # How quickly action must be taken
    
    # Chemical control
    fungicide_recommendations: List[str]  # FRAC codes, product names
    resistance_management: str  # Rotation strategy
    application_timing: str
    spray_coverage_critical: bool  # Must reach leaf undersides
    
    # Cultural control
    increase_air_circulation: bool
    reduce_humidity_target: float  # Target RH%
    eliminate_leaf_wetness: bool
    remove_infected_leaves: bool
    quarantine_zone: bool
    
    # Biological control
    biocontrol_options: List[str]
    
    # Preventive measures
    preventive_spray_schedule: str
    resistant_varieties: List[str]  # If replanting needed
    
    estimated_cost_usd: float
    efficacy_percent: float
    days_to_control: int


@dataclass
class DownyMildewDetectionResult:
    """Complete analysis output"""
    timestamp: datetime
    crop_type: str
    pathogen_suspected: DownyMildewPathogen
    
    # Detection results
    upper_surface_lesions: List[AngularLesion]
    lower_surface_sporulation: List[SporulationZone]
    clusters: List[DownyMildewCluster]
    systemic_infection: Optional[SystemicInfection]
    
    # Severity metrics
    total_lesion_count: int
    total_infected_area_mm2: float
    percent_leaf_area_affected: float
    average_lesion_size_mm2: float
    dominant_stage: DownyMildewStage
    sporulation_present: bool
    
    # Risk assessment
    environmental_risk: EnvironmentalRiskFactors
    secondary_spread_probability: float  # 0-1, risk to other plants
    yield_loss_estimate_percent: float
    
    # Recommendations
    treatment_plan: DownyMildewTreatmentPlan
    
    # Visualizations
    annotated_upper_image: np.ndarray
    annotated_lower_image: Optional[np.ndarray]
    lesion_heatmap: np.ndarray
    sporulation_map: Optional[np.ndarray]


class DownyMildewDetector:
    """
    Detect and analyze downy mildew infections in greenhouse crops.
    
    Requires images of BOTH upper and lower leaf surfaces for accurate detection.
    Upper surface shows angular chlorotic lesions.
    Lower surface shows characteristic white/purple/gray sporulation.
    """
    
    def __init__(
        self,
        crop_type: str,
        pixels_per_mm: float = 10.0,
        detection_sensitivity: float = 0.5,
        require_lower_surface: bool = True
    ):
        """
        Initialize detector.
        
        Args:
            crop_type: One of: cucumber, lettuce, basil, cabbage, grape, onion, spinach, melon
            pixels_per_mm: Image resolution (default 10 pixels = 1mm)
            detection_sensitivity: 0-1, higher = more sensitive (more false positives)
            require_lower_surface: If True, requires underside image for confirmation
        """
        self.crop_type = crop_type.lower()
        self.pixels_per_mm = pixels_per_mm
        self.detection_sensitivity = detection_sensitivity
        self.require_lower_surface = require_lower_surface
        
        # Load crop-specific parameters
        self.crop_params = self._load_crop_parameters()
        
        if self.crop_type not in self.crop_params:
            raise ValueError(f"Unsupported crop type: {crop_type}. Supported: {list(self.crop_params.keys())}")
    
    def _load_crop_parameters(self) -> Dict:
        """Crop-specific disease parameters"""
        return {
            "cucumber": {
                "pathogen": DownyMildewPathogen.PSEUDOPERONOSPORA_CUBENSIS,
                "sporulation_color": SporulationColor.WHITE,
                "susceptibility": "very_high",
                "typical_lesion_size_mm": (2.0, 25.0),
                "yield_loss_factor": 0.85,
                "critical_growth_stages": ["flowering", "fruit_set"],
                "defoliation_threshold_percent": 20.0,  # Above this = severe yield loss
            },
            "lettuce": {
                "pathogen": DownyMildewPathogen.BREMIA_LACTUCAE,
                "sporulation_color": SporulationColor.PURPLE,
                "susceptibility": "very_high",
                "typical_lesion_size_mm": (1.0, 15.0),
                "yield_loss_factor": 1.0,  # Total loss if severe (unmarketable)
                "critical_growth_stages": ["head_formation", "harvest"],
                "market_rejection_threshold": 5.0,  # % leaf area with lesions
            },
            "basil": {
                "pathogen": DownyMildewPathogen.PERONOSPORA_BELBAHRII,
                "sporulation_color": SporulationColor.GRAY,
                "susceptibility": "extreme",  # Emerged 2001, no resistant varieties
                "typical_lesion_size_mm": (1.0, 10.0),
                "yield_loss_factor": 1.0,  # Complete crop loss typical
                "critical_growth_stages": ["all"],  # Devastating at any stage
                "market_rejection_threshold": 1.0,  # Even minor infection = rejection
            },
            "cabbage": {
                "pathogen": DownyMildewPathogen.PERONOSPORA_PARASITICA,
                "sporulation_color": SporulationColor.WHITE,
                "susceptibility": "high",
                "typical_lesion_size_mm": (3.0, 30.0),
                "yield_loss_factor": 0.7,
                "critical_growth_stages": ["seedling", "heading"],
                "defoliation_threshold_percent": 30.0,
            },
            "grape": {
                "pathogen": DownyMildewPathogen.PLASMOPARA_VITICOLA,
                "sporulation_color": SporulationColor.WHITE,
                "susceptibility": "high",
                "typical_lesion_size_mm": (5.0, 50.0),
                "yield_loss_factor": 0.95,
                "critical_growth_stages": ["flowering", "berry_development"],
                "historical_note": "Caused European viticulture collapse 1870s",
            },
            "onion": {
                "pathogen": DownyMildewPathogen.PERONOSPORA_DESTRUCTOR,
                "sporulation_color": SporulationColor.PURPLE,
                "susceptibility": "high",
                "typical_lesion_size_mm": (2.0, 40.0),
                "yield_loss_factor": 0.75,
                "critical_growth_stages": ["bulbing"],
                "tip_dieback": True,  # Characteristic symptom
            },
            "spinach": {
                "pathogen": DownyMildewPathogen.PERONOSPORA_EFFUSA,
                "sporulation_color": SporulationColor.GRAY,
                "susceptibility": "high",
                "typical_lesion_size_mm": (1.0, 20.0),
                "yield_loss_factor": 0.9,
                "critical_growth_stages": ["vegetative"],
                "market_rejection_threshold": 3.0,
            },
            "melon": {
                "pathogen": DownyMildewPathogen.PSEUDOPERONOSPORA_CUBENSIS,
                "sporulation_color": SporulationColor.WHITE,
                "susceptibility": "very_high",
                "typical_lesion_size_mm": (2.0, 25.0),
                "yield_loss_factor": 0.8,
                "critical_growth_stages": ["flowering", "fruit_development"],
                "defoliation_threshold_percent": 25.0,
            },
        }
    
    def preprocess_image(self, image: np.ndarray, surface: LeafSurface) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Preprocess image for analysis.
        
        Args:
            image: RGB image
            surface: Whether this is upper or lower leaf surface
            
        Returns:
            (enhanced_rgb, hsv, gray)
        """
        # Resize if needed
        if image.shape[0] > 2000 or image.shape[1] > 2000:
            scale = 2000 / max(image.shape[:2])
            image = cv2.resize(image, None, fx=scale, fy=scale)
        
        # Enhance contrast for subtle symptoms
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        enhanced_lab = cv2.merge([l, a, b])
        enhanced_rgb = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2RGB)
        
        # Color space conversions
        hsv = cv2.cvtColor(enhanced_rgb, cv2.COLOR_RGB2HSV)
        gray = cv2.cvtColor(enhanced_rgb, cv2.COLOR_RGB2GRAY)
        
        return enhanced_rgb, hsv, gray
    
    def detect_angular_lesions(self, image: np.ndarray, hsv: np.ndarray) -> np.ndarray:
        """
        Detect angular chlorotic lesions on upper leaf surface.
        
        Angular lesions are key differentiator from circular powdery mildew.
        Lesions confined between leaf veins (vein-limited).
        """
        h, s, v = cv2.split(hsv)
        
        # Yellow/chlorotic regions (loss of green pigment)
        # Hue: 20-40 (yellow range)
        # Saturation: 30-150 (not too gray, not too vivid)
        # Value: 100-255 (not dark)
        chlorotic_mask = cv2.inRange(hsv, np.array([20, 30, 100]), np.array([40, 150, 255]))
        
        # Also detect pale/whitish regions (advanced chlorosis)
        pale_mask = cv2.inRange(hsv, np.array([0, 0, 180]), np.array([180, 60, 255]))
        
        # Combine masks
        lesion_mask = cv2.bitwise_or(chlorotic_mask, pale_mask)
        
        # Morphological operations to connect angular regions
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))  # Rectangular for angular
        lesion_mask = cv2.morphologyEx(lesion_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        
        return lesion_mask
    
    def detect_sporulation(self, image: np.ndarray, hsv: np.ndarray, expected_color: SporulationColor) -> np.ndarray:
        """
        Detect sporulation on lower leaf surface.
        
        Color varies by pathogen:
        - White: Pseudoperonospora (cucumber, melon)
        - Purple/Gray: Bremia (lettuce), Peronospora (brassicas)
        - Gray: Plasmopara (grape)
        """
        h, s, v = cv2.split(hsv)
        
        if expected_color == SporulationColor.WHITE:
            # White fuzzy growth
            sporulation_mask = cv2.inRange(hsv, np.array([0, 0, 180]), np.array([180, 60, 255]))
        
        elif expected_color == SporulationColor.PURPLE:
            # Purple/violet sporulation
            mask1 = cv2.inRange(hsv, np.array([130, 20, 80]), np.array([160, 200, 255]))
            mask2 = cv2.inRange(hsv, np.array([0, 20, 80]), np.array([10, 200, 255]))  # Reddish-purple
            sporulation_mask = cv2.bitwise_or(mask1, mask2)
        
        elif expected_color == SporulationColor.GRAY:
            # Gray sporulation
            sporulation_mask = cv2.inRange(hsv, np.array([0, 0, 80]), np.array([180, 60, 200]))
        
        else:  # BROWN (necrotic)
            sporulation_mask = cv2.inRange(hsv, np.array([10, 20, 40]), np.array([30, 200, 120]))
        
        # Enhance fuzzy texture
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        sporulation_mask = cv2.morphologyEx(sporulation_mask, cv2.MORPH_CLOSE, kernel)
        
        return sporulation_mask
    
    def calculate_angularity(self, contour: np.ndarray) -> float:
        """
        Calculate how angular a lesion is (vs circular).
        
        Angular lesions are diagnostic for downy mildew.
        Returns 0-1, where 1 = perfectly angular (rectangle).
        """
        # Fit bounding rectangle
        rect = cv2.minAreaRect(contour)
        box = cv2.boxPoints(rect)
        box_area = cv2.contourArea(box)
        
        # Get contour area
        contour_area = cv2.contourArea(contour)
        
        if box_area == 0:
            return 0.0
        
        # Ratio of contour area to bounding box
        # Angular lesions fill their bounding box more completely
        angularity = contour_area / box_area
        
        # Also check perimeter-to-area ratio
        perimeter = cv2.arcLength(contour, True)
        if contour_area > 0:
            # Angular shapes have higher perimeter relative to area
            compactness = (perimeter ** 2) / (4 * np.pi * contour_area)
            # Normalize: circle=1.0, square=1.27, highly angular>1.5
            angularity_score = min(1.0, (compactness - 1.0) / 0.5)
        else:
            angularity_score = 0.0
        
        # Combine metrics
        final_score = (angularity + angularity_score) / 2
        return min(1.0, max(0.0, final_score))
    
    def classify_lesion_stage(self, lesion_area_mm2: float, chlorosis_intensity: float, 
                             necrotic: bool, sporulation_present: bool) -> Tuple[DownyMildewStage, int]:
        """
        Classify infection stage and estimate age.
        
        Returns:
            (stage, estimated_hours_since_infection)
        """
        if lesion_area_mm2 < 1.0 and chlorosis_intensity < 0.3:
            return DownyMildewStage.INCUBATION, 48  # 0-3 days
        
        elif not sporulation_present and not necrotic:
            if chlorosis_intensity < 0.5:
                return DownyMildewStage.CHLOROTIC, 96  # 3-5 days
            else:
                return DownyMildewStage.ANGULAR_LESION, 144  # 5-7 days
        
        elif sporulation_present and not necrotic:
            if lesion_area_mm2 < 50.0:
                return DownyMildewStage.EARLY_SPORULATION, 192  # 7-10 days
            else:
                return DownyMildewStage.HEAVY_SPORULATION, 264  # 10-14 days
        
        elif necrotic:
            return DownyMildewStage.NECROTIC, 360  # 14+ days
        
        else:
            return DownyMildewStage.ANGULAR_LESION, 120
    
    def analyze_lesions(self, mask: np.ndarray, image: np.ndarray, hsv: np.ndarray, 
                       sporulation_detected: bool) -> List[AngularLesion]:
        """Analyze individual angular lesions"""
        lesions = []
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        params = self.crop_params[self.crop_type]
        min_area_px = (params["typical_lesion_size_mm"][0] * self.pixels_per_mm) ** 2
        max_area_px = (params["typical_lesion_size_mm"][1] * self.pixels_per_mm) ** 2
        
        h, s, v = cv2.split(hsv)
        
        for contour in contours:
            area_px = cv2.contourArea(contour)
            
            # Filter by size
            if area_px < min_area_px * 0.5 or area_px > max_area_px * 2.0:
                continue
            
            # Get bounding box
            x, y, w, h = cv2.boundingRect(contour)
            
            # Calculate metrics
            area_mm2 = area_px / (self.pixels_per_mm ** 2)
            perimeter_mm = cv2.arcLength(contour, True) / self.pixels_per_mm
            angularity = self.calculate_angularity(contour)
            
            # Only accept if angular enough (key diagnostic feature)
            if angularity < 0.3:
                continue
            
            # Calculate chlorosis intensity (degree of yellowing)
            lesion_region = hsv[y:y+h, x:x+w]
            h_vals = lesion_region[:, :, 0][mask[y:y+h, x:x+w] > 0]
            s_vals = lesion_region[:, :, 1][mask[y:y+h, x:x+w] > 0]
            v_vals = lesion_region[:, :, 2][mask[y:y+h, x:x+w] > 0]
            
            if len(h_vals) == 0:
                continue
            
            # Chlorosis intensity based on yellowing
            yellow_hue = np.sum((h_vals >= 20) & (h_vals <= 40)) / len(h_vals)
            chlorosis_intensity = float(yellow_hue * np.mean(s_vals) / 255.0)
            
            # Check if necrotic (brown/dead tissue)
            necrotic = bool(np.sum((h_vals >= 10) & (h_vals <= 25) & (v_vals < 100)) > len(h_vals) * 0.3)
            
            # Classify stage
            stage, age_hours = self.classify_lesion_stage(
                area_mm2, chlorosis_intensity, necrotic, sporulation_detected
            )
            
            # Calculate confidence
            confidence = angularity * 0.4 + chlorosis_intensity * 0.3 + min(1.0, area_mm2 / 10.0) * 0.3
            
            lesion = AngularLesion(
                bbox=(x, y, w, h),
                area_mm2=area_mm2,
                perimeter_mm=perimeter_mm,
                angularity_score=angularity,
                chlorosis_intensity=chlorosis_intensity,
                vein_limited=True,  # Assume true (requires vein detection for verification)
                necrotic=necrotic,
                stage=stage,
                confidence=confidence
            )
            
            lesions.append(lesion)
        
        return lesions
    
    def analyze_sporulation(self, mask: np.ndarray, image: np.ndarray, 
                          expected_color: SporulationColor) -> List[SporulationZone]:
        """Analyze sporulation zones on lower leaf surface"""
        zones = []
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area_px = cv2.contourArea(contour)
            
            if area_px < 100:  # Minimum 100 pixels
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            area_mm2 = area_px / (self.pixels_per_mm ** 2)
            
            # Calculate sporulation density
            sporulation_region = mask[y:y+h, x:x+w]
            density = np.sum(sporulation_region > 0) / (w * h)
            
            # Estimate sporangia count (millions per cm²)
            # Downy mildew produces 10,000-100,000 sporangia per lesion
            sporangia_estimate = int(area_mm2 * 0.1 * density * 50000)  # Rough estimate
            
            # Determine stage based on density and area
            if density < 0.3:
                stage = DownyMildewStage.EARLY_SPORULATION
            elif density < 0.7:
                stage = DownyMildewStage.HEAVY_SPORULATION
            else:
                stage = DownyMildewStage.NECROTIC
            
            zone = SporulationZone(
                bbox=(x, y, w, h),
                area_mm2=area_mm2,
                color=expected_color,
                density=density,
                sporangia_count_estimate=sporangia_estimate,
                corresponding_upper_lesion=None,  # Would need spatial correlation
                stage=stage,
                confidence=density * 0.7 + min(1.0, area_mm2 / 20.0) * 0.3
            )
            
            zones.append(zone)
        
        return zones
    
    def group_into_clusters(self, lesions: List[AngularLesion]) -> List[DownyMildewCluster]:
        """Group nearby lesions into infection clusters"""
        if len(lesions) == 0:
            return []
        
        clusters = []
        # Simple clustering by proximity
        used = set()
        
        for i, lesion in enumerate(lesions):
            if i in used:
                continue
            
            cluster_lesions = [lesion]
            cluster_area = lesion.area_mm2
            used.add(i)
            
            # Find nearby lesions (within 20mm)
            x1, y1, w1, h1 = lesion.bbox
            center1 = (x1 + w1/2, y1 + h1/2)
            
            for j, other in enumerate(lesions):
                if j in used:
                    continue
                
                x2, y2, w2, h2 = other.bbox
                center2 = (x2 + w2/2, y2 + h2/2)
                
                distance_px = np.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)
                distance_mm = distance_px / self.pixels_per_mm
                
                if distance_mm < 20.0:  # 20mm proximity
                    cluster_lesions.append(other)
                    cluster_area += other.area_mm2
                    used.add(j)
            
            # Only create cluster if multiple lesions
            if len(cluster_lesions) >= 2:
                cluster = DownyMildewCluster(
                    lesion_count=len(cluster_lesions),
                    total_area_mm2=cluster_area,
                    lesions=cluster_lesions,
                    sporulation_zones=[],  # Would need correlation with lower surface
                    spread_rate_mm2_per_day=cluster_area * 0.15,  # Estimate 15% growth/day
                    vein_pattern=True,  # Assume follows veins
                    secondary_infection_risk=min(1.0, len(cluster_lesions) / 10.0)
                )
                clusters.append(cluster)
        
        return clusters
    
    def assess_environmental_risk(self, leaf_wetness_hours: float, relative_humidity: float,
                                 temperature: float, overhead_irrigation: bool) -> EnvironmentalRiskFactors:
        """
        Assess environmental conditions for downy mildew development.
        
        Downy mildew REQUIRES free moisture for sporulation and infection.
        """
        # Optimal conditions for most downy mildew pathogens
        optimal_temp = 15.0 <= temperature <= 22.0
        high_humidity = relative_humidity > 85.0
        adequate_wetness = leaf_wetness_hours > 4.0
        
        # Calculate risk score
        risk = 0.0
        
        # Leaf wetness is CRITICAL (most important factor)
        if leaf_wetness_hours > 6.0:
            risk += 0.5
        elif leaf_wetness_hours > 4.0:
            risk += 0.3
        elif leaf_wetness_hours > 2.0:
            risk += 0.1
        
        # High humidity
        if relative_humidity > 90.0:
            risk += 0.3
        elif relative_humidity > 85.0:
            risk += 0.2
        
        # Optimal temperature
        if optimal_temp:
            risk += 0.15
        
        # Overhead irrigation (creates leaf wetness)
        if overhead_irrigation:
            risk += 0.05
        
        risk = min(1.0, risk)
        
        return EnvironmentalRiskFactors(
            leaf_wetness_hours=leaf_wetness_hours,
            relative_humidity_percent=relative_humidity,
            temperature_celsius=temperature,
            dew_formation=leaf_wetness_hours > 0,
            overhead_irrigation=overhead_irrigation,
            poor_air_circulation=relative_humidity > 85.0,  # Proxy indicator
            risk_score=risk,
            optimal_for_pathogen=optimal_temp and high_humidity and adequate_wetness
        )
    
    def generate_treatment_plan(self, severity: float, sporulation_present: bool,
                               environmental_risk: EnvironmentalRiskFactors) -> DownyMildewTreatmentPlan:
        """
        Generate integrated management recommendations.
        
        Downy mildew management is challenging:
        - Obligate pathogen (cannot culture in lab)
        - Rapidly develops fungicide resistance
        - FRAC rotation critical
        """
        params = self.crop_params[self.crop_type]
        
        # Determine severity level
        if severity < 5.0:
            level = "low"
            urgency = 72
        elif severity < 15.0:
            level = "moderate"
            urgency = 48
        elif severity < 30.0:
            level = "high"
            urgency = 24
        elif severity < 50.0:
            level = "severe"
            urgency = 12
        else:
            level = "catastrophic"
            urgency = 6
        
        # Chemical recommendations by severity
        if level == "catastrophic":
            fungicides = [
                "Orondis Gold (FRAC 49 + 40: oxathiapiprolin + mefenoxam) - SYSTEMIC RESCUE",
                "Previcur Flex (FRAC 28: propamocarb) - TANK MIX",
                "Forum (FRAC 50: dimethomorph) - TRANSLAMINAR",
                "Copper hydroxide (FRAC M01) - BROAD SPECTRUM"
            ]
            resistance_mgmt = "Emergency protocol: Apply 2 different FRAC codes in tank mix. Rotate weekly."
            application = "Apply immediately to entire crop + 5m buffer. Spray both sides of leaves."
            spray_critical = True
            cost = 800.0
            efficacy = 60.0
            days = 14
        
        elif level == "severe":
            fungicides = [
                "Ranman (FRAC 21: cyazofamid) - SYSTEMIC",
                "Revus (FRAC 40: mandipropamid) - TRANSLAMINAR",
                "Zampro (FRAC 45 + 40: ametoctradin + dimethomorph)",
                "Phosphorous acid (FRAC P07) - INDUCES RESISTANCE"
            ]
            resistance_mgmt = "Rotate between 3 FRAC groups weekly. Do not repeat same code within 21 days."
            application = "Apply within 12 hours to affected plants + adjacent rows. Ensure coverage of leaf undersides."
            spray_critical = True
            cost = 450.0
            efficacy = 75.0
            days = 10
        
        elif level == "high":
            fungicides = [
                "Presidio (FRAC 43: fluopicolide)",
                "Curzate (FRAC 27: cymoxanil) - SHORT RESIDUAL",
                "Gavel (FRAC M03 + 4: mancozeb + zoxamide)",
                "Actigard (FRAC P01: acibenzolar) - SAR ACTIVATOR"
            ]
            resistance_mgmt = "Alternate FRAC codes every 7-10 days. Max 3 applications per code per season."
            application = "Apply within 24 hours. Focus on new growth and leaf undersides."
            spray_critical = True
            cost = 250.0
            efficacy = 85.0
            days = 7
        
        elif level == "moderate":
            fungicides = [
                "Regalia (FRAC P05: Reynoutria extract) - BIOFUNGICIDE",
                "Cease (FRAC 44: Bacillus subtilis)",
                "Copper (FRAC M01) - PREVENTIVE",
                "Mancozeb (FRAC M03) - MULTI-SITE PROTECTANT"
            ]
            resistance_mgmt = "Preventive sprays every 7 days. Alternate with biocontrols."
            application = "Apply within 48 hours. Preventive spray program."
            spray_critical = False
            cost = 120.0
            efficacy = 90.0
            days = 10
        
        else:  # low
            fungicides = [
                "Cease (Bacillus subtilis) - PREVENTIVE",
                "Copper (FRAC M01) - LOW RATE PREVENTIVE"
            ]
            resistance_mgmt = "Weekly preventive sprays. No systemic fungicides needed yet."
            application = "Preventive program. Monitor closely."
            spray_critical = False
            cost = 50.0
            efficacy = 95.0
            days = 14
        
        # Cultural controls (CRITICAL for downy mildew)
        increase_circulation = environmental_risk.poor_air_circulation
        reduce_humidity = environmental_risk.relative_humidity_percent > 85.0
        humidity_target = 65.0 if reduce_humidity else environmental_risk.relative_humidity_percent
        eliminate_wetness = environmental_risk.leaf_wetness_hours > 2.0
        remove_leaves = severity > 15.0
        quarantine = severity > 30.0
        
        # Biological options
        biocontrols = [
            "Bacillus subtilis (Cease, Serenade)",
            "Trichoderma harzianum",
            "Reynoutria sachalinensis extract (Regalia)",
            "Potassium phosphite (induces plant resistance)"
        ]
        
        # Preventive measures
        preventive = "Weekly preventive sprays with FRAC M or P-code fungicides. Avoid overhead irrigation. Increase ventilation."
        
        # Resistant varieties (if replanting)
        resistant = []
        if self.crop_type == "lettuce":
            resistant = ["Slobolt", "Nevada", "Green Towers (some resistance to Bremia)"]
        elif self.crop_type == "cucumber":
            resistant = ["Darius", "Bristol", "Marketmore 76 (moderate tolerance)"]
        elif self.crop_type == "basil":
            resistant = ["Rutgers Devotion DMR", "Rutgers Obsession DMR (downy mildew resistant)"]
        
        return DownyMildewTreatmentPlan(
            severity_level=level,
            urgency_hours=urgency,
            fungicide_recommendations=fungicides,
            resistance_management=resistance_mgmt,
            application_timing=application,
            spray_coverage_critical=spray_critical,
            increase_air_circulation=increase_circulation,
            reduce_humidity_target=humidity_target,
            eliminate_leaf_wetness=eliminate_wetness,
            remove_infected_leaves=remove_leaves,
            quarantine_zone=quarantine,
            biocontrol_options=biocontrols,
            preventive_spray_schedule=preventive,
            resistant_varieties=resistant,
            estimated_cost_usd=cost,
            efficacy_percent=efficacy,
            days_to_control=days
        )
    
    def detect(
        self,
        upper_surface_image: np.ndarray,
        lower_surface_image: Optional[np.ndarray] = None,
        temperature: float = 20.0,
        relative_humidity: float = 80.0,
        leaf_wetness_hours: float = 2.0,
        overhead_irrigation: bool = False
    ) -> DownyMildewDetectionResult:
        """
        Perform complete downy mildew detection and analysis.
        
        Args:
            upper_surface_image: RGB image of upper leaf surface (shows angular lesions)
            lower_surface_image: RGB image of lower surface (shows sporulation) - RECOMMENDED
            temperature: Current temperature (°C)
            relative_humidity: Current RH (%)
            leaf_wetness_hours: Hours of leaf wetness in last 24h
            overhead_irrigation: Whether overhead irrigation is used
            
        Returns:
            Complete detection results with treatment recommendations
        """
        timestamp = datetime.now()
        
        # Preprocess upper surface
        upper_enhanced, upper_hsv, upper_gray = self.preprocess_image(upper_surface_image, LeafSurface.UPPER)
        
        # Detect angular lesions on upper surface
        lesion_mask = self.detect_angular_lesions(upper_enhanced, upper_hsv)
        
        # Analyze lesions (need to know if sporulation present)
        sporulation_detected = lower_surface_image is not None
        upper_lesions = self.analyze_lesions(lesion_mask, upper_enhanced, upper_hsv, sporulation_detected)
        
        # Analyze lower surface sporulation if provided
        lower_sporulation = []
        sporulation_map = None
        annotated_lower = None
        
        if lower_surface_image is not None:
            lower_enhanced, lower_hsv, lower_gray = self.preprocess_image(lower_surface_image, LeafSurface.LOWER)
            expected_color = self.crop_params[self.crop_type]["sporulation_color"]
            sporulation_mask = self.detect_sporulation(lower_enhanced, lower_hsv, expected_color)
            lower_sporulation = self.analyze_sporulation(sporulation_mask, lower_enhanced, expected_color)
            sporulation_detected = len(lower_sporulation) > 0
            
            # Create sporulation map
            sporulation_map = cv2.applyColorMap((sporulation_mask).astype(np.uint8), cv2.COLORMAP_JET)
            
            # Annotate lower image
            annotated_lower = lower_enhanced.copy()
            for zone in lower_sporulation:
                x, y, w, h = zone.bbox
                cv2.rectangle(annotated_lower, (x, y), (x+w, y+h), (255, 0, 255), 2)
                label = f"{zone.color.value} {zone.density:.1%}"
                cv2.putText(annotated_lower, label, (x, y-5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)
        
        # Group lesions into clusters
        clusters = self.group_into_clusters(upper_lesions)
        
        # Calculate severity metrics
        total_lesions = len(upper_lesions)
        total_area = sum(l.area_mm2 for l in upper_lesions)
        
        # Estimate total leaf area (assuming 1000mm² visible)
        estimated_leaf_area = upper_enhanced.shape[0] * upper_enhanced.shape[1] / (self.pixels_per_mm ** 2)
        percent_affected = (total_area / estimated_leaf_area * 100) if estimated_leaf_area > 0 else 0.0
        
        avg_lesion_size = total_area / total_lesions if total_lesions > 0 else 0.0
        
        # Determine dominant stage
        if upper_lesions:
            stage_counts = {}
            for lesion in upper_lesions:
                stage_counts[lesion.stage] = stage_counts.get(lesion.stage, 0) + 1
            dominant_stage = max(stage_counts, key=stage_counts.get)
        else:
            dominant_stage = DownyMildewStage.INCUBATION
        
        # Assess environmental risk
        env_risk = self.assess_environmental_risk(
            leaf_wetness_hours, relative_humidity, temperature, overhead_irrigation
        )
        
        # Calculate secondary spread probability
        spread_prob = min(1.0, (
            (len(lower_sporulation) / 10.0) * 0.4 +
            env_risk.risk_score * 0.4 +
            (len(clusters) / 5.0) * 0.2
        ))
        
        # Estimate yield loss
        params = self.crop_params[self.crop_type]
        yield_loss = min(100.0, percent_affected * params["yield_loss_factor"])
        
        # Generate treatment plan
        treatment = self.generate_treatment_plan(percent_affected, sporulation_detected, env_risk)
        
        # Create visualizations
        annotated_upper = upper_enhanced.copy()
        for lesion in upper_lesions:
            x, y, w, h = lesion.bbox
            color = (0, 255, 0) if lesion.stage in [DownyMildewStage.CHLOROTIC, DownyMildewStage.ANGULAR_LESION] else (0, 0, 255)
            cv2.rectangle(annotated_upper, (x, y), (x+w, y+h), color, 2)
            label = f"{lesion.stage.value[:3]} A:{lesion.angularity_score:.2f}"
            cv2.putText(annotated_upper, label, (x, y-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Heatmap
        heatmap = cv2.applyColorMap((lesion_mask).astype(np.uint8), cv2.COLORMAP_HOT)
        
        return DownyMildewDetectionResult(
            timestamp=timestamp,
            crop_type=self.crop_type,
            pathogen_suspected=params["pathogen"],
            upper_surface_lesions=upper_lesions,
            lower_surface_sporulation=lower_sporulation,
            clusters=clusters,
            systemic_infection=None,  # Would require whole-plant imaging
            total_lesion_count=total_lesions,
            total_infected_area_mm2=total_area,
            percent_leaf_area_affected=percent_affected,
            average_lesion_size_mm2=avg_lesion_size,
            dominant_stage=dominant_stage,
            sporulation_present=sporulation_detected,
            environmental_risk=env_risk,
            secondary_spread_probability=spread_prob,
            yield_loss_estimate_percent=yield_loss,
            treatment_plan=treatment,
            annotated_upper_image=annotated_upper,
            annotated_lower_image=annotated_lower,
            lesion_heatmap=heatmap,
            sporulation_map=sporulation_map
        )
