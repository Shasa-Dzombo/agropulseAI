"""
Drone Imagery Analysis System

Comprehensive drone-based agricultural monitoring:
- Photogrammetry and 3D reconstruction
- Orthomosaic generation
- Digital elevation models (DEM)
- Vegetation indices from drone imagery
- Precision agriculture mapping
- Plant counting and spacing analysis
- Crop height estimation
- Anomaly detection
- Flight planning and mission management

Integrates with consumer and professional agricultural drones.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image
import rasterio
from rasterio.transform import from_bounds
from scipy.spatial import Delaunay
from scipy.interpolate import griddata
from sklearn.cluster import DBSCAN
import open3d as o3d

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DroneImage:
    """Represents a single drone image with metadata"""
    
    def __init__(
        self,
        image_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.image_path = image_path
        self.image = None
        self.metadata = metadata or {}
        
        # EXIF data
        self.gps_coords: Optional[Tuple[float, float, float]] = None
        self.altitude: Optional[float] = None
        self.gimbal_angles: Optional[Tuple[float, float, float]] = None
        self.timestamp: Optional[datetime] = None
        
        self._load_image()
        self._extract_metadata()
    
    def _load_image(self) -> None:
        """Load image from file"""
        try:
            self.image = cv2.imread(self.image_path)
            if self.image is None:
                raise ValueError(f"Could not load image: {self.image_path}")
        except Exception as e:
            logger.error(f"Failed to load image: {e}")
    
    def _extract_metadata(self) -> None:
        """Extract metadata from EXIF data"""
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS, GPSTAGS
            
            pil_image = Image.open(self.image_path)
            exif_data = pil_image._getexif()
            
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    
                    if tag == "GPSInfo":
                        gps_data = {}
                        for gps_tag_id in value:
                            gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                            gps_data[gps_tag] = value[gps_tag_id]
                        
                        # Extract GPS coordinates
                        self.gps_coords = self._parse_gps_coords(gps_data)
                    
                    elif tag == "DateTime":
                        self.timestamp = datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                    
                    self.metadata[tag] = value
        
        except Exception as e:
            logger.warning(f"Could not extract EXIF metadata: {e}")
    
    def _parse_gps_coords(self, gps_data: Dict[str, Any]) -> Tuple[float, float, float]:
        """Parse GPS coordinates from EXIF"""
        def convert_to_degrees(value):
            d, m, s = value
            return d + (m / 60.0) + (s / 3600.0)
        
        lat = convert_to_degrees(gps_data.get("GPSLatitude", (0, 0, 0)))
        if gps_data.get("GPSLatitudeRef") == "S":
            lat = -lat
        
        lon = convert_to_degrees(gps_data.get("GPSLongitude", (0, 0, 0)))
        if gps_data.get("GPSLongitudeRef") == "W":
            lon = -lon
        
        alt = gps_data.get("GPSAltitude", 0)
        
        return (lat, lon, alt)


class FeatureExtractor:
    """Extract features for photogrammetry"""
    
    def __init__(self, feature_type: str = "sift"):
        """
        Initialize feature extractor
        
        Args:
            feature_type: Type of feature detector (sift, orb, akaze)
        """
        self.feature_type = feature_type
        
        if feature_type == "sift":
            self.detector = cv2.SIFT_create()
        elif feature_type == "orb":
            self.detector = cv2.ORB_create()
        elif feature_type == "akaze":
            self.detector = cv2.AKAZE_create()
        else:
            self.detector = cv2.SIFT_create()
    
    def extract_features(
        self,
        image: np.ndarray
    ) -> Tuple[List[cv2.KeyPoint], np.ndarray]:
        """
        Extract keypoints and descriptors from image
        
        Returns:
            Tuple of (keypoints, descriptors)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        keypoints, descriptors = self.detector.detectAndCompute(gray, None)
        
        return keypoints, descriptors
    
    def match_features(
        self,
        desc1: np.ndarray,
        desc2: np.ndarray,
        ratio_threshold: float = 0.75
    ) -> List[cv2.DMatch]:
        """
        Match features between two images using Lowe's ratio test
        
        Args:
            desc1: Descriptors from first image
            desc2: Descriptors from second image
            ratio_threshold: Ratio test threshold
        
        Returns:
            List of good matches
        """
        # Create matcher
        if self.feature_type == "orb" or self.feature_type == "akaze":
            matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        else:
            matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
        
        # Match descriptors
        matches = matcher.knnMatch(desc1, desc2, k=2)
        
        # Apply ratio test
        good_matches = []
        for match_pair in matches:
            if len(match_pair) == 2:
                m, n = match_pair
                if m.distance < ratio_threshold * n.distance:
                    good_matches.append(m)
        
        return good_matches


class PoseEstimator:
    """Estimate camera poses from matched features"""
    
    def __init__(self, camera_matrix: np.ndarray):
        """
        Initialize pose estimator
        
        Args:
            camera_matrix: 3x3 camera intrinsic matrix
        """
        self.camera_matrix = camera_matrix
    
    def estimate_pose(
        self,
        points1: np.ndarray,
        points2: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Estimate relative pose between two views
        
        Args:
            points1: Points in first image (Nx2)
            points2: Points in second image (Nx2)
        
        Returns:
            Tuple of (essential_matrix, rotation, translation)
        """
        # Compute essential matrix
        E, mask = cv2.findEssentialMat(
            points1,
            points2,
            self.camera_matrix,
            method=cv2.RANSAC,
            prob=0.999,
            threshold=1.0
        )
        
        # Recover pose
        _, R, t, mask = cv2.recoverPose(
            E,
            points1,
            points2,
            self.camera_matrix
        )
        
        return E, R, t
    
    def triangulate_points(
        self,
        points1: np.ndarray,
        points2: np.ndarray,
        P1: np.ndarray,
        P2: np.ndarray
    ) -> np.ndarray:
        """
        Triangulate 3D points from two views
        
        Args:
            points1: Points in first image (Nx2)
            points2: Points in second image (Nx2)
            P1: Projection matrix for first camera (3x4)
            P2: Projection matrix for second camera (3x4)
        
        Returns:
            3D points (Nx3)
        """
        # Triangulate
        points_4d = cv2.triangulatePoints(
            P1,
            P2,
            points1.T,
            points2.T
        )
        
        # Convert from homogeneous to 3D
        points_3d = points_4d[:3] / points_4d[3]
        
        return points_3d.T


class PointCloudProcessor:
    """Process and refine point clouds"""
    
    @staticmethod
    def create_point_cloud(
        points_3d: np.ndarray,
        colors: Optional[np.ndarray] = None
    ) -> o3d.geometry.PointCloud:
        """
        Create Open3D point cloud from numpy array
        
        Args:
            points_3d: 3D points (Nx3)
            colors: RGB colors (Nx3), values in [0, 1]
        
        Returns:
            Open3D point cloud
        """
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points_3d)
        
        if colors is not None:
            pcd.colors = o3d.utility.Vector3dVector(colors)
        
        return pcd
    
    @staticmethod
    def filter_outliers(
        pcd: o3d.geometry.PointCloud,
        nb_neighbors: int = 20,
        std_ratio: float = 2.0
    ) -> o3d.geometry.PointCloud:
        """
        Remove statistical outliers from point cloud
        
        Args:
            pcd: Input point cloud
            nb_neighbors: Number of neighbors to analyze
            std_ratio: Standard deviation ratio threshold
        
        Returns:
            Filtered point cloud
        """
        filtered_pcd, _ = pcd.remove_statistical_outlier(
            nb_neighbors=nb_neighbors,
            std_ratio=std_ratio
        )
        
        return filtered_pcd
    
    @staticmethod
    def downsample(
        pcd: o3d.geometry.PointCloud,
        voxel_size: float = 0.05
    ) -> o3d.geometry.PointCloud:
        """
        Downsample point cloud using voxel grid
        
        Args:
            pcd: Input point cloud
            voxel_size: Size of voxel for downsampling
        
        Returns:
            Downsampled point cloud
        """
        return pcd.voxel_down_sample(voxel_size=voxel_size)
    
    @staticmethod
    def estimate_normals(
        pcd: o3d.geometry.PointCloud,
        search_radius: float = 0.1,
        max_nn: int = 30
    ) -> o3d.geometry.PointCloud:
        """
        Estimate point cloud normals
        
        Args:
            pcd: Input point cloud
            search_radius: Search radius for normal estimation
            max_nn: Maximum number of neighbors
        
        Returns:
            Point cloud with normals
        """
        pcd.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(
                radius=search_radius,
                max_nn=max_nn
            )
        )
        
        # Orient normals consistently
        pcd.orient_normals_consistent_tangent_plane(k=15)
        
        return pcd


class MeshGenerator:
    """Generate 3D mesh from point cloud"""
    
    @staticmethod
    def poisson_reconstruction(
        pcd: o3d.geometry.PointCloud,
        depth: int = 9,
        scale: float = 1.1
    ) -> o3d.geometry.TriangleMesh:
        """
        Poisson surface reconstruction
        
        Args:
            pcd: Input point cloud with normals
            depth: Octree depth for reconstruction
            scale: Surface scale factor
        
        Returns:
            Triangle mesh
        """
        mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
            pcd,
            depth=depth,
            scale=scale
        )
        
        return mesh
    
    @staticmethod
    def ball_pivoting(
        pcd: o3d.geometry.PointCloud,
        radii: List[float]
    ) -> o3d.geometry.TriangleMesh:
        """
        Ball pivoting algorithm
        
        Args:
            pcd: Input point cloud with normals
            radii: List of radii for ball pivoting
        
        Returns:
            Triangle mesh
        """
        mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(
            pcd,
            o3d.utility.DoubleVector(radii)
        )
        
        return mesh
    
    @staticmethod
    def alpha_shape(
        pcd: o3d.geometry.PointCloud,
        alpha: float = 0.03
    ) -> o3d.geometry.TriangleMesh:
        """
        Alpha shape reconstruction
        
        Args:
            pcd: Input point cloud
            alpha: Alpha value
        
        Returns:
            Triangle mesh
        """
        mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_alpha_shape(
            pcd,
            alpha
        )
        
        return mesh


class OrthomosaicGenerator:
    """Generate georeferenced orthomosaics"""
    
    def __init__(self, output_resolution: float = 0.05):
        """
        Initialize orthomosaic generator
        
        Args:
            output_resolution: Output resolution in meters per pixel
        """
        self.output_resolution = output_resolution
    
    def generate_orthomosaic(
        self,
        images: List[DroneImage],
        dem: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Generate orthomosaic from drone images
        
        Args:
            images: List of drone images with GPS data
            dem: Optional digital elevation model
        
        Returns:
            Tuple of (orthomosaic_array, metadata)
        """
        # Find bounding box
        lats = [img.gps_coords[0] for img in images if img.gps_coords]
        lons = [img.gps_coords[1] for img in images if img.gps_coords]
        
        if not lats or not lons:
            raise ValueError("No GPS coordinates found in images")
        
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        
        # Calculate output dimensions
        lat_range = max_lat - min_lat
        lon_range = max_lon - min_lon
        
        # Approximate meters per degree
        meters_per_deg_lat = 111320
        meters_per_deg_lon = 111320 * np.cos(np.radians((min_lat + max_lat) / 2))
        
        height_m = lat_range * meters_per_deg_lat
        width_m = lon_range * meters_per_deg_lon
        
        output_height = int(height_m / self.output_resolution)
        output_width = int(width_m / self.output_resolution)
        
        # Initialize output arrays
        mosaic = np.zeros((output_height, output_width, 3), dtype=np.float32)
        weights = np.zeros((output_height, output_width), dtype=np.float32)
        
        # Project each image onto mosaic
        for image in images:
            if not image.gps_coords:
                continue
            
            lat, lon, alt = image.gps_coords
            
            # Calculate pixel position
            pixel_x = int((lon - min_lon) * meters_per_deg_lon / self.output_resolution)
            pixel_y = int((max_lat - lat) * meters_per_deg_lat / self.output_resolution)
            
            # Calculate footprint size based on altitude and FOV
            # Assuming 90° FOV and altitude in meters
            if alt > 0:
                footprint_size = alt * 2  # Simplified
                pixel_footprint = int(footprint_size / self.output_resolution)
            else:
                pixel_footprint = 100  # Default size
            
            # Resize and blend image
            resized = cv2.resize(
                image.image,
                (pixel_footprint, pixel_footprint)
            )
            
            # Calculate weight (distance from center)
            y_grid, x_grid = np.ogrid[:pixel_footprint, :pixel_footprint]
            center_y, center_x = pixel_footprint // 2, pixel_footprint // 2
            distance = np.sqrt((x_grid - center_x)**2 + (y_grid - center_y)**2)
            max_dist = np.sqrt(2 * (pixel_footprint // 2)**2)
            weight = 1.0 - (distance / max_dist)
            
            # Blend into mosaic
            y1 = max(0, pixel_y - pixel_footprint // 2)
            y2 = min(output_height, pixel_y + pixel_footprint // 2)
            x1 = max(0, pixel_x - pixel_footprint // 2)
            x2 = min(output_width, pixel_x + pixel_footprint // 2)
            
            crop_y1 = pixel_footprint // 2 - (pixel_y - y1)
            crop_y2 = crop_y1 + (y2 - y1)
            crop_x1 = pixel_footprint // 2 - (pixel_x - x1)
            crop_x2 = crop_x1 + (x2 - x1)
            
            if y2 > y1 and x2 > x1:
                mosaic[y1:y2, x1:x2] += resized[crop_y1:crop_y2, crop_x1:crop_x2] * weight[crop_y1:crop_y2, crop_x1:crop_x2, np.newaxis]
                weights[y1:y2, x1:x2] += weight[crop_y1:crop_y2, crop_x1:crop_x2]
        
        # Normalize by weights
        weights[weights == 0] = 1  # Avoid division by zero
        mosaic = mosaic / weights[:, :, np.newaxis]
        mosaic = np.clip(mosaic, 0, 255).astype(np.uint8)
        
        metadata = {
            "bounds": (min_lon, min_lat, max_lon, max_lat),
            "resolution": self.output_resolution,
            "width": output_width,
            "height": output_height,
            "crs": "EPSG:4326"
        }
        
        return mosaic, metadata
    
    def save_geotiff(
        self,
        mosaic: np.ndarray,
        metadata: Dict[str, Any],
        output_path: str
    ) -> None:
        """
        Save orthomosaic as GeoTIFF
        
        Args:
            mosaic: Orthomosaic array
            metadata: Metadata with bounds and CRS
            output_path: Output file path
        """
        bounds = metadata["bounds"]
        height, width = mosaic.shape[:2]
        
        transform = from_bounds(
            bounds[0], bounds[1], bounds[2], bounds[3],
            width, height
        )
        
        with rasterio.open(
            output_path,
            'w',
            driver='GTiff',
            height=height,
            width=width,
            count=3,
            dtype=mosaic.dtype,
            crs=metadata["crs"],
            transform=transform
        ) as dst:
            for i in range(3):
                dst.write(mosaic[:, :, i], i + 1)
        
        logger.info(f"Saved orthomosaic to {output_path}")


class DEMGenerator:
    """Generate Digital Elevation Model"""
    
    def __init__(self, resolution: float = 1.0):
        """
        Initialize DEM generator
        
        Args:
            resolution: Grid resolution in meters
        """
        self.resolution = resolution
    
    def generate_dem(
        self,
        point_cloud: np.ndarray
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Generate DEM from point cloud
        
        Args:
            point_cloud: Nx3 array of 3D points
        
        Returns:
            Tuple of (dem_array, metadata)
        """
        # Extract x, y, z
        x = point_cloud[:, 0]
        y = point_cloud[:, 1]
        z = point_cloud[:, 2]
        
        # Create grid
        x_min, x_max = x.min(), x.max()
        y_min, y_max = y.min(), y.max()
        
        grid_x = np.arange(x_min, x_max, self.resolution)
        grid_y = np.arange(y_min, y_max, self.resolution)
        
        grid_x, grid_y = np.meshgrid(grid_x, grid_y)
        
        # Interpolate elevations
        grid_z = griddata(
            (x, y),
            z,
            (grid_x, grid_y),
            method='cubic',
            fill_value=np.nan
        )
        
        metadata = {
            "bounds": (x_min, y_min, x_max, y_max),
            "resolution": self.resolution,
            "width": grid_z.shape[1],
            "height": grid_z.shape[0]
        }
        
        return grid_z, metadata
    
    def calculate_slope(self, dem: np.ndarray, resolution: float) -> np.ndarray:
        """
        Calculate slope from DEM
        
        Args:
            dem: Digital elevation model
            resolution: Grid resolution
        
        Returns:
            Slope array in degrees
        """
        # Calculate gradients
        dy, dx = np.gradient(dem, resolution)
        
        # Calculate slope
        slope = np.arctan(np.sqrt(dx**2 + dy**2))
        slope_degrees = np.degrees(slope)
        
        return slope_degrees
    
    def calculate_aspect(self, dem: np.ndarray, resolution: float) -> np.ndarray:
        """
        Calculate aspect from DEM
        
        Args:
            dem: Digital elevation model
            resolution: Grid resolution
        
        Returns:
            Aspect array in degrees (0-360)
        """
        # Calculate gradients
        dy, dx = np.gradient(dem, resolution)
        
        # Calculate aspect
        aspect = np.arctan2(dy, dx)
        aspect_degrees = np.degrees(aspect)
        
        # Convert to 0-360
        aspect_degrees = (90 - aspect_degrees) % 360
        
        return aspect_degrees


class VegetationAnalyzer:
    """Analyze vegetation from drone imagery"""
    
    def __init__(self):
        self.ndvi_cache: Dict[str, np.ndarray] = {}
    
    def calculate_ndvi(
        self,
        nir_band: np.ndarray,
        red_band: np.ndarray
    ) -> np.ndarray:
        """
        Calculate NDVI from drone multispectral imagery
        
        Args:
            nir_band: Near-infrared band
            red_band: Red band
        
        Returns:
            NDVI array
        """
        with np.errstate(divide='ignore', invalid='ignore'):
            ndvi = (nir_band - red_band) / (nir_band + red_band)
            ndvi = np.where(np.isfinite(ndvi), ndvi, 0)
        
        return ndvi
    
    def segment_crops(
        self,
        ndvi: np.ndarray,
        threshold: float = 0.3
    ) -> np.ndarray:
        """
        Segment crop areas from NDVI
        
        Args:
            ndvi: NDVI array
            threshold: NDVI threshold for vegetation
        
        Returns:
            Binary mask of crop areas
        """
        crop_mask = ndvi > threshold
        
        # Morphological operations to clean up
        kernel = np.ones((5, 5), np.uint8)
        crop_mask = cv2.morphologyEx(
            crop_mask.astype(np.uint8),
            cv2.MORPH_CLOSE,
            kernel
        )
        crop_mask = cv2.morphologyEx(
            crop_mask,
            cv2.MORPH_OPEN,
            kernel
        )
        
        return crop_mask.astype(bool)
    
    def count_plants(
        self,
        image: np.ndarray,
        min_area: int = 50,
        max_area: int = 5000
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Count individual plants in image
        
        Args:
            image: Input image
            min_area: Minimum plant area in pixels
            max_area: Maximum plant area in pixels
        
        Returns:
            Tuple of (plant_count, plant_details)
        """
        # Convert to HSV for better plant detection
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Create mask for green vegetation
        lower_green = np.array([25, 40, 40])
        upper_green = np.array([85, 255, 255])
        mask = cv2.inRange(hsv, lower_green, upper_green)
        
        # Find contours
        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        # Filter by area and analyze
        plants = []
        for contour in contours:
            area = cv2.contourArea(contour)
            
            if min_area < area < max_area:
                # Calculate properties
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                else:
                    cx, cy = 0, 0
                
                # Fit ellipse for plant shape
                if len(contour) >= 5:
                    ellipse = cv2.fitEllipse(contour)
                    (x, y), (w, h), angle = ellipse
                else:
                    w, h, angle = 0, 0, 0
                
                plants.append({
                    "center": (cx, cy),
                    "area": area,
                    "width": w,
                    "height": h,
                    "angle": angle
                })
        
        return len(plants), plants
    
    def estimate_plant_height(
        self,
        dem: np.ndarray,
        ground_elevation: float
    ) -> np.ndarray:
        """
        Estimate plant height from DEM
        
        Args:
            dem: Digital elevation model
            ground_elevation: Ground level elevation
        
        Returns:
            Plant height map
        """
        height = dem - ground_elevation
        height = np.maximum(height, 0)  # Negative heights to zero
        
        return height


class AnomalyDetector:
    """Detect anomalies in crop fields"""
    
    def detect_stress_areas(
        self,
        ndvi: np.ndarray,
        threshold_percentile: float = 10
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """
        Detect stressed crop areas from NDVI
        
        Args:
            ndvi: NDVI array
            threshold_percentile: Percentile below which areas are stressed
        
        Returns:
            Tuple of (stress_mask, stress_regions)
        """
        # Calculate threshold
        threshold = np.percentile(ndvi[ndvi > 0], threshold_percentile)
        
        # Create stress mask
        stress_mask = (ndvi < threshold) & (ndvi > 0)
        
        # Find connected components
        labeled, num_regions = cv2.connectedComponents(
            stress_mask.astype(np.uint8)
        )
        
        # Analyze regions
        stress_regions = []
        for region_id in range(1, num_regions + 1):
            region_mask = labeled == region_id
            area = np.sum(region_mask)
            
            if area > 100:  # Minimum area threshold
                # Find region center
                y_coords, x_coords = np.where(region_mask)
                center_y = int(np.mean(y_coords))
                center_x = int(np.mean(x_coords))
                
                # Calculate average NDVI in region
                avg_ndvi = np.mean(ndvi[region_mask])
                
                stress_regions.append({
                    "id": region_id,
                    "center": (center_x, center_y),
                    "area": area,
                    "avg_ndvi": avg_ndvi,
                    "severity": (threshold - avg_ndvi) / threshold
                })
        
        return stress_mask, stress_regions
    
    def detect_weeds(
        self,
        image: np.ndarray,
        crop_mask: np.ndarray
    ) -> np.ndarray:
        """
        Detect weeds between crop rows
        
        Args:
            image: Input image
            crop_mask: Mask of known crop areas
        
        Returns:
            Weed mask
        """
        # Convert to HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Detect all vegetation
        lower_green = np.array([25, 40, 40])
        upper_green = np.array([85, 255, 255])
        all_veg_mask = cv2.inRange(hsv, lower_green, upper_green)
        
        # Weeds are vegetation outside crop areas
        weed_mask = all_veg_mask & ~crop_mask
        
        return weed_mask


class FlightPlanner:
    """Plan autonomous drone missions"""
    
    def __init__(
        self,
        field_boundary: List[Tuple[float, float]],
        flight_altitude: float = 50.0,
        overlap_ratio: float = 0.75
    ):
        """
        Initialize flight planner
        
        Args:
            field_boundary: List of (lat, lon) coordinates
            flight_altitude: Flight altitude in meters
            overlap_ratio: Image overlap ratio (0-1)
        """
        self.field_boundary = field_boundary
        self.flight_altitude = flight_altitude
        self.overlap_ratio = overlap_ratio
    
    def generate_flight_path(
        self,
        camera_fov: float = 84.0,
        heading: float = 0.0
    ) -> List[Tuple[float, float, float]]:
        """
        Generate optimal flight path for field coverage
        
        Args:
            camera_fov: Camera field of view in degrees
            heading: Flight heading in degrees
        
        Returns:
            List of (lat, lon, alt) waypoints
        """
        # Calculate footprint size
        footprint_size = 2 * self.flight_altitude * np.tan(np.radians(camera_fov / 2))
        
        # Calculate line spacing
        line_spacing = footprint_size * (1 - self.overlap_ratio)
        
        # Find field bounding box
        lats = [coord[0] for coord in self.field_boundary]
        lons = [coord[1] for coord in self.field_boundary]
        
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        
        # Generate parallel flight lines
        waypoints = []
        
        # Calculate number of lines
        lat_range = max_lat - min_lat
        meters_per_deg_lat = 111320
        field_width = lat_range * meters_per_deg_lat
        num_lines = int(field_width / line_spacing) + 1
        
        # Generate waypoints
        for i in range(num_lines):
            offset = i * line_spacing / meters_per_deg_lat
            current_lat = min_lat + offset
            
            if i % 2 == 0:
                # Forward pass
                waypoints.append((current_lat, min_lon, self.flight_altitude))
                waypoints.append((current_lat, max_lon, self.flight_altitude))
            else:
                # Return pass
                waypoints.append((current_lat, max_lon, self.flight_altitude))
                waypoints.append((current_lat, min_lon, self.flight_altitude))
        
        return waypoints
    
    def estimate_flight_time(
        self,
        waypoints: List[Tuple[float, float, float]],
        cruise_speed: float = 10.0
    ) -> float:
        """
        Estimate total flight time
        
        Args:
            waypoints: List of waypoints
            cruise_speed: Cruise speed in m/s
        
        Returns:
            Estimated flight time in minutes
        """
        total_distance = 0.0
        
        for i in range(len(waypoints) - 1):
            # Calculate distance between waypoints
            lat1, lon1, alt1 = waypoints[i]
            lat2, lon2, alt2 = waypoints[i + 1]
            
            # Haversine formula for distance
            dlat = np.radians(lat2 - lat1)
            dlon = np.radians(lon2 - lon1)
            a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
            c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
            distance = 6371000 * c  # Earth radius in meters
            
            total_distance += distance
        
        flight_time_seconds = total_distance / cruise_speed
        flight_time_minutes = flight_time_seconds / 60
        
        return flight_time_minutes


class DroneAnalysisSystem:
    """Main coordinator for drone analysis"""
    
    def __init__(self):
        self.feature_extractor = FeatureExtractor("sift")
        self.point_cloud_processor = PointCloudProcessor()
        self.mesh_generator = MeshGenerator()
        self.orthomosaic_generator = OrthomosaicGenerator()
        self.dem_generator = DEMGenerator()
        self.vegetation_analyzer = VegetationAnalyzer()
        self.anomaly_detector = AnomalyDetector()
    
    def process_mission(
        self,
        image_paths: List[str],
        output_dir: str
    ) -> Dict[str, Any]:
        """
        Process complete drone mission
        
        Args:
            image_paths: Paths to drone images
            output_dir: Output directory
        
        Returns:
            Processing results
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Load images
        images = [DroneImage(path) for path in image_paths]
        logger.info(f"Loaded {len(images)} images")
        
        # Generate orthomosaic
        logger.info("Generating orthomosaic...")
        orthomosaic, metadata = self.orthomosaic_generator.generate_orthomosaic(images)
        orthomosaic_path = os.path.join(output_dir, "orthomosaic.tif")
        self.orthomosaic_generator.save_geotiff(orthomosaic, metadata, orthomosaic_path)
        
        # Mock vegetation analysis
        logger.info("Analyzing vegetation...")
        # (In real implementation, extract NIR and Red bands)
        mock_ndvi = np.random.rand(*orthomosaic.shape[:2]) * 0.8 + 0.1
        
        # Detect anomalies
        stress_mask, stress_regions = self.anomaly_detector.detect_stress_areas(mock_ndvi)
        logger.info(f"Detected {len(stress_regions)} stressed areas")
        
        results = {
            "num_images": len(images),
            "orthomosaic_path": orthomosaic_path,
            "orthomosaic_bounds": metadata["bounds"],
            "stressed_areas_count": len(stress_regions),
            "stressed_areas": stress_regions
        }
        
        return results


# Example usage
def example_usage():
    """Demonstrate drone analysis system"""
    
    system = DroneAnalysisSystem()
    
    # Mock image paths
    image_paths = [f"drone_image_{i}.jpg" for i in range(10)]
    
    # Flight planning
    field_boundary = [
        (42.0, -93.0),
        (42.0, -92.9),
        (42.1, -92.9),
        (42.1, -93.0)
    ]
    
    planner = FlightPlanner(field_boundary, flight_altitude=50)
    waypoints = planner.generate_flight_path()
    flight_time = planner.estimate_flight_time(waypoints)
    
    print(f"Flight plan: {len(waypoints)} waypoints")
    print(f"Estimated flight time: {flight_time:.1f} minutes")


if __name__ == "__main__":
    example_usage()
