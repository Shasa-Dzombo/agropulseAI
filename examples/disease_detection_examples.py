"""
Disease Detection Examples
==========================

Comprehensive examples showing how to use the AgroPulse disease detection system
in different modes and configurations.

Author: AgroPulse Team
Date: November 2025
"""

import cv2
import numpy as np
from pathlib import Path

# Import detection system
import sys
sys.path.append(str(Path(__file__).parent.parent))

from nvr_system.disease_detection.unified_disease_detector import (
    UnifiedDiseaseDetector,
    DetectionMode,
    CropType
)
from nvr_system.disease_detection.config import load_config


def example_1_quick_start():
    """
    Example 1: Quick Start - Simplest usage
    Automatically uses best available method (AI if configured, else rule-based)
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 1: QUICK START - AUTOMATIC MODE")
    print("=" * 70)
    
    # Initialize detector (will auto-detect if AI available)
    detector = UnifiedDiseaseDetector(
        mode=DetectionMode.AUTO
    )
    
    # Load image
    image = cv2.imread("path/to/diseased_leaf.jpg")
    
    if image is None:
        print("⚠️  No image file provided, using random test image")
        image = np.random.randint(0, 255, (640, 480, 3), dtype=np.uint8)
    
    # Detect disease
    result = detector.detect(
        image=image,
        crop_type=CropType.TOMATO
    )
    
    if result:
        print("\n📄 DETECTION REPORT:")
        print(result.to_farmer_report())
    else:
        print("❌ No disease detected")


def example_2_with_config():
    """
    Example 2: Using Configuration File
    Load settings from config file for consistent behavior
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 2: USING CONFIGURATION FILE")
    print("=" * 70)
    
    # Load configuration
    config = load_config(
        config_file="agropulse_config.json",  # Optional config file
        profile="production"  # Or "development", "offline", "testing"
    )
    config.print_summary()
    
    # Initialize with config
    detector = UnifiedDiseaseDetector(
        kindwise_api_key=config.kindwise.api_key,
        mode=config.detection.detection_mode,
        enable_cache=config.cache.enable_cache,
        confidence_threshold=config.detection.confidence_threshold
    )
    
    # Detect
    image = np.random.randint(0, 255, (640, 480, 3), dtype=np.uint8)
    result = detector.detect(image, CropType.POTATO)
    
    if result:
        print(f"\n✓ Detected: {result.disease_name}")
        print(f"  Confidence: {result.confidence:.1%}")
        print(f"  Method: {result.diagnostic_certainty}")


def example_3_offline_mode():
    """
    Example 3: Offline Mode - No Internet Required
    Uses only rule-based detection, perfect for field deployment
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 3: OFFLINE MODE - RULE-BASED ONLY")
    print("=" * 70)
    
    detector = UnifiedDiseaseDetector(
        mode=DetectionMode.RULE_BASED_ONLY  # No API calls
    )
    
    print("✓ Detector initialized in offline mode")
    print("  - No internet required")
    print("  - No API costs")
    print("  - Fast local processing")
    print("  - 145+ diseases covered")
    
    # Batch processing example
    images = [
        np.random.randint(0, 255, (640, 480, 3), dtype=np.uint8)
        for _ in range(3)
    ]
    
    crop_types = [CropType.TOMATO, CropType.POTATO, CropType.CUCUMBER]
    
    results = detector.batch_detect(images, crop_types)
    
    print(f"\n✓ Batch processed {len(results)} images")
    for i, result in enumerate(results):
        if result:
            print(f"  {i+1}. {crop_types[i].value}: {result.disease_name} ({result.confidence:.0%})")


def example_4_ai_only_mode():
    """
    Example 4: AI Only Mode - Kindwise API
    Uses Kindwise's 288 disease database with EPPO codes
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 4: AI ONLY MODE - KINDWISE API")
    print("=" * 70)
    
    # Requires API key (set KINDWISE_API_KEY environment variable)
    detector = UnifiedDiseaseDetector(
        kindwise_api_key="your_api_key_here",  # Or set via env var
        mode=DetectionMode.AI_ONLY
    )
    
    if not detector.ai_available:
        print("⚠️  AI not available - set KINDWISE_API_KEY to use this mode")
        return
    
    print("✓ AI detection enabled")
    print("  - 288 diseases and pests")
    print("  - 85% top-1, 93% top-3 accuracy")
    print("  - EPPO codes included")
    print("  - Treatment recommendations")
    
    image = np.random.randint(0, 255, (640, 480, 3), dtype=np.uint8)
    
    result = detector.detect(
        image=image,
        crop_type=CropType.APPLE,
        latitude=40.7128,  # GPS for location-specific diseases
        longitude=-74.0060
    )
    
    if result:
        print(f"\n✓ Detected: {result.disease_name}")
        if result.eppo_code:
            print(f"  EPPO Code: {result.eppo_code}")
        print(f"  Severity: {result.severity.value}")
        print(f"\n💊 Urgent Actions:")
        for action in result.urgent_actions[:3]:
            print(f"  • {action}")


def example_5_hybrid_comprehensive():
    """
    Example 5: Hybrid Comprehensive Mode
    Runs both rule-based and AI, combines results for highest accuracy
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 5: HYBRID COMPREHENSIVE MODE")
    print("=" * 70)
    
    detector = UnifiedDiseaseDetector(
        mode=DetectionMode.HYBRID_COMPREHENSIVE  # Both methods always
    )
    
    print("✓ Hybrid comprehensive mode")
    print("  - Runs both rule-based and AI")
    print("  - Highest accuracy")
    print("  - Confidence boost when methods agree")
    print("  - Differential diagnosis when disagreement")
    
    image = np.random.randint(0, 255, (640, 480, 3), dtype=np.uint8)
    
    result = detector.detect(
        image=image,
        crop_type=CropType.GRAPE,
        latitude=41.8781,
        longitude=-87.6298
    )
    
    if result:
        print(f"\n✓ Detection Summary:")
        print(f"  Disease: {result.disease_name}")
        print(f"  Combined Confidence: {result.confidence:.1%}")
        print(f"  Detected by rules: {'Yes ✓' if result.detected_by_rules else 'No'}")
        print(f"  Detected by AI: {'Yes ✓' if result.detected_by_ai else 'No'}")
        print(f"  Certainty: {result.diagnostic_certainty}")
        
        if result.alternative_diagnoses:
            print(f"\n⚠️  Alternative diagnoses:")
            for alt in result.alternative_diagnoses:
                print(f"  • {alt}")


def example_6_hybrid_fast_recommended():
    """
    Example 6: Hybrid Fast Mode (RECOMMENDED)
    Best balance of speed, cost, and accuracy
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 6: HYBRID FAST MODE (RECOMMENDED)")
    print("=" * 70)
    
    detector = UnifiedDiseaseDetector(
        mode=DetectionMode.HYBRID_FAST,  # Recommended for production
        confidence_threshold=0.7  # Only use AI if rule confidence < 70%
    )
    
    print("✓ Hybrid fast mode (recommended)")
    print("  - Rule-based first (fast, free)")
    print("  - AI validation only if needed")
    print("  - Minimizes API costs")
    print("  - Good accuracy/speed balance")
    
    # Simulate multiple detections
    test_cases = [
        (CropType.TOMATO, "Clear late blight symptoms"),
        (CropType.CUCUMBER, "Ambiguous leaf spotting"),
        (CropType.STRAWBERRY, "Early disease stage")
    ]
    
    for crop, description in test_cases:
        print(f"\n🔍 Analyzing {crop.value}: {description}")
        
        image = np.random.randint(0, 255, (640, 480, 3), dtype=np.uint8)
        result = detector.detect(image, crop)
        
        if result:
            print(f"  ✓ {result.disease_name} ({result.confidence:.0%})")
            print(f"    Method: {result.diagnostic_certainty}")
            if result.api_cost_usd > 0:
                print(f"    API cost: ${result.api_cost_usd:.3f}")


def example_7_with_gps_location():
    """
    Example 7: Using GPS Location
    Location helps identify region-specific diseases and emerging threats
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 7: GPS-BASED DISEASE IDENTIFICATION")
    print("=" * 70)
    
    detector = UnifiedDiseaseDetector(mode=DetectionMode.AUTO)
    
    # Different locations
    locations = [
        ("California, USA", 36.7783, -119.4179),
        ("Kenya", -1.2921, 36.8219),
        ("India", 20.5937, 78.9629),
    ]
    
    image = np.random.randint(0, 255, (640, 480, 3), dtype=np.uint8)
    
    for location_name, lat, lon in locations:
        print(f"\n📍 {location_name} ({lat:.4f}, {lon:.4f})")
        
        result = detector.detect(
            image=image,
            crop_type=CropType.COFFEE,
            latitude=lat,
            longitude=lon
        )
        
        if result:
            print(f"  ✓ {result.disease_name}")
            print(f"    Spread risk: {result.spread_risk}")
            print(f"    Economic impact: {result.economic_impact}")


def example_8_error_handling():
    """
    Example 8: Robust Error Handling
    Handle various failure scenarios gracefully
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 8: ERROR HANDLING AND EDGE CASES")
    print("=" * 70)
    
    detector = UnifiedDiseaseDetector(mode=DetectionMode.AUTO)
    
    # Test case 1: Invalid image
    print("\n1. Testing with None image:")
    result = detector.detect(None, CropType.TOMATO)
    print(f"   Result: {'✓ Handled gracefully' if result is None else '❌ Unexpected'}")
    
    # Test case 2: Very small image
    print("\n2. Testing with tiny image (100x100):")
    tiny_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    result = detector.detect(tiny_image, CropType.POTATO)
    print(f"   Result: {result.disease_name if result else 'Image too small (expected)'}")
    
    # Test case 3: Unsupported crop
    print("\n3. Testing with unsupported crop:")
    image = np.random.randint(0, 255, (640, 480, 3), dtype=np.uint8)
    try:
        # This would require adding the crop to CropType enum
        result = detector.detect(image, CropType.BANANA)
        print(f"   Result: {result.disease_name if result else 'No detection'}")
    except Exception as e:
        print(f"   Handled: {type(e).__name__}")
    
    # Test case 4: No disease present (healthy plant)
    print("\n4. Testing with healthy plant (no disease):")
    result = detector.detect(image, CropType.LETTUCE)
    print(f"   Result: {result.disease_name if result else 'Healthy/No detection (expected)'}")


def example_9_performance_comparison():
    """
    Example 9: Performance Comparison
    Compare different detection modes for speed and accuracy
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 9: PERFORMANCE COMPARISON")
    print("=" * 70)
    
    import time
    
    image = np.random.randint(0, 255, (640, 480, 3), dtype=np.uint8)
    
    modes = [
        DetectionMode.RULE_BASED_ONLY,
        DetectionMode.HYBRID_FAST,
        DetectionMode.HYBRID_COMPREHENSIVE,
    ]
    
    print("\nProcessing same image with different modes:")
    print(f"{'Mode':<25} {'Time (ms)':<12} {'Confidence':<12} {'API Cost'}")
    print("-" * 70)
    
    for mode in modes:
        detector = UnifiedDiseaseDetector(mode=mode)
        
        start = time.time()
        result = detector.detect(image, CropType.TOMATO)
        duration = int((time.time() - start) * 1000)
        
        if result:
            print(f"{mode.value:<25} {duration:<12} {result.confidence:.1%:<12} ${result.api_cost_usd:.3f}")
        else:
            print(f"{mode.value:<25} {duration:<12} {'N/A':<12} $0.000")


def run_all_examples():
    """Run all examples sequentially"""
    print("\n" + "=" * 70)
    print("AGROPULSE DISEASE DETECTION - COMPREHENSIVE EXAMPLES")
    print("=" * 70)
    
    examples = [
        ("Quick Start", example_1_quick_start),
        ("Configuration File", example_2_with_config),
        ("Offline Mode", example_3_offline_mode),
        ("AI Only Mode", example_4_ai_only_mode),
        ("Hybrid Comprehensive", example_5_hybrid_comprehensive),
        ("Hybrid Fast (Recommended)", example_6_hybrid_fast_recommended),
        ("GPS Location", example_7_with_gps_location),
        ("Error Handling", example_8_error_handling),
        ("Performance Comparison", example_9_performance_comparison),
    ]
    
    for name, func in examples:
        try:
            func()
        except Exception as e:
            print(f"\n❌ Example '{name}' failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("✓ ALL EXAMPLES COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="AgroPulse Disease Detection Examples"
    )
    parser.add_argument(
        '--example',
        type=int,
        choices=range(1, 10),
        help='Run specific example (1-9), or all if not specified'
    )
    
    args = parser.parse_args()
    
    if args.example:
        examples_map = {
            1: example_1_quick_start,
            2: example_2_with_config,
            3: example_3_offline_mode,
            4: example_4_ai_only_mode,
            5: example_5_hybrid_comprehensive,
            6: example_6_hybrid_fast_recommended,
            7: example_7_with_gps_location,
            8: example_8_error_handling,
            9: example_9_performance_comparison,
        }
        examples_map[args.example]()
    else:
        run_all_examples()
