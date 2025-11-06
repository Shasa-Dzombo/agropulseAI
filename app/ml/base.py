"""
ML Base Module

This module provides the foundation for all machine learning models in AgroPulse,
including base classes, utilities, and common functionality.

Key Components:
- BaseMLModel: Abstract base class for all ML models
- ModelMetrics: Model performance evaluation
- PredictionResult: Standardized prediction output
- FeatureEngineering: Data preprocessing and feature extraction
- ModelRegistry: Model versioning and management
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from pathlib import Path
from abc import ABC, abstractmethod
import json
import pickle
import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ModelType(str, Enum):
    """Types of ML models."""
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    CLUSTERING = "clustering"
    RECOMMENDATION = "recommendation"


class ModelStatus(str, Enum):
    """Model lifecycle status."""
    TRAINING = "training"
    TESTING = "testing"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    FAILED = "failed"


@dataclass
class ModelMetrics:
    """
    Model performance metrics container.
    
    Attributes:
        accuracy: Model accuracy (0-1)
        precision: Precision score
        recall: Recall score
        f1_score: F1 score
        mae: Mean Absolute Error (regression)
        rmse: Root Mean Squared Error (regression)
        r2_score: R-squared score (regression)
        confusion_matrix: Confusion matrix (classification)
        feature_importance: Feature importance scores
        training_time: Time taken to train (seconds)
        inference_time: Average inference time (milliseconds)
        timestamp: Metrics collection timestamp
    """
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    mae: Optional[float] = None
    rmse: Optional[float] = None
    r2_score: Optional[float] = None
    confusion_matrix: Optional[np.ndarray] = None
    feature_importance: Optional[Dict[str, float]] = None
    training_time: Optional[float] = None
    inference_time: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "mae": self.mae,
            "rmse": self.rmse,
            "r2_score": self.r2_score,
            "confusion_matrix": self.confusion_matrix.tolist() if self.confusion_matrix is not None else None,
            "feature_importance": self.feature_importance,
            "training_time": self.training_time,
            "inference_time": self.inference_time,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class PredictionResult:
    """
    Standardized prediction result container.
    
    Attributes:
        prediction: Primary prediction value
        confidence: Confidence score (0-1)
        probabilities: Class probabilities (classification)
        explanation: Human-readable explanation
        metadata: Additional metadata
        model_version: Version of model used
        features_used: Features used for prediction
        timestamp: Prediction timestamp
    """
    prediction: Any
    confidence: float
    probabilities: Optional[Dict[str, float]] = None
    explanation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    model_version: Optional[str] = None
    features_used: Optional[List[str]] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert prediction to dictionary."""
        return {
            "prediction": self.prediction,
            "confidence": self.confidence,
            "probabilities": self.probabilities,
            "explanation": self.explanation,
            "metadata": self.metadata,
            "model_version": self.model_version,
            "features_used": self.features_used,
            "timestamp": self.timestamp.isoformat()
        }


class BaseMLModel(ABC):
    """
    Abstract base class for all ML models.
    
    This class provides common functionality for model lifecycle management,
    including training, prediction, evaluation, and persistence.
    """
    
    def __init__(
        self,
        model_name: str,
        model_type: ModelType,
        version: str = "1.0.0"
    ):
        """
        Initialize the ML model.
        
        Args:
            model_name: Name of the model
            model_type: Type of model
            version: Model version
        """
        self.model_name = model_name
        self.model_type = model_type
        self.version = version
        self.model = None
        self.is_trained = False
        self.metrics: Optional[ModelMetrics] = None
        self.feature_names: List[str] = []
        self.metadata: Dict[str, Any] = {
            "created_at": datetime.utcnow().isoformat(),
            "status": ModelStatus.TRAINING.value
        }
        
        logger.info(f"Initialized {model_name} v{version} ({model_type.value})")
    
    @abstractmethod
    def train(
        self,
        X_train: Union[np.ndarray, pd.DataFrame],
        y_train: Union[np.ndarray, pd.Series],
        **kwargs
    ) -> ModelMetrics:
        """
        Train the model.
        
        Args:
            X_train: Training features
            y_train: Training labels
            **kwargs: Additional training parameters
            
        Returns:
            Training metrics
        """
        pass
    
    @abstractmethod
    def predict(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        **kwargs
    ) -> PredictionResult:
        """
        Make predictions.
        
        Args:
            X: Input features
            **kwargs: Additional prediction parameters
            
        Returns:
            Prediction result
        """
        pass
    
    @abstractmethod
    def evaluate(
        self,
        X_test: Union[np.ndarray, pd.DataFrame],
        y_test: Union[np.ndarray, pd.Series]
    ) -> ModelMetrics:
        """
        Evaluate model performance.
        
        Args:
            X_test: Test features
            y_test: Test labels
            
        Returns:
            Evaluation metrics
        """
        pass
    
    def save_model(self, path: str) -> str:
        """
        Save model to disk.
        
        Args:
            path: Directory path to save model
            
        Returns:
            Full path to saved model file
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before saving")
        
        Path(path).mkdir(parents=True, exist_ok=True)
        
        model_file = Path(path) / f"{self.model_name}_v{self.version}.pkl"
        metadata_file = Path(path) / f"{self.model_name}_v{self.version}_metadata.json"
        
        # Save model
        with open(model_file, 'wb') as f:
            pickle.dump(self.model, f)
        
        # Save metadata
        metadata = {
            "model_name": self.model_name,
            "model_type": self.model_type.value,
            "version": self.version,
            "feature_names": self.feature_names,
            "metrics": self.metrics.to_dict() if self.metrics else None,
            "metadata": self.metadata
        }
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Model saved to {model_file}")
        return str(model_file)
    
    def load_model(self, path: str) -> bool:
        """
        Load model from disk.
        
        Args:
            path: Path to model file
            
        Returns:
            True if successful
        """
        model_file = Path(path)
        metadata_file = model_file.parent / f"{model_file.stem}_metadata.json"
        
        if not model_file.exists():
            raise FileNotFoundError(f"Model file not found: {model_file}")
        
        # Load model
        with open(model_file, 'rb') as f:
            self.model = pickle.load(f)
        
        # Load metadata if available
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                self.feature_names = metadata.get("feature_names", [])
                self.metadata = metadata.get("metadata", {})
        
        self.is_trained = True
        logger.info(f"Model loaded from {model_file}")
        return True
    
    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """
        Get feature importance scores.
        
        Returns:
            Dictionary mapping feature names to importance scores
        """
        if not self.is_trained:
            return None
        
        # This should be implemented by subclasses based on model type
        return None
    
    def update_status(self, status: ModelStatus):
        """Update model status."""
        self.metadata["status"] = status.value
        self.metadata["updated_at"] = datetime.utcnow().isoformat()
        logger.info(f"{self.model_name} status: {status.value}")


class FeatureEngineering:
    """
    Feature engineering utilities for data preprocessing.
    
    Provides methods for feature extraction, transformation, and normalization
    specific to agricultural data.
    """
    
    @staticmethod
    def normalize_features(
        data: Union[np.ndarray, pd.DataFrame],
        method: str = "standard"
    ) -> np.ndarray:
        """
        Normalize features.
        
        Args:
            data: Input data
            method: Normalization method (standard, minmax, robust)
            
        Returns:
            Normalized data
        """
        if isinstance(data, pd.DataFrame):
            data = data.values
        
        if method == "standard":
            # Standardization (mean=0, std=1)
            mean = np.mean(data, axis=0)
            std = np.std(data, axis=0)
            return (data - mean) / (std + 1e-8)
        
        elif method == "minmax":
            # Min-Max scaling (0-1)
            min_val = np.min(data, axis=0)
            max_val = np.max(data, axis=0)
            return (data - min_val) / (max_val - min_val + 1e-8)
        
        elif method == "robust":
            # Robust scaling (median and IQR)
            median = np.median(data, axis=0)
            q75, q25 = np.percentile(data, [75, 25], axis=0)
            iqr = q75 - q25
            return (data - median) / (iqr + 1e-8)
        
        else:
            raise ValueError(f"Unknown normalization method: {method}")
    
    @staticmethod
    def extract_soil_features(soil_data: Dict[str, float]) -> np.ndarray:
        """
        Extract and engineer soil features.
        
        Args:
            soil_data: Dictionary with soil measurements
            
        Returns:
            Feature array
        """
        features = []
        
        # Basic soil properties
        features.append(soil_data.get("ph", 7.0))
        features.append(soil_data.get("nitrogen", 0.0))
        features.append(soil_data.get("phosphorus", 0.0))
        features.append(soil_data.get("potassium", 0.0))
        features.append(soil_data.get("organic_matter", 0.0))
        features.append(soil_data.get("moisture", 0.0))
        
        # Derived features
        npk_total = soil_data.get("nitrogen", 0.0) + \
                   soil_data.get("phosphorus", 0.0) + \
                   soil_data.get("potassium", 0.0)
        features.append(npk_total)
        
        # NPK ratios
        n = soil_data.get("nitrogen", 0.0)
        p = soil_data.get("phosphorus", 0.0)
        k = soil_data.get("potassium", 0.0)
        
        features.append(n / (p + 1e-8))  # N:P ratio
        features.append(n / (k + 1e-8))  # N:K ratio
        features.append(p / (k + 1e-8))  # P:K ratio
        
        return np.array(features)
    
    @staticmethod
    def extract_weather_features(weather_data: Dict[str, Any]) -> np.ndarray:
        """
        Extract and engineer weather features.
        
        Args:
            weather_data: Dictionary with weather data
            
        Returns:
            Feature array
        """
        features = []
        
        # Current conditions
        features.append(weather_data.get("temperature", 25.0))
        features.append(weather_data.get("humidity", 60.0))
        features.append(weather_data.get("rainfall", 0.0))
        features.append(weather_data.get("wind_speed", 0.0))
        features.append(weather_data.get("pressure", 1013.0))
        
        # Historical aggregates
        features.append(weather_data.get("avg_temp_7d", 25.0))
        features.append(weather_data.get("total_rainfall_7d", 0.0))
        features.append(weather_data.get("avg_humidity_7d", 60.0))
        
        # Derived features
        temp = weather_data.get("temperature", 25.0)
        humidity = weather_data.get("humidity", 60.0)
        
        # Heat index approximation
        heat_index = temp + 0.5 * (humidity - 50) * 0.1
        features.append(heat_index)
        
        # Growing degree days (GDD) - base 10°C
        gdd = max(0, temp - 10)
        features.append(gdd)
        
        return np.array(features)
    
    @staticmethod
    def extract_crop_features(crop_data: Dict[str, Any]) -> np.ndarray:
        """
        Extract crop-specific features.
        
        Args:
            crop_data: Dictionary with crop information
            
        Returns:
            Feature array
        """
        features = []
        
        # Crop characteristics
        features.append(crop_data.get("growth_duration_days", 90))
        features.append(crop_data.get("water_requirement", 500.0))
        features.append(crop_data.get("optimal_temp_min", 15.0))
        features.append(crop_data.get("optimal_temp_max", 30.0))
        
        # Current growth stage (encoded)
        growth_stage_map = {
            "germination": 0,
            "vegetative": 1,
            "flowering": 2,
            "fruiting": 3,
            "maturity": 4
        }
        stage = crop_data.get("growth_stage", "vegetative")
        features.append(growth_stage_map.get(stage, 1))
        
        # Days since planting
        features.append(crop_data.get("days_since_planting", 0))
        
        # Area planted
        features.append(crop_data.get("area_acres", 1.0))
        
        return np.array(features)
    
    @staticmethod
    def create_time_features(timestamp: datetime) -> np.ndarray:
        """
        Create time-based features.
        
        Args:
            timestamp: Datetime object
            
        Returns:
            Feature array
        """
        features = []
        
        # Month (1-12)
        features.append(timestamp.month)
        
        # Season (encoded)
        month = timestamp.month
        if month in [12, 1, 2]:
            season = 0  # Winter
        elif month in [3, 4, 5]:
            season = 1  # Spring
        elif month in [6, 7, 8]:
            season = 2  # Summer
        else:
            season = 3  # Fall
        features.append(season)
        
        # Day of year (1-365)
        features.append(timestamp.timetuple().tm_yday)
        
        # Cyclic encoding for month (sin/cos)
        month_sin = np.sin(2 * np.pi * timestamp.month / 12)
        month_cos = np.cos(2 * np.pi * timestamp.month / 12)
        features.append(month_sin)
        features.append(month_cos)
        
        return np.array(features)
    
    @staticmethod
    def handle_missing_values(
        data: pd.DataFrame,
        strategy: str = "mean"
    ) -> pd.DataFrame:
        """
        Handle missing values in dataset.
        
        Args:
            data: Input dataframe
            strategy: Imputation strategy (mean, median, mode, forward, drop)
            
        Returns:
            Dataframe with imputed values
        """
        if strategy == "mean":
            return data.fillna(data.mean())
        elif strategy == "median":
            return data.fillna(data.median())
        elif strategy == "mode":
            return data.fillna(data.mode().iloc[0])
        elif strategy == "forward":
            return data.fillna(method='ffill')
        elif strategy == "drop":
            return data.dropna()
        else:
            raise ValueError(f"Unknown strategy: {strategy}")


class ModelRegistry:
    """
    Model registry for version management and tracking.
    
    Maintains a registry of all models with their versions, metrics,
    and metadata for model governance and reproducibility.
    """
    
    def __init__(self, registry_path: str = "models/registry.json"):
        """
        Initialize model registry.
        
        Args:
            registry_path: Path to registry file
        """
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry: Dict[str, List[Dict]] = self._load_registry()
    
    def _load_registry(self) -> Dict[str, List[Dict]]:
        """Load registry from disk."""
        if self.registry_path.exists():
            with open(self.registry_path, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_registry(self):
        """Save registry to disk."""
        with open(self.registry_path, 'w') as f:
            json.dump(self.registry, f, indent=2)
    
    def register_model(
        self,
        model_name: str,
        version: str,
        metrics: ModelMetrics,
        model_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Register a model version.
        
        Args:
            model_name: Name of model
            version: Model version
            metrics: Performance metrics
            model_path: Path to saved model
            metadata: Additional metadata
        """
        if model_name not in self.registry:
            self.registry[model_name] = []
        
        entry = {
            "version": version,
            "registered_at": datetime.utcnow().isoformat(),
            "metrics": metrics.to_dict(),
            "model_path": model_path,
            "metadata": metadata or {},
            "status": ModelStatus.PRODUCTION.value
        }
        
        self.registry[model_name].append(entry)
        self._save_registry()
        
        logger.info(f"Registered {model_name} v{version}")
    
    def get_model_info(
        self,
        model_name: str,
        version: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get model information.
        
        Args:
            model_name: Name of model
            version: Specific version (optional, defaults to latest)
            
        Returns:
            Model information dictionary
        """
        if model_name not in self.registry:
            return None
        
        versions = self.registry[model_name]
        
        if version:
            for v in versions:
                if v["version"] == version:
                    return v
            return None
        else:
            # Return latest version
            return versions[-1] if versions else None
    
    def list_models(self) -> Dict[str, int]:
        """
        List all registered models.
        
        Returns:
            Dictionary mapping model names to version count
        """
        return {
            name: len(versions)
            for name, versions in self.registry.items()
        }
    
    def compare_versions(
        self,
        model_name: str,
        metric: str = "accuracy"
    ) -> List[Tuple[str, float]]:
        """
        Compare model versions by metric.
        
        Args:
            model_name: Name of model
            metric: Metric to compare
            
        Returns:
            List of (version, metric_value) tuples sorted by metric
        """
        if model_name not in self.registry:
            return []
        
        comparisons = []
        for version_info in self.registry[model_name]:
            metrics = version_info.get("metrics", {})
            value = metrics.get(metric)
            if value is not None:
                comparisons.append((version_info["version"], value))
        
        return sorted(comparisons, key=lambda x: x[1], reverse=True)


class DataValidator:
    """
    Data validation utilities for ML pipelines.
    
    Ensures data quality and consistency before model training or inference.
    """
    
    @staticmethod
    def validate_features(
        features: Union[np.ndarray, pd.DataFrame],
        expected_shape: Optional[Tuple[int, ...]] = None,
        expected_columns: Optional[List[str]] = None
    ) -> bool:
        """
        Validate feature data.
        
        Args:
            features: Feature data
            expected_shape: Expected shape (optional)
            expected_columns: Expected column names (optional)
            
        Returns:
            True if valid
            
        Raises:
            ValueError: If validation fails
        """
        if isinstance(features, pd.DataFrame):
            if expected_columns:
                missing = set(expected_columns) - set(features.columns)
                if missing:
                    raise ValueError(f"Missing columns: {missing}")
            
            if expected_shape and features.shape != expected_shape:
                raise ValueError(f"Shape mismatch: expected {expected_shape}, got {features.shape}")
        
        elif isinstance(features, np.ndarray):
            if expected_shape and features.shape != expected_shape:
                raise ValueError(f"Shape mismatch: expected {expected_shape}, got {features.shape}")
            
            # Check for NaN or inf
            if np.any(np.isnan(features)) or np.any(np.isinf(features)):
                raise ValueError("Features contain NaN or inf values")
        
        return True
    
    @staticmethod
    def validate_labels(
        labels: Union[np.ndarray, pd.Series],
        num_classes: Optional[int] = None
    ) -> bool:
        """
        Validate label data.
        
        Args:
            labels: Label data
            num_classes: Expected number of classes (optional)
            
        Returns:
            True if valid
            
        Raises:
            ValueError: If validation fails
        """
        if isinstance(labels, pd.Series):
            labels = labels.values
        
        # Check for NaN
        if np.any(np.isnan(labels)):
            raise ValueError("Labels contain NaN values")
        
        # Check number of classes
        if num_classes:
            unique_classes = len(np.unique(labels))
            if unique_classes != num_classes:
                raise ValueError(f"Expected {num_classes} classes, found {unique_classes}")
        
        return True
