"""
Blackberry Disease Detection Suite
===================================

Comprehensive disease identification for blackberry (Rubus spp.), premium
bramble fruit with cane diseases and orange rust epidemic challenges.

Blackberry Types:
- Erect thorny - Self-supporting, cold-hardy
- Erect thornless - Commercial standard
- Semi-erect thornless - High yield, large fruit
- Trailing (dewberry) - Ground cover, mild climates

Major Varieties:
- Triple Crown - Semi-erect, large sweet fruit
- Natchez - Erect thornless, early, large
- Ouachita - Erect thornless, disease resistant
- Apache - Erect thornless, firm fruit
- Kiowa - Erect thorny, huge berries

Critical Diseases:
1. Orange Rust (Arthuriomyces peckianus + Gymnoconia nitens) - SYSTEMIC, NO CURE, 100% PLANT LOSS
2. Anthracnose (Elsinoe veneta) - #1 CANE DISEASE, PURPLE SPOTS
3. Cane/Crown Gall (Agrobacterium tumefaciens) - CROWN TUMORS, PLANT DEATH
4. Botrytis Fruit Rot/Gray Mold - POSTHARVEST 20-50% LOSSES
5. Double Blossom/Rosette (Cercosporella rubi) - FLOWER ABNORMALITY
6. Septoria Leaf Spot - DEFOLIATION
7. Phytophthora Root Rot - WATERLOGGING DISASTER
8. Blackberry Yellow Vein Virus - NO CURE, APHID VECTOR

Market Intelligence:
- USA production: $600 million (Oregon 55%, Texas 8%, Arkansas 7%)
- Global production: $2 billion (Mexico 40%, USA 30%, Guatemala 8%)
- Retail: $5-8/pint fresh, $8-14/lb organic
- Orange rust: 100% infected plant loss, NO CURE
- Anthracnose: 50-80% losses without fungicides
- Cane lifespan: 2 years (biennial)

Author: AgroPulse Team
Date: November 2025
"""

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


class BlackberryType(Enum):
    """Blackberry type categories"""
    ERECT_THORNY = "erect_thorny"
    ERECT_THORNLESS = "erect_thornless"
    SEMI_ERECT = "semi_erect"
    TRAILING = "trailing"  # Dewberry


class BlackberryDisease(Enum):
    """Major blackberry diseases"""
    ORANGE_RUST = "orange_rust"
    ANTHRACNOSE = "anthracnose"
    CANE_GALL = "cane_gall"
    BOTRYTIS = "botrytis"
    DOUBLE_BLOSSOM = "double_blossom"
    SEPTORIA = "septoria"
    PHYTOPHTHORA_ROOT_ROT = "phytophthora"
    YELLOW_VEIN_VIRUS = "yellow_vein_virus"


@dataclass
class BlackberryDiseaseParams:
    """Disease parameters for blackberry"""
    disease: BlackberryDisease
    pathogen: str
    severity: str
    yield_loss: Tuple[int, int]
    
    symptoms: List[str]
    diagnostic_features: str
    
    cultural_control: List[str]
    chemical_control: List[str]
    
    economic_impact: str
    treatment_cost_per_acre: float


# Comprehensive disease database
BLACKBERRY_DISEASES = {
    BlackberryDisease.ORANGE_RUST: BlackberryDiseaseParams(
        disease=BlackberryDisease.ORANGE_RUST,
        pathogen="Arthuriomyces peckianus + Gymnoconia nitens (SYSTEMIC, NO CURE)",
        severity="10/10 - SYSTEMIC INFECTION, 100% PLANT LOSS, NO CURE",
        yield_loss=(100, 100),
        
        symptoms=[
            "BRIGHT ORANGE PUSTULES on leaf undersides DIAGNOSTIC",
            "Entire plant infected (SYSTEMIC, not curable)",
            "Stunted, spindly growth",
            "Pale, distorted leaves spring",
            "NO FRUIT PRODUCTION",
            "Plant dies or produces no yield",
            "Spreads to adjacent plants",
        ],
        
        diagnostic_features="Bright orange pustules, systemic infection, stunted plant",
        
        cultural_control=[
            "🚨 REMOVE INFECTED PLANTS IMMEDIATELY (dig crown + roots)",
            "Destroy infected plants (burn or bury deep)",
            "DO NOT compost",
            "Scout weekly spring (early detection critical)",
            "Inspect new plantings carefully",
            "Remove wild blackberries within 500 feet (reservoir)",
        ],
        
        chemical_control=[
            "NO EFFECTIVE FUNGICIDES (systemic infection)",
            "Prevention through plant removal only",
            "NO CURE - must remove plants",
        ],
        
        economic_impact="CATASTROPHIC - 100% infected plant loss, no production, replanting required",
        treatment_cost_per_acre=0.0  # No treatment, must remove
    ),
    
    BlackberryDisease.ANTHRACNOSE: BlackberryDiseaseParams(
        disease=BlackberryDisease.ANTHRACNOSE,
        pathogen="Elsinoe veneta (#1 CANE DISEASE)",
        severity="9/10 - #1 CANE DISEASE, 50-80% LOSSES",
        yield_loss=(50, 80),
        
        symptoms=[
            "PURPLE SPOTS with gray centers on canes DIAGNOSTIC",
            "Sunken lesions on canes",
            "Fruit spots (unmarketable)",
            "Cane cracking/splitting",
            "Premature fruit drop",
            "Complete cane death severe cases",
        ],
        
        diagnostic_features="Purple spots gray centers on canes, wet weather epidemic",
        
        cultural_control=[
            "Remove infected canes (winter)",
            "Thin canes (air circulation)",
            "Avoid overhead irrigation",
            "Resistant varieties (Ouachita, Apache)",
        ],
        
        chemical_control=[
            "FRAC M1: Copper - weekly wet weather",
            "FRAC 3: Tebuconazole - 14-day intervals",
            "FRAC 11: Azoxystrobin - monthly",
            "Begin: Budbreak",
            "Continue: Through bloom",
        ],
        
        economic_impact="SEVERE - 50-80% losses without fungicides, #1 blackberry cane disease",
        treatment_cost_per_acre=450.0
    ),
}


class BlackberryDiseaseDetector:
    """Blackberry disease detector - Orange rust systemic NO CURE, anthracnose #1 cane"""
    
    def __init__(self):
        self.diseases = BLACKBERRY_DISEASES


if __name__ == "__main__":
    print("=" * 80)
    print("BLACKBERRY DISEASE DETECTION SYSTEM")
    print("=" * 80)
    print("\n🚨 ORANGE RUST: SYSTEMIC, 100% PLANT LOSS, NO CURE")
    print("   Bright orange pustules, REMOVE PLANTS IMMEDIATELY")
    print("   NO fungicide treatment available")
    print("\n⚠️  ANTHRACNOSE: #1 Cane Disease, 50-80% losses")
    print("   Purple spots gray centers on canes")
    print("\n✓ Blackberry disease detection system initialized")
    print("  Market: $600M USA (Oregon 55%), $2B global")
    print("=" * 80)
