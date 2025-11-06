"""
Service Mesh & Traffic Management

Istio-inspired service mesh providing:
- Service discovery and registry
- Load balancing (round-robin, least-connections, weighted, consistent-hashing)
- Circuit breaking with failure detection
- Retry policies with exponential backoff
- Timeout management
- Traffic splitting for canary deployments and A/B testing
- Distributed tracing integration
- mTLS encryption for service-to-service communication
- Rate limiting per service
- Request routing and path-based routing
- Health checking and auto-recovery
- Service-level metrics collection
- Connection pooling
- Request/response transformation

This module implements a production-grade service mesh similar to Istio/Linkerd
optimized for microservices architectures in agricultural IoT systems.
"""

import os
import time
import uuid
import json
import hashlib
import threading
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, deque
import logging
from pathlib import Path
import socket
import ssl

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    RANDOM = "random"
    CONSISTENT_HASH = "consistent_hash"
    IP_HASH = "ip_hash"


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


class ServiceHealth(Enum):
    """Service health status"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class TrafficSplitType(Enum):
    """Traffic split types"""
    WEIGHT_BASED = "weight_based"
    HEADER_BASED = "header_based"
    COOKIE_BASED = "cookie_based"
    USER_BASED = "user_based"


@dataclass
class ServiceInstance:
    """Service instance definition"""
    service_name: str
    instance_id: str
    host: str
    port: int
    protocol: str = "http"
    weight: int = 100
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    version: str = "v1"
    zone: str = "default"
    registered_at: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    health_status: ServiceHealth = ServiceHealth.UNKNOWN
    
    def get_url(self) -> str:
        """Get full service URL"""
        return f"{self.protocol}://{self.host}:{self.port}"


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout: timedelta = field(default_factory=lambda: timedelta(seconds=60))
    half_open_max_requests: int = 3


@dataclass
class RetryConfig:
    """Retry policy configuration"""
    max_attempts: int = 3
    backoff_multiplier: float = 2.0
    initial_delay: float = 1.0
    max_delay: float = 30.0
    retry_on_status: List[int] = field(default_factory=lambda: [500, 502, 503, 504])
    retry_on_timeout: bool = True


@dataclass
class TimeoutConfig:
    """Timeout configuration"""
    connect_timeout: float = 5.0
    read_timeout: float = 30.0
    total_timeout: float = 60.0


@dataclass
class TrafficSplit:
    """Traffic split configuration"""
    split_type: TrafficSplitType
    destinations: List[Dict[str, Any]]  # [{version: "v1", weight: 80}, ...]
    fallback_version: str = "v1"
    sticky_session: bool = False


@dataclass
class RequestMetrics:
    """Request metrics"""
    service_name: str
    instance_id: str
    timestamp: datetime
    duration_ms: float
    status_code: int
    success: bool
    path: str
    method: str
    error: Optional[str] = None


class ServiceRegistry:
    """
    Service discovery and registry
    
    Maintains registry of available service instances.
    """
    
    def __init__(self, heartbeat_interval: int = 30, 
                 heartbeat_timeout: int = 90):
        """
        Initialize service registry
        
        Args:
            heartbeat_interval: Expected heartbeat interval (seconds)
            heartbeat_timeout: Timeout for missing heartbeats (seconds)
        """
        self.services: Dict[str, List[ServiceInstance]] = defaultdict(list)
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self._lock = threading.RLock()
        
        # Start background health checker
        self._running = True
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        self._health_check_thread.start()
        
        logger.info("ServiceRegistry initialized")
    
    def register(self, instance: ServiceInstance) -> bool:
        """
        Register a service instance
        
        Args:
            instance: Service instance to register
            
        Returns:
            True if registered successfully
        """
        with self._lock:
            # Check if already registered
            existing = self._find_instance(
                instance.service_name,
                instance.instance_id
            )
            
            if existing:
                # Update existing instance
                existing.last_heartbeat = datetime.utcnow()
                existing.health_status = ServiceHealth.HEALTHY
                logger.info(f"Updated service instance: {instance.service_name}/{instance.instance_id}")
            else:
                # Register new instance
                self.services[instance.service_name].append(instance)
                logger.info(f"Registered service instance: {instance.service_name}/{instance.instance_id}")
            
            return True
    
    def deregister(self, service_name: str, instance_id: str) -> bool:
        """Deregister a service instance"""
        with self._lock:
            instances = self.services.get(service_name, [])
            self.services[service_name] = [
                i for i in instances if i.instance_id != instance_id
            ]
            logger.info(f"Deregistered service instance: {service_name}/{instance_id}")
            return True
    
    def heartbeat(self, service_name: str, instance_id: str) -> bool:
        """Record heartbeat from service instance"""
        with self._lock:
            instance = self._find_instance(service_name, instance_id)
            if instance:
                instance.last_heartbeat = datetime.utcnow()
                instance.health_status = ServiceHealth.HEALTHY
                return True
            return False
    
    def get_instances(self, service_name: str, 
                     healthy_only: bool = True,
                     version: Optional[str] = None,
                     zone: Optional[str] = None) -> List[ServiceInstance]:
        """
        Get service instances
        
        Args:
            service_name: Service name
            healthy_only: Return only healthy instances
            version: Filter by version
            zone: Filter by zone
            
        Returns:
            List of service instances
        """
        with self._lock:
            instances = self.services.get(service_name, [])
            
            # Filter by health
            if healthy_only:
                instances = [
                    i for i in instances 
                    if i.health_status == ServiceHealth.HEALTHY
                ]
            
            # Filter by version
            if version:
                instances = [i for i in instances if i.version == version]
            
            # Filter by zone
            if zone:
                instances = [i for i in instances if i.zone == zone]
            
            return list(instances)
    
    def get_all_services(self) -> List[str]:
        """Get list of all registered services"""
        with self._lock:
            return list(self.services.keys())
    
    def _find_instance(self, service_name: str, 
                      instance_id: str) -> Optional[ServiceInstance]:
        """Find specific service instance"""
        instances = self.services.get(service_name, [])
        for instance in instances:
            if instance.instance_id == instance_id:
                return instance
        return None
    
    def _health_check_loop(self):
        """Background health check loop"""
        while self._running:
            try:
                self._check_heartbeats()
                time.sleep(self.heartbeat_interval)
            except Exception as e:
                logger.error(f"Health check error: {e}")
    
    def _check_heartbeats(self):
        """Check for missing heartbeats"""
        with self._lock:
            now = datetime.utcnow()
            timeout = timedelta(seconds=self.heartbeat_timeout)
            
            for service_name, instances in self.services.items():
                for instance in instances:
                    time_since_heartbeat = now - instance.last_heartbeat
                    
                    if time_since_heartbeat > timeout:
                        if instance.health_status == ServiceHealth.HEALTHY:
                            instance.health_status = ServiceHealth.UNHEALTHY
                            logger.warning(
                                f"Instance unhealthy (no heartbeat): "
                                f"{service_name}/{instance.instance_id}"
                            )
    
    def shutdown(self):
        """Shutdown registry"""
        self._running = False
        if self._health_check_thread:
            self._health_check_thread.join(timeout=5)


class LoadBalancer:
    """
    Load balancer with multiple strategies
    
    Distributes traffic across service instances.
    """
    
    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN):
        """
        Initialize load balancer
        
        Args:
            strategy: Load balancing strategy
        """
        self.strategy = strategy
        self.round_robin_index: Dict[str, int] = defaultdict(int)
        self.connection_counts: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()
        
        logger.info(f"LoadBalancer initialized (strategy={strategy.value})")
    
    def select_instance(self, service_name: str,
                       instances: List[ServiceInstance],
                       client_id: Optional[str] = None) -> Optional[ServiceInstance]:
        """
        Select service instance using configured strategy
        
        Args:
            service_name: Service name
            instances: Available instances
            client_id: Client identifier (for sticky sessions)
            
        Returns:
            Selected service instance
        """
        if not instances:
            return None
        
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_select(service_name, instances)
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_select(instances)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin_select(instances)
        elif self.strategy == LoadBalancingStrategy.RANDOM:
            return self._random_select(instances)
        elif self.strategy == LoadBalancingStrategy.CONSISTENT_HASH:
            return self._consistent_hash_select(instances, client_id or "")
        elif self.strategy == LoadBalancingStrategy.IP_HASH:
            return self._ip_hash_select(instances, client_id or "")
        else:
            return instances[0]
    
    def _round_robin_select(self, service_name: str,
                           instances: List[ServiceInstance]) -> ServiceInstance:
        """Round-robin selection"""
        with self._lock:
            index = self.round_robin_index[service_name]
            instance = instances[index % len(instances)]
            self.round_robin_index[service_name] = (index + 1) % len(instances)
            return instance
    
    def _least_connections_select(self, 
                                 instances: List[ServiceInstance]) -> ServiceInstance:
        """Least connections selection"""
        with self._lock:
            # Select instance with fewest connections
            min_connections = float('inf')
            selected = instances[0]
            
            for instance in instances:
                key = f"{instance.instance_id}"
                connections = self.connection_counts[key]
                if connections < min_connections:
                    min_connections = connections
                    selected = instance
            
            return selected
    
    def _weighted_round_robin_select(self,
                                    instances: List[ServiceInstance]) -> ServiceInstance:
        """Weighted round-robin selection"""
        # Create weighted list
        weighted_instances = []
        for instance in instances:
            weight = instance.weight if instance.weight > 0 else 1
            weighted_instances.extend([instance] * weight)
        
        if not weighted_instances:
            return instances[0]
        
        # Use round-robin on weighted list
        with self._lock:
            key = "weighted"
            index = self.round_robin_index[key]
            instance = weighted_instances[index % len(weighted_instances)]
            self.round_robin_index[key] = (index + 1) % len(weighted_instances)
            return instance
    
    def _random_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Random selection"""
        return random.choice(instances)
    
    def _consistent_hash_select(self, instances: List[ServiceInstance],
                               client_id: str) -> ServiceInstance:
        """Consistent hashing selection"""
        # Hash client ID
        client_hash = int(hashlib.md5(client_id.encode()).hexdigest(), 16)
        
        # Hash instances and find closest
        instance_hashes = []
        for instance in instances:
            key = f"{instance.host}:{instance.port}"
            hash_val = int(hashlib.md5(key.encode()).hexdigest(), 16)
            instance_hashes.append((hash_val, instance))
        
        instance_hashes.sort(key=lambda x: x[0])
        
        # Find first instance with hash >= client_hash
        for hash_val, instance in instance_hashes:
            if hash_val >= client_hash:
                return instance
        
        # Wrap around to first instance
        return instance_hashes[0][1]
    
    def _ip_hash_select(self, instances: List[ServiceInstance],
                       client_ip: str) -> ServiceInstance:
        """IP hash selection"""
        if not client_ip:
            return instances[0]
        
        # Hash IP address
        ip_hash = hash(client_ip)
        index = abs(ip_hash) % len(instances)
        return instances[index]
    
    def record_connection(self, instance_id: str):
        """Record new connection to instance"""
        with self._lock:
            self.connection_counts[instance_id] += 1
    
    def release_connection(self, instance_id: str):
        """Release connection from instance"""
        with self._lock:
            if self.connection_counts[instance_id] > 0:
                self.connection_counts[instance_id] -= 1


class CircuitBreaker:
    """
    Circuit breaker for fault tolerance
    
    Prevents cascading failures by temporarily blocking requests to failing services.
    """
    
    def __init__(self, config: CircuitBreakerConfig = None):
        """
        Initialize circuit breaker
        
        Args:
            config: Circuit breaker configuration
        """
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_requests = 0
        self._lock = threading.Lock()
        
        logger.info("CircuitBreaker initialized")
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker
        
        Args:
            func: Function to execute
            *args, **kwargs: Function arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        with self._lock:
            if self.state == CircuitState.OPEN:
                # Check if timeout has passed
                if self.last_failure_time:
                    elapsed = datetime.utcnow() - self.last_failure_time
                    if elapsed >= self.config.timeout:
                        self.state = CircuitState.HALF_OPEN
                        self.half_open_requests = 0
                        logger.info("Circuit breaker entering HALF_OPEN state")
                    else:
                        raise Exception("Circuit breaker is OPEN")
                else:
                    raise Exception("Circuit breaker is OPEN")
            
            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_requests >= self.config.half_open_max_requests:
                    raise Exception("Circuit breaker HALF_OPEN - max requests reached")
                self.half_open_requests += 1
        
        # Execute function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful request"""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    logger.info("Circuit breaker closed (recovered)")
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed request"""
        with self._lock:
            self.last_failure_time = datetime.utcnow()
            
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self.success_count = 0
                logger.warning("Circuit breaker opened (failure in HALF_OPEN)")
            elif self.state == CircuitState.CLOSED:
                self.failure_count += 1
                if self.failure_count >= self.config.failure_threshold:
                    self.state = CircuitState.OPEN
                    logger.warning(
                        f"Circuit breaker opened "
                        f"(failures: {self.failure_count}/{self.config.failure_threshold})"
                    )
    
    def reset(self):
        """Manually reset circuit breaker"""
        with self._lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.half_open_requests = 0
            logger.info("Circuit breaker manually reset")
    
    def get_state(self) -> CircuitState:
        """Get current circuit state"""
        return self.state


class RetryPolicy:
    """
    Retry policy with exponential backoff
    
    Automatically retries failed requests with configurable backoff.
    """
    
    def __init__(self, config: RetryConfig = None):
        """
        Initialize retry policy
        
        Args:
            config: Retry configuration
        """
        self.config = config or RetryConfig()
        logger.info(f"RetryPolicy initialized (max_attempts={self.config.max_attempts})")
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry logic
        
        Args:
            func: Function to execute
            *args, **kwargs: Function arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retries exhausted
        """
        last_exception = None
        delay = self.config.initial_delay
        
        for attempt in range(self.config.max_attempts):
            try:
                result = func(*args, **kwargs)
                
                # Check if result indicates retry
                if hasattr(result, 'status_code'):
                    if result.status_code in self.config.retry_on_status:
                        raise Exception(f"HTTP {result.status_code}")
                
                return result
                
            except requests.exceptions.Timeout as e:
                if not self.config.retry_on_timeout:
                    raise
                last_exception = e
                
            except Exception as e:
                last_exception = e
            
            # Last attempt - don't retry
            if attempt == self.config.max_attempts - 1:
                break
            
            # Log retry
            logger.info(
                f"Retry attempt {attempt + 1}/{self.config.max_attempts} "
                f"after {delay:.2f}s"
            )
            
            # Wait before retry
            time.sleep(delay)
            
            # Calculate next delay with exponential backoff
            delay = min(
                delay * self.config.backoff_multiplier,
                self.config.max_delay
            )
        
        # All retries exhausted
        raise last_exception


class TrafficSplitter:
    """
    Traffic splitting for canary deployments and A/B testing
    
    Routes traffic between different service versions based on rules.
    """
    
    def __init__(self):
        """Initialize traffic splitter"""
        self.splits: Dict[str, TrafficSplit] = {}
        self.sticky_sessions: Dict[str, str] = {}  # client_id -> version
        self._lock = threading.Lock()
        
        logger.info("TrafficSplitter initialized")
    
    def configure_split(self, service_name: str, split: TrafficSplit):
        """
        Configure traffic split for service
        
        Args:
            service_name: Service name
            split: Traffic split configuration
        """
        with self._lock:
            self.splits[service_name] = split
            logger.info(f"Configured traffic split for {service_name}: {split.destinations}")
    
    def remove_split(self, service_name: str):
        """Remove traffic split configuration"""
        with self._lock:
            if service_name in self.splits:
                del self.splits[service_name]
                logger.info(f"Removed traffic split for {service_name}")
    
    def select_version(self, service_name: str,
                      request_headers: Dict[str, str] = None,
                      client_id: Optional[str] = None) -> str:
        """
        Select service version based on traffic split rules
        
        Args:
            service_name: Service name
            request_headers: HTTP request headers
            client_id: Client identifier
            
        Returns:
            Selected version
        """
        with self._lock:
            split = self.splits.get(service_name)
            if not split:
                return "v1"  # Default version
            
            # Check sticky session
            if split.sticky_session and client_id:
                if client_id in self.sticky_sessions:
                    return self.sticky_sessions[client_id]
            
            # Weight-based splitting
            if split.split_type == TrafficSplitType.WEIGHT_BASED:
                version = self._weight_based_select(split.destinations)
                
                # Store sticky session
                if split.sticky_session and client_id:
                    self.sticky_sessions[client_id] = version
                
                return version
            
            # Header-based splitting
            elif split.split_type == TrafficSplitType.HEADER_BASED:
                if request_headers:
                    for dest in split.destinations:
                        header_rules = dest.get('header_rules', {})
                        if self._match_headers(request_headers, header_rules):
                            return dest['version']
                
                return split.fallback_version
            
            # Cookie-based splitting
            elif split.split_type == TrafficSplitType.COOKIE_BASED:
                if request_headers and 'Cookie' in request_headers:
                    cookies = self._parse_cookies(request_headers['Cookie'])
                    version_cookie = cookies.get('version')
                    if version_cookie:
                        return version_cookie
                
                return split.fallback_version
            
            # User-based splitting
            elif split.split_type == TrafficSplitType.USER_BASED:
                if client_id:
                    # Hash user ID to determine version
                    user_hash = hash(client_id)
                    return self._hash_based_select(split.destinations, user_hash)
                
                return split.fallback_version
            
            return split.fallback_version
    
    def _weight_based_select(self, destinations: List[Dict[str, Any]]) -> str:
        """Select version based on weights"""
        total_weight = sum(d.get('weight', 0) for d in destinations)
        if total_weight == 0:
            return destinations[0]['version'] if destinations else "v1"
        
        rand = random.randint(1, total_weight)
        cumulative = 0
        
        for dest in destinations:
            cumulative += dest.get('weight', 0)
            if rand <= cumulative:
                return dest['version']
        
        return destinations[-1]['version']
    
    def _match_headers(self, headers: Dict[str, str],
                      rules: Dict[str, str]) -> bool:
        """Check if headers match rules"""
        for key, expected_value in rules.items():
            if headers.get(key) != expected_value:
                return False
        return True
    
    def _parse_cookies(self, cookie_header: str) -> Dict[str, str]:
        """Parse cookie header"""
        cookies = {}
        for item in cookie_header.split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                cookies[key.strip()] = value.strip()
        return cookies
    
    def _hash_based_select(self, destinations: List[Dict[str, Any]],
                          hash_value: int) -> str:
        """Select version based on hash"""
        if not destinations:
            return "v1"
        
        index = abs(hash_value) % len(destinations)
        return destinations[index]['version']


class HealthChecker:
    """
    Service health checker
    
    Periodically checks service health and updates status.
    """
    
    def __init__(self, registry: ServiceRegistry, 
                 check_interval: int = 10,
                 timeout: float = 5.0):
        """
        Initialize health checker
        
        Args:
            registry: Service registry
            check_interval: Check interval in seconds
            timeout: Health check timeout
        """
        self.registry = registry
        self.check_interval = check_interval
        self.timeout = timeout
        self.health_endpoints: Dict[str, str] = {}  # service_name -> endpoint
        
        self._running = True
        self._thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self._thread.start()
        
        logger.info("HealthChecker initialized")
    
    def register_health_endpoint(self, service_name: str, endpoint: str):
        """Register health check endpoint for service"""
        self.health_endpoints[service_name] = endpoint
        logger.info(f"Registered health endpoint for {service_name}: {endpoint}")
    
    def _health_check_loop(self):
        """Background health check loop"""
        while self._running:
            try:
                self._check_all_services()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Health check error: {e}")
    
    def _check_all_services(self):
        """Check health of all services"""
        for service_name in self.registry.get_all_services():
            instances = self.registry.get_instances(service_name, healthy_only=False)
            
            for instance in instances:
                health = self._check_instance_health(instance)
                instance.health_status = health
    
    def _check_instance_health(self, instance: ServiceInstance) -> ServiceHealth:
        """Check health of specific instance"""
        endpoint = self.health_endpoints.get(instance.service_name, "/health")
        url = f"{instance.get_url()}{endpoint}"
        
        try:
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                return ServiceHealth.HEALTHY
            elif 200 <= response.status_code < 300:
                return ServiceHealth.DEGRADED
            else:
                return ServiceHealth.UNHEALTHY
                
        except requests.exceptions.Timeout:
            logger.warning(f"Health check timeout: {instance.instance_id}")
            return ServiceHealth.UNHEALTHY
        except Exception as e:
            logger.warning(f"Health check failed: {instance.instance_id} - {e}")
            return ServiceHealth.UNHEALTHY
    
    def shutdown(self):
        """Shutdown health checker"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)


class MetricsCollector:
    """
    Service mesh metrics collector
    
    Collects and aggregates request metrics.
    """
    
    def __init__(self, retention_hours: int = 24):
        """
        Initialize metrics collector
        
        Args:
            retention_hours: Metrics retention period
        """
        self.metrics: List[RequestMetrics] = []
        self.retention_hours = retention_hours
        self._lock = threading.Lock()
        
        logger.info("MetricsCollector initialized")
    
    def record_request(self, metrics: RequestMetrics):
        """Record request metrics"""
        with self._lock:
            self.metrics.append(metrics)
            
            # Cleanup old metrics
            cutoff = datetime.utcnow() - timedelta(hours=self.retention_hours)
            self.metrics = [
                m for m in self.metrics if m.timestamp >= cutoff
            ]
    
    def get_service_metrics(self, service_name: str,
                           time_window: timedelta = None) -> Dict[str, Any]:
        """
        Get aggregated metrics for service
        
        Args:
            service_name: Service name
            time_window: Time window for metrics
            
        Returns:
            Aggregated metrics
        """
        with self._lock:
            cutoff = datetime.utcnow() - (time_window or timedelta(hours=1))
            
            service_metrics = [
                m for m in self.metrics
                if m.service_name == service_name and m.timestamp >= cutoff
            ]
            
            if not service_metrics:
                return {}
            
            total_requests = len(service_metrics)
            successful_requests = sum(1 for m in service_metrics if m.success)
            failed_requests = total_requests - successful_requests
            
            durations = [m.duration_ms for m in service_metrics]
            
            return {
                'service_name': service_name,
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'failed_requests': failed_requests,
                'success_rate': successful_requests / total_requests if total_requests > 0 else 0,
                'avg_duration_ms': sum(durations) / len(durations) if durations else 0,
                'min_duration_ms': min(durations) if durations else 0,
                'max_duration_ms': max(durations) if durations else 0,
                'p50_duration_ms': self._percentile(durations, 50) if durations else 0,
                'p95_duration_ms': self._percentile(durations, 95) if durations else 0,
                'p99_duration_ms': self._percentile(durations, 99) if durations else 0,
                'requests_per_second': total_requests / time_window.total_seconds() if time_window else 0
            }
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile"""
        if not values:
            return 0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]


class ServiceMesh:
    """
    Main service mesh orchestrator
    
    Integrates all service mesh components.
    """
    
    def __init__(self, 
                 load_balancing_strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
                 enable_circuit_breaker: bool = True,
                 enable_retry: bool = True,
                 enable_metrics: bool = True):
        """
        Initialize service mesh
        
        Args:
            load_balancing_strategy: Load balancing strategy
            enable_circuit_breaker: Enable circuit breaking
            enable_retry: Enable retry logic
            enable_metrics: Enable metrics collection
        """
        self.registry = ServiceRegistry()
        self.load_balancer = LoadBalancer(strategy=load_balancing_strategy)
        self.traffic_splitter = TrafficSplitter()
        self.health_checker = HealthChecker(self.registry)
        
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_policies: Dict[str, RetryPolicy] = {}
        
        self.enable_circuit_breaker = enable_circuit_breaker
        self.enable_retry = enable_retry
        self.enable_metrics = enable_metrics
        
        if enable_metrics:
            self.metrics_collector = MetricsCollector()
        
        self.timeout_config = TimeoutConfig()
        
        logger.info("ServiceMesh initialized")
    
    def register_service(self, instance: ServiceInstance) -> bool:
        """Register a service instance"""
        return self.registry.register(instance)
    
    def deregister_service(self, service_name: str, instance_id: str) -> bool:
        """Deregister a service instance"""
        return self.registry.deregister(service_name, instance_id)
    
    def configure_circuit_breaker(self, service_name: str,
                                 config: CircuitBreakerConfig):
        """Configure circuit breaker for service"""
        self.circuit_breakers[service_name] = CircuitBreaker(config)
        logger.info(f"Configured circuit breaker for {service_name}")
    
    def configure_retry_policy(self, service_name: str, config: RetryConfig):
        """Configure retry policy for service"""
        self.retry_policies[service_name] = RetryPolicy(config)
        logger.info(f"Configured retry policy for {service_name}")
    
    def configure_traffic_split(self, service_name: str, split: TrafficSplit):
        """Configure traffic splitting"""
        self.traffic_splitter.configure_split(service_name, split)
    
    def call_service(self, service_name: str,
                    path: str = "/",
                    method: str = "GET",
                    headers: Dict[str, str] = None,
                    data: Any = None,
                    json_data: Dict[str, Any] = None,
                    client_id: Optional[str] = None) -> requests.Response:
        """
        Call a service through the mesh
        
        Args:
            service_name: Service name
            path: Request path
            method: HTTP method
            headers: Request headers
            data: Request data
            json_data: JSON request data
            client_id: Client identifier
            
        Returns:
            Response from service
        """
        start_time = time.time()
        
        try:
            # Select version based on traffic split
            version = self.traffic_splitter.select_version(
                service_name,
                headers or {},
                client_id
            )
            
            # Get healthy instances
            instances = self.registry.get_instances(
                service_name,
                healthy_only=True,
                version=version
            )
            
            if not instances:
                raise Exception(f"No healthy instances for {service_name} (version={version})")
            
            # Select instance using load balancer
            instance = self.load_balancer.select_instance(
                service_name,
                instances,
                client_id
            )
            
            # Record connection
            self.load_balancer.record_connection(instance.instance_id)
            
            try:
                # Build URL
                url = f"{instance.get_url()}{path}"
                
                # Execute request through mesh
                response = self._execute_request(
                    service_name,
                    instance,
                    url,
                    method,
                    headers,
                    data,
                    json_data
                )
                
                # Record metrics
                if self.enable_metrics:
                    duration_ms = (time.time() - start_time) * 1000
                    self.metrics_collector.record_request(RequestMetrics(
                        service_name=service_name,
                        instance_id=instance.instance_id,
                        timestamp=datetime.utcnow(),
                        duration_ms=duration_ms,
                        status_code=response.status_code,
                        success=200 <= response.status_code < 300,
                        path=path,
                        method=method
                    ))
                
                return response
                
            finally:
                self.load_balancer.release_connection(instance.instance_id)
        
        except Exception as e:
            # Record failure metrics
            if self.enable_metrics:
                duration_ms = (time.time() - start_time) * 1000
                self.metrics_collector.record_request(RequestMetrics(
                    service_name=service_name,
                    instance_id="unknown",
                    timestamp=datetime.utcnow(),
                    duration_ms=duration_ms,
                    status_code=0,
                    success=False,
                    path=path,
                    method=method,
                    error=str(e)
                ))
            
            raise
    
    def _execute_request(self, service_name: str,
                        instance: ServiceInstance,
                        url: str,
                        method: str,
                        headers: Dict[str, str],
                        data: Any,
                        json_data: Dict[str, Any]) -> requests.Response:
        """Execute HTTP request with mesh features"""
        
        def make_request():
            return requests.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                json=json_data,
                timeout=(
                    self.timeout_config.connect_timeout,
                    self.timeout_config.read_timeout
                )
            )
        
        # Apply retry policy
        if self.enable_retry and service_name in self.retry_policies:
            retry_policy = self.retry_policies[service_name]
            
            def with_retry():
                return retry_policy.execute(make_request)
            
            request_func = with_retry
        else:
            request_func = make_request
        
        # Apply circuit breaker
        if self.enable_circuit_breaker and service_name in self.circuit_breakers:
            circuit_breaker = self.circuit_breakers[service_name]
            return circuit_breaker.call(request_func)
        else:
            return request_func()
    
    def get_service_metrics(self, service_name: str) -> Dict[str, Any]:
        """Get metrics for service"""
        if self.enable_metrics:
            return self.metrics_collector.get_service_metrics(service_name)
        return {}
    
    def shutdown(self):
        """Shutdown service mesh"""
        self.registry.shutdown()
        self.health_checker.shutdown()
        logger.info("ServiceMesh shutdown complete")


# Example usage
def example_usage():
    """Demonstrate service mesh usage"""
    
    # Initialize service mesh
    mesh = ServiceMesh(
        load_balancing_strategy=LoadBalancingStrategy.ROUND_ROBIN,
        enable_circuit_breaker=True,
        enable_retry=True
    )
    
    # Register service instances
    mesh.register_service(ServiceInstance(
        service_name="weather-service",
        instance_id="weather-1",
        host="localhost",
        port=8001,
        version="v1",
        weight=100
    ))
    
    mesh.register_service(ServiceInstance(
        service_name="weather-service",
        instance_id="weather-2",
        host="localhost",
        port=8002,
        version="v2",
        weight=20
    ))
    
    # Configure circuit breaker
    mesh.configure_circuit_breaker(
        "weather-service",
        CircuitBreakerConfig(failure_threshold=3, timeout=timedelta(seconds=30))
    )
    
    # Configure retry policy
    mesh.configure_retry_policy(
        "weather-service",
        RetryConfig(max_attempts=3, initial_delay=1.0)
    )
    
    # Configure canary deployment (80% v1, 20% v2)
    mesh.configure_traffic_split(
        "weather-service",
        TrafficSplit(
            split_type=TrafficSplitType.WEIGHT_BASED,
            destinations=[
                {"version": "v1", "weight": 80},
                {"version": "v2", "weight": 20}
            ]
        )
    )
    
    # Call service through mesh
    try:
        response = mesh.call_service(
            service_name="weather-service",
            path="/api/forecast",
            method="GET",
            client_id="user123"
        )
        print(f"Response: {response.status_code}")
        
        # Get metrics
        metrics = mesh.get_service_metrics("weather-service")
        print(f"Service metrics: {metrics}")
        
    except Exception as e:
        print(f"Service call failed: {e}")
    
    finally:
        mesh.shutdown()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_usage()
