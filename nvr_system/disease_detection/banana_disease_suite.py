"""
Banana Disease Detection Suite
Comprehensive detection system for banana diseases

CRITICAL DISEASES:

1. Panama Disease (Fusarium Wilt) - MOST DEVASTATING BANANA DISEASE
   - Tropical Race 4 (TR4) - "Banana AIDS"
   - Destroyed 'Gros Michel' industry 1950s (Race 1)
   - TR4 threatens 'Cavendish' (90% of exports)
   - NO CURE - soil remains infested 40+ years
   - Quarantine disease - eradication protocols
   - $400+ million annual losses

2. Black Sigatoka (Mycosphaerella fijiensis) - #1 FUNGAL THREAT
   - Replaced Yellow Sigatoka as dominant
   - 35-50% yield loss if untreated
   - Fungicide resistance widespread
   - $500 million annual fungicide costs
   - Weekly sprays required

3. Banana Bunchy Top Virus (BBTV) - APHID-TRANSMITTED
   - Entire plant stunted
   - Dark green streaks on petioles
   - NO CURE - remove infected plants
   - Aphid vector control

4. Banana Bacterial Wilt (Xanthomonas) - EAST AFRICAN EPIDEMIC
   - Destroyed plantations in Uganda, Rwanda
   - Yellow bacterial ooze
   - Insect and tool transmission
   - Eradication protocols

5. Moko Disease (Ralstonia solanacearum) - BACTERIAL WILT
   - Latin American threat
   - Vascular browning
   - Systemic infection
   - Quarantine disease

DETECTION CHALLENGE:
- Panama disease soil-borne (cannot see until wilting)
- Sigatoka requires early detection (exponential spread)
- BBTV vector control critical
- Multiple bacterial wilts (differential diagnosis)

Author: AgroPulse AI Team
Version: 1.0.0
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class BananaDisease(Enum):
    """Comprehensive banana disease classification"""
    PANAMA_DISEASE = "panama_disease"  # Fusarium TR4 - DEVASTATING
    BLACK_SIGATOKA = "black_sigatoka"  # Mycosphaerella fijiensis - #1 fungal
    YELLOW_SIGATOKA = "yellow_sigatoka"  # Mycosphaerella musicola
    BUNCHY_TOP_VIRUS = "bunchy_top_virus"  # BBTV - aphid vector
    BANANA_BACTERIAL_WILT = "banana_bacterial_wilt"  # Xanthomonas
    MOKO_DISEASE = "moko_disease"  # Ralstonia - bacterial wilt
    CROWN_ROT = "crown_rot"  # Post-harvest fungal complex
    FINGER_ROT = "finger_rot"  # Colletotrichum, Fusarium
    BANANA_STREAK_VIRUS = "banana_streak_virus"  # BSV
    BANANA_BRACT_MOSAIC_VIRUS = "banana_bract_mosaic_virus"  # BBrMV
    FRECKLE = "freckle"  # Guignardia/Phyllosticta
    CIGAR_END_ROT = "cigar_end_rot"  # Verticillium, Trachysphaera


class BananaType(Enum):
    """Banana variety classifications"""
    CAVENDISH = "cavendish"  # 90% of exports, TR4 susceptible
    GROS_MICHEL = "gros_michel"  # Destroyed by Race 1, superior flavor
    PLANTAIN = "plantain"  # Cooking banana
    LADY_FINGER = "lady_finger"  # Sweet, small
    RED_BANANA = "red_banana"  # Red skin
    BURRO = "burro"  # Square shape, lemony
    AAB_GROUP = "aab_group"  # Silk subgroup
    ABB_GROUP = "abb_group"  # Cooking types


@dataclass
class BananaLesion:
    """Banana disease lesion characteristics"""
    color_hsv_range: Tuple[Tuple[int, int, int], Tuple[int, int, int]]
    shape: str  # streak, spot, circular, elongated
    texture: str  # necrotic, water_soaked, dry, sunken
    location: str  # leaf, pseudostem, fruit, root
    size_mm: Tuple[float, float]
    progression: str  # expanding, static, coalescing
    margin: str  # defined, diffuse, yellow_halo
    
    # Diagnostic features
    black_streaks: bool = False  # Black Sigatoka
    yellow_wilting: bool = False  # Panama disease
    bacterial_ooze: bool = False  # Bacterial wilts
    bunchy_growth: bool = False  # BBTV
    vascular_browning: bool = False  # Wilts
    
    # Economic impact
    yield_loss_percent: float = 0.0
    fruit_quality_impact: str = "none"  # none, blemish, unmarketable


@dataclass
class BananaFruitDisease:
    """Fruit-specific disease parameters"""
    fruit_symptoms: List[str]
    infection_timing: str  # field, harvest, post_harvest
    marketability: str  # export_grade, local_market, processing, loss
    shelf_life_impact: str  # none, reduced, severe


@dataclass
class EnvironmentalRisk:
    """Environmental factors for banana disease risk"""
    temperature_range: Tuple[float, float]
    humidity_threshold: float
    rainfall_mm_monthly: Tuple[float, float]
    altitude_range: Tuple[float, float]
    
    risk_level: str = "low"
    infection_period_hours: float = 0.0
    incubation_period_days: float = 0.0


@dataclass
class TreatmentPlan:
    """Banana disease treatment strategy"""
    fungicides: List[Dict[str, str]] = field(default_factory=list)
    bactericides: List[Dict[str, str]] = field(default_factory=list)
    cultural_controls: List[str] = field(default_factory=list)
    
    spray_interval_days: int = 14
    resistance_management: str = ""
    
    # Critical protocols
    eradication_required: bool = False
    quarantine_protocols: bool = False
    
    treatment_cost_per_hectare: float = 0.0
    expected_yield_protection: float = 0.0
    roi_ratio: float = 0.0


@dataclass
class DetectionResult:
    """Disease detection result"""
    disease: BananaDisease
    confidence: float
    severity: float
    affected_area_percent: float
    lesion_count: int
    lesions: List[BananaLesion]
    environmental_risk: EnvironmentalRisk
    treatment_plan: TreatmentPlan
    
    # Quarantine status
    quarantine_disease: bool = False
    eradication_protocol: bool = False
    
    # Plantation impact
    plant_removal_required: bool = False
    replanting_feasible: bool = True
    
    timestamp: datetime = field(default_factory=datetime.now)


class BananaDiseaseDetector:
    """
    Advanced banana disease detection system
    
    CRITICAL FOCUS:
    - Panama disease TR4 early detection (quarantine)
    - Black Sigatoka spray timing
    - BBTV vector control
    - Bacterial wilt eradication protocols
    """
    
    def __init__(self):
        self.disease_database = self._initialize_disease_database()
        self.variety_resistance = self._initialize_variety_resistance()
        
    def _initialize_disease_database(self) -> Dict[BananaDisease, Dict]:
        """Comprehensive banana disease parameter database"""
        return {
            BananaDisease.PANAMA_DISEASE: {
                'pathogen': 'Fusarium oxysporum f.sp. cubense (Foc)',
                'pathogen_type': 'Fungus (soil-borne vascular wilt)',
                'races': {
                    'Race_1': 'Destroyed Gros Michel 1950s-1960s',
                    'Race_2': 'Cooking bananas',
                    'Tropical_Race_4': 'TR4 - threatens Cavendish (90% exports)'
                },
                'common_name': '"Banana AIDS" (no cure, spreads relentlessly)',
                'threat_level': 'MOST DEVASTATING BANANA DISEASE',
                'historical_impact': 'Destroyed Gros Michel industry, TR4 threatens $8B Cavendish trade',
                'symptoms': [
                    'YELLOWING of older leaves (starts at edges)',
                    'Leaves collapse at petiole',
                    'Splitting of pseudostem base',
                    'VASCULAR BROWNING (cut pseudostem shows brown streaks)',
                    'Plant death (no recovery)',
                    'Entire mat dies over time'
                ],
                'diagnostic_features': [
                    'VASCULAR BROWNING in pseudostem and rhizome (diagnostic)',
                    'Yellow wilting progresses to younger leaves',
                    'External symptoms late (internal infection weeks before)',
                    'Soil-borne (persists 40+ years)',
                    'Water, soil, equipment spread',
                    'NO CURE - infected plants die'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(24, 32),
                    humidity_threshold=0,
                    rainfall_mm_monthly=(100, 400),
                    altitude_range=(0, 1200),
                    risk_level='CRITICAL',
                    incubation_period_days=90  # Long latency
                ),
                'economic_impact': {
                    'yield_loss': '100% in infected fields',
                    'soil_persistence': '40+ years (field lost)',
                    'global_threat': 'Threatens $8 billion Cavendish export industry',
                    'annual_losses': '$400+ million',
                    'tr4_spread': 'Asia, Africa, Middle East, Australia, Latin America'
                },
                'treatment': TreatmentPlan(
                    fungicides=[],  # NO EFFECTIVE CHEMICAL CONTROL
                    cultural_controls=[
                        'QUARANTINE: Prevent introduction to farm',
                        'ERADICATION: Remove infected plants + surrounding mat',
                        'Sanitize equipment (5% formalin)',
                        'Restrict movement from infected areas',
                        'Use TR4-resistant varieties (limited options)',
                        'Soil solarization (limited efficacy)',
                        'Flood fallow (4-6 months)',
                        'Organic amendments (biological control)',
                        'Do NOT replant susceptible varieties'
                    ],
                    eradication_required=True,
                    quarantine_protocols=True,
                    treatment_cost_per_hectare=0.0,
                    expected_yield_protection=0.0,
                    roi_ratio=0.0
                ),
                'resistant_varieties': {
                    'cavendish': 'HIGHLY SUSCEPTIBLE to TR4',
                    'gros_michel': 'Susceptible to Race 1',
                    'resistant': [
                        'GCTCV-219 (Taiwan)',
                        'FHIA-01, FHIA-02, FHIA-03 (Honduras)',
                        'Some wild diploids'
                    ],
                    'trade_off': 'Resistant varieties often inferior flavor/yield'
                },
                'notes': 'NO CURE - quarantine and eradication ONLY effective measures, soil remains infested 40+ years'
            },
            
            BananaDisease.BLACK_SIGATOKA: {
                'pathogen': 'Pseudocercospora fijiensis (formerly Mycosphaerella fijiensis)',
                'pathogen_type': 'Fungus',
                'importance': '#1 FUNGAL DISEASE OF BANANA',
                'replaced': 'Yellow Sigatoka (more aggressive)',
                'symptoms': [
                    'Stage 1: Tiny yellow specks (barely visible)',
                    'Stage 2: Yellow streaks (2mm wide, parallel to veins)',
                    'Stage 3: Brown streaks (3-4mm wide)',
                    'Stage 4: BLACK SPOTS with yellow halo',
                    'Stage 5: Black spots with gray center (sporulating)',
                    'Stage 6: Spots coalesce, entire leaf dies',
                    'Severe: 50-100% defoliation'
                ],
                'diagnostic_features': [
                    'BLACK SPOTS with yellow halo (advanced stage)',
                    'STREAKS parallel to veins (early stages)',
                    'Sequential leaf necrosis (oldest to youngest)',
                    'More aggressive than Yellow Sigatoka',
                    'Spores on leaf underside'
                ],
                'lifecycle': {
                    'infection': 'Ascospores or conidia',
                    'incubation': '14-21 days (invisible)',
                    'sporulation': '21-35 days',
                    'cycles': 'Continuous (no sexual stage required)'
                },
                'environmental': EnvironmentalRisk(
                    temperature_range=(20, 28),
                    humidity_threshold=95,
                    rainfall_mm_monthly=(200, 500),
                    altitude_range=(0, 1800),
                    risk_level='high',
                    infection_period_hours=6,
                    incubation_period_days=18
                ),
                'economic_impact': {
                    'yield_loss': '35-50% if untreated',
                    'fruit_quality': 'Premature ripening, reduced weight',
                    'fungicide_cost': '$500 million annually (global)',
                    'spray_programs': '25-50 applications per year',
                    'resistance': 'QoI and DMI resistance widespread'
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Chlorothalonil', 'active': 'chlorothalonil', 'frac': 'M5'},
                        {'name': 'Mancozeb', 'active': 'mancozeb', 'frac': 'M3'},
                        {'name': 'Azoxystrobin', 'active': 'azoxystrobin', 'frac': '11'},
                        {'name': 'Difenoconazole', 'active': 'difenoconazole', 'frac': '3'},
                        {'name': 'Tebuconazole', 'active': 'tebuconazole', 'frac': '3'},
                        {'name': 'Pyraclostrobin', 'active': 'pyraclostrobin', 'frac': '11'}
                    ],
                    cultural_controls=[
                        'Leaf removal (reduce inoculum)',
                        'Improve drainage',
                        'Wider spacing (air circulation)',
                        'De-leafing at harvest',
                        'Use resistant varieties'
                    ],
                    spray_interval_days=7,  # INTENSIVE: Weekly sprays
                    resistance_management='CRITICAL: Rotate FRAC groups, QoI and DMI resistance widespread',
                    treatment_cost_per_hectare=2500.0,  # High fungicide cost
                    expected_yield_protection=85.0,
                    roi_ratio=4.5
                ),
                'spray_programs': {
                    'low_pressure': '15-20 applications/year',
                    'moderate_pressure': '25-35 applications/year',
                    'high_pressure': '40-52 applications/year (weekly)',
                    'method': 'Aerial or ground application with oil'
                },
                'resistance_crisis': {
                    'qoi_frac_11': 'Widespread resistance',
                    'dmi_frac_3': 'Resistance emerging',
                    'management': 'Multi-site protectants + tank mixes essential'
                },
                'notes': 'MOST EXPENSIVE DISEASE to control, weekly sprays required in high-pressure areas'
            },
            
            BananaDisease.BUNCHY_TOP_VIRUS: {
                'pathogen': 'Banana bunchy top virus (BBTV)',
                'pathogen_type': 'Virus (Babuvirus)',
                'vector': 'Banana aphid (Pentalonia nigronervosa)',
                'threat_level': 'LETHAL - NO CURE',
                'symptoms': [
                    'SEVERE STUNTING (bunchy appearance)',
                    'DARK GREEN STREAKS on petiole and midrib (diagnostic)',
                    'Narrow upright leaves (bunched)',
                    'Brittle leaves',
                    'No fruit production',
                    'Entire mat infected progressively'
                ],
                'diagnostic_features': [
                    'DARK GREEN STREAKS (dots/dashes) on petiole (pathognomonic)',
                    'BUNCHY TOP appearance',
                    'Severe stunting',
                    'Aphid vector present',
                    'PCR confirmation available'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(20, 30),
                    humidity_threshold=0,
                    rainfall_mm_monthly=(100, 400),
                    altitude_range=(0, 1200),
                    risk_level='high',
                    incubation_period_days=60
                ),
                'economic_impact': {
                    'yield_loss': '100% infected plants',
                    'spread': 'Entire plantation over 2-3 years',
                    'quarantine': 'Movement restrictions',
                    'australia_threat': 'Major constraint'
                },
                'treatment': TreatmentPlan(
                    cultural_controls=[
                        'REMOVE INFECTED PLANTS IMMEDIATELY (entire mat)',
                        'Aphid control (systemic insecticides)',
                        'Use virus-free planting material (tissue culture)',
                        'Scout regularly for symptoms',
                        'Quarantine infected areas',
                        'Border barrier crops'
                    ],
                    eradication_required=True,
                    treatment_cost_per_hectare=0.0,
                    expected_yield_protection=0.0,
                    roi_ratio=0.0
                ),
                'aphid_control': {
                    'insecticides': [
                        'Imidacloprid (systemic)',
                        'Thiamethoxam',
                        'Pymetrozine'
                    ],
                    'timing': 'Continuous in endemic areas',
                    'efficacy': 'Reduces spread but does not eliminate'
                },
                'notes': 'NO CURE - remove infected plants, control aphids, use clean planting material'
            },
            
            BananaDisease.BANANA_BACTERIAL_WILT: {
                'pathogen': 'Xanthomonas campestris pv. musacearum',
                'pathogen_type': 'Bacteria',
                'geographic': 'EAST AFRICAN EPIDEMIC',
                'historical': 'Destroyed plantations in Uganda, Rwanda, DR Congo 2000s',
                'symptoms': [
                    'Yellowing of youngest leaves first',
                    'Progressive wilting',
                    'YELLOW BACTERIAL OOZE from cut pseudostem',
                    'Premature fruit ripening (on plant)',
                    'Dry rot of fruit',
                    'Entire plant death'
                ],
                'diagnostic_features': [
                    'YELLOW BACTERIAL OOZE (diagnostic)',
                    'Youngest leaves wilt first (vs Panama oldest first)',
                    'Rapid progression (weeks)',
                    'Insect vectors (fruit flies, bees)',
                    'Tool transmission'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(20, 30),
                    humidity_threshold=80,
                    rainfall_mm_monthly=(100, 400),
                    altitude_range=(1000, 2000),
                    risk_level='CRITICAL',
                    incubation_period_days=14
                ),
                'economic_impact': {
                    'east_africa': 'Thousands of hectares destroyed',
                    'food_security': 'Major threat to food security',
                    'yield_loss': '100% in infected fields'
                },
                'treatment': TreatmentPlan(
                    cultural_controls=[
                        'REMOVE ENTIRE MAT immediately',
                        'De-budding male flowers (insect entry)',
                        'Disinfect tools (sodium hypochlorite 3%)',
                        'Do not walk through fields when wet',
                        'Control insect vectors',
                        'Use clean planting material',
                        'Quarantine infected farms'
                    ],
                    eradication_required=True,
                    quarantine_protocols=True,
                    treatment_cost_per_hectare=0.0,
                    expected_yield_protection=0.0,
                    roi_ratio=0.0
                ),
                'notes': 'ERADICATION ONLY - no chemical control, tool sanitation CRITICAL'
            },
            
            BananaDisease.MOKO_DISEASE: {
                'pathogen': 'Ralstonia solanacearum race 2',
                'pathogen_type': 'Bacteria (vascular wilt)',
                'geographic': 'Latin America',
                'symptoms': [
                    'Leaf yellowing and wilting',
                    'Vascular browning',
                    'Bacterial ooze from cut tissue',
                    'Fruit pulp rot (internal)',
                    'Plant death'
                ],
                'diagnostic_features': [
                    'Vascular browning',
                    'Bacterial streaming in water',
                    'Insect and tool transmission'
                ],
                'treatment': TreatmentPlan(
                    cultural_controls=[
                        'Eradicate infected plants',
                        'Disinfect tools',
                        'Insect control',
                        'Quarantine'
                    ],
                    eradication_required=True,
                    quarantine_protocols=True
                )
            },
            
            BananaDisease.CROWN_ROT: {
                'pathogen': 'Fungal complex (Colletotrichum, Fusarium, Botryodiplodia)',
                'pathogen_type': 'Fungus',
                'importance': '#1 POST-HARVEST DISEASE',
                'symptoms': [
                    'Black rot at crown (cut surface)',
                    'Spreads to fingers',
                    'Soft rot',
                    'Premature ripening'
                ],
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Thiabendazole', 'active': 'TBZ', 'application': 'Crown dip/spray'},
                        {'name': 'Prochloraz', 'active': 'prochloraz', 'application': 'Crown treatment'}
                    ],
                    cultural_controls=[
                        'Minimize crown injury at harvest',
                        'Rapid cooling',
                        'Proper post-harvest handling'
                    ],
                    treatment_cost_per_hectare=150.0
                ),
                'fruit_disease': BananaFruitDisease(
                    fruit_symptoms=['crown_rot', 'finger_rot'],
                    infection_timing='harvest',
                    marketability='export_grade',
                    shelf_life_impact='severe'
                )
            }
        }
    
    def _initialize_variety_resistance(self) -> Dict[BananaType, Dict]:
        """Variety-specific disease resistance"""
        return {
            BananaType.CAVENDISH: {
                'panama_tr4': 'HIGHLY SUSCEPTIBLE',
                'panama_race1': 'resistant',
                'black_sigatoka': 'susceptible',
                'bbtv': 'susceptible',
                'production': '90% of banana exports',
                'notes': 'TR4 threatens entire export industry'
            },
            BananaType.GROS_MICHEL: {
                'panama_race1': 'HIGHLY SUSCEPTIBLE (destroyed 1950s)',
                'panama_tr4': 'susceptible',
                'black_sigatoka': 'susceptible',
                'flavor': 'Superior to Cavendish',
                'notes': 'Commercially extinct due to Panama Race 1'
            },
            BananaType.PLANTAIN: {
                'panama_race2': 'susceptible',
                'black_sigatoka': 'highly susceptible',
                'use': 'Cooking banana',
                'importance': 'Staple food Africa/Latin America'
            }
        }
    
    def detect_panama_disease(self, image: np.ndarray) -> Optional[DetectionResult]:
        """
        Detect Panama Disease (Fusarium Wilt TR4)
        
        MOST DEVASTATING BANANA DISEASE
        DIAGNOSTIC: Yellow wilting + vascular browning
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Yellow wilting leaves
        lower_yellow = np.array([20, 30, 100])
        upper_yellow = np.array([40, 200, 255])
        yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
        
        # Brown vascular tissue (if pseudostem cross-section)
        lower_brown = np.array([10, 50, 40])
        upper_brown = np.array([25, 200, 120])
        brown_mask = cv2.inRange(hsv, lower_brown, upper_brown)
        
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
            if area < 500:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            
            # Check for vascular browning
            roi_brown = brown_mask[y:y+h, x:x+w]
            vascular_brown = np.sum(roi_brown > 0) > (w * h * 0.05)
            
            lesion = BananaLesion(
                color_hsv_range=((20, 30, 100), (40, 200, 255)),
                shape='irregular',
                texture='necrotic',
                location='leaf',
                size_mm=(w * 0.1, h * 0.1),
                progression='expanding',
                margin='diffuse',
                yellow_wilting=True,
                vascular_browning=vascular_brown,
                yield_loss_percent=100.0,
                fruit_quality_impact='unmarketable'
            )
            lesions.append(lesion)
            total_area += area
        
        affected_area = (total_area / (image.shape[0] * image.shape[1])) * 100
        
        # Symptoms suggestive but vascular browning confirms
        vascular_found = any(l.vascular_browning for l in lesions)
        confidence = min(0.5 + (affected_area / 40) * 0.2, 0.70)
        if vascular_found:
            confidence = min(confidence + 0.20, 0.90)
        
        disease_info = self.disease_database[BananaDisease.PANAMA_DISEASE]
        
        result = DetectionResult(
            disease=BananaDisease.PANAMA_DISEASE,
            confidence=confidence,
            severity=100.0,
            affected_area_percent=affected_area,
            lesion_count=len(lesions),
            lesions=lesions,
            environmental_risk=disease_info['environmental'],
            treatment_plan=disease_info['treatment'],
            quarantine_disease=True,
            eradication_protocol=True,
            plant_removal_required=True,
            replanting_feasible=False  # Soil infested 40+ years
        )
        
        return result
    
    def detect_black_sigatoka(self, image: np.ndarray) -> Optional[DetectionResult]:
        """
        Detect Black Sigatoka (Mycosphaerella fijiensis)
        
        #1 FUNGAL BANANA DISEASE
        DIAGNOSTIC: Black spots with yellow halo
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Black spots
        lower_black = np.array([0, 0, 0])
        upper_black = np.array([180, 255, 60])
        black_mask = cv2.inRange(hsv, lower_black, upper_black)
        
        # Yellow halo
        lower_yellow = np.array([20, 50, 150])
        upper_yellow = np.array([35, 200, 255])
        yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(black_mask, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) == 0:
            return None
        
        lesions = []
        total_area = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 50:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            
            # Check for yellow halo
            x1, y1 = max(0, x-3), max(0, y-3)
            x2, y2 = min(image.shape[1], x+w+3), min(image.shape[0], y+h+3)
            roi_halo = yellow_mask[y1:y2, x1:x2]
            has_halo = np.sum(roi_halo > 0) > (w * h * 0.3)
            
            lesion = BananaLesion(
                color_hsv_range=((0, 0, 0), (180, 255, 60)),
                shape='circular',
                texture='necrotic',
                location='leaf',
                size_mm=(w * 0.1, h * 0.1),
                progression='expanding',
                margin='yellow_halo',
                black_streaks=True,
                yield_loss_percent=40.0,
                fruit_quality_impact='blemish'
            )
            lesions.append(lesion)
            total_area += area
        
        affected_area = (total_area / (image.shape[0] * image.shape[1])) * 100
        
        # Black spots with yellow halo diagnostic
        confidence = min(0.7 + (affected_area / 30) * 0.2, 0.95)
        
        disease_info = self.disease_database[BananaDisease.BLACK_SIGATOKA]
        
        result = DetectionResult(
            disease=BananaDisease.BLACK_SIGATOKA,
            confidence=confidence,
            severity=min(affected_area * 2, 100),
            affected_area_percent=affected_area,
            lesion_count=len(lesions),
            lesions=lesions,
            environmental_risk=disease_info['environmental'],
            treatment_plan=disease_info['treatment']
        )
        
        return result


def main():
    """Example usage"""
    detector = BananaDiseaseDetector()
    
    print("=== AgroPulse Banana Disease Detection System ===")
    print(f"Monitoring {len(detector.disease_database)} major banana diseases")
    print("\nCRITICAL PATHOGENS:")
    print("1. Panama Disease TR4 - MOST DEVASTATING")
    print("   - Destroyed Gros Michel 1950s")
    print("   - Threatens Cavendish (90% exports)")
    print("   - NO CURE - soil infested 40+ years")
    print("\n2. Black Sigatoka - #1 FUNGAL THREAT")
    print("   - 35-50% yield loss")
    print("   - $500M annual fungicide costs")
    print("   - Weekly sprays required")
    print("\n3. Bunchy Top Virus - APHID-TRANSMITTED")
    print("   - Dark green streaks diagnostic")
    print("   - NO CURE - eradication only")
    print("\nSYSTEM STATUS: Ready for plantation monitoring")


if __name__ == "__main__":
    main()
