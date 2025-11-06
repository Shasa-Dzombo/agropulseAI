
# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\pest_identification\__init__.py

"""
Pest Identification Package
===========================

This package provides a comprehensive suite of tools for building, training, and
deploying deep learning models for pest identification tasks, including both
image classification and object detection.

The package is designed to be modular, configurable, and extensible, following
modern deep learning best practices.

Core Components:
----------------

-   **`PestDataModule`**:
    A PyTorch Lightning-style data module that handles all aspects of data
    loading, augmentation, and preprocessing. It provides a clean interface
    for creating training, validation, and test data loaders.
    Located in `data_loader.py`.

-   **`ModelFactory`**:
    A factory class for creating various deep learning models. It supports a
    wide range of architectures from `timm` (for classification) and `torchvision`
    (for detection), such as EfficientNet, ResNet, Faster R-CNN, RetinaNet, and DETR.
    Located in `models.py`.

-   **`LossFactory`**:
    A factory for creating loss functions suitable for different tasks. It includes
    standard losses as well as more advanced ones like Label Smoothing, Focal Loss,
    and a complete DETR loss implementation with bipartite matching.
    Located in `losses.py`.

-   **`TrainingEngine`**:
    The core of the training pipeline. This class abstracts away the boilerplate
    of training loops, validation loops, metric calculation, and device management.
    It is highly configurable and uses a callback system for custom logic.
    Located in `training_engine.py`.

-   **`Callback` System**:
    A modular system for injecting logic into the training process. Key callbacks
    include `ModelCheckpoint` (for saving the best models), `TensorBoardLogger`
    (for experiment tracking), `EarlyStopping` (to prevent overfitting), and
    `LRSchedulerCallback` (for dynamic learning rate adjustments).
    Located in `callbacks.py`.

-   **`InferenceEngine`**:
    A class designed for easy deployment and prediction. It loads a trained model
    and provides a simple `predict()` method to run inference on new images. It also
    includes utilities for model optimization, such as ONNX export.
    Located in `deployment.py`.

-   **`main.py`**:
    The main command-line interface (CLI) for the package. It ties all the
    components together, allowing users to run training, evaluation, prediction,
    and model export tasks from the terminal using a configuration file.

Public API:
-----------
This `__init__.py` file exposes the main classes from each module for easy
importing and use in other parts of the application or in external scripts.
"""

# Expose key components from the data_loader module
from .data_loader import PestDataModule, PestClassificationDataset, PestDetectionDataset

# Expose the model factory and model-related utilities
from .models import ModelFactory

# Expose the loss factory
from .losses import LossFactory, DETRLoss, SetCriterion

# Expose the core training engine and optimizer/scheduler creation functions
from .training_engine import TrainingEngine, create_optimizer, create_scheduler

# Expose the callback system and all implemented callbacks
from .callbacks import (
    Callback,
    ModelCheckpoint,
    TensorBoardLogger,
    EarlyStopping,
    LRSchedulerCallback,
    ProgressLogger
)

# Expose the deployment engine and related utilities
from .deployment import InferenceEngine, export_to_onnx, visualize_predictions

# Define what gets imported with a wildcard import
__all__ = [
    # From data_loader
    'PestDataModule',
    'PestClassificationDataset',
    'PestDetectionDataset',
    # From models
    'ModelFactory',
    # From losses
    'LossFactory',
    'DETRLoss',
    'SetCriterion',
    # From training_engine
    'TrainingEngine',
    'create_optimizer',
    'create_scheduler',
    # From callbacks
    'Callback',
    'ModelCheckpoint',
    'TensorBoardLogger',
    'EarlyStopping',
    'LRSchedulerCallback',
    'ProgressLogger',
    # From deployment
    'InferenceEngine',
    'export_to_onnx',
    'visualize_predictions',
]

# Version of the pest_identification package
__version__ = "1.0.0"

