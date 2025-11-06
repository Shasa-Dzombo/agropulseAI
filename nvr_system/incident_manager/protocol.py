# Data models for Incident Management

from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, List
from datetime import datetime

class IncidentStatus(str, Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    FALSE_ALARM = "FALSE_ALARM"

class IncidentSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class Incident(BaseModel):
    incident_id: str
    status: IncidentStatus
    severity: IncidentSeverity
    created_at: str
    resolved_at: Optional[str] = None
    title: str
    assigned_to: Optional[str] = None

class IncidentLogEntry(BaseModel):
    log_id: Optional[int] = None
    incident_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    user: str
    action: str
    notes: Optional[str] = None
