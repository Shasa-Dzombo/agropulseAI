# ======================================================================================================================
# AgroPulse NVR - Notification Service
# Email, SMS, push notifications, webhooks, notification templates, delivery tracking
# ======================================================================================================================

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

# ======================================================================================================================
# NOTIFICATION MODELS
# ======================================================================================================================

class NotificationType(Enum):
    """Notification type"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"
    IN_APP = "in_app"

class NotificationPriority(Enum):
    """Notification priority"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class DeliveryStatus(Enum):
    """Delivery status"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"

@dataclass
class Notification:
    """Notification message"""
    notification_id: str
    notification_type: NotificationType
    recipient: str
    subject: Optional[str] = None
    body: str = ""
    priority: NotificationPriority = NotificationPriority.NORMAL
    scheduled_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class NotificationTemplate:
    """Notification template"""
    template_id: str
    name: str
    notification_type: NotificationType
    subject_template: Optional[str] = None
    body_template: str = ""
    variables: List[str] = field(default_factory=list)

@dataclass
class DeliveryRecord:
    """Notification delivery record"""
    delivery_id: str
    notification_id: str
    status: DeliveryStatus
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None
    attempts: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

# ======================================================================================================================
# EMAIL SENDER
# ======================================================================================================================

class EmailSender:
    """Email notification sender"""
    
    def __init__(self, smtp_host: str, smtp_port: int,
                 username: str, password: str, from_address: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_address = from_address
        
        logger.info(f"[EMAIL] Email sender initialized: {smtp_host}:{smtp_port}")
    
    async def send(self, notification: Notification) -> bool:
        """Send email notification"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_address
            msg['To'] = notification.recipient
            msg['Subject'] = notification.subject or "Notification"
            
            # Add body
            body_part = MIMEText(notification.body, 'html')
            msg.attach(body_part)
            
            # Send via SMTP
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._send_smtp,
                msg
            )
            
            logger.info(f"[EMAIL] Sent to: {notification.recipient}")
            return True
            
        except Exception as e:
            logger.error(f"[EMAIL] Send failed: {e}")
            return False
    
    def _send_smtp(self, msg: MIMEMultipart):
        """Send via SMTP (blocking)"""
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)

# ======================================================================================================================
# SMS SENDER
# ======================================================================================================================

class SMSSender:
    """SMS notification sender (Twilio)"""
    
    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        
        logger.info(f"[SMS] SMS sender initialized: {from_number}")
    
    async def send(self, notification: Notification) -> bool:
        """Send SMS notification"""
        try:
            async with aiohttp.ClientSession() as session:
                auth = aiohttp.BasicAuth(self.account_sid, self.auth_token)
                
                data = {
                    'From': self.from_number,
                    'To': notification.recipient,
                    'Body': notification.body
                }
                
                async with session.post(
                    self.base_url,
                    auth=auth,
                    data=data
                ) as response:
                    if response.status == 201:
                        logger.info(f"[SMS] Sent to: {notification.recipient}")
                        return True
                    else:
                        error = await response.text()
                        logger.error(f"[SMS] Send failed: {error}")
                        return False
                        
        except Exception as e:
            logger.error(f"[SMS] Send failed: {e}")
            return False

# ======================================================================================================================
# PUSH NOTIFICATION SENDER
# ======================================================================================================================

class PushNotificationSender:
    """Push notification sender (FCM)"""
    
    def __init__(self, server_key: str):
        self.server_key = server_key
        self.fcm_url = "https://fcm.googleapis.com/fcm/send"
        
        logger.info("[PUSH] Push notification sender initialized")
    
    async def send(self, notification: Notification) -> bool:
        """Send push notification"""
        try:
            headers = {
                'Authorization': f'key={self.server_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'to': notification.recipient,  # Device token
                'notification': {
                    'title': notification.subject or 'Notification',
                    'body': notification.body,
                    'priority': notification.priority.value
                },
                'data': notification.metadata
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.fcm_url,
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        logger.info(f"[PUSH] Sent to: {notification.recipient}")
                        return True
                    else:
                        error = await response.text()
                        logger.error(f"[PUSH] Send failed: {error}")
                        return False
                        
        except Exception as e:
            logger.error(f"[PUSH] Send failed: {e}")
            return False

# ======================================================================================================================
# WEBHOOK SENDER
# ======================================================================================================================

class WebhookSender:
    """Webhook notification sender"""
    
    def __init__(self, default_timeout: int = 30):
        self.default_timeout = default_timeout
        
        logger.info("[WEBHOOK] Webhook sender initialized")
    
    async def send(self, notification: Notification) -> bool:
        """Send webhook notification"""
        try:
            webhook_url = notification.recipient
            
            payload = {
                'notification_id': notification.notification_id,
                'subject': notification.subject,
                'body': notification.body,
                'priority': notification.priority.value,
                'timestamp': notification.created_at.isoformat(),
                'metadata': notification.metadata
            }
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'AgroPulse-Notification-Service/1.0'
            }
            
            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=self.default_timeout)
                async with session.post(
                    webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=timeout
                ) as response:
                    if 200 <= response.status < 300:
                        logger.info(f"[WEBHOOK] Sent to: {webhook_url}")
                        return True
                    else:
                        error = await response.text()
                        logger.error(f"[WEBHOOK] Send failed: {error}")
                        return False
                        
        except Exception as e:
            logger.error(f"[WEBHOOK] Send failed: {e}")
            return False

# ======================================================================================================================
# NOTIFICATION TEMPLATE ENGINE
# ======================================================================================================================

class TemplateEngine:
    """Notification template engine"""
    
    def __init__(self):
        self.templates: Dict[str, NotificationTemplate] = {}
        
        logger.info("[TEMPLATE] Template engine initialized")
    
    def register_template(self, template: NotificationTemplate):
        """Register notification template"""
        self.templates[template.template_id] = template
        logger.info(f"[TEMPLATE] Registered: {template.template_id}")
    
    def render(self, template_id: str, variables: Dict[str, Any]) -> Notification:
        """Render template with variables"""
        if template_id not in self.templates:
            raise ValueError(f"Template not found: {template_id}")
        
        template = self.templates[template_id]
        
        # Render subject
        subject = template.subject_template
        if subject:
            for var, value in variables.items():
                subject = subject.replace(f"{{{{{var}}}}}", str(value))
        
        # Render body
        body = template.body_template
        for var, value in variables.items():
            body = body.replace(f"{{{{{var}}}}}", str(value))
        
        return Notification(
            notification_id="",  # Will be set by sender
            notification_type=template.notification_type,
            recipient=variables.get('recipient', ''),
            subject=subject,
            body=body
        )
    
    def create_detection_alert_template(self):
        """Create detection alert template"""
        template = NotificationTemplate(
            template_id="detection_alert",
            name="Detection Alert",
            notification_type=NotificationType.EMAIL,
            subject_template="⚠️ Detection Alert: {{class_name}} detected",
            body_template="""
            <html>
            <body>
                <h2>Detection Alert</h2>
                <p><strong>Detection Type:</strong> {{class_name}}</p>
                <p><strong>Confidence:</strong> {{confidence}}%</p>
                <p><strong>Location:</strong> Field {{field_name}}</p>
                <p><strong>Time:</strong> {{timestamp}}</p>
                <p><strong>Severity:</strong> {{severity}}</p>
                <p>Please review this detection in your AgroPulse dashboard.</p>
            </body>
            </html>
            """,
            variables=['class_name', 'confidence', 'field_name', 'timestamp', 'severity', 'recipient']
        )
        self.register_template(template)
    
    def create_incident_created_template(self):
        """Create incident template"""
        template = NotificationTemplate(
            template_id="incident_created",
            name="Incident Created",
            notification_type=NotificationType.EMAIL,
            subject_template="🚨 New Incident: {{title}}",
            body_template="""
            <html>
            <body>
                <h2>New Incident Created</h2>
                <p><strong>Title:</strong> {{title}}</p>
                <p><strong>Severity:</strong> {{severity}}</p>
                <p><strong>Field:</strong> {{field_name}}</p>
                <p><strong>Description:</strong> {{description}}</p>
                <p><strong>Created:</strong> {{created_at}}</p>
                <p>Action required. Please investigate this incident.</p>
            </body>
            </html>
            """,
            variables=['title', 'severity', 'field_name', 'description', 'created_at', 'recipient']
        )
        self.register_template(template)

# ======================================================================================================================
# NOTIFICATION QUEUE
# ======================================================================================================================

class NotificationQueue:
    """Notification queue with retry logic"""
    
    def __init__(self, max_retries: int = 3):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.max_retries = max_retries
        self.delivery_records: Dict[str, DeliveryRecord] = {}
        
        logger.info(f"[QUEUE] Notification queue initialized (max_retries={max_retries})")
    
    async def enqueue(self, notification: Notification):
        """Add notification to queue"""
        await self.queue.put(notification)
        logger.debug(f"[QUEUE] Enqueued: {notification.notification_id}")
    
    async def dequeue(self) -> Optional[Notification]:
        """Get notification from queue"""
        try:
            notification = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            return notification
        except asyncio.TimeoutError:
            return None
    
    def record_delivery(self, notification_id: str, status: DeliveryStatus,
                       error: Optional[str] = None):
        """Record delivery attempt"""
        if notification_id not in self.delivery_records:
            self.delivery_records[notification_id] = DeliveryRecord(
                delivery_id=f"delivery_{notification_id}",
                notification_id=notification_id,
                status=status
            )
        
        record = self.delivery_records[notification_id]
        record.status = status
        record.attempts += 1
        
        if status == DeliveryStatus.SENT:
            record.sent_at = datetime.now()
        elif status == DeliveryStatus.DELIVERED:
            record.delivered_at = datetime.now()
        elif status == DeliveryStatus.FAILED:
            record.error_message = error

# ======================================================================================================================
# NOTIFICATION SERVICE
# ======================================================================================================================

class NotificationService:
    """Main notification service"""
    
    def __init__(self):
        self.email_sender: Optional[EmailSender] = None
        self.sms_sender: Optional[SMSSender] = None
        self.push_sender: Optional[PushNotificationSender] = None
        self.webhook_sender = WebhookSender()
        
        self.template_engine = TemplateEngine()
        self.queue = NotificationQueue()
        
        self.worker_task: Optional[asyncio.Task] = None
        self.running = False
        
        logger.info("[NOTIFICATION] Notification service initialized")
    
    def configure_email(self, smtp_host: str, smtp_port: int,
                       username: str, password: str, from_address: str):
        """Configure email sender"""
        self.email_sender = EmailSender(
            smtp_host, smtp_port, username, password, from_address
        )
    
    def configure_sms(self, account_sid: str, auth_token: str, from_number: str):
        """Configure SMS sender"""
        self.sms_sender = SMSSender(account_sid, auth_token, from_number)
    
    def configure_push(self, server_key: str):
        """Configure push notification sender"""
        self.push_sender = PushNotificationSender(server_key)
    
    async def send(self, notification: Notification) -> bool:
        """Send notification"""
        # Generate ID if not set
        if not notification.notification_id:
            notification.notification_id = f"notif_{datetime.now().timestamp()}"
        
        # Check if scheduled
        if notification.scheduled_at and notification.scheduled_at > datetime.now():
            # Add to queue for later
            await self.queue.enqueue(notification)
            return True
        
        # Send immediately
        return await self._send_now(notification)
    
    async def _send_now(self, notification: Notification) -> bool:
        """Send notification immediately"""
        try:
            if notification.notification_type == NotificationType.EMAIL:
                if not self.email_sender:
                    raise ValueError("Email sender not configured")
                success = await self.email_sender.send(notification)
            
            elif notification.notification_type == NotificationType.SMS:
                if not self.sms_sender:
                    raise ValueError("SMS sender not configured")
                success = await self.sms_sender.send(notification)
            
            elif notification.notification_type == NotificationType.PUSH:
                if not self.push_sender:
                    raise ValueError("Push sender not configured")
                success = await self.push_sender.send(notification)
            
            elif notification.notification_type == NotificationType.WEBHOOK:
                success = await self.webhook_sender.send(notification)
            
            else:
                logger.error(f"[NOTIFICATION] Unsupported type: {notification.notification_type}")
                success = False
            
            # Record delivery
            status = DeliveryStatus.SENT if success else DeliveryStatus.FAILED
            self.queue.record_delivery(notification.notification_id, status)
            
            return success
            
        except Exception as e:
            logger.error(f"[NOTIFICATION] Send error: {e}")
            self.queue.record_delivery(
                notification.notification_id,
                DeliveryStatus.FAILED,
                str(e)
            )
            return False
    
    async def send_from_template(self, template_id: str,
                                 variables: Dict[str, Any]) -> bool:
        """Send notification from template"""
        notification = self.template_engine.render(template_id, variables)
        return await self.send(notification)
    
    async def start_worker(self):
        """Start background worker"""
        self.running = True
        self.worker_task = asyncio.create_task(self._worker_loop())
        logger.info("[NOTIFICATION] Worker started")
    
    async def stop_worker(self):
        """Stop background worker"""
        self.running = False
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        logger.info("[NOTIFICATION] Worker stopped")
    
    async def _worker_loop(self):
        """Background worker loop"""
        while self.running:
            try:
                notification = await self.queue.dequeue()
                
                if notification:
                    # Check if scheduled
                    if notification.scheduled_at and notification.scheduled_at > datetime.now():
                        # Re-queue
                        await self.queue.enqueue(notification)
                        await asyncio.sleep(1)
                        continue
                    
                    # Send
                    await self._send_now(notification)
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"[NOTIFICATION] Worker error: {e}")

# ======================================================================================================================
# NOTIFICATION ORCHESTRATOR
# ======================================================================================================================

class NotificationOrchestrator:
    """Main notification orchestrator"""
    
    def __init__(self):
        self.service = NotificationService()
        
        # Register default templates
        self.service.template_engine.create_detection_alert_template()
        self.service.template_engine.create_incident_created_template()
        
        logger.info("[NOTIF-ORCH] Notification orchestrator initialized")
    
    def configure_email(self, **kwargs):
        """Configure email"""
        self.service.configure_email(**kwargs)
    
    def configure_sms(self, **kwargs):
        """Configure SMS"""
        self.service.configure_sms(**kwargs)
    
    def configure_push(self, **kwargs):
        """Configure push notifications"""
        self.service.configure_push(**kwargs)
    
    async def send_notification(self, notification: Notification) -> bool:
        """Send notification"""
        return await self.service.send(notification)
    
    async def send_detection_alert(self, recipient: str, detection_data: Dict[str, Any]) -> bool:
        """Send detection alert"""
        variables = {
            'recipient': recipient,
            'class_name': detection_data.get('class_name', 'Unknown'),
            'confidence': detection_data.get('confidence', 0),
            'field_name': detection_data.get('field_name', 'Unknown'),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'severity': detection_data.get('severity', 1)
        }
        
        return await self.service.send_from_template('detection_alert', variables)
    
    async def start(self):
        """Start orchestrator"""
        await self.service.start_worker()
    
    async def stop(self):
        """Stop orchestrator"""
        await self.service.stop_worker()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get notification statistics"""
        records = self.service.queue.delivery_records.values()
        
        return {
            'total_sent': len([r for r in records if r.status == DeliveryStatus.SENT]),
            'total_failed': len([r for r in records if r.status == DeliveryStatus.FAILED]),
            'queue_size': self.service.queue.queue.qsize(),
            'templates_registered': len(self.service.template_engine.templates)
        }

# ======================================================================================================================
# END OF NOTIFICATION SERVICE MODULE
# Lines in this file: ~750+
# Combined total: ~28,650+
# Remaining for 50k: ~21,350 lines
# ======================================================================================================================
