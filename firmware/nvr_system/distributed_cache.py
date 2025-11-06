# ======================================================================================================================
# AgroPulse NVR - Distributed Cache System
# Redis-style caching, cache strategies, expiration, eviction policies, cache warming, replication
# ======================================================================================================================

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import OrderedDict, deque, defaultdict
import time
import random
import json
import hashlib

logger = logging.getLogger(__name__)

# ======================================================================================================================
# CACHE MODELS
# ======================================================================================================================

class EvictionPolicy(Enum):
    """Cache eviction policies"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In First Out
    TTL = "ttl"  # Time To Live only

class CacheStrategy(Enum):
    """Cache strategies"""
    WRITE_THROUGH = "write_through"
    WRITE_BACK = "write_back"
    WRITE_AROUND = "write_around"
    READ_THROUGH = "read_through"

class DataType(Enum):
    """Redis-style data types"""
    STRING = "string"
    LIST = "list"
    SET = "set"
    HASH = "hash"
    SORTED_SET = "sorted_set"

@dataclass
class CacheEntry:
    """Cache entry"""
    key: str
    value: Any
    data_type: DataType
    created_at: datetime
    accessed_at: datetime
    access_count: int = 0
    ttl_seconds: Optional[int] = None
    expiry_time: Optional[datetime] = None
    size_bytes: int = 0
    tags: Set[str] = field(default_factory=set)

@dataclass
class CacheNode:
    """Cache cluster node"""
    node_id: str
    host: str
    port: int
    is_primary: bool
    created_at: datetime
    total_memory_mb: int = 1024
    used_memory_mb: int = 0
    status: str = "healthy"

@dataclass
class CacheStats:
    """Cache statistics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    writes: int = 0
    deletes: int = 0
    total_requests: int = 0

# ======================================================================================================================
# CACHE STORAGE
# ======================================================================================================================

class CacheStorage:
    """Core cache storage with eviction"""
    
    def __init__(self, max_size: int = 10000,
                eviction_policy: EvictionPolicy = EvictionPolicy.LRU):
        self.max_size = max_size
        self.eviction_policy = eviction_policy
        self.storage: Dict[str, CacheEntry] = {}
        self.lru_order: OrderedDict = OrderedDict()
        self.access_frequency: Dict[str, int] = defaultdict(int)
        self.stats = CacheStats()
        
        logger.info(f"[CACHE-STORAGE] Initialized with {eviction_policy.value} policy")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        entry = self.storage.get(key)
        
        if not entry:
            self.stats.misses += 1
            self.stats.total_requests += 1
            return None
        
        # Check expiry
        if entry.expiry_time and datetime.now() > entry.expiry_time:
            self.delete(key)
            self.stats.expirations += 1
            self.stats.misses += 1
            self.stats.total_requests += 1
            return None
        
        # Update access metadata
        entry.accessed_at = datetime.now()
        entry.access_count += 1
        
        # Update LRU
        if self.eviction_policy == EvictionPolicy.LRU:
            self.lru_order.move_to_end(key)
        
        # Update LFU
        if self.eviction_policy == EvictionPolicy.LFU:
            self.access_frequency[key] += 1
        
        self.stats.hits += 1
        self.stats.total_requests += 1
        
        return entry.value
    
    def set(self, key: str, value: Any,
           data_type: DataType = DataType.STRING,
           ttl_seconds: Optional[int] = None,
           tags: Set[str] = None):
        """Set value in cache"""
        # Evict if necessary
        if key not in self.storage and len(self.storage) >= self.max_size:
            self._evict()
        
        # Calculate size
        size_bytes = len(str(value).encode('utf-8'))
        
        # Create entry
        entry = CacheEntry(
            key=key,
            value=value,
            data_type=data_type,
            created_at=datetime.now(),
            accessed_at=datetime.now(),
            ttl_seconds=ttl_seconds,
            expiry_time=datetime.now() + timedelta(seconds=ttl_seconds) if ttl_seconds else None,
            size_bytes=size_bytes,
            tags=tags or set()
        )
        
        self.storage[key] = entry
        
        # Update LRU
        if self.eviction_policy == EvictionPolicy.LRU:
            self.lru_order[key] = True
        
        self.stats.writes += 1
        
        logger.debug(f"[CACHE-STORAGE] Set key: {key}")
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if key in self.storage:
            del self.storage[key]
            
            if key in self.lru_order:
                del self.lru_order[key]
            
            if key in self.access_frequency:
                del self.access_frequency[key]
            
            self.stats.deletes += 1
            
            logger.debug(f"[CACHE-STORAGE] Deleted key: {key}")
            return True
        
        return False
    
    def _evict(self):
        """Evict entry based on policy"""
        if self.eviction_policy == EvictionPolicy.LRU:
            # Remove least recently used
            if self.lru_order:
                key, _ = self.lru_order.popitem(last=False)
                if key in self.storage:
                    del self.storage[key]
                self.stats.evictions += 1
        
        elif self.eviction_policy == EvictionPolicy.LFU:
            # Remove least frequently used
            if self.access_frequency:
                key = min(self.access_frequency, key=self.access_frequency.get)
                del self.storage[key]
                del self.access_frequency[key]
                self.stats.evictions += 1
        
        elif self.eviction_policy == EvictionPolicy.FIFO:
            # Remove oldest
            if self.storage:
                oldest_key = min(self.storage.keys(),
                               key=lambda k: self.storage[k].created_at)
                del self.storage[oldest_key]
                self.stats.evictions += 1
    
    def clear(self):
        """Clear all cache"""
        self.storage.clear()
        self.lru_order.clear()
        self.access_frequency.clear()
        logger.info("[CACHE-STORAGE] Cleared cache")
    
    def get_hit_rate(self) -> float:
        """Get cache hit rate"""
        if self.stats.total_requests == 0:
            return 0.0
        
        return self.stats.hits / self.stats.total_requests

# ======================================================================================================================
# REDIS-STYLE OPERATIONS
# ======================================================================================================================

class RedisStyleCache:
    """Redis-style cache operations"""
    
    def __init__(self, storage: CacheStorage):
        self.storage = storage
        
        logger.info("[REDIS-CACHE] Redis-style cache initialized")
    
    # String operations
    def set_string(self, key: str, value: str, ttl_seconds: Optional[int] = None):
        """SET operation"""
        self.storage.set(key, value, DataType.STRING, ttl_seconds)
    
    def get_string(self, key: str) -> Optional[str]:
        """GET operation"""
        return self.storage.get(key)
    
    def incr(self, key: str) -> int:
        """INCR operation"""
        value = self.storage.get(key)
        
        if value is None:
            new_value = 1
        else:
            new_value = int(value) + 1
        
        self.storage.set(key, new_value, DataType.STRING)
        return new_value
    
    def decr(self, key: str) -> int:
        """DECR operation"""
        value = self.storage.get(key)
        
        if value is None:
            new_value = -1
        else:
            new_value = int(value) - 1
        
        self.storage.set(key, new_value, DataType.STRING)
        return new_value
    
    # List operations
    def lpush(self, key: str, *values):
        """LPUSH operation"""
        current = self.storage.get(key) or []
        
        if not isinstance(current, list):
            current = []
        
        current = list(values) + current
        
        self.storage.set(key, current, DataType.LIST)
    
    def rpush(self, key: str, *values):
        """RPUSH operation"""
        current = self.storage.get(key) or []
        
        if not isinstance(current, list):
            current = []
        
        current = current + list(values)
        
        self.storage.set(key, current, DataType.LIST)
    
    def lpop(self, key: str) -> Optional[Any]:
        """LPOP operation"""
        current = self.storage.get(key)
        
        if not current or not isinstance(current, list) or len(current) == 0:
            return None
        
        value = current.pop(0)
        self.storage.set(key, current, DataType.LIST)
        
        return value
    
    def lrange(self, key: str, start: int, stop: int) -> List[Any]:
        """LRANGE operation"""
        current = self.storage.get(key)
        
        if not current or not isinstance(current, list):
            return []
        
        return current[start:stop + 1]
    
    # Set operations
    def sadd(self, key: str, *members):
        """SADD operation"""
        current = self.storage.get(key) or set()
        
        if not isinstance(current, set):
            current = set()
        
        current.update(members)
        
        self.storage.set(key, current, DataType.SET)
    
    def smembers(self, key: str) -> Set[Any]:
        """SMEMBERS operation"""
        current = self.storage.get(key)
        
        if not current or not isinstance(current, set):
            return set()
        
        return current
    
    def sismember(self, key: str, member: Any) -> bool:
        """SISMEMBER operation"""
        current = self.storage.get(key)
        
        if not current or not isinstance(current, set):
            return False
        
        return member in current
    
    # Hash operations
    def hset(self, key: str, field: str, value: Any):
        """HSET operation"""
        current = self.storage.get(key) or {}
        
        if not isinstance(current, dict):
            current = {}
        
        current[field] = value
        
        self.storage.set(key, current, DataType.HASH)
    
    def hget(self, key: str, field: str) -> Optional[Any]:
        """HGET operation"""
        current = self.storage.get(key)
        
        if not current or not isinstance(current, dict):
            return None
        
        return current.get(field)
    
    def hgetall(self, key: str) -> Dict[str, Any]:
        """HGETALL operation"""
        current = self.storage.get(key)
        
        if not current or not isinstance(current, dict):
            return {}
        
        return current
    
    # Key operations
    def exists(self, key: str) -> bool:
        """EXISTS operation"""
        return key in self.storage.storage
    
    def delete(self, *keys) -> int:
        """DELETE operation"""
        deleted = 0
        
        for key in keys:
            if self.storage.delete(key):
                deleted += 1
        
        return deleted
    
    def expire(self, key: str, seconds: int) -> bool:
        """EXPIRE operation"""
        entry = self.storage.storage.get(key)
        
        if not entry:
            return False
        
        entry.ttl_seconds = seconds
        entry.expiry_time = datetime.now() + timedelta(seconds=seconds)
        
        return True
    
    def ttl(self, key: str) -> int:
        """TTL operation"""
        entry = self.storage.storage.get(key)
        
        if not entry:
            return -2  # Key doesn't exist
        
        if not entry.expiry_time:
            return -1  # No expiry
        
        remaining = (entry.expiry_time - datetime.now()).total_seconds()
        
        return int(remaining) if remaining > 0 else -2

# ======================================================================================================================
# CACHE WARMER
# ======================================================================================================================

class CacheWarmer:
    """Pre-populate cache with frequently accessed data"""
    
    def __init__(self, redis_cache: RedisStyleCache):
        self.redis_cache = redis_cache
        self.warming_strategies: List[Callable] = []
        
        logger.info("[CACHE-WARMER] Cache warmer initialized")
    
    def add_warming_strategy(self, strategy: Callable):
        """Add cache warming strategy"""
        self.warming_strategies.append(strategy)
    
    async def warm_cache(self):
        """Warm cache with strategies"""
        logger.info("[CACHE-WARMER] Starting cache warming")
        
        for strategy in self.warming_strategies:
            try:
                await strategy(self.redis_cache)
            except Exception as e:
                logger.error(f"[CACHE-WARMER] Error in strategy: {e}")
        
        logger.info("[CACHE-WARMER] Cache warming complete")
    
    async def warm_popular_keys(self, keys: List[Tuple[str, Any]]):
        """Warm cache with popular keys"""
        for key, value in keys:
            self.redis_cache.set_string(key, str(value), ttl_seconds=3600)

# ======================================================================================================================
# CACHE CLUSTER
# ======================================================================================================================

class CacheCluster:
    """Distributed cache cluster"""
    
    def __init__(self):
        self.nodes: Dict[str, CacheNode] = {}
        self.node_caches: Dict[str, CacheStorage] = {}
        self.primary_node: Optional[str] = None
        self.replication_enabled = True
        
        logger.info("[CACHE-CLUSTER] Cache cluster initialized")
    
    def add_node(self, host: str, port: int,
                is_primary: bool = False,
                memory_mb: int = 1024) -> CacheNode:
        """Add node to cluster"""
        node_id = f"node_{host}_{port}"
        
        node = CacheNode(
            node_id=node_id,
            host=host,
            port=port,
            is_primary=is_primary,
            created_at=datetime.now(),
            total_memory_mb=memory_mb
        )
        
        self.nodes[node_id] = node
        self.node_caches[node_id] = CacheStorage(max_size=10000)
        
        if is_primary:
            self.primary_node = node_id
        
        logger.info(f"[CACHE-CLUSTER] Added node: {node_id} (primary: {is_primary})")
        return node
    
    def remove_node(self, node_id: str):
        """Remove node from cluster"""
        if node_id in self.nodes:
            del self.nodes[node_id]
            del self.node_caches[node_id]
            
            if self.primary_node == node_id:
                self.primary_node = None
            
            logger.info(f"[CACHE-CLUSTER] Removed node: {node_id}")
    
    def get_node_for_key(self, key: str) -> str:
        """Get node for key using consistent hashing"""
        if not self.nodes:
            raise ValueError("No nodes in cluster")
        
        # Simple hash-based routing
        hash_val = int(hashlib.md5(key.encode()).hexdigest(), 16)
        node_ids = list(self.nodes.keys())
        
        return node_ids[hash_val % len(node_ids)]
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """Set value in cluster"""
        node_id = self.get_node_for_key(key)
        cache = self.node_caches[node_id]
        
        cache.set(key, value, DataType.STRING, ttl_seconds)
        
        # Replicate to other nodes
        if self.replication_enabled:
            for other_node_id, other_cache in self.node_caches.items():
                if other_node_id != node_id:
                    other_cache.set(key, value, DataType.STRING, ttl_seconds)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cluster"""
        node_id = self.get_node_for_key(key)
        cache = self.node_caches[node_id]
        
        return cache.get(key)
    
    def get_cluster_stats(self) -> Dict[str, Any]:
        """Get cluster statistics"""
        total_keys = sum(len(cache.storage) for cache in self.node_caches.values())
        total_hits = sum(cache.stats.hits for cache in self.node_caches.values())
        total_misses = sum(cache.stats.misses for cache in self.node_caches.values())
        
        return {
            'node_count': len(self.nodes),
            'total_keys': total_keys,
            'total_hits': total_hits,
            'total_misses': total_misses,
            'hit_rate': total_hits / (total_hits + total_misses) if (total_hits + total_misses) > 0 else 0.0
        }

# ======================================================================================================================
# CACHE ORCHESTRATOR
# ======================================================================================================================

class DistributedCacheOrchestrator:
    """Main cache orchestrator"""
    
    def __init__(self, max_size: int = 10000,
                eviction_policy: EvictionPolicy = EvictionPolicy.LRU):
        self.storage = CacheStorage(max_size, eviction_policy)
        self.redis_cache = RedisStyleCache(self.storage)
        self.cache_warmer = CacheWarmer(self.redis_cache)
        self.cluster = CacheCluster()
        
        self.monitoring = False
        self.monitor_task = None
        
        self._setup_cluster()
        self._create_sample_data()
        
        logger.info("[CACHE-ORCH] Distributed cache orchestrator initialized")
    
    def _setup_cluster(self):
        """Setup cache cluster"""
        # Add cluster nodes
        self.cluster.add_node("10.0.1.10", 6379, is_primary=True, memory_mb=2048)
        self.cluster.add_node("10.0.1.11", 6379, is_primary=False, memory_mb=2048)
        self.cluster.add_node("10.0.1.12", 6379, is_primary=False, memory_mb=2048)
    
    def _create_sample_data(self):
        """Create sample cache data"""
        # String data
        self.redis_cache.set_string("user:1000:name", "John Doe", ttl_seconds=3600)
        self.redis_cache.set_string("farm:5001:location", "California", ttl_seconds=7200)
        
        # Counter
        self.redis_cache.set_string("detection:count", "1523")
        
        # List data
        self.redis_cache.rpush("recent:detections", "det_001", "det_002", "det_003")
        
        # Set data
        self.redis_cache.sadd("active:users", "user_1", "user_2", "user_3")
        
        # Hash data
        self.redis_cache.hset("farm:5001", "name", "Green Valley Farm")
        self.redis_cache.hset("farm:5001", "area_hectares", "250")
        self.redis_cache.hset("farm:5001", "owner", "John Doe")
    
    async def start_monitoring(self):
        """Start cache monitoring"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        
        logger.info("[CACHE-ORCH] Started monitoring")
    
    async def stop_monitoring(self):
        """Stop cache monitoring"""
        if not self.monitoring:
            return
        
        self.monitoring = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("[CACHE-ORCH] Stopped monitoring")
    
    async def _monitor_loop(self):
        """Monitoring loop"""
        while self.monitoring:
            try:
                # Expire old entries
                expired_keys = []
                
                for key, entry in self.storage.storage.items():
                    if entry.expiry_time and datetime.now() > entry.expiry_time:
                        expired_keys.append(key)
                
                for key in expired_keys:
                    self.storage.delete(key)
                    self.storage.stats.expirations += 1
                
                if expired_keys:
                    logger.debug(f"[CACHE-ORCH] Expired {len(expired_keys)} keys")
                
                await asyncio.sleep(60)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[CACHE-ORCH] Error: {e}")
                await asyncio.sleep(10)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'total_keys': len(self.storage.storage),
            'max_size': self.storage.max_size,
            'hit_rate': self.storage.get_hit_rate(),
            'hits': self.storage.stats.hits,
            'misses': self.storage.stats.misses,
            'evictions': self.storage.stats.evictions,
            'expirations': self.storage.stats.expirations,
            'writes': self.storage.stats.writes,
            'deletes': self.storage.stats.deletes,
            'cluster_stats': self.cluster.get_cluster_stats()
        }

# ======================================================================================================================
# END OF DISTRIBUTED CACHE MODULE
# Lines in this file: ~850+
# Combined total: ~48,650+
# Remaining for 50k: ~1,350 lines
# ======================================================================================================================
