# ======================================================================================================================
# AgroPulse NVR - Webhook Management System
# Webhook registration, delivery, retry, verification, event subscriptions
# ======================================================================================================================

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import hmac
import hashlib
import json
import aiohttp

logger = logging.getLogger(__name__)

# ======================================================================================================================
# WEBHOOK MODELS
# ======================================================================================================================

class WebhookEvent(Enum):
    """Webhook events"""
    DETECTION_CREATED = "detection.created"
    INCIDENT_CREATED = "incident.created"
    INCIDENT_UPDATED = "incident.updated"
    INCIDENT_RESOLVED = "incident.resolved"
    DEVICE_ONLINE = "device.online"
    DEVICE_OFFLINE = "device.offline"
    FARM_CREATED = "farm.created"
    FIELD_HEALTH_CHANGED = "field.health_changed"
    ALERT_TRIGGERED = "alert.triggered"
    PAYMENT_SUCCEEDED = "payment.succeeded"
    PAYMENT_FAILED = "payment.failed"
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_CANCELED = "subscription.canceled"

class WebhookStatus(Enum):
    """Webhook status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISABLED = "disabled"

class DeliveryStatus(Enum):
    """Delivery status"""
    PENDING = "pending"
    DELIVERING = "delivering"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"

@dataclass
class Webhook:
    """Webhook configuration"""
    webhook_id: str
    user_id: str
    url: str
    events: Set[WebhookEvent]
    secret: str
    status: WebhookStatus = WebhookStatus.ACTIVE
    description: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 60
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class WebhookDelivery:
    """Webhook delivery record"""
    delivery_id: str
    webhook_id: str
    event_type: WebhookEvent
    payload: Dict[str, Any]
    status: DeliveryStatus
    attempt_count: int = 0
    response_code: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    delivered_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class WebhookEvent:
    """Webhook event data"""
    event_id: str
    event_type: WebhookEvent
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)

# ======================================================================================================================
# WEBHOOK REGISTRY
# ======================================================================================================================

class WebhookRegistry:
    """Register and manage webhooks"""
    
    def __init__(self):
        self.webhooks: Dict[str, Webhook] = {}
        self.event_subscriptions: Dict[WebhookEvent, Set[str]] = {}
        
        logger.info("[WEBHOOK-REG] Webhook registry initialized")
    
    def register_webhook(self, webhook: Webhook) -> str:
        """Register webhook"""
        self.webhooks[webhook.webhook_id] = webhook
        
        # Add to event subscriptions
        for event in webhook.events:
            if event not in self.event_subscriptions:
                self.event_subscriptions[event] = set()
            self.event_subscriptions[event].add(webhook.webhook_id)
        
        logger.info(f"[WEBHOOK-REG] Registered: {webhook.webhook_id} ({len(webhook.events)} events)")
        return webhook.webhook_id
    
    def unregister_webhook(self, webhook_id: str):
        """Unregister webhook"""
        webhook = self.webhooks.get(webhook_id)
        if not webhook:
            return
        
        # Remove from event subscriptions
        for event in webhook.events:
            if event in self.event_subscriptions:
                self.event_subscriptions[event].discard(webhook_id)
        
        del self.webhooks[webhook_id]
        logger.info(f"[WEBHOOK-REG] Unregistered: {webhook_id}")
    
    def get_webhook(self, webhook_id: str) -> Optional[Webhook]:
        """Get webhook"""
        return self.webhooks.get(webhook_id)
    
    def get_webhooks_for_event(self, event: WebhookEvent) -> List[Webhook]:
        """Get webhooks subscribed to event"""
        webhook_ids = self.event_subscriptions.get(event, set())
        return [
            self.webhooks[wid] for wid in webhook_ids
            if wid in self.webhooks and self.webhooks[wid].status == WebhookStatus.ACTIVE
        ]
    
    def get_user_webhooks(self, user_id: str) -> List[Webhook]:
        """Get user's webhooks"""
        return [
            webhook for webhook in self.webhooks.values()
            if webhook.user_id == user_id
        ]
    
    def update_webhook(self, webhook_id: str, **updates):
        """Update webhook"""
        webhook = self.webhooks.get(webhook_id)
        if not webhook:
            return
        
        for key, value in updates.items():
            if hasattr(webhook, key):
                setattr(webhook, key, value)
        
        logger.info(f"[WEBHOOK-REG] Updated: {webhook_id}")
    
    def disable_webhook(self, webhook_id: str):
        """Disable webhook"""
        webhook = self.webhooks.get(webhook_id)
        if webhook:
            webhook.status = WebhookStatus.DISABLED
            logger.info(f"[WEBHOOK-REG] Disabled: {webhook_id}")

# ======================================================================================================================
# WEBHOOK SIGNATURE
# ======================================================================================================================

class WebhookSignature:
    """Generate and verify webhook signatures"""
    
    @staticmethod
    def generate_signature(payload: str, secret: str) -> str:
        """Generate HMAC signature"""
        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"sha256={signature}"
    
    @staticmethod
    def verify_signature(payload: str, secret: str, signature: str) -> bool:
        """Verify HMAC signature"""
        expected = WebhookSignature.generate_signature(payload, secret)
        return hmac.compare_digest(expected, signature)

# ======================================================================================================================
# WEBHOOK DELIVERY ENGINE
# ======================================================================================================================

class WebhookDeliveryEngine:
    """Deliver webhooks with retry logic"""
    
    def __init__(self):
        self.deliveries: Dict[str, WebhookDelivery] = {}
        self.delivery_queue: asyncio.Queue = asyncio.Queue()
        self.workers: List[asyncio.Task] = []
        self.running = False
        
        logger.info("[DELIVERY] Webhook delivery engine initialized")
    
    async def start(self, num_workers: int = 5):
        """Start delivery workers"""
        self.running = True
        
        for i in range(num_workers):
            worker = asyncio.create_task(self._delivery_worker(i))
            self.workers.append(worker)
        
        logger.info(f"[DELIVERY] Started {num_workers} workers")
    
    async def stop(self):
        """Stop delivery workers"""
        self.running = False
        
        for worker in self.workers:
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass
        
        self.workers.clear()
        logger.info("[DELIVERY] Stopped workers")
    
    async def _delivery_worker(self, worker_id: int):
        """Delivery worker"""
        logger.info(f"[DELIVERY-{worker_id}] Worker started")
        
        while self.running:
            try:
                delivery = await asyncio.wait_for(
                    self.delivery_queue.get(),
                    timeout=1.0
                )
                
                await self._deliver_webhook(delivery)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"[DELIVERY-{worker_id}] Worker error: {e}")
    
    async def queue_delivery(self, webhook: Webhook, event: WebhookEvent):
        """Queue webhook delivery"""
        delivery_id = f"del_{webhook.webhook_id}_{datetime.now().timestamp()}"
        
        # Prepare payload
        payload = {
            'event_id': event.event_id,
            'event_type': event.event_type.value,
            'data': event.data,
            'timestamp': event.timestamp.isoformat(),
            'webhook_id': webhook.webhook_id
        }
        
        delivery = WebhookDelivery(
            delivery_id=delivery_id,
            webhook_id=webhook.webhook_id,
            event_type=event.event_type,
            payload=payload,
            status=DeliveryStatus.PENDING
        )
        
        self.deliveries[delivery_id] = delivery
        await self.delivery_queue.put(delivery)
        
        logger.debug(f"[DELIVERY] Queued: {delivery_id}")
    
    async def _deliver_webhook(self, delivery: WebhookDelivery):
        """Deliver webhook"""
        webhook = None  # Would get from registry
        
        # Simulate webhook retrieval
        webhook_url = "https://example.com/webhook"
        webhook_secret = "secret"
        webhook_timeout = 30
        webhook_max_retries = 3
        
        delivery.status = DeliveryStatus.DELIVERING
        delivery.attempt_count += 1
        
        try:
            # Prepare payload
            payload_str = json.dumps(delivery.payload)
            
            # Generate signature
            signature = WebhookSignature.generate_signature(payload_str, webhook_secret)
            
            # Send webhook
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Content-Type': 'application/json',
                    'X-Webhook-Signature': signature,
                    'X-Webhook-Delivery-ID': delivery.delivery_id,
                    'X-Webhook-Event': delivery.event_type.value
                }
                
                async with session.post(
                    webhook_url,
                    data=payload_str,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=webhook_timeout)
                ) as response:
                    delivery.response_code = response.status
                    delivery.response_body = await response.text()
                    
                    if 200 <= response.status < 300:
                        delivery.status = DeliveryStatus.DELIVERED
                        delivery.delivered_at = datetime.now()
                        logger.info(f"[DELIVERY] Delivered: {delivery.delivery_id}")
                    else:
                        raise Exception(f"HTTP {response.status}")
        
        except Exception as e:
            delivery.status = DeliveryStatus.FAILED
            delivery.error_message = str(e)
            logger.error(f"[DELIVERY] Failed: {delivery.delivery_id} - {e}")
            
            # Retry if possible
            if delivery.attempt_count < webhook_max_retries:
                delivery.status = DeliveryStatus.RETRYING
                await asyncio.sleep(60)  # Wait before retry
                await self.delivery_queue.put(delivery)
    
    def get_delivery(self, delivery_id: str) -> Optional[WebhookDelivery]:
        """Get delivery record"""
        return self.deliveries.get(delivery_id)
    
    def get_webhook_deliveries(self, webhook_id: str,
                               limit: int = 100) -> List[WebhookDelivery]:
        """Get webhook deliveries"""
        deliveries = [
            d for d in self.deliveries.values()
            if d.webhook_id == webhook_id
        ]
        
        # Sort by created_at descending
        deliveries.sort(key=lambda d: d.created_at, reverse=True)
        
        return deliveries[:limit]

# ======================================================================================================================
# WEBHOOK EVENT PUBLISHER
# ======================================================================================================================

class WebhookEventPublisher:
    """Publish events to webhooks"""
    
    def __init__(self, registry: WebhookRegistry,
                 delivery_engine: WebhookDeliveryEngine):
        self.registry = registry
        self.delivery_engine = delivery_engine
        
        logger.info("[PUBLISHER] Webhook event publisher initialized")
    
    async def publish_event(self, event_type: WebhookEvent, data: Dict[str, Any]):
        """Publish event to webhooks"""
        event = WebhookEvent(
            event_id=f"evt_{datetime.now().timestamp()}",
            event_type=event_type,
            data=data
        )
        
        # Get webhooks subscribed to this event
        webhooks = self.registry.get_webhooks_for_event(event_type)
        
        # Queue deliveries
        for webhook in webhooks:
            await self.delivery_engine.queue_delivery(webhook, event)
        
        logger.info(f"[PUBLISHER] Published {event_type.value} to {len(webhooks)} webhooks")
    
    async def publish_detection_created(self, detection_data: Dict[str, Any]):
        """Publish detection created event"""
        await self.publish_event(WebhookEvent.DETECTION_CREATED, detection_data)
    
    async def publish_incident_created(self, incident_data: Dict[str, Any]):
        """Publish incident created event"""
        await self.publish_event(WebhookEvent.INCIDENT_CREATED, incident_data)
    
    async def publish_device_status(self, device_id: str, online: bool):
        """Publish device status event"""
        event_type = WebhookEvent.DEVICE_ONLINE if online else WebhookEvent.DEVICE_OFFLINE
        await self.publish_event(event_type, {'device_id': device_id})

# ======================================================================================================================
# WEBHOOK ANALYTICS
# ======================================================================================================================

class WebhookAnalytics:
    """Webhook delivery analytics"""
    
    def __init__(self, delivery_engine: WebhookDeliveryEngine):
        self.delivery_engine = delivery_engine
        
        logger.info("[ANALYTICS] Webhook analytics initialized")
    
    def get_delivery_stats(self, webhook_id: Optional[str] = None) -> Dict[str, Any]:
        """Get delivery statistics"""
        deliveries = (
            self.delivery_engine.get_webhook_deliveries(webhook_id)
            if webhook_id
            else list(self.delivery_engine.deliveries.values())
        )
        
        total = len(deliveries)
        delivered = len([d for d in deliveries if d.status == DeliveryStatus.DELIVERED])
        failed = len([d for d in deliveries if d.status == DeliveryStatus.FAILED])
        pending = len([d for d in deliveries if d.status in [DeliveryStatus.PENDING, DeliveryStatus.RETRYING]])
        
        return {
            'total_deliveries': total,
            'delivered': delivered,
            'failed': failed,
            'pending': pending,
            'success_rate': (delivered / total * 100) if total > 0 else 0
        }
    
    def get_failure_reasons(self, webhook_id: str) -> List[Dict[str, Any]]:
        """Get failure reasons"""
        deliveries = self.delivery_engine.get_webhook_deliveries(webhook_id)
        failed = [d for d in deliveries if d.status == DeliveryStatus.FAILED]
        
        reasons = {}
        for delivery in failed:
            error = delivery.error_message or 'Unknown'
            if error not in reasons:
                reasons[error] = 0
            reasons[error] += 1
        
        return [
            {'reason': reason, 'count': count}
            for reason, count in sorted(reasons.items(), key=lambda x: x[1], reverse=True)
        ]

# ======================================================================================================================
# WEBHOOK ORCHESTRATOR
# ======================================================================================================================

class WebhookOrchestrator:
    """Main webhook orchestrator"""
    
    def __init__(self):
        self.registry = WebhookRegistry()
        self.delivery_engine = WebhookDeliveryEngine()
        self.publisher = WebhookEventPublisher(self.registry, self.delivery_engine)
        self.analytics = WebhookAnalytics(self.delivery_engine)
        
        logger.info("[WEBHOOK-ORCH] Webhook orchestrator initialized")
    
    async def start(self, num_workers: int = 5):
        """Start webhook system"""
        await self.delivery_engine.start(num_workers)
    
    async def stop(self):
        """Stop webhook system"""
        await self.delivery_engine.stop()
    
    def create_webhook(self, user_id: str, url: str,
                      events: List[WebhookEvent],
                      secret: Optional[str] = None) -> str:
        """Create webhook"""
        webhook_id = f"whk_{user_id}_{datetime.now().timestamp()}"
        
        # Generate secret if not provided
        if not secret:
            secret = hashlib.sha256(f"{webhook_id}{datetime.now()}".encode()).hexdigest()
        
        webhook = Webhook(
            webhook_id=webhook_id,
            user_id=user_id,
            url=url,
            events=set(events),
            secret=secret
        )
        
        self.registry.register_webhook(webhook)
        return webhook_id
    
    def delete_webhook(self, webhook_id: str):
        """Delete webhook"""
        self.registry.unregister_webhook(webhook_id)
    
    def update_webhook(self, webhook_id: str, **updates):
        """Update webhook"""
        self.registry.update_webhook(webhook_id, **updates)
    
    async def publish_event(self, event_type: WebhookEvent, data: Dict[str, Any]):
        """Publish event"""
        await self.publisher.publish_event(event_type, data)
    
    def get_webhook(self, webhook_id: str) -> Optional[Webhook]:
        """Get webhook"""
        return self.registry.get_webhook(webhook_id)
    
    def get_user_webhooks(self, user_id: str) -> List[Webhook]:
        """Get user webhooks"""
        return self.registry.get_user_webhooks(user_id)
    
    def get_delivery_history(self, webhook_id: str) -> List[WebhookDelivery]:
        """Get delivery history"""
        return self.delivery_engine.get_webhook_deliveries(webhook_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get webhook statistics"""
        return {
            'total_webhooks': len(self.registry.webhooks),
            'active_webhooks': len([
                w for w in self.registry.webhooks.values()
                if w.status == WebhookStatus.ACTIVE
            ]),
            'delivery_stats': self.analytics.get_delivery_stats(),
            'queue_size': self.delivery_engine.delivery_queue.qsize()
        }

# ======================================================================================================================
# END OF WEBHOOK MANAGEMENT MODULE
# Lines in this file: ~550+
# Combined total: ~32,700+
# Remaining for 50k: ~17,300 lines
# ======================================================================================================================
