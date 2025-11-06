"""
Main Training Orchestrator for Yield Estimation
================================================

This script serves as the main entry point for training a yield estimation model.
It orchestrates the entire training pipeline, from data loading and model
creation to the training loop and final model saving. It is designed to be
highly configurable through a central settings object.

Key Responsibilities:
---------------------
1.  **Configuration Loading**:
    -   Loads all configurations from the `Settings` object provided by
      `utils.config.get_settings()`. This includes data paths, model choices,
      and training hyperparameters.

2.  **Data Pipeline Setup**:
    -   Calls `create_dataloaders` to get the training, validation, and test
      data loaders. The setup is entirely driven by the `DataConfig` and
      `TrainConfig` sections of the settings.

3.  **Model Initialization**:
    -   Uses the `ModelFactory` to create the specified model architecture. The
      choice of model (e.g., 'faster_rcnn', 'unet', 'cnn_regressor') and its
      specific hyperparameters are read from the `ModelConfig`.
    -   Moves the model to the selected device (CPU or GPU).

4.  **Optimizer and Scheduler Setup**:
    -   Configures the optimizer (e.g., AdamW, SGD) and learning rate scheduler
      (e.g., Cosine Annealing, StepLR) based on the `TrainConfig`.

5.  **Training and Evaluation Loop**:
    -   Iterates for the specified number of epochs.
    -   In each epoch, it calls the `train_one_epoch` function from the `engine`
      module to perform one full pass over the training data.
    -   After each training epoch, it calls the `evaluate` function to measure
      the model's performance on the validation set.
    -   The primary validation metric (mAP, mIoU, or MSE) is used to track the
      best performing model.

6.  **Model Checkpointing and Artifacts**:
    -   Saves a checkpoint of the model, optimizer state, and other relevant info
      at the end of each epoch.
    -   Keeps track of the best model based on the validation metric and saves a
      separate `best_model.pth` file.
    -   Can be extended to log metrics to experiment tracking tools like MLflow
      or TensorBoard.

7.  **Command-Line Interface**:
    -   Uses `argparse` to allow for key configurations (like task type and model
      choice) to be specified at runtime, overriding the defaults if necessary.

This script provides a robust and reusable template for training any model within
the yield estimation framework.
"""

import argparse
import torch
from torch.optim.lr_scheduler import StepLR, CosineAnnealingLR
import logging
import os

from app.computer_vision.yield_estimation.utils.config import get_settings, Settings
from app.computer_vision.yield_estimation.utils.logging_config import setup_logging
from app.computer_vision.yield_estimation.data.loader import create_dataloaders
from app.computer_vision.yield_estimation.models.factory import ModelFactory
from app.computer_vision.yield_estimation.engine import train_one_epoch, evaluate

def get_args_parser():
    """Defines command-line arguments for the training script."""
    parser = argparse.ArgumentParser(description="Yield Estimation Model Training")
    parser.add_argument('--task', required=True, choices=['detection', 'segmentation', 'regression'],
                        help="The type of task to train.")
    parser.add_argument('--model-key', required=True,
                        help="The key for the model config in settings.json (e.g., 'default_detection').")
    parser.add_argument('--modalities', nargs='+', default=['rgb'],
                        help="List of image modalities to use (e.g., rgb nir).")
    return parser

def main(args):
    """Main training function."""
    # --- Setup ---
    settings = get_settings()
    setup_logging(log_level=settings.log_level)
    logger = logging.getLogger(__name__)

    device = torch.device(settings.train.device if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")

    if not os.path.exists(settings.train.checkpoint_dir):
        os.makedirs(settings.train.checkpoint_dir)

    # --- Data Loading ---
    dataloaders = create_dataloaders(settings, task=args.task, modalities=args.modalities)
    train_loader = dataloaders['train']
    val_loader = dataloaders['val']

    # --- Model Initialization ---
    model_config = settings.models.get(args.model_key)
    if model_config is None:
        raise ValueError(f"Model key '{args.model_key}' not found in settings.")
    
    factory = ModelFactory()
    model = factory.create_model(task_type=args.task, model_config=model_config, pretrained=True)
    model.to(device)

    # --- Optimizer and Scheduler ---
    params = [p for p in model.parameters() if p.requires_grad]
    if settings.train.optimizer == 'adamw':
        optimizer = torch.optim.AdamW(params, lr=settings.train.learning_rate, weight_decay=settings.train.weight_decay)
    elif settings.train.optimizer == 'sgd':
        optimizer = torch.optim.SGD(params, lr=settings.train.learning_rate, momentum=0.9, weight_decay=settings.train.weight_decay)
    else:
        raise NotImplementedError(f"Optimizer '{settings.train.optimizer}' not supported.")

    if settings.train.scheduler == 'cosine_annealing':
        scheduler = CosineAnnealingLR(optimizer, T_max=settings.train.epochs, eta_min=1e-6)
    else: # Default to StepLR
        scheduler = StepLR(optimizer, step_size=settings.train.patience, gamma=0.1)

    # --- AMP Grad Scaler ---
    amp_scaler = torch.cuda.amp.GradScaler() if settings.train.amp and device.type == 'cuda' else None
    if amp_scaler:
        logger.info("Using Automatic Mixed Precision (AMP).")

    # --- Training Loop ---
    logger.info(f"Starting training for {settings.train.epochs} epochs...")
    best_metric = -1.0 if args.task != 'regression' else float('inf')

    for epoch in range(settings.train.epochs):
        train_metrics = train_one_epoch(
            model, optimizer, train_loader, device, epoch, args.task, settings.train.log_interval, amp_scaler
        )
        
        eval_metrics = evaluate(model, val_loader, device, args.task)
        
        scheduler.step()

        # --- Checkpointing ---
        current_metric = 0
        if args.task == 'detection':
            current_metric = eval_metrics['coco_evaluator'].coco_eval['bbox'].stats[0] # mAP
        elif args.task == 'segmentation':
            current_metric = eval_metrics['mIoU']
        elif args.task == 'regression':
            current_metric = eval_metrics['mse']

        is_best = (current_metric > best_metric) if args.task != 'regression' else (current_metric < best_metric)
        if is_best:
            best_metric = current_metric
            logger.info(f"New best model found! Metric: {best_metric:.4f}. Saving to 'best_model.pth'.")
            save_path = os.path.join(settings.train.checkpoint_dir, f"{args.task}_best_model.pth")
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'metric': best_metric,
                'model_config': model_config.dict()
            }, save_path)

        logger.info(f"Epoch {epoch+1}/{settings.train.epochs} | Train Loss: {train_metrics['train_loss']:.4f} | Val Metric: {current_metric:.4f}")

    logger.info("Training finished.")

if __name__ == '__main__':
    parser = get_args_parser()
    args = parser.parse_args()
    main(args)
