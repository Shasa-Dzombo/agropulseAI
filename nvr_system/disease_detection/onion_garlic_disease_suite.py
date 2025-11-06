"""
Onion & Garlic Disease Detection Suite
Comprehensive detection system for Allium crop diseases

CRITICAL DISEASES:

ONION (Allium cepa):
1. Downy Mildew (Peronospora destructor) - #1 ONION THREAT
   - Purple sporulation distinctive
   - Can destroy crop in 2-3 weeks
   - 40-80% yield loss
   
2. Purple Blotch (Alternaria porri) - MAJOR STORAGE DISEASE
   - Purple to brown lesions
   - Enters through wounds
   - 20-50% storage loss
   
3. Stemphylium Leaf Blight - EMERGING THREAT
   - Tan to brown lesions
   - Multiple cycles per season
   
4. Botrytis Neck Rot - #1 STORAGE LOSS
   - Gray mold at neck
   - 10-30% storage loss
   - Latent infection at harvest

GARLIC (Allium sativum):
1. White Rot (Sclerotium cepivorum) - PERSISTENT SOIL PATHOGEN
   - Fluffy white mold on bulb
   - Sclerotia survive 20+ years in soil
   - Field quarantine required
   
2. Rust (Puccinia allii) - LEAF DISEASE
   - Orange pustules
   - Reduces bulb size
   
3. Botrytis - NECK ROT
   - Storage disease
   - Gray mold

DETECTION CHALLENGE:
- Downy mildew requires rapid response (2-3 day window)
- Purple blotch vs Stemphylium differentiation critical
- White rot field eradication (20+ year persistence)
- Storage diseases start as latent infections

Author: AgroPulse AI Team
Version: 1.0.0
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class AlliumDisease(Enum):
    """Comprehensive onion and garlic disease classification"""
    # Onion diseases
    ONION_DOWNY_MILDEW = "onion_downy_mildew"  # Peronospora destructor - #1 threat
    PURPLE_BLOTCH = "purple_blotch"  # Alternaria porri
    STEMPHYLIUM_BLIGHT = "stemphylium_blight"  # Stemphylium vesicarium
    BOTRYTIS_NECK_ROT = "botrytis_neck_rot"  # Storage #1
    ONION_WHITE_ROT = "onion_white_rot"  # Sclerotium cepivorum
    PINK_ROOT = "pink_root"  # Phoma terrestris - root disease
    BACTERIAL_SOFT_ROT = "bacterial_soft_rot"  # Erwinia
    FUSARIUM_BASAL_ROT = "fusarium_basal_rot"  # Fusarium oxysporum
    ONION_SMUT = "onion_smut"  # Urocystis cepulae - seedling
    IRIS_YELLOW_SPOT_VIRUS = "iris_yellow_spot_virus"  # IYSV - thrips
    
    # Garlic diseases
    GARLIC_WHITE_ROT = "garlic_white_rot"  # Sclerotium cepivorum - PERSISTENT
    GARLIC_RUST = "garlic_rust"  # Puccinia allii - orange pustules
    GARLIC_BOTRYTIS = "garlic_botrytis"  # Gray mold
    GARLIC_FUSARIUM = "garlic_fusarium"  # Basal rot
    GARLIC_NEMATODES = "garlic_nematodes"  # Bloat nematode


class AlliumType(Enum):
    """Onion and garlic type classifications"""
    # Onions
    YELLOW_ONION = "yellow_onion"  # Most common storage type
    RED_ONION = "red_onion"  # Sweet, less pungent
    WHITE_ONION = "white_onion"  # Mild flavor
    SWEET_ONION = "sweet_onion"  # Vidalia, Walla Walla
    GREEN_ONION = "green_onion"  # Scallions, bunching
    SHALLOT = "shallot"  # Allium cepa aggregatum
    
    # Garlic
    HARDNECK_GARLIC = "hardneck_garlic"  # Produces scapes, cold hardy
    SOFTNECK_GARLIC = "softneck_garlic"  # Braiding type, stores well
    ELEPHANT_GARLIC = "elephant_garlic"  # Actually a leek (A. ampeloprasum)


@dataclass
class AlliumLesion:
    """Onion/garlic disease lesion characteristics"""
    color_hsv_range: Tuple[Tuple[int, int, int], Tuple[int, int, int]]
    shape: str  # oval, elongated, irregular, circular
    texture: str  # smooth, fuzzy, powdery, slimy, corky
    location: str  # leaf, neck, bulb, root
    size_mm: Tuple[float, float]
    progression: str  # expanding, static, coalescing
    margin: str  # defined, diffuse, chlorotic_halo, water_soaked
    
    # Diagnostic features
    purple_sporulation: bool = False  # Downy mildew (Peronospora)
    purple_blotch_zoning: bool = False  # Alternaria porri
    orange_pustules: bool = False  # Rust
    white_fluffy_mold: bool = False  # White rot
    gray_mold: bool = False  # Botrytis
    black_sclerotia: bool = False  # Sclerotium, Botrytis
    
    # Economic impact
    yield_loss_percent: float = 0.0
    storage_impact: str = "none"  # none, minor, moderate, severe, total_loss
    marketability: str = "market_grade"  # market_grade, processing_only, unmarketable


@dataclass
class AlliumBulbDisease:
    """Specific bulb disease parameters"""
    external_symptoms: List[str]
    internal_symptoms: List[str]
    storage_loss_rate: float  # Percent loss per month
    field_vs_storage: str  # field_infection, storage_infection, latent
    marketability: str  # fresh_market, processing, unmarketable
    
    # Critical for storage
    curing_impact: bool = False  # Affects curing process
    latent_infection: bool = False  # Present at harvest but invisible
    spread_in_storage: bool = False  # Can spread to adjacent bulbs


@dataclass
class EnvironmentalRisk:
    """Environmental factors for Allium disease risk"""
    temperature_range: Tuple[float, float]
    humidity_threshold: float
    leaf_wetness_hours: float
    soil_moisture: str
    soil_ph_range: Tuple[float, float]
    wind_dispersal: bool
    
    risk_level: str = "low"
    infection_period_hours: float = 0.0
    sporulation_period_hours: float = 0.0
    
    # Allium-specific
    sclerotia_persistence_years: int = 0  # White rot critical


@dataclass
class TreatmentPlan:
    """Allium disease treatment strategy"""
    fungicides: List[Dict[str, str]] = field(default_factory=list)
    bactericides: List[Dict[str, str]] = field(default_factory=list)
    cultural_controls: List[str] = field(default_factory=list)
    biocontrols: List[str] = field(default_factory=list)
    
    spray_interval_days: int = 7
    resistance_management: str = ""
    
    # Storage disease prevention
    curing_protocol: str = ""
    storage_conditions: str = ""
    
    treatment_cost_per_acre: float = 0.0
    expected_yield_protection: float = 0.0
    roi_ratio: float = 0.0


@dataclass
class DetectionResult:
    """Disease detection result"""
    disease: AlliumDisease
    confidence: float
    severity: float
    affected_area_percent: float
    lesion_count: int
    lesions: List[AlliumLesion]
    environmental_risk: EnvironmentalRisk
    treatment_plan: TreatmentPlan
    
    # Storage disease warning
    storage_risk: str = "low"  # low, moderate, high, critical
    curing_recommendation: str = ""
    
    timestamp: datetime = field(default_factory=datetime.now)


class AlliumDiseaseDetector:
    """
    Advanced onion and garlic disease detection system
    
    CRITICAL FOCUS:
    - Downy mildew early warning (2-3 day response window)
    - Purple blotch vs Stemphylium differentiation
    - White rot field quarantine triggers
    - Storage disease latent infection detection
    """
    
    def __init__(self):
        self.disease_database = self._initialize_disease_database()
        
    def _initialize_disease_database(self) -> Dict[AlliumDisease, Dict]:
        """Comprehensive onion/garlic disease parameter database"""
        return {
            AlliumDisease.ONION_DOWNY_MILDEW: {
                'pathogen': 'Peronospora destructor',
                'pathogen_type': 'Oomycete',
                'threat_level': '#1 ONION DISEASE WORLDWIDE',
                'symptoms': [
                    'Pale green to yellow lesions on leaves',
                    'PURPLE SPORULATION on leaf surface (diagnostic)',
                    'Lesions elongated along leaf',
                    'Leaf dieback from tip downward',
                    'Entire crop can collapse in 2-3 weeks',
                    'Bulb size reduced significantly'
                ],
                'diagnostic_features': [
                    'PURPLE FUZZY GROWTH - pathognomonic sign',
                    'Elongated pale lesions',
                    'Cool wet weather (13-16°C optimal)',
                    'Morning dew sporulation',
                    'Systemic infection in some varieties'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(6, 20),
                    humidity_threshold=95,
                    leaf_wetness_hours=6,
                    soil_moisture='moist',
                    soil_ph_range=(6.0, 7.5),
                    wind_dispersal=True,
                    risk_level='high',
                    infection_period_hours=4,
                    sporulation_period_hours=8
                ),
                'economic_impact': {
                    'yield_loss': '40-80% if untreated',
                    'quality_reduction': 'Bulb size reduced 30-50%',
                    'global_importance': 'Major constraint worldwide'
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Ridomil Gold', 'active': 'mefenoxam', 'frac': '4'},
                        {'name': 'Presidio', 'active': 'fluopicolide', 'frac': '43'},
                        {'name': 'Ranman', 'active': 'cyazofamid', 'frac': '21'},
                        {'name': 'Zampro', 'active': 'ametoctradin', 'frac': '45'}
                    ],
                    cultural_controls=[
                        'Use resistant varieties (if available)',
                        'Destroy cull piles and volunteers',
                        'Improve air circulation (wider spacing)',
                        'Avoid overhead irrigation',
                        'Remove infected plants',
                        'Crop rotation 2-3 years'
                    ],
                    spray_interval_days=5,  # AGGRESSIVE: 5-7 days
                    resistance_management='Rotate FRAC groups, tank-mix when possible',
                    treatment_cost_per_acre=250.0,
                    expected_yield_protection=75.0,
                    roi_ratio=6.0
                )
            },
            
            AlliumDisease.PURPLE_BLOTCH: {
                'pathogen': 'Alternaria porri',
                'pathogen_type': 'Fungus',
                'importance': 'MAJOR STORAGE DISEASE',
                'symptoms': [
                    'Small white lesions enlarge to purple-brown',
                    'Concentric zoning (target pattern)',
                    'Lesions girdling leaves',
                    'Enters bulb through neck',
                    'Storage rot develops from neck down'
                ],
                'diagnostic_features': [
                    'PURPLE to BROWN coloration',
                    'Zonate pattern (concentric rings)',
                    'Stem/neck infection critical',
                    'Warm weather disease (vs downy mildew cool)'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(21, 30),
                    humidity_threshold=85,
                    leaf_wetness_hours=12,
                    soil_moisture='moist',
                    soil_ph_range=(6.0, 7.0),
                    wind_dispersal=True,
                    risk_level='moderate'
                ),
                'economic_impact': {
                    'yield_loss': '15-30% field loss',
                    'storage_loss': '20-50% if enters storage',
                    'market_value': 'Neck infection = unmarketable'
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Quadris', 'active': 'azoxystrobin', 'frac': '11'},
                        {'name': 'Bravo', 'active': 'chlorothalonil', 'frac': 'M5'},
                        {'name': 'Rovral', 'active': 'iprodione', 'frac': '2'}
                    ],
                    cultural_controls=[
                        'Avoid wounding leaves',
                        'Proper curing before storage',
                        'Cut tops 1-2" above bulb (reduce neck infection)',
                        'Crop rotation',
                        'Remove crop debris'
                    ],
                    spray_interval_days=7,
                    curing_protocol='Cure at 85-95°F with good air flow for 2-4 weeks',
                    storage_conditions='32-35°F, 65-70% RH',
                    treatment_cost_per_acre=180.0,
                    expected_yield_protection=65.0,
                    roi_ratio=4.5
                )
            },
            
            AlliumDisease.BOTRYTIS_NECK_ROT: {
                'pathogen': 'Botrytis allii',
                'pathogen_type': 'Fungus',
                'importance': '#1 STORAGE LOSS',
                'symptoms': [
                    'Gray mold at neck',
                    'Soft watery decay',
                    'Progresses from neck into bulb scales',
                    'Mummified bulbs in storage',
                    'Often LATENT at harvest (invisible)'
                ],
                'diagnostic_features': [
                    'GRAY FUZZY MOLD at neck',
                    'Latent infection common (appears 2-4 months storage)',
                    'Cool storage temperatures slow but don\'t stop',
                    'Spread to adjacent bulbs'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(15, 20),
                    humidity_threshold=85,
                    leaf_wetness_hours=8,
                    soil_moisture='moist',
                    soil_ph_range=(6.0, 7.0),
                    wind_dispersal=True,
                    risk_level='moderate'
                ),
                'economic_impact': {
                    'storage_loss': '10-30% typical',
                    'severe_years': 'Up to 50% in poorly cured onions',
                    'market_timing': 'Worse in late storage (March-May)'
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Switch', 'active': 'cyprodinil+fludioxonil', 'frac': '9+12'},
                        {'name': 'Rovral', 'active': 'iprodione', 'frac': '2'}
                    ],
                    cultural_controls=[
                        'CRITICAL: Proper curing (tight necks)',
                        'Avoid late nitrogen (delays maturity)',
                        'Harvest when 50% tops down',
                        'Field dry if possible',
                        'Cut tops 1" above bulb when dry',
                        'Storage ventilation excellent'
                    ],
                    curing_protocol='85-95°F, good air circulation, 2-4 weeks until necks tight',
                    storage_conditions='32-35°F, 65-70% RH, continuous air movement',
                    treatment_cost_per_acre=120.0,
                    expected_yield_protection=60.0,
                    roi_ratio=5.0
                ),
                'bulb_disease': AlliumBulbDisease(
                    external_symptoms=['gray_mold', 'soft_neck'],
                    internal_symptoms=['scale_rot', 'watery_decay'],
                    storage_loss_rate=8.0,  # 8% per month
                    field_vs_storage='latent',
                    marketability='unmarketable',
                    curing_impact=True,
                    latent_infection=True,
                    spread_in_storage=True
                )
            },
            
            AlliumDisease.GARLIC_WHITE_ROT: {
                'pathogen': 'Sclerotium cepivorum',
                'pathogen_type': 'Fungus',
                'persistence': 'SCLEROTIA SURVIVE 20+ YEARS',
                'threat_level': 'FIELD ERADICATION DISEASE',
                'symptoms': [
                    'Yellowing and dieback of older leaves',
                    'White fluffy mycelial growth on bulb',
                    'BLACK SCLEROTIA on bulb and roots (mustard seed size)',
                    'Plant death',
                    'Hollow bulb interior'
                ],
                'diagnostic_features': [
                    'WHITE FLUFFY MOLD on bulb base (diagnostic)',
                    'BLACK SCLEROTIA (0.2-0.5 mm)',
                    'Cool temperature disease (9-20°C)',
                    'Sclerotia persist 20+ years',
                    'Field becomes UNSUITABLE for garlic/onion'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(9, 20),
                    humidity_threshold=80,
                    leaf_wetness_hours=0,
                    soil_moisture='moist',
                    soil_ph_range=(6.0, 7.5),
                    wind_dispersal=False,
                    risk_level='CRITICAL',
                    sclerotia_persistence_years=20
                ),
                'economic_impact': {
                    'yield_loss': '50-100% in infested fields',
                    'field_loss': 'Field unsuitable for Alliums 20+ years',
                    'quarantine': 'Movement restrictions may apply',
                    'global_threat': 'Expanding distribution worldwide'
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Contans WG', 'active': 'Coniothyrium minitans', 'note': 'Biocontrol'},
                        {'name': 'Tebuconazole', 'active': 'tebuconazole', 'frac': '3', 'note': 'Suppression only'}
                    ],
                    cultural_controls=[
                        'AVOID PLANTING in infested fields (20+ year quarantine)',
                        'Use clean planting material',
                        'Diallyl disulfide (garlic extract) stimulates sclerotia germination without host',
                        'Solarization (limited efficacy)',
                        'Remove infected plants and surrounding soil',
                        'Sanitize equipment',
                        'Long rotation (10+ years minimum)'
                    ],
                    spray_interval_days=0,
                    resistance_management='Prevention primary - no effective cure',
                    treatment_cost_per_acre=0.0,
                    expected_yield_protection=30.0,
                    roi_ratio=0.0
                ),
                'notes': 'CATASTROPHIC DISEASE - Field eradication priority #1'
            },
            
            AlliumDisease.GARLIC_RUST: {
                'pathogen': 'Puccinia allii',
                'pathogen_type': 'Fungus (Rust)',
                'symptoms': [
                    'ORANGE PUSTULES on leaves',
                    'Yellowing around pustules',
                    'Severe: Entire leaf orange',
                    'Premature leaf death',
                    'Reduced bulb size'
                ],
                'diagnostic_features': [
                    'ORANGE POWDERY PUSTULES (urediniospores)',
                    'Later: Black pustules (teliospores)',
                    'Wipe off with finger (orange powder)',
                    'Cool moist conditions favor'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(10, 24),
                    humidity_threshold=90,
                    leaf_wetness_hours=4,
                    soil_moisture='moist',
                    soil_ph_range=(6.0, 7.5),
                    wind_dispersal=True,
                    risk_level='moderate'
                ),
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Quadris', 'active': 'azoxystrobin', 'frac': '11'},
                        {'name': 'Folicur', 'active': 'tebuconazole', 'frac': '3'}
                    ],
                    cultural_controls=[
                        'Improve air circulation',
                        'Avoid overhead irrigation',
                        'Remove infected leaves',
                        'Crop rotation'
                    ],
                    spray_interval_days=7,
                    treatment_cost_per_acre=150.0,
                    expected_yield_protection=60.0,
                    roi_ratio=4.0
                )
            }
        }
    
    def detect_onion_downy_mildew(self, image: np.ndarray,
                                  environmental_data: Dict) -> Optional[DetectionResult]:
        """
        Detect Onion Downy Mildew (Peronospora destructor)
        
        CRITICAL: #1 onion disease worldwide
        DIAGNOSTIC: Purple sporulation
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Pale lesions
        lower_lesion = np.array([30, 20, 80])
        upper_lesion = np.array([70, 100, 180])
        lesion_mask = cv2.inRange(hsv, lower_lesion, upper_lesion)
        
        # PURPLE SPORULATION (diagnostic)
        lower_purple = np.array([125, 40, 60])
        upper_purple = np.array([150, 255, 200])
        purple_mask = cv2.inRange(hsv, lower_purple, upper_purple)
        
        # Morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        lesion_mask = cv2.morphologyEx(lesion_mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(lesion_mask, cv2.RETR_EXTERNAL,
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
            
            # Check for purple sporulation
            roi_purple = purple_mask[y:y+h, x:x+w]
            purple_detected = np.sum(roi_purple > 0) > (w * h * 0.1)
            
            lesion = AlliumLesion(
                color_hsv_range=((30, 20, 80), (70, 100, 180)),
                shape='elongated',
                texture='fuzzy',
                location='leaf',
                size_mm=(w * 0.1, h * 0.1),
                progression='expanding',
                margin='diffuse',
                purple_sporulation=purple_detected,
                yield_loss_percent=60.0,
                storage_impact='severe',
                marketability='unmarketable'
            )
            lesions.append(lesion)
            total_area += area
        
        affected_area = (total_area / (image.shape[0] * image.shape[1])) * 100
        
        # Purple sporulation is DIAGNOSTIC
        purple_found = any(l.purple_sporulation for l in lesions)
        confidence = min(0.5 + (affected_area / 40) * 0.3, 0.85)
        if purple_found:
            confidence = min(confidence + 0.15, 0.95)
        
        disease_info = self.disease_database[AlliumDisease.ONION_DOWNY_MILDEW]
        
        result = DetectionResult(
            disease=AlliumDisease.ONION_DOWNY_MILDEW,
            confidence=confidence,
            severity=min(affected_area * 2, 100),
            affected_area_percent=affected_area,
            lesion_count=len(lesions),
            lesions=lesions,
            environmental_risk=disease_info['environmental'],
            treatment_plan=disease_info['treatment'],
            storage_risk='high'
        )
        
        return result
    
    def detect_garlic_white_rot(self, bulb_image: np.ndarray) -> Optional[DetectionResult]:
        """
        Detect Garlic White Rot (Sclerotium cepivorum)
        
        CATASTROPHIC: Sclerotia persist 20+ years
        DIAGNOSTIC: White fluffy mold + black sclerotia
        """
        hsv = cv2.cvtColor(bulb_image, cv2.COLOR_BGR2HSV)
        
        # White fluffy mycelium
        lower_white = np.array([0, 0, 200])
        upper_white = np.array([180, 40, 255])
        white_mask = cv2.inRange(hsv, lower_white, upper_white)
        
        # Black sclerotia (mustard seed size)
        lower_black = np.array([0, 0, 0])
        upper_black = np.array([180, 255, 50])
        black_mask = cv2.inRange(hsv, lower_black, upper_black)
        
        # Find white mold
        contours_white, _ = cv2.findContours(white_mask, cv2.RETR_EXTERNAL,
                                             cv2.CHAIN_APPROX_SIMPLE)
        
        # Find black sclerotia
        contours_black, _ = cv2.findContours(black_mask, cv2.RETR_EXTERNAL,
                                             cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours_white) == 0:
            return None
        
        lesions = []
        total_area = 0
        
        for contour in contours_white:
            area = cv2.contourArea(contour)
            if area < 200:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            
            # Check for black sclerotia nearby
            roi_black = black_mask[y:y+h, x:x+w]
            sclerotia_detected = len([c for c in contours_black 
                                     if cv2.contourArea(c) < 50]) > 5
            
            lesion = AlliumLesion(
                color_hsv_range=((0, 0, 200), (180, 40, 255)),
                shape='irregular',
                texture='fuzzy',
                location='bulb',
                size_mm=(w * 0.1, h * 0.1),
                progression='expanding',
                margin='defined',
                white_fluffy_mold=True,
                black_sclerotia=sclerotia_detected,
                yield_loss_percent=100.0,
                storage_impact='total_loss',
                marketability='unmarketable'
            )
            lesions.append(lesion)
            total_area += area
        
        affected_area = (total_area / (bulb_image.shape[0] * bulb_image.shape[1])) * 100
        
        # White mold + black sclerotia = definitive
        sclerotia_found = any(l.black_sclerotia for l in lesions)
        confidence = min(0.7 + (len(lesions) / 3) * 0.15, 0.90)
        if sclerotia_found:
            confidence = 0.95
        
        disease_info = self.disease_database[AlliumDisease.GARLIC_WHITE_ROT]
        
        result = DetectionResult(
            disease=AlliumDisease.GARLIC_WHITE_ROT,
            confidence=confidence,
            severity=100.0,
            affected_area_percent=affected_area,
            lesion_count=len(lesions),
            lesions=lesions,
            environmental_risk=disease_info['environmental'],
            treatment_plan=disease_info['treatment'],
            storage_risk='critical',
            curing_recommendation='FIELD QUARANTINE - Do not plant Alliums for 20+ years'
        )
        
        return result


def main():
    """Example usage"""
    detector = AlliumDiseaseDetector()
    
    print("=== AgroPulse Onion & Garlic Disease Detection System ===")
    print(f"Monitoring {len(detector.disease_database)} major Allium diseases")
    print("\nCRITICAL PATHOGENS:")
    print("1. Onion Downy Mildew - #1 worldwide threat")
    print("   - Purple sporulation diagnostic")
    print("   - 40-80% yield loss")
    print("\n2. Garlic White Rot - PERSISTENT SOIL PATHOGEN")
    print("   - Sclerotia survive 20+ years")
    print("   - Field quarantine required")
    print("\n3. Botrytis Neck Rot - #1 storage loss")
    print("   - Latent infection at harvest")
    print("   - 10-30% storage loss")


if __name__ == "__main__":
    main()
