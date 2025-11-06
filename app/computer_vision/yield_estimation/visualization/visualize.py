"""
Visualization Utilities for Yield Estimation
============================================

This module provides a set of functions for visualizing the outputs of the yield
estimation models. Creating clear and informative visualizations is crucial for
debugging models, presenting results, and building user-facing applications.

Each function is tailored to a specific task type (detection, segmentation, or
regression) and is designed to overlay predictions onto the original image.

Core Functions:
----------------
1.  **`visualize_detections`**:
    -   **Purpose**: To draw bounding boxes for detected objects (e.g., fruits).
    -   **Inputs**: An image and the output from the `YieldPredictor` for a
      detection task (a dictionary containing 'boxes', 'labels', 'scores').
    -   **Process**:
        -   Iterates through each detected object.
        -   Draws a rectangle for the bounding box using `cv2.rectangle`.
        -   Creates a text label with the class name and confidence score.
        -   Draws a filled rectangle as a background for the text to ensure
          it's readable regardless of the image content behind it.
        -   Puts the text on the background rectangle.
    -   **Customization**: Colors for different classes can be customized.

2.  **`visualize_segmentation`**:
    -   **Purpose**: To overlay a colored segmentation mask on an image.
    -   **Inputs**: An image and the output from the `YieldPredictor` for a
      segmentation task (a dictionary containing a 'mask').
    -   **Process**:
        -   Generates a color map to assign a unique color to each class ID
          in the segmentation mask.
        -   Creates a colored version of the mask by mapping class IDs to colors.
        -   Blends the colored mask with the original image using `cv2.addWeighted`
          to create a transparent overlay effect.
    -   **Output**: An image showing the original scene with segmented areas
      highlighted in color.

3.  **`visualize_regression`**:
    -   **Purpose**: To display the predicted continuous yield value on an image.
    -   **Inputs**: An image and the output from the `YieldPredictor` for a
      regression task (a dictionary containing 'yield').
    -   **Process**:
        -   Formats the predicted yield value into a string.
        -   Draws a semi-transparent black rectangle at the top of the image to
          serve as a background for the text.
        -   Puts the formatted text onto the background using `cv2.putText`.
    -   **Output**: The original image with the predicted yield clearly displayed.
"""

import cv2
import numpy as np
import random
from typing import Dict, Any

def generate_color_map(num_classes: int) -> Dict[int, tuple]:
    """Generates a random color for each class index."""
    color_map = {}
    for i in range(num_classes):
        if i == 0: # Background
            color_map[i] = (0, 0, 0)
        else:
            color_map[i] = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
    return color_map

def visualize_detections(image: np.ndarray, predictions: Dict[str, Any]) -> np.ndarray:
    """
    Draws bounding boxes, labels, and scores on an image for detection tasks.

    Args:
        image (np.ndarray): The original image in BGR format.
        predictions (Dict): A dictionary containing 'boxes', 'labels', and 'scores'.

    Returns:
        np.ndarray: The image with visualizations.
    """
    vis_image = image.copy()
    boxes = predictions.get('boxes', [])
    labels = predictions.get('labels', [])
    scores = predictions.get('scores', [])
    
    # Generate a color for each class label
    unique_labels = np.unique(labels)
    color_map = generate_color_map(len(unique_labels) + 1) # +1 for safety

    for box, label, score in zip(boxes, labels, scores):
        xmin, ymin, xmax, ymax = map(int, box)
        color = color_map.get(label, (255, 255, 255)) # Default to white

        # Draw bounding box
        cv2.rectangle(vis_image, (xmin, ymin), (xmax, ymax), color, 2)

        # Create label text
        text = f"ID:{label} {score:.2f}"
        
        # Get text size to draw a background rectangle
        (text_width, text_height), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        
        # Draw background rectangle
        cv2.rectangle(vis_image, (xmin, ymin - text_height - baseline), (xmin + text_width, ymin), color, -1)
        
        # Put text on the background
        cv2.putText(vis_image, text, (xmin, ymin - baseline), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    return vis_image

def visualize_segmentation(image: np.ndarray, predictions: Dict[str, Any]) -> np.ndarray:
    """
    Overlays a colored segmentation mask on an image.

    Args:
        image (np.ndarray): The original image in BGR format.
        predictions (Dict): A dictionary containing the 'mask'.

    Returns:
        np.ndarray: The image with the segmentation mask overlay.
    """
    vis_image = image.copy()
    mask = predictions.get('mask')
    if mask is None:
        return vis_image

    num_classes = np.max(mask) + 1
    color_map = generate_color_map(num_classes)

    # Create a colored version of the mask
    colored_mask = np.zeros((mask.shape[0], mask.shape[1], 3), dtype=np.uint8)
    for class_id, color in color_map.items():
        colored_mask[mask == class_id] = color

    # Blend the mask with the original image
    overlay = cv2.addWeighted(vis_image, 0.6, colored_mask, 0.4, 0)
    
    return overlay

def visualize_regression(image: np.ndarray, predictions: Dict[str, Any]) -> np.ndarray:
    """
    Displays the predicted yield value on an image.

    Args:
        image (np.ndarray): The original image in BGR format.
        predictions (Dict): A dictionary containing the 'yield' value.

    Returns:
        np.ndarray: The image with the predicted yield displayed.
    """
    vis_image = image.copy()
    yield_value = predictions.get('yield')
    if yield_value is None:
        return vis_image

    text = f"Predicted Yield: {yield_value:.2f}"
    
    # Draw a semi-transparent background rectangle at the top
    cv2.rectangle(vis_image, (0, 0), (vis_image.shape[1], 50), (0, 0, 0), -1)
    
    # Put text on the background
    cv2.putText(vis_image, text, (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)

    return vis_image
