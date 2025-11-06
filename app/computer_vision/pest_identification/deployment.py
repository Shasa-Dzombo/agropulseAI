# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\pest_identification\deployment.py

"""
Model Deployment and Inference Engine
=====================================

This module provides the tools and infrastructure for deploying trained pest
identification models and running efficient inference. It bridges the gap between
a trained model checkpoint (`.pth` file) and a live, production-ready service.

The module is designed to be versatile, supporting different deployment targets
from a simple local server to optimized edge devices.

Key Components:
---------------
1.  **`InferenceEngine`**: A high-level class that encapsulates the entire
    inference process. It handles:
    -   **Model Loading**: Loads a trained model from a checkpoint file and sets it
      to evaluation mode.
    -   **Preprocessing**: Takes a raw image (e.g., from a file path or a numpy
      array) and applies the necessary transformations (resizing, normalization)
      to prepare it for the model.
    -   **Inference**: Runs the preprocessed image through the model.
    -   **Post-processing**: Converts the raw model output (logits or bounding
      boxes) into a human-readable format.
        -   For **classification**, this includes applying softmax to get
          probabilities and mapping class indices to class names.
        -   For **object detection**, this involves applying a confidence threshold,
          performing Non-Maximum Suppression (NMS) to remove duplicate detections,
          and scaling bounding boxes back to the original image dimensions.

2.  **Model Optimization**: Includes utilities for converting and optimizing models
    for different deployment targets:
    -   **`to_onnx()`**: Converts a PyTorch model to the ONNX (Open Neural Network
      Exchange) format. ONNX models are highly portable and can be run on various
      inference engines (e.g., ONNX Runtime, TensorRT).
    -   **`to_tensorrt()`**: A placeholder for a function that would take an ONNX
      model and use NVIDIA's TensorRT to further optimize it for NVIDIA GPUs,
      achieving significant speedups through techniques like layer fusion and
      precision calibration (e.g., to FP16 or INT8).
    -   **`to_torchscript()`**: Converts a PyTorch model to TorchScript, a static
      graph representation that can be run in non-Python environments (like C++
      servers or mobile apps).

3.  **Inference Server (Conceptual)**:
    -   The `if __name__ == '__main__':` block demonstrates how to wrap the
      `InferenceEngine` in a simple web server using Flask. This creates a REST
      API endpoint where users can send an image and receive pest identification
      results in JSON format. This serves as a blueprint for a production
      microservice.

4.  **Visualization Utilities**:
    -   `visualize_predictions()`: A function to draw the predicted bounding boxes
      and labels on an image, providing a clear visual representation of the
      model's output.

Workflow for Inference:
-----------------------
1.  **Initialization**: An `InferenceEngine` is created with the path to a trained
    model checkpoint and a configuration file (containing class names, image size,
    etc.).
2.  **Prediction**: The `predict()` method is called with a raw image.
3.  **Preprocessing**: The image is loaded, resized, and normalized.
4.  **Inference**: The model's `forward()` method is called.
5.  **Post-processing**: The raw output is filtered (NMS, thresholding) and formatted.
6.  **Return**: A structured JSON-like dictionary containing the predictions is
    returned.

This module is crucial for making the trained models usable in real-world
applications, whether it's for batch processing large datasets of farm images or
for real-time analysis from a drone's video feed.
"""

import logging
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision.ops import nms
from PIL import Image

from .models import ModelFactory
from .data_loader import create_augmentations

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class InferenceEngine:
    """
    Handles loading a model and running inference on new images.
    """
    def __init__(self, model_path: str, config: Dict[str, Any]):
        """
        Args:
            model_path (str): Path to the trained model checkpoint (.pth file).
            config (Dict[str, Any]): The configuration dictionary used during training.
        """
        self.config = config
        self.device = torch.device(config.get('device', 'cuda' if torch.cuda.is_available() else 'cpu'))
        self.task = config.get('task', 'classification')

        # Load class names (assuming they are stored in the config or a separate file)
        self.class_names = config.get('class_names', [f'class_{i}' for i in range(config['model']['num_classes'])])

        # Load model
        self.model = self._load_model(model_path)
        
        # Create preprocessing pipeline
        self.transform = create_augmentations(config['data'], stage='test')

        logging.info(f"InferenceEngine initialized for task '{self.task}' on device '{self.device}'.")

    def _load_model(self, model_path: str) -> nn.Module:
        """Loads the model from a checkpoint."""
        if not Path(model_path).exists():
            raise FileNotFoundError(f"Model checkpoint not found at {model_path}")
        
        model = ModelFactory.create_model(self.config['model'])
        model.load_state_dict(torch.load(model_path, map_location=self.device))
        model.to(self.device)
        model.eval()
        logging.info(f"Model loaded from {model_path}")
        return model

    @torch.no_grad()
    def predict(self,
                image: Union[str, np.ndarray, Image.Image],
                confidence_threshold: float = 0.5) -> List[Dict[str, Any]]:
        """
        Makes a prediction on a single image.

        Args:
            image (Union[str, np.ndarray, Image.Image]): Path to the image file,
                a numpy array (H, W, C), or a PIL Image.
            confidence_threshold (float): Minimum confidence score for a prediction
                to be considered.

        Returns:
            List[Dict[str, Any]]: A list of prediction dictionaries.
                For classification: [{'class_name': str, 'confidence': float}]
                For detection: [{'class_name': str, 'confidence': float, 'bbox': [x1, y1, x2, y2]}]
        """
        # 1. Preprocess Image
        img_np = self._load_image(image)
        transformed = self.transform(image=img_np)
        input_tensor = transformed['image'].unsqueeze(0).to(self.device)

        # 2. Run Inference
        outputs = self.model(input_tensor)

        # 3. Post-process
        if self.task == 'classification':
            return self._postprocess_classification(outputs, confidence_threshold)
        elif self.task == 'detection':
            # The detection model output is already a list of dicts in eval mode
            return self._postprocess_detection(outputs, img_np.shape, confidence_threshold)
        else:
            raise ValueError(f"Unsupported task for prediction: {self.task}")

    def _load_image(self, image: Union[str, np.ndarray, Image.Image]) -> np.ndarray:
        """Loads an image into a numpy array in RGB format."""
        if isinstance(image, str):
            img = cv2.imread(image)
            if img is None:
                raise IOError(f"Could not read image from path: {image}")
            return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        elif isinstance(image, Image.Image):
            return np.array(image.convert('RGB'))
        elif isinstance(image, np.ndarray):
            # Assume BGR if 3 channels, convert to RGB
            if image.ndim == 3 and image.shape[2] == 3:
                return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            return image
        else:
            raise TypeError(f"Unsupported image type: {type(image)}")

    def _postprocess_classification(self, outputs: torch.Tensor, threshold: float) -> List[Dict[str, Any]]:
        """Post-processes classification model output."""
        probabilities = torch.softmax(outputs, dim=1)[0]
        top_prob, top_idx = torch.max(probabilities, dim=0)

        if top_prob.item() < threshold:
            return []

        return [{
            'class_name': self.class_names[top_idx.item()],
            'confidence': top_prob.item()
        }]

    def _postprocess_detection(self, outputs: List[Dict[str, torch.Tensor]],
                               original_shape: Tuple[int, int],
                               threshold: float) -> List[Dict[str, Any]]:
        """Post-processes detection model output."""
        # outputs is a list (for batch), we take the first element
        output = outputs[0]
        
        scores = output['scores']
        labels = output['labels']
        boxes = output['boxes']

        # Filter by confidence threshold
        keep = scores > threshold
        scores = scores[keep]
        labels = labels[keep]
        boxes = boxes[keep]

        # Perform Non-Maximum Suppression (NMS)
        # Note: Some models like DETR don't require NMS. This is a general pipeline.
        if self.config['model']['name'] not in ['detr']:
            nms_keep = nms(boxes, scores, iou_threshold=0.5)
            scores = scores[nms_keep]
            labels = labels[nms_keep]
            boxes = boxes[nms_keep]

        # Scale boxes to original image size
        h, w = original_shape[:2]
        img_size_cfg = self.config['data']['image_size']
        scale_x = w / img_size_cfg[1]
        scale_y = h / img_size_cfg[0]
        
        boxes[:, [0, 2]] *= scale_x
        boxes[:, [1, 3]] *= scale_y

        results = []
        for score, label, box in zip(scores, labels, boxes):
            results.append({
                'class_name': self.class_names[label.item() - 1], # BG is often 0
                'confidence': score.item(),
                'bbox': box.cpu().numpy().astype(int).tolist() # [x1, y1, x2, y2]
            })
        return results

# --- Visualization ---

def visualize_predictions(image: Union[str, np.ndarray], predictions: List[Dict[str, Any]]):
    """
    Draws predictions on an image.

    Args:
        image (Union[str, np.ndarray]): Path to image or image as numpy array.
        predictions (List[Dict]): List of prediction dictionaries from InferenceEngine.
    """
    if isinstance(image, str):
        img_bgr = cv2.imread(image)
    else:
        img_bgr = image if image.ndim == 3 else cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    if not predictions:
        logging.info("No predictions to visualize.")
        return img_bgr

    for pred in predictions:
        if 'bbox' in pred: # Detection
            x1, y1, x2, y2 = pred['bbox']
            label = f"{pred['class_name']}: {pred['confidence']:.2f}"
            cv2.rectangle(img_bgr, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(img_bgr, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        else: # Classification
            label = f"{pred['class_name']}: {pred['confidence']:.2f}"
            cv2.putText(img_bgr, label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
    
    return img_bgr

# --- Model Optimization and Export ---

def export_to_onnx(engine: InferenceEngine, output_path: str, dummy_input_shape: Tuple[int, ...]):
    """
    Exports the engine's model to ONNX format.

    Args:
        engine (InferenceEngine): The inference engine containing the model.
        output_path (str): Path to save the ONNX model.
        dummy_input_shape (Tuple[int, ...]): Shape of a dummy input tensor, e.g., (1, 3, 224, 224).
    """
    logging.info(f"Exporting model to ONNX at {output_path}...")
    dummy_input = torch.randn(*dummy_input_shape, device=engine.device)
    
    try:
        torch.onnx.export(
            engine.model,
            dummy_input,
            output_path,
            export_params=True,
            opset_version=11,
            do_constant_folding=True,
            input_names=['input'],
            output_names=['output'],
            dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}}
        )
        logging.info("ONNX export successful.")
    except Exception as e:
        logging.error(f"ONNX export failed: {e}", exc_info=True)

# --- Example Usage and Simple Flask Server ---

if __name__ == '__main__':
    import shutil
    from flask import Flask, request, jsonify

    logging.info("--- Running Deployment and Inference Demo ---")

    # 1. Setup a dummy model and config
    dummy_model_dir = Path('./dummy_inference_model')
    dummy_model_dir.mkdir(exist_ok=True)
    dummy_model_path = dummy_model_dir / 'dummy_model.pth'
    
    demo_config = {
        'task': 'detection',
        'device': 'cpu',
        'model': {'name': 'retinanet', 'num_classes': 3, 'pretrained': False},
        'data': {'image_size': [256, 256]},
        'class_names': ['aphid', 'whitefly', 'thrips']
    }
    
    # Create and save a dummy model state_dict
    dummy_model = ModelFactory.create_model(demo_config['model'])
    torch.save(dummy_model.state_dict(), dummy_model_path)

    # 2. Initialize InferenceEngine
    try:
        engine = InferenceEngine(str(dummy_model_path), demo_config)
    except Exception as e:
        logging.error(f"Failed to initialize InferenceEngine: {e}")
        shutil.rmtree(dummy_model_dir)
        exit()

    # 3. Create a dummy image and run prediction
    dummy_image = np.random.randint(0, 255, size=(480, 640, 3), dtype=np.uint8)
    cv2.imwrite(str(dummy_model_dir / 'test_image.jpg'), dummy_image)
    
    logging.info("\n--- Running prediction on a dummy image ---")
    # The dummy model is untrained, so predictions will be random.
    predictions = engine.predict(dummy_image, confidence_threshold=0.1)
    logging.info(f"Predictions: {json.dumps(predictions, indent=2)}")

    # Visualize the predictions
    viz_image = visualize_predictions(dummy_image, predictions)
    cv2.imwrite(str(dummy_model_dir / 'test_image_with_preds.jpg'), viz_image)
    logging.info("Saved prediction visualization to 'dummy_inference_model/test_image_with_preds.jpg'")

    # 4. Export to ONNX
    export_to_onnx(engine, str(dummy_model_dir / 'model.onnx'), (1, 3, *demo_config['data']['image_size']))

    # 5. Simple Flask API Server (conceptual)
    app = Flask(__name__)

    @app.route('/predict', methods=['POST'])
    def handle_prediction():
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        try:
            img_bytes = file.read()
            img_np = np.frombuffer(img_bytes, np.uint8)
            img_cv = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
            
            preds = engine.predict(img_cv)
            return jsonify(preds)
        except Exception as e:
            logging.error(f"Error during API prediction: {e}")
            return jsonify({'error': 'Failed to process image'}), 500

    logging.info("\n--- Flask Server Demo ---")
    logging.info("To run the server, you would use a command like 'flask run' or 'gunicorn'.")
    logging.info("Example request:")
    logging.info("curl -X POST -F 'file=@dummy_inference_model/test_image.jpg' http://127.0.0.1:5000/predict")
    
    # To run this server:
    # 1. Save this script as, e.g., `server.py`.
    # 2. Run `pip install Flask`.
    # 3. Set `FLASK_APP=server.py`.
    # 4. Run `flask run`.
    # The server is not started here to prevent blocking the script.

    # Cleanup
    shutil.rmtree(dummy_model_dir)
    logging.info("\n--- Deployment Demo Complete ---")
