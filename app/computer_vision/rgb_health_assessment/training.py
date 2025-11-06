# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\rgb_health_assessment\training.py

"""
Training and Evaluation Pipeline for RGB-Based Health Models
============================================================

This module provides a complete, end-to-end pipeline for training and evaluating
the machine learning models defined in the `models` module. It is designed to
work with datasets of images and their corresponding health labels, orchestrating
the entire process from data loading to model serialization.

The pipeline is highly configurable and automates several key MLOps practices,
such as experiment tracking, hyperparameter tuning, and detailed performance
evaluation.

Core Components:
---------------
1.  **`RGBDataset`**:
    -   A custom PyTorch-style `Dataset` class (though it doesn't use PyTorch
      tensors) that manages a collection of image paths and their associated labels.
    -   It lazily loads and processes images using the `RGBDataPipeline` only when
      an item is requested, making it memory-efficient for large datasets.

2.  **`TrainingPipeline`**:
    -   The main orchestrator for the training workflow.
    -   **Data Loading & Processing**: Takes a DataFrame of image paths and labels,
      splits it into training and validation sets, and uses `RGBDataset` and
      `RGBDataPipeline` to process the images and extract feature vectors.
    -   **Model Creation**: Uses the `RGBHealthModelFactory` to instantiate the
      model specified in the configuration.
    -   **Hyperparameter Tuning**: Optionally performs an exhaustive grid search
      over a predefined hyperparameter space using `GridSearchCV` to find the
      best model configuration.
    -   **Training**: Trains the final model on the full training dataset using
      the best found hyperparameters (or the default ones if tuning is skipped).
    -   **Evaluation**: Computes a comprehensive set of performance metrics on the
      hold-out validation set, including accuracy, precision, recall, F1-score,
      and a confusion matrix.
    -   **Feature Importance**: For tree-based models (like RandomForest and
      GradientBoosting), it calculates and saves the feature importance scores,
      providing insights into which features are most predictive of health status.
    -   **Serialization**: Saves the trained model, the full pipeline configuration,
      the evaluation report, and the feature importance plot to a specified
      output directory, ensuring reproducibility.

Configuration:
--------------
The entire pipeline is driven by a single JSON configuration file that specifies:
-   `data_params`: Path to the CSV/Excel file containing image paths and labels.
-   `pipeline_config`: The configuration for the `RGBDataPipeline` (preprocessing).
-   `model_params`: The model type and its fixed hyperparameters.
-   `training_params`: Settings for the training process, including test set size,
    output directory, and whether to perform hyperparameter tuning.
-   `hyperparameter_tuning`: The parameter grid to search if tuning is enabled.

This modular and configurable design allows researchers and engineers to easily
experiment with different preprocessing strategies, models, and hyperparameters
to find the optimal solution for their specific use case.
"""

import os
import json
import pandas as pd
import numpy as np
from tqdm import tqdm
import joblib
import logging
from typing import Dict, Any, Tuple, List
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.base import ClassifierMixin

from .preprocessing import RGBDataPipeline
from .models import RGBHealthModelFactory

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Dataset Class ---

class RGBDataset:
    """
    A dataset class to manage image paths and labels, and process them on the fly.
    """
    def __init__(self, dataframe: pd.DataFrame, pipeline: RGBDataPipeline, image_base_dir: str = ''):
        """
        Args:
            dataframe (pd.DataFrame): A DataFrame with 'image_path' and 'label' columns.
            pipeline (RGBDataPipeline): The configured preprocessing pipeline.
            image_base_dir (str): A base directory to prepend to the image paths in the dataframe.
        """
        self.dataframe = dataframe
        self.pipeline = pipeline
        self.image_base_dir = image_base_dir

    def __len__(self) -> int:
        return len(self.dataframe)

    def __getitem__(self, idx: int) -> Tuple[Dict[str, float], Any]:
        """
        Loads, processes an image, and returns its features and label.
        """
        row = self.dataframe.iloc[idx]
        full_image_path = os.path.join(self.image_base_dir, row['image_path'])
        label = row['label']
        
        try:
            processed_data = self.pipeline.process_image(full_image_path)
            features = processed_data['features']
            if not features:
                logging.warning(f"No features extracted for image: {full_image_path}. Skipping.")
                return None, None
            return features, label
        except Exception as e:
            logging.error(f"Failed to process image {full_image_path}: {e}", exc_info=True)
            return None, None

# --- Main Training Pipeline ---

class TrainingPipeline:
    """
    Orchestrates the end-to-end model training and evaluation workflow.
    """
    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config (Dict[str, Any]): The master configuration dictionary.
        """
        self.config = config
        self.data_params = config['data_params']
        self.pipeline_config = config['pipeline_config']
        self.model_params = config['model_params']
        self.training_params = config['training_params']
        self.tuning_params = config.get('hyperparameter_tuning', {})

        self.rgb_pipeline = RGBDataPipeline(self.pipeline_config)
        self.model: ClassifierMixin = None
        self.feature_names: List[str] = []
        
        os.makedirs(self.training_params['output_dir'], exist_ok=True)
        logging.info("Initialized TrainingPipeline.")

    def run(self):
        """Executes the entire training workflow."""
        logging.info("Starting training workflow...")

        # 1. Load and split data manifest
        df = self._load_data_manifest()
        train_df, val_df = train_test_split(
            df,
            test_size=self.training_params.get('val_size', 0.2),
            random_state=self.training_params.get('random_state', 42),
            stratify=df['label'] if 'label' in df.columns else None
        )
        logging.info(f"Data split: {len(train_df)} training samples, {len(val_df)} validation samples.")

        # 2. Process data and extract features
        X_train, y_train = self._process_dataset(train_df)
        X_val, y_val = self._process_dataset(val_df, is_validation=True)
        
        if X_train.shape[0] == 0 or X_val.shape[0] == 0:
            logging.error("No data to train or validate on after feature extraction. Aborting.")
            return

        # 3. Create model
        self.model = RGBHealthModelFactory.create_model(self.model_params)

        # 4. Hyperparameter Tuning (Optional)
        if self.training_params.get('perform_tuning', False) and self.tuning_params:
            logging.info("Starting hyperparameter tuning with GridSearchCV...")
            self._perform_grid_search(X_train, y_train)
        else:
            logging.info("Skipping hyperparameter tuning. Training with default parameters.")
            self.model.fit(X_train, y_train)

        # 5. Evaluate model
        logging.info("Evaluating model on validation set...")
        self._evaluate(X_val, y_val)

        # 6. Save artifacts
        logging.info("Saving training artifacts...")
        self._save_artifacts()
        
        logging.info("Training workflow completed successfully.")

    def _load_data_manifest(self) -> pd.DataFrame:
        """Loads the CSV/Excel file with image paths and labels."""
        path = self.data_params['manifest_path']
        if path.endswith('.csv'):
            return pd.read_csv(path)
        elif path.endswith('.xlsx'):
            return pd.read_excel(path)
        else:
            raise ValueError(f"Unsupported manifest file format: {path}")

    def _process_dataset(self, df: pd.DataFrame, is_validation: bool = False) -> Tuple[np.ndarray, np.ndarray]:
        """
        Uses RGBDataset to process a dataframe of images and returns features and labels.
        """
        dataset = RGBDataset(df, self.rgb_pipeline, self.data_params.get('image_base_dir', ''))
        
        features_list = []
        labels_list = []
        
        logging.info(f"Processing {len(dataset)} images...")
        for i in tqdm(range(len(dataset))):
            features, label = dataset[i]
            if features is not None and label is not None:
                if not self.feature_names and not is_validation:
                    # Capture feature names from the first valid sample in the training set
                    self.feature_names = list(features.keys())
                
                # Ensure consistent feature order
                ordered_features = [features.get(name, 0) for name in self.feature_names]
                features_list.append(ordered_features)
                labels_list.append(label)
        
        if not features_list:
            return np.array([]), np.array([])
            
        return np.array(features_list), np.array(labels_list)

    def _perform_grid_search(self, X_train: np.ndarray, y_train: np.ndarray):
        """Finds the best hyperparameters using GridSearchCV."""
        grid_search = GridSearchCV(
            estimator=self.model,
            param_grid=self.tuning_params['param_grid'],
            cv=self.tuning_params.get('cv', 5),
            scoring=self.tuning_params.get('scoring', 'accuracy'),
            n_jobs=-1,
            verbose=2
        )
        grid_search.fit(X_train, y_train)
        
        logging.info(f"Best parameters found: {grid_search.best_params_}")
        logging.info(f"Best cross-validation score: {grid_search.best_score_:.4f}")
        
        # The best estimator is now our model
        self.model = grid_search.best_estimator_

    def _evaluate(self, X_val: np.ndarray, y_val: np.ndarray):
        """Calculates and saves performance metrics."""
        y_pred = self.model.predict(X_val)
        accuracy = accuracy_score(y_val, y_pred)
        report = classification_report(y_val, y_pred, output_dict=True)
        
        logging.info(f"Validation Accuracy: {accuracy:.4f}")
        logging.info("Classification Report:\n" + classification_report(y_val, y_pred))
        
        # Save report to file
        report_path = os.path.join(self.training_params['output_dir'], "evaluation_report.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=4)
            
        # Create and save confusion matrix plot
        cm = confusion_matrix(y_val, y_pred)
        plt.figure(figsize=(10, 8))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=self.model.classes_, yticklabels=self.model.classes_)
        plt.title('Confusion Matrix')
        plt.xlabel('Predicted Label')
        plt.ylabel('True Label')
        cm_path = os.path.join(self.training_params['output_dir'], "confusion_matrix.png")
        plt.savefig(cm_path)
        plt.close()

    def _save_artifacts(self):
        """Saves the model, config, and feature importances."""
        output_dir = self.training_params['output_dir']
        
        # 1. Save the trained model
        model_path = os.path.join(output_dir, "model.joblib")
        joblib.dump(self.model, model_path)
        
        # 2. Save the configuration used for this run
        config_path = os.path.join(output_dir, "config.json")
        # Add the final best params to the config for reproducibility
        if hasattr(self.model, 'get_params'):
            self.config['model_params']['final_params'] = self.model.get_params()
        self.config['feature_names'] = self.feature_names # Save the feature order
        with open(config_path, 'w') as f:
            json.dump(self.config, f, indent=4)
            
        # 3. Save feature importances if available
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            feature_importance_df = pd.DataFrame({
                'feature': self.feature_names,
                'importance': importances
            }).sort_values(by='importance', ascending=False)
            
            # Save to CSV
            importance_csv_path = os.path.join(output_dir, "feature_importances.csv")
            feature_importance_df.to_csv(importance_csv_path, index=False)
            
            # Save plot of top features
            plt.figure(figsize=(12, 8))
            sns.barplot(x='importance', y='feature', data=feature_importance_df.head(20))
            plt.title('Top 20 Feature Importances')
            plt.tight_layout()
            importance_plot_path = os.path.join(output_dir, "feature_importances.png")
            plt.savefig(importance_plot_path)
            plt.close()

# --- Example Usage ---
if __name__ == '__main__':
    print("--- RGB Training Pipeline Demo ---")
    
    # 1. Create a dummy dataset and manifest file
    temp_dir = "c:/temp/rgb_training_demo"
    image_dir = os.path.join(temp_dir, "images")
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(image_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    manifest_data = []
    for i in range(30): # 30 dummy images
        is_healthy = i % 2 == 0
        label = 'healthy' if is_healthy else 'stressed'
        
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[:] = (40, 50, 60) # Soil background
        
        # Healthy plants are greener, stressed plants are more yellow
        plant_color = (50, 180, 70) if is_healthy else (40, 170, 190)
        cv2.circle(img, (50, 50), 30, plant_color, -1)
        
        img_name = f"plant_{i}.png"
        img_path = os.path.join(image_dir, img_name)
        cv2.imwrite(img_path, img)
        manifest_data.append({'image_path': os.path.join("images", img_name), 'label': label})

    manifest_path = os.path.join(temp_dir, "manifest.csv")
    pd.DataFrame(manifest_data).to_csv(manifest_path, index=False)
    print(f"Created dummy dataset with {len(manifest_data)} images in '{temp_dir}'")

    # 2. Define a master configuration for the pipeline
    master_config = {
        "data_params": {
            "manifest_path": manifest_path,
            "image_base_dir": temp_dir
        },
        "pipeline_config": {
            "color_correction": {"method": "gray_world"},
            "segmentation": {"method": "hsv_threshold"},
            "feature_extraction": {"feature_sets": ['indices', 'histograms']}
        },
        "model_params": {
            "type": "RandomForest",
            "params": {"random_state": 42}
        },
        "training_params": {
            "output_dir": output_dir,
            "val_size": 0.3,
            "random_state": 42,
            "perform_tuning": True
        },
        "hyperparameter_tuning": {
            "param_grid": {
                "n_estimators": [10, 20, 50],
                "max_depth": [None, 5, 10]
            },
            "cv": 3
        }
    }
    
    config_save_path = os.path.join(temp_dir, "run_config.json")
    with open(config_save_path, 'w') as f:
        json.dump(master_config, f, indent=4)
    print(f"Saved master configuration to '{config_save_path}'")

    # 3. Initialize and run the training pipeline
    try:
        pipeline = TrainingPipeline(master_config)
        pipeline.run()
        
        print("\n--- Demo Run Finished ---")
        print(f"Training artifacts saved in: '{output_dir}'")
        print("Check the directory for 'model.joblib', 'config.json', 'evaluation_report.json', and plots.")
    except Exception as e:
        logging.error(f"An error occurred during the demo training run: {e}", exc_info=True)
```