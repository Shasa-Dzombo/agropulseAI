# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\crop_health_assessment\models.py

"""
Models for Crop Health Assessment
=================================

This module defines the machine learning and deep learning models used for
assessing crop health. The models are designed to work with the processed data
from the `data_processing` module, which can be in the form of:
1.  **Tabular Spectral Data**: A set of spectral bands or vegetation indices for
    a given point or zone, used to predict a single health metric (e.g.,
    nitrogen content, stress level).
2.  **Hyperspectral Signatures**: A 1D vector representing the full spectral
    reflectance curve for a pixel.
3.  **Image Patches (Data Cubes)**: Small 2D or 3D patches of multispectral or
    hyperspectral imagery.

The module provides a flexible `HealthModelFactory` to instantiate different
types of models based on a configuration dictionary.

Model Categories:
-----------------
1.  **Classical Machine Learning Models**:
    -   These models are suitable for tabular data (e.g., zonal statistics or
      pixel-based spectral features).
    -   They are implemented using `scikit-learn` and include robust options
      like Gradient Boosting, Random Forest, and Support Vector Machines.
    -   Partial Least Squares (PLS) Regression is also included, as it is a
      standard and powerful technique for chemometrics and spectral analysis.

2.  **1D Deep Learning Models for Spectral Signatures**:
    -   These models are designed to process entire spectral signatures (1D vectors)
      and are effective at learning patterns from hyperspectral data.
    -   A generic `SpectralCNN1D` is implemented, which uses 1D convolutional
      layers to extract features along the spectral dimension.

3.  **2D/3D Deep Learning Models for Image Patches**:
    -   These models work with small image patches (data cubes) and can capture
      both spectral and spatial patterns.
    -   A `SpectralCNN3D` model is provided, which uses 3D convolutions to process
      the (height, width, bands) cube simultaneously. This is computationally
      intensive but powerful.
    -   A `HybridCNN` model that combines 2D spatial convolutions with 1D spectral
      convolutions is also included as a more efficient alternative.

Core Components:
----------------
-   `HealthModelFactory`: A factory class that creates a model instance based on
  a name and configuration. This allows for easy experimentation by simply
  changing a config file.

-   **Scikit-learn Wrappers**: Simple wrappers around scikit-learn models to ensure
  a consistent interface.

-   **PyTorch Models**:
    -   `SpectralCNN1D`: A 1D CNN for processing spectral signatures.
    -   `SpectralCNN3D`: A 3D CNN for processing hyperspectral data cubes.
    -   `HybridCNN`: A model combining 2D and 1D convolutions.

The choice of model depends heavily on the nature of the input data and the
specific crop health problem being addressed.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Any, List

# Scikit-learn models for tabular data
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.svm import SVR
from sklearn.cross_decomposition import PLSRegression
from sklearn.base import BaseEstimator

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- PyTorch Deep Learning Models ---

class SpectralCNN1D(nn.Module):
    """
    A 1D Convolutional Neural Network for processing spectral signatures.
    This is ideal for hyperspectral data where each sample is a 1D vector of
    reflectance values across many narrow bands.
    """
    def __init__(self, input_bands: int, num_outputs: int = 1, task: str = 'regression'):
        super().__init__()
        self.input_bands = input_bands
        self.num_outputs = num_outputs
        self.task = task

        self.conv_block1 = nn.Sequential(
            nn.Conv1d(1, 16, kernel_size=7, padding=3),
            nn.BatchNorm1d(16),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=2, stride=2)
        )
        
        self.conv_block2 = nn.Sequential(
            nn.Conv1d(16, 32, kernel_size=5, padding=2),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=2, stride=2)
        )
        
        self.conv_block3 = nn.Sequential(
            nn.Conv1d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=2, stride=2)
        )
        
        # Calculate the flattened size dynamically
        dummy_input = torch.randn(1, 1, input_bands)
        flattened_size = self._get_flattened_size(dummy_input)
        
        self.fc_block = nn.Sequential(
            nn.Linear(flattened_size, 128),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, num_outputs)
        )
        
        logging.info(f"Initialized 1D Spectral CNN with flattened size {flattened_size}.")

    def _get_flattened_size(self, x: torch.Tensor) -> int:
        x = self.conv_block1(x)
        x = self.conv_block2(x)
        x = self.conv_block3(x)
        return x.numel()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Input shape: (batch_size, num_bands)
        # Add a channel dimension for Conv1D: (batch_size, 1, num_bands)
        x = x.unsqueeze(1)
        
        x = self.conv_block1(x)
        x = self.conv_block2(x)
        x = self.conv_block3(x)
        
        # Flatten for the fully connected layers
        x = x.view(x.size(0), -1)
        
        x = self.fc_block(x)
        
        if self.task == 'classification':
            # If multi-class, output raw logits for CrossEntropyLoss
            # If binary, could use sigmoid, but BCEWithLogitsLoss is preferred
            return x
        else: # regression
            return x.squeeze(-1) if self.num_outputs == 1 else x


class SpectralCNN3D(nn.Module):
    """
    A 3D Convolutional Neural Network for processing hyperspectral image patches (cubes).
    This model can capture both spatial and spectral patterns simultaneously.
    """
    def __init__(self, input_bands: int, patch_size: int, num_outputs: int = 1, task: str = 'regression'):
        super().__init__()
        self.input_bands = input_bands
        self.patch_size = patch_size
        self.num_outputs = num_outputs
        self.task = task

        # Kernel size is (depth, height, width)
        self.conv_block1 = nn.Sequential(
            nn.Conv3d(1, 16, kernel_size=(3, 3, 3), padding=1),
            nn.BatchNorm3d(16),
            nn.ReLU(),
            nn.MaxPool3d(kernel_size=(2, 2, 2), stride=2)
        )
        
        self.conv_block2 = nn.Sequential(
            nn.Conv3d(16, 32, kernel_size=(3, 3, 3), padding=1),
            nn.BatchNorm3d(32),
            nn.ReLU(),
            nn.MaxPool3d(kernel_size=(2, 2, 2), stride=2)
        )
        
        # Calculate flattened size
        dummy_input = torch.randn(1, 1, input_bands, patch_size, patch_size)
        flattened_size = self._get_flattened_size(dummy_input)
        
        self.fc_block = nn.Sequential(
            nn.Linear(flattened_size, 256),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, num_outputs)
        )
        
        logging.info(f"Initialized 3D Spectral CNN with flattened size {flattened_size}.")

    def _get_flattened_size(self, x: torch.Tensor) -> int:
        x = self.conv_block1(x)
        x = self.conv_block2(x)
        return x.numel()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Input shape: (batch_size, bands, height, width)
        # Add a channel dimension for Conv3D: (batch_size, 1, bands, height, width)
        x = x.unsqueeze(1)
        
        x = self.conv_block1(x)
        x = self.conv_block2(x)
        
        x = x.view(x.size(0), -1)
        x = self.fc_block(x)
        
        if self.task == 'classification':
            return x
        else:
            return x.squeeze(-1) if self.num_outputs == 1 else x


class HybridCNN(nn.Module):
    """
    A hybrid model that first applies 2D spatial convolutions across bands,
    then uses 1D convolutions to process the resulting spectral features.
    This is often more efficient than a full 3D CNN.
    """
    def __init__(self, input_bands: int, patch_size: int, num_outputs: int = 1, task: str = 'regression'):
        super().__init__()
        self.input_bands = input_bands
        self.patch_size = patch_size
        self.num_outputs = num_outputs
        self.task = task

        # Spatial feature extraction (2D convolutions)
        self.spatial_conv = nn.Sequential(
            nn.Conv2d(input_bands, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d(1) # Global average pooling to get one feature vector per patch
        )
        
        # Spectral feature extraction (1D convolutions)
        self.spectral_fc = nn.Sequential(
            nn.Linear(128, 256),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(256, num_outputs)
        )
        
        logging.info("Initialized Hybrid 2D+1D CNN.")

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Input shape: (batch_size, bands, height, width)
        
        # Apply spatial convolutions
        spatial_features = self.spatial_conv(x) # -> (batch_size, 128, 1, 1)
        
        # Squeeze to get a feature vector
        spatial_features = spatial_features.squeeze(-1).squeeze(-1) # -> (batch_size, 128)
        
        # Apply final classification/regression head
        output = self.spectral_fc(spatial_features)
        
        if self.task == 'classification':
            return output
        else:
            return output.squeeze(-1) if self.num_outputs == 1 else output


# --- Model Factory ---

class HealthModelFactory:
    """
    Factory class to create crop health assessment models.
    """
    _sklearn_models: Dict[str, BaseEstimator] = {
        'random_forest': RandomForestRegressor,
        'gradient_boosting': GradientBoostingRegressor,
        'svr': SVR,
        'pls': PLSRegression,
    }
    
    _pytorch_models: Dict[str, nn.Module] = {
        'spectral_cnn_1d': SpectralCNN1D,
        'spectral_cnn_3d': SpectralCNN3D,
        'hybrid_cnn': HybridCNN,
    }

    @staticmethod
    def create_model(config: Dict[str, Any]) -> Any:
        """
        Creates a model instance based on the provided configuration.

        Args:
            config (Dict[str, Any]): A dictionary containing model configuration.
                Must include 'name' and other model-specific parameters.
                Example for a PyTorch model:
                {
                    'name': 'spectral_cnn_1d',
                    'params': {'input_bands': 224, 'num_outputs': 1}
                }
                Example for an sklearn model:
                {
                    'name': 'random_forest',
                    'params': {'n_estimators': 100, 'max_depth': 10}
                }

        Returns:
            An instance of a scikit-learn model or a PyTorch nn.Module.
            
        Raises:
            ValueError: If the model name is not supported.
        """
        model_name = config.get('name', '').lower()
        params = config.get('params', {})

        logging.info(f"Creating model '{model_name}' with params: {params}")

        if model_name in HealthModelFactory._sklearn_models:
            model_class = HealthModelFactory._sklearn_models[model_name]
            return model_class(**params)
        
        elif model_name in HealthModelFactory._pytorch_models:
            model_class = HealthModelFactory._pytorch_models[model_name]
            return model_class(**params)
            
        else:
            supported = list(HealthModelFactory._sklearn_models.keys()) + \
                        list(HealthModelFactory._pytorch_models.keys())
            raise ValueError(f"Unsupported model name: '{model_name}'. "
                             f"Supported models are: {supported}")

# --- Example Usage ---
if __name__ == '__main__':
    print("--- Crop Health Model Factory Demo ---")

    # 1. Create a scikit-learn model (Random Forest)
    print("\n1. Creating scikit-learn Random Forest model...")
    rf_config = {'name': 'random_forest', 'params': {'n_estimators': 150, 'random_state': 42}}
    rf_model = HealthModelFactory.create_model(rf_config)
    print(f"  - Model created: {rf_model}")
    print(f"  - Parameters: {rf_model.get_params()}")

    # 2. Create a PLS Regression model
    print("\n2. Creating scikit-learn PLS Regression model...")
    pls_config = {'name': 'pls', 'params': {'n_components': 10}}
    pls_model = HealthModelFactory.create_model(pls_config)
    print(f"  - Model created: {pls_model}")

    # 3. Create a 1D Spectral CNN (PyTorch)
    print("\n3. Creating PyTorch 1D Spectral CNN...")
    cnn1d_config = {
        'name': 'spectral_cnn_1d',
        'params': {'input_bands': 200, 'num_outputs': 1, 'task': 'regression'}
    }
    cnn1d_model = HealthModelFactory.create_model(cnn1d_config)
    print(f"  - Model created: {cnn1d_model}")
    # Test with dummy data
    dummy_input_1d = torch.randn(4, 200) # Batch of 4 samples, 200 bands each
    output_1d = cnn1d_model(dummy_input_1d)
    print(f"  - Input shape: {dummy_input_1d.shape}")
    print(f"  - Output shape: {output_1d.shape}")

    # 4. Create a 3D Spectral CNN (PyTorch)
    print("\n4. Creating PyTorch 3D Spectral CNN...")
    cnn3d_config = {
        'name': 'spectral_cnn_3d',
        'params': {'input_bands': 100, 'patch_size': 16, 'num_outputs': 5, 'task': 'classification'}
    }
    cnn3d_model = HealthModelFactory.create_model(cnn3d_config)
    print(f"  - Model created: {cnn3d_model}")
    # Test with dummy data
    dummy_input_3d = torch.randn(2, 100, 16, 16) # Batch of 2 patches
    output_3d = cnn3d_model(dummy_input_3d)
    print(f"  - Input shape: {dummy_input_3d.shape}")
    print(f"  - Output shape: {output_3d.shape}")

    # 5. Create a Hybrid CNN (PyTorch)
    print("\n5. Creating PyTorch Hybrid CNN...")
    hybrid_config = {
        'name': 'hybrid_cnn',
        'params': {'input_bands': 50, 'patch_size': 32, 'num_outputs': 1}
    }
    hybrid_model = HealthModelFactory.create_model(hybrid_config)
    print(f"  - Model created: {hybrid_model}")
    # Test with dummy data
    dummy_input_hybrid = torch.randn(8, 50, 32, 32)
    output_hybrid = hybrid_model(dummy_input_hybrid)
    print(f"  - Input shape: {dummy_input_hybrid.shape}")
    print(f"  - Output shape: {output_hybrid.shape}")

    # 6. Test error handling for unsupported model
    print("\n6. Testing unsupported model name...")
    try:
        HealthModelFactory.create_model({'name': 'unsupported_model'})
    except ValueError as e:
        print(f"  - Successfully caught expected error: {e}")

```