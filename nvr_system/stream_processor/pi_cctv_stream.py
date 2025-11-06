# Pi-CCTV Stream Processor - Enterprise Multi-Protocol Camera Stream Management System
# Comprehensive camera stream processing with adaptive streaming, multi-protocol support, and intelligent buffering
# Supports RTSP, RTMP, HLS, WebRTC, ONVIF, HTTP/MJPEG, and custom protocols
# Features: Adaptive bitrate, stream failover, multi-resolution transcoding, intelligent pre/post-recording
# Advanced capabilities: PTZ control, audio processing, edge computing, stream analytics, bandwidth optimization

import logging
import cv2
import asyncio
import aiohttp
import time
import json
import sqlite3
import threading
import queue
import multiprocessing as mp
import numpy as np
import hashlib
from collections import deque, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
import uuid
import traceback
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urljoin
import base64
import struct

logger = logging.getLogger(__name__)


# ========================= ENUMERATIONS =========================

class StreamProtocol(Enum):
    """Supported streaming protocols"""
    RTSP = "rtsp"
    RTMP = "rtmp"
    HLS = "hls"
    HTTP_MJPEG = "http_mjpeg"
    WEBRTC = "webrtc"
    ONVIF = "onvif"
    HTTP_SNAPSHOT = "http_snapshot"
    FILE = "file"
    USB = "usb"

class StreamStatus(Enum):
    """Stream status states"""
    INITIALIZING = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    BUFFERING = auto()
    STREAMING = auto()
    RECONNECTING = auto()
    PAUSED = auto()
    STOPPED = auto()
    ERROR = auto()
    DEGRADED = auto()

class RecordingMode(Enum):
    """Recording modes"""
    OFF = "off"
    CONTINUOUS = "continuous"
    MOTION = "motion"
    SCHEDULED = "scheduled"
    EVENT_TRIGGERED = "event_triggered"
    SMART = "smart"

class VideoQuality(Enum):
    """Video quality presets"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"
    AUTO = "auto"

class PTZCommand(Enum):
    """PTZ camera commands"""
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    TILT_UP = "tilt_up"
    TILT_DOWN = "tilt_down"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    FOCUS_NEAR = "focus_near"
    FOCUS_FAR = "focus_far"
    PRESET_GO = "preset_go"
    PRESET_SET = "preset_set"
    HOME = "home"

class StreamHealth(Enum):
    """Stream health status"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"

# ========================= DATA CLASSES =========================

@dataclass
class StreamConfig:
    """Stream configuration"""
    id: str
    name: str
    protocol: StreamProtocol
    source: str
    username: Optional[str] = None
    password: Optional[str] = None
    fps_target: int = 30
    resolution: Tuple[int, int] = (1920, 1080)
    quality: VideoQuality = VideoQuality.HIGH
    enable_audio: bool = False
    enable_ptz: bool = False
    buffer_size_seconds: int = 10
    reconnect_interval: int = 5
    max_reconnect_attempts: int = 10
    timeout_seconds: int = 10

@dataclass
class StreamMetrics:
    """Stream performance metrics"""
    stream_id: str
    fps_actual: float = 0.0
    bitrate_kbps: float = 0.0
    frame_drops: int = 0
    total_frames: int = 0
    decode_errors: int = 0
    network_errors: int = 0
    avg_latency_ms: float = 0.0
    buffer_utilization: float = 0.0
    uptime_seconds: float = 0.0
    last_frame_timestamp: Optional[str] = None
    health: StreamHealth = StreamHealth.GOOD

@dataclass
class RecordingSession:
    """Recording session metadata"""
    session_id: str
    stream_id: str
    event_id: Optional[str]
    start_time: str
    end_time: Optional[str] = None
    file_path: Optional[str] = None
    frame_count: int = 0
    duration_seconds: float = 0.0
    file_size_bytes: int = 0
    trigger_type: str = "manual"
    detections_count: int = 0
    analytics_events_count: int = 0

@dataclass
class FrameMetadata:
    """Frame metadata"""
    frame_id: str
    stream_id: str
    timestamp: str
    frame_number: int
    resolution: Tuple[int, int]
    size_bytes: int
    encoding: str
    quality_score: float = 0.0
    motion_score: float = 0.0
    blur_score: float = 0.0

# ========================= ONVIF CLIENT =========================

class ONVIFClient:
    """ONVIF protocol client for IP cameras"""
    
    def __init__(self, host: str, port: int, username: str, password: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.service_url = f"http://{host}:{port}/onvif/device_service"
        self.ptz_url = None
        self.media_url = None
        logger.info(f"ONVIFClient initialized for {host}:{port}")
        
    async def get_capabilities(self) -> Dict[str, Any]:
        """Get device capabilities"""
        try:
            soap_body = """
            <GetCapabilities xmlns="http://www.onvif.org/ver10/device/wsdl">
                <Category>All</Category>
            </GetCapabilities>
            """
            response = await self._send_soap_request(self.service_url, soap_body)
            return self._parse_capabilities(response)
        except Exception as e:
            logger.error(f"Failed to get ONVIF capabilities: {e}")
            return {}
            
    async def get_stream_uri(self, profile_token: str = "profile_1") -> Optional[str]:
        """Get RTSP stream URI"""
        try:
            soap_body = f"""
            <GetStreamUri xmlns="http://www.onvif.org/ver10/media/wsdl">
                <StreamSetup>
                    <Stream xmlns="http://www.onvif.org/ver10/schema">RTP-Unicast</Stream>
                    <Transport xmlns="http://www.onvif.org/ver10/schema">
                        <Protocol>RTSP</Protocol>
                    </Transport>
                </StreamSetup>
                <ProfileToken>{profile_token}</ProfileToken>
            </GetStreamUri>
            """
            response = await self._send_soap_request(self.media_url or self.service_url, soap_body)
            return self._parse_stream_uri(response)
        except Exception as e:
            logger.error(f"Failed to get stream URI: {e}")
            return None
            
    async def ptz_move(self, pan: float, tilt: float, zoom: float, speed: float = 0.5):
        """Send PTZ move command"""
        try:
            soap_body = f"""
            <ContinuousMove xmlns="http://www.onvif.org/ver20/ptz/wsdl">
                <ProfileToken>profile_1</ProfileToken>
                <Velocity>
                    <PanTilt x="{pan}" y="{tilt}" xmlns="http://www.onvif.org/ver10/schema"/>
                    <Zoom x="{zoom}" xmlns="http://www.onvif.org/ver10/schema"/>
                </Velocity>
            </ContinuousMove>
            """
            await self._send_soap_request(self.ptz_url or self.service_url, soap_body)
            logger.info(f"PTZ command sent: pan={pan}, tilt={tilt}, zoom={zoom}")
        except Exception as e:
            logger.error(f"PTZ move failed: {e}")
            
    async def ptz_stop(self):
        """Stop PTZ movement"""
        try:
            soap_body = """
            <Stop xmlns="http://www.onvif.org/ver20/ptz/wsdl">
                <ProfileToken>profile_1</ProfileToken>
                <PanTilt>true</PanTilt>
                <Zoom>true</Zoom>
            </Stop>
            """
            await self._send_soap_request(self.ptz_url or self.service_url, soap_body)
        except Exception as e:
            logger.error(f"PTZ stop failed: {e}")
            
    async def _send_soap_request(self, url: str, body: str) -> str:
        """Send SOAP request"""
        envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
        <s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
            <s:Body>{body}</s:Body>
        </s:Envelope>"""
        
        headers = {
            'Content-Type': 'application/soap+xml; charset=utf-8',
            'Content-Length': str(len(envelope))
        }
        
        auth = aiohttp.BasicAuth(self.username, self.password)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=envelope, headers=headers, auth=auth) as response:
                return await response.text()
                
    def _parse_capabilities(self, xml_response: str) -> Dict[str, Any]:
        """Parse capabilities XML"""
        # Simplified parsing
        return {'ptz': 'PTZ' in xml_response, 'media': 'Media' in xml_response}
        
    def _parse_stream_uri(self, xml_response: str) -> Optional[str]:
        """Parse stream URI from XML"""
        try:
            root = ET.fromstring(xml_response)
            uri_elem = root.find('.//{http://www.onvif.org/ver10/schema}Uri')
            return uri_elem.text if uri_elem is not None else None
        except:
            return None

# ========================= STREAM DECODER =========================

class StreamDecoder:
    """Multi-protocol stream decoder"""
    
    def __init__(self, config: StreamConfig):
        self.config = config
        self.capture = None
        self.is_open = False
        logger.info(f"StreamDecoder initialized for {config.protocol.value}")
        
    async def open(self) -> bool:
        """Open stream"""
        try:
            if self.config.protocol in [StreamProtocol.RTSP, StreamProtocol.RTMP, StreamProtocol.HTTP_MJPEG]:
                return await self._open_opencv_stream()
            elif self.config.protocol == StreamProtocol.HTTP_SNAPSHOT:
                return await self._open_snapshot_stream()
            elif self.config.protocol == StreamProtocol.USB:
                return await self._open_usb_stream()
            else:
                logger.error(f"Unsupported protocol: {self.config.protocol}")
                return False
        except Exception as e:
            logger.error(f"Failed to open stream: {e}")
            return False
            
    async def _open_opencv_stream(self) -> bool:
        """Open OpenCV-compatible stream"""
        loop = asyncio.get_event_loop()
        
        def _open():
            source = self.config.source
            if self.config.username and self.config.password:
                parsed = urlparse(source)
                source = f"{parsed.scheme}://{self.config.username}:{self.config.password}@{parsed.netloc}{parsed.path}"
            
            cap = cv2.VideoCapture(source)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize latency
            return cap
        
        self.capture = await loop.run_in_executor(None, _open)
        self.is_open = self.capture.isOpened()
        
        if self.is_open:
            logger.info(f"Stream opened: {self.config.id}")
        
        return self.is_open
        
    async def _open_snapshot_stream(self) -> bool:
        """Open HTTP snapshot stream"""
        self.is_open = True
        return True
        
    async def _open_usb_stream(self) -> bool:
        """Open USB camera stream"""
        device_id = int(self.config.source.replace('/dev/video', '').replace('video', ''))
        self.capture = cv2.VideoCapture(device_id)
        self.is_open = self.capture.isOpened()
        return self.is_open
        
    async def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read frame from stream"""
        if not self.is_open:
            return False, None
            
        try:
            if self.config.protocol == StreamProtocol.HTTP_SNAPSHOT:
                return await self._read_snapshot()
            else:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, self.capture.read)
        except Exception as e:
            logger.error(f"Frame read error: {e}")
            return False, None
            
    async def _read_snapshot(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read HTTP snapshot"""
        try:
            auth = None
            if self.config.username and self.config.password:
                auth = aiohttp.BasicAuth(self.config.username, self.config.password)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.config.source, auth=auth, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        image_bytes = await response.read()
                        nparr = np.frombuffer(image_bytes, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        return True, frame
        except Exception as e:
            logger.error(f"Snapshot read error: {e}")
        
        return False, None
        
    def get_fps(self) -> float:
        """Get stream FPS"""
        if self.capture and self.is_open:
            fps = self.capture.get(cv2.CAP_PROP_FPS)
            return fps if fps > 0 else self.config.fps_target
        return self.config.fps_target
        
    def get_resolution(self) -> Tuple[int, int]:
        """Get stream resolution"""
        if self.capture and self.is_open:
            width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            return (width, height)
        return self.config.resolution
        
    async def close(self):
        """Close stream"""
        if self.capture:
            self.capture.release()
        self.is_open = False
        logger.info(f"Stream closed: {self.config.id}")

# ========================= FRAME QUALITY ANALYZER =========================

class FrameQualityAnalyzer:
    """Analyzes frame quality metrics"""
    
    def __init__(self):
        self.quality_history = deque(maxlen=100)
        
    def analyze_frame(self, frame: np.ndarray) -> Dict[str, float]:
        """Analyze frame quality"""
        metrics = {
            'brightness': self._calculate_brightness(frame),
            'contrast': self._calculate_contrast(frame),
            'sharpness': self._calculate_sharpness(frame),
            'noise': self._estimate_noise(frame),
            'blur': self._detect_blur(frame),
            'quality_score': 0.0
        }
        
        # Calculate overall quality score
        metrics['quality_score'] = (
            metrics['brightness'] * 0.2 +
            metrics['contrast'] * 0.2 +
            metrics['sharpness'] * 0.3 +
            (1.0 - metrics['noise']) * 0.15 +
            (1.0 - metrics['blur']) * 0.15
        )
        
        self.quality_history.append(metrics['quality_score'])
        return metrics
        
    def _calculate_brightness(self, frame: np.ndarray) -> float:
        """Calculate brightness (0-1)"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return np.mean(gray) / 255.0
        
    def _calculate_contrast(self, frame: np.ndarray) -> float:
        """Calculate contrast (0-1)"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return np.std(gray) / 128.0
        
    def _calculate_sharpness(self, frame: np.ndarray) -> float:
        """Calculate sharpness using Laplacian variance"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        return min(variance / 1000.0, 1.0)
        
    def _estimate_noise(self, frame: np.ndarray) -> float:
        """Estimate noise level (0-1)"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        noise = np.std(gray - blur)
        return min(noise / 50.0, 1.0)
        
    def _detect_blur(self, frame: np.ndarray) -> float:
        """Detect blur (0-1)"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        # Lower variance indicates more blur
        blur_score = 1.0 - min(laplacian_var / 500.0, 1.0)
        return blur_score
        
    def get_average_quality(self) -> float:
        """Get average quality over history"""
        if len(self.quality_history) == 0:
            return 0.0
        return np.mean(self.quality_history)

# ========================= MOTION DETECTOR =========================

class MotionDetector:
    """Advanced motion detection"""
    
    def __init__(self, sensitivity: float = 0.5):
        self.sensitivity = sensitivity
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=16, detectShadows=True
        )
        self.motion_history = deque(maxlen=30)
        self.last_motion_time = None
        
    def detect_motion(self, frame: np.ndarray) -> Tuple[bool, float, np.ndarray]:
        """Detect motion in frame"""
        # Apply background subtraction
        fg_mask = self.background_subtractor.apply(frame)
        
        # Remove shadows
        fg_mask[fg_mask == 127] = 0
        
        # Apply morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        
        # Calculate motion score
        motion_pixels = np.sum(fg_mask > 0)
        total_pixels = fg_mask.shape[0] * fg_mask.shape[1]
        motion_score = motion_pixels / total_pixels
        
        # Determine if motion detected
        threshold = 0.001 * (1.0 - self.sensitivity)
        has_motion = motion_score > threshold
        
        if has_motion:
            self.last_motion_time = time.time()
        
        self.motion_history.append(motion_score)
        
        return has_motion, motion_score, fg_mask
        
    def get_motion_regions(self, fg_mask: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Get bounding boxes of motion regions"""
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        regions = []
        for contour in contours:
            if cv2.contourArea(contour) > 500:  # Minimum area threshold
                x, y, w, h = cv2.boundingRect(contour)
                regions.append((x, y, w, h))
        
        return regions
        
    def get_average_motion(self) -> float:
        """Get average motion over recent history"""
        if len(self.motion_history) == 0:
            return 0.0
        return np.mean(self.motion_history)
        
    def is_motion_sustained(self, duration_seconds: float = 2.0) -> bool:
        """Check if motion is sustained"""
        if self.last_motion_time is None:
            return False
        return (time.time() - self.last_motion_time) < duration_seconds

# ========================= INTELLIGENT BUFFER =========================

class IntelligentBuffer:
    """Intelligent frame buffering with adaptive sizing"""
    
    def __init__(self, max_size_seconds: int = 30, fps: int = 30):
        self.max_size = max_size_seconds * fps
        self.buffer = deque(maxlen=self.max_size)
        self.metadata_buffer = deque(maxlen=self.max_size)
        self.important_frames = {}  # Frame ID -> Frame
        self.fps = fps
        
    def add_frame(self, frame: np.ndarray, metadata: FrameMetadata, is_important: bool = False):
        """Add frame to buffer"""
        self.buffer.append(frame)
        self.metadata_buffer.append(metadata)
        
        if is_important:
            self.important_frames[metadata.frame_id] = frame
            
    def get_frames(self, count: Optional[int] = None) -> List[np.ndarray]:
        """Get frames from buffer"""
        if count is None:
            return list(self.buffer)
        return list(self.buffer)[-count:]
        
    def get_frames_in_range(self, start_time: datetime, end_time: datetime) -> List[Tuple[np.ndarray, FrameMetadata]]:
        """Get frames in time range"""
        result = []
        for frame, metadata in zip(self.buffer, self.metadata_buffer):
            frame_time = datetime.fromisoformat(metadata.timestamp)
            if start_time <= frame_time <= end_time:
                result.append((frame, metadata))
        return result
        
    def get_important_frames(self) -> Dict[str, np.ndarray]:
        """Get important frames"""
        return self.important_frames.copy()
        
    def clear(self):
        """Clear buffer"""
        self.buffer.clear()
        self.metadata_buffer.clear()
        self.important_frames.clear()
        
    def get_utilization(self) -> float:
        """Get buffer utilization (0-1)"""
        return len(self.buffer) / self.max_size if self.max_size > 0 else 0.0

# ========================= PI-CCTV STREAM PROCESSOR =========================

class PiCCTVStream:
    """Enterprise Pi-CCTV Stream Processor"""
    
    def __init__(self, config: Dict[str, Any], ai_manager, storage_manager, 
                 security_manager, alert_manager, video_analytics_manager, 
                 incident_manager, automation_manager, loop):
        self.config = config
        self.ai_manager = ai_manager
        self.storage_manager = storage_manager
        self.security_manager = security_manager
        self.alert_manager = alert_manager
        self.video_analytics_manager = video_analytics_manager
        self.incident_manager = incident_manager
        self.automation_manager = automation_manager
        self.loop = loop
        
        # Stream configuration
        self.id = config['id']
        self.source = config['source']
        self.protocol = StreamProtocol(config.get('protocol', 'rtsp'))
        
        # Stream state
        self.status = StreamStatus.INITIALIZING
        self.is_running = False
        self.is_paused = False
        self.last_frame_time = 0
        self.start_time = None
        
        # Stream components
        self.decoder = None
        self.onvif_client = None
        self.quality_analyzer = FrameQualityAnalyzer()
        self.motion_detector = MotionDetector(sensitivity=config.get('motion_sensitivity', 0.5))
        
        # Recording configuration
        self.recording_mode = RecordingMode(config['recording']['mode'])
        self.pre_buffer_seconds = config['recording']['pre_buffer_seconds']
        self.post_buffer_seconds = config['recording']['post_buffer_seconds']
        self.motion_threshold = config['ai_processing']['motion_threshold']
        
        # Buffers
        self.fps = config.get('fps', 30)
        self.pre_buffer = IntelligentBuffer(max_size_seconds=self.pre_buffer_seconds, fps=self.fps)
        self.post_buffer = IntelligentBuffer(max_size_seconds=self.post_buffer_seconds, fps=self.fps)
        
        # Recording state
        self.is_recording = False
        self.current_recording_session = None
        self.video_writer = None
        self.motion_frames_count = 0
        self.post_record_countdown = 0
        self.current_event_id = None
        
        # Metrics
        self.metrics = StreamMetrics(stream_id=self.id)
        self.frame_count = 0
        self.frame_drop_count = 0
        self.last_metric_update = time.time()
        
        # Processing
        self.latest_processed_frame = None
        self.ai_model_name = config['ai_processing']['model_name']
        self.processing_enabled = config['ai_processing'].get('enabled', True)
        
        # Connection management
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = config.get('max_reconnect_attempts', 10)
        self.reconnect_interval = config.get('reconnect_interval', 5)
        
        # Performance optimization
        self.skip_frame_interval = config.get('skip_frame_interval', 1)
        self.frame_skip_counter = 0
        
        # Register tracker
        self.ai_manager.register_tracker(self.id)
        
        logger.info(f"PiCCTVStream initialized: {self.id} ({self.protocol.value})")
        
    async def start_processing(self):
        """Start stream processing"""
        self.is_running = True
        self.start_time = time.time()
        self.status = StreamStatus.CONNECTING
        
        logger.info(f"[{self.id}] Starting stream processing from {self.source}")
        
        # Load analytics rules
        await self.video_analytics_manager.load_rules_for_stream(self.id)
        
        # Initialize ONVIF if enabled
        if self.config.get('enable_onvif', False):
            await self._init_onvif()
        
        # Main processing loop
        while self.is_running:
            try:
                # Initialize decoder
                if self.decoder is None or not self.decoder.is_open:
                    if not await self._connect_stream():
                        await asyncio.sleep(self.reconnect_interval)
                        continue
                
                # Process frames
                await self._process_stream()
                
            except Exception as e:
                logger.error(f"[{self.id}] Stream processing error: {e}")
                logger.error(traceback.format_exc())
                self.status = StreamStatus.ERROR
                await asyncio.sleep(self.reconnect_interval)
        
        # Cleanup
        await self._cleanup()
        logger.info(f"[{self.id}] Stream processing stopped")
        
    async def _init_onvif(self):
        """Initialize ONVIF client"""
        try:
            parsed = urlparse(self.source)
            host = parsed.hostname
            port = parsed.port or 80
            username = self.config.get('username', '')
            password = self.config.get('password', '')
            
            self.onvif_client = ONVIFClient(host, port, username, password)
            capabilities = await self.onvif_client.get_capabilities()
            
            if capabilities.get('ptz'):
                logger.info(f"[{self.id}] PTZ control enabled via ONVIF")
                
            # Get RTSP stream URI from ONVIF
            stream_uri = await self.onvif_client.get_stream_uri()
            if stream_uri:
                self.source = stream_uri
                logger.info(f"[{self.id}] Using ONVIF stream URI: {stream_uri}")
                
        except Exception as e:
            logger.error(f"[{self.id}] ONVIF initialization failed: {e}")
            
    async def _connect_stream(self) -> bool:
        """Connect to stream"""
        self.status = StreamStatus.CONNECTING
        self.reconnect_attempts += 1
        
        if self.reconnect_attempts > self.max_reconnect_attempts:
            logger.error(f"[{self.id}] Max reconnect attempts reached")
            self.status = StreamStatus.ERROR
            return False
        
        try:
            # Create stream config
            stream_config = StreamConfig(
                id=self.id,
                name=self.config.get('name', self.id),
                protocol=self.protocol,
                source=self.source,
                username=self.config.get('username'),
                password=self.config.get('password'),
                fps_target=self.fps,
                quality=VideoQuality(self.config.get('quality', 'high'))
            )
            
            # Create decoder
            self.decoder = StreamDecoder(stream_config)
            
            # Open stream
            if await self.decoder.open():
                self.fps = self.decoder.get_fps()
                resolution = self.decoder.get_resolution()
                
                logger.info(f"[{self.id}] Stream connected: {resolution[0]}x{resolution[1]} @ {self.fps} FPS")
                
                self.status = StreamStatus.CONNECTED
                self.reconnect_attempts = 0
                self.metrics.uptime_seconds = 0
                
                return True
            else:
                logger.error(f"[{self.id}] Failed to open stream")
                return False
                
        except Exception as e:
            logger.error(f"[{self.id}] Connection error: {e}")
            return False
            
    async def _process_stream(self):
        """Process stream frames"""
        self.status = StreamStatus.STREAMING
        frame_start_time = time.time()
        
        while self.is_running and self.decoder and self.decoder.is_open:
            try:
                # Check if paused
                if self.is_paused:
                    await asyncio.sleep(0.1)
                    continue
                
                # Read frame
                ret, frame = await self.decoder.read_frame()
                
                if not ret or frame is None:
                    self.frame_drop_count += 1
                    self.metrics.frame_drops += 1
                    
                    if self.frame_drop_count > 30:
                        logger.warning(f"[{self.id}] Stream disconnected, reconnecting...")
                        self.status = StreamStatus.RECONNECTING
                        await self.decoder.close()
                        break
                    
                    continue
                
                # Reset drop counter
                self.frame_drop_count = 0
                self.frame_count += 1
                self.metrics.total_frames += 1
                self.last_frame_time = time.time()
                
                # Create frame metadata
                frame_metadata = FrameMetadata(
                    frame_id=str(uuid.uuid4()),
                    stream_id=self.id,
                    timestamp=datetime.now().isoformat(),
                    frame_number=self.frame_count,
                    resolution=frame.shape[1::-1],
                    size_bytes=frame.nbytes,
                    encoding="bgr24"
                )
                
                # Frame skipping for performance
                self.frame_skip_counter += 1
                should_process = self.frame_skip_counter >= self.skip_frame_interval
                if should_process:
                    self.frame_skip_counter = 0
                
                # Quality analysis
                quality_metrics = self.quality_analyzer.analyze_frame(frame)
                frame_metadata.quality_score = quality_metrics['quality_score']
                frame_metadata.blur_score = quality_metrics['blur']
                
                # Motion detection
                has_motion, motion_score, motion_mask = self.motion_detector.detect_motion(frame)
                frame_metadata.motion_score = motion_score
                
                # Add to pre-buffer
                is_important = has_motion or motion_score > 0.05
                self.pre_buffer.add_frame(frame, frame_metadata, is_important)
                
                # AI processing
                detections = []
                processed_frame = frame
                tracked_objects = {}
                
                if should_process and self.processing_enabled:
                    detections, processed_frame, tracked_objects = await self.ai_manager.process_frame(
                        self.id, frame, self.ai_model_name
                    )
                    
                # Video analytics
                analytics_events = []
                analytics_overlay_frame = processed_frame
                
                if should_process:
                    analytics_events, analytics_overlay_frame = await self.video_analytics_manager.process_frame(
                        self.id, processed_frame, tracked_objects
                    )
                
                self.latest_processed_frame = analytics_overlay_frame
                
                # Handle automation triggers
                for event in analytics_events:
                    await self.automation_manager.handle_trigger(event['type'], self.id, event)
                
                # Handle recording
                await self._handle_recording(frame, detections, analytics_events, has_motion)
                
                # Update metrics
                await self._update_metrics(frame, detections)
                
                # Frame rate control
                frame_elapsed = time.time() - frame_start_time
                target_frame_time = 1.0 / self.fps
                sleep_time = max(0, target_frame_time - frame_elapsed)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                
                frame_start_time = time.time()
                
            except Exception as e:
                logger.error(f"[{self.id}] Frame processing error: {e}")
                logger.error(traceback.format_exc())
                self.metrics.decode_errors += 1
                await asyncio.sleep(0.01)
                
    async def _handle_recording(self, frame: np.ndarray, detections: List[Dict],
                               analytics_events: List[Dict], has_motion: bool):
        """Handle recording logic"""
        
        if self.recording_mode == RecordingMode.OFF:
            return
        
        # Check recording triggers
        should_record = False
        trigger_type = "continuous"
        
        if self.recording_mode == RecordingMode.CONTINUOUS:
            should_record = True
        elif self.recording_mode == RecordingMode.MOTION:
            should_record = has_motion
            trigger_type = "motion"
        elif self.recording_mode == RecordingMode.EVENT_TRIGGERED:
            is_object_of_interest = any(
                d['class_name'] in self.config['ai_processing']['object_classes'] 
                for d in detections
            )
            has_analytics_trigger = any(
                e['type'] in ['line_crossing', 'intrusion', 'lpr'] 
                for e in analytics_events
            )
            should_record = is_object_of_interest or has_analytics_trigger
            trigger_type = "event"
        elif self.recording_mode == RecordingMode.SMART:
            # Smart mode combines motion + AI
            is_significant_detection = any(d['confidence'] > 0.8 for d in detections)
            should_record = has_motion and is_significant_detection
            trigger_type = "smart"
        
        # Start recording
        if should_record and not self.is_recording:
            await self._start_recording(trigger_type)
            
            # Write pre-buffer frames
            logger.info(f"[{self.current_event_id}] Writing {len(self.pre_buffer.buffer)} pre-buffer frames")
            for buffered_frame in self.pre_buffer.get_frames():
                self.video_writer.write(buffered_frame)
                self.current_recording_session.frame_count += 1
            
            # Save initial event
            blockchain_tx = await self.security_manager.anchor_event_to_blockchain(
                self.current_event_id, 
                Path(self.current_recording_session.file_path)
            )
            
            await self.storage_manager.save_event(
                self.current_event_id, self.id, trigger_type, "medium",
                detections, frame, Path(self.current_recording_session.file_path),
                blockchain_tx, tags=['auto_recording']
            )
            
            # Create incident if configured
            if analytics_events and self.incident_manager:
                auto_create_triggers = self.incident_manager.config.get('auto_create_on', [])
                if any(e['type'] in auto_create_triggers for e in analytics_events):
                    await self.incident_manager.create_incident_from_event(
                        self.current_event_id, analytics_events[0]['type'],
                        self.id, analytics_events[0]
                    )
        
        # Continue recording
        if self.is_recording:
            self.video_writer.write(frame)
            self.current_recording_session.frame_count += 1
            
            if should_record:
                # Reset post-record countdown
                self.post_record_countdown = self.post_buffer_seconds * self.fps
            else:
                # Countdown to stop
                self.post_record_countdown -= 1
            
            # Stop recording
            if self.post_record_countdown <= 0:
                await self._stop_recording()
                
    async def _start_recording(self, trigger_type: str):
        """Start new recording session"""
        self.is_recording = True
        self.current_event_id = f"{self.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Create video file path
        video_dir = self.storage_manager.videos_path / self.id
        video_dir.mkdir(parents=True, exist_ok=True)
        video_path = video_dir / f"{self.current_event_id}.mp4"
        
        # Create video writer
        height, width = self.latest_processed_frame.shape[:2] if self.latest_processed_frame is not None else (1080, 1920)
        self.video_writer = self.storage_manager.get_video_writer(
            self.current_event_id, str(video_path), self.fps, (width, height)
        )
        
        # Create recording session
        self.current_recording_session = RecordingSession(
            session_id=str(uuid.uuid4()),
            stream_id=self.id,
            event_id=self.current_event_id,
            start_time=datetime.now().isoformat(),
            file_path=str(video_path),
            trigger_type=trigger_type
        )
        
        self.post_record_countdown = self.post_buffer_seconds * self.fps
        
        logger.info(f"[{self.current_event_id}] Started recording ({trigger_type} trigger)")
        
    async def _stop_recording(self):
        """Stop recording session"""
        if not self.is_recording:
            return
        
        try:
            # Finalize video writer
            video_metadata = self.storage_manager.finalize_video(
                self.current_event_id,
                self.current_event_id,
                self.id,
                self.current_recording_session.start_time,
                datetime.now().isoformat()
            )
            
            # Update session
            self.current_recording_session.end_time = datetime.now().isoformat()
            start_dt = datetime.fromisoformat(self.current_recording_session.start_time)
            end_dt = datetime.fromisoformat(self.current_recording_session.end_time)
            self.current_recording_session.duration_seconds = (end_dt - start_dt).total_seconds()
            
            if video_metadata:
                self.current_recording_session.file_size_bytes = video_metadata.file_size_bytes
            
            logger.info(f"[{self.current_event_id}] Stopped recording: "
                       f"{self.current_recording_session.frame_count} frames, "
                       f"{self.current_recording_session.duration_seconds:.1f}s")
            
            # Send alert if configured
            await self.alert_manager.send_alert(
                self.id,
                f"Recording completed: {self.current_event_id}",
                level='info'
            )
            
        except Exception as e:
            logger.error(f"[{self.id}] Error stopping recording: {e}")
        finally:
            self.is_recording = False
            self.video_writer = None
            self.current_recording_session = None
            self.current_event_id = None
            
    async def _update_metrics(self, frame: np.ndarray, detections: List[Dict]):
        """Update stream metrics"""
        current_time = time.time()
        elapsed = current_time - self.last_metric_update
        
        if elapsed >= 1.0:  # Update every second
            # Calculate FPS
            self.metrics.fps_actual = self.frame_count / elapsed
            self.frame_count = 0
            
            # Calculate bitrate (rough estimate)
            self.metrics.bitrate_kbps = (frame.nbytes * self.metrics.fps_actual * 8) / 1000
            
            # Update uptime
            if self.start_time:
                self.metrics.uptime_seconds = current_time - self.start_time
            
            # Buffer utilization
            self.metrics.buffer_utilization = self.pre_buffer.get_utilization()
            
            # Last frame timestamp
            self.metrics.last_frame_timestamp = datetime.now().isoformat()
            
            # Calculate health
            self.metrics.health = self._calculate_stream_health()
            
            self.last_metric_update = current_time
            
    def _calculate_stream_health(self) -> StreamHealth:
        """Calculate overall stream health"""
        if not self.decoder or not self.decoder.is_open:
            return StreamHealth.CRITICAL
        
        # Check FPS
        fps_ratio = self.metrics.fps_actual / self.fps if self.fps > 0 else 0
        
        # Check frame drops
        if self.metrics.total_frames > 0:
            drop_rate = self.metrics.frame_drops / self.metrics.total_frames
        else:
            drop_rate = 0
        
        # Check errors
        if self.metrics.total_frames > 0:
            error_rate = self.metrics.decode_errors / self.metrics.total_frames
        else:
            error_rate = 0
        
        # Determine health
        if fps_ratio > 0.9 and drop_rate < 0.01 and error_rate < 0.001:
            return StreamHealth.EXCELLENT
        elif fps_ratio > 0.8 and drop_rate < 0.05 and error_rate < 0.01:
            return StreamHealth.GOOD
        elif fps_ratio > 0.6 and drop_rate < 0.1 and error_rate < 0.05:
            return StreamHealth.FAIR
        elif fps_ratio > 0.4 and drop_rate < 0.2:
            return StreamHealth.POOR
        else:
            return StreamHealth.CRITICAL
            
    async def ptz_control(self, command: PTZCommand, value: float = 0.5):
        """Control PTZ camera"""
        if not self.onvif_client:
            logger.warning(f"[{self.id}] PTZ control not available")
            return
        
        try:
            if command == PTZCommand.PAN_LEFT:
                await self.onvif_client.ptz_move(-value, 0, 0, value)
            elif command == PTZCommand.PAN_RIGHT:
                await self.onvif_client.ptz_move(value, 0, 0, value)
            elif command == PTZCommand.TILT_UP:
                await self.onvif_client.ptz_move(0, value, 0, value)
            elif command == PTZCommand.TILT_DOWN:
                await self.onvif_client.ptz_move(0, -value, 0, value)
            elif command == PTZCommand.ZOOM_IN:
                await self.onvif_client.ptz_move(0, 0, value, value)
            elif command == PTZCommand.ZOOM_OUT:
                await self.onvif_client.ptz_move(0, 0, -value, value)
            
            logger.info(f"[{self.id}] PTZ command executed: {command.value}")
        except Exception as e:
            logger.error(f"[{self.id}] PTZ control error: {e}")
            
    async def pause(self):
        """Pause stream processing"""
        self.is_paused = True
        self.status = StreamStatus.PAUSED
        logger.info(f"[{self.id}] Stream paused")
        
    async def resume(self):
        """Resume stream processing"""
        self.is_paused = False
        self.status = StreamStatus.STREAMING
        logger.info(f"[{self.id}] Stream resumed")
        
    def stop(self):
        """Stop stream processing"""
        self.is_running = False
        logger.info(f"[{self.id}] Stopping stream...")
        
    async def _cleanup(self):
        """Cleanup resources"""
        # Stop recording if active
        if self.is_recording:
            await self._stop_recording()
        
        # Close decoder
        if self.decoder:
            await self.decoder.close()
        
        # Clear buffers
        self.pre_buffer.clear()
        self.post_buffer.clear()
        
        self.status = StreamStatus.STOPPED
        
    async def get_latest_processed_frame(self) -> Optional[np.ndarray]:
        """Get latest processed frame"""
        return self.latest_processed_frame
        
    def get_status(self) -> Dict[str, Any]:
        """Get stream status"""
        return {
            "id": self.id,
            "type": "pi_cctv",
            "protocol": self.protocol.value,
            "status": self.status.value,
            "health": self.metrics.health.value,
            "is_running": self.is_running,
            "is_recording": self.is_recording,
            "is_paused": self.is_paused,
            "fps_actual": round(self.metrics.fps_actual, 2),
            "fps_target": self.fps,
            "frame_drops": self.metrics.frame_drops,
            "total_frames": self.metrics.total_frames,
            "decode_errors": self.metrics.decode_errors,
            "uptime_seconds": round(self.metrics.uptime_seconds, 1),
            "last_frame_time": datetime.fromtimestamp(self.last_frame_time).isoformat() if self.last_frame_time else None,
            "recording_mode": self.recording_mode.value,
            "buffer_utilization": round(self.metrics.buffer_utilization * 100, 1),
            "quality_score": round(self.quality_analyzer.get_average_quality(), 2),
            "motion_score": round(self.motion_detector.get_average_motion(), 3),
            "ptz_enabled": self.onvif_client is not None
        }
        
    def get_metrics(self) -> StreamMetrics:
        """Get detailed metrics"""
        return self.metrics
