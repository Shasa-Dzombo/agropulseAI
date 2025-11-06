"""
Metrics for Segmentation Tasks
==============================

This module provides a helper class to compute common metrics for semantic
segmentation tasks, primarily Intersection over Union (IoU) and the Dice
Coefficient. These metrics are essential for evaluating the performance of
segmentation models.

Core Components:
----------------
1.  **`SegmentationMetrics` Class**:
    -   **Purpose**: To accumulate predictions and ground truths over an entire
      evaluation dataset and compute overall metrics.
    -   **Initialization (`__init__`)**:
        -   Takes the number of classes as input to correctly initialize
          confusion matrices.
    -   **`update` Method**:
        -   Takes the model's output logits and the ground truth masks for a batch.
        -   Converts the logits to predicted class indices.
        -   Flattens the predictions and ground truths to compute a batch-level
          confusion matrix.
        -   Adds the batch confusion matrix to a running total for the entire dataset.
    -   **`get_metrics` Method**:
        -   Calculates the final metrics based on the accumulated confusion matrix.
        -   **IoU (Intersection over Union)**: For each class, `IoU = TP / (TP + FP + FN)`.
          The function calculates the mean IoU (mIoU) across all classes.
        -   **Dice Coefficient**: For each class, `Dice = 2 * TP / (2 * TP + FP + FN)`.
          This is closely related to IoU and is also a very common segmentation metric.
        -   Returns a dictionary containing the computed metrics.

This class provides a robust way to track segmentation performance during
training and evaluation, ensuring that metrics are calculated correctly over
the entire dataset rather than being averaged on a per-batch basis, which can
be inaccurate.
"""

import torch
import numpy as np

class SegmentationMetrics:
    def __init__(self, num_classes: int):
        self.num_classes = num_classes
        self.confusion_matrix = np.zeros((num_classes, num_classes))

    def _fast_hist(self, label_true, label_pred, n_class):
        mask = (label_true >= 0) & (label_true < n_class)
        hist = np.bincount(
            n_class * label_true[mask].astype(int) + label_pred[mask],
            minlength=n_class ** 2,
        ).reshape(n_class, n_class)
        return hist

    def update(self, logits: torch.Tensor, labels: torch.Tensor):
        """
        Update the confusion matrix with a new batch of predictions and labels.
        """
        preds = torch.argmax(logits, dim=1).cpu().numpy()
        labels = labels.cpu().numpy()

        for lt, lp in zip(labels, preds):
            self.confusion_matrix += self._fast_hist(
                lt.flatten(), lp.flatten(), self.num_classes
            )

    def get_metrics(self) -> dict:
        """
        Calculate metrics from the accumulated confusion matrix.
        """
        hist = self.confusion_matrix
        # Intersection over Union (IoU)
        iou = np.diag(hist) / (hist.sum(axis=1) + hist.sum(axis=0) - np.diag(hist))
        miou = np.nanmean(iou)

        # Dice Coefficient
        dice = 2 * np.diag(hist) / (hist.sum(axis=1) + hist.sum(axis=0))
        mean_dice = np.nanmean(dice)

        # Pixel Accuracy
        acc = np.diag(hist).sum() / hist.sum()
        acc_cls = np.diag(hist) / hist.sum(axis=1)
        mean_acc_cls = np.nanmean(acc_cls)

        return {
            "mIoU": miou,
            "dice": mean_dice,
            "pixel_accuracy": acc,
            "mean_class_accuracy": mean_acc_cls,
        }

    def reset(self):
        self.confusion_matrix = np.zeros((self.num_classes, self.num_classes))
