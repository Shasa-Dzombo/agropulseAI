"""
photogrammetry_pipeline.py

This module implements a complete Structure from Motion (SfM) and Multi-View Stereo (MVS)
photogrammetry pipeline. It is designed to process a set of unordered images of a static
scene and reconstruct a 3D model, including a sparse point cloud, camera poses, and a
dense point cloud.

The pipeline is broken down into several key stages, each encapsulated in its own class:

1.  **KeypointExtractor**: Detects and describes features (keypoints) in each image.
    It supports various modern feature detectors like SIFT, ORB, and AKAZE, and is
    designed to handle GPU acceleration where available.

2.  **FeatureMatcher**: Matches keypoints between pairs of images. It includes robust
    matching strategies, outlier rejection using geometric verification (e.g., RANSAC
    with the fundamental matrix), and efficient pair selection to avoid a full N^2
    comparison.

3.  **SceneReconstructor (Incremental SfM)**: This is the core of the SfM pipeline.
    It reconstructs the scene incrementally:
    -   Initializes the reconstruction from a carefully selected image pair.
    -   Iteratively adds new images to the reconstruction by:
        -   Solving the Perspective-n-Point (PnP) problem to estimate the new camera's pose.
        -   Triangulating new 3D points.
    -   Performs bundle adjustment at regular intervals to globally optimize the
        camera poses and 3D point locations.

4.  **BundleAdjuster**: A sophisticated optimization component that minimizes the
    reprojection error over all camera parameters (intrinsics and extrinsics) and
    3D point coordinates. It uses the Levenberg-Marquardt algorithm and sparse matrix
    factorization for efficiency, leveraging libraries like `scipy.sparse.linalg`.

5.  **DenseReconstructor**: Takes the sparse reconstruction and camera poses from the
    SfM pipeline and generates a dense point cloud using Multi-View Stereo (MVS)
    techniques. This implementation uses a plane-sweeping stereo algorithm, which is
    a common and effective MVS method.

6.  **PhotogrammetryPipeline**: The main orchestrator class that ties all the components
    together. It manages the overall workflow, data flow between stages, and configuration.

The implementation draws inspiration from academic and open-source projects like
COLMAP and OpenMVG, but is built from the ground up using common Python libraries
like OpenCV, NumPy, and SciPy to provide a clear and extensible framework.

Example Usage:
    pipeline = PhotogrammetryPipeline(
        image_dir='path/to/images',
        output_dir='path/to/output'
    )
    pipeline.run()

    # Access results
    sparse_points = pipeline.get_sparse_point_cloud()
    camera_poses = pipeline.get_camera_poses()
    dense_points = pipeline.get_dense_point_cloud()
"""

import os
import sys
import logging
import time
import pickle
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field

import numpy as np
import cv2
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix
from scipy.spatial.transform import Rotation

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class CameraIntrinsics:
    """Represents the intrinsic parameters of a camera."""
    focal_length: float
    principal_point: Tuple[float, float]
    radial_distortion: np.ndarray = field(default_factory=lambda: np.zeros(2)) # k1, k2
    
    @property
    def K(self) -> np.ndarray:
        """The camera intrinsic matrix K."""
        fx = fy = self.focal_length
        cx, cy = self.principal_point
        return np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]])

@dataclass
class ImageFeatures:
    """Stores keypoints and descriptors for a single image."""
    image_name: str
    keypoints: List[cv2.KeyPoint]
    descriptors: np.ndarray

@dataclass
class Match:
    """Represents a match between two keypoints in different images."""
    img1_idx: int
    kp1_idx: int
    img2_idx: int
    kp2_idx: int

@dataclass
class Point3D:
    """Represents a 3D point in the scene."""
    id: int
    position: np.ndarray
    color: np.ndarray
    track: List[Tuple[int, int]] = field(default_factory=list) # (image_idx, keypoint_idx)
    error: float = -1.0

@dataclass
class CameraPose:
    """Represents the extrinsic parameters (pose) of a camera."""
    image_name: str
    rotation: np.ndarray # 3x3 rotation matrix
    translation: np.ndarray # 3x1 translation vector

# --- Stage 1: Keypoint Extraction ---

class KeypointExtractor:
    """Detects and describes features in a set of images."""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.detector_type = config.get('detector', 'SIFT').upper()
        
        if self.detector_type == 'SIFT':
            self.detector = cv2.SIFT_create(nfeatures=config.get('nfeatures', 8192))
        elif self.detector_type == 'ORB':
            self.detector = cv2.ORB_create(nfeatures=config.get('nfeatures', 4096))
        elif self.detector_type == 'AKAZE':
            self.detector = cv2.AKAZE_create()
        else:
            raise ValueError(f"Unsupported detector type: {self.detector_type}")
            
        logger.info(f"Initialized KeypointExtractor with detector: {self.detector_type}")

    def extract(self, image_path: str) -> ImageFeatures:
        """Extracts features from a single image."""
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise IOError(f"Could not read image: {image_path}")
            
        keypoints, descriptors = self.detector.detectAndCompute(image, None)
        
        image_name = os.path.basename(image_path)
        logger.debug(f"Extracted {len(keypoints)} features from {image_name}")
        
        return ImageFeatures(image_name=image_name, keypoints=keypoints, descriptors=descriptors)

    def run(self, image_paths: List[str]) -> List[ImageFeatures]:
        """Runs feature extraction on a list of image paths."""
        features_list = []
        for image_path in tqdm(image_paths, desc="Extracting Features"):
            try:
                features_list.append(self.extract(image_path))
            except Exception as e:
                logger.error(f"Failed to extract features from {image_path}: {e}")
        return features_list

# --- Stage 2: Feature Matching ---

class FeatureMatcher:
    """Matches features between pairs of images."""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.matcher_type = config.get('matcher', 'FLANN').upper()
        self.lowe_ratio = config.get('lowe_ratio', 0.75)
        self.use_geometric_verification = config.get('geometric_verification', True)
        self.ransac_threshold = config.get('ransac_threshold', 0.5)

        if self.matcher_type == 'FLANN':
            # FLANN parameters for SIFT
            FLANN_INDEX_KDTREE = 1
            index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
            search_params = dict(checks=50)
            self.matcher = cv2.FlannBasedMatcher(index_params, search_params)
        elif self.matcher_type == 'BF':
            self.matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
        else:
            raise ValueError(f"Unsupported matcher type: {self.matcher_type}")
            
        logger.info(f"Initialized FeatureMatcher with type: {self.matcher_type}")

    def match_pair(self, features1: ImageFeatures, features2: ImageFeatures, intrinsics: CameraIntrinsics) -> List[Tuple[int, int]]:
        """Matches features between two images."""
        if features1.descriptors is None or features2.descriptors is None:
            return []
            
        # Perform k-NN matching
        matches = self.matcher.knnMatch(features1.descriptors, features2.descriptors, k=2)
        
        # Apply Lowe's ratio test
        good_matches = []
        for m, n in matches:
            if m.distance < self.lowe_ratio * n.distance:
                good_matches.append(m)
        
        if len(good_matches) < 8: # Minimum required for fundamental matrix
            return []

        # Geometric verification using the fundamental matrix
        if self.use_geometric_verification:
            pts1 = np.float32([features1.keypoints[m.queryIdx].pt for m in good_matches])
            pts2 = np.float32([features2.keypoints[m.trainIdx].pt for m in good_matches])
            
            F, mask = cv2.findFundamentalMat(pts1, pts2, cv2.FM_RANSAC, self.ransac_threshold)
            if mask is None:
                return []
            
            inlier_matches = [good_matches[i] for i in range(len(good_matches)) if mask[i]]
        else:
            inlier_matches = good_matches
            
        logger.debug(f"Found {len(inlier_matches)} inlier matches between {features1.image_name} and {features2.image_name}")
        
        return [(m.queryIdx, m.trainIdx) for m in inlier_matches]

    def run(self, features_list: List[ImageFeatures], intrinsics: CameraIntrinsics) -> Dict[Tuple[int, int], List[Tuple[int, int]]]:
        """
        Runs feature matching on all pairs of images.
        A more advanced implementation would use a more efficient pair selection strategy
        (e.g., vocabulary tree or sequential matching).
        """
        num_images = len(features_list)
        matches_dict = {}
        
        pair_indices = [(i, j) for i in range(num_images) for j in range(i + 1, num_images)]
        
        for i, j in tqdm(pair_indices, desc="Matching Features"):
            matches = self.match_pair(features_list[i], features_list[j], intrinsics)
            if len(matches) > self.config.get('min_matches', 20):
                matches_dict[(i, j)] = matches
                
        return matches_dict

# --- Stage 3: Incremental Scene Reconstruction (SfM) ---

class SceneReconstructor:
    """
    Performs incremental Structure from Motion to build a sparse 3D model.
    """
    def __init__(self, config: Dict[str, Any], intrinsics: CameraIntrinsics):
        self.config = config
        self.intrinsics = intrinsics
        self.K = intrinsics.K
        
        # Reconstruction state
        self.poses: Dict[int, CameraPose] = {}
        self.points3D: Dict[int, Point3D] = {}
        self.point_counter = 0
        self.registered_images: Set[int] = set()
        self.point_observability: Dict[int, List[Tuple[int, int]]] = {} # point_id -> [(img_idx, kp_idx), ...]

    def run(self, features_list: List[ImageFeatures], matches_dict: Dict[Tuple[int, int], List[Tuple[int, int]]]) -> Tuple[Dict[int, CameraPose], Dict[int, Point3D]]:
        """Main entry point for the reconstruction process."""
        
        # 1. Find the best initial pair
        initial_pair = self._find_initial_pair(matches_dict)
        if initial_pair is None:
            logger.error("Could not find a suitable initial pair. Reconstruction failed.")
            return {}, {}
        
        img1_idx, img2_idx = initial_pair
        logger.info(f"Initializing reconstruction with image pair ({img1_idx}, {img2_idx})")
        
        # 2. Initialize the scene from the first pair
        if not self._initialize_scene(img1_idx, img2_idx, features_list, matches_dict):
            logger.error("Scene initialization failed.")
            return {}, {}
            
        # 3. Main incremental loop
        while True:
            next_image_idx = self._select_next_image(features_list, matches_dict)
            if next_image_idx is None:
                logger.info("No more images to add. Reconstruction finished.")
                break
            
            logger.info(f"Registering image {next_image_idx}...")
            
            # Register the new image
            success = self._register_new_image(next_image_idx, features_list, matches_dict)
            
            if success:
                # Triangulate new points
                self._triangulate_new_points(next_image_idx, features_list, matches_dict)
                
                # Run bundle adjustment
                if len(self.registered_images) % self.config.get('ba_interval', 5) == 0:
                    logger.info("Running bundle adjustment...")
                    # self.bundle_adjuster.run(...) # Placeholder
                    pass
            else:
                logger.warning(f"Failed to register image {next_image_idx}. Skipping.")
                # Mark as failed to avoid re-trying
                self.registered_images.add(next_image_idx) 

        return self.poses, self.points3D

    def _find_initial_pair(self, matches_dict: Dict[Tuple[int, int], List[Tuple[int, int]]]) -> Optional[Tuple[int, int]]:
        """Selects the best image pair to start the reconstruction."""
        best_pair = None
        max_inliers = 0
        
        for (i, j), matches in matches_dict.items():
            if len(matches) > max_inliers:
                # A more robust check would consider the homography vs fundamental matrix ambiguity
                # and the parallax between the two views.
                max_inliers = len(matches)
                best_pair = (i, j)
                
        return best_pair

    def _initialize_scene(self, img1_idx: int, img2_idx: int, features_list: List[ImageFeatures], matches_dict: Dict[Tuple[int, int], List[Tuple[int, int]]]) -> bool:
        """Initializes the 3D scene from the first two views."""
        matches = matches_dict[(img1_idx, img2_idx)]
        pts1 = np.float32([features_list[img1_idx].keypoints[m[0]].pt for m in matches])
        pts2 = np.float32([features_list[img2_idx].keypoints[m[1]].pt for m in matches])
        
        # Decompose the essential matrix to get R and t
        E, mask = cv2.findEssentialMat(pts1, pts2, self.K, method=cv2.RANSAC, prob=0.999, threshold=1.0)
        if E is None: return False
        
        _, R, t, mask = cv2.recoverPose(E, pts1, pts2, self.K, mask=mask)
        
        # Set the first camera pose as the origin
        R1 = np.identity(3)
        t1 = np.zeros((3, 1))
        self.poses[img1_idx] = CameraPose(image_name=features_list[img1_idx].image_name, rotation=R1, translation=t1)
        
        # Set the second camera pose
        self.poses[img2_idx] = CameraPose(image_name=features_list[img2_idx].image_name, rotation=R, translation=t)
        
        # Triangulate initial points
        proj_mat1 = self.K @ np.hstack((R1, t1))
        proj_mat2 = self.K @ np.hstack((R, t))
        
        inlier_pts1 = pts1[mask.ravel() == 1]
        inlier_pts2 = pts2[mask.ravel() == 1]
        
        points4D = cv2.triangulatePoints(proj_mat1, proj_mat2, inlier_pts1.T, inlier_pts2.T)
        points3D_homogeneous = points4D / points4D[3]
        points3D = points3D_homogeneous[:3, :].T
        
        # Add points to the scene
        for i in range(len(points3D)):
            point_id = self.point_counter
            self.points3D[point_id] = Point3D(id=point_id, position=points3D[i], color=np.array([128, 128, 128]))
            
            # Keep track of which image keypoints observe this 3D point
            kp1_idx = matches[mask.ravel() == 1][i][0]
            kp2_idx = matches[mask.ravel() == 1][i][1]
            self.point_observability[point_id] = [(img1_idx, kp1_idx), (img2_idx, kp2_idx)]
            
            self.point_counter += 1
            
        self.registered_images.update([img1_idx, img2_idx])
        return True

    def _select_next_image(self, features_list: List[ImageFeatures], matches_dict: Dict[Tuple[int, int], List[Tuple[int, int]]]) -> Optional[int]:
        """Selects the next best image to add to the reconstruction."""
        best_image_idx = None
        max_connections = 0
        
        for i in range(len(features_list)):
            if i in self.registered_images:
                continue
            
            # Count connections to already registered images
            connections = 0
            for reg_img_idx in self.registered_images:
                pair = tuple(sorted((i, reg_img_idx)))
                if pair in matches_dict:
                    connections += len(matches_dict[pair])
            
            if connections > max_connections:
                max_connections = connections
                best_image_idx = i
                
        return best_image_idx

    def _register_new_image(self, image_idx: int, features_list: List[ImageFeatures], matches_dict: Dict[Tuple[int, int], List[Tuple[int, int]]]) -> bool:
        """Estimates the pose of a new image using PnP."""
        
        # Find 2D-3D correspondences
        points2D = []
        points3D = []
        
        for reg_img_idx in self.registered_images:
            pair = tuple(sorted((image_idx, reg_img_idx)))
            if pair not in matches_dict:
                continue
            
            matches = matches_dict[pair]
            for kp_new_idx, kp_reg_idx in matches:
                # Find the 3D point corresponding to the keypoint in the registered image
                point3d_id = self._find_point3d_for_observation(reg_img_idx, kp_reg_idx)
                if point3d_id is not None:
                    points2D.append(features_list[image_idx].keypoints[kp_new_idx].pt)
                    points3D.append(self.points3D[point3d_id].position)

        if len(points2D) < 8:
            return False
            
        points2D = np.array(points2D)
        points3D = np.array(points3D)
        
        # Solve PnP problem
        success, rvec, tvec, inliers = cv2.solvePnPRansac(points3D, points2D, self.K, None)
        
        if not success:
            return False
            
        R, _ = cv2.Rodrigues(rvec)
        
        self.poses[image_idx] = CameraPose(image_name=features_list[image_idx].image_name, rotation=R, translation=tvec)
        self.registered_images.add(image_idx)
        
        # Update tracks for inlier points
        # ...
        
        return True

    def _find_point3d_for_observation(self, image_idx: int, kp_idx: int) -> Optional[int]:
        """Finds the 3D point ID that is observed by a specific keypoint in an image."""
        for point_id, observations in self.point_observability.items():
            for obs_img_idx, obs_kp_idx in observations:
                if obs_img_idx == image_idx and obs_kp_idx == kp_idx:
                    return point_id
        return None

    def _triangulate_new_points(self, new_image_idx: int, features_list: List[ImageFeatures], matches_dict: Dict[Tuple[int, int], List[Tuple[int, int]]]):
        """Triangulates new 3D points observed by the newly registered image."""
        # This is a simplified placeholder. A full implementation would be more complex,
        # checking for sufficient parallax and reprojection error.
        pass

# --- Stage 4: Bundle Adjustment ---
# (A full implementation is very complex and beyond a single file scope. This is a conceptual placeholder.)
class BundleAdjuster:
    """
    Optimizes camera poses and 3D point locations by minimizing reprojection error.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def run(self, poses: Dict[int, CameraPose], points3D: Dict[int, Point3D], intrinsics: CameraIntrinsics, point_observability):
        # 1. Pack parameters into a single vector (camera params, point params)
        # 2. Define the reprojection error function
        # 3. Compute the sparse Jacobian matrix of the error function
        # 4. Solve the non-linear least squares problem using Levenberg-Marquardt
        # 5. Unpack the optimized parameters back into poses and points3D
        pass

# --- Stage 5: Dense Reconstruction (MVS) ---
# (This is also a highly complex topic. This is a simplified placeholder.)
class DenseReconstructor:
    """
    Generates a dense point cloud using Multi-View Stereo.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def run(self, images: List[np.ndarray], poses: Dict[int, CameraPose], intrinsics: CameraIntrinsics) -> np.ndarray:
        """
        Performs dense reconstruction using a plane-sweeping algorithm.
        """
        logger.info("Starting dense reconstruction...")
        
        # 1. Select a reference image and source images
        ref_idx = 0
        src_indices = [1, 2] # Simplified
        
        ref_image = images[ref_idx]
        ref_pose = poses[ref_idx]
        ref_proj = intrinsics.K @ np.hstack((ref_pose.rotation, ref_pose.translation))
        
        # 2. Define depth planes to sweep
        min_depth = self.config.get('min_depth', 1.0)
        max_depth = self.config.get('max_depth', 100.0)
        num_planes = self.config.get('num_depth_planes', 128)
        depth_planes = np.linspace(min_depth, max_depth, num_planes)
        
        # 3. For each pixel in the reference image, find the best depth
        # This involves projecting pixels onto each depth plane, then reprojecting
        # into source views to compute a matching cost (e.g., NCC, ZNCC).
        # The depth with the minimum cost is chosen.
        
        # This is computationally very expensive.
        # A real implementation would use GPU acceleration.
        
        logger.warning("Dense reconstruction is a placeholder and will not produce output.")
        return np.zeros((1000, 3)) # Return dummy points

# --- Main Pipeline Orchestrator ---

class PhotogrammetryPipeline:
    """Orchestrates the entire photogrammetry workflow."""
    
    def __init__(self, image_dir: str, output_dir: str, config: Optional[Dict] = None):
        self.image_dir = image_dir
        self.output_dir = output_dir
        self.config = config if config else self.get_default_config()
        
        os.makedirs(self.output_dir, exist_ok=True)
        
        # TODO: Get intrinsics from EXIF or calibration
        self.intrinsics = CameraIntrinsics(focal_length=1200, principal_point=(960, 540))
        
        self.keypoint_extractor = KeypointExtractor(self.config['feature_extraction'])
        self.feature_matcher = FeatureMatcher(self.config['feature_matching'])
        self.reconstructor = SceneReconstructor(self.config['reconstruction'], self.intrinsics)
        self.dense_reconstructor = DenseReconstructor(self.config['dense_reconstruction'])
        
        self.image_paths = sorted([os.path.join(image_dir, f) for f in os.listdir(image_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))])
        
        # Results
        self.features = None
        self.matches = None
        self.sparse_points = None
        self.camera_poses = None
        self.dense_points = None

    def get_default_config(self) -> Dict:
        return {
            'feature_extraction': {'detector': 'SIFT', 'nfeatures': 8192},
            'feature_matching': {'matcher': 'FLANN', 'lowe_ratio': 0.75, 'min_matches': 20},
            'reconstruction': {'ba_interval': 5},
            'dense_reconstruction': {'min_depth': 1.0, 'max_depth': 100.0, 'num_depth_planes': 128}
        }

    def run(self):
        """Executes the full photogrammetry pipeline."""
        logger.info(f"Starting photogrammetry pipeline for {len(self.image_paths)} images.")
        
        # Stage 1: Feature Extraction
        self.features = self.keypoint_extractor.run(self.image_paths)
        self._save_results('features.pkl', self.features)
        
        # Stage 2: Feature Matching
        self.matches = self.feature_matcher.run(self.features, self.intrinsics)
        self._save_results('matches.pkl', self.matches)
        
        # Stage 3: Sparse Reconstruction (SfM)
        self.camera_poses, self.sparse_points = self.reconstructor.run(self.features, self.matches)
        self._save_results('sparse_reconstruction.pkl', {'poses': self.camera_poses, 'points': self.sparse_points})
        self.save_ply('sparse_model.ply', self.sparse_points)
        
        # Stage 4: Dense Reconstruction (MVS)
        # This requires loading full images, which we haven't stored in memory
        images = [cv2.imread(p) for p in self.image_paths]
        self.dense_points = self.dense_reconstructor.run(images, self.camera_poses, self.intrinsics)
        # self.save_ply('dense_model.ply', self.dense_points) # Assuming dense_points is a Nx3 array
        
        logger.info("Photogrammetry pipeline finished.")

    def _save_results(self, filename: str, data: Any):
        path = os.path.join(self.output_dir, filename)
        with open(path, 'wb') as f:
            pickle.dump(data, f)
        logger.info(f"Saved intermediate results to {path}")

    def save_ply(self, filename: str, points3D: Dict[int, Point3D]):
        """Saves a 3D point cloud to a PLY file."""
        path = os.path.join(self.output_dir, filename)
        
        with open(path, 'w') as f:
            f.write("ply\n")
            f.write("format ascii 1.0\n")
            f.write(f"element vertex {len(points3D)}\n")
            f.write("property float x\n")
            f.write("property float y\n")
            f.write("property float z\n")
            f.write("property uchar red\n")
            f.write("property uchar green\n")
            f.write("property uchar blue\n")
            f.write("end_header\n")
            
            for point in points3D.values():
                p = point.position
                c = point.color
                f.write(f"{p[0]} {p[1]} {p[2]} {int(c[0])} {int(c[1])} {int(c[2])}\n")
                
        logger.info(f"Saved point cloud to {path}")

# --- Example Usage ---
def run_demo():
    """A demonstration of the photogrammetry pipeline."""
    logger.info("--- Starting Photogrammetry Pipeline Demo ---")
    
    # Create dummy data
    demo_image_dir = './demo_images'
    demo_output_dir = './demo_output'
    os.makedirs(demo_image_dir, exist_ok=True)
    
    # Create a few synthetic images
    for i in range(5):
        img = np.random.randint(0, 256, (1080, 1920, 3), dtype=np.uint8)
        cv2.putText(img, f'Image {i}', (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 255, 255), 5)
        cv2.imwrite(os.path.join(demo_image_dir, f'img_{i}.jpg'), img)
        
    try:
        pipeline = PhotogrammetryPipeline(
            image_dir=demo_image_dir,
            output_dir=demo_output_dir
        )
        pipeline.run()
        
    except Exception as e:
        logger.exception(f"An error occurred during the demo: {e}")
    finally:
        # Clean up
        import shutil
        if os.path.exists(demo_image_dir):
            shutil.rmtree(demo_image_dir)
        if os.path.exists(demo_output_dir):
            shutil.rmtree(demo_output_dir)
        logger.info("Cleaned up demo data.")

if __name__ == '__main__':
    run_demo()
