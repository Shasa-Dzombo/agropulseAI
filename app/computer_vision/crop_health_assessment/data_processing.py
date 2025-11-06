# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\crop_health_assessment\data_processing.py

"""
Data Processing for Crop Health Assessment
==========================================

This module is responsible for all data ingestion, preprocessing, and preparation
tasks related to assessing crop health from remote sensing data, primarily
multispectral and hyperspectral imagery.

The complexity in this domain comes from handling multi-band imagery, aligning
it with various sources of ground truth data, and extracting meaningful features
for the health assessment models.

Key Responsibilities:
---------------------
1.  **Data Ingestion**:
    -   Read multi-band raster data, typically in GeoTIFF format, using libraries
      like `rasterio`.
    -   Handle metadata, including coordinate reference systems (CRS), geotransforms,
      and band-specific information (e.g., wavelengths).
    -   Load vector data (e.g., GeoJSON, Shapefiles) that defines field boundaries,
      management zones, or locations of ground truth samples.

2.  **Data Alignment and Fusion**:
    -   **Geospatial Alignment**: Re-project vector and raster data to a common CRS
      to ensure they overlay correctly.
    -   **Temporal Alignment**: Group and align images taken at different times for
      time-series analysis.
    -   **Data Fusion**: Combine remote sensing data with other data sources, such
      as:
        -   Weather data (temperature, precipitation).
        -   Soil sensor data (moisture, nutrient levels).
        -   As-applied data from farm machinery (e.g., fertilizer rates).
        -   Scouting reports and manual observations.

3.  **Preprocessing and Cleaning**:
    -   **Atmospheric Correction**: Apply corrections to remove the effects of the
      atmosphere from the imagery, converting sensor radiance to surface reflectance.
      (This can be a complex process, often relying on pre-computed models or
      specific bands).
    -   **Cloud Masking**: Identify and mask out pixels obscured by clouds or cloud
      shadows, which would otherwise corrupt the analysis.
    -   **Normalization**: Scale pixel values to a standard range (e.g., 0-1) or
      standardize them based on dataset statistics.

4.  **Feature Extraction**:
    -   **Pixel Extraction**: Extract pixel values (spectral signatures) from the
      raster data at specific locations defined by vector points (e.g., soil sample
      locations).
    -   **Zonal Statistics**: Calculate statistics (mean, median, std dev) of pixel
      values within polygons (e.g., management zones) to create aggregate features.
    -   **Data Cube Creation**: For deep learning models, generate small 3D data cubes
      (height x width x bands) centered around points of interest.

5.  **Dataset Creation**:
    -   Structure the processed data into formats suitable for machine learning,
      such as PyTorch or TensorFlow datasets.
    -   Handle the creation of training, validation, and test splits, often using
      spatial cross-validation techniques to avoid data leakage due to spatial
      autocorrelation.

Core Classes:
-------------
-   `MultispectralImage`: A wrapper around a `rasterio` dataset object, providing
  convenience methods for reading bands, getting metadata, and performing common
  preprocessing steps like normalization and cloud masking.

-   `GroundTruthManager`: A class to load, manage, and align various forms of
  ground truth data (points, polygons) with the imagery.

-   `HealthDataPipeline`: The main orchestrator class that uses `MultispectralImage`
  and `GroundTruthManager` to execute a full data processing pipeline from raw
-   files to a machine-learning-ready dataset.

-   `CropHealthDataset`: A PyTorch-compatible `Dataset` class that serves individual
  data samples (e.g., spectral signatures, image patches) and their corresponding
  health labels.
"""

import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
import fiona
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple, Any, Optional
from torch.utils.data import Dataset
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MultispectralImage:
    """
    A handler for multispectral raster images, providing methods for reading,
    preprocessing, and extracting data.
    """
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"Image file not found: {self.file_path}")
        
        self.dataset = rasterio.open(self.file_path)
        self.meta = self.dataset.meta
        self.crs = self.dataset.crs
        self.transform = self.dataset.transform
        self.band_count = self.dataset.count
        self.band_names: Optional[List[str]] = None # To be populated if available

        logging.info(f"Opened multispectral image: {self.file_path.name} with {self.band_count} bands.")
        logging.info(f"CRS: {self.crs}, Dimensions: {self.meta['width']}x{self.meta['height']}")

    def get_band_data(self, band_indices: List[int]) -> np.ndarray:
        """Reads specific bands into a numpy array."""
        for i in band_indices:
            if not (1 <= i <= self.band_count):
                raise ValueError(f"Invalid band index {i}. Must be between 1 and {self.band_count}.")
        
        return self.dataset.read(band_indices)

    def reproject_to_crs(self, target_crs: str, output_path: str) -> 'MultispectralImage':
        """Reprojects the image to a new Coordinate Reference System."""
        transform, width, height = calculate_default_transform(
            self.crs, target_crs, self.meta['width'], self.meta['height'], *self.dataset.bounds
        )
        
        kwargs = self.meta.copy()
        kwargs.update({
            'crs': target_crs,
            'transform': transform,
            'width': width,
            'height': height
        })

        with rasterio.open(output_path, 'w', **kwargs) as dst:
            for i in range(1, self.band_count + 1):
                reproject(
                    source=rasterio.band(self.dataset, i),
                    destination=rasterio.band(dst, i),
                    src_transform=self.transform,
                    src_crs=self.crs,
                    dst_transform=transform,
                    dst_crs=target_crs,
                    resampling=Resampling.nearest
                )
        logging.info(f"Reprojected image to {target_crs} and saved to {output_path}")
        return MultispectralImage(output_path)

    def extract_pixels_at_points(self, points: List[Tuple[float, float]]) -> np.ndarray:
        """
        Extracts the spectral signatures (all bands) for a list of geographic
        coordinate points.
        
        Args:
            points: A list of (longitude, latitude) tuples.
            
        Returns:
            A numpy array of shape (num_points, num_bands).
        """
        if not self.crs.is_geographic:
             logging.warning("CRS is not geographic, but points are assumed to be (lon, lat). Ensure they match.")

        rows, cols = rasterio.transform.rowcol(self.transform, [p[0] for p in points], [p[1] for p in points])
        
        # Filter out points that are outside the image bounds
        valid_indices = [
            i for i, (r, c) in enumerate(zip(rows, cols))
            if 0 <= r < self.meta['height'] and 0 <= c < self.meta['width']
        ]
        
        if len(valid_indices) < len(points):
            logging.warning(f"{len(points) - len(valid_indices)} points are outside the image extent.")

        valid_rows = [rows[i] for i in valid_indices]
        valid_cols = [cols[i] for i in valid_indices]

        if not valid_rows:
            return np.array([]).reshape(0, self.band_count)

        # rasterio's sample method is efficient for this
        point_coords = [(points[i][0], points[i][1]) for i in valid_indices]
        
        # The sample method returns a generator
        samples = self.dataset.sample(point_coords)
        
        # Convert generator to numpy array
        pixel_values = np.vstack([s for s in samples])
        
        return pixel_values

    def get_zonal_stats(self, zone_geometries: List[Dict]) -> pd.DataFrame:
        """
        Calculates zonal statistics for a list of polygon geometries.
        
        Args:
            zone_geometries: A list of GeoJSON-like geometry dictionaries.
            
        Returns:
            A pandas DataFrame with statistics for each zone and each band.
        """
        stats = []
        for i, geom in enumerate(zone_geometries):
            try:
                out_image, out_transform = mask(self.dataset, [geom], crop=True, nodata=self.meta.get('nodata'))
                
                zone_stats = {'zone_id': i}
                for band_idx in range(out_image.shape[0]):
                    band_data = out_image[band_idx, :, :]
                    # Use a masked array to ignore nodata values in calculations
                    masked_data = np.ma.masked_equal(band_data, self.meta.get('nodata', 0))
                    
                    if masked_data.count() > 0: # Check if there is any valid data
                        zone_stats[f'band_{band_idx+1}_mean'] = masked_data.mean()
                        zone_stats[f'band_{band_idx+1}_median'] = np.ma.median(masked_data)
                        zone_stats[f'band_{band_idx+1}_std'] = masked_data.std()
                        zone_stats[f'band_{band_idx+1}_min'] = masked_data.min()
                        zone_stats[f'band_{band_idx+1}_max'] = masked_data.max()
                    else:
                        # Fill with NaNs if the zone is empty or outside the raster
                        for stat_name in ['mean', 'median', 'std', 'min', 'max']:
                            zone_stats[f'band_{band_idx+1}_{stat_name}'] = np.nan
                stats.append(zone_stats)
            except Exception as e:
                logging.error(f"Could not process zone {i}: {e}")
                stats.append({'zone_id': i}) # Append empty stats
                
        return pd.DataFrame(stats)

    def close(self):
        """Closes the rasterio dataset."""
        self.dataset.close()
        logging.info(f"Closed image file: {self.file_path.name}")

class GroundTruthManager:
    """
    Manages loading and aligning ground truth data from vector files (Shapefile, GeoJSON).
    """
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"Ground truth file not found: {self.file_path}")
        
        with fiona.open(self.file_path, 'r') as source:
            self.crs = source.crs
            self.schema = source.schema
            self.records = list(source)
        
        logging.info(f"Loaded {len(self.records)} ground truth records from {self.file_path.name}")

    def get_geometries(self, target_crs: Optional[str] = None) -> List[Dict]:
        """
        Returns a list of geometries, optionally reprojected to a target CRS.
        """
        if target_crs and self.crs != target_crs:
            # This is a simplified reprojection. For production, use pyproj for more control.
            logging.warning("Reprojection on-the-fly is not implemented in this mock. "
                            "Ensure ground truth CRS matches image CRS.")
        
        return [rec['geometry'] for rec in self.records]

    def get_properties(self) -> List[Dict]:
        """Returns a list of properties for each feature."""
        return [rec['properties'] for rec in self.records]

    def to_dataframe(self) -> pd.DataFrame:
        """Converts the ground truth records to a pandas DataFrame."""
        properties = self.get_properties()
        geometries = self.get_geometries()
        df = pd.DataFrame(properties)
        df['geometry'] = geometries
        return df

class HealthDataPipeline:
    """
    Orchestrates the entire data processing workflow from raw files to a
    structured DataFrame ready for ML.
    """
    def __init__(self, image_path: str, ground_truth_path: str, config: Dict):
        self.image = MultispectralImage(image_path)
        self.ground_truth = GroundTruthManager(ground_truth_path)
        self.config = config
        self.processing_mode = config.get('processing_mode', 'zonal') # 'zonal' or 'pixel'

        # Ensure CRS match
        if self.image.crs != self.ground_truth.crs:
            logging.warning(f"CRS mismatch! Image: {self.image.crs}, Ground Truth: {self.ground_truth.crs}. "
                            "Reprojection should be handled for accurate alignment.")
            # In a real scenario, you would reproject one to match the other.
            # For this example, we'll assume they are compatible.

    def run(self) -> pd.DataFrame:
        """Executes the data processing pipeline."""
        logging.info(f"Starting data pipeline in '{self.processing_mode}' mode.")
        
        gt_df = self.ground_truth.to_dataframe()
        
        if self.processing_mode == 'zonal':
            if self.ground_truth.schema['geometry'] not in ['Polygon', 'MultiPolygon']:
                raise ValueError("Zonal mode requires Polygon geometries in ground truth file.")
            
            zonal_stats_df = self.image.get_zonal_stats(gt_df['geometry'].tolist())
            # Join ground truth properties with the calculated zonal statistics
            merged_df = gt_df.join(zonal_stats_df.set_index('zone_id'))
            
        elif self.processing_mode == 'pixel':
            if self.ground_truth.schema['geometry'] != 'Point':
                raise ValueError("Pixel mode requires Point geometries in ground truth file.")
            
            points = [(geom['coordinates'][0], geom['coordinates'][1]) for geom in gt_df['geometry']]
            pixel_values = self.image.extract_pixels_at_points(points)
            
            band_columns = [f'band_{i+1}' for i in range(pixel_values.shape[1])]
            pixel_df = pd.DataFrame(pixel_values, columns=band_columns)
            
            # Join ground truth properties with the extracted pixel values
            merged_df = pd.concat([gt_df.reset_index(drop=True), pixel_df], axis=1)
            
        else:
            raise ValueError(f"Unsupported processing mode: {self.processing_mode}")
            
        self.image.close()
        logging.info("Data pipeline finished successfully.")
        return merged_df.drop(columns=['geometry']) # Drop geometry as it's not needed for ML

class CropHealthDataset(Dataset):
    """
    A PyTorch Dataset for crop health assessment.
    Assumes input is a DataFrame from the HealthDataPipeline.
    """
    def __init__(self, dataframe: pd.DataFrame, feature_columns: List[str], target_column: str):
        self.features = dataframe[feature_columns].values.astype(np.float32)
        self.targets = dataframe[target_column].values.astype(np.float32)
        
        if self.features.shape[0] != self.targets.shape[0]:
            raise ValueError("Features and targets must have the same number of samples.")
            
        logging.info(f"Created dataset with {len(self)} samples.")

    def __len__(self) -> int:
        return len(self.targets)

    def __getitem__(self, idx: int) -> Tuple[np.ndarray, np.ndarray]:
        return self.features[idx], self.targets[idx]

# Example Usage (for demonstration)
if __name__ == '__main__':
    # This is a mock example. It requires dummy files to be created.
    # 1. Create a dummy GeoTIFF
    # 2. Create a dummy Shapefile
    
    # Create a dummy directory
    DUMMY_DATA_DIR = Path('./dummy_health_data')
    DUMMY_DATA_DIR.mkdir(exist_ok=True)
    
    IMAGE_PATH = DUMMY_DATA_DIR / 'dummy_image.tif'
    SHAPEFILE_PATH = DUMMY_DATA_DIR / 'dummy_zones.shp'

    # --- Create Dummy GeoTIFF ---
    dummy_array = np.random.rand(5, 256, 256).astype(np.float32) * 100
    dummy_transform = rasterio.transform.from_origin(10, 50, 1, 1)
    with rasterio.open(
        IMAGE_PATH, 'w', driver='GTiff', height=256, width=256,
        count=5, dtype=np.float32, crs='EPSG:4326', transform=dummy_transform
    ) as dst:
        dst.write(dummy_array)
    
    # --- Create Dummy Shapefile (Polygons) ---
    from shapely.geometry import Polygon, mapping
    schema = {'geometry': 'Polygon', 'properties': {'health_score': 'float'}}
    polygons = [
        Polygon([(10, 40), (20, 40), (20, 30), (10, 30), (10, 40)]),
        Polygon([(30, 20), (40, 20), (40, 10), (30, 10), (30, 20)])
    ]
    with fiona.open(
        SHAPEFILE_PATH, 'w', driver='ESRI Shapefile', crs='EPSG:4326', schema=schema
    ) as c:
        for i, poly in enumerate(polygons):
            c.write({
                'geometry': mapping(poly),
                'properties': {'health_score': np.random.uniform(1, 5)}
            })

    logging.info("--- Running Zonal Statistics Example ---")
    zonal_config = {'processing_mode': 'zonal'}
    pipeline_zonal = HealthDataPipeline(str(IMAGE_PATH), str(SHAPEFILE_PATH), zonal_config)
    zonal_df = pipeline_zonal.run()
    print("Zonal Statistics DataFrame:")
    print(zonal_df.head())

    # --- Create Dummy Shapefile (Points) ---
    POINT_SHAPEFILE_PATH = DUMMY_DATA_DIR / 'dummy_points.shp'
    from shapely.geometry import Point, mapping
    schema_points = {'geometry': 'Point', 'properties': {'nitrogen_level': 'float'}}
    points_geom = [Point(15, 35), Point(35, 15), Point(50, 50)]
    with fiona.open(
        POINT_SHAPEFILE_PATH, 'w', driver='ESRI Shapefile', crs='EPSG:4326', schema=schema_points
    ) as c:
        for pt in points_geom:
            c.write({
                'geometry': mapping(pt),
                'properties': {'nitrogen_level': np.random.uniform(0.5, 2.0)}
            })

    logging.info("\n--- Running Pixel Extraction Example ---")
    pixel_config = {'processing_mode': 'pixel'}
    pipeline_pixel = HealthDataPipeline(str(IMAGE_PATH), str(POINT_SHAPEFILE_PATH), pixel_config)
    pixel_df = pipeline_pixel.run()
    print("Pixel Extraction DataFrame:")
    print(pixel_df.head())

    # --- Create a PyTorch Dataset ---
    if not pixel_df.empty:
        feature_cols = [col for col in pixel_df.columns if 'band' in col]
        target_col = 'nitrogen_level'
        dataset = CropHealthDataset(pixel_df, feature_cols, target_col)
        print(f"\nSuccessfully created a dataset. First sample:")
        features, target = dataset[0]
        print(f"Features: {features}")
        print(f"Target: {target}")
