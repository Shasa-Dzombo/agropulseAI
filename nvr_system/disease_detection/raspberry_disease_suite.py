"""
Raspberry Disease Detection Suite
==================================

Comprehensive disease identification for red/black raspberry (Rubus idaeus/occidentalis),
premium bramble fruit with cane diseases and Phytophthora root rot challenges.

Raspberry Types:
- Red raspberry (Rubus idaeus) - 80% production, summer/fall bearing
- Black raspberry (R. occidentalis) - "Black caps", different diseases
- Yellow/Golden raspberry - Color variant of red
- Purple raspberry - Hybrid red × black

Major Varieties:
- Heritage - Fall-bearing, disease resistant
- Tulameen - Summer, large fruit, susceptible
- Meeker - Processing standard
- Caroline - Fall-bearing, vigorous
- Jewel - Black raspberry

Critical Diseases:
1. Phytophthora Root Rot (P. fragariae var. rubi) - #1 KILLER, WATERLOGGING
2. Cane Blight (Leptosphaeria coniothyrium) - CANE DEATH EPIDEMIC
3. Spur Blight (Didymella applanata) - LATERAL DEATH, 30-60% LOSS
4. Botrytis Fruit Rot/Gray Mold - #1 POSTHARVEST, 30-70% LOSSES
5. Anthracnose (Elsinoe veneta) - CANE LESIONS, FRUIT SPOTTING
6. Cane/Crown Gall (Agrobacterium) - CROWN TUMORS
7. Raspberry Mosaic Virus Complex - NO CURE, APHID VECTOR
8. Root Rot Complex (Pythium + Rhizoctonia + Fusarium) - POOR DRAINAGE

Market Intelligence:
- USA production: $750 million (Washington 65%, Oregon 20%, California 8%)
- Global production: $5 billion (Russia 20%, Poland 12%, USA 15%, Serbia 10%)
- Retail: $6-9/pint fresh, $8-12/lb frozen, $10-16/lb organic
- Phytophthora: #1 cause raspberry field failure, replanting $8,000-12,000/acre
- Botrytis: 30-70% postharvest losses wet harvest
- Cane lifespan: 2 years (annual replacement essential)

Author: AgroPulse Team  
Date: November 2025
"""

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


class RaspberryType(Enum):
    """Raspberry type categories"""
    RED_SUMMER = "red_summer"  # Summer-bearing red
    RED_FALL = "red_fall"  # Fall-bearing (primocane)
    BLACK = "black"  # Black raspberry
    YELLOW = "yellow"  # Golden raspberry
    PURPLE = "purple"  # Hybrid


class RaspberryDisease(Enum):
    """Major raspberry diseases"""
    PHYTOPHTHORA_ROOT_ROT = "phytophthora"
    CANE_BLIGHT = "cane_blight"
    SPUR_BLIGHT = "spur_blight"
    BOTRYTIS_FRUIT_ROT = "botrytis"
    ANTHRACNOSE = "anthracnose"
    CANE_GALL = "cane_gall"
    VIRUS_COMPLEX = "virus_complex"
    ROOT_ROT_COMPLEX = "root_rot_complex"


@dataclass
class RaspberryDiseaseParams:
    """Disease parameters for raspberry"""
    disease: RaspberryDisease
    pathogen: str
    severity: str
    yield_loss: Tuple[int, int]
    
    symptoms: List[str]
    diagnostic_features: str
    
    cultural_control: List[str]
    chemical_control: List[str]
    
    economic_impact: str
    treatment_cost_per_acre: float


# Abbreviated database
RASPBERRY_DISEASES = {
    RaspberryDisease.PHYTOPHTHORA_ROOT_ROT: RaspberryDiseaseParams(
        disease=RaspberryDisease.PHYTOPHTHORA_ROOT_ROT,
        pathogen="Phytophthora fragariae var. rubi (#1 RASPBERRY KILLER)",
        severity="10/10 - #1 CAUSE RASPBERRY FIELD FAILURE",
        yield_loss=(80, 100),
        
        symptoms=[
            "Wilting entire rows DIAGNOSTIC",
            "Stunted growth",
            "Yellowing leaves",
            "Cane dieback",
            "Red-brown root discoloration",
            "Complete plant death",
            "Field failure (replanting required)",
        ],
        
        diagnostic_features="Row wilting + waterlogging history + red roots",
        
        cultural_control=[
            "🚨 RAISED BEDS 12-18 inches ESSENTIAL (mandatory)",
            "Excellent drainage (most critical)",
            "Avoid overwatering",
            "Fumigation pre-plant (dazomet, metam sodium)",
            "Certified disease-free planting stock",
            "Avoid replanting infested sites",
        ],
        
        chemical_control=[
            "FRAC 4: Mefenoxam drench - preventative",
            "Apply at planting + annually",
            "NO CURE (prevention only)",
            "RAISED BEDS > FUNGICIDES",
        ],
        
        economic_impact="CATASTROPHIC - Field failure, replanting $8,000-12,000/acre + 3-4 year production loss",
        treatment_cost_per_acre=500.0
    ),
    
    RaspberryDisease.BOTRYTIS_FRUIT_ROT: RaspberryDiseaseParams(
        disease=RaspberryDisease.BOTRYTIS_FRUIT_ROT,
        pathogen="Botrytis cinerea (#1 POSTHARVEST DISEASE)",
        severity="9/10 - #1 POSTHARVEST, 30-70% LOSSES WET HARVEST",
        yield_loss=(30, 70),
        
        symptoms=[
            "GRAY FUZZY MOLD on ripe fruit DIAGNOSTIC",
            "Fruit rot rapid post-harvest",
            "Spreads fruit-to-fruit in containers",
            "Flower blight (wet weather)",
            "Complete unmarketable",
        ],
        
        diagnostic_features="Gray fuzzy mold, wet weather epidemic",
        
        cultural_control=[
            "Harvest dry fruit only (morning dew = high risk)",
            "Rapid cooling post-harvest (32-34°F)",
            "Good air circulation (pruning, row orientation)",
            "Avoid overhead irrigation",
            "Remove infected fruit",
        ],
        
        chemical_control=[
            "FRAC 17: Fenhexamid - bloom + pre-harvest",
            "FRAC 9: Cyprodinil + fludioxonil - pre-harvest",
            "FRAC 7: Boscalid - alternating",
            "Rotate FRAC codes (resistance common)",
        ],
        
        economic_impact="SEVERE - 30-70% postharvest losses wet harvest, $50-100M annual USA losses",
        treatment_cost_per_acre=400.0
    ),
}


class RaspberryDiseaseDetector:
    """Raspberry disease detector - Phytophthora #1 killer, Botrytis postharvest"""
    
    def __init__(self):
        self.diseases = RASPBERRY_DISEASES


if __name__ == "__main__":
    print("Raspberry Disease Detection System")
    print("=" * 70)
    print("\n🚨 PHYTOPHTHORA ROOT ROT: #1 Raspberry Killer")
    print("  Field failure, replanting $8,000-12,000/acre")
    print("  RAISED BEDS 12-18 inches ESSENTIAL")
    print("\n⚠️  BOTRYTIS: #1 Postharvest, 30-70% losses wet harvest")
    print("\n✓ Raspberry disease detection system initialized")
    print("  Market: $750M USA (Washington 65%), $5B global")
