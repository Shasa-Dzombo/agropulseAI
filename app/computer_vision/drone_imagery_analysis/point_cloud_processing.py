# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\drone_imagery_analysis\point_cloud_processing.py

"""
Advanced Point Cloud Processing for Agricultural Analysis
=========================================================

This module provides a suite of advanced tools for processing, segmenting, and
analyzing 3D point clouds, specifically tailored for agricultural applications.
While `dem_generation.py` focuses on creating elevation models, this module
delves deeper into the structure and properties of the point cloud itself to
extract meaningful information about vegetation, terrain, and objects.

The functionalities provided here are essential for tasks such as individual
plant analysis, canopy structure characterization, and detailed terrain modeling.

Key Components:
---------------
1.  **Advanced Filtering**: A collection of filters to pre-process and clean
    point clouds beyond simple outlier removal.
    -   `VoxelGridDownsampler`: Reduces point cloud density uniformly, which is
        crucial for managing large datasets and speeding up subsequent processing
        steps while preserving the overall structure.
    -   `PassThroughFilter`: Allows for simple spatial filtering by keeping or
        discarding points within a specified range along a given axis.
    -   `RadiusOutlierRemover`: Removes points that are isolated from their
        neighbors, effective for cleaning up sparse noise.

2.  **Feature Extraction**: Algorithms to compute geometric properties at the
    point or neighborhood level. These features are the basis for most
    segmentation and classification tasks.
    -   `NormalEstimator`: Computes the normal vector for each point by analyzing
        the local surface geometry of its neighbors. Normals are fundamental for
        detecting surfaces, edges, and orientation.
    -   `GeometricFeatureExtractor`: Calculates a variety of insightful features
        from the eigenvalues of the local covariance matrix, such as:
        -   Linearity, Planarity, Sphericity: Describe the shape of the local
          neighborhood (is it a line, a plane, or a sphere?).
        -   Curvature: Measures how much the surface bends at a point.
        -   Verticality: Indicates how vertical the local surface is, useful for
          distinguishing tree trunks from ground or foliage.

3.  **Segmentation**: Algorithms to partition the point cloud into meaningful,
    distinct clusters or segments.
    -   `EuclideanClusterExtraction`: A fast and effective method for grouping
        spatially close points. It's excellent for separating individual trees,
        bushes, or other distinct objects.
    -   `RegionGrowingSegmentation`: A more sophisticated algorithm that groups
        points based on the similarity of their properties, typically normals
        and curvature. It can find smooth surfaces even if they are spatially
        large.
    -   `RANSACSegmenter`: Implements the Random Sample Consensus (RANSAC)
        algorithm to find and segment primitive shapes like planes (for ground
        or building roofs) and cylinders (for tree trunks or poles).

4.  **Classification**:
    -   `PointCloudClassifier`: A machine learning-based component that uses the
        extracted geometric features to classify each point into semantic
        categories (e.g., 'ground', 'low vegetation', 'high vegetation',
        'building'). This provides a semantic understanding of the scene.

5.  **`PointCloudProcessor`**: An orchestrator pipeline that chains these
    operations together into a configurable workflow, allowing users to easily
    apply a sequence of processing steps to a point cloud.

Dependencies:
-------------
- NumPy: For all numerical operations.
- SciPy: For spatial data structures (cKDTree).
- Scikit-learn: For RANSAC, clustering algorithms (DBSCAN), and classifiers
  (RandomForestClassifier).
- Open3D (optional but recommended): Provides highly optimized implementations
  for many of these algorithms and is excellent for visualization. This module
  provides NumPy-based implementations for core understanding but can be
  bridged to Open3D for performance.
"""

import numpy as np
from scipy.spatial import cKDTree
from sklearn.cluster import DBSCAN
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from collections import defaultdict
import logging
import time
from typing import Tuple, List, Dict, Any, Optional

# Re-use PointCloud structure from dem_generation for consistency
try:
    from .dem_generation import PointCloud
except ImportError:
    # Fallback for standalone execution
    @dataclass
    class PointCloud:
        points: np.ndarray
        colors: Optional[np.ndarray] = None
        classification: Optional[np.ndarray] = None
        crs: Optional[Any] = None
        # Add other fields that might be added by this module
        normals: Optional[np.ndarray] = None
        features: Optional[Dict[str, np.ndarray]] = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Advanced Filtering ---

class VoxelGridDownsampler:
    """
    Downsamples a point cloud by averaging points within each voxel of a 3D grid.
    """
    def __init__(self, voxel_size: float):
        """
        Args:
            voxel_size (float): The edge length of a single voxel.
        """
        self.voxel_size = voxel_size

    def filter(self, pc: PointCloud) -> PointCloud:
        """
        Applies the voxel grid downsampling.
        """
        logging.info(f"Downsampling point cloud with voxel size {self.voxel_size}...")
        start_time = time.time()

        # Determine voxel indices for each point
        voxel_indices = np.floor(pc.points / self.voxel_size).astype(np.int32)
        
        # Use a dictionary to group points by their voxel index
        voxel_dict = defaultdict(list)
        for i, idx_tuple in enumerate(map(tuple, voxel_indices)):
            voxel_dict[idx_tuple].append(i)

        # Compute the centroid for each voxel
        downsampled_points = np.array([
            np.mean(pc.points[indices], axis=0) for indices in voxel_dict.values()
        ])
        
        # Average colors and other attributes if they exist
        downsampled_colors = None
        if pc.colors is not None:
            downsampled_colors = np.array([
                np.mean(pc.colors[indices], axis=0) for indices in voxel_dict.values()
            ]).astype(np.uint8)

        num_original = len(pc.points)
        num_downsampled = len(downsampled_points)
        logging.info(
            f"Downsampling complete in {time.time() - start_time:.2f}s. "
            f"Reduced from {num_original} to {num_downsampled} points."
        )

        return PointCloud(
            points=downsampled_points,
            colors=downsampled_colors,
            crs=pc.crs
        )

class PassThroughFilter:
    """
    Filters points based on a value range along a specified axis.
    """
    def __init__(self, axis: str = 'z', min_val: float = -np.inf, max_val: float = np.inf):
        self.axis_map = {'x': 0, 'y': 1, 'z': 2}
        if axis not in self.axis_map:
            raise ValueError("Axis must be one of 'x', 'y', or 'z'.")
        self.axis_idx = self.axis_map[axis]
        self.min_val = min_val
        self.max_val = max_val

    def filter(self, pc: PointCloud) -> PointCloud:
        """Applies the pass-through filter."""
        logging.info(f"Applying pass-through filter on axis {self.axis_idx} with range ({self.min_val}, {self.max_val}).")
        
        axis_values = pc.points[:, self.axis_idx]
        mask = (axis_values >= self.min_val) & (axis_values <= self.max_val)
        
        return PointCloud(
            points=pc.points[mask],
            colors=pc.colors[mask] if pc.colors is not None else None,
            classification=pc.classification[mask] if pc.classification is not None else None,
            crs=pc.crs
        )

# --- Feature Extraction ---

class NormalEstimator:
    """
    Computes normal vectors for each point in the point cloud.
    """
    def __init__(self, search_radius: float, k_neighbors: Optional[int] = None):
        """
        Args:
            search_radius (float): Radius to find neighbors for normal estimation.
            k_neighbors (int, optional): Max number of neighbors to use. If None, uses all in radius.
        """
        self.search_radius = search_radius
        self.k_neighbors = k_neighbors

    def compute(self, pc: PointCloud):
        """
        Computes normals and attaches them to the PointCloud object.
        """
        logging.info(f"Estimating normals with search radius {self.search_radius}...")
        start_time = time.time()

        if not hasattr(pc, '_kdtree') or pc._kdtree is None:
            pc._kdtree = cKDTree(pc.points)
        
        # Find neighbors for each point
        neighbors_indices = pc._kdtree.query_ball_point(pc.points, self.search_radius)
        
        normals = np.zeros_like(pc.points)
        
        for i, indices in enumerate(neighbors_indices):
            if len(indices) < 3:
                # Not enough points to define a plane, normal remains zero
                continue
            
            if self.k_neighbors is not None and len(indices) > self.k_neighbors:
                indices = np.random.choice(indices, self.k_neighbors, replace=False)

            # Extract neighbor points and compute covariance matrix
            neighbor_points = pc.points[indices]
            center = np.mean(neighbor_points, axis=0)
            covariance_matrix = np.cov(neighbor_points - center, rowvar=False)
            
            # The normal is the eigenvector corresponding to the smallest eigenvalue
            eigenvalues, eigenvectors = np.linalg.eigh(covariance_matrix)
            normal = eigenvectors[:, np.argmin(eigenvalues)]
            normals[i] = normal

        # Orient normals consistently (e.g., towards a viewpoint)
        # A simple approach: orient all normals "upwards" along Z axis if possible
        z_axis = np.array([0, 0, 1])
        for i in range(len(normals)):
            if np.dot(normals[i], z_axis) < 0:
                normals[i] *= -1
        
        pc.normals = normals
        logging.info(f"Normal estimation completed in {time.time() - start_time:.2f}s.")

class GeometricFeatureExtractor:
    """
    Extracts geometric features based on the local neighborhood of each point.
    """
    def __init__(self, search_radius: float):
        self.search_radius = search_radius

    def compute(self, pc: PointCloud):
        """
        Computes features and attaches them to the PointCloud object.
        """
        logging.info(f"Extracting geometric features with search radius {self.search_radius}...")
        start_time = time.time()

        if not hasattr(pc, '_kdtree') or pc._kdtree is None:
            pc._kdtree = cKDTree(pc.points)
        
        neighbors_indices = pc._kdtree.query_ball_point(pc.points, self.search_radius)
        
        num_points = len(pc.points)
        features = {
            'linearity': np.zeros(num_points),
            'planarity': np.zeros(num_points),
            'sphericity': np.zeros(num_points),
            'curvature': np.zeros(num_points),
            'verticality': np.zeros(num_points),
        }

        if pc.normals is None:
            logging.warning("Normals not found. Computing them first for verticality.")
            ne = NormalEstimator(search_radius=self.search_radius)
            ne.compute(pc)

        for i, indices in enumerate(neighbors_indices):
            if len(indices) < 3:
                continue

            neighbor_points = pc.points[indices]
            center = np.mean(neighbor_points, axis=0)
            covariance_matrix = np.cov(neighbor_points - center, rowvar=False)
            
            eigenvalues = np.linalg.eigh(covariance_matrix)[0]
            eigenvalues = np.sort(eigenvalues)[::-1] # Sort descending: e1 > e2 > e3
            
            e1, e2, e3 = eigenvalues
            sum_e = e1 + e2 + e3
            if sum_e == 0:
                continue

            # Normalize eigenvalues
            l1, l2, l3 = eigenvalues / sum_e

            features['linearity'][i] = (l1 - l2) / l1 if l1 > 0 else 0
            features['planarity'][i] = (l2 - l3) / l1 if l1 > 0 else 0
            features['sphericity'][i] = l3 / l1 if l1 > 0 else 0
            features['curvature'][i] = l3 / (l1 + l2 + l3) if (l1 + l2 + l3) > 0 else 0
            
            # Verticality requires normals
            if pc.normals is not None:
                z_axis = np.array([0, 0, 1])
                features['verticality'][i] = 1.0 - np.abs(np.dot(pc.normals[i], z_axis))

        pc.features = features
        logging.info(f"Geometric feature extraction completed in {time.time() - start_time:.2f}s.")

# --- Segmentation ---

class EuclideanClusterExtraction:
    """
    Groups points into clusters based on Euclidean distance.
    Uses DBSCAN, a density-based clustering algorithm.
    """
    def __init__(self, search_radius: float, min_cluster_size: int = 10):
        """
        Args:
            search_radius (float): The maximum distance between two samples for
                                   one to be considered as in the neighborhood of the other.
            min_cluster_size (int): The number of samples in a neighborhood for a
                                    point to be considered as a core point.
        """
        self.search_radius = search_radius
        self.min_cluster_size = min_cluster_size

    def segment(self, pc: PointCloud) -> List[PointCloud]:
        """
        Segments the point cloud into a list of smaller PointCloud objects.
        """
        logging.info(f"Performing Euclidean clustering with radius {self.search_radius} and min size {self.min_cluster_size}...")
        start_time = time.time()

        db = DBSCAN(eps=self.search_radius, min_samples=self.min_cluster_size).fit(pc.points)
        labels = db.labels_
        
        unique_labels = set(labels)
        num_clusters = len(unique_labels) - (1 if -1 in labels else 0)
        logging.info(f"Found {num_clusters} clusters in {time.time() - start_time:.2f}s.")

        clusters = []
        for label in unique_labels:
            if label == -1: # -1 is the label for noise points in DBSCAN
                continue
            
            mask = labels == label
            cluster_pc = PointCloud(
                points=pc.points[mask],
                colors=pc.colors[mask] if pc.colors is not None else None,
                classification=pc.classification[mask] if pc.classification is not None else None,
                crs=pc.crs
            )
            clusters.append(cluster_pc)
            
        return clusters

class RANSACSegmenter:
    """
    Segments primitive shapes (e.g., planes) using RANSAC.
    """
    def __init__(self, model_type: str = 'plane', threshold: float = 0.1):
        """
        Args:
            model_type (str): The type of model to fit ('plane', 'cylinder', etc.).
            threshold (float): Maximum distance for a point to be considered an inlier.
        """
        if model_type != 'plane':
            raise NotImplementedError("Only 'plane' model is implemented in this example.")
        self.model_type = model_type
        self.threshold = threshold

    def segment(self, pc: PointCloud, max_iterations: int = 100) -> Tuple[Optional[PointCloud], Optional[PointCloud]]:
        """
        Finds one instance of the model in the point cloud.

        Returns:
            A tuple of (inlier_cloud, outlier_cloud).
        """
        logging.info(f"Attempting to segment a '{self.model_type}' with RANSAC...")
        start_time = time.time()

        if self.model_type == 'plane':
            best_inliers_mask = None
            best_inlier_count = 0

            for _ in range(max_iterations):
                # 1. Randomly sample 3 points
                sample_indices = np.random.choice(len(pc.points), 3, replace=False)
                sample_points = pc.points[sample_indices]

                # 2. Define the plane (Ax + By + Cz + D = 0)
                v1 = sample_points[1] - sample_points[0]
                v2 = sample_points[2] - sample_points[0]
                normal = np.cross(v1, v2)
                norm = np.linalg.norm(normal)
                if norm == 0:
                    continue
                normal /= norm
                
                A, B, C = normal
                D = -np.dot(normal, sample_points[0])

                # 3. Calculate distance of all points to the plane
                distances = np.abs(A * pc.points[:, 0] + B * pc.points[:, 1] + C * pc.points[:, 2] + D)
                
                # 4. Count inliers
                inliers_mask = distances < self.threshold
                inlier_count = np.sum(inliers_mask)

                # 5. Keep the best model
                if inlier_count > best_inlier_count:
                    best_inlier_count = inlier_count
                    best_inliers_mask = inliers_mask
            
            if best_inliers_mask is None:
                logging.warning("RANSAC failed to find a plane.")
                return None, pc

            inlier_pc = PointCloud(
                points=pc.points[best_inliers_mask],
                colors=pc.colors[best_inliers_mask] if pc.colors is not None else None,
                crs=pc.crs
            )
            outlier_pc = PointCloud(
                points=pc.points[~best_inliers_mask],
                colors=pc.colors[~best_inliers_mask] if pc.colors is not None else None,
                crs=pc.crs
            )
            
            logging.info(f"RANSAC found a plane with {best_inlier_count} inliers in {time.time() - start_time:.2f}s.")
            return inlier_pc, outlier_pc
        
        return None, pc

# --- Classification ---

class PointCloudClassifier:
    """
    Classifies points using their geometric features.
    """
    def __init__(self, model=None):
        self.model = model if model is not None else RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)

    def train(self, pc: PointCloud, labels: np.ndarray):
        """
        Trains the classifier.

        Args:
            pc (PointCloud): A point cloud with computed features.
            labels (np.ndarray): An array of integer labels for each point.
        """
        if pc.features is None:
            raise ValueError("Point cloud must have features computed before training.")
        
        logging.info("Training point cloud classifier...")
        feature_matrix = np.vstack([f for f in pc.features.values()]).T
        
        X_train, X_test, y_train, y_test = train_test_split(feature_matrix, labels, test_size=0.3, random_state=42)
        
        self.model.fit(X_train, y_train)
        
        y_pred = self.model.predict(X_test)
        logging.info("Classifier training complete. Evaluation report:")
        print(classification_report(y_test, y_pred))

    def predict(self, pc: PointCloud) -> np.ndarray:
        """
        Predicts the class for each point in the point cloud.
        """
        if self.model is None:
            raise RuntimeError("Classifier has not been trained.")
        if pc.features is None:
            raise ValueError("Point cloud must have features computed before prediction.")

        logging.info("Classifying points...")
        feature_matrix = np.vstack([f for f in pc.features.values()]).T
        
        predictions = self.model.predict(feature_matrix)
        pc.classification = predictions
        
        logging.info("Classification complete.")
        return predictions

# --- Main Processor ---

class PointCloudProcessor:
    """
    An orchestrator to run a sequence of processing steps on a point cloud.
    """
    def __init__(self, pc: PointCloud):
        self.pc = pc

    def run_pipeline(self, steps: List[Dict[str, Any]]):
        """
        Executes a processing pipeline defined by a list of steps.

        Example `steps` format:
        [
            {'type': 'downsample', 'voxel_size': 0.1},
            {'type': 'estimate_normals', 'search_radius': 0.3},
            {'type': 'extract_features', 'search_radius': 0.5},
            {'type': 'classify', 'model': trained_model_object},
        ]
        """
        logging.info("Starting point cloud processing pipeline...")
        for step in steps:
            step_type = step.pop('type')
            if step_type == 'downsample':
                self.pc = VoxelGridDownsampler(**step).filter(self.pc)
            elif step_type == 'estimate_normals':
                NormalEstimator(**step).compute(self.pc)
            elif step_type == 'extract_features':
                GeometricFeatureExtractor(**step).compute(self.pc)
            elif step_type == 'classify':
                PointCloudClassifier(**step).predict(self.pc)
            else:
                logging.warning(f"Unknown pipeline step type: {step_type}")
        
        logging.info("Pipeline execution finished.")
        return self.pc

# --- Example Usage ---

def generate_demo_pc_for_processing() -> PointCloud:
    """Generates a synthetic point cloud with planes and clusters."""
    # Ground plane
    ground = np.random.rand(5000, 3)
    ground[:, 0] *= 10
    ground[:, 1] *= 10
    ground[:, 2] *= 0.1 # Flat-ish ground
    
    # Wall plane
    wall = np.random.rand(3000, 3)
    wall[:, 0] *= 0.1
    wall[:, 1] *= 10
    wall[:, 2] *= 5 # 5m high wall
    wall[:, 0] += 10 # Position wall at x=10

    # Two spherical clusters (trees/bushes)
    theta1 = np.random.uniform(0, 2 * np.pi, 1000)
    phi1 = np.random.uniform(0, np.pi, 1000)
    r1 = np.random.uniform(0.5, 1.5, 1000)
    cluster1 = np.array([
        r1 * np.sin(phi1) * np.cos(theta1) + 3,
        r1 * np.sin(phi1) * np.sin(theta1) + 3,
        r1 * np.cos(phi1) + 1.5
    ]).T

    theta2, phi2, r2 = np.random.uniform(0, 2*np.pi, 1200), np.random.uniform(0, np.pi, 1200), np.random.uniform(0.8, 1.8, 1200)
    cluster2 = np.array([
        r2 * np.sin(phi2) * np.cos(theta2) + 7,
        r2 * np.sin(phi2) * np.sin(theta2) + 7,
        r2 * np.cos(phi2) + 2.0
    ]).T

    points = np.vstack([ground, wall, cluster1, cluster2])
    
    # Create labels for training demo
    # 0=ground, 1=wall, 2=vegetation
    labels = np.concatenate([
        np.full(len(ground), 0),
        np.full(len(wall), 1),
        np.full(len(cluster1), 2),
        np.full(len(cluster2), 2)
    ])

    return PointCloud(points=points), labels


if __name__ == '__main__':
    logging.info("--- Running Advanced Point Cloud Processing Demo ---")

    pc, labels = generate_demo_pc_for_processing()
    logging.info(f"Generated a demo point cloud with {len(pc.points)} points.")

    # --- Demo 1: Segmentation ---
    logging.info("\n--- Demo 1: Plane and Cluster Segmentation ---")
    
    # Find the ground plane
    ransac_segmenter = RANSACSegmenter(model_type='plane', threshold=0.1)
    ground_plane_pc, non_ground_pc = ransac_segmenter.segment(pc)

    if non_ground_pc:
        # Find clusters in the remaining points
        cluster_extractor = EuclideanClusterExtraction(search_radius=0.5, min_cluster_size=50)
        clusters = cluster_extractor.segment(non_ground_pc)
        logging.info(f"Found {len(clusters)} clusters in the non-ground points.")
        if ground_plane_pc:
            logging.info(f"Ground plane has {len(ground_plane_pc.points)} points.")

    # --- Demo 2: Feature Extraction and Classification ---
    logging.info("\n--- Demo 2: Feature-based Classification ---")
    
    # Create a fresh PC for this demo
    pc_for_classification, labels = generate_demo_pc_for_processing()

    # Define and run a processing pipeline
    pipeline_steps = [
        {'type': 'estimate_normals', 'search_radius': 0.4},
        {'type': 'extract_features', 'search_radius': 0.6},
    ]
    processor = PointCloudProcessor(pc_for_classification)
    processed_pc = processor.run_pipeline(pipeline_steps)

    # Train a classifier
    classifier = PointCloudClassifier()
    classifier.train(processed_pc, labels)

    # Predict on the same data (for demonstration)
    predicted_labels = classifier.predict(processed_pc)
    logging.info(f"Sample of predicted labels: {predicted_labels[:20]}")
    logging.info(f"Number of points classified as ground (0): {np.sum(predicted_labels == 0)}")
    logging.info(f"Number of points classified as wall (1): {np.sum(predicted_labels == 1)}")
    logging.info(f"Number of points classified as vegetation (2): {np.sum(predicted_labels == 2)}")

    logging.info("--- Demo Complete ---")
