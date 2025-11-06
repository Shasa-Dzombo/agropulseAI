"""
Apple Disease Detection Suite
Comprehensive detection system for apple diseases in greenhouse/orchard environments

CRITICAL DISEASES:

1. Apple Scab (Venturia inaequalis) - #1 APPLE DISEASE WORLDWIDE
   - $100+ million annual losses USA alone
   - Olive-green to black lesions on fruit and leaves
   - Primary infection from overwintered leaves (ascospores)
   - Secondary cycles every 7-14 days
   - Fungicide resistance widespread

2. Fire Blight (Erwinia amylovora) - BACTERIAL DEVASTATING
   - "Shepherd's crook" shoot blight diagnostic
   - Bacterial ooze (amber droplets)
   - Can kill entire tree in one season
   - Spreads during bloom via bees, rain
   - NO CURE - management only

3. Cedar Apple Rust (Gymnosporangium juniperi-virginianae)
   - Alternate host required (Eastern red cedar/juniper)
   - Orange gelatinous galls on cedar
   - Yellow-orange spots on apple leaves
   - Fruit lesions reduce marketability

4. Powdery Mildew (Podosphaera leucotricha) - SHOOT/LEAF DISEASE
   - White powdery growth
   - Terminal shoot infection
   - Overwintering in buds
   - Reduces tree vigor

5. Bitter Rot (Colletotrichum spp.) - FRUIT ROT
   - Sunken lesions with concentric rings
   - Post-harvest storage disease
   - Hot humid weather
   - Multiple infection cycles

DETECTION CHALLENGE:
- Scab requires infection period models (Mills table)
- Fire blight emergency response (24-48 hour spread)
- Rust requires alternate host knowledge
- Multiple diseases with similar leaf spots (differential diagnosis)

Author: AgroPulse AI Team
Version: 1.0.0
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class AppleDisease(Enum):
    """Comprehensive apple disease classification"""
    APPLE_SCAB = "apple_scab"  # Venturia inaequalis - #1 worldwide
    FIRE_BLIGHT = "fire_blight"  # Erwinia amylovora - BACTERIAL LETHAL
    CEDAR_APPLE_RUST = "cedar_apple_rust"  # Gymnosporangium - alternate host
    POWDERY_MILDEW = "powdery_mildew"  # Podosphaera leucotricha
    BITTER_ROT = "bitter_rot"  # Colletotrichum - fruit rot
    BROOKS_FRUIT_SPOT = "brooks_fruit_spot"  # Mycosphaerella pomi
    BLACK_ROT = "black_rot"  # Botryosphaeria obtusa - frog eye
    WHITE_ROT = "white_rot"  # Botryosphaeria dothidea
    SOOTY_BLOTCH = "sooty_blotch"  # Complex - cosmetic
    FLYSPECK = "flyspeck"  # Zygophiala jamaicensis - cosmetic
    CROWN_ROT = "crown_rot"  # Phytophthora cactorum
    ALTERNARIA_BLOTCH = "alternaria_blotch"  # Alternaria alternata
    APPLE_MOSAIC_VIRUS = "apple_mosaic_virus"  # ApMV
    APPLE_CHLOROTIC_LEAF_SPOT_VIRUS = "apple_chlorotic_leaf_spot_virus"  # ACLSV


class AppleVarietyType(Enum):
    """Apple variety classifications"""
    FRESH_MARKET_RED = "fresh_market_red"  # Red Delicious, Gala, Fuji
    FRESH_MARKET_YELLOW = "fresh_market_yellow"  # Golden Delicious
    FRESH_MARKET_GREEN = "fresh_market_green"  # Granny Smith
    PROCESSING = "processing"  # Sauce, juice varieties
    CIDER = "cider"  # High tannin varieties
    HEIRLOOM = "heirloom"  # Heritage varieties
    STORAGE = "storage"  # Long storage capability


@dataclass
class AppleLesion:
    """Apple disease lesion characteristics"""
    color_hsv_range: Tuple[Tuple[int, int, int], Tuple[int, int, int]]
    shape: str  # circular, irregular, angular
    texture: str  # velvety, corky, sunken, raised, powdery
    location: str  # leaf, fruit, shoot, blossom
    size_mm: Tuple[float, float]
    progression: str  # expanding, static, coalescing
    margin: str  # defined, feathery, chlorotic_halo
    
    # Diagnostic features
    velvety_olive_growth: bool = False  # Apple scab
    bacterial_ooze: bool = False  # Fire blight
    shepherds_crook: bool = False  # Fire blight shoot
    orange_rust_spots: bool = False  # Cedar apple rust
    white_powdery_growth: bool = False  # Powdery mildew
    concentric_rings: bool = False  # Bitter rot, black rot
    
    # Economic impact
    yield_loss_percent: float = 0.0
    fruit_marketability: str = "grade_A"  # grade_A, grade_B, processing, unmarketable
    cosmetic_only: bool = False  # Sooty blotch, flyspeck


@dataclass
class AppleFruitDisease:
    """Fruit-specific disease parameters"""
    fruit_symptoms: List[str]
    infection_timing: str  # bloom, petal_fall, fruit_set, pre_harvest
    storage_disease: bool  # Develops or worsens in storage
    cosmetic_vs_decay: str  # cosmetic, decay, both
    
    # Market impact
    fresh_market_acceptable: bool = True
    processing_acceptable: bool = True
    storage_life_impact: str  # none, reduced, severe


@dataclass
class EnvironmentalRisk:
    """Environmental factors for apple disease risk"""
    temperature_range: Tuple[float, float]
    humidity_threshold: float
    leaf_wetness_hours: float
    rainfall_trigger_mm: float
    
    risk_level: str = "low"
    infection_period_hours: float = 0.0
    incubation_period_days: float = 0.0
    
    # Scab-specific (Mills table)
    mills_period: bool = False  # Scab infection period


@dataclass
class TreatmentPlan:
    """Apple disease treatment strategy"""
    fungicides: List[Dict[str, str]] = field(default_factory=list)
    bactericides: List[Dict[str, str]] = field(default_factory=list)
    antibiotics: List[Dict[str, str]] = field(default_factory=list)
    cultural_controls: List[str] = field(default_factory=list)
    
    spray_interval_days: int = 7
    resistance_management: str = ""
    
    # Timing critical
    phenological_timing: str = ""  # green_tip, pink, bloom, petal_fall
    pre_harvest_interval: int = 0
    
    treatment_cost_per_acre: float = 0.0
    expected_yield_protection: float = 0.0
    roi_ratio: float = 0.0


@dataclass
class DetectionResult:
    """Disease detection result"""
    disease: AppleDisease
    confidence: float
    severity: float
    affected_area_percent: float
    lesion_count: int
    lesions: List[AppleLesion]
    environmental_risk: EnvironmentalRisk
    treatment_plan: TreatmentPlan
    
    # Tree health
    tree_vigor_impact: str = "none"  # none, minor, moderate, severe
    emergency_response: bool = False  # Fire blight
    
    # Variety-specific
    variety_susceptibility: str = "unknown"
    resistance_genes: List[str] = field(default_factory=list)
    
    timestamp: datetime = field(default_factory=datetime.now)


class AppleDiseaseDetector:
    """
    Advanced apple disease detection system
    
    CRITICAL FOCUS:
    - Scab infection period prediction (Mills table)
    - Fire blight emergency response
    - Cedar rust alternate host management
    - Fruit quality disease differentiation
    """
    
    def __init__(self):
        self.disease_database = self._initialize_disease_database()
        self.variety_resistance = self._initialize_variety_resistance()
        self.scab_infection_model = self._initialize_mills_table()
        
    def _initialize_disease_database(self) -> Dict[AppleDisease, Dict]:
        """Comprehensive apple disease parameter database"""
        return {
            AppleDisease.APPLE_SCAB: {
                'pathogen': 'Venturia inaequalis',
                'pathogen_type': 'Fungus (Ascomycete)',
                'global_importance': '#1 APPLE DISEASE WORLDWIDE',
                'economic_loss': '$100+ million annually (USA alone)',
                'symptoms': [
                    'Olive-green to black velvety lesions on leaves',
                    'Circular to irregular lesions',
                    'Severe: Leaf distortion and premature drop',
                    'Fruit: Corky brown to black lesions',
                    'Fruit cracking around lesions',
                    'Storage rot can develop from lesions'
                ],
                'diagnostic_features': [
                    'VELVETY OLIVE-GREEN growth (conidia)',
                    'Primary infection from overwintered leaves (ascospores)',
                    'Secondary cycles every 7-14 days (conidia)',
                    'Mills infection periods (temp + wetness)',
                    'Early infections most damaging'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(6, 24),
                    humidity_threshold=95,
                    leaf_wetness_hours=9,  # Varies by temp (Mills table)
                    rainfall_trigger_mm=2.5,
                    risk_level='high',
                    infection_period_hours=9,
                    incubation_period_days=9,
                    mills_period=True
                ),
                'mills_infection_table': {
                    # Temperature (°C) : Hours of leaf wetness required
                    '6-7°C': 28,
                    '8-10°C': 19,
                    '11-13°C': 14,
                    '14-16°C': 12,
                    '17-20°C': 9,
                    '21-24°C': 9,
                    'above_24°C': 'infection_unlikely'
                },
                'economic_impact': {
                    'yield_loss': '10-70% if untreated',
                    'fruit_quality': 'Severe marketability loss',
                    'fungicide_cost': '$300-600/acre/season',
                    'organic_challenge': 'Most difficult disease for organic'
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Captan', 'active': 'captan', 'frac': 'M4'},
                        {'name': 'Mancozeb', 'active': 'mancozeb', 'frac': 'M3'},
                        {'name': 'Rally', 'active': 'myclobutanil', 'frac': '3'},
                        {'name': 'Flint', 'active': 'trifloxystrobin', 'frac': '11'},
                        {'name': 'Inspire Super', 'active': 'difenoconazole+cyprodinil', 'frac': '3+9'},
                        {'name': 'Luna Sensation', 'active': 'fluopyram+trifloxystrobin', 'frac': '7+11'},
                        {'name': 'Fontelis', 'active': 'penthiopyrad', 'frac': '7'}
                    ],
                    cultural_controls=[
                        'CRITICAL: Remove fallen leaves (primary inoculum)',
                        'Leaf shredding (accelerate decomposition)',
                        'Urea application to fallen leaves (5% solution)',
                        'Prune to improve air circulation',
                        'Use resistant varieties',
                        'Avoid overhead irrigation'
                    ],
                    spray_interval_days=7,
                    resistance_management='CRITICAL: DMI (3) and QoI (11) resistance widespread, rotate FRAC groups',
                    phenological_timing='Start: Green tip, Continue through petal fall + 2 weeks',
                    pre_harvest_interval=14,
                    treatment_cost_per_acre=500.0,
                    expected_yield_protection=85.0,
                    roi_ratio=7.0
                ),
                'resistance_crisis': {
                    'frac_3_resistance': 'DMI resistance widespread',
                    'frac_11_resistance': 'QoI resistance common',
                    'management': 'Multi-site protectants (captan, mancozeb) essential backbone'
                },
                'notes': 'PRIMARY INFECTION control (green tip through petal fall) most critical'
            },
            
            AppleDisease.FIRE_BLIGHT: {
                'pathogen': 'Erwinia amylovora',
                'pathogen_type': 'Bacteria',
                'threat_level': 'DEVASTATING - CAN KILL ENTIRE TREE',
                'symptoms': [
                    '"SHEPHERD\'S CROOK" shoot blight (DIAGNOSTIC)',
                    'Blackened blossoms and shoots',
                    'BACTERIAL OOZE (amber droplets) on cankers',
                    'Shoot tips wilted, curved downward',
                    'Cankers on branches and trunk',
                    'Tree death possible in severe infections'
                ],
                'diagnostic_features': [
                    'SHEPHERD\'S CROOK - pathognomonic sign',
                    'BACTERIAL OOZE (milky to amber)',
                    'Blackened tissue (not brown)',
                    'Rapid spread during bloom',
                    'Bees spread bacteria during pollination',
                    'Warm wet weather (18-28°C with rain)'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(18, 30),
                    humidity_threshold=70,
                    leaf_wetness_hours=2,
                    rainfall_trigger_mm=2.5,
                    risk_level='CRITICAL',
                    infection_period_hours=4,
                    incubation_period_days=3
                ),
                'economic_impact': {
                    'tree_loss': 'Can kill entire tree in one season',
                    'orchard_loss': 'Can destroy young orchards',
                    'nursery_threat': 'Severe losses in nurseries',
                    'quarantine': 'Movement restrictions in some regions'
                },
                'treatment': TreatmentPlan(
                    antibiotics=[
                        {'name': 'Streptomycin', 'active': 'streptomycin sulfate', 'note': 'Most effective'},
                        {'name': 'Kasumin', 'active': 'kasugamycin', 'note': 'Alternative'},
                        {'name': 'Oxytetracycline', 'active': 'oxytetracycline', 'note': 'Resistance concerns'}
                    ],
                    bactericides=[
                        {'name': 'Copper', 'active': 'copper hydroxide', 'note': 'Suppression only'},
                        {'name': 'Blossom Protect', 'active': 'Aureobasidium pullulans', 'note': 'Biological'}
                    ],
                    cultural_controls=[
                        'PRUNE OUT INFECTIONS IMMEDIATELY (12-24" below visible symptoms)',
                        'Disinfect pruning tools between cuts (10% bleach)',
                        'Remove infected trees if severe',
                        'Avoid excessive nitrogen (succulent growth)',
                        'Use resistant rootstocks and varieties',
                        'Remove fire blight hosts nearby (hawthorn, pear)',
                        'Hail damage = entry points'
                    ],
                    spray_interval_days=3,  # BLOOM: Every 3-4 days
                    resistance_management='Streptomycin resistance emerging in some regions',
                    phenological_timing='CRITICAL: Bloom sprays (every 3-4 days during bloom)',
                    pre_harvest_interval=30,
                    treatment_cost_per_acre=200.0,
                    expected_yield_protection=60.0,
                    roi_ratio=8.0
                ),
                'infection_model': {
                    'maryblyt': 'Prediction model (blossom blight risk)',
                    'cougarblight': 'Regional prediction system',
                    'trauma_blight': 'Hail and wind damage infection periods'
                },
                'notes': 'EMERGENCY DISEASE - 24-48 hour response window during bloom'
            },
            
            AppleDisease.CEDAR_APPLE_RUST: {
                'pathogen': 'Gymnosporangium juniperi-virginianae',
                'pathogen_type': 'Fungus (Rust - heteroecious)',
                'alternate_host': 'Eastern red cedar (Juniperus virginiana)',
                'lifecycle': '2-year cycle requiring both apple and cedar',
                'symptoms': [
                    'BRIGHT ORANGE-YELLOW spots on apple leaves (upper surface)',
                    'Spots enlarge, develop small black dots (spermogonia)',
                    'Cluster cups on leaf underside (aecia)',
                    'Fruit lesions: Dimpled, orange spots',
                    'Cedar: Orange gelatinous galls (telial horns) in spring'
                ],
                'diagnostic_features': [
                    'BRIGHT ORANGE color distinctive',
                    'Cedar galls (golf ball size) with orange jelly horns',
                    'Requires both hosts within 2-4 miles',
                    'Spring infection (spores from cedar)',
                    'One infection cycle per year'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(15, 24),
                    humidity_threshold=95,
                    leaf_wetness_hours=4,
                    rainfall_trigger_mm=2.5,
                    risk_level='moderate',
                    infection_period_hours=4,
                    incubation_period_days=14
                ),
                'economic_impact': {
                    'yield_loss': '5-30% in severe cases',
                    'fruit_quality': 'Reduced marketability (blemishes)',
                    'defoliation': 'Premature leaf drop reduces tree vigor'
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Rally', 'active': 'myclobutanil', 'frac': '3'},
                        {'name': 'Immunox', 'active': 'myclobutanil', 'frac': '3'},
                        {'name': 'Bayleton', 'active': 'triadimefon', 'frac': '3'},
                        {'name': 'Mancozeb', 'active': 'mancozeb', 'frac': 'M3'}
                    ],
                    cultural_controls=[
                        'REMOVE CEDAR TREES within 2-4 miles (if practical)',
                        'Remove galls from cedar in winter',
                        'Use resistant apple varieties',
                        'Plant cedar-free if establishing new orchard'
                    ],
                    spray_interval_days=7,
                    resistance_management='DMI fungicides effective, rotate with multi-site',
                    phenological_timing='Pink through 2 weeks post petal fall',
                    pre_harvest_interval=14,
                    treatment_cost_per_acre=150.0,
                    expected_yield_protection=70.0,
                    roi_ratio=5.0
                ),
                'alternate_host_management': {
                    'cedar_removal': 'Most effective long-term control',
                    'gall_removal': 'Labor intensive but reduces inoculum',
                    'cedar_sprays': 'Generally not practical'
                },
                'notes': 'Management on APPLE side only - cedar removal most effective'
            },
            
            AppleDisease.POWDERY_MILDEW: {
                'pathogen': 'Podosphaera leucotricha',
                'pathogen_type': 'Fungus',
                'symptoms': [
                    'WHITE POWDERY growth on leaves, shoots, blossoms',
                    'Terminal shoots stunted and distorted',
                    'Leaves curled, narrowed, thickened',
                    'Fruit: Russeted patches (cosmetic)',
                    'Overwinters in infected buds'
                ],
                'diagnostic_features': [
                    'WHITE POWDERY coating',
                    'Terminal shoot infection characteristic',
                    'Dry weather disease (vs downy mildew)',
                    'Infected buds fail to open properly',
                    'Secondary shoots proliferate (rosette)'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(10, 25),
                    humidity_threshold=70,
                    leaf_wetness_hours=0,  # No free water needed
                    rainfall_trigger_mm=0,
                    risk_level='moderate',
                    infection_period_hours=3,
                    incubation_period_days=7
                ),
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Sulfur', 'active': 'sulfur', 'frac': 'M2'},
                        {'name': 'Rally', 'active': 'myclobutanil', 'frac': '3'},
                        {'name': 'Procure', 'active': 'triflumizole', 'frac': '3'},
                        {'name': 'Luna Sensation', 'active': 'fluopyram+trifloxystrobin', 'frac': '7+11'}
                    ],
                    cultural_controls=[
                        'Prune out infected shoots in winter',
                        'Remove mummified fruit',
                        'Avoid excessive nitrogen',
                        'Use resistant varieties'
                    ],
                    spray_interval_days=10,
                    phenological_timing='Green tip through bloom',
                    treatment_cost_per_acre=200.0,
                    expected_yield_protection=75.0,
                    roi_ratio=5.5
                )
            },
            
            AppleDisease.BITTER_ROT: {
                'pathogen': 'Colletotrichum spp. (C. gloeosporioides, C. acutatum)',
                'pathogen_type': 'Fungus',
                'importance': 'MAJOR FRUIT ROT in hot humid climates',
                'symptoms': [
                    'SUNKEN CIRCULAR LESIONS on fruit',
                    'Light brown with darker border',
                    'CONCENTRIC RINGS of spore masses (salmon/pink)',
                    'V-shaped rot into fruit core',
                    'Fruit mummifies on tree',
                    'Storage rot from latent infections'
                ],
                'diagnostic_features': [
                    'CONCENTRIC RINGS of acervuli (spore masses)',
                    'BITTER TASTE of infected fruit',
                    'Hot weather disease (25-30°C)',
                    'Multiple infection cycles',
                    'Latent infections common (symptomless at harvest)'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(25, 32),
                    humidity_threshold=85,
                    leaf_wetness_hours=12,
                    rainfall_trigger_mm=10,
                    risk_level='high',
                    infection_period_hours=12,
                    incubation_period_days=14
                ),
                'economic_impact': {
                    'fruit_loss': '10-80% in hot humid years',
                    'storage_loss': 'Latent infections develop in storage',
                    'regional_importance': 'Southeastern USA major problem'
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Captan', 'active': 'captan', 'frac': 'M4'},
                        {'name': 'Ziram', 'active': 'ziram', 'frac': 'M3'},
                        {'name': 'Pristine', 'active': 'pyraclostrobin+boscalid', 'frac': '11+7'},
                        {'name': 'Merivon', 'active': 'fluxapyroxad+pyraclostrobin', 'frac': '7+11'}
                    ],
                    cultural_controls=[
                        'Remove mummified fruit (primary inoculum)',
                        'Prune to improve air circulation',
                        'Avoid wounding fruit',
                        'Harvest at proper maturity',
                        'Rapid cooling post-harvest'
                    ],
                    spray_interval_days=10,
                    resistance_management='Multi-site protectants essential',
                    phenological_timing='Petal fall through pre-harvest',
                    pre_harvest_interval=7,
                    treatment_cost_per_acre=250.0,
                    expected_yield_protection=70.0,
                    roi_ratio=6.0
                ),
                'fruit_disease': AppleFruitDisease(
                    fruit_symptoms=['sunken_lesions', 'concentric_rings', 'mummification'],
                    infection_timing='fruit_set',
                    storage_disease=True,
                    cosmetic_vs_decay='decay',
                    fresh_market_acceptable=False,
                    processing_acceptable=False,
                    storage_life_impact='severe'
                )
            },
            
            AppleDisease.BLACK_ROT: {
                'pathogen': 'Botryosphaeria obtusa (anamorph: Diplodia seriata)',
                'pathogen_type': 'Fungus',
                'symptoms': [
                    '"FROG EYE" leaf spots (circular with purple border)',
                    'Fruit: Firm brown rot',
                    'Target pattern (concentric rings)',
                    'Limb cankers',
                    'Black rot advances from calyx or stem end'
                ],
                'diagnostic_features': [
                    'FROG EYE leaf spots',
                    'Fruit rot firm (not soft)',
                    'Black pycnidia on fruit',
                    'Cankers on limbs'
                ],
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Captan', 'active': 'captan', 'frac': 'M4'},
                        {'name': 'Ziram', 'active': 'ziram', 'frac': 'M3'}
                    ],
                    cultural_controls=[
                        'Prune out cankers',
                        'Remove mummified fruit',
                        'Sanitation critical'
                    ],
                    spray_interval_days=10,
                    treatment_cost_per_acre=180.0,
                    expected_yield_protection=65.0,
                    roi_ratio=4.5
                )
            },
            
            AppleDisease.SOOTY_BLOTCH: {
                'pathogen': 'Complex of fungi (Peltaster, Geastrumia, Leptodontium)',
                'pathogen_type': 'Fungus complex',
                'importance': 'COSMETIC ONLY - no decay',
                'symptoms': [
                    'Dark olive to black smudges on fruit surface',
                    'Rubs off with effort',
                    'No penetration into fruit',
                    'Often with flyspeck'
                ],
                'diagnostic_features': [
                    'COSMETIC only (eating quality unaffected)',
                    'Late season (August-September)',
                    'Cool wet weather',
                    'Poor air circulation'
                ],
                'economic_impact': {
                    'yield_loss': '0%',
                    'fresh_market': 'Unmarketable appearance',
                    'processing': 'Acceptable for juice/sauce'
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Captan', 'active': 'captan', 'frac': 'M4'},
                        {'name': 'Ziram', 'active': 'ziram', 'frac': 'M3'}
                    ],
                    cultural_controls=[
                        'Prune to improve air circulation',
                        'Weed control around trees'
                    ],
                    spray_interval_days=14,
                    treatment_cost_per_acre=120.0,
                    expected_yield_protection=100.0,
                    roi_ratio=8.0
                ),
                'fruit_disease': AppleFruitDisease(
                    fruit_symptoms=['dark_smudges', 'surface_only'],
                    infection_timing='pre_harvest',
                    storage_disease=False,
                    cosmetic_vs_decay='cosmetic',
                    fresh_market_acceptable=False,
                    processing_acceptable=True,
                    storage_life_impact='none'
                )
            }
        }
    
    def _initialize_variety_resistance(self) -> Dict[AppleVarietyType, Dict]:
        """Variety-specific disease resistance"""
        return {
            AppleVarietyType.FRESH_MARKET_RED: {
                'varieties': ['Gala', 'Fuji', 'Honeycrisp'],
                'scab_resistance': 'susceptible (no Vf gene)',
                'fire_blight': 'Honeycrisp highly susceptible',
                'cedar_rust': 'susceptible',
                'notes': 'Require intensive spray programs'
            },
            AppleVarietyType.FRESH_MARKET_GREEN: {
                'varieties': ['Granny Smith'],
                'scab_resistance': 'susceptible',
                'fire_blight': 'moderate resistance',
                'bitter_rot': 'susceptible',
                'notes': 'Scab management critical'
            }
        }
    
    def _initialize_mills_table(self) -> Dict[int, int]:
        """Mills infection period table for apple scab"""
        return {
            # Temperature (°C) : Minimum hours of leaf wetness for infection
            6: 28, 7: 28, 8: 19, 9: 19, 10: 19,
            11: 14, 12: 14, 13: 14, 14: 12, 15: 12,
            16: 12, 17: 9, 18: 9, 19: 9, 20: 9,
            21: 9, 22: 9, 23: 9, 24: 9
        }
    
    def detect_apple_scab(self, image: np.ndarray,
                         environmental_data: Dict) -> Optional[DetectionResult]:
        """
        Detect Apple Scab (Venturia inaequalis)
        
        #1 APPLE DISEASE WORLDWIDE
        DIAGNOSTIC: Velvety olive-green lesions
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Olive-green to black velvety lesions
        lower_lesion = np.array([30, 40, 40])
        upper_lesion = np.array([80, 180, 120])
        lesion_mask = cv2.inRange(hsv, lower_lesion, upper_lesion)
        
        # Morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        lesion_mask = cv2.morphologyEx(lesion_mask, cv2.MORPH_CLOSE, kernel)
        lesion_mask = cv2.morphologyEx(lesion_mask, cv2.MORPH_OPEN, kernel)
        
        contours, _ = cv2.findContours(lesion_mask, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) == 0:
            return None
        
        lesions = []
        total_area = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 100:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            
            lesion = AppleLesion(
                color_hsv_range=((30, 40, 40), (80, 180, 120)),
                shape='circular',
                texture='velvety',
                location='leaf',
                size_mm=(w * 0.1, h * 0.1),
                progression='expanding',
                margin='defined',
                velvety_olive_growth=True,
                yield_loss_percent=40.0,
                fruit_marketability='grade_B'
            )
            lesions.append(lesion)
            total_area += area
        
        affected_area = (total_area / (image.shape[0] * image.shape[1])) * 100
        
        # Check Mills infection period
        temp = environmental_data.get('temperature', 20)
        leaf_wetness = environmental_data.get('leaf_wetness_hours', 0)
        
        mills_threshold = self.scab_infection_model.get(int(temp), 9)
        mills_infection = leaf_wetness >= mills_threshold
        
        confidence = min(0.6 + (affected_area / 40) * 0.25, 0.90)
        if mills_infection:
            confidence = min(confidence + 0.05, 0.95)
        
        disease_info = self.disease_database[AppleDisease.APPLE_SCAB]
        
        result = DetectionResult(
            disease=AppleDisease.APPLE_SCAB,
            confidence=confidence,
            severity=min(affected_area * 1.8, 100),
            affected_area_percent=affected_area,
            lesion_count=len(lesions),
            lesions=lesions,
            environmental_risk=disease_info['environmental'],
            treatment_plan=disease_info['treatment'],
            tree_vigor_impact='moderate'
        )
        
        return result
    
    def detect_fire_blight(self, image: np.ndarray) -> Optional[DetectionResult]:
        """
        Detect Fire Blight (Erwinia amylovora)
        
        DEVASTATING BACTERIAL DISEASE
        DIAGNOSTIC: Shepherd's crook + bacterial ooze
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Blackened tissue
        lower_black = np.array([0, 0, 0])
        upper_black = np.array([180, 255, 60])
        black_mask = cv2.inRange(hsv, lower_black, upper_black)
        
        # Look for curved shoot structures (shepherd's crook)
        edges = cv2.Canny(gray, 50, 150)
        
        contours, _ = cv2.findContours(black_mask, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) == 0:
            return None
        
        lesions = []
        total_area = 0
        shepherds_crook_detected = False
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 200:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            
            # Check for curved structure
            aspect_ratio = h / w if w > 0 else 0
            if aspect_ratio > 2.0:  # Vertical shoot
                # Analyze curvature
                roi_edges = edges[y:y+h, x:x+w]
                if np.sum(roi_edges > 0) > (h * 0.3):
                    shepherds_crook_detected = True
            
            lesion = AppleLesion(
                color_hsv_range=((0, 0, 0), (180, 255, 60)),
                shape='irregular',
                texture='necrotic',
                location='shoot',
                size_mm=(w * 0.1, h * 0.1),
                progression='expanding',
                margin='defined',
                shepherds_crook=shepherds_crook_detected,
                bacterial_ooze=False,  # Would need close-up detection
                yield_loss_percent=100.0,
                fruit_marketability='unmarketable'
            )
            lesions.append(lesion)
            total_area += area
        
        if len(lesions) == 0:
            return None
        
        affected_area = (total_area / (image.shape[0] * image.shape[1])) * 100
        
        # Shepherd's crook is DIAGNOSTIC
        confidence = min(0.6 + (len(lesions) / 5) * 0.2, 0.85)
        if shepherds_crook_detected:
            confidence = min(confidence + 0.15, 0.95)
        
        disease_info = self.disease_database[AppleDisease.FIRE_BLIGHT]
        
        result = DetectionResult(
            disease=AppleDisease.FIRE_BLIGHT,
            confidence=confidence,
            severity=100.0,  # Always severe
            affected_area_percent=affected_area,
            lesion_count=len(lesions),
            lesions=lesions,
            environmental_risk=disease_info['environmental'],
            treatment_plan=disease_info['treatment'],
            emergency_response=True,
            tree_vigor_impact='severe'
        )
        
        return result
    
    def detect_cedar_apple_rust(self, image: np.ndarray) -> Optional[DetectionResult]:
        """
        Detect Cedar Apple Rust (Gymnosporangium juniperi-virginianae)
        
        DIAGNOSTIC: Bright orange-yellow spots
        Requires alternate host (Eastern red cedar)
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Bright orange-yellow rust spots
        lower_orange = np.array([10, 100, 120])
        upper_orange = np.array([30, 255, 255])
        orange_mask = cv2.inRange(hsv, lower_orange, upper_orange)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        orange_mask = cv2.morphologyEx(orange_mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(orange_mask, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) == 0:
            return None
        
        lesions = []
        total_area = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 80:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            
            lesion = AppleLesion(
                color_hsv_range=((10, 100, 120), (30, 255, 255)),
                shape='circular',
                texture='raised',
                location='leaf',
                size_mm=(w * 0.1, h * 0.1),
                progression='static',
                margin='defined',
                orange_rust_spots=True,
                yield_loss_percent=20.0,
                fruit_marketability='grade_B'
            )
            lesions.append(lesion)
            total_area += area
        
        affected_area = (total_area / (image.shape[0] * image.shape[1])) * 100
        
        # Bright orange color is DISTINCTIVE
        confidence = min(0.7 + (affected_area / 30) * 0.2, 0.95)
        
        disease_info = self.disease_database[AppleDisease.CEDAR_APPLE_RUST]
        
        result = DetectionResult(
            disease=AppleDisease.CEDAR_APPLE_RUST,
            confidence=confidence,
            severity=min(affected_area * 1.5, 100),
            affected_area_percent=affected_area,
            lesion_count=len(lesions),
            lesions=lesions,
            environmental_risk=disease_info['environmental'],
            treatment_plan=disease_info['treatment'],
            tree_vigor_impact='minor'
        )
        
        return result


def main():
    """Example usage"""
    detector = AppleDiseaseDetector()
    
    print("=== AgroPulse Apple Disease Detection System ===")
    print(f"Monitoring {len(detector.disease_database)} major apple diseases")
    print("\nCRITICAL PATHOGENS:")
    print("1. Apple Scab - #1 disease worldwide")
    print("   - $100+ million annual losses")
    print("   - Mills infection period model integrated")
    print("\n2. Fire Blight - BACTERIAL DEVASTATING")
    print("   - Shepherd's crook diagnostic")
    print("   - Can kill entire tree")
    print("\n3. Cedar Apple Rust - Alternate host required")
    print("   - Bright orange spots")
    print("   - Cedar removal most effective")
    print("\nSYSTEM STATUS: Ready for orchard monitoring")


if __name__ == "__main__":
    main()
