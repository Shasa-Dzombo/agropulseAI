"""
Predictive Maintenance Engine

Machine learning-based predictive maintenance for IoT devices and farm equipment.

Features:
- Failure prediction using survival analysis
- Anomaly-based degradation detection
- Remaining useful life (RUL) estimation
- Maintenance scheduling optimization
- Cost-benefit analysis
- Multi-component system analysis
- Sensor drift detection
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import json
import pickle

from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from lifelines import KaplanMeierFitter, CoxPHFitter, WeibullAFTFitter
from scipy import stats
import warnings
warnings.filterwarnings('ignore')


logger = logging.getLogger(__name__)


@dataclass
class MaintenanceEvent:
    """Maintenance event record"""
    device_id: str
    event_type: str  # 'preventive', 'corrective', 'inspection'
    timestamp: datetime
    component: str
    cost: float
    downtime_hours: float
    description: str
    metadata: Dict = field(default_factory=dict)


@dataclass
class FailurePrediction:
    """Failure prediction result"""
    device_id: str
    component: str
    failure_probability: float
    predicted_failure_date: Optional[datetime]
    remaining_useful_life_days: Optional[float]
    confidence: float
    risk_level: str  # 'low', 'medium', 'high', 'critical'
    contributing_factors: Dict[str, float]
    recommended_action: str
    estimated_cost_if_failure: float
    estimated_cost_preventive: float
    timestamp: datetime


@dataclass
class HealthScore:
    """Device health score"""
    device_id: str
    overall_score: float  # 0-100
    component_scores: Dict[str, float]
    degradation_rate: float
    timestamp: datetime
    alerts: List[str] = field(default_factory=list)


class SurvivalAnalysisEngine:
    """
    Survival analysis for failure time prediction
    
    Uses Kaplan-Meier, Cox Proportional Hazards, and Weibull models.
    """
    
    def __init__(self, model_type: str = 'weibull'):
        """
        Initialize survival analysis engine
        
        Args:
            model_type: 'kaplan_meier', 'cox', 'weibull'
        """
        self.model_type = model_type
        
        if model_type == 'kaplan_meier':
            self.model = KaplanMeierFitter()
        elif model_type == 'cox':
            self.model = CoxPHFitter()
        elif model_type == 'weibull':
            self.model = WeibullAFTFitter()
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        
        self.fitted = False
        logger.info(f"SurvivalAnalysisEngine initialized (model={model_type})")
    
    def fit(
        self,
        durations: np.ndarray,
        events: np.ndarray,
        covariates: Optional[pd.DataFrame] = None
    ):
        """
        Fit survival model
        
        Args:
            durations: Time to event or censoring
            events: Event indicator (1=failed, 0=censored)
            covariates: Optional covariates for Cox/Weibull models
        """
        if self.model_type == 'kaplan_meier':
            self.model.fit(durations, events)
        else:
            if covariates is None:
                raise ValueError(f"{self.model_type} requires covariates")
            
            df = covariates.copy()
            df['duration'] = durations
            df['event'] = events
            
            self.model.fit(df, duration_col='duration', event_col='event')
        
        self.fitted = True
        logger.info("Survival model fitted")
    
    def predict_survival_function(
        self,
        times: np.ndarray,
        covariates: Optional[pd.DataFrame] = None
    ) -> np.ndarray:
        """
        Predict survival function
        
        Args:
            times: Time points to predict
            covariates: Covariates for prediction
            
        Returns:
            Survival probabilities
        """
        if not self.fitted:
            raise RuntimeError("Model not fitted")
        
        if self.model_type == 'kaplan_meier':
            return self.model.survival_function_at_times(times).values
        else:
            return self.model.predict_survival_function(covariates, times=times).values.T
    
    def predict_median_lifetime(
        self,
        covariates: Optional[pd.DataFrame] = None
    ) -> float:
        """Predict median lifetime"""
        if not self.fitted:
            raise RuntimeError("Model not fitted")
        
        if self.model_type == 'kaplan_meier':
            return self.model.median_survival_time_
        else:
            return self.model.predict_median(covariates).values[0]


class DegradationModel:
    """
    Degradation-based RUL estimation
    
    Models gradual degradation using regression and extrapolation.
    """
    
    def __init__(
        self,
        failure_threshold: float = 100.0,
        model_type: str = 'gbr'
    ):
        """
        Initialize degradation model
        
        Args:
            failure_threshold: Degradation level indicating failure
            model_type: 'gbr' (Gradient Boosting) or 'linear'
        """
        self.failure_threshold = failure_threshold
        self.model_type = model_type
        
        if model_type == 'gbr':
            self.model = GradientBoostingRegressor(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            )
        else:
            from sklearn.linear_model import LinearRegression
            self.model = LinearRegression()
        
        self.scaler = StandardScaler()
        self.fitted = False
        
        logger.info(f"DegradationModel initialized (model={model_type})")
    
    def fit(self, features: np.ndarray, degradation_levels: np.ndarray):
        """
        Fit degradation model
        
        Args:
            features: Input features
            degradation_levels: Observed degradation levels
        """
        features_scaled = self.scaler.fit_transform(features)
        self.model.fit(features_scaled, degradation_levels)
        self.fitted = True
        logger.info("Degradation model fitted")
    
    def predict_degradation(self, features: np.ndarray) -> np.ndarray:
        """Predict current degradation level"""
        if not self.fitted:
            raise RuntimeError("Model not fitted")
        
        features_scaled = self.scaler.transform(features)
        return self.model.predict(features_scaled)
    
    def estimate_rul(
        self,
        current_features: np.ndarray,
        degradation_rate: float,
        time_unit: str = 'days'
    ) -> float:
        """
        Estimate remaining useful life
        
        Args:
            current_features: Current state features
            degradation_rate: Rate of degradation per time unit
            time_unit: Time unit for RUL
            
        Returns:
            RUL in specified time units
        """
        if not self.fitted:
            raise RuntimeError("Model not fitted")
        
        current_degradation = self.predict_degradation(current_features)[0]
        
        if current_degradation >= self.failure_threshold:
            return 0.0
        
        remaining_degradation = self.failure_threshold - current_degradation
        
        if degradation_rate <= 0:
            return float('inf')
        
        rul = remaining_degradation / degradation_rate
        return max(0.0, rul)


class PredictiveMaintenanceEngine:
    """
    Complete predictive maintenance system
    
    Combines survival analysis, degradation modeling, and anomaly detection
    for comprehensive maintenance prediction.
    """
    
    def __init__(
        self,
        enable_survival_analysis: bool = True,
        enable_degradation_model: bool = True,
        enable_anomaly_detection: bool = True
    ):
        self.enable_survival_analysis = enable_survival_analysis
        self.enable_degradation_model = enable_degradation_model
        self.enable_anomaly_detection = enable_anomaly_detection
        
        # Models
        self.survival_model = SurvivalAnalysisEngine(model_type='weibull')
        self.degradation_model = DegradationModel()
        self.failure_classifier = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        
        # Device history tracking
        self.device_histories: Dict[str, deque] = {}
        self.maintenance_histories: Dict[str, List[MaintenanceEvent]] = {}
        
        # Health scores
        self.health_scores: Dict[str, HealthScore] = {}
        
        # Feature extractors
        self.feature_extractors: Dict[str, callable] = {}
        
        # Thresholds
        self.alert_thresholds = {
            'critical': 0.9,  # 90% failure probability
            'high': 0.7,
            'medium': 0.5,
            'low': 0.3
        }
        
        # Costs
        self.failure_costs = {
            'sensor': 50.0,
            'pump': 500.0,
            'motor': 1000.0,
            'gateway': 200.0,
            'solar_panel': 300.0,
        }
        
        self.preventive_costs = {
            'sensor': 20.0,
            'pump': 200.0,
            'motor': 400.0,
            'gateway': 80.0,
            'solar_panel': 100.0,
        }
        
        logger.info("PredictiveMaintenanceEngine initialized")
    
    def register_feature_extractor(
        self,
        component: str,
        extractor: callable
    ):
        """
        Register custom feature extractor for component
        
        Args:
            component: Component name
            extractor: Function that extracts features from device data
        """
        self.feature_extractors[component] = extractor
        logger.info(f"Registered feature extractor for {component}")
    
    def _extract_features(
        self,
        device_id: str,
        component: str,
        data: Dict
    ) -> np.ndarray:
        """Extract features for prediction"""
        if component in self.feature_extractors:
            return self.feature_extractors[component](data)
        
        # Default feature extraction
        features = []
        
        # Operating hours
        features.append(data.get('operating_hours', 0))
        
        # Number of cycles
        features.append(data.get('cycle_count', 0))
        
        # Average load
        features.append(data.get('avg_load', 0))
        
        # Temperature statistics
        features.append(data.get('avg_temperature', 25))
        features.append(data.get('max_temperature', 30))
        
        # Vibration (if available)
        features.append(data.get('avg_vibration', 0))
        
        # Time since last maintenance
        features.append(data.get('days_since_maintenance', 0))
        
        # Number of failures
        features.append(data.get('failure_count', 0))
        
        return np.array(features).reshape(1, -1)
    
    def _calculate_degradation_rate(
        self,
        device_id: str,
        component: str
    ) -> float:
        """Calculate degradation rate from history"""
        if device_id not in self.device_histories:
            return 0.1  # Default rate
        
        history = list(self.device_histories[device_id])
        if len(history) < 2:
            return 0.1
        
        # Calculate rate from recent history
        recent_values = [h.get('degradation', 0) for h in history[-10:]]
        if len(recent_values) < 2:
            return 0.1
        
        # Linear regression for rate
        x = np.arange(len(recent_values))
        coeffs = np.polyfit(x, recent_values, 1)
        rate = abs(coeffs[0])
        
        return max(0.01, rate)
    
    def _determine_risk_level(self, failure_probability: float) -> str:
        """Determine risk level from failure probability"""
        if failure_probability >= self.alert_thresholds['critical']:
            return 'critical'
        elif failure_probability >= self.alert_thresholds['high']:
            return 'high'
        elif failure_probability >= self.alert_thresholds['medium']:
            return 'medium'
        else:
            return 'low'
    
    def _generate_recommendation(
        self,
        risk_level: str,
        rul_days: Optional[float],
        component: str
    ) -> str:
        """Generate maintenance recommendation"""
        if risk_level == 'critical':
            return f"URGENT: Schedule immediate maintenance for {component}"
        elif risk_level == 'high':
            if rul_days and rul_days < 7:
                return f"Schedule maintenance within 7 days for {component}"
            else:
                return f"Schedule maintenance within 2 weeks for {component}"
        elif risk_level == 'medium':
            return f"Monitor {component} closely, plan maintenance in next month"
        else:
            return f"{component} is healthy, continue normal monitoring"
    
    def train_models(
        self,
        training_data: pd.DataFrame,
        target_col: str = 'failed',
        duration_col: str = 'operating_hours',
        event_col: str = 'event'
    ):
        """
        Train predictive models
        
        Args:
            training_data: Historical data with features and outcomes
            target_col: Column indicating failure (1) or not (0)
            duration_col: Time to event column
            event_col: Event indicator column
        """
        logger.info("Training predictive maintenance models...")
        
        # Prepare data
        feature_cols = [
            col for col in training_data.columns
            if col not in [target_col, duration_col, event_col]
        ]
        X = training_data[feature_cols].values
        y = training_data[target_col].values
        
        # Train failure classifier
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        self.failure_classifier.fit(X_train, y_train)
        
        train_score = self.failure_classifier.score(X_train, y_train)
        test_score = self.failure_classifier.score(X_test, y_test)
        logger.info(f"Failure classifier - Train: {train_score:.3f}, Test: {test_score:.3f}")
        
        # Train survival model (if enabled)
        if self.enable_survival_analysis:
            durations = training_data[duration_col].values
            events = training_data[event_col].values
            covariates = training_data[feature_cols]
            
            self.survival_model.fit(durations, events, covariates)
            logger.info("Survival model trained")
        
        # Train degradation model (if enabled)
        if self.enable_degradation_model and 'degradation' in training_data.columns:
            degradation = training_data['degradation'].values
            self.degradation_model.fit(X, degradation)
            logger.info("Degradation model trained")
    
    def predict_failure(
        self,
        device_id: str,
        component: str,
        current_data: Dict
    ) -> FailurePrediction:
        """
        Predict failure for device component
        
        Args:
            device_id: Device ID
            component: Component name
            current_data: Current device data
            
        Returns:
            Failure prediction
        """
        # Extract features
        features = self._extract_features(device_id, component, current_data)
        
        # Predict failure probability
        failure_prob = self.failure_classifier.predict_proba(features)[0, 1]
        
        # Estimate RUL
        rul_days = None
        predicted_failure_date = None
        
        if self.enable_degradation_model and self.degradation_model.fitted:
            degradation_rate = self._calculate_degradation_rate(device_id, component)
            rul_days = self.degradation_model.estimate_rul(
                features,
                degradation_rate
            )
            predicted_failure_date = datetime.now() + timedelta(days=rul_days)
        
        # Feature importance
        if hasattr(self.failure_classifier, 'feature_importances_'):
            feature_names = [f'feature_{i}' for i in range(features.shape[1])]
            importances = dict(zip(
                feature_names,
                self.failure_classifier.feature_importances_
            ))
            # Get top 5 contributing factors
            contributing_factors = dict(
                sorted(importances.items(), key=lambda x: x[1], reverse=True)[:5]
            )
        else:
            contributing_factors = {}
        
        # Determine risk level
        risk_level = self._determine_risk_level(failure_prob)
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            risk_level,
            rul_days,
            component
        )
        
        # Estimate costs
        failure_cost = self.failure_costs.get(component, 100.0)
        preventive_cost = self.preventive_costs.get(component, 50.0)
        
        # Calculate confidence
        confidence = max(0.5, 1.0 - abs(0.5 - failure_prob))
        
        return FailurePrediction(
            device_id=device_id,
            component=component,
            failure_probability=failure_prob,
            predicted_failure_date=predicted_failure_date,
            remaining_useful_life_days=rul_days,
            confidence=confidence,
            risk_level=risk_level,
            contributing_factors=contributing_factors,
            recommended_action=recommendation,
            estimated_cost_if_failure=failure_cost,
            estimated_cost_preventive=preventive_cost,
            timestamp=datetime.now()
        )
    
    def calculate_health_score(
        self,
        device_id: str,
        component_predictions: Dict[str, FailurePrediction]
    ) -> HealthScore:
        """
        Calculate overall device health score
        
        Args:
            device_id: Device ID
            component_predictions: Predictions for each component
            
        Returns:
            Health score
        """
        component_scores = {}
        alerts = []
        
        for component, prediction in component_predictions.items():
            # Convert failure probability to health score (0-100)
            health_score = (1 - prediction.failure_probability) * 100
            component_scores[component] = health_score
            
            # Generate alerts
            if prediction.risk_level in ['critical', 'high']:
                alerts.append(
                    f"{component}: {prediction.risk_level.upper()} risk - "
                    f"{prediction.recommended_action}"
                )
        
        # Overall score is weighted average
        if component_scores:
            overall_score = np.mean(list(component_scores.values()))
        else:
            overall_score = 100.0
        
        # Calculate degradation rate
        degradation_rate = 0.0
        if device_id in self.health_scores:
            prev_score = self.health_scores[device_id].overall_score
            time_diff = (datetime.now() - self.health_scores[device_id].timestamp).days
            if time_diff > 0:
                degradation_rate = (prev_score - overall_score) / time_diff
        
        health = HealthScore(
            device_id=device_id,
            overall_score=overall_score,
            component_scores=component_scores,
            degradation_rate=degradation_rate,
            timestamp=datetime.now(),
            alerts=alerts
        )
        
        self.health_scores[device_id] = health
        return health
    
    def optimize_maintenance_schedule(
        self,
        predictions: List[FailurePrediction],
        max_downtime_days: int = 30,
        budget: Optional[float] = None
    ) -> List[Dict]:
        """
        Optimize maintenance schedule using cost-benefit analysis
        
        Args:
            predictions: List of failure predictions
            max_downtime_days: Maximum acceptable downtime
            budget: Optional budget constraint
            
        Returns:
            Optimized maintenance schedule
        """
        # Sort by expected loss (failure_prob * failure_cost - preventive_cost)
        scored_predictions = []
        for pred in predictions:
            expected_loss_no_action = (
                pred.failure_probability * pred.estimated_cost_if_failure
            )
            expected_loss_preventive = pred.estimated_cost_preventive
            net_benefit = expected_loss_no_action - expected_loss_preventive
            
            scored_predictions.append({
                'prediction': pred,
                'net_benefit': net_benefit,
                'urgency_score': pred.failure_probability / max(pred.remaining_useful_life_days or 1, 1)
            })
        
        # Sort by urgency and benefit
        scored_predictions.sort(
            key=lambda x: (x['urgency_score'], x['net_benefit']),
            reverse=True
        )
        
        # Build schedule within constraints
        schedule = []
        total_cost = 0.0
        scheduled_days = 0
        
        for item in scored_predictions:
            pred = item['prediction']
            
            # Check if maintenance is beneficial
            if item['net_benefit'] <= 0 and pred.risk_level not in ['critical', 'high']:
                continue
            
            # Check budget constraint
            if budget and (total_cost + pred.estimated_cost_preventive > budget):
                continue
            
            # Check downtime constraint
            maintenance_duration_days = 1  # Assume 1 day per maintenance
            if scheduled_days + maintenance_duration_days > max_downtime_days:
                continue
            
            # Add to schedule
            schedule.append({
                'device_id': pred.device_id,
                'component': pred.component,
                'scheduled_date': datetime.now() + timedelta(days=scheduled_days),
                'estimated_cost': pred.estimated_cost_preventive,
                'expected_benefit': item['net_benefit'],
                'risk_level': pred.risk_level,
                'priority': len(schedule) + 1
            })
            
            total_cost += pred.estimated_cost_preventive
            scheduled_days += maintenance_duration_days
        
        logger.info(
            f"Optimized schedule: {len(schedule)} maintenance tasks, "
            f"total cost: ${total_cost:.2f}"
        )
        
        return schedule
    
    def record_maintenance_event(self, event: MaintenanceEvent):
        """Record maintenance event"""
        device_id = event.device_id
        
        if device_id not in self.maintenance_histories:
            self.maintenance_histories[device_id] = []
        
        self.maintenance_histories[device_id].append(event)
        logger.info(f"Recorded maintenance event for {device_id}")
    
    def get_device_maintenance_history(
        self,
        device_id: str
    ) -> List[MaintenanceEvent]:
        """Get maintenance history for device"""
        return self.maintenance_histories.get(device_id, [])
