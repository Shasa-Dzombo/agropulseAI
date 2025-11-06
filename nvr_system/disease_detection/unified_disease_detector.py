"""
Unified Disease Detection Engine
=================================

Hybrid system combining:
1. Rule-based detection (local, fast, detailed symptom analysis)
2. Kindwise AI (cloud, 288 diseases, farmer-focused)
3. Confidence validation and result fusion

Architecture:
- Primary: Rule-based detection for known diseases with high confidence
- Secondary: Kindwise AI for validation and unknown diseases
- Tertiary: Differential diagnosis for ambiguous cases

Benefits:
- Offline capable (rule-based fallback)
- Cost-effective (reduces API calls with smart routing)
- Comprehensive (combines 145+ local + 288 Kindwise diseases)
- Robust (dual validation reduces false positives)

Author: AgroPulse Team
Date: November 2025
"""

import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

# Import Kindwise client
from .kindwise_api_client import (
    KindwiseAPIClient,
    CropType,
    DiseaseSeverity,
    KindwiseAPIResponse,
    DiseaseIdentification
)

# Import local detectors
from .tomato_disease_suite import TomatoDiseaseDetector
from .potato_disease_suite import PotatoDiseaseDetector
from .cucumber_disease_suite import CucumberDiseaseDetector
from .pepper_disease_suite import PepperDiseaseDetector
from .lettuce_disease_suite import LettuceDiseaseDetector
from .strawberry_disease_suite import StrawberryDiseaseDetector
from .grape_disease_suite import GrapeDiseaseDetector
from .apple_disease_suite import AppleDiseaseDetector
from .citrus_disease_suite import CitrusDiseaseDetector
from .banana_disease_suite import BananaDiseaseDetector
from .mango_disease_suite import MangoDiseaseDetector
from .peach_disease_suite import PeachDiseaseDetector
from .olive_disease_suite import OliveDiseaseDetector
from .coffee_disease_suite import CoffeeDiseaseDetector
from .tea_disease_suite import TeaDiseaseDetector
from .onion_garlic_disease_suite import AlliumDiseaseDetector
from .cabbage_disease_suite import CabbageDiseaseDetector
from .watermelon_disease_suite import WatermelonDiseaseDetector
from .spinach_disease_suite import SpinachDiseaseDetector
from .eggplant_disease_suite import EggplantDiseaseDetector
from .sweet_potato_disease_suite import SweetPotatoDiseaseDetector
from .carrot_disease_suite import CarrotDiseaseDetector
from .broccoli_disease_suite import BroccoliDiseaseDetector


class DetectionMode(Enum):
    """Detection strategy selection"""
    RULE_BASED_ONLY = "rule_based"  # Local only, no API calls
    AI_ONLY = "ai_only"  # Kindwise only
    HYBRID_FAST = "hybrid_fast"  # Rule-based primary, AI for validation if low confidence
    HYBRID_COMPREHENSIVE = "hybrid_comprehensive"  # Both always, combine results
    AUTO = "auto"  # Intelligent routing based on confidence and connectivity


class ConfidenceLevel(Enum):
    """Overall detection confidence"""
    VERY_HIGH = "very_high"  # >90%, single method sufficient
    HIGH = "high"  # 75-90%, likely correct
    MODERATE = "moderate"  # 50-75%, consider alternatives
    LOW = "low"  # <50%, uncertain, needs validation


@dataclass
class UnifiedDiseaseResult:
    """
    Combined detection result from multiple sources
    """
    disease_name: str
    confidence: float  # 0.0 to 1.0, combined from all sources
    confidence_level: ConfidenceLevel
    
    # Detection sources (which methods identified this)
    detected_by_rules: bool = False
    detected_by_ai: bool = False
    rule_confidence: Optional[float] = None
    ai_confidence: Optional[float] = None
    
    # Disease details
    severity: DiseaseSeverity = DiseaseSeverity.MODERATE
    eppo_code: Optional[str] = None
    symptoms: List[str] = field(default_factory=list)
    
    # Farmer-focused output
    urgent_actions: List[str] = field(default_factory=list)
    treatments: List[Dict[str, Any]] = field(default_factory=list)
    economic_impact: str = ""
    spread_risk: str = "Moderate"
    
    # Validation
    alternative_diagnoses: List[str] = field(default_factory=list)
    diagnostic_certainty: str = ""  # "Confirmed", "Probable", "Possible"
    
    # Metadata
    detection_time_ms: int = 0
    api_cost_usd: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_farmer_report(self) -> str:
        """Generate farmer-friendly text report"""
        report = []
        report.append(f"🌱 DISEASE DETECTION REPORT")
        report.append(f"=" * 50)
        report.append(f"Disease: {self.disease_name}")
        report.append(f"Confidence: {self.confidence:.0%} ({self.confidence_level.value})")
        report.append(f"Severity: {self.severity.value.upper()}")
        
        if self.eppo_code:
            report.append(f"EPPO Code: {self.eppo_code} (International Standard)")
        
        report.append(f"\n📋 SYMPTOMS DETECTED:")
        for symptom in self.symptoms[:5]:
            report.append(f"  • {symptom}")
        
        if self.urgent_actions:
            report.append(f"\n🔴 URGENT ACTIONS REQUIRED:")
            for action in self.urgent_actions:
                report.append(f"  • {action}")
        
        report.append(f"\n💊 TREATMENT OPTIONS:")
        for i, treatment in enumerate(self.treatments[:3], 1):
            report.append(f"  {i}. {treatment.get('action', 'N/A')}")
            report.append(f"     Timing: {treatment.get('timing', 'N/A')}")
        
        report.append(f"\n💰 ECONOMIC IMPACT:")
        report.append(f"  {self.economic_impact}")
        
        report.append(f"\n📊 DIAGNOSTIC CERTAINTY: {self.diagnostic_certainty}")
        
        if self.alternative_diagnoses:
            report.append(f"\n⚠️  CONSIDER ALSO:")
            for alt in self.alternative_diagnoses[:3]:
                report.append(f"  • {alt}")
        
        report.append(f"\n🕒 Analysis completed in {self.detection_time_ms}ms")
        
        return "\n".join(report)


class UnifiedDiseaseDetector:
    """
    Main detection orchestrator combining rule-based and AI approaches
    
    Usage:
        detector = UnifiedDiseaseDetector(
            kindwise_api_key="your_key",
            mode=DetectionMode.HYBRID_FAST
        )
        
        image = cv2.imread("diseased_tomato.jpg")
        result = detector.detect(
            image=image,
            crop_type=CropType.TOMATO,
            latitude=40.7128,
            longitude=-74.0060
        )
        
        print(result.to_farmer_report())
    """
    
    def __init__(self,
                 kindwise_api_key: Optional[str] = None,
                 mode: DetectionMode = DetectionMode.HYBRID_FAST,
                 enable_cache: bool = True,
                 confidence_threshold: float = 0.7):
        """
        Initialize unified detector
        
        Args:
            kindwise_api_key: Kindwise API key (optional for rule-based only)
            mode: Detection strategy
            enable_cache: Enable response caching
            confidence_threshold: Minimum confidence for rule-based acceptance
        """
        self.mode = mode
        self.confidence_threshold = confidence_threshold
        
        # Initialize Kindwise client (if API key provided)
        self.kindwise_client = None
        if kindwise_api_key:
            try:
                self.kindwise_client = KindwiseAPIClient(
                    api_key=kindwise_api_key,
                    enable_caching=enable_cache
                )
                self.ai_available = self.kindwise_client.health_check()
            except Exception as e:
                print(f"⚠️  Kindwise API unavailable: {e}")
                self.ai_available = False
        else:
            self.ai_available = False
        
        # Initialize local detectors
        self.rule_detectors = {
            CropType.TOMATO: TomatoDiseaseDetector(),
            CropType.POTATO: PotatoDiseaseDetector(),
            CropType.CUCUMBER: CucumberDiseaseDetector(),
            CropType.PEPPER: PepperDiseaseDetector(),
            CropType.LETTUCE: LettuceDiseaseDetector(),
            CropType.STRAWBERRY: StrawberryDiseaseDetector(),
            CropType.GRAPE: GrapeDiseaseDetector(),
            CropType.APPLE: AppleDiseaseDetector(),
            CropType.CITRUS: CitrusDiseaseDetector(),
            CropType.BANANA: BananaDiseaseDetector(),
            CropType.MANGO: MangoDiseaseDetector(),
            CropType.PEACH: PeachDiseaseDetector(),
            CropType.OLIVE: OliveDiseaseDetector(),
            CropType.COFFEE: CoffeeDiseaseDetector(),
            CropType.TEA: TeaDiseaseDetector(),
            CropType.ONION: AlliumDiseaseDetector(),
            CropType.GARLIC: AlliumDiseaseDetector(),
            CropType.CABBAGE: CabbageDiseaseDetector(),
            CropType.WATERMELON: WatermelonDiseaseDetector(),
            # New horticultural vegetables (2025-11-04)
            "spinach": SpinachDiseaseDetector(),
            "eggplant": EggplantDiseaseDetector(),
            "sweet_potato": SweetPotatoDiseaseDetector(),
            "carrot": CarrotDiseaseDetector(),
            "broccoli": BroccoliDiseaseDetector(),
        }
        
        print(f"✓ Unified detector initialized")
        print(f"  Mode: {mode.value}")
        print(f"  AI available: {'Yes ✓' if self.ai_available else 'No (rule-based only)'}")
        print(f"  Local detectors: {len(self.rule_detectors)} crops")
    
    def detect(self,
               image: np.ndarray,
               crop_type: CropType,
               latitude: Optional[float] = None,
               longitude: Optional[float] = None,
               variety: Optional[str] = None) -> Optional[UnifiedDiseaseResult]:
        """
        Unified disease detection with intelligent routing
        
        Args:
            image: BGR image from cv2.imread
            crop_type: Crop being analyzed
            latitude: GPS location for regional diseases
            longitude: GPS location
            variety: Specific crop variety (for resistance gene lookup)
        
        Returns:
            UnifiedDiseaseResult with combined analysis
        """
        import time
        start_time = time.time()
        
        # Determine detection strategy
        mode = self._select_detection_mode()
        
        print(f"\n🔍 Analyzing {crop_type.value} using {mode.value} mode...")
        
        # Execute detection based on mode
        if mode == DetectionMode.RULE_BASED_ONLY:
            result = self._detect_rule_based(image, crop_type)
        
        elif mode == DetectionMode.AI_ONLY:
            result = self._detect_ai_only(image, crop_type, latitude, longitude)
        
        elif mode == DetectionMode.HYBRID_FAST:
            result = self._detect_hybrid_fast(image, crop_type, latitude, longitude)
        
        elif mode == DetectionMode.HYBRID_COMPREHENSIVE:
            result = self._detect_hybrid_comprehensive(image, crop_type, latitude, longitude)
        
        else:  # AUTO
            result = self._detect_auto(image, crop_type, latitude, longitude)
        
        if result:
            result.detection_time_ms = int((time.time() - start_time) * 1000)
        
        return result
    
    def _select_detection_mode(self) -> DetectionMode:
        """Intelligent mode selection based on configuration and availability"""
        if self.mode == DetectionMode.AUTO:
            # Auto mode: use hybrid if AI available, else rule-based
            if self.ai_available:
                return DetectionMode.HYBRID_FAST
            else:
                return DetectionMode.RULE_BASED_ONLY
        
        # Use configured mode
        return self.mode
    
    def _detect_rule_based(self,
                          image: np.ndarray,
                          crop_type: CropType) -> Optional[UnifiedDiseaseResult]:
        """Rule-based detection only (offline capable)"""
        detector = self.rule_detectors.get(crop_type)
        if not detector:
            print(f"❌ No rule-based detector for {crop_type.value}")
            return None
        
        print(f"  🔬 Running rule-based analysis...")
        
        # Call crop-specific detector
        # Note: Each detector has different interface, need to standardize
        result = detector.detect(image)
        
        if not result:
            return None
        
        # Convert to unified format
        return self._convert_rule_result_to_unified(result, crop_type)
    
    def _detect_ai_only(self,
                       image: np.ndarray,
                       crop_type: CropType,
                       latitude: Optional[float],
                       longitude: Optional[float]) -> Optional[UnifiedDiseaseResult]:
        """Kindwise AI detection only"""
        if not self.ai_available:
            print(f"❌ AI detection unavailable")
            return None
        
        print(f"  🤖 Calling Kindwise AI...")
        
        response = self.kindwise_client.identify_disease(
            image=image,
            crop_type=crop_type,
            latitude=latitude,
            longitude=longitude
        )
        
        if not response or not response.top1_disease:
            return None
        
        return self._convert_ai_result_to_unified(response)
    
    def _detect_hybrid_fast(self,
                           image: np.ndarray,
                           crop_type: CropType,
                           latitude: Optional[float],
                           longitude: Optional[float]) -> Optional[UnifiedDiseaseResult]:
        """
        Hybrid fast mode:
        1. Try rule-based first (fast, free)
        2. If confidence low, validate with AI
        3. Combine results if both available
        """
        # Step 1: Rule-based detection
        rule_result = self._detect_rule_based(image, crop_type)
        
        if rule_result and rule_result.rule_confidence >= self.confidence_threshold:
            # High confidence from rules, no need for AI validation
            print(f"  ✓ High confidence from rules ({rule_result.rule_confidence:.0%})")
            rule_result.diagnostic_certainty = "Confirmed (rule-based)"
            return rule_result
        
        # Step 2: Low confidence or no detection, use AI
        if self.ai_available:
            print(f"  ⚠️  Low rule confidence, validating with AI...")
            ai_result = self._detect_ai_only(image, crop_type, latitude, longitude)
            
            if ai_result:
                # Combine results
                return self._merge_results(rule_result, ai_result)
        
        # Fallback to rule-based result even if low confidence
        if rule_result:
            rule_result.diagnostic_certainty = "Probable (unvalidated)"
            return rule_result
        
        return None
    
    def _detect_hybrid_comprehensive(self,
                                    image: np.ndarray,
                                    crop_type: CropType,
                                    latitude: Optional[float],
                                    longitude: Optional[float]) -> Optional[UnifiedDiseaseResult]:
        """
        Hybrid comprehensive mode:
        Always run both methods and combine results for maximum accuracy
        """
        rule_result = self._detect_rule_based(image, crop_type)
        ai_result = self._detect_ai_only(image, crop_type, latitude, longitude) if self.ai_available else None
        
        if rule_result and ai_result:
            return self._merge_results(rule_result, ai_result)
        elif rule_result:
            return rule_result
        elif ai_result:
            return ai_result
        else:
            return None
    
    def _detect_auto(self,
                    image: np.ndarray,
                    crop_type: CropType,
                    latitude: Optional[float],
                    longitude: Optional[float]) -> Optional[UnifiedDiseaseResult]:
        """Auto mode with intelligent routing"""
        # Use hybrid fast for best balance of speed, cost, and accuracy
        return self._detect_hybrid_fast(image, crop_type, latitude, longitude)
    
    def _convert_rule_result_to_unified(self,
                                       rule_result: Any,
                                       crop_type: CropType) -> UnifiedDiseaseResult:
        """Convert rule-based detector result to unified format"""
        # Extract disease name and confidence
        # Note: Each detector has different result format, this is generic handling
        
        disease_name = getattr(rule_result, 'disease_name', 'Unknown')
        confidence = getattr(rule_result, 'confidence', 0.5)
        
        confidence_level = self._classify_confidence(confidence)
        
        return UnifiedDiseaseResult(
            disease_name=disease_name,
            confidence=confidence,
            confidence_level=confidence_level,
            detected_by_rules=True,
            rule_confidence=confidence,
            severity=DiseaseSeverity.MODERATE,
            symptoms=[],
            diagnostic_certainty="Rule-based detection",
            economic_impact="Variable depending on severity"
        )
    
    def _convert_ai_result_to_unified(self,
                                     ai_response: KindwiseAPIResponse) -> UnifiedDiseaseResult:
        """Convert Kindwise API response to unified format"""
        top_disease = ai_response.top1_disease
        
        # Extract treatments
        treatments = []
        for treatment in top_disease.treatments:
            treatments.append({
                'category': treatment.category,
                'action': treatment.action,
                'timing': treatment.timing,
                'priority': treatment.priority
            })
        
        # Extract urgent actions
        urgent_actions = [
            t.action for t in top_disease.get_urgent_actions()
        ]
        
        confidence_level = self._classify_confidence(top_disease.confidence)
        
        return UnifiedDiseaseResult(
            disease_name=top_disease.disease_name,
            confidence=top_disease.confidence,
            confidence_level=confidence_level,
            detected_by_ai=True,
            ai_confidence=top_disease.confidence,
            severity=top_disease.severity,
            eppo_code=top_disease.eppo_code.code if top_disease.eppo_code else None,
            symptoms=top_disease.symptoms_observed,
            urgent_actions=urgent_actions,
            treatments=treatments,
            economic_impact=top_disease.economic_impact,
            spread_risk=top_disease.spread_risk,
            alternative_diagnoses=top_disease.similar_diseases,
            diagnostic_certainty="AI-based detection",
            api_cost_usd=0.05  # Estimated cost per API call
        )
    
    def _merge_results(self,
                      rule_result: Optional[UnifiedDiseaseResult],
                      ai_result: Optional[UnifiedDiseaseResult]) -> UnifiedDiseaseResult:
        """
        Intelligent fusion of rule-based and AI results
        
        Strategy:
        1. If both agree on disease: boost confidence
        2. If disagree: use higher confidence, list other as alternative
        3. Combine symptoms and treatments from both sources
        """
        if not rule_result:
            return ai_result
        if not ai_result:
            return rule_result
        
        # Check if both methods agree
        disease_match = (
            rule_result.disease_name.lower() in ai_result.disease_name.lower() or
            ai_result.disease_name.lower() in rule_result.disease_name.lower()
        )
        
        if disease_match:
            # Agreement: boost confidence
            print(f"  ✓ Both methods agree: {rule_result.disease_name}")
            combined_confidence = (rule_result.confidence + ai_result.confidence) / 2
            combined_confidence = min(1.0, combined_confidence * 1.2)  # 20% boost for agreement
            
            return UnifiedDiseaseResult(
                disease_name=ai_result.disease_name,  # Use AI name (more standardized)
                confidence=combined_confidence,
                confidence_level=self._classify_confidence(combined_confidence),
                detected_by_rules=True,
                detected_by_ai=True,
                rule_confidence=rule_result.confidence,
                ai_confidence=ai_result.confidence,
                severity=ai_result.severity,
                eppo_code=ai_result.eppo_code,
                symptoms=list(set(rule_result.symptoms + ai_result.symptoms)),
                urgent_actions=ai_result.urgent_actions,
                treatments=ai_result.treatments,
                economic_impact=ai_result.economic_impact,
                spread_risk=ai_result.spread_risk,
                alternative_diagnoses=[],
                diagnostic_certainty="Confirmed (dual validation)",
                api_cost_usd=ai_result.api_cost_usd
            )
        else:
            # Disagreement: use higher confidence
            print(f"  ⚠️  Methods disagree: Rules={rule_result.disease_name}, AI={ai_result.disease_name}")
            
            if ai_result.confidence > rule_result.confidence:
                primary = ai_result
                primary.alternative_diagnoses.append(rule_result.disease_name)
                primary.diagnostic_certainty = "Probable (AI primary, rules differ)"
            else:
                primary = rule_result
                primary.alternative_diagnoses.append(ai_result.disease_name)
                primary.diagnostic_certainty = "Probable (rules primary, AI differs)"
            
            primary.detected_by_rules = True
            primary.detected_by_ai = True
            return primary
    
    def _classify_confidence(self, confidence: float) -> ConfidenceLevel:
        """Classify numeric confidence into level"""
        if confidence >= 0.90:
            return ConfidenceLevel.VERY_HIGH
        elif confidence >= 0.75:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.50:
            return ConfidenceLevel.MODERATE
        else:
            return ConfidenceLevel.LOW
    
    def batch_detect(self,
                    images: List[np.ndarray],
                    crop_types: List[CropType],
                    latitudes: Optional[List[float]] = None,
                    longitudes: Optional[List[float]] = None) -> List[Optional[UnifiedDiseaseResult]]:
        """Batch processing for multiple images"""
        results = []
        
        for i, (image, crop_type) in enumerate(zip(images, crop_types)):
            lat = latitudes[i] if latitudes else None
            lon = longitudes[i] if longitudes else None
            
            result = self.detect(image, crop_type, lat, lon)
            results.append(result)
        
        return results


# Example usage
if __name__ == "__main__":
    print("Unified Disease Detector - Example Usage")
    print("=" * 60)
    
    # Initialize detector
    detector = UnifiedDiseaseDetector(
        kindwise_api_key=None,  # Will use rule-based only without key
        mode=DetectionMode.AUTO
    )
    
    # Test with sample image
    print("\n📸 Testing with sample image...")
    test_image = np.random.randint(0, 255, (640, 480, 3), dtype=np.uint8)
    
    result = detector.detect(
        image=test_image,
        crop_type=CropType.TOMATO,
        latitude=40.7128,
        longitude=-74.0060
    )
    
    if result:
        print("\n" + result.to_farmer_report())
    else:
        print("❌ No disease detected")
    
    print("\n✓ Example completed")
