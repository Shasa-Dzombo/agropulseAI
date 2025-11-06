"""
Carrot Disease Detection Suite
==============================

Comprehensive disease identification for carrot (Daucus carota),
a major root vegetable with foliar and storage disease challenges.

Critical Diseases:
1. Alternaria Leaf Blight (Alternaria dauci) - #1 DISEASE WORLDWIDE
2. Cercospora Leaf Spot (Cercospora carotae) - DEFOLIATION SEVERE
3. Cavity Spot (Pythium violae, P. sulcatum) - MARKET REJECTION
4. Bacterial Soft Rot (Erwinia, Pectobacterium) - STORAGE DESTROYER
5. Powdery Mildew (Erysiphe/Leveillula) - LATE-SEASON EPIDEMIC
6. Black Root Rot (Thielaviopsis basicola) - SOILBORNE STUNTING
7. Aster Yellows Phytoplasma - LEAFHOPPER-BORNE, BITTER ROOTS
8. Root-Knot Nematodes (Meloidogyne) - FORKING/GALLING

Market Context:
- Global production: 44 million tons/year, $10 billion
- China: 45% world production, USA: 1.3M tons
- Fresh market: 60% of production, processing: 40%
- Alternaria: Can cause 50-80% yield loss, $200M+ annual damage
- Storage losses: 15-30% without proper conditions
- Premium baby carrots: 40% price premium over standard
- Organic market: 50% premium, disease control challenging

Author: AgroPulse Team
Date: November 2025
"""

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional


class CarrotType(Enum):
    """Carrot variety categories"""
    NANTES = "nantes"  # Cylindrical, sweet, fresh market
    IMPERATOR = "imperator"  # Long, tapered, processing
    CHANTENAY = "chantenay"  # Short, thick, heavy soils
    DANVERS = "danvers"  # Intermediate, adaptable
    BABY = "baby"  # Small, premium fresh market
    COLORED = "colored"  # Purple, yellow, white varieties


class CarrotDisease(Enum):
    """Major carrot diseases"""
    ALTERNARIA_BLIGHT = "alternaria"
    CERCOSPORA_SPOT = "cercospora"
    CAVITY_SPOT = "cavity_spot"
    BACTERIAL_SOFT_ROT = "soft_rot"
    POWDERY_MILDEW = "powdery_mildew"
    BLACK_ROOT_ROT = "black_root_rot"
    ASTER_YELLOWS = "aster_yellows"
    ROOT_KNOT_NEMATODE = "nematode"


@dataclass
class CarrotDiseaseParams:
    """Disease parameters for carrot"""
    disease: CarrotDisease
    pathogen: str
    severity: str
    yield_loss: Tuple[int, int]
    
    # Symptoms
    foliar_symptoms: List[str]
    root_symptoms: List[str]
    diagnostic_features: str
    
    # Environmental
    temp_optimal_c: float
    leaf_wetness_hours: int
    
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
CARROT_DISEASES = {
    CarrotDisease.ALTERNARIA_BLIGHT: CarrotDiseaseParams(
        disease=CarrotDisease.ALTERNARIA_BLIGHT,
        pathogen="Alternaria dauci (#1 carrot disease worldwide)",
        severity="10/10 - EPIDEMIC POTENTIAL, 50-80% YIELD LOSS",
        yield_loss=(30, 80),
        
        foliar_symptoms=[
            "Brown lesions on leaflets DIAGNOSTIC",
            "Lesions have yellow halo around brown center",
            "Starts on older leaves, progresses upward",
            "Severe defoliation (80-100% foliage lost)",
            "Concentric rings in lesions (target spot pattern)",
            "Blackening of entire leaves in severe cases",
            "Petiole infection causes leaf collapse",
            "Rain splash dispersal rapid",
        ],
        
        root_symptoms=[
            "Crown rot at soil line",
            "Black lesions on root shoulders",
            "Reduced root size (30-50% smaller)",
            "Premature harvest due to dying tops",
            "Storage rot can develop from crown infection",
        ],
        
        diagnostic_features="Brown lesions with yellow halos, target spot pattern",
        temp_optimal_c=28.0,
        leaf_wetness_hours=12,
        
        resistant_varieties=[
            "Bolero - good resistance",
            "Resistafly - moderate resistance",
            "Most varieties susceptible",
        ],
        resistance_notes="Resistance incomplete, disease pressure overcomes",
        
        cultural_control=[
            "2-3 year rotation away from carrots/parsley/celery",
            "Buried crop residue (plow down after harvest)",
            "Avoid overhead irrigation when possible",
            "Wider row spacing for air circulation",
            "North-south row orientation for faster drying",
            "Remove volunteer carrots (inoculum sources)",
            "Plant resistant varieties where available",
            "Scout weekly starting 45 days after seeding",
        ],
        
        fungicide_groups=[
            "FRAC 11: Azoxystrobin, pyraclostrobin (resistance common)",
            "FRAC 7: Boscalid",
            "FRAC 3: Difenoconazole, propiconazole",
            "FRAC M5: Chlorothalonil (protectant)",
            "Rotate FRAC codes - resistance develops rapidly",
            "Begin sprays at first symptoms or 45 days",
            "7-14 day intervals depending on pressure",
        ],
        
        market_impact="Can destroy entire crop, premature harvest = small roots",
        treatment_cost_per_acre=250.0
    ),
    
    CarrotDisease.CERCOSPORA_SPOT: CarrotDiseaseParams(
        disease=CarrotDisease.CERCOSPORA_SPOT,
        pathogen="Cercospora carotae (secondary to Alternaria usually)",
        severity="7/10 - DEFOLIATION, COMBINES WITH ALTERNARIA",
        yield_loss=(20, 50),
        
        foliar_symptoms=[
            "Small circular brown spots DIAGNOSTIC",
            "White to gray center as lesions age",
            "Yellow halo less prominent than Alternaria",
            "Numerous small spots (vs fewer large Alternaria)",
            "Coalesce causing leaf blight",
            "Lower leaves affected first",
            "Worse in warm humid conditions",
        ],
        
        root_symptoms=[
            "Minimal direct root impact",
            "Defoliation reduces root size",
        ],
        
        diagnostic_features="Numerous small circular spots with gray centers",
        temp_optimal_c=26.0,
        leaf_wetness_hours=10,
        
        resistant_varieties=[
            "Limited resistance available",
            "Most commercial varieties susceptible",
        ],
        resistance_notes="Often overlooked vs Alternaria",
        
        cultural_control=[
            "Same as Alternaria (often occur together)",
            "Rotation critical",
            "Residue management",
            "Wider spacing",
        ],
        
        fungicide_groups=[
            "Same programs cover both Alternaria and Cercospora",
            "FRAC 11, 7, 3, M5",
        ],
        
        market_impact="Combined with Alternaria = severe defoliation",
        treatment_cost_per_acre=200.0
    ),
    
    CarrotDisease.CAVITY_SPOT: CarrotDiseaseParams(
        disease=CarrotDisease.CAVITY_SPOT,
        pathogen="Pythium violae, P. sulcatum, P. intermedium (soilborne)",
        severity="8/10 - MARKET REJECTION, COSMETIC DISASTER",
        yield_loss=(10, 40),  # Yield less affected, market value destroyed
        
        foliar_symptoms=[
            "No foliar symptoms (root disease only)",
        ],
        
        root_symptoms=[
            "Elliptical sunken lesions on root surface DIAGNOSTIC",
            "Lesions 2-10mm long, dark brown",
            "Often at lenticels (natural pores)",
            "Multiple lesions on single root",
            "Lesions do not enlarge in storage (vs soft rot)",
            "Worst in middle third of root",
            "Secondary rots can invade cavities",
            "Cosmetic damage = total market rejection",
        ],
        
        diagnostic_features="Elliptical sunken pits, multiple per root, at lenticels",
        temp_optimal_c=15.0,
        leaf_wetness_hours=0,  # Soil disease
        
        resistant_varieties=[
            "No effective resistance",
            "All varieties susceptible",
        ],
        resistance_notes="Resistance breeding difficult",
        
        cultural_control=[
            "Soil drainage CRITICAL (waterlogged soils worst)",
            "Avoid fields with history of cavity spot",
            "4+ year rotation",
            "Raised beds improve drainage",
            "Avoid excess irrigation",
            "Soil pH 6.0-6.5 optimal",
            "Organic matter improves soil structure",
            "Cooler soils favor disease (fall crops worse)",
        ],
        
        fungicide_groups=[
            "Metalaxyl seed treatment - limited efficacy",
            "Mefenoxam in-furrow - suppression only",
            "No foliar treatments effective",
            "Prevention through drainage primary",
        ],
        
        market_impact="COSMETIC - fresh market total rejection, processing accepts",
        treatment_cost_per_acre=150.0
    ),
    
    CarrotDisease.BACTERIAL_SOFT_ROT: CarrotDiseaseParams(
        disease=CarrotDisease.BACTERIAL_SOFT_ROT,
        pathogen="Erwinia carotovora, Pectobacterium carotovorum (storage)",
        severity="8/10 - STORAGE DESTROYER, RAPID SPREAD",
        yield_loss=(20, 60),
        
        foliar_symptoms=[
            "Can cause bacterial soft rot in field (rare)",
            "Usually post-harvest storage disease",
        ],
        
        root_symptoms=[
            "Water-soaked lesions initially",
            "Rapid progression to complete soft rot",
            "Foul odor DIAGNOSTIC (bacterial decay)",
            "Tissue completely disintegrated, liquid",
            "Starts at wounds, cracks, insect damage",
            "Spreads root-to-root in storage",
            "Can destroy bins in 1-2 weeks",
            "Worse at high storage temperatures (>5°C)",
        ],
        
        diagnostic_features="Foul odor, complete tissue disintegration, liquid ooze",
        temp_optimal_c=30.0,
        leaf_wetness_hours=0,
        
        resistant_varieties=[
            "No resistance",
            "All varieties susceptible",
        ],
        resistance_notes="Wound avoidance critical",
        
        cultural_control=[
            "STORAGE TEMPERATURE: 0-2°C critical",
            "95-100% relative humidity",
            "Careful harvest to minimize wounds",
            "Rapid cooling after harvest",
            "Remove wounded/cracked roots before storage",
            "Disinfect storage bins",
            "Daily monitoring in storage",
            "Remove infected roots immediately",
        ],
        
        fungicide_groups=[
            "No chemical control",
            "Antibiotics ineffective in storage",
            "Prevention only strategy",
        ],
        
        market_impact="Can destroy entire storage",
        treatment_cost_per_acre=100.0  # Cooling costs
    ),
    
    CarrotDisease.POWDERY_MILDEW: CarrotDiseaseParams(
        disease=CarrotDisease.POWDERY_MILDEW,
        pathogen="Erysiphe heraclei, Leveillula taurica (late-season)",
        severity="6/10 - LATE-SEASON, QUALITY REDUCTION",
        yield_loss=(10, 30),
        
        foliar_symptoms=[
            "White powdery growth on leaves DIAGNOSTIC",
            "Both upper and lower leaf surfaces",
            "Starts as small white patches",
            "Coalesces to cover entire leaf",
            "Leaves turn yellow, then brown",
            "Late-season disease (harvest approaching)",
            "Worse in dry weather (vs most fungal diseases)",
        ],
        
        root_symptoms=[
            "Minimal if disease occurs late",
            "Early severe infection reduces root size",
        ],
        
        diagnostic_features="White powder on leaves, late season, dry conditions",
        temp_optimal_c=25.0,
        leaf_wetness_hours=0,  # Dry weather disease
        
        resistant_varieties=[
            "Limited resistance breeding",
        ],
        resistance_notes="Late-season timing reduces impact",
        
        cultural_control=[
            "Often not economical to treat (harvest approaching)",
            "Avoid excess nitrogen (lush growth susceptible)",
            "Good air circulation",
        ],
        
        fungicide_groups=[
            "FRAC 11: Azoxystrobin",
            "FRAC 3: Myclobutanil, tebuconazole",
            "FRAC 13: Quinoxyfen",
            "Sulfur (organic)",
        ],
        
        market_impact="Minimal if occurs near harvest",
        treatment_cost_per_acre=80.0
    ),
    
    CarrotDisease.ASTER_YELLOWS: CarrotDiseaseParams(
        disease=CarrotDisease.ASTER_YELLOWS,
        pathogen="Aster Yellows Phytoplasma (leafhopper vector)",
        severity="7/10 - PHYTOPLASMA, BITTER ROOTS, NO CURE",
        yield_loss=(30, 100),
        
        foliar_symptoms=[
            "Yellowing of new growth (chlorosis)",
            "Excessive branching (witches' broom) DIAGNOSTIC",
            "Twisted, distorted leaves",
            "Proliferation of secondary shoots",
            "Stunted growth",
            "Symptoms appear 3-6 weeks after infection",
        ],
        
        root_symptoms=[
            "Numerous small hairy roots (excessive lateral roots)",
            "Bitter taste DIAGNOSTIC",
            "Pale color (reduced pigments)",
            "Unmarketable due to bitterness",
            "Root size reduced",
        ],
        
        diagnostic_features="Excessive branching, hairy roots, bitter taste",
        temp_optimal_c=25.0,
        leaf_wetness_hours=0,
        
        resistant_varieties=[
            "No resistance available",
            "All varieties susceptible",
        ],
        resistance_notes="Vector control only option",
        
        cultural_control=[
            "Control leafhoppers (vectors) CRITICAL",
            "Remove infected plants immediately",
            "Avoid planting near aster family weeds",
            "Row covers can exclude leafhoppers",
            "Scout for leafhoppers weekly",
        ],
        
        fungicide_groups=[
            "No treatment for phytoplasma",
            "Insecticides for leafhopper control:",
            "Imidacloprid, thiamethoxam (systemics)",
            "Pyrethroids for quick knockdown",
        ],
        
        market_impact="Bitter roots = total loss, unmarketable",
        treatment_cost_per_acre=120.0
    ),
}


@dataclass
class CarrotDiseaseResult:
    """Detection result for carrot diseases"""
    disease: CarrotDisease
    confidence: float
    severity: str
    symptoms_detected: List[str]
    immediate_actions: List[str]
    spray_program: List[str]
    harvest_recommendation: str


class CarrotDiseaseDetector:
    """
    Carrot disease detector focusing on Alternaria (disease #1)
    
    Key differentiations:
    - Alternaria: Large lesions, yellow halo, target spots
    - Cercospora: Small numerous spots, gray centers
    - Cavity spot: Sunken pits on roots, cosmetic
    - Soft rot: Foul odor, complete breakdown
    """
    
    def __init__(self):
        self.diseases = CARROT_DISEASES
    
    def detect_disease(self,
                      image: np.ndarray,
                      plant_part: str = "foliage",  # "foliage" or "root"
                      days_from_seeding: int = 0) -> List[CarrotDiseaseResult]:
        """
        Detect carrot diseases
        
        Args:
            image: BGR image of foliage or root
            plant_part: "foliage" or "root"
            days_from_seeding: Days since planting
        
        Returns:
            List of detected diseases with spray recommendations
        """
        if image is None or image.size == 0:
            return []
        
        results = []
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        if plant_part == "foliage":
            # Detect Alternaria (large brown lesions with yellow halos)
            alternaria_score = self._detect_alternaria_lesions(image, hsv)
            if alternaria_score > 0.4:
                results.append(self._create_result(
                    CarrotDisease.ALTERNARIA_BLIGHT,
                    alternaria_score,
                    "CRITICAL - Begin spray program immediately",
                    days_from_seeding
                ))
            
            # Detect Cercospora (small numerous spots)
            cercospora_score = self._detect_cercospora_spots(image, hsv)
            if cercospora_score > 0.4:
                results.append(self._create_result(
                    CarrotDisease.CERCOSPORA_SPOT,
                    cercospora_score,
                    "Moderate - Often with Alternaria",
                    days_from_seeding
                ))
            
            # Detect powdery mildew (white powder)
            powdery_score = self._detect_white_powder(image, hsv)
            if powdery_score > 0.5:
                results.append(self._create_result(
                    CarrotDisease.POWDERY_MILDEW,
                    powdery_score,
                    "Late-season disease",
                    days_from_seeding
                ))
        
        elif plant_part == "root":
            # Detect cavity spot (sunken pits)
            cavity_score = self._detect_cavity_pits(image, hsv)
            if cavity_score > 0.4:
                results.append(self._create_result(
                    CarrotDisease.CAVITY_SPOT,
                    cavity_score,
                    "Cosmetic - Market rejection",
                    days_from_seeding
                ))
        
        return sorted(results, key=lambda x: x.confidence, reverse=True)
    
    def _detect_alternaria_lesions(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect large brown lesions with yellow halos (Alternaria)"""
        # Brown lesion centers
        brown_lower = np.array([10, 40, 40])
        brown_upper = np.array([25, 255, 150])
        brown_mask = cv2.inRange(hsv, brown_lower, brown_upper)
        
        # Yellow halos
        yellow_lower = np.array([20, 50, 100])
        yellow_upper = np.array([35, 255, 255])
        yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
        
        # Combine
        combined = cv2.bitwise_or(brown_mask, yellow_mask)
        
        contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        large_lesions = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 200:  # Large lesions
                large_lesions += 1
        
        return min(1.0, large_lesions / 10.0)
    
    def _detect_cercospora_spots(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect numerous small circular spots (Cercospora)"""
        # Gray-brown centers
        gray_lower = np.array([0, 0, 60])
        gray_upper = np.array([180, 50, 130])
        gray_mask = cv2.inRange(hsv, gray_lower, gray_upper)
        
        contours, _ = cv2.findContours(gray_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        small_spots = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 20 < area < 200:  # Small spots
                perimeter = cv2.arcLength(cnt, True)
                if perimeter > 0:
                    circularity = 4 * np.pi * area / (perimeter ** 2)
                    if circularity > 0.7:
                        small_spots += 1
        
        return min(1.0, small_spots / 15.0)
    
    def _detect_white_powder(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect white powdery growth (powdery mildew)"""
        white_lower = np.array([0, 0, 200])
        white_upper = np.array([180, 50, 255])
        white_mask = cv2.inRange(hsv, white_lower, white_upper)
        
        coverage = np.sum(white_mask > 0) / white_mask.size
        return min(1.0, coverage * 20)
    
    def _detect_cavity_pits(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect sunken elliptical pits (cavity spot)"""
        # Dark sunken areas
        dark_lower = np.array([10, 50, 20])
        dark_upper = np.array([25, 200, 80])
        dark_mask = cv2.inRange(hsv, dark_lower, dark_upper)
        
        contours, _ = cv2.findContours(dark_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        elliptical_pits = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 50 < area < 500:
                if len(cnt) >= 5:
                    ellipse = cv2.fitEllipse(cnt)
                    # Check if elongated (cavity spots are elliptical)
                    width, height = ellipse[1]
                    if width > 0 and height > 0:
                        aspect = max(width, height) / min(width, height)
                        if 1.5 < aspect < 4.0:
                            elliptical_pits += 1
        
        return min(1.0, elliptical_pits / 8.0)
    
    def _create_result(self,
                      disease: CarrotDisease,
                      confidence: float,
                      severity: str,
                      days_from_seeding: int) -> CarrotDiseaseResult:
        """Create detection result with spray program"""
        params = self.diseases[disease]
        
        # Disease-specific recommendations
        if disease == CarrotDisease.ALTERNARIA_BLIGHT:
            immediate = [
                "Begin fungicide program IMMEDIATELY if not already",
                "Scout entire field for disease extent",
                "Check spray equipment calibration",
                "Plan 7-day spray intervals in wet weather"
            ]
            spray = [
                "Week 1: Chlorothalonil (FRAC M5) protectant",
                "Week 2: Azoxystrobin + Difenoconazole (FRAC 11+3)",
                "Week 3: Boscalid (FRAC 7)",
                "Week 4: Rotate back to FRAC M5",
                "Continue 7-14 day intervals until harvest"
            ]
            harvest = "Do not delay harvest - defoliation reduces yield rapidly"
        
        elif disease == CarrotDisease.CAVITY_SPOT:
            immediate = [
                "Improve field drainage immediately",
                "Reduce irrigation frequency",
                "Consider early harvest (minimize storage time)",
                "Direct to processing market (fresh market rejected)"
            ]
            spray = ["No effective spray treatment", "Focus on drainage"]
            harvest = "Early harvest recommended - severity worsens with time"
        
        else:
            immediate = params.cultural_control[:2]
            spray = params.fungicide_groups[:3] if params.fungicide_groups else ["No spray treatment"]
            harvest = "Normal harvest timing"
        
        return CarrotDiseaseResult(
            disease=disease,
            confidence=confidence,
            severity=severity,
            symptoms_detected=params.foliar_symptoms[:3] if params.foliar_symptoms else params.root_symptoms[:3],
            immediate_actions=immediate,
            spray_program=spray,
            harvest_recommendation=harvest
        )


# Example usage
if __name__ == "__main__":
    print("Carrot Disease Detection System")
    print("=" * 70)
    
    detector = CarrotDiseaseDetector()
    
    print("\n📚 CARROT DISEASE DATABASE:")
    print("\nFOLIAR DISEASES (Priority):")
    for disease, params in CARROT_DISEASES.items():
        if "EPIDEMIC" in params.severity or disease == CarrotDisease.ALTERNARIA_BLIGHT:
            print(f"\n{disease.value.upper()}")
            print(f"  Pathogen: {params.pathogen}")
            print(f"  Severity: {params.severity}")
            print(f"  Yield Loss: {params.yield_loss[0]}-{params.yield_loss[1]}%")
            print(f"  Diagnostic: {params.diagnostic_features}")
    
    print("\n" + "=" * 70)
    print("ALTERNARIA SPRAY PROGRAM (CRITICAL):")
    alt_params = CARROT_DISEASES[CarrotDisease.ALTERNARIA_BLIGHT]
    print("\nFungicide Rotation:")
    for i, fungicide in enumerate(alt_params.fungicide_groups[:4], 1):
        print(f"  {i}. {fungicide}")
    print("\nTiming: Begin at 45 days or first symptoms")
    print("Interval: 7-14 days depending on weather")
    print("Cost: $250/acre/season")
    
    print("\n✓ Carrot disease detection system initialized")
    print("  Alternaria: #1 disease, can destroy entire crop")
    print("  Fungicide rotation critical: Resistance common")
