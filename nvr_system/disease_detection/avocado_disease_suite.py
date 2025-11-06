"""
Avocado Disease Detection Suite
================================

Comprehensive disease identification for avocado (Persea americana), premium
tropical/subtropical fruit with CATASTROPHIC Phytophthora root rot pandemic.

Avocado Varieties:
- Hass (black skin, 95% California commercial production)
- Fuerte (green skin, cold-hardy)
- Pinkerton (green skin, small seed)
- Reed (round, summer harvest)
- Bacon (cold-tolerant)
- Zutano (cold-tolerant)

Critical Diseases:
1. Phytophthora Root Rot (P. cinnamomi) - #1 WORLDWIDE KILLER, PANDEMIC
2. Anthracnose (Colletotrichum gloeosporioides) - #1 POSTHARVEST, FRUIT ROT
3. Cercospora Spot (Pseudocercospora purpurea) - PURPLE SPOTS, DEFOLIATION
4. Avocado Black Streak (Fusarium spp.) - VASCULAR WILT
5. Dothiorella Canker (Dothiorella gregaria) - STEM CANKERS, DIEBACK
6. Bacterial Canker (Xanthomonas campestris) - CANKERS, LEAF SPOTS
7. Avocado Sunblotch Viroid - QUARANTINE, PERMANENT INFECTION
8. Root Rot Complex (Multiple Phytophthora species)

Rootstock Resistance:
- Duke 7 - MOST resistant to Phytophthora cinnamomi
- Dusa - Resistant, salt-tolerant
- Thomas - Moderately resistant
- Toro Canyon - Resistant
- Mexicola - Cold-hardy, moderately resistant
- CRITICAL: Rootstock selection determines Phytophthora survival

Market Intelligence:
- Global production: $13 billion (Mexico 30%, Dominican Republic 10%, Peru 8%, USA 6%)
- USA production: $411 million (California 90%, Florida 10%)
- Hass premium: $1.50-3.00/avocado retail, $25-45/box wholesale (25 lbs)
- Organic premium: $2.50-4.00/avocado retail
- Phytophthora: ESTIMATED 40-60% global yield loss
- California losses: $40-70 million annually to Phytophthora
- Tree replacement: $150-300/tree (grafted, 3-4 years)

Author: AgroPulse Team
Date: November 2025
"""

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Dict


class AvocadoVariety(Enum):
    """Major avocado commercial varieties"""
    HASS = "hass"  # 95% California, black skin
    FUERTE = "fuerte"  # Green skin, cold-hardy
    PINKERTON = "pinkerton"  # Green, small seed
    REED = "reed"  # Round, summer
    BACON = "bacon"  # Cold-tolerant
    ZUTANO = "zutano"  # Cold-tolerant


class AvocadoRootstock(Enum):
    """Rootstocks with Phytophthora resistance levels"""
    DUKE_7 = "duke_7"  # MOST resistant
    DUSA = "dusa"  # Resistant, salt-tolerant
    THOMAS = "thomas"  # Moderately resistant
    TORO_CANYON = "toro_canyon"  # Resistant
    MEXICOLA = "mexicola"  # Cold-hardy, moderate
    SEEDLING = "seedling"  # SUSCEPTIBLE, avoid


class AvocadoDisease(Enum):
    """Major avocado diseases"""
    PHYTOPHTHORA_ROOT_ROT = "phytophthora"
    ANTHRACNOSE = "anthracnose"
    CERCOSPORA_SPOT = "cercospora"
    BLACK_STREAK = "black_streak"
    DOTHIORELLA_CANKER = "dothiorella"
    BACTERIAL_CANKER = "bacterial_canker"
    SUNBLOTCH_VIROID = "sunblotch"
    ROOT_ROT_COMPLEX = "root_rot_complex"


@dataclass
class AvocadoDiseaseParams:
    """Comprehensive disease parameters for avocado"""
    disease: AvocadoDisease
    pathogen: str
    severity: str
    yield_loss: Tuple[int, int]
    tree_mortality: int  # Percentage of infected trees that die
    
    symptoms: List[str]
    diagnostic_features: str
    
    # Avocado-specific parameters
    rootstock_resistance: Dict[str, str]  # Rootstock: resistance level
    fruit_symptoms: List[str]
    tree_symptoms: List[str]
    
    # Control strategies
    rootstock_selection: str
    cultural_control: List[str]
    chemical_control: List[str]
    organic_control: List[str]
    
    economic_impact: str
    treatment_cost_per_acre: float


# Comprehensive disease database
AVOCADO_DISEASES = {
    AvocadoDisease.PHYTOPHTHORA_ROOT_ROT: AvocadoDiseaseParams(
        disease=AvocadoDisease.PHYTOPHTHORA_ROOT_ROT,
        pathogen="Phytophthora cinnamomi (#1 WORLDWIDE AVOCADO KILLER, PANDEMIC)",
        severity="10/10 - CATASTROPHIC WORLDWIDE PANDEMIC, #1 DISEASE",
        yield_loss=(40, 100),
        tree_mortality=90,  # 90% of infected trees die without treatment
        
        symptoms=[
            "Wilting despite adequate soil moisture DIAGNOSTIC",
            "Yellowing leaves (chlorosis)",
            "Sparse, small leaves",
            "Twig dieback from canopy edges",
            "Premature fruit drop",
            "Reduced fruit size",
            "Tree decline over months to years",
            "Complete tree death (90% mortality)",
        ],
        
        diagnostic_features="Wilting + black mushy roots + poor drainage history",
        
        rootstock_resistance={
            "Duke 7": "HIGHLY RESISTANT (best choice)",
            "Dusa": "RESISTANT + salt-tolerant",
            "Thomas": "MODERATELY RESISTANT",
            "Toro Canyon": "RESISTANT",
            "Mexicola": "MODERATE resistance + cold-hardy",
            "Seedling rootstock": "HIGHLY SUSCEPTIBLE - AVOID"
        },
        
        fruit_symptoms=[
            "Small fruit size",
            "Premature fruit drop",
            "Poor fruit quality",
            "Reduced oil content",
        ],
        
        tree_symptoms=[
            "BLACK MUSHY ROOTS (diagnostic)",
            "No white feeder roots",
            "Crown rot at soil line",
            "Canopy thinning",
            "Branch dieback",
            "Complete tree death",
        ],
        
        rootstock_selection="🚨 CRITICAL: Duke 7 or Dusa rootstock ESSENTIAL in Phytophthora areas",
        
        cultural_control=[
            "🚨 ROOTSTOCK: Duke 7 or Dusa in Phytophthora zones (most critical)",
            "EXCELLENT DRAINAGE essential (raised beds 12-18 inches minimum)",
            "Avoid overwatering (common killer)",
            "Mulch application (organic mulch suppresses Phytophthora)",
            "Avoid planting in infested soil",
            "Remove infected trees + soil (5-foot radius minimum)",
            "Plant on slopes (gravity drainage)",
            "Drip irrigation only (NO flooding, NO overhead)",
            "Soil solarization pre-plant (6-8 weeks summer)",
        ],
        
        chemical_control=[
            "FRAC 4: Mefenoxam (Ridomil Gold) - trunk injection or drench",
            "FRAC 43: Fluopicolide - drench",
            "FRAC 22: Potassium phosphite (Agri-Fos) - trunk injection or foliar",
            "Trunk injection: 2-4x per year (most effective delivery)",
            "Soil drench: Monthly during wet season",
            "Rotate FRAC codes annually",
            "Start treatments BEFORE symptoms (preventative essential)",
        ],
        
        organic_control=[
            "Potassium phosphite (Agri-Fos) - OMRI listed, trunk injection",
            "Gypsum soil amendment (improves drainage + calcium)",
            "Organic mulch (bark, wood chips - Phytophthora suppression)",
            "Compost tea drenches (beneficial microbes)",
            "Trichoderma harzianum biological fungicide",
            "DRAINAGE + RESISTANT ROOTSTOCK most critical",
        ],
        
        economic_impact="CATASTROPHIC - $40-70M annual California losses, 40-60% global yield loss, tree replacement $150-300",
        treatment_cost_per_acre=800.0  # Fungicide trunk injections expensive
    ),
    
    AvocadoDisease.ANTHRACNOSE: AvocadoDiseaseParams(
        disease=AvocadoDisease.ANTHRACNOSE,
        pathogen="Colletotrichum gloeosporioides (#1 POSTHARVEST DISEASE)",
        severity="9/10 - #1 POSTHARVEST FRUIT ROT, 20-50% LOSSES",
        yield_loss=(20, 50),
        tree_mortality=0,  # Doesn't kill trees
        
        symptoms=[
            "Black, circular fruit spots DIAGNOSTIC",
            "Sunken lesions on ripe fruit",
            "Pink spore masses in humid conditions",
            "Rapid fruit rot after harvest",
            "Latent infection during fruit development",
            "Symptoms appear at ripening",
        ],
        
        diagnostic_features="Black circular spots on ripe fruit, pink spores",
        
        rootstock_resistance={
            "Not rootstock-dependent": "Fruit disease, varietal tolerance varies"
        },
        
        fruit_symptoms=[
            "BLACK CIRCULAR SPOTS (diagnostic)",
            "Sunken lesions",
            "Pink-orange spore masses",
            "Rapid rot at ripening",
            "Complete fruit unmarketable",
            "Spreads fruit-to-fruit in storage",
        ],
        
        tree_symptoms=[
            "Leaf spots (minor)",
            "Twig dieback (minor)",
            "NO tree death",
        ],
        
        rootstock_selection="Not applicable (fruit disease)",
        
        cultural_control=[
            "Harvest at proper maturity (immature = more susceptible)",
            "Handle fruit carefully (wounds = infection)",
            "Hot water treatment: 122°F for 20 minutes post-harvest",
            "Rapid cooling after harvest (delays ripening = delays symptoms)",
            "Clean storage facilities",
            "Remove infected fruit promptly",
        ],
        
        chemical_control=[
            "Pre-harvest sprays critical:",
            "FRAC 3: Prochloraz (Guardian) - 2-4 weeks before harvest",
            "FRAC 11: Azoxystrobin - monthly during fruit development",
            "FRAC 7: Boscalid - pre-harvest",
            "Copper fungicides: Weekly during wet weather",
            "Post-harvest: Prochloraz dip or hot water",
        ],
        
        organic_control=[
            "Hot water treatment: 122°F for 20 minutes (most effective)",
            "Copper fungicides (organic-approved)",
            "Potassium bicarbonate sprays",
            "Essential oils (thyme, cinnamon)",
            "Harvest at optimal maturity",
            "Rapid cooling",
        ],
        
        economic_impact="SEVERE - 20-50% postharvest losses, $50-100M global annually",
        treatment_cost_per_acre=400.0
    ),
    
    AvocadoDisease.CERCOSPORA_SPOT: AvocadoDiseaseParams(
        disease=AvocadoDisease.CERCOSPORA_SPOT,
        pathogen="Pseudocercospora purpurea (purple spot, defoliation)",
        severity="7/10 - DEFOLIATION, FRUIT SPOTTING",
        yield_loss=(15, 35),
        tree_mortality=0,
        
        symptoms=[
            "PURPLE-BROWN SPOTS on leaves DIAGNOSTIC",
            "Angular leaf spots with yellow halos",
            "Premature leaf drop (defoliation)",
            "Purple-black spots on fruit skin",
            "Fruit cosmetically damaged (downgraded)",
        ],
        
        diagnostic_features="Purple-brown leaf spots, yellow halos, defoliation",
        
        rootstock_resistance={"Not applicable": "Foliar disease"},
        
        fruit_symptoms=[
            "Purple-black spots on skin",
            "Cosmetic damage (market rejection)",
            "NO internal fruit damage",
            "Fruit downgraded to processing",
        ],
        
        tree_symptoms=[
            "PURPLE-BROWN LEAF SPOTS (diagnostic)",
            "Yellow halos around spots",
            "Premature leaf drop",
            "Defoliation 30-60%",
            "Weakened trees",
        ],
        
        rootstock_selection="Not applicable",
        
        cultural_control=[
            "Remove infected leaves",
            "Improve air circulation (pruning)",
            "Avoid overhead irrigation",
            "Copper sprays during wet weather",
        ],
        
        chemical_control=[
            "FRAC M1: Copper hydroxide - preventative, weekly wet weather",
            "FRAC 11: Azoxystrobin - monthly",
            "FRAC 3: Tebuconazole - 14-day intervals",
            "Begin sprays at leaf flush",
        ],
        
        organic_control=[
            "Copper fungicides (organic-approved)",
            "Weekly during wet weather",
            "Sulfur sprays",
            "Remove infected leaves",
        ],
        
        economic_impact="Fruit cosmetic damage, downgrading to processing $0.50-1.00/lb vs $2-3/lb fresh",
        treatment_cost_per_acre=350.0
    ),
    
    AvocadoDisease.BLACK_STREAK: AvocadoDiseaseParams(
        disease=AvocadoDisease.BLACK_STREAK,
        pathogen="Fusarium spp. (vascular wilt)",
        severity="8/10 - VASCULAR WILT, TREE DEATH",
        yield_loss=(30, 80),
        tree_mortality=60,
        
        symptoms=[
            "BLACK STREAKS in vascular tissue DIAGNOSTIC",
            "Wilting branches (usually one-sided)",
            "Yellowing leaves",
            "Branch dieback",
            "Tree decline over months",
            "Tree death (60% mortality)",
        ],
        
        diagnostic_features="Black streaks in wood, one-sided wilting",
        
        rootstock_resistance={
            "Variable": "Some Fusarium resistance in West Indian types"
        },
        
        fruit_symptoms=[
            "Premature drop",
            "Small fruit",
        ],
        
        tree_symptoms=[
            "BLACK STREAKS in wood (cut branch to see)",
            "One-sided wilting (diagnostic)",
            "Branch dieback",
            "Vascular discoloration",
            "Tree death",
        ],
        
        rootstock_selection="West Indian rootstocks may have some resistance",
        
        cultural_control=[
            "Remove infected trees immediately",
            "Disinfect pruning tools (10% bleach)",
            "Avoid wounding trees",
            "Plant resistant varieties/rootstocks",
            "Soil fumigation before replanting",
        ],
        
        chemical_control=[
            "NO EFFECTIVE FUNGICIDES (systemic vascular infection)",
            "Prevention through sanitation only",
        ],
        
        organic_control=[
            "Remove infected trees",
            "Sanitation",
            "No organic treatment available",
        ],
        
        economic_impact="Tree death, replacement $150-300/tree + 3-4 years lost production",
        treatment_cost_per_acre=0.0  # No effective treatment
    ),
    
    AvocadoDisease.DOTHIORELLA_CANKER: AvocadoDiseaseParams(
        disease=AvocadoDisease.DOTHIORELLA_CANKER,
        pathogen="Dothiorella gregaria (stem cankers, branch dieback)",
        severity="7/10 - STEM CANKERS, FRUIT ROT",
        yield_loss=(10, 30),
        tree_mortality=5,
        
        symptoms=[
            "Dark brown stem cankers",
            "Cracked bark",
            "Branch dieback",
            "White latex oozing from cankers",
            "Fruit stem-end rot",
        ],
        
        diagnostic_features="Stem cankers with latex ooze, cracked bark",
        
        rootstock_resistance={"Variable": "Some tolerance in vigorous rootstocks"},
        
        fruit_symptoms=[
            "STEM-END ROT after harvest",
            "Spreads from stem into fruit",
            "Black rot at stem end",
            "Postharvest losses 10-20%",
        ],
        
        tree_symptoms=[
            "DARK CANKERS on branches",
            "White latex oozing",
            "Cracked, peeling bark",
            "Branch dieback",
        ],
        
        rootstock_selection="Vigorous rootstocks tolerate better",
        
        cultural_control=[
            "Prune out infected branches (4-6 inches below canker)",
            "Disinfect tools (10% bleach)",
            "Avoid wounding trees (sunburn protection)",
            "Paint exposed branches (white latex paint - sunburn prevention)",
            "Proper irrigation (water stress increases susceptibility)",
        ],
        
        chemical_control=[
            "FRAC M1: Copper fungicides - spray after pruning",
            "FRAC 3: Tebuconazole - spray wounds",
        ],
        
        organic_control=[
            "Prune infected branches",
            "Copper sprays after pruning",
            "Prevent sunburn (paint trunks white)",
        ],
        
        economic_impact="Postharvest fruit losses 10-20%, branch dieback reduces yield",
        treatment_cost_per_acre=200.0
    ),
    
    AvocadoDisease.BACTERIAL_CANKER: AvocadoDiseaseParams(
        disease=AvocadoDisease.BACTERIAL_CANKER,
        pathogen="Xanthomonas campestris (bacterial cankers, leaf spots)",
        severity="6/10 - CANKERS, LEAF SPOTS",
        yield_loss=(10, 25),
        tree_mortality=2,
        
        symptoms=[
            "Dark brown to black cankers on branches",
            "Raised, corky lesions",
            "Leaf spots with yellow halos",
            "Twig dieback",
            "Bacterial ooze from cankers",
        ],
        
        diagnostic_features="Raised corky cankers, bacterial ooze, leaf spots with halos",
        
        rootstock_resistance={"Unknown": "Limited resistance data"},
        
        fruit_symptoms=[
            "Fruit spots (cosmetic)",
            "Minor impact",
        ],
        
        tree_symptoms=[
            "RAISED CORKY CANKERS (diagnostic)",
            "Bacterial ooze",
            "Leaf spots with yellow halos",
            "Twig dieback",
        ],
        
        rootstock_selection="Not well studied",
        
        cultural_control=[
            "Prune infected branches",
            "Disinfect tools (70% alcohol or 10% bleach)",
            "Copper sprays preventative",
            "Avoid overhead irrigation",
            "Wind protection (wind spreads bacteria)",
        ],
        
        chemical_control=[
            "FRAC M1: Copper hydroxide - weekly during wet weather",
            "Streptomycin (where registered) - limited effectiveness",
            "NO HIGHLY EFFECTIVE BACTERICIDES",
        ],
        
        organic_control=[
            "Copper sprays (organic-approved)",
            "Prune infected branches",
            "Sanitation",
        ],
        
        economic_impact="Moderate - canker management + leaf spotting",
        treatment_cost_per_acre=250.0
    ),
    
    AvocadoDisease.SUNBLOTCH_VIROID: AvocadoDiseaseParams(
        disease=AvocadoDisease.SUNBLOTCH_VIROID,
        pathogen="Avocado sunblotch viroid (ASBVd) - QUARANTINE, NO CURE",
        severity="8/10 - PERMANENT INFECTION, QUARANTINE",
        yield_loss=(20, 60),
        tree_mortality=0,  # Doesn't kill but reduces productivity
        
        symptoms=[
            "Yellow or white streaks on fruit skin DIAGNOSTIC",
            "Yellow mottling on leaves",
            "Stem streaking",
            "Reduced fruit quality",
            "Reduced yield (30-50%)",
            "PERMANENT INFECTION (no cure)",
        ],
        
        diagnostic_features="Yellow/white fruit streaks, leaf mottling, NO CURE",
        
        rootstock_resistance={"None": "No resistance, viroid infects all avocado"},
        
        fruit_symptoms=[
            "YELLOW OR WHITE STREAKS on skin (diagnostic)",
            "Misshapen fruit",
            "Poor fruit quality",
            "Unmarketable",
        ],
        
        tree_symptoms=[
            "Yellow mottling on leaves",
            "Stem streaking (red-yellow)",
            "Reduced tree vigor",
            "Reduced yield 30-50%",
            "PERMANENT INFECTION",
        ],
        
        rootstock_selection="Use CERTIFIED VIRUS-FREE nursery stock only",
        
        cultural_control=[
            "🚨 REMOVE INFECTED TREES IMMEDIATELY (no cure)",
            "🚨 CERTIFIED VIRUS-FREE NURSERY STOCK ONLY",
            "Disinfect tools (viroids spread mechanically)",
            "10% bleach or heat sterilization (250°F for 1 minute)",
            "Quarantine infected orchards",
            "NO propagation from infected trees",
        ],
        
        chemical_control=[
            "NO CHEMICAL TREATMENT (viroid, not virus or bacteria)",
            "Prevention through certified stock only",
        ],
        
        organic_control=[
            "Remove infected trees",
            "Certified virus-free stock",
            "No treatment available",
        ],
        
        economic_impact="SEVERE - tree removal, replanting, 30-50% yield loss in infected trees",
        treatment_cost_per_acre=0.0  # No treatment, must remove trees
    ),
    
    AvocadoDisease.ROOT_ROT_COMPLEX: AvocadoDiseaseParams(
        disease=AvocadoDisease.ROOT_ROT_COMPLEX,
        pathogen="Multiple Phytophthora species (P. cinnamomi + P. citricola + P. palmivora)",
        severity="9/10 - MULTIPLE PHYTOPHTHORA SPECIES",
        yield_loss=(40, 90),
        tree_mortality=80,
        
        symptoms=[
            "Similar to P. cinnamomi root rot",
            "Multiple Phytophthora species present",
            "More aggressive than single species",
            "Rapid tree decline",
        ],
        
        diagnostic_features="Black mushy roots + multiple Phytophthora species identified",
        
        rootstock_resistance={
            "Duke 7": "Best broad Phytophthora resistance",
            "Dusa": "Broad resistance",
        },
        
        fruit_symptoms=["Premature drop", "Small fruit"],
        tree_symptoms=["Black mushy roots", "No feeder roots", "Rapid decline"],
        
        rootstock_selection="Duke 7 or Dusa - BROAD Phytophthora resistance",
        
        cultural_control=[
            "Same as Phytophthora cinnamomi",
            "Duke 7/Dusa rootstock even MORE critical",
            "Excellent drainage essential",
        ],
        
        chemical_control=[
            "Rotate multiple FRAC codes:",
            "FRAC 4: Mefenoxam",
            "FRAC 43: Fluopicolide",
            "FRAC 22: Potassium phosphite",
            "Tank mix for broad spectrum",
        ],
        
        organic_control=[
            "Potassium phosphite",
            "Drainage",
            "Resistant rootstock CRITICAL",
        ],
        
        economic_impact="CATASTROPHIC - worse than single species Phytophthora",
        treatment_cost_per_acre=1000.0  # Multiple fungicides
    ),
}


class AvocadoDiseaseDetector:
    """
    Avocado disease detection system - Phytophthora pandemic emphasis
    """
    
    def __init__(self):
        self.diseases = AVOCADO_DISEASES
        
        # Rootstock resistance rankings
        self.rootstock_phytophthora_resistance = {
            AvocadoRootstock.DUKE_7: 9,  # 1-10 scale
            AvocadoRootstock.DUSA: 8,
            AvocadoRootstock.TORO_CANYON: 7,
            AvocadoRootstock.THOMAS: 6,
            AvocadoRootstock.MEXICOLA: 5,
            AvocadoRootstock.SEEDLING: 2,
        }
    
    def detect_disease(self,
                      image: np.ndarray,
                      plant_part: str = "leaf",
                      rootstock: AvocadoRootstock = AvocadoRootstock.SEEDLING,
                      drainage_quality: str = "poor") -> List[Dict]:
        """
        Detect avocado diseases from image
        
        Args:
            image: Input image (BGR)
            plant_part: 'leaf', 'fruit', 'root', 'stem'
            rootstock: Rootstock type (impacts Phytophthora risk)
            drainage_quality: 'excellent', 'good', 'poor'
        """
        if image is None or image.size == 0:
            return []
        
        results = []
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        if plant_part == "root":
            # Phytophthora root rot (black mushy roots)
            phyto_score = self._detect_black_mushy_roots(hsv)
            if phyto_score > 0.4:
                resistance = self.rootstock_phytophthora_resistance.get(rootstock, 2)
                risk_multiplier = 1.0
                if drainage_quality == "poor":
                    risk_multiplier = 2.0
                elif drainage_quality == "good":
                    risk_multiplier = 0.7
                
                adjusted_score = min(1.0, phyto_score * risk_multiplier / (resistance / 5.0))
                
                warning = "🚨 CATASTROPHIC: Phytophthora root rot #1 killer"
                if rootstock == AvocadoRootstock.SEEDLING:
                    warning += " | SEEDLING ROOTSTOCK HIGHLY SUSCEPTIBLE - use Duke 7"
                if drainage_quality == "poor":
                    warning += " | POOR DRAINAGE = DEATH SENTENCE"
                
                results.append({
                    "disease": "Phytophthora Root Rot",
                    "confidence": adjusted_score,
                    "severity": "CATASTROPHIC - 40-60% global yield loss",
                    "warning": warning,
                    "rootstock_recommendation": "Duke 7 or Dusa (resistant)",
                    "treatment": "Trunk injection mefenoxam + excellent drainage + resistant rootstock"
                })
        
        elif plant_part == "fruit":
            # Anthracnose (black circular spots)
            anthr_score = self._detect_black_circular_spots(hsv)
            if anthr_score > 0.3:
                results.append({
                    "disease": "Anthracnose",
                    "confidence": anthr_score,
                    "severity": "#1 POSTHARVEST - 20-50% losses",
                    "treatment": "Hot water 122°F for 20 min + pre-harvest fungicides"
                })
            
            # Cercospora (purple-black spots)
            cercospora_score = self._detect_purple_black_spots(hsv)
            if cercospora_score > 0.3:
                results.append({
                    "disease": "Cercospora Spot",
                    "confidence": cercospora_score,
                    "severity": "Cosmetic damage, fruit downgraded",
                    "treatment": "Copper sprays weekly wet weather"
                })
            
            # Sunblotch viroid (yellow/white streaks)
            sunblotch_score = self._detect_yellow_streaks_fruit(hsv)
            if sunblotch_score > 0.4:
                results.append({
                    "disease": "Sunblotch Viroid",
                    "confidence": sunblotch_score,
                    "severity": "QUARANTINE - NO CURE",
                    "warning": "🚨 REMOVE TREE IMMEDIATELY - permanent infection, no treatment",
                    "treatment": "REMOVE TREE + use certified virus-free nursery stock"
                })
        
        elif plant_part == "leaf":
            # Cercospora (purple-brown spots with yellow halos)
            cercospora_score = self._detect_purple_brown_leaf_spots(hsv)
            if cercospora_score > 0.3:
                results.append({
                    "disease": "Cercospora Spot",
                    "confidence": cercospora_score,
                    "severity": "Defoliation 30-60%",
                    "treatment": "Copper weekly + azoxystrobin monthly"
                })
            
            # Sunblotch viroid (yellow mottling)
            sunblotch_score = self._detect_yellow_mottling_leaf(hsv)
            if sunblotch_score > 0.4:
                results.append({
                    "disease": "Sunblotch Viroid",
                    "confidence": sunblotch_score,
                    "severity": "PERMANENT INFECTION",
                    "warning": "🚨 NO CURE - remove tree",
                    "treatment": "REMOVE TREE"
                })
        
        elif plant_part == "stem":
            # Dothiorella canker (dark cankers with latex ooze)
            doth_score = self._detect_stem_cankers(hsv)
            if doth_score > 0.3:
                results.append({
                    "disease": "Dothiorella Canker",
                    "confidence": doth_score,
                    "severity": "Branch dieback + postharvest fruit rot 10-20%",
                    "treatment": "Prune 4-6 inches below canker + copper spray wounds"
                })
            
            # Bacterial canker (raised corky lesions)
            bact_score = self._detect_raised_corky_cankers(hsv)
            if bact_score > 0.3:
                results.append({
                    "disease": "Bacterial Canker",
                    "confidence": bact_score,
                    "severity": "Cankers + leaf spots",
                    "treatment": "Prune + copper weekly wet weather"
                })
        
        return results
    
    def _detect_black_mushy_roots(self, hsv: np.ndarray) -> float:
        """Detect black mushy roots (Phytophthora)"""
        black_lower = np.array([0, 0, 0])
        black_upper = np.array([180, 255, 50])
        black_mask = cv2.inRange(hsv, black_lower, black_upper)
        
        # Look for mushy texture (low contrast)
        gray = cv2.cvtColor(cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR), cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F).var()
        mushy = 1.0 if laplacian < 100 else 0.5
        
        coverage = np.sum(black_mask > 0) / black_mask.size
        return min(1.0, coverage * 15 * mushy)
    
    def _detect_black_circular_spots(self, hsv: np.ndarray) -> float:
        """Detect black circular spots on fruit (anthracnose)"""
        black_lower = np.array([0, 0, 0])
        black_upper = np.array([180, 255, 60])
        black_mask = cv2.inRange(hsv, black_lower, black_upper)
        
        contours, _ = cv2.findContours(black_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        circular_spots = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 50:
                perimeter = cv2.arcLength(contour, True)
                if perimeter > 0:
                    circularity = 4 * np.pi * area / (perimeter ** 2)
                    if circularity > 0.7:
                        circular_spots += 1
        
        return min(1.0, circular_spots * 0.15)
    
    def _detect_purple_black_spots(self, hsv: np.ndarray) -> float:
        """Detect purple-black spots on fruit (Cercospora)"""
        purple_lower = np.array([120, 50, 30])
        purple_upper = np.array([160, 200, 100])
        purple_mask = cv2.inRange(hsv, purple_lower, purple_upper)
        
        coverage = np.sum(purple_mask > 0) / purple_mask.size
        return min(1.0, coverage * 25)
    
    def _detect_yellow_streaks_fruit(self, hsv: np.ndarray) -> float:
        """Detect yellow/white streaks on fruit (sunblotch viroid)"""
        yellow_lower = np.array([20, 30, 150])
        yellow_upper = np.array([40, 150, 255])
        yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
        
        # Look for linear patterns (streaks)
        edges = cv2.Canny(yellow_mask, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=30, minLineLength=20, maxLineGap=5)
        
        streak_score = 0
        if lines is not None:
            streak_score = min(1.0, len(lines) * 0.1)
        
        return streak_score
    
    def _detect_purple_brown_leaf_spots(self, hsv: np.ndarray) -> float:
        """Detect purple-brown leaf spots with yellow halos (Cercospora)"""
        brown_lower = np.array([10, 50, 40])
        brown_upper = np.array([25, 200, 120])
        brown_mask = cv2.inRange(hsv, brown_lower, brown_upper)
        
        yellow_lower = np.array([20, 80, 150])
        yellow_upper = np.array([35, 255, 255])
        yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
        
        # Combine spots with halos
        combined = cv2.dilate(brown_mask, None, iterations=1)
        halo_overlap = cv2.bitwise_and(combined, yellow_mask)
        
        coverage = (np.sum(brown_mask > 0) + np.sum(halo_overlap > 0)) / brown_mask.size
        return min(1.0, coverage * 20)
    
    def _detect_yellow_mottling_leaf(self, hsv: np.ndarray) -> float:
        """Detect yellow mottling on leaves (sunblotch viroid)"""
        yellow_lower = np.array([20, 40, 100])
        yellow_upper = np.array([40, 200, 255])
        yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
        
        # Mottling = patchy, irregular pattern
        contours, _ = cv2.findContours(yellow_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        irregular_patches = sum(1 for c in contours if cv2.contourArea(c) > 100)
        
        return min(1.0, irregular_patches * 0.1)
    
    def _detect_stem_cankers(self, hsv: np.ndarray) -> float:
        """Detect stem cankers (Dothiorella)"""
        dark_lower = np.array([0, 0, 20])
        dark_upper = np.array([30, 150, 80])
        dark_mask = cv2.inRange(hsv, dark_lower, dark_upper)
        
        coverage = np.sum(dark_mask > 0) / dark_mask.size
        return min(1.0, coverage * 18)
    
    def _detect_raised_corky_cankers(self, hsv: np.ndarray) -> float:
        """Detect raised corky cankers (bacterial)"""
        brown_lower = np.array([10, 40, 60])
        brown_upper = np.array([25, 150, 130])
        brown_mask = cv2.inRange(hsv, brown_lower, brown_upper)
        
        # Raised = texture variation
        gray = cv2.cvtColor(cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR), cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        texture = 1.5 if laplacian_var > 500 else 1.0
        
        coverage = np.sum(brown_mask > 0) / brown_mask.size
        return min(1.0, coverage * 20 * texture)
    
    def assess_phytophthora_risk(self,
                                 rootstock: AvocadoRootstock,
                                 drainage: str,
                                 irrigation_frequency: str) -> Dict:
        """
        Assess Phytophthora root rot risk
        
        Returns risk assessment and recommendations
        """
        resistance = self.rootstock_phytophthora_resistance.get(rootstock, 2)
        
        risk_score = 10 - resistance  # Base risk from rootstock
        
        if drainage == "poor":
            risk_score += 5
        elif drainage == "good":
            risk_score += 1
        # excellent drainage adds 0
        
        if irrigation_frequency == "high":
            risk_score += 3
        elif irrigation_frequency == "moderate":
            risk_score += 1
        
        risk_score = min(10, risk_score)
        
        if risk_score >= 8:
            risk_level = "CATASTROPHIC"
            action = "🚨 IMMEDIATE ACTION: Change rootstock to Duke 7, improve drainage to raised beds"
        elif risk_score >= 6:
            risk_level = "HIGH"
            action = "Install raised beds, reduce irrigation, consider trunk injections"
        elif risk_score >= 4:
            risk_level = "MODERATE"
            action = "Monitor closely, ensure good drainage, preventative phosphite"
        else:
            risk_level = "LOW"
            action = "Continue current practices, monitor"
        
        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "rootstock_resistance": resistance,
            "recommended_action": action,
            "rootstock_recommendation": "Duke 7 or Dusa" if resistance < 7 else "Current rootstock adequate"
        }


if __name__ == "__main__":
    print("=" * 80)
    print("AVOCADO DISEASE DETECTION SYSTEM")
    print("=" * 80)
    print("\n🚨 PHYTOPHTHORA ROOT ROT: #1 WORLDWIDE AVOCADO KILLER")
    print("   Pathogen: Phytophthora cinnamomi")
    print("   Impact: 40-60% GLOBAL YIELD LOSS, $40-70M annual California losses")
    print("   Symptoms: Wilting + black mushy roots + tree death (90% mortality)")
    print("   Treatment: Duke 7 rootstock + excellent drainage + trunk injections")
    print("   Prevention: RAISED BEDS 12-18 inches + drip irrigation + avoid overwatering")
    print("\n🍐 ANTHRACNOSE: #1 POSTHARVEST DISEASE")
    print("   Impact: 20-50% postharvest losses")
    print("   Symptoms: Black circular fruit spots at ripening")
    print("   Treatment: Hot water 122°F for 20 min + pre-harvest fungicides")
    print("\n⚠️  ROOTSTOCK RESISTANCE (Phytophthora):")
    print("   Duke 7: ⭐⭐⭐⭐⭐ (9/10) - BEST")
    print("   Dusa: ⭐⭐⭐⭐ (8/10) - Excellent + salt-tolerant")
    print("   Thomas: ⭐⭐⭐ (6/10) - Moderate")
    print("   Seedling: ⭐ (2/10) - AVOID")
    print("\n💰 MARKET: $13B global, USA $411M")
    print("   Hass: 95% California production, $1.50-3.00/avocado retail")
    print("   Tree replacement: $150-300 + 3-4 years lost production")
    print("\n✓ Avocado disease detection system initialized")
    print("  8 diseases | Rootstock resistance | Phytophthora risk assessment")
    print("=" * 80)
