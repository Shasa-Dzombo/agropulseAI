# Advanced Enterprise AI-NVR System - Main Application
# Comprehensive surveillance and security platform with full enterprise capabilities
# Multi-million LOC distributed architecture with advanced analytics, AI, and security

import asyncio
import os
import sys
import signal
import yaml
import json
import logging
import time
import threading
import multiprocessing
import psutil
import socket
import hashlib
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set, Union
from dataclasses import dataclass, field
from enum import Enum
import traceback
import gc
import resource
import platform

# Advanced import management with fallback handling
try:
    import uvloop
    UVLOOP_AVAILABLE = True
except ImportError:
    UVLOOP_AVAILABLE = False

try:
    import prometheus_client
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

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

# Core NVR System Imports
from stream_processor.manager import StreamManager
from ai_engine.manager import AIEngineManager
from storage_manager.manager import StorageManager
from security_manager.manager import SecurityManager
from api.server import APIServer
from database.manager import DatabaseManager
from system_health.manager import SystemHealthManager
from alerting.manager import AlertManager
from video_analytics.manager import VideoAnalyticsManager
from federation.manager import FederationManager
from cloud_sync.manager import CloudSyncManager
from incident_manager.manager import IncidentManager
from live_map.manager import LiveMapManager
from reporting.manager import ReportingManager
from automation.manager import AutomationManager
from onvif_client.manager import ONVIFManager
from ha_manager.manager import HAManager

# Advanced Feature Managers
from predictive_analytics.manager import PredictiveAnalyticsManager
from mobile_units.manager import MobileUnitManager
from biometrics.manager import BiometricsManager
from access_control.manager import AccessControlManager
from forensics.manager import ForensicsManager
from supply_chain_security.manager import SupplyChainSecurityManager
from human_computer_interface.manager import HCIManager
from environmental_sensing.manager import EnvironmentalSensingManager
from compliance_automation.manager import ComplianceManager
from blockchain_ledger.manager import BlockchainLedgerManager
from cyber_defense.manager import CyberDefenseManager
from quantum_security.manager import QuantumSecurityManager
from simulation.manager import SimulationManager
from operational_intelligence.manager import OperationalIntelligenceManager
from collaboration.manager import CollaborationManager
from audio_analytics.manager import AudioAnalyticsManager
from evidence_chain.manager import EvidenceChainManager

# Advanced logging configuration with structured logging
class StructuredFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'process': os.getpid(),
            'thread': threading.current_thread().name
        }
        
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry)

class SystemStatus(Enum):
    INITIALIZING = "initializing"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"

class ServicePriority(Enum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4

@dataclass
class ServiceInfo:
    name: str
    manager: Any
    priority: ServicePriority
    depends_on: List[str] = field(default_factory=list)
    health_check: Optional[str] = None
    startup_timeout: int = 30
    shutdown_timeout: int = 15
    restart_policy: str = "always"
    max_restarts: int = 3
    restart_count: int = 0
    last_restart: Optional[float] = None
    status: str = "inactive"
    error_count: int = 0

@dataclass
class SystemMetrics:
    startup_time: Optional[float] = None
    total_memory_usage: float = 0.0
    cpu_usage: float = 0.0
    gpu_usage: float = 0.0
    disk_io: Dict[str, float] = field(default_factory=dict)
    network_io: Dict[str, float] = field(default_factory=dict)
    active_streams: int = 0
    processed_frames: int = 0
    generated_alerts: int = 0
    system_errors: int = 0
    uptime: float = 0.0

class ConfigurationManager:
    def __init__(self, config_path: str = 'config/nvr_config.yml'):
        self.config_path = Path(config_path)
        self.config = {}
        self.config_watchers = []
        self.last_modified = 0
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration with validation and environment variable substitution"""
        try:
            if not self.config_path.exists():
                self._create_default_config()
            
            with open(self.config_path, 'r') as f:
                raw_config = yaml.safe_load(f)
            
            # Environment variable substitution
            self.config = self._substitute_env_vars(raw_config)
            
            # Validate configuration
            self._validate_config()
            
            self.last_modified = self.config_path.stat().st_mtime
            
            logger.info(f"Configuration loaded successfully from {self.config_path}")
            return self.config
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _substitute_env_vars(self, config: Any) -> Any:
        """Recursively substitute environment variables in configuration"""
        if isinstance(config, dict):
            return {k: self._substitute_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        elif isinstance(config, str) and config.startswith('${') and config.endswith('}'):
            env_var = config[2:-1]
            default_value = None
            if ':' in env_var:
                env_var, default_value = env_var.split(':', 1)
            return os.getenv(env_var, default_value)
        else:
            return config
    
    def _validate_config(self):
        """Validate critical configuration parameters"""
        required_sections = ['system', 'database', 'security', 'storage', 'alerting']
        
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required configuration section: {section}")
        
        # Validate system resources
        system_config = self.config['system']
        max_workers = system_config.get('thread_pool_workers', 8)
        
        if max_workers > multiprocessing.cpu_count() * 2:
            logger.warning(f"Thread pool workers ({max_workers}) exceeds recommended maximum")
    
    def _create_default_config(self):
        """Create default configuration if none exists"""
        default_config = {
            'system': {
                'name': 'AgroPulse-NVR-Enterprise',
                'version': '2.0.0',
                'instance_id': hashlib.md5(socket.gethostname().encode()).hexdigest()[:8],
                'thread_pool_workers': min(32, (os.cpu_count() or 1) + 4),
                'process_pool_workers': min(16, os.cpu_count() or 1),
                'max_memory_usage_gb': 16,
                'log_level': 'INFO',
                'metrics_enabled': True,
                'health_check_interval': 30
            },
            'database': {
                'type': 'postgresql',
                'host': '${DB_HOST:localhost}',
                'port': '${DB_PORT:5432}',
                'name': '${DB_NAME:agropulse_nvr}',
                'user': '${DB_USER:nvr_user}',
                'password': '${DB_PASSWORD:secure_password}',
                'pool_size': 20,
                'max_overflow': 30
            },
            'security': {
                'encryption_enabled': True,
                'tls_enabled': True,
                'certificate_path': 'certs/server.crt',
                'private_key_path': 'certs/server.key',
                'jwt_secret': '${JWT_SECRET:change_this_secret}',
                'session_timeout': 3600,
                'max_login_attempts': 5
            },
            'storage': {
                'base_path': '${STORAGE_PATH:/var/lib/agropulse/storage}',
                'retention_days': 90,
                'compression_enabled': True,
                'encryption_enabled': True,
                'redundancy_level': 2
            },
            'alerting': {
                'enabled': True,
                'email_enabled': True,
                'sms_enabled': False,
                'webhook_enabled': True,
                'escalation_enabled': True
            },
            'cameras': {},
            'ai_engine': {
                'enabled': True,
                'gpu_enabled': True,
                'model_cache_size': 5,
                'inference_batch_size': 4
            }
        }
        
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
        
        logger.info(f"Created default configuration at {self.config_path}")

class PerformanceMonitor:
    def __init__(self, nvr_system):
        self.nvr_system = nvr_system
        self.metrics = SystemMetrics()
        self.is_monitoring = False
        self.monitor_thread = None
        
        # Prometheus metrics if available
        self.prometheus_metrics = {}
        if PROMETHEUS_AVAILABLE:
            self._setup_prometheus_metrics()
    
    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics collectors"""
        self.prometheus_metrics = {
            'system_info': prometheus_client.Info('nvr_system', 'NVR System Information'),
            'uptime': prometheus_client.Gauge('nvr_uptime_seconds', 'System uptime in seconds'),
            'memory_usage': prometheus_client.Gauge('nvr_memory_usage_bytes', 'Memory usage in bytes'),
            'cpu_usage': prometheus_client.Gauge('nvr_cpu_usage_percent', 'CPU usage percentage'),
            'active_streams': prometheus_client.Gauge('nvr_active_streams', 'Number of active streams'),
            'processed_frames': prometheus_client.Counter('nvr_processed_frames_total', 'Total processed frames'),
            'alerts_generated': prometheus_client.Counter('nvr_alerts_total', 'Total alerts generated'),
            'errors': prometheus_client.Counter('nvr_errors_total', 'Total system errors')
        }
    
    def start_monitoring(self):
        """Start performance monitoring"""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        logger.info("Performance monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                self._collect_system_metrics()
                self._collect_application_metrics()
                self._update_prometheus_metrics()
                time.sleep(10)  # Collect metrics every 10 seconds
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                time.sleep(5)
    
    def _collect_system_metrics(self):
        """Collect system-level performance metrics"""
        try:
            # CPU and Memory
            self.metrics.cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            self.metrics.total_memory_usage = memory.used
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            if disk_io:
                self.metrics.disk_io = {
                    'read_bytes': disk_io.read_bytes,
                    'write_bytes': disk_io.write_bytes,
                    'read_count': disk_io.read_count,
                    'write_count': disk_io.write_count
                }
            
            # Network I/O
            network_io = psutil.net_io_counters()
            if network_io:
                self.metrics.network_io = {
                    'bytes_sent': network_io.bytes_sent,
                    'bytes_recv': network_io.bytes_recv,
                    'packets_sent': network_io.packets_sent,
                    'packets_recv': network_io.packets_recv
                }
            
            # System uptime
            if self.metrics.startup_time:
                self.metrics.uptime = time.time() - self.metrics.startup_time
                
        except Exception as e:
            logger.error(f"System metrics collection error: {e}")
    
    def _collect_application_metrics(self):
        """Collect application-specific metrics"""
        try:
            # Stream metrics
            if hasattr(self.nvr_system, 'stream_manager'):
                self.metrics.active_streams = len(self.nvr_system.stream_manager.active_streams)
            
            # Processing metrics from managers
            total_processed_frames = 0
            total_alerts = 0
            total_errors = 0
            
            for service_name, service_info in self.nvr_system.services.items():
                manager = service_info.manager
                
                if hasattr(manager, 'get_metrics'):
                    manager_metrics = manager.get_metrics()
                    total_processed_frames += manager_metrics.get('processed_frames', 0)
                    total_alerts += manager_metrics.get('generated_alerts', 0)
                    total_errors += manager_metrics.get('error_count', 0)
            
            self.metrics.processed_frames = total_processed_frames
            self.metrics.generated_alerts = total_alerts
            self.metrics.system_errors = total_errors
            
        except Exception as e:
            logger.error(f"Application metrics collection error: {e}")
    
    def _update_prometheus_metrics(self):
        """Update Prometheus metrics if available"""
        if not PROMETHEUS_AVAILABLE or not self.prometheus_metrics:
            return
        
        try:
            self.prometheus_metrics['uptime'].set(self.metrics.uptime)
            self.prometheus_metrics['memory_usage'].set(self.metrics.total_memory_usage)
            self.prometheus_metrics['cpu_usage'].set(self.metrics.cpu_usage)
            self.prometheus_metrics['active_streams'].set(self.metrics.active_streams)
            
        except Exception as e:
            logger.error(f"Prometheus metrics update error: {e}")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        return {
            'system': {
                'uptime': self.metrics.uptime,
                'cpu_usage': self.metrics.cpu_usage,
                'memory_usage_mb': self.metrics.total_memory_usage / 1024 / 1024,
                'startup_time': self.metrics.startup_time
            },
            'application': {
                'active_streams': self.metrics.active_streams,
                'processed_frames': self.metrics.processed_frames,
                'generated_alerts': self.metrics.generated_alerts,
                'system_errors': self.metrics.system_errors
            },
            'io': {
                'disk': self.metrics.disk_io,
                'network': self.metrics.network_io
            }
        }

class ServiceOrchestrator:
    def __init__(self, nvr_system):
        self.nvr_system = nvr_system
        self.services = {}
        self.dependency_graph = {}
        self.startup_order = []
        self.shutdown_order = []
        
    def register_service(self, service_info: ServiceInfo):
        """Register a service with the orchestrator"""
        self.services[service_info.name] = service_info
        self._build_dependency_graph()
    
    def _build_dependency_graph(self):
        """Build service dependency graph and determine startup order"""
        # Reset graphs
        self.dependency_graph = {name: info.depends_on for name, info in self.services.items()}
        
        # Calculate startup order using topological sort
        self.startup_order = self._topological_sort()
        self.shutdown_order = list(reversed(self.startup_order))
    
    def _topological_sort(self) -> List[str]:
        """Perform topological sort to determine startup order"""
        visited = set()
        temp_visited = set()
        order = []
        
        def visit(service_name: str):
            if service_name in temp_visited:
                raise ValueError(f"Circular dependency detected involving {service_name}")
            
            if service_name not in visited:
                temp_visited.add(service_name)
                
                for dependency in self.dependency_graph.get(service_name, []):
                    visit(dependency)
                
                temp_visited.remove(service_name)
                visited.add(service_name)
                order.append(service_name)
        
        for service_name in self.services:
            if service_name not in visited:
                visit(service_name)
        
        return order
    
    async def start_services(self):
        """Start all services in dependency order"""
        logger.info("Starting services in dependency order...")
        
        for service_name in self.startup_order:
            service_info = self.services[service_name]
            
            try:
                logger.info(f"Starting service: {service_name}")
                service_info.status = "starting"
                
                # Check dependencies
                for dependency in service_info.depends_on:
                    dep_service = self.services.get(dependency)
                    if not dep_service or dep_service.status != "running":
                        raise RuntimeError(f"Dependency {dependency} is not running")
                
                # Start the service with timeout
                start_task = asyncio.create_task(service_info.manager.start())
                await asyncio.wait_for(start_task, timeout=service_info.startup_timeout)
                
                service_info.status = "running"
                logger.info(f"Service {service_name} started successfully")
                
            except asyncio.TimeoutError:
                logger.error(f"Service {service_name} startup timeout")
                service_info.status = "failed"
                service_info.error_count += 1
                
            except Exception as e:
                logger.error(f"Failed to start service {service_name}: {e}")
                service_info.status = "failed"
                service_info.error_count += 1
                
                # Handle restart policy
                if service_info.restart_policy == "always" and service_info.restart_count < service_info.max_restarts:
                    await self._restart_service(service_name)
    
    async def stop_services(self):
        """Stop all services in reverse dependency order"""
        logger.info("Stopping services in reverse dependency order...")
        
        for service_name in self.shutdown_order:
            service_info = self.services[service_name]
            
            try:
                if service_info.status == "running":
                    logger.info(f"Stopping service: {service_name}")
                    service_info.status = "stopping"
                    
                    # Stop the service with timeout
                    if hasattr(service_info.manager, 'stop'):
                        stop_task = asyncio.create_task(service_info.manager.stop())
                        await asyncio.wait_for(stop_task, timeout=service_info.shutdown_timeout)
                    
                    service_info.status = "stopped"
                    logger.info(f"Service {service_name} stopped successfully")
                    
            except asyncio.TimeoutError:
                logger.warning(f"Service {service_name} shutdown timeout, forcing stop")
                service_info.status = "stopped"
                
            except Exception as e:
                logger.error(f"Error stopping service {service_name}: {e}")
                service_info.status = "failed"
    
    async def _restart_service(self, service_name: str):
        """Restart a failed service"""
        service_info = self.services[service_name]
        
        if service_info.restart_count >= service_info.max_restarts:
            logger.error(f"Service {service_name} exceeded maximum restart attempts")
            return
        
        service_info.restart_count += 1
        service_info.last_restart = time.time()
        
        logger.info(f"Restarting service {service_name} (attempt {service_info.restart_count})")
        
        try:
            # Stop the service first
            if hasattr(service_info.manager, 'stop'):
                await service_info.manager.stop()
            
            # Wait a bit before restarting
            await asyncio.sleep(2)
            
            # Start the service again
            await service_info.manager.start()
            service_info.status = "running"
            
            logger.info(f"Service {service_name} restarted successfully")
            
        except Exception as e:
            logger.error(f"Failed to restart service {service_name}: {e}")
            service_info.status = "failed"
    
    def get_service_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all services"""
        status = {}
        
        for name, info in self.services.items():
            status[name] = {
                'status': info.status,
                'priority': info.priority.name,
                'restart_count': info.restart_count,
                'error_count': info.error_count,
                'last_restart': info.last_restart,
                'depends_on': info.depends_on
            }
        
        return status

class NVRSystem:
    def __init__(self, config_path='config/nvr_config.yml'):
        # System identification
        self.instance_id = hashlib.md5(f"{socket.gethostname()}_{os.getpid()}_{time.time()}".encode()).hexdigest()[:16]
        self.startup_time = time.time()
        self.status = SystemStatus.INITIALIZING
        
        # Configuration management
        self.config_manager = ConfigurationManager(config_path)
        self.config = self.config_manager.load_config()
        
        # Advanced logging setup
        self._setup_advanced_logging()
        
        logger.info(f"Initializing AgroPulse AI-NVR Enterprise System v2.0 (Instance: {self.instance_id})")
        logger.info(f"Platform: {platform.platform()}")
        logger.info(f"Python: {sys.version}")
        logger.info(f"CPUs: {multiprocessing.cpu_count()}")
        logger.info(f"Memory: {psutil.virtual_memory().total // 1024 // 1024 // 1024} GB")
        
        # Event loop optimization
        if UVLOOP_AVAILABLE:
            uvloop.install()
            logger.info("UVLoop event loop installed for better performance")
        
        # Execution infrastructure
        self.loop = asyncio.get_event_loop()
        self.executor = ThreadPoolExecutor(
            max_workers=self.config['system']['thread_pool_workers'],
            thread_name_prefix="NVR-Worker"
        )
        self.process_executor = ProcessPoolExecutor(
            max_workers=self.config['system'].get('process_pool_workers', 4)
        )
        
        # Service orchestration
        self.orchestrator = ServiceOrchestrator(self)
        self.services = {}
        
        # Performance monitoring
        self.performance_monitor = PerformanceMonitor(self)
        self.performance_monitor.metrics.startup_time = self.startup_time
        
        # Signal handlers
        self._setup_signal_handlers()
        
        # Initialize all managers with advanced configuration
        self._initialize_core_managers()
        self._initialize_analytics_managers()
        self._initialize_enterprise_managers()
        self._initialize_advanced_managers()
        
        # Register all services with orchestrator
        self._register_services()
        
        logger.info(f"Initialized {len(self.services)} enterprise-grade services")
        logger.info("All enterprise managers loaded successfully - Ready for multi-million LOC operation")
    
    def _setup_advanced_logging(self):
        """Setup advanced structured logging with multiple outputs"""
        log_level = getattr(logging, self.config['system'].get('log_level', 'INFO'))
        
        # Create logs directory
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler with structured formatting
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(console_handler)
        
        # File handler for persistent logging
        file_handler = logging.FileHandler(
            log_dir / f'nvr_system_{datetime.now().strftime("%Y%m%d")}.log'
        )
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)
        
        # Error file handler
        error_handler = logging.FileHandler(log_dir / 'nvr_errors.log')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(error_handler)
        
        # Performance log handler
        perf_handler = logging.FileHandler(log_dir / 'nvr_performance.log')
        perf_handler.setLevel(logging.INFO)
        perf_handler.addFilter(lambda record: 'performance' in record.getMessage().lower())
        root_logger.addHandler(perf_handler)
    
    def _setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        if hasattr(signal, 'SIGHUP'):
            def reload_handler(signum, frame):
                logger.info("Received SIGHUP, reloading configuration...")
                asyncio.create_task(self._reload_configuration())
            signal.signal(signal.SIGHUP, reload_handler)
    
    def _initialize_core_managers(self):
        """Initialize core system managers"""
        logger.info("Initializing core system managers...")
        
        # Database manager - Foundation for all data operations
        self.db_manager = DatabaseManager(self.config['database'])
        
        # Alert manager - Critical for system notifications
        self.alert_manager = AlertManager(self.config['alerting'])
        
        # Security manager - Enterprise security framework
        self.security_manager = SecurityManager(self.config['security'], self.db_manager)
        
        # Storage manager - Scalable storage orchestration
        self.storage_manager = StorageManager(self.config['storage'], self.db_manager)
        
        # AI engine manager - Advanced artificial intelligence
        self.ai_manager = AIEngineManager(self.config['ai_engine'], self.executor, self.db_manager)
        
        # System health manager - Comprehensive monitoring
        self.system_health_manager = SystemHealthManager(self.config['system_health'], self.alert_manager)
        
        logger.info("Core managers initialized successfully")
    
    def _initialize_analytics_managers(self):
        """Initialize video analytics and processing managers"""
        logger.info("Initializing analytics and processing managers...")
        
        # Video analytics - Advanced computer vision
        self.video_analytics_manager = VideoAnalyticsManager(
            self.config.get('video_analytics', {}), 
            self.db_manager, 
            self.alert_manager
        )
        
        # Audio analytics - Sound analysis and recognition
        self.audio_analytics_manager = AudioAnalyticsManager(
            self.config.get('audio_analytics', {}),
            self.db_manager,
            self.alert_manager
        )
        
        # Stream processor - Real-time video processing
        self.stream_manager = StreamManager(
            self.config['cameras'], 
            self.ai_manager, 
            self.storage_manager,
            self.security_manager, 
            self.alert_manager, 
            self.video_analytics_manager,
            None,  # incident_manager initialized later
            None,  # automation_manager initialized later
            self.loop
        )
        
        # Incident manager - Intelligent event correlation
        self.incident_manager = IncidentManager(
            self.config, 
            self.db_manager, 
            self.alert_manager, 
            self
        )
        
        # Automation manager - Rule-based automation
        self.automation_manager = AutomationManager(self.config, self.db_manager)
        
        logger.info("Analytics managers initialized successfully")
    
    def _initialize_enterprise_managers(self):
        """Initialize enterprise-grade managers"""
        logger.info("Initializing enterprise managers...")
        
        # Federation and clustering
        self.federation_manager = FederationManager(self.config, self.db_manager, self.alert_manager)
        self.ha_manager = HAManager(self.config, self.federation_manager, self.alert_manager)
        
        # Cloud and synchronization
        self.cloud_sync_manager = CloudSyncManager(self.config, self.db_manager, self.alert_manager)
        
        # Advanced analytics and intelligence
        self.predictive_analytics_manager = PredictiveAnalyticsManager(
            self.config, self.db_manager, self.alert_manager
        )
        self.operational_intelligence_manager = OperationalIntelligenceManager(
            self.config, self.db_manager, self.alert_manager
        )
        
        # Biometrics and access control
        self.biometrics_manager = BiometricsManager(self.config, self.db_manager)
        self.access_control_manager = AccessControlManager(
            self.config, self.db_manager, self.biometrics_manager
        )
        
        # Forensics and evidence management
        self.forensics_manager = ForensicsManager(
            self.config, self.db_manager, self.storage_manager
        )
        self.evidence_chain_manager = EvidenceChainManager(
            self.config, self.db_manager, self.storage_manager
        )
        
        # Mobile and field operations
        self.mobile_unit_manager = MobileUnitManager(
            self.config, self.db_manager, self.alert_manager
        )
        
        logger.info("Enterprise managers initialized successfully")
    
    def _initialize_advanced_managers(self):
        """Initialize advanced specialized managers"""
        logger.info("Initializing advanced specialized managers...")
        
        # Next-generation security
        self.cyber_defense_manager = CyberDefenseManager(
            self.config, self.db_manager, self.alert_manager
        )
        self.quantum_security_manager = QuantumSecurityManager(
            self.config, self.db_manager
        )
        
        # Supply chain and compliance
        self.supply_chain_manager = SupplyChainSecurityManager(
            self.config, self.db_manager, self.alert_manager
        )
        self.compliance_manager = ComplianceManager(self.config, self.db_manager)
        
        # Advanced interfaces and collaboration
        self.hci_manager = HCIManager(self.config)
        self.collaboration_manager = CollaborationManager(
            self.config, self.db_manager, self.alert_manager
        )
        
        # Environmental and IoT integration
        self.env_sensing_manager = EnvironmentalSensingManager(self.config)
        
        # Blockchain and immutable ledger
        self.blockchain_ledger_manager = BlockchainLedgerManager(self.config, self.db_manager)
        
        # Simulation and testing
        self.simulation_manager = SimulationManager(
            self.config, self.db_manager, self.alert_manager
        )
        
        # Reporting and visualization
        self.live_map_manager = LiveMapManager(self.config, self.db_manager)
        self.reporting_manager = ReportingManager(self.config, self.db_manager)
        
        # Integration and protocols
        self.onvif_manager = ONVIFManager(self.config)
        
        # API server - Comprehensive REST/GraphQL/WebSocket API
        self.api_server = APIServer(self)
        
        logger.info("Advanced specialized managers initialized successfully")
    
    def _register_services(self):
        """Register all services with the orchestrator"""
        # Core services (Critical priority)
        core_services = [
            ('database', self.db_manager, []),
            ('security', self.security_manager, ['database']),
            ('storage', self.storage_manager, ['database']),
            ('alert', self.alert_manager, ['database']),
            ('system_health', self.system_health_manager, ['database', 'alert'])
        ]
        
        for name, manager, deps in core_services:
            service_info = ServiceInfo(
                name=name,
                manager=manager,
                priority=ServicePriority.CRITICAL,
                depends_on=deps,
                startup_timeout=60,
                restart_policy="always"
            )
            self.orchestrator.register_service(service_info)
            self.services[name] = service_info
        
        # Analytics services (High priority)
        analytics_services = [
            ('ai_engine', self.ai_manager, ['database', 'storage']),
            ('video_analytics', self.video_analytics_manager, ['database', 'ai_engine']),
            ('audio_analytics', self.audio_analytics_manager, ['database', 'ai_engine']),
            ('stream_processor', self.stream_manager, ['database', 'storage', 'ai_engine', 'video_analytics']),
            ('incident_manager', self.incident_manager, ['database', 'alert', 'video_analytics']),
            ('automation', self.automation_manager, ['database'])
        ]
        
        for name, manager, deps in analytics_services:
            service_info = ServiceInfo(
                name=name,
                manager=manager,
                priority=ServicePriority.HIGH,
                depends_on=deps,
                startup_timeout=120,
                restart_policy="always"
            )
            self.orchestrator.register_service(service_info)
            self.services[name] = service_info
        
        # Enterprise services (Normal priority)
        enterprise_services = [
            ('federation', self.federation_manager, ['database', 'security']),
            ('ha_manager', self.ha_manager, ['federation']),
            ('cloud_sync', self.cloud_sync_manager, ['database', 'security']),
            ('predictive_analytics', self.predictive_analytics_manager, ['database', 'ai_engine']),
            ('operational_intelligence', self.operational_intelligence_manager, ['database', 'video_analytics']),
            ('biometrics', self.biometrics_manager, ['database']),
            ('access_control', self.access_control_manager, ['database', 'biometrics']),
            ('forensics', self.forensics_manager, ['database', 'storage']),
            ('evidence_chain', self.evidence_chain_manager, ['database', 'storage', 'forensics']),
            ('mobile_units', self.mobile_unit_manager, ['database', 'alert']),
            ('cyber_defense', self.cyber_defense_manager, ['database', 'security']),
            ('quantum_security', self.quantum_security_manager, ['database']),
            ('supply_chain', self.supply_chain_manager, ['database', 'alert']),
            ('compliance', self.compliance_manager, ['database']),
            ('hci', self.hci_manager, []),
            ('collaboration', self.collaboration_manager, ['database']),
            ('env_sensing', self.env_sensing_manager, []),
            ('blockchain_ledger', self.blockchain_ledger_manager, ['database']),
            ('simulation', self.simulation_manager, ['database']),
            ('live_map', self.live_map_manager, ['database']),
            ('reporting', self.reporting_manager, ['database']),
            ('onvif', self.onvif_manager, []),
            ('api_server', self.api_server, ['database', 'security', 'stream_processor'])
        ]
        
        for name, manager, deps in enterprise_services:
            service_info = ServiceInfo(
                name=name,
                manager=manager,
                priority=ServicePriority.NORMAL,
                depends_on=deps,
                startup_timeout=90,
                restart_policy="on_failure"
            )
            self.orchestrator.register_service(service_info)
            self.services[name] = service_info
    
    async def start(self):
        """Start the complete NVR system"""
        try:
            self.status = SystemStatus.STARTING
            logger.info("=" * 80)
            logger.info("STARTING AGROPULSE AI-NVR ENTERPRISE SYSTEM")
            logger.info("=" * 80)
            
            # Start performance monitoring
            self.performance_monitor.start_monitoring()
            
            # Validate system resources
            await self._validate_system_resources()
            
            # Initialize Kubernetes integration if available
            if KUBERNETES_AVAILABLE:
                await self._initialize_kubernetes()
            
            # Start all services through orchestrator
            await self.orchestrator.start_services()
            
            # Update stream manager references after incident and automation managers are started
            if hasattr(self.stream_manager, 'set_managers'):
                self.stream_manager.set_managers(self.incident_manager, self.automation_manager)
            
            # Perform system health check
            await self._perform_health_check()
            
            self.status = SystemStatus.RUNNING
            
            startup_duration = time.time() - self.startup_time
            logger.info("=" * 80)
            logger.info(f"AI-NVR SYSTEM FULLY OPERATIONAL ({startup_duration:.2f}s startup)")
            logger.info(f"Instance ID: {self.instance_id}")
            logger.info(f"Services Running: {len([s for s in self.services.values() if s.status == 'running'])}")
            logger.info(f"Memory Usage: {psutil.virtual_memory().percent:.1f}%")
            logger.info(f"CPU Count: {multiprocessing.cpu_count()}")
            logger.info("=" * 80)
            
            # Main event loop
            await self._main_loop()
            
        except Exception as e:
            self.status = SystemStatus.FAILED
            logger.error(f"Critical system startup failure: {e}", exc_info=True)
            await self.stop()
            raise
    
    async def _validate_system_resources(self):
        """Validate system has sufficient resources"""
        logger.info("Validating system resources...")
        
        # Check memory
        memory = psutil.virtual_memory()
        min_memory_gb = self.config['system'].get('min_memory_gb', 4)
        
        if memory.total < min_memory_gb * 1024 * 1024 * 1024:
            logger.warning(f"System has {memory.total // 1024 // 1024 // 1024}GB RAM, recommended minimum: {min_memory_gb}GB")
        
        # Check disk space
        storage_path = Path(self.config['storage']['base_path'])
        if storage_path.exists():
            disk_usage = psutil.disk_usage(storage_path)
            min_free_gb = self.config['storage'].get('min_free_gb', 10)
            
            if disk_usage.free < min_free_gb * 1024 * 1024 * 1024:
                logger.warning(f"Storage path has {disk_usage.free // 1024 // 1024 // 1024}GB free, minimum recommended: {min_free_gb}GB")
        
        # Check network connectivity
        await self._check_network_connectivity()
        
        logger.info("System resource validation completed")
    
    async def _check_network_connectivity(self):
        """Check network connectivity for external services"""
        test_hosts = [
            ('8.8.8.8', 53),  # Google DNS
            ('1.1.1.1', 53),  # Cloudflare DNS
        ]
        
        for host, port in test_hosts:
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port), timeout=5
                )
                writer.close()
                await writer.wait_closed()
                logger.debug(f"Network connectivity to {host}:{port} - OK")
                break
            except:
                continue
        else:
            logger.warning("External network connectivity may be limited")
    
    async def _initialize_kubernetes(self):
        """Initialize Kubernetes integration if available"""
        try:
            k8s_config.load_incluster_config()
            logger.info("Kubernetes in-cluster configuration loaded")
        except:
            try:
                k8s_config.load_kube_config()
                logger.info("Kubernetes configuration loaded from kubeconfig")
            except:
                logger.info("Kubernetes not available or not configured")
    
    async def _perform_health_check(self):
        """Perform comprehensive system health check"""
        logger.info("Performing system health check...")
        
        health_results = {}
        
        for service_name, service_info in self.services.items():
            try:
                if hasattr(service_info.manager, 'health_check'):
                    result = await service_info.manager.health_check()
                    health_results[service_name] = result
                else:
                    health_results[service_name] = {'status': 'ok', 'message': 'No health check implemented'}
            except Exception as e:
                health_results[service_name] = {'status': 'error', 'message': str(e)}
        
        failed_services = [name for name, result in health_results.items() 
                          if result.get('status') != 'ok']
        
        if failed_services:
            logger.warning(f"Health check failed for services: {failed_services}")
            self.status = SystemStatus.DEGRADED
        else:
            logger.info("System health check passed - All services operational")
    
    async def _main_loop(self):
        """Main application event loop"""
        logger.info("Entering main system event loop...")
        
        loop_interval = self.config['system'].get('main_loop_interval', 300)  # 5 minutes
        
        try:
            while self.status in [SystemStatus.RUNNING, SystemStatus.DEGRADED]:
                # Periodic health checks
                await self._perform_health_check()
                
                # Memory cleanup
                if self._should_perform_gc():
                    await self._perform_memory_cleanup()
                
                # Configuration reload check
                await self._check_configuration_changes()
                
                # System metrics update
                metrics = self.performance_monitor.get_metrics_summary()
                logger.info(f"System metrics: CPU {metrics['system']['cpu_usage']:.1f}%, "
                           f"Memory {metrics['system']['memory_usage_mb']:.0f}MB, "
                           f"Streams {metrics['application']['active_streams']}")
                
                await asyncio.sleep(loop_interval)
                
        except asyncio.CancelledError:
            logger.info("Main loop cancelled - shutting down")
        except Exception as e:
            logger.error(f"Main loop error: {e}", exc_info=True)
            self.status = SystemStatus.FAILED
    
    def _should_perform_gc(self) -> bool:
        """Determine if garbage collection should be performed"""
        memory = psutil.virtual_memory()
        max_memory_percent = self.config['system'].get('max_memory_percent', 80)
        
        return memory.percent > max_memory_percent
    
    async def _perform_memory_cleanup(self):
        """Perform memory cleanup and garbage collection"""
        logger.info("Performing memory cleanup...")
        
        initial_memory = psutil.virtual_memory().percent
        
        # Force garbage collection
        gc.collect()
        
        # Clear manager caches if available
        for service_name, service_info in self.services.items():
            manager = service_info.manager
            if hasattr(manager, 'clear_cache'):
                await manager.clear_cache()
        
        final_memory = psutil.virtual_memory().percent
        logger.info(f"Memory cleanup completed: {initial_memory:.1f}% -> {final_memory:.1f}%")
    
    async def _check_configuration_changes(self):
        """Check for configuration file changes and reload if necessary"""
        try:
            if self.config_manager.config_path.exists():
                current_modified = self.config_manager.config_path.stat().st_mtime
                
                if current_modified > self.config_manager.last_modified:
                    logger.info("Configuration file changed, reloading...")
                    await self._reload_configuration()
        except Exception as e:
            logger.error(f"Configuration change check error: {e}")
    
    async def _reload_configuration(self):
        """Reload system configuration"""
        try:
            new_config = self.config_manager.load_config()
            
            # Update configuration for managers that support hot reload
            for service_name, service_info in self.services.items():
                manager = service_info.manager
                if hasattr(manager, 'reload_config'):
                    await manager.reload_config(new_config.get(service_name, {}))
            
            self.config = new_config
            logger.info("Configuration reloaded successfully")
            
        except Exception as e:
            logger.error(f"Configuration reload failed: {e}")
    
    async def stop(self):
        """Stop the complete NVR system"""
        self.status = SystemStatus.STOPPING
        logger.info("Initiating graceful system shutdown...")
        
        try:
            # Stop performance monitoring
            self.performance_monitor.stop_monitoring()
            
            # Stop all services through orchestrator
            await self.orchestrator.stop_services()
            
            # Shutdown executors
            logger.info("Shutting down thread pools...")
            self.executor.shutdown(wait=True, timeout=30)
            self.process_executor.shutdown(wait=True, timeout=30)
            
            self.status = SystemStatus.STOPPED
            
            shutdown_duration = time.time() - self.startup_time
            logger.info("=" * 80)
            logger.info(f"AI-NVR SYSTEM SHUTDOWN COMPLETE ({shutdown_duration:.2f}s total runtime)")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"Error during system shutdown: {e}", exc_info=True)
            self.status = SystemStatus.FAILED
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            'instance_id': self.instance_id,
            'status': self.status.value,
            'startup_time': self.startup_time,
            'uptime': time.time() - self.startup_time,
            'services': self.orchestrator.get_service_status(),
            'metrics': self.performance_monitor.get_metrics_summary(),
            'platform': {
                'system': platform.system(),
                'release': platform.release(),
                'python_version': sys.version,
                'cpu_count': multiprocessing.cpu_count(),
                'memory_gb': psutil.virtual_memory().total // 1024 // 1024 // 1024
            }
        }

# Global logger configuration after imports
logger = logging.getLogger("NVR_Main")

if __name__ == "__main__":
    """Main entry point with comprehensive error handling and resource management"""
    
    # Set process title if available
    try:
        import setproctitle
        setproctitle.setproctitle("agropulse-nvr-enterprise")
    except ImportError:
        pass
    
    # Increase resource limits if running as root/admin
    try:
        if os.getuid() == 0:  # Running as root
            # Increase file descriptor limit
            resource.setrlimit(resource.RLIMIT_NOFILE, (65536, 65536))
            
            # Increase memory lock limit for better performance
            resource.setrlimit(resource.RLIMIT_MEMLOCK, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
            
            logger.info("Increased system resource limits for optimal performance")
    except (AttributeError, OSError):
        pass  # Not on Unix or insufficient permissions
    
    # Ensure configuration directory exists
    config_dir = Path('config')
    config_dir.mkdir(exist_ok=True)
    
    config_file = config_dir / 'nvr_config.yml'
    
    # Create configuration from template if needed
    if not config_file.exists():
        template_file = config_dir / 'nvr_config.template.yml'
        if template_file.exists():
            import shutil
            shutil.copy(template_file, config_file)
            logger.info(f"Created configuration file from template: {config_file}")
        else:
            # Will create default config in ConfigurationManager
            logger.info("No configuration found, will create default configuration")
    
    # Initialize and start the NVR system
    nvr_system = None
    exit_code = 0
    
    try:
        # Create NVR system instance
        nvr_system = NVRSystem(config_path=str(config_file))
        
        # Start the system
        logger.info("Starting AgroPulse AI-NVR Enterprise System...")
        asyncio.run(nvr_system.start())
        
    except KeyboardInterrupt:
        logger.info("Shutdown signal received (Ctrl+C)")
        exit_code = 0
        
    except SystemExit as e:
        logger.info(f"System exit requested: {e}")
        exit_code = e.code
        
    except Exception as e:
        logger.error(f"Fatal system error: {e}", exc_info=True)
        exit_code = 1
        
    finally:
        # Ensure proper cleanup
        if nvr_system:
            try:
                if asyncio.get_event_loop().is_running():
                    asyncio.create_task(nvr_system.stop())
                else:
                    asyncio.run(nvr_system.stop())
            except Exception as e:
                logger.error(f"Error during final cleanup: {e}")
                exit_code = 1
        
        # Final resource cleanup
        try:
            # Close all asyncio tasks
            pending_tasks = [task for task in asyncio.all_tasks() if not task.done()]
            if pending_tasks:
                logger.info(f"Cancelling {len(pending_tasks)} pending tasks...")
                for task in pending_tasks:
                    task.cancel()
        except:
            pass
        
        logger.info(f"System exit with code: {exit_code}")
        sys.exit(exit_code)
