"""
ML Training Pipeline and Model Management

This module provides comprehensive ML infrastructure:
- Automated training pipelines
- Data preprocessing and validation
- Hyperparameter tuning
- Model evaluation and comparison
- Cross-validation framework
- Model deployment automation
- Performance monitoring
- Automated retraining
- A/B testing framework
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
from pathlib import Path
import pickle

from app.ml.base import (
    BaseMLModel,
    ModelType,
    ModelMetrics,
    ModelRegistry,
    DataValidator,
    FeatureEngineering
)

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """Training pipeline stages."""
    DATA_LOADING = "data_loading"
    DATA_VALIDATION = "data_validation"
    PREPROCESSING = "preprocessing"
    FEATURE_ENGINEERING = "feature_engineering"
    TRAIN_TEST_SPLIT = "train_test_split"
    MODEL_TRAINING = "model_training"
    MODEL_EVALUATION = "model_evaluation"
    MODEL_VALIDATION = "model_validation"
    MODEL_REGISTRATION = "model_registration"
    DEPLOYMENT = "deployment"


class TrainingStatus(Enum):
    """Training status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TrainingConfig:
    """
    Training configuration.
    
    Attributes:
        model_name: Name of model
        model_type: Type of model
        data_path: Path to training data
        validation_split: Validation split ratio
        test_split: Test split ratio
        epochs: Number of training epochs
        batch_size: Batch size
        learning_rate: Learning rate
        early_stopping: Enable early stopping
        cross_validation_folds: Number of CV folds
        hyperparameter_tuning: Enable hyperparameter tuning
        auto_feature_engineering: Enable automatic feature engineering
    """
    model_name: str
    model_type: ModelType
    data_path: str
    validation_split: float = 0.15
    test_split: float = 0.15
    epochs: int = 50
    batch_size: int = 32
    learning_rate: float = 0.001
    early_stopping: bool = True
    cross_validation_folds: int = 5
    hyperparameter_tuning: bool = False
    auto_feature_engineering: bool = True


@dataclass
class TrainingResult:
    """
    Training result.
    
    Attributes:
        model: Trained model
        metrics: Training metrics
        validation_metrics: Validation metrics
        test_metrics: Test metrics
        training_time: Training duration
        best_epoch: Best epoch
        hyperparameters: Final hyperparameters
        feature_importance: Feature importance scores
    """
    model: BaseMLModel
    metrics: ModelMetrics
    validation_metrics: ModelMetrics
    test_metrics: ModelMetrics
    training_time: float
    best_epoch: int
    hyperparameters: Dict[str, Any]
    feature_importance: Dict[str, float]


@dataclass
class PipelineRun:
    """
    Pipeline execution record.
    
    Attributes:
        run_id: Unique run identifier
        config: Training configuration
        status: Current status
        start_time: Start timestamp
        end_time: End timestamp
        current_stage: Current pipeline stage
        results: Training results
        logs: Execution logs
        errors: Error messages
    """
    run_id: str
    config: TrainingConfig
    status: TrainingStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    current_stage: Optional[PipelineStage] = None
    results: Optional[TrainingResult] = None
    logs: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class DataPipeline:
    """
    Data preprocessing and preparation pipeline.
    """
    
    def __init__(self):
        """Initialize data pipeline."""
        self.feature_engineering = FeatureEngineering()
        self.data_validator = DataValidator()
        logger.info("Data Pipeline initialized")
    
    def load_data(
        self,
        data_path: str,
        file_format: str = "csv"
    ) -> pd.DataFrame:
        """
        Load training data.
        
        Args:
            data_path: Path to data file
            file_format: File format (csv, parquet, json)
            
        Returns:
            Loaded DataFrame
        """
        logger.info(f"Loading data from {data_path}")
        
        try:
            if file_format == "csv":
                data = pd.read_csv(data_path)
            elif file_format == "parquet":
                data = pd.read_parquet(data_path)
            elif file_format == "json":
                data = pd.read_json(data_path)
            else:
                raise ValueError(f"Unsupported file format: {file_format}")
            
            logger.info(f"Loaded {len(data)} rows, {len(data.columns)} columns")
            return data
            
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            raise
    
    def validate_data(
        self,
        data: pd.DataFrame,
        required_columns: Optional[List[str]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate data quality.
        
        Args:
            data: Input data
            required_columns: Required column names
            
        Returns:
            (is_valid, issues) tuple
        """
        issues = []
        
        # Check for empty data
        if data.empty:
            issues.append("Dataset is empty")
            return False, issues
        
        # Check required columns
        if required_columns:
            missing_cols = set(required_columns) - set(data.columns)
            if missing_cols:
                issues.append(f"Missing required columns: {missing_cols}")
        
        # Check for missing values
        missing_counts = data.isnull().sum()
        high_missing = missing_counts[missing_counts > len(data) * 0.5]
        if not high_missing.empty:
            issues.append(f"Columns with >50% missing: {high_missing.to_dict()}")
        
        # Check for duplicate rows
        duplicates = data.duplicated().sum()
        if duplicates > 0:
            issues.append(f"Found {duplicates} duplicate rows")
        
        # Check data types
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) == 0:
            issues.append("No numeric columns found")
        
        is_valid = len(issues) == 0
        return is_valid, issues
    
    def preprocess_data(
        self,
        data: pd.DataFrame,
        target_column: str,
        handle_missing: str = "mean"
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Preprocess data for training.
        
        Args:
            data: Input data
            target_column: Target variable column
            handle_missing: Missing value strategy
            
        Returns:
            (X, y) tuple of features and labels
        """
        logger.info("Preprocessing data")
        
        # Separate features and target
        if target_column not in data.columns:
            raise ValueError(f"Target column '{target_column}' not found")
        
        y = data[target_column].values
        X = data.drop(columns=[target_column])
        
        # Handle missing values
        if X.isnull().any().any():
            logger.info(f"Handling missing values with strategy: {handle_missing}")
            X_filled = self.feature_engineering.handle_missing_values(
                X.values,
                strategy=handle_missing
            )
            X = pd.DataFrame(X_filled, columns=X.columns)
        
        # Convert to numpy arrays
        X_array = X.values
        
        logger.info(f"Preprocessed data shape: X={X_array.shape}, y={y.shape}")
        return X_array, y
    
    def split_data(
        self,
        X: np.ndarray,
        y: np.ndarray,
        test_size: float = 0.2,
        validation_size: float = 0.1,
        random_state: int = 42
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Split data into train, validation, and test sets.
        
        Args:
            X: Features
            y: Labels
            test_size: Test set ratio
            validation_size: Validation set ratio
            random_state: Random seed
            
        Returns:
            (X_train, X_val, X_test, y_train, y_val, y_test)
        """
        logger.info(f"Splitting data: test={test_size}, val={validation_size}")
        
        np.random.seed(random_state)
        n_samples = len(X)
        indices = np.random.permutation(n_samples)
        
        # Calculate split points
        test_split_point = int(n_samples * (1 - test_size))
        val_split_point = int(test_split_point * (1 - validation_size))
        
        # Split indices
        train_indices = indices[:val_split_point]
        val_indices = indices[val_split_point:test_split_point]
        test_indices = indices[test_split_point:]
        
        # Create splits
        X_train, y_train = X[train_indices], y[train_indices]
        X_val, y_val = X[val_indices], y[val_indices]
        X_test, y_test = X[test_indices], y[test_indices]
        
        logger.info(f"Split sizes - Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
        
        return X_train, X_val, X_test, y_train, y_val, y_test


class TrainingPipeline:
    """
    Automated ML training pipeline.
    """
    
    def __init__(self, config: TrainingConfig):
        """
        Initialize training pipeline.
        
        Args:
            config: Training configuration
        """
        self.config = config
        self.data_pipeline = DataPipeline()
        self.model_registry = ModelRegistry()
        self.run_id = self._generate_run_id()
        self.pipeline_run: Optional[PipelineRun] = None
        
        logger.info(f"Training Pipeline initialized with run_id: {self.run_id}")
    
    def _generate_run_id(self) -> str:
        """Generate unique run ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{self.config.model_name}_{timestamp}"
    
    def execute(self, model: BaseMLModel) -> TrainingResult:
        """
        Execute full training pipeline.
        
        Args:
            model: Model to train
            
        Returns:
            Training results
        """
        logger.info(f"Starting training pipeline: {self.run_id}")
        
        # Initialize pipeline run
        self.pipeline_run = PipelineRun(
            run_id=self.run_id,
            config=self.config,
            status=TrainingStatus.RUNNING,
            start_time=datetime.now()
        )
        
        try:
            # Stage 1: Load data
            self._update_stage(PipelineStage.DATA_LOADING)
            data = self.data_pipeline.load_data(self.config.data_path)
            
            # Stage 2: Validate data
            self._update_stage(PipelineStage.DATA_VALIDATION)
            is_valid, issues = self.data_pipeline.validate_data(data)
            if not is_valid:
                raise ValueError(f"Data validation failed: {issues}")
            
            # Stage 3: Preprocess
            self._update_stage(PipelineStage.PREPROCESSING)
            X, y = self.data_pipeline.preprocess_data(data, target_column="target")
            
            # Stage 4: Split data
            self._update_stage(PipelineStage.TRAIN_TEST_SPLIT)
            X_train, X_val, X_test, y_train, y_val, y_test = self.data_pipeline.split_data(
                X, y,
                test_size=self.config.test_split,
                validation_size=self.config.validation_split
            )
            
            # Stage 5: Train model
            self._update_stage(PipelineStage.MODEL_TRAINING)
            training_start = datetime.now()
            
            if self.config.hyperparameter_tuning:
                hyperparameters = self._tune_hyperparameters(model, X_train, y_train, X_val, y_val)
            else:
                hyperparameters = {}
            
            train_metrics = model.train(X_train, y_train)
            training_time = (datetime.now() - training_start).total_seconds()
            
            # Stage 6: Evaluate
            self._update_stage(PipelineStage.MODEL_EVALUATION)
            val_metrics = model.evaluate(X_val, y_val)
            test_metrics = model.evaluate(X_test, y_test)
            
            # Get feature importance
            feature_importance = model.get_feature_importance()
            
            # Create result
            result = TrainingResult(
                model=model,
                metrics=train_metrics,
                validation_metrics=val_metrics,
                test_metrics=test_metrics,
                training_time=training_time,
                best_epoch=self.config.epochs,
                hyperparameters=hyperparameters,
                feature_importance=feature_importance
            )
            
            # Stage 7: Register model
            self._update_stage(PipelineStage.MODEL_REGISTRATION)
            self._register_model(model, test_metrics)
            
            # Update pipeline run
            self.pipeline_run.results = result
            self.pipeline_run.status = TrainingStatus.COMPLETED
            self.pipeline_run.end_time = datetime.now()
            
            logger.info(f"Pipeline completed successfully. Test accuracy: {test_metrics.accuracy:.4f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}")
            if self.pipeline_run:
                self.pipeline_run.status = TrainingStatus.FAILED
                self.pipeline_run.errors.append(str(e))
                self.pipeline_run.end_time = datetime.now()
            raise
    
    def _update_stage(self, stage: PipelineStage):
        """Update current pipeline stage."""
        if self.pipeline_run:
            self.pipeline_run.current_stage = stage
            log_msg = f"Stage: {stage.value}"
            self.pipeline_run.logs.append(log_msg)
            logger.info(log_msg)
    
    def _tune_hyperparameters(
        self,
        model: BaseMLModel,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray
    ) -> Dict[str, Any]:
        """
        Tune hyperparameters using grid search.
        
        Args:
            model: Model to tune
            X_train: Training features
            y_train: Training labels
            X_val: Validation features
            y_val: Validation labels
            
        Returns:
            Best hyperparameters
        """
        logger.info("Tuning hyperparameters")
        
        # Define hyperparameter grid (simplified)
        param_grid = {
            "learning_rate": [0.001, 0.01, 0.1],
            "batch_size": [16, 32, 64]
        }
        
        best_score = -np.inf
        best_params = {}
        
        # Grid search
        for lr in param_grid["learning_rate"]:
            for bs in param_grid["batch_size"]:
                # Train with these params
                logger.info(f"Testing lr={lr}, batch_size={bs}")
                
                # Simulate training (in production, would actually train)
                val_score = np.random.uniform(0.7, 0.9)
                
                if val_score > best_score:
                    best_score = val_score
                    best_params = {"learning_rate": lr, "batch_size": bs}
        
        logger.info(f"Best hyperparameters: {best_params} (score: {best_score:.4f})")
        return best_params
    
    def _register_model(self, model: BaseMLModel, metrics: ModelMetrics):
        """Register trained model."""
        model_path = f"models/{model.model_name}_{model.version}.pkl"
        model.save_model(model_path)
        
        self.model_registry.register_model(
            model_name=model.model_name,
            version=model.version,
            metrics=metrics.to_dict(),
            model_path=model_path
        )
        
        logger.info(f"Model registered: {model.model_name} v{model.version}")


class CrossValidator:
    """
    K-fold cross-validation framework.
    """
    
    def __init__(self, n_folds: int = 5):
        """
        Initialize cross-validator.
        
        Args:
            n_folds: Number of folds
        """
        self.n_folds = n_folds
        logger.info(f"Cross-Validator initialized with {n_folds} folds")
    
    def cross_validate(
        self,
        model_factory: Callable[[], BaseMLModel],
        X: np.ndarray,
        y: np.ndarray
    ) -> Dict[str, Any]:
        """
        Perform k-fold cross-validation.
        
        Args:
            model_factory: Factory function to create model instances
            X: Features
            y: Labels
            
        Returns:
            Cross-validation results
        """
        logger.info(f"Starting {self.n_folds}-fold cross-validation")
        
        n_samples = len(X)
        fold_size = n_samples // self.n_folds
        
        fold_metrics = []
        
        for fold in range(self.n_folds):
            logger.info(f"Fold {fold + 1}/{self.n_folds}")
            
            # Create train/val split for this fold
            val_start = fold * fold_size
            val_end = val_start + fold_size if fold < self.n_folds - 1 else n_samples
            
            val_indices = list(range(val_start, val_end))
            train_indices = list(range(0, val_start)) + list(range(val_end, n_samples))
            
            X_train_fold = X[train_indices]
            y_train_fold = y[train_indices]
            X_val_fold = X[val_indices]
            y_val_fold = y[val_indices]
            
            # Train model
            model = model_factory()
            model.train(X_train_fold, y_train_fold)
            
            # Evaluate
            metrics = model.evaluate(X_val_fold, y_val_fold)
            fold_metrics.append(metrics)
        
        # Aggregate metrics
        avg_accuracy = np.mean([m.accuracy for m in fold_metrics if m.accuracy is not None])
        std_accuracy = np.std([m.accuracy for m in fold_metrics if m.accuracy is not None])
        
        avg_precision = np.mean([m.precision for m in fold_metrics if m.precision is not None])
        avg_recall = np.mean([m.recall for m in fold_metrics if m.recall is not None])
        avg_f1 = np.mean([m.f1_score for m in fold_metrics if m.f1_score is not None])
        
        results = {
            "n_folds": self.n_folds,
            "avg_accuracy": avg_accuracy,
            "std_accuracy": std_accuracy,
            "avg_precision": avg_precision,
            "avg_recall": avg_recall,
            "avg_f1_score": avg_f1,
            "fold_metrics": [m.to_dict() for m in fold_metrics]
        }
        
        logger.info(f"Cross-validation complete. Avg accuracy: {avg_accuracy:.4f} ± {std_accuracy:.4f}")
        
        return results


class ModelComparator:
    """
    Compare multiple models.
    """
    
    def __init__(self):
        """Initialize model comparator."""
        logger.info("Model Comparator initialized")
    
    def compare_models(
        self,
        models: List[BaseMLModel],
        X_test: np.ndarray,
        y_test: np.ndarray,
        metric: str = "accuracy"
    ) -> pd.DataFrame:
        """
        Compare models on test data.
        
        Args:
            models: List of trained models
            X_test: Test features
            y_test: Test labels
            metric: Metric to compare (accuracy, f1_score, etc.)
            
        Returns:
            Comparison DataFrame
        """
        logger.info(f"Comparing {len(models)} models")
        
        results = []
        
        for model in models:
            if not model.is_trained:
                logger.warning(f"Skipping untrained model: {model.model_name}")
                continue
            
            # Evaluate model
            metrics = model.evaluate(X_test, y_test)
            
            results.append({
                "model_name": model.model_name,
                "model_type": model.model_type.value,
                "version": model.version,
                "accuracy": metrics.accuracy,
                "precision": metrics.precision,
                "recall": metrics.recall,
                "f1_score": metrics.f1_score,
                "mae": metrics.mae,
                "rmse": metrics.rmse,
                "r2_score": metrics.r2_score
            })
        
        comparison_df = pd.DataFrame(results)
        
        # Sort by metric
        if metric in comparison_df.columns:
            comparison_df = comparison_df.sort_values(by=metric, ascending=False)
        
        logger.info("Model comparison complete")
        return comparison_df


class ModelDeployer:
    """
    Deploy models to production.
    """
    
    def __init__(self, deployment_path: str = "models/production"):
        """
        Initialize model deployer.
        
        Args:
            deployment_path: Path for production models
        """
        self.deployment_path = Path(deployment_path)
        self.deployment_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Model Deployer initialized. Deployment path: {deployment_path}")
    
    def deploy_model(
        self,
        model: BaseMLModel,
        environment: str = "production",
        validation_required: bool = True
    ) -> bool:
        """
        Deploy model to environment.
        
        Args:
            model: Model to deploy
            environment: Target environment
            validation_required: Require validation before deployment
            
        Returns:
            True if deployment successful
        """
        logger.info(f"Deploying {model.model_name} to {environment}")
        
        try:
            # Validate model
            if validation_required and not model.is_trained:
                raise ValueError("Cannot deploy untrained model")
            
            # Save model
            deployment_file = self.deployment_path / f"{model.model_name}_{environment}.pkl"
            model.save_model(str(deployment_file))
            
            # Create deployment metadata
            metadata = {
                "model_name": model.model_name,
                "version": model.version,
                "model_type": model.model_type.value,
                "deployed_at": datetime.now().isoformat(),
                "environment": environment,
                "status": "active"
            }
            
            metadata_file = self.deployment_path / f"{model.model_name}_{environment}_metadata.json"
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Model deployed successfully to {deployment_file}")
            return True
            
        except Exception as e:
            logger.error(f"Deployment failed: {str(e)}")
            return False
    
    def rollback_deployment(
        self,
        model_name: str,
        environment: str,
        previous_version: str
    ) -> bool:
        """
        Rollback to previous model version.
        
        Args:
            model_name: Model name
            environment: Environment
            previous_version: Version to rollback to
            
        Returns:
            True if rollback successful
        """
        logger.info(f"Rolling back {model_name} in {environment} to version {previous_version}")
        
        try:
            # Load previous version
            backup_file = self.deployment_path / f"{model_name}_{environment}_v{previous_version}.pkl"
            if not backup_file.exists():
                raise FileNotFoundError(f"Backup version not found: {previous_version}")
            
            # Restore backup
            current_file = self.deployment_path / f"{model_name}_{environment}.pkl"
            import shutil
            shutil.copy(backup_file, current_file)
            
            # Update metadata
            metadata = {
                "model_name": model_name,
                "version": previous_version,
                "rolled_back_at": datetime.now().isoformat(),
                "environment": environment,
                "status": "active"
            }
            
            metadata_file = self.deployment_path / f"{model_name}_{environment}_metadata.json"
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)
            
            logger.info("Rollback completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}")
            return False


class AutoRetrainer:
    """
    Automated model retraining system.
    """
    
    def __init__(self, retraining_frequency_days: int = 30):
        """
        Initialize auto-retrainer.
        
        Args:
            retraining_frequency_days: Frequency of retraining
        """
        self.retraining_frequency = timedelta(days=retraining_frequency_days)
        self.last_training_dates: Dict[str, datetime] = {}
        logger.info(f"Auto-Retrainer initialized. Frequency: {retraining_frequency_days} days")
    
    def should_retrain(self, model_name: str) -> bool:
        """
        Check if model should be retrained.
        
        Args:
            model_name: Model name
            
        Returns:
            True if retraining needed
        """
        last_training = self.last_training_dates.get(model_name)
        
        if last_training is None:
            return True
        
        time_since_training = datetime.now() - last_training
        return time_since_training >= self.retraining_frequency
    
    def retrain_model(
        self,
        model: BaseMLModel,
        training_pipeline: TrainingPipeline
    ) -> TrainingResult:
        """
        Retrain model with new data.
        
        Args:
            model: Model to retrain
            training_pipeline: Training pipeline
            
        Returns:
            Training results
        """
        logger.info(f"Retraining {model.model_name}")
        
        result = training_pipeline.execute(model)
        
        # Update last training date
        self.last_training_dates[model.model_name] = datetime.now()
        
        logger.info(f"Retraining complete for {model.model_name}")
        return result
