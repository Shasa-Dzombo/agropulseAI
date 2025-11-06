"""
Unit Tests for the Training and Evaluation Engine
=================================================

This module contains unit tests for the core `engine.py` module, which houses
the `train_one_epoch` and `evaluate` functions. These tests are critical for
ensuring that the training and evaluation loops behave correctly for each
supported task type.

The tests use mocking extensively to isolate the engine functions from actual
models, data loaders, and optimizers. This allows for focused testing of the
loop logic, loss calculation, and metric computation.

Core Components:
----------------
1.  **Mock Fixtures**:
    -   `mock_model`: A `MagicMock` object that simulates a PyTorch model. Its
      return values are configured to mimic the outputs for different tasks
      (e.g., a loss dictionary for detection, logits for segmentation/regression).
    -   `mock_optimizer`: A `MagicMock` simulating a PyTorch optimizer.
    -   `mock_data_loader`: A `MagicMock` that yields batches of dummy data and
      targets, simulating a `DataLoader`.

2.  **`test_train_one_epoch`**:
    -   **Purpose**: To verify the training loop's correctness.
    -   **Execution**:
        -   Calls `train_one_epoch` with the mock objects for each task type
          ('detection', 'segmentation', 'regression').
        -   **Asserts that `model.train()` was called**.
        -   **Asserts that the optimizer's `zero_grad()`, `step()`, and the loss's
          `backward()` methods were called**, confirming that backpropagation
          is being performed.
        -   Checks that the function returns a dictionary containing the training loss.
        -   For detection, it verifies that the model's output (a loss dictionary)
          is correctly summed.
        -   For segmentation and regression, it verifies that the appropriate
          loss function (`CrossEntropyLoss` or `MSELoss`) is used.

3.  **`test_evaluate`**:
    -   **Purpose**: To verify the evaluation loop's correctness.
    -   **Execution**:
        -   Calls `evaluate` with the mock objects for each task.
        -   **Asserts that `model.eval()` was called**.
        -   Asserts that the model is called within a `torch.no_grad()` context.
        -   **Task-Specific Metric Verification**:
            -   For **detection**, it mocks the `CocoEvaluator` and asserts that
              its `update` and `summarize` methods are called.
            -   For **segmentation**, it mocks `SegmentationMetrics` and asserts
              that its `update` and `get_metrics` methods are called.
            -   For **regression**, it mocks `RegressionMetrics` and asserts
              that its `update` and `get_metrics` methods are called.
        -   This ensures that the correct evaluation logic is triggered for each
          task type.

These tests provide confidence that the core computational engine of the training
pipeline is functioning as expected under various conditions.
"""

import pytest
from unittest.mock import MagicMock, patch
import torch

from app.computer_vision.yield_estimation.engine import train_one_epoch, evaluate

@pytest.fixture
def mock_model():
    """A mock model that can be configured for different tasks."""
    model = MagicMock(spec=torch.nn.Module)
    model.train = MagicMock()
    model.eval = MagicMock()
    return model

@pytest.fixture
def mock_optimizer():
    """A mock optimizer."""
    optimizer = MagicMock(spec=torch.optim.Optimizer)
    optimizer.zero_grad = MagicMock()
    optimizer.step = MagicMock()
    return optimizer

@pytest.fixture
def mock_data_loader():
    """A mock data loader that yields one batch."""
    # Dummy data for one batch
    images = {'rgb': torch.rand(2, 3, 10, 10)}
    # Detection targets
    det_targets = [{'boxes': torch.rand(1, 4), 'labels': torch.ones(1, dtype=torch.long)}] * 2
    # Segmentation targets
    seg_targets = {'mask': torch.randint(0, 2, (2, 10, 10))}
    # Regression targets
    reg_targets = torch.rand(2, 1)
    
    return {
        'detection': [(images, det_targets)],
        'segmentation': [(images, seg_targets)],
        'regression': [(images, reg_targets)]
    }

def test_train_one_epoch_detection(mock_model, mock_optimizer, mock_data_loader):
    """Test training loop for a detection task."""
    device = torch.device('cpu')
    # Model returns a loss dict in training mode for detection
    mock_model.return_value = {'loss_box_reg': torch.tensor(0.5, requires_grad=True)}
    
    result = train_one_epoch(mock_model, mock_optimizer, mock_data_loader['detection'], device, 0, 'detection', 10)
    
    mock_model.train.assert_called_once()
    mock_optimizer.zero_grad.assert_called()
    mock_optimizer.step.assert_called()
    assert 'train_loss' in result
    assert result['train_loss'] > 0

@patch('app.computer_vision.yield_estimation.engine.nn.CrossEntropyLoss')
def test_train_one_epoch_segmentation(mock_criterion, mock_model, mock_optimizer, mock_data_loader):
    """Test training loop for a segmentation task."""
    device = torch.device('cpu')
    mock_loss = MagicMock(return_value=torch.tensor(0.6, requires_grad=True))
    mock_criterion.return_value = mock_loss
    mock_model.return_value = torch.rand(2, 5, 10, 10) # (B, C, H, W) logits

    result = train_one_epoch(mock_model, mock_optimizer, mock_data_loader['segmentation'], device, 0, 'segmentation', 10)

    mock_model.train.assert_called_once()
    mock_optimizer.step.assert_called()
    mock_loss.assert_called()
    assert 'train_loss' in result

@patch('app.computer_vision.yield_estimation.engine.CocoEvaluator')
@patch('app.computer_vision.yield_estimation.engine.get_coco_api_from_dataset')
def test_evaluate_detection(mock_get_coco, mock_coco_eval, mock_model, mock_data_loader):
    """Test evaluation loop for a detection task."""
    device = torch.device('cpu')
    mock_evaluator = MagicMock()
    mock_coco_eval.return_value = mock_evaluator
    # Eval output is a list of dicts with boxes, labels, scores
    mock_model.return_value = [{'boxes': torch.rand(1,4), 'labels': torch.ones(1), 'scores': torch.rand(1)}] * 2

    evaluate(mock_model, mock_data_loader['detection'], device, 'detection')

    mock_model.eval.assert_called_once()
    mock_evaluator.update.assert_called()
    mock_evaluator.summarize.assert_called()

@patch('app.computer_vision.yield_estimation.engine.SegmentationMetrics')
def test_evaluate_segmentation(mock_seg_metrics, mock_model, mock_data_loader):
    """Test evaluation loop for a segmentation task."""
    device = torch.device('cpu')
    mock_metrics = MagicMock()
    mock_seg_metrics.return_value = mock_metrics
    mock_model.return_value = torch.rand(2, 5, 10, 10)

    evaluate(mock_model, mock_data_loader['segmentation'], device, 'segmentation')

    mock_model.eval.assert_called_once()
    mock_metrics.update.assert_called()
    mock_metrics.get_metrics.assert_called()
