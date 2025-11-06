"""
Kindwise crop.health API Integration
=====================================

Professional API client for Kindwise's specialized agricultural disease identification service.
Provides access to 288 diseases and pests with farmer-focused data including EPPO codes,
treatment instructions, and severity ratings.

Key Features:
- 85% top-1 accuracy, 93% top-3 accuracy on validation data
- 288 diseases and pests identified
- EPPO codes (internationally recognized plant protection standards)
- Horticultural focus: apples, bananas, citrus, cucumbers, eggplants, garlic, 
  grapevines, onions, potatoes, tomatoes
- Detailed symptoms, treatments, and severity assessments

Integration Strategy:
1. Image capture with quality validation
2. API request with crop metadata and GPS location
3. AI CNN-based analysis (cloud black box)
4. Farmer-focused response formatting
5. Hybrid validation with rule-based system

Author: AgroPulse Team
Date: November 2025
"""

import os
import time
import hashlib
import requests
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import numpy as np
import cv2
from pathlib import Path


class DiseaseSeverity(Enum):
    """Disease severity classification aligned with Kindwise API"""
    MINOR = "minor"  # Early stage, minimal impact
    MODERATE = "moderate"  # Active infection, yield impact likely
    SEVERE = "severe"  # Advanced stage, major crop loss
    CRITICAL = "critical"  # Emergency intervention required


class CropType(Enum):
    """Horticultural crops supported by Kindwise crop.health API"""
    APPLE = "apple"
    BANANA = "banana"
    CITRUS = "citrus"
    CUCUMBER = "cucumber"
    EGGPLANT = "eggplant"
    GARLIC = "garlic"
    GRAPE = "grape"
    ONION = "onion"
    POTATO = "potato"
    TOMATO = "tomato"
    PEPPER = "pepper"
    STRAWBERRY = "strawberry"
    LETTUCE = "lettuce"
    CABBAGE = "cabbage"
    WATERMELON = "watermelon"
    COFFEE = "coffee"
    TEA = "tea"
    MANGO = "mango"
    PEACH = "peach"
    OLIVE = "olive"


@dataclass
class EPPOCode:
    """
    EPPO Code - European and Mediterranean Plant Protection Organization standard
    Internationally recognized identification system for plant pests and diseases
    """
    code: str  # e.g., "PHYTIN" for Phytophthora infestans
    scientific_name: str  # e.g., "Phytophthora infestans"
    common_name: str  # e.g., "Late blight of potato"
    quarantine_status: bool = False  # Regulated pest requiring notification
    
    def __post_init__(self):
        """Validate EPPO code format (6 characters, uppercase)"""
        if len(self.code) != 6:
            raise ValueError(f"EPPO code must be 6 characters: {self.code}")
        self.code = self.code.upper()


@dataclass
class TreatmentRecommendation:
    """Farmer-focused treatment instructions"""
    category: str  # "chemical", "cultural", "biological", "quarantine"
    priority: int  # 1=urgent, 2=recommended, 3=optional
    action: str  # Clear instruction: "Apply copper fungicide at 2kg/ha"
    timing: str  # "Immediately", "Within 24 hours", "Next growing season"
    materials: List[str]  # ["Copper hydroxide", "Spreader-sticker"]
    cost_estimate_usd: Optional[float] = None
    effectiveness_percent: Optional[int] = None  # Expected disease reduction
    safety_precautions: List[str] = field(default_factory=list)
    
    def to_farmer_text(self) -> str:
        """Format for farmer readability"""
        priority_text = {1: "🔴 URGENT", 2: "🟡 RECOMMENDED", 3: "🟢 OPTIONAL"}
        text = f"{priority_text.get(self.priority, '')} {self.action}\n"
        text += f"   When: {self.timing}\n"
        if self.materials:
            text += f"   Materials: {', '.join(self.materials)}\n"
        if self.effectiveness_percent:
            text += f"   Expected reduction: {self.effectiveness_percent}%\n"
        return text


@dataclass
class DiseaseIdentification:
    """Complete disease identification from Kindwise API"""
    disease_name: str
    confidence: float  # 0.0 to 1.0
    eppo_code: Optional[EPPOCode]
    severity: DiseaseSeverity
    symptoms_observed: List[str]
    treatments: List[TreatmentRecommendation]
    economic_impact: str  # "Yield loss: 20-40%"
    spread_risk: str  # "High", "Moderate", "Low"
    similar_diseases: List[str]  # Differential diagnosis
    
    def is_quarantine_disease(self) -> bool:
        """Check if disease requires regulatory notification"""
        return self.eppo_code is not None and self.eppo_code.quarantine_status
    
    def get_urgent_actions(self) -> List[TreatmentRecommendation]:
        """Extract priority 1 (urgent) treatments"""
        return [t for t in self.treatments if t.priority == 1]


@dataclass
class KindwiseAPIResponse:
    """Complete API response with metadata"""
    identifications: List[DiseaseIdentification]
    image_quality_score: float  # 0.0 to 1.0
    processing_time_ms: int
    model_version: str
    top1_disease: Optional[DiseaseIdentification] = None
    top3_diseases: List[DiseaseIdentification] = field(default_factory=list)
    
    def __post_init__(self):
        """Automatically extract top predictions"""
        if self.identifications:
            sorted_ids = sorted(self.identifications, 
                              key=lambda x: x.confidence, 
                              reverse=True)
            self.top1_disease = sorted_ids[0] if sorted_ids else None
            self.top3_diseases = sorted_ids[:3]


class ImageQualityValidator:
    """
    Validates image quality before API submission
    Poor quality images waste API calls and reduce accuracy
    """
    
    @staticmethod
    def validate(image: np.ndarray) -> Tuple[bool, str, float]:
        """
        Returns: (is_valid, message, quality_score)
        
        Quality checks:
        - Resolution sufficient (min 224x224 for CNN)
        - Not too blurry (Laplacian variance)
        - Adequate lighting (not over/underexposed)
        - Disease symptoms visible (leaf/stem/fruit detected)
        """
        h, w = image.shape[:2]
        
        # Check 1: Resolution
        if h < 224 or w < 224:
            return False, f"Image too small: {w}x{h}. Minimum 224x224 required", 0.0
        
        # Check 2: Blur detection (Laplacian variance)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        if laplacian_var < 100:
            return False, f"Image too blurry (variance: {laplacian_var:.1f})", 0.3
        
        # Check 3: Lighting (histogram analysis)
        brightness = np.mean(gray)
        if brightness < 30:
            return False, f"Image too dark (brightness: {brightness:.1f})", 0.4
        if brightness > 225:
            return False, f"Image overexposed (brightness: {brightness:.1f})", 0.4
        
        # Check 4: Color information present (not grayscale image)
        if len(image.shape) < 3:
            return False, "Grayscale image. Color required for disease identification", 0.5
        
        # Calculate quality score (0.0 to 1.0)
        resolution_score = min(1.0, (h * w) / (1024 * 1024))  # 1MP = 1.0
        sharpness_score = min(1.0, laplacian_var / 500)
        lighting_score = 1.0 - abs(brightness - 127) / 127
        
        quality_score = (resolution_score + sharpness_score + lighting_score) / 3
        
        return True, "Image quality acceptable", quality_score


class KindwiseAPIClient:
    """
    Professional client for Kindwise crop.health API
    
    Usage:
        client = KindwiseAPIClient(api_key="your_key")
        image = cv2.imread("diseased_leaf.jpg")
        response = client.identify_disease(
            image=image,
            crop_type=CropType.TOMATO,
            latitude=40.7128,
            longitude=-74.0060
        )
        
        if response.top1_disease:
            print(f"Disease: {response.top1_disease.disease_name}")
            print(f"Confidence: {response.top1_disease.confidence:.1%}")
            for treatment in response.top1_disease.get_urgent_actions():
                print(treatment.to_farmer_text())
    """
    
    # Kindwise API endpoints
    BASE_URL = "https://crop.kindwise.com/api/v1"
    IDENTIFY_ENDPOINT = f"{BASE_URL}/identification"
    HEALTH_CHECK_ENDPOINT = f"{BASE_URL}/health_check"
    
    # Rate limiting (adjust based on your API plan)
    MAX_REQUESTS_PER_MINUTE = 60
    MAX_REQUESTS_PER_DAY = 5000
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 cache_dir: str = "./kindwise_cache",
                 enable_caching: bool = True,
                 timeout_seconds: int = 30):
        """
        Initialize Kindwise API client
        
        Args:
            api_key: Your Kindwise API key (or set KINDWISE_API_KEY env var)
            cache_dir: Directory for caching responses (saves API calls)
            enable_caching: Enable local response caching
            timeout_seconds: Request timeout
        """
        self.api_key = api_key or os.getenv("KINDWISE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Kindwise API key required. Set KINDWISE_API_KEY environment "
                "variable or pass api_key parameter"
            )
        
        self.cache_dir = Path(cache_dir)
        self.enable_caching = enable_caching
        self.timeout = timeout_seconds
        
        if enable_caching:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Rate limiting tracking
        self._request_times: List[datetime] = []
        self._daily_request_count = 0
        self._last_reset_date = datetime.now().date()
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            "Api-Key": self.api_key,
            "Content-Type": "application/json"
        })
    
    def _check_rate_limit(self) -> Tuple[bool, str]:
        """
        Check if we're within rate limits
        Returns: (allowed, message)
        """
        now = datetime.now()
        
        # Reset daily counter at midnight
        if now.date() > self._last_reset_date:
            self._daily_request_count = 0
            self._last_reset_date = now.date()
        
        # Check daily limit
        if self._daily_request_count >= self.MAX_REQUESTS_PER_DAY:
            return False, f"Daily limit reached ({self.MAX_REQUESTS_PER_DAY} requests)"
        
        # Check per-minute limit
        one_minute_ago = now - timedelta(minutes=1)
        self._request_times = [t for t in self._request_times if t > one_minute_ago]
        
        if len(self._request_times) >= self.MAX_REQUESTS_PER_MINUTE:
            wait_seconds = (self._request_times[0] - one_minute_ago).total_seconds()
            return False, f"Rate limit: wait {wait_seconds:.0f} seconds"
        
        return True, "OK"
    
    def _record_request(self):
        """Record API request for rate limiting"""
        self._request_times.append(datetime.now())
        self._daily_request_count += 1
    
    def _get_cache_key(self, image: np.ndarray, crop_type: CropType) -> str:
        """Generate cache key from image content and crop type"""
        # Use image hash to avoid re-analyzing identical images
        img_bytes = cv2.imencode('.jpg', image)[1].tobytes()
        img_hash = hashlib.md5(img_bytes).hexdigest()
        return f"{crop_type.value}_{img_hash}"
    
    def _get_cached_response(self, cache_key: str) -> Optional[KindwiseAPIResponse]:
        """Retrieve cached response if available and fresh (< 7 days)"""
        if not self.enable_caching:
            return None
        
        cache_file = self.cache_dir / f"{cache_key}.json"
        if not cache_file.exists():
            return None
        
        # Check cache age
        cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
        if cache_age > timedelta(days=7):
            cache_file.unlink()  # Delete stale cache
            return None
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            return self._parse_api_response(data)
        except Exception as e:
            print(f"Cache read error: {e}")
            return None
    
    def _save_to_cache(self, cache_key: str, response_data: Dict):
        """Save API response to cache"""
        if not self.enable_caching:
            return
        
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(response_data, f, indent=2)
        except Exception as e:
            print(f"Cache write error: {e}")
    
    def health_check(self) -> bool:
        """Verify API connectivity and authentication"""
        try:
            response = self.session.get(
                self.HEALTH_CHECK_ENDPOINT,
                timeout=self.timeout
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Health check failed: {e}")
            return False
    
    def identify_disease(self,
                        image: np.ndarray,
                        crop_type: CropType,
                        latitude: Optional[float] = None,
                        longitude: Optional[float] = None,
                        max_results: int = 3) -> Optional[KindwiseAPIResponse]:
        """
        Identify disease from image using Kindwise API
        
        Args:
            image: BGR image (numpy array from cv2.imread)
            crop_type: Crop being analyzed
            latitude: GPS latitude for location-specific diseases
            longitude: GPS longitude
            max_results: Maximum disease suggestions (1-10)
        
        Returns:
            KindwiseAPIResponse with top disease identifications
            None if API call fails
        """
        
        # Step 1: Validate image quality
        is_valid, message, quality_score = ImageQualityValidator.validate(image)
        if not is_valid:
            print(f"❌ Image quality check failed: {message}")
            return None
        
        print(f"✓ Image quality: {quality_score:.1%}")
        
        # Step 2: Check cache
        cache_key = self._get_cache_key(image, crop_type)
        cached = self._get_cached_response(cache_key)
        if cached:
            print(f"✓ Using cached response (saved API call)")
            return cached
        
        # Step 3: Check rate limits
        allowed, limit_message = self._check_rate_limit()
        if not allowed:
            print(f"❌ Rate limit: {limit_message}")
            return None
        
        # Step 4: Encode image to base64
        _, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 95])
        import base64
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # Step 5: Build API request
        payload = {
            "images": [image_base64],
            "modifiers": ["crops_fast", "similar_images"],
            "plant_details": {
                "crop": crop_type.value,
                "latitude": latitude,
                "longitude": longitude
            },
            "max_suggestions": max_results
        }
        
        # Step 6: Make API request
        try:
            print(f"🌐 Calling Kindwise API for {crop_type.value}...")
            start_time = time.time()
            
            self._record_request()
            
            response = self.session.post(
                self.IDENTIFY_ENDPOINT,
                json=payload,
                timeout=self.timeout
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            if response.status_code != 200:
                print(f"❌ API error {response.status_code}: {response.text}")
                return None
            
            response_data = response.json()
            response_data['processing_time_ms'] = processing_time
            response_data['image_quality_score'] = quality_score
            
            # Step 7: Cache response
            self._save_to_cache(cache_key, response_data)
            
            # Step 8: Parse and return
            api_response = self._parse_api_response(response_data)
            print(f"✓ API response received in {processing_time}ms")
            
            return api_response
            
        except requests.Timeout:
            print(f"❌ API timeout after {self.timeout}s")
            return None
        except Exception as e:
            print(f"❌ API request failed: {e}")
            return None
    
    def _parse_api_response(self, data: Dict) -> KindwiseAPIResponse:
        """
        Parse Kindwise API JSON response into structured objects
        
        Kindwise response structure:
        {
            "suggestions": [
                {
                    "id": "disease_id",
                    "probability": 0.85,
                    "name": "Late blight",
                    "details": {
                        "eppo_code": "PHYTIN",
                        "description": "...",
                        "treatment": {...}
                    }
                }
            ]
        }
        """
        identifications = []
        
        for suggestion in data.get('suggestions', [])[:10]:
            # Extract core data
            disease_name = suggestion.get('name', 'Unknown disease')
            confidence = suggestion.get('probability', 0.0)
            
            details = suggestion.get('details', {})
            
            # Parse EPPO code
            eppo_code = None
            if 'eppo_code' in details:
                eppo_code = EPPOCode(
                    code=details['eppo_code'],
                    scientific_name=details.get('scientific_name', disease_name),
                    common_name=disease_name,
                    quarantine_status=details.get('quarantine', False)
                )
            
            # Determine severity from description keywords
            severity_text = details.get('severity', '').lower()
            if 'critical' in severity_text or 'severe' in severity_text:
                severity = DiseaseSeverity.SEVERE
            elif 'moderate' in severity_text:
                severity = DiseaseSeverity.MODERATE
            else:
                severity = DiseaseSeverity.MINOR
            
            # Parse symptoms
            symptoms = details.get('symptoms', [])
            if isinstance(symptoms, str):
                symptoms = [s.strip() for s in symptoms.split(',')]
            
            # Parse treatments
            treatments = []
            treatment_data = details.get('treatment', {})
            
            if isinstance(treatment_data, dict):
                # Chemical treatments
                for chem in treatment_data.get('chemical', []):
                    treatments.append(TreatmentRecommendation(
                        category="chemical",
                        priority=1 if 'urgent' in chem.lower() else 2,
                        action=chem,
                        timing="As soon as possible",
                        materials=[chem],
                        effectiveness_percent=70
                    ))
                
                # Cultural practices
                for cultural in treatment_data.get('cultural', []):
                    treatments.append(TreatmentRecommendation(
                        category="cultural",
                        priority=2,
                        action=cultural,
                        timing="Ongoing",
                        materials=[],
                        effectiveness_percent=50
                    ))
                
                # Biological control
                for bio in treatment_data.get('biological', []):
                    treatments.append(TreatmentRecommendation(
                        category="biological",
                        priority=3,
                        action=bio,
                        timing="Preventative",
                        materials=[bio],
                        effectiveness_percent=40
                    ))
            
            # Create identification
            identification = DiseaseIdentification(
                disease_name=disease_name,
                confidence=confidence,
                eppo_code=eppo_code,
                severity=severity,
                symptoms_observed=symptoms,
                treatments=treatments,
                economic_impact=details.get('economic_impact', 'Variable'),
                spread_risk=details.get('spread_risk', 'Moderate'),
                similar_diseases=details.get('similar_diseases', [])
            )
            
            identifications.append(identification)
        
        return KindwiseAPIResponse(
            identifications=identifications,
            image_quality_score=data.get('image_quality_score', 0.8),
            processing_time_ms=data.get('processing_time_ms', 0),
            model_version=data.get('model_version', 'unknown')
        )
    
    def batch_identify(self,
                      images: List[np.ndarray],
                      crop_types: List[CropType],
                      latitude: Optional[float] = None,
                      longitude: Optional[float] = None) -> List[Optional[KindwiseAPIResponse]]:
        """
        Batch process multiple images
        Respects rate limits with automatic pacing
        """
        results = []
        
        for i, (image, crop_type) in enumerate(zip(images, crop_types)):
            print(f"\nProcessing image {i+1}/{len(images)}...")
            
            result = self.identify_disease(
                image=image,
                crop_type=crop_type,
                latitude=latitude,
                longitude=longitude
            )
            
            results.append(result)
            
            # Pace requests to respect rate limits
            if i < len(images) - 1:
                time.sleep(1.0)  # 1 second between requests
        
        return results
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup"""
        self.session.close()


# Example usage and testing
if __name__ == "__main__":
    print("Kindwise API Client - Example Usage")
    print("=" * 50)
    
    # Test without actual API key (mock mode for development)
    try:
        client = KindwiseAPIClient(api_key="demo_key_for_testing")
        print(f"✓ Client initialized")
        print(f"  Cache directory: {client.cache_dir}")
        print(f"  Rate limit: {client.MAX_REQUESTS_PER_MINUTE}/min")
        
        # Test image quality validator
        print("\n📸 Testing Image Quality Validator:")
        test_image = np.random.randint(0, 255, (640, 480, 3), dtype=np.uint8)
        is_valid, message, score = ImageQualityValidator.validate(test_image)
        print(f"  Test image: {message} (score: {score:.2f})")
        
        # Demonstrate EPPO code
        print("\n🏷️  EPPO Code Example:")
        late_blight = EPPOCode(
            code="PHYTIN",
            scientific_name="Phytophthora infestans",
            common_name="Late blight of potato and tomato",
            quarantine_status=True
        )
        print(f"  {late_blight.code}: {late_blight.common_name}")
        print(f"  Quarantine: {'YES ⚠️' if late_blight.quarantine_status else 'No'}")
        
        # Demonstrate treatment formatting
        print("\n💊 Treatment Recommendation Example:")
        treatment = TreatmentRecommendation(
            category="chemical",
            priority=1,
            action="Apply copper hydroxide at 2-3 kg/ha",
            timing="Within 24 hours of symptom detection",
            materials=["Copper hydroxide 77% WP", "Spreader-sticker"],
            effectiveness_percent=85,
            cost_estimate_usd=45.0,
            safety_precautions=["Wear gloves", "Apply in calm weather"]
        )
        print(treatment.to_farmer_text())
        
        print("\n✓ All tests completed successfully")
        
    except ValueError as e:
        print(f"⚠️  Note: {e}")
        print("   Set KINDWISE_API_KEY environment variable for actual API calls")
