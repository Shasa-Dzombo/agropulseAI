# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\weed_detection\main.py

"""
Main Command-Line Interface for Weed Detection
==============================================

This script provides a unified command-line interface (CLI) to interact with the
weed detection module. It uses `argparse` with subparsers to create a clean and
extensible command structure, similar to tools like `git` or `docker`.

The CLI supports two main commands:
1.  **`train`**:
    -   **Purpose**: To launch the model training process.
    -   **Functionality**: This command wraps the `training.py` script. It accepts
      all the arguments defined in `training.get_args_parser()` (e.g., `--data-path`,
      `--model-name`, `--epochs`, `--batch-size`) and passes them to the main
      training function.
    -   **Benefit**: Provides a single entry point for all module operations and
      makes it easy to initiate training without needing to call the training
      script directly.

2.  **`predict`**:
    -   **Purpose**: To run inference on a single image using a trained model.
    -   **Functionality**: This command wraps the `prediction.py` script. It
      accepts arguments like `--model-path`, `--image-path`, `--output-path`, and
      `--threshold` to load a model, process an image, and save the visualized
      output.
    -   **Benefit**: Simplifies the process of testing the model on new images and
      generating visual results.

This structure makes the module self-contained and easy to use from the command
line, promoting reusability and clear separation of concerns.

Usage Examples:
---------------
**Training:**
```bash
python -m app.computer_vision.weed_detection.main train \\
    --data-path /path/to/weed_dataset \\
    --model-name fasterrcnn_resnet50_fpn \\
    --epochs 25 \\
    --output-dir /path/to/save/models
```

**Prediction:**
```bash
python -m app.computer_vision.weed_detection.main predict \\
    --model-path /path/to/best_model.pth \\
    --image-path /path/to/input_image.jpg \\
    --output-path /path/to/output_image.jpg \\
    --threshold 0.6
```
"""

import argparse
import sys
import os
import logging

# Adjust the path to ensure local modules can be imported
# This is important when running the script as a main entry point
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from app.computer_vision.weed_detection import training
from app.computer_vision.weed_detection import prediction
from app.computer_vision.weed_detection.control_strategies import WeedControlAdvisor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """
    The main function that parses arguments and calls the appropriate subcommand.
    """
    parser = argparse.ArgumentParser(description="Weed Detection Module CLI")
    subparsers = parser.add_subparsers(dest='command', required=True, help='Available commands')

    # --- Train Command ---
    parser_train = subparsers.add_parser('train', help='Train a new weed detection model')
    # We can reuse the argument parser from the training script
    training.get_args_parser(parser_train)
    parser_train.set_defaults(func=run_train_command)

    # --- Predict Command ---
    parser_predict = subparsers.add_parser('predict', help='Run inference with a trained model')
    parser_predict.add_argument('--model-path', required=True, help='Path to the trained model checkpoint (.pth)')
    parser_predict.add_argument('--image-path', required=True, help='Path to the input image')
    parser_predict.add_argument('--output-path', required=True, help='Path to save the visualized output image')
    parser_predict.add_argument('--threshold', type=float, default=0.5, help='Confidence threshold for detections')
    parser_predict.add_argument('--device', default='cuda', help='Device to use for inference (cuda or cpu)')
    parser_predict.set_defaults(func=run_predict_command)

    # --- Advise Command ---
    parser_advise = subparsers.add_parser('advise', help='Get control strategy recommendations for a detected weed')
    parser_advise.add_argument('--weed-name', required=True, help='The common name of the weed (e.g., "common_lambsquarters")')
    parser_advise.add_argument('--strategy-type', choices=['all', 'chemical', 'mechanical', 'organic'], default='all', help='The type of control strategy to retrieve')
    parser_advise.set_defaults(func=run_advise_command)

    args = parser.parse_args()
    args.func(args)

def run_train_command(args):
    """
    Executes the training process based on parsed arguments.
    """
    logging.info("Starting 'train' command...")
    try:
        training.main(args)
        logging.info("'train' command finished successfully.")
    except Exception as e:
        logging.error(f"An error occurred during training: {e}", exc_info=True)
        sys.exit(1)

def run_predict_command(args):
    """
    Executes the prediction process based on parsed arguments.
    """
    logging.info("Starting 'predict' command...")
    try:
        # This logic is adapted from the main block of prediction.py
        detector = prediction.WeedDetector(model_path=args.model_path, device=args.device)
        
        if not os.path.exists(args.image_path):
            raise FileNotFoundError(f"Input image not found at {args.image_path}")
        image = prediction.cv2.imread(args.image_path)
        if image is None:
            raise IOError(f"Could not read image from {args.image_path}")

        boxes, labels, scores = detector.predict(image, threshold=args.threshold)
        logging.info(f"Found {len(boxes)} objects with confidence > {args.threshold}")

        output_image = prediction.visualize_predictions(image, boxes, labels, scores, detector.class_map)

        output_dir = os.path.dirname(args.output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        prediction.cv2.imwrite(args.output_path, output_image)
        
        logging.info(f"Prediction complete. Visualized output saved to {args.output_path}")
        
        # After prediction, offer advice for the detected weeds
        if labels:
            unique_weeds = sorted(list(set(labels)))
            logging.info("\n--- Control Recommendations for Detected Weeds ---")
            advisor = WeedControlAdvisor()
            for weed_name in unique_weeds:
                print_advice(advisor, weed_name)
            logging.info("Use the 'advise' command for more detailed strategies.")

        logging.info("'predict' command finished successfully.")

    except Exception as e:
        logging.error(f"An error occurred during prediction: {e}", exc_info=True)
        sys.exit(1)

def run_advise_command(args):
    """
    Executes the advisory process for a given weed.
    """
    logging.info(f"Starting 'advise' command for weed: {args.weed_name}")
    try:
        advisor = WeedControlAdvisor()
        print_advice(advisor, args.weed_name, strategy_type=args.strategy_type)
        logging.info("'advise' command finished successfully.")
    except Exception as e:
        logging.error(f"An error occurred while getting advice: {e}", exc_info=True)
        sys.exit(1)

def print_advice(advisor: WeedControlAdvisor, weed_name: str, strategy_type: str = 'all'):
    """Helper function to format and print control advice."""
    print(f"\n--- Recommendations for: {weed_name.replace('_', ' ').title()} ---")
    try:
        advice = advisor.get_control_strategy(weed_name)
        
        if not advice:
            print("  No specific control strategy found for this weed.")
            return

        if strategy_type in ['all', 'chemical'] and advice.chemical_control:
            print("\n  [Chemical Control]")
            for strat in advice.chemical_control:
                print(f"  - Herbicide: {strat.herbicide_name}")
                print(f"    Type: {strat.type}")
                print(f"    Application: {strat.application_timing}")
                print(f"    Notes: {strat.notes}")

        if strategy_type in ['all', 'mechanical'] and advice.mechanical_control:
            print("\n  [Mechanical Control]")
            for strat in advice.mechanical_control:
                print(f"  - Method: {strat.method}")
                print(f"    Timing: {strat.timing}")
                print(f"    Notes: {strat.notes}")

        if strategy_type in ['all', 'organic'] and advice.organic_control:
            print("\n  [Organic Control]")
            for strat in advice.organic_control:
                print(f"  - Method: {strat.method}")
                print(f"    Description: {strat.description}")
                print(f"    Notes: {strat.notes}")

    except ValueError as e:
        print(f"  Could not retrieve advice: {e}")

if __name__ == '__main__':
    # To make this runnable, we need to ensure the parent directories are in the python path
    # This allows imports like `from app.computer_vision...` to work correctly.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # Re-import with the correct path context
    from app.computer_vision.weed_detection import training, prediction
    from app.computer_vision.weed_detection.control_strategies import WeedControlAdvisor
    
    main()
```