"""
AgroPulse Drone System - Pest Damage Classification
===================================================

Advanced AI system for detecting and classifying crop damage caused by insect pests
from aerial drone imagery. Enables targeted pest management and reduces pesticide usage.

Capabilities:
- Pest damage type classification (chewing, sucking, boring, mining)
- Pest species identification (100+ common agricultural pests)
- Damage severity assessment (economic threshold determination)
- Infestation spread mapping (spatial and temporal)
- Life stage detection (egg masses, larvae, adults)
- Natural enemy presence (beneficial insects)
- Pesticide recommendation engine
- Integrated Pest Management (IPM) decision support
- Economic injury level (EIL) calculations

Damage Categories:
- Chewing damage: Caterpillars, beetles, grasshoppers (leaf holes, defoliation)
- Sucking damage: Aphids, whiteflies, leafhoppers (chlorosis, honeydew, sooty mold)
- Boring damage: Corn borers, stem borers, fruit flies (entry holes, frass)
- Mining damage: Leafminers (serpentine tunnels in leaves)
- Galling damage: Gall wasps, gall midges (abnormal tissue growths)
- Root damage: Root-feeding larvae (stunting, wilting)

Technologies:
- YOLOv8 for object detection (pest individuals, egg masses)
- EfficientNet-B6 for damage pattern classification
- Temporal tracking (multi-visit analysis)
- Degree-day models for pest phenology
- Economic threshold algorithms

Target: 18,000 Lines of Code
"""

import numpy as np
import cv2
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import logging
import torch
import torch.nn as nn
import torchvision.models as models
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class DamageType(Enum):
    """Categories of pest damage."""
    CHEWING = "chewing"  # Leaf holes, defoliation
    SUCKING = "sucking"  # Chlorosis, stunting, honeydew
    BORING = "boring"  # Entry holes, tunneling, frass
    MINING = "mining"  # Leaf mines (serpentine tunnels)
    GALLING = "galling"  # Abnormal tissue growth
    ROOT_FEEDING = "root_feeding"  # Wilting, stunting, yellowing
    FRUIT_DAMAGE = "fruit_damage"  # Feeding scars, stings, rots
    SEED_DAMAGE = "seed_damage"  # Kernel feeding, chaff
    STEM_DAMAGE = "stem_damage"  # Stem tunneling, girdling


class PestGroup(Enum):
    """Major pest groups."""
    LEPIDOPTERA = "lepidoptera"  # Moths, butterflies
    COLEOPTERA = "coleoptera"  # Beetles
    HEMIPTERA = "hemiptera"  # True bugs, aphids, whiteflies
    DIPTERA = "diptera"  # Flies, midges
    ORTHOPTERA = "orthoptera"  # Grasshoppers, crickets
    HYMENOPTERA = "hymenoptera"  # Sawflies, wasps
    THYSANOPTERA = "thysanoptera"  # Thrips
    ACARI = "acari"  # Mites


class DamageSeverity(Enum):
    """Severity of pest damage."""
    NONE = "none"  # No visible damage
    TRACE = "trace"  # <5% defoliation/damage
    LIGHT = "light"  # 5-15% damage
    MODERATE = "moderate"  # 15-30% damage
    HEAVY = "heavy"  # 30-60% damage
    SEVERE = "severe"  # >60% damage
    TOTAL = "total"  # 100% loss


class LifeStage(Enum):
    """Pest life stages."""
    EGG = "egg"
    LARVA = "larva"  # Or nymph for hemimetabolous
    PUPA = "pupa"
    ADULT = "adult"


@dataclass
class PestDamageDetection:
    """Comprehensive pest damage detection result."""
    damage_type: DamageType
    pest_group: Optional[PestGroup]
    suspected_pest_species: List[str]  # Ranked by likelihood
    damage_severity: DamageSeverity
    confidence: float  # 0-1
    affected_area_hectares: float
    defoliation_percent: float  # For chewing damage
    plant_population_affected_percent: float
    life_stages_detected: List[LifeStage]
    spatial_pattern: str  # "uniform", "clustered", "edge_focused", "random"
    damage_age: str  # "fresh", "recent", "old"
    pest_density_per_meter_squared: Optional[float]
    economic_threshold_exceeded: bool
    recommended_action: str  # "monitor", "treat", "no_action"
    recommended_pesticide: Optional[str]
    natural_enemies_present: List[str]
    detection_date: datetime
    gps_location: Tuple[float, float]
    crop_growth_stage: str
    weather_conditions: Dict[str, float]


class PestDamageDetector(nn.Module):
    """
    Deep learning model for pest damage detection and classification.
    
    Multi-task network that simultaneously detects:
    - Damage type (9 categories)
    - Pest group (8 groups)
    - Damage severity (7 levels)
    - Spatial pattern (4 patterns)
    - Damage age (3 stages)
    """
    
    def __init__(
        self,
        num_damage_types: int = 9,
        num_pest_groups: int = 8,
        num_severity_levels: int = 7,
        num_patterns: int = 4,
        num_age_categories: int = 3
    ):
        super().__init__()
        
        # EfficientNet-B6 backbone for fine-grained pattern recognition
        from torchvision.models import efficientnet_b6
        effnet = efficientnet_b6(pretrained=True)
        self.features = effnet.features
        self.avgpool = effnet.avgpool
        
        feature_dim = 2304
        
        # Damage type classifier
        self.damage_type_classifier = nn.Sequential(
            nn.Linear(feature_dim, 1024),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(1024, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, num_damage_types)
        )
        
        # Pest group classifier
        self.pest_group_classifier = nn.Sequential(
            nn.Linear(feature_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.4),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, num_pest_groups),
            nn.Softmax(dim=1)
        )
        
        # Severity classifier
        self.severity_classifier = nn.Sequential(
            nn.Linear(feature_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, num_severity_levels),
            nn.Softmax(dim=1)
        )
        
        # Spatial pattern classifier
        self.pattern_classifier = nn.Sequential(
            nn.Linear(feature_dim, 256),
            nn.ReLU(),
            nn.Linear(256, num_patterns),
            nn.Softmax(dim=1)
        )
        
        # Damage age classifier
        self.age_classifier = nn.Sequential(
            nn.Linear(feature_dim, 256),
            nn.ReLU(),
            nn.Linear(256, num_age_categories),
            nn.Softmax(dim=1)
        )
        
        # Defoliation regressor (for chewing damage)
        self.defoliation_regressor = nn.Sequential(
            nn.Linear(feature_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 1),
            nn.Sigmoid()  # Output 0-1 (percentage)
        )
        
    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """Forward pass through pest damage detection network."""
        features = self.features(x)
        features = self.avgpool(features)
        features = features.view(features.size(0), -1)
        
        return {
            "damage_type": self.damage_type_classifier(features),
            "pest_group": self.pest_group_classifier(features),
            "severity": self.severity_classifier(features),
            "spatial_pattern": self.pattern_classifier(features),
            "damage_age": self.age_classifier(features),
            "defoliation": self.defoliation_regressor(features)
        }


class PestObjectDetector:
    """
    Object detection for individual pests and egg masses using YOLOv8.
    
    Detects and counts:
    - Adult insects (beetles, moths, bugs)
    - Larvae/caterpillars
    - Egg masses
    - Beneficial insects (predators, parasitoids)
    """
    
    def __init__(self, model_path: str = "pest_yolov8.pt"):
        from ultralytics import YOLO
        self.model = YOLO(model_path)
        
        # Pest categories trained in model
        self.pest_categories = {
            0: "caterpillar_small",
            1: "caterpillar_large",
            2: "beetle_adult",
            3: "beetle_larva",
            4: "aphid_colony",
            5: "whitefly_adult",
            6: "egg_mass",
            7: "grasshopper",
            8: "moth_adult",
            9: "leafhopper",
            10: "thrips",
            11: "mite_damage",
            12: "ladybug",  # Beneficial
            13: "lacewing",  # Beneficial
            14: "parasitoid_wasp"  # Beneficial
        }
        
    def detect_pests(
        self,
        image: np.ndarray,
        confidence_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Detect individual pests and egg masses in image.
        
        Args:
            image: Aerial image
            confidence_threshold: Minimum detection confidence
            
        Returns:
            Detection results with counts and locations
        """
        # Run YOLOv8 inference
        results = self.model(image, conf=confidence_threshold)
        
        # Parse results
        detections = defaultdict(list)
        pest_counts = defaultdict(int)
        beneficial_counts = defaultdict(int)
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                bbox = box.xyxy[0].cpu().numpy()
                
                category = self.pest_categories.get(class_id, "unknown")
                
                detection_info = {
                    "category": category,
                    "confidence": confidence,
                    "bbox": bbox.tolist(),
                    "center": ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
                }
                
                detections[category].append(detection_info)
                
                # Count pests vs beneficials
                if category in ["ladybug", "lacewing", "parasitoid_wasp"]:
                    beneficial_counts[category] += 1
                else:
                    pest_counts[category] += 1
        
        # Calculate pest density (pests per image area)
        image_area_m2 = self._calculate_image_area(image)
        total_pests = sum(pest_counts.values())
        pest_density = total_pests / image_area_m2 if image_area_m2 > 0 else 0
        
        return {
            "detections": dict(detections),
            "pest_counts": dict(pest_counts),
            "beneficial_counts": dict(beneficial_counts),
            "total_pests": total_pests,
            "total_beneficials": sum(beneficial_counts.values()),
            "pest_density_per_m2": pest_density,
            "beneficial_to_pest_ratio": (
                sum(beneficial_counts.values()) / total_pests
                if total_pests > 0 else 0
            )
        }
    
    def _calculate_image_area(self, image: np.ndarray) -> float:
        """Calculate ground area covered by image (m²)."""
        # Placeholder - would use flight altitude, camera FOV, etc.
        # Typical drone at 100m altitude with 4000x3000 image
        # covers approximately 200m x 150m = 30,000 m²
        return 30000.0


class PestKnowledgeBase:
    """
    Comprehensive pest knowledge base for agricultural pests.
    
    Contains information on:
    - Pest identification characteristics
    - Damage symptoms
    - Life cycles and phenology
    - Economic thresholds
    - Management recommendations
    """
    
    def __init__(self):
        self.pest_database = self._build_pest_database()
        
    def _build_pest_database(self) -> Dict[str, Dict[str, Any]]:
        """Build comprehensive pest information database."""
        return {
            "corn_earworm": {
                "scientific_name": "Helicoverpa zea",
                "common_names": ["Corn earworm", "Tomato fruitworm", "Cotton bollworm"],
                "pest_group": PestGroup.LEPIDOPTERA,
                "damage_type": [DamageType.CHEWING, DamageType.FRUIT_DAMAGE],
                "host_crops": ["Corn", "Tomato", "Cotton", "Soybean", "Pepper"],
                "damage_description": (
                    "Larvae feed on corn silks and kernels in ear tip. "
                    "In tomatoes, bore into fruit. Large, irregular holes with frass."
                ),
                "identification": {
                    "larvae": "Vary in color (green, pink, brown), 1.5 inches long, striped",
                    "adults": "Tan moths with irregular dark bands, 1.5-inch wingspan",
                    "eggs": "White, ribbed, dome-shaped, laid singly on silks/fruit"
                },
                "life_cycle": {
                    "generations_per_year": 3-4,
                    "overwintering_stage": "pupa",
                    "development_time_days": 30,
                    "degree_days_required": 850  # Base 55°F
                },
                "economic_threshold": {
                    "corn": "5-10% ears with live larvae",
                    "tomato": "1 larva per 5 plants"
                },
                "scouting_method": "Check ear zone for larvae, frass, or damage",
                "management": {
                    "chemical": [
                        "Spinosad",
                        "Carbaryl",
                        "Bifenthrin",
                        "Chlorantraniliprole"
                    ],
                    "biological": [
                        "Trichogramma wasps (egg parasitoid)",
                        "Bt (Bacillus thuringiensis)",
                        "Nuclear polyhedrosis virus"
                    ],
                    "cultural": [
                        "Early planting to avoid peak populations",
                        "Destroy crop residue",
                        "Trap crops"
                    ],
                    "timing": "Treat at silk stage when 5-10% ears have larvae"
                },
                "natural_enemies": ["Lacewings", "Ladybugs", "Pirate bugs", "Parasitoid wasps"],
                "resistance_risk": "High - resistant to pyrethroids in many areas"
            },
            
            "fall_armyworm": {
                "scientific_name": "Spodoptera frugiperda",
                "common_names": ["Fall armyworm"],
                "pest_group": PestGroup.LEPIDOPTERA,
                "damage_type": [DamageType.CHEWING],
                "host_crops": ["Corn", "Sorghum", "Rice", "Wheat", "Cotton"],
                "damage_description": (
                    "Larvae feed on leaves creating ragged holes and window-paning. "
                    "Prefer whorl of corn. Heavy infestations can cause total defoliation."
                ),
                "identification": {
                    "larvae": "Green to brown with 3 yellow stripes, inverted Y on head",
                    "adults": "Gray moths with white hindwings, 1.5-inch wingspan",
                    "eggs": "Gray, fuzzy masses of 100-200 eggs on leaves"
                },
                "life_cycle": {
                    "generations_per_year": 4-6,
                    "overwintering_stage": "pupa (in warm climates)",
                    "development_time_days": 25-30,
                    "degree_days_required": 800
                },
                "economic_threshold": {
                    "corn_vegetative": "20% plants with 2+ larvae in whorl",
                    "corn_reproductive": "5% plants with larvae in ear zone"
                },
                "scouting_method": "Check 20 plants in 5 locations, look in whorls",
                "management": {
                    "chemical": [
                        "Chlorantraniliprole",
                        "Spinetoram",
                        "Methomyl",
                        "Lambda-cyhalothrin"
                    ],
                    "biological": [
                        "Bt corn hybrids",
                        "Nomuraea rileyi (fungus)",
                        "Telenomus remus (egg parasitoid)"
                    ],
                    "cultural": [
                        "Early planting",
                        "Deep tillage to destroy pupae",
                        "Avoid continuous corn"
                    ],
                    "timing": "Treat when larvae <0.5 inch before entering whorl"
                },
                "natural_enemies": ["Spiders", "Ground beetles", "Parasitoid wasps", "Fungi"],
                "resistance_risk": "Very high - multiple resistance documented"
            },
            
            "aphids_corn": {
                "scientific_name": "Rhopalosiphum maidis",
                "common_names": ["Corn leaf aphid"],
                "pest_group": PestGroup.HEMIPTERA,
                "damage_type": [DamageType.SUCKING],
                "host_crops": ["Corn", "Sorghum", "Wheat", "Barley"],
                "damage_description": (
                    "Pierce leaves and suck sap, causing yellowing and stunting. "
                    "Produce honeydew (sticky substance) leading to sooty mold. "
                    "Vector of viral diseases."
                ),
                "identification": {
                    "adult": "Blue-green, soft-bodied, 1-2mm long, colonies on leaves/whorl",
                    "nymph": "Smaller, lighter colored",
                    "eggs": "Rarely seen - mostly parthenogenetic reproduction"
                },
                "life_cycle": {
                    "generations_per_year": "Many (asexual reproduction)",
                    "overwintering_stage": "adult on winter grains",
                    "development_time_days": 7-10,
                    "degree_days_required": 150
                },
                "economic_threshold": {
                    "vegetative": "50% plants with colonies covering 50% of leaf area",
                    "tassel_to_blister": "400 aphids per plant"
                },
                "scouting_method": "Check upper leaves and whorl for colonies",
                "management": {
                    "chemical": [
                        "Thiamethoxam (seed treatment)",
                        "Dimethoate",
                        "Lambda-cyhalothrin",
                        "Avoid broad-spectrum that kill beneficials"
                    ],
                    "biological": [
                        "Ladybugs (Hippodamia convergens)",
                        "Lacewings (Chrysoperla spp.)",
                        "Parasitoid wasps (Aphidius spp.)",
                        "Entomopathogenic fungi"
                    ],
                    "cultural": [
                        "Avoid excessive nitrogen",
                        "Eliminate volunteer corn/grasses",
                        "Tolerant hybrids"
                    ],
                    "timing": "Usually unnecessary - natural enemies provide control"
                },
                "natural_enemies": ["Ladybugs", "Lacewings", "Hoverfly larvae", "Parasitoid wasps"],
                "resistance_risk": "Moderate"
            },
            
            "western_corn_rootworm": {
                "scientific_name": "Diabrotica virgifera virgifera",
                "common_names": ["Western corn rootworm"],
                "pest_group": PestGroup.COLEOPTERA,
                "damage_type": [DamageType.ROOT_FEEDING, DamageType.CHEWING],
                "host_crops": ["Corn"],
                "damage_description": (
                    "Larvae feed on corn roots, causing lodging and nutrient/water stress. "
                    "Adults feed on silks (interfering with pollination) and leaves. "
                    "Can cause severe yield loss."
                ),
                "identification": {
                    "larvae": "White, brown head, 0.5 inch long, in soil on roots",
                    "adults": "Yellow-green beetles with black stripes, 0.25 inch",
                    "eggs": "White, oval, laid in soil near corn roots"
                },
                "life_cycle": {
                    "generations_per_year": 1,
                    "overwintering_stage": "egg",
                    "development_time_days": 50-60,
                    "degree_days_required": 900
                },
                "economic_threshold": {
                    "adults": "1 beetle per plant during silk stage",
                    "larvae": "Root damage node-injury scale >0.75"
                },
                "scouting_method": "Sticky traps for adults, root digs for larvae",
                "management": {
                    "chemical": [
                        "Soil insecticides at planting",
                        "Bifenthrin",
                        "Chlorpyrifos",
                        "Adult control: Carbaryl, Bifenthrin"
                    ],
                    "biological": [
                        "Bt corn (Cry3Bb1, Cry34/35Ab1)",
                        "Entomopathogenic nematodes (Heterorhabditis spp.)",
                        "Entomopathogenic fungi (Metarhizium)"
                    ],
                    "cultural": [
                        "Crop rotation (most effective)",
                        "Avoid continuous corn",
                        "Late planting (after egg hatch)"
                    ],
                    "timing": "Soil insecticide at planting, adult control at silk"
                },
                "natural_enemies": ["Ground beetles", "Rove beetles", "Nematodes", "Fungi"],
                "resistance_risk": "Very high - resistant to Bt proteins and insecticides"
            },
            
            "soybean_aphid": {
                "scientific_name": "Aphis glycines",
                "common_names": ["Soybean aphid"],
                "pest_group": PestGroup.HEMIPTERA,
                "damage_type": [DamageType.SUCKING],
                "host_crops": ["Soybean"],
                "damage_description": (
                    "Suck sap from stems, leaves, pods. Cause yellowing, stunting, "
                    "reduced seed size. Produce honeydew. Vector of viral diseases. "
                    "Can reach very high densities (thousands per plant)."
                ),
                "identification": {
                    "adult": "Pale yellow, soft-bodied, 1.5mm, black cornicles, on undersides",
                    "nymph": "Smaller, lighter",
                    "eggs": "Black, shiny, on buckthorn (overwintering host)"
                },
                "life_cycle": {
                    "generations_per_year": "Many (up to 18)",
                    "overwintering_stage": "egg on buckthorn",
                    "development_time_days": 7,
                    "degree_days_required": 120
                },
                "economic_threshold": {
                    "r1_r5": "250 aphids per plant with population increasing",
                    "after_r5": "Rarely economic"
                },
                "scouting_method": "Check 20-30 plants, count aphids on upper leaves",
                "management": {
                    "chemical": [
                        "Thiamethoxam (seed treatment)",
                        "Lambda-cyhalothrin",
                        "Bifenthrin + imidacloprid",
                        "Sulfoxaflor"
                    ],
                    "biological": [
                        "Ladybugs (multicolored Asian lady beetle)",
                        "Lacewings",
                        "Parasitoid wasps (Aphelinus certus)",
                        "Entomopathogenic fungi"
                    ],
                    "cultural": [
                        "Early planting",
                        "Aphid-resistant varieties (Rag genes)",
                        "Remove buckthorn (overwintering host)"
                    ],
                    "timing": "Treat when threshold exceeded and population increasing"
                },
                "natural_enemies": ["Ladybugs", "Lacewings", "Minute pirate bugs", "Parasitoid wasps"],
                "resistance_risk": "Moderate"
            },
            
            "colorado_potato_beetle": {
                "scientific_name": "Leptinotarsa decemlineata",
                "common_names": ["Colorado potato beetle", "Potato bug"],
                "pest_group": PestGroup.COLEOPTERA,
                "damage_type": [DamageType.CHEWING],
                "host_crops": ["Potato", "Tomato", "Eggplant", "Pepper"],
                "damage_description": (
                    "Adults and larvae feed on foliage, causing defoliation. "
                    "Can completely strip plants. Larvae more damaging than adults."
                ),
                "identification": {
                    "larvae": "Red-orange with black spots, humpbacked, 0.5 inch",
                    "adults": "Yellow-orange with 10 black stripes, 0.4 inch, hard shell",
                    "eggs": "Yellow-orange, oval, in clusters on leaf undersides"
                },
                "life_cycle": {
                    "generations_per_year": 1-3,
                    "overwintering_stage": "adult in soil",
                    "development_time_days": 21-24,
                    "degree_days_required": 400
                },
                "economic_threshold": {
                    "potato": "25 beetles (or 75 larvae) per 10 plants before flowering"
                },
                "scouting_method": "Visual inspection of plants, check undersides for eggs",
                "management": {
                    "chemical": [
                        "Spinosad",
                        "Novaluron",
                        "Chlorantraniliprole",
                        "Imidacloprid (soil/foliar)"
                    ],
                    "biological": [
                        "Bt (Bacillus thuringiensis tenebrionis)",
                        "Beauveria bassiana (fungus)",
                        "Predatory stink bugs"
                    ],
                    "cultural": [
                        "Crop rotation (500m from last year's potatoes)",
                        "Deep straw mulch",
                        "Trap crops",
                        "Handpicking (small gardens)"
                    ],
                    "timing": "Treat when larvae are small (1st-2nd instar)"
                },
                "natural_enemies": ["Ground beetles", "Ladybugs", "Spined soldier bug"],
                "resistance_risk": "Extremely high - resistant to nearly all insecticides"
            },
            
            "european_corn_borer": {
                "scientific_name": "Ostrinia nubilalis",
                "common_names": ["European corn borer"],
                "pest_group": PestGroup.LEPIDOPTERA,
                "damage_type": [DamageType.BORING, DamageType.CHEWING],
                "host_crops": ["Corn", "Pepper", "Potato", "Bean"],
                "damage_description": (
                    "Larvae tunnel into stalks, ears, and leaf midribs. "
                    "Cause broken tassels, dropped ears, stalk lodging. "
                    "Entry holes with sawdust-like frass."
                ),
                "identification": {
                    "larvae": "Flesh-colored with brown head, 1 inch long, inside stalks",
                    "adults": "Tan moths with zigzag lines, 1-inch wingspan",
                    "eggs": "White, overlapping scales in masses on leaves"
                },
                "life_cycle": {
                    "generations_per_year": 2,
                    "overwintering_stage": "larva in corn stalks/residue",
                    "development_time_days": 35-50,
                    "degree_days_required": 1400
                },
                "economic_threshold": {
                    "first_generation": "50% plants with whorl feeding and 1+ larvae per plant",
                    "second_generation": "50% plants with silk feeding"
                },
                "scouting_method": "Check for leaf feeding, cavities in ear shanks, broken tassels",
                "management": {
                    "chemical": [
                        "Chlorantraniliprole",
                        "Bifenthrin",
                        "Lambda-cyhalothrin",
                        "Spinosad"
                    ],
                    "biological": [
                        "Bt corn (Cry1Ab)",
                        "Trichogramma wasps (egg parasitoid)",
                        "Bacillus thuringiensis spray"
                    ],
                    "cultural": [
                        "Tillage to destroy overwintering larvae",
                        "Early harvest and destroy residue",
                        "Avoid late planting"
                    ],
                    "timing": "First generation: late whorl. Second generation: silk stage"
                },
                "natural_enemies": ["Tachinid flies", "Trichogramma wasps", "Ladybugs", "Lacewings"],
                "resistance_risk": "Low to moderate"
            },
            
            "stink_bugs": {
                "scientific_name": "Multiple species (Halyomorpha, Euschistus, Nezara)",
                "common_names": ["Brown marmorated stink bug", "Brown stink bug", "Green stink bug"],
                "pest_group": PestGroup.HEMIPTERA,
                "damage_type": [DamageType.SUCKING, DamageType.FRUIT_DAMAGE],
                "host_crops": ["Soybean", "Corn", "Cotton", "Fruit trees", "Vegetables"],
                "damage_description": (
                    "Pierce pods/fruits and suck sap. Cause shriveled seeds, "
                    "yeast spot, cat-facing of fruits. Inject enzymes that "
                    "kill plant tissue."
                ),
                "identification": {
                    "adult": "Shield-shaped, 0.5-0.7 inch, brown/green/marbled coloration",
                    "nymph": "Smaller, rounder, brightly colored (red/yellow/black)",
                    "eggs": "Barrel-shaped, in clusters on leaf undersides"
                },
                "life_cycle": {
                    "generations_per_year": 1-2,
                    "overwintering_stage": "adult in protected areas",
                    "development_time_days": 40-60,
                    "degree_days_required": 800
                },
                "economic_threshold": {
                    "soybean": "4-8 adults per 25 sweeps (varies by stage)",
                    "fruit": "1 stink bug per 5 trees"
                },
                "scouting_method": "Sweep net (25 sweeps), check pods/fruits",
                "management": {
                    "chemical": [
                        "Bifenthrin",
                        "Lambda-cyhalothrin",
                        "Thiamethoxam",
                        "Dinotefuran"
                    ],
                    "biological": [
                        "Samurai wasp (Trissolcus japonicus) - BMSB",
                        "Telenomus podisi (egg parasitoid)",
                        "Tachinid flies"
                    ],
                    "cultural": [
                        "Remove crop residue",
                        "Border trapping",
                        "Early planting to avoid peak populations",
                        "Trap crops (sorghum)"
                    ],
                    "timing": "Treat when threshold exceeded during pod fill (R3-R6)"
                },
                "natural_enemies": ["Tachinid flies", "Parasitoid wasps", "Predatory stink bugs"],
                "resistance_risk": "Moderate"
            }
        }
    
    def get_pest_info(self, pest_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve pest information by name."""
        return self.pest_database.get(pest_name.lower().replace(" ", "_"))
    
    def identify_pest_by_damage(
        self,
        damage_type: DamageType,
        crop: str,
        damage_description: str
    ) -> List[Tuple[str, float]]:
        """
        Identify likely pest species based on damage characteristics.
        
        Returns:
            List of (pest_name, likelihood_score) tuples, sorted by likelihood
        """
        candidates = []
        
        for pest_name, pest_info in self.pest_database.items():
            # Check if damage type matches
            if damage_type not in pest_info["damage_type"]:
                continue
            
            # Check if crop is a host
            if crop.capitalize() not in pest_info["host_crops"]:
                continue
            
            # Calculate likelihood score (placeholder - would use ML)
            likelihood = 0.5  # Base score
            
            # Boost if damage description matches
            if any(keyword in damage_description.lower() 
                   for keyword in pest_info["damage_description"].lower().split()):
                likelihood += 0.3
            
            candidates.append((pest_name, likelihood))
        
        # Sort by likelihood
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        return candidates


class EconomicThresholdCalculator:
    """
    Calculate economic injury levels (EIL) and economic thresholds (ET).
    
    EIL = Cost of control / (Market value × Yield loss per pest × Efficacy)
    ET = EIL with safety factor (typically 0.7-0.9 × EIL)
    """
    
    def __init__(self):
        pass
    
    def calculate_eil(
        self,
        control_cost_per_hectare: float,
        crop_market_value_per_unit: float,
        expected_yield_units_per_hectare: float,
        yield_loss_per_pest_percent: float,
        control_efficacy: float = 0.90
    ) -> float:
        """
        Calculate Economic Injury Level (pest density where control = loss value).
        
        Args:
            control_cost_per_hectare: Cost of pesticide + application ($/ha)
            crop_market_value_per_unit: Market price ($/bushel, $/kg, etc.)
            expected_yield_units_per_hectare: Expected yield without pests
            yield_loss_per_pest_percent: % yield loss per pest per unit area
            control_efficacy: Expected control (0-1)
            
        Returns:
            EIL in pests per hectare
        """
        # Value of yield per hectare
        total_crop_value = crop_market_value_per_unit * expected_yield_units_per_hectare
        
        # Value lost per pest
        value_loss_per_pest = total_crop_value * (yield_loss_per_pest_percent / 100)
        
        # EIL = Control cost / (Value lost per pest × Efficacy)
        eil = control_cost_per_hectare / (value_loss_per_pest * control_efficacy)
        
        return eil
    
    def calculate_et(
        self,
        eil: float,
        safety_factor: float = 0.8
    ) -> float:
        """
        Calculate Economic Threshold (when to treat, before reaching EIL).
        
        Args:
            eil: Economic Injury Level
            safety_factor: Multiplier (0.7-0.9) to treat before EIL reached
            
        Returns:
            ET in pests per hectare
        """
        return eil * safety_factor
    
    def should_treat(
        self,
        observed_pest_density: float,
        economic_threshold: float
    ) -> bool:
        """Determine if treatment is economically justified."""
        return observed_pest_density >= economic_threshold
    
    def calculate_roi_of_treatment(
        self,
        observed_pest_density: float,
        control_cost_per_hectare: float,
        crop_market_value_per_unit: float,
        expected_yield_units_per_hectare: float,
        yield_loss_per_pest_percent: float,
        control_efficacy: float = 0.90,
        field_area_hectares: float = 1.0
    ) -> Dict[str, float]:
        """Calculate return on investment for pest control treatment."""
        # Total crop value
        total_value = crop_market_value_per_unit * expected_yield_units_per_hectare * field_area_hectares
        
        # Yield loss without treatment
        total_loss_without_treatment = total_value * (
            observed_pest_density * yield_loss_per_pest_percent / 100
        )
        
        # Yield loss with treatment (reduced by efficacy)
        total_loss_with_treatment = total_loss_without_treatment * (1 - control_efficacy)
        
        # Value saved by treatment
        value_saved = total_loss_without_treatment - total_loss_with_treatment
        
        # Treatment cost
        total_cost = control_cost_per_hectare * field_area_hectares
        
        # Net benefit
        net_benefit = value_saved - total_cost
        
        # ROI
        roi = (net_benefit / total_cost * 100) if total_cost > 0 else 0
        
        return {
            "value_saved": value_saved,
            "treatment_cost": total_cost,
            "net_benefit": net_benefit,
            "roi_percent": roi,
            "recommended": net_benefit > 0
        }


class PestPhenologyModel:
    """
    Degree-day models for predicting pest development and emergence timing.
    
    Uses Growing Degree Days (GDD) to forecast:
    - Adult emergence from overwintering
    - Egg hatch timing
    - Peak larval activity
    - Optimal treatment windows
    """
    
    def __init__(self):
        # Degree-day models for major pests
        self.dd_models = {
            "corn_earworm": {
                "base_temp_f": 55,
                "adult_emergence_dd": [500, 1350, 2200],  # 3 generations
                "egg_to_larva_dd": 100,
                "larva_to_pupa_dd": 300,
                "pupa_to_adult_dd": 250
            },
            "fall_armyworm": {
                "base_temp_f": 50,
                "adult_emergence_dd": [400, 1200, 2000, 2800],  # 4 generations
                "egg_to_larva_dd": 80,
                "larva_to_pupa_dd": 280,
                "pupa_to_adult_dd": 200
            },
            "western_corn_rootworm": {
                "base_temp_f": 52,
                "egg_hatch_dd": 684,  # 50% hatch
                "larva_to_pupa_dd": 500,
                "pupa_to_adult_dd": 200
            },
            "european_corn_borer": {
                "base_temp_f": 50,
                "adult_emergence_dd": [600, 1800],  # 2 generations
                "egg_to_larva_dd": 70,
                "larva_to_pupa_dd": 400,
                "pupa_to_adult_dd": 300
            }
        }
        
    def calculate_gdd(
        self,
        temp_max_f: float,
        temp_min_f: float,
        base_temp_f: float
    ) -> float:
        """
        Calculate Growing Degree Days for one day.
        
        GDD = (T_max + T_min) / 2 - T_base
        
        With adjustments:
        - Cap T_max at upper threshold (usually 86°F)
        - Set T_min to base if below base
        """
        # Cap max temperature
        temp_max_f = min(temp_max_f, 86)
        
        # Set min to base if below
        temp_min_f = max(temp_min_f, base_temp_f)
        
        # Calculate average
        avg_temp = (temp_max_f + temp_min_f) / 2
        
        # GDD
        gdd = max(0, avg_temp - base_temp_f)
        
        return gdd
    
    def predict_pest_stage(
        self,
        pest_name: str,
        cumulative_gdd: float,
        biofix_date: datetime
    ) -> Dict[str, Any]:
        """
        Predict current pest life stage and timing of next stages.
        
        Args:
            pest_name: Name of pest
            cumulative_gdd: Accumulated GDD since biofix
            biofix_date: Start date for GDD accumulation
            
        Returns:
            Prediction of current and upcoming life stages
        """
        model = self.dd_models.get(pest_name.lower().replace(" ", "_"))
        if not model:
            return {"error": "Pest model not found"}
        
        # Determine current generation
        current_generation = 1
        for gen_dd in model.get("adult_emergence_dd", []):
            if cumulative_gdd >= gen_dd:
                current_generation += 1
        
        # Determine life stage within generation
        gen_start_dd = model.get("adult_emergence_dd", [0])[current_generation - 1]
        dd_since_gen_start = cumulative_gdd - gen_start_dd
        
        if dd_since_gen_start < model.get("egg_to_larva_dd", 100):
            current_stage = "egg"
        elif dd_since_gen_start < model.get("egg_to_larva_dd", 100) + model.get("larva_to_pupa_dd", 300):
            current_stage = "larva"
        elif dd_since_gen_start < (
            model.get("egg_to_larva_dd", 100) + 
            model.get("larva_to_pupa_dd", 300) + 
            model.get("pupa_to_adult_dd", 200)
        ):
            current_stage = "pupa"
        else:
            current_stage = "adult"
        
        # Predict next generation start
        next_gen_dd = model.get("adult_emergence_dd", [9999])[
            min(current_generation, len(model.get("adult_emergence_dd", [])) - 1)
        ]
        dd_to_next_gen = next_gen_dd - cumulative_gdd
        
        return {
            "pest": pest_name,
            "cumulative_gdd": cumulative_gdd,
            "current_generation": current_generation,
            "current_stage": current_stage,
            "dd_to_next_generation": dd_to_next_gen,
            "biofix_date": biofix_date.strftime("%Y-%m-%d")
        }


__all__ = [
    "PestDamageDetector",
    "PestObjectDetector",
    "PestKnowledgeBase",
    "EconomicThresholdCalculator",
    "PestPhenologyModel",
    "PestDamageDetection",
    "DamageType",
    "PestGroup",
    "DamageSeverity",
    "LifeStage",
]
