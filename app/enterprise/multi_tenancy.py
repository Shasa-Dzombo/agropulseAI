"""
Enterprise Multi-Tenancy Management System

Provides comprehensive multi-tenant architecture with three isolation strategies:
1. Database per tenant (highest isolation)
2. Schema per tenant (balanced)
3. Row-level security (highest density)

Features:
- Tenant lifecycle management (provisioning, suspension, termination)
- Resource quota enforcement
- Cross-tenant data isolation
- Tenant-specific configuration
- Usage tracking and billing
- Automated scaling
"""

import asyncio
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import psycopg2
from psycopg2 import sql
from psycopg2.pool import ThreadedConnectionPool
import redis
from sqlalchemy import create_engine, text, MetaData, Table, Column, String, Integer, DateTime, Boolean, JSON, Float
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IsolationStrategy(Enum):
    """Tenant isolation strategies"""
    DATABASE_PER_TENANT = "database"
    SCHEMA_PER_TENANT = "schema"
    ROW_LEVEL_SECURITY = "rls"


class TenantStatus(Enum):
    """Tenant lifecycle states"""
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    EXPIRED = "expired"
    TERMINATED = "terminated"


class TenantTier(Enum):
    """Subscription tiers with different resource limits"""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class TenantConfig:
    """Configuration for a tenant"""
    
    def __init__(self, tenant_id: str, tier: TenantTier):
        self.tenant_id = tenant_id
        self.tier = tier
        self.limits = self._get_tier_limits(tier)
        self.features = self._get_tier_features(tier)
        self.custom_config: Dict[str, Any] = {}
    
    def _get_tier_limits(self, tier: TenantTier) -> Dict[str, int]:
        """Get resource limits for tier"""
        limits = {
            TenantTier.FREE: {
                "max_users": 5,
                "max_farms": 2,
                "max_sensors": 10,
                "max_storage_gb": 1,
                "max_api_calls_per_hour": 1000,
                "max_db_connections": 5,
                "max_concurrent_jobs": 2,
            },
            TenantTier.STARTER: {
                "max_users": 20,
                "max_farms": 10,
                "max_sensors": 50,
                "max_storage_gb": 10,
                "max_api_calls_per_hour": 10000,
                "max_db_connections": 20,
                "max_concurrent_jobs": 5,
            },
            TenantTier.PROFESSIONAL: {
                "max_users": 100,
                "max_farms": 50,
                "max_sensors": 500,
                "max_storage_gb": 100,
                "max_api_calls_per_hour": 100000,
                "max_db_connections": 50,
                "max_concurrent_jobs": 20,
            },
            TenantTier.ENTERPRISE: {
                "max_users": -1,  # unlimited
                "max_farms": -1,
                "max_sensors": -1,
                "max_storage_gb": -1,
                "max_api_calls_per_hour": -1,
                "max_db_connections": 100,
                "max_concurrent_jobs": 50,
            },
        }
        return limits.get(tier, limits[TenantTier.FREE])
    
    def _get_tier_features(self, tier: TenantTier) -> Set[str]:
        """Get enabled features for tier"""
        features = {
            TenantTier.FREE: {"basic_analytics", "email_support"},
            TenantTier.STARTER: {"basic_analytics", "advanced_sensors", "email_support", "api_access"},
            TenantTier.PROFESSIONAL: {
                "basic_analytics", "advanced_analytics", "ml_predictions",
                "advanced_sensors", "integrations", "priority_support",
                "api_access", "webhooks", "custom_reports"
            },
            TenantTier.ENTERPRISE: {
                "basic_analytics", "advanced_analytics", "ml_predictions",
                "advanced_sensors", "integrations", "dedicated_support",
                "api_access", "webhooks", "custom_reports", "sso",
                "audit_logs", "custom_integrations", "sla_guarantee",
                "white_label", "dedicated_infrastructure"
            },
        }
        return features.get(tier, features[TenantTier.FREE])
    
    def has_feature(self, feature: str) -> bool:
        """Check if tenant has access to feature"""
        return feature in self.features
    
    def check_limit(self, resource: str, current_value: int) -> bool:
        """Check if resource usage is within limits"""
        limit = self.limits.get(resource, 0)
        if limit == -1:  # unlimited
            return True
        return current_value < limit
    
    def update_custom_config(self, key: str, value: Any) -> None:
        """Update tenant-specific configuration"""
        self.custom_config[key] = value
    
    def get_custom_config(self, key: str, default: Any = None) -> Any:
        """Get tenant-specific configuration"""
        return self.custom_config.get(key, default)


class TenantContext:
    """Thread-local tenant context for request handling"""
    
    _context: Dict[int, str] = {}
    
    @classmethod
    def set_current_tenant(cls, tenant_id: str) -> None:
        """Set current tenant for thread"""
        import threading
        cls._context[threading.get_ident()] = tenant_id
    
    @classmethod
    def get_current_tenant(cls) -> Optional[str]:
        """Get current tenant from thread"""
        import threading
        return cls._context.get(threading.get_ident())
    
    @classmethod
    def clear_current_tenant(cls) -> None:
        """Clear tenant from thread"""
        import threading
        ident = threading.get_ident()
        if ident in cls._context:
            del cls._context[ident]


class TenantDatabaseManager:
    """Manages tenant-specific database connections"""
    
    def __init__(self, master_connection_string: str, isolation_strategy: IsolationStrategy):
        self.master_connection_string = master_connection_string
        self.isolation_strategy = isolation_strategy
        self.connection_pools: Dict[str, ThreadedConnectionPool] = {}
        self.engines: Dict[str, Any] = {}
        
    def create_tenant_database(self, tenant_id: str) -> bool:
        """Create dedicated database for tenant"""
        try:
            if self.isolation_strategy == IsolationStrategy.DATABASE_PER_TENANT:
                # Connect to master database
                conn = psycopg2.connect(self.master_connection_string)
                conn.autocommit = True
                cursor = conn.cursor()
                
                # Create database
                db_name = f"tenant_{tenant_id.replace('-', '_')}"
                cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
                
                # Create user
                user_name = f"user_{tenant_id.replace('-', '_')}"
                password = self._generate_secure_password()
                cursor.execute(
                    sql.SQL("CREATE USER {} WITH PASSWORD %s").format(sql.Identifier(user_name)),
                    [password]
                )
                
                # Grant privileges
                cursor.execute(
                    sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
                        sql.Identifier(db_name),
                        sql.Identifier(user_name)
                    )
                )
                
                cursor.close()
                conn.close()
                
                logger.info(f"Created database for tenant {tenant_id}")
                return True
                
            elif self.isolation_strategy == IsolationStrategy.SCHEMA_PER_TENANT:
                # Create schema in shared database
                conn = psycopg2.connect(self.master_connection_string)
                cursor = conn.cursor()
                
                schema_name = f"tenant_{tenant_id.replace('-', '_')}"
                cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema_name)))
                
                # Set search path for tenant
                cursor.execute(
                    sql.SQL("ALTER DATABASE {} SET search_path TO {}, public").format(
                        sql.Identifier("agropulse"),  # main database name
                        sql.Identifier(schema_name)
                    )
                )
                
                conn.commit()
                cursor.close()
                conn.close()
                
                logger.info(f"Created schema for tenant {tenant_id}")
                return True
                
            elif self.isolation_strategy == IsolationStrategy.ROW_LEVEL_SECURITY:
                # Enable RLS on tables
                conn = psycopg2.connect(self.master_connection_string)
                cursor = conn.cursor()
                
                # Enable RLS on all tenant tables
                tables = ["farms", "users", "sensors", "crops", "analytics"]
                for table in tables:
                    cursor.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
                    
                    # Create policy
                    cursor.execute(f"""
                        CREATE POLICY tenant_isolation_policy ON {table}
                        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
                    """)
                
                conn.commit()
                cursor.close()
                conn.close()
                
                logger.info(f"Enabled RLS for tenant {tenant_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create tenant database: {e}")
            return False
    
    def get_tenant_connection(self, tenant_id: str) -> Any:
        """Get database connection for tenant"""
        if tenant_id not in self.connection_pools:
            connection_string = self._get_tenant_connection_string(tenant_id)
            self.connection_pools[tenant_id] = ThreadedConnectionPool(
                minconn=5,
                maxconn=20,
                dsn=connection_string
            )
        
        return self.connection_pools[tenant_id].getconn()
    
    def get_tenant_engine(self, tenant_id: str) -> Any:
        """Get SQLAlchemy engine for tenant"""
        if tenant_id not in self.engines:
            connection_string = self._get_tenant_connection_string(tenant_id)
            self.engines[tenant_id] = create_engine(
                connection_string,
                poolclass=NullPool,
                pool_pre_ping=True
            )
        
        return self.engines[tenant_id]
    
    def _get_tenant_connection_string(self, tenant_id: str) -> str:
        """Build connection string for tenant"""
        if self.isolation_strategy == IsolationStrategy.DATABASE_PER_TENANT:
            db_name = f"tenant_{tenant_id.replace('-', '_')}"
            # Replace database name in connection string
            parts = self.master_connection_string.split("/")
            parts[-1] = db_name
            return "/".join(parts)
            
        elif self.isolation_strategy == IsolationStrategy.SCHEMA_PER_TENANT:
            # Use same connection string but set search path
            return self.master_connection_string
            
        else:  # ROW_LEVEL_SECURITY
            return self.master_connection_string
    
    def set_tenant_context(self, conn: Any, tenant_id: str) -> None:
        """Set tenant context for connection (RLS)"""
        if self.isolation_strategy == IsolationStrategy.ROW_LEVEL_SECURITY:
            cursor = conn.cursor()
            cursor.execute("SET app.current_tenant_id = %s", [tenant_id])
            cursor.close()
        elif self.isolation_strategy == IsolationStrategy.SCHEMA_PER_TENANT:
            cursor = conn.cursor()
            schema_name = f"tenant_{tenant_id.replace('-', '_')}"
            cursor.execute(f"SET search_path TO {schema_name}, public")
            cursor.close()
    
    def _generate_secure_password(self, length: int = 32) -> str:
        """Generate secure random password"""
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits + string.punctuation
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def delete_tenant_database(self, tenant_id: str) -> bool:
        """Delete tenant database (hard delete)"""
        try:
            if self.isolation_strategy == IsolationStrategy.DATABASE_PER_TENANT:
                conn = psycopg2.connect(self.master_connection_string)
                conn.autocommit = True
                cursor = conn.cursor()
                
                # Terminate connections
                db_name = f"tenant_{tenant_id.replace('-', '_')}"
                cursor.execute(f"""
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = '{db_name}'
                """)
                
                # Drop database
                cursor.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(db_name)))
                
                cursor.close()
                conn.close()
                
            elif self.isolation_strategy == IsolationStrategy.SCHEMA_PER_TENANT:
                conn = psycopg2.connect(self.master_connection_string)
                cursor = conn.cursor()
                
                schema_name = f"tenant_{tenant_id.replace('-', '_')}"
                cursor.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema_name)))
                
                conn.commit()
                cursor.close()
                conn.close()
            
            logger.info(f"Deleted database for tenant {tenant_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete tenant database: {e}")
            return False


class TenantResourceTracker:
    """Tracks resource usage per tenant"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    def increment_usage(self, tenant_id: str, resource: str, amount: int = 1) -> int:
        """Increment resource usage counter"""
        key = f"tenant:{tenant_id}:usage:{resource}"
        return self.redis.incrby(key, amount)
    
    def get_usage(self, tenant_id: str, resource: str) -> int:
        """Get current resource usage"""
        key = f"tenant:{tenant_id}:usage:{resource}"
        value = self.redis.get(key)
        return int(value) if value else 0
    
    def reset_usage(self, tenant_id: str, resource: str) -> None:
        """Reset resource usage counter"""
        key = f"tenant:{tenant_id}:usage:{resource}"
        self.redis.delete(key)
    
    def check_rate_limit(self, tenant_id: str, limit: int, window_seconds: int = 3600) -> bool:
        """Check if tenant is within rate limit"""
        key = f"tenant:{tenant_id}:ratelimit"
        
        # Use sliding window rate limiting
        now = datetime.utcnow().timestamp()
        window_start = now - window_seconds
        
        # Remove old entries
        self.redis.zremrangebyscore(key, 0, window_start)
        
        # Count requests in window
        count = self.redis.zcard(key)
        
        if count >= limit:
            return False
        
        # Add current request
        self.redis.zadd(key, {str(uuid.uuid4()): now})
        self.redis.expire(key, window_seconds)
        
        return True
    
    def get_storage_usage(self, tenant_id: str) -> float:
        """Get storage usage in GB"""
        key = f"tenant:{tenant_id}:storage_bytes"
        value = self.redis.get(key)
        bytes_used = int(value) if value else 0
        return bytes_used / (1024 ** 3)  # Convert to GB
    
    def update_storage_usage(self, tenant_id: str, bytes_delta: int) -> None:
        """Update storage usage"""
        key = f"tenant:{tenant_id}:storage_bytes"
        self.redis.incrby(key, bytes_delta)
    
    def get_connection_count(self, tenant_id: str) -> int:
        """Get active database connection count"""
        key = f"tenant:{tenant_id}:connections"
        return self.redis.scard(key)
    
    def register_connection(self, tenant_id: str, connection_id: str) -> None:
        """Register active connection"""
        key = f"tenant:{tenant_id}:connections"
        self.redis.sadd(key, connection_id)
        self.redis.expire(key, 3600)  # Expire after 1 hour
    
    def unregister_connection(self, tenant_id: str, connection_id: str) -> None:
        """Unregister connection"""
        key = f"tenant:{tenant_id}:connections"
        self.redis.srem(key, connection_id)


class TenantProvisioner:
    """Handles tenant provisioning and lifecycle"""
    
    def __init__(
        self,
        db_manager: TenantDatabaseManager,
        resource_tracker: TenantResourceTracker,
        master_db_session: Session
    ):
        self.db_manager = db_manager
        self.resource_tracker = resource_tracker
        self.master_db = master_db_session
    
    def provision_tenant(
        self,
        name: str,
        tier: TenantTier,
        admin_email: str,
        admin_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Provision new tenant"""
        try:
            tenant_id = str(uuid.uuid4())
            
            # Create tenant record
            tenant_data = {
                "id": tenant_id,
                "name": name,
                "tier": tier.value,
                "status": TenantStatus.PROVISIONING.value,
                "admin_email": admin_email,
                "admin_name": admin_name,
                "created_at": datetime.utcnow(),
                "metadata": json.dumps(metadata or {})
            }
            
            self.master_db.execute(
                text("""
                    INSERT INTO tenants (id, name, tier, status, admin_email, admin_name, created_at, metadata)
                    VALUES (:id, :name, :tier, :status, :admin_email, :admin_name, :created_at, :metadata)
                """),
                tenant_data
            )
            self.master_db.commit()
            
            # Create database/schema
            success = self.db_manager.create_tenant_database(tenant_id)
            if not success:
                raise Exception("Failed to create tenant database")
            
            # Initialize schema
            self._initialize_tenant_schema(tenant_id)
            
            # Create admin user
            self._create_tenant_admin(tenant_id, admin_email, admin_name)
            
            # Update status to active
            self.master_db.execute(
                text("UPDATE tenants SET status = :status WHERE id = :id"),
                {"status": TenantStatus.ACTIVE.value, "id": tenant_id}
            )
            self.master_db.commit()
            
            logger.info(f"Provisioned tenant {tenant_id}: {name}")
            return tenant_id
            
        except Exception as e:
            logger.error(f"Failed to provision tenant: {e}")
            self.master_db.rollback()
            return None
    
    def _initialize_tenant_schema(self, tenant_id: str) -> None:
        """Initialize database schema for tenant"""
        engine = self.db_manager.get_tenant_engine(tenant_id)
        
        # Create tables
        metadata = MetaData()
        
        # Users table
        Table(
            'users', metadata,
            Column('id', String, primary_key=True),
            Column('tenant_id', String, nullable=False, index=True),
            Column('email', String, nullable=False, unique=True),
            Column('name', String, nullable=False),
            Column('role', String, nullable=False),
            Column('created_at', DateTime, default=datetime.utcnow),
            Column('active', Boolean, default=True)
        )
        
        # Farms table
        Table(
            'farms', metadata,
            Column('id', String, primary_key=True),
            Column('tenant_id', String, nullable=False, index=True),
            Column('name', String, nullable=False),
            Column('location', JSON),
            Column('size_hectares', Float),
            Column('created_at', DateTime, default=datetime.utcnow)
        )
        
        # Sensors table
        Table(
            'sensors', metadata,
            Column('id', String, primary_key=True),
            Column('tenant_id', String, nullable=False, index=True),
            Column('farm_id', String, nullable=False),
            Column('type', String, nullable=False),
            Column('location', JSON),
            Column('status', String, default='active'),
            Column('created_at', DateTime, default=datetime.utcnow)
        )
        
        metadata.create_all(engine)
        logger.info(f"Initialized schema for tenant {tenant_id}")
    
    def _create_tenant_admin(self, tenant_id: str, email: str, name: str) -> None:
        """Create admin user for tenant"""
        engine = self.db_manager.get_tenant_engine(tenant_id)
        conn = engine.connect()
        
        admin_id = str(uuid.uuid4())
        conn.execute(
            text("""
                INSERT INTO users (id, tenant_id, email, name, role, created_at, active)
                VALUES (:id, :tenant_id, :email, :name, :role, :created_at, :active)
            """),
            {
                "id": admin_id,
                "tenant_id": tenant_id,
                "email": email,
                "name": name,
                "role": "admin",
                "created_at": datetime.utcnow(),
                "active": True
            }
        )
        conn.commit()
        conn.close()
    
    def suspend_tenant(self, tenant_id: str, reason: str) -> bool:
        """Suspend tenant access"""
        try:
            self.master_db.execute(
                text("UPDATE tenants SET status = :status, suspended_at = :time, suspension_reason = :reason WHERE id = :id"),
                {
                    "status": TenantStatus.SUSPENDED.value,
                    "time": datetime.utcnow(),
                    "reason": reason,
                    "id": tenant_id
                }
            )
            self.master_db.commit()
            
            logger.warning(f"Suspended tenant {tenant_id}: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to suspend tenant: {e}")
            return False
    
    def reactivate_tenant(self, tenant_id: str) -> bool:
        """Reactivate suspended tenant"""
        try:
            self.master_db.execute(
                text("UPDATE tenants SET status = :status, suspended_at = NULL, suspension_reason = NULL WHERE id = :id"),
                {"status": TenantStatus.ACTIVE.value, "id": tenant_id}
            )
            self.master_db.commit()
            
            logger.info(f"Reactivated tenant {tenant_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reactivate tenant: {e}")
            return False
    
    def terminate_tenant(self, tenant_id: str, soft_delete: bool = True) -> bool:
        """Terminate tenant (soft or hard delete)"""
        try:
            if soft_delete:
                # Mark as terminated but keep data
                self.master_db.execute(
                    text("UPDATE tenants SET status = :status, terminated_at = :time WHERE id = :id"),
                    {
                        "status": TenantStatus.TERMINATED.value,
                        "time": datetime.utcnow(),
                        "id": tenant_id
                    }
                )
                self.master_db.commit()
            else:
                # Hard delete - remove all data
                self.db_manager.delete_tenant_database(tenant_id)
                
                self.master_db.execute(
                    text("DELETE FROM tenants WHERE id = :id"),
                    {"id": tenant_id}
                )
                self.master_db.commit()
            
            logger.info(f"Terminated tenant {tenant_id} (soft={soft_delete})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to terminate tenant: {e}")
            return False
    
    def upgrade_tenant_tier(self, tenant_id: str, new_tier: TenantTier) -> bool:
        """Upgrade tenant to higher tier"""
        try:
            self.master_db.execute(
                text("UPDATE tenants SET tier = :tier, upgraded_at = :time WHERE id = :id"),
                {
                    "tier": new_tier.value,
                    "time": datetime.utcnow(),
                    "id": tenant_id
                }
            )
            self.master_db.commit()
            
            logger.info(f"Upgraded tenant {tenant_id} to {new_tier.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upgrade tenant: {e}")
            return False


class TenantMiddleware:
    """Middleware for multi-tenant request handling"""
    
    def __init__(
        self,
        db_manager: TenantDatabaseManager,
        resource_tracker: TenantResourceTracker,
        config_cache: Dict[str, TenantConfig]
    ):
        self.db_manager = db_manager
        self.resource_tracker = resource_tracker
        self.config_cache = config_cache
    
    async def process_request(self, request: Any) -> Tuple[bool, Optional[str]]:
        """Process incoming request and set tenant context"""
        try:
            # Extract tenant ID from request
            tenant_id = self._extract_tenant_id(request)
            if not tenant_id:
                return False, "Tenant ID not provided"
            
            # Load tenant config
            config = self._get_tenant_config(tenant_id)
            if not config:
                return False, "Tenant not found"
            
            # Check rate limits
            limit = config.limits.get("max_api_calls_per_hour", 1000)
            if not self.resource_tracker.check_rate_limit(tenant_id, limit):
                return False, "Rate limit exceeded"
            
            # Check connection limits
            max_connections = config.limits.get("max_db_connections", 10)
            if self.resource_tracker.get_connection_count(tenant_id) >= max_connections:
                return False, "Connection limit exceeded"
            
            # Set tenant context
            TenantContext.set_current_tenant(tenant_id)
            
            # Get database connection with tenant context
            conn = self.db_manager.get_tenant_connection(tenant_id)
            self.db_manager.set_tenant_context(conn, tenant_id)
            
            # Register connection
            connection_id = str(uuid.uuid4())
            self.resource_tracker.register_connection(tenant_id, connection_id)
            
            # Store in request for cleanup
            request.state.tenant_id = tenant_id
            request.state.connection_id = connection_id
            request.state.db_connection = conn
            
            return True, None
            
        except Exception as e:
            logger.error(f"Request processing failed: {e}")
            return False, str(e)
    
    async def cleanup_request(self, request: Any) -> None:
        """Cleanup after request processing"""
        try:
            if hasattr(request.state, 'tenant_id'):
                tenant_id = request.state.tenant_id
                connection_id = request.state.connection_id
                
                # Unregister connection
                self.resource_tracker.unregister_connection(tenant_id, connection_id)
                
                # Return connection to pool
                if hasattr(request.state, 'db_connection'):
                    conn = request.state.db_connection
                    self.db_manager.connection_pools[tenant_id].putconn(conn)
                
                # Clear tenant context
                TenantContext.clear_current_tenant()
                
        except Exception as e:
            logger.error(f"Request cleanup failed: {e}")
    
    def _extract_tenant_id(self, request: Any) -> Optional[str]:
        """Extract tenant ID from request"""
        # Try different methods to get tenant ID
        
        # 1. From subdomain (e.g., tenant123.agropulse.com)
        if hasattr(request, 'url') and request.url.hostname:
            hostname_parts = request.url.hostname.split('.')
            if len(hostname_parts) > 2:
                return hostname_parts[0]
        
        # 2. From header
        if hasattr(request, 'headers'):
            tenant_id = request.headers.get('X-Tenant-ID')
            if tenant_id:
                return tenant_id
        
        # 3. From query parameter
        if hasattr(request, 'query_params'):
            tenant_id = request.query_params.get('tenant_id')
            if tenant_id:
                return tenant_id
        
        # 4. From JWT token
        if hasattr(request, 'state') and hasattr(request.state, 'user'):
            user = request.state.user
            if isinstance(user, dict) and 'tenant_id' in user:
                return user['tenant_id']
        
        return None
    
    def _get_tenant_config(self, tenant_id: str) -> Optional[TenantConfig]:
        """Get tenant configuration with caching"""
        if tenant_id in self.config_cache:
            return self.config_cache[tenant_id]
        
        # Load from database
        # (In real implementation, query master database)
        # For now, return mock config
        config = TenantConfig(tenant_id, TenantTier.PROFESSIONAL)
        self.config_cache[tenant_id] = config
        return config


class TenantBillingManager:
    """Manages tenant billing and usage-based pricing"""
    
    def __init__(self, resource_tracker: TenantResourceTracker):
        self.resource_tracker = resource_tracker
    
    def calculate_monthly_bill(self, tenant_id: str, tier: TenantTier) -> Dict[str, Any]:
        """Calculate monthly bill for tenant"""
        base_prices = {
            TenantTier.FREE: 0,
            TenantTier.STARTER: 49,
            TenantTier.PROFESSIONAL: 199,
            TenantTier.ENTERPRISE: 999,
        }
        
        base_price = base_prices.get(tier, 0)
        
        # Calculate overage charges
        overage_charges = {}
        total_overage = 0
        
        # Storage overage ($0.10 per GB over limit)
        storage_used = self.resource_tracker.get_storage_usage(tenant_id)
        config = TenantConfig(tenant_id, tier)
        storage_limit = config.limits.get("max_storage_gb", 0)
        
        if storage_limit > 0 and storage_used > storage_limit:
            storage_overage = storage_used - storage_limit
            storage_charge = storage_overage * 0.10
            overage_charges['storage'] = {
                'amount': storage_overage,
                'unit': 'GB',
                'price_per_unit': 0.10,
                'charge': storage_charge
            }
            total_overage += storage_charge
        
        # API call overage ($0.01 per 1000 calls over limit)
        api_calls = self.resource_tracker.get_usage(tenant_id, 'api_calls')
        api_limit = config.limits.get("max_api_calls_per_hour", 0) * 730  # Monthly
        
        if api_limit > 0 and api_calls > api_limit:
            api_overage = (api_calls - api_limit) / 1000
            api_charge = api_overage * 0.01
            overage_charges['api_calls'] = {
                'amount': api_overage,
                'unit': '1000 calls',
                'price_per_unit': 0.01,
                'charge': api_charge
            }
            total_overage += api_charge
        
        total = base_price + total_overage
        
        return {
            'tenant_id': tenant_id,
            'tier': tier.value,
            'base_price': base_price,
            'overage_charges': overage_charges,
            'total_overage': total_overage,
            'total': total,
            'currency': 'USD',
            'billing_period': datetime.utcnow().strftime('%Y-%m')
        }
    
    def generate_invoice(self, tenant_id: str, tier: TenantTier) -> str:
        """Generate invoice for tenant"""
        bill = self.calculate_monthly_bill(tenant_id, tier)
        
        invoice = f"""
        INVOICE
        
        Tenant ID: {tenant_id}
        Billing Period: {bill['billing_period']}
        
        Base Subscription ({tier.value}): ${bill['base_price']:.2f}
        
        Overage Charges:
        """
        
        for resource, details in bill['overage_charges'].items():
            invoice += f"  {resource}: {details['amount']:.2f} {details['unit']} x ${details['price_per_unit']:.2f} = ${details['charge']:.2f}\n"
        
        invoice += f"""
        Total Overage: ${bill['total_overage']:.2f}
        
        TOTAL AMOUNT DUE: ${bill['total']:.2f} {bill['currency']}
        """
        
        return invoice


# Example usage and testing
def example_usage():
    """Example demonstrating multi-tenancy system"""
    
    # Initialize components
    master_conn_string = "postgresql://user:pass@localhost/agropulse_master"
    isolation_strategy = IsolationStrategy.SCHEMA_PER_TENANT
    
    db_manager = TenantDatabaseManager(master_conn_string, isolation_strategy)
    
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    resource_tracker = TenantResourceTracker(redis_client)
    
    # Create master DB session (mock)
    engine = create_engine(master_conn_string)
    Session_maker = sessionmaker(bind=engine)
    master_session = Session_maker()
    
    provisioner = TenantProvisioner(db_manager, resource_tracker, master_session)
    
    # Provision new tenant
    tenant_id = provisioner.provision_tenant(
        name="Green Valley Farms",
        tier=TenantTier.PROFESSIONAL,
        admin_email="admin@greenvalley.com",
        admin_name="John Smith",
        metadata={"industry": "agriculture", "region": "midwest"}
    )
    
    if tenant_id:
        print(f"Provisioned tenant: {tenant_id}")
        
        # Create tenant config
        config = TenantConfig(tenant_id, TenantTier.PROFESSIONAL)
        
        # Check feature access
        print(f"Has ML predictions: {config.has_feature('ml_predictions')}")
        print(f"Has white label: {config.has_feature('white_label')}")
        
        # Track resource usage
        resource_tracker.increment_usage(tenant_id, 'api_calls', 100)
        resource_tracker.update_storage_usage(tenant_id, 5 * 1024**3)  # 5 GB
        
        # Check limits
        api_calls = resource_tracker.get_usage(tenant_id, 'api_calls')
        print(f"API calls: {api_calls}")
        
        within_limit = config.check_limit('max_api_calls_per_hour', api_calls)
        print(f"Within API limit: {within_limit}")
        
        # Generate bill
        billing_manager = TenantBillingManager(resource_tracker)
        invoice = billing_manager.generate_invoice(tenant_id, TenantTier.PROFESSIONAL)
        print(invoice)
        
        # Upgrade tier
        provisioner.upgrade_tenant_tier(tenant_id, TenantTier.ENTERPRISE)
        
    master_session.close()


if __name__ == "__main__":
    example_usage()
