# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\weed_detection\engine.py

"""
Training and Evaluation Engine for Weed Detection Models
========================================================

This module provides the core functions for training and evaluating object
detection models built with PyTorch. It is adapted from the official PyTorch
vision references to provide a standardized, robust, and feature-rich training
loop.

The engine is designed to be generic and can work with any PyTorch object
detection model that follows the standard input/output format (i.e., accepts a
list of images and returns a list of dictionaries with 'boxes', 'labels', and
'scores').

Core Components:
----------------
1.  **`train_one_epoch`**:
    -   **Purpose**: Manages the training process for a single epoch.
    -   **Process**:
        -   Sets the model to training mode (`model.train()`).
        -   Iterates over the data loader, moving images and targets to the
          specified device (CPU or GPU).
        -   Performs the forward pass, which returns a dictionary of losses
          (e.g., classification loss, box regression loss).
        -   Calculates the total loss and performs the backward pass to compute
          gradients.
        -   Updates the model's weights using the optimizer.
        -   Optionally updates the learning rate using a scheduler.
        -   Tracks and prints metrics using a `MetricLogger`.

2.  **`evaluate`**:
    -   **Purpose**: Manages the evaluation process on a validation or test set.
    -   **Process**:
        -   Sets the model to evaluation mode (`model.eval()`).
        -   Iterates over the data loader without computing gradients
          (`torch.no_grad()`).
        -   Performs the forward pass to get model predictions.
        -   Processes the model outputs and formats them for the COCO evaluation API.
        -   Uses `pycocotools` to compute standard object detection metrics, such
          as mean Average Precision (mAP) at different IoU thresholds.
        -   Returns a `CocoEvaluator` object containing the aggregated results.

3.  **`MetricLogger` and `SmoothedValue`**:
    -   Utility classes (inspired by `vision/references/detection/utils.py`)
      for tracking, smoothing, and printing various metrics during training.
    -   This provides a clean and informative log of the training progress,
      showing smoothed loss values, learning rate, and iteration time.

4.  **`CocoEvaluator`**:
    -   A utility class that wraps the standard COCO evaluation tools.
    -   It accumulates predictions from all images in the validation set and
      then runs the official COCO evaluation script to compute mAP, mAR, etc.
    -   This ensures that the model's performance is measured using industry-standard
      metrics, making it comparable to other published results.

This engine abstracts away the boilerplate code of a PyTorch training loop,
allowing the main training script to focus on higher-level orchestration like
epoch management, model saving, and configuration.
"""

import math
import sys
import time
import torch
from collections import defaultdict, deque
import datetime

from coco_eval import CocoEvaluator
from coco_utils import get_coco_api_from_dataset

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Training Function ---

def train_one_epoch(model, optimizer, data_loader, device, epoch, print_freq, scaler=None):
    """
    Trains the model for one epoch.
    """
    model.train()
    metric_logger = MetricLogger(delimiter="  ")
    metric_logger.add_meter("lr", SmoothedValue(window_size=1, fmt="{value:.6f}"))
    header = f"Epoch: [{epoch}]"

    lr_scheduler = None
    if epoch == 0:
        warmup_factor = 1.0 / 1000
        warmup_iters = min(1000, len(data_loader) - 1)
        lr_scheduler = torch.optim.lr_scheduler.LinearLR(
            optimizer, start_factor=warmup_factor, total_iters=warmup_iters
        )

    for images, targets in metric_logger.log_every(data_loader, print_freq, header):
        images = list(image.to(device) for image in images)
        targets = [{k: v.to(device) for k, v in t.items()} for t in targets]

        with torch.cuda.amp.autocast(enabled=scaler is not None):
            loss_dict = model(images, targets)
            losses = sum(loss for loss in loss_dict.values())

        # reduce losses over all GPUs for logging purposes
        loss_dict_reduced = {k: v.item() for k, v in loss_dict.items()}
        losses_reduced = sum(loss for loss in loss_dict_reduced.values())
        loss_value = losses_reduced

        if not math.isfinite(loss_value):
            logging.error(f"Loss is {loss_value}, stopping training. Loss dict: {loss_dict_reduced}")
            sys.exit(1)

        optimizer.zero_grad()
        if scaler is not None:
            scaler.scale(losses).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            losses.backward()
            optimizer.step()

        if lr_scheduler is not None:
            lr_scheduler.step()

        metric_logger.update(loss=loss_value, **loss_dict_reduced)
        metric_logger.update(lr=optimizer.param_groups[0]["lr"])

    return metric_logger

# --- Evaluation Function ---

@torch.no_grad()
def evaluate(model, data_loader, device):
    """
    Evaluates the model on the given data loader.
    """
    n_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    cpu_device = torch.device("cpu")
    model.eval()
    metric_logger = MetricLogger(delimiter="  ")
    header = "Test:"

    coco = get_coco_api_from_dataset(data_loader.dataset)
    iou_types = ["bbox"] # Assuming bounding box detection
    coco_evaluator = CocoEvaluator(coco, iou_types)

    for images, targets in metric_logger.log_every(data_loader, 100, header):
        images = list(img.to(device) for img in images)

        if torch.cuda.is_available():
            torch.cuda.synchronize()
        model_time = time.time()
        outputs = model(images)

        outputs = [{k: v.to(cpu_device) for k, v in t.items()} for t in outputs]
        model_time = time.time() - model_time

        res = {target["image_id"].item(): output for target, output in zip(targets, outputs)}
        
        evaluator_time = time.time()
        coco_evaluator.update(res)
        evaluator_time = time.time() - evaluator_time
        
        metric_logger.update(model_time=model_time, evaluator_time=evaluator_time)

    # gather the stats from all processes
    metric_logger.synchronize_between_processes()
    logging.info("Averaged stats:", metric_logger)
    coco_evaluator.synchronize_between_processes()

    # accumulate predictions from all images
    coco_evaluator.accumulate()
    coco_evaluator.summarize()
    
    torch.set_num_threads(n_threads)
    return coco_evaluator


# --- Utility Classes for Logging ---

class SmoothedValue:
    """Track a series of values and provide access to smoothed values over a
    window or the global average of the series.
    """

    def __init__(self, window_size=20, fmt=None):
        if fmt is None:
            fmt = "{median:.4f} ({global_avg:.4f})"
        self.deque = deque(maxlen=window_size)
        self.total = 0.0
        self.count = 0
        self.fmt = fmt

    def update(self, value, n=1):
        self.deque.append(value)
        self.count += n
        self.total += value * n

    def synchronize_between_processes(self):
        """
        Warning: does not synchronize the deque!
        """
        # In a multi-GPU setting, this would sync stats.
        # For single-GPU or CPU, this is a no-op.
        pass

    @property
    def median(self):
        d = torch.tensor(list(self.deque))
        return d.median().item()

    @property
    def avg(self):
        d = torch.tensor(list(self.deque), dtype=torch.float32)
        return d.mean().item()

    @property
    def global_avg(self):
        return self.total / self.count

    @property
    def max(self):
        return max(self.deque)

    @property
    def value(self):
        return self.deque[-1]

    def __str__(self):
        return self.fmt.format(
            median=self.median,
            avg=self.avg,
            global_avg=self.global_avg,
            max=self.max,
            value=self.value,
        )


class MetricLogger:
    def __init__(self, delimiter="\t"):
        self.meters = defaultdict(SmoothedValue)
        self.delimiter = delimiter

    def update(self, **kwargs):
        for k, v in kwargs.items():
            if isinstance(v, torch.Tensor):
                v = v.item()
            assert isinstance(v, (float, int))
            self.meters[k].update(v)

    def __getattr__(self, attr):
        if attr in self.meters:
            return self.meters[attr]
        if attr in self.__dict__:
            return self.__dict__[attr]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{attr}'")

    def __str__(self):
        loss_str = []
        for name, meter in self.meters.items():
            loss_str.append(f"{name}: {str(meter)}")
        return self.delimiter.join(loss_str)

    def synchronize_between_processes(self):
        for meter in self.meters.values():
            meter.synchronize_between_processes()

    def add_meter(self, name, meter):
        self.meters[name] = meter

    def log_every(self, iterable, print_freq, header=None):
        i = 0
        if not header:
            header = ""
        start_time = time.time()
        end = time.time()
        iter_time = SmoothedValue(fmt="{avg:.4f}")
        data_time = SmoothedValue(fmt="{avg:.4f}")
        space_fmt = ":" + str(len(str(len(iterable)))) + "d"
        if torch.cuda.is_available():
            log_msg = self.delimiter.join(
                [
                    header,
                    "[{0" + space_fmt + "}/{1}]",
                    "eta: {eta}",
                    "{meters}",
                    "time: {time}",
                    "data: {data}",
                    "max mem: {memory:.0f}",
                ]
            )
        else:
            log_msg = self.delimiter.join(
                [header, "[{0" + space_fmt + "}/{1}]", "eta: {eta}", "{meters}", "time: {time}", "data: {data}"]
            )
        MB = 1024.0 * 1024.0
        for obj in iterable:
            data_time.update(time.time() - end)
            yield obj
            iter_time.update(time.time() - end)
            if i % print_freq == 0 or i == len(iterable) - 1:
                eta_seconds = iter_time.global_avg * (len(iterable) - i)
                eta_string = str(datetime.timedelta(seconds=int(eta_seconds)))
                if torch.cuda.is_available():
                    logging.info(
                        log_msg.format(
                            i,
                            len(iterable),
                            eta=eta_string,
                            meters=str(self),
                            time=str(iter_time),
                            data=str(data_time),
                            memory=torch.cuda.max_memory_allocated() / MB,
                        )
                    )
                else:
                    logging.info(
                        log_msg.format(
                            i, len(iterable), eta=eta_string, meters=str(self), time=str(iter_time), data=str(data_time)
                        )
                    )
            i += 1
            end = time.time()
        total_time = time.time() - start_time
        total_time_str = str(datetime.timedelta(seconds=int(total_time)))
        logging.info(f"{header} Total time: {total_time_str} ({total_time / len(iterable):.4f} s / it)")
```