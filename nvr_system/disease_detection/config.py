"""
Configuration Management System
================================

Centralized configuration for AgroPulse disease detection system.
Manages API keys, detection modes, caching, rate limits, and output preferences.

Features:
- Environment variable support
- JSON config file support
- Validation and defaults
- Production/development profiles

Usage:
    config = DetectionConfig.load()
    detector = UnifiedDiseaseDetector(
        kindwise_api_key=config.kindwise_api_key,
        mode=config.detection_mode,
        enable_cache=config.enable_cache
    )

Author: AgroPulse Team
Date: November 2025
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict, field
from enum import Enum


class DetectionModeConfig(Enum):
    """Detection mode configuration"""
    RULE_BASED_ONLY = "rule_based"
    AI_ONLY = "ai_only"
    HYBRID_FAST = "hybrid_fast"
    HYBRID_COMPREHENSIVE = "hybrid_comprehensive"
    AUTO = "auto"


class EnvironmentProfile(Enum):
    """Environment profiles with different defaults"""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    OFFLINE = "offline"
    TESTING = "testing"


@dataclass
class KindwiseConfig:
    """Kindwise API configuration"""
    api_key: Optional[str] = None
    base_url: str = "https://crop.kindwise.com/api/v1"
    timeout_seconds: int = 30
    max_requests_per_minute: int = 60
    max_requests_per_day: int = 5000
    enable_caching: bool = True
    cache_dir: str = "./kindwise_cache"
    cache_expiry_days: int = 7
    
    def validate(self) -> bool:
        """Validate configuration"""
        if not self.api_key:
            print("⚠️  Warning: No Kindwise API key configured")
            return False
        
        if self.timeout_seconds < 5 or self.timeout_seconds > 120:
            print("⚠️  Warning: Unusual timeout setting")
            
        return True


@dataclass
class DetectionConfig:
    """Disease detection configuration"""
    detection_mode: DetectionModeConfig = DetectionModeConfig.AUTO
    confidence_threshold: float = 0.7  # Minimum for rule-based acceptance
    enable_differential_diagnosis: bool = True
    max_alternative_diseases: int = 3
    enable_resistance_lookup: bool = True
    enable_economic_impact: bool = True
    enable_forecasting: bool = True


@dataclass
class CacheConfig:
    """Caching configuration"""
    enable_cache: bool = True
    cache_dir: str = "./detection_cache"
    max_cache_size_mb: int = 1000
    cache_expiry_hours: int = 168  # 7 days
    cache_images: bool = False  # Don't cache images (large)
    cache_api_responses: bool = True


@dataclass
class OutputConfig:
    """Output formatting configuration"""
    format: str = "json"  # json, text, pdf
    language: str = "en"
    include_eppo_codes: bool = True
    include_treatments: bool = True
    include_images: bool = False
    include_confidence_scores: bool = True
    farmer_friendly: bool = True
    technical_details: bool = False


@dataclass
class APIConfig:
    """API server configuration"""
    host: str = "0.0.0.0"
    port: int = 8000
    enable_cors: bool = True
    max_upload_size_mb: int = 10
    rate_limit_per_minute: int = 100
    enable_auth: bool = False
    auth_token: Optional[str] = None


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    log_to_file: bool = True
    log_dir: str = "./logs"
    log_api_calls: bool = True
    log_detections: bool = True
    log_errors: bool = True


@dataclass
class DetectionSystemConfig:
    """
    Complete system configuration
    
    Profiles:
    - development: Fast iteration, verbose logging, caching enabled
    - production: Hybrid mode, rate limiting, security enabled
    - offline: Rule-based only, no API calls
    - testing: Mock mode, no external dependencies
    """
    
    # Profile
    profile: EnvironmentProfile = EnvironmentProfile.DEVELOPMENT
    
    # Component configs
    kindwise: KindwiseConfig = field(default_factory=KindwiseConfig)
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    api: APIConfig = field(default_factory=APIConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # System settings
    enable_gpu: bool = False
    num_workers: int = 4
    batch_size: int = 1
    
    @classmethod
    def load(cls, 
             config_file: Optional[str] = None,
             profile: Optional[EnvironmentProfile] = None) -> "DetectionSystemConfig":
        """
        Load configuration from file and environment variables
        
        Priority:
        1. Environment variables (highest)
        2. Config file
        3. Profile defaults
        4. Default values (lowest)
        
        Args:
            config_file: Path to JSON config file
            profile: Environment profile (development, production, offline, testing)
        
        Returns:
            Loaded configuration
        """
        # Start with defaults
        config = cls()
        
        # Apply profile defaults
        if profile:
            config = cls._apply_profile(config, profile)
        
        # Load from config file if provided
        if config_file and Path(config_file).exists():
            config = cls._load_from_file(config, config_file)
        
        # Override with environment variables
        config = cls._load_from_env(config)
        
        # Validate
        config.validate()
        
        return config
    
    @classmethod
    def _apply_profile(cls, 
                       config: "DetectionSystemConfig", 
                       profile: EnvironmentProfile) -> "DetectionSystemConfig":
        """Apply profile-specific defaults"""
        config.profile = profile
        
        if profile == EnvironmentProfile.DEVELOPMENT:
            # Fast iteration, verbose
            config.detection.detection_mode = DetectionModeConfig.HYBRID_FAST
            config.cache.enable_cache = True
            config.logging.level = "DEBUG"
            config.logging.log_api_calls = True
            config.api.enable_auth = False
            
        elif profile == EnvironmentProfile.PRODUCTION:
            # Secure, comprehensive
            config.detection.detection_mode = DetectionModeConfig.HYBRID_COMPREHENSIVE
            config.cache.enable_cache = True
            config.logging.level = "INFO"
            config.logging.log_to_file = True
            config.api.enable_auth = True
            config.api.rate_limit_per_minute = 100
            
        elif profile == EnvironmentProfile.OFFLINE:
            # No external dependencies
            config.detection.detection_mode = DetectionModeConfig.RULE_BASED_ONLY
            config.kindwise.enable_caching = False
            config.cache.enable_cache = True  # Local cache still useful
            config.logging.level = "INFO"
            
        elif profile == EnvironmentProfile.TESTING:
            # Mock mode, no real API calls
            config.detection.detection_mode = DetectionModeConfig.RULE_BASED_ONLY
            config.cache.enable_cache = False
            config.logging.level = "DEBUG"
            config.kindwise.api_key = "test_key_mock"
        
        return config
    
    @classmethod
    def _load_from_file(cls, 
                       config: "DetectionSystemConfig", 
                       config_file: str) -> "DetectionSystemConfig":
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                data = json.load(f)
            
            # Update config from file data
            if 'kindwise' in data:
                for key, value in data['kindwise'].items():
                    if hasattr(config.kindwise, key):
                        setattr(config.kindwise, key, value)
            
            if 'detection' in data:
                for key, value in data['detection'].items():
                    if hasattr(config.detection, key):
                        if key == 'detection_mode':
                            value = DetectionModeConfig(value)
                        setattr(config.detection, key, value)
            
            if 'cache' in data:
                for key, value in data['cache'].items():
                    if hasattr(config.cache, key):
                        setattr(config.cache, key, value)
            
            if 'output' in data:
                for key, value in data['output'].items():
                    if hasattr(config.output, key):
                        setattr(config.output, key, value)
            
            if 'api' in data:
                for key, value in data['api'].items():
                    if hasattr(config.api, key):
                        setattr(config.api, key, value)
            
            if 'logging' in data:
                for key, value in data['logging'].items():
                    if hasattr(config.logging, key):
                        setattr(config.logging, key, value)
            
            print(f"✓ Configuration loaded from {config_file}")
            
        except Exception as e:
            print(f"⚠️  Error loading config file: {e}")
        
        return config
    
    @classmethod
    def _load_from_env(cls, config: "DetectionSystemConfig") -> "DetectionSystemConfig":
        """Load configuration from environment variables"""
        
        # Kindwise API
        if os.getenv("KINDWISE_API_KEY"):
            config.kindwise.api_key = os.getenv("KINDWISE_API_KEY")
        
        if os.getenv("KINDWISE_BASE_URL"):
            config.kindwise.base_url = os.getenv("KINDWISE_BASE_URL")
        
        # Detection mode
        if os.getenv("DETECTION_MODE"):
            try:
                config.detection.detection_mode = DetectionModeConfig(
                    os.getenv("DETECTION_MODE")
                )
            except ValueError:
                print(f"⚠️  Invalid DETECTION_MODE: {os.getenv('DETECTION_MODE')}")
        
        # Cache
        if os.getenv("ENABLE_CACHE"):
            config.cache.enable_cache = os.getenv("ENABLE_CACHE").lower() == "true"
        
        if os.getenv("CACHE_DIR"):
            config.cache.cache_dir = os.getenv("CACHE_DIR")
        
        # API
        if os.getenv("API_HOST"):
            config.api.host = os.getenv("API_HOST")
        
        if os.getenv("API_PORT"):
            try:
                config.api.port = int(os.getenv("API_PORT"))
            except ValueError:
                print(f"⚠️  Invalid API_PORT: {os.getenv('API_PORT')}")
        
        if os.getenv("API_AUTH_TOKEN"):
            config.api.auth_token = os.getenv("API_AUTH_TOKEN")
            config.api.enable_auth = True
        
        # Logging
        if os.getenv("LOG_LEVEL"):
            config.logging.level = os.getenv("LOG_LEVEL")
        
        if os.getenv("LOG_DIR"):
            config.logging.log_dir = os.getenv("LOG_DIR")
        
        return config
    
    def validate(self) -> bool:
        """Validate entire configuration"""
        valid = True
        
        # Validate Kindwise config
        if self.detection.detection_mode != DetectionModeConfig.RULE_BASED_ONLY:
            if not self.kindwise.validate():
                print("⚠️  AI detection requested but Kindwise not configured properly")
                print("   Falling back to rule-based only mode")
                self.detection.detection_mode = DetectionModeConfig.RULE_BASED_ONLY
        
        # Validate confidence threshold
        if self.detection.confidence_threshold < 0 or self.detection.confidence_threshold > 1:
            print(f"⚠️  Invalid confidence_threshold: {self.detection.confidence_threshold}")
            self.detection.confidence_threshold = 0.7
            valid = False
        
        # Validate cache settings
        if self.cache.max_cache_size_mb < 100:
            print(f"⚠️  Cache size very small: {self.cache.max_cache_size_mb}MB")
        
        # Validate API port
        if self.api.port < 1024 or self.api.port > 65535:
            print(f"⚠️  Invalid API port: {self.api.port}")
            self.api.port = 8000
            valid = False
        
        # Create directories
        self._ensure_directories()
        
        return valid
    
    def _ensure_directories(self):
        """Create required directories"""
        dirs = [
            self.kindwise.cache_dir,
            self.cache.cache_dir,
            self.logging.log_dir
        ]
        
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    def save(self, config_file: str):
        """Save configuration to JSON file"""
        try:
            # Convert to dict
            data = {
                'profile': self.profile.value,
                'kindwise': asdict(self.kindwise),
                'detection': {
                    **asdict(self.detection),
                    'detection_mode': self.detection.detection_mode.value
                },
                'cache': asdict(self.cache),
                'output': asdict(self.output),
                'api': asdict(self.api),
                'logging': asdict(self.logging),
                'enable_gpu': self.enable_gpu,
                'num_workers': self.num_workers,
                'batch_size': self.batch_size
            }
            
            with open(config_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"✓ Configuration saved to {config_file}")
            
        except Exception as e:
            print(f"❌ Error saving config: {e}")
    
    def print_summary(self):
        """Print configuration summary"""
        print("\n" + "=" * 60)
        print("AGROPULSE DISEASE DETECTION CONFIGURATION")
        print("=" * 60)
        print(f"Profile: {self.profile.value}")
        print(f"\nDetection Mode: {self.detection.detection_mode.value}")
        print(f"Confidence Threshold: {self.detection.confidence_threshold:.0%}")
        print(f"AI Available: {'Yes' if self.kindwise.api_key else 'No (rule-based only)'}")
        print(f"Cache Enabled: {'Yes' if self.cache.enable_cache else 'No'}")
        print(f"Cache Directory: {self.cache.cache_dir}")
        print(f"\nAPI Server: {self.api.host}:{self.api.port}")
        print(f"Authentication: {'Enabled' if self.api.enable_auth else 'Disabled'}")
        print(f"CORS: {'Enabled' if self.api.enable_cors else 'Disabled'}")
        print(f"\nLogging Level: {self.logging.level}")
        print(f"Log Directory: {self.logging.log_dir}")
        print(f"Log to File: {'Yes' if self.logging.log_to_file else 'No'}")
        print("=" * 60 + "\n")


# Convenience functions
def load_config(config_file: Optional[str] = None, 
                profile: str = "development") -> DetectionSystemConfig:
    """
    Quick config loader
    
    Usage:
        config = load_config()  # Development defaults
        config = load_config(profile="production")  # Production settings
        config = load_config("my_config.json")  # From file
    """
    profile_enum = EnvironmentProfile(profile)
    return DetectionSystemConfig.load(config_file=config_file, profile=profile_enum)


def create_default_config(output_file: str = "agropulse_config.json", 
                         profile: str = "production"):
    """
    Create a default configuration file
    
    Usage:
        create_default_config("my_config.json", profile="production")
    """
    profile_enum = EnvironmentProfile(profile)
    config = DetectionSystemConfig()
    config = DetectionSystemConfig._apply_profile(config, profile_enum)
    config.save(output_file)
    print(f"✓ Created default {profile} configuration: {output_file}")
    print("  Edit this file to customize settings")
    print("  Or set environment variables to override")


# Example usage
if __name__ == "__main__":
    print("AgroPulse Configuration System")
    print("=" * 60)
    
    # Example 1: Load with development defaults
    print("\n1. Development Configuration:")
    config_dev = load_config(profile="development")
    config_dev.print_summary()
    
    # Example 2: Load with production defaults
    print("\n2. Production Configuration:")
    config_prod = load_config(profile="production")
    config_prod.print_summary()
    
    # Example 3: Offline mode
    print("\n3. Offline Configuration:")
    config_offline = load_config(profile="offline")
    config_offline.print_summary()
    
    # Example 4: Create default config file
    print("\n4. Creating default config file...")
    create_default_config("agropulse_config.json", profile="production")
    
    print("\n✓ Configuration examples completed")
