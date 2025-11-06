"""
👤 Users API (Growers & Horticulturists)

FastAPI endpoints for user management, profile, and account operations.

Endpoints:
- GET /users - List users (admin/agronomist/horticulturist only)
- GET /users/{user_id} - Get user by ID
- GET /users/search - Search users
- PATCH /users/{user_id} - Update user profile
- DELETE /users/{user_id} - Delete user (soft delete)
- GET /users/{user_id}/farms - Get user's greenhouse facilities
- GET /users/{user_id}/diagnoses - Get user's crop health diagnoses
- GET /users/{user_id}/referrals - Get user's referrals
- GET /users/statistics - Get user statistics (admin only)
- POST /users/{user_id}/subscription - Update subscription
- POST /users/{user_id}/avatar - Upload avatar

Author: AgroPulse Engineering Team
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.db_config import get_production_db_dependency
from app.repositories.user import UserRepository
from app.api.auth import get_current_user


router = APIRouter(prefix="/users", tags=["Users"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class UserListResponse(BaseModel):
    """User list response."""
    id: int
    uuid: str
    email: str
    first_name: str
    last_name: str
    role: str
    status: str
    county: Optional[str]
    is_verified: bool
    subscription_tier: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserDetailResponse(BaseModel):
    """Detailed user response."""
    id: int
    uuid: str
    email: str
    phone_number: Optional[str]
    first_name: str
    last_name: str
    middle_name: Optional[str]
    display_name: Optional[str]
    date_of_birth: Optional[str]
    gender: Optional[str]
    national_id: Optional[str]
    
    # Contact
    alternate_phone: Optional[str]
    whatsapp_number: Optional[str]
    address_line1: Optional[str]
    city: Optional[str]
    county: Optional[str]
    country: str
    
    # Location
    latitude: Optional[float]
    longitude: Optional[float]
    
    # Role and status
    role: str
    status: str
    is_verified: bool
    email_verified: bool
    phone_verified: bool
    
    # Subscription
    subscription_tier: str
    subscription_expires_at: Optional[datetime]
    diagnoses_remaining: int
    
    # Profile
    profile_completion_percentage: float
    onboarding_completed: bool
    avatar_url: Optional[str]
    
    # Activity
    last_login_at: Optional[datetime]
    login_count: int
    
    # Metrics
    total_diagnoses: int
    total_farms: int
    reputation_score: float
    
    # Referral
    referral_code: Optional[str]
    referral_count: int
    referral_earnings_ksh: float
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UpdateProfileRequest(BaseModel):
    """Update profile request."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    display_name: Optional[str] = Field(None, max_length=200)
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    alternate_phone: Optional[str] = None
    whatsapp_number: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class UpdateSubscriptionRequest(BaseModel):
    """Update subscription request."""
    tier: str = Field(..., pattern='^(free|basic|premium|enterprise)$')
    duration_months: int = Field(..., ge=1, le=36)
    diagnoses_count: Optional[int] = Field(None, ge=0)


class PaginatedUsersResponse(BaseModel):
    """Paginated users response."""
    items: List[UserListResponse]
    total: int
    page: int
    page_size: int
    pages: int


class UserStatisticsResponse(BaseModel):
    """User statistics response."""
    total_users: int
    active_users: int
    verified_users: int
    farmers: int
    agronomists: int
    pending_verification: int
    subscription_breakdown: dict


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def check_admin(current_user: dict):
    """Check if current user is admin."""
    if current_user['role'] not in ['admin', 'superuser']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )


def check_access(current_user: dict, user_id: int):
    """Check if current user can access user data."""
    if current_user['role'] not in ['admin', 'superuser'] and current_user['id'] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("", response_model=PaginatedUsersResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Optional[str] = None,
    county: Optional[str] = None,
    status: Optional[str] = None,
    verified_only: bool = False,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    List users with pagination and filters.
    
    Requires admin or agronomist role.
    
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **role**: Filter by role (optional)
    - **county**: Filter by county (optional)
    - **status**: Filter by status (optional)
    - **verified_only**: Show only verified users (default: false)
    """
    # Check permissions
    if current_user['role'] not in ['admin', 'agronomist', 'superuser']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or agronomist access required"
        )
    
    user_repo = UserRepository(db)
    
    # Build filters
    filters = {}
    if role:
        filters['role'] = role
    if county:
        filters['county'] = county
    if status:
        filters['status'] = status
    if verified_only:
        filters['is_verified'] = True
    
    # Get users
    skip = (page - 1) * page_size
    users = user_repo.filter(filters, skip=skip, limit=page_size)
    total = user_repo.count(filters)
    
    return PaginatedUsersResponse(
        items=users,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.get("/search", response_model=List[UserListResponse])
async def search_users(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Search users by name, email, or phone.
    
    - **q**: Search query (min 2 characters)
    - **limit**: Maximum results (default: 20, max: 100)
    """
    user_repo = UserRepository(db)
    users = user_repo.search_users(q, skip=0, limit=limit)
    
    return users


@router.get("/statistics", response_model=UserStatisticsResponse)
async def get_user_statistics(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Get user statistics.
    
    Requires admin role.
    """
    check_admin(current_user)
    
    user_repo = UserRepository(db)
    stats = user_repo.get_user_statistics()
    breakdown = user_repo.get_subscription_breakdown()
    
    return UserStatisticsResponse(
        **stats,
        subscription_breakdown=breakdown
    )


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Get user by ID.
    
    Users can access their own data.
    Admins and agronomists can access any user.
    """
    check_access(current_user, user_id)
    
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.patch("/{user_id}", response_model=UserDetailResponse)
async def update_user_profile(
    user_id: int,
    request: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Update user profile.
    
    Users can update their own profile.
    Admins can update any user profile.
    """
    check_access(current_user, user_id)
    
    user_repo = UserRepository(db)
    
    # Filter out None values
    update_data = {k: v for k, v in request.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data to update"
        )
    
    user = user_repo.update_profile(user_id, **update_data)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    permanent: bool = Query(False),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Delete user (soft delete by default).
    
    - **permanent**: Permanent delete (default: false, requires admin)
    
    Users can delete their own account.
    Admins can delete any account.
    """
    check_access(current_user, user_id)
    
    # Permanent delete requires admin
    if permanent and current_user['role'] not in ['admin', 'superuser']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for permanent deletion"
        )
    
    user_repo = UserRepository(db)
    success = user_repo.delete_by_id(user_id, soft=not permanent)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "message": "User deleted successfully",
        "permanent": permanent
    }


@router.get("/{user_id}/farms")
async def get_user_farms(
    user_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Get user's farms.
    
    Users can access their own farms.
    Admins and agronomists can access any user's farms.
    """
    check_access(current_user, user_id)
    
    from app.repositories.farm import FarmRepository
    farm_repo = FarmRepository(db)
    farms = farm_repo.get_by_user(user_id)
    
    return {
        "user_id": user_id,
        "total_farms": len(farms),
        "farms": farms
    }


@router.get("/{user_id}/referrals")
async def get_user_referrals(
    user_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Get user's referrals.
    
    Users can access their own referrals.
    Admins can access any user's referrals.
    """
    check_access(current_user, user_id)
    
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    referrals = user_repo.get_referrals(user_id)
    
    return {
        "user_id": user_id,
        "referral_code": user.referral_code,
        "total_referrals": user.referral_count,
        "earnings_ksh": float(user.referral_earnings_ksh),
        "referrals": [
            {
                "id": r.id,
                "name": f"{r.first_name} {r.last_name}",
                "email": r.email,
                "joined_at": r.created_at
            } for r in referrals
        ]
    }


@router.post("/{user_id}/subscription", response_model=UserDetailResponse)
async def update_user_subscription(
    user_id: int,
    request: UpdateSubscriptionRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Update user subscription.
    
    Requires admin role.
    
    - **tier**: Subscription tier (free, basic, premium, enterprise)
    - **duration_months**: Duration in months (1-36)
    - **diagnoses_count**: Number of diagnoses to add (optional)
    """
    check_admin(current_user)
    
    from datetime import timedelta
    user_repo = UserRepository(db)
    
    # Calculate expiry date
    expires_at = datetime.utcnow() + timedelta(days=request.duration_months * 30)
    
    # Determine diagnoses count based on tier
    if request.diagnoses_count is not None:
        diagnoses = request.diagnoses_count
    else:
        tier_diagnoses = {
            'free': 3,
            'basic': 50,
            'premium': 200,
            'enterprise': 999999
        }
        diagnoses = tier_diagnoses.get(request.tier, 3)
    
    user = user_repo.update_subscription(
        user_id=user_id,
        tier=request.tier,
        expires_at=expires_at,
        diagnoses_remaining=diagnoses
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.post("/{user_id}/avatar")
async def upload_avatar(
    user_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Upload user avatar.
    
    Users can upload their own avatar.
    
    - **file**: Image file (jpg, png, max 5MB)
    """
    check_access(current_user, user_id)
    
    # Validate file type
    if file.content_type not in ['image/jpeg', 'image/png', 'image/jpg']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only JPG and PNG allowed."
        )
    
    # TODO: Implement file upload to cloud storage
    # For now, return placeholder
    avatar_url = f"https://storage.agropulse.ke/avatars/{user_id}/{file.filename}"
    
    user_repo = UserRepository(db)
    user = user_repo.update_profile(user_id, avatar_url=avatar_url)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "message": "Avatar uploaded successfully",
        "avatar_url": avatar_url
    }
