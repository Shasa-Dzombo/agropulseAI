"""
Machine Learning Package

This package contains all AI/ML models and infrastructure for AgroPulse, including:
- Crop recommendation engine
- Pest detection models
- Yield prediction models
- Weather forecasting integration
- Soil analysis algorithms
- Model training and evaluation pipelines
- Feature engineering utilities
- Model registry and versioning

Design Principles:
1. Model Modularity: Each model is independent and reusable
2. Feature Engineering: Comprehensive data preprocessing
3. Model Versioning: Track model performance and versions
4. Production Ready: Optimized for real-time inference
5. Explainability: Provide reasoning for predictions
6. Continuous Learning: Support for model retraining
"""

from app.ml.base import (
    BaseMLModel,
    ModelMetrics,
    PredictionResult,
    FeatureEngineering,
    ModelRegistry
)

__all__ = [
    # Base classes
    "BaseMLModel",
    "ModelMetrics",
    "PredictionResult",
    "FeatureEngineering",
    "ModelRegistry",
]
