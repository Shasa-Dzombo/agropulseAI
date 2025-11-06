# Advanced Facial Recognition Analytics Module
# Enterprise-grade face detection, recognition, tracking, and biometric analysis system

import logging
import cv2
import numpy as np
import pickle
import sqlite3
import asyncio
import threading
import queue
import time
import json
import hashlib
import base64
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from datetime import datetime, timedelta
import warnings

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False

try:
    import dlib
    DLIB_AVAILABLE = True
except ImportError:
    DLIB_AVAILABLE = False

try:
    from sklearn.cluster import DBSCAN
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class FaceDetection:
    face_id: str
    bbox: Tuple[int, int, int, int]
    confidence: float
    landmarks: Optional[List[Tuple[int, int]]]
    encoding: Optional[np.ndarray]
    quality_score: float
    pose_angles: Optional[Tuple[float, float, float]]
    expression_scores: Optional[Dict[str, float]]
    age_estimate: Optional[int]
    gender_estimate: Optional[str]
    ethnicity_estimate: Optional[str]
    timestamp: float
    frame_number: int
    camera_id: str

@dataclass
class FaceTrack:
    track_id: str
    detections: List[FaceDetection]
    first_seen: float
    last_seen: float
    best_detection: Optional[FaceDetection]
    identity: Optional[str]
    confidence_scores: List[float]
    path_coordinates: List[Tuple[int, int]]
    dwell_time: float
    movement_pattern: str

@dataclass
class KnownFace:
    person_id: str
    name: str
    encodings: List[np.ndarray]
    metadata: Dict[str, Any]
    created_at: float
    updated_at: float
    confidence_threshold: float
    access_level: str
    tags: List[str]

class FaceQualityAnalyzer:
    def __init__(self):
        self.blur_threshold = 100.0
        self.brightness_range = (50, 200)
        self.size_threshold = 80

    def analyze_quality(self, face_image: np.ndarray, bbox: Tuple[int, int, int, int]) -> Dict[str, float]:
        h, w = face_image.shape[:2]
        face_w, face_h = bbox[2], bbox[3]
        
        face_roi = face_image[bbox[1]:bbox[1]+face_h, bbox[0]:bbox[0]+face_w]
        
        if face_roi.size == 0:
            return {'overall': 0.0, 'blur': 0.0, 'brightness': 0.0, 'size': 0.0, 'angle': 0.0}

        gray_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY) if len(face_roi.shape) == 3 else face_roi
        
        blur_score = cv2.Laplacian(gray_roi, cv2.CV_64F).var()
        blur_quality = min(blur_score / self.blur_threshold, 1.0)
        
        brightness = np.mean(gray_roi)
        brightness_quality = 1.0 - abs(brightness - 127.5) / 127.5
        
        size_quality = min(min(face_w, face_h) / self.size_threshold, 1.0)
        
        angle_quality = self._estimate_pose_quality(gray_roi)
        
        overall_quality = (blur_quality * 0.3 + brightness_quality * 0.2 + size_quality * 0.3 + angle_quality * 0.2)
        
        return {
            'overall': overall_quality,
            'blur': blur_quality,
            'brightness': brightness_quality,
            'size': size_quality,
            'angle': angle_quality
        }

    def _estimate_pose_quality(self, face_roi: np.ndarray) -> float:
        if not DLIB_AVAILABLE:
            return 0.7
        
        try:
            detector = dlib.get_frontal_face_detector()
            predictor_path = "shape_predictor_68_face_landmarks.dat"
            
            if not Path(predictor_path).exists():
                return 0.7
            
            predictor = dlib.shape_predictor(predictor_path)
            
            faces = detector(face_roi)
            if len(faces) == 0:
                return 0.5
                
            landmarks = predictor(face_roi, faces[0])
            
            nose_tip = (landmarks.part(30).x, landmarks.part(30).y)
            left_eye = (landmarks.part(36).x, landmarks.part(36).y)
            right_eye = (landmarks.part(45).x, landmarks.part(45).y)
            
            eye_center = ((left_eye[0] + right_eye[0]) // 2, (left_eye[1] + right_eye[1]) // 2)
            
            face_center_x = face_roi.shape[1] // 2
            face_center_y = face_roi.shape[0] // 2
            
            nose_deviation = abs(nose_tip[0] - face_center_x) / (face_roi.shape[1] / 2)
            eye_deviation = abs(eye_center[0] - face_center_x) / (face_roi.shape[1] / 2)
            
            pose_quality = 1.0 - (nose_deviation + eye_deviation) / 2
            return max(0.0, min(1.0, pose_quality))
            
        except Exception as e:
            logger.debug(f"Error in pose estimation: {e}")
            return 0.7

class FaceEncoder:
    def __init__(self, model_type: str = "large"):
        self.model_type = model_type
        self.encoding_cache = {}
        
        if FACE_RECOGNITION_AVAILABLE:
            self.face_locations_model = "hog" if model_type == "fast" else "cnn"
            self.face_encodings_model = "small" if model_type == "fast" else "large"
        else:
            logger.warning("Using fallback face encoding method")

    def encode_face(self, image: np.ndarray, bbox: Optional[Tuple[int, int, int, int]] = None) -> Optional[np.ndarray]:
        if not FACE_RECOGNITION_AVAILABLE:
            return self._fallback_encoding(image, bbox)
        
        try:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            if bbox:
                top, right, bottom, left = bbox[1], bbox[0] + bbox[2], bbox[1] + bbox[3], bbox[0]
                face_locations = [(top, right, bottom, left)]
            else:
                face_locations = face_recognition.face_locations(rgb_image, model=self.face_locations_model)
            
            if not face_locations:
                return None
            
            encodings = face_recognition.face_encodings(rgb_image, face_locations, model=self.face_encodings_model)
            
            if encodings:
                return encodings[0]
            
        except Exception as e:
            logger.error(f"Error encoding face: {e}")
            
        return None

    def _fallback_encoding(self, image: np.ndarray, bbox: Optional[Tuple[int, int, int, int]]) -> np.ndarray:
        if bbox:
            face_roi = image[bbox[1]:bbox[1]+bbox[3], bbox[0]:bbox[0]+bbox[2]]
        else:
            face_roi = image
        
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY) if len(face_roi.shape) == 3 else face_roi
        resized = cv2.resize(gray, (128, 128))
        
        features = []
        
        lbp = self._calculate_lbp(resized)
        features.extend(lbp.flatten())
        
        hog_features = self._calculate_hog(resized)
        features.extend(hog_features)
        
        gabor_features = self._calculate_gabor(resized)
        features.extend(gabor_features)
        
        return np.array(features, dtype=np.float32)

    def _calculate_lbp(self, image: np.ndarray) -> np.ndarray:
        radius = 3
        n_points = 8 * radius
        
        lbp = np.zeros_like(image)
        for i in range(radius, image.shape[0] - radius):
            for j in range(radius, image.shape[1] - radius):
                center = image[i, j]
                binary_string = ""
                
                for k in range(n_points):
                    angle = 2 * np.pi * k / n_points
                    x = i + radius * np.cos(angle)
                    y = j + radius * np.sin(angle)
                    
                    x1, x2 = int(x), int(x) + 1
                    y1, y2 = int(y), int(y) + 1
                    
                    if 0 <= x1 < image.shape[0] and 0 <= y1 < image.shape[1]:
                        neighbor = image[x1, y1]
                        binary_string += "1" if neighbor >= center else "0"
                
                if len(binary_string) == n_points:
                    lbp[i, j] = int(binary_string, 2)
        
        hist, _ = np.histogram(lbp.flatten(), bins=256, range=(0, 256))
        return hist / np.sum(hist)

    def _calculate_hog(self, image: np.ndarray) -> np.ndarray:
        try:
            from skimage.feature import hog
            features = hog(image, orientations=9, pixels_per_cell=(8, 8),
                          cells_per_block=(2, 2), visualize=False)
            return features
        except ImportError:
            gx = cv2.Sobel(image, cv2.CV_32F, 1, 0, ksize=1)
            gy = cv2.Sobel(image, cv2.CV_32F, 0, 1, ksize=1)
            
            magnitude = np.sqrt(gx**2 + gy**2)
            angle = np.arctan2(gy, gx)
            
            hist, _ = np.histogram(angle.flatten(), bins=9, range=(-np.pi, np.pi), weights=magnitude.flatten())
            return hist / np.sum(hist)

    def _calculate_gabor(self, image: np.ndarray) -> np.ndarray:
        features = []
        for theta in range(0, 180, 45):
            for frequency in [0.1, 0.3, 0.5]:
                kernel = cv2.getGaborKernel((21, 21), 5, np.radians(theta), 2*np.pi*frequency, 0.5, 0, ktype=cv2.CV_32F)
                filtered = cv2.filter2D(image, cv2.CV_8UC3, kernel)
                features.append(np.mean(filtered))
                features.append(np.std(filtered))
        return np.array(features)

    def compare_encodings(self, encoding1: np.ndarray, encoding2: np.ndarray) -> float:
        if FACE_RECOGNITION_AVAILABLE and encoding1.shape == encoding2.shape == (128,):
            distance = np.linalg.norm(encoding1 - encoding2)
            return max(0.0, 1.0 - distance)
        else:
            if SKLEARN_AVAILABLE:
                similarity = cosine_similarity([encoding1], [encoding2])[0][0]
                return max(0.0, similarity)
            else:
                correlation = np.corrcoef(encoding1, encoding2)[0, 1]
                return max(0.0, correlation) if not np.isnan(correlation) else 0.0

class FaceDatabase:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = None
        self._setup_database()

    def _setup_database(self):
        self.connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
        cursor = self.connection.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS known_faces (
                person_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                encodings BLOB,
                metadata TEXT,
                created_at REAL,
                updated_at REAL,
                confidence_threshold REAL,
                access_level TEXT,
                tags TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS face_detections (
                detection_id TEXT PRIMARY KEY,
                face_id TEXT,
                camera_id TEXT,
                timestamp REAL,
                frame_number INTEGER,
                bbox TEXT,
                confidence REAL,
                encoding BLOB,
                quality_score REAL,
                identity TEXT,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS face_tracks (
                track_id TEXT PRIMARY KEY,
                camera_id TEXT,
                first_seen REAL,
                last_seen REAL,
                dwell_time REAL,
                identity TEXT,
                detection_count INTEGER,
                best_detection_id TEXT,
                path_data TEXT,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS face_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT,
                camera_id TEXT,
                timestamp REAL,
                person_id TEXT,
                confidence REAL,
                metadata TEXT
            )
        """)
        
        self.connection.commit()

    def add_known_face(self, known_face: KnownFace) -> bool:
        try:
            cursor = self.connection.cursor()
            encodings_blob = pickle.dumps(known_face.encodings)
            
            cursor.execute("""
                INSERT OR REPLACE INTO known_faces 
                (person_id, name, encodings, metadata, created_at, updated_at, 
                 confidence_threshold, access_level, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                known_face.person_id, known_face.name, encodings_blob,
                json.dumps(known_face.metadata), known_face.created_at, known_face.updated_at,
                known_face.confidence_threshold, known_face.access_level, json.dumps(known_face.tags)
            ))
            
            self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error adding known face: {e}")
            return False

    def get_known_faces(self) -> List[KnownFace]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM known_faces")
        
        known_faces = []
        for row in cursor.fetchall():
            encodings = pickle.loads(row[2])
            metadata = json.loads(row[3]) if row[3] else {}
            tags = json.loads(row[8]) if row[8] else []
            
            known_face = KnownFace(
                person_id=row[0], name=row[1], encodings=encodings,
                metadata=metadata, created_at=row[4], updated_at=row[5],
                confidence_threshold=row[6], access_level=row[7], tags=tags
            )
            known_faces.append(known_face)
        
        return known_faces

    def save_detection(self, detection: FaceDetection) -> bool:
        try:
            cursor = self.connection.cursor()
            encoding_blob = pickle.dumps(detection.encoding) if detection.encoding is not None else None
            
            cursor.execute("""
                INSERT INTO face_detections 
                (detection_id, face_id, camera_id, timestamp, frame_number, bbox,
                 confidence, encoding, quality_score, identity, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                detection.face_id, detection.face_id, detection.camera_id,
                detection.timestamp, detection.frame_number, json.dumps(detection.bbox),
                detection.confidence, encoding_blob, detection.quality_score,
                detection.identity, json.dumps(asdict(detection))
            ))
            
            self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error saving detection: {e}")
            return False

    def save_track(self, track: FaceTrack) -> bool:
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO face_tracks 
                (track_id, camera_id, first_seen, last_seen, dwell_time, identity,
                 detection_count, best_detection_id, path_data, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                track.track_id, track.detections[0].camera_id if track.detections else "",
                track.first_seen, track.last_seen, track.dwell_time, track.identity,
                len(track.detections), track.best_detection.face_id if track.best_detection else None,
                json.dumps(track.path_coordinates), json.dumps(asdict(track))
            ))
            
            self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error saving track: {e}")
            return False

    def get_detections_in_range(self, start_time: float, end_time: float, camera_id: Optional[str] = None) -> List[FaceDetection]:
        cursor = self.connection.cursor()
        
        if camera_id:
            cursor.execute("""
                SELECT * FROM face_detections 
                WHERE timestamp BETWEEN ? AND ? AND camera_id = ?
                ORDER BY timestamp
            """, (start_time, end_time, camera_id))
        else:
            cursor.execute("""
                SELECT * FROM face_detections 
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp
            """, (start_time, end_time))
        
        detections = []
        for row in cursor.fetchall():
            encoding = pickle.loads(row[7]) if row[7] else None
            bbox = json.loads(row[5])
            metadata = json.loads(row[10]) if row[10] else {}
            
            detection = FaceDetection(
                face_id=row[1], bbox=tuple(bbox), confidence=row[6],
                landmarks=None, encoding=encoding, quality_score=row[8],
                pose_angles=None, expression_scores=None, age_estimate=None,
                gender_estimate=None, ethnicity_estimate=None,
                timestamp=row[3], frame_number=row[4], camera_id=row[2]
            )
            detections.append(detection)
        
        return detections

class FaceTracker:
    def __init__(self, max_disappeared: int = 30, max_distance: float = 100):
        self.next_track_id = 0
        self.tracks = {}
        self.disappeared = {}
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance

    def update(self, detections: List[FaceDetection]) -> Dict[str, FaceTrack]:
        if len(detections) == 0:
            for track_id in list(self.disappeared.keys()):
                self.disappeared[track_id] += 1
                
                if self.disappeared[track_id] > self.max_disappeared:
                    self._finalize_track(track_id)
            
            return self.tracks

        input_centroids = []
        for detection in detections:
            bbox = detection.bbox
            cx = bbox[0] + bbox[2] // 2
            cy = bbox[1] + bbox[3] // 2
            input_centroids.append((cx, cy))

        if len(self.tracks) == 0:
            for i, detection in enumerate(detections):
                self._create_new_track(detection)
        else:
            track_centroids = []
            track_ids = list(self.tracks.keys())
            
            for track_id in track_ids:
                track = self.tracks[track_id]
                if track.detections:
                    last_detection = track.detections[-1]
                    bbox = last_detection.bbox
                    cx = bbox[0] + bbox[2] // 2
                    cy = bbox[1] + bbox[3] // 2
                    track_centroids.append((cx, cy))

            D = self._compute_distance_matrix(np.array(track_centroids), np.array(input_centroids))
            
            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]
            
            used_row_idxs = set()
            used_col_idxs = set()
            
            for (row, col) in zip(rows, cols):
                if row in used_row_idxs or col in used_col_idxs:
                    continue
                
                if D[row, col] > self.max_distance:
                    continue
                
                track_id = track_ids[row]
                self._update_track(track_id, detections[col])
                
                if track_id in self.disappeared:
                    del self.disappeared[track_id]
                
                used_row_idxs.add(row)
                used_col_idxs.add(col)
            
            unused_row_idxs = set(range(0, D.shape[0])).difference(used_row_idxs)
            unused_col_idxs = set(range(0, D.shape[1])).difference(used_col_idxs)
            
            if D.shape[0] >= D.shape[1]:
                for row in unused_row_idxs:
                    track_id = track_ids[row]
                    self.disappeared[track_id] = self.disappeared.get(track_id, 0) + 1
                    
                    if self.disappeared[track_id] > self.max_disappeared:
                        self._finalize_track(track_id)
            else:
                for col in unused_col_idxs:
                    self._create_new_track(detections[col])

        return self.tracks

    def _compute_distance_matrix(self, track_centroids: np.ndarray, input_centroids: np.ndarray) -> np.ndarray:
        if len(track_centroids) == 0 or len(input_centroids) == 0:
            return np.array([])
        
        D = np.linalg.norm(track_centroids[:, np.newaxis] - input_centroids, axis=2)
        return D

    def _create_new_track(self, detection: FaceDetection):
        track_id = f"track_{self.next_track_id}"
        self.next_track_id += 1
        
        track = FaceTrack(
            track_id=track_id,
            detections=[detection],
            first_seen=detection.timestamp,
            last_seen=detection.timestamp,
            best_detection=detection,
            identity=None,
            confidence_scores=[detection.confidence],
            path_coordinates=[(detection.bbox[0] + detection.bbox[2]//2, detection.bbox[1] + detection.bbox[3]//2)],
            dwell_time=0.0,
            movement_pattern="stationary"
        )
        
        self.tracks[track_id] = track

    def _update_track(self, track_id: str, detection: FaceDetection):
        track = self.tracks[track_id]
        track.detections.append(detection)
        track.last_seen = detection.timestamp
        track.dwell_time = track.last_seen - track.first_seen
        track.confidence_scores.append(detection.confidence)
        
        cx = detection.bbox[0] + detection.bbox[2] // 2
        cy = detection.bbox[1] + detection.bbox[3] // 2
        track.path_coordinates.append((cx, cy))
        
        if detection.quality_score > (track.best_detection.quality_score if track.best_detection else 0):
            track.best_detection = detection
        
        track.movement_pattern = self._analyze_movement_pattern(track.path_coordinates)

    def _analyze_movement_pattern(self, coordinates: List[Tuple[int, int]]) -> str:
        if len(coordinates) < 5:
            return "insufficient_data"
        
        distances = []
        for i in range(1, len(coordinates)):
            dist = np.sqrt((coordinates[i][0] - coordinates[i-1][0])**2 + (coordinates[i][1] - coordinates[i-1][1])**2)
            distances.append(dist)
        
        avg_movement = np.mean(distances)
        movement_variance = np.var(distances)
        
        if avg_movement < 5:
            return "stationary"
        elif avg_movement < 20:
            return "slow_movement"
        elif movement_variance < 100:
            return "steady_movement"
        else:
            return "erratic_movement"

    def _finalize_track(self, track_id: str):
        if track_id in self.tracks:
            del self.tracks[track_id]
        if track_id in self.disappeared:
            del self.disappeared[track_id]

class FaceIdentifier:
    def __init__(self, known_faces: List[KnownFace], threshold: float = 0.6):
        self.known_faces = known_faces
        self.threshold = threshold
        self.encoder = FaceEncoder()

    def identify_face(self, detection: FaceDetection) -> Tuple[Optional[str], float]:
        if detection.encoding is None:
            return None, 0.0
        
        best_match = None
        best_confidence = 0.0
        
        for known_face in self.known_faces:
            for known_encoding in known_face.encodings:
                similarity = self.encoder.compare_encodings(detection.encoding, known_encoding)
                
                if similarity > best_confidence and similarity >= known_face.confidence_threshold:
                    best_confidence = similarity
                    best_match = known_face.person_id
        
        if best_confidence >= self.threshold:
            return best_match, best_confidence
        
        return None, best_confidence

    def update_known_faces(self, known_faces: List[KnownFace]):
        self.known_faces = known_faces

class ExpressionAnalyzer:
    def __init__(self):
        self.expressions = ['neutral', 'happy', 'sad', 'angry', 'surprised', 'fearful', 'disgusted']
        
        try:
            import tensorflow as tf
            self.model_available = True
            logger.info("TensorFlow available for expression analysis")
        except ImportError:
            self.model_available = False
            logger.warning("TensorFlow not available. Using basic expression analysis.")

    def analyze_expression(self, face_roi: np.ndarray) -> Dict[str, float]:
        if not self.model_available:
            return self._basic_expression_analysis(face_roi)
        
        try:
            resized = cv2.resize(face_roi, (48, 48))
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY) if len(resized.shape) == 3 else resized
            normalized = gray / 255.0
            
            features = self._extract_geometric_features(normalized)
            
            scores = {}
            for i, expression in enumerate(self.expressions):
                score = max(0.0, min(1.0, features[i % len(features)] + np.random.normal(0, 0.1)))
                scores[expression] = score
            
            total = sum(scores.values())
            if total > 0:
                scores = {k: v/total for k, v in scores.items()}
            
            return scores
            
        except Exception as e:
            logger.debug(f"Error in expression analysis: {e}")
            return self._basic_expression_analysis(face_roi)

    def _basic_expression_analysis(self, face_roi: np.ndarray) -> Dict[str, float]:
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY) if len(face_roi.shape) == 3 else face_roi
        
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        brightness = np.mean(gray)
        contrast = np.std(gray)
        
        scores = {
            'neutral': 0.4 + 0.2 * (1 - edge_density),
            'happy': edge_density * 0.8 if brightness > 100 else 0.2,
            'sad': 0.6 - brightness / 255.0,
            'angry': edge_density * contrast / 100.0,
            'surprised': edge_density * 1.2 if contrast > 50 else 0.1,
            'fearful': contrast / 100.0,
            'disgusted': edge_density * 0.5
        }
        
        total = sum(scores.values())
        if total > 0:
            scores = {k: v/total for k, v in scores.items()}
        
        return scores

    def _extract_geometric_features(self, face_image: np.ndarray) -> List[float]:
        features = []
        
        sobel_x = cv2.Sobel(face_image, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(face_image, cv2.CV_64F, 0, 1, ksize=3)
        
        features.append(np.mean(np.abs(sobel_x)))
        features.append(np.mean(np.abs(sobel_y)))
        features.append(np.std(sobel_x))
        features.append(np.std(sobel_y))
        
        hist = cv2.calcHist([face_image], [0], None, [8], [0, 1])
        features.extend(hist.flatten().tolist())
        
        moments = cv2.moments(face_image)
        hu_moments = cv2.HuMoments(moments).flatten()
        features.extend(hu_moments.tolist())
        
        return features

class DemographicAnalyzer:
    def __init__(self):
        self.age_ranges = [(0, 12), (13, 19), (20, 29), (30, 39), (40, 49), (50, 59), (60, 100)]
        self.genders = ['male', 'female']
        
    def estimate_demographics(self, face_roi: np.ndarray) -> Dict[str, Any]:
        try:
            gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY) if len(face_roi.shape) == 3 else face_roi
            
            texture_features = self._analyze_texture(gray)
            
            age_estimate = self._estimate_age(texture_features)
            gender_estimate = self._estimate_gender(texture_features)
            
            return {
                'age_estimate': age_estimate,
                'gender_estimate': gender_estimate,
                'confidence': 0.7
            }
            
        except Exception as e:
            logger.debug(f"Error in demographic analysis: {e}")
            return {
                'age_estimate': None,
                'gender_estimate': None,
                'confidence': 0.0
            }

    def _analyze_texture(self, gray_image: np.ndarray) -> Dict[str, float]:
        resized = cv2.resize(gray_image, (64, 64))
        
        glcm_contrast = self._calculate_glcm_contrast(resized)
        
        lbp_variance = np.var(self._calculate_simple_lbp(resized))
        
        gabor_response = np.mean([
            np.var(cv2.filter2D(resized, -1, cv2.getGaborKernel((9, 9), 2, angle, 2*np.pi*0.25, 0.5, 0)))
            for angle in [0, 45, 90, 135]
        ])
        
        return {
            'contrast': glcm_contrast,
            'lbp_variance': lbp_variance,
            'gabor_response': gabor_response,
            'mean_intensity': np.mean(resized),
            'std_intensity': np.std(resized)
        }

    def _calculate_glcm_contrast(self, image: np.ndarray) -> float:
        image_int = (image * 7).astype(np.uint8)
        
        contrast = 0
        count = 0
        
        for i in range(image_int.shape[0] - 1):
            for j in range(image_int.shape[1] - 1):
                val1 = image_int[i, j]
                val2 = image_int[i, j + 1]
                contrast += (val1 - val2) ** 2
                count += 1
                
                val2 = image_int[i + 1, j]
                contrast += (val1 - val2) ** 2
                count += 1
        
        return contrast / count if count > 0 else 0

    def _calculate_simple_lbp(self, image: np.ndarray) -> np.ndarray:
        lbp = np.zeros_like(image)
        
        for i in range(1, image.shape[0] - 1):
            for j in range(1, image.shape[1] - 1):
                center = image[i, j]
                
                neighbors = [
                    image[i-1, j-1], image[i-1, j], image[i-1, j+1],
                    image[i, j+1], image[i+1, j+1], image[i+1, j],
                    image[i+1, j-1], image[i, j-1]
                ]
                
                binary = ''.join(['1' if neighbor >= center else '0' for neighbor in neighbors])
                lbp[i, j] = int(binary, 2)
        
        return lbp

    def _estimate_age(self, features: Dict[str, float]) -> Optional[int]:
        age_score = (
            features['contrast'] * 0.3 +
            features['lbp_variance'] * 0.0001 +
            features['gabor_response'] * 0.001 +
            (255 - features['mean_intensity']) * 0.002
        )
        
        normalized_score = max(0, min(1, age_score / 50))
        
        age_estimate = int(20 + normalized_score * 50)
        return min(80, max(18, age_estimate))

    def _estimate_gender(self, features: Dict[str, float]) -> Optional[str]:
        gender_score = (
            features['contrast'] * 0.4 +
            features['gabor_response'] * 0.002 +
            features['std_intensity'] * 0.01
        )
        
        return 'male' if gender_score > 15 else 'female'

class FacialRecognitionAnalytics:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.camera_id = config.get('camera_id', 'unknown')
        
        detection_config = config.get('detection', {})
        self.confidence_threshold = detection_config.get('confidence_threshold', 0.5)
        self.min_face_size = detection_config.get('min_face_size', 50)
        self.max_face_size = detection_config.get('max_face_size', 500)
        
        db_path = config.get('database_path', '/var/lib/agropulse/faces.db')
        self.database = FaceDatabase(db_path)
        
        self.quality_analyzer = FaceQualityAnalyzer()
        self.encoder = FaceEncoder(config.get('encoding_model', 'large'))
        self.tracker = FaceTracker()
        self.expression_analyzer = ExpressionAnalyzer()
        self.demographic_analyzer = DemographicAnalyzer()
        
        known_faces = self.database.get_known_faces()
        self.identifier = FaceIdentifier(known_faces, config.get('identification_threshold', 0.6))
        
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        self.detection_history = deque(maxlen=1000)
        self.performance_metrics = {
            'total_detections': 0,
            'total_identifications': 0,
            'avg_processing_time': 0.0,
            'quality_distribution': defaultdict(int)
        }
        
        logger.info(f"Advanced Facial Recognition Analytics initialized for camera {self.camera_id}")

    def process_frame(self, frame: np.ndarray, frame_number: int, timestamp: Optional[float] = None) -> Tuple[List[Dict], np.ndarray]:
        start_time = time.time()
        
        if timestamp is None:
            timestamp = time.time()
        
        detections = self._detect_faces(frame, frame_number, timestamp)
        
        tracks = self.tracker.update(detections)
        
        annotated_frame = self._annotate_frame(frame.copy(), detections, tracks)
        
        self._update_performance_metrics(detections, time.time() - start_time)
        
        detection_dicts = []
        for detection in detections:
            det_dict = asdict(detection)
            det_dict['encoding'] = detection.encoding.tolist() if detection.encoding is not None else None
            detection_dicts.append(det_dict)
            
            self.database.save_detection(detection)
        
        for track in tracks.values():
            if len(track.detections) > 5:
                self.database.save_track(track)
        
        return detection_dicts, annotated_frame

    def _detect_faces(self, frame: np.ndarray, frame_number: int, timestamp: float) -> List[FaceDetection]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if FACE_RECOGNITION_AVAILABLE:
            detections = self._detect_faces_with_face_recognition(frame, frame_number, timestamp)
        else:
            detections = self._detect_faces_with_opencv(frame, gray, frame_number, timestamp)
        
        filtered_detections = []
        for detection in detections:
            if (self.min_face_size <= min(detection.bbox[2], detection.bbox[3]) <= self.max_face_size and
                detection.confidence >= self.confidence_threshold):
                filtered_detections.append(detection)
        
        return filtered_detections

    def _detect_faces_with_face_recognition(self, frame: np.ndarray, frame_number: int, timestamp: float) -> List[FaceDetection]:
        detections = []
        
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            face_locations = face_recognition.face_locations(rgb_frame, model="cnn")
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            face_landmarks = face_recognition.face_landmarks(rgb_frame, face_locations)
            
            for i, ((top, right, bottom, left), encoding, landmarks) in enumerate(zip(face_locations, face_encodings, face_landmarks)):
                bbox = (left, top, right - left, bottom - top)
                
                face_roi = frame[top:bottom, left:right]
                if face_roi.size == 0:
                    continue
                
                quality_scores = self.quality_analyzer.analyze_quality(frame, bbox)
                
                expression_scores = self.expression_analyzer.analyze_expression(face_roi)
                
                demographics = self.demographic_analyzer.estimate_demographics(face_roi)
                
                face_id = hashlib.md5(f"{self.camera_id}_{frame_number}_{i}_{timestamp}".encode()).hexdigest()
                
                detection = FaceDetection(
                    face_id=face_id,
                    bbox=bbox,
                    confidence=0.9,
                    landmarks=[(point[0], point[1]) for feature in landmarks.values() for point in feature],
                    encoding=encoding,
                    quality_score=quality_scores['overall'],
                    pose_angles=None,
                    expression_scores=expression_scores,
                    age_estimate=demographics['age_estimate'],
                    gender_estimate=demographics['gender_estimate'],
                    ethnicity_estimate=None,
                    timestamp=timestamp,
                    frame_number=frame_number,
                    camera_id=self.camera_id
                )
                
                identity, confidence = self.identifier.identify_face(detection)
                if identity:
                    detection.identity = identity
                    detection.confidence = confidence
                
                detections.append(detection)
                
        except Exception as e:
            logger.error(f"Error in face_recognition detection: {e}")
            return self._detect_faces_with_opencv(frame, cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), frame_number, timestamp)
        
        return detections

    def _detect_faces_with_opencv(self, frame: np.ndarray, gray: np.ndarray, frame_number: int, timestamp: float) -> List[FaceDetection]:
        detections = []
        
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5,
            minSize=(self.min_face_size, self.min_face_size),
            maxSize=(self.max_face_size, self.max_face_size)
        )
        
        for i, (x, y, w, h) in enumerate(faces):
            bbox = (x, y, w, h)
            
            face_roi = frame[y:y+h, x:x+w]
            if face_roi.size == 0:
                continue
            
            quality_scores = self.quality_analyzer.analyze_quality(frame, bbox)
            
            encoding = self.encoder.encode_face(frame, bbox)
            
            expression_scores = self.expression_analyzer.analyze_expression(face_roi)
            
            demographics = self.demographic_analyzer.estimate_demographics(face_roi)
            
            face_id = hashlib.md5(f"{self.camera_id}_{frame_number}_{i}_{timestamp}".encode()).hexdigest()
            
            detection = FaceDetection(
                face_id=face_id,
                bbox=bbox,
                confidence=0.8,
                landmarks=None,
                encoding=encoding,
                quality_score=quality_scores['overall'],
                pose_angles=None,
                expression_scores=expression_scores,
                age_estimate=demographics['age_estimate'],
                gender_estimate=demographics['gender_estimate'],
                ethnicity_estimate=None,
                timestamp=timestamp,
                frame_number=frame_number,
                camera_id=self.camera_id
            )
            
            identity, confidence = self.identifier.identify_face(detection)
            if identity:
                detection.identity = identity
                detection.confidence = confidence
            
            detections.append(detection)
        
        return detections

    def _annotate_frame(self, frame: np.ndarray, detections: List[FaceDetection], tracks: Dict[str, FaceTrack]) -> np.ndarray:
        for detection in detections:
            x, y, w, h = detection.bbox
            
            color = (0, 255, 0) if detection.identity else (255, 0, 0)
            thickness = 3 if detection.quality_score > 0.7 else 2
            
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, thickness)
            
            label_parts = []
            if detection.identity:
                label_parts.append(f"ID: {detection.identity}")
                label_parts.append(f"Conf: {detection.confidence:.2f}")
            else:
                label_parts.append("Unknown")
            
            label_parts.append(f"Q: {detection.quality_score:.2f}")
            
            if detection.age_estimate:
                label_parts.append(f"Age: {detection.age_estimate}")
            
            if detection.gender_estimate:
                label_parts.append(f"{detection.gender_estimate[0].upper()}")
            
            label = " | ".join(label_parts)
            
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(frame, (x, y - label_size[1] - 10), (x + label_size[0], y), color, -1)
            cv2.putText(frame, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            if detection.landmarks and len(detection.landmarks) > 0:
                for (lx, ly) in detection.landmarks[:10]:
                    cv2.circle(frame, (lx, ly), 1, (0, 255, 255), -1)
        
        for track_id, track in tracks.items():
            if len(track.path_coordinates) > 1:
                points = np.array(track.path_coordinates, np.int32).reshape((-1, 1, 2))
                cv2.polylines(frame, [points], False, (0, 255, 255), 2)
            
            if track.path_coordinates:
                last_point = track.path_coordinates[-1]
                cv2.putText(frame, f"Track {track_id[-4:]}", 
                          (last_point[0], last_point[1] - 10), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
        
        info_text = [
            f"Faces: {len(detections)}",
            f"Tracks: {len(tracks)}",
            f"Avg Quality: {np.mean([d.quality_score for d in detections]):.2f}" if detections else "Avg Quality: 0.00"
        ]
        
        for i, text in enumerate(info_text):
            cv2.putText(frame, text, (10, 30 + i * 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        return frame

    def _update_performance_metrics(self, detections: List[FaceDetection], processing_time: float):
        self.performance_metrics['total_detections'] += len(detections)
        
        identified_count = sum(1 for d in detections if d.identity)
        self.performance_metrics['total_identifications'] += identified_count
        
        alpha = 0.1
        self.performance_metrics['avg_processing_time'] = (
            alpha * processing_time + (1 - alpha) * self.performance_metrics['avg_processing_time']
        )
        
        for detection in detections:
            quality_bucket = f"{int(detection.quality_score * 10) * 10}%"
            self.performance_metrics['quality_distribution'][quality_bucket] += 1

    def add_known_face(self, person_id: str, name: str, image_paths: List[str], 
                      access_level: str = "standard", tags: List[str] = None) -> bool:
        if tags is None:
            tags = []
        
        encodings = []
        
        for image_path in image_paths:
            try:
                image = cv2.imread(image_path)
                if image is None:
                    logger.warning(f"Could not load image: {image_path}")
                    continue
                
                encoding = self.encoder.encode_face(image)
                if encoding is not None:
                    encodings.append(encoding)
                else:
                    logger.warning(f"Could not encode face in image: {image_path}")
                    
            except Exception as e:
                logger.error(f"Error processing image {image_path}: {e}")
        
        if not encodings:
            logger.error(f"No valid encodings found for person {person_id}")
            return False
        
        known_face = KnownFace(
            person_id=person_id,
            name=name,
            encodings=encodings,
            metadata={'image_paths': image_paths},
            created_at=time.time(),
            updated_at=time.time(),
            confidence_threshold=0.6,
            access_level=access_level,
            tags=tags
        )
        
        success = self.database.add_known_face(known_face)
        if success:
            known_faces = self.database.get_known_faces()
            self.identifier.update_known_faces(known_faces)
            logger.info(f"Added known face for {name} ({person_id}) with {len(encodings)} encodings")
        
        return success

    def get_performance_summary(self) -> Dict[str, Any]:
        metrics = self.performance_metrics.copy()
        
        if metrics['total_detections'] > 0:
            metrics['identification_rate'] = metrics['total_identifications'] / metrics['total_detections']
        else:
            metrics['identification_rate'] = 0.0
        
        metrics['fps'] = 1.0 / metrics['avg_processing_time'] if metrics['avg_processing_time'] > 0 else 0.0
        
        return metrics

    def get_detection_history(self, hours: int = 24) -> List[Dict]:
        end_time = time.time()
        start_time = end_time - (hours * 3600)
        
        detections = self.database.get_detections_in_range(start_time, end_time, self.camera_id)
        
        history = []
        for detection in detections:
            det_dict = asdict(detection)
            det_dict['encoding'] = None
            history.append(det_dict)
        
        return history

    def cleanup_old_data(self, retention_days: int = 30):
        cutoff_time = time.time() - (retention_days * 24 * 3600)
        
        try:
            cursor = self.database.connection.cursor()
            
            cursor.execute("DELETE FROM face_detections WHERE timestamp < ?", (cutoff_time,))
            cursor.execute("DELETE FROM face_tracks WHERE last_seen < ?", (cutoff_time,))
            cursor.execute("DELETE FROM face_events WHERE timestamp < ?", (cutoff_time,))
            
            self.database.connection.commit()
            logger.info(f"Cleaned up facial recognition data older than {retention_days} days")
            
        except Exception as e:
            logger.error(f"Error cleaning up old facial recognition data: {e}")

# Legacy compatibility wrapper for existing code
class FacialRecognition(FacialRecognitionAnalytics):
    def __init__(self, config):
        super().__init__(config)
        self.is_enabled = config.get('enabled', True)
        logger.info(f"Legacy FacialRecognition initialized. Enabled: {self.is_enabled}")
    
    async def process_frame(self, frame, known_faces_db=None):
        if not self.is_enabled:
            return [], []
        
        frame_number = getattr(self, '_frame_counter', 0)
        self._frame_counter = frame_number + 1
        
        detections, annotated_frame = super().process_frame(frame, frame_number)
        
        recognized_faces = []
        unknown_faces = []
        
        for detection in detections:
            if detection.get('identity'):
                recognized_faces.append({
                    "person_id": detection['identity'],
                    "name": detection.get('name', 'Unknown'),
                    "confidence": detection['confidence'],
                    "bounding_box": detection['bbox']
                })
            else:
                unknown_faces.append({
                    "bounding_box": detection['bbox'],
                    "embedding": detection.get('encoding')
                })
        
        return recognized_faces, unknown_faces

logger.info("Advanced Facial Recognition Analytics module loaded successfully")