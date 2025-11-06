"""
Peach Disease Detection Suite
Comprehensive detection system for peach and nectarine diseases

CRITICAL DISEASES:

1. Brown Rot (Monilinia spp.) - #1 STONE FRUIT DISEASE WORLDWIDE
   - 50-80% crop loss if untreated
   - Pre-harvest and post-harvest losses
   - Blossom blight (kills flowers)
   - Fruit rot (mummies persist)
   - $160+ million annual losses USA alone

2. Peach Leaf Curl (Taphrina deformans) - UNIQUE FUNGUS
   - Puckered distorted leaves (spring)
   - 100% defoliation in severe cases
   - Weakens tree (reduced winter hardiness)
   - EASY TO CONTROL: Single dormant spray

3. Bacterial Spot (Xanthomonas arboricola pv. pruni)
   - Fruit and leaf lesions
   - Tree decline over years
   - Copper resistance widespread
   - 20-50% yield loss

4. Peach Scab (Cladosporium carpophilum)
   - Olive-green velvety spots on fruit
   - Cosmetic damage
   - Export market rejection

5. Cytospora Canker (Leucostoma spp.)
   - Gummy cankers on branches
   - Tree death
   - Stress-related

DETECTION CHALLENGE:
- Brown rot rapid spread (48-72 hours)
- Leaf curl timing critical (dormant spray)
- Bacterial spot copper resistance
- Post-harvest brown rot latent infections

Author: AgroPulse AI Team
Version: 1.0.0
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class PeachDisease(Enum):
    """Comprehensive peach disease classification"""
    BROWN_ROT = "brown_rot"  # Monilinia - #1 disease
    PEACH_LEAF_CURL = "peach_leaf_curl"  # Taphrina - unique
    BACTERIAL_SPOT = "bacterial_spot"  # Xanthomonas
    PEACH_SCAB = "peach_scab"  # Cladosporium
    CYTOSPORA_CANKER = "cytospora_canker"  # Leucostoma
    POWDERY_MILDEW = "powdery_mildew"  # Sphaerotheca
    SHOT_HOLE = "shot_hole"  # Wilsonomyces/Stigmina
    RUST = "rust"  # Tranzschelia
    ANTHRACNOSE = "anthracnose"  # Colletotrichum
    PHYTOPHTHORA_ROOT_ROT = "phytophthora_root_rot"
    ARMILLARIA_ROOT_ROT = "armillaria_root_rot"
    BACTERIAL_CANKER = "bacterial_canker"  # Pseudomonas


class PeachType(Enum):
    """Peach and nectarine classifications"""
    YELLOW_FLESH_PEACH = "yellow_flesh_peach"
    WHITE_FLESH_PEACH = "white_flesh_peach"
    NECTARINE = "nectarine"  # Fuzzless (recessive gene)
    FLAT_PEACH = "flat_peach"  # Donut/Saturn peach
    CLING = "cling"  # Flesh adheres to pit
    FREESTONE = "freestone"  # Flesh separates from pit
    SEMI_FREESTONE = "semi_freestone"


@dataclass
class PeachLesion:
    """Peach disease lesion characteristics"""
    color_hsv_range: Tuple[Tuple[int, int, int], Tuple[int, int, int]]
    shape: str  # circular, angular, irregular
    texture: str  # fuzzy, velvety, raised, sunken, gummy
    location: str  # fruit, leaf, flower, twig, trunk
    size_mm: Tuple[float, float]
    progression: str  # rapid, expanding, static
    margin: str  # defined, diffuse
    
    # Diagnostic features
    brown_fuzzy_spores: bool = False  # Brown rot
    puckered_distorted: bool = False  # Leaf curl
    shot_hole: bool = False  # Shot hole disease
    gummy_exudate: bool = False  # Cankers
    
    # Economic impact
    yield_loss_percent: float = 0.0
    fruit_quality_impact: str = "none"  # none, blemish, unmarketable


@dataclass
class PeachFruitDisease:
    """Fruit-specific disease parameters"""
    fruit_symptoms: List[str]
    infection_timing: str  # bloom, fruit_development, pre_harvest, post_harvest
    latent_period_days: float
    marketability: str  # fresh_market, processing, loss
    shelf_life_impact: str  # none, reduced, severe


@dataclass
class EnvironmentalRisk:
    """Environmental factors for peach disease risk"""
    temperature_range: Tuple[float, float]
    humidity_threshold: float
    wetness_duration_hours: float
    rainfall_mm: float
    
    risk_level: str = "low"
    infection_period_hours: float = 0.0
    incubation_period_days: float = 0.0


@dataclass
class TreatmentPlan:
    """Peach disease treatment strategy"""
    fungicides: List[Dict[str, str]] = field(default_factory=list)
    bactericides: List[Dict[str, str]] = field(default_factory=list)
    cultural_controls: List[str] = field(default_factory=list)
    
    spray_interval_days: int = 14
    critical_timing: str = ""
    resistance_management: str = ""
    
    dormant_spray: bool = False  # Leaf curl
    bloom_spray: bool = False  # Brown rot blossom blight
    
    treatment_cost_per_hectare: float = 0.0
    expected_yield_protection: float = 0.0
    roi_ratio: float = 0.0


@dataclass
class DetectionResult:
    """Disease detection result"""
    disease: PeachDisease
    confidence: float
    severity: float
    affected_area_percent: float
    lesion_count: int
    lesions: List[PeachLesion]
    environmental_risk: EnvironmentalRisk
    treatment_plan: TreatmentPlan
    
    # Timing criticality
    dormant_spray_required: bool = False
    bloom_protection_critical: bool = False
    post_harvest_risk: bool = False
    
    timestamp: datetime = field(default_factory=datetime.now)


class PeachDiseaseDetector:
    """
    Advanced peach disease detection system
    
    CRITICAL FOCUS:
    - Brown rot rapid spread detection
    - Leaf curl dormant spray timing
    - Bacterial spot resistance management
    - Post-harvest disease prediction
    """
    
    def __init__(self):
        self.disease_database = self._initialize_disease_database()
        self.variety_resistance = self._initialize_variety_resistance()
        
    def _initialize_disease_database(self) -> Dict[PeachDisease, Dict]:
        """Comprehensive peach disease parameter database"""
        return {
            PeachDisease.BROWN_ROT: {
                'pathogen': 'Monilinia fructicola (primary USA), M. laxa, M. fructigena (Europe)',
                'pathogen_type': 'Fungus',
                'importance': '#1 STONE FRUIT DISEASE WORLDWIDE',
                'impact': 'Most economically damaging peach disease',
                'symptoms': [
                    'BLOSSOM BLIGHT: Brown wilted flowers (early season)',
                    'TWIG BLIGHT: Wilted shoots with gum',
                    'FRUIT ROT: Brown circular lesions (expand rapidly)',
                    'FUZZY GRAY-TAN SPORE MASSES on fruit (diagnostic)',
                    'Fruit mummification (shriveled fruit hangs on tree)',
                    'POST-HARVEST ROT: Rapid spread in storage'
                ],
                'diagnostic_features': [
                    'FUZZY GRAY-TAN SPORES in concentric rings (pathognomonic)',
                    'Rapid expansion (entire fruit rotted 48-72 hours)',
                    'Brown rot (not black)',
                    'Gum production on twigs',
                    'Mummies persist year to year (inoculum source)',
                    'Entire orchard can be lost in days near harvest'
                ],
                'lifecycle': {
                    'overwintering': 'Mummified fruit (on tree or ground), twig cankers',
                    'primary_infection': 'Blossom infection (spores or ascospores)',
                    'secondary_infection': 'Fruit-to-fruit spread (conidia)',
                    'sporulation': '24-48 hours on ripe fruit',
                    'spread': 'Rain splash, insects, contact'
                },
                'environmental': EnvironmentalRisk(
                    temperature_range=(15, 30),
                    humidity_threshold=85,
                    wetness_duration_hours=4,
                    rainfall_mm=2.5,
                    risk_level='CRITICAL',
                    infection_period_hours=4,
                    incubation_period_days=3
                ),
                'economic_impact': {
                    'pre_harvest_loss': '50-80% if untreated',
                    'post_harvest_loss': '30-50% in storage',
                    'usa_losses': '$160+ million annually',
                    'california': 'Major constraint (90% USA peaches)',
                    'south_carolina': 'Severe annual losses',
                    'georgia': '"Peach State" - brown rot primary challenge'
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Captan', 'active': 'captan', 'frac': 'M4', 'timing': 'bloom_to_harvest'},
                        {'name': 'Propiconazole', 'active': 'propiconazole', 'frac': '3', 'timing': 'bloom'},
                        {'name': 'Fenbuconazole', 'active': 'fenbuconazole', 'frac': '3', 'timing': 'pre_harvest'},
                        {'name': 'Azoxystrobin', 'active': 'azoxystrobin', 'frac': '11', 'timing': 'all_stages'},
                        {'name': 'Pyraclostrobin', 'active': 'pyraclostrobin', 'frac': '11', 'timing': 'pre_harvest'},
                        {'name': 'Fenhexamid', 'active': 'fenhexamid', 'frac': '17', 'timing': 'bloom'}
                    ],
                    cultural_controls=[
                        'REMOVE MUMMIES (critical - primary inoculum)',
                        'Remove mummies from tree and ground (destroy)',
                        'Prune dead twigs (twig blight cankers)',
                        'Thin fruit (reduce contact)',
                        'Avoid fruit injury',
                        'Rapid harvest when ripe',
                        'Cool storage immediately after harvest',
                        'Avoid overhead irrigation near harvest'
                    ],
                    spray_interval_days=7,  # Intensive pre-harvest
                    critical_timing='BLOOM (blossom blight) + 2-3 weeks PRE-HARVEST (fruit protection)',
                    resistance_management='CRITICAL: DMI (FRAC-3) and QoI (FRAC-11) resistance documented, rotate',
                    bloom_spray=True,
                    treatment_cost_per_hectare=1200.0,
                    expected_yield_protection=80.0,
                    roi_ratio=10.0
                ),
                'critical_periods': {
                    'bloom': 'Blossom blight prevention (kills flowers)',
                    'shuck_split': 'Young fruit infection',
                    'pre_harvest': 'MOST CRITICAL: 2-3 weeks before harvest, weekly sprays'
                },
                'resistance': {
                    'dmi_frac_3': 'Resistance documented (USA, Europe)',
                    'qoi_frac_11': 'Resistance emerging',
                    'management': 'Tank mixes essential, rotate FRAC groups'
                },
                'post_harvest': {
                    'cooling': 'Rapid cooling to 0-2°C stops development',
                    'ca_storage': 'Controlled atmosphere (low O2) reduces',
                    'hot_water': 'Not effective (damages fruit)',
                    'fungicide_dips': 'Limited efficacy post-harvest'
                },
                'notes': 'MOST CRITICAL SPRAYS: 2-3 weeks pre-harvest (weekly), entire crop can be lost in 72 hours'
            },
            
            PeachDisease.PEACH_LEAF_CURL: {
                'pathogen': 'Taphrina deformans',
                'pathogen_type': 'Fungus (unique - no mycelium, yeast-like)',
                'importance': 'Most distinctive peach disease',
                'unique': 'Only infects during bud swell (narrow window)',
                'symptoms': [
                    'THICK PUCKERED DISTORTED LEAVES (spring) - DIAGNOSTIC',
                    'RED to PURPLE discoloration (anthocyanins)',
                    'Leaves curl and twist',
                    'Whitish bloom on leaf surface (asci)',
                    'Premature leaf drop (defoliation)',
                    'Stunted shoot growth',
                    'Reduced fruit set',
                    'Weakened tree (winter injury susceptibility)'
                ],
                'diagnostic_features': [
                    'PUCKERED THICK DISTORTED LEAVES (pathognomonic)',
                    'Red-purple color',
                    'Appears in SPRING only (early season)',
                    'New growth may be normal if infection missed',
                    'Whitish bloom (asci with ascospores)',
                    'UNMISTAKABLE appearance'
                ],
                'lifecycle': {
                    'overwintering': 'Ascospores on bud scales, bark crevices',
                    'infection': 'ONLY during bud swell (spring rain + cool temps)',
                    'infection_window': 'Very narrow (2-4 weeks)',
                    'symptom_development': '2-3 weeks after infection',
                    'sporulation': 'Asci produce ascospores on leaf surface',
                    'no_summer_infection': 'Cannot infect open leaves'
                },
                'environmental': EnvironmentalRisk(
                    temperature_range=(10, 16),  # Cool temps favor
                    humidity_threshold=98,  # Rain required
                    wetness_duration_hours=12,
                    rainfall_mm=2.5,
                    risk_level='high',
                    infection_period_hours=12,
                    incubation_period_days=14
                ),
                'economic_impact': {
                    'defoliation': 'Up to 100% leaf loss',
                    'tree_weakness': 'Reduced winter hardiness',
                    'fruit_reduction': '30-50% reduced yield',
                    'multi_year_impact': 'Weakened trees over multiple years',
                    'control_cost': 'Low (single spray)'
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Chlorothalonil', 'active': 'chlorothalonil', 'frac': 'M5', 'timing': 'dormant'},
                        {'name': 'Copper', 'active': 'copper', 'frac': 'M1', 'timing': 'dormant'},
                        {'name': 'Lime sulfur', 'active': 'polysulfide', 'frac': 'M2', 'timing': 'dormant'},
                        {'name': 'Ziram', 'active': 'ziram', 'frac': 'M3', 'timing': 'dormant'}
                    ],
                    cultural_controls=[
                        'DORMANT SPRAY (single application) - MOST EFFECTIVE',
                        'Apply before bud swell (late fall or early spring)',
                        'Spray when dry weather forecast (2-3 days)',
                        'Complete coverage essential (buds, twigs)',
                        'Prune to improve coverage',
                        'Remove infected leaves (reduces inoculum)'
                    ],
                    spray_interval_days=0,  # Single spray
                    critical_timing='DORMANT (before bud swell) - SINGLE SPRAY CONTROLS',
                    resistance_management='No resistance issues',
                    dormant_spray=True,
                    treatment_cost_per_hectare=150.0,
                    expected_yield_protection=95.0,
                    roi_ratio=20.0  # Extremely high ROI (single cheap spray)
                ),
                'control_simplicity': {
                    'effectiveness': 'Single dormant spray 95%+ effective',
                    'timing': 'Before bud swell (narrow window)',
                    'cost': 'Very low ($150/hectare)',
                    'failure': 'Usually due to missed timing or poor coverage',
                    'rain_protection': 'Protects for entire season'
                },
                'timing_critical': {
                    'too_early': 'Rain washes off before bud swell',
                    'optimal': 'Just before bud swell (80-90% bud swelling)',
                    'too_late': 'After infection has occurred',
                    'weather': 'Apply when 2-3 days dry weather forecast'
                },
                'notes': 'EASIEST DISEASE TO CONTROL - single dormant spray 95%+ effective, timing critical'
            },
            
            PeachDisease.BACTERIAL_SPOT: {
                'pathogen': 'Xanthomonas arboricola pv. pruni',
                'pathogen_type': 'Bacteria',
                'importance': 'Major problem in eastern USA',
                'challenge': 'Copper resistance widespread',
                'symptoms': [
                    'SMALL ANGULAR LEAF SPOTS (water-soaked initially)',
                    'Purple-black leaf lesions',
                    'Leaf drop (defoliation)',
                    'FRUIT LESIONS: Small dark spots (sunken)',
                    'Fruit cracking at lesion sites',
                    'Twig cankers (winter)',
                    'Tree decline over years'
                ],
                'diagnostic_features': [
                    'ANGULAR LEAF SPOTS (veins limit spread)',
                    'Water-soaked appearance early',
                    'Purple-black color mature',
                    'Bacterial streaming in water',
                    'Shothole appearance (tissue drops out)',
                    'Fruit spots SUNKEN (vs raised fungal scab)'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(24, 30),
                    humidity_threshold=85,
                    wetness_duration_hours=1,  # Very short
                    rainfall_mm=2.5,
                    risk_level='high',
                    infection_period_hours=1,
                    incubation_period_days=7
                ),
                'economic_impact': {
                    'yield_loss': '20-50% in severe cases',
                    'fruit_quality': 'Cracked fruit unmarketable',
                    'defoliation': '50-80% leaf loss (weakens tree)',
                    'tree_decline': 'Progressive weakness over years',
                    'southeast_usa': 'Major problem (humid climate)',
                    'copper_resistance': 'Limits control options'
                },
                'treatment': TreatmentPlan(
                    bactericides=[
                        {'name': 'Copper', 'active': 'copper', 'frac': 'M1', 'note': 'Resistance widespread'},
                        {'name': 'Oxytetracycline', 'active': 'oxytet', 'frac': '41', 'timing': 'bloom'},
                        {'name': 'Kasugamycin', 'active': 'kasugamycin', 'frac': '24', 'timing': 'bloom'}
                    ],
                    cultural_controls=[
                        'Windbreaks (reduce wind-driven rain)',
                        'Avoid overhead irrigation',
                        'Prune for air circulation',
                        'Remove infected leaves',
                        'Winter sanitation (remove cankers)',
                        'Plant resistant varieties',
                        'Avoid excessive nitrogen'
                    ],
                    spray_interval_days=7,
                    critical_timing='Petal fall through shuck split',
                    resistance_management='CRITICAL: Copper resistance widespread, rotate antibiotics',
                    treatment_cost_per_hectare=900.0,
                    expected_yield_protection=60.0,
                    roi_ratio=4.5
                ),
                'copper_resistance': {
                    'prevalence': 'Widespread in major production areas',
                    'mechanism': 'Copper efflux pumps',
                    'alternatives': 'Oxytetracycline, kasugamycin (limited availability)',
                    'tank_mixes': 'Copper + antibiotic may improve'
                },
                'resistant_varieties': {
                    'more_resistant': ['Candor', 'Harbrite', 'Harken'],
                    'susceptible': ['Redhaven', 'Cresthaven'],
                    'note': 'No complete resistance available'
                },
                'notes': 'COPPER RESISTANCE CRISIS - limited effective control options remain'
            },
            
            PeachDisease.PEACH_SCAB: {
                'pathogen': 'Cladosporium carpophilum',
                'pathogen_type': 'Fungus',
                'importance': 'Cosmetic damage, export rejection',
                'symptoms': [
                    'OLIVE-GREEN VELVETY SPOTS on fruit (diagnostic)',
                    'Circular lesions (2-5mm)',
                    'Coalescence to large patches',
                    'Leaf spots (rare)',
                    'Twig lesions (olive-brown)'
                ],
                'diagnostic_features': [
                    'OLIVE-GREEN color (diagnostic)',
                    'VELVETY texture (conidia)',
                    'Fruit only (leaves rarely affected)',
                    'Cosmetic damage (fruit edible)'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(15, 25),
                    humidity_threshold=90,
                    wetness_duration_hours=24,
                    rainfall_mm=5.0,
                    risk_level='moderate',
                    infection_period_hours=24,
                    incubation_period_days=30
                ),
                'economic_impact': {
                    'fresh_market': 'Unmarketable (cosmetic damage)',
                    'processing': 'Acceptable (damage only cosmetic)',
                    'export': 'Rejection due to appearance',
                    'yield_loss': 'None (fruit edible)'
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Captan', 'active': 'captan', 'frac': 'M4'},
                        {'name': 'Sulfur', 'active': 'sulfur', 'frac': 'M2'},
                        {'name': 'Ziram', 'active': 'ziram', 'frac': 'M3'}
                    ],
                    cultural_controls=[
                        'Prune for air circulation',
                        'Remove infected twigs (overwintering)',
                        'Thin fruit'
                    ],
                    spray_interval_days=14,
                    critical_timing='Shuck split through pit hardening',
                    treatment_cost_per_hectare=600.0,
                    expected_yield_protection=90.0
                ),
                'notes': 'COSMETIC ONLY - fruit edible but unmarketable for fresh market'
            },
            
            PeachDisease.CYTOSPORA_CANKER: {
                'pathogen': 'Leucostoma cincta, L. persoonii',
                'pathogen_type': 'Fungus',
                'importance': 'Tree death',
                'symptoms': [
                    'GUM EXUDATION from cankers (diagnostic)',
                    'Sunken bark lesions',
                    'Branch dieback',
                    'Tree death (progressive)'
                ],
                'diagnostic_features': [
                    'GUMMY AMBER OOZE',
                    'Sunken cankers',
                    'Perennial (enlarges yearly)',
                    'Stress-related'
                ],
                'treatment': TreatmentPlan(
                    cultural_controls=[
                        'Avoid tree stress (water, nutrients)',
                        'Prune dead wood (summer - dry)',
                        'Avoid trunk injury',
                        'Winter protection',
                        'Remove severely infected trees'
                    ],
                    treatment_cost_per_hectare=400.0
                ),
                'notes': 'NO CHEMICAL CONTROL - stress management key'
            }
        }
    
    def _initialize_variety_resistance(self) -> Dict[PeachType, Dict]:
        """Variety-specific disease resistance"""
        return {
            PeachType.NECTARINE: {
                'brown_rot': 'MORE SUSCEPTIBLE (no fuzz protection)',
                'bacterial_spot': 'susceptible',
                'scab': 'susceptible',
                'note': 'Smooth skin increases disease susceptibility'
            },
            PeachType.YELLOW_FLESH_PEACH: {
                'brown_rot': 'susceptible',
                'bacterial_spot': 'variable by cultivar',
                'characteristics': 'Most common type'
            }
        }
    
    def detect_brown_rot(self, image: np.ndarray) -> Optional[DetectionResult]:
        """
        Detect Brown Rot (Monilinia fructicola)
        
        #1 STONE FRUIT DISEASE WORLDWIDE
        DIAGNOSTIC: Brown rot with fuzzy gray-tan spores
        CRITICAL: Entire crop can be lost in 48-72 hours
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Brown rot lesions
        lower_brown = np.array([10, 50, 40])
        upper_brown = np.array([25, 200, 150])
        brown_mask = cv2.inRange(hsv, lower_brown, upper_brown)
        
        # Fuzzy gray-tan spore masses
        lower_gray = np.array([0, 0, 100])
        upper_gray = np.array([180, 50, 200])
        gray_mask = cv2.inRange(hsv, lower_gray, upper_gray)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        brown_mask = cv2.morphologyEx(brown_mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(brown_mask, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) == 0:
            return None
        
        lesions = []
        total_area = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 300:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            
            # Check for fuzzy spores (increases confidence)
            roi_spores = gray_mask[y:y+h, x:x+w]
            has_spores = np.sum(roi_spores > 0) > (w * h * 0.15)
            
            lesion = PeachLesion(
                color_hsv_range=((10, 50, 40), (25, 200, 150)),
                shape='circular',
                texture='fuzzy' if has_spores else 'soft_rot',
                location='fruit',
                size_mm=(w * 0.2, h * 0.2),
                progression='rapid',
                margin='defined',
                brown_fuzzy_spores=has_spores,
                yield_loss_percent=100.0,
                fruit_quality_impact='unmarketable'
            )
            lesions.append(lesion)
            total_area += area
        
        affected_area = (total_area / (image.shape[0] * image.shape[1])) * 100
        
        # Brown rot with fuzzy spores diagnostic
        spore_count = sum(1 for l in lesions if l.brown_fuzzy_spores)
        confidence = min(0.75 + (spore_count / max(len(lesions), 1)) * 0.20, 0.95)
        
        disease_info = self.disease_database[PeachDisease.BROWN_ROT]
        
        result = DetectionResult(
            disease=PeachDisease.BROWN_ROT,
            confidence=confidence,
            severity=min(affected_area * 4, 100),
            affected_area_percent=affected_area,
            lesion_count=len(lesions),
            lesions=lesions,
            environmental_risk=disease_info['environmental'],
            treatment_plan=disease_info['treatment'],
            bloom_protection_critical=True,
            post_harvest_risk=True
        )
        
        return result
    
    def detect_peach_leaf_curl(self, image: np.ndarray) -> Optional[DetectionResult]:
        """
        Detect Peach Leaf Curl (Taphrina deformans)
        
        UNIQUE FUNGUS
        DIAGNOSTIC: Thick puckered distorted red-purple leaves
        EASIEST TO CONTROL: Single dormant spray 95%+ effective
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Red-purple distorted leaves
        lower_red1 = np.array([0, 50, 50])
        upper_red1 = np.array([10, 255, 200])
        lower_red2 = np.array([160, 50, 50])
        upper_red2 = np.array([180, 255, 200])
        
        red_mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        red_mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) == 0:
            return None
        
        lesions = []
        total_area = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 500:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            
            # Puckered appearance (irregular shape)
            perimeter = cv2.arcLength(contour, True)
            circularity = 0.0
            if perimeter > 0:
                circularity = (4 * np.pi * area) / (perimeter * perimeter)
            
            is_puckered = circularity < 0.5  # Irregular = puckered
            
            lesion = PeachLesion(
                color_hsv_range=((0, 50, 50), (10, 255, 200)),
                shape='irregular',
                texture='thick_puckered',
                location='leaf',
                size_mm=(w * 0.15, h * 0.15),
                progression='static',
                margin='diffuse',
                puckered_distorted=is_puckered,
                yield_loss_percent=40.0,
                fruit_quality_impact='blemish'
            )
            lesions.append(lesion)
            total_area += area
        
        affected_area = (total_area / (image.shape[0] * image.shape[1])) * 100
        
        # Red-purple puckered leaves diagnostic
        confidence = min(0.85 + (affected_area / 40) * 0.10, 0.95)
        
        disease_info = self.disease_database[PeachDisease.PEACH_LEAF_CURL]
        
        result = DetectionResult(
            disease=PeachDisease.PEACH_LEAF_CURL,
            confidence=confidence,
            severity=min(affected_area * 2, 100),
            affected_area_percent=affected_area,
            lesion_count=len(lesions),
            lesions=lesions,
            environmental_risk=disease_info['environmental'],
            treatment_plan=disease_info['treatment'],
            dormant_spray_required=True
        )
        
        return result


def main():
    """Example usage"""
    detector = PeachDiseaseDetector()
    
    print("=== AgroPulse Peach Disease Detection System ===")
    print(f"Monitoring {len(detector.disease_database)} major peach diseases")
    print("\nCRITICAL PATHOGENS:")
    print("1. Brown Rot - #1 STONE FRUIT DISEASE")
    print("   - 50-80% crop loss if untreated")
    print("   - Entire crop lost in 48-72 hours near harvest")
    print("   - $160+ million annual USA losses")
    print("\n2. Peach Leaf Curl - EASIEST TO CONTROL")
    print("   - Thick puckered red-purple leaves")
    print("   - Single dormant spray 95%+ effective")
    print("   - Timing critical (before bud swell)")
    print("\n3. Bacterial Spot - COPPER RESISTANCE")
    print("   - Angular leaf spots, fruit lesions")
    print("   - Copper resistance widespread")
    print("   - 20-50% yield loss")
    print("\nSYSTEM STATUS: Ready for orchard monitoring")


if __name__ == "__main__":
    main()
