"""
Friend requests + county-based farmer discovery - v1, small and scoped
directly by the user: help people find a chama worth joining, not a general
social network (no messaging, no profiles beyond name/county) and not a
vouching layer wired into chama approval - those were both considered and
explicitly ruled out in favor of this narrower purpose.

"Proximity" means same-county (User.county), not GPS radius - the user's
own call, since county is already a real, populated field (no new location
math needed). Connections are symmetric friend requests: send, the other
person accepts or rejects, then both sides are equally "friends" - no
followers/following asymmetry.
"""

from datetime import datetime, timezone
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db_config import get_production_db_dependency
from app.models.database import Chama, FriendRequest, User, user_chama_association
from app.schemas.friend import (
    ChamaSummary, FriendRequestCreate, FriendRequestResponse, FriendResponse, NearbyFarmerResponse,
)

router = APIRouter(tags=["Friends"])


def _full_name(user: User) -> str:
    return f"{user.first_name} {user.last_name}".strip()


def _public_chamas_by_user(db: Session, user_ids: List[int]) -> Dict[int, List[ChamaSummary]]:
    if not user_ids:
        return {}
    rows = db.execute(
        select(user_chama_association.c.user_id, Chama.id, Chama.name)
        .join(Chama, Chama.id == user_chama_association.c.chama_id)
        .where(
            user_chama_association.c.user_id.in_(user_ids),
            user_chama_association.c.status == "active",
            Chama.is_public == True,  # noqa: E712
        )
    ).all()
    by_user: Dict[int, List[ChamaSummary]] = {}
    for user_id, chama_id, chama_name in rows:
        by_user.setdefault(user_id, []).append(ChamaSummary(id=chama_id, name=chama_name))
    return by_user


@router.get("/users/nearby", response_model=List[NearbyFarmerResponse])
async def list_nearby_farmers(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    """Other users in the caller's own county - the discovery list a farmer
    browses to find people (and, via their public chamas, chamas) worth
    connecting with. Empty county means nothing to compare against, so it
    returns an empty list rather than everyone."""
    me = db.execute(select(User).where(User.id == current_user["id"])).scalar_one()
    if not me.county:
        return []

    others = db.execute(
        select(User).where(User.county == me.county, User.id != me.id, User.is_deleted == False)  # noqa: E712
    ).scalars().all()
    if not others:
        return []

    other_ids = [u.id for u in others]
    existing = db.execute(
        select(FriendRequest).where(
            FriendRequest.requester_id.in_([me.id, *other_ids]),
            FriendRequest.recipient_id.in_([me.id, *other_ids]),
        )
    ).scalars().all()
    friend_ids = set()
    pending_sent_ids = set()
    for req in existing:
        if me.id not in (req.requester_id, req.recipient_id):
            continue
        other_id = req.recipient_id if req.requester_id == me.id else req.requester_id
        if req.status == "accepted":
            friend_ids.add(other_id)
        elif req.status == "pending" and req.requester_id == me.id:
            pending_sent_ids.add(other_id)

    chamas_by_user = _public_chamas_by_user(db, other_ids)

    return [
        NearbyFarmerResponse(
            id=u.id, name=_full_name(u), county=u.county,
            is_friend=u.id in friend_ids, request_pending=u.id in pending_sent_ids,
            public_chamas=chamas_by_user.get(u.id, []),
        )
        for u in others
    ]


@router.post("/friends/requests", response_model=FriendRequestResponse, status_code=status.HTTP_201_CREATED)
async def send_friend_request(
    request: FriendRequestCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    if request.recipient_id == current_user["id"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot friend-request yourself")
    recipient = db.execute(select(User).where(User.id == request.recipient_id)).scalar_one_or_none()
    if recipient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    reverse = db.execute(
        select(FriendRequest).where(
            FriendRequest.requester_id == request.recipient_id, FriendRequest.recipient_id == current_user["id"],
        )
    ).scalar_one_or_none()
    if reverse is not None:
        if reverse.status == "accepted":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already friends")
        # They already asked first - accepting now makes this a mutual
        # request rather than two separate pending rows for the same pair.
        reverse.status = "accepted"
        reverse.responded_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(reverse)
        return FriendRequestResponse(
            id=reverse.id, requester_id=reverse.requester_id, requester_name=_full_name(recipient),
            requester_county=recipient.county, created_at=reverse.created_at,
        )

    forward = db.execute(
        select(FriendRequest).where(
            FriendRequest.requester_id == current_user["id"], FriendRequest.recipient_id == request.recipient_id,
        )
    ).scalar_one_or_none()
    if forward is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already friends" if forward.status == "accepted" else "Request already pending",
        )

    friend_request = FriendRequest(requester_id=current_user["id"], recipient_id=request.recipient_id)
    db.add(friend_request)
    db.commit()
    db.refresh(friend_request)
    me = db.execute(select(User).where(User.id == current_user["id"])).scalar_one()
    return FriendRequestResponse(
        id=friend_request.id, requester_id=me.id, requester_name=_full_name(me),
        requester_county=me.county, created_at=friend_request.created_at,
    )


@router.get("/friends/requests", response_model=List[FriendRequestResponse])
async def list_incoming_friend_requests(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    rows = db.execute(
        select(FriendRequest, User)
        .join(User, User.id == FriendRequest.requester_id)
        .where(FriendRequest.recipient_id == current_user["id"], FriendRequest.status == "pending")
        .order_by(FriendRequest.created_at.desc())
    ).all()
    return [
        FriendRequestResponse(
            id=req.id, requester_id=req.requester_id, requester_name=_full_name(requester),
            requester_county=requester.county, created_at=req.created_at,
        )
        for req, requester in rows
    ]


@router.post("/friends/requests/{request_id}/accept", response_model=FriendResponse)
async def accept_friend_request(
    request_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    req = db.execute(
        select(FriendRequest).where(FriendRequest.id == request_id, FriendRequest.recipient_id == current_user["id"])
    ).scalar_one_or_none()
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friend request not found")
    req.status = "accepted"
    req.responded_at = datetime.now(timezone.utc)
    db.commit()
    requester = db.execute(select(User).where(User.id == req.requester_id)).scalar_one()
    return FriendResponse(id=requester.id, name=_full_name(requester), county=requester.county, friends_since=req.responded_at)


@router.post("/friends/requests/{request_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_friend_request(
    request_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    req = db.execute(
        select(FriendRequest).where(FriendRequest.id == request_id, FriendRequest.recipient_id == current_user["id"])
    ).scalar_one_or_none()
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friend request not found")
    db.delete(req)
    db.commit()


@router.get("/friends", response_model=List[FriendResponse])
async def list_friends(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency),
):
    rows = db.execute(
        select(FriendRequest).where(
            FriendRequest.status == "accepted",
            (FriendRequest.requester_id == current_user["id"]) | (FriendRequest.recipient_id == current_user["id"]),
        )
    ).scalars().all()
    friend_ids = [
        req.recipient_id if req.requester_id == current_user["id"] else req.requester_id
        for req in rows
    ]
    by_id = {req_friend_id: req for req_friend_id, req in zip(friend_ids, rows)}
    if not friend_ids:
        return []
    users = db.execute(select(User).where(User.id.in_(friend_ids))).scalars().all()
    return [
        FriendResponse(id=u.id, name=_full_name(u), county=u.county, friends_since=by_id[u.id].responded_at)
        for u in users
    ]
