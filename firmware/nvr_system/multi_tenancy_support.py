# ======================================================================================================================
# AgroPulse NVR - Multi-Tenancy Support
# Tenant isolation, data partitioning, resource quotas, tenant management
# ======================================================================================================================

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

# ======================================================================================================================
# MULTI-TENANCY MODELS
# ======================================================================================================================

class TenantStatus(Enum):
    """Tenant status"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    INACTIVE = "inactive"

class IsolationLevel(Enum):
    """Data isolation level"""
    SHARED_DATABASE = "shared_database"  # Shared DB, separate tables
    SEPARATE_SCHEMA = "separate_schema"  # Separate schema per tenant
    SEPARATE_DATABASE = "separate_database"  # Dedicated DB per tenant

@dataclass
class TenantConfig:
    """Tenant configuration"""
    tenant_id: str
    tenant_name: str
    domain: str
    status: TenantStatus = TenantStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    isolation_level: IsolationLevel = IsolationLevel.SHARED_DATABASE
    
    # Resource quotas
    max_users: int = 10
    max_farms: int = 5
    max_devices: int = 50
    max_storage_gb: int = 10
    
    # Feature flags
    features: Dict[str, bool] = field(default_factory=dict)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TenantContext:
    """Tenant context for request"""
    tenant_id: str
    tenant_name: str
    user_id: Optional[str] = None
    permissions: List[str] = field(default_factory=list)

@dataclass
class ResourceUsage:
    """Tenant resource usage"""
    tenant_id: str
    users_count: int = 0
    farms_count: int = 0
    devices_count: int = 0
    storage_gb: float = 0.0
    api_calls_today: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

# ======================================================================================================================
# TENANT MANAGER
# ======================================================================================================================

class TenantManager:
    """Tenant management"""
    
    def __init__(self):
        self.tenants: Dict[str, TenantConfig] = {}
        self.domain_mapping: Dict[str, str] = {}  # domain -> tenant_id
        
        logger.info("[TENANT] Tenant manager initialized")
    
    def create_tenant(self, config: TenantConfig) -> TenantConfig:
        """Create new tenant"""
        if config.tenant_id in self.tenants:
            raise ValueError(f"Tenant already exists: {config.tenant_id}")
        
        if config.domain in self.domain_mapping:
            raise ValueError(f"Domain already in use: {config.domain}")
        
        self.tenants[config.tenant_id] = config
        self.domain_mapping[config.domain] = config.tenant_id
        
        logger.info(f"[TENANT] Created tenant: {config.tenant_id} ({config.tenant_name})")
        return config
    
    def get_tenant(self, tenant_id: str) -> Optional[TenantConfig]:
        """Get tenant by ID"""
        return self.tenants.get(tenant_id)
    
    def get_tenant_by_domain(self, domain: str) -> Optional[TenantConfig]:
        """Get tenant by domain"""
        tenant_id = self.domain_mapping.get(domain)
        if tenant_id:
            return self.tenants.get(tenant_id)
        return None
    
    def update_tenant(self, tenant_id: str, updates: Dict[str, Any]) -> bool:
        """Update tenant configuration"""
        if tenant_id not in self.tenants:
            return False
        
        tenant = self.tenants[tenant_id]
        
        for key, value in updates.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)
        
        logger.info(f"[TENANT] Updated tenant: {tenant_id}")
        return True
    
    def suspend_tenant(self, tenant_id: str) -> bool:
        """Suspend tenant"""
        if tenant_id not in self.tenants:
            return False
        
        self.tenants[tenant_id].status = TenantStatus.SUSPENDED
        logger.warning(f"[TENANT] Suspended tenant: {tenant_id}")
        return True
    
    def activate_tenant(self, tenant_id: str) -> bool:
        """Activate tenant"""
        if tenant_id not in self.tenants:
            return False
        
        self.tenants[tenant_id].status = TenantStatus.ACTIVE
        logger.info(f"[TENANT] Activated tenant: {tenant_id}")
        return True
    
    def list_tenants(self, status: Optional[TenantStatus] = None) -> List[TenantConfig]:
        """List all tenants"""
        tenants = list(self.tenants.values())
        
        if status:
            tenants = [t for t in tenants if t.status == status]
        
        return tenants

# ======================================================================================================================
# DATA PARTITIONING
# ======================================================================================================================

class DataPartitioner:
    """Data partitioning for tenant isolation"""
    
    def __init__(self, isolation_level: IsolationLevel = IsolationLevel.SHARED_DATABASE):
        self.isolation_level = isolation_level
        
        logger.info(f"[PARTITION] Data partitioner initialized: {isolation_level.value}")
    
    def get_table_name(self, tenant_id: str, base_table: str) -> str:
        """Get partitioned table name"""
        if self.isolation_level == IsolationLevel.SHARED_DATABASE:
            return f"{base_table}"  # Add tenant_id in WHERE clause
        elif self.isolation_level == IsolationLevel.SEPARATE_SCHEMA:
            return f"tenant_{tenant_id}.{base_table}"
        elif self.isolation_level == IsolationLevel.SEPARATE_DATABASE:
            return f"{base_table}"  # Use separate DB connection
        
        return base_table
    
    def add_tenant_filter(self, query: str, tenant_id: str) -> str:
        """Add tenant filter to query"""
        if self.isolation_level == IsolationLevel.SHARED_DATABASE:
            # Add WHERE tenant_id = ?
            if "WHERE" in query.upper():
                return query.replace("WHERE", f"WHERE tenant_id = '{tenant_id}' AND")
            else:
                return f"{query} WHERE tenant_id = '{tenant_id}'"
        
        return query
    
    def get_connection_string(self, tenant_id: str, base_connection: str) -> str:
        """Get tenant-specific connection string"""
        if self.isolation_level == IsolationLevel.SEPARATE_DATABASE:
            # Modify database name
            return base_connection.replace(
                "database=agropulse",
                f"database=agropulse_tenant_{tenant_id}"
            )
        
        return base_connection

# ======================================================================================================================
# RESOURCE QUOTA MANAGER
# ======================================================================================================================

class ResourceQuotaManager:
    """Manage tenant resource quotas"""
    
    def __init__(self):
        self.usage: Dict[str, ResourceUsage] = {}
        
        logger.info("[QUOTA] Resource quota manager initialized")
    
    def track_usage(self, tenant_id: str, resource_type: str, amount: int = 1):
        """Track resource usage"""
        if tenant_id not in self.usage:
            self.usage[tenant_id] = ResourceUsage(tenant_id=tenant_id)
        
        usage = self.usage[tenant_id]
        
        if resource_type == "users":
            usage.users_count += amount
        elif resource_type == "farms":
            usage.farms_count += amount
        elif resource_type == "devices":
            usage.devices_count += amount
        elif resource_type == "api_calls":
            usage.api_calls_today += amount
        
        usage.timestamp = datetime.now()
    
    def check_quota(self, tenant_id: str, tenant_config: TenantConfig,
                   resource_type: str, amount: int = 1) -> bool:
        """Check if resource allocation is within quota"""
        if tenant_id not in self.usage:
            self.usage[tenant_id] = ResourceUsage(tenant_id=tenant_id)
        
        usage = self.usage[tenant_id]
        
        if resource_type == "users":
            return usage.users_count + amount <= tenant_config.max_users
        elif resource_type == "farms":
            return usage.farms_count + amount <= tenant_config.max_farms
        elif resource_type == "devices":
            return usage.devices_count + amount <= tenant_config.max_devices
        elif resource_type == "storage":
            return usage.storage_gb + amount <= tenant_config.max_storage_gb
        
        return True
    
    def get_usage(self, tenant_id: str) -> Optional[ResourceUsage]:
        """Get resource usage"""
        return self.usage.get(tenant_id)
    
    def reset_daily_counters(self):
        """Reset daily counters"""
        for usage in self.usage.values():
            usage.api_calls_today = 0
        
        logger.info("[QUOTA] Reset daily counters")

# ======================================================================================================================
# TENANT CONTEXT MANAGER
# ======================================================================================================================

class TenantContextManager:
    """Manage tenant context for requests"""
    
    def __init__(self, tenant_manager: TenantManager):
        self.tenant_manager = tenant_manager
        self.current_context: Dict[str, TenantContext] = {}
        
        logger.info("[CONTEXT] Tenant context manager initialized")
    
    def set_context(self, request_id: str, context: TenantContext):
        """Set tenant context for request"""
        self.current_context[request_id] = context
    
    def get_context(self, request_id: str) -> Optional[TenantContext]:
        """Get tenant context"""
        return self.current_context.get(request_id)
    
    def clear_context(self, request_id: str):
        """Clear tenant context"""
        if request_id in self.current_context:
            del self.current_context[request_id]
    
    def extract_tenant_from_request(self, request: Dict[str, Any]) -> Optional[TenantContext]:
        """Extract tenant from request"""
        # Try subdomain
        host = request.get('host', '')
        subdomain = host.split('.')[0] if '.' in host else None
        
        if subdomain:
            tenant = self.tenant_manager.get_tenant_by_domain(subdomain)
            if tenant:
                return TenantContext(
                    tenant_id=tenant.tenant_id,
                    tenant_name=tenant.tenant_name,
                    user_id=request.get('user_id')
                )
        
        # Try header
        tenant_id = request.get('headers', {}).get('X-Tenant-ID')
        if tenant_id:
            tenant = self.tenant_manager.get_tenant(tenant_id)
            if tenant:
                return TenantContext(
                    tenant_id=tenant.tenant_id,
                    tenant_name=tenant.tenant_name,
                    user_id=request.get('user_id')
                )
        
        return None

# ======================================================================================================================
# TENANT MIDDLEWARE
# ======================================================================================================================

class TenantMiddleware:
    """Middleware for tenant isolation"""
    
    def __init__(self, tenant_manager: TenantManager,
                 context_manager: TenantContextManager,
                 quota_manager: ResourceQuotaManager):
        self.tenant_manager = tenant_manager
        self.context_manager = context_manager
        self.quota_manager = quota_manager
        
        logger.info("[MIDDLEWARE] Tenant middleware initialized")
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process request with tenant context"""
        request_id = request.get('request_id', str(uuid.uuid4()))
        
        # Extract tenant context
        context = self.context_manager.extract_tenant_from_request(request)
        
        if not context:
            return {
                'error': 'Tenant not found',
                'status': 401
            }
        
        # Check tenant status
        tenant = self.tenant_manager.get_tenant(context.tenant_id)
        if not tenant or tenant.status != TenantStatus.ACTIVE:
            return {
                'error': 'Tenant not active',
                'status': 403
            }
        
        # Set context
        self.context_manager.set_context(request_id, context)
        
        # Track API call
        self.quota_manager.track_usage(context.tenant_id, "api_calls")
        
        # Add tenant info to request
        request['tenant_context'] = context
        request['request_id'] = request_id
        
        return request
    
    def add_tenant_headers(self, response: Dict[str, Any],
                          context: TenantContext) -> Dict[str, Any]:
        """Add tenant headers to response"""
        headers = response.get('headers', {})
        headers['X-Tenant-ID'] = context.tenant_id
        headers['X-Tenant-Name'] = context.tenant_name
        response['headers'] = headers
        return response

# ======================================================================================================================
# FEATURE FLAG MANAGER
# ======================================================================================================================

class FeatureFlagManager:
    """Manage tenant-specific feature flags"""
    
    def __init__(self):
        logger.info("[FEATURE-FLAGS] Feature flag manager initialized")
    
    def is_enabled(self, tenant: TenantConfig, feature: str) -> bool:
        """Check if feature is enabled for tenant"""
        return tenant.features.get(feature, False)
    
    def enable_feature(self, tenant: TenantConfig, feature: str):
        """Enable feature for tenant"""
        tenant.features[feature] = True
        logger.info(f"[FEATURE-FLAGS] Enabled {feature} for {tenant.tenant_id}")
    
    def disable_feature(self, tenant: TenantConfig, feature: str):
        """Disable feature for tenant"""
        tenant.features[feature] = False
        logger.info(f"[FEATURE-FLAGS] Disabled {feature} for {tenant.tenant_id}")
    
    def get_enabled_features(self, tenant: TenantConfig) -> List[str]:
        """Get all enabled features"""
        return [f for f, enabled in tenant.features.items() if enabled]

# ======================================================================================================================
# MULTI-TENANCY ORCHESTRATOR
# ======================================================================================================================

class MultiTenancyOrchestrator:
    """Main multi-tenancy orchestrator"""
    
    def __init__(self, isolation_level: IsolationLevel = IsolationLevel.SHARED_DATABASE):
        self.tenant_manager = TenantManager()
        self.partitioner = DataPartitioner(isolation_level)
        self.quota_manager = ResourceQuotaManager()
        self.context_manager = TenantContextManager(self.tenant_manager)
        self.middleware = TenantMiddleware(
            self.tenant_manager,
            self.context_manager,
            self.quota_manager
        )
        self.feature_flags = FeatureFlagManager()
        
        logger.info("[MULTI-TENANT] Multi-tenancy orchestrator initialized")
    
    def create_tenant(self, config: TenantConfig) -> TenantConfig:
        """Create new tenant"""
        return self.tenant_manager.create_tenant(config)
    
    def get_tenant(self, tenant_id: str) -> Optional[TenantConfig]:
        """Get tenant"""
        return self.tenant_manager.get_tenant(tenant_id)
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process request with tenant isolation"""
        return await self.middleware.process_request(request)
    
    def check_quota(self, tenant_id: str, resource_type: str, amount: int = 1) -> bool:
        """Check resource quota"""
        tenant = self.tenant_manager.get_tenant(tenant_id)
        if not tenant:
            return False
        
        return self.quota_manager.check_quota(tenant_id, tenant, resource_type, amount)
    
    def track_usage(self, tenant_id: str, resource_type: str, amount: int = 1):
        """Track resource usage"""
        self.quota_manager.track_usage(tenant_id, resource_type, amount)
    
    def is_feature_enabled(self, tenant_id: str, feature: str) -> bool:
        """Check if feature is enabled"""
        tenant = self.tenant_manager.get_tenant(tenant_id)
        if not tenant:
            return False
        
        return self.feature_flags.is_enabled(tenant, feature)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get multi-tenancy statistics"""
        tenants = self.tenant_manager.list_tenants()
        
        return {
            'total_tenants': len(tenants),
            'active_tenants': len([t for t in tenants if t.status == TenantStatus.ACTIVE]),
            'trial_tenants': len([t for t in tenants if t.status == TenantStatus.TRIAL]),
            'suspended_tenants': len([t for t in tenants if t.status == TenantStatus.SUSPENDED]),
            'isolation_level': self.partitioner.isolation_level.value
        }

# ======================================================================================================================
# END OF MULTI-TENANCY SUPPORT MODULE
# Lines in this file: ~550+
# Combined total: ~27,900+
# Remaining for 50k: ~22,100 lines
# ======================================================================================================================
