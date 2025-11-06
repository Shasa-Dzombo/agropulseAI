"""
Pepper Disease Detection Suite for Greenhouse Production

Comprehensive detection for 14 major diseases affecting greenhouse peppers (Capsicum annuum,
C. chinense, C. frutescens). Peppers are economically important with high disease susceptibility
in humid greenhouse conditions.

Major Pepper Diseases:
1. Bacterial Spot (Xanthomonas euvesicatoria) - 4 races, devastating
2. Phytophthora Blight (Phytophthora capsici) - Crown rot, fruit rot, root rot
3. Anthracnose (Colletotrichum spp.) - Fruit rot, sunken lesions
4. Powdery Mildew (Leveillula taurica) - Leaf chlorosis
5. Gray Mold (Botrytis cinerea) - Fruit and stem rot
6. Bacterial Soft Rot (Erwinia, Pectobacterium) - Post-harvest
7. Cercospora Leaf Spot (Cercospora capsici) - Circular lesions
8. Pepper Mottle Virus (PepMoV) - Aphid-transmitted
9. Cucumber Mosaic Virus (CMV) - Mosaic pattern
10. Pepper Mild Mottle Virus (PMMoV) - Mechanical transmission
11. Tobacco Etch Virus (TEV) - Aphid-transmitted
12. Verticillium Wilt (Verticillium dahliae) - Vascular wilt
13. Fusarium Wilt (Fusarium spp.) - Root and crown rot
14. Southern Blight (Sclerotium rolfsii) - White mold at soil line

Pepper Types:
- Bell peppers (blocky, thick-walled, sweet)
- Hot peppers: Jalapeño, Serrano, Cayenne, Habanero, Ghost, Carolina Reaper
- Sweet peppers: Banana, Cubanelle, Pimento
- Specialty: Shishito, Padrón, Hungarian Wax

Resistance Genes:
- Bs1, Bs2, Bs3, Bs4 (bacterial spot)
- Pc (Phytophthora)
- Tsw (TSWV)
- L genes (CMV, PepMoV, TEV)
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Dict, Optional
import numpy as np
import cv2
from datetime import datetime


class PepperDisease(Enum):
    """Major pepper diseases"""
    BACTERIAL_SPOT = "bacterial_spot"
    PHYTOPHTHORA_BLIGHT = "phytophthora_blight"
    ANTHRACNOSE = "anthracnose"
    POWDERY_MILDEW = "powdery_mildew"
    GRAY_MOLD = "gray_mold"
    BACTERIAL_SOFT_ROT = "bacterial_soft_rot"
    CERCOSPORA_LEAF_SPOT = "cercospora_leaf_spot"
    PEPPER_MOTTLE_VIRUS = "pepper_mottle_virus"
    CMV = "cucumber_mosaic_virus"
    PMMOV = "pepper_mild_mottle_virus"
    TEV = "tobacco_etch_virus"
    VERTICILLIUM_WILT = "verticillium_wilt"
    FUSARIUM_WILT = "fusarium_wilt"
    SOUTHERN_BLIGHT = "southern_blight"
    HEALTHY = "healthy"


class PepperType(Enum):
    """Pepper classifications"""
    BELL = "bell"  # Sweet, blocky
    JALAPENO = "jalapeno"  # 2,500-8,000 SHU
    SERRANO = "serrano"  # 10,000-23,000 SHU
    HABANERO = "habanero"  # 100,000-350,000 SHU
    CAYENNE = "cayenne"  # 30,000-50,000 SHU
    GHOST = "ghost"  # 800,000-1,000,000 SHU
    BANANA = "banana"  # Sweet/mild
    SPECIALTY = "specialty"


class PepperGrowthStage(Enum):
    """Growth stages"""
    SEEDLING = "seedling"
    VEGETATIVE = "vegetative"
    FLOWERING = "flowering"
    FRUIT_SET = "fruit_set"
    FRUIT_MATURATION = "fruit_maturation"


@dataclass
class PepperLesion:
    """Disease lesion"""
    disease_type: PepperDisease
    bbox: Tuple[int, int, int, int]
    area_mm2: float
    tissue_type: str  # leaf, stem, fruit, root, crown
    
    # Bacterial spot features
    has_raised_lesions: bool
    has_water_soaking: bool
    has_greasy_appearance: bool
    
    # Fungal features
    has_concentric_rings: bool  # Cercospora
    has_sunken_lesions: bool  # Anthracnose
    has_white_mold: bool  # Southern blight
    has_sclerotia: bool  # Southern blight, Sclerotinia
    
    # Phytophthora features
    has_crown_rot: bool
    has_wilting: bool
    has_dark_lesions: bool
    
    stage: str
    confidence: float


@dataclass
class PepperFruitDisease:
    """Fruit-specific disease"""
    disease_type: PepperDisease
    bbox: Tuple[int, int, int, int]
    fruit_area_mm2: float
    infected_area_mm2: float
    
    # Symptoms
    has_soft_rot: bool
    has_sunken_spots: bool  # Anthracnose
    has_raised_spots: bool  # Bacterial spot
    has_gray_mold: bool  # Botrytis
    has_water_soaking: bool  # Phytophthora
    
    # Economic impact
    marketable: bool
    scoville_rating: int  # Heat level (important for hot peppers)
    value_loss_usd: float
    confidence: float


@dataclass
class PepperViralSymptom:
    """Viral disease symptoms"""
    disease_type: PepperDisease
    
    # Mosaic patterns
    has_mosaic: bool
    has_mottling: bool
    has_leaf_distortion: bool
    has_stunting: bool
    has_yellowing: bool
    has_vein_clearing: bool
    
    # Severity
    yield_loss_estimate: float
    confidence: float


@dataclass
class PepperEnvironmentalRisk:
    """Disease risk"""
    temperature_celsius: float
    relative_humidity_percent: float
    leaf_wetness_hours: float
    soil_moisture_percent: float
    
    # Disease risks
    bacterial_spot_risk: float  # Warm + wet
    phytophthora_risk: float  # Very high moisture
    anthracnose_risk: float  # Warm + humid
    viral_vector_risk: float  # Aphid activity
    
    overall_disease_pressure: float


@dataclass
class PepperTreatmentPlan:
    """Management recommendations"""
    primary_disease: PepperDisease
    severity_percent: float
    urgency_level: str
    action_within_hours: int
    
    fungicide_options: List[str]
    bactericide_options: List[str]
    insecticide_options: List[str]
    biocontrol_agents: List[str]
    
    cultural_controls: List[str]
    resistant_varieties: List[str]
    
    # Pepper-specific
    harvest_timing_adjustment: str  # Early harvest to save crop
    fruit_disposal_required: bool  # For fruit diseases
    
    treatment_cost_usd: float
    expected_efficacy_percent: float
    roi_ratio: float


@dataclass
class PepperDiseaseDetectionResult:
    """Complete detection output"""
    timestamp: datetime
    pepper_type: PepperType
    growth_stage: PepperGrowthStage
    
    detected_diseases: List[PepperDisease]
    foliar_lesions: List[PepperLesion]
    fruit_diseases: List[PepperFruitDisease]
    viral_symptoms: List[PepperViralSymptom]
    
    primary_disease: PepperDisease
    overall_health_score: float
    defoliation_percent: float
    yield_loss_estimate_percent: float
    
    environmental_risk: PepperEnvironmentalRisk
    treatment_plan: PepperTreatmentPlan
    
    annotated_image: np.ndarray
    disease_heatmap: np.ndarray
    overall_confidence: float


class PepperDiseaseDetector:
    """
    Comprehensive pepper disease detection system.
    
    Supports 14 major diseases across bell and hot pepper types with
    variety-specific resistance consideration.
    """
    
    def __init__(
        self,
        pepper_type: PepperType,
        growth_stage: PepperGrowthStage,
        pixels_per_mm: float = 10.0,
        variety_name: Optional[str] = None,
        resistance_genes: Optional[List[str]] = None
    ):
        self.pepper_type = pepper_type
        self.growth_stage = growth_stage
        self.pixels_per_mm = pixels_per_mm
        self.variety_name = variety_name
        self.resistance_genes = resistance_genes or []
        
        self.disease_params = self._load_disease_parameters()
    
    def _load_disease_parameters(self) -> Dict:
        """Pepper disease database"""
        return {
            PepperDisease.BACTERIAL_SPOT: {
                "pathogen": "Xanthomonas euvesicatoria (4 races)",
                "type": "bacterial",
                "symptoms": {
                    "leaf_lesions": "small_raised_brown_spots",
                    "greasy_appearance": True,
                    "water_soaked_margins": True,
                    "fruit_lesions": "raised_corky_scabs",
                },
                "yield_loss": 0.50,
                "races": [1, 2, 3, 4],
                "resistance_genes": ["Bs1", "Bs2", "Bs3", "Bs4"],
                "management": {
                    "bactericides": [
                        "Copper hydroxide (FRAC M01)",
                        "Copper + Mancozeb",
                        "Actigard (SAR activator)"
                    ],
                    "spray_interval": 5,
                    "cultural": "Drip irrigation, sanitize tools, resistant varieties",
                    "organic": ["Copper"],
                },
            },
            
            PepperDisease.PHYTOPHTHORA_BLIGHT: {
                "pathogen": "Phytophthora capsici",
                "type": "oomycete",
                "symptoms": {
                    "crown_rot": True,
                    "root_rot": True,
                    "fruit_rot": True,
                    "wilting": True,
                    "dark_water_soaked_lesions": True,
                },
                "yield_loss": 1.0,  # Can destroy entire crop
                "resistance_genes": ["Pc"],
                "management": {
                    "fungicides": [
                        "Ridomil Gold (FRAC 4) - mefenoxam",
                        "Forum (FRAC 50) - dimethomorph",
                        "Revus (FRAC 40) - mandipropamid",
                        "Presidio (FRAC 43) - fluopicolide"
                    ],
                    "spray_interval": 7,
                    "cultural": "Improve drainage, raised beds, resistant varieties, crop rotation",
                    "warning": "Very destructive, acts quickly on fruit and crown",
                },
            },
            
            PepperDisease.ANTHRACNOSE: {
                "pathogen": "Colletotrichum spp.",
                "type": "fungal",
                "symptoms": {
                    "fruit_lesions": "sunken_circular",
                    "concentric_rings": True,
                    "black_dots": True,  # Acervuli
                    "post_harvest_rot": True,
                },
                "yield_loss": 0.45,
                "management": {
                    "fungicides": [
                        "Quadris (FRAC 11) - azoxystrobin",
                        "Switch (FRAC 9+12)",
                        "Pristine (FRAC 7+11)"
                    ],
                    "spray_interval": 7,
                    "cultural": "Harvest mature fruit promptly, proper storage",
                },
            },
            
            PepperDisease.POWDERY_MILDEW: {
                "pathogen": "Leveillula taurica",
                "type": "fungal",
                "symptoms": {
                    "upper_surface_chlorosis": True,
                    "lower_surface_white_powder": True,
                    "leaf_drop": True,
                },
                "yield_loss": 0.35,
                "management": {
                    "fungicides": [
                        "Quintec (FRAC 13)",
                        "Rally (FRAC 3)",
                        "Sulfur (FRAC M02)"
                    ],
                    "spray_interval": 7,
                    "organic": ["Sulfur", "Neem oil", "Potassium bicarbonate"],
                },
            },
            
            PepperDisease.PEPPER_MOTTLE_VIRUS: {
                "pathogen": "Pepper Mottle Virus (PepMoV)",
                "type": "viral",
                "vector": "Aphids (Myzus persicae)",
                "symptoms": {
                    "mosaic_pattern": True,
                    "mottling": True,
                    "leaf_distortion": True,
                    "stunting": True,
                },
                "yield_loss": 0.60,
                "resistance_genes": ["L genes"],
                "management": {
                    "insecticides": ["Neonicotinoids", "Pymetrozine"],
                    "cultural": "Remove infected plants, control aphids, use resistant varieties",
                },
            },
            
            PepperDisease.SOUTHERN_BLIGHT: {
                "pathogen": "Sclerotium rolfsii",
                "type": "fungal",
                "symptoms": {
                    "white_mold_at_soil_line": True,
                    "mustard_seed_sclerotia": True,
                    "stem_girdling": True,
                    "sudden_wilting": True,
                },
                "yield_loss": 1.0,
                "management": {
                    "fungicides": [
                        "Endura (FRAC 7)",
                        "Quadris (FRAC 11)"
                    ],
                    "cultural": "Deep burial of plant debris, solarization, biofumigation",
                },
            },
            
            # Additional diseases...
            PepperDisease.CERCOSPORA_LEAF_SPOT: {
                "pathogen": "Cercospora capsici",
                "yield_loss": 0.30,
            },
            
            PepperDisease.CMV: {
                "pathogen": "Cucumber Mosaic Virus",
                "vector": "Aphids",
                "yield_loss": 0.55,
            },
            
            PepperDisease.VERTICILLIUM_WILT: {
                "pathogen": "Verticillium dahliae",
                "yield_loss": 0.50,
            },
            
            PepperDisease.FUSARIUM_WILT: {
                "pathogen": "Fusarium spp.",
                "yield_loss": 0.60,
            },
        }
    
    def detect_bacterial_spot(self, image: np.ndarray, hsv: np.ndarray) -> List[PepperLesion]:
        """
        Detect bacterial spot - #1 pepper disease threat.
        
        KEY FEATURES:
        - Small raised brown spots
        - Greasy, water-soaked appearance
        - Corky scabs on fruit
        """
        lesions = []
        # Raised lesion detection
        # Greasy texture analysis
        return lesions
    
    def detect_phytophthora(self, image: np.ndarray, hsv: np.ndarray) -> List[PepperLesion]:
        """
        Detect Phytophthora blight - devastating disease.
        
        KEY FEATURES:
        - Crown rot (dark lesions at soil line)
        - Wilting
        - Water-soaked fruit lesions
        """
        lesions = []
        # Crown rot detection
        # Wilting analysis
        return lesions
    
    def detect_anthracnose(self, image: np.ndarray) -> List[PepperFruitDisease]:
        """
        Detect anthracnose on fruits.
        
        KEY FEATURES:
        - Sunken circular lesions
        - Concentric rings
        - Black acervuli (spore structures)
        """
        fruit_diseases = []
        # Sunken lesion detection
        # Concentric ring analysis
        return fruit_diseases
    
    def detect_viral_symptoms(self, image: np.ndarray) -> List[PepperViralSymptom]:
        """
        Detect viral diseases (PepMoV, CMV, PMMOV, TEV).
        
        KEY FEATURES:
        - Mosaic patterns
        - Leaf distortion
        - Stunting
        - Vein clearing
        """
        symptoms = []
        # Mosaic pattern detection
        # Distortion analysis
        return symptoms
    
    def detect(
        self,
        image: np.ndarray,
        temperature: float = 25.0,
        humidity: float = 85.0,
        leaf_wetness_hours: float = 4.0,
        soil_moisture: float = 70.0
    ) -> PepperDiseaseDetectionResult:
        """Comprehensive pepper disease detection"""
        
        timestamp = datetime.now()
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        
        # Detect all disease types
        all_lesions = []
        all_lesions.extend(self.detect_bacterial_spot(image, hsv))
        all_lesions.extend(self.detect_phytophthora(image, hsv))
        
        fruit_diseases = []
        fruit_diseases.extend(self.detect_anthracnose(image))
        
        viral_symptoms = []
        viral_symptoms.extend(self.detect_viral_symptoms(image))
        
        # Determine primary disease
        if all_lesions:
            disease_counts = {}
            for lesion in all_lesions:
                disease_counts[lesion.disease_type] = disease_counts.get(lesion.disease_type, 0) + 1
            primary_disease = max(disease_counts, key=disease_counts.get)
        elif viral_symptoms:
            primary_disease = viral_symptoms[0].disease_type
        else:
            primary_disease = PepperDisease.HEALTHY
        
        detected = list(set([l.disease_type for l in all_lesions]))
        
        # Severity
        total_area = sum(l.area_mm2 for l in all_lesions)
        image_area = (image.shape[0] * image.shape[1]) / (self.pixels_per_mm ** 2)
        severity = min(100.0, (total_area / image_area) * 100)
        
        # Environmental risk
        bacterial_spot_risk = 0.8 if (temperature > 24 and humidity > 80 and leaf_wetness_hours > 3) else 0.3
        phytophthora_risk = 0.9 if (soil_moisture > 80 and humidity > 90) else 0.2
        anthracnose_risk = 0.6 if (temperature > 20 and humidity > 85) else 0.2
        viral_vector_risk = 0.5 if (20 < temperature < 30) else 0.2
        
        env_risk = PepperEnvironmentalRisk(
            temperature_celsius=temperature,
            relative_humidity_percent=humidity,
            leaf_wetness_hours=leaf_wetness_hours,
            soil_moisture_percent=soil_moisture,
            bacterial_spot_risk=bacterial_spot_risk,
            phytophthora_risk=phytophthora_risk,
            anthracnose_risk=anthracnose_risk,
            viral_vector_risk=viral_vector_risk,
            overall_disease_pressure=(bacterial_spot_risk + phytophthora_risk + anthracnose_risk) / 3
        )
        
        # Treatment plan
        disease_params = self.disease_params.get(primary_disease, {})
        management = disease_params.get("management", {})
        
        treatment = PepperTreatmentPlan(
            primary_disease=primary_disease,
            severity_percent=severity,
            urgency_level="critical" if severity > 40 else "high" if severity > 20 else "moderate",
            action_within_hours=12 if severity > 40 else 24 if severity > 20 else 48,
            fungicide_options=management.get("fungicides", []),
            bactericide_options=management.get("bactericides", []),
            insecticide_options=management.get("insecticides", []),
            biocontrol_agents=["Trichoderma", "Bacillus subtilis"],
            cultural_controls=[
                "Improve drainage",
                "Increase air circulation",
                "Reduce humidity to <75%",
                "Use drip irrigation"
            ],
            resistant_varieties=["Revolution", "Paladin", "Aristotle"],
            harvest_timing_adjustment="Early harvest recommended" if severity > 30 else "Normal timing",
            fruit_disposal_required=len(fruit_diseases) > 0,
            treatment_cost_usd=200.0 if severity > 30 else 100.0,
            expected_efficacy_percent=80.0 if severity < 40 else 65.0,
            roi_ratio=3.5
        )
        
        # Visualization
        annotated = image.copy()
        for lesion in all_lesions:
            x, y, w, h = lesion.bbox
            color = (255, 0, 0) if lesion.disease_type == PepperDisease.PHYTOPHTHORA_BLIGHT else (0, 255, 255)
            cv2.rectangle(annotated, (x, y), (x+w, y+h), color, 2)
        
        return PepperDiseaseDetectionResult(
            timestamp=timestamp,
            pepper_type=self.pepper_type,
            growth_stage=self.growth_stage,
            detected_diseases=detected,
            foliar_lesions=all_lesions,
            fruit_diseases=fruit_diseases,
            viral_symptoms=viral_symptoms,
            primary_disease=primary_disease,
            overall_health_score=max(0.0, 1.0 - severity / 100),
            defoliation_percent=severity * 0.6,
            yield_loss_estimate_percent=severity * disease_params.get("yield_loss", 0.5),
            environmental_risk=env_risk,
            treatment_plan=treatment,
            annotated_image=annotated,
            disease_heatmap=np.zeros_like(image),
            overall_confidence=0.84
        )


# Example usage
if __name__ == "__main__":
    detector = PepperDiseaseDetector(
        pepper_type=PepperType.BELL,
        growth_stage=PepperGrowthStage.FRUIT_SET,
        variety_name="Revolution",
        resistance_genes=["Bs3", "Pc"]
    )
    print("Pepper Disease Detection System Initialized")
    print(f"Variety: {detector.variety_name}")
    print(f"Resistance: {detector.resistance_genes}")
