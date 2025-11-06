"""
Unit Tests for Data Loading and Processing
==========================================

This module contains unit tests for the data-related components of the yield
estimation module, including the `YieldDataset`, data augmentations, and the
`create_dataloaders` function.

The tests are designed to run without requiring a real dataset on disk. Instead,
they use `pytest`'s `tmp_path` fixture to create temporary directories and dummy
data files (images, masks, and annotation files) on the fly. This makes the
tests self-contained, fast, and reliable.

Core Tests:
-----------
1.  **`test_yield_dataset`**:
    -   **Purpose**: To verify that the `YieldDataset` class can correctly load
      and parse data for all supported tasks (detection, segmentation, regression).
    -   **Setup**:
        -   Creates a temporary directory structure for a mock dataset.
        -   Generates dummy PNG images for RGB and NIR modalities.
        -   Generates a dummy segmentation mask.
        -   Creates a `coco.json` file for detection annotations.
        -   Creates a `regression.csv` file for regression targets.
    -   **Execution**:
        -   Initializes `YieldDataset` for each task type.
        -   Asserts that the dataset has the correct length.
        -   Retrieves a sample from the dataset.
        -   Asserts that the sample has the correct structure and data types
          for each task (e.g., 'boxes' and 'labels' for detection, 'mask' for
          segmentation, a float tensor for regression).

2.  **`test_create_dataloaders`**:
    -   **Purpose**: To ensure that the `create_dataloaders` function correctly
      builds `DataLoader` instances for training, validation, and testing.
    -   **Setup**:
        -   Uses the same mock dataset setup as `test_yield_dataset`.
        -   Uses a mock `Settings` object to configure the data loaders.
    -   **Execution**:
        -   Calls `create_dataloaders`.
        -   Asserts that the function returns a dictionary containing 'train',
          'val', and 'test' loaders.
        -   Retrieves a batch from the 'train' loader.
        -   Asserts that the batch has the correct structure and that the tensors
          have the expected shapes, confirming that batching works correctly.

These tests ensure that the data pipeline is robust and can handle the different
data formats and task requirements, which is fundamental to the success of the
entire modeling process.
"""

import pytest
import numpy as np
import cv2
import json
import pandas as pd
from torch.utils.data import DataLoader

from app.computer_vision.yield_estimation.utils.config import get_settings, Settings
from app.computer_vision.yield_estimation.data.dataset import YieldDataset
from app.computer_vision.yield_estimation.data.loader import create_dataloaders

@pytest.fixture
def mock_dataset_path(tmp_path):
    """Creates a temporary directory structure with dummy data for testing."""
    # Root directories
    data_root = tmp_path / "data"
    data_root.mkdir()
    
    # Subdirectories for different data types
    (data_root / "rgb").mkdir()
    (data_root / "nir").mkdir()
    (data_root / "masks").mkdir()
    
    # Create dummy image files (10x10 pixels)
    dummy_image_rgb = np.random.randint(0, 256, (10, 10, 3), dtype=np.uint8)
    dummy_image_nir = np.random.randint(0, 256, (10, 10, 1), dtype=np.uint8)
    cv2.imwrite(str(data_root / "rgb" / "sample1.png"), dummy_image_rgb)
    cv2.imwrite(str(data_root / "nir" / "sample1.png"), dummy_image_nir)

    # Create dummy mask file
    dummy_mask = np.zeros((10, 10), dtype=np.uint8)
    dummy_mask[2:5, 2:8] = 1 # Class 1
    cv2.imwrite(str(data_root / "masks" / "sample1.png"), dummy_mask)

    # Create dummy COCO annotation file for detection
    coco_annotations = {
        "images": [{"id": 1, "file_name": "sample1.png", "height": 10, "width": 10}],
        "annotations": [{"id": 1, "image_id": 1, "category_id": 1, "bbox": [2, 2, 6, 3], "area": 18, "iscrowd": 0}],
        "categories": [{"id": 1, "name": "fruit"}]
    }
    with open(data_root / "coco.json", "w") as f:
        json.dump(coco_annotations, f)

    # Create dummy CSV for regression
    regression_data = {"image_name": ["sample1.png"], "yield": [123.45]}
    pd.DataFrame(regression_data).to_csv(data_root / "regression.csv", index=False)

    return data_root

@pytest.fixture
def mock_settings(mock_dataset_path):
    """Overrides the default settings to use the mock dataset."""
    settings = get_settings()
    settings.data.data_path = str(mock_dataset_path)
    settings.data.annotation_file = str(mock_dataset_path / "coco.json")
    settings.data.regression_file = str(mock_dataset_path / "regression.csv")
    settings.data.mask_dir = str(mock_dataset_path / "masks")
    settings.data.image_sets = {
        "train": ["sample1"],
        "val": ["sample1"],
        "test": ["sample1"]
    }
    return settings

def test_yield_dataset_detection(mock_settings):
    """Test the YieldDataset for a detection task."""
    dataset = YieldDataset(settings=mock_settings, image_set="train", task="detection", modalities=["rgb"])
    assert len(dataset) == 1
    
    image, target = dataset[0]
    assert "rgb" in image
    assert "boxes" in target
    assert "labels" in target
    assert target['boxes'].shape == (1, 4)

def test_yield_dataset_segmentation(mock_settings):
    """Test the YieldDataset for a segmentation task."""
    dataset = YieldDataset(settings=mock_settings, image_set="train", task="segmentation", modalities=["rgb"])
    assert len(dataset) == 1
    
    image, target = dataset[0]
    assert "rgb" in image
    assert "mask" in target
    assert target['mask'].shape == (10, 10)
    assert np.sum(target['mask']) > 0

def test_yield_dataset_regression(mock_settings):
    """Test the YieldDataset for a regression task."""
    dataset = YieldDataset(settings=mock_settings, image_set="train", task="regression", modalities=["rgb"])
    assert len(dataset) == 1
    
    image, target = dataset[0]
    assert "rgb" in image
    assert isinstance(target.item(), float)
    assert target.item() == 123.45

def test_create_dataloaders(mock_settings):
    """Test the create_dataloaders function."""
    mock_settings.train.batch_size = 1
    dataloaders = create_dataloaders(mock_settings, task="detection", modalities=["rgb"])
    
    assert "train" in dataloaders
    assert "val" in dataloaders
    assert "test" in dataloaders
    
    train_loader = dataloaders['train']
    assert isinstance(train_loader, DataLoader)
    
    images, targets = next(iter(train_loader))
    assert "rgb" in images
    assert images['rgb'].shape == (1, 3, mock_settings.data.image_size[0], mock_settings.data.image_size[1])
    assert len(targets) == 1
    assert "boxes" in targets[0]
