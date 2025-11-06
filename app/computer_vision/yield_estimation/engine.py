"""
Training and Evaluation Engine for Yield Estimation
====================================================

This module provides the core functions for model training and evaluation. It is
designed to be generic enough to handle the different tasks involved in yield
estimation: object detection, semantic segmentation, and direct regression.

The engine contains two primary functions: `train_one_epoch` and `evaluate`.
These functions encapsulate the standard PyTorch training and validation loops,
but with added flexibility to accommodate different model outputs and loss
calculations.

Core Components:
----------------
1.  **`train_one_epoch`**:
    -   **Purpose**: Executes a single pass over the entire training dataset.
    -   **Functionality**:
        -   Sets the model to training mode (`model.train()`).
        -   Iterates over the training data loader.
        -   Moves data and targets to the specified device (e.g., GPU).
        -   Performs the forward pass.
        -   **Task-Specific Loss Calculation**: The key feature is its ability to
          handle different model outputs. For detection models from `torchvision`,
          the model itself returns a dictionary of losses when in training mode.
          For segmentation and regression, a separate loss function must be computed.
        -   Performs the backward pass and optimizer step.
        -   Logs metrics like loss and learning rate at regular intervals.
    -   **AMP Support**: Integrates with `torch.cuda.amp.GradScaler` for Automatic
      Mixed Precision training, which can significantly speed up training on
      compatible GPUs.

2.  **`evaluate`**:
    -   **Purpose**: Evaluates the model's performance on a validation or test dataset.
    -   **Functionality**:
        -   Sets the model to evaluation mode (`model.eval()`).
        -   Disables gradient calculations (`with torch.no_grad()`).
        -   Iterates over the validation data loader.
        -   Performs the forward pass.
        -   **Task-Specific Metric Calculation**:
            -   For **detection**, it formats the model outputs and uses the
              `pycocotools` library to compute standard object detection metrics
              like mean Average Precision (mAP).
            -   For **segmentation**, it calculates metrics like Intersection over
              Union (IoU) and Dice score.
            -   For **regression**, it computes metrics like Mean Squared Error (MSE)
              and Mean Absolute Error (MAE).
        -   Aggregates the metrics over the entire dataset and returns a summary.

This modular engine separates the core training logic from the orchestration
script, making the code cleaner and more reusable. It provides the computational
heart of the yield estimation pipeline.
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import math
import sys
import logging
from typing import Dict, List, Any, Literal

# Import evaluation utilities
from .utils.coco_utils import get_coco_api_from_dataset
from .utils.coco_eval import CocoEvaluator
from .utils.segmentation_metrics import SegmentationMetrics
from .utils.regression_metrics import RegressionMetrics

logger = logging.getLogger(__name__)

def train_one_epoch(model: nn.Module, 
                    optimizer: torch.optim.Optimizer, 
                    data_loader: DataLoader, 
                    device: torch.device, 
                    epoch: int, 
                    task: Literal['detection', 'segmentation', 'regression'],
                    log_interval: int,
                    amp_scaler: torch.cuda.amp.GradScaler = None) -> Dict[str, float]:
    """
    Trains the model for one epoch.
    """
    model.train()
    
    # Custom loss functions for tasks not handled by the model directly
    if task == 'segmentation':
        # CrossEntropyLoss is common for multi-class segmentation
        criterion = nn.CrossEntropyLoss()
    elif task == 'regression':
        # MSE is common for regression
        criterion = nn.MSELoss()

    running_loss = 0.0
    for i, (images, targets) in enumerate(data_loader):
        # Move images to device
        images_on_device = {k: v.to(device) for k, v in images.items()}

        # --- Forward Pass ---
        with torch.cuda.amp.autocast(enabled=amp_scaler is not None):
            if task == 'detection':
                # For torchvision detection models, just pass images and targets.
                # The model returns a dict of losses in training mode.
                targets_on_device = [{k: v.to(device) for k, v in t.items()} for t in targets]
                loss_dict = model(list(images_on_device.values()), targets_on_device)
                losses = sum(loss for loss in loss_dict.values())
            else:
                # For segmentation and regression
                outputs = model(images_on_device)
                if task == 'segmentation':
                    targets_on_device = targets['mask'].to(device)
                    losses = criterion(outputs, targets_on_device)
                elif task == 'regression':
                    targets_on_device = targets.to(device)
                    losses = criterion(outputs, targets_on_device)

        loss_value = losses.item()
        running_loss += loss_value

        if not math.isfinite(loss_value):
            logger.error(f"Loss is {loss_value}, stopping training.")
            sys.exit(1)

        # --- Backward Pass ---
        optimizer.zero_grad()
        if amp_scaler:
            amp_scaler.scale(losses).backward()
            amp_scaler.step(optimizer)
            amp_scaler.update()
        else:
            losses.backward()
            optimizer.step()

        # --- Logging ---
        if (i + 1) % log_interval == 0:
            lr = optimizer.param_groups[0]["lr"]
            logger.info(f"Epoch [{epoch+1}] Batch [{i+1}/{len(data_loader)}] Loss: {loss_value:.4f} LR: {lr:.6f}")

    avg_loss = running_loss / len(data_loader)
    return {'train_loss': avg_loss}


@torch.no_grad()
def evaluate(model: nn.Module, 
             data_loader: DataLoader, 
             device: torch.device, 
             task: Literal['detection', 'segmentation', 'regression']) -> Dict[str, Any]:
    """
    Evaluates the model on the given dataset.
    """
    model.eval()
    
    if task == 'detection':
        coco = get_coco_api_from_dataset(data_loader.dataset)
        coco_evaluator = CocoEvaluator(coco, ['bbox'])
    elif task == 'segmentation':
        seg_metrics = SegmentationMetrics(num_classes=model.segmentation_head[0].out_channels)
    elif task == 'regression':
        reg_metrics = RegressionMetrics()

    logger.info(f"Starting evaluation for task '{task}'...")
    for images, targets in data_loader:
        images_on_device = {k: v.to(device) for k, v in images.items()}
        
        outputs = model(list(images_on_device.values()))

        if task == 'detection':
            outputs = [{k: v.to(torch.device("cpu")) for k, v in t.items()} for t in outputs]
            res = {target["image_id"].item(): output for target, output in zip(targets, outputs)}
            coco_evaluator.update(res)
        else:
            if task == 'segmentation':
                targets_on_device = targets['mask'].to(device)
                seg_metrics.update(outputs, targets_on_device)
            elif task == 'regression':
                targets_on_device = targets.to(device)
                reg_metrics.update(outputs, targets_on_device)

    logger.info("Evaluation finished.")
    
    # --- Aggregate and Return Metrics ---
    if task == 'detection':
        coco_evaluator.synchronize_between_processes()
        coco_evaluator.accumulate()
        coco_evaluator.summarize()
        return {'coco_evaluator': coco_evaluator}
    elif task == 'segmentation':
        metrics = seg_metrics.get_metrics()
        logger.info(f"Segmentation Metrics - mIoU: {metrics['mIoU']:.4f}, Dice: {metrics['dice']:.4f}")
        return metrics
    elif task == 'regression':
        metrics = reg_metrics.get_metrics()
        logger.info(f"Regression Metrics - MSE: {metrics['mse']:.4f}, MAE: {metrics['mae']:.4f}, R2: {metrics['r2']:.4f}")
        return metrics
    
    return {}
