"""
Tarragon Disease Detection Suite
=================================

Comprehensive disease identification for tarragon (Artemisia dracunculus), premium
French culinary herb with rust epidemic and sterile propagation challenges.

Tarragon Types:
- French tarragon (A. dracunculus var. sativa) - TRUE TARRAGON, sterile, premium
- Russian tarragon (A. dracunculus var. inodora) - seed-grown, inferior flavor
- Mexican tarragon (Tagetes lucida) - different genus, substitute

Critical Diseases:
1. Rust (Puccinia tanaceti) - #1 DISEASE, EPIDEMIC, OVERWINTERS
2. Powdery Mildew (Erysiphe cichoracearum) - GREENHOUSE
3. Rhizoctonia Root Rot - DAMPING-OFF, CROWN ROT
4. Pythium Root Rot - WATERLOGGING
5. Fusarium Root Rot - POOR DRAINAGE
6. Alternaria Leaf Spot - DEFOLIATION
7. Botrytis Gray Mold - POSTHARVEST
8. Root Rot Complex - OVERWATERING

Market Intelligence:
- USA production: $15 million (specialty herb, limited volume)
- Fresh tarragon: $15-30/lb retail, $10-18/lb wholesale
- Dried tarragon: $40-80/lb (flavor degrades rapidly)
- Essential oil: $200-500/kg (estragole content)
- French tarragon ONLY sterile (vegetative propagation required)
- Russian tarragon inferior (seed-grown, poor flavor)
- Perennial: 3-5 year stands, dividing every 3-4 years
- Premium market: French restaurants, gourmet cooking

Author: AgroPulse Team
Date: November 2025
"""

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


class TarragonType(Enum):
    """Tarragon variety categories"""
    FRENCH = "french"  # A. dracunculus var. sativa - TRUE, sterile
    RUSSIAN = "russian"  # A. dracunculus var. inodora - inferior
    MEXICAN = "mexican"  # Tagetes lucida - substitute


class TarragonDisease(Enum):
    """Major tarragon diseases"""
    RUST = "rust"
    POWDERY_MILDEW = "powdery_mildew"
    RHIZOCTONIA_ROOT_ROT = "rhizoctonia"
    PYTHIUM_ROOT_ROT = "pythium"
    FUSARIUM_ROOT_ROT = "fusarium"
    ALTERNARIA_LEAF_SPOT = "alternaria"
    BOTRYTIS_GRAY_MOLD = "botrytis"
    ROOT_ROT_COMPLEX = "root_rot_complex"


@dataclass
class TarragonDiseaseParams:
    """Disease parameters for tarragon"""
    disease: TarragonDisease
    pathogen: str
    severity: str
    yield_loss: Tuple[int, int]
    
    symptoms: List[str]
    diagnostic_features: str
    
    propagation_notes: str  # French tarragon sterile = vegetative only
    cultural_control: List[str]
    fungicide_control: List[str]
    
    market_impact: str
    treatment_cost_per_acre: float


# Abbreviated database
TARRAGON_DISEASES = {
    TarragonDisease.RUST: TarragonDiseaseParams(
        disease=TarragonDisease.RUST,
        pathogen="Puccinia tanaceti (#1 TARRAGON DISEASE, epidemic)",
        severity="10/10 - #1 DISEASE, EPIDEMIC, OVERWINTERS",
        yield_loss=(50, 90),
        
        symptoms=[
            "Orange-brown pustules on leaves DIAGNOSTIC",
            "Pustules on leaf undersides",
            "Chlorotic spots on upper surface",
            "Premature leaf drop",
            "Complete defoliation in severe cases",
            "Overwinters in crowns",
        ],
        
        diagnostic_features="Orange-brown pustules, epidemic, overwinters",
        
        propagation_notes="⚠️ French tarragon STERILE - vegetative propagation spreads rust",
        
        cultural_control=[
            "🚨 DO NOT propagate from infected plants",
            "Fall cleanup critical (overwinters)",
            "Remove infected leaves promptly",
            "Good air circulation",
            "Divide plants every 3-4 years with rust-free stock",
        ],
        
        fungicide_control=[
            "FRAC 3: Tebuconazole, myclobutanil",
            "FRAC 11: Azoxystrobin",
            "7-14 day intervals",
            "Begin at first pustules",
            "Preventative in endemic areas",
        ],
        
        market_impact="CATASTROPHIC - #1 disease, destroys French tarragon",
        treatment_cost_per_acre=300.0
    ),
    
    TarragonDisease.ROOT_ROT_COMPLEX: TarragonDiseaseParams(
        disease=TarragonDisease.ROOT_ROT_COMPLEX,
        pathogen="Pythium + Rhizoctonia + Fusarium (OVERWATERING)",
        severity="9/10 - OVERWATERING DISASTER",
        yield_loss=(70, 100),
        
        symptoms=[
            "Wilting despite adequate moisture",
            "Yellowing",
            "Root browning/blackening",
            "Crown rot",
            "Plant death",
            "PRIMARY CAUSE: OVERWATERING",
        ],
        
        diagnostic_features="Root rot, overwatering history",
        
        propagation_notes="Use disease-free stock, well-drained propagation media",
        
        cultural_control=[
            "EXCELLENT DRAINAGE ESSENTIAL",
            "Avoid overwatering (common error)",
            "Raised beds in poorly drained sites",
            "Sandy, well-drained soil",
            "Allow soil to dry between irrigations",
        ],
        
        fungicide_control=[
            "FRAC 4: Mefenoxam (preventative)",
            "DRAINAGE MORE IMPORTANT",
        ],
        
        market_impact="Plant death, stand replacement",
        treatment_cost_per_acre=350.0
    ),
}


class TarragonDiseaseDetector:
    """Tarragon disease detector - rust #1, French tarragon sterile propagation"""
    
    def __init__(self):
        self.diseases = TARRAGON_DISEASES
    
    def detect_disease(self, image: np.ndarray, tarragon_type: TarragonType = TarragonType.FRENCH) -> List:
        """Detect tarragon diseases (abbreviated)"""
        if image is None or image.size == 0:
            return []
        
        results = []
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Rust (orange-brown pustules)
        rust_score = self._detect_orange_brown_pustules(hsv)
        if rust_score > 0.3:
            warning = "🚨 CRITICAL: French tarragon sterile - vegetative propagation spreads rust"
            results.append({
                "disease": "Rust",
                "confidence": rust_score,
                "propagation_warning": warning if tarragon_type == TarragonType.FRENCH else "Monitor"
            })
        
        return results
    
    def _detect_orange_brown_pustules(self, hsv: np.ndarray) -> float:
        """Detect orange-brown pustules (rust)"""
        orange_lower = np.array([10, 80, 80])
        orange_upper = np.array([30, 255, 255])
        orange_mask = cv2.inRange(hsv, orange_lower, orange_upper)
        coverage = np.sum(orange_mask > 0) / orange_mask.size
        return min(1.0, coverage * 25)


if __name__ == "__main__":
    print("Tarragon Disease Detection System")
    print("=" * 70)
    print("\n🚨 CRITICAL: Rust (#1 Disease)")
    print("  Orange-brown pustules, epidemic, overwinters")
    print("  50-90% yield loss")
    print("\n⚠️  FRENCH TARRAGON WARNING:")
    print("  French tarragon is STERILE (no seeds)")
    print("  100% vegetative propagation required")
    print("  Rust spreads through infected cuttings")
    print("  DO NOT propagate from infected plants")
    print("\n💡 Russian tarragon: Seed-grown but INFERIOR flavor")
    print("   Not acceptable for premium French cuisine")
    print("\n✓ Tarragon disease detection system initialized")
    print("  Market: $15M USA specialty, French $15-30/lb retail")
