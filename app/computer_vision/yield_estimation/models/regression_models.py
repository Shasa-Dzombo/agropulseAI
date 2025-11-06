"""
Direct Regression Models for Yield Estimation
=============================================

This module provides implementations of deep learning models designed for direct
yield regression. Instead of counting objects or measuring area, these models
take an entire image (or features extracted from it) and directly predict a
continuous yield value (e.g., tons per hectare, bushels per acre).

This approach is useful when:
-   Individual objects (like fruits) are too small or numerous to count reliably.
-   Yield is a complex function of overall plot health, density, and other visual
    cues that are hard to model with detection or segmentation alone.
-   Multi-modal data (e.g., RGB, weather data, soil data) needs to be fused to
    make a prediction.

Core Components:
----------------
1.  **`CNNRegressor`**:
    -   A standard Convolutional Neural Network (CNN) architecture adapted for
      regression.
    -   It uses a pre-trained CNN backbone (like ResNet or EfficientNet) as a
      powerful feature extractor.
    -   The classification head of the pre-trained model is replaced with a new
      regression head, typically consisting of a few fully connected layers,
      dropout for regularization, and a single output neuron that predicts the
      yield value.
    -   This model is ideal for predicting yield from a single image.

2.  **`MultiModalRegressor` (Conceptual)**:
    -   A more advanced architecture designed to fuse features from different
      data sources.
    -   It might have separate processing streams (e.g., a CNN for images, an MLP
      for tabular data like weather and soil measurements).
    -   The features from these streams are then concatenated and passed through
      a final set of layers to produce the yield prediction.
    -   This module provides a basic structure for such a model, which can be
      expanded upon.

3.  **`create_regression_model` Function**:
    -   The factory function that instantiates the appropriate regression model
      based on the provided `RegressionModelConfig`.

This module provides the tools to tackle yield estimation as a direct regression
problem, offering a powerful alternative or complement to counting- and
segmentation-based methods.
"""

import torch
import torch.nn as nn
from torchvision import models
import logging

from app.computer_vision.yield_estimation.utils.config import RegressionModelConfig

logger = logging.getLogger(__name__)

class CNNRegressor(nn.Module):
    """
    A CNN-based regression model that uses a pre-trained backbone for feature
    extraction and a custom head for predicting a single continuous value.
    """
    def __init__(self, backbone_name: str = 'resnet50', pretrained: bool = True, dropout_rate: float = 0.5):
        """
        Args:
            backbone_name (str): The name of the torchvision model to use as a backbone.
            pretrained (bool): If True, loads pre-trained ImageNet weights.
            dropout_rate (float): The dropout probability for the regression head.
        """
        super().__init__()
        
        # Load the pre-trained backbone
        if backbone_name == 'resnet50':
            self.backbone = models.resnet50(pretrained=pretrained)
            num_ftrs = self.backbone.fc.in_features
            # Replace the final classification layer
            self.backbone.fc = nn.Identity()
        elif backbone_name == 'efficientnet_b0':
            self.backbone = models.efficientnet_b0(pretrained=pretrained)
            num_ftrs = self.backbone.classifier[1].in_features
            self.backbone.classifier = nn.Identity()
        else:
            raise NotImplementedError(f"Backbone '{backbone_name}' is not supported.")

        # Define the regression head
        self.regression_head = nn.Sequential(
            nn.Linear(num_ftrs, 512),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(256, 1) # Single output for yield value
        )
        
        logger.info(f"CNNRegressor created with backbone '{backbone_name}' and dropout {dropout_rate}.")

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass of the model.

        Args:
            x (torch.Tensor): Input image tensor of shape (N, C, H, W).

        Returns:
            torch.Tensor: Predicted yield value(s) of shape (N, 1).
        """
        # The input `x` is expected to be a dictionary from the dataloader,
        # containing different modalities. We'll assume 'rgb' is the primary one.
        if isinstance(x, dict):
            x = x['rgb']
            
        features = self.backbone(x)
        output = self.regression_head(features)
        return output

# --- Factory Function ---

def create_regression_model(config: RegressionModelConfig, pretrained: bool = True) -> nn.Module:
    """
    Factory function to create a regression model based on the config.

    Args:
        config (RegressionModelConfig): The model configuration.
        pretrained (bool): Whether to use pre-trained weights for the backbone.

    Returns:
        nn.Module: The created regression model.
    """
    model_name = config.name
    
    if model_name == 'cnn_regressor':
        # A more advanced implementation could select the backbone from the config
        return CNNRegressor(
            backbone_name='resnet50', 
            pretrained=pretrained,
            dropout_rate=config.dropout_rate
        )
    # Add other models like 'multimodal_regressor' here
    # elif model_name == 'multimodal_regressor':
    #     return MultiModalRegressor(...)
    else:
        raise NotImplementedError(f"Regression model '{model_name}' is not supported. "
                                  "Supported models are: 'cnn_regressor'.")

# --- Example Usage ---
if __name__ == '__main__':
    print("--- Regression Models Demo ---")

    # 1. Create a config for a CNN Regressor
    reg_config = RegressionModelConfig(
        name='cnn_regressor',
        input_features=3,
        dropout_rate=0.4
    )

    # 2. Create the model
    print("\n[1. Creating CNNRegressor model]")
    try:
        reg_model = create_regression_model(reg_config, pretrained=True)
        print(f"  Model created: {type(reg_model)}")
        assert reg_model is not None
    except Exception as e:
        print(f"  Could not create model. Is torchvision installed? Error: {e}")

    # 3. Test the forward pass
    print("\n[2. Testing forward pass]")
    if 'reg_model' in locals():
        # Create a dummy input batch (batch size 4, 3 channels, 224x224)
        # The dict simulates the output of our custom dataloader
        dummy_input = {'rgb': torch.randn(4, 3, 224, 224)}
        
        output = reg_model(dummy_input)
        
        print(f"  Input shape: {dummy_input['rgb'].shape}")
        print(f"  Output shape: {output.shape}")
        print(f"  Output values: {output.squeeze().tolist()}")
        
        # The output should be (batch_size, 1)
        assert output.shape == (4, 1)
        
        print("  Forward pass successful.")

    print("\nRegression models demo finished successfully.")
