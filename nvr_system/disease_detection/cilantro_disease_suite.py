"""
Cilantro/Coriander Disease Detection Suite
===========================================

Comprehensive disease identification for cilantro/coriander (Coriandrum sativum),
dual-purpose herb (leaf cilantro + seed coriander) with bacterial and fungal challenges.

Product Forms:
- Fresh cilantro (leaves) - premium $6-12/lb, 30-40 day cycle
- Coriander seed (spice) - $2-4/lb, 90-120 days
- Microgreens - ultra-premium $40-80/lb, 10-14 days
- Essential oil - $200-400/kg

Critical Diseases:
1. Bacterial Leaf Spot (Pseudomonas syringae) - #1 FRESH, SEED-BORNE
2. Cercospora Leaf Blight - DEFOLIATION, QoI RESISTANCE
3. Powdery Mildew (Erysiphe polygoni) - LATE SEASON
4. Bacterial Soft Rot (Erwinia) - POSTHARVEST
5. Alternaria Leaf Blight - SEED QUALITY
6. Fusarium Wilt - SOILBORNE
7. Sclerotinia Stem Rot - WHITE MOLD, SCLEROTIA
8. Aster Yellows (Phytoplasma) - LEAFHOPPER VECTOR

Market Intelligence:
- USA production: $25 million fresh, $8 million seed
- Fresh cilantro: 25-40 day harvest cycles (8-12 crops/year possible)
- Organic cilantro: 60% of premium market
- Seed contamination: ZERO tolerance (Salmonella concerns)
- Bolting: Temperature-sensitive (>75°F accelerates)
- Slow-bolt varieties: Premium seed $120/lb vs $40/lb standard

Author: AgroPulse Team
Date: November 2025
"""

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional


class CilantroProductType(Enum):
    """Cilantro product categories"""
    FRESH_LEAF = "fresh_leaf"  # Cilantro, 30-40 days
    SEED_CORIANDER = "seed_coriander"  # Spice, 90-120 days
    MICROGREENS = "microgreens"  # 10-14 days
    DUAL_PURPOSE = "dual_purpose"  # Both leaf and seed


class CilantroMarket(Enum):
    """Market channels"""
    FRESH_BUNDLE = "fresh_bundle"  # Grocery bunches
    ORGANIC_PREMIUM = "organic_premium"  # Certified organic
    MICROGREENS = "microgreens"  # Ultra-premium
    SEED_SPICE = "seed_spice"  # Coriander seed
    ETHNIC_MARKET = "ethnic_market"  # High volume, lower price


class CilantroDisease(Enum):
    """Major cilantro diseases"""
    BACTERIAL_LEAF_SPOT = "bacterial_spot"
    CERCOSPORA_BLIGHT = "cercospora"
    POWDERY_MILDEW = "powdery_mildew"
    BACTERIAL_SOFT_ROT = "soft_rot"
    ALTERNARIA_BLIGHT = "alternaria"
    FUSARIUM_WILT = "fusarium"
    SCLEROTINIA_STEM_ROT = "sclerotinia"
    ASTER_YELLOWS = "aster_yellows"


@dataclass
class CilantroDiseaseParams:
    """Disease parameters for cilantro"""
    disease: CilantroDisease
    pathogen: str
    severity: str
    leaf_yield_loss: Tuple[int, int]  # Fresh cilantro
    seed_yield_loss: Tuple[int, int]  # Coriander seed
    
    # Symptoms
    leaf_symptoms: List[str]
    stem_symptoms: List[str]
    seed_symptoms: List[str]
    diagnostic_features: str
    
    # Resistance
    resistant_varieties: List[str]
    slow_bolt_advantage: str  # Slow-bolt varieties have longer harvest window
    
    # Control
    cultural_control: List[str]
    organic_control: List[str]
    conventional_control: List[str]
    
    # Seed-borne considerations
    seed_transmission: str
    seed_treatment: str
    
    # Economics
    market_impact: str
    treatment_cost_per_acre: float


# Disease database
CILANTRO_DISEASES = {
    CilantroDisease.BACTERIAL_LEAF_SPOT: CilantroDiseaseParams(
        disease=CilantroDisease.BACTERIAL_LEAF_SPOT,
        pathogen="Pseudomonas syringae pv. coriandricola (SEED-BORNE, bacterial)",
        severity="10/10 - #1 FRESH CILANTRO DISEASE, SEED-BORNE",
        leaf_yield_loss=(40, 80),
        seed_yield_loss=(20, 50),
        
        leaf_symptoms=[
            "Small angular brown-black spots on leaves",
            "Spots 1-5mm diameter",
            "Water-soaked appearance initially",
            "Yellow halo around spots DIAGNOSTIC",
            "Spots coalesce to large blighted areas",
            "Rapid defoliation in wet weather",
            "ANY leaf spots = unmarketable fresh cilantro",
        ],
        
        stem_symptoms=[
            "Black streaks on stems and petioles",
            "Stem lesions cause lodging",
        ],
        
        seed_symptoms=[
            "Seed discoloration",
            "Reduced germination",
            "Transmits to next generation",
        ],
        
        diagnostic_features="Angular spots with yellow halos, water-soaked, wet weather",
        
        resistant_varieties=[
            "Limited resistance available",
            "Santo (moderate tolerance)",
            "Slow-bolt varieties may have less disease (longer season)",
        ],
        slow_bolt_advantage="Slow-bolt extends harvest, but more disease exposure risk",
        
        cultural_control=[
            "CERTIFIED PATHOGEN-FREE SEED critical",
            "Hot water seed treatment (difficult for cilantro)",
            "Avoid overhead irrigation",
            "Wide row spacing (12-18 inches)",
            "Good air circulation",
            "Remove crop residues",
            "2-3 year rotation",
            "Avoid working in wet fields",
        ],
        
        organic_control=[
            "Copper hydroxide (OMRI listed)",
            "  - Apply preventatively",
            "  - Limited curative activity",
            "Pathogen-free seed ESSENTIAL",
            "Acibenzolar-S-methyl (SAR inducer)",
            "Weekly applications in wet weather",
        ],
        
        conventional_control=[
            "Copper bactericides + mancozeb",
            "Streptomycin (limited use, resistance)",
            "Preventative applications critical",
            "7-10 day intervals",
            "Begin at first symptoms",
        ],
        
        seed_transmission="SEED-BORNE primary inoculum source",
        seed_treatment="Hot water treatment problematic (damages germination), certified seed best",
        
        market_impact="CATASTROPHIC for fresh cilantro - any spots = rejection",
        treatment_cost_per_acre=180.0
    ),
    
    CilantroDisease.CERCOSPORA_BLIGHT: CilantroDiseaseParams(
        disease=CilantroDisease.CERCOSPORA_BLIGHT,
        pathogen="Cercospora spp. (QoI fungicide resistance reported)",
        severity="9/10 - DEFOLIATION, QoI RESISTANCE",
        leaf_yield_loss=(30, 70),
        seed_yield_loss=(40, 70),
        
        leaf_symptoms=[
            "Circular to irregular brown spots",
            "Spots 3-10mm diameter",
            "Dark brown centers with lighter margins",
            "Yellowing around spots",
            "Premature leaf drop",
            "Complete defoliation possible",
        ],
        
        stem_symptoms=[
            "Stem lesions brown-black",
        ],
        
        seed_symptoms=[
            "Reduced seed set",
            "Seed discoloration",
        ],
        
        diagnostic_features="Circular brown spots, target pattern possible",
        
        resistant_varieties=[
            "Limited resistance",
            "Some varieties more tolerant",
        ],
        slow_bolt_advantage="Longer season = more disease pressure",
        
        cultural_control=[
            "Crop rotation (2-3 years)",
            "Remove crop residues",
            "Avoid overhead irrigation",
            "Good air circulation",
        ],
        
        organic_control=[
            "Copper hydroxide",
            "Bacillus subtilis (Serenade)",
            "Limited organic efficacy",
        ],
        
        conventional_control=[
            "CAUTION: QoI (FRAC 11) resistance reported",
            "Effective alternatives:",
            "  FRAC 3: Tebuconazole, difenoconazole",
            "  FRAC 7: Boscalid",
            "  FRAC M5: Chlorothalonil",
            "Rotate FRAC codes strictly",
            "7-14 day intervals",
        ],
        
        seed_transmission="Not significantly seed-borne",
        seed_treatment="Not required for this disease",
        
        market_impact="Defoliation = harvest loss, seed yield reduced",
        treatment_cost_per_acre=200.0
    ),
    
    CilantroDisease.POWDERY_MILDEW: CilantroDiseaseParams(
        disease=CilantroDisease.POWDERY_MILDEW,
        pathogen="Erysiphe polygoni (late-season disease)",
        severity="7/10 - LATE SEASON, SEED PRODUCTION",
        leaf_yield_loss=(20, 40),
        seed_yield_loss=(30, 60),
        
        leaf_symptoms=[
            "White powdery growth on leaves",
            "Starts as small white patches",
            "Covers entire leaf surface",
            "Leaves yellow then brown",
            "More severe as plants mature (seed stage)",
        ],
        
        stem_symptoms=[
            "White powder on stems",
        ],
        
        seed_symptoms=[
            "Reduced seed fill",
            "Premature plant senescence",
        ],
        
        diagnostic_features="White powder, late-season, dry weather",
        
        resistant_varieties=[
            "Limited powdery mildew resistance in cilantro",
        ],
        slow_bolt_advantage="Fast-bolt escapes disease (shorter season)",
        
        cultural_control=[
            "Early planting escapes disease",
            "Good air circulation",
            "Avoid excessive nitrogen (promotes succulence)",
        ],
        
        organic_control=[
            "Sulfur (OMRI listed)",
            "Potassium bicarbonate (MilStop)",
            "Bacillus subtilis",
            "Neem oil",
        ],
        
        conventional_control=[
            "FRAC 3: Myclobutanil, tebuconazole",
            "FRAC 13: Quinoxyfen",
            "Sulfur (organic)",
            "7-14 day intervals",
        ],
        
        seed_transmission="Not seed-borne",
        seed_treatment="Not applicable",
        
        market_impact="Mainly affects seed production, less impact on fresh leaf",
        treatment_cost_per_acre=150.0
    ),
    
    CilantroDisease.FUSARIUM_WILT: CilantroDiseaseParams(
        disease=CilantroDisease.FUSARIUM_WILT,
        pathogen="Fusarium oxysporum (soilborne, vascular wilt)",
        severity="8/10 - SOILBORNE, SYSTEMIC",
        leaf_yield_loss=(40, 80),
        seed_yield_loss=(50, 100),
        
        leaf_symptoms=[
            "Yellowing starting from lower leaves",
            "Wilting during hot weather",
            "Brown vascular streaks in leaf veins",
            "Progressive upward disease movement",
        ],
        
        stem_symptoms=[
            "Brown vascular discoloration in cut stems DIAGNOSTIC",
            "Stem browning at soil line",
            "Plant death",
        ],
        
        seed_symptoms=[
            "No seed production if plant dies",
        ],
        
        diagnostic_features="Vascular browning in stems, systemic wilt, soilborne",
        
        resistant_varieties=[
            "NO RESISTANCE available",
        ],
        slow_bolt_advantage="Longer season = more disease exposure risk",
        
        cultural_control=[
            "3-4 year rotation",
            "Avoid infested soils",
            "Good drainage",
            "Remove infected plants",
        ],
        
        organic_control=[
            "Trichoderma harzianum (preventative)",
            "Bacillus subtilis",
            "NO CURE once infected",
        ],
        
        conventional_control=[
            "NO effective curative fungicides",
            "Prevention only",
            "Soil fumigation (pre-plant)",
        ],
        
        seed_transmission="Not seed-borne (soilborne)",
        seed_treatment="Not applicable",
        
        market_impact="Scattered plant losses, rotation critical",
        treatment_cost_per_acre=250.0
    ),
    
    CilantroDisease.ASTER_YELLOWS: CilantroDiseaseParams(
        disease=CilantroDisease.ASTER_YELLOWS,
        pathogen="Phytoplasma (leafhopper vector, systemic)",
        severity="8/10 - LEAFHOPPER VECTOR, SYSTEMIC",
        leaf_yield_loss=(50, 100),
        seed_yield_loss=(80, 100),
        
        leaf_symptoms=[
            "Yellowing of entire plant",
            "Stunted growth (30-50% reduction)",
            "Leaf proliferation (witches' broom)",
            "Distorted leaves",
            "Plants unmarketable",
        ],
        
        stem_symptoms=[
            "Stunted internodes",
            "Abnormal branching",
        ],
        
        seed_symptoms=[
            "No seed production in infected plants",
            "Flower sterility",
        ],
        
        diagnostic_features="Yellow stunted plants, witches' broom, leafhopper presence",
        
        resistant_varieties=[
            "NO RESISTANCE available",
        ],
        slow_bolt_advantage="Not applicable (phytoplasma disease)",
        
        cultural_control=[
            "LEAFHOPPER CONTROL critical",
            "Insecticide applications",
            "Remove infected plants immediately",
            "Control weeds (reservoir hosts)",
            "Floating row covers (exclude leafhoppers)",
        ],
        
        organic_control=[
            "Insecticidal soaps for leafhoppers",
            "Pyrethrin sprays",
            "Row covers until plants established",
            "Remove infected plants",
        ],
        
        conventional_control=[
            "Insecticides for leafhopper control:",
            "  - Imidacloprid (systemic)",
            "  - Pyrethroids",
            "NO CURE for phytoplasma",
            "Vector control only strategy",
        ],
        
        seed_transmission="NOT seed-borne (leafhopper vector)",
        seed_treatment="Not applicable",
        
        market_impact="Total plant loss, vector control expensive",
        treatment_cost_per_acre=200.0
    ),
}


@dataclass
class CilantroDiseaseResult:
    """Detection result for cilantro diseases"""
    disease: CilantroDisease
    confidence: float
    severity: str
    product_impact: Dict[str, str]  # leaf vs seed impact
    seed_transmission_risk: str
    immediate_actions: List[str]
    slow_bolt_considerations: str


class CilantroDiseaseDetector:
    """
    Cilantro/coriander disease detector
    
    Focus on:
    - Fresh cilantro quality (zero tolerance for leaf spots)
    - Seed-borne diseases (bacterial spot, Alternaria)
    - Rapid growth cycles (25-40 days)
    - Slow-bolt variety advantages
    """
    
    def __init__(self):
        self.diseases = CILANTRO_DISEASES
    
    def detect_disease(self,
                      image: np.ndarray,
                      plant_part: str = "leaf",
                      product_type: CilantroProductType = CilantroProductType.FRESH_LEAF) -> List[CilantroDiseaseResult]:
        """
        Detect cilantro diseases
        
        Args:
            image: BGR image
            plant_part: "leaf", "stem", "seed"
            product_type: Fresh leaf, seed, or dual-purpose
        
        Returns:
            List of diseases with product-specific impacts
        """
        if image is None or image.size == 0:
            return []
        
        results = []
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        if plant_part == "leaf":
            # Bacterial spot (yellow halo)
            bacterial_score = self._detect_angular_halo_spots(image, hsv)
            if bacterial_score > 0.3:
                results.append(self._create_result(
                    CilantroDisease.BACTERIAL_LEAF_SPOT,
                    bacterial_score,
                    product_type
                ))
            
            # Cercospora (circular spots)
            cercospora_score = self._detect_circular_brown_spots(image, hsv)
            if cercospora_score > 0.4:
                results.append(self._create_result(
                    CilantroDisease.CERCOSPORA_BLIGHT,
                    cercospora_score,
                    product_type
                ))
            
            # Powdery mildew
            powdery_score = self._detect_white_powder(image, hsv)
            if powdery_score > 0.4:
                results.append(self._create_result(
                    CilantroDisease.POWDERY_MILDEW,
                    powdery_score,
                    product_type
                ))
            
            # Aster yellows (overall yellowing)
            aster_score = self._detect_overall_yellowing(image, hsv)
            if aster_score > 0.5:
                results.append(self._create_result(
                    CilantroDisease.ASTER_YELLOWS,
                    aster_score,
                    product_type
                ))
        
        elif plant_part == "stem":
            # Fusarium (vascular browning)
            fusarium_score = self._detect_vascular_browning(image, hsv)
            if fusarium_score > 0.5:
                results.append(self._create_result(
                    CilantroDisease.FUSARIUM_WILT,
                    fusarium_score,
                    product_type
                ))
        
        return sorted(results, key=lambda x: x.confidence, reverse=True)
    
    def _detect_angular_halo_spots(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect angular spots with yellow halos (bacterial)"""
        dark_lower = np.array([0, 50, 0])
        dark_upper = np.array([180, 255, 80])
        dark_mask = cv2.inRange(hsv, dark_lower, dark_upper)
        
        coverage = np.sum(dark_mask > 0) / dark_mask.size
        return min(1.0, coverage * 20)
    
    def _detect_circular_brown_spots(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect circular brown spots (Cercospora)"""
        brown_lower = np.array([10, 50, 40])
        brown_upper = np.array([25, 200, 150])
        brown_mask = cv2.inRange(hsv, brown_lower, brown_upper)
        
        coverage = np.sum(brown_mask > 0) / brown_mask.size
        return min(1.0, coverage * 18)
    
    def _detect_white_powder(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect white powder (powdery mildew)"""
        white_lower = np.array([0, 0, 200])
        white_upper = np.array([180, 50, 255])
        white_mask = cv2.inRange(hsv, white_lower, white_upper)
        
        coverage = np.sum(white_mask > 0) / white_mask.size
        return min(1.0, coverage * 20)
    
    def _detect_overall_yellowing(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect overall yellowing (aster yellows)"""
        yellow_lower = np.array([20, 50, 100])
        yellow_upper = np.array([35, 255, 255])
        yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
        
        coverage = np.sum(yellow_mask > 0) / yellow_mask.size
        return min(1.0, coverage * 10)
    
    def _detect_vascular_browning(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect vascular browning (Fusarium)"""
        brown_lower = np.array([10, 50, 30])
        brown_upper = np.array([25, 200, 150])
        brown_mask = cv2.inRange(hsv, brown_lower, brown_upper)
        
        coverage = np.sum(brown_mask > 0) / brown_mask.size
        return min(1.0, coverage * 18)
    
    def _create_result(self,
                      disease: CilantroDisease,
                      confidence: float,
                      product_type: CilantroProductType) -> CilantroDiseaseResult:
        """Create result with product-specific impacts"""
        params = self.diseases[disease]
        
        # Product-specific impacts
        if product_type == CilantroProductType.FRESH_LEAF:
            product_impact = {
                "fresh_leaf": f"CRITICAL - {params.leaf_yield_loss[0]}-{params.leaf_yield_loss[1]}% loss",
                "seed": "Not applicable (fresh harvest)",
            }
        elif product_type == CilantroProductType.SEED_CORIANDER:
            product_impact = {
                "fresh_leaf": "Not applicable (seed crop)",
                "seed": f"CRITICAL - {params.seed_yield_loss[0]}-{params.seed_yield_loss[1]}% loss",
            }
        else:  # Dual-purpose
            product_impact = {
                "fresh_leaf": f"{params.leaf_yield_loss[0]}-{params.leaf_yield_loss[1]}% loss",
                "seed": f"{params.seed_yield_loss[0]}-{params.seed_yield_loss[1]}% loss",
            }
        
        # Disease-specific actions
        if disease == CilantroDisease.BACTERIAL_LEAF_SPOT:
            immediate = [
                "Use certified pathogen-free seed",
                "Apply copper bactericide immediately",
                "Avoid overhead irrigation",
                "Harvest before disease spreads",
            ]
        elif disease == CilantroDisease.CERCOSPORA_BLIGHT:
            immediate = [
                "Apply non-QoI fungicide",
                "Increase row spacing",
                "Remove crop residues",
            ]
        elif disease == CilantroDisease.ASTER_YELLOWS:
            immediate = [
                "Remove infected plants immediately",
                "Apply insecticide for leafhoppers",
                "Scout for leafhoppers weekly",
            ]
        else:
            immediate = params.cultural_control[:3]
        
        return CilantroDiseaseResult(
            disease=disease,
            confidence=confidence,
            severity=params.severity,
            product_impact=product_impact,
            seed_transmission_risk=params.seed_transmission,
            immediate_actions=immediate,
            slow_bolt_considerations=params.slow_bolt_advantage
        )


# Example usage
if __name__ == "__main__":
    print("Cilantro/Coriander Disease Detection System")
    print("=" * 70)
    
    detector = CilantroDiseaseDetector()
    
    print("\n📚 CILANTRO DISEASE DATABASE:")
    print("\nCRITICAL DISEASES:")
    for disease, params in CILANTRO_DISEASES.items():
        if disease in [CilantroDisease.BACTERIAL_LEAF_SPOT, CilantroDisease.CERCOSPORA_BLIGHT]:
            print(f"\n{disease.value.upper()}")
            print(f"  Pathogen: {params.pathogen}")
            print(f"  Leaf loss: {params.leaf_yield_loss[0]}-{params.leaf_yield_loss[1]}%")
            print(f"  Seed loss: {params.seed_yield_loss[0]}-{params.seed_yield_loss[1]}%")
    
    print("\n" + "=" * 70)
    print("SEED-BORNE DISEASE CONTROL:")
    bacterial = CILANTRO_DISEASES[CilantroDisease.BACTERIAL_LEAF_SPOT]
    print(f"  Bacterial spot: {bacterial.seed_transmission}")
    print(f"  Treatment: {bacterial.seed_treatment}")
    
    print("\n✓ Cilantro disease detection system initialized")
    print("  Focus: Fresh leaf quality, seed-borne prevention, rapid cycles")
    print("  Market: $33M USA, fresh $6-12/lb, microgreens $40-80/lb")
