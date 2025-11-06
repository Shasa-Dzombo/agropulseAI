"""
Isolation Forest Anomaly Detection Models
=========================================

Unsupervised anomaly detection for agricultural sensor data, irrigation patterns,
and weather anomalies using Isolation Forest and One-Class SVM.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import joblib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class AnomalyResult:
    """Anomaly detection result."""
    timestamp: datetime
    is_anomaly: bool
    anomaly_score: float
    feature_values: Dict[str, float]
    anomaly_type: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    explanation: str


class SensorAnomalyDetector:
    """
    Detect anomalies in IoT sensor readings.
    
    Anomaly types:
    - Sensor malfunction (stuck values, out-of-range)
    - Data transmission errors
    - Environmental extremes
    - Battery issues
    - Physical damage
    
    Features:
    - Temperature (°C)
    - Humidity (%)
    - Soil moisture (%)
    - Light intensity (lux)
    - Battery voltage (V)
    - RSSI (signal strength)
    """
    
    def __init__(
        self,
        contamination: float = 0.05,
        n_estimators: int = 100,
        max_samples: int = 256,
        random_state: int = 42,
    ):
        """
        Initialize sensor anomaly detector.
        
        Args:
            contamination: Expected proportion of anomalies (default: 5%)
            n_estimators: Number of isolation trees
            max_samples: Samples to draw for each tree
            random_state: Random seed
        """
        self.contamination = contamination
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            max_samples=max_samples,
            random_state=random_state,
            n_jobs=-1,
        )
        
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=0.95)  # Retain 95% variance
        
        self.feature_names = [
            'temperature',
            'humidity',
            'soil_moisture',
            'light_intensity',
            'battery_voltage',
            'rssi',
        ]
        
        self.is_fitted = False
        self.baseline_stats = {}
        
    def fit(
        self,
        X: pd.DataFrame,
        sensor_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Train anomaly detector on normal sensor data.
        
        Args:
            X: Training data with sensor features
            sensor_ids: Optional sensor identifiers for per-sensor modeling
            
        Returns:
            Training statistics
        """
        logger.info(f"Training sensor anomaly detector on {len(X)} samples...")
        
        # Calculate baseline statistics
        for feature in self.feature_names:
            if feature in X.columns:
                self.baseline_stats[feature] = {
                    'mean': X[feature].mean(),
                    'std': X[feature].std(),
                    'min': X[feature].min(),
                    'max': X[feature].max(),
                    'q1': X[feature].quantile(0.25),
                    'q3': X[feature].quantile(0.75),
                }
                
        # Scale features
        X_scaled = self.scaler.fit_transform(X[self.feature_names])
        
        # Optional dimensionality reduction
        if X_scaled.shape[1] > 10:
            X_scaled = self.pca.fit_transform(X_scaled)
            
        # Train isolation forest
        self.model.fit(X_scaled)
        self.is_fitted = True
        
        # Calculate training metrics
        predictions = self.model.predict(X_scaled)
        scores = self.model.score_samples(X_scaled)
        
        n_anomalies = np.sum(predictions == -1)
        anomaly_rate = n_anomalies / len(predictions)
        
        metrics = {
            'samples': len(X),
            'anomalies_detected': n_anomalies,
            'anomaly_rate': anomaly_rate,
            'mean_score': scores.mean(),
            'std_score': scores.std(),
        }
        
        logger.info(f"Training complete: {n_anomalies}/{len(X)} anomalies ({anomaly_rate*100:.2f}%)")
        return metrics
        
    def detect(
        self,
        X: pd.DataFrame,
        return_scores: bool = True,
    ) -> List[AnomalyResult]:
        """
        Detect anomalies in new sensor data.
        
        Args:
            X: Sensor data with timestamps
            return_scores: Whether to return anomaly scores
            
        Returns:
            List of AnomalyResult objects
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before detection")
            
        # Scale features
        X_scaled = self.scaler.transform(X[self.feature_names])
        
        if hasattr(self.pca, 'components_'):
            X_scaled = self.pca.transform(X_scaled)
            
        # Predict anomalies
        predictions = self.model.predict(X_scaled)
        scores = self.model.score_samples(X_scaled)
        
        # Convert scores to 0-1 range (lower score = more anomalous)
        # Isolation forest returns negative scores
        normalized_scores = 1 / (1 + np.exp(scores))  # Sigmoid transformation
        
        results = []
        for i in range(len(X)):
            is_anomaly = predictions[i] == -1
            score = normalized_scores[i]
            
            # Determine severity
            if score > 0.9:
                severity = 'critical'
            elif score > 0.75:
                severity = 'high'
            elif score > 0.6:
                severity = 'medium'
            else:
                severity = 'low'
                
            # Identify anomaly type
            anomaly_type, explanation = self._identify_anomaly_type(
                X.iloc[i],
                is_anomaly,
            )
            
            results.append(AnomalyResult(
                timestamp=X.iloc[i].get('timestamp', datetime.now()),
                is_anomaly=is_anomaly,
                anomaly_score=float(score),
                feature_values={
                    feat: float(X.iloc[i][feat])
                    for feat in self.feature_names
                    if feat in X.columns
                },
                anomaly_type=anomaly_type,
                severity=severity,
                explanation=explanation,
            ))
            
        n_anomalies = sum(1 for r in results if r.is_anomaly)
        logger.info(f"Detected {n_anomalies}/{len(results)} anomalies")
        
        return results
        
    def _identify_anomaly_type(
        self,
        sample: pd.Series,
        is_anomaly: bool,
    ) -> Tuple[str, str]:
        """
        Identify the type of anomaly based on feature values.
        
        Returns:
            Tuple of (anomaly_type, explanation)
        """
        if not is_anomaly:
            return ('normal', 'All sensor readings within normal range')
            
        issues = []
        
        # Check temperature
        if 'temperature' in sample and 'temperature' in self.baseline_stats:
            temp = sample['temperature']
            stats = self.baseline_stats['temperature']
            if temp < stats['min'] - 3 * stats['std']:
                issues.append('Temperature too low')
            elif temp > stats['max'] + 3 * stats['std']:
                issues.append('Temperature too high')
                
        # Check humidity
        if 'humidity' in sample and 'humidity' in self.baseline_stats:
            hum = sample['humidity']
            stats = self.baseline_stats['humidity']
            if hum < 10:
                issues.append('Humidity sensor error (too low)')
            elif hum > 100:
                issues.append('Humidity sensor error (out of range)')
                
        # Check soil moisture
        if 'soil_moisture' in sample and 'soil_moisture' in self.baseline_stats:
            moisture = sample['soil_moisture']
            if moisture < 5:
                issues.append('Extremely dry soil')
            elif moisture > 90:
                issues.append('Soil waterlogged')
                
        # Check battery voltage
        if 'battery_voltage' in sample:
            voltage = sample['battery_voltage']
            if voltage < 3.3:
                issues.append('Low battery (critical)')
            elif voltage < 3.5:
                issues.append('Low battery')
                
        # Check RSSI
        if 'rssi' in sample:
            rssi = sample['rssi']
            if rssi < -100:
                issues.append('Weak signal')
                
        if issues:
            return ('sensor_malfunction', '; '.join(issues))
        else:
            return ('unknown_anomaly', 'Unusual pattern detected')
            
    def save(self, filepath: str):
        """Save trained model."""
        if not self.is_fitted:
            raise ValueError("Cannot save unfitted model")
            
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'pca': self.pca,
            'baseline_stats': self.baseline_stats,
            'feature_names': self.feature_names,
        }
        joblib.dump(model_data, filepath)
        logger.info(f"Model saved to {filepath}")
        
    @classmethod
    def load(cls, filepath: str) -> 'SensorAnomalyDetector':
        """Load trained model."""
        model_data = joblib.load(filepath)
        
        detector = cls()
        detector.model = model_data['model']
        detector.scaler = model_data['scaler']
        detector.pca = model_data['pca']
        detector.baseline_stats = model_data['baseline_stats']
        detector.feature_names = model_data['feature_names']
        detector.is_fitted = True
        
        logger.info(f"Model loaded from {filepath}")
        return detector


class IrrigationAnomalyDetector:
    """
    Detect anomalies in irrigation patterns.
    
    Anomaly types:
    - Over-irrigation
    - Under-irrigation
    - Irregular scheduling
    - System leaks
    - Valve malfunctions
    
    Features:
    - Flow rate (L/min)
    - Pressure (PSI)
    - Duration (minutes)
    - Frequency (times/day)
    - Soil moisture before/after
    """
    
    def __init__(
        self,
        contamination: float = 0.03,
        kernel: str = 'rbf',
    ):
        """
        Initialize irrigation anomaly detector.
        
        Args:
            contamination: Expected anomaly proportion (default: 3%)
            kernel: SVM kernel ('rbf', 'linear', 'poly')
        """
        self.model = OneClassSVM(
            kernel=kernel,
            gamma='auto',
            nu=contamination,
        )
        
        self.scaler = StandardScaler()
        
        self.feature_names = [
            'flow_rate',
            'pressure',
            'duration',
            'frequency',
            'moisture_before',
            'moisture_after',
            'temperature',
            'humidity',
        ]
        
        self.is_fitted = False
        
    def fit(self, X: pd.DataFrame) -> Dict[str, Any]:
        """Train irrigation anomaly detector."""
        logger.info(f"Training irrigation anomaly detector on {len(X)} samples...")
        
        X_scaled = self.scaler.fit_transform(X[self.feature_names])
        self.model.fit(X_scaled)
        self.is_fitted = True
        
        predictions = self.model.predict(X_scaled)
        n_anomalies = np.sum(predictions == -1)
        
        metrics = {
            'samples': len(X),
            'anomalies': n_anomalies,
            'anomaly_rate': n_anomalies / len(X),
        }
        
        logger.info(f"Training complete: {n_anomalies} anomalies detected")
        return metrics
        
    def detect(self, X: pd.DataFrame) -> List[AnomalyResult]:
        """Detect irrigation anomalies."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted first")
            
        X_scaled = self.scaler.transform(X[self.feature_names])
        predictions = self.model.predict(X_scaled)
        
        # SVM decision function (distance to boundary)
        decision_scores = self.model.decision_function(X_scaled)
        normalized_scores = 1 / (1 + np.exp(decision_scores))
        
        results = []
        for i in range(len(X)):
            is_anomaly = predictions[i] == -1
            score = normalized_scores[i]
            
            # Determine severity
            if score > 0.8:
                severity = 'critical'
            elif score > 0.65:
                severity = 'high'
            elif score > 0.5:
                severity = 'medium'
            else:
                severity = 'low'
                
            # Identify issue
            anomaly_type, explanation = self._identify_irrigation_issue(
                X.iloc[i],
                is_anomaly,
            )
            
            results.append(AnomalyResult(
                timestamp=X.iloc[i].get('timestamp', datetime.now()),
                is_anomaly=is_anomaly,
                anomaly_score=float(score),
                feature_values={
                    feat: float(X.iloc[i][feat])
                    for feat in self.feature_names
                    if feat in X.columns
                },
                anomaly_type=anomaly_type,
                severity=severity,
                explanation=explanation,
            ))
            
        return results
        
    def _identify_irrigation_issue(
        self,
        sample: pd.Series,
        is_anomaly: bool,
    ) -> Tuple[str, str]:
        """Identify irrigation anomaly type."""
        if not is_anomaly:
            return ('normal', 'Irrigation within normal parameters')
            
        issues = []
        
        # Check flow rate
        if 'flow_rate' in sample:
            flow = sample['flow_rate']
            if flow < 5:
                issues.append('Low flow rate (possible clog)')
            elif flow > 50:
                issues.append('High flow rate (possible leak)')
                
        # Check pressure
        if 'pressure' in sample:
            pressure = sample['pressure']
            if pressure < 20:
                issues.append('Low pressure')
            elif pressure > 60:
                issues.append('High pressure (system stress)')
                
        # Check duration
        if 'duration' in sample:
            duration = sample['duration']
            if duration < 5:
                issues.append('Very short irrigation cycle')
            elif duration > 60:
                issues.append('Excessive irrigation duration')
                
        # Check moisture change
        if 'moisture_before' in sample and 'moisture_after' in sample:
            before = sample['moisture_before']
            after = sample['moisture_after']
            change = after - before
            
            if change < 5:
                issues.append('Little moisture increase (ineffective irrigation)')
            elif change > 40:
                issues.append('Excessive moisture increase (over-irrigation)')
                
        if issues:
            return ('irrigation_malfunction', '; '.join(issues))
        else:
            return ('unusual_pattern', 'Irrigation pattern unusual')


class WeatherAnomalyDetector:
    """
    Detect weather anomalies and extreme events.
    
    Anomaly types:
    - Extreme temperatures
    - Unexpected rainfall
    - Severe storms
    - Drought conditions
    - Frost events
    """
    
    def __init__(
        self,
        seasonal: bool = True,
        location: str = 'unknown',
    ):
        """
        Initialize weather anomaly detector.
        
        Args:
            seasonal: Account for seasonal patterns
            location: Location identifier
        """
        self.model = IsolationForest(
            contamination=0.02,
            n_estimators=100,
            random_state=42,
        )
        
        self.scaler = StandardScaler()
        self.seasonal = seasonal
        self.location = location
        
        self.feature_names = [
            'temperature',
            'rainfall',
            'humidity',
            'wind_speed',
            'pressure',
            'solar_radiation',
        ]
        
        if seasonal:
            self.feature_names.extend(['month', 'day_of_year'])
            
        self.is_fitted = False
        
    def fit(self, X: pd.DataFrame) -> Dict[str, Any]:
        """Train weather anomaly detector."""
        logger.info(f"Training weather anomaly detector for {self.location}...")
        
        # Add seasonal features
        if self.seasonal and 'timestamp' in X.columns:
            X = X.copy()
            X['month'] = pd.to_datetime(X['timestamp']).dt.month
            X['day_of_year'] = pd.to_datetime(X['timestamp']).dt.dayofyear
            
        X_scaled = self.scaler.fit_transform(X[self.feature_names])
        self.model.fit(X_scaled)
        self.is_fitted = True
        
        predictions = self.model.predict(X_scaled)
        n_anomalies = np.sum(predictions == -1)
        
        metrics = {
            'samples': len(X),
            'anomalies': n_anomalies,
            'location': self.location,
        }
        
        logger.info(f"Training complete: {n_anomalies} weather anomalies found")
        return metrics
        
    def detect(self, X: pd.DataFrame) -> List[AnomalyResult]:
        """Detect weather anomalies."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted first")
            
        # Add seasonal features
        if self.seasonal and 'timestamp' in X.columns:
            X = X.copy()
            X['month'] = pd.to_datetime(X['timestamp']).dt.month
            X['day_of_year'] = pd.to_datetime(X['timestamp']).dt.dayofyear
            
        X_scaled = self.scaler.transform(X[self.feature_names])
        predictions = self.model.predict(X_scaled)
        scores = self.model.score_samples(X_scaled)
        
        normalized_scores = 1 / (1 + np.exp(scores))
        
        results = []
        for i in range(len(X)):
            is_anomaly = predictions[i] == -1
            score = normalized_scores[i]
            
            if score > 0.9:
                severity = 'critical'
            elif score > 0.75:
                severity = 'high'
            elif score > 0.6:
                severity = 'medium'
            else:
                severity = 'low'
                
            anomaly_type, explanation = self._identify_weather_event(
                X.iloc[i],
                is_anomaly,
            )
            
            results.append(AnomalyResult(
                timestamp=X.iloc[i].get('timestamp', datetime.now()),
                is_anomaly=is_anomaly,
                anomaly_score=float(score),
                feature_values={
                    feat: float(X.iloc[i][feat])
                    for feat in self.feature_names
                    if feat in X.columns
                },
                anomaly_type=anomaly_type,
                severity=severity,
                explanation=explanation,
            ))
            
        return results
        
    def _identify_weather_event(
        self,
        sample: pd.Series,
        is_anomaly: bool,
    ) -> Tuple[str, str]:
        """Identify weather anomaly type."""
        if not is_anomaly:
            return ('normal', 'Normal weather conditions')
            
        events = []
        
        # Temperature extremes
        if 'temperature' in sample:
            temp = sample['temperature']
            if temp < 0:
                events.append('Frost warning')
            elif temp < 10:
                events.append('Unusually cold')
            elif temp > 40:
                events.append('Extreme heat')
                
        # Rainfall
        if 'rainfall' in sample:
            rain = sample['rainfall']
            if rain > 50:
                events.append('Heavy rainfall')
            elif rain > 100:
                events.append('Extreme rainfall (flooding risk)')
                
        # Wind
        if 'wind_speed' in sample:
            wind = sample['wind_speed']
            if wind > 30:
                events.append('High winds')
            elif wind > 50:
                events.append('Storm conditions')
                
        if events:
            return ('weather_extreme', '; '.join(events))
        else:
            return ('unusual_weather', 'Unusual weather pattern')
