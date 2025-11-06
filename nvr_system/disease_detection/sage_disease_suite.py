"""
Sage Disease Detection Suite
=============================

Comprehensive disease identification for sage (Salvia officinalis), premium Mediterranean
herb with powdery mildew dominance and root rot from overwatering.

Sage Types:
- Common sage (S. officinalis) - culinary standard
- Purple sage - ornamental, culinary
- Tricolor sage - variegated, ornamental
- Golden sage - yellow variegated
- Pineapple sage (S. elegans) - fruity scent

Critical Diseases:
1. Powdery Mildew (Erysiphe biocellata) - #1 DISEASE, EPIDEMIC
2. Root Rot Complex (Phytophthora + Rhizoctonia + Pythium) - OVERWATERING
3. Botrytis Gray Mold - POSTHARVEST, GREENHOUSE
4. Verticillium Wilt - SOILBORNE, 10+ YEARS
5. Bacterial Leaf Spot (Pseudomonas syringae) - CUTTING SPREAD
6. Alternaria Leaf Blight - DEFOLIATION
7. Cercospora Leaf Spot - LATE SEASON
8. Southern Blight (Sclerotium rolfsii) - WHITE MYCELIUM, SCLEROTIA

Market Intelligence:
- USA production: $35 million, Mediterranean regions
- Fresh sage: $10-16/lb wholesale, $15-25/lb retail
- Dried sage: $20-40/lb organic
- Essential oil: $120-300/kg (thujone content regulated)
- Perennial: 3-5 year stands
- Drought-adapted: OVERWATERING #1 grower error
- Cutting propagation: 90% commercial

Author: AgroPulse Team
Date: November 2025
"""

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


class SageType(Enum):
    """Sage variety categories"""
    COMMON = "common"  # S. officinalis
    PURPLE = "purple"
    TRICOLOR = "tricolor"
    GOLDEN = "golden"
    PINEAPPLE = "pineapple"


class SageDisease(Enum):
    """Major sage diseases"""
    POWDERY_MILDEW = "powdery_mildew"
    ROOT_ROT_COMPLEX = "root_rot"
    BOTRYTIS_GRAY_MOLD = "botrytis"
    VERTICILLIUM_WILT = "verticillium"
    BACTERIAL_LEAF_SPOT = "bacterial_spot"
    ALTERNARIA_BLIGHT = "alternaria"
    CERCOSPORA_LEAF_SPOT = "cercospora"
    SOUTHERN_BLIGHT = "southern_blight"


@dataclass
class SageDiseaseParams:
    """Disease parameters for sage"""
    disease: SageDisease
    pathogen: str
    severity: str
    yield_loss: Tuple[int, int]
    
    symptoms: List[str]
    diagnostic_features: str
    
    irrigation_relationship: str  # Critical for Mediterranean herb
    cultural_control: List[str]
    fungicide_control: List[str]
    
    market_impact: str
    treatment_cost_per_acre: float


# Abbreviated database
SAGE_DISEASES = {
    SageDisease.POWDERY_MILDEW: SageDiseaseParams(
        disease=SageDisease.POWDERY_MILDEW,
        pathogen="Erysiphe biocellata (#1 SAGE DISEASE, epidemic)",
        severity="10/10 - #1 DISEASE, EPIDEMIC IN GREENHOUSE",
        yield_loss=(30, 70),
        
        symptoms=[
            "White powdery growth on leaves",
            "Starts as small patches, covers leaves",
            "Leaves yellow then brown",
            "Severe in greenhouse/high humidity",
        ],
        
        diagnostic_features="White powder, greenhouse epidemic",
        
        irrigation_relationship="Humidity promotes (not wetness)",
        
        cultural_control=[
            "Good air circulation",
            "Reduce greenhouse humidity",
            "Space plants for air flow",
            "Avoid excessive nitrogen",
        ],
        
        fungicide_control=[
            "FRAC 3: Myclobutanil, tebuconazole",
            "FRAC 13: Quinoxyfen",
            "FRAC 50: Metrafenone",
            "Sulfur (organic)",
            "7-14 day intervals",
        ],
        
        market_impact="#1 disease, 30-70% loss in greenhouse",
        treatment_cost_per_acre=200.0
    ),
    
    SageDisease.ROOT_ROT_COMPLEX: SageDiseaseParams(
        disease=SageDisease.ROOT_ROT_COMPLEX,
        pathogen="Phytophthora + Rhizoctonia + Pythium (OVERWATERING disaster)",
        severity="10/10 - OVERWATERING KILLS SAGE",
        yield_loss=(80, 100),
        
        symptoms=[
            "Wilting despite adequate moisture",
            "Yellowing foliage",
            "Black mushy roots",
            "Complete plant death",
            "PRIMARY CAUSE: OVERWATERING",
        ],
        
        diagnostic_features="Black mushy roots, overwatering history",
        
        irrigation_relationship="🚨 OVERWATERING #1 CAUSE - sage drought-adapted",
        
        cultural_control=[
            "🚨 DO NOT OVERWATER (most common error)",
            "Excellent drainage ESSENTIAL",
            "Raised beds 8-12 inches",
            "Allow soil to dry between irrigations",
            "Sandy, well-drained soil",
        ],
        
        fungicide_control=[
            "FRAC 4: Mefenoxam (preventative only)",
            "DRAINAGE MORE IMPORTANT",
        ],
        
        market_impact="CATASTROPHIC - #1 cause sage crop failure",
        treatment_cost_per_acre=400.0
    ),
}


class SageDiseaseDetector:
    """Sage disease detector - powdery mildew + overwatering disasters"""
    
    def __init__(self):
        self.diseases = SAGE_DISEASES
    
    def detect_disease(self, image: np.ndarray) -> List:
        """Detect sage diseases (abbreviated)"""
        if image is None or image.size == 0:
            return []
        
        results = []
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Powdery mildew
        powdery_score = self._detect_white_powder(hsv)
        if powdery_score > 0.4:
            results.append({"disease": "Powdery Mildew", "confidence": powdery_score})
        
        return results
    
    def _detect_white_powder(self, hsv: np.ndarray) -> float:
        """Detect white powder"""
        white_lower = np.array([0, 0, 200])
        white_upper = np.array([180, 50, 255])
        white_mask = cv2.inRange(hsv, white_lower, white_upper)
        coverage = np.sum(white_mask > 0) / white_mask.size
        return min(1.0, coverage * 20)


if __name__ == "__main__":
    print("Sage Disease Detection System")
    print("=" * 70)
    print("\n🚨 CRITICAL DISEASES:")
    print("  1. Powdery Mildew - #1 disease, greenhouse epidemic")
    print("  2. Root Rot - OVERWATERING disaster (drought-adapted herb)")
    print("\n⚠️  GROWER ERROR: OVERWATERING kills sage")
    print("  Sage is Mediterranean, drought-adapted")
    print("  Excellent drainage ESSENTIAL")
    print("\n✓ Sage disease detection system initialized")
    print("  Market: $35M USA, dried $20-40/lb organic")
