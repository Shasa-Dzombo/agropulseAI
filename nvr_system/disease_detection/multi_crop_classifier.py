"""
Multi-Crop Disease Classifier
Cross-crop disease recognition and family-level pattern analysis

CAPABILITIES:
- Species-agnostic symptom analysis
- Cross-crop disease identification
- Family-level disease patterns (Solanaceae, Cucurbitaceae, Rosaceae)
- Symptom overlap resolution
- Host range determination
- Multi-host pathogen detection

CRITICAL CROSS-CROP DISEASES:

1. Botrytis cinerea (Gray Mold) - 200+ HOST SPECIES
   - Affects: Strawberry, grape, tomato, pepper, lettuce
   - Universal gray fuzzy spores
   - $10-100 billion annual losses globally

2. Powdery Mildew Complex - MULTIPLE SPECIES
   - Erysiphe/Oidium/Podosphaera/Sphaerotheca
   - Affects: Grape, cucumber, strawberry, mango, peach
   - White powdery growth diagnostic across all hosts

3. Phytophthora infestans (Late Blight) - SOLANACEAE SPECIALIST
   - Affects: Potato, tomato (Solanaceae family)
   - Water-soaked lesions + white sporulation
   - Irish Famine pathogen

4. Verticillium Wilt - BROAD HOST RANGE
   - Affects: Tomato, pepper, eggplant, strawberry, olive, coffee
   - Vascular browning pattern consistent
   - NO CURE across all hosts

5. Anthracnose Complex - COLLETOTRICHUM SPP.
   - Affects: Mango, strawberry, pepper, tomato, coffee, olive
   - Black sunken lesions + pink spore masses
   - Species-specific but similar symptoms

FAMILY-LEVEL PATTERNS:
- Solanaceae (tomato, potato, pepper, eggplant): Late blight, Verticillium, bacterial spots
- Cucurbitaceae (cucumber, watermelon): Downy mildew, powdery mildew, gummy stem blight
- Rosaceae (strawberry, apple, peach): Fire blight, powdery mildew, brown rot

Author: AgroPulse AI Team
Version: 1.0.0
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime


class PlantFamily(Enum):
    """Major plant family classifications"""
    SOLANACEAE = "solanaceae"  # Tomato, potato, pepper, eggplant
    CUCURBITACEAE = "cucurbitaceae"  # Cucumber, watermelon
    ROSACEAE = "rosaceae"  # Strawberry, apple, peach
    VITACEAE = "vitaceae"  # Grape
    RUTACEAE = "rutaceae"  # Citrus
    FABACEAE = "fabaceae"  # Pea, beans
    BRASSICACEAE = "brassicaceae"  # Cabbage, broccoli
    ASTERACEAE = "asteraceae"  # Lettuce
    LAURACEAE = "lauraceae"  # Avocado
    RUBIACEAE = "rubiaceae"  # Coffee
    THEACEAE = "theaceae"  # Tea
    OLEACEAE = "oleaceae"  # Olive
    MUSACEAE = "musaceae"  # Banana
    ANACARDIACEAE = "anacardiaceae"  # Mango


class DiseaseHostRange(Enum):
    """Disease host range classifications"""
    NARROW = "narrow"  # 1-2 species
    FAMILY = "family"  # Single plant family
    BROAD = "broad"  # Multiple families
    UNIVERSAL = "universal"  # 100+ species


class CrossCropDisease(Enum):
    """Major cross-crop disease classifications"""
    # Universal pathogens
    BOTRYTIS_GRAY_MOLD = "botrytis_gray_mold"
    POWDERY_MILDEW_COMPLEX = "powdery_mildew_complex"
    ANTHRACNOSE_COMPLEX = "anthracnose_complex"
    
    # Broad host range
    VERTICILLIUM_WILT = "verticillium_wilt"
    FUSARIUM_WILT_COMPLEX = "fusarium_wilt_complex"
    PHYTOPHTHORA_ROOT_ROT = "phytophthora_root_rot"
    SCLEROTINIA_WHITE_MOLD = "sclerotinia_white_mold"
    RHIZOCTONIA_ROOT_ROT = "rhizoctonia_root_rot"
    
    # Family-specific
    SOLANACEAE_LATE_BLIGHT = "late_blight"  # Potato, tomato
    SOLANACEAE_BACTERIAL_SPOT = "bacterial_spot_solanaceae"
    CUCURBIT_DOWNY_MILDEW = "downy_mildew_cucurbit"
    ROSACEAE_FIRE_BLIGHT = "fire_blight"
    ROSACEAE_BROWN_ROT = "brown_rot"


@dataclass
class UniversalSymptom:
    """Species-agnostic symptom description"""
    symptom_type: str  # lesion, wilt, rot, blight, mold
    color_pattern: str  # brown, black, white, gray, yellow
    texture: str  # fuzzy, powdery, water_soaked, necrotic, sunken
    location: str  # leaf, fruit, stem, root, flower
    progression: str  # rapid, slow, static
    
    # Diagnostic features
    diagnostic_color: Optional[str] = None
    diagnostic_texture: Optional[str] = None
    diagnostic_shape: Optional[str] = None
    
    # Host-independent markers
    spore_color: Optional[str] = None
    bacterial_ooze: bool = False
    vascular_browning: bool = False


@dataclass
class HostRange:
    """Disease host range information"""
    primary_hosts: List[str]
    family_susceptibility: Dict[PlantFamily, str]  # resistant, susceptible, highly_susceptible
    host_range_type: DiseaseHostRange
    
    # Geographic and environmental
    global_distribution: str
    optimal_hosts: List[str]


@dataclass
class MultiCropDetectionResult:
    """Multi-crop disease detection result"""
    disease: CrossCropDisease
    confidence: float
    affected_crops: List[str]
    host_range: HostRange
    universal_symptoms: List[UniversalSymptom]
    
    # Family-level analysis
    plant_family: Optional[PlantFamily] = None
    family_specific: bool = False
    
    # Cross-crop risk
    spread_potential: str = "low"  # low, moderate, high, critical
    quarantine_concern: bool = False
    
    timestamp: datetime = field(default_factory=datetime.now)


class MultiCropDiseaseClassifier:
    """
    Advanced multi-crop disease classification system
    
    CAPABILITIES:
    - Species-agnostic symptom recognition
    - Cross-crop disease identification
    - Family-level pattern analysis
    - Host range determination
    """
    
    def __init__(self):
        self.disease_database = self._initialize_cross_crop_database()
        self.family_patterns = self._initialize_family_patterns()
        
    def _initialize_cross_crop_database(self) -> Dict[CrossCropDisease, Dict]:
        """Comprehensive cross-crop disease database"""
        return {
            CrossCropDisease.BOTRYTIS_GRAY_MOLD: {
                'pathogen': 'Botrytis cinerea',
                'pathogen_type': 'Fungus (necrotrophic)',
                'host_range': HostRange(
                    primary_hosts=[
                        'Strawberry', 'Grape', 'Tomato', 'Pepper', 'Lettuce',
                        'Cucumber', 'Apple', 'Peach', 'Blueberry', 'Raspberry'
                    ],
                    family_susceptibility={
                        PlantFamily.ROSACEAE: 'highly_susceptible',
                        PlantFamily.VITACEAE: 'highly_susceptible',
                        PlantFamily.SOLANACEAE: 'susceptible',
                        PlantFamily.CUCURBITACEAE: 'susceptible',
                        PlantFamily.ASTERACEAE: 'susceptible'
                    },
                    host_range_type=DiseaseHostRange.UNIVERSAL,
                    global_distribution='Worldwide - every continent',
                    optimal_hosts=['Strawberry (20-50% post-harvest)', 'Grape (20-30% bunch rot)']
                ),
                'universal_symptoms': [
                    UniversalSymptom(
                        symptom_type='mold',
                        color_pattern='gray',
                        texture='fuzzy',
                        location='fruit',
                        progression='rapid',
                        diagnostic_color='gray',
                        diagnostic_texture='fuzzy_spores',
                        spore_color='gray'
                    ),
                    UniversalSymptom(
                        symptom_type='rot',
                        color_pattern='brown',
                        texture='soft_watery',
                        location='fruit',
                        progression='rapid'
                    ),
                    UniversalSymptom(
                        symptom_type='blight',
                        color_pattern='brown',
                        texture='necrotic',
                        location='flower',
                        progression='rapid'
                    )
                ],
                'diagnostic_features': {
                    'spores': 'GRAY FUZZY spore masses (universal across all hosts)',
                    'progression': 'Rapid soft rot (24-72 hours)',
                    'conditions': 'Cool + humid (18-24°C, 90%+ RH)',
                    'spread': 'Airborne conidia',
                    'persistence': 'Sclerotia survive 2+ years'
                },
                'economic_impact': {
                    'global_losses': '$10-100 billion annually (estimates vary)',
                    'hosts_affected': '200+ plant species',
                    'strawberry': '20-50% post-harvest losses',
                    'grape': '20-30% bunch rot',
                    'tomato': '10-30% greenhouse losses'
                },
                'control_universal': {
                    'fungicides': 'FRAC-7 (boscalid), FRAC-9 (cyprodinil), FRAC-17 (fenhexamid)',
                    'resistance': 'CRITICAL - resistance to all major groups documented',
                    'cultural': 'Air circulation, reduce humidity, rapid cooling',
                    'biological': 'Aureobasidium pullulans, Trichoderma'
                },
                'notes': 'MOST ECONOMICALLY IMPORTANT PATHOGEN WORLDWIDE - 200+ hosts'
            },
            
            CrossCropDisease.POWDERY_MILDEW_COMPLEX: {
                'pathogen': 'Multiple genera (Erysiphe, Oidium, Podosphaera, Sphaerotheca)',
                'pathogen_type': 'Fungi (obligate parasites)',
                'host_range': HostRange(
                    primary_hosts=[
                        'Grape', 'Cucumber', 'Strawberry', 'Mango', 'Peach',
                        'Apple', 'Tomato', 'Pepper', 'Watermelon'
                    ],
                    family_susceptibility={
                        PlantFamily.VITACEAE: 'highly_susceptible',
                        PlantFamily.CUCURBITACEAE: 'highly_susceptible',
                        PlantFamily.ROSACEAE: 'susceptible',
                        PlantFamily.SOLANACEAE: 'moderately_susceptible'
                    },
                    host_range_type=DiseaseHostRange.UNIVERSAL,
                    global_distribution='Worldwide',
                    optimal_hosts=['Grape ($1B annual)', 'Cucumber (#1 cucurbit disease)']
                ),
                'universal_symptoms': [
                    UniversalSymptom(
                        symptom_type='mildew',
                        color_pattern='white',
                        texture='powdery',
                        location='leaf',
                        progression='slow',
                        diagnostic_color='white',
                        diagnostic_texture='powdery',
                        spore_color='white'
                    ),
                    UniversalSymptom(
                        symptom_type='mildew',
                        color_pattern='white',
                        texture='powdery',
                        location='fruit',
                        progression='slow'
                    )
                ],
                'diagnostic_features': {
                    'appearance': 'WHITE POWDERY coating (universal across all hosts)',
                    'conditions': 'DRY weather disease (no wetness required)',
                    'spread': 'Wind-borne conidia',
                    'host_specific': 'Each host has specific Erysiphe/Oidium species',
                    'cross_infection': 'Generally host-specific (grape PM ≠ cucumber PM)'
                },
                'species_specific': {
                    'grape': 'Erysiphe necator (Uncinula necator)',
                    'cucumber': 'Podosphaera xanthii, Golovinomyces cichoracearum',
                    'strawberry': 'Podosphaera aphanis',
                    'mango': 'Oidium mangiferae',
                    'apple': 'Podosphaera leucotricha'
                },
                'economic_impact': {
                    'global': '$2-3 billion annually',
                    'grape': '$1 billion annually',
                    'cucumber': '#1 cucurbit disease'
                },
                'control_universal': {
                    'fungicides': 'FRAC-3 (DMI), FRAC-11 (QoI), FRAC-U6 (potassium bicarbonate)',
                    'resistance': 'DMI resistance widespread, QoI emerging',
                    'cultural': 'Sulfur (oldest fungicide), air circulation',
                    'biological': 'Bacillus subtilis, Ampelomyces quisqualis'
                },
                'notes': 'HOST-SPECIFIC SPECIES but universal symptom (white powdery coating)'
            },
            
            CrossCropDisease.VERTICILLIUM_WILT: {
                'pathogen': 'Verticillium dahliae, V. albo-atrum',
                'pathogen_type': 'Fungus (soil-borne vascular)',
                'threat_level': 'LETHAL - NO CURE',
                'host_range': HostRange(
                    primary_hosts=[
                        'Tomato', 'Pepper', 'Eggplant', 'Potato', 'Strawberry',
                        'Olive', 'Coffee', 'Cotton', 'Maple'
                    ],
                    family_susceptibility={
                        PlantFamily.SOLANACEAE: 'highly_susceptible',
                        PlantFamily.ROSACEAE: 'susceptible',
                        PlantFamily.OLEACEAE: 'susceptible'
                    },
                    host_range_type=DiseaseHostRange.BROAD,
                    global_distribution='Worldwide temperate regions',
                    optimal_hosts=['Tomato (most studied)', 'Olive (ancient groves threat)']
                ),
                'universal_symptoms': [
                    UniversalSymptom(
                        symptom_type='wilt',
                        color_pattern='yellow',
                        texture='wilted',
                        location='leaf',
                        progression='slow',
                        vascular_browning=True
                    ),
                    UniversalSymptom(
                        symptom_type='vascular_browning',
                        color_pattern='brown',
                        texture='necrotic',
                        location='stem',
                        progression='slow',
                        diagnostic_color='brown_streaks',
                        vascular_browning=True
                    )
                ],
                'diagnostic_features': {
                    'vascular': 'BROWN VASCULAR STREAKS (universal diagnostic)',
                    'pattern': 'Sectoral wilting (one side first)',
                    'progression': 'Slow progressive death',
                    'soil': 'Persists 15+ years in soil',
                    'no_cure': 'NO CHEMICAL CONTROL across all hosts'
                },
                'economic_impact': {
                    'tomato': 'Major greenhouse constraint',
                    'olive': 'Threatens ancient groves (centuries old)',
                    'strawberry': 'Soil fumigation required',
                    'soil_loss': 'Fields infested 15+ years'
                },
                'control_universal': {
                    'chemical': 'NONE EFFECTIVE',
                    'cultural': 'Soil fumigation (pre-plant), resistant varieties, crop rotation',
                    'prevention': 'ONLY control method',
                    'rotation': '7-10 years non-host crops'
                },
                'notes': 'NO CURE across all hosts - vascular browning diagnostic universal'
            },
            
            CrossCropDisease.SOLANACEAE_LATE_BLIGHT: {
                'pathogen': 'Phytophthora infestans',
                'pathogen_type': 'Oomycete (water mold)',
                'historical': 'IRISH FAMINE 1845-1852 (1 million deaths)',
                'host_range': HostRange(
                    primary_hosts=['Potato', 'Tomato'],
                    family_susceptibility={
                        PlantFamily.SOLANACEAE: 'highly_susceptible'
                    },
                    host_range_type=DiseaseHostRange.FAMILY,
                    global_distribution='Worldwide potato/tomato growing regions',
                    optimal_hosts=['Potato (tuber infection)', 'Tomato (fruit infection)']
                ),
                'universal_symptoms': [
                    UniversalSymptom(
                        symptom_type='blight',
                        color_pattern='brown',
                        texture='water_soaked',
                        location='leaf',
                        progression='rapid',
                        diagnostic_texture='water_soaked',
                        spore_color='white'
                    )
                ],
                'diagnostic_features': {
                    'lesions': 'WATER-SOAKED lesions (both hosts)',
                    'sporulation': 'WHITE FUZZY growth leaf underside (humid)',
                    'progression': 'RAPID (entire field 7-10 days)',
                    'family_specific': 'SOLANACEAE ONLY',
                    'cross_infection': 'Potato infects tomato and vice versa'
                },
                'economic_impact': {
                    'global': '$6.7 billion annually',
                    'historical': 'Irish Famine (1 million deaths, 1 million emigrated)',
                    'potato': 'Can destroy crop 7-10 days',
                    'tomato': 'Major constraint worldwide'
                },
                'notes': 'FAMILY-SPECIFIC but cross-infects within Solanaceae'
            },
            
            CrossCropDisease.ANTHRACNOSE_COMPLEX: {
                'pathogen': 'Colletotrichum spp. (C. gloeosporioides, C. acutatum, C. kahawae)',
                'pathogen_type': 'Fungi (multiple species)',
                'host_range': HostRange(
                    primary_hosts=[
                        'Mango', 'Strawberry', 'Pepper', 'Tomato', 'Coffee',
                        'Olive', 'Avocado', 'Citrus', 'Apple'
                    ],
                    family_susceptibility={
                        PlantFamily.ANACARDIACEAE: 'highly_susceptible',
                        PlantFamily.ROSACEAE: 'susceptible',
                        PlantFamily.SOLANACEAE: 'susceptible',
                        PlantFamily.RUBIACEAE: 'susceptible'
                    },
                    host_range_type=DiseaseHostRange.BROAD,
                    global_distribution='Worldwide tropical/subtropical',
                    optimal_hosts=['Mango (#1 disease)', 'Coffee (African endemic)']
                ),
                'universal_symptoms': [
                    UniversalSymptom(
                        symptom_type='lesion',
                        color_pattern='black',
                        texture='sunken',
                        location='fruit',
                        progression='rapid',
                        diagnostic_color='black',
                        diagnostic_shape='circular_sunken',
                        spore_color='pink'
                    )
                ],
                'diagnostic_features': {
                    'lesions': 'BLACK SUNKEN circular lesions (universal)',
                    'spores': 'PINK SALMON-colored acervuli (wet conditions)',
                    'latent': 'Latent infections (invisible at harvest)',
                    'host_specific': 'Species vary but symptoms similar'
                },
                'economic_impact': {
                    'mango': '$500+ million (20-80% post-harvest)',
                    'coffee': 'African endemic (30-80% loss)',
                    'strawberry': 'Crown rot + fruit rot'
                },
                'notes': 'SPECIES-SPECIFIC but similar symptoms across hosts'
            }
        }
    
    def _initialize_family_patterns(self) -> Dict[PlantFamily, Dict]:
        """Family-level disease susceptibility patterns"""
        return {
            PlantFamily.SOLANACEAE: {
                'members': ['Tomato', 'Potato', 'Pepper', 'Eggplant', 'Tobacco'],
                'common_diseases': [
                    'Late blight (Phytophthora infestans)',
                    'Verticillium wilt',
                    'Bacterial spot (Xanthomonas)',
                    'Fusarium wilt',
                    'Powdery mildew (less severe than other families)'
                ],
                'diagnostic_pattern': 'Water-soaked lesions common',
                'resistance_genes': 'Shared resistance (Pto, Prf, Cf genes)',
                'notes': 'Late blight ONLY attacks Solanaceae'
            },
            
            PlantFamily.CUCURBITACEAE: {
                'members': ['Cucumber', 'Watermelon', 'Squash', 'Pumpkin', 'Melon'],
                'common_diseases': [
                    'Downy mildew (Pseudoperonospora cubensis) - #1 THREAT',
                    'Powdery mildew (Podosphaera/Golovinomyces) - #2',
                    'Gummy stem blight',
                    'Fusarium wilt',
                    'Bacterial wilt (Erwinia)'
                ],
                'diagnostic_pattern': 'Angular leaf spots (veins limit spread)',
                'resistance_genes': 'Limited resistance available',
                'notes': 'Downy mildew and powdery mildew BOTH major problems'
            },
            
            PlantFamily.ROSACEAE: {
                'members': ['Strawberry', 'Apple', 'Peach', 'Cherry', 'Pear', 'Rose'],
                'common_diseases': [
                    'Fire blight (Erwinia amylovora) - bacterial',
                    'Brown rot (Monilinia) - stone fruits',
                    'Powdery mildew',
                    'Apple scab (Venturia)',
                    'Botrytis gray mold'
                ],
                'diagnostic_pattern': 'Fire blight "shepherd\'s crook" characteristic',
                'resistance_genes': 'Vf (apple scab), fire blight resistance',
                'notes': 'Fire blight threatens all Rosaceae'
            },
            
            PlantFamily.VITACEAE: {
                'members': ['Grape (wine/table)'],
                'common_diseases': [
                    'Downy mildew (Plasmopara) - $3B annually',
                    'Powdery mildew (Erysiphe) - $1B annually',
                    'Botrytis (dual nature)',
                    'Pierce\'s disease (Xylella)'
                ],
                'diagnostic_pattern': 'Downy mildew "oil spots" + white underside',
                'notes': 'Viticulture threatened by multiple diseases'
            }
        }
    
    def classify_universal_symptoms(self, image: np.ndarray) -> Optional[MultiCropDetectionResult]:
        """
        Classify disease based on universal symptoms (species-agnostic)
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Check for gray fuzzy spores (Botrytis universal marker)
        gray_spores = self._detect_gray_fuzzy_spores(hsv)
        if gray_spores['detected']:
            disease_info = self.disease_database[CrossCropDisease.BOTRYTIS_GRAY_MOLD]
            return MultiCropDetectionResult(
                disease=CrossCropDisease.BOTRYTIS_GRAY_MOLD,
                confidence=gray_spores['confidence'],
                affected_crops=disease_info['host_range'].primary_hosts,
                host_range=disease_info['host_range'],
                universal_symptoms=disease_info['universal_symptoms'],
                spread_potential='critical',
                quarantine_concern=False
            )
        
        # Check for white powdery coating (Powdery mildew universal marker)
        white_powder = self._detect_white_powdery(hsv)
        if white_powder['detected']:
            disease_info = self.disease_database[CrossCropDisease.POWDERY_MILDEW_COMPLEX]
            return MultiCropDetectionResult(
                disease=CrossCropDisease.POWDERY_MILDEW_COMPLEX,
                confidence=white_powder['confidence'],
                affected_crops=disease_info['host_range'].primary_hosts,
                host_range=disease_info['host_range'],
                universal_symptoms=disease_info['universal_symptoms'],
                spread_potential='high',
                quarantine_concern=False
            )
        
        # Check for vascular browning (Verticillium universal marker)
        vascular = self._detect_vascular_browning(hsv)
        if vascular['detected']:
            disease_info = self.disease_database[CrossCropDisease.VERTICILLIUM_WILT]
            return MultiCropDetectionResult(
                disease=CrossCropDisease.VERTICILLIUM_WILT,
                confidence=vascular['confidence'],
                affected_crops=disease_info['host_range'].primary_hosts,
                host_range=disease_info['host_range'],
                universal_symptoms=disease_info['universal_symptoms'],
                spread_potential='moderate',
                quarantine_concern=False
            )
        
        return None
    
    def _detect_gray_fuzzy_spores(self, hsv: np.ndarray) -> Dict:
        """Detect gray fuzzy Botrytis spores (universal marker)"""
        lower_gray = np.array([0, 0, 80])
        upper_gray = np.array([180, 50, 180])
        gray_mask = cv2.inRange(hsv, lower_gray, upper_gray)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        gray_mask = cv2.morphologyEx(gray_mask, cv2.MORPH_CLOSE, kernel)
        
        gray_pixels = np.sum(gray_mask > 0)
        total_pixels = hsv.shape[0] * hsv.shape[1]
        gray_percent = (gray_pixels / total_pixels) * 100
        
        if gray_percent > 2.0:
            return {
                'detected': True,
                'confidence': min(0.75 + (gray_percent / 20) * 0.20, 0.95)
            }
        return {'detected': False, 'confidence': 0.0}
    
    def _detect_white_powdery(self, hsv: np.ndarray) -> Dict:
        """Detect white powdery coating (universal powdery mildew marker)"""
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 30, 255])
        white_mask = cv2.inRange(hsv, lower_white, upper_white)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE, kernel)
        
        white_pixels = np.sum(white_mask > 0)
        total_pixels = hsv.shape[0] * hsv.shape[1]
        white_percent = (white_pixels / total_pixels) * 100
        
        if white_percent > 3.0:
            return {
                'detected': True,
                'confidence': min(0.80 + (white_percent / 25) * 0.15, 0.95)
            }
        return {'detected': False, 'confidence': 0.0}
    
    def _detect_vascular_browning(self, hsv: np.ndarray) -> Dict:
        """Detect vascular browning (Verticillium universal marker)"""
        lower_brown = np.array([10, 50, 40])
        upper_brown = np.array([25, 200, 120])
        brown_mask = cv2.inRange(hsv, lower_brown, upper_brown)
        
        # Look for streak pattern (vascular)
        kernel_vertical = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 10))
        streaks = cv2.morphologyEx(brown_mask, cv2.MORPH_OPEN, kernel_vertical)
        
        streak_pixels = np.sum(streaks > 0)
        total_pixels = hsv.shape[0] * hsv.shape[1]
        streak_percent = (streak_pixels / total_pixels) * 100
        
        if streak_percent > 1.0:
            return {
                'detected': True,
                'confidence': min(0.70 + (streak_percent / 10) * 0.20, 0.90)
            }
        return {'detected': False, 'confidence': 0.0}
    
    def get_family_disease_risk(self, plant_family: PlantFamily) -> Dict:
        """Get disease risk profile for plant family"""
        if plant_family in self.family_patterns:
            return self.family_patterns[plant_family]
        return {}
    
    def check_cross_infection_risk(self, disease: CrossCropDisease, 
                                   crops_in_vicinity: List[str]) -> Dict:
        """
        Check if disease can cross-infect nearby crops
        """
        if disease not in self.disease_database:
            return {'risk': 'unknown', 'susceptible_crops': []}
        
        disease_info = self.disease_database[disease]
        host_range = disease_info['host_range']
        
        susceptible_nearby = []
        for crop in crops_in_vicinity:
            if crop in host_range.primary_hosts:
                susceptible_nearby.append(crop)
        
        risk_level = 'low'
        if len(susceptible_nearby) > 0:
            if host_range.host_range_type == DiseaseHostRange.UNIVERSAL:
                risk_level = 'critical'
            elif host_range.host_range_type == DiseaseHostRange.BROAD:
                risk_level = 'high'
            elif host_range.host_range_type == DiseaseHostRange.FAMILY:
                risk_level = 'moderate'
        
        return {
            'risk': risk_level,
            'susceptible_crops': susceptible_nearby,
            'host_range_type': host_range.host_range_type.value
        }


def main():
    """Example usage"""
    classifier = MultiCropDiseaseClassifier()
    
    print("=== AgroPulse Multi-Crop Disease Classifier ===")
    print(f"\nMonitoring {len(classifier.disease_database)} cross-crop diseases")
    print(f"Family patterns: {len(classifier.family_patterns)} plant families")
    
    print("\n🔬 UNIVERSAL PATHOGENS (200+ hosts):")
    print("1. Botrytis Gray Mold")
    print("   - Gray fuzzy spores (universal diagnostic)")
    print("   - $10-100 billion annual losses")
    print("   - Affects: Strawberry, grape, tomato, pepper, lettuce, cucumber...")
    
    print("\n2. Powdery Mildew Complex")
    print("   - White powdery coating (universal diagnostic)")
    print("   - $2-3 billion annual losses")
    print("   - Affects: Grape, cucumber, strawberry, mango, peach, apple...")
    
    print("\n🧬 FAMILY-SPECIFIC PATTERNS:")
    print("• Solanaceae (tomato, potato, pepper, eggplant)")
    print("  - Late blight (ONLY Solanaceae)")
    print("  - Water-soaked lesions characteristic")
    
    print("\n• Cucurbitaceae (cucumber, watermelon)")
    print("  - Downy mildew + Powdery mildew (BOTH major)")
    print("  - Angular leaf spots (veins limit spread)")
    
    print("\n• Rosaceae (strawberry, apple, peach)")
    print("  - Fire blight bacterial (all Rosaceae)")
    print("  - Brown rot stone fruits")
    
    print("\n✅ SYSTEM STATUS: Ready for cross-crop analysis")


if __name__ == "__main__":
    main()
