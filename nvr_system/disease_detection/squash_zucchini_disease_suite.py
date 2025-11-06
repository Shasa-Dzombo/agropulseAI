"""
Squash & Zucchini Disease Detection Suite
=========================================

Comprehensive disease identification for summer squash and zucchini (Cucurbita pepo),
high-value quick-rotation crops with viral disease complexes and bacterial wilt challenges.

Critical Diseases:
1. Virus Complex (ZYMV, CMV, WMV-2) - APHID-BORNE, NO CURE, 80% LOSS
2. Bacterial Wilt (Erwinia tracheiphila) - BEETLE VECTOR, SYSTEMIC
3. Powdery Mildew (Podosphaera xanthii) - EPIDEMIC, QoI RESISTANCE
4. Downy Mildew (Pseudoperonospora cubensis) - QoI RESISTANCE COMMON
5. Phytophthora Blight (P. capsici) - FRUIT/CROWN ROT CATASTROPHIC
6. Scab (Cladosporium cucumerinum) - FRUIT QUALITY, COOL WET
7. Fusarium Crown Rot (Fusarium solani f.sp. cucurbitae) - SOILBORNE
8. Angular Leaf Spot (Pseudomonas syringae pv. lachrymans) - BACTERIAL

Market Context:
- USA production: 1.2 million tons, $550 million
- Summer squash: 30-50 day harvest cycle (3-4 crops/season possible)
- Zucchini: Premium $1.50-3.00/lb fresh, processing $0.40/lb
- Virus complexes: 60-80% yield loss, #1 disease constraint
- QoI resistance: Widespread in downy/powdery mildew, fungicides failing
- Organic zucchini: 60% premium, disease control challenging

Author: AgroPulse Team
Date: November 2025
"""

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional


class SquashType(Enum):
    """Squash/zucchini variety categories"""
    ZUCCHINI = "zucchini"  # Green cylindrical, most common
    YELLOW_SQUASH = "yellow_squash"  # Crookneck, straightneck
    PATTYPAN = "pattypan"  # Scalloped, flat
    COUSA = "cousa"  # Middle Eastern type
    GOURMET = "gourmet"  # Specialty colors (dark green, gold, striped)


class SquashDisease(Enum):
    """Major squash/zucchini diseases"""
    VIRUS_COMPLEX = "virus_complex"
    BACTERIAL_WILT = "bacterial_wilt"
    POWDERY_MILDEW = "powdery_mildew"
    DOWNY_MILDEW = "downy_mildew"
    PHYTOPHTHORA_BLIGHT = "phytophthora"
    SCAB = "scab"
    FUSARIUM_CROWN_ROT = "fusarium"
    ANGULAR_LEAF_SPOT = "angular_spot"


@dataclass
class SquashDiseaseParams:
    """Disease parameters for squash/zucchini"""
    disease: SquashDisease
    pathogen: str
    severity: str
    yield_loss: Tuple[int, int]
    fruit_quality_impact: str
    
    # Symptoms
    leaf_symptoms: List[str]
    fruit_symptoms: List[str]
    plant_symptoms: List[str]
    diagnostic_features: str
    
    # Resistance
    resistant_varieties: List[str]
    resistance_notes: str
    
    # Control
    cultural_control: List[str]
    chemical_control: List[str]
    vector_control: str  # For virus/bacterial wilt
    
    # Economics
    market_impact: str
    treatment_cost_per_acre: float


# Disease database
SQUASH_DISEASES = {
    SquashDisease.VIRUS_COMPLEX: SquashDiseaseParams(
        disease=SquashDisease.VIRUS_COMPLEX,
        pathogen="ZYMV + CMV + WMV-2 (Zucchini Yellow Mosaic + Cucumber Mosaic + Watermelon Mosaic)",
        severity="10/10 - #1 DISEASE CONSTRAINT, 60-80% YIELD LOSS, NO CURE",
        yield_loss=(60, 80),
        fruit_quality_impact="Deformed, discolored, unmarketable fruit",
        
        leaf_symptoms=[
            "Yellow mosaic patterns on leaves DIAGNOSTIC",
            "Leaf distortion and puckering",
            "Stunted growth (50-70% reduction)",
            "Dark green blisters on leaf surface",
            "Vein clearing (veins lighter than tissue)",
        ],
        
        fruit_symptoms=[
            "Fruit distortion and warping CATASTROPHIC",
            "Yellow/green mottling on fruit surface",
            "Bumpy, knobby fruit texture",
            "Reduced fruit size",
            "Fruit completely unmarketable",
            "Bitter taste in severe cases",
        ],
        
        plant_symptoms=[
            "Stunted plant growth overall",
            "Reduced flowering",
            "Plant death in severe mixed infections",
            "Symptoms appear 2-4 weeks after infection",
        ],
        
        diagnostic_features="Yellow mosaic leaves + deformed fruit, aphid vectors",
        
        resistant_varieties=[
            "Tigress, Spineless Beauty - CMV resistance",
            "Dunja, Amalthea - ZYMV tolerance",
            "Limited varieties with multi-virus resistance",
        ],
        resistance_notes="Single virus resistance inadequate, need multi-virus resistance",
        
        cultural_control=[
            "APHID CONTROL CRITICAL (virus vectors)",
            "Early planting escapes peak aphid pressure",
            "Reflective mulches repel aphids",
            "Perimeter trap crops",
            "Scout weekly for aphids and symptoms",
            "Rogue infected plants IMMEDIATELY",
            "Remove old crop residues (virus inoculum)",
            "Floating row covers until flowering",
        ],
        
        chemical_control=[
            "NO CHEMICAL CURE FOR VIRUSES",
            "Insecticides for aphid control:",
            "  - Imidacloprid (Admire Pro) soil drench",
            "  - Thiamethoxam (Platinum) seed treatment",
            "  - Pymetrozine (Fulfill) aphid-specific",
            "  - Pyrethroids for quick knockdown",
            "Early season protection critical (before infection)",
            "Once infected, no recovery possible"
        ],
        
        vector_control="Aphid management ESSENTIAL - systemic neonicotinoids + foliar sprays",
        market_impact="CATASTROPHIC - 60-80% yield loss, fruit unmarketable",
        treatment_cost_per_acre=250.0  # Insecticides + roguing labor
    ),
    
    SquashDisease.BACTERIAL_WILT: SquashDiseaseParams(
        disease=SquashDisease.BACTERIAL_WILT,
        pathogen="Erwinia tracheiphila (cucumber beetle vector, systemic vascular)",
        severity="9/10 - SYSTEMIC, NO CURE, BEETLE VECTOR",
        yield_loss=(30, 70),
        fruit_quality_impact="Fruit on wilted plants unmarketable",
        
        leaf_symptoms=[
            "Sudden wilting of leaves (vascular blockage)",
            "Initially one or few leaves, progresses rapidly",
            "Leaves remain green while wilted initially",
            "Entire plant wilts and dies within 7-14 days",
        ],
        
        fruit_symptoms=[
            "Fruit on infected vines stops developing",
            "Existing fruit may soften and rot",
        ],
        
        plant_symptoms=[
            "Cut stem oozes milky white sticky sap DIAGNOSTIC",
            "Bacterial ooze forms string when touched (key test)",
            "Vascular browning in stems",
            "Plant death inevitable once symptomatic",
            "More severe in summer squash vs winter squash or pumpkin",
        ],
        
        diagnostic_features="Bacterial ooze string test + sudden wilt + beetle presence",
        
        resistant_varieties=[
            "NO resistance in zucchini/summer squash",
            "Some winter squash have tolerance genes",
        ],
        resistance_notes="Resistance breeding focus needed for summer squash",
        
        cultural_control=[
            "CUCUMBER BEETLE CONTROL #1 PRIORITY (vector)",
            "Weekly insecticide applications",
            "Perimeter trap crops (Blue Hubbard attracts beetles)",
            "Floating row covers until flowering",
            "Remove infected plants immediately",
            "Straw mulch reduces beetle attraction",
            "Delay planting until beetles pass (risky)",
        ],
        
        chemical_control=[
            "Insecticides for beetle control:",
            "  - Neonicotinoids: Imidacloprid, thiamethoxam, clothianidin",
            "  - Pyrethroids: Bifenthrin, lambda-cyhalothrin",
            "  - Carbamates: Carbaryl (Sevin)",
            "Weekly applications during beetle flight",
            "Apply to base of plant where beetles feed",
            "NO fungicides effective (bacterial disease)"
        ],
        
        vector_control="Intensive beetle management: Soil + foliar insecticides, weekly",
        market_impact="Scattered plant losses, intensive beetle control costly",
        treatment_cost_per_acre=200.0
    ),
    
    SquashDisease.POWDERY_MILDEW: SquashDiseaseParams(
        disease=SquashDisease.POWDERY_MILDEW,
        pathogen="Podosphaera xanthii (QoI fungicide resistance widespread)",
        severity="8/10 - EPIDEMIC, FUNGICIDE RESISTANCE COMMON",
        yield_loss=(30, 60),
        fruit_quality_impact="Premature fruit, sunscald from defoliation",
        
        leaf_symptoms=[
            "White powdery growth on leaf surfaces",
            "Starts as small white patches, covers entire leaf",
            "Upper surface first, then lower",
            "Leaves yellow, then brown and die",
            "Rapid defoliation in untreated fields",
        ],
        
        fruit_symptoms=[
            "Sunscald on exposed fruit",
            "Premature ripening",
            "Reduced fruit size and quality",
        ],
        
        plant_symptoms=[
            "Defoliation reduces photosynthesis",
            "Plant vigor declines",
            "Fruit production stops prematurely",
        ],
        
        diagnostic_features="White powder on leaves, DRY weather disease",
        
        resistant_varieties=[
            "Dunja, Amalthea - PM resistance",
            "Resistance race-specific (Race 1, 2, 3, 4, 5)",
            "New races overcome resistance regularly",
        ],
        resistance_notes="Race 1, 2, 3, 4, 5 exist and overcome PM genes",
        
        cultural_control=[
            "Plant resistant varieties (check race)",
            "Early planting escapes peak pressure",
            "Scout weekly",
            "Remove old crop residues",
        ],
        
        chemical_control=[
            "CRITICAL: QoI (FRAC 11) RESISTANCE WIDESPREAD - AVOID",
            "Effective alternatives:",
            "  FRAC 3: Myclobutanil, tebuconazole",
            "  FRAC 13: Quinoxyfen (Quintec)",
            "  FRAC 50: Metrafenone",
            "  FRAC U6: Cyflufenamid",
            "  Sulfur (organic, protectant)",
            "  Potassium bicarbonate (organic, curative)",
            "ROTATE FRAC codes strictly",
            "7-14 day intervals",
            "DO NOT use QoI fungicides (resistance confirmed)"
        ],
        
        vector_control="Not applicable (wind-dispersed spores)",
        market_impact="Yield loss, early season termination",
        treatment_cost_per_acre=200.0
    ),
    
    SquashDisease.DOWNY_MILDEW: SquashDiseaseParams(
        disease=SquashDisease.DOWNY_MILDEW,
        pathogen="Pseudoperonospora cubensis (QoI resistance confirmed)",
        severity="9/10 - EXPLOSIVE DEFOLIATION, QoI RESISTANCE",
        yield_loss=(40, 70),
        fruit_quality_impact="Rapid defoliation, harvest window shortened",
        
        leaf_symptoms=[
            "Angular yellow spots on upper leaf surface",
            "Purple-gray fuzzy growth on lower surface",
            "Spots follow leaf veins (angular pattern)",
            "Rapid progression to complete defoliation",
            "Can destroy field in 7-14 days",
        ],
        
        fruit_symptoms=[
            "Sunscald from defoliation",
            "Premature end to harvest season",
        ],
        
        plant_symptoms=[
            "Rapid leaf loss",
            "Plant vigor collapse",
            "Epidemic spreads regionally (wind-borne)",
        ],
        
        diagnostic_features="Angular spots, purple-gray undersides, EPIDEMIC speed",
        
        resistant_varieties=[
            "Limited resistance in squash",
            "Breeding ongoing",
        ],
        resistance_notes="Resistance sources limited in summer squash",
        
        cultural_control=[
            "Monitor IPM forecasts (cdm.ipmpipe.org)",
            "Begin sprays when detected within 50 miles",
            "Avoid overhead irrigation",
            "Good air circulation",
        ],
        
        chemical_control=[
            "CRITICAL: QoI (FRAC 11) RESISTANCE CONFIRMED",
            "Effective fungicides:",
            "  FRAC 40: Cyazofamid (Ranman) - BEST",
            "  FRAC 43: Fluopicolide (Presidio)",
            "  FRAC 22: Famoxadone + cymoxanil (Tanos)",
            "  FRAC 4: Mefenoxam (if no resistance)",
            "DO NOT use QoI fungicides alone",
            "Preventative sprays CRITICAL",
            "5-7 day intervals in epidemic conditions"
        ],
        
        vector_control="Not applicable (wind-dispersed)",
        market_impact="Rapid crop loss, regional epidemic threat",
        treatment_cost_per_acre=300.0
    ),
    
    SquashDisease.PHYTOPHTHORA_BLIGHT: SquashDiseaseParams(
        disease=SquashDisease.PHYTOPHTHORA_BLIGHT,
        pathogen="Phytophthora capsici (oospores 10+ years, fruit/crown rot)",
        severity="10/10 - CATASTROPHIC, CROWN AND FRUIT ROT",
        yield_loss=(70, 100),
        fruit_quality_impact="TOTAL fruit loss, crown rot kills plants",
        
        leaf_symptoms=[
            "Water-soaked lesions on leaves",
            "Rapid leaf blight",
        ],
        
        fruit_symptoms=[
            "Water-soaked spots on fruit surface",
            "Rapid progression to complete fruit rot",
            "White fluffy mycelium on rotting fruit",
            "Can destroy 100% of fruit in field",
        ],
        
        plant_symptoms=[
            "Crown rot at soil line DEVASTATING",
            "Entire plant wilts and dies suddenly",
            "Stem girdling above and below soil line",
            "Field patches of dead plants",
        ],
        
        diagnostic_features="Crown rot + fruit rot, waterlogged soils, rapid death",
        
        resistant_varieties=[
            "Limited resistance, race-specific",
            "Resistance incomplete",
        ],
        resistance_notes="Races 1-5 exist, multi-race resistance needed",
        
        cultural_control=[
            "DRAINAGE CRITICAL - waterlogged = disaster",
            "Avoid infested fields (10+ year contamination)",
            "Raised beds essential",
            "Drip irrigation only",
            "3-4 year rotation to non-hosts",
            "Plastic mulch reduces soil splash",
        ],
        
        chemical_control=[
            "FRAC 4: Mefenoxam (Ridomil) - at-plant",
            "FRAC 43: Fluopicolide (Presidio)",
            "FRAC 40: Cyazofamid (Ranman)",
            "FRAC 22: Famoxadone (Tanos)",
            "Preventative only - once infected, too late",
            "Intensive program in wet weather"
        ],
        
        vector_control="Not applicable (soilborne, splash-dispersed)",
        market_impact="CATASTROPHIC - field abandonment, 10+ year loss",
        treatment_cost_per_acre=350.0
    ),
}


@dataclass
class SquashDiseaseResult:
    """Detection result for squash/zucchini diseases"""
    disease: SquashDisease
    confidence: float
    severity: str
    fruit_marketability: str
    symptoms_detected: List[str]
    immediate_actions: List[str]
    spray_program: List[str]
    resistance_alert: str


class SquashZucchiniDiseaseDetector:
    """
    Squash and zucchini disease detector
    
    Critical focus:
    - Virus complexes: #1 constraint, no cure, vector control
    - QoI fungicide resistance: Powdery and downy mildew
    - Bacterial wilt: Beetle vector, no cure
    - Phytophthora: Catastrophic crown/fruit rot
    """
    
    def __init__(self):
        self.diseases = SQUASH_DISEASES
    
    def detect_disease(self,
                      image: np.ndarray,
                      plant_part: str = "leaf",
                      qoi_fungicide_used: bool = False) -> List[SquashDiseaseResult]:
        """
        Detect squash/zucchini diseases
        
        Args:
            image: BGR image
            plant_part: "leaf", "fruit", or "plant"
            qoi_fungicide_used: Alert if QoI resistance suspected
        
        Returns:
            List of detected diseases with resistance alerts
        """
        if image is None or image.size == 0:
            return []
        
        results = []
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        if plant_part == "leaf":
            # Virus (yellow mosaic)
            virus_score = self._detect_yellow_mosaic(image, hsv)
            if virus_score > 0.4:
                results.append(self._create_result(
                    SquashDisease.VIRUS_COMPLEX,
                    virus_score,
                    "#1 DISEASE - Vector control critical",
                    qoi_fungicide_used
                ))
            
            # Powdery mildew (white powder)
            powdery_score = self._detect_white_powder(image, hsv)
            if powdery_score > 0.4:
                results.append(self._create_result(
                    SquashDisease.POWDERY_MILDEW,
                    powdery_score,
                    "QoI resistance widespread",
                    qoi_fungicide_used
                ))
            
            # Downy mildew (angular spots)
            downy_score = self._detect_angular_purple(image, hsv)
            if downy_score > 0.4:
                results.append(self._create_result(
                    SquashDisease.DOWNY_MILDEW,
                    downy_score,
                    "QoI resistance confirmed",
                    qoi_fungicide_used
                ))
        
        elif plant_part == "fruit":
            # Phytophthora (water-soaked rot)
            phytophthora_score = self._detect_water_soaked(image, hsv)
            if phytophthora_score > 0.5:
                results.append(self._create_result(
                    SquashDisease.PHYTOPHTHORA_BLIGHT,
                    phytophthora_score,
                    "CATASTROPHIC - Remove fruit",
                    qoi_fungicide_used
                ))
        
        return sorted(results, key=lambda x: x.confidence, reverse=True)
    
    def _detect_yellow_mosaic(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect yellow mosaic pattern (virus)"""
        yellow_lower = np.array([20, 50, 100])
        yellow_upper = np.array([35, 255, 255])
        yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
        
        # Look for patchy distribution (mosaic)
        coverage = np.sum(yellow_mask > 0) / yellow_mask.size
        return min(1.0, coverage * 12)
    
    def _detect_white_powder(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect white powder (powdery mildew)"""
        white_lower = np.array([0, 0, 200])
        white_upper = np.array([180, 50, 255])
        white_mask = cv2.inRange(hsv, white_lower, white_upper)
        
        coverage = np.sum(white_mask > 0) / white_mask.size
        return min(1.0, coverage * 20)
    
    def _detect_angular_purple(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect angular spots with purple sporulation (downy)"""
        yellow_lower = np.array([20, 50, 100])
        yellow_upper = np.array([35, 255, 255])
        yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
        
        purple_lower = np.array([120, 20, 40])
        purple_upper = np.array([160, 150, 150])
        purple_mask = cv2.inRange(hsv, purple_lower, purple_upper)
        
        combined = cv2.bitwise_or(yellow_mask, purple_mask)
        coverage = np.sum(combined > 0) / combined.size
        return min(1.0, coverage * 15)
    
    def _detect_water_soaked(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect water-soaked lesions (Phytophthora)"""
        dark_lower = np.array([0, 50, 0])
        dark_upper = np.array([180, 255, 100])
        dark_mask = cv2.inRange(hsv, dark_lower, dark_upper)
        
        coverage = np.sum(dark_mask > 0) / dark_mask.size
        return min(1.0, coverage * 12)
    
    def _create_result(self,
                      disease: SquashDisease,
                      confidence: float,
                      severity: str,
                      qoi_used: bool) -> SquashDiseaseResult:
        """Create result with resistance alerts"""
        params = self.diseases[disease]
        
        # Disease-specific recommendations
        if disease == SquashDisease.VIRUS_COMPLEX:
            immediate = [
                "ROGUE infected plants immediately",
                "Intensify aphid control",
                "Apply systemic insecticides",
                "Scout daily for new infections"
            ]
            spray = [
                "Imidacloprid soil drench",
                "Pymetrozine foliar spray",
                "NO CURE for viruses",
                "Prevention only"
            ]
            resistance = "Multi-virus resistance needed, single gene insufficient"
        
        elif disease == SquashDisease.POWDERY_MILDEW:
            if qoi_used:
                immediate = ["STOP using QoI fungicides - resistance widespread"]
                resistance = "QoI (FRAC 11) RESISTANCE CONFIRMED - switch fungicide classes"
            else:
                immediate = ["Begin non-QoI fungicide program"]
                resistance = "QoI resistance widespread - use FRAC 3, 13, 50"
            spray = [
                "FRAC 13: Quinoxyfen",
                "FRAC 3: Tebuconazole",
                "FRAC 50: Metrafenone",
                "AVOID QoI fungicides"
            ]
        
        elif disease == SquashDisease.DOWNY_MILDEW:
            if qoi_used:
                immediate = ["STOP QoI fungicides immediately - resistance confirmed"]
                resistance = "QoI (FRAC 11) RESISTANCE CONFIRMED - crop failure if continued"
            else:
                immediate = ["Use FRAC 40 or 43 fungicides"]
                resistance = "QoI resistance confirmed - Cyazofamid or Fluopicolide ONLY"
            spray = [
                "FRAC 40: Cyazofamid (BEST)",
                "FRAC 43: Fluopicolide",
                "FRAC 22: Famoxadone",
                "QoI fungicides INEFFECTIVE"
            ]
        
        elif disease == SquashDisease.PHYTOPHTHORA_BLIGHT:
            immediate = [
                "Remove infected fruit/plants immediately",
                "Improve drainage urgently",
                "Preventative fungicide program"
            ]
            spray = [
                "FRAC 43: Fluopicolide",
                "FRAC 40: Cyazofamid",
                "5-7 day intervals"
            ]
            resistance = "Races 1-5 exist, field contamination 10+ years"
        
        else:
            immediate = params.cultural_control[:2]
            spray = params.chemical_control[:3]
            resistance = params.resistance_notes
        
        return SquashDiseaseResult(
            disease=disease,
            confidence=confidence,
            severity=severity,
            fruit_marketability=params.fruit_quality_impact,
            symptoms_detected=params.leaf_symptoms[:3],
            immediate_actions=immediate,
            spray_program=spray,
            resistance_alert=resistance
        )


# Example usage
if __name__ == "__main__":
    print("Squash & Zucchini Disease Detection System")
    print("=" * 70)
    
    detector = SquashZucchiniDiseaseDetector()
    
    print("\n📚 SQUASH/ZUCCHINI DISEASE DATABASE:")
    print("\nCRITICAL DISEASES:")
    for disease, params in SQUASH_DISEASES.items():
        if disease in [SquashDisease.VIRUS_COMPLEX, SquashDisease.POWDERY_MILDEW, SquashDisease.DOWNY_MILDEW]:
            print(f"\n{disease.value.upper()}")
            print(f"  Pathogen: {params.pathogen}")
            print(f"  Severity: {params.severity}")
    
    print("\n" + "=" * 70)
    print("QoI FUNGICIDE RESISTANCE ALERT:")
    print("  Powdery mildew: QoI (FRAC 11) resistance WIDESPREAD")
    print("  Downy mildew: QoI (FRAC 11) resistance CONFIRMED")
    print("  WARNING: DO NOT use azoxystrobin, pyraclostrobin alone")
    print("  Alternative: FRAC 40 (Cyazofamid), FRAC 43 (Fluopicolide)")
    
    print("\n✓ Squash/zucchini disease detection system initialized")
    print("  Focus: Virus control, fungicide resistance management")
    print("  Market: $550M USA, 30-50 day cycles, premium fresh $1.50-3.00/lb")
