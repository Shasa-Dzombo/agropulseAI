# Advanced Enterprise Video Analytics Management System
# Comprehensive orchestration platform for multi-stream video intelligence, real-time processing, and advanced analytics

import asyncio
import cv2
import numpy as np
import logging
import time
import json
import sqlite3
import threading
import queue
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set, Union, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import statistics
import hashlib
import uuid
import pickle
import copy

from .line_crossing import LineCrossingDetector
from .intrusion_detection import IntrusionDetector  
from .lpr import LicensePlateRecognizer
from .facial_recognition import FacialRecognitionAnalytics

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    import pika
    RABBITMQ_AVAILABLE = True
except ImportError:
    RABBITMQ_AVAILABLE = False

try:
    from kafka import KafkaProducer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False

try:
    import tensorflow as tf
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False

logger = logging.getLogger(__name__)

class AnalyticsType(Enum):
    LINE_CROSSING = "line_crossing"
    INTRUSION_DETECTION = "intrusion_detection"
    LICENSE_PLATE_RECOGNITION = "lpr"
    FACIAL_RECOGNITION = "facial_recognition"
    MOTION_DETECTION = "motion_detection"
    OBJECT_CLASSIFICATION = "object_classification"
    CROWD_ANALYSIS = "crowd_analysis"
    BEHAVIOR_ANALYSIS = "behavior_analysis"
    TRAFFIC_ANALYSIS = "traffic_analysis"
    PERIMETER_SECURITY = "perimeter_security"

class EventSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ProcessingPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

class StreamStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    MAINTENANCE = "maintenance"

@dataclass
class AnalyticsEvent:
    event_id: str
    event_type: AnalyticsType
    stream_id: str
    timestamp: float
    severity: EventSeverity
    confidence: float
    metadata: Dict[str, Any]
    frame_number: int
    bbox: Optional[Tuple[int, int, int, int]] = None
    rule_id: Optional[str] = None
    object_id: Optional[str] = None
    description: str = ""
    alert_sent: bool = False
    processed: bool = False

@dataclass
class StreamConfiguration:
    stream_id: str
    enabled_analytics: Set[AnalyticsType]
    processing_priority: ProcessingPriority
    frame_skip: int
    resolution: Tuple[int, int]
    fps_limit: int
    analytics_config: Dict[str, Any]
    alert_config: Dict[str, Any]
    retention_policy: Dict[str, Any]
    status: StreamStatus = StreamStatus.ACTIVE
    last_processed: float = 0.0

@dataclass 
class AnalyticsRule:
    rule_id: str
    rule_type: AnalyticsType
    stream_id: str
    configuration: Dict[str, Any]
    enabled: bool
    created_at: float
    updated_at: float
    trigger_conditions: Dict[str, Any]
    actions: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ProcessingStats:
    frames_processed: int = 0
    events_generated: int = 0
    processing_time_total: float = 0.0
    last_processing_time: float = 0.0
    fps: float = 0.0
    error_count: int = 0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0

class FrameProcessor:
    def __init__(self, processor_id: str, config: Dict[str, Any]):
        self.processor_id = processor_id
        self.config = config
        self.is_active = False
        self.frame_queue = queue.Queue(maxsize=config.get('queue_size', 100))
        self.result_queue = queue.Queue()
        self.processing_thread = None
        self.stats = ProcessingStats()
        
    def start(self):
        if not self.is_active:
            self.is_active = True
            self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
            self.processing_thread.start()
            logger.info(f"Frame processor {self.processor_id} started")
    
    def stop(self):
        self.is_active = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5.0)
        logger.info(f"Frame processor {self.processor_id} stopped")
    
    def _processing_loop(self):
        while self.is_active:
            try:
                if not self.frame_queue.empty():
                    frame_data = self.frame_queue.get(timeout=1.0)
                    result = self._process_frame_data(frame_data)
                    if result:
                        self.result_queue.put(result)
                else:
                    time.sleep(0.01)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Frame processor {self.processor_id} error: {e}")
                self.stats.error_count += 1
    
    def _process_frame_data(self, frame_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        start_time = time.time()
        
        try:
            # Process frame based on analytics type
            stream_id = frame_data['stream_id']
            frame = frame_data['frame']
            analytics_type = frame_data['analytics_type']
            config = frame_data['config']
            
            result = None
            
            if analytics_type == AnalyticsType.MOTION_DETECTION:
                result = self._process_motion_detection(frame, config)
            elif analytics_type == AnalyticsType.OBJECT_CLASSIFICATION:
                result = self._process_object_classification(frame, config)
            elif analytics_type == AnalyticsType.CROWD_ANALYSIS:
                result = self._process_crowd_analysis(frame, config)
            elif analytics_type == AnalyticsType.BEHAVIOR_ANALYSIS:
                result = self._process_behavior_analysis(frame, config)
            
            processing_time = time.time() - start_time
            self.stats.frames_processed += 1
            self.stats.processing_time_total += processing_time
            self.stats.last_processing_time = processing_time
            
            if self.stats.frames_processed > 0:
                self.stats.fps = 1.0 / (self.stats.processing_time_total / self.stats.frames_processed)
            
            return result
            
        except Exception as e:
            logger.error(f"Frame processing error: {e}")
            self.stats.error_count += 1
            return None
    
    def _process_motion_detection(self, frame: np.ndarray, config: Dict[str, Any]) -> Dict[str, Any]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (21, 21), 0)
        
        # Background subtraction for motion detection
        if not hasattr(self, '_background_model'):
            self._background_model = cv2.createBackgroundSubtractorMOG2(detectShadows=True)
        
        fg_mask = self._background_model.apply(frame)
        
        # Morphological operations to clean up the mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        motion_areas = []
        min_area = config.get('min_motion_area', 500)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > min_area:
                x, y, w, h = cv2.boundingRect(contour)
                motion_areas.append({
                    'bbox': (x, y, w, h),
                    'area': area,
                    'confidence': min(area / 10000, 1.0)
                })
        
        return {
            'motion_areas': motion_areas,
            'total_motion': len(motion_areas),
            'motion_percentage': np.sum(fg_mask > 0) / fg_mask.size
        }
    
    def _process_object_classification(self, frame: np.ndarray, config: Dict[str, Any]) -> Dict[str, Any]:
        # Simplified object detection using contour analysis
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 50, 150)
        
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        objects = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > config.get('min_object_area', 1000):
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h
                
                # Simple object classification based on shape
                object_type = "unknown"
                confidence = 0.5
                
                if 0.8 <= aspect_ratio <= 1.2:
                    object_type = "person"
                    confidence = 0.7
                elif aspect_ratio > 1.5:
                    object_type = "vehicle"
                    confidence = 0.6
                
                objects.append({
                    'type': object_type,
                    'bbox': (x, y, w, h),
                    'confidence': confidence,
                    'area': area,
                    'aspect_ratio': aspect_ratio
                })
        
        return {'detected_objects': objects}
    
    def _process_crowd_analysis(self, frame: np.ndarray, config: Dict[str, Any]) -> Dict[str, Any]:
        # Crowd density estimation using background subtraction
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if not hasattr(self, '_crowd_bg_subtractor'):
            self._crowd_bg_subtractor = cv2.createBackgroundSubtractorMOG2()
        
        fg_mask = self._crowd_bg_subtractor.apply(frame)
        
        # Count foreground pixels as crowd density indicator
        crowd_pixels = np.sum(fg_mask > 0)
        total_pixels = fg_mask.size
        crowd_density = crowd_pixels / total_pixels
        
        # Detect crowd clusters using connected components
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_mask, connectivity=8)
        
        crowd_clusters = []
        min_cluster_size = config.get('min_cluster_size', 500)
        
        for i in range(1, num_labels):  # Skip background label 0
            area = stats[i, cv2.CC_STAT_AREA]
            if area > min_cluster_size:
                x = stats[i, cv2.CC_STAT_LEFT]
                y = stats[i, cv2.CC_STAT_TOP]
                w = stats[i, cv2.CC_STAT_WIDTH]
                h = stats[i, cv2.CC_STAT_HEIGHT]
                
                estimated_people = max(1, int(area / 2000))  # Rough estimation
                
                crowd_clusters.append({
                    'bbox': (x, y, w, h),
                    'area': area,
                    'estimated_people': estimated_people,
                    'centroid': centroids[i].tolist()
                })
        
        return {
            'crowd_density': crowd_density,
            'crowd_clusters': crowd_clusters,
            'total_estimated_people': sum(cluster['estimated_people'] for cluster in crowd_clusters)
        }
    
    def _process_behavior_analysis(self, frame: np.ndarray, config: Dict[str, Any]) -> Dict[str, Any]:
        # Simple behavior analysis based on motion patterns
        if not hasattr(self, '_behavior_history'):
            self._behavior_history = deque(maxlen=30)  # 30 frame history
        
        # Extract motion vectors
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if hasattr(self, '_prev_gray'):
            # Calculate optical flow
            flow = cv2.calcOpticalFlowPyrLK(
                self._prev_gray, gray, None, None,
                winSize=(15, 15), maxLevel=2,
                criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
            )
            
            # Analyze motion patterns
            motion_magnitude = np.mean(np.abs(flow[0])) if flow[0] is not None else 0
            motion_direction = np.mean(np.arctan2(flow[0][:, 1], flow[0][:, 0])) if flow[0] is not None else 0
            
            behavior_data = {
                'motion_magnitude': float(motion_magnitude),
                'motion_direction': float(motion_direction),
                'timestamp': time.time()
            }
            
            self._behavior_history.append(behavior_data)
        
        self._prev_gray = gray.copy()
        
        # Analyze behavior patterns
        if len(self._behavior_history) >= 10:
            recent_motions = [data['motion_magnitude'] for data in list(self._behavior_history)[-10:]]
            motion_variance = np.var(recent_motions)
            
            # Detect anomalous behavior
            anomaly_threshold = config.get('anomaly_threshold', 0.5)
            is_anomalous = motion_variance > anomaly_threshold
            
            behavior_type = "normal"
            if is_anomalous:
                behavior_type = "suspicious"
            
            return {
                'behavior_type': behavior_type,
                'motion_variance': float(motion_variance),
                'is_anomalous': is_anomalous,
                'confidence': min(motion_variance / anomaly_threshold, 1.0) if is_anomalous else 0.8
            }
        
        return {'behavior_type': 'normal', 'confidence': 0.5}

class EventDispatcher:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.event_handlers = {}
        self.message_queue = queue.Queue()
        self.is_active = False
        self.dispatch_thread = None
        
        self._setup_message_brokers()
    
    def _setup_message_brokers(self):
        self.redis_client = None
        self.rabbitmq_connection = None
        self.kafka_producer = None
        
        if REDIS_AVAILABLE and self.config.get('redis_enabled', False):
            try:
                import redis
                self.redis_client = redis.Redis(
                    host=self.config.get('redis_host', 'localhost'),
                    port=self.config.get('redis_port', 6379),
                    db=self.config.get('redis_db', 0)
                )
                logger.info("Redis client initialized for event dispatching")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis: {e}")
        
        if RABBITMQ_AVAILABLE and self.config.get('rabbitmq_enabled', False):
            try:
                import pika
                self.rabbitmq_connection = pika.BlockingConnection(
                    pika.ConnectionParameters(self.config.get('rabbitmq_host', 'localhost'))
                )
                logger.info("RabbitMQ connection initialized for event dispatching")
            except Exception as e:
                logger.warning(f"Failed to initialize RabbitMQ: {e}")
        
        if KAFKA_AVAILABLE and self.config.get('kafka_enabled', False):
            try:
                from kafka import KafkaProducer
                self.kafka_producer = KafkaProducer(
                    bootstrap_servers=self.config.get('kafka_servers', ['localhost:9092']),
                    value_serializer=lambda x: json.dumps(x).encode('utf-8')
                )
                logger.info("Kafka producer initialized for event dispatching")
            except Exception as e:
                logger.warning(f"Failed to initialize Kafka: {e}")
    
    def start(self):
        if not self.is_active:
            self.is_active = True
            self.dispatch_thread = threading.Thread(target=self._dispatch_loop, daemon=True)
            self.dispatch_thread.start()
            logger.info("Event dispatcher started")
    
    def stop(self):
        self.is_active = False
        if self.dispatch_thread:
            self.dispatch_thread.join(timeout=5.0)
        logger.info("Event dispatcher stopped")
    
    def dispatch_event(self, event: AnalyticsEvent):
        try:
            self.message_queue.put(event, timeout=1.0)
        except queue.Full:
            logger.warning("Event dispatch queue is full, dropping event")
    
    def _dispatch_loop(self):
        while self.is_active:
            try:
                if not self.message_queue.empty():
                    event = self.message_queue.get(timeout=1.0)
                    self._process_event(event)
                else:
                    time.sleep(0.01)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Event dispatch error: {e}")
    
    def _process_event(self, event: AnalyticsEvent):
        event_data = asdict(event)
        
        # Send to Redis
        if self.redis_client:
            try:
                self.redis_client.lpush('analytics_events', json.dumps(event_data))
            except Exception as e:
                logger.error(f"Redis dispatch error: {e}")
        
        # Send to RabbitMQ
        if self.rabbitmq_connection:
            try:
                channel = self.rabbitmq_connection.channel()
                channel.queue_declare(queue='analytics_events')
                channel.basic_publish(
                    exchange='',
                    routing_key='analytics_events',
                    body=json.dumps(event_data)
                )
            except Exception as e:
                logger.error(f"RabbitMQ dispatch error: {e}")
        
        # Send to Kafka
        if self.kafka_producer:
            try:
                self.kafka_producer.send('analytics_events', event_data)
            except Exception as e:
                logger.error(f"Kafka dispatch error: {e}")

class VideoAnalyticsManager:
    def __init__(self, config: Dict[str, Any], db_manager=None, alert_manager=None):
        self.config = config
        self.db_manager = db_manager
        self.alert_manager = alert_manager
        
        # Core analytics components
        self.lpr = LicensePlateRecognizer(config.get('lpr', {}))
        self.facial_recognition = FacialRecognitionAnalytics(config.get('facial_recognition', {}))
        
        # Stream management
        self.stream_configurations = {}
        self.stream_rules = {}
        self.stream_stats = {}
        self.active_streams = set()
        
        # Processing infrastructure
        self.frame_processors = {}
        self.processing_executor = ThreadPoolExecutor(max_workers=config.get('max_workers', 4))
        self.event_dispatcher = EventDispatcher(config.get('event_dispatch', {}))
        
        # Performance monitoring
        self.performance_monitor = PerformanceMonitor()
        
        # Rule engine
        self.rule_engine = RuleEngine()
        
        # Event storage
        self.event_buffer = deque(maxlen=config.get('event_buffer_size', 10000))
        
        # Database setup
        self._setup_analytics_database()
        
        logger.info("Advanced Video Analytics Manager initialized")
    
    def _setup_analytics_database(self):
        if not self.db_manager:
            return
            
        try:
            # Create analytics tables
            self.db_manager.execute_query("""
                CREATE TABLE IF NOT EXISTS analytics_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT,
                    stream_id TEXT,
                    timestamp REAL,
                    severity TEXT,
                    confidence REAL,
                    metadata TEXT,
                    frame_number INTEGER,
                    bbox TEXT,
                    rule_id TEXT,
                    object_id TEXT,
                    description TEXT,
                    alert_sent BOOLEAN,
                    processed BOOLEAN
                )
            """)
            
            self.db_manager.execute_query("""
                CREATE TABLE IF NOT EXISTS stream_configurations (
                    stream_id TEXT PRIMARY KEY,
                    enabled_analytics TEXT,
                    processing_priority INTEGER,
                    frame_skip INTEGER,
                    resolution TEXT,
                    fps_limit INTEGER,
                    analytics_config TEXT,
                    alert_config TEXT,
                    retention_policy TEXT,
                    status TEXT,
                    last_processed REAL
                )
            """)
            
            self.db_manager.execute_query("""
                CREATE TABLE IF NOT EXISTS analytics_rules (
                    rule_id TEXT PRIMARY KEY,
                    rule_type TEXT,
                    stream_id TEXT,
                    configuration TEXT,
                    enabled BOOLEAN,
                    created_at REAL,
                    updated_at REAL,
                    trigger_conditions TEXT,
                    actions TEXT,
                    metadata TEXT
                )
            """)
            
            logger.info("Analytics database tables created successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup analytics database: {e}")
    
    async def initialize_stream(self, stream_id: str, stream_config: Dict[str, Any]) -> bool:
        try:
            # Create stream configuration
            config = StreamConfiguration(
                stream_id=stream_id,
                enabled_analytics=set(AnalyticsType(t) for t in stream_config.get('enabled_analytics', [])),
                processing_priority=ProcessingPriority(stream_config.get('priority', 2)),
                frame_skip=stream_config.get('frame_skip', 1),
                resolution=tuple(stream_config.get('resolution', (1920, 1080))),
                fps_limit=stream_config.get('fps_limit', 30),
                analytics_config=stream_config.get('analytics_config', {}),
                alert_config=stream_config.get('alert_config', {}),
                retention_policy=stream_config.get('retention_policy', {'days': 30})
            )
            
            self.stream_configurations[stream_id] = config
            self.stream_stats[stream_id] = ProcessingStats()
            
            # Load analytics rules for this stream
            await self.load_rules_for_stream(stream_id)
            
            # Initialize frame processor for this stream if needed
            if stream_config.get('dedicated_processor', False):
                processor = FrameProcessor(f"processor_{stream_id}", stream_config)
                self.frame_processors[stream_id] = processor
                processor.start()
            
            self.active_streams.add(stream_id)
            
            logger.info(f"Stream {stream_id} initialized with {len(config.enabled_analytics)} analytics")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize stream {stream_id}: {e}")
            return False
    
    async def load_rules_for_stream(self, stream_id: str):
        """Enhanced rule loading with support for complex analytics"""
        try:
            if self.db_manager:
                rules = await self.db_manager.get_analytics_rules(stream_id)
            else:
                rules = []
            
            # Initialize rule containers for this stream
            self.stream_rules[stream_id] = {
                'line_crossing': [],
                'intrusion_detection': [],
                'lpr': [],
                'facial_recognition': [],
                'motion_detection': [],
                'object_classification': [],
                'crowd_analysis': [],
                'behavior_analysis': [],
                'traffic_analysis': [],
                'perimeter_security': []
            }
            
            # Load rules based on type
            for rule_data in rules:
                rule = AnalyticsRule(
                    rule_id=rule_data['rule_id'],
                    rule_type=AnalyticsType(rule_data['rule_type']),
                    stream_id=stream_id,
                    configuration=json.loads(rule_data['configuration']),
                    enabled=rule_data['enabled'],
                    created_at=rule_data['created_at'],
                    updated_at=rule_data['updated_at'],
                    trigger_conditions=json.loads(rule_data['trigger_conditions']),
                    actions=json.loads(rule_data['actions']),
                    metadata=json.loads(rule_data.get('metadata', '{}'))
                )
                
                if not rule.enabled:
                    continue
                
                if rule.rule_type == AnalyticsType.LINE_CROSSING:
                    detector = LineCrossingDetector(rule.rule_id, rule.configuration['points'])
                    self.stream_rules[stream_id]['line_crossing'].append(detector)
                
                elif rule.rule_type == AnalyticsType.INTRUSION_DETECTION:
                    detector = IntrusionDetector(rule.rule_id, rule.configuration['points'])
                    self.stream_rules[stream_id]['intrusion_detection'].append(detector)
                
                # Add other rule types as needed
                
            logger.info(f"Loaded {len(rules)} analytics rules for stream '{stream_id}'")
            
        except Exception as e:
            logger.error(f"Failed to load rules for stream {stream_id}: {e}")
    
    async def process_frame(self, stream_id: str, frame: np.ndarray, 
                          tracked_objects: Dict[str, Any] = None,
                          frame_number: int = 0) -> Tuple[List[AnalyticsEvent], np.ndarray]:
        """
        Enhanced frame processing with comprehensive analytics pipeline
        """
        start_time = time.time()
        analytics_events = []
        
        if stream_id not in self.stream_configurations:
            return analytics_events, frame
        
        config = self.stream_configurations[stream_id]
        
        # Check if this frame should be processed based on frame skip
        if frame_number % config.frame_skip != 0:
            return analytics_events, frame
        
        # Update stream stats
        stats = self.stream_stats[stream_id]
        stats.frames_processed += 1
        
        try:
            # Process each enabled analytics type
            if AnalyticsType.LINE_CROSSING in config.enabled_analytics:
                events = await self._process_line_crossing(stream_id, frame, tracked_objects, frame_number)
                analytics_events.extend(events)
            
            if AnalyticsType.INTRUSION_DETECTION in config.enabled_analytics:
                events = await self._process_intrusion_detection(stream_id, frame, tracked_objects, frame_number)
                analytics_events.extend(events)
            
            if AnalyticsType.LICENSE_PLATE_RECOGNITION in config.enabled_analytics:
                events = await self._process_lpr(stream_id, frame, frame_number)
                analytics_events.extend(events)
            
            if AnalyticsType.FACIAL_RECOGNITION in config.enabled_analytics:
                events = await self._process_facial_recognition(stream_id, frame, frame_number)
                analytics_events.extend(events)
            
            if AnalyticsType.MOTION_DETECTION in config.enabled_analytics:
                events = await self._process_motion_detection(stream_id, frame, frame_number)
                analytics_events.extend(events)
            
            if AnalyticsType.OBJECT_CLASSIFICATION in config.enabled_analytics:
                events = await self._process_object_classification(stream_id, frame, frame_number)
                analytics_events.extend(events)
            
            if AnalyticsType.CROWD_ANALYSIS in config.enabled_analytics:
                events = await self._process_crowd_analysis(stream_id, frame, frame_number)
                analytics_events.extend(events)
            
            if AnalyticsType.BEHAVIOR_ANALYSIS in config.enabled_analytics:
                events = await self._process_behavior_analysis(stream_id, frame, frame_number)
                analytics_events.extend(events)
            
            # Process events through rule engine
            for event in analytics_events:
                self.rule_engine.process_event(event)
                self.event_buffer.append(event)
                
                # Dispatch event for external processing
                self.event_dispatcher.dispatch_event(event)
                
                # Store event in database
                if self.db_manager:
                    await self._store_event(event)
            
            # Update statistics
            processing_time = time.time() - start_time
            stats.processing_time_total += processing_time
            stats.last_processing_time = processing_time
            stats.events_generated += len(analytics_events)
            
            if stats.frames_processed > 0:
                stats.fps = 1.0 / (stats.processing_time_total / stats.frames_processed)
            
            # Draw overlays on frame
            processed_frame = self.draw_overlays(frame.copy(), stream_id, analytics_events)
            
            return analytics_events, processed_frame
            
        except Exception as e:
            logger.error(f"Frame processing error for stream {stream_id}: {e}")
            stats.error_count += 1
            return [], frame
    
    async def _process_line_crossing(self, stream_id: str, frame: np.ndarray, 
                                   tracked_objects: Dict[str, Any], 
                                   frame_number: int) -> List[AnalyticsEvent]:
        events = []
        
        if stream_id not in self.stream_rules or not tracked_objects:
            return events
        
        for detector in self.stream_rules[stream_id]['line_crossing']:
            crossings = detector.update(tracked_objects)
            
            for obj_id, direction in crossings:
                event = AnalyticsEvent(
                    event_id=str(uuid.uuid4()),
                    event_type=AnalyticsType.LINE_CROSSING,
                    stream_id=stream_id,
                    timestamp=time.time(),
                    severity=EventSeverity.MEDIUM,
                    confidence=0.9,
                    metadata={
                        'direction': direction,
                        'rule_name': getattr(detector, 'rule_name', 'Unknown')
                    },
                    frame_number=frame_number,
                    rule_id=detector.rule_id,
                    object_id=obj_id,
                    description=f"Object {obj_id} crossed line in {direction} direction"
                )
                events.append(event)
        
        return events
    
    async def _process_intrusion_detection(self, stream_id: str, frame: np.ndarray,
                                         tracked_objects: Dict[str, Any],
                                         frame_number: int) -> List[AnalyticsEvent]:
        events = []
        
        if stream_id not in self.stream_rules or not tracked_objects:
            return events
        
        for detector in self.stream_rules[stream_id]['intrusion_detection']:
            intrusions = detector.update(tracked_objects)
            
            for obj_id in intrusions:
                event = AnalyticsEvent(
                    event_id=str(uuid.uuid4()),
                    event_type=AnalyticsType.INTRUSION_DETECTION,
                    stream_id=stream_id,
                    timestamp=time.time(),
                    severity=EventSeverity.HIGH,
                    confidence=0.85,
                    metadata={
                        'zone_name': getattr(detector, 'zone_name', 'Unknown'),
                        'threat_level': 'medium'
                    },
                    frame_number=frame_number,
                    rule_id=detector.rule_id,
                    object_id=obj_id,
                    description=f"Intrusion detected by object {obj_id}"
                )
                events.append(event)
        
        return events
    
    async def _process_lpr(self, stream_id: str, frame: np.ndarray, 
                          frame_number: int) -> List[AnalyticsEvent]:
        events = []
        
        if not self.lpr.is_enabled:
            return events
        
        try:
            plate_detections = await self.lpr.recognize(frame)
            
            for detection in plate_detections:
                # Check watchlist
                watchlist_alert = self.lpr.check_watchlist(detection.plate_text)
                
                severity = EventSeverity.LOW
                if watchlist_alert:
                    severity = EventSeverity.CRITICAL if watchlist_alert['alert_type'] == 'wanted' else EventSeverity.HIGH
                
                event = AnalyticsEvent(
                    event_id=str(uuid.uuid4()),
                    event_type=AnalyticsType.LICENSE_PLATE_RECOGNITION,
                    stream_id=stream_id,
                    timestamp=time.time(),
                    severity=severity,
                    confidence=detection.confidence,
                    metadata={
                        'plate_text': detection.plate_text,
                        'plate_format': detection.format_type.value,
                        'vehicle_type': detection.vehicle_type.value if detection.vehicle_type else None,
                        'watchlist_match': watchlist_alert is not None
                    },
                    frame_number=frame_number,
                    bbox=detection.bbox,
                    description=f"License plate detected: {detection.plate_text}"
                )
                events.append(event)
                
        except Exception as e:
            logger.error(f"LPR processing error: {e}")
        
        return events
    
    async def _process_facial_recognition(self, stream_id: str, frame: np.ndarray,
                                        frame_number: int) -> List[AnalyticsEvent]:
        events = []
        
        try:
            if not hasattr(self.facial_recognition, 'analyze_frame'):
                return events
                
            face_results = await self.facial_recognition.analyze_frame(frame)
            
            for result in face_results.get('faces', []):
                severity = EventSeverity.LOW
                if result.get('identity_match'):
                    severity = EventSeverity.MEDIUM
                if result.get('watchlist_match'):
                    severity = EventSeverity.HIGH
                
                event = AnalyticsEvent(
                    event_id=str(uuid.uuid4()),
                    event_type=AnalyticsType.FACIAL_RECOGNITION,
                    stream_id=stream_id,
                    timestamp=time.time(),
                    severity=severity,
                    confidence=result.get('confidence', 0.0),
                    metadata=result,
                    frame_number=frame_number,
                    bbox=result.get('bbox'),
                    description=f"Face detected: {result.get('identity', 'Unknown')}"
                )
                events.append(event)
                
        except Exception as e:
            logger.error(f"Facial recognition processing error: {e}")
        
        return events
    
    async def _process_motion_detection(self, stream_id: str, frame: np.ndarray,
                                      frame_number: int) -> List[AnalyticsEvent]:
        events = []
        
        try:
            # Use dedicated processor if available
            processor = self.frame_processors.get(stream_id)
            if processor:
                frame_data = {
                    'stream_id': stream_id,
                    'frame': frame,
                    'analytics_type': AnalyticsType.MOTION_DETECTION,
                    'config': self.stream_configurations[stream_id].analytics_config.get('motion_detection', {})
                }
                
                processor.frame_queue.put(frame_data)
                
                # Try to get result (non-blocking)
                try:
                    result = processor.result_queue.get_nowait()
                    if result and result.get('motion_areas'):
                        for motion_area in result['motion_areas']:
                            if motion_area['confidence'] > 0.5:
                                event = AnalyticsEvent(
                                    event_id=str(uuid.uuid4()),
                                    event_type=AnalyticsType.MOTION_DETECTION,
                                    stream_id=stream_id,
                                    timestamp=time.time(),
                                    severity=EventSeverity.LOW,
                                    confidence=motion_area['confidence'],
                                    metadata=motion_area,
                                    frame_number=frame_number,
                                    bbox=motion_area['bbox'],
                                    description="Motion detected"
                                )
                                events.append(event)
                except queue.Empty:
                    pass
                    
        except Exception as e:
            logger.error(f"Motion detection processing error: {e}")
        
        return events
    
    async def _process_object_classification(self, stream_id: str, frame: np.ndarray,
                                           frame_number: int) -> List[AnalyticsEvent]:
        events = []
        
        try:
            processor = self.frame_processors.get(stream_id)
            if processor:
                frame_data = {
                    'stream_id': stream_id,
                    'frame': frame,
                    'analytics_type': AnalyticsType.OBJECT_CLASSIFICATION,
                    'config': self.stream_configurations[stream_id].analytics_config.get('object_classification', {})
                }
                
                processor.frame_queue.put(frame_data)
                
                try:
                    result = processor.result_queue.get_nowait()
                    if result and result.get('detected_objects'):
                        for obj in result['detected_objects']:
                            if obj['confidence'] > 0.6:
                                event = AnalyticsEvent(
                                    event_id=str(uuid.uuid4()),
                                    event_type=AnalyticsType.OBJECT_CLASSIFICATION,
                                    stream_id=stream_id,
                                    timestamp=time.time(),
                                    severity=EventSeverity.LOW,
                                    confidence=obj['confidence'],
                                    metadata=obj,
                                    frame_number=frame_number,
                                    bbox=obj['bbox'],
                                    description=f"Object detected: {obj['type']}"
                                )
                                events.append(event)
                except queue.Empty:
                    pass
                    
        except Exception as e:
            logger.error(f"Object classification processing error: {e}")
        
        return events
    
    async def _process_crowd_analysis(self, stream_id: str, frame: np.ndarray,
                                    frame_number: int) -> List[AnalyticsEvent]:
        events = []
        
        try:
            processor = self.frame_processors.get(stream_id)
            if processor:
                frame_data = {
                    'stream_id': stream_id,
                    'frame': frame,
                    'analytics_type': AnalyticsType.CROWD_ANALYSIS,
                    'config': self.stream_configurations[stream_id].analytics_config.get('crowd_analysis', {})
                }
                
                processor.frame_queue.put(frame_data)
                
                try:
                    result = processor.result_queue.get_nowait()
                    if result:
                        crowd_density = result.get('crowd_density', 0)
                        total_people = result.get('total_estimated_people', 0)
                        
                        # Generate event for high crowd density
                        if crowd_density > 0.3 or total_people > 20:
                            severity = EventSeverity.MEDIUM if crowd_density > 0.5 else EventSeverity.LOW
                            
                            event = AnalyticsEvent(
                                event_id=str(uuid.uuid4()),
                                event_type=AnalyticsType.CROWD_ANALYSIS,
                                stream_id=stream_id,
                                timestamp=time.time(),
                                severity=severity,
                                confidence=0.8,
                                metadata=result,
                                frame_number=frame_number,
                                description=f"Crowd detected: {total_people} people, density {crowd_density:.2f}"
                            )
                            events.append(event)
                            
                except queue.Empty:
                    pass
                    
        except Exception as e:
            logger.error(f"Crowd analysis processing error: {e}")
        
        return events
    
    async def _process_behavior_analysis(self, stream_id: str, frame: np.ndarray,
                                       frame_number: int) -> List[AnalyticsEvent]:
        events = []
        
        try:
            processor = self.frame_processors.get(stream_id)
            if processor:
                frame_data = {
                    'stream_id': stream_id,
                    'frame': frame,
                    'analytics_type': AnalyticsType.BEHAVIOR_ANALYSIS,
                    'config': self.stream_configurations[stream_id].analytics_config.get('behavior_analysis', {})
                }
                
                processor.frame_queue.put(frame_data)
                
                try:
                    result = processor.result_queue.get_nowait()
                    if result and result.get('is_anomalous', False):
                        event = AnalyticsEvent(
                            event_id=str(uuid.uuid4()),
                            event_type=AnalyticsType.BEHAVIOR_ANALYSIS,
                            stream_id=stream_id,
                            timestamp=time.time(),
                            severity=EventSeverity.MEDIUM,
                            confidence=result.get('confidence', 0.5),
                            metadata=result,
                            frame_number=frame_number,
                            description=f"Anomalous behavior detected: {result.get('behavior_type', 'unknown')}"
                        )
                        events.append(event)
                        
                except queue.Empty:
                    pass
                    
        except Exception as e:
            logger.error(f"Behavior analysis processing error: {e}")
        
        return events
    
    async def _store_event(self, event: AnalyticsEvent):
        """Store analytics event in database"""
        try:
            if self.db_manager:
                query = """
                    INSERT INTO analytics_events 
                    (event_id, event_type, stream_id, timestamp, severity, confidence, 
                     metadata, frame_number, bbox, rule_id, object_id, description, 
                     alert_sent, processed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                params = (
                    event.event_id, event.event_type.value, event.stream_id,
                    event.timestamp, event.severity.value, event.confidence,
                    json.dumps(event.metadata), event.frame_number,
                    json.dumps(event.bbox) if event.bbox else None,
                    event.rule_id, event.object_id, event.description,
                    event.alert_sent, event.processed
                )
                
                await self.db_manager.execute_query(query, params)
                
        except Exception as e:
            logger.error(f"Failed to store analytics event: {e}")
    
    def draw_overlays(self, frame: np.ndarray, stream_id: str, 
                     events: List[AnalyticsEvent] = None) -> np.ndarray:
        """Enhanced overlay drawing with event highlights"""
        if stream_id not in self.stream_rules:
            return frame
        
        # Draw analytics rules
        for detector in self.stream_rules[stream_id]['line_crossing']:
            cv2.line(frame, detector.line[0], detector.line[1], (0, 255, 0), 3)
            cv2.putText(frame, f"Line: {detector.rule_id}", 
                       (detector.line[0][0], detector.line[0][1] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        for detector in self.stream_rules[stream_id]['intrusion_detection']:
            pts = np.array(detector.zone, np.int32).reshape((-1, 1, 2))
            cv2.polylines(frame, [pts], isClosed=True, color=(0, 0, 255), thickness=3)
            
            # Calculate center of zone for label
            center_x = int(np.mean([pt[0] for pt in detector.zone]))
            center_y = int(np.mean([pt[1] for pt in detector.zone]))
            cv2.putText(frame, f"Zone: {detector.rule_id}",
                       (center_x - 50, center_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Highlight event locations
        if events:
            for event in events:
                if event.bbox:
                    x, y, w, h = event.bbox
                    
                    # Color based on severity
                    color = (0, 255, 0)  # Green for low
                    if event.severity == EventSeverity.MEDIUM:
                        color = (0, 255, 255)  # Yellow
                    elif event.severity == EventSeverity.HIGH:
                        color = (0, 165, 255)  # Orange
                    elif event.severity == EventSeverity.CRITICAL:
                        color = (0, 0, 255)  # Red
                    
                    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                    
                    # Add event label
                    label = f"{event.event_type.value}: {event.confidence:.2f}"
                    cv2.putText(frame, label, (x, y - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # Add stream info overlay
        config = self.stream_configurations.get(stream_id)
        stats = self.stream_stats.get(stream_id)
        
        if config and stats:
            info_text = [
                f"Stream: {stream_id}",
                f"FPS: {stats.fps:.1f}",
                f"Processed: {stats.frames_processed}",
                f"Events: {stats.events_generated}",
                f"Analytics: {len(config.enabled_analytics)}"
            ]
            
            y_offset = 30
            for text in info_text:
                cv2.putText(frame, text, (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                y_offset += 25
        
        return frame
    
    def get_stream_statistics(self, stream_id: str = None) -> Dict[str, Any]:
        """Get comprehensive statistics for stream(s)"""
        if stream_id:
            if stream_id in self.stream_stats:
                stats = self.stream_stats[stream_id]
                return {
                    'stream_id': stream_id,
                    'frames_processed': stats.frames_processed,
                    'events_generated': stats.events_generated,
                    'fps': stats.fps,
                    'processing_time': stats.last_processing_time,
                    'error_count': stats.error_count,
                    'status': self.stream_configurations[stream_id].status.value if stream_id in self.stream_configurations else 'unknown'
                }
            return {}
        else:
            # Return statistics for all streams
            all_stats = {}
            for stream_id, stats in self.stream_stats.items():
                all_stats[stream_id] = {
                    'frames_processed': stats.frames_processed,
                    'events_generated': stats.events_generated,
                    'fps': stats.fps,
                    'error_count': stats.error_count,
                    'status': self.stream_configurations[stream_id].status.value if stream_id in self.stream_configurations else 'unknown'
                }
            return all_stats
    
    def get_recent_events(self, stream_id: str = None, limit: int = 100,
                         event_type: AnalyticsType = None) -> List[AnalyticsEvent]:
        """Get recent analytics events with optional filtering"""
        events = list(self.event_buffer)
        
        # Filter by stream
        if stream_id:
            events = [e for e in events if e.stream_id == stream_id]
        
        # Filter by event type
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        # Sort by timestamp (most recent first)
        events.sort(key=lambda x: x.timestamp, reverse=True)
        
        return events[:limit]
    
    async def cleanup_old_data(self, retention_days: int = 30):
        """Clean up old analytics data based on retention policy"""
        try:
            cutoff_time = time.time() - (retention_days * 24 * 3600)
            
            if self.db_manager:
                # Clean up old events
                await self.db_manager.execute_query(
                    "DELETE FROM analytics_events WHERE timestamp < ?",
                    (cutoff_time,)
                )
                
                logger.info(f"Cleaned up analytics data older than {retention_days} days")
            
            # Clean up LPR data
            self.lpr.cleanup_old_data(retention_days)
            
        except Exception as e:
            logger.error(f"Error during analytics data cleanup: {e}")
    
    def start(self):
        """Start the analytics manager and all components"""
        try:
            # Start event dispatcher
            self.event_dispatcher.start()
            
            # Start frame processors
            for processor in self.frame_processors.values():
                processor.start()
            
            # Start performance monitoring
            self.performance_monitor.start()
            
            logger.info("Video Analytics Manager started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Video Analytics Manager: {e}")
    
    def stop(self):
        """Stop the analytics manager and cleanup resources"""
        try:
            # Stop event dispatcher
            self.event_dispatcher.stop()
            
            # Stop frame processors
            for processor in self.frame_processors.values():
                processor.stop()
            
            # Stop performance monitoring
            self.performance_monitor.stop()
            
            # Shutdown thread pool
            self.processing_executor.shutdown(wait=True)
            
            logger.info("Video Analytics Manager stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping Video Analytics Manager: {e}")

class PerformanceMonitor:
    def __init__(self):
        self.is_active = False
        self.monitor_thread = None
        self.metrics = {
            'cpu_usage': deque(maxlen=100),
            'memory_usage': deque(maxlen=100),
            'gpu_usage': deque(maxlen=100),
            'processing_latency': deque(maxlen=1000)
        }
    
    def start(self):
        if not self.is_active:
            self.is_active = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("Performance monitor started")
    
    def stop(self):
        self.is_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        logger.info("Performance monitor stopped")
    
    def _monitor_loop(self):
        import psutil
        
        while self.is_active:
            try:
                # Collect system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_percent = psutil.virtual_memory().percent
                
                self.metrics['cpu_usage'].append(cpu_percent)
                self.metrics['memory_usage'].append(memory_percent)
                
                time.sleep(5)  # Monitor every 5 seconds
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                time.sleep(1)

class RuleEngine:
    def __init__(self):
        self.rules = {}
        self.event_history = deque(maxlen=10000)
    
    def add_rule(self, rule_id: str, conditions: Dict[str, Any], actions: List[Dict[str, Any]]):
        self.rules[rule_id] = {
            'conditions': conditions,
            'actions': actions,
            'triggered_count': 0
        }
    
    def process_event(self, event: AnalyticsEvent):
        self.event_history.append(event)
        
        for rule_id, rule in self.rules.items():
            if self._evaluate_conditions(event, rule['conditions']):
                self._execute_actions(event, rule['actions'])
                rule['triggered_count'] += 1
    
    def _evaluate_conditions(self, event: AnalyticsEvent, conditions: Dict[str, Any]) -> bool:
        # Simple condition evaluation
        for key, value in conditions.items():
            if key == 'event_type':
                if event.event_type.value != value:
                    return False
            elif key == 'severity':
                if event.severity.value != value:
                    return False
            elif key == 'confidence_threshold':
                if event.confidence < value:
                    return False
        
        return True
    
    def _execute_actions(self, event: AnalyticsEvent, actions: List[Dict[str, Any]]):
        for action in actions:
            action_type = action.get('type')
            
            if action_type == 'log':
                logger.info(f"Rule triggered: {action.get('message', 'No message')}")
            elif action_type == 'alert':
                # Send alert (would integrate with alert manager)
                logger.warning(f"ALERT: {action.get('message', 'Analytics alert')}")

logger.info("Advanced Enterprise Video Analytics Management System loaded successfully")
