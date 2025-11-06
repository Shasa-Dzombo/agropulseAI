"""
Cauliflower Disease Detection Suite
===================================

Comprehensive disease identification for cauliflower (Brassica oleracea var. botrytis),
a premium brassica crop with critical curd quality and blanching requirements.

Critical Diseases:
1. Bacterial Soft Rot (Erwinia, Pectobacterium) - CURD DESTROYER #1
2. Downy Mildew (Peronospora parasitica) - CURD DISCOLORATION
3. Black Rot (Xanthomonas campestris) - QUARANTINE, VASCULAR
4. Alternaria Leaf Spot (Alternaria brassicae) - DEFOLIATION
5. Clubroot (Plasmodiophora brassicae) - 20+ YEAR PERSISTENCE
6. Brown Rot (Rhizoctonia solani) - CURD BASE INFECTION
7. Bacterial Leaf Spot (Pseudomonas, Xanthomonas) - QUALITY DOWNGRADE
8. White Rust (Albugo candida) - EXPORT RESTRICTION

Market Context:
- Global production: 27 million tons/year, $18 billion
- India: 40% world production, China: 25%
- Premium white curd: $2.50-4.00/lb fresh, quality CRITICAL
- Curd defects: 100% market rejection in premium segment
- Bacterial soft rot: Can destroy 60-90% harvest in 24-48 hours
- Organic cauliflower: 70% premium, disease control challenging
- Colored varieties (purple, orange, green): 50% price premium

Author: AgroPulse Team
Date: November 2025
"""

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional


class CauliflowerType(Enum):
    """Cauliflower variety categories"""
    WHITE = "white"  # Standard, premium fresh market
    PURPLE = "purple"  # Anthocyanin, specialty
    ORANGE = "orange"  # High carotene, "Cheddar"
    GREEN = "green"  # Romanesco type
    SELF_BLANCHING = "self_blanching"  # Leaves wrap curd


class CauliflowerDisease(Enum):
    """Major cauliflower diseases"""
    BACTERIAL_SOFT_ROT = "soft_rot"
    DOWNY_MILDEW = "downy_mildew"
    BLACK_ROT = "black_rot"
    ALTERNARIA_LEAF_SPOT = "alternaria"
    CLUBROOT = "clubroot"
    BROWN_ROT = "brown_rot"
    BACTERIAL_LEAF_SPOT = "bacterial_spot"
    WHITE_RUST = "white_rust"


@dataclass
class CauliflowerDiseaseParams:
    """Disease parameters for cauliflower"""
    disease: CauliflowerDisease
    pathogen: str
    severity: str
    yield_loss: Tuple[int, int]
    curd_impact: str  # Critical for cauliflower
    quarantine_status: bool
    
    # Symptoms
    curd_symptoms: List[str]
    leaf_symptoms: List[str]
    stem_root_symptoms: List[str]
    
    # Environmental
    temp_optimal_c: float
    humidity_optimal: int
    
    # Resistance
    resistant_varieties: List[str]
    resistance_notes: str
    
    # Control
    cultural_control: List[str]
    chemical_control: List[str]
    harvest_timing: str
    
    # Economics
    market_impact: str
    treatment_cost_per_acre: float


# Disease database
CAULIFLOWER_DISEASES = {
    CauliflowerDisease.BACTERIAL_SOFT_ROT: CauliflowerDiseaseParams(
        disease=CauliflowerDisease.BACTERIAL_SOFT_ROT,
        pathogen="Erwinia carotovora, Pectobacterium carotovorum (curd destroyer)",
        severity="10/10 - CATASTROPHIC CURD ROT, 24-48 HOUR LOSS",
        yield_loss=(60, 100),
        curd_impact="TOTAL LOSS - Complete curd disintegration, foul odor",
        quarantine_status=False,
        
        curd_symptoms=[
            "Water-soaked spots on curd surface EARLY WARNING",
            "Rapid progression to brown, mushy rot",
            "Foul odor develops (bacterial decay) DIAGNOSTIC",
            "Complete curd disintegration within 24-48 hours",
            "Liquid ooze from infected tissue",
            "Cannot be salvaged once symptoms appear",
            "Spreads curd-to-curd in field",
            "Worst in high humidity and warm weather",
        ],
        
        leaf_symptoms=[
            "Can start as leaf spot, progresses to curd",
            "Water-soaked lesions on leaves and petioles",
        ],
        
        stem_root_symptoms=[
            "Stem base can rot following curd infection",
        ],
        
        temp_optimal_c=30.0,
        humidity_optimal=95,
        
        resistant_varieties=[
            "No resistance available",
            "All varieties susceptible",
        ],
        resistance_notes="Temperature and moisture management only control",
        
        cultural_control=[
            "AVOID OVERHEAD IRRIGATION DURING CURD FORMATION",
            "Harvest promptly when curds mature (delay = disaster)",
            "Morning harvest when tissues dry",
            "Wide spacing for air circulation (30-36 inches)",
            "Remove lower leaves to expose curd base to air",
            "Do not work in fields when wet",
            "In rainy periods: DAILY scouting, emergency harvest",
            "Rapid post-harvest cooling to 0-2°C",
        ],
        
        chemical_control=[
            "Copper sprays: Minimal preventative effect only",
            "Bactericides largely ineffective once established",
            "Prevention through cultural practices PRIMARY",
        ],
        
        harvest_timing="Harvest immediately at maturity - delay invites disaster",
        market_impact="CATASTROPHIC - 100% curd loss, cannot salvage",
        treatment_cost_per_acre=0.0  # No effective treatment
    ),
    
    CauliflowerDisease.DOWNY_MILDEW: CauliflowerDiseaseParams(
        disease=CauliflowerDisease.DOWNY_MILDEW,
        pathogen="Peronospora parasitica (curd discoloration disaster)",
        severity="9/10 - CURD QUALITY DESTROYER, MARKET REJECTION",
        yield_loss=(40, 80),
        curd_impact="Brown/gray discoloration on curd = 100% rejection",
        quarantine_status=False,
        
        curd_symptoms=[
            "Brown to gray discoloration on curd florets CATASTROPHIC",
            "Purple-gray sporulation may be visible",
            "Cannot be washed off or trimmed away",
            "Total market rejection for fresh market",
            "Curd quality destroyed even with light infection",
        ],
        
        leaf_symptoms=[
            "Yellow angular spots on upper leaf surface",
            "Purple-gray fuzzy growth on leaf undersides DIAGNOSTIC",
            "Lesions follow veins (angular pattern)",
            "Severe defoliation reduces curd size",
            "Can kill young seedlings",
        ],
        
        stem_root_symptoms=[
            "Stem infection uncommon",
        ],
        
        temp_optimal_c=15.0,
        humidity_optimal=95,
        
        resistant_varieties=[
            "Some varieties with partial tolerance",
            "Resistance incomplete in wet years",
        ],
        resistance_notes="Cool wet weather overwhelms resistance",
        
        cultural_control=[
            "Avoid overhead irrigation especially near heading",
            "Wide row spacing (36+ inches)",
            "North-south rows for rapid drying",
            "Remove lower leaves at curd formation",
            "Good field drainage critical",
            "Avoid low-lying fields with poor air circulation",
            "Morning irrigation only (allows drying)",
        ],
        
        chemical_control=[
            "FRAC 40: Cyazofamid (Ranman) - excellent control",
            "FRAC 22: Famoxadone + cymoxanil (Tanos)",
            "FRAC 11: Azoxystrobin, pyraclostrobin (resistance risk)",
            "FRAC P07: Acibenzolar-S-methyl (Actigard) - induced resistance",
            "Begin sprays at heading or earlier in wet conditions",
            "7-day intervals CRITICAL in wet weather",
            "Cost: $300-400/acre for protection",
        ],
        
        harvest_timing="Early harvest in wet weather to prevent curd infection",
        market_impact="Curd discoloration = 100% fresh market rejection",
        treatment_cost_per_acre=350.0
    ),
    
    CauliflowerDisease.BLACK_ROT: CauliflowerDiseaseParams(
        disease=CauliflowerDisease.BLACK_ROT,
        pathogen="Xanthomonas campestris pv. campestris (QUARANTINE)",
        severity="9/10 - QUARANTINE DISEASE, SYSTEMIC VASCULAR",
        yield_loss=(50, 100),
        curd_impact="Black vascular streaks in curd, unmarketable",
        quarantine_status=True,
        
        curd_symptoms=[
            "Black vascular streaks in curd tissue",
            "Curd quality destroyed",
            "Unmarketable for fresh consumption",
        ],
        
        leaf_symptoms=[
            "V-shaped yellow lesions from leaf margin DIAGNOSTIC",
            "Lesions progress toward midrib",
            "Black veins PATHOGNOMONIC (vascular infection)",
            "Leaf margins dry and necrotic",
            "Severe defoliation possible",
        ],
        
        stem_root_symptoms=[
            "Vascular browning visible in stem cross-section",
            "Systemic infection through plant",
        ],
        
        temp_optimal_c=28.0,
        humidity_optimal=85,
        
        resistant_varieties=[
            "Limited resistance available in cauliflower",
        ],
        resistance_notes="Resistance less developed than in cabbage",
        
        cultural_control=[
            "CERTIFIED DISEASE-FREE SEED MANDATORY",
            "Hot water seed treatment: 50°C for 25 minutes",
            "2-3 year rotation away from all brassicas",
            "Remove and destroy crop residues",
            "Control cruciferous weeds (hosts)",
            "Disinfect equipment between fields",
            "Rogue infected plants immediately",
        ],
        
        chemical_control=[
            "NO EFFECTIVE CHEMICAL CONTROL",
            "Copper sprays: Minimal preventative benefit",
            "Prevention through seed sanitation PRIMARY",
        ],
        
        harvest_timing="Do not harvest infected plants - quarantine",
        market_impact="Quarantine disease, regulatory notification required",
        treatment_cost_per_acre=0.0  # No cure available
    ),
    
    CauliflowerDisease.BROWN_ROT: CauliflowerDiseaseParams(
        disease=CauliflowerDisease.BROWN_ROT,
        pathogen="Rhizoctonia solani (soilborne, curd base infection)",
        severity="7/10 - CURD BASE ROT, QUALITY DESTRUCTION",
        yield_loss=(30, 60),
        curd_impact="Brown rot at curd base, stems, spreads upward",
        quarantine_status=False,
        
        curd_symptoms=[
            "Brown, water-soaked lesions at curd base",
            "Rot starts where curd contacts soil or stem",
            "Progresses upward through curd",
            "Mycelium visible in advanced stages",
            "Entire curd can be destroyed",
        ],
        
        leaf_symptoms=[
            "Lower leaves show brown lesions",
            "Stem base browning and girdling",
        ],
        
        stem_root_symptoms=[
            "Brown lesions on stem at soil line",
            "Stem girdling in severe cases",
            "Root rot can occur",
        ],
        
        temp_optimal_c=25.0,
        humidity_optimal=90,
        
        resistant_varieties=[
            "No resistance available",
        ],
        resistance_notes="Cultural control primary strategy",
        
        cultural_control=[
            "Raise curds above soil contact (tie leaves over curd)",
            "Good drainage prevents waterlogging",
            "Avoid excess nitrogen (succulent tissue susceptible)",
            "3-4 year rotation from brassicas",
            "Deep tillage buries inoculum",
            "Remove crop debris after harvest",
        ],
        
        chemical_control=[
            "FRAC 1: PCNB (Terraclor) - soil application",
            "Limited efficacy once infection established",
            "Prevention through cultural practices better",
        ],
        
        harvest_timing="Harvest before curd contacts soil/stem",
        market_impact="Quality downgrade, processing market may accept",
        treatment_cost_per_acre=150.0
    ),
    
    CauliflowerDisease.CLUBROOT: CauliflowerDiseaseParams(
        disease=CauliflowerDisease.CLUBROOT,
        pathogen="Plasmodiophora brassicae (20+ year resting spores)",
        severity="10/10 - FIELD ABANDONMENT, PERSISTENT",
        yield_loss=(50, 100),
        curd_impact="Curds do not form or extremely undersized",
        quarantine_status=False,
        
        curd_symptoms=[
            "Curds fail to form",
            "Extremely small, unmarketable curds",
            "Premature bolting (flowering)",
        ],
        
        leaf_symptoms=[
            "Yellowing, wilting despite adequate moisture",
            "Stunted growth (70-90% size reduction)",
            "Purple pigmentation (nutrient deficiency)",
            "Plant death in severe cases",
        ],
        
        stem_root_symptoms=[
            "Swollen, club-like root galls DIAGNOSTIC",
            "Roots 10x normal diameter",
            "Galls decay releasing resting spores",
            "Spores survive 20+ years in soil",
        ],
        
        temp_optimal_c=20.0,
        humidity_optimal=85,
        
        resistant_varieties=[
            "Limited clubroot resistant cauliflower varieties",
            "More developed in cabbage than cauliflower",
        ],
        resistance_notes="Resistance genes less available than cabbage",
        
        cultural_control=[
            "SOIL pH >7.2 CRITICAL for suppression (lime heavily)",
            "Avoid fields with clubroot history",
            "7+ year rotation (20+ for complete suppression)",
            "Clean equipment thoroughly (spores spread on soil)",
            "Control cruciferous weeds",
            "Improve drainage",
            "Plant resistant varieties if available",
        ],
        
        chemical_control=[
            "No effective fungicide treatment",
            "Fluazinam (Omega): Expensive, suppression only",
        ],
        
        harvest_timing="Infected plants do not produce harvestable curds",
        market_impact="Field loss, 20+ year contamination",
        treatment_cost_per_acre=0.0  # No effective treatment
    ),
}


@dataclass
class CauliflowerDiseaseResult:
    """Detection result for cauliflower diseases"""
    disease: CauliflowerDisease
    confidence: float
    severity: str
    curd_damage: str
    quarantine: bool
    symptoms_detected: List[str]
    immediate_actions: List[str]
    harvest_recommendation: str
    spray_program: List[str]


class CauliflowerDiseaseDetector:
    """
    Cauliflower disease detector with curd quality focus
    
    Critical: Curd defects = 100% rejection in premium market
    
    Key differentiations:
    - Bacterial soft rot: Foul odor, rapid 24-48h progression, mushy
    - Downy mildew: Gray/brown curd discoloration, cannot remove
    - Brown rot: Curd base infection, soil contact disease
    - Black rot: V-shaped leaf lesions, vascular streaks in curd
    """
    
    def __init__(self):
        self.diseases = CAULIFLOWER_DISEASES
    
    def detect_disease(self,
                      image: np.ndarray,
                      plant_part: str = "leaf",  # "leaf", "curd", "root"
                      days_to_harvest: int = 30,
                      weather_wet: bool = False) -> List[CauliflowerDiseaseResult]:
        """
        Detect cauliflower diseases
        
        Args:
            image: BGR image of plant part
            plant_part: "leaf", "curd", or "root"
            days_to_harvest: Days until harvest
            weather_wet: Recent rain/high humidity
        
        Returns:
            List of detected diseases with curd impact assessment
        """
        if image is None or image.size == 0:
            return []
        
        results = []
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        if plant_part == "curd":
            # Bacterial soft rot (water-soaked, mushy)
            soft_rot_score = self._detect_water_soaked_curd(image, hsv)
            if soft_rot_score > 0.5:
                results.append(self._create_result(
                    CauliflowerDisease.BACTERIAL_SOFT_ROT,
                    soft_rot_score,
                    "EMERGENCY - 24-48h to total loss",
                    days_to_harvest,
                    weather_wet
                ))
            
            # Downy mildew (gray/brown discoloration)
            downy_score = self._detect_curd_discoloration(image, hsv)
            if downy_score > 0.4:
                results.append(self._create_result(
                    CauliflowerDisease.DOWNY_MILDEW,
                    downy_score,
                    "CRITICAL - 100% market rejection",
                    days_to_harvest,
                    weather_wet
                ))
            
            # Brown rot (base infection)
            brown_rot_score = self._detect_curd_base_rot(image, hsv)
            if brown_rot_score > 0.4:
                results.append(self._create_result(
                    CauliflowerDisease.BROWN_ROT,
                    brown_rot_score,
                    "Moderate - Quality loss",
                    days_to_harvest,
                    weather_wet
                ))
        
        elif plant_part == "leaf":
            # Black rot (V-shaped lesions)
            black_rot_score = self._detect_v_lesions(image, hsv)
            if black_rot_score > 0.4:
                results.append(self._create_result(
                    CauliflowerDisease.BLACK_ROT,
                    black_rot_score,
                    "QUARANTINE - Rogue immediately",
                    days_to_harvest,
                    weather_wet
                ))
            
            # Downy mildew (purple-gray sporulation)
            downy_leaf_score = self._detect_purple_sporulation(image, hsv)
            if downy_leaf_score > 0.4:
                results.append(self._create_result(
                    CauliflowerDisease.DOWNY_MILDEW,
                    downy_leaf_score,
                    "URGENT - Spray before curd infection",
                    days_to_harvest,
                    weather_wet
                ))
        
        elif plant_part == "root":
            # Clubroot (swollen clubs)
            clubroot_score = self._detect_root_clubs(image, hsv)
            if clubroot_score > 0.5:
                results.append(self._create_result(
                    CauliflowerDisease.CLUBROOT,
                    clubroot_score,
                    "Field contaminated 20+ years",
                    days_to_harvest,
                    weather_wet
                ))
        
        return sorted(results, key=lambda x: x.confidence, reverse=True)
    
    def _detect_water_soaked_curd(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect water-soaked appearance (bacterial soft rot)"""
        # Dark, saturated regions
        dark_lower = np.array([0, 50, 0])
        dark_upper = np.array([180, 255, 100])
        dark_mask = cv2.inRange(hsv, dark_lower, dark_upper)
        
        coverage = np.sum(dark_mask > 0) / dark_mask.size
        return min(1.0, coverage * 12)
    
    def _detect_curd_discoloration(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect gray/brown discoloration (downy mildew)"""
        # Gray-brown on white curd
        gray_lower = np.array([0, 0, 60])
        gray_upper = np.array([180, 100, 140])
        gray_mask = cv2.inRange(hsv, gray_lower, gray_upper)
        
        coverage = np.sum(gray_mask > 0) / gray_mask.size
        return min(1.0, coverage * 15)
    
    def _detect_curd_base_rot(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect brown rot at curd base"""
        # Brown lesions
        brown_lower = np.array([10, 50, 40])
        brown_upper = np.array([25, 200, 120])
        brown_mask = cv2.inRange(hsv, brown_lower, brown_upper)
        
        # Check if concentrated at bottom of image (base)
        bottom_half = brown_mask[brown_mask.shape[0]//2:, :]
        coverage = np.sum(bottom_half > 0) / bottom_half.size
        return min(1.0, coverage * 10)
    
    def _detect_v_lesions(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect V-shaped yellow lesions (black rot)"""
        # Yellow lesions
        yellow_lower = np.array([20, 40, 100])
        yellow_upper = np.array([35, 255, 255])
        yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
        
        # Check edge regions (V-shaped from margin)
        edge_region = yellow_mask[:, :50]
        edge_coverage = np.sum(edge_region > 0) / edge_region.size
        return min(1.0, edge_coverage * 15)
    
    def _detect_purple_sporulation(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect purple-gray sporulation (downy mildew)"""
        # Purple-gray
        purple_lower = np.array([120, 20, 40])
        purple_upper = np.array([160, 150, 150])
        purple_mask = cv2.inRange(hsv, purple_lower, purple_upper)
        
        coverage = np.sum(purple_mask > 0) / purple_mask.size
        return min(1.0, coverage * 18)
    
    def _detect_root_clubs(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect swollen root clubs (clubroot)"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        contours, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        swollen_count = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 500:
                perimeter = cv2.arcLength(cnt, True)
                if perimeter > 0:
                    compactness = area / (perimeter ** 2)
                    if compactness > 0.05:
                        swollen_count += 1
        
        return min(1.0, swollen_count / 5.0)
    
    def _create_result(self,
                      disease: CauliflowerDisease,
                      confidence: float,
                      severity: str,
                      days_to_harvest: int,
                      weather_wet: bool) -> CauliflowerDiseaseResult:
        """Create detection result with curd protection focus"""
        params = self.diseases[disease]
        
        # Disease-specific recommendations
        if disease == CauliflowerDisease.BACTERIAL_SOFT_ROT:
            immediate = [
                "HARVEST IMMEDIATELY if any curds salvageable",
                "Remove infected curds from field",
                "STOP overhead irrigation",
                "Increase air circulation around plants"
            ]
            harvest = "URGENT: Harvest within 24 hours or total loss"
            spray = ["No chemical control", "Cultural practices only"]
        
        elif disease == CauliflowerDisease.DOWNY_MILDEW:
            if days_to_harvest < 7:
                immediate = ["Early harvest to prevent curd infection"]
                harvest = "Harvest ASAP before curd discoloration"
                spray = ["Too late for sprays", "Harvest now"]
            else:
                immediate = ["Begin intensive spray program", "Avoid overhead irrigation"]
                harvest = "Continue protection until harvest"
                spray = [
                    "Week 1: Cyazofamid (FRAC 40)",
                    "Week 2: Famoxadone (FRAC 22)",
                    "Week 3: Rotate back to FRAC 40",
                    "7-day intervals critical"
                ]
        
        elif disease == CauliflowerDisease.BLACK_ROT:
            immediate = [
                "ROGUE infected plants immediately",
                "Burn or bury deep - DO NOT COMPOST",
                "Disinfect tools",
                "Notify authorities if quarantine region"
            ]
            harvest = "Do not harvest infected plants"
            spray = ["No chemical control available"]
        
        elif disease == CauliflowerDisease.CLUBROOT:
            immediate = [
                "Current crop lost",
                "Lime soil to pH >7.2 for future crops",
                "7+ year rotation required"
            ]
            harvest = "Infected plants have no marketable curd"
            spray = ["No effective treatment"]
        
        else:
            immediate = params.cultural_control[:2]
            harvest = params.harvest_timing
            spray = params.chemical_control[:2]
        
        return CauliflowerDiseaseResult(
            disease=disease,
            confidence=confidence,
            severity=severity,
            curd_damage=params.curd_impact,
            quarantine=params.quarantine_status,
            symptoms_detected=params.curd_symptoms[:3] if params.curd_symptoms else params.leaf_symptoms[:3],
            immediate_actions=immediate,
            harvest_recommendation=harvest,
            spray_program=spray
        )


# Example usage
if __name__ == "__main__":
    print("Cauliflower Disease Detection System")
    print("=" * 70)
    
    detector = CauliflowerDiseaseDetector()
    
    print("\n📚 CAULIFLOWER DISEASE DATABASE:")
    print("\nCURD QUALITY DISEASES (CRITICAL):")
    for disease, params in CAULIFLOWER_DISEASES.items():
        if "curd" in params.curd_impact.lower() and ("TOTAL" in params.curd_impact or "100%" in params.curd_impact):
            print(f"\n{disease.value.upper()}")
            print(f"  Pathogen: {params.pathogen}")
            print(f"  Severity: {params.severity}")
            print(f"  Curd Impact: {params.curd_impact}")
            print(f"  Market: {params.market_impact}")
    
    print("\n" + "=" * 70)
    print("CURD PROTECTION PRIORITY:")
    print("  1. Bacterial soft rot: 24-48 hour total loss window")
    print("  2. Downy mildew: Curd discoloration = 100% rejection")
    print("  3. Brown rot: Curd base infection from soil contact")
    print("  4. Quality standard: White, blemish-free curds required")
    
    print("\n" + "=" * 70)
    print("HARVEST TIMING CRITICAL:")
    print("  - Delayed harvest = increased soft rot risk")
    print("  - Wet weather = emergency harvest may be necessary")
    print("  - Morning harvest when tissues dry")
    print("  - Premium market: Zero tolerance for defects")
    
    print("\n✓ Cauliflower disease detection system initialized")
    print("  Focus: Curd quality protection (100% rejection for defects)")
    print("  Market: $18B global, $2.50-4.00/lb premium white curd")
