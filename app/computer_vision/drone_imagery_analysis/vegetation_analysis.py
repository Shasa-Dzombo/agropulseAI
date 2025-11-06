# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\drone_imagery_analysis\vegetation_analysis.py

"""
Vegetation Analysis from Drone-Derived Data Products
=====================================================

This module provides a comprehensive suite of tools for performing advanced
vegetation analysis using data products derived from the drone imagery pipeline,
such as orthomosaics, Digital Surface Models (DSMs), and Digital Terrain Models (DTMs).

The analyses provided are critical for precision agriculture, enabling farmers
and agronomists to monitor crop health, assess growth, and make informed
management decisions at the individual plant or sub-field level.

Key Components and Analyses:
----------------------------
1.  **Canopy Height Model (CHM) Generation**:
    -   Calculates a CHM by subtracting the DTM (bare earth) from the DSM (top
      surface). The CHM represents the height of objects above the ground, which
      is a direct measure of plant height.

2.  **Vegetation Index (VI) Calculation**:
    -   A powerful tool for assessing crop health, vigor, and stress. This
      component computes various VIs from a multispectral orthomosaic.
    -   It requires the orthomosaic to contain specific spectral bands, such as
      Near-Infrared (NIR), Red, Green, Blue, and Red-Edge.
    -   **Indices Implemented**:
        -   `NDVI` (Normalized Difference Vegetation Index): General health and biomass.
        -   `SAVI` (Soil-Adjusted Vegetation Index): NDVI modified to reduce soil
          background influence.
        -   `EVI` (Enhanced Vegetation Index): Improved sensitivity in high biomass
          areas.
        -   `NDRE` (Normalized Difference Red Edge Index): Sensitive to chlorophyll
          content, useful for late-season nitrogen management.
        -   `GNDVI` (Green Normalized Difference Vegetation Index): Similar to NDVI but
          uses the green band, sensitive to chlorophyll concentration.

3.  **Individual Plant Segmentation and Analysis**:
    -   An advanced algorithm to detect, segment, and analyze individual plants.
      This is the cornerstone of per-plant analytics.
    -   **Workflow**:
        1.  **Local Maxima Detection**: Finds potential plant centers by identifying
            peaks in the Canopy Height Model.
        2.  **Marker-Controlled Watershed Segmentation**: Uses the detected peaks as
            markers to segment the CHM into individual plant crowns, preventing
            over-segmentation.
        3.  **Property Extraction**: For each segmented plant, it calculates key
            metrics like location, height, crown diameter, area, and estimated volume.

4.  **Canopy Cover and Gap Analysis**:
    -   **Canopy Cover**: Calculates the percentage of the ground covered by
      vegetation, a key indicator of crop growth and weed pressure. This is
      typically done by thresholding an NDVI map.
    -   **Row and Gap Detection**: Identifies crop rows using techniques like the
      Hough Transform on the vegetation mask. It then analyzes these rows to
      detect and quantify gaps where plants are missing.

5.  **`VegetationAnalyzer`**:
    -   The main orchestrator class that integrates all these functionalities. It
      takes the core data products as input and provides a clean API to run the
      various analyses and generate output reports or maps.

Dependencies:
-------------
- NumPy: For all numerical and array operations.
- Rasterio: For reading and writing geospatial raster data (orthomosaics, DEMs).
- Scikit-image: For advanced image processing tasks like segmentation (watershed),
  feature detection (local maxima), and transformations (Hough).
- Shapely: For geometric calculations on plant crowns.
- GeoPandas: For creating and managing georeferenced vector data (e.g., shapefiles
  of plant locations).
"""

import numpy as np
import rasterio
from rasterio.windows import Window
from skimage.feature import peak_local_max
from skimage.segmentation import watershed
from skimage.measure import regionprops
from skimage.transform import hough_line, hough_line_peaks
from scipy.ndimage import distance_transform_edt
import geopandas as gpd
from shapely.geometry import Point, Polygon
import logging
import time
from typing import Tuple, List, Dict, Optional, Any
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Data Structures ---

@dataclass
class PlantMetrics:
    """Stores metrics for a single detected plant."""
    id: int
    location: Point  # Centroid of the plant in the CRS of the input data
    max_height: float
    avg_height: float
    crown_area: float  # Area in square meters
    crown_diameter: float # Estimated diameter in meters
    crown_polygon: Polygon # The geometric shape of the crown
    estimated_volume: float # A simple volumetric estimate

# --- Core Components ---

class CanopyHeightModel:
    """
    Generates a Canopy Height Model (CHM) from a DSM and DTM.
    """
    def __init__(self, dsm_path: str, dtm_path: str):
        self.dsm_path = dsm_path
        self.dtm_path = dtm_path

    def generate(self, output_path: str, chunk_size: int = 2048):
        """
        Generates the CHM by subtracting the DTM from the DSM.
        Processes in chunks to handle large files.

        Args:
            output_path (str): Path to save the output CHM GeoTIFF.
            chunk_size (int): The size of processing chunks (in pixels).
        """
        logging.info("Generating Canopy Height Model (CHM)...")
        start_time = time.time()

        with rasterio.open(self.dsm_path) as dsm_src, rasterio.open(self.dtm_path) as dtm_src:
            # Verify that the DSM and DTM are compatible
            if dsm_src.profile['crs'] != dtm_src.profile['crs'] or dsm_src.profile['transform'] != dtm_src.profile['transform']:
                # In a real application, you would reproject/resample the DTM to match the DSM
                raise ValueError("DSM and DTM must have the same CRS and transform for CHM generation.")

            profile = dsm_src.profile
            profile.update(dtype=rasterio.float32, compress='lzw', nodata=np.nan)

            with rasterio.open(output_path, 'w', **profile) as dst:
                for i in range(0, dsm_src.width, chunk_size):
                    for j in range(0, dsm_src.height, chunk_size):
                        width = min(chunk_size, dsm_src.width - i)
                        height = min(chunk_size, dsm_src.height - j)
                        window = Window(i, j, width, height)

                        dsm_chunk = dsm_src.read(1, window=window)
                        dtm_chunk = dtm_src.read(1, window=window)

                        chm_chunk = dsm_chunk.astype(np.float32) - dtm_chunk.astype(np.float32)
                        chm_chunk[chm_chunk < 0] = 0  # Heights cannot be negative
                        
                        # Handle no-data values
                        nodata_mask = (dsm_chunk == dsm_src.nodata) | (dtm_chunk == dtm_src.nodata)
                        chm_chunk[nodata_mask] = np.nan

                        dst.write(chm_chunk, 1, window=window)
        
        logging.info(f"CHM generation complete in {time.time() - start_time:.2f}s. Saved to {output_path}.")

class VegetationIndexCalculator:
    """
    Calculates various vegetation indices from a multispectral orthomosaic.
    """
    def __init__(self, ortho_path: str, band_map: Dict[str, int]):
        """
        Args:
            ortho_path (str): Path to the multispectral orthomosaic GeoTIFF.
            band_map (Dict[str, int]): A dictionary mapping band names (e.g., 'red', 'nir')
                                       to their 1-based band index in the GeoTIFF.
        """
        self.ortho_path = ortho_path
        self.band_map = {k.lower(): v for k, v in band_map.items()}
        self._validate_bands()

    def _validate_bands(self):
        required_for_any = {'red', 'green', 'blue', 'nir', 'red_edge'}
        with rasterio.open(self.ortho_path) as src:
            if max(self.band_map.values()) > src.count:
                raise ValueError("Band index in band_map exceeds the number of bands in the raster.")
        
        if not any(key in self.band_map for key in required_for_any):
             logging.warning("Band map does not contain standard band names (red, nir, etc.). Calculations may fail.")

    def _read_band(self, src: rasterio.io.DatasetReader, band_name: str) -> np.ndarray:
        """Reads a specific band, handling potential errors."""
        if band_name not in self.band_map:
            raise ValueError(f"'{band_name}' band not defined in band map.")
        band_data = src.read(self.band_map[band_name]).astype(np.float32)
        band_data[band_data == src.nodata] = np.nan
        return band_data

    def calculate(self, index_name: str, output_path: str):
        """
        Calculates a specified vegetation index and saves it as a GeoTIFF.

        Args:
            index_name (str): The name of the index to calculate (e.g., 'NDVI').
            output_path (str): Path to save the output index map.
        """
        index_name = index_name.upper()
        logging.info(f"Calculating {index_name} index...")
        
        with rasterio.open(self.ortho_path) as src:
            profile = src.profile
            profile.update(dtype=rasterio.float32, count=1, compress='lzw', nodata=np.nan)

            with rasterio.open(output_path, 'w', **profile) as dst:
                # This implementation reads the whole bands into memory.
                # For very large files, chunk-based processing would be necessary.
                
                try:
                    if index_name == 'NDVI':
                        nir = self._read_band(src, 'nir')
                        red = self._read_band(src, 'red')
                        index_map = (nir - red) / (nir + red + 1e-6)
                    elif index_name == 'GNDVI':
                        nir = self._read_band(src, 'nir')
                        green = self._read_band(src, 'green')
                        index_map = (nir - green) / (nir + green + 1e-6)
                    elif index_name == 'NDRE':
                        nir = self._read_band(src, 'nir')
                        red_edge = self._read_band(src, 'red_edge')
                        index_map = (nir - red_edge) / (nir + red_edge + 1e-6)
                    elif index_name == 'SAVI':
                        nir = self._read_band(src, 'nir')
                        red = self._read_band(src, 'red')
                        L = 0.5  # Soil brightness correction factor
                        index_map = ((nir - red) / (nir + red + L)) * (1 + L)
                    elif index_name == 'EVI':
                        nir = self._read_band(src, 'nir')
                        red = self._read_band(src, 'red')
                        blue = self._read_band(src, 'blue')
                        index_map = 2.5 * ((nir - red) / (nir + 6 * red - 7.5 * blue + 1))
                    else:
                        raise ValueError(f"Unknown vegetation index: {index_name}")
                except ValueError as e:
                    logging.error(f"Failed to calculate {index_name}: {e}")
                    return

                dst.write(index_map, 1)
        
        logging.info(f"{index_name} map saved to {output_path}.")

class PlantSegmenter:
    """
    Segments and analyzes individual plants from a Canopy Height Model.
    """
    def __init__(self, chm_path: str):
        self.chm_path = chm_path

    def segment_and_analyze(self, min_height: float = 0.2, peak_min_distance: int = 5) -> List[PlantMetrics]:
        """
        Performs plant segmentation and extracts metrics for each plant.

        Args:
            min_height (float): Minimum height to be considered a plant.
            peak_min_distance (int): The minimum distance (in pixels) between peaks
                                     to be considered separate plants.

        Returns:
            A list of PlantMetrics objects.
        """
        logging.info("Starting individual plant segmentation and analysis...")
        start_time = time.time()

        with rasterio.open(self.chm_path) as src:
            chm = src.read(1)
            transform = src.transform
            crs = src.crs
            
            # Handle no-data
            chm[chm == src.nodata] = 0
            chm[np.isnan(chm)] = 0

            # 1. Create a mask for areas above the minimum height
            plant_mask = chm > min_height

            # 2. Find local maxima (potential plant centers)
            coordinates = peak_local_max(chm, min_distance=peak_min_distance, labels=plant_mask)
            
            # Create markers for watershed
            markers = np.zeros(chm.shape, dtype=bool)
            markers[tuple(coordinates.T)] = True
            from scipy.ndimage import label
            markers, _ = label(markers)

            # 3. Perform watershed segmentation
            # The algorithm floods basins from the markers until they meet at the "watersheds".
            # We use the inverse of the CHM so that peaks become basins.
            labels = watershed(-chm, markers, mask=plant_mask)
            
            logging.info(f"Found {len(np.unique(labels)) - 1} potential plants.")

            # 4. Extract properties for each labeled region
            plant_metrics_list = []
            regions = regionprops(labels, intensity_image=chm)
            
            pixel_area = abs(transform.a * transform.e)

            for i, props in enumerate(regions):
                if props.max_intensity < min_height:
                    continue

                # Get geometric properties
                center_y, center_x = props.centroid
                world_x, world_y = transform * (center_x, center_y)
                
                crown_poly_pixels = Polygon(props.coords[:, ::-1]) # regionprops gives (row, col)
                
                # Convert polygon to world coordinates
                crown_coords_world = [transform * (px, py) for px, py in crown_poly_pixels.exterior.coords]
                crown_poly_world = Polygon(crown_coords_world)

                metrics = PlantMetrics(
                    id=i + 1,
                    location=Point(world_x, world_y),
                    max_height=props.max_intensity,
                    avg_height=props.mean_intensity,
                    crown_area=props.area * pixel_area,
                    crown_diameter=props.equivalent_diameter * np.sqrt(pixel_area),
                    crown_polygon=crown_poly_world,
                    estimated_volume=props.area * pixel_area * props.mean_intensity
                )
                plant_metrics_list.append(metrics)

        logging.info(f"Segmentation and analysis complete in {time.time() - start_time:.2f}s. Found {len(plant_metrics_list)} plants.")
        return plant_metrics_list

class FieldCoverageAnalyzer:
    """
    Analyzes canopy cover, crop rows, and planting gaps.
    """
    def __init__(self, vi_map_path: str):
        self.vi_map_path = vi_map_path

    def analyze_canopy_cover(self, threshold: float = 0.3) -> float:
        """
        Calculates the percentage of the area covered by vegetation.

        Args:
            threshold (float): The VI value above which a pixel is considered vegetation.

        Returns:
            The canopy cover percentage (0.0 to 100.0).
        """
        logging.info(f"Analyzing canopy cover with threshold {threshold}...")
        with rasterio.open(self.vi_map_path) as src:
            vi_map = src.read(1)
            nodata_mask = (vi_map == src.nodata) | np.isnan(vi_map)
            
            total_pixels = np.sum(~nodata_mask)
            if total_pixels == 0:
                return 0.0
            
            vegetation_pixels = np.sum(vi_map[~nodata_mask] > threshold)
            
            canopy_cover = (vegetation_pixels / total_pixels) * 100.0
            logging.info(f"Canopy cover is {canopy_cover:.2f}%.")
            return canopy_cover

    def detect_crop_rows(self, vi_threshold: float = 0.3, hough_threshold: int = 100) -> Optional[Dict[str, Any]]:
        """
        Detects dominant crop rows in the field.

        Args:
            vi_threshold (float): Threshold to create the vegetation mask.
            hough_threshold (int): Accumulator threshold for the Hough transform.

        Returns:
            A dictionary with 'angle' and 'spacing' of the detected rows, or None.
        """
        logging.info("Detecting crop rows...")
        with rasterio.open(self.vi_map_path) as src:
            vi_map = src.read(1)
            vi_map[np.isnan(vi_map)] = 0
            veg_mask = (vi_map > vi_threshold).astype(np.uint8)

            # Use Hough Transform to find lines
            h, theta, d = hough_line(veg_mask)
            
            # Find peaks in the Hough accumulator
            _, angles, dists = hough_line_peaks(h, theta, d, threshold=hough_threshold)

            if len(angles) == 0:
                logging.warning("No significant crop rows detected.")
                return None

            # Find the dominant angle
            # A more robust method would use histogram analysis
            dominant_angle = np.rad2deg(np.median(angles))
            
            # Analyze spacing at the dominant angle
            # This is a simplification; a full analysis is complex
            # We assume rows are mostly parallel
            dists_at_angle = sorted([dist for angle, dist in zip(angles, dists) if np.isclose(np.rad2deg(angle), dominant_angle, atol=5)])
            spacings = np.diff(dists_at_angle)
            
            if len(spacings) == 0:
                logging.warning("Could not determine row spacing.")
                return {'angle': dominant_angle, 'spacing': None}

            median_spacing = np.median(spacings) * abs(src.transform.a) # Convert to meters

            result = {'angle': dominant_angle, 'spacing': median_spacing}
            logging.info(f"Detected crop rows with dominant angle {dominant_angle:.2f} degrees and median spacing {median_spacing:.2f}m.")
            return result

# --- Main Orchestrator ---

class VegetationAnalyzer:
    """
    Orchestrates all vegetation analysis tasks.
    """
    def __init__(self, dsm_path: str, dtm_path: str, ortho_path: str, band_map: Dict[str, int]):
        self.dsm_path = dsm_path
        self.dtm_path = dtm_path
        self.ortho_path = ortho_path
        self.band_map = band_map
        
        # Paths for intermediate products
        self.chm_path = dsm_path.replace('.tif', '_chm.tif')
        self.ndvi_path = ortho_path.replace('.tif', '_ndvi.tif')

    def run_full_analysis(self, output_plants_shapefile: str):
        """
        Runs a default full analysis pipeline.
        """
        logging.info("--- Starting Full Vegetation Analysis Pipeline ---")

        # 1. Generate CHM
        chm_generator = CanopyHeightModel(self.dsm_path, self.dtm_path)
        chm_generator.generate(self.chm_path)

        # 2. Generate NDVI for canopy cover and row analysis
        vi_calculator = VegetationIndexCalculator(self.ortho_path, self.band_map)
        vi_calculator.calculate('NDVI', self.ndvi_path)

        # 3. Analyze canopy cover and rows
        coverage_analyzer = FieldCoverageAnalyzer(self.ndvi_path)
        canopy_cover = coverage_analyzer.analyze_canopy_cover()
        row_info = coverage_analyzer.detect_crop_rows()

        # 4. Segment individual plants
        plant_segmenter = PlantSegmenter(self.chm_path)
        plant_metrics = plant_segmenter.segment_and_analyze()

        # 5. Save plant metrics to a shapefile
        if plant_metrics:
            gdf = gpd.GeoDataFrame(
                data=[{'id': p.id, 'max_height': p.max_height, 'crown_area': p.crown_area} for p in plant_metrics],
                geometry=[p.location for p in plant_metrics],
                crs=plant_metrics[0].location.wkt # Get CRS from first point
            )
            gdf.to_file(output_plants_shapefile)
            logging.info(f"Plant locations and metrics saved to {output_plants_shapefile}")

        logging.info("--- Full Vegetation Analysis Pipeline Complete ---")
        return {
            'canopy_cover': canopy_cover,
            'row_info': row_info,
            'plant_count': len(plant_metrics)
        }

# --- Example Usage ---

def create_dummy_geospatial_data(base_path: str):
    """Creates dummy DSM, DTM, and multispectral ortho for testing."""
    import os
    os.makedirs(base_path, exist_ok=True)
    
    shape = (500, 500)
    transform = from_origin(300000, 5000000, 0.1, 0.1) # 10cm GSD
    crs = "EPSG:32632"

    # DTM (sloped terrain)
    dtm = np.fromfunction(lambda r, c: 100 + r * 0.01 + c * 0.005, shape, dtype=np.float32)
    dtm_path = os.path.join(base_path, 'dummy_dtm.tif')
    with rasterio.open(dtm_path, 'w', driver='GTiff', height=shape[0], width=shape[1], count=1, dtype='float32', crs=crs, transform=transform) as dst:
        dst.write(dtm, 1)

    # DSM (add some "plants")
    dsm = dtm.copy()
    for _ in range(50): # 50 plants
        r, c = np.random.randint(50, 450), np.random.randint(50, 450)
        radius = np.random.randint(5, 15)
        height = np.random.uniform(0.5, 2.5)
        rr, cc = np.ogrid[-radius:radius+1, -radius:radius+1]
        mask = rr**2 + cc**2 <= radius**2
        dsm[r-radius:r+radius+1, c-radius:c+radius+1][mask] += height * np.cos(np.sqrt(rr**2 + cc**2)[mask] * np.pi / (2*radius))

    dsm_path = os.path.join(base_path, 'dummy_dsm.tif')
    with rasterio.open(dsm_path, 'w', driver='GTiff', height=shape[0], width=shape[1], count=1, dtype='float32', crs=crs, transform=transform) as dst:
        dst.write(dsm, 1)

    # Multispectral Ortho (5 bands: R, G, B, Red-Edge, NIR)
    ortho_path = os.path.join(base_path, 'dummy_ortho.tif')
    with rasterio.open(ortho_path, 'w', driver='GTiff', height=shape[0], width=shape[1], count=5, dtype='uint16', crs=crs, transform=transform) as dst:
        # Simulate higher NIR reflectance for plants
        plant_mask = (dsm > dtm + 0.1)
        for i in range(1, 6):
            band = np.full(shape, 1000, dtype=np.uint16)
            if i == 5: # NIR band
                band[plant_mask] = 4000
            if i == 1: # Red band
                band[plant_mask] = 500
            dst.write(band, i)
            
    band_map = {'red': 1, 'green': 2, 'blue': 3, 'red_edge': 4, 'nir': 5}
    return dsm_path, dtm_path, ortho_path, band_map


if __name__ == '__main__':
    logging.info("--- Running Vegetation Analysis Demo ---")
    
    DATA_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'dummy_veg_analysis_data')
    dsm_p, dtm_p, ortho_p, b_map = create_dummy_geospatial_data(DATA_PATH)
    
    output_shp = os.path.join(DATA_PATH, 'detected_plants.shp')

    # Initialize and run the analyzer
    analyzer = VegetationAnalyzer(
        dsm_path=dsm_p,
        dtm_path=dtm_p,
        ortho_path=ortho_p,
        band_map=b_map
    )
    
    analysis_summary = analyzer.run_full_analysis(output_plants_shapefile=output_shp)

    print("\n--- Analysis Summary ---")
    print(f"Canopy Cover: {analysis_summary['canopy_cover']:.2f}%")
    print(f"Detected Rows: {analysis_summary['row_info']}")
    print(f"Total Plants Detected: {analysis_summary['plant_count']}")
    print("------------------------")

    logging.info("--- Demo Complete ---")
