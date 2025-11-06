"""
🤝 Chamas API

FastAPI endpoints for digital cooperative management (chamas), microfinance, and group operations.

Endpoints:
- GET /chamas - List chamas
- POST /chamas - Create new chama
- GET /chamas/{chama_id} - Get chama details
- PATCH /chamas/{chama_id} - Update chama
- DELETE /chamas/{chama_id} - Delete chama
- POST /chamas/{chama_id}/join - Join chama
- POST /chamas/{chama_id}/leave - Leave chama
- GET /chamas/{chama_id}/members - List members
- POST /chamas/{chama_id}/members/{user_id}/role - Update member role
- POST /chamas/{chama_id}/transactions - Record transaction
- GET /chamas/{chama_id}/transactions - List transactions
- POST /chamas/{chama_id}/loans - Request loan
- GET /chamas/{chama_id}/loans - List loans
- GET /chamas/{chama_id}/loans/{loan_id} - Get loan details
- POST /chamas/{chama_id}/loans/{loan_id}/approve - Approve loan
- POST /chamas/{chama_id}/loans/{loan_id}/reject - Reject loan
- POST /chamas/{chama_id}/loans/{loan_id}/repay - Record repayment
- GET /chamas/{chama_id}/financial-summary - Financial dashboard
- POST /chamas/{chama_id}/meetings - Schedule meeting
- GET /chamas/{chama_id}/meetings - List meetings

Author: AgroPulse Engineering Team
"""

from datetime import datetime, timedelta
from typing import Optional, List
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from app.db_config import get_production_db_dependency
from app.api.auth import get_current_user


router = APIRouter(prefix="/chamas", tags=["Chamas"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ChamaCreateRequest(BaseModel):
    """Create chama request."""
    name: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    county: str = Field(..., max_length=100)
    sub_county: Optional[str] = None
    chama_type: str = Field(..., pattern="^(savings|investment|farming|mixed)$")
    minimum_contribution: Decimal = Field(..., gt=0)
    contribution_frequency: str = Field(..., pattern="^(weekly|monthly|quarterly)$")
    max_members: int = Field(50, ge=5, le=500)
    registration_fee: Decimal = Field(0, ge=0)
    meeting_frequency: Optional[str] = None


class ChamaUpdateRequest(BaseModel):
    """Update chama request."""
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    minimum_contribution: Optional[Decimal] = Field(None, gt=0)
    contribution_frequency: Optional[str] = None
    max_members: Optional[int] = Field(None, ge=5, le=500)
    registration_fee: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ChamaListResponse(BaseModel):
    """Chama list response."""
    id: int
    uuid: str
    name: str
    county: str
    chama_type: str
    member_count: int
    total_savings: Decimal
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChamaDetailResponse(BaseModel):
    """Detailed chama response."""
    id: int
    uuid: str
    founder_id: int
    name: str
    description: Optional[str]
    chama_code: Optional[str]
    
    # Location
    county: str
    sub_county: Optional[str]
    
    # Type and rules
    chama_type: str
    minimum_contribution: Decimal
    contribution_frequency: str
    max_members: int
    registration_fee: Decimal
    
    # Stats
    member_count: int
    total_savings: Decimal
    total_loans_disbursed: Decimal
    total_loans_repaid: Decimal
    
    # Status
    is_active: bool
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MemberResponse(BaseModel):
    """Chama member response."""
    id: int
    user_id: int
    username: str
    full_name: str
    role: str
    total_contributions: Decimal
    total_borrowed: Decimal
    joined_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True


class TransactionCreateRequest(BaseModel):
    """Create transaction request."""
    transaction_type: str = Field(..., pattern="^(contribution|withdrawal|loan_disbursement|loan_repayment|fee|penalty|dividend)$")
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = None
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None


class TransactionResponse(BaseModel):
    """Transaction response."""
    id: int
    uuid: str
    chama_id: int
    user_id: int
    transaction_type: str
    amount: Decimal
    balance_after: Decimal
    description: Optional[str]
    payment_method: Optional[str]
    reference_number: Optional[str]
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class LoanRequestCreate(BaseModel):
    """Create loan request."""
    amount: Decimal = Field(..., gt=0)
    purpose: str = Field(..., min_length=20)
    repayment_period_months: int = Field(..., ge=1, le=24)
    guarantor_ids: List[int] = Field(..., min_items=1, max_items=3)
    collateral_description: Optional[str] = None


class LoanResponse(BaseModel):
    """Loan response."""
    id: int
    uuid: str
    chama_id: int
    borrower_id: int
    amount: Decimal
    interest_rate: Decimal
    repayment_period_months: int
    monthly_repayment: Decimal
    total_repayment: Decimal
    amount_paid: Decimal
    balance: Decimal
    purpose: str
    status: str
    approved_by: Optional[int]
    approved_at: Optional[datetime]
    disbursed_at: Optional[datetime]
    due_date: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class LoanRepaymentRequest(BaseModel):
    """Loan repayment request."""
    amount: Decimal = Field(..., gt=0)
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None


class FinancialSummaryResponse(BaseModel):
    """Financial summary response."""
    chama_id: int
    total_members: int
    active_members: int
    
    # Savings
    total_savings: Decimal
    total_contributions_month: Decimal
    total_withdrawals_month: Decimal
    
    # Loans
    total_loans: int
    active_loans: int
    total_loans_disbursed: Decimal
    total_loans_repaid: Decimal
    outstanding_balance: Decimal
    default_rate: float
    
    # Performance
    average_member_savings: Decimal
    total_dividends_paid: Decimal
    return_on_savings: float


class MeetingCreateRequest(BaseModel):
    """Create meeting request."""
    title: str = Field(..., min_length=5, max_length=200)
    description: Optional[str] = None
    meeting_date: datetime
    location: Optional[str] = None
    agenda: Optional[str] = None


class MeetingResponse(BaseModel):
    """Meeting response."""
    id: int
    uuid: str
    chama_id: int
    title: str
    meeting_date: datetime
    location: Optional[str]
    agenda: Optional[str]
    attendance_count: int
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class PaginatedChamasResponse(BaseModel):
    """Paginated chamas response."""
    items: List[ChamaListResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def check_chama_access(current_user: dict, chama_id: int, db: Session):
    """Check if user is a member of the chama."""
    from app.models.database import ChamaMember
    
    if current_user['role'] in ['admin', 'superuser']:
        return True
    
    member = db.query(ChamaMember).filter(
        ChamaMember.chama_id == chama_id,
        ChamaMember.user_id == current_user['id'],
        ChamaMember.is_active == True
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this chama"
        )
    
    return member


def check_chama_admin(current_user: dict, chama_id: int, db: Session):
    """Check if user is admin/leader of the chama."""
    member = check_chama_access(current_user, chama_id, db)
    
    if current_user['role'] in ['admin', 'superuser']:
        return True
    
    if member.role not in ['admin', 'chairperson', 'treasurer']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or leadership role required"
        )
    
    return member


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("", response_model=PaginatedChamasResponse)
async def list_chamas(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    county: Optional[str] = None,
    chama_type: Optional[str] = None,
    active_only: bool = True,
    my_chamas: bool = False,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    List chamas with pagination and filters.
    
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **county**: Filter by county (optional)
    - **chama_type**: Filter by type (optional)
    - **active_only**: Show only active chamas (default: true)
    - **my_chamas**: Show only user's chamas (default: false)
    """
    from app.models.database import Chama, ChamaMember
    
    query = db.query(Chama).filter(Chama.is_deleted == False)
    
    if active_only:
        query = query.filter(Chama.is_active == True)
    
    if county:
        query = query.filter(Chama.county == county)
    
    if chama_type:
        query = query.filter(Chama.chama_type == chama_type)
    
    if my_chamas:
        # Get chamas where user is a member
        member_chama_ids = db.query(ChamaMember.chama_id).filter(
            ChamaMember.user_id == current_user['id'],
            ChamaMember.is_active == True
        ).all()
        chama_ids = [cid[0] for cid in member_chama_ids]
        query = query.filter(Chama.id.in_(chama_ids))
    
    total = query.count()
    
    skip = (page - 1) * page_size
    chamas = query.order_by(Chama.created_at.desc()).offset(skip).limit(page_size).all()
    
    return PaginatedChamasResponse(
        items=chamas,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.post("", response_model=ChamaDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_chama(
    request: ChamaCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Create new chama.
    
    The user creating the chama becomes the founder and admin.
    """
    from app.models.database import Chama, ChamaMember
    
    # Create chama
    chama = Chama(
        founder_id=current_user['id'],
        name=request.name,
        description=request.description,
        county=request.county,
        sub_county=request.sub_county,
        chama_type=request.chama_type,
        minimum_contribution=request.minimum_contribution,
        contribution_frequency=request.contribution_frequency,
        max_members=request.max_members,
        registration_fee=request.registration_fee,
        meeting_frequency=request.meeting_frequency,
        member_count=1,
        total_savings=Decimal('0.00')
    )
    
    db.add(chama)
    db.flush()
    
    # Add founder as admin member
    founder_member = ChamaMember(
        chama_id=chama.id,
        user_id=current_user['id'],
        role='admin',
        total_contributions=Decimal('0.00'),
        is_active=True
    )
    
    db.add(founder_member)
    db.commit()
    db.refresh(chama)
    
    return chama


@router.get("/{chama_id}", response_model=ChamaDetailResponse)
async def get_chama(
    chama_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Get chama details by ID.
    """
    from app.models.database import Chama
    
    chama = db.query(Chama).filter(
        Chama.id == chama_id,
        Chama.is_deleted == False
    ).first()
    
    if not chama:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chama not found"
        )
    
    return chama


@router.patch("/{chama_id}", response_model=ChamaDetailResponse)
async def update_chama(
    chama_id: int,
    request: ChamaUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Update chama details.
    
    Requires admin or leadership role.
    """
    from app.models.database import Chama
    
    chama = db.query(Chama).filter(
        Chama.id == chama_id,
        Chama.is_deleted == False
    ).first()
    
    if not chama:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chama not found"
        )
    
    check_chama_admin(current_user, chama_id, db)
    
    # Update fields
    update_data = {k: v for k, v in request.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data to update"
        )
    
    for key, value in update_data.items():
        setattr(chama, key, value)
    
    chama.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(chama)
    
    return chama


@router.delete("/{chama_id}")
async def delete_chama(
    chama_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Delete chama (soft delete).
    
    Requires admin role or founder.
    """
    from app.models.database import Chama
    
    chama = db.query(Chama).filter(
        Chama.id == chama_id,
        Chama.is_deleted == False
    ).first()
    
    if not chama:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chama not found"
        )
    
    if current_user['role'] not in ['admin', 'superuser']:
        if chama.founder_id != current_user['id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only founder or admin can delete chama"
            )
    
    chama.is_deleted = True
    chama.deleted_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Chama deleted successfully"}


@router.post("/{chama_id}/join")
async def join_chama(
    chama_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Join a chama.
    
    User must pay registration fee if applicable.
    """
    from app.models.database import Chama, ChamaMember
    
    chama = db.query(Chama).filter(
        Chama.id == chama_id,
        Chama.is_deleted == False,
        Chama.is_active == True
    ).first()
    
    if not chama:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chama not found"
        )
    
    # Check if already a member
    existing = db.query(ChamaMember).filter(
        ChamaMember.chama_id == chama_id,
        ChamaMember.user_id == current_user['id']
    ).first()
    
    if existing:
        if existing.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are already a member"
            )
        else:
            # Reactivate membership
            existing.is_active = True
            db.commit()
            return {"message": "Membership reactivated"}
    
    # Check max members
    if chama.member_count >= chama.max_members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chama has reached maximum members"
        )
    
    # Create membership
    member = ChamaMember(
        chama_id=chama_id,
        user_id=current_user['id'],
        role='member',
        total_contributions=Decimal('0.00'),
        is_active=True
    )
    
    db.add(member)
    
    # Update member count
    chama.member_count += 1
    
    db.commit()
    
    return {
        "message": "Successfully joined chama",
        "chama_id": chama_id,
        "registration_fee": float(chama.registration_fee)
    }


@router.post("/{chama_id}/leave")
async def leave_chama(
    chama_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Leave a chama.
    
    Founders cannot leave their own chama.
    """
    from app.models.database import Chama, ChamaMember
    
    chama = db.query(Chama).filter(Chama.id == chama_id).first()
    
    if not chama:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chama not found"
        )
    
    if chama.founder_id == current_user['id']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Founders cannot leave their own chama"
        )
    
    member = db.query(ChamaMember).filter(
        ChamaMember.chama_id == chama_id,
        ChamaMember.user_id == current_user['id'],
        ChamaMember.is_active == True
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not a member"
        )
    
    # Deactivate membership
    member.is_active = False
    chama.member_count -= 1
    
    db.commit()
    
    return {"message": "Successfully left chama"}


@router.get("/{chama_id}/members", response_model=List[MemberResponse])
async def list_members(
    chama_id: int,
    active_only: bool = True,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    List chama members.
    
    Requires membership in the chama.
    """
    from app.models.database import ChamaMember, User
    
    check_chama_access(current_user, chama_id, db)
    
    query = db.query(
        ChamaMember.id,
        ChamaMember.user_id,
        User.username,
        User.full_name,
        ChamaMember.role,
        ChamaMember.total_contributions,
        ChamaMember.total_borrowed,
        ChamaMember.joined_at,
        ChamaMember.is_active
    ).join(User, ChamaMember.user_id == User.id).filter(
        ChamaMember.chama_id == chama_id
    )
    
    if active_only:
        query = query.filter(ChamaMember.is_active == True)
    
    members = query.all()
    
    return [
        MemberResponse(
            id=m[0],
            user_id=m[1],
            username=m[2],
            full_name=m[3],
            role=m[4],
            total_contributions=m[5],
            total_borrowed=m[6] or Decimal('0.00'),
            joined_at=m[7],
            is_active=m[8]
        )
        for m in members
    ]


@router.post("/{chama_id}/transactions", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    chama_id: int,
    request: TransactionCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Record a chama transaction.
    
    Types: contribution, withdrawal, loan_disbursement, loan_repayment, fee, penalty, dividend
    """
    from app.models.database import ChamaTransaction, ChamaMember, Chama
    
    member = check_chama_access(current_user, chama_id, db)
    
    # Get current balance
    from sqlalchemy import func
    current_balance = db.query(
        func.coalesce(func.sum(ChamaTransaction.amount), 0)
    ).filter(
        ChamaTransaction.chama_id == chama_id,
        ChamaTransaction.user_id == current_user['id']
    ).scalar()
    
    # Calculate new balance
    if request.transaction_type in ['contribution', 'loan_repayment']:
        new_balance = current_balance + request.amount
    else:
        new_balance = current_balance - request.amount
    
    # Create transaction
    transaction = ChamaTransaction(
        chama_id=chama_id,
        user_id=current_user['id'],
        transaction_type=request.transaction_type,
        amount=request.amount,
        balance_after=new_balance,
        description=request.description,
        payment_method=request.payment_method,
        reference_number=request.reference_number,
        status='completed'
    )
    
    db.add(transaction)
    
    # Update member contributions
    if request.transaction_type == 'contribution':
        member.total_contributions += request.amount
    
    # Update chama totals
    chama = db.query(Chama).filter(Chama.id == chama_id).first()
    if request.transaction_type == 'contribution':
        chama.total_savings += request.amount
    
    db.commit()
    db.refresh(transaction)
    
    return transaction


@router.get("/{chama_id}/transactions", response_model=List[TransactionResponse])
async def list_transactions(
    chama_id: int,
    transaction_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    List chama transactions.
    """
    from app.models.database import ChamaTransaction
    
    check_chama_access(current_user, chama_id, db)
    
    query = db.query(ChamaTransaction).filter(
        ChamaTransaction.chama_id == chama_id
    )
    
    if transaction_type:
        query = query.filter(ChamaTransaction.transaction_type == transaction_type)
    
    transactions = query.order_by(
        ChamaTransaction.created_at.desc()
    ).limit(limit).all()
    
    return transactions


@router.post("/{chama_id}/loans", response_model=LoanResponse, status_code=status.HTTP_201_CREATED)
async def request_loan(
    chama_id: int,
    request: LoanRequestCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Request a loan from the chama.
    
    Requires guarantors (1-3 members).
    """
    from app.models.database import ChamaLoan
    
    check_chama_access(current_user, chama_id, db)
    
    # Calculate loan terms (10% interest rate example)
    interest_rate = Decimal('10.00')
    total_repayment = request.amount * (1 + interest_rate / 100)
    monthly_repayment = total_repayment / request.repayment_period_months
    
    due_date = datetime.utcnow() + timedelta(days=30 * request.repayment_period_months)
    
    # Create loan
    loan = ChamaLoan(
        chama_id=chama_id,
        borrower_id=current_user['id'],
        amount=request.amount,
        interest_rate=interest_rate,
        repayment_period_months=request.repayment_period_months,
        monthly_repayment=monthly_repayment,
        total_repayment=total_repayment,
        amount_paid=Decimal('0.00'),
        balance=total_repayment,
        purpose=request.purpose,
        collateral_description=request.collateral_description,
        guarantor_ids=request.guarantor_ids,
        status='pending',
        due_date=due_date
    )
    
    db.add(loan)
    db.commit()
    db.refresh(loan)
    
    return loan


@router.get("/{chama_id}/loans", response_model=List[LoanResponse])
async def list_loans(
    chama_id: int,
    status: Optional[str] = None,
    my_loans: bool = False,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    List chama loans.
    """
    from app.models.database import ChamaLoan
    
    check_chama_access(current_user, chama_id, db)
    
    query = db.query(ChamaLoan).filter(ChamaLoan.chama_id == chama_id)
    
    if my_loans:
        query = query.filter(ChamaLoan.borrower_id == current_user['id'])
    
    if status:
        query = query.filter(ChamaLoan.status == status)
    
    loans = query.order_by(ChamaLoan.created_at.desc()).all()
    
    return loans


@router.post("/{chama_id}/loans/{loan_id}/approve")
async def approve_loan(
    chama_id: int,
    loan_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Approve a loan request.
    
    Requires admin or treasurer role.
    """
    from app.models.database import ChamaLoan, Chama
    
    check_chama_admin(current_user, chama_id, db)
    
    loan = db.query(ChamaLoan).filter(
        ChamaLoan.id == loan_id,
        ChamaLoan.chama_id == chama_id
    ).first()
    
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan not found"
        )
    
    if loan.status != 'pending':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Loan is not pending"
        )
    
    # Check if chama has sufficient funds
    chama = db.query(Chama).filter(Chama.id == chama_id).first()
    if chama.total_savings < loan.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient chama funds"
        )
    
    loan.status = 'approved'
    loan.approved_by = current_user['id']
    loan.approved_at = datetime.utcnow()
    loan.disbursed_at = datetime.utcnow()
    
    # Update chama totals
    chama.total_loans_disbursed += loan.amount
    
    db.commit()
    
    return {
        "message": "Loan approved successfully",
        "loan_id": loan_id
    }


@router.post("/{chama_id}/loans/{loan_id}/reject")
async def reject_loan(
    chama_id: int,
    loan_id: int,
    reason: str = Query(..., min_length=10),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Reject a loan request.
    
    Requires admin or treasurer role.
    """
    from app.models.database import ChamaLoan
    
    check_chama_admin(current_user, chama_id, db)
    
    loan = db.query(ChamaLoan).filter(
        ChamaLoan.id == loan_id,
        ChamaLoan.chama_id == chama_id
    ).first()
    
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan not found"
        )
    
    if loan.status != 'pending':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Loan is not pending"
        )
    
    loan.status = 'rejected'
    loan.rejection_reason = reason
    loan.approved_by = current_user['id']
    loan.approved_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": "Loan rejected",
        "loan_id": loan_id
    }


@router.post("/{chama_id}/loans/{loan_id}/repay")
async def repay_loan(
    chama_id: int,
    loan_id: int,
    request: LoanRepaymentRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Make a loan repayment.
    """
    from app.models.database import ChamaLoan, ChamaMember, Chama
    
    check_chama_access(current_user, chama_id, db)
    
    loan = db.query(ChamaLoan).filter(
        ChamaLoan.id == loan_id,
        ChamaLoan.chama_id == chama_id,
        ChamaLoan.borrower_id == current_user['id']
    ).first()
    
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan not found"
        )
    
    if loan.status not in ['approved', 'disbursed', 'active']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Loan is not active"
        )
    
    if request.amount > loan.balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment amount exceeds balance"
        )
    
    # Update loan
    loan.amount_paid += request.amount
    loan.balance -= request.amount
    
    if loan.balance == 0:
        loan.status = 'repaid'
        loan.repaid_at = datetime.utcnow()
    
    # Update chama totals
    chama = db.query(Chama).filter(Chama.id == chama_id).first()
    chama.total_loans_repaid += request.amount
    
    db.commit()
    
    return {
        "message": "Payment recorded successfully",
        "amount_paid": float(request.amount),
        "remaining_balance": float(loan.balance)
    }


@router.get("/{chama_id}/financial-summary", response_model=FinancialSummaryResponse)
async def get_financial_summary(
    chama_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Get chama financial summary.
    
    Requires membership.
    """
    from app.models.database import Chama, ChamaMember, ChamaLoan, ChamaTransaction
    from sqlalchemy import func
    
    check_chama_access(current_user, chama_id, db)
    
    chama = db.query(Chama).filter(Chama.id == chama_id).first()
    
    # Active members
    active_members = db.query(func.count(ChamaMember.id)).filter(
        ChamaMember.chama_id == chama_id,
        ChamaMember.is_active == True
    ).scalar()
    
    # Monthly contributions
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total_contributions_month = db.query(
        func.coalesce(func.sum(ChamaTransaction.amount), 0)
    ).filter(
        ChamaTransaction.chama_id == chama_id,
        ChamaTransaction.transaction_type == 'contribution',
        ChamaTransaction.created_at >= month_start
    ).scalar()
    
    # Withdrawals this month
    total_withdrawals_month = db.query(
        func.coalesce(func.sum(ChamaTransaction.amount), 0)
    ).filter(
        ChamaTransaction.chama_id == chama_id,
        ChamaTransaction.transaction_type == 'withdrawal',
        ChamaTransaction.created_at >= month_start
    ).scalar()
    
    # Loan statistics
    total_loans = db.query(func.count(ChamaLoan.id)).filter(
        ChamaLoan.chama_id == chama_id
    ).scalar()
    
    active_loans = db.query(func.count(ChamaLoan.id)).filter(
        ChamaLoan.chama_id == chama_id,
        ChamaLoan.status.in_(['approved', 'disbursed', 'active'])
    ).scalar()
    
    outstanding_balance = db.query(
        func.coalesce(func.sum(ChamaLoan.balance), 0)
    ).filter(
        ChamaLoan.chama_id == chama_id,
        ChamaLoan.status.in_(['approved', 'disbursed', 'active'])
    ).scalar()
    
    # Calculate metrics
    average_member_savings = chama.total_savings / active_members if active_members > 0 else Decimal('0.00')
    default_rate = 0.0  # Placeholder
    return_on_savings = 0.0  # Placeholder
    
    return FinancialSummaryResponse(
        chama_id=chama_id,
        total_members=chama.member_count,
        active_members=active_members,
        total_savings=chama.total_savings,
        total_contributions_month=total_contributions_month,
        total_withdrawals_month=total_withdrawals_month,
        total_loans=total_loans,
        active_loans=active_loans,
        total_loans_disbursed=chama.total_loans_disbursed,
        total_loans_repaid=chama.total_loans_repaid,
        outstanding_balance=outstanding_balance,
        default_rate=default_rate,
        average_member_savings=average_member_savings,
        total_dividends_paid=Decimal('0.00'),
        return_on_savings=return_on_savings
    )


@router.post("/{chama_id}/meetings", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def schedule_meeting(
    chama_id: int,
    request: MeetingCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Schedule a chama meeting.
    
    Requires admin or leadership role.
    """
    from app.models.database import ChamaMeeting
    
    check_chama_admin(current_user, chama_id, db)
    
    meeting = ChamaMeeting(
        chama_id=chama_id,
        title=request.title,
        description=request.description,
        meeting_date=request.meeting_date,
        location=request.location,
        agenda=request.agenda,
        status='scheduled'
    )
    
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    
    return meeting


@router.get("/{chama_id}/meetings", response_model=List[MeetingResponse])
async def list_meetings(
    chama_id: int,
    upcoming_only: bool = True,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    List chama meetings.
    """
    from app.models.database import ChamaMeeting
    
    check_chama_access(current_user, chama_id, db)
    
    query = db.query(ChamaMeeting).filter(ChamaMeeting.chama_id == chama_id)
    
    if upcoming_only:
        query = query.filter(ChamaMeeting.meeting_date >= datetime.utcnow())
    
    meetings = query.order_by(ChamaMeeting.meeting_date.asc()).all()
    
    return meetings
