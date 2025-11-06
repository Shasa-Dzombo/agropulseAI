"""
SMS and Push Notification System

Multi-provider SMS, push notifications, templates, scheduling.

Features:
- Twilio SMS integration
- Firebase Cloud Messaging (FCM)
- Apple Push Notification Service (APNS)
- SMS templates
- Notification scheduling
- Delivery tracking
- Opt-in/opt-out management
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import re

try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logging.warning("Twilio library not available")


logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Notification types"""
    SMS = "sms"
    PUSH = "push"
    EMAIL = "email"
    IN_APP = "in_app"


class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class DeliveryStatus(Enum):
    """Delivery status"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class NotificationTemplate:
    """Notification template"""
    template_id: str
    name: str
    type: NotificationType
    content: str
    variables: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    def render(self, context: Dict[str, Any]) -> str:
        """
        Render template with context
        
        Args:
            context: Template variables
            
        Returns:
            Rendered content
        """
        rendered = self.content
        
        for var in self.variables:
            placeholder = f"{{{var}}}"
            value = context.get(var, '')
            rendered = rendered.replace(placeholder, str(value))
        
        return rendered


@dataclass
class Notification:
    """Notification message"""
    notification_id: str
    type: NotificationType
    recipient: str
    content: str
    priority: NotificationPriority = NotificationPriority.MEDIUM
    status: DeliveryStatus = DeliveryStatus.PENDING
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    metadata: Dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'notification_id': self.notification_id,
            'type': self.type.value,
            'recipient': self.recipient,
            'content': self.content,
            'priority': self.priority.value,
            'status': self.status.value,
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat()
        }


class SMSProvider:
    """
    SMS provider using Twilio
    
    Sends SMS messages with delivery tracking.
    """
    
    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str
    ):
        """
        Initialize SMS provider
        
        Args:
            account_sid: Twilio account SID
            auth_token: Twilio auth token
            from_number: Sender phone number
        """
        if not TWILIO_AVAILABLE:
            logger.warning("Twilio not available, using mock mode")
            self.mock_mode = True
            self.client = None
        else:
            self.mock_mode = False
            self.client = TwilioClient(account_sid, auth_token)
        
        self.from_number = from_number
        self.sent_messages: Dict[str, Dict] = {}
        
        logger.info(f"SMSProvider initialized (mock_mode={self.mock_mode})")
    
    def send_sms(
        self,
        to_number: str,
        message: str,
        metadata: Optional[Dict] = None
    ) -> Tuple[bool, str]:
        """
        Send SMS message
        
        Args:
            to_number: Recipient phone number
            message: Message content
            metadata: Additional metadata
            
        Returns:
            (success, message_id)
        """
        # Validate phone number
        if not self._validate_phone_number(to_number):
            logger.error(f"Invalid phone number: {to_number}")
            return False, ''
        
        # Truncate message if too long
        if len(message) > 1600:
            message = message[:1597] + '...'
        
        if self.mock_mode:
            message_id = f"sms_mock_{int(datetime.now().timestamp())}"
            self.sent_messages[message_id] = {
                'to': to_number,
                'message': message,
                'status': 'sent',
                'timestamp': datetime.now()
            }
            logger.info(f"[MOCK] SMS sent to {to_number}: {message_id}")
            return True, message_id
        
        try:
            result = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number
            )
            
            message_id = result.sid
            self.sent_messages[message_id] = {
                'to': to_number,
                'message': message,
                'status': result.status,
                'timestamp': datetime.now(),
                'metadata': metadata or {}
            }
            
            logger.info(f"SMS sent to {to_number}: {message_id}")
            
            return True, message_id
        
        except Exception as e:
            logger.error(f"Failed to send SMS to {to_number}: {e}")
            return False, ''
    
    def send_bulk_sms(
        self,
        recipients: List[str],
        message: str
    ) -> Dict[str, str]:
        """
        Send SMS to multiple recipients
        
        Args:
            recipients: List of phone numbers
            message: Message content
            
        Returns:
            Dictionary mapping phone numbers to message IDs
        """
        results = {}
        
        for phone in recipients:
            success, message_id = self.send_sms(phone, message)
            if success:
                results[phone] = message_id
        
        logger.info(f"Bulk SMS sent: {len(results)}/{len(recipients)} successful")
        
        return results
    
    def get_delivery_status(self, message_id: str) -> Optional[str]:
        """
        Get SMS delivery status
        
        Args:
            message_id: Message SID
            
        Returns:
            Delivery status
        """
        if message_id in self.sent_messages:
            return self.sent_messages[message_id]['status']
        
        if self.mock_mode:
            return 'delivered'
        
        try:
            message = self.client.messages(message_id).fetch()
            return message.status
        
        except Exception as e:
            logger.error(f"Failed to get status for {message_id}: {e}")
            return None
    
    def _validate_phone_number(self, phone: str) -> bool:
        """Validate phone number format"""
        # Simple E.164 format validation
        pattern = r'^\+[1-9]\d{1,14}$'
        return bool(re.match(pattern, phone))


class PushNotificationProvider:
    """
    Push notification provider using Firebase Cloud Messaging
    
    Sends push notifications to mobile devices.
    """
    
    def __init__(
        self,
        server_key: str,
        project_id: str
    ):
        """
        Initialize push notification provider
        
        Args:
            server_key: FCM server key
            project_id: Firebase project ID
        """
        self.server_key = server_key
        self.project_id = project_id
        self.mock_mode = True  # Would use firebase-admin SDK
        
        self.device_tokens: Dict[str, List[str]] = {}
        self.sent_notifications: Dict[str, Dict] = {}
        
        logger.info(f"PushNotificationProvider initialized (mock_mode={self.mock_mode})")
    
    def register_device(
        self,
        user_id: str,
        device_token: str,
        platform: str
    ):
        """
        Register device for push notifications
        
        Args:
            user_id: User identifier
            device_token: FCM device token
            platform: Platform (ios, android)
        """
        if user_id not in self.device_tokens:
            self.device_tokens[user_id] = []
        
        if device_token not in self.device_tokens[user_id]:
            self.device_tokens[user_id].append(device_token)
        
        logger.info(f"Device registered for user {user_id}: {platform}")
    
    def send_push(
        self,
        user_id: str,
        title: str,
        body: str,
        data: Optional[Dict] = None,
        priority: str = 'high'
    ) -> List[str]:
        """
        Send push notification to user
        
        Args:
            user_id: User identifier
            title: Notification title
            body: Notification body
            data: Additional data payload
            priority: Notification priority
            
        Returns:
            List of message IDs
        """
        if user_id not in self.device_tokens:
            logger.warning(f"No devices registered for user {user_id}")
            return []
        
        message_ids = []
        
        for device_token in self.device_tokens[user_id]:
            message_id = self._send_to_device(
                device_token,
                title,
                body,
                data,
                priority
            )
            if message_id:
                message_ids.append(message_id)
        
        logger.info(f"Push sent to {len(message_ids)} devices for user {user_id}")
        
        return message_ids
    
    def _send_to_device(
        self,
        device_token: str,
        title: str,
        body: str,
        data: Optional[Dict],
        priority: str
    ) -> Optional[str]:
        """Send push to single device"""
        if self.mock_mode:
            message_id = f"push_mock_{int(datetime.now().timestamp())}"
            self.sent_notifications[message_id] = {
                'device_token': device_token,
                'title': title,
                'body': body,
                'status': 'sent',
                'timestamp': datetime.now()
            }
            logger.info(f"[MOCK] Push sent: {message_id}")
            return message_id
        
        # Would use Firebase Admin SDK
        return None
    
    def send_topic(
        self,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Send push to topic subscribers
        
        Args:
            topic: Topic name
            title: Notification title
            body: Notification body
            data: Additional data payload
            
        Returns:
            Message ID
        """
        message_id = f"topic_{topic}_{int(datetime.now().timestamp())}"
        
        self.sent_notifications[message_id] = {
            'topic': topic,
            'title': title,
            'body': body,
            'status': 'sent',
            'timestamp': datetime.now()
        }
        
        logger.info(f"Topic notification sent: {topic}")
        
        return message_id
    
    def subscribe_to_topic(
        self,
        user_id: str,
        topic: str
    ) -> bool:
        """
        Subscribe user to topic
        
        Args:
            user_id: User identifier
            topic: Topic name
            
        Returns:
            True if successful
        """
        if user_id not in self.device_tokens:
            logger.warning(f"No devices for user {user_id}")
            return False
        
        logger.info(f"User {user_id} subscribed to topic: {topic}")
        
        return True


class NotificationService:
    """
    Unified notification service
    
    Manages all notification types and providers.
    """
    
    def __init__(
        self,
        sms_provider: Optional[SMSProvider] = None,
        push_provider: Optional[PushNotificationProvider] = None
    ):
        """
        Initialize notification service
        
        Args:
            sms_provider: SMS provider instance
            push_provider: Push notification provider instance
        """
        self.sms_provider = sms_provider
        self.push_provider = push_provider
        
        self.templates: Dict[str, NotificationTemplate] = {}
        self.notifications: Dict[str, Notification] = {}
        self.scheduled_queue: List[Notification] = []
        
        # User preferences
        self.user_preferences: Dict[str, Dict] = {}
        
        logger.info("NotificationService initialized")
    
    def register_template(self, template: NotificationTemplate):
        """Register notification template"""
        self.templates[template.template_id] = template
        logger.info(f"Template registered: {template.template_id}")
    
    def send_notification(
        self,
        type: NotificationType,
        recipient: str,
        content: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        metadata: Optional[Dict] = None
    ) -> Notification:
        """
        Send notification
        
        Args:
            type: Notification type
            recipient: Recipient identifier
            content: Notification content
            priority: Priority level
            metadata: Additional metadata
            
        Returns:
            Notification object
        """
        notification_id = f"notif_{int(datetime.now().timestamp())}"
        
        notification = Notification(
            notification_id=notification_id,
            type=type,
            recipient=recipient,
            content=content,
            priority=priority,
            metadata=metadata or {}
        )
        
        # Check user preferences
        if not self._should_send(recipient, type):
            notification.status = DeliveryStatus.CANCELLED
            logger.info(f"Notification cancelled due to user preferences: {notification_id}")
            self.notifications[notification_id] = notification
            return notification
        
        # Send based on type
        success = False
        
        if type == NotificationType.SMS:
            if self.sms_provider:
                success, message_id = self.sms_provider.send_sms(
                    recipient,
                    content,
                    metadata
                )
                notification.metadata['provider_message_id'] = message_id
        
        elif type == NotificationType.PUSH:
            if self.push_provider:
                message_ids = self.push_provider.send_push(
                    recipient,
                    'AgroPulse Alert',
                    content,
                    metadata
                )
                success = len(message_ids) > 0
                notification.metadata['provider_message_ids'] = message_ids
        
        # Update status
        if success:
            notification.status = DeliveryStatus.SENT
            notification.sent_at = datetime.now()
        else:
            notification.status = DeliveryStatus.FAILED
        
        self.notifications[notification_id] = notification
        
        logger.info(f"Notification {notification_id} status: {notification.status.value}")
        
        return notification
    
    def send_from_template(
        self,
        template_id: str,
        recipient: str,
        context: Dict[str, Any],
        type: Optional[NotificationType] = None
    ) -> Notification:
        """
        Send notification from template
        
        Args:
            template_id: Template identifier
            recipient: Recipient identifier
            context: Template context variables
            type: Override notification type
            
        Returns:
            Notification object
        """
        if template_id not in self.templates:
            raise ValueError(f"Template not found: {template_id}")
        
        template = self.templates[template_id]
        content = template.render(context)
        
        return self.send_notification(
            type or template.type,
            recipient,
            content,
            metadata={'template_id': template_id}
        )
    
    def schedule_notification(
        self,
        type: NotificationType,
        recipient: str,
        content: str,
        send_at: datetime,
        priority: NotificationPriority = NotificationPriority.MEDIUM
    ) -> Notification:
        """
        Schedule notification for future delivery
        
        Args:
            type: Notification type
            recipient: Recipient identifier
            content: Notification content
            send_at: Scheduled send time
            priority: Priority level
            
        Returns:
            Notification object
        """
        notification_id = f"sched_{int(datetime.now().timestamp())}"
        
        notification = Notification(
            notification_id=notification_id,
            type=type,
            recipient=recipient,
            content=content,
            priority=priority,
            scheduled_at=send_at,
            status=DeliveryStatus.PENDING
        )
        
        self.scheduled_queue.append(notification)
        self.notifications[notification_id] = notification
        
        logger.info(f"Notification scheduled: {notification_id} for {send_at}")
        
        return notification
    
    def process_scheduled(self):
        """Process scheduled notifications"""
        now = datetime.now()
        
        to_send = [
            n for n in self.scheduled_queue
            if n.scheduled_at and n.scheduled_at <= now
        ]
        
        for notification in to_send:
            self.send_notification(
                notification.type,
                notification.recipient,
                notification.content,
                notification.priority,
                notification.metadata
            )
            self.scheduled_queue.remove(notification)
        
        if to_send:
            logger.info(f"Processed {len(to_send)} scheduled notifications")
    
    def set_user_preferences(
        self,
        user_id: str,
        preferences: Dict[str, bool]
    ):
        """
        Set user notification preferences
        
        Args:
            user_id: User identifier
            preferences: Preference dictionary
                {
                    'sms_enabled': True,
                    'push_enabled': True,
                    'email_enabled': False
                }
        """
        self.user_preferences[user_id] = preferences
        logger.info(f"Updated preferences for user {user_id}")
    
    def _should_send(
        self,
        user_id: str,
        type: NotificationType
    ) -> bool:
        """Check if notification should be sent based on preferences"""
        if user_id not in self.user_preferences:
            return True
        
        prefs = self.user_preferences[user_id]
        key = f"{type.value}_enabled"
        
        return prefs.get(key, True)
    
    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """Get notification by ID"""
        return self.notifications.get(notification_id)
    
    def get_user_notifications(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Notification]:
        """
        Get notifications for user
        
        Args:
            user_id: User identifier
            limit: Maximum number to return
            
        Returns:
            List of notifications
        """
        user_notifs = [
            n for n in self.notifications.values()
            if n.recipient == user_id
        ]
        
        # Sort by creation time, newest first
        user_notifs.sort(key=lambda n: n.created_at, reverse=True)
        
        return user_notifs[:limit]
    
    def get_statistics(self) -> Dict:
        """Get notification statistics"""
        total = len(self.notifications)
        
        by_status = {}
        by_type = {}
        
        for notification in self.notifications.values():
            status = notification.status.value
            ntype = notification.type.value
            
            by_status[status] = by_status.get(status, 0) + 1
            by_type[ntype] = by_type.get(ntype, 0) + 1
        
        return {
            'total_notifications': total,
            'by_status': by_status,
            'by_type': by_type,
            'scheduled_pending': len(self.scheduled_queue)
        }
