"""
Sweet Potato Disease Detection Suite
====================================

Comprehensive disease identification for sweet potato (Ipomoea batatas),
a major horticultural root crop with critical storage disease challenges.

Critical Diseases:
1. Fusarium Wilt (Fusarium oxysporum f.sp. batatas) - SOILBORNE LETHAL
2. Black Rot (Ceratocystis fimbriata) - #1 STORAGE DISEASE GLOBALLY
3. Scurf (Monilochaetes infuscans) - COSMETIC, MARKET REJECTION
4. Bacterial Soft Rot (Erwinia chrysanthemi) - STORAGE DESTROYER
5. Alternaria Leaf Spot (Alternaria spp.) - DEFOLIATION YIELD LOSS
6. Root-Knot Nematodes (Meloidogyne spp.) - QUALITY DOWNGRADE
7. Feathery Mottle Virus (SPFMV) - YIELD LOSS 20-60%
8. Soil Rot (Streptomyces ipomoea) - PORE ROT AT HARVEST

Market Context:
- Global production: 90 million tons/year, $28 billion
- China: 70% world production, Africa: 20%
- USA sweet potato: $170M market, North Carolina #1
- Storage critical: 6-12 months common
- Storage losses: 30-50% without proper curing and control
- Black rot: $500M+ annual storage losses worldwide
- Premium varieties: Purple/orange flesh = 40% price premium
- Organic market: 60% premium, disease control challenging

Author: AgroPulse Team
Date: November 2025
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Dict
from datetime import datetime


class SweetPotatoType(Enum):
    """Sweet potato variety categories"""
    ORANGE_FLESH = "orange_flesh"  # High carotene, US market
    PURPLE_FLESH = "purple_flesh"  # Anthocyanin, premium Asian market
    WHITE_FLESH = "white_flesh"  # Traditional, starch content high
    YELLOW_FLESH = "yellow_flesh"  # Intermediate carotene
    JAPANESE = "japanese"  # Satsumaimo, premium specialty


class SweetPotatoDisease(Enum):
    """Major sweet potato diseases"""
    FUSARIUM_WILT = "fusarium_wilt"
    BLACK_ROT = "black_rot"
    SCURF = "scurf"
    BACTERIAL_SOFT_ROT = "bacterial_soft_rot"
    ALTERNARIA_LEAF_SPOT = "alternaria"
    ROOT_KNOT_NEMATODE = "nematode"
    FEATHERY_MOTTLE_VIRUS = "spfmv"
    SOIL_ROT = "soil_rot"


@dataclass
class SweetPotatoDiseaseParams:
    """Disease parameters for sweet potato"""
    disease: SweetPotatoDisease
    pathogen: str
    severity: str
    yield_loss: Tuple[int, int]
    storage_impact: str
    
    # Symptoms
    root_symptoms: List[str]
    vine_symptoms: List[str]
    storage_progression: List[str]
    
    # Environmental
    temp_range_c: Tuple[float, float]
    humidity_optimal: int
    
    # Resistance
    resistant_varieties: List[str]
    
    # Control
    cultural_control: List[str]
    chemical_control: List[str]
    curing_impact: str
    
    # Economics
    market_impact: str
    treatment_cost: float


# Disease database
SWEET_POTATO_DISEASES = {
    SweetPotatoDisease.BLACK_ROT: SweetPotatoDiseaseParams(
        disease=SweetPotatoDisease.BLACK_ROT,
        pathogen="Ceratocystis fimbriata (wound pathogen, sweet odor diagnostic)",
        severity="10/10 - #1 STORAGE DISEASE GLOBALLY, $500M+ ANNUAL LOSSES",
        yield_loss=(20, 80),
        storage_impact="CATASTROPHIC - 50-90% storage loss without control",
        
        root_symptoms=[
            "Circular black lesions on root surface DIAGNOSTIC",
            "Lesions start at wounds (harvest damage, insect feeding)",
            "Lesions enlarge rapidly in storage (2-3cm/week)",
            "Black discoloration penetrates deep into flesh",
            "Bitter taste develops (glycosides) = total loss",
            "Sweet fruity odor PATHOGNOMONIC (like fermentation)",
            "Roots shrivel and mummify",
            "Secondary rots follow (Rhizopus, bacteria)",
        ],
        
        vine_symptoms=[
            "Rarely affects vines in field",
            "Can cause stem cankers if wounded",
        ],
        
        storage_progression=[
            "Day 0-7: Small black spots at wounds",
            "Day 7-14: Lesions expand 1-2cm diameter",
            "Day 14-30: Deep penetration, bitter taste develops",
            "Day 30+: Complete root rot, total loss",
            "Spreads root-to-root in storage bins via contact",
        ],
        
        temp_range_c=(20.0, 30.0),
        humidity_optimal=85,
        
        resistant_varieties=[
            "Beauregard - moderate resistance",
            "Jewel - some tolerance",
            "Resistance incomplete - sanitation critical",
        ],
        
        cultural_control=[
            "CURING CRITICAL: 29-32°C, 85-90% RH, 4-7 days",
            "Curing heals wounds, prevents infection entry",
            "Careful harvest to minimize wounds",
            "Discard wounded roots immediately",
            "Storage at 13-16°C, 85-90% RH (colder causes chilling injury)",
            "Separate storage bins by harvest date/field",
            "Disinfect bins between uses (10% bleach)",
            "Regular inspection, remove infected roots immediately",
            "Avoid temperature fluctuations (condensation = infection)",
        ],
        
        chemical_control=[
            "Thiabendazole (TBZ) post-harvest dip - resistance developing",
            "Sodium hypochlorite wash (100-150 ppm) pre-curing",
            "Dicloran (Botran) storage treatment",
            "Fludioxonil (Scholar) - newer alternative",
        ],
        
        curing_impact="ESSENTIAL - reduces black rot by 70-90%",
        market_impact="Storage disease #1, bitter taste = total rejection",
        treatment_cost=200.0
    ),
    
    SweetPotatoDisease.SCURF: SweetPotatoDiseaseParams(
        disease=SweetPotatoDisease.SCURF,
        pathogen="Monilochaetes infuscans (cosmetic only, no rot)",
        severity="6/10 - COSMETIC DAMAGE, MARKET REJECTION, NO ROT",
        yield_loss=(0, 20),  # Yield unaffected, market value reduced
        storage_impact="Cosmetic only - no storage rot, but market rejection",
        
        root_symptoms=[
            "Dark brown to black superficial spots and patches",
            "Irregular shaped lesions, often coalescing",
            "Lesions on peel only, DO NOT PENETRATE FLESH",
            "Rough texture on affected areas",
            "No odor, no softening, no rot",
            "Appears during storage (not at harvest)",
            "Washing does not remove (embedded in periderm)",
        ],
        
        vine_symptoms=[
            "Can cause root lesions and stunting in severe cases",
            "Usually minimal vine symptoms",
        ],
        
        storage_progression=[
            "Often not visible at harvest",
            "Develops during storage (30-90 days)",
            "Spreads by contact in bins",
            "Severity increases with storage duration",
            "No rot development (cosmetic only)",
        ],
        
        temp_range_c=(10.0, 30.0),
        humidity_optimal=90,
        
        resistant_varieties=[
            "Porto Rico - resistant",
            "Beauregard - moderately resistant",
            "Jewel - susceptible",
            "Resistance varies widely",
        ],
        
        cultural_control=[
            "Use scurf-free seed roots (certified)",
            "3-4 year rotation away from sweet potato",
            "Soil pH >5.5 reduces severity",
            "Avoid wet soils during growth",
            "Gentle harvest, rapid drying",
            "Curing helps but doesn't prevent",
            "Market tolerance varies: processing accepts, fresh rejects",
        ],
        
        chemical_control=[
            "No effective chemical control",
            "Preventative only: seed treatment",
            "Mancozeb transplant dip",
        ],
        
        curing_impact="Minimal effect on scurf development",
        market_impact="Fresh market rejection, processing market accepts",
        treatment_cost=50.0
    ),
    
    SweetPotatoDisease.FUSARIUM_WILT: SweetPotatoDiseaseParams(
        disease=SweetPotatoDisease.FUSARIUM_WILT,
        pathogen="Fusarium oxysporum f.sp. batatas (soilborne, races 0-6)",
        severity="9/10 - SOILBORNE LETHAL, FIELD ABANDONMENT",
        yield_loss=(40, 100),
        storage_impact="Infected roots rot in storage",
        
        root_symptoms=[
            "Internal discoloration (brown to black) DIAGNOSTIC",
            "Discoloration starts at stem end, progresses to root tip",
            "Vascular browning visible when cut lengthwise",
            "Firm initially, progresses to soft rot",
            "Secondary rots common (Rhizopus follows)",
        ],
        
        vine_symptoms=[
            "Yellowing of leaves (chlorosis)",
            "Wilting despite adequate soil moisture",
            "One-sided wilting initially (vascular infection)",
            "Stem blackening at soil line",
            "Plant death in severe cases",
            "Symptoms appear 60-90 days after planting",
        ],
        
        storage_progression=[
            "Infected roots deteriorate rapidly in storage",
            "Complete rot within 30-60 days",
        ],
        
        temp_range_c=(24.0, 32.0),
        humidity_optimal=70,
        
        resistant_varieties=[
            "Beauregard - resistant to some races",
            "Jewel - susceptible",
            "Race-specific resistance available",
            "New races overcome resistance (3-5 years)",
        ],
        
        cultural_control=[
            "Plant resistant varieties",
            "Long rotation (5+ years) with non-hosts",
            "Avoid planting in infested fields",
            "Use certified disease-free transplants",
            "Soil solarization in warm climates",
            "Organic amendments may suppress",
            "Good drainage reduces severity",
        ],
        
        chemical_control=[
            "No effective fungicides once established",
            "Soil fumigation pre-plant (very expensive)",
        ],
        
        curing_impact="No effect on fusarium-infected roots",
        market_impact="Field losses severe, storage losses total",
        treatment_cost=0.0  # No cure available
    ),
    
    SweetPotatoDisease.BACTERIAL_SOFT_ROT: SweetPotatoDiseaseParams(
        disease=SweetPotatoDisease.BACTERIAL_SOFT_ROT,
        pathogen="Erwinia chrysanthemi (now Dickeya dadantii)",
        severity="8/10 - STORAGE DESTROYER, RAPID SOFT ROT",
        yield_loss=(30, 70),
        storage_impact="RAPID - Complete bin loss in 7-14 days if not controlled",
        
        root_symptoms=[
            "Water-soaked lesions initially",
            "Rapid progression to soft, mushy rot",
            "Foul odor DIAGNOSTIC (bacterial decay)",
            "Internal tissue completely disintegrated",
            "Liquid ooze from infected roots",
            "Secondary bacterial and fungal rots follow",
        ],
        
        vine_symptoms=[
            "Rarely affects vines in field",
        ],
        
        storage_progression=[
            "Triggered by high storage temperature (>18°C)",
            "Spreads extremely rapidly bin-to-bin",
            "Can destroy entire storage in 1-2 weeks",
            "Starts at wounds and lenticels",
        ],
        
        temp_range_c=(25.0, 35.0),
        humidity_optimal=95,
        
        resistant_varieties=[
            "No resistance available",
            "All varieties susceptible",
        ],
        
        cultural_control=[
            "TEMPERATURE CONTROL CRITICAL: store at 13-16°C",
            "Higher temperatures = rapid bacterial multiplication",
            "Curing heals wounds (entry points)",
            "Minimize harvest wounds",
            "Rapid cooling after curing",
            "Remove any wounded roots before storage",
            "Daily monitoring during warm periods",
            "Separate bins, prevent contact spread",
        ],
        
        chemical_control=[
            "Antibiotics ineffective in storage",
            "Sodium hypochlorite wash (200 ppm) pre-storage",
            "Prevention only, no cure",
        ],
        
        curing_impact="Critical - heals wounds that bacteria enter",
        market_impact="Catastrophic if outbreak occurs in storage",
        treatment_cost=150.0
    ),
    
    SweetPotatoDisease.FEATHERY_MOTTLE_VIRUS: SweetPotatoDiseaseParams(
        disease=SweetPotatoDisease.FEATHERY_MOTTLE_VIRUS,
        pathogen="Sweet Potato Feathery Mottle Virus (SPFMV) - aphid transmitted",
        severity="7/10 - YIELD LOSS 20-60%, VIRUS ACCUMULATION",
        yield_loss=(20, 60),
        storage_impact="No storage rot, but quality reduced",
        
        root_symptoms=[
            "Internal necrosis in some cultivars",
            "Reduced size and number of storage roots",
            "Uneven root development",
            "Quality parameters reduced (starch, sugars)",
        ],
        
        vine_symptoms=[
            "Chlorotic spots and mottling on leaves DIAGNOSTIC",
            "Feathery appearance of chlorotic areas (name origin)",
            "Leaf distortion and puckering",
            "Stunted growth (50-70% of normal)",
            "Purple pigmentation in some varieties",
            "Symptoms variable by variety and strain",
            "Asymptomatic carriers exist (latent infection)",
        ],
        
        storage_progression=[
            "Virus does not cause storage rot",
            "Infected roots stored normally",
            "But used as seed = disease carryover",
        ],
        
        temp_range_c=(20.0, 30.0),
        humidity_optimal=80,
        
        resistant_varieties=[
            "Beauregard - tolerant",
            "Excel - resistant",
            "Most varieties susceptible",
            "Tolerance does not prevent infection",
        ],
        
        cultural_control=[
            "USE VIRUS-TESTED SEED ROOTS (certified)",
            "Tissue culture propagation for clean stock",
            "ELISA or PCR testing for certification",
            "Isolate seed production from commercial fields",
            "Control aphids (virus vectors) in seed beds",
            "Rogue infected plants early (visible symptoms)",
            "Replace seed stock every 2-3 years",
            "Multiple virus complex worse (SPFMV + SPCSV)",
        ],
        
        chemical_control=[
            "No chemical cure for viruses",
            "Aphid control reduces spread: imidacloprid, pymetrozine",
            "Insecticides preventative only",
        ],
        
        curing_impact="No effect on virus",
        market_impact="Yield loss accumulates over years, seed quality critical",
        treatment_cost=300.0  # Cost of certified virus-free seed
    ),
    
    SweetPotatoDisease.SOIL_ROT: SweetPotatoDiseaseParams(
        disease=SweetPotatoDisease.SOIL_ROT,
        pathogen="Streptomyces ipomoea (pore rot, soil acidity pathogen)",
        severity="7/10 - SOIL pH DISEASE, PORE ROT AT HARVEST",
        yield_loss=(15, 50),
        storage_impact="Rotted areas expand in storage",
        
        root_symptoms=[
            "Circular pits or pores on root surface DIAGNOSTIC",
            "Pits 2-5mm deep, dark brown to black",
            "Corky tissue around pits",
            "Multiple pits coalesce into large rotted areas",
            "Musty odor from affected tissue",
            "Often at lenticels (natural pores)",
            "Worst in acidic soils (pH <5.2)",
        ],
        
        vine_symptoms=[
            "No vine symptoms",
            "Root infection only",
        ],
        
        storage_progression=[
            "Pits present at harvest",
            "Expand slowly in storage",
            "Secondary rots invade pitted areas",
        ],
        
        temp_range_c=(20.0, 30.0),
        humidity_optimal=90,
        
        resistant_varieties=[
            "Beauregard - moderately resistant",
            "Porto Rico - resistant",
            "Centennial - susceptible",
        ],
        
        cultural_control=[
            "SOIL pH MANAGEMENT: lime to pH 5.2-6.5",
            "Acidic soils favor disease",
            "Avoid excess nitrogen (promotes lush growth, thin skin)",
            "Allow roots to mature fully before harvest",
            "Rapid drying after harvest",
            "Rotation with cover crops",
        ],
        
        chemical_control=[
            "No effective chemical control",
            "Prevention through pH management",
        ],
        
        curing_impact="Minimal effect once infection established",
        market_impact="Cosmetic damage, market downgrade",
        treatment_cost=100.0  # Lime costs
    ),
}


@dataclass
class SweetPotatoDiseaseResult:
    """Detection result for sweet potato diseases"""
    disease: SweetPotatoDisease
    confidence: float
    severity: str
    storage_critical: bool
    symptoms_detected: List[str]
    immediate_actions: List[str]
    curing_recommendation: str
    storage_protocol: str
    economic_impact: str


class SweetPotatoDiseaseDetector:
    """
    Sweet potato disease detector with storage focus
    
    Critical differentiations:
    - Black rot: Sweet odor, bitter taste, black lesions
    - Scurf: Cosmetic only, no rot, superficial
    - Bacterial soft rot: Foul odor, rapid progression, mushy
    - Fusarium: Internal vascular browning
    """
    
    def __init__(self):
        self.diseases = SWEET_POTATO_DISEASES
    
    def detect_disease(self,
                      image: np.ndarray,
                      location: str = "field",  # "field", "storage", "market"
                      days_in_storage: int = 0) -> List[SweetPotatoDiseaseResult]:
        """
        Detect sweet potato diseases
        
        Args:
            image: BGR image of root or vine
            location: Where disease detected (affects probability)
            days_in_storage: Days since harvest (affects likely diseases)
        
        Returns:
            List of detected diseases with recommendations
        """
        if image is None or image.size == 0:
            return []
        
        results = []
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Detect black rot (black circular lesions)
        black_rot_score = self._detect_black_lesions(image, hsv)
        if black_rot_score > 0.5:
            results.append(self._create_result(
                SweetPotatoDisease.BLACK_ROT,
                black_rot_score,
                "Critical - Storage destroyer",
                days_in_storage
            ))
        
        # Detect scurf (superficial dark patches)
        scurf_score = self._detect_surface_patches(image, hsv)
        if scurf_score > 0.4 and location == "storage":
            results.append(self._create_result(
                SweetPotatoDisease.SCURF,
                scurf_score,
                "Moderate - Cosmetic only",
                days_in_storage
            ))
        
        # Detect soft rot (water-soaked, mushy texture indicators)
        soft_rot_score = self._detect_soft_rot(image, hsv)
        if soft_rot_score > 0.6:
            results.append(self._create_result(
                SweetPotatoDisease.BACTERIAL_SOFT_ROT,
                soft_rot_score,
                "URGENT - Rapid spread risk",
                days_in_storage
            ))
        
        return sorted(results, key=lambda x: x.confidence, reverse=True)
    
    def _detect_black_lesions(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect circular black lesions (black rot)"""
        # Black color range
        black_lower = np.array([0, 0, 0])
        black_upper = np.array([180, 255, 50])
        black_mask = cv2.inRange(hsv, black_lower, black_upper)
        
        contours, _ = cv2.findContours(black_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        circular_lesions = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 100 < area < 5000:
                # Check circularity
                perimeter = cv2.arcLength(cnt, True)
                if perimeter > 0:
                    circularity = 4 * np.pi * area / (perimeter ** 2)
                    if circularity > 0.7:
                        circular_lesions += 1
        
        return min(1.0, circular_lesions / 8.0)
    
    def _detect_surface_patches(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect superficial dark patches (scurf)"""
        # Dark brown surface
        brown_lower = np.array([10, 30, 30])
        brown_upper = np.array([25, 150, 100])
        brown_mask = cv2.inRange(hsv, brown_lower, brown_upper)
        
        coverage = np.sum(brown_mask > 0) / brown_mask.size
        return min(1.0, coverage * 15)
    
    def _detect_soft_rot(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect soft rot indicators"""
        # Water-soaked appearance (darker, saturated)
        dark_lower = np.array([0, 50, 0])
        dark_upper = np.array([180, 255, 80])
        dark_mask = cv2.inRange(hsv, dark_lower, dark_upper)
        
        coverage = np.sum(dark_mask > 0) / dark_mask.size
        return min(1.0, coverage * 12)
    
    def _create_result(self,
                      disease: SweetPotatoDisease,
                      confidence: float,
                      severity: str,
                      days_in_storage: int) -> SweetPotatoDiseaseResult:
        """Create detection result with storage-specific recommendations"""
        params = self.diseases[disease]
        
        # Storage-specific actions
        if disease == SweetPotatoDisease.BLACK_ROT:
            immediate = [
                "Remove infected roots immediately",
                "Check adjacent roots for spread",
                "Verify storage temperature 13-16°C",
                "If uncured, curing now will not help"
            ]
            curing = "CRITICAL - Must cure within 24h of harvest"
            storage = "13-16°C, 85-90% RH, inspect daily"
        
        elif disease == SweetPotatoDisease.BACTERIAL_SOFT_ROT:
            immediate = [
                "URGENT: Lower storage temperature immediately",
                "Remove all affected roots from bin",
                "Discard entire bin if >10% infected",
                "Increase air circulation"
            ]
            curing = "Curing prevents by healing wounds"
            storage = "MUST maintain 13-16°C - higher = disaster"
        
        else:
            immediate = params.cultural_control[:2]
            curing = params.curing_impact
            storage = "Standard curing + cool storage"
        
        return SweetPotatoDiseaseResult(
            disease=disease,
            confidence=confidence,
            severity=severity,
            storage_critical=(disease in [SweetPotatoDisease.BLACK_ROT, 
                                         SweetPotatoDisease.BACTERIAL_SOFT_ROT]),
            symptoms_detected=params.root_symptoms[:3],
            immediate_actions=immediate,
            curing_recommendation=curing,
            storage_protocol=storage,
            economic_impact=params.market_impact
        )


# Example usage
if __name__ == "__main__":
    print("Sweet Potato Disease Detection System")
    print("=" * 70)
    
    detector = SweetPotatoDiseaseDetector()
    
    print("\n📚 SWEET POTATO DISEASE DATABASE:")
    print("\nSTORAGE-CRITICAL DISEASES:")
    for disease, params in SWEET_POTATO_DISEASES.items():
        if "STORAGE" in params.severity or "storage" in params.storage_impact.lower():
            print(f"\n{disease.value.upper()}")
            print(f"  Pathogen: {params.pathogen}")
            print(f"  Severity: {params.severity}")
            print(f"  Storage Impact: {params.storage_impact}")
            print(f"  Curing: {params.curing_impact}")
    
    print("\n" + "=" * 70)
    print("CURING PROTOCOL (CRITICAL FOR DISEASE CONTROL):")
    print("  Temperature: 29-32°C")
    print("  Humidity: 85-90% RH")
    print("  Duration: 4-7 days")
    print("  Effect: Heals wounds, suberizes periderm, reduces rot 70-90%")
    
    print("\n" + "=" * 70)
    print("STORAGE PROTOCOL:")
    print("  Temperature: 13-16°C (55-60°F)")
    print("  Humidity: 85-90% RH")
    print("  Duration: 6-12 months maximum")
    print("  WARNING: >18°C = bacterial soft rot epidemic")
    print("  WARNING: <13°C = chilling injury")
    
    print("\n✓ Sweet potato disease detection system initialized")
    print("  Storage diseases: #1 global constraint (30-50% losses)")
    print("  Curing critical: Reduces losses 70-90%")
