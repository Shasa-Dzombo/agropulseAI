"""
Unit Tests for Model Creation and Forward Pass
===============================================

This module contains unit tests for the model-related components of the yield
estimation module, focusing on the `ModelFactory` and the basic functionality
of the created models.

The tests ensure that the factory can correctly instantiate models for each
supported task and that these models can perform a forward pass with dummy data
of the correct shape. This validates the model architecture and the connections
between layers.

Core Tests:
-----------
1.  **`test_model_factory_detection`**:
    -   **Purpose**: To verify that the `ModelFactory` can create a detection model.
    -   **Setup**:
        -   Creates a `DetectionModelConfig` with parameters for a detection model
          (e.g., `fasterrcnn_resnet50_fpn`).
        -   Instantiates the `ModelFactory`.
    -   **Execution**:
        -   Calls `factory.create_model` with `task_type='detection'`.
        -   Asserts that the returned model is an instance of `torch.nn.Module`.
        -   Creates a dummy input tensor with the shape `(batch, channels, height, width)`.
        -   Performs a forward pass (`model(dummy_input)`).
        -   Asserts that the model output is in the expected format for detection
          (a list of dictionaries containing 'boxes', 'labels', 'scores').

2.  **`test_model_factory_segmentation`**:
    -   **Purpose**: To verify that the `ModelFactory` can create a segmentation model.
    -   **Setup**:
        -   Creates a `SegmentationModelConfig` for a segmentation model (e.g., `unet`).
    -   **Execution**:
        -   Calls `factory.create_model` with `task_type='segmentation'`.
        -   Asserts that the model is a `torch.nn.Module`.
        -   Creates a dummy input tensor.
        -   Performs a forward pass.
        -   Asserts that the output tensor has the expected shape for a segmentation
          mask: `(batch, num_classes, height, width)`.

3.  **`test_model_factory_regression`**:
    -   **Purpose**: To verify that the `ModelFactory` can create a regression model.
    -   **Setup**:
        -   Creates a `RegressionModelConfig` for a regression model (e.g., `cnn_regressor`).
    -   **Execution**:
        -   Calls `factory.create_model` with `task_type='regression'`.
        -   Asserts that the model is a `torch.nn.Module`.
        -   Creates a dummy input tensor.
        -   Performs a forward pass.
        -   Asserts that the output tensor has the expected shape for a regression
          task: `(batch, 1)`.

These tests provide a crucial sanity check that the model architectures are
correctly defined and that the factory pattern works as expected, allowing for
flexible model selection during training and inference.
"""

import pytest
import torch

from app.computer_vision.yield_estimation.models.factory import ModelFactory
from app.computer_vision.yield_estimation.utils.config import (
    DetectionModelConfig, SegmentationModelConfig, RegressionModelConfig
)

@pytest.fixture
def factory():
    return ModelFactory()

def test_model_factory_detection(factory):
    """Test creating a detection model."""
    config = DetectionModelConfig(
        name="fasterrcnn_resnet50_fpn",
        num_classes=5,
        confidence_threshold=0.5
    )
    model = factory.create_model(task_type='detection', model_config=config, pretrained=False)
    assert isinstance(model, torch.nn.Module)

    # Test forward pass with a dummy input
    dummy_input = [torch.rand(3, 256, 256)]
    model.eval() # Set to eval mode for prediction output format
    output = model(dummy_input)
    
    assert isinstance(output, list)
    assert isinstance(output[0], dict)
    assert 'boxes' in output[0]
    assert 'labels' in output[0]
    assert 'scores' in output[0]

def test_model_factory_segmentation(factory):
    """Test creating a segmentation model."""
    config = SegmentationModelConfig(
        name="unet",
        encoder_name="resnet34",
        encoder_weights="imagenet",
        in_channels=3,
        num_classes=5
    )
    model = factory.create_model(task_type='segmentation', model_config=config)
    assert isinstance(model, torch.nn.Module)

    # Test forward pass with a dummy input
    dummy_input = {'rgb': torch.rand(1, 3, 256, 256)}
    output = model(dummy_input)
    
    assert isinstance(output, torch.Tensor)
    assert output.shape == (1, config.num_classes, 256, 256)

def test_model_factory_regression(factory):
    """Test creating a regression model."""
    config = RegressionModelConfig(
        name="cnn_regressor",
        backbone="resnet18",
        in_channels=3,
        dropout_rate=0.5
    )
    model = factory.create_model(task_type='regression', model_config=config)
    assert isinstance(model, torch.nn.Module)

    # Test forward pass with a dummy input
    dummy_input = {'rgb': torch.rand(1, 3, 256, 256)}
    output = model(dummy_input)
    
    assert isinstance(output, torch.Tensor)
    assert output.shape == (1, 1)

def test_factory_invalid_task(factory):
    """Test that the factory raises an error for an invalid task type."""
    with pytest.raises(ValueError):
        factory.create_model(task_type='invalid_task', model_config=None)
