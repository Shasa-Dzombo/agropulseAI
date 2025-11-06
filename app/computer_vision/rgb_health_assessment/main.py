# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\rgb_health_assessment\main.py

"""
Main Command-Line Interface for RGB Health Assessment
=====================================================

This script provides a powerful and easy-to-use command-line interface (CLI)
to run the various workflows of the RGB Health Assessment module. It serves as
the main entry point for users to train models, make predictions on new images,
and generate example configurations.

The CLI is built with Python's `argparse` and is organized into logical
sub-commands for each major task.

Supported Workflows:
--------------------
1.  **`train`**:
    -   **Purpose**: To execute the end-to-end model training pipeline.
    -   **Process**: This command initializes and runs the `TrainingPipeline` from
      the `training` module. It requires a single argument: the path to a master
      JSON configuration file that defines all parameters for the run.
    -   **Output**: The command will create an output directory containing the
      trained model (`model.joblib`), the configuration file used (`config.json`),
      a detailed evaluation report, and plots for the confusion matrix and
      feature importances.

2.  **`predict`**:
    -   **Purpose**: To use a pre-trained model to predict the health status of
      one or more new images.
    -   **Process**: This command initializes the `PredictionPipeline` from the
      `prediction` module. It requires the path to the directory containing the
      trained model artifacts and the path(s) to the new image(s).
    -   **Output**: For each image, it prints the predicted class and class
      probabilities to the console. It also saves an annotated visualization
      of the prediction in the same directory as the input image.

3.  **`create-config`**:
    -   **Purpose**: To generate a template configuration file.
    -   **Process**: This command creates a `template_config.json` file in the
      specified directory. This file contains all the necessary sections and
      parameters for a training run, which users can then edit to suit their
      specific dataset and requirements. This helps lower the barrier to entry
      for using the training pipeline.

Usage Examples:
---------------
-   **Generate a template configuration file**:
    ```bash
    python -m app.computer_vision.rgb_health_assessment.main create-config --path ./
    ```

-   **Train a new model using a configuration file**:
    ```bash
    python -m app.computer_vision.rgb_health_assessment.main train --config-path /path/to/your_config.json
    ```

-   **Predict the health of a single image**:
    ```bash
    python -m app.computer_vision.rgb_health_assessment.main predict --model-dir /path/to/model_output --image-paths /path/to/new_image.jpg
    ```

-   **Predict the health of multiple images**:
    ```bash
    python -m app.computer_vision.rgb_health_assessment.main predict --model-dir /path/to/model_output --image-paths /path/to/img1.png /path/to/img2.jpg
    ```
"""

import argparse
import os
import json
import logging

# Import the main pipeline classes from the module
from .training import TrainingPipeline
from .prediction import PredictionPipeline

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_training(args):
    """Handles the 'train' sub-command."""
    logger.info(f"Starting training workflow with configuration: {args.config_path}")
    
    if not os.path.exists(args.config_path):
        logger.error(f"Configuration file not found at: {args.config_path}")
        return

    try:
        with open(args.config_path, 'r') as f:
            config = json.load(f)
        
        pipeline = TrainingPipeline(config)
        pipeline.run()
        
        logger.info("Training workflow completed successfully.")
        logger.info(f"All artifacts saved to: {config['training_params']['output_dir']}")
    except Exception as e:
        logger.error(f"An error occurred during the training workflow: {e}", exc_info=True)

def run_prediction(args):
    """Handles the 'predict' sub-command."""
    logger.info(f"Initializing prediction pipeline from model directory: {args.model_dir}")

    try:
        predictor = PredictionPipeline(model_dir=args.model_dir)
        
        for image_path in args.image_paths:
            logger.info(f"\n--- Predicting for: {image_path} ---")
            if not os.path.exists(image_path):
                logger.warning(f"Image not found at {image_path}. Skipping.")
                continue
            
            result = predictor.predict(image_path=image_path)
            
            print(f"  Prediction: {result['prediction']}")
            print(f"  Probabilities: {result['probabilities']}")
            
            # Save visualization
            if result['visualization'] is not None:
                import cv2
                base_name = os.path.basename(image_path)
                name, ext = os.path.splitext(base_name)
                vis_path = os.path.join(os.path.dirname(image_path), f"{name}_prediction_vis{ext}")
                cv2.imwrite(vis_path, result['visualization'])
                logger.info(f"Saved prediction visualization to: {vis_path}")

    except Exception as e:
        logger.error(f"An error occurred during the prediction workflow: {e}", exc_info=True)

def create_config_template(args):
    """Handles the 'create-config' sub-command."""
    template = {
        "data_params": {
            "manifest_path": "/path/to/your/data_manifest.csv",
            "image_base_dir": "/path/to/your/images_folder"
        },
        "pipeline_config": {
            "color_correction": {
                "method": "gray_world"
            },
            "segmentation": {
                "method": "hsv_threshold",
                "params": {
                    "lower_green": [30, 40, 40],
                    "upper_green": [90, 255, 255]
                }
            },
            "feature_extraction": {
                "feature_sets": ["indices", "histograms", "texture", "morphology"]
            }
        },
        "model_params": {
            "type": "RandomForest",
            "params": {
                "n_estimators": 100,
                "random_state": 42
            }
        },
        "training_params": {
            "output_dir": "/path/to/your/output_folder",
            "val_size": 0.2,
            "random_state": 42,
            "perform_tuning": True
        },
        "hyperparameter_tuning": {
            "param_grid": {
                "n_estimators": [50, 100, 200],
                "max_depth": [None, 10, 20, 30],
                "min_samples_split": [2, 5, 10]
            },
            "cv": 5,
            "scoring": "accuracy"
        }
    }
    
    output_path = os.path.join(args.path, "template_config.json")
    try:
        with open(output_path, 'w') as f:
            json.dump(template, f, indent=4)
        logger.info(f"Successfully created template configuration file at: {output_path}")
        logger.info("Please edit this file with the correct paths and parameters for your dataset.")
    except Exception as e:
        logger.error(f"Could not create template file: {e}", exc_info=True)

def main():
    """Main function to parse arguments and dispatch to the correct workflow."""
    parser = argparse.ArgumentParser(description="RGB Health Assessment Module CLI")
    subparsers = parser.add_subparsers(dest='command', required=True, help="Available commands")

    # --- Train sub-command ---
    parser_train = subparsers.add_parser('train', help="Train a new plant health model.")
    parser_train.add_argument('--config-path', type=str, required=True, help="Path to the master JSON configuration file.")
    parser_train.set_defaults(func=run_training)

    # --- Predict sub-command ---
    parser_predict = subparsers.add_parser('predict', help="Predict health status for new images.")
    parser_predict.add_argument('--model-dir', type=str, required=True, help="Directory containing the trained model artifacts.")
    parser_predict.add_argument('--image-paths', type=str, nargs='+', required=True, help="One or more paths to images for prediction.")
    parser_predict.set_defaults(func=run_prediction)

    # --- Create Config sub-command ---
    parser_create_config = subparsers.add_parser('create-config', help="Generate a template configuration file.")
    parser_create_config.add_argument('--path', type=str, required=True, help="Directory where the template_config.json will be saved.")
    parser_create_config.set_defaults(func=create_config_template)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
```