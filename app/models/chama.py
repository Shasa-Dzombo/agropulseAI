"""
Digital Chama Database Models
Farmer cooperative management with AI-powered coordination

Models:
1. Chama - Cooperative group
2. ChamaMember - Individual farmer membership
3. SACCOAccount - Digital savings & loan account
4. SACCOTransaction - Financial ledger
5. GroupBuy - Bulk input purchases
6. HarvestBundle - Aggregated produce sales
7. EquipmentBooking - Shared asset scheduling
8. ChatMessage - Community forum
9. ReputationScore - Trust ledger
10. DisputeCase - Marketplace dispute resolution
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum

from app.database import Base


class ChamaStatus(str, Enum):
    FORMING = "forming"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISSOLVED = "dissolved"


class MemberRole(str, Enum):
    LEADER = "leader"
    TREASURER = "treasurer"
    SECRETARY = "secretary"
    AGRI_OFFICER = "agri_officer"
    MEMBER = "member"


class TransactionType(str, Enum):
    CONTRIBUTION = "contribution"
    LOAN_DISBURSEMENT = "loan_disbursement"
    LOAN_REPAYMENT = "loan_repayment"
    FINE = "fine"
    DIVIDEND = "dividend"
    GROUP_BUY_PAYMENT = "group_buy_payment"
    HARVEST_PAYOUT = "harvest_payout"


class ChatMessageCategory(str, Enum):
    PEST_DISEASE = "pest_disease"
    FERTILIZER_QUERY = "fertilizer_query"
    HARVEST_TIMING = "harvest_timing"
    EQUIPMENT_BOOKING = "equipment_booking"
    SACCO_LOAN = "sacco_loan"
    GENERAL_CHAT = "general_chat"


class DisputeStatus(str, Enum):
    PENDING = "pending"
    AI_REVIEWING = "ai_reviewing"
    AI_RESOLVED = "ai_resolved"
    ESCALATED = "escalated"
    ARBITRATION_VOTING = "arbitration_voting"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Chama(Base):
    """
    Farmer Cooperative Group
    """
    __tablename__ = "chamas"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    registration_number = Column(String(100), unique=True, nullable=True)
    county = Column(String(100), nullable=False)
    sub_county = Column(String(100), nullable=True)
    village = Column(String(100), nullable=True)
    
    # GPS location (collection point)
    gps_latitude = Column(Float, nullable=True)
    gps_longitude = Column(Float, nullable=True)
    
    # Status
    status = Column(SQLEnum(ChamaStatus), default=ChamaStatus.FORMING)
    founded_date = Column(DateTime, default=datetime.utcnow)
    
    # Rules and governance
    contribution_amount_ksh = Column(Float, default=500.0)
    contribution_day_of_month = Column(Integer, default=5)
    late_payment_fine_percent = Column(Float, default=10.0)
    loan_interest_rate_percent = Column(Float, default=5.0)
    
    # Reputation & verification
    reputation_score = Column(Float, default=0.0)  # 0-100
    verified_by_agropulse = Column(Boolean, default=False)
    blockchain_identity_hash = Column(String(66), nullable=True)  # On-chain identity
    
    # Statistics
    total_members = Column(Integer, default=0)
    total_sacco_balance_ksh = Column(Float, default=0.0)
    total_harvest_sales_ksh = Column(Float, default=0.0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    members = relationship("ChamaMember", back_populates="chama")
    sacco_accounts = relationship("SACCOAccount", back_populates="chama")
    group_buys = relationship("GroupBuy", back_populates="chama")
    harvest_bundles = relationship("HarvestBundle", back_populates="chama")
    equipment_bookings = relationship("EquipmentBooking", back_populates="chama")
    chat_messages = relationship("ChatMessage", back_populates="chama")


class ChamaMember(Base):
    """
    Individual Farmer Membership in Chama
    """
    __tablename__ = "chama_members"
    
    id = Column(Integer, primary_key=True, index=True)
    chama_id = Column(Integer, ForeignKey("chamas.id"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)  # Links to users table
    
    # Role
    role = Column(SQLEnum(MemberRole), default=MemberRole.MEMBER)
    joined_date = Column(DateTime, default=datetime.utcnow)
    active = Column(Boolean, default=True)
    
    # Farm details
    farm_name = Column(String(200), nullable=True)
    farm_size_acres = Column(Float, nullable=True)
    primary_crops = Column(JSON, nullable=True)  # ["potato", "maize", "beans"]
    farm_gps_latitude = Column(Float, nullable=True)
    farm_gps_longitude = Column(Float, nullable=True)
    
    # Reputation score (individual)
    reputation_score = Column(Float, default=50.0)  # 0-100, starts at 50
    
    # Statistics
    total_contributions_ksh = Column(Float, default=0.0)
    total_loans_taken_ksh = Column(Float, default=0.0)
    total_loans_repaid_ksh = Column(Float, default=0.0)
    total_fines_ksh = Column(Float, default=0.0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    chama = relationship("Chama", back_populates="members")
    sacco_account = relationship("SACCOAccount", back_populates="member", uselist=False)
    transactions = relationship("SACCOTransaction", back_populates="member")
    reputation_scores = relationship("ReputationScore", back_populates="member")


class SACCOAccount(Base):
    """
    Digital Savings & Loan Account (SACCO)
    """
    __tablename__ = "sacco_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    chama_id = Column(Integer, ForeignKey("chamas.id"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("chama_members.id"), nullable=False, unique=True, index=True)
    
    # Account details
    account_number = Column(String(50), unique=True, nullable=False)
    
    # Balances
    savings_balance_ksh = Column(Float, default=0.0)
    loan_balance_ksh = Column(Float, default=0.0)  # Outstanding loan amount
    available_credit_ksh = Column(Float, default=0.0)  # Max borrowable based on risk score
    
    # Risk scoring (AI-calculated)
    risk_score = Column(Float, default=50.0)  # 0-100, higher = lower risk
    savings_consistency_score = Column(Float, default=0.0)  # 0-100
    loan_repayment_score = Column(Float, default=100.0)  # 0-100
    farm_asset_value_ksh = Column(Float, default=0.0)  # Drone-verified
    predicted_annual_income_ksh = Column(Float, default=0.0)  # AgroPulse AI prediction
    
    # Status
    account_status = Column(String(50), default="active")  # active, suspended, closed
    last_contribution_date = Column(DateTime, nullable=True)
    consecutive_contributions = Column(Integer, default=0)
    missed_contributions = Column(Integer, default=0)
    
    # Loan details
    active_loan = Column(Boolean, default=False)
    loan_amount_ksh = Column(Float, default=0.0)
    loan_disbursed_date = Column(DateTime, nullable=True)
    loan_due_date = Column(DateTime, nullable=True)
    loan_interest_rate_percent = Column(Float, default=5.0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    chama = relationship("Chama", back_populates="sacco_accounts")
    member = relationship("ChamaMember", back_populates="sacco_account")
    transactions = relationship("SACCOTransaction", back_populates="account")


class SACCOTransaction(Base):
    """
    Financial Ledger (Immutable Audit Trail)
    """
    __tablename__ = "sacco_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("sacco_accounts.id"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("chama_members.id"), nullable=False, index=True)
    
    # Transaction details
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    amount_ksh = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    reference_number = Column(String(100), unique=True, nullable=False)
    
    # Balances after transaction
    balance_after_ksh = Column(Float, nullable=False)
    
    # Blockchain anchoring (immutable proof)
    transaction_hash = Column(String(66), nullable=True)  # SHA-256
    blockchain_tx_hash = Column(String(66), nullable=True)  # On-chain anchor
    
    # Approval & signatures
    approved_by_member_id = Column(Integer, nullable=True)  # For loans
    digital_signature = Column(Text, nullable=True)
    
    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    account = relationship("SACCOAccount", back_populates="transactions")
    member = relationship("ChamaMember", back_populates="transactions")


class GroupBuy(Base):
    """
    Bulk Input Purchases (Fertilizer, Seeds, etc.)
    """
    __tablename__ = "group_buys"
    
    id = Column(Integer, primary_key=True, index=True)
    chama_id = Column(Integer, ForeignKey("chamas.id"), nullable=False, index=True)
    
    # Product details
    product_name = Column(String(200), nullable=False)
    product_category = Column(String(100), nullable=False)  # fertilizer, seed, pesticide, equipment
    product_unit = Column(String(50), default="bag")  # bag, kg, liter
    
    # Pricing
    unit_price_ksh = Column(Float, nullable=False)
    bulk_discount_percent = Column(Float, default=0.0)
    final_unit_price_ksh = Column(Float, nullable=False)
    
    # Quantity
    target_quantity = Column(Integer, nullable=False)
    current_quantity = Column(Integer, default=0)
    
    # Status
    status = Column(String(50), default="open")  # open, locked, ordered, delivered, cancelled
    deadline = Column(DateTime, nullable=True)
    
    # Vendor
    vendor_name = Column(String(200), nullable=True)
    vendor_contact = Column(String(100), nullable=True)
    vendor_rating = Column(Float, nullable=True)  # 0-5 stars
    
    # Payment escrow
    total_committed_ksh = Column(Float, default=0.0)
    escrow_address = Column(String(200), nullable=True)  # Smart contract address
    funds_released = Column(Boolean, default=False)
    goods_confirmed = Column(Boolean, default=False)
    confirmation_count = Column(Integer, default=0)  # Members who confirmed delivery
    
    # AI optimization
    ai_recommended = Column(Boolean, default=False)
    predicted_demand = Column(Integer, nullable=True)
    
    # Metadata
    created_by_member_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    chama = relationship("Chama", back_populates="group_buys")


class HarvestBundle(Base):
    """
    Aggregated Produce Sales (Harvest Futures Marketplace)
    """
    __tablename__ = "harvest_bundles"
    
    id = Column(Integer, primary_key=True, index=True)
    chama_id = Column(Integer, ForeignKey("chamas.id"), nullable=False, index=True)
    
    # Crop details
    crop_type = Column(String(100), nullable=False, index=True)
    crop_variety = Column(String(100), nullable=True)
    
    # Quantity & quality (from grading belt or drone prediction)
    total_quantity_kg = Column(Float, default=0.0)
    grade_a_quantity_kg = Column(Float, default=0.0)
    grade_b_quantity_kg = Column(Float, default=0.0)
    
    # Source of data
    data_source = Column(String(50), default="predicted")  # predicted (drone), graded (belt), actual
    drone_scan_id = Column(Integer, nullable=True)
    confidence_score = Column(Float, default=0.0)  # 0-1
    
    # Harvest readiness
    predicted_harvest_date = Column(DateTime, nullable=True)
    actual_harvest_date = Column(DateTime, nullable=True)
    
    # Pricing
    asking_price_ksh_per_kg = Column(Float, nullable=True)
    minimum_price_ksh_per_kg = Column(Float, nullable=True)
    market_price_ksh_per_kg = Column(Float, nullable=True)  # AI market intelligence
    
    # Status
    status = Column(String(50), default="forecasted")  # forecasted, listed, reserved, sold, delivered
    listed_date = Column(DateTime, nullable=True)
    
    # Buyer
    buyer_id = Column(Integer, nullable=True)  # Links to buyers table
    buyer_name = Column(String(200), nullable=True)
    sale_price_ksh_per_kg = Column(Float, nullable=True)
    total_revenue_ksh = Column(Float, default=0.0)
    
    # Smart contract escrow
    smart_contract_address = Column(String(200), nullable=True)
    escrow_amount_ksh = Column(Float, default=0.0)
    funds_locked = Column(Boolean, default=False)
    
    # Digital manifest (from grading belt)
    manifest_id = Column(Integer, nullable=True)  # Links to digital_manifests
    manifest_hash = Column(String(66), nullable=True)
    blockchain_verified = Column(Boolean, default=False)
    
    # Quantum optimization
    quantum_matched = Column(Boolean, default=False)
    optimization_score = Column(Float, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    chama = relationship("Chama", back_populates="harvest_bundles")


class EquipmentBooking(Base):
    """
    Shared Asset Scheduling (Tractors, Grading Belt, etc.)
    """
    __tablename__ = "equipment_bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    chama_id = Column(Integer, ForeignKey("chamas.id"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("chama_members.id"), nullable=False, index=True)
    
    # Equipment details
    equipment_type = Column(String(100), nullable=False)  # tractor, grading_belt, planter, sprayer
    equipment_id = Column(String(100), nullable=True)
    
    # Booking details
    booking_date = Column(DateTime, nullable=False, index=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    duration_hours = Column(Float, nullable=False)
    
    # Location
    farm_gps_latitude = Column(Float, nullable=True)
    farm_gps_longitude = Column(Float, nullable=True)
    
    # Status
    status = Column(String(50), default="requested")  # requested, approved, scheduled, in_progress, completed, cancelled
    
    # AI optimization
    ai_scheduled = Column(Boolean, default=False)
    route_optimization_id = Column(String(100), nullable=True)
    estimated_fuel_cost_ksh = Column(Float, nullable=True)
    
    # Costs
    booking_fee_ksh = Column(Float, default=0.0)
    payment_status = Column(String(50), default="pending")  # pending, paid, refunded
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    chama = relationship("Chama", back_populates="equipment_bookings")


class ChatMessage(Base):
    """
    Community Forum Messages
    """
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    chama_id = Column(Integer, ForeignKey("chamas.id"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("chama_members.id"), nullable=False, index=True)
    
    # Message content
    channel = Column(String(100), default="general")  # general, ask_officer, group_buys, harvest_bundles
    message_text = Column(Text, nullable=False)
    image_url = Column(String(500), nullable=True)
    
    # AI classification
    ai_category = Column(SQLEnum(ChatMessageCategory), nullable=True)
    ai_confidence = Column(Float, nullable=True)
    ai_tagged_officer = Column(Boolean, default=False)
    ai_response = Column(Text, nullable=True)  # RAG-generated instant response
    
    # Routing
    redirected_to = Column(String(100), nullable=True)  # group_buy, equipment_booking, sacco_loan
    thread_id = Column(String(100), nullable=True)
    
    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    edited = Column(Boolean, default=False)
    deleted = Column(Boolean, default=False)
    
    # Relationships
    chama = relationship("Chama", back_populates="chat_messages")


class ReputationScore(Base):
    """
    Verifiable Farmer & Chama Reputation Ledger
    """
    __tablename__ = "reputation_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("chama_members.id"), nullable=False, index=True)
    
    # Overall score (0-100)
    total_score = Column(Float, default=50.0)
    
    # Component scores
    financial_score = Column(Float, default=50.0)  # SACCO savings & loan repayment
    agronomic_score = Column(Float, default=50.0)  # Adherence to AgroPulse schedules
    quality_score = Column(Float, default=50.0)  # Average grade from grading belt
    commercial_score = Column(Float, default=50.0)  # Group buy & harvest participation
    
    # Specific metrics
    sacco_repayment_rate_percent = Column(Float, default=100.0)
    consecutive_on_time_payments = Column(Integer, default=0)
    average_crop_grade = Column(String(10), nullable=True)  # A, B, C
    total_group_buys_participated = Column(Integer, default=0)
    total_harvests_delivered = Column(Integer, default=0)
    years_of_membership = Column(Float, default=0.0)
    
    # Certification
    certification_level = Column(String(50), default="Bronze")  # Bronze, Silver, Gold, Platinum, 5-Star
    blockchain_reputation_hash = Column(String(66), nullable=True)  # Immutable proof
    
    # Metadata
    calculated_at = Column(DateTime, default=datetime.utcnow)
    next_calculation_at = Column(DateTime, nullable=True)
    
    # Relationships
    member = relationship("ChamaMember", back_populates="reputation_scores")


class DisputeCase(Base):
    """
    Marketplace Dispute Resolution
    """
    __tablename__ = "dispute_cases"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Parties
    buyer_id = Column(Integer, nullable=False, index=True)
    chama_id = Column(Integer, ForeignKey("chamas.id"), nullable=False, index=True)
    harvest_bundle_id = Column(Integer, ForeignKey("harvest_bundles.id"), nullable=True)
    
    # Dispute details
    dispute_type = Column(String(100), nullable=False)  # quality_mismatch, quantity_shortage, delivery_delay
    claimed_issue = Column(Text, nullable=False)
    claimed_loss_ksh = Column(Float, default=0.0)
    
    # Evidence (immutable)
    smart_contract_address = Column(String(200), nullable=True)
    manifest_hash = Column(String(66), nullable=True)
    grading_belt_images = Column(JSON, nullable=True)  # URLs
    buyer_submitted_images = Column(JSON, nullable=True)  # URLs
    blockchain_evidence_hash = Column(String(66), nullable=True)
    
    # Status
    status = Column(SQLEnum(DisputeStatus), default=DisputeStatus.PENDING)
    
    # AI adjudication (Tier 1)
    ai_reviewed = Column(Boolean, default=False)
    ai_decision = Column(String(100), nullable=True)  # approve_buyer, reject_buyer, escalate
    ai_confidence = Column(Float, nullable=True)
    ai_analysis = Column(JSON, nullable=True)  # Detailed AI reasoning
    
    # Human arbitration (Tier 2)
    escalated = Column(Boolean, default=False)
    arbitration_panel_ids = Column(JSON, nullable=True)  # List of arbitrator member IDs
    arbitration_votes = Column(JSON, nullable=True)  # {"approve": 3, "reject": 2}
    arbitration_decision = Column(String(100), nullable=True)
    
    # Resolution
    resolved = Column(Boolean, default=False)
    resolution_summary = Column(Text, nullable=True)
    payout_buyer_percent = Column(Float, default=0.0)
    payout_chama_percent = Column(Float, default=100.0)
    
    # Metadata
    filed_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships
    harvest_bundle = relationship("HarvestBundle")
