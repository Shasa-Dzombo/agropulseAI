"""
Microservices Architecture for AgroPulse

Service mesh, API gateway, service discovery, circuit breakers.

Features:
- Service registry and discovery
- API Gateway with routing
- Circuit breaker pattern
- Load balancing
- Health checks
- Service-to-service communication
- Distributed tracing
"""

import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import time
import random
from collections import deque

try:
    import aiohttp
    import aiodns
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False
    logging.warning("aiohttp not available")


logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, requests rejected
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class ServiceInstance:
    """Service instance registration"""
    service_name: str
    instance_id: str
    host: str
    port: int
    protocol: str = "http"
    metadata: Dict = field(default_factory=dict)
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_heartbeat: datetime = field(default_factory=datetime.now)
    registered_at: datetime = field(default_factory=datetime.now)
    
    @property
    def url(self) -> str:
        """Get service URL"""
        return f"{self.protocol}://{self.host}:{self.port}"
    
    @property
    def is_healthy(self) -> bool:
        """Check if instance is healthy"""
        return self.status == ServiceStatus.HEALTHY


@dataclass
class ServiceMetrics:
    """Service performance metrics"""
    service_name: str
    request_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_latency: float = 0.0
    min_latency: float = float('inf')
    max_latency: float = 0.0
    last_request_time: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.request_count == 0:
            return 0.0
        return self.success_count / self.request_count
    
    @property
    def average_latency(self) -> float:
        """Calculate average latency"""
        if self.request_count == 0:
            return 0.0
        return self.total_latency / self.request_count


class ServiceRegistry:
    """
    Service registry for microservices discovery
    
    Features:
    - Service registration
    - Health monitoring
    - Instance selection
    - Load balancing
    """
    
    def __init__(
        self,
        heartbeat_interval: int = 30,
        heartbeat_timeout: int = 90
    ):
        """
        Initialize service registry
        
        Args:
            heartbeat_interval: Expected heartbeat interval (seconds)
            heartbeat_timeout: Timeout before marking unhealthy (seconds)
        """
        self.services: Dict[str, List[ServiceInstance]] = {}
        self.metrics: Dict[str, ServiceMetrics] = {}
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        
        self._monitoring_task = None
        
        logger.info("ServiceRegistry initialized")
    
    def register_service(
        self,
        service_name: str,
        instance_id: str,
        host: str,
        port: int,
        protocol: str = "http",
        metadata: Optional[Dict] = None
    ) -> ServiceInstance:
        """
        Register service instance
        
        Args:
            service_name: Service name
            instance_id: Unique instance ID
            host: Host address
            port: Port number
            protocol: Protocol (http/https)
            metadata: Additional metadata
            
        Returns:
            Registered service instance
        """
        instance = ServiceInstance(
            service_name=service_name,
            instance_id=instance_id,
            host=host,
            port=port,
            protocol=protocol,
            metadata=metadata or {}
        )
        
        if service_name not in self.services:
            self.services[service_name] = []
            self.metrics[service_name] = ServiceMetrics(service_name=service_name)
        
        # Remove existing instance with same ID
        self.services[service_name] = [
            s for s in self.services[service_name]
            if s.instance_id != instance_id
        ]
        
        self.services[service_name].append(instance)
        
        logger.info(f"Registered service: {service_name}/{instance_id} at {instance.url}")
        
        return instance
    
    def deregister_service(self, service_name: str, instance_id: str):
        """Deregister service instance"""
        if service_name in self.services:
            self.services[service_name] = [
                s for s in self.services[service_name]
                if s.instance_id != instance_id
            ]
            logger.info(f"Deregistered service: {service_name}/{instance_id}")
    
    def update_heartbeat(self, service_name: str, instance_id: str):
        """Update service heartbeat"""
        if service_name in self.services:
            for instance in self.services[service_name]:
                if instance.instance_id == instance_id:
                    instance.last_heartbeat = datetime.now()
                    instance.status = ServiceStatus.HEALTHY
                    break
    
    def get_service_instances(
        self,
        service_name: str,
        healthy_only: bool = True
    ) -> List[ServiceInstance]:
        """
        Get all instances of a service
        
        Args:
            service_name: Service name
            healthy_only: Return only healthy instances
            
        Returns:
            List of service instances
        """
        instances = self.services.get(service_name, [])
        
        if healthy_only:
            instances = [i for i in instances if i.is_healthy]
        
        return instances
    
    def select_instance(
        self,
        service_name: str,
        strategy: str = "round_robin"
    ) -> Optional[ServiceInstance]:
        """
        Select service instance using load balancing strategy
        
        Args:
            service_name: Service name
            strategy: Selection strategy (round_robin, random, least_connections)
            
        Returns:
            Selected service instance
        """
        instances = self.get_service_instances(service_name, healthy_only=True)
        
        if not instances:
            logger.warning(f"No healthy instances found for service: {service_name}")
            return None
        
        if strategy == "random":
            return random.choice(instances)
        elif strategy == "round_robin":
            # Simple round-robin based on current metrics
            return instances[self.metrics[service_name].request_count % len(instances)]
        elif strategy == "least_connections":
            # Would need per-instance metrics
            return instances[0]
        else:
            return instances[0]
    
    def check_health(self):
        """Check health of all registered instances"""
        now = datetime.now()
        timeout_threshold = timedelta(seconds=self.heartbeat_timeout)
        
        for service_name, instances in self.services.items():
            for instance in instances:
                time_since_heartbeat = now - instance.last_heartbeat
                
                if time_since_heartbeat > timeout_threshold:
                    instance.status = ServiceStatus.UNHEALTHY
                    logger.warning(
                        f"Service unhealthy: {service_name}/{instance.instance_id} "
                        f"(last heartbeat: {time_since_heartbeat.total_seconds()}s ago)"
                    )
    
    def get_service_metrics(self, service_name: str) -> Optional[ServiceMetrics]:
        """Get metrics for a service"""
        return self.metrics.get(service_name)
    
    def record_request(
        self,
        service_name: str,
        success: bool,
        latency: float
    ):
        """
        Record service request metrics
        
        Args:
            service_name: Service name
            success: Whether request succeeded
            latency: Request latency in seconds
        """
        if service_name not in self.metrics:
            self.metrics[service_name] = ServiceMetrics(service_name=service_name)
        
        metrics = self.metrics[service_name]
        metrics.request_count += 1
        metrics.last_request_time = datetime.now()
        
        if success:
            metrics.success_count += 1
        else:
            metrics.failure_count += 1
        
        metrics.total_latency += latency
        metrics.min_latency = min(metrics.min_latency, latency)
        metrics.max_latency = max(metrics.max_latency, latency)


class CircuitBreaker:
    """
    Circuit breaker pattern implementation
    
    Prevents cascading failures by temporarily blocking requests
    to failing services.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: float = 60.0,
        half_open_timeout: float = 30.0
    ):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Failures before opening circuit
            success_threshold: Successes needed to close circuit
            timeout: Timeout in open state (seconds)
            half_open_timeout: Timeout in half-open state (seconds)
        """
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.half_open_timeout = half_open_timeout
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_state_change: datetime = datetime.now()
        
        logger.info("CircuitBreaker initialized")
    
    def can_execute(self) -> bool:
        """Check if request can be executed"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if self.last_failure_time:
                time_since_failure = (datetime.now() - self.last_failure_time).total_seconds()
                if time_since_failure >= self.timeout:
                    self._transition_to_half_open()
                    return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            return True
        
        return False
    
    def record_success(self):
        """Record successful request"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self._transition_to_closed()
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def record_failure(self):
        """Record failed request"""
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitState.CLOSED:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self._transition_to_open()
        elif self.state == CircuitState.HALF_OPEN:
            self._transition_to_open()
    
    def _transition_to_open(self):
        """Transition to open state"""
        self.state = CircuitState.OPEN
        self.last_state_change = datetime.now()
        logger.warning("Circuit breaker opened")
    
    def _transition_to_half_open(self):
        """Transition to half-open state"""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.failure_count = 0
        self.last_state_change = datetime.now()
        logger.info("Circuit breaker half-opened")
    
    def _transition_to_closed(self):
        """Transition to closed state"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_state_change = datetime.now()
        logger.info("Circuit breaker closed")
    
    def get_status(self) -> Dict:
        """Get circuit breaker status"""
        return {
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'time_in_state': (datetime.now() - self.last_state_change).total_seconds()
        }


class APIGateway:
    """
    API Gateway for microservices
    
    Features:
    - Request routing
    - Load balancing
    - Circuit breaking
    - Rate limiting
    - Authentication
    - Request/response transformation
    """
    
    def __init__(
        self,
        service_registry: ServiceRegistry,
        enable_circuit_breaker: bool = True,
        enable_rate_limiting: bool = True
    ):
        """
        Initialize API Gateway
        
        Args:
            service_registry: Service registry instance
            enable_circuit_breaker: Enable circuit breaker
            enable_rate_limiting: Enable rate limiting
        """
        if not ASYNC_AVAILABLE:
            raise RuntimeError("aiohttp not available")
        
        self.service_registry = service_registry
        self.enable_circuit_breaker = enable_circuit_breaker
        self.enable_rate_limiting = enable_rate_limiting
        
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.rate_limiters: Dict[str, deque] = {}
        
        self.routes: Dict[str, str] = {}
        
        logger.info("APIGateway initialized")
    
    def register_route(self, path: str, service_name: str):
        """
        Register route to service
        
        Args:
            path: Request path pattern
            service_name: Target service name
        """
        self.routes[path] = service_name
        logger.info(f"Registered route: {path} -> {service_name}")
    
    def _get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for service"""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreaker()
        return self.circuit_breakers[service_name]
    
    def _check_rate_limit(
        self,
        client_id: str,
        limit: int = 100,
        window: int = 60
    ) -> bool:
        """
        Check rate limit
        
        Args:
            client_id: Client identifier
            limit: Maximum requests per window
            window: Time window in seconds
            
        Returns:
            True if within limit
        """
        if not self.enable_rate_limiting:
            return True
        
        if client_id not in self.rate_limiters:
            self.rate_limiters[client_id] = deque()
        
        now = time.time()
        requests = self.rate_limiters[client_id]
        
        # Remove old requests
        while requests and requests[0] < now - window:
            requests.popleft()
        
        if len(requests) >= limit:
            return False
        
        requests.append(now)
        return True
    
    async def forward_request(
        self,
        path: str,
        method: str = "GET",
        headers: Optional[Dict] = None,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        client_id: str = "default"
    ) -> Dict:
        """
        Forward request to appropriate service
        
        Args:
            path: Request path
            method: HTTP method
            headers: Request headers
            data: Request body
            params: Query parameters
            client_id: Client identifier
            
        Returns:
            Response dictionary
        """
        # Find matching route
        service_name = self._match_route(path)
        
        if not service_name:
            return {
                'status': 404,
                'error': f"No route found for path: {path}"
            }
        
        # Check rate limit
        if not self._check_rate_limit(client_id):
            return {
                'status': 429,
                'error': "Rate limit exceeded"
            }
        
        # Check circuit breaker
        if self.enable_circuit_breaker:
            circuit_breaker = self._get_circuit_breaker(service_name)
            if not circuit_breaker.can_execute():
                return {
                    'status': 503,
                    'error': f"Service unavailable: {service_name} (circuit open)"
                }
        
        # Select service instance
        instance = self.service_registry.select_instance(service_name)
        
        if not instance:
            return {
                'status': 503,
                'error': f"No healthy instances for service: {service_name}"
            }
        
        # Forward request
        start_time = time.time()
        
        try:
            url = f"{instance.url}{path}"
            
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    json=data,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    latency = time.time() - start_time
                    
                    # Record metrics
                    success = 200 <= response.status < 300
                    self.service_registry.record_request(service_name, success, latency)
                    
                    # Update circuit breaker
                    if self.enable_circuit_breaker:
                        if success:
                            circuit_breaker.record_success()
                        else:
                            circuit_breaker.record_failure()
                    
                    # Return response
                    response_data = await response.json() if response.content_type == 'application/json' else await response.text()
                    
                    return {
                        'status': response.status,
                        'data': response_data,
                        'headers': dict(response.headers),
                        'latency': latency
                    }
        
        except asyncio.TimeoutError:
            latency = time.time() - start_time
            self.service_registry.record_request(service_name, False, latency)
            
            if self.enable_circuit_breaker:
                circuit_breaker.record_failure()
            
            return {
                'status': 504,
                'error': f"Request timeout to service: {service_name}"
            }
        
        except Exception as e:
            latency = time.time() - start_time
            self.service_registry.record_request(service_name, False, latency)
            
            if self.enable_circuit_breaker:
                circuit_breaker.record_failure()
            
            logger.error(f"Error forwarding request to {service_name}: {e}")
            
            return {
                'status': 500,
                'error': f"Internal error: {str(e)}"
            }
    
    def _match_route(self, path: str) -> Optional[str]:
        """Match path to service"""
        # Simple exact match
        if path in self.routes:
            return self.routes[path]
        
        # Prefix matching
        for route_path, service_name in self.routes.items():
            if path.startswith(route_path):
                return service_name
        
        return None
    
    def get_service_health(self) -> Dict:
        """Get health status of all services"""
        health = {}
        
        for service_name in self.routes.values():
            instances = self.service_registry.get_service_instances(service_name, healthy_only=False)
            metrics = self.service_registry.get_service_metrics(service_name)
            circuit_breaker = self.circuit_breakers.get(service_name)
            
            health[service_name] = {
                'total_instances': len(instances),
                'healthy_instances': sum(1 for i in instances if i.is_healthy),
                'metrics': {
                    'request_count': metrics.request_count if metrics else 0,
                    'success_rate': metrics.success_rate if metrics else 0.0,
                    'average_latency': metrics.average_latency if metrics else 0.0
                },
                'circuit_breaker': circuit_breaker.get_status() if circuit_breaker else None
            }
        
        return health
