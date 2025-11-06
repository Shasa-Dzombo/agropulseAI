# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\pest_identification\losses.py

"""
Custom Loss Functions for Pest Identification
=============================================

This module implements a variety of loss functions tailored for pest identification
tasks, particularly for classification and object detection. While standard losses
like Cross-Entropy are sufficient for basic classification, more advanced techniques
are often needed to handle challenges like class imbalance and hard-to-classify
examples.

For object detection, this module provides Python implementations of complex loss
functions used in state-of-the-art models, such as the Focal Loss for RetinaNet
and the bipartite matching loss for DETR.

Key Components:
---------------
1.  **`LossFactory`**: A factory class to create loss functions based on a
    configuration string or dictionary. This allows for easy swapping of loss
    functions during experimentation.

2.  **Classification Losses**:
    -   **`LabelSmoothingCrossEntropy`**: A modification of the standard cross-entropy
      loss that prevents the model from becoming over-confident. Instead of using
      one-hot labels (0 or 1), it uses smoothed labels (e.g., 0.9 for the true
      class and a small value for others).
    -   **`FocalLoss` for Classification**: An implementation of Focal Loss for
      multi-class classification. It down-weights the loss assigned to well-classified
      examples, allowing the model to focus on hard, misclassified examples. This
      is particularly useful for datasets with significant class imbalance.

3.  **Object Detection Losses**:
    -   **`FocalLoss` for Detection**: The original Focal Loss as proposed for
      RetinaNet, designed to handle the extreme foreground-background class
      imbalance in one-stage object detectors.
    -   **`DETRLoss`**: A Python-based re-implementation of the loss used in the
      DETR (Detection Transformer) model. This is a complex, multi-part loss that
      involves:
        -   **Bipartite Matching**: Using the Hungarian algorithm (`scipy.optimize.linear_sum_assignment`)
          to find the optimal one-to-one matching between predicted and ground-truth
          bounding boxes.
        -   **Box Regression Loss**: A combination of L1 loss and Generalized IoU (GIoU)
          loss for the matched bounding boxes.
        -   **Classification Loss**: A standard cross-entropy loss for the matched boxes.

4.  **Utility Losses**:
    -   **`GIoULoss`**: Generalized Intersection over Union loss, which provides a
      more robust bounding box regression metric than standard L1 or L2 loss, as
      it accounts for the area, shape, and location of the boxes.

Workflow:
---------
1.  The `TrainingEngine` receives a configuration specifying the desired loss
    (e.g., 'focal_loss').
2.  It calls the `LossFactory` to get an instance of the corresponding loss class.
3.  During the training step, the model's output and the ground-truth labels are
    passed to the loss function, which computes the final scalar loss value used
    for backpropagation.
4.  For complex losses like `DETRLoss`, the loss function itself performs the
    critical step of matching predictions to targets before computing the individual
    loss components.

These advanced loss functions are crucial for training high-performance models that
can accurately identify and locate small pests in cluttered agricultural environments.
"""

import logging
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor
from typing import Dict, Any, List, Optional

try:
    from scipy.optimize import linear_sum_assignment
except ImportError:
    logging.error("scipy is not installed. Please install it: pip install scipy")
    linear_sum_assignment = None

from torchvision.ops.boxes import box_convert, generalized_box_iou

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Loss Factory ---

class LossFactory:
    """
    Factory to create loss functions from configuration.
    """
    @staticmethod
    def create_loss(config: Dict[str, Any]) -> nn.Module:
        """
        Creates a loss function module based on the config.

        Args:
            config (Dict[str, Any]): Dictionary with 'name' and other params.
                                     Example: {'name': 'focal_loss', 'alpha': 0.25, 'gamma': 2.0}

        Returns:
            nn.Module: The instantiated loss function.
        """
        loss_name = config.get('name', '').lower()
        params = {k: v for k, v in config.items() if k != 'name'}
        
        logging.info(f"Creating loss function: {loss_name} with params: {params}")

        if loss_name == 'cross_entropy':
            return nn.CrossEntropyLoss(**params)
        elif loss_name == 'label_smoothing_ce':
            return LabelSmoothingCrossEntropy(**params)
        elif loss_name == 'focal_loss_clf':
            return FocalLossClassification(**params)
        elif loss_name == 'detr_loss':
            return DETRLoss(**params)
        else:
            raise ValueError(f"Loss function '{loss_name}' is not supported.")

# --- Classification Losses ---

class LabelSmoothingCrossEntropy(nn.Module):
    """
    Cross-entropy loss with label smoothing.
    """
    def __init__(self, smoothing: float = 0.1, reduction: str = 'mean'):
        super().__init__()
        assert 0.0 <= smoothing < 1.0
        self.smoothing = smoothing
        self.reduction = reduction

    def forward(self, pred: Tensor, target: Tensor) -> Tensor:
        """
        Args:
            pred (Tensor): Logits from the model (before softmax), shape (N, C).
            target (Tensor): Ground truth labels, shape (N).
        """
        num_classes = pred.size(-1)
        log_preds = F.log_softmax(pred, dim=-1)
        
        with torch.no_grad():
            # Create smoothed labels
            true_dist = torch.zeros_like(log_preds)
            true_dist.fill_(self.smoothing / (num_classes - 1))
            true_dist.scatter_(1, target.data.unsqueeze(1), 1.0 - self.smoothing)

        loss = torch.sum(-true_dist * log_preds, dim=-1)

        if self.reduction == 'mean':
            return loss.mean()
        elif self.reduction == 'sum':
            return loss.sum()
        else:
            return loss

class FocalLossClassification(nn.Module):
    """
    Focal Loss for multi-class classification.
    """
    def __init__(self, alpha: float = 0.25, gamma: float = 2.0, reduction: str = 'mean'):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction
        self.ce_loss = nn.CrossEntropyLoss(reduction='none')

    def forward(self, pred: Tensor, target: Tensor) -> Tensor:
        """
        Args:
            pred (Tensor): Logits from the model, shape (N, C).
            target (Tensor): Ground truth labels, shape (N).
        """
        ce = self.ce_loss(pred, target)
        pt = torch.exp(-ce)
        focal_loss = self.alpha * (1 - pt) ** self.gamma * ce

        if self.reduction == 'mean':
            return focal_loss.mean()
        elif self.reduction == 'sum':
            return focal_loss.sum()
        else:
            return focal_loss

# --- Object Detection Losses ---

class GIoULoss(nn.Module):
    """
    Generalized Intersection over Union Loss.
    """
    def __init__(self, reduction: str = 'mean'):
        super().__init__()
        self.reduction = reduction

    def forward(self, pred_boxes: Tensor, target_boxes: Tensor) -> Tensor:
        """
        Args:
            pred_boxes (Tensor): Predicted boxes, shape (N, 4), format (cx, cy, w, h).
            target_boxes (Tensor): Target boxes, shape (N, 4), format (cx, cy, w, h).
        """
        # Convert to (x1, y1, x2, y2) format
        pred_boxes_xyxy = box_convert(pred_boxes, in_fmt='cxcywh', out_fmt='xyxy')
        target_boxes_xyxy = box_convert(target_boxes, in_fmt='cxcywh', out_fmt='xyxy')

        # GIoU is 1 - gIoU
        giou = generalized_box_iou(pred_boxes_xyxy, target_boxes_xyxy)
        loss = 1 - torch.diag(giou)

        if self.reduction == 'mean':
            return loss.mean()
        elif self.reduction == 'sum':
            return loss.sum()
        else:
            return loss

class DETRLoss(nn.Module):
    """
    This class computes the loss for DETR.
    The process happens in two steps:
    1) We compute hungarian assignment between ground truth boxes and the outputs of the model
    2) We supervise each pair of matched ground-truth / prediction
    """
    def __init__(self, num_classes: int, eos_coef: float,
                 cost_class: float = 1.0, cost_bbox: float = 5.0, cost_giou: float = 2.0):
        """
        Args:
            num_classes (int): Number of object categories, not including the special "no object" class.
            eos_coef (float): Relative classification weight of the "no object" class.
            cost_class (float): Weight for classification cost in matcher.
            cost_bbox (float): Weight for L1 box cost in matcher.
            cost_giou (float): Weight for GIoU cost in matcher.
        """
        super().__init__()
        if linear_sum_assignment is None:
            raise RuntimeError("scipy is required for DETRLoss.")
            
        self.num_classes = num_classes
        self.eos_coef = eos_coef # "end of sentence" coefficient for no-object class
        
        # Matcher costs
        self.cost_class = cost_class
        self.cost_bbox = cost_bbox
        self.cost_giou = cost_giou
        
        # Loss weights (used after matching)
        self.l1_loss = nn.L1Loss(reduction='none')
        self.giou_loss = GIoULoss(reduction='none')
        
        # Prepare weight tensor for classification loss
        empty_weight = torch.ones(self.num_classes + 1)
        empty_weight[-1] = self.eos_coef
        self.register_buffer('empty_weight', empty_weight)

    @torch.no_grad()
    def _matcher(self, outputs: Dict[str, Tensor], targets: List[Dict[str, Tensor]]) -> List[Tuple[Tensor, Tensor]]:
        """
        Performs the Hungarian matching between predictions and ground truth.

        Args:
            outputs (Dict): Model outputs, containing 'pred_logits' and 'pred_boxes'.
            targets (List[Dict]): A list of targets, one for each image in the batch.

        Returns:
            A list of tuples (row_ind, col_ind) for each image, where row_ind are
            indices of the matched predictions and col_ind are indices of the matched targets.
        """
        bs, num_queries = outputs["pred_logits"].shape[:2]

        # We flatten to compute the cost matrices in a batch
        out_prob = outputs["pred_logits"].flatten(0, 1).softmax(-1)  # [batch_size * num_queries, num_classes + 1]
        out_bbox = outputs["pred_boxes"].flatten(0, 1)  # [batch_size * num_queries, 4]

        # Also concat the target boxes and labels
        tgt_ids = torch.cat([v["labels"] for v in targets])
        tgt_bbox = torch.cat([v["boxes"] for v in targets])

        # Compute the classification cost.
        cost_class = -out_prob[:, tgt_ids]

        # Compute the L1 cost between boxes
        cost_bbox = torch.cdist(out_bbox, tgt_bbox, p=1)

        # Compute the GIoU cost between boxes
        cost_giou = -generalized_box_iou(box_convert(out_bbox, in_fmt='cxcywh', out_fmt='xyxy'),
                                         box_convert(tgt_bbox, in_fmt='cxcywh', out_fmt='xyxy'))

        # Final cost matrix
        C = self.cost_bbox * cost_bbox + self.cost_class * cost_class + self.cost_giou * cost_giou
        C = C.view(bs, num_queries, -1).cpu()

        sizes = [len(v["boxes"]) for v in targets]
        indices = [linear_sum_assignment(c[i]) for i, c in enumerate(C.split(sizes, -1))]
        
        return [(torch.as_tensor(i, dtype=torch.int64), torch.as_tensor(j, dtype=torch.int64)) for i, j in indices]

    def _get_src_permutation_idx(self, indices: List[Tuple[Tensor, Tensor]]) -> Tuple[Tensor, Tensor]:
        # permute predictions following indices
        batch_idx = torch.cat([torch.full_like(src, i) for i, (src, _) in enumerate(indices)])
        src_idx = torch.cat([src for (src, _) in indices])
        return batch_idx, src_idx

    def _get_tgt_permutation_idx(self, indices: List[Tuple[Tensor, Tensor]]) -> Tuple[Tensor, Tensor]:
        # permute targets following indices
        batch_idx = torch.cat([torch.full_like(tgt, i) for i, (_, tgt) in enumerate(indices)])
        tgt_idx = torch.cat([tgt for (_, tgt) in indices])
        return batch_idx, tgt_idx

    def forward(self, outputs: Dict[str, Tensor], targets: List[Dict[str, Tensor]]) -> Dict[str, Tensor]:
        """
        Loss computation.

        Args:
            outputs (Dict): Must contain 'pred_logits' and 'pred_boxes'.
            targets (List[Dict]): List of dicts, each with 'labels' and 'boxes'.

        Returns:
            A dictionary of losses.
        """
        # Step 1: Perform bipartite matching
        indices = self._matcher(outputs, targets)

        # Get the indices for matched predictions and targets
        src_idx = self._get_src_permutation_idx(indices)
        tgt_idx = self._get_tgt_permutation_idx(indices)

        # --- Compute Classification Loss ---
        pred_logits = outputs['pred_logits']
        
        # Create a target tensor of shape [batch_size, num_queries] full of "no object" class
        target_classes = torch.full(pred_logits.shape[:2], self.num_classes,
                                    dtype=torch.int64, device=pred_logits.device)
        # Assign the correct class to the matched queries
        target_classes[src_idx] = torch.cat([t["labels"][J] for t, (_, J) in zip(targets, indices)])
        
        loss_ce = F.cross_entropy(pred_logits.transpose(1, 2), target_classes, self.empty_weight)

        # --- Compute Box Regression Losses (L1 and GIoU) ---
        # This loss is only computed for the matched pairs
        matched_pred_boxes = outputs['pred_boxes'][src_idx]
        matched_target_boxes = torch.cat([t['boxes'][i] for t, (_, i) in zip(targets, indices)], dim=0)

        loss_bbox = self.l1_loss(matched_pred_boxes, matched_target_boxes).sum() / len(indices)
        loss_giou = self.giou_loss(matched_pred_boxes, matched_target_boxes).sum() / len(indices)

        losses = {
            'loss_ce': loss_ce,
            'loss_bbox': loss_bbox,
            'loss_giou': loss_giou,
        }
        return losses


# --- Example Usage ---

if __name__ == '__main__':
    logging.info("--- Running Loss Functions Demo ---")

    # --- Label Smoothing Demo ---
    logging.info("\n--- Label Smoothing CE Demo ---")
    ls_loss = LabelSmoothingCrossEntropy(smoothing=0.1)
    preds_ls = torch.randn(4, 10) # 4 samples, 10 classes
    targets_ls = torch.randint(0, 10, (4,))
    loss_val_ls = ls_loss(preds_ls, targets_ls)
    logging.info(f"Label Smoothing Loss: {loss_val_ls.item()}")
    assert loss_val_ls.item() > 0

    # --- Focal Loss Classification Demo ---
    logging.info("\n--- Focal Loss Classification Demo ---")
    focal_loss_clf = FocalLossClassification(alpha=0.25, gamma=2.0)
    preds_focal = torch.randn(8, 5) # 8 samples, 5 classes
    targets_focal = torch.randint(0, 5, (8,))
    # Make some predictions very confident to show the effect of focal loss
    preds_focal[0, targets_focal[0]] = 10.0 # Easy example
    preds_focal[1, targets_focal[1]] = -10.0 # Hard example
    loss_val_focal = focal_loss_clf(preds_focal, targets_focal)
    logging.info(f"Focal Loss (Classification): {loss_val_focal.item()}")
    assert loss_val_focal.item() > 0

    # --- DETR Loss Demo ---
    if linear_sum_assignment:
        logging.info("\n--- DETR Loss Demo ---")
        detr_loss_fn = DETRLoss(num_classes=80, eos_coef=0.1)
        
        # Dummy model output
        batch_size = 2
        num_queries = 100
        num_classes = 80
        outputs = {
            'pred_logits': torch.randn(batch_size, num_queries, num_classes + 1),
            'pred_boxes': torch.rand(batch_size, num_queries, 4) # cxcywh format, normalized
        }
        
        # Dummy targets
        targets = [
            {'labels': torch.randint(0, num_classes, (5,)), 'boxes': torch.rand(5, 4)},
            {'labels': torch.randint(0, num_classes, (8,)), 'boxes': torch.rand(8, 4)}
        ]
        
        losses = detr_loss_fn(outputs, targets)
        logging.info(f"DETR Losses: {losses}")
        assert 'loss_ce' in losses and losses['loss_ce'].item() > 0
        assert 'loss_bbox' in losses and losses['loss_bbox'].item() > 0
        assert 'loss_giou' in losses and losses['loss_giou'].item() > 0
    else:
        logging.warning("Skipping DETR loss demo because scipy is not installed.")

    logging.info("\n--- Loss Functions Demo Complete ---")
