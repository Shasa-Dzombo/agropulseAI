from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ChamaSummary(BaseModel):
    id: int
    name: str


class NearbyFarmerResponse(BaseModel):
    """A user in the caller's own county, for chama-discovery purposes -
    see app/api/friends.py's GET /users/nearby. public_chamas only ever
    lists chamas with is_public=True, same visibility rule the chama
    browse endpoint already uses (app/api/chamas.py)."""
    id: int
    name: str
    county: Optional[str] = None
    is_friend: bool
    request_pending: bool
    public_chamas: List[ChamaSummary] = []


class FriendRequestCreate(BaseModel):
    recipient_id: int


class FriendRequestResponse(BaseModel):
    id: int
    requester_id: int
    requester_name: str
    requester_county: Optional[str] = None
    created_at: datetime


class FriendResponse(BaseModel):
    id: int
    name: str
    county: Optional[str] = None
    friends_since: Optional[datetime] = None
