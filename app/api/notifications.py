"""
🔔 Notifications API

FastAPI endpoints for notification management, delivery, and preferences.

Endpoints:
- GET /notifications - List user notifications
- GET /notifications/{notification_id} - Get notification details
- PATCH /notifications/{notification_id}/read - Mark as read
- DELETE /notifications/{notification_id} - Delete notification
- POST /notifications/mark-all-read - Mark all as read
- GET /notifications/unread-count - Get unread count
- POST /notifications/send - Send notification (admin)
- GET /notifications/preferences - Get user preferences
- PATCH /notifications/preferences - Update preferences
- POST /notifications/subscribe - Subscribe to push notifications
- POST /notifications/unsubscribe - Unsubscribe from push

Author: AgroPulse Engineering Team
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db_config import get_production_db_dependency
from app.api.auth import get_current_user


router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class NotificationSendRequest(BaseModel):
    """Send notification request."""
    user_ids: List[int] = Field(..., min_items=1)
    notification_type: str = Field(..., pattern="^(info|warning|success|error|alert)$")
    title: str = Field(..., min_length=3, max_length=200)
    message: str = Field(..., min_length=10)
    action_url: Optional[str] = None
    priority: str = Field("normal", pattern="^(low|normal|high|urgent)$")
    send_push: bool = True
    send_email: bool = False
    send_sms: bool = False


class NotificationListResponse(BaseModel):
    """Notification list response."""
    id: int
    uuid: str
    notification_type: str
    title: str
    message: str
    is_read: bool
    priority: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class NotificationDetailResponse(BaseModel):
    """Detailed notification response."""
    id: int
    uuid: str
    user_id: int
    notification_type: str
    title: str
    message: str
    action_url: Optional[str]
    priority: str
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class NotificationPreferencesResponse(BaseModel):
    """Notification preferences response."""
    user_id: int
    email_notifications: bool
    sms_notifications: bool
    push_notifications: bool
    digest_frequency: str
    
    # Category preferences
    diagnosis_alerts: bool
    weather_alerts: bool
    price_alerts: bool
    chama_notifications: bool
    system_notifications: bool
    marketing_notifications: bool
    
    class Config:
        from_attributes = True


class NotificationPreferencesUpdateRequest(BaseModel):
    """Update notification preferences request."""
    email_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    digest_frequency: Optional[str] = Field(None, pattern="^(immediate|daily|weekly|never)$")
    
    # Category preferences
    diagnosis_alerts: Optional[bool] = None
    weather_alerts: Optional[bool] = None
    price_alerts: Optional[bool] = None
    chama_notifications: Optional[bool] = None
    system_notifications: Optional[bool] = None
    marketing_notifications: Optional[bool] = None


class PushSubscriptionRequest(BaseModel):
    """Push notification subscription request."""
    endpoint: str = Field(..., min_length=10)
    auth_key: str = Field(..., min_length=10)
    p256dh_key: str = Field(..., min_length=10)
    device_type: str = Field(..., pattern="^(web|android|ios)$")
    device_name: Optional[str] = None


class UnreadCountResponse(BaseModel):
    """Unread notification count response."""
    unread_count: int
    by_type: dict
    by_priority: dict


class PaginatedNotificationsResponse(BaseModel):
    """Paginated notifications response."""
    items: List[NotificationListResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def send_push_notification(user_id: int, title: str, message: str, db: Session):
    """Send push notification to user's devices."""
    # TODO: Integrate with Firebase Cloud Messaging (FCM) or similar
    # Get user's push subscriptions and send notifications
    pass


async def send_email_notification(user_id: int, title: str, message: str, db: Session):
    """Send email notification to user."""
    # TODO: Integrate with email service (SendGrid, AWS SES, etc.)
    from app.models.database import User
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.email:
        # Send email
        pass


async def send_sms_notification(user_id: int, message: str, db: Session):
    """Send SMS notification to user."""
    # TODO: Integrate with SMS service (Twilio, Africa's Talking, etc.)
    from app.models.database import User
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.phone_number:
        # Send SMS
        pass


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("", response_model=PaginatedNotificationsResponse)
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = False,
    notification_type: Optional[str] = None,
    priority: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    List user notifications with pagination.
    
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **unread_only**: Show only unread notifications (default: false)
    - **notification_type**: Filter by type (optional)
    - **priority**: Filter by priority (optional)
    """
    from app.models.database import Notification
    
    query = db.query(Notification).filter(
        Notification.user_id == current_user['id'],
        Notification.is_deleted == False
    )
    
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    if notification_type:
        query = query.filter(Notification.notification_type == notification_type)
    
    if priority:
        query = query.filter(Notification.priority == priority)
    
    total = query.count()
    
    skip = (page - 1) * page_size
    notifications = query.order_by(
        Notification.created_at.desc()
    ).offset(skip).limit(page_size).all()
    
    return PaginatedNotificationsResponse(
        items=notifications,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Get unread notification count.
    """
    from app.models.database import Notification
    from sqlalchemy import func
    
    # Total unread
    unread_count = db.query(func.count(Notification.id)).filter(
        Notification.user_id == current_user['id'],
        Notification.is_read == False,
        Notification.is_deleted == False
    ).scalar()
    
    # Count by type
    by_type = {}
    type_counts = db.query(
        Notification.notification_type,
        func.count(Notification.id).label('count')
    ).filter(
        Notification.user_id == current_user['id'],
        Notification.is_read == False,
        Notification.is_deleted == False
    ).group_by(Notification.notification_type).all()
    
    for ntype, count in type_counts:
        by_type[ntype] = count
    
    # Count by priority
    by_priority = {}
    priority_counts = db.query(
        Notification.priority,
        func.count(Notification.id).label('count')
    ).filter(
        Notification.user_id == current_user['id'],
        Notification.is_read == False,
        Notification.is_deleted == False
    ).group_by(Notification.priority).all()
    
    for priority, count in priority_counts:
        by_priority[priority] = count
    
    return UnreadCountResponse(
        unread_count=unread_count,
        by_type=by_type,
        by_priority=by_priority
    )


@router.get("/{notification_id}", response_model=NotificationDetailResponse)
async def get_notification(
    notification_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Get notification details by ID.
    """
    from app.models.database import Notification
    
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user['id'],
        Notification.is_deleted == False
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return notification


@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Mark notification as read.
    """
    from app.models.database import Notification
    
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user['id'],
        Notification.is_deleted == False
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        db.commit()
    
    return {
        "message": "Notification marked as read",
        "notification_id": notification_id
    }


@router.post("/mark-all-read")
async def mark_all_notifications_read(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Mark all notifications as read.
    """
    from app.models.database import Notification
    
    updated_count = db.query(Notification).filter(
        Notification.user_id == current_user['id'],
        Notification.is_read == False,
        Notification.is_deleted == False
    ).update({
        "is_read": True,
        "read_at": datetime.utcnow()
    })
    
    db.commit()
    
    return {
        "message": "All notifications marked as read",
        "count": updated_count
    }


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Delete notification (soft delete).
    """
    from app.models.database import Notification
    
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user['id'],
        Notification.is_deleted == False
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    notification.is_deleted = True
    notification.deleted_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Notification deleted successfully"}


@router.post("/send", status_code=status.HTTP_201_CREATED)
async def send_notification(
    request: NotificationSendRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Send notification to users.
    
    Requires admin role.
    
    - **user_ids**: List of user IDs (required)
    - **notification_type**: Type (info, warning, success, error, alert)
    - **title**: Notification title (required)
    - **message**: Notification message (required)
    - **action_url**: Optional action URL
    - **priority**: Priority level (low, normal, high, urgent)
    - **send_push**: Send push notification (default: true)
    - **send_email**: Send email notification (default: false)
    - **send_sms**: Send SMS notification (default: false)
    """
    from app.models.database import Notification
    
    if current_user['role'] not in ['admin', 'superuser']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    notifications_created = []
    
    for user_id in request.user_ids:
        # Create notification record
        notification = Notification(
            user_id=user_id,
            notification_type=request.notification_type,
            title=request.title,
            message=request.message,
            action_url=request.action_url,
            priority=request.priority,
            is_read=False
        )
        
        db.add(notification)
        notifications_created.append(user_id)
        
        # Send via different channels
        if request.send_push:
            await send_push_notification(user_id, request.title, request.message, db)
        
        if request.send_email:
            await send_email_notification(user_id, request.title, request.message, db)
        
        if request.send_sms:
            await send_sms_notification(user_id, request.message, db)
    
    db.commit()
    
    return {
        "message": "Notifications sent successfully",
        "count": len(notifications_created),
        "user_ids": notifications_created
    }


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Get user notification preferences.
    """
    from app.models.database import NotificationPreference
    
    preferences = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user['id']
    ).first()
    
    if not preferences:
        # Create default preferences
        preferences = NotificationPreference(
            user_id=current_user['id'],
            email_notifications=True,
            sms_notifications=False,
            push_notifications=True,
            digest_frequency='immediate',
            diagnosis_alerts=True,
            weather_alerts=True,
            price_alerts=True,
            chama_notifications=True,
            system_notifications=True,
            marketing_notifications=False
        )
        db.add(preferences)
        db.commit()
        db.refresh(preferences)
    
    return preferences


@router.patch("/preferences", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    request: NotificationPreferencesUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Update user notification preferences.
    """
    from app.models.database import NotificationPreference
    
    preferences = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user['id']
    ).first()
    
    if not preferences:
        # Create with provided values
        preferences = NotificationPreference(user_id=current_user['id'])
        db.add(preferences)
    
    # Update fields
    update_data = {k: v for k, v in request.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data to update"
        )
    
    for key, value in update_data.items():
        setattr(preferences, key, value)
    
    preferences.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(preferences)
    
    return preferences


@router.post("/subscribe", status_code=status.HTTP_201_CREATED)
async def subscribe_push_notifications(
    request: PushSubscriptionRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Subscribe to push notifications.
    
    - **endpoint**: Push service endpoint (required)
    - **auth_key**: Authentication key (required)
    - **p256dh_key**: Encryption key (required)
    - **device_type**: Device type (web, android, ios)
    - **device_name**: Optional device name
    """
    from app.models.database import PushSubscription
    
    # Check if subscription already exists
    existing = db.query(PushSubscription).filter(
        PushSubscription.user_id == current_user['id'],
        PushSubscription.endpoint == request.endpoint
    ).first()
    
    if existing:
        # Update existing subscription
        existing.auth_key = request.auth_key
        existing.p256dh_key = request.p256dh_key
        existing.device_type = request.device_type
        existing.device_name = request.device_name
        existing.is_active = True
        existing.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            "message": "Push subscription updated",
            "subscription_id": existing.id
        }
    
    # Create new subscription
    subscription = PushSubscription(
        user_id=current_user['id'],
        endpoint=request.endpoint,
        auth_key=request.auth_key,
        p256dh_key=request.p256dh_key,
        device_type=request.device_type,
        device_name=request.device_name,
        is_active=True
    )
    
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    
    return {
        "message": "Push subscription created successfully",
        "subscription_id": subscription.id
    }


@router.post("/unsubscribe")
async def unsubscribe_push_notifications(
    endpoint: str = Query(..., min_length=10),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Unsubscribe from push notifications.
    
    - **endpoint**: Push service endpoint to unsubscribe
    """
    from app.models.database import PushSubscription
    
    subscription = db.query(PushSubscription).filter(
        PushSubscription.user_id == current_user['id'],
        PushSubscription.endpoint == endpoint,
        PushSubscription.is_active == True
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    subscription.is_active = False
    subscription.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "message": "Push subscription deactivated successfully"
    }
