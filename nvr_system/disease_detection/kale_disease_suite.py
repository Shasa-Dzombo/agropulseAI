"""
Kale Disease Detection Suite
============================

Comprehensive disease identification for kale (Brassica oleracea var. acephala),
premium superfood crop with organic market dominance and brassica disease complexes.

Kale Types:
- Curly kale (most common, hardy)
- Lacinato/Dinosaur (Italian, premium)
- Red Russian (tender, baby kale)
- Siberian (cold hardy)
- Baby kale (premium salad mix, $8-12/lb)

Critical Diseases:
1. Alternaria Leaf Spot (A. brassicae/brassicicola) - #1 DISEASE, SEED-BORNE
2. Downy Mildew (Hyaloperonospora brassicae) - QoI RESISTANCE
3. Black Rot (Xanthomonas campestris) - QUARANTINE, SEED TREATMENT
4. Clubroot (Plasmodiophora brassicae) - 20+ YEAR PERSISTENCE
5. White Rust (Albugo candida) - QUARANTINE, HYBRID RESISTANCE
6. Blackleg (Phoma lingam) - SEED-BORNE, CANOLA PATHOGEN
7. Bacterial Soft Rot (Erwinia/Pectobacterium) - POSTHARVEST
8. Cercospora Leaf Spot - DEFOLIATION

Market Intelligence:
- USA production: $200 million, growing 15% annually
- Organic kale: 80%+ of premium market, $3.50-6.00/lb retail
- Baby kale: $8-12/lb wholesale, 20-day harvest cycles
- Superfood status: Drives premium pricing, appearance critical
- Certified organic: Disease control without synthetics challenging
- Farmers market: Zero tolerance for leaf spots (cosmetic)

Author: AgroPulse Team
Date: November 2025
"""

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional


class KaleType(Enum):
    """Kale variety categories"""
    CURLY = "curly"  # Standard curly, hardy
    LACINATO = "lacinato"  # Italian, dinosaur, flat leaves
    RED_RUSSIAN = "red_russian"  # Purple veins, tender
    SIBERIAN = "siberian"  # Cold hardy, smooth leaves
    BABY_KALE = "baby_kale"  # Premium salad mix


class KaleMarket(Enum):
    """Market channels for kale"""
    ORGANIC_PREMIUM = "organic_premium"  # Certified organic retail
    CONVENTIONAL_RETAIL = "conventional_retail"  # Standard grocery
    BABY_SALAD_MIX = "baby_salad_mix"  # Premium baby kale
    FARMERS_MARKET = "farmers_market"  # Direct consumer
    FOOD_SERVICE = "food_service"  # Restaurant/institutional


class KaleDisease(Enum):
    """Major kale diseases"""
    ALTERNARIA_LEAF_SPOT = "alternaria"
    DOWNY_MILDEW = "downy_mildew"
    BLACK_ROT = "black_rot"
    CLUBROOT = "clubroot"
    WHITE_RUST = "white_rust"
    BLACKLEG = "blackleg"
    BACTERIAL_SOFT_ROT = "soft_rot"
    CERCOSPORA_LEAF_SPOT = "cercospora"


@dataclass
class KaleDiseaseParams:
    """Disease parameters for kale"""
    disease: KaleDisease
    pathogen: str
    severity: str
    yield_loss: Tuple[int, int]
    cosmetic_impact: str  # Critical for kale (appearance-driven sales)
    
    # Symptoms
    leaf_symptoms: List[str]
    petiole_symptoms: List[str]
    root_symptoms: List[str]
    diagnostic_features: str
    
    # Resistance
    resistant_varieties: List[str]
    resistance_genes: List[str]
    
    # Organic control
    organic_control: List[str]  # Critical for 80% organic market
    organic_effectiveness: str
    
    # Conventional control
    conventional_control: List[str]
    fungicide_notes: str
    
    # Economics
    market_impact: str
    treatment_cost_per_acre: float
    organic_premium_at_risk: float  # Lost premium if disease present


# Disease database
KALE_DISEASES = {
    KaleDisease.ALTERNARIA_LEAF_SPOT: KaleDiseaseParams(
        disease=KaleDisease.ALTERNARIA_LEAF_SPOT,
        pathogen="Alternaria brassicae + A. brassicicola (seed-borne, #1 disease)",
        severity="10/10 - #1 KALE DISEASE, COSMETIC DAMAGE, SEED-BORNE",
        yield_loss=(20, 60),
        cosmetic_impact="ANY leaf spots = unmarketable in premium/organic market",
        
        leaf_symptoms=[
            "Circular to irregular brown spots on leaves",
            "Target-ring pattern (concentric rings) DIAGNOSTIC",
            "Yellow halo around spots",
            "Spots 5-20mm diameter",
            "Coalesce to large blighted areas",
            "Premature leaf yellowing and drop",
        ],
        
        petiole_symptoms=[
            "Dark brown to black lesions on petioles",
            "Petiole weakening and collapse",
        ],
        
        root_symptoms=[],
        
        diagnostic_features="Target-ring spots on leaves, seed-borne transmission",
        
        resistant_varieties=[
            "Winterbor (moderate resistance)",
            "Red Russian (some tolerance)",
            "Limited resistance available",
        ],
        resistance_genes=["Quantitative resistance only, no major R genes"],
        
        organic_control=[
            "CERTIFIED DISEASE-FREE SEED critical",
            "Hot water seed treatment: 50°C × 20 min",
            "Copper hydroxide (OMRI listed)",
            "Bacillus subtilis (Serenade) - biofungicide",
            "Trichoderma (RootShield) - preventative",
            "Wide row spacing (18-24 inches)",
            "Avoid overhead irrigation",
            "2-3 year rotation to non-brassicas",
            "Remove infected leaves promptly",
        ],
        organic_effectiveness="MODERATE - prevention critical, curative poor",
        
        conventional_control=[
            "FRAC 7: Boscalid (Endura)",
            "FRAC 11: Azoxystrobin, pyraclostrobin",
            "FRAC 3: Difenoconazole",
            "FRAC M5: Chlorothalonil",
            "Rotate FRAC codes",
            "7-14 day intervals",
            "Begin at first spots",
        ],
        fungicide_notes="QoI (FRAC 11) resistance developing in some regions",
        
        market_impact="CATASTROPHIC in organic/premium - cosmetic damage = rejection",
        treatment_cost_per_acre=180.0,
        organic_premium_at_risk=1200.0  # $3-4/lb premium × yield
    ),
    
    KaleDisease.DOWNY_MILDEW: KaleDiseaseParams(
        disease=KaleDisease.DOWNY_MILDEW,
        pathogen="Hyaloperonospora brassicae (formerly Peronospora parasitica)",
        severity="9/10 - COOL WEATHER DISEASE, QoI RESISTANCE",
        yield_loss=(30, 70),
        cosmetic_impact="Purple-gray sporulation = 100% unmarketable",
        
        leaf_symptoms=[
            "Yellow angular spots on upper leaf surface",
            "Purple-gray fuzzy growth on lower surface",
            "Spots follow veins (angular pattern)",
            "Leaf distortion and curling",
            "Rapid defoliation in cool wet weather",
        ],
        
        petiole_symptoms=[
            "Systemic infection through petioles",
        ],
        
        root_symptoms=[],
        
        diagnostic_features="Angular yellow spots + purple-gray undersides, cool weather",
        
        resistant_varieties=[
            "Winterbor (DM resistance)",
            "Red Russian (moderate resistance)",
            "Some hybrids with resistance",
        ],
        resistance_genes=["Multiple R genes under development"],
        
        organic_control=[
            "Plant resistant varieties",
            "Copper hydroxide (preventative)",
            "Bacillus subtilis (Serenade)",
            "Potassium bicarbonate (MilStop)",
            "Avoid overhead irrigation",
            "Good air circulation (18-24" spacing)",
            "Remove infected leaves",
            "Cool weather scouting critical",
        ],
        organic_effectiveness="GOOD if preventative, resistant varieties help",
        
        conventional_control=[
            "FRAC 40: Cyazofamid (Ranman)",
            "FRAC 43: Fluopicolide (Presidio)",
            "FRAC 22: Famoxadone (Tanos)",
            "FRAC 4: Mefenoxam (if no resistance)",
            "QoI (FRAC 11) resistance developing",
            "7-10 day intervals in cool wet weather",
        ],
        fungicide_notes="QoI resistance reported in some brassica downy mildew populations",
        
        market_impact="Purple sporulation visible = total rejection",
        treatment_cost_per_acre=220.0,
        organic_premium_at_risk=1000.0
    ),
    
    KaleDisease.BLACK_ROT: KaleDiseaseParams(
        disease=KaleDisease.BLACK_ROT,
        pathogen="Xanthomonas campestris pv. campestris (QUARANTINE, seed-borne)",
        severity="10/10 - QUARANTINE DISEASE, SEED TREATMENT MANDATORY",
        yield_loss=(40, 80),
        cosmetic_impact="V-shaped lesions highly visible = total rejection",
        
        leaf_symptoms=[
            "V-shaped yellow lesions from leaf margins",
            "Black vascular veins in lesion PATHOGNOMONIC",
            "Lesions progress toward midrib",
            "Entire leaf may yellow and die",
            "Lesions start at hydathodes (leaf margins)",
        ],
        
        petiole_symptoms=[
            "Black vascular streaks visible in petioles",
            "Systemic vascular infection",
        ],
        
        root_symptoms=[],
        
        diagnostic_features="V-shaped lesions with black veins, seed-borne",
        
        resistant_varieties=[
            "Limited resistance in kale",
            "Some cabbage resistance genes not in kale",
        ],
        resistance_genes=["Resistance breeding ongoing"],
        
        organic_control=[
            "HOT WATER SEED TREATMENT MANDATORY",
            "  - 50°C × 25 minutes",
            "  - Or 52°C × 15 minutes",
            "Certified pathogen-free seed",
            "Copper hydroxide (limited efficacy)",
            "Acibenzolar-S-methyl (SAR inducer, some organic)",
            "3-year rotation to non-brassicas",
            "Remove infected plants immediately",
            "Avoid overhead irrigation",
            "Disinfect tools (10% bleach)",
        ],
        organic_effectiveness="MODERATE - hot water seed treatment essential",
        
        conventional_control=[
            "Hot water seed treatment PRIMARY",
            "Copper + mancozeb",
            "Acibenzolar-S-methyl (Actigard) - SAR",
            "Streptomycin (limited effectiveness)",
            "Preventative only - no cure once infected",
            "Weekly applications",
        ],
        fungicide_notes="No highly effective chemical control, prevention critical",
        
        market_impact="QUARANTINE - field rejection, market access loss",
        treatment_cost_per_acre=200.0,
        organic_premium_at_risk=1500.0  # Potential field rejection
    ),
    
    KaleDisease.CLUBROOT: KaleDiseaseParams(
        disease=KaleDisease.CLUBROOT,
        pathogen="Plasmodiophora brassicae (20+ year soil persistence, pH control)",
        severity="10/10 - CATASTROPHIC, 20+ YEAR PERSISTENCE",
        yield_loss=(50, 100),
        cosmetic_impact="Stunted plants unmarketable",
        
        leaf_symptoms=[
            "Stunted growth",
            "Wilting during hot weather (revive at night)",
            "Yellowing and purple tinge",
            "Poor growth overall",
        ],
        
        petiole_symptoms=[],
        
        root_symptoms=[
            "Severely clubbed, swollen roots DIAGNOSTIC",
            "Root galls resemble clubs or spindles",
            "Galls eventually rot and release spores",
            "Root function impaired",
        ],
        
        diagnostic_features="Clubbed swollen roots + stunted plants, acid soils",
        
        resistant_varieties=[
            "Limited clubroot resistance in kale",
            "More resistance available in cabbage",
            "Resistance breeding priority",
        ],
        resistance_genes=["Crr genes being introduced from canola"],
        
        organic_control=[
            "AVOID INFESTED FIELDS (20+ year contamination)",
            "Raise soil pH to 7.2-7.4 (lime application)",
            "  - High pH suppresses disease",
            "  - Apply 2-4 tons lime/acre",
            "Long rotation (6+ years) to non-brassicas",
            "Brassica trap crops (destroy before flowering)",
            "Clean equipment between fields",
            "NO organic cure once established",
        ],
        organic_effectiveness="PREVENTION ONLY - pH management helps",
        
        conventional_control=[
            "Lime to raise pH >7.2 CRITICAL",
            "Fluazinam (Allegro) soil drench",
            "Prevention in transplants",
            "No cure for infected plants",
            "Avoid infested fields",
        ],
        fungicide_notes="Limited chemical control, pH management most effective",
        
        market_impact="CATASTROPHIC - field abandonment, 20+ year loss",
        treatment_cost_per_acre=400.0,  # Lime + fungicide
        organic_premium_at_risk=2000.0  # Field abandonment
    ),
    
    KaleDisease.WHITE_RUST: KaleDiseaseParams(
        disease=KaleDisease.WHITE_RUST,
        pathogen="Albugo candida (QUARANTINE in some regions, hybrid resistance)",
        severity="8/10 - QUARANTINE POTENTIAL, HYBRID RESISTANCE",
        yield_loss=(20, 50),
        cosmetic_impact="White pustules highly visible = rejection",
        
        leaf_symptoms=[
            "White chalky pustules on lower leaf surface",
            "Raised blisters 1-5mm diameter",
            "Chlorotic spots on upper surface",
            "Leaf distortion in severe cases",
            "Systemic infection causes stunting",
        ],
        
        petiole_symptoms=[
            "Hypertrophy (swelling) of infected tissues",
        ],
        
        root_symptoms=[],
        
        diagnostic_features="White chalky pustules on leaf undersides, quarantine",
        
        resistant_varieties=[
            "Many hybrids have resistance",
            "Check variety disease ratings",
        ],
        resistance_genes=["WR gene effective against most races"],
        
        organic_control=[
            "Plant resistant varieties CRITICAL",
            "Remove infected plants immediately",
            "3-year rotation",
            "Copper hydroxide (limited efficacy)",
            "Scout weekly in cool weather",
        ],
        organic_effectiveness="GOOD with resistant varieties, poor without",
        
        conventional_control=[
            "Plant resistant varieties PRIMARY",
            "FRAC 4: Mefenoxam",
            "FRAC 40: Cyazofamid",
            "Preventative applications",
        ],
        fungicide_notes="Resistance provides best control",
        
        market_impact="Quarantine concern, cosmetic rejection",
        treatment_cost_per_acre=150.0,
        organic_premium_at_risk=800.0
    ),
}


@dataclass
class KaleDiseaseResult:
    """Detection result for kale diseases"""
    disease: KaleDisease
    confidence: float
    severity: str
    cosmetic_impact: str
    organic_compatible_control: List[str]
    market_impact: str
    immediate_actions: List[str]


class KaleDiseaseDetector:
    """
    Kale disease detector with organic market emphasis
    
    Focus on:
    - Cosmetic quality (appearance-driven sales)
    - Organic control methods (80% organic market)
    - Seed-borne diseases (Alternaria, Black Rot)
    - Long-term soil issues (Clubroot 20+ years)
    """
    
    def __init__(self):
        self.diseases = KALE_DISEASES
    
    def detect_disease(self,
                      image: np.ndarray,
                      plant_part: str = "leaf",
                      market_channel: KaleMarket = KaleMarket.ORGANIC_PREMIUM) -> List[KaleDiseaseResult]:
        """
        Detect kale diseases with organic control emphasis
        
        Args:
            image: BGR image
            plant_part: "leaf", "petiole", "root"
            market_channel: Target market (organic premium most sensitive)
        
        Returns:
            List of diseases with organic-compatible recommendations
        """
        if image is None or image.size == 0:
            return []
        
        results = []
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        if plant_part == "leaf":
            # Alternaria (target rings)
            alternaria_score = self._detect_target_rings(image, hsv)
            if alternaria_score > 0.3:
                results.append(self._create_result(
                    KaleDisease.ALTERNARIA_LEAF_SPOT,
                    alternaria_score,
                    market_channel
                ))
            
            # Downy mildew (angular spots)
            downy_score = self._detect_angular_purple(image, hsv)
            if downy_score > 0.4:
                results.append(self._create_result(
                    KaleDisease.DOWNY_MILDEW,
                    downy_score,
                    market_channel
                ))
            
            # Black rot (V-lesions)
            blackrot_score = self._detect_v_lesions(image, hsv)
            if blackrot_score > 0.4:
                results.append(self._create_result(
                    KaleDisease.BLACK_ROT,
                    blackrot_score,
                    market_channel
                ))
            
            # White rust (white pustules)
            whiterust_score = self._detect_white_pustules(image, hsv)
            if whiterust_score > 0.4:
                results.append(self._create_result(
                    KaleDisease.WHITE_RUST,
                    whiterust_score,
                    market_channel
                ))
        
        elif plant_part == "root":
            # Clubroot (swollen roots)
            clubroot_score = self._detect_root_clubs(image, hsv)
            if clubroot_score > 0.5:
                results.append(self._create_result(
                    KaleDisease.CLUBROOT,
                    clubroot_score,
                    market_channel
                ))
        
        return sorted(results, key=lambda x: x.confidence, reverse=True)
    
    def _detect_target_rings(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect target-ring pattern (Alternaria)"""
        brown_lower = np.array([10, 50, 40])
        brown_upper = np.array([25, 200, 150])
        brown_mask = cv2.inRange(hsv, brown_lower, brown_upper)
        
        coverage = np.sum(brown_mask > 0) / brown_mask.size
        return min(1.0, coverage * 18)
    
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
    
    def _detect_v_lesions(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect V-shaped lesions (black rot)"""
        yellow_lower = np.array([20, 50, 100])
        yellow_upper = np.array([35, 255, 255])
        yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
        
        coverage = np.sum(yellow_mask > 0) / yellow_mask.size
        return min(1.0, coverage * 12)
    
    def _detect_white_pustules(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect white chalky pustules (white rust)"""
        white_lower = np.array([0, 0, 200])
        white_upper = np.array([180, 50, 255])
        white_mask = cv2.inRange(hsv, white_lower, white_upper)
        
        coverage = np.sum(white_mask > 0) / white_mask.size
        return min(1.0, coverage * 20)
    
    def _detect_root_clubs(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect swollen clubbed roots (clubroot)"""
        # Look for abnormal root swelling (shape analysis)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return 0.0
        
        # Analyze largest contour for clubbing
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)
        perimeter = cv2.arcLength(largest, True)
        
        if perimeter == 0:
            return 0.0
        
        # Clubbed roots have high area:perimeter ratio
        circularity = 4 * np.pi * area / (perimeter ** 2)
        return min(1.0, circularity * 2.0)
    
    def _create_result(self,
                      disease: KaleDisease,
                      confidence: float,
                      market_channel: KaleMarket) -> KaleDiseaseResult:
        """Create result with organic emphasis"""
        params = self.diseases[disease]
        
        # Adjust severity based on market channel
        if market_channel in [KaleMarket.ORGANIC_PREMIUM, KaleMarket.BABY_SALAD_MIX]:
            cosmetic_emphasis = "CRITICAL - Zero tolerance for cosmetic defects"
        else:
            cosmetic_emphasis = params.cosmetic_impact
        
        # Disease-specific actions
        if disease == KaleDisease.ALTERNARIA_LEAF_SPOT:
            immediate = [
                "Use certified disease-free seed",
                "Hot water seed treatment: 50°C × 20min",
                "Copper hydroxide spray (organic)",
                "Remove infected leaves",
            ]
        elif disease == KaleDisease.BLACK_ROT:
            immediate = [
                "HOT WATER SEED TREATMENT MANDATORY (50°C × 25min)",
                "Remove infected plants immediately",
                "Disinfect tools (10% bleach)",
                "3-year rotation to non-brassicas",
            ]
        elif disease == KaleDisease.CLUBROOT:
            immediate = [
                "AVOID THIS FIELD (20+ year contamination)",
                "Apply lime to raise pH >7.2",
                "6+ year rotation to non-brassicas",
                "NO organic cure available",
            ]
        elif disease == KaleDisease.WHITE_RUST:
            immediate = [
                "Plant resistant varieties immediately",
                "Remove infected plants",
                "Scout weekly in cool weather",
            ]
        else:
            immediate = params.organic_control[:3]
        
        return KaleDiseaseResult(
            disease=disease,
            confidence=confidence,
            severity=params.severity,
            cosmetic_impact=cosmetic_emphasis,
            organic_compatible_control=params.organic_control[:4],
            market_impact=params.market_impact,
            immediate_actions=immediate
        )


# Example usage
if __name__ == "__main__":
    print("Kale Disease Detection System")
    print("=" * 70)
    
    detector = KaleDiseaseDetector()
    
    print("\n📚 KALE DISEASE DATABASE:")
    print("\nCRITICAL DISEASES:")
    for disease, params in KALE_DISEASES.items():
        if disease in [KaleDisease.ALTERNARIA_LEAF_SPOT, KaleDisease.CLUBROOT, KaleDisease.BLACK_ROT]:
            print(f"\n{disease.value.upper()}")
            print(f"  Pathogen: {params.pathogen}")
            print(f"  Severity: {params.severity}")
            print(f"  Cosmetic: {params.cosmetic_impact}")
    
    print("\n" + "=" * 70)
    print("ORGANIC CONTROL EMPHASIS (80% ORGANIC MARKET):")
    alternaria = KALE_DISEASES[KaleDisease.ALTERNARIA_LEAF_SPOT]
    print(f"\nAlternaria (#{1} disease):")
    print(f"  Organic controls: {', '.join(alternaria.organic_control[:3])}")
    print(f"  Effectiveness: {alternaria.organic_effectiveness}")
    
    clubroot = KALE_DISEASES[KaleDisease.CLUBROOT]
    print(f"\nClubroot (20+ year persistence):")
    print(f"  Organic controls: {', '.join(clubroot.organic_control[:3])}")
    print(f"  Effectiveness: {clubroot.organic_effectiveness}")
    
    print("\n" + "=" * 70)
    print("SEED TREATMENT CRITICAL:")
    print("  Alternaria: Hot water 50°C × 20 minutes")
    print("  Black Rot: Hot water 50°C × 25 minutes")
    print("  Certified disease-free seed ESSENTIAL")
    
    print("\n✓ Kale disease detection system initialized")
    print("  Focus: Cosmetic quality, organic control, seed-borne prevention")
    print("  Market: $200M USA, organic 80%+, baby kale $8-12/lb premium")
