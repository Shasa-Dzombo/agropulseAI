# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\crop_health_assessment\__init__.py

"""
Crop Health Assessment Package
==============================

This package provides a complete suite of tools for assessing crop health using
multispectral and hyperspectral remote sensing data. It covers the entire
workflow from raw data processing to model training, prediction, and temporal analysis.

The package is designed to be a powerful toolkit for precision agriculture,
enabling the creation of models that can predict crop stress, nutrient
deficiencies, and disease presence from aerial or satellite imagery.

Core Components:
----------------

-   **`data_processing` Module**: Handles ingestion and alignment of raster and
    vector data to create ML-ready datasets.
-   **`vegetation_indices` Module**: A comprehensive library for calculating
    common vegetation indices.
-   **`models` Module**: A factory for creating both classical (sklearn) and
    deep learning (PyTorch) models for spectral data.
-   **`training_pipeline` Module**: A unified pipeline for training and
    evaluating any model created by the factory.
-   **`prediction_pipeline` Module**: Orchestrates the use of a trained model to
    generate a georeferenced prediction map for new imagery.
-   **`temporal_analysis` Module**: Provides tools for smoothing time-series data,
    extracting phenological metrics, and detecting anomalies in crop growth curves.

Public API:
-----------
This `__init__.py` file exposes the key classes and functions from each module,
providing a clean and convenient public API for using the package.
"""

# Expose key components from the data_processing module
from .data_processing import (
    MultispectralImage,
    GroundTruthManager,
    HealthDataPipeline,
    CropHealthDataset
)

# Expose the main function from the vegetation_indices module
from .vegetation_indices import calculate_indices, INDEX_REGISTRY

# Expose the model factory and all model classes
from .models import (
    HealthModelFactory,
    SpectralCNN1D,
    SpectralCNN3D,
    HybridCNN
)

# Expose the training pipeline and early stopping utility
from .training_pipeline import HealthTrainingPipeline, EarlyStopping

# Expose the prediction pipeline
from .prediction_pipeline import HealthPredictionPipeline

# Expose temporal analysis tools
from .temporal_analysis import (
    TimeSeriesSmoother,
    PhenologyModel,
    TemporalAnomalyDetector
)


# Define what gets imported with a wildcard import
__all__ = [
    # From data_processing
    'MultispectralImage',
    'GroundTruthManager',
    'HealthDataPipeline',
    'CropHealthDataset',
    
    # From vegetation_indices
    'calculate_indices',
    'INDEX_REGISTRY',
    
    # From models
    'HealthModelFactory',
    'SpectralCNN1D',
    'SpectralCNN3D',
    'HybridCNN',
    
    # From training_pipeline
    'HealthTrainingPipeline',
    'EarlyStopping',

    # From prediction_pipeline
    'HealthPredictionPipeline',

    # From temporal_analysis
    'TimeSeriesSmoother',
    'PhenologyModel',
    'TemporalAnomalyDetector',
]

# Version of the crop_health_assessment package
__version__ = "1.1.0"

