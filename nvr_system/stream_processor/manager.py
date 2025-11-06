# Enterprise Stream Processing Management System
# Advanced multi-stream orchestration with load balancing, failover, and intelligent processing distribution

import asyncio
import cv2
import numpy as np
import logging
import time
import threading
import queue
import multiprocessing
import json
import sqlite3
import hashlib
import statistics
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set, Union, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import socket
import psutil
import gc

from .pi_cctv_stream import PiCCTVStream
from .esp32_snapshot_stream import ESP32SnapshotStream

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    from kubernetes import client, config as k8s_config
    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False

try:
    import nvidia_ml_py as nvml
    NVIDIA_ML_AVAILABLE = True
    nvml.nvmlInit()
except ImportError:
    NVIDIA_ML_AVAILABLE = False

logger = logging.getLogger(__name__)

class StreamStatus(Enum):
    INACTIVE = "inactive"
    INITIALIZING = "initializing"
    CONNECTING = "connecting"
    ACTIVE = "active"
    BUFFERING = "buffering"
    RECONNECTING = "reconnecting"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    STOPPED = "stopped"

class ProcessingPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4

class StreamType(Enum):
    PI_CCTV = "pi_cctv"
    ESP32_SNAPSHOT = "esp32_snapshot"
    RTSP_STREAM = "rtsp_stream"
    HTTP_MJPEG = "http_mjpeg"
    USB_CAMERA = "usb_camera"
    IP_CAMERA = "ip_camera"
    DRONE_STREAM = "drone_stream"
    MOBILE_STREAM = "mobile_stream"
    VIRTUAL_STREAM = "virtual_stream"

class LoadBalancingStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    RESOURCE_BASED = "resource_based"
    GEOGRAPHIC = "geographic"

@dataclass
class StreamMetrics:
    stream_id: str
    fps: float = 0.0
    bitrate: float = 0.0
    resolution: Tuple[int, int] = (0, 0)
    frames_processed: int = 0
    frames_dropped: int = 0
    latency_ms: float = 0.0
    connection_failures: int = 0
    last_frame_time: float = 0.0
    processing_time_avg: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage: float = 0.0
    gpu_usage: float = 0.0
    network_bandwidth_mbps: float = 0.0
    error_count: int = 0
    uptime_seconds: float = 0.0
    quality_score: float = 0.0

@dataclass
class StreamConfiguration:
    stream_id: str
    stream_type: StreamType
    source_url: str
    enabled: bool = True
    priority: ProcessingPriority = ProcessingPriority.NORMAL
    max_fps: int = 30
    target_resolution: Tuple[int, int] = (1920, 1080)
    encoding_settings: Dict[str, Any] = field(default_factory=dict)
    analytics_enabled: List[str] = field(default_factory=list)
    recording_enabled: bool = True
    motion_detection: bool = True
    audio_enabled: bool = False
    failover_sources: List[str] = field(default_factory=list)
    geo_location: Optional[Tuple[float, float]] = None
    processing_node: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ProcessingNode:
    node_id: str
    hostname: str
    ip_address: str
    port: int
    cpu_cores: int
    memory_gb: float
    gpu_count: int = 0
    current_load: float = 0.0
    active_streams: Set[str] = field(default_factory=set)
    max_streams: int = 10
    last_heartbeat: float = 0.0
    status: str = "active"
    capabilities: List[str] = field(default_factory=list)

class StreamBuffer:
    def __init__(self, max_size: int = 30):
        self.max_size = max_size
        self.buffer = deque(maxlen=max_size)
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
        
    def put(self, frame_data: Dict[str, Any]):
        with self.condition:
            self.buffer.append(frame_data)
            self.condition.notify()
    
    def get(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        with self.condition:
            if not self.buffer:
                self.condition.wait(timeout)
            
            if self.buffer:
                return self.buffer.popleft()
            return None
    
    def clear(self):
        with self.lock:
            self.buffer.clear()
    
    def size(self) -> int:
        with self.lock:
            return len(self.buffer)

class AdvancedStreamProcessor:
    def __init__(self, stream_config: StreamConfiguration, managers: Dict[str, Any]):
        self.config = stream_config
        self.managers = managers
        self.stream_id = stream_config.stream_id
        
        self.status = StreamStatus.INACTIVE
        self.metrics = StreamMetrics(stream_id=self.stream_id)
        self.start_time = time.time()
        
        # Processing infrastructure
        self.frame_buffer = StreamBuffer(max_size=60)
        self.processing_thread = None
        self.capture_thread = None
        self.is_running = False
        
        # Connection management
        self.capture = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5.0
        
        # Frame processing
        self.frame_counter = 0
        self.last_fps_calculation = time.time()
        self.fps_frame_count = 0
        
        # Performance monitoring
        self.processing_times = deque(maxlen=100)
        self.frame_timestamps = deque(maxlen=1000)
        
        # Analytics integration
        self.analytics_results = deque(maxlen=100)
        
    async def start(self):
        """Start the stream processor"""
        if self.is_running:
            return False
        
        logger.info(f"Starting stream processor for {self.stream_id}")
        self.status = StreamStatus.INITIALIZING
        
        try:
            # Initialize video capture
            if not await self._initialize_capture():
                self.status = StreamStatus.ERROR
                return False
            
            self.is_running = True
            self.status = StreamStatus.ACTIVE
            
            # Start processing threads
            self.capture_thread = threading.Thread(
                target=self._capture_loop, 
                name=f"Capture-{self.stream_id}",
                daemon=True
            )
            self.processing_thread = threading.Thread(
                target=self._processing_loop,
                name=f"Process-{self.stream_id}",
                daemon=True
            )
            
            self.capture_thread.start()
            self.processing_thread.start()
            
            logger.info(f"Stream processor {self.stream_id} started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start stream processor {self.stream_id}: {e}")
            self.status = StreamStatus.ERROR
            return False
    
    async def stop(self):
        """Stop the stream processor"""
        if not self.is_running:
            return
        
        logger.info(f"Stopping stream processor for {self.stream_id}")
        self.is_running = False
        self.status = StreamStatus.STOPPED
        
        # Stop threads
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=5.0)
        
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5.0)
        
        # Release capture
        if self.capture:
            self.capture.release()
            self.capture = None
        
        logger.info(f"Stream processor {self.stream_id} stopped")
    
    async def _initialize_capture(self) -> bool:
        """Initialize video capture based on stream type"""
        try:
            if self.config.stream_type == StreamType.RTSP_STREAM:
                self.capture = cv2.VideoCapture(self.config.source_url)
                
            elif self.config.stream_type == StreamType.USB_CAMERA:
                device_id = int(self.config.source_url) if self.config.source_url.isdigit() else 0
                self.capture = cv2.VideoCapture(device_id)
                
            elif self.config.stream_type == StreamType.IP_CAMERA:
                self.capture = cv2.VideoCapture(self.config.source_url)
                
            else:
                # Use legacy stream processors for specific types
                return True
            
            if self.capture and self.capture.isOpened():
                # Configure capture properties
                self._configure_capture_properties()
                return True
            else:
                logger.error(f"Failed to open video capture for {self.stream_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing capture for {self.stream_id}: {e}")
            return False
    
    def _configure_capture_properties(self):
        """Configure video capture properties"""
        if not self.capture:
            return
        
        try:
            # Set buffer size
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Set resolution
            width, height = self.config.target_resolution
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            
            # Set FPS
            self.capture.set(cv2.CAP_PROP_FPS, self.config.max_fps)
            
            # Additional properties based on stream type
            if self.config.stream_type in [StreamType.RTSP_STREAM, StreamType.IP_CAMERA]:
                # Set timeout for network streams
                self.capture.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
                self.capture.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
            
        except Exception as e:
            logger.warning(f"Could not set all capture properties for {self.stream_id}: {e}")
    
    def _capture_loop(self):
        """Main capture loop running in separate thread"""
        logger.info(f"Starting capture loop for {self.stream_id}")
        
        while self.is_running:
            try:
                if not self.capture or not self.capture.isOpened():
                    if not self._reconnect():
                        time.sleep(1.0)
                        continue
                
                ret, frame = self.capture.read()
                
                if not ret or frame is None:
                    logger.warning(f"Failed to read frame from {self.stream_id}")
                    self.metrics.frames_dropped += 1
                    
                    # Attempt reconnection after multiple failures
                    if self.metrics.frames_dropped % 10 == 0:
                        self._reconnect()
                    
                    continue
                
                # Reset failure counters on successful read
                self.reconnect_attempts = 0
                self.metrics.frames_dropped = 0
                
                # Frame preprocessing
                processed_frame = self._preprocess_frame(frame)
                
                # Create frame data package
                frame_data = {
                    'frame': processed_frame,
                    'timestamp': time.time(),
                    'frame_number': self.frame_counter,
                    'stream_id': self.stream_id,
                    'resolution': processed_frame.shape[:2][::-1],
                    'metadata': {
                        'original_resolution': frame.shape[:2][::-1],
                        'processing_time': 0.0
                    }
                }
                
                # Add to buffer
                self.frame_buffer.put(frame_data)
                
                self.frame_counter += 1
                self.metrics.frames_processed += 1
                self.metrics.last_frame_time = time.time()
                
                # Calculate FPS
                self._calculate_fps()
                
                # Rate limiting
                self._apply_rate_limiting()
                
            except Exception as e:
                logger.error(f"Error in capture loop for {self.stream_id}: {e}")
                time.sleep(1.0)
    
    def _processing_loop(self):
        """Main processing loop running in separate thread"""
        logger.info(f"Starting processing loop for {self.stream_id}")
        
        while self.is_running:
            try:
                # Get frame from buffer
                frame_data = self.frame_buffer.get(timeout=1.0)
                
                if frame_data is None:
                    continue
                
                start_time = time.time()
                
                # Process frame through analytics pipeline
                await self._process_frame(frame_data)
                
                processing_time = time.time() - start_time
                self.processing_times.append(processing_time)
                
                # Update metrics
                self.metrics.processing_time_avg = statistics.mean(self.processing_times)
                
            except Exception as e:
                logger.error(f"Error in processing loop for {self.stream_id}: {e}")
                self.metrics.error_count += 1
    
    async def _process_frame(self, frame_data: Dict[str, Any]):
        """Process frame through analytics pipeline"""
        frame = frame_data['frame']
        timestamp = frame_data['timestamp']
        
        try:
            # Video analytics processing
            if 'video_analytics_manager' in self.managers:
                analytics_manager = self.managers['video_analytics_manager']
                
                # Apply enabled analytics
                events, processed_frame = await analytics_manager.process_frame(
                    self.stream_id, frame, frame_number=frame_data['frame_number']
                )
                
                # Store analytics results
                if events:
                    self.analytics_results.extend(events)
                
                frame_data['processed_frame'] = processed_frame
                frame_data['analytics_events'] = events
            
            # AI processing
            if 'ai_manager' in self.managers and self.managers['ai_manager']:
                ai_results = await self.managers['ai_manager'].process_frame(frame, self.stream_id)
                frame_data['ai_results'] = ai_results
            
            # Storage management
            if self.config.recording_enabled and 'storage_manager' in self.managers:
                await self.managers['storage_manager'].store_frame(self.stream_id, frame_data)
            
            # Incident management
            if 'incident_manager' in self.managers and frame_data.get('analytics_events'):
                await self.managers['incident_manager'].process_events(
                    frame_data['analytics_events'], self.stream_id
                )
            
            # Update frame timestamp tracking
            self.frame_timestamps.append(timestamp)
            
        except Exception as e:
            logger.error(f"Error processing frame for {self.stream_id}: {e}")
            self.metrics.error_count += 1
    
    def _preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """Preprocess frame before analytics"""
        try:
            # Resize if needed
            current_height, current_width = frame.shape[:2]
            target_width, target_height = self.config.target_resolution
            
            if (current_width, current_height) != (target_width, target_height):
                frame = cv2.resize(frame, (target_width, target_height))
            
            # Apply any additional preprocessing
            if self.config.encoding_settings.get('denoise', False):
                frame = cv2.fastNlMeansDenoisingColored(frame)
            
            if self.config.encoding_settings.get('enhance_contrast', False):
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                frame[:,:,0] = clahe.apply(frame[:,:,0])
                frame[:,:,1] = clahe.apply(frame[:,:,1])
                frame[:,:,2] = clahe.apply(frame[:,:,2])
            
            return frame
            
        except Exception as e:
            logger.error(f"Error preprocessing frame for {self.stream_id}: {e}")
            return frame
    
    def _calculate_fps(self):
        """Calculate current FPS"""
        self.fps_frame_count += 1
        current_time = time.time()
        
        if current_time - self.last_fps_calculation >= 1.0:
            self.metrics.fps = self.fps_frame_count / (current_time - self.last_fps_calculation)
            self.fps_frame_count = 0
            self.last_fps_calculation = current_time
    
    def _apply_rate_limiting(self):
        """Apply rate limiting based on target FPS"""
        if self.config.max_fps > 0:
            target_interval = 1.0 / self.config.max_fps
            elapsed = time.time() - self.metrics.last_frame_time
            
            if elapsed < target_interval:
                time.sleep(target_interval - elapsed)
    
    def _reconnect(self) -> bool:
        """Attempt to reconnect to stream source"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error(f"Max reconnection attempts reached for {self.stream_id}")
            self.status = StreamStatus.ERROR
            return False
        
        self.reconnect_attempts += 1
        self.status = StreamStatus.RECONNECTING
        
        logger.info(f"Attempting to reconnect {self.stream_id} (attempt {self.reconnect_attempts})")
        
        try:
            # Release current capture
            if self.capture:
                self.capture.release()
                self.capture = None
            
            # Wait before reconnecting
            time.sleep(self.reconnect_delay)
            
            # Reinitialize capture
            if asyncio.run(self._initialize_capture()):
                self.status = StreamStatus.ACTIVE
                logger.info(f"Successfully reconnected {self.stream_id}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Reconnection failed for {self.stream_id}: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive stream status"""
        return {
            'stream_id': self.stream_id,
            'status': self.status.value,
            'uptime': time.time() - self.start_time,
            'metrics': asdict(self.metrics),
            'buffer_size': self.frame_buffer.size(),
            'reconnect_attempts': self.reconnect_attempts,
            'config': asdict(self.config)
        }

class StreamManager:
    def __init__(self, camera_configs, ai_manager, storage_manager, security_manager, 
                 alert_manager, video_analytics_manager, incident_manager, automation_manager, loop):
        self.camera_configs = camera_configs
        self.managers = {
            'ai_manager': ai_manager,
            'storage_manager': storage_manager,
            'security_manager': security_manager,
            'alert_manager': alert_manager,
            'video_analytics_manager': video_analytics_manager,
            'incident_manager': incident_manager,
            'automation_manager': automation_manager
        }
        self.loop = loop
        
        # Stream management
        self.streams = {}
        self.legacy_streams = {}  # For backward compatibility
        self.active_streams = set()
        
        # Load balancing and distribution
        self.processing_nodes = {}
        self.load_balancer_strategy = LoadBalancingStrategy.RESOURCE_BASED
        
        # Performance monitoring
        self.global_metrics = {
            'total_streams': 0,
            'active_streams': 0,
            'total_frames_processed': 0,
            'total_events_generated': 0,
            'average_latency': 0.0,
            'system_load': 0.0
        }
        
        # Thread pool for stream operations
        self.executor = ThreadPoolExecutor(max_workers=min(32, len(camera_configs) * 2))
        
        # Database for stream metadata
        self.db_path = Path("data/stream_manager.db")
        self._setup_database()
        
        # Initialize processing nodes
        self._initialize_processing_nodes()
        
        # Initialize streams
        self._initialize_streams()
        
        # Start monitoring
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.is_monitoring = True
        self.monitor_thread.start()
        
        logger.info(f"Advanced Stream Manager initialized with {len(self.streams)} streams and {len(self.processing_nodes)} processing nodes")
    
    def _setup_database(self):
        """Setup SQLite database for stream metadata"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stream_metrics (
                stream_id TEXT,
                timestamp REAL,
                fps REAL,
                latency_ms REAL,
                frames_processed INTEGER,
                frames_dropped INTEGER,
                error_count INTEGER,
                cpu_usage REAL,
                memory_usage_mb REAL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stream_events (
                event_id TEXT PRIMARY KEY,
                stream_id TEXT,
                timestamp REAL,
                event_type TEXT,
                event_data TEXT,
                processed BOOLEAN DEFAULT FALSE
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _initialize_processing_nodes(self):
        """Initialize processing node registry"""
        # Local processing node
        local_node = ProcessingNode(
            node_id="local",
            hostname=socket.gethostname(),
            ip_address="127.0.0.1",
            port=8080,
            cpu_cores=multiprocessing.cpu_count(),
            memory_gb=psutil.virtual_memory().total / 1024 / 1024 / 1024,
            gpu_count=self._detect_gpu_count(),
            max_streams=min(50, multiprocessing.cpu_count() * 4),
            capabilities=["video_analytics", "ai_processing", "storage", "alerts"]
        )
        
        self.processing_nodes["local"] = local_node
        
        # Discover additional nodes if in cluster mode
        if KUBERNETES_AVAILABLE:
            self._discover_kubernetes_nodes()
    
    def _detect_gpu_count(self) -> int:
        """Detect number of available GPUs"""
        if NVIDIA_ML_AVAILABLE:
            try:
                return nvml.nvmlDeviceGetCount()
            except:
                return 0
        return 0
    
    def _discover_kubernetes_nodes(self):
        """Discover processing nodes in Kubernetes cluster"""
        try:
            k8s_config.load_incluster_config()
            v1 = client.CoreV1Api()
            
            nodes = v1.list_node()
            for node in nodes.items:
                if node.metadata.name != socket.gethostname():
                    # Extract node information
                    node_info = ProcessingNode(
                        node_id=node.metadata.name,
                        hostname=node.metadata.name,
                        ip_address=node.status.addresses[0].address,
                        port=8080,
                        cpu_cores=int(node.status.allocatable.get('cpu', '1')),
                        memory_gb=int(node.status.allocatable.get('memory', '1Gi').rstrip('Gi')),
                        capabilities=["video_analytics", "storage"]
                    )
                    
                    self.processing_nodes[node.metadata.name] = node_info
            
            logger.info(f"Discovered {len(self.processing_nodes) - 1} additional processing nodes")
            
        except Exception as e:
            logger.warning(f"Could not discover Kubernetes nodes: {e}")
    
    def _initialize_streams(self):
        """Initialize all configured streams"""
        for config in self.camera_configs:
            if not config.get('enabled', False):
                continue
            
            cam_id = config['id']
            cam_type = config['type']
            
            try:
                # Create stream configuration
                stream_config = StreamConfiguration(
                    stream_id=cam_id,
                    stream_type=StreamType(cam_type) if cam_type in [t.value for t in StreamType] else StreamType.IP_CAMERA,
                    source_url=config.get('url', config.get('source', '')),
                    enabled=config.get('enabled', True),
                    priority=ProcessingPriority(config.get('priority', 2)),
                    max_fps=config.get('fps', 30),
                    target_resolution=tuple(config.get('resolution', [1920, 1080])),
                    analytics_enabled=config.get('analytics', []),
                    recording_enabled=config.get('recording', True),
                    geo_location=tuple(config.get('location', [])) if config.get('location') else None,
                    metadata=config.get('metadata', {})
                )
                
                # Create appropriate stream processor
                if cam_type in ['pi_cctv', 'esp32_snapshot']:
                    # Use legacy stream processors for backward compatibility
                    self._create_legacy_stream(config, cam_type)
                else:
                    # Use advanced stream processor
                    processor = AdvancedStreamProcessor(stream_config, self.managers)
                    self.streams[cam_id] = processor
                
            except Exception as e:
                logger.error(f"Failed to initialize stream {cam_id}: {e}")
    
    def _create_legacy_stream(self, config: Dict[str, Any], cam_type: str):
        """Create legacy stream processor for backward compatibility"""
        cam_id = config['id']
        
        common_args = (
            config, 
            self.managers['ai_manager'],
            self.managers['storage_manager'],
            self.managers['security_manager'],
            self.managers['alert_manager'],
            self.managers['video_analytics_manager'],
            self.managers['incident_manager'],
            self.managers['automation_manager'],
            self.loop
        )
        
        try:
            if cam_type == 'pi_cctv':
                self.legacy_streams[cam_id] = PiCCTVStream(*common_args)
            elif cam_type == 'esp32_snapshot':
                # Handle ESP32 with backward compatibility
                import inspect
                sig = inspect.signature(ESP32SnapshotStream.__init__)
                if 'video_analytics_manager' in sig.parameters:
                    self.legacy_streams[cam_id] = ESP32SnapshotStream(*common_args)
                else:
                    # Legacy constructor
                    legacy_args = (
                        config,
                        self.managers['ai_manager'],
                        self.managers['storage_manager'],
                        self.managers['security_manager'],
                        self.loop
                    )
                    self.legacy_streams[cam_id] = ESP32SnapshotStream(*legacy_args)
                    
        except Exception as e:
            logger.error(f"Failed to create legacy stream {cam_id}: {e}")
    
    async def start_all_streams(self):
        """Start all configured streams with intelligent load balancing"""
        if not self.streams and not self.legacy_streams:
            logger.warning("No streams configured to start")
            return
        
        logger.info("Starting all camera streams with load balancing...")
        
        # Start legacy streams
        for cam_id, stream in self.legacy_streams.items():
            try:
                task = asyncio.create_task(stream.start_processing())
                self.active_streams.add(cam_id)
                logger.info(f"Legacy stream '{cam_id}' started")
            except Exception as e:
                logger.error(f"Failed to start legacy stream {cam_id}: {e}")
        
        # Start advanced streams with load balancing
        for cam_id, processor in self.streams.items():
            try:
                # Select optimal processing node
                node = self._select_processing_node(processor.config)
                if node:
                    processor.config.processing_node = node.node_id
                    node.active_streams.add(cam_id)
                
                # Start the processor
                success = await processor.start()
                if success:
                    self.active_streams.add(cam_id)
                    logger.info(f"Stream '{cam_id}' started on node '{node.node_id if node else 'local'}'")
                else:
                    logger.error(f"Failed to start stream '{cam_id}'")
                    
            except Exception as e:
                logger.error(f"Error starting stream {cam_id}: {e}")
        
        logger.info(f"Stream startup completed. Active streams: {len(self.active_streams)}")
    
    def _select_processing_node(self, stream_config: StreamConfiguration) -> Optional[ProcessingNode]:
        """Select optimal processing node based on load balancing strategy"""
        available_nodes = [node for node in self.processing_nodes.values() 
                          if len(node.active_streams) < node.max_streams and node.status == "active"]
        
        if not available_nodes:
            logger.warning("No available processing nodes")
            return None
        
        if self.load_balancer_strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return min(available_nodes, key=lambda n: len(n.active_streams))
        
        elif self.load_balancer_strategy == LoadBalancingStrategy.RESOURCE_BASED:
            # Select node with best resource availability
            return min(available_nodes, key=lambda n: n.current_load)
        
        elif self.load_balancer_strategy == LoadBalancingStrategy.GEOGRAPHIC:
            # Select closest node based on geographic location
            if stream_config.geo_location:
                # Simplified geographic selection (would need actual geo calculation)
                return available_nodes[0]
        
        # Default to least connections
        return min(available_nodes, key=lambda n: len(n.active_streams))
    
    def stop_all_streams(self):
        """Stop all running streams"""
        logger.info("Stopping all camera streams...")
        
        self.is_monitoring = False
        
        # Stop advanced streams
        for cam_id, processor in self.streams.items():
            try:
                asyncio.create_task(processor.stop())
            except Exception as e:
                logger.error(f"Error stopping stream {cam_id}: {e}")
        
        # Stop legacy streams
        for cam_id, stream in self.legacy_streams.items():
            try:
                stream.stop()
            except Exception as e:
                logger.error(f"Error stopping legacy stream {cam_id}: {e}")
        
        # Clear active streams
        self.active_streams.clear()
        
        # Clear node assignments
        for node in self.processing_nodes.values():
            node.active_streams.clear()
        
        # Shutdown executor
        self.executor.shutdown(wait=True, timeout=30)
        
        logger.info("All streams stopped")
    
    def _monitoring_loop(self):
        """Monitor stream health and performance"""
        logger.info("Starting stream monitoring loop")
        
        while self.is_monitoring:
            try:
                # Update global metrics
                self._update_global_metrics()
                
                # Monitor individual streams
                self._monitor_stream_health()
                
                # Update processing node metrics
                self._update_node_metrics()
                
                # Store metrics in database
                self._store_metrics()
                
                time.sleep(10)  # Monitor every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)
    
    def _update_global_metrics(self):
        """Update global system metrics"""
        self.global_metrics['total_streams'] = len(self.streams) + len(self.legacy_streams)
        self.global_metrics['active_streams'] = len(self.active_streams)
        
        total_frames = sum(s.metrics.frames_processed for s in self.streams.values())
        self.global_metrics['total_frames_processed'] = total_frames
        
        # Calculate system load
        cpu_percent = psutil.cpu_percent()
        memory_percent = psutil.virtual_memory().percent
        self.global_metrics['system_load'] = (cpu_percent + memory_percent) / 2
    
    def _monitor_stream_health(self):
        """Monitor health of individual streams"""
        current_time = time.time()
        
        for cam_id, processor in self.streams.items():
            try:
                # Check if stream is responsive
                if processor.status == StreamStatus.ACTIVE:
                    last_frame_age = current_time - processor.metrics.last_frame_time
                    
                    if last_frame_age > 30:  # No frame for 30 seconds
                        logger.warning(f"Stream {cam_id} appears unresponsive")
                        processor.status = StreamStatus.ERROR
                        
                        # Attempt restart
                        asyncio.create_task(self._restart_stream(cam_id))
                
                # Update stream uptime
                processor.metrics.uptime_seconds = current_time - processor.start_time
                
            except Exception as e:
                logger.error(f"Error monitoring stream {cam_id}: {e}")
    
    def _update_node_metrics(self):
        """Update processing node performance metrics"""
        for node in self.processing_nodes.values():
            try:
                if node.node_id == "local":
                    # Update local node metrics
                    node.current_load = psutil.cpu_percent()
                    node.last_heartbeat = time.time()
                else:
                    # For remote nodes, would need to query their health endpoints
                    pass
                    
            except Exception as e:
                logger.error(f"Error updating node metrics for {node.node_id}: {e}")
    
    def _store_metrics(self):
        """Store performance metrics to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            current_time = time.time()
            
            for cam_id, processor in self.streams.items():
                metrics = processor.metrics
                
                cursor.execute("""
                    INSERT INTO stream_metrics 
                    (stream_id, timestamp, fps, latency_ms, frames_processed, frames_dropped, 
                     error_count, cpu_usage, memory_usage_mb)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cam_id, current_time, metrics.fps, metrics.latency_ms,
                    metrics.frames_processed, metrics.frames_dropped, metrics.error_count,
                    metrics.cpu_usage, metrics.memory_usage_mb
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing metrics: {e}")
    
    async def _restart_stream(self, stream_id: str):
        """Restart a failed stream"""
        logger.info(f"Attempting to restart stream {stream_id}")
        
        try:
            if stream_id in self.streams:
                processor = self.streams[stream_id]
                
                # Stop current processor
                await processor.stop()
                
                # Wait before restart
                await asyncio.sleep(5)
                
                # Start processor again
                success = await processor.start()
                
                if success:
                    logger.info(f"Stream {stream_id} restarted successfully")
                else:
                    logger.error(f"Failed to restart stream {stream_id}")
                    
            elif stream_id in self.legacy_streams:
                # Handle legacy stream restart
                stream = self.legacy_streams[stream_id]
                stream.stop()
                
                await asyncio.sleep(5)
                
                asyncio.create_task(stream.start_processing())
                logger.info(f"Legacy stream {stream_id} restart attempted")
                
        except Exception as e:
            logger.error(f"Error restarting stream {stream_id}: {e}")
    
    def set_managers(self, incident_manager, automation_manager):
        """Update manager references after initialization"""
        self.managers['incident_manager'] = incident_manager
        self.managers['automation_manager'] = automation_manager
    
    def get_stream_by_id(self, camera_id: str):
        """Get stream processor by ID"""
        if camera_id in self.streams:
            return self.streams[camera_id]
        elif camera_id in self.legacy_streams:
            return self.legacy_streams[camera_id]
        return None
    
    def get_all_streams_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all streams"""
        status = {
            'global_metrics': self.global_metrics,
            'processing_nodes': {
                node_id: {
                    'hostname': node.hostname,
                    'active_streams': len(node.active_streams),
                    'max_streams': node.max_streams,
                    'load': node.current_load,
                    'status': node.status
                }
                for node_id, node in self.processing_nodes.items()
            },
            'streams': {}
        }
        
        # Advanced stream status
        for cam_id, processor in self.streams.items():
            status['streams'][cam_id] = processor.get_status()
        
        # Legacy stream status
        for cam_id, stream in self.legacy_streams.items():
            try:
                status['streams'][cam_id] = stream.get_status()
            except:
                status['streams'][cam_id] = {
                    'stream_id': cam_id,
                    'status': 'unknown',
                    'type': 'legacy'
                }
        
        return status
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary across all streams"""
        total_fps = sum(s.metrics.fps for s in self.streams.values())
        total_latency = sum(s.metrics.latency_ms for s in self.streams.values())
        active_count = len(self.active_streams)
        
        return {
            'total_streams': len(self.streams) + len(self.legacy_streams),
            'active_streams': active_count,
            'total_fps': total_fps,
            'average_latency': total_latency / max(active_count, 1),
            'system_load': self.global_metrics['system_load'],
            'processing_nodes': len(self.processing_nodes),
            'frames_processed_total': self.global_metrics['total_frames_processed']
        }

logger.info("Advanced Enterprise Stream Processing Management System loaded successfully")
