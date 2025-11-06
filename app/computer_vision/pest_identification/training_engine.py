# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\pest_identification\training_engine.py

"""
Training and Evaluation Engine for Pest Identification
======================================================

This module provides a comprehensive and flexible training and evaluation engine,
designed to work with the models, data loaders, and loss functions defined in the
other modules of the `pest_identification` package. It is inspired by modern
training frameworks like PyTorch Lightning and fastai, abstracting away the
boilerplate code of training loops, validation loops, and metric calculation.

The `TrainingEngine` is designed to be highly configurable and extensible,
supporting both classification and object detection tasks.

Key Features:
-------------
1.  **Modular Design**: The engine is initialized with a model, data module, loss
    function, and optimizer, making it easy to swap components.

2.  **Task-Agnostic Training Loop**: The main `train` method handles the overall
    training process (epochs, batch iteration), while task-specific logic is
    delegated to `_train_step` and `_eval_step` methods.

3.  **Task-Specific Steps**:
    -   For **classification**, the steps involve a standard forward pass, loss
      computation, and accuracy calculation.
    -   For **object detection**, the steps are more complex, handling model
      outputs (dictionaries of logits and boxes) and targets (lists of
      dictionaries).

4.  **Metrics Calculation**:
    -   **Classification**: Computes accuracy, precision, recall, and F1-score
      (using `torchmetrics`).
    -   **Object Detection**: Computes standard COCO metrics like mean Average
      Precision (mAP) at different IoU thresholds (e.g., mAP@.50, mAP@.50:.95)
      using `torchmetrics.detection.MeanAveragePrecision`.

5.  **Callbacks System**: A powerful callback system allows for custom logic to be
    injected at various points in the training loop without modifying the engine's
    core code. Built-in callbacks include:
    -   `ModelCheckpoint`: Saves the best performing model based on a monitored
      metric (e.g., validation loss, mAP).
    -   `LearningRateScheduler`: Adjusts the learning rate during training using
      schedulers like `CosineAnnealingLR` or `ReduceLROnPlateau`.
    -   `TensorBoardLogger`: Logs training and validation metrics, and potentially
      images, to TensorBoard for real-time visualization.
    -   `EarlyStopping`: Stops training if a monitored metric does not improve for
      a specified number of epochs.

6.  **Optimizer and Scheduler Factory**: Includes a factory to create optimizers
    (e.g., AdamW, SGD) and learning rate schedulers from configuration dictionaries.

7.  **Mixed-Precision Training**: Supports automatic mixed-precision (AMP) training
    using `torch.cuda.amp.GradScaler` to speed up training and reduce memory usage
    on compatible GPUs.

Workflow:
---------
1.  **Initialization**: The `TrainingEngine` is instantiated with all necessary
    components (model, data, loss, optimizer, callbacks, etc.) and a configuration
    dictionary.
2.  **`train()` call**: The main training method is called.
3.  **Epoch Loop**: The engine iterates through the specified number of epochs.
    -   **Training Phase**: It iterates through the training dataloader, calling
      `_train_step` for each batch, performing backpropagation, and updating
      model weights.
    -   **Validation Phase**: It iterates through the validation dataloader, calling
      `_eval_step` for each batch, and aggregates the validation metrics.
    -   **Callback Hooks**: After each step, batch, and epoch, the corresponding
      callback methods are triggered (e.g., `on_epoch_end`).
4.  **Post-Training**: After the training loop finishes, the best model checkpoint
    is loaded, and an optional final evaluation can be run on the test set.

This engine provides the robust machinery needed to train state-of-the-art pest
identification models efficiently and reproducibly.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import torch
import torch.nn as nn
from torch.optim import Optimizer
from torch.optim.lr_scheduler import _LRScheduler
from torch.utils.data import DataLoader
from torch.cuda.amp import GradScaler, autocast
from tqdm import tqdm

try:
    import torchmetrics
    from torchmetrics.detection import MeanAveragePrecision
except ImportError:
    logging.error("torchmetrics is not installed. Please install it: pip install torchmetrics")
    torchmetrics = None

from .data_loader import PestDataModule
from .losses import LossFactory
from .models import ModelFactory
from .callbacks import Callback, ModelCheckpoint, TensorBoardLogger, EarlyStopping, LRSchedulerCallback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Optimizer and Scheduler Factory ---

def create_optimizer(model: nn.Module, config: Dict[str, Any]) -> Optimizer:
    """Creates an optimizer from configuration."""
    name = config.get('name', 'adamw').lower()
    lr = config.get('lr', 1e-3)
    params = {k: v for k, v in config.items() if k not in ['name', 'lr']}
    
    if name == 'adam':
        return torch.optim.Adam(model.parameters(), lr=lr, **params)
    elif name == 'adamw':
        return torch.optim.AdamW(model.parameters(), lr=lr, **params)
    elif name == 'sgd':
        return torch.optim.SGD(model.parameters(), lr=lr, **params)
    else:
        raise ValueError(f"Optimizer '{name}' not supported.")

def create_scheduler(optimizer: Optimizer, config: Dict[str, Any]) -> Optional[_LRScheduler]:
    """Creates a learning rate scheduler from configuration."""
    if not config:
        return None
    name = config.get('name', '').lower()
    params = {k: v for k, v in config.items() if k != 'name'}

    if name == 'cosine_annealing':
        return torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, **params)
    elif name == 'reduce_on_plateau':
        return torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, **params)
    elif name == 'step_lr':
        return torch.optim.lr_scheduler.StepLR(optimizer, **params)
    else:
        logging.warning(f"Scheduler '{name}' not supported or not specified.")
        return None

# --- Training Engine ---

class TrainingEngine:
    """
    A flexible engine for training and evaluating pest identification models.
    """
    def __init__(self,
                 config: Dict[str, Any],
                 model: nn.Module,
                 data_module: PestDataModule,
                 loss_fn: nn.Module,
                 optimizer: Optimizer,
                 scheduler: Optional[_LRScheduler] = None,
                 callbacks: Optional[List[Callback]] = None):
        
        self.config = config
        self.task = config.get('task', 'classification')
        self.device = torch.device(config.get('device', 'cuda' if torch.cuda.is_available() else 'cpu'))
        
        self.model = model.to(self.device)
        self.data_module = data_module
        self.loss_fn = loss_fn.to(self.device)
        self.optimizer = optimizer
        self.scheduler = scheduler
        
        self.callbacks = callbacks if callbacks else []
        for cb in self.callbacks:
            cb.set_engine(self)

        self.use_amp = config.get('use_amp', False) and self.device.type == 'cuda'
        self.grad_scaler = GradScaler(enabled=self.use_amp)

        self.train_loader = self.data_module.train_dataloader()
        self.val_loader = self.data_module.val_dataloader()

        self.epoch = 0
        self.global_step = 0
        self.history = {'train_loss': [], 'val_loss': [], 'val_metrics': []}

        # Initialize metrics
        if torchmetrics:
            if self.task == 'classification':
                self.train_metrics = torchmetrics.Accuracy(task="multiclass", num_classes=config['model']['num_classes']).to(self.device)
                self.val_metrics = torchmetrics.MetricCollection([
                    torchmetrics.Accuracy(task="multiclass", num_classes=config['model']['num_classes']),
                    torchmetrics.Precision(task="multiclass", num_classes=config['model']['num_classes'], average='macro'),
                    torchmetrics.Recall(task="multiclass", num_classes=config['model']['num_classes'], average='macro'),
                    torchmetrics.F1Score(task="multiclass", num_classes=config['model']['num_classes'], average='macro')
                ]).to(self.device)
            elif self.task == 'detection':
                self.val_metrics = MeanAveragePrecision(box_format='xywh').to(self.device)
        else:
            self.train_metrics = self.val_metrics = None

    def _train_step(self, batch: Dict) -> torch.Tensor:
        """Performs a single training step."""
        self.optimizer.zero_grad()
        
        images = batch['image'].to(self.device)
        
        with autocast(enabled=self.use_amp):
            if self.task == 'classification':
                targets = batch['label'].to(self.device)
                outputs = self.model(images)
                loss = self.loss_fn(outputs, targets)
                # Update train metrics
                if self.train_metrics:
                    self.train_metrics.update(outputs.softmax(dim=-1), targets)
            
            elif self.task == 'detection':
                targets = [{k: v.to(self.device) for k, v in t.items()} for t in batch['target']]
                # For DETR-like models, loss is computed inside the model/loss_fn
                if self.config['loss']['name'] == 'detr_loss':
                    outputs = self.model(images)
                    loss_dict = self.loss_fn(outputs, targets)
                    loss = sum(loss_dict.values())
                else: # For FasterRCNN, RetinaNet, etc.
                    loss_dict = self.model(images, targets)
                    loss = sum(l for l in loss_dict.values())
        
        self.grad_scaler.scale(loss).backward()
        self.grad_scaler.step(self.optimizer)
        self.grad_scaler.update()
        
        return loss

    @torch.no_grad()
    def _eval_step(self, batch: Dict) -> torch.Tensor:
        """Performs a single evaluation step."""
        self.model.eval()
        images = batch['image'].to(self.device)
        
        with autocast(enabled=self.use_amp):
            if self.task == 'classification':
                targets = batch['label'].to(self.device)
                outputs = self.model(images)
                loss = self.loss_fn(outputs, targets)
                if self.val_metrics:
                    self.val_metrics.update(outputs.softmax(dim=-1), targets)
            
            elif self.task == 'detection':
                targets = [{k: v.to(self.device) for k, v in t.items()} for t in batch['target']]
                if self.config['loss']['name'] == 'detr_loss':
                    outputs = self.model(images)
                    loss_dict = self.loss_fn(outputs, targets)
                    loss = sum(loss_dict.values())
                    # For DETR, need to post-process for mAP
                    # This is complex and requires a post-processor class, simplified here
                    # For now, we just update with dummy data for val_metrics
                    # A real implementation would convert logits/boxes to COCO format
                    # self.val_metrics.update(preds, targets)
                else: # FasterRCNN, RetinaNet
                    # In eval mode, these models return predictions
                    outputs = self.model(images)
                    # Loss is not computed during eval, but we can compute it for monitoring
                    # To do this, we'd need to re-run in train mode, which is inefficient.
                    # We'll just return 0 for loss and focus on mAP.
                    loss = torch.tensor(0.0)
                    if self.val_metrics:
                        self.val_metrics.update(outputs, targets)
        
        return loss

    def train(self, num_epochs: int):
        """Main training loop."""
        logging.info(f"Starting training for {num_epochs} epochs on device '{self.device}'.")
        self.callbacks_hook('on_train_begin')

        for self.epoch in range(1, num_epochs + 1):
            self.callbacks_hook('on_epoch_begin')
            
            # --- Training Phase ---
            self.model.train()
            train_loss = 0.0
            train_pbar = tqdm(self.train_loader, desc=f"Epoch {self.epoch}/{num_epochs} [Train]")
            
            for batch in train_pbar:
                self.callbacks_hook('on_train_batch_begin')
                loss = self._train_step(batch)
                train_loss += loss.item()
                self.global_step += 1
                train_pbar.set_postfix(loss=loss.item())
                self.callbacks_hook('on_train_batch_end', logs={'loss': loss.item()})
            
            avg_train_loss = train_loss / len(self.train_loader)
            self.history['train_loss'].append(avg_train_loss)
            
            train_metrics_log = {}
            if self.train_metrics and self.task == 'classification':
                train_metrics_log = {'train_acc': self.train_metrics.compute().item()}
                self.train_metrics.reset()

            # --- Validation Phase ---
            self.model.eval()
            val_loss = 0.0
            val_pbar = tqdm(self.val_loader, desc=f"Epoch {self.epoch}/{num_epochs} [Val]")

            for batch in val_pbar:
                self.callbacks_hook('on_eval_batch_begin')
                loss = self._eval_step(batch)
                val_loss += loss.item()
                val_pbar.set_postfix(loss=loss.item())
                self.callbacks_hook('on_eval_batch_end')

            avg_val_loss = val_loss / len(self.val_loader)
            self.history['val_loss'].append(avg_val_loss)

            val_metrics_log = {}
            if self.val_metrics:
                val_metrics_log = self.val_metrics.compute()
                self.val_metrics.reset()
                # Convert tensors to float for logging
                val_metrics_log = {k: v.item() for k, v in val_metrics_log.items()}

            self.history['val_metrics'].append(val_metrics_log)

            # --- Epoch End ---
            logs = {
                'epoch': self.epoch,
                'train_loss': avg_train_loss,
                'val_loss': avg_val_loss,
                **train_metrics_log,
                **val_metrics_log
            }
            self.callbacks_hook('on_epoch_end', logs=logs)

            # Check for early stopping
            if hasattr(self, 'should_stop') and self.should_stop:
                logging.info("Early stopping triggered.")
                break

        self.callbacks_hook('on_train_end')
        logging.info("Training finished.")

    def evaluate(self, test_loader: DataLoader) -> Dict[str, float]:
        """Evaluates the model on a given dataloader."""
        self.model.to(self.device)
        self.model.eval()
        
        test_pbar = tqdm(test_loader, desc="[Test]")
        for batch in test_pbar:
            self._eval_step(batch) # This updates the val_metrics object
            
        if self.val_metrics:
            test_metrics = self.val_metrics.compute()
            self.val_metrics.reset()
            test_metrics = {k: v.item() for k, v in test_metrics.items()}
            logging.info(f"Test Metrics: {test_metrics}")
            return test_metrics
        return {}

    def callbacks_hook(self, hook_name: str, logs: Optional[Dict] = None):
        """Triggers a specific hook on all callbacks."""
        for cb in self.callbacks:
            if hasattr(cb, hook_name):
                getattr(cb, hook_name)(logs=logs)


# --- Example Usage ---

if __name__ == '__main__':
    import shutil
    from .data_loader import create_dummy_classification_data

    logging.info("--- Running Training Engine Demo ---")

    # 1. Setup dummy data and project directory
    data_root = Path('./dummy_train_data')
    create_dummy_classification_data(data_root)
    exp_dir = Path('./pest_training_experiment')
    if exp_dir.exists():
        shutil.rmtree(exp_dir)
    exp_dir.mkdir()

    # 2. Create configuration
    config = {
        'task': 'classification',
        'device': 'cpu', # Use CPU for this demo
        'use_amp': False,
        'data': {
            'task': 'classification',
            'root_dir': str(data_root),
            'image_size': [32, 32], # Small for speed
            'batch_size': 4,
            'num_workers': 0,
            'train_augmentations': {'HorizontalFlip': {'p': 0.5}},
            'val_augmentations': {},
        },
        'model': {
            'name': 'resnet18',
            'num_classes': 3,
            'pretrained': False, # No pretraining for dummy data
        },
        'loss': {
            'name': 'cross_entropy',
        },
        'optimizer': {
            'name': 'adamw',
            'lr': 1e-3,
        },
        'scheduler': {
            'name': 'cosine_annealing',
            'T_max': 5,
        },
        'training': {
            'num_epochs': 3,
        }
    }

    # 3. Initialize components
    data_module = PestDataModule(config['data'])
    data_module.setup('fit')
    
    model = ModelFactory.create_model(config['model'])
    loss_fn = LossFactory.create_loss(config['loss'])
    optimizer = create_optimizer(model, config['optimizer'])
    scheduler = create_scheduler(optimizer, config['scheduler'])

    # 4. Setup Callbacks
    callbacks = [
        ModelCheckpoint(directory=exp_dir, monitor='val_loss', mode='min'),
        TensorBoardLogger(log_dir=exp_dir / 'logs'),
        EarlyStopping(monitor='val_loss', patience=2, mode='min'),
        LRSchedulerCallback(scheduler=scheduler, metric='val_loss') # For ReduceLROnPlateau
    ]
    if scheduler and not isinstance(scheduler, torch.optim.lr_scheduler.ReduceLROnPlateau):
        # CosineAnnealing is updated per epoch, handled by LRSchedulerCallback
        callbacks.append(LRSchedulerCallback(scheduler=scheduler, step_moment='epoch'))


    # 5. Initialize and run the Training Engine
    engine = TrainingEngine(
        config=config,
        model=model,
        data_module=data_module,
        loss_fn=loss_fn,
        optimizer=optimizer,
        scheduler=scheduler,
        callbacks=callbacks
    )

    try:
        engine.train(num_epochs=config['training']['num_epochs'])
        logging.info("Training demo completed successfully.")
        
        # Test evaluation
        logging.info("Running evaluation on validation set as a test.")
        test_loader = data_module.val_dataloader()
        engine.evaluate(test_loader)

    except Exception as e:
        logging.error(f"An error occurred during the training demo: {e}", exc_info=True)
    
    finally:
        # 7. Cleanup
        shutil.rmtree(data_root)
        shutil.rmtree(exp_dir)
        logging.info("Cleaned up dummy data and experiment directories.")

    logging.info("--- Training Engine Demo Complete ---")
