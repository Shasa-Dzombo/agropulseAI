# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\rgb_health_assessment\__init__.py

"""
RGB Health Assessment Package
=============================

This package provides a complete, end-to-end solution for assessing plant and
crop health using standard RGB images from sources like mobile phones, drones,
and CCTV cameras. It is designed to work without the need for specialized
multispectral or hyperspectral sensors.

The package encapsulates the entire machine learning workflow, from image
preprocessing and feature extraction to model training and prediction. It is
built to be highly modular and configurable, allowing users to easily adapt
the pipeline to their specific needs and datasets.

Core Modules:
-------------

-   **`rgb_indices` Module**:
    -   Provides a comprehensive library of vegetation indices that can be
      calculated from only the Red, Green, and Blue channels of an image.
    -   Includes indices like VARI, NGRDI, ExG, and TGI, which are effective
      at highlighting vegetation and estimating its health.

-   **`preprocessing` Module**:
    -   `RGBDataPipeline`: An orchestrator for a multi-step preprocessing workflow.
    -   `ColorCorrector`: Standardizes image colors to handle variations in
      lighting conditions using methods like Gray World or White Patch.
    -   `PlantSegmenter`: Accurately separates plant pixels from the background
      using techniques ranging from simple index-based thresholding to advanced
      deep learning models (DeepLabV3+).
    -   `FeatureExtractor`: Computes a rich, tabular feature vector from the
      segmented plant, including statistics from RGB indices, color histograms,
      texture features (GLCM), and morphological properties.

-   **`models` Module**:
    -   `RGBHealthModelFactory`: A factory for creating various classical
      machine learning classifiers that are well-suited for tabular feature data.
    -   Supports a wide range of scikit-learn models, including `RandomForest`,
      `GradientBoosting`, `SVC`, and `MLP`, as well as `XGBoost`.

-   **`training` Module**:
    -   `TrainingPipeline`: An end-to-end pipeline that automates the model
      training process. It handles data splitting, feature extraction, optional
      hyperparameter tuning (`GridSearchCV`), model evaluation, and the
      serialization of all resulting artifacts (model, config, reports).

-   **`prediction` Module**:
    -   `PredictionPipeline`: A lightweight and deployable pipeline for making
      predictions on new images. It loads a trained model and its associated
      configuration to ensure reproducible preprocessing and prediction.

-   **`main` Module**:
    -   Provides a command-line interface (CLI) that exposes the core
      functionality of the package, allowing users to easily train models,
      make predictions, and generate configuration templates from the terminal.

Public API:
-----------
This `__init__.py` file exposes the primary pipeline classes from each module,
offering a clean and high-level API for programmatic use of the package.
"""

# Expose the main function from the rgb_indices module
from .rgb_indices import calculate_rgb_indices, get_available_rgb_indices

# Expose the main data pipeline from the preprocessing module
from .preprocessing import RGBDataPipeline

# Expose the model factory from the models module
from .models import RGBHealthModelFactory

# Expose the main training pipeline
from .training import TrainingPipeline

# Expose the main prediction pipeline
from .prediction import PredictionPipeline

# Define what gets imported with a wildcard import
__all__ = [
    # From rgb_indices
    'calculate_rgb_indices',
    'get_available_rgb_indices',
    
    # From preprocessing
    'RGBDataPipeline',
    
    # From models
    'RGBHealthModelFactory',
    
    # From training
    'TrainingPipeline',
    
    # From prediction
    'PredictionPipeline',
]

# Version of the rgb_health_assessment package
__version__ = "1.0.0"
```