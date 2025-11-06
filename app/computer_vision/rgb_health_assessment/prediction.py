# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\rgb_health_assessment\prediction.py

"""
Prediction Pipeline for RGB-Based Health Assessment
===================================================

This module provides the functionality to use a pre-trained RGB health
assessment model to make predictions on new, unseen images. It encapsulates
the entire prediction workflow, from loading the model and its associated
configuration to processing the new image and outputting a health prediction.

The core component is the `PredictionPipeline`, which is designed to be
lightweight and easy to deploy, for example, in a web service, a mobile app
backend, or an edge device.

Core Components:
---------------
1.  **`PredictionPipeline`**:
    -   **Purpose**: An orchestrator class that handles all steps of the
      prediction process for a single image.
    -   **Initialization**: It is initialized with the path to a model directory.
      This directory must contain the serialized model (e.g., `model.joblib`)
      and the `config.json` file that was generated during the training run.
      This ensures that the exact same preprocessing steps and feature set
      are used for prediction as were used for training.
    -   **Workflow**:
        1.  **Load Artifacts**: Loads the trained `model.joblib` and the
            `config.json` file.
        2.  **Instantiate Pipeline**: Re-creates the `RGBDataPipeline` for
            preprocessing using the configuration stored in `config.json`.
        3.  **Process Image**: Takes the path to a new image, runs it through
            the `RGBDataPipeline` to extract its feature vector.
        4.  **Predict**: Feeds the extracted feature vector into the loaded
            model to get the health prediction. It can return both the predicted
            class label (e.g., 'healthy', 'stressed') and the class probabilities.
        5.  **Visualization (Optional)**: Can generate a visualization of the
            segmented plant, which is useful for debugging or for user-facing
            applications.

Design Philosophy:
------------------
-   **Reproducibility**: By bundling the model with its configuration, the
  `PredictionPipeline` guarantees that predictions are made using the exact
  same logic as training, which is critical for reliable performance.
-   **Encapsulation**: The complexity of the preprocessing and feature extraction
  is hidden from the user of the pipeline. They only need to provide the model
  directory and the new image path.
-   **Deployability**: The class is self-contained and easy to integrate into
  various deployment environments.

Usage Example:
--------------
```python
# Initialize the prediction pipeline with the path to the trained model artifacts
predictor = PredictionPipeline(model_dir='/path/to/training/output')

# Make a prediction on a new image
result = predictor.predict(image_path='/path/to/new_plant_image.jpg')

# Print the results
print(f"Predicted Health Status: {result['prediction']}")
print(f"Class Probabilities: {result['probabilities']}")

# Save the visualization if created
if 'visualization' in result:
    cv2.imwrite('prediction_visualization.png', result['visualization'])
```
"""

import os
import json
import joblib
import numpy as np
import cv2
import logging
from typing import Dict, Any, List

from .preprocessing import RGBDataPipeline
from sklearn.base import ClassifierMixin

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PredictionPipeline:
    """
    A pipeline for making health predictions on new images using a trained model.
    """
    def __init__(self, model_dir: str):
        """
        Args:
            model_dir (str): The directory containing the trained model artifacts
                             ('model.joblib' and 'config.json').
        """
        self.model_dir = model_dir
        self.model: ClassifierMixin = None
        self.config: Dict[str, Any] = None
        self.feature_names: List[str] = None
        self.rgb_pipeline: RGBDataPipeline = None

        self._load_artifacts()
        logging.info("PredictionPipeline initialized successfully.")

    def _load_artifacts(self):
        """Loads the model and configuration from the model directory."""
        # Load configuration
        config_path = os.path.join(self.model_dir, "config.json")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file 'config.json' not found in {self.model_dir}")
        
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # Extract feature names in the correct order
        self.feature_names = self.config.get('feature_names')
        if not self.feature_names:
            raise ValueError("'feature_names' not found in config.json. The model cannot be used for prediction.")

        # Load model
        model_path = os.path.join(self.model_dir, "model.joblib")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file 'model.joblib' not found in {self.model_dir}")
            
        self.model = joblib.load(model_path)

        # Initialize the preprocessing pipeline with the loaded config
        self.rgb_pipeline = RGBDataPipeline(self.config['pipeline_config'])
        
        logging.info(f"Loaded model and configuration from {self.model_dir}")

    def predict(self, image_path: str, create_visualization: bool = True) -> Dict[str, Any]:
        """
        Processes a new image and predicts its health status.

        Args:
            image_path (str): The path to the new image file.
            create_visualization (bool): If True, an annotated visualization image
                                         will be created and returned.

        Returns:
            Dict[str, Any]: A dictionary containing the prediction results,
                including 'prediction' (the predicted class label),
                'probabilities' (a dict of class probabilities), and optionally
                'visualization' (the annotated image).
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image to predict not found at: {image_path}")

        logging.info(f"Making prediction for image: {image_path}")

        # 1. Process the image and extract features
        try:
            processed_data = self.rgb_pipeline.process_image(image_path)
            features_dict = processed_data.get('features')
        except Exception as e:
            logging.error(f"Failed to process image {image_path}: {e}", exc_info=True)
            raise

        if not features_dict:
            raise ValueError("Feature extraction failed or returned no features. Cannot make a prediction.")

        # 2. Convert features to a numpy array in the correct order
        feature_vector = np.array([features_dict.get(name, 0) for name in self.feature_names]).reshape(1, -1)

        # 3. Make prediction
        prediction = self.model.predict(feature_vector)[0]
        
        # 4. Get probabilities
        probabilities = {}
        if hasattr(self.model, 'predict_proba'):
            probs = self.model.predict_proba(feature_vector)[0]
            probabilities = {self.model.classes_[i]: float(probs[i]) for i in range(len(self.model.classes_))}
        
        logging.info(f"Prediction: {prediction}, Probabilities: {probabilities}")

        # 5. Create visualization (optional)
        visualization_image = None
        if create_visualization:
            visualization_image = self._create_visualization(
                processed_data['masked_image'],
                prediction,
                probabilities
            )

        return {
            "prediction": prediction,
            "probabilities": probabilities,
            "visualization": visualization_image,
            "features": features_dict
        }

    def _create_visualization(self, masked_image: np.ndarray, prediction: str, probabilities: Dict[str, float]) -> np.ndarray:
        """Creates an annotated image with the prediction results."""
        vis_image = masked_image.copy()
        
        # Create a black banner at the top to display text
        banner_height = 80
        h, w, _ = vis_image.shape
        full_vis = np.zeros((h + banner_height, w, 3), dtype=np.uint8)
        full_vis[banner_height:] = vis_image

        # Define text properties
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        font_color = (255, 255, 255)
        line_type = 2

        # Display prediction
        pred_text = f"Prediction: {str(prediction).upper()}"
        cv2.putText(full_vis, pred_text, (10, 30), font, font_scale, font_color, line_type)

        # Display probabilities
        prob_text = "Probabilities: " + ", ".join([f"{k}: {v:.2f}" for k, v in probabilities.items()])
        cv2.putText(full_vis, prob_text, (10, 60), font, font_scale * 0.9, font_color, line_type)
        
        return full_vis

# --- Example Usage ---
if __name__ == '__main__':
    print("--- RGB Prediction Pipeline Demo ---")

    # This demo requires a trained model. We will use the output from the
    # training.py demo. First, let's ensure it runs to generate the artifacts.
    from .training import TrainingPipeline
    
    # 1. Setup dummy training to get model artifacts
    temp_dir = "c:/temp/rgb_prediction_demo"
    image_dir = os.path.join(temp_dir, "images")
    output_dir = os.path.join(temp_dir, "model_output")
    os.makedirs(image_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    manifest_data = []
    # Create 10 healthy and 10 stressed images for training
    for i in range(20):
        is_healthy = i % 2 == 0
        label = 'healthy' if is_healthy else 'stressed'
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[:] = (40, 50, 60)
        plant_color = (50, 180, 70) if is_healthy else (40, 170, 190)
        cv2.circle(img, (50, 50), 30, plant_color, -1)
        img_name = f"train_plant_{i}.png"
        img_path = os.path.join(image_dir, img_name)
        cv2.imwrite(img_path, img)
        manifest_data.append({'image_path': os.path.join("images", img_name), 'label': label})

    manifest_path = os.path.join(temp_dir, "manifest.csv")
    pd.DataFrame(manifest_data).to_csv(manifest_path, index=False)

    training_config = {
        "data_params": {"manifest_path": manifest_path, "image_base_dir": temp_dir},
        "pipeline_config": {
            "color_correction": {"method": "gray_world"},
            "segmentation": {"method": "hsv_threshold"},
            "feature_extraction": {"feature_sets": ['indices', 'histograms']}
        },
        "model_params": {"type": "RandomForest", "params": {"n_estimators": 10, "random_state": 42}},
        "training_params": {"output_dir": output_dir, "val_size": 0.2, "random_state": 42}
    }
    
    print("\nStep 1: Running a quick training to generate model artifacts...")
    try:
        train_pipeline = TrainingPipeline(training_config)
        train_pipeline.run()
        print("Training finished. Model artifacts are in:", output_dir)
    except Exception as e:
        logging.error(f"Demo training failed, cannot proceed with prediction demo: {e}", exc_info=True)
        exit()

    # 2. Create a new dummy image to predict
    new_image = np.zeros((200, 200, 3), dtype=np.uint8)
    new_image[:] = (35, 45, 55)
    # A slightly yellowish-green plant, could be either
    cv2.circle(new_image, (100, 100), 60, (45, 175, 130), -1)
    new_image_path = os.path.join(temp_dir, "new_plant_to_predict.png")
    cv2.imwrite(new_image_path, new_image)
    print(f"\nStep 2: Created a new image for prediction: {new_image_path}")

    # 3. Initialize the PredictionPipeline and make a prediction
    print("\nStep 3: Initializing prediction pipeline and making a prediction...")
    try:
        prediction_pipeline = PredictionPipeline(model_dir=output_dir)
        result = prediction_pipeline.predict(image_path=new_image_path)

        print("\n--- Prediction Results ---")
        print(f"  Predicted Label: {result['prediction']}")
        print(f"  Probabilities: {result['probabilities']}")
        
        if result['visualization'] is not None:
            vis_path = os.path.join(temp_dir, "prediction_visualization.png")
            cv2.imwrite(vis_path, result['visualization'])
            print(f"  Saved prediction visualization to: {vis_path}")

    except Exception as e:
        logging.error(f"An error occurred during the prediction demo: {e}", exc_info=True)
```