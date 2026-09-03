"""
Digital Chama (savings group) API - v1, real and deliberately small.

Rewritten 2026-09-03 from scratch. The two previous implementations
(this file's old version, and app/api/digital_chama.py) were both dead:
neither was wired into main.py, one had no authentication at all, and both
referenced ORM classes/columns (ChamaMember, ChamaLoan, county, founder_id...)
that don't exist in the real Chama/Transaction/Loan models below - see the
audit that preceded this rewrite. Rather than reconcile three incompatible,
non-functional designs against a live schema none of them matched, and with
zero real chama membership in the database to migrate, this starts over
against what's actually there.

Scope is intentionally minimal: create a chama, join one, see its members,
record and view contributions. No loans, guarantors, meetings, disputes,
"AI" risk scoring, or blockchain/quantum anything - the old implementations'
versions of those were placeholder constants and marketing language, not
real functionality (see the audit), and none of it is needed for a first
real version of "a savings group, formalized."
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db_config import get_production_db_dependency
from app.models.database import Chama, Transaction, TransactionStatus, TransactionType, User, user_chama_association
from app.schemas.chama import (
    ChamaCreateRequest, ChamaMemberResponse, ChamaResponse,
    ContributionCreateRequest, ContributionResponse,
)

router = APIRouter(prefix="/chamas", tags=["Digital Chama"])


def _is_member(db: Session, chama_id: int, user_id: int) -> bool:
    return db.execute(
        select(user_chama_association.c.user_id).where(
            user_chama_association.c.chama_id == chama_id,
            user_chama_association.c.user_id == user_id,
            user_chama_association.c.status == 'active',
        )
    ).first() is not None


def _is_pending(db: Session, chama_id: int, user_id: int) -> bool:
    return db.execute(
        select(user_chama_association.c.user_id).where(
            user_chama_association.c.chama_id == chama_id,
            user_chama_association.c.user_id == user_id,
            user_chama_association.c.status == 'pending',
        )
    ).first() is not None


def _is_leader(chama: Chama, user_id: int) -> bool:
    """Chairperson, treasurer, or secretary - any of the three leadership
    seats on the Chama model can vet new members, matching how a real
    chama's committee (not just one person) usually handles admissions."""
    return user_id in (chama.chairperson_id, chama.treasurer_id, chama.secretary_id)


def _get_chama_or_404(db: Session, chama_id: int) -> Chama:
    chama = db.get(Chama, chama_id)
    if chama is None or chama.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chama not found")
    return chama


def _to_response(chama: Chama, user_id: int, is_member: bool, is_pending: bool = False) -> ChamaResponse:
    resp = ChamaResponse.model_validate(chama)
    resp.is_member = is_member
    resp.is_pending = is_pending
    resp.is_leader = _is_leader(chama, user_id)
    # The paybill is where members actually send money - visible to members
    # only, same as the member list and contribution history below.
    if not is_member:
        resp.mpesa_paybill_number = None
    return resp


@router.post("", response_model=ChamaResponse, status_code=status.HTTP_201_CREATED)
def create_chama(
    request: ChamaCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    """Creates a chama and makes the creator its chairperson and first
    member. chama_code is generated, not user-supplied - it's an internal
    unique identifier, not a vanity name (name is)."""
    chama = Chama(
        uuid=uuid.uuid4(),
        chama_code=f"CHM-{uuid.uuid4().hex[:8].upper()}",
        name=request.name,
        description=request.description,
        chama_type=request.chama_type,
        chairperson_id=current_user["id"],
        member_count=1,
        monthly_contribution_ksh=request.monthly_contribution_ksh,
        is_public=request.is_public,
        mpesa_paybill_number=request.mpesa_paybill_number,
    )
    db.add(chama)
    db.flush()

    db.execute(insert(user_chama_association).values(
        user_id=current_user["id"], chama_id=chama.id, role="chairperson", status="active",
    ))
    db.commit()
    db.refresh(chama)
    return _to_response(chama, current_user["id"], is_member=True)


@router.get("", response_model=List[ChamaResponse])
def list_chamas(
    mine_only: bool = Query(False, description="Only chamas the caller belongs to"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    """Public chamas, plus any private ones the caller already belongs to -
    same visibility rule GET /chamas/{id} enforces. mine_only=true narrows
    that down to just the caller's own chamas (public or not)."""
    membership_rows = db.execute(
        select(user_chama_association.c.chama_id, user_chama_association.c.status).where(
            user_chama_association.c.user_id == current_user["id"],
        )
    ).all()
    member_chama_ids = {r.chama_id for r in membership_rows if r.status == 'active'}
    pending_chama_ids = {r.chama_id for r in membership_rows if r.status == 'pending'}

    query = select(Chama).where(Chama.is_deleted == False)  # noqa: E712
    if mine_only:
        if not member_chama_ids:
            return []
        query = query.where(Chama.id.in_(member_chama_ids))
    else:
        known_ids = member_chama_ids | pending_chama_ids
        query = query.where((Chama.is_public == True) | (Chama.id.in_(known_ids) if known_ids else False))  # noqa: E712

    chamas = db.execute(
        query.order_by(Chama.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()

    return [
        _to_response(c, current_user["id"], is_member=c.id in member_chama_ids, is_pending=c.id in pending_chama_ids)
        for c in chamas
    ]


@router.get("/{chama_id}", response_model=ChamaResponse)
def get_chama(
    chama_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    chama = _get_chama_or_404(db, chama_id)
    is_member = _is_member(db, chama_id, current_user["id"])
    is_pending = False if is_member else _is_pending(db, chama_id, current_user["id"])
    if not chama.is_public and not is_member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chama not found")
    return _to_response(chama, current_user["id"], is_member, is_pending)


@router.post("/{chama_id}/join", response_model=ChamaResponse)
def join_chama(
    chama_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    """Requests membership - does not grant it. A chairperson/treasurer/
    secretary must approve via POST /{chama_id}/join-requests/{user_id}/approve
    before this becomes real membership (is_member stays false; is_pending
    turns true). This is the vetting step real chamas already do informally
    before letting someone into the money pool - skipping it was the gap in
    the first version of this endpoint."""
    chama = _get_chama_or_404(db, chama_id)
    if not chama.is_public:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This chama is not open to new members")
    if _is_member(db, chama_id, current_user["id"]):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already a member of this chama")
    if _is_pending(db, chama_id, current_user["id"]):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Your request to join is already pending")
    if chama.max_members is not None and chama.member_count >= chama.max_members:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This chama is full")

    db.execute(insert(user_chama_association).values(
        user_id=current_user["id"], chama_id=chama_id, role="member", status="pending", is_active=False,
    ))
    db.commit()
    db.refresh(chama)
    return _to_response(chama, current_user["id"], is_member=False, is_pending=True)


@router.get("/{chama_id}/join-requests", response_model=List[ChamaMemberResponse])
def list_join_requests(
    chama_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    chama = _get_chama_or_404(db, chama_id)
    if not _is_leader(chama, current_user["id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the chairperson, treasurer, or secretary can view join requests")

    rows = db.execute(
        select(User.id, User.first_name, User.last_name, User.username, user_chama_association.c.joined_at)
        .join(user_chama_association, user_chama_association.c.user_id == User.id)
        .where(user_chama_association.c.chama_id == chama_id, user_chama_association.c.status == 'pending')
        .order_by(user_chama_association.c.joined_at)
    ).all()

    return [
        ChamaMemberResponse(
            user_id=r.id, full_name=f"{r.first_name} {r.last_name}".strip(),
            username=r.username, role='pending', joined_at=r.joined_at,
        )
        for r in rows
    ]


@router.post("/{chama_id}/join-requests/{user_id}/approve", response_model=ChamaResponse)
def approve_join_request(
    chama_id: int,
    user_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    chama = _get_chama_or_404(db, chama_id)
    if not _is_leader(chama, current_user["id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the chairperson, treasurer, or secretary can approve join requests")
    if not _is_pending(db, chama_id, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No pending request from this user")

    db.execute(update(user_chama_association).where(
        user_chama_association.c.chama_id == chama_id, user_chama_association.c.user_id == user_id,
    ).values(status='active', is_active=True))
    db.execute(update(Chama).where(Chama.id == chama_id).values(member_count=Chama.member_count + 1))
    db.commit()
    db.refresh(chama)
    return _to_response(chama, current_user["id"], is_member=True)


@router.post("/{chama_id}/join-requests/{user_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
def reject_join_request(
    chama_id: int,
    user_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    """Deletes the pending request rather than marking it 'rejected' -
    non-punitive, the same person can request again later (e.g. after
    resolving whatever the leadership's concern was)."""
    chama = _get_chama_or_404(db, chama_id)
    if not _is_leader(chama, current_user["id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the chairperson, treasurer, or secretary can reject join requests")
    if not _is_pending(db, chama_id, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No pending request from this user")

    db.execute(user_chama_association.delete().where(
        user_chama_association.c.chama_id == chama_id, user_chama_association.c.user_id == user_id,
    ))
    db.commit()


@router.get("/{chama_id}/members", response_model=List[ChamaMemberResponse])
def list_members(
    chama_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    _get_chama_or_404(db, chama_id)
    if not _is_member(db, chama_id, current_user["id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only members can view the member list")

    rows = db.execute(
        select(User.id, User.first_name, User.last_name, User.username,
               user_chama_association.c.role, user_chama_association.c.joined_at)
        .join(user_chama_association, user_chama_association.c.user_id == User.id)
        .where(user_chama_association.c.chama_id == chama_id, user_chama_association.c.status == 'active')
        .order_by(user_chama_association.c.joined_at)
    ).all()

    return [
        ChamaMemberResponse(
            user_id=r.id, full_name=f"{r.first_name} {r.last_name}".strip(),
            username=r.username, role=r.role, joined_at=r.joined_at,
        )
        for r in rows
    ]


@router.post("/{chama_id}/contributions", response_model=ContributionResponse, status_code=status.HTTP_201_CREATED)
def record_contribution(
    chama_id: int,
    request: ContributionCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    """Records a member's contribution as a real Transaction row and adds it
    to the chama's running savings total. No payment gateway is called here
    (no M-Pesa/Flutterwave integration exists in this codebase for chama
    contributions) - this records that a contribution happened, the same
    way a treasurer would write it in a ledger book. Marked COMPLETED
    immediately for that reason: there's no external payment to wait on."""
    chama = _get_chama_or_404(db, chama_id)
    if not _is_member(db, chama_id, current_user["id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only members can contribute")

    transaction = Transaction(
        uuid=uuid.uuid4(),
        transaction_id=f"TXN-{uuid.uuid4().hex[:12]}",
        user_id=current_user["id"],
        chama_id=chama_id,
        transaction_type=TransactionType.SAVINGS_DEPOSIT,
        amount_ksh=request.amount_ksh,
        payment_method=request.payment_method,
        status=TransactionStatus.COMPLETED,
        notes=request.notes,
    )
    db.add(transaction)
    db.execute(update(Chama).where(Chama.id == chama_id).values(
        total_savings_ksh=Chama.total_savings_ksh + request.amount_ksh
    ))
    db.commit()
    db.refresh(transaction)
    return ContributionResponse(
        id=transaction.id, transaction_id=transaction.transaction_id, user_id=transaction.user_id,
        amount_ksh=transaction.amount_ksh, payment_method=transaction.payment_method,
        status=transaction.status.value, notes=transaction.notes, initiated_at=transaction.initiated_at,
    )


@router.get("/{chama_id}/contributions", response_model=List[ContributionResponse])
def list_contributions(
    chama_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    """Full contribution history for the chama, not just the caller's own -
    a group's members seeing each other's contributions is the point of a
    transparent savings group, not a privacy leak."""
    _get_chama_or_404(db, chama_id)
    if not _is_member(db, chama_id, current_user["id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only members can view contributions")

    transactions = db.execute(
        select(Transaction)
        .where(Transaction.chama_id == chama_id, Transaction.transaction_type == TransactionType.SAVINGS_DEPOSIT)
        .order_by(Transaction.initiated_at.desc())
    ).scalars().all()

    return [
        ContributionResponse(
            id=t.id, transaction_id=t.transaction_id, user_id=t.user_id,
            amount_ksh=t.amount_ksh, payment_method=t.payment_method,
            status=t.status.value, notes=t.notes, initiated_at=t.initiated_at,
        )
        for t in transactions
    ]
