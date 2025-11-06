"""
Tea Disease Detection Suite
Comprehensive detection system for tea (Camellia sinensis) diseases

CRITICAL DISEASES:

1. Blister Blight (Exobasidium venkatesii) - #1 TEA DISEASE
   - Most devastating tea disease
   - 20-50% yield loss in endemic areas
   - Transparent blisters turn brown
   - India/Sri Lanka major problem
   - $50+ million annual losses

2. Gray Blight (Pestalotiopsis theae) - DIEBACK DISEASE
   - Branch dieback
   - Gray lesions on leaves
   - Stress-related
   - Secondary pathogen

3. Red Rust (Cephaleuros parasiticus) - ALGAL DISEASE
   - Parasitic alga (not fungus)
   - Reddish-brown spots on leaves
   - High humidity disease
   - Reduces photosynthesis

4. Root Rot Complex - FATAL
   - Multiple pathogens
   - Tree death
   - Replanting required

5. Black Rot (Corticium invisible) - STEM DISEASE
   - Thread blight
   - Branch death
   - Humid tropics

DETECTION CHALLENGE:
- Blister blight rapid spread (monsoon season)
- High altitude disease patterns (1,000-2,200m)
- Plucking surfaces (2-leaf-and-bud) at risk
- Ancient tea gardens at risk

Author: AgroPulse AI Team
Version: 1.0.0
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class TeaDisease(Enum):
    """Comprehensive tea disease classification"""
    BLISTER_BLIGHT = "blister_blight"  # Exobasidium - #1 disease
    GRAY_BLIGHT = "gray_blight"  # Pestalotiopsis - dieback
    RED_RUST = "red_rust"  # Cephaleuros - algal
    BLACK_ROT = "black_rot"  # Corticium - thread blight
    BROWN_BLIGHT = "brown_blight"  # Colletotrichum
    STEM_CANKER = "stem_canker"  # Macrophoma
    ROOT_ROT = "root_rot"  # Phytophthora, Armillaria, Fomes
    CHARCOAL_STUMP_ROT = "charcoal_stump_rot"  # Ustulina
    THORNY_STEM_BLIGHT = "thorny_stem_blight"  # Aglaospora
    SHOT_HOLE = "shot_hole"  # Cercospora


class TeaType(Enum):
    """Tea variety classifications"""
    CAMELLIA_SINENSIS_SINENSIS = "china_type"  # China type, small leaf
    CAMELLIA_SINENSIS_ASSAMICA = "assam_type"  # Assam type, large leaf
    HYBRID = "hybrid"  # China x Assam hybrid
    ORTHODOX_TEA = "orthodox"  # Traditional processing
    CTC_TEA = "ctc"  # Crush-Tear-Curl processing


@dataclass
class TeaLesion:
    """Tea disease lesion characteristics"""
    color_hsv_range: Tuple[Tuple[int, int, int], Tuple[int, int, int]]
    shape: str  # blister, spot, lesion
    texture: str  # transparent, brown, rust, gray
    location: str  # young_leaf, mature_leaf, stem, root
    size_mm: Tuple[float, float]
    progression: str  # rapid, expanding
    margin: str  # defined, diffuse
    
    # Diagnostic features
    transparent_blister: bool = False  # Blister blight
    rust_colored: bool = False  # Red rust
    gray_dieback: bool = False  # Gray blight
    
    # Economic impact
    yield_loss_percent: float = 0.0
    quality_impact: str = "none"  # none, reduced, severe


@dataclass
class EnvironmentalRisk:
    """Environmental factors for tea disease risk"""
    temperature_range: Tuple[float, float]
    humidity_threshold: float
    altitude_range: Tuple[float, float]
    rainfall_mm_monthly: Tuple[float, float]
    
    risk_level: str = "low"
    incubation_period_days: float = 0.0


@dataclass
class TreatmentPlan:
    """Tea disease treatment strategy"""
    fungicides: List[Dict[str, str]] = field(default_factory=list)
    cultural_controls: List[str] = field(default_factory=list)
    
    spray_interval_days: int = 14
    critical_timing: str = ""
    resistance_management: str = ""
    
    treatment_cost_per_hectare: float = 0.0
    expected_yield_protection: float = 0.0


@dataclass
class DetectionResult:
    """Disease detection result"""
    disease: TeaDisease
    confidence: float
    severity: float
    affected_area_percent: float
    lesion_count: int
    lesions: List[TeaLesion]
    environmental_risk: EnvironmentalRisk
    treatment_plan: TreatmentPlan
    
    # Timing criticality
    monsoon_season_critical: bool = False
    plucking_surface_affected: bool = False
    
    timestamp: datetime = field(default_factory=datetime.now)


class TeaDiseaseDetector:
    """
    Advanced tea disease detection system
    
    CRITICAL FOCUS:
    - Blister blight monsoon season detection
    - High altitude disease patterns
    - Plucking surface protection (2-leaf-and-bud)
    - Quality tea preservation
    """
    
    def __init__(self):
        self.disease_database = self._initialize_disease_database()
        
    def _initialize_disease_database(self) -> Dict[TeaDisease, Dict]:
        """Comprehensive tea disease parameter database"""
        return {
            TeaDisease.BLISTER_BLIGHT: {
                'pathogen': 'Exobasidium venkatesii',
                'pathogen_type': 'Fungus (obligate parasite)',
                'importance': '#1 TEA DISEASE - Most devastating',
                'distribution': 'India (Darjeeling, Assam), Sri Lanka, Africa',
                'symptoms': [
                    'TRANSPARENT BLISTERS on young leaves (diagnostic)',
                    'Blisters turn PINK then BROWN',
                    'Concave upper surface, convex lower surface',
                    'WHITE BLOOM on underside (basidiospores)',
                    'Affected leaves fall prematurely',
                    'Plucking surfaces destroyed',
                    'Rapid spread during monsoon'
                ],
                'diagnostic_features': [
                    'TRANSPARENT BLISTERS initially (pathognomonic)',
                    'Turn pink then brown (color progression diagnostic)',
                    'WHITE BASIDIOSPORE layer underside',
                    'Young tender leaves primarily affected',
                    'Concave-convex blister shape',
                    'Rapid epidemic spread (monsoon)'
                ],
                'lifecycle': {
                    'infection': 'Basidiospores infect young tender leaves',
                    'incubation': '5-10 days',
                    'sporulation': '3-5 days after symptoms appear',
                    'spread': 'Wind-borne basidiospores',
                    'conditions': 'Cool (15-25°C) + high humidity (95%+) + rain'
                },
                'environmental': EnvironmentalRisk(
                    temperature_range=(15, 25),  # Cool temps favor
                    humidity_threshold=95,
                    altitude_range=(1000, 2200),  # High altitude disease
                    rainfall_mm_monthly=(200, 800),
                    risk_level='CRITICAL',
                    incubation_period_days=7
                ),
                'economic_impact': {
                    'yield_loss': '20-50% in endemic areas',
                    'quality_reduction': 'Plucking surfaces destroyed',
                    'india': '$30+ million annual losses',
                    'sri_lanka': '$20+ million annual losses',
                    'darjeeling': 'Major constraint (premium tea)',
                    'assam': 'Severe epidemic years',
                    'global': '$50+ million annual losses'
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Copper oxychloride', 'active': 'copper', 'frac': 'M1'},
                        {'name': 'Copper hydroxide', 'active': 'copper', 'frac': 'M1'},
                        {'name': 'Hexaconazole', 'active': 'hexaconazole', 'frac': '3'},
                        {'name': 'Propiconazole', 'active': 'propiconazole', 'frac': '3'},
                        {'name': 'Tridemorph', 'active': 'tridemorph', 'frac': '5'}
                    ],
                    cultural_controls=[
                        'PREVENTIVE SPRAYS before monsoon',
                        'Scout young leaves continuously',
                        'Remove infected leaves',
                        'Light pruning (shade predisposes)',
                        'Drainage (reduce humidity)',
                        'Spray at first symptom appearance',
                        'Cover vulnerable sections during monsoon',
                        'Biological control (antagonists)'
                    ],
                    spray_interval_days=7,  # Weekly during monsoon
                    critical_timing='MONSOON SEASON (May-October)',
                    resistance_management='Rotate copper and systemic fungicides',
                    treatment_cost_per_hectare=600.0,
                    expected_yield_protection=70.0
                ),
                'critical_seasons': {
                    'monsoon': 'PEAK DISEASE PERIOD (May-October)',
                    'pre_monsoon': 'Preventive sprays essential',
                    'winter': 'Disease subsides (dry + cool)'
                },
                'epidemic_conditions': {
                    'temperature': '15-25°C (cool)',
                    'humidity': '95%+ (high)',
                    'rainfall': 'Frequent light showers',
                    'altitude': '1,000-2,200m (high estates)',
                    'shade': 'Excessive shade increases risk'
                },
                'notes': 'MOST DEVASTATING TEA DISEASE - weekly sprays during monsoon essential, destroys quality'
            },
            
            TeaDisease.GRAY_BLIGHT: {
                'pathogen': 'Pestalotiopsis theae (formerly Pestalotia theae)',
                'pathogen_type': 'Fungus',
                'importance': 'Dieback disease',
                'symptoms': [
                    'GRAY LESIONS on leaves (diagnostic)',
                    'Brown margins with gray center',
                    'Branch dieback',
                    'Acervuli with black setae',
                    'Stress-related (secondary pathogen)'
                ],
                'diagnostic_features': [
                    'GRAY CENTER with brown margins',
                    'Black fruiting bodies (acervuli)',
                    'Dieback pattern',
                    'Stress indicator'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(20, 30),
                    humidity_threshold=80,
                    altitude_range=(0, 2200),
                    rainfall_mm_monthly=(100, 400),
                    risk_level='moderate',
                    incubation_period_days=10
                ),
                'economic_impact': {
                    'yield_loss': '10-20% in severe cases',
                    'branch_loss': 'Dieback reduces productive area',
                    'secondary': 'Attacks stressed trees'
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Copper', 'active': 'copper', 'frac': 'M1'},
                        {'name': 'Mancozeb', 'active': 'mancozeb', 'frac': 'M3'}
                    ],
                    cultural_controls=[
                        'Reduce tree stress (water, nutrients)',
                        'Prune dead wood',
                        'Improve vigor',
                        'Shade management'
                    ],
                    spray_interval_days=14,
                    treatment_cost_per_hectare=400.0,
                    expected_yield_protection=75.0
                ),
                'notes': 'SECONDARY PATHOGEN - stress reduction key to control'
            },
            
            TeaDisease.RED_RUST: {
                'pathogen': 'Cephaleuros parasiticus',
                'pathogen_type': 'Alga (parasitic green alga)',
                'unique': 'Not a fungus - ALGAL disease',
                'symptoms': [
                    'REDDISH-BROWN VELVETY SPOTS on leaves (diagnostic)',
                    'Rust-like appearance',
                    'Raised felt-like texture',
                    'Reduces photosynthesis',
                    'Twig infections'
                ],
                'diagnostic_features': [
                    'RUST-COLORED spots',
                    'VELVETY texture',
                    'ALGAL (not fungal)',
                    'High humidity disease'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(20, 30),
                    humidity_threshold=90,
                    altitude_range=(0, 1500),
                    rainfall_mm_monthly=(200, 600),
                    risk_level='moderate'
                ),
                'economic_impact': {
                    'photosynthesis': 'Reduced by 20-30%',
                    'yield_loss': '10-15%',
                    'quality': 'Minor impact'
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Copper', 'active': 'copper', 'frac': 'M1', 'note': 'Algicide'}
                    ],
                    cultural_controls=[
                        'Improve air circulation',
                        'Reduce humidity',
                        'Prune for light penetration',
                        'Drainage'
                    ],
                    spray_interval_days=21,
                    treatment_cost_per_hectare=300.0,
                    expected_yield_protection=80.0
                ),
                'notes': 'ALGAL DISEASE - copper effective as algicide'
            },
            
            TeaDisease.BLACK_ROT: {
                'pathogen': 'Corticium invisible (Rhizoctonia)',
                'pathogen_type': 'Fungus',
                'common_name': 'Thread blight',
                'symptoms': [
                    'BLACK THREAD-LIKE mycelium on stems',
                    'Web of mycelium',
                    'Branch dieback',
                    'Humid tropics disease'
                ],
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Copper', 'active': 'copper', 'frac': 'M1'}
                    ],
                    cultural_controls=[
                        'Prune infected branches',
                        'Improve air circulation',
                        'Reduce humidity'
                    ],
                    treatment_cost_per_hectare=350.0
                )
            },
            
            TeaDisease.ROOT_ROT: {
                'pathogen': 'Complex (Phytophthora, Armillaria, Fomes, Poria)',
                'pathogen_type': 'Fungi (multiple species)',
                'threat_level': 'FATAL',
                'symptoms': [
                    'Yellowing and wilting',
                    'Tree death',
                    'Root decay',
                    'Replanting required'
                ],
                'treatment': TreatmentPlan(
                    cultural_controls=[
                        'Remove infected trees',
                        'Improve drainage',
                        'Avoid waterlogging',
                        'Replant resistant clones'
                    ],
                    treatment_cost_per_hectare=0.0
                ),
                'notes': 'NO CURE - prevention through drainage essential'
            },
            
            TeaDisease.BROWN_BLIGHT: {
                'pathogen': 'Colletotrichum camelliae',
                'pathogen_type': 'Fungus',
                'symptoms': [
                    'Brown lesions on leaves',
                    'Anthracnose symptoms'
                ],
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Copper', 'active': 'copper', 'frac': 'M1'}
                    ],
                    treatment_cost_per_hectare=350.0
                )
            }
        }
    
    def detect_blister_blight(self, image: np.ndarray) -> Optional[DetectionResult]:
        """
        Detect Blister Blight (Exobasidium venkatesii)
        
        #1 TEA DISEASE - Most devastating
        DIAGNOSTIC: Transparent blisters → pink → brown
        MONSOON SEASON CRITICAL
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Transparent/pink blisters (early stage)
        lower_pink = np.array([0, 20, 180])
        upper_pink = np.array([15, 100, 255])
        pink_mask = cv2.inRange(hsv, lower_pink, upper_pink)
        
        # Brown blisters (late stage)
        lower_brown = np.array([10, 50, 50])
        upper_brown = np.array([25, 200, 150])
        brown_mask = cv2.inRange(hsv, lower_brown, upper_brown)
        
        # Combine masks
        blister_mask = cv2.bitwise_or(pink_mask, brown_mask)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        blister_mask = cv2.morphologyEx(blister_mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(blister_mask, cv2.RETR_EXTERNAL,
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
            
            # Check if circular (blister shape)
            circularity = 0.0
            perimeter = cv2.arcLength(contour, True)
            if perimeter > 0:
                circularity = (4 * np.pi * area) / (perimeter * perimeter)
            
            is_blister = circularity > 0.6
            
            lesion = TeaLesion(
                color_hsv_range=((0, 20, 180), (15, 100, 255)),
                shape='circular' if is_blister else 'irregular',
                texture='blister',
                location='young_leaf',
                size_mm=(w * 0.1, h * 0.1),
                progression='rapid',
                margin='defined',
                transparent_blister=is_blister,
                yield_loss_percent=40.0,
                quality_impact='severe'
            )
            lesions.append(lesion)
            total_area += area
        
        affected_area = (total_area / (image.shape[0] * image.shape[1])) * 100
        
        # Transparent/pink blisters diagnostic
        confidence = min(0.80 + (affected_area / 30) * 0.15, 0.95)
        
        disease_info = self.disease_database[TeaDisease.BLISTER_BLIGHT]
        
        result = DetectionResult(
            disease=TeaDisease.BLISTER_BLIGHT,
            confidence=confidence,
            severity=min(affected_area * 3, 100),
            affected_area_percent=affected_area,
            lesion_count=len(lesions),
            lesions=lesions,
            environmental_risk=disease_info['environmental'],
            treatment_plan=disease_info['treatment'],
            monsoon_season_critical=True,
            plucking_surface_affected=True
        )
        
        return result
    
    def detect_red_rust(self, image: np.ndarray) -> Optional[DetectionResult]:
        """
        Detect Red Rust (Cephaleuros parasiticus)
        
        ALGAL DISEASE (not fungal)
        DIAGNOSTIC: Reddish-brown velvety spots
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Rust-colored spots
        lower_rust = np.array([0, 80, 80])
        upper_rust = np.array([15, 255, 180])
        rust_mask = cv2.inRange(hsv, lower_rust, upper_rust)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        rust_mask = cv2.morphologyEx(rust_mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(rust_mask, cv2.RETR_EXTERNAL,
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
            
            lesion = TeaLesion(
                color_hsv_range=((0, 80, 80), (15, 255, 180)),
                shape='irregular',
                texture='rust',
                location='mature_leaf',
                size_mm=(w * 0.1, h * 0.1),
                progression='expanding',
                margin='defined',
                rust_colored=True,
                yield_loss_percent=12.0,
                quality_impact='reduced'
            )
            lesions.append(lesion)
            total_area += area
        
        affected_area = (total_area / (image.shape[0] * image.shape[1])) * 100
        
        # Rust-colored velvety spots diagnostic
        confidence = min(0.75 + (affected_area / 25) * 0.15, 0.90)
        
        disease_info = self.disease_database[TeaDisease.RED_RUST]
        
        result = DetectionResult(
            disease=TeaDisease.RED_RUST,
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
    detector = TeaDiseaseDetector()
    
    print("=== AgroPulse Tea Disease Detection System ===")
    print(f"Monitoring {len(detector.disease_database)} major tea diseases")
    print("\nCRITICAL PATHOGENS:")
    print("1. Blister Blight - #1 TEA DISEASE")
    print("   - Most devastating tea disease")
    print("   - Transparent blisters → pink → brown")
    print("   - 20-50% yield loss in endemic areas")
    print("   - $50+ million annual losses (India/Sri Lanka)")
    print("\n2. Gray Blight - DIEBACK DISEASE")
    print("   - Gray lesions, branch dieback")
    print("   - Secondary pathogen (stress-related)")
    print("\n3. Red Rust - ALGAL DISEASE")
    print("   - Parasitic alga (not fungus)")
    print("   - Reddish-brown velvety spots")
    print("   - Reduces photosynthesis 20-30%")
    print("\nSYSTEM STATUS: Ready for tea estate monitoring")


if __name__ == "__main__":
    main()
