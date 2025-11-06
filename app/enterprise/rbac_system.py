"""
Role-Based Access Control (RBAC) System

Implements comprehensive RBAC with:
- Hierarchical roles with inheritance
- Fine-grained permissions
- Attribute-based access control (ABAC)
- Dynamic role assignment
- Permission delegation
- Audit logging
- Context-aware authorization

Features:
- Role hierarchy (admin > manager > user)
- Resource-level permissions
- Time-based access
- Conditional permissions
- Permission caching
- Bulk permission checks
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Callable

import redis
from sqlalchemy import create_engine, text, Column, String, DateTime, Boolean, JSON, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()


class PermissionAction(Enum):
    """Standard CRUD actions"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    APPROVE = "approve"
    SHARE = "share"
    EXPORT = "export"


class ResourceType(Enum):
    """System resources"""
    FARM = "farm"
    SENSOR = "sensor"
    CROP = "crop"
    USER = "user"
    REPORT = "report"
    ANALYTICS = "analytics"
    DEVICE = "device"
    ALERT = "alert"
    WORKFLOW = "workflow"
    INTEGRATION = "integration"


class Role(Base):
    """Role model"""
    __tablename__ = 'roles'
    
    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String)
    parent_role_id = Column(String, ForeignKey('roles.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_system_role = Column(Boolean, default=False)
    metadata = Column(JSON, default={})
    
    # Relationships
    parent_role = relationship("Role", remote_side=[id], backref="child_roles")


class Permission(Base):
    """Permission model"""
    __tablename__ = 'permissions'
    
    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    resource_type = Column(String, nullable=False)
    action = Column(String, nullable=False)
    description = Column(String)
    conditions = Column(JSON, default={})  # Conditional permissions
    created_at = Column(DateTime, default=datetime.utcnow)


# Association table for role-permission many-to-many
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', String, ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', String, ForeignKey('permissions.id'), primary_key=True),
    Column('granted_at', DateTime, default=datetime.utcnow)
)


class UserRole(Base):
    """User role assignments"""
    __tablename__ = 'user_roles'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    role_id = Column(String, ForeignKey('roles.id'), nullable=False)
    scope = Column(JSON, default={})  # Resource scope (e.g., specific farm)
    valid_from = Column(DateTime, default=datetime.utcnow)
    valid_until = Column(DateTime, nullable=True)  # For temporary roles
    assigned_by = Column(String, nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)


class PermissionDelegation(Base):
    """Delegated permissions"""
    __tablename__ = 'permission_delegations'
    
    id = Column(String, primary_key=True)
    delegator_id = Column(String, nullable=False, index=True)
    delegate_id = Column(String, nullable=False, index=True)
    permission_id = Column(String, ForeignKey('permissions.id'), nullable=False)
    scope = Column(JSON, default={})
    valid_from = Column(DateTime, default=datetime.utcnow)
    valid_until = Column(DateTime, nullable=False)
    can_redelegate = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AccessLog(Base):
    """Audit log for access attempts"""
    __tablename__ = 'access_logs'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    allowed = Column(Boolean, nullable=False)
    reason = Column(String)
    context = Column(JSON, default={})
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class RoleManager:
    """Manages roles and role hierarchy"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def create_role(
        self,
        name: str,
        description: str,
        parent_role_id: Optional[str] = None,
        is_system_role: bool = False
    ) -> str:
        """Create new role"""
        import uuid
        
        role_id = str(uuid.uuid4())
        role = Role(
            id=role_id,
            name=name,
            description=description,
            parent_role_id=parent_role_id,
            is_system_role=is_system_role
        )
        
        self.db.add(role)
        self.db.commit()
        
        logger.info(f"Created role: {name} (ID: {role_id})")
        return role_id
    
    def get_role(self, role_id: str) -> Optional[Role]:
        """Get role by ID"""
        return self.db.query(Role).filter(Role.id == role_id).first()
    
    def get_role_by_name(self, name: str) -> Optional[Role]:
        """Get role by name"""
        return self.db.query(Role).filter(Role.name == name).first()
    
    def get_role_hierarchy(self, role_id: str) -> List[str]:
        """Get all parent roles in hierarchy"""
        hierarchy = [role_id]
        
        current_role = self.get_role(role_id)
        while current_role and current_role.parent_role_id:
            hierarchy.append(current_role.parent_role_id)
            current_role = self.get_role(current_role.parent_role_id)
        
        return hierarchy
    
    def is_role_ancestor(self, potential_ancestor: str, role_id: str) -> bool:
        """Check if role is ancestor of another"""
        hierarchy = self.get_role_hierarchy(role_id)
        return potential_ancestor in hierarchy
    
    def delete_role(self, role_id: str) -> bool:
        """Delete role"""
        role = self.get_role(role_id)
        if not role:
            return False
        
        if role.is_system_role:
            logger.warning(f"Cannot delete system role: {role.name}")
            return False
        
        # Check if role has children
        children = self.db.query(Role).filter(Role.parent_role_id == role_id).count()
        if children > 0:
            logger.warning(f"Cannot delete role with children: {role.name}")
            return False
        
        self.db.delete(role)
        self.db.commit()
        
        logger.info(f"Deleted role: {role.name}")
        return True
    
    def initialize_system_roles(self) -> None:
        """Initialize default system roles"""
        # Super admin (top of hierarchy)
        super_admin_id = self.create_role(
            "super_admin",
            "Super administrator with full system access",
            is_system_role=True
        )
        
        # Admin (below super admin)
        admin_id = self.create_role(
            "admin",
            "Administrator with full tenant access",
            parent_role_id=super_admin_id,
            is_system_role=True
        )
        
        # Manager (below admin)
        manager_id = self.create_role(
            "manager",
            "Manager with elevated permissions",
            parent_role_id=admin_id,
            is_system_role=True
        )
        
        # User (below manager)
        user_id = self.create_role(
            "user",
            "Standard user with basic permissions",
            parent_role_id=manager_id,
            is_system_role=True
        )
        
        # Viewer (below user)
        self.create_role(
            "viewer",
            "Read-only access",
            parent_role_id=user_id,
            is_system_role=True
        )
        
        logger.info("Initialized system roles")


class PermissionManager:
    """Manages permissions and role-permission assignments"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def create_permission(
        self,
        name: str,
        resource_type: ResourceType,
        action: PermissionAction,
        description: str,
        conditions: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create new permission"""
        import uuid
        
        permission_id = str(uuid.uuid4())
        permission = Permission(
            id=permission_id,
            name=name,
            resource_type=resource_type.value,
            action=action.value,
            description=description,
            conditions=conditions or {}
        )
        
        self.db.add(permission)
        self.db.commit()
        
        logger.info(f"Created permission: {name} (ID: {permission_id})")
        return permission_id
    
    def get_permission(self, permission_id: str) -> Optional[Permission]:
        """Get permission by ID"""
        return self.db.query(Permission).filter(Permission.id == permission_id).first()
    
    def get_permission_by_name(self, name: str) -> Optional[Permission]:
        """Get permission by name"""
        return self.db.query(Permission).filter(Permission.name == name).first()
    
    def assign_permission_to_role(self, role_id: str, permission_id: str) -> bool:
        """Assign permission to role"""
        try:
            self.db.execute(
                text("""
                    INSERT INTO role_permissions (role_id, permission_id, granted_at)
                    VALUES (:role_id, :permission_id, :granted_at)
                """),
                {
                    "role_id": role_id,
                    "permission_id": permission_id,
                    "granted_at": datetime.utcnow()
                }
            )
            self.db.commit()
            
            logger.info(f"Assigned permission {permission_id} to role {role_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to assign permission: {e}")
            self.db.rollback()
            return False
    
    def revoke_permission_from_role(self, role_id: str, permission_id: str) -> bool:
        """Revoke permission from role"""
        try:
            self.db.execute(
                text("""
                    DELETE FROM role_permissions
                    WHERE role_id = :role_id AND permission_id = :permission_id
                """),
                {"role_id": role_id, "permission_id": permission_id}
            )
            self.db.commit()
            
            logger.info(f"Revoked permission {permission_id} from role {role_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke permission: {e}")
            return False
    
    def get_role_permissions(self, role_id: str) -> List[Permission]:
        """Get all permissions for role"""
        result = self.db.execute(
            text("""
                SELECT p.* FROM permissions p
                JOIN role_permissions rp ON p.id = rp.permission_id
                WHERE rp.role_id = :role_id
            """),
            {"role_id": role_id}
        )
        
        return [Permission(**dict(row)) for row in result]
    
    def initialize_standard_permissions(self) -> None:
        """Initialize standard CRUD permissions for all resources"""
        for resource_type in ResourceType:
            for action in PermissionAction:
                if action in [PermissionAction.CREATE, PermissionAction.READ, 
                             PermissionAction.UPDATE, PermissionAction.DELETE]:
                    name = f"{resource_type.value}:{action.value}"
                    description = f"{action.value.capitalize()} {resource_type.value}"
                    
                    self.create_permission(
                        name=name,
                        resource_type=resource_type,
                        action=action,
                        description=description
                    )
        
        logger.info("Initialized standard permissions")


class UserRoleManager:
    """Manages user role assignments"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def assign_role_to_user(
        self,
        user_id: str,
        role_id: str,
        assigned_by: str,
        scope: Optional[Dict[str, Any]] = None,
        valid_until: Optional[datetime] = None
    ) -> str:
        """Assign role to user"""
        import uuid
        
        assignment_id = str(uuid.uuid4())
        user_role = UserRole(
            id=assignment_id,
            user_id=user_id,
            role_id=role_id,
            scope=scope or {},
            valid_until=valid_until,
            assigned_by=assigned_by
        )
        
        self.db.add(user_role)
        self.db.commit()
        
        logger.info(f"Assigned role {role_id} to user {user_id}")
        return assignment_id
    
    def revoke_role_from_user(self, user_id: str, role_id: str) -> bool:
        """Revoke role from user"""
        result = self.db.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        ).delete()
        
        self.db.commit()
        
        if result > 0:
            logger.info(f"Revoked role {role_id} from user {user_id}")
            return True
        return False
    
    def get_user_roles(self, user_id: str, include_expired: bool = False) -> List[UserRole]:
        """Get all roles assigned to user"""
        query = self.db.query(UserRole).filter(UserRole.user_id == user_id)
        
        if not include_expired:
            now = datetime.utcnow()
            query = query.filter(
                (UserRole.valid_from <= now) &
                ((UserRole.valid_until.is_(None)) | (UserRole.valid_until > now))
            )
        
        return query.all()
    
    def get_users_with_role(self, role_id: str) -> List[str]:
        """Get all users with specific role"""
        result = self.db.query(UserRole.user_id).filter(
            UserRole.role_id == role_id
        ).distinct().all()
        
        return [row[0] for row in result]


class AuthorizationContext:
    """Context for authorization decisions"""
    
    def __init__(
        self,
        user_id: str,
        resource_type: ResourceType,
        resource_id: str,
        action: PermissionAction,
        attributes: Optional[Dict[str, Any]] = None
    ):
        self.user_id = user_id
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.action = action
        self.attributes = attributes or {}
        self.timestamp = datetime.utcnow()
    
    def get_attribute(self, key: str, default: Any = None) -> Any:
        """Get attribute from context"""
        return self.attributes.get(key, default)
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Set attribute in context"""
        self.attributes[key] = value


class ConditionEvaluator:
    """Evaluates conditional permissions"""
    
    @staticmethod
    def evaluate(condition: Dict[str, Any], context: AuthorizationContext) -> bool:
        """Evaluate condition against context"""
        condition_type = condition.get("type")
        
        if condition_type == "time_based":
            return ConditionEvaluator._evaluate_time_based(condition, context)
        
        elif condition_type == "resource_owner":
            return ConditionEvaluator._evaluate_resource_owner(condition, context)
        
        elif condition_type == "attribute_match":
            return ConditionEvaluator._evaluate_attribute_match(condition, context)
        
        elif condition_type == "ip_whitelist":
            return ConditionEvaluator._evaluate_ip_whitelist(condition, context)
        
        elif condition_type == "composite":
            return ConditionEvaluator._evaluate_composite(condition, context)
        
        else:
            logger.warning(f"Unknown condition type: {condition_type}")
            return False
    
    @staticmethod
    def _evaluate_time_based(condition: Dict[str, Any], context: AuthorizationContext) -> bool:
        """Evaluate time-based condition"""
        now = context.timestamp
        
        if "start_time" in condition:
            start_time = datetime.fromisoformat(condition["start_time"])
            if now < start_time:
                return False
        
        if "end_time" in condition:
            end_time = datetime.fromisoformat(condition["end_time"])
            if now > end_time:
                return False
        
        if "days_of_week" in condition:
            allowed_days = condition["days_of_week"]  # 0-6 (Monday-Sunday)
            if now.weekday() not in allowed_days:
                return False
        
        if "hours" in condition:
            allowed_hours = condition["hours"]  # 0-23
            if now.hour not in allowed_hours:
                return False
        
        return True
    
    @staticmethod
    def _evaluate_resource_owner(condition: Dict[str, Any], context: AuthorizationContext) -> bool:
        """Check if user is resource owner"""
        owner_attribute = condition.get("owner_attribute", "owner_id")
        resource_owner = context.get_attribute(owner_attribute)
        return resource_owner == context.user_id
    
    @staticmethod
    def _evaluate_attribute_match(condition: Dict[str, Any], context: AuthorizationContext) -> bool:
        """Evaluate attribute matching condition"""
        attribute = condition.get("attribute")
        expected_value = condition.get("value")
        operator = condition.get("operator", "equals")
        
        actual_value = context.get_attribute(attribute)
        
        if operator == "equals":
            return actual_value == expected_value
        elif operator == "not_equals":
            return actual_value != expected_value
        elif operator == "in":
            return actual_value in expected_value
        elif operator == "contains":
            return expected_value in actual_value
        elif operator == "greater_than":
            return actual_value > expected_value
        elif operator == "less_than":
            return actual_value < expected_value
        else:
            return False
    
    @staticmethod
    def _evaluate_ip_whitelist(condition: Dict[str, Any], context: AuthorizationContext) -> bool:
        """Check if IP is in whitelist"""
        allowed_ips = condition.get("allowed_ips", [])
        user_ip = context.get_attribute("ip_address")
        return user_ip in allowed_ips
    
    @staticmethod
    def _evaluate_composite(condition: Dict[str, Any], context: AuthorizationContext) -> bool:
        """Evaluate composite condition (AND/OR)"""
        operator = condition.get("operator", "AND")
        conditions = condition.get("conditions", [])
        
        if operator == "AND":
            return all(ConditionEvaluator.evaluate(c, context) for c in conditions)
        elif operator == "OR":
            return any(ConditionEvaluator.evaluate(c, context) for c in conditions)
        elif operator == "NOT":
            return not ConditionEvaluator.evaluate(conditions[0], context)
        else:
            return False


class PermissionCache:
    """Caches permission checks for performance"""
    
    def __init__(self, redis_client: redis.Redis, ttl: int = 300):
        self.redis = redis_client
        self.ttl = ttl
    
    def get_cached_decision(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str
    ) -> Optional[bool]:
        """Get cached authorization decision"""
        key = self._make_cache_key(user_id, resource_type, resource_id, action)
        value = self.redis.get(key)
        
        if value is not None:
            return value == "1"
        return None
    
    def cache_decision(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        allowed: bool
    ) -> None:
        """Cache authorization decision"""
        key = self._make_cache_key(user_id, resource_type, resource_id, action)
        self.redis.setex(key, self.ttl, "1" if allowed else "0")
    
    def invalidate_user_cache(self, user_id: str) -> None:
        """Invalidate all cached decisions for user"""
        pattern = f"authz:{user_id}:*"
        keys = self.redis.keys(pattern)
        if keys:
            self.redis.delete(*keys)
    
    def invalidate_resource_cache(self, resource_type: str, resource_id: str) -> None:
        """Invalidate all cached decisions for resource"""
        pattern = f"authz:*:{resource_type}:{resource_id}:*"
        keys = self.redis.keys(pattern)
        if keys:
            self.redis.delete(*keys)
    
    def _make_cache_key(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str
    ) -> str:
        """Generate cache key"""
        return f"authz:{user_id}:{resource_type}:{resource_id}:{action}"


class AuthorizationEngine:
    """Main authorization engine with RBAC and ABAC"""
    
    def __init__(
        self,
        db_session: Session,
        role_manager: RoleManager,
        permission_manager: PermissionManager,
        user_role_manager: UserRoleManager,
        cache: Optional[PermissionCache] = None
    ):
        self.db = db_session
        self.role_manager = role_manager
        self.permission_manager = permission_manager
        self.user_role_manager = user_role_manager
        self.cache = cache
    
    def authorize(self, context: AuthorizationContext) -> Tuple[bool, str]:
        """Check if user is authorized for action"""
        
        # Check cache first
        if self.cache:
            cached = self.cache.get_cached_decision(
                context.user_id,
                context.resource_type.value,
                context.resource_id,
                context.action.value
            )
            if cached is not None:
                reason = "Authorized (cached)" if cached else "Denied (cached)"
                self._log_access(context, cached, reason)
                return cached, reason
        
        # Get user roles
        user_roles = self.user_role_manager.get_user_roles(context.user_id)
        if not user_roles:
            reason = "User has no roles"
            self._log_access(context, False, reason)
            return False, reason
        
        # Check each role (including inherited roles)
        for user_role in user_roles:
            # Get role hierarchy
            role_hierarchy = self.role_manager.get_role_hierarchy(user_role.role_id)
            
            # Check permissions for each role in hierarchy
            for role_id in role_hierarchy:
                permissions = self.permission_manager.get_role_permissions(role_id)
                
                for permission in permissions:
                    # Check if permission matches
                    if (permission.resource_type == context.resource_type.value and
                        permission.action == context.action.value):
                        
                        # Check conditions
                        if permission.conditions:
                            condition_met = ConditionEvaluator.evaluate(
                                permission.conditions,
                                context
                            )
                            if not condition_met:
                                continue
                        
                        # Check scope
                        if user_role.scope:
                            scope_met = self._check_scope(user_role.scope, context)
                            if not scope_met:
                                continue
                        
                        # Authorized
                        reason = f"Authorized via role {role_id}"
                        self._log_access(context, True, reason)
                        
                        # Cache decision
                        if self.cache:
                            self.cache.cache_decision(
                                context.user_id,
                                context.resource_type.value,
                                context.resource_id,
                                context.action.value,
                                True
                            )
                        
                        return True, reason
        
        # Check delegated permissions
        delegated = self._check_delegated_permissions(context)
        if delegated[0]:
            self._log_access(context, True, delegated[1])
            return delegated
        
        # Not authorized
        reason = "No matching permissions found"
        self._log_access(context, False, reason)
        
        # Cache decision
        if self.cache:
            self.cache.cache_decision(
                context.user_id,
                context.resource_type.value,
                context.resource_id,
                context.action.value,
                False
            )
        
        return False, reason
    
    def _check_scope(self, scope: Dict[str, Any], context: AuthorizationContext) -> bool:
        """Check if context matches role scope"""
        # Example scope: {"farm_id": "123"} - user can only access specific farm
        for key, value in scope.items():
            context_value = context.get_attribute(key)
            if context_value != value:
                return False
        return True
    
    def _check_delegated_permissions(
        self,
        context: AuthorizationContext
    ) -> Tuple[bool, str]:
        """Check if user has delegated permissions"""
        now = datetime.utcnow()
        
        # Find active delegations
        delegations = self.db.query(PermissionDelegation).filter(
            PermissionDelegation.delegate_id == context.user_id,
            PermissionDelegation.valid_from <= now,
            PermissionDelegation.valid_until > now
        ).all()
        
        for delegation in delegations:
            permission = self.permission_manager.get_permission(delegation.permission_id)
            
            if (permission.resource_type == context.resource_type.value and
                permission.action == context.action.value):
                
                # Check scope
                if delegation.scope:
                    scope_met = self._check_scope(delegation.scope, context)
                    if not scope_met:
                        continue
                
                reason = f"Authorized via delegation from {delegation.delegator_id}"
                return True, reason
        
        return False, "No matching delegations"
    
    def _log_access(self, context: AuthorizationContext, allowed: bool, reason: str) -> None:
        """Log access attempt"""
        import uuid
        
        log = AccessLog(
            id=str(uuid.uuid4()),
            user_id=context.user_id,
            resource_type=context.resource_type.value,
            resource_id=context.resource_id,
            action=context.action.value,
            allowed=allowed,
            reason=reason,
            context=context.attributes,
            timestamp=context.timestamp
        )
        
        self.db.add(log)
        self.db.commit()
    
    def bulk_authorize(
        self,
        user_id: str,
        checks: List[Tuple[ResourceType, str, PermissionAction]]
    ) -> Dict[str, bool]:
        """Perform bulk authorization checks"""
        results = {}
        
        for resource_type, resource_id, action in checks:
            context = AuthorizationContext(user_id, resource_type, resource_id, action)
            allowed, _ = self.authorize(context)
            key = f"{resource_type.value}:{resource_id}:{action.value}"
            results[key] = allowed
        
        return results


class DelegationManager:
    """Manages permission delegation"""
    
    def __init__(self, db_session: Session, auth_engine: AuthorizationEngine):
        self.db = db_session
        self.auth_engine = auth_engine
    
    def delegate_permission(
        self,
        delegator_id: str,
        delegate_id: str,
        permission_id: str,
        valid_until: datetime,
        scope: Optional[Dict[str, Any]] = None,
        can_redelegate: bool = False
    ) -> Optional[str]:
        """Delegate permission to another user"""
        import uuid
        
        # Check if delegator has the permission
        # (In real implementation, verify delegator can delegate)
        
        delegation_id = str(uuid.uuid4())
        delegation = PermissionDelegation(
            id=delegation_id,
            delegator_id=delegator_id,
            delegate_id=delegate_id,
            permission_id=permission_id,
            scope=scope or {},
            valid_until=valid_until,
            can_redelegate=can_redelegate
        )
        
        self.db.add(delegation)
        self.db.commit()
        
        logger.info(f"Delegated permission {permission_id} from {delegator_id} to {delegate_id}")
        return delegation_id
    
    def revoke_delegation(self, delegation_id: str) -> bool:
        """Revoke delegated permission"""
        result = self.db.query(PermissionDelegation).filter(
            PermissionDelegation.id == delegation_id
        ).delete()
        
        self.db.commit()
        
        return result > 0
    
    def get_user_delegations(self, user_id: str, active_only: bool = True) -> List[PermissionDelegation]:
        """Get delegations for user"""
        query = self.db.query(PermissionDelegation).filter(
            PermissionDelegation.delegate_id == user_id
        )
        
        if active_only:
            now = datetime.utcnow()
            query = query.filter(
                PermissionDelegation.valid_from <= now,
                PermissionDelegation.valid_until > now
            )
        
        return query.all()


# Example usage
def example_usage():
    """Demonstrate RBAC system"""
    
    # Setup
    engine = create_engine("postgresql://user:pass@localhost/agropulse")
    Base.metadata.create_all(engine)
    Session_maker = sessionmaker(bind=engine)
    session = Session_maker()
    
    # Initialize managers
    role_mgr = RoleManager(session)
    perm_mgr = PermissionManager(session)
    user_role_mgr = UserRoleManager(session)
    
    # Initialize system
    role_mgr.initialize_system_roles()
    perm_mgr.initialize_standard_permissions()
    
    # Get roles
    admin_role = role_mgr.get_role_by_name("admin")
    user_role = role_mgr.get_role_by_name("user")
    
    # Assign permissions to admin
    farm_create_perm = perm_mgr.get_permission_by_name("farm:create")
    if admin_role and farm_create_perm:
        perm_mgr.assign_permission_to_role(admin_role.id, farm_create_perm.id)
    
    # Assign role to user
    user_id = "user-123"
    if user_role:
        user_role_mgr.assign_role_to_user(
            user_id=user_id,
            role_id=user_role.id,
            assigned_by="system"
        )
    
    # Setup authorization engine
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    cache = PermissionCache(redis_client)
    
    auth_engine = AuthorizationEngine(
        session,
        role_mgr,
        perm_mgr,
        user_role_mgr,
        cache
    )
    
    # Check authorization
    context = AuthorizationContext(
        user_id=user_id,
        resource_type=ResourceType.FARM,
        resource_id="farm-456",
        action=PermissionAction.READ
    )
    
    allowed, reason = auth_engine.authorize(context)
    print(f"Authorization: {allowed}, Reason: {reason}")
    
    # Bulk authorization
    checks = [
        (ResourceType.FARM, "farm-456", PermissionAction.READ),
        (ResourceType.SENSOR, "sensor-789", PermissionAction.CREATE),
        (ResourceType.CROP, "crop-101", PermissionAction.UPDATE),
    ]
    
    results = auth_engine.bulk_authorize(user_id, checks)
    print(f"Bulk results: {results}")
    
    session.close()


if __name__ == "__main__":
    example_usage()
