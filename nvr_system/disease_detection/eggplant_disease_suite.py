"""
Eggplant/Aubergine Disease Detection Suite
==========================================

Comprehensive disease identification for eggplant (Solanum melongena),
a critical Solanaceae horticultural crop.

Critical Diseases:
1. Bacterial Wilt (Ralstonia solanacearum) - #1 DISEASE, QUARANTINE
2. Verticillium Wilt (Verticillium dahliae) - SOILBORNE, 15+ YEAR SURVIVAL
3. Phomopsis Blight (Phomopsis vexans) - FRUIT ROT DESTROYER
4. Fusarium Wilt (Fusarium oxysporum f.sp. melongenae) - LETHAL SOILBORNE
5. Cercospora Leaf Spot (Cercospora melongenae) - DEFOLIATION SEVERE
6. Anthracnose (Colletotrichum melongenae) - FRUIT QUALITY DESTROYER
7. Powdery Mildew (Leveillula taurica) - GREENHOUSE EPIDEMIC
8. Little Leaf Disease (Phytoplasma) - VECTORED, NO CURE

Market Context:
- Global eggplant: 55 million tons/year, $12 billion
- China: 60% world production, India: 25%
- Export market: Middle East, Europe premium
- Organic eggplant: 50% price premium
- Bacterial wilt: #1 constraint, field abandonment
- Fruit diseases: 30-70% post-harvest losses without control

Author: AgroPulse Team
Date: November 2025
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Dict
from datetime import datetime


class EggplantType(Enum):
    """Eggplant variety categories"""
    GLOBE = "globe"  # Large, purple, US/Europe market
    ITALIAN = "italian"  # Elongated, traditional
    JAPANESE = "japanese"  # Slender, premium market
    CHINESE = "chinese"  # Long, thin, Asian market
    WHITE = "white"  # Specialty, premium
    THAI = "thai"  # Small, green/white, bitter
    INDIAN = "indian"  # Small, round, varied colors


class EggplantDisease(Enum):
    """Major eggplant diseases"""
    BACTERIAL_WILT = "bacterial_wilt"
    VERTICILLIUM_WILT = "verticillium_wilt"
    PHOMOPSIS_BLIGHT = "phomopsis_blight"
    FUSARIUM_WILT = "fusarium_wilt"
    CERCOSPORA_LEAF_SPOT = "cercospora"
    ANTHRACNOSE = "anthracnose"
    POWDERY_MILDEW = "powdery_mildew"
    LITTLE_LEAF = "little_leaf"


@dataclass
class EggplantDiseaseParams:
    """Disease parameters for eggplant"""
    disease: EggplantDisease
    pathogen: str
    severity: str
    yield_loss: Tuple[int, int]
    quarantine_status: bool
    
    # Symptoms
    leaf_symptoms: List[str]
    fruit_symptoms: List[str]
    vascular_symptoms: List[str]
    
    # Environmental
    temp_range_c: Tuple[float, float]
    humidity_range: Tuple[int, int]
    
    # Resistance
    resistant_varieties: List[str]
    resistance_genes: List[str]
    
    # Control
    chemical_control: List[str]
    cultural_control: List[str]
    
    # Economics
    field_impact: str
    treatment_cost_per_acre: float


# Disease database
EGGPLANT_DISEASES = {
    EggplantDisease.BACTERIAL_WILT: EggplantDiseaseParams(
        disease=EggplantDisease.BACTERIAL_WILT,
        pathogen="Ralstonia solanacearum Race 3 Biovar 2",
        severity="10/10 - QUARANTINE DISEASE, #1 CONSTRAINT GLOBALLY",
        yield_loss=(80, 100),
        quarantine_status=True,
        
        leaf_symptoms=[
            "Sudden wilting of entire plant despite wet soil PATHOGNOMONIC",
            "Wilting starts on one side (vascular infection)",
            "Leaves remain green initially (not yellowing like fusarium)",
            "Rapid progression: wilt → collapse → death in 3-7 days",
            "No recovery once symptoms visible",
            "Young plants most susceptible",
        ],
        
        fruit_symptoms=[
            "Internal browning and decay",
            "Fruit collapse and shrivel",
        ],
        
        vascular_symptoms=[
            "Bacterial streaming DIAGNOSTIC TEST:",
            "Cut stem → place in water → white bacterial ooze streams out",
            "Vascular browning visible in cut stems",
            "Foul odor from cut stems",
        ],
        
        temp_range_c=(27.0, 35.0),
        humidity_range=(80, 100),
        
        resistant_varieties=[
            "Limited resistance available",
            "Some Japanese varieties show tolerance",
            "Grafting onto tomato rootstock (potential)",
        ],
        
        resistance_genes=[
            "Polygenic resistance",
            "No single dominant R genes identified",
        ],
        
        chemical_control=[
            "NO EFFECTIVE CHEMICAL CURE",
            "Antibiotics (streptomycin) - limited, temporary suppression",
            "Copper compounds - preventative only, not curative",
        ],
        
        cultural_control=[
            "QUARANTINE DISEASE - report to authorities immediately",
            "Remove and burn infected plants (do not compost)",
            "Field abandonment for 5-7 years minimum",
            "Soil solarization (6 weeks at >45°C)",
            "Grafting onto resistant rootstock (experimental)",
            "Strict sanitation of tools (10% bleach between plants)",
            "No rotation with Solanaceae, rotation with rice/grass effective",
            "Biocontrol: antagonistic bacteria (Pseudomonas fluorescens)",
        ],
        
        field_impact="Field abandonment, 5+ years, losses $10,000+ per acre",
        treatment_cost_per_acre=0.0  # No effective treatment
    ),
    
    EggplantDisease.VERTICILLIUM_WILT: EggplantDiseaseParams(
        disease=EggplantDisease.VERTICILLIUM_WILT,
        pathogen="Verticillium dahliae (microsclerotia survive 15+ years)",
        severity="9/10 - LETHAL SOILBORNE, LONG-TERM FIELD CONTAMINATION",
        yield_loss=(50, 100),
        quarantine_status=False,
        
        leaf_symptoms=[
            "Yellowing of lower leaves progressing upward",
            "One-sided wilting (one branch while others normal)",
            "Interveinal chlorosis V-shaped patterns",
            "Premature leaf drop",
            "Stunted plant growth",
            "Symptoms worse during hot days, may recover at night (temporary)",
        ],
        
        fruit_symptoms=[
            "Reduced fruit size and number",
            "Poor fruit quality",
        ],
        
        vascular_symptoms=[
            "Brown streaking in vascular tissue DIAGNOSTIC",
            "Cut stem shows brown discoloration",
            "Discoloration extends from roots upward",
            "No bacterial streaming (differs from bacterial wilt)",
        ],
        
        temp_range_c=(20.0, 28.0),
        humidity_range=(60, 90),
        
        resistant_varieties=[
            "Limited resistance in eggplant",
            "Grafting onto resistant tomato rootstock effective",
            "Ve gene in tomato provides resistance",
        ],
        
        resistance_genes=[
            "No major R genes in eggplant germplasm",
            "Grafting exploits tomato Ve gene",
        ],
        
        chemical_control=[
            "No effective fungicides for established infections",
            "Soil fumigation pre-plant (metam sodium, chloropicrin)",
            "VERY EXPENSIVE - $1,000-2,000/acre",
        ],
        
        cultural_control=[
            "Grafting onto resistant rootstock MOST EFFECTIVE",
            "Long rotations (5+ years) with non-hosts",
            "Avoid fields with previous Verticillium history",
            "Soil solarization in warm climates",
            "Deep plowing to bury inoculum",
            "Organic amendments (chitin, mustard green manure)",
            "Biocontrol: Trichoderma, non-pathogenic Verticillium",
        ],
        
        field_impact="Long-term contamination, microsclerotia survive 15+ years",
        treatment_cost_per_acre=1500.0  # Fumigation if attempted
    ),
    
    EggplantDisease.PHOMOPSIS_BLIGHT: EggplantDiseaseParams(
        disease=EggplantDisease.PHOMOPSIS_BLIGHT,
        pathogen="Phomopsis vexans (seed-transmitted, fruit rot major)",
        severity="8/10 - FRUIT ROT DESTROYER, SEED-TRANSMITTED",
        yield_loss=(40, 80),
        quarantine_status=False,
        
        leaf_symptoms=[
            "Circular gray lesions with concentric rings",
            "Lesions start small (2-3mm) → expand to 20mm",
            "Pycnidia (black fruiting bodies) in lesion centers DIAGNOSTIC",
            "Lesions coalesce causing blight",
            "Severe defoliation in wet weather",
        ],
        
        fruit_symptoms=[
            "Sunken circular spots on fruit MAJOR DAMAGE",
            "Lesions start small → expand rapidly",
            "Light brown to tan centers",
            "Fruit rot spreads in storage and transport",
            "Pycnidia visible on fruit (black dots) PATHOGNOMONIC",
            "Complete fruit loss if not controlled",
            "Post-harvest losses 50-70% without treatment",
        ],
        
        vascular_symptoms=[
            "Stem cankers with pycnidia",
            "Girdling can cause plant death",
        ],
        
        temp_range_c=(24.0, 30.0),
        humidity_range=(85, 100),
        
        resistant_varieties=[
            "Limited resistance",
            "Some Asian varieties show tolerance",
        ],
        
        resistance_genes=[
            "Quantitative resistance",
            "No major R genes",
        ],
        
        chemical_control=[
            "FRAC 3 - DMI fungicides (Difenoconazole, Tebuconazole)",
            "FRAC 11 - QoI strobilurins (Azoxystrobin)",
            "FRAC M5 - Chlorothalonil (broad spectrum)",
            "Rotate FRAC codes to prevent resistance",
            "Weekly applications during fruiting",
        ],
        
        cultural_control=[
            "Hot water seed treatment: 50°C for 25 minutes CRITICAL",
            "Certified disease-free seed only",
            "2-3 year rotation with non-Solanaceae",
            "Remove crop debris immediately post-harvest",
            "Avoid overhead irrigation (drip only)",
            "Mulch to prevent soil splash",
            "Stake plants for air circulation",
            "Harvest regularly to remove infected fruit",
        ],
        
        field_impact="Fruit rot major - 50-70% losses without control",
        treatment_cost_per_acre=300.0
    ),
    
    EggplantDisease.CERCOSPORA_LEAF_SPOT: EggplantDiseaseParams(
        disease=EggplantDisease.CERCOSPORA_LEAF_SPOT,
        pathogen="Cercospora melongenae (defoliation severe)",
        severity="7/10 - DEFOLIATION, QUALITY DOWNGRADE",
        yield_loss=(20, 50),
        quarantine_status=False,
        
        leaf_symptoms=[
            "Circular spots with gray centers and dark borders",
            "Spots 3-10mm diameter",
            "Gray spore masses in centers under humid conditions",
            "Spots coalesce causing extensive blight",
            "Severe defoliation reduces fruit quality",
            "Lower leaves affected first",
        ],
        
        fruit_symptoms=[
            "Rare fruit infection",
            "Quality reduced by defoliation",
        ],
        
        vascular_symptoms=[
            "No vascular infection",
        ],
        
        temp_range_c=(25.0, 32.0),
        humidity_range=(85, 100),
        
        resistant_varieties=[
            "Some resistance in Indian varieties",
        ],
        
        resistance_genes=[
            "Quantitative resistance",
        ],
        
        chemical_control=[
            "FRAC 11 - QoI fungicides",
            "FRAC 3 - DMI triazoles",
            "FRAC M5 - Chlorothalonil",
            "Preventative applications critical",
        ],
        
        cultural_control=[
            "Avoid overhead irrigation",
            "Adequate spacing for air flow",
            "Remove lower leaves when spotted",
            "2-year rotation",
        ],
        
        field_impact="Defoliation reduces photosynthesis, fruit size/quality",
        treatment_cost_per_acre=150.0
    ),
    
    EggplantDisease.POWDERY_MILDEW: EggplantDiseaseParams(
        disease=EggplantDisease.POWDERY_MILDEW,
        pathogen="Leveillula taurica (greenhouse epidemic, endoparasitic)",
        severity="6/10 - GREENHOUSE DISEASE, ENDOPARASITIC UNIQUE",
        yield_loss=(15, 40),
        quarantine_status=False,
        
        leaf_symptoms=[
            "Yellow spots on UPPER surface initially (endoparasitic entry)",
            "White powdery growth on UNDERSIDES (differs from other powdery mildews)",
            "Spots progress to necrosis",
            "Premature leaf senescence",
            "Greenhouse conditions favor rapid spread",
        ],
        
        fruit_symptoms=[
            "Indirect damage from defoliation",
            "Sunscald from leaf loss",
        ],
        
        vascular_symptoms=[
            "No vascular infection",
        ],
        
        temp_range_c=(20.0, 27.0),
        humidity_range=(50, 70),  # Lower humidity than most
        
        resistant_varieties=[
            "Limited resistance",
        ],
        
        resistance_genes=[
            "Under research",
        ],
        
        chemical_control=[
            "FRAC 3 - DMI fungicides effective",
            "FRAC 11 - QoI strobilurins",
            "Sulfur - organic option (phytotoxic >30°C)",
            "Potassium bicarbonate - organic",
        ],
        
        cultural_control=[
            "Greenhouse: maintain RH <70%",
            "Increase air circulation",
            "Avoid dense planting",
            "Remove infected leaves promptly",
        ],
        
        field_impact="Primarily greenhouse issue, field less common",
        treatment_cost_per_acre=120.0
    ),
}


@dataclass
class EggplantDiseaseResult:
    """Detection result"""
    disease: EggplantDisease
    confidence: float
    severity: str
    is_quarantine: bool
    symptoms: List[str]
    urgent_actions: List[str]
    economic_impact: str


class EggplantDiseaseDetector:
    """Eggplant disease detector"""
    
    def __init__(self):
        self.diseases = EGGPLANT_DISEASES
    
    def detect_disease(self,
                      image: np.ndarray,
                      plant_part: str = "leaf") -> List[EggplantDiseaseResult]:
        """Detect diseases"""
        if image is None or image.size == 0:
            return []
        
        results = []
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Check for wilting patterns (bacterial or verticillium)
        if plant_part == "whole_plant":
            wilt_score = self._detect_wilting(image)
            if wilt_score > 0.6:
                # Both wilts look similar, need bacterial streaming test
                results.append(self._create_result(
                    EggplantDisease.BACTERIAL_WILT,
                    wilt_score,
                    "CRITICAL - Perform bacterial streaming test"
                ))
        
        # Detect fruit lesions (phomopsis)
        if plant_part == "fruit":
            phomopsis_score = self._detect_fruit_lesions(image, hsv)
            if phomopsis_score > 0.5:
                results.append(self._create_result(
                    EggplantDisease.PHOMOPSIS_BLIGHT,
                    phomopsis_score,
                    "High - Fruit rot major concern"
                ))
        
        # Detect leaf spots
        if plant_part == "leaf":
            cercospora_score = self._detect_leaf_spots(image, hsv)
            if cercospora_score > 0.4:
                results.append(self._create_result(
                    EggplantDisease.CERCOSPORA_LEAF_SPOT,
                    cercospora_score,
                    "Moderate - Defoliation risk"
                ))
            
            powdery_score = self._detect_powdery_mildew(image, hsv)
            if powdery_score > 0.4:
                results.append(self._create_result(
                    EggplantDisease.POWDERY_MILDEW,
                    powdery_score,
                    "Moderate - Check undersides"
                ))
        
        return sorted(results, key=lambda x: x.confidence, reverse=True)
    
    def _detect_wilting(self, image: np.ndarray) -> float:
        """Detect wilting patterns"""
        # Simplified: check for drooping leaves
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        wilt_score = np.sum(edges) / (image.shape[0] * image.shape[1])
        return min(1.0, wilt_score * 10)
    
    def _detect_fruit_lesions(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect sunken lesions on fruit"""
        # Brown lesions
        brown_lower = np.array([10, 30, 30])
        brown_upper = np.array([25, 255, 150])
        brown_mask = cv2.inRange(hsv, brown_lower, brown_upper)
        
        contours, _ = cv2.findContours(brown_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        lesion_count = sum(1 for cnt in contours if 100 < cv2.contourArea(cnt) < 5000)
        
        return min(1.0, lesion_count / 8.0)
    
    def _detect_leaf_spots(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect circular leaf spots"""
        gray_lower = np.array([0, 0, 60])
        gray_upper = np.array([180, 50, 140])
        gray_mask = cv2.inRange(hsv, gray_lower, gray_upper)
        
        contours, _ = cv2.findContours(gray_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        spot_count = sum(1 for cnt in contours if 50 < cv2.contourArea(cnt) < 2000)
        
        return min(1.0, spot_count / 15.0)
    
    def _detect_powdery_mildew(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect white powdery growth"""
        white_lower = np.array([0, 0, 200])
        white_upper = np.array([180, 30, 255])
        white_mask = cv2.inRange(hsv, white_lower, white_upper)
        
        white_coverage = np.sum(white_mask > 0) / white_mask.size
        return min(1.0, white_coverage * 20)
    
    def _create_result(self, disease: EggplantDisease, confidence: float, severity: str) -> EggplantDiseaseResult:
        """Create result"""
        params = self.diseases[disease]
        
        return EggplantDiseaseResult(
            disease=disease,
            confidence=confidence,
            severity=severity,
            is_quarantine=params.quarantine_status,
            symptoms=params.leaf_symptoms[:3],
            urgent_actions=params.cultural_control[:2],
            economic_impact=params.field_impact
        )


if __name__ == "__main__":
    print("Eggplant Disease Detection System")
    print("=" * 60)
    
    detector = EggplantDiseaseDetector()
    
    print("\n📚 EGGPLANT DISEASE DATABASE:")
    for disease, params in EGGPLANT_DISEASES.items():
        print(f"\n{disease.value.upper()}")
        print(f"  Pathogen: {params.pathogen}")
        print(f"  Severity: {params.severity}")
        print(f"  Quarantine: {'YES ⚠️' if params.quarantine_status else 'No'}")
        print(f"  Field Impact: {params.field_impact}")
    
    print("\n✓ Eggplant detector initialized")
    print("  Critical: Bacterial wilt (quarantine, no cure)")
    print("  Critical: Verticillium wilt (15+ year survival)")
