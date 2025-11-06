"""
Pumpkin Disease Detection Suite
===============================

Comprehensive disease identification for pumpkin (Cucurbita spp.),
a major cucurbit crop with epidemic powdery mildew and fruit rot challenges.

Critical Diseases:
1. Powdery Mildew (Podosphaera xanthii) - #1 EPIDEMIC DISEASE WORLDWIDE
2. Downy Mildew (Pseudoperonospora cubensis) - EXPLOSIVE DEFOLIATION
3. Phytophthora Fruit Rot (P. capsici) - OOSPORE 10+ YEARS
4. Bacterial Wilt (Erwinia tracheiphila) - CUCUMBER BEETLE VECTOR
5. Fusarium Fruit Rot (Fusarium spp.) - POST-HARVEST MAJOR
6. Plectosporium Blight (Plectosporium tabacinum) - WET SEASON DESTROYER
7. Anthracnose (Colletotrichum) - FRUIT QUALITY DESTRUCTION
8. Gummy Stem Blight (Stagonosporopsis cucurbitacearum) - CANKER STEM GIRDLE

Market Context:
- Global production: 28 million tons/year, $7 billion
- USA: 600,000 tons, Halloween/pie market critical
- Powdery mildew: Can destroy 50-80% yield, $150M+ annual damage USA
- Phytophthora: 80-100% fruit loss in infected fields
- Premium pumpkins: $0.50-3.00/lb (ornamental > pie)
- Organic pumpkins: 50% premium, disease control challenging

Author: AgroPulse Team
Date: November 2025
"""

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional


class PumpkinType(Enum):
    """Pumpkin variety categories"""
    PIE = "pie"  # Sugar pumpkin, small, sweet
    JACK_O_LANTERN = "jack_o_lantern"  # Carving, Halloween
    GIANT = "giant"  # Competition, >100 lbs
    MINIATURE = "miniature"  # Decorative, <2 lbs
    SPECIALTY = "specialty"  # White, blue, warty varieties


class PumpkinDisease(Enum):
    """Major pumpkin diseases"""
    POWDERY_MILDEW = "powdery_mildew"
    DOWNY_MILDEW = "downy_mildew"
    PHYTOPHTHORA_BLIGHT = "phytophthora"
    BACTERIAL_WILT = "bacterial_wilt"
    FUSARIUM_FRUIT_ROT = "fusarium"
    PLECTOSPORIUM_BLIGHT = "plectosporium"
    ANTHRACNOSE = "anthracnose"
    GUMMY_STEM_BLIGHT = "gummy_stem_blight"


@dataclass
class PumpkinDiseaseParams:
    """Disease parameters for pumpkin"""
    disease: PumpkinDisease
    pathogen: str
    severity: str
    yield_loss: Tuple[int, int]
    fruit_impact: str
    
    # Symptoms
    leaf_symptoms: List[str]
    fruit_symptoms: List[str]
    stem_vine_symptoms: List[str]
    diagnostic_features: str
    
    # Environmental
    temp_optimal_c: float
    humidity_requirement: str
    
    # Resistance
    resistant_varieties: List[str]
    resistance_notes: str
    
    # Control
    cultural_control: List[str]
    fungicide_groups: List[str]  # FRAC codes
    
    # Economics
    market_impact: str
    treatment_cost_per_acre: float


# Disease database
PUMPKIN_DISEASES = {
    PumpkinDisease.POWDERY_MILDEW: PumpkinDiseaseParams(
        disease=PumpkinDisease.POWDERY_MILDEW,
        pathogen="Podosphaera xanthii (formerly Sphaerotheca fuliginea) - #1 DISEASE",
        severity="10/10 - EPIDEMIC WORLDWIDE, 50-80% YIELD LOSS",
        yield_loss=(40, 80),
        fruit_impact="Premature fruit drop, undersized fruit, poor quality",
        
        leaf_symptoms=[
            "White powdery growth on leaf surfaces DIAGNOSTIC",
            "Upper leaf surface first, then lower",
            "Starts as small white patches",
            "Rapidly covers entire leaf surface",
            "Leaves turn yellow, then brown and die",
            "Severe defoliation (80-100% leaves lost)",
            "Exposed fruit sunscald from defoliation",
            "Spreads extremely rapidly (days, not weeks)",
        ],
        
        fruit_symptoms=[
            "Premature ripening (defoliation stress)",
            "Undersized fruit (30-50% smaller)",
            "Sunscald on exposed fruit",
            "Poor storage quality",
            "Reduced sugar content (pie quality loss)",
        ],
        
        stem_vine_symptoms=[
            "Can infect stems and petioles",
            "White powder on all plant parts",
        ],
        
        diagnostic_features="White powder on leaves, epidemic spread, DRY weather favored",
        temp_optimal_c=25.0,
        humidity_requirement="Low - dry weather disease (unique among fungal diseases)",
        
        resistant_varieties=[
            "PM resistance increasingly common in varieties",
            "Resistance often overcome by new pathogen races",
            "Partial resistance better than none",
        ],
        resistance_notes="Race 1, 2, 3, 4, 5 exist, resistance race-specific",
        
        cultural_control=[
            "Plant resistant varieties (check race)",
            "Cannot avoid by irrigation timing (dry disease)",
            "Early planting escapes peak disease pressure",
            "Wider row spacing for spray coverage",
            "Remove old crop residues",
            "Scout weekly starting at flowering",
        ],
        
        fungicide_groups=[
            "FRAC 11: Azoxystrobin, pyraclostrobin (RESISTANCE COMMON)",
            "FRAC 3: Myclobutanil, tebuconazole, difenoconazole",
            "FRAC 13: Quinoxyfen (Quintec)",
            "FRAC U6: Cyflufenamid",
            "FRAC 50: Metrafenone",
            "Sulfur (FRAC M2) - organic, protectant",
            "Potassium bicarbonate - organic, curative",
            "ROTATE FRAC CODES - resistance develops rapidly (2-3 years)",
            "7-14 day intervals, begin at first symptoms or preventative",
            "Cost: $200-300/acre/season for protection"
        ],
        
        market_impact="Yield loss severe, fruit quality reduced, early defoliation",
        treatment_cost_per_acre=250.0
    ),
    
    PumpkinDisease.PHYTOPHTHORA_BLIGHT: PumpkinDiseaseParams(
        disease=PumpkinDisease.PHYTOPHTHORA_BLIGHT,
        pathogen="Phytophthora capsici (oospores survive 10+ years, races exist)",
        severity="10/10 - CATASTROPHIC FRUIT ROT, FIELD ABANDONMENT",
        yield_loss=(60, 100),
        fruit_impact="TOTAL FRUIT LOSS - 80-100% in infected areas, rapid rot",
        
        leaf_symptoms=[
            "Water-soaked lesions on leaves",
            "Rapid leaf blight and collapse",
            "White fungal growth on lesions in humid conditions",
        ],
        
        fruit_symptoms=[
            "Water-soaked spots on fruit EARLY WARNING",
            "Rapid progression to complete fruit rot",
            "White fluffy mycelium covers rotting fruit",
            "Foul odor as secondary bacteria invade",
            "Fruit collapses and liquefies",
            "Spreads fruit-to-fruit in field and storage",
            "Can destroy 100% of fruit in field in 7-10 days",
        ],
        
        stem_vine_symptoms=[
            "Crown rot at soil line",
            "Stem girdling causes plant death",
            "Entire plant wilts and dies suddenly",
        ],
        
        diagnostic_features="Rapid fruit rot, water-soaked lesions, favored by wet soil",
        temp_optimal_c=28.0,
        humidity_requirement="High - waterlogged soils CRITICAL, poor drainage disaster",
        
        resistant_varieties=[
            "Limited resistance available",
            "Some varieties less susceptible",
            "Resistance incomplete, races overcome",
        ],
        resistance_notes="Race 1, 2, 3, 4, 5 documented, need multi-race resistance",
        
        cultural_control=[
            "FIELD DRAINAGE CRITICAL - waterlogged = disaster",
            "Avoid fields with Phytophthora history (10+ year survival)",
            "Raised beds essential in heavy soils",
            "Drip irrigation vs overhead (reduce leaf wetness)",
            "Do not work in wet fields (spreads oospores)",
            "3-4 year rotation to non-hosts",
            "Remove infected fruit immediately from field",
            "Plastic mulch reduces splash from soil",
        ],
        
        fungicide_groups=[
            "FRAC 4: Mefenoxam (Ridomil) - at-plant, resistance risk",
            "FRAC 43: Fluopicolide (Presidio)",
            "FRAC 40: Cyazofamid (Ranman)",
            "FRAC 22: Famoxadone + cymoxanil (Tanos)",
            "Preventative sprays in wet weather CRITICAL",
            "Once fruit infection starts, too late",
            "Cost: $300-400/acre for intensive protection"
        ],
        
        market_impact="CATASTROPHIC - complete field loss possible, 10+ year contamination",
        treatment_cost_per_acre=350.0
    ),
    
    PumpkinDisease.DOWNY_MILDEW: PumpkinDiseaseParams(
        disease=PumpkinDisease.DOWNY_MILDEW,
        pathogen="Pseudoperonospora cubensis (explosive spread, wind-borne)",
        severity="9/10 - EXPLOSIVE DEFOLIATION, EPIDEMIC",
        yield_loss=(40, 70),
        fruit_impact="Premature fruit ripening, undersized, sunscald",
        
        leaf_symptoms=[
            "Yellow angular spots on upper leaf surface DIAGNOSTIC",
            "Spots follow veins (angular pattern)",
            "Purple-gray fuzzy growth on lower leaf surface",
            "Rapid progression to complete defoliation",
            "Can destroy field in 7-14 days",
            "Wind-borne spores spread for miles",
            "Epidemics move north through USA each summer",
        ],
        
        fruit_symptoms=[
            "Defoliation causes sunscald",
            "Premature ripening",
            "Reduced fruit size",
        ],
        
        stem_vine_symptoms=[
            "Stem infection uncommon",
        ],
        
        diagnostic_features="Angular yellow spots, purple-gray undersides, EPIDEMIC speed",
        temp_optimal_c=20.0,
        humidity_requirement="High - leaf wetness 6+ hours, wet weather explosive",
        
        resistant_varieties=[
            "No effective resistance in pumpkin",
            "All varieties susceptible",
        ],
        resistance_notes="Resistance breeding difficult, pathogen variability high",
        
        cultural_control=[
            "Monitor IPM forecasts (cdm.ipmpipe.org)",
            "Begin sprays when detected within 50 miles",
            "Cannot prevent by cultural practices alone",
            "Avoid overhead irrigation",
            "Wider row spacing for spray coverage",
        ],
        
        fungicide_groups=[
            "FRAC 40: Cyazofamid (Ranman) - excellent",
            "FRAC 43: Fluopicolide (Presidio)",
            "FRAC 22: Famoxadone (Tanos)",
            "FRAC 11: QoI fungicides (RESISTANCE COMMON - avoid)",
            "FRAC 4: Mefenoxam (if no resistance)",
            "Preventative sprays CRITICAL - curative control limited",
            "5-7 day intervals in wet weather or after forecast alert",
            "Cost: $300/acre for intensive protection"
        ],
        
        market_impact="Rapid defoliation, premature harvest, reduced yield",
        treatment_cost_per_acre=300.0
    ),
    
    PumpkinDisease.BACTERIAL_WILT: PumpkinDiseaseParams(
        disease=PumpkinDisease.BACTERIAL_WILT,
        pathogen="Erwinia tracheiphila (cucumber beetle vector, systemic)",
        severity="8/10 - SYSTEMIC VASCULAR, NO CURE",
        yield_loss=(20, 60),
        fruit_impact="Fruit on wilted plants do not develop",
        
        leaf_symptoms=[
            "Sudden wilting of leaves despite adequate moisture",
            "Initially one or few leaves wilt",
            "Rapid progression to entire plant wilting",
            "Leaves remain green while wilted (vascular)",
        ],
        
        fruit_symptoms=[
            "Fruit stops developing on wilted vines",
            "Existing fruit may soften",
        ],
        
        stem_vine_symptoms=[
            "Cut stem oozes sticky white sap when squeezed DIAGNOSTIC",
            "Milky bacterial ooze forms string when touched",
            "Vascular browning visible in stem",
            "Plant death within 7-14 days of symptom onset",
        ],
        
        diagnostic_features="Bacterial ooze test (sticky string), cucumber beetle presence",
        temp_optimal_c=28.0,
        humidity_requirement="Not humidity dependent",
        
        resistant_varieties=[
            "No resistance available in pumpkin",
            "Some squash varieties resistant",
        ],
        resistance_notes="Resistance genes not available in pumpkin genetics",
        
        cultural_control=[
            "CUCUMBER BEETLE CONTROL CRITICAL (vector)",
            "Insecticides for beetle management:",
            "  - Neonicotinoids (imidacloprid, thiamethoxam)",
            "  - Pyrethroids for quick knockdown",
            "  - Weekly applications in high pressure",
            "Remove infected plants immediately",
            "Perimeter trap crops (Blue Hubbard squash)",
            "Floating row covers until flowering",
        ],
        
        fungicide_groups=[
            "No fungicide effective (bacterial, not fungal)",
            "Vector (beetle) control only strategy",
        ],
        
        market_impact="Scattered plant losses, vector control costs high",
        treatment_cost_per_acre=200.0  # Insecticides
    ),
    
    PumpkinDisease.GUMMY_STEM_BLIGHT: PumpkinDiseaseParams(
        disease=PumpkinDisease.GUMMY_STEM_BLIGHT,
        pathogen="Stagonosporopsis cucurbitacearum (seed-borne, fruit storage rot)",
        severity="7/10 - STEM CANKER, FRUIT STORAGE ROT",
        yield_loss=(20, 50),
        fruit_impact="Storage rot major, stem cankers reduce yield",
        
        leaf_symptoms=[
            "Tan to brown lesions on leaves",
            "Lesions have dark margin",
            "Severe defoliation in wet conditions",
        ],
        
        fruit_symptoms=[
            "Gummy ooze from fruit lesions",
            "Black rot develops in storage MAJOR PROBLEM",
            "Storage losses can be 30-50%",
            "Starts at stem end of fruit",
        ],
        
        stem_vine_symptoms=[
            "Tan cankers on stems DIAGNOSTIC",
            "Black pycnidia (fruiting bodies) in cankers",
            "Gummy amber exudate oozes from cankers",
            "Stem girdling causes vine dieback",
            "Can girdle stem, killing entire vine",
        ],
        
        diagnostic_features="Gummy ooze on stems, black pycnidia, storage fruit rot",
        temp_optimal_c=24.0,
        humidity_requirement="High - wet weather favors",
        
        resistant_varieties=[
            "Limited resistance available",
        ],
        resistance_notes="Resistance incomplete",
        
        cultural_control=[
            "CERTIFIED DISEASE-FREE SEED critical (seed-borne)",
            "2-3 year rotation",
            "Remove crop debris (overwinters on residue)",
            "Avoid overhead irrigation",
            "Harvest with stem attached reduces entry point",
        ],
        
        fungicide_groups=[
            "FRAC 3: Difenoconazole, tebuconazole",
            "FRAC 7: Boscalid (Endura)",
            "FRAC M5: Chlorothalonil",
            "Begin sprays at vine run or first symptoms",
        ],
        
        market_impact="Storage losses significant, stem girdling reduces yield",
        treatment_cost_per_acre=200.0
    ),
}


@dataclass
class PumpkinDiseaseResult:
    """Detection result for pumpkin diseases"""
    disease: PumpkinDisease
    confidence: float
    severity: str
    fruit_damage: str
    symptoms_detected: List[str]
    immediate_actions: List[str]
    spray_program: List[str]
    epidemic_risk: str


class PumpkinDiseaseDetector:
    """
    Pumpkin disease detector with powdery mildew and Phytophthora focus
    
    Critical diseases:
    - Powdery mildew: #1 epidemic disease, dry weather, rapid spread
    - Phytophthora: Catastrophic fruit rot, 10+ year soil survival
    - Downy mildew: Explosive defoliation, wind-borne epidemic
    - Bacterial wilt: Cucumber beetle vector, no cure
    """
    
    def __init__(self):
        self.diseases = PUMPKIN_DISEASES
    
    def detect_disease(self,
                      image: np.ndarray,
                      plant_part: str = "leaf",  # "leaf", "fruit", "stem"
                      weather_wet: bool = False) -> List[PumpkinDiseaseResult]:
        """
        Detect pumpkin diseases
        
        Args:
            image: BGR image of plant part
            plant_part: "leaf", "fruit", or "stem"
            weather_wet: Recent rain/high humidity
        
        Returns:
            List of detected diseases with epidemic risk assessment
        """
        if image is None or image.size == 0:
            return []
        
        results = []
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        if plant_part == "leaf":
            # Powdery mildew (white powder)
            powdery_score = self._detect_white_powder(image, hsv)
            if powdery_score > 0.4:
                results.append(self._create_result(
                    PumpkinDisease.POWDERY_MILDEW,
                    powdery_score,
                    "EPIDEMIC - Spreads rapidly",
                    weather_wet
                ))
            
            # Downy mildew (angular spots, purple-gray)
            downy_score = self._detect_angular_spots_purple(image, hsv)
            if downy_score > 0.4 and weather_wet:
                results.append(self._create_result(
                    PumpkinDisease.DOWNY_MILDEW,
                    downy_score,
                    "EXPLOSIVE - Monitor IPM forecasts",
                    weather_wet
                ))
        
        elif plant_part == "fruit":
            # Phytophthora (water-soaked, rapid rot)
            phytophthora_score = self._detect_water_soaked_fruit(image, hsv)
            if phytophthora_score > 0.5 and weather_wet:
                results.append(self._create_result(
                    PumpkinDisease.PHYTOPHTHORA_BLIGHT,
                    phytophthora_score,
                    "CATASTROPHIC - Remove fruit immediately",
                    weather_wet
                ))
        
        elif plant_part == "stem":
            # Gummy stem blight (cankers with gummy ooze)
            gummy_score = self._detect_stem_cankers(image, hsv)
            if gummy_score > 0.4:
                results.append(self._create_result(
                    PumpkinDisease.GUMMY_STEM_BLIGHT,
                    gummy_score,
                    "Moderate - Storage rot risk",
                    weather_wet
                ))
        
        return sorted(results, key=lambda x: x.confidence, reverse=True)
    
    def _detect_white_powder(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect white powdery growth (powdery mildew)"""
        white_lower = np.array([0, 0, 200])
        white_upper = np.array([180, 50, 255])
        white_mask = cv2.inRange(hsv, white_lower, white_upper)
        
        coverage = np.sum(white_mask > 0) / white_mask.size
        return min(1.0, coverage * 20)
    
    def _detect_angular_spots_purple(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect angular yellow spots with purple undersides (downy mildew)"""
        # Yellow spots
        yellow_lower = np.array([20, 50, 100])
        yellow_upper = np.array([35, 255, 255])
        yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
        
        # Purple-gray regions
        purple_lower = np.array([120, 20, 40])
        purple_upper = np.array([160, 150, 150])
        purple_mask = cv2.inRange(hsv, purple_lower, purple_upper)
        
        combined = cv2.bitwise_or(yellow_mask, purple_mask)
        coverage = np.sum(combined > 0) / combined.size
        return min(1.0, coverage * 15)
    
    def _detect_water_soaked_fruit(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect water-soaked lesions (Phytophthora)"""
        dark_lower = np.array([0, 50, 0])
        dark_upper = np.array([180, 255, 100])
        dark_mask = cv2.inRange(hsv, dark_lower, dark_upper)
        
        coverage = np.sum(dark_mask > 0) / dark_mask.size
        return min(1.0, coverage * 12)
    
    def _detect_stem_cankers(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect tan cankers on stems (gummy stem blight)"""
        tan_lower = np.array([15, 30, 80])
        tan_upper = np.array([30, 150, 180])
        tan_mask = cv2.inRange(hsv, tan_lower, tan_upper)
        
        coverage = np.sum(tan_mask > 0) / tan_mask.size
        return min(1.0, coverage * 10)
    
    def _create_result(self,
                      disease: PumpkinDisease,
                      confidence: float,
                      severity: str,
                      weather_wet: bool) -> PumpkinDiseaseResult:
        """Create detection result with epidemic assessment"""
        params = self.diseases[disease]
        
        # Disease-specific recommendations
        if disease == PumpkinDisease.POWDERY_MILDEW:
            immediate = [
                "Begin fungicide program IMMEDIATELY",
                "Scout entire field for extent",
                "Rotate FRAC codes strictly",
                "7-14 day spray intervals"
            ]
            spray = [
                "Week 1: Quinoxyfen (FRAC 13)",
                "Week 2: Tebuconazole (FRAC 3)",
                "Week 3: Sulfur (organic option)",
                "Week 4: Rotate back to FRAC 13",
                "Continue until harvest"
            ]
            epidemic = "HIGH - Spreads rapidly in days, not weeks"
        
        elif disease == PumpkinDisease.PHYTOPHTHORA_BLIGHT:
            immediate = [
                "Remove infected fruit from field IMMEDIATELY",
                "Improve drainage urgently",
                "Stop overhead irrigation",
                "Preventative sprays if not already"
            ]
            spray = [
                "Fluopicolide (FRAC 43)",
                "Cyazofamid (FRAC 40)",
                "5-7 day intervals in wet weather",
                "Once fruit infected, too late"
            ]
            epidemic = "CATASTROPHIC - Can destroy 100% fruit in 7-10 days"
        
        elif disease == PumpkinDisease.DOWNY_MILDEW:
            immediate = [
                "Check IPM forecasts immediately",
                "Begin intensive spray program",
                "5-7 day intervals critical",
                "Avoid overhead irrigation"
            ]
            spray = [
                "Cyazofamid (FRAC 40) - best efficacy",
                "Famoxadone (FRAC 22)",
                "Rotate FRAC codes",
                "Preventative only - no curative control"
            ]
            epidemic = "EXPLOSIVE - Wind-borne, regional epidemic possible"
        
        else:
            immediate = params.cultural_control[:2]
            spray = params.fungicide_groups[:3]
            epidemic = "Moderate - Monitor and manage"
        
        return PumpkinDiseaseResult(
            disease=disease,
            confidence=confidence,
            severity=severity,
            fruit_damage=params.fruit_impact,
            symptoms_detected=params.leaf_symptoms[:3] if params.leaf_symptoms else params.fruit_symptoms[:3],
            immediate_actions=immediate,
            spray_program=spray,
            epidemic_risk=epidemic
        )


# Example usage
if __name__ == "__main__":
    print("Pumpkin Disease Detection System")
    print("=" * 70)
    
    detector = PumpkinDiseaseDetector()
    
    print("\n📚 PUMPKIN DISEASE DATABASE:")
    print("\nEPIDEMIC DISEASES (CRITICAL):")
    for disease, params in PUMPKIN_DISEASES.items():
        if "EPIDEMIC" in params.severity or "CATASTROPHIC" in params.severity:
            print(f"\n{disease.value.upper()}")
            print(f"  Pathogen: {params.pathogen}")
            print(f"  Severity: {params.severity}")
            print(f"  Yield Loss: {params.yield_loss[0]}-{params.yield_loss[1]}%")
    
    print("\n" + "=" * 70)
    print("POWDERY MILDEW MANAGEMENT (DISEASE #1):")
    pm_params = PUMPKIN_DISEASES[PumpkinDisease.POWDERY_MILDEW]
    print("\nFRAC Rotation (Resistance Management):")
    for i, frac in enumerate(pm_params.fungicide_groups[:5], 1):
        print(f"  {i}. {frac}")
    print("\nCritical: Rotate FRAC codes, resistance develops in 2-3 years")
    
    print("\n✓ Pumpkin disease detection system initialized")
    print("  Focus: Epidemic disease management (powdery, downy, Phytophthora)")
    print("  Market: $7B global, Halloween/pie markets critical")
