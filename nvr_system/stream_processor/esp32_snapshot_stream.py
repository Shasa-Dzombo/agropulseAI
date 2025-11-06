# Enterprise ESP32/IoT Camera Stream Processing System
# Advanced snapshot and IoT device management with edge computing, fleet management, and intelligent synchronization
# Supports ESP32-CAM, ESP32-S3, ESP-EYE, and custom IoT camera implementations with OTA updates

import logging
import cv2
import numpy as np
import asyncio
import aiohttp
import time
import json
import hashlib
import sqlite3
import threading
import queue
import ssl
import certifi
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set, Union, Callable
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
from enum import Enum
import struct
import socket
import base64
import zlib
import pickle
import uuid
import re
import hmac

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

try:
    import pyzbar.pyzbar as pyzbar
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont, ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

logger = logging.getLogger(__name__)

class DeviceStatus(Enum):
    INITIALIZING = "initializing"
    ONLINE = "online"
    OFFLINE = "offline"
    SLEEPING = "sleeping"
    LOW_BATTERY = "low_battery"
    UPDATING = "updating"
    ERROR = "error"
    MAINTENANCE = "maintenance"

class SnapshotQuality(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"

class DeviceMode(Enum):
    CONTINUOUS = "continuous"
    MOTION_TRIGGERED = "motion_triggered"
    SCHEDULED = "scheduled"
    EVENT_DRIVEN = "event_driven"
    POWER_SAVE = "power_save"

class EdgeProcessingMode(Enum):
    NONE = "none"
    BASIC = "basic"
    ADVANCED = "advanced"
    FULL_AI = "full_ai"

@dataclass
class DeviceCapabilities:
    resolution_max: Tuple[int, int] = (1600, 1200)
    resolution_min: Tuple[int, int] = (320, 240)
    formats_supported: List[str] = field(default_factory=lambda: ["jpeg", "png", "bmp"])
    has_flash: bool = False
    has_pir_sensor: bool = False
    has_audio: bool = False
    has_accelerometer: bool = False
    has_temperature_sensor: bool = False
    has_humidity_sensor: bool = False
    has_light_sensor: bool = False
    storage_available: bool = False
    edge_ai_capable: bool = False
    wifi_rssi_monitoring: bool = True
    battery_monitoring: bool = False
    ota_update_capable: bool = True

@dataclass
class DeviceMetrics:
    device_id: str
    uptime_seconds: float = 0.0
    snapshots_captured: int = 0
    snapshots_failed: int = 0
    bytes_transferred: int = 0
    average_capture_time: float = 0.0
    average_transfer_time: float = 0.0
    wifi_rssi: int = 0
    battery_level: float = 100.0
    temperature_celsius: float = 0.0
    free_memory_kb: int = 0
    cpu_frequency_mhz: int = 0
    error_count: int = 0
    last_seen: float = 0.0
    firmware_version: str = "unknown"

@dataclass
class SnapshotRequest:
    request_id: str
    device_id: str
    timestamp: float
    quality: SnapshotQuality
    resolution: Tuple[int, int]
    enable_flash: bool = False
    apply_filters: List[str] = field(default_factory=list)
    edge_processing: EdgeProcessingMode = EdgeProcessingMode.NONE
    priority: int = 5
    timeout_seconds: int = 30
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SnapshotResult:
    request_id: str
    device_id: str
    timestamp: float
    success: bool
    image_data: Optional[bytes] = None
    image_hash: Optional[str] = None
    resolution: Optional[Tuple[int, int]] = None
    file_size_bytes: int = 0
    capture_time_ms: float = 0.0
    transfer_time_ms: float = 0.0
    edge_detections: List[Dict[str, Any]] = field(default_factory=list)
    device_metrics: Optional[DeviceMetrics] = None
    error_message: Optional[str] = None

class ESP32DeviceManager:
    """Manages individual ESP32 device communication and state"""
    
    def __init__(self, device_config: Dict[str, Any]):
        self.device_id = device_config['id']
        self.config = device_config
        
        # Connection settings
        self.base_url = device_config.get('source', device_config.get('url'))
        self.auth_token = device_config.get('auth_token')
        self.use_https = device_config.get('use_https', False)
        
        # Device state
        self.status = DeviceStatus.INITIALIZING
        self.capabilities = self._parse_capabilities(device_config.get('capabilities', {}))
        self.metrics = DeviceMetrics(device_id=self.device_id)
        
        # Communication
        self.session = None
        self.mqtt_client = None
        self.last_heartbeat = 0.0
        self.connection_timeout = device_config.get('timeout', 30)
        
        # Request management
        self.pending_requests = {}
        self.request_queue = queue.PriorityQueue()
        
        # Caching and optimization
        self.image_cache = deque(maxlen=10)
        self.compression_level = device_config.get('compression_level', 85)
        
        # Security
        self.encryption_key = device_config.get('encryption_key')
        self.verify_ssl = device_config.get('verify_ssl', True)
        
        # Performance tracking
        self.capture_times = deque(maxlen=100)
        self.transfer_times = deque(maxlen=100)
        
    def _parse_capabilities(self, cap_config: Dict[str, Any]) -> DeviceCapabilities:
        """Parse device capabilities from configuration"""
        return DeviceCapabilities(
            resolution_max=tuple(cap_config.get('max_resolution', [1600, 1200])),
            resolution_min=tuple(cap_config.get('min_resolution', [320, 240])),
            formats_supported=cap_config.get('formats', ["jpeg"]),
            has_flash=cap_config.get('flash', False),
            has_pir_sensor=cap_config.get('pir', False),
            has_audio=cap_config.get('audio', False),
            has_accelerometer=cap_config.get('accelerometer', False),
            has_temperature_sensor=cap_config.get('temperature', False),
            has_humidity_sensor=cap_config.get('humidity', False),
            has_light_sensor=cap_config.get('light_sensor', False),
            storage_available=cap_config.get('storage', False),
            edge_ai_capable=cap_config.get('edge_ai', False),
            wifi_rssi_monitoring=cap_config.get('wifi_monitoring', True),
            battery_monitoring=cap_config.get('battery', False),
            ota_update_capable=cap_config.get('ota', True)
        )
    
    async def initialize(self) -> bool:
        """Initialize device connection and verify capabilities"""
        try:
            # Create HTTP session with appropriate settings
            connector = aiohttp.TCPConnector(
                ssl=ssl.create_default_context(cafile=certifi.where()) if self.verify_ssl else False,
                limit=10,
                ttl_dns_cache=300
            )
            
            timeout = aiohttp.ClientTimeout(total=self.connection_timeout)
            
            headers = {}
            if self.auth_token:
                headers['Authorization'] = f'Bearer {self.auth_token}'
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=headers
            )
            
            # Verify device connectivity
            if await self._ping_device():
                # Query device capabilities
                await self._query_device_info()
                
                # Initialize MQTT if available
                if MQTT_AVAILABLE and self.config.get('mqtt_enabled', False):
                    await self._initialize_mqtt()
                
                self.status = DeviceStatus.ONLINE
                logger.info(f"ESP32 device {self.device_id} initialized successfully")
                return True
            else:
                self.status = DeviceStatus.OFFLINE
                logger.error(f"Failed to ping ESP32 device {self.device_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize ESP32 device {self.device_id}: {e}")
            self.status = DeviceStatus.ERROR
            return False
    
    async def _ping_device(self) -> bool:
        """Ping device to verify connectivity"""
        try:
            ping_url = f"{self.base_url}/ping"
            async with self.session.get(ping_url) as response:
                if response.status == 200:
                    self.last_heartbeat = time.time()
                    return True
                return False
        except:
            return False
    
    async def _query_device_info(self):
        """Query detailed device information"""
        try:
            info_url = f"{self.base_url}/info"
            async with self.session.get(info_url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Update metrics
                    self.metrics.firmware_version = data.get('firmware', 'unknown')
                    self.metrics.free_memory_kb = data.get('free_memory', 0)
                    self.metrics.cpu_frequency_mhz = data.get('cpu_freq', 0)
                    self.metrics.uptime_seconds = data.get('uptime', 0)
                    
                    if 'wifi_rssi' in data:
                        self.metrics.wifi_rssi = data['wifi_rssi']
                    
                    if 'battery' in data:
                        self.metrics.battery_level = data['battery']
                        if self.metrics.battery_level < 20:
                            self.status = DeviceStatus.LOW_BATTERY
                    
                    if 'temperature' in data:
                        self.metrics.temperature_celsius = data['temperature']
                    
                    logger.info(f"Device {self.device_id} info: FW {self.metrics.firmware_version}, "
                              f"RSSI {self.metrics.wifi_rssi}dBm, Memory {self.metrics.free_memory_kb}KB")
                    
        except Exception as e:
            logger.warning(f"Could not query device info for {self.device_id}: {e}")
    
    async def _initialize_mqtt(self):
        """Initialize MQTT connection for real-time communication"""
        try:
            mqtt_config = self.config.get('mqtt', {})
            
            self.mqtt_client = mqtt.Client(client_id=f"nvr_{self.device_id}")
            
            # Set callbacks
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_message = self._on_mqtt_message
            self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
            
            # Authentication
            if mqtt_config.get('username'):
                self.mqtt_client.username_pw_set(
                    mqtt_config['username'],
                    mqtt_config.get('password')
                )
            
            # TLS
            if mqtt_config.get('use_tls', False):
                self.mqtt_client.tls_set()
            
            # Connect
            broker = mqtt_config.get('broker', 'localhost')
            port = mqtt_config.get('port', 1883)
            
            self.mqtt_client.connect_async(broker, port, keepalive=60)
            self.mqtt_client.loop_start()
            
            logger.info(f"MQTT initialized for device {self.device_id}")
            
        except Exception as e:
            logger.warning(f"Failed to initialize MQTT for {self.device_id}: {e}")
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            # Subscribe to device topics
            client.subscribe(f"esp32/{self.device_id}/status")
            client.subscribe(f"esp32/{self.device_id}/snapshot")
            client.subscribe(f"esp32/{self.device_id}/alert")
            logger.info(f"MQTT connected for device {self.device_id}")
        else:
            logger.error(f"MQTT connection failed for {self.device_id}: {rc}")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """MQTT message callback"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            if 'status' in topic:
                self._handle_status_update(payload)
            elif 'snapshot' in topic:
                self._handle_mqtt_snapshot(payload)
            elif 'alert' in topic:
                self._handle_device_alert(payload)
                
        except Exception as e:
            logger.error(f"Error processing MQTT message for {self.device_id}: {e}")
    
    def _on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        logger.warning(f"MQTT disconnected for device {self.device_id}: {rc}")
    
    def _handle_status_update(self, payload: Dict[str, Any]):
        """Handle device status update via MQTT"""
        if 'battery' in payload:
            self.metrics.battery_level = payload['battery']
        if 'rssi' in payload:
            self.metrics.wifi_rssi = payload['rssi']
        if 'temperature' in payload:
            self.metrics.temperature_celsius = payload['temperature']
        
        self.last_heartbeat = time.time()
        self.metrics.last_seen = self.last_heartbeat
    
    def _handle_mqtt_snapshot(self, payload: Dict[str, Any]):
        """Handle snapshot data received via MQTT"""
        # Process MQTT-delivered snapshot
        logger.debug(f"Received MQTT snapshot from {self.device_id}")
    
    def _handle_device_alert(self, payload: Dict[str, Any]):
        """Handle device alert via MQTT"""
        alert_type = payload.get('type', 'unknown')
        logger.warning(f"Device {self.device_id} alert: {alert_type} - {payload.get('message')}")
    
    async def capture_snapshot(self, request: SnapshotRequest) -> SnapshotResult:
        """Capture snapshot from device"""
        start_time = time.time()
        
        try:
            # Build request URL with parameters
            params = {
                'quality': request.quality.value,
                'width': request.resolution[0],
                'height': request.resolution[1]
            }
            
            if request.enable_flash and self.capabilities.has_flash:
                params['flash'] = 1
            
            capture_url = f"{self.base_url}/capture"
            
            # Make request
            capture_start = time.time()
            async with self.session.get(capture_url, params=params, timeout=aiohttp.ClientTimeout(total=request.timeout_seconds)) as response:
                if response.status == 200:
                    image_data = await response.read()
                    capture_time = (time.time() - capture_start) * 1000
                    
                    # Calculate hash
                    image_hash = hashlib.sha256(image_data).hexdigest()
                    
                    # Decode to verify
                    np_arr = np.frombuffer(image_data, np.uint8)
                    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                    
                    if frame is None:
                        raise ValueError("Failed to decode image")
                    
                    # Update metrics
                    self.metrics.snapshots_captured += 1
                    self.metrics.bytes_transferred += len(image_data)
                    self.capture_times.append(capture_time)
                    
                    if self.capture_times:
                        self.metrics.average_capture_time = statistics.mean(self.capture_times)
                    
                    # Create result
                    result = SnapshotResult(
                        request_id=request.request_id,
                        device_id=self.device_id,
                        timestamp=time.time(),
                        success=True,
                        image_data=image_data,
                        image_hash=image_hash,
                        resolution=frame.shape[:2][::-1],
                        file_size_bytes=len(image_data),
                        capture_time_ms=capture_time,
                        transfer_time_ms=(time.time() - start_time) * 1000,
                        device_metrics=self.metrics
                    )
                    
                    # Cache the snapshot
                    self.image_cache.append({
                        'timestamp': time.time(),
                        'image_data': image_data,
                        'hash': image_hash
                    })
                    
                    self.last_heartbeat = time.time()
                    self.status = DeviceStatus.ONLINE
                    
                    return result
                    
                else:
                    self.metrics.snapshots_failed += 1
                    return SnapshotResult(
                        request_id=request.request_id,
                        device_id=self.device_id,
                        timestamp=time.time(),
                        success=False,
                        error_message=f"HTTP {response.status}"
                    )
                    
        except asyncio.TimeoutError:
            self.metrics.snapshots_failed += 1
            self.metrics.error_count += 1
            return SnapshotResult(
                request_id=request.request_id,
                device_id=self.device_id,
                timestamp=time.time(),
                success=False,
                error_message="Timeout"
            )
            
        except Exception as e:
            self.metrics.snapshots_failed += 1
            self.metrics.error_count += 1
            logger.error(f"Snapshot capture failed for {self.device_id}: {e}")
            return SnapshotResult(
                request_id=request.request_id,
                device_id=self.device_id,
                timestamp=time.time(),
                success=False,
                error_message=str(e)
            )
    
    async def configure_device(self, settings: Dict[str, Any]) -> bool:
        """Send configuration to device"""
        try:
            config_url = f"{self.base_url}/config"
            async with self.session.post(config_url, json=settings) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Failed to configure device {self.device_id}: {e}")
            return False
    
    async def trigger_ota_update(self, firmware_url: str) -> bool:
        """Trigger OTA firmware update"""
        if not self.capabilities.ota_update_capable:
            logger.warning(f"Device {self.device_id} does not support OTA updates")
            return False
        
        try:
            self.status = DeviceStatus.UPDATING
            
            ota_url = f"{self.base_url}/ota"
            payload = {'firmware_url': firmware_url}
            
            async with self.session.post(ota_url, json=payload) as response:
                if response.status == 200:
                    logger.info(f"OTA update initiated for device {self.device_id}")
                    return True
                return False
                
        except Exception as e:
            logger.error(f"OTA update failed for {self.device_id}: {e}")
            self.status = DeviceStatus.ERROR
            return False
    
    async def set_power_mode(self, mode: DeviceMode) -> bool:
        """Set device power/operation mode"""
        try:
            mode_url = f"{self.base_url}/mode"
            payload = {'mode': mode.value}
            
            async with self.session.post(mode_url, json=payload) as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"Failed to set power mode for {self.device_id}: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup device resources"""
        if self.session:
            await self.session.close()
        
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

class FleetManager:
    """Manages fleet of ESP32 devices"""
    
    def __init__(self):
        self.devices: Dict[str, ESP32DeviceManager] = {}
        self.device_groups: Dict[str, Set[str]] = defaultdict(set)
        self.scheduler_queue = queue.PriorityQueue()
        self.is_running = False
        
        # Performance tracking
        self.fleet_metrics = {
            'total_devices': 0,
            'online_devices': 0,
            'total_snapshots': 0,
            'failed_snapshots': 0,
            'total_bytes_transferred': 0,
            'average_response_time': 0.0
        }
        
        # Database for fleet data
        self.db_path = Path("data/esp32_fleet.db")
        self._setup_database()
    
    def _setup_database(self):
        """Setup fleet management database"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_registry (
                device_id TEXT PRIMARY KEY,
                device_type TEXT,
                firmware_version TEXT,
                capabilities TEXT,
                first_seen REAL,
                last_seen REAL,
                status TEXT,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS snapshot_log (
                snapshot_id TEXT PRIMARY KEY,
                device_id TEXT,
                timestamp REAL,
                success BOOLEAN,
                file_size INTEGER,
                capture_time_ms REAL,
                image_hash TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_metrics_history (
                device_id TEXT,
                timestamp REAL,
                uptime REAL,
                wifi_rssi INTEGER,
                battery_level REAL,
                temperature REAL,
                free_memory INTEGER,
                snapshots_captured INTEGER,
                error_count INTEGER
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def register_device(self, device_config: Dict[str, Any]) -> bool:
        """Register new device in fleet"""
        device_id = device_config['id']
        
        try:
            device_manager = ESP32DeviceManager(device_config)
            
            if await device_manager.initialize():
                self.devices[device_id] = device_manager
                
                # Add to groups
                for group in device_config.get('groups', []):
                    self.device_groups[group].add(device_id)
                
                # Store in database
                await self._store_device_registration(device_manager)
                
                self.fleet_metrics['total_devices'] = len(self.devices)
                self._update_online_count()
                
                logger.info(f"Device {device_id} registered successfully")
                return True
            else:
                logger.error(f"Failed to initialize device {device_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to register device {device_id}: {e}")
            return False
    
    async def _store_device_registration(self, device: ESP32DeviceManager):
        """Store device registration in database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO device_registry
                (device_id, device_type, firmware_version, capabilities, first_seen, last_seen, status, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                device.device_id,
                'ESP32-CAM',
                device.metrics.firmware_version,
                json.dumps(asdict(device.capabilities)),
                time.time(),
                time.time(),
                device.status.value,
                json.dumps(device.config.get('metadata', {}))
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store device registration: {e}")
    
    def _update_online_count(self):
        """Update count of online devices"""
        online = sum(1 for d in self.devices.values() if d.status == DeviceStatus.ONLINE)
        self.fleet_metrics['online_devices'] = online
    
    async def capture_from_device(self, device_id: str, quality: SnapshotQuality = SnapshotQuality.HIGH,
                                  resolution: Tuple[int, int] = (1600, 1200)) -> Optional[SnapshotResult]:
        """Capture snapshot from specific device"""
        if device_id not in self.devices:
            logger.error(f"Device {device_id} not found in fleet")
            return None
        
        device = self.devices[device_id]
        
        request = SnapshotRequest(
            request_id=str(uuid.uuid4()),
            device_id=device_id,
            timestamp=time.time(),
            quality=quality,
            resolution=resolution
        )
        
        result = await device.capture_snapshot(request)
        
        # Log result
        await self._log_snapshot(result)
        
        # Update fleet metrics
        if result.success:
            self.fleet_metrics['total_snapshots'] += 1
            self.fleet_metrics['total_bytes_transferred'] += result.file_size_bytes
        else:
            self.fleet_metrics['failed_snapshots'] += 1
        
        return result
    
    async def _log_snapshot(self, result: SnapshotResult):
        """Log snapshot to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO snapshot_log
                (snapshot_id, device_id, timestamp, success, file_size, capture_time_ms, image_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                result.request_id,
                result.device_id,
                result.timestamp,
                result.success,
                result.file_size_bytes,
                result.capture_time_ms,
                result.image_hash
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to log snapshot: {e}")
    
    async def capture_from_group(self, group_name: str) -> List[SnapshotResult]:
        """Capture snapshots from all devices in a group"""
        if group_name not in self.device_groups:
            logger.error(f"Device group {group_name} not found")
            return []
        
        tasks = []
        for device_id in self.device_groups[group_name]:
            tasks.append(self.capture_from_device(device_id))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [r for r in results if isinstance(r, SnapshotResult)]
    
    async def broadcast_configuration(self, settings: Dict[str, Any], device_ids: Optional[List[str]] = None):
        """Broadcast configuration to multiple devices"""
        target_devices = device_ids if device_ids else list(self.devices.keys())
        
        tasks = []
        for device_id in target_devices:
            if device_id in self.devices:
                tasks.append(self.devices[device_id].configure_device(settings))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if r is True)
        logger.info(f"Configuration broadcast: {success_count}/{len(target_devices)} devices configured")
    
    async def fleet_health_check(self):
        """Perform health check on all devices"""
        logger.info("Performing fleet health check...")
        
        for device_id, device in self.devices.items():
            try:
                if await device._ping_device():
                    await device._query_device_info()
                    
                    # Store metrics
                    await self._store_device_metrics(device)
                else:
                    if device.status != DeviceStatus.OFFLINE:
                        device.status = DeviceStatus.OFFLINE
                        logger.warning(f"Device {device_id} is offline")
                        
            except Exception as e:
                logger.error(f"Health check failed for {device_id}: {e}")
        
        self._update_online_count()
    
    async def _store_device_metrics(self, device: ESP32DeviceManager):
        """Store device metrics to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            metrics = device.metrics
            
            cursor.execute("""
                INSERT INTO device_metrics_history
                (device_id, timestamp, uptime, wifi_rssi, battery_level, temperature,
                 free_memory, snapshots_captured, error_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                device.device_id,
                time.time(),
                metrics.uptime_seconds,
                metrics.wifi_rssi,
                metrics.battery_level,
                metrics.temperature_celsius,
                metrics.free_memory_kb,
                metrics.snapshots_captured,
                metrics.error_count
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store device metrics: {e}")
    
    def get_fleet_status(self) -> Dict[str, Any]:
        """Get comprehensive fleet status"""
        device_statuses = {}
        
        for device_id, device in self.devices.items():
            device_statuses[device_id] = {
                'status': device.status.value,
                'metrics': asdict(device.metrics),
                'capabilities': asdict(device.capabilities),
                'last_seen': device.last_heartbeat
            }
        
        return {
            'fleet_metrics': self.fleet_metrics,
            'device_count': len(self.devices),
            'groups': {name: len(devices) for name, devices in self.device_groups.items()},
            'devices': device_statuses
        }
    
    async def cleanup(self):
        """Cleanup all fleet resources"""
        logger.info("Cleaning up ESP32 fleet...")
        
        for device in self.devices.values():
            await device.cleanup()
        
        self.devices.clear()
        self.device_groups.clear()

class ESP32SnapshotStream:
    """Legacy-compatible ESP32 snapshot stream processor with advanced features"""
    
    def __init__(self, config, ai_manager, storage_manager, security_manager, loop,
                 alert_manager=None, video_analytics_manager=None, incident_manager=None,
                 automation_manager=None):
        self.config = config
        self.ai_manager = ai_manager
        self.storage_manager = storage_manager
        self.security_manager = security_manager
        self.alert_manager = alert_manager
        self.video_analytics_manager = video_analytics_manager
        self.incident_manager = incident_manager
        self.automation_manager = automation_manager
        self.loop = loop
        
        self.id = config['id']
        self.source = config.get('source', config.get('url'))
        self.interval = config.get('snapshot_interval_seconds', config.get('interval', 30))
        self.is_running = False
        self.last_snapshot_time = 0
        
        # Advanced features
        self.fleet_manager = FleetManager()
        self.device_manager = None
        
        # Processing
        self.latest_processed_frame = None
        self.snapshot_history = deque(maxlen=100)
        self.analytics_results = deque(maxlen=100)
        
        # Status
        self.status = "Initialized"
        self.error_count = 0
        self.successful_snapshots = 0
        
        # Image processing
        self.enable_preprocessing = config.get('enable_preprocessing', True)
        self.enable_edge_detection = config.get('enable_edge_detection', False)
        
    async def start_processing(self):
        """Main loop to fetch and process snapshots at intervals with advanced fleet management"""
        self.is_running = True
        self.status = "Running"
        
        # Initialize device manager
        try:
            await self.fleet_manager.register_device(self.config)
            self.device_manager = self.fleet_manager.devices.get(self.id)
        except Exception as e:
            logger.error(f"Failed to initialize fleet management for {self.id}: {e}")
        
        logger.info(f"[{self.id}] Starting advanced snapshot processing from {self.source} every {self.interval}s.")
        
        # Start health monitoring thread
        health_thread = threading.Thread(target=self._health_monitoring_loop, daemon=True)
        health_thread.start()
        
        while self.is_running:
            try:
                # Capture snapshot using fleet manager if available
                if self.device_manager:
                    result = await self.fleet_manager.capture_from_device(
                        self.id,
                        quality=SnapshotQuality.HIGH,
                        resolution=(1600, 1200)
                    )
                    
                    if result and result.success:
                        await self._process_snapshot_result(result)
                    else:
                        logger.warning(f"[{self.id}] Snapshot capture failed: {result.error_message if result else 'Unknown error'}")
                        self.error_count += 1
                        self.status = f"Error: {result.error_message if result else 'Unknown'}"
                else:
                    # Fallback to legacy HTTP capture
                    await self._legacy_snapshot_capture()
                
            except Exception as e:
                logger.error(f"[{self.id}] Error in snapshot processing: {e}", exc_info=True)
                self.error_count += 1
                self.status = "Error: Processing failed"
            
            await asyncio.sleep(self.interval)
        
        # Cleanup
        await self.fleet_manager.cleanup()
        
        logger.info(f"[{self.id}] Snapshot processing stopped.")
        self.status = "Stopped"
    
    async def _legacy_snapshot_capture(self):
        """Legacy HTTP snapshot capture method"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.source) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        
                        # Decode image
                        frame = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)
                        self.last_snapshot_time = time.time()
                        
                        if frame is not None:
                            await self._process_frame(frame, image_data)
                            self.successful_snapshots += 1
                        else:
                            logger.error(f"[{self.id}] Failed to decode image")
                            self.error_count += 1
                    else:
                        logger.warning(f"[{self.id}] Failed to fetch snapshot. Status: {response.status}")
                        self.status = f"Error: HTTP {response.status}"
                        self.error_count += 1
                        
        except Exception as e:
            logger.error(f"[{self.id}] Legacy capture error: {e}")
            self.error_count += 1
            self.status = "Error: Connection failed"
    
    async def _process_snapshot_result(self, result: SnapshotResult):
        """Process snapshot result from fleet manager"""
        # Decode image
        frame = cv2.imdecode(np.frombuffer(result.image_data, np.uint8), cv2.IMREAD_COLOR)
        
        if frame is None:
            logger.error(f"[{self.id}] Failed to decode snapshot")
            return
        
        self.last_snapshot_time = result.timestamp
        
        # Process frame
        await self._process_frame(frame, result.image_data)
        
        self.successful_snapshots += 1
        self.status = "Running"
    
    async def _process_frame(self, frame: np.ndarray, image_data: bytes):
        """Process captured frame through analytics pipeline"""
        try:
            # Preprocessing
            if self.enable_preprocessing:
                frame = self._preprocess_frame(frame)
            
            # AI object detection
            if self.ai_manager:
                detections, processed_frame = await self.ai_manager.detect_objects(frame)
                self.latest_processed_frame = processed_frame
            else:
                detections = []
                processed_frame = frame
            
            # Video analytics
            if self.video_analytics_manager:
                analytics_events, analytics_frame = await self.video_analytics_manager.process_frame(
                    self.id, frame, frame_number=self.successful_snapshots
                )
                
                if analytics_events:
                    self.analytics_results.extend(analytics_events)
                    
                    # Handle incidents
                    if self.incident_manager:
                        await self.incident_manager.process_events(analytics_events, self.id)
                
                processed_frame = analytics_frame
            
            # Check for objects of interest
            ai_config = self.config.get('ai_processing', {})
            object_classes = ai_config.get('object_classes', [])
            
            is_object_of_interest_detected = any(
                d['class_name'] in object_classes for d in detections
            )
            
            # Save event if objects detected or analytics triggered
            if is_object_of_interest_detected or self.analytics_results:
                await self._save_snapshot_event(frame, detections, image_data)
            
            # Store in history
            self.snapshot_history.append({
                'timestamp': time.time(),
                'detections': detections,
                'analytics_events': len(self.analytics_results),
                'frame_hash': hashlib.md5(image_data).hexdigest()
            })
            
        except Exception as e:
            logger.error(f"[{self.id}] Frame processing error: {e}")
            self.error_count += 1
    
    def _preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """Preprocess frame for better analysis"""
        try:
            # Denoise
            frame = cv2.fastNlMeansDenoisingColored(frame, None, 10, 10, 7, 21)
            
            # Enhance contrast
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            frame = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
            
            # Sharpen
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            frame = cv2.filter2D(frame, -1, kernel)
            
            return frame
            
        except Exception as e:
            logger.error(f"Preprocessing error: {e}")
            return frame
    
    async def _save_snapshot_event(self, frame: np.ndarray, detections: List[Dict], image_data: bytes):
        """Save snapshot as a discrete event with blockchain anchoring"""
        event_id = f"{self.id}_snapshot_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        logger.info(f"[{event_id}] Object of interest detected in snapshot. Saving event.")
        
        try:
            # Save image to storage
            temp_image_path = self.storage_manager.base_path / f"snapshots/{self.id}" / f"{event_id}.jpg"
            temp_image_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save high-quality version
            cv2.imwrite(str(temp_image_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            # Blockchain anchoring if security manager available
            blockchain_tx = None
            if self.security_manager and hasattr(self.security_manager, 'anchor_event_to_blockchain'):
                try:
                    blockchain_tx = await self.security_manager.anchor_event_to_blockchain(event_id, temp_image_path)
                except Exception as e:
                    logger.warning(f"Blockchain anchoring failed: {e}")
            
            # Save event to storage manager
            if hasattr(self.storage_manager, 'save_event'):
                await self.storage_manager.save_event(
                    event_id, self.id, detections, frame,
                    video_path=None, blockchain_tx=blockchain_tx
                )
            
            # Trigger alerts if configured
            if self.alert_manager and detections:
                await self._trigger_alerts(event_id, detections)
            
            logger.info(f"[{event_id}] Snapshot event saved successfully")
            
        except Exception as e:
            logger.error(f"[{event_id}] Failed to save snapshot event: {e}")
    
    async def _trigger_alerts(self, event_id: str, detections: List[Dict]):
        """Trigger alerts based on detections"""
        try:
            for detection in detections:
                alert_config = self.config.get('alerts', {})
                if detection['class_name'] in alert_config.get('trigger_classes', []):
                    await self.alert_manager.send_alert(
                        alert_type='object_detection',
                        message=f"Detected {detection['class_name']} on camera {self.id}",
                        severity='medium',
                        camera_id=self.id,
                        event_id=event_id,
                        metadata={'detection': detection}
                    )
        except Exception as e:
            logger.error(f"Alert trigger error: {e}")
    
    def _health_monitoring_loop(self):
        """Monitor device health in background thread"""
        while self.is_running:
            try:
                if self.fleet_manager and self.device_manager:
                    asyncio.run(self.fleet_manager.fleet_health_check())
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                time.sleep(30)
    
    def stop(self):
        """Stop snapshot processing"""
        self.is_running = False
        logger.info(f"[{self.id}] Stop signal sent")
    
    async def get_latest_processed_frame(self):
        """Get latest processed frame"""
        return self.latest_processed_frame
    
    def get_status(self):
        """Get comprehensive device status"""
        base_status = {
            "id": self.id,
            "type": "esp32_snapshot",
            "status": self.status,
            "is_running": self.is_running,
            "last_snapshot_time_utc": datetime.fromtimestamp(self.last_snapshot_time).isoformat() if self.last_snapshot_time else None,
            "successful_snapshots": self.successful_snapshots,
            "error_count": self.error_count,
            "snapshot_interval": self.interval
        }
        
        # Add fleet metrics if available
        if self.device_manager:
            base_status['device_metrics'] = asdict(self.device_manager.metrics)
            base_status['device_capabilities'] = asdict(self.device_manager.capabilities)
            base_status['device_status'] = self.device_manager.status.value
        
        return base_status
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics"""
        success_rate = 0.0
        if self.successful_snapshots + self.error_count > 0:
            success_rate = self.successful_snapshots / (self.successful_snapshots + self.error_count)
        
        return {
            'success_rate': success_rate,
            'total_snapshots': self.successful_snapshots,
            'failed_snapshots': self.error_count,
            'average_interval': self.interval,
            'recent_snapshots': len(self.snapshot_history),
            'analytics_events': len(self.analytics_results),
            'uptime': time.time() - self.last_snapshot_time if self.last_snapshot_time else 0
        }

logger.info("Enterprise ESP32/IoT Camera Stream Processing System loaded successfully")
