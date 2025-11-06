# ======================================================================================================================
# AgroPulse NVR - Database Operations & ORM Layer
# Advanced database operations, query optimization, and data persistence
# ======================================================================================================================

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import select, update, delete, func, and_, or_, case, cast
from sqlalchemy.dialects.postgresql import insert
from typing import Dict, List, Optional, Tuple, Any
import logging
from datetime import datetime, timedelta
import json
from contextlib import asynccontextmanager
import redis.asyncio as aioredis
from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_Contains, ST_Intersects
from geoalchemy2.elements import WKTElement
import numpy as np

logger = logging.getLogger(__name__)

# ======================================================================================================================
# DATABASE CONNECTION POOL
# ======================================================================================================================

class DatabasePool:
    """Manages async database connection pool"""
    
    def __init__(self, database_url: str, pool_size: int = 20, max_overflow: int = 10):
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.engine = None
        self.session_factory = None
        
    async def initialize(self):
        """Initialize connection pool"""
        self.engine = create_async_engine(
            self.database_url,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False
        )
        
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        logger.info(f"[DB] Connection pool initialized: {self.pool_size} connections")
    
    @asynccontextmanager
    async def get_session(self):
        """Get database session context manager"""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    async def close(self):
        """Close connection pool"""
        if self.engine:
            await self.engine.dispose()
        logger.info("[DB] Connection pool closed")

# ======================================================================================================================
# FARM OPERATIONS
# ======================================================================================================================

class FarmOperations:
    """Database operations for farms"""
    
    def __init__(self, db_pool: DatabasePool):
        self.db = db_pool
        
    async def create_farm(self, name: str, boundary_wkt: str, metadata: Dict) -> str:
        """Create new farm"""
        async with self.db.get_session() as session:
            from core_firmware import FarmModel
            
            farm = FarmModel(
                name=name,
                boundary=WKTElement(boundary_wkt, srid=4326),
                metadata=metadata
            )
            
            # Calculate area and center
            await session.execute(
                update(FarmModel).
                where(FarmModel.id == farm.id).
                values(
                    area_hectares=func.ST_Area(func.ST_Transform(FarmModel.boundary, 3857)) / 10000,
                    center_point=func.ST_Centroid(FarmModel.boundary)
                )
            )
            
            session.add(farm)
            await session.flush()
            
            logger.info(f"[DB] Farm created: {farm.id}")
            return str(farm.id)
    
    async def get_farm(self, farm_id: str) -> Optional[Dict]:
        """Get farm by ID"""
        async with self.db.get_session() as session:
            from core_firmware import FarmModel
            
            result = await session.execute(
                select(FarmModel).where(FarmModel.id == farm_id)
            )
            farm = result.scalar_one_or_none()
            
            if not farm:
                return None
            
            return {
                'id': str(farm.id),
                'name': farm.name,
                'boundary': farm.boundary.desc if farm.boundary else None,
                'area_hectares': float(farm.area_hectares) if farm.area_hectares else 0,
                'center_point': (farm.center_point.x, farm.center_point.y) if farm.center_point else None,
                'metadata': farm.metadata,
                'created_at': farm.created_at.isoformat()
            }
    
    async def get_all_farms(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get all farms"""
        async with self.db.get_session() as session:
            from core_firmware import FarmModel
            
            result = await session.execute(
                select(FarmModel).
                order_by(FarmModel.name).
                limit(limit).
                offset(offset)
            )
            farms = result.scalars().all()
            
            return [
                {
                    'id': str(f.id),
                    'name': f.name,
                    'area_hectares': float(f.area_hectares) if f.area_hectares else 0
                }
                for f in farms
            ]
    
    async def update_farm(self, farm_id: str, updates: Dict) -> bool:
        """Update farm"""
        async with self.db.get_session() as session:
            from core_firmware import FarmModel
            
            await session.execute(
                update(FarmModel).
                where(FarmModel.id == farm_id).
                values(**updates)
            )
            
            logger.info(f"[DB] Farm updated: {farm_id}")
            return True
    
    async def delete_farm(self, farm_id: str) -> bool:
        """Delete farm"""
        async with self.db.get_session() as session:
            from core_firmware import FarmModel
            
            await session.execute(
                delete(FarmModel).where(FarmModel.id == farm_id)
            )
            
            logger.info(f"[DB] Farm deleted: {farm_id}")
            return True

# ======================================================================================================================
# PLOT OPERATIONS
# ======================================================================================================================

class PlotOperations:
    """Database operations for crop plots"""
    
    def __init__(self, db_pool: DatabasePool):
        self.db = db_pool
        
    async def create_plot(self, farm_id: str, name: str, crop_type: str,
                         boundary_wkt: str, metadata: Dict) -> str:
        """Create new plot"""
        async with self.db.get_session() as session:
            from core_firmware import PlotModel
            
            plot = PlotModel(
                farm_id=farm_id,
                name=name,
                crop_type=crop_type,
                boundary=WKTElement(boundary_wkt, srid=4326),
                status='healthy',
                metadata=metadata
            )
            
            session.add(plot)
            await session.flush()
            
            logger.info(f"[DB] Plot created: {plot.id}")
            return str(plot.id)
    
    async def get_plots_by_farm(self, farm_id: str) -> List[Dict]:
        """Get all plots for a farm"""
        async with self.db.get_session() as session:
            from core_firmware import PlotModel
            
            result = await session.execute(
                select(PlotModel).
                where(PlotModel.farm_id == farm_id).
                order_by(PlotModel.name)
            )
            plots = result.scalars().all()
            
            return [
                {
                    'id': str(p.id),
                    'name': p.name,
                    'crop_type': p.crop_type,
                    'status': p.status,
                    'area_hectares': float(p.area_hectares) if p.area_hectares else 0,
                    'planting_date': p.planting_date.isoformat() if p.planting_date else None
                }
                for p in plots
            ]
    
    async def update_plot_status(self, plot_id: str, status: str, health_score: float = None):
        """Update plot health status"""
        async with self.db.get_session() as session:
            from core_firmware import PlotModel
            
            updates = {'status': status, 'updated_at': datetime.utcnow()}
            if health_score is not None:
                updates['health_score'] = health_score
            
            await session.execute(
                update(PlotModel).
                where(PlotModel.id == plot_id).
                values(**updates)
            )
            
            logger.info(f"[DB] Plot status updated: {plot_id} -> {status}")
    
    async def get_plots_needing_attention(self, farm_id: str = None) -> List[Dict]:
        """Get plots with health issues"""
        async with self.db.get_session() as session:
            from core_firmware import PlotModel
            
            query = select(PlotModel).where(
                PlotModel.status.in_(['needs_attention', 'diseased', 'pest_infestation', 'critical'])
            )
            
            if farm_id:
                query = query.where(PlotModel.farm_id == farm_id)
            
            result = await session.execute(query.order_by(PlotModel.health_score))
            plots = result.scalars().all()
            
            return [
                {
                    'id': str(p.id),
                    'name': p.name,
                    'farm_id': str(p.farm_id),
                    'status': p.status,
                    'health_score': p.health_score,
                    'crop_type': p.crop_type
                }
                for p in plots
            ]

# ======================================================================================================================
# DEVICE OPERATIONS
# ======================================================================================================================

class DeviceOperations:
    """Database operations for ESP32 devices"""
    
    def __init__(self, db_pool: DatabasePool):
        self.db = db_pool
        
    async def register_device(self, device_id: str, device_type: str,
                             location: Tuple[float, float], metadata: Dict) -> bool:
        """Register new device"""
        async with self.db.get_session() as session:
            from core_firmware import DeviceModel
            
            device = DeviceModel(
                device_id=device_id,
                device_type=device_type,
                location=f'POINT({location[1]} {location[0]})',
                status='online',
                firmware_version='1.0.0',
                metadata=metadata,
                last_heartbeat=datetime.utcnow()
            )
            
            session.add(device)
            logger.info(f"[DB] Device registered: {device_id}")
            return True
    
    async def update_device_heartbeat(self, device_id: str, battery_level: float = None,
                                     signal_strength: int = None):
        """Update device heartbeat"""
        async with self.db.get_session() as session:
            from core_firmware import DeviceModel
            
            updates = {'last_heartbeat': datetime.utcnow()}
            if battery_level is not None:
                updates['battery_level'] = battery_level
            if signal_strength is not None:
                updates['signal_strength'] = signal_strength
            
            await session.execute(
                update(DeviceModel).
                where(DeviceModel.device_id == device_id).
                values(**updates)
            )
    
    async def get_online_devices(self, timeout_minutes: int = 5) -> List[Dict]:
        """Get devices that are online"""
        async with self.db.get_session() as session:
            from core_firmware import DeviceModel
            
            cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
            
            result = await session.execute(
                select(DeviceModel).
                where(DeviceModel.last_heartbeat > cutoff_time)
            )
            devices = result.scalars().all()
            
            return [
                {
                    'device_id': d.device_id,
                    'device_type': d.device_type,
                    'battery_level': d.battery_level,
                    'signal_strength': d.signal_strength,
                    'location': (d.location.x, d.location.y) if d.location else None
                }
                for d in devices
            ]
    
    async def get_devices_near_location(self, latitude: float, longitude: float,
                                       radius_meters: float) -> List[Dict]:
        """Get devices within radius of location"""
        async with self.db.get_session() as session:
            from core_firmware import DeviceModel
            
            point = f'POINT({longitude} {latitude})'
            
            result = await session.execute(
                select(DeviceModel).
                where(ST_DWithin(
                    DeviceModel.location,
                    WKTElement(point, srid=4326),
                    radius_meters
                ))
            )
            devices = result.scalars().all()
            
            return [{'device_id': d.device_id, 'device_type': d.device_type} for d in devices]

# ======================================================================================================================
# DETECTION OPERATIONS
# ======================================================================================================================

class DetectionOperations:
    """Database operations for AI detections"""
    
    def __init__(self, db_pool: DatabasePool):
        self.db = db_pool
        
    async def create_detection(self, camera_id: str, class_name: str, confidence: float,
                              bounding_box: Dict, location: Tuple[float, float],
                              image_path: str, metadata: Dict) -> str:
        """Create new detection"""
        async with self.db.get_session() as session:
            from core_firmware import DetectionModel
            
            detection = DetectionModel(
                camera_id=camera_id,
                class_name=class_name,
                confidence=confidence,
                bounding_box=bounding_box,
                location=f'POINT({location[1]} {location[0]})',
                image_path=image_path,
                metadata=metadata,
                timestamp=datetime.utcnow()
            )
            
            session.add(detection)
            await session.flush()
            
            logger.info(f"[DB] Detection created: {class_name} at confidence {confidence:.2f}")
            return str(detection.id)
    
    async def get_recent_detections(self, hours: int = 24, farm_id: str = None,
                                   min_confidence: float = 0.7) -> List[Dict]:
        """Get recent detections"""
        async with self.db.get_session() as session:
            from core_firmware import DetectionModel, CameraModel
            
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            query = select(DetectionModel).where(
                and_(
                    DetectionModel.timestamp > cutoff_time,
                    DetectionModel.confidence >= min_confidence
                )
            ).order_by(DetectionModel.timestamp.desc())
            
            result = await session.execute(query)
            detections = result.scalars().all()
            
            return [
                {
                    'id': str(d.id),
                    'class_name': d.class_name,
                    'confidence': d.confidence,
                    'location': (d.location.x, d.location.y) if d.location else None,
                    'timestamp': d.timestamp.isoformat()
                }
                for d in detections
            ]
    
    async def get_detections_by_plot(self, plot_id: str, days: int = 7) -> List[Dict]:
        """Get detections within a plot boundary"""
        async with self.db.get_session() as session:
            from core_firmware import DetectionModel, PlotModel
            
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            
            # Get plot boundary
            plot_result = await session.execute(
                select(PlotModel).where(PlotModel.id == plot_id)
            )
            plot = plot_result.scalar_one_or_none()
            
            if not plot:
                return []
            
            # Find detections within boundary
            result = await session.execute(
                select(DetectionModel).where(
                    and_(
                        ST_Contains(plot.boundary, DetectionModel.location),
                        DetectionModel.timestamp > cutoff_time
                    )
                )
            )
            detections = result.scalars().all()
            
            return [
                {
                    'id': str(d.id),
                    'class_name': d.class_name,
                    'confidence': d.confidence,
                    'timestamp': d.timestamp.isoformat()
                }
                for d in detections
            ]
    
    async def get_disease_statistics(self, farm_id: str = None, days: int = 30) -> Dict:
        """Get disease detection statistics"""
        async with self.db.get_session() as session:
            from core_firmware import DetectionModel
            
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            
            # Count by disease class
            result = await session.execute(
                select(
                    DetectionModel.class_name,
                    func.count(DetectionModel.id).label('count'),
                    func.avg(DetectionModel.confidence).label('avg_confidence')
                ).where(
                    DetectionModel.timestamp > cutoff_time
                ).group_by(DetectionModel.class_name)
            )
            
            stats = result.all()
            
            return {
                'total_detections': sum(s.count for s in stats),
                'by_disease': {
                    s.class_name: {
                        'count': s.count,
                        'avg_confidence': float(s.avg_confidence)
                    }
                    for s in stats
                }
            }

# ======================================================================================================================
# INCIDENT OPERATIONS
# ======================================================================================================================

class IncidentOperations:
    """Database operations for field incidents"""
    
    def __init__(self, db_pool: DatabasePool):
        self.db = db_pool
        
    async def create_incident(self, plot_id: str, detection_id: str, incident_type: str,
                             severity: int, location: Tuple[float, float],
                             description: str, recommended_action: str) -> str:
        """Create new incident"""
        async with self.db.get_session() as session:
            from core_firmware import IncidentModel
            
            incident = IncidentModel(
                plot_id=plot_id,
                detection_id=detection_id,
                incident_type=incident_type,
                severity=severity,
                location=f'POINT({location[1]} {location[0]})',
                description=description,
                recommended_action=recommended_action,
                status='open',
                reported_at=datetime.utcnow()
            )
            
            session.add(incident)
            await session.flush()
            
            logger.info(f"[DB] Incident created: {incident_type} (Severity {severity})")
            return str(incident.id)
    
    async def get_active_incidents(self, farm_id: str = None, severity_min: int = 1) -> List[Dict]:
        """Get active incidents"""
        async with self.db.get_session() as session:
            from core_firmware import IncidentModel, PlotModel
            
            query = select(IncidentModel).where(
                and_(
                    IncidentModel.status.in_(['open', 'assigned', 'in_progress']),
                    IncidentModel.severity >= severity_min
                )
            ).order_by(IncidentModel.severity.desc(), IncidentModel.reported_at)
            
            result = await session.execute(query)
            incidents = result.scalars().all()
            
            return [
                {
                    'id': str(i.id),
                    'incident_type': i.incident_type,
                    'severity': i.severity,
                    'status': i.status,
                    'location': (i.location.x, i.location.y) if i.location else None,
                    'description': i.description,
                    'reported_at': i.reported_at.isoformat()
                }
                for i in incidents
            ]
    
    async def assign_incident(self, incident_id: str, worker_id: str):
        """Assign incident to worker"""
        async with self.db.get_session() as session:
            from core_firmware import IncidentModel
            
            await session.execute(
                update(IncidentModel).
                where(IncidentModel.id == incident_id).
                values(
                    assigned_to=worker_id,
                    status='assigned',
                    assigned_at=datetime.utcnow()
                )
            )
            
            logger.info(f"[DB] Incident {incident_id} assigned to {worker_id}")
    
    async def resolve_incident(self, incident_id: str, resolution_notes: str,
                              resolution_images: List[str] = None):
        """Resolve incident"""
        async with self.db.get_session() as session:
            from core_firmware import IncidentModel
            
            await session.execute(
                update(IncidentModel).
                where(IncidentModel.id == incident_id).
                values(
                    status='resolved',
                    resolution_notes=resolution_notes,
                    resolution_images=resolution_images or [],
                    resolved_at=datetime.utcnow()
                )
            )
            
            logger.info(f"[DB] Incident resolved: {incident_id}")

# ======================================================================================================================
# TASK OPERATIONS
# ======================================================================================================================

class TaskOperations:
    """Database operations for field tasks"""
    
    def __init__(self, db_pool: DatabasePool):
        self.db = db_pool
        
    async def create_task(self, incident_id: str, task_type: str, priority: int,
                         location: Tuple[float, float], description: str,
                         estimated_duration_minutes: int) -> str:
        """Create new task"""
        async with self.db.get_session() as session:
            from core_firmware import TaskModel
            
            task = TaskModel(
                incident_id=incident_id,
                task_type=task_type,
                priority=priority,
                location=f'POINT({location[1]} {location[0]})',
                description=description,
                estimated_duration_minutes=estimated_duration_minutes,
                status='pending',
                created_at=datetime.utcnow()
            )
            
            session.add(task)
            await session.flush()
            
            logger.info(f"[DB] Task created: {task_type} (Priority {priority})")
            return str(task.id)
    
    async def assign_task(self, task_id: str, worker_id: str):
        """Assign task to worker"""
        async with self.db.get_session() as session:
            from core_firmware import TaskModel
            
            await session.execute(
                update(TaskModel).
                where(TaskModel.id == task_id).
                values(
                    assigned_to=worker_id,
                    status='assigned',
                    assigned_at=datetime.utcnow()
                )
            )
            
            logger.info(f"[DB] Task {task_id} assigned to {worker_id}")
    
    async def get_worker_tasks(self, worker_id: str, include_completed: bool = False) -> List[Dict]:
        """Get tasks for a worker"""
        async with self.db.get_session() as session:
            from core_firmware import TaskModel
            
            if include_completed:
                query = select(TaskModel).where(TaskModel.assigned_to == worker_id)
            else:
                query = select(TaskModel).where(
                    and_(
                        TaskModel.assigned_to == worker_id,
                        TaskModel.status != 'completed'
                    )
                )
            
            query = query.order_by(TaskModel.priority.desc(), TaskModel.due_date)
            result = await session.execute(query)
            tasks = result.scalars().all()
            
            return [
                {
                    'id': str(t.id),
                    'task_type': t.task_type,
                    'priority': t.priority,
                    'status': t.status,
                    'location': (t.location.x, t.location.y) if t.location else None,
                    'description': t.description,
                    'estimated_duration': t.estimated_duration_minutes
                }
                for t in tasks
            ]
    
    async def complete_task(self, task_id: str, completion_notes: str,
                           completion_images: List[str] = None):
        """Mark task as completed"""
        async with self.db.get_session() as session:
            from core_firmware import TaskModel
            
            await session.execute(
                update(TaskModel).
                where(TaskModel.id == task_id).
                values(
                    status='completed',
                    completion_notes=completion_notes,
                    completion_images=completion_images or [],
                    completed_at=datetime.utcnow()
                )
            )
            
            logger.info(f"[DB] Task completed: {task_id}")

# ======================================================================================================================
# CACHE MANAGER
# ======================================================================================================================

class CacheManager:
    """Redis cache manager for performance optimization"""
    
    def __init__(self, redis_url: str = 'redis://localhost:6379'):
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None
        
    async def initialize(self):
        """Initialize Redis connection"""
        self.redis = await aioredis.from_url(
            self.redis_url,
            encoding='utf-8',
            decode_responses=True
        )
        logger.info("[CACHE] Redis connection established")
    
    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
        logger.info("[CACHE] Redis connection closed")
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        return await self.redis.get(key)
    
    async def set(self, key: str, value: str, expire_seconds: int = 300):
        """Set value in cache"""
        await self.redis.set(key, value, ex=expire_seconds)
    
    async def delete(self, key: str):
        """Delete key from cache"""
        await self.redis.delete(key)
    
    async def get_json(self, key: str) -> Optional[Dict]:
        """Get JSON value from cache"""
        value = await self.get(key)
        return json.loads(value) if value else None
    
    async def set_json(self, key: str, value: Dict, expire_seconds: int = 300):
        """Set JSON value in cache"""
        await self.set(key, json.dumps(value), expire_seconds)
    
    async def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern"""
        keys = []
        async for key in self.redis.scan_iter(match=pattern):
            keys.append(key)
        
        if keys:
            await self.redis.delete(*keys)
            logger.info(f"[CACHE] Invalidated {len(keys)} keys matching {pattern}")

# ======================================================================================================================
# QUERY OPTIMIZER
# ======================================================================================================================

class QueryOptimizer:
    """Optimizes database queries with caching and indexing"""
    
    def __init__(self, db_pool: DatabasePool, cache_manager: CacheManager):
        self.db = db_pool
        self.cache = cache_manager
        
    async def get_with_cache(self, cache_key: str, query_func, expire_seconds: int = 300):
        """Get data with cache fallback"""
        # Try cache first
        cached = await self.cache.get_json(cache_key)
        if cached:
            logger.debug(f"[CACHE] Hit: {cache_key}")
            return cached
        
        # Cache miss - query database
        logger.debug(f"[CACHE] Miss: {cache_key}")
        result = await query_func()
        
        # Store in cache
        await self.cache.set_json(cache_key, result, expire_seconds)
        
        return result
    
    async def invalidate_farm_cache(self, farm_id: str):
        """Invalidate all farm-related cache entries"""
        await self.cache.invalidate_pattern(f"farm:{farm_id}:*")
    
    async def invalidate_plot_cache(self, plot_id: str):
        """Invalidate all plot-related cache entries"""
        await self.cache.invalidate_pattern(f"plot:{plot_id}:*")

# ======================================================================================================================
# END OF DATABASE OPERATIONS MODULE
# Lines in this file: ~900+
# Combined total: ~6,400+
# Remaining for 50k: ~43,600 lines
# ======================================================================================================================
