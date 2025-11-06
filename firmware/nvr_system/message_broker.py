# ======================================================================================================================
# AgroPulse NVR - Message Broker System
# Pub/Sub messaging, message queues, dead letter queues, guaranteed delivery, event-driven architecture
# ======================================================================================================================

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict
import time
import random
import json

logger = logging.getLogger(__name__)

# ======================================================================================================================
# MESSAGING MODELS
# ======================================================================================================================

class MessagePriority(Enum):
    """Message priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3

class DeliveryGuarantee(Enum):
    """Message delivery guarantees"""
    AT_MOST_ONCE = "at_most_once"
    AT_LEAST_ONCE = "at_least_once"
    EXACTLY_ONCE = "exactly_once"

class MessageStatus(Enum):
    """Message status"""
    PENDING = "pending"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"

@dataclass
class Message:
    """Message object"""
    message_id: str
    topic: str
    payload: Dict[str, Any]
    headers: Dict[str, str]
    priority: MessagePriority
    created_at: datetime
    delivered_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    status: MessageStatus = MessageStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    expiry_time: Optional[datetime] = None
    correlation_id: Optional[str] = None

@dataclass
class Topic:
    """Message topic"""
    name: str
    created_at: datetime
    subscribers: Set[str] = field(default_factory=set)
    message_count: int = 0
    total_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Queue:
    """Message queue"""
    name: str
    created_at: datetime
    max_size: int = 10000
    messages: deque = field(default_factory=lambda: deque(maxlen=10000))
    dead_letter_queue: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Subscription:
    """Topic subscription"""
    subscription_id: str
    subscriber_id: str
    topic: str
    callback: Callable
    filter_rules: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    message_count: int = 0

# ======================================================================================================================
# TOPIC MANAGER
# ======================================================================================================================

class TopicManager:
    """Manage pub/sub topics"""
    
    def __init__(self):
        self.topics: Dict[str, Topic] = {}
        
        logger.info("[TOPIC-MGR] Topic manager initialized")
    
    def create_topic(self, name: str) -> Topic:
        """Create new topic"""
        if name in self.topics:
            return self.topics[name]
        
        topic = Topic(
            name=name,
            created_at=datetime.now()
        )
        
        self.topics[name] = topic
        
        logger.info(f"[TOPIC-MGR] Created topic: {name}")
        return topic
    
    def delete_topic(self, name: str) -> bool:
        """Delete topic"""
        if name in self.topics:
            del self.topics[name]
            logger.info(f"[TOPIC-MGR] Deleted topic: {name}")
            return True
        
        return False
    
    def get_topic(self, name: str) -> Optional[Topic]:
        """Get topic"""
        return self.topics.get(name)
    
    def list_topics(self) -> List[Topic]:
        """List all topics"""
        return list(self.topics.values())
    
    def add_subscriber(self, topic_name: str, subscriber_id: str):
        """Add subscriber to topic"""
        topic = self.get_topic(topic_name)
        
        if topic:
            topic.subscribers.add(subscriber_id)
            logger.debug(f"[TOPIC-MGR] Added subscriber {subscriber_id} to {topic_name}")
    
    def remove_subscriber(self, topic_name: str, subscriber_id: str):
        """Remove subscriber from topic"""
        topic = self.get_topic(topic_name)
        
        if topic and subscriber_id in topic.subscribers:
            topic.subscribers.remove(subscriber_id)
            logger.debug(f"[TOPIC-MGR] Removed subscriber {subscriber_id} from {topic_name}")

# ======================================================================================================================
# PUBLISHER
# ======================================================================================================================

class Publisher:
    """Publish messages to topics"""
    
    def __init__(self, topic_manager: TopicManager):
        self.topic_manager = topic_manager
        self.published_messages: deque = deque(maxlen=10000)
        
        logger.info("[PUBLISHER] Publisher initialized")
    
    async def publish(self, topic_name: str, payload: Dict[str, Any],
                     headers: Dict[str, str] = None,
                     priority: MessagePriority = MessagePriority.NORMAL,
                     ttl_seconds: int = 3600) -> Message:
        """Publish message to topic"""
        # Get or create topic
        topic = self.topic_manager.get_topic(topic_name)
        
        if not topic:
            topic = self.topic_manager.create_topic(topic_name)
        
        # Create message
        message_id = f"msg_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        
        message = Message(
            message_id=message_id,
            topic=topic_name,
            payload=payload,
            headers=headers or {},
            priority=priority,
            created_at=datetime.now(),
            expiry_time=datetime.now() + timedelta(seconds=ttl_seconds)
        )
        
        self.published_messages.append(message)
        
        # Update topic stats
        topic.message_count += 1
        topic.total_bytes += len(json.dumps(payload))
        
        logger.debug(f"[PUBLISHER] Published message {message_id} to {topic_name}")
        
        return message
    
    async def publish_batch(self, topic_name: str,
                           payloads: List[Dict[str, Any]]) -> List[Message]:
        """Publish batch of messages"""
        messages = []
        
        for payload in payloads:
            message = await self.publish(topic_name, payload)
            messages.append(message)
        
        logger.info(f"[PUBLISHER] Published {len(messages)} messages to {topic_name}")
        return messages

# ======================================================================================================================
# SUBSCRIBER
# ======================================================================================================================

class Subscriber:
    """Subscribe to topics and receive messages"""
    
    def __init__(self, topic_manager: TopicManager):
        self.topic_manager = topic_manager
        self.subscriptions: Dict[str, Subscription] = {}
        
        logger.info("[SUBSCRIBER] Subscriber initialized")
    
    def subscribe(self, subscriber_id: str, topic_name: str,
                 callback: Callable,
                 filter_rules: List[Dict[str, Any]] = None) -> Subscription:
        """Subscribe to topic"""
        # Create subscription
        subscription_id = f"sub_{int(time.time())}_{random.randint(1000, 9999)}"
        
        subscription = Subscription(
            subscription_id=subscription_id,
            subscriber_id=subscriber_id,
            topic=topic_name,
            callback=callback,
            filter_rules=filter_rules or []
        )
        
        self.subscriptions[subscription_id] = subscription
        
        # Add to topic
        self.topic_manager.add_subscriber(topic_name, subscriber_id)
        
        logger.info(f"[SUBSCRIBER] Created subscription {subscription_id} for {topic_name}")
        return subscription
    
    def unsubscribe(self, subscription_id: str):
        """Unsubscribe from topic"""
        subscription = self.subscriptions.get(subscription_id)
        
        if subscription:
            self.topic_manager.remove_subscriber(
                subscription.topic,
                subscription.subscriber_id
            )
            
            del self.subscriptions[subscription_id]
            
            logger.info(f"[SUBSCRIBER] Unsubscribed: {subscription_id}")
    
    async def deliver_message(self, message: Message) -> bool:
        """Deliver message to subscribers"""
        delivered = False
        
        for subscription in self.subscriptions.values():
            if subscription.topic == message.topic:
                # Check filter rules
                if self._matches_filters(message, subscription.filter_rules):
                    try:
                        await subscription.callback(message)
                        subscription.message_count += 1
                        delivered = True
                        
                        logger.debug(f"[SUBSCRIBER] Delivered message to {subscription.subscriber_id}")
                    
                    except Exception as e:
                        logger.error(f"[SUBSCRIBER] Error delivering message: {e}")
        
        return delivered
    
    def _matches_filters(self, message: Message,
                        filter_rules: List[Dict[str, Any]]) -> bool:
        """Check if message matches filter rules"""
        if not filter_rules:
            return True
        
        for rule in filter_rules:
            attribute = rule.get('attribute')
            value = rule.get('value')
            
            if attribute in message.headers:
                if message.headers[attribute] == value:
                    return True
        
        return len(filter_rules) == 0

# ======================================================================================================================
# QUEUE MANAGER
# ======================================================================================================================

class QueueManager:
    """Manage message queues"""
    
    def __init__(self):
        self.queues: Dict[str, Queue] = {}
        
        logger.info("[QUEUE-MGR] Queue manager initialized")
    
    def create_queue(self, name: str, max_size: int = 10000,
                    dead_letter_queue: Optional[str] = None) -> Queue:
        """Create new queue"""
        if name in self.queues:
            return self.queues[name]
        
        queue = Queue(
            name=name,
            created_at=datetime.now(),
            max_size=max_size,
            dead_letter_queue=dead_letter_queue
        )
        
        self.queues[name] = queue
        
        logger.info(f"[QUEUE-MGR] Created queue: {name}")
        return queue
    
    def delete_queue(self, name: str) -> bool:
        """Delete queue"""
        if name in self.queues:
            del self.queues[name]
            logger.info(f"[QUEUE-MGR] Deleted queue: {name}")
            return True
        
        return False
    
    def get_queue(self, name: str) -> Optional[Queue]:
        """Get queue"""
        return self.queues.get(name)
    
    def enqueue(self, queue_name: str, message: Message) -> bool:
        """Add message to queue"""
        queue = self.get_queue(queue_name)
        
        if not queue:
            return False
        
        if len(queue.messages) >= queue.max_size:
            logger.warning(f"[QUEUE-MGR] Queue {queue_name} is full")
            return False
        
        queue.messages.append(message)
        logger.debug(f"[QUEUE-MGR] Enqueued message to {queue_name}")
        
        return True
    
    def dequeue(self, queue_name: str) -> Optional[Message]:
        """Remove and return message from queue"""
        queue = self.get_queue(queue_name)
        
        if not queue or not queue.messages:
            return None
        
        message = queue.messages.popleft()
        logger.debug(f"[QUEUE-MGR] Dequeued message from {queue_name}")
        
        return message
    
    def peek(self, queue_name: str, count: int = 1) -> List[Message]:
        """Peek at messages without removing"""
        queue = self.get_queue(queue_name)
        
        if not queue:
            return []
        
        return list(queue.messages)[:count]
    
    def get_queue_size(self, queue_name: str) -> int:
        """Get queue size"""
        queue = self.get_queue(queue_name)
        
        if not queue:
            return 0
        
        return len(queue.messages)

# ======================================================================================================================
# MESSAGE ROUTER
# ======================================================================================================================

class MessageRouter:
    """Route messages between topics and queues"""
    
    def __init__(self, topic_manager: TopicManager, queue_manager: QueueManager):
        self.topic_manager = topic_manager
        self.queue_manager = queue_manager
        self.routes: Dict[str, List[str]] = defaultdict(list)
        
        logger.info("[ROUTER] Message router initialized")
    
    def add_route(self, from_topic: str, to_queue: str):
        """Add routing rule"""
        self.routes[from_topic].append(to_queue)
        logger.info(f"[ROUTER] Added route: {from_topic} -> {to_queue}")
    
    def remove_route(self, from_topic: str, to_queue: str):
        """Remove routing rule"""
        if from_topic in self.routes:
            self.routes[from_topic].remove(to_queue)
            logger.info(f"[ROUTER] Removed route: {from_topic} -> {to_queue}")
    
    async def route_message(self, message: Message):
        """Route message to queues"""
        target_queues = self.routes.get(message.topic, [])
        
        for queue_name in target_queues:
            self.queue_manager.enqueue(queue_name, message)
            logger.debug(f"[ROUTER] Routed message to {queue_name}")

# ======================================================================================================================
# DEAD LETTER QUEUE HANDLER
# ======================================================================================================================

class DeadLetterQueueHandler:
    """Handle failed messages"""
    
    def __init__(self, queue_manager: QueueManager):
        self.queue_manager = queue_manager
        self.dlq_name = "dead_letter_queue"
        
        # Create DLQ
        self.queue_manager.create_queue(self.dlq_name)
        
        logger.info("[DLQ] Dead letter queue handler initialized")
    
    def send_to_dlq(self, message: Message, reason: str):
        """Send message to dead letter queue"""
        message.status = MessageStatus.DEAD_LETTER
        message.headers['dlq_reason'] = reason
        message.headers['dlq_timestamp'] = str(datetime.now())
        
        self.queue_manager.enqueue(self.dlq_name, message)
        
        logger.warning(f"[DLQ] Message {message.message_id} sent to DLQ: {reason}")
    
    def get_dlq_messages(self, limit: int = 100) -> List[Message]:
        """Get messages from DLQ"""
        return self.queue_manager.peek(self.dlq_name, limit)
    
    def retry_dlq_message(self, message_id: str) -> Optional[Message]:
        """Retry message from DLQ"""
        messages = self.get_dlq_messages()
        
        for msg in messages:
            if msg.message_id == message_id:
                msg.retry_count = 0
                msg.status = MessageStatus.PENDING
                
                # Remove DLQ headers
                msg.headers.pop('dlq_reason', None)
                msg.headers.pop('dlq_timestamp', None)
                
                logger.info(f"[DLQ] Retrying message: {message_id}")
                return msg
        
        return None

# ======================================================================================================================
# MESSAGE BROKER
# ======================================================================================================================

class MessageBroker:
    """Main message broker"""
    
    def __init__(self):
        self.topic_manager = TopicManager()
        self.queue_manager = QueueManager()
        self.publisher = Publisher(self.topic_manager)
        self.subscriber = Subscriber(self.topic_manager)
        self.router = MessageRouter(self.topic_manager, self.queue_manager)
        self.dlq_handler = DeadLetterQueueHandler(self.queue_manager)
        
        self.running = False
        self.broker_task = None
        
        logger.info("[BROKER] Message broker initialized")
    
    async def start(self):
        """Start message broker"""
        if self.running:
            return
        
        self.running = True
        self.broker_task = asyncio.create_task(self._broker_loop())
        
        logger.info("[BROKER] Message broker started")
    
    async def stop(self):
        """Stop message broker"""
        if not self.running:
            return
        
        self.running = False
        
        if self.broker_task:
            self.broker_task.cancel()
            try:
                await self.broker_task
            except asyncio.CancelledError:
                pass
        
        logger.info("[BROKER] Message broker stopped")
    
    async def _broker_loop(self):
        """Main broker loop"""
        while self.running:
            try:
                # Process published messages
                while self.publisher.published_messages:
                    message = self.publisher.published_messages.popleft()
                    
                    # Check expiry
                    if message.expiry_time and datetime.now() > message.expiry_time:
                        logger.warning(f"[BROKER] Message {message.message_id} expired")
                        continue
                    
                    # Route to queues
                    await self.router.route_message(message)
                    
                    # Deliver to subscribers
                    delivered = await self.subscriber.deliver_message(message)
                    
                    if delivered:
                        message.status = MessageStatus.DELIVERED
                        message.delivered_at = datetime.now()
                    else:
                        message.retry_count += 1
                        
                        if message.retry_count >= message.max_retries:
                            self.dlq_handler.send_to_dlq(
                                message,
                                "Max retries exceeded"
                            )
                        else:
                            # Re-queue for retry
                            self.publisher.published_messages.append(message)
                
                await asyncio.sleep(0.1)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[BROKER] Error: {e}")
                await asyncio.sleep(1)
    
    async def publish(self, topic: str, payload: Dict[str, Any],
                     priority: MessagePriority = MessagePriority.NORMAL) -> Message:
        """Publish message"""
        return await self.publisher.publish(topic, payload, priority=priority)
    
    def subscribe(self, subscriber_id: str, topic: str,
                 callback: Callable) -> Subscription:
        """Subscribe to topic"""
        return self.subscriber.subscribe(subscriber_id, topic, callback)
    
    def create_queue(self, name: str, max_size: int = 10000) -> Queue:
        """Create queue"""
        return self.queue_manager.create_queue(name, max_size)
    
    def add_route(self, from_topic: str, to_queue: str):
        """Add routing rule"""
        self.router.add_route(from_topic, to_queue)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get broker statistics"""
        return {
            'topics': len(self.topic_manager.topics),
            'queues': len(self.queue_manager.queues),
            'subscriptions': len(self.subscriber.subscriptions),
            'published_messages': len(self.publisher.published_messages),
            'dlq_messages': self.queue_manager.get_queue_size('dead_letter_queue'),
            'routes': sum(len(queues) for queues in self.router.routes.values())
        }

# ======================================================================================================================
# MESSAGE BROKER ORCHESTRATOR
# ======================================================================================================================

class MessageBrokerOrchestrator:
    """Message broker orchestrator with defaults"""
    
    def __init__(self):
        self.broker = MessageBroker()
        
        self._setup_default_config()
        
        logger.info("[BROKER-ORCH] Message broker orchestrator initialized")
    
    def _setup_default_config(self):
        """Setup default configuration"""
        # Create default topics
        self.broker.topic_manager.create_topic("detections")
        self.broker.topic_manager.create_topic("alerts")
        self.broker.topic_manager.create_topic("events")
        
        # Create default queues
        self.broker.create_queue("detection_processing", max_size=5000)
        self.broker.create_queue("alert_notifications", max_size=1000)
        
        # Setup default routes
        self.broker.add_route("detections", "detection_processing")
        self.broker.add_route("alerts", "alert_notifications")
    
    async def start(self):
        """Start broker"""
        await self.broker.start()
    
    async def stop(self):
        """Stop broker"""
        await self.broker.stop()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics"""
        return self.broker.get_stats()

# ======================================================================================================================
# END OF MESSAGE BROKER MODULE
# Lines in this file: ~750+
# Combined total: ~47,000+
# Remaining for 50k: ~3,000 lines
# ======================================================================================================================
