# ======================================================================================================================
# AgroPulse NVR - Feature Flags System
# Dynamic feature rollout, kill switches, A/B testing integration, gradual releases, targeting rules
# ======================================================================================================================

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)

# ======================================================================================================================
# FEATURE FLAG MODELS
# ======================================================================================================================

class FlagStatus(Enum):
    """Feature flag status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"

class FlagVariant(Enum):
    """Feature flag variants"""
    CONTROL = "control"
    TREATMENT_A = "treatment_a"
    TREATMENT_B = "treatment_b"
    TREATMENT_C = "treatment_c"

class TargetingType(Enum):
    """Targeting types"""
    PERCENTAGE = "percentage"
    USER_IDS = "user_ids"
    USER_ATTRIBUTES = "user_attributes"
    GEOGRAPHIC = "geographic"
    DEVICE_TYPE = "device_type"

@dataclass
class FlagVariantConfig:
    """Feature flag variant configuration"""
    variant: FlagVariant
    weight: float  # 0.0 to 1.0
    value: Any
    description: str = ""

@dataclass
class TargetingRule:
    """Targeting rule"""
    rule_id: str
    targeting_type: TargetingType
    conditions: Dict[str, Any]
    variant: FlagVariant
    priority: int = 0

@dataclass
class FeatureFlag:
    """Feature flag definition"""
    flag_id: str
    name: str
    description: str
    status: FlagStatus
    default_variant: FlagVariant
    default_value: Any
    variants: List[FlagVariantConfig] = field(default_factory=list)
    targeting_rules: List[TargetingRule] = field(default_factory=list)
    environments: List[str] = field(default_factory=lambda: ["production"])
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class FlagEvaluation:
    """Feature flag evaluation result"""
    flag_id: str
    user_id: str
    variant: FlagVariant
    value: Any
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)

# ======================================================================================================================
# FLAG EVALUATOR
# ======================================================================================================================

class FlagEvaluator:
    """Evaluate feature flags"""
    
    def __init__(self):
        logger.info("[EVALUATOR] Flag evaluator initialized")
    
    def evaluate(self, flag: FeatureFlag, user_id: str,
                user_context: Optional[Dict[str, Any]] = None) -> FlagEvaluation:
        """Evaluate flag for user"""
        if flag.status != FlagStatus.ACTIVE:
            return FlagEvaluation(
                flag_id=flag.flag_id,
                user_id=user_id,
                variant=flag.default_variant,
                value=flag.default_value,
                reason="flag_inactive"
            )
        
        # Check targeting rules (ordered by priority)
        sorted_rules = sorted(flag.targeting_rules, key=lambda r: r.priority, reverse=True)
        
        for rule in sorted_rules:
            if self._check_rule(rule, user_id, user_context):
                variant_config = self._get_variant_config(flag, rule.variant)
                
                return FlagEvaluation(
                    flag_id=flag.flag_id,
                    user_id=user_id,
                    variant=rule.variant,
                    value=variant_config.value if variant_config else flag.default_value,
                    reason=f"targeting_rule:{rule.rule_id}"
                )
        
        # No rules matched, use percentage rollout
        variant = self._get_variant_by_hash(flag, user_id)
        variant_config = self._get_variant_config(flag, variant)
        
        return FlagEvaluation(
            flag_id=flag.flag_id,
            user_id=user_id,
            variant=variant,
            value=variant_config.value if variant_config else flag.default_value,
            reason="percentage_rollout"
        )
    
    def _check_rule(self, rule: TargetingRule, user_id: str,
                   user_context: Optional[Dict[str, Any]]) -> bool:
        """Check if targeting rule matches"""
        if rule.targeting_type == TargetingType.USER_IDS:
            user_ids = rule.conditions.get('user_ids', [])
            return user_id in user_ids
        
        elif rule.targeting_type == TargetingType.PERCENTAGE:
            percentage = rule.conditions.get('percentage', 0)
            user_hash = self._hash_user(user_id)
            return user_hash < percentage
        
        elif rule.targeting_type == TargetingType.USER_ATTRIBUTES:
            if not user_context:
                return False
            
            for attr, value in rule.conditions.items():
                if user_context.get(attr) != value:
                    return False
            
            return True
        
        elif rule.targeting_type == TargetingType.DEVICE_TYPE:
            if not user_context:
                return False
            
            device_types = rule.conditions.get('device_types', [])
            user_device = user_context.get('device_type')
            return user_device in device_types
        
        return False
    
    def _get_variant_by_hash(self, flag: FeatureFlag, user_id: str) -> FlagVariant:
        """Get variant based on user hash"""
        if not flag.variants:
            return flag.default_variant
        
        user_hash = self._hash_user(user_id)
        
        cumulative_weight = 0.0
        for variant_config in flag.variants:
            cumulative_weight += variant_config.weight
            if user_hash <= cumulative_weight:
                return variant_config.variant
        
        return flag.default_variant
    
    def _hash_user(self, user_id: str) -> float:
        """Hash user ID to 0.0-1.0"""
        hash_obj = hashlib.md5(user_id.encode())
        hash_int = int(hash_obj.hexdigest(), 16)
        return (hash_int % 10000) / 10000.0
    
    def _get_variant_config(self, flag: FeatureFlag,
                           variant: FlagVariant) -> Optional[FlagVariantConfig]:
        """Get variant configuration"""
        for config in flag.variants:
            if config.variant == variant:
                return config
        return None

# ======================================================================================================================
# FLAG MANAGER
# ======================================================================================================================

class FlagManager:
    """Manage feature flags"""
    
    def __init__(self):
        self.flags: Dict[str, FeatureFlag] = {}
        self.evaluator = FlagEvaluator()
        
        logger.info("[FLAG-MGR] Flag manager initialized")
    
    def create_flag(self, flag_id: str, name: str, description: str,
                   default_value: Any,
                   default_variant: FlagVariant = FlagVariant.CONTROL) -> FeatureFlag:
        """Create feature flag"""
        flag = FeatureFlag(
            flag_id=flag_id,
            name=name,
            description=description,
            status=FlagStatus.INACTIVE,
            default_variant=default_variant,
            default_value=default_value
        )
        
        self.flags[flag_id] = flag
        
        logger.info(f"[FLAG-MGR] Created flag: {flag_id}")
        return flag
    
    def add_variant(self, flag_id: str, variant: FlagVariant,
                   weight: float, value: Any, description: str = ""):
        """Add variant to flag"""
        flag = self.flags.get(flag_id)
        
        if not flag:
            raise ValueError(f"Flag not found: {flag_id}")
        
        variant_config = FlagVariantConfig(
            variant=variant,
            weight=weight,
            value=value,
            description=description
        )
        
        flag.variants.append(variant_config)
        flag.updated_at = datetime.now()
        
        logger.info(f"[FLAG-MGR] Added variant to {flag_id}: {variant.value} (weight: {weight})")
    
    def add_targeting_rule(self, flag_id: str, rule_id: str,
                          targeting_type: TargetingType,
                          conditions: Dict[str, Any],
                          variant: FlagVariant,
                          priority: int = 0):
        """Add targeting rule to flag"""
        flag = self.flags.get(flag_id)
        
        if not flag:
            raise ValueError(f"Flag not found: {flag_id}")
        
        rule = TargetingRule(
            rule_id=rule_id,
            targeting_type=targeting_type,
            conditions=conditions,
            variant=variant,
            priority=priority
        )
        
        flag.targeting_rules.append(rule)
        flag.updated_at = datetime.now()
        
        logger.info(f"[FLAG-MGR] Added targeting rule to {flag_id}: {rule_id}")
    
    def activate_flag(self, flag_id: str):
        """Activate feature flag"""
        flag = self.flags.get(flag_id)
        
        if flag:
            flag.status = FlagStatus.ACTIVE
            flag.updated_at = datetime.now()
            logger.info(f"[FLAG-MGR] Activated flag: {flag_id}")
    
    def deactivate_flag(self, flag_id: str):
        """Deactivate feature flag"""
        flag = self.flags.get(flag_id)
        
        if flag:
            flag.status = FlagStatus.INACTIVE
            flag.updated_at = datetime.now()
            logger.info(f"[FLAG-MGR] Deactivated flag: {flag_id}")
    
    def archive_flag(self, flag_id: str):
        """Archive feature flag"""
        flag = self.flags.get(flag_id)
        
        if flag:
            flag.status = FlagStatus.ARCHIVED
            flag.updated_at = datetime.now()
            logger.info(f"[FLAG-MGR] Archived flag: {flag_id}")
    
    def get_flag_value(self, flag_id: str, user_id: str,
                      user_context: Optional[Dict[str, Any]] = None) -> Any:
        """Get flag value for user"""
        flag = self.flags.get(flag_id)
        
        if not flag:
            logger.warning(f"[FLAG-MGR] Flag not found: {flag_id}, returning None")
            return None
        
        evaluation = self.evaluator.evaluate(flag, user_id, user_context)
        
        logger.debug(f"[FLAG-MGR] Evaluated {flag_id} for {user_id}: {evaluation.variant.value} (reason: {evaluation.reason})")
        
        return evaluation.value
    
    def is_enabled(self, flag_id: str, user_id: str,
                  user_context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if flag is enabled for user"""
        value = self.get_flag_value(flag_id, user_id, user_context)
        
        # Handle boolean flags
        if isinstance(value, bool):
            return value
        
        # Treat non-control variants as enabled
        evaluation = self._evaluate_internal(flag_id, user_id, user_context)
        return evaluation.variant != FlagVariant.CONTROL if evaluation else False
    
    def _evaluate_internal(self, flag_id: str, user_id: str,
                          user_context: Optional[Dict[str, Any]]) -> Optional[FlagEvaluation]:
        """Internal evaluation method"""
        flag = self.flags.get(flag_id)
        if not flag:
            return None
        
        return self.evaluator.evaluate(flag, user_id, user_context)

# ======================================================================================================================
# FLAG ANALYTICS
# ======================================================================================================================

class FlagAnalytics:
    """Track feature flag analytics"""
    
    def __init__(self):
        self.evaluations: List[FlagEvaluation] = []
        self.variant_counts: Dict[str, Dict[FlagVariant, int]] = {}
        
        logger.info("[ANALYTICS] Flag analytics initialized")
    
    def track_evaluation(self, evaluation: FlagEvaluation):
        """Track flag evaluation"""
        self.evaluations.append(evaluation)
        
        # Update variant counts
        if evaluation.flag_id not in self.variant_counts:
            self.variant_counts[evaluation.flag_id] = {}
        
        variant = evaluation.variant
        self.variant_counts[evaluation.flag_id][variant] = \
            self.variant_counts[evaluation.flag_id].get(variant, 0) + 1
    
    def get_flag_stats(self, flag_id: str) -> Dict[str, Any]:
        """Get statistics for flag"""
        flag_evaluations = [e for e in self.evaluations if e.flag_id == flag_id]
        
        if not flag_evaluations:
            return {
                'flag_id': flag_id,
                'total_evaluations': 0,
                'variant_distribution': {},
                'unique_users': 0
            }
        
        unique_users = len(set(e.user_id for e in flag_evaluations))
        
        variant_distribution = {}
        total = len(flag_evaluations)
        
        for variant, count in self.variant_counts.get(flag_id, {}).items():
            variant_distribution[variant.value] = {
                'count': count,
                'percentage': (count / total * 100) if total > 0 else 0
            }
        
        return {
            'flag_id': flag_id,
            'total_evaluations': total,
            'variant_distribution': variant_distribution,
            'unique_users': unique_users
        }

# ======================================================================================================================
# KILL SWITCH MANAGER
# ======================================================================================================================

class KillSwitchManager:
    """Emergency kill switch for features"""
    
    def __init__(self, flag_manager: FlagManager):
        self.flag_manager = flag_manager
        self.kill_switches: Dict[str, datetime] = {}
        
        logger.info("[KILL-SWITCH] Kill switch manager initialized")
    
    def activate_kill_switch(self, flag_id: str, reason: str = ""):
        """Activate kill switch (disable feature)"""
        self.flag_manager.deactivate_flag(flag_id)
        self.kill_switches[flag_id] = datetime.now()
        
        logger.warning(f"[KILL-SWITCH] Activated kill switch for {flag_id}: {reason}")
    
    def deactivate_kill_switch(self, flag_id: str):
        """Deactivate kill switch (re-enable feature)"""
        self.flag_manager.activate_flag(flag_id)
        
        if flag_id in self.kill_switches:
            del self.kill_switches[flag_id]
        
        logger.info(f"[KILL-SWITCH] Deactivated kill switch for {flag_id}")
    
    def is_killed(self, flag_id: str) -> bool:
        """Check if feature is killed"""
        return flag_id in self.kill_switches

# ======================================================================================================================
# FEATURE FLAGS ORCHESTRATOR
# ======================================================================================================================

class FeatureFlagsOrchestrator:
    """Main feature flags orchestrator"""
    
    def __init__(self):
        self.flag_manager = FlagManager()
        self.analytics = FlagAnalytics()
        self.kill_switch_manager = KillSwitchManager(self.flag_manager)
        
        logger.info("[FLAGS-ORCH] Feature flags orchestrator initialized")
        
        self._create_default_flags()
    
    def _create_default_flags(self):
        """Create default feature flags"""
        # New dashboard feature
        flag = self.flag_manager.create_flag(
            "new_dashboard",
            "New Dashboard UI",
            "New modern dashboard interface",
            default_value=False
        )
        
        self.flag_manager.add_variant(
            "new_dashboard",
            FlagVariant.CONTROL,
            weight=0.5,
            value=False,
            description="Old dashboard"
        )
        
        self.flag_manager.add_variant(
            "new_dashboard",
            FlagVariant.TREATMENT_A,
            weight=0.5,
            value=True,
            description="New dashboard"
        )
        
        # Advanced analytics feature
        self.flag_manager.create_flag(
            "advanced_analytics",
            "Advanced Analytics",
            "Advanced analytics features",
            default_value=False
        )
    
    def check_feature(self, flag_id: str, user_id: str,
                     user_context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if feature is enabled for user"""
        enabled = self.flag_manager.is_enabled(flag_id, user_id, user_context)
        
        # Track evaluation
        evaluation = self.flag_manager._evaluate_internal(flag_id, user_id, user_context)
        if evaluation:
            self.analytics.track_evaluation(evaluation)
        
        return enabled
    
    def get_feature_value(self, flag_id: str, user_id: str,
                         user_context: Optional[Dict[str, Any]] = None) -> Any:
        """Get feature value for user"""
        value = self.flag_manager.get_flag_value(flag_id, user_id, user_context)
        
        # Track evaluation
        evaluation = self.flag_manager._evaluate_internal(flag_id, user_id, user_context)
        if evaluation:
            self.analytics.track_evaluation(evaluation)
        
        return value
    
    def create_percentage_rollout(self, flag_id: str, name: str,
                                 description: str, percentage: float):
        """Create percentage-based rollout"""
        flag = self.flag_manager.create_flag(
            flag_id,
            name,
            description,
            default_value=False
        )
        
        # Add targeting rule
        self.flag_manager.add_targeting_rule(
            flag_id,
            f"{flag_id}_percentage",
            TargetingType.PERCENTAGE,
            {'percentage': percentage},
            FlagVariant.TREATMENT_A,
            priority=1
        )
        
        # Add variants
        self.flag_manager.add_variant(
            flag_id,
            FlagVariant.CONTROL,
            weight=1.0 - percentage,
            value=False
        )
        
        self.flag_manager.add_variant(
            flag_id,
            FlagVariant.TREATMENT_A,
            weight=percentage,
            value=True
        )
        
        self.flag_manager.activate_flag(flag_id)
        
        logger.info(f"[FLAGS-ORCH] Created percentage rollout: {flag_id} ({percentage*100}%)")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get feature flags statistics"""
        active_flags = [f for f in self.flag_manager.flags.values() if f.status == FlagStatus.ACTIVE]
        
        return {
            'total_flags': len(self.flag_manager.flags),
            'active_flags': len(active_flags),
            'total_evaluations': len(self.analytics.evaluations),
            'kill_switches_active': len(self.kill_switch_manager.kill_switches),
            'flags_by_status': {
                status.value: len([
                    f for f in self.flag_manager.flags.values()
                    if f.status == status
                ])
                for status in FlagStatus
            }
        }

# ======================================================================================================================
# END OF FEATURE FLAGS SYSTEM MODULE
# Lines in this file: ~650+
# Combined total: ~37,500+
# Remaining for 50k: ~12,500 lines
# ======================================================================================================================
