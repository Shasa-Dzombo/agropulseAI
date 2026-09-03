from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class ChamaCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=300)
    description: Optional[str] = None
    chama_type: str = Field("savings", pattern="^(savings|investment|welfare|multipurpose)$")
    monthly_contribution_ksh: Optional[Decimal] = Field(None, gt=0)
    is_public: bool = True
    # Reference only - a paybill members pay into manually via their own
    # M-Pesa app. Not verified or reconciled by this app; see the column's
    # comment in app/models/database.py.
    mpesa_paybill_number: Optional[str] = Field(None, max_length=20)


class ChamaResponse(BaseModel):
    id: int
    chama_code: str
    name: str
    description: Optional[str] = None
    chama_type: str
    member_count: int
    monthly_contribution_ksh: Optional[Decimal] = None
    total_savings_ksh: Decimal
    status: str
    is_public: bool
    is_member: bool = False
    # True when the caller has an unapproved join request on this chama -
    # mutually exclusive with is_member (a request stops being "pending" the
    # moment it's approved and becomes real membership).
    is_pending: bool = False
    # Chairperson/treasurer/secretary - can see and act on join requests.
    is_leader: bool = False
    mpesa_paybill_number: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChamaMemberResponse(BaseModel):
    user_id: int
    full_name: Optional[str] = None
    username: Optional[str] = None
    role: str
    joined_at: Optional[datetime] = None


class ContributionCreateRequest(BaseModel):
    amount_ksh: Decimal = Field(gt=0)
    payment_method: Optional[str] = Field(None, pattern="^(mpesa|bank|cash|card)$")
    notes: Optional[str] = None


class ContributionResponse(BaseModel):
    id: int
    transaction_id: str
    user_id: int
    amount_ksh: Decimal
    payment_method: Optional[str] = None
    status: str
    notes: Optional[str] = None
    initiated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChamaListResponse(BaseModel):
    items: List[ChamaResponse]
