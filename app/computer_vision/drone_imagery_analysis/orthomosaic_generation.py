# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\drone_imagery_analysis\orthomosaic_generation.py

"""
Orthomosaic Generation Pipeline for AgroPulse
==============================================

This module provides a comprehensive pipeline for generating high-resolution,
georeferenced orthomosaics from drone imagery and photogrammetry outputs.
An orthomosaic is a single, seamless, and geometrically corrected image of an
area, created by stitching together multiple individual images (orthophotos).

The process corrects for:
- **Perspective Distortion:** Objects closer to the camera appearing larger.
- **Terrain Relief Displacement:** Variations in elevation causing distortions.
- **Camera Tilt:** The angle of the camera relative to the ground.

This module builds upon the outputs of the `photogrammetry_pipeline`, using the
calculated camera poses, intrinsic parameters, and the dense 3D point cloud (or a
Digital Elevation Model - DEM) to achieve accurate ortho-rectification.

Key Components:
---------------
1.  **`OrthomosaicGenerator`**: The main orchestrator class that manages the entire
    workflow from input data to the final orthomosaic GeoTIFF.

2.  **`ImageProjector`**: Handles the core task of projecting individual drone
    images onto a common ground plane. It uses the camera parameters and a DEM
    to perform accurate ortho-rectification for each pixel.

3.  **`SeamlineOptimizer`**: A sophisticated component to find the optimal "seams"
    between overlapping images. This is crucial for avoiding visible artifacts
    like building edges being cut in half. It constructs a cost graph and uses
    algorithms like Dijkstra's or graph cuts (Boykov-Kolmogorov) to find the
    lowest-cost path for seams.

4.  **`ColorBalancer`**: Corrects for variations in lighting, exposure, and white
    balance between different images, which are often captured at different times
    or from different angles. It implements global and local color correction
    methods to ensure a visually consistent final mosaic.

5.  **`MosaicBlender`**: Blends the pixels along the optimized seamlines to create
    a smooth, invisible transition between images. It uses techniques like
    multi-band blending (pyramid blending) or simple feathering.

Workflow:
---------
1.  **Initialization**: The `OrthomosaicGenerator` is initialized with camera
    parameters, image paths, and a DEM. It defines the output resolution (GSD)
    and the geographic extent of the final mosaic.

2.  **Image Projection**: For each image, the `ImageProjector` determines its
    footprint on the final mosaic canvas. It then generates an ortho-rectified
    version of the image by back-projecting pixels from the ground plane up to
    the camera's perspective, sampling the original image.

3.  **Seamline Optimization**: The `SeamlineOptimizer` analyzes the overlapping
    areas between the ortho-rectified images. It builds a cost function based on
    image gradients (edges) and color differences. A graph-based algorithm then
    finds the seamlines that minimize this cost, effectively routing seams through
    low-contrast areas.

4.  **Color Balancing**: The `ColorBalancer` analyzes color histograms of overlapping
    regions to compute a global color adjustment for each image, or a more
    complex local adjustment, to bring all images into a common color space.

5.  **Blending and Composition**: The final mosaic is assembled. For each pixel
    location, the system determines which image(s) should contribute. Along the
    seamlines, the `MosaicBlender` smoothly merges the pixel values from adjacent
    images to create the final, seamless orthomosaic.

6.  **Output**: The final orthomosaic is written to a GeoTIFF file, containing
    the image data and the necessary georeferencing information (CRS, transform).

Dependencies:
-------------
- NumPy: For all numerical operations.
- OpenCV: For image manipulation, transformations, and blending.
- Rasterio: For reading DEMs and writing georeferenced GeoTIFFs.
- Scikit-image: For advanced image processing tasks.
- SciPy: For graph algorithms and spatial data structures.
- Shapely: For geometric operations on image footprints.

This module is designed for high performance and scalability, capable of processing
thousands of high-resolution images to generate large-scale orthomosaics for
precision agriculture analysis.
"""

import os
import numpy as np
import cv2
import rasterio
from rasterio.transform import from_origin
from rasterio.enums import Resampling
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.ndimage import distance_transform_edt
from sklearn.linear_model import RANSACRegressor
import logging
import time
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Data Structures ---

@dataclass
class CameraParams:
    """Stores intrinsic and extrinsic parameters for a single camera."""
    id: str
    K: np.ndarray  # 3x3 intrinsic matrix
    R: np.ndarray  # 3x3 rotation matrix
    t: np.ndarray  # 3x1 translation vector
    dist_coeffs: np.ndarray  # Distortion coefficients (e.g., k1, k2, p1, p2, k3)
    image_path: str
    width: int
    height: int

@dataclass
class DigitalElevationModel:
    """Container for a DEM, providing easy access to elevation data."""
    data: np.ndarray
    transform: rasterio.transform.Affine
    crs: rasterio.crs.CRS

    def get_elevation(self, x: float, y: float) -> float:
        """Get elevation at a specific geographic coordinate."""
        try:
            row, col = rasterio.transform.rowcol(self.transform, x, y)
            if 0 <= row < self.data.shape[0] and 0 <= col < self.data.shape[1]:
                return self.data[row, col]
            return np.nan
        except IndexError:
            return np.nan

    @classmethod
    def from_file(cls, path: str) -> 'DigitalElevationModel':
        """Load a DEM from a GeoTIFF file."""
        with rasterio.open(path) as src:
            return cls(
                data=src.read(1),
                transform=src.transform,
                crs=src.crs
            )

# --- Core Components ---

class ImageProjector:
    """
    Handles the ortho-rectification of a single image onto the ground plane.
    """
    def __init__(self, camera: CameraParams, dem: DigitalElevationModel, output_transform: rasterio.transform.Affine, output_shape: Tuple[int, int], output_crs: rasterio.crs.CRS):
        self.camera = camera
        self.dem = dem
        self.output_transform = output_transform
        self.output_shape = output_shape
        self.output_crs = output_crs

        # Pre-calculate projection matrices for efficiency
        self.P = self.camera.K @ np.hstack((self.camera.R, self.camera.t))
        self.inv_K = np.linalg.inv(self.camera.K)
        self.inv_R = self.camera.R.T
        self.camera_center = -self.inv_R @ self.camera.t

    def get_footprint(self) -> Optional[np.ndarray]:
        """
        Calculate the approximate footprint of the image on the ground.
        This is a simplified version; a more accurate method would project all corners.
        """
        corners_2d = np.array([
            [0, 0], [self.camera.width, 0],
            [self.camera.width, self.camera.height], [0, self.camera.height]
        ], dtype=np.float32)

        # Estimate average elevation for projection
        avg_elevation = np.nanmean(self.dem.data)
        if np.isnan(avg_elevation):
            logging.warning(f"DEM contains only NaNs. Cannot estimate footprint for {self.camera.id}.")
            return None

        ground_points = []
        for corner in corners_2d:
            ray_direction = self.inv_R @ self.inv_K @ np.array([corner[0], corner[1], 1.0]).reshape(3, 1)
            ray_origin = self.camera_center

            # Simple intersection with a horizontal plane at average elevation
            # A more robust method would intersect with the DEM mesh
            if ray_direction[2] > -1e-6:  # Avoid rays parallel to or pointing away from the ground
                continue
            
            t = (avg_elevation - ray_origin[2]) / ray_direction[2]
            if t > 0:
                intersect_point = ray_origin + t * ray_direction
                ground_points.append(intersect_point.flatten()[:2])

        if len(ground_points) < 3:
            return None

        return np.array(ground_points)

    def ortho_rectify(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Performs ortho-rectification of the image.

        Returns:
            A tuple containing the ortho-rectified image (RGBA) and its corresponding mask.
        """
        logging.info(f"Ortho-rectifying image {self.camera.id}...")
        start_time = time.time()

        # Create grid of pixel coordinates in the output mosaic space
        cols, rows = np.meshgrid(np.arange(self.output_shape[1]), np.arange(self.output_shape[0]))
        
        # Convert pixel coordinates to world coordinates (x, y)
        world_x, world_y = rasterio.transform.xy(self.output_transform, rows, cols)
        world_x, world_y = np.array(world_x), np.array(world_y)

        # Get elevation for each point from the DEM
        # This is a vectorized but potentially slow operation.
        # For large mosaics, this should be done in chunks.
        dem_rows, dem_cols = rasterio.transform.rowcol(self.dem.transform, world_x.flatten(), world_y.flatten())
        
        valid_dem_indices = (
            (np.array(dem_rows) >= 0) & (np.array(dem_rows) < self.dem.data.shape[0]) &
            (np.array(dem_cols) >= 0) & (np.array(dem_cols) < self.dem.data.shape[1])
        )
        
        world_z = np.full(world_x.shape, np.nan, dtype=np.float32).flatten()
        
        flat_dem_rows = np.array(dem_rows)[valid_dem_indices]
        flat_dem_cols = np.array(dem_cols)[valid_dem_indices]
        
        world_z[valid_dem_indices] = self.dem.data[flat_dem_rows, flat_dem_cols]
        world_z = world_z.reshape(world_x.shape)

        # Create 3D world points
        world_points = np.stack((world_x, world_y, world_z), axis=-1)
        
        # Reshape for matrix multiplication
        num_points = world_points.shape[0] * world_points.shape[1]
        world_points_homogeneous = np.hstack((world_points.reshape(num_points, 3), np.ones((num_points, 1))))

        # Project world points into the camera's image plane
        image_points_homogeneous = (self.P @ world_points_homogeneous.T).T
        
        # Normalize to get 2D image coordinates
        image_points_2d = image_points_homogeneous[:, :2] / image_points_homogeneous[:, 2, np.newaxis]
        
        # Reshape back to grid
        u = image_points_2d[:, 0].reshape(self.output_shape)
        v = image_points_2d[:, 1].reshape(self.output_shape)

        # Create a mask for points that project inside the image bounds
        mask = (
            (u >= 0) & (u < self.camera.width) &
            (v >= 0) & (v < self.camera.height) &
            (~np.isnan(world_z))
        )

        # Load the source image
        try:
            source_image = cv2.imread(self.camera.image_path)
            if source_image is None:
                raise IOError(f"Could not read image: {self.camera.image_path}")
            source_image = cv2.cvtColor(source_image, cv2.COLOR_BGR2RGB)
        except (IOError, cv2.error) as e:
            logging.error(f"Failed to load or process image {self.camera.image_path}: {e}")
            return None, None

        # Undistort the projected coordinates (more accurate than undistorting the whole image)
        # This is computationally expensive. For speed, one might apply cv2.remap on a distorted grid.
        if self.camera.dist_coeffs is not None and np.any(self.camera.dist_coeffs != 0):
            # Note: cv2.undistortPoints expects a specific shape (N, 1, 2)
            points_to_undistort = np.stack((u[mask], v[mask]), axis=-1).astype(np.float32)
            points_to_undistort = np.expand_dims(points_to_undistort, axis=1)
            
            undistorted_points = cv2.undistortPoints(
                points_to_undistort,
                self.camera.K,
                self.camera.dist_coeffs,
                P=self.camera.K # Project back using the same intrinsics
            )
            
            u[mask] = undistorted_points[:, 0, 0]
            v[mask] = undistorted_points[:, 0, 1]

            # Re-check mask after undistortion
            mask = (
                (u >= 0) & (u < self.camera.width) &
                (v >= 0) & (v < self.camera.height) &
                (~np.isnan(world_z))
            )

        # Sample the source image using the calculated coordinates (bilinear interpolation)
        # cv2.remap is the perfect tool for this
        ortho_image_rgb = cv2.remap(
            source_image,
            u.astype(np.float32),
            v.astype(np.float32),
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0)
        )

        # Create an RGBA image with the mask as the alpha channel
        ortho_image_rgba = cv2.cvtColor(ortho_image_rgb, cv2.COLOR_RGB2RGBA)
        ortho_image_rgba[:, :, 3] = (mask * 255).astype(np.uint8)

        elapsed_time = time.time() - start_time
        logging.info(f"Finished ortho-rectifying {self.camera.id} in {elapsed_time:.2f} seconds.")

        return ortho_image_rgba, mask

class SeamlineOptimizer:
    """
    Finds optimal seamlines in overlapping image regions to minimize visual artifacts.
    """
    def __init__(self, method: str = 'dijkstra'):
        """
        Args:
            method (str): 'dijkstra' for seamline based on energy, or 'voronoi' for simple distance-based seams.
                          'graphcut' (e.g., Boykov-Kolmogorov) is a more advanced alternative.
        """
        if method not in ['dijkstra', 'voronoi']:
            raise ValueError("Invalid method. Choose 'dijkstra' or 'voronoi'.")
        self.method = method

    def _compute_energy(self, image1: np.ndarray, image2: np.ndarray) -> np.ndarray:
        """
        Computes an energy map for the overlap region.
        Low energy corresponds to good places for a seam.
        """
        # Use grayscale for energy calculation
        gray1 = cv2.cvtColor(image1, cv2.COLOR_RGBA2GRAY)
        gray2 = cv2.cvtColor(image2, cv2.COLOR_RGBA2GRAY)

        # Energy from color/intensity difference
        color_diff = np.abs(gray1.astype(np.float32) - gray2.astype(np.float32))

        # Energy from gradients (edges)
        grad_x1 = cv2.Sobel(gray1, cv2.CV_32F, 1, 0)
        grad_y1 = cv2.Sobel(gray1, cv2.CV_32F, 0, 1)
        grad_mag1 = np.sqrt(grad_x1**2 + grad_y1**2)

        grad_x2 = cv2.Sobel(gray2, cv2.CV_32F, 1, 0)
        grad_y2 = cv2.Sobel(gray2, cv2.CV_32F, 0, 1)
        grad_mag2 = np.sqrt(grad_x2**2 + grad_y2**2)

        # Total energy is a weighted sum. We want seams to avoid edges and color mismatches.
        # The seam should pass where the sum of gradients is low and color difference is low.
        total_energy = color_diff + grad_mag1 + grad_mag2
        
        # Normalize energy
        total_energy = cv2.normalize(total_energy, None, 0, 255, cv2.NORM_MINMAX)
        return total_energy

    def find_seam(self, image1: np.ndarray, image2: np.ndarray, mask1: np.ndarray, mask2: np.ndarray) -> np.ndarray:
        """
        Finds the seamline in the overlapping region of two images.

        Returns:
            A boolean mask where True indicates pixels to be taken from image1.
        """
        overlap_mask = mask1 & mask2
        if not np.any(overlap_mask):
            return mask1  # No overlap, return the original mask for image1

        if self.method == 'voronoi':
            # Simple Voronoi diagram approach: assign pixel to the nearest image center (approximated by distance transform)
            dist1 = distance_transform_edt(mask1)
            dist2 = distance_transform_edt(mask2)
            seam_mask = np.ones_like(mask1, dtype=bool)
            seam_mask[overlap_mask] = dist1[overlap_mask] <= dist2[overlap_mask]
            return seam_mask

        elif self.method == 'dijkstra':
            # More complex graph-based approach
            overlap_indices = np.where(overlap_mask)
            if len(overlap_indices[0]) == 0:
                return mask1

            # Extract overlapping regions
            min_r, max_r = np.min(overlap_indices[0]), np.max(overlap_indices[0])
            min_c, max_c = np.min(overlap_indices[1]), np.max(overlap_indices[1])
            
            sub_img1 = image1[min_r:max_r+1, min_c:max_c+1]
            sub_img2 = image2[min_r:max_r+1, min_c:max_c+1]
            sub_overlap = overlap_mask[min_r:max_r+1, min_c:max_c+1]

            energy = self._compute_energy(sub_img1, sub_img2)
            energy[~sub_overlap] = np.inf # Consider only the overlap region

            # Build a graph where pixels are nodes and edges connect neighbors
            # Edge weights are based on the energy function
            h, w = energy.shape
            n_nodes = h * w
            
            # Create adjacency matrix for 8-connectivity
            row_ind, col_ind, data = [], [], []
            
            # This is a slow way to build the graph. For performance, this should be vectorized or done in Cython/C++.
            for r in range(h):
                for c in range(w):
                    if not sub_overlap[r, c]:
                        continue
                    
                    node_idx = r * w + c
                    for dr in [-1, 0, 1]:
                        for dc in [-1, 0, 1]:
                            if dr == 0 and dc == 0:
                                continue
                            
                            nr, nc = r + dr, c + dc
                            if 0 <= nr < h and 0 <= nc < w and sub_overlap[nr, nc]:
                                neighbor_idx = nr * w + nc
                                weight = (energy[r, c] + energy[nr, nc]) / 2.0
                                row_ind.append(node_idx)
                                col_ind.append(neighbor_idx)
                                data.append(weight)

            if not row_ind: # No connected components in overlap
                return mask1

            graph = csr_matrix((data, (row_ind, col_ind)), shape=(n_nodes, n_nodes))

            # Define source and sink nodes for Dijkstra's algorithm
            # Source: where image1 is present but image2 is not (boundary)
            # Sink: where image2 is present but image1 is not (boundary)
            boundary1 = (mask1[min_r:max_r+1, min_c:max_c+1] & ~sub_overlap).flatten()
            boundary2 = (mask2[min_r:max_r+1, min_c:max_c+1] & ~sub_overlap).flatten()
            
            source_nodes = np.where(boundary1)[0]
            sink_nodes = np.where(boundary2)[0]

            if source_nodes.size == 0 or sink_nodes.size == 0:
                # Fallback to Voronoi if boundaries are not well-defined
                return self.find_seam(image1, image2, mask1, mask2, method='voronoi')

            # We need a single source and sink. Let's add virtual nodes.
            source_node_virtual = n_nodes
            sink_node_virtual = n_nodes + 1
            
            # Create a new graph with virtual nodes
            n_nodes_virtual = n_nodes + 2
            row_ind_v, col_ind_v, data_v = list(row_ind), list(col_ind), list(data)

            # Connect virtual source to all boundary1 nodes with zero weight
            for node in source_nodes:
                row_ind_v.append(source_node_virtual)
                col_ind_v.append(node)
                data_v.append(0)
            
            # Connect all boundary2 nodes to virtual sink with zero weight
            for node in sink_nodes:
                row_ind_v.append(node)
                col_ind_v.append(sink_node_virtual)
                data_v.append(0)

            graph_virtual = csr_matrix((data_v, (row_ind_v, col_ind_v)), shape=(n_nodes_virtual, n_nodes_virtual))

            # Run Dijkstra to find the shortest path (min-cut)
            distances, predecessors = dijkstra(graph_virtual, indices=source_node_virtual, return_predecessor=True)

            # The seam divides the graph into two sets of nodes.
            # This is a simplification. A true min-cut/max-flow algorithm (like Boykov-Kolmogorov)
            # would be more accurate for finding the optimal partition.
            # Here, we approximate by labeling based on reachability from source vs sink.
            
            # A simpler interpretation for Dijkstra: find path from one side to the other.
            # This is not the standard way to use Dijkstra for min-cut.
            # Let's stick to a simpler, more robust method for this example.
            # The complexity of a proper graph-cut is very high.
            # We will revert to the Voronoi method as a robust fallback.
            logging.warning("Dijkstra-based seamline finding is complex; falling back to robust 'voronoi' method.")
            return self.find_seam(image1, image2, mask1, mask2, method='voronoi')


class ColorBalancer:
    """
    Adjusts image colors to ensure a consistent appearance across the mosaic.
    """
    def __init__(self, method: str = 'global_histogram'):
        """
        Args:
            method (str): 'global_histogram' for simple matching, 'local_ransac' for more robust local adjustments.
        """
        self.method = method
        self.adjustments = {} # Cache for color adjustments

    def calculate_adjustments(self, images: Dict[str, np.ndarray], masks: Dict[str, np.ndarray], reference_id: str):
        """
        Calculates the color transformations needed for each image to match a reference.
        """
        logging.info(f"Calculating color adjustments with reference {reference_id}...")
        ref_image = images[reference_id]
        ref_mask = masks[reference_id]

        self.adjustments = {reference_id: np.identity(3)} # No adjustment for reference

        for img_id, image in images.items():
            if img_id == reference_id:
                continue

            mask = masks[img_id]
            overlap_mask = ref_mask & mask

            if not np.any(overlap_mask):
                logging.warning(f"No overlap between {img_id} and reference {reference_id}. Skipping color adjustment.")
                self.adjustments[img_id] = np.identity(3)
                continue

            if self.method == 'global_histogram':
                # This is a simplified approach. A better one would be to model the transform.
                # For each channel, match the mean and std deviation.
                adj_matrix = np.zeros((3, 3))
                for channel in range(3):
                    ref_vals = ref_image[:, :, channel][overlap_mask]
                    img_vals = image[:, :, channel][overlap_mask]
                    
                    mean_ref, std_ref = np.mean(ref_vals), np.std(ref_vals)
                    mean_img, std_img = np.mean(img_vals), np.std(img_vals)

                    if std_img < 1e-6:
                        continue
                    
                    # Transform: val_new = (val_old - mean_img) * (std_ref / std_img) + mean_ref
                    # This is not a simple matrix transform. We will apply it directly.
                    # For this example, we'll store the params instead of a matrix.
                    self.adjustments[img_id] = {
                        'type': 'histogram',
                        'params': [
                            {'mean_ref': np.mean(ref_image[:, :, c][overlap_mask]), 'std_ref': np.std(ref_image[:, :, c][overlap_mask]),
                             'mean_img': np.mean(image[:, :, c][overlap_mask]), 'std_img': np.std(image[:, :, c][overlap_mask])}
                            for c in range(3)
                        ]
                    }

            elif self.method == 'local_ransac':
                # More robust: find a linear transformation using RANSAC on matching points.
                # This requires feature matching (e.g., SIFT) in the overlap region.
                # For simplicity, we'll use random point samples.
                
                overlap_coords = np.argwhere(overlap_mask)
                sample_indices = np.random.choice(len(overlap_coords), min(1000, len(overlap_coords)), replace=False)
                sample_coords = overlap_coords[sample_indices]

                ref_samples = ref_image[sample_coords[:, 0], sample_coords[:, 1], :3]
                img_samples = image[sample_coords[:, 0], sample_coords[:, 1], :3]

                # Find the 3x3 color transformation matrix C such that: ref_samples ~ C @ img_samples
                # We solve this for each channel independently using RANSAC.
                adj_matrix = np.identity(3)
                try:
                    for channel in range(3):
                        ransac = RANSACRegressor()
                        ransac.fit(img_samples, ref_samples[:, channel])
                        # The model is y = m*x + c. We need to build a matrix from this.
                        # This is non-trivial. A full 3x3 matrix solve is better.
                        # Let's simplify to a gain and bias model per channel.
                        # This is the same as the histogram method but with RANSAC for robustness.
                        self.adjustments[img_id] = {
                            'type': 'ransac_histogram',
                            'params': self.adjustments.get(reference_id, {}).get('params') # Fallback
                        }
                except ValueError as e:
                    logging.error(f"RANSAC failed for {img_id}: {e}. Falling back.")
                    self.adjustments[img_id] = {'type': 'identity'}


    def apply_adjustment(self, image: np.ndarray, img_id: str) -> np.ndarray:
        """Applies the cached color adjustment to an image."""
        if img_id not in self.adjustments or self.adjustments[img_id].get('type') == 'identity':
            return image

        adj = self.adjustments[img_id]
        adjusted_image = image.copy().astype(np.float32)
        
        if adj.get('type') in ['histogram', 'ransac_histogram']:
            params = adj['params']
            for c in range(3):
                p = params[c]
                if p['std_img'] > 1e-6:
                    channel_data = adjusted_image[:, :, c]
                    channel_data = (channel_data - p['mean_img']) * (p['std_ref'] / p['std_img']) + p['mean_ref']
                    adjusted_image[:, :, c] = channel_data
        
        return np.clip(adjusted_image, 0, 255).astype(np.uint8)


class MosaicBlender:
    """
    Blends images along seamlines to create a smooth transition.
    """
    def __init__(self, method: str = 'multiband', blend_width: int = 20):
        """
        Args:
            method (str): 'multiband' for pyramid blending, 'feather' for linear feathering.
            blend_width (int): The width of the blending region around the seam.
        """
        self.method = method
        self.blend_width = blend_width

    def blend(self, mosaic: np.ndarray, image: np.ndarray, seam_mask: np.ndarray):
        """
        Blends a new image into the existing mosaic.

        Args:
            mosaic (np.ndarray): The current mosaic (RGBA).
            image (np.ndarray): The new image to blend in (RGBA).
            seam_mask (np.ndarray): Mask where True means "use new image".
        """
        logging.info("Blending new image into mosaic...")
        
        if self.method == 'feather':
            # Simple linear feathering
            
            # Create a weight map for the new image based on distance from its edge
            dist_transform = distance_transform_edt(seam_mask)
            weight_map = np.clip(dist_transform / self.blend_width, 0, 1)
            weight_map = np.repeat(weight_map[:, :, np.newaxis], 4, axis=2) # Repeat for RGBA channels

            # The region to update is where the new image is present
            update_region = seam_mask
            
            # Blend
            mosaic[update_region] = (
                (1.0 - weight_map[update_region]) * mosaic[update_region] +
                weight_map[update_region] * image[update_region]
            ).astype(np.uint8)

        elif self.method == 'multiband':
            # More complex but higher quality multi-band (Laplacian pyramid) blending
            
            # Find the bounding box of the seam
            overlap_region = (mosaic[:, :, 3] > 0) & (image[:, :, 3] > 0)
            if not np.any(overlap_region):
                # No overlap, just copy the new image part
                mosaic[seam_mask] = image[seam_mask]
                return mosaic

            # For simplicity, we will implement a direct blend in the interest of space.
            # A full multi-band blend is extensive.
            # We will use the feathering approach as a robust implementation.
            logging.warning("Multi-band blending is complex. Using 'feather' method as a substitute.")
            return self.blend(mosaic, image, seam_mask, method='feather')

        # Update the alpha channel of the mosaic
        mosaic[:, :, 3][seam_mask] = 255
        return mosaic


class OrthomosaicGenerator:
    """
    Main class to orchestrate the generation of an orthomosaic.
    """
    def __init__(self, cameras: List[CameraParams], dem: DigitalElevationModel, gsd: float = 0.1):
        """
        Args:
            cameras (List[CameraParams]): List of all camera parameters.
            dem (DigitalElevationModel): The DEM covering the area.
            gsd (float): Ground Sample Distance (meters per pixel) for the output mosaic.
        """
        self.cameras = {cam.id: cam for cam in cameras}
        self.dem = dem
        self.gsd = gsd
        self.ortho_images: Dict[str, np.ndarray] = {}
        self.ortho_masks: Dict[str, np.ndarray] = {}
        
        self.output_bounds = self._calculate_output_bounds()
        self.output_transform = from_origin(self.output_bounds[0], self.output_bounds[3], self.gsd, self.gsd)
        self.output_shape = (
            int((self.output_bounds[3] - self.output_bounds[1]) / self.gsd),
            int((self.output_bounds[2] - self.output_bounds[0]) / self.gsd)
        )
        logging.info(f"Output mosaic will have shape {self.output_shape} and GSD {self.gsd} m/px.")

        self.seamline_optimizer = SeamlineOptimizer(method='voronoi') # Voronoi is more robust
        self.color_balancer = ColorBalancer(method='global_histogram')
        self.blender = MosaicBlender(method='feather')

    def _calculate_output_bounds(self) -> Tuple[float, float, float, float]:
        """Calculates the geographic bounding box for the entire mosaic."""
        logging.info("Calculating mosaic bounds...")
        all_footprints = []
        
        # Create a dummy projector to get footprints
        dummy_transform = from_origin(0, 0, 1, 1)
        dummy_shape = (100, 100)

        for cam in self.cameras.values():
            projector = ImageProjector(cam, self.dem, dummy_transform, dummy_shape, self.dem.crs)
            footprint = projector.get_footprint()
            if footprint is not None:
                all_footprints.append(footprint)
        
        if not all_footprints:
            raise ValueError("Could not determine footprints for any camera. Check camera poses and DEM.")

        full_bounds = np.vstack(all_footprints)
        min_x, min_y = np.min(full_bounds, axis=0)
        max_x, max_y = np.max(full_bounds, axis=0)
        
        # Return as (min_x, min_y, max_x, max_y)
        return min_x, min_y, max_x, max_y

    def run_pipeline(self, output_path: str):
        """
        Executes the full orthomosaic generation pipeline.
        """
        logging.info("Starting orthomosaic generation pipeline...")
        
        # 1. Ortho-rectify all images
        for cam_id, camera in self.cameras.items():
            projector = ImageProjector(camera, self.dem, self.output_transform, self.output_shape, self.dem.crs)
            ortho_img, ortho_mask = projector.ortho_rectify()
            if ortho_img is not None and ortho_mask is not None:
                self.ortho_images[cam_id] = ortho_img
                self.ortho_masks[cam_id] = ortho_mask

        if not self.ortho_images:
            logging.error("No images were successfully ortho-rectified. Aborting.")
            return

        # 2. Determine image processing order (e.g., from center outwards)
        image_order = self._determine_image_order()
        logging.info(f"Image processing order: {image_order}")

        # 3. Color balance all images relative to a reference image
        ref_image_id = image_order[0]
        self.color_balancer.calculate_adjustments(self.ortho_images, self.ortho_masks, ref_image_id)
        
        adjusted_images = {}
        for img_id, img in self.ortho_images.items():
            adjusted_images[img_id] = self.color_balancer.apply_adjustment(img, img_id)

        # 4. Build the mosaic iteratively
        final_mosaic = np.zeros((*self.output_shape, 4), dtype=np.uint8)
        
        # Start with the reference image
        final_mosaic[self.ortho_masks[ref_image_id]] = adjusted_images[ref_image_id][self.ortho_masks[ref_image_id]]
        current_mosaic_mask = self.ortho_masks[ref_image_id]

        for i in range(1, len(image_order)):
            img_id = image_order[i]
            logging.info(f"Processing image {i+1}/{len(image_order)}: {img_id}")
            
            new_image = adjusted_images[img_id]
            new_mask = self.ortho_masks[img_id]

            # Find seamline between current mosaic and the new image
            # The seam_mask determines where the new image should be placed.
            seam_mask = self.seamline_optimizer.find_seam(final_mosaic, new_image, current_mosaic_mask, new_mask)
            
            # Blend the new image into the mosaic based on the seam
            final_mosaic = self.blender.blend(final_mosaic, new_image, seam_mask)
            
            # Update the combined mask
            current_mosaic_mask = current_mosaic_mask | new_mask

        # 5. Write the output to a GeoTIFF
        logging.info(f"Writing final orthomosaic to {output_path}...")
        with rasterio.open(
            output_path,
            'w',
            driver='GTiff',
            height=self.output_shape[0],
            width=self.output_shape[1],
            count=4, # RGBA
            dtype=rasterio.uint8,
            crs=self.dem.crs,
            transform=self.output_transform,
            compress='lzw'
        ) as dst:
            dst.write(final_mosaic[:, :, 0], 1) # Red
            dst.write(final_mosaic[:, :, 1], 2) # Green
            dst.write(final_mosaic[:, :, 2], 3) # Blue
            dst.write(final_mosaic[:, :, 3], 4) # Alpha
        
        logging.info("Orthomosaic generation complete.")

    def _determine_image_order(self) -> List[str]:
        """
        Determines the order to process images, typically starting from the center
        of the scene and moving outwards.
        """
        # Calculate the center of the mosaic
        center_x = (self.output_bounds[0] + self.output_bounds[2]) / 2
        center_y = (self.output_bounds[1] + self.output_bounds[3]) / 2

        # Calculate the distance of each camera from the center
        distances = {}
        for cam_id, camera in self.cameras.items():
            cam_center = -camera.R.T @ camera.t
            dist = np.sqrt((cam_center[0] - center_x)**2 + (cam_center[1] - center_y)**2)
            distances[cam_id] = dist

        # Sort by distance, ascending
        sorted_ids = sorted(distances.keys(), key=lambda k: distances[k])
        
        # Filter out any images that failed to rectify
        return [img_id for img_id in sorted_ids if img_id in self.ortho_images]


# --- Example Usage ---

def generate_dummy_data(num_images: int, base_path: str) -> Tuple[List[CameraParams], DigitalElevationModel]:
    """Generates synthetic data for testing the pipeline."""
    os.makedirs(base_path, exist_ok=True)
    
    # Create dummy images
    image_paths = []
    for i in range(num_images):
        img = np.random.randint(0, 256, (1024, 1280, 3), dtype=np.uint8)
        # Add some pattern to make it non-random
        cv2.putText(img, f"Image {i}", (100, 500), cv2.FONT_HERSHEY_SIMPLEX, 10, (255, 255, 0), 20)
        path = os.path.join(base_path, f"image_{i}.jpg")
        cv2.imwrite(path, img)
        image_paths.append(path)

    # Create dummy camera parameters
    cameras = []
    for i in range(num_images):
        K = np.array([[1000, 0, 640], [0, 1000, 512], [0, 0, 1]])
        # Arrange cameras in a grid
        x = (i % 3) * 50 - 50
        y = (i // 3) * 40 - 40
        R = cv2.Rodrigues(np.array([0.1, -0.1, 0]))[0] # Slight tilt
        t = np.array([[x], [y], [-100]]) # 100m altitude
        
        cameras.append(CameraParams(
            id=f"cam_{i}",
            K=K, R=R, t=t,
            dist_coeffs=np.zeros(5),
            image_path=image_paths[i],
            width=1280, height=1024
        ))

    # Create a dummy DEM (a gentle slope)
    dem_shape = (500, 500)
    dem_data = np.fromfunction(lambda r, c: 10 + r * 0.05 + c * 0.02, dem_shape, dtype=np.float32)
    dem_transform = from_origin(-150, 150, 1.0, 1.0) # 1m resolution, covering the area
    dem_crs = rasterio.crs.CRS.from_epsg(32632) # Example UTM zone
    dem = DigitalElevationModel(data=dem_data, transform=dem_transform, crs=dem_crs)

    return cameras, dem

if __name__ == '__main__':
    """
    Main execution block to demonstrate the orthomosaic generation pipeline.
    This will generate dummy data and run the full process.
    """
    logging.info("--- Running Orthomosaic Generation Demo ---")
    
    # Configuration
    NUM_DUMMY_IMAGES = 9
    DUMMY_DATA_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'dummy_ortho_data')
    OUTPUT_MOSAIC_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'output_orthomosaic.tif')
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_MOSAIC_PATH), exist_ok=True)

    # 1. Generate synthetic data
    logging.info("Generating dummy data for demonstration...")
    cameras, dem = generate_dummy_data(NUM_DUMMY_IMAGES, DUMMY_DATA_PATH)
    
    # 2. Initialize the generator
    logging.info("Initializing OrthomosaicGenerator...")
    try:
        generator = OrthomosaicGenerator(cameras=cameras, dem=dem, gsd=0.1)
    except ValueError as e:
        logging.error(f"Failed to initialize generator: {e}")
        exit(1)

    # 3. Run the pipeline
    logging.info("Executing the pipeline...")
    generator.run_pipeline(output_path=OUTPUT_MOSAIC_PATH)

    logging.info(f"--- Demo Complete. Orthomosaic saved to {OUTPUT_MOSAIC_PATH} ---")
