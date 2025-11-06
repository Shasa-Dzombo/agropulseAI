"""
Cabbage Disease Detection Suite
Comprehensive disease detection for Brassica oleracea var. capitata

MAJOR CABBAGE DISEASES:

1. BLACK ROT (Xanthomonas campestris pv. campestris) - #1 BACTERIAL DISEASE
   - V-shaped yellow lesions from leaf margin
   - Blackened veins diagnostic (vascular pathogen)
   - Systemic infection from seedling stage
   - 70-80% loss severe epidemics
   - Seed transmission critical (hot water treatment 50°C 25min)
   - Zero tolerance for transplants (discard infected)

2. CLUBROOT (Plasmodiophora brassicae) - MOST DEVASTATING
   - Swollen distorted roots (club-shaped galls)
   - Stunting, wilting, yellowing above ground
   - Soil pH <7.2 favors disease (liming = control strategy)
   - Survives 20+ YEARS in soil as resting spores
   - Field abandonment for brassicas
   - Resistant varieties critical (CR genes)

3. DOWNY MILDEW (Peronospora parasitica) - SEEDLING KILLER
   - White-gray downy growth on leaf undersides
   - Yellow angular leaf spots upper surface
   - Cool humid conditions (10-15°C optimal)
   - Seed treatment + fungicides
   - Systemic infection from cotyledons

4. ALTERNARIA LEAF SPOT (Alternaria brassicicola/brassicae)
   - Circular spots with concentric rings (target spot)
   - Black sooty mold on older lesions
   - Seed transmission (major spread mechanism)
   - Storage rots from field infections
   - Hot water seed treatment

5. FUSARIUM YELLOWS (Fusarium oxysporum f.sp. conglutinans)
   - One-sided yellowing initially
   - Vascular browning (cut stem shows brown streaks)
   - Warm weather disease (24-28°C)
   - Soilborne, survives years
   - Race 1 and Race 2 (resistance genes available)

6. WHITE RUST (Albugo candida) - WHITE PUSTULES
   - White chalky pustules on leaves/stems
   - Leaf distortion, systemic infection
   - Cool humid conditions
   - Often mixed with downy mildew

7. WIRESTEM (Rhizoctonia solani) - DAMPING OFF
   - Stem constriction at soil line
   - Wire-like hardened stems
   - Seedling death or stunted plants
   - Damping off in nursery

CABBAGE TYPES:
- Green cabbage (most common)
- Red/Purple cabbage (anthocyanin pigment)
- Savoy cabbage (crinkled leaves)
- Napa cabbage (Chinese cabbage)
- Bok choy (Chinese cabbage type)

RESISTANCE GENES:
- CR genes (clubroot resistance) - multiple loci
- Race-specific resistance vs P. brassicae pathotypes
- Fusarium yellows: Type A, B, C resistance

Author: AgroPulse AI Team
Version: 1.0.0
"""

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Dict, Optional


class CabbageDisease(Enum):
    """Cabbage diseases"""
    BLACK_ROT = "black_rot"
    CLUBROOT = "clubroot"
    DOWNY_MILDEW = "downy_mildew"
    ALTERNARIA_LEAF_SPOT = "alternaria_leaf_spot"
    FUSARIUM_YELLOWS = "fusarium_yellows"
    WHITE_RUST = "white_rust"
    WIRESTEM = "wirestem"
    BACTERIAL_SOFT_ROT = "bacterial_soft_rot"
    HEALTHY = "healthy"


class CabbageType(Enum):
    """Cabbage varieties"""
    GREEN_CABBAGE = "green_cabbage"
    RED_CABBAGE = "red_cabbage"
    SAVOY_CABBAGE = "savoy_cabbage"
    NAPA_CABBAGE = "napa_cabbage"
    BOK_CHOY = "bok_choy"


@dataclass
class CabbageSymptoms:
    """Cabbage disease symptom parameters"""
    # V-shaped lesions (black rot)
    v_shaped_lesions: bool = False
    lesion_from_margin: bool = False
    blackened_veins: bool = False
    
    # Root symptoms (clubroot)
    root_galls: bool = False
    swollen_roots: bool = False
    club_shaped_roots: bool = False
    
    # Leaf spots
    circular_spots: bool = False
    concentric_rings: bool = False
    target_spot_pattern: bool = False
    angular_spots: bool = False
    
    # Mildew
    downy_growth_underside: bool = False
    white_chalky_pustules: bool = False
    
    # Wilting and yellowing
    one_sided_yellowing: bool = False
    vascular_browning: bool = False
    stunting: bool = False
    wilting: bool = False
    
    # Stem symptoms
    stem_constriction: bool = False
    wire_like_stem: bool = False
    damping_off: bool = False
    
    # Color analysis
    yellow_lesion_area: float = 0.0
    brown_lesion_area: float = 0.0
    black_vein_area: float = 0.0
    white_pustule_area: float = 0.0


@dataclass
class CabbageDiseaseResult:
    """Detection result"""
    disease: CabbageDisease
    confidence: float
    symptoms: CabbageSymptoms
    severity: str
    
    # Disease info
    pathogen: str
    treatment: str
    resistance_available: bool
    
    notes: str = ""


class CabbageDiseaseDetector:
    """
    Cabbage disease detection system
    
    FEATURES:
    - Black rot V-shaped lesion detection
    - Clubroot root gall identification
    - Downy mildew detection
    - Alternaria target spot recognition
    - Fusarium vascular wilt
    """
    
    def __init__(self):
        self.disease_database = self._initialize_disease_database()
    
    def _initialize_disease_database(self) -> Dict:
        """Comprehensive cabbage disease database"""
        return {
            'black_rot': {
                'pathogen': 'Xanthomonas campestris pv. campestris',
                'type': 'Bacterial',
                'symptoms': [
                    'V-shaped yellow lesions from leaf margin',
                    'Blackened veins (vascular infection)',
                    'Systemic spread from infection point',
                    'Leaf drop severe infections'
                ],
                'conditions': {
                    'temperature': (24, 30),  # 24-30°C optimal
                    'humidity': 85,
                    'wetness_hours': 4
                },
                'impact': 'SEVERE: 70-80% loss in epidemics. Seed transmission critical.',
                'treatment': 'Copper bactericides (limited efficacy). Hot water seed treatment 50°C 25min. Resistant varieties.',
                'resistance': 'Limited resistance available. Mainly cultural control.',
                'notes': '#1 BACTERIAL DISEASE of cabbage worldwide. V-shaped lesions diagnostic. Zero tolerance for transplants.'
            },
            
            'clubroot': {
                'pathogen': 'Plasmodiophora brassicae',
                'type': 'Protist (Obligate parasite)',
                'symptoms': [
                    'Swollen distorted roots (clubs/galls)',
                    'Stunting and wilting above ground',
                    'Yellowing and premature senescence',
                    'Poor head formation or no head'
                ],
                'conditions': {
                    'temperature': (18, 25),
                    'soil_ph': (5.5, 6.8),  # Acid soils favor
                    'soil_moisture': 'high'
                },
                'impact': 'CATASTROPHIC: Field abandoned for brassicas 20+ years. 100% loss in infested soil.',
                'treatment': 'Soil liming pH >7.2. Long rotations (7+ years). Resistant varieties (CR genes). Soil fumigation limited.',
                'resistance': 'CR resistance genes available. Race-specific resistance (pathotypes A-P identified).',
                'notes': 'MOST DEVASTATING brassica disease. Survives 20+ years as resting spores. Liming = key control.'
            },
            
            'downy_mildew': {
                'pathogen': 'Peronospora parasitica (Hyaloperonospora parasitica)',
                'type': 'Oomycete',
                'symptoms': [
                    'White-gray downy growth on leaf undersides',
                    'Yellow angular spots on upper leaf surface',
                    'Seedling death (damping off)',
                    'Systemic infection from cotyledons'
                ],
                'conditions': {
                    'temperature': (10, 15),  # Cool conditions
                    'humidity': 95,
                    'wetness_hours': 6
                },
                'impact': 'SEVERE: Seedling killer. 80-100% loss in nursery without control.',
                'treatment': 'Fungicides (mancozeb, copper, fosetyl-Al). Seed treatment. Greenhouse ventilation.',
                'resistance': 'Some resistance in modern varieties.',
                'notes': 'SEEDLING KILLER. Cool humid conditions. Seed transmission. Systemic infection serious.'
            },
            
            'alternaria_leaf_spot': {
                'pathogen': 'Alternaria brassicicola / Alternaria brassicae',
                'type': 'Fungal',
                'symptoms': [
                    'Circular spots with concentric rings (target spot)',
                    'Black sooty mold on older lesions',
                    'Leaf drop and defoliation',
                    'Storage rots from field infections'
                ],
                'conditions': {
                    'temperature': (16, 24),
                    'humidity': 85,
                    'wetness_hours': 8
                },
                'impact': 'MODERATE: 10-30% loss. Storage rot = post-harvest loss 20-50%.',
                'treatment': 'Fungicides (azoxystrobin, chlorothalonil, mancozeb). Hot water seed treatment. Crop rotation.',
                'resistance': 'Limited resistance available.',
                'notes': 'TARGET SPOT pattern diagnostic. Seed transmission major. Storage rots from field infections.'
            },
            
            'fusarium_yellows': {
                'pathogen': 'Fusarium oxysporum f.sp. conglutinans',
                'type': 'Fungal',
                'symptoms': [
                    'One-sided yellowing (starts one side of plant)',
                    'Vascular browning (cut stem shows streaks)',
                    'Stunting and poor head development',
                    'Premature death severe cases'
                ],
                'conditions': {
                    'temperature': (24, 28),  # Warm weather
                    'soil_ph': (5.5, 7.0),
                    'soil_moisture': 'moderate'
                },
                'impact': 'SEVERE: 50-80% loss in infested fields warm regions.',
                'treatment': 'Resistant varieties (Type A, B, C resistance). Long rotation. Soil solarization.',
                'resistance': 'Excellent resistance available. Type A, B, C resistance vs Race 1 and 2.',
                'notes': 'WARM WEATHER DISEASE. Vascular wilt (cut stem = brown streaks). Resistant varieties highly effective.'
            },
            
            'white_rust': {
                'pathogen': 'Albugo candida',
                'type': 'Oomycete',
                'symptoms': [
                    'White chalky pustules on leaves/stems',
                    'Leaf distortion and thickening',
                    'Systemic infection (white "stagheads")',
                    'Often mixed with downy mildew'
                ],
                'conditions': {
                    'temperature': (10, 18),
                    'humidity': 90,
                    'wetness_hours': 4
                },
                'impact': 'MODERATE: 10-30% loss. Cosmetic damage mainly.',
                'treatment': 'Fungicides for downy mildew also control white rust. Mancozeb, copper.',
                'resistance': 'Some resistance in varieties.',
                'notes': 'WHITE PUSTULES diagnostic. Cool humid conditions. Often co-infects with downy mildew.'
            },
            
            'wirestem': {
                'pathogen': 'Rhizoctonia solani',
                'type': 'Fungal',
                'symptoms': [
                    'Stem constriction at soil line',
                    'Wire-like hardened brown stems',
                    'Seedling death (damping off)',
                    'Stunted plants if survive'
                ],
                'conditions': {
                    'temperature': (15, 24),
                    'soil_moisture': 'high',
                    'poor_drainage': True
                },
                'impact': 'MODERATE: 20-40% seedling loss in nursery.',
                'treatment': 'Fungicides (azoxystrobin, flutolanil). Improve drainage. Avoid overwatering.',
                'resistance': 'No resistance. Cultural control critical.',
                'notes': 'WIRE-LIKE STEM diagnostic. Damping off pathogen. Nursery problem mainly.'
            }
        }
    
    def detect_disease(self, image: np.ndarray, cabbage_type: CabbageType) -> List[CabbageDiseaseResult]:
        """
        Detect cabbage diseases from image
        
        Args:
            image: RGB image of cabbage plant
            cabbage_type: Type of cabbage
            
        Returns:
            List of detected diseases with confidence scores
        """
        # Extract symptoms
        symptoms = self._analyze_symptoms(image)
        
        # Detect diseases
        results = []
        
        # Black rot detection
        black_rot_conf = self._detect_black_rot(symptoms)
        if black_rot_conf > 0.3:
            results.append(self._create_result(
                CabbageDisease.BLACK_ROT,
                black_rot_conf,
                symptoms,
                'severe' if black_rot_conf > 0.7 else 'moderate'
            ))
        
        # Clubroot detection
        clubroot_conf = self._detect_clubroot(symptoms)
        if clubroot_conf > 0.4:
            results.append(self._create_result(
                CabbageDisease.CLUBROOT,
                clubroot_conf,
                symptoms,
                'severe'
            ))
        
        # Downy mildew detection
        downy_conf = self._detect_downy_mildew(symptoms)
        if downy_conf > 0.3:
            results.append(self._create_result(
                CabbageDisease.DOWNY_MILDEW,
                downy_conf,
                symptoms,
                'severe' if downy_conf > 0.6 else 'moderate'
            ))
        
        # Alternaria detection
        alternaria_conf = self._detect_alternaria(symptoms)
        if alternaria_conf > 0.3:
            results.append(self._create_result(
                CabbageDisease.ALTERNARIA_LEAF_SPOT,
                alternaria_conf,
                symptoms,
                'moderate'
            ))
        
        # Fusarium yellows detection
        fusarium_conf = self._detect_fusarium_yellows(symptoms)
        if fusarium_conf > 0.3:
            results.append(self._create_result(
                CabbageDisease.FUSARIUM_YELLOWS,
                fusarium_conf,
                symptoms,
                'severe' if fusarium_conf > 0.6 else 'moderate'
            ))
        
        # White rust detection
        white_rust_conf = self._detect_white_rust(symptoms)
        if white_rust_conf > 0.3:
            results.append(self._create_result(
                CabbageDisease.WHITE_RUST,
                white_rust_conf,
                symptoms,
                'moderate'
            ))
        
        # If no diseases detected
        if not results:
            results.append(self._create_result(
                CabbageDisease.HEALTHY,
                0.9,
                symptoms,
                'none'
            ))
        
        return sorted(results, key=lambda x: x.confidence, reverse=True)
    
    def _analyze_symptoms(self, image: np.ndarray) -> CabbageSymptoms:
        """Extract disease symptoms from image"""
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        height, width = image.shape[:2]
        total_pixels = height * width
        
        # V-shaped lesion detection (black rot)
        yellow_mask = cv2.inRange(hsv, np.array([20, 40, 40]), np.array([35, 255, 255]))
        v_shaped = self._detect_v_shaped_lesions(yellow_mask)
        
        # Black vein detection
        black_mask = cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 255, 50]))
        black_vein_area = np.sum(black_mask > 0) / total_pixels
        blackened_veins = black_vein_area > 0.02
        
        # White pustule detection (white rust)
        white_mask = cv2.inRange(hsv, np.array([0, 0, 200]), np.array([180, 30, 255]))
        white_pustule_area = np.sum(white_mask > 0) / total_pixels
        
        # Target spot detection (alternaria)
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1, 20,
                                   param1=50, param2=30, minRadius=5, maxRadius=50)
        target_spots = circles is not None and len(circles[0]) > 3
        
        # Concentric rings (alternaria)
        edges = cv2.Canny(gray, 50, 150)
        concentric = np.sum(edges > 0) / total_pixels > 0.1
        
        # Downy mildew (white-gray fuzzy growth)
        gray_fuzzy_mask = cv2.inRange(hsv, np.array([0, 0, 150]), np.array([180, 50, 220]))
        downy_growth = np.sum(gray_fuzzy_mask > 0) / total_pixels > 0.05
        
        # Yellow lesion area
        yellow_area = np.sum(yellow_mask > 0) / total_pixels
        
        # Brown lesion area
        brown_mask = cv2.inRange(hsv, np.array([10, 40, 20]), np.array([20, 255, 150]))
        brown_area = np.sum(brown_mask > 0) / total_pixels
        
        return CabbageSymptoms(
            v_shaped_lesions=v_shaped,
            lesion_from_margin=v_shaped,
            blackened_veins=blackened_veins,
            circular_spots=target_spots,
            concentric_rings=concentric,
            target_spot_pattern=target_spots and concentric,
            downy_growth_underside=downy_growth,
            white_chalky_pustules=white_pustule_area > 0.03,
            yellow_lesion_area=yellow_area,
            brown_lesion_area=brown_area,
            black_vein_area=black_vein_area,
            white_pustule_area=white_pustule_area
        )
    
    def _detect_v_shaped_lesions(self, mask: np.ndarray) -> bool:
        """Detect V-shaped lesions characteristic of black rot"""
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            if cv2.contourArea(contour) < 100:
                continue
            
            # Fit polygon
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # V-shape has roughly triangular appearance
            if len(approx) >= 3:
                # Check if shape is elongated (V-shaped from margin)
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = float(w) / h if h > 0 else 0
                
                if 0.3 < aspect_ratio < 3.0:  # Elongated shape
                    return True
        
        return False
    
    def _detect_black_rot(self, symptoms: CabbageSymptoms) -> float:
        """Detect black rot (Xanthomonas)"""
        confidence = 0.0
        
        # V-shaped lesions from margin = PATHOGNOMONIC
        if symptoms.v_shaped_lesions:
            confidence += 0.5
        
        # Blackened veins = DIAGNOSTIC
        if symptoms.blackened_veins:
            confidence += 0.4
        
        # Yellow lesion area
        if symptoms.yellow_lesion_area > 0.05:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _detect_clubroot(self, symptoms: CabbageSymptoms) -> float:
        """Detect clubroot (requires root inspection)"""
        confidence = 0.0
        
        # Root galls diagnostic
        if symptoms.root_galls or symptoms.swollen_roots:
            confidence += 0.8
        
        # Above-ground symptoms (stunting, wilting)
        if symptoms.stunting and symptoms.wilting:
            confidence += 0.3
        
        # One-sided yellowing sometimes
        if symptoms.one_sided_yellowing:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _detect_downy_mildew(self, symptoms: CabbageSymptoms) -> float:
        """Detect downy mildew"""
        confidence = 0.0
        
        # Downy growth on undersides = DIAGNOSTIC
        if symptoms.downy_growth_underside:
            confidence += 0.6
        
        # Angular spots
        if symptoms.angular_spots:
            confidence += 0.3
        
        # Yellow lesion area
        if symptoms.yellow_lesion_area > 0.1:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _detect_alternaria(self, symptoms: CabbageSymptoms) -> float:
        """Detect Alternaria leaf spot"""
        confidence = 0.0
        
        # Target spot pattern = DIAGNOSTIC
        if symptoms.target_spot_pattern:
            confidence += 0.6
        
        # Concentric rings
        if symptoms.concentric_rings:
            confidence += 0.3
        
        # Circular spots
        if symptoms.circular_spots:
            confidence += 0.2
        
        # Brown lesions
        if symptoms.brown_lesion_area > 0.05:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _detect_fusarium_yellows(self, symptoms: CabbageSymptoms) -> float:
        """Detect Fusarium yellows"""
        confidence = 0.0
        
        # One-sided yellowing = CHARACTERISTIC
        if symptoms.one_sided_yellowing:
            confidence += 0.5
        
        # Vascular browning (cut stem)
        if symptoms.vascular_browning:
            confidence += 0.4
        
        # Stunting and wilting
        if symptoms.stunting and symptoms.wilting:
            confidence += 0.3
        
        return min(confidence, 1.0)
    
    def _detect_white_rust(self, symptoms: CabbageSymptoms) -> float:
        """Detect white rust (Albugo)"""
        confidence = 0.0
        
        # White chalky pustules = DIAGNOSTIC
        if symptoms.white_chalky_pustules:
            confidence += 0.7
        
        # White pustule area
        if symptoms.white_pustule_area > 0.03:
            confidence += 0.3
        
        return min(confidence, 1.0)
    
    def _create_result(
        self,
        disease: CabbageDisease,
        confidence: float,
        symptoms: CabbageSymptoms,
        severity: str
    ) -> CabbageDiseaseResult:
        """Create disease result with full information"""
        if disease == CabbageDisease.HEALTHY:
            return CabbageDiseaseResult(
                disease=disease,
                confidence=confidence,
                symptoms=symptoms,
                severity=severity,
                pathogen='None',
                treatment='No treatment needed',
                resistance_available=False,
                notes='Healthy cabbage plant'
            )
        
        disease_key = disease.value
        disease_info = self.disease_database.get(disease_key, {})
        
        return CabbageDiseaseResult(
            disease=disease,
            confidence=confidence,
            symptoms=symptoms,
            severity=severity,
            pathogen=disease_info.get('pathogen', 'Unknown'),
            treatment=disease_info.get('treatment', 'Consult specialist'),
            resistance_available=disease_info.get('resistance', '') != 'No resistance',
            notes=disease_info.get('notes', '')
        )


def main():
    """Example usage"""
    detector = CabbageDiseaseDetector()
    
    print("=== AgroPulse Cabbage Disease Detection ===")
    print(f"\nDiseases tracked: {len(detector.disease_database)}")
    
    print("\n🥬 MAJOR CABBAGE DISEASES:")
    
    print("\n1. BLACK ROT (Xanthomonas campestris pv. campestris)")
    print("   - V-shaped yellow lesions from leaf margin")
    print("   - Blackened veins DIAGNOSTIC (vascular pathogen)")
    print("   - 70-80% loss severe epidemics")
    print("   - Seed transmission critical")
    print("   - #1 BACTERIAL DISEASE worldwide")
    
    print("\n2. CLUBROOT (Plasmodiophora brassicae)")
    print("   - Swollen club-shaped root galls")
    print("   - Survives 20+ YEARS in soil")
    print("   - 100% loss in infested fields")
    print("   - Soil pH >7.2 = control (liming)")
    print("   - MOST DEVASTATING brassica disease")
    
    print("\n3. DOWNY MILDEW (Peronospora parasitica)")
    print("   - White-gray downy growth on undersides")
    print("   - Yellow angular spots upper surface")
    print("   - SEEDLING KILLER (80-100% loss)")
    print("   - Cool humid conditions (10-15°C)")
    
    print("\n4. ALTERNARIA LEAF SPOT (Alternaria brassicicola)")
    print("   - Target spot with concentric rings")
    print("   - Black sooty mold on lesions")
    print("   - Seed transmission major")
    print("   - Storage rots from field infections")
    
    print("\n5. FUSARIUM YELLOWS (Fusarium oxysporum)")
    print("   - One-sided yellowing characteristic")
    print("   - Vascular browning (cut stem)")
    print("   - Warm weather (24-28°C)")
    print("   - Resistant varieties excellent")
    
    print("\n🧬 RESISTANCE GENES:")
    print("   - CR genes (clubroot resistance)")
    print("   - Fusarium: Type A, B, C resistance")
    print("   - Race-specific resistance critical")
    
    print("\n✅ SYSTEM STATUS: Cabbage detection ready")


if __name__ == "__main__":
    main()
