from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class PaymentMethod(str, Enum):
    MPESA = "mpesa"
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PaymentInitiate(BaseModel):
    amount: float = Field(..., gt=0)
    payment_method: PaymentMethod
    phone_number: str
    description: Optional[str] = "AgroPulse Service Payment"


class PaymentResponse(BaseModel):
    id: int
    amount: float
    currency: str
    payment_method: PaymentMethod
    status: PaymentStatus
    gateway_transaction_id: Optional[str] = None
    mpesa_receipt_number: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PermitStatus(str, Enum):
    PENDING = "pending"
    MINTED = "minted"
    USED = "used"
    EXPIRED = "expired"


class PermitResponse(BaseModel):
    id: int
    permit_token_id: Optional[str] = None
    transaction_hash: Optional[str] = None
    status: PermitStatus
    permit_type: str
    is_used: bool
    expires_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class PaymentCallback(BaseModel):
    """M-Pesa/Flutterwave webhook callback"""
    transaction_id: str
    status: str
    amount: float
    phone_number: Optional[str] = None
    reference: Optional[str] = None
