"""
Coffee Disease Detection Suite
Comprehensive detection system for coffee diseases

CRITICAL DISEASES:

1. Coffee Leaf Rust (Hemileia vastatrix) - #1 GLOBAL COFFEE THREAT
   - "La Roya" - The Rust
   - $1-2 billion annual losses globally
   - Destroyed Sri Lankan coffee industry 1870s
   - Central American epidemic 2012-2013 (lost $3.2 billion)
   - Orange powdery pustules on leaf underside
   - Can defoliate entire plantations
   - Arabica highly susceptible, Robusta resistant

2. Coffee Berry Disease (Colletotrichum kahawae) - AFRICAN ENDEMIC
   - 30-80% crop loss in East Africa
   - Attacks green berries only
   - Black sunken lesions
   - Mummified berries
   - Cool wet highlands disease

3. Coffee Wilt Disease (Fusarium xylarioides) - TRACHEOMYCOSIS
   - Vascular wilt (xylem-clogging)
   - Branch wilting, tree death
   - 50-100% yield loss
   - Spreads through root contact
   - NO CURE - infected trees die

4. American Leaf Spot (Mycena citricolor) - "OJO DE GALLO"
   - Eye of the rooster appearance
   - High altitude disease (>1200m)
   - Circular lesions with gray centers
   - Premature defoliation

DETECTION CHALLENGE:
- Rust early detection saves crop (spreads exponentially)
- Berry disease requires pre-infection sprays
- Wilt disease emergency eradication protocols
- High-value crop justifies intensive monitoring

Author: AgroPulse AI Team
Version: 1.0.0
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class CoffeeDisease(Enum):
    """Comprehensive coffee disease classification"""
    COFFEE_LEAF_RUST = "coffee_leaf_rust"  # Hemileia vastatrix - #1 THREAT
    COFFEE_BERRY_DISEASE = "coffee_berry_disease"  # Colletotrichum kahawae
    COFFEE_WILT_DISEASE = "coffee_wilt_disease"  # Fusarium xylarioides
    AMERICAN_LEAF_SPOT = "american_leaf_spot"  # Mycena citricolor - ojo de gallo
    BROWN_EYE_SPOT = "brown_eye_spot"  # Cercospora coffeicola
    PINK_DISEASE = "pink_disease"  # Corticium salmonicolor
    ROOT_ROT = "root_rot"  # Rosellinia bunodes
    THREAD_BLIGHT = "thread_blight"  # Pellicularia koleroga
    PHOMA_LEAF_SPOT = "phoma_leaf_spot"  # Phoma costarricensis
    BACTERIAL_BLIGHT = "bacterial_blight"  # Pseudomonas syringae


class CoffeeSpecies(Enum):
    """Coffee species classifications"""
    ARABICA = "arabica"  # Coffea arabica - 60% production, rust susceptible
    ROBUSTA = "robusta"  # Coffea canephora - 40% production, rust resistant
    LIBERICA = "liberica"  # Coffea liberica - minor production
    HYBRID = "hybrid"  # Arabica x Robusta crosses


@dataclass
class CoffeeLesion:
    """Coffee disease lesion characteristics"""
    color_hsv_range: Tuple[Tuple[int, int, int], Tuple[int, int, int]]
    shape: str  # circular, irregular, angular
    texture: str  # powdery, sunken, necrotic, velvety
    location: str  # leaf, berry, stem, root
    size_mm: Tuple[float, float]
    progression: str  # expanding, static, coalescing
    margin: str  # defined, diffuse, chlorotic_halo
    
    # Diagnostic features
    orange_rust_pustules: bool = False  # Coffee leaf rust
    black_berry_rot: bool = False  # Berry disease
    vascular_browning: bool = False  # Wilt disease
    bulls_eye_pattern: bool = False  # Ojo de gallo
    
    # Economic impact
    yield_loss_percent: float = 0.0
    defoliation_risk: str = "none"  # none, minor, moderate, severe, total
    bean_quality_impact: str = "none"  # none, minor, severe, unmarketable


@dataclass
class CoffeeBerryDisease:
    """Berry-specific disease parameters"""
    berry_stage_affected: List[str]  # green, ripening, ripe
    bean_damage: bool  # Internal bean affected
    grade_reduction: str  # specialty, commercial, defect
    cup_quality_impact: str  # none, off_flavors, unmarketable


@dataclass
class EnvironmentalRisk:
    """Environmental factors for coffee disease risk"""
    temperature_range: Tuple[float, float]
    humidity_threshold: float
    leaf_wetness_hours: float
    altitude_range: Tuple[float, float]  # meters above sea level
    rainfall_mm_annual: Tuple[float, float]
    
    risk_level: str = "low"
    infection_period_hours: float = 0.0
    incubation_period_days: float = 0.0


@dataclass
class TreatmentPlan:
    """Coffee disease treatment strategy"""
    fungicides: List[Dict[str, str]] = field(default_factory=list)
    bactericides: List[Dict[str, str]] = field(default_factory=list)
    cultural_controls: List[str] = field(default_factory=list)
    
    spray_interval_days: int = 14
    resistance_management: str = ""
    
    # Economic considerations
    treatment_cost_per_hectare: float = 0.0
    expected_yield_protection: float = 0.0
    roi_ratio: float = 0.0
    
    # Organic alternatives
    organic_options: List[str] = field(default_factory=list)


@dataclass
class DetectionResult:
    """Disease detection result"""
    disease: CoffeeDisease
    confidence: float
    severity: float
    affected_area_percent: float
    lesion_count: int
    lesions: List[CoffeeLesion]
    environmental_risk: EnvironmentalRisk
    treatment_plan: TreatmentPlan
    
    # Coffee-specific
    species_susceptibility: str = "unknown"
    defoliation_risk: str = "low"
    harvest_impact: str = "none"  # none, reduced_yield, quality_loss, total_loss
    
    # Emergency protocols
    epidemic_alert: bool = False  # Rust epidemic potential
    eradication_required: bool = False  # Wilt disease
    
    timestamp: datetime = field(default_factory=datetime.now)


class CoffeeDiseaseDetector:
    """
    Advanced coffee disease detection system
    
    CRITICAL FOCUS:
    - Coffee leaf rust early warning (epidemic prevention)
    - Berry disease pre-infection timing
    - Wilt disease emergency eradication
    - Species-specific resistance
    """
    
    def __init__(self):
        self.disease_database = self._initialize_disease_database()
        self.species_resistance = self._initialize_species_resistance()
        
    def _initialize_disease_database(self) -> Dict[CoffeeDisease, Dict]:
        """Comprehensive coffee disease parameter database"""
        return {
            CoffeeDisease.COFFEE_LEAF_RUST: {
                'pathogen': 'Hemileia vastatrix',
                'pathogen_type': 'Fungus (Basidiomycete rust)',
                'historical_significance': 'Destroyed Sri Lankan coffee industry 1870s',
                'recent_epidemic': 'Central America 2012-2013: $3.2 billion loss, 1.7M jobs lost',
                'global_threat': '#1 COFFEE DISEASE WORLDWIDE',
                'economic_loss': '$1-2 billion annually',
                'symptoms': [
                    'ORANGE POWDERY PUSTULES on leaf underside (DIAGNOSTIC)',
                    'Yellow-orange spots on leaf upper surface',
                    'Premature leaf drop (50-100% defoliation)',
                    'Reduced flowering and fruiting',
                    'Tree death in severe repeated infections',
                    'Reduced bean size and quality'
                ],
                'diagnostic_features': [
                    'ORANGE RUST PUSTULES (urediniospores) - pathognomonic',
                    'Underside of leaf primarily affected',
                    'Coffee-specific rust (only Coffea spp.)',
                    'Exponential spread under optimal conditions',
                    'Arabica highly susceptible, Robusta resistant'
                ],
                'lifecycle': {
                    'overwintering': 'Urediniospores on leaves, no alternate host',
                    'dispersal': 'Wind, rain splash, short distance',
                    'infection': 'Requires free water on leaf 2-6 hours',
                    'incubation': '30-45 days',
                    'sporulation_cycles': 'New pustules every 14-21 days'
                },
                'environmental': EnvironmentalRisk(
                    temperature_range=(21, 25),
                    humidity_threshold=85,
                    leaf_wetness_hours=2,
                    altitude_range=(600, 1800),  # meters
                    rainfall_mm_annual=(1500, 3000),
                    risk_level='CRITICAL',
                    infection_period_hours=2,
                    incubation_period_days=35
                ),
                'economic_impact': {
                    'yield_loss': '20-50% typical, 80-100% severe',
                    'defoliation': '50-100% leaf loss',
                    'tree_death': 'Repeated severe infections kill trees',
                    'bean_quality': 'Size reduced, quality degraded',
                    'global_cost': '$1-2 billion/year',
                    'epidemic_cost': 'Central America 2012-13: $3.2B, 1.7M jobs'
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Copper hydroxide', 'active': 'copper', 'frac': 'M1'},
                        {'name': 'Triadimefon', 'active': 'triadimefon', 'frac': '3'},
                        {'name': 'Tebuconazole', 'active': 'tebuconazole', 'frac': '3'},
                        {'name': 'Cyproconazole', 'active': 'cyproconazole', 'frac': '3'},
                        {'name': 'Azoxystrobin', 'active': 'azoxystrobin', 'frac': '11'}
                    ],
                    cultural_controls=[
                        'PLANT RESISTANT VARIETIES (most effective long-term)',
                        'Shade management (reduce humidity)',
                        'Proper spacing (air circulation)',
                        'Remove infected leaves (reduce inoculum)',
                        'Balanced nutrition (avoid excess N)',
                        'Weed control',
                        'Pruning to open canopy'
                    ],
                    spray_interval_days=21,  # 3-week cycles
                    resistance_management='Rotate FRAC groups, DMI resistance emerging',
                    treatment_cost_per_hectare=400.0,
                    expected_yield_protection=75.0,
                    roi_ratio=8.0,
                    organic_options=[
                        'Bordeaux mixture (copper)',
                        'Shade trees (reduce leaf wetness)',
                        'Resistant varieties',
                        'Biofungicides (limited efficacy)'
                    ]
                ),
                'resistant_varieties': {
                    'traditional': ['Robusta (Coffea canephora) - naturally resistant'],
                    'arabica_resistant': [
                        'Sarchimor lines (Timor Hybrid x Caturra)',
                        'Catimor (Timor Hybrid x Caturra)',
                        'Colombia variety',
                        'Castillo variety',
                        'Marsellesa variety',
                        'Centroamericano variety'
                    ],
                    'resistance_genes': 'SH1-SH9 genes from C. liberica (Timor Hybrid)',
                    'trade_offs': 'Some resistant varieties have lower cup quality'
                },
                'notes': 'EPIDEMIC DISEASE - early detection and rapid response critical'
            },
            
            CoffeeDisease.COFFEE_BERRY_DISEASE: {
                'pathogen': 'Colletotrichum kahawae',
                'pathogen_type': 'Fungus (Anthracnose)',
                'geographic_distribution': 'ENDEMIC TO AFRICA (Kenya, Ethiopia, Tanzania)',
                'threat_level': 'MAJOR AFRICAN COFFEE THREAT',
                'symptoms': [
                    'BLACK SUNKEN LESIONS on green berries',
                    'Berries mummify and remain on tree',
                    'Brown discoloration of beans',
                    'Premature berry drop',
                    'Only affects GREEN berries (expanding berries most susceptible)',
                    'No infection of ripe red berries'
                ],
                'diagnostic_features': [
                    'BLACK LESIONS on green berries only (diagnostic)',
                    'Mummified berries hang on tree',
                    'Cool wet highlands disease (1400-2100m)',
                    'Infection during flowering to 4-weeks post-flowering',
                    'African endemic (not in Americas, Asia)'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(15, 21),
                    humidity_threshold=90,
                    leaf_wetness_hours=6,
                    altitude_range=(1400, 2100),
                    rainfall_mm_annual=(1500, 2500),
                    risk_level='high',
                    infection_period_hours=6,
                    incubation_period_days=14
                ),
                'economic_impact': {
                    'yield_loss': '30-80% in susceptible varieties',
                    'bean_quality': 'Brown beans (defect)',
                    'african_importance': 'Major constraint in East African highlands',
                    'quarantine': 'Not present in Americas/Asia - quarantine threat'
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Copper oxychloride', 'active': 'copper', 'frac': 'M1'},
                        {'name': 'Chlorothalonil', 'active': 'chlorothalonil', 'frac': 'M5'},
                        {'name': 'Azoxystrobin', 'active': 'azoxystrobin', 'frac': '11'},
                        {'name': 'Trifloxystrobin', 'active': 'trifloxystrobin', 'frac': '11'}
                    ],
                    cultural_controls=[
                        'Use resistant varieties',
                        'Remove mummified berries (sanitation)',
                        'Prune to improve air circulation',
                        'Shade management',
                        'Timing: Spray before flowering through 4-weeks post'
                    ],
                    spray_interval_days=14,
                    resistance_management='Rotate FRAC groups',
                    treatment_cost_per_hectare=350.0,
                    expected_yield_protection=70.0,
                    roi_ratio=7.0
                ),
                'berry_disease': CoffeeBerryDisease(
                    berry_stage_affected=['green', 'expanding'],
                    bean_damage=True,
                    grade_reduction='defect',
                    cup_quality_impact='severe'
                ),
                'notes': 'PRE-FLOWERING sprays most critical'
            },
            
            CoffeeDisease.COFFEE_WILT_DISEASE: {
                'pathogen': 'Fusarium xylarioides',
                'pathogen_type': 'Fungus (Vascular wilt)',
                'threat_level': 'LETHAL - ERADICATION DISEASE',
                'symptoms': [
                    'Wilting of branches (one side of tree first)',
                    'Yellowing and wilting of leaves',
                    'Brown streaking in vascular tissue (xylem)',
                    'Progressive tree death',
                    'Blue-green discoloration of wood',
                    'Tree death in 6-12 months'
                ],
                'diagnostic_features': [
                    'VASCULAR BROWNING (cut stem shows brown streaks)',
                    'ONE-SIDED wilting initially',
                    'NO CURE - infected trees die',
                    'Spreads through root contact',
                    'Robusta more susceptible than Arabica',
                    'Soil-borne pathogen persists'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(20, 28),
                    humidity_threshold=80,
                    leaf_wetness_hours=0,
                    altitude_range=(800, 1800),
                    rainfall_mm_annual=(1200, 2000),
                    risk_level='CRITICAL'
                ),
                'economic_impact': {
                    'tree_loss': '100% infected trees die',
                    'yield_loss': '50-100% farm level',
                    'epidemic_history': 'Destroyed 60% Central Africa coffee 1940s-1950s',
                    'current_threat': 'Re-emerging in Uganda, DR Congo'
                },
                'treatment': TreatmentPlan(
                    fungicides=[],  # NO EFFECTIVE CHEMICAL CONTROL
                    cultural_controls=[
                        'EMERGENCY: Remove and burn infected trees IMMEDIATELY',
                        'Remove stumps and roots',
                        'Do not replant in same spot for 2-3 years',
                        'Trench around healthy trees (prevent root contact)',
                        'Use resistant varieties',
                        'Sanitize tools',
                        'Quarantine infected areas'
                    ],
                    spray_interval_days=0,
                    resistance_management='NO CURE - eradication only',
                    treatment_cost_per_hectare=0.0,
                    expected_yield_protection=0.0,
                    roi_ratio=0.0
                ),
                'notes': 'ERADICATION DISEASE - remove and burn infected trees immediately, quarantine farm'
            },
            
            CoffeeDisease.AMERICAN_LEAF_SPOT: {
                'pathogen': 'Mycena citricolor',
                'pathogen_type': 'Fungus (Basidiomycete)',
                'common_name': '"OJO DE GALLO" - Eye of the Rooster',
                'geographic_distribution': 'Central and South America',
                'symptoms': [
                    'CIRCULAR LESIONS with gray-white centers (eye-like)',
                    'Brown border around lesions',
                    'White fungal growth in center when humid',
                    'Lesions on leaves, berries, shoots',
                    'Premature defoliation',
                    'Berry drop'
                ],
                'diagnostic_features': [
                    'BULL\'S-EYE PATTERN - gray center, brown border',
                    'High altitude disease (>1200m)',
                    'Cool wet conditions',
                    'White mycelium in lesion center'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(16, 20),
                    humidity_threshold=90,
                    leaf_wetness_hours=12,
                    altitude_range=(1200, 2200),
                    rainfall_mm_annual=(2000, 3500),
                    risk_level='moderate',
                    infection_period_hours=12,
                    incubation_period_days=10
                ),
                'economic_impact': {
                    'yield_loss': '10-30% typical',
                    'defoliation': '20-40%',
                    'high_altitude_constraint': 'Major in cool highlands'
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Copper fungicides', 'active': 'copper', 'frac': 'M1'},
                        {'name': 'Chlorothalonil', 'active': 'chlorothalonil', 'frac': 'M5'}
                    ],
                    cultural_controls=[
                        'Shade management (reduce humidity)',
                        'Prune to improve air circulation',
                        'Remove infected leaves',
                        'Proper spacing'
                    ],
                    spray_interval_days=21,
                    treatment_cost_per_hectare=200.0,
                    expected_yield_protection=65.0,
                    roi_ratio=5.0
                )
            },
            
            CoffeeDisease.BROWN_EYE_SPOT: {
                'pathogen': 'Cercospora coffeicola',
                'pathogen_type': 'Fungus',
                'symptoms': [
                    'Circular brown lesions with light centers',
                    'Yellowing around lesions',
                    'Premature leaf drop',
                    'Berry lesions reduce quality'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(20, 28),
                    humidity_threshold=80,
                    leaf_wetness_hours=8,
                    altitude_range=(400, 1400),
                    rainfall_mm_annual=(1200, 2000),
                    risk_level='moderate'
                ),
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Copper fungicides', 'active': 'copper', 'frac': 'M1'},
                        {'name': 'Azoxystrobin', 'active': 'azoxystrobin', 'frac': '11'}
                    ],
                    cultural_controls=[
                        'Balanced nutrition (avoid nitrogen excess)',
                        'Shade trees',
                        'Sanitation'
                    ],
                    spray_interval_days=21,
                    treatment_cost_per_hectare=180.0,
                    expected_yield_protection=60.0,
                    roi_ratio=4.5
                )
            }
        }
    
    def _initialize_species_resistance(self) -> Dict[CoffeeSpecies, Dict]:
        """Species-specific disease resistance"""
        return {
            CoffeeSpecies.ARABICA: {
                'rust_resistance': 'HIGHLY SUSCEPTIBLE',
                'berry_disease': 'susceptible',
                'wilt': 'moderate resistance',
                'notes': 'Premium quality, disease vulnerable',
                'resistant_cultivars': [
                    'Sarchimor', 'Catimor', 'Colombia', 'Castillo'
                ]
            },
            CoffeeSpecies.ROBUSTA: {
                'rust_resistance': 'RESISTANT',
                'berry_disease': 'susceptible',
                'wilt': 'highly susceptible',
                'notes': 'Lower quality, rust resistant',
                'production': '40% global coffee'
            },
            CoffeeSpecies.HYBRID: {
                'rust_resistance': 'resistant (from Robusta)',
                'berry_disease': 'variable',
                'wilt': 'variable',
                'notes': 'Arabica quality + Robusta resistance',
                'examples': ['Timor Hybrid', 'Arabusta']
            }
        }
    
    def detect_coffee_leaf_rust(self, image: np.ndarray,
                               environmental_data: Dict) -> Optional[DetectionResult]:
        """
        Detect Coffee Leaf Rust (Hemileia vastatrix)
        
        #1 GLOBAL COFFEE THREAT
        DIAGNOSTIC: Orange powdery pustules on leaf underside
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Orange rust pustules
        lower_orange = np.array([5, 100, 120])
        upper_orange = np.array([25, 255, 255])
        orange_mask = cv2.inRange(hsv, lower_orange, upper_orange)
        
        # Yellow spots on upper surface
        lower_yellow = np.array([20, 50, 150])
        upper_yellow = np.array([35, 180, 255])
        yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
        
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
            if area < 50:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            
            lesion = CoffeeLesion(
                color_hsv_range=((5, 100, 120), (25, 255, 255)),
                shape='irregular',
                texture='powdery',
                location='leaf',
                size_mm=(w * 0.1, h * 0.1),
                progression='expanding',
                margin='diffuse',
                orange_rust_pustules=True,
                yield_loss_percent=40.0,
                defoliation_risk='severe',
                bean_quality_impact='severe'
            )
            lesions.append(lesion)
            total_area += area
        
        affected_area = (total_area / (image.shape[0] * image.shape[1])) * 100
        
        # Orange pustules are DIAGNOSTIC
        confidence = min(0.7 + (affected_area / 30) * 0.2, 0.95)
        
        # Check epidemic conditions
        temp = environmental_data.get('temperature', 22)
        humidity = environmental_data.get('humidity', 80)
        epidemic_conditions = (21 <= temp <= 25 and humidity >= 85)
        
        disease_info = self.disease_database[CoffeeDisease.COFFEE_LEAF_RUST]
        
        result = DetectionResult(
            disease=CoffeeDisease.COFFEE_LEAF_RUST,
            confidence=confidence,
            severity=min(affected_area * 2.5, 100),
            affected_area_percent=affected_area,
            lesion_count=len(lesions),
            lesions=lesions,
            environmental_risk=disease_info['environmental'],
            treatment_plan=disease_info['treatment'],
            species_susceptibility='Arabica highly susceptible',
            defoliation_risk='severe',
            harvest_impact='reduced_yield',
            epidemic_alert=epidemic_conditions
        )
        
        return result
    
    def detect_coffee_berry_disease(self, berry_image: np.ndarray) -> Optional[DetectionResult]:
        """
        Detect Coffee Berry Disease (Colletotrichum kahawae)
        
        AFRICAN ENDEMIC
        DIAGNOSTIC: Black sunken lesions on green berries
        """
        hsv = cv2.cvtColor(berry_image, cv2.COLOR_BGR2HSV)
        
        # Black lesions on green berries
        lower_black = np.array([0, 0, 0])
        upper_black = np.array([180, 255, 80])
        black_mask = cv2.inRange(hsv, lower_black, upper_black)
        
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
            if area < 100:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            
            lesion = CoffeeLesion(
                color_hsv_range=((0, 0, 0), (180, 255, 80)),
                shape='circular',
                texture='sunken',
                location='berry',
                size_mm=(w * 0.1, h * 0.1),
                progression='expanding',
                margin='defined',
                black_berry_rot=True,
                yield_loss_percent=60.0,
                bean_quality_impact='severe'
            )
            lesions.append(lesion)
            total_area += area
        
        affected_area = (total_area / (berry_image.shape[0] * berry_image.shape[1])) * 100
        confidence = min(0.7 + (len(lesions) / 5) * 0.2, 0.90)
        
        disease_info = self.disease_database[CoffeeDisease.COFFEE_BERRY_DISEASE]
        
        result = DetectionResult(
            disease=CoffeeDisease.COFFEE_BERRY_DISEASE,
            confidence=confidence,
            severity=min(affected_area * 2, 100),
            affected_area_percent=affected_area,
            lesion_count=len(lesions),
            lesions=lesions,
            environmental_risk=disease_info['environmental'],
            treatment_plan=disease_info['treatment'],
            harvest_impact='total_loss'
        )
        
        return result


def main():
    """Example usage"""
    detector = CoffeeDiseaseDetector()
    
    print("=== AgroPulse Coffee Disease Detection System ===")
    print(f"Monitoring {len(detector.disease_database)} major coffee diseases")
    print("\nCRITICAL PATHOGENS:")
    print("1. Coffee Leaf Rust - #1 GLOBAL THREAT")
    print("   - Destroyed Sri Lankan coffee 1870s")
    print("   - Central America epidemic 2012-13: $3.2B loss")
    print("   - Orange pustules diagnostic")
    print("\n2. Coffee Berry Disease - AFRICAN ENDEMIC")
    print("   - 30-80% crop loss")
    print("   - Green berries only")
    print("\n3. Coffee Wilt Disease - LETHAL")
    print("   - NO CURE - eradication only")
    print("   - 100% tree mortality")
    print("\nSYSTEM STATUS: Ready for plantation monitoring")


if __name__ == "__main__":
    main()
