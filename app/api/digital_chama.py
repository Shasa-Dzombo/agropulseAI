"""
Digital Chama API Endpoints
Farmer cooperative management with AI coordination

Endpoints:
1. POST /chamas - Create new Chama
2. POST /chamas/{chama_id}/members - Add member
3. POST /chamas/{chama_id}/chat - Send chat message (AI routing)
4. GET /chamas/{chama_id}/group-buys - List group buys
5. POST /chamas/{chama_id}/group-buys - Create group buy
6. GET /chamas/{chama_id}/harvest-bundles - List harvest bundles
7. POST /sacco/accounts/{member_id}/risk-score - Calculate loan risk
8. POST /sacco/accounts/{member_id}/loan - Apply for loan
9. GET /reputation/{member_id} - Get reputation score
10. POST /marketplace/dispute - File dispute
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from app.database import get_db
from app.models.chama import (
    Chama, ChamaMember, SACCOAccount, SACCOTransaction,
    GroupBuy, HarvestBundle, ChatMessage, ReputationScore,
    DisputeCase, ChamaStatus, MemberRole, TransactionType
)
from app.services.digital_chama_service import digital_chama_ai_service

router = APIRouter(prefix="/digital-chama", tags=["Digital Chama"])


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class CreateChamaRequest(BaseModel):
    name: str = Field(..., description="Chama name")
    county: str = Field(..., description="County location")
    sub_county: Optional[str] = None
    village: Optional[str] = None
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    contribution_amount_ksh: float = Field(500.0, description="Monthly contribution")
    contribution_day_of_month: int = Field(5, description="Contribution due date")


class AddMemberRequest(BaseModel):
    user_id: int = Field(..., description="User ID")
    role: MemberRole = Field(MemberRole.MEMBER, description="Member role")
    farm_size_acres: Optional[float] = None
    primary_crops: Optional[List[str]] = None
    farm_gps_latitude: Optional[float] = None
    farm_gps_longitude: Optional[float] = None


class SendChatMessageRequest(BaseModel):
    member_id: int = Field(..., description="Sender member ID")
    message_text: str = Field(..., description="Message content")
    image_url: Optional[str] = None
    channel: str = Field("general", description="Chat channel")


class CreateGroupBuyRequest(BaseModel):
    product_name: str = Field(..., description="Product name")
    product_category: str = Field(..., description="Category: fertilizer, seed, pesticide")
    product_unit: str = Field("bag", description="Unit of measurement")
    unit_price_ksh: float = Field(..., description="Price per unit")
    target_quantity: int = Field(..., description="Target quantity")
    deadline_days: int = Field(14, description="Days until deadline")
    vendor_name: Optional[str] = None


class ApplyLoanRequest(BaseModel):
    loan_amount_ksh: float = Field(..., description="Requested loan amount")
    loan_purpose: str = Field(..., description="Purpose of loan")
    duration_months: int = Field(6, description="Loan duration")


class FileDisputeRequest(BaseModel):
    buyer_id: int = Field(..., description="Buyer ID")
    chama_id: int = Field(..., description="Chama ID")
    harvest_bundle_id: int = Field(..., description="Harvest bundle ID")
    dispute_type: str = Field(..., description="Type of dispute")
    claimed_issue: str = Field(..., description="Description of issue")
    claimed_loss_ksh: float = Field(0.0, description="Claimed loss amount")
    buyer_submitted_images: Optional[List[str]] = None


# ============================================================================
# CHAMA MANAGEMENT
# ============================================================================

@router.post("/chamas", status_code=status.HTTP_201_CREATED)
async def create_chama(
    request: CreateChamaRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create new farmer cooperative (Chama)
    """
    chama = Chama(
        name=request.name,
        county=request.county,
        sub_county=request.sub_county,
        village=request.village,
        gps_latitude=request.gps_latitude,
        gps_longitude=request.gps_longitude,
        contribution_amount_ksh=request.contribution_amount_ksh,
        contribution_day_of_month=request.contribution_day_of_month,
        status=ChamaStatus.FORMING,
        founded_date=datetime.utcnow()
    )
    db.add(chama)
    await db.commit()
    await db.refresh(chama)
    
    return {
        "chama_id": chama.id,
        "name": chama.name,
        "status": chama.status.value,
        "message": "✅ Chama created successfully"
    }


@router.post("/chamas/{chama_id}/members", status_code=status.HTTP_201_CREATED)
async def add_member(
    chama_id: int,
    request: AddMemberRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Add member to Chama
    """
    # Check if Chama exists
    result = await db.execute(select(Chama).where(Chama.id == chama_id))
    chama = result.scalar_one_or_none()
    if not chama:
        raise HTTPException(status_code=404, detail="Chama not found")
    
    # Create member
    member = ChamaMember(
        chama_id=chama_id,
        user_id=request.user_id,
        role=request.role,
        farm_size_acres=request.farm_size_acres,
        primary_crops=request.primary_crops,
        farm_gps_latitude=request.farm_gps_latitude,
        farm_gps_longitude=request.farm_gps_longitude,
        joined_date=datetime.utcnow()
    )
    db.add(member)
    
    # Create SACCO account
    account_number = f"SACCO-{chama_id:04d}-{request.user_id:06d}"
    sacco_account = SACCOAccount(
        chama_id=chama_id,
        member_id=member.id,
        account_number=account_number,
        created_at=datetime.utcnow()
    )
    db.add(sacco_account)
    
    # Update Chama member count
    chama.total_members += 1
    
    await db.commit()
    await db.refresh(member)
    
    return {
        "member_id": member.id,
        "chama_id": chama_id,
        "sacco_account_number": account_number,
        "role": request.role.value,
        "message": f"✅ Member added to {chama.name}"
    }


@router.get("/chamas/{chama_id}")
async def get_chama(
    chama_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get Chama details
    """
    result = await db.execute(select(Chama).where(Chama.id == chama_id))
    chama = result.scalar_one_or_none()
    if not chama:
        raise HTTPException(status_code=404, detail="Chama not found")
    
    return {
        "chama_id": chama.id,
        "name": chama.name,
        "status": chama.status.value,
        "county": chama.county,
        "village": chama.village,
        "total_members": chama.total_members,
        "total_sacco_balance_ksh": chama.total_sacco_balance_ksh,
        "reputation_score": chama.reputation_score,
        "verified_by_agropulse": chama.verified_by_agropulse,
        "founded_date": chama.founded_date.isoformat()
    }


# ============================================================================
# CORE IDEA 1: AI CHAT ROUTING
# ============================================================================

@router.post("/chamas/{chama_id}/chat")
async def send_chat_message(
    chama_id: int,
    request: SendChatMessageRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Send message with AI routing
    
    AI Moderator classifies and routes:
    - Pest/Disease → Tag Agri-Officer
    - Fertilizer → RAG Knowledge Base
    - Equipment → Equipment Booking
    - SACCO → Loan System
    """
    result = await digital_chama_ai_service.route_chat_message(
        db=db,
        chama_id=chama_id,
        member_id=request.member_id,
        message_text=request.message_text,
        image_url=request.image_url
    )
    
    return {
        "message_id": result["message_id"],
        "category": result["category"],
        "confidence": result["confidence"],
        "ai_response": result["ai_response"],
        "tagged_officer": result["tagged_officer"],
        "redirected_to": result["redirected_to"]
    }


@router.get("/chamas/{chama_id}/chat")
async def get_chat_messages(
    chama_id: int,
    channel: str = "general",
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent chat messages
    """
    query = select(ChatMessage).where(
        and_(
            ChatMessage.chama_id == chama_id,
            ChatMessage.channel == channel,
            ChatMessage.deleted == False
        )
    ).order_by(ChatMessage.timestamp.desc()).limit(limit)
    
    result = await db.execute(query)
    messages = result.scalars().all()
    
    return {
        "chama_id": chama_id,
        "channel": channel,
        "message_count": len(messages),
        "messages": [
            {
                "message_id": msg.id,
                "member_id": msg.member_id,
                "message_text": msg.message_text,
                "image_url": msg.image_url,
                "ai_category": msg.ai_category.value if msg.ai_category else None,
                "ai_response": msg.ai_response,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in messages
        ]
    }


# ============================================================================
# CORE IDEA 2: GROUP BUYING
# ============================================================================

@router.get("/chamas/{chama_id}/demand-prediction")
async def predict_input_demand(
    chama_id: int,
    product_category: str = "fertilizer",
    db: AsyncSession = Depends(get_db)
):
    """
    Predict demand for agricultural inputs using AI
    """
    prediction = await digital_chama_ai_service.predict_input_demand(
        db=db,
        chama_id=chama_id,
        product_category=product_category
    )
    
    return prediction


@router.post("/chamas/{chama_id}/group-buys")
async def create_group_buy(
    chama_id: int,
    request: CreateGroupBuyRequest,
    member_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Create group buy for bulk purchasing
    """
    group_buy = GroupBuy(
        chama_id=chama_id,
        product_name=request.product_name,
        product_category=request.product_category,
        product_unit=request.product_unit,
        unit_price_ksh=request.unit_price_ksh,
        final_unit_price_ksh=request.unit_price_ksh,
        target_quantity=request.target_quantity,
        deadline=datetime.utcnow() + timedelta(days=request.deadline_days),
        vendor_name=request.vendor_name,
        created_by_member_id=member_id,
        status="open"
    )
    db.add(group_buy)
    await db.commit()
    await db.refresh(group_buy)
    
    return {
        "group_buy_id": group_buy.id,
        "product_name": group_buy.product_name,
        "target_quantity": group_buy.target_quantity,
        "unit_price_ksh": group_buy.unit_price_ksh,
        "deadline": group_buy.deadline.isoformat(),
        "status": group_buy.status,
        "message": "✅ Group Buy created"
    }


@router.get("/chamas/{chama_id}/group-buys")
async def list_group_buys(
    chama_id: int,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List group buys
    """
    query = select(GroupBuy).where(GroupBuy.chama_id == chama_id)
    if status:
        query = query.where(GroupBuy.status == status)
    
    result = await db.execute(query.order_by(GroupBuy.created_at.desc()))
    group_buys = result.scalars().all()
    
    return {
        "chama_id": chama_id,
        "group_buy_count": len(group_buys),
        "group_buys": [
            {
                "group_buy_id": gb.id,
                "product_name": gb.product_name,
                "target_quantity": gb.target_quantity,
                "current_quantity": gb.current_quantity,
                "unit_price_ksh": gb.unit_price_ksh,
                "status": gb.status,
                "deadline": gb.deadline.isoformat() if gb.deadline else None,
                "ai_recommended": gb.ai_recommended
            }
            for gb in group_buys
        ]
    }


# ============================================================================
# CORE IDEA 3: SACCO & LOAN RISK SCORING
# ============================================================================

@router.post("/sacco/members/{member_id}/risk-score")
async def calculate_risk_score(
    member_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate AI-powered loan risk score
    
    Factors:
    - Savings consistency
    - Farm asset value (drone-verified)
    - Yield prediction (AgroPulse AI)
    - Loan repayment history
    """
    risk_analysis = await digital_chama_ai_service.calculate_loan_risk_score(
        db=db,
        member_id=member_id
    )
    
    return risk_analysis


@router.post("/sacco/members/{member_id}/loan")
async def apply_for_loan(
    member_id: int,
    request: ApplyLoanRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Apply for SACCO micro-loan
    """
    # Calculate risk score first
    risk_analysis = await digital_chama_ai_service.calculate_loan_risk_score(
        db=db,
        member_id=member_id
    )
    
    # Check eligibility
    max_loan = risk_analysis["loan_recommendation"]["max_loan_amount_ksh"]
    if request.loan_amount_ksh > max_loan:
        raise HTTPException(
            status_code=400,
            detail=f"Requested amount exceeds maximum ({max_loan} KSh)"
        )
    
    # Get SACCO account
    result = await db.execute(
        select(SACCOAccount).where(SACCOAccount.member_id == member_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="SACCO account not found")
    
    # Check if already has active loan
    if account.active_loan:
        raise HTTPException(status_code=400, detail="Already has active loan")
    
    # Approve loan
    interest_rate = risk_analysis["loan_recommendation"]["interest_rate_percent"]
    loan_due_date = datetime.utcnow() + timedelta(days=request.duration_months * 30)
    
    account.active_loan = True
    account.loan_amount_ksh = request.loan_amount_ksh
    account.loan_balance_ksh = request.loan_amount_ksh * (1 + interest_rate / 100)
    account.loan_disbursed_date = datetime.utcnow()
    account.loan_due_date = loan_due_date
    account.loan_interest_rate_percent = interest_rate
    account.savings_balance_ksh += request.loan_amount_ksh
    
    # Create transaction
    transaction = SACCOTransaction(
        account_id=account.id,
        member_id=member_id,
        transaction_type=TransactionType.LOAN_DISBURSEMENT,
        amount_ksh=request.loan_amount_ksh,
        description=f"Loan approved: {request.loan_purpose}",
        reference_number=f"LOAN-{member_id}-{int(datetime.utcnow().timestamp())}",
        balance_after_ksh=account.savings_balance_ksh,
        timestamp=datetime.utcnow()
    )
    db.add(transaction)
    
    await db.commit()
    
    return {
        "loan_approved": True,
        "loan_amount_ksh": request.loan_amount_ksh,
        "interest_rate_percent": interest_rate,
        "total_repayment_ksh": account.loan_balance_ksh,
        "due_date": loan_due_date.isoformat(),
        "monthly_payment_ksh": account.loan_balance_ksh / request.duration_months,
        "transaction_reference": transaction.reference_number,
        "message": "🎉 Loan approved and disbursed!"
    }


@router.get("/sacco/members/{member_id}/nudges")
async def get_behavioral_nudges(
    member_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get personalized financial coaching nudges
    """
    nudges = await digital_chama_ai_service.send_behavioral_nudge(
        db=db,
        member_id=member_id
    )
    
    return nudges


# ============================================================================
# CORE IDEA 7: REPUTATION LEDGER
# ============================================================================

@router.post("/reputation/{member_id}/calculate")
async def calculate_reputation(
    member_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate verifiable reputation score
    
    Components:
    - Financial: SACCO performance
    - Agronomic: Best practices
    - Quality: Crop grades
    - Commercial: Participation
    """
    reputation = await digital_chama_ai_service.calculate_reputation_score(
        db=db,
        member_id=member_id
    )
    
    return reputation


@router.get("/reputation/{member_id}")
async def get_reputation(
    member_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get current reputation score
    """
    result = await db.execute(
        select(ReputationScore).where(
            ReputationScore.member_id == member_id
        ).order_by(ReputationScore.calculated_at.desc()).limit(1)
    )
    score = result.scalar_one_or_none()
    
    if not score:
        raise HTTPException(status_code=404, detail="Reputation score not found")
    
    return {
        "member_id": member_id,
        "total_score": score.total_score,
        "certification_level": score.certification_level,
        "component_scores": {
            "financial": score.financial_score,
            "agronomic": score.agronomic_score,
            "quality": score.quality_score,
            "commercial": score.commercial_score
        },
        "blockchain_hash": score.blockchain_reputation_hash,
        "calculated_at": score.calculated_at.isoformat()
    }


# ============================================================================
# HARVEST BUNDLES & MARKETPLACE
# ============================================================================

@router.get("/chamas/{chama_id}/harvest-bundles")
async def list_harvest_bundles(
    chama_id: int,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List harvest bundles (Harvest Futures Marketplace)
    """
    query = select(HarvestBundle).where(HarvestBundle.chama_id == chama_id)
    if status:
        query = query.where(HarvestBundle.status == status)
    
    result = await db.execute(query.order_by(HarvestBundle.created_at.desc()))
    bundles = result.scalars().all()
    
    return {
        "chama_id": chama_id,
        "bundle_count": len(bundles),
        "harvest_bundles": [
            {
                "bundle_id": hb.id,
                "crop_type": hb.crop_type,
                "total_quantity_kg": hb.total_quantity_kg,
                "grade_a_quantity_kg": hb.grade_a_quantity_kg,
                "asking_price_ksh_per_kg": hb.asking_price_ksh_per_kg,
                "status": hb.status,
                "data_source": hb.data_source,
                "confidence_score": hb.confidence_score,
                "predicted_harvest_date": hb.predicted_harvest_date.isoformat() if hb.predicted_harvest_date else None,
                "blockchain_verified": hb.blockchain_verified
            }
            for hb in bundles
        ]
    }


# ============================================================================
# DISPUTE RESOLUTION
# ============================================================================

@router.post("/marketplace/disputes")
async def file_dispute(
    request: FileDisputeRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    File marketplace dispute
    
    AI adjudication (Tier 1) → Human arbitration (Tier 2)
    """
    dispute = DisputeCase(
        buyer_id=request.buyer_id,
        chama_id=request.chama_id,
        harvest_bundle_id=request.harvest_bundle_id,
        dispute_type=request.dispute_type,
        claimed_issue=request.claimed_issue,
        claimed_loss_ksh=request.claimed_loss_ksh,
        buyer_submitted_images=request.buyer_submitted_images,
        status=DisputeStatus.PENDING,
        filed_at=datetime.utcnow()
    )
    db.add(dispute)
    await db.commit()
    await db.refresh(dispute)
    
    return {
        "dispute_id": dispute.id,
        "status": dispute.status.value,
        "message": "⚖️ Dispute filed. AI review in progress..."
    }


@router.get("/marketplace/disputes/{dispute_id}")
async def get_dispute(
    dispute_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get dispute details
    """
    result = await db.execute(select(DisputeCase).where(DisputeCase.id == dispute_id))
    dispute = result.scalar_one_or_none()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    
    return {
        "dispute_id": dispute.id,
        "buyer_id": dispute.buyer_id,
        "chama_id": dispute.chama_id,
        "dispute_type": dispute.dispute_type,
        "claimed_issue": dispute.claimed_issue,
        "claimed_loss_ksh": dispute.claimed_loss_ksh,
        "status": dispute.status.value,
        "ai_decision": dispute.ai_decision,
        "ai_confidence": dispute.ai_confidence,
        "resolved": dispute.resolved,
        "filed_at": dispute.filed_at.isoformat(),
        "resolved_at": dispute.resolved_at.isoformat() if dispute.resolved_at else None
    }


from datetime import timedelta
