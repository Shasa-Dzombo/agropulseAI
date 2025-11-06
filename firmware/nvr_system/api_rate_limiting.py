# ======================================================================================================================
# AgroPulse NVR - API Rate Limiting & Throttling
# Token bucket, sliding window, rate limiting middleware, quota management
# ======================================================================================================================

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict
import hashlib

logger = logging.getLogger(__name__)

# ======================================================================================================================
# RATE LIMITING MODELS
# ======================================================================================================================

class RateLimitStrategy(Enum):
    """Rate limiting strategy"""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    LEAKY_BUCKET = "leaky_bucket"

class RateLimitStatus(Enum):
    """Rate limit status"""
    ALLOWED = "allowed"
    THROTTLED = "throttled"
    BLOCKED = "blocked"

@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    requests_per_second: Optional[int] = None
    requests_per_minute: Optional[int] = None
    requests_per_hour: Optional[int] = None
    requests_per_day: Optional[int] = None
    burst_size: Optional[int] = None
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET

@dataclass
class RateLimitResult:
    """Rate limit check result"""
    status: RateLimitStatus
    allowed: bool
    remaining: int
    reset_time: datetime
    retry_after: Optional[int] = None  # Seconds
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class QuotaConfig:
    """API quota configuration"""
    quota_id: str
    max_requests: int
    period_seconds: int
    burst_allowed: bool = True
    overage_allowed: bool = False
    overage_rate: float = 0.0  # Cost multiplier for overages

# ======================================================================================================================
# TOKEN BUCKET RATE LIMITER
# ======================================================================================================================

class TokenBucketLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self, rate: float, capacity: int):
        """
        Args:
            rate: Tokens per second
            capacity: Maximum bucket capacity
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_update = time.time()
        
        logger.info(
            f"[TOKEN-BUCKET] Initialized: rate={rate}/s, capacity={capacity}"
        )
    
    def _refill(self):
        """Refill tokens based on time elapsed"""
        now = time.time()
        elapsed = now - self.last_update
        
        # Add tokens based on elapsed time
        self.tokens = min(
            self.capacity,
            self.tokens + (elapsed * self.rate)
        )
        self.last_update = now
    
    def consume(self, tokens: int = 1) -> RateLimitResult:
        """Consume tokens"""
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            
            return RateLimitResult(
                status=RateLimitStatus.ALLOWED,
                allowed=True,
                remaining=int(self.tokens),
                reset_time=datetime.now() + timedelta(
                    seconds=(self.capacity - self.tokens) / self.rate
                )
            )
        else:
            # Calculate retry after
            tokens_needed = tokens - self.tokens
            retry_after = int(tokens_needed / self.rate) + 1
            
            return RateLimitResult(
                status=RateLimitStatus.THROTTLED,
                allowed=False,
                remaining=0,
                reset_time=datetime.now() + timedelta(seconds=retry_after),
                retry_after=retry_after
            )
    
    def reset(self):
        """Reset bucket"""
        self.tokens = float(self.capacity)
        self.last_update = time.time()

# ======================================================================================================================
# SLIDING WINDOW RATE LIMITER
# ======================================================================================================================

class SlidingWindowLimiter:
    """Sliding window rate limiter"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: deque = deque()
        
        logger.info(
            f"[SLIDING-WINDOW] Initialized: {max_requests} requests per {window_seconds}s"
        )
    
    def _cleanup_old_requests(self):
        """Remove requests outside window"""
        now = time.time()
        cutoff = now - self.window_seconds
        
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()
    
    def consume(self, tokens: int = 1) -> RateLimitResult:
        """Check and record request"""
        self._cleanup_old_requests()
        
        current_count = len(self.requests)
        
        if current_count + tokens <= self.max_requests:
            # Allow request
            now = time.time()
            for _ in range(tokens):
                self.requests.append(now)
            
            return RateLimitResult(
                status=RateLimitStatus.ALLOWED,
                allowed=True,
                remaining=self.max_requests - (current_count + tokens),
                reset_time=datetime.now() + timedelta(seconds=self.window_seconds)
            )
        else:
            # Throttle
            if self.requests:
                oldest_request = self.requests[0]
                retry_after = int(oldest_request + self.window_seconds - time.time()) + 1
            else:
                retry_after = 1
            
            return RateLimitResult(
                status=RateLimitStatus.THROTTLED,
                allowed=False,
                remaining=0,
                reset_time=datetime.now() + timedelta(seconds=retry_after),
                retry_after=retry_after
            )
    
    def reset(self):
        """Reset window"""
        self.requests.clear()

# ======================================================================================================================
# FIXED WINDOW RATE LIMITER
# ======================================================================================================================

class FixedWindowLimiter:
    """Fixed window rate limiter"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_count = 0
        self.window_start = time.time()
        
        logger.info(
            f"[FIXED-WINDOW] Initialized: {max_requests} requests per {window_seconds}s"
        )
    
    def _check_window_reset(self):
        """Check if window needs reset"""
        now = time.time()
        if now - self.window_start >= self.window_seconds:
            self.request_count = 0
            self.window_start = now
    
    def consume(self, tokens: int = 1) -> RateLimitResult:
        """Check and record request"""
        self._check_window_reset()
        
        if self.request_count + tokens <= self.max_requests:
            self.request_count += tokens
            
            return RateLimitResult(
                status=RateLimitStatus.ALLOWED,
                allowed=True,
                remaining=self.max_requests - self.request_count,
                reset_time=datetime.fromtimestamp(
                    self.window_start + self.window_seconds
                )
            )
        else:
            retry_after = int(self.window_start + self.window_seconds - time.time()) + 1
            
            return RateLimitResult(
                status=RateLimitStatus.THROTTLED,
                allowed=False,
                remaining=0,
                reset_time=datetime.fromtimestamp(
                    self.window_start + self.window_seconds
                ),
                retry_after=retry_after
            )
    
    def reset(self):
        """Reset window"""
        self.request_count = 0
        self.window_start = time.time()

# ======================================================================================================================
# RATE LIMITER MANAGER
# ======================================================================================================================

class RateLimiterManager:
    """Manage multiple rate limiters"""
    
    def __init__(self):
        self.limiters: Dict[str, Any] = {}
        self.configs: Dict[str, RateLimitConfig] = {}
        
        logger.info("[RATE-LIMIT] Rate limiter manager initialized")
    
    def create_limiter(self, identifier: str, config: RateLimitConfig):
        """Create rate limiter"""
        if config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            if config.requests_per_second:
                limiter = TokenBucketLimiter(
                    rate=config.requests_per_second,
                    capacity=config.burst_size or config.requests_per_second * 2
                )
            elif config.requests_per_minute:
                limiter = TokenBucketLimiter(
                    rate=config.requests_per_minute / 60.0,
                    capacity=config.burst_size or config.requests_per_minute
                )
            else:
                raise ValueError("Token bucket requires rate configuration")
        
        elif config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            if config.requests_per_minute:
                limiter = SlidingWindowLimiter(
                    max_requests=config.requests_per_minute,
                    window_seconds=60
                )
            elif config.requests_per_hour:
                limiter = SlidingWindowLimiter(
                    max_requests=config.requests_per_hour,
                    window_seconds=3600
                )
            else:
                raise ValueError("Sliding window requires max_requests configuration")
        
        elif config.strategy == RateLimitStrategy.FIXED_WINDOW:
            if config.requests_per_minute:
                limiter = FixedWindowLimiter(
                    max_requests=config.requests_per_minute,
                    window_seconds=60
                )
            elif config.requests_per_hour:
                limiter = FixedWindowLimiter(
                    max_requests=config.requests_per_hour,
                    window_seconds=3600
                )
            else:
                raise ValueError("Fixed window requires max_requests configuration")
        else:
            raise ValueError(f"Unsupported strategy: {config.strategy}")
        
        self.limiters[identifier] = limiter
        self.configs[identifier] = config
        
        logger.info(f"[RATE-LIMIT] Created limiter: {identifier} ({config.strategy.value})")
    
    def check_limit(self, identifier: str, tokens: int = 1) -> RateLimitResult:
        """Check rate limit"""
        if identifier not in self.limiters:
            # No limiter configured, allow by default
            return RateLimitResult(
                status=RateLimitStatus.ALLOWED,
                allowed=True,
                remaining=999999,
                reset_time=datetime.now() + timedelta(days=1)
            )
        
        limiter = self.limiters[identifier]
        return limiter.consume(tokens)
    
    def reset_limiter(self, identifier: str):
        """Reset limiter"""
        if identifier in self.limiters:
            self.limiters[identifier].reset()
            logger.info(f"[RATE-LIMIT] Reset limiter: {identifier}")

# ======================================================================================================================
# QUOTA MANAGER
# ======================================================================================================================

class QuotaManager:
    """API quota manager"""
    
    def __init__(self):
        self.quotas: Dict[str, QuotaConfig] = {}
        self.usage: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.period_start: Dict[str, datetime] = {}
        
        logger.info("[QUOTA] Quota manager initialized")
    
    def set_quota(self, user_id: str, config: QuotaConfig):
        """Set quota for user"""
        key = f"{user_id}:{config.quota_id}"
        self.quotas[key] = config
        self.period_start[key] = datetime.now()
        
        logger.info(
            f"[QUOTA] Set quota: {user_id}/{config.quota_id} = "
            f"{config.max_requests} per {config.period_seconds}s"
        )
    
    def check_quota(self, user_id: str, quota_id: str,
                   cost: int = 1) -> RateLimitResult:
        """Check quota availability"""
        key = f"{user_id}:{quota_id}"
        
        if key not in self.quotas:
            # No quota configured
            return RateLimitResult(
                status=RateLimitStatus.ALLOWED,
                allowed=True,
                remaining=999999,
                reset_time=datetime.now() + timedelta(days=1)
            )
        
        config = self.quotas[key]
        
        # Check if period needs reset
        self._check_period_reset(key)
        
        current_usage = self.usage[key][quota_id]
        remaining = config.max_requests - current_usage
        
        if current_usage + cost <= config.max_requests:
            # Within quota
            self.usage[key][quota_id] += cost
            
            return RateLimitResult(
                status=RateLimitStatus.ALLOWED,
                allowed=True,
                remaining=remaining - cost,
                reset_time=self.period_start[key] + timedelta(
                    seconds=config.period_seconds
                ),
                metadata={
                    'quota_id': quota_id,
                    'usage': current_usage + cost,
                    'max_requests': config.max_requests
                }
            )
        
        elif config.overage_allowed:
            # Allow with overage charge
            overage_cost = int(cost * (1 + config.overage_rate))
            self.usage[key][quota_id] += overage_cost
            
            return RateLimitResult(
                status=RateLimitStatus.ALLOWED,
                allowed=True,
                remaining=0,
                reset_time=self.period_start[key] + timedelta(
                    seconds=config.period_seconds
                ),
                metadata={
                    'quota_id': quota_id,
                    'usage': current_usage + overage_cost,
                    'max_requests': config.max_requests,
                    'overage': True,
                    'overage_cost': overage_cost
                }
            )
        
        else:
            # Quota exceeded
            reset_time = self.period_start[key] + timedelta(
                seconds=config.period_seconds
            )
            retry_after = int((reset_time - datetime.now()).total_seconds())
            
            return RateLimitResult(
                status=RateLimitStatus.BLOCKED,
                allowed=False,
                remaining=0,
                reset_time=reset_time,
                retry_after=retry_after,
                metadata={
                    'quota_id': quota_id,
                    'usage': current_usage,
                    'max_requests': config.max_requests
                }
            )
    
    def _check_period_reset(self, key: str):
        """Check if quota period needs reset"""
        if key not in self.period_start:
            self.period_start[key] = datetime.now()
            return
        
        config = self.quotas[key]
        elapsed = (datetime.now() - self.period_start[key]).total_seconds()
        
        if elapsed >= config.period_seconds:
            # Reset period
            quota_id = key.split(':')[1]
            self.usage[key][quota_id] = 0
            self.period_start[key] = datetime.now()
            logger.info(f"[QUOTA] Period reset: {key}")
    
    def get_usage(self, user_id: str, quota_id: str) -> Dict[str, Any]:
        """Get quota usage"""
        key = f"{user_id}:{quota_id}"
        
        if key not in self.quotas:
            return {}
        
        config = self.quotas[key]
        current_usage = self.usage[key][quota_id]
        
        return {
            'user_id': user_id,
            'quota_id': quota_id,
            'usage': current_usage,
            'max_requests': config.max_requests,
            'remaining': config.max_requests - current_usage,
            'period_seconds': config.period_seconds,
            'period_start': self.period_start[key].isoformat(),
            'period_end': (
                self.period_start[key] + timedelta(seconds=config.period_seconds)
            ).isoformat()
        }

# ======================================================================================================================
# RATE LIMITING MIDDLEWARE
# ======================================================================================================================

class RateLimitMiddleware:
    """Rate limiting middleware for API requests"""
    
    def __init__(self, rate_limiter: RateLimiterManager,
                 quota_manager: Optional[QuotaManager] = None):
        self.rate_limiter = rate_limiter
        self.quota_manager = quota_manager
        
        logger.info("[MIDDLEWARE] Rate limit middleware initialized")
    
    def get_client_identifier(self, request: Dict[str, Any]) -> str:
        """Get client identifier from request"""
        # Try API key first
        api_key = request.get('headers', {}).get('X-API-Key')
        if api_key:
            return f"api_key:{hashlib.md5(api_key.encode()).hexdigest()}"
        
        # Try user ID
        user_id = request.get('user_id')
        if user_id:
            return f"user:{user_id}"
        
        # Fall back to IP address
        ip = request.get('client_ip', 'unknown')
        return f"ip:{ip}"
    
    async def check_rate_limit(self, request: Dict[str, Any]) -> RateLimitResult:
        """Check rate limit for request"""
        identifier = self.get_client_identifier(request)
        
        # Check rate limit
        result = self.rate_limiter.check_limit(identifier)
        
        if not result.allowed:
            logger.warning(
                f"[MIDDLEWARE] Rate limit exceeded: {identifier} "
                f"(retry after {result.retry_after}s)"
            )
        
        return result
    
    async def check_quota(self, request: Dict[str, Any],
                         quota_id: str = "default") -> RateLimitResult:
        """Check quota for request"""
        if not self.quota_manager:
            return RateLimitResult(
                status=RateLimitStatus.ALLOWED,
                allowed=True,
                remaining=999999,
                reset_time=datetime.now() + timedelta(days=1)
            )
        
        user_id = request.get('user_id', 'anonymous')
        cost = request.get('cost', 1)
        
        result = self.quota_manager.check_quota(user_id, quota_id, cost)
        
        if not result.allowed:
            logger.warning(
                f"[MIDDLEWARE] Quota exceeded: {user_id}/{quota_id}"
            )
        
        return result
    
    def add_rate_limit_headers(self, response: Dict[str, Any],
                               result: RateLimitResult) -> Dict[str, Any]:
        """Add rate limit headers to response"""
        headers = response.get('headers', {})
        
        headers['X-RateLimit-Limit'] = str(result.remaining + 1)
        headers['X-RateLimit-Remaining'] = str(result.remaining)
        headers['X-RateLimit-Reset'] = str(int(result.reset_time.timestamp()))
        
        if result.retry_after:
            headers['Retry-After'] = str(result.retry_after)
        
        response['headers'] = headers
        return response

# ======================================================================================================================
# THROTTLING STRATEGIES
# ======================================================================================================================

class AdaptiveThrottling:
    """Adaptive throttling based on system load"""
    
    def __init__(self, base_limit: int):
        self.base_limit = base_limit
        self.current_limit = base_limit
        self.cpu_threshold = 80.0
        self.memory_threshold = 85.0
        
        logger.info(f"[ADAPTIVE] Adaptive throttling initialized: base={base_limit}")
    
    def adjust_limit(self, cpu_usage: float, memory_usage: float) -> int:
        """Adjust rate limit based on system metrics"""
        if cpu_usage > self.cpu_threshold or memory_usage > self.memory_threshold:
            # Reduce limit
            reduction_factor = 0.7
            self.current_limit = int(self.base_limit * reduction_factor)
            logger.warning(
                f"[ADAPTIVE] Reduced limit to {self.current_limit} "
                f"(CPU: {cpu_usage}%, Mem: {memory_usage}%)"
            )
        else:
            # Restore limit
            self.current_limit = self.base_limit
        
        return self.current_limit

# ======================================================================================================================
# RATE LIMITING ORCHESTRATOR
# ======================================================================================================================

class RateLimitingOrchestrator:
    """Main rate limiting orchestrator"""
    
    def __init__(self):
        self.rate_limiter = RateLimiterManager()
        self.quota_manager = QuotaManager()
        self.middleware = RateLimitMiddleware(self.rate_limiter, self.quota_manager)
        self.adaptive_throttling = AdaptiveThrottling(base_limit=100)
        
        logger.info("[RATE-LIMIT-ORCH] Rate limiting orchestrator initialized")
    
    def configure_rate_limit(self, identifier: str, config: RateLimitConfig):
        """Configure rate limit"""
        self.rate_limiter.create_limiter(identifier, config)
    
    def configure_quota(self, user_id: str, config: QuotaConfig):
        """Configure quota"""
        self.quota_manager.set_quota(user_id, config)
    
    async def check_request(self, request: Dict[str, Any]) -> RateLimitResult:
        """Check request against rate limit and quota"""
        # Check rate limit
        rate_result = await self.middleware.check_rate_limit(request)
        if not rate_result.allowed:
            return rate_result
        
        # Check quota
        quota_result = await self.middleware.check_quota(request)
        return quota_result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics"""
        return {
            'configured_limiters': len(self.rate_limiter.limiters),
            'configured_quotas': len(self.quota_manager.quotas),
            'adaptive_limit': self.adaptive_throttling.current_limit
        }

# ======================================================================================================================
# END OF API RATE LIMITING & THROTTLING MODULE
# Lines in this file: ~750+
# Combined total: ~27,350+
# Remaining for 50k: ~22,650 lines
# ======================================================================================================================
