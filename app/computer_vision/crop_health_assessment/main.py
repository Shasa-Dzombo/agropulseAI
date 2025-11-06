# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\crop_health_assessment\main.py

"""
Main Command-Line Interface for Crop Health Assessment
======================================================

This script provides a command-line interface (CLI) to orchestrate the different
workflows within the Crop Health Assessment module. It allows users to easily
execute training, prediction, and temporal analysis tasks from the terminal.

The CLI is built using Python's `argparse` module and is structured around
sub-commands, each corresponding to a major workflow.

Workflows Supported:
--------------------
1.  **`train`**:
    -   **Purpose**: To train a new crop health model.
    -   **Process**: This command initializes and runs the `HealthTrainingPipeline`.
      It requires a single argument: the path to a JSON configuration file.
    -   **Configuration File**: The JSON config file is the single source of truth
      for the training process. It defines everything from the paths to the
      training data, the type of model to use (e.g., 'RandomForest', 'SpectralCNN1D'),
      the features to include (bands and vegetation indices), and the
      hyperparameters for the model and training loop.

2.  **`predict`**:
    -   **Purpose**: To generate a crop health prediction map for a new image
      using a pre-trained model.
    -   **Process**: This command runs the `HealthPredictionPipeline`. It requires
      three arguments:
        1.  The path to the directory containing the trained model and its
            accompanying `config.json`.
        2.  The path to the new input raster image (e.g., a GeoTIFF).
        3.  The path where the output prediction map (also a GeoTIFF) will be saved.

3.  **`analyze-temporal`**:
    -   **Purpose**: To perform temporal analysis on a time-series of vegetation
      indices for a specific field or region.
    -   **Process**: This command demonstrates the capabilities of the `temporal_analysis`
      module. It takes a CSV file containing time-series data (dates and VI values),
      performs smoothing, fits a phenology model to extract key growth dates (SOS, POS, EOS),
      and runs an anomaly detection algorithm.
    -   **Input Format**: The input CSV file should have at least two columns,
      typically 'date' and a vegetation index like 'ndvi'.

Usage Examples:
---------------
-   **Training a new model**:
    ```bash
    python -m app.computer_vision.crop_health_assessment.main train --config-path /path/to/training_config.json
    ```

-   **Generating a prediction map**:
    ```bash
    python -m app.computer_vision.crop_health_assessment.main predict --model-dir /path/to/model --input-image /path/to/new_image.tif --output-path /path/to/prediction.tif
    ```

-   **Running temporal analysis**:
    ```bash
    python -m app.computer_vision.crop_health_assessment.main analyze-temporal --csv-path /path/to/field_timeseries.csv
    ```
"""

import argparse
import json
import os
import pandas as pd
import numpy as np

# Import the core components of the package
from .training_pipeline import HealthTrainingPipeline
from .prediction_pipeline import HealthPredictionPipeline
from .temporal_analysis import TimeSeriesSmoother, PhenologyModel, TemporalAnomalyDetector, double_logistic

import logging

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
        
        pipeline = HealthTrainingPipeline(config)
        pipeline.run()
        
        logger.info("Training workflow completed successfully.")
    except Exception as e:
        logger.error(f"An error occurred during the training workflow: {e}", exc_info=True)

def run_prediction(args):
    """Handles the 'predict' sub-command."""
    logger.info(f"Starting prediction workflow.")
    logger.info(f"Model Directory: {args.model_dir}")
    logger.info(f"Input Image: {args.input_image}")
    logger.info(f"Output Path: {args.output_path}")

    try:
        pipeline = HealthPredictionPipeline(model_dir=args.model_dir)
        pipeline.predict(
            image_path=args.input_image,
            output_path=args.output_path
        )
        logger.info("Prediction workflow completed successfully.")
    except Exception as e:
        logger.error(f"An error occurred during the prediction workflow: {e}", exc_info=True)

def run_temporal_analysis(args):
    """Handles the 'analyze-temporal' sub-command."""
    logger.info(f"Starting temporal analysis workflow for: {args.csv_path}")

    if not os.path.exists(args.csv_path):
        logger.error(f"CSV file not found at: {args.csv_path}")
        return

    try:
        # 1. Load and prepare data
        df = pd.read_csv(args.csv_path, parse_dates=['date'])
        df = df.set_index('date')
        
        # Assuming the CSV has a column named 'ndvi'
        if 'ndvi' not in df.columns:
            logger.error("Input CSV must contain an 'ndvi' column.")
            return
            
        ts_raw = df['ndvi']
        logger.info(f"Loaded time-series with {len(ts_raw)} observations.")

        # 2. Smooth and interpolate
        smoother = TimeSeriesSmoother(method='savgol', window_length=15, polyorder=2)
        ts_smoothed = smoother.smooth(ts_raw)
        ts_daily = smoother.interpolate(ts_smoothed, freq='D')
        logger.info("Time-series smoothed and interpolated to daily frequency.")

        # 3. Fit phenology model
        pheno_model = PhenologyModel(ts_daily)
        pheno_model.fit()
        if pheno_model.pheno_metrics:
            logger.info("Phenological Metrics Extracted:")
            for key, value in pheno_model.pheno_metrics.items():
                logger.info(f"  - {key}: {value.strftime('%Y-%m-%d')}")
        else:
            logger.warning("Could not extract phenological metrics.")

        # 4. Anomaly Detection (using a simple Z-score for demonstration)
        # Create dummy historical data for the example
        historical_data = []
        for i in range(3): # 3 pseudo-historical seasons
            noise = np.random.normal(0, 0.05, len(ts_raw))
            offset = (i - 1) * 0.02
            hist_series = ts_raw + noise + offset
            historical_data.append(hist_series)
        
        anomaly_detector = TemporalAnomalyDetector(method='z_score')
        anomaly_detector.fit(historical_data)
        
        # Introduce a synthetic anomaly for demonstration
        ts_anomaly = ts_raw.copy()
        anomaly_date = ts_anomaly.index[len(ts_anomaly) // 2]
        ts_anomaly.loc[anomaly_date] *= 0.7 # 30% drop in NDVI
        
        anomaly_scores = anomaly_detector.detect(ts_anomaly, threshold=2.0)
        
        anomalies_found = anomaly_scores[anomaly_scores > 2.0]
        logger.info(f"Anomaly detection found {len(anomalies_found)} potential anomalies.")
        if not anomalies_found.empty:
            logger.info("Top 5 anomalies (date, z-score):")
            for date, score in anomalies_found.nlargest(5).items():
                logger.info(f"  - {date.strftime('%Y-%m-%d')}: {score:.2f}")

        logger.info("Temporal analysis workflow completed.")

    except Exception as e:
        logger.error(f"An error occurred during temporal analysis: {e}", exc_info=True)


def create_dummy_files_for_testing():
    """Creates a set of dummy files to test the CLI commands."""
    logger.info("Creating dummy files for testing purposes...")
    
    # Create a temp directory
    temp_dir = "c:/temp/crop_health_demo"
    os.makedirs(temp_dir, exist_ok=True)
    
    # --- For Training ---
    train_config_path = os.path.join(temp_dir, "training_config.json")
    dummy_config = {
        "data_params": {
            "raster_path": "dummy_raster.tif", # This file won't be created to avoid rasterio dependency here
            "vector_path": "dummy_vectors.geojson",
            "features": ["B4_RED", "B8_NIR", "NDVI"],
            "target_metric": "yield"
        },
        "model_params": {
            "type": "RandomForest",
            "params": {"n_estimators": 50, "random_state": 42}
        },
        "training_params": {
            "output_dir": temp_dir,
            "output_model_name": "health_model.joblib",
            "test_size": 0.25
        }
    }
    with open(train_config_path, 'w') as f:
        json.dump(dummy_config, f, indent=4)
    logger.info(f"Created dummy training config: {train_config_path}")
    
    # --- For Temporal Analysis ---
    csv_path = os.path.join(temp_dir, "temporal_data.csv")
    dates = pd.to_datetime(pd.date_range(start='2023-04-01', end='2023-09-30', freq='7D'))
    doy = dates.dayofyear
    ndvi = double_logistic(doy, 0.15, 0.65, 150, 0.1, 230, 0.1, 0) + np.random.normal(0, 0.03, len(dates))
    pd.DataFrame({'date': dates, 'ndvi': ndvi}).to_csv(csv_path, index=False)
    logger.info(f"Created dummy temporal data CSV: {csv_path}")
    
    logger.info("\n--- Instructions for Testing ---")
    logger.info("NOTE: The 'train' and 'predict' commands require actual data and may not fully run with these dummy files.")
    logger.info(f"1. Test Temporal Analysis: \n   python -m app.computer_vision.crop_health_assessment.main analyze-temporal --csv-path {csv_path}")
    logger.info(f"2. Test Training (will fail on data loading, but tests config parsing): \n   python -m app.computer_vision.crop_health_assessment.main train --config-path {train_config_path}")
    logger.info("---------------------------------")


def main():
    """Main function to parse arguments and dispatch to the correct workflow."""
    parser = argparse.ArgumentParser(description="Crop Health Assessment Module CLI")
    subparsers = parser.add_subparsers(dest='command', required=True, help="Available commands")

    # --- Train sub-command ---
    parser_train = subparsers.add_parser('train', help="Train a new crop health model.")
    parser_train.add_argument('--config-path', type=str, required=True, help="Path to the JSON training configuration file.")
    parser_train.set_defaults(func=run_training)

    # --- Predict sub-command ---
    parser_predict = subparsers.add_parser('predict', help="Generate predictions with a trained model.")
    parser_predict.add_argument('--model-dir', type=str, required=True, help="Directory containing the trained model and config.json.")
    parser_predict.add_argument('--input-image', type=str, required=True, help="Path to the input image for prediction.")
    parser_predict.add_argument('--output-path', type=str, required=True, help="Path to save the output prediction map.")
    parser_predict.set_defaults(func=run_prediction)

    # --- Temporal Analysis sub-command ---
    parser_temporal = subparsers.add_parser('analyze-temporal', help="Perform temporal analysis on a VI time-series.")
    parser_temporal.add_argument('--csv-path', type=str, required=True, help="Path to the CSV file with 'date' and 'ndvi' columns.")
    parser_temporal.set_defaults(func=run_temporal_analysis)
    
    # --- Dummy file generation command ---
    parser_dummy = subparsers.add_parser('create-test-files', help="Create dummy files for testing the CLI.")
    parser_dummy.set_defaults(func=lambda args: create_dummy_files_for_testing())

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
```