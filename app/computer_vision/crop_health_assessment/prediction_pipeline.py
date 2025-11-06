# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\crop_health_assessment\prediction_pipeline.py

"""
Prediction Pipeline for Crop Health Assessment
==============================================

This module defines the pipeline for generating crop health predictions from new
multispectral or hyperspectral imagery using a pre-trained model. The pipeline
is designed to be flexible, handling both classical machine learning models
(from scikit-learn) and deep learning models (from PyTorch).

The prediction process involves several key steps:
1.  **Model Loading**: Loading a serialized model from disk. This can be a
    `joblib` file for scikit-learn models or a `.pth` file for PyTorch models.
    The pipeline also loads the associated configuration, which contains crucial
    metadata like the features used for training.

2.  **Data Ingestion**: Reading a new raster image (e.g., a GeoTIFF) for which
    predictions are to be made. This is handled by the `MultispectralImage`
    class from the `data_processing` module.

3.  **Feature Engineering**: Preprocessing the raw raster data to generate the
    features that the model expects. This typically involves:
    -   Calculating the same set of vegetation indices that were used during training.
    -   Stacking the required spectral bands and indices into a feature array.

4.  **Prediction**:
    -   For pixel-based models (like RandomForest or 1D CNNs), the pipeline
      iterates over each pixel of the image, extracts its feature vector, and
      feeds it to the model to get a health score.
    -   For patch-based models (like 2D or 3D CNNs), the pipeline extracts
      small image patches (e.g., 32x32 pixels) and feeds them to the model.
      This can capture spatial context.

5.  **Output Generation**: Assembling the per-pixel or per-patch predictions
    into a 2D map (a raster image) that represents the spatial distribution of
    the predicted crop health metric. This output map is georeferenced,
    inheriting the coordinate reference system (CRS) and transform from the
    input image, allowing it to be used in GIS software.

Core Class:
-----------
-   `HealthPredictionPipeline`: Orchestrates the entire prediction workflow. It
    is initialized with a path to a trained model and its configuration. The
    `predict` method takes a new image path and produces a prediction map.

Design Considerations:
----------------------
-   **Efficiency**: Processing large raster images pixel by pixel can be slow.
    The pipeline is optimized by reading the image data into memory in chunks
    (windows) and vectorizing the prediction process where possible.
-   **Extensibility**: The pipeline is designed to be easily extended to support
    new model types or different feature engineering strategies.
-   **Configuration-Driven**: The entire process is driven by a configuration
    file, ensuring that the prediction steps are consistent with the training
    procedure.
"""

import os
import json
import joblib
import numpy as np
import torch
import rasterio
from rasterio.windows import Window
from tqdm import tqdm
from typing import Dict, Any, Union

from .data_processing import MultispectralImage
from .vegetation_indices import calculate_indices
from .models import HealthModelFactory

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class HealthPredictionPipeline:
    """
    Orchestrates the process of generating predictions from a trained crop health model.
    """
    def __init__(self, model_dir: str):
        """
        Initializes the prediction pipeline by loading the model and configuration.

        Args:
            model_dir (str): The directory containing the trained model file
                             (e.g., 'model.joblib' or 'model.pth') and the
                             'config.json' file.
        """
        self.model_dir = model_dir
        self.config: Dict[str, Any] = self._load_config()
        self.model_type = self.config['model_params']['type']
        self.model = self._load_model()
        self.features = self.config['data_params']['features']
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logging.info(f"Prediction pipeline initialized for model type '{self.model_type}' on device '{self.device}'.")
        logging.info(f"Features for prediction: {self.features}")

    def _load_config(self) -> Dict[str, Any]:
        """Loads the configuration file from the model directory."""
        config_path = os.path.join(self.model_dir, 'config.json')
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found at {config_path}")
        with open(config_path, 'r') as f:
            return json.load(f)

    def _load_model(self) -> Any:
        """Loads the trained model from disk."""
        model_path = os.path.join(self.model_dir, self.config['training_params']['output_model_name'])
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at {model_path}")

        if self.model_type in ['RandomForest', 'GradientBoosting', 'SVR', 'PLSRegression']:
            logging.info(f"Loading scikit-learn model from {model_path}")
            return joblib.load(model_path)
        elif self.model_type in ['SpectralCNN1D', 'SpectralCNN3D', 'HybridCNN']:
            logging.info(f"Loading PyTorch model from {model_path}")
            model_params = self.config['model_params'].get('params', {})
            # We need to know the number of input features to initialize the model
            model_params['n_features'] = len(self.features)
            
            model_factory = HealthModelFactory(
                model_type=self.model_type,
                **model_params
            )
            model = model_factory.create_model()
            model.load_state_dict(torch.load(model_path, map_location=self.device))
            model.to(self.device)
            model.eval() # Set model to evaluation mode
            return model
        else:
            raise ValueError(f"Unsupported model type for prediction: {self.model_type}")

    def predict(self, image_path: str, output_path: str, chunk_size: int = 256):
        """
        Generates a prediction map for a new image.

        Args:
            image_path (str): Path to the input multispectral/hyperspectral image.
            output_path (str): Path to save the output prediction map (GeoTIFF).
            chunk_size (int): The size of the square chunks (windows) to process at a time.
                              Helps manage memory for large images.
        """
        logging.info(f"Starting prediction for image: {image_path}")
        
        # 1. Ingest the new image data
        ms_image = MultispectralImage(image_path)
        
        # 2. Prepare the output raster
        profile = ms_image.profile
        profile.update(dtype=rasterio.float32, count=1, compress='lzw')
        
        with rasterio.open(output_path, 'w', **profile) as dst:
            # Iterate over the image in chunks
            for i in tqdm(range(0, ms_image.height, chunk_size), desc="Processing chunks"):
                for j in range(0, ms_image.width, chunk_size):
                    height = min(chunk_size, ms_image.height - i)
                    width = min(chunk_size, ms_image.width - j)
                    window = Window(j, i, width, height)
                    
                    # 3. Feature Engineering for the chunk
                    chunk_data = ms_image.read_bands(window=window)
                    
                    # Handle masked data if present
                    mask = chunk_data.mask.any(axis=0) if hasattr(chunk_data, 'mask') else np.zeros((height, width), dtype=bool)
                    
                    # Create a feature stack (bands + indices)
                    feature_stack = self._prepare_features(chunk_data, ms_image.band_names)
                    
                    # Reshape for prediction: (n_pixels, n_features)
                    pixels_to_predict = feature_stack[:, ~mask].T
                    
                    if pixels_to_predict.shape[0] == 0:
                        continue # Skip empty chunks
                        
                    # 4. Prediction
                    predictions = self._predict_pixels(pixels_to_predict)
                    
                    # 5. Write output
                    output_chunk = np.full((height, width), profile['nodata'], dtype=np.float32)
                    output_chunk[~mask] = predictions
                    
                    dst.write(output_chunk, 1, window=window)
                    
        logging.info(f"Prediction map successfully saved to: {output_path}")

    def _prepare_features(self, chunk_data: np.ndarray, band_names: Dict[int, str]) -> np.ndarray:
        """
        Prepares the feature stack (bands and VIs) for a given data chunk.
        
        Args:
            chunk_data (np.ndarray): The raw band data for the chunk.
            band_names (Dict[int, str]): Mapping from band index to band name.
            
        Returns:
            np.ndarray: A stack of features with shape (n_features, height, width).
        """
        h, w = chunk_data.shape[1], chunk_data.shape[2]
        feature_list = []
        
        # Calculate required vegetation indices
        vi_features = [f for f in self.features if f not in band_names.values()]
        if vi_features:
            indices = calculate_indices(chunk_data, band_names, vi_features)
        
        for feature_name in self.features:
            if feature_name in band_names.values():
                # Find the band index for this feature name
                band_idx = [k for k, v in band_names.items() if v == feature_name][0] - 1
                feature_list.append(chunk_data[band_idx])
            elif feature_name in vi_features:
                feature_list.append(indices[feature_name])
            else:
                logging.warning(f"Feature '{feature_name}' not found in bands or calculable indices. Skipping.")
        
        return np.stack(feature_list, axis=0)

    def _predict_pixels(self, pixel_features: np.ndarray) -> np.ndarray:
        """
        Performs prediction on a batch of pixel feature vectors.
        
        Args:
            pixel_features (np.ndarray): Array of shape (n_pixels, n_features).
            
        Returns:
            np.ndarray: Array of shape (n_pixels,) containing the predictions.
        """
        if self.model_type in ['RandomForest', 'GradientBoosting', 'SVR', 'PLSRegression']:
            return self.model.predict(pixel_features)
        
        elif self.model_type in ['SpectralCNN1D', 'SpectralCNN3D', 'HybridCNN']:
            # PyTorch models require data to be on the correct device
            pixel_features_tensor = torch.from_numpy(pixel_features).float().to(self.device)
            
            # Reshape for the specific model if necessary
            if self.model_type == 'SpectralCNN1D':
                # (batch, features) -> (batch, 1, features)
                pixel_features_tensor = pixel_features_tensor.unsqueeze(1)
            # Note: 3D/Hybrid models are typically patch-based and would require a different
            # data loading strategy. This implementation assumes they can operate per-pixel
            # for simplicity, which might not be their intended use.
            
            with torch.no_grad():
                predictions = self.model(pixel_features_tensor)
            
            return predictions.cpu().numpy().squeeze()
        
        return np.array([])


# --- Example Usage ---
if __name__ == '__main__':
    # This is a conceptual example. Running it requires a trained model and data.
    print("--- Health Prediction Pipeline Example ---")
    
    # Assume we have a trained model in 'c:/temp/agro_model'
    # This directory would contain 'model.joblib' and 'config.json'
    
    # 1. Create dummy model and config for demonstration
    
    # Dummy config
    dummy_config = {
        "model_params": {"type": "RandomForest", "params": {"n_estimators": 10}},
        "data_params": {"features": ["B4_RED", "B8_NIR", "NDVI"]},
        "training_params": {"output_model_name": "dummy_model.joblib"}
    }
    
    # Dummy scikit-learn model
    from sklearn.ensemble import RandomForestRegressor
    dummy_model = RandomForestRegressor(n_estimators=10)
    # A real model would be fitted on data, e.g., dummy_model.fit(X, y)
    
    # Create a temporary directory for the model
    model_dir = "c:/temp/dummy_health_model"
    os.makedirs(model_dir, exist_ok=True)
    
    # Save dummy model and config
    joblib.dump(dummy_model, os.path.join(model_dir, dummy_config['training_params']['output_model_name']))
    with open(os.path.join(model_dir, 'config.json'), 'w') as f:
        json.dump(dummy_config, f)
        
    print(f"Created a dummy model and config in: {model_dir}")

    # 2. Create a dummy input image
    dummy_image_path = "c:/temp/dummy_input_image.tif"
    profile = {
        'driver': 'GTiff', 'dtype': 'uint16', 'nodata': 0,
        'width': 100, 'height': 100, 'count': 2,
        'crs': 'EPSG:32610', 'transform': rasterio.transform.from_origin(1000, 2000, 10, 10)
    }
    with rasterio.open(dummy_image_path, 'w', **profile) as dst:
        # Band 1: RED (B4), Band 2: NIR (B8)
        red_band = np.random.randint(500, 1500, (100, 100), dtype=np.uint16)
        nir_band = np.random.randint(2000, 4000, (100, 100), dtype=np.uint16)
        dst.write(red_band, 1)
        dst.write(nir_band, 2)
        dst.update_tags(1, band_name='B4_RED')
        dst.update_tags(2, band_name='B8_NIR')
        
    print(f"Created a dummy input image: {dummy_image_path}")

    # 3. Initialize and run the prediction pipeline
    try:
        prediction_pipeline = HealthPredictionPipeline(model_dir=model_dir)
        
        output_prediction_path = "c:/temp/prediction_map.tif"
        prediction_pipeline.predict(
            image_path=dummy_image_path,
            output_path=output_prediction_path
        )
        
        print(f"\nPrediction finished. Output map saved to: {output_prediction_path}")
        
        # Verify output
        with rasterio.open(output_prediction_path) as src:
            print(f"Output map properties: {src.width}x{src.height}, CRS={src.crs}")
            data = src.read(1)
            print(f"Sample prediction values: min={np.min(data)}, max={np.max(data)}")

    except Exception as e:
        print(f"\nAn error occurred during the example run: {e}")
    finally:
        # Clean up dummy files
        import shutil
        if os.path.exists(model_dir):
            shutil.rmtree(model_dir)
        if os.path.exists(dummy_image_path):
            os.remove(dummy_image_path)
        if os.path.exists("c:/temp/prediction_map.tif"):
            os.remove("c:/temp/prediction_map.tif")
        print("\nCleaned up dummy files.")

```