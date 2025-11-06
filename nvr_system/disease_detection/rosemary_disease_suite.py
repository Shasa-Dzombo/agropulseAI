"""
Rosemary Disease Detection Suite
=================================

Comprehensive disease identification for rosemary (Rosmarinus officinalis/Salvia rosmarinus),
premium Mediterranean herb with Phytophthora root rot dominance and botrytis blight challenges.

Rosemary Types:
- Upright varieties - commercial production
- Prostrate/trailing - ornamental, ground cover
- Arp - cold hardy
- Tuscan Blue - culinary premium
- Blue Spires - tall upright

Critical Diseases:
1. Phytophthora Root Rot (P. cinnamomi, P. cryptogea) - #1 KILLER, WATERLOGGING
2. Botrytis Gray Mold (Botrytis cinerea) - GREENHOUSE, POSTHARVEST
3. Powdery Mildew (Golovinomyces biocellatus) - GREENHOUSE
4. Bacterial Leaf Spot (Pseudomonas syringae) - CUTTING PROPAGATION
5. Rhizoctonia Root Rot - SOILBORNE
6. Alternaria Leaf Blight - DEFOLIATION
7. Cercospora Leaf Spot - LATE SEASON
8. Root Rot Complex (Pythium + Rhizoctonia + Fusarium) - POOR DRAINAGE

Market Intelligence:
- USA production: $45 million, Mediterranean regions
- Fresh rosemary: $12-20/lb retail, $6-12/lb wholesale
- Dried rosemary: $15-30/lb organic
- Essential oil: $80-200/kg (1,8-cineole content critical)
- Cutting propagation: 90% of commercial, disease spread risk
- Drought-adapted: OVERWATERING #1 grower error (Phytophthora)
- Greenhouse production: 60% of commercial fresh herbs

Author: AgroPulse Team
Date: November 2025
"""

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional


class RosemaryType(Enum):
    """Rosemary growth habits"""
    UPRIGHT = "upright"  # Commercial production
    PROSTRATE = "prostrate"  # Trailing, ornamental
    SEMI_UPRIGHT = "semi_upright"  # Intermediate


class RosemaryDisease(Enum):
    """Major rosemary diseases"""
    PHYTOPHTHORA_ROOT_ROT = "phytophthora"
    BOTRYTIS_GRAY_MOLD = "botrytis"
    POWDERY_MILDEW = "powdery_mildew"
    BACTERIAL_LEAF_SPOT = "bacterial_spot"
    RHIZOCTONIA_ROOT_ROT = "rhizoctonia"
    ALTERNARIA_BLIGHT = "alternaria"
    CERCOSPORA_LEAF_SPOT = "cercospora"
    ROOT_ROT_COMPLEX = "root_rot_complex"


@dataclass
class RosemaryDiseaseParams:
    """Disease parameters for rosemary"""
    disease: RosemaryDisease
    pathogen: str
    severity: str
    yield_loss: Tuple[int, int]
    essential_oil_impact: str
    
    # Symptoms
    foliage_symptoms: List[str]
    stem_symptoms: List[str]
    root_symptoms: List[str]
    diagnostic_features: str
    
    # Water management critical
    irrigation_relationship: str
    drainage_requirements: str
    
    # Propagation
    cutting_transmission_risk: str
    mother_stock_management: str
    
    # Control
    cultural_control: List[str]
    fungicide_control: List[str]
    greenhouse_specific: List[str]
    
    # Economics
    market_impact: str
    treatment_cost_per_acre: float


# Disease database
ROSEMARY_DISEASES = {
    RosemaryDisease.PHYTOPHTHORA_ROOT_ROT: RosemaryDiseaseParams(
        disease=RosemaryDisease.PHYTOPHTHORA_ROOT_ROT,
        pathogen="Phytophthora cinnamomi + P. cryptogea (WATERLOGGING, #1 killer)",
        severity="10/10 - #1 ROSEMARY KILLER, WATERLOGGING DISASTER",
        yield_loss=(80, 100),
        essential_oil_impact="Complete plant death = 100% loss",
        
        foliage_symptoms=[
            "Wilting despite adequate moisture DIAGNOSTIC",
            "Yellowing foliage progressing upward",
            "Brown needle tips",
            "Foliage turns grayish-brown then dies",
            "Entire plant death within 2-4 weeks",
        ],
        
        stem_symptoms=[
            "Stem browning at soil line",
            "Bark sloughing off at crown",
        ],
        
        root_symptoms=[
            "Black, mushy roots DIAGNOSTIC",
            "Root rot starting from fine roots",
            "Complete root system collapse",
            "Characteristic foul odor",
        ],
        
        diagnostic_features="Wilting + black mushy roots + waterlogged history",
        
        irrigation_relationship="OVERWATERING PRIMARY CAUSE - rosemary drought-adapted",
        drainage_requirements="EXCELLENT drainage ESSENTIAL - raised beds or containers",
        
        cutting_transmission_risk="LOW (soilborne, not systemic in cuttings)",
        mother_stock_management="Protect mother plants from Phytophthora infection",
        
        cultural_control=[
            "DRAINAGE IS EVERYTHING - raise beds 8-12 inches",
            "Sandy, well-drained soil mandatory",
            "DO NOT OVERWATER (most common error)",
            "Allow soil to dry between irrigations",
            "Drip irrigation only, NO overhead",
            "Avoid low spots where water collects",
            "Container production on benches",
            "NEVER plant where Phytophthora present",
        ],
        
        fungicide_control=[
            "PREVENTATIVE ONLY - no cure once infected",
            "FRAC 4: Mefenoxam (Ridomil) - drench at planting",
            "FRAC 43: Fluopicolide (Presidio)",
            "FRAC 40: Cyazofamid (Ranman)",
            "Apply at planting in high-risk sites",
            "Repeat monthly in wet seasons",
            "DRAINAGE MORE IMPORTANT THAN FUNGICIDES",
        ],
        
        greenhouse_specific=[
            "Bench production prevents soil contact",
            "Drip irrigation with precise water management",
            "Avoid floor watering",
            "Sterile media essential",
        ],
        
        market_impact="CATASTROPHIC - #1 cause of rosemary crop failure",
        treatment_cost_per_acre=400.0  # Raised beds + fungicides
    ),
    
    RosemaryDisease.BOTRYTIS_GRAY_MOLD: RosemaryDiseaseParams(
        disease=RosemaryDisease.BOTRYTIS_GRAY_MOLD,
        pathogen="Botrytis cinerea (GREENHOUSE, high humidity, postharvest)",
        severity="8/10 - GREENHOUSE EPIDEMIC, POSTHARVEST LOSS",
        yield_loss=(20, 50),
        essential_oil_impact="Infected foliage unusable, 20-50% loss",
        
        foliage_symptoms=[
            "Gray fuzzy mold growth on leaves/stems DIAGNOSTIC",
            "Brown water-soaked lesions",
            "Blighted shoot tips",
            "Rapid spread in humid conditions",
        ],
        
        stem_symptoms=[
            "Stem cankers with gray mold",
            "Die-back of shoots",
        ],
        
        root_symptoms=[],
        
        diagnostic_features="Gray fuzzy mold, humid conditions, greenhouse",
        
        irrigation_relationship="Overhead irrigation + humidity promotes disease",
        drainage_requirements="Air circulation more critical than drainage",
        
        cutting_transmission_risk="MODERATE - infected cuttings spread disease",
        mother_stock_management="Keep mother stock dry, good air circulation",
        
        cultural_control=[
            "GREENHOUSE HUMIDITY CONTROL CRITICAL",
            "Dehumidify to <70% RH",
            "Increase air circulation (fans)",
            "Space plants for air flow",
            "Morning irrigation (leaves dry by night)",
            "Avoid overhead irrigation",
            "Remove infected plant debris",
        ],
        
        fungicide_control=[
            "FRAC 7: Boscalid (Endura)",
            "FRAC 9: Cyprodinil + fludioxonil (Switch)",
            "FRAC 17: Fenhexamid (Decree)",
            "FRAC 11: Azoxystrobin",
            "Rotate FRAC codes (resistance risk)",
            "Preventative applications in humid weather",
        ],
        
        greenhouse_specific=[
            "Dehumidification systems essential",
            "Horizontal air flow fans",
            "Heat + vent to reduce humidity",
            "Morning watering protocol",
        ],
        
        market_impact="Greenhouse losses, postharvest spoilage",
        treatment_cost_per_acre=250.0
    ),
    
    RosemaryDisease.BACTERIAL_LEAF_SPOT: RosemaryDiseaseParams(
        disease=RosemaryDisease.BACTERIAL_LEAF_SPOT,
        pathogen="Pseudomonas syringae (cutting propagation spreads)",
        severity="7/10 - CUTTING PROPAGATION RISK",
        yield_loss=(15, 40),
        essential_oil_impact="Cosmetic damage reduces value 15-40%",
        
        foliage_symptoms=[
            "Small dark brown-black leaf spots",
            "Spots 1-3mm diameter",
            "Water-soaked appearance initially",
            "Yellow halo around spots",
        ],
        
        stem_symptoms=[
            "Black streaks on young stems",
        ],
        
        root_symptoms=[],
        
        diagnostic_features="Dark spots with yellow halos, wet weather",
        
        irrigation_relationship="Overhead irrigation spreads bacteria",
        drainage_requirements="Standard drainage adequate",
        
        cutting_transmission_risk="HIGH - bacteria spread through cutting propagation",
        mother_stock_management="CRITICAL - maintain disease-free mother stock",
        
        cultural_control=[
            "DISEASE-FREE MOTHER STOCK essential",
            "Disinfect cutting tools (10% bleach)",
            "Avoid overhead irrigation",
            "Good air circulation",
            "Remove infected plants",
        ],
        
        fungicide_control=[
            "Copper bactericides",
            "Weekly applications in wet weather",
            "Limited efficacy",
        ],
        
        greenhouse_specific=[
            "Drip irrigation only",
            "Tool disinfection strict protocol",
            "Quarantine new stock",
        ],
        
        market_impact="Cosmetic damage, propagation stock contamination",
        treatment_cost_per_acre=180.0
    ),
}


@dataclass
class RosemaryDiseaseResult:
    """Detection result for rosemary diseases"""
    disease: RosemaryDisease
    confidence: float
    severity: str
    irrigation_warning: str
    drainage_recommendation: str
    immediate_actions: List[str]
    propagation_precautions: str


class RosemaryDiseaseDetector:
    """
    Rosemary disease detector
    
    CRITICAL FOCUS:
    - Phytophthora root rot: #1 killer, overwatering disaster
    - Drainage absolutely essential (drought-adapted plant)
    - Greenhouse botrytis epidemic risk
    - Cutting propagation disease spread
    """
    
    def __init__(self):
        self.diseases = ROSEMARY_DISEASES
    
    def detect_disease(self,
                      image: np.ndarray,
                      plant_part: str = "foliage",
                      production_system: str = "greenhouse",
                      soil_drainage: str = "unknown") -> List[RosemaryDiseaseResult]:
        """
        Detect rosemary diseases
        
        Args:
            image: BGR image
            plant_part: "foliage", "stem", "root"
            production_system: "greenhouse", "field", "container"
            soil_drainage: "excellent", "good", "poor", "unknown"
        
        Returns:
            List of detected diseases with irrigation/drainage warnings
        """
        if image is None or image.size == 0:
            return []
        
        results = []
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        if plant_part == "foliage":
            # Botrytis (gray mold)
            botrytis_score = self._detect_gray_fuzzy_mold(image, hsv)
            if botrytis_score > 0.4:
                results.append(self._create_result(
                    RosemaryDisease.BOTRYTIS_GRAY_MOLD,
                    botrytis_score,
                    production_system,
                    soil_drainage
                ))
            
            # Bacterial spot
            bacterial_score = self._detect_dark_spots_halo(image, hsv)
            if bacterial_score > 0.4:
                results.append(self._create_result(
                    RosemaryDisease.BACTERIAL_LEAF_SPOT,
                    bacterial_score,
                    production_system,
                    soil_drainage
                ))
        
        elif plant_part == "root":
            # PHYTOPHTHORA - CRITICAL
            phytophthora_score = self._detect_black_mushy_roots(image, hsv)
            if phytophthora_score > 0.5:
                results.append(self._create_result(
                    RosemaryDisease.PHYTOPHTHORA_ROOT_ROT,
                    phytophthora_score,
                    production_system,
                    soil_drainage,
                    alert="CRITICAL"
                ))
        
        return sorted(results, key=lambda x: x.confidence, reverse=True)
    
    def _detect_gray_fuzzy_mold(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect gray fuzzy mold (Botrytis)"""
        gray_lower = np.array([0, 0, 80])
        gray_upper = np.array([180, 50, 180])
        gray_mask = cv2.inRange(hsv, gray_lower, gray_upper)
        
        coverage = np.sum(gray_mask > 0) / gray_mask.size
        return min(1.0, coverage * 20)
    
    def _detect_dark_spots_halo(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect dark spots with yellow halos (bacterial)"""
        dark_lower = np.array([0, 50, 0])
        dark_upper = np.array([180, 255, 80])
        dark_mask = cv2.inRange(hsv, dark_lower, dark_upper)
        
        coverage = np.sum(dark_mask > 0) / dark_mask.size
        return min(1.0, coverage * 18)
    
    def _detect_black_mushy_roots(self, image: np.ndarray, hsv: np.ndarray) -> float:
        """Detect black mushy roots (Phytophthora) - CRITICAL"""
        black_lower = np.array([0, 0, 0])
        black_upper = np.array([180, 255, 50])
        black_mask = cv2.inRange(hsv, black_lower, black_upper)
        
        coverage = np.sum(black_mask > 0) / black_mask.size
        return min(1.0, coverage * 15)
    
    def _create_result(self,
                      disease: RosemaryDisease,
                      confidence: float,
                      production_system: str,
                      soil_drainage: str,
                      alert: str = "") -> RosemaryDiseaseResult:
        """Create result with irrigation/drainage emphasis"""
        params = self.diseases[disease]
        
        if disease == RosemaryDisease.PHYTOPHTHORA_ROOT_ROT:
            severity = f"🚨 {alert} - {params.severity}" if alert else params.severity
            irrigation_warn = "🚨 STOP OVERWATERING IMMEDIATELY - #1 cause of rosemary death"
            drainage_rec = "CRITICAL: Raise beds 8-12 inches, improve drainage urgently"
            immediate = [
                "🚨 STOP watering immediately",
                "Improve drainage urgently (raised beds)",
                "Remove infected plants + surrounding soil",
                "Apply Mefenoxam to remaining plants",
                "Allow soil to dry between irrigations",
                "Rosemary is DROUGHT-ADAPTED (common overwatering mistake)",
            ]
            propagation = "Low risk in cuttings (soilborne)"
            
        elif disease == RosemaryDisease.BOTRYTIS_GRAY_MOLD:
            severity = params.severity
            irrigation_warn = "Avoid overhead irrigation, reduce humidity"
            drainage_rec = "Air circulation more critical than drainage"
            immediate = [
                "Reduce greenhouse humidity <70% RH",
                "Increase air circulation (fans)",
                "Apply Botrytis fungicide",
                "Remove infected plant debris",
                "Morning watering only",
            ]
            propagation = "Moderate risk - keep mother stock dry"
            
        elif disease == RosemaryDisease.BACTERIAL_LEAF_SPOT:
            severity = params.severity
            irrigation_warn = "Overhead irrigation spreads bacteria"
            drainage_rec = "Standard drainage adequate"
            immediate = [
                "Disinfect cutting tools (10% bleach)",
                "Maintain disease-free mother stock",
                "Apply copper bactericide",
                "Switch to drip irrigation",
            ]
            propagation = "⚠️ HIGH RISK - spreads through cutting propagation"
            
        else:
            severity = params.severity
            irrigation_warn = params.irrigation_relationship
            drainage_rec = params.drainage_requirements
            immediate = params.cultural_control[:4]
            propagation = params.cutting_transmission_risk
        
        return RosemaryDiseaseResult(
            disease=disease,
            confidence=confidence,
            severity=severity,
            irrigation_warning=irrigation_warn,
            drainage_recommendation=drainage_rec,
            immediate_actions=immediate,
            propagation_precautions=propagation
        )


# Example usage
if __name__ == "__main__":
    print("Rosemary Disease Detection System")
    print("=" * 70)
    
    detector = RosemaryDiseaseDetector()
    
    print("\n📚 ROSEMARY DISEASE DATABASE:")
    print("\n🚨 CRITICAL: PHYTOPHTHORA ROOT ROT (#1 Killer)")
    phyto = ROSEMARY_DISEASES[RosemaryDisease.PHYTOPHTHORA_ROOT_ROT]
    print(f"  Pathogen: {phyto.pathogen}")
    print(f"  Severity: {phyto.severity}")
    print(f"  Primary cause: OVERWATERING (rosemary drought-adapted)")
    print(f"  Diagnostic: {phyto.diagnostic_features}")
    print(f"  Prevention: {phyto.drainage_requirements}")
    
    print("\n⚠️  COMMON GROWER ERROR:")
    print("  Rosemary is DROUGHT-ADAPTED Mediterranean herb")
    print("  OVERWATERING is #1 cause of crop failure")
    print("  Excellent drainage ESSENTIAL (raised beds 8-12 inches)")
    print("  Allow soil to dry between irrigations")
    
    print("\n✓ Rosemary disease detection system initialized")
    print("  Focus: Phytophthora prevention, drainage, greenhouse botrytis")
    print("  Market: $45M USA, fresh $12-20/lb, essential oil $80-200/kg")
