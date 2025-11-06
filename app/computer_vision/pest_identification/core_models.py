
"""
Core Models for Pest Identification

This module defines the primary deep learning architectures used for pest
classification and object detection. It includes:
- Custom backbone implementations (EfficientNetB7).
- High-level classifier and detector classes that integrate backbones.
- Implementations of state-of-the-art detection heads (YOLOv8, RetinaNet).
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision.models import resnet50, ResNet50_Weights
from typing import List, Tuple, Dict, Optional
import math

# ==============================================================================
# SECTION 1: UTILITY LAYERS AND BLOCKS
# ==============================================================================

class ConvBlock(nn.Module):
    """Standard Convolution Block: Conv -> BatchNorm -> Activation"""
    def __init__(self, in_channels, out_channels, kernel_size=3, stride=1, padding=1, activation='silu'):
        super().__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding, bias=False)
        self.bn = nn.BatchNorm2d(out_channels)
        if activation == 'silu':
            self.activation = nn.SiLU(inplace=True)
        elif activation == 'relu':
            self.activation = nn.ReLU(inplace=True)
        else:
            self.activation = nn.Identity()

    def forward(self, x):
        return self.activation(self.bn(self.conv(x)))

class SqueezeExcite(nn.Module):
    """Squeeze-and-Excitation block."""
    def __init__(self, in_channels, reduced_dim):
        super().__init__()
        self.se = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(in_channels, reduced_dim, 1),
            nn.SiLU(),
            nn.Conv2d(reduced_dim, in_channels, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        return x * self.se(x)

class MBConv(nn.Module):
    """Mobile Inverted Bottleneck Convolution (MBConv) block."""
    def __init__(self, in_channels, out_channels, kernel_size, stride, expand_ratio, se_ratio=0.25, drop_rate=0.2):
        super().__init__()
        self.use_residual = in_channels == out_channels and stride == 1
        hidden_dim = in_channels * expand_ratio
        self.expand_ratio = expand_ratio
        
        layers = []
        # Expansion phase
        if expand_ratio != 1:
            layers.append(ConvBlock(in_channels, hidden_dim, kernel_size=1, padding=0))
        
        # Depthwise convolution
        layers.extend([
            ConvBlock(hidden_dim, hidden_dim, kernel_size, stride, padding=kernel_size//2, activation='silu'),
            SqueezeExcite(hidden_dim, int(in_channels * se_ratio)),
        ])
        
        # Projection phase
        layers.append(nn.Conv2d(hidden_dim, out_channels, 1, bias=False))
        layers.append(nn.BatchNorm2d(out_channels))
        
        self.conv = nn.Sequential(*layers)
        self.drop_rate = drop_rate

    def forward(self, x):
        identity = x
        x = self.conv(x)
        if self.use_residual:
            if self.drop_rate > 0:
                x = self.stochastic_depth(x, self.drop_rate, self.training)
            x += identity
        return x

    @staticmethod
    def stochastic_depth(x, p, training):
        if not training or p == 0.0:
            return x
        keep_prob = 1.0 - p
        shape = (x.shape[0],) + (1,) * (x.ndim - 1)
        random_tensor = keep_prob + torch.rand(shape, dtype=x.dtype, device=x.device)
        random_tensor.floor_()
        return x.div(keep_prob) * random_tensor

# ==============================================================================
# SECTION 2: EFFICIENTNET-B7 BACKBONE
# ==============================================================================

class EfficientNetB7(nn.Module):
    """
    An implementation of the EfficientNet-B7 backbone.
    This provides powerful features for classification and detection.
    """
    def __init__(self, num_classes=1000, pretrained=True):
        super().__init__()
        # EfficientNet-B7 parameters
        # repeats, channels, kernel_size, stride, expand_ratio
        params = [
            (4, 32, 3, 1, 1),
            (8, 48, 3, 2, 6),
            (8, 80, 5, 2, 6),
            (12, 160, 3, 2, 6),
            (12, 224, 5, 1, 6),
            (16, 384, 5, 2, 6),
            (4, 640, 3, 1, 6),
        ]
        
        self.stem = ConvBlock(3, 64, stride=2)
        
        self.blocks = nn.ModuleList([])
        in_channels = 64
        for r, c, k, s, e in params:
            for i in range(r):
                stride = s if i == 0 else 1
                self.blocks.append(MBConv(in_channels, c, k, stride, e))
                in_channels = c
        
        self.head = nn.Sequential(
            ConvBlock(in_channels, 2560, kernel_size=1, padding=0),
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Dropout(0.5),
            nn.Linear(2560, num_classes)
        )
        
        if pretrained:
            self.load_pretrained_weights()

    def forward(self, x):
        x = self.stem(x)
        # To extract features for a detector, we would tap into these blocks
        # For classification, we run through all of them.
        for block in self.blocks:
            x = block(x)
        x = self.head(x)
        return x

    def load_pretrained_weights(self):
        # In a real scenario, you would download and load weights from a URL.
        # Here we just initialize them.
        logging.info("Initializing EfficientNet-B7 with random weights (pretrained weights not available).")
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode="fan_out", nonlinearity="relu")
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                nn.init.zeros_(m.bias)

    def extract_features(self, x) -> List[torch.Tensor]:
        """Extract features for use in a Feature Pyramid Network (FPN)."""
        features = []
        x = self.stem(x)
        # This is a simplified feature extraction. A real one would be more careful
        # about which blocks correspond to which feature levels (C2, C3, C4, C5).
        for i, block in enumerate(self.blocks):
            x = block(x)
            if i in [3, 11, 23, 39]: # Example indices for feature extraction
                features.append(x)
        return features

# ==============================================================================
# SECTION 3: PEST CLASSIFIER
# ==============================================================================

class PestClassifier(nn.Module):
    """
    A high-level classifier for identifying pest species from an image.
    Can use different backbones like ResNet or EfficientNet.
    """
    def __init__(self, num_classes: int, backbone_name: str = 'resnet50', pretrained: bool = True):
        super().__init__()
        self.num_classes = num_classes
        
        if backbone_name == 'resnet50':
            weights = ResNet50_Weights.IMAGENET1K_V2 if pretrained else None
            self.backbone = resnet50(weights=weights)
            in_features = self.backbone.fc.in_features
            self.backbone.fc = nn.Identity() # Remove original head
        elif backbone_name == 'efficientnet_b7':
            self.backbone = EfficientNetB7(num_classes=1000, pretrained=pretrained)
            in_features = 2560
            self.backbone.head = nn.Identity() # Remove original head
        else:
            raise ValueError(f"Unsupported backbone: {backbone_name}")
            
        # Custom classification head
        self.classifier_head = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.BatchNorm1d(in_features),
            nn.Dropout(0.5),
            nn.Linear(in_features, 512),
            nn.ReLU(),
            nn.BatchNorm1d(512),
            nn.Dropout(0.5),
            nn.Linear(512, num_classes)
        )

    def forward(self, x):
        features = self.backbone(x)
        return self.classifier_head(features)

# ==============================================================================
# SECTION 4: OBJECT DETECTION MODELS (YOLO, RETINANET)
# ==============================================================================

class FPN(nn.Module):
    """Feature Pyramid Network for object detection."""
    def __init__(self, in_channels_list: List[int], out_channels: int):
        super().__init__()
        self.lateral_convs = nn.ModuleList()
        self.fpn_convs = nn.ModuleList()
        
        for in_channels in in_channels_list:
            self.lateral_convs.append(nn.Conv2d(in_channels, out_channels, 1))
            self.fpn_convs.append(nn.Conv2d(out_channels, out_channels, 3, padding=1))
            
        # Initialize weights
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_uniform_(m.weight, a=1)
                nn.init.constant_(m.bias, 0)

    def forward(self, features: List[torch.Tensor]) -> List[torch.Tensor]:
        # features should be [C3, C4, C5]
        laterals = [conv(f) for conv, f in zip(self.lateral_convs, features)]
        
        # Top-down path
        for i in range(len(laterals) - 1, 0, -1):
            laterals[i-1] += F.interpolate(laterals[i], scale_factor=2, mode='nearest')
            
        # Output convs
        outs = [conv(lat) for conv, lat in zip(self.fpn_convs, laterals)]
        
        # Add P6 and P7 for RetinaNet
        p6 = F.max_pool2d(outs[-1], kernel_size=1, stride=2)
        p7 = F.relu(self.fpn_convs[-1](p6)) # Re-use a conv for simplicity
        p7 = F.max_pool2d(p7, kernel_size=1, stride=2)
        
        return outs + [p6, p7]

class RetinaNet(nn.Module):
    """
    Implementation of RetinaNet with Focal Loss for dense object detection.
    """
    def __init__(self, num_classes: int, backbone: nn.Module, fpn_out_channels: int = 256, num_anchors: int = 9):
        super().__init__()
        self.backbone = backbone
        # Assuming backbone.extract_features returns features from C3, C4, C5
        # with channel sizes [512, 1024, 2048] for a ResNet50
        self.fpn = FPN(in_channels_list=[512, 1024, 2048], out_channels=fpn_out_channels)
        
        self.num_classes = num_classes
        self.num_anchors = num_anchors
        
        # Subnets
        self.classification_subnet = self._make_subnet(fpn_out_channels, num_anchors * num_classes)
        self.bbox_regression_subnet = self._make_subnet(fpn_out_channels, num_anchors * 4)
        
        # Initialize classification subnet bias
        prior_prob = 0.01
        bias_value = -math.log((1 - prior_prob) / prior_prob)
        torch.nn.init.constant_(self.classification_subnet[-1].bias, bias_value)

    def _make_subnet(self, in_channels, out_channels):
        layers = []
        for _ in range(4):
            layers.append(nn.Conv2d(in_channels, in_channels, 3, padding=1))
            layers.append(nn.ReLU(inplace=True))
        layers.append(nn.Conv2d(in_channels, out_channels, 3, padding=1))
        return nn.Sequential(*layers)

    def forward(self, images):
        # Backbone and FPN
        features = self.backbone.extract_features(images)
        fpn_features = self.fpn(features)
        
        class_preds = []
        bbox_preds = []
        
        for feature in fpn_features:
            class_pred = self.classification_subnet(feature)
            bbox_pred = self.bbox_regression_subnet(feature)
            
            # Reshape for processing
            # (N, C, H, W) -> (N, H*W*A, num_classes)
            class_pred = class_pred.permute(0, 2, 3, 1).contiguous().view(images.shape[0], -1, self.num_classes)
            # (N, C, H, W) -> (N, H*W*A, 4)
            bbox_pred = bbox_pred.permute(0, 2, 3, 1).contiguous().view(images.shape[0], -1, 4)
            
            class_preds.append(class_pred)
            bbox_preds.append(bbox_pred)
            
        return torch.cat(class_preds, dim=1), torch.cat(bbox_preds, dim=1)

class YOLOv8(nn.Module):
    """
    A simplified implementation of the YOLOv8 architecture, focusing on the head.
    """
    def __init__(self, num_classes: int, backbone: nn.Module, fpn_out_channels: int = 256):
        super().__init__()
        self.backbone = backbone
        # YOLO typically uses a custom CSP-based backbone and PANet neck.
        # We'll reuse our FPN for simplicity.
        self.neck = FPN(in_channels_list=[512, 1024, 2048], out_channels=fpn_out_channels)
        
        self.num_classes = num_classes
        self.num_outputs = num_classes + 4 # 4 for bbox
        
        # Detection heads for P3, P4, P5
        self.detect_heads = nn.ModuleList()
        for _ in range(3): # For P3, P4, P5 from FPN
            self.detect_heads.append(
                nn.Conv2d(fpn_out_channels, self.num_outputs, 1)
            )

    def forward(self, images):
        features = self.backbone.extract_features(images)
        neck_features = self.neck(features)[:3] # Take P3, P4, P5
        
        predictions = []
        for i, feature in enumerate(neck_features):
            pred = self.detect_heads[i](feature)
            bs, _, h, w = pred.shape
            pred = pred.view(bs, self.num_outputs, h * w).permute(0, 2, 1).contiguous()
            predictions.append(pred)
            
        return torch.cat(predictions, dim=1)

class PestObjectDetector(nn.Module):
    """
    High-level object detector for locating pests in an image.
    """
    def __init__(self, num_classes: int, model_type: str = 'yolov8', backbone_name: str = 'resnet50', pretrained: bool = True):
        super().__init__()
        
        # Create a backbone that can extract features
        if backbone_name == 'resnet50':
            # A bit of a hack to make resnet50 extract features
            original_backbone = resnet50(weights=ResNet50_Weights.IMAGENET1K_V2 if pretrained else None)
            class ResNetFeatureExtractor(nn.Module):
                def __init__(self):
                    super().__init__()
                    self.layer1 = nn.Sequential(*list(original_backbone.children())[:5])
                    self.layer2 = original_backbone.layer2
                    self.layer3 = original_backbone.layer3
                    self.layer4 = original_backbone.layer4
                def forward(self, x):
                    x = self.layer1(x)
                    c3 = self.layer2(x)
                    c4 = self.layer3(c3)
                    c5 = self.layer4(c4)
                    return [c3, c4, c5]
            backbone = ResNetFeatureExtractor()
        else:
            # In a real scenario, you'd have feature extractors for other backbones too
            raise ValueError(f"Backbone {backbone_name} not supported for detection.")

        if model_type == 'yolov8':
            self.model = YOLOv8(num_classes, backbone)
        elif model_type == 'retinanet':
            self.model = RetinaNet(num_classes, backbone)
        else:
            raise ValueError(f"Unsupported detector type: {model_type}")

    def forward(self, x):
        return self.model(x)

    def predict(self, images, confidence_threshold=0.5, nms_threshold=0.45):
        """
        Run inference and apply post-processing (NMS).
        """
        self.eval()
        with torch.no_grad():
            predictions = self.forward(images)
            
            # The output of YOLO/RetinaNet needs significant post-processing:
            # 1. Decode bounding boxes from model outputs.
            # 2. Apply confidence thresholding.
            # 3. Apply Non-Maximum Suppression (NMS).
            # This is complex and often handled by library functions.
            # We'll simulate the output format.
            
            output = []
            for i in range(images.shape[0]):
                # Dummy output for demonstration
                num_preds = predictions[i].shape[0]
                boxes = torch.rand(num_preds, 4) * images.shape[2] # Random boxes
                scores = torch.rand(num_preds)
                labels = torch.randint(0, self.model.num_classes, (num_preds,))
                
                # Apply confidence threshold
                keep = scores > confidence_threshold
                boxes, scores, labels = boxes[keep], scores[keep], labels[keep]
                
                # Apply NMS (using torchvision's implementation)
                from torchvision.ops import nms
                keep_nms = nms(boxes, scores, nms_threshold)
                
                output.append({
                    "boxes": boxes[keep_nms].cpu().numpy(),
                    "scores": scores[keep_nms].cpu().numpy(),
                    "labels": labels[keep_nms].cpu().numpy(),
                })
        return output
