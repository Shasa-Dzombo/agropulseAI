# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\pest_identification\callbacks.py

"""
Callbacks for the Training Engine
=================================

This module defines a system of callbacks for the `TrainingEngine`. Callbacks are
self-contained programs that can be injected into the training loop to perform
custom actions at various stages, such as at the beginning or end of an epoch,
or after a training batch.

This design keeps the `TrainingEngine` clean and focused on the core training
logic, while allowing for complex, stateful behaviors to be added in a modular
and reusable way.

Key Features:
-------------
1.  **`Callback` Base Class**: A simple base class that all other callbacks inherit
    from. It defines the interface of hooks that the `TrainingEngine` will call.
    The hooks include:
    -   `on_train_begin`, `on_train_end`
    -   `on_epoch_begin`, `on_epoch_end`
    -   `on_train_batch_begin`, `on_train_batch_end`
    -   `on_eval_begin`, `on_eval_end`
    -   `on_eval_batch_begin`, `on_eval_batch_end`

2.  **`ModelCheckpoint`**: One of the most critical callbacks. It monitors a specified
    metric (e.g., `val_loss`, `val_mAP`) and saves the model's state dictionary
    whenever the metric improves. This ensures that you always have access to the
    best performing model from the training run.
    -   Supports `min` and `max` modes for monitoring.
    -   Can save only the best model or all models that show improvement.

3.  **`TensorBoardLogger`**: Integrates with TensorBoard for powerful real-time
    visualization of the training process.
    -   Logs scalar metrics like training/validation loss and accuracy.
    -   Can be extended to log images with bounding boxes, model graphs, and
      hyperparameter configurations.

4.  **`EarlyStopping`**: Prevents wasting resources by stopping the training process
    if a monitored metric fails to improve for a specified number of "patience"
    epochs. This helps to avoid overfitting.

5.  **`LRSchedulerCallback`**: A generic callback to handle the stepping of PyTorch's
    learning rate schedulers. It can be configured to step at the end of each
    epoch (e.g., for `CosineAnnealingLR`) or based on a metric from the validation
    loop (for `ReduceLROnPlateau`).

6.  **`ProgressLogger`**: A simple callback that prints a formatted summary of the
    metrics at the end of each epoch to the console.

This callback system makes the training pipeline highly extensible. Custom callbacks
can be easily written to perform actions like sending notifications, profiling code,
or performing complex model-specific validations during training.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import torch
import torch.nn as nn

try:
    from torch.utils.tensorboard import SummaryWriter
except ImportError:
    SummaryWriter = None

# Forward declaration for type hinting
class TrainingEngine:
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Base Callback ---

class Callback:
    """
    Abstract base class for creating callbacks.
    """
    def __init__(self):
        self.engine: Optional[TrainingEngine] = None

    def set_engine(self, engine: 'TrainingEngine'):
        self.engine = engine

    def on_train_begin(self, logs: Optional[Dict] = None): pass
    def on_train_end(self, logs: Optional[Dict] = None): pass
    def on_epoch_begin(self, logs: Optional[Dict] = None): pass
    def on_epoch_end(self, logs: Optional[Dict] = None): pass
    def on_train_batch_begin(self, logs: Optional[Dict] = None): pass
    def on_train_batch_end(self, logs: Optional[Dict] = None): pass
    def on_eval_begin(self, logs: Optional[Dict] = None): pass
    def on_eval_end(self, logs: Optional[Dict] = None): pass
    def on_eval_batch_begin(self, logs: Optional[Dict] = None): pass
    def on_eval_batch_end(self, logs: Optional[Dict] = None): pass


# --- Built-in Callbacks ---

class ModelCheckpoint(Callback):
    """
    Saves the model when a monitored metric improves.
    """
    def __init__(self,
                 directory: str,
                 filename: str = 'best_model.pth',
                 monitor: str = 'val_loss',
                 mode: str = 'min',
                 save_best_only: bool = True):
        super().__init__()
        self.directory = Path(directory)
        self.filename = filename
        self.monitor = monitor
        self.mode = mode
        self.save_best_only = save_best_only
        
        self.directory.mkdir(parents=True, exist_ok=True)

        if mode == 'min':
            self.best_metric = float('inf')
            self.monitor_op = lambda current, best: current < best
        elif mode == 'max':
            self.best_metric = float('-inf')
            self.monitor_op = lambda current, best: current > best
        else:
            raise ValueError(f"Mode '{mode}' is not supported. Use 'min' or 'max'.")

    def on_epoch_end(self, logs: Optional[Dict] = None):
        current_metric = logs.get(self.monitor)
        if current_metric is None:
            logging.warning(f"ModelCheckpoint monitored metric '{self.monitor}' not found in logs. Skipping.")
            return

        if self.monitor_op(current_metric, self.best_metric):
            logging.info(f"Metric '{self.monitor}' improved from {self.best_metric:.6f} to {current_metric:.6f}. Saving model.")
            self.best_metric = current_metric
            self._save_model()

    def _save_model(self):
        if self.engine is None: return
        
        filepath = self.directory / self.filename
        torch.save(self.engine.model.state_dict(), filepath)
        logging.info(f"Model saved to {filepath}")


class TensorBoardLogger(Callback):
    """
    Logs metrics to TensorBoard.
    """
    def __init__(self, log_dir: str):
        super().__init__()
        if SummaryWriter is None:
            raise ImportError("TensorBoard is not available. Please install it: pip install tensorboard")
        self.log_dir = log_dir
        self.writer = SummaryWriter(log_dir=self.log_dir)
        logging.info(f"TensorBoard logs will be saved to: {self.log_dir}")

    def on_epoch_end(self, logs: Optional[Dict] = None):
        if logs is None: return
        
        epoch = logs.get('epoch')
        for key, value in logs.items():
            if key != 'epoch':
                self.writer.add_scalar(key, value, epoch)
    
    def on_train_batch_end(self, logs: Optional[Dict] = None):
        if self.engine is None or logs is None: return
        
        step = self.engine.global_step
        loss = logs.get('loss')
        if loss is not None:
            self.writer.add_scalar('train_batch_loss', loss, step)

    def on_train_end(self, logs: Optional[Dict] = None):
        self.writer.close()
        logging.info("TensorBoard writer closed.")


class EarlyStopping(Callback):
    """
    Stops training when a monitored metric has stopped improving.
    """
    def __init__(self,
                 monitor: str = 'val_loss',
                 patience: int = 5,
                 mode: str = 'min',
                 min_delta: float = 1e-5):
        super().__init__()
        self.monitor = monitor
        self.patience = patience
        self.mode = mode
        self.min_delta = min_delta
        self.wait_count = 0
        
        if mode == 'min':
            self.best_metric = float('inf')
            self.monitor_op = lambda current, best: current < best - self.min_delta
        elif mode == 'max':
            self.best_metric = float('-inf')
            self.monitor_op = lambda current, best: current > best + self.min_delta
        else:
            raise ValueError(f"Mode '{mode}' is not supported. Use 'min' or 'max'.")

    def on_epoch_end(self, logs: Optional[Dict] = None):
        if self.engine is None: return
        
        current_metric = logs.get(self.monitor)
        if current_metric is None:
            logging.warning(f"EarlyStopping monitored metric '{self.monitor}' not found in logs. Skipping.")
            return

        if self.monitor_op(current_metric, self.best_metric):
            self.best_metric = current_metric
            self.wait_count = 0
        else:
            self.wait_count += 1
            logging.info(f"EarlyStopping: Metric '{self.monitor}' did not improve. Patience: {self.wait_count}/{self.patience}")

        if self.wait_count >= self.patience:
            logging.info(f"Early stopping triggered after {self.patience} epochs of no improvement.")
            self.engine.should_stop = True # Signal the engine to stop

    def on_train_begin(self, logs: Optional[Dict] = None):
        if self.engine is None: return
        self.wait_count = 0
        self.engine.should_stop = False


class LRSchedulerCallback(Callback):
    """
    Handles learning rate scheduler updates.
    """
    def __init__(self, scheduler, step_moment: str = 'epoch', metric: Optional[str] = None):
        """
        Args:
            scheduler: The PyTorch LR scheduler.
            step_moment (str): When to step the scheduler ('epoch' or 'batch').
                               'epoch' is default. For ReduceLROnPlateau, this is ignored.
            metric (str, optional): The metric to monitor for ReduceLROnPlateau.
        """
        super().__init__()
        self.scheduler = scheduler
        self.step_moment = step_moment
        self.metric = metric

        if isinstance(self.scheduler, torch.optim.lr_scheduler.ReduceLROnPlateau) and self.metric is None:
            raise ValueError("LRSchedulerCallback requires a 'metric' for ReduceLROnPlateau.")

    def on_epoch_end(self, logs: Optional[Dict] = None):
        if self.scheduler is None: return
        
        if isinstance(self.scheduler, torch.optim.lr_scheduler.ReduceLROnPlateau):
            metric_val = logs.get(self.metric)
            if metric_val is not None:
                self.scheduler.step(metric_val)
            else:
                logging.warning(f"LRScheduler metric '{self.metric}' not found in logs.")
        elif self.step_moment == 'epoch':
            self.scheduler.step()
            
        if self.engine:
            # Log the learning rate
            current_lr = self.engine.optimizer.param_groups[0]['lr']
            logging.info(f"Epoch {logs.get('epoch')}: Learning rate set to {current_lr:.8f}")


    def on_train_batch_end(self, logs: Optional[Dict] = None):
        if self.scheduler and self.step_moment == 'batch' and \
           not isinstance(self.scheduler, torch.optim.lr_scheduler.ReduceLROnPlateau):
            self.scheduler.step()


class ProgressLogger(Callback):
    """
    Logs a summary of metrics to the console at the end of each epoch.
    """
    def on_epoch_end(self, logs: Optional[Dict] = None):
        if logs is None: return
        
        log_str = f"Epoch {logs['epoch']:03d} | "
        log_str += f"Train Loss: {logs.get('train_loss', -1):.5f} | "
        log_str += f"Val Loss: {logs.get('val_loss', -1):.5f} | "
        
        # Add other metrics
        for key, value in logs.items():
            if key not in ['epoch', 'train_loss', 'val_loss']:
                log_str += f"{key}: {value:.5f} | "
        
        logging.info(log_str.strip(" | "))


# --- Example Usage ---

if __name__ == '__main__':
    logging.info("--- Running Callbacks Demo ---")

    # This is a conceptual demo. The callbacks are designed to be used with the TrainingEngine.
    
    # 1. Instantiate callbacks
    model_checkpoint = ModelCheckpoint(directory='./demo_checkpoints', monitor='val_acc', mode='max')
    tensorboard_logger = TensorBoardLogger(log_dir='./demo_logs')
    early_stopping = EarlyStopping(monitor='val_acc', patience=3, mode='max')
    progress_logger = ProgressLogger()

    # 2. Mock TrainingEngine and its state
    class MockEngine:
        def __init__(self):
            self.model = nn.Sequential(nn.Linear(10, 2))
            self.global_step = 0
            self.should_stop = False
            self.optimizer = torch.optim.Adam(self.model.parameters())

    mock_engine = MockEngine()

    # 3. Set the engine for the callbacks
    callbacks = [model_checkpoint, tensorboard_logger, early_stopping, progress_logger]
    for cb in callbacks:
        cb.set_engine(mock_engine)

    # 4. Simulate a training loop and call hooks
    logging.info("\n--- Simulating a training loop ---")
    
    # on_train_begin
    for cb in callbacks: cb.on_train_begin()

    # Simulate 5 epochs
    for epoch in range(1, 6):
        # on_epoch_begin
        for cb in callbacks: cb.on_epoch_begin(logs={'epoch': epoch})

        # Simulate training batches
        for i in range(10):
            mock_engine.global_step += 1
            for cb in callbacks: cb.on_train_batch_end(logs={'loss': 1.0 / (i + 1)})

        # Simulate validation and create logs
        # Let's pretend accuracy is improving for 2 epochs, then stagnates
        val_acc = 0.85 if epoch < 3 else 0.84
        epoch_logs = {
            'epoch': epoch,
            'train_loss': 0.5 / epoch,
            'val_loss': 0.6 / epoch,
            'val_acc': val_acc
        }
        
        # on_epoch_end
        logging.info(f"\n--- End of Epoch {epoch} ---")
        for cb in callbacks: cb.on_epoch_end(logs=epoch_logs)

        if mock_engine.should_stop:
            break
    
    # on_train_end
    for cb in callbacks: cb.on_train_end()

    logging.info("\n--- Callbacks Demo Complete ---")
    logging.info("Check for './demo_checkpoints' and './demo_logs' directories.")

    # Cleanup
    import shutil
    if os.path.exists('./demo_checkpoints'):
        shutil.rmtree('./demo_checkpoints')
    if os.path.exists('./demo_logs'):
        shutil.rmtree('./demo_logs')
