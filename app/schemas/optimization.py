from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


class OptimizationStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ScoutingPlanRequest(BaseModel):
    farm_id: int
    available_budget_ksh: float = Field(..., gt=0)
    available_time_hours: float = Field(..., gt=0, le=24)
    alert_ids: List[int]


class AlertPriority(BaseModel):
    alert_id: int
    zone_name: str
    alert_type: str
    severity: str
    risk_score: float
    estimated_cost_ksh: float
    estimated_time_minutes: float


class ScoutingPlanResponse(BaseModel):
    id: int
    status: OptimizationStatus
    optimal_path: Optional[List[int]] = None
    estimated_cost: Optional[float] = None
    estimated_time_hours: Optional[float] = None
    risk_coverage_percentage: Optional[float] = None
    priority_alerts: Optional[List[AlertPriority]] = None
    skipped_alerts: Optional[List[int]] = None
    reasoning: Optional[str] = None
    quantum_backend: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ChatbotMessage(BaseModel):
    message: str
    farm_id: Optional[int] = None
    context: Optional[Dict[str, Any]] = None


class ChatbotResponse(BaseModel):
    response: str
    suggested_actions: Optional[List[str]] = None
    scouting_plan: Optional[ScoutingPlanResponse] = None
