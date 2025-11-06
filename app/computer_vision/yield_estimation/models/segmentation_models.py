"""
Image Segmentation Models for Yield Estimation
==============================================

This module provides implementations of semantic segmentation models, which are
used for yield estimation tasks where the goal is to measure area or biomass.
For example, estimating the yield of leafy greens or forage crops can be done by
segmenting the canopy area in an image and correlating it with yield.

This module uses the excellent `segmentation-models-pytorch` library, which
provides a wide range of pre-trained segmentation architectures with various
encoder backbones. This allows for rapid experimentation and high performance.

Core Components:
----------------
1.  **`create_segmentation_model` Function**:
    -   The main factory function for creating segmentation models.
    -   It takes a `SegmentationModelConfig` object, which specifies the model
      architecture (e.g., 'unet', 'deeplabv3+'), the encoder backbone (e.g.,
      'resnet50'), pre-trained weights for the encoder (e.g., 'imagenet'), and
      the number of output classes (e.g., background, crop_type_1, crop_type_2).
    -   It dynamically creates the specified model using the `smp` library.

2.  **Supported Architectures**:
    -   **U-Net**: A very popular and effective architecture for biomedical image
      segmentation, which also works exceptionally well for agricultural scenes.
      It has a symmetric encoder-decoder structure with skip connections that
      help preserve high-resolution spatial information.
    -   **DeepLabV3+**: A state-of-the-art model that uses Atrous (dilated)
      convolutions to capture multi-scale context and an effective
      encoder-decoder structure. It is known for producing highly accurate
      segmentation maps.

Dependencies:
-------------
-   **segmentation-models-pytorch**: This library is a prerequisite. It can be
    installed via pip: `pip install segmentation-models-pytorch`.
-   **timm**: `smp` depends on `timm` for a wide selection of encoder backbones.

This module abstracts away the complexity of building these models from scratch,
providing a simple, configuration-driven way to instantiate powerful segmentation
models for yield estimation.
"""

import torch.nn as nn
import logging

from app.computer_vision.yield_estimation.utils.config import SegmentationModelConfig

# Attempt to import segmentation_models_pytorch
try:
    import segmentation_models_pytorch as smp
except ImportError:
    smp = None
    # A warning will be logged by the function if the library is needed.

logger = logging.getLogger(__name__)

def create_segmentation_model(config: SegmentationModelConfig, pretrained: bool = True) -> nn.Module:
    """
    Factory function to create a semantic segmentation model using segmentation-models-pytorch.

    Args:
        config (SegmentationModelConfig): The model configuration.
        pretrained (bool): If True, uses pre-trained weights for the encoder.
                           Note: `smp` uses the `encoder_weights` field from the config.

    Returns:
        nn.Module: The created segmentation model.
    """
    if smp is None:
        logger.error("The 'segmentation-models-pytorch' library is required for segmentation tasks.")
        raise ImportError("Please install it via: pip install segmentation-models-pytorch")

    model_name = config.name
    encoder_weights = config.encoder_weights if pretrained else None

    if model_name == 'unet':
        model = smp.Unet(
            encoder_name=config.encoder_name,
            encoder_weights=encoder_weights,
            in_channels=3,  # Assuming RGB input, can be made configurable
            classes=config.num_classes,
        )
        logger.info(f"Created U-Net model with encoder '{config.encoder_name}' and {config.num_classes} classes.")
    elif model_name == 'deeplabv3+':
        model = smp.DeepLabV3Plus(
            encoder_name=config.encoder_name,
            encoder_weights=encoder_weights,
            in_channels=3,
            classes=config.num_classes,
        )
        logger.info(f"Created DeepLabV3+ model with encoder '{config.encoder_name}' and {config.num_classes} classes.")
    else:
        raise NotImplementedError(f"Segmentation model '{model_name}' is not supported. "
                                  "Supported models are: 'unet', 'deeplabv3+'.")
    
    return model

# --- Example Usage ---
if __name__ == '__main__':
    print("--- Segmentation Models Demo ---")

    if smp is None:
        print("\nSkipping demo because 'segmentation-models-pytorch' is not installed.")
        print("Please run: pip install segmentation-models-pytorch")
    else:
        # 1. Create a config for a U-Net model
        unet_config = SegmentationModelConfig(
            name='unet',
            num_classes=5,  # e.g., background, soil, crop1, crop2, weed
            encoder_name='resnet34',
            encoder_weights='imagenet'
        )

        # 2. Create the model
        print("\n[1. Creating U-Net model]")
        try:
            unet_model = create_segmentation_model(unet_config, pretrained=True)
            print(f"  Model created: {type(unet_model)}")
            # Verify the output channels of the segmentation head
            final_channels = unet_model.segmentation_head[0].out_channels
            print(f"  Final layer output channels: {final_channels}")
            assert final_channels == 5
        except Exception as e:
            print(f"  An error occurred: {e}")

        # 3. Create a config for a DeepLabV3+ model
        deeplab_config = SegmentationModelConfig(
            name='deeplabv3+',
            num_classes=3,
            encoder_name='timm-efficientnet-b0',
            encoder_weights='imagenet'
        )

        # 4. Create the model
        print("\n[2. Creating DeepLabV3+ model]")
        try:
            deeplab_model = create_segmentation_model(deeplab_config, pretrained=True)
            print(f"  Model created: {type(deeplab_model)}")
            final_channels = deeplab_model.segmentation_head[0].out_channels
            print(f"  Final layer output channels: {final_channels}")
            assert final_channels == 3
        except Exception as e:
            print(f"  An error occurred: {e}")

        print("\nSegmentation models demo finished successfully.")
