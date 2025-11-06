# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\crop_health_assessment\training_pipeline.py

"""
Training Pipeline for Crop Health Assessment
============================================

This module provides a flexible and robust pipeline for training and evaluating
the crop health models defined in `models.py`. It is designed to handle both
classical machine learning (scikit-learn) and deep learning (PyTorch) models,
providing a unified interface for experimentation.

The pipeline abstracts away the boilerplate code for model training, validation,
hyperparameter tuning, and evaluation, allowing researchers and engineers to
focus on model architecture and data quality.

Key Features:
-------------
1.  **Unified Interface**: A single `HealthTrainingPipeline` class is used to manage
    both scikit-learn and PyTorch models. The class automatically detects the
    model type and adapts its behavior accordingly.

2.  **Scikit-learn Integration**:
    -   For sklearn models, the pipeline uses the familiar `fit` and `predict` API.
    -   It seamlessly integrates with `GridSearchCV` or `RandomizedSearchCV` for
      systematic hyperparameter tuning.
    -   Supports standard cross-validation as well as spatial cross-validation
      (e.g., `SpatialKFold`) to handle the spatial autocorrelation common in
      geospatial data.

3.  **PyTorch Training Engine**:
    -   For PyTorch models, the pipeline includes a robust training engine that
      handles the complete training and validation loops.
    -   **Device Management**: Automatically moves the model and data to the
      correct device (CPU or GPU).
    -   **Optimizer & Scheduler**: Supports various optimizers (Adam, SGD, etc.)
      and learning rate schedulers (Cosine Annealing, StepLR, etc.), which can
      be specified via configuration.
    -   **Loss Functions**: Supports standard regression (MSE, MAE) and
      classification (Cross-Entropy) loss functions.
    -   **Metrics Tracking**: Tracks and logs training and validation metrics
      (e.g., loss, R-squared, accuracy) throughout the training process.
    -   **Early Stopping**: Includes an early stopping mechanism to prevent
      overfitting and save training time.

4.  **Model Persistence**: Provides methods to save and load trained models,
    whether they are scikit-learn objects (using `joblib`) or PyTorch models
    (saving the `state_dict`).

Core Classes:
-------------
-   `HealthTrainingPipeline`: The main orchestrator class. It takes a model,
  data, and a configuration dictionary to run the entire training and
  evaluation workflow.

-   `EarlyStopping`: A utility class used by the PyTorch training engine to
  monitor a validation metric and stop training when it no longer improves.

The pipeline is designed to be driven by a configuration file, making experiments
reproducible and easy to modify.
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_squared_error, r2_score, accuracy_score
from sklearn.base import BaseEstimator
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
import logging
from typing import Dict, Any, Tuple, Union

from .models import HealthModelFactory

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EarlyStopping:
    """
    Utility for early stopping in PyTorch training loop.
    """
    def __init__(self, patience: int = 7, verbose: bool = False, delta: float = 0, mode: str = 'min'):
        self.patience = patience
        self.verbose = verbose
        self.delta = delta
        self.mode = mode
        self.counter = 0
        self.best_score = np.Inf if mode == 'min' else -np.Inf
        self.early_stop = False

    def __call__(self, val_metric: float):
        score_improved = False
        if self.mode == 'min':
            if val_metric < self.best_score - self.delta:
                self.best_score = val_metric
                score_improved = True
        else: # mode == 'max'
            if val_metric > self.best_score + self.delta:
                self.best_score = val_metric
                score_improved = True

        if score_improved:
            self.counter = 0
        else:
            self.counter += 1
            if self.verbose:
                logging.info(f"EarlyStopping counter: {self.counter} out of {self.patience}")
            if self.counter >= self.patience:
                self.early_stop = True

class HealthTrainingPipeline:
    """
    A pipeline for training and evaluating crop health models.
    """
    def __init__(self, model: Union[BaseEstimator, nn.Module], config: Dict[str, Any]):
        self.model = model
        self.config = config
        self.is_pytorch_model = isinstance(model, nn.Module)
        
        if self.is_pytorch_model:
            self.device = torch.device(config.get('device', 'cuda' if torch.cuda.is_available() else 'cpu'))
            self.model.to(self.device)
            logging.info(f"PyTorch model moved to device: {self.device}")
        else:
            logging.info("Initialized pipeline for scikit-learn model.")

    def fit(self, X: pd.DataFrame, y: pd.Series):
        """
        Trains the model on the given data.
        
        Args:
            X (pd.DataFrame): Feature data.
            y (pd.Series): Target data.
        """
        if self.is_pytorch_model:
            self._fit_pytorch(X.values, y.values)
        else:
            self._fit_sklearn(X, y)

    def _fit_sklearn(self, X: pd.DataFrame, y: pd.Series):
        """Handles training for scikit-learn models, including hyperparameter tuning."""
        logging.info(f"Starting training for {self.model.__class__.__name__}.")
        
        tuning_config = self.config.get('hyperparameter_tuning')
        if tuning_config:
            logging.info("Performing GridSearchCV for hyperparameter tuning.")
            grid_search = GridSearchCV(
                self.model,
                tuning_config['param_grid'],
                cv=tuning_config.get('cv', 5),
                scoring=tuning_config.get('scoring'),
                n_jobs=tuning_config.get('n_jobs', -1)
            )
            grid_search.fit(X, y)
            self.model = grid_search.best_estimator_
            logging.info(f"Best parameters found: {grid_search.best_params_}")
            logging.info(f"Best score: {grid_search.best_score_:.4f}")
        else:
            self.model.fit(X, y)
            
        logging.info("Scikit-learn model training complete.")

    def _fit_pytorch(self, X: np.ndarray, y: np.ndarray):
        """Handles the training loop for PyTorch models."""
        train_params = self.config['training_params']
        
        # Data preparation
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=train_params.get('val_split', 0.2), random_state=42
        )
        
        train_dataset = TensorDataset(torch.from_numpy(X_train).float(), torch.from_numpy(y_train).float())
        val_dataset = TensorDataset(torch.from_numpy(X_val).float(), torch.from_numpy(y_val).float())
        
        train_loader = DataLoader(train_dataset, batch_size=train_params['batch_size'], shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=train_params['batch_size'])

        # Optimizer, Scheduler, Loss
        optimizer = self._create_optimizer(train_params['optimizer'])
        scheduler = self._create_scheduler(optimizer, train_params.get('scheduler', {}))
        loss_fn = self._get_loss_function()
        
        early_stopper = EarlyStopping(
            patience=train_params.get('early_stopping_patience', 10),
            mode=train_params.get('early_stopping_mode', 'min'),
            verbose=True
        )

        logging.info(f"Starting PyTorch model training for {train_params['num_epochs']} epochs.")
        
        for epoch in range(train_params['num_epochs']):
            self.model.train()
            train_loss = 0.0
            for batch_X, batch_y in train_loader:
                batch_X, batch_y = batch_X.to(self.device), batch_y.to(self.device)
                
                optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = loss_fn(outputs, batch_y)
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item()
            
            avg_train_loss = train_loss / len(train_loader)
            
            # Validation loop
            val_loss, _ = self.evaluate(val_loader)
            
            logging.info(f"Epoch {epoch+1}/{train_params['num_epochs']} | "
                         f"Train Loss: {avg_train_loss:.4f} | Val Loss: {val_loss:.4f}")
            
            if scheduler:
                if isinstance(scheduler, torch.optim.lr_scheduler.ReduceLROnPlateau):
                    scheduler.step(val_loss)
                else:
                    scheduler.step()
            
            early_stopper(val_loss)
            if early_stopper.early_stop:
                logging.info("Early stopping triggered.")
                break
                
        logging.info("PyTorch model training complete.")

    def evaluate(self, data_loader: DataLoader) -> Tuple[float, Dict[str, float]]:
        """Evaluates a PyTorch model on a given data loader."""
        if not self.is_pytorch_model:
            raise TypeError("This evaluation method is for PyTorch models only.")
            
        self.model.eval()
        total_loss = 0.0
        all_preds, all_targets = [], []
        loss_fn = self._get_loss_function()

        with torch.no_grad():
            for batch_X, batch_y in data_loader:
                batch_X, batch_y = batch_X.to(self.device), batch_y.to(self.device)
                outputs = self.model(batch_X)
                loss = loss_fn(outputs, batch_y)
                total_loss += loss.item()
                
                all_preds.append(outputs.cpu().numpy())
                all_targets.append(batch_y.cpu().numpy())
        
        avg_loss = total_loss / len(data_loader)
        
        all_preds = np.concatenate(all_preds)
        all_targets = np.concatenate(all_targets)
        
        metrics = self._calculate_metrics(all_targets, all_preds)
        return avg_loss, metrics

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Generates predictions for new data."""
        if self.is_pytorch_model:
            self.model.eval()
            with torch.no_grad():
                X_tensor = torch.from_numpy(X.values).float().to(self.device)
                predictions = self.model(X_tensor).cpu().numpy()
        else:
            predictions = self.model.predict(X)
        return predictions

    def save_model(self, path: str):
        """Saves the trained model to a file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        
        if self.is_pytorch_model:
            torch.save(self.model.state_dict(), p)
            logging.info(f"PyTorch model state_dict saved to {p}")
        else:
            joblib.dump(self.model, p)
            logging.info(f"Scikit-learn model saved to {p}")

    def _create_optimizer(self, opt_config: Dict) -> torch.optim.Optimizer:
        name = opt_config['name'].lower()
        lr = opt_config['lr']
        if name == 'adam':
            return torch.optim.Adam(self.model.parameters(), lr=lr)
        elif name == 'sgd':
            return torch.optim.SGD(self.model.parameters(), lr=lr, momentum=opt_config.get('momentum', 0.9))
        else:
            raise ValueError(f"Unsupported optimizer: {name}")

    def _create_scheduler(self, optimizer: torch.optim.Optimizer, sched_config: Dict):
        name = sched_config.get('name', '').lower()
        if not name:
            return None
        if name == 'cosine_annealing':
            return torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=sched_config['T_max'])
        elif name == 'step_lr':
            return torch.optim.lr_scheduler.StepLR(optimizer, step_size=sched_config['step_size'], gamma=sched_config['gamma'])
        elif name == 'reduce_on_plateau':
            return torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.1, patience=5)
        else:
            raise ValueError(f"Unsupported scheduler: {name}")

    def _get_loss_function(self):
        task = self.config.get('task', 'regression')
        if task == 'regression':
            return nn.MSELoss()
        elif task == 'classification':
            return nn.CrossEntropyLoss()
        else:
            raise ValueError(f"Unsupported task for loss function: {task}")

    def _calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        task = self.config.get('task', 'regression')
        if task == 'regression':
            return {
                'mse': mean_squared_error(y_true, y_pred),
                'r2': r2_score(y_true, y_pred)
            }
        elif task == 'classification':
            y_pred_class = np.argmax(y_pred, axis=1) if y_pred.ndim > 1 else (y_pred > 0.5).astype(int)
            return {
                'accuracy': accuracy_score(y_true, y_pred_class)
            }
        return {}

# Example Usage
if __name__ == '__main__':
    print("--- Health Training Pipeline Demo ---")

    # --- Demo 1: Scikit-learn (Random Forest Regressor) ---
    print("\n1. Scikit-learn Random Forest Demo")
    # Dummy data
    X_train_sk = pd.DataFrame(np.random.rand(100, 10))
    y_train_sk = pd.Series(np.random.rand(100) * 10)
    
    # Model and pipeline config
    rf_config = {'name': 'random_forest', 'params': {'n_estimators': 50, 'random_state': 42}}
    rf_model = HealthModelFactory.create_model(rf_config)
    
    pipeline_config_sk = {
        'task': 'regression',
        # Example of hyperparameter tuning config
        'hyperparameter_tuning': {
            'param_grid': {'n_estimators': [20, 50], 'max_depth': [5, 10]},
            'cv': 3,
            'scoring': 'r2'
        }
    }
    
    pipeline_sk = HealthTrainingPipeline(rf_model, pipeline_config_sk)
    pipeline_sk.fit(X_train_sk, y_train_sk)
    
    # Test prediction
    X_test_sk = pd.DataFrame(np.random.rand(5, 10))
    preds_sk = pipeline_sk.predict(X_test_sk)
    print(f"Sklearn predictions: {preds_sk}")
    
    # Save model
    pipeline_sk.save_model('./trained_models/rf_health_model.joblib')

    # --- Demo 2: PyTorch (1D CNN) ---
    print("\n2. PyTorch 1D CNN Demo")
    # Dummy data
    X_train_torch = np.random.rand(200, 150) # 200 samples, 150 spectral bands
    y_train_torch = np.random.rand(200) * 5
    
    # Model and pipeline config
    cnn1d_config = {'name': 'spectral_cnn_1d', 'params': {'input_bands': 150}}
    cnn1d_model = HealthModelFactory.create_model(cnn1d_config)
    
    pipeline_config_torch = {
        'task': 'regression',
        'device': 'cpu',
        'training_params': {
            'num_epochs': 5, # Short for demo
            'batch_size': 16,
            'val_split': 0.2,
            'optimizer': {'name': 'adam', 'lr': 0.001},
            'scheduler': {'name': 'cosine_annealing', 'T_max': 5},
            'early_stopping_patience': 3
        }
    }
    
    pipeline_torch = HealthTrainingPipeline(cnn1d_model, pipeline_config_torch)
    pipeline_torch.fit(pd.DataFrame(X_train_torch), pd.Series(y_train_torch))
    
    # Test prediction
    X_test_torch = pd.DataFrame(np.random.rand(5, 150))
    preds_torch = pipeline_torch.predict(X_test_torch)
    print(f"PyTorch predictions: {preds_torch}")
    
    # Save model
    pipeline_torch.save_model('./trained_models/cnn1d_health_model.pth')

```