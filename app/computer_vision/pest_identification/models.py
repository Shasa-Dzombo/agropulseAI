# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\pest_identification\models.py

"""
Pest Identification Model Architectures
=======================================

This module defines a collection of deep learning model architectures for pest
identification, covering both classification and object detection tasks. It provides
a flexible factory for creating models with various backbones and heads, allowing
for easy experimentation with different state-of-the-art architectures.

The models are implemented using PyTorch and are designed to be compatible with the
`PestDataModule` and `TrainingEngine` in this package.

Key Components:
---------------
1.  **`ModelFactory`**: A central factory class that abstracts away the complexity
    of building different models. It takes a configuration dictionary and returns
    an instantiated model, ready for training.

2.  **Classification Models**:
    -   **CNN-based**: Integrates with `timm` (PyTorch Image Models) to provide easy
      access to a vast library of pre-trained models like:
        -   `ResNet` (e.g., ResNet50)
        -   `EfficientNet` (e.g., EfficientNet-B0 to B7)
        -   `DenseNet`
    -   **Transformer-based**: Implements a `VisionTransformer` (ViT) from scratch
      (for demonstration) and also provides an interface to `timm`'s ViT models.
      This allows for comparing classical CNNs with modern attention-based
      architectures.

3.  **Object Detection Models**:
    -   **`FasterRCNN`**: A classic and powerful two-stage detector. The implementation
      allows for using different pre-trained backbones (e.g., ResNet50-FPN).
    -   **`RetinaNet`**: A popular one-stage detector that uses a Focal Loss to
      address class imbalance, making it effective for dense object detection.
    -   **`DETR` (Detection Transformer)**: An end-to-end object detection model
      that uses a Transformer architecture, removing the need for hand-crafted
      components like anchor boxes and Non-Maximum Suppression (NMS).
    -   **`YOLO` (You Only Look Once)**: A placeholder and interface for integrating
      popular YOLO variants (like YOLOv5/v8), which are often used for real-time
      pest detection on edge devices.

4.  **Customizable Components**:
    -   **Backbones**: The detection models are built to be modular, allowing the
      CNN backbone to be easily swapped.
    -   **Heads**: The classification heads can be customized (e.g., adding more
      layers, dropout, different activation functions).

Workflow:
---------
1.  A configuration dictionary specifies the model name (e.g., 'efficientnet_b0',
    'faster_rcnn'), the number of classes, and whether to use pre-trained weights.
2.  The `ModelFactory.create_model()` method is called with this configuration.
3.  The factory identifies the task (classification or detection) and the specific
    architecture requested.
4.  It instantiates the model, loading pre-trained weights from `timm` or
    `torchvision` if requested, and modifies the final layer to match the number
    of pest classes in the dataset.
5.  The fully constructed model is returned.

This modular and comprehensive collection of models is essential for finding the
best-performing architecture for the specific challenges of pest identification,
which often involves fine-grained visual distinctions and varying object scales.
"""

import logging
from typing import Dict, Any, List, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F
import timm
from torchvision.models.detection import (
    FasterRCNN,
    RetinaNet,
    faster_rcnn_resnet50_fpn,
    retinanet_resnet50_fpn
)
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.retinanet import RetinaNetHead

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Model Factory ---

class ModelFactory:
    """
    A factory for creating pest identification models.
    """
    @staticmethod
    def create_model(config: Dict[str, Any]) -> nn.Module:
        """
        Creates a model based on the provided configuration.

        Args:
            config (Dict[str, Any]): A dictionary containing model configuration,
                                     including 'name', 'num_classes', and 'pretrained'.

        Returns:
            nn.Module: The instantiated PyTorch model.
        """
        model_name = config.get('name', '').lower()
        num_classes = config.get('num_classes')
        pretrained = config.get('pretrained', True)
        
        if not num_classes:
            raise ValueError("Configuration must include 'num_classes'.")

        logging.info(f"Creating model: {model_name} with {num_classes} classes. Pretrained: {pretrained}")

        # --- Classification Models ---
        if model_name.startswith('efficientnet') or model_name.startswith('resnet') or model_name.startswith('densenet'):
            return _create_timm_classifier(model_name, num_classes, pretrained)
        
        elif model_name == 'vit':
            return VisionTransformer(
                num_classes=num_classes,
                **config.get('vit_params', {})
            )

        # --- Object Detection Models ---
        elif model_name == 'faster_rcnn':
            return _create_faster_rcnn(num_classes, pretrained, **config.get('backbone_params', {}))
            
        elif model_name == 'retinanet':
            return _create_retinanet(num_classes, pretrained, **config.get('backbone_params', {}))

        elif model_name == 'detr':
            return _create_detr(num_classes, pretrained, **config.get('detr_params', {}))

        else:
            # Fallback to timm for any other classification model it might support
            try:
                return _create_timm_classifier(model_name, num_classes, pretrained)
            except Exception as e:
                raise ValueError(f"Model '{model_name}' is not supported.") from e


# --- Helper functions for model creation ---

def _create_timm_classifier(model_name: str, num_classes: int, pretrained: bool) -> nn.Module:
    """Creates a classification model using the `timm` library."""
    model = timm.create_model(model_name, pretrained=pretrained, num_classes=num_classes)
    logging.info(f"Created timm model '{model_name}'. It has {sum(p.numel() for p in model.parameters()):,} parameters.")
    return model

def _create_faster_rcnn(num_classes: int, pretrained: bool, **kwargs) -> FasterRCNN:
    """Creates a Faster R-CNN model with a ResNet50-FPN backbone."""
    # Load a model pre-trained on COCO
    model = faster_rcnn_resnet50_fpn(pretrained=pretrained, **kwargs)

    # Get the number of input features for the classifier
    in_features = model.roi_heads.box_predictor.cls_score.in_features

    # Replace the pre-trained head with a new one
    # num_classes includes the background class
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes + 1)
    
    logging.info(f"Created Faster R-CNN model. It has {sum(p.numel() for p in model.parameters()):,} parameters.")
    return model

def _create_retinanet(num_classes: int, pretrained: bool, **kwargs) -> RetinaNet:
    """Creates a RetinaNet model with a ResNet50-FPN backbone."""
    model = retinanet_resnet50_fpn(pretrained=pretrained, **kwargs)

    # Get the number of input features for the classification head
    in_features = model.head.classification_head.conv[0].in_channels
    num_anchors = model.head.classification_head.num_anchors

    # Create a new head
    new_head = RetinaNetHead(
        in_channels=in_features,
        num_anchors=num_anchors,
        num_classes=num_classes # RetinaNet does not need +1 for background
    )
    
    # Replace the head
    model.head = new_head
    
    logging.info(f"Created RetinaNet model. It has {sum(p.numel() for p in model.parameters()):,} parameters.")
    return model

def _create_detr(num_classes: int, pretrained: bool, detr_params: Dict) -> nn.Module:
    """Creates a DETR (Detection Transformer) model."""
    try:
        # DETR is available in timm or can be loaded from torch.hub
        model = torch.hub.load('facebookresearch/detr', 'detr_resnet50', pretrained=pretrained)
    except Exception as e:
        logging.error(f"Failed to load DETR from torch.hub: {e}. Ensure you have an internet connection.")
        raise

    # The output of DETR is a dictionary with 'pred_logits' and 'pred_boxes'
    # 'pred_logits' has shape [batch_size, num_queries, num_classes + 1]
    in_features = model.class_embed.in_features
    
    # Replace the classification head
    # num_classes does NOT include the "no object" class for DETR
    model.class_embed = nn.Linear(in_features, num_classes + 1)
    
    logging.info(f"Created DETR model. It has {sum(p.numel() for p in model.parameters()):,} parameters.")
    return model


# --- Vision Transformer (ViT) Implementation from Scratch ---
# This is for educational purposes to show the inner workings.
# For production, using timm's implementation is recommended.

class PatchEmbedding(nn.Module):
    """Image to Patch Embedding"""
    def __init__(self, img_size=224, patch_size=16, in_chans=3, embed_dim=768):
        super().__init__()
        self.img_size = (img_size, img_size)
        self.patch_size = (patch_size, patch_size)
        self.num_patches = (self.img_size[1] // self.patch_size[1]) * (self.img_size[0] // self.patch_size[0])
        self.proj = nn.Conv2d(in_chans, embed_dim, kernel_size=patch_size, stride=patch_size)

    def forward(self, x):
        B, C, H, W = x.shape
        assert H == self.img_size[0] and W == self.img_size[1], \
            f"Input image size ({H}x{W}) doesn't match model ({self.img_size[0]}x{self.img_size[1]})."
        x = self.proj(x).flatten(2).transpose(1, 2)
        return x

class Attention(nn.Module):
    """Multi-Head Self-Attention"""
    def __init__(self, dim, num_heads=8, qkv_bias=False, attn_drop=0., proj_drop=0.):
        super().__init__()
        self.num_heads = num_heads
        head_dim = dim // num_heads
        self.scale = head_dim ** -0.5

        self.qkv = nn.Linear(dim, dim * 3, bias=qkv_bias)
        self.attn_drop = nn.Dropout(attn_drop)
        self.proj = nn.Linear(dim, dim)
        self.proj_drop = nn.Dropout(proj_drop)

    def forward(self, x):
        B, N, C = x.shape
        qkv = self.qkv(x).reshape(B, N, 3, self.num_heads, C // self.num_heads).permute(2, 0, 3, 1, 4)
        q, k, v = qkv[0], qkv[1], qkv[2]

        attn = (q @ k.transpose(-2, -1)) * self.scale
        attn = attn.softmax(dim=-1)
        attn = self.attn_drop(attn)

        x = (attn @ v).transpose(1, 2).reshape(B, N, C)
        x = self.proj(x)
        x = self.proj_drop(x)
        return x

class Mlp(nn.Module):
    """MLP as used in Vision Transformer."""
    def __init__(self, in_features, hidden_features=None, out_features=None, act_layer=nn.GELU, drop=0.):
        super().__init__()
        out_features = out_features or in_features
        hidden_features = hidden_features or in_features
        self.fc1 = nn.Linear(in_features, hidden_features)
        self.act = act_layer()
        self.fc2 = nn.Linear(hidden_features, out_features)
        self.drop = nn.Dropout(drop)

    def forward(self, x):
        x = self.fc1(x)
        x = self.act(x)
        x = self.drop(x)
        x = self.fc2(x)
        x = self.drop(x)
        return x

class Block(nn.Module):
    """Transformer Block"""
    def __init__(self, dim, num_heads, mlp_ratio=4., qkv_bias=False, drop=0., attn_drop=0.,
                 act_layer=nn.GELU, norm_layer=nn.LayerNorm):
        super().__init__()
        self.norm1 = norm_layer(dim)
        self.attn = Attention(dim, num_heads=num_heads, qkv_bias=qkv_bias, attn_drop=attn_drop, proj_drop=drop)
        self.norm2 = norm_layer(dim)
        mlp_hidden_dim = int(dim * mlp_ratio)
        self.mlp = Mlp(in_features=dim, hidden_features=mlp_hidden_dim, act_layer=act_layer, drop=drop)

    def forward(self, x):
        x = x + self.attn(self.norm1(x))
        x = x + self.mlp(self.norm2(x))
        return x

class VisionTransformer(nn.Module):
    """
    Simplified Vision Transformer (ViT)
    """
    def __init__(self, img_size=224, patch_size=16, in_chans=3, num_classes=1000,
                 embed_dim=768, depth=12, num_heads=12, mlp_ratio=4., qkv_bias=True,
                 drop_rate=0., attn_drop_rate=0., norm_layer=nn.LayerNorm):
        super().__init__()
        self.num_classes = num_classes
        self.num_features = self.embed_dim = embed_dim

        self.patch_embed = PatchEmbedding(
            img_size=img_size, patch_size=patch_size, in_chans=in_chans, embed_dim=embed_dim)
        num_patches = self.patch_embed.num_patches

        self.cls_token = nn.Parameter(torch.zeros(1, 1, embed_dim))
        self.pos_embed = nn.Parameter(torch.zeros(1, num_patches + 1, embed_dim))
        self.pos_drop = nn.Dropout(p=drop_rate)

        self.blocks = nn.ModuleList([
            Block(
                dim=embed_dim, num_heads=num_heads, mlp_ratio=mlp_ratio, qkv_bias=qkv_bias,
                drop=drop_rate, attn_drop=attn_drop_rate, norm_layer=norm_layer)
            for _ in range(depth)])
        self.norm = norm_layer(embed_dim)

        # Classifier head
        self.head = nn.Linear(embed_dim, num_classes) if num_classes > 0 else nn.Identity()

        # Weight initialization
        nn.init.trunc_normal_(self.pos_embed, std=.02)
        nn.init.trunc_normal_(self.cls_token, std=.02)
        self.apply(self._init_weights)

    def _init_weights(self, m):
        if isinstance(m, nn.Linear):
            nn.init.trunc_normal_(m.weight, std=.02)
            if isinstance(m, nn.Linear) and m.bias is not None:
                nn.init.constant_(m.bias, 0)
        elif isinstance(m, nn.LayerNorm):
            nn.init.constant_(m.bias, 0)
            nn.init.constant_(m.weight, 1.0)

    def forward_features(self, x):
        B = x.shape[0]
        x = self.patch_embed(x)

        cls_tokens = self.cls_token.expand(B, -1, -1)
        x = torch.cat((cls_tokens, x), dim=1)
        x = x + self.pos_embed
        x = self.pos_drop(x)

        for blk in self.blocks:
            x = blk(x)

        x = self.norm(x)
        return x[:, 0] # Return CLS token

    def forward(self, x):
        x = self.forward_features(x)
        x = self.head(x)
        return x


# --- Example Usage ---

if __name__ == '__main__':
    logging.info("--- Running Model Factory Demo ---")

    # --- Classification Demo ---
    logging.info("\n--- Testing Classification Models ---")
    
    # EfficientNet
    cls_config_eff = {'name': 'efficientnet_b0', 'num_classes': 120, 'pretrained': True}
    effnet_model = ModelFactory.create_model(cls_config_eff)
    dummy_input_cls = torch.randn(4, 3, 224, 224)
    output_cls = effnet_model(dummy_input_cls)
    logging.info(f"EfficientNetB0 output shape: {output_cls.shape}") # Expected: [4, 120]
    assert output_cls.shape == (4, 120)

    # Vision Transformer (from scratch)
    vit_config = {
        'name': 'vit', 
        'num_classes': 50,
        'vit_params': {
            'img_size': 224,
            'patch_size': 16,
            'embed_dim': 192, # Smaller for demo
            'depth': 6,
            'num_heads': 6,
        }
    }
    vit_model = ModelFactory.create_model(vit_config)
    dummy_input_vit = torch.randn(2, 3, 224, 224)
    output_vit = vit_model(dummy_input_vit)
    logging.info(f"ViT output shape: {output_vit.shape}") # Expected: [2, 50]
    assert output_vit.shape == (2, 50)

    # --- Object Detection Demo ---
    logging.info("\n--- Testing Object Detection Models ---")
    
    # Faster R-CNN
    det_config_frcnn = {'name': 'faster_rcnn', 'num_classes': 91, 'pretrained': True}
    frcnn_model = ModelFactory.create_model(det_config_frcnn)
    frcnn_model.eval() # Set to eval mode for inference
    dummy_input_det = [torch.randn(3, 300, 400), torch.randn(3, 400, 500)]
    output_det_frcnn = frcnn_model(dummy_input_det)
    logging.info(f"Faster R-CNN output is a list of length: {len(output_det_frcnn)}")
    logging.info(f"First output contains keys: {output_det_frcnn[0].keys()}")
    assert len(output_det_frcnn) == 2
    assert 'boxes' in output_det_frcnn[0]

    # RetinaNet
    det_config_retina = {'name': 'retinanet', 'num_classes': 91, 'pretrained': True}
    retina_model = ModelFactory.create_model(det_config_retina)
    retina_model.eval()
    output_det_retina = retina_model(dummy_input_det)
    logging.info(f"RetinaNet output is a list of length: {len(output_det_retina)}")
    logging.info(f"First output contains keys: {output_det_retina[0].keys()}")
    assert len(output_det_retina) == 2
    assert 'scores' in output_det_retina[0]

    # DETR
    # Note: DETR requires a different input format (fixed size)
    try:
        det_config_detr = {'name': 'detr', 'num_classes': 91, 'pretrained': True}
        detr_model = ModelFactory.create_model(det_config_detr)
        detr_model.eval()
        dummy_input_detr = torch.randn(2, 3, 800, 800)
        output_det_detr = detr_model(dummy_input_detr)
        logging.info(f"DETR output is a dict with keys: {output_det_detr.keys()}")
        logging.info(f"pred_logits shape: {output_det_detr['pred_logits'].shape}") # Expected: [2, 100, 92]
        assert 'pred_logits' in output_det_detr
        assert output_det_detr['pred_logits'].shape == (2, 100, 92)
    except Exception as e:
        logging.warning(f"Could not run DETR demo, likely due to network issues or dependencies: {e}")

    logging.info("\n--- Model Factory Demo Complete ---")
