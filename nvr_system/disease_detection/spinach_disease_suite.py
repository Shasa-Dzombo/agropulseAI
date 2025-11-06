"""
Spinach Disease Detection Suite
================================

Comprehensive disease identification for spinach (Spinacia oleracea),
a critical dark leafy green horticultural crop.

Critical Diseases:
1. Downy Mildew (Peronospora farinosa f.sp. spinaciae) - #1 DISEASE GLOBALLY
2. White Rust (Albugo occidentalis) - QUARANTINE DISEASE
3. Anthracnose (Colletotrichum dematium) - STORAGE DESTROYER
4. Cercospora Leaf Spot (Cercospora beticola) - QUALITY DOWNGRADE
5. Stemphylium Leaf Spot (Stemphylium botryosum) - FALL EPIDEMIC
6. Fusarium Wilt (Fusarium oxysporum f.sp. spinaciae) - SOILBORNE LETHAL
7. Cucumber Mosaic Virus (CMV) - YIELD LOSS 30-50%
8. Bacterial Leaf Spot (Pseudomonas syringae) - COOLING WATER PATHOGEN

Market Context:
- Global spinach market: $1.8 billion
- Fresh market demand: 70%, processing: 30%
- Baby spinach premium: 40% higher price
- Organic spinach: 60% price premium
- Shelf life critical: 7-14 days fresh, disease cuts to 3-5 days
- Quality grades: USDA No. 1 (zero disease), No. 2 (minor spots allowed)

Author: AgroPulse Team
Date: November 2025
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Dict
from datetime import datetime


class SpinachType(Enum):
    """Spinach variety categories"""
    SAVOY = "savoy"  # Crinkled leaves, cold-hardy, processing
    FLAT_LEAF = "flat_leaf"  # Smooth, easy cleaning, fresh market
    SEMI_SAVOY = "semi_savoy"  # Hybrid, dual-purpose
    BABY_SPINACH = "baby_spinach"  # Premium fresh market, 20-30 days harvest
    GIANT_NOBLE = "giant_noble"  # Large smooth leaves, bunching


class SpinachDisease(Enum):
    """Major spinach diseases"""
    DOWNY_MILDEW = "downy_mildew"
    WHITE_RUST = "white_rust"
    ANTHRACNOSE = "anthracnose"
    CERCOSPORA_LEAF_SPOT = "cercospora"
    STEMPHYLIUM_LEAF_SPOT = "stemphylium"
    FUSARIUM_WILT = "fusarium_wilt"
    CUCUMBER_MOSAIC_VIRUS = "cmv"
    BACTERIAL_LEAF_SPOT = "bacterial_spot"


@dataclass
class SpinachDiseaseParams:
    """Disease-specific parameters for spinach"""
    disease: SpinachDisease
    pathogen_scientific: str
    severity_scale: str  # 1-10 scale
    yield_loss_percent: Tuple[int, int]  # (min, max)
    quality_downgrade: str
    market_impact: str
    
    # Symptom characteristics
    leaf_symptoms: List[str]
    stem_symptoms: List[str]
    root_symptoms: List[str]
    
    # Environmental triggers
    optimal_temp_c: Tuple[float, float]
    optimal_humidity: Tuple[int, int]
    leaf_wetness_hours: int
    
    # Resistance genes (Dm genes for downy mildew)
    resistance_genes: List[str]
    
    # Control measures
    fungicide_frac_codes: List[str]
    biocontrol_agents: List[str]
    cultural_practices: List[str]
    
    # Economic data
    treatment_cost_per_acre: float
    yield_protection_percent: int
    quality_preservation: str


# Disease database
SPINACH_DISEASES = {
    SpinachDisease.DOWNY_MILDEW: SpinachDiseaseParams(
        disease=SpinachDisease.DOWNY_MILDEW,
        pathogen_scientific="Peronospora farinosa f.sp. spinaciae",
        severity_scale="10/10 - MOST DEVASTATING SPINACH DISEASE GLOBALLY",
        yield_loss_percent=(50, 100),
        quality_downgrade="Total loss - unmarketable",
        market_impact="$500M+ annual losses worldwide, #1 constraint to production",
        
        leaf_symptoms=[
            "Yellow angular spots on upper leaf surface DIAGNOSTIC (bound by veins)",
            "Purple-gray downy growth on undersides (sporangiophores and sporangia)",
            "Lesions start small (1-2mm) → expand to 10-15mm, coalesce",
            "Chlorotic halos around lesions",
            "Rapid defoliation in 5-7 days under favorable conditions",
            "Systemic infection from cotyledons = stunted plants",
            "Lesion edges remain angular (never circular like cercospora)",
        ],
        stem_symptoms=[
            "Rarely affected directly",
            "Stunting from systemic infection",
        ],
        root_symptoms=[
            "No direct infection",
            "Reduced root mass from defoliation",
        ],
        
        optimal_temp_c=(7.0, 15.0),  # Cool weather pathogen
        optimal_humidity=(85, 100),  # High humidity required
        leaf_wetness_hours=4,  # Minimum 4 hours for infection
        
        resistance_genes=[
            "Dm-1", "Dm-2", "Dm-3", "Dm-4", "Dm-5", "Dm-6", "Dm-7", "Dm-8",
            "Dm-9", "Dm-10", "Dm-11", "Dm-12", "Dm-13", "Dm-14", "Dm-15", "Dm-16",
            # 16+ resistance genes identified, but pathogen has 17+ RACES
            # Race-specific resistance: Dm genes overcome rapidly (3-5 years)
            # New races emerge continuously: Race 13, 14, 15, 16, 17 recent
        ],
        
        fungicide_frac_codes=[
            "4-Phenylamides",  # Metalaxyl, mefenoxam - RESISTANCE SEVERE
            "11-QoI",  # Azoxystrobin - RESISTANCE DOCUMENTED
            "40-Phosphonates",  # Fosetyl-Al - moderate efficacy
            "43-Carbamates",  # Propamocarb - tank mix partner
            "U15-Unknown",  # Oxathiapiprolin - newest chemistry, still effective
        ],
        
        biocontrol_agents=[
            "Trichoderma harzianum - seed treatment",
            "Bacillus subtilis - foliar spray, preventative",
            "Reynoutria sachalinensis extract - plant defense activator",
        ],
        
        cultural_practices=[
            "Plant resistant varieties (check latest race profile in region)",
            "Avoid overhead irrigation - drip only",
            "3-year rotation minimum (spores survive 3-5 years in crop debris)",
            "Remove crop debris immediately post-harvest (burn or bury deep)",
            "Greenhouse: maintain RH <85%, increase air circulation",
            "Scout fields 2x per week during cool humid periods",
            "Weekly fungicide preventative applications starting at 2-leaf stage",
            "Harvest early if infection detected (salvage yield)",
        ],
        
        treatment_cost_per_acre=180.0,  # Weekly sprays expensive
        yield_protection_percent=60,  # Even with fungicides, 40% loss common
        quality_preservation="Critical - spots make leaves unmarketable for fresh market"
    ),
    
    SpinachDisease.WHITE_RUST: SpinachDiseaseParams(
        disease=SpinachDisease.WHITE_RUST,
        pathogen_scientific="Albugo occidentalis",
        severity_scale="9/10 - QUARANTINE DISEASE, EXPORT RESTRICTIONS",
        yield_loss_percent=(30, 80),
        quality_downgrade="Total loss for fresh market - white pustules unacceptable",
        market_impact="Export quarantine, market rejection, $200M+ losses",
        
        leaf_symptoms=[
            "White chalky pustules on undersides DIAGNOSTIC PATHOGNOMONIC",
            "Raised blisters (2-5mm diameter) rupture to release white spores",
            "Pustules often in circular clusters",
            "Yellow spots on upper surface corresponding to pustules",
            "Leaf distortion and curling around infection sites",
            "Hypertrophy (abnormal tissue swelling) at pustules",
            "Systemically infected plants = severe stunting, rosetting",
        ],
        stem_symptoms=[
            "White pustules on stems and petioles",
            "Stem hypertrophy and distortion",
        ],
        root_symptoms=[
            "No infection",
        ],
        
        optimal_temp_c=(10.0, 18.0),
        optimal_humidity=(80, 100),
        leaf_wetness_hours=6,
        
        resistance_genes=[
            "Race-specific genes under research",
            "No commercial varieties with complete resistance",
            "Tolerance varies by variety",
        ],
        
        fungicide_frac_codes=[
            "11-QoI",  # Azoxystrobin, pyraclostrobin
            "M1-Copper",  # Copper hydroxide - preventative only
            "M3-Dithiocarbamates",  # Mancozeb, preventative
            "40-Phosphonates",  # Fosetyl-Al
        ],
        
        biocontrol_agents=[
            "Limited efficacy - chemical control primary",
        ],
        
        cultural_practices=[
            "QUARANTINE DISEASE - report to agricultural authorities",
            "Destroy infected plants immediately (do not compost)",
            "Avoid planting spinach in same field for 3+ years",
            "Overhead irrigation spreads spores - use drip",
            "Control wild amaranth and lambsquarters (alternative hosts)",
            "Preventative fungicides starting at seedling stage",
            "Field scouting daily if disease present in region",
        ],
        
        treatment_cost_per_acre=200.0,
        yield_protection_percent=50,
        quality_preservation="Zero tolerance for fresh market - processing only if severe"
    ),
    
    SpinachDisease.ANTHRACNOSE: SpinachDiseaseParams(
        disease=SpinachDisease.ANTHRACNOSE,
        pathogen_scientific="Colletotrichum dematium f.sp. spinaciae",
        severity_scale="7/10 - STORAGE DISEASE, POST-HARVEST LOSSES SEVERE",
        yield_loss_percent=(20, 60),
        quality_downgrade="Rapid post-harvest decay, shelf life reduced 50-70%",
        market_impact="Storage losses $100M+, particularly baby spinach",
        
        leaf_symptoms=[
            "Circular to irregular brown lesions with tan centers",
            "Dark brown to black margins DIAGNOSTIC",
            "Acervuli (fruiting bodies) visible as tiny black dots in lesion centers",
            "Lesions start 2-3mm, expand to 10mm+",
            "Pinkish spore masses in humid conditions (PATHOGNOMONIC)",
            "Lesions often along leaf edges and tips",
            "Post-harvest: rapid spreading soft rot (48-72 hours)",
        ],
        stem_symptoms=[
            "Brown cankers on petioles",
            "Petiole collapse leads to leaf wilt",
        ],
        root_symptoms=[
            "Crown rot in severe cases",
        ],
        
        optimal_temp_c=(20.0, 28.0),  # Warm weather pathogen
        optimal_humidity=(90, 100),
        leaf_wetness_hours=8,
        
        resistance_genes=[
            "Polygenic resistance",
            "No single major genes identified",
        ],
        
        fungicide_frac_codes=[
            "3-DMI",  # Difenoconazole - post-harvest dip
            "11-QoI",  # Azoxystrobin - field application
            "M5-Chloronitriles",  # Chlorothalonil - broad spectrum
        ],
        
        biocontrol_agents=[
            "Bacillus subtilis - post-harvest wash",
            "Pseudomonas fluorescens - biological control",
        ],
        
        cultural_practices=[
            "Harvest in morning when leaves are dry",
            "Rapid cooling to 4°C within 2 hours of harvest CRITICAL",
            "Sanitize packing equipment between loads",
            "Pre-harvest fungicide application 3 days before cutting",
            "Avoid field damage during harvest (entry points for fungus)",
            "Storage at 0-2°C, 95-98% RH (proper cold chain)",
            "Limit storage time for baby spinach to 7 days maximum",
        ],
        
        treatment_cost_per_acre=120.0,
        yield_protection_percent=70,
        quality_preservation="Essential for storage and transportation"
    ),
    
    SpinachDisease.CERCOSPORA_LEAF_SPOT: SpinachDiseaseParams(
        disease=SpinachDisease.CERCOSPORA_LEAF_SPOT,
        pathogen_scientific="Cercospora beticola",
        severity_scale="6/10 - QUALITY DOWNGRADE, GRADING LOSSES",
        yield_loss_percent=(10, 30),
        quality_downgrade="USDA Grade downgrade from No. 1 to No. 2 or cull",
        market_impact="Fresh market rejection, price reduction 30-50%",
        
        leaf_symptoms=[
            "Circular spots with tan to gray centers DIAGNOSTIC",
            "Purple to brown margins (distinct from downy mildew)",
            "Spots remain CIRCULAR never angular (key differential diagnosis)",
            "Spots 2-8mm diameter",
            "Gray spore masses in center under humid conditions",
            "Spots coalesce causing leaf blighting",
            "Older leaves affected first",
        ],
        stem_symptoms=[
            "Rare",
        ],
        root_symptoms=[
            "No infection",
        ],
        
        optimal_temp_c=(25.0, 32.0),  # Hot weather pathogen
        optimal_humidity=(85, 100),
        leaf_wetness_hours=10,
        
        resistance_genes=[
            "Quantitative resistance",
            "No major resistance genes",
        ],
        
        fungicide_frac_codes=[
            "11-QoI",  # Strobilurins - resistance developing
            "3-DMI",  # Triazoles
            "M5-Chloronitriles",  # Chlorothalonil
        ],
        
        biocontrol_agents=[
            "Trichoderma spp.",
            "Bacillus amyloliquefaciens",
        ],
        
        cultural_practices=[
            "Avoid overhead irrigation in late afternoon (evening dew extends wetness)",
            "Remove old leaves before spots form (sanitation)",
            "2-year rotation with non-Chenopodiaceae crops",
            "Preventative fungicides if disease historically present",
        ],
        
        treatment_cost_per_acre=90.0,
        yield_protection_percent=80,
        quality_preservation="Important for fresh market grading"
    ),
    
    SpinachDisease.FUSARIUM_WILT: SpinachDiseaseParams(
        disease=SpinachDisease.FUSARIUM_WILT,
        pathogen_scientific="Fusarium oxysporum f.sp. spinaciae",
        severity_scale="8/10 - SOILBORNE, LETHAL, LONG-TERM SURVIVAL",
        yield_loss_percent=(40, 100),
        quality_downgrade="Plant death - total loss",
        market_impact="Field abandonment, 10+ year soil infestation",
        
        leaf_symptoms=[
            "Yellowing starting on lower leaves",
            "One-sided yellowing initially (vascular infection)",
            "Wilting despite adequate soil moisture",
            "Interveinal chlorosis",
            "Necrosis and leaf drop",
        ],
        stem_symptoms=[
            "Vascular browning DIAGNOSTIC - cut stem shows brown streaks",
            "Stem base browning and necrosis",
        ],
        root_symptoms=[
            "Browning and death of feeder roots",
            "Taproot discoloration internally",
        ],
        
        optimal_temp_c=(22.0, 28.0),
        optimal_humidity=(60, 90),
        leaf_wetness_hours=0,  # Soilborne, not dependent on leaf wetness
        
        resistance_genes=[
            "Race 1 resistance available in some varieties",
            "Multiple races identified",
        ],
        
        fungicide_frac_codes=[
            "No effective fungicides for established infections",
            "Soil fumigation pre-plant only option",
        ],
        
        biocontrol_agents=[
            "Trichoderma harzianum - soil amendment",
            "Non-pathogenic Fusarium strains - competitive exclusion",
        ],
        
        cultural_practices=[
            "Plant resistant varieties where available",
            "Long rotations (5+ years) with non-hosts",
            "Soil solarization in warm climates",
            "Avoid field with fusarium history if possible",
            "No cure once established - prevention only",
        ],
        
        treatment_cost_per_acre=0.0,  # No effective treatment
        yield_protection_percent=0,
        quality_preservation="Prevention only strategy"
    ),
}


@dataclass
class SpinachDiseaseResult:
    """Detection result for spinach diseases"""
    disease: SpinachDisease
    confidence: float
    severity: str
    symptoms_detected: List[str]
    treatment_urgency: str
    recommended_actions: List[str]
    economic_impact: str
    detection_time: datetime = field(default_factory=datetime.now)


class SpinachDiseaseDetector:
    """
    Specialized detector for spinach diseases
    
    Critical differentiations:
    - Downy mildew vs cercospora: ANGULAR vs CIRCULAR spots
    - White rust vs downy mildew: WHITE PUSTULES vs GRAY SPORULATION
    - Anthracnose vs cercospora: DARK MARGINS + PINK SPORES vs GRAY
    """
    
    def __init__(self):
        self.diseases = SPINACH_DISEASES
        
    def detect_disease(self, 
                      image: np.ndarray,
                      spinach_type: SpinachType,
                      field_history: Optional[Dict] = None) -> List[SpinachDiseaseResult]:
        """
        Detect diseases on spinach plants
        
        Args:
            image: BGR image from camera
            spinach_type: Variety category
            field_history: Previous disease occurrences
            
        Returns:
            List of detected diseases with confidence scores
        """
        if image is None or image.size == 0:
            return []
        
        results = []
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Detect angular spots (downy mildew)
        downy_score = self._detect_angular_spots(image, hsv)
        if downy_score > 0.5:
            results.append(self._create_result(
                SpinachDisease.DOWNY_MILDEW,
                downy_score,
                "High - Angular yellow spots with gray sporulation"
            ))
        
        # Detect white pustules (white rust)
        white_rust_score = self._detect_white_pustules(image, hsv)
        if white_rust_score > 0.5:
            results.append(self._create_result(
                SpinachDisease.WHITE_RUST,
                white_rust_score,
                "Critical - Quarantine disease"
            ))
        
        # Detect circular spots (cercospora)
        cercospora_score = self._detect_circular_spots(image, hsv)
        if cercospora_score > 0.4:
            results.append(self._create_result(
                SpinachDisease.CERCOSPORA_LEAF_SPOT,
                cercospora_score,
                "Moderate - Quality downgrade risk"
            ))
        
        # Detect anthracnose lesions
        anthracnose_score = self._detect_anthracnose_lesions(image, hsv)
        if anthracnose_score > 0.4:
            results.append(self._create_result(
                SpinachDisease.ANTHRACNOSE,
                anthracnose_score,
                "High - Post-harvest losses severe"
            ))
        
        return sorted(results, key=lambda x: x.confidence, reverse=True)
    
    def _detect_angular_spots(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect angular yellow spots bound by veins (downy mildew)"""
        # Extract yellow regions
        yellow_lower = np.array([20, 40, 40])
        yellow_upper = np.array([35, 255, 255])
        yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
        
        # Find contours
        contours, _ = cv2.findContours(yellow_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return 0.0
        
        angular_count = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 50 or area > 5000:
                continue
            
            # Check angularity using contour approximation
            epsilon = 0.02 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            
            # Angular spots have more vertices (polygonal, not circular)
            if len(approx) >= 6:  # Angular shapes have 6+ vertices
                angular_count += 1
        
        return min(1.0, angular_count / 10.0)
    
    def _detect_white_pustules(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect white chalky pustules (white rust)"""
        # White color range
        white_lower = np.array([0, 0, 180])
        white_upper = np.array([180, 40, 255])
        white_mask = cv2.inRange(hsv, white_lower, white_upper)
        
        # Morphological operations to find raised pustules
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        pustule_count = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 20 < area < 500:  # Pustule size range
                # Check circularity (pustules are circular)
                perimeter = cv2.arcLength(cnt, True)
                if perimeter > 0:
                    circularity = 4 * np.pi * area / (perimeter ** 2)
                    if circularity > 0.7:  # Circular pustules
                        pustule_count += 1
        
        return min(1.0, pustule_count / 15.0)
    
    def _detect_circular_spots(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect circular tan/gray spots (cercospora)"""
        # Tan to gray color range
        gray_lower = np.array([0, 0, 60])
        gray_upper = np.array([180, 50, 140])
        gray_mask = cv2.inRange(hsv, gray_lower, gray_upper)
        
        contours, _ = cv2.findContours(gray_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        circular_count = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 50 or area > 2000:
                continue
            
            # Check circularity (cercospora spots are circular, not angular)
            perimeter = cv2.arcLength(cnt, True)
            if perimeter > 0:
                circularity = 4 * np.pi * area / (perimeter ** 2)
                if circularity > 0.75:  # Highly circular
                    circular_count += 1
        
        return min(1.0, circular_count / 12.0)
    
    def _detect_anthracnose_lesions(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect dark-bordered lesions with tan centers (anthracnose)"""
        # Dark brown range
        brown_lower = np.array([10, 50, 20])
        brown_upper = np.array([20, 255, 100])
        brown_mask = cv2.inRange(hsv, brown_lower, brown_upper)
        
        contours, _ = cv2.findContours(brown_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        lesion_count = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 100 < area < 3000:
                lesion_count += 1
        
        return min(1.0, lesion_count / 10.0)
    
    def _create_result(self, disease: SpinachDisease, confidence: float, severity: str) -> SpinachDiseaseResult:
        """Create detection result with recommendations"""
        params = self.diseases[disease]
        
        return SpinachDiseaseResult(
            disease=disease,
            confidence=confidence,
            severity=severity,
            symptoms_detected=params.leaf_symptoms[:3],
            treatment_urgency="URGENT" if confidence > 0.7 else "Monitor",
            recommended_actions=params.cultural_practices[:3],
            economic_impact=params.market_impact
        )


# Example usage
if __name__ == "__main__":
    print("Spinach Disease Detection System")
    print("=" * 60)
    
    detector = SpinachDiseaseDetector()
    
    # Display disease database
    print("\n📚 SPINACH DISEASE DATABASE:")
    for disease_type, params in SPINACH_DISEASES.items():
        print(f"\n{disease_type.value.upper()}")
        print(f"  Pathogen: {params.pathogen_scientific}")
        print(f"  Severity: {params.severity_scale}")
        print(f"  Yield Loss: {params.yield_loss_percent[0]}-{params.yield_loss_percent[1]}%")
        print(f"  Market Impact: {params.market_impact}")
        if params.resistance_genes:
            print(f"  Resistance Genes: {', '.join(params.resistance_genes[:5])}")
    
    print("\n✓ Spinach disease detection system initialized")
    print(f"  Diseases covered: {len(SPINACH_DISEASES)}")
    print(f"  Critical focus: Downy mildew (16+ resistance genes, 17+ pathogen races)")
    print(f"  Quarantine alert: White rust (export restrictions)")
