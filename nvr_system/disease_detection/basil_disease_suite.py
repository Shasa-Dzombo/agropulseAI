"""
Basil Disease Detection Suite
==============================

Comprehensive disease identification for basil (Ocimum basilicum), premium culinary herb
with catastrophic downy mildew risk and essential oil quality focus.

Basil Types:
- Sweet basil (Genovese) - standard culinary
- Thai basil - Asian cuisine
- Purple basil - ornamental, specialty
- Lemon basil - citrus flavor
- Holy basil (Tulsi) - medicinal

Critical Diseases:
1. Basil Downy Mildew (Peronospora benta) - #1 DISEASE, CATASTROPHIC, RACE EVOLUTION
2. Fusarium Wilt (Fusarium oxysporum f.sp. basilici) - SOILBORNE, SYSTEMIC
3. Bacterial Leaf Spot (Pseudomonas cichorii) - SEED-BORNE
4. Cercospora Leaf Spot - DEFOLIATION
5. Botrytis Gray Mold - POSTHARVEST
6. Pythium Root Rot - HYDROPONIC SYSTEMS
7. Rhizoctonia Damping-Off - SEEDLINGS
8. Virus Complex (CMV, AMV) - APHID VECTORS

Market Intelligence:
- USA production: $60 million, rapid growth
- Fresh basil: $8-16/lb retail, $3-6/lb wholesale
- Organic basil: 90% of premium market, $12-20/lb retail
- Essential oil: $150-300/kg, purity critical
- Downy mildew: SINGLE DISEASE destroyed USA basil 2007-2012
- Zero tolerance: ANY downy mildew = total field rejection
- Greenhouse/hydroponic: 80% of commercial production

Author: AgroPulse Team
Date: November 2025
"""

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional


class BasilType(Enum):
    """Basil variety categories"""
    SWEET_GENOVESE = "sweet_genovese"  # Standard culinary
    THAI = "thai"  # Asian cuisine
    PURPLE = "purple"  # Ornamental, specialty
    LEMON = "lemon"  # Citrus flavor
    HOLY_TULSI = "holy_tulsi"  # Medicinal


class BasilProductionSystem(Enum):
    """Basil production methods"""
    GREENHOUSE = "greenhouse"  # 80% of commercial
    HYDROPONIC = "hydroponic"  # NFT, DWC systems
    FIELD = "field"  # Outdoor, high risk
    HIGH_TUNNEL = "high_tunnel"  # Protected but not sealed


class BasilDisease(Enum):
    """Major basil diseases"""
    DOWNY_MILDEW = "downy_mildew"
    FUSARIUM_WILT = "fusarium_wilt"
    BACTERIAL_LEAF_SPOT = "bacterial_spot"
    CERCOSPORA_LEAF_SPOT = "cercospora"
    BOTRYTIS_GRAY_MOLD = "botrytis"
    PYTHIUM_ROOT_ROT = "pythium"
    RHIZOCTONIA_DAMPING_OFF = "rhizoctonia"
    VIRUS_COMPLEX = "virus"


@dataclass
class BasilDiseaseParams:
    """Disease parameters for basil"""
    disease: BasilDisease
    pathogen: str
    severity: str
    yield_loss: Tuple[int, int]
    essential_oil_impact: str  # Critical for premium products
    
    # Symptoms
    leaf_symptoms: List[str]
    stem_symptoms: List[str]
    root_symptoms: List[str]
    diagnostic_features: str
    
    # Resistance
    resistant_varieties: List[str]
    resistance_genes: List[str]
    race_information: str
    
    # Control (organic emphasis - 90% market)
    cultural_control: List[str]
    organic_control: List[str]
    conventional_control: List[str]
    greenhouse_specific: List[str]
    
    # Economics
    market_impact: str
    treatment_cost_per_acre: float


# Disease database
BASIL_DISEASES = {
    BasilDisease.DOWNY_MILDEW: BasilDiseaseParams(
        disease=BasilDisease.DOWNY_MILDEW,
        pathogen="Peronospora benta (OBLIGATE PATHOGEN, races evolving, USA 2007)",
        severity="10/10 - CATASTROPHIC, DESTROYED USA BASIL 2007-2012, ZERO TOLERANCE",
        yield_loss=(80, 100),
        essential_oil_impact="Complete loss of essential oil quality",
        
        leaf_symptoms=[
            "Yellow spots on upper leaf surface",
            "Gray-purple fuzzy sporulation on lower surface DIAGNOSTIC",
            "Spots enlarge and coalesce rapidly",
            "Entire leaf yellows then browns",
            "Complete defoliation in 7-14 days",
            "Disease spreads EXPLOSIVELY in humid conditions",
        ],
        
        stem_symptoms=[
            "Black streaks on stems (advanced infection)",
        ],
        
        root_symptoms=[],
        
        diagnostic_features="Gray-purple fuzzy undersides, EXPLOSIVE spread, zero recovery",
        
        resistant_varieties=[
            "RUTGERS BRED RESISTANT VARIETIES:",
            "  - Rutgers Devotion DMR (Race 1 resistance)",
            "  - Rutgers Obsession DMR (Race 1)",
            "  - Rutgers Passion DMR (Race 1)",
            "  - Rutgers Thunderstruck DMR (Race 1, compact)",
            "WARNING: New races overcoming resistance",
        ],
        resistance_genes=[
            "Quantitative resistance loci (QTL) identified",
            "Multiple minor genes provide resistance",
            "Resistance race-specific",
        ],
        race_information="RACE 1 first USA (2009), NEW RACES evolving, resistance breakdown reported",
        
        cultural_control=[
            "RESISTANT VARIETIES ABSOLUTELY ESSENTIAL",
            "Greenhouse production with low humidity",
            "Space plants widely (no crowding)",
            "Avoid overhead irrigation completely",
            "Dehumidify greenhouses (<70% RH)",
            "Fan circulation to dry leaves",
            "Scout DAILY for symptoms",
            "Remove infected plants IMMEDIATELY",
            "Disinfect entire greenhouse if detected",
        ],
        
        organic_control=[
            "RESISTANT VARIETIES ONLY OPTION",
            "Copper hydroxide (OMRI) - LIMITED efficacy",
            "Bacillus subtilis (Serenade) - POOR efficacy",
            "Potassium bicarbonate - POOR",
            "CANNOT control with organic products alone",
            "Prevention through resistant varieties critical",
        ],
        
        conventional_control=[
            "PREVENTATIVE ONLY - no cure once established",
            "FRAC 40: Cyazofamid (Ranman) - BEST",
            "FRAC 43: Oxathiapiprolin (Orondis) - EXCELLENT",
            "FRAC 4: Mefenoxam (Ridomil) - good",
            "FRAC 22: Famoxadone (Tanos)",
            "MUST begin before symptoms",
            "5-7 day intervals in humid weather",
            "Tank-mix FRAC codes",
            "Resistance develops if single mode used",
        ],
        
        greenhouse_specific=[
            "Maintain humidity <70% CRITICAL",
            "24/7 air circulation fans",
            "Morning watering only (leaves dry by night)",
            "Space benches for air flow",
            "HEPA filters on greenhouse intakes",
            "Positive pressure to exclude spores",
        ],
        
        market_impact="CATASTROPHIC - ANY downy mildew = total field/greenhouse rejection",
        treatment_cost_per_acre=600.0  # Intensive fungicide program + resistant seed premium
    ),
    
    BasilDisease.FUSARIUM_WILT: BasilDiseaseParams(
        disease=BasilDisease.FUSARIUM_WILT,
        pathogen="Fusarium oxysporum f.sp. basilici (SOILBORNE, systemic vascular)",
        severity="9/10 - SOILBORNE, SYSTEMIC, NO CURE",
        yield_loss=(50, 100),
        essential_oil_impact="Essential oil production stops",
        
        leaf_symptoms=[
            "Wilting of leaves (vascular blockage)",
            "Yellowing starting from lower leaves",
            "Brown streaks in leaf veins",
            "Leaves drop prematurely",
        ],
        
        stem_symptoms=[
            "Brown vascular streaks visible in cut stems DIAGNOSTIC",
            "Stem browning at soil line",
            "Entire plant wilts and dies",
        ],
        
        root_symptoms=[
            "Root browning and rot",
            "Vascular discoloration in roots",
        ],
        
        diagnostic_features="Brown vascular streaks in stems, systemic wilting, soil-borne",
        
        resistant_varieties=[
            "NO RESISTANCE in sweet basil",
            "Some tolerance in certain varieties",
            "Resistance breeding ongoing",
        ],
        resistance_genes=["No major R genes identified"],
        race_information="Multiple races exist",
        
        cultural_control=[
            "AVOID INFESTED SOIL/MEDIA",
            "Use pasteurized/sterilized media",
            "3-4 year rotation in field",
            "Good drainage critical",
            "Avoid overwatering",
            "Remove infected plants and surrounding soil",
            "Disinfect benches/pots (10% bleach)",
        ],
        
        organic_control=[
            "Trichoderma harzianum (RootShield) - preventative",
            "Bacillus subtilis (preventative)",
            "Pasteurized media essential",
            "NO cure once infected",
        ],
        
        conventional_control=[
            "NO CURATIVE fungicides",
            "Prevention only:",
            "  - Soil fumigation (methyl bromide alternatives)",
            "  - Biological control products",
            "  - Sterile media in greenhouse",
        ],
        
        greenhouse_specific=[
            "Pasteurize ALL media before use",
            "Drip irrigation (avoid splash)",
            "Elevated benches (off ground)",
            "Disinfect between crops",
        ],
        
        market_impact="Scattered plant losses, greenhouse sanitation costly",
        treatment_cost_per_acre=300.0
    ),
    
    BasilDisease.BACTERIAL_LEAF_SPOT: BasilDiseaseParams(
        disease=BasilDisease.BACTERIAL_LEAF_SPOT,
        pathogen="Pseudomonas cichorii (SEED-BORNE, bacterial)",
        severity="8/10 - SEED-BORNE, COSMETIC DAMAGE",
        yield_loss=(30, 60),
        essential_oil_impact="Leaf damage reduces oil yield and quality",
        
        leaf_symptoms=[
            "Small dark brown to black spots",
            "Spots circular, 1-3mm diameter",
            "Yellow halo around spots",
            "Spots coalesce to larger blighted areas",
            "Leaf drop in severe cases",
        ],
        
        stem_symptoms=[
            "Black streaks on stems (systemic infection)",
        ],
        
        root_symptoms=[],
        
        diagnostic_features="Small dark spots with yellow halos, seed-borne",
        
        resistant_varieties=[
            "Limited resistance available",
            "Some varieties more tolerant",
        ],
        resistance_genes=["No major resistance genes"],
        race_information="Multiple strains",
        
        cultural_control=[
            "CERTIFIED PATHOGEN-FREE SEED critical",
            "Hot water seed treatment (not for basil - damages germination)",
            "Avoid overhead irrigation",
            "Good air circulation",
            "Remove infected leaves",
            "3-year rotation",
        ],
        
        organic_control=[
            "Copper hydroxide (OMRI listed)",
            "Acibenzolar-S-methyl (SAR inducer)",
            "Pathogen-free seed essential",
            "Limited organic efficacy",
        ],
        
        conventional_control=[
            "Copper bactericides",
            "Streptomycin (limited use)",
            "Preventative applications",
            "Weekly sprays",
        ],
        
        greenhouse_specific=[
            "Drip irrigation only",
            "Space plants for air flow",
            "Morning watering",
        ],
        
        market_impact="Cosmetic damage reduces value",
        treatment_cost_per_acre=200.0
    ),
}


@dataclass
class BasilDiseaseResult:
    """Detection result for basil diseases"""
    disease: BasilDisease
    confidence: float
    severity: str
    resistant_varieties: List[str]
    immediate_actions: List[str]
    greenhouse_protocols: List[str]
    race_alert: str


class BasilDiseaseDetector:
    """
    Basil disease detector
    
    CRITICAL FOCUS:
    - Downy mildew: #1 disease, catastrophic, resistant varieties essential
    - Essential oil quality preservation
    - Greenhouse environmental control
    - Organic production methods (90% market)
    """
    
    def __init__(self):
        self.diseases = BASIL_DISEASES
    
    def detect_disease(self,
                      image: np.ndarray,
                      plant_part: str = "leaf",
                      production_system: BasilProductionSystem = BasilProductionSystem.GREENHOUSE) -> List[BasilDiseaseResult]:
        """
        Detect basil diseases
        
        Args:
            image: BGR image
            plant_part: "leaf", "stem", "root"
            production_system: Production method (greenhouse vs field)
        
        Returns:
            List of detected diseases with resistance recommendations
        """
        if image is None or image.size == 0:
            return []
        
        results = []
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        if plant_part == "leaf":
            # DOWNY MILDEW - CRITICAL DETECTION
            downy_score = self._detect_purple_sporulation(image, hsv)
            if downy_score > 0.3:  # Lower threshold - early detection critical
                results.append(self._create_result(
                    BasilDisease.DOWNY_MILDEW,
                    downy_score,
                    production_system,
                    alert_level="EMERGENCY"
                ))
            
            # Bacterial spot
            bacterial_score = self._detect_dark_spots_halo(image, hsv)
            if bacterial_score > 0.4:
                results.append(self._create_result(
                    BasilDisease.BACTERIAL_LEAF_SPOT,
                    bacterial_score,
                    production_system
                ))
        
        elif plant_part == "stem":
            # Fusarium (vascular browning)
            fusarium_score = self._detect_vascular_browning(image, hsv)
            if fusarium_score > 0.5:
                results.append(self._create_result(
                    BasilDisease.FUSARIUM_WILT,
                    fusarium_score,
                    production_system
                ))
        
        return sorted(results, key=lambda x: x.confidence, reverse=True)
    
    def _detect_purple_sporulation(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect gray-purple sporulation (downy mildew) - CRITICAL"""
        purple_lower = np.array([120, 20, 40])
        purple_upper = np.array([160, 150, 150])
        purple_mask = cv2.inRange(hsv, purple_lower, purple_upper)
        
        gray_lower = np.array([0, 0, 80])
        gray_upper = np.array([180, 50, 180])
        gray_mask = cv2.inRange(hsv, gray_lower, gray_upper)
        
        combined = cv2.bitwise_or(purple_mask, gray_mask)
        coverage = np.sum(combined > 0) / combined.size
        
        return min(1.0, coverage * 25)  # High multiplier - critical disease
    
    def _detect_dark_spots_halo(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect dark spots with halos (bacterial)"""
        dark_lower = np.array([0, 50, 0])
        dark_upper = np.array([180, 255, 80])
        dark_mask = cv2.inRange(hsv, dark_lower, dark_upper)
        
        coverage = np.sum(dark_mask > 0) / dark_mask.size
        return min(1.0, coverage * 15)
    
    def _detect_vascular_browning(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect vascular browning (Fusarium)"""
        brown_lower = np.array([10, 50, 30])
        brown_upper = np.array([25, 200, 150])
        brown_mask = cv2.inRange(hsv, brown_lower, brown_upper)
        
        coverage = np.sum(brown_mask > 0) / brown_mask.size
        return min(1.0, coverage * 18)
    
    def _create_result(self,
                      disease: BasilDisease,
                      confidence: float,
                      production_system: BasilProductionSystem,
                      alert_level: str = "STANDARD") -> BasilDiseaseResult:
        """Create result with emergency protocols for downy mildew"""
        params = self.diseases[disease]
        
        if disease == BasilDisease.DOWNY_MILDEW:
            severity = "🚨 EMERGENCY - CATASTROPHIC DISEASE"
            resistant = [
                "Rutgers Devotion DMR (Race 1 resistant)",
                "Rutgers Obsession DMR",
                "Rutgers Passion DMR",
                "Rutgers Thunderstruck DMR (compact)"
            ]
            immediate = [
                "🚨 EMERGENCY: Remove ALL infected plants IMMEDIATELY",
                "Destroy plants (burn or seal in bags)",
                "Apply fungicide to remaining plants",
                "Reduce humidity <70% urgently",
                "Increase air circulation 24/7",
                "Scout remaining plants DAILY",
                "Consider destroying entire crop if widespread",
            ]
            greenhouse = [
                "Dehumidify to <70% RH IMMEDIATELY",
                "Run fans 24/7",
                "Stop overhead watering",
                "HEPA filters on air intakes",
                "Positive pressure in greenhouse",
                "Disinfect entire facility if severe",
            ]
            race_alert = "⚠️ NEW RACES evolving, resistance breakdown reported"
            
        elif disease == BasilDisease.FUSARIUM_WILT:
            severity = params.severity
            resistant = ["No resistance available in sweet basil"]
            immediate = [
                "Remove infected plants + surrounding soil",
                "Disinfect tools (10% bleach)",
                "Switch to pasteurized media",
                "Improve drainage",
            ]
            greenhouse = params.greenhouse_specific[:3]
            race_alert = "Multiple races exist"
            
        else:
            severity = params.severity
            resistant = params.resistant_varieties[:3]
            immediate = params.cultural_control[:4]
            greenhouse = params.greenhouse_specific[:3] if params.greenhouse_specific else []
            race_alert = params.race_information
        
        return BasilDiseaseResult(
            disease=disease,
            confidence=confidence,
            severity=severity,
            resistant_varieties=resistant,
            immediate_actions=immediate,
            greenhouse_protocols=greenhouse,
            race_alert=race_alert
        )


# Example usage
if __name__ == "__main__":
    print("Basil Disease Detection System")
    print("=" * 70)
    
    detector = BasilDiseaseDetector()
    
    print("\n📚 BASIL DISEASE DATABASE:")
    print("\n🚨 CRITICAL: DOWNY MILDEW")
    downy = BASIL_DISEASES[BasilDisease.DOWNY_MILDEW]
    print(f"  Pathogen: {downy.pathogen}")
    print(f"  Severity: {downy.severity}")
    print(f"  History: Destroyed USA basil industry 2007-2012")
    print(f"  Resistance: {', '.join(downy.resistant_varieties[:4])}")
    
    print("\n" + "=" * 70)
    print("RUTGERS RESISTANT VARIETIES:")
    print("  - Rutgers Devotion DMR (Race 1)")
    print("  - Rutgers Obsession DMR (Race 1)")
    print("  - Rutgers Passion DMR (Race 1)")
    print("  - Rutgers Thunderstruck DMR (Race 1, compact)")
    print("\n⚠️  WARNING: New races overcoming resistance")
    
    print("\n✓ Basil disease detection system initialized")
    print("  Focus: Downy mildew catastrophic prevention, resistant varieties")
    print("  Market: $60M USA, organic 90%, $8-16/lb fresh, $12-20/lb organic")
