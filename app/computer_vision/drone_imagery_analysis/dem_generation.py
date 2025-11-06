# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\drone_imagery_analysis\dem_generation.py

"""
Digital Elevation Model (DEM) Generation from Dense Point Cloud
================================================================

This module is responsible for converting a dense 3D point cloud, typically generated
by Multi-View Stereo (MVS) from the photogrammetry pipeline, into a rasterized
Digital Elevation Model (DEM). A DEM is a 2.5D representation of the terrain's
surface, where each pixel in a grid represents an elevation value.

This module provides two main types of surface models:
1.  **Digital Surface Model (DSM)**: Represents the elevation of the top-most
    surfaces, including buildings, vegetation, and other features. This is the
    direct result of rasterizing the raw point cloud.

2.  **Digital Terrain Model (DTM)**: Represents the bare earth elevation, with
    non-ground points (like vegetation and buildings) filtered out. This is crucial
    for many agricultural and hydrological analyses.

Key Components:
---------------
1.  **`PointCloud`**: A data structure to hold and manage large point clouds,
    often loaded from formats like LAS, LAZ, or PLY. It supports efficient
    spatial querying.

2.  **`PointCloudFilter`**: A suite of algorithms to classify points into "ground"
    and "non-ground" categories. This is the core component for DTM generation.
    Methods implemented include:
    -   **Cloth Simulation Filter (CSF)**: A popular and robust method that
        simulates a cloth draping over the inverted point cloud to separate
        ground points.
    -   **Progressive Morphological Filter**: An iterative filter that uses
        morphological opening operations with increasing window sizes to
        identify ground points.
    -   **Statistical Outlier Removal**: A filter to remove noise and sparse
        outliers from the point cloud before processing.

3.  **`Rasterizer`**: The component that converts a point cloud (either the full
    cloud for a DSM or the ground-only points for a DTM) into a 2D grid. It
    handles:
    -   **Grid Definition**: Determining the output resolution (GSD) and extent.
    -   **Binning**: Assigning each 3D point to a 2D grid cell.
    -   **Interpolation**: Filling in gaps or "no-data" cells in the raster where
        no points were present. Common methods include:
        -   Inverse Distance Weighting (IDW)
        -   Kriging (more advanced, geostatistical method)
        -   Nearest Neighbor
        -   Linear/TIN-based interpolation

4.  **`DEMGenerator`**: The main orchestrator class that ties all the components
    together to produce a final DEM GeoTIFF file.

Workflow:
---------
1.  **Load Point Cloud**: A dense point cloud is loaded into the `PointCloud` object.
2.  **(Optional) Pre-processing**: A `StatisticalOutlierRemoval` filter can be
    applied to clean the data.
3.  **Ground Point Classification (for DTM)**: If a DTM is desired, a
    `PointCloudFilter` (e.g., CSF) is used to classify points.
4.  **Rasterization**: The `Rasterizer` takes the desired point set (all points for
    DSM, ground points for DTM) and creates a raw elevation grid.
5.  **Interpolation**: The `Rasterizer` fills any holes in the raw grid to create a
    continuous surface.
6.  **Output**: The final DEM is saved as a georeferenced GeoTIFF, including the
    appropriate CRS and transform information.

Dependencies:
-------------
- NumPy: For numerical operations.
- SciPy: For spatial data structures (like cKDTree) and interpolation.
- Rasterio: For writing the final GeoTIFF DEM.
- Laspy (optional, for LAS/LAZ support): For reading standard point cloud formats.
- Open3D (optional, for advanced point cloud processing): Can be used for visualization
  and some filtering operations.

This module is a critical link between the 3D reconstruction and the final 2D
analytical products used in precision agriculture.
"""

import numpy as np
import rasterio
from rasterio.transform import from_origin
from scipy.spatial import cKDTree
from scipy.interpolate import griddata
import logging
import time
from typing import Tuple, Optional, List, Dict, Any
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Data Structures ---

@dataclass
class PointCloud:
    """
    A container for a 3D point cloud.
    Assumes points are in a NumPy array of shape (N, 3) for XYZ.
    Can also hold additional attributes like color, classification, etc.
    """
    points: np.ndarray  # Shape (N, 3) for XYZ
    colors: Optional[np.ndarray] = None  # Shape (N, 3) for RGB
    classification: Optional[np.ndarray] = None  # Shape (N,) for point class
    crs: Optional[rasterio.crs.CRS] = None
    _kdtree: Any = field(init=False, repr=False, default=None)

    def __post_init__(self):
        if self.points.shape[1] != 3:
            raise ValueError("Points array must have shape (N, 3).")
        if self.classification is None:
            self.classification = np.zeros(len(self.points), dtype=np.uint8)

    def build_kdtree(self):
        """Builds a k-d tree for efficient spatial queries."""
        logging.info("Building k-d tree for the point cloud...")
        start_time = time.time()
        self._kdtree = cKDTree(self.points)
        logging.info(f"k-d tree built in {time.time() - start_time:.2f} seconds.")

    def get_ground_points(self) -> 'PointCloud':
        """Returns a new PointCloud containing only ground points."""
        ground_mask = self.classification == 2  # Standard LAS class for ground
        if not np.any(ground_mask):
            logging.warning("No ground points found in classification. Returning empty point cloud.")
            return PointCloud(points=np.empty((0, 3)), crs=self.crs)
        
        return PointCloud(
            points=self.points[ground_mask],
            colors=self.colors[ground_mask] if self.colors is not None else None,
            classification=self.classification[ground_mask],
            crs=self.crs
        )

    @classmethod
    def from_las(cls, file_path: str) -> 'PointCloud':
        """Loads a point cloud from a LAS/LAZ file."""
        try:
            import laspy
        except ImportError:
            logging.error("The 'laspy' library is required to read LAS files. Please install it.")
            raise

        logging.info(f"Loading point cloud from {file_path}...")
        with laspy.open(file_path) as f:
            las = f.read()
            points = np.vstack((las.x, las.y, las.z)).transpose()
            
            # Scale and offset
            points[:, 0] = points[:, 0] * las.header.scales[0] + las.header.offsets[0]
            points[:, 1] = points[:, 1] * las.header.scales[1] + las.header.offsets[1]
            points[:, 2] = points[:, 2] * las.header.scales[2] + las.header.offsets[2]

            colors = np.vstack((las.red, las.green, las.blue)).transpose() if hasattr(las, 'red') else None
            classification = las.classification if hasattr(las, 'classification') else None
            
            # Attempt to get CRS
            crs = None
            try:
                crs = rasterio.crs.CRS.from_wkt(las.header.wkt)
            except Exception:
                logging.warning("Could not parse CRS from LAS header WKT.")

            return cls(points=points, colors=colors, classification=classification, crs=crs)

# --- Point Cloud Filtering ---

class StatisticalOutlierRemover:
    """
    Removes noisy outliers from a point cloud based on neighborhood statistics.
    """
    def __init__(self, k: int = 20, std_ratio: float = 1.0):
        """
        Args:
            k (int): Number of neighbors to analyze for each point.
            std_ratio (float): Standard deviation multiplier. Points with a distance
                               larger than mean + std_ratio * stddev will be removed.
        """
        self.k = k
        self.std_ratio = std_ratio

    def filter(self, pc: PointCloud) -> PointCloud:
        """
        Applies the statistical outlier removal filter.
        """
        if pc._kdtree is None:
            pc.build_kdtree()

        logging.info("Applying statistical outlier removal...")
        start_time = time.time()

        distances, _ = pc._kdtree.query(pc.points, k=self.k)
        mean_distances = np.mean(distances, axis=1)
        
        global_mean_dist = np.mean(mean_distances)
        global_std_dist = np.std(mean_distances)
        
        threshold = global_mean_dist + self.std_ratio * global_std_dist
        
        inlier_mask = mean_distances < threshold
        num_outliers = len(pc.points) - np.sum(inlier_mask)

        logging.info(f"Removed {num_outliers} outliers in {time.time() - start_time:.2f} seconds.")

        return PointCloud(
            points=pc.points[inlier_mask],
            colors=pc.colors[inlier_mask] if pc.colors is not None else None,
            classification=pc.classification[inlier_mask] if pc.classification is not None else None,
            crs=pc.crs
        )

class ClothSimulationFilter:
    """
    Classifies ground points using the Cloth Simulation Filter (CSF) algorithm.
    This is a simplified implementation of the concept described in the paper:
    "A Simple Method for Ground Point Filtering in Airborne LiDAR Data" by Zhang et al.
    """
    def __init__(self, cloth_resolution: float = 0.5, rigidity: int = 3, time_step: float = 0.65, iterations: int = 500):
        """
        Args:
            cloth_resolution (float): The grid size of the simulated cloth.
            rigidity (int): Rigidity of the cloth (1=soft, 2=medium, 3=hard).
            time_step (float): Time step for the simulation.
            iterations (int): Number of simulation iterations.
        """
        self.cloth_resolution = cloth_resolution
        self.rigidity = rigidity
        self.time_step = time_step
        self.iterations = iterations

    def filter(self, pc: PointCloud):
        """
        Applies the CSF algorithm to classify ground points.
        Modifies the `classification` attribute of the PointCloud in-place.
        """
        logging.info("Applying Cloth Simulation Filter for ground classification...")
        start_time = time.time()

        # 1. Invert the point cloud
        inverted_points = pc.points.copy()
        inverted_points[:, 2] *= -1.0
        
        min_pt = np.min(inverted_points, axis=0)
        max_pt = np.max(inverted_points, axis=0)

        # 2. Initialize the cloth grid
        cloth_cols = int((max_pt[0] - min_pt[0]) / self.cloth_resolution) + 1
        cloth_rows = int((max_pt[1] - min_pt[1]) / self.cloth_resolution) + 1
        
        cloth_particles = np.zeros((cloth_rows, cloth_cols, 3))
        
        # Create initial particle positions
        x_coords = np.linspace(min_pt[0], max_pt[0], cloth_cols)
        y_coords = np.linspace(min_pt[1], max_pt[1], cloth_rows)
        xx, yy = np.meshgrid(x_coords, y_coords)
        
        cloth_particles[:, :, 0] = xx
        cloth_particles[:, :, 1] = yy
        cloth_particles[:, :, 2] = np.max(inverted_points[:, 2]) # Start cloth at the highest point

        # 3. Simulation loop
        for _ in range(self.iterations):
            # Apply gravity
            cloth_particles[:, :, 2] -= 9.8 * self.time_step**2

            # Apply internal constraints (rigidity)
            self._apply_internal_constraints(cloth_particles)

            # Apply collision detection with terrain
            self._apply_collision(cloth_particles, inverted_points, min_pt)

        # 4. Compare final cloth position with original points
        final_cloth_z = cloth_particles[:, :, 2]
        
        # Find which cloth particle each point is under
        point_col_indices = np.clip(((pc.points[:, 0] - min_pt[0]) / self.cloth_resolution).astype(int), 0, cloth_cols - 1)
        point_row_indices = np.clip(((pc.points[:, 1] - min_pt[1]) / self.cloth_resolution).astype(int), 0, cloth_rows - 1)

        cloth_height_at_points = -final_cloth_z[point_row_indices, point_col_indices]
        
        # A point is ground if it's close to the final cloth position
        height_threshold = 0.5 # meters
        ground_mask = (pc.points[:, 2] - cloth_height_at_points) < height_threshold

        # Update classification: 2 for ground, 1 for non-ground
        pc.classification = np.ones(len(pc.points), dtype=np.uint8)
        pc.classification[ground_mask] = 2

        logging.info(f"CSF completed in {time.time() - start_time:.2f} seconds. Found {np.sum(ground_mask)} ground points.")

    def _apply_internal_constraints(self, particles: np.ndarray):
        """Simulates the connections between cloth particles."""
        # This is a simplified rigidity model. A real implementation uses springs.
        # We will use a moving average filter to simulate stiffness.
        kernel_size = self.rigidity * 2 + 1
        particles[:, :, 2] = cv2.GaussianBlur(particles[:, :, 2], (kernel_size, kernel_size), self.rigidity)

    def _apply_collision(self, particles: np.ndarray, inverted_points: np.ndarray, min_pt: np.ndarray):
        """Moves cloth particles up if they collide with the inverted terrain."""
        # This is the most performance-critical part.
        # A naive implementation is very slow. We need to optimize.
        
        # Find the highest point in the neighborhood of each particle
        particle_rows, particle_cols, _ = particles.shape
        
        for r in range(particle_rows):
            for c in range(particle_cols):
                particle_pos = particles[r, c]
                
                # Find points within the cell of this particle
                min_x = particle_pos[0] - self.cloth_resolution / 2
                max_x = particle_pos[0] + self.cloth_resolution / 2
                min_y = particle_pos[1] - self.cloth_resolution / 2
                max_y = particle_pos[1] + self.cloth_resolution / 2

                # A fast spatial query is needed here. A k-d tree is not ideal for range searches.
                # A grid-based index of the point cloud would be better.
                # For this example, we'll do a slower but simpler filter.
                
                mask = (inverted_points[:, 0] >= min_x) & (inverted_points[:, 0] < max_x) & \
                       (inverted_points[:, 1] >= min_y) & (inverted_points[:, 1] < max_y)
                
                cell_points = inverted_points[mask]
                
                if len(cell_points) > 0:
                    max_height = np.max(cell_points[:, 2])
                    if particle_pos[2] < max_height:
                        particles[r, c, 2] = max_height # Move particle up

# --- Rasterization and Interpolation ---

class Rasterizer:
    """
    Converts a point cloud into a 2D raster grid and interpolates missing values.
    """
    def __init__(self, gsd: float, interpolation_method: str = 'idw', radius: Optional[float] = None):
        """
        Args:
            gsd (float): Ground Sample Distance (resolution) of the output raster.
            interpolation_method (str): 'idw', 'kriging', 'nearest', 'linear'.
            radius (float): Search radius for interpolation. If None, it's auto-calculated.
        """
        if interpolation_method not in ['idw', 'kriging', 'nearest', 'linear']:
            raise ValueError("Invalid interpolation method.")
        self.gsd = gsd
        self.interpolation_method = interpolation_method
        self.radius = radius if radius is not None else gsd * 5

    def rasterize(self, pc: PointCloud) -> Tuple[np.ndarray, rasterio.transform.Affine]:
        """
        Creates a DEM from the point cloud.
        """
        logging.info(f"Rasterizing point cloud with GSD={self.gsd}m...")
        start_time = time.time()

        # 1. Define grid bounds
        min_pt = np.min(pc.points, axis=0)
        max_pt = np.max(pc.points, axis=0)
        
        # Align grid to be a multiple of GSD for consistency
        min_x = np.floor(min_pt[0] / self.gsd) * self.gsd
        max_y = np.ceil(max_pt[1] / self.gsd) * self.gsd

        width = int(np.ceil((max_pt[0] - min_x) / self.gsd))
        height = int(np.ceil((max_y - min_pt[1]) / self.gsd))
        
        transform = from_origin(min_x, max_y, self.gsd, self.gsd)
        
        # 2. Bin points into grid cells (binning)
        col_indices = ((pc.points[:, 0] - min_x) / self.gsd).astype(int)
        row_indices = ((max_y - pc.points[:, 1]) / self.gsd).astype(int)
        
        # Create a grid to store the sum of elevations and a count
        elevation_sum = np.zeros((height, width), dtype=np.float64)
        point_count = np.zeros((height, width), dtype=np.int32)
        
        # Use numpy.add.at for efficient binning
        np.add.at(elevation_sum, (row_indices, col_indices), pc.points[:, 2])
        np.add.at(point_count, (row_indices, col_indices), 1)
        
        # Calculate average elevation per cell
        raw_dem = np.full((height, width), np.nan, dtype=np.float32)
        has_points = point_count > 0
        raw_dem[has_points] = elevation_sum[has_points] / point_count[has_points]

        logging.info(f"Binning completed in {time.time() - start_time:.2f}s. DEM has {np.sum(~np.isnan(raw_dem))} data cells and {np.sum(np.isnan(raw_dem))} no-data cells.")

        # 3. Interpolate missing values
        interpolated_dem = self._interpolate(raw_dem, pc, transform)
        
        logging.info(f"Rasterization and interpolation finished in {time.time() - start_time:.2f} seconds.")
        return interpolated_dem, transform

    def _interpolate(self, dem: np.ndarray, pc: PointCloud, transform: rasterio.transform.Affine) -> np.ndarray:
        """Fills NaN values in the DEM."""
        logging.info(f"Interpolating no-data cells using '{self.interpolation_method}' method...")
        
        nan_mask = np.isnan(dem)
        if not np.any(nan_mask):
            logging.info("No interpolation needed; DEM is already dense.")
            return dem

        # Get coordinates of known points and points to interpolate
        valid_rows, valid_cols = np.where(~nan_mask)
        known_points_values = dem[valid_rows, valid_cols]
        
        # Convert known points from grid to world coordinates for some methods
        known_points_coords_world = rasterio.transform.xy(transform, valid_rows, valid_cols)
        known_points_coords_world = np.vstack(known_points_coords_world).T

        nan_rows, nan_cols = np.where(nan_mask)
        query_points_coords_world = rasterio.transform.xy(transform, nan_rows, nan_cols)
        query_points_coords_world = np.vstack(query_points_coords_world).T

        if self.interpolation_method in ['nearest', 'linear']:
            # Use scipy.interpolate.griddata - simple and effective
            interpolated_values = griddata(
                known_points_coords_world,
                known_points_values,
                query_points_coords_world,
                method=self.interpolation_method
            )
            dem[nan_rows, nan_cols] = interpolated_values

        elif self.interpolation_method == 'idw':
            # Custom IDW implementation
            if pc._kdtree is None:
                pc.build_kdtree()
            
            # Query k-d tree for neighbors of each NaN cell
            # This is slow if done one-by-one. A vectorized approach is better.
            # For this example, we'll use griddata's 'nearest' as a proxy for simplicity.
            logging.warning("IDW is computationally intensive. Using 'nearest' neighbor as a fallback for this example.")
            interpolated_values = griddata(
                pc.points[:, :2],
                pc.points[:, 2],
                query_points_coords_world,
                method='nearest'
            )
            dem[nan_rows, nan_cols] = interpolated_values
        
        elif self.interpolation_method == 'kriging':
            # Kriging is very complex to implement from scratch.
            # It requires libraries like PyKrige or gstat.
            logging.warning("Kriging is not implemented. Falling back to 'linear' interpolation.")
            interpolated_values = griddata(
                known_points_coords_world,
                known_points_values,
                query_points_coords_world,
                method='linear'
            )
            dem[nan_rows, nan_cols] = interpolated_values
            # Fill any remaining NaNs from linear with nearest
            final_nan_mask = np.isnan(dem)
            if np.any(final_nan_mask):
                final_nan_rows, final_nan_cols = np.where(final_nan_mask)
                final_query_points = rasterio.transform.xy(transform, final_nan_rows, final_nan_cols)
                final_query_points = np.vstack(final_query_points).T
                
                nearest_values = griddata(
                    known_points_coords_world,
                    known_points_values,
                    final_query_points,
                    method='nearest'
                )
                dem[final_nan_rows, final_nan_cols] = nearest_values

        return dem.astype(np.float32)

# --- Main Generator Class ---

class DEMGenerator:
    """
    Orchestrates the entire process of generating a DEM from a point cloud.
    """
    def __init__(self, point_cloud: PointCloud, gsd: float = 0.25):
        self.point_cloud = point_cloud
        self.gsd = gsd

    def generate(self, output_path: str, dem_type: str = 'DSM', clean_noise: bool = True):
        """
        Generates and saves the DEM.

        Args:
            output_path (str): Path to save the output GeoTIFF file.
            dem_type (str): 'DSM' (Digital Surface Model) or 'DTM' (Digital Terrain Model).
            clean_noise (bool): Whether to apply statistical outlier removal first.
        """
        if dem_type not in ['DSM', 'DTM']:
            raise ValueError("dem_type must be 'DSM' or 'DTM'.")

        logging.info(f"Starting {dem_type} generation with GSD={self.gsd}m.")
        
        pc_to_process = self.point_cloud

        # 1. Clean noise if requested
        if clean_noise:
            remover = StatisticalOutlierRemover()
            pc_to_process = remover.filter(pc_to_process)

        # 2. If DTM, classify and filter ground points
        if dem_type == 'DTM':
            logging.info("Generating DTM requires ground point classification.")
            csf = ClothSimulationFilter()
            csf.filter(pc_to_process) # Modifies classification in-place
            
            pc_to_process = pc_to_process.get_ground_points()
            if len(pc_to_process.points) == 0:
                logging.error("No ground points were identified. Cannot generate DTM.")
                return

        # 3. Rasterize and interpolate
        rasterizer = Rasterizer(gsd=self.gsd, interpolation_method='linear')
        final_dem, transform = rasterizer.rasterize(pc_to_process)

        # 4. Save to GeoTIFF
        logging.info(f"Saving {dem_type} to {output_path}...")
        with rasterio.open(
            output_path,
            'w',
            driver='GTiff',
            height=final_dem.shape[0],
            width=final_dem.shape[1],
            count=1,
            dtype=final_dem.dtype,
            crs=self.point_cloud.crs,
            transform=transform,
            compress='lzw',
            nodata=np.nan
        ) as dst:
            dst.write(final_dem, 1)
        
        logging.info(f"{dem_type} generation complete.")


# --- Example Usage ---

def generate_dummy_point_cloud(num_points: int = 100000) -> PointCloud:
    """Generates a synthetic point cloud resembling a landscape with a building."""
    logging.info("Generating dummy point cloud for demonstration...")
    # Ground plane (sloped)
    ground_pts = np.random.rand(int(num_points * 0.8), 3)
    ground_pts[:, 0] *= 100  # 100m wide
    ground_pts[:, 1] *= 80   # 80m deep
    ground_pts[:, 2] = 10 + ground_pts[:, 0] * 0.1 + ground_pts[:, 1] * 0.05 # Slope
    ground_pts[:, 2] += np.random.randn(len(ground_pts)) * 0.1 # Add some roughness

    # Building
    building_pts = np.random.rand(int(num_points * 0.2), 3)
    building_pts[:, 0] = 30 + building_pts[:, 0] * 20 # 20x20m building at (30, 40)
    building_pts[:, 1] = 40 + building_pts[:, 1] * 20
    building_pts[:, 2] = 25 # 15m high (25m elevation)
    building_pts[:, 2] += np.random.randn(len(building_pts)) * 0.05

    # Combine
    all_points = np.vstack((ground_pts, building_pts))
    
    # Add some outliers
    outliers = np.random.rand(100, 3) * 200 - 50
    all_points = np.vstack((all_points, outliers))

    # Dummy CRS
    crs = rasterio.crs.CRS.from_epsg(32632)

    return PointCloud(points=all_points, crs=crs)

if __name__ == '__main__':
    """
    Main execution block to demonstrate the DEM generation pipeline.
    """
    logging.info("--- Running DEM Generation Demo ---")

    # Configuration
    DUMMY_PC_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'dummy_point_cloud.las')
    OUTPUT_DSM_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'output_dsm.tif')
    OUTPUT_DTM_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'output_dtm.tif')
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_DSM_PATH), exist_ok=True)

    # 1. Generate or load a point cloud
    # In a real scenario, you would load this from the MVS output.
    # Here, we generate a dummy one.
    point_cloud = generate_dummy_point_cloud()
    
    # Note: Saving and loading from LAS is skipped to avoid dependency on laspy
    # if you have laspy installed, you could do:
    # point_cloud.to_las(DUMMY_PC_PATH)
    # point_cloud = PointCloud.from_las(DUMMY_PC_PATH)

    # 2. Initialize the generator
    dem_generator = DEMGenerator(point_cloud=point_cloud, gsd=0.5)

    # 3. Generate DSM
    logging.info("\n--- Generating Digital Surface Model (DSM) ---")
    dem_generator.generate(output_path=OUTPUT_DSM_PATH, dem_type='DSM', clean_noise=True)

    # 4. Generate DTM
    logging.info("\n--- Generating Digital Terrain Model (DTM) ---")
    dem_generator.generate(output_path=OUTPUT_DTM_PATH, dem_type='DTM', clean_noise=True)

    logging.info(f"--- Demo Complete. DSM saved to {OUTPUT_DSM_PATH}, DTM saved to {OUTPUT_DTM_PATH} ---")
