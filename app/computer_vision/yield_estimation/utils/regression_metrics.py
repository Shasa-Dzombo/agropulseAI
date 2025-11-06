"""
Metrics for Regression Tasks
============================

This module provides a helper class to compute common metrics for regression
tasks, such as Mean Squared Error (MSE), Mean Absolute Error (MAE), and the
Coefficient of Determination (R-squared). These metrics are fundamental for
evaluating the performance of direct yield regression models.

Core Components:
----------------
1.  **`RegressionMetrics` Class**:
    -   **Purpose**: To accumulate predictions and ground truths over an entire
      evaluation dataset and compute overall performance metrics.
    -   **Initialization (`__init__`)**:
        -   Initializes empty lists to store all predictions and corresponding
          ground truth values from the dataset.
    -   **`update` Method**:
        -   Takes the model's output predictions and the ground truth values for a batch.
        -   Detaches the tensors from the computation graph, moves them to the CPU,
          and converts them to NumPy arrays.
        -   Appends the batch values to the running lists.
    -   **`get_metrics` Method**:
        -   Calculates the final metrics once all batches have been processed.
        -   **MSE (Mean Squared Error)**: The average of the squared differences
          between predicted and actual values. It penalizes larger errors more heavily.
        -   **MAE (Mean Absolute Error)**: The average of the absolute differences
          between predicted and actual values. It is less sensitive to outliers than MSE.
        -   **R-squared (Coefficient of Determination)**: Represents the proportion
          of the variance in the dependent variable that is predictable from the
          independent variable(s). An R-squared of 1 indicates that the model
          perfectly predicts the data.
        -   Returns a dictionary containing the computed metrics.

This class ensures that regression metrics are calculated based on the entire
dataset, providing a reliable assessment of the model's predictive performance.
"""

import torch
import numpy as np

class RegressionMetrics:
    def __init__(self):
        self.predictions = []
        self.targets = []

    def update(self, preds: torch.Tensor, targets: torch.Tensor):
        """
        Update the lists with a new batch of predictions and targets.
        """
        self.predictions.extend(preds.detach().cpu().numpy().flatten())
        self.targets.extend(targets.detach().cpu().numpy().flatten())

    def get_metrics(self) -> dict:
        """
        Calculate metrics from the accumulated predictions and targets.
        """
        preds = np.array(self.predictions)
        targets = np.array(self.targets)

        if len(preds) == 0:
            return {"mse": 0, "mae": 0, "r2": 0}

        # Mean Squared Error (MSE)
        mse = np.mean((preds - targets) ** 2)

        # Mean Absolute Error (MAE)
        mae = np.mean(np.abs(preds - targets))

        # R-squared (Coefficient of Determination)
        ss_tot = np.sum((targets - np.mean(targets)) ** 2)
        ss_res = np.sum((targets - preds) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        return {
            "mse": float(mse),
            "mae": float(mae),
            "r2": float(r2),
        }

    def reset(self):
        self.predictions = []
        self.targets = []
