# Advanced Line Crossing Detection and Traffic Analytics System
# Enterprise-grade line crossing detection with directional analysis, traffic counting, and behavioral analytics

import cv2
import numpy as np
import logging
import time
import json
import sqlite3
import threading
import queue
import asyncio
import math
from collections import defaultdict, deque
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any, Set, Union
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import statistics

try:
    from scipy.spatial.distance import euclidean
    from scipy.interpolate import interp1d
    from sklearn.cluster import DBSCAN
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

logger = logging.getLogger(__name__)

class CrossingDirection(Enum):
    LEFT_TO_RIGHT = "left_to_right"
    RIGHT_TO_LEFT = "right_to_left"
    TOP_TO_BOTTOM = "top_to_bottom"
    BOTTOM_TO_TOP = "bottom_to_top"
    BIDIRECTIONAL = "bidirectional"
    UNKNOWN = "unknown"

class CrossingType(Enum):
    ENTRY = "entry"
    EXIT = "exit"
    TRANSIT = "transit"
    LOITERING = "loitering"
    REVERSE = "reverse"
    VIOLATION = "violation"

class LineType(Enum):
    COUNTING = "counting"
    SECURITY = "security"
    TRAFFIC = "traffic"
    PERIMETER = "perimeter"
    ENTRANCE = "entrance"
    EXIT = "exit"
    BIDIRECTIONAL = "bidirectional"

@dataclass
class CrossingEvent:
    event_id: str
    rule_id: str
    line_id: str
    object_id: str
    object_type: str
    crossing_type: CrossingType
    direction: CrossingDirection
    timestamp: float
    crossing_point: Tuple[int, int]
    entry_point: Tuple[int, int]
    exit_point: Tuple[int, int]
    velocity: float
    angle: float
    confidence: float
    duration: float
    path_length: float
    object_size: Tuple[int, int]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TrafficLine:
    line_id: str
    name: str
    line_type: LineType
    start_point: Tuple[int, int]
    end_point: Tuple[int, int]
    enabled: bool = True
    allowed_directions: Set[CrossingDirection] = field(default_factory=set)
    restricted_times: List[Tuple[str, str]] = field(default_factory=list)
    min_object_size: int = 50
    max_object_size: int = 10000
    allowed_object_types: Set[str] = field(default_factory=set)
    confidence_threshold: float = 0.5
    sensitivity: float = 0.8
    buffer_zone: int = 10
    debounce_time: float = 1.0
    speed_limits: Tuple[float, float] = (0.0, float('inf'))
    priority: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TrackedCrossing:
    object_id: str
    line_id: str
    start_time: float
    last_update: float
    positions: List[Tuple[int, int]]
    line_positions: List[int]
    velocities: List[float]
    confidences: List[float]
    object_type: str
    bbox_history: List[Tuple[int, int, int, int]]
    predicted_direction: Optional[CrossingDirection] = None
    crossing_confidence: float = 0.0

class GeometryUtils:
    @staticmethod
    def point_line_distance(point: Tuple[int, int], line_start: Tuple[int, int], 
                          line_end: Tuple[int, int]) -> float:
        x0, y0 = point
        x1, y1 = line_start
        x2, y2 = line_end
        
        if x1 == x2 and y1 == y2:
            return math.sqrt((x0 - x1)**2 + (y0 - y1)**2)
        
        A = y2 - y1
        B = x1 - x2
        C = x2 * y1 - x1 * y2
        
        distance = abs(A * x0 + B * y0 + C) / math.sqrt(A**2 + B**2)
        return distance
    
    @staticmethod
    def line_intersection(line1_start: Tuple[int, int], line1_end: Tuple[int, int],
                         line2_start: Tuple[int, int], line2_end: Tuple[int, int]) -> Optional[Tuple[float, float]]:
        x1, y1 = line1_start
        x2, y2 = line1_end
        x3, y3 = line2_start
        x4, y4 = line2_end
        
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        
        if abs(denom) < 1e-10:
            return None
        
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
        
        if 0 <= t <= 1 and 0 <= u <= 1:
            intersection_x = x1 + t * (x2 - x1)
            intersection_y = y1 + t * (y2 - y1)
            return (intersection_x, intersection_y)
        
        return None
    
    @staticmethod
    def calculate_angle(point1: Tuple[int, int], point2: Tuple[int, int]) -> float:
        dx = point2[0] - point1[0]
        dy = point2[1] - point1[1]
        angle = math.atan2(dy, dx)
        return math.degrees(angle) % 360
    
    @staticmethod
    def calculate_velocity(positions: List[Tuple[int, int]], timestamps: List[float]) -> float:
        if len(positions) < 2:
            return 0.0
        
        total_distance = 0.0
        for i in range(1, len(positions)):
            distance = math.sqrt((positions[i][0] - positions[i-1][0])**2 + 
                               (positions[i][1] - positions[i-1][1])**2)
            total_distance += distance
        
        total_time = timestamps[-1] - timestamps[0]
        return total_distance / total_time if total_time > 0 else 0.0

class PathPredictor:
    def __init__(self):
        self.prediction_window = 10
        
    def predict_crossing(self, tracked_crossing: TrackedCrossing, 
                        line: TrafficLine) -> Tuple[CrossingDirection, float]:
        if len(tracked_crossing.positions) < 3:
            return CrossingDirection.UNKNOWN, 0.0
        
        positions = tracked_crossing.positions[-self.prediction_window:]
        
        direction_vector = self._calculate_direction_vector(positions)
        
        crossing_point = self._predict_intersection(positions, line)
        
        if crossing_point is None:
            return CrossingDirection.UNKNOWN, 0.0
        
        direction = self._classify_direction(direction_vector, line)
        
        confidence = self._calculate_confidence(tracked_crossing, direction_vector)
        
        return direction, confidence
    
    def _calculate_direction_vector(self, positions: List[Tuple[int, int]]) -> np.ndarray:
        if len(positions) < 2:
            return np.array([0, 0])
        
        vectors = []
        for i in range(1, len(positions)):
            vector = np.array([positions[i][0] - positions[i-1][0], 
                             positions[i][1] - positions[i-1][1]])
            if np.linalg.norm(vector) > 0:
                vectors.append(vector / np.linalg.norm(vector))
        
        if not vectors:
            return np.array([0, 0])
        
        return np.mean(vectors, axis=0)
    
    def _predict_intersection(self, positions: List[Tuple[int, int]], 
                            line: TrafficLine) -> Optional[Tuple[float, float]]:
        if len(positions) < 2:
            return None
        
        direction_vector = self._calculate_direction_vector(positions)
        
        if np.linalg.norm(direction_vector) < 0.1:
            return None
        
        last_position = positions[-1]
        
        future_point = (last_position[0] + direction_vector[0] * 100,
                       last_position[1] + direction_vector[1] * 100)
        
        intersection = GeometryUtils.line_intersection(
            last_position, future_point, line.start_point, line.end_point
        )
        
        return intersection
    
    def _classify_direction(self, direction_vector: np.ndarray, 
                          line: TrafficLine) -> CrossingDirection:
        if np.linalg.norm(direction_vector) < 0.1:
            return CrossingDirection.UNKNOWN
        
        line_vector = np.array([line.end_point[0] - line.start_point[0],
                               line.end_point[1] - line.start_point[1]])
        
        if np.linalg.norm(line_vector) < 0.1:
            return CrossingDirection.UNKNOWN
        
        line_vector = line_vector / np.linalg.norm(line_vector)
        
        cross_product = np.cross(direction_vector, line_vector)
        
        if abs(cross_product) < 0.3:
            dot_product = np.dot(direction_vector, line_vector)
            return CrossingDirection.TOP_TO_BOTTOM if dot_product > 0 else CrossingDirection.BOTTOM_TO_TOP
        
        return CrossingDirection.LEFT_TO_RIGHT if cross_product > 0 else CrossingDirection.RIGHT_TO_LEFT
    
    def _calculate_confidence(self, tracked_crossing: TrackedCrossing, 
                            direction_vector: np.ndarray) -> float:
        if len(tracked_crossing.positions) < 3:
            return 0.0
        
        consistency_score = np.linalg.norm(direction_vector)
        
        velocity_consistency = 1.0
        if len(tracked_crossing.velocities) > 1:
            velocity_std = np.std(tracked_crossing.velocities)
            velocity_mean = np.mean(tracked_crossing.velocities)
            if velocity_mean > 0:
                velocity_consistency = max(0, 1 - (velocity_std / velocity_mean))
        
        confidence_consistency = np.mean(tracked_crossing.confidences) if tracked_crossing.confidences else 0.0
        
        path_length = len(tracked_crossing.positions)
        length_factor = min(path_length / 10.0, 1.0)
        
        overall_confidence = (consistency_score * 0.4 + 
                            velocity_consistency * 0.3 + 
                            confidence_consistency * 0.2 + 
                            length_factor * 0.1)
        
        return max(0.0, min(1.0, overall_confidence))

class TrafficCounter:
    def __init__(self):
        self.counts = defaultdict(lambda: defaultdict(int))
        self.hourly_counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        self.daily_counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        self.reset_time = time.time()
    
    def record_crossing(self, line_id: str, direction: CrossingDirection, 
                       object_type: str, timestamp: float = None):
        if timestamp is None:
            timestamp = time.time()
        
        dt = datetime.fromtimestamp(timestamp)
        hour_key = dt.strftime("%Y-%m-%d_%H")
        day_key = dt.strftime("%Y-%m-%d")
        
        self.counts[line_id][direction.value] += 1
        self.hourly_counts[line_id][hour_key][direction.value] += 1
        self.daily_counts[line_id][day_key][direction.value] += 1
        
        type_key = f"{direction.value}_{object_type}"
        self.counts[line_id][type_key] += 1
        self.hourly_counts[line_id][hour_key][type_key] += 1
        self.daily_counts[line_id][day_key][type_key] += 1
    
    def get_counts(self, line_id: str = None, period: str = "total") -> Dict[str, Any]:
        if period == "total":
            source = self.counts
        elif period == "hourly":
            source = self.hourly_counts
        elif period == "daily":
            source = self.daily_counts
        else:
            source = self.counts
        
        if line_id:
            return dict(source.get(line_id, {}))
        else:
            return {lid: dict(counts) for lid, counts in source.items()}
    
    def reset_counts(self, line_id: str = None):
        if line_id:
            self.counts[line_id].clear()
            self.hourly_counts[line_id].clear()
            self.daily_counts[line_id].clear()
        else:
            self.counts.clear()
            self.hourly_counts.clear()
            self.daily_counts.clear()
        
        self.reset_time = time.time()

class CrossingDatabase:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = None
        self._setup_database()
    
    def _setup_database(self):
        self.connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
        cursor = self.connection.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS traffic_lines (
                line_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                line_type TEXT,
                start_point TEXT,
                end_point TEXT,
                enabled BOOLEAN,
                allowed_directions TEXT,
                restricted_times TEXT,
                min_object_size INTEGER,
                max_object_size INTEGER,
                allowed_object_types TEXT,
                confidence_threshold REAL,
                sensitivity REAL,
                buffer_zone INTEGER,
                debounce_time REAL,
                speed_limits TEXT,
                priority INTEGER,
                metadata TEXT,
                created_at REAL,
                updated_at REAL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crossing_events (
                event_id TEXT PRIMARY KEY,
                rule_id TEXT,
                line_id TEXT,
                object_id TEXT,
                object_type TEXT,
                crossing_type TEXT,
                direction TEXT,
                timestamp REAL,
                crossing_point TEXT,
                entry_point TEXT,
                exit_point TEXT,
                velocity REAL,
                angle REAL,
                confidence REAL,
                duration REAL,
                path_length REAL,
                object_size TEXT,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS traffic_statistics (
                stat_id TEXT PRIMARY KEY,
                line_id TEXT,
                date_hour TEXT,
                direction TEXT,
                object_type TEXT,
                count INTEGER,
                avg_velocity REAL,
                avg_size REAL,
                peak_time TEXT,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crossing_violations (
                violation_id TEXT PRIMARY KEY,
                event_id TEXT,
                violation_type TEXT,
                severity TEXT,
                timestamp REAL,
                description TEXT,
                metadata TEXT
            )
        """)
        
        self.connection.commit()
    
    def save_line(self, line: TrafficLine) -> bool:
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO traffic_lines 
                (line_id, name, line_type, start_point, end_point, enabled, allowed_directions,
                 restricted_times, min_object_size, max_object_size, allowed_object_types,
                 confidence_threshold, sensitivity, buffer_zone, debounce_time, speed_limits,
                 priority, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                line.line_id, line.name, line.line_type.value, json.dumps(line.start_point),
                json.dumps(line.end_point), line.enabled, json.dumps([d.value for d in line.allowed_directions]),
                json.dumps(line.restricted_times), line.min_object_size, line.max_object_size,
                json.dumps(list(line.allowed_object_types)), line.confidence_threshold,
                line.sensitivity, line.buffer_zone, line.debounce_time, json.dumps(line.speed_limits),
                line.priority, json.dumps(line.metadata), time.time(), time.time()
            ))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving line: {e}")
            return False
    
    def save_event(self, event: CrossingEvent) -> bool:
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO crossing_events 
                (event_id, rule_id, line_id, object_id, object_type, crossing_type, direction,
                 timestamp, crossing_point, entry_point, exit_point, velocity, angle, confidence,
                 duration, path_length, object_size, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id, event.rule_id, event.line_id, event.object_id, event.object_type,
                event.crossing_type.value, event.direction.value, event.timestamp,
                json.dumps(event.crossing_point), json.dumps(event.entry_point),
                json.dumps(event.exit_point), event.velocity, event.angle, event.confidence,
                event.duration, event.path_length, json.dumps(event.object_size),
                json.dumps(event.metadata)
            ))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving event: {e}")
            return False
    
    def get_events(self, start_time: float = None, end_time: float = None,
                   line_id: str = None, direction: CrossingDirection = None) -> List[CrossingEvent]:
        cursor = self.connection.cursor()
        
        query = "SELECT * FROM crossing_events WHERE 1=1"
        params = []
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        
        if line_id:
            query += " AND line_id = ?"
            params.append(line_id)
        
        if direction:
            query += " AND direction = ?"
            params.append(direction.value)
        
        query += " ORDER BY timestamp DESC"
        
        cursor.execute(query, params)
        events = []
        
        for row in cursor.fetchall():
            event = CrossingEvent(
                event_id=row[0], rule_id=row[1], line_id=row[2], object_id=row[3],
                object_type=row[4], crossing_type=CrossingType(row[5]),
                direction=CrossingDirection(row[6]), timestamp=row[7],
                crossing_point=tuple(json.loads(row[8])), entry_point=tuple(json.loads(row[9])),
                exit_point=tuple(json.loads(row[10])), velocity=row[11], angle=row[12],
                confidence=row[13], duration=row[14], path_length=row[15],
                object_size=tuple(json.loads(row[16])), metadata=json.loads(row[17] or '{}')
            )
            events.append(event)
        
        return events

class PerformanceAnalyzer:
    def __init__(self):
        self.processing_times = deque(maxlen=1000)
        self.detection_accuracy = deque(maxlen=100)
        self.false_positive_rate = 0.0
        self.total_detections = 0
        self.successful_crossings = 0
    
    def record_processing_time(self, processing_time: float):
        self.processing_times.append(processing_time)
    
    def record_detection(self, accuracy: float, is_false_positive: bool = False):
        self.detection_accuracy.append(accuracy)
        self.total_detections += 1
        
        if not is_false_positive:
            self.successful_crossings += 1
        
        if self.total_detections > 0:
            self.false_positive_rate = (self.total_detections - self.successful_crossings) / self.total_detections
    
    def get_performance_metrics(self) -> Dict[str, float]:
        return {
            'avg_processing_time': statistics.mean(self.processing_times) if self.processing_times else 0.0,
            'max_processing_time': max(self.processing_times) if self.processing_times else 0.0,
            'fps': 1.0 / statistics.mean(self.processing_times) if self.processing_times and statistics.mean(self.processing_times) > 0 else 0.0,
            'avg_accuracy': statistics.mean(self.detection_accuracy) if self.detection_accuracy else 0.0,
            'false_positive_rate': self.false_positive_rate,
            'success_rate': self.successful_crossings / max(self.total_detections, 1),
            'total_detections': self.total_detections
        }

class LineCrossingDetector:
    def __init__(self, rule_id: str, points: List[List[int]], config: Dict[str, Any] = None):
        self.rule_id = rule_id
        
        if len(points) < 2:
            raise ValueError("Line crossing requires at least 2 points")
        
        self.line = TrafficLine(
            line_id=rule_id,
            name=config.get('name', f'Line_{rule_id}') if config else f'Line_{rule_id}',
            line_type=LineType(config.get('line_type', 'counting')) if config else LineType.COUNTING,
            start_point=tuple(points[0]),
            end_point=tuple(points[1]),
            **({k: v for k, v in config.items() if k in TrafficLine.__dataclass_fields__} if config else {})
        )
        
        self.config = config or {}
        
        self.previous_positions = defaultdict(int)
        self.crossed_ids = set()
        self.active_crossings = {}
        self.recent_crossings = deque(maxlen=100)
        
        self.path_predictor = PathPredictor()
        self.traffic_counter = TrafficCounter()
        
        db_path = self.config.get('database_path', '/var/lib/agropulse/crossings.db')
        self.database = CrossingDatabase(db_path)
        
        self.performance_analyzer = PerformanceAnalyzer()
        
        self.event_callbacks = []
        
        self.database.save_line(self.line)
        
        logger.info(f"Advanced Line Crossing Detector initialized for line {rule_id}")
    
    def _get_position(self, point: Tuple[int, int]) -> int:
        """Determines if a point is to the left (-1), on (0), or right (1) of the line."""
        x, y = point
        x1, y1 = self.line.start_point
        x2, y2 = self.line.end_point
        val = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
        if val > 0: 
            return 1  # Right side
        if val < 0: 
            return -1  # Left side
        return 0  # On the line
    
    def _is_near_line(self, point: Tuple[int, int]) -> bool:
        distance = GeometryUtils.point_line_distance(point, self.line.start_point, self.line.end_point)
        return distance <= self.line.buffer_zone
    
    def _validate_crossing(self, obj_id: str, object_details: Dict[str, Any]) -> bool:
        if not self.line.enabled:
            return False
        
        obj_type = object_details.get('type', 'unknown')
        if self.line.allowed_object_types and obj_type not in self.line.allowed_object_types:
            return False
        
        confidence = object_details.get('confidence', 0.0)
        if confidence < self.line.confidence_threshold:
            return False
        
        obj_size = object_details.get('size', (0, 0))
        size_area = obj_size[0] * obj_size[1]
        if size_area < self.line.min_object_size or size_area > self.line.max_object_size:
            return False
        
        velocity = object_details.get('velocity', 0.0)
        if velocity < self.line.speed_limits[0] or velocity > self.line.speed_limits[1]:
            return False
        
        if self._is_time_restricted():
            return False
        
        return True
    
    def _is_time_restricted(self) -> bool:
        if not self.line.restricted_times:
            return False
        
        current_time = datetime.now().strftime("%H:%M")
        
        for start_time, end_time in self.line.restricted_times:
            if start_time <= current_time <= end_time:
                return True
        
        return False
    
    def update(self, tracked_objects: Dict[str, Tuple[int, int]], 
               object_details: Dict[str, Dict[str, Any]] = None) -> List[CrossingEvent]:
        start_time = time.time()
        
        if object_details is None:
            object_details = {}
        
        crossing_events = []
        current_ids = set(tracked_objects.keys())
        
        for obj_id, centroid in tracked_objects.items():
            details = object_details.get(obj_id, {})
            
            if not self._validate_crossing(obj_id, details):
                continue
            
            current_pos = self._get_position(centroid)
            prev_pos = self.previous_positions.get(obj_id)
            
            if obj_id in self.active_crossings:
                self._update_active_crossing(obj_id, centroid, details, current_pos)
            
            if self._is_near_line(centroid) and obj_id not in self.active_crossings:
                self._start_tracking_crossing(obj_id, centroid, details, current_pos)
            
            if (prev_pos is not None and current_pos != prev_pos and 
                current_pos != 0 and prev_pos != 0 and obj_id not in self.crossed_ids):
                
                crossing_event = self._process_crossing(obj_id, centroid, details, 
                                                      current_pos, prev_pos)
                if crossing_event:
                    crossing_events.append(crossing_event)
            
            self.previous_positions[obj_id] = current_pos
        
        self._cleanup_expired_crossings(current_ids)
        
        processing_time = time.time() - start_time
        self.performance_analyzer.record_processing_time(processing_time)
        
        return crossing_events
    
    def _start_tracking_crossing(self, obj_id: str, centroid: Tuple[int, int],
                               details: Dict[str, Any], current_pos: int):
        self.active_crossings[obj_id] = TrackedCrossing(
            object_id=obj_id,
            line_id=self.line.line_id,
            start_time=time.time(),
            last_update=time.time(),
            positions=[centroid],
            line_positions=[current_pos],
            velocities=[details.get('velocity', 0.0)],
            confidences=[details.get('confidence', 0.0)],
            object_type=details.get('type', 'unknown'),
            bbox_history=[details.get('bbox', (0, 0, 0, 0))]
        )
    
    def _update_active_crossing(self, obj_id: str, centroid: Tuple[int, int],
                              details: Dict[str, Any], current_pos: int):
        crossing = self.active_crossings[obj_id]
        crossing.last_update = time.time()
        crossing.positions.append(centroid)
        crossing.line_positions.append(current_pos)
        crossing.velocities.append(details.get('velocity', 0.0))
        crossing.confidences.append(details.get('confidence', 0.0))
        crossing.bbox_history.append(details.get('bbox', (0, 0, 0, 0)))
        
        if len(crossing.positions) >= 3:
            direction, confidence = self.path_predictor.predict_crossing(crossing, self.line)
            crossing.predicted_direction = direction
            crossing.crossing_confidence = confidence
    
    def _process_crossing(self, obj_id: str, centroid: Tuple[int, int],
                         details: Dict[str, Any], current_pos: int, prev_pos: int) -> Optional[CrossingEvent]:
        
        direction = CrossingDirection.RIGHT_TO_LEFT if current_pos == -1 else CrossingDirection.LEFT_TO_RIGHT
        
        if self.line.allowed_directions and direction not in self.line.allowed_directions:
            return None
        
        crossing_type = self._classify_crossing_type(obj_id, direction, details)
        
        crossing_point = self._calculate_crossing_point(obj_id, centroid)
        
        path_length = 0.0
        duration = 0.0
        entry_point = centroid
        exit_point = centroid
        
        if obj_id in self.active_crossings:
            crossing = self.active_crossings[obj_id]
            duration = time.time() - crossing.start_time
            
            if len(crossing.positions) > 1:
                path_length = sum(
                    math.sqrt((crossing.positions[i][0] - crossing.positions[i-1][0])**2 +
                             (crossing.positions[i][1] - crossing.positions[i-1][1])**2)
                    for i in range(1, len(crossing.positions))
                )
                entry_point = crossing.positions[0]
                exit_point = crossing.positions[-1]
        
        velocity = details.get('velocity', 0.0)
        angle = GeometryUtils.calculate_angle(entry_point, exit_point) if entry_point != exit_point else 0.0
        
        event = CrossingEvent(
            event_id=f"{self.line.line_id}_{obj_id}_{int(time.time())}",
            rule_id=self.rule_id,
            line_id=self.line.line_id,
            object_id=obj_id,
            object_type=details.get('type', 'unknown'),
            crossing_type=crossing_type,
            direction=direction,
            timestamp=time.time(),
            crossing_point=crossing_point,
            entry_point=entry_point,
            exit_point=exit_point,
            velocity=velocity,
            angle=angle,
            confidence=details.get('confidence', 0.0),
            duration=duration,
            path_length=path_length,
            object_size=details.get('size', (0, 0)),
            metadata={
                'line_name': self.line.name,
                'line_type': self.line.line_type.value,
                'prediction_confidence': self.active_crossings.get(obj_id, TrackedCrossing("", "", 0, 0, [], [], [], [], "", [])).crossing_confidence
            }
        )
        
        self.crossed_ids.add(obj_id)
        self.recent_crossings.append(event)
        
        self.traffic_counter.record_crossing(self.line.line_id, direction, 
                                           details.get('type', 'unknown'))
        
        self.database.save_event(event)
        
        self._trigger_callbacks(event)
        
        if obj_id in self.active_crossings:
            del self.active_crossings[obj_id]
        
        self.performance_analyzer.record_detection(event.confidence)
        
        logger.info(f"Line crossing detected: {obj_id} crossed {self.line.name} {direction.value}")
        
        return event
    
    def _classify_crossing_type(self, obj_id: str, direction: CrossingDirection,
                              details: Dict[str, Any]) -> CrossingType:
        if self.line.line_type == LineType.ENTRANCE and direction == CrossingDirection.LEFT_TO_RIGHT:
            return CrossingType.ENTRY
        elif self.line.line_type == LineType.EXIT and direction == CrossingDirection.RIGHT_TO_LEFT:
            return CrossingType.EXIT
        elif obj_id in self.recent_crossings:
            return CrossingType.REVERSE
        else:
            return CrossingType.TRANSIT
    
    def _calculate_crossing_point(self, obj_id: str, current_centroid: Tuple[int, int]) -> Tuple[int, int]:
        if obj_id in self.active_crossings:
            crossing = self.active_crossings[obj_id]
            if len(crossing.positions) > 1:
                last_pos = crossing.positions[-2]
                intersection = GeometryUtils.line_intersection(
                    last_pos, current_centroid, self.line.start_point, self.line.end_point
                )
                if intersection:
                    return (int(intersection[0]), int(intersection[1]))
        
        return current_centroid
    
    def _cleanup_expired_crossings(self, current_ids: Set[str]):
        current_time = time.time()
        expired_ids = []
        
        for obj_id, crossing in self.active_crossings.items():
            if (obj_id not in current_ids or 
                current_time - crossing.last_update > self.line.debounce_time):
                expired_ids.append(obj_id)
        
        for obj_id in expired_ids:
            del self.active_crossings[obj_id]
        
        disappeared_ids = set(self.previous_positions.keys()) - current_ids
        for obj_id in disappeared_ids:
            del self.previous_positions[obj_id]
            if obj_id in self.crossed_ids:
                self.crossed_ids.remove(obj_id)
    
    def _trigger_callbacks(self, event: CrossingEvent):
        for callback in self.event_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in crossing event callback: {e}")
    
    def add_event_callback(self, callback):
        self.event_callbacks.append(callback)
    
    def get_traffic_statistics(self, period: str = "total") -> Dict[str, Any]:
        counts = self.traffic_counter.get_counts(self.line.line_id, period)
        
        performance = self.performance_analyzer.get_performance_metrics()
        
        return {
            'line_id': self.line.line_id,
            'line_name': self.line.name,
            'line_type': self.line.line_type.value,
            'counts': counts,
            'performance': performance,
            'active_crossings': len(self.active_crossings),
            'recent_crossings': len(self.recent_crossings)
        }
    
    def reset_statistics(self):
        self.traffic_counter.reset_counts(self.line.line_id)
        self.crossed_ids.clear()
        self.recent_crossings.clear()
        logger.info(f"Statistics reset for line {self.line.line_id}")
    
    def update_line_config(self, config: Dict[str, Any]):
        for key, value in config.items():
            if hasattr(self.line, key):
                setattr(self.line, value)
        
        self.database.save_line(self.line)
        logger.info(f"Updated configuration for line {self.line.line_id}")
    
    def get_recent_events(self, hours: int = 24) -> List[CrossingEvent]:
        start_time = time.time() - (hours * 3600)
        return self.database.get_events(start_time=start_time, line_id=self.line.line_id)
    
    def draw_line(self, frame: np.ndarray, color: Tuple[int, int, int] = (0, 255, 0),
                  thickness: int = 3, show_info: bool = True) -> np.ndarray:
        annotated_frame = frame.copy()
        
        cv2.line(annotated_frame, self.line.start_point, self.line.end_point, color, thickness)
        
        cv2.circle(annotated_frame, self.line.start_point, 5, (0, 0, 255), -1)
        cv2.circle(annotated_frame, self.line.end_point, 5, (255, 0, 0), -1)
        
        if show_info:
            active_count = len(self.active_crossings)
            total_crossings = sum(self.traffic_counter.get_counts(self.line.line_id).values())
            
            info_text = f"{self.line.name}: {active_count} active, {total_crossings} total"
            
            text_size = cv2.getTextSize(info_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            
            mid_point = ((self.line.start_point[0] + self.line.end_point[0]) // 2,
                        (self.line.start_point[1] + self.line.end_point[1]) // 2)
            
            text_pos = (mid_point[0] - text_size[0] // 2, mid_point[1] - 10)
            
            cv2.rectangle(annotated_frame,
                         (text_pos[0] - 5, text_pos[1] - text_size[1] - 5),
                         (text_pos[0] + text_size[0] + 5, text_pos[1] + 5),
                         (0, 0, 0), -1)
            
            cv2.putText(annotated_frame, info_text, text_pos,
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return annotated_frame

logger.info("Advanced Line Crossing Detection System loaded successfully")
