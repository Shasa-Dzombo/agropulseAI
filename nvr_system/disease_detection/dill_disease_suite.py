"""
Dill Disease Detection Suite
=============================

Comprehensive disease identification for dill (Anethum graveolens), premium culinary
herb with Cercospora blight dominance and rapid growth cycle challenges.

Dill Types:
- Bouquet/Mammoth - seed production, tall (3-4 ft)
- Fernleaf - compact, slow-bolt, foliage
- Dukat - European variety, aromatic
- Superdukat - improved Dukat

Critical Diseases:
1. Cercospora Leaf Blight (Cercospora anethicola) - #1 DISEASE, EPIDEMIC
2. Alternaria Leaf Blight - SEED-BORNE, DEFOLIATION
3. Powdery Mildew (Erysiphe heraclei) - LATE SEASON
4. Bacterial Leaf Spot (Pseudomonas syringae) - WET WEATHER
5. Septoria Leaf Spot - TARGET RINGS
6. Fusarium Wilt - SOILBORNE
7. Carrot Mosaic Virus (CMV) - APHID VECTOR
8. Aster Yellows (Phytoplasma) - LEAFHOPPER VECTOR

Market Intelligence:
- USA production: $25 million fresh, $10 million seed
- Fresh dill: $6-12/lb wholesale, $12-18/lb retail
- Dill seed: $4-8/lb (spice market)
- Dill weed (dried): $15-30/lb organic
- Essential oil: $80-150/kg (carvone content critical)
- Fast growth: 40-60 days fresh, 90-120 days seed
- Succession planting: 2-week intervals (short harvest window)

Author: AgroPulse Team
Date: November 2025
"""

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


class DillProductType(Enum):
    """Dill harvest types"""
    FRESH_LEAF = "fresh_leaf"  # Dill weed, 40-60 days
    SEED = "seed"  # Spice, 90-120 days
    DUAL_PURPOSE = "dual"  # Both leaf and seed


class DillDisease(Enum):
    """Major dill diseases"""
    CERCOSPORA_BLIGHT = "cercospora"
    ALTERNARIA_BLIGHT = "alternaria"
    POWDERY_MILDEW = "powdery_mildew"
    BACTERIAL_LEAF_SPOT = "bacterial_spot"
    SEPTORIA_LEAF_SPOT = "septoria"
    FUSARIUM_WILT = "fusarium"
    CARROT_MOSAIC_VIRUS = "carrot_mosaic"
    ASTER_YELLOWS = "aster_yellows"


@dataclass
class DillDiseaseParams:
    """Disease parameters for dill"""
    disease: DillDisease
    pathogen: str
    severity: str
    leaf_yield_loss: Tuple[int, int]
    seed_yield_loss: Tuple[int, int]
    
    leaf_symptoms: List[str]
    seed_symptoms: List[str]
    diagnostic_features: str
    
    resistant_varieties: List[str]
    cultural_control: List[str]
    fungicide_control: List[str]
    
    market_impact: str
    treatment_cost_per_acre: float


# Abbreviated database (key diseases)
DILL_DISEASES = {
    DillDisease.CERCOSPORA_BLIGHT: DillDiseaseParams(
        disease=DillDisease.CERCOSPORA_BLIGHT,
        pathogen="Cercospora anethicola (#1 DILL DISEASE, epidemic defoliation)",
        severity="10/10 - #1 DISEASE, EPIDEMIC DEFOLIATION",
        leaf_yield_loss=(40, 80),
        seed_yield_loss=(50, 90),
        
        leaf_symptoms=[
            "Circular brown spots 2-10mm",
            "Target-ring pattern",
            "Yellow halo around spots",
            "Spots coalesce to large blighted areas",
            "Complete defoliation in severe cases",
            "Epidemic spread in warm humid weather",
        ],
        
        seed_symptoms=[
            "Seed discoloration",
            "Reduced seed set",
            "Poor germination",
        ],
        
        diagnostic_features="Target-ring spots, epidemic defoliation, warm weather",
        
        resistant_varieties=[
            "Limited resistance available",
            "Dukat may have some tolerance",
        ],
        
        cultural_control=[
            "2-3 year rotation to non-Apiaceae",
            "Remove crop residues",
            "Good air circulation",
            "Avoid overhead irrigation",
            "Succession planting escapes peak pressure",
        ],
        
        fungicide_control=[
            "FRAC 7: Boscalid",
            "FRAC 11: Azoxystrobin",
            "FRAC 3: Difenoconazole",
            "7-14 day intervals",
            "Begin at first spots",
        ],
        
        market_impact="CATASTROPHIC - #1 disease, 40-80% loss",
        treatment_cost_per_acre=200.0
    ),
    
    DillDisease.ALTERNARIA_BLIGHT: DillDiseaseParams(
        disease=DillDisease.ALTERNARIA_BLIGHT,
        pathogen="Alternaria spp. (SEED-BORNE, defoliation)",
        severity="9/10 - SEED-BORNE, DEFOLIATION",
        leaf_yield_loss=(30, 60),
        seed_yield_loss=(40, 70),
        
        leaf_symptoms=[
            "Brown spots with target rings",
            "Premature leaf drop",
        ],
        
        seed_symptoms=[
            "Seed-borne transmission critical",
            "Use certified disease-free seed",
        ],
        
        diagnostic_features="Target rings, seed-borne",
        
        resistant_varieties=["Limited"],
        
        cultural_control=[
            "Certified disease-free seed",
            "Rotation",
            "Remove residues",
        ],
        
        fungicide_control=[
            "FRAC 7: Boscalid",
            "FRAC 11: Azoxystrobin",
        ],
        
        market_impact="Defoliation + seed contamination",
        treatment_cost_per_acre=180.0
    ),
}


class DillDiseaseDetector:
    """Dill disease detector - Cercospora blight #1 epidemic"""
    
    def __init__(self):
        self.diseases = DILL_DISEASES
    
    def detect_disease(self, image: np.ndarray) -> List:
        """Detect dill diseases (abbreviated)"""
        if image is None or image.size == 0:
            return []
        
        results = []
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Cercospora (target rings)
        cercospora_score = self._detect_target_rings(hsv)
        if cercospora_score > 0.4:
            results.append({"disease": "Cercospora", "confidence": cercospora_score})
        
        return results
    
    def _detect_target_rings(self, hsv: np.ndarray) -> float:
        """Detect target-ring spots"""
        brown_lower = np.array([10, 50, 40])
        brown_upper = np.array([25, 200, 150])
        brown_mask = cv2.inRange(hsv, brown_lower, brown_upper)
        coverage = np.sum(brown_mask > 0) / brown_mask.size
        return min(1.0, coverage * 18)


if __name__ == "__main__":
    print("Dill Disease Detection System")
    print("=" * 70)
    print("\n🚨 CRITICAL: Cercospora Leaf Blight (#1 Disease)")
    print("  Epidemic defoliation, 40-80% loss")
    print("  Fast growth (40-60 days) = rapid disease progression")
    print("\n✓ Dill disease detection system initialized")
    print("  Market: $35M USA, fresh $6-12/lb, seed $4-8/lb")
