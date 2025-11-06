# Advanced Intrusion Detection and Perimeter Security System
# Enterprise-grade intrusion detection with behavioral analysis, threat classification, and multi-zone management

import cv2
import numpy as np
import logging
import time
import json
import sqlite3
import threading
import queue
import asyncio
from collections import defaultdict, deque
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any, Set, Union
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import math
import statistics

try:
    from scipy.spatial.distance import euclidean
    from scipy.signal import find_peaks
    from sklearn.cluster import DBSCAN
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

logger = logging.getLogger(__name__)

class ThreatLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class IntrusionType(Enum):
    UNAUTHORIZED_ENTRY = "unauthorized_entry"
    LOITERING = "loitering"
    PERIMETER_BREACH = "perimeter_breach"
    VEHICLE_INTRUSION = "vehicle_intrusion"
    GROUP_INTRUSION = "group_intrusion"
    RESTRICTED_AREA = "restricted_area"
    DIRECTION_VIOLATION = "direction_violation"
    SIZE_ANOMALY = "size_anomaly"
    SPEED_VIOLATION = "speed_violation"
    TIME_VIOLATION = "time_violation"

class ZoneType(Enum):
    RESTRICTED = "restricted"
    EXCLUSION = "exclusion"
    DETECTION = "detection"
    MONITORING = "monitoring"
    PERIMETER = "perimeter"
    ENTRANCE = "entrance"
    EXIT = "exit"
    PARKING = "parking"

@dataclass
class IntrusionEvent:
    event_id: str
    rule_id: str
    zone_id: str
    object_id: str
    object_type: str
    intrusion_type: IntrusionType
    threat_level: ThreatLevel
    timestamp: float
    duration: float
    entry_point: Tuple[int, int]
    current_position: Tuple[int, int]
    object_size: Tuple[int, int]
    confidence: float
    velocity: float
    direction: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolution_timestamp: Optional[float] = None

@dataclass
class SecurityZone:
    zone_id: str
    name: str
    zone_type: ZoneType
    points: List[Tuple[int, int]]
    enabled: bool = True
    sensitivity: float = 0.8
    alert_threshold_frames: int = 5
    min_object_size: int = 100
    max_object_size: int = 10000
    allowed_object_types: Set[str] = field(default_factory=set)
    restricted_times: List[Tuple[str, str]] = field(default_factory=list)
    max_occupancy: int = -1
    loitering_threshold: float = 60.0
    speed_limits: Tuple[float, float] = (0.0, float('inf'))
    directional_constraints: Optional[Tuple[float, float]] = None
    priority: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TrackedObject:
    object_id: str
    object_type: str
    confidence: float
    centroid: Tuple[int, int]
    bbox: Tuple[int, int, int, int]
    velocity: float
    direction: float
    size: Tuple[int, int]
    first_seen: float
    last_seen: float
    path: List[Tuple[int, int]]
    zone_history: List[Tuple[str, float]]
    properties: Dict[str, Any] = field(default_factory=dict)

class IntrusionTracker:
    def __init__(self):
        self.intruding_objects = defaultdict(lambda: defaultdict(dict))
        self.zone_occupancy = defaultdict(set)
        self.object_histories = {}
        self.event_queue = queue.Queue()
        
    def track_intrusion(self, zone_id: str, obj_id: str, zone: SecurityZone, obj: TrackedObject) -> Dict[str, Any]:
        if zone_id not in self.intruding_objects[obj_id]:
            self.intruding_objects[obj_id][zone_id] = {
                'frames_inside': 0,
                'entry_time': time.time(),
                'entry_point': obj.centroid,
                'max_confidence': obj.confidence,
                'path_inside': [obj.centroid],
                'violations': []
            }
        
        tracker = self.intruding_objects[obj_id][zone_id]
        tracker['frames_inside'] += 1
        tracker['last_position'] = obj.centroid
        tracker['path_inside'].append(obj.centroid)
        tracker['max_confidence'] = max(tracker['max_confidence'], obj.confidence)
        
        return tracker

    def check_violations(self, zone: SecurityZone, obj: TrackedObject, tracker: Dict[str, Any]) -> List[IntrusionType]:
        violations = []
        
        if tracker['frames_inside'] >= zone.alert_threshold_frames:
            violations.append(IntrusionType.UNAUTHORIZED_ENTRY)
        
        if time.time() - tracker['entry_time'] > zone.loitering_threshold:
            violations.append(IntrusionType.LOITERING)
        
        if obj.object_type not in zone.allowed_object_types and zone.allowed_object_types:
            violations.append(IntrusionType.RESTRICTED_AREA)
        
        obj_size = obj.size[0] * obj.size[1]
        if obj_size < zone.min_object_size or obj_size > zone.max_object_size:
            violations.append(IntrusionType.SIZE_ANOMALY)
        
        if obj.velocity < zone.speed_limits[0] or obj.velocity > zone.speed_limits[1]:
            violations.append(IntrusionType.SPEED_VIOLATION)
        
        if zone.directional_constraints:
            allowed_min, allowed_max = zone.directional_constraints
            if not (allowed_min <= obj.direction <= allowed_max):
                violations.append(IntrusionType.DIRECTION_VIOLATION)
        
        if self._is_time_restricted(zone):
            violations.append(IntrusionType.TIME_VIOLATION)
        
        current_occupancy = len(self.zone_occupancy[zone.zone_id])
        if zone.max_occupancy > 0 and current_occupancy > zone.max_occupancy:
            violations.append(IntrusionType.GROUP_INTRUSION)
        
        return violations

    def _is_time_restricted(self, zone: SecurityZone) -> bool:
        if not zone.restricted_times:
            return False
        
        current_time = datetime.now().strftime("%H:%M")
        
        for start_time, end_time in zone.restricted_times:
            if start_time <= current_time <= end_time:
                return True
        
        return False

    def clear_object(self, obj_id: str, zone_id: str = None):
        if zone_id:
            if obj_id in self.intruding_objects and zone_id in self.intruding_objects[obj_id]:
                del self.intruding_objects[obj_id][zone_id]
                if obj_id in self.zone_occupancy[zone_id]:
                    self.zone_occupancy[zone_id].remove(obj_id)
        else:
            if obj_id in self.intruding_objects:
                for zid in list(self.intruding_objects[obj_id].keys()):
                    if obj_id in self.zone_occupancy[zid]:
                        self.zone_occupancy[zid].remove(obj_id)
                del self.intruding_objects[obj_id]

class ThreatClassifier:
    def __init__(self):
        self.threat_weights = {
            IntrusionType.UNAUTHORIZED_ENTRY: 0.6,
            IntrusionType.LOITERING: 0.4,
            IntrusionType.PERIMETER_BREACH: 0.9,
            IntrusionType.VEHICLE_INTRUSION: 0.8,
            IntrusionType.GROUP_INTRUSION: 0.7,
            IntrusionType.RESTRICTED_AREA: 0.8,
            IntrusionType.DIRECTION_VIOLATION: 0.3,
            IntrusionType.SIZE_ANOMALY: 0.5,
            IntrusionType.SPEED_VIOLATION: 0.4,
            IntrusionType.TIME_VIOLATION: 0.6
        }
    
    def classify_threat(self, violations: List[IntrusionType], zone: SecurityZone, 
                       obj: TrackedObject, context: Dict[str, Any]) -> ThreatLevel:
        if not violations:
            return ThreatLevel.LOW
        
        threat_score = 0.0
        
        for violation in violations:
            weight = self.threat_weights.get(violation, 0.5)
            threat_score += weight
        
        zone_multiplier = 1.0
        if zone.zone_type == ZoneType.RESTRICTED:
            zone_multiplier = 1.5
        elif zone.zone_type == ZoneType.PERIMETER:
            zone_multiplier = 1.3
        elif zone.zone_type == ZoneType.EXCLUSION:
            zone_multiplier = 1.4
        
        priority_multiplier = zone.priority / 3.0
        
        confidence_factor = obj.confidence
        size_factor = min(obj.size[0] * obj.size[1] / 10000, 2.0)
        
        final_score = threat_score * zone_multiplier * priority_multiplier * confidence_factor * size_factor
        
        if final_score >= 3.0:
            return ThreatLevel.CRITICAL
        elif final_score >= 2.0:
            return ThreatLevel.HIGH
        elif final_score >= 1.0:
            return ThreatLevel.MEDIUM
        else:
            return ThreatLevel.LOW

class BehavioralAnalyzer:
    def __init__(self):
        self.behavior_history = defaultdict(list)
        self.suspicious_patterns = {
            'zigzag_movement': self._detect_zigzag,
            'prolonged_stationary': self._detect_prolonged_stationary,
            'rapid_direction_changes': self._detect_rapid_direction_changes,
            'boundary_testing': self._detect_boundary_testing,
            'group_coordination': self._detect_group_coordination
        }
    
    def analyze_behavior(self, obj: TrackedObject) -> Dict[str, float]:
        behavior_scores = {}
        
        if len(obj.path) < 5:
            return behavior_scores
        
        for pattern_name, detector in self.suspicious_patterns.items():
            score = detector(obj)
            behavior_scores[pattern_name] = score
        
        return behavior_scores
    
    def _detect_zigzag(self, obj: TrackedObject) -> float:
        if len(obj.path) < 10:
            return 0.0
        
        direction_changes = 0
        for i in range(2, len(obj.path)):
            p1, p2, p3 = obj.path[i-2:i+1]
            
            v1 = (p2[0] - p1[0], p2[1] - p1[1])
            v2 = (p3[0] - p2[0], p3[1] - p2[1])
            
            if np.linalg.norm(v1) > 5 and np.linalg.norm(v2) > 5:
                dot_product = np.dot(v1, v2)
                norms = np.linalg.norm(v1) * np.linalg.norm(v2)
                if norms > 0:
                    angle = np.arccos(np.clip(dot_product / norms, -1.0, 1.0))
                    if angle > np.pi / 3:
                        direction_changes += 1
        
        zigzag_ratio = direction_changes / max(len(obj.path) - 2, 1)
        return min(zigzag_ratio * 3, 1.0)
    
    def _detect_prolonged_stationary(self, obj: TrackedObject) -> float:
        if len(obj.path) < 5:
            return 0.0
        
        stationary_count = 0
        movement_threshold = 10
        
        for i in range(1, len(obj.path)):
            distance = np.linalg.norm(np.array(obj.path[i]) - np.array(obj.path[i-1]))
            if distance < movement_threshold:
                stationary_count += 1
        
        stationary_ratio = stationary_count / len(obj.path)
        
        duration_factor = min((obj.last_seen - obj.first_seen) / 30.0, 2.0)
        
        return min(stationary_ratio * duration_factor, 1.0)
    
    def _detect_rapid_direction_changes(self, obj: TrackedObject) -> float:
        if len(obj.path) < 6:
            return 0.0
        
        direction_changes = 0
        threshold_angle = np.pi / 4
        
        for i in range(2, len(obj.path) - 1):
            points = obj.path[i-2:i+2]
            
            if len(points) == 4:
                v1 = np.array(points[1]) - np.array(points[0])
                v2 = np.array(points[2]) - np.array(points[1])
                v3 = np.array(points[3]) - np.array(points[2])
                
                if np.linalg.norm(v1) > 3 and np.linalg.norm(v2) > 3 and np.linalg.norm(v3) > 3:
                    angle1 = self._calculate_angle(v1, v2)
                    angle2 = self._calculate_angle(v2, v3)
                    
                    if angle1 > threshold_angle and angle2 > threshold_angle:
                        direction_changes += 1
        
        change_ratio = direction_changes / max(len(obj.path) - 5, 1)
        return min(change_ratio * 2, 1.0)
    
    def _detect_boundary_testing(self, obj: TrackedObject) -> float:
        return 0.0
    
    def _detect_group_coordination(self, obj: TrackedObject) -> float:
        return 0.0
    
    def _calculate_angle(self, v1: np.ndarray, v2: np.ndarray) -> float:
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        return np.arccos(cos_angle)

class IntrusionDatabase:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = None
        self._setup_database()
    
    def _setup_database(self):
        self.connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
        cursor = self.connection.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_zones (
                zone_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                zone_type TEXT,
                points TEXT,
                enabled BOOLEAN,
                sensitivity REAL,
                alert_threshold_frames INTEGER,
                min_object_size INTEGER,
                max_object_size INTEGER,
                allowed_object_types TEXT,
                restricted_times TEXT,
                max_occupancy INTEGER,
                loitering_threshold REAL,
                speed_limits TEXT,
                directional_constraints TEXT,
                priority INTEGER,
                metadata TEXT,
                created_at REAL,
                updated_at REAL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS intrusion_events (
                event_id TEXT PRIMARY KEY,
                rule_id TEXT,
                zone_id TEXT,
                object_id TEXT,
                object_type TEXT,
                intrusion_type TEXT,
                threat_level TEXT,
                timestamp REAL,
                duration REAL,
                entry_point TEXT,
                current_position TEXT,
                object_size TEXT,
                confidence REAL,
                velocity REAL,
                direction REAL,
                metadata TEXT,
                resolved BOOLEAN,
                resolution_timestamp REAL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tracked_objects (
                object_id TEXT,
                zone_id TEXT,
                timestamp REAL,
                centroid TEXT,
                bbox TEXT,
                velocity REAL,
                direction REAL,
                confidence REAL,
                object_type TEXT,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS behavioral_analysis (
                analysis_id TEXT PRIMARY KEY,
                object_id TEXT,
                zone_id TEXT,
                timestamp REAL,
                behavior_type TEXT,
                confidence_score REAL,
                details TEXT,
                risk_level TEXT
            )
        """)
        
        self.connection.commit()
    
    def save_zone(self, zone: SecurityZone) -> bool:
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO security_zones 
                (zone_id, name, zone_type, points, enabled, sensitivity, alert_threshold_frames,
                 min_object_size, max_object_size, allowed_object_types, restricted_times,
                 max_occupancy, loitering_threshold, speed_limits, directional_constraints,
                 priority, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                zone.zone_id, zone.name, zone.zone_type.value, json.dumps(zone.points),
                zone.enabled, zone.sensitivity, zone.alert_threshold_frames,
                zone.min_object_size, zone.max_object_size, json.dumps(list(zone.allowed_object_types)),
                json.dumps(zone.restricted_times), zone.max_occupancy, zone.loitering_threshold,
                json.dumps(zone.speed_limits), json.dumps(zone.directional_constraints),
                zone.priority, json.dumps(zone.metadata), time.time(), time.time()
            ))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving zone: {e}")
            return False
    
    def save_event(self, event: IntrusionEvent) -> bool:
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO intrusion_events 
                (event_id, rule_id, zone_id, object_id, object_type, intrusion_type, threat_level,
                 timestamp, duration, entry_point, current_position, object_size, confidence,
                 velocity, direction, metadata, resolved, resolution_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id, event.rule_id, event.zone_id, event.object_id, event.object_type,
                event.intrusion_type.value, event.threat_level.value, event.timestamp, event.duration,
                json.dumps(event.entry_point), json.dumps(event.current_position),
                json.dumps(event.object_size), event.confidence, event.velocity, event.direction,
                json.dumps(event.metadata), event.resolved, event.resolution_timestamp
            ))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving event: {e}")
            return False
    
    def get_events(self, start_time: float = None, end_time: float = None, 
                   zone_id: str = None, threat_level: ThreatLevel = None) -> List[IntrusionEvent]:
        cursor = self.connection.cursor()
        
        query = "SELECT * FROM intrusion_events WHERE 1=1"
        params = []
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        
        if zone_id:
            query += " AND zone_id = ?"
            params.append(zone_id)
        
        if threat_level:
            query += " AND threat_level = ?"
            params.append(threat_level.value)
        
        query += " ORDER BY timestamp DESC"
        
        cursor.execute(query, params)
        events = []
        
        for row in cursor.fetchall():
            event = IntrusionEvent(
                event_id=row[0], rule_id=row[1], zone_id=row[2], object_id=row[3],
                object_type=row[4], intrusion_type=IntrusionType(row[5]),
                threat_level=ThreatLevel(row[6]), timestamp=row[7], duration=row[8],
                entry_point=tuple(json.loads(row[9])), current_position=tuple(json.loads(row[10])),
                object_size=tuple(json.loads(row[11])), confidence=row[12],
                velocity=row[13], direction=row[14], metadata=json.loads(row[15] or '{}'),
                resolved=row[16], resolution_timestamp=row[17]
            )
            events.append(event)
        
        return events

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            'total_detections': 0,
            'total_intrusions': 0,
            'false_positives': 0,
            'processing_times': deque(maxlen=1000),
            'zone_activity': defaultdict(int),
            'threat_distribution': defaultdict(int),
            'hourly_stats': defaultdict(int)
        }
    
    def record_detection(self, processing_time: float, zone_id: str, threat_level: ThreatLevel):
        self.metrics['total_detections'] += 1
        self.metrics['processing_times'].append(processing_time)
        self.metrics['zone_activity'][zone_id] += 1
        self.metrics['threat_distribution'][threat_level.value] += 1
        
        hour = datetime.now().hour
        self.metrics['hourly_stats'][hour] += 1
    
    def get_performance_summary(self) -> Dict[str, Any]:
        if not self.metrics['processing_times']:
            avg_processing_time = 0
        else:
            avg_processing_time = statistics.mean(self.metrics['processing_times'])
        
        return {
            'total_detections': self.metrics['total_detections'],
            'total_intrusions': self.metrics['total_intrusions'],
            'false_positive_rate': self.metrics['false_positives'] / max(self.metrics['total_detections'], 1),
            'avg_processing_time': avg_processing_time,
            'fps': 1.0 / avg_processing_time if avg_processing_time > 0 else 0.0,
            'zone_activity': dict(self.metrics['zone_activity']),
            'threat_distribution': dict(self.metrics['threat_distribution']),
            'hourly_stats': dict(self.metrics['hourly_stats'])
        }

class IntrusionDetector:
    def __init__(self, rule_id: str, points: List[List[int]], config: Dict[str, Any] = None):
        self.rule_id = rule_id
        self.zone = SecurityZone(
            zone_id=rule_id,
            name=config.get('name', f'Zone_{rule_id}') if config else f'Zone_{rule_id}',
            zone_type=ZoneType(config.get('zone_type', 'detection')) if config else ZoneType.DETECTION,
            points=[(p[0], p[1]) for p in points],
            **({k: v for k, v in config.items() if k in SecurityZone.__dataclass_fields__} if config else {})
        )
        
        self.config = config or {}
        self.tracker = IntrusionTracker()
        self.threat_classifier = ThreatClassifier()
        self.behavioral_analyzer = BehavioralAnalyzer()
        
        db_path = self.config.get('database_path', '/var/lib/agropulse/intrusion.db')
        self.database = IntrusionDatabase(db_path)
        
        self.performance_monitor = PerformanceMonitor()
        
        self.zone_polygon = np.array(self.zone.points, dtype=np.int32)
        
        self.active_events = {}
        self.event_callbacks = []
        
        self.database.save_zone(self.zone)
        
        logger.info(f"Advanced Intrusion Detector initialized for zone {rule_id}")
    
    def update(self, tracked_objects: Dict[str, Tuple[int, int]], 
               object_details: Dict[str, Dict[str, Any]] = None) -> List[IntrusionEvent]:
        start_time = time.time()
        
        if object_details is None:
            object_details = {}
        
        intrusion_events = []
        current_ids = set(tracked_objects.keys())
        
        for obj_id, centroid in tracked_objects.items():
            details = object_details.get(obj_id, {})
            
            tracked_obj = TrackedObject(
                object_id=obj_id,
                object_type=details.get('type', 'unknown'),
                confidence=details.get('confidence', 0.8),
                centroid=centroid,
                bbox=details.get('bbox', (centroid[0]-25, centroid[1]-25, 50, 50)),
                velocity=details.get('velocity', 0.0),
                direction=details.get('direction', 0.0),
                size=details.get('size', (50, 50)),
                first_seen=details.get('first_seen', time.time()),
                last_seen=time.time(),
                path=details.get('path', [centroid]),
                zone_history=details.get('zone_history', []),
                properties=details.get('properties', {})
            )
            
            is_inside = cv2.pointPolygonTest(self.zone_polygon, centroid, False) >= 0
            
            if is_inside:
                self.tracker.zone_occupancy[self.zone.zone_id].add(obj_id)
                
                tracker = self.tracker.track_intrusion(self.zone.zone_id, obj_id, self.zone, tracked_obj)
                
                violations = self.tracker.check_violations(self.zone, tracked_obj, tracker)
                
                if violations:
                    behavior_scores = self.behavioral_analyzer.analyze_behavior(tracked_obj)
                    
                    threat_level = self.threat_classifier.classify_threat(
                        violations, self.zone, tracked_obj, {'behavior': behavior_scores}
                    )
                    
                    for violation_type in violations:
                        event_id = f"{self.zone.zone_id}_{obj_id}_{violation_type.value}_{int(time.time())}"
                        
                        if event_id not in self.active_events:
                            event = IntrusionEvent(
                                event_id=event_id,
                                rule_id=self.rule_id,
                                zone_id=self.zone.zone_id,
                                object_id=obj_id,
                                object_type=tracked_obj.object_type,
                                intrusion_type=violation_type,
                                threat_level=threat_level,
                                timestamp=time.time(),
                                duration=time.time() - tracker['entry_time'],
                                entry_point=tracker['entry_point'],
                                current_position=centroid,
                                object_size=tracked_obj.size,
                                confidence=tracked_obj.confidence,
                                velocity=tracked_obj.velocity,
                                direction=tracked_obj.direction,
                                metadata={
                                    'behavior_scores': behavior_scores,
                                    'zone_name': self.zone.name,
                                    'frames_inside': tracker['frames_inside'],
                                    'path_length': len(tracker['path_inside'])
                                }
                            )
                            
                            self.active_events[event_id] = event
                            intrusion_events.append(event)
                            
                            self.database.save_event(event)
                            
                            self._trigger_callbacks(event)
            else:
                if obj_id in self.tracker.zone_occupancy[self.zone.zone_id]:
                    self.tracker.zone_occupancy[self.zone.zone_id].remove(obj_id)
                
                self.tracker.clear_object(obj_id, self.zone.zone_id)
        
        disappeared_ids = set(self.tracker.intruding_objects.keys()) - current_ids
        for obj_id in disappeared_ids:
            self.tracker.clear_object(obj_id)
            if obj_id in self.tracker.zone_occupancy[self.zone.zone_id]:
                self.tracker.zone_occupancy[self.zone.zone_id].remove(obj_id)
        
        processing_time = time.time() - start_time
        
        for event in intrusion_events:
            self.performance_monitor.record_detection(processing_time, self.zone.zone_id, event.threat_level)
        
        self._cleanup_resolved_events()
        
        return intrusion_events
    
    def _trigger_callbacks(self, event: IntrusionEvent):
        for callback in self.event_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")
    
    def _cleanup_resolved_events(self):
        current_time = time.time()
        resolved_events = []
        
        for event_id, event in list(self.active_events.items()):
            if current_time - event.timestamp > 300:
                event.resolved = True
                event.resolution_timestamp = current_time
                resolved_events.append(event_id)
        
        for event_id in resolved_events:
            del self.active_events[event_id]
    
    def add_event_callback(self, callback):
        self.event_callbacks.append(callback)
    
    def get_zone_statistics(self) -> Dict[str, Any]:
        return {
            'zone_id': self.zone.zone_id,
            'zone_name': self.zone.name,
            'zone_type': self.zone.zone_type.value,
            'current_occupancy': len(self.tracker.zone_occupancy[self.zone.zone_id]),
            'active_events': len(self.active_events),
            'performance': self.performance_monitor.get_performance_summary(),
            'zone_config': asdict(self.zone)
        }
    
    def update_zone_config(self, config: Dict[str, Any]):
        for key, value in config.items():
            if hasattr(self.zone, key):
                setattr(self.zone, value)
        
        self.database.save_zone(self.zone)
        logger.info(f"Updated configuration for zone {self.zone.zone_id}")
    
    def get_recent_events(self, hours: int = 24) -> List[IntrusionEvent]:
        start_time = time.time() - (hours * 3600)
        return self.database.get_events(start_time=start_time, zone_id=self.zone.zone_id)
    
    def resolve_event(self, event_id: str):
        if event_id in self.active_events:
            event = self.active_events[event_id]
            event.resolved = True
            event.resolution_timestamp = time.time()
            
            self.database.save_event(event)
            del self.active_events[event_id]
            
            logger.info(f"Resolved event {event_id}")
    
    def draw_zone(self, frame: np.ndarray, color: Tuple[int, int, int] = (0, 255, 0), 
                  thickness: int = 2, show_info: bool = True) -> np.ndarray:
        annotated_frame = frame.copy()
        
        cv2.polylines(annotated_frame, [self.zone_polygon], True, color, thickness)
        
        if show_info:
            occupancy = len(self.tracker.zone_occupancy[self.zone.zone_id])
            active_events = len(self.active_events)
            
            info_text = f"{self.zone.name}: {occupancy} objects, {active_events} events"
            
            text_size = cv2.getTextSize(info_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            
            zone_center = np.mean(self.zone_polygon, axis=0).astype(int)
            text_pos = (zone_center[0] - text_size[0]//2, zone_center[1])
            
            cv2.rectangle(annotated_frame, 
                         (text_pos[0] - 5, text_pos[1] - text_size[1] - 5),
                         (text_pos[0] + text_size[0] + 5, text_pos[1] + 5),
                         (0, 0, 0), -1)
            
            cv2.putText(annotated_frame, info_text, text_pos, 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return annotated_frame

logger.info("Advanced Intrusion Detection System loaded successfully")
