"""
Bay Laurel Disease Detection Suite
===================================

Comprehensive disease identification for bay laurel (Laurus nobilis), premium
Mediterranean tree herb with Phytophthora root rot and scale insect sooty mold challenges.

Bay Laurel Types:
- True bay (Laurus nobilis) - culinary standard
- Willow-leaf bay - narrow leaves
- Golden bay - yellow foliage
- Note: California bay (Umbellularia californica) - different genus, stronger flavor

Critical Diseases:
1. Phytophthora Root Rot (P. cinnamomi, P. citricola) - #1 KILLER, WATERLOGGING
2. Anthracnose (Colletotrichum spp.) - LEAF SPOTS, DEFOLIATION
3. Sooty Mold (Capnodium spp.) - SCALE INSECT HONEYDEW
4. Powdery Mildew (Oidium spp.) - GREENHOUSE
5. Bacterial Leaf Spot (Pseudomonas spp.) - WATER-SOAKED SPOTS
6. Phomopsis Leaf Blight - STEM CANKERS
7. Cercospora Leaf Spot - TARGET RINGS
8. Root Rot Complex (Pythium + Rhizoctonia) - POOR DRAINAGE

Market Intelligence:
- USA production: $10 million (specialty, limited volume)
- Fresh bay leaves: $25-40/lb retail (premium), $15-25/lb wholesale
- Dried bay leaves: $40-100/lb organic
- Essential oil: $150-400/kg (1,8-cineole, eugenol)
- Slow-growing tree: 3-5 years to commercial size
- Container production dominant (90% nursery/specialty)
- Drought-adapted: OVERWATERING #1 killer
- Premium market: Gourmet cooking, Mediterranean cuisine

Author: AgroPulse Team
Date: November 2025
"""

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


class BayLaurelType(Enum):
    """Bay laurel variety categories"""
    TRUE_BAY = "true_bay"  # L. nobilis - standard
    WILLOW_LEAF = "willow_leaf"  # Narrow leaves
    GOLDEN = "golden"  # Yellow foliage
    CALIFORNIA_BAY = "california_bay"  # Umbellularia - different genus


class BayLaurelDisease(Enum):
    """Major bay laurel diseases"""
    PHYTOPHTHORA_ROOT_ROT = "phytophthora"
    ANTHRACNOSE = "anthracnose"
    SOOTY_MOLD = "sooty_mold"
    POWDERY_MILDEW = "powdery_mildew"
    BACTERIAL_LEAF_SPOT = "bacterial_spot"
    PHOMOPSIS_BLIGHT = "phomopsis"
    CERCOSPORA_LEAF_SPOT = "cercospora"
    ROOT_ROT_COMPLEX = "root_rot_complex"


@dataclass
class BayLaurelDiseaseParams:
    """Disease parameters for bay laurel"""
    disease: BayLaurelDisease
    pathogen: str
    severity: str
    yield_loss: Tuple[int, int]
    
    symptoms: List[str]
    diagnostic_features: str
    
    container_production_notes: str  # 90% container-grown
    irrigation_relationship: str
    cultural_control: List[str]
    fungicide_control: List[str]
    
    market_impact: str
    treatment_cost_per_plant: float  # Tree crop, per-plant cost


# Abbreviated database
BAY_LAUREL_DISEASES = {
    BayLaurelDisease.PHYTOPHTHORA_ROOT_ROT: BayLaurelDiseaseParams(
        disease=BayLaurelDisease.PHYTOPHTHORA_ROOT_ROT,
        pathogen="Phytophthora cinnamomi + P. citricola (#1 KILLER, waterlogging)",
        severity="10/10 - #1 BAY LAUREL KILLER, OVERWATERING DISASTER",
        yield_loss=(80, 100),
        
        symptoms=[
            "Wilting despite adequate moisture DIAGNOSTIC",
            "Yellowing leaves",
            "Leaf drop",
            "Dieback of branches",
            "Black, mushy roots",
            "Crown rot at soil line",
            "Complete tree death within weeks-months",
        ],
        
        diagnostic_features="Wilting + black mushy roots + waterlogging history",
        
        container_production_notes="CRITICAL: Container drainage holes essential, well-drained media",
        irrigation_relationship="🚨 OVERWATERING #1 CAUSE - bay laurel drought-adapted Mediterranean tree",
        
        cultural_control=[
            "🚨 EXCELLENT DRAINAGE ESSENTIAL (most critical factor)",
            "Container production: Drainage holes, well-drained media",
            "Field: Raised beds 12+ inches, sandy soil",
            "DO NOT OVERWATER (common killer)",
            "Allow soil to dry between irrigations",
            "Drip irrigation only, NO overhead",
            "Avoid planting where Phytophthora present",
        ],
        
        fungicide_control=[
            "PREVENTATIVE ONLY - no cure:",
            "FRAC 4: Mefenoxam (Ridomil) drench",
            "FRAC 43: Fluopicolide",
            "Apply at planting",
            "Monthly in wet seasons",
            "DRAINAGE > FUNGICIDES",
        ],
        
        market_impact="CATASTROPHIC - #1 cause bay laurel death, tree replacement",
        treatment_cost_per_plant=50.0  # 3-5 year tree replacement
    ),
    
    BayLaurelDisease.ANTHRACNOSE: BayLaurelDiseaseParams(
        disease=BayLaurelDisease.ANTHRACNOSE,
        pathogen="Colletotrichum spp. (leaf spots, defoliation)",
        severity="8/10 - LEAF SPOTS, DEFOLIATION",
        yield_loss=(20, 50),
        
        symptoms=[
            "Circular to irregular brown leaf spots",
            "Spots with dark borders",
            "Premature leaf drop",
            "Twig dieback",
            "Severe in wet, humid weather",
        ],
        
        diagnostic_features="Leaf spots, defoliation, wet weather",
        
        container_production_notes="Good air circulation between containers reduces disease",
        irrigation_relationship="Wet foliage promotes disease",
        
        cultural_control=[
            "Avoid overhead irrigation",
            "Good air circulation",
            "Remove infected leaves",
            "Prune for air flow",
        ],
        
        fungicide_control=[
            "FRAC 11: Azoxystrobin",
            "FRAC 7: Boscalid",
            "FRAC 3: Difenoconazole",
            "Apply during wet weather",
        ],
        
        market_impact="Leaf spotting reduces harvest quality",
        treatment_cost_per_plant=10.0
    ),
    
    BayLaurelDisease.SOOTY_MOLD: BayLaurelDiseaseParams(
        disease=BayLaurelDisease.SOOTY_MOLD,
        pathogen="Capnodium spp. (grows on SCALE INSECT HONEYDEW)",
        severity="7/10 - COSMETIC DAMAGE, SCALE INSECT PROBLEM",
        yield_loss=(15, 40),
        
        symptoms=[
            "Black sooty coating on leaves DIAGNOSTIC",
            "Coating easily wipes off",
            "Grows on HONEYDEW from scale insects",
            "Blocks light, reduces photosynthesis",
            "Cosmetically unacceptable",
        ],
        
        diagnostic_features="Black sooty coating, scale insects present, wipes off",
        
        container_production_notes="Inspect containers for scale insects regularly",
        irrigation_relationship="Not water-related (insect problem)",
        
        cultural_control=[
            "🚨 CONTROL SCALE INSECTS (root cause)",
            "Insecticidal soap for scale",
            "Horticultural oil sprays",
            "Remove sooty mold by washing leaves",
            "Scout for scale insects weekly",
        ],
        
        fungicide_control=[
            "NOT A FUNGAL INFECTION OF PLANT",
            "Control scale insects instead",
            "Wash off sooty mold with water + soap",
        ],
        
        market_impact="Cosmetic damage, unmarketable leaves",
        treatment_cost_per_plant=8.0
    ),
}


class BayLaurelDiseaseDetector:
    """Bay laurel disease detector - Phytophthora #1 killer, container production focus"""
    
    def __init__(self):
        self.diseases = BAY_LAUREL_DISEASES
    
    def detect_disease(self,
                      image: np.ndarray,
                      plant_part: str = "leaf",
                      container_grown: bool = True) -> List:
        """Detect bay laurel diseases (abbreviated)"""
        if image is None or image.size == 0:
            return []
        
        results = []
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        if plant_part == "leaf":
            # Sooty mold (black coating)
            sooty_score = self._detect_black_coating(hsv)
            if sooty_score > 0.4:
                results.append({
                    "disease": "Sooty Mold",
                    "confidence": sooty_score,
                    "note": "🚨 Control scale insects (root cause)"
                })
            
            # Anthracnose (leaf spots)
            anthr_score = self._detect_leaf_spots(hsv)
            if anthr_score > 0.4:
                results.append({"disease": "Anthracnose", "confidence": anthr_score})
        
        elif plant_part == "root":
            # Phytophthora (black mushy roots)
            phyto_score = self._detect_black_mushy_roots(hsv)
            if phyto_score > 0.5:
                drainage_warn = "CRITICAL: Check drainage, DO NOT overwater"
                results.append({
                    "disease": "Phytophthora Root Rot",
                    "confidence": phyto_score,
                    "warning": drainage_warn
                })
        
        return results
    
    def _detect_black_coating(self, hsv: np.ndarray) -> float:
        """Detect black sooty coating"""
        black_lower = np.array([0, 0, 0])
        black_upper = np.array([180, 255, 60])
        black_mask = cv2.inRange(hsv, black_lower, black_upper)
        coverage = np.sum(black_mask > 0) / black_mask.size
        return min(1.0, coverage * 20)
    
    def _detect_leaf_spots(self, hsv: np.ndarray) -> float:
        """Detect leaf spots (anthracnose)"""
        brown_lower = np.array([10, 50, 40])
        brown_upper = np.array([25, 200, 150])
        brown_mask = cv2.inRange(hsv, brown_lower, brown_upper)
        coverage = np.sum(brown_mask > 0) / brown_mask.size
        return min(1.0, coverage * 18)
    
    def _detect_black_mushy_roots(self, hsv: np.ndarray) -> float:
        """Detect black mushy roots (Phytophthora)"""
        black_lower = np.array([0, 0, 0])
        black_upper = np.array([180, 255, 50])
        black_mask = cv2.inRange(hsv, black_lower, black_upper)
        coverage = np.sum(black_mask > 0) / black_mask.size
        return min(1.0, coverage * 15)


if __name__ == "__main__":
    print("Bay Laurel Disease Detection System")
    print("=" * 70)
    print("\n🚨 CRITICAL: Phytophthora Root Rot (#1 Killer)")
    print("  OVERWATERING disaster for drought-adapted Mediterranean tree")
    print("  Excellent drainage ESSENTIAL")
    print("  Container production: Drainage holes + well-drained media")
    print("\n⚠️  SOOTY MOLD:")
    print("  Black coating = SCALE INSECT HONEYDEW")
    print("  Control scale insects, not a fungal infection")
    print("\n💡 SLOW-GROWING TREE:")
    print("  3-5 years to commercial size")
    print("  Tree death = major economic loss")
    print("  Prevention through drainage critical")
    print("\n✓ Bay laurel disease detection system initialized")
    print("  Market: $10M USA specialty, fresh $25-40/lb retail")
