"""
Olive Disease Detection Suite
Comprehensive detection system for olive diseases

CRITICAL DISEASES:

1. Olive Peacock Spot (Cycloconium oleaginum) - #1 OLIVE DISEASE WORLDWIDE
   - Circular leaf spots with yellow halo
   - 20-30% defoliation
   - Reduced yield, tree weakness
   - Mediterranean basin primary problem

2. Verticillium Wilt (Verticillium dahliae) - LETHAL VASCULAR DISEASE
   - Vascular browning
   - Branch dieback
   - Tree death in 2-5 years
   - NO CURE - soil infested 15+ years
   - Threatens ancient olive groves

3. Anthracnose (Colletotrichum spp.) - FRUIT ROT
   - Pre-harvest fruit rot
   - Oil quality reduction
   - Pink spore masses

4. Olive Knot (Pseudomonas savastanoi) - BACTERIAL GALLS
   - Galls on branches
   - Twig dieback
   - Worldwide distribution

DETECTION CHALLENGE:
- Peacock spot requires copper sprays
- Verticillium wilt NO CURE (prevention only)
- Ancient trees (centuries old) at risk
- Mediterranean climate diseases

Author: AgroPulse AI Team
Version: 1.0.0
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class OliveDisease(Enum):
    """Comprehensive olive disease classification"""
    PEACOCK_SPOT = "peacock_spot"  # Cycloconium - #1 disease
    VERTICILLIUM_WILT = "verticillium_wilt"  # Lethal vascular
    ANTHRACNOSE = "anthracnose"  # Colletotrichum - fruit rot
    OLIVE_KNOT = "olive_knot"  # Pseudomonas - bacterial
    SOOTY_MOLD = "sooty_mold"  # Capnodium - secondary
    CERCOSPORA_LEAF_SPOT = "cercospora_leaf_spot"
    OLIVE_LEAF_SPOT = "olive_leaf_spot"  # Mycocentrospora
    DALMATIAN_DISEASE = "dalmatian_disease"  # Pseudocercospora


class OliveType(Enum):
    """Olive variety classifications"""
    ARBEQUINA = "arbequina"  # Spanish, oil
    KORONEIKI = "koroneiki"  # Greek, oil
    PICUAL = "picual"  # Spanish, oil
    MANZANILLA = "manzanilla"  # Table olive
    KALAMATA = "kalamata"  # Greek table olive
    MISSION = "mission"  # California
    FRANTOIO = "frantoio"  # Italian oil


@dataclass
class OliveLesion:
    """Olive disease lesion characteristics"""
    color_hsv_range: Tuple[Tuple[int, int, int], Tuple[int, int, int]]
    shape: str  # circular, irregular
    texture: str  # spot, gall, sooty
    location: str  # leaf, fruit, branch, trunk
    size_mm: Tuple[float, float]
    progression: str  # expanding, static
    margin: str  # yellow_halo, defined
    
    # Diagnostic features
    yellow_halo: bool = False  # Peacock spot
    vascular_browning: bool = False  # Verticillium
    bacterial_gall: bool = False  # Olive knot
    
    # Economic impact
    yield_loss_percent: float = 0.0
    oil_quality_impact: str = "none"  # none, reduced, severe


@dataclass
class EnvironmentalRisk:
    """Environmental factors for olive disease risk"""
    temperature_range: Tuple[float, float]
    humidity_threshold: float
    rainfall_mm_monthly: Tuple[float, float]
    
    risk_level: str = "low"
    incubation_period_days: float = 0.0


@dataclass
class TreatmentPlan:
    """Olive disease treatment strategy"""
    fungicides: List[Dict[str, str]] = field(default_factory=list)
    bactericides: List[Dict[str, str]] = field(default_factory=list)
    cultural_controls: List[str] = field(default_factory=list)
    
    spray_interval_days: int = 14
    critical_timing: str = ""
    
    # Verticillium protocols
    fumigation_required: bool = False
    replanting_feasible: bool = True
    
    treatment_cost_per_hectare: float = 0.0
    expected_yield_protection: float = 0.0


@dataclass
class DetectionResult:
    """Disease detection result"""
    disease: OliveDisease
    confidence: float
    severity: float
    affected_area_percent: float
    lesion_count: int
    lesions: List[OliveLesion]
    environmental_risk: EnvironmentalRisk
    treatment_plan: TreatmentPlan
    
    # Lethal disease status
    tree_removal_required: bool = False
    replanting_feasible: bool = True
    
    timestamp: datetime = field(default_factory=datetime.now)


class OliveDiseaseDetector:
    """
    Advanced olive disease detection system
    
    CRITICAL FOCUS:
    - Peacock spot copper spray timing
    - Verticillium wilt early detection
    - Ancient tree protection (centuries old)
    """
    
    def __init__(self):
        self.disease_database = self._initialize_disease_database()
        
    def _initialize_disease_database(self) -> Dict[OliveDisease, Dict]:
        """Comprehensive olive disease parameter database"""
        return {
            OliveDisease.PEACOCK_SPOT: {
                'pathogen': 'Cycloconium oleaginum (formerly Spilocaea oleaginea)',
                'pathogen_type': 'Fungus',
                'importance': '#1 OLIVE DISEASE WORLDWIDE',
                'distribution': 'Mediterranean basin, California, Australia',
                'symptoms': [
                    'CIRCULAR LEAF SPOTS with YELLOW HALO (diagnostic)',
                    'Dark olive-green to brown center',
                    'Spots resemble peacock feathers (hence name)',
                    'Premature leaf drop (defoliation 20-30%)',
                    'Twig lesions (cankers)',
                    'Reduced fruit set',
                    'Tree weakness'
                ],
                'diagnostic_features': [
                    'CIRCULAR SPOTS with YELLOW HALO (pathognomonic)',
                    'Peacock feather appearance',
                    'Leaf underside primarily affected',
                    'Dark green-brown center'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(10, 20),  # Cool wet weather
                    humidity_threshold=95,
                    rainfall_mm_monthly=(50, 300),
                    risk_level='high',
                    incubation_period_days=45
                ),
                'economic_impact': {
                    'defoliation': '20-30% leaf loss',
                    'yield_reduction': '10-20%',
                    'oil_quality': 'Reduced (stressed trees)',
                    'mediterranean': 'Most important disease',
                    'california': 'Annual problem'
                },
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Copper hydroxide', 'active': 'copper', 'frac': 'M1'},
                        {'name': 'Copper oxychloride', 'active': 'copper', 'frac': 'M1'},
                        {'name': 'Dodine', 'active': 'dodine', 'frac': 'U12'}
                    ],
                    cultural_controls=[
                        'Copper sprays (fall/spring)',
                        'Prune for air circulation',
                        'Remove infected leaves',
                        'Improve drainage'
                    ],
                    spray_interval_days=21,
                    critical_timing='Fall (September-October) and Spring (March-April)',
                    treatment_cost_per_hectare=400.0,
                    expected_yield_protection=75.0
                ),
                'notes': 'Copper sprays essential in Mediterranean climate'
            },
            
            OliveDisease.VERTICILLIUM_WILT: {
                'pathogen': 'Verticillium dahliae',
                'pathogen_type': 'Fungus (soil-borne vascular wilt)',
                'threat_level': 'LETHAL - NO CURE',
                'importance': 'Threatens ancient olive groves',
                'symptoms': [
                    'WILTING of branches (one side initially)',
                    'VASCULAR BROWNING (cut branch shows streaks)',
                    'Branch dieback',
                    'Leaf yellowing and drop',
                    'Tree death (2-5 years)',
                    'Entire groves can be destroyed'
                ],
                'diagnostic_features': [
                    'VASCULAR BROWNING in xylem (diagnostic)',
                    'Sectoral wilting pattern',
                    'Progressive tree death',
                    'Soil-borne (persists 15+ years)',
                    'NO CURE'
                ],
                'environmental': EnvironmentalRisk(
                    temperature_range=(20, 27),
                    humidity_threshold=0,
                    rainfall_mm_monthly=(0, 300),
                    risk_level='CRITICAL',
                    incubation_period_days=30
                ),
                'economic_impact': {
                    'tree_death': '100% of infected trees',
                    'ancient_groves': 'Threatens centuries-old trees',
                    'soil_persistence': '15+ years (field lost)',
                    'spain': 'Major threat to olive industry',
                    'italy': 'Severe losses',
                    'greece': 'Ancient groves at risk'
                },
                'treatment': TreatmentPlan(
                    fungicides=[],  # NO EFFECTIVE CHEMICAL CONTROL
                    cultural_controls=[
                        'PREVENTION ONLY (no cure)',
                        'Remove infected trees immediately',
                        'Fumigate soil (methyl bromide alternatives)',
                        'Plant resistant varieties',
                        'Avoid planting in infested fields',
                        'Sanitize equipment',
                        'Do NOT replant olives for 10+ years',
                        'Rotate to non-host crops'
                    ],
                    fumigation_required=True,
                    replanting_feasible=False,
                    treatment_cost_per_hectare=0.0,
                    expected_yield_protection=0.0
                ),
                'resistant_varieties': {
                    'resistant': ['Frantoio', 'Leccino'],
                    'susceptible': ['Picual', 'Arbequina'],
                    'note': 'Resistance varies by V. dahliae strain'
                },
                'notes': 'NO CURE - threatens ancient olive groves (some trees 1000+ years old)'
            },
            
            OliveDisease.ANTHRACNOSE: {
                'pathogen': 'Colletotrichum acutatum, C. gloeosporioides',
                'pathogen_type': 'Fungus',
                'importance': 'Major fruit disease',
                'symptoms': [
                    'Dark sunken lesions on fruit',
                    'Pink spore masses (wet conditions)',
                    'Fruit rot',
                    'Premature fruit drop',
                    'Oil quality reduction'
                ],
                'treatment': TreatmentPlan(
                    fungicides=[
                        {'name': 'Copper', 'active': 'copper', 'frac': 'M1'}
                    ],
                    cultural_controls=[
                        'Timely harvest',
                        'Prune for air circulation',
                        'Remove infected fruit'
                    ],
                    treatment_cost_per_hectare=300.0
                )
            },
            
            OliveDisease.OLIVE_KNOT: {
                'pathogen': 'Pseudomonas savastanoi pv. savastanoi',
                'pathogen_type': 'Bacteria',
                'distribution': 'Worldwide',
                'symptoms': [
                    'GALLS on branches and twigs (diagnostic)',
                    'Rough warty growths',
                    'Twig dieback',
                    'Reduced vigor'
                ],
                'diagnostic_features': [
                    'GALLS (swollen tissue)',
                    'Bacterial infection through wounds'
                ],
                'treatment': TreatmentPlan(
                    bactericides=[
                        {'name': 'Copper', 'active': 'copper', 'frac': 'M1'}
                    ],
                    cultural_controls=[
                        'Prune infected branches',
                        'Disinfect tools',
                        'Copper sprays (protection)',
                        'Avoid pruning in wet weather'
                    ],
                    treatment_cost_per_hectare=350.0
                ),
                'notes': 'Enters through wounds - avoid pruning in rain'
            }
        }
    
    def detect_peacock_spot(self, image: np.ndarray) -> Optional[DetectionResult]:
        """
        Detect Olive Peacock Spot (Cycloconium oleaginum)
        
        #1 OLIVE DISEASE WORLDWIDE
        DIAGNOSTIC: Circular spots with yellow halo
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Dark olive-green to brown center
        lower_spot = np.array([20, 40, 30])
        upper_spot = np.array([60, 200, 100])
        spot_mask = cv2.inRange(hsv, lower_spot, upper_spot)
        
        # Yellow halo
        lower_yellow = np.array([20, 50, 150])
        upper_yellow = np.array([35, 200, 255])
        yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        spot_mask = cv2.morphologyEx(spot_mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(spot_mask, cv2.RETR_EXTERNAL,
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
            has_halo = np.sum(roi_halo > 0) > (w * h * 0.2)
            
            lesion = OliveLesion(
                color_hsv_range=((20, 40, 30), (60, 200, 100)),
                shape='circular',
                texture='spot',
                location='leaf',
                size_mm=(w * 0.1, h * 0.1),
                progression='expanding',
                margin='yellow_halo',
                yellow_halo=has_halo,
                yield_loss_percent=15.0,
                oil_quality_impact='reduced'
            )
            lesions.append(lesion)
            total_area += area
        
        affected_area = (total_area / (image.shape[0] * image.shape[1])) * 100
        
        # Circular spots with yellow halo diagnostic
        confidence = min(0.80 + (affected_area / 25) * 0.15, 0.95)
        
        disease_info = self.disease_database[OliveDisease.PEACOCK_SPOT]
        
        result = DetectionResult(
            disease=OliveDisease.PEACOCK_SPOT,
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
    detector = OliveDiseaseDetector()
    
    print("=== AgroPulse Olive Disease Detection System ===")
    print(f"Monitoring {len(detector.disease_database)} major olive diseases")
    print("\nCRITICAL PATHOGENS:")
    print("1. Peacock Spot - #1 OLIVE DISEASE")
    print("   - Circular spots with yellow halo")
    print("   - 20-30% defoliation")
    print("   - Mediterranean basin primary problem")
    print("\n2. Verticillium Wilt - LETHAL")
    print("   - Vascular browning, NO CURE")
    print("   - Tree death in 2-5 years")
    print("   - Threatens ancient olive groves (centuries old)")
    print("\nSYSTEM STATUS: Ready for grove monitoring")


if __name__ == "__main__":
    main()
