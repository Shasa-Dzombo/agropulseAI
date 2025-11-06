# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\weed_detection\__init__.py

"""
Weed Detection Package
======================

This package provides a complete pipeline for training and deploying deep learning-based
object detection models for the task of weed detection in agricultural imagery.

It includes modules for:
-   **Data Loading**: Handling datasets with PASCAL VOC-style annotations, with
    support for complex data augmentation using `albumentations`.
-   **Model Creation**: A factory for instantiating various `torchvision` object
    detection models like Faster R-CNN, SSD, and RetinaNet, with automatic
    head replacement for transfer learning.
-   **Training Engine**: A robust training and evaluation engine adapted from
    PyTorch's official references, featuring a `MetricLogger` and `CocoEvaluator`
    for standard COCO-based performance metrics (mAP).
-   **Prediction**: A simple and efficient inference pipeline for running a trained
    model on new images and visualizing the results.

Key Modules and Classes:
------------------------
-   `data_loader.WeedDataset`: The main PyTorch Dataset class.
-   `data_loader.DetectionAugmenter`: Handles image and bounding box augmentations.
-   `models.WeedDetectionModelFactory`: Creates object detection models.
-   `engine.train_one_epoch`: The core training loop for a single epoch.
-   `engine.evaluate`: The core evaluation loop using COCO metrics.
-   `prediction.WeedDetector`: A high-level class for running inference.

This `__init__.py` file makes the `weed_detection` directory a Python package and
exposes its most important components at the top level for easier access.
"""

# Expose key classes and functions for easier access from outside the package
from .data_loader import WeedDataset, AnnotationParser, DetectionAugmenter, collate_fn
from .models import WeedDetectionModelFactory
from .engine import train_one_epoch, evaluate
from .prediction import WeedDetector, visualize_predictions
from .training import main as run_training

__all__ = [
    "WeedDataset",
    "AnnotationParser",
    "DetectionAugmenter",
    "collate_fn",
    "WeedDetectionModelFactory",
    "train_one_epoch",
    "evaluate",
    "WeedDetector",
    "visualize_predictions",
    "run_training",
]

__version__ = "0.1.0"
```