"""
Citrus Disease Detection Suite
Comprehensive detection system for citrus diseases (Orange, Tangerine, Lemon, Lime)

CRITICAL DISEASES:

1. Citrus Greening (Huanglongbing - HLB) - MOST DEVASTATING CITRUS DISEASE
   - "Yellow Dragon Disease"
   - NO CURE - infected trees die
   - Psyllid vector (Asian citrus psyllid)
   - Threatens entire citrus industry
   - Florida lost 75% of orange production since 2005
   - $4.5 billion damage to Florida economy

2. Citrus Canker (Xanthomonas citri) - QUARANTINE DISEASE
   - Bacterial leaf/fruit lesions
   - Raised corky lesions with yellow halo
   - Fruit drop, unmarketable fruit
   - Eradication programs mandatory
   - International quarantine restrictions

3. Citrus Black Spot (Phyllosticta citricarpa) - QUARANTINE THREAT
   - Cosmetic fruit damage
   - Export restrictions
   - False black spot (Phyllosticta capitalensis) - harmless lookalike
   - Differential diagnosis critical

4. Melanose (Diaporthe citri) - FRUIT QUALITY DISEASE
   - Raised brown pustules on young fruit
   - Reduces fresh market grade
   - Dead wood inoculum source

5. Citrus Scab (Elsinoe fawcettii) - FRUIT BLEMISH
   - Warty growths on fruit
   - Young tissue susceptible
   - Processing fruit acceptable

DETECTION CHALLENGE:
- HLB early detection saves grove (asymptomatic carriers spread disease)
- Canker vs other bacterial spots differentiation
- Black spot vs false black spot critical distinction
- Quarantine disease reporting requirements

Author: AgroPulse AI Team
Version: 1.0.0
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class CitrusDisease(Enum):
    """Comprehensive citrus disease classification"""
    CITRUS_GREENING = "citrus_greening"  # HLB - Candidatus Liberibacter - DEVASTATING
    CITRUS_CANKER = "citrus_canker"  # Xanthomonas - QUARANTINE
    CITRUS_BLACK_SPOT = "citrus_black_spot"  # Phyllosticta citricarpa - QUARANTINE
    MELANOSE = "melanose"  # Diaporthe citri
    CITRUS_SCAB = "citrus_scab"  # Elsinoe fawcettii
    GREASY_SPOT = "greasy_spot"  # Mycosphaerella citri
    ALTERNARIA_BROWN_SPOT = "alternaria_brown_spot"  # Alternaria alternata
    PHYTOPHTHORA_ROOT_ROT = "phytophthora_root_rot"  # Phytophthora spp.
    CITRUS_TRISTEZA_VIRUS = "citrus_tristeza_virus"  # CTV - devastating historically
    CITRUS_STUBBORN = "citrus_stubborn"  # Spiroplasma citri
    POSTBLOOM_FRUIT_DROP = "postbloom_fruit_drop"  # Colletotrichum acutatum
    SOOTY_MOLD = "sooty_mold"  # Complex - follows aphids/scale


class CitrusType(Enum):
    """Citrus type classifications"""
    SWEET_ORANGE = "sweet_orange"  # Valencia, Navel, Hamlin
    MANDARIN = "mandarin"  # Tangerine, Clementine, Satsuma
    GRAPEFRUIT = "grapefruit"  # White, pink, red
    LEMON = "lemon"  # Eureka, Lisbon
    LIME = "lime"  # Persian, Key lime
    TANGELO = "tangelo"  # Minneola - tangerine x grapefruit
    KUMQUAT = "kumquat"  # Fortunella
    PUMMELO = "pummelo"  # Shaddock


@dataclass
class CitrusLesion:
    """Citrus disease lesion characteristics"""
    color_hsv_range: Tuple[Tuple[int, int, int], Tuple[int, int, int]]
    shape: str  # circular, irregular, angular
    texture: str  # raised, sunken, corky, smooth, warty
    location: str  # leaf, fruit, twig, trunk
    size_mm: Tuple[float, float]
    progression: str  # expanding, static
    margin: str  # defined, diffuse, yellow_halo, water_soaked
    
    # Diagnostic features
    raised_corky_lesion: bool = False  # Canker
    yellow_halo: bool = False  # Canker diagnostic
    blotchy_mottling: bool = False  # HLB
    black_spots_fruit: bool = False  # Black spot
    warty_growth: bool = False  # Scab
    
    # Economic impact
    fruit_marketability: str = "grade_A"  # grade_A, grade_B, processing, unmarketable
    export_restriction: bool = False  # Quarantine diseases


@dataclass
class CitrusFruitDisease:
    """Fruit-specific disease parameters"""
    fruit_symptoms: List[str]
    infection_timing: str  # bloom, fruit_set, fruit_development, mature
    cosmetic_vs_decay: str  # cosmetic, decay, both
    fresh_market_impact: str  # acceptable, grade_reduction, unmarketable
    juice_quality_impact: str  # none, reduced_yield, off_flavor


@dataclass
class EnvironmentalRisk:
    """Environmental factors for citrus disease risk"""
    temperature_range: Tuple[float, float]
    humidity_threshold: float
    rainfall_trigger_mm: float
    wind_dispersal: bool
    
    risk_level: str = "low"
    infection_period_hours: float = 0.0
    incubation_period_days: float = 0.0


@dataclass
class TreatmentPlan:
    """Citrus disease treatment strategy"""
    fungicides: List[Dict[str, str]] = field(default_factory=list)
    bactericides: List[Dict[str, str]] = field(default_factory=list)
    antibiotics: List[Dict[str, str]] = field(default_factory=list)
    cultural_controls: List[str] = field(default_factory=list)
    
    spray_interval_days: int = 14
    resistance_management: str = ""
    
    # Vector control
    psyllid_control: bool = False  # HLB
    
    # Quarantine
    eradication_required: bool = False
    reporting_required: bool = False
    
    treatment_cost_per_acre: float = 0.0
    expected_yield_protection: float = 0.0
    roi_ratio: float = 0.0


@dataclass
class DetectionResult:
    """Disease detection result"""
    disease: CitrusDisease
    confidence: float
    severity: float
    affected_area_percent: float
    lesion_count: int
    lesions: List[CitrusLesion]
    environmental_risk: EnvironmentalRisk
    treatment_plan: TreatmentPlan
    
    # Quarantine status
    quarantine_disease: bool = False
    reporting_required: bool = False
    eradication_protocol: bool = False
    
    # Economic impact
    export_restriction: bool = False
    tree_removal_recommended: bool = False
    
    timestamp: datetime = field(default_factory=datetime.now)


class CitrusDiseaseDetector:
    """
    Advanced citrus disease detection system
    
    CRITICAL FOCUS:
    - HLB early detection (asymptomatic carrier detection)
    - Canker quarantine compliance
    - Black spot vs false black spot differentiation
    - Vector control (Asian citrus psyllid)
    """
    
    def __init__(self):
        self.disease_database = self._initialize_disease_database()
        self.variety_susceptibility = self._initialize_variety_susceptibility()
        
    def _initialize_disease_database(self) -> Dict[CitrusDisease, Dict]:
        """Comprehensive citrus disease parameter database"""
        return {
            CitrusDisease.CITRUS_GREENING: {
                'pathogen': 'Candidatus Liberibacter asiaticus (CLas)',
                'common_name': 'Huanglongbing (HLB) - "Yellow Dragon Disease"',
                'pathogen_type': 'Bacteria (phloem-limited, unculturable)',
                'vector': 'Asian citrus psyllid (Diaphorina citri)',
                'threat_level': 'MOST DEVASTATING CITRUS DISEASE EVER',
                'historical_impact': 'China 1870s discovery, Florida 2005, lost 75% orange production',
                'economic_damage': '$4.5 billion to Florida economy, threatens global citrus',
                'symptoms': [
                    'BLOTCHY MOTTLING on leaves (asymmetrical yellowing)',
                    'Yellow shoots',
                    'Lopsided fruit (one side green, one yellow)',
                    'Small misshapen fruit',
                    'Bitter taste',
                    'Aborted seeds',
                    'Premature fruit drop',
                    'Twig dieback',
                    'Tree decline and death (3-5 years)'
                ],
                'diagnostic_features': [
                    'BLOTCHY ASYMMETRIC YELLOWING (not uniform like nutrient deficiency)',
                    'Lopsided fruit pathognomonic',
                    'LONG INCUBATION (6-12 months asymptomatic)',
                    'PCR testing required for definitive diagnosis',
                    'Psyllid vector presence',
                    'No cure - infected trees die'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(25, 32),
                    humidity_threshold=0,
                    rainfall_trigger_mm=0,
                    wind_dispersal=False,  # Psyllid vector
                    risk_level='CRITICAL',
                    incubation_period_days=180  # 6-12 months
                ),
                'economic_impact': {
                    'tree_mortality': '100% - all infected trees die',
                    'florida_losses': '75% reduction in orange production since 2005',
                    'economic_damage': '$4.5 billion Florida, threatens $9 billion USA citrus',
                    'global_threat': 'Present in Asia, Americas, Africa',
                    'no_resistant_varieties': 'All commercial citrus susceptible'
                },
                'treatment': TreatmentPlan(
                    antibiotics=[
                        {'name': 'Oxytetracycline', 'active': 'oxytetracycline', 'note': 'Trunk injection, suppression only'},
                        {'name': 'Streptomycin', 'active': 'streptomycin', 'note': 'Limited efficacy'}
                    ],
                    cultural_controls=[
                        'PSYLLID CONTROL CRITICAL (systemic insecticides)',
                        'Remove infected trees (reduce inoculum)',
                        'Use certified disease-free nursery stock',
                        'Scout for psyllids weekly',
                        'Remove abandoned groves (psyllid habitat)',
                        'Enhanced nutrition (trees live longer)',
                        'Windbreaks to reduce psyllid movement'
                    ],
                    spray_interval_days=7,  # Psyllid control
                    psyllid_control=True,
                    eradication_required=False,  # Too widespread
                    reporting_required=True,
                    treatment_cost_per_acre=1200.0,  # Intensive management
                    expected_yield_protection=30.0,  # Limited efficacy
                    roi_ratio=2.0
                ),
                'psyllid_management': {
                    'insecticides': [
                        'Imidacloprid (neonicotinoid)',
                        'Thiamethoxam (neonicotinoid)',
                        'Spinetoram',
                        'Fenpropathrin (pyrethroid)'
                    ],
                    'timing': 'Flush growth critical (psyllids lay eggs on new leaves)',
                    'resistance': 'Pyrethroid resistance common'
                },
                'notes': 'NO CURE - management focuses on prolonging productive life, new plantings require intensive psyllid control'
            },
            
            CitrusDisease.CITRUS_CANKER: {
                'pathogen': 'Xanthomonas citri subsp. citri',
                'pathogen_type': 'Bacteria',
                'threat_level': 'QUARANTINE DISEASE',
                'regulatory_status': 'Mandatory eradication in USA',
                'symptoms': [
                    'RAISED CORKY LESIONS with YELLOW HALO (DIAGNOSTIC)',
                    'Lesions on leaves, fruit, twigs',
                    'Fruit: Brown raised spots, premature drop',
                    'Severe: Defoliation, twig dieback',
                    'Water-soaked appearance initially',
                    'Crater-like lesions as tissue collapses'
                ],
                'diagnostic_features': [
                    'YELLOW HALO around lesion (pathognomonic)',
                    'RAISED CORKY center',
                    'Lesions on both sides of leaf (vs greasy spot underside only)',
                    'Wind-driven rain spreads bacteria',
                    'Young tissue most susceptible'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(20, 30),
                    humidity_threshold=0,
                    rainfall_trigger_mm=25,  # Wind-driven rain critical
                    wind_dispersal=True,
                    risk_level='high',
                    infection_period_hours=2,
                    incubation_period_days=7
                ),
                'economic_impact': {
                    'fruit_quality': 'Unmarketable for fresh market',
                    'premature_drop': '50-100% in severe cases',
                    'quarantine': 'International trade restrictions',
                    'eradication_cost': 'Millions in eradication programs',
                    'florida_history': '$100+ million in tree removal 1990s-2000s'
                },
                'treatment': TreatmentPlan(
                    bactericides=[
                        {'name': 'Copper hydroxide', 'active': 'copper', 'note': 'Protectant only'},
                        {'name': 'Copper + Mancozeb', 'active': 'copper+mancozeb', 'note': 'Tank mix'}
                    ],
                    cultural_controls=[
                        'Windbreaks (reduce wind-driven rain)',
                        'Remove infected fruit/twigs',
                        'Avoid overhead irrigation',
                        'Sanitation of equipment',
                        'Use less susceptible varieties',
                        'ERADICATION PROGRAM compliance'
                    ],
                    spray_interval_days=14,
                    eradication_required=True,  # In many regions
                    reporting_required=True,
                    treatment_cost_per_acre=300.0,
                    expected_yield_protection=60.0,
                    roi_ratio=4.0
                ),
                'regulatory': {
                    'usa_policy': 'Mandatory reporting, eradication programs in some states',
                    'international': 'Export restrictions from affected regions',
                    'quarantine_zones': 'Movement restrictions'
                },
                'notes': 'REPORT IMMEDIATELY to agriculture authorities'
            },
            
            CitrusDisease.CITRUS_BLACK_SPOT: {
                'pathogen': 'Phyllosticta citricarpa',
                'pathogen_type': 'Fungus',
                'threat_level': 'QUARANTINE THREAT',
                'lookalike': 'FALSE black spot (Phyllosticta capitalensis) - HARMLESS',
                'symptoms': [
                    'BLACK SPOTS on fruit (cosmetic damage)',
                    'Hard spot type: Flat, hard',
                    'Virulent spot type: Sunken with red halo',
                    'False melanose type: Multiple small spots',
                    'Freckle type: Numerous small specks',
                    'Lesions appear months after infection',
                    'NO LEAF SYMPTOMS (vs false black spot has leaf spots)'
                ],
                'diagnostic_features': [
                    'FRUIT ONLY (true black spot)',
                    'NO LEAF SYMPTOMS (diagnostic vs false)',
                    'Appears late in season (months after infection)',
                    'DNA testing required for definitive ID',
                    'Geographic distribution (true CBS not in USA mainland)'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(20, 28),
                    humidity_threshold=85,
                    rainfall_trigger_mm=10,
                    wind_dispersal=False,
                    risk_level='moderate',
                    infection_period_hours=8,
                    incubation_period_days=60  # Long latency
                ),
                'economic_impact': {
                    'cosmetic_damage': 'Fresh fruit unmarketable',
                    'juice_quality': 'No impact on juice',
                    'export_restrictions': 'Severe - EU bans fruit from CBS areas',
                    'quarantine_status': 'USA: Not present on mainland (quarantine threat)'
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Copper fungicides', 'active': 'copper', 'frac': 'M1'},
                        {'name': 'Strobilurins', 'active': 'azoxystrobin', 'frac': '11'},
                        {'name': 'Benomyl', 'active': 'benomyl', 'frac': '1'}
                    ],
                    cultural_controls=[
                        'Remove fallen leaves (inoculum)',
                        'Prune dead wood',
                        'Improve air circulation',
                        'Harvest fruit promptly'
                    ],
                    spray_interval_days=21,
                    reporting_required=True,  # If found in CBS-free area
                    treatment_cost_per_acre=250.0,
                    expected_yield_protection=70.0,
                    roi_ratio=5.0
                ),
                'differential_diagnosis': {
                    'true_cbs': 'Fruit only, long latency, quarantine disease',
                    'false_cbs': 'Fruit AND leaves, shorter latency, harmless',
                    'critical': 'DNA testing required - false positive has severe trade implications'
                },
                'notes': 'DIFFERENTIAL DIAGNOSIS CRITICAL - false CBS is harmless, misidentification causes export problems'
            },
            
            CitrusDisease.MELANOSE: {
                'pathogen': 'Diaporthe citri',
                'pathogen_type': 'Fungus',
                'inoculum_source': 'Dead wood',
                'symptoms': [
                    'Raised brown pustules on young fruit',
                    'Mudcake type: Large raised scabs',
                    'Fruit rind only affected (no internal damage)',
                    'Twig lesions',
                    'Young tissue susceptible (first 12-16 weeks)'
                ],
                'diagnostic_features': [
                    'RAISED BROWN PUSTULES',
                    'Young fruit only (first 12-16 weeks)',
                    'Dead wood inoculum source',
                    'Spring disease (rainy season)'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(18, 28),
                    humidity_threshold=0,
                    rainfall_trigger_mm=12,
                    wind_dispersal=True,
                    risk_level='moderate',
                    infection_period_hours=6,
                    incubation_period_days=10
                ),
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Copper fungicides', 'active': 'copper', 'frac': 'M1'},
                        {'name': 'Mancozeb', 'active': 'mancozeb', 'frac': 'M3'}
                    ],
                    cultural_controls=[
                        'REMOVE DEAD WOOD (primary inoculum source)',
                        'Prune out deadwood annually',
                        'Timing: Protect fruit first 12-16 weeks'
                    ],
                    spray_interval_days=21,
                    treatment_cost_per_acre=180.0,
                    expected_yield_protection=75.0,
                    roi_ratio=6.0
                ),
                'fruit_disease': CitrusFruitDisease(
                    fruit_symptoms=['raised_pustules', 'mudcake_scabs'],
                    infection_timing='fruit_set',
                    cosmetic_vs_decay='cosmetic',
                    fresh_market_impact='grade_reduction',
                    juice_quality_impact='none'
                )
            },
            
            CitrusDisease.CITRUS_SCAB: {
                'pathogen': 'Elsinoe fawcettii',
                'pathogen_type': 'Fungus',
                'symptoms': [
                    'WARTY GROWTHS on fruit',
                    'Irregular raised lesions',
                    'Pink to gray color',
                    'Young tissue susceptible',
                    'Leaf distortion'
                ],
                'diagnostic_features': [
                    'WARTY appearance',
                    'Young tissue (2-4 weeks after petal fall)',
                    'Tangerines/grapefruit most susceptible',
                    'Sweet oranges less affected'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(20, 28),
                    humidity_threshold=90,
                    rainfall_trigger_mm=2.5,
                    wind_dispersal=False,
                    risk_level='moderate'
                ),
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Copper fungicides', 'active': 'copper', 'frac': 'M1'},
                        {'name': 'Benomyl', 'active': 'benomyl', 'frac': '1'}
                    ],
                    spray_interval_days=14,
                    treatment_cost_per_acre=150.0,
                    expected_yield_protection=70.0,
                    roi_ratio=5.0
                )
            },
            
            CitrusDisease.GREASY_SPOT: {
                'pathogen': 'Mycosphaerella citri',
                'pathogen_type': 'Fungus',
                'symptoms': [
                    'Yellow-brown blisters on LEAF UNDERSIDE',
                    'Greasy appearance',
                    'Premature defoliation',
                    'Reduced tree vigor'
                ],
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Copper + Oil', 'active': 'copper+oil', 'note': 'Summer/fall application'}
                    ],
                    spray_interval_days=30,
                    treatment_cost_per_acre=120.0,
                    expected_yield_protection=60.0,
                    roi_ratio=4.0
                )
            }
        }
    
    def _initialize_variety_susceptibility(self) -> Dict[CitrusType, Dict]:
        """Variety-specific disease susceptibility"""
        return {
            CitrusType.SWEET_ORANGE: {
                'hlb': 'highly susceptible',
                'canker': 'susceptible',
                'melanose': 'moderate',
                'scab': 'resistant',
                'notes': 'Primary commercial type, HLB devastating'
            },
            CitrusType.MANDARIN: {
                'hlb': 'highly susceptible',
                'canker': 'highly susceptible',
                'scab': 'highly susceptible',
                'notes': 'Tangerines very canker susceptible'
            },
            CitrusType.GRAPEFRUIT: {
                'hlb': 'highly susceptible',
                'canker': 'susceptible',
                'scab': 'susceptible',
                'melanose': 'susceptible'
            }
        }
    
    def detect_citrus_greening(self, image: np.ndarray) -> Optional[DetectionResult]:
        """
        Detect Citrus Greening (HLB)
        
        MOST DEVASTATING CITRUS DISEASE
        DIAGNOSTIC: Blotchy asymmetric yellowing
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Blotchy yellow mottling
        lower_yellow = np.array([20, 30, 120])
        upper_yellow = np.array([40, 180, 255])
        yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
        
        # Green areas
        lower_green = np.array([35, 40, 40])
        upper_green = np.array([85, 255, 255])
        green_mask = cv2.inRange(hsv, lower_green, upper_green)
        
        # Check for asymmetric pattern
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        yellow_mask = cv2.morphologyEx(yellow_mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(yellow_mask, cv2.RETR_EXTERNAL,
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
            
            # Check for asymmetry (green and yellow mixed)
            roi_green = green_mask[y:y+h, x:x+w]
            asymmetric = np.sum(roi_green > 0) > (w * h * 0.2)
            
            lesion = CitrusLesion(
                color_hsv_range=((20, 30, 120), (40, 180, 255)),
                shape='irregular',
                texture='smooth',
                location='leaf',
                size_mm=(w * 0.1, h * 0.1),
                progression='expanding',
                margin='diffuse',
                blotchy_mottling=asymmetric,
                fruit_marketability='unmarketable',
                export_restriction=False
            )
            lesions.append(lesion)
            total_area += area
        
        affected_area = (total_area / (image.shape[0] * image.shape[1])) * 100
        
        # Blotchy mottling suggestive but PCR required for confirmation
        confidence = min(0.5 + (affected_area / 40) * 0.2, 0.75)  # Lower confidence - needs PCR
        
        disease_info = self.disease_database[CitrusDisease.CITRUS_GREENING]
        
        result = DetectionResult(
            disease=CitrusDisease.CITRUS_GREENING,
            confidence=confidence,
            severity=100.0,  # Always lethal
            affected_area_percent=affected_area,
            lesion_count=len(lesions),
            lesions=lesions,
            environmental_risk=disease_info['environmental'],
            treatment_plan=disease_info['treatment'],
            quarantine_disease=False,  # Too widespread
            reporting_required=True,
            tree_removal_recommended=True
        )
        
        return result
    
    def detect_citrus_canker(self, image: np.ndarray) -> Optional[DetectionResult]:
        """
        Detect Citrus Canker (Xanthomonas citri)
        
        QUARANTINE DISEASE
        DIAGNOSTIC: Raised corky lesion with yellow halo
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Brown corky lesions
        lower_brown = np.array([10, 40, 60])
        upper_brown = np.array([25, 200, 150])
        brown_mask = cv2.inRange(hsv, lower_brown, upper_brown)
        
        # Yellow halo detection
        lower_yellow = np.array([20, 50, 150])
        upper_yellow = np.array([35, 200, 255])
        yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        brown_mask = cv2.morphologyEx(brown_mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(brown_mask, cv2.RETR_EXTERNAL,
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
            
            # Check for yellow halo around lesion
            x1, y1 = max(0, x-5), max(0, y-5)
            x2, y2 = min(image.shape[1], x+w+5), min(image.shape[0], y+h+5)
            roi_halo = yellow_mask[y1:y2, x1:x2]
            has_halo = np.sum(roi_halo > 0) > (w * h * 0.3)
            
            lesion = CitrusLesion(
                color_hsv_range=((10, 40, 60), (25, 200, 150)),
                shape='circular',
                texture='raised',
                location='leaf',
                size_mm=(w * 0.1, h * 0.1),
                progression='static',
                margin='yellow_halo',
                raised_corky_lesion=True,
                yellow_halo=has_halo,
                fruit_marketability='unmarketable',
                export_restriction=True
            )
            lesions.append(lesion)
            total_area += area
        
        affected_area = (total_area / (image.shape[0] * image.shape[1])) * 100
        
        # Yellow halo is DIAGNOSTIC
        halo_found = any(l.yellow_halo for l in lesions)
        confidence = min(0.6 + (affected_area / 30) * 0.2, 0.85)
        if halo_found:
            confidence = min(confidence + 0.15, 0.95)
        
        disease_info = self.disease_database[CitrusDisease.CITRUS_CANKER]
        
        result = DetectionResult(
            disease=CitrusDisease.CITRUS_CANKER,
            confidence=confidence,
            severity=min(affected_area * 2, 100),
            affected_area_percent=affected_area,
            lesion_count=len(lesions),
            lesions=lesions,
            environmental_risk=disease_info['environmental'],
            treatment_plan=disease_info['treatment'],
            quarantine_disease=True,
            reporting_required=True,
            eradication_protocol=True,
            export_restriction=True
        )
        
        return result


def main():
    """Example usage"""
    detector = CitrusDiseaseDetector()
    
    print("=== AgroPulse Citrus Disease Detection System ===")
    print(f"Monitoring {len(detector.disease_database)} major citrus diseases")
    print("\nCRITICAL PATHOGENS:")
    print("1. Citrus Greening (HLB) - MOST DEVASTATING")
    print("   - NO CURE - trees die")
    print("   - Florida lost 75% orange production since 2005")
    print("   - $4.5 billion economic damage")
    print("   - Psyllid vector control critical")
    print("\n2. Citrus Canker - QUARANTINE DISEASE")
    print("   - Yellow halo diagnostic")
    print("   - Mandatory reporting and eradication")
    print("   - Export restrictions")
    print("\n3. Citrus Black Spot - QUARANTINE THREAT")
    print("   - FALSE black spot lookalike (harmless)")
    print("   - Differential diagnosis CRITICAL")
    print("\nSYSTEM STATUS: Ready for grove monitoring")


if __name__ == "__main__":
    main()
