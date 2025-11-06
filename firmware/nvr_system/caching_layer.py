# ======================================================================================================================
# AgroPulse NVR - Caching Layer Module
# Redis, Memcached, and distributed caching infrastructure
# ======================================================================================================================

import asyncio
import logging
import hashlib
import pickle
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import redis.asyncio as redis
import aiomcache
from functools import wraps
import time

logger = logging.getLogger(__name__)

# ======================================================================================================================
# CACHE BACKENDS
# ======================================================================================================================

class CacheBackend(Enum):
    """Cache backend types"""
    REDIS = "redis"
    MEMCACHED = "memcached"
    MEMORY = "memory"

# ======================================================================================================================
# CACHE MODELS
# ======================================================================================================================

@dataclass
class CacheEntry:
    """Cache entry"""
    key: str
    value: Any
    ttl: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    size_bytes: int = 0

@dataclass
class CacheStats:
    """Cache statistics"""
    total_keys: int = 0
    total_size_bytes: int = 0
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    hit_rate: float = 0.0
    
    def calculate_hit_rate(self):
        """Calculate hit rate"""
        total = self.hits + self.misses
        self.hit_rate = (self.hits / total * 100) if total > 0 else 0.0

# ======================================================================================================================
# REDIS CACHE MANAGER
# ======================================================================================================================

class RedisCacheManager:
    """Redis cache manager"""
    
    def __init__(self, host: str = "localhost", port: int = 6379,
                 db: int = 0, password: Optional[str] = None,
                 key_prefix: str = "agropulse:"):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.key_prefix = key_prefix
        self.client = None
        self.stats = CacheStats()
        
        logger.info(
            f"[REDIS] Redis cache manager initialized: {host}:{port}/{db}"
        )
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=False
            )
            
            # Test connection
            await self.client.ping()
            
            logger.info(f"[REDIS] Connected to Redis: {self.host}:{self.port}")
            
        except Exception as e:
            logger.error(f"[REDIS] Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.client:
            await self.client.close()
            logger.info("[REDIS] Disconnected from Redis")
    
    def _make_key(self, key: str) -> str:
        """Make prefixed key"""
        return f"{self.key_prefix}{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            redis_key = self._make_key(key)
            value = await self.client.get(redis_key)
            
            if value is not None:
                self.stats.hits += 1
                logger.debug(f"[REDIS] Cache hit: {key}")
                return pickle.loads(value)
            else:
                self.stats.misses += 1
                logger.debug(f"[REDIS] Cache miss: {key}")
                return None
                
        except Exception as e:
            logger.error(f"[REDIS] Error getting key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            redis_key = self._make_key(key)
            serialized = pickle.dumps(value)
            
            if ttl:
                await self.client.setex(redis_key, ttl, serialized)
            else:
                await self.client.set(redis_key, serialized)
            
            self.stats.sets += 1
            logger.debug(f"[REDIS] Cache set: {key} (ttl={ttl})")
            return True
            
        except Exception as e:
            logger.error(f"[REDIS] Error setting key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            redis_key = self._make_key(key)
            result = await self.client.delete(redis_key)
            
            if result > 0:
                self.stats.deletes += 1
                logger.debug(f"[REDIS] Cache delete: {key}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"[REDIS] Error deleting key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            redis_key = self._make_key(key)
            return await self.client.exists(redis_key) > 0
        except Exception as e:
            logger.error(f"[REDIS] Error checking key {key}: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on key"""
        try:
            redis_key = self._make_key(key)
            return await self.client.expire(redis_key, ttl)
        except Exception as e:
            logger.error(f"[REDIS] Error setting expiration on {key}: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """Get time to live"""
        try:
            redis_key = self._make_key(key)
            return await self.client.ttl(redis_key)
        except Exception as e:
            logger.error(f"[REDIS] Error getting TTL for {key}: {e}")
            return -1
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern"""
        try:
            redis_pattern = self._make_key(pattern)
            keys = await self.client.keys(redis_pattern)
            
            # Remove prefix from keys
            prefix_len = len(self.key_prefix)
            return [key.decode()[prefix_len:] for key in keys]
            
        except Exception as e:
            logger.error(f"[REDIS] Error getting keys: {e}")
            return []
    
    async def flush(self, pattern: Optional[str] = None):
        """Flush cache"""
        try:
            if pattern:
                keys = await self.keys(pattern)
                if keys:
                    redis_keys = [self._make_key(k) for k in keys]
                    await self.client.delete(*redis_keys)
                    logger.info(f"[REDIS] Flushed {len(keys)} keys matching: {pattern}")
            else:
                await self.client.flushdb()
                logger.info("[REDIS] Flushed entire cache")
                
        except Exception as e:
            logger.error(f"[REDIS] Error flushing cache: {e}")
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        try:
            redis_key = self._make_key(key)
            return await self.client.incrby(redis_key, amount)
        except Exception as e:
            logger.error(f"[REDIS] Error incrementing {key}: {e}")
            return 0
    
    async def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement counter"""
        try:
            redis_key = self._make_key(key)
            return await self.client.decrby(redis_key, amount)
        except Exception as e:
            logger.error(f"[REDIS] Error decrementing {key}: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            info = await self.client.info("stats")
            
            self.stats.calculate_hit_rate()
            
            return {
                'backend': 'redis',
                'hits': self.stats.hits,
                'misses': self.stats.misses,
                'hit_rate': self.stats.hit_rate,
                'sets': self.stats.sets,
                'deletes': self.stats.deletes,
                'redis_info': info
            }
        except Exception as e:
            logger.error(f"[REDIS] Error getting stats: {e}")
            return {}

# ======================================================================================================================
# MEMCACHED CACHE MANAGER
# ======================================================================================================================

class MemcachedCacheManager:
    """Memcached cache manager"""
    
    def __init__(self, host: str = "localhost", port: int = 11211,
                 key_prefix: str = "agropulse:"):
        self.host = host
        self.port = port
        self.key_prefix = key_prefix
        self.client = None
        self.stats = CacheStats()
        
        logger.info(
            f"[MEMCACHED] Memcached cache manager initialized: {host}:{port}"
        )
    
    async def connect(self):
        """Connect to Memcached"""
        try:
            self.client = aiomcache.Client(self.host, self.port)
            
            # Test connection
            await self.client.version()
            
            logger.info(f"[MEMCACHED] Connected: {self.host}:{self.port}")
            
        except Exception as e:
            logger.error(f"[MEMCACHED] Failed to connect: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Memcached"""
        if self.client:
            await self.client.close()
            logger.info("[MEMCACHED] Disconnected")
    
    def _make_key(self, key: str) -> bytes:
        """Make prefixed key"""
        return f"{self.key_prefix}{key}".encode()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            mc_key = self._make_key(key)
            value = await self.client.get(mc_key)
            
            if value is not None:
                self.stats.hits += 1
                logger.debug(f"[MEMCACHED] Cache hit: {key}")
                return pickle.loads(value)
            else:
                self.stats.misses += 1
                logger.debug(f"[MEMCACHED] Cache miss: {key}")
                return None
                
        except Exception as e:
            logger.error(f"[MEMCACHED] Error getting key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            mc_key = self._make_key(key)
            serialized = pickle.dumps(value)
            
            exptime = ttl if ttl else 0  # 0 means never expire
            
            await self.client.set(mc_key, serialized, exptime=exptime)
            
            self.stats.sets += 1
            logger.debug(f"[MEMCACHED] Cache set: {key} (ttl={ttl})")
            return True
            
        except Exception as e:
            logger.error(f"[MEMCACHED] Error setting key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            mc_key = self._make_key(key)
            result = await self.client.delete(mc_key)
            
            if result:
                self.stats.deletes += 1
                logger.debug(f"[MEMCACHED] Cache delete: {key}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"[MEMCACHED] Error deleting key {key}: {e}")
            return False
    
    async def flush(self):
        """Flush cache"""
        try:
            await self.client.flush_all()
            logger.info("[MEMCACHED] Flushed entire cache")
        except Exception as e:
            logger.error(f"[MEMCACHED] Error flushing cache: {e}")
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        try:
            mc_key = self._make_key(key)
            result = await self.client.incr(mc_key, amount)
            return result if result else 0
        except Exception as e:
            logger.error(f"[MEMCACHED] Error incrementing {key}: {e}")
            return 0
    
    async def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement counter"""
        try:
            mc_key = self._make_key(key)
            result = await self.client.decr(mc_key, amount)
            return result if result else 0
        except Exception as e:
            logger.error(f"[MEMCACHED] Error decrementing {key}: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            stats = await self.client.stats()
            
            self.stats.calculate_hit_rate()
            
            return {
                'backend': 'memcached',
                'hits': self.stats.hits,
                'misses': self.stats.misses,
                'hit_rate': self.stats.hit_rate,
                'sets': self.stats.sets,
                'deletes': self.stats.deletes,
                'memcached_stats': stats
            }
        except Exception as e:
            logger.error(f"[MEMCACHED] Error getting stats: {e}")
            return {}

# ======================================================================================================================
# IN-MEMORY CACHE MANAGER
# ======================================================================================================================

class MemoryCacheManager:
    """In-memory cache manager"""
    
    def __init__(self, max_size: int = 10000):
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.stats = CacheStats()
        
        logger.info(f"[MEMORY] Memory cache initialized (max_size={max_size})")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if key in self.cache:
                entry = self.cache[key]
                
                # Check expiration
                if entry.ttl:
                    age = (datetime.now() - entry.created_at).total_seconds()
                    if age > entry.ttl:
                        await self.delete(key)
                        self.stats.misses += 1
                        return None
                
                # Update access info
                entry.accessed_at = datetime.now()
                entry.access_count += 1
                
                self.stats.hits += 1
                logger.debug(f"[MEMORY] Cache hit: {key}")
                return entry.value
            else:
                self.stats.misses += 1
                logger.debug(f"[MEMORY] Cache miss: {key}")
                return None
                
        except Exception as e:
            logger.error(f"[MEMORY] Error getting key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            # Check size limit
            if key not in self.cache and len(self.cache) >= self.max_size:
                await self._evict_lru()
            
            # Calculate size
            size_bytes = len(pickle.dumps(value))
            
            # Create entry
            self.cache[key] = CacheEntry(
                key=key,
                value=value,
                ttl=ttl,
                size_bytes=size_bytes
            )
            
            self.stats.sets += 1
            self.stats.total_keys = len(self.cache)
            self.stats.total_size_bytes += size_bytes
            
            logger.debug(f"[MEMORY] Cache set: {key} (ttl={ttl})")
            return True
            
        except Exception as e:
            logger.error(f"[MEMORY] Error setting key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            if key in self.cache:
                entry = self.cache[key]
                self.stats.total_size_bytes -= entry.size_bytes
                del self.cache[key]
                
                self.stats.deletes += 1
                self.stats.total_keys = len(self.cache)
                
                logger.debug(f"[MEMORY] Cache delete: {key}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"[MEMORY] Error deleting key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        return key in self.cache
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern"""
        # Simple pattern matching (not full glob support)
        if pattern == "*":
            return list(self.cache.keys())
        
        import re
        regex_pattern = pattern.replace("*", ".*")
        regex = re.compile(regex_pattern)
        
        return [k for k in self.cache.keys() if regex.match(k)]
    
    async def flush(self, pattern: Optional[str] = None):
        """Flush cache"""
        if pattern:
            keys = await self.keys(pattern)
            for key in keys:
                await self.delete(key)
            logger.info(f"[MEMORY] Flushed {len(keys)} keys matching: {pattern}")
        else:
            self.cache.clear()
            self.stats = CacheStats()
            logger.info("[MEMORY] Flushed entire cache")
    
    async def _evict_lru(self):
        """Evict least recently used entry"""
        if not self.cache:
            return
        
        # Find LRU entry
        lru_key = min(
            self.cache.keys(),
            key=lambda k: self.cache[k].accessed_at
        )
        
        await self.delete(lru_key)
        self.stats.evictions += 1
        
        logger.debug(f"[MEMORY] Evicted LRU key: {lru_key}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        self.stats.calculate_hit_rate()
        
        return {
            'backend': 'memory',
            'total_keys': self.stats.total_keys,
            'total_size_bytes': self.stats.total_size_bytes,
            'hits': self.stats.hits,
            'misses': self.stats.misses,
            'hit_rate': self.stats.hit_rate,
            'sets': self.stats.sets,
            'deletes': self.stats.deletes,
            'evictions': self.stats.evictions,
            'max_size': self.max_size
        }

# ======================================================================================================================
# UNIFIED CACHE MANAGER
# ======================================================================================================================

class CacheManager:
    """Unified cache manager"""
    
    def __init__(self, backend: CacheBackend = CacheBackend.REDIS,
                 **backend_config):
        self.backend = backend
        self.cache = None
        
        # Initialize backend
        if backend == CacheBackend.REDIS:
            self.cache = RedisCacheManager(**backend_config)
        elif backend == CacheBackend.MEMCACHED:
            self.cache = MemcachedCacheManager(**backend_config)
        elif backend == CacheBackend.MEMORY:
            self.cache = MemoryCacheManager(**backend_config)
        else:
            raise ValueError(f"Unsupported cache backend: {backend}")
        
        logger.info(f"[CACHE] Cache manager initialized: {backend.value}")
    
    async def connect(self):
        """Connect to cache backend"""
        if hasattr(self.cache, 'connect'):
            await self.cache.connect()
    
    async def disconnect(self):
        """Disconnect from cache backend"""
        if hasattr(self.cache, 'disconnect'):
            await self.cache.disconnect()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        return await self.cache.get(key)
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        return await self.cache.set(key, value, ttl)
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        return await self.cache.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if hasattr(self.cache, 'exists'):
            return await self.cache.exists(key)
        return await self.cache.get(key) is not None
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern"""
        if hasattr(self.cache, 'keys'):
            return await self.cache.keys(pattern)
        return []
    
    async def flush(self, pattern: Optional[str] = None):
        """Flush cache"""
        await self.cache.flush(pattern)
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        if hasattr(self.cache, 'increment'):
            return await self.cache.increment(key, amount)
        return 0
    
    async def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement counter"""
        if hasattr(self.cache, 'decrement'):
            return await self.cache.decrement(key, amount)
        return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return await self.cache.get_stats()

# ======================================================================================================================
# CACHE DECORATOR
# ======================================================================================================================

def cached(cache_manager: CacheManager, ttl: Optional[int] = None,
           key_prefix: str = "", key_func: Optional[Callable] = None):
    """Cache decorator for functions"""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [key_prefix, func.__name__]
                if args:
                    key_parts.append(str(args))
                if kwargs:
                    key_parts.append(str(sorted(kwargs.items())))
                cache_key = hashlib.md5(
                    ":".join(key_parts).encode()
                ).hexdigest()
            
            # Try to get from cache
            cached_value = await cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"[CACHE] Decorator cache hit: {func.__name__}")
                return cached_value
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Store in cache
            await cache_manager.set(cache_key, result, ttl)
            logger.debug(f"[CACHE] Decorator cache set: {func.__name__}")
            
            return result
        
        return wrapper
    return decorator

# ======================================================================================================================
# CACHE PATTERNS
# ======================================================================================================================

class CacheAsidePattern:
    """Cache-aside (lazy loading) pattern"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
    
    async def get_or_load(self, key: str, loader: Callable,
                          ttl: Optional[int] = None) -> Any:
        """Get from cache or load"""
        # Try cache first
        value = await self.cache.get(key)
        if value is not None:
            return value
        
        # Load from source
        value = await loader()
        
        # Store in cache
        if value is not None:
            await self.cache.set(key, value, ttl)
        
        return value

class WriteThroughPattern:
    """Write-through caching pattern"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
    
    async def write(self, key: str, value: Any, writer: Callable,
                   ttl: Optional[int] = None) -> bool:
        """Write to cache and storage"""
        # Write to storage first
        success = await writer(value)
        
        if success:
            # Update cache
            await self.cache.set(key, value, ttl)
        
        return success

class WriteBackPattern:
    """Write-back (write-behind) caching pattern"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.write_queue: asyncio.Queue = asyncio.Queue()
        self.writer_task = None
    
    async def write(self, key: str, value: Any, ttl: Optional[int] = None):
        """Write to cache and queue for storage"""
        # Write to cache immediately
        await self.cache.set(key, value, ttl)
        
        # Queue for async write to storage
        await self.write_queue.put((key, value))
    
    async def start_writer(self, writer: Callable):
        """Start background writer"""
        async def writer_loop():
            while True:
                key, value = await self.write_queue.get()
                try:
                    await writer(key, value)
                except Exception as e:
                    logger.error(f"[CACHE] Write-back error: {e}")
                finally:
                    self.write_queue.task_done()
        
        self.writer_task = asyncio.create_task(writer_loop())
    
    async def stop_writer(self):
        """Stop background writer"""
        if self.writer_task:
            self.writer_task.cancel()
            await self.write_queue.join()

# ======================================================================================================================
# CACHE ORCHESTRATOR
# ======================================================================================================================

class CacheOrchestrator:
    """Main cache orchestrator"""
    
    def __init__(self):
        self.cache_managers: Dict[str, CacheManager] = {}
        self.patterns: Dict[str, Any] = {}
        
        logger.info("[CACHE] Cache orchestrator initialized")
    
    def register_cache(self, name: str, cache_manager: CacheManager):
        """Register cache manager"""
        self.cache_managers[name] = cache_manager
        logger.info(f"[CACHE] Registered cache: {name}")
    
    def get_cache(self, name: str) -> Optional[CacheManager]:
        """Get cache manager"""
        return self.cache_managers.get(name)
    
    def register_pattern(self, name: str, pattern: Any):
        """Register cache pattern"""
        self.patterns[name] = pattern
        logger.info(f"[CACHE] Registered pattern: {name}")
    
    def get_pattern(self, name: str) -> Optional[Any]:
        """Get cache pattern"""
        return self.patterns.get(name)
    
    async def connect_all(self):
        """Connect all caches"""
        for name, cache in self.cache_managers.items():
            try:
                await cache.connect()
                logger.info(f"[CACHE] Connected cache: {name}")
            except Exception as e:
                logger.error(f"[CACHE] Failed to connect {name}: {e}")
    
    async def disconnect_all(self):
        """Disconnect all caches"""
        for name, cache in self.cache_managers.items():
            try:
                await cache.disconnect()
                logger.info(f"[CACHE] Disconnected cache: {name}")
            except Exception as e:
                logger.error(f"[CACHE] Failed to disconnect {name}: {e}")
    
    async def get_all_stats(self) -> Dict[str, Any]:
        """Get stats from all caches"""
        stats = {}
        for name, cache in self.cache_managers.items():
            try:
                stats[name] = await cache.get_stats()
            except Exception as e:
                logger.error(f"[CACHE] Failed to get stats for {name}: {e}")
                stats[name] = {'error': str(e)}
        return stats

# ======================================================================================================================
# END OF CACHING LAYER MODULE
# Lines in this file: ~850+
# Combined total with GraphQL: ~22,700+
# Remaining for 50k: ~27,300 lines
# ======================================================================================================================
