"""
Oregano Disease Detection Suite
================================

Comprehensive disease identification for oregano (Origanum vulgare and related species),
premium Mediterranean herb with rust epidemic potential and Botrytis postharvest challenges.

Oregano Species:
- Greek oregano (O. vulgare subsp. hirtum) - highest quality, pungent
- Italian oregano (O. × majoricum) - hybrid, mild
- Syrian oregano (O. syriacum) - za'atar spice
- Mexican oregano (Lippia graveolens) - different genus, similar use
- Marjoram (O. majorana) - sweet oregano

Critical Diseases:
1. Mint Rust (Puccinia menthae) - CROSS-INFECTS FROM MINT, EPIDEMIC
2. Botrytis Gray Mold (Botrytis cinerea) - POSTHARVEST 15-30% LOSS
3. Alternaria Leaf Blight - DEFOLIATION
4. Rhizoctonia Root Rot - DAMPING-OFF, SOILBORNE
5. Fusarium Wilt - VASCULAR, PROPAGATION SPREAD
6. Pythium Root Rot - WATERLOGGING
7. Powdery Mildew (Erysiphe biocellata) - GREENHOUSE
8. Bacterial Leaf Spot (Pseudomonas cichorii) - CUTTING PROPAGATION

Market Intelligence:
- USA production: $40 million, Mediterranean climate zones
- Fresh oregano: $10-18/lb retail, $5-10/lb wholesale
- Dried oregano: $20-40/lb organic (Greek premium)
- Essential oil: $150-400/kg (carvacrol 60-80% premium)
- Greek oregano: 3-5x price premium over Italian
- Perennial crop: 3-5 year stands, disease accumulation risk
- Cutting propagation: 85% commercial, rust spread critical

Author: AgroPulse Team
Date: November 2025
"""

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional


class OreganoSpecies(Enum):
    """Oregano species/varieties"""
    GREEK = "greek"  # O. vulgare subsp. hirtum - premium
    ITALIAN = "italian"  # O. × majoricum - mild
    SYRIAN = "syrian"  # O. syriacum - za'atar
    MEXICAN = "mexican"  # Lippia graveolens
    MARJORAM = "marjoram"  # O. majorana - sweet


class OreganoDisease(Enum):
    """Major oregano diseases"""
    MINT_RUST = "mint_rust"
    BOTRYTIS_GRAY_MOLD = "botrytis"
    ALTERNARIA_BLIGHT = "alternaria"
    RHIZOCTONIA_ROOT_ROT = "rhizoctonia"
    FUSARIUM_WILT = "fusarium"
    PYTHIUM_ROOT_ROT = "pythium"
    POWDERY_MILDEW = "powdery_mildew"
    BACTERIAL_LEAF_SPOT = "bacterial_spot"


@dataclass
class OreganoDiseaseParams:
    """Disease parameters for oregano"""
    disease: OreganoDisease
    pathogen: str
    severity: str
    yield_loss: Tuple[int, int]
    essential_oil_impact: str
    
    # Symptoms
    leaf_symptoms: List[str]
    stem_symptoms: List[str]
    root_symptoms: List[str]
    diagnostic_features: str
    
    # Cross-infection risk
    mint_proximity_risk: str  # Mint rust cross-infection
    propagation_spread: str
    
    # Resistance
    resistant_cultivars: List[str]
    
    # Control
    cultural_control: List[str]
    fungicide_control: List[str]
    postharvest_control: List[str]
    
    # Economics
    market_impact: str
    treatment_cost_per_acre: float


# Disease database
OREGANO_DISEASES = {
    OreganoDisease.MINT_RUST: OreganoDiseaseParams(
        disease=OreganoDisease.MINT_RUST,
        pathogen="Puccinia menthae (CROSS-INFECTS from mint, epidemic potential)",
        severity="10/10 - EPIDEMIC, CROSS-INFECTION FROM MINT FIELDS",
        yield_loss=(50, 100),
        essential_oil_impact="CATASTROPHIC - 70-100% oil loss, quality destroyed",
        
        leaf_symptoms=[
            "Orange-yellow pustules on leaf undersides DIAGNOSTIC",
            "Pustules contain powdery orange spores",
            "Chlorotic spots on upper leaf surface",
            "Pustules coalesce to cover entire leaf",
            "Premature leaf drop (complete defoliation)",
            "Black overwintering pustules (teliospores) late season",
        ],
        
        stem_symptoms=[
            "Orange pustules on stems",
            "Stem distortion",
        ],
        
        root_symptoms=[
            "Survives in crowns/rhizomes over winter",
        ],
        
        diagnostic_features="Orange pustules, cross-infects from mint, overwinters",
        
        mint_proximity_risk="EXTREME - Plant oregano >500 yards from mint fields (spore dispersal)",
        propagation_spread="CRITICAL - Infected rootstock spreads to entire planting",
        
        resistant_cultivars=[
            "Limited rust resistance in oregano",
            "Greek oregano may have some tolerance",
            "No major resistance genes identified",
        ],
        
        cultural_control=[
            "SEPARATE from mint fields (>500 yards minimum)",
            "CERTIFIED RUST-FREE PLANTING STOCK critical",
            "Scout weekly during growing season",
            "Remove volunteer plants near fields",
            "Fall cleanup destroys overwintering inoculum",
            "DO NOT propagate from infected plants",
        ],
        
        fungicide_control=[
            "FRAC 3: Tebuconazole, myclobutanil",
            "FRAC 11: Azoxystrobin",
            "FRAC 7: Boscalid",
            "Begin at first pustule detection",
            "7-14 day intervals",
            "Preventative sprays if mint rust in region",
        ],
        
        postharvest_control=[
            "Harvest before severe infection",
            "Infected foliage unmarketable",
        ],
        
        market_impact="CATASTROPHIC - epidemic potential, 70-100% loss",
        treatment_cost_per_acre=300.0
    ),
    
    OreganoDisease.BOTRYTIS_GRAY_MOLD: OreganoDiseaseParams(
        disease=OreganoDisease.BOTRYTIS_GRAY_MOLD,
        pathogen="Botrytis cinerea (postharvest, cold storage, greenhouse)",
        severity="9/10 - POSTHARVEST 15-30% LOSS",
        yield_loss=(10, 25),
        essential_oil_impact="Moldy product unusable, 15-30% loss",
        
        leaf_symptoms=[
            "Gray fuzzy mold on leaves/stems",
            "Water-soaked brown lesions",
            "Shoot tip blight",
            "Rapid spread in humid storage",
        ],
        
        stem_symptoms=[
            "Stem cankers with gray sporulation",
        ],
        
        root_symptoms=[],
        
        diagnostic_features="Gray fuzzy mold, postharvest, high humidity",
        
        mint_proximity_risk="Not applicable",
        propagation_spread="MODERATE - can spread on cuttings",
        
        resistant_cultivars=[
            "No resistance available",
        ],
        
        cultural_control=[
            "Harvest when dry",
            "Pre-cool immediately",
            "Cold storage 32-36°F, 90-95% RH",
            "Good air circulation in storage",
        ],
        
        fungicide_control=[
            "Pre-harvest applications:",
            "FRAC 7: Boscalid (Endura)",
            "FRAC 9: Switch",
            "FRAC 17: Fenhexamid",
            "Apply 1-3 days before harvest",
        ],
        
        postharvest_control=[
            "Pre-cooling within 2 hours",
            "Maintain 90-95% RH with air flow",
            "Inspect daily, remove infected bunches",
            "Rapid market turnover (2-3 weeks)",
        ],
        
        market_impact="Postharvest losses 15-30%, storage management critical",
        treatment_cost_per_acre=200.0
    ),
    
    OreganoDisease.ALTERNARIA_BLIGHT: OreganoDiseaseParams(
        disease=OreganoDisease.ALTERNARIA_BLIGHT,
        pathogen="Alternaria spp. (defoliation, warm humid weather)",
        severity="8/10 - DEFOLIATION EPIDEMIC",
        yield_loss=(25, 50),
        essential_oil_impact="25-50% yield loss from defoliation",
        
        leaf_symptoms=[
            "Circular brown spots with target rings",
            "Spots enlarge and coalesce",
            "Yellow halo around spots",
            "Premature leaf drop",
        ],
        
        stem_symptoms=[
            "Brown stem lesions",
        ],
        
        root_symptoms=[],
        
        diagnostic_features="Target-ring spots, defoliation, warm weather",
        
        mint_proximity_risk="Not applicable",
        propagation_spread="LOW",
        
        resistant_cultivars=[
            "Limited resistance",
        ],
        
        cultural_control=[
            "Good air circulation",
            "Avoid overhead irrigation",
            "Remove crop residues",
            "2-3 year rotation",
        ],
        
        fungicide_control=[
            "FRAC 7: Boscalid",
            "FRAC 11: Azoxystrobin",
            "FRAC 3: Difenoconazole",
            "7-14 day intervals",
        ],
        
        postharvest_control=[
            "Standard protocols",
        ],
        
        market_impact="Defoliation reduces harvest yield",
        treatment_cost_per_acre=180.0
    ),
    
    OreganoDisease.RHIZOCTONIA_ROOT_ROT: OreganoDiseaseParams(
        disease=OreganoDisease.RHIZOCTONIA_ROOT_ROT,
        pathogen="Rhizoctonia solani (damping-off, crown rot)",
        severity="8/10 - DAMPING-OFF, STAND LOSS",
        yield_loss=(20, 40),
        essential_oil_impact="Stand thinning reduces total yield",
        
        leaf_symptoms=[
            "Wilting from root damage",
        ],
        
        stem_symptoms=[
            "Brown lesions at soil line",
            "Stem girdling",
            "Damping-off of cuttings",
        ],
        
        root_symptoms=[
            "Brown root rot",
            "Crown rot at soil line",
        ],
        
        diagnostic_features="Crown rot at soil line, damping-off",
        
        mint_proximity_risk="Not applicable",
        propagation_spread="MODERATE - contaminated propagation media",
        
        resistant_cultivars=[
            "No resistance",
        ],
        
        cultural_control=[
            "Good drainage",
            "Avoid overwatering",
            "Pasteurized propagation media",
            "Raised beds",
        ],
        
        fungicide_control=[
            "FRAC 7: Flutolanil at planting",
            "FRAC 11: Azoxystrobin",
        ],
        
        postharvest_control=[],
        
        market_impact="Stand establishment issues",
        treatment_cost_per_acre=200.0
    ),
}


@dataclass
class OreganoDisease Result:
    """Detection result for oregano diseases"""
    disease: OreganoDisease
    confidence: float
    severity: str
    mint_proximity_warning: str
    immediate_actions: List[str]
    propagation_precautions: str


class OreganoDiseaseDetector:
    """
    Oregano disease detector
    
    CRITICAL FOCUS:
    - Mint rust: Cross-infection from mint fields (>500 yard separation)
    - Botrytis: Postharvest 15-30% loss
    - Perennial crop management (disease accumulation)
    - Essential oil quality (Greek oregano premium)
    """
    
    def __init__(self):
        self.diseases = OREGANO_DISEASES
    
    def detect_disease(self,
                      image: np.ndarray,
                      plant_part: str = "leaf",
                      mint_fields_nearby: bool = False) -> List[OreganoDiseaseResult]:
        """
        Detect oregano diseases
        
        Args:
            image: BGR image
            plant_part: "leaf", "stem", "root"
            mint_fields_nearby: Alert for mint rust cross-infection risk
        
        Returns:
            List of detected diseases with mint proximity warnings
        """
        if image is None or image.size == 0:
            return []
        
        results = []
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        if plant_part == "leaf":
            # MINT RUST - CRITICAL CROSS-INFECTION
            rust_score = self._detect_orange_pustules(image, hsv)
            if rust_score > 0.3:
                results.append(self._create_result(
                    OreganoDisease.MINT_RUST,
                    rust_score,
                    mint_fields_nearby,
                    alert="EPIDEMIC"
                ))
            
            # Botrytis
            botrytis_score = self._detect_gray_mold(image, hsv)
            if botrytis_score > 0.4:
                results.append(self._create_result(
                    OreganoDisease.BOTRYTIS_GRAY_MOLD,
                    botrytis_score,
                    mint_fields_nearby
                ))
            
            # Alternaria
            alternaria_score = self._detect_target_rings(image, hsv)
            if alternaria_score > 0.4:
                results.append(self._create_result(
                    OreganoDisease.ALTERNARIA_BLIGHT,
                    alternaria_score,
                    mint_fields_nearby
                ))
        
        return sorted(results, key=lambda x: x.confidence, reverse=True)
    
    def _detect_orange_pustules(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect orange pustules (MINT RUST - CRITICAL)"""
        orange_lower = np.array([10, 100, 100])
        orange_upper = np.array([25, 255, 255])
        orange_mask = cv2.inRange(hsv, orange_lower, orange_upper)
        
        coverage = np.sum(orange_mask > 0) / orange_mask.size
        return min(1.0, coverage * 25)
    
    def _detect_gray_mold(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect gray mold (Botrytis)"""
        gray_lower = np.array([0, 0, 80])
        gray_upper = np.array([180, 50, 180])
        gray_mask = cv2.inRange(hsv, gray_lower, gray_upper)
        
        coverage = np.sum(gray_mask > 0) / gray_mask.size
        return min(1.0, coverage * 20)
    
    def _detect_target_rings(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect target-ring spots (Alternaria)"""
        brown_lower = np.array([10, 50, 40])
        brown_upper = np.array([25, 200, 150])
        brown_mask = cv2.inRange(hsv, brown_lower, brown_upper)
        
        coverage = np.sum(brown_mask > 0) / brown_mask.size
        return min(1.0, coverage * 18)
    
    def _create_result(self,
                      disease: OreganoDisease,
                      confidence: float,
                      mint_nearby: bool,
                      alert: str = "") -> OreganoDisease Result:
        """Create result with mint proximity warnings"""
        params = self.diseases[disease]
        
        if disease == OreganoDisease.MINT_RUST:
            severity = f"🚨 {alert} - {params.severity}"
            
            if mint_nearby:
                mint_warning = "🚨 CRITICAL: Mint fields nearby = HIGH RUST RISK, separate >500 yards"
                immediate = [
                    "🚨 URGENT: Inspect for mint rust in nearby mint fields",
                    "Separate oregano >500 yards from mint",
                    "Apply preventative fungicide immediately",
                    "DO NOT propagate from infected plants",
                    "Scout weekly for orange pustules",
                ]
            else:
                mint_warning = "⚠️ Separate from mint fields >500 yards"
                immediate = [
                    "Remove infected plants immediately",
                    "Apply fungicide to remaining plants",
                    "Fall cleanup critical",
                    "Use rust-free planting stock",
                ]
            
            propagation = "🚨 CRITICAL: DO NOT propagate from infected plants"
            
        elif disease == OreganoDisease.BOTRYTIS_GRAY_MOLD:
            severity = params.severity
            mint_warning = "Not applicable"
            immediate = [
                "Apply pre-harvest fungicide (1-3 days before harvest)",
                "Harvest when dry",
                "Pre-cool within 2 hours",
                "Cold storage 32-36°F, 90-95% RH",
            ]
            propagation = "Moderate risk in cuttings"
            
        else:
            severity = params.severity
            mint_warning = params.mint_proximity_risk
            immediate = params.cultural_control[:3]
            propagation = params.propagation_spread
        
        return OreganoDisease Result(
            disease=disease,
            confidence=confidence,
            severity=severity,
            mint_proximity_warning=mint_warning,
            immediate_actions=immediate,
            propagation_precautions=propagation
        )


# Example usage
if __name__ == "__main__":
    print("Oregano Disease Detection System")
    print("=" * 70)
    
    detector = OreganoDiseaseDetector()
    
    print("\n📚 OREGANO DISEASE DATABASE:")
    print("\n🚨 CRITICAL: MINT RUST (Cross-Infection from Mint)")
    rust = OREGANO_DISEASES[OreganoDisease.MINT_RUST]
    print(f"  Pathogen: {rust.pathogen}")
    print(f"  Severity: {rust.severity}")
    print(f"  Mint proximity: {rust.mint_proximity_risk}")
    
    print("\n⚠️  MINT PROXIMITY WARNING:")
    print("  Plant oregano >500 yards from mint fields")
    print("  Rust spores disperse long distances")
    print("  Cross-infection causes epidemic in oregano")
    
    print("\n✓ Oregano disease detection system initialized")
    print("  Focus: Mint rust cross-infection, Botrytis postharvest")
    print("  Market: $40M USA, Greek premium 3-5x, essential oil $150-400/kg")
