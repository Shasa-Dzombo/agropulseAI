"""
Prediction Pipeline for Yield Estimation Models
===============================================

This module provides the functionality to run inference with a trained yield
estimation model. It encapsulates the entire process of loading a model,
preprocessing input data, running the model, and post-processing the
predictions for visualization or direct use.

Core Components:
----------------
1.  **`YieldPredictor` Class**:
    -   **Purpose**: A high-level wrapper that simplifies the prediction process
      for any of the supported task types (detection, segmentation, regression).
    -   **Initialization (`__init__`)**:
        -   Loads the trained model weights from a checkpoint file (`.pth`).
        -   Crucially, it also loads the model configuration that was saved
          during training. This ensures that the correct model architecture is
          re-created.
        -   Instantiates the model using the `ModelFactory`.
        -   Sets the model to evaluation mode (`model.eval()`) and moves it to
          the specified device.
    -   **Prediction (`predict`)**:
        -   Takes raw input data (e.g., an image as a NumPy array) and a
          confidence threshold as input.
        -   Preprocesses the input data using the same transformations as the
          validation set during training (e.g., resizing, normalization).
        -   Performs the forward pass through the model.
        -   Post-processes the raw model output into a human-readable format
          (e.g., filtering detections by score, converting segmentation masks
          to class labels).
        -   Returns the final predictions.

2.  **Visualization Functions**:
    -   A suite of functions to draw predictions on an image, tailored to each
      task type.
    -   `visualize_detections`: Draws bounding boxes, labels, and scores.
    -   `visualize_segmentation`: Overlays a colored segmentation mask on the
      original image.
    -   `visualize_regression`: Displays the predicted yield value on the image.

3.  **Main Execution Block (`if __name__ == "__main__":`)**:
    -   Provides a command-line interface for running predictions on a single
      image or data sample.
    -   Uses `argparse` to accept the path to the model checkpoint, the input
      data, the output path for visualization, and a confidence threshold.
    -   Demonstrates the end-to-end prediction workflow.

This module makes it easy to deploy and use the trained yield estimation models,
providing a clear and consistent API for inference.
"""

import torch
import cv2
import numpy as np
import argparse
import os
import logging

from app.computer_vision.yield_estimation.utils.config import get_settings, DetectionModelConfig, SegmentationModelConfig, RegressionModelConfig
from app.computer_vision.yield_estimation.models.factory import ModelFactory
from app.computer_vision.yield_estimation.data.augmentations import YieldEstimationAugmenter
from app.computer_vision.yield_estimation.visualization.visualize import visualize_detections, visualize_segmentation, visualize_regression

class YieldPredictor:
    """
    A wrapper class for loading a trained model and making predictions.
    """
    def __init__(self, model_path: str, device: str = 'cuda'):
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        logger.info(f"Loading model on device: {self.device}")

        checkpoint = torch.load(model_path, map_location=self.device)
        
        # Determine task type and load appropriate config
        model_config_dict = checkpoint['model_config']
        self.task = self._infer_task_from_config(model_config_dict)
        
        if self.task == 'detection':
            model_config = DetectionModelConfig(**model_config_dict)
        elif self.task == 'segmentation':
            model_config = SegmentationModelConfig(**model_config_dict)
        elif self.task == 'regression':
            model_config = RegressionModelConfig(**model_config_dict)
        else:
            raise ValueError("Could not determine task type from model config.")

        # Create model instance
        factory = ModelFactory()
        self.model = factory.create_model(self.task, model_config, pretrained=False)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.to(self.device)
        self.model.eval()

        # Setup preprocessing transforms (from validation set)
        settings = get_settings()
        augmenter = YieldEstimationAugmenter(settings.augmentation, settings.data.image_size)
        self.transform = augmenter.get_transforms(is_train=False)
        
        logger.info(f"Predictor for task '{self.task}' with model '{model_config.name}' loaded successfully.")

    def _infer_task_from_config(self, config: dict) -> str:
        """Infer task type based on keys present in the model config."""
        if 'confidence_threshold' in config:
            return 'detection'
        if 'encoder_name' in config:
            return 'segmentation'
        if 'dropout_rate' in config:
            return 'regression'
        return None

    @torch.no_grad()
    def predict(self, image: np.ndarray, threshold: float = 0.5):
        """
        Makes a prediction on a single image.

        Args:
            image (np.ndarray): The input image in BGR format.
            threshold (float): The confidence threshold for filtering detections.

        Returns:
            The post-processed model output (depends on task).
        """
        # Preprocess the image
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        transformed = self.transform(image=image_rgb)
        input_tensor = transformed['image'].unsqueeze(0).to(self.device)

        # --- Model Inference ---
        output = self.model(input_tensor)

        # --- Post-processing ---
        if self.task == 'detection':
            # Filter by score
            scores = output[0]['scores'].cpu().numpy()
            keep_indices = scores > threshold
            
            boxes = output[0]['boxes'][keep_indices].cpu().numpy()
            labels = output[0]['labels'][keep_indices].cpu().numpy()
            scores = scores[keep_indices]
            return {'boxes': boxes, 'labels': labels, 'scores': scores}

        elif self.task == 'segmentation':
            # Get the class with the highest probability for each pixel
            mask = torch.argmax(output.squeeze(), dim=0).cpu().numpy()
            return {'mask': mask}

        elif self.task == 'regression':
            predicted_yield = output.cpu().numpy().flatten()[0]
            return {'yield': predicted_yield}
        
        return None

def main():
    parser = argparse.ArgumentParser(description="Run Yield Estimation Inference")
    parser.add_argument('--model-path', required=True, help='Path to the trained model checkpoint (.pth)')
    parser.add_argument('--image-path', required=True, help='Path to the input image')
    parser.add_argument('--output-path', required=True, help='Path to save the visualized output image')
    parser.add_argument('--threshold', type=float, default=0.5, help='Confidence threshold for detections')
    parser.add_argument('--device', default='cuda', help='Device to use for inference (cuda or cpu)')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    logger.info(f"Running inference on {args.image_path}...")

    # 1. Initialize predictor
    predictor = YieldPredictor(model_path=args.model_path, device=args.device)
    
    # 2. Load image
    image = cv2.imread(args.image_path)
    if image is None:
        raise IOError(f"Could not read image from {args.image_path}")

    # 3. Get predictions
    predictions = predictor.predict(image, threshold=args.threshold)
    
    # 4. Visualize predictions
    output_image = None
    if predictor.task == 'detection':
        logger.info(f"Found {len(predictions['boxes'])} objects.")
        output_image = visualize_detections(image, predictions)
    elif predictor.task == 'segmentation':
        logger.info("Visualizing segmentation mask.")
        output_image = visualize_segmentation(image, predictions)
    elif predictor.task == 'regression':
        logger.info(f"Predicted yield: {predictions['yield']:.2f}")
        output_image = visualize_regression(image, predictions)

    # 5. Save output
    if output_image is not None:
        output_dir = os.path.dirname(args.output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        cv2.imwrite(args.output_path, output_image)
        logger.info(f"Prediction complete. Visualized output saved to {args.output_path}")

if __name__ == '__main__':
    main()
