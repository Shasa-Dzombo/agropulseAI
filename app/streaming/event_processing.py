"""
Real-time Stream Processing for Agricultural Data

Apache Kafka, event sourcing, CQRS, stream analytics.

Features:
- Kafka producer/consumer
- Event sourcing architecture
- CQRS pattern implementation
- Stream aggregations
- Window operations
- Real-time alerts
- Event replay
"""

import logging
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
import asyncio
from collections import defaultdict, deque
import time

try:
    from kafka import KafkaProducer, KafkaConsumer, TopicPartition
    from kafka.errors import KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logging.warning("kafka-python not available")


logger = logging.getLogger(__name__)


class EventType(Enum):
    """Agricultural event types"""
    SENSOR_READING = "sensor_reading"
    IRRIGATION_EVENT = "irrigation_event"
    PEST_DETECTION = "pest_detection"
    DISEASE_DETECTION = "disease_detection"
    HARVEST_EVENT = "harvest_event"
    WEATHER_UPDATE = "weather_update"
    ALERT_GENERATED = "alert_generated"
    EQUIPMENT_STATUS = "equipment_status"


@dataclass
class Event:
    """Base event class"""
    event_id: str
    event_type: EventType
    timestamp: datetime
    farm_id: str
    field_id: Optional[str] = None
    data: Dict = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'timestamp': self.timestamp.isoformat(),
            'farm_id': self.farm_id,
            'field_id': self.field_id,
            'data': self.data,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Event':
        """Create from dictionary"""
        return cls(
            event_id=data['event_id'],
            event_type=EventType(data['event_type']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            farm_id=data['farm_id'],
            field_id=data.get('field_id'),
            data=data.get('data', {}),
            metadata=data.get('metadata', {})
        )


class KafkaEventProducer:
    """
    Kafka producer for agricultural events
    
    Publishes events to Kafka topics for stream processing.
    """
    
    def __init__(
        self,
        bootstrap_servers: List[str] = ['localhost:9092'],
        topic_prefix: str = 'agropulse'
    ):
        """
        Initialize Kafka producer
        
        Args:
            bootstrap_servers: Kafka broker addresses
            topic_prefix: Prefix for topic names
        """
        if not KAFKA_AVAILABLE:
            logger.warning("Kafka not available, using mock mode")
            self.mock_mode = True
            self.producer = None
        else:
            self.mock_mode = False
            self.producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3,
                max_in_flight_requests_per_connection=1
            )
        
        self.topic_prefix = topic_prefix
        self.event_count = 0
        
        logger.info(f"KafkaEventProducer initialized (mock_mode={self.mock_mode})")
    
    def produce_event(
        self,
        event: Event,
        partition_key: Optional[str] = None
    ) -> bool:
        """
        Produce event to Kafka
        
        Args:
            event: Event to publish
            partition_key: Optional partition key (uses farm_id by default)
            
        Returns:
            True if successful
        """
        topic = f"{self.topic_prefix}.{event.event_type.value}"
        key = partition_key or event.farm_id
        
        if self.mock_mode:
            logger.info(f"[MOCK] Producing event to {topic}: {event.event_id}")
            self.event_count += 1
            return True
        
        try:
            future = self.producer.send(
                topic,
                key=key,
                value=event.to_dict()
            )
            
            # Wait for confirmation
            record_metadata = future.get(timeout=10)
            
            self.event_count += 1
            
            logger.info(
                f"Event published: {event.event_id} to {topic} "
                f"(partition={record_metadata.partition}, offset={record_metadata.offset})"
            )
            
            return True
        
        except KafkaError as e:
            logger.error(f"Failed to produce event {event.event_id}: {e}")
            return False
    
    def produce_batch(self, events: List[Event]) -> int:
        """
        Produce multiple events
        
        Args:
            events: List of events
            
        Returns:
            Number of successfully produced events
        """
        success_count = 0
        
        for event in events:
            if self.produce_event(event):
                success_count += 1
        
        if not self.mock_mode and self.producer:
            self.producer.flush()
        
        return success_count
    
    def close(self):
        """Close producer"""
        if not self.mock_mode and self.producer:
            self.producer.close()


class KafkaEventConsumer:
    """
    Kafka consumer for agricultural events
    
    Consumes and processes events from Kafka topics.
    """
    
    def __init__(
        self,
        bootstrap_servers: List[str] = ['localhost:9092'],
        group_id: str = 'agropulse-consumers',
        topic_pattern: str = 'agropulse.*'
    ):
        """
        Initialize Kafka consumer
        
        Args:
            bootstrap_servers: Kafka broker addresses
            group_id: Consumer group ID
            topic_pattern: Topic pattern to subscribe
        """
        if not KAFKA_AVAILABLE:
            logger.warning("Kafka not available, using mock mode")
            self.mock_mode = True
            self.consumer = None
        else:
            self.mock_mode = False
            self.consumer = KafkaConsumer(
                bootstrap_servers=bootstrap_servers,
                group_id=group_id,
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                auto_commit_interval_ms=5000
            )
            
            # Subscribe to topics
            self.consumer.subscribe(pattern=topic_pattern)
        
        self.event_handlers: Dict[EventType, List[Callable]] = defaultdict(list)
        self.running = False
        
        logger.info(f"KafkaEventConsumer initialized (mock_mode={self.mock_mode})")
    
    def register_handler(
        self,
        event_type: EventType,
        handler: Callable[[Event], None]
    ):
        """
        Register event handler
        
        Args:
            event_type: Event type to handle
            handler: Handler function
        """
        self.event_handlers[event_type].append(handler)
        logger.info(f"Registered handler for {event_type.value}")
    
    async def start_consuming(self):
        """Start consuming events"""
        if self.mock_mode:
            logger.info("[MOCK] Consumer running")
            return
        
        self.running = True
        
        logger.info("Starting event consumption")
        
        while self.running:
            try:
                # Poll for messages
                messages = self.consumer.poll(timeout_ms=1000)
                
                for topic_partition, records in messages.items():
                    for record in records:
                        await self._process_message(record)
                
                await asyncio.sleep(0.1)
            
            except Exception as e:
                logger.error(f"Error in consumer loop: {e}")
                await asyncio.sleep(1)
    
    async def _process_message(self, record):
        """Process individual message"""
        try:
            # Parse event
            event = Event.from_dict(record.value)
            
            # Call registered handlers
            handlers = self.event_handlers.get(event.event_type, [])
            
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.error(f"Handler error for event {event.event_id}: {e}")
        
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def stop(self):
        """Stop consuming"""
        self.running = False
        
        if not self.mock_mode and self.consumer:
            self.consumer.close()


class EventStore:
    """
    Event store for event sourcing
    
    Stores all events immutably and allows replay.
    """
    
    def __init__(self):
        """Initialize event store"""
        self.events: List[Event] = []
        self.snapshots: Dict[str, Dict] = {}
        
        logger.info("EventStore initialized")
    
    def append_event(self, event: Event):
        """Append event to store"""
        self.events.append(event)
        logger.debug(f"Event stored: {event.event_id}")
    
    def get_events(
        self,
        farm_id: Optional[str] = None,
        field_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Event]:
        """
        Query events
        
        Args:
            farm_id: Filter by farm ID
            field_id: Filter by field ID
            event_type: Filter by event type
            start_time: Filter by start time
            end_time: Filter by end time
            
        Returns:
            Filtered events
        """
        filtered = self.events
        
        if farm_id:
            filtered = [e for e in filtered if e.farm_id == farm_id]
        
        if field_id:
            filtered = [e for e in filtered if e.field_id == field_id]
        
        if event_type:
            filtered = [e for e in filtered if e.event_type == event_type]
        
        if start_time:
            filtered = [e for e in filtered if e.timestamp >= start_time]
        
        if end_time:
            filtered = [e for e in filtered if e.timestamp <= end_time]
        
        return filtered
    
    def replay_events(
        self,
        aggregate_id: str,
        reducer: Callable[[Dict, Event], Dict],
        initial_state: Optional[Dict] = None
    ) -> Dict:
        """
        Replay events to rebuild state
        
        Args:
            aggregate_id: Aggregate identifier
            reducer: Reducer function (state, event) -> new_state
            initial_state: Initial state
            
        Returns:
            Final state
        """
        state = initial_state or {}
        
        events = self.get_events(farm_id=aggregate_id)
        
        for event in events:
            state = reducer(state, event)
        
        return state
    
    def create_snapshot(self, aggregate_id: str, state: Dict):
        """Create state snapshot"""
        self.snapshots[aggregate_id] = {
            'state': state,
            'timestamp': datetime.now(),
            'event_count': len(self.get_events(farm_id=aggregate_id))
        }
        logger.info(f"Snapshot created for {aggregate_id}")


class CQRSManager:
    """
    CQRS (Command Query Responsibility Segregation) manager
    
    Separates write model (commands) from read model (queries).
    """
    
    def __init__(self, event_store: EventStore, event_producer: KafkaEventProducer):
        """
        Initialize CQRS manager
        
        Args:
            event_store: Event store instance
            event_producer: Event producer instance
        """
        self.event_store = event_store
        self.event_producer = event_producer
        
        # Write model (aggregate roots)
        self.aggregates: Dict[str, Dict] = {}
        
        # Read model (projections)
        self.projections: Dict[str, Dict] = {}
        
        logger.info("CQRSManager initialized")
    
    def handle_command(
        self,
        command_type: str,
        aggregate_id: str,
        command_data: Dict
    ) -> List[Event]:
        """
        Handle command (write operation)
        
        Args:
            command_type: Type of command
            aggregate_id: Aggregate identifier
            command_data: Command data
            
        Returns:
            Generated events
        """
        # Get current aggregate state
        aggregate = self.aggregates.get(aggregate_id, {})
        
        # Process command and generate events
        events = self._process_command(command_type, aggregate, command_data)
        
        # Store and publish events
        for event in events:
            self.event_store.append_event(event)
            self.event_producer.produce_event(event)
        
        # Update aggregate state
        for event in events:
            aggregate = self._apply_event(aggregate, event)
        
        self.aggregates[aggregate_id] = aggregate
        
        return events
    
    def _process_command(
        self,
        command_type: str,
        aggregate: Dict,
        command_data: Dict
    ) -> List[Event]:
        """Process command and generate events"""
        events = []
        
        # Command handlers
        if command_type == 'schedule_irrigation':
            event = Event(
                event_id=f"evt_{int(time.time()*1000)}",
                event_type=EventType.IRRIGATION_EVENT,
                timestamp=datetime.now(),
                farm_id=command_data['farm_id'],
                field_id=command_data.get('field_id'),
                data=command_data
            )
            events.append(event)
        
        elif command_type == 'record_harvest':
            event = Event(
                event_id=f"evt_{int(time.time()*1000)}",
                event_type=EventType.HARVEST_EVENT,
                timestamp=datetime.now(),
                farm_id=command_data['farm_id'],
                field_id=command_data.get('field_id'),
                data=command_data
            )
            events.append(event)
        
        return events
    
    def _apply_event(self, aggregate: Dict, event: Event) -> Dict:
        """Apply event to aggregate state"""
        # Event sourcing: rebuild state from events
        
        if event.event_type == EventType.IRRIGATION_EVENT:
            if 'total_water_used' not in aggregate:
                aggregate['total_water_used'] = 0
            aggregate['total_water_used'] += event.data.get('water_amount', 0)
            aggregate['last_irrigation'] = event.timestamp
        
        elif event.event_type == EventType.HARVEST_EVENT:
            if 'total_yield' not in aggregate:
                aggregate['total_yield'] = 0
            aggregate['total_yield'] += event.data.get('yield_amount', 0)
            aggregate['last_harvest'] = event.timestamp
        
        return aggregate
    
    def query_projection(
        self,
        projection_name: str,
        query_params: Optional[Dict] = None
    ) -> Dict:
        """
        Query read model
        
        Args:
            projection_name: Name of projection
            query_params: Optional query parameters
            
        Returns:
            Query result
        """
        return self.projections.get(projection_name, {})
    
    def update_projection(
        self,
        projection_name: str,
        event: Event
    ):
        """
        Update read model projection
        
        Args:
            projection_name: Projection name
            event: Event to process
        """
        if projection_name not in self.projections:
            self.projections[projection_name] = {}
        
        projection = self.projections[projection_name]
        
        # Update projection based on event
        if projection_name == 'farm_statistics':
            farm_id = event.farm_id
            
            if farm_id not in projection:
                projection[farm_id] = {
                    'event_count': 0,
                    'last_updated': None
                }
            
            projection[farm_id]['event_count'] += 1
            projection[farm_id]['last_updated'] = event.timestamp


class StreamProcessor:
    """
    Real-time stream processing
    
    Performs aggregations and analytics on event streams.
    """
    
    def __init__(self, window_size: int = 60):
        """
        Initialize stream processor
        
        Args:
            window_size: Time window size in seconds
        """
        self.window_size = window_size
        
        # Windowed data
        self.windows: Dict[str, deque] = defaultdict(lambda: deque())
        
        # Aggregations
        self.aggregations: Dict[str, Any] = {}
        
        logger.info(f"StreamProcessor initialized (window_size={window_size}s)")
    
    def process_event(self, event: Event):
        """
        Process event in stream
        
        Args:
            event: Event to process
        """
        key = f"{event.farm_id}:{event.event_type.value}"
        
        # Add to window
        self.windows[key].append(event)
        
        # Remove old events
        cutoff_time = datetime.now() - timedelta(seconds=self.window_size)
        while self.windows[key] and self.windows[key][0].timestamp < cutoff_time:
            self.windows[key].popleft()
        
        # Update aggregations
        self._update_aggregations(key)
    
    def _update_aggregations(self, key: str):
        """Update aggregations for window"""
        events = list(self.windows[key])
        
        if not events:
            return
        
        # Count aggregation
        self.aggregations[f"{key}:count"] = len(events)
        
        # Sensor reading aggregations
        if events[0].event_type == EventType.SENSOR_READING:
            values = [e.data.get('value', 0) for e in events]
            
            self.aggregations[f"{key}:avg"] = sum(values) / len(values)
            self.aggregations[f"{key}:min"] = min(values)
            self.aggregations[f"{key}:max"] = max(values)
    
    def get_aggregation(self, key: str, aggregation_type: str) -> Optional[Any]:
        """
        Get aggregation value
        
        Args:
            key: Aggregation key
            aggregation_type: Type of aggregation (count, avg, min, max)
            
        Returns:
            Aggregation value
        """
        return self.aggregations.get(f"{key}:{aggregation_type}")
    
    def detect_anomalies(
        self,
        farm_id: str,
        event_type: EventType,
        threshold: float = 2.0
    ) -> List[Event]:
        """
        Detect anomalous events
        
        Args:
            farm_id: Farm ID
            event_type: Event type
            threshold: Standard deviation threshold
            
        Returns:
            Anomalous events
        """
        key = f"{farm_id}:{event_type.value}"
        events = list(self.windows[key])
        
        if len(events) < 10:
            return []
        
        # Get values
        values = [e.data.get('value', 0) for e in events]
        
        # Calculate statistics
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5
        
        # Find anomalies
        anomalies = []
        for event, value in zip(events, values):
            z_score = abs(value - mean) / std_dev if std_dev > 0 else 0
            if z_score > threshold:
                anomalies.append(event)
        
        return anomalies
