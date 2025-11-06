"""
Thyme Disease Detection Suite
==============================

Comprehensive disease identification for thyme (Thymus vulgaris and related species),
premium Mediterranean herb with gray mold postharvest dominance and root rot challenges.

Thyme Species:
- Common thyme (T. vulgaris) - culinary standard
- Lemon thyme (T. × citriodorus) - citrus notes
- Creeping thyme (T. serpyllum) - ground cover
- Caraway thyme - unique flavor
- Woolly thyme - ornamental

Critical Diseases:
1. Botrytis Gray Mold (Botrytis cinerea) - #1 POSTHARVEST, GREENHOUSE
2. Alternaria Leaf Blight - DEFOLIATION, EPIDEMIC
3. Rhizoctonia Root Rot - DAMPING-OFF, SOILBORNE
4. Fusarium Root Rot - WATERLOGGING
5. Pythium Root Rot - POOR DRAINAGE
6. Bacterial Soft Rot (Erwinia) - POSTHARVEST
7. Powdery Mildew (Erysiphe spp.) - GREENHOUSE
8. Cercospora Leaf Spot - LATE SEASON

Market Intelligence:
- USA production: $30 million, Mediterranean climate zones
- Fresh thyme: $12-18/lb retail, $6-10/lb wholesale
- Dried thyme: $18-35/lb organic
- Essential oil: $100-250/kg (thymol content 30-50% optimal)
- Postharvest loss: 20-40% from Botrytis if uncontrolled
- Cutting propagation: 80% of commercial, disease spread
- Cold storage: 32-36°F, 95% RH, 2-3 week shelf life

Author: AgroPulse Team
Date: November 2025
"""

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional


class ThymeSpecies(Enum):
    """Thyme species/varieties"""
    COMMON = "common"  # T. vulgaris
    LEMON = "lemon"  # T. × citriodorus
    CREEPING = "creeping"  # T. serpyllum
    CARAWAY = "caraway"
    WOOLLY = "woolly"


class ThymeDisease(Enum):
    """Major thyme diseases"""
    BOTRYTIS_GRAY_MOLD = "botrytis"
    ALTERNARIA_BLIGHT = "alternaria"
    RHIZOCTONIA_ROOT_ROT = "rhizoctonia"
    FUSARIUM_ROOT_ROT = "fusarium"
    PYTHIUM_ROOT_ROT = "pythium"
    BACTERIAL_SOFT_ROT = "soft_rot"
    POWDERY_MILDEW = "powdery_mildew"
    CERCOSPORA_LEAF_SPOT = "cercospora"


@dataclass
class ThymeDiseaseParams:
    """Disease parameters for thyme"""
    disease: ThymeDisease
    pathogen: str
    severity: str
    field_yield_loss: Tuple[int, int]
    postharvest_loss: Tuple[int, int]  # Critical for thyme
    essential_oil_impact: str
    
    # Symptoms
    leaf_symptoms: List[str]
    stem_symptoms: List[str]
    root_symptoms: List[str]
    diagnostic_features: str
    
    # Postharvest critical
    postharvest_conditions: str
    storage_recommendations: str
    
    # Control
    cultural_control: List[str]
    fungicide_control: List[str]
    postharvest_control: List[str]
    
    # Economics
    market_impact: str
    treatment_cost_per_acre: float


# Disease database
THYME_DISEASES = {
    ThymeDisease.BOTRYTIS_GRAY_MOLD: ThymeDiseaseParams(
        disease=ThymeDisease.BOTRYTIS_GRAY_MOLD,
        pathogen="Botrytis cinerea (#1 POSTHARVEST DISEASE, cold storage epidemic)",
        severity="10/10 - #1 POSTHARVEST LOSS, 20-40% WASTE",
        field_yield_loss=(10, 30),
        postharvest_loss=(20, 40),
        essential_oil_impact="Moldy product unusable, 20-40% loss",
        
        leaf_symptoms=[
            "Gray fuzzy mold growth DIAGNOSTIC",
            "Water-soaked brown lesions",
            "Leaf blight starting from tips",
            "Rapid spread in humid/cold storage",
        ],
        
        stem_symptoms=[
            "Stem blight with gray sporulation",
            "Stem cankers",
        ],
        
        root_symptoms=[],
        
        diagnostic_features="Gray fuzzy mold, high humidity, postharvest",
        
        postharvest_conditions="CRITICAL: Develops rapidly in cold storage (32-36°F, 95% RH)",
        storage_recommendations="Pre-cooling, air circulation, <95% RH, rapid turnover",
        
        cultural_control=[
            "Harvest in morning when dry",
            "Avoid harvesting wet foliage",
            "Pre-cool immediately after harvest",
            "Cold storage with air circulation",
            "High humidity (95% RH) but good air flow",
            "Rapid market turnover (2-3 weeks max)",
        ],
        
        fungicide_control=[
            "PRE-HARVEST applications critical:",
            "FRAC 7: Boscalid (Endura)",
            "FRAC 9: Cyprodinil + fludioxonil (Switch)",
            "FRAC 17: Fenhexamid (Decree)",
            "Apply 1-3 days before harvest",
            "Observe PHI (pre-harvest intervals)",
        ],
        
        postharvest_control=[
            "Pre-cooling to 32-36°F within 2 hours",
            "Forced air cooling systems",
            "Maintain 90-95% RH (not >95%)",
            "Air circulation in storage",
            "Inspect daily, remove infected bunches",
            "Chlorine dioxide fumigation (research stage)",
        ],
        
        market_impact="CATASTROPHIC - #1 postharvest loss, 20-40% waste",
        treatment_cost_per_acre=200.0
    ),
    
    ThymeDisease.ALTERNARIA_BLIGHT: ThymeDiseaseParams(
        disease=ThymeDisease.ALTERNARIA_BLIGHT,
        pathogen="Alternaria spp. (defoliation epidemic, warm humid weather)",
        severity="9/10 - DEFOLIATION EPIDEMIC",
        field_yield_loss=(30, 60),
        postharvest_loss=(10, 20),
        essential_oil_impact="30-60% yield loss from defoliation",
        
        leaf_symptoms=[
            "Circular to irregular brown spots",
            "Target-ring pattern on spots",
            "Spots enlarge and coalesce",
            "Premature leaf drop",
            "Can cause complete defoliation",
        ],
        
        stem_symptoms=[
            "Brown stem lesions",
        ],
        
        root_symptoms=[],
        
        diagnostic_features="Target-ring spots, defoliation, warm humid weather",
        
        postharvest_conditions="Minor postharvest issue (field disease primary)",
        storage_recommendations="Standard cold storage adequate",
        
        cultural_control=[
            "Good air circulation",
            "Avoid overhead irrigation",
            "Remove crop residues",
            "2-3 year rotation",
        ],
        
        fungicide_control=[
            "FRAC 7: Boscalid (Endura)",
            "FRAC 11: Azoxystrobin, pyraclostrobin",
            "FRAC 3: Difenoconazole",
            "7-14 day intervals",
            "Begin at first spots",
        ],
        
        postharvest_control=[
            "Standard cold storage",
        ],
        
        market_impact="Field yield loss, defoliation",
        treatment_cost_per_acre=180.0
    ),
    
    ThymeDisease.RHIZOCTONIA_ROOT_ROT: ThymeDiseaseParams(
        disease=ThymeDisease.RHIZOCTONIA_ROOT_ROT,
        pathogen="Rhizoctonia solani (damping-off, soilborne)",
        severity="8/10 - DAMPING-OFF, SEEDLING LOSS",
        field_yield_loss=(20, 50),
        postharvest_loss=(0, 0),
        essential_oil_impact="Stand loss reduces total yield 20-50%",
        
        leaf_symptoms=[
            "Wilting from root damage",
        ],
        
        stem_symptoms=[
            "Brown lesions at soil line",
            "Stem girdling",
            "Damping-off of seedlings/cuttings",
        ],
        
        root_symptoms=[
            "Brown root rot",
            "Crown rot at soil line",
        ],
        
        diagnostic_features="Crown rot at soil line, damping-off, soilborne",
        
        postharvest_conditions="Not applicable (field disease)",
        storage_recommendations="Not applicable",
        
        cultural_control=[
            "Good drainage",
            "Avoid overwatering",
            "Raised beds in poorly drained sites",
            "Pasteurized propagation media",
        ],
        
        fungicide_control=[
            "FRAC 7: Flutolanil at planting",
            "FRAC 11: Azoxystrobin",
            "Apply at planting or first symptoms",
        ],
        
        postharvest_control=[],
        
        market_impact="Stand establishment issues",
        treatment_cost_per_acre=200.0
    ),
    
    ThymeDisease.FUSARIUM_ROOT_ROT: ThymeDiseaseParams(
        disease=ThymeDisease.FUSARIUM_ROOT_ROT,
        pathogen="Fusarium spp. (waterlogging, poor drainage)",
        severity="8/10 - WATERLOGGING DISEASE",
        field_yield_loss=(30, 70),
        postharvest_loss=(0, 0),
        essential_oil_impact="Plant death = yield loss",
        
        leaf_symptoms=[
            "Yellowing",
            "Wilting",
        ],
        
        stem_symptoms=[
            "Brown vascular streaks",
            "Stem browning at soil line",
        ],
        
        root_symptoms=[
            "Brown root rot",
            "Vascular discoloration",
        ],
        
        diagnostic_features="Vascular browning, waterlogging history",
        
        postharvest_conditions="Not applicable",
        storage_recommendations="Not applicable",
        
        cultural_control=[
            "DRAINAGE CRITICAL (Mediterranean herb)",
            "Avoid waterlogging",
            "Raised beds",
            "Reduce irrigation frequency",
        ],
        
        fungicide_control=[
            "Limited efficacy",
            "Prevention through drainage",
        ],
        
        postharvest_control=[],
        
        market_impact="Plant death in poorly drained sites",
        treatment_cost_per_acre=250.0
    ),
}


@dataclass
class ThymeDiseaseResult:
    """Detection result for thyme diseases"""
    disease: ThymeDisease
    confidence: float
    severity: str
    postharvest_risk: str
    immediate_actions: List[str]
    harvest_recommendations: List[str]
    storage_protocols: List[str]


class ThymeDiseaseDetector:
    """
    Thyme disease detector
    
    CRITICAL FOCUS:
    - Botrytis gray mold: #1 postharvest loss (20-40%)
    - Pre-harvest fungicide timing
    - Cold storage management
    - Root rot from overwatering (Mediterranean herb)
    """
    
    def __init__(self):
        self.diseases = THYME_DISEASES
    
    def detect_disease(self,
                      image: np.ndarray,
                      plant_part: str = "leaf",
                      stage: str = "field",
                      days_to_harvest: Optional[int] = None) -> List[ThymeDiseaseResult]:
        """
        Detect thyme diseases
        
        Args:
            image: BGR image
            plant_part: "leaf", "stem", "root"
            stage: "field", "postharvest", "storage"
            days_to_harvest: Days until harvest (for fungicide PHI)
        
        Returns:
            List of detected diseases with postharvest emphasis
        """
        if image is None or image.size == 0:
            return []
        
        results = []
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        if plant_part == "leaf":
            # BOTRYTIS - CRITICAL POSTHARVEST
            botrytis_score = self._detect_gray_fuzzy_mold(image, hsv)
            if botrytis_score > 0.3:
                results.append(self._create_result(
                    ThymeDisease.BOTRYTIS_GRAY_MOLD,
                    botrytis_score,
                    stage,
                    days_to_harvest
                ))
            
            # Alternaria (target rings)
            alternaria_score = self._detect_target_rings(image, hsv)
            if alternaria_score > 0.4:
                results.append(self._create_result(
                    ThymeDisease.ALTERNARIA_BLIGHT,
                    alternaria_score,
                    stage,
                    days_to_harvest
                ))
        
        elif plant_part == "root":
            # Root rots
            root_rot_score = self._detect_brown_roots(image, hsv)
            if root_rot_score > 0.5:
                results.append(self._create_result(
                    ThymeDisease.RHIZOCTONIA_ROOT_ROT,
                    root_rot_score,
                    stage,
                    days_to_harvest
                ))
        
        return sorted(results, key=lambda x: x.confidence, reverse=True)
    
    def _detect_gray_fuzzy_mold(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect gray fuzzy mold (Botrytis) - CRITICAL POSTHARVEST"""
        gray_lower = np.array([0, 0, 80])
        gray_upper = np.array([180, 50, 180])
        gray_mask = cv2.inRange(hsv, gray_lower, gray_upper)
        
        coverage = np.sum(gray_mask > 0) / gray_mask.size
        return min(1.0, coverage * 25)  # High multiplier - critical disease
    
    def _detect_target_rings(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect target-ring spots (Alternaria)"""
        brown_lower = np.array([10, 50, 40])
        brown_upper = np.array([25, 200, 150])
        brown_mask = cv2.inRange(hsv, brown_lower, brown_upper)
        
        coverage = np.sum(brown_mask > 0) / brown_mask.size
        return min(1.0, coverage * 18)
    
    def _detect_brown_roots(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect brown root rot"""
        brown_lower = np.array([10, 50, 30])
        brown_upper = np.array([25, 200, 150])
        brown_mask = cv2.inRange(hsv, brown_lower, brown_upper)
        
        coverage = np.sum(brown_mask > 0) / brown_mask.size
        return min(1.0, coverage * 15)
    
    def _create_result(self,
                      disease: ThymeDisease,
                      confidence: float,
                      stage: str,
                      days_to_harvest: Optional[int]) -> ThymeDiseaseResult:
        """Create result with postharvest emphasis"""
        params = self.diseases[disease]
        
        if disease == ThymeDisease.BOTRYTIS_GRAY_MOLD:
            severity = f"🚨 CRITICAL POSTHARVEST - {params.severity}"
            postharvest = f"HIGH RISK: {params.postharvest_loss[0]}-{params.postharvest_loss[1]}% postharvest loss"
            
            if stage == "field" and days_to_harvest and days_to_harvest <= 3:
                immediate = [
                    "Apply pre-harvest fungicide NOW (within 1-3 days of harvest)",
                    "Boscalid or Switch (observe PHI)",
                    "Harvest in morning when dry",
                    "Pre-cool within 2 hours",
                ]
            elif stage == "postharvest":
                immediate = [
                    "Remove infected bunches immediately",
                    "Improve cold storage air circulation",
                    "Check humidity (should be 90-95%, not >95%)",
                    "Rapid market turnover",
                ]
            else:
                immediate = params.cultural_control[:3]
            
            harvest = [
                "Harvest in morning when foliage dry",
                "Avoid harvesting wet plants",
                "Pre-harvest fungicide 1-3 days before",
            ]
            
            storage = [
                "Pre-cool to 32-36°F within 2 hours",
                "Forced air cooling system",
                "Maintain 90-95% RH with air circulation",
                "Inspect daily, remove infected bunches",
                "2-3 week maximum storage",
            ]
            
        elif disease == ThymeDisease.ALTERNARIA_BLIGHT:
            severity = params.severity
            postharvest = f"Minor postharvest risk: {params.postharvest_loss[0]}-{params.postharvest_loss[1]}%"
            immediate = [
                "Apply fungicide immediately",
                "7-14 day intervals",
                "Remove infected leaves",
            ]
            harvest = ["Harvest before severe defoliation"]
            storage = ["Standard cold storage adequate"]
            
        else:
            severity = params.severity
            postharvest = f"Field disease, postharvest loss: {params.postharvest_loss[0]}-{params.postharvest_loss[1]}%"
            immediate = params.cultural_control[:3]
            harvest = ["Standard harvest protocols"]
            storage = ["Standard cold storage"]
        
        return ThymeDiseaseResult(
            disease=disease,
            confidence=confidence,
            severity=severity,
            postharvest_risk=postharvest,
            immediate_actions=immediate,
            harvest_recommendations=harvest,
            storage_protocols=storage
        )


# Example usage
if __name__ == "__main__":
    print("Thyme Disease Detection System")
    print("=" * 70)
    
    detector = ThymeDiseaseDetector()
    
    print("\n📚 THYME DISEASE DATABASE:")
    print("\n🚨 CRITICAL: BOTRYTIS GRAY MOLD (#1 Postharvest Loss)")
    botrytis = THYME_DISEASES[ThymeDisease.BOTRYTIS_GRAY_MOLD]
    print(f"  Pathogen: {botrytis.pathogen}")
    print(f"  Severity: {botrytis.severity}")
    print(f"  Postharvest loss: {botrytis.postharvest_loss[0]}-{botrytis.postharvest_loss[1]}%")
    print(f"  Storage conditions: {botrytis.postharvest_conditions}")
    
    print("\n📦 POSTHARVEST MANAGEMENT:")
    print("  Pre-cooling: 32-36°F within 2 hours of harvest")
    print("  Storage: 32-36°F, 90-95% RH, air circulation")
    print("  Shelf life: 2-3 weeks maximum")
    print("  Pre-harvest fungicide: 1-3 days before harvest CRITICAL")
    
    print("\n✓ Thyme disease detection system initialized")
    print("  Focus: Botrytis postharvest control, cold storage management")
    print("  Market: $30M USA, fresh $12-18/lb, essential oil $100-250/kg")
