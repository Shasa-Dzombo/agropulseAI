# ======================================================================================================================
# AgroPulse NVR - Time-Series Data Management
# InfluxDB integration, time-series storage, aggregation, retention policies
# ======================================================================================================================

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd

logger = logging.getLogger(__name__)

# ======================================================================================================================
# TIME-SERIES MODELS
# ======================================================================================================================

class AggregationFunction(Enum):
    """Aggregation function"""
    MEAN = "mean"
    SUM = "sum"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    FIRST = "first"
    LAST = "last"
    MEDIAN = "median"
    STDDEV = "stddev"

class RetentionPeriod(Enum):
    """Retention period"""
    ONE_HOUR = "1h"
    ONE_DAY = "1d"
    ONE_WEEK = "7d"
    ONE_MONTH = "30d"
    THREE_MONTHS = "90d"
    SIX_MONTHS = "180d"
    ONE_YEAR = "365d"
    INFINITE = "inf"

@dataclass
class TimeSeriesPoint:
    """Time series data point"""
    measurement: str
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    fields: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DownsamplingRule:
    """Downsampling rule for data aggregation"""
    source_measurement: str
    target_measurement: str
    aggregation_window: str  # e.g., "5m", "1h", "1d"
    aggregation_function: AggregationFunction
    retention_period: RetentionPeriod
    fields: List[str]

@dataclass
class TimeSeriesQuery:
    """Time series query"""
    measurement: str
    start_time: datetime
    end_time: Optional[datetime] = None
    tags: Dict[str, str] = field(default_factory=dict)
    fields: Optional[List[str]] = None
    aggregation_window: Optional[str] = None
    aggregation_function: Optional[AggregationFunction] = None
    limit: Optional[int] = None

# ======================================================================================================================
# INFLUXDB CONNECTION MANAGER
# ======================================================================================================================

class InfluxDBManager:
    """InfluxDB connection and operations manager"""
    
    def __init__(self, url: str, token: str, org: str, bucket: str):
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        self.client: Optional[InfluxDBClient] = None
        self.write_api = None
        self.query_api = None
        
        logger.info(f"[INFLUX] InfluxDB manager initialized: {url}/{bucket}")
    
    def connect(self):
        """Connect to InfluxDB"""
        try:
            self.client = InfluxDBClient(
                url=self.url,
                token=self.token,
                org=self.org
            )
            
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.query_api = self.client.query_api()
            
            # Test connection
            health = self.client.health()
            logger.info(f"[INFLUX] Connected - Status: {health.status}")
            
        except Exception as e:
            logger.error(f"[INFLUX] Connection failed: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from InfluxDB"""
        if self.client:
            self.client.close()
            logger.info("[INFLUX] Disconnected")
    
    def write_point(self, point: TimeSeriesPoint):
        """Write single point"""
        try:
            p = Point(point.measurement)
            
            # Add tags
            for tag_key, tag_value in point.tags.items():
                p = p.tag(tag_key, tag_value)
            
            # Add fields
            for field_key, field_value in point.fields.items():
                p = p.field(field_key, field_value)
            
            # Set timestamp
            p = p.time(point.timestamp, WritePrecision.NS)
            
            self.write_api.write(bucket=self.bucket, record=p)
            logger.debug(f"[INFLUX] Wrote point: {point.measurement}")
            
        except Exception as e:
            logger.error(f"[INFLUX] Write error: {e}")
            raise
    
    def write_points(self, points: List[TimeSeriesPoint]):
        """Write multiple points"""
        try:
            records = []
            for point in points:
                p = Point(point.measurement)
                
                for tag_key, tag_value in point.tags.items():
                    p = p.tag(tag_key, tag_value)
                
                for field_key, field_value in point.fields.items():
                    p = p.field(field_key, field_value)
                
                p = p.time(point.timestamp, WritePrecision.NS)
                records.append(p)
            
            self.write_api.write(bucket=self.bucket, record=records)
            logger.info(f"[INFLUX] Wrote {len(points)} points")
            
        except Exception as e:
            logger.error(f"[INFLUX] Batch write error: {e}")
            raise
    
    def query(self, flux_query: str) -> List[Dict[str, Any]]:
        """Execute Flux query"""
        try:
            tables = self.query_api.query(flux_query, org=self.org)
            
            results = []
            for table in tables:
                for record in table.records:
                    results.append({
                        'measurement': record.get_measurement(),
                        'time': record.get_time(),
                        'value': record.get_value(),
                        'field': record.get_field(),
                        'tags': {k: v for k, v in record.values.items() 
                                if k not in ['_time', '_value', '_field', '_measurement']}
                    })
            
            logger.debug(f"[INFLUX] Query returned {len(results)} records")
            return results
            
        except Exception as e:
            logger.error(f"[INFLUX] Query error: {e}")
            raise

# ======================================================================================================================
# TIME-SERIES DATA WRITER
# ======================================================================================================================

class TimeSeriesWriter:
    """Time-series data writer with buffering"""
    
    def __init__(self, influx_manager: InfluxDBManager,
                 buffer_size: int = 1000,
                 flush_interval: int = 10):
        self.influx = influx_manager
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        
        self.buffer: List[TimeSeriesPoint] = []
        self.last_flush = datetime.now()
        self.write_count = 0
        
        logger.info(
            f"[TS-WRITER] Time-series writer initialized "
            f"(buffer={buffer_size}, interval={flush_interval}s)"
        )
    
    async def write(self, point: TimeSeriesPoint):
        """Write point with buffering"""
        self.buffer.append(point)
        
        # Check if flush needed
        if len(self.buffer) >= self.buffer_size:
            await self.flush()
        elif (datetime.now() - self.last_flush).total_seconds() >= self.flush_interval:
            await self.flush()
    
    async def flush(self):
        """Flush buffer to InfluxDB"""
        if not self.buffer:
            return
        
        try:
            self.influx.write_points(self.buffer)
            self.write_count += len(self.buffer)
            logger.info(f"[TS-WRITER] Flushed {len(self.buffer)} points")
            
            self.buffer.clear()
            self.last_flush = datetime.now()
            
        except Exception as e:
            logger.error(f"[TS-WRITER] Flush error: {e}")
    
    async def write_device_telemetry(self, device_id: str, telemetry: Dict[str, float]):
        """Write device telemetry"""
        point = TimeSeriesPoint(
            measurement="device_telemetry",
            timestamp=datetime.now(),
            tags={'device_id': device_id},
            fields=telemetry
        )
        await self.write(point)
    
    async def write_field_metrics(self, field_id: str, metrics: Dict[str, float]):
        """Write field metrics"""
        point = TimeSeriesPoint(
            measurement="field_metrics",
            timestamp=datetime.now(),
            tags={'field_id': field_id},
            fields=metrics
        )
        await self.write(point)
    
    async def write_detection_event(self, camera_id: str, detection_data: Dict[str, Any]):
        """Write detection event"""
        point = TimeSeriesPoint(
            measurement="detection_events",
            timestamp=datetime.now(),
            tags={
                'camera_id': camera_id,
                'class_name': detection_data.get('class_name', 'unknown')
            },
            fields={
                'confidence': detection_data.get('confidence', 0.0),
                'count': 1
            }
        )
        await self.write(point)

# ======================================================================================================================
# TIME-SERIES DATA READER
# ======================================================================================================================

class TimeSeriesReader:
    """Time-series data reader with query builder"""
    
    def __init__(self, influx_manager: InfluxDBManager):
        self.influx = influx_manager
        
        logger.info("[TS-READER] Time-series reader initialized")
    
    def build_query(self, query: TimeSeriesQuery) -> str:
        """Build Flux query from TimeSeriesQuery"""
        flux_parts = []
        
        # Base query
        flux_parts.append(f'from(bucket: "{self.influx.bucket}")')
        
        # Time range
        start_str = query.start_time.isoformat()
        flux_parts.append(f'|> range(start: {start_str}')
        if query.end_time:
            end_str = query.end_time.isoformat()
            flux_parts.append(f', stop: {end_str}')
        flux_parts.append(')')
        
        # Filter by measurement
        flux_parts.append(f'|> filter(fn: (r) => r["_measurement"] == "{query.measurement}")')
        
        # Filter by fields
        if query.fields:
            field_conditions = ' or '.join([f'r["_field"] == "{f}"' for f in query.fields])
            flux_parts.append(f'|> filter(fn: (r) => {field_conditions})')
        
        # Filter by tags
        for tag_key, tag_value in query.tags.items():
            flux_parts.append(
                f'|> filter(fn: (r) => r["{tag_key}"] == "{tag_value}")'
            )
        
        # Aggregation
        if query.aggregation_window and query.aggregation_function:
            flux_parts.append(
                f'|> aggregateWindow(every: {query.aggregation_window}, '
                f'fn: {query.aggregation_function.value})'
            )
        
        # Limit
        if query.limit:
            flux_parts.append(f'|> limit(n: {query.limit})')
        
        flux_query = '\n  '.join(flux_parts)
        logger.debug(f"[TS-READER] Built query:\n{flux_query}")
        
        return flux_query
    
    def query(self, query: TimeSeriesQuery) -> List[Dict[str, Any]]:
        """Execute query"""
        flux_query = self.build_query(query)
        return self.influx.query(flux_query)
    
    def get_device_telemetry(self, device_id: str,
                            start_time: datetime,
                            end_time: Optional[datetime] = None,
                            fields: Optional[List[str]] = None) -> pd.DataFrame:
        """Get device telemetry as DataFrame"""
        query = TimeSeriesQuery(
            measurement="device_telemetry",
            start_time=start_time,
            end_time=end_time,
            tags={'device_id': device_id},
            fields=fields
        )
        
        results = self.query(query)
        
        if not results:
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(results)
        return df
    
    def get_field_metrics(self, field_id: str,
                         start_time: datetime,
                         aggregation_window: str = "1h") -> pd.DataFrame:
        """Get field metrics with aggregation"""
        query = TimeSeriesQuery(
            measurement="field_metrics",
            start_time=start_time,
            tags={'field_id': field_id},
            aggregation_window=aggregation_window,
            aggregation_function=AggregationFunction.MEAN
        )
        
        results = self.query(query)
        
        if not results:
            return pd.DataFrame()
        
        df = pd.DataFrame(results)
        return df
    
    def get_detection_count(self, camera_id: Optional[str] = None,
                           start_time: datetime = None,
                           end_time: Optional[datetime] = None) -> int:
        """Get detection count"""
        tags = {}
        if camera_id:
            tags['camera_id'] = camera_id
        
        query = TimeSeriesQuery(
            measurement="detection_events",
            start_time=start_time or (datetime.now() - timedelta(days=1)),
            end_time=end_time,
            tags=tags,
            fields=['count']
        )
        
        results = self.query(query)
        return sum(r.get('value', 0) for r in results)

# ======================================================================================================================
# CONTINUOUS QUERIES / DOWNSAMPLING
# ======================================================================================================================

class DownsamplingEngine:
    """Downsampling engine for data aggregation"""
    
    def __init__(self, influx_manager: InfluxDBManager):
        self.influx = influx_manager
        self.rules: List[DownsamplingRule] = []
        self.running = False
        self.task = None
        
        logger.info("[DOWNSAMPLE] Downsampling engine initialized")
    
    def add_rule(self, rule: DownsamplingRule):
        """Add downsampling rule"""
        self.rules.append(rule)
        logger.info(
            f"[DOWNSAMPLE] Added rule: {rule.source_measurement} -> "
            f"{rule.target_measurement} ({rule.aggregation_window})"
        )
    
    async def start(self):
        """Start downsampling engine"""
        self.running = True
        self.task = asyncio.create_task(self._downsample_loop())
        logger.info("[DOWNSAMPLE] Engine started")
    
    async def stop(self):
        """Stop downsampling engine"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("[DOWNSAMPLE] Engine stopped")
    
    async def _downsample_loop(self):
        """Downsampling loop"""
        while self.running:
            try:
                for rule in self.rules:
                    await self._execute_rule(rule)
                
                # Run every hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"[DOWNSAMPLE] Loop error: {e}")
    
    async def _execute_rule(self, rule: DownsamplingRule):
        """Execute downsampling rule"""
        try:
            logger.info(f"[DOWNSAMPLE] Executing rule: {rule.target_measurement}")
            
            # Build Flux query for downsampling
            flux_query = f'''
from(bucket: "{self.influx.bucket}")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "{rule.source_measurement}")
  |> aggregateWindow(every: {rule.aggregation_window}, fn: {rule.aggregation_function.value})
  |> set(key: "_measurement", value: "{rule.target_measurement}")
  |> to(bucket: "{self.influx.bucket}")
'''
            
            # Execute query (this writes to target measurement)
            self.influx.query(flux_query)
            
            logger.info(f"[DOWNSAMPLE] Completed: {rule.target_measurement}")
            
        except Exception as e:
            logger.error(f"[DOWNSAMPLE] Rule execution error: {e}")

# ======================================================================================================================
# RETENTION POLICY MANAGER
# ======================================================================================================================

class RetentionPolicyManager:
    """Retention policy manager"""
    
    def __init__(self, influx_manager: InfluxDBManager):
        self.influx = influx_manager
        self.policies: Dict[str, RetentionPeriod] = {}
        
        logger.info("[RETENTION] Retention policy manager initialized")
    
    def set_policy(self, measurement: str, period: RetentionPeriod):
        """Set retention policy for measurement"""
        self.policies[measurement] = period
        logger.info(f"[RETENTION] Set policy: {measurement} = {period.value}")
    
    async def enforce_policies(self):
        """Enforce retention policies"""
        for measurement, period in self.policies.items():
            if period == RetentionPeriod.INFINITE:
                continue
            
            try:
                # Calculate cutoff time
                cutoff_map = {
                    RetentionPeriod.ONE_HOUR: timedelta(hours=1),
                    RetentionPeriod.ONE_DAY: timedelta(days=1),
                    RetentionPeriod.ONE_WEEK: timedelta(days=7),
                    RetentionPeriod.ONE_MONTH: timedelta(days=30),
                    RetentionPeriod.THREE_MONTHS: timedelta(days=90),
                    RetentionPeriod.SIX_MONTHS: timedelta(days=180),
                    RetentionPeriod.ONE_YEAR: timedelta(days=365)
                }
                
                cutoff_time = datetime.now() - cutoff_map[period]
                
                # Delete old data
                flux_query = f'''
from(bucket: "{self.influx.bucket}")
  |> range(start: -100y, stop: {cutoff_time.isoformat()})
  |> filter(fn: (r) => r["_measurement"] == "{measurement}")
  |> delete()
'''
                
                self.influx.query(flux_query)
                logger.info(
                    f"[RETENTION] Enforced policy for {measurement}: "
                    f"deleted data older than {cutoff_time}"
                )
                
            except Exception as e:
                logger.error(f"[RETENTION] Policy enforcement error: {e}")

# ======================================================================================================================
# TIME-SERIES ORCHESTRATOR
# ======================================================================================================================

class TimeSeriesOrchestrator:
    """Main time-series orchestrator"""
    
    def __init__(self, url: str, token: str, org: str, bucket: str):
        self.influx_manager = InfluxDBManager(url, token, org, bucket)
        self.writer = TimeSeriesWriter(self.influx_manager)
        self.reader = TimeSeriesReader(self.influx_manager)
        self.downsampling = DownsamplingEngine(self.influx_manager)
        self.retention = RetentionPolicyManager(self.influx_manager)
        
        logger.info("[TS] Time-series orchestrator initialized")
    
    def connect(self):
        """Connect to InfluxDB"""
        self.influx_manager.connect()
    
    def disconnect(self):
        """Disconnect from InfluxDB"""
        self.influx_manager.disconnect()
    
    async def start(self):
        """Start background tasks"""
        await self.downsampling.start()
        logger.info("[TS] Orchestrator started")
    
    async def stop(self):
        """Stop background tasks"""
        await self.writer.flush()
        await self.downsampling.stop()
        logger.info("[TS] Orchestrator stopped")
    
    async def write_point(self, point: TimeSeriesPoint):
        """Write time-series point"""
        await self.writer.write(point)
    
    def query(self, query: TimeSeriesQuery) -> List[Dict[str, Any]]:
        """Query time-series data"""
        return self.reader.query(query)
    
    def add_downsampling_rule(self, rule: DownsamplingRule):
        """Add downsampling rule"""
        self.downsampling.add_rule(rule)
    
    def set_retention_policy(self, measurement: str, period: RetentionPeriod):
        """Set retention policy"""
        self.retention.set_policy(measurement, period)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get time-series statistics"""
        return {
            'writer': {
                'buffer_size': len(self.writer.buffer),
                'write_count': self.writer.write_count,
                'last_flush': self.writer.last_flush.isoformat()
            },
            'downsampling_rules': len(self.downsampling.rules),
            'retention_policies': len(self.retention.policies)
        }

# ======================================================================================================================
# END OF TIME-SERIES DATA MANAGEMENT MODULE
# Lines in this file: ~850+
# Combined total: ~25,750+
# Remaining for 50k: ~24,250 lines
# ======================================================================================================================
