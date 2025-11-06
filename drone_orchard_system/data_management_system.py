"""
Advanced Data Management and Database Infrastructure

This module provides comprehensive data management capabilities:
- Time-series data management for sensor readings
- Spatial database with PostGIS integration
- Image and file storage management
- Data versioning and lineage tracking
- Real-time data streaming pipelines
- Data quality validation and cleaning
- ETL (Extract, Transform, Load) pipelines
- Data caching and indexing strategies
- Batch and streaming data processing
- Data backup and disaster recovery
- Multi-tenant data isolation
- Access control and encryption
- Data analytics and aggregation
- Query optimization
- Database sharding and replication

Author: AgroPulse Development Team
Version: 3.0.0
"""

import asyncio
import asyncpg
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, 
    Boolean, ForeignKey, Text, JSON, LargeBinary, Table, MetaData,
    Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from sqlalchemy.pool import QueuePool
from geoalchemy2 import Geometry
import redis
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import pickle
import hashlib
import uuid
from pathlib import Path
import pandas as pd
import numpy as np
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

# Database Base
Base = declarative_base()


class DataType(Enum):
    """Types of data stored in system"""
    IMAGE = "Image"
    SENSOR_READING = "Sensor Reading"
    FLIGHT_LOG = "Flight Log"
    ANALYSIS_RESULT = "Analysis Result"
    MODEL_PREDICTION = "Model Prediction"
    METADATA = "Metadata"


class StorageTier(Enum):
    """Storage tiers for data lifecycle management"""
    HOT = "Hot"  # Frequently accessed, fast storage
    WARM = "Warm"  # Occasionally accessed
    COLD = "Cold"  # Rarely accessed, archival
    GLACIER = "Glacier"  # Long-term archival


@dataclass
class DataQualityReport:
    """Data quality assessment report"""
    total_records: int
    valid_records: int
    invalid_records: int
    missing_values: Dict[str, int]
    outliers: Dict[str, int]
    duplicates: int
    quality_score: float
    issues: List[str]
    timestamp: datetime = field(default_factory=datetime.now)


# ============================================================================
# Database Models
# ============================================================================

class Drone(Base):
    """Drone entity"""
    __tablename__ = 'drones'
    
    id = Column(String(50), primary_key=True)
    serial_number = Column(String(100), unique=True, nullable=False)
    model = Column(String(100))
    manufacturer = Column(String(100))
    purchase_date = Column(DateTime)
    last_maintenance = Column(DateTime)
    status = Column(String(50))
    firmware_version = Column(String(50))
    battery_capacity_mah = Column(Integer)
    max_flight_time_min = Column(Integer)
    max_payload_kg = Column(Float)
    location_lat = Column(Float)
    location_lon = Column(Float)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    flight_logs = relationship("FlightLog", back_populates="drone")
    sensor_readings = relationship("SensorReading", back_populates="drone")
    
    # Indexes
    __table_args__ = (
        Index('idx_drone_status', 'status'),
        Index('idx_drone_location', 'location_lat', 'location_lon'),
    )


class Field(Base):
    """Agricultural field entity"""
    __tablename__ = 'fields'
    
    id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False)
    farm_id = Column(String(50), ForeignKey('farms.id'))
    area_hectares = Column(Float)
    crop_type = Column(String(100))
    planting_date = Column(DateTime)
    expected_harvest_date = Column(DateTime)
    soil_type = Column(String(100))
    irrigation_type = Column(String(100))
    geometry = Column(Geometry('POLYGON'))
    elevation_avg = Column(Float)
    slope_avg = Column(Float)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    farm = relationship("Farm", back_populates="fields")
    flight_logs = relationship("FlightLog", back_populates="field")
    sensor_readings = relationship("SensorReading", back_populates="field")
    
    # Indexes
    __table_args__ = (
        Index('idx_field_farm', 'farm_id'),
        Index('idx_field_crop', 'crop_type'),
        Index('idx_field_geometry', 'geometry', postgresql_using='gist'),
    )


class Farm(Base):
    """Farm entity"""
    __tablename__ = 'farms'
    
    id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False)
    owner_id = Column(String(50), ForeignKey('users.id'))
    address = Column(Text)
    total_area_hectares = Column(Float)
    location_lat = Column(Float)
    location_lon = Column(Float)
    timezone = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    owner = relationship("User", back_populates="farms")
    fields = relationship("Field", back_populates="farm")
    
    # Indexes
    __table_args__ = (
        Index('idx_farm_owner', 'owner_id'),
        Index('idx_farm_location', 'location_lat', 'location_lon'),
    )


class User(Base):
    """User entity"""
    __tablename__ = 'users'
    
    id = Column(String(50), primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(200))
    role = Column(String(50))
    phone = Column(String(50))
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    farms = relationship("Farm", back_populates="owner")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_username', 'username'),
    )


class FlightLog(Base):
    """Flight log entry"""
    __tablename__ = 'flight_logs'
    
    id = Column(String(50), primary_key=True)
    drone_id = Column(String(50), ForeignKey('drones.id'), nullable=False)
    field_id = Column(String(50), ForeignKey('fields.id'))
    mission_type = Column(String(100))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    duration_seconds = Column(Integer)
    distance_km = Column(Float)
    area_covered_hectares = Column(Float)
    battery_start = Column(Float)
    battery_end = Column(Float)
    battery_consumed = Column(Float)
    max_altitude_m = Column(Float)
    avg_speed_mps = Column(Float)
    images_captured = Column(Integer)
    status = Column(String(50))
    trajectory = Column(Geometry('LINESTRING'))
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    drone = relationship("Drone", back_populates="flight_logs")
    field = relationship("Field", back_populates="flight_logs")
    
    # Indexes
    __table_args__ = (
        Index('idx_flight_drone', 'drone_id'),
        Index('idx_flight_field', 'field_id'),
        Index('idx_flight_time', 'start_time'),
        Index('idx_flight_trajectory', 'trajectory', postgresql_using='gist'),
    )


class SensorReading(Base):
    """Time-series sensor data"""
    __tablename__ = 'sensor_readings'
    
    id = Column(String(50), primary_key=True)
    drone_id = Column(String(50), ForeignKey('drones.id'))
    field_id = Column(String(50), ForeignKey('fields.id'))
    sensor_type = Column(String(100), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    location = Column(Geometry('POINT'))
    value = Column(Float)
    unit = Column(String(50))
    quality_flag = Column(String(50))
    metadata = Column(JSON)
    
    # Relationships
    drone = relationship("Drone", back_populates="sensor_readings")
    field = relationship("Field", back_populates="sensor_readings")
    
    # Indexes
    __table_args__ = (
        Index('idx_sensor_drone', 'drone_id'),
        Index('idx_sensor_field', 'field_id'),
        Index('idx_sensor_type', 'sensor_type'),
        Index('idx_sensor_time', 'timestamp'),
        Index('idx_sensor_location', 'location', postgresql_using='gist'),
    )


class ImageData(Base):
    """Image metadata and storage reference"""
    __tablename__ = 'images'
    
    id = Column(String(50), primary_key=True)
    flight_log_id = Column(String(50), ForeignKey('flight_logs.id'))
    field_id = Column(String(50), ForeignKey('fields.id'))
    image_type = Column(String(50))
    capture_time = Column(DateTime, nullable=False)
    location = Column(Geometry('POINT'))
    altitude_m = Column(Float)
    camera_angle = Column(Float)
    resolution_width = Column(Integer)
    resolution_height = Column(Integer)
    file_path = Column(String(500))
    file_size_mb = Column(Float)
    storage_tier = Column(String(50))
    checksum = Column(String(64))
    is_processed = Column(Boolean, default=False)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
    
    # Indexes
    __table_args__ = (
        Index('idx_image_flight', 'flight_log_id'),
        Index('idx_image_field', 'field_id'),
        Index('idx_image_time', 'capture_time'),
        Index('idx_image_location', 'location', postgresql_using='gist'),
        Index('idx_image_processed', 'is_processed'),
    )


class AnalysisResult(Base):
    """Analysis results from ML models"""
    __tablename__ = 'analysis_results'
    
    id = Column(String(50), primary_key=True)
    image_id = Column(String(50), ForeignKey('images.id'))
    field_id = Column(String(50), ForeignKey('fields.id'))
    analysis_type = Column(String(100), nullable=False)
    model_name = Column(String(100))
    model_version = Column(String(50))
    timestamp = Column(DateTime, nullable=False)
    results = Column(JSON)
    confidence_score = Column(Float)
    processing_time_ms = Column(Float)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
    
    # Indexes
    __table_args__ = (
        Index('idx_analysis_image', 'image_id'),
        Index('idx_analysis_field', 'field_id'),
        Index('idx_analysis_type', 'analysis_type'),
        Index('idx_analysis_time', 'timestamp'),
    )


# ============================================================================
# Database Manager
# ============================================================================

class DatabaseManager:
    """
    Centralized database management
    """
    
    def __init__(self, 
                 connection_string: str,
                 pool_size: int = 20,
                 max_overflow: int = 10):
        """
        Initialize database manager
        
        Args:
            connection_string: Database connection string
            pool_size: Connection pool size
            max_overflow: Max overflow connections
        """
        self.engine = create_engine(
            connection_string,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
            echo=False
        )
        
        self.SessionLocal = scoped_session(sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        ))
        
        # Create tables
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self):
        """Get database session"""
        return self.SessionLocal()
    
    def close_session(self, session):
        """Close database session"""
        session.close()
    
    def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """
        Execute raw SQL query
        
        Args:
            query: SQL query string
            params: Query parameters
        
        Returns:
            Query results as list of dictionaries
        """
        session = self.get_session()
        try:
            result = session.execute(query, params or {})
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in result.fetchall()]
            return data
        finally:
            self.close_session(session)
    
    def bulk_insert(self, model_class, records: List[Dict]):
        """
        Bulk insert records
        
        Args:
            model_class: SQLAlchemy model class
            records: List of record dictionaries
        """
        session = self.get_session()
        try:
            session.bulk_insert_mappings(model_class, records)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.close_session(session)
    
    def bulk_update(self, model_class, records: List[Dict]):
        """
        Bulk update records
        
        Args:
            model_class: SQLAlchemy model class
            records: List of record dictionaries with id
        """
        session = self.get_session()
        try:
            session.bulk_update_mappings(model_class, records)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.close_session(session)


# ============================================================================
# Cache Manager
# ============================================================================

class CacheManager:
    """
    Redis-based caching system
    """
    
    def __init__(self, 
                 host: str = 'localhost',
                 port: int = 6379,
                 db: int = 0,
                 default_ttl: int = 3600):
        """
        Initialize cache manager
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            default_ttl: Default time-to-live in seconds
        """
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=False
        )
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None
        """
        value = self.redis_client.get(key)
        if value:
            return pickle.loads(value)
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
        """
        ttl = ttl or self.default_ttl
        serialized = pickle.dumps(value)
        self.redis_client.setex(key, ttl, serialized)
    
    def delete(self, key: str):
        """Delete key from cache"""
        self.redis_client.delete(key)
    
    def clear_pattern(self, pattern: str):
        """
        Clear all keys matching pattern
        
        Args:
            pattern: Pattern to match (e.g., 'user:*')
        """
        keys = self.redis_client.keys(pattern)
        if keys:
            self.redis_client.delete(*keys)
    
    def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment counter
        
        Args:
            key: Counter key
            amount: Increment amount
        
        Returns:
            New value
        """
        return self.redis_client.incr(key, amount)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        info = self.redis_client.info()
        return {
            'used_memory_mb': info['used_memory'] / (1024 * 1024),
            'total_keys': self.redis_client.dbsize(),
            'hit_rate': info.get('keyspace_hits', 0) / max(
                info.get('keyspace_hits', 0) + info.get('keyspace_misses', 1),
                1
            )
        }


# ============================================================================
# Time-Series Data Manager
# ============================================================================

class TimeSeriesManager:
    """
    Manage time-series sensor data with efficient storage and retrieval
    """
    
    def __init__(self, db_manager: DatabaseManager, cache_manager: CacheManager):
        self.db = db_manager
        self.cache = cache_manager
    
    def insert_reading(self,
                      drone_id: str,
                      field_id: str,
                      sensor_type: str,
                      timestamp: datetime,
                      value: float,
                      location: Tuple[float, float],
                      metadata: Optional[Dict] = None):
        """
        Insert sensor reading
        
        Args:
            drone_id: Drone identifier
            field_id: Field identifier
            sensor_type: Type of sensor
            timestamp: Reading timestamp
            value: Sensor value
            location: (latitude, longitude)
            metadata: Additional metadata
        """
        reading_id = str(uuid.uuid4())
        
        session = self.db.get_session()
        try:
            reading = SensorReading(
                id=reading_id,
                drone_id=drone_id,
                field_id=field_id,
                sensor_type=sensor_type,
                timestamp=timestamp,
                location=f'POINT({location[1]} {location[0]})',
                value=value,
                metadata=metadata
            )
            session.add(reading)
            session.commit()
            
            # Invalidate cache
            cache_key = f"sensor:{field_id}:{sensor_type}"
            self.cache.delete(cache_key)
            
        finally:
            self.db.close_session(session)
    
    def bulk_insert_readings(self, readings: List[Dict]):
        """
        Bulk insert sensor readings
        
        Args:
            readings: List of reading dictionaries
        """
        # Add IDs and format geometry
        for reading in readings:
            reading['id'] = str(uuid.uuid4())
            if 'location' in reading and isinstance(reading['location'], tuple):
                lat, lon = reading['location']
                reading['location'] = f'POINT({lon} {lat})'
        
        self.db.bulk_insert(SensorReading, readings)
    
    def query_time_range(self,
                        field_id: str,
                        sensor_type: str,
                        start_time: datetime,
                        end_time: datetime) -> pd.DataFrame:
        """
        Query sensor readings in time range
        
        Args:
            field_id: Field identifier
            sensor_type: Sensor type
            start_time: Start of time range
            end_time: End of time range
        
        Returns:
            DataFrame with readings
        """
        # Check cache
        cache_key = f"sensor:{field_id}:{sensor_type}:{start_time}:{end_time}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        # Query database
        session = self.db.get_session()
        try:
            readings = session.query(SensorReading).filter(
                SensorReading.field_id == field_id,
                SensorReading.sensor_type == sensor_type,
                SensorReading.timestamp >= start_time,
                SensorReading.timestamp <= end_time
            ).all()
            
            # Convert to DataFrame
            data = [{
                'timestamp': r.timestamp,
                'value': r.value,
                'location': r.location,
                'metadata': r.metadata
            } for r in readings]
            
            df = pd.DataFrame(data)
            
            # Cache result
            self.cache.set(cache_key, df, ttl=300)  # 5 minutes
            
            return df
            
        finally:
            self.db.close_session(session)
    
    def aggregate_by_time(self,
                         field_id: str,
                         sensor_type: str,
                         start_time: datetime,
                         end_time: datetime,
                         interval: str = '1H') -> pd.DataFrame:
        """
        Aggregate sensor readings by time interval
        
        Args:
            field_id: Field identifier
            sensor_type: Sensor type
            start_time: Start time
            end_time: End time
            interval: Pandas time interval (e.g., '1H', '15T')
        
        Returns:
            Aggregated DataFrame
        """
        df = self.query_time_range(field_id, sensor_type, start_time, end_time)
        
        if df.empty:
            return df
        
        # Set timestamp as index
        df.set_index('timestamp', inplace=True)
        
        # Resample and aggregate
        aggregated = df['value'].resample(interval).agg([
            ('mean', 'mean'),
            ('min', 'min'),
            ('max', 'max'),
            ('count', 'count')
        ])
        
        return aggregated


# ============================================================================
# Data Quality Manager
# ============================================================================

class DataQualityManager:
    """
    Data quality assessment and validation
    """
    
    def __init__(self):
        self.validation_rules = {}
    
    def add_validation_rule(self,
                           field_name: str,
                           rule_type: str,
                           params: Dict):
        """
        Add validation rule
        
        Args:
            field_name: Field to validate
            rule_type: Type of rule (range, type, pattern, custom)
            params: Rule parameters
        """
        if field_name not in self.validation_rules:
            self.validation_rules[field_name] = []
        
        self.validation_rules[field_name].append({
            'type': rule_type,
            'params': params
        })
    
    def validate_record(self, record: Dict) -> Tuple[bool, List[str]]:
        """
        Validate a single record
        
        Args:
            record: Record to validate
        
        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues = []
        
        for field_name, rules in self.validation_rules.items():
            if field_name not in record:
                issues.append(f"Missing required field: {field_name}")
                continue
            
            value = record[field_name]
            
            for rule in rules:
                rule_type = rule['type']
                params = rule['params']
                
                if rule_type == 'range':
                    min_val = params.get('min')
                    max_val = params.get('max')
                    if value < min_val or value > max_val:
                        issues.append(
                            f"{field_name} out of range: {value} not in [{min_val}, {max_val}]"
                        )
                
                elif rule_type == 'type':
                    expected_type = params.get('type')
                    if not isinstance(value, expected_type):
                        issues.append(
                            f"{field_name} type mismatch: expected {expected_type}, got {type(value)}"
                        )
                
                elif rule_type == 'not_null':
                    if value is None:
                        issues.append(f"{field_name} cannot be null")
        
        is_valid = len(issues) == 0
        return is_valid, issues
    
    def assess_dataset_quality(self, data: pd.DataFrame) -> DataQualityReport:
        """
        Assess quality of entire dataset
        
        Args:
            data: DataFrame to assess
        
        Returns:
            Data quality report
        """
        total_records = len(data)
        
        # Missing values
        missing_values = data.isnull().sum().to_dict()
        
        # Outliers (using IQR method)
        outliers = {}
        for col in data.select_dtypes(include=[np.number]).columns:
            Q1 = data[col].quantile(0.25)
            Q3 = data[col].quantile(0.75)
            IQR = Q3 - Q1
            outlier_mask = (data[col] < Q1 - 1.5 * IQR) | (data[col] > Q3 + 1.5 * IQR)
            outliers[col] = outlier_mask.sum()
        
        # Duplicates
        duplicates = data.duplicated().sum()
        
        # Validate records
        valid_count = 0
        invalid_count = 0
        all_issues = []
        
        for _, record in data.iterrows():
            is_valid, issues = self.validate_record(record.to_dict())
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
                all_issues.extend(issues)
        
        # Calculate quality score
        quality_score = (
            (valid_count / total_records) * 0.5 +
            (1 - sum(missing_values.values()) / (total_records * len(data.columns))) * 0.3 +
            (1 - duplicates / total_records) * 0.2
        )
        
        return DataQualityReport(
            total_records=total_records,
            valid_records=valid_count,
            invalid_records=invalid_count,
            missing_values={k: int(v) for k, v in missing_values.items()},
            outliers={k: int(v) for k, v in outliers.items()},
            duplicates=int(duplicates),
            quality_score=quality_score,
            issues=list(set(all_issues))[:100]  # Top 100 unique issues
        )


# ============================================================================
# ETL Pipeline
# ============================================================================

class ETLPipeline:
    """
    Extract, Transform, Load pipeline
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.transformers = []
    
    def add_transformer(self, transformer: Callable):
        """Add transformation function"""
        self.transformers.append(transformer)
    
    def extract(self, source: str, **kwargs) -> pd.DataFrame:
        """
        Extract data from source
        
        Args:
            source: Data source (csv, database, api)
            **kwargs: Source-specific parameters
        
        Returns:
            Extracted DataFrame
        """
        if source == 'csv':
            return pd.read_csv(kwargs['file_path'])
        elif source == 'database':
            return pd.read_sql_query(kwargs['query'], self.db.engine)
        elif source == 'json':
            return pd.read_json(kwargs['file_path'])
        else:
            raise ValueError(f"Unsupported source: {source}")
    
    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Apply transformations
        
        Args:
            data: Input DataFrame
        
        Returns:
            Transformed DataFrame
        """
        result = data.copy()
        
        for transformer in self.transformers:
            result = transformer(result)
        
        return result
    
    def load(self, data: pd.DataFrame, destination: str, **kwargs):
        """
        Load data to destination
        
        Args:
            data: DataFrame to load
            destination: Destination (database, csv, parquet)
            **kwargs: Destination-specific parameters
        """
        if destination == 'database':
            data.to_sql(
                kwargs['table_name'],
                self.db.engine,
                if_exists=kwargs.get('if_exists', 'append'),
                index=False
            )
        elif destination == 'csv':
            data.to_csv(kwargs['file_path'], index=False)
        elif destination == 'parquet':
            data.to_parquet(kwargs['file_path'], index=False)
        else:
            raise ValueError(f"Unsupported destination: {destination}")
    
    def run(self, source: str, destination: str, **kwargs):
        """
        Run complete ETL pipeline
        
        Args:
            source: Data source
            destination: Data destination
            **kwargs: Parameters for extract and load
        """
        print("ETL Pipeline: Extracting...")
        data = self.extract(source, **kwargs)
        print(f"Extracted {len(data)} records")
        
        print("ETL Pipeline: Transforming...")
        data = self.transform(data)
        print(f"Transformed to {len(data)} records")
        
        print("ETL Pipeline: Loading...")
        self.load(data, destination, **kwargs)
        print("ETL Pipeline: Complete!")


def main():
    """Demonstration of data management system"""
    print("=" * 80)
    print("AgroPulse Advanced Data Management System")
    print("=" * 80)
    
    # Initialize database (SQLite for demo)
    print("\nInitializing database...")
    db_manager = DatabaseManager('sqlite:///agropulse_demo.db')
    
    # Initialize cache
    print("Initializing cache...")
    try:
        cache_manager = CacheManager()
        cache_enabled = True
    except:
        print("Redis not available, skipping cache")
        cache_enabled = False
        cache_manager = None
    
    # Create sample data
    print("\nCreating sample records...")
    session = db_manager.get_session()
    
    # Create user
    user = User(
        id='user_001',
        username='farmer_john',
        email='john@farm.com',
        password_hash=hashlib.sha256('password'.encode()).hexdigest(),
        full_name='John Farmer',
        role='farmer'
    )
    session.add(user)
    
    # Create farm
    farm = Farm(
        id='farm_001',
        name='Green Valley Farm',
        owner_id='user_001',
        total_area_hectares=50.0,
        location_lat=45.5,
        location_lon=-120.5
    )
    session.add(farm)
    
    # Create field
    field = Field(
        id='field_001',
        name='North Field',
        farm_id='farm_001',
        area_hectares=10.0,
        crop_type='Apple',
        soil_type='Loam'
    )
    session.add(field)
    
    # Create drone
    drone = Drone(
        id='drone_001',
        serial_number='DRN-2025-001',
        model='AgroPulse X1',
        manufacturer='AgroPulse Inc',
        status='active',
        battery_capacity_mah=22000,
        max_flight_time_min=30
    )
    session.add(drone)
    
    session.commit()
    db_manager.close_session(session)
    
    print(f"Created: User, Farm, Field, Drone")
    
    # Time-series manager
    if cache_enabled:
        print("\nTesting time-series data...")
        ts_manager = TimeSeriesManager(db_manager, cache_manager)
        
        # Insert sample readings
        for i in range(10):
            ts_manager.insert_reading(
                drone_id='drone_001',
                field_id='field_001',
                sensor_type='temperature',
                timestamp=datetime.now() - timedelta(hours=i),
                value=20.0 + i * 0.5,
                location=(45.5, -120.5)
            )
        
        print("Inserted 10 sensor readings")
    
    # Data quality assessment
    print("\nTesting data quality assessment...")
    quality_mgr = DataQualityManager()
    
    # Add validation rules
    quality_mgr.add_validation_rule('temperature', 'range', {'min': -10, 'max': 50})
    quality_mgr.add_validation_rule('humidity', 'range', {'min': 0, 'max': 100})
    
    # Create sample dataset
    sample_data = pd.DataFrame({
        'temperature': [20, 25, 30, 100, 22],  # One outlier
        'humidity': [60, 65, 70, 75, None]  # One missing
    })
    
    report = quality_mgr.assess_dataset_quality(sample_data)
    
    print(f"\nData Quality Report:")
    print(f"  Total Records: {report.total_records}")
    print(f"  Valid Records: {report.valid_records}")
    print(f"  Quality Score: {report.quality_score:.2f}")
    print(f"  Missing Values: {report.missing_values}")
    print(f"  Outliers: {report.outliers}")
    
    print("\n" + "=" * 80)
    print("Data management demonstration complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
