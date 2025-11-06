# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\weed_detection\models.py

"""
Object Detection Models for Weed Detection
==========================================

This module provides a factory for creating and configuring various object
detection models for the task of weed detection. It leverages the pre-trained
models available in `torchvision.models.detection` to enable rapid development
and fine-tuning on custom weed datasets.

Using pre-trained models is a powerful form of transfer learning. These models
have been trained on large-scale datasets like COCO and have already learned
rich feature hierarchies. By replacing the classification head of these models,
we can adapt them to our specific classes (e.g., 'weed', 'crop') and fine-tune
them to achieve high accuracy with a relatively small amount of data.

Core Components:
---------------
1.  **`WeedDetectionModelFactory`**:
    -   **Purpose**: A factory class that constructs an object detection model
      based on a configuration dictionary.
    -   **Flexibility**: It supports several state-of-the-art model architectures,
      allowing for easy comparison and selection of the best model for the task.
    -   **Configuration**: The factory takes a `model_config` dictionary that
      specifies the `type` of model, the number of classes, and whether to use
      a pre-trained backbone.

Supported Model Architectures:
------------------------------
-   **`FasterRCNN`**:
    -   A classic and powerful two-stage detector. It first proposes regions of
      interest (RoIs) using a Region Proposal Network (RPN) and then classifies
      and refines the bounding boxes for these regions.
    -   Known for its high accuracy.
    -   The factory allows specifying different backbones, such as `ResNet-50` or
      `MobileNetV3-Large`.

-   **`SSD` (Single Shot Detector)**:
    -   A fast and efficient one-stage detector. It predicts bounding boxes and
      class probabilities directly from feature maps at multiple scales in a
      single pass.
    -   Offers a good trade-off between speed and accuracy, making it suitable
      for real-time applications.
    -   The factory uses the `SSD300_VGG16` implementation from torchvision.

-   **`RetinaNet`**:
    -   A one-stage detector that addresses the class imbalance problem inherent
      in dense object detection by using a novel "Focal Loss" function.
    -   It often achieves the accuracy of two-stage detectors like Faster R-CNN
      while maintaining the speed of one-stage detectors.
    -   The factory uses a `ResNet-50` backbone.

Usage:
------
The factory is used within the training pipeline to instantiate the desired model.
The number of classes (including the background class) must be specified.

Example configuration for a Faster R-CNN with a pre-trained ResNet-50 backbone:
```json
{
  "model_params": {
    "type": "FasterRCNN",
    "num_classes": 3, // e.g., background, weed, crop
    "pretrained_backbone": true,
    "backbone": "resnet50"
  }
}
```
"""

import torchvision
from torchvision.models.detection import (
    FasterRCNN, fasterrcnn_resnet50_fpn, fasterrcnn_mobilenet_v3_large_320_fpn,
    SSD300_VGG16_Weights, ssd300_vgg16,
    RetinaNet, retinanet_resnet50_fpn,
)
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.ssd import SSDHeader
from torchvision.models.detection.retinanet import RetinaNetClassificationHead
from torch import nn
from typing import Dict, Any
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class WeedDetectionModelFactory:
    """
    A factory for creating object detection models for weed detection.
    """

    @staticmethod
    def create_model(model_config: Dict[str, Any]) -> nn.Module:
        """
        Creates an object detection model based on the provided configuration.

        Args:
            model_config (Dict[str, Any]): A dictionary containing the model
                configuration. It must have 'type' and 'num_classes' keys.
                Example:
                {
                    'type': 'FasterRCNN',
                    'num_classes': 3,
                    'pretrained_backbone': True,
                    'backbone': 'resnet50'
                }

        Returns:
            nn.Module: An instance of a PyTorch object detection model.

        Raises:
            ValueError: If the model type or backbone is unknown.
        """
        model_type = model_config.get('type')
        num_classes = model_config.get('num_classes')
        pretrained = model_config.get('pretrained_backbone', True)

        if not model_type or not num_classes:
            raise ValueError("Model config must include 'type' and 'num_classes'.")

        logging.info(f"Creating model of type '{model_type}' with {num_classes} classes.")
        
        model_type_lower = model_type.lower()

        if model_type_lower == 'fasterrcnn':
            backbone_type = model_config.get('backbone', 'resnet50').lower()
            return WeedDetectionModelFactory._create_fasterrcnn(num_classes, pretrained, backbone_type)
        
        elif model_type_lower == 'ssd':
            return WeedDetectionModelFactory._create_ssd(num_classes, pretrained)
            
        elif model_type_lower == 'retinanet':
            return WeedDetectionModelFactory._create_retinanet(num_classes, pretrained)
            
        else:
            supported = ['FasterRCNN', 'SSD', 'RetinaNet']
            raise ValueError(f"Unknown model type '{model_type}'. Supported types are: {supported}")

    @staticmethod
    def _create_fasterrcnn(num_classes: int, pretrained: bool, backbone: str) -> FasterRCNN:
        """Creates a Faster R-CNN model with a custom classification head."""
        logging.info(f"Using FasterRCNN with backbone: {backbone}")
        
        if backbone == 'resnet50':
            model = fasterrcnn_resnet50_fpn(weights='DEFAULT' if pretrained else None)
            # Get the number of input features for the classifier
            in_features = model.roi_heads.box_predictor.cls_score.in_features
            # Replace the pre-trained head with a new one
            model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
        
        elif backbone == 'mobilenetv3':
            model = fasterrcnn_mobilenet_v3_large_320_fpn(weights='DEFAULT' if pretrained else None)
            in_features = model.roi_heads.box_predictor.cls_score.in_features
            model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
            
        else:
            raise ValueError(f"Unsupported FasterRCNN backbone: {backbone}. Choose 'resnet50' or 'mobilenetv3'.")
            
        return model

    @staticmethod
    def _create_ssd(num_classes: int, pretrained: bool) -> nn.Module:
        """Creates an SSD300 model with a custom classification head."""
        logging.info("Using SSD300_VGG16.")
        
        weights = SSD300_VGG16_Weights.DEFAULT if pretrained else None
        model = ssd300_vgg16(weights=weights)

        # Get the number of input channels for the classification head
        in_channels = [i.in_channels for i in model.head.classification_head.module_list]
        
        # The number of anchors per location for SSD300 is [4, 6, 6, 6, 4, 4]
        num_anchors = model.anchor_generator.num_anchors_per_location()

        # Create a new classification head
        new_head = SSDHeader(in_channels, num_anchors, num_classes)
        
        # Replace the head
        model.head = new_head
        
        return model

    @staticmethod
    def _create_retinanet(num_classes: int, pretrained: bool) -> RetinaNet:
        """Creates a RetinaNet model with a custom classification head."""
        logging.info("Using RetinaNet with ResNet-50 backbone.")
        
        model = retinanet_resnet50_fpn(weights='DEFAULT' if pretrained else None)

        # Get the number of input features for the classifier
        in_features = model.head.classification_head.conv[0].in_channels
        num_anchors = model.head.classification_head.num_anchors
        
        # Create a new classification head
        new_cls_head = RetinaNetClassificationHead(
            in_channels=in_features,
            num_anchors=num_anchors,
            num_classes=num_classes
        )
        
        # Replace the head
        model.head.classification_head = new_cls_head
        
        return model

# --- Example Usage ---
if __name__ == '__main__':
    print("--- Weed Detection Model Factory Demo ---")
    
    num_classes = 3  # e.g., background, weed, crop

    # 1. Define configurations for different models
    model_configs = {
        "FasterRCNN-ResNet50": {
            "type": "FasterRCNN",
            "num_classes": num_classes,
            "pretrained_backbone": True,
            "backbone": "resnet50"
        },
        "FasterRCNN-MobileNetV3": {
            "type": "FasterRCNN",
            "num_classes": num_classes,
            "pretrained_backbone": True,
            "backbone": "mobilenetv3"
        },
        "SSD300": {
            "type": "SSD",
            "num_classes": num_classes,
            "pretrained_backbone": True
        },
        "RetinaNet-ResNet50": {
            "type": "RetinaNet",
            "num_classes": num_classes,
            "pretrained_backbone": True
        }
    }

    # 2. Create instances of each model using the factory
    for name, config in model_configs.items():
        print(f"\n--- Creating {name} ---")
        try:
            model = WeedDetectionModelFactory.create_model(config)
            print(f"Successfully created model instance of type: {type(model).__name__}")
            
            # You can inspect the model structure, e.g., the classifier head
            if isinstance(model, FasterRCNN):
                print("Classifier head:", model.roi_heads.box_predictor)
            elif isinstance(model, SSD300_VGG16_Weights):
                 print("Classifier head:", model.head)
            elif isinstance(model, RetinaNet):
                 print("Classifier head:", model.head.classification_head)

            # Test with a dummy input
            dummy_input = torch.randn(1, 3, 416, 416)
            model.eval()
            with torch.no_grad():
                output = model(dummy_input)
            print(f"Model forward pass successful. Output keys (for one image): {output[0].keys()}")

        except (ValueError, TypeError) as e:
            print(f"Failed to create model: {e}")

    # 3. Demonstrate error handling
    print("\n--- Testing Error Handling ---")
    unknown_config = {"type": "YOLOv9", "num_classes": num_classes}
    try:
        WeedDetectionModelFactory.create_model(unknown_config)
    except ValueError as e:
        print(f"Successfully caught error for unknown model type: {e}")
        
    bad_backbone_config = {
        "type": "FasterRCNN", 
        "num_classes": num_classes,
        "backbone": "EfficientNet"
    }
    try:
        WeedDetectionModelFactory.create_model(bad_backbone_config)
    except ValueError as e:
        print(f"Successfully caught error for unsupported backbone: {e}")
```