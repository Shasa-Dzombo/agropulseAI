"""
AgroPulse - Anomaly Detection System
====================================

Machine learning models for detecting anomalies in agricultural operations
including sensor malfunctions, crop diseases, irrigation issues, and fraud.
"""

from .isolation_forest import (
    SensorAnomalyDetector,
    IrrigationAnomalyDetector,
    WeatherAnomalyDetector,
)
from .autoencoder import (
    CropHealthAutoencoder,
    SoilPatternAutoencoder,
    MultivariateAnomalyDetector,
)
from .statistical_methods import (
    ZScoreDetector,
    MADDetector,
    SeasonalDecompositionDetector,
)
from .ensemble import (
    EnsembleAnomalyDetector,
    VotingDetector,
    StackedDetector,
)

__all__ = [
    # Isolation Forest
    'SensorAnomalyDetector',
    'IrrigationAnomalyDetector',
    'WeatherAnomalyDetector',
    
    # Autoencoder
    'CropHealthAutoencoder',
    'SoilPatternAutoencoder',
    'MultivariateAnomalyDetector',
    
    # Statistical
    'ZScoreDetector',
    'MADDetector',
    'SeasonalDecompositionDetector',
    
    # Ensemble
    'EnsembleAnomalyDetector',
    'VotingDetector',
    'StackedDetector',
]
