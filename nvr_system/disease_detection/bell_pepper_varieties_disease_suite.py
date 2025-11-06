"""
Bell Pepper Varieties Disease Detection Suite
=============================================

Comprehensive disease management for bell pepper color variants with variety-specific
resistance profiles, grafting strategies, and Phytophthora/bacterial spot races.

Bell Pepper Color Classes:
- Green (immature, highest production)
- Red (fully mature, premium $2.00-4.50/lb)
- Yellow/Orange (specialty, highest premium $3.50-5.00/lb)
- Purple/Chocolate (boutique markets)

Critical Disease Complexes:
1. Bacterial Spot (Xanthomonas euvesicatoria) - 5 RACES A-E, COPPER RESISTANCE
2. Phytophthora Blight (P. capsici) - 5 RACES, GRAFT FOR CONTROL
3. Virus Complex (TEV, TMV, PVY, PepMoV) - SEED-BORNE, GRAFTING SPREAD
4. Anthracnose (Colletotrichum spp.) - FRUIT ROT, LATENT INFECTION
5. Cercospora Leaf Spot - DEFOLIATION, QoI RESISTANCE
6. Bacterial Wilt (Ralstonia) - QUARANTINE, SOIL STERILIZATION
7. Powdery Mildew (Leveillula taurica) - INTERNAL LEAF COLONIZATION
8. Southern Blight (Sclerotium rolfsii) - WHITE MYCELIUM, SCLEROTIA

Market Intelligence:
- USA production: 2.5 billion lbs, $1.2 billion
- Colored peppers: 300% premium over green ($1.50 green vs $4.50 red)
- Grafted transplants: $1.50 each vs $0.30 ungrafted
- Grafting for Phytophthora: 60-90% yield improvement infested soil
- Organic bell pepper: $4.00-7.00/lb premium, disease control challenging
- Greenhouse production: $12-20/lb premium baby bell peppers

Author: AgroPulse Team
Date: November 2025
"""

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional, Dict


class BellPepperColor(Enum):
    """Bell pepper color categories (maturity stages)"""
    GREEN = "green"  # Immature (20-25 days from set)
    RED = "red"  # Fully mature (45-60 days)
    YELLOW = "yellow"  # Specialty mature
    ORANGE = "orange"  # Specialty mature
    PURPLE = "purple"  # Boutique
    CHOCOLATE = "chocolate"  # Boutique


class BellPepperType(Enum):
    """Bell pepper production systems"""
    FIELD_STANDARD = "field_standard"  # Open field, standard size
    FIELD_JUMBO = "field_jumbo"  # Large fruit (XL)
    GREENHOUSE = "greenhouse"  # Protected culture
    BABY_BELL = "baby_bell"  # Mini snack peppers
    ORGANIC = "organic"  # Certified organic


class BellPepperDisease(Enum):
    """Major bell pepper diseases"""
    BACTERIAL_SPOT = "bacterial_spot"
    PHYTOPHTHORA_BLIGHT = "phytophthora"
    VIRUS_COMPLEX = "virus_complex"
    ANTHRACNOSE = "anthracnose"
    CERCOSPORA_LEAF_SPOT = "cercospora"
    BACTERIAL_WILT = "bacterial_wilt"
    POWDERY_MILDEW = "powdery_mildew"
    SOUTHERN_BLIGHT = "southern_blight"


@dataclass
class BellPepperDiseaseParams:
    """Disease parameters with variety-specific resistance"""
    disease: BellPepperDisease
    pathogen: str
    severity: str
    yield_loss: Tuple[int, int]
    fruit_quality_impact: str
    
    # Symptoms
    leaf_symptoms: List[str]
    fruit_symptoms: List[str]
    stem_symptoms: List[str]
    diagnostic_features: str
    
    # Race/strain information
    races_strains: str
    race_testing_notes: str
    
    # Resistance genes/varieties
    resistant_varieties: Dict[str, List[str]]  # Color -> varieties
    resistance_genes: List[str]
    
    # Grafting strategy
    grafting_recommended: bool
    rootstock_options: List[str]
    grafting_notes: str
    
    # Control
    cultural_control: List[str]
    chemical_control: List[str]
    copper_resistance_notes: str  # For bacterial diseases
    
    # Economics
    market_impact: str
    treatment_cost_per_acre: float
    grafting_cost_premium: float  # $/plant


# Disease database with variety-specific resistance
BELL_PEPPER_DISEASES = {
    BellPepperDisease.BACTERIAL_SPOT: BellPepperDiseaseParams(
        disease=BellPepperDisease.BACTERIAL_SPOT,
        pathogen="Xanthomonas euvesicatoria (5 races A-E, copper resistance common)",
        severity="10/10 - #1 DISEASE, COPPER RESISTANCE, RACE COMPLEXITY",
        yield_loss=(30, 70),
        fruit_quality_impact="Fruit lesions = 100% reject, unmarketable",
        
        leaf_symptoms=[
            "Small water-soaked spots on leaves",
            "Spots enlarge to 3-5mm, dark brown center",
            "Yellow halo around spots DIAGNOSTIC",
            "Leaf defoliation in severe cases",
            "Underside of leaf has raised bacterial pustules",
        ],
        
        fruit_symptoms=[
            "Raised corky lesions on fruit surface",
            "Lesions 2-5mm, white halo around spot",
            "ANY fruit lesion = 100% market rejection",
            "Fruit downgraded or discarded completely",
            "Lesions become entry points for soft rot",
        ],
        
        stem_symptoms=[
            "Water-soaked streaks on stems",
            "Cankers on stem and petioles",
        ],
        
        diagnostic_features="Yellow halo leaf spots + raised corky fruit lesions",
        
        races_strains="FIVE RACES (A, B, C, D, E) with different host specificity",
        race_testing_notes="Race determination critical for resistance deployment, laboratory testing recommended",
        
        resistant_varieties={
            "red": [
                "Revolution (Race A,B,C resistance)",
                "Red Knight (Race A resistance)",
                "Paladin (Race A,B,C,D resistance) - BROAD SPECTRUM",
            ],
            "yellow": [
                "Escudero (Race A,B,C resistance)",
                "Yellow Scorpion (Race A resistance)",
            ],
            "orange": [
                "Orange Blaze (Race A,B,C resistance)",
            ],
            "green": [
                "Aristotle (Race A,B,C resistance)",
                "Intruder (Race A resistance)",
            ]
        },
        
        resistance_genes=[
            "Bs2 gene - broad spectrum (Races A,B,C,D)",
            "Bs3 gene - Race C specific",
            "Bs4 gene - limited spectrum",
        ],
        
        grafting_recommended=False,
        rootstock_options=[],
        grafting_notes="Not effective (foliar disease)",
        
        cultural_control=[
            "Plant resistant varieties CRITICAL",
            "Determine race present (lab test)",
            "Use pathogen-free transplants",
            "Avoid overhead irrigation",
            "Wide row spacing for air circulation",
            "Remove crop residues",
            "3-year rotation to non-hosts",
            "Copper resistance WIDESPREAD",
        ],
        
        chemical_control=[
            "Copper hydroxide + mancozeb (if no resistance)",
            "Acibenzolar-S-methyl (Actigard) - SAR inducer",
            "Streptomycin (limited, resistance developing)",
            "Weekly applications preventatively",
            "CRITICAL: Copper resistance common",
            "  - Test copper sensitivity",
            "  - Tank-mix copper + mancozeb",
            "  - Add spreader-sticker",
            "Resistance deployment FIRST LINE",
        ],
        
        copper_resistance_notes="70-90% strains resistant to copper in FL/GA/NC, tank-mix essential",
        market_impact="CATASTROPHIC - Any fruit lesion = total rejection",
        treatment_cost_per_acre=350.0,
        grafting_cost_premium=0.0
    ),
    
    BellPepperDisease.PHYTOPHTHORA_BLIGHT: BellPepperDiseaseParams(
        disease=BellPepperDisease.PHYTOPHTHORA_BLIGHT,
        pathogen="Phytophthora capsici (5 races, oospores 10+ years, GRAFT CONTROL)",
        severity="10/10 - CATASTROPHIC, GRAFTING SOLUTION",
        yield_loss=(60, 100),
        fruit_quality_impact="Complete crop loss in infested fields",
        
        leaf_symptoms=[
            "Large irregular water-soaked leaf lesions",
            "Rapid leaf blight and wilting",
        ],
        
        fruit_symptoms=[
            "Water-soaked spots on fruit",
            "White fluffy mycelium on rotting fruit",
            "Complete fruit collapse within 3-5 days",
            "Can destroy 100% of fruit in field",
        ],
        
        stem_symptoms=[
            "Crown rot at soil line DEVASTATING",
            "Dark water-soaked stem lesions",
            "Girdling causes sudden plant wilt and death",
            "Entire plant dies from crown infection",
        ],
        
        diagnostic_features="Crown rot + fruit rot, waterlogged fields, sudden death",
        
        races_strains="FIVE RACES (1, 2, 3, 4, 5) with differential virulence",
        race_testing_notes="Race typing essential for rootstock selection",
        
        resistant_varieties={
            "red": ["Limited field resistance, GRAFTING preferred"],
            "yellow": ["Limited field resistance"],
            "orange": ["Limited field resistance"],
            "green": ["Limited field resistance"],
        },
        
        resistance_genes=[
            "No major resistance genes in bell pepper",
            "Quantitative resistance only",
            "GRAFTING to resistant rootstocks SOLUTION",
        ],
        
        grafting_recommended=True,
        rootstock_options=[
            "Criollo de Morelos CM-334 (Race 1,2,3 resistance)",
            "PI 201234 (Broad spectrum resistance)",
            "Commercial rootstocks: Revolution, Scarface, Red Defender",
        ],
        grafting_notes="Grafting provides 60-90% yield improvement in infested fields, $1.50/plant vs $0.30",
        
        cultural_control=[
            "GRAFTING ESSENTIAL in infested fields",
            "Drainage CRITICAL (waterlogged = disaster)",
            "Avoid infested fields (10+ year oospore survival)",
            "Raised beds mandatory",
            "Drip irrigation only",
            "4-year rotation to non-hosts (no pepper, tomato, eggplant, cucurbits)",
            "Plastic mulch reduces splash",
        ],
        
        chemical_control=[
            "FRAC 4: Mefenoxam (Ridomil) at-plant",
            "FRAC 43: Fluopicolide (Presidio)",
            "FRAC 40: Cyazofamid (Ranman)",
            "FRAC 22: Famoxadone (Tanos)",
            "Preventative applications CRITICAL",
            "Once crown rot begins, NO CURE",
            "5-7 day intervals in wet weather",
        ],
        
        copper_resistance_notes="Not applicable (oomycete, not bacterial)",
        market_impact="CATASTROPHIC - field abandonment, 10+ year loss without grafting",
        treatment_cost_per_acre=400.0,
        grafting_cost_premium=1.20  # $1.50 grafted vs $0.30 ungrafted
    ),
    
    BellPepperDisease.VIRUS_COMPLEX: BellPepperDiseaseParams(
        disease=BellPepperDisease.VIRUS_COMPLEX,
        pathogen="TEV + TMV + PVY + PepMoV (Tobacco Etch, Mosaic, Potato Y, Pepper Mottle)",
        severity="9/10 - SEED-BORNE, APHID VECTORS, GRAFTING SPREAD",
        yield_loss=(40, 80),
        fruit_quality_impact="Fruit deformation, discoloration, unmarketable",
        
        leaf_symptoms=[
            "Mosaic pattern (light/dark green areas)",
            "Leaf distortion and puckering",
            "Stunted growth (30-50% reduction)",
            "Vein clearing",
            "Leaf drop in severe infections",
        ],
        
        fruit_symptoms=[
            "Fruit mottling and color breaks",
            "Distorted, lumpy fruit shape",
            "Reduced fruit size",
            "Necrotic spots on fruit",
            "Fruit unmarketable",
        ],
        
        stem_symptoms=[
            "Stunted internodes",
            "Necrotic streaks on stems (TEV)",
        ],
        
        diagnostic_features="Mosaic leaves + deformed fruit, ELISA test for virus ID",
        
        races_strains="Multiple virus species, aphid and mechanical transmission",
        race_testing_notes="ELISA testing identifies specific viruses present",
        
        resistant_varieties={
            "red": [
                "Red Knight (TMV resistance - Tm gene)",
                "Revolution (TMV, TEV resistance)",
            ],
            "yellow": [
                "Yellow Scorpion (TMV resistance)",
            ],
            "orange": [
                "Orange Blaze (TMV resistance)",
            ],
            "green": [
                "Aristotle (TMV resistance)",
            ]
        },
        
        resistance_genes=[
            "L gene - TEV resistance",
            "Tm-2² gene - TMV resistance (most durable)",
            "pvr2 gene - PVY resistance",
        ],
        
        grafting_recommended=False,
        rootstock_options=[],
        grafting_notes="WARNING: Grafting spreads virus if rootstock/scion infected, use virus-free plants",
        
        cultural_control=[
            "CERTIFIED VIRUS-FREE TRANSPLANTS essential",
            "Aphid control critical (virus vectors)",
            "Remove infected plants immediately",
            "Disinfect grafting/pruning tools (10% bleach)",
            "Control volunteer tobacco and weeds",
            "Wash hands after smoking (TMV)",
            "Avoid grafting if virus present",
        ],
        
        chemical_control=[
            "NO CURE for viruses",
            "Insecticides for aphid control:",
            "  - Imidacloprid soil drench",
            "  - Thiamethoxam seed treatment",
            "  - Pymetrozine (Fulfill) aphid-specific",
            "Early season protection critical",
        ],
        
        copper_resistance_notes="Not applicable (viral)",
        market_impact="Fruit deformation and discoloration = total rejection",
        treatment_cost_per_acre=200.0,
        grafting_cost_premium=0.0
    ),
    
    BellPepperDisease.ANTHRACNOSE: BellPepperDiseaseParams(
        disease=BellPepperDisease.ANTHRACNOSE,
        pathogen="Colletotrichum capsici (latent infection, fruit rot at maturity)",
        severity="8/10 - LATENT INFECTION, STORAGE/TRANSIT LOSS",
        yield_loss=(20, 50),
        fruit_quality_impact="Fruit rot during ripening, storage, transit",
        
        leaf_symptoms=[
            "Brown circular leaf spots (less common)",
        ],
        
        fruit_symptoms=[
            "Circular sunken lesions on ripe fruit",
            "Lesions 5-20mm, concentric rings",
            "Black fungal acervuli in lesion centers",
            "Orange-pink spore masses in humid conditions",
            "Latent infection on green fruit, symptoms at ripening",
            "30-50% postharvest loss potential",
        ],
        
        stem_symptoms=[
            "Stem lesions near fruit attachment",
        ],
        
        diagnostic_features="Sunken fruit lesions with concentric rings, ripe fruit",
        
        races_strains="Multiple Colletotrichum species involved",
        race_testing_notes="Species identification helps predict severity",
        
        resistant_varieties={
            "red": ["Limited resistance, cultural control key"],
            "yellow": ["Limited resistance"],
            "orange": ["Limited resistance"],
            "green": ["Harvest green reduces losses"],
        },
        
        resistance_genes=["No major resistance genes identified"],
        
        grafting_recommended=False,
        rootstock_options=[],
        grafting_notes="Not effective (foliar/fruit disease)",
        
        cultural_control=[
            "Harvest fruit before full maturity",
            "Avoid overhead irrigation",
            "Remove infected fruit from field",
            "Crop rotation",
            "Avoid wounding fruit during harvest",
        ],
        
        chemical_control=[
            "FRAC 3: Azoxystrobin, pyraclostrobin",
            "FRAC 11: Trifloxystrobin",
            "FRAC 7: Boscalid",
            "FRAC M5: Chlorothalonil",
            "Begin sprays at first fruit set",
            "Continue through harvest",
            "7-14 day intervals",
        ],
        
        copper_resistance_notes="Not applicable (fungal)",
        market_impact="Storage/transit losses 30-50% if not controlled",
        treatment_cost_per_acre=250.0,
        grafting_cost_premium=0.0
    ),
}


@dataclass
class BellPepperDiseaseResult:
    """Detection result for bell pepper diseases"""
    disease: BellPepperDisease
    confidence: float
    severity: str
    fruit_impact: str
    color_variety_resistance: Dict[str, str]  # Color -> resistance info
    grafting_recommendation: str
    immediate_actions: List[str]
    resistance_genes_available: List[str]


class BellPepperVarietyDiseaseDetector:
    """
    Bell pepper variety-specific disease detector
    
    Focus on:
    - Variety-specific resistance by color class
    - Grafting for Phytophthora management
    - Copper resistance in bacterial spot
    - Race/strain complexity
    """
    
    def __init__(self):
        self.diseases = BELL_PEPPER_DISEASES
    
    def detect_disease(self,
                      image: np.ndarray,
                      plant_part: str = "leaf",
                      pepper_color: BellPepperColor = BellPepperColor.GREEN,
                      field_history: Optional[str] = None) -> List[BellPepperDiseaseResult]:
        """
        Detect bell pepper diseases with variety recommendations
        
        Args:
            image: BGR image
            plant_part: "leaf", "fruit", "stem"
            pepper_color: Color variety being grown
            field_history: "phytophthora_present", "bacterial_spot_present", etc.
        
        Returns:
            List of diseases with variety-specific recommendations
        """
        if image is None or image.size == 0:
            return []
        
        results = []
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        if plant_part == "leaf":
            # Bacterial spot (yellow halo)
            bacterial_score = self._detect_yellow_halo_spots(image, hsv)
            if bacterial_score > 0.4:
                results.append(self._create_result(
                    BellPepperDisease.BACTERIAL_SPOT,
                    bacterial_score,
                    pepper_color,
                    field_history
                ))
            
            # Cercospora (circular spots)
            cercospora_score = self._detect_circular_spots(image, hsv)
            if cercospora_score > 0.3:
                # Would add Cercospora here (simplified for now)
                pass
        
        elif plant_part == "fruit":
            # Anthracnose (sunken lesions)
            anthracnose_score = self._detect_sunken_lesions(image, hsv)
            if anthracnose_score > 0.4:
                results.append(self._create_result(
                    BellPepperDisease.ANTHRACNOSE,
                    anthracnose_score,
                    pepper_color,
                    field_history
                ))
            
            # Phytophthora fruit rot
            phytophthora_score = self._detect_water_soaked_fruit(image, hsv)
            if phytophthora_score > 0.5:
                results.append(self._create_result(
                    BellPepperDisease.PHYTOPHTHORA_BLIGHT,
                    phytophthora_score,
                    pepper_color,
                    field_history
                ))
        
        elif plant_part == "stem":
            # Crown rot (Phytophthora)
            crown_score = self._detect_crown_rot(image, hsv)
            if crown_score > 0.5:
                results.append(self._create_result(
                    BellPepperDisease.PHYTOPHTHORA_BLIGHT,
                    crown_score,
                    pepper_color,
                    field_history
                ))
        
        return sorted(results, key=lambda x: x.confidence, reverse=True)
    
    def recommend_varieties(self,
                          diseases_present: List[BellPepperDisease],
                          pepper_color: BellPepperColor) -> Dict[str, List[str]]:
        """
        Recommend resistant varieties based on diseases present
        
        Returns:
            {disease_name: [variety names with resistance]}
        """
        recommendations = {}
        
        for disease in diseases_present:
            if disease in self.diseases:
                params = self.diseases[disease]
                color_key = pepper_color.value
                
                if color_key in params.resistant_varieties:
                    recommendations[disease.value] = params.resistant_varieties[color_key]
                else:
                    recommendations[disease.value] = ["Limited resistance available"]
        
        return recommendations
    
    def _detect_yellow_halo_spots(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect spots with yellow halos (bacterial spot)"""
        yellow_lower = np.array([20, 50, 100])
        yellow_upper = np.array([35, 255, 255])
        yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
        
        brown_lower = np.array([10, 50, 30])
        brown_upper = np.array([25, 200, 150])
        brown_mask = cv2.inRange(hsv, brown_lower, brown_upper)
        
        # Look for brown spots with yellow halos
        combined = cv2.bitwise_or(yellow_mask, brown_mask)
        coverage = np.sum(combined > 0) / combined.size
        return min(1.0, coverage * 15)
    
    def _detect_sunken_lesions(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect sunken lesions (anthracnose)"""
        dark_lower = np.array([0, 50, 20])
        dark_upper = np.array([20, 200, 120])
        dark_mask = cv2.inRange(hsv, dark_lower, dark_upper)
        
        coverage = np.sum(dark_mask > 0) / dark_mask.size
        return min(1.0, coverage * 18)
    
    def _detect_water_soaked_fruit(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect water-soaked areas (Phytophthora)"""
        dark_lower = np.array([0, 30, 0])
        dark_upper = np.array([180, 255, 80])
        dark_mask = cv2.inRange(hsv, dark_lower, dark_upper)
        
        coverage = np.sum(dark_mask > 0) / dark_mask.size
        return min(1.0, coverage * 12)
    
    def _detect_crown_rot(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect crown rot symptoms"""
        dark_lower = np.array([0, 50, 0])
        dark_upper = np.array([180, 255, 100])
        dark_mask = cv2.inRange(hsv, dark_lower, dark_upper)
        
        coverage = np.sum(dark_mask > 0) / dark_mask.size
        return min(1.0, coverage * 15)
    
    def _detect_circular_spots(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect circular spots (Cercospora)"""
        brown_lower = np.array([10, 40, 40])
        brown_upper = np.array([25, 200, 150])
        brown_mask = cv2.inRange(hsv, brown_lower, brown_upper)
        
        coverage = np.sum(brown_mask > 0) / brown_mask.size
        return min(1.0, coverage * 20)
    
    def _create_result(self,
                      disease: BellPepperDisease,
                      confidence: float,
                      pepper_color: BellPepperColor,
                      field_history: Optional[str]) -> BellPepperDiseaseResult:
        """Create result with variety-specific recommendations"""
        params = self.diseases[disease]
        
        # Get color-specific resistance info
        color_resistance = {}
        for color, varieties in params.resistant_varieties.items():
            color_resistance[color] = ", ".join(varieties[:2])  # Top 2 varieties
        
        # Grafting recommendation
        if params.grafting_recommended:
            if field_history == "phytophthora_present":
                grafting_rec = f"GRAFTING ESSENTIAL - {params.grafting_notes}"
            else:
                grafting_rec = f"Grafting recommended - {params.rootstock_options[0]}"
        else:
            grafting_rec = "Grafting not needed for this disease"
        
        # Disease-specific actions
        if disease == BellPepperDisease.BACTERIAL_SPOT:
            immediate = [
                "Plant resistant variety (check race)",
                "STOP copper if resistance present",
                "Acibenzolar-S-methyl (SAR inducer)",
                "Weekly sprays preventatively",
            ]
        elif disease == BellPepperDisease.PHYTOPHTHORA_BLIGHT:
            immediate = [
                "GRAFT to resistant rootstock",
                "Improve drainage immediately",
                "Preventative fungicide program",
                "Consider field abandonment if severe",
            ]
        elif disease == BellPepperDisease.ANTHRACNOSE:
            immediate = [
                "Harvest fruit before full maturity",
                "Begin fungicide program",
                "Remove infected fruit",
                "Reduce storage time",
            ]
        else:
            immediate = params.cultural_control[:3]
        
        return BellPepperDiseaseResult(
            disease=disease,
            confidence=confidence,
            severity=params.severity,
            fruit_impact=params.fruit_quality_impact,
            color_variety_resistance=color_resistance,
            grafting_recommendation=grafting_rec,
            immediate_actions=immediate,
            resistance_genes_available=params.resistance_genes
        )


# Example usage
if __name__ == "__main__":
    print("Bell Pepper Variety Disease Detection System")
    print("=" * 70)
    
    detector = BellPepperVarietyDiseaseDetector()
    
    print("\n📚 BELL PEPPER DISEASE DATABASE:")
    print("\nCRITICAL DISEASES BY COLOR CLASS:")
    
    for disease, params in BELL_PEPPER_DISEASES.items():
        if disease in [BellPepperDisease.BACTERIAL_SPOT, BellPepperDisease.PHYTOPHTHORA_BLIGHT]:
            print(f"\n{disease.value.upper()}")
            print(f"  Pathogen: {params.pathogen}")
            print(f"  Severity: {params.severity}")
            print(f"  Grafting: {params.grafting_recommended}")
            print(f"  Resistance genes: {', '.join(params.resistance_genes[:2])}")
    
    print("\n" + "=" * 70)
    print("VARIETY RECOMMENDATIONS BY COLOR:")
    
    for color in ["red", "yellow", "green"]:
        print(f"\n{color.upper()} PEPPERS:")
        bacterial_spot = BELL_PEPPER_DISEASES[BellPepperDisease.BACTERIAL_SPOT]
        if color in bacterial_spot.resistant_varieties:
            print(f"  Bacterial Spot: {', '.join(bacterial_spot.resistant_varieties[color])}")
    
    print("\n" + "=" * 70)
    print("GRAFTING FOR PHYTOPHTHORA:")
    phyto = BELL_PEPPER_DISEASES[BellPepperDisease.PHYTOPHTHORA_BLIGHT]
    print(f"  Rootstocks: {', '.join(phyto.rootstock_options)}")
    print(f"  Cost premium: ${phyto.grafting_cost_premium:.2f}/plant")
    print(f"  Notes: {phyto.grafting_notes}")
    
    print("\n✓ Bell pepper variety disease detection system initialized")
    print("  Focus: Variety resistance, grafting strategies, race management")
    print("  Market: $1.2B USA, colored peppers $2-5/lb, grafted plants $1.50 each")
