from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class OptimizationStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ScoutingPlan(Base):
    __tablename__ = "scouting_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("app_users.id"), nullable=False)
    farm_id = Column(Integer, ForeignKey("app_farms.id"), nullable=False)

    status = Column(SQLEnum(OptimizationStatus), default=OptimizationStatus.PENDING)
    
    # Input parameters
    available_budget_ksh = Column(Float, nullable=False)
    available_time_hours = Column(Float, nullable=False)
    alert_ids = Column(JSON, nullable=False)  # Array of alert IDs to consider
    
    # Quantum optimization results
    optimal_path = Column(JSON, nullable=True)  # Ordered list of zones/alerts
    estimated_cost = Column(Float, nullable=True)
    estimated_time_hours = Column(Float, nullable=True)
    risk_coverage_percentage = Column(Float, nullable=True)
    
    # Recommendations
    priority_alerts = Column(JSON, nullable=True)
    skipped_alerts = Column(JSON, nullable=True)
    reasoning = Column(Text, nullable=True)
    
    # Processing details
    quantum_backend = Column(String(100), nullable=True)  # aws_braket, azure_quantum
    processing_time_seconds = Column(Float, nullable=True)
    algorithm_used = Column(String(100), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User")
    farm = relationship("Farm")


class RegionalAlert(Base):
    __tablename__ = "regional_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    
    region = Column(String(255), nullable=False)
    disease_type = Column(String(255), nullable=False)
    severity = Column(String(50), nullable=False)
    
    affected_farms_count = Column(Integer, default=0)
    total_cases = Column(Integer, default=0)
    
    description = Column(Text, nullable=True)
    recommended_actions = Column(JSON, nullable=True)
    
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
