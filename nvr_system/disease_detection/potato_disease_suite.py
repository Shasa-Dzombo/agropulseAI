"""
Potato Disease Detection Suite
Comprehensive detection system for potato diseases in greenhouse environments

Potato is the world's 4th most important food crop after rice, wheat, and maize.
Disease management is critical as pathogens can destroy entire crops rapidly.

CRITICAL DISEASES:
1. Late Blight (Phytophthora infestans) - HISTORIC "IRISH FAMINE" PATHOGEN
   - Can destroy crop in 7-10 days under ideal conditions
   - Caused Irish Potato Famine 1845-1852 (1M deaths)
   - Still causes $6.7 billion annual losses globally
   - Requires emergency response protocols

2. Early Blight (Alternaria solani) - BULL'S-EYE LESIONS
   - Most common potato disease worldwide
   - Concentric ring pattern diagnostic
   - Defoliates plants, reduces tuber size
   
3. Blackleg (Pectobacterium spp.) - BACTERIAL SEED-BORNE
   - Seed potato contamination critical
   - Black rot up stem from soil
   - Zero tolerance for seed certification
   
4. Common Scab (Streptomyces scabies) - CORKY LESIONS
   - Bacterial soil-borne disease
   - Reduced market value (cosmetic)
   - pH >5.2 favors disease
   
5. Pink Rot (Phytophthora erythroseptica) - TUBER ROT
   - Wet soil conditions
   - Pink flesh when cut open
   - Storage rot threat

DETECTION CHALLENGE:
- Late blight requires 24/7 monitoring (can spread overnight)
- Early detection (pre-sporulation) saves crop
- Seed potato health determines season outcome
- Storage diseases reduce marketable yield

Author: AgroPulse AI Team
Version: 1.0.0
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class PotatoDisease(Enum):
    """Comprehensive potato disease classification"""
    LATE_BLIGHT = "late_blight"  # Phytophthora infestans - EMERGENCY PATHOGEN
    EARLY_BLIGHT = "early_blight"  # Alternaria solani - bull's-eye lesions
    BLACKLEG = "blackleg"  # Pectobacterium - bacterial seed-borne
    COMMON_SCAB = "common_scab"  # Streptomyces - corky lesions
    PINK_ROT = "pink_rot"  # Phytophthora erythroseptica - tuber
    VERTICILLIUM_WILT = "verticillium_wilt"  # Soil-borne vascular
    FUSARIUM_DRY_ROT = "fusarium_dry_rot"  # Storage tuber rot
    BACTERIAL_SOFT_ROT = "bacterial_soft_rot"  # Erwinia - wet rot
    POWDERY_MILDEW = "powdery_mildew"  # White fungal growth
    GRAY_MOLD = "gray_mold"  # Botrytis cinerea
    POTATO_VIRUS_Y = "potato_virus_y"  # PVY - aphid-transmitted
    POTATO_LEAFROLL_VIRUS = "potato_leafroll_virus"  # PLRV - persistent
    POTATO_VIRUS_X = "potato_virus_x"  # PVX - mechanical transmission
    RHIZOCTONIA_CANKER = "rhizoctonia_canker"  # Black scurf on tubers
    SILVER_SCURF = "silver_scurf"  # Helminthosporium - cosmetic


class PotatoVarietyType(Enum):
    """Potato variety classifications"""
    RUSSET = "russet"  # Russet Burbank - baking, frying, most common USA
    RED = "red"  # Red Pontiac, Red Norland - boiling, salads
    WHITE = "white"  # Kennebec, Katahdin - all-purpose
    YELLOW = "yellow"  # Yukon Gold - buttery, creamy
    FINGERLING = "fingerling"  # Russian Banana - specialty, gourmet
    PURPLE = "purple"  # Purple Majesty - anthocyanin-rich
    EARLY_MATURING = "early_maturing"  # 70-90 days - early market
    LATE_MATURING = "late_maturing"  # 110-140 days - storage


@dataclass
class PotatoLesion:
    """Potato disease lesion characteristics"""
    color_hsv_range: Tuple[Tuple[int, int, int], Tuple[int, int, int]]
    shape: str  # circular, angular, irregular, concentric_rings
    texture: str  # smooth, corky, sunken, raised, fuzzy
    location: str  # leaf, stem, tuber, root, stolon
    size_mm: Tuple[float, float]  # min, max diameter
    progression: str  # static, expanding, coalescing
    margin: str  # defined, feathery, water_soaked, chlorotic_halo
    
    # Late blight specific
    white_sporulation: bool = False  # Sporangia on leaf underside
    concentric_rings: bool = False  # Early blight bull's-eye pattern
    black_stem_rot: bool = False  # Blackleg symptom
    corky_texture: bool = False  # Common scab
    pink_flesh: bool = False  # Pink rot tuber
    
    # Economic impact
    yield_loss_percent: float = 0.0
    marketability_impact: str = "minor"  # minor, moderate, severe, unmarketable


@dataclass
class PotatoTuberDisease:
    """Specific tuber disease parameters"""
    external_symptoms: List[str]  # skin_lesions, black_scurf, silver_sheen
    internal_symptoms: List[str]  # pink_rot, dry_rot, hollow_heart
    storage_loss_rate: float  # Percent loss per month in storage
    seed_transmission: bool  # Can transmit to next generation
    marketability: str  # fresh_market, processing, seed_only, unmarketable
    
    # Critical for seed potato certification
    zero_tolerance: bool = False  # Blackleg, ring rot require zero tolerance
    seed_certification_threshold: float = 0.0  # Max % for certified seed


@dataclass
class EnvironmentalRisk:
    """Environmental factors for potato disease risk"""
    temperature_range: Tuple[float, float]  # Optimal °C for pathogen
    humidity_threshold: float  # Minimum RH% for infection
    leaf_wetness_hours: float  # Hours of wetness needed
    soil_moisture: str  # dry, moist, saturated
    soil_ph_range: Tuple[float, float]  # Optimal pH (scab >5.2)
    wind_dispersal: bool  # Late blight sporangia wind-blown
    
    # Risk levels
    risk_level: str = "low"  # low, moderate, high, EMERGENCY
    infection_period_hours: float = 0.0  # Hours to infection
    sporulation_period_hours: float = 0.0  # Hours to spore production


@dataclass
class TreatmentPlan:
    """Comprehensive potato disease treatment strategy"""
    fungicides: List[Dict[str, str]] = field(default_factory=list)
    bactericides: List[Dict[str, str]] = field(default_factory=list)
    cultural_controls: List[str] = field(default_factory=list)
    biocontrols: List[str] = field(default_factory=list)
    
    # Emergency protocols
    emergency_response: bool = False  # Late blight requires immediate action
    spray_interval_days: int = 7
    resistance_management: str = ""
    
    # Economic analysis
    treatment_cost_per_acre: float = 0.0
    expected_yield_protection: float = 0.0
    roi_ratio: float = 0.0


@dataclass
class DetectionResult:
    """Disease detection result with confidence metrics"""
    disease: PotatoDisease
    confidence: float
    severity: float  # 0-100 scale
    affected_area_percent: float
    lesion_count: int
    lesions: List[PotatoLesion]
    environmental_risk: EnvironmentalRisk
    treatment_plan: TreatmentPlan
    
    # Late blight emergency
    emergency_alert: bool = False
    hours_to_epidemic: Optional[float] = None
    
    # Variety-specific
    variety_susceptibility: str = "unknown"
    resistance_genes: List[str] = field(default_factory=list)
    
    timestamp: datetime = field(default_factory=datetime.now)


class PotatoDiseaseDetector:
    """
    Advanced potato disease detection system
    
    CRITICAL FOCUS:
    - Late blight early warning (pre-epidemic)
    - Seed potato health certification
    - Storage disease prevention
    - Variety-specific resistance
    """
    
    def __init__(self):
        self.disease_database = self._initialize_disease_database()
        self.variety_resistance = self._initialize_variety_resistance()
        self.emergency_threshold = 0.75  # Late blight confidence threshold
        
    def _initialize_disease_database(self) -> Dict[PotatoDisease, Dict]:
        """Comprehensive potato disease parameter database"""
        return {
            PotatoDisease.LATE_BLIGHT: {
                'pathogen': 'Phytophthora infestans',
                'pathogen_type': 'Oomycete (water mold)',
                'historical_significance': 'Irish Potato Famine 1845-1852, 1 million deaths',
                'global_losses': '$6.7 billion annually',
                'symptoms': [
                    'Water-soaked lesions on leaves',
                    'Dark brown to black spreading rapidly',
                    'White sporulation on leaf underside (high humidity)',
                    'Brown tuber rot with granular texture',
                    'Entire plant collapse in 7-10 days'
                ],
                'diagnostic_features': [
                    'White fuzzy growth on leaf underside',
                    'Rapid overnight spread',
                    'Characteristic musty odor',
                    'Green-gray lesion color before necrosis',
                    'Stem lesions dark brown to black'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(10, 25),
                    humidity_threshold=90,
                    leaf_wetness_hours=12,
                    soil_moisture='moist',
                    soil_ph_range=(5.0, 7.0),
                    wind_dispersal=True,
                    risk_level='EMERGENCY',
                    infection_period_hours=4,
                    sporulation_period_hours=12
                ),
                'economic_impact': {
                    'yield_loss': '50-100% if untreated',
                    'fungicide_cost': '$200-400/acre/season',
                    'total_global_loss': '$6.7 billion/year'
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Ridomil Gold', 'active': 'mefenoxam', 'frac': '4'},
                        {'name': 'Previcur Flex', 'active': 'propamocarb', 'frac': '28'},
                        {'name': 'Revus', 'active': 'mandipropamid', 'frac': '40'},
                        {'name': 'Curzate', 'active': 'cymoxanil', 'frac': '27'},
                        {'name': 'Ranman', 'active': 'cyazofamid', 'frac': '21'}
                    ],
                    cultural_controls=[
                        'Destroy volunteer potatoes and cull piles',
                        'Use certified seed only (zero tolerance)',
                        'Remove infected plants immediately',
                        'Increase air circulation',
                        'Avoid overhead irrigation',
                        'Hill soil to protect tubers from spore wash-down'
                    ],
                    emergency_response=True,
                    spray_interval_days=5,  # AGGRESSIVE: 5-7 days
                    resistance_management='Rotate FRAC groups every spray, never use single-site fungicides alone',
                    treatment_cost_per_acre=350.0,
                    expected_yield_protection=90.0,
                    roi_ratio=8.5
                ),
                'resistance_genes': ['R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9', 'R10', 'R11'],
                'notes': 'ZERO COMPLACENCY DISEASE - Monitor daily, respond within hours'
            },
            
            PotatoDisease.EARLY_BLIGHT: {
                'pathogen': 'Alternaria solani',
                'pathogen_type': 'Fungus',
                'global_distribution': 'Worldwide - most common potato disease',
                'symptoms': [
                    'Dark brown lesions with concentric rings (bull\'s-eye)',
                    'Lesions start on lower older leaves',
                    'Yellowing around lesions (chlorotic halo)',
                    'Defoliation from bottom up',
                    'Stem lesions dark sunken'
                ],
                'diagnostic_features': [
                    'BULL\'S-EYE PATTERN - concentric rings diagnostic',
                    'Starts on mature leaves (not young like late blight)',
                    'Slow progression (not rapid like late blight)',
                    'Dry lesions (not water-soaked)'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(24, 29),
                    humidity_threshold=80,
                    leaf_wetness_hours=8,
                    soil_moisture='moist',
                    soil_ph_range=(5.5, 7.0),
                    wind_dispersal=True,
                    risk_level='moderate',
                    infection_period_hours=12,
                    sporulation_period_hours=24
                ),
                'economic_impact': {
                    'yield_loss': '20-30% defoliation reduces yield 25-50%',
                    'tuber_size_reduction': '15-30%',
                    'treatment_cost': '$100-200/acre/season'
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Quadris', 'active': 'azoxystrobin', 'frac': '11'},
                        {'name': 'Bravo', 'active': 'chlorothalonil', 'frac': 'M5'},
                        {'name': 'Inspire Super', 'active': 'difenoconazole', 'frac': '3'},
                        {'name': 'Scala', 'active': 'pyrimethanil', 'frac': '9'}
                    ],
                    cultural_controls=[
                        'Remove infected lower leaves',
                        'Improve air circulation',
                        'Avoid water stress (stressed plants more susceptible)',
                        'Balanced nitrogen (excess N increases susceptibility)',
                        '2-year crop rotation minimum'
                    ],
                    spray_interval_days=7,
                    resistance_management='Rotate FRAC groups, include multi-site fungicide (chlorothalonil)',
                    treatment_cost_per_acre=150.0,
                    expected_yield_protection=70.0,
                    roi_ratio=5.0
                )
            },
            
            PotatoDisease.BLACKLEG: {
                'pathogen': 'Pectobacterium spp. (P. atrosepticum, P. carotovorum)',
                'pathogen_type': 'Bacteria',
                'transmission': 'SEED-BORNE - latent infection in seed tubers',
                'symptoms': [
                    'Black slimy rot of stem base',
                    'Starts at soil line and moves up',
                    'Yellowing and wilting of plant',
                    'Vascular tissue black and slimy',
                    'Foul odor from rotting tissue',
                    'Plant death within 2-3 weeks'
                ],
                'diagnostic_features': [
                    'BLACK STEM ROT from ground up',
                    'Slimy bacterial ooze',
                    'Foul smell distinctive',
                    'Tuber rot brown to black cream-colored',
                    'Seed potato source can be traced'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(20, 30),
                    humidity_threshold=85,
                    leaf_wetness_hours=0,  # Soil moisture critical
                    soil_moisture='saturated',  # Waterlogged soil favors
                    soil_ph_range=(6.0, 7.5),
                    wind_dispersal=False,
                    risk_level='high',
                    infection_period_hours=24,
                    sporulation_period_hours=0  # Bacterial
                ),
                'economic_impact': {
                    'seed_potato_losses': 'ZERO TOLERANCE for certification',
                    'yield_loss': '5-30% depending on seed infection level',
                    'market_value': 'Unmarketable - complete loss'
                },
                'treatment': TreatmentPlan(
                    bactericides=[
                        {'name': 'Fixed copper', 'active': 'copper hydroxide', 'note': 'Preventive only'},
                        {'name': 'Streptomycin', 'active': 'streptomycin sulfate', 'note': 'Resistance common'}
                    ],
                    cultural_controls=[
                        'USE CERTIFIED SEED ONLY - most critical control',
                        'Inspect seed tubers carefully before planting',
                        'Avoid planting in waterlogged soil',
                        'Improve drainage',
                        'Discard cull piles away from field',
                        'Sanitize cutting equipment',
                        'Avoid cutting seed in wet conditions',
                        'Wound healing period 3-5 days before planting'
                    ],
                    emergency_response=False,
                    spray_interval_days=0,  # No effective chemical control
                    resistance_management='Prevention only - no curative treatment',
                    treatment_cost_per_acre=0.0,
                    expected_yield_protection=0.0,
                    roi_ratio=0.0
                ),
                'tuber_disease': PotatoTuberDisease(
                    external_symptoms=['soft_rot', 'black_discoloration'],
                    internal_symptoms=['cream_colored_rot', 'slimy_texture'],
                    storage_loss_rate=100.0,  # Total loss
                    seed_transmission=True,
                    marketability='unmarketable',
                    zero_tolerance=True,
                    seed_certification_threshold=0.0
                ),
                'notes': 'PREVENTION ONLY - no cure once established. Certified seed is MANDATORY.'
            },
            
            PotatoDisease.COMMON_SCAB: {
                'pathogen': 'Streptomyces scabies (and other Streptomyces spp.)',
                'pathogen_type': 'Bacteria (Actinomycete)',
                'soil_borne': True,
                'symptoms': [
                    'Corky lesions on tuber surface',
                    'Brown rough scab-like texture',
                    'Shallow to deep pitted lesions',
                    'Does not affect internal flesh',
                    'Cosmetic damage reduces market value'
                ],
                'diagnostic_features': [
                    'CORKY TEXTURE on tuber skin',
                    'No leaf symptoms',
                    'pH >5.2 increases severity',
                    'Dry soil during tuber formation favors disease',
                    'Can be superficial or deep pitted'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(20, 22),
                    humidity_threshold=0,  # Soil moisture critical
                    leaf_wetness_hours=0,
                    soil_moisture='dry',  # DRY soil during tuber set favors scab
                    soil_ph_range=(5.2, 8.0),  # pH >5.2 FAVORS disease
                    wind_dispersal=False,
                    risk_level='moderate',
                    infection_period_hours=72,
                    sporulation_period_hours=0
                ),
                'economic_impact': {
                    'yield_loss': '0-5% (cosmetic mainly)',
                    'market_value_reduction': '30-60% for fresh market',
                    'processing_impact': 'Minimal for chip/fry processing'
                },
                'treatment': TreatmentPlan(
                    cultural_controls=[
                        'Lower soil pH to 5.0-5.2 (sulfur amendment)',
                        'Maintain adequate soil moisture during tuber initiation',
                        'Use resistant varieties',
                        'Avoid fresh manure (increases pH)',
                        '3-4 year crop rotation',
                        'Green manure crops (mustard, rapeseed) can reduce',
                        'Avoid liming before potatoes'
                    ],
                    biocontrols=[
                        'Biological inoculants (limited efficacy)'
                    ],
                    spray_interval_days=0,
                    resistance_management='Variety selection + pH management primary',
                    treatment_cost_per_acre=50.0,
                    expected_yield_protection=40.0,
                    roi_ratio=2.5
                ),
                'tuber_disease': PotatoTuberDisease(
                    external_symptoms=['corky_lesions', 'rough_texture', 'pitting'],
                    internal_symptoms=[],  # No internal symptoms
                    storage_loss_rate=0.0,
                    seed_transmission=False,
                    marketability='fresh_market_reduced',
                    zero_tolerance=False,
                    seed_certification_threshold=5.0
                ),
                'notes': 'COSMETIC disease - pH management is KEY control'
            },
            
            PotatoDisease.PINK_ROT: {
                'pathogen': 'Phytophthora erythroseptica',
                'pathogen_type': 'Oomycete',
                'symptoms': [
                    'Tuber rot starts at eyes or wounds',
                    'Cream to light pink discoloration',
                    'PINK COLOR develops when cut tuber exposed to air (10-30 min)',
                    'Rubbery texture',
                    'Clear boundary between healthy and diseased tissue',
                    'Dark brown final stage'
                ],
                'diagnostic_features': [
                    'PINK DISCOLORATION when cut tuber exposed to air (diagnostic)',
                    'Starts at tuber eyes or wounds',
                    'Wet soil conditions',
                    'Storage rot threat'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(25, 30),
                    humidity_threshold=0,
                    leaf_wetness_hours=0,
                    soil_moisture='saturated',  # Waterlogged soil critical
                    soil_ph_range=(5.5, 7.0),
                    wind_dispersal=False,
                    risk_level='high',
                    infection_period_hours=48,
                    sporulation_period_hours=0
                ),
                'economic_impact': {
                    'harvest_loss': '10-30% in wet years',
                    'storage_loss': '5-20% can develop in storage',
                    'market_value': 'Unmarketable'
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Ridomil Gold', 'active': 'mefenoxam', 'frac': '4'},
                        {'name': 'Presidio', 'active': 'fluopicolide', 'frac': '43'}
                    ],
                    cultural_controls=[
                        'Improve field drainage',
                        'Avoid harvesting when soil is wet',
                        'Harvest at proper tuber maturity',
                        'Avoid wounding tubers during harvest',
                        'Proper storage ventilation',
                        'Storage temperature 45-50°F (7-10°C)',
                        'Crop rotation 3-4 years'
                    ],
                    spray_interval_days=14,
                    treatment_cost_per_acre=120.0,
                    expected_yield_protection=60.0,
                    roi_ratio=4.0
                ),
                'tuber_disease': PotatoTuberDisease(
                    external_symptoms=['soft_rot', 'rubbery_texture'],
                    internal_symptoms=['pink_flesh', 'cream_discoloration'],
                    storage_loss_rate=15.0,
                    seed_transmission=True,
                    marketability='unmarketable',
                    zero_tolerance=False,
                    seed_certification_threshold=2.0
                )
            },
            
            PotatoDisease.VERTICILLIUM_WILT: {
                'pathogen': 'Verticillium dahliae',
                'pathogen_type': 'Fungus (soil-borne)',
                'symptoms': [
                    'Yellowing of lower leaves',
                    'Marginal necrosis (leaf edges brown)',
                    'Premature senescence',
                    'Vascular discoloration (brown streaks in stem)',
                    'Wilting on hot days',
                    'Reduced tuber size and number'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(21, 27),
                    humidity_threshold=0,
                    leaf_wetness_hours=0,
                    soil_moisture='moist',
                    soil_ph_range=(5.5, 7.5),
                    wind_dispersal=False,
                    risk_level='moderate'
                ),
                'treatment': TreatmentPlan(
                    cultural_controls=[
                        'Use resistant varieties',
                        'Long crop rotation (5+ years)',
                        'Avoid fields with history of verticillium',
                        'Control weeds (alternate hosts)',
                        'Maintain plant vigor',
                        'Avoid water stress'
                    ],
                    treatment_cost_per_acre=0.0,
                    expected_yield_protection=30.0,
                    roi_ratio=0.0
                )
            },
            
            PotatoDisease.POTATO_VIRUS_Y: {
                'pathogen': 'Potato Virus Y (PVY)',
                'pathogen_type': 'Virus',
                'transmission': 'Aphid-transmitted (non-persistent)',
                'symptoms': [
                    'Mosaic pattern on leaves',
                    'Leaf crinkling and distortion',
                    'Necrotic lesions on leaves/stems',
                    'Stunted growth',
                    'Tuber necrotic ringspot'
                ],
                'economic_impact': {
                    'yield_loss': '10-80% depending on strain and infection timing',
                    'seed_potato_degrade': 'Seed lots can be decertified'
                },
                'treatment': TreatmentPlan(
                    cultural_controls=[
                        'Use certified virus-free seed',
                        'Aphid control critical',
                        'Rogue infected plants',
                        'Control volunteer potatoes',
                        'Isolation from other nightshades'
                    ]
                )
            }
        }
    
    def _initialize_variety_resistance(self) -> Dict[PotatoVarietyType, Dict]:
        """Variety-specific disease resistance profiles"""
        return {
            PotatoVarietyType.RUSSET: {
                'varieties': ['Russet Burbank', 'Ranger Russet', 'Umatilla Russet'],
                'late_blight_resistance': 'susceptible',
                'early_blight_resistance': 'moderate',
                'common_scab_resistance': 'susceptible',
                'virus_resistance': 'moderate',
                'notes': 'Most common USA variety, requires intensive late blight protection'
            },
            PotatoVarietyType.RED: {
                'varieties': ['Red Norland', 'Red Pontiac', 'Dark Red Norland'],
                'late_blight_resistance': 'moderate',
                'early_blight_resistance': 'moderate',
                'common_scab_resistance': 'moderate-resistant',
                'virus_resistance': 'moderate',
                'notes': 'Better scab resistance than russets'
            },
            PotatoVarietyType.YELLOW: {
                'varieties': ['Yukon Gold', 'Yellow Finn'],
                'late_blight_resistance': 'susceptible',
                'early_blight_resistance': 'moderate',
                'common_scab_resistance': 'susceptible',
                'virus_resistance': 'moderate',
                'notes': 'Premium market variety'
            }
        }
    
    def detect_late_blight(self, image: np.ndarray, 
                          environmental_data: Dict) -> Optional[DetectionResult]:
        """
        EMERGENCY DETECTION: Late Blight (Phytophthora infestans)
        
        CRITICAL: This disease requires immediate response
        Detection triggers emergency protocols
        """
        # Preprocessing
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        
        # Late blight lesion detection
        # Water-soaked appearance: dark green-gray to brown-black
        # HSV: Hue 80-120 (green-brown), Saturation 40-100, Value 20-80
        lower_lesion = np.array([80, 40, 20])
        upper_lesion = np.array([120, 100, 80])
        lesion_mask = cv2.inRange(hsv, lower_lesion, upper_lesion)
        
        # White sporulation detection (leaf underside)
        # Critical diagnostic: white fuzzy growth
        lower_spores = np.array([0, 0, 180])
        upper_spores = np.array([180, 30, 255])
        spore_mask = cv2.inRange(hsv, lower_spores, upper_spores)
        
        # Morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        lesion_mask = cv2.morphologyEx(lesion_mask, cv2.MORPH_CLOSE, kernel)
        lesion_mask = cv2.morphologyEx(lesion_mask, cv2.MORPH_OPEN, kernel)
        
        # Find lesions
        contours, _ = cv2.findContours(lesion_mask, cv2.RETR_EXTERNAL, 
                                       cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) == 0:
            return None
        
        # Analyze lesions
        lesions = []
        total_area = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 100:  # Minimum lesion size
                continue
            
            # Bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            
            # Check for white sporulation nearby
            roi_spore = spore_mask[y:y+h, x:x+w]
            sporulation_detected = np.sum(roi_spore > 0) > (w * h * 0.05)
            
            lesion = PotatoLesion(
                color_hsv_range=((80, 40, 20), (120, 100, 80)),
                shape='irregular',
                texture='water_soaked',
                location='leaf',
                size_mm=(w * 0.1, h * 0.1),  # Approximate mm
                progression='expanding',
                margin='feathery',
                white_sporulation=sporulation_detected,
                yield_loss_percent=75.0,
                marketability_impact='unmarketable'
            )
            lesions.append(lesion)
            total_area += area
        
        # Calculate confidence and severity
        affected_area = (total_area / (image.shape[0] * image.shape[1])) * 100
        
        # Sporulation is CRITICAL diagnostic
        sporulation_found = any(l.white_sporulation for l in lesions)
        base_confidence = min(0.6 + (affected_area / 50) * 0.3, 0.9)
        if sporulation_found:
            confidence = min(base_confidence + 0.1, 0.95)
        else:
            confidence = base_confidence
        
        # Environmental risk assessment
        temp = environmental_data.get('temperature', 20)
        humidity = environmental_data.get('humidity', 80)
        leaf_wetness = environmental_data.get('leaf_wetness_hours', 0)
        
        risk_level = 'EMERGENCY' if (10 <= temp <= 25 and 
                                     humidity >= 90 and 
                                     leaf_wetness >= 12) else 'high'
        
        env_risk = EnvironmentalRisk(
            temperature_range=(10, 25),
            humidity_threshold=90,
            leaf_wetness_hours=12,
            soil_moisture='moist',
            soil_ph_range=(5.0, 7.0),
            wind_dispersal=True,
            risk_level=risk_level,
            infection_period_hours=4,
            sporulation_period_hours=12
        )
        
        # Emergency alert calculation
        emergency = False
        hours_to_epidemic = None
        
        if confidence > self.emergency_threshold:
            emergency = True
            # Estimate time to epidemic based on conditions
            if risk_level == 'EMERGENCY':
                hours_to_epidemic = 48  # Can spread field-wide in 48 hours
            else:
                hours_to_epidemic = 120  # 5 days under moderate conditions
        
        disease_info = self.disease_database[PotatoDisease.LATE_BLIGHT]
        
        result = DetectionResult(
            disease=PotatoDisease.LATE_BLIGHT,
            confidence=confidence,
            severity=min(affected_area * 2, 100),
            affected_area_percent=affected_area,
            lesion_count=len(lesions),
            lesions=lesions,
            environmental_risk=env_risk,
            treatment_plan=disease_info['treatment'],
            emergency_alert=emergency,
            hours_to_epidemic=hours_to_epidemic,
            variety_susceptibility='high',
            resistance_genes=[]
        )
        
        return result
    
    def detect_early_blight(self, image: np.ndarray) -> Optional[DetectionResult]:
        """
        Detect Early Blight (Alternaria solani)
        
        DIAGNOSTIC: Concentric ring pattern (bull's-eye)
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Dark brown lesions with concentric rings
        lower_lesion = np.array([10, 30, 30])
        upper_lesion = np.array([30, 150, 120])
        lesion_mask = cv2.inRange(hsv, lower_lesion, upper_lesion)
        
        # Morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        lesion_mask = cv2.morphologyEx(lesion_mask, cv2.MORPH_CLOSE, kernel)
        
        # Find lesions
        contours, _ = cv2.findContours(lesion_mask, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) == 0:
            return None
        
        lesions = []
        total_area = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 200:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            
            # Check for concentric rings (bull's-eye pattern)
            roi = gray[y:y+h, x:x+w]
            
            # Detect concentric circles using edge detection
            edges = cv2.Canny(roi, 50, 150)
            circles = cv2.HoughCircles(edges, cv2.HOUGH_GRADIENT, 1, 20,
                                      param1=50, param2=30, minRadius=5, maxRadius=50)
            
            has_concentric_rings = circles is not None and len(circles[0]) >= 2
            
            lesion = PotatoLesion(
                color_hsv_range=((10, 30, 30), (30, 150, 120)),
                shape='circular',
                texture='smooth',
                location='leaf',
                size_mm=(w * 0.1, h * 0.1),
                progression='expanding',
                margin='chlorotic_halo',
                concentric_rings=has_concentric_rings,
                yield_loss_percent=30.0,
                marketability_impact='moderate'
            )
            lesions.append(lesion)
            total_area += area
        
        affected_area = (total_area / (image.shape[0] * image.shape[1])) * 100
        
        # Bull's-eye pattern increases confidence significantly
        rings_found = any(l.concentric_rings for l in lesions)
        confidence = min(0.5 + (affected_area / 40) * 0.3, 0.85)
        if rings_found:
            confidence = min(confidence + 0.15, 0.95)
        
        disease_info = self.disease_database[PotatoDisease.EARLY_BLIGHT]
        
        result = DetectionResult(
            disease=PotatoDisease.EARLY_BLIGHT,
            confidence=confidence,
            severity=min(affected_area * 1.5, 100),
            affected_area_percent=affected_area,
            lesion_count=len(lesions),
            lesions=lesions,
            environmental_risk=disease_info['environmental'],
            treatment_plan=disease_info['treatment']
        )
        
        return result
    
    def detect_blackleg(self, image: np.ndarray) -> Optional[DetectionResult]:
        """
        Detect Blackleg (Pectobacterium spp.)
        
        CRITICAL: Black stem rot from soil line upward
        Seed-borne bacterial disease
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Black stem lesions
        lower_black = np.array([0, 0, 0])
        upper_black = np.array([180, 255, 50])
        black_mask = cv2.inRange(hsv, lower_black, upper_black)
        
        # Focus on vertical stem structures
        kernel_vertical = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 15))
        stem_mask = cv2.morphologyEx(black_mask, cv2.MORPH_CLOSE, kernel_vertical)
        
        contours, _ = cv2.findContours(stem_mask, cv2.RETR_EXTERNAL,
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
            
            # Vertical elongation (stem characteristic)
            aspect_ratio = h / w if w > 0 else 0
            
            if aspect_ratio > 2.0:  # Vertical stem lesion
                lesion = PotatoLesion(
                    color_hsv_range=((0, 0, 0), (180, 255, 50)),
                    shape='irregular',
                    texture='slimy',
                    location='stem',
                    size_mm=(w * 0.1, h * 0.1),
                    progression='expanding',
                    margin='water_soaked',
                    black_stem_rot=True,
                    yield_loss_percent=100.0,
                    marketability_impact='unmarketable'
                )
                lesions.append(lesion)
                total_area += area
        
        if len(lesions) == 0:
            return None
        
        affected_area = (total_area / (image.shape[0] * image.shape[1])) * 100
        confidence = min(0.6 + (len(lesions) / 5) * 0.2, 0.90)
        
        disease_info = self.disease_database[PotatoDisease.BLACKLEG]
        
        result = DetectionResult(
            disease=PotatoDisease.BLACKLEG,
            confidence=confidence,
            severity=100.0,  # Always severe
            affected_area_percent=affected_area,
            lesion_count=len(lesions),
            lesions=lesions,
            environmental_risk=disease_info['environmental'],
            treatment_plan=disease_info['treatment'],
            emergency_alert=True,  # Zero tolerance disease
            variety_susceptibility='high'
        )
        
        return result
    
    def detect_common_scab(self, tuber_image: np.ndarray) -> Optional[DetectionResult]:
        """
        Detect Common Scab (Streptomyces scabies)
        
        DIAGNOSTIC: Corky lesions on tuber surface
        Cosmetic disease affecting market value
        """
        hsv = cv2.cvtColor(tuber_image, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(tuber_image, cv2.COLOR_BGR2GRAY)
        
        # Brown corky lesions
        lower_scab = np.array([10, 20, 60])
        upper_scab = np.array([30, 180, 150])
        scab_mask = cv2.inRange(hsv, lower_scab, upper_scab)
        
        # Texture analysis for corky appearance
        # Use Laplacian for texture roughness
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        texture_score = np.var(laplacian)
        
        contours, _ = cv2.findContours(scab_mask, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) == 0:
            return None
        
        lesions = []
        total_area = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 150:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            
            lesion = PotatoLesion(
                color_hsv_range=((10, 20, 60), (30, 180, 150)),
                shape='irregular',
                texture='corky',
                location='tuber',
                size_mm=(w * 0.1, h * 0.1),
                progression='static',
                margin='defined',
                corky_texture=True,
                yield_loss_percent=0.0,
                marketability_impact='moderate'
            )
            lesions.append(lesion)
            total_area += area
        
        affected_area = (total_area / (tuber_image.shape[0] * tuber_image.shape[1])) * 100
        
        # High texture score indicates corky surface
        confidence = min(0.5 + (affected_area / 30) * 0.2, 0.80)
        if texture_score > 500:  # Rough corky texture
            confidence = min(confidence + 0.15, 0.90)
        
        disease_info = self.disease_database[PotatoDisease.COMMON_SCAB]
        
        result = DetectionResult(
            disease=PotatoDisease.COMMON_SCAB,
            confidence=confidence,
            severity=min(affected_area * 2, 100),
            affected_area_percent=affected_area,
            lesion_count=len(lesions),
            lesions=lesions,
            environmental_risk=disease_info['environmental'],
            treatment_plan=disease_info['treatment']
        )
        
        return result
    
    def analyze_potato_health(self, image: np.ndarray, 
                             environmental_data: Dict,
                             variety_type: PotatoVarietyType = PotatoVarietyType.RUSSET,
                             image_type: str = 'leaf') -> List[DetectionResult]:
        """
        Comprehensive potato disease analysis
        
        Args:
            image: Input image (RGB)
            environmental_data: Temperature, humidity, etc.
            variety_type: Potato variety for resistance lookup
            image_type: 'leaf', 'stem', or 'tuber'
        
        Returns:
            List of detected diseases sorted by confidence
        """
        results = []
        
        if image_type == 'leaf' or image_type == 'stem':
            # Check for emergency late blight
            late_blight = self.detect_late_blight(image, environmental_data)
            if late_blight and late_blight.confidence > 0.6:
                results.append(late_blight)
            
            # Check early blight
            early_blight = self.detect_early_blight(image)
            if early_blight and early_blight.confidence > 0.5:
                results.append(early_blight)
            
            # Check blackleg
            blackleg = self.detect_blackleg(image)
            if blackleg and blackleg.confidence > 0.6:
                results.append(blackleg)
        
        elif image_type == 'tuber':
            # Check common scab
            scab = self.detect_common_scab(image)
            if scab and scab.confidence > 0.5:
                results.append(scab)
        
        # Sort by confidence
        results.sort(key=lambda x: x.confidence, reverse=True)
        
        # Add variety-specific information
        variety_info = self.variety_resistance.get(variety_type, {})
        for result in results:
            result.variety_susceptibility = variety_info.get(
                f'{result.disease.value}_resistance', 'unknown'
            )
        
        return results


def main():
    """Example usage of potato disease detector"""
    detector = PotatoDiseaseDetector()
    
    print("=== AgroPulse Potato Disease Detection System ===")
    print(f"Monitoring {len(detector.disease_database)} major potato diseases")
    print("\nCRITICAL PATHOGENS:")
    print("1. Late Blight (Phytophthora infestans) - EMERGENCY RESPONSE")
    print("   - Irish Potato Famine pathogen")
    print("   - Can destroy crop in 7-10 days")
    print("   - $6.7 billion annual global losses")
    print("\n2. Blackleg (Pectobacterium) - ZERO TOLERANCE")
    print("   - Seed-borne bacterial disease")
    print("   - Seed certification requirement")
    print("\n3. Early Blight (Alternaria) - MOST COMMON")
    print("   - Bull's-eye lesion pattern")
    print("   - Worldwide distribution")
    print("\nSYSTEM STATUS: Ready for 24/7 monitoring")
    print("Late Blight Emergency Threshold: 75% confidence")


if __name__ == "__main__":
    main()
