"""
Broccoli Disease Detection Suite
================================

Comprehensive disease identification for broccoli (Brassica oleracea var. italica),
a high-value brassica crop with critical head quality diseases.

Critical Diseases:
1. Black Rot (Xanthomonas campestris pv. campestris) - QUARANTINE WORLDWIDE
2. Downy Mildew (Peronospora parasitica) - HEAD ROT, MARKET REJECTION
3. Alternaria Leaf Spot (Alternaria brassicae, A. brassicicola) - DEFOLIATION
4. Clubroot (Plasmodiophora brassicae) - 20+ YEAR SOIL SURVIVAL
5. White Rust (Albugo candida) - QUARANTINE SOME REGIONS
6. Head Rot Complex (Pseudomonas, Erwinia, Xanthomonas) - CATASTROPHIC
7. Blackleg (Phoma lingam) - STEM GIRDLING, LODGING
8. Bacterial Soft Rot (Erwinia, Pectobacterium) - POST-HARVEST

Market Context:
- Global production: 26 million tons/year, $15 billion
- China: 50% world production, USA: 1.1M tons
- Premium product: $1.50-3.00/lb fresh, quality critical
- Head rot: Can destroy 50-100% of market value in 48 hours
- Clubroot: Fields abandoned 20+ years, $1B+ global losses
- Black rot: Quarantine disease, export restrictions
- Organic premium: 60%, disease control challenging

Author: AgroPulse Team
Date: November 2025
"""

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional


class BroccoliType(Enum):
    """Broccoli variety categories"""
    CALABRESE = "calabrese"  # Standard large head
    SPROUTING = "sprouting"  # Multiple small heads
    ROMANESCO = "romanesco"  # Fractal spiral pattern
    CHINESE = "chinese"  # Gai lan, leafy stems
    BROCCOLINI = "broccolini"  # Hybrid, tender stems


class BroccoliDisease(Enum):
    """Major broccoli diseases"""
    BLACK_ROT = "black_rot"
    DOWNY_MILDEW = "downy_mildew"
    ALTERNARIA_LEAF_SPOT = "alternaria"
    CLUBROOT = "clubroot"
    WHITE_RUST = "white_rust"
    HEAD_ROT = "head_rot"
    BLACKLEG = "blackleg"
    BACTERIAL_SOFT_ROT = "soft_rot"


@dataclass
class BroccoliDiseaseParams:
    """Disease parameters for broccoli"""
    disease: BroccoliDisease
    pathogen: str
    severity: str
    yield_loss: Tuple[int, int]
    quarantine_status: bool
    
    # Symptoms
    head_symptoms: List[str]
    leaf_symptoms: List[str]
    stem_root_symptoms: List[str]
    diagnostic_features: str
    
    # Environmental
    temp_optimal_c: float
    leaf_wetness_hours: int
    soil_survival_years: int
    
    # Resistance
    resistant_varieties: List[str]
    resistance_genes: List[str]
    
    # Control
    cultural_control: List[str]
    chemical_control: List[str]
    seed_treatment: str
    
    # Economics
    market_impact: str
    treatment_cost_per_acre: float


# Disease database
BROCCOLI_DISEASES = {
    BroccoliDisease.BLACK_ROT: BroccoliDiseaseParams(
        disease=BroccoliDisease.BLACK_ROT,
        pathogen="Xanthomonas campestris pv. campestris (QUARANTINE)",
        severity="10/10 - QUARANTINE WORLDWIDE, VASCULAR PATHOGEN",
        yield_loss=(50, 100),
        quarantine_status=True,
        
        head_symptoms=[
            "Black discoloration of head florets",
            "Heads unmarketable",
            "Infection via vascular system from leaves",
        ],
        
        leaf_symptoms=[
            "V-shaped yellow lesions from leaf margin DIAGNOSTIC",
            "Lesions progress toward midrib",
            "Black veins PATHOGNOMONIC (systemic infection)",
            "Leaf margins dry and brown",
            "Severe defoliation",
            "Young plants can be killed",
        ],
        
        stem_root_symptoms=[
            "Vascular browning visible in stem cross-section",
            "Stem girdling in severe cases",
            "Roots usually not directly affected",
        ],
        
        diagnostic_features="V-shaped lesions with black veins, vascular browning",
        temp_optimal_c=28.0,
        leaf_wetness_hours=8,
        soil_survival_years=2,
        
        resistant_varieties=[
            "Limited resistance available",
            "Resistance incomplete",
        ],
        resistance_genes=[
            "Some varieties have partial resistance",
            "Quantitative trait - not single gene",
        ],
        
        cultural_control=[
            "CERTIFIED DISEASE-FREE SEED CRITICAL",
            "Hot water seed treatment: 50°C for 25 minutes",
            "2-3 year rotation away from all brassicas",
            "Remove and destroy crop residues",
            "Control cruciferous weeds (wild mustard hosts)",
            "Avoid overhead irrigation",
            "Disinfect equipment between fields",
            "Scout regularly, rogue infected plants",
        ],
        
        chemical_control=[
            "NO EFFECTIVE CHEMICAL CONTROL",
            "Copper sprays: Limited preventative effect",
            "Acibenzolar-S-methyl (Actigard): Induced resistance",
            "Prevention through sanitation only strategy",
        ],
        
        seed_treatment="Hot water treatment MANDATORY for clean seed",
        market_impact="Quarantine disease, export restrictions, field destruction",
        treatment_cost_per_acre=0.0  # No cure, prevention only
    ),
    
    BroccoliDisease.DOWNY_MILDEW: BroccoliDiseaseParams(
        disease=BroccoliDisease.DOWNY_MILDEW,
        pathogen="Peronospora parasitica (syn. Hyaloperonospora parasitica)",
        severity="9/10 - HEAD ROT, CATASTROPHIC MARKET LOSS",
        yield_loss=(40, 90),
        quarantine_status=False,
        
        head_symptoms=[
            "Gray-purple sporulation on head florets CATASTROPHIC",
            "Heads completely unmarketable",
            "Rot develops within 48 hours of infection",
            "Cannot be removed by washing",
            "Total market rejection",
        ],
        
        leaf_symptoms=[
            "Yellow angular spots on upper leaf surface",
            "Purple-gray sporulation on undersides DIAGNOSTIC",
            "Lesions follow veins (angular shape)",
            "Severe defoliation in wet conditions",
            "Young seedlings can be killed (damping off)",
        ],
        
        stem_root_symptoms=[
            "Stem infection rare",
            "Crown infection can occur",
        ],
        
        diagnostic_features="Purple-gray sporulation on leaf undersides and heads",
        temp_optimal_c=15.0,
        leaf_wetness_hours=12,
        soil_survival_years=5,
        
        resistant_varieties=[
            "Some varieties with tolerance",
            "Resistance incomplete in wet years",
        ],
        resistance_genes=[
            "Multiple QTLs identified",
            "Race-specific resistance exists",
        ],
        
        cultural_control=[
            "Avoid overhead irrigation near heading",
            "Wide row spacing for air circulation",
            "North-south rows for faster drying",
            "Remove lower leaves to increase air flow",
            "Harvest promptly when mature",
            "Avoid working in wet fields (spreads spores)",
        ],
        
        chemical_control=[
            "FRAC 40: Cyazofamid (Ranman) - excellent",
            "FRAC 22: Famoxadone (Tanos)",
            "FRAC 11: Azoxystrobin, pyraclostrobin",
            "FRAC P07: Acibenzolar-S-methyl (plant defense activator)",
            "Begin sprays at heading or first symptoms",
            "7-day intervals in wet weather CRITICAL",
            "Head infection = total loss, prevention essential",
        ],
        
        seed_treatment="Hot water or fungicide seed treatment",
        market_impact="Head infection = 100% market rejection, cannot salvage",
        treatment_cost_per_acre=300.0
    ),
    
    BroccoliDisease.CLUBROOT: BroccoliDiseaseParams(
        disease=BroccoliDisease.CLUBROOT,
        pathogen="Plasmodiophora brassicae (protist, 20+ year soil survival)",
        severity="10/10 - FIELD ABANDONMENT, 20+ YEAR PERSISTENCE",
        yield_loss=(50, 100),
        quarantine_status=False,
        
        head_symptoms=[
            "Heads do not form or extremely small",
            "Premature flowering (bolting) under stress",
        ],
        
        leaf_symptoms=[
            "Yellowing and wilting despite adequate moisture",
            "Stunted growth (50-90% reduction)",
            "Purple pigmentation (phosphorus deficiency-like)",
            "Early plant death in severe cases",
        ],
        
        stem_root_symptoms=[
            "Swollen, distorted roots with clubs/galls DIAGNOSTIC",
            "Clubs can be 10x normal root diameter",
            "Resting spores released when clubs decay",
            "Spores survive 20+ years in soil",
            "Favored by acidic soils (pH <7.2)",
        ],
        
        diagnostic_features="Swollen root clubs, stunting, acidic soil association",
        temp_optimal_c=20.0,
        leaf_wetness_hours=0,
        soil_survival_years=20,  # Resting spores extremely persistent
        
        resistant_varieties=[
            "Starts - resistant",
            "Emerald Pride - resistant",
            "Several CR (clubroot resistant) varieties available",
        ],
        resistance_genes=[
            "Crr1, Crr2, Crr3, Crr4 genes from B. rapa",
            "Rcr1 from fodder turnip",
            "Resistance can be overcome by new pathotypes",
            "At least 19 pathotypes identified",
        ],
        
        cultural_control=[
            "PLANT RESISTANT VARIETIES if clubroot present",
            "Soil pH >7.2 suppresses disease (lime heavily)",
            "7+ year rotation (20+ years for full suppression)",
            "Avoid fields with clubroot history",
            "Clean equipment thoroughly (spores spread on soil)",
            "Control cruciferous weeds (mustard, shepherd's purse hosts)",
            "Improve drainage (waterlogged soils favor disease)",
            "Calcium cyanamide soil amendment (suppressive)",
        ],
        
        chemical_control=[
            "No effective fungicides",
            "Fluazinam (Omega) - suppression only, expensive",
            "Resistance genes primary control strategy",
        ],
        
        seed_treatment="No seed treatment effective",
        market_impact="Field abandonment common, 20+ year loss",
        treatment_cost_per_acre=0.0  # No effective treatment
    ),
    
    BroccoliDisease.HEAD_ROT: BroccoliDiseaseParams(
        disease=BroccoliDisease.HEAD_ROT,
        pathogen="Pseudomonas, Erwinia, Xanthomonas complex (bacterial)",
        severity="9/10 - CATASTROPHIC 48-HOUR ROT, TOTAL LOSS",
        yield_loss=(50, 100),
        quarantine_status=False,
        
        head_symptoms=[
            "Water-soaked florets EARLY DIAGNOSTIC",
            "Rapid progression to brown/black slime",
            "Foul odor develops",
            "Complete head disintegration in 48-72 hours",
            "Cannot be harvested once symptoms appear",
            "Spreads head-to-head in field",
        ],
        
        leaf_symptoms=[
            "May start as leaf spot, progresses to head",
            "Water-soaked lesions",
        ],
        
        stem_root_symptoms=[
            "Stem infection can follow head rot",
        ],
        
        diagnostic_features="Rapid head rot, water-soaked to slime in 48h",
        temp_optimal_c=25.0,
        leaf_wetness_hours=24,
        soil_survival_years=1,
        
        resistant_varieties=[
            "No resistance available",
            "All varieties susceptible",
        ],
        resistance_genes=[],
        
        cultural_control=[
            "AVOID OVERHEAD IRRIGATION AT HEADING",
            "Harvest promptly when mature (delay = risk)",
            "Do not work in wet fields",
            "Wide spacing for air circulation",
            "Remove infected heads immediately",
            "In wet weather: Daily scouting, rapid harvest",
        ],
        
        chemical_control=[
            "Copper sprays: Minimal preventative effect",
            "Bactericides largely ineffective",
            "Prevention only strategy",
        ],
        
        seed_treatment="No seed treatment prevents head rot",
        market_impact="Total loss, 48-hour progression, NO SALVAGE",
        treatment_cost_per_acre=0.0  # Prevention through cultural practice
    ),
    
    BroccoliDisease.ALTERNARIA_LEAF_SPOT: BroccoliDiseaseParams(
        disease=BroccoliDisease.ALTERNARIA_LEAF_SPOT,
        pathogen="Alternaria brassicae, A. brassicicola (seed-borne)",
        severity="7/10 - DEFOLIATION, HEAD SIZE REDUCTION",
        yield_loss=(20, 50),
        quarantine_status=False,
        
        head_symptoms=[
            "Heads undersized due to defoliation",
            "Direct head infection uncommon",
        ],
        
        leaf_symptoms=[
            "Circular brown spots with target pattern DIAGNOSTIC",
            "Concentric rings in lesions (target spot)",
            "Yellow halo around lesions",
            "Starts on older leaves",
            "Coalesce causing severe defoliation",
            "Black fungal sporulation in lesion centers",
        ],
        
        stem_root_symptoms=[
            "Stem lesions can cause girdling",
            "Black streaks on stems",
        ],
        
        diagnostic_features="Target spot pattern with concentric rings",
        temp_optimal_c=25.0,
        leaf_wetness_hours=10,
        soil_survival_years=2,
        
        resistant_varieties=[
            "Limited resistance available",
        ],
        resistance_genes=[],
        
        cultural_control=[
            "Use disease-free seed (seed-borne)",
            "Hot water seed treatment",
            "2-year rotation",
            "Bury crop residues",
            "Avoid overhead irrigation",
        ],
        
        chemical_control=[
            "FRAC 11: Azoxystrobin, pyraclostrobin",
            "FRAC 7: Boscalid",
            "FRAC 3: Difenoconazole",
            "FRAC M5: Chlorothalonil (protectant)",
            "Rotate FRAC codes",
        ],
        
        seed_treatment="Hot water or fungicide treatment recommended",
        market_impact="Head size reduction, aesthetic damage",
        treatment_cost_per_acre=200.0
    ),
}


@dataclass
class BroccoliDiseaseResult:
    """Detection result for broccoli diseases"""
    disease: BroccoliDisease
    confidence: float
    severity: str
    quarantine: bool
    symptoms_detected: List[str]
    immediate_actions: List[str]
    harvest_decision: str
    field_management: str


class BroccoliDiseaseDetector:
    """
    Broccoli disease detector with head quality focus
    
    Critical differentiations:
    - Black rot: V-shaped lesions, black veins, vascular browning
    - Downy mildew: Purple-gray sporulation on heads = catastrophe
    - Clubroot: Root clubs, stunting, acidic soil
    - Head rot: Rapid 48-hour progression, water-soaked to slime
    """
    
    def __init__(self):
        self.diseases = BROCCOLI_DISEASES
    
    def detect_disease(self,
                      image: np.ndarray,
                      plant_part: str = "leaf",  # "leaf", "head", "root"
                      days_to_harvest: int = 30) -> List[BroccoliDiseaseResult]:
        """
        Detect broccoli diseases
        
        Args:
            image: BGR image of plant part
            plant_part: "leaf", "head", or "root"
            days_to_harvest: Days until expected harvest
        
        Returns:
            List of detected diseases with harvest recommendations
        """
        if image is None or image.size == 0:
            return []
        
        results = []
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        if plant_part == "leaf":
            # Detect black rot (V-shaped lesions)
            black_rot_score = self._detect_v_lesions(image, hsv)
            if black_rot_score > 0.4:
                results.append(self._create_result(
                    BroccoliDisease.BLACK_ROT,
                    black_rot_score,
                    "QUARANTINE - Rogue immediately",
                    days_to_harvest,
                    True
                ))
            
            # Detect downy mildew (purple-gray sporulation)
            downy_score = self._detect_purple_sporulation(image, hsv)
            if downy_score > 0.4:
                results.append(self._create_result(
                    BroccoliDisease.DOWNY_MILDEW,
                    downy_score,
                    "CRITICAL if near heading",
                    days_to_harvest,
                    False
                ))
            
            # Detect Alternaria (target spots)
            alternaria_score = self._detect_target_spots(image, hsv)
            if alternaria_score > 0.4:
                results.append(self._create_result(
                    BroccoliDisease.ALTERNARIA_LEAF_SPOT,
                    alternaria_score,
                    "Moderate - Defoliation risk",
                    days_to_harvest,
                    False
                ))
        
        elif plant_part == "head":
            # Detect head rot (water-soaked)
            head_rot_score = self._detect_water_soaked(image, hsv)
            if head_rot_score > 0.5:
                results.append(self._create_result(
                    BroccoliDisease.HEAD_ROT,
                    head_rot_score,
                    "EMERGENCY - 48h to total loss",
                    days_to_harvest,
                    False
                ))
            
            # Detect downy mildew on head (gray sporulation)
            downy_head_score = self._detect_gray_head_sporulation(image, hsv)
            if downy_head_score > 0.3:
                results.append(self._create_result(
                    BroccoliDisease.DOWNY_MILDEW,
                    downy_head_score,
                    "CATASTROPHIC - Total market rejection",
                    days_to_harvest,
                    False
                ))
        
        elif plant_part == "root":
            # Detect clubroot (swollen clubs)
            clubroot_score = self._detect_root_clubs(image, hsv)
            if clubroot_score > 0.5:
                results.append(self._create_result(
                    BroccoliDisease.CLUBROOT,
                    clubroot_score,
                    "Field abandonment likely",
                    days_to_harvest,
                    False
                ))
        
        return sorted(results, key=lambda x: x.confidence, reverse=True)
    
    def _detect_v_lesions(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect V-shaped yellow lesions (black rot)"""
        # Yellow lesions
        yellow_lower = np.array([20, 40, 100])
        yellow_upper = np.array([35, 255, 255])
        yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
        
        # Look for V-shaped patterns (wedge from margin)
        # Simplified: Check for yellow lesions touching image edge
        edge_region = yellow_mask[:, :50]  # Left edge
        edge_coverage = np.sum(edge_region > 0) / edge_region.size
        
        return min(1.0, edge_coverage * 15)
    
    def _detect_purple_sporulation(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect purple-gray sporulation (downy mildew)"""
        # Purple-gray color range
        purple_lower = np.array([120, 20, 40])
        purple_upper = np.array([160, 150, 150])
        purple_mask = cv2.inRange(hsv, purple_lower, purple_upper)
        
        coverage = np.sum(purple_mask > 0) / purple_mask.size
        return min(1.0, coverage * 18)
    
    def _detect_target_spots(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect target spot pattern (Alternaria)"""
        # Brown lesions
        brown_lower = np.array([10, 40, 40])
        brown_upper = np.array([25, 200, 150])
        brown_mask = cv2.inRange(hsv, brown_lower, brown_upper)
        
        contours, _ = cv2.findContours(brown_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        circular_lesions = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 150:
                perimeter = cv2.arcLength(cnt, True)
                if perimeter > 0:
                    circularity = 4 * np.pi * area / (perimeter ** 2)
                    if circularity > 0.6:
                        circular_lesions += 1
        
        return min(1.0, circular_lesions / 8.0)
    
    def _detect_water_soaked(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect water-soaked appearance (head rot)"""
        # Dark, saturated regions
        dark_lower = np.array([0, 50, 0])
        dark_upper = np.array([180, 255, 100])
        dark_mask = cv2.inRange(hsv, dark_lower, dark_upper)
        
        coverage = np.sum(dark_mask > 0) / dark_mask.size
        return min(1.0, coverage * 12)
    
    def _detect_gray_head_sporulation(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect gray sporulation on head (downy mildew)"""
        # Gray color on florets
        gray_lower = np.array([0, 0, 80])
        gray_upper = np.array([180, 50, 160])
        gray_mask = cv2.inRange(hsv, gray_lower, gray_upper)
        
        coverage = np.sum(gray_mask > 0) / gray_mask.size
        return min(1.0, coverage * 20)
    
    def _detect_root_clubs(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect swollen root clubs (clubroot)"""
        # Detect abnormally thick root regions
        # This is simplified - real detection would use shape analysis
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        contours, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        swollen_regions = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 500:
                # Check if rounded (swollen club-like)
                perimeter = cv2.arcLength(cnt, True)
                if perimeter > 0:
                    compactness = area / (perimeter ** 2)
                    if compactness > 0.05:  # Rounded shape
                        swollen_regions += 1
        
        return min(1.0, swollen_regions / 5.0)
    
    def _create_result(self,
                      disease: BroccoliDisease,
                      confidence: float,
                      severity: str,
                      days_to_harvest: int,
                      is_quarantine: bool) -> BroccoliDiseaseResult:
        """Create detection result with harvest decision"""
        params = self.diseases[disease]
        
        # Disease-specific recommendations
        if disease == BroccoliDisease.BLACK_ROT:
            immediate = [
                "ROGUE infected plants immediately",
                "DO NOT COMPOST - burn or bury deep",
                "Disinfect tools and equipment",
                "Notify regulatory authorities if quarantine region"
            ]
            harvest = "Do not harvest infected plants - QUARANTINE"
            field_mgmt = "Consider field abandonment for 2-3 years"
        
        elif disease == BroccoliDisease.HEAD_ROT:
            immediate = [
                "HARVEST IMMEDIATELY if heads salvageable",
                "Remove infected heads from field",
                "Stop overhead irrigation",
                "Increase air circulation"
            ]
            harvest = "URGENT: Harvest within 24 hours or total loss"
            field_mgmt = "48-hour window to save crop"
        
        elif disease == BroccoliDisease.DOWNY_MILDEW:
            if days_to_harvest < 7:
                harvest = "Early harvest recommended if near maturity"
                immediate = ["Harvest ASAP to prevent head infection"]
            else:
                harvest = "Intensive fungicide program, 7-day intervals"
                immediate = ["Begin spray program immediately", "Avoid overhead irrigation"]
            field_mgmt = "Head infection = 100% loss, prevention critical"
        
        elif disease == BroccoliDisease.CLUBROOT:
            immediate = [
                "Lime soil to pH >7.2 for next crop",
                "Plant resistant varieties only",
                "7+ year rotation from brassicas"
            ]
            harvest = "Current crop loss, plan for future"
            field_mgmt = "Field contaminated 20+ years"
        
        else:
            immediate = params.cultural_control[:2]
            harvest = "Normal harvest timing"
            field_mgmt = "Standard rotation and residue management"
        
        return BroccoliDiseaseResult(
            disease=disease,
            confidence=confidence,
            severity=severity,
            quarantine=is_quarantine,
            symptoms_detected=params.leaf_symptoms[:2] if params.leaf_symptoms else params.head_symptoms[:2],
            immediate_actions=immediate,
            harvest_decision=harvest,
            field_management=field_mgmt
        )


# Example usage
if __name__ == "__main__":
    print("Broccoli Disease Detection System")
    print("=" * 70)
    
    detector = BroccoliDiseaseDetector()
    
    print("\n📚 BROCCOLI DISEASE DATABASE:")
    print("\nCRITICAL DISEASES:")
    for disease, params in BROCCOLI_DISEASES.items():
        if params.quarantine_status or "CATASTROPHIC" in params.severity:
            print(f"\n{disease.value.upper()}")
            print(f"  Pathogen: {params.pathogen}")
            print(f"  Severity: {params.severity}")
            print(f"  Quarantine: {params.quarantine_status}")
            print(f"  Market Impact: {params.market_impact}")
    
    print("\n" + "=" * 70)
    print("HEAD QUALITY CRITICAL:")
    print("  Downy mildew on heads: 100% market rejection")
    print("  Head rot: 48-hour progression to total loss")
    print("  Prevention only strategy - no cure once heads infected")
    
    print("\n" + "=" * 70)
    print("CLUBROOT MANAGEMENT:")
    clubroot = BROCCOLI_DISEASES[BroccoliDisease.CLUBROOT]
    print(f"  Soil survival: {clubroot.soil_survival_years}+ years")
    print(f"  Resistance genes: {', '.join(clubroot.resistance_genes[:3])}")
    print("  Control: pH >7.2, resistant varieties, long rotation")
    
    print("\n✓ Broccoli disease detection system initialized")
    print("  Head quality diseases: ZERO tolerance, prevention critical")
    print("  Quarantine diseases: Black rot regulatory compliance required")
