"""
Model Factory for Yield Estimation
==================================

This module implements a `ModelFactory`, a crucial design pattern for creating
and managing different deep learning models within the yield estimation pipeline.
The factory pattern decouples the model creation logic from the main training
script, making it easy to switch between different architectures and task types
(detection, segmentation, regression) by simply changing a configuration parameter.

Core Responsibilities:
----------------------
1.  **Centralized Model Instantiation**:
    -   Provides a single entry point, `create_model`, to get a model instance
      based on its name and task type.
    -   This avoids `if/elif/else` blocks for model selection in the training code,
      leading to cleaner and more maintainable scripts.

2.  **Dynamic Model Loading**:
    -   The factory can dynamically import and instantiate model classes from
      other files within the `models` sub-package (e.g., `detection_models.py`,
      `segmentation_models.py`). This makes the factory extensible without
      requiring modifications to its own code.

3.  **Configuration-driven Creation**:
    -   It takes a `ModelConfig` object (from `utils.config`) as input. This
      object contains all the necessary hyperparameters for the model, such as
      the number of classes, backbone architecture, and pre-trained status.
    -   This ensures that models are always created with the correct, centrally
      managed configuration.

4.  **Pre-trained Weight Handling**:
    -   The factory logic can handle the loading of pre-trained weights, either
      from a public repository (like ImageNet) or from a local checkpoint file.
      This is essential for transfer learning, which significantly speeds up
      training and improves performance.

Structure:
----------
-   **`ModelFactory` Class**:
    -   `__init__`: Initializes the factory, potentially pre-loading information
      about available models.
    -   `create_model`: The main method. It takes a `ModelConfig` and a task type,
      and returns an initialized `torch.nn.Module` model. It contains the logic
      to select the correct model builder function based on the configuration.

Example Usage:
--------------
```python
from app.computer_vision.yield_estimation.utils.config import get_settings
from app.computer_vision.yield_estimation.models.factory import ModelFactory

# 1. Get model configuration from global settings
settings = get_settings()
detection_config = settings.models['default_detection']

# 2. Create the factory
factory = ModelFactory()

# 3. Create a model instance
detection_model = factory.create_model(
    task_type='detection',
    model_config=detection_config
)

# The model is now ready to be trained.
```
This factory is a key component for building a flexible and scalable MLOps
pipeline, allowing for rapid experimentation with different model architectures.
"""

import torch.nn as nn
from typing import Literal

from app.computer_vision.yield_estimation.utils.config import ModelConfig, DetectionModelConfig, SegmentationModelConfig, RegressionModelConfig
from .detection_models import create_detection_model
from .segmentation_models import create_segmentation_model
from .regression_models import create_regression_model
import logging

logger = logging.getLogger(__name__)

class ModelFactory:
    """
    A factory class to create yield estimation models based on configuration.
    """
    def __init__(self):
        self.model_builders = {
            'detection': create_detection_model,
            'segmentation': create_segmentation_model,
            'regression': create_regression_model,
        }
        logger.info(f"ModelFactory initialized with builders for: {list(self.model_builders.keys())}")

    def create_model(self, 
                     task_type: Literal['detection', 'segmentation', 'regression'], 
                     model_config: ModelConfig,
                     pretrained: bool = True) -> nn.Module:
        """
        Creates a model instance based on the task type and configuration.

        Args:
            task_type (str): The type of task the model is for.
            model_config (ModelConfig): The Pydantic model configuration object.
            pretrained (bool): Whether to load pre-trained weights.

        Returns:
            nn.Module: An initialized PyTorch model.
        """
        builder = self.model_builders.get(task_type)
        
        if builder is None:
            raise ValueError(f"Unsupported task type '{task_type}'. "
                             f"Available types are: {list(self.model_builders.keys())}")

        logger.info(f"Creating model for task '{task_type}' with config: {model_config.dict()}")
        
        # The builder function is responsible for interpreting its specific config
        model = builder(model_config, pretrained=pretrained)
        
        return model

# --- Example Usage ---
if __name__ == '__main__':
    from app.computer_vision.yield_estimation.utils.config import get_settings

    print("--- Model Factory Demo ---")

    # 1. Get settings and initialize factory
    settings = get_settings()
    factory = ModelFactory()

    # 2. Create a detection model
    print("\n[1. Creating a Detection Model]")
    try:
        detection_config = settings.models['default_detection']
        detection_config.name = 'faster_rcnn' # Specify which one
        detection_model = factory.create_model(task_type='detection', model_config=detection_config)
        print(f"  Successfully created model: {type(detection_model).__name__}")
        assert detection_model is not None
    except Exception as e:
        print(f"  Could not create detection model. This may be expected if torchvision is not installed. Error: {e}")


    # 3. Create a segmentation model
    print("\n[2. Creating a Segmentation Model]")
    try:
        segmentation_config = settings.models['default_segmentation']
        segmentation_config.name = 'unet'
        segmentation_model = factory.create_model(task_type='segmentation', model_config=segmentation_config)
        print(f"  Successfully created model: {type(segmentation_model).__name__}")
        assert segmentation_model is not None
    except Exception as e:
        print(f"  Could not create segmentation model. This may be expected if segmentation_models_pytorch is not installed. Error: {e}")


    # 4. Create a regression model
    print("\n[3. Creating a Regression Model]")
    try:
        regression_config = settings.models['default_regression']
        regression_config.name = 'cnn_regressor'
        regression_model = factory.create_model(task_type='regression', model_config=regression_config)
        print(f"  Successfully created model: {type(regression_model).__name__}")
        assert regression_model is not None
    except Exception as e:
        print(f"  Could not create regression model. Error: {e}")

    # 5. Test invalid task type
    print("\n[4. Testing Invalid Task Type]")
    try:
        factory.create_model(task_type='invalid_task', model_config=detection_config)
    except ValueError as e:
        print(f"  Successfully caught expected error: {e}")

    print("\nModel factory demo finished.")
