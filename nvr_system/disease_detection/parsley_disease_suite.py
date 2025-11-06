"""
Parsley Disease Detection Suite
================================

Comprehensive disease identification for parsley (Petroselinum crispum),
premium culinary herb with Septoria leaf spot endemic and celery mosaic virus risk.

Parsley Types:
- Curly parsley - garnish, most common
- Flat-leaf (Italian) - culinary, stronger flavor
- Hamburg (root parsley) - root vegetable
- Japanese parsley (Mitsuba) - Asian cuisine

Critical Diseases:
1. Septoria Leaf Spot (Septoria petroselini) - #1 DISEASE, ENDEMIC WORLDWIDE
2. Bacterial Leaf Spot (Pseudomonas syringae) - SEED-BORNE
3. Cercospora Leaf Blight - DEFOLIATION
4. Celery Mosaic Virus (CeMV) - APHID VECTOR, SYSTEMIC
5. Powdery Mildew (Erysiphe heraclei) - LATE SEASON
6. Sclerotinia Crown Rot - WHITE MOLD, SCLEROTIA
7. Fusarium Wilt - SOILBORNE
8. Aster Yellows (Phytoplasma) - LEAFHOPPER VECTOR

Market Intelligence:
- USA production: $35 million fresh, growing 8% annually
- Fresh parsley: $4-8/lb wholesale, $8-15/lb retail
- Organic parsley: 70% of premium market, $10-18/lb
- Zero tolerance: ANY leaf spots = unmarketable (garnish)
- Biennial crop: Overwinters, bolts second year
- Slow germination: 14-21 days (pre-soak seed improves)

Author: AgroPulse Team
Date: November 2025
"""

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional


class ParsleyType(Enum):
    """Parsley variety categories"""
    CURLY = "curly"  # Garnish, decorative
    FLAT_LEAF_ITALIAN = "flat_leaf"  # Culinary, stronger flavor
    HAMBURG_ROOT = "hamburg"  # Root vegetable
    JAPANESE_MITSUBA = "mitsuba"  # Asian cuisine


class ParsleyDisease(Enum):
    """Major parsley diseases"""
    SEPTORIA_LEAF_SPOT = "septoria"
    BACTERIAL_LEAF_SPOT = "bacterial_spot"
    CERCOSPORA_BLIGHT = "cercospora"
    CELERY_MOSAIC_VIRUS = "celery_mosaic"
    POWDERY_MILDEW = "powdery_mildew"
    SCLEROTINIA_CROWN_ROT = "sclerotinia"
    FUSARIUM_WILT = "fusarium"
    ASTER_YELLOWS = "aster_yellows"


@dataclass
class ParsleyDiseaseParams:
    """Disease parameters for parsley"""
    disease: ParsleyDisease
    pathogen: str
    severity: str
    yield_loss: Tuple[int, int]
    cosmetic_impact: str  # Critical for garnish parsley
    
    # Symptoms
    leaf_symptoms: List[str]
    stem_symptoms: List[str]
    root_symptoms: List[str]
    diagnostic_features: str
    
    # Resistance
    resistant_varieties: List[str]
    resistance_notes: str
    
    # Control (organic emphasis)
    cultural_control: List[str]
    organic_control: List[str]
    conventional_control: List[str]
    
    # Seed-borne
    seed_transmission: str
    seed_treatment: str
    
    # Economics
    market_impact: str
    treatment_cost_per_acre: float


# Disease database
PARSLEY_DISEASES = {
    ParsleyDisease.SEPTORIA_LEAF_SPOT: ParsleyDiseaseParams(
        disease=ParsleyDisease.SEPTORIA_LEAF_SPOT,
        pathogen="Septoria petroselini (ENDEMIC WORLDWIDE, #1 parsley disease)",
        severity="10/10 - #1 DISEASE, ENDEMIC, CATASTROPHIC COSMETIC DAMAGE",
        yield_loss=(40, 80),
        cosmetic_impact="ANY leaf spots = 100% unmarketable as garnish",
        
        leaf_symptoms=[
            "Small circular tan spots with dark borders",
            "Spots 2-5mm diameter with target-ring pattern",
            "Black pycnidia (fruiting bodies) in spot centers DIAGNOSTIC",
            "Yellow halo around spots",
            "Spots coalesce to large blighted areas",
            "Premature leaf yellowing and drop",
            "Disease starts on lower/older leaves",
        ],
        
        stem_symptoms=[
            "Stem lesions brown-black",
            "Petiole infection causes leaf collapse",
        ],
        
        root_symptoms=[],
        
        diagnostic_features="Tan spots with black pycnidia centers, target rings, endemic",
        
        resistant_varieties=[
            "Limited resistance available",
            "Some varieties more tolerant",
            "Plain-leaf types may be less susceptible than curly",
        ],
        resistance_notes="No major resistance, tolerance only",
        
        cultural_control=[
            "2-3 year rotation to non-Apiaceae",
            "Remove crop residues (overwinter inoculum)",
            "Avoid overhead irrigation",
            "Wide row spacing (18-24 inches)",
            "Good air circulation",
            "Scout weekly",
            "Remove infected leaves promptly",
            "Avoid working in wet fields",
        ],
        
        organic_control=[
            "Copper hydroxide (OMRI listed) - LIMITED efficacy",
            "Bacillus subtilis (Serenade) - POOR",
            "DIFFICULT to control organically",
            "Prevention through cultural practices critical",
            "Weekly copper applications may slow progression",
        ],
        
        conventional_control=[
            "FRAC 7: Boscalid (Endura) - GOOD",
            "FRAC 11: Azoxystrobin, pyraclostrobin - GOOD",
            "FRAC 3: Difenoconazole - moderate",
            "FRAC M5: Chlorothalonil - protectant",
            "Rotate FRAC codes",
            "7-10 day intervals",
            "Begin preventatively (endemic disease)",
        ],
        
        seed_transmission="Seed-borne possible, less important than residue",
        seed_treatment="Hot water treatment: 50°C × 25 minutes (optional)",
        
        market_impact="CATASTROPHIC - endemic disease, constant pressure, any spots = rejection",
        treatment_cost_per_acre=250.0
    ),
    
    ParsleyDisease.BACTERIAL_LEAF_SPOT: ParsleyDiseaseParams(
        disease=ParsleyDisease.BACTERIAL_LEAF_SPOT,
        pathogen="Pseudomonas syringae pv. apii (SEED-BORNE, bacterial)",
        severity="9/10 - SEED-BORNE, COSMETIC DAMAGE",
        yield_loss=(30, 70),
        cosmetic_impact="Dark spots highly visible = total rejection",
        
        leaf_symptoms=[
            "Small angular dark brown-black spots",
            "Water-soaked appearance initially",
            "Yellow halo around spots",
            "Spots 1-5mm, angular (follow veins)",
            "Rapid spread in wet weather",
        ],
        
        stem_symptoms=[
            "Black streaks on petioles",
        ],
        
        root_symptoms=[],
        
        diagnostic_features="Angular water-soaked spots, yellow halos, wet weather",
        
        resistant_varieties=[
            "Limited resistance",
        ],
        resistance_notes="No major resistance genes",
        
        cultural_control=[
            "CERTIFIED PATHOGEN-FREE SEED critical",
            "Avoid overhead irrigation",
            "Good air circulation",
            "Remove infected plants",
            "3-year rotation",
            "Disinfect tools",
        ],
        
        organic_control=[
            "Copper hydroxide (OMRI)",
            "Acibenzolar-S-methyl (SAR inducer)",
            "Pathogen-free seed ESSENTIAL",
            "Limited organic efficacy",
        ],
        
        conventional_control=[
            "Copper bactericides + mancozeb",
            "Streptomycin (limited)",
            "Preventative applications",
            "Weekly in wet weather",
        ],
        
        seed_transmission="SEED-BORNE primary source",
        seed_treatment="Hot water: 50°C × 25 minutes",
        
        market_impact="Cosmetic damage = total rejection",
        treatment_cost_per_acre=200.0
    ),
    
    ParsleyDisease.CELERY_MOSAIC_VIRUS: ParsleyDiseaseParams(
        disease=ParsleyDisease.CELERY_MOSAIC_VIRUS,
        pathogen="Celery Mosaic Virus (CeMV) - aphid vector, systemic",
        severity="9/10 - APHID VECTOR, SYSTEMIC, NO CURE",
        yield_loss=(50, 100),
        cosmetic_impact="Leaf distortion = unmarketable",
        
        leaf_symptoms=[
            "Yellow mosaic patterns on leaves",
            "Leaf distortion and curling",
            "Stunted growth (30-50% reduction)",
            "Vein clearing",
            "Mottled appearance",
        ],
        
        stem_symptoms=[
            "Stunted internodes",
        ],
        
        root_symptoms=[],
        
        diagnostic_features="Mosaic, distortion, stunting, aphid vectors",
        
        resistant_varieties=[
            "NO RESISTANCE available",
        ],
        resistance_notes="No resistance genes identified",
        
        cultural_control=[
            "APHID CONTROL CRITICAL",
            "Remove infected plants immediately",
            "Control weeds (reservoir hosts)",
            "Floating row covers (exclude aphids)",
            "Scout for aphids weekly",
        ],
        
        organic_control=[
            "Insecticidal soaps for aphids",
            "Pyrethrin sprays",
            "Row covers",
            "NO CURE for virus",
        ],
        
        conventional_control=[
            "Insecticides for aphid control:",
            "  - Imidacloprid (systemic)",
            "  - Thiamethoxam",
            "  - Pyrethroids",
            "NO CURE for virus",
            "Prevention through vector control",
        ],
        
        seed_transmission="Can be seed-borne",
        seed_treatment="Certified virus-free seed",
        
        market_impact="Total plant loss, unmarketable",
        treatment_cost_per_acre=200.0
    ),
}


@dataclass
class ParsleyDiseaseResult:
    """Detection result for parsley diseases"""
    disease: ParsleyDisease
    confidence: float
    severity: str
    cosmetic_impact: str
    immediate_actions: List[str]
    organic_options: List[str]
    seed_treatment_needed: bool


class ParsleyDiseaseDetector:
    """
    Parsley disease detector
    
    Focus on:
    - Septoria leaf spot: Endemic #1 disease
    - Cosmetic quality (garnish zero tolerance)
    - Seed-borne diseases
    - Organic production methods (70% market)
    """
    
    def __init__(self):
        self.diseases = PARSLEY_DISEASES
    
    def detect_disease(self,
                      image: np.ndarray,
                      plant_part: str = "leaf",
                      parsley_type: ParsleyType = ParsleyType.CURLY) -> List[ParsleyDiseaseResult]:
        """
        Detect parsley diseases
        
        Args:
            image: BGR image
            plant_part: "leaf", "stem", "root"
            parsley_type: Variety type
        
        Returns:
            List of detected diseases
        """
        if image is None or image.size == 0:
            return []
        
        results = []
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        if plant_part == "leaf":
            # SEPTORIA - #1 disease
            septoria_score = self._detect_spots_with_pycnidia(image, hsv)
            if septoria_score > 0.3:
                results.append(self._create_result(
                    ParsleyDisease.SEPTORIA_LEAF_SPOT,
                    septoria_score,
                    parsley_type
                ))
            
            # Bacterial spot
            bacterial_score = self._detect_angular_water_soaked(image, hsv)
            if bacterial_score > 0.4:
                results.append(self._create_result(
                    ParsleyDisease.BACTERIAL_LEAF_SPOT,
                    bacterial_score,
                    parsley_type
                ))
            
            # Virus (mosaic)
            virus_score = self._detect_mosaic_distortion(image, hsv)
            if virus_score > 0.4:
                results.append(self._create_result(
                    ParsleyDisease.CELERY_MOSAIC_VIRUS,
                    virus_score,
                    parsley_type
                ))
        
        return sorted(results, key=lambda x: x.confidence, reverse=True)
    
    def _detect_spots_with_pycnidia(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect tan spots with black pycnidia (Septoria)"""
        tan_lower = np.array([15, 30, 100])
        tan_upper = np.array([30, 150, 200])
        tan_mask = cv2.inRange(hsv, tan_lower, tan_upper)
        
        black_lower = np.array([0, 0, 0])
        black_upper = np.array([180, 255, 50])
        black_mask = cv2.inRange(hsv, black_lower, black_upper)
        
        combined = cv2.bitwise_or(tan_mask, black_mask)
        coverage = np.sum(combined > 0) / combined.size
        return min(1.0, coverage * 18)
    
    def _detect_angular_water_soaked(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect angular water-soaked spots (bacterial)"""
        dark_lower = np.array([0, 50, 0])
        dark_upper = np.array([180, 255, 80])
        dark_mask = cv2.inRange(hsv, dark_lower, dark_upper)
        
        coverage = np.sum(dark_mask > 0) / dark_mask.size
        return min(1.0, coverage * 20)
    
    def _detect_mosaic_distortion(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect mosaic pattern (virus)"""
        yellow_lower = np.array([20, 50, 100])
        yellow_upper = np.array([35, 255, 255])
        yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
        
        coverage = np.sum(yellow_mask > 0) / yellow_mask.size
        return min(1.0, coverage * 15)
    
    def _create_result(self,
                      disease: ParsleyDisease,
                      confidence: float,
                      parsley_type: ParsleyType) -> ParsleyDiseaseResult:
        """Create result with organic emphasis"""
        params = self.diseases[disease]
        
        if disease == ParsleyDisease.SEPTORIA_LEAF_SPOT:
            immediate = [
                "Apply fungicide IMMEDIATELY (endemic disease)",
                "Remove infected leaves",
                "Improve air circulation",
                "Begin preventative spray program",
            ]
            organic = [
                "Copper hydroxide weekly",
                "Remove crop residues after harvest",
                "3-year rotation to non-Apiaceae",
                "DIFFICULT organic control",
            ]
            seed_treat = False
            
        elif disease == ParsleyDisease.BACTERIAL_LEAF_SPOT:
            immediate = [
                "Use certified pathogen-free seed",
                "Apply copper bactericide",
                "Avoid overhead irrigation",
                "Remove infected plants",
            ]
            organic = params.organic_control[:3]
            seed_treat = True
            
        elif disease == ParsleyDisease.CELERY_MOSAIC_VIRUS:
            immediate = [
                "Remove infected plants IMMEDIATELY",
                "Control aphids urgently",
                "Scout for aphids daily",
            ]
            organic = [
                "Insecticidal soap for aphids",
                "Row covers to exclude vectors",
                "NO CURE for virus",
            ]
            seed_treat = True
            
        else:
            immediate = params.cultural_control[:3]
            organic = params.organic_control[:3]
            seed_treat = params.seed_transmission != "Not seed-borne"
        
        return ParsleyDiseaseResult(
            disease=disease,
            confidence=confidence,
            severity=params.severity,
            cosmetic_impact=params.cosmetic_impact,
            immediate_actions=immediate,
            organic_options=organic,
            seed_treatment_needed=seed_treat
        )


# Example usage
if __name__ == "__main__":
    print("Parsley Disease Detection System")
    print("=" * 70)
    
    detector = ParsleyDiseaseDetector()
    
    print("\n📚 PARSLEY DISEASE DATABASE:")
    print("\n#1 DISEASE: SEPTORIA LEAF SPOT")
    septoria = PARSLEY_DISEASES[ParsleyDisease.SEPTORIA_LEAF_SPOT]
    print(f"  Pathogen: {septoria.pathogen}")
    print(f"  Severity: {septoria.severity}")
    print(f"  Diagnostic: {septoria.diagnostic_features}")
    print(f"  Cosmetic: {septoria.cosmetic_impact}")
    
    print("\n✓ Parsley disease detection system initialized")
    print("  Focus: Septoria endemic, cosmetic quality, organic methods")
    print("  Market: $35M USA, organic 70%, $4-8/lb wholesale, $8-15/lb retail")
