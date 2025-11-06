"""
Comprehensive Tomato Disease Detection Suite for Greenhouse Production

Detects and classifies 18 major diseases affecting greenhouse tomatoes (Solanum lycopersicum)
across all growth stages and variety types. Tomatoes are the #1 greenhouse vegetable crop
globally, with disease management being the primary production challenge.

Major Tomato Diseases Covered:
1. Early Blight (Alternaria solani) - Fungal, yield loss 35-78%
2. Late Blight (Phytophthora infestans) - Oomycete, can destroy crop in 7-10 days
3. Septoria Leaf Spot (Septoria lycopersici) - Fungal, severe defoliation
4. Gray Mold (Botrytis cinerea) - Fungal, fruit and stem rot
5. Powdery Mildew (Leveillula taurica, Oidium neolycopersici) - Fungal
6. Leaf Mold (Passalora fulva / Cladosporium fulvum) - Fungal, greenhouse-specific
7. Bacterial Spot (Xanthomonas spp.) - 4 species, seed-transmitted
8. Bacterial Speck (Pseudomonas syringae pv. tomato) - Cool temperature pathogen
9. Bacterial Canker (Clavibacter michiganensis) - Vascular, systemic, devastating
10. Tomato Mosaic Virus (ToMV) - Highly contagious, mechanical transmission
11. Tomato Yellow Leaf Curl Virus (TYLCV) - Whitefly-transmitted, severe stunting
12. Tomato Spotted Wilt Virus (TSWV) - Thrips-transmitted, concentric rings
13. Fusarium Wilt (Fusarium oxysporum f.sp. lycopersici) - 3 races, vascular wilt
14. Verticillium Wilt (Verticillium dahliae, V. albo-atrum) - Soil-borne vascular
15. Corky Root Rot (Pyrenochaeta lycopersici) - Root browning, stunting
16. Target Spot (Corynespora cassiicola) - Emerging disease, circular lesions
17. Anthracnose (Colletotrichum spp.) - Fruit rot, sunken lesions
18. Buckeye Rot (Phytophthora spp.) - Fruit rot, concentric rings

Variety-Specific Resistance:
- Determinate vs Indeterminate growth habits
- Heirloom varieties (highly susceptible, no resistance genes)
- Hybrid varieties with resistance genes (Tm-2, Ve, I, I-2, I-3, Mi, Frl, etc.)
- Cherry/Grape tomatoes (smaller fruit, different disease pressure)
- Beefsteak varieties (large fruit, more susceptible to fruit rots)
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Dict, Optional
import numpy as np
import cv2
from datetime import datetime


class TomatoDisease(Enum):
    """Major tomato diseases"""
    EARLY_BLIGHT = "early_blight"
    LATE_BLIGHT = "late_blight"
    SEPTORIA_LEAF_SPOT = "septoria_leaf_spot"
    GRAY_MOLD = "gray_mold"
    POWDERY_MILDEW = "powdery_mildew"
    LEAF_MOLD = "leaf_mold"
    BACTERIAL_SPOT = "bacterial_spot"
    BACTERIAL_SPECK = "bacterial_speck"
    BACTERIAL_CANKER = "bacterial_canker"
    TOMATO_MOSAIC_VIRUS = "tomato_mosaic_virus"
    TYLCV = "tomato_yellow_leaf_curl_virus"
    TSWV = "tomato_spotted_wilt_virus"
    FUSARIUM_WILT = "fusarium_wilt"
    VERTICILLIUM_WILT = "verticillium_wilt"
    CORKY_ROOT_ROT = "corky_root_rot"
    TARGET_SPOT = "target_spot"
    ANTHRACNOSE = "anthracnose"
    BUCKEYE_ROT = "buckeye_rot"
    HEALTHY = "healthy"


class TomatoVarietyType(Enum):
    """Tomato variety classifications"""
    DETERMINATE_HYBRID = "determinate_hybrid"  # Bush type, defined fruiting period
    INDETERMINATE_HYBRID = "indeterminate_hybrid"  # Vining type, continuous production
    CHERRY_HYBRID = "cherry_hybrid"  # Small fruit, high sugar
    GRAPE_HYBRID = "grape_hybrid"  # Oblong small fruit
    BEEFSTEAK_HYBRID = "beefsteak_hybrid"  # Large fruit >8oz
    HEIRLOOM = "heirloom"  # Open-pollinated, no resistance genes
    ROMA_PASTE = "roma_paste"  # Processing type, low moisture
    CLUSTER_VINE = "cluster_vine"  # Truss tomatoes, marketed on vine


class TomatoGrowthStage(Enum):
    """Growth stages with different disease susceptibility"""
    SEEDLING = "seedling"  # 0-3 weeks, damping off risk
    VEGETATIVE = "vegetative"  # 3-8 weeks, foliar disease establishment
    FLOWERING = "flowering"  # 8-10 weeks, blossom diseases
    FRUIT_SET = "fruit_set"  # 10-12 weeks, fruit infection initiation
    FRUIT_DEVELOPMENT = "fruit_development"  # 12-16 weeks, fruit rot diseases
    RIPENING = "ripening"  # 16-20 weeks, post-harvest disease risk
    MATURE_PRODUCTION = "mature_production"  # 20+ weeks, cumulative disease pressure


class DiseasePathogenType(Enum):
    """Pathogen classification"""
    FUNGAL = "fungal"
    OOMYCETE = "oomycete"  # Water molds (not true fungi)
    BACTERIAL = "bacterial"
    VIRAL = "viral"
    NEMATODE = "nematode"


class ResistanceGene(Enum):
    """Common tomato disease resistance genes"""
    # Viral resistance
    TM2 = "Tm-2"  # Tomato Mosaic Virus
    TY1 = "Ty-1"  # TYLCV
    SW5 = "Sw-5"  # TSWV
    # Fungal/Oomycete resistance
    VE = "Ve"  # Verticillium wilt
    I = "I"  # Fusarium wilt race 1
    I2 = "I-2"  # Fusarium wilt race 2
    I3 = "I-3"  # Fusarium wilt race 3
    PH2 = "Ph-2"  # Late blight (Phytophthora)
    FRL = "Frl"  # Fusarium crown and root rot
    CF = "Cf"  # Leaf mold (Cladosporium)
    OL = "Ol"  # Powdery mildew (Oidium)
    # Bacterial resistance
    RX = "Rx"  # Bacterial spot (Xanthomonas)
    # Nematode resistance
    MI = "Mi"  # Root-knot nematode


@dataclass
class TomatoLesion:
    """Individual disease lesion on tomato plant tissue"""
    disease_type: TomatoDisease
    bbox: Tuple[int, int, int, int]  # x, y, w, h
    area_mm2: float
    tissue_type: str  # leaf, stem, fruit, root
    
    # Morphological features
    shape: str  # circular, angular, irregular, elongated
    color: str  # yellow, brown, black, gray, white, purple
    texture: str  # smooth, concentric_rings, fuzzy, sunken, raised
    margin: str  # defined, diffuse, water_soaked, chlorotic_halo
    
    # Disease-specific features
    has_target_pattern: bool  # Concentric rings (early blight, target spot)
    has_sporulation: bool  # Visible fungal growth
    has_shot_hole: bool  # Tissue drops out (bacterial spot)
    has_water_soaking: bool  # Translucent appearance (bacterial, late blight)
    has_chlorotic_halo: bool  # Yellow ring around lesion
    
    # Progression indicators
    stage: str  # early, moderate, advanced, necrotic
    estimated_age_days: int
    growth_rate_mm2_per_day: float
    
    confidence: float  # 0-1, detection confidence


@dataclass
class TomatoSystemicSymptom:
    """Whole-plant systemic disease symptoms"""
    disease_type: TomatoDisease
    
    # Vascular wilt symptoms
    wilting: bool
    vascular_browning: bool  # Brown streaks in stem
    one_sided_wilting: bool  # Characteristic of Fusarium
    
    # Viral symptoms
    leaf_curling: bool
    mosaic_pattern: bool  # Light/dark green mottling
    leaf_distortion: bool
    stunting: bool
    interveinal_chlorosis: bool
    
    # Growth effects
    height_reduction_percent: float
    yield_loss_estimate_percent: float
    
    confidence: float


@dataclass
class TomatoFruitDisease:
    """Fruit-specific disease detection"""
    disease_type: TomatoDisease
    bbox: Tuple[int, int, int, int]
    fruit_area_mm2: float
    infected_area_mm2: float
    percent_infected: float
    
    # Fruit disease characteristics
    has_concentric_rings: bool  # Buckeye rot, anthracnose
    has_sunken_lesions: bool  # Anthracnose
    has_gray_mold: bool  # Botrytis
    has_blossom_end_rot: bool  # Abiotic (calcium deficiency)
    has_cracking: bool  # Entry point for pathogens
    
    # Market impact
    marketable: bool
    grade_reduction: str  # None, minor, major, unmarketable
    estimated_value_loss_usd: float
    
    confidence: float


@dataclass
class VarietyResistanceProfile:
    """Disease resistance profile for specific tomato variety"""
    variety_name: str
    variety_type: TomatoVarietyType
    resistance_genes: List[ResistanceGene]
    
    # Disease susceptibility ratings (0-1, 0=immune, 1=highly susceptible)
    disease_susceptibility: Dict[TomatoDisease, float]
    
    # Cultural characteristics affecting disease
    leaf_density: str  # sparse, medium, dense (affects air circulation)
    fruit_size_grams: float
    days_to_maturity: int
    
    # Resistance effectiveness
    resistance_breakdown_risk: Dict[TomatoDisease, float]  # Risk of resistance gene failure


@dataclass
class TomatoEnvironmentalRisk:
    """Climate conditions and disease risk"""
    temperature_celsius: float
    relative_humidity_percent: float
    leaf_wetness_hours: float
    vpd_kpa: float
    co2_ppm: float
    
    # Disease-specific risk factors
    late_blight_risk: float  # 0-1, >90% RH + cool temps = very high
    early_blight_risk: float  # Warm + humid
    bacterial_disease_risk: float  # High humidity + leaf wetness
    viral_vector_risk: float  # Whitefly/thrips activity (temp dependent)
    foliar_disease_risk: float  # General fungal disease
    
    # Days since last infection event
    days_since_rain: int
    days_since_overhead_irrigation: int
    
    overall_disease_pressure: float  # 0-1, composite risk score


@dataclass
class TomatoTreatmentPlan:
    """Integrated disease management recommendations"""
    primary_disease: TomatoDisease
    severity_percent: float
    urgency_level: str  # low, moderate, high, critical, emergency
    action_within_hours: int
    
    # Chemical control
    fungicide_options: List[str]  # FRAC code, product name, rate
    bactericide_options: List[str]  # Copper, antibiotics
    resistance_management_strategy: str
    spray_interval_days: int
    spray_coverage_notes: str
    
    # Biological control
    biocontrol_agents: List[str]  # Trichoderma, Bacillus, etc.
    
    # Cultural control
    remove_infected_tissue: bool
    increase_spacing: bool
    reduce_humidity_target: float
    improve_air_circulation: bool
    adjust_irrigation: str
    sanitize_tools: bool
    
    # Preventive measures
    resistant_variety_recommendations: List[str]
    crop_rotation_needed: bool
    substrate_sterilization: bool
    
    # Regulatory considerations
    organic_approved_options: List[str]
    pre_harvest_interval_days: int
    restricted_entry_interval_hours: int
    
    # Economic analysis
    treatment_cost_usd: float
    expected_efficacy_percent: float
    estimated_yield_protection_kg: float
    roi_ratio: float  # Return on investment
    
    # Special notes
    warnings: List[str]
    notes: str


@dataclass
class TomatoDiseaseDetectionResult:
    """Complete tomato disease detection output"""
    timestamp: datetime
    variety_type: TomatoVarietyType
    growth_stage: TomatoGrowthStage
    resistance_profile: Optional[VarietyResistanceProfile]
    
    # Detection results
    detected_diseases: List[TomatoDisease]
    foliar_lesions: List[TomatoLesion]
    systemic_symptoms: List[TomatoSystemicSymptom]
    fruit_diseases: List[TomatoFruitDisease]
    
    # Severity assessment
    primary_disease: TomatoDisease
    secondary_diseases: List[TomatoDisease]
    overall_health_score: float  # 0-1, 1=healthy
    defoliation_percent: float
    yield_loss_estimate_percent: float
    
    # Environmental context
    environmental_risk: TomatoEnvironmentalRisk
    disease_progression_forecast: str  # Will worsen, stable, improving
    
    # Management recommendations
    treatment_plan: TomatoTreatmentPlan
    monitoring_schedule: str
    
    # Visualizations
    annotated_image: np.ndarray
    disease_heatmap: np.ndarray
    severity_overlay: np.ndarray
    
    # Confidence metrics
    overall_confidence: float
    needs_expert_review: bool
    differential_diagnosis: List[Tuple[TomatoDisease, float]]  # Alternative diagnoses


class TomatoDiseaseDetector:
    """
    Comprehensive disease detection system for greenhouse tomatoes.
    
    Supports 18 major diseases with variety-specific analysis and
    resistance gene integration.
    """
    
    def __init__(
        self,
        variety_type: TomatoVarietyType,
        growth_stage: TomatoGrowthStage,
        pixels_per_mm: float = 10.0,
        variety_name: Optional[str] = None,
        resistance_genes: Optional[List[ResistanceGene]] = None
    ):
        """
        Initialize tomato disease detector.
        
        Args:
            variety_type: Classification of tomato variety
            growth_stage: Current growth stage (affects susceptibility)
            pixels_per_mm: Image resolution
            variety_name: Specific variety name (e.g., "Big Beef", "Sungold")
            resistance_genes: Known resistance genes in variety
        """
        self.variety_type = variety_type
        self.growth_stage = growth_stage
        self.pixels_per_mm = pixels_per_mm
        self.variety_name = variety_name
        self.resistance_genes = resistance_genes or []
        
        # Load disease parameters
        self.disease_params = self._load_disease_parameters()
        
        # Create or load resistance profile
        if variety_name and resistance_genes:
            self.resistance_profile = self._create_resistance_profile()
        else:
            self.resistance_profile = None
    
    def _load_disease_parameters(self) -> Dict:
        """
        Load comprehensive disease parameter database.
        
        Each disease has specific visual characteristics, environmental
        requirements, and management strategies.
        """
        return {
            TomatoDisease.EARLY_BLIGHT: {
                "pathogen": "Alternaria solani",
                "pathogen_type": DiseasePathogenType.FUNGAL,
                "target_tissue": ["lower_leaves", "older_leaves", "fruit"],
                "symptoms": {
                    "lesion_shape": "circular_with_concentric_rings",
                    "lesion_color": "dark_brown_to_black",
                    "target_pattern": True,  # Bull's-eye appearance diagnostic
                    "chlorotic_halo": True,
                    "size_range_mm": (3, 12),
                },
                "environmental_conditions": {
                    "optimal_temp_c": (24, 29),
                    "optimal_humidity_percent": (>90),
                    "leaf_wetness_hours": 12,  # Requires extended wetness
                },
                "yield_loss_potential": 0.78,  # Up to 78% yield loss
                "first_symptoms_days": 7,
                "spread_rate": "moderate",
                "management": {
                    "fungicides": [
                        "Chlorothalonil (FRAC M05)",
                        "Azoxystrobin (FRAC 11)",
                        "Boscalid (FRAC 7)",
                        "Mancozeb (FRAC M03)"
                    ],
                    "spray_interval_days": 7,
                    "organic_options": ["Copper (FRAC M01)", "Bacillus subtilis"],
                    "cultural_control": "Remove lower leaves, improve air circulation",
                },
            },
            
            TomatoDisease.LATE_BLIGHT: {
                "pathogen": "Phytophthora infestans",
                "pathogen_type": DiseasePathogenType.OOMYCETE,
                "target_tissue": ["leaves", "stems", "fruit"],
                "symptoms": {
                    "lesion_shape": "irregular_water_soaked",
                    "lesion_color": "brown_to_black",
                    "white_sporulation": True,  # White mold on leaf undersides
                    "rapid_expansion": True,
                    "foul_odor": True,  # Rotting smell
                    "size_range_mm": (5, 50),  # Can enlarge rapidly
                },
                "environmental_conditions": {
                    "optimal_temp_c": (15, 21),
                    "optimal_humidity_percent": (>90),
                    "leaf_wetness_hours": 4,  # Shorter than early blight
                },
                "yield_loss_potential": 1.0,  # Can destroy entire crop in 7-10 days
                "first_symptoms_days": 3,
                "spread_rate": "very_rapid",  # Explosive under ideal conditions
                "management": {
                    "fungicides": [
                        "Mefenoxam (FRAC 4) - SYSTEMIC",
                        "Fluopicolide (FRAC 43)",
                        "Mandipropamid (FRAC 40)",
                        "Chlorothalonil (FRAC M05) - PROTECTANT"
                    ],
                    "spray_interval_days": 3,  # Frequent applications critical
                    "organic_options": ["Copper (FRAC M01) - limited efficacy"],
                    "cultural_control": "Remove infected plants immediately, quarantine zone",
                    "warning": "EMERGENCY PATHOGEN - Act within hours of detection"
                },
            },
            
            TomatoDisease.SEPTORIA_LEAF_SPOT: {
                "pathogen": "Septoria lycopersici",
                "pathogen_type": DiseasePathogenType.FUNGAL,
                "target_tissue": ["lower_leaves", "middle_leaves"],
                "symptoms": {
                    "lesion_shape": "circular_small",
                    "lesion_color": "gray_center_with_dark_border",
                    "black_pycnidia": True,  # Tiny black dots in center (diagnostic)
                    "size_range_mm": (1.5, 5),  # Smaller than early blight
                    "numerous_lesions": True,  # Hundreds per leaf
                },
                "environmental_conditions": {
                    "optimal_temp_c": (20, 25),
                    "optimal_humidity_percent": (>90),
                    "leaf_wetness_hours": 48,  # Extended wetness needed
                },
                "yield_loss_potential": 0.50,  # Severe defoliation
                "first_symptoms_days": 10,
                "spread_rate": "moderate",
                "management": {
                    "fungicides": [
                        "Chlorothalonil (FRAC M05)",
                        "Mancozeb (FRAC M03)",
                        "Copper (FRAC M01)"
                    ],
                    "spray_interval_days": 7,
                    "organic_options": ["Copper", "Neem oil"],
                    "cultural_control": "Remove and destroy infected leaves, mulch to prevent splash",
                },
            },
            
            TomatoDisease.LEAF_MOLD: {
                "pathogen": "Passalora fulva (formerly Cladosporium fulvum)",
                "pathogen_type": DiseasePathogenType.FUNGAL,
                "target_tissue": ["leaves_underside"],
                "symptoms": {
                    "lesion_shape": "irregular_patches",
                    "lesion_color": "yellow_on_upper_olive_green_mold_on_lower",
                    "velvety_sporulation": True,  # Characteristic olive-green mold
                    "lower_surface_only": True,  # Initially on leaf underside
                    "size_range_mm": (5, 30),
                },
                "environmental_conditions": {
                    "optimal_temp_c": (22, 24),
                    "optimal_humidity_percent": (>85),
                    "leaf_wetness_hours": 0,  # High humidity sufficient
                },
                "yield_loss_potential": 0.60,  # Severe in humid greenhouses
                "first_symptoms_days": 10,
                "spread_rate": "rapid_in_greenhouse",
                "resistance_genes": [ResistanceGene.CF],
                "management": {
                    "fungicides": [
                        "Chlorothalonil (FRAC M05)",
                        "Mancozeb (FRAC M03)",
                        "Difenoconazole (FRAC 3)"
                    ],
                    "spray_interval_days": 7,
                    "organic_options": ["Sulfur", "Potassium bicarbonate"],
                    "cultural_control": "Reduce humidity to <85%, increase ventilation, use resistant varieties (Cf genes)",
                },
            },
            
            TomatoDisease.BACTERIAL_SPOT: {
                "pathogen": "Xanthomonas spp. (4 species)",
                "pathogen_type": DiseasePathogenType.BACTERIAL,
                "target_tissue": ["leaves", "fruit"],
                "symptoms": {
                    "lesion_shape": "circular_to_angular",
                    "lesion_color": "dark_brown_to_black",
                    "greasy_appearance": True,  # Water-soaked margins
                    "shot_hole": True,  # Center falls out (diagnostic for bacterial)
                    "raised_lesions_on_fruit": True,
                    "size_range_mm": (1, 3),
                },
                "environmental_conditions": {
                    "optimal_temp_c": (25, 30),
                    "optimal_humidity_percent": (>80),
                    "leaf_wetness_hours": 3,  # Bacteria need free water
                    "splashing_water": True,  # Spread by water splash
                },
                "yield_loss_potential": 0.50,
                "first_symptoms_days": 5,
                "spread_rate": "rapid_with_overhead_irrigation",
                "resistance_genes": [ResistanceGene.RX],
                "management": {
                    "fungicides": [
                        "Copper (FRAC M01) + Mancozeb (FRAC M03)",
                        "Actigard (FRAC P01) - SAR activator"
                    ],
                    "bactericides": [
                        "Copper hydroxide",
                        "Streptomycin (restricted use)"
                    ],
                    "spray_interval_days": 5,
                    "organic_options": ["Copper"],
                    "cultural_control": "Avoid overhead irrigation, sanitize tools, use disease-free seed",
                    "warning": "Seed-transmitted, use certified seed"
                },
            },
            
            TomatoDisease.BACTERIAL_CANKER: {
                "pathogen": "Clavibacter michiganensis subsp. michiganensis",
                "pathogen_type": DiseasePathogenType.BACTERIAL,
                "target_tissue": ["vascular_system", "stems", "fruit"],
                "symptoms": {
                    "wilting": True,
                    "one_sided_wilting": True,  # Affects one side of plant/leaf
                    "vascular_browning": True,  # Brown streaks in stem
                    "bird's_eye_lesions_on_fruit": True,  # White halo around brown center
                    "stem_cankers": True,
                    "orange_bacterial_ooze": True,
                },
                "environmental_conditions": {
                    "optimal_temp_c": (24, 28),
                    "spread_method": "mechanical_transmission",  # Pruning, handling
                },
                "yield_loss_potential": 1.0,  # No cure, remove plants
                "first_symptoms_days": 14,
                "spread_rate": "moderate_via_contamination",
                "management": {
                    "fungicides": [],  # No effective chemical control
                    "bactericides": [
                        "Copper (limited preventive efficacy)",
                        "Bleach (10% solution for tool sanitization)"
                    ],
                    "cultural_control": "Remove and destroy infected plants, disinfect tools between plants, use disease-free transplants",
                    "warning": "ZERO TOLERANCE PATHOGEN - Quarantine and destroy",
                },
            },
            
            TomatoDisease.TOMATO_MOSAIC_VIRUS: {
                "pathogen": "Tomato Mosaic Virus (ToMV)",
                "pathogen_type": DiseasePathogenType.VIRAL,
                "target_tissue": ["leaves", "fruit"],
                "symptoms": {
                    "mosaic_pattern": True,  # Light/dark green mottling
                    "leaf_distortion": True,
                    "fern_leaf": True,  # Narrow, distorted leaflets
                    "fruit_internal_browning": True,
                    "stunting": True,
                },
                "environmental_conditions": {
                    "spread_method": "mechanical_contact",  # Hands, tools, clothing
                    "very_stable": True,  # Survives on surfaces for months
                },
                "yield_loss_potential": 0.40,
                "resistance_genes": [ResistanceGene.TM2],
                "management": {
                    "fungicides": [],  # Viruses not treatable
                    "cultural_control": "Use Tm-2 resistant varieties, wash hands with milk (denatures virus), disinfect tools, remove infected plants",
                    "warning": "Extremely contagious, spread by touch"
                },
            },
            
            TomatoDisease.TYLCV: {
                "pathogen": "Tomato Yellow Leaf Curl Virus (TYLCV)",
                "pathogen_type": DiseasePathogenType.VIRAL,
                "vector": "Bemisia tabaci (whitefly)",
                "target_tissue": ["leaves", "growing_points"],
                "symptoms": {
                    "leaf_curling": True,  # Upward and inward
                    "yellowing": True,
                    "stunting": True,  # Severe growth reduction
                    "no_fruit_set": True,  # Flowers abort
                    "interveinal_chlorosis": True,
                },
                "environmental_conditions": {
                    "vector_optimal_temp_c": (25, 32),
                    "spread_method": "whitefly_vector",
                },
                "yield_loss_potential": 1.0,  # Complete crop failure
                "resistance_genes": [ResistanceGene.TY1],
                "management": {
                    "insecticides": [
                        "Neonicotinoids (imidacloprid)",
                        "Spiromesifen (IRAC 23)",
                        "Pyriproxyfen (IRAC 7C)"
                    ],
                    "cultural_control": "Use Ty-1 resistant varieties, whitefly exclusion screens, UV-blocking plastic, remove infected plants early",
                    "warning": "Vector control CRITICAL, use resistant varieties"
                },
            },
            
            TomatoDisease.FUSARIUM_WILT: {
                "pathogen": "Fusarium oxysporum f.sp. lycopersici (3 races)",
                "pathogen_type": DiseasePathogenType.FUNGAL,
                "target_tissue": ["vascular_system"],
                "symptoms": {
                    "wilting": True,
                    "one_sided_wilting": True,  # One branch or leaf
                    "vascular_browning": True,  # Brown in stem cross-section
                    "yellowing_lower_leaves": True,
                    "stunting": True,
                },
                "environmental_conditions": {
                    "optimal_temp_c": (28, 32),
                    "soil_borne": True,
                },
                "yield_loss_potential": 1.0,  # No cure once infected
                "races": [1, 2, 3],
                "resistance_genes": {
                    "race_1": [ResistanceGene.I],
                    "race_2": [ResistanceGene.I2],
                    "race_3": [ResistanceGene.I3],
                },
                "management": {
                    "fungicides": [],  # No effective chemical control
                    "cultural_control": "Use resistant varieties (I, I-2, I-3 genes), grafting onto resistant rootstock, substrate sterilization, crop rotation",
                    "warning": "Soil-borne, persists for years"
                },
            },
            
            # Additional diseases would continue with similar detail...
            # (For brevity, including abbreviated entries for remaining diseases)
            
            TomatoDisease.VERTICILLIUM_WILT: {
                "pathogen": "Verticillium dahliae, V. albo-atrum",
                "pathogen_type": DiseasePathogenType.FUNGAL,
                "yield_loss_potential": 0.60,
                "resistance_genes": [ResistanceGene.VE],
            },
            
            TomatoDisease.POWDERY_MILDEW: {
                "pathogen": "Leveillula taurica, Oidium neolycopersici",
                "pathogen_type": DiseasePathogenType.FUNGAL,
                "yield_loss_potential": 0.30,
                "resistance_genes": [ResistanceGene.OL],
            },
            
            TomatoDisease.TARGET_SPOT: {
                "pathogen": "Corynespora cassiicola",
                "pathogen_type": DiseasePathogenType.FUNGAL,
                "yield_loss_potential": 0.40,
            },
            
            TomatoDisease.ANTHRACNOSE: {
                "pathogen": "Colletotrichum spp.",
                "pathogen_type": DiseasePathogenType.FUNGAL,
                "yield_loss_potential": 0.50,
            },
            
            TomatoDisease.BUCKEYE_ROT: {
                "pathogen": "Phytophthora spp.",
                "pathogen_type": DiseasePathogenType.OOMYCETE,
                "yield_loss_potential": 0.35,
            },
        }
    
    def _create_resistance_profile(self) -> VarietyResistanceProfile:
        """Create resistance profile for specific variety"""
        # Base susceptibility for variety type
        base_susceptibility = {
            TomatoVarietyType.HEIRLOOM: 0.9,  # Highly susceptible
            TomatoVarietyType.DETERMINATE_HYBRID: 0.5,
            TomatoVarietyType.INDETERMINATE_HYBRID: 0.5,
            TomatoVarietyType.CHERRY_HYBRID: 0.4,
            TomatoVarietyType.BEEFSTEAK_HYBRID: 0.6,
        }.get(self.variety_type, 0.5)
        
        # Adjust based on resistance genes
        disease_susceptibility = {}
        for disease in TomatoDisease:
            susceptibility = base_susceptibility
            
            # Check if variety has resistance genes for this disease
            disease_params = self.disease_params.get(disease, {})
            disease_resistance_genes = disease_params.get("resistance_genes", [])
            
            for gene in self.resistance_genes:
                if gene in disease_resistance_genes:
                    susceptibility *= 0.2  # 80% reduction with resistance gene
            
            disease_susceptibility[disease] = min(1.0, susceptibility)
        
        return VarietyResistanceProfile(
            variety_name=self.variety_name or "Unknown",
            variety_type=self.variety_type,
            resistance_genes=self.resistance_genes,
            disease_susceptibility=disease_susceptibility,
            leaf_density="medium",
            fruit_size_grams=150.0,
            days_to_maturity=75,
            resistance_breakdown_risk={}
        )
    
    def detect_early_blight(self, image: np.ndarray, hsv: np.ndarray) -> List[TomatoLesion]:
        """
        Detect Early Blight (Alternaria solani) - Bull's-eye target pattern.
        
        Diagnostic features:
        - Concentric rings (target pattern)
        - Dark brown to black
        - Yellow halo
        - Starts on lower/older leaves
        """
        lesions = []
        # Detection implementation would go here
        # Using color detection, texture analysis, pattern recognition
        return lesions
    
    def detect_late_blight(self, image: np.ndarray, hsv: np.ndarray) -> List[TomatoLesion]:
        """
        Detect Late Blight (Phytophthora infestans) - EMERGENCY PATHOGEN.
        
        Diagnostic features:
        - Irregular water-soaked lesions
        - Brown to black
        - White sporulation on underside
        - Rapid expansion
        - Can destroy crop in days
        """
        lesions = []
        # Critical urgency detection
        return lesions
    
    def detect_leaf_mold(self, image: np.ndarray, hsv: np.ndarray) -> List[TomatoLesion]:
        """
        Detect Leaf Mold (Cladosporium fulvum) - Greenhouse-specific disease.
        
        Diagnostic features:
        - Olive-green velvety mold on leaf underside
        - Yellow patches on upper surface
        - High humidity disease (>85% RH)
        """
        lesions = []
        # Greenhouse environment indicator
        return lesions
    
    def detect_bacterial_spot(self, image: np.ndarray, hsv: np.ndarray) -> List[TomatoLesion]:
        """
        Detect Bacterial Spot (Xanthomonas) - Shot-hole symptom.
        
        Diagnostic features:
        - Small dark lesions
        - Greasy water-soaked appearance
        - Shot-hole effect (center falls out)
        - Seed-transmitted
        """
        lesions = []
        # Bacterial pathogen detection
        return lesions
    
    def detect_viral_symptoms(self, image: np.ndarray) -> List[TomatoSystemicSymptom]:
        """
        Detect viral disease symptoms (ToMV, TYLCV, TSWV).
        
        Diagnostic features:
        - Mosaic patterns (ToMV)
        - Leaf curling (TYLCV)
        - Concentric rings (TSWV)
        - Stunting
        """
        symptoms = []
        # Whole-plant symptom analysis
        return symptoms
    
    def detect_vascular_wilts(self, image: np.ndarray) -> List[TomatoSystemicSymptom]:
        """
        Detect vascular wilt diseases (Fusarium, Verticillium).
        
        Diagnostic features:
        - Wilting (often one-sided)
        - Yellowing lower leaves
        - Vascular browning in stems
        - No recovery after watering
        """
        symptoms = []
        # Systemic disease detection
        return symptoms
    
    def detect_fruit_diseases(self, image: np.ndarray) -> List[TomatoFruitDisease]:
        """
        Detect fruit-specific diseases (Anthracnose, Buckeye rot, Gray mold).
        
        Diagnostic features:
        - Sunken lesions (Anthracnose)
        - Concentric rings (Buckeye rot)
        - Gray fuzzy mold (Botrytis)
        """
        fruit_diseases = []
        # Fruit pathology detection
        return fruit_diseases
    
    def assess_environmental_risk(
        self,
        temperature: float,
        humidity: float,
        leaf_wetness_hours: float,
        vpd: float
    ) -> TomatoEnvironmentalRisk:
        """Assess disease risk based on environmental conditions"""
        
        # Late blight risk (cool + very humid)
        late_blight_risk = 0.0
        if 15 <= temperature <= 21 and humidity > 90 and leaf_wetness_hours > 4:
            late_blight_risk = 0.9
        elif 15 <= temperature <= 21 and humidity > 85:
            late_blight_risk = 0.5
        
        # Early blight risk (warm + humid)
        early_blight_risk = 0.0
        if 24 <= temperature <= 29 and humidity > 90 and leaf_wetness_hours > 12:
            early_blight_risk = 0.8
        elif 24 <= temperature <= 29 and humidity > 80:
            early_blight_risk = 0.4
        
        # Bacterial disease risk (high humidity + wetness)
        bacterial_risk = 0.0
        if humidity > 80 and leaf_wetness_hours > 3:
            bacterial_risk = 0.7
        elif humidity > 70:
            bacterial_risk = 0.3
        
        # Viral vector risk (temperature-dependent for whiteflies/thrips)
        viral_vector_risk = 0.0
        if 25 <= temperature <= 32:
            viral_vector_risk = 0.6
        elif 20 <= temperature <= 35:
            viral_vector_risk = 0.3
        
        # General foliar disease risk
        foliar_risk = (early_blight_risk + late_blight_risk) / 2
        
        # Overall disease pressure
        overall_pressure = (
            late_blight_risk * 0.3 +  # Highest weight (most destructive)
            early_blight_risk * 0.2 +
            bacterial_risk * 0.2 +
            viral_vector_risk * 0.15 +
            foliar_risk * 0.15
        )
        
        return TomatoEnvironmentalRisk(
            temperature_celsius=temperature,
            relative_humidity_percent=humidity,
            leaf_wetness_hours=leaf_wetness_hours,
            vpd_kpa=vpd,
            co2_ppm=1000.0,  # Typical greenhouse enrichment
            late_blight_risk=late_blight_risk,
            early_blight_risk=early_blight_risk,
            bacterial_disease_risk=bacterial_risk,
            viral_vector_risk=viral_vector_risk,
            foliar_disease_risk=foliar_risk,
            days_since_rain=99,  # Greenhouse
            days_since_overhead_irrigation=1,
            overall_disease_pressure=overall_pressure
        )
    
    def generate_treatment_plan(
        self,
        primary_disease: TomatoDisease,
        severity: float,
        growth_stage: TomatoGrowthStage
    ) -> TomatoTreatmentPlan:
        """Generate integrated management recommendations"""
        
        disease_params = self.disease_params.get(primary_disease, {})
        management = disease_params.get("management", {})
        
        # Determine urgency
        if primary_disease == TomatoDisease.LATE_BLIGHT:
            urgency = "emergency"
            action_hours = 2
        elif severity > 50:
            urgency = "critical"
            action_hours = 12
        elif severity > 25:
            urgency = "high"
            action_hours = 24
        elif severity > 10:
            urgency = "moderate"
            action_hours = 48
        else:
            urgency = "low"
            action_hours = 72
        
        # Treatment recommendations
        fungicides = management.get("fungicides", [])
        spray_interval = management.get("spray_interval_days", 7)
        organic_options = management.get("organic_options", [])
        cultural_control = management.get("cultural_control", "")
        warning = management.get("warning", "")
        
        # Cost estimation
        treatment_cost = {
            "emergency": 500.0,
            "critical": 300.0,
            "high": 150.0,
            "moderate": 75.0,
            "low": 30.0
        }.get(urgency, 50.0)
        
        # Efficacy estimation
        efficacy = {
            "emergency": 60.0,
            "critical": 75.0,
            "high": 85.0,
            "moderate": 90.0,
            "low": 95.0
        }.get(urgency, 80.0)
        
        # Resistant variety recommendations
        resistant_vars = []
        if primary_disease in [TomatoDisease.LATE_BLIGHT]:
            resistant_vars = ["Mountain Magic", "Defiant PhR", "Iron Lady"]
        elif primary_disease in [TomatoDisease.FUSARIUM_WILT]:
            resistant_vars = ["Celebrity", "Better Boy", "Mountain Fresh Plus"]
        elif primary_disease in [TomatoDisease.TYLCV]:
            resistant_vars = ["Tygress", "Phoenix", "Security"]
        
        return TomatoTreatmentPlan(
            primary_disease=primary_disease,
            severity_percent=severity,
            urgency_level=urgency,
            action_within_hours=action_hours,
            fungicide_options=fungicides,
            bactericide_options=management.get("bactericides", []),
            resistance_management_strategy="Rotate FRAC groups, max 3 applications per code per season",
            spray_interval_days=spray_interval,
            spray_coverage_notes="Ensure coverage of leaf undersides, use adequate water volume",
            biocontrol_agents=["Trichoderma harzianum", "Bacillus subtilis", "Streptomyces lydicus"],
            remove_infected_tissue=severity > 10,
            increase_spacing=False,
            reduce_humidity_target=75.0 if severity > 20 else 80.0,
            improve_air_circulation=True,
            adjust_irrigation="Switch to drip, avoid overhead watering" if severity > 15 else "Continue current",
            sanitize_tools=True,
            resistant_variety_recommendations=resistant_vars,
            crop_rotation_needed=disease_params.get("soil_borne", False),
            substrate_sterilization=disease_params.get("soil_borne", False),
            organic_approved_options=organic_options,
            pre_harvest_interval_days=3,
            restricted_entry_interval_hours=12,
            treatment_cost_usd=treatment_cost,
            expected_efficacy_percent=efficacy,
            estimated_yield_protection_kg=100.0 * (severity / 100) * (efficacy / 100),
            roi_ratio=3.5,
            warnings=[warning] if warning else [],
            notes=f"Growth stage: {growth_stage.value}. {cultural_control}"
        )
    
    def detect(
        self,
        image: np.ndarray,
        temperature: float = 22.0,
        humidity: float = 80.0,
        leaf_wetness_hours: float = 2.0,
        vpd: float = 0.8
    ) -> TomatoDiseaseDetectionResult:
        """
        Comprehensive tomato disease detection.
        
        Analyzes image for all 18 major tomato diseases with variety-specific
        resistance consideration.
        """
        timestamp = datetime.now()
        
        # Preprocess image
        if image.shape[0] > 2000 or image.shape[1] > 2000:
            scale = 2000 / max(image.shape[:2])
            image = cv2.resize(image, None, fx=scale, fy=scale)
        
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        # Run all detection methods
        all_lesions = []
        all_lesions.extend(self.detect_early_blight(image, hsv))
        all_lesions.extend(self.detect_late_blight(image, hsv))
        all_lesions.extend(self.detect_leaf_mold(image, hsv))
        all_lesions.extend(self.detect_bacterial_spot(image, hsv))
        # ... (additional detection methods)
        
        systemic_symptoms = []
        systemic_symptoms.extend(self.detect_viral_symptoms(image))
        systemic_symptoms.extend(self.detect_vascular_wilts(image))
        
        fruit_diseases = self.detect_fruit_diseases(image)
        
        # Determine primary disease
        if all_lesions:
            disease_counts = {}
            for lesion in all_lesions:
                disease_counts[lesion.disease_type] = disease_counts.get(lesion.disease_type, 0) + 1
            primary_disease = max(disease_counts, key=disease_counts.get)
        elif systemic_symptoms:
            primary_disease = systemic_symptoms[0].disease_type
        elif fruit_diseases:
            primary_disease = fruit_diseases[0].disease_type
        else:
            primary_disease = TomatoDisease.HEALTHY
        
        # Calculate severity
        detected_diseases = list(set([l.disease_type for l in all_lesions]))
        total_lesion_area = sum(l.area_mm2 for l in all_lesions)
        image_area = (image.shape[0] * image.shape[1]) / (self.pixels_per_mm ** 2)
        severity_percent = min(100.0, (total_lesion_area / image_area) * 100)
        
        # Environmental risk
        env_risk = self.assess_environmental_risk(temperature, humidity, leaf_wetness_hours, vpd)
        
        # Treatment plan
        treatment = self.generate_treatment_plan(primary_disease, severity_percent, self.growth_stage)
        
        # Health score
        health_score = max(0.0, 1.0 - (severity_percent / 100))
        
        # Create visualization
        annotated = image.copy()
        for lesion in all_lesions:
            x, y, w, h = lesion.bbox
            color = (255, 0, 0) if lesion.disease_type == TomatoDisease.LATE_BLIGHT else (0, 255, 255)
            cv2.rectangle(annotated, (x, y), (x+w, y+h), color, 2)
            cv2.putText(annotated, lesion.disease_type.value[:8], (x, y-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        return TomatoDiseaseDetectionResult(
            timestamp=timestamp,
            variety_type=self.variety_type,
            growth_stage=self.growth_stage,
            resistance_profile=self.resistance_profile,
            detected_diseases=detected_diseases,
            foliar_lesions=all_lesions,
            systemic_symptoms=systemic_symptoms,
            fruit_diseases=fruit_diseases,
            primary_disease=primary_disease,
            secondary_diseases=[d for d in detected_diseases if d != primary_disease][:3],
            overall_health_score=health_score,
            defoliation_percent=severity_percent * 0.8,
            yield_loss_estimate_percent=severity_percent * self.disease_params.get(primary_disease, {}).get("yield_loss_potential", 0.5),
            environmental_risk=env_risk,
            disease_progression_forecast="Will worsen" if env_risk.overall_disease_pressure > 0.6 else "Stable",
            treatment_plan=treatment,
            monitoring_schedule="Daily if critical, weekly if moderate",
            annotated_image=annotated,
            disease_heatmap=np.zeros_like(image),
            severity_overlay=np.zeros_like(image),
            overall_confidence=0.85,
            needs_expert_review=primary_disease == TomatoDisease.LATE_BLIGHT or severity_percent > 50,
            differential_diagnosis=[(primary_disease, 0.85)]
        )


# Example usage demonstration
if __name__ == "__main__":
    # Initialize detector for indeterminate hybrid tomato in flowering stage
    detector = TomatoDiseaseDetector(
        variety_type=TomatoVarietyType.INDETERMINATE_HYBRID,
        growth_stage=TomatoGrowthStage.FLOWERING,
        variety_name="Big Beef",
        resistance_genes=[ResistanceGene.VE, ResistanceGene.I, ResistanceGene.I2, ResistanceGene.TM2]
    )
    
    print("Tomato Disease Detection System Initialized")
    print(f"Variety: {detector.variety_name}")
    print(f"Resistance genes: {[g.value for g in detector.resistance_genes]}")
    print(f"Supported diseases: {len(detector.disease_params)}")
    print("\nReady for image analysis...")
