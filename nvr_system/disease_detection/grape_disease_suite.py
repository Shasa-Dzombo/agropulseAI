"""
Grape Disease Detection Suite
Comprehensive detection system for grapevine diseases

CRITICAL DISEASES:

1. Downy Mildew (Plasmopara viticola) - HISTORIC EUROPEAN VITICULTURE COLLAPSE
   - Destroyed European wine industry 1870s-1880s
   - "Oil spot" lesions diagnostic
   - White sporulation on leaf underside
   - Fruit infection = total crop loss
   - $3 billion annual losses globally

2. Powdery Mildew (Erysiphe necator) - #1 GRAPE DISEASE WORLDWIDE
   - White powdery growth on all green tissue
   - Berry cracking and splitting
   - Wine quality severely degraded
   - Fungicide resistance common
   - $1 billion annual losses

3. Botrytis Bunch Rot (Botrytis cinerea) - DUAL NATURE DISEASE
   - DESTRUCTIVE: Pre-harvest rot (20-30% loss)
   - BENEFICIAL: "Noble rot" for dessert wines (Sauternes)
   - Gray mold on clusters
   - Sour rot complex

4. Black Rot (Guignardia bidwellii) - NORTH AMERICAN NATIVE
   - Mummified berries diagnostic
   - 5-80% crop loss
   - Hot humid weather disease

5. Pierce's Disease (Xylella fastidiosa) - BACTERIAL LETHAL
   - Xylem-clogging bacteria
   - Sharpshooter leafhopper vector
   - NO CURE - infected vines die
   - California wine industry threat

DETECTION CHALLENGE:
- Downy mildew requires pre-infection prediction (6-8 hour window)
- Powdery mildew fungicide resistance management critical
- Botrytis decision: beneficial vs destructive
- Pierce's disease early detection saves vineyard

Author: AgroPulse AI Team
Version: 1.0.0
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class GrapeDisease(Enum):
    """Comprehensive grape disease classification"""
    DOWNY_MILDEW = "downy_mildew"  # Plasmopara viticola - HISTORIC
    POWDERY_MILDEW = "powdery_mildew"  # Erysiphe necator - #1 worldwide
    BOTRYTIS_BUNCH_ROT = "botrytis_bunch_rot"  # Botrytis cinerea
    BLACK_ROT = "black_rot"  # Guignardia bidwellii - mummies
    PIERCES_DISEASE = "pierces_disease"  # Xylella fastidiosa - LETHAL
    ANTHRACNOSE = "anthracnose"  # Elsinoe ampelina - bird's eye
    PHOMOPSIS_CANE = "phomopsis_cane"  # Phomopsis viticola
    EUTYPA_DIEBACK = "eutypa_dieback"  # Eutypa lata - dead arm
    ESCA = "esca"  # Complex - Tiger stripe leaves
    CROWN_GALL = "crown_gall"  # Agrobacterium - tumors
    GRAPEVINE_LEAFROLL_VIRUS = "grapevine_leafroll_virus"  # GLRaV
    GRAPEVINE_FANLEAF_VIRUS = "grapevine_fanleaf_virus"  # GFLV - nematode


class GrapeVarietyType(Enum):
    """Grape variety classifications"""
    WINE_RED = "wine_red"  # Cabernet, Merlot, Pinot Noir
    WINE_WHITE = "wine_white"  # Chardonnay, Sauvignon Blanc, Riesling
    TABLE_SEEDED = "table_seeded"  # Cardinal, Flame Seedless
    TABLE_SEEDLESS = "table_seedless"  # Thompson Seedless, Crimson
    RAISIN = "raisin"  # Thompson, Black Corinth
    JUICE = "juice"  # Concord, Niagara
    ROOTSTOCK = "rootstock"  # Phylloxera-resistant


@dataclass
class GrapeLesion:
    """Grape disease lesion characteristics"""
    color_hsv_range: Tuple[Tuple[int, int, int], Tuple[int, int, int]]
    shape: str  # circular, angular, irregular
    texture: str  # powdery, oily, corky, necrotic
    location: str  # leaf, berry, cane, trunk
    size_mm: Tuple[float, float]
    progression: str  # expanding, static, coalescing
    margin: str  # defined, diffuse, chlorotic_halo
    
    # Diagnostic features
    oil_spot_appearance: bool = False  # Downy mildew
    white_powdery_growth: bool = False  # Powdery mildew
    gray_mold: bool = False  # Botrytis
    mummified_berry: bool = False  # Black rot
    bacterial_ooze: bool = False  # Pierce's disease
    
    # Economic impact
    yield_loss_percent: float = 0.0
    wine_quality_impact: str = "none"  # none, minor, moderate, severe, unmarketable
    table_grape_marketability: str = "grade_A"  # grade_A, grade_B, processing, unmarketable


@dataclass
class GrapeBerryDisease:
    """Berry-specific disease parameters"""
    berry_symptoms: List[str]
    cluster_symptoms: List[str]
    wine_quality_degradation: str  # none, off_flavors, unmarketable
    table_grape_appearance: str  # perfect, blemished, unmarketable
    
    # Critical timing
    veraison_susceptibility: bool = False  # Color change critical period
    pre_harvest_risk: bool = False
    post_harvest_storage: bool = False


@dataclass
class EnvironmentalRisk:
    """Environmental factors for grape disease risk"""
    temperature_range: Tuple[float, float]
    humidity_threshold: float
    leaf_wetness_hours: float
    rainfall_trigger_mm: float  # Downy mildew infection event
    wind_dispersal: bool
    
    risk_level: str = "low"
    infection_period_hours: float = 0.0
    incubation_period_days: float = 0.0


@dataclass
class TreatmentPlan:
    """Grape disease treatment strategy"""
    fungicides: List[Dict[str, str]] = field(default_factory=list)
    bactericides: List[Dict[str, str]] = field(default_factory=list)
    cultural_controls: List[str] = field(default_factory=list)
    
    spray_interval_days: int = 7
    resistance_management: str = ""
    
    # Wine quality considerations
    pre_harvest_interval: int = 0  # Days before harvest
    wine_taint_risk: str = "none"  # none, low, moderate, high
    
    treatment_cost_per_acre: float = 0.0
    expected_yield_protection: float = 0.0
    roi_ratio: float = 0.0


@dataclass
class DetectionResult:
    """Disease detection result"""
    disease: GrapeDisease
    confidence: float
    severity: float
    affected_area_percent: float
    lesion_count: int
    lesions: List[GrapeLesion]
    environmental_risk: EnvironmentalRisk
    treatment_plan: TreatmentPlan
    
    # Vineyard-specific
    growth_stage: str = "unknown"  # bloom, berry_set, veraison, harvest
    variety_susceptibility: str = "unknown"
    
    # Wine quality impact
    harvest_recommendation: str = ""
    
    timestamp: datetime = field(default_factory=datetime.now)


class GrapeDiseaseDetector:
    """
    Advanced grape disease detection system
    
    CRITICAL FOCUS:
    - Downy mildew infection event prediction
    - Powdery mildew resistance management
    - Botrytis timing (beneficial vs destructive)
    - Pierce's disease early warning
    """
    
    def __init__(self):
        self.disease_database = self._initialize_disease_database()
        self.variety_resistance = self._initialize_variety_resistance()
        
    def _initialize_disease_database(self) -> Dict[GrapeDisease, Dict]:
        """Comprehensive grape disease parameter database"""
        return {
            GrapeDisease.DOWNY_MILDEW: {
                'pathogen': 'Plasmopara viticola',
                'pathogen_type': 'Oomycete',
                'historical_significance': 'Destroyed European wine industry 1870s-1880s',
                'origin': 'North America → Europe via infected vines',
                'global_losses': '$3 billion annually',
                'symptoms': [
                    '"OIL SPOT" lesions on upper leaf surface (diagnostic)',
                    'Yellow to brown irregular lesions',
                    'WHITE DOWNY SPORULATION on leaf underside',
                    'Leaf distortion and cupping',
                    'Berry infection: Gray-brown rot (complete loss)',
                    'Young shoots can be systemically infected'
                ],
                'diagnostic_features': [
                    'OIL SPOT appearance on top leaf surface',
                    'White downy growth underneath',
                    'Cool wet weather (13-18°C optimal)',
                    'Infection requires FREE WATER on leaves',
                    'Berry susceptibility until pea-size'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(13, 25),
                    humidity_threshold=95,
                    leaf_wetness_hours=6,
                    rainfall_trigger_mm=10,  # 10mm rain = infection event
                    wind_dispersal=True,
                    risk_level='high',
                    infection_period_hours=6,
                    incubation_period_days=7
                ),
                'economic_impact': {
                    'yield_loss': '50-100% if untreated',
                    'berry_infection': 'Total cluster loss',
                    'global_cost': '$3 billion/year',
                    'fungicide_cost': '$300-500/acre/season'
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Ridomil Gold', 'active': 'mefenoxam', 'frac': '4'},
                        {'name': 'Forum', 'active': 'dimethomorph', 'frac': '40'},
                        {'name': 'Revus', 'active': 'mandipropamid', 'frac': '40'},
                        {'name': 'Zampro', 'active': 'ametoctradin+dimethomorph', 'frac': '45+40'},
                        {'name': 'Copper', 'active': 'copper hydroxide', 'frac': 'M1'}
                    ],
                    cultural_controls=[
                        'Canopy management (reduce humidity)',
                        'Leaf removal in fruit zone',
                        'Avoid overhead irrigation',
                        'Remove infected leaves/clusters',
                        'Destroy crop debris'
                    ],
                    spray_interval_days=7,  # 7-10 days
                    resistance_management='Rotate FRAC groups, never single-site alone',
                    pre_harvest_interval=14,
                    treatment_cost_per_acre=400.0,
                    expected_yield_protection=85.0,
                    roi_ratio=7.0
                ),
                'infection_model': {
                    'primary_infection': 'Oospores in fallen leaves overwinter',
                    'secondary_cycles': '7-10 days, multiple cycles per season',
                    'critical_period': 'Bloom through berry pea-size'
                }
            },
            
            GrapeDisease.POWDERY_MILDEW: {
                'pathogen': 'Erysiphe necator (formerly Uncinula necator)',
                'pathogen_type': 'Fungus',
                'global_importance': '#1 GRAPE DISEASE WORLDWIDE',
                'symptoms': [
                    'WHITE POWDERY GROWTH on all green tissue',
                    'Leaves: White patches, curling, distortion',
                    'Berries: White powder, berry cracking',
                    'Cracked berries = entry for Botrytis',
                    'Wine: Off-flavors, reduced quality',
                    'Table grapes: Unmarketable appearance'
                ],
                'diagnostic_features': [
                    'WHITE POWDERY coating (diagnostic)',
                    'Warm dry weather (vs downy mildew)',
                    'Does NOT require free water',
                    'Black cleistothecia (sexual stage) on infected tissue',
                    'Berry susceptibility entire season'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(20, 27),
                    humidity_threshold=40,  # LOW humidity (vs downy)
                    leaf_wetness_hours=0,  # No free water needed
                    rainfall_trigger_mm=0,
                    wind_dispersal=True,
                    risk_level='high',
                    infection_period_hours=4,
                    incubation_period_days=5
                ),
                'economic_impact': {
                    'yield_loss': '10-40% typical',
                    'wine_quality': 'Severe degradation, off-flavors',
                    'table_grapes': 'Unmarketable if visible',
                    'global_cost': '$1 billion/year'
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Rally', 'active': 'myclobutanil', 'frac': '3'},
                        {'name': 'Vivando', 'active': 'metrafenone', 'frac': 'U8'},
                        {'name': 'Torino', 'active': 'cyflufenamid', 'frac': 'U6'},
                        {'name': 'Sulfur', 'active': 'sulfur', 'frac': 'M2'},
                        {'name': 'Luna Experience', 'active': 'fluopyram+tebuconazole', 'frac': '7+3'}
                    ],
                    cultural_controls=[
                        'Sulfur dust (oldest treatment, still effective)',
                        'Canopy management (sun exposure)',
                        'Remove infected tissue',
                        'Avoid excessive nitrogen'
                    ],
                    spray_interval_days=10,
                    resistance_management='CRITICAL: DMI (FRAC 3) resistance widespread, rotate groups',
                    pre_harvest_interval=7,
                    treatment_cost_per_acre=350.0,
                    expected_yield_protection=80.0,
                    roi_ratio=6.5
                ),
                'resistance_crisis': {
                    'frac_3_resistance': 'DMI (triazole) resistance common worldwide',
                    'frac_11_resistance': 'QoI (strobilurin) resistance documented',
                    'management': 'Multi-site fungicides (sulfur) in rotation essential'
                }
            },
            
            GrapeDisease.BOTRYTIS_BUNCH_ROT: {
                'pathogen': 'Botrytis cinerea',
                'pathogen_type': 'Fungus',
                'dual_nature': 'DESTRUCTIVE vs BENEFICIAL',
                'symptoms': [
                    'GRAY FUZZY MOLD on berries and clusters',
                    'Berries split and rot',
                    'Sour rot smell',
                    'Entire cluster can collapse',
                    'Rapid spread in humid conditions'
                ],
                'beneficial_infection': {
                    'noble_rot': 'Pourriture Noble (French), Edelfäule (German)',
                    'wine_types': 'Sauternes, Tokaji, Trockenbeerenauslese',
                    'mechanism': 'Concentrates sugars, develops complex flavors',
                    'conditions': 'Morning fog, afternoon sun, controlled infection',
                    'value': 'Premium dessert wines ($100-1000+/bottle)'
                },
                'diagnostic_features': [
                    'GRAY MOLD characteristic',
                    'Pre-harvest infection most damaging',
                    'Tight clusters more susceptible',
                    'Wounded berries entry point',
                    'Cool humid weather favors'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(15, 20),
                    humidity_threshold=85,
                    leaf_wetness_hours=10,
                    rainfall_trigger_mm=5,
                    wind_dispersal=True,
                    risk_level='moderate',
                    infection_period_hours=8,
                    incubation_period_days=3
                ),
                'economic_impact': {
                    'destructive_loss': '20-30% pre-harvest',
                    'table_grapes': 'Unmarketable',
                    'wine_grapes': {
                        'dry_wines': 'Total loss',
                        'dessert_wines': 'Premium value if controlled'
                    }
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Switch', 'active': 'cyprodinil+fludioxonil', 'frac': '9+12'},
                        {'name': 'Elevate', 'active': 'fenhexamid', 'frac': '17'},
                        {'name': 'Rovral', 'active': 'iprodione', 'frac': '2'},
                        {'name': 'Scala', 'active': 'pyrimethanil', 'frac': '9'}
                    ],
                    cultural_controls=[
                        'Leaf removal in fruit zone (air circulation)',
                        'Cluster thinning (loose clusters)',
                        'Avoid late nitrogen',
                        'Powdery mildew control (berry cracks)',
                        'Insect control (berry damage)',
                        'Harvest timing critical'
                    ],
                    spray_interval_days=7,
                    resistance_management='Rotate FRAC groups, limited applications per group',
                    pre_harvest_interval=0,  # Some products day-of-harvest
                    treatment_cost_per_acre=250.0,
                    expected_yield_protection=70.0,
                    roi_ratio=5.5
                ),
                'management_decision': 'Wine type determines strategy: Prevent for dry wines, manage for dessert wines'
            },
            
            GrapeDisease.BLACK_ROT: {
                'pathogen': 'Guignardia bidwellii',
                'pathogen_type': 'Fungus',
                'origin': 'Native to North America',
                'symptoms': [
                    'Leaf lesions: Circular tan with dark border',
                    'Berry infection: Brown rot then MUMMIFICATION',
                    'MUMMIFIED BERRIES diagnostic (shriveled black)',
                    'Berries remain attached to cluster',
                    'Shoot lesions elongated sunken'
                ],
                'diagnostic_features': [
                    'MUMMIFIED BERRIES (pathognomonic)',
                    'Pycnidia (black dots) in lesions',
                    'Hot humid weather disease',
                    'Berry susceptibility bloom through 6-weeks post-bloom',
                    'Mummies overwinter on vines'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(21, 27),
                    humidity_threshold=85,
                    leaf_wetness_hours=8,
                    rainfall_trigger_mm=2.5,
                    wind_dispersal=True,
                    risk_level='high',
                    infection_period_hours=6,
                    incubation_period_days=10
                ),
                'economic_impact': {
                    'yield_loss': '5-80% depending on timing',
                    'early_infection': 'Total cluster loss',
                    'regional_importance': 'Major in hot humid climates (SE USA)'
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Mancozeb', 'active': 'mancozeb', 'frac': 'M3'},
                        {'name': 'Ziram', 'active': 'ziram', 'frac': 'M3'},
                        {'name': 'Abound', 'active': 'azoxystrobin', 'frac': '11'},
                        {'name': 'Pristine', 'active': 'pyraclostrobin+boscalid', 'frac': '11+7'}
                    ],
                    cultural_controls=[
                        'REMOVE MUMMIES (primary inoculum)',
                        'Canopy management',
                        'Avoid overhead irrigation',
                        'Pruning out infected canes'
                    ],
                    spray_interval_days=10,
                    resistance_management='Multi-site protectant fungicides key',
                    pre_harvest_interval=14,
                    treatment_cost_per_acre=200.0,
                    expected_yield_protection=75.0,
                    roi_ratio=6.0
                )
            },
            
            GrapeDisease.PIERCES_DISEASE: {
                'pathogen': 'Xylella fastidiosa',
                'pathogen_type': 'Bacteria (xylem-limited)',
                'vector': 'Glassy-winged sharpshooter leafhopper',
                'threat_level': 'LETHAL - NO CURE',
                'symptoms': [
                    'Leaf scorching (marginal necrosis)',
                    '"Matchstick" petioles (leaves drop, petiole attached)',
                    'Irregular cane maturation',
                    'Fruit shriveling',
                    'Vine death in 1-5 years'
                ],
                'diagnostic_features': [
                    'MATCHSTICK PETIOLES diagnostic',
                    'Uneven cane maturation (green islands)',
                    'Bacteria visible in xylem (microscope)',
                    'Southern California major threat',
                    'No recovery - progressive decline'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(25, 32),
                    humidity_threshold=0,
                    leaf_wetness_hours=0,
                    rainfall_trigger_mm=0,
                    wind_dispersal=False,
                    risk_level='CRITICAL',
                    incubation_period_days=90
                ),
                'economic_impact': {
                    'vine_loss': '100% infected vines die',
                    'vineyard_loss': 'Can destroy entire vineyard',
                    'california_threat': 'Threatens $5.4 billion wine industry',
                    'quarantine': 'Movement restrictions in place'
                },
                'treatment': TreatmentPlan(
                    bactericides=[],  # NO EFFECTIVE TREATMENT
                    cultural_controls=[
                        'Vector control (glassy-winged sharpshooter)',
                        'Remove infected vines IMMEDIATELY',
                        'Use resistant rootstocks (limited)',
                        'Quarantine measures',
                        'Biological control of vector'
                    ],
                    spray_interval_days=0,
                    resistance_management='NO CURE - prevention only',
                    treatment_cost_per_acre=0.0,
                    expected_yield_protection=0.0,
                    roi_ratio=0.0
                ),
                'notes': 'ERADICATION DISEASE - remove and burn infected vines immediately'
            }
        }
    
    def _initialize_variety_resistance(self) -> Dict[GrapeVarietyType, Dict]:
        """Variety-specific disease resistance"""
        return {
            GrapeVarietyType.WINE_RED: {
                'varieties': ['Cabernet Sauvignon', 'Merlot', 'Pinot Noir'],
                'downy_mildew': 'susceptible to moderate',
                'powdery_mildew': 'susceptible',
                'botrytis': 'Pinot Noir highly susceptible (tight clusters)',
                'notes': 'Intensive spray programs required'
            },
            GrapeVarietyType.WINE_WHITE: {
                'varieties': ['Chardonnay', 'Sauvignon Blanc', 'Riesling'],
                'downy_mildew': 'susceptible',
                'powdery_mildew': 'susceptible',
                'botrytis': 'Riesling - noble rot compatible',
                'notes': 'Riesling used for dessert wines (controlled Botrytis)'
            }
        }
    
    def detect_downy_mildew(self, image: np.ndarray,
                           environmental_data: Dict) -> Optional[DetectionResult]:
        """
        Detect Grape Downy Mildew (Plasmopara viticola)
        
        DIAGNOSTIC: "Oil spot" lesions on top, white sporulation underneath
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Oil spot lesions (yellow-brown on top surface)
        lower_oil = np.array([20, 30, 100])
        upper_oil = np.array([40, 150, 200])
        oil_mask = cv2.inRange(hsv, lower_oil, upper_oil)
        
        # White sporulation (underside)
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 40, 255])
        white_mask = cv2.inRange(hsv, lower_white, upper_white)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        oil_mask = cv2.morphologyEx(oil_mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(oil_mask, cv2.RETR_EXTERNAL,
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
            
            # Check for white sporulation
            roi_white = white_mask[y:y+h, x:x+w]
            sporulation = np.sum(roi_white > 0) > (w * h * 0.1)
            
            lesion = GrapeLesion(
                color_hsv_range=((20, 30, 100), (40, 150, 200)),
                shape='irregular',
                texture='oily',
                location='leaf',
                size_mm=(w * 0.1, h * 0.1),
                progression='expanding',
                margin='diffuse',
                oil_spot_appearance=True,
                yield_loss_percent=70.0,
                wine_quality_impact='severe'
            )
            lesions.append(lesion)
            total_area += area
        
        affected_area = (total_area / (image.shape[0] * image.shape[1])) * 100
        confidence = min(0.6 + (affected_area / 40) * 0.25, 0.90)
        
        disease_info = self.disease_database[GrapeDisease.DOWNY_MILDEW]
        
        return DetectionResult(
            disease=GrapeDisease.DOWNY_MILDEW,
            confidence=confidence,
            severity=min(affected_area * 2, 100),
            affected_area_percent=affected_area,
            lesion_count=len(lesions),
            lesions=lesions,
            environmental_risk=disease_info['environmental'],
            treatment_plan=disease_info['treatment'],
            harvest_recommendation='Spray immediately, 7-10 day intervals'
        )
    
    def detect_powdery_mildew(self, image: np.ndarray) -> Optional[DetectionResult]:
        """
        Detect Grape Powdery Mildew (Erysiphe necator)
        
        #1 GRAPE DISEASE WORLDWIDE
        DIAGNOSTIC: White powdery coating
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # White powdery growth
        lower_powder = np.array([0, 0, 180])
        upper_powder = np.array([180, 50, 255])
        powder_mask = cv2.inRange(hsv, lower_powder, upper_powder)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        powder_mask = cv2.morphologyEx(powder_mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(powder_mask, cv2.RETR_EXTERNAL,
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
            
            lesion = GrapeLesion(
                color_hsv_range=((0, 0, 180), (180, 50, 255)),
                shape='irregular',
                texture='powdery',
                location='leaf',
                size_mm=(w * 0.1, h * 0.1),
                progression='expanding',
                margin='diffuse',
                white_powdery_growth=True,
                yield_loss_percent=30.0,
                wine_quality_impact='severe',
                table_grape_marketability='unmarketable'
            )
            lesions.append(lesion)
            total_area += area
        
        affected_area = (total_area / (image.shape[0] * image.shape[1])) * 100
        confidence = min(0.7 + (affected_area / 30) * 0.2, 0.95)
        
        disease_info = self.disease_database[GrapeDisease.POWDERY_MILDEW]
        
        return DetectionResult(
            disease=GrapeDisease.POWDERY_MILDEW,
            confidence=confidence,
            severity=min(affected_area * 1.8, 100),
            affected_area_percent=affected_area,
            lesion_count=len(lesions),
            lesions=lesions,
            environmental_risk=disease_info['environmental'],
            treatment_plan=disease_info['treatment'],
            harvest_recommendation='Rotate FRAC groups - resistance common'
        )


def main():
    """Example usage"""
    detector = GrapeDiseaseDetector()
    
    print("=== AgroPulse Grape Disease Detection System ===")
    print(f"Monitoring {len(detector.disease_database)} major grape diseases")
    print("\nCRITICAL PATHOGENS:")
    print("1. Downy Mildew - European viticulture collapse 1870s")
    print("   - $3 billion annual losses")
    print("   - Oil spot lesions diagnostic")
    print("\n2. Powdery Mildew - #1 grape disease worldwide")
    print("   - Fungicide resistance crisis")
    print("   - $1 billion annual losses")
    print("\n3. Pierce's Disease - LETHAL bacterial")
    print("   - NO CURE")
    print("   - California wine industry threat")


if __name__ == "__main__":
    main()
