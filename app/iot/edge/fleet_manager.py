"""
Fleet Management System for IoT Devices

Comprehensive fleet management for thousands of agricultural IoT devices.

Features:
- Device inventory management
- Real-time device monitoring
- Group management & hierarchies
- Command & control
- Configuration management
- Geolocation tracking
- Device health monitoring
- Automated alerts
- Resource utilization tracking
"""

import logging
from typing import Dict, List, Optional, Tuple, Union, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import asyncio
from collections import defaultdict, deque
import numpy as np

from redis import Redis
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import paho.mqtt.client as mqtt


logger = logging.getLogger(__name__)

Base = declarative_base()


class DeviceStatus(Enum):
    """Device status enumeration"""
    ONLINE = "online"
    OFFLINE = "offline"
    WARNING = "warning"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    DECOMMISSIONED = "decommissioned"


class DeviceType(Enum):
    """Device type enumeration"""
    SENSOR_NODE = "sensor_node"
    GATEWAY = "gateway"
    ACTUATOR = "actuator"
    CAMERA = "camera"
    WEATHER_STATION = "weather_station"
    DRONE = "drone"


@dataclass
class DeviceInfo:
    """Device information"""
    device_id: str
    device_type: DeviceType
    name: str
    status: DeviceStatus
    firmware_version: str
    hardware_version: str
    location: Tuple[float, float]  # (latitude, longitude)
    farm_id: str
    last_seen: datetime
    registration_date: datetime
    metadata: Dict = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class DeviceMetrics:
    """Device operational metrics"""
    device_id: str
    timestamp: datetime
    battery_level: Optional[float] = None
    signal_strength: Optional[float] = None  # RSSI
    temperature: Optional[float] = None
    uptime_seconds: Optional[int] = None
    memory_usage_percent: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    network_bytes_sent: Optional[int] = None
    network_bytes_received: Optional[int] = None
    error_count: int = 0
    message_count: int = 0


@dataclass
class DeviceCommand:
    """Command to send to device"""
    command_id: str
    device_id: str
    command_type: str
    parameters: Dict
    created_at: datetime
    executed_at: Optional[datetime] = None
    status: str = "pending"  # pending, sent, acknowledged, completed, failed
    response: Optional[Dict] = None
    timeout_seconds: int = 300


@dataclass
class DeviceGroup:
    """Device group for hierarchical organization"""
    group_id: str
    name: str
    description: str
    parent_group_id: Optional[str] = None
    device_ids: Set[str] = field(default_factory=set)
    child_group_ids: Set[str] = field(default_factory=set)
    metadata: Dict = field(default_factory=dict)


class DeviceModel(Base):
    """SQLAlchemy model for device persistence"""
    __tablename__ = 'devices'
    
    id = Column(Integer, primary_key=True)
    device_id = Column(String(100), unique=True, nullable=False, index=True)
    device_type = Column(String(50), nullable=False)
    name = Column(String(200))
    status = Column(String(50), nullable=False)
    firmware_version = Column(String(50))
    hardware_version = Column(String(50))
    latitude = Column(Float)
    longitude = Column(Float)
    farm_id = Column(String(100), index=True)
    last_seen = Column(DateTime)
    registration_date = Column(DateTime, default=datetime.now)
    metadata = Column(JSON)
    tags = Column(JSON)


class FleetManager:
    """
    Central fleet management system
    
    Manages inventory, monitoring, and control of IoT device fleet.
    """
    
    def __init__(
        self,
        database_url: str,
        redis_client: Redis,
        mqtt_broker: str = "localhost",
        mqtt_port: int = 1883
    ):
        # Database setup
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Redis for caching and real-time data
        self.redis = redis_client
        
        # MQTT for device communication
        self.mqtt_client = mqtt.Client()
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.mqtt_connected = False
        
        # In-memory caches
        self.device_cache: Dict[str, DeviceInfo] = {}
        self.metrics_cache: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.groups: Dict[str, DeviceGroup] = {}
        self.pending_commands: Dict[str, DeviceCommand] = {}
        
        # Statistics
        self.stats = {
            'total_devices': 0,
            'online_devices': 0,
            'offline_devices': 0,
            'warning_devices': 0,
            'error_devices': 0,
        }
        
        # Setup MQTT callbacks
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        
        # Connect to MQTT
        try:
            self.mqtt_client.connect(mqtt_broker, mqtt_port, 60)
            self.mqtt_client.loop_start()
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
        
        logger.info(f"FleetManager initialized (broker={mqtt_broker}:{mqtt_port})")
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            self.mqtt_connected = True
            # Subscribe to all device topics
            self.mqtt_client.subscribe("devices/+/status")
            self.mqtt_client.subscribe("devices/+/metrics")
            self.mqtt_client.subscribe("devices/+/data")
            self.mqtt_client.subscribe("devices/+/response")
            logger.info("Connected to MQTT broker")
        else:
            logger.error(f"MQTT connection failed with code {rc}")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """MQTT message callback"""
        try:
            # Parse topic
            topic_parts = msg.topic.split('/')
            if len(topic_parts) < 3:
                return
            
            device_id = topic_parts[1]
            message_type = topic_parts[2]
            
            # Parse payload
            payload = json.loads(msg.payload.decode())
            
            # Handle message based on type
            if message_type == 'status':
                self._handle_status_update(device_id, payload)
            elif message_type == 'metrics':
                self._handle_metrics_update(device_id, payload)
            elif message_type == 'response':
                self._handle_command_response(device_id, payload)
            
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def _handle_status_update(self, device_id: str, payload: Dict):
        """Handle device status update"""
        if device_id in self.device_cache:
            device = self.device_cache[device_id]
            old_status = device.status
            new_status = DeviceStatus(payload.get('status', 'online'))
            
            device.status = new_status
            device.last_seen = datetime.now()
            
            # Update stats
            if old_status != new_status:
                self._update_stats()
            
            # Cache in Redis
            self.redis.setex(
                f"device:status:{device_id}",
                300,  # 5 minute TTL
                json.dumps({
                    'status': new_status.value,
                    'last_seen': device.last_seen.isoformat()
                })
            )
    
    def _handle_metrics_update(self, device_id: str, payload: Dict):
        """Handle device metrics update"""
        metrics = DeviceMetrics(
            device_id=device_id,
            timestamp=datetime.now(),
            battery_level=payload.get('battery_level'),
            signal_strength=payload.get('rssi'),
            temperature=payload.get('temperature'),
            uptime_seconds=payload.get('uptime'),
            memory_usage_percent=payload.get('memory_usage'),
            cpu_usage_percent=payload.get('cpu_usage'),
            network_bytes_sent=payload.get('bytes_sent'),
            network_bytes_received=payload.get('bytes_received'),
            error_count=payload.get('error_count', 0),
            message_count=payload.get('message_count', 0)
        )
        
        # Add to metrics cache
        self.metrics_cache[device_id].append(metrics)
        
        # Cache in Redis with 1-hour TTL
        self.redis.setex(
            f"device:metrics:{device_id}",
            3600,
            json.dumps({
                'battery_level': metrics.battery_level,
                'signal_strength': metrics.signal_strength,
                'timestamp': metrics.timestamp.isoformat()
            })
        )
        
        # Check for alerts
        self._check_device_alerts(device_id, metrics)
    
    def _handle_command_response(self, device_id: str, payload: Dict):
        """Handle command response from device"""
        command_id = payload.get('command_id')
        if command_id in self.pending_commands:
            command = self.pending_commands[command_id]
            command.status = payload.get('status', 'completed')
            command.response = payload.get('response')
            command.executed_at = datetime.now()
            
            logger.info(f"Command {command_id} {command.status} on device {device_id}")
    
    def _check_device_alerts(self, device_id: str, metrics: DeviceMetrics):
        """Check for alert conditions"""
        alerts = []
        
        # Low battery
        if metrics.battery_level is not None and metrics.battery_level < 20:
            alerts.append({
                'type': 'low_battery',
                'severity': 'warning' if metrics.battery_level > 10 else 'critical',
                'message': f"Low battery: {metrics.battery_level}%",
                'device_id': device_id
            })
        
        # Poor signal
        if metrics.signal_strength is not None and metrics.signal_strength < -90:
            alerts.append({
                'type': 'poor_signal',
                'severity': 'warning',
                'message': f"Poor signal strength: {metrics.signal_strength} dBm",
                'device_id': device_id
            })
        
        # High temperature
        if metrics.temperature is not None and metrics.temperature > 70:
            alerts.append({
                'type': 'high_temperature',
                'severity': 'critical',
                'message': f"High temperature: {metrics.temperature}°C",
                'device_id': device_id
            })
        
        # Publish alerts
        for alert in alerts:
            self.mqtt_client.publish(
                f"alerts/{device_id}",
                json.dumps(alert)
            )
            logger.warning(f"Alert for {device_id}: {alert['message']}")
    
    def _update_stats(self):
        """Update fleet statistics"""
        stats = {
            'total_devices': len(self.device_cache),
            'online_devices': 0,
            'offline_devices': 0,
            'warning_devices': 0,
            'error_devices': 0,
        }
        
        for device in self.device_cache.values():
            if device.status == DeviceStatus.ONLINE:
                stats['online_devices'] += 1
            elif device.status == DeviceStatus.OFFLINE:
                stats['offline_devices'] += 1
            elif device.status == DeviceStatus.WARNING:
                stats['warning_devices'] += 1
            elif device.status == DeviceStatus.ERROR:
                stats['error_devices'] += 1
        
        self.stats = stats
        
        # Cache in Redis
        self.redis.setex('fleet:stats', 60, json.dumps(stats))
    
    def register_device(
        self,
        device_id: str,
        device_type: DeviceType,
        name: str,
        firmware_version: str,
        hardware_version: str,
        location: Tuple[float, float],
        farm_id: str,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None
    ) -> DeviceInfo:
        """
        Register new device in fleet
        
        Args:
            device_id: Unique device ID
            device_type: Type of device
            name: Device name
            firmware_version: Firmware version
            hardware_version: Hardware version
            location: GPS coordinates (lat, lon)
            farm_id: Farm ID
            metadata: Optional metadata
            tags: Optional tags
            
        Returns:
            Device info
        """
        device_info = DeviceInfo(
            device_id=device_id,
            device_type=device_type,
            name=name,
            status=DeviceStatus.OFFLINE,
            firmware_version=firmware_version,
            hardware_version=hardware_version,
            location=location,
            farm_id=farm_id,
            last_seen=datetime.now(),
            registration_date=datetime.now(),
            metadata=metadata or {},
            tags=tags or []
        )
        
        # Add to cache
        self.device_cache[device_id] = device_info
        
        # Persist to database
        db = self.SessionLocal()
        try:
            device_model = DeviceModel(
                device_id=device_id,
                device_type=device_type.value,
                name=name,
                status=DeviceStatus.OFFLINE.value,
                firmware_version=firmware_version,
                hardware_version=hardware_version,
                latitude=location[0],
                longitude=location[1],
                farm_id=farm_id,
                registration_date=datetime.now(),
                metadata=metadata,
                tags=tags
            )
            db.add(device_model)
            db.commit()
        finally:
            db.close()
        
        self._update_stats()
        logger.info(f"Registered device: {device_id}")
        
        return device_info
    
    def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        """Get device information"""
        # Try cache first
        if device_id in self.device_cache:
            return self.device_cache[device_id]
        
        # Try Redis
        cached = self.redis.get(f"device:info:{device_id}")
        if cached:
            data = json.loads(cached)
            return DeviceInfo(**data)
        
        # Load from database
        db = self.SessionLocal()
        try:
            device = db.query(DeviceModel).filter_by(device_id=device_id).first()
            if device:
                device_info = DeviceInfo(
                    device_id=device.device_id,
                    device_type=DeviceType(device.device_type),
                    name=device.name,
                    status=DeviceStatus(device.status),
                    firmware_version=device.firmware_version,
                    hardware_version=device.hardware_version,
                    location=(device.latitude, device.longitude),
                    farm_id=device.farm_id,
                    last_seen=device.last_seen,
                    registration_date=device.registration_date,
                    metadata=device.metadata or {},
                    tags=device.tags or []
                )
                self.device_cache[device_id] = device_info
                return device_info
        finally:
            db.close()
        
        return None
    
    def list_devices(
        self,
        farm_id: Optional[str] = None,
        device_type: Optional[DeviceType] = None,
        status: Optional[DeviceStatus] = None,
        tags: Optional[List[str]] = None
    ) -> List[DeviceInfo]:
        """List devices with optional filtering"""
        devices = list(self.device_cache.values())
        
        if farm_id:
            devices = [d for d in devices if d.farm_id == farm_id]
        
        if device_type:
            devices = [d for d in devices if d.device_type == device_type]
        
        if status:
            devices = [d for d in devices if d.status == status]
        
        if tags:
            devices = [
                d for d in devices
                if any(tag in d.tags for tag in tags)
            ]
        
        return devices
    
    def send_command(
        self,
        device_id: str,
        command_type: str,
        parameters: Dict,
        timeout_seconds: int = 300
    ) -> DeviceCommand:
        """
        Send command to device
        
        Args:
            device_id: Device ID
            command_type: Command type
            parameters: Command parameters
            timeout_seconds: Command timeout
            
        Returns:
            Device command
        """
        import uuid
        
        command_id = str(uuid.uuid4())
        command = DeviceCommand(
            command_id=command_id,
            device_id=device_id,
            command_type=command_type,
            parameters=parameters,
            created_at=datetime.now(),
            timeout_seconds=timeout_seconds
        )
        
        # Store command
        self.pending_commands[command_id] = command
        
        # Publish to MQTT
        topic = f"devices/{device_id}/commands"
        payload = json.dumps({
            'command_id': command_id,
            'command_type': command_type,
            'parameters': parameters
        })
        
        self.mqtt_client.publish(topic, payload)
        command.status = 'sent'
        
        logger.info(f"Sent command {command_id} to device {device_id}")
        
        return command
    
    def get_device_metrics(
        self,
        device_id: str,
        limit: int = 100
    ) -> List[DeviceMetrics]:
        """Get recent metrics for device"""
        if device_id in self.metrics_cache:
            metrics_list = list(self.metrics_cache[device_id])
            return metrics_list[-limit:]
        return []
    
    def get_fleet_statistics(self) -> Dict:
        """Get fleet-wide statistics"""
        return self.stats.copy()
    
    def create_group(
        self,
        group_id: str,
        name: str,
        description: str,
        parent_group_id: Optional[str] = None
    ) -> DeviceGroup:
        """Create device group"""
        group = DeviceGroup(
            group_id=group_id,
            name=name,
            description=description,
            parent_group_id=parent_group_id
        )
        
        self.groups[group_id] = group
        
        # Add to parent's children
        if parent_group_id and parent_group_id in self.groups:
            self.groups[parent_group_id].child_group_ids.add(group_id)
        
        logger.info(f"Created group: {group_id}")
        return group
    
    def add_device_to_group(self, device_id: str, group_id: str):
        """Add device to group"""
        if group_id in self.groups:
            self.groups[group_id].device_ids.add(device_id)
            logger.info(f"Added device {device_id} to group {group_id}")
    
    def get_group_devices(self, group_id: str, recursive: bool = True) -> List[str]:
        """Get all devices in group"""
        if group_id not in self.groups:
            return []
        
        device_ids = set(self.groups[group_id].device_ids)
        
        # Recursively get devices from child groups
        if recursive:
            for child_id in self.groups[group_id].child_group_ids:
                device_ids.update(self.get_group_devices(child_id, recursive=True))
        
        return list(device_ids)


class DeviceOrchestrator:
    """
    Device orchestration for bulk operations
    
    Coordinates actions across multiple devices.
    """
    
    def __init__(self, fleet_manager: FleetManager):
        self.fleet_manager = fleet_manager
        self.active_jobs: Dict[str, Dict] = {}
        logger.info("DeviceOrchestrator initialized")
    
    async def bulk_command(
        self,
        device_ids: List[str],
        command_type: str,
        parameters: Dict,
        parallel: bool = True,
        max_concurrent: int = 10
    ) -> Dict[str, DeviceCommand]:
        """
        Send command to multiple devices
        
        Args:
            device_ids: List of device IDs
            command_type: Command type
            parameters: Command parameters
            parallel: Execute in parallel
            max_concurrent: Max concurrent operations
            
        Returns:
            Map of device_id to command result
        """
        import asyncio
        
        results = {}
        
        if parallel:
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def send_with_limit(device_id):
                async with semaphore:
                    command = self.fleet_manager.send_command(
                        device_id, command_type, parameters
                    )
                    results[device_id] = command
            
            tasks = [send_with_limit(dev_id) for dev_id in device_ids]
            await asyncio.gather(*tasks)
        else:
            for device_id in device_ids:
                command = self.fleet_manager.send_command(
                    device_id, command_type, parameters
                )
                results[device_id] = command
        
        logger.info(f"Bulk command sent to {len(device_ids)} devices")
        return results
    
    async def rolling_update(
        self,
        device_ids: List[str],
        firmware_url: str,
        batch_size: int = 10,
        wait_between_batches: int = 300
    ):
        """
        Perform rolling firmware update
        
        Args:
            device_ids: Devices to update
            firmware_url: Firmware download URL
            batch_size: Devices per batch
            wait_between_batches: Wait time in seconds
        """
        import asyncio
        
        total_devices = len(device_ids)
        batches = [device_ids[i:i+batch_size] for i in range(0, total_devices, batch_size)]
        
        logger.info(f"Starting rolling update for {total_devices} devices in {len(batches)} batches")
        
        for i, batch in enumerate(batches):
            logger.info(f"Updating batch {i+1}/{len(batches)}")
            
            results = await self.bulk_command(
                batch,
                'firmware_update',
                {'url': firmware_url}
            )
            
            # Wait between batches
            if i < len(batches) - 1:
                logger.info(f"Waiting {wait_between_batches}s before next batch")
                await asyncio.sleep(wait_between_batches)
        
        logger.info("Rolling update completed")
