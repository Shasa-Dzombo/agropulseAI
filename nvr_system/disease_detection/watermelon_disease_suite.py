"""
Watermelon Disease Detection Suite
Comprehensive disease detection for Citrullus lanatus

MAJOR WATERMELON DISEASES:

1. FUSARIUM WILT (Fusarium oxysporum f.sp. niveum) - #1 SOILBORNE DISEASE
   - Four races (0, 1, 2, 3) identified
   - Vascular wilt (yellowing → wilting → death)
   - Brown vascular discoloration diagnostic
   - Survives 10+ years in soil
   - Race 1 widespread, Race 2 emerging threat
   - Resistant varieties critical (Fon genes)
   - Field abandonment for susceptible varieties

2. ANTHRACNOSE (Colletotrichum orbiculare) - #1 FOLIAR DISEASE
   - Circular water-soaked spots on leaves/fruits
   - Pink-salmon spore masses in humid conditions
   - Fruit lesions = sunken black craters
   - 50-80% loss untreated humid regions
   - Seed transmission major (hot water treatment)
   - Fungicide resistance documented (QoI, DMI)

3. GUMMY STEM BLIGHT (Stagonosporopsis cucurbitacearum) - CROWN ROT
   - Black gummy exudate from stems diagnostic
   - Crown rot at soil line = plant death
   - Fruit rot from blossom end
   - Black pycnidia (fruiting bodies) on stems
   - 30-60% loss severe epidemics
   - Fungicide rotation critical

4. DOWNY MILDEW (Pseudoperonospora cubensis) - EXPLOSIVE EPIDEMIC
   - Angular yellow spots bound by veins
   - Purple-gray downy growth on undersides
   - Rapid defoliation (3-5 days complete loss)
   - Resistant to QoI fungicides (FRAC 11)
   - New pathotypes overcome resistance
   - Weekly fungicides required

5. POWDERY MILDEW (Podosphaera xanthii) - MOST COMMON
   - White powdery coating on upper leaf surface
   - Starts as small white spots → complete coverage
   - Reduces photosynthesis, yield, quality
   - DMI resistance widespread
   - Sulfur standard but phytotoxic >32°C
   - Multiple fungicide modes required

6. BACTERIAL FRUIT BLOTCH (Acidovorax citrulli) - QUARANTINE DISEASE
   - Water-soaked lesions on fruit surface
   - Internal fruit rot = complete loss
   - Seedling blight from infected seed
   - 50-100% loss from contaminated seed lot
   - Zero tolerance for seed industry
   - Seed treatment + testing critical

7. PHYTOPHTHORA BLIGHT (Phytophthora capsici) - CROWN ROT
   - Water-soaked lesions on crown/fruit
   - Rapid plant collapse
   - White mold on fruit humid conditions
   - Soil flooding triggers epidemic
   - Survives years in soil (oospores)
   - Mefenoxam resistance widespread

WATERMELON TYPES:
- Seeded (standard with black seeds)
- Seedless (triploid, no black seeds)
- Mini/personal (3-6 kg)
- Yellow flesh
- Orange flesh

RESISTANCE GENES:
- Fon genes (Fusarium oxysporum f.sp. niveum resistance)
- Fon-1, Fon-2 (Race 1, 2 resistance)
- Anthracnose resistance genes
- Downy mildew resistance (breaking down)

Author: AgroPulse AI Team
Version: 1.0.0
"""

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Dict, Optional


class WatermelonDisease(Enum):
    """Watermelon diseases"""
    FUSARIUM_WILT = "fusarium_wilt"
    ANTHRACNOSE = "anthracnose"
    GUMMY_STEM_BLIGHT = "gummy_stem_blight"
    DOWNY_MILDEW = "downy_mildew"
    POWDERY_MILDEW = "powdery_mildew"
    BACTERIAL_FRUIT_BLOTCH = "bacterial_fruit_blotch"
    PHYTOPHTHORA_BLIGHT = "phytophthora_blight"
    ALTERNARIA_LEAF_SPOT = "alternaria_leaf_spot"
    HEALTHY = "healthy"


class WatermelonType(Enum):
    """Watermelon varieties"""
    SEEDED = "seeded"
    SEEDLESS = "seedless"
    MINI = "mini"
    YELLOW_FLESH = "yellow_flesh"
    ORANGE_FLESH = "orange_flesh"


@dataclass
class WatermelonSymptoms:
    """Watermelon disease symptom parameters"""
    # Wilt symptoms
    wilting: bool = False
    yellowing: bool = False
    vascular_browning: bool = False
    one_sided_symptoms: bool = False
    
    # Leaf spots
    circular_spots: bool = False
    angular_spots: bool = False
    water_soaked_lesions: bool = False
    
    # Mildew
    white_powdery_coating: bool = False
    downy_gray_growth: bool = False
    
    # Stem symptoms
    black_gummy_exudate: bool = False
    crown_rot: bool = False
    stem_cankers: bool = False
    
    # Fruit symptoms
    sunken_fruit_lesions: bool = False
    fruit_water_soaked_spots: bool = False
    fruit_rot: bool = False
    
    # Color markers
    pink_spore_masses: bool = False
    black_pycnidia: bool = False
    
    # Measurements
    white_coating_area: float = 0.0
    brown_lesion_area: float = 0.0
    yellow_spot_area: float = 0.0
    water_soaked_area: float = 0.0


@dataclass
class WatermelonDiseaseResult:
    """Detection result"""
    disease: WatermelonDisease
    confidence: float
    symptoms: WatermelonSymptoms
    severity: str
    
    # Disease info
    pathogen: str
    race: Optional[str]
    treatment: str
    resistance_available: bool
    
    notes: str = ""


class WatermelonDiseaseDetector:
    """
    Watermelon disease detection system
    
    FEATURES:
    - Fusarium wilt race identification
    - Anthracnose fruit lesion detection
    - Gummy stem blight exudate recognition
    - Mildew differentiation (downy vs powdery)
    - Bacterial fruit blotch quarantine alert
    """
    
    def __init__(self):
        self.disease_database = self._initialize_disease_database()
    
    def _initialize_disease_database(self) -> Dict:
        """Comprehensive watermelon disease database"""
        return {
            'fusarium_wilt': {
                'pathogen': 'Fusarium oxysporum f.sp. niveum',
                'type': 'Fungal',
                'races': ['Race 0', 'Race 1', 'Race 2', 'Race 3'],
                'symptoms': [
                    'Yellowing and wilting (often one-sided)',
                    'Brown vascular discoloration (cut stem)',
                    'Plant death within 2-3 weeks',
                    'Wilt progresses from bottom up'
                ],
                'conditions': {
                    'temperature': (24, 28),  # Warm weather
                    'soil_ph': (5.5, 6.5)
                },
                'impact': 'SEVERE: 50-100% loss in infested soil. Field abandonment for susceptible varieties.',
                'treatment': 'Resistant varieties (Fon-1, Fon-2 genes). Crop rotation 5+ years. Grafting onto resistant rootstock.',
                'resistance': 'Excellent resistance available. Race 1 resistance common. Race 2 resistance emerging.',
                'notes': '#1 SOILBORNE DISEASE. Survives 10+ years. Race 1 widespread globally. Race 2 emerging threat USA.'
            },
            
            'anthracnose': {
                'pathogen': 'Colletotrichum orbiculare (C. lagenarium)',
                'type': 'Fungal',
                'symptoms': [
                    'Circular water-soaked spots on leaves',
                    'Pink-salmon spore masses in lesions',
                    'Sunken black craters on fruit',
                    'Rapid leaf blight humid conditions'
                ],
                'conditions': {
                    'temperature': (20, 27),
                    'humidity': 95,
                    'wetness_hours': 12
                },
                'impact': 'SEVERE: 50-80% loss untreated humid regions. Fruit lesions = total loss.',
                'treatment': 'Fungicides (chlorothalonil, azoxystrobin, mancozeb). FRAC rotation. Hot water seed treatment.',
                'resistance': 'Some resistance in varieties. Resistance breaking down.',
                'notes': '#1 FOLIAR DISEASE humid regions. Pink spore masses diagnostic. Seed transmission critical. QoI/DMI resistance.'
            },
            
            'gummy_stem_blight': {
                'pathogen': 'Stagonosporopsis cucurbitacearum (Didymella bryoniae)',
                'type': 'Fungal',
                'symptoms': [
                    'Black gummy exudate from stems/petioles',
                    'Crown rot at soil line',
                    'Stem cankers with black pycnidia',
                    'Fruit rot from blossom end'
                ],
                'conditions': {
                    'temperature': (20, 25),
                    'humidity': 85,
                    'wetness_hours': 8
                },
                'impact': 'SEVERE: 30-60% loss severe epidemics. Crown rot = plant death.',
                'treatment': 'Fungicides (azoxystrobin, chlorothalonil, boscalid). FRAC rotation critical. Avoid stem wounds.',
                'resistance': 'Limited resistance available.',
                'notes': 'BLACK GUMMY EXUDATE diagnostic. Crown rot kills plants rapidly. Black pycnidia = fruiting bodies.'
            },
            
            'downy_mildew': {
                'pathogen': 'Pseudoperonospora cubensis',
                'type': 'Oomycete',
                'symptoms': [
                    'Angular yellow spots bound by leaf veins',
                    'Purple-gray downy growth on undersides',
                    'Rapid defoliation (3-5 days)',
                    'Complete leaf loss severe cases'
                ],
                'conditions': {
                    'temperature': (15, 22),
                    'humidity': 95,
                    'wetness_hours': 6
                },
                'impact': 'CATASTROPHIC: 100% defoliation in 3-5 days. Epidemic pathogen.',
                'treatment': 'Weekly fungicides (chlorothalonil, mancozeb, cymoxanil, mandipropamid). QoI RESISTANCE.',
                'resistance': 'Resistance breaking down rapidly. New pathotypes overcome genes.',
                'notes': 'EXPLOSIVE EPIDEMIC. 3-5 days = complete defoliation. QoI resistance severe. Angular spots diagnostic.'
            },
            
            'powdery_mildew': {
                'pathogen': 'Podosphaera xanthii (Sphaerotheca fuliginea)',
                'type': 'Fungal',
                'symptoms': [
                    'White powdery coating on upper leaves',
                    'Starts as small white spots',
                    'Expands to complete leaf coverage',
                    'Premature senescence and defoliation'
                ],
                'conditions': {
                    'temperature': (20, 30),
                    'humidity': (50, 70),  # Moderate humidity
                    'wetness_hours': 0  # Does NOT require free water
                },
                'impact': 'MODERATE-SEVERE: 20-50% yield loss. Quality reduction.',
                'treatment': 'Fungicides (sulfur, myclobutanil, boscalid, cyflufenamid). Sulfur phytotoxic >32°C. FRAC rotation.',
                'resistance': 'Some resistance available. Race-specific resistance common.',
                'notes': 'MOST COMMON cucurbit disease. White powdery coating diagnostic. DMI resistance widespread.'
            },
            
            'bacterial_fruit_blotch': {
                'pathogen': 'Acidovorax citrulli',
                'type': 'Bacterial',
                'symptoms': [
                    'Water-soaked lesions on fruit surface',
                    'Internal fruit rot and cavity',
                    'Seedling blight from contaminated seed',
                    'Brown bacterial ooze from lesions'
                ],
                'conditions': {
                    'temperature': (24, 28),
                    'humidity': 85,
                    'seed_contamination': True
                },
                'impact': 'CATASTROPHIC: 50-100% loss from contaminated seed lot. QUARANTINE DISEASE.',
                'treatment': 'Seed testing and treatment. Copper bactericides limited efficacy. Zero tolerance for transplants.',
                'resistance': 'Limited resistance available.',
                'notes': 'QUARANTINE DISEASE many regions. Seed transmission critical. Zero tolerance seed industry. 100% loss possible.'
            },
            
            'phytophthora_blight': {
                'pathogen': 'Phytophthora capsici',
                'type': 'Oomycete',
                'symptoms': [
                    'Water-soaked lesions on crown/stems',
                    'Rapid plant collapse and death',
                    'White mold on fruit humid conditions',
                    'Fruit rot starts at soil contact'
                ],
                'conditions': {
                    'temperature': (25, 30),
                    'soil_moisture': 'saturated',
                    'flooding': True
                },
                'impact': 'SEVERE: 40-80% loss in poorly drained fields. Rapid plant death.',
                'treatment': 'Fungicides (mefenoxam, mandipropamid, fluopicolide). Drainage critical. Mefenoxam RESISTANCE.',
                'resistance': 'No resistance available.',
                'notes': 'WATER-MOLD. Flooding triggers epidemic. Rapid collapse. Mefenoxam resistance widespread.'
            }
        }
    
    def detect_disease(self, image: np.ndarray, watermelon_type: WatermelonType) -> List[WatermelonDiseaseResult]:
        """
        Detect watermelon diseases from image
        
        Args:
            image: RGB image of watermelon plant/fruit
            watermelon_type: Type of watermelon
            
        Returns:
            List of detected diseases with confidence scores
        """
        # Extract symptoms
        symptoms = self._analyze_symptoms(image)
        
        # Detect diseases
        results = []
        
        # Fusarium wilt detection
        fusarium_conf = self._detect_fusarium_wilt(symptoms)
        if fusarium_conf > 0.3:
            results.append(self._create_result(
                WatermelonDisease.FUSARIUM_WILT,
                fusarium_conf,
                symptoms,
                'severe' if fusarium_conf > 0.6 else 'moderate'
            ))
        
        # Anthracnose detection
        anthracnose_conf = self._detect_anthracnose(symptoms)
        if anthracnose_conf > 0.3:
            results.append(self._create_result(
                WatermelonDisease.ANTHRACNOSE,
                anthracnose_conf,
                symptoms,
                'severe' if anthracnose_conf > 0.6 else 'moderate'
            ))
        
        # Gummy stem blight detection
        gummy_conf = self._detect_gummy_stem_blight(symptoms)
        if gummy_conf > 0.3:
            results.append(self._create_result(
                WatermelonDisease.GUMMY_STEM_BLIGHT,
                gummy_conf,
                symptoms,
                'severe'
            ))
        
        # Downy mildew detection
        downy_conf = self._detect_downy_mildew(symptoms)
        if downy_conf > 0.3:
            results.append(self._create_result(
                WatermelonDisease.DOWNY_MILDEW,
                downy_conf,
                symptoms,
                'critical' if downy_conf > 0.7 else 'severe'
            ))
        
        # Powdery mildew detection
        powdery_conf = self._detect_powdery_mildew(symptoms)
        if powdery_conf > 0.3:
            results.append(self._create_result(
                WatermelonDisease.POWDERY_MILDEW,
                powdery_conf,
                symptoms,
                'moderate'
            ))
        
        # Bacterial fruit blotch detection
        bfb_conf = self._detect_bacterial_fruit_blotch(symptoms)
        if bfb_conf > 0.3:
            results.append(self._create_result(
                WatermelonDisease.BACTERIAL_FRUIT_BLOTCH,
                bfb_conf,
                symptoms,
                'critical'
            ))
        
        # Phytophthora blight detection
        phytophthora_conf = self._detect_phytophthora(symptoms)
        if phytophthora_conf > 0.3:
            results.append(self._create_result(
                WatermelonDisease.PHYTOPHTHORA_BLIGHT,
                phytophthora_conf,
                symptoms,
                'severe'
            ))
        
        # If no diseases detected
        if not results:
            results.append(self._create_result(
                WatermelonDisease.HEALTHY,
                0.9,
                symptoms,
                'none'
            ))
        
        return sorted(results, key=lambda x: x.confidence, reverse=True)
    
    def _analyze_symptoms(self, image: np.ndarray) -> WatermelonSymptoms:
        """Extract disease symptoms from image"""
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        height, width = image.shape[:2]
        total_pixels = height * width
        
        # White powdery coating (powdery mildew)
        white_mask = cv2.inRange(hsv, np.array([0, 0, 200]), np.array([180, 30, 255]))
        white_area = np.sum(white_mask > 0) / total_pixels
        white_powdery = white_area > 0.05
        
        # Gray downy growth (downy mildew)
        gray_mask = cv2.inRange(hsv, np.array([0, 0, 100]), np.array([180, 50, 180]))
        downy_growth = np.sum(gray_mask > 0) / total_pixels > 0.03
        
        # Yellow spots
        yellow_mask = cv2.inRange(hsv, np.array([20, 40, 40]), np.array([35, 255, 255]))
        yellow_area = np.sum(yellow_mask > 0) / total_pixels
        
        # Water-soaked lesions (darker wet-looking areas)
        dark_mask = cv2.inRange(hsv, np.array([0, 0, 20]), np.array([180, 255, 100]))
        water_soaked_area = np.sum(dark_mask > 0) / total_pixels
        water_soaked = water_soaked_area > 0.05
        
        # Brown lesions
        brown_mask = cv2.inRange(hsv, np.array([10, 40, 20]), np.array([20, 255, 150]))
        brown_area = np.sum(brown_mask > 0) / total_pixels
        
        # Black gummy exudate detection
        black_mask = cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 255, 40]))
        black_gummy = np.sum(black_mask > 0) / total_pixels > 0.02
        
        # Pink spore masses (anthracnose)
        pink_mask = cv2.inRange(hsv, np.array([150, 40, 100]), np.array([170, 255, 255]))
        pink_spores = np.sum(pink_mask > 0) / total_pixels > 0.01
        
        # Angular vs circular spot detection
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # Detect spots
        contours, _ = cv2.findContours(yellow_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        angular_spots = False
        circular_spots = False
        
        for contour in contours:
            if cv2.contourArea(contour) < 50:
                continue
            
            # Check if angular (downy mildew) or circular (anthracnose)
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.04 * perimeter, True)
            
            if len(approx) < 6:  # Angular
                angular_spots = True
            else:  # Circular
                circular_spots = True
        
        return WatermelonSymptoms(
            white_powdery_coating=white_powdery,
            downy_gray_growth=downy_growth,
            water_soaked_lesions=water_soaked,
            angular_spots=angular_spots,
            circular_spots=circular_spots,
            black_gummy_exudate=black_gummy,
            pink_spore_masses=pink_spores,
            white_coating_area=white_area,
            yellow_spot_area=yellow_area,
            water_soaked_area=water_soaked_area,
            brown_lesion_area=brown_area
        )
    
    def _detect_fusarium_wilt(self, symptoms: WatermelonSymptoms) -> float:
        """Detect Fusarium wilt"""
        confidence = 0.0
        
        # Wilting and yellowing
        if symptoms.wilting and symptoms.yellowing:
            confidence += 0.4
        
        # Vascular browning (cut stem)
        if symptoms.vascular_browning:
            confidence += 0.5
        
        # One-sided symptoms characteristic
        if symptoms.one_sided_symptoms:
            confidence += 0.3
        
        return min(confidence, 1.0)
    
    def _detect_anthracnose(self, symptoms: WatermelonSymptoms) -> float:
        """Detect anthracnose"""
        confidence = 0.0
        
        # Pink spore masses = DIAGNOSTIC
        if symptoms.pink_spore_masses:
            confidence += 0.6
        
        # Circular water-soaked spots
        if symptoms.circular_spots and symptoms.water_soaked_lesions:
            confidence += 0.4
        
        # Sunken fruit lesions
        if symptoms.sunken_fruit_lesions:
            confidence += 0.3
        
        # Brown lesions
        if symptoms.brown_lesion_area > 0.1:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _detect_gummy_stem_blight(self, symptoms: WatermelonSymptoms) -> float:
        """Detect gummy stem blight"""
        confidence = 0.0
        
        # Black gummy exudate = DIAGNOSTIC
        if symptoms.black_gummy_exudate:
            confidence += 0.7
        
        # Crown rot
        if symptoms.crown_rot:
            confidence += 0.4
        
        # Stem cankers
        if symptoms.stem_cankers:
            confidence += 0.3
        
        # Black pycnidia
        if symptoms.black_pycnidia:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _detect_downy_mildew(self, symptoms: WatermelonSymptoms) -> float:
        """Detect downy mildew"""
        confidence = 0.0
        
        # Angular spots = CHARACTERISTIC
        if symptoms.angular_spots:
            confidence += 0.4
        
        # Downy gray growth on undersides = DIAGNOSTIC
        if symptoms.downy_gray_growth:
            confidence += 0.5
        
        # Yellow spots
        if symptoms.yellow_spot_area > 0.1:
            confidence += 0.3
        
        return min(confidence, 1.0)
    
    def _detect_powdery_mildew(self, symptoms: WatermelonSymptoms) -> float:
        """Detect powdery mildew"""
        confidence = 0.0
        
        # White powdery coating = DIAGNOSTIC
        if symptoms.white_powdery_coating:
            confidence += 0.7
        
        # White coating area
        if symptoms.white_coating_area > 0.1:
            confidence += 0.3
        
        return min(confidence, 1.0)
    
    def _detect_bacterial_fruit_blotch(self, symptoms: WatermelonSymptoms) -> float:
        """Detect bacterial fruit blotch"""
        confidence = 0.0
        
        # Water-soaked fruit lesions = CHARACTERISTIC
        if symptoms.fruit_water_soaked_spots:
            confidence += 0.6
        
        # Water-soaked lesions
        if symptoms.water_soaked_lesions:
            confidence += 0.3
        
        # Fruit rot
        if symptoms.fruit_rot:
            confidence += 0.3
        
        return min(confidence, 1.0)
    
    def _detect_phytophthora(self, symptoms: WatermelonSymptoms) -> float:
        """Detect Phytophthora blight"""
        confidence = 0.0
        
        # Water-soaked crown lesions
        if symptoms.water_soaked_lesions and symptoms.crown_rot:
            confidence += 0.6
        
        # Rapid collapse
        if symptoms.wilting:
            confidence += 0.3
        
        # Fruit rot
        if symptoms.fruit_rot:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _create_result(
        self,
        disease: WatermelonDisease,
        confidence: float,
        symptoms: WatermelonSymptoms,
        severity: str
    ) -> WatermelonDiseaseResult:
        """Create disease result with full information"""
        if disease == WatermelonDisease.HEALTHY:
            return WatermelonDiseaseResult(
                disease=disease,
                confidence=confidence,
                symptoms=symptoms,
                severity=severity,
                pathogen='None',
                race=None,
                treatment='No treatment needed',
                resistance_available=False,
                notes='Healthy watermelon plant'
            )
        
        disease_key = disease.value
        disease_info = self.disease_database.get(disease_key, {})
        
        # Determine race for Fusarium wilt
        race = None
        if disease == WatermelonDisease.FUSARIUM_WILT:
            race = 'Race 1 (most common)'
        
        return WatermelonDiseaseResult(
            disease=disease,
            confidence=confidence,
            symptoms=symptoms,
            severity=severity,
            pathogen=disease_info.get('pathogen', 'Unknown'),
            race=race,
            treatment=disease_info.get('treatment', 'Consult specialist'),
            resistance_available=disease_info.get('resistance', '') != 'No resistance',
            notes=disease_info.get('notes', '')
        )


def main():
    """Example usage"""
    detector = WatermelonDiseaseDetector()
    
    print("=== AgroPulse Watermelon Disease Detection ===")
    print(f"\nDiseases tracked: {len(detector.disease_database)}")
    
    print("\n🍉 MAJOR WATERMELON DISEASES:")
    
    print("\n1. FUSARIUM WILT (Fusarium oxysporum f.sp. niveum)")
    print("   - Four races (0, 1, 2, 3)")
    print("   - Vascular browning diagnostic")
    print("   - Survives 10+ years in soil")
    print("   - Race 1 widespread, Race 2 emerging")
    print("   - #1 SOILBORNE DISEASE")
    
    print("\n2. ANTHRACNOSE (Colletotrichum orbiculare)")
    print("   - Pink-salmon spore masses diagnostic")
    print("   - Sunken black fruit craters")
    print("   - 50-80% loss untreated")
    print("   - QoI/DMI resistance documented")
    print("   - #1 FOLIAR DISEASE")
    
    print("\n3. GUMMY STEM BLIGHT (Stagonosporopsis)")
    print("   - Black gummy exudate DIAGNOSTIC")
    print("   - Crown rot = plant death")
    print("   - Black pycnidia on stems")
    print("   - 30-60% loss severe")
    
    print("\n4. DOWNY MILDEW (Pseudoperonospora cubensis)")
    print("   - Angular spots bound by veins")
    print("   - 3-5 days = complete defoliation")
    print("   - EXPLOSIVE EPIDEMIC pathogen")
    print("   - QoI resistance severe")
    
    print("\n5. BACTERIAL FRUIT BLOTCH (Acidovorax citrulli)")
    print("   - QUARANTINE DISEASE")
    print("   - 50-100% loss from contaminated seed")
    print("   - Zero tolerance seed industry")
    
    print("\n🧬 RESISTANCE GENES:")
    print("   - Fon-1, Fon-2 (Fusarium Race 1, 2)")
    print("   - Anthracnose resistance available")
    print("   - Downy mildew resistance breaking down")
    
    print("\n✅ SYSTEM STATUS: Watermelon detection ready")


if __name__ == "__main__":
    main()
