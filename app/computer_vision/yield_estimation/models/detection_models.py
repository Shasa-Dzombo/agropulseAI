"""
Object Detection Models for Yield Estimation
============================================

This module provides implementations of various object detection models tailored
for yield estimation tasks, such as counting fruits, vegetables, or grain heads
in an image. It leverages pre-built models from `torchvision.models.detection`
and wraps them in a consistent creation function.

The primary goal is to provide a standardized way to instantiate different
detection architectures (e.g., Faster R-CNN, RetinaNet) based on a configuration
object, allowing for easy experimentation.

Core Components:
----------------
1.  **`create_detection_model` Function**:
    -   This is the main entry point for creating any detection model.
    -   It takes a `DetectionModelConfig` and a `pretrained` flag as input.
    -   Based on the `name` field in the config (e.g., 'faster_rcnn', 'retinanet'),
      it calls the appropriate helper function to build the model.
    -   It modifies the model's classification head to match the number of classes
      specified in the configuration. This is a crucial step in transfer learning,
      adapting a model pre-trained on a large dataset (like COCO) to our specific
      yield estimation task (e.g., detecting 'apple', 'orange').

2.  **Model-specific Helper Functions** (e.g., `_create_faster_rcnn`):
    -   These internal functions handle the instantiation of specific models from
      `torchvision`.
    -   They load the model with pre-trained weights if requested.
    -   They perform the surgery on the model's head. For example, in Faster R-CNN,
      the `box_predictor` is replaced with a new `FastRCNNPredictor` that has the
      correct number of output dimensions (`num_classes`).

Supported Models:
-----------------
-   **Faster R-CNN**: A classic and powerful two-stage detector. It first proposes
    regions of interest (RoIs) and then classifies them. Known for high accuracy.
    We support backbones like ResNet-50.
-   **RetinaNet**: A popular one-stage detector that addresses the class imbalance
    problem during training using a "Focal Loss". It often provides a good
    balance between speed and accuracy.

This modular approach allows new detection architectures to be added easily by
simply creating a new helper function and adding it to the main `create_detection_model`
dispatcher.
"""

import torchvision
from torchvision.models.detection import FasterRCNN, RetinaNet
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.retinanet import RetinaNetHead
import torch.nn as nn
import logging

from app.computer_vision.yield_estimation.utils.config import DetectionModelConfig

logger = logging.getLogger(__name__)

def _create_faster_rcnn(config: DetectionModelConfig, pretrained: bool) -> FasterRCNN:
    """
    Creates a Faster R-CNN model with a specified backbone.

    Args:
        config (DetectionModelConfig): Configuration for the model.
        pretrained (bool): If True, loads weights pre-trained on COCO.

    Returns:
        FasterRCNN: An initialized Faster R-CNN model.
    """
    # Load a model pre-trained on COCO
    model = torchvision.models.detection.fasterrcnn_resnet50_fpn(pretrained=pretrained)

    # Get the number of input features for the classifier
    in_features = model.roi_heads.box_predictor.cls_score.in_features

    # Replace the pre-trained head with a new one
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, config.num_classes)
    
    logger.info(f"Created Faster R-CNN model with {config.num_classes} classes.")
    return model

def _create_retinanet(config: DetectionModelConfig, pretrained: bool) -> RetinaNet:
    """
    Creates a RetinaNet model with a specified backbone.

    Args:
        config (DetectionModelConfig): Configuration for the model.
        pretrained (bool): If True, loads weights pre-trained on COCO.

    Returns:
        RetinaNet: An initialized RetinaNet model.
    """
    # Load a model pre-trained on COCO
    model = torchvision.models.detection.retinanet_resnet50_fpn(pretrained=pretrained)

    # Get the number of input features for the classifier
    # The head has a classification subnet, we need to get one of its conv layers
    in_channels = model.head.classification_head.conv[0].in_channels
    num_anchors = model.head.classification_head.num_anchors

    # Create a new head
    model.head = RetinaNetHead(
        in_channels=in_channels,
        num_anchors=num_anchors,
        num_classes=config.num_classes
    )

    logger.info(f"Created RetinaNet model with {config.num_classes} classes.")
    return model


def create_detection_model(config: DetectionModelConfig, pretrained: bool = True) -> nn.Module:
    """
    Factory function to create an object detection model based on the config.

    Args:
        config (DetectionModelConfig): The model configuration.
        pretrained (bool): Whether to use pre-trained weights.

    Returns:
        nn.Module: The created detection model.
    """
    model_name = config.name
    
    if model_name == 'faster_rcnn':
        return _create_faster_rcnn(config, pretrained)
    elif model_name == 'retinanet':
        return _create_retinanet(config, pretrained)
    # Add other models like 'yolo', 'detr' here as elif blocks
    # elif model_name == 'yolo':
    #     return _create_yolo(config, pretrained)
    else:
        raise NotImplementedError(f"Detection model '{model_name}' is not supported. "
                                  "Supported models are: 'faster_rcnn', 'retinanet'.")

# --- Example Usage ---
if __name__ == '__main__':
    print("--- Detection Models Demo ---")

    # 1. Create a config for a Faster R-CNN model
    # Typically this would come from the main config system
    faster_rcnn_config = DetectionModelConfig(
        name='faster_rcnn',
        num_classes=10, # e.g., 9 fruits + 1 background
        confidence_threshold=0.5,
        nms_threshold=0.45,
        backbone='resnet50_fpn'
    )

    # 2. Create the model
    print("\n[1. Creating Faster R-CNN model]")
    try:
        faster_rcnn_model = create_detection_model(faster_rcnn_config, pretrained=True)
        print(f"  Model created: {type(faster_rcnn_model)}")
        # Verify the head has been changed
        final_layer = faster_rcnn_model.roi_heads.box_predictor.cls_score
        print(f"  Final layer output features: {final_layer.out_features}")
        assert final_layer.out_features == 10
    except Exception as e:
        print(f"  Could not create model. Is torchvision installed? Error: {e}")

    # 3. Create a config for a RetinaNet model
    retinanet_config = DetectionModelConfig(
        name='retinanet',
        num_classes=5, # e.g., 4 vegetables + 1 background
        confidence_threshold=0.4,
        nms_threshold=0.5,
        backbone='resnet50_fpn'
    )

    # 4. Create the model
    print("\n[2. Creating RetinaNet model]")
    try:
        retinanet_model = create_detection_model(retinanet_config, pretrained=True)
        print(f"  Model created: {type(retinanet_model)}")
        # Verify the head has been changed
        # The classification head's final layer has `num_classes * num_anchors` outputs
        final_layer = retinanet_model.head.classification_head.cls_logits
        num_anchors = retinanet_model.head.classification_head.num_anchors
        print(f"  Final layer output features: {final_layer.out_channels}")
        assert final_layer.out_channels == retinanet_config.num_classes * num_anchors
    except Exception as e:
        print(f"  Could not create model. Is torchvision installed? Error: {e}")

    print("\nDetection models demo finished successfully.")
