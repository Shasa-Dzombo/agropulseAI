from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class PermitStatus(str, enum.Enum):
    PENDING = "pending"
    MINTED = "minted"
    USED = "used"
    EXPIRED = "expired"
    REFUNDED = "refunded"


class Permit(Base):
    __tablename__ = "permits"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    
    permit_token_id = Column(String(255), unique=True, nullable=True)  # Blockchain token ID
    transaction_hash = Column(String(255), unique=True, nullable=True)
    contract_address = Column(String(255), nullable=True)
    
    status = Column(SQLEnum(PermitStatus), default=PermitStatus.PENDING)
    permit_type = Column(String(50), default="diagnosis")  # diagnosis, premium_feature
    
    is_used = Column(Boolean, default=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="permits")
    payment = relationship("Payment", back_populates="permit")
    diagnosis = relationship("Diagnosis", back_populates="permit", uselist=False)


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethod(str, enum.Enum):
    MPESA = "mpesa"
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    WALLET = "wallet"


class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="KES")
    
    payment_method = Column(SQLEnum(PaymentMethod), nullable=False)
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING)
    
    # Payment gateway details
    gateway_transaction_id = Column(String(255), unique=True, nullable=True)
    gateway_reference = Column(String(255), nullable=True)
    
    # M-Pesa specific
    mpesa_receipt_number = Column(String(100), nullable=True)
    phone_number = Column(String(20), nullable=True)
    
    # Flutterwave details
    flutterwave_tx_ref = Column(String(255), unique=True, nullable=True)
    flutterwave_transaction_id = Column(String(255), nullable=True)
    
    description = Column(Text, nullable=True)
    payment_metadata = Column(JSON, nullable=True)

    completed_at = Column(DateTime(timezone=True), nullable=True)
    failed_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="payments")
    permit = relationship("Permit", back_populates="payment", uselist=False)
