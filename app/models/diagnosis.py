from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class DiagnosisStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DiseaseCategory(str, enum.Enum):
    FUNGAL = "fungal"
    BACTERIAL = "bacterial"
    VIRAL = "viral"
    PEST = "pest"
    NUTRIENT_DEFICIENCY = "nutrient_deficiency"
    ENVIRONMENTAL = "environmental"
    HEALTHY = "healthy"


class Diagnosis(Base):
    __tablename__ = "diagnoses"
    
    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=True)
    permit_id = Column(Integer, ForeignKey("permits.id"), nullable=False)
    
    status = Column(SQLEnum(DiagnosisStatus), default=DiagnosisStatus.PENDING)
    
    # Input data
    image_urls = Column(JSON, nullable=False)  # Array of image URLs
    metadata = Column(JSON, nullable=True)  # Camera settings, location, etc.
    
    # AI Results
    primary_diagnosis = Column(String(255), nullable=True)
    category = Column(SQLEnum(DiseaseCategory), nullable=True)
    confidence_score = Column(Float, nullable=True)
    
    # Secondary diagnoses (differential diagnosis)
    alternative_diagnoses = Column(JSON, nullable=True)
    
    # Detailed analysis
    affected_area_percentage = Column(Float, nullable=True)
    severity_level = Column(String(50), nullable=True)
    
    # Recommendations
    treatment_recommendations = Column(JSON, nullable=True)
    preventive_measures = Column(JSON, nullable=True)
    estimated_yield_impact = Column(Float, nullable=True)
    
    # Processing info
    ai_model_version = Column(String(50), nullable=True)
    processing_time_seconds = Column(Float, nullable=True)
    
    # Triage (on-device) results
    triage_diagnosis = Column(String(255), nullable=True)
    triage_confidence = Column(Float, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    farmer = relationship("User", back_populates="diagnoses")
    alert = relationship("Alert", back_populates="diagnoses")
    permit = relationship("Permit", back_populates="diagnosis")


class TreatmentProduct(Base):
    __tablename__ = "treatment_products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)  # pesticide, fungicide, fertilizer
    active_ingredient = Column(String(255), nullable=True)
    manufacturer = Column(String(255), nullable=True)
    application_method = Column(Text, nullable=True)
    dosage_instructions = Column(Text, nullable=True)
    safety_precautions = Column(Text, nullable=True)
    estimated_cost_ksh = Column(Float, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
