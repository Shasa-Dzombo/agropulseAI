"""
Database models for advanced features:
- Blockchain Digital Health Passport
- Chama Groups and Memberships
- Treatment Options and Efficacy
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
import enum


# ============================================================================
# BLOCKCHAIN: Digital Health Passport Models
# ============================================================================

class CropHealthPassport(Base):
    """
    Immutable blockchain-anchored crop health record
    
    Each passport represents a verified diagnostic event with:
    - Cryptographic hash of complete diagnostic package
    - NFT "Permit" token for farmer access control
    - IPFS link to full diagnostic data
    - Blockchain transaction hash for verification
    """
    __tablename__ = "crop_health_passports"
    
    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    
    # Blockchain identifiers
    passport_hash = Column(String(66), unique=True, nullable=False, index=True)  # 0x + 64 hex chars
    blockchain_tx_hash = Column(String(66), nullable=False, index=True)
    permit_token_id = Column(Integer, nullable=False, unique=True, index=True)
    
    # Decentralized storage
    ipfs_url = Column(String(255), nullable=False)  # ipfs://Qm...
    
    # Diagnostic data (JSON serialized)
    diagnosis_data = Column(JSON, nullable=False)
    capture_metadata = Column(JSON, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    verified_at = Column(DateTime, nullable=True)
    
    # Relationships
    farmer = relationship("User", back_populates="health_passports")
    field = relationship("Field", back_populates="health_passports")
    access_permits = relationship("PassportAccessPermit", back_populates="passport")


class PassportAccessPermit(Base):
    """
    Time-limited access permissions for third parties
    
    Enables farmer to grant read-only access to:
    - Bulk buyers (verify crop health for premium pricing)
    - Banks/SACCOs (de-risk loan applications)
    - Researchers (aggregate anonymized data)
    """
    __tablename__ = "passport_access_permits"
    
    id = Column(Integer, primary_key=True, index=True)
    passport_id = Column(Integer, ForeignKey("crop_health_passports.id"), nullable=False, index=True)
    farmer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    third_party_id = Column(Integer, nullable=False, index=True)
    third_party_type = Column(String(50), nullable=False)  # buyer, bank, researcher
    
    # Access control
    access_level = Column(String(50), default="read_only", nullable=False)
    granted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    
    # Relationships
    passport = relationship("CropHealthPassport", back_populates="access_permits")
    farmer = relationship("User")


# ============================================================================
# CHAMA: Community Intelligence Models
# ============================================================================

class ChamaGroup(Base):
    """
    Chama (farmer cooperative) group for community intelligence
    
    Members share anonymized diagnostic data for:
    - Outbreak prediction
    - Community-wide alerts
    - Collective negotiation power
    - Shared learning
    """
    __tablename__ = "chama_groups"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    region = Column(String(100), nullable=False, index=True)
    
    # Location (approximate center)
    center_latitude = Column(Float, nullable=True)
    center_longitude = Column(Float, nullable=True)
    
    # Group statistics
    member_count = Column(Integer, default=0, nullable=False)
    total_farm_area_ha = Column(Float, default=0.0, nullable=False)
    
    # Settings
    data_sharing_enabled = Column(Boolean, default=True, nullable=False)
    outbreak_alerts_enabled = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    memberships = relationship("ChamaMembership", back_populates="chama")
    outbreak_analyses = relationship("ChamaOutbreakAnalysis", back_populates="chama")


class ChamaMembership(Base):
    """
    Individual farmer membership in Chama group
    """
    __tablename__ = "chama_memberships"
    
    id = Column(Integer, primary_key=True, index=True)
    chama_id = Column(Integer, ForeignKey("chama_groups.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Membership status
    active = Column(Boolean, default=True, nullable=False, index=True)
    role = Column(String(50), default="member", nullable=False)  # member, leader, treasurer
    
    # Data sharing preferences
    share_diagnostic_data = Column(Boolean, default=True, nullable=False)
    share_location_data = Column(Boolean, default=True, nullable=False)
    receive_outbreak_alerts = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    left_at = Column(DateTime, nullable=True)
    
    # Relationships
    chama = relationship("ChamaGroup", back_populates="memberships")
    user = relationship("User", back_populates="chama_memberships")


class ChamaOutbreakAnalysis(Base):
    """
    Periodic community-wide outbreak analysis results
    """
    __tablename__ = "chama_outbreak_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    chama_id = Column(Integer, ForeignKey("chama_groups.id"), nullable=False, index=True)
    
    # Analysis period
    analysis_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    lookback_days = Column(Integer, default=14, nullable=False)
    
    # Results (JSON serialized)
    active_clusters = Column(JSON, nullable=True)
    spread_analysis = Column(JSON, nullable=True)
    outbreak_predictions = Column(JSON, nullable=True)
    at_risk_farmers = Column(JSON, nullable=True)
    
    # Summary statistics
    member_count = Column(Integer, nullable=False)
    diagnosis_count = Column(Integer, nullable=False)
    cluster_count = Column(Integer, default=0, nullable=False)
    alerts_sent = Column(Integer, default=0, nullable=False)
    
    # Intervention urgency
    urgency_level = Column(String(50), nullable=True)  # low, medium, high, critical
    
    # Relationships
    chama = relationship("ChamaGroup", back_populates="outbreak_analyses")


# ============================================================================
# TREATMENT: Intervention Optimization Models
# ============================================================================

class TreatmentOption(Base):
    """
    Localized treatment options database
    
    Includes:
    - Chemical pesticides
    - Organic solutions
    - Biological controls
    - Cultural practices
    """
    __tablename__ = "treatment_options"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Treatment identification
    name = Column(String(255), nullable=False, index=True)
    active_ingredient = Column(String(255), nullable=True)
    treatment_type = Column(String(50), nullable=False, index=True)  # chemical, organic, biological, cultural
    
    # Target pests/diseases (JSON array)
    target_diseases = Column(JSON, nullable=False)
    approved_crops = Column(JSON, nullable=False)
    
    # Cost data
    unit_cost_ksh = Column(Float, nullable=False)
    unit_type = Column(String(50), nullable=False)  # liter, kilogram, etc.
    application_rate_per_ha = Column(Float, nullable=False)
    application_cost_ksh_per_ha = Column(Float, default=300, nullable=False)
    
    # Efficacy data (JSON by severity level)
    efficacy_data = Column(JSON, nullable=False)
    
    # Application details
    time_to_effect_days = Column(Integer, nullable=False)
    reapplication_needed = Column(Boolean, default=False, nullable=False)
    reapplication_days = Column(Integer, nullable=True)
    
    # Safety and availability
    safety_rating = Column(String(50), default="medium", nullable=False)  # low, medium, high
    local_availability = Column(String(50), default="common", nullable=False)
    supplier = Column(String(255), nullable=True)
    
    # Certifications
    organic_certified = Column(Boolean, default=False, nullable=False)
    export_safe = Column(Boolean, default=True, nullable=False)
    
    # Region-specific
    region = Column(String(100), nullable=False, index=True, default="kenya")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    efficacy_records = relationship("TreatmentEfficacy", back_populates="treatment")


class TreatmentEfficacy(Base):
    """
    Real-world treatment efficacy data from farmer reports
    
    Enables continuous improvement of recommendations based on
    actual field results rather than manufacturer claims
    """
    __tablename__ = "treatment_efficacy"
    
    id = Column(Integer, primary_key=True, index=True)
    treatment_id = Column(Integer, ForeignKey("treatment_options.id"), nullable=False, index=True)
    
    # Farmer report
    farmer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False)
    
    # Treatment details
    disease_treated = Column(String(255), nullable=False, index=True)
    crop_type = Column(String(100), nullable=False, index=True)
    severity_before = Column(String(50), nullable=False)
    severity_after = Column(String(50), nullable=False)
    
    # Efficacy metrics
    days_to_effect = Column(Integer, nullable=True)
    estimated_yield_saved_percent = Column(Float, nullable=True)
    farmer_satisfaction_rating = Column(Integer, nullable=True)  # 1-5 stars
    
    # Cost data
    actual_cost_ksh = Column(Float, nullable=True)
    field_area_ha = Column(Float, nullable=True)
    
    # Timestamps
    treatment_applied_at = Column(DateTime, nullable=False)
    evaluated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    treatment = relationship("TreatmentOption", back_populates="efficacy_records")
    farmer = relationship("User")
    field = relationship("Field")


# ============================================================================
# Add relationships to existing User model
# ============================================================================

# These would be added to the existing User model:
# health_passports = relationship("CropHealthPassport", back_populates="farmer")
# chama_memberships = relationship("ChamaMembership", back_populates="user")
