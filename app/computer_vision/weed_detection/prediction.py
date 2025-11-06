# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\weed_detection\prediction.py

"""
Prediction Pipeline for Weed Detection Models
=============================================

This module provides the functionality to run inference with a trained weed
detection model. It encapsulates the entire process of loading a model,
preprocessing an input image, running the model, and post-processing the
predictions for visualization.

Core Components:
----------------
1.  **`WeedDetector` Class**:
    -   **Purpose**: A high-level wrapper that simplifies the prediction process.
    -   **Initialization (`__init__`)**:
        -   Loads the trained model weights from a checkpoint file (`.pth`).
        -   The associated training arguments, which include the model name and
          number of classes, are also loaded from the checkpoint.
        -   Instantiates the correct model architecture using the
          `WeedDetectionModelFactory`.
        -   Sets the model to evaluation mode (`model.eval()`) and moves it to
          the specified device (GPU or CPU).
    -   **Prediction (`predict`)**:
        -   Takes a raw image (as a NumPy array) and a confidence threshold as input.
        -   Preprocesses the image: converts it to a PyTorch tensor and normalizes it.
        -   Performs the forward pass through the model to get raw predictions.
        -   Filters the predictions based on the confidence threshold to remove
          low-confidence detections.
        -   Returns the filtered bounding boxes, labels, and scores.

2.  **Visualization Function (`visualize_predictions`)**:
    -   **Purpose**: Draws the predicted bounding boxes, labels, and scores on an image.
    -   **Process**:
        -   Takes an image and the model's predictions as input.
        -   Iterates through each detected object.
        -   Draws a rectangle for the bounding box.
        -   Creates a text label with the class name and confidence score.
        -   Puts the text on the image, often with a colored background for better
          visibility.
    -   **Output**: Returns the image with the visualizations drawn on it.

3.  **Main Execution Block (`if __name__ == "__main__":`)**:
    -   Provides a command-line interface for running predictions on a single image.
    -   Uses `argparse` to accept the path to the model checkpoint, the input image,
      the output path for the visualized image, and a confidence threshold.
    -   Demonstrates the end-to-end workflow:
        1.  Instantiate `WeedDetector`.
        2.  Load and preprocess the image.
        3.  Call the `predict` method.
        4.  Call `visualize_predictions` to draw the results.
        5.  Save the final image.

Usage Example:
--------------
```bash
python prediction.py \\
    --model-path /path/to/best_model.pth \\
    --image-path /path/to/input_image.jpg \\
    --output-path /path/to/output_image.jpg \\
    --threshold 0.5
```
"""

import torch
import cv2
import numpy as np
import argparse
import os
import random

from models import WeedDetectionModelFactory
from app.computer_vision.weed_detection.taxonomy import get_class_map

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class WeedDetector:
    """
    A wrapper class for loading a trained weed detection model and making predictions.
    """
    def __init__(self, model_path, device='cuda'):
        """
        Initializes the detector by loading the model and its configuration.

        Args:
            model_path (str): Path to the trained model checkpoint (.pth file).
            device (str): The device to run the model on ('cuda' or 'cpu').
        """
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        logging.info(f"Loading model on device: {self.device}")

        checkpoint = torch.load(model_path, map_location=self.device)
        
        # Load training arguments from the checkpoint
        train_args = checkpoint.get('args')
        if train_args is None:
            raise ValueError("Checkpoint does not contain training arguments ('args').")

        self.model_name = train_args.model_name
        
        # Dynamically get class map and number of classes from the taxonomy
        self.class_map = get_class_map()
        num_classes = len(self.class_map)

        # Create model instance
        model_factory = WeedDetectionModelFactory(num_classes=num_classes)
        self.model = model_factory.create_model(self.model_name, pretrained=False)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.to(self.device)
        self.model.eval()

        # Store reverse class map for visualization
        self.reverse_class_map = {v: k for k, v in self.class_map.items()}
        logging.info(f"Model {self.model_name} loaded successfully with {num_classes} classes.")

    def predict(self, image, threshold=0.5):
        """
        Makes a prediction on a single image.

        Args:
            image (np.ndarray): The input image in BGR format (as read by OpenCV).
            threshold (float): The confidence threshold to filter detections.

        Returns:
            tuple: A tuple containing (boxes, labels, scores) for the filtered detections.
                   - boxes (np.ndarray): (N, 4) array of bounding boxes [xmin, ymin, xmax, ymax].
                   - labels (list): List of N string labels.
                   - scores (np.ndarray): (N,) array of confidence scores.
        """
        # Preprocess the image
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        img_tensor = torch.from_numpy(img_rgb / 255.).permute(2, 0, 1).float().to(self.device)
        
        with torch.no_grad():
            prediction = self.model([img_tensor])[0]

        # Filter predictions by threshold
        scores = prediction['scores'].cpu().numpy()
        keep_indices = scores > threshold
        
        boxes = prediction['boxes'][keep_indices].cpu().numpy()
        labels_int = prediction['labels'][keep_indices].cpu().numpy()
        scores = scores[keep_indices]

        # Convert integer labels to string names
        labels_str = [self.reverse_class_map[i] for i in labels_int]

        return boxes, labels_str, scores

def generate_color_map(class_map):
    """Generates a random color for each class."""
    color_map = {}
    for class_name in class_map.keys():
        if class_name == '__background__':
            continue
        # Generate a random BGR color
        color_map[class_name] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    return color_map

def visualize_predictions(image, boxes, labels, scores, class_map):
    """
    Draws bounding boxes, labels, and scores on an image.

    Args:
        image (np.ndarray): The original image.
        boxes (np.ndarray): Bounding boxes for detections.
        labels (list): String labels for detections.
        scores (np.ndarray): Confidence scores for detections.
        class_map (dict): A map from class index to class name.
    """
    vis_image = image.copy()
    
    # Generate a color for each class label
    color_map = generate_color_map(class_map)

    for box, label, score in zip(boxes, labels, scores):
        xmin, ymin, xmax, ymax = map(int, box)
        color = color_map.get(label, (255, 255, 255)) # Default to white

        # Draw bounding box
        cv2.rectangle(vis_image, (xmin, ymin), (xmax, ymax), color, 2)

        # Create label text
        text = f"{label}: {score:.2f}"
        
        # Get text size to draw a background rectangle
        (text_width, text_height), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        
        # Draw background rectangle
        cv2.rectangle(vis_image, (xmin, ymin - text_height - baseline), (xmin + text_width, ymin), color, -1)
        
        # Put text on the background
        cv2.putText(vis_image, text, (xmin, ymin - baseline + 1), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

    return vis_image


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run Weed Detection Inference")
    parser.add_argument('--model-path', required=True, help='Path to the trained model checkpoint (.pth)')
    parser.add_argument('--image-path', required=True, help='Path to the input image')
    parser.add_argument('--output-path', required=True, help='Path to save the visualized output image')
    parser.add_argument('--threshold', type=float, default=0.5, help='Confidence threshold for detections')
    parser.add_argument('--device', default='cuda', help='Device to use for inference (cuda or cpu)')
    args = parser.parse_args()

    # --- Run Prediction ---
    logging.info(f"Running inference on {args.image_path}...")
    
    # 1. Initialize detector
    detector = WeedDetector(model_path=args.model_path, device=args.device)
    
    # 2. Load image
    if not os.path.exists(args.image_path):
        raise FileNotFoundError(f"Input image not found at {args.image_path}")
    image = cv2.imread(args.image_path)
    if image is None:
        raise IOError(f"Could not read image from {args.image_path}")

    # 3. Get predictions
    boxes, labels, scores = detector.predict(image, threshold=args.threshold)
    logging.info(f"Found {len(boxes)} objects with confidence > {args.threshold}")

    # 4. Visualize predictions
    output_image = visualize_predictions(image, boxes, labels, scores, detector.class_map)

    # 5. Save output
    output_dir = os.path.dirname(args.output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    cv2.imwrite(args.output_path, output_image)
    
    logging.info(f"Prediction complete. Visualized output saved to {args.output_path}")
```