"""
Main Command-Line Interface for Yield Estimation
================================================

This script provides a unified command-line interface (CLI) to interact with the
entire yield estimation module. It uses `argparse` with subparsers to create a
clean and extensible command structure for training and prediction.

The CLI supports two main commands:
1.  **`train`**:
    -   **Purpose**: To launch the model training process.
    -   **Functionality**: This command wraps the `training.py` script. It accepts
      arguments to specify the task type, model configuration, and data modalities.

2.  **`predict`**:
    -   **Purpose**: To run inference on a single image using a trained model.
    -   **Functionality**: This command wraps the `prediction.py` script. It
      accepts arguments like `--model-path`, `--image-path`, and `--output-path`
      to load a model, process an image, and save the visualized output.

This structure makes the module self-contained and easy to use from the command
line, promoting reusability and clear separation of concerns.

Usage Examples:
---------------
**Training a detection model:**
```bash
python -m app.computer_vision.yield_estimation.main train \\
    --task detection \\
    --model-key default_detection \\
    --modalities rgb
```

**Training a segmentation model:**
```bash
python -m app.computer_vision.yield_estimation.main train \\
    --task segmentation \\
    --model-key default_segmentation \\
    --modalities rgb nir
```

**Prediction:**
```bash
python -m app.computer_vision.yield_estimation.main predict \\
    --model-path models/checkpoints/detection_best_model.pth \\
    --image-path /path/to/input_image.jpg \\
    --output-path /path/to/output_image.jpg \\
    --threshold 0.6
```
"""

import argparse
import sys
import os
import logging

# Adjust path to allow for root-level imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from app.computer_vision.yield_estimation import training
from app.computer_vision.yield_estimation import prediction

def main():
    """
    Main function that parses arguments and calls the appropriate subcommand.
    """
    parser = argparse.ArgumentParser(description="Yield Estimation Module CLI")
    subparsers = parser.add_subparsers(dest='command', required=True, help='Available commands')

    # --- Train Command ---
    parser_train = subparsers.add_parser('train', help='Train a new yield estimation model')
    train_group = parser_train.add_argument_group('Training Arguments')
    training.get_args_parser(train_group) # Add args from training script
    parser_train.set_defaults(func=run_train_command)

    # --- Predict Command ---
    parser_predict = subparsers.add_parser('predict', help='Run inference with a trained model')
    predict_group = parser_predict.add_argument_group('Prediction Arguments')
    # We add arguments directly here as prediction.py's main is the entry point
    predict_group.add_argument('--model-path', required=True, help='Path to the trained model checkpoint (.pth)')
    predict_group.add_argument('--image-path', required=True, help='Path to the input image')
    predict_group.add_argument('--output-path', required=True, help='Path to save the visualized output image')
    predict_group.add_argument('--threshold', type=float, default=0.5, help='Confidence threshold for detections')
    predict_group.add_argument('--device', default='cuda', help='Device to use for inference (cuda or cpu)')
    parser_predict.set_defaults(func=run_predict_command)

    args = parser.parse_args()
    args.func(args)

def run_train_command(args):
    """Executes the training process."""
    logging.info("CLI: Initiating 'train' command.")
    try:
        training.main(args)
        logging.info("CLI: 'train' command finished successfully.")
    except Exception as e:
        logging.error(f"CLI: An error occurred during training: {e}", exc_info=True)
        sys.exit(1)

def run_predict_command(args):
    """Executes the prediction process."""
    logging.info("CLI: Initiating 'predict' command.")
    try:
        # The main logic is already in prediction.py's main function
        prediction.main()
        logging.info("CLI: 'predict' command finished successfully.")
    except Exception as e:
        logging.error(f"CLI: An error occurred during prediction: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    # This allows the script to be run directly, ensuring correct module resolution
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # Re-import with the correct path context
    from app.computer_vision.yield_estimation import training, prediction
    
    main()
