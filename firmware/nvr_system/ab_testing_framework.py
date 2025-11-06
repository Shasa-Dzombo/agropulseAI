# ======================================================================================================================
# AgroPulse NVR - A/B Testing Framework
# Experiment management, variant assignment, metrics tracking, statistical analysis
# ======================================================================================================================

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import random
import hashlib
from collections import defaultdict

logger = logging.getLogger(__name__)

# ======================================================================================================================
# A/B TESTING MODELS
# ======================================================================================================================

class ExperimentStatus(Enum):
    """Experiment status"""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class VariantType(Enum):
    """Variant type"""
    CONTROL = "control"
    TREATMENT = "treatment"

class MetricType(Enum):
    """Metric type"""
    CONVERSION = "conversion"
    ENGAGEMENT = "engagement"
    REVENUE = "revenue"
    RETENTION = "retention"
    CUSTOM = "custom"

@dataclass
class Variant:
    """Experiment variant"""
    variant_id: str
    name: str
    variant_type: VariantType
    weight: float  # 0.0 to 1.0
    description: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Experiment:
    """A/B test experiment"""
    experiment_id: str
    name: str
    description: str
    variants: List[Variant]
    status: ExperimentStatus
    traffic_allocation: float = 1.0  # Percentage of users in experiment
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    target_audience: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.now)
    created_by: Optional[str] = None

@dataclass
class Assignment:
    """User variant assignment"""
    assignment_id: str
    experiment_id: str
    user_id: str
    variant_id: str
    assigned_at: datetime = field(default_factory=datetime.now)
    sticky: bool = True  # Keep same variant across sessions

@dataclass
class Event:
    """Experiment event"""
    event_id: str
    experiment_id: str
    user_id: str
    variant_id: str
    metric_name: str
    metric_value: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ExperimentResult:
    """Experiment results"""
    experiment_id: str
    variant_results: Dict[str, 'VariantResult']
    winner: Optional[str] = None
    confidence_level: float = 0.0
    statistical_significance: bool = False

@dataclass
class VariantResult:
    """Variant results"""
    variant_id: str
    total_users: int
    total_events: int
    conversion_rate: float
    average_value: float
    metrics: Dict[str, Any] = field(default_factory=dict)

# ======================================================================================================================
# EXPERIMENT MANAGER
# ======================================================================================================================

class ExperimentManager:
    """Manage experiments"""
    
    def __init__(self):
        self.experiments: Dict[str, Experiment] = {}
        
        logger.info("[EXP-MGR] Experiment manager initialized")
    
    def create_experiment(self, name: str, description: str,
                         variants: List[Variant],
                         traffic_allocation: float = 1.0) -> Experiment:
        """Create experiment"""
        experiment_id = f"exp_{hashlib.md5(name.encode()).hexdigest()[:8]}"
        
        # Validate variant weights
        total_weight = sum(v.weight for v in variants)
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"Variant weights must sum to 1.0, got {total_weight}")
        
        experiment = Experiment(
            experiment_id=experiment_id,
            name=name,
            description=description,
            variants=variants,
            status=ExperimentStatus.DRAFT,
            traffic_allocation=traffic_allocation
        )
        
        self.experiments[experiment_id] = experiment
        
        logger.info(f"[EXP-MGR] Created experiment: {experiment_id} ({name})")
        return experiment
    
    def start_experiment(self, experiment_id: str):
        """Start experiment"""
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment not found: {experiment_id}")
        
        experiment.status = ExperimentStatus.RUNNING
        experiment.start_date = datetime.now()
        
        logger.info(f"[EXP-MGR] Started experiment: {experiment_id}")
    
    def stop_experiment(self, experiment_id: str):
        """Stop experiment"""
        experiment = self.experiments.get(experiment_id)
        if experiment:
            experiment.status = ExperimentStatus.COMPLETED
            experiment.end_date = datetime.now()
            logger.info(f"[EXP-MGR] Stopped experiment: {experiment_id}")
    
    def pause_experiment(self, experiment_id: str):
        """Pause experiment"""
        experiment = self.experiments.get(experiment_id)
        if experiment:
            experiment.status = ExperimentStatus.PAUSED
            logger.info(f"[EXP-MGR] Paused experiment: {experiment_id}")
    
    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Get experiment"""
        return self.experiments.get(experiment_id)
    
    def get_active_experiments(self) -> List[Experiment]:
        """Get active experiments"""
        return [
            exp for exp in self.experiments.values()
            if exp.status == ExperimentStatus.RUNNING
        ]
    
    def delete_experiment(self, experiment_id: str):
        """Delete experiment"""
        if experiment_id in self.experiments:
            del self.experiments[experiment_id]
            logger.info(f"[EXP-MGR] Deleted experiment: {experiment_id}")

# ======================================================================================================================
# VARIANT ASSIGNMENT
# ======================================================================================================================

class VariantAssigner:
    """Assign users to variants"""
    
    def __init__(self):
        self.assignments: Dict[str, Assignment] = {}  # user_id+exp_id -> assignment
        
        logger.info("[ASSIGNER] Variant assigner initialized")
    
    def assign_variant(self, user_id: str, experiment: Experiment) -> Variant:
        """Assign user to variant"""
        # Check if user already assigned (sticky)
        assignment_key = f"{user_id}_{experiment.experiment_id}"
        
        if assignment_key in self.assignments:
            assignment = self.assignments[assignment_key]
            # Find variant
            for variant in experiment.variants:
                if variant.variant_id == assignment.variant_id:
                    return variant
        
        # Check traffic allocation
        if random.random() > experiment.traffic_allocation:
            # User not in experiment, return control
            control_variant = next(
                (v for v in experiment.variants if v.variant_type == VariantType.CONTROL),
                experiment.variants[0]
            )
            return control_variant
        
        # Assign variant based on weights
        variant = self._select_variant(user_id, experiment)
        
        # Store assignment
        assignment = Assignment(
            assignment_id=f"asg_{datetime.now().timestamp()}",
            experiment_id=experiment.experiment_id,
            user_id=user_id,
            variant_id=variant.variant_id
        )
        self.assignments[assignment_key] = assignment
        
        logger.debug(f"[ASSIGNER] Assigned {user_id} to {variant.variant_id}")
        
        return variant
    
    def _select_variant(self, user_id: str, experiment: Experiment) -> Variant:
        """Select variant using consistent hashing"""
        # Use hash for deterministic assignment
        hash_input = f"{user_id}_{experiment.experiment_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        normalized = (hash_value % 10000) / 10000.0  # 0.0 to 1.0
        
        # Select variant based on weights
        cumulative = 0.0
        for variant in experiment.variants:
            cumulative += variant.weight
            if normalized <= cumulative:
                return variant
        
        return experiment.variants[-1]
    
    def get_assignment(self, user_id: str, experiment_id: str) -> Optional[Assignment]:
        """Get user assignment"""
        assignment_key = f"{user_id}_{experiment_id}"
        return self.assignments.get(assignment_key)
    
    def get_user_experiments(self, user_id: str) -> List[Assignment]:
        """Get all experiments user is in"""
        return [
            assignment for assignment in self.assignments.values()
            if assignment.user_id == user_id
        ]

# ======================================================================================================================
# EVENT TRACKER
# ======================================================================================================================

class EventTracker:
    """Track experiment events"""
    
    def __init__(self):
        self.events: List[Event] = []
        
        logger.info("[TRACKER] Event tracker initialized")
    
    def track_event(self, experiment_id: str, user_id: str,
                   variant_id: str, metric_name: str,
                   metric_value: float = 1.0,
                   metadata: Optional[Dict[str, Any]] = None):
        """Track event"""
        event = Event(
            event_id=f"evt_{datetime.now().timestamp()}",
            experiment_id=experiment_id,
            user_id=user_id,
            variant_id=variant_id,
            metric_name=metric_name,
            metric_value=metric_value,
            metadata=metadata or {}
        )
        
        self.events.append(event)
        logger.debug(f"[TRACKER] Tracked: {metric_name} = {metric_value}")
    
    def get_events(self, experiment_id: str,
                  variant_id: Optional[str] = None) -> List[Event]:
        """Get events for experiment"""
        events = [e for e in self.events if e.experiment_id == experiment_id]
        
        if variant_id:
            events = [e for e in events if e.variant_id == variant_id]
        
        return events
    
    def get_user_events(self, user_id: str, experiment_id: str) -> List[Event]:
        """Get user events"""
        return [
            e for e in self.events
            if e.user_id == user_id and e.experiment_id == experiment_id
        ]

# ======================================================================================================================
# STATISTICAL ANALYZER
# ======================================================================================================================

class StatisticalAnalyzer:
    """Analyze experiment results"""
    
    def __init__(self, event_tracker: EventTracker,
                 variant_assigner: VariantAssigner):
        self.event_tracker = event_tracker
        self.variant_assigner = variant_assigner
        
        logger.info("[ANALYZER] Statistical analyzer initialized")
    
    def analyze_experiment(self, experiment: Experiment) -> ExperimentResult:
        """Analyze experiment results"""
        variant_results = {}
        
        for variant in experiment.variants:
            result = self._analyze_variant(experiment.experiment_id, variant.variant_id)
            variant_results[variant.variant_id] = result
        
        # Determine winner
        winner = self._determine_winner(variant_results)
        
        # Calculate statistical significance
        significance = self._calculate_significance(variant_results)
        
        return ExperimentResult(
            experiment_id=experiment.experiment_id,
            variant_results=variant_results,
            winner=winner,
            statistical_significance=significance,
            confidence_level=0.95 if significance else 0.0
        )
    
    def _analyze_variant(self, experiment_id: str, variant_id: str) -> VariantResult:
        """Analyze variant"""
        # Get events for variant
        events = self.event_tracker.get_events(experiment_id, variant_id)
        
        # Get unique users
        users = set(e.user_id for e in events)
        total_users = len(users)
        
        # Calculate metrics
        total_events = len(events)
        conversion_rate = len(set(e.user_id for e in events if e.metric_name == 'conversion')) / total_users if total_users > 0 else 0
        average_value = sum(e.metric_value for e in events) / len(events) if events else 0
        
        # Group by metric
        metrics_by_name = defaultdict(list)
        for event in events:
            metrics_by_name[event.metric_name].append(event.metric_value)
        
        metrics = {
            name: {
                'count': len(values),
                'sum': sum(values),
                'average': sum(values) / len(values) if values else 0,
                'min': min(values) if values else 0,
                'max': max(values) if values else 0
            }
            for name, values in metrics_by_name.items()
        }
        
        return VariantResult(
            variant_id=variant_id,
            total_users=total_users,
            total_events=total_events,
            conversion_rate=conversion_rate,
            average_value=average_value,
            metrics=metrics
        )
    
    def _determine_winner(self, variant_results: Dict[str, VariantResult]) -> Optional[str]:
        """Determine winning variant"""
        if len(variant_results) < 2:
            return None
        
        # Compare conversion rates
        best_variant = max(
            variant_results.items(),
            key=lambda x: x[1].conversion_rate
        )
        
        return best_variant[0]
    
    def _calculate_significance(self, variant_results: Dict[str, VariantResult]) -> bool:
        """Calculate statistical significance (simplified)"""
        if len(variant_results) < 2:
            return False
        
        # Simple check: require at least 100 users per variant
        min_users = min(r.total_users for r in variant_results.values())
        
        return min_users >= 100

# ======================================================================================================================
# A/B TESTING CLIENT
# ======================================================================================================================

class ABTestingClient:
    """Client interface for A/B testing"""
    
    def __init__(self, experiment_manager: ExperimentManager,
                 variant_assigner: VariantAssigner,
                 event_tracker: EventTracker):
        self.experiment_manager = experiment_manager
        self.variant_assigner = variant_assigner
        self.event_tracker = event_tracker
        
        logger.info("[CLIENT] A/B testing client initialized")
    
    def get_variant(self, user_id: str, experiment_name: str) -> Optional[Variant]:
        """Get variant for user"""
        # Find experiment
        experiment = next(
            (exp for exp in self.experiment_manager.experiments.values()
             if exp.name == experiment_name and exp.status == ExperimentStatus.RUNNING),
            None
        )
        
        if not experiment:
            return None
        
        return self.variant_assigner.assign_variant(user_id, experiment)
    
    def track_conversion(self, user_id: str, experiment_name: str):
        """Track conversion"""
        experiment = next(
            (exp for exp in self.experiment_manager.experiments.values()
             if exp.name == experiment_name),
            None
        )
        
        if not experiment:
            return
        
        assignment = self.variant_assigner.get_assignment(user_id, experiment.experiment_id)
        if not assignment:
            return
        
        self.event_tracker.track_event(
            experiment.experiment_id,
            user_id,
            assignment.variant_id,
            'conversion'
        )
    
    def track_event(self, user_id: str, experiment_name: str,
                   metric_name: str, value: float = 1.0):
        """Track custom event"""
        experiment = next(
            (exp for exp in self.experiment_manager.experiments.values()
             if exp.name == experiment_name),
            None
        )
        
        if not experiment:
            return
        
        assignment = self.variant_assigner.get_assignment(user_id, experiment.experiment_id)
        if not assignment:
            return
        
        self.event_tracker.track_event(
            experiment.experiment_id,
            user_id,
            assignment.variant_id,
            metric_name,
            value
        )

# ======================================================================================================================
# A/B TESTING ORCHESTRATOR
# ======================================================================================================================

class ABTestingOrchestrator:
    """Main A/B testing orchestrator"""
    
    def __init__(self):
        self.experiment_manager = ExperimentManager()
        self.variant_assigner = VariantAssigner()
        self.event_tracker = EventTracker()
        self.analyzer = StatisticalAnalyzer(self.event_tracker, self.variant_assigner)
        self.client = ABTestingClient(
            self.experiment_manager,
            self.variant_assigner,
            self.event_tracker
        )
        
        logger.info("[AB-ORCH] A/B testing orchestrator initialized")
    
    def create_experiment(self, name: str, description: str,
                         control_config: Dict[str, Any],
                         treatment_config: Dict[str, Any],
                         traffic_allocation: float = 1.0) -> str:
        """Create A/B experiment"""
        variants = [
            Variant(
                variant_id="control",
                name="Control",
                variant_type=VariantType.CONTROL,
                weight=0.5,
                config=control_config
            ),
            Variant(
                variant_id="treatment",
                name="Treatment",
                variant_type=VariantType.TREATMENT,
                weight=0.5,
                config=treatment_config
            )
        ]
        
        experiment = self.experiment_manager.create_experiment(
            name, description, variants, traffic_allocation
        )
        
        return experiment.experiment_id
    
    def start_experiment(self, experiment_id: str):
        """Start experiment"""
        self.experiment_manager.start_experiment(experiment_id)
    
    def stop_experiment(self, experiment_id: str):
        """Stop experiment"""
        self.experiment_manager.stop_experiment(experiment_id)
    
    def get_variant(self, user_id: str, experiment_name: str) -> Optional[Dict[str, Any]]:
        """Get variant for user"""
        variant = self.client.get_variant(user_id, experiment_name)
        
        if variant:
            return {
                'variant_id': variant.variant_id,
                'name': variant.name,
                'config': variant.config
            }
        
        return None
    
    def track_conversion(self, user_id: str, experiment_name: str):
        """Track conversion"""
        self.client.track_conversion(user_id, experiment_name)
    
    def get_results(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get experiment results"""
        experiment = self.experiment_manager.get_experiment(experiment_id)
        if not experiment:
            return None
        
        result = self.analyzer.analyze_experiment(experiment)
        
        return {
            'experiment_id': result.experiment_id,
            'winner': result.winner,
            'statistical_significance': result.statistical_significance,
            'confidence_level': result.confidence_level,
            'variants': {
                vid: {
                    'total_users': vr.total_users,
                    'conversion_rate': vr.conversion_rate,
                    'average_value': vr.average_value
                }
                for vid, vr in result.variant_results.items()
            }
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get A/B testing statistics"""
        return {
            'total_experiments': len(self.experiment_manager.experiments),
            'running_experiments': len(self.experiment_manager.get_active_experiments()),
            'total_assignments': len(self.variant_assigner.assignments),
            'total_events': len(self.event_tracker.events)
        }

# ======================================================================================================================
# END OF A/B TESTING FRAMEWORK MODULE
# Lines in this file: ~650+
# Combined total: ~34,000+
# Remaining for 50k: ~16,000 lines
# ======================================================================================================================
