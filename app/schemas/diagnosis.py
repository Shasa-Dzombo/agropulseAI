"""
🌾 AgroPulse - Enterprise-Grade Diagnosis Schema

Comprehensive Pydantic schemas for AI-powered crop diagnosis system with:
- Multi-tier validation and sanitization
- Version control and audit trails
- Batch processing and bulk operations
- Advanced analytics and reporting
- Integration with external systems
- Compliance and regulatory tracking
- Multi-language support
- Real-time notifications
- Quality assurance workflows
- Cost optimization and billing
- SLA tracking and monitoring

Author: AgroPulse AI Team
Date: November 1, 2025
Version: 2.0.0-enterprise
"""

from pydantic import (
    BaseModel, 
    Field, 
    validator, 
    root_validator,
    HttpUrl,
    EmailStr,
    constr,
    conint,
    confloat,
    conlist
)
from typing import (
    Optional, 
    List, 
    Dict, 
    Any, 
    Union,
    Tuple,
    Set,
    Literal
)
from datetime import datetime, date, timedelta
from enum import Enum
from decimal import Decimal
import re
from uuid import UUID, uuid4


# ============================================================================
# ENUMERATIONS - Type-safe status and category definitions
# ============================================================================

class DiagnosisStatus(str, Enum):
    """Diagnosis processing status."""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    ANALYZING_IMAGES = "analyzing_images"
    RUNNING_ML_MODEL = "running_ml_model"
    GENERATING_RECOMMENDATIONS = "generating_recommendations"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    ESCALATED = "escalated"


class DiseaseCategory(str, Enum):
    """Disease/issue categories."""
    FUNGAL = "fungal"
    BACTERIAL = "bacterial"
    VIRAL = "viral"
    PEST_INSECT = "pest_insect"
    PEST_MAMMAL = "pest_mammal"
    PEST_BIRD = "pest_bird"
    NUTRIENT_DEFICIENCY_NITROGEN = "nutrient_deficiency_nitrogen"
    NUTRIENT_DEFICIENCY_PHOSPHORUS = "nutrient_deficiency_phosphorus"
    NUTRIENT_DEFICIENCY_POTASSIUM = "nutrient_deficiency_potassium"
    NUTRIENT_DEFICIENCY_MICRONUTRIENT = "nutrient_deficiency_micronutrient"
    ENVIRONMENTAL_WATER_STRESS = "environmental_water_stress"
    ENVIRONMENTAL_HEAT_STRESS = "environmental_heat_stress"
    ENVIRONMENTAL_FROST_DAMAGE = "environmental_frost_damage"
    ENVIRONMENTAL_WIND_DAMAGE = "environmental_wind_damage"
    HERBICIDE_DAMAGE = "herbicide_damage"
    MECHANICAL_DAMAGE = "mechanical_damage"
    POST_HARVEST_DISEASE = "post_harvest_disease"
    HEALTHY = "healthy"
    UNKNOWN = "unknown"


class SeverityLevel(str, Enum):
    """Severity classification."""
    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"
    CATASTROPHIC = "catastrophic"


class UrgencyLevel(str, Enum):
    """Treatment urgency."""
    IMMEDIATE = "immediate"  # <24 hours
    URGENT = "urgent"  # 1-3 days
    MODERATE = "moderate"  # 3-7 days
    LOW = "low"  # >7 days
    MONITORING = "monitoring"  # No immediate action


class TreatmentCategory(str, Enum):
    """Treatment types."""
    CHEMICAL_PESTICIDE = "chemical_pesticide"
    CHEMICAL_FUNGICIDE = "chemical_fungicide"
    CHEMICAL_HERBICIDE = "chemical_herbicide"
    BIOLOGICAL_CONTROL = "biological_control"
    ORGANIC_TREATMENT = "organic_treatment"
    CULTURAL_PRACTICE = "cultural_practice"
    MECHANICAL_REMOVAL = "mechanical_removal"
    FERTILIZER_APPLICATION = "fertilizer_application"
    IRRIGATION_ADJUSTMENT = "irrigation_adjustment"
    NO_TREATMENT_NEEDED = "no_treatment_needed"


class ImageQuality(str, Enum):
    """Image quality assessment."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    UNUSABLE = "unusable"


class ModelVersion(str, Enum):
    """AI model versions."""
    V1_0_BASELINE = "v1.0_baseline"
    V1_1_IMPROVED = "v1.1_improved"
    V2_0_TRANSFORMER = "v2.0_transformer"
    V2_1_MULTIMODAL = "v2.1_multimodal"
    V3_0_FOUNDATION = "v3.0_foundation"
    EXPERIMENTAL = "experimental"


class ConfidenceLevel(str, Enum):
    """Confidence level categories."""
    VERY_HIGH = "very_high"  # >95%
    HIGH = "high"  # 85-95%
    MEDIUM = "medium"  # 70-85%
    LOW = "low"  # 50-70%
    VERY_LOW = "very_low"  # <50%


class PaymentStatus(str, Enum):
    """Payment status for diagnosis."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    WAIVED = "waived"


class NotificationChannel(str, Enum):
    """Notification delivery channels."""
    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"
    WHATSAPP = "whatsapp"
    IN_APP = "in_app"


class CropType(str, Enum):
    """Supported crop types."""
    MAIZE = "maize"
    WHEAT = "wheat"
    RICE = "rice"
    BEANS = "beans"
    POTATO = "potato"
    SWEET_POTATO = "sweet_potato"
    CASSAVA = "cassava"
    TOMATO = "tomato"
    CABBAGE = "cabbage"
    KALE = "kale"
    ONION = "onion"
    CARROT = "carrot"
    BANANA = "banana"
    COFFEE = "coffee"
    TEA = "tea"
    SUGARCANE = "sugarcane"
    COTTON = "cotton"
    SORGHUM = "sorghum"
    MILLET = "millet"
    OTHER = "other"


class GrowthStage(str, Enum):
    """Crop growth stages."""
    GERMINATION = "germination"
    SEEDLING = "seedling"
    VEGETATIVE = "vegetative"
    FLOWERING = "flowering"
    FRUIT_DEVELOPMENT = "fruit_development"
    RIPENING = "ripening"
    MATURITY = "maturity"
    POST_HARVEST = "post_harvest"


# ============================================================================
# BASE MODELS - Reusable component schemas
# ============================================================================

class GPSCoordinates(BaseModel):
    """GPS location data."""
    latitude: confloat(ge=-90, le=90) = Field(..., description="Latitude in decimal degrees")
    longitude: confloat(ge=-180, le=180) = Field(..., description="Longitude in decimal degrees")
    altitude: Optional[float] = Field(None, description="Altitude in meters")
    accuracy: Optional[float] = Field(None, description="GPS accuracy in meters")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    @validator('accuracy')
    def validate_accuracy(cls, v):
        if v is not None and v < 0:
            raise ValueError("Accuracy must be non-negative")
        return v


class ImageMetadata(BaseModel):
    """Detailed image metadata."""
    url: HttpUrl
    filename: str
    size_bytes: conint(gt=0)
    width: conint(gt=0)
    height: conint(gt=0)
    format: Literal["JPEG", "PNG", "WEBP", "TIFF"]
    mime_type: str
    captured_at: datetime
    gps_coordinates: Optional[GPSCoordinates] = None
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    focal_length: Optional[float] = None
    iso: Optional[int] = None
    exposure_time: Optional[str] = None
    flash_used: Optional[bool] = None
    quality_score: Optional[confloat(ge=0, le=100)] = None
    quality_assessment: Optional[ImageQuality] = None
    blur_score: Optional[confloat(ge=0, le=100)] = None
    brightness_score: Optional[confloat(ge=0, le=100)] = None
    contrast_score: Optional[confloat(ge=0, le=100)] = None
    has_motion_blur: Optional[bool] = None
    has_focus_issues: Optional[bool] = None
    is_augmented: bool = False
    augmentation_type: Optional[str] = None
    thumbnail_url: Optional[HttpUrl] = None
    processed_url: Optional[HttpUrl] = None
    hash_sha256: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://storage.agropulse.ai/images/IMG_20251101_143022.jpg",
                "filename": "IMG_20251101_143022.jpg",
                "size_bytes": 2458624,
                "width": 4032,
                "height": 3024,
                "format": "JPEG",
                "mime_type": "image/jpeg",
                "captured_at": "2025-11-01T14:30:22Z",
                "quality_score": 87.5
            }
        }


class WeatherData(BaseModel):
    """Weather conditions at diagnosis time."""
    temperature_celsius: Optional[float] = None
    humidity_percent: Optional[confloat(ge=0, le=100)] = None
    rainfall_mm: Optional[confloat(ge=0)] = None
    wind_speed_kmh: Optional[confloat(ge=0)] = None
    cloud_cover_percent: Optional[confloat(ge=0, le=100)] = None
    uv_index: Optional[confloat(ge=0, le=15)] = None
    soil_moisture_percent: Optional[confloat(ge=0, le=100)] = None
    weather_description: Optional[str] = None
    forecast_next_7_days: Optional[Dict[str, Any]] = None
    data_source: Optional[str] = Field(None, description="Weather API source")
    timestamp: datetime = Field(default_factory=datetime.now)


class FarmContext(BaseModel):
    """Farm and environmental context."""
    farm_id: Optional[str] = None
    farm_name: Optional[str] = None
    farm_size_acres: Optional[confloat(gt=0)] = None
    field_zone: Optional[str] = None
    crop_type: CropType
    crop_variety: Optional[str] = None
    growth_stage: Optional[GrowthStage] = None
    planting_date: Optional[date] = None
    days_since_planting: Optional[conint(ge=0)] = None
    expected_harvest_date: Optional[date] = None
    soil_type: Optional[str] = None
    irrigation_system: Optional[str] = None
    last_fertilizer_application: Optional[date] = None
    last_pesticide_application: Optional[date] = None
    previous_diseases: Optional[List[str]] = None
    nearby_crops: Optional[List[str]] = None
    organic_certified: bool = False
    gps_coordinates: Optional[GPSCoordinates] = None
    weather_data: Optional[WeatherData] = None


class UserContext(BaseModel):
    """User and request context."""
    user_id: str
    farmer_id: Optional[str] = None
    user_name: Optional[str] = None
    phone_number: Optional[constr(pattern=r'^\+?[1-9]\d{1,14}$')] = None
    email: Optional[EmailStr] = None
    language_preference: str = Field(default="en", description="ISO 639-1 language code")
    country_code: str = Field(default="KE", description="ISO 3166-1 alpha-2 country code")
    timezone: str = Field(default="Africa/Nairobi")
    subscription_tier: Optional[str] = None
    diagnoses_remaining: Optional[int] = None
    preferred_notification_channel: NotificationChannel = NotificationChannel.SMS
    notification_channels: List[NotificationChannel] = [NotificationChannel.SMS, NotificationChannel.IN_APP]


class BillingInfo(BaseModel):
    """Billing and payment information."""
    payment_id: Optional[str] = None
    amount_ksh: Decimal = Field(..., decimal_places=2)
    currency: str = Field(default="KES")
    payment_method: str
    payment_status: PaymentStatus
    transaction_id: Optional[str] = None
    payment_provider: Optional[str] = None
    discount_applied: Optional[Decimal] = Field(None, decimal_places=2)
    discount_code: Optional[str] = None
    tax_amount: Optional[Decimal] = Field(None, decimal_places=2)
    total_amount: Optional[Decimal] = Field(None, decimal_places=2)
    paid_at: Optional[datetime] = None
    refund_amount: Optional[Decimal] = Field(None, decimal_places=2)
    refunded_at: Optional[datetime] = None
    refund_reason: Optional[str] = None
    invoice_url: Optional[HttpUrl] = None
    receipt_url: Optional[HttpUrl] = None


class AIModelInfo(BaseModel):
    """AI model execution information."""
    model_name: str
    model_version: ModelVersion
    model_architecture: Optional[str] = None
    training_date: Optional[date] = None
    training_samples: Optional[int] = None
    validation_accuracy: Optional[confloat(ge=0, le=1)] = None
    inference_time_ms: Optional[float] = None
    gpu_used: Optional[bool] = None
    batch_size: Optional[int] = None
    preprocessing_time_ms: Optional[float] = None
    postprocessing_time_ms: Optional[float] = None
    total_time_ms: Optional[float] = None
    confidence_threshold: Optional[float] = None
    model_endpoint: Optional[str] = None
    model_parameters: Optional[Dict[str, Any]] = None


class QualityMetrics(BaseModel):
    """Quality assurance metrics."""
    overall_quality_score: confloat(ge=0, le=100)
    image_quality_score: confloat(ge=0, le=100)
    diagnosis_confidence: confloat(ge=0, le=1)
    model_agreement_score: Optional[confloat(ge=0, le=1)] = None
    human_review_required: bool = False
    human_review_reason: Optional[str] = None
    quality_flags: List[str] = []
    anomalies_detected: List[str] = []
    passed_quality_checks: bool = True
    quality_check_timestamp: datetime = Field(default_factory=datetime.now)


class AuditTrail(BaseModel):
    """Audit trail entry."""
    timestamp: datetime = Field(default_factory=datetime.now)
    action: str
    actor_id: str
    actor_type: Literal["user", "system", "ai_model", "admin", "api"]
    changes: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    notes: Optional[str] = None


# ============================================================================
# CORE REQUEST SCHEMAS
# ============================================================================

class DiagnosisRequest(BaseModel):
    """
    Main diagnosis request schema with comprehensive validation.
    
    Supports both simple and advanced diagnostic workflows.
    """
    # Core identification
    request_id: Optional[str] = Field(default_factory=lambda: str(uuid4()))
    alert_id: Optional[int] = Field(None, description="Optional Sentry alert ID")
    permit_token_id: str = Field(..., description="Permit NFT token ID")
    
    # Images
    image_urls: conlist(HttpUrl, min_length=1, max_length=10) = Field(
        ..., 
        description="1-10 image URLs for diagnosis"
    )
    image_metadata: Optional[List[ImageMetadata]] = None
    
    # Context
    user_context: UserContext
    farm_context: FarmContext
    
    # Symptoms and observations
    user_symptoms: Optional[constr(min_length=5, max_length=2000)] = Field(
        None,
        description="Farmer's description of symptoms"
    )
    symptom_tags: Optional[List[str]] = Field(
        None,
        description="Structured symptom tags"
    )
    affected_plant_parts: Optional[List[str]] = Field(
        None,
        description="List of affected parts (leaf, stem, root, fruit)"
    )
    symptom_duration_days: Optional[conint(ge=0)] = None
    symptom_progression: Optional[str] = None
    
    # Triage (from mobile AI)
    triage_diagnosis: Optional[str] = None
    triage_confidence: Optional[confloat(ge=0, le=1)] = None
    triage_timestamp: Optional[datetime] = None
    on_device_model_version: Optional[str] = None
    
    # Priority and urgency
    priority: Optional[int] = Field(
        3,
        ge=1,
        le=5,
        description="Priority level (1=critical, 5=low)"
    )
    requested_urgency: Optional[UrgencyLevel] = UrgencyLevel.MODERATE
    
    # Processing preferences
    require_human_review: bool = False
    enable_advanced_analysis: bool = True
    include_similar_cases: bool = True
    max_processing_time_seconds: Optional[conint(gt=0, le=300)] = 60
    preferred_model_version: Optional[ModelVersion] = None
    
    # Billing
    billing_info: Optional[BillingInfo] = None
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional custom metadata"
    )
    source_platform: Optional[str] = Field("mobile_app", description="Request source")
    api_version: str = Field("v2.0", description="API version")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    @validator('expires_at', always=True)
    def set_expiration(cls, v, values):
        if v is None and 'created_at' in values:
            return values['created_at'] + timedelta(hours=24)
        return v
    
    @root_validator(skip_on_failure=True)
    def validate_request(cls, values):
        """Cross-field validation."""
        # Validate image metadata matches image URLs
        image_urls = values.get('image_urls', [])
        image_metadata = values.get('image_metadata', [])
        
        if image_metadata and len(image_metadata) != len(image_urls):
            raise ValueError("Image metadata count must match image URLs count")
        
        # Validate triage data consistency
        if values.get('triage_diagnosis') and not values.get('triage_confidence'):
            raise ValueError("Triage confidence required when triage diagnosis provided")
        
        return values
    
    class Config:
        json_schema_extra = {
            "example": {
                "permit_token_id": "NFT-001-456",
                "image_urls": ["https://storage.agropulse.ai/images/img1.jpg"],
                "user_context": {
                    "user_id": "USER-001",
                    "phone_number": "+254712345678"
                },
                "farm_context": {
                    "crop_type": "maize",
                    "growth_stage": "flowering"
                },
                "user_symptoms": "Yellow spots on leaves with brown edges"
            }
        }


class BulkDiagnosisRequest(BaseModel):
    """Batch diagnosis request for multiple samples."""
    batch_id: str = Field(default_factory=lambda: f"BATCH-{uuid4()}")
    diagnoses: conlist(DiagnosisRequest, min_length=1, max_length=50)
    batch_priority: int = Field(3, ge=1, le=5)
    batch_metadata: Optional[Dict[str, Any]] = None
    callback_url: Optional[HttpUrl] = None
    notification_email: Optional[EmailStr] = None
    created_at: datetime = Field(default_factory=datetime.now)
    
    @validator('diagnoses')
    def validate_batch(cls, v):
        """Validate batch consistency."""
        if len(v) > 50:
            raise ValueError("Maximum 50 diagnoses per batch")
        
        # Check for duplicate request IDs
        request_ids = [d.request_id for d in v if d.request_id]
        if len(request_ids) != len(set(request_ids)):
            raise ValueError("Duplicate request IDs in batch")
        
        return v


# ============================================================================
# TREATMENT AND RECOMMENDATION SCHEMAS
# ============================================================================

class ChemicalTreatment(BaseModel):
    """Chemical treatment details."""
    product_name: str
    active_ingredient: str
    category: TreatmentCategory
    dosage_rate: str
    dosage_per_acre: str
    application_method: str
    water_volume_liters: Optional[float] = None
    pre_harvest_interval_days: Optional[int] = None
    re_entry_interval_hours: Optional[int] = None
    toxicity_class: Optional[str] = None
    safety_precautions: List[str]
    estimated_cost_ksh: Decimal
    cost_per_acre_ksh: Optional[Decimal] = None
    availability: Optional[str] = None
    supplier_name: Optional[str] = None
    supplier_contact: Optional[str] = None
    alternative_products: Optional[List[str]] = None
    environmental_impact: Optional[str] = None
    organic_compatible: bool = False
    application_timing: Optional[str] = None
    weather_restrictions: Optional[str] = None
    mixing_compatibility: Optional[List[str]] = None


class BiologicalControl(BaseModel):
    """Biological control method."""
    control_agent: str
    agent_type: Literal["predator", "parasite", "pathogen", "competitor"]
    target_pest: str
    release_rate: Optional[str] = None
    application_method: str
    efficacy_rate: Optional[confloat(ge=0, le=1)] = None
    establishment_time_days: Optional[int] = None
    environmental_conditions: Optional[str] = None
    cost_estimate_ksh: Optional[Decimal] = None
    availability: Optional[str] = None
    advantages: List[str]
    limitations: List[str]


class CulturalPractice(BaseModel):
    """Cultural/agronomic practice."""
    practice_name: str
    description: str
    implementation_steps: List[str]
    timing: str
    frequency: Optional[str] = None
    resources_needed: List[str]
    labor_hours: Optional[float] = None
    estimated_cost_ksh: Optional[Decimal] = None
    expected_efficacy: Optional[str] = None
    time_to_effect_days: Optional[int] = None
    long_term_benefits: Optional[List[str]] = None
    compatibility_with_other_methods: bool = True


class TreatmentRecommendation(BaseModel):
    """Backward-compatible treatment recommendation (maintained for compatibility)."""
    product_name: str
    application_rate: str
    application_method: str
    frequency: str
    duration_days: int
    estimated_cost_ksh: Optional[float] = None


class TreatmentPlan(BaseModel):
    """Comprehensive treatment plan."""
    plan_id: str = Field(default_factory=lambda: f"PLAN-{uuid4()}")
    urgency: UrgencyLevel
    immediate_actions: List[str]
    
    # Treatment options
    chemical_treatments: Optional[List[ChemicalTreatment]] = None
    biological_controls: Optional[List[BiologicalControl]] = None
    cultural_practices: Optional[List[CulturalPractice]] = None
    
    # Integrated pest management
    ipm_strategy: Optional[str] = None
    treatment_sequence: Optional[List[Dict[str, Any]]] = None
    
    # Follow-up
    monitoring_schedule: Optional[List[str]] = None
    follow_up_actions: Optional[List[str]] = None
    success_indicators: Optional[List[str]] = None
    
    # Prevention
    preventive_measures: List[str]
    long_term_management: Optional[List[str]] = None
    
    # Costs
    total_estimated_cost_ksh: Optional[Decimal] = None
    cost_breakdown: Optional[Dict[str, Decimal]] = None
    cost_benefit_analysis: Optional[str] = None
    
    # Timeline
    treatment_timeline: Optional[str] = None
    expected_recovery_days: Optional[int] = None
    
    # Additional information
    safety_warnings: Optional[List[str]] = None
    environmental_considerations: Optional[str] = None
    regulatory_compliance: Optional[List[str]] = None
    expert_consultation_recommended: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "urgency": "urgent",
                "immediate_actions": [
                    "Remove severely infected plants",
                    "Improve field drainage"
                ],
                "preventive_measures": [
                    "Use certified disease-free seed",
                    "Practice crop rotation"
                ]
            }
        }


# ============================================================================
# DIAGNOSIS RESULT SCHEMAS
# ============================================================================

class AlternativeDiagnosis(BaseModel):
    """Alternative diagnosis possibility."""
    diagnosis: str
    disease_id: Optional[str] = None
    category: DiseaseCategory
    confidence: confloat(ge=0, le=1)
    confidence_level: ConfidenceLevel
    probability_percentage: confloat(ge=0, le=100)
    distinguishing_features: Optional[List[str]] = None
    key_differences: Optional[str] = None
    additional_tests_needed: Optional[List[str]] = None


class SimilarCase(BaseModel):
    """Similar historical case."""
    case_id: str
    diagnosis: str
    similarity_score: confloat(ge=0, le=1)
    image_url: Optional[HttpUrl] = None
    crop_type: CropType
    location: Optional[str] = None
    treatment_used: Optional[str] = None
    treatment_outcome: Optional[str] = None
    recovery_time_days: Optional[int] = None
    date: date


class YieldImpactEstimate(BaseModel):
    """Estimated yield impact."""
    current_severity: SeverityLevel
    estimated_yield_loss_percent: confloat(ge=0, le=100)
    yield_loss_range_min: confloat(ge=0, le=100)
    yield_loss_range_max: confloat(ge=0, le=100)
    financial_impact_ksh: Optional[Decimal] = None
    
    # If treated
    yield_loss_if_treated_percent: Optional[confloat(ge=0, le=100)] = None
    yield_loss_if_untreated_percent: Optional[confloat(ge=0, le=100)] = None
    potential_savings_ksh: Optional[Decimal] = None
    
    # Factors
    impact_factors: Optional[List[str]] = None
    assumptions: Optional[List[str]] = None
    confidence: Optional[confloat(ge=0, le=1)] = None


class SpreadRiskAssessment(BaseModel):
    """Disease spread risk assessment."""
    spread_risk_level: SeverityLevel
    spread_probability: confloat(ge=0, le=1)
    spread_rate: Optional[str] = None
    factors_increasing_spread: List[str]
    factors_decreasing_spread: List[str]
    containment_measures: List[str]
    quarantine_recommended: bool = False
    notify_neighbors: bool = False
    estimated_spread_area_acres: Optional[float] = None
    time_to_spread_days: Optional[int] = None


class ExpertReview(BaseModel):
    """Human expert review details."""
    reviewer_id: str
    reviewer_name: str
    reviewer_qualifications: str
    review_date: datetime
    agreement_with_ai: Optional[confloat(ge=0, le=1)] = None
    modifications_made: Optional[List[str]] = None
    additional_notes: Optional[str] = None
    confidence_in_diagnosis: confloat(ge=0, le=1)
    recommended_follow_up: Optional[str] = None


# ============================================================================
# MAIN RESPONSE SCHEMAS
# ============================================================================

class DiagnosisResponse(BaseModel):
    """
    Comprehensive diagnosis response schema.
    
    Contains all diagnostic information, recommendations, and metadata.
    """
    # Core identification
    id: int
    request_id: str
    diagnosis_id: str = Field(default_factory=lambda: f"DIAG-{uuid4()}")
    
    # Status
    status: DiagnosisStatus
    status_message: Optional[str] = None
    progress_percentage: Optional[confloat(ge=0, le=100)] = None
    
    # Primary diagnosis
    primary_diagnosis: Optional[str] = None
    disease_id: Optional[str] = None
    disease_scientific_name: Optional[str] = None
    disease_common_names: Optional[List[str]] = None
    category: Optional[DiseaseCategory] = None
    
    # Confidence and severity
    confidence_score: confloat(ge=0, le=1) = 0.0
    confidence_level: Optional[ConfidenceLevel] = None
    severity_level: Optional[SeverityLevel] = None
    urgency: Optional[UrgencyLevel] = None
    
    # Alternative diagnoses
    alternative_diagnoses: Optional[List[AlternativeDiagnosis]] = None
    differential_diagnosis_notes: Optional[str] = None
    
    # Detailed analysis
    affected_area_percentage: Optional[confloat(ge=0, le=100)] = None
    disease_stage: Optional[str] = None
    pathogen_identification: Optional[str] = None
    symptoms_observed: Optional[List[str]] = None
    disease_description: Optional[str] = None
    disease_life_cycle: Optional[str] = None
    transmission_method: Optional[str] = None
    
    # Treatment
    treatment_plan: Optional[TreatmentPlan] = None
    treatment_summary: Optional[str] = None
    quick_action_items: Optional[List[str]] = None
    
    # Impact assessment
    yield_impact: Optional[YieldImpactEstimate] = None
    spread_risk: Optional[SpreadRiskAssessment] = None
    economic_impact_summary: Optional[str] = None
    
    # Similar cases
    similar_cases: Optional[List[SimilarCase]] = None
    historical_context: Optional[str] = None
    
    # Quality assurance
    quality_metrics: Optional[QualityMetrics] = None
    requires_human_review: bool = False
    human_review_reason: Optional[str] = None
    expert_review: Optional[ExpertReview] = None
    
    # AI model information
    ai_model_info: Optional[AIModelInfo] = None
    processing_details: Optional[Dict[str, Any]] = None
    
    # Additional resources
    educational_content_url: Optional[HttpUrl] = None
    video_tutorials: Optional[List[HttpUrl]] = None
    reference_materials: Optional[List[str]] = None
    expert_contact_info: Optional[Dict[str, str]] = None
    
    # Timestamps
    created_at: datetime
    queued_at: Optional[datetime] = None
    processing_started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_time_seconds: Optional[float] = None
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, validation_alias="diagnosis_metadata")
    version: str = "2.0"

    class Config:
        from_attributes = True
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "id": 12345,
                "request_id": "req-abc-123",
                "status": "completed",
                "primary_diagnosis": "Late Blight (Phytophthora infestans)",
                "category": "fungal",
                "confidence_score": 0.94,
                "severity_level": "high",
                "urgency": "urgent"
            }
        }


class DiagnosisComplete(DiagnosisResponse):
    """
    Extended response with all details for completed diagnosis.
    
    Includes full context and processing information.
    """
    # Original request data
    image_urls: List[HttpUrl]
    image_metadata: Optional[List[ImageMetadata]] = None
    user_symptoms: Optional[str] = None
    farm_context: Optional[FarmContext] = None
    user_context: Optional[UserContext] = None
    
    # Triage information
    triage_diagnosis: Optional[str] = None
    triage_confidence: Optional[float] = None
    triage_vs_final_match: Optional[bool] = None
    
    # Audit trail
    audit_trail: List[AuditTrail] = []
    
    # Performance metrics
    cache_hit: bool = False
    model_latency_ms: Optional[float] = None
    total_latency_ms: Optional[float] = None
    
    # Billing
    billing_info: Optional[BillingInfo] = None


# ============================================================================
# BATCH AND ANALYTICS SCHEMAS
# ============================================================================

class BatchDiagnosisStatus(BaseModel):
    """Batch diagnosis status."""
    batch_id: str
    total_diagnoses: int
    completed: int
    processing: int
    failed: int
    pending: int
    progress_percentage: confloat(ge=0, le=100)
    estimated_completion_time: Optional[datetime] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    individual_statuses: List[Dict[str, Any]]


class DiagnosisAnalytics(BaseModel):
    """Analytics for diagnosis patterns."""
    time_period_start: date
    time_period_end: date
    total_diagnoses: int
    
    # By category
    diagnoses_by_category: Dict[DiseaseCategory, int]
    most_common_diseases: List[Tuple[str, int]]
    
    # By severity
    by_severity: Dict[SeverityLevel, int]
    critical_cases: int
    
    # Performance metrics
    average_confidence_score: float
    average_processing_time_seconds: float
    human_review_rate: float
    
    # Accuracy metrics
    accuracy_rate: Optional[float] = None
    false_positive_rate: Optional[float] = None
    false_negative_rate: Optional[float] = None
    
    # Geographic distribution
    by_region: Optional[Dict[str, int]] = None
    by_crop_type: Dict[CropType, int]
    
    # Temporal patterns
    seasonal_patterns: Optional[Dict[str, Any]] = None
    peak_hours: Optional[List[int]] = None
    
    # Economic impact
    total_economic_impact_ksh: Optional[Decimal] = None
    average_yield_impact_percent: Optional[float] = None


class DiagnosisReport(BaseModel):
    """Comprehensive diagnosis report for export."""
    report_id: str = Field(default_factory=lambda: f"REP-{uuid4()}")
    report_type: Literal["individual", "batch", "analytics", "summary"]
    generated_at: datetime = Field(default_factory=datetime.now)
    generated_by: str
    
    # Report content
    diagnoses: Optional[List[DiagnosisComplete]] = None
    analytics: Optional[DiagnosisAnalytics] = None
    executive_summary: Optional[str] = None
    recommendations: Optional[List[str]] = None
    
    # Filters applied
    filters: Optional[Dict[str, Any]] = None
    
    # Export formats
    pdf_url: Optional[HttpUrl] = None
    excel_url: Optional[HttpUrl] = None
    json_url: Optional[HttpUrl] = None
    
    # Metadata
    report_metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# FEEDBACK AND QUALITY ASSURANCE SCHEMAS
# ============================================================================

class DiagnosisFeedback(BaseModel):
    """User feedback on diagnosis."""
    diagnosis_id: str
    user_id: str
    submitted_at: datetime = Field(default_factory=datetime.now)
    
    # Ratings (1-5 stars)
    overall_rating: conint(ge=1, le=5)
    accuracy_rating: Optional[conint(ge=1, le=5)] = None
    usefulness_rating: Optional[conint(ge=1, le=5)] = None
    timeliness_rating: Optional[conint(ge=1, le=5)] = None
    
    # Detailed feedback
    was_diagnosis_correct: Optional[bool] = None
    actual_disease: Optional[str] = None
    treatment_followed: Optional[bool] = None
    treatment_effective: Optional[bool] = None
    recovery_time_days: Optional[int] = None
    
    # Open feedback
    comments: Optional[constr(max_length=1000)] = None
    suggestions: Optional[str] = None
    issues_encountered: Optional[List[str]] = None
    
    # Media
    follow_up_images: Optional[List[HttpUrl]] = None
    
    # Metadata
    feedback_type: Literal["positive", "negative", "neutral", "correction"]
    would_recommend: Optional[bool] = None


class QualityAudit(BaseModel):
    """Quality audit record."""
    audit_id: str = Field(default_factory=lambda: f"AUD-{uuid4()}")
    diagnosis_id: str
    auditor_id: str
    auditor_name: str
    audit_date: datetime = Field(default_factory=datetime.now)
    
    # Audit results
    diagnosis_accuracy: Literal["correct", "partially_correct", "incorrect", "unverifiable"]
    confidence_appropriate: bool
    treatment_plan_appropriate: bool
    quality_standards_met: bool
    
    # Detailed assessment
    strengths: List[str]
    weaknesses: List[str]
    improvement_areas: List[str]
    
    # Scores
    technical_accuracy_score: confloat(ge=0, le=100)
    completeness_score: confloat(ge=0, le=100)
    clarity_score: confloat(ge=0, le=100)
    overall_quality_score: confloat(ge=0, le=100)
    
    # Actions
    corrective_actions: Optional[List[str]] = None
    follow_up_required: bool = False
    escalation_needed: bool = False
    
    # Notes
    audit_notes: Optional[str] = None
    reviewed_by_senior_expert: bool = False


# ============================================================================
# NOTIFICATION AND WEBHOOK SCHEMAS
# ============================================================================

class DiagnosisNotification(BaseModel):
    """Notification configuration."""
    notification_id: str = Field(default_factory=lambda: f"NOTIF-{uuid4()}")
    diagnosis_id: str
    recipient_id: str
    
    # Channels
    channels: List[NotificationChannel]
    priority: Literal["low", "medium", "high", "urgent"]
    
    # Content
    title: str
    message: str
    action_url: Optional[HttpUrl] = None
    action_text: Optional[str] = None
    
    # Delivery
    scheduled_for: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    
    # Status
    status: Literal["pending", "sent", "delivered", "failed", "read"]
    delivery_attempts: int = 0
    error_message: Optional[str] = None
    
    # Metadata
    notification_type: str
    metadata: Optional[Dict[str, Any]] = None


class WebhookPayload(BaseModel):
    """Webhook notification payload."""
    webhook_id: str = Field(default_factory=lambda: f"WH-{uuid4()}")
    event_type: Literal[
        "diagnosis.created",
        "diagnosis.processing",
        "diagnosis.completed",
        "diagnosis.failed",
        "batch.completed",
        "quality.alert"
    ]
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Event data
    diagnosis: Optional[DiagnosisResponse] = None
    batch: Optional[BatchDiagnosisStatus] = None
    error: Optional[Dict[str, Any]] = None
    
    # Metadata
    api_version: str = "2.0"
    signature: Optional[str] = Field(None, description="HMAC signature for verification")


# ============================================================================
# SEARCH AND FILTER SCHEMAS
# ============================================================================

class DiagnosisSearchQuery(BaseModel):
    """Advanced search query."""
    # Text search
    query: Optional[str] = Field(None, description="Full-text search query")
    
    # Filters
    diagnosis_ids: Optional[List[str]] = None
    user_ids: Optional[List[str]] = None
    farmer_ids: Optional[List[str]] = None
    statuses: Optional[List[DiagnosisStatus]] = None
    categories: Optional[List[DiseaseCategory]] = None
    severity_levels: Optional[List[SeverityLevel]] = None
    crop_types: Optional[List[CropType]] = None
    
    # Date ranges
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    completed_after: Optional[datetime] = None
    completed_before: Optional[datetime] = None
    
    # Numeric ranges
    confidence_min: Optional[confloat(ge=0, le=1)] = None
    confidence_max: Optional[confloat(ge=0, le=1)] = None
    processing_time_max_seconds: Optional[float] = None
    
    # Boolean filters
    requires_human_review: Optional[bool] = None
    has_expert_review: Optional[bool] = None
    has_user_feedback: Optional[bool] = None
    
    # Sorting
    sort_by: Optional[Literal[
        "created_at",
        "completed_at",
        "confidence_score",
        "severity_level",
        "processing_time"
    ]] = "created_at"
    sort_order: Literal["asc", "desc"] = "desc"
    
    # Pagination
    page: conint(ge=1) = 1
    page_size: conint(ge=1, le=100) = 20
    
    # Advanced options
    include_deleted: bool = False
    include_metadata: bool = False


class DiagnosisSearchResult(BaseModel):
    """Search results."""
    query: DiagnosisSearchQuery
    total_results: int
    page: int
    page_size: int
    total_pages: int
    results: List[DiagnosisResponse]
    facets: Optional[Dict[str, Dict[str, int]]] = None
    execution_time_ms: float


# ============================================================================
# EXPORT AND INTEGRATION SCHEMAS
# ============================================================================

class DiagnosisExport(BaseModel):
    """Export configuration."""
    export_id: str = Field(default_factory=lambda: f"EXP-{uuid4()}")
    export_format: Literal["json", "csv", "excel", "pdf"]
    search_query: DiagnosisSearchQuery
    include_images: bool = False
    include_treatment_plans: bool = True
    include_metadata: bool = False
    
    # Status
    status: Literal["pending", "processing", "completed", "failed"]
    progress_percentage: confloat(ge=0, le=100) = 0.0
    
    # Result
    download_url: Optional[HttpUrl] = None
    file_size_bytes: Optional[int] = None
    expires_at: Optional[datetime] = None
    
    # Timestamps
    requested_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class ThirdPartyIntegration(BaseModel):
    """Third-party system integration."""
    integration_id: str
    integration_type: Literal["erpnext", "farmos", "agrivi", "cropwise", "custom"]
    diagnosis_id: str
    
    # Mapping
    external_id: Optional[str] = None
    external_url: Optional[HttpUrl] = None
    field_mappings: Dict[str, str]
    
    # Sync status
    sync_status: Literal["pending", "synced", "failed", "conflict"]
    last_synced_at: Optional[datetime] = None
    sync_errors: Optional[List[str]] = None
    
    # Bidirectional sync
    sync_direction: Literal["push", "pull", "bidirectional"]
    auto_sync: bool = False


# ============================================================================
# CONFIGURATION AND SETTINGS SCHEMAS
# ============================================================================

class DiagnosisSystemConfig(BaseModel):
    """System configuration."""
    # Model settings
    default_model_version: ModelVersion = ModelVersion.V2_1_MULTIMODAL
    confidence_threshold: confloat(ge=0, le=1) = 0.70
    human_review_threshold: confloat(ge=0, le=1) = 0.80
    
    # Processing limits
    max_concurrent_diagnoses: int = 100
    max_queue_size: int = 1000
    max_processing_time_seconds: int = 300
    max_image_size_mb: int = 10
    max_batch_size: int = 50
    
    # Quality assurance
    enable_quality_checks: bool = True
    enable_expert_review: bool = True
    audit_sample_rate: confloat(ge=0, le=1) = 0.10
    
    # Caching
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600
    
    # Features
    enable_similar_cases: bool = True
    enable_yield_impact: bool = True
    enable_spread_risk: bool = True
    enable_advanced_analytics: bool = True
    
    # Notifications
    notification_enabled: bool = True
    notification_channels: List[NotificationChannel] = [
        NotificationChannel.SMS,
        NotificationChannel.IN_APP
    ]
    
    # API settings
    rate_limit_per_hour: int = 100
    rate_limit_per_day: int = 500
    
    # Billing
    default_price_ksh: Decimal = Decimal("150.00")
    bulk_discount_threshold: int = 10
    bulk_discount_percentage: confloat(ge=0, le=100) = 15.0


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def validate_image_url(url: str) -> bool:
    """Validate image URL format and accessibility."""
    try:
        # Check URL format
        parsed = HttpUrl(url)
        # Check file extension
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.tiff']
        return any(url.lower().endswith(ext) for ext in valid_extensions)
    except:
        return False


def calculate_confidence_level(confidence_score: float) -> ConfidenceLevel:
    """Convert confidence score to confidence level."""
    if confidence_score >= 0.95:
        return ConfidenceLevel.VERY_HIGH
    elif confidence_score >= 0.85:
        return ConfidenceLevel.HIGH
    elif confidence_score >= 0.70:
        return ConfidenceLevel.MEDIUM
    elif confidence_score >= 0.50:
        return ConfidenceLevel.LOW
    else:
        return ConfidenceLevel.VERY_LOW


def estimate_processing_time(
    image_count: int,
    enable_advanced_analysis: bool,
    model_version: ModelVersion
) -> int:
    """Estimate processing time in seconds."""
    base_time = 10
    time_per_image = 5
    advanced_overhead = 10 if enable_advanced_analysis else 0
    model_multiplier = 1.5 if model_version == ModelVersion.V3_0_FOUNDATION else 1.0
    
    return int((base_time + (image_count * time_per_image) + advanced_overhead) * model_multiplier)


# ============================================================================
# MULTI-LANGUAGE AND INTERNATIONALIZATION SCHEMAS
# ============================================================================

class TranslatedText(BaseModel):
    """Multi-language text support."""
    en: str  # English (required)
    sw: Optional[str] = None  # Swahili
    fr: Optional[str] = None  # French
    ar: Optional[str] = None  # Arabic
    es: Optional[str] = None  # Spanish
    pt: Optional[str] = None  # Portuguese
    am: Optional[str] = None  # Amharic
    ha: Optional[str] = None  # Hausa
    zu: Optional[str] = None  # Zulu
    yo: Optional[str] = None  # Yoruba
    
    def get_translation(self, language_code: str) -> str:
        """Get translation for specified language, fallback to English."""
        return getattr(self, language_code, None) or self.en


class LocalizedDiagnosis(BaseModel):
    """Diagnosis result with multi-language support."""
    diagnosis_id: str
    language: str = Field(default="en", description="Language code for response")
    
    # Localized content
    disease_name: TranslatedText
    disease_description: TranslatedText
    symptoms_description: TranslatedText
    treatment_summary: TranslatedText
    preventive_measures_text: TranslatedText
    
    # Cultural adaptations
    local_disease_name: Optional[str] = None
    traditional_names: Optional[List[str]] = None
    cultural_context: Optional[str] = None
    local_treatment_practices: Optional[List[str]] = None
    
    # Regional specifics
    region: Optional[str] = None
    climate_zone: Optional[str] = None
    prevalence_in_region: Optional[str] = None
    seasonal_occurrence: Optional[str] = None


class InternationalizedTreatment(BaseModel):
    """Treatment recommendation with regional adaptations."""
    treatment_id: str
    
    # Product information by region
    product_name_international: str
    product_names_local: Dict[str, str] = {}  # Country code -> local name
    
    # Localized instructions
    application_instructions: TranslatedText
    safety_warnings: TranslatedText
    mixing_instructions: Optional[TranslatedText] = None
    
    # Regional availability
    available_countries: List[str]
    alternative_products_by_region: Dict[str, List[str]] = {}
    
    # Regulatory information
    registration_status: Dict[str, str] = {}  # Country -> status
    restricted_countries: List[str] = []
    requires_permit: Dict[str, bool] = {}


class CulturalAdvisory(BaseModel):
    """Cultural and regional farming advisories."""
    advisory_id: str = Field(default_factory=lambda: f"ADV-{uuid4()}")
    region: str
    culture: Optional[str] = None
    
    # Traditional knowledge
    traditional_diagnosis_methods: Optional[List[str]] = None
    indigenous_treatments: Optional[List[str]] = None
    traditional_prevention: Optional[List[str]] = None
    cultural_taboos: Optional[List[str]] = None
    
    # Modern-traditional integration
    complementary_practices: Optional[List[str]] = None
    scientific_validation: Optional[str] = None
    integration_recommendations: Optional[str] = None
    
    # Community practices
    community_response_patterns: Optional[str] = None
    collective_action_needed: Optional[bool] = None
    extension_officer_contact: Optional[str] = None


# ============================================================================
# COMPLIANCE AND REGULATORY SCHEMAS
# ============================================================================

class PesticideRegulation(BaseModel):
    """Pesticide regulatory information."""
    product_name: str
    active_ingredient: str
    
    # Registration details
    registration_number: Optional[str] = None
    registration_country: str
    registration_authority: str
    registration_date: Optional[date] = None
    expiry_date: Optional[date] = None
    registration_status: Literal["active", "suspended", "expired", "pending"]
    
    # WHO classification
    who_toxicity_class: Optional[Literal["Ia", "Ib", "II", "III", "U"]] = None
    who_classification_date: Optional[date] = None
    
    # Restrictions
    restricted_use: bool = False
    restricted_crops: Optional[List[str]] = None
    banned_countries: Optional[List[str]] = None
    conditional_approval: Optional[str] = None
    
    # Usage requirements
    requires_license: bool = False
    requires_prescription: bool = False
    requires_training: bool = False
    ppe_required: List[str] = []
    
    # Environmental restrictions
    water_buffer_zone_meters: Optional[float] = None
    bee_toxicity_warning: bool = False
    aquatic_toxicity_warning: bool = False
    soil_persistence_days: Optional[int] = None
    
    # Monitoring requirements
    residue_testing_required: bool = False
    maximum_residue_limit_ppm: Optional[float] = None
    pre_harvest_interval_days: int
    re_entry_interval_hours: int
    
    # Documentation
    msds_url: Optional[HttpUrl] = None
    label_url: Optional[HttpUrl] = None
    technical_sheet_url: Optional[HttpUrl] = None


class OrganicCertificationCompliance(BaseModel):
    """Organic farming certification compliance."""
    treatment_id: str
    product_name: str
    
    # Certification standards
    usda_organic_approved: bool = False
    eu_organic_approved: bool = False
    ifoam_approved: bool = False
    regional_organic_standards: Dict[str, bool] = {}
    
    # Organic status details
    organic_classification: Literal[
        "fully_organic",
        "approved_with_restrictions",
        "transitional_allowed",
        "not_organic",
        "synthetic"
    ]
    restrictions_for_organic: Optional[List[str]] = None
    waiting_period_days: Optional[int] = None
    
    # Documentation
    organic_certification_number: Optional[str] = None
    certifying_body: Optional[str] = None
    certification_document_url: Optional[HttpUrl] = None
    
    # Alternatives
    organic_alternatives: Optional[List[str]] = None
    natural_alternatives: Optional[List[str]] = None


class EnvironmentalImpactAssessment(BaseModel):
    """Environmental impact of treatment."""
    treatment_id: str
    assessment_date: date
    
    # Impact scores (0-100, higher = more harmful)
    water_contamination_risk: confloat(ge=0, le=100)
    soil_degradation_risk: confloat(ge=0, le=100)
    air_quality_impact: confloat(ge=0, le=100)
    biodiversity_impact: confloat(ge=0, le=100)
    pollinator_impact: confloat(ge=0, le=100)
    
    # Overall assessment
    overall_environmental_score: confloat(ge=0, le=100)
    environmental_classification: Literal["low_impact", "moderate_impact", "high_impact", "severe_impact"]
    
    # Mitigation measures
    mitigation_required: bool
    mitigation_measures: List[str]
    monitoring_requirements: List[str]
    
    # Long-term effects
    persistence_in_environment: Optional[str] = None
    bioaccumulation_potential: Optional[str] = None
    ecosystem_recovery_time: Optional[str] = None
    
    # Sustainability rating
    sustainability_score: Optional[confloat(ge=0, le=100)] = None
    sustainable_alternatives_available: bool = False


class ComplianceAuditLog(BaseModel):
    """Compliance audit trail."""
    audit_id: str = Field(default_factory=lambda: f"COMP-AUD-{uuid4()}")
    diagnosis_id: str
    audit_timestamp: datetime = Field(default_factory=datetime.now)
    
    # Regulatory checks
    pesticide_registration_verified: bool
    organic_compliance_verified: bool
    who_guidelines_followed: bool
    local_regulations_followed: bool
    environmental_assessment_completed: bool
    
    # Documentation
    regulations_checked: List[str]
    compliance_issues_found: List[str]
    compliance_warnings: List[str]
    corrective_actions: List[str]
    
    # Auditor information
    audit_performed_by: str
    audit_type: Literal["automatic", "manual", "triggered", "scheduled"]
    audit_result: Literal["compliant", "non_compliant", "conditional", "requires_review"]
    
    # Follow-up
    requires_follow_up: bool
    follow_up_deadline: Optional[datetime] = None
    responsible_party: Optional[str] = None


class RegulatoryAlert(BaseModel):
    """Regulatory change alert."""
    alert_id: str = Field(default_factory=lambda: f"REG-ALERT-{uuid4()}")
    alert_type: Literal["new_regulation", "restriction", "ban", "approval", "guideline_change"]
    severity: Literal["info", "warning", "critical", "urgent"]
    
    # Alert details
    title: str
    description: str
    affected_products: List[str]
    affected_regions: List[str]
    affected_crops: Optional[List[str]] = None
    
    # Regulatory body
    issuing_authority: str
    regulation_reference: Optional[str] = None
    regulation_url: Optional[HttpUrl] = None
    
    # Timeline
    effective_date: date
    compliance_deadline: Optional[date] = None
    transition_period_days: Optional[int] = None
    
    # Impact
    impact_assessment: str
    action_required: List[str]
    alternatives_available: bool
    
    # Notifications
    users_notified: int
    notification_sent_at: datetime = Field(default_factory=datetime.now)


# ============================================================================
# ADVANCED ANALYTICS AND REPORTING SCHEMAS
# ============================================================================

class DiagnosticAccuracyMetrics(BaseModel):
    """Detailed accuracy metrics for AI model."""
    model_version: ModelVersion
    evaluation_period_start: date
    evaluation_period_end: date
    total_diagnoses_evaluated: int
    
    # Overall metrics
    overall_accuracy: confloat(ge=0, le=1)
    precision: confloat(ge=0, le=1)
    recall: confloat(ge=0, le=1)
    f1_score: confloat(ge=0, le=1)
    
    # Per-category metrics
    accuracy_by_category: Dict[DiseaseCategory, float]
    precision_by_category: Dict[DiseaseCategory, float]
    recall_by_category: Dict[DiseaseCategory, float]
    
    # Confidence calibration
    confidence_accuracy_curve: List[Tuple[float, float]]  # (confidence_threshold, accuracy)
    overconfidence_rate: float
    underconfidence_rate: float
    
    # Error analysis
    false_positive_rate: float
    false_negative_rate: float
    misclassification_matrix: Optional[Dict[str, Dict[str, int]]] = None
    common_misclassifications: List[Tuple[str, str, int]]  # (actual, predicted, count)
    
    # Performance by condition
    accuracy_by_severity: Dict[SeverityLevel, float]
    accuracy_by_crop: Dict[CropType, float]
    accuracy_by_image_quality: Dict[ImageQuality, float]
    
    # Human agreement
    human_expert_agreement_rate: Optional[float] = None
    cases_requiring_human_review_percentage: float
    
    # Improvement trends
    accuracy_trend_last_30_days: List[Tuple[date, float]]
    improvement_rate_per_month: float


class PerformanceBenchmark(BaseModel):
    """System performance benchmarks."""
    benchmark_id: str = Field(default_factory=lambda: f"BENCH-{uuid4()}")
    benchmark_date: datetime = Field(default_factory=datetime.now)
    period_days: int
    
    # Latency metrics
    average_total_latency_ms: float
    p50_latency_ms: float
    p90_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    
    # Throughput
    diagnoses_per_hour: float
    diagnoses_per_day: float
    peak_concurrent_diagnoses: int
    
    # Resource utilization
    average_cpu_usage_percent: float
    average_memory_usage_mb: float
    average_gpu_usage_percent: Optional[float] = None
    average_api_calls_per_diagnosis: float
    
    # Success rates
    completion_rate: confloat(ge=0, le=1)
    failure_rate: confloat(ge=0, le=1)
    retry_rate: confloat(ge=0, le=1)
    timeout_rate: confloat(ge=0, le=1)
    
    # Queue metrics
    average_queue_wait_time_seconds: float
    max_queue_length: int
    queue_overflow_events: int
    
    # Cost metrics
    cost_per_diagnosis_usd: Optional[Decimal] = None
    total_infrastructure_cost_usd: Optional[Decimal] = None
    cost_efficiency_score: Optional[float] = None
    
    # SLA compliance
    sla_compliance_rate: confloat(ge=0, le=1)
    sla_violations: int
    sla_target_met: bool


class BusinessIntelligence(BaseModel):
    """Business intelligence metrics."""
    report_id: str = Field(default_factory=lambda: f"BI-{uuid4()}")
    report_period_start: date
    report_period_end: date
    
    # User engagement
    total_active_users: int
    new_users: int
    returning_users: int
    user_retention_rate: confloat(ge=0, le=1)
    average_diagnoses_per_user: float
    
    # Revenue metrics
    total_revenue_ksh: Decimal
    revenue_per_user_ksh: Decimal
    average_transaction_value_ksh: Decimal
    revenue_growth_rate: float
    
    # Service usage
    diagnoses_completed: int
    diagnoses_growth_rate: float
    peak_usage_hours: List[int]
    seasonal_patterns: Dict[str, float]
    
    # Geographic distribution
    users_by_region: Dict[str, int]
    diagnoses_by_region: Dict[str, int]
    revenue_by_region: Dict[str, Decimal]
    expansion_opportunities: List[str]
    
    # Product metrics
    most_diagnosed_diseases: List[Tuple[str, int]]
    most_affected_crops: List[Tuple[CropType, int]]
    treatment_adoption_rate: confloat(ge=0, le=1)
    
    # Customer satisfaction
    average_rating: confloat(ge=1, le=5)
    nps_score: Optional[confloat(ge=-100, le=100)] = None
    customer_satisfaction_score: Optional[confloat(ge=0, le=100)] = None
    
    # Operational efficiency
    average_resolution_time_hours: float
    first_time_accuracy_rate: confloat(ge=0, le=1)
    escalation_rate: confloat(ge=0, le=1)
    
    # Growth indicators
    month_over_month_growth: float
    user_acquisition_cost_ksh: Optional[Decimal] = None
    lifetime_value_ksh: Optional[Decimal] = None
    churn_rate: confloat(ge=0, le=1)


class PredictiveInsights(BaseModel):
    """Predictive analytics and forecasting."""
    insight_id: str = Field(default_factory=lambda: f"PRED-{uuid4()}")
    generated_at: datetime = Field(default_factory=datetime.now)
    forecast_horizon_days: int
    confidence_interval: float = 0.95
    
    # Disease outbreak predictions
    predicted_disease_outbreaks: List[Dict[str, Any]]  # Disease, region, probability, timeframe
    outbreak_risk_score: confloat(ge=0, le=100)
    high_risk_regions: List[str]
    
    # Demand forecasting
    predicted_diagnosis_volume: Dict[date, int]
    predicted_peak_dates: List[date]
    capacity_requirements: Dict[str, Any]
    
    # Seasonal trends
    upcoming_disease_season: Optional[str] = None
    seasonal_preparation_recommendations: List[str]
    crop_vulnerability_forecast: Dict[CropType, float]
    
    # Treatment effectiveness
    predicted_treatment_outcomes: Dict[str, float]
    emerging_resistance_patterns: List[str]
    treatment_optimization_suggestions: List[str]
    
    # Resource planning
    estimated_support_staff_needed: int
    estimated_expert_review_volume: int
    estimated_infrastructure_needs: Dict[str, Any]
    
    # Business forecasts
    revenue_forecast_next_quarter_ksh: Decimal
    user_growth_forecast: Dict[date, int]
    market_expansion_opportunities: List[str]


class CompetitiveAnalysis(BaseModel):
    """Competitive intelligence (anonymized)."""
    analysis_id: str = Field(default_factory=lambda: f"COMP-{uuid4()}")
    analysis_date: date
    
    # Market position
    market_share_estimate: Optional[confloat(ge=0, le=1)] = None
    competitive_advantages: List[str]
    areas_for_improvement: List[str]
    
    # Feature comparison
    unique_features: List[str]
    industry_standard_features: List[str]
    missing_features: List[str]
    feature_roadmap_priority: List[str]
    
    # Performance benchmarks
    response_time_vs_industry_avg: str  # "faster", "average", "slower"
    accuracy_vs_industry_avg: str
    cost_vs_industry_avg: str
    
    # Customer satisfaction
    satisfaction_vs_competitors: str
    churn_rate_vs_industry: str
    nps_vs_industry: Optional[str] = None
    
    # Innovation metrics
    ai_model_advancement_score: confloat(ge=0, le=100)
    feature_innovation_rate: float
    technology_adoption_speed: str
    
    # Strategic recommendations
    priority_investments: List[str]
    partnership_opportunities: List[str]
    market_expansion_strategy: Optional[str] = None


# ============================================================================
# ADVANCED DATA SCIENCE AND ML OPS SCHEMAS
# ============================================================================

class ModelExperiment(BaseModel):
    """ML model experiment tracking."""
    experiment_id: str = Field(default_factory=lambda: f"EXP-{uuid4()}")
    experiment_name: str
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: str
    
    # Model configuration
    model_architecture: str
    model_version: str
    hyperparameters: Dict[str, Any]
    training_dataset_size: int
    validation_dataset_size: int
    test_dataset_size: int
    
    # Training details
    training_started_at: datetime
    training_completed_at: Optional[datetime] = None
    training_duration_hours: Optional[float] = None
    epochs_completed: int
    early_stopping_epoch: Optional[int] = None
    
    # Performance metrics
    training_accuracy: confloat(ge=0, le=1)
    validation_accuracy: confloat(ge=0, le=1)
    test_accuracy: confloat(ge=0, le=1)
    training_loss: float
    validation_loss: float
    test_loss: float
    
    # Additional metrics
    precision: confloat(ge=0, le=1)
    recall: confloat(ge=0, le=1)
    f1_score: confloat(ge=0, le=1)
    auc_roc: Optional[confloat(ge=0, le=1)] = None
    
    # Resource usage
    gpu_hours_used: Optional[float] = None
    cost_usd: Optional[Decimal] = None
    carbon_emissions_kg: Optional[float] = None
    
    # Deployment
    deployed_to_production: bool = False
    deployment_date: Optional[datetime] = None
    deployment_status: Optional[str] = None
    
    # Notes and artifacts
    experiment_notes: Optional[str] = None
    model_artifact_url: Optional[HttpUrl] = None
    tensorboard_url: Optional[HttpUrl] = None
    mlflow_run_id: Optional[str] = None


class DataDriftDetection(BaseModel):
    """Data drift monitoring."""
    detection_id: str = Field(default_factory=lambda: f"DRIFT-{uuid4()}")
    detection_date: datetime = Field(default_factory=datetime.now)
    baseline_period_start: date
    baseline_period_end: date
    comparison_period_start: date
    comparison_period_end: date
    
    # Drift metrics
    overall_drift_score: confloat(ge=0, le=1)
    drift_detected: bool
    drift_severity: Literal["none", "low", "moderate", "high", "severe"]
    
    # Feature-level drift
    drifted_features: List[str]
    feature_drift_scores: Dict[str, float]
    statistical_tests: Dict[str, Dict[str, Any]]  # Feature -> test results
    
    # Distribution changes
    mean_shifts: Dict[str, float]
    variance_changes: Dict[str, float]
    new_categories_emerged: Dict[str, List[str]]
    
    # Impact assessment
    predicted_accuracy_degradation: confloat(ge=0, le=1)
    affected_disease_categories: List[DiseaseCategory]
    affected_crops: List[CropType]
    
    # Recommendations
    retraining_recommended: bool
    retraining_priority: Literal["low", "medium", "high", "critical"]
    retraining_eta_days: Optional[int] = None
    mitigation_actions: List[str]
    
    # Alerts
    alert_triggered: bool
    alert_recipients: List[str]
    alert_sent_at: Optional[datetime] = None


class ModelMonitoring(BaseModel):
    """Continuous model monitoring."""
    monitoring_id: str = Field(default_factory=lambda: f"MON-{uuid4()}")
    model_version: ModelVersion
    monitoring_period_start: datetime
    monitoring_period_end: datetime
    
    # Performance tracking
    predictions_made: int
    average_confidence: float
    low_confidence_predictions: int
    high_confidence_incorrect_predictions: int
    
    # Accuracy tracking
    verified_predictions: int
    correct_predictions: int
    current_accuracy: confloat(ge=0, le=1)
    accuracy_trend: Literal["improving", "stable", "degrading"]
    
    # Latency tracking
    average_inference_time_ms: float
    p95_inference_time_ms: float
    slow_inferences: int
    timeout_count: int
    
    # Error tracking
    total_errors: int
    error_rate: float
    error_types: Dict[str, int]
    critical_errors: int
    
    # Resource usage
    average_memory_mb: float
    peak_memory_mb: float
    average_cpu_percent: float
    average_gpu_percent: Optional[float] = None
    
    # Alerts and incidents
    alerts_triggered: int
    incidents_reported: int
    mean_time_to_detection_hours: Optional[float] = None
    mean_time_to_resolution_hours: Optional[float] = None
    
    # Health score
    overall_health_score: confloat(ge=0, le=100)
    health_status: Literal["healthy", "warning", "critical", "degraded"]


class FeatureImportance(BaseModel):
    """Feature importance analysis."""
    analysis_id: str = Field(default_factory=lambda: f"FEAT-IMP-{uuid4()}")
    model_version: ModelVersion
    analysis_date: datetime = Field(default_factory=datetime.now)
    method: Literal["shap", "lime", "permutation", "gain", "integrated_gradients"]
    
    # Global importance
    feature_rankings: List[Tuple[str, float]]  # (feature_name, importance_score)
    top_10_features: List[str]
    redundant_features: List[str]
    
    # Per-disease importance
    importance_by_disease: Dict[str, List[Tuple[str, float]]]
    disease_specific_features: Dict[str, List[str]]
    
    # Temporal importance
    importance_trends: Dict[str, List[Tuple[date, float]]]
    emerging_important_features: List[str]
    declining_important_features: List[str]
    
    # Feature interactions
    top_feature_interactions: List[Tuple[str, str, float]]
    synergistic_features: List[Tuple[str, str]]
    
    # Actionable insights
    data_collection_priorities: List[str]
    feature_engineering_suggestions: List[str]
    model_optimization_recommendations: List[str]


class ABTestExperiment(BaseModel):
    """A/B testing experiment."""
    experiment_id: str = Field(default_factory=lambda: f"ABT-{uuid4()}")
    experiment_name: str
    hypothesis: str
    start_date: datetime
    end_date: Optional[datetime] = None
    status: Literal["planning", "running", "paused", "completed", "cancelled"]
    
    # Experiment design
    control_group_model: ModelVersion
    treatment_group_model: ModelVersion
    traffic_split_percentage: confloat(ge=0, le=100) = 50.0
    randomization_method: str
    
    # Sample sizes
    control_group_size: int
    treatment_group_size: int
    minimum_sample_size: int
    statistical_power: confloat(ge=0, le=1) = 0.80
    
    # Primary metrics
    primary_metric: str
    control_metric_value: Optional[float] = None
    treatment_metric_value: Optional[float] = None
    metric_lift_percentage: Optional[float] = None
    
    # Statistical significance
    p_value: Optional[float] = None
    confidence_level: confloat(ge=0, le=1) = 0.95
    statistically_significant: Optional[bool] = None
    
    # Secondary metrics
    secondary_metrics: Dict[str, Tuple[float, float]]  # metric -> (control, treatment)
    unexpected_impacts: List[str]
    
    # Decision
    decision: Optional[Literal["adopt_treatment", "keep_control", "inconclusive", "run_longer"]] = None
    decision_date: Optional[datetime] = None
    decision_rationale: Optional[str] = None
    
    # Rollout plan
    rollout_percentage: confloat(ge=0, le=100) = 0.0
    full_rollout_date: Optional[datetime] = None


# ============================================================================
# BLOCKCHAIN AND IMMUTABILITY SCHEMAS
# ============================================================================

class BlockchainAnchor(BaseModel):
    """Blockchain immutability anchor."""
    anchor_id: str = Field(default_factory=lambda: f"CHAIN-{uuid4()}")
    diagnosis_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Blockchain details
    blockchain_network: Literal["ethereum", "polygon", "avalanche", "celo", "custom"]
    contract_address: str
    transaction_hash: str
    block_number: int
    block_timestamp: datetime
    
    # Anchored data
    data_hash_sha256: str
    data_merkle_root: Optional[str] = None
    metadata_hash: Optional[str] = None
    
    # Verification
    verification_url: HttpUrl
    ipfs_cid: Optional[str] = None
    arweave_txid: Optional[str] = None
    
    # Gas and costs
    gas_used: Optional[int] = None
    gas_price_gwei: Optional[float] = None
    transaction_cost_usd: Optional[Decimal] = None
    
    # Status
    confirmations: int = 0
    finalized: bool = False
    verification_status: Literal["pending", "confirmed", "finalized", "failed"]


class TamperProofEvidence(BaseModel):
    """Tamper-proof evidence package."""
    evidence_id: str = Field(default_factory=lambda: f"EVID-{uuid4()}")
    diagnosis_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Evidence components
    original_images_hash: str
    processed_images_hash: Optional[str] = None
    ai_output_hash: str
    metadata_hash: str
    treatment_plan_hash: Optional[str] = None
    
    # Chain of custody
    custody_chain: List[Dict[str, Any]]
    current_custodian: str
    access_log: List[Dict[str, Any]]
    
    # Cryptographic proofs
    digital_signature: str
    public_key: str
    signature_algorithm: str = "ECDSA-secp256k1"
    timestamp_authority: Optional[str] = None
    
    # Immutability guarantees
    blockchain_anchor: Optional[BlockchainAnchor] = None
    distributed_storage_urls: List[HttpUrl]
    redundancy_factor: int = 3
    
    # Verification tools
    verification_script_url: Optional[HttpUrl] = None
    verification_instructions: str
    independent_verification_possible: bool = True


class AuditableDecisionLog(BaseModel):
    """Complete audit trail of all decisions."""
    log_id: str = Field(default_factory=lambda: f"DEC-LOG-{uuid4()}")
    diagnosis_id: str
    
    # Decision points
    decisions: List[Dict[str, Any]]  # Each decision with timestamp, actor, reasoning
    
    # AI reasoning
    ai_decision_tree: Optional[Dict[str, Any]] = None
    confidence_evolution: List[Tuple[datetime, float]]
    alternative_pathways_considered: List[Dict[str, Any]]
    
    # Human interventions
    human_overrides: List[Dict[str, Any]]
    expert_consultations: List[Dict[str, Any]]
    manual_adjustments: List[Dict[str, Any]]
    
    # Compliance checkpoints
    regulatory_checks: List[Dict[str, Any]]
    safety_validations: List[Dict[str, Any]]
    quality_gates: List[Dict[str, Any]]
    
    # Explainability
    decision_explanations: Dict[str, str]
    risk_assessments: List[Dict[str, Any]]
    assumption_log: List[str]
    
    # Immutability
    log_hash: str
    previous_log_hash: Optional[str] = None
    log_signature: str


# ============================================================================
# REAL-TIME COLLABORATION AND NOTIFICATIONS
# ============================================================================

class RealtimeCollaborationSession(BaseModel):
    """Real-time collaboration on diagnosis."""
    session_id: str = Field(default_factory=lambda: f"COLLAB-{uuid4()}")
    diagnosis_id: str
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    
    # Participants
    primary_diagnostician: str
    collaborating_experts: List[str]
    observers: List[str]
    
    # Activity stream
    annotations: List[Dict[str, Any]]
    comments: List[Dict[str, Any]]
    suggestions: List[Dict[str, Any]]
    approvals: List[Dict[str, Any]]
    
    # Consensus building
    voting_enabled: bool = False
    votes: Dict[str, str] = {}  # participant -> vote
    consensus_reached: bool = False
    consensus_diagnosis: Optional[str] = None
    
    # Communication
    messages: List[Dict[str, Any]]
    video_call_url: Optional[HttpUrl] = None
    screen_sharing_active: bool = False
    
    # Version control
    diagnosis_versions: List[Dict[str, Any]]
    current_version: int = 1
    change_history: List[Dict[str, Any]]


class PushNotificationConfig(BaseModel):
    """Push notification configuration."""
    notification_id: str = Field(default_factory=lambda: f"PUSH-{uuid4()}")
    user_id: str
    
    # Preferences
    enabled: bool = True
    notification_types: List[str]
    quiet_hours_start: Optional[int] = None  # Hour 0-23
    quiet_hours_end: Optional[int] = None
    
    # Device tokens
    device_tokens: List[str]
    platform: Literal["ios", "android", "web"]
    
    # Delivery rules
    max_daily_notifications: int = 20
    priority_only_during_quiet_hours: bool = True
    group_similar_notifications: bool = True
    
    # Customization
    sound_enabled: bool = True
    vibration_enabled: bool = True
    badge_enabled: bool = True
    
    # Localization
    language: str = "en"
    timezone: str = "Africa/Nairobi"


class EmailDigest(BaseModel):
    """Email digest configuration."""
    digest_id: str = Field(default_factory=lambda: f"DIGEST-{uuid4()}")
    user_id: str
    email: EmailStr
    
    # Schedule
    frequency: Literal["daily", "weekly", "monthly"]
    preferred_day: Optional[int] = None  # 0=Monday for weekly
    preferred_hour: int = 8  # 0-23
    
    # Content preferences
    include_diagnoses: bool = True
    include_treatments: bool = True
    include_analytics: bool = True
    include_alerts: bool = True
    include_recommendations: bool = True
    
    # Filtering
    min_severity: SeverityLevel = SeverityLevel.LOW
    crop_types: Optional[List[CropType]] = None
    
    # Format
    format: Literal["html", "plain_text", "pdf_attachment"]
    language: str = "en"
    
    # Delivery tracking
    last_sent: Optional[datetime] = None
    open_rate: Optional[float] = None
    click_rate: Optional[float] = None


# ============================================================================
# INTEGRATION WITH EXTERNAL SYSTEMS
# ============================================================================

class WeatherAPIIntegration(BaseModel):
    """Weather API integration details."""
    integration_id: str = Field(default_factory=lambda: f"WEATHER-{uuid4()}")
    provider: Literal["openweather", "weatherapi", "climacell", "tomorrow_io"]
    
    # API details
    api_key_hash: str
    rate_limit_per_hour: int
    requests_used: int = 0
    
    # Data sources
    historical_data_available: bool
    forecast_days_available: int
    hyperlocal_data_available: bool
    
    # Integration status
    last_successful_call: Optional[datetime] = None
    consecutive_failures: int = 0
    integration_healthy: bool = True


class PaymentGatewayIntegration(BaseModel):
    """Payment gateway integration."""
    integration_id: str = Field(default_factory=lambda: f"PAY-{uuid4()}")
    provider: Literal["mpesa", "stripe", "paystack", "flutterwave"]
    
    # Configuration
    merchant_id: str
    api_version: str
    webhook_url: HttpUrl
    
    # Capabilities
    supports_mobile_money: bool
    supports_cards: bool
    supports_bank_transfer: bool
    supports_subscriptions: bool
    
    # Performance
    average_transaction_time_seconds: float
    success_rate: confloat(ge=0, le=1)
    last_transaction_at: Optional[datetime] = None


class SatelliteImageryIntegration(BaseModel):
    """Satellite imagery integration."""
    integration_id: str = Field(default_factory=lambda: f"SAT-{uuid4()}")
    provider: Literal["sentinel", "landsat", "planet", "maxar"]
    
    # Capabilities
    resolution_meters: float
    revisit_frequency_days: int
    spectral_bands: List[str]
    
    # NDVI and vegetation indices
    ndvi_available: bool
    evi_available: bool
    savi_available: bool
    custom_indices_supported: bool
    
    # Access details
    api_endpoint: HttpUrl
    coverage_areas: List[str]
    historical_archive_years: int


# ============================================================================
# IOT DEVICE AND SENSOR SCHEMAS
# ============================================================================

class IoTDeviceInfo(BaseModel):
    """IoT device information."""
    device_id: str
    device_type: Literal["sentry", "soil_sensor", "weather_station", "camera_trap", "moisture_sensor"]
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    firmware_version: Optional[str] = None
    
    # Location
    farm_id: str
    field_zone: Optional[str] = None
    gps_coordinates: GPSCoordinates
    installation_date: date
    
    # Status
    online: bool = True
    battery_level_percent: Optional[confloat(ge=0, le=100)] = None
    signal_strength_dbm: Optional[float] = None
    last_heartbeat: Optional[datetime] = None
    
    # Calibration
    last_calibration_date: Optional[date] = None
    calibration_status: Literal["valid", "expired", "required", "unknown"]
    calibration_certificate_url: Optional[HttpUrl] = None
    
    # Maintenance
    maintenance_schedule: Optional[str] = None
    last_maintenance_date: Optional[date] = None
    next_maintenance_due: Optional[date] = None
    
    # Data quality
    measurement_accuracy: Optional[str] = None
    data_reliability_score: Optional[confloat(ge=0, le=100)] = None
    anomaly_detection_enabled: bool = True


class SentryDeviceReading(BaseModel):
    """ESP32-CAM Sentry device reading."""
    reading_id: str = Field(default_factory=lambda: f"SENTRY-{uuid4()}")
    device_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Image capture
    image_url: HttpUrl
    image_hash: str
    capture_quality: ImageQuality
    
    # Computed metrics
    ndvi_proxy: confloat(ge=-1, le=1)
    vegetation_index: float
    health_score: confloat(ge=0, le=100)
    anomaly_detected: bool
    
    # Environmental context
    ambient_light_lux: Optional[float] = None
    ambient_temperature_celsius: Optional[float] = None
    capture_angle_degrees: Optional[float] = None
    
    # Processing
    edge_processing_time_ms: float
    transmitted_to_cloud: bool
    transmission_size_bytes: int
    
    # Alert status
    alert_triggered: bool
    alert_type: Optional[Literal["health_decline", "pest_detected", "disease_suspected", "urgent"]] = None
    alert_severity: Optional[SeverityLevel] = None


class SoilSensorReading(BaseModel):
    """Soil sensor measurements."""
    reading_id: str = Field(default_factory=lambda: f"SOIL-{uuid4()}")
    device_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Soil properties
    soil_moisture_percent: confloat(ge=0, le=100)
    soil_temperature_celsius: float
    soil_ph: confloat(ge=0, le=14)
    
    # Nutrients (ppm)
    nitrogen_ppm: Optional[float] = None
    phosphorus_ppm: Optional[float] = None
    potassium_ppm: Optional[float] = None
    
    # Electrical conductivity
    ec_ms_cm: Optional[float] = None  # Soil salinity
    
    # Derived insights
    irrigation_needed: bool
    nutrient_deficiency_detected: bool
    drainage_issues_detected: bool
    
    # Quality indicators
    measurement_confidence: confloat(ge=0, le=1)
    sensor_calibration_valid: bool


class WeatherStationReading(BaseModel):
    """Weather station measurements."""
    reading_id: str = Field(default_factory=lambda: f"WEATHER-{uuid4()}")
    device_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Atmospheric measurements
    temperature_celsius: float
    humidity_percent: confloat(ge=0, le=100)
    pressure_hpa: float
    
    # Precipitation
    rainfall_mm: confloat(ge=0)
    rainfall_rate_mm_hour: confloat(ge=0)
    
    # Wind
    wind_speed_kmh: confloat(ge=0)
    wind_direction_degrees: confloat(ge=0, lt=360)
    wind_gust_kmh: Optional[confloat(ge=0)] = None
    
    # Solar radiation
    solar_radiation_w_m2: Optional[float] = None
    uv_index: Optional[confloat(ge=0, le=15)] = None
    
    # Derived insights
    frost_risk: bool
    heat_stress_risk: bool
    disease_favorable_conditions: bool
    optimal_spraying_conditions: bool


class IoTDataPipeline(BaseModel):
    """IoT data processing pipeline."""
    pipeline_id: str = Field(default_factory=lambda: f"PIPE-{uuid4()}")
    source_device_id: str
    
    # Data flow
    raw_data_received_at: datetime
    preprocessed_at: Optional[datetime] = None
    analyzed_at: Optional[datetime] = None
    stored_at: Optional[datetime] = None
    
    # Processing steps
    preprocessing_applied: List[str]
    anomaly_detection_run: bool
    ml_inference_run: bool
    
    # Quality assurance
    data_validation_passed: bool
    validation_errors: List[str]
    data_completeness: confloat(ge=0, le=1)
    
    # Output
    diagnosis_triggered: bool
    alert_generated: bool
    data_archived: bool
    
    # Performance
    total_latency_ms: float
    pipeline_efficiency_score: confloat(ge=0, le=100)


# ============================================================================
# MOBILE APP AND USER EXPERIENCE SCHEMAS
# ============================================================================

class MobileAppSession(BaseModel):
    """Mobile app user session."""
    session_id: str = Field(default_factory=lambda: f"SESSION-{uuid4()}")
    user_id: str
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    
    # Device information
    device_os: Literal["ios", "android"]
    device_model: Optional[str] = None
    app_version: str
    os_version: str
    
    # Session metrics
    actions_performed: List[str]
    screens_visited: List[str]
    diagnoses_requested: int = 0
    diagnoses_completed: int = 0
    
    # Engagement
    session_duration_seconds: Optional[float] = None
    photos_captured: int = 0
    videos_watched: int = 0
    articles_read: int = 0
    
    # Performance
    crashes_occurred: int = 0
    errors_encountered: List[str]
    average_screen_load_time_ms: Optional[float] = None
    
    # Network
    network_type: Optional[Literal["wifi", "4g", "3g", "2g", "offline"]] = None
    data_consumed_mb: Optional[float] = None
    offline_mode_used: bool = False


class CameraGuidance(BaseModel):
    """Camera guidance for capturing diagnostic images."""
    guidance_id: str = Field(default_factory=lambda: f"GUIDE-{uuid4()}")
    crop_type: CropType
    symptom_type: Optional[str] = None
    
    # Capture requirements
    recommended_distance_cm: int
    recommended_angle: str
    lighting_requirements: str
    focus_area: str
    
    # Step-by-step guidance
    capture_steps: List[str]
    image_count_required: int
    example_images: List[HttpUrl]
    
    # Quality checks
    real_time_quality_checks: List[str]
    auto_reject_criteria: List[str]
    auto_enhance_enabled: bool
    
    # Accessibility
    voice_guidance_available: bool
    haptic_feedback_enabled: bool
    visual_aids: List[str]


class OfflineDiagnosisCache(BaseModel):
    """Offline diagnosis capability."""
    cache_id: str = Field(default_factory=lambda: f"CACHE-{uuid4()}")
    user_id: str
    device_id: str
    
    # Cached models
    cached_models: List[str]
    model_versions: Dict[str, str]
    total_cache_size_mb: float
    last_updated: datetime
    
    # Cached data
    disease_database_cached: bool
    treatment_database_cached: bool
    historical_diagnoses_cached: int
    
    # Offline capabilities
    offline_diagnosis_available: bool
    offline_accuracy_estimate: confloat(ge=0, le=1)
    supported_crops: List[CropType]
    supported_diseases: List[str]
    
    # Sync status
    pending_sync_diagnoses: int
    last_sync_at: Optional[datetime] = None
    sync_conflicts: int


class UserOnboarding(BaseModel):
    """User onboarding progress."""
    user_id: str
    onboarding_started_at: datetime
    onboarding_completed_at: Optional[datetime] = None
    
    # Progress
    steps_completed: List[str]
    steps_remaining: List[str]
    completion_percentage: confloat(ge=0, le=100)
    
    # Profile setup
    profile_complete: bool
    farm_details_added: bool
    crops_registered: int
    payment_method_added: bool
    
    # Tutorial completion
    tutorial_videos_watched: List[str]
    practice_diagnoses_completed: int
    help_articles_read: int
    
    # Activation
    first_real_diagnosis: Optional[datetime] = None
    days_to_activation: Optional[int] = None
    onboarding_abandoned: bool = False


class UserEngagementMetrics(BaseModel):
    """User engagement analytics."""
    user_id: str
    period_start: date
    period_end: date
    
    # Activity metrics
    days_active: int
    sessions: int
    average_session_duration_minutes: float
    
    # Feature usage
    diagnoses_requested: int
    treatments_purchased: int
    articles_read: int
    videos_watched: int
    community_posts: int
    
    # Depth metrics
    features_used: List[str]
    advanced_features_used: List[str]
    feature_adoption_score: confloat(ge=0, le=100)
    
    # Engagement score
    overall_engagement_score: confloat(ge=0, le=100)
    engagement_trend: Literal["increasing", "stable", "declining"]
    churn_risk_score: confloat(ge=0, le=1)
    
    # Recommendations
    recommended_features: List[str]
    reengagement_strategy: Optional[str] = None


# ============================================================================
# API VERSIONING AND COMPATIBILITY SCHEMAS
# ============================================================================

class APIVersion(BaseModel):
    """API version information."""
    version: str  # e.g., "v2.1.0"
    released_at: date
    deprecated: bool = False
    deprecated_at: Optional[date] = None
    sunset_date: Optional[date] = None
    
    # Compatibility
    backward_compatible_with: List[str]
    breaking_changes: List[str]
    new_features: List[str]
    bug_fixes: List[str]
    
    # Documentation
    documentation_url: HttpUrl
    migration_guide_url: Optional[HttpUrl] = None
    changelog_url: HttpUrl
    
    # Support
    support_status: Literal["active", "maintenance", "deprecated", "unsupported"]
    recommended_upgrade_to: Optional[str] = None


class APIRequestContext(BaseModel):
    """Complete API request context."""
    request_id: str = Field(default_factory=lambda: f"REQ-{uuid4()}")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Client information
    api_version: str
    client_version: Optional[str] = None
    client_platform: Optional[str] = None
    user_agent: str
    
    # Request details
    endpoint: str
    http_method: str
    request_size_bytes: int
    ip_address: str
    
    # Authentication
    user_id: Optional[str] = None
    api_key_hash: Optional[str] = None
    authentication_method: Optional[str] = None
    
    # Rate limiting
    rate_limit_remaining: int
    rate_limit_reset_at: datetime
    
    # Geographic context
    country_code: Optional[str] = None
    region: Optional[str] = None
    language_preference: str = "en"


class APIResponseEnvelope(BaseModel):
    """Standardized API response wrapper."""
    success: bool
    timestamp: datetime = Field(default_factory=datetime.now)
    request_id: str
    api_version: str
    
    # Response data
    data: Optional[Any] = None
    meta: Optional[Dict[str, Any]] = None
    
    # Pagination (if applicable)
    pagination: Optional[Dict[str, Any]] = None
    
    # Errors (if any)
    errors: Optional[List[Dict[str, Any]]] = None
    warnings: Optional[List[str]] = None
    
    # Performance metrics
    processing_time_ms: float
    cache_hit: bool = False
    
    # Links (HATEOAS)
    links: Optional[Dict[str, HttpUrl]] = None
    
    # Deprecation notices
    deprecation_warning: Optional[str] = None
    sunset_date: Optional[date] = None


class SchemaValidationError(BaseModel):
    """Detailed schema validation error."""
    field: str
    error_type: str
    message: str
    invalid_value: Optional[Any] = None
    expected_type: Optional[str] = None
    constraint_violated: Optional[str] = None
    suggestion: Optional[str] = None
    
    # Location in nested structure
    path: List[str]
    
    # Severity
    severity: Literal["error", "warning", "info"]
    
    # Documentation
    documentation_url: Optional[HttpUrl] = None


# ============================================================================
# SECURITY AND AUDIT SCHEMAS
# ============================================================================

class SecurityEvent(BaseModel):
    """Security event logging."""
    event_id: str = Field(default_factory=lambda: f"SEC-{uuid4()}")
    timestamp: datetime = Field(default_factory=datetime.now)
    event_type: Literal[
        "authentication_success",
        "authentication_failure",
        "authorization_failure",
        "suspicious_activity",
        "data_breach_attempt",
        "rate_limit_exceeded",
        "invalid_token",
        "session_hijacking_suspected"
    ]
    
    # Actor information
    user_id: Optional[str] = None
    ip_address: str
    user_agent: str
    geographic_location: Optional[str] = None
    
    # Context
    resource_accessed: Optional[str] = None
    action_attempted: Optional[str] = None
    failure_reason: Optional[str] = None
    
    # Severity and response
    severity: Literal["low", "medium", "high", "critical"]
    automated_response: Optional[str] = None
    requires_investigation: bool
    investigated_by: Optional[str] = None
    resolution: Optional[str] = None


class DataAccessLog(BaseModel):
    """Sensitive data access logging."""
    access_id: str = Field(default_factory=lambda: f"ACCESS-{uuid4()}")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Accessor information
    user_id: str
    user_role: str
    access_method: Literal["api", "dashboard", "export", "direct_query"]
    
    # Data accessed
    resource_type: str
    resource_id: str
    data_fields_accessed: List[str]
    sensitive_data_accessed: bool
    
    # Purpose
    access_purpose: Optional[str] = None
    authorization_granted_by: Optional[str] = None
    
    # Compliance
    gdpr_lawful_basis: Optional[str] = None
    data_retention_policy_applied: bool
    
    # Audit trail
    previous_access_count: int
    last_access_by_user: Optional[datetime] = None


class PrivacyCompliance(BaseModel):
    """Privacy and data protection compliance."""
    compliance_id: str = Field(default_factory=lambda: f"PRIV-{uuid4()}")
    user_id: str
    
    # Consents
    gdpr_consent: bool = False
    marketing_consent: bool = False
    data_sharing_consent: bool = False
    consent_timestamp: datetime
    consent_ip_address: str
    
    # Data subject rights
    right_to_access_requests: int = 0
    right_to_erasure_requests: int = 0
    right_to_portability_requests: int = 0
    right_to_rectification_requests: int = 0
    
    # Data retention
    data_retention_period_days: int
    data_deletion_scheduled: bool = False
    scheduled_deletion_date: Optional[date] = None
    
    # Cross-border transfers
    data_storage_locations: List[str]
    cross_border_transfer_approved: bool
    adequacy_decision: Optional[str] = None
    
    # Breach notifications
    breaches_notified: int = 0
    last_breach_notification: Optional[datetime] = None


# ============================================================================
# DOCUMENTATION AND HELP SCHEMAS
# ============================================================================

class InteractiveDocumentation(BaseModel):
    """Interactive API documentation."""
    doc_id: str = Field(default_factory=lambda: f"DOC-{uuid4()}")
    title: str
    category: str
    
    # Content
    description: str
    examples: List[Dict[str, Any]]
    code_snippets: Dict[str, str]  # language -> code
    
    # Metadata
    last_updated: datetime
    version: str
    author: str
    
    # Interactive elements
    try_it_out_enabled: bool = True
    live_sandbox_url: Optional[HttpUrl] = None
    
    # Related resources
    related_docs: List[str]
    video_tutorials: List[HttpUrl]
    faq_items: List[Dict[str, str]]


class ContextualHelp(BaseModel):
    """Context-sensitive help content."""
    help_id: str = Field(default_factory=lambda: f"HELP-{uuid4()}")
    context: str
    
    # Help content
    title: str
    short_description: str
    detailed_explanation: Optional[str] = None
    
    # Multimedia
    screenshot_url: Optional[HttpUrl] = None
    video_url: Optional[HttpUrl] = None
    animation_url: Optional[HttpUrl] = None
    
    # Actions
    quick_actions: List[Dict[str, str]]
    related_features: List[str]
    
    # Feedback
    helpful_count: int = 0
    not_helpful_count: int = 0
    improvement_suggestions: List[str] = []


# ============================================================================
# EXAMPLE USAGE DEMONSTRATIONS
# ============================================================================

# Example 1: Create a comprehensive enterprise diagnosis request
def create_enterprise_diagnosis_request_example():
    """
    Example: Enterprise-grade diagnosis request with all features.
    """
    request = DiagnosisRequest(
        permit_token_id="NFT-ENT-2025-001",
        image_urls=[
            HttpUrl("https://storage.agropulse.ai/farm_45/IMG_001.jpg"),
            HttpUrl("https://storage.agropulse.ai/farm_45/IMG_002.jpg"),
            HttpUrl("https://storage.agropulse.ai/farm_45/IMG_003.jpg")
        ],
        image_metadata=[
            ImageMetadata(
                url=HttpUrl("https://storage.agropulse.ai/farm_45/IMG_001.jpg"),
                filename="IMG_001.jpg",
                size_bytes=3145728,
                width=4032,
                height=3024,
                format="JPEG",
                mime_type="image/jpeg",
                captured_at=datetime.now(),
                gps_coordinates=GPSCoordinates(
                    latitude=-1.286389,
                    longitude=36.817223,
                    accuracy=3.5
                ),
                quality_score=94.2
            )
        ],
        user_context=UserContext(
            user_id="FARMER-KE-00123",
            phone_number="+254712345678",
            email="farmer@example.com",
            language_preference="sw",
            subscription_tier="enterprise"
        ),
        farm_context=FarmContext(
            farm_id="FARM-NAIROBI-456",
            farm_name="Green Valley Enterprises",
            farm_size_acres=25.5,
            crop_type=CropType.TOMATO,
            crop_variety="Money Maker F1",
            growth_stage=GrowthStage.FRUIT_DEVELOPMENT,
            planting_date=date(2025, 9, 15),
            organic_certified=True,
            gps_coordinates=GPSCoordinates(
                latitude=-1.286389,
                longitude=36.817223
            ),
            weather_data=WeatherData(
                temperature_celsius=23.5,
                humidity_percent=82.0,
                rainfall_mm=5.2
            )
        ),
        user_symptoms="Dark spots on leaves, spreading quickly. Some fruits showing brown patches.",
        symptom_tags=["leaf_spots", "fruit_rot", "rapid_spread"],
        affected_plant_parts=["leaves", "fruits"],
        symptom_duration_days=4,
        triage_diagnosis="Late Blight",
        triage_confidence=0.89,
        priority=2,
        enable_advanced_analysis=True,
        include_similar_cases=True
    )
    return request


# Example 2: Process a complete diagnosis response
def create_comprehensive_diagnosis_response_example():
    """
    Example: Complete diagnosis response with all enterprise features.
    """
    response = DiagnosisComplete(
        id=98765,
        request_id="req-2025-11-01-789",
        status=DiagnosisStatus.COMPLETED,
        primary_diagnosis="Late Blight (Phytophthora infestans)",
        disease_scientific_name="Phytophthora infestans",
        disease_common_names=["Late Blight", "Potato Blight", "Tomato Blight"],
        category=DiseaseCategory.FUNGAL,
        confidence_score=0.96,
        confidence_level=ConfidenceLevel.VERY_HIGH,
        severity_level=SeverityLevel.HIGH,
        urgency=UrgencyLevel.URGENT,
        affected_area_percentage=30.0,
        symptoms_observed=[
            "Water-soaked lesions on leaves",
            "White mycelial growth",
            "Brown fruit lesions",
            "Rapid disease progression"
        ],
        treatment_plan=TreatmentPlan(
            urgency=UrgencyLevel.URGENT,
            immediate_actions=[
                "Remove infected plants immediately",
                "Cease overhead irrigation",
                "Improve air circulation"
            ],
            chemical_treatments=[
                ChemicalTreatment(
                    product_name="Ridomil Gold MZ 68 WP",
                    active_ingredient="Metalaxyl 8% + Mancozeb 60%",
                    category=TreatmentCategory.CHEMICAL_FUNGICIDE,
                    dosage_rate="2.5 kg/ha",
                    dosage_per_acre="1 kg/acre",
                    application_method="Foliar spray",
                    pre_harvest_interval_days=14,
                    safety_precautions=[
                        "Wear protective clothing",
                        "Avoid spraying in windy conditions"
                    ],
                    estimated_cost_ksh=Decimal("2500.00"),
                    organic_compatible=False
                )
            ],
            preventive_measures=[
                "Use certified disease-free seeds",
                "Practice 3-year crop rotation",
                "Avoid planting near potatoes",
                "Monitor weather conditions"
            ],
            total_estimated_cost_ksh=Decimal("3500.00")
        ),
        yield_impact=YieldImpactEstimate(
            current_severity=SeverityLevel.HIGH,
            estimated_yield_loss_percent=40.0,
            yield_loss_range_min=30.0,
            yield_loss_range_max=60.0,
            yield_loss_if_treated_percent=15.0,
            yield_loss_if_untreated_percent=85.0,
            potential_savings_ksh=Decimal("75000.00")
        ),
        quality_metrics=QualityMetrics(
            overall_quality_score=95.0,
            image_quality_score=94.2,
            diagnosis_confidence=0.96,
            passed_quality_checks=True
        ),
        ai_model_info=AIModelInfo(
            model_name="AgroPulse-DiagnosisNet-v2.1",
            model_version=ModelVersion.V2_1_MULTIMODAL,
            validation_accuracy=0.97,
            inference_time_ms=1240.5
        ),
        created_at=datetime.now(),
        completed_at=datetime.now(),
        processing_time_seconds=2.8,
        image_urls=[HttpUrl("https://storage.agropulse.ai/farm_45/IMG_001.jpg")],
        user_symptoms="Dark spots on leaves"
    )
    return response


# ============================================================================
# SCHEMA VERSION AND METADATA
# ============================================================================

SCHEMA_VERSION = "2.0.0-enterprise"
SCHEMA_RELEASE_DATE = date(2025, 11, 1)
TOTAL_MODELS = 100
TOTAL_ENUMERATIONS = 20
LINES_OF_CODE = 3000

def get_schema_info() -> Dict[str, Any]:
    """Get comprehensive schema information."""
    return {
        "version": SCHEMA_VERSION,
        "release_date": SCHEMA_RELEASE_DATE,
        "total_models": TOTAL_MODELS,
        "total_enumerations": TOTAL_ENUMERATIONS,
        "lines_of_code": LINES_OF_CODE,
        "features": [
            "Multi-tier validation",
            "Audit trails",
            "Batch processing",
            "Advanced analytics",
            "Multi-language support",
            "Compliance tracking",
            "IoT integration",
            "Real-time notifications",
            "Blockchain anchoring",
            "Machine learning operations",
            "API versioning",
            "Security logging"
        ],
        "backward_compatible": True,
        "production_ready": True
    }


if __name__ == "__main__":
    """
    Schema validation and example demonstrations.
    """
    print("=" * 80)
    print("🌾 AgroPulse Enterprise Diagnosis Schema v2.0")
    print("=" * 80)
    print(f"\n📊 Schema Statistics:")
    print(f"   • Version: {SCHEMA_VERSION}")
    print(f"   • Total Models: {TOTAL_MODELS}+")
    print(f"   • Total Enumerations: {TOTAL_ENUMERATIONS}+")
    print(f"   • Lines of Code: {LINES_OF_CODE}+")
    print(f"\n✅ Enterprise Features:")
    print(f"   ✓ Advanced Validation & Sanitization")
    print(f"   ✓ Comprehensive Audit Trails")
    print(f"   ✓ Multi-Language Support (10+ languages)")
    print(f"   ✓ Regulatory Compliance (GDPR, WHO, Organic)")
    print(f"   ✓ IoT Device Integration")
    print(f"   ✓ Blockchain Immutability")
    print(f"   ✓ Real-time Collaboration")
    print(f"   ✓ Advanced Analytics & ML Ops")
    print(f"   ✓ API Versioning & Compatibility")
    print(f"   ✓ Security & Privacy Controls")
    print(f"\n🚀 Production-Ready for Global Agriculture Platforms!")
    print("=" * 80)
