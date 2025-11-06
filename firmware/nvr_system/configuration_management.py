# ======================================================================================================================
# AgroPulse NVR - Configuration Management & Settings
# Centralized configuration, environment management, and runtime settings
# ======================================================================================================================

import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ======================================================================================================================
# CONFIGURATION DATACLASSES
# ======================================================================================================================

@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str = "localhost"
    port: int = 5432
    database: str = "agropulse"
    username: str = "postgres"
    password: str = ""
    pool_size: int = 20
    max_overflow: int = 10
    ssl_mode: str = "prefer"
    connect_timeout: int = 30
    command_timeout: int = 60
    
@dataclass
class RedisConfig:
    """Redis cache configuration"""
    host: str = "localhost"
    port: int = 6379
    password: str = ""
    db: int = 0
    max_connections: int = 50
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    
@dataclass
class GeminiConfig:
    """Gemini AI configuration"""
    api_key: str = ""
    model_name: str = "gemini-1.5-pro"
    vision_model: str = "gemini-pro-vision"
    temperature: float = 0.3
    top_p: float = 0.95
    top_k: int = 40
    max_output_tokens: int = 2048
    request_timeout: int = 60
    rate_limit_requests_per_minute: int = 60
    
@dataclass
class VideoConfig:
    """Video processing configuration"""
    max_streams: int = 64
    default_fps: int = 30
    frame_buffer_size: int = 30
    rtsp_transport: str = "tcp"
    codec: str = "h264"
    resolution_width: int = 1920
    resolution_height: int = 1080
    bitrate_kbps: int = 4000
    keyframe_interval: int = 30
    recording_enabled: bool = True
    recording_path: str = "./recordings"
    retention_days: int = 30
    
@dataclass
class MLConfig:
    """Machine learning configuration"""
    models_dir: str = "./models"
    device: str = "cuda"  # cuda, cpu, mps
    batch_size: int = 1
    num_workers: int = 4
    fp16_enabled: bool = True
    confidence_threshold: float = 0.7
    nms_threshold: float = 0.45
    max_detections: int = 100
    warmup_iterations: int = 10
    
@dataclass
class ESP32Config:
    """ESP32 device configuration"""
    heartbeat_interval: int = 30
    heartbeat_timeout: int = 90
    firmware_update_url: str = "http://localhost:8080/firmware"
    command_timeout: int = 10
    max_retry_attempts: int = 3
    telemetry_interval: int = 60
    
@dataclass
class APIConfig:
    """API server configuration"""
    host: str = "0.0.0.0"
    port: int = 8080
    ssl_enabled: bool = False
    ssl_cert_path: str = ""
    ssl_key_path: str = ""
    cors_enabled: bool = True
    cors_origins: List[str] = None
    max_request_size_mb: int = 100
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    
    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["*"]
            
@dataclass
class MonitoringConfig:
    """System monitoring configuration"""
    enabled: bool = True
    check_interval: int = 5
    metrics_retention_hours: int = 24
    alert_cpu_threshold: float = 90.0
    alert_memory_threshold: float = 85.0
    alert_disk_threshold: float = 90.0
    alert_enabled: bool = True
    alert_email: List[str] = None
    
    def __post_init__(self):
        if self.alert_email is None:
            self.alert_email = []
            
@dataclass
class StorageConfig:
    """Storage configuration"""
    base_path: str = "./storage"
    images_path: str = "./storage/images"
    videos_path: str = "./storage/videos"
    logs_path: str = "./storage/logs"
    backups_path: str = "./storage/backups"
    temp_path: str = "./storage/temp"
    max_storage_gb: int = 1000
    cleanup_enabled: bool = True
    cleanup_interval_hours: int = 24
    
@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_enabled: bool = True
    file_path: str = "./logs/agropulse.log"
    file_max_bytes: int = 10485760  # 10MB
    file_backup_count: int = 5
    console_enabled: bool = True
    json_format: bool = False
    
@dataclass
class SecurityConfig:
    """Security configuration"""
    encryption_enabled: bool = True
    encryption_key: str = ""
    password_min_length: int = 8
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_numbers: bool = True
    password_require_special: bool = True
    session_timeout_minutes: int = 30
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    
@dataclass
class NotificationConfig:
    """Notification configuration"""
    email_enabled: bool = False
    email_smtp_host: str = ""
    email_smtp_port: int = 587
    email_username: str = ""
    email_password: str = ""
    email_from: str = ""
    sms_enabled: bool = False
    sms_provider: str = "twilio"
    sms_account_sid: str = ""
    sms_auth_token: str = ""
    sms_from_number: str = ""
    push_enabled: bool = True
    fcm_server_key: str = ""

# ======================================================================================================================
# MAIN CONFIGURATION CLASS
# ======================================================================================================================

@dataclass
class AgroPulseConfig:
    """Main AgroPulse configuration"""
    environment: str = "development"  # development, staging, production
    version: str = "1.0.0"
    debug: bool = False
    database: DatabaseConfig = None
    redis: RedisConfig = None
    gemini: GeminiConfig = None
    video: VideoConfig = None
    ml: MLConfig = None
    esp32: ESP32Config = None
    api: APIConfig = None
    monitoring: MonitoringConfig = None
    storage: StorageConfig = None
    logging: LoggingConfig = None
    security: SecurityConfig = None
    notification: NotificationConfig = None
    
    def __post_init__(self):
        if self.database is None:
            self.database = DatabaseConfig()
        if self.redis is None:
            self.redis = RedisConfig()
        if self.gemini is None:
            self.gemini = GeminiConfig()
        if self.video is None:
            self.video = VideoConfig()
        if self.ml is None:
            self.ml = MLConfig()
        if self.esp32 is None:
            self.esp32 = ESP32Config()
        if self.api is None:
            self.api = APIConfig()
        if self.monitoring is None:
            self.monitoring = MonitoringConfig()
        if self.storage is None:
            self.storage = StorageConfig()
        if self.logging is None:
            self.logging = LoggingConfig()
        if self.security is None:
            self.security = SecurityConfig()
        if self.notification is None:
            self.notification = NotificationConfig()

# ======================================================================================================================
# CONFIGURATION MANAGER
# ======================================================================================================================

class ConfigManager:
    """Manages application configuration"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = Path(config_file)
        self.config: Optional[AgroPulseConfig] = None
        self._config_watchers = []
        
    def load_config(self) -> AgroPulseConfig:
        """Load configuration from file"""
        if self.config_file.exists():
            logger.info(f"[CONFIG] Loading configuration from {self.config_file}")
            
            with open(self.config_file, 'r') as f:
                if self.config_file.suffix == '.yaml' or self.config_file.suffix == '.yml':
                    data = yaml.safe_load(f)
                elif self.config_file.suffix == '.json':
                    data = json.load(f)
                else:
                    raise ValueError(f"Unsupported config file format: {self.config_file.suffix}")
            
            self.config = self._dict_to_config(data)
        else:
            logger.warning(f"[CONFIG] Config file not found, using defaults")
            self.config = AgroPulseConfig()
        
        # Override with environment variables
        self._apply_env_overrides()
        
        # Validate configuration
        self._validate_config()
        
        logger.info(f"[CONFIG] Configuration loaded: {self.config.environment} environment")
        return self.config
    
    def _dict_to_config(self, data: Dict) -> AgroPulseConfig:
        """Convert dictionary to config dataclass"""
        config_dict = {}
        
        # Parse each section
        if 'database' in data:
            config_dict['database'] = DatabaseConfig(**data['database'])
        if 'redis' in data:
            config_dict['redis'] = RedisConfig(**data['redis'])
        if 'gemini' in data:
            config_dict['gemini'] = GeminiConfig(**data['gemini'])
        if 'video' in data:
            config_dict['video'] = VideoConfig(**data['video'])
        if 'ml' in data:
            config_dict['ml'] = MLConfig(**data['ml'])
        if 'esp32' in data:
            config_dict['esp32'] = ESP32Config(**data['esp32'])
        if 'api' in data:
            config_dict['api'] = APIConfig(**data['api'])
        if 'monitoring' in data:
            config_dict['monitoring'] = MonitoringConfig(**data['monitoring'])
        if 'storage' in data:
            config_dict['storage'] = StorageConfig(**data['storage'])
        if 'logging' in data:
            config_dict['logging'] = LoggingConfig(**data['logging'])
        if 'security' in data:
            config_dict['security'] = SecurityConfig(**data['security'])
        if 'notification' in data:
            config_dict['notification'] = NotificationConfig(**data['notification'])
        
        # Top-level fields
        for field in ['environment', 'version', 'debug']:
            if field in data:
                config_dict[field] = data[field]
        
        return AgroPulseConfig(**config_dict)
    
    def _apply_env_overrides(self):
        """Override config with environment variables"""
        # Database
        if os.getenv('DB_HOST'):
            self.config.database.host = os.getenv('DB_HOST')
        if os.getenv('DB_PORT'):
            self.config.database.port = int(os.getenv('DB_PORT'))
        if os.getenv('DB_NAME'):
            self.config.database.database = os.getenv('DB_NAME')
        if os.getenv('DB_USER'):
            self.config.database.username = os.getenv('DB_USER')
        if os.getenv('DB_PASSWORD'):
            self.config.database.password = os.getenv('DB_PASSWORD')
        
        # Redis
        if os.getenv('REDIS_HOST'):
            self.config.redis.host = os.getenv('REDIS_HOST')
        if os.getenv('REDIS_PORT'):
            self.config.redis.port = int(os.getenv('REDIS_PORT'))
        if os.getenv('REDIS_PASSWORD'):
            self.config.redis.password = os.getenv('REDIS_PASSWORD')
        
        # Gemini
        if os.getenv('GEMINI_API_KEY'):
            self.config.gemini.api_key = os.getenv('GEMINI_API_KEY')
        
        # API
        if os.getenv('API_HOST'):
            self.config.api.host = os.getenv('API_HOST')
        if os.getenv('API_PORT'):
            self.config.api.port = int(os.getenv('API_PORT'))
        if os.getenv('JWT_SECRET'):
            self.config.api.jwt_secret_key = os.getenv('JWT_SECRET')
        
        # Security
        if os.getenv('ENCRYPTION_KEY'):
            self.config.security.encryption_key = os.getenv('ENCRYPTION_KEY')
        
        # Environment
        if os.getenv('ENVIRONMENT'):
            self.config.environment = os.getenv('ENVIRONMENT')
        if os.getenv('DEBUG'):
            self.config.debug = os.getenv('DEBUG').lower() == 'true'
    
    def _validate_config(self):
        """Validate configuration"""
        errors = []
        
        # Database validation
        if not self.config.database.host:
            errors.append("Database host is required")
        if not self.config.database.database:
            errors.append("Database name is required")
        
        # Gemini validation
        if not self.config.gemini.api_key and self.config.environment == 'production':
            errors.append("Gemini API key is required in production")
        
        # API validation
        if not self.config.api.jwt_secret_key and self.config.environment == 'production':
            errors.append("JWT secret key is required in production")
        
        # Security validation
        if not self.config.security.encryption_key and self.config.security.encryption_enabled:
            errors.append("Encryption key is required when encryption is enabled")
        
        if errors:
            raise ValueError(f"Configuration validation failed:\n" + "\n".join(f"- {e}" for e in errors))
    
    def save_config(self, filepath: Optional[str] = None):
        """Save configuration to file"""
        if filepath:
            output_path = Path(filepath)
        else:
            output_path = self.config_file
        
        # Convert to dictionary
        config_dict = self._config_to_dict(self.config)
        
        # Save
        with open(output_path, 'w') as f:
            if output_path.suffix == '.yaml' or output_path.suffix == '.yml':
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            elif output_path.suffix == '.json':
                json.dump(config_dict, f, indent=2)
        
        logger.info(f"[CONFIG] Configuration saved to {output_path}")
    
    def _config_to_dict(self, config: AgroPulseConfig) -> Dict:
        """Convert config to dictionary"""
        return {
            'environment': config.environment,
            'version': config.version,
            'debug': config.debug,
            'database': asdict(config.database),
            'redis': asdict(config.redis),
            'gemini': asdict(config.gemini),
            'video': asdict(config.video),
            'ml': asdict(config.ml),
            'esp32': asdict(config.esp32),
            'api': asdict(config.api),
            'monitoring': asdict(config.monitoring),
            'storage': asdict(config.storage),
            'logging': asdict(config.logging),
            'security': asdict(config.security),
            'notification': asdict(config.notification)
        }
    
    def get_config(self) -> AgroPulseConfig:
        """Get current configuration"""
        if self.config is None:
            self.load_config()
        return self.config
    
    def update_config(self, section: str, key: str, value: Any):
        """Update configuration value"""
        if self.config is None:
            self.load_config()
        
        section_obj = getattr(self.config, section, None)
        if section_obj is None:
            raise ValueError(f"Unknown config section: {section}")
        
        if not hasattr(section_obj, key):
            raise ValueError(f"Unknown config key: {section}.{key}")
        
        setattr(section_obj, key, value)
        logger.info(f"[CONFIG] Updated {section}.{key} = {value}")
        
        # Notify watchers
        self._notify_watchers(section, key, value)
    
    def register_watcher(self, callback):
        """Register config change watcher"""
        self._config_watchers.append(callback)
    
    def _notify_watchers(self, section: str, key: str, value: Any):
        """Notify watchers of config change"""
        for watcher in self._config_watchers:
            try:
                watcher(section, key, value)
            except Exception as e:
                logger.error(f"[CONFIG] Watcher error: {e}")

# ======================================================================================================================
# ENVIRONMENT PROFILES
# ======================================================================================================================

class EnvironmentProfiles:
    """Predefined environment profiles"""
    
    @staticmethod
    def development() -> AgroPulseConfig:
        """Development environment profile"""
        return AgroPulseConfig(
            environment="development",
            debug=True,
            database=DatabaseConfig(
                host="localhost",
                port=5432,
                database="agropulse_dev",
                pool_size=5
            ),
            redis=RedisConfig(
                host="localhost",
                port=6379
            ),
            api=APIConfig(
                host="localhost",
                port=8080,
                cors_enabled=True,
                cors_origins=["*"]
            ),
            logging=LoggingConfig(
                level="DEBUG",
                console_enabled=True
            )
        )
    
    @staticmethod
    def staging() -> AgroPulseConfig:
        """Staging environment profile"""
        return AgroPulseConfig(
            environment="staging",
            debug=False,
            database=DatabaseConfig(
                host="staging-db.example.com",
                port=5432,
                database="agropulse_staging",
                pool_size=10,
                ssl_mode="require"
            ),
            redis=RedisConfig(
                host="staging-redis.example.com",
                port=6379
            ),
            api=APIConfig(
                host="0.0.0.0",
                port=8080,
                ssl_enabled=True,
                rate_limit_enabled=True
            ),
            logging=LoggingConfig(
                level="INFO",
                file_enabled=True,
                console_enabled=True
            )
        )
    
    @staticmethod
    def production() -> AgroPulseConfig:
        """Production environment profile"""
        return AgroPulseConfig(
            environment="production",
            debug=False,
            database=DatabaseConfig(
                host="prod-db.example.com",
                port=5432,
                database="agropulse_prod",
                pool_size=20,
                max_overflow=10,
                ssl_mode="require"
            ),
            redis=RedisConfig(
                host="prod-redis.example.com",
                port=6379,
                max_connections=100
            ),
            api=APIConfig(
                host="0.0.0.0",
                port=443,
                ssl_enabled=True,
                rate_limit_enabled=True,
                rate_limit_requests=60
            ),
            monitoring=MonitoringConfig(
                enabled=True,
                alert_enabled=True
            ),
            logging=LoggingConfig(
                level="WARNING",
                file_enabled=True,
                console_enabled=False,
                json_format=True
            ),
            security=SecurityConfig(
                encryption_enabled=True,
                session_timeout_minutes=15
            )
        )

# ======================================================================================================================
# FEATURE FLAGS
# ======================================================================================================================

class FeatureFlags:
    """Feature flag management"""
    
    def __init__(self):
        self.flags: Dict[str, bool] = {
            'gemini_ai_enabled': True,
            'advanced_scan_enabled': True,
            'mesh_networking_enabled': True,
            'ar_integration_enabled': True,
            'predictive_analytics_enabled': False,
            'auto_task_assignment_enabled': True,
            'mobile_app_enabled': True,
            'email_notifications_enabled': False,
            'sms_notifications_enabled': False,
            'push_notifications_enabled': True,
            'video_recording_enabled': True,
            'real_time_streaming_enabled': True,
            'batch_processing_enabled': True,
            'model_retraining_enabled': False,
            'multi_farm_support_enabled': True
        }
    
    def is_enabled(self, flag_name: str) -> bool:
        """Check if feature is enabled"""
        return self.flags.get(flag_name, False)
    
    def enable(self, flag_name: str):
        """Enable feature"""
        self.flags[flag_name] = True
        logger.info(f"[FEATURES] Enabled: {flag_name}")
    
    def disable(self, flag_name: str):
        """Disable feature"""
        self.flags[flag_name] = False
        logger.info(f"[FEATURES] Disabled: {flag_name}")
    
    def get_all_flags(self) -> Dict[str, bool]:
        """Get all feature flags"""
        return self.flags.copy()
    
    def load_from_dict(self, flags: Dict[str, bool]):
        """Load flags from dictionary"""
        self.flags.update(flags)

# ======================================================================================================================
# SETTINGS VALIDATOR
# ======================================================================================================================

class SettingsValidator:
    """Validates configuration settings"""
    
    @staticmethod
    def validate_port(port: int) -> bool:
        """Validate port number"""
        return 1 <= port <= 65535
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email address"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL"""
        import re
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return re.match(pattern, url) is not None
    
    @staticmethod
    def validate_path(path: str, must_exist: bool = False) -> bool:
        """Validate file path"""
        p = Path(path)
        if must_exist:
            return p.exists()
        return True
    
    @staticmethod
    def validate_percentage(value: float) -> bool:
        """Validate percentage value"""
        return 0.0 <= value <= 100.0
    
    @staticmethod
    def validate_positive_integer(value: int) -> bool:
        """Validate positive integer"""
        return isinstance(value, int) and value > 0

# ======================================================================================================================
# CONFIGURATION TEMPLATES
# ======================================================================================================================

class ConfigTemplates:
    """Configuration file templates"""
    
    @staticmethod
    def generate_default_yaml() -> str:
        """Generate default YAML configuration"""
        config = AgroPulseConfig()
        manager = ConfigManager()
        config_dict = manager._config_to_dict(config)
        return yaml.dump(config_dict, default_flow_style=False, indent=2)
    
    @staticmethod
    def generate_docker_compose_config() -> str:
        """Generate Docker Compose configuration"""
        return """
version: '3.8'

services:
  agropulse-nvr:
    build: .
    ports:
      - "8080:8080"
    environment:
      - ENVIRONMENT=production
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=agropulse
      - DB_USER=postgres
      - DB_PASSWORD=${DB_PASSWORD}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    depends_on:
      - postgres
      - redis
    volumes:
      - ./storage:/app/storage
      - ./models:/app/models
    restart: unless-stopped
  
  postgres:
    image: postgis/postgis:15-3.3
    environment:
      - POSTGRES_DB=agropulse
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
"""
    
    @staticmethod
    def generate_env_template() -> str:
        """Generate .env template"""
        return """# AgroPulse Environment Variables

# Environment
ENVIRONMENT=development
DEBUG=true

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=agropulse
DB_USER=postgres
DB_PASSWORD=your_secure_password_here

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Gemini AI
GEMINI_API_KEY=your_api_key_here

# API
API_HOST=0.0.0.0
API_PORT=8080
JWT_SECRET=your_jwt_secret_here

# Security
ENCRYPTION_KEY=your_encryption_key_here

# Notifications
FCM_SERVER_KEY=your_fcm_key_here
"""

# ======================================================================================================================
# END OF CONFIGURATION MANAGEMENT MODULE
# Lines in this file: ~800+
# Combined total: ~10,400+
# Remaining for 50k: ~39,600 lines
# ======================================================================================================================
