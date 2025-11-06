"""
AgroPulse - Advanced Time-Series Forecasting Module
====================================================

This module provides state-of-the-art time-series forecasting capabilities for
agricultural predictions including crop yields, market prices, weather patterns,
and optimal harvest timing.

Features:
---------
- Prophet forecasting for seasonal patterns
- LSTM neural networks for complex dependencies
- Multi-variate time-series analysis
- Confidence intervals and uncertainty quantification
- Automated model selection and hyperparameter tuning
- Real-time inference API

Models:
-------
1. YieldPredictor: Crop yield forecasting based on historical data, weather, and sensor inputs
2. PriceForecaster: Market price predictions using time-series and external factors
3. WeatherForecaster: Weather pattern predictions for farm planning
4. SeasonalAnalyzer: Seasonal trend decomposition and analysis
5. OptimalHarvestPredictor: Optimal harvest timing recommendations

Author: AgroPulse ML Team
Version: 1.0.0
"""

from .prophet_models import (
    ProphetYieldPredictor,
    ProphetPriceForecaster,
    ProphetWeatherForecaster,
)
from .lstm_models import (
    LSTMYieldPredictor,
    LSTMPriceForecaster,
    LSTMMultivariatePredictor,
)
from .ensemble_models import (
    EnsembleForecaster,
    StackedPredictor,
    WeightedAveragePredictor,
)
from .training_pipeline import (
    ForecastingPipeline,
    ModelTrainer,
    HyperparameterOptimizer,
)
from .inference import (
    ForecastingService,
    BatchPredictor,
    RealtimePredictor,
)

__all__ = [
    # Prophet models
    'ProphetYieldPredictor',
    'ProphetPriceForecaster',
    'ProphetWeatherForecaster',
    
    # LSTM models
    'LSTMYieldPredictor',
    'LSTMPriceForecaster',
    'LSTMMultivariatePredictor',
    
    # Ensemble models
    'EnsembleForecaster',
    'StackedPredictor',
    'WeightedAveragePredictor',
    
    # Training pipeline
    'ForecastingPipeline',
    'ModelTrainer',
    'HyperparameterOptimizer',
    
    # Inference
    'ForecastingService',
    'BatchPredictor',
    'RealtimePredictor',
]

__version__ = '1.0.0'
