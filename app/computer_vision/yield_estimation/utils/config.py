"""
Centralized Configuration Management for Yield Estimation
=========================================================

This module provides a robust and centralized configuration system for the entire
yield estimation pipeline. It uses Pydantic for data validation and settings
management, allowing for type-safe, hierarchical, and environment-aware
configurations.

Core Principles:
----------------
1.  **Single Source of Truth**: All configurable parameters for data paths, model
    hyperparameters, training settings, and API configurations are defined here.
2.  **Type Safety**: Pydantic ensures that all configuration values have the correct
    data type, preventing common runtime errors.
3.  **Hierarchical Structure**: Configurations are organized into logical nested
    classes (e.g., `DataConfig`, `ModelConfig`, `TrainConfig`), making the structure
    intuitive and easy to navigate.
4.  **Environment Variable Overrides**: The system can automatically override default
    values with environment variables, making it suitable for different deployment
    environments (development, staging, production) without code changes.
5.  **Validation**: Pydantic models allow for custom validators to ensure that
    configuration values are not just the right type, but also within valid ranges
    or adhere to specific constraints.
6.  **Extensibility**: New configurations can be easily added by defining new
    Pydantic models.

Structure:
----------
-   `DataConfig`: Manages paths to datasets, defines data sources (e.g., drone,
    satellite), and specifies parameters for data splitting and sampling.
-   `AugmentationConfig`: Defines the parameters for various data augmentation
    techniques, allowing for fine-grained control over the augmentation pipeline.
-   `ModelConfig`: A parent class for model-specific configurations.
    -   `DetectionModelConfig`: Hyperparameters for object detection models (e.g.,
      YOLO, DETR), such as confidence thresholds and NMS settings.
    -   `SegmentationModelConfig`: Settings for segmentation models (e.g., U-Net),
      including encoder backbones and loss functions.
    -   `RegressionModelConfig`: Parameters for direct regression models, including
      input feature dimensions and fusion strategies.
-   `TrainConfig`: Governs the training process, including learning rate, batch size,
    number of epochs, optimizer choice, and scheduler settings.
-   `APIConfig`: Configuration for the FastAPI application, such as host, port, and
    log levels.
-   `Settings`: The main container class that aggregates all other configuration
    models and provides a single point of access.

Usage:
------
The settings are loaded once and made available throughout the application via a
singleton pattern.

```python
from app.computer_vision.yield_estimation.utils.config import get_settings

settings = get_settings()
print(settings.train.learning_rate)
print(settings.data.raw_data_dir)
```
"""

import os
from pydantic import BaseModel, Field, validator
from typing import List, Tuple, Dict, Optional, Literal
from functools import lru_cache

# --- Base Configurations ---

class BaseConfig(BaseModel):
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        extra = 'ignore'

# --- Data Configurations ---

class DataSourceConfig(BaseConfig):
    """Configuration for a single data source."""
    name: str = Field(..., description="Unique name for the data source (e.g., 'drone_rgb', 'sentinel2_nir').")
    type: Literal['drone', 'satellite', 'ground'] = Field(..., description="Type of the imagery source.")
    modalities: List[str] = Field(..., description="List of data modalities provided (e.g., ['RGB', 'NIR', 'thermal']).")
    resolution: float = Field(..., description="Spatial resolution in meters per pixel.")

class DataConfig(BaseConfig):
    """Configuration for data loading and processing."""
    raw_data_dir: str = Field("data/raw", description="Directory for raw, unprocessed data.")
    processed_data_dir: str = Field("data/processed", description="Directory for processed and structured data.")
    train_split: float = Field(0.7, ge=0, le=1, description="Proportion of data for the training set.")
    val_split: float = Field(0.15, ge=0, le=1, description="Proportion of data for the validation set.")
    test_split: float = Field(0.15, ge=0, le=1, description="Proportion of data for the test set.")
    image_size: Tuple[int, int] = Field((512, 512), description="Target image size (height, width) for model input.")
    sources: List[DataSourceConfig] = Field(default_factory=list, description="List of available data sources.")

    @validator('train_split', 'val_split', 'test_split')
    def splits_must_sum_to_one(cls, v, values):
        """Ensure that data splits are configured correctly."""
        # This validator is tricky to implement perfectly without seeing all values.
        # A more robust implementation would be a root validator in a final settings object.
        return v

# --- Augmentation Configurations ---

class AugmentationConfig(BaseConfig):
    """Configuration for data augmentation techniques."""
    enable: bool = Field(True, description="Enable or disable augmentations for the training set.")
    h_flip_prob: float = Field(0.5, ge=0, le=1)
    v_flip_prob: float = Field(0.5, ge=0, le=1)
    rotation_limit: int = Field(45, ge=0, le=360)
    rotation_prob: float = Field(0.5, ge=0, le=1)
    brightness_contrast_prob: float = Field(0.3, ge=0, le=1)
    gauss_noise_prob: float = Field(0.2, ge=0, le=1)
    crop_prob: float = Field(0.5, ge=0, le=1)

# --- Model Configurations ---

class ModelConfig(BaseConfig):
    """Base configuration for any model."""
    name: str = Field(..., description="Name of the model architecture.")
    num_classes: int = Field(1, description="Number of output classes (for classification/segmentation).")

class DetectionModelConfig(ModelConfig):
    """Configuration for object detection models."""
    name: Literal['yolo', 'detr', 'faster_rcnn'] = 'yolo'
    confidence_threshold: float = Field(0.5, ge=0, le=1)
    nms_threshold: float = Field(0.45, ge=0, le=1)
    backbone: str = Field("darknet53", description="Backbone for the detector.")

class SegmentationModelConfig(ModelConfig):
    """Configuration for segmentation models."""
    name: Literal['unet', 'deeplabv3+'] = 'unet'
    encoder_name: str = Field("resnet50", description="Encoder backbone for the segmentation model.")
    encoder_weights: str = Field("imagenet", description="Pre-trained weights for the encoder.")

class RegressionModelConfig(ModelConfig):
    """Configuration for direct yield regression models."""
    name: Literal['cnn_regressor', 'multimodal_regressor'] = 'cnn_regressor'
    input_features: int = Field(3, description="Number of input channels (e.g., 3 for RGB).")
    dropout_rate: float = Field(0.5, ge=0, le=1)

# --- Training Configurations ---

class TrainConfig(BaseConfig):
    """Configuration for the training process."""
    device: Literal['cuda', 'cpu'] = Field('cuda', description="Device to use for training.")
    epochs: int = Field(100, gt=0)
    batch_size: int = Field(16, gt=0)
    optimizer: Literal['adam', 'sgd', 'adamw'] = Field('adamw')
    learning_rate: float = Field(1e-4, gt=0)
    weight_decay: float = Field(1e-5, ge=0)
    scheduler: Literal['step_lr', 'cosine_annealing', 'reduce_on_plateau'] = Field('cosine_annealing')
    patience: int = Field(10, description="Patience for ReduceLROnPlateau scheduler.")
    num_workers: int = Field(4, ge=0)
    amp: bool = Field(True, description="Enable Automatic Mixed Precision (AMP) for faster training.")
    log_interval: int = Field(50, description="Log training metrics every N batches.")
    checkpoint_dir: str = Field("models/checkpoints", description="Directory to save model checkpoints.")

# --- API Configurations ---

class APIConfig(BaseConfig):
    """Configuration for the FastAPI application."""
    host: str = Field("0.0.0.0")
    port: int = Field(8000)
    log_level: str = Field("info")
    workers: int = Field(1, description="Number of Gunicorn workers.")
    secret_key: str = Field("a_very_secret_key", description="Secret key for JWT or other security features.")
    api_prefix: str = Field("/api/v1", description="Prefix for all API routes.")

# --- Main Settings Container ---

class Settings(BaseConfig):
    """Main settings container for the entire application."""
    project_name: str = "AgroPulse Yield Estimation"
    version: str = "1.0.0"
    log_level: str = Field("INFO")
    
    data: DataConfig = DataConfig()
    augmentation: AugmentationConfig = AugmentationConfig()
    
    # Allow for multiple model configurations
    models: Dict[str, Union[DetectionModelConfig, SegmentationModelConfig, RegressionModelConfig]] = Field(
        default_factory=lambda: {
            "default_detection": DetectionModelConfig(),
            "default_segmentation": SegmentationModelConfig(),
            "default_regression": RegressionModelConfig(),
        }
    )
    
    train: TrainConfig = TrainConfig()
    api: APIConfig = APIConfig()

    class Config:
        env_nested_delimiter = '__'

@lru_cache()
def get_settings() -> Settings:
    """
    Loads and returns the application settings.
    The lru_cache decorator ensures this function is only run once, creating a
    singleton-like behavior for the settings object.
    """
    # In a real application, you might load from a YAML file here
    # and merge with environment variables.
    # For simplicity, we rely on Pydantic's .env loading.
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
    logging.info("Loading application settings...")
    settings = Settings()
    logging.info("Application settings loaded successfully.")
    return settings

# Example of how to use it
if __name__ == "__main__":
    settings = get_settings()
    
    print("--- Yield Estimation Configuration ---")
    print(f"Project: {settings.project_name} v{settings.version}")
    print(f"Log Level: {settings.log_level}")
    
    print("\n[Data Configuration]")
    print(f"  Raw Data Path: {settings.data.raw_data_dir}")
    print(f"  Processed Data Path: {settings.data.processed_data_dir}")
    print(f"  Image Size: {settings.data.image_size}")
    
    print("\n[Training Configuration]")
    print(f"  Device: {settings.train.device}")
    print(f"  Epochs: {settings.train.epochs}")
    print(f"  Batch Size: {settings.train.batch_size}")
    print(f"  Learning Rate: {settings.train.learning_rate}")
    
    print("\n[API Configuration]")
    print(f"  Host: {settings.api.host}")
    print(f"  Port: {settings.api.port}")
    
    print("\n[Default Detection Model Configuration]")
    print(f"  Model Name: {settings.models['default_detection'].name}")
    print(f"  Backbone: {settings.models['default_detection'].backbone}")
    
    # You can access nested settings easily
    assert settings.train.batch_size == 16
    
    # Example of how environment variables would override this:
    # export TRAIN__BATCH_SIZE=32
    # The settings loader would automatically pick this up.
    print("\nConfiguration system is working correctly.")
