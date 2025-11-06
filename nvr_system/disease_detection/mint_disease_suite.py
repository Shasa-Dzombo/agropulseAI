"""
Mint Disease Detection Suite
=============================

Comprehensive disease identification for mint (Mentha spp.), high-value essential oil
crop with rust epidemic risk and vegetative propagation disease amplification.

Mint Species:
- Spearmint (M. spicata) - gum, candy, toothpaste
- Peppermint (M. × piperita) - essential oil, tea
- Apple mint - beverage, culinary
- Chocolate mint - specialty
- Pennyroyal - medicinal (toxic in large amounts)

Critical Diseases:
1. Mint Rust (Puccinia menthae) - #1 DISEASE, EPIDEMIC, PERENNIAL SURVIVAL
2. Verticillium Wilt (Verticillium dahliae) - SOILBORNE, 10+ YEARS
3. Rhizoctonia Root Rot - WEB BLIGHT, DAMPING-OFF
4. Fusarium Wilt - VASCULAR, PROPAGATION SPREADS
5. Alternaria Leaf Blight - DEFOLIATION
6. Powdery Mildew (Erysiphe biocellata) - LATE SEASON
7. Bacterial Soft Rot (Erwinia) - POSTHARVEST
8. Mint Anthracnose (Colletotrichum) - STEM CANKERS

Market Intelligence:
- USA production: $50 million, Pacific Northwest dominance
- Essential oil: $150-500/kg (peppermint), $200-600/kg (spearmint)
- Fresh mint: $8-16/lb retail, $4-8/lb wholesale
- Dried mint: $12-25/lb organic
- Vegetative propagation: Disease amplification risk (clones inherit infection)
- Perennial crop: 3-5 year stands, disease accumulates
- Rust epidemic: Can destroy 100% of crop, overwintering inoculum

Author: AgroPulse Team
Date: November 2025
"""

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional


class MintSpecies(Enum):
    """Mint species/varieties"""
    SPEARMINT = "spearmint"  # M. spicata
    PEPPERMINT = "peppermint"  # M. × piperita
    APPLE_MINT = "apple_mint"
    CHOCOLATE_MINT = "chocolate_mint"
    PENNYROYAL = "pennyroyal"


class MintProductType(Enum):
    """Mint product forms"""
    ESSENTIAL_OIL = "essential_oil"  # Distillation
    FRESH_LEAF = "fresh_leaf"  # Culinary
    DRIED_LEAF = "dried_leaf"  # Tea, spice
    EXTRACT = "extract"  # Flavor industry


class MintDisease(Enum):
    """Major mint diseases"""
    MINT_RUST = "mint_rust"
    VERTICILLIUM_WILT = "verticillium"
    RHIZOCTONIA_ROOT_ROT = "rhizoctonia"
    FUSARIUM_WILT = "fusarium"
    ALTERNARIA_BLIGHT = "alternaria"
    POWDERY_MILDEW = "powdery_mildew"
    BACTERIAL_SOFT_ROT = "soft_rot"
    MINT_ANTHRACNOSE = "anthracnose"


@dataclass
class MintDiseaseParams:
    """Disease parameters for mint"""
    disease: MintDisease
    pathogen: str
    severity: str
    yield_loss: Tuple[int, int]
    essential_oil_impact: str  # Critical for oil production
    
    # Symptoms
    leaf_symptoms: List[str]
    stem_symptoms: List[str]
    root_symptoms: List[str]
    diagnostic_features: str
    
    # Resistance
    resistant_cultivars: List[str]
    resistance_notes: str
    
    # Propagation considerations
    propagation_spread_risk: str  # Vegetative = disease amplification
    clean_stock_critical: bool
    
    # Control
    cultural_control: List[str]
    fungicide_control: List[str]
    stand_management: List[str]  # Perennial crop considerations
    
    # Economics
    market_impact: str
    treatment_cost_per_acre: float


# Disease database
MINT_DISEASES = {
    MintDisease.MINT_RUST: MintDiseaseParams(
        disease=MintDisease.MINT_RUST,
        pathogen="Puccinia menthae (OBLIGATE, perennial survival, epidemic)",
        severity="10/10 - #1 MINT DISEASE, EPIDEMIC, OVERWINTERS IN CROWNS",
        yield_loss=(50, 100),
        essential_oil_impact="CATASTROPHIC - 70-100% oil yield loss, quality destroyed",
        
        leaf_symptoms=[
            "Orange-yellow pustules on lower leaf surface DIAGNOSTIC",
            "Pustules contain orange powdery spores (urediniospores)",
            "Upper leaf surface shows chlorotic spots",
            "Pustules coalesce to cover entire leaf",
            "Premature leaf drop (complete defoliation)",
            "Black overwintering pustules (teliospores) form late season",
        ],
        
        stem_symptoms=[
            "Orange pustules on stems and petioles",
            "Stem distortion from infection",
        ],
        
        root_symptoms=[
            "Survives in rhizomes/crowns over winter",
        ],
        
        diagnostic_features="Orange pustules on leaf undersides, epidemic spread, overwinters",
        
        resistant_cultivars=[
            "Murray Mitcham (peppermint) - RESISTANT",
            "Scotch Spearmint - moderate resistance",
            "Native Spearmint - susceptible (avoid)",
            "Todd's Mitcham - resistant",
        ],
        resistance_notes="Resistance breeding successful, MUST use resistant cultivars",
        
        propagation_spread_risk="EXTREME - infected rootstock spreads to entire new planting",
        clean_stock_critical=True,
        
        cultural_control=[
            "PLANT RESISTANT CULTIVARS (Murray Mitcham, Todd's) ESSENTIAL",
            "CERTIFIED RUST-FREE PLANTING STOCK critical",
            "Inspect rootstock rigorously before planting",
            "Destroy infected fields (plow under)",
            "3-5 year rotation before replanting mint",
            "Remove volunteer mint plants (harbor rust)",
            "Fall cleanup removes overwintering inoculum",
            "Avoid overhead irrigation",
        ],
        
        fungicide_control=[
            "FRAC 3: Tebuconazole, myclobutanil - GOOD",
            "FRAC 11: Azoxystrobin - GOOD",
            "FRAC 7: Boscalid - moderate",
            "Begin at first pustule detection",
            "7-14 day intervals",
            "Preventative sprays critical",
            "CANNOT eradicate once established",
            "Fungicides reduce spread, don't cure",
        ],
        
        stand_management=[
            "Replant stand with resistant cultivar if rust severe",
            "Fall tillage to bury infected residue",
            "Spring emergence scouting CRITICAL",
            "Economic threshold: 1-2 pustules/plant = spray",
        ],
        
        market_impact="CATASTROPHIC - 70-100% essential oil loss, epidemic can destroy region",
        treatment_cost_per_acre=300.0
    ),
    
    MintDisease.VERTICILLIUM_WILT: MintDiseaseParams(
        disease=MintDisease.VERTICILLIUM_WILT,
        pathogen="Verticillium dahliae (SOILBORNE, 10-15 year survival, microsclerotia)",
        severity="10/10 - SOILBORNE, 10+ YEAR PERSISTENCE, STAND DECLINE",
        yield_loss=(40, 80),
        essential_oil_impact="Progressive stand decline, 40-80% oil loss over 2-3 years",
        
        leaf_symptoms=[
            "Yellowing starting from lower leaves",
            "Marginal leaf necrosis (browning edges)",
            "Leaves wilt during hot weather",
            "Progressive upward symptom development",
        ],
        
        stem_symptoms=[
            "Brown vascular streaks in cut stems DIAGNOSTIC",
            "One side of plant affected (sectoral wilt)",
            "Stem browning at soil line",
        ],
        
        root_symptoms=[
            "Root discoloration",
            "Vascular browning in rhizomes",
            "Progressive stand thinning",
        ],
        
        diagnostic_features="Vascular browning, sectoral wilt, progressive stand decline",
        
        resistant_cultivars=[
            "Murray Mitcham - VERTICILLIUM RESISTANT",
            "Todd's Mitcham - resistant",
            "Some spearmint varieties tolerant",
        ],
        resistance_notes="Resistance available but incomplete",
        
        propagation_spread_risk="HIGH - infected rootstock spreads disease to new fields",
        clean_stock_critical=True,
        
        cultural_control=[
            "CERTIFIED DISEASE-FREE ROOTSTOCK essential",
            "AVOID infested fields (10-15 year contamination)",
            "5+ year rotation to non-hosts",
            "Plant resistant cultivars",
            "Good weed control (weeds harbor pathogen)",
            "Fall tillage to promote microsclerotia germination",
        ],
        
        fungicide_control=[
            "NO EFFECTIVE fungicides",
            "Prevention through clean stock ONLY option",
        ],
        
        stand_management=[
            "Replant with resistant cultivar",
            "Avoid rotating to potatoes, tomatoes, eggplants (hosts)",
            "Economic threshold: 20% stand loss = replant",
        ],
        
        market_impact="Progressive yield decline, stand replacement costly",
        treatment_cost_per_acre=400.0  # Stand replacement
    ),
    
    MintDisease.RHIZOCTONIA_ROOT_ROT: MintDiseaseParams(
        disease=MintDisease.RHIZOCTONIA_ROOT_ROT,
        pathogen="Rhizoctonia solani (WEB BLIGHT, damping-off, soilborne)",
        severity="8/10 - DAMPING-OFF, WEB BLIGHT, SOILBORNE",
        yield_loss=(20, 50),
        essential_oil_impact="Stand thinning reduces oil yield 20-50%",
        
        leaf_symptoms=[
            "Wilting from root/crown damage",
            "Yellowing",
        ],
        
        stem_symptoms=[
            "Brown lesions at soil line",
            "Stem girdling causes plant death",
            "Web-like mycelium visible in humid weather",
        ],
        
        root_symptoms=[
            "Brown root rot",
            "Crown rot at soil line CRITICAL",
            "Damping-off of new shoots",
        ],
        
        diagnostic_features="Crown rot at soil line, web blight, damping-off",
        
        resistant_cultivars=[
            "Limited resistance",
        ],
        resistance_notes="No major resistance",
        
        propagation_spread_risk="MODERATE - can spread on infected rootstock",
        clean_stock_critical=True,
        
        cultural_control=[
            "Good drainage critical",
            "Avoid overwatering",
            "Raised beds in poorly drained soils",
            "Promote air circulation",
        ],
        
        fungicide_control=[
            "FRAC 7: Flutolanil, boscalid",
            "FRAC 11: Azoxystrobin",
            "Apply at planting or first symptoms",
        ],
        
        stand_management=[
            "Improve drainage urgently",
            "Thin stands if too dense",
        ],
        
        market_impact="Stand thinning, replant patches",
        treatment_cost_per_acre=250.0
    ),
    
    MintDisease.FUSARIUM_WILT: MintDiseaseParams(
        disease=MintDisease.FUSARIUM_WILT,
        pathogen="Fusarium oxysporum (vascular wilt, propagation spreads)",
        severity="8/10 - VASCULAR, PROPAGATION AMPLIFIES",
        yield_loss=(30, 60),
        essential_oil_impact="30-60% oil loss from wilted plants",
        
        leaf_symptoms=[
            "Wilting during hot weather",
            "Yellowing progressing upward",
        ],
        
        stem_symptoms=[
            "Brown vascular streaks in stems",
            "One-sided wilting (sectoral)",
        ],
        
        root_symptoms=[
            "Root discoloration",
            "Vascular browning",
        ],
        
        diagnostic_features="Vascular browning, wilting, propagation spreads",
        
        resistant_cultivars=[
            "Limited resistance",
        ],
        resistance_notes="Breeding for resistance ongoing",
        
        propagation_spread_risk="HIGH - vegetative propagation spreads disease",
        clean_stock_critical=True,
        
        cultural_control=[
            "Certified clean rootstock",
            "Avoid infested soils",
            "Rotation",
        ],
        
        fungicide_control=[
            "NO effective fungicides",
        ],
        
        stand_management=[
            "Replant with clean stock",
        ],
        
        market_impact="Scattered plant losses",
        treatment_cost_per_acre=300.0
    ),
}


@dataclass
class MintDiseaseResult:
    """Detection result for mint diseases"""
    disease: MintDisease
    confidence: float
    severity: str
    essential_oil_impact: str
    resistant_cultivars: List[str]
    immediate_actions: List[str]
    propagation_warning: str


class MintDiseaseDetector:
    """
    Mint disease detector
    
    CRITICAL FOCUS:
    - Mint rust: #1 epidemic disease, overwinters, resistant cultivars essential
    - Verticillium wilt: 10+ year soil contamination
    - Propagation disease amplification (vegetative = clonal spread)
    - Essential oil quality and yield
    - Perennial crop management (disease accumulation)
    """
    
    def __init__(self):
        self.diseases = MINT_DISEASES
    
    def detect_disease(self,
                      image: np.ndarray,
                      plant_part: str = "leaf",
                      mint_species: MintSpecies = MintSpecies.PEPPERMINT) -> List[MintDiseaseResult]:
        """
        Detect mint diseases
        
        Args:
            image: BGR image
            plant_part: "leaf", "stem", "root"
            mint_species: Mint species
        
        Returns:
            List of detected diseases
        """
        if image is None or image.size == 0:
            return []
        
        results = []
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        if plant_part == "leaf":
            # MINT RUST - CRITICAL
            rust_score = self._detect_orange_pustules(image, hsv)
            if rust_score > 0.3:  # Lower threshold - early detection critical
                results.append(self._create_result(
                    MintDisease.MINT_RUST,
                    rust_score,
                    mint_species,
                    alert="EPIDEMIC DISEASE"
                ))
            
            # Powdery mildew
            powdery_score = self._detect_white_powder(image, hsv)
            if powdery_score > 0.4:
                results.append(self._create_result(
                    MintDisease.POWDERY_MILDEW,
                    powdery_score,
                    mint_species
                ))
        
        elif plant_part == "stem":
            # Verticillium/Fusarium (vascular browning)
            vascular_score = self._detect_vascular_browning(image, hsv)
            if vascular_score > 0.5:
                results.append(self._create_result(
                    MintDisease.VERTICILLIUM_WILT,
                    vascular_score,
                    mint_species
                ))
        
        return sorted(results, key=lambda x: x.confidence, reverse=True)
    
    def _detect_orange_pustules(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect orange-yellow pustules (MINT RUST - CRITICAL)"""
        orange_lower = np.array([10, 100, 100])
        orange_upper = np.array([25, 255, 255])
        orange_mask = cv2.inRange(hsv, orange_lower, orange_upper)
        
        yellow_lower = np.array([20, 100, 100])
        yellow_upper = np.array([30, 255, 255])
        yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
        
        combined = cv2.bitwise_or(orange_mask, yellow_mask)
        coverage = np.sum(combined > 0) / combined.size
        
        return min(1.0, coverage * 25)  # High multiplier - critical disease
    
    def _detect_white_powder(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect white powder (powdery mildew)"""
        white_lower = np.array([0, 0, 200])
        white_upper = np.array([180, 50, 255])
        white_mask = cv2.inRange(hsv, white_lower, white_upper)
        
        coverage = np.sum(white_mask > 0) / white_mask.size
        return min(1.0, coverage * 20)
    
    def _detect_vascular_browning(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect vascular browning (Verticillium/Fusarium)"""
        brown_lower = np.array([10, 50, 30])
        brown_upper = np.array([25, 200, 150])
        brown_mask = cv2.inRange(hsv, brown_lower, brown_upper)
        
        coverage = np.sum(brown_mask > 0) / brown_mask.size
        return min(1.0, coverage * 18)
    
    def _create_result(self,
                      disease: MintDisease,
                      confidence: float,
                      mint_species: MintSpecies,
                      alert: str = "") -> MintDiseaseResult:
        """Create result with propagation warnings"""
        params = self.diseases[disease]
        
        if disease == MintDisease.MINT_RUST:
            severity = f"🚨 {alert} - {params.severity}"
            resistant = [
                "Murray Mitcham (peppermint) - RESISTANT",
                "Todd's Mitcham - resistant",
                "Scotch Spearmint - moderate"
            ]
            immediate = [
                "🚨 INSPECT ROOTSTOCK - Do not propagate from infected plants",
                "Plant resistant cultivars IMMEDIATELY",
                "Apply fungicide to remaining plants",
                "Remove severely infected plants",
                "Fall cleanup destroys overwintering inoculum",
            ]
            propagation_warn = "🚨 CRITICAL: DO NOT propagate from infected plants - rust spreads to ALL new plants"
            
        elif disease == MintDisease.VERTICILLIUM_WILT:
            severity = params.severity
            resistant = ["Murray Mitcham - resistant", "Todd's Mitcham - resistant"]
            immediate = [
                "Use certified disease-free rootstock",
                "Avoid infested fields (10+ year contamination)",
                "Replant with resistant cultivar",
            ]
            propagation_warn = "⚠️ Infected rootstock contaminates new plantings permanently"
            
        else:
            severity = params.severity
            resistant = params.resistant_cultivars[:3]
            immediate = params.cultural_control[:3]
            propagation_warn = params.propagation_spread_risk if params.clean_stock_critical else "Monitor rootstock"
        
        return MintDiseaseResult(
            disease=disease,
            confidence=confidence,
            severity=severity,
            essential_oil_impact=params.essential_oil_impact,
            resistant_cultivars=resistant,
            immediate_actions=immediate,
            propagation_warning=propagation_warn
        )


# Example usage
if __name__ == "__main__":
    print("Mint Disease Detection System")
    print("=" * 70)
    
    detector = MintDiseaseDetector()
    
    print("\n📚 MINT DISEASE DATABASE:")
    print("\n🚨 CRITICAL: MINT RUST (Epidemic Disease)")
    rust = MINT_DISEASES[MintDisease.MINT_RUST]
    print(f"  Pathogen: {rust.pathogen}")
    print(f"  Severity: {rust.severity}")
    print(f"  Oil impact: {rust.essential_oil_impact}")
    print(f"  Resistant: {', '.join(rust.resistant_cultivars[:3])}")
    
    print("\n⚠️  VERTICILLIUM WILT (10+ Year Contamination)")
    vert = MINT_DISEASES[MintDisease.VERTICILLIUM_WILT]
    print(f"  Pathogen: {vert.pathogen}")
    print(f"  Persistence: 10-15 years in soil")
    
    print("\n🚨 PROPAGATION WARNING:")
    print("  Vegetative propagation spreads diseases to ALL new plants")
    print("  MUST use certified disease-free rootstock")
    print("  Mint rust + Verticillium can destroy entire plantings")
    
    print("\n✓ Mint disease detection system initialized")
    print("  Focus: Rust epidemic, Verticillium persistence, propagation risks")
    print("  Market: $50M USA, essential oil $150-600/kg, perennial 3-5 years")
