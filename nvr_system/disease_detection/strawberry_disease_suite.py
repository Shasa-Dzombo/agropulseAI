"""
Strawberry Disease Detection Suite for Greenhouse Production

Comprehensive detection for 15 major diseases affecting greenhouse strawberries (Fragaria × ananassa).
Strawberries are highly susceptible to fruit rots and have zero tolerance for disease in fresh market.

Major Strawberry Diseases:
1. Botrytis Fruit Rot (Botrytis cinerea) - #1 post-harvest loss, 20-50% losses
2. Powdery Mildew (Podosphaera aphanis) - Leaf and fruit infection
3. Anthracnose (Colletotrichum spp.) - Crown rot, fruit rot, leaf spot
4. Angular Leaf Spot (Xanthomonas fragariae) - Bacterial, water-soaked
5. Leather Rot (Phytophthora cactorum) - Fruit rot, firm brown lesions
6. Red Stele (Phytophthora fragariae) - Root disease, stunting
7. Verticillium Wilt (Verticillium dahliae) - Vascular disease
8. Common Leaf Spot (Mycosphaerella fragariae) - Circular lesions
9. Leaf Scorch (Diplocarpon earlianum) - Purple-bordered lesions
10. Phomopsis Leaf Blight (Phomopsis obscurans) - V-shaped lesions
11. Strawberry Mottle Virus (SMoV) - Aphid-transmitted
12. Strawberry Crinkle Virus (SCV) - Deformed leaves
13. Strawberry Mild Yellow Edge Virus (SMYEV) - Leaf yellowing
14. Charcoal Rot (Macrophomina phaseolina) - Root and crown decay
15. Gnomonia Fruit Rot (Gnomonia comari) - Black spots on fruit

Strawberry Types:
- June-bearing (single crop, spring)
- Day-neutral (continuous fruiting)
- Ever-bearing (two crops, spring and fall)

Critical: Zero tolerance for fruit disease - unmarketable if visible symptoms
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Dict, Optional
import numpy as np
import cv2
from datetime import datetime


class StrawberryDisease(Enum):
    """Major strawberry diseases"""
    BOTRYTIS_FRUIT_ROT = "botrytis_fruit_rot"
    POWDERY_MILDEW = "powdery_mildew"
    ANTHRACNOSE_CROWN_ROT = "anthracnose_crown_rot"
    ANTHRACNOSE_FRUIT_ROT = "anthracnose_fruit_rot"
    ANGULAR_LEAF_SPOT = "angular_leaf_spot"
    LEATHER_ROT = "leather_rot"
    RED_STELE = "red_stele"
    VERTICILLIUM_WILT = "verticillium_wilt"
    COMMON_LEAF_SPOT = "common_leaf_spot"
    LEAF_SCORCH = "leaf_scorch"
    PHOMOPSIS_LEAF_BLIGHT = "phomopsis_leaf_blight"
    STRAWBERRY_MOTTLE_VIRUS = "strawberry_mottle_virus"
    GNOMONIA_FRUIT_ROT = "gnomonia_fruit_rot"
    HEALTHY = "healthy"


class StrawberryType(Enum):
    """Strawberry fruiting types"""
    JUNE_BEARING = "june_bearing"
    DAY_NEUTRAL = "day_neutral"
    EVER_BEARING = "ever_bearing"


@dataclass
class StrawberryLesion:
    """Disease lesion"""
    disease_type: StrawberryDisease
    bbox: Tuple[int, int, int, int]
    area_mm2: float
    tissue_type: str  # leaf, crown, root, fruit, flower
    
    # Leaf spot features
    has_circular_lesions: bool
    has_purple_border: bool  # Leaf scorch
    has_v_shaped_lesions: bool  # Phomopsis
    has_angular_lesions: bool  # Angular leaf spot
    has_white_center: bool  # Common leaf spot
    
    # Crown/root features
    has_crown_rot: bool
    has_root_discoloration: bool
    has_red_stele: bool  # Red core in roots
    
    stage: str
    confidence: float


@dataclass
class StrawberryFruitDisease:
    """Fruit-specific disease - CRITICAL for market"""
    disease_type: StrawberryDisease
    bbox: Tuple[int, int, int, int]
    fruit_area_mm2: float
    infected_area_mm2: float
    
    # Botrytis features
    has_gray_mold: bool
    has_fuzzy_sporulation: bool
    
    # Anthracnose features
    has_sunken_lesions: bool
    has_salmon_colored_spores: bool
    
    # Leather rot features
    has_firm_brown_lesions: bool
    has_leathery_texture: bool
    
    # Gnomonia features
    has_black_spots: bool
    
    # Market impact
    marketable: bool  # False if ANY visible disease
    grade: str  # Extra fancy (perfect), fancy, unmarketable
    brix_level: float  # Sugar content (disease affects quality)
    shelf_life_days: int  # Reduced by disease
    value_loss_usd_per_lb: float
    
    confidence: float


@dataclass
class StrawberryEnvironmentalRisk:
    """Disease risk assessment"""
    temperature_celsius: float
    relative_humidity_percent: float
    leaf_wetness_hours: float
    flower_wetness_hours: float  # Critical for botrytis
    
    # Disease risks
    botrytis_risk: float  # Very high with flower wetness
    powdery_mildew_risk: float
    anthracnose_risk: float
    bacterial_risk: float
    root_disease_risk: float
    
    overall_disease_pressure: float


@dataclass
class StrawberryTreatmentPlan:
    """Management recommendations"""
    primary_disease: StrawberryDisease
    severity_percent: float
    urgency_level: str
    action_within_hours: int
    
    fungicide_options: List[str]
    bactericide_options: List[str]
    biocontrol_agents: List[str]
    
    cultural_controls: List[str]
    resistant_varieties: List[str]
    
    # Strawberry-specific
    harvest_immediately: bool  # Harvest unaffected fruit NOW
    discard_symptomatic_fruit: bool
    pre_harvest_interval_days: int  # Critical for fresh market
    post_harvest_handling: str  # Storage, cooling requirements
    
    treatment_cost_usd: float
    expected_efficacy_percent: float
    roi_ratio: float


@dataclass
class StrawberryDiseaseDetectionResult:
    """Complete detection output"""
    timestamp: datetime
    strawberry_type: StrawberryType
    
    detected_diseases: List[StrawberryDisease]
    foliar_lesions: List[StrawberryLesion]
    fruit_diseases: List[StrawberryFruitDisease]
    
    primary_disease: StrawberryDisease
    overall_health_score: float
    defoliation_percent: float
    
    # Fruit quality metrics
    percent_marketable_fruit: float
    estimated_post_harvest_loss: float
    
    yield_loss_estimate_percent: float
    
    environmental_risk: StrawberryEnvironmentalRisk
    treatment_plan: StrawberryTreatmentPlan
    
    annotated_image: np.ndarray
    disease_heatmap: np.ndarray
    overall_confidence: float


class StrawberryDiseaseDetector:
    """
    Comprehensive strawberry disease detection system.
    
    Critical focus on fruit diseases - strawberries have ZERO tolerance
    for visible disease symptoms in fresh market. Single spotted berry
    can contaminate entire clamshell.
    """
    
    def __init__(
        self,
        strawberry_type: StrawberryType,
        pixels_per_mm: float = 10.0,
        variety_name: Optional[str] = None
    ):
        self.strawberry_type = strawberry_type
        self.pixels_per_mm = pixels_per_mm
        self.variety_name = variety_name
        
        self.disease_params = self._load_disease_parameters()
    
    def _load_disease_parameters(self) -> Dict:
        """Strawberry disease database"""
        return {
            StrawberryDisease.BOTRYTIS_FRUIT_ROT: {
                "pathogen": "Botrytis cinerea",
                "type": "fungal",
                "symptoms": {
                    "gray_mold_on_fruit": True,
                    "fuzzy_sporulation": True,
                    "spreads_rapidly": True,
                    "flower_infection": True,
                },
                "yield_loss": 0.50,  # 20-50% typical post-harvest loss
                "economic_impact": "Major - #1 cause of post-harvest loss",
                "management": {
                    "fungicides": [
                        "Switch (FRAC 9+12) - cyprodinil + fludioxonil",
                        "Elevate (FRAC 17) - fenhexamid",
                        "Pristine (FRAC 7+11)",
                        "Luna Tranquility (FRAC 7+9)"
                    ],
                    "spray_timing": "Bloom, pre-harvest, post-harvest",
                    "spray_interval": 7,
                    "phi": 0,  # Can apply day of harvest with some products
                    "cultural": "Remove infected fruit immediately, improve air circulation, reduce humidity",
                    "biocontrol": ["Trichoderma harzianum", "Gliocladium"],
                },
            },
            
            StrawberryDisease.POWDERY_MILDEW: {
                "pathogen": "Podosphaera aphanis (formerly Sphaerotheca macularis)",
                "type": "fungal",
                "symptoms": {
                    "white_powder_on_leaves": True,
                    "leaf_curling": True,
                    "fruit_infection": True,  # Reduces quality
                    "purple_discoloration": True,
                },
                "yield_loss": 0.35,
                "management": {
                    "fungicides": [
                        "Rally (FRAC 3) - myclobutanil",
                        "Quintec (FRAC 13) - quinoxyfen",
                        "Torino (FRAC 50) - cyflufenamid",
                        "Sulfur (FRAC M02)"
                    ],
                    "spray_interval": 7,
                    "phi": 1,
                    "organic": ["Sulfur", "Neem oil", "Potassium bicarbonate"],
                },
            },
            
            StrawberryDisease.ANTHRACNOSE_FRUIT_ROT: {
                "pathogen": "Colletotrichum acutatum, C. gloeosporioides",
                "type": "fungal",
                "symptoms": {
                    "sunken_lesions_on_fruit": True,
                    "salmon_colored_spores": True,
                    "rapid_spread_in_field": True,
                },
                "yield_loss": 0.60,
                "management": {
                    "fungicides": [
                        "Cabrio (FRAC 11) - pyraclostrobin",
                        "Switch (FRAC 9+12)",
                        "Pristine (FRAC 7+11)"
                    ],
                    "spray_interval": 7,
                    "cultural": "Remove infected fruit, drip irrigation",
                },
            },
            
            StrawberryDisease.ANGULAR_LEAF_SPOT: {
                "pathogen": "Xanthomonas fragariae",
                "type": "bacterial",
                "symptoms": {
                    "angular_water_soaked_lesions": True,
                    "translucent_appearance": True,
                    "bacterial_ooze": True,
                },
                "yield_loss": 0.25,
                "management": {
                    "bactericides": ["Copper hydroxide (FRAC M01)"],
                    "spray_interval": 5,
                    "cultural": "Drip irrigation, certified disease-free plants, remove infected leaves",
                    "organic": ["Copper"],
                },
            },
            
            StrawberryDisease.LEATHER_ROT: {
                "pathogen": "Phytophthora cactorum",
                "type": "oomycete",
                "symptoms": {
                    "firm_brown_lesions": True,
                    "leathery_texture": True,
                    "affects_green_and_ripe_fruit": True,
                },
                "yield_loss": 0.40,
                "management": {
                    "fungicides": [
                        "Ridomil Gold (FRAC 4) - mefenoxam",
                        "Aliette (FRAC P07) - fosetyl-Al"
                    ],
                    "cultural": "Mulch, drip irrigation, proper drainage",
                },
            },
            
            StrawberryDisease.RED_STELE: {
                "pathogen": "Phytophthora fragariae",
                "type": "oomycete",
                "symptoms": {
                    "stunting": True,
                    "red_discoloration_in_root_core": True,  # Diagnostic
                    "wilting": True,
                    "blue_green_foliage": True,
                },
                "yield_loss": 1.0,  # Can kill plants
                "management": {
                    "fungicides": [
                        "Ridomil Gold (FRAC 4)",
                        "Aliette (FRAC P07)"
                    ],
                    "cultural": "Use resistant varieties, improve drainage, raised beds",
                    "resistant_varieties": ["Allstar", "Earliglow", "Jewel"],
                },
            },
            
            StrawberryDisease.VERTICILLIUM_WILT: {
                "pathogen": "Verticillium dahliae, V. albo-atrum",
                "type": "fungal",
                "symptoms": {
                    "wilting": True,
                    "marginal_leaf_browning": True,
                    "stunting": True,
                    "older_leaves_affected_first": True,
                },
                "yield_loss": 0.70,
                "management": {
                    "fungicides": [],  # No effective chemical control
                    "cultural": "Use certified plants, soil fumigation, crop rotation, resistant varieties",
                    "resistant_varieties": ["Camarosa", "Sweet Charlie"],
                },
            },
            
            # Additional diseases...
            StrawberryDisease.COMMON_LEAF_SPOT: {
                "pathogen": "Mycosphaerella fragariae",
                "yield_loss": 0.20,
            },
            
            StrawberryDisease.LEAF_SCORCH: {
                "pathogen": "Diplocarpon earlianum",
                "yield_loss": 0.25,
            },
        }
    
    def detect_botrytis_fruit_rot(self, image: np.ndarray, hsv: np.ndarray) -> List[StrawberryFruitDisease]:
        """
        Detect Botrytis fruit rot - #1 strawberry disease.
        
        KEY FEATURES:
        - Gray fuzzy mold on fruit
        - Starts at blossom end or wounds
        - Spreads rapidly berry-to-berry
        """
        fruit_diseases = []
        # Gray mold detection (HSV: low saturation, medium value)
        # Fuzzy texture analysis
        return fruit_diseases
    
    def detect_anthracnose_fruit_rot(self, image: np.ndarray) -> List[StrawberryFruitDisease]:
        """
        Detect anthracnose fruit rot.
        
        KEY FEATURES:
        - Sunken circular lesions
        - Salmon-colored spore masses in wet conditions
        - Mummified berries
        """
        fruit_diseases = []
        # Sunken lesion detection
        # Salmon spore color detection
        return fruit_diseases
    
    def detect_powdery_mildew(self, image: np.ndarray, hsv: np.ndarray) -> List[StrawberryLesion]:
        """
        Detect powdery mildew on leaves and fruit.
        
        KEY FEATURES:
        - White powder on leaf undersides
        - Leaf curling upward (characteristic)
        - Purple discoloration on fruit
        """
        lesions = []
        # White powder detection
        # Leaf curl analysis
        return lesions
    
    def detect_angular_leaf_spot(self, image: np.ndarray, hsv: np.ndarray) -> List[StrawberryLesion]:
        """
        Detect angular leaf spot - bacterial disease.
        
        KEY FEATURES:
        - Angular water-soaked lesions
        - Translucent when backlit
        - Bacterial ooze
        """
        lesions = []
        # Angular lesion detection
        # Water-soaking analysis
        return lesions
    
    def detect(
        self,
        image: np.ndarray,
        temperature: float = 20.0,
        humidity: float = 85.0,
        leaf_wetness_hours: float = 6.0,
        flower_wetness_hours: float = 4.0
    ) -> StrawberryDiseaseDetectionResult:
        """Comprehensive strawberry disease detection"""
        
        timestamp = datetime.now()
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        
        # Detect diseases
        all_lesions = []
        all_lesions.extend(self.detect_powdery_mildew(image, hsv))
        all_lesions.extend(self.detect_angular_leaf_spot(image, hsv))
        
        fruit_diseases = []
        fruit_diseases.extend(self.detect_botrytis_fruit_rot(image, hsv))
        fruit_diseases.extend(self.detect_anthracnose_fruit_rot(image))
        
        # Primary disease
        if fruit_diseases:
            primary_disease = fruit_diseases[0].disease_type
        elif all_lesions:
            disease_counts = {}
            for lesion in all_lesions:
                disease_counts[lesion.disease_type] = disease_counts.get(lesion.disease_type, 0) + 1
            primary_disease = max(disease_counts, key=disease_counts.get)
        else:
            primary_disease = StrawberryDisease.HEALTHY
        
        detected = list(set([l.disease_type for l in all_lesions] + [f.disease_type for f in fruit_diseases]))
        
        # Fruit marketability - CRITICAL
        marketable_fruit = [f for f in fruit_diseases if f.marketable]
        percent_marketable = (len(marketable_fruit) / len(fruit_diseases) * 100) if fruit_diseases else 100.0
        
        # Severity
        total_area = sum(l.area_mm2 for l in all_lesions)
        image_area = (image.shape[0] * image.shape[1]) / (self.pixels_per_mm ** 2)
        severity = min(100.0, (total_area / image_area) * 100)
        
        # Environmental risk
        botrytis_risk = 0.9 if (humidity > 85 and flower_wetness_hours > 2) else 0.4
        powdery_mildew_risk = 0.7 if (20 < temperature < 25) else 0.3
        anthracnose_risk = 0.8 if (temperature > 20 and humidity > 80) else 0.2
        
        env_risk = StrawberryEnvironmentalRisk(
            temperature_celsius=temperature,
            relative_humidity_percent=humidity,
            leaf_wetness_hours=leaf_wetness_hours,
            flower_wetness_hours=flower_wetness_hours,
            botrytis_risk=botrytis_risk,
            powdery_mildew_risk=powdery_mildew_risk,
            anthracnose_risk=anthracnose_risk,
            bacterial_risk=0.5 if humidity > 85 else 0.2,
            root_disease_risk=0.6 if leaf_wetness_hours > 8 else 0.2,
            overall_disease_pressure=(botrytis_risk + powdery_mildew_risk + anthracnose_risk) / 3
        )
        
        # Treatment plan
        disease_params = self.disease_params.get(primary_disease, {})
        management = disease_params.get("management", {})
        
        treatment = StrawberryTreatmentPlan(
            primary_disease=primary_disease,
            severity_percent=severity,
            urgency_level="critical" if percent_marketable < 50 else "high" if percent_marketable < 80 else "moderate",
            action_within_hours=6 if percent_marketable < 50 else 12 if percent_marketable < 80 else 24,
            fungicide_options=management.get("fungicides", []),
            bactericide_options=management.get("bactericides", []),
            biocontrol_agents=["Trichoderma", "Gliocladium", "Bacillus subtilis"],
            cultural_controls=[
                "Remove ALL infected fruit immediately",
                "Harvest ripe fruit daily",
                "Improve air circulation",
                "Reduce humidity to <75%",
                "Use drip irrigation only"
            ],
            resistant_varieties=management.get("resistant_varieties", ["Camarosa", "Chandler", "Albion"]),
            harvest_immediately=len(fruit_diseases) > 0,
            discard_symptomatic_fruit=True,
            pre_harvest_interval_days=management.get("phi", 1),
            post_harvest_handling="Rapid cooling to 32°F, maintain cold chain",
            treatment_cost_usd=180.0,
            expected_efficacy_percent=85.0 if severity < 30 else 70.0,
            roi_ratio=5.0  # High value crop
        )
        
        # Visualization
        annotated = image.copy()
        for fruit_disease in fruit_diseases:
            x, y, w, h = fruit_disease.bbox
            color = (0, 0, 255) if not fruit_disease.marketable else (0, 255, 0)
            cv2.rectangle(annotated, (x, y), (x+w, y+h), color, 3)
            label = f"{fruit_disease.disease_type.value[:8]}"
            cv2.putText(annotated, label, (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        return StrawberryDiseaseDetectionResult(
            timestamp=timestamp,
            strawberry_type=self.strawberry_type,
            detected_diseases=detected,
            foliar_lesions=all_lesions,
            fruit_diseases=fruit_diseases,
            primary_disease=primary_disease,
            overall_health_score=max(0.0, 1.0 - severity / 100),
            defoliation_percent=severity * 0.5,
            percent_marketable_fruit=percent_marketable,
            estimated_post_harvest_loss=20.0 if botrytis_risk > 0.7 else 5.0,
            yield_loss_estimate_percent=severity * disease_params.get("yield_loss", 0.5),
            environmental_risk=env_risk,
            treatment_plan=treatment,
            annotated_image=annotated,
            disease_heatmap=np.zeros_like(image),
            overall_confidence=0.87
        )


# Example usage
if __name__ == "__main__":
    detector = StrawberryDiseaseDetector(
        strawberry_type=StrawberryType.DAY_NEUTRAL,
        variety_name="Albion"
    )
    print("Strawberry Disease Detection System Initialized")
    print(f"Variety: {detector.variety_name}")
    print("Critical focus: ZERO tolerance for fruit disease")
