# ======================================================================================================================
#
# AgroPulse NVR System Firmware - Core Intelligence Platform
#
# FILE: nvr_firmware_main.py
#
# This is the main firmware module for the AgroPulse Network Video Recorder (NVR) system,
# specifically designed for Agricultural Intelligence and Farm Management.
#
# The system integrates:
# - Real-time video analytics with Gemini AI
# - Geospatial crop monitoring and disease detection
# - ESP32 IoT device fleet management
# - Mobile field worker guidance
# - Digital twin farm mapping
# - Multi-modal sensor fusion
# - Edge-cloud hybrid processing
# - Predictive analytics for crop health
#
# ======================================================================================================================

import asyncio
import aiohttp
import aiomqtt
import logging
import json
import uuid
import time
import hashlib
import hmac
import base64
import struct
import socket
import ssl
import pathlib
from typing import Dict, List, Optional, Set, Any, Tuple, Callable, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, IntEnum
from collections import defaultdict, deque
import numpy as np
import cv2
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import queue

# Google AI imports
try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning("Google Generative AI not available")

# Database imports
import sqlite3
import aiosqlite
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from geoalchemy2 import Geometry
from geoalchemy2.elements import WKTElement
from geoalchemy2.functions import ST_Distance, ST_Within, ST_Point

# Geospatial imports
try:
    from pyproj import Transformer, CRS
    from shapely.geometry import Point, Polygon, LineString, box
    from shapely.ops import transform
    import folium
    GEOSPATIAL_AVAILABLE = True
except ImportError:
    GEOSPATIAL_AVAILABLE = False
    logging.warning("Geospatial libraries not fully available")

# ======================================================================================================================
# SECTION 1: CORE CONFIGURATION & CONSTANTS
# ======================================================================================================================

# System Information
NVR_FIRMWARE_VERSION = "5.2.1-AGRI"
NVR_BUILD_DATE = "2025-11-02"
NVR_CODENAME = "GEMINI-HARVEST"

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/agropulse/nvr_firmware.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Hardware Configuration
CPU_CORES = multiprocessing.cpu_count()
GPU_AVAILABLE = False
NPU_AVAILABLE = False

try:
    import torch
    GPU_AVAILABLE = torch.cuda.is_available()
    if GPU_AVAILABLE:
        GPU_DEVICE = torch.device('cuda:0')
        GPU_COUNT = torch.cuda.device_count()
        logger.info(f"GPU acceleration available: {GPU_COUNT} device(s)")
except ImportError:
    pass

# Network Configuration
NVR_HOST = "0.0.0.0"
NVR_HTTP_PORT = 8080
NVR_HTTPS_PORT = 8443
NVR_WEBSOCKET_PORT = 9000
NVR_MQTT_PORT = 1883
NVR_RTSP_PORT = 554

# API Configuration
API_VERSION = "v1"
API_BASE_PATH = f"/api/{API_VERSION}"
API_RATE_LIMIT = 1000  # requests per minute
API_TOKEN_EXPIRY = 3600  # seconds

# Database Configuration
DB_PATH = "/var/lib/agropulse/nvr.db"
DB_BACKUP_PATH = "/var/lib/agropulse/backups"
DB_CONNECTION_POOL_SIZE = 20
DB_MAX_OVERFLOW = 50

# Storage Configuration
STORAGE_ROOT = "/mnt/agropulse"
VIDEO_STORAGE_PATH = f"{STORAGE_ROOT}/videos"
IMAGE_STORAGE_PATH = f"{STORAGE_ROOT}/images"
MODEL_STORAGE_PATH = f"{STORAGE_ROOT}/models"
TEMP_STORAGE_PATH = f"{STORAGE_ROOT}/temp"

# Storage Limits
MAX_VIDEO_RETENTION_DAYS = 90
MAX_IMAGE_RETENTION_DAYS = 365
STORAGE_WARNING_THRESHOLD = 80  # percent
STORAGE_CRITICAL_THRESHOLD = 95  # percent

# Gemini AI Configuration
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"  # Load from secure config
GEMINI_MODEL = "gemini-1.5-pro"
GEMINI_VISION_MODEL = "gemini-pro-vision"
GEMINI_MAX_TOKENS = 8192
GEMINI_TEMPERATURE = 0.4
GEMINI_TOP_P = 0.95
GEMINI_TOP_K = 40

# AI Model Configuration
AI_INFERENCE_BATCH_SIZE = 8
AI_CONFIDENCE_THRESHOLD = 0.75
AI_NMS_THRESHOLD = 0.45  # Non-Maximum Suppression
AI_MAX_DETECTIONS = 100

# Supported crop types for specialized detection
CROP_TYPES = [
    "tomato", "potato", "pepper", "cucumber", "lettuce", "cabbage",
    "carrot", "corn", "wheat", "rice", "soybean", "cotton",
    "grape", "apple", "orange", "strawberry", "blueberry"
]

# Disease classes (expandable)
DISEASE_CLASSES = [
    "healthy",
    "early_blight", "late_blight", "leaf_mold", "septoria_leaf_spot",
    "spider_mites", "target_spot", "yellow_leaf_curl_virus", "mosaic_virus",
    "bacterial_spot", "powdery_mildew", "rust", "anthracnose",
    "downy_mildew", "black_rot", "bacterial_wilt", "fusarium_wilt",
    "verticillium_wilt", "root_rot", "crown_gall", "fire_blight"
]

# Pest classes
PEST_CLASSES = [
    "no_pest",
    "aphid", "whitefly", "spider_mite", "thrips", "leafhopper",
    "caterpillar", "beetle", "weevil", "grasshopper", "cricket",
    "slug", "snail", "nematode", "fruit_fly", "moth"
]

# Video Analytics Configuration
VIDEO_FRAME_RATE = 30  # fps for processing
VIDEO_RESOLUTION = (1920, 1080)  # Full HD
VIDEO_CODEC = "h264"
VIDEO_BITRATE = 4000000  # 4 Mbps

# ESP32 Device Management
ESP32_MAX_DEVICES = 1000
ESP32_HEARTBEAT_TIMEOUT = 60  # seconds
ESP32_FIRMWARE_CHECK_INTERVAL = 3600  # seconds

# Geospatial Configuration
DEFAULT_CRS = "EPSG:4326"  # WGS84
UTM_CRS_BASE = "EPSG:326"  # Will append zone number
GEOFENCE_BUFFER_METERS = 5.0
GPS_ACCURACY_THRESHOLD = 10.0  # meters

# Mobile App Configuration
MOBILE_PUSH_PROVIDER = "firebase"  # or "apns"
MOBILE_MAX_SESSIONS = 100
MOBILE_SESSION_TIMEOUT = 1800  # seconds

# System Performance
MAX_CONCURRENT_STREAMS = 64
MAX_CONCURRENT_INFERENCES = 16
MAX_QUEUE_SIZE = 1000
WORKER_THREAD_COUNT = CPU_CORES * 2
PROCESS_POOL_SIZE = max(1, CPU_CORES - 1)

# Alert Severity Levels
class AlertSeverity(IntEnum):
    INFO = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    CRITICAL = 5
    EMERGENCY = 6

# ======================================================================================================================
# SECTION 2: DATA MODELS & ENUMERATIONS
# ======================================================================================================================

Base = declarative_base()

class DeviceStatus(Enum):
    """ESP32 device status"""
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    UPDATING = "updating"

class CropStatus(Enum):
    """Crop health status"""
    HEALTHY = "healthy"
    WARNING = "warning"
    DISEASED = "diseased"
    PEST_DETECTED = "pest_detected"
    STRESS = "stress"
    UNKNOWN = "unknown"

class TaskStatus(Enum):
    """Field task status"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"

class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5

@dataclass
class GeoPosition:
    """GPS position with metadata"""
    latitude: float
    longitude: float
    altitude: float = 0.0
    accuracy: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_point(self):
        """Convert to Shapely Point"""
        return Point(self.longitude, self.latitude, self.altitude)
    
    def to_wkt(self):
        """Convert to WKT format"""
        return f"POINT({self.longitude} {self.latitude} {self.altitude})"
    
    def distance_to(self, other: 'GeoPosition') -> float:
        """Calculate distance to another position in meters"""
        from geopy.distance import geodesic
        return geodesic(
            (self.latitude, self.longitude),
            (other.latitude, other.longitude)
        ).meters

@dataclass
class BoundingBox:
    """Bounding box for detected objects"""
    x: int
    y: int
    width: int
    height: int
    confidence: float
    class_id: int
    class_name: str
    
    def to_dict(self):
        return {
            'x': self.x, 'y': self.y,
            'width': self.width, 'height': self.height,
            'confidence': self.confidence,
            'class_id': self.class_id,
            'class_name': self.class_name
        }
    
    def iou(self, other: 'BoundingBox') -> float:
        """Calculate Intersection over Union with another box"""
        x1 = max(self.x, other.x)
        y1 = max(self.y, other.y)
        x2 = min(self.x + self.width, other.x + other.width)
        y2 = min(self.y + self.height, other.y + other.height)
        
        if x2 < x1 or y2 < y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        area1 = self.width * self.height
        area2 = other.width * other.height
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0

# ======================================================================================================================
# SECTION 3: DATABASE MODELS
# ======================================================================================================================

class FarmModel(Base):
    """Farm entity"""
    __tablename__ = 'farms'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    owner = Column(String)
    total_area = Column(Float)  # hectares
    boundary = Column(Geometry('POLYGON'))
    center_point = Column(Geometry('POINT'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata = Column(JSON)
    
    # Relationships
    plots = relationship("PlotModel", back_populates="farm", cascade="all, delete-orphan")
    devices = relationship("DeviceModel", back_populates="farm")

class PlotModel(Base):
    """Agricultural plot/field"""
    __tablename__ = 'plots'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    farm_id = Column(String, ForeignKey('farms.id'))
    name = Column(String, nullable=False)
    crop_type = Column(String)
    crop_variety = Column(String)
    planting_date = Column(DateTime)
    expected_harvest_date = Column(DateTime)
    area = Column(Float)  # hectares
    boundary = Column(Geometry('POLYGON'))
    center_point = Column(Geometry('POINT'))
    current_status = Column(String, default="healthy")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata = Column(JSON)
    
    # Relationships
    farm = relationship("FarmModel", back_populates="plots")
    cameras = relationship("CameraModel", back_populates="plot")
    incidents = relationship("IncidentModel", back_populates="plot")
    
    # Indexes
    __table_args__ = (
        Index('idx_plot_farm', 'farm_id'),
        Index('idx_plot_crop', 'crop_type'),
        Index('idx_plot_status', 'current_status'),
    )

class DeviceModel(Base):
    """ESP32 IoT Device"""
    __tablename__ = 'devices'
    
    id = Column(String, primary_key=True)  # Device ID from hardware
    farm_id = Column(String, ForeignKey('farms.id'))
    device_type = Column(String)
    firmware_version = Column(String)
    status = Column(String, default="offline")
    location = Column(Geometry('POINT'))
    battery_level = Column(Float)
    signal_strength = Column(Integer)
    last_heartbeat = Column(DateTime)
    total_data_sent = Column(Integer, default=0)
    total_images_captured = Column(Integer, default=0)
    total_detections = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    configuration = Column(JSON)
    metadata = Column(JSON)
    
    # Relationships
    farm = relationship("FarmModel", back_populates="devices")
    sensor_readings = relationship("SensorReadingModel", back_populates="device")
    
    # Indexes
    __table_args__ = (
        Index('idx_device_farm', 'farm_id'),
        Index('idx_device_status', 'status'),
        Index('idx_device_heartbeat', 'last_heartbeat'),
    )

class CameraModel(Base):
    """Camera (physical or virtual from ESP32)"""
    __tablename__ = 'cameras'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String, ForeignKey('devices.id'), nullable=True)
    plot_id = Column(String, ForeignKey('plots.id'))
    name = Column(String, nullable=False)
    camera_type = Column(String)  # 'fixed', 'ptz', 'esp32_cam'
    location = Column(Geometry('POINT'))
    viewing_direction = Column(Float)  # degrees from north
    viewing_angle = Column(Float)  # field of view in degrees
    coverage_area = Column(Geometry('POLYGON'))  # calculated viewing area
    resolution = Column(String)
    is_active = Column(Boolean, default=True)
    rtsp_url = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    calibration_data = Column(JSON)
    metadata = Column(JSON)
    
    # Relationships
    plot = relationship("PlotModel", back_populates="cameras")
    detections = relationship("DetectionModel", back_populates="camera")
    
    # Indexes
    __table_args__ = (
        Index('idx_camera_plot', 'plot_id'),
        Index('idx_camera_active', 'is_active'),
    )

class SensorReadingModel(Base):
    """Environmental sensor reading"""
    __tablename__ = 'sensor_readings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, ForeignKey('devices.id'))
    timestamp = Column(DateTime, default=datetime.utcnow)
    temperature = Column(Float)
    humidity = Column(Float)
    soil_moisture = Column(Float)
    light_level = Column(Float)
    battery_voltage = Column(Float)
    pressure = Column(Float)
    rainfall = Column(Float)
    wind_speed = Column(Float)
    wind_direction = Column(Float)
    extra_data = Column(JSON)
    
    # Relationships
    device = relationship("DeviceModel", back_populates="sensor_readings")
    
    # Indexes
    __table_args__ = (
        Index('idx_reading_device_time', 'device_id', 'timestamp'),
        Index('idx_reading_timestamp', 'timestamp'),
    )

class DetectionModel(Base):
    """AI Detection result"""
    __tablename__ = 'detections'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    camera_id = Column(String, ForeignKey('cameras.id'))
    timestamp = Column(DateTime, default=datetime.utcnow)
    image_path = Column(String)
    detection_type = Column(String)  # 'disease', 'pest', 'object'
    class_id = Column(Integer)
    class_name = Column(String)
    confidence = Column(Float)
    bounding_box = Column(JSON)
    location = Column(Geometry('POINT'))  # GPS location
    pixel_location = Column(JSON)  # x, y in image
    severity = Column(String)
    ai_model_version = Column(String)
    processing_time_ms = Column(Float)
    reviewed = Column(Boolean, default=False)
    false_positive = Column(Boolean, default=False)
    metadata = Column(JSON)
    
    # Relationships
    camera = relationship("CameraModel", back_populates="detections")
    incident = relationship("IncidentModel", back_populates="detection", uselist=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_detection_camera_time', 'camera_id', 'timestamp'),
        Index('idx_detection_type', 'detection_type'),
        Index('idx_detection_class', 'class_name'),
        Index('idx_detection_timestamp', 'timestamp'),
        Index('idx_detection_reviewed', 'reviewed'),
    )

class IncidentModel(Base):
    """Field incident requiring attention"""
    __tablename__ = 'incidents'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    plot_id = Column(String, ForeignKey('plots.id'))
    detection_id = Column(String, ForeignKey('detections.id'))
    incident_type = Column(String)  # 'disease', 'pest', 'stress', 'other'
    title = Column(String, nullable=False)
    description = Column(String)
    severity = Column(Integer)  # 1-6 (AlertSeverity)
    status = Column(String, default="pending")
    location = Column(Geometry('POINT'))
    affected_area = Column(Geometry('POLYGON'))
    estimated_impact = Column(String)
    recommended_action = Column(String)
    assigned_to = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime)
    resolution_notes = Column(String)
    images = Column(JSON)  # List of image paths
    metadata = Column(JSON)
    
    # Relationships
    plot = relationship("PlotModel", back_populates="incidents")
    detection = relationship("DetectionModel", back_populates="incident")
    tasks = relationship("TaskModel", back_populates="incident")
    
    # Indexes
    __table_args__ = (
        Index('idx_incident_plot', 'plot_id'),
        Index('idx_incident_status', 'status'),
        Index('idx_incident_severity', 'severity'),
        Index('idx_incident_created', 'created_at'),
    )

class TaskModel(Base):
    """Field task for workers"""
    __tablename__ = 'tasks'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, ForeignKey('incidents.id'))
    title = Column(String, nullable=False)
    description = Column(String)
    task_type = Column(String)  # 'inspection', 'treatment', 'harvest', etc.
    priority = Column(Integer)  # 1-5 (TaskPriority)
    status = Column(String, default="pending")
    assigned_to = Column(String)
    location = Column(Geometry('POINT'))
    due_date = Column(DateTime)
    estimated_duration = Column(Integer)  # minutes
    actual_duration = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    completion_notes = Column(String)
    completion_images = Column(JSON)
    metadata = Column(JSON)
    
    # Relationships
    incident = relationship("IncidentModel", back_populates="tasks")
    
    # Indexes
    __table_args__ = (
        Index('idx_task_status', 'status'),
        Index('idx_task_assigned', 'assigned_to'),
        Index('idx_task_priority', 'priority'),
        Index('idx_task_due_date', 'due_date'),
    )

class UserModel(Base):
    """User/Worker"""
    __tablename__ = 'users'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True)
    password_hash = Column(String)
    full_name = Column(String)
    role = Column(String)  # 'admin', 'manager', 'worker', 'viewer'
    phone_number = Column(String)
    current_location = Column(Geometry('POINT'))
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    fcm_token = Column(String)  # Firebase Cloud Messaging token
    preferences = Column(JSON)
    metadata = Column(JSON)
    
    # Indexes
    __table_args__ = (
        Index('idx_user_username', 'username'),
        Index('idx_user_role', 'role'),
        Index('idx_user_active', 'is_active'),
    )

# ======================================================================================================================
# SECTION 4: GEOSPATIAL MANAGER
# ======================================================================================================================

class GeospatialManager:
    """Manages all geospatial operations and digital twin mapping"""
    
    def __init__(self):
        self.transformer_to_utm = None
        self.transformer_from_utm = None
        self.farm_boundaries = {}
        self.plot_boundaries = {}
        self.camera_coverage = {}
        
        logger.info("[GEO] Geospatial Manager initialized")
    
    def setup_coordinate_system(self, center_lat: float, center_lon: float):
        """Setup coordinate transformation for a farm's location"""
        # Determine UTM zone
        utm_zone = int((center_lon + 180) / 6) + 1
        utm_crs = f"{UTM_CRS_BASE}{utm_zone}N" if center_lat >= 0 else f"{UTM_CRS_BASE}{utm_zone}S"
        
        # Create transformers
        self.transformer_to_utm = Transformer.from_crs(
            DEFAULT_CRS, utm_crs, always_xy=True
        )
        self.transformer_from_utm = Transformer.from_crs(
            utm_crs, DEFAULT_CRS, always_xy=True
        )
        
        logger.info(f"[GEO] Coordinate system setup: {utm_crs}")
    
    def pixel_to_gps(self, camera_id: str, pixel_x: int, pixel_y: int,
                     camera_pos: GeoPosition, camera_direction: float,
                     camera_fov: float, image_width: int, image_height: int,
                     ground_elevation: float = 0.0) -> Optional[GeoPosition]:
        """
        Convert pixel coordinates to GPS coordinates using camera calibration
        
        This is the critical function that enables the "tap on video -> GPS navigation" feature
        """
        try:
            # Get camera parameters
            camera_height = camera_pos.altitude - ground_elevation
            if camera_height <= 0:
                return None
            
            # Calculate normalized pixel coordinates (-0.5 to 0.5)
            norm_x = (pixel_x / image_width) - 0.5
            norm_y = (pixel_y / image_height) - 0.5
            
            # Calculate horizontal and vertical field of view
            aspect_ratio = image_width / image_height
            h_fov = camera_fov
            v_fov = camera_fov / aspect_ratio
            
            # Calculate angles from camera center
            h_angle = norm_x * h_fov
            v_angle = norm_y * v_fov
            
            # Calculate ground distance using trigonometry
            # This is a simplified model; real implementation would use full camera calibration matrix
            ground_distance = camera_height * np.tan(np.radians(90 - v_angle))
            
            # Calculate bearing to point
            bearing = (camera_direction + h_angle) % 360
            
            # Calculate GPS offset using bearing and distance
            # Convert to radians
            bearing_rad = np.radians(bearing)
            
            # Earth radius in meters
            R = 6371000
            
            # Calculate new position
            lat1 = np.radians(camera_pos.latitude)
            lon1 = np.radians(camera_pos.longitude)
            
            lat2 = np.arcsin(
                np.sin(lat1) * np.cos(ground_distance / R) +
                np.cos(lat1) * np.sin(ground_distance / R) * np.cos(bearing_rad)
            )
            
            lon2 = lon1 + np.arctan2(
                np.sin(bearing_rad) * np.sin(ground_distance / R) * np.cos(lat1),
                np.cos(ground_distance / R) - np.sin(lat1) * np.sin(lat2)
            )
            
            # Convert back to degrees
            target_lat = np.degrees(lat2)
            target_lon = np.degrees(lon2)
            
            result = GeoPosition(
                latitude=target_lat,
                longitude=target_lon,
                altitude=ground_elevation,
                accuracy=ground_distance * 0.1,  # 10% of distance as accuracy estimate
                timestamp=datetime.utcnow()
            )
            
            logger.debug(f"[GEO] Pixel ({pixel_x}, {pixel_y}) -> GPS ({target_lat:.6f}, {target_lon:.6f})")
            return result
            
        except Exception as e:
            logger.error(f"[GEO] Pixel to GPS conversion error: {e}")
            return None
    
    def calculate_camera_coverage(self, camera_pos: GeoPosition, direction: float,
                                   fov: float, max_range: float) -> Polygon:
        """Calculate the ground area covered by a camera's field of view"""
        try:
            # Calculate coverage polygon vertices
            angles = [
                direction - fov/2,
                direction + fov/2
            ]
            
            # Create coverage polygon
            vertices = [camera_pos.to_point()]
            
            for angle in angles:
                # Calculate point at max range
                bearing_rad = np.radians(angle)
                R = 6371000  # Earth radius
                
                lat1 = np.radians(camera_pos.latitude)
                lon1 = np.radians(camera_pos.longitude)
                
                lat2 = np.arcsin(
                    np.sin(lat1) * np.cos(max_range / R) +
                    np.cos(lat1) * np.sin(max_range / R) * np.cos(bearing_rad)
                )
                
                lon2 = lon1 + np.arctan2(
                    np.sin(bearing_rad) * np.sin(max_range / R) * np.cos(lat1),
                    np.cos(max_range / R) - np.sin(lat1) * np.sin(lat2)
                )
                
                vertices.append(Point(np.degrees(lon2), np.degrees(lat2)))
            
            vertices.append(camera_pos.to_point())  # Close the polygon
            
            coverage = Polygon([(p.x, p.y) for p in vertices])
            
            logger.debug(f"[GEO] Camera coverage calculated: {coverage.area} sq degrees")
            return coverage
            
        except Exception as e:
            logger.error(f"[GEO] Coverage calculation error: {e}")
            return Polygon()
    
    def find_nearest_camera(self, position: GeoPosition, cameras: List[Dict]) -> Optional[str]:
        """Find nearest camera to a GPS position"""
        min_distance = float('inf')
        nearest_camera_id = None
        
        for camera in cameras:
            camera_pos = GeoPosition(
                latitude=camera['latitude'],
                longitude=camera['longitude']
            )
            
            distance = position.distance_to(camera_pos)
            
            if distance < min_distance:
                min_distance = distance
                nearest_camera_id = camera['id']
        
        return nearest_camera_id
    
    def create_navigation_route(self, start: GeoPosition, end: GeoPosition,
                                obstacles: List[Polygon] = None) -> LineString:
        """Create navigation route avoiding obstacles"""
        # Simplified straight-line route
        # Real implementation would use pathfinding algorithm considering obstacles
        
        route = LineString([
            (start.longitude, start.latitude),
            (end.longitude, end.latitude)
        ])
        
        return route
    
    def generate_farm_map(self, farm_id: str, include_layers: List[str] = None) -> str:
        """Generate interactive Folium map for a farm"""
        if not GEOSPATIAL_AVAILABLE:
            return None
        
        try:
            # Create base map
            map_obj = folium.Map(
                location=[0, 0],  # Will be set from farm center
                zoom_start=16,
                tiles='Esri.WorldImagery'
            )
            
            # Add farm layers
            if include_layers:
                for layer in include_layers:
                    if layer == 'plots':
                        pass  # Add plot boundaries
                    elif layer == 'cameras':
                        pass  # Add camera locations and coverage
                    elif layer == 'devices':
                        pass  # Add ESP32 device locations
                    elif layer == 'incidents':
                        pass  # Add incident markers
            
            # Save to HTML
            map_path = f"{TEMP_STORAGE_PATH}/maps/farm_{farm_id}.html"
            map_obj.save(map_path)
            
            return map_path
            
        except Exception as e:
            logger.error(f"[GEO] Map generation error: {e}")
            return None

# ======================================================================================================================
# SECTION 5: GEMINI AI INTEGRATION
# ======================================================================================================================

class GeminiAIEngine:
    """Gemini AI integration for advanced crop analysis"""
    
    def __init__(self):
        self.initialized = False
        self.model = None
        self.vision_model = None
        self.request_count = 0
        self.total_tokens_used = 0
        
        if GEMINI_AVAILABLE:
            self.initialize()
    
    def initialize(self):
        """Initialize Gemini AI"""
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            
            # Initialize text model
            self.model = genai.GenerativeModel(
                model_name=GEMINI_MODEL,
                generation_config={
                    'temperature': GEMINI_TEMPERATURE,
                    'top_p': GEMINI_TOP_P,
                    'top_k': GEMINI_TOP_K,
                    'max_output_tokens': GEMINI_MAX_TOKENS,
                }
            )
            
            # Initialize vision model
            self.vision_model = genai.GenerativeModel(model_name=GEMINI_VISION_MODEL)
            
            self.initialized = True
            logger.info("[GEMINI] Gemini AI initialized successfully")
            
        except Exception as e:
            logger.error(f"[GEMINI] Initialization error: {e}")
            self.initialized = False
    
    async def analyze_crop_image(self, image_path: str, crop_type: str,
                                  context: Dict = None) -> Dict:
        """
        Analyze crop image using Gemini Vision
        
        This is the core function for the "advanced scan" when worker reaches the location
        """
        if not self.initialized:
            return {'error': 'Gemini AI not initialized'}
        
        try:
            # Load image
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Prepare context prompt
            prompt = self._build_crop_analysis_prompt(crop_type, context)
            
            # Generate content
            response = await asyncio.to_thread(
                self.vision_model.generate_content,
                [prompt, {'mime_type': 'image/jpeg', 'data': image_data}]
            )
            
            self.request_count += 1
            
            # Parse response
            result = self._parse_crop_analysis_response(response.text)
            result['model'] = GEMINI_VISION_MODEL
            result['timestamp'] = datetime.utcnow().isoformat()
            
            logger.info(f"[GEMINI] Crop analysis complete: {result.get('diagnosis', 'unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"[GEMINI] Analysis error: {e}")
            return {'error': str(e)}
    
    def _build_crop_analysis_prompt(self, crop_type: str, context: Dict = None) -> str:
        """Build detailed prompt for crop analysis"""
        prompt = f"""You are an expert agricultural pathologist analyzing a {crop_type} plant image.

Perform a comprehensive analysis and provide:

1. **Health Status**: Overall health (Healthy/Diseased/Stressed)
2. **Disease Identification**: If diseased, identify the specific disease with confidence level
3. **Pest Detection**: Any visible pest presence
4. **Symptom Description**: Detailed description of visible symptoms
5. **Severity Assessment**: Rate severity as Low/Medium/High/Critical
6. **Recommended Action**: Immediate treatment recommendations
7. **Preventive Measures**: Steps to prevent spread
8. **Chemical Treatment**: Specific fungicide/pesticide recommendations if applicable
9. **Organic Treatment**: Organic treatment alternatives
10. **Expected Recovery Time**: Timeline for treatment effectiveness

"""
        
        if context:
            prompt += "\n**Additional Context:**\n"
            if 'environmental' in context:
                env = context['environmental']
                prompt += f"- Temperature: {env.get('temperature')}°C\n"
                prompt += f"- Humidity: {env.get('humidity')}%\n"
                prompt += f"- Soil Moisture: {env.get('soil_moisture')}%\n"
            
            if 'growth_stage' in context:
                prompt += f"- Growth Stage: {context['growth_stage']}\n"
            
            if 'previous_detections' in context:
                prompt += f"- Previous Issues: {context['previous_detections']}\n"
        
        prompt += """

Provide your analysis in a structured JSON format with all the above fields.
Be specific with disease names, chemical recommendations, and dosages.
"""
        
        return prompt
    
    def _parse_crop_analysis_response(self, response_text: str) -> Dict:
        """Parse Gemini response into structured format"""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if json_match:
                return json.loads(json_match.group())
            else:
                # Fallback to text parsing
                return {
                    'diagnosis': 'Analysis completed',
                    'raw_response': response_text,
                    'confidence': 0.0
                }
        except Exception as e:
            logger.error(f"[GEMINI] Response parsing error: {e}")
            return {
                'diagnosis': 'Parse error',
                'raw_response': response_text,
                'error': str(e)
            }
    
    async def generate_field_report(self, farm_id: str, date_range: Tuple[datetime, datetime]) -> str:
        """Generate comprehensive field report using Gemini"""
        # Would gather all detections, sensor data, etc. and ask Gemini to summarize
        pass
    
    async def chat_agricultural_assistant(self, user_query: str, context: Dict = None) -> str:
        """Interactive agricultural assistant"""
        if not self.initialized:
            return "AI assistant not available"
        
        try:
            # Build context-aware prompt
            system_context = """You are an expert agricultural advisor helping farmers with crop management,
disease identification, pest control, and farming best practices."""
            
            full_prompt = f"{system_context}\n\nUser Question: {user_query}"
            
            if context:
                full_prompt += f"\n\nContext: {json.dumps(context)}"
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                full_prompt
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"[GEMINI] Chat error: {e}")
            return f"Error: {str(e)}"

# ======================================================================================================================
# END OF PART 1
# Current line count: ~1,400+
# This is the foundation. Need to add ~48,000+ more lines across multiple modules:
# - Video stream processing
# - ESP32 device fleet management
# - Mobile worker guidance system
# - Real-time alert management
# - Task scheduling and routing
# - Advanced analytics
# - System monitoring
# - API endpoints
# - WebSocket handlers
# - Database operations
# - Cache management
# - Security and authentication
# - Logging and diagnostics
# ======================================================================================================================
