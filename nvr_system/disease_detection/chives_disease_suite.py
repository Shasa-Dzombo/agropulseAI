"""
Chives Disease Detection Suite
===============================

Comprehensive disease identification for chives (Allium schoenoprasum), perennial
onion-family herb with rust epidemic and Botrytis postharvest challenges.

Chives Types:
- Common chives (A. schoenoprasum) - standard, purple flowers
- Garlic chives (A. tuberosum) - flat leaves, white flowers
- Giant Siberian chives - large, cold hardy

Critical Diseases:
1. Rust (Puccinia allii) - #1 DISEASE, ORANGE PUSTULES, EPIDEMIC
2. Botrytis Leaf Blight (Botrytis squamosa) - TIP DIEBACK
3. Downy Mildew (Peronospora destructor) - ONION PATHOGEN
4. Purple Blotch (Alternaria porri) - PURPLE LESIONS
5. White Rot (Sclerotium cepivorum) - SOILBORNE, 20+ YEARS
6. Fusarium Basal Rot - BULB/ROOT ROT
7. Stemphylium Leaf Blight - DEFOLIATION
8. Pink Root (Phoma terrestris) - ROOT DISCOLORATION

Market Intelligence:
- USA production: $20 million fresh, growing segment
- Fresh chives: $8-14/lb wholesale, $15-25/lb retail
- Freeze-dried chives: $40-80/lb
- Organic chives: 60% of premium market
- Perennial: 3-5 year stands, dividing every 3 years
- Succession cutting: Harvest every 3-4 weeks
- Allium family: Shares diseases with onion, garlic

Author: AgroPulse Team
Date: November 2025
"""

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


class ChivesType(Enum):
    """Chives variety categories"""
    COMMON = "common"  # A. schoenoprasum
    GARLIC = "garlic"  # A. tuberosum
    GIANT_SIBERIAN = "giant_siberian"


class ChivesDisease(Enum):
    """Major chives diseases"""
    RUST = "rust"
    BOTRYTIS_LEAF_BLIGHT = "botrytis"
    DOWNY_MILDEW = "downy_mildew"
    PURPLE_BLOTCH = "purple_blotch"
    WHITE_ROT = "white_rot"
    FUSARIUM_BASAL_ROT = "fusarium"
    STEMPHYLIUM_BLIGHT = "stemphylium"
    PINK_ROOT = "pink_root"


@dataclass
class ChivesDiseaseParams:
    """Disease parameters for chives"""
    disease: ChivesDisease
    pathogen: str
    severity: str
    yield_loss: Tuple[int, int]
    
    symptoms: List[str]
    diagnostic_features: str
    
    onion_family_cross_infection: str  # Shares diseases with onion/garlic
    cultural_control: List[str]
    fungicide_control: List[str]
    
    market_impact: str
    treatment_cost_per_acre: float


# Abbreviated database
CHIVES_DISEASES = {
    ChivesDisease.RUST: ChivesDiseaseParams(
        disease=ChivesDisease.RUST,
        pathogen="Puccinia allii (#1 CHIVES DISEASE, orange pustules)",
        severity="10/10 - #1 DISEASE, EPIDEMIC DEFOLIATION",
        yield_loss=(40, 80),
        
        symptoms=[
            "Orange-yellow pustules on leaves DIAGNOSTIC",
            "Pustules contain powdery orange spores",
            "Leaves yellow then brown",
            "Complete defoliation in severe cases",
            "Epidemic spread in humid conditions",
        ],
        
        diagnostic_features="Orange pustules on leaves, epidemic",
        
        onion_family_cross_infection="Cross-infects from onions, garlic, leeks",
        
        cultural_control=[
            "Separate from onion/garlic fields",
            "Remove infected leaves promptly",
            "Good air circulation",
            "Avoid overhead irrigation",
            "Fall cleanup",
        ],
        
        fungicide_control=[
            "FRAC 3: Tebuconazole, myclobutanil",
            "FRAC 11: Azoxystrobin",
            "7-14 day intervals",
            "Begin at first pustules",
        ],
        
        market_impact="CATASTROPHIC - #1 disease, 40-80% loss",
        treatment_cost_per_acre=250.0
    ),
    
    ChivesDisease.BOTRYTIS_LEAF_BLIGHT: ChivesDiseaseParams(
        disease=ChivesDisease.BOTRYTIS_LEAF_BLIGHT,
        pathogen="Botrytis squamosa (tip dieback, onion pathogen)",
        severity="9/10 - TIP DIEBACK, DEFOLIATION",
        yield_loss=(30, 60),
        
        symptoms=[
            "Leaf tip dieback DIAGNOSTIC",
            "White spots progress to tan blighted areas",
            "Premature leaf senescence",
            "Reduced harvest quality",
        ],
        
        diagnostic_features="Tip dieback, white spots, onion pathogen",
        
        onion_family_cross_infection="Primary onion pathogen, infects chives",
        
        cultural_control=[
            "Separate from onion fields",
            "Remove infected leaves",
            "Good air circulation",
            "Reduce humidity",
        ],
        
        fungicide_control=[
            "FRAC 7: Boscalid",
            "FRAC 9: Switch",
            "7-10 day intervals",
        ],
        
        market_impact="Tip dieback reduces harvest quality",
        treatment_cost_per_acre=200.0
    ),
    
    ChivesDisease.WHITE_ROT: ChivesDiseaseParams(
        disease=ChivesDisease.WHITE_ROT,
        pathogen="Sclerotium cepivorum (SOILBORNE, 20+ YEAR PERSISTENCE, QUARANTINE)",
        severity="10/10 - CATASTROPHIC, 20+ YEAR SOIL CONTAMINATION",
        yield_loss=(80, 100),
        
        symptoms=[
            "Yellowing and wilting",
            "White fluffy mycelium at bulb base DIAGNOSTIC",
            "Black sclerotia (1-2mm) in mycelium",
            "Complete plant death",
            "Soil remains contaminated 20+ years",
        ],
        
        diagnostic_features="White mycelium + black sclerotia at bulb base",
        
        onion_family_cross_infection="AFFECTS ALL ALLIUMS - never plant chives/onions/garlic in infested soil",
        
        cultural_control=[
            "🚨 AVOID INFESTED FIELDS (20+ year contamination)",
            "NEVER plant any Alliums in infested soil",
            "No effective control once established",
            "Quarantine disease in some regions",
        ],
        
        fungicide_control=[
            "NO EFFECTIVE FUNGICIDES",
            "Prevention only option",
        ],
        
        market_impact="CATASTROPHIC - field abandonment for all Alliums",
        treatment_cost_per_acre=500.0  # Field abandonment
    ),
}


class ChivesDiseaseDetector:
    """Chives disease detector - rust #1 epidemic, white rot catastrophic"""
    
    def __init__(self):
        self.diseases = CHIVES_DISEASES
    
    def detect_disease(self, image: np.ndarray) -> List:
        """Detect chives diseases (abbreviated)"""
        if image is None or image.size == 0:
            return []
        
        results = []
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Rust (orange pustules)
        rust_score = self._detect_orange_pustules(hsv)
        if rust_score > 0.3:
            results.append({"disease": "Rust", "confidence": rust_score})
        
        return results
    
    def _detect_orange_pustules(self, hsv: np.ndarray) -> float:
        """Detect orange pustules (rust)"""
        orange_lower = np.array([10, 100, 100])
        orange_upper = np.array([25, 255, 255])
        orange_mask = cv2.inRange(hsv, orange_lower, orange_upper)
        coverage = np.sum(orange_mask > 0) / orange_mask.size
        return min(1.0, coverage * 25)


if __name__ == "__main__":
    print("Chives Disease Detection System")
    print("=" * 70)
    print("\n🚨 CRITICAL DISEASES:")
    print("  1. Rust - #1 disease, orange pustules, 40-80% loss")
    print("  2. White Rot - CATASTROPHIC, 20+ year soil contamination")
    print("\n⚠️  ALLIUM FAMILY WARNING:")
    print("  Chives share diseases with onions, garlic, leeks")
    print("  White rot contaminates soil for ALL Alliums 20+ years")
    print("  Separate chives from onion/garlic fields")
    print("\n✓ Chives disease detection system initialized")
    print("  Market: $20M USA, fresh $8-14/lb, freeze-dried $40-80/lb")
