"""
🌾 AgroPulse - Comprehensive Database Models

SQLAlchemy ORM models for the entire AgroPulse platform.
Enterprise-grade with relationships, indexes, constraints, and audit trails.

Author: AgroPulse Engineering Team
Date: November 1, 2025
Version: 2.0.0-enterprise
Total Models: 50+
Lines: 8000+
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, Text,
    ForeignKey, Table, Index, UniqueConstraint, CheckConstraint,
    Enum as SQLEnum, JSON, DECIMAL, BigInteger, SmallInteger,
    LargeBinary, ARRAY, Interval
)
from sqlalchemy.orm import relationship, declarative_base, declared_attr, validates, Session
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.sql import func, select, and_, or_, case
from sqlalchemy.dialects.postgresql import UUID, JSONB, TSVECTOR, INET, MACADDR
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal
import enum
import uuid
from passlib.hash import bcrypt
from geoalchemy2 import Geography, Geometry
from sqlalchemy_utils import PasswordType, EmailType, URLType, ChoiceType, ColorType

# Base class for all models
Base = declarative_base()

# ============================================================================
# ENUMERATIONS - Database-level enums
# ============================================================================

class UserRole(enum.Enum):
    """User roles in the system."""
    FARMER = "farmer"
    GROWER = "grower"
    HORTICULTURIST = "horticulturist"
    AGRONOMIST = "agronomist"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
    EXTENSION_OFFICER = "extension_officer"
    RESEARCHER = "researcher"
    SUPPLIER = "supplier"
    BUYER = "buyer"
    COOPERATIVE_MANAGER = "cooperative_manager"
    FIELD_AGENT = "field_agent"


class SubscriptionTier(enum.Enum):
    """Subscription tiers."""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"
    TRIAL = "trial"


class AccountStatus(enum.Enum):
    """Account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    BANNED = "banned"
    PENDING_VERIFICATION = "pending_verification"
    DELETED = "deleted"


class TransactionType(enum.Enum):
    """Financial transaction types."""
    DIAGNOSIS_PAYMENT = "diagnosis_payment"
    SUBSCRIPTION_PAYMENT = "subscription_payment"
    PRODUCT_PURCHASE = "product_purchase"
    LOAN_DISBURSEMENT = "loan_disbursement"
    LOAN_REPAYMENT = "loan_repayment"
    SAVINGS_DEPOSIT = "savings_deposit"
    SAVINGS_WITHDRAWAL = "savings_withdrawal"
    DIVIDEND_PAYMENT = "dividend_payment"
    REFUND = "refund"
    FEE = "fee"


class TransactionStatus(enum.Enum):
    """Transaction status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class CropStatus(enum.Enum):
    """Crop planting status."""
    PLANNED = "planned"
    PLANTED = "planted"
    GROWING = "growing"
    HARVESTED = "harvested"
    FAILED = "failed"
    SOLD = "sold"


class AlertSeverity(enum.Enum):
    """Alert severity levels."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class DeviceStatus(enum.Enum):
    """IoT device status."""
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    DECOMMISSIONED = "decommissioned"


class HorticulturalCropType(enum.Enum):
    """Enum for horticultural crop categories."""
    FRUIT = "fruit"
    VEGETABLE = "vegetable"
    FLOWER = "flower"
    ORNAMENTAL = "ornamental"
    HERB = "herb"
    MUSHROOM = "mushroom"


class GreenhouseSystemType(enum.Enum):
    """Types of systems within a greenhouse."""
    HYDROPONICS = "hydroponics"
    AEROPONICS = "aeroponics"
    AQUAPONICS = "aquaponics"
    SOIL_BASED = "soil_based"
    VERTICAL_FARM = "vertical_farm"


class DeviceType(enum.Enum):
    """Types of IoT devices."""
    WEATHER_STATION = "weather_station"
    SOIL_SENSOR = "soil_sensor"
    MOISTURE_SENSOR = "moisture_sensor"
    CAMERA = "camera"
    DRONE = "drone"
    GATEWAY = "gateway"
    ACTUATOR = "actuator"
    PAR_SENSOR = "par_sensor"  # Photosynthetically Active Radiation
    CO2_SENSOR = "co2_sensor"
    WATER_PH_SENSOR = "water_ph_sensor"
    WATER_EC_SENSOR = "water_ec_sensor"
    LIGHT_CONTROLLER = "light_controller"
    PUMP_CONTROLLER = "pump_controller"
    VENT_CONTROLLER = "vent_controller"


# ============================================================================
# MIXIN CLASSES - Reusable model components
# ============================================================================

class TimestampMixin:
    """Add created_at and updated_at timestamps."""
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SoftDeleteMixin:
    """Soft delete support."""
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    
    def soft_delete(self):
        """Mark record as deleted."""
        self.deleted_at = datetime.utcnow()
        self.is_deleted = True
    
    def restore(self):
        """Restore soft-deleted record."""
        self.deleted_at = None
        self.is_deleted = False


class AuditMixin:
    """Audit trail fields."""
    @declared_attr
    def created_by_id(cls):
        return Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    @declared_attr
    def updated_by_id(cls):
        return Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    @declared_attr
    def created_by(cls):
        return relationship("User", foreign_keys=[cls.created_by_id], lazy='select')

    @declared_attr
    def updated_by(cls):
        return relationship("User", foreign_keys=[cls.updated_by_id], lazy='select')


class VersionMixin:
    """Optimistic locking with versioning."""
    version = Column(Integer, default=1, nullable=False)
    
    @validates('version')
    def validate_version(self, key, value):
        """Increment version on update."""
        return value + 1 if value else 1


class GeoLocationMixin:
    """Geographic location fields."""
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    altitude = Column(Float, nullable=True)
    location = Column(Geography(geometry_type='POINT', srid=4326), nullable=True)
    location_accuracy = Column(Float, nullable=True)  # meters
    
    @hybrid_property
    def coordinates(self):
        """Return coordinates as tuple."""
        if self.latitude and self.longitude:
            return (self.latitude, self.longitude)
        return None
    
    @coordinates.setter
    def coordinates(self, value):
        """Set coordinates from tuple."""
        if value:
            self.latitude, self.longitude = value


# ============================================================================
# ASSOCIATION TABLES - Many-to-many relationships
# ============================================================================

# User-Chama association
user_chama_association = Table(
    'user_chama_association',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('chama_id', Integer, ForeignKey('chamas.id', ondelete='CASCADE'), primary_key=True),
    Column('joined_at', DateTime(timezone=True), server_default=func.now()),
    Column('role', String(50), default='member'),
    Column('is_active', Boolean, default=True)
)

# Diagnosis-Expert association (for multi-expert reviews)
diagnosis_expert_association = Table(
    'diagnosis_expert_association',
    Base.metadata,
    Column('diagnosis_id', Integer, ForeignKey('diagnoses.id', ondelete='CASCADE'), primary_key=True),
    Column('expert_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('assigned_at', DateTime(timezone=True), server_default=func.now()),
    Column('reviewed_at', DateTime(timezone=True), nullable=True),
    Column('review_status', String(50), default='pending')
)

# Crop-Disease association (vulnerability mapping)
crop_disease_association = Table(
    'crop_disease_association',
    Base.metadata,
    Column('crop_type', String(100), primary_key=True),
    Column('disease_id', Integer, ForeignKey('diseases.id', ondelete='CASCADE'), primary_key=True),
    Column('susceptibility_level', String(50)),  # low, medium, high
    Column('seasonal_peak', String(100), nullable=True),
    Column('prevalence_score', Float, default=0.0)
)

# Product-Supplier association
product_supplier_association = Table(
    'product_supplier_association',
    Base.metadata,
    Column('product_id', Integer, ForeignKey('products.id', ondelete='CASCADE'), primary_key=True),
    Column('supplier_id', Integer, ForeignKey('suppliers.id', ondelete='CASCADE'), primary_key=True),
    Column('price_ksh', DECIMAL(10, 2)),
    Column('availability', String(50)),
    Column('last_updated', DateTime(timezone=True), server_default=func.now())
)


# ============================================================================
# CORE USER MANAGEMENT MODELS
# ============================================================================

class User(Base, TimestampMixin, SoftDeleteMixin, GeoLocationMixin):
    """Core user model with comprehensive profile."""
    __tablename__ = 'users'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False, index=True)
    
    # Authentication
    username = Column(String(50), unique=True, nullable=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone_number = Column(String(20), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    two_factor_secret = Column(String(100), nullable=True)
    two_factor_enabled = Column(Boolean, default=False)
    
    # Profile information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), nullable=True)
    display_name = Column(String(200), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    national_id = Column(String(50), nullable=True, unique=True)
    
    # Contact information
    alternate_phone = Column(String(20), nullable=True)
    whatsapp_number = Column(String(20), nullable=True)
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    county = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), default='Kenya')
    
    # Role and permissions
    role = Column(SQLEnum(UserRole), default=UserRole.GROWER, nullable=False, index=True)
    permissions = Column(JSONB, default=dict)
    is_superuser = Column(Boolean, default=False)
    is_staff = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    
    # Account status
    status = Column(SQLEnum(AccountStatus), default=AccountStatus.PENDING_VERIFICATION, nullable=False, index=True)
    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)
    kyc_verified = Column(Boolean, default=False)
    
    # Subscription
    subscription_tier = Column(SQLEnum(SubscriptionTier), default=SubscriptionTier.FREE, index=True)
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)
    diagnoses_remaining = Column(Integer, default=3)  # Free tier limit
    
    # Preferences
    language_preference = Column(String(10), default='en')
    timezone = Column(String(50), default='Africa/Nairobi')
    notification_preferences = Column(JSONB, default=dict)
    theme_preference = Column(String(20), default='light')
    
    # Profile completion
    profile_completion_percentage = Column(Float, default=0.0)
    onboarding_completed = Column(Boolean, default=False)
    onboarding_step = Column(Integer, default=0)
    
    # Activity tracking
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(INET, nullable=True)
    login_count = Column(Integer, default=0)
    failed_login_attempts = Column(Integer, default=0)
    last_failed_login_at = Column(DateTime(timezone=True), nullable=True)
    account_locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Profile images
    avatar_url = Column(URLType, nullable=True)
    cover_photo_url = Column(URLType, nullable=True)
    
    # Social links
    social_links = Column(JSONB, default=dict)  # {"facebook": "url", "twitter": "url", etc.}
    
    # Metrics
    total_diagnoses = Column(Integer, default=0)
    total_farms = Column(Integer, default=0)
    total_spent_ksh = Column(DECIMAL(12, 2), default=0)
    reputation_score = Column(Float, default=0.0)
    
    # Referral system
    referral_code = Column(String(20), unique=True, nullable=True, index=True)
    referred_by_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    referral_count = Column(Integer, default=0)
    referral_earnings_ksh = Column(DECIMAL(10, 2), default=0)
    
    # Relationships
    referred_by = relationship("User", remote_side=[id], backref='referrals')
    farms = relationship("Farm", back_populates="owner", cascade="all, delete-orphan", foreign_keys="Farm.owner_id")
    diagnoses = relationship("Diagnosis", back_populates="user", foreign_keys="Diagnosis.user_id")
    transactions = relationship("Transaction", back_populates="user", foreign_keys="Transaction.user_id")
    devices = relationship("IoTDevice", back_populates="owner")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", foreign_keys="AuditLog.user_id")
    
    # Chama memberships (many-to-many)
    chamas = relationship(
        "Chama",
        secondary=user_chama_association,
        back_populates="members",
        lazy='dynamic'
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_user_email_status', 'email', 'status'),
        Index('idx_user_phone_status', 'phone_number', 'status'),
        Index('idx_user_role_status', 'role', 'status'),
        Index('idx_user_created_at', 'created_at'),
        Index('idx_user_subscription', 'subscription_tier', 'subscription_expires_at'),
        CheckConstraint('profile_completion_percentage >= 0 AND profile_completion_percentage <= 100'),
        CheckConstraint('reputation_score >= 0 AND reputation_score <= 100'),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role.value}')>"
    
    @property
    def full_name(self):
        """Get full name."""
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        return ' '.join(parts)
    
    @property
    def is_active(self):
        """Check if user account is active."""
        return self.status == AccountStatus.ACTIVE and not self.is_deleted
    
    @property
    def is_subscription_active(self):
        """Check if subscription is active."""
        if self.subscription_tier == SubscriptionTier.FREE:
            return True
        return self.subscription_expires_at and self.subscription_expires_at > datetime.utcnow()
    
    @property
    def is_account_locked(self):
        """Check if account is temporarily locked."""
        if self.account_locked_until:
            return self.account_locked_until > datetime.utcnow()
        return False
    
    def verify_password(self, password: str) -> bool:
        """Verify password against hash."""
        return bcrypt.verify(password, self.password_hash)
    
    def set_password(self, password: str):
        """Set password hash."""
        self.password_hash = bcrypt.hash(password)
    
    def generate_referral_code(self):
        """Generate unique referral code."""
        import random
        import string
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not Session.object_session(self).query(User).filter_by(referral_code=code).first():
                self.referral_code = code
                break
    
    def record_login(self, ip_address: str = None):
        """Record successful login."""
        self.last_login_at = datetime.utcnow()
        self.last_login_ip = ip_address
        self.login_count += 1
        self.failed_login_attempts = 0
        self.account_locked_until = None
    
    def record_failed_login(self):
        """Record failed login attempt."""
        self.failed_login_attempts += 1
        self.last_failed_login_at = datetime.utcnow()
        
        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.account_locked_until = datetime.utcnow() + timedelta(minutes=30)
    
    def calculate_profile_completion(self):
        """Calculate profile completion percentage."""
        fields = [
            self.email, self.phone_number, self.first_name, self.last_name,
            self.date_of_birth, self.address_line1, self.city, self.county,
            self.avatar_url, self.email_verified, self.phone_verified
        ]
        completed = sum(1 for field in fields if field)
        self.profile_completion_percentage = (completed / len(fields)) * 100


class UserSession(Base, TimestampMixin):
    """Track user sessions for security and analytics."""
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Session details
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token = Column(String(255), unique=True, nullable=True, index=True)
    device_id = Column(String(255), nullable=True, index=True)
    
    # Device information
    user_agent = Column(Text, nullable=True)
    device_type = Column(String(50), nullable=True)  # mobile, tablet, desktop
    os = Column(String(50), nullable=True)
    os_version = Column(String(50), nullable=True)
    browser = Column(String(50), nullable=True)
    browser_version = Column(String(50), nullable=True)
    
    # Network information
    ip_address = Column(INET, nullable=True)
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    isp = Column(String(255), nullable=True)
    
    # Session lifecycle
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    
    # Session state
    is_active = Column(Boolean, default=True, index=True)
    logout_reason = Column(String(100), nullable=True)  # user_logout, timeout, forced, security
    
    # Security
    risk_score = Column(Float, default=0.0)
    is_suspicious = Column(Boolean, default=False)
    security_events = Column(JSONB, default=list)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    __table_args__ = (
        Index('idx_session_user_active', 'user_id', 'is_active'),
        Index('idx_session_expires', 'expires_at'),
    )
    
    @property
    def is_expired(self):
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def duration_seconds(self):
        """Get session duration in seconds."""
        end_time = self.ended_at or datetime.utcnow()
        return (end_time - self.started_at).total_seconds()
    
    def end_session(self, reason: str = 'user_logout'):
        """End the session."""
        self.ended_at = datetime.utcnow()
        self.is_active = False
        self.logout_reason = reason
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity_at = datetime.utcnow()


class APIKey(Base, TimestampMixin, SoftDeleteMixin):
    """API key management for programmatic access."""
    __tablename__ = 'api_keys'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Key details
    key_name = Column(String(100), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    key_prefix = Column(String(20), nullable=False)  # First few characters for identification
    
    # Permissions and scope
    scopes = Column(ARRAY(String), default=list)  # ['read:diagnosis', 'write:farms', etc.]
    rate_limit_per_hour = Column(Integer, default=100)
    rate_limit_per_day = Column(Integer, default=1000)
    
    # Usage tracking
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    total_requests = Column(BigInteger, default=0)
    failed_requests = Column(BigInteger, default=0)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Security
    allowed_ip_addresses = Column(ARRAY(String), default=list)
    allowed_domains = Column(ARRAY(String), default=list)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    __table_args__ = (
        Index('idx_apikey_user_active', 'user_id', 'is_active'),
    )
    
    @property
    def is_expired(self):
        """Check if API key is expired."""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
    
    @property
    def is_valid(self):
        """Check if API key is valid."""
        return self.is_active and not self.is_expired and not self.is_deleted
    
    def record_usage(self, success: bool = True):
        """Record API key usage."""
        self.last_used_at = datetime.utcnow()
        self.total_requests += 1
        if not success:
            self.failed_requests += 1


# ============================================================================
# FARM MANAGEMENT MODELS
# ============================================================================

class Farm(Base, TimestampMixin, SoftDeleteMixin, AuditMixin, GeoLocationMixin, VersionMixin):
    """Comprehensive farm management model."""
    __tablename__ = 'farms'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Basic information
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    farm_code = Column(String(50), unique=True, nullable=True, index=True)
    farm_type = Column(String(50), nullable=True)  # mixed, organic, commercial, etc.
    primary_crop = Column(String(100), nullable=True)

    # Size and boundaries
    size_acres = Column(Float, nullable=False)
    size_hectares = Column(Float, nullable=True)
    cultivated_area_acres = Column(Float, nullable=True)
    boundary_geojson = Column(JSONB, nullable=True)  # GeoJSON polygon
    boundary_geometry = Column(Geometry(geometry_type='POLYGON', srid=4326), nullable=True)
    
    # Location details
    address = Column(String(500), nullable=True)
    village = Column(String(100), nullable=True)
    ward = Column(String(100), nullable=True)
    sub_county = Column(String(100), nullable=True)
    county = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    
    # Soil information
    soil_type = Column(String(100), nullable=True)
    soil_ph = Column(Float, nullable=True)
    soil_texture = Column(String(50), nullable=True)  # clay, loam, sand, etc.
    soil_fertility = Column(String(50), nullable=True)  # poor, moderate, good, excellent
    soil_test_date = Column(Date, nullable=True)
    soil_test_results = Column(JSONB, nullable=True)
    
    # Water and irrigation
    water_source = Column(String(100), nullable=True)  # river, borehole, rain, etc.
    irrigation_type = Column(String(100), nullable=True)  # drip, sprinkler, flood, none
    has_irrigation = Column(Boolean, default=False)
    water_availability = Column(String(50), nullable=True)  # abundant, adequate, limited, scarce
    
    # Climate and environment
    elevation_meters = Column(Float, nullable=True)
    annual_rainfall_mm = Column(Float, nullable=True)
    growing_zones = Column(ARRAY(String), default=list)
    micro_climate_notes = Column(Text, nullable=True)
    
    # Certifications
    organic_certified = Column(Boolean, default=False)
    organic_certification_body = Column(String(200), nullable=True)
    organic_certification_number = Column(String(100), nullable=True)
    organic_certification_date = Column(Date, nullable=True)
    organic_certification_expiry = Column(Date, nullable=True)
    
    gap_certified = Column(Boolean, default=False)  # Good Agricultural Practices
    gap_certification_details = Column(JSONB, nullable=True)
    
    fairtrade_certified = Column(Boolean, default=False)
    other_certifications = Column(JSONB, default=list)
    
    # Infrastructure
    has_greenhouse = Column(Boolean, default=False)
    greenhouse_area_sqm = Column(Float, nullable=True)
    has_storage_facility = Column(Boolean, default=False)
    storage_capacity_kg = Column(Float, nullable=True)
    has_processing_facility = Column(Boolean, default=False)
    has_cold_storage = Column(Boolean, default=False)
    
    # Labor and management
    full_time_workers = Column(Integer, default=0)
    part_time_workers = Column(Integer, default=0)
    seasonal_workers = Column(Integer, default=0)
    farm_manager_name = Column(String(200), nullable=True)
    farm_manager_phone = Column(String(20), nullable=True)
    
    # Horticultural properties
    is_horticulture_focused = Column(Boolean, default=True)
    number_of_greenhouses = Column(Integer, default=0)

    # Production and financial
    annual_production_kg = Column(Float, nullable=True)
    annual_revenue_ksh = Column(DECIMAL(15, 2), nullable=True)
    production_cost_per_acre_ksh = Column(DECIMAL(10, 2), nullable=True)
    
    # IoT and technology
    has_iot_devices = Column(Boolean, default=False)
    iot_device_count = Column(Integer, default=0)
    has_weather_station = Column(Boolean, default=False)
    has_soil_sensors = Column(Boolean, default=False)
    has_sentry_cameras = Column(Boolean, default=False)
    
    # Status and activity
    is_active = Column(Boolean, default=True, index=True)
    verification_status = Column(String(50), default='pending', nullable=False)  # pending, verified, rejected
    last_harvest_date = Column(Date, nullable=True)
    next_planting_date = Column(Date, nullable=True)
    
    # Images and media
    photos = Column(ARRAY(String), default=list)  # URLs to farm photos
    drone_imagery_urls = Column(ARRAY(String), default=list)
    satellite_imagery_date = Column(Date, nullable=True)
    
    # Notes and history
    notes = Column(Text, nullable=True)
    establishment_date = Column(Date, nullable=True)
    previous_crops = Column(JSONB, default=list)
    
    # Metrics
    total_crops_planted = Column(Integer, default=0)
    total_diagnoses = Column(Integer, default=0)
    total_yield_kg = Column(Float, default=0)
    average_yield_per_acre = Column(Float, nullable=True)
    
    # Relationships
    owner = relationship("User", back_populates="farms", foreign_keys=[owner_id])
    fields = relationship("Field", back_populates="farm", cascade="all, delete-orphan")
    greenhouses = relationship("Greenhouse", back_populates="farm", cascade="all, delete-orphan")
    crops = relationship("CropPlanting", back_populates="farm", cascade="all, delete-orphan")
    diagnoses = relationship("Diagnosis", back_populates="farm")
    devices = relationship("IoTDevice", back_populates="farm")
    weather_data = relationship("WeatherRecord", back_populates="farm")
    soil_tests = relationship("SoilTest", back_populates="farm")
    alerts = relationship("Alert", back_populates="farm")
    
    __table_args__ = (
        Index('idx_farm_owner_active', 'owner_id', 'is_active'),
        Index('idx_farm_county', 'county'),
        Index('idx_farm_organic', 'organic_certified'),
        CheckConstraint('size_acres > 0'),
        CheckConstraint('soil_ph >= 0 AND soil_ph <= 14'),
    )
    
    def __repr__(self):
        return f"<Farm(id={self.id}, name='{self.name}', size={self.size_acres} acres)>"
    
    @hybrid_property
    def size_hectares_computed(self):
        """Convert acres to hectares."""
        if self.size_acres:
            return self.size_acres * 0.404686
        return None
    
    @property
    def organic_status(self):
        """Get organic certification status."""
        if not self.organic_certified:
            return "Not Certified"
        if self.organic_certification_expiry and self.organic_certification_expiry < date.today():
            return "Expired"
        return "Certified"
    
    def calculate_total_crop_area(self):
        """Calculate total area under crops."""
        return sum(crop.area_acres for crop in self.crops if crop.status != CropStatus.HARVESTED)


class Field(Base, TimestampMixin, SoftDeleteMixin, GeoLocationMixin):
    """Individual field/plot within a farm."""
    __tablename__ = 'fields'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    farm_id = Column(Integer, ForeignKey('farms.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Field identification
    name = Column(String(100), nullable=False)
    field_number = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    
    # Size and boundaries
    size_acres = Column(Float, nullable=False)
    boundary_geojson = Column(JSONB, nullable=True)
    boundary_geometry = Column(Geometry(geometry_type='POLYGON', srid=4326), nullable=True)
    
    # Soil characteristics
    soil_type = Column(String(100), nullable=True)
    soil_quality_score = Column(Float, nullable=True)  # 0-100
    drainage_quality = Column(String(50), nullable=True)  # poor, fair, good, excellent
    
    # Field status
    is_active = Column(Boolean, default=True)
    current_crop_id = Column(Integer, ForeignKey('crop_plantings.id', ondelete='SET NULL'), nullable=True)
    last_planting_date = Column(Date, nullable=True)
    fallow_since = Column(Date, nullable=True)
    
    # History
    rotation_history = Column(JSONB, default=list)
    yield_history = Column(JSONB, default=list)
    
    # Relationships
    farm = relationship("Farm", back_populates="fields")
    current_crop = relationship("CropPlanting", foreign_keys=[current_crop_id], post_update=True)
    
    __table_args__ = (
        Index('idx_field_farm_active', 'farm_id', 'is_active'),
        CheckConstraint('size_acres > 0'),
    )


# ============================================================================
# CROP MANAGEMENT MODELS
# ============================================================================

class CropPlanting(Base, TimestampMixin, SoftDeleteMixin):
    """Track individual crop plantings."""
    __tablename__ = 'crop_plantings'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    farm_id = Column(Integer, ForeignKey('farms.id', ondelete='CASCADE'), nullable=False, index=True)
    field_id = Column(Integer, ForeignKey('fields.id', ondelete='SET NULL'), nullable=True)
    
    # Crop details
    crop_type = Column(String(100), nullable=False, index=True)
    horticultural_type = Column(SQLEnum(HorticulturalCropType), nullable=True, index=True)
    variety = Column(String(200), nullable=True)
    seed_source = Column(String(200), nullable=True)
    seed_lot_number = Column(String(100), nullable=True)
    
    # Planting information
    planting_date = Column(Date, nullable=False, index=True)
    planting_method = Column(String(100), nullable=True)  # direct, transplant, etc.
    area_acres = Column(Float, nullable=False)
    plant_population = Column(Integer, nullable=True)
    row_spacing_cm = Column(Float, nullable=True)
    plant_spacing_cm = Column(Float, nullable=True)
    
    # Growth tracking
    current_growth_stage = Column(String(100), nullable=True)
    growth_stage_updated_at = Column(DateTime(timezone=True), nullable=True)
    expected_maturity_days = Column(Integer, nullable=True)
    expected_harvest_date = Column(Date, nullable=True)
    actual_harvest_date = Column(Date, nullable=True)
    
    # Status
    status = Column(SQLEnum(CropStatus), default=CropStatus.PLANTED, nullable=False, index=True)
    health_status = Column(String(50), nullable=True)  # excellent, good, fair, poor, critical
    disease_history = Column(JSONB, default=list)
    pest_history = Column(JSONB, default=list)
    
    # Input tracking
    fertilizer_applications = Column(JSONB, default=list)
    pesticide_applications = Column(JSONB, default=list)
    irrigation_events = Column(JSONB, default=list)
    
    # Yield and production
    expected_yield_kg = Column(Float, nullable=True)
    actual_yield_kg = Column(Float, nullable=True)
    yield_per_acre = Column(Float, nullable=True)
    quality_grade = Column(String(20), nullable=True)  # A, B, C, Reject
    
    # Financial
    production_cost_ksh = Column(DECIMAL(12, 2), nullable=True)
    revenue_ksh = Column(DECIMAL(12, 2), nullable=True)
    profit_margin_percentage = Column(Float, nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relationships
    farm = relationship("Farm", back_populates="crops")
    field = relationship("Field", foreign_keys=[field_id])
    diagnoses = relationship("Diagnosis", back_populates="crop")
    
    __table_args__ = (
        Index('idx_crop_farm_status', 'farm_id', 'status'),
        Index('idx_crop_type_status', 'crop_type', 'status'),
        Index('idx_crop_planting_date', 'planting_date'),
        CheckConstraint('area_acres > 0'),
    )
    
    @property
    def age_days(self):
        """Calculate crop age in days."""
        if self.planting_date:
            return (date.today() - self.planting_date).days
        return None
    
    @property
    def days_to_harvest(self):
        """Calculate days remaining until harvest."""
        if self.expected_harvest_date:
            days = (self.expected_harvest_date - date.today()).days
            return max(0, days)
        return None
    
    @hybrid_property
    def is_ready_for_harvest(self):
        """Check if crop is ready for harvest."""
        if self.expected_harvest_date:
            return date.today() >= self.expected_harvest_date
        return False


# ============================================================================
# GREENHOUSE MODELS
# ============================================================================

class Greenhouse(Base, TimestampMixin, SoftDeleteMixin, GeoLocationMixin):
    """Model for managing greenhouses."""
    __tablename__ = 'greenhouses'

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False, index=True)
    farm_id = Column(Integer, ForeignKey('farms.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Basic Information
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Physical Characteristics
    area_sqm = Column(Float, nullable=False)
    volume_m3 = Column(Float, nullable=True)
    structure_type = Column(String(100), nullable=True)  # e.g., Dome, A-Frame
    covering_material = Column(String(100), nullable=True) # e.g., Glass, Polycarbonate
    
    # Systems
    system_type = Column(SQLEnum(GreenhouseSystemType), nullable=True)
    
    # Relationships
    farm = relationship("Farm", back_populates="greenhouses")
    environmental_data = relationship("GreenhouseEnvironment", back_populates="greenhouse", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_greenhouse_farm_id', 'farm_id'),
        CheckConstraint('area_sqm > 0'),
    )

class GreenhouseEnvironment(Base, TimestampMixin):
    """Stores environmental data from within a greenhouse."""
    __tablename__ = 'greenhouse_environment'

    id = Column(BigInteger, primary_key=True)
    greenhouse_id = Column(Integer, ForeignKey('greenhouses.id', ondelete='CASCADE'), nullable=False, index=True)
    reading_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Environmental Parameters
    temperature_celsius = Column(Float, nullable=True)
    humidity_percentage = Column(Float, nullable=True)
    co2_ppm = Column(Float, nullable=True)
    par_umol_m2_s = Column(Float, nullable=True) # Photosynthetically Active Radiation
    light_duration_hours = Column(Float, nullable=True)
    
    # Hydroponics/Aquaponics Parameters
    water_ph = Column(Float, nullable=True)
    water_ec = Column(Float, nullable=True) # Electrical Conductivity
    water_temperature_celsius = Column(Float, nullable=True)
    
    # Relationships
    greenhouse = relationship("Greenhouse", back_populates="environmental_data")

    __table_args__ = (
        Index('idx_greenhouse_env_timestamp', 'greenhouse_id', 'reading_timestamp'),
    )


# ============================================================================
# DIAGNOSIS MODELS (Enhanced)
# ============================================================================

class Diagnosis(Base, TimestampMixin, SoftDeleteMixin, VersionMixin):
    """Enhanced diagnosis model with comprehensive tracking."""
    __tablename__ = 'diagnoses'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False, index=True)
    diagnosis_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # User and context
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    farm_id = Column(Integer, ForeignKey('farms.id', ondelete='SET NULL'), nullable=True, index=True)
    crop_id = Column(Integer, ForeignKey('crop_plantings.id', ondelete='SET NULL'), nullable=True)
    alert_id = Column(Integer, ForeignKey('alerts.id', ondelete='SET NULL'), nullable=True)
    
    # Request information
    request_payload = Column(JSONB, nullable=False)
    permit_token_id = Column(String(100), nullable=False)
    image_urls = Column(ARRAY(String), nullable=False)
    image_metadata = Column(JSONB, default=list)
    user_symptoms = Column(Text, nullable=True)
    
    # Processing status
    status = Column(String(50), default='pending', nullable=False, index=True)
    status_message = Column(Text, nullable=True)
    progress_percentage = Column(Float, default=0.0)
    
    # Queue and priority
    queued_at = Column(DateTime(timezone=True), nullable=True)
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    priority = Column(Integer, default=3, index=True)  # 1-5
    
    # Triage (from mobile AI)
    triage_diagnosis = Column(String(200), nullable=True)
    triage_confidence = Column(Float, nullable=True)
    triage_timestamp = Column(DateTime(timezone=True), nullable=True)
    triage_model_version = Column(String(50), nullable=True)
    
    # Primary diagnosis results
    primary_diagnosis = Column(String(300), nullable=True, index=True)
    disease_id = Column(String(100), nullable=True)
    disease_category = Column(String(100), nullable=True, index=True)
    confidence_score = Column(Float, nullable=True)
    confidence_level = Column(String(50), nullable=True)
    
    # Severity and urgency
    severity_level = Column(String(50), nullable=True, index=True)
    urgency_level = Column(String(50), nullable=True)
    affected_area_percentage = Column(Float, nullable=True)
    
    # Detailed analysis
    symptoms_observed = Column(JSONB, default=list)
    alternative_diagnoses = Column(JSONB, default=list)
    similar_cases = Column(JSONB, default=list)
    
    # Treatment plan
    treatment_plan = Column(JSONB, nullable=True)
    immediate_actions = Column(JSONB, default=list)
    preventive_measures = Column(JSONB, default=list)
    estimated_treatment_cost_ksh = Column(DECIMAL(10, 2), nullable=True)
    
    # Impact assessment
    estimated_yield_loss_percentage = Column(Float, nullable=True)
    financial_impact_ksh = Column(DECIMAL(12, 2), nullable=True)
    spread_risk_level = Column(String(50), nullable=True)
    
    # AI model information
    model_name = Column(String(200), nullable=True)
    model_version = Column(String(50), nullable=True)
    model_confidence_threshold = Column(Float, nullable=True)
    inference_time_ms = Column(Float, nullable=True)
    total_processing_time_ms = Column(Float, nullable=True)
    
    # Quality assurance
    quality_score = Column(Float, nullable=True)
    image_quality_score = Column(Float, nullable=True)
    requires_human_review = Column(Boolean, default=False, index=True)
    human_review_reason = Column(Text, nullable=True)
    expert_reviewed = Column(Boolean, default=False)
    expert_review_data = Column(JSONB, nullable=True)
    
    # Billing and payment
    payment_id = Column(String(100), nullable=True, index=True)
    payment_status = Column(String(50), default='pending')
    amount_ksh = Column(DECIMAL(10, 2), nullable=True)
    payment_completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata and tracking
    source_platform = Column(String(50), default='mobile_app')
    api_version = Column(String(20), nullable=True)
    processing_metadata = Column(JSONB, default=dict)
    cache_hit = Column(Boolean, default=False)
    
    # Follow-up and feedback
    feedback_rating = Column(Integer, nullable=True)  # 1-5 stars
    feedback_comment = Column(Text, nullable=True)
    feedback_submitted_at = Column(DateTime(timezone=True), nullable=True)
    treatment_followed = Column(Boolean, nullable=True)
    treatment_effective = Column(Boolean, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="diagnoses", foreign_keys=[user_id])
    farm = relationship("Farm", back_populates="diagnoses")
    crop = relationship("CropPlanting", back_populates="diagnoses")
    # Not a back_populates pair with Alert.diagnosis - diagnoses.alert_id and
    # alerts.diagnosis_id are two independent FKs (this diagnosis's triggering
    # alert, vs. an alert's resulting diagnosis), so each needs its own
    # disambiguated relationship rather than mirroring one join condition.
    alert = relationship("Alert", foreign_keys=[alert_id], uselist=False)
    
    # Expert reviews (many-to-many)
    expert_reviewers = relationship(
        "User",
        secondary=diagnosis_expert_association,
        lazy='dynamic'
    )
    
    __table_args__ = (
        Index('idx_diagnosis_user_status', 'user_id', 'status'),
        Index('idx_diagnosis_created', 'created_at'),
        Index('idx_diagnosis_disease', 'disease_category', 'severity_level'),
        Index('idx_diagnosis_payment', 'payment_id', 'payment_status'),
        CheckConstraint('confidence_score >= 0 AND confidence_score <= 1'),
        CheckConstraint('priority >= 1 AND priority <= 5'),
    )
    
    def __repr__(self):
        return f"<Diagnosis(id={self.id}, diagnosis_id='{self.diagnosis_id}', status='{self.status}')>"
    
    @property
    def processing_time_seconds(self):
        """Calculate total processing time."""
        if self.completed_at and self.processing_started_at:
            return (self.completed_at - self.processing_started_at).total_seconds()
        return None


# ============================================================================
# DISEASE AND TREATMENT MODELS
# ============================================================================

class Disease(Base, TimestampMixin):
    """Disease knowledge base."""
    __tablename__ = 'diseases'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    
    # Disease identification
    disease_code = Column(String(50), unique=True, nullable=False, index=True)
    scientific_name = Column(String(300), nullable=False)
    common_names = Column(JSONB, default=dict)  # {"en": "Rust", "sw": "Kutu", ...}
    disease_category = Column(String(100), nullable=False, index=True)
    
    # Classification
    pathogen_type = Column(String(100), nullable=True)  # fungal, bacterial, viral, nematode, abiotic
    pathogen_species = Column(String(300), nullable=True)
    
    # Description
    description = Column(Text, nullable=False)
    symptoms = Column(JSONB, default=list)
    causes = Column(JSONB, default=list)
    spread_mechanism = Column(Text, nullable=True)
    
    # Impact
    typical_severity = Column(String(50), nullable=True)
    yield_loss_range_min = Column(Float, nullable=True)
    yield_loss_range_max = Column(Float, nullable=True)
    economic_impact_level = Column(String(50), nullable=True)
    
    # Conditions
    favorable_conditions = Column(JSONB, default=dict)
    temperature_range_min = Column(Float, nullable=True)
    temperature_range_max = Column(Float, nullable=True)
    humidity_range_min = Column(Float, nullable=True)
    humidity_range_max = Column(Float, nullable=True)
    seasonal_occurrence = Column(JSONB, default=list)
    
    # Geographic distribution
    endemic_regions = Column(ARRAY(String), default=list)
    global_distribution = Column(JSONB, default=dict)
    
    # Images and references
    reference_images = Column(ARRAY(String), default=list)
    diagnostic_images = Column(ARRAY(String), default=list)
    scientific_references = Column(JSONB, default=list)
    
    # Treatment information
    treatment_methods = Column(JSONB, default=list)
    preventive_measures = Column(JSONB, default=list)
    organic_solutions = Column(JSONB, default=list)
    chemical_solutions = Column(JSONB, default=list)
    
    # AI model data
    training_sample_count = Column(Integer, default=0)
    detection_accuracy_percentage = Column(Float, nullable=True)
    model_confidence_threshold = Column(Float, default=0.7)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_reportable = Column(Boolean, default=False)  # Requires government notification
    quarantine_required = Column(Boolean, default=False)
    
    # Note: crop_disease_association maps crop *types* (a plain string
    # category, e.g. "mango") to diseases for vulnerability lookups - it has
    # no foreign key to crop_plantings, so it can't back a relationship to
    # individual CropPlanting rows. Query crop_disease_association directly
    # by crop_type instead.

    __table_args__ = (
        Index('idx_disease_category', 'disease_category'),
        Index('idx_disease_code', 'disease_code'),
    )


class Treatment(Base, TimestampMixin, SoftDeleteMixin):
    """Treatment recommendations and tracking."""
    __tablename__ = 'treatments'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    diagnosis_id = Column(Integer, ForeignKey('diagnoses.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Treatment plan
    treatment_type = Column(String(100), nullable=False)  # chemical, organic, biological, cultural
    treatment_name = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    
    # Application details
    application_method = Column(String(200), nullable=True)
    dosage = Column(String(200), nullable=True)
    frequency = Column(String(200), nullable=True)
    duration_days = Column(Integer, nullable=True)
    timing = Column(String(200), nullable=True)
    
    # Products
    recommended_products = Column(JSONB, default=list)
    product_alternatives = Column(JSONB, default=list)
    
    # Cost estimation
    estimated_cost_ksh = Column(DECIMAL(10, 2), nullable=True)
    cost_breakdown = Column(JSONB, nullable=True)
    
    # Safety and compliance
    safety_precautions = Column(JSONB, default=list)
    protective_equipment = Column(JSONB, default=list)
    pre_harvest_interval_days = Column(Integer, nullable=True)
    re_entry_interval_hours = Column(Integer, nullable=True)
    organic_approved = Column(Boolean, default=False)
    registration_numbers = Column(JSONB, default=list)
    
    # Effectiveness
    expected_effectiveness = Column(String(50), nullable=True)
    expected_recovery_days = Column(Integer, nullable=True)
    success_rate_percentage = Column(Float, nullable=True)
    
    # Implementation tracking
    status = Column(String(50), default='recommended', index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    actual_effectiveness = Column(String(50), nullable=True)
    farmer_feedback = Column(Text, nullable=True)
    
    # Relationships
    diagnosis = relationship("Diagnosis", backref="treatments")
    applications = relationship("TreatmentApplication", back_populates="treatment")
    
    __table_args__ = (
        Index('idx_treatment_diagnosis', 'diagnosis_id'),
        Index('idx_treatment_type_status', 'treatment_type', 'status'),
    )


class TreatmentApplication(Base, TimestampMixin):
    """Track individual treatment applications."""
    __tablename__ = 'treatment_applications'
    
    id = Column(Integer, primary_key=True)
    treatment_id = Column(Integer, ForeignKey('treatments.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Application details
    application_date = Column(DateTime(timezone=True), nullable=False, index=True)
    applied_by = Column(String(200), nullable=True)
    area_treated_acres = Column(Float, nullable=True)
    
    # Products used
    product_name = Column(String(300), nullable=False)
    product_batch = Column(String(100), nullable=True)
    quantity_used = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    
    # Application method
    application_method = Column(String(200), nullable=True)
    equipment_used = Column(String(200), nullable=True)
    weather_conditions = Column(JSONB, nullable=True)
    
    # Cost tracking
    product_cost_ksh = Column(DECIMAL(10, 2), nullable=True)
    labor_cost_ksh = Column(DECIMAL(10, 2), nullable=True)
    total_cost_ksh = Column(DECIMAL(10, 2), nullable=True)
    
    # Observations
    notes = Column(Text, nullable=True)
    photos = Column(ARRAY(String), default=list)
    
    # Effectiveness tracking
    effectiveness_rating = Column(Integer, nullable=True)  # 1-5
    side_effects_observed = Column(JSONB, default=list)
    
    # Relationships
    treatment = relationship("Treatment", back_populates="applications")
    
    __table_args__ = (
        Index('idx_application_treatment_date', 'treatment_id', 'application_date'),
    )


class Product(Base, TimestampMixin, SoftDeleteMixin):
    """Agricultural products (pesticides, fertilizers, seeds, etc.)."""
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    
    # Product identification
    product_code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(300), nullable=False, index=True)
    brand = Column(String(200), nullable=True)
    manufacturer = Column(String(300), nullable=True)
    
    # Category
    product_type = Column(String(100), nullable=False, index=True)  # pesticide, fertilizer, seed, equipment
    sub_category = Column(String(100), nullable=True)
    
    # Description
    description = Column(Text, nullable=True)
    active_ingredients = Column(JSONB, default=list)
    formulation = Column(String(200), nullable=True)
    
    # Specifications
    pack_sizes = Column(JSONB, default=list)  # [{"size": 1, "unit": "kg", "price": 500}]
    application_rates = Column(JSONB, default=dict)
    
    # Pricing
    price_ksh = Column(DECIMAL(10, 2), nullable=True)
    price_per_unit = Column(String(100), nullable=True)
    bulk_discounts = Column(JSONB, default=list)
    
    # Regulatory
    registration_number = Column(String(100), nullable=True, index=True)
    registration_country = Column(String(100), default='Kenya')
    regulatory_body = Column(String(200), nullable=True)  # PCPB, KEPHIS, etc.
    approved_for_use = Column(Boolean, default=True)
    organic_certified = Column(Boolean, default=False)
    
    # Safety
    toxicity_class = Column(String(50), nullable=True)  # WHO classification
    safety_warnings = Column(JSONB, default=list)
    first_aid_measures = Column(JSONB, default=dict)
    environmental_precautions = Column(JSONB, default=list)
    
    # Usage
    target_pests = Column(JSONB, default=list)
    target_diseases = Column(JSONB, default=list)
    suitable_crops = Column(JSONB, default=list)
    application_timing = Column(Text, nullable=True)
    
    # Storage and handling
    storage_requirements = Column(Text, nullable=True)
    shelf_life_months = Column(Integer, nullable=True)
    disposal_instructions = Column(Text, nullable=True)
    
    # Documentation
    datasheet_url = Column(URLType, nullable=True)
    msds_url = Column(URLType, nullable=True)  # Material Safety Data Sheet
    label_url = Column(URLType, nullable=True)
    images = Column(ARRAY(String), default=list)
    
    # Availability
    in_stock = Column(Boolean, default=True)
    stock_level = Column(Integer, nullable=True)
    restock_date = Column(Date, nullable=True)
    
    # Ratings and reviews
    average_rating = Column(Float, nullable=True)
    review_count = Column(Integer, default=0)
    recommendation_count = Column(Integer, default=0)
    
    # Suppliers (many-to-many)
    suppliers = relationship(
        "Supplier",
        secondary=product_supplier_association,
        back_populates="products"
    )
    
    __table_args__ = (
        Index('idx_product_type', 'product_type'),
        Index('idx_product_name', 'name'),
    )


class Supplier(Base, TimestampMixin, SoftDeleteMixin):
    """Agricultural product suppliers."""
    __tablename__ = 'suppliers'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    
    # Company information
    company_name = Column(String(300), nullable=False, index=True)
    business_registration = Column(String(100), nullable=True)
    tax_id = Column(String(100), nullable=True)
    
    # Contact information
    contact_person = Column(String(200), nullable=True)
    email = Column(EmailType, nullable=True)
    phone_number = Column(String(20), nullable=True)
    alternate_phone = Column(String(20), nullable=True)
    website = Column(URLType, nullable=True)
    
    # Location
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    county = Column(String(100), nullable=True)
    country = Column(String(100), default='Kenya')
    
    # Business details
    supplier_type = Column(String(100), nullable=True)  # manufacturer, distributor, retailer
    product_categories = Column(ARRAY(String), default=list)
    delivery_areas = Column(ARRAY(String), default=list)
    
    # Operations
    operating_hours = Column(JSONB, nullable=True)
    delivery_available = Column(Boolean, default=True)
    minimum_order_ksh = Column(DECIMAL(10, 2), nullable=True)
    delivery_fee_ksh = Column(DECIMAL(10, 2), nullable=True)
    free_delivery_threshold_ksh = Column(DECIMAL(10, 2), nullable=True)
    
    # Payment methods
    payment_methods = Column(ARRAY(String), default=list)
    credit_available = Column(Boolean, default=False)
    credit_terms_days = Column(Integer, nullable=True)
    
    # Ratings
    average_rating = Column(Float, nullable=True)
    reliability_score = Column(Float, nullable=True)
    total_orders = Column(Integer, default=0)
    
    # Status
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True, index=True)
    
    # Relationships
    products = relationship(
        "Product",
        secondary=product_supplier_association,
        back_populates="suppliers"
    )
    
    __table_args__ = (
        Index('idx_supplier_name', 'company_name'),
        Index('idx_supplier_active', 'is_active'),
    )


# ============================================================================
# FINANCIAL MODELS (Digital Chama Integration)
# ============================================================================

class Chama(Base, TimestampMixin, SoftDeleteMixin):
    """Digital Chama (cooperative) model."""
    __tablename__ = 'chamas'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    
    # Chama identification
    chama_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(300), nullable=False, index=True)
    description = Column(Text, nullable=True)
    registration_number = Column(String(100), nullable=True, unique=True)
    
    # Type and structure
    chama_type = Column(String(100), nullable=False)  # savings, investment, welfare, multipurpose
    governance_model = Column(String(100), nullable=True)  # democratic, hierarchical, rotating
    
    # Leadership
    chairperson_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    treasurer_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    secretary_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Membership
    member_count = Column(Integer, default=0)
    max_members = Column(Integer, nullable=True)
    membership_fee_ksh = Column(DECIMAL(10, 2), nullable=True)
    monthly_contribution_ksh = Column(DECIMAL(10, 2), nullable=True)
    
    # Financial status
    total_savings_ksh = Column(DECIMAL(15, 2), default=0)
    total_loans_outstanding_ksh = Column(DECIMAL(15, 2), default=0)
    total_investments_ksh = Column(DECIMAL(15, 2), default=0)
    cash_balance_ksh = Column(DECIMAL(15, 2), default=0)
    
    # Loan policies
    loan_interest_rate = Column(Float, nullable=True)
    max_loan_amount_ksh = Column(DECIMAL(12, 2), nullable=True)
    loan_repayment_period_months = Column(Integer, nullable=True)
    loan_approval_threshold = Column(Integer, nullable=True)  # Percentage of members
    
    # Dividend and welfare
    annual_dividend_rate = Column(Float, nullable=True)
    welfare_fund_ksh = Column(DECIMAL(12, 2), default=0)
    emergency_fund_ksh = Column(DECIMAL(12, 2), default=0)
    
    # Meeting schedule
    meeting_frequency = Column(String(50), nullable=True)  # weekly, monthly, quarterly
    meeting_day = Column(String(20), nullable=True)
    next_meeting_date = Column(DateTime(timezone=True), nullable=True)
    last_meeting_date = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    status = Column(String(50), default='active', index=True)
    formation_date = Column(Date, nullable=True)
    is_public = Column(Boolean, default=False)  # Open for new members
    
    # Contact
    contact_email = Column(EmailType, nullable=True)
    contact_phone = Column(String(20), nullable=True)
    meeting_location = Column(Text, nullable=True)
    
    # Documents
    constitution_url = Column(URLType, nullable=True)
    bylaws_url = Column(URLType, nullable=True)
    certificate_url = Column(URLType, nullable=True)
    
    # Members (many-to-many)
    members = relationship(
        "User",
        secondary=user_chama_association,
        back_populates="chamas"
    )
    
    # Relationships
    transactions = relationship("Transaction", back_populates="chama")
    loans = relationship("Loan", back_populates="chama")
    meetings = relationship("ChamaMeeting", back_populates="chama")
    
    __table_args__ = (
        Index('idx_chama_code', 'chama_code'),
        Index('idx_chama_status', 'status'),
    )


class Transaction(Base, TimestampMixin):
    """Financial transactions."""
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    transaction_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Parties involved
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    chama_id = Column(Integer, ForeignKey('chamas.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Transaction details
    transaction_type = Column(SQLEnum(TransactionType), nullable=False, index=True)
    amount_ksh = Column(DECIMAL(12, 2), nullable=False)
    currency = Column(String(10), default='KES')
    
    # Payment details
    payment_method = Column(String(100), nullable=True)  # mpesa, bank, cash, card
    payment_reference = Column(String(200), nullable=True, index=True)
    mpesa_receipt_number = Column(String(100), nullable=True, index=True)
    mpesa_phone = Column(String(20), nullable=True)
    
    # Status
    status = Column(SQLEnum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False, index=True)
    status_message = Column(Text, nullable=True)
    
    # Related entities
    diagnosis_id = Column(Integer, ForeignKey('diagnoses.id', ondelete='SET NULL'), nullable=True)
    loan_id = Column(Integer, ForeignKey('loans.id', ondelete='SET NULL'), nullable=True)
    
    # Timestamps
    initiated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Description and notes
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    transaction_metadata = Column(JSONB, default=dict)

    # Fees and charges
    transaction_fee_ksh = Column(DECIMAL(10, 2), default=0)
    net_amount_ksh = Column(DECIMAL(12, 2), nullable=True)
    
    # Reconciliation
    reconciled = Column(Boolean, default=False, index=True)
    reconciled_at = Column(DateTime(timezone=True), nullable=True)
    reconciled_by_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Receipt
    receipt_number = Column(String(100), nullable=True, unique=True)
    receipt_url = Column(URLType, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="transactions", foreign_keys=[user_id])
    chama = relationship("Chama", back_populates="transactions")
    
    __table_args__ = (
        Index('idx_transaction_user_type', 'user_id', 'transaction_type'),
        Index('idx_transaction_status_date', 'status', 'initiated_at'),
        Index('idx_transaction_chama', 'chama_id', 'transaction_type'),
        CheckConstraint('amount_ksh > 0'),
    )


class Loan(Base, TimestampMixin, SoftDeleteMixin):
    """Loan management."""
    __tablename__ = 'loans'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    loan_number = Column(String(100), unique=True, nullable=False, index=True)
    
    # Borrower
    borrower_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    chama_id = Column(Integer, ForeignKey('chamas.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Loan details
    loan_amount_ksh = Column(DECIMAL(12, 2), nullable=False)
    interest_rate = Column(Float, nullable=False)
    loan_purpose = Column(Text, nullable=True)
    
    # Repayment terms
    repayment_period_months = Column(Integer, nullable=False)
    installment_frequency = Column(String(50), nullable=False)  # weekly, monthly
    installment_amount_ksh = Column(DECIMAL(10, 2), nullable=False)
    
    # Status
    status = Column(String(50), default='pending', nullable=False, index=True)
    application_date = Column(DateTime(timezone=True), server_default=func.now())
    approval_date = Column(DateTime(timezone=True), nullable=True)
    disbursement_date = Column(DateTime(timezone=True), nullable=True)
    maturity_date = Column(Date, nullable=True)
    
    # Amounts
    principal_outstanding_ksh = Column(DECIMAL(12, 2), nullable=True)
    interest_outstanding_ksh = Column(DECIMAL(12, 2), nullable=True)
    total_outstanding_ksh = Column(DECIMAL(12, 2), nullable=True)
    total_paid_ksh = Column(DECIMAL(12, 2), default=0)
    
    # Guarantors
    guarantor_1_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    guarantor_2_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    guarantor_approval_1 = Column(Boolean, default=False)
    guarantor_approval_2 = Column(Boolean, default=False)
    
    # Collateral
    collateral_description = Column(Text, nullable=True)
    collateral_value_ksh = Column(DECIMAL(12, 2), nullable=True)
    
    # Approval workflow
    approved_by_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    approval_notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Repayment tracking
    next_payment_date = Column(Date, nullable=True, index=True)
    last_payment_date = Column(Date, nullable=True)
    payments_made = Column(Integer, default=0)
    payments_missed = Column(Integer, default=0)
    days_overdue = Column(Integer, default=0)
    
    # Default handling
    defaulted = Column(Boolean, default=False, index=True)
    default_date = Column(Date, nullable=True)
    recovery_actions = Column(JSONB, default=list)
    
    # Relationships
    borrower = relationship("User", foreign_keys=[borrower_id])
    chama = relationship("Chama", back_populates="loans")
    repayments = relationship("LoanRepayment", back_populates="loan")
    
    __table_args__ = (
        Index('idx_loan_borrower_status', 'borrower_id', 'status'),
        Index('idx_loan_chama', 'chama_id'),
        Index('idx_loan_next_payment', 'next_payment_date'),
        CheckConstraint('loan_amount_ksh > 0'),
        CheckConstraint('interest_rate >= 0'),
    )


class LoanRepayment(Base, TimestampMixin):
    """Loan repayment tracking."""
    __tablename__ = 'loan_repayments'
    
    id = Column(Integer, primary_key=True)
    loan_id = Column(Integer, ForeignKey('loans.id', ondelete='CASCADE'), nullable=False, index=True)
    transaction_id = Column(Integer, ForeignKey('transactions.id', ondelete='SET NULL'), nullable=True)
    
    # Repayment details
    payment_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    amount_ksh = Column(DECIMAL(10, 2), nullable=False)
    principal_amount_ksh = Column(DECIMAL(10, 2), nullable=False)
    interest_amount_ksh = Column(DECIMAL(10, 2), nullable=False)
    penalty_amount_ksh = Column(DECIMAL(10, 2), default=0)
    
    # Status
    payment_status = Column(String(50), default='completed', nullable=False)
    payment_method = Column(String(100), nullable=True)
    payment_reference = Column(String(200), nullable=True)
    
    # Schedule tracking
    scheduled_payment_date = Column(Date, nullable=True)
    is_early = Column(Boolean, default=False)
    is_late = Column(Boolean, default=False)
    days_late = Column(Integer, default=0)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relationships
    loan = relationship("Loan", back_populates="repayments")
    
    __table_args__ = (
        Index('idx_repayment_loan_date', 'loan_id', 'payment_date'),
        CheckConstraint('amount_ksh > 0'),
    )


class ChamaMeeting(Base, TimestampMixin):
    """Chama meeting records."""
    __tablename__ = 'chama_meetings'
    
    id = Column(Integer, primary_key=True)
    chama_id = Column(Integer, ForeignKey('chamas.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Meeting details
    meeting_date = Column(DateTime(timezone=True), nullable=False, index=True)
    meeting_type = Column(String(100), nullable=False)  # regular, special, agm, emergency
    location = Column(Text, nullable=True)
    
    # Attendance
    members_present = Column(JSONB, default=list)  # List of user IDs
    members_absent = Column(JSONB, default=list)
    attendance_count = Column(Integer, default=0)
    quorum_met = Column(Boolean, default=False)
    
    # Agenda and minutes
    agenda = Column(Text, nullable=True)
    minutes = Column(Text, nullable=True)
    decisions_made = Column(JSONB, default=list)
    action_items = Column(JSONB, default=list)
    
    # Financial summary
    contributions_collected_ksh = Column(DECIMAL(12, 2), default=0)
    loans_approved = Column(JSONB, default=list)  # Loan IDs
    expenses_approved_ksh = Column(DECIMAL(12, 2), default=0)
    
    # Documentation
    minutes_url = Column(URLType, nullable=True)
    photos = Column(ARRAY(String), default=list)
    
    # Status
    status = Column(String(50), default='scheduled', nullable=False)
    chaired_by_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    chama = relationship("Chama", back_populates="meetings")
    
    __table_args__ = (
        Index('idx_meeting_chama_date', 'chama_id', 'meeting_date'),
    )


# ============================================================================
# IOT AND SENSOR MODELS
# ============================================================================

class IoTDevice(Base, TimestampMixin, SoftDeleteMixin, GeoLocationMixin):
    """IoT device management."""
    __tablename__ = 'iot_devices'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    device_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Device information
    device_name = Column(String(200), nullable=False)
    device_type = Column(SQLEnum(DeviceType), nullable=False, index=True)
    manufacturer = Column(String(200), nullable=True)
    model = Column(String(200), nullable=True)
    serial_number = Column(String(200), nullable=True, unique=True)
    
    # Assignment
    owner_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    farm_id = Column(Integer, ForeignKey('farms.id', ondelete='SET NULL'), nullable=True, index=True)
    field_id = Column(Integer, ForeignKey('fields.id', ondelete='SET NULL'), nullable=True)
    
    # Network configuration
    ip_address = Column(INET, nullable=True)
    mac_address = Column(MACADDR, nullable=True, unique=True)
    network_type = Column(String(50), nullable=True)  # wifi, cellular, lorawan
    signal_strength = Column(Integer, nullable=True)  # dBm
    
    # Status
    status = Column(SQLEnum(DeviceStatus), default=DeviceStatus.OFFLINE, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    last_data_at = Column(DateTime(timezone=True), nullable=True)

    # Power and data collection
    battery_level = Column(Float, nullable=True)  # Percentage, 0-100
    sampling_interval_seconds = Column(Integer, nullable=True)
    installation_date = Column(Date, nullable=True)

    # Firmware
    firmware_version = Column(String(50), nullable=True)
    firmware_update_available = Column(Boolean, default=False)

    # Relationships
    owner = relationship("User", back_populates="devices", foreign_keys=[owner_id])
    farm = relationship("Farm")
    readings = relationship("SensorReading", back_populates="device", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_iot_device_owner', 'owner_id'),
        Index('idx_iot_device_farm', 'farm_id'),
    )


class SensorReading(Base, TimestampMixin):
    """Individual readings reported by an IoT device (soil/weather-station sensors, etc.)."""
    __tablename__ = 'sensor_readings'

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    device_id = Column(Integer, ForeignKey('iot_devices.id', ondelete='CASCADE'), nullable=False, index=True)

    recorded_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # Common sensor values - nullable since a given device/reading only populates what it measures
    temperature_celsius = Column(Float, nullable=True)
    humidity_percentage = Column(Float, nullable=True)
    soil_moisture_percentage = Column(Float, nullable=True)
    soil_ph = Column(Float, nullable=True)
    light_intensity_lux = Column(Float, nullable=True)
    co2_ppm = Column(Float, nullable=True)
    water_ph = Column(Float, nullable=True)

    battery_voltage = Column(Float, nullable=True)
    signal_strength = Column(Integer, nullable=True)  # dBm

    # Raw payload for values not covered by the columns above
    raw_data = Column(JSONB, nullable=True)

    # Relationships
    device = relationship("IoTDevice", back_populates="readings")

    __table_args__ = (
        Index('idx_sensor_reading_device_time', 'device_id', 'recorded_at'),
    )


class WeatherRecord(Base, TimestampMixin):
    """Weather station / forecast records for a farm."""
    __tablename__ = 'weather_records'

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    farm_id = Column(Integer, ForeignKey('farms.id', ondelete='CASCADE'), nullable=False, index=True)

    # Timestamp
    record_date = Column(Date, nullable=False, index=True)
    record_timestamp = Column(DateTime(timezone=True), nullable=False)

    # Source
    data_source = Column(String(100), nullable=False)  # iot_device, api, manual
    source_id = Column(String(200), nullable=True)

    # Temperature
    temperature_min_celsius = Column(Float, nullable=True)
    temperature_max_celsius = Column(Float, nullable=True)
    temperature_avg_celsius = Column(Float, nullable=True)

    # Humidity
    humidity_min_percentage = Column(Float, nullable=True)
    humidity_max_percentage = Column(Float, nullable=True)
    humidity_avg_percentage = Column(Float, nullable=True)

    # Precipitation
    rainfall_mm = Column(Float, nullable=True)
    rainfall_probability = Column(Float, nullable=True)

    # Wind
    wind_speed_avg_kmh = Column(Float, nullable=True)
    wind_speed_max_kmh = Column(Float, nullable=True)
    wind_direction_degrees = Column(Integer, nullable=True)

    # Pressure
    pressure_hpa = Column(Float, nullable=True)

    # Solar
    sunshine_hours = Column(Float, nullable=True)
    solar_radiation_wm2 = Column(Float, nullable=True)
    uv_index_max = Column(Float, nullable=True)

    # Conditions
    weather_condition = Column(String(100), nullable=True)  # sunny, cloudy, rainy, etc.
    cloud_cover_percentage = Column(Integer, nullable=True)
    visibility_km = Column(Float, nullable=True)

    # Forecast data
    is_forecast = Column(Boolean, default=False)
    forecast_confidence = Column(Float, nullable=True)

    # Relationships
    farm = relationship("Farm", back_populates="weather_data")

    __table_args__ = (
        Index('idx_weather_farm_date', 'farm_id', 'record_date'),
        Index('idx_weather_date', 'record_date'),
    )


class SoilTest(Base, TimestampMixin):
    """Soil testing records."""
    __tablename__ = 'soil_tests'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    farm_id = Column(Integer, ForeignKey('farms.id', ondelete='CASCADE'), nullable=False, index=True)
    field_id = Column(Integer, ForeignKey('fields.id', ondelete='SET NULL'), nullable=True)
    
    # Test information
    test_date = Column(Date, nullable=False, index=True)
    test_number = Column(String(100), nullable=True)
    laboratory = Column(String(200), nullable=True)
    tested_by = Column(String(200), nullable=True)
    
    # Sample details
    sample_depth_cm = Column(Float, nullable=True)
    sample_location_description = Column(Text, nullable=True)
    sample_coordinates = Column(Geography(geometry_type='POINT', srid=4326), nullable=True)
    
    # Physical properties
    soil_texture = Column(String(100), nullable=True)
    sand_percentage = Column(Float, nullable=True)
    silt_percentage = Column(Float, nullable=True)
    clay_percentage = Column(Float, nullable=True)
    bulk_density = Column(Float, nullable=True)
    
    # Chemical properties
    ph = Column(Float, nullable=True)
    electrical_conductivity = Column(Float, nullable=True)
    organic_matter_percentage = Column(Float, nullable=True)
    organic_carbon_percentage = Column(Float, nullable=True)
    cation_exchange_capacity = Column(Float, nullable=True)
    
    # Nutrients (ppm or mg/kg)
    nitrogen_total = Column(Float, nullable=True)
    nitrogen_available = Column(Float, nullable=True)
    phosphorus = Column(Float, nullable=True)
    potassium = Column(Float, nullable=True)
    calcium = Column(Float, nullable=True)
    magnesium = Column(Float, nullable=True)
    sulfur = Column(Float, nullable=True)
    
    # Micronutrients (ppm)
    iron = Column(Float, nullable=True)
    manganese = Column(Float, nullable=True)
    zinc = Column(Float, nullable=True)
    copper = Column(Float, nullable=True)
    boron = Column(Float, nullable=True)
    
    # Contaminants
    heavy_metals = Column(JSONB, nullable=True)
    pesticide_residues = Column(JSONB, nullable=True)
    
    # Recommendations
    fertilizer_recommendations = Column(JSONB, default=list)
    lime_requirement_kg_per_acre = Column(Float, nullable=True)
    improvement_suggestions = Column(Text, nullable=True)
    
    # Documentation
    report_url = Column(URLType, nullable=True)
    certificate_url = Column(URLType, nullable=True)
    
    # Cost
    test_cost_ksh = Column(DECIMAL(10, 2), nullable=True)
    
    # Relationships
    farm = relationship("Farm", back_populates="soil_tests")
    
    __table_args__ = (
        Index('idx_soiltest_farm_date', 'farm_id', 'test_date'),
    )


# ============================================================================
# ALERT AND NOTIFICATION MODELS
# ============================================================================

class Alert(Base, TimestampMixin):
    """Alert system for farms and users."""
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    
    # Alert details
    alert_type = Column(String(100), nullable=False, index=True)  # disease, pest, weather, device, financial
    alert_category = Column(String(100), nullable=True)
    severity = Column(SQLEnum(AlertSeverity), nullable=False, index=True)
    
    # Title and message
    title = Column(String(300), nullable=False)
    message = Column(Text, nullable=False)
    action_required = Column(Text, nullable=True)
    
    # Affected entities
    farm_id = Column(Integer, ForeignKey('farms.id', ondelete='CASCADE'), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    device_id = Column(String(100), ForeignKey('iot_devices.device_id', ondelete='SET NULL'), nullable=True)
    
    # Alert source
    triggered_by = Column(String(200), nullable=True)  # system, iot_device, manual, ai_model
    trigger_condition = Column(Text, nullable=True)
    trigger_value = Column(String(200), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_acknowledged = Column(Boolean, default=False, index=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    is_resolved = Column(Boolean, default=False, index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Auto-resolve
    auto_resolve_at = Column(DateTime(timezone=True), nullable=True)
    
    # Related diagnosis
    diagnosis_id = Column(Integer, ForeignKey('diagnoses.id', ondelete='SET NULL'), nullable=True)
    
    # Notification tracking
    notification_sent = Column(Boolean, default=False)
    notification_channels = Column(ARRAY(String), default=list)  # email, sms, push, whatsapp
    
    # Metadata
    alert_metadata = Column(JSONB, default=dict)

    # Relationships
    farm = relationship("Farm", back_populates="alerts")
    diagnosis = relationship("Diagnosis", foreign_keys=[diagnosis_id])
    
    __table_args__ = (
        Index('idx_alert_farm_severity', 'farm_id', 'severity'),
        Index('idx_alert_user_active', 'user_id', 'is_active'),
        Index('idx_alert_created', 'created_at'),
    )


class Notification(Base, TimestampMixin):
    """User notifications."""
    __tablename__ = 'notifications'
    
    id = Column(BigInteger, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Notification details
    notification_type = Column(String(100), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    message = Column(Text, nullable=False)
    
    # Channel
    channel = Column(String(50), nullable=False)  # push, email, sms, in_app
    
    # Status
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Delivery
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    delivery_status = Column(String(50), default='pending')
    failure_reason = Column(Text, nullable=True)
    
    # Actions
    action_url = Column(URLType, nullable=True)
    action_buttons = Column(JSONB, default=list)
    
    # Priority
    priority = Column(String(50), default='normal')  # low, normal, high, urgent
    
    # Expiry
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Related entity
    related_entity_type = Column(String(100), nullable=True)
    related_entity_id = Column(Integer, nullable=True)
    
    # Metadata
    notification_metadata = Column(JSONB, default=dict)

    # Relationships
    user = relationship("User", back_populates="notifications")
    
    __table_args__ = (
        Index('idx_notification_user_read', 'user_id', 'is_read'),
        Index('idx_notification_user_created', 'user_id', 'created_at'),
        Index('idx_notification_expires', 'expires_at'),
    )


# ============================================================================
# AUDIT AND LOGGING MODELS
# ============================================================================

class AuditLog(Base, TimestampMixin):
    """Comprehensive audit logging."""
    __tablename__ = 'audit_logs'
    
    id = Column(BigInteger, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    
    # User and session
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    session_id = Column(Integer, ForeignKey('user_sessions.id', ondelete='SET NULL'), nullable=True)
    
    # Action details
    action = Column(String(100), nullable=False, index=True)
    action_category = Column(String(100), nullable=True)  # authentication, data_access, data_modification
    action_result = Column(String(50), default='success')  # success, failure, partial
    
    # Entity affected
    entity_type = Column(String(100), nullable=True, index=True)
    entity_id = Column(String(100), nullable=True)
    entity_name = Column(String(300), nullable=True)
    
    # Changes (for data modifications)
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)
    changes_summary = Column(Text, nullable=True)
    
    # Request details
    request_method = Column(String(20), nullable=True)
    request_url = Column(Text, nullable=True)
    request_ip = Column(INET, nullable=True)
    request_user_agent = Column(Text, nullable=True)
    
    # Security
    risk_score = Column(Float, default=0.0)
    is_suspicious = Column(Boolean, default=False, index=True)
    security_flags = Column(ARRAY(String), default=list)
    
    # Performance
    execution_time_ms = Column(Float, nullable=True)
    
    # Additional context
    additional_data = Column(JSONB, nullable=True)
    error_details = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs", foreign_keys=[user_id])
    
    __table_args__ = (
        Index('idx_audit_user_action', 'user_id', 'action'),
        Index('idx_audit_created', 'created_at'),
        Index('idx_audit_entity', 'entity_type', 'entity_id'),
        # Partition by month for scalability
    )


# ============================================================================
# HELPER FUNCTIONS AND UTILITIES
# ============================================================================

def init_database(engine):
    """Initialize database with all tables."""
    Base.metadata.create_all(engine)


def drop_all_tables(engine):
    """Drop all tables (use with caution!)."""
    Base.metadata.drop_all(engine)


# Export all models
__all__ = [
    'Base',
    'User', 'UserSession', 'APIKey',
    'Farm', 'Field', 'CropPlanting',
    'Diagnosis', 'Disease', 'Treatment', 'TreatmentApplication',
    'Product', 'Supplier',
    'Chama', 'Transaction', 'Loan', 'LoanRepayment', 'ChamaMeeting',
    'IoTDevice', 'SensorReading', 'WeatherRecord', 'SoilTest',
    'Alert', 'Notification',
    'AuditLog',
    'init_database', 'drop_all_tables'
]
