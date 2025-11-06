# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\pest_identification\main.py

"""
Main Entry Point for Pest Identification
========================================

This module serves as the main entry point for the pest identification package.
It provides a command-line interface (CLI) using `argparse` to allow users to
easily run the main functionalities of the package, such as training a new model,
running inference on images, and evaluating a model's performance.

This script ties together all the other modules (`data_loader`, `models`,
`training_engine`, `deployment`) into a cohesive application.

Key Functionalities via CLI:
----------------------------
1.  **`train`**:
    -   Kicks off the model training process.
    -   Requires a path to a project configuration file (`.json` or `.yaml`) that
      defines all parameters for the data, model, loss, optimizer, and training
      engine.
    -   Manages the creation of an experiment directory to store logs, checkpoints,
      and other artifacts.

2.  **`evaluate`**:
    -   Evaluates a trained model on a test dataset.
    -   Requires a path to a trained model checkpoint and the project configuration
      file.
    -   Prints a table of performance metrics (e.g., mAP for detection, accuracy/F1
      for classification).

3.  **`predict`**:
    -   Runs inference on a single image or a directory of images.
    -   Requires a path to a trained model checkpoint and the project configuration.
    -   Outputs the predictions to the console in JSON format and can optionally
      save the images with predictions drawn on them.

4.  **`export`**:
    -   Exports a trained PyTorch model to an optimized format for deployment.
    -   Supports exporting to ONNX (`.onnx`) and TorchScript (`.pt`).
    -   This is a crucial step for preparing a model for production inference.

Configuration-Driven Approach:
------------------------------
The entire system is driven by a central configuration file. This approach has
several advantages:
-   **Reproducibility**: The exact configuration used for a training run can be
  saved, ensuring that the experiment can be reproduced perfectly.
-   **Flexibility**: Users can easily experiment with different models, data
  augmentations, or hyperparameters by simply editing the text-based config
  file, without touching the source code.
-   **Clarity**: The config file serves as a clear record of all settings for a
  given experiment.

Example `config.yaml`:
----------------------
```yaml
project_name: "wheat_aphid_detection_v1"
task: "detection"
device: "cuda"
use_amp: true

data:
  root_dir: "/path/to/pest_dataset"
  # ... other data settings

model:
  name: "retinanet"
  num_classes: 5
  # ... other model settings

loss:
  name: "focal_loss_det" # Placeholder, as loss is internal to RetinaNet
  # ...

optimizer:
  name: "adamw"
  lr: 0.0001

scheduler:
  name: "cosine_annealing"
  T_max: 50

training:
  num_epochs: 50
  experiment_dir: "./experiments"
```

This main script acts as the user-facing orchestrator for the entire pest
identification pipeline.
"""

import argparse
import json
import logging
from pathlib import Path
import yaml  # Requires PyYAML

from .data_loader import PestDataModule
from .models import ModelFactory
from .losses import LossFactory
from .training_engine import TrainingEngine, create_optimizer, create_scheduler
from .callbacks import ModelCheckpoint, TensorBoardLogger, EarlyStopping, LRSchedulerCallback, ProgressLogger
from .deployment import InferenceEngine, visualize_predictions, export_to_onnx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def load_config(config_path: str) -> Dict:
    """Loads a YAML or JSON configuration file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found at {config_path}")
    
    with open(path, 'r') as f:
        if path.suffix in ['.yaml', '.yml']:
            return yaml.safe_load(f)
        elif path.suffix == '.json':
            return json.load(f)
        else:
            raise ValueError(f"Unsupported config file format: {path.suffix}")

def train(args):
    """Handles the training process."""
    logging.info("--- Starting Training Mode ---")
    config = load_config(args.config)
    
    # Create experiment directory
    exp_dir = Path(config['training'].get('experiment_dir', './experiments'))
    project_name = config.get('project_name', 'pest_id_exp')
    run_dir = exp_dir / project_name
    run_dir.mkdir(parents=True, exist_ok=True)
    logging.info(f"Experiment artifacts will be saved to: {run_dir}")

    # Save config to experiment directory
    with open(run_dir / 'config.yaml', 'w') as f:
        yaml.dump(config, f)

    # Initialize components
    data_module = PestDataModule(config['data'])
    data_module.setup('fit')
    
    # Add num_classes from data to model config if not present
    if 'num_classes' not in config['model']:
        if data_module.train_dataset:
            config['model']['num_classes'] = len(data_module.train_dataset.class_to_idx)
        else:
            raise ValueError("Cannot infer num_classes. Please specify in config or ensure data is available.")

    model = ModelFactory.create_model(config['model'])
    loss_fn = LossFactory.create_loss(config['loss'])
    optimizer = create_optimizer(model, config['optimizer'])
    scheduler = create_scheduler(optimizer, config.get('scheduler', {}))

    # Setup callbacks
    callbacks = [
        ModelCheckpoint(
            directory=run_dir / 'checkpoints',
            monitor=config['training'].get('checkpoint_monitor', 'val_loss'),
            mode=config['training'].get('checkpoint_mode', 'min')
        ),
        TensorBoardLogger(log_dir=run_dir / 'tensorboard_logs'),
        EarlyStopping(
            monitor=config['training'].get('early_stop_monitor', 'val_loss'),
            patience=config['training'].get('early_stop_patience', 5),
            mode=config['training'].get('early_stop_mode', 'min')
        ),
        ProgressLogger()
    ]
    if scheduler:
        scheduler_metric = config['scheduler'].get('monitor')
        scheduler_moment = 'batch' if config['scheduler'].get('step_per_batch') else 'epoch'
        callbacks.append(LRSchedulerCallback(scheduler, step_moment=scheduler_moment, metric=scheduler_metric))

    # Initialize and run the Training Engine
    engine = TrainingEngine(
        config=config,
        model=model,
        data_module=data_module,
        loss_fn=loss_fn,
        optimizer=optimizer,
        scheduler=scheduler,
        callbacks=callbacks
    )
    
    engine.train(num_epochs=config['training']['num_epochs'])
    logging.info("--- Training Finished ---")

def evaluate(args):
    """Handles model evaluation."""
    logging.info("--- Starting Evaluation Mode ---")
    config = load_config(args.config)
    
    # Override device if specified in CLI
    if args.device:
        config['device'] = args.device

    data_module = PestDataModule(config['data'])
    data_module.setup('test')
    test_loader = data_module.test_dataloader()

    # Load model for evaluation
    model = ModelFactory.create_model(config['model'])
    model.load_state_dict(torch.load(args.checkpoint, map_location=config['device']))
    
    # Use a dummy engine for evaluation
    engine = TrainingEngine(
        config=config,
        model=model,
        data_module=data_module,
        loss_fn=nn.CrossEntropyLoss(), # Dummy loss
        optimizer=torch.optim.Adam(model.parameters()) # Dummy optimizer
    )

    metrics = engine.evaluate(test_loader)
    logging.info(f"Evaluation Metrics: \n{json.dumps(metrics, indent=2)}")
    logging.info("--- Evaluation Finished ---")

def predict(args):
    """Handles inference on images."""
    logging.info("--- Starting Prediction Mode ---")
    config = load_config(args.config)
    
    # Override device if specified in CLI
    if args.device:
        config['device'] = args.device

    engine = InferenceEngine(model_path=args.checkpoint, config=config)
    
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)

    image_paths = []
    if input_path.is_dir():
        image_paths = list(input_path.glob('*.*'))
    elif input_path.is_file():
        image_paths = [input_path]

    for img_path in image_paths:
        logging.info(f"Predicting on: {img_path.name}")
        try:
            predictions = engine.predict(str(img_path), confidence_threshold=args.threshold)
            logging.info(f"Predictions: {json.dumps(predictions, indent=2)}")

            if args.save_visuals:
                img_with_preds = visualize_predictions(str(img_path), predictions)
                save_path = output_dir / f"{img_path.stem}_predicted.jpg"
                cv2.imwrite(str(save_path), img_with_preds)
                logging.info(f"Saved visualization to {save_path}")
        except Exception as e:
            logging.error(f"Failed to process {img_path.name}: {e}")

    logging.info("--- Prediction Finished ---")

def export(args):
    """Handles model exporting."""
    logging.info("--- Starting Export Mode ---")
    config = load_config(args.config)
    
    engine = InferenceEngine(model_path=args.checkpoint, config=config)
    output_path = Path(args.output)
    output_path.parent.mkdir(exist_ok=True, parents=True)

    if args.format == 'onnx':
        img_size = config['data']['image_size']
        dummy_input_shape = (1, 3, *img_size)
        export_to_onnx(engine, str(output_path), dummy_input_shape)
    elif args.format == 'torchscript':
        logging.info(f"Exporting model to TorchScript at {output_path}...")
        try:
            scripted_model = torch.jit.script(engine.model)
            scripted_model.save(str(output_path))
            logging.info("TorchScript export successful.")
        except Exception as e:
            logging.error(f"TorchScript export failed: {e}", exc_info=True)
    else:
        raise ValueError(f"Unsupported export format: {args.format}")

    logging.info("--- Export Finished ---")


def main():
    """Main function to parse arguments and dispatch commands."""
    parser = argparse.ArgumentParser(description="Pest Identification CLI")
    subparsers = parser.add_subparsers(dest='command', required=True, help="Available commands")

    # --- Train command ---
    parser_train = subparsers.add_parser('train', help="Train a new model")
    parser_train.add_argument('--config', type=str, required=True, help="Path to the configuration file (.yaml or .json)")
    parser_train.set_defaults(func=train)

    # --- Evaluate command ---
    parser_eval = subparsers.add_parser('evaluate', help="Evaluate a trained model")
    parser_eval.add_argument('--config', type=str, required=True, help="Path to the configuration file")
    parser_eval.add_argument('--checkpoint', type=str, required=True, help="Path to the model checkpoint (.pth)")
    parser_eval.add_argument('--device', type=str, help="Override device (e.g., 'cpu', 'cuda:0')")
    parser_eval.set_defaults(func=evaluate)

    # --- Predict command ---
    parser_predict = subparsers.add_parser('predict', help="Run inference on images")
    parser_predict.add_argument('--config', type=str, required=True, help="Path to the configuration file")
    parser_predict.add_argument('--checkpoint', type=str, required=True, help="Path to the model checkpoint")
    parser_predict.add_argument('--input', type=str, required=True, help="Path to an image or a directory of images")
    parser_predict.add_argument('--output_dir', type=str, default='./predictions', help="Directory to save output visuals")
    parser_predict.add_argument('--threshold', type=float, default=0.5, help="Confidence threshold for predictions")
    parser_predict.add_argument('--save_visuals', action='store_true', help="Save images with predictions drawn on them")
    parser_predict.add_argument('--device', type=str, help="Override device")
    parser_predict.set_defaults(func=predict)

    # --- Export command ---
    parser_export = subparsers.add_parser('export', help="Export a model for deployment")
    parser_export.add_argument('--config', type=str, required=True, help="Path to the configuration file")
    parser_export.add_argument('--checkpoint', type=str, required=True, help="Path to the model checkpoint")
    parser_export.add_argument('--output', type=str, required=True, help="Path to save the exported model")
    parser_export.add_argument('--format', type=str, required=True, choices=['onnx', 'torchscript'], help="Export format")
    parser_export.set_defaults(func=export)

    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    # To run from the command line:
    # python -m app.computer_vision.pest_identification.main train --config /path/to/config.yaml
    # python -m app.computer_vision.pest_identification.main predict --config ... --checkpoint ... --input ...
    main()
