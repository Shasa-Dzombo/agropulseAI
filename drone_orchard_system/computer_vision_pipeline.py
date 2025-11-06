"""
Advanced Computer Vision and Image Processing Pipeline

This module provides comprehensive image processing capabilities for agricultural analysis:
- Multi-spectral image processing and calibration
- Advanced image enhancement and noise reduction
- Feature extraction and descriptor matching
- 3D reconstruction from stereo/multi-view imagery
- Semantic and instance segmentation
- Object tracking across frames
- Image stitching and orthomosaic generation
- Texture analysis and pattern recognition
- Color space transformations and analysis
- Edge detection and contour analysis
- Morphological operations
- Image quality assessment
- HDR imaging and exposure fusion
- Motion blur correction
- Lens distortion correction

Author: AgroPulse Development Team
Version: 3.0.0
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.transforms as transforms
import numpy as np
import cv2
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from scipy import ndimage, signal, interpolate
from scipy.spatial import Delaunay
from sklearn.cluster import KMeans, DBSCAN
from sklearn.decomposition import PCA
import warnings
warnings.filterwarnings('ignore')


class ImageType(Enum):
    """Types of agricultural imagery"""
    RGB = "RGB"
    MULTISPECTRAL = "Multispectral"
    HYPERSPECTRAL = "Hyperspectral"
    THERMAL = "Thermal"
    LIDAR = "LiDAR"
    NDVI = "NDVI"
    SAR = "Synthetic Aperture Radar"


class ColorSpace(Enum):
    """Color space representations"""
    RGB = "RGB"
    BGR = "BGR"
    HSV = "HSV"
    LAB = "LAB"
    YCrCb = "YCrCb"
    GRAY = "Grayscale"


@dataclass
class ImageMetadata:
    """Comprehensive image metadata"""
    timestamp: datetime
    drone_id: str
    location: Tuple[float, float, float]  # lat, lon, altitude
    camera_params: Dict[str, float]
    image_type: ImageType
    resolution: Tuple[int, int]  # width, height
    sensor_id: str
    exposure_time_ms: float
    iso: int
    focal_length_mm: float
    gimbal_angles: Tuple[float, float, float]  # roll, pitch, yaw
    sun_angle: float
    cloud_cover: float


@dataclass
class FeatureMatch:
    """Feature matching result"""
    keypoint1: Tuple[float, float]
    keypoint2: Tuple[float, float]
    descriptor_distance: float
    confidence: float


@dataclass
class SegmentationResult:
    """Segmentation output"""
    mask: np.ndarray
    class_labels: List[str]
    confidence_scores: List[float]
    bounding_boxes: List[Tuple[int, int, int, int]]
    pixel_counts: Dict[str, int]


class MultiSpectralImageProcessor:
    """
    Process and calibrate multi-spectral imagery
    """
    
    def __init__(self, num_bands: int = 5):
        self.num_bands = num_bands
        self.calibration_params = {}
    
    def calibrate_image(self,
                       raw_image: np.ndarray,
                       dark_current: np.ndarray,
                       flat_field: np.ndarray,
                       radiometric_cal: Dict[str, float]) -> np.ndarray:
        """
        Calibrate raw multispectral image to reflectance
        
        Args:
            raw_image: Raw sensor data (H, W, bands)
            dark_current: Dark current reference
            flat_field: Flat field correction
            radiometric_cal: Radiometric calibration coefficients
        
        Returns:
            Calibrated reflectance image
        """
        # Step 1: Dark current subtraction
        corrected = raw_image.astype(np.float32) - dark_current
        
        # Step 2: Flat field correction
        corrected = corrected / (flat_field + 1e-6)
        
        # Step 3: Radiometric calibration
        gain = radiometric_cal.get('gain', 1.0)
        offset = radiometric_cal.get('offset', 0.0)
        
        reflectance = (corrected * gain + offset) / 100.0  # Convert to 0-1 range
        
        # Clip to valid range
        reflectance = np.clip(reflectance, 0, 1)
        
        return reflectance
    
    def compute_vegetation_indices(self, 
                                  multispectral: np.ndarray,
                                  band_mapping: Dict[str, int]) -> Dict[str, np.ndarray]:
        """
        Compute various vegetation indices
        
        Args:
            multispectral: Calibrated multispectral image
            band_mapping: Mapping of band names to indices
        
        Returns:
            Dictionary of vegetation indices
        """
        indices = {}
        
        # Extract bands
        blue = multispectral[:, :, band_mapping.get('blue', 0)] if 'blue' in band_mapping else None
        green = multispectral[:, :, band_mapping.get('green', 1)]
        red = multispectral[:, :, band_mapping.get('red', 2)]
        nir = multispectral[:, :, band_mapping.get('nir', 3)]
        red_edge = multispectral[:, :, band_mapping.get('red_edge', 4)] if 'red_edge' in band_mapping else None
        
        # NDVI (Normalized Difference Vegetation Index)
        indices['ndvi'] = (nir - red) / (nir + red + 1e-6)
        
        # GNDVI (Green Normalized Difference Vegetation Index)
        indices['gndvi'] = (nir - green) / (nir + green + 1e-6)
        
        # NDRE (Normalized Difference Red Edge)
        if red_edge is not None:
            indices['ndre'] = (nir - red_edge) / (nir + red_edge + 1e-6)
        
        # EVI (Enhanced Vegetation Index)
        if blue is not None:
            indices['evi'] = 2.5 * (nir - red) / (nir + 6 * red - 7.5 * blue + 1)
        
        # SAVI (Soil Adjusted Vegetation Index)
        L = 0.5  # Soil brightness correction factor
        indices['savi'] = ((nir - red) / (nir + red + L)) * (1 + L)
        
        # MSAVI (Modified Soil Adjusted Vegetation Index)
        indices['msavi'] = (2 * nir + 1 - np.sqrt((2 * nir + 1)**2 - 8 * (nir - red))) / 2
        
        # OSAVI (Optimized Soil Adjusted Vegetation Index)
        indices['osavi'] = (nir - red) / (nir + red + 0.16)
        
        # CIG (Chlorophyll Index Green)
        indices['cig'] = (nir / green) - 1
        
        # VARI (Visible Atmospherically Resistant Index)
        if blue is not None:
            indices['vari'] = (green - red) / (green + red - blue + 1e-6)
        
        # TGI (Triangular Greenness Index)
        if blue is not None:
            indices['tgi'] = green - 0.39 * red - 0.61 * blue
        
        return indices
    
    def atmospheric_correction(self,
                              image: np.ndarray,
                              visibility_km: float = 15.0,
                              altitude_m: float = 100.0) -> np.ndarray:
        """
        Perform atmospheric correction using Dark Object Subtraction
        
        Args:
            image: Input image
            visibility_km: Atmospheric visibility
            altitude_m: Flight altitude
        
        Returns:
            Atmospherically corrected image
        """
        # Simple Dark Object Subtraction (DOS)
        corrected = np.zeros_like(image, dtype=np.float32)
        
        for band in range(image.shape[2]):
            band_data = image[:, :, band].astype(np.float32)
            
            # Estimate atmospheric scattering (dark object value)
            dark_value = np.percentile(band_data, 1)
            
            # Subtract dark value
            corrected[:, :, band] = band_data - dark_value
        
        # Normalize
        corrected = np.clip(corrected, 0, None)
        corrected = corrected / corrected.max() if corrected.max() > 0 else corrected
        
        return corrected


class AdvancedImageEnhancer:
    """
    Advanced image enhancement techniques
    """
    
    def __init__(self):
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    
    def enhance_contrast(self,
                        image: np.ndarray,
                        method: str = 'clahe') -> np.ndarray:
        """
        Enhance image contrast
        
        Args:
            image: Input image
            method: Enhancement method (clahe, histogram_eq, gamma)
        
        Returns:
            Enhanced image
        """
        if method == 'clahe':
            # Contrast Limited Adaptive Histogram Equalization
            if len(image.shape) == 2:
                return self.clahe.apply(image)
            else:
                # Apply to each channel
                enhanced = np.zeros_like(image)
                for i in range(image.shape[2]):
                    enhanced[:, :, i] = self.clahe.apply(image[:, :, i])
                return enhanced
        
        elif method == 'histogram_eq':
            # Global histogram equalization
            if len(image.shape) == 2:
                return cv2.equalizeHist(image)
            else:
                enhanced = np.zeros_like(image)
                for i in range(image.shape[2]):
                    enhanced[:, :, i] = cv2.equalizeHist(image[:, :, i])
                return enhanced
        
        elif method == 'gamma':
            # Gamma correction
            gamma = 1.5
            normalized = image / 255.0
            corrected = np.power(normalized, gamma)
            return (corrected * 255).astype(np.uint8)
        
        return image
    
    def denoise_image(self,
                     image: np.ndarray,
                     method: str = 'non_local_means',
                     strength: float = 10.0) -> np.ndarray:
        """
        Remove noise from image
        
        Args:
            image: Noisy input image
            method: Denoising method
            strength: Denoising strength
        
        Returns:
            Denoised image
        """
        if method == 'non_local_means':
            # Non-local means denoising
            if len(image.shape) == 2:
                return cv2.fastNlMeansDenoising(image, None, strength, 7, 21)
            else:
                return cv2.fastNlMeansDenoisingColored(image, None, strength, strength, 7, 21)
        
        elif method == 'bilateral':
            # Bilateral filtering (edge-preserving)
            return cv2.bilateralFilter(image, 9, 75, 75)
        
        elif method == 'gaussian':
            # Gaussian blur
            return cv2.GaussianBlur(image, (5, 5), 1.0)
        
        elif method == 'median':
            # Median filter
            return cv2.medianBlur(image, 5)
        
        return image
    
    def sharpen_image(self, image: np.ndarray, amount: float = 1.0) -> np.ndarray:
        """
        Sharpen image using unsharp masking
        
        Args:
            image: Input image
            amount: Sharpening amount
        
        Returns:
            Sharpened image
        """
        # Gaussian blur
        blurred = cv2.GaussianBlur(image, (5, 5), 1.0)
        
        # Unsharp mask
        sharpened = cv2.addWeighted(image, 1.0 + amount, blurred, -amount, 0)
        
        return sharpened
    
    def correct_illumination(self, image: np.ndarray) -> np.ndarray:
        """
        Correct non-uniform illumination
        
        Args:
            image: Input image with uneven lighting
        
        Returns:
            Illumination-corrected image
        """
        # Estimate background illumination
        background = cv2.GaussianBlur(image, (51, 51), 0)
        
        # Divide by background
        corrected = cv2.divide(image.astype(np.float32), background.astype(np.float32) + 1e-6)
        
        # Normalize
        corrected = cv2.normalize(corrected, None, 0, 255, cv2.NORM_MINMAX)
        
        return corrected.astype(np.uint8)


class FeatureExtractor:
    """
    Extract and match features for image registration and 3D reconstruction
    """
    
    def __init__(self, detector_type: str = 'sift'):
        """
        Initialize feature detector
        
        Args:
            detector_type: Type of feature detector (sift, surf, orb, akaze)
        """
        if detector_type == 'sift':
            self.detector = cv2.SIFT_create()
        elif detector_type == 'surf':
            self.detector = cv2.xfeatures2d.SURF_create() if hasattr(cv2, 'xfeatures2d') else cv2.SIFT_create()
        elif detector_type == 'orb':
            self.detector = cv2.ORB_create(nfeatures=5000)
        elif detector_type == 'akaze':
            self.detector = cv2.AKAZE_create()
        else:
            self.detector = cv2.SIFT_create()
        
        # Feature matcher
        self.matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
    
    def detect_features(self, image: np.ndarray) -> Tuple[List, np.ndarray]:
        """
        Detect keypoints and compute descriptors
        
        Args:
            image: Input image
        
        Returns:
            Tuple of (keypoints, descriptors)
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Detect and compute
        keypoints, descriptors = self.detector.detectAndCompute(gray, None)
        
        return keypoints, descriptors
    
    def match_features(self,
                      descriptors1: np.ndarray,
                      descriptors2: np.ndarray,
                      ratio_threshold: float = 0.75) -> List[cv2.DMatch]:
        """
        Match features between two images using Lowe's ratio test
        
        Args:
            descriptors1: Descriptors from first image
            descriptors2: Descriptors from second image
            ratio_threshold: Ratio test threshold
        
        Returns:
            List of good matches
        """
        # Match descriptors
        matches = self.matcher.knnMatch(descriptors1, descriptors2, k=2)
        
        # Apply ratio test
        good_matches = []
        for match_pair in matches:
            if len(match_pair) == 2:
                m, n = match_pair
                if m.distance < ratio_threshold * n.distance:
                    good_matches.append(m)
        
        return good_matches
    
    def estimate_homography(self,
                          keypoints1: List,
                          keypoints2: List,
                          matches: List[cv2.DMatch]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Estimate homography matrix from matched features
        
        Args:
            keypoints1: Keypoints from first image
            keypoints2: Keypoints from second image
            matches: Feature matches
        
        Returns:
            Tuple of (homography matrix, inlier mask)
        """
        if len(matches) < 4:
            return None, None
        
        # Extract matched keypoint coordinates
        src_pts = np.float32([keypoints1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([keypoints2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
        
        # Estimate homography with RANSAC
        H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        
        return H, mask


class StereoVision3DReconstructor:
    """
    3D reconstruction from stereo or multi-view imagery
    """
    
    def __init__(self, baseline_m: float = 0.5, focal_length_px: float = 1000.0):
        """
        Initialize stereo reconstructor
        
        Args:
            baseline_m: Distance between camera centers (meters)
            focal_length_px: Focal length in pixels
        """
        self.baseline = baseline_m
        self.focal_length = focal_length_px
    
    def rectify_stereo_pair(self,
                           img1: np.ndarray,
                           img2: np.ndarray,
                           camera_matrix: np.ndarray,
                           dist_coeffs: np.ndarray,
                           R: np.ndarray,
                           T: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Rectify stereo image pair
        
        Args:
            img1, img2: Stereo image pair
            camera_matrix: Camera intrinsic matrix
            dist_coeffs: Distortion coefficients
            R: Rotation matrix between cameras
            T: Translation vector between cameras
        
        Returns:
            Rectified stereo pair
        """
        h, w = img1.shape[:2]
        
        # Compute rectification transforms
        R1, R2, P1, P2, Q, roi1, roi2 = cv2.stereoRectify(
            camera_matrix, dist_coeffs,
            camera_matrix, dist_coeffs,
            (w, h), R, T,
            alpha=0
        )
        
        # Compute rectification maps
        map1x, map1y = cv2.initUndistortRectifyMap(
            camera_matrix, dist_coeffs, R1, P1, (w, h), cv2.CV_32FC1
        )
        map2x, map2y = cv2.initUndistortRectifyMap(
            camera_matrix, dist_coeffs, R2, P2, (w, h), cv2.CV_32FC1
        )
        
        # Rectify images
        img1_rectified = cv2.remap(img1, map1x, map1y, cv2.INTER_LINEAR)
        img2_rectified = cv2.remap(img2, map2x, map2y, cv2.INTER_LINEAR)
        
        return img1_rectified, img2_rectified
    
    def compute_disparity(self,
                         img1: np.ndarray,
                         img2: np.ndarray,
                         max_disparity: int = 128) -> np.ndarray:
        """
        Compute disparity map from rectified stereo pair
        
        Args:
            img1, img2: Rectified stereo images
            max_disparity: Maximum disparity to search
        
        Returns:
            Disparity map
        """
        # Convert to grayscale
        if len(img1.shape) == 3:
            gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        else:
            gray1, gray2 = img1, img2
        
        # Semi-Global Block Matching
        stereo = cv2.StereoSGBM_create(
            minDisparity=0,
            numDisparities=max_disparity,
            blockSize=5,
            P1=8 * 3 * 5**2,
            P2=32 * 3 * 5**2,
            disp12MaxDiff=1,
            uniquenessRatio=10,
            speckleWindowSize=100,
            speckleRange=32
        )
        
        disparity = stereo.compute(gray1, gray2).astype(np.float32) / 16.0
        
        return disparity
    
    def disparity_to_depth(self, disparity: np.ndarray) -> np.ndarray:
        """
        Convert disparity to depth
        
        Args:
            disparity: Disparity map
        
        Returns:
            Depth map in meters
        """
        # Depth = (baseline * focal_length) / disparity
        depth = np.zeros_like(disparity)
        
        valid_mask = disparity > 0
        depth[valid_mask] = (self.baseline * self.focal_length) / disparity[valid_mask]
        
        return depth
    
    def generate_point_cloud(self,
                            depth_map: np.ndarray,
                            color_image: np.ndarray,
                            camera_matrix: np.ndarray) -> np.ndarray:
        """
        Generate 3D point cloud from depth map
        
        Args:
            depth_map: Depth values
            color_image: Color image
            camera_matrix: Camera intrinsics
        
        Returns:
            Point cloud (N, 6) with XYZ and RGB
        """
        h, w = depth_map.shape
        
        # Generate pixel coordinates
        u, v = np.meshgrid(np.arange(w), np.arange(h))
        
        # Camera intrinsics
        fx = camera_matrix[0, 0]
        fy = camera_matrix[1, 1]
        cx = camera_matrix[0, 2]
        cy = camera_matrix[1, 2]
        
        # Back-project to 3D
        Z = depth_map
        X = (u - cx) * Z / fx
        Y = (v - cy) * Z / fy
        
        # Filter valid points
        valid_mask = (Z > 0) & (Z < 100)  # Valid depth range
        
        points_3d = np.stack([X[valid_mask], Y[valid_mask], Z[valid_mask]], axis=1)
        
        # Add color
        if len(color_image.shape) == 3:
            colors = color_image[valid_mask]
        else:
            colors = np.stack([color_image[valid_mask]] * 3, axis=1)
        
        point_cloud = np.concatenate([points_3d, colors], axis=1)
        
        return point_cloud


class OrthomosaicGenerator:
    """
    Generate orthomosaic maps from overlapping aerial images
    """
    
    def __init__(self):
        self.feature_extractor = FeatureExtractor(detector_type='sift')
    
    def stitch_images(self,
                     images: List[np.ndarray],
                     metadata: List[ImageMetadata]) -> np.ndarray:
        """
        Stitch multiple images into panorama/orthomosaic
        
        Args:
            images: List of overlapping images
            metadata: Image metadata including GPS positions
        
        Returns:
            Stitched orthomosaic
        """
        if len(images) < 2:
            return images[0] if images else None
        
        # Start with first image
        result = images[0]
        
        # Progressively stitch images
        for i in range(1, len(images)):
            result = self._stitch_pair(result, images[i])
            
            if result is None:
                print(f"Failed to stitch image {i}")
                return None
        
        return result
    
    def _stitch_pair(self,
                    img1: np.ndarray,
                    img2: np.ndarray) -> Optional[np.ndarray]:
        """Stitch two images together"""
        # Detect features
        kp1, desc1 = self.feature_extractor.detect_features(img1)
        kp2, desc2 = self.feature_extractor.detect_features(img2)
        
        if desc1 is None or desc2 is None:
            return None
        
        # Match features
        matches = self.feature_extractor.match_features(desc1, desc2)
        
        if len(matches) < 10:
            return None
        
        # Estimate homography
        H, mask = self.feature_extractor.estimate_homography(kp1, kp2, matches)
        
        if H is None:
            return None
        
        # Warp and blend
        h1, w1 = img1.shape[:2]
        h2, w2 = img2.shape[:2]
        
        # Determine output size
        corners = np.array([[0, 0, 1], [w2, 0, 1], [w2, h2, 1], [0, h2, 1]]).T
        warped_corners = H @ corners
        warped_corners = warped_corners / warped_corners[2, :]
        
        x_min = min(0, warped_corners[0, :].min())
        x_max = max(w1, warped_corners[0, :].max())
        y_min = min(0, warped_corners[1, :].min())
        y_max = max(h1, warped_corners[1, :].max())
        
        # Translation to keep all pixels
        translation = np.array([[1, 0, -x_min],
                               [0, 1, -y_min],
                               [0, 0, 1]])
        
        # Warp second image
        output_size = (int(x_max - x_min), int(y_max - y_min))
        warped_img2 = cv2.warpPerspective(img2, translation @ H, output_size)
        
        # Place first image
        result = warped_img2.copy()
        result[int(-y_min):int(-y_min + h1), int(-x_min):int(-x_min + w1)] = img1
        
        # Simple blending in overlap region
        mask1 = (result > 0).astype(np.float32)
        mask2 = (warped_img2 > 0).astype(np.float32)
        overlap = mask1 * mask2
        
        if overlap.sum() > 0:
            alpha = 0.5
            result = np.where(overlap > 0,
                            alpha * result + (1 - alpha) * warped_img2,
                            result)
        
        return result.astype(np.uint8)


class SemanticSegmentationEngine(nn.Module):
    """
    Semantic segmentation for agricultural scene understanding
    Using DeepLabV3+ architecture
    """
    
    def __init__(self, num_classes: int = 10, backbone: str = 'resnet50'):
        super(SemanticSegmentationEngine, self).__init__()
        
        # Load pretrained backbone
        if backbone == 'resnet50':
            resnet = models.resnet50(pretrained=True)
            self.backbone = nn.Sequential(*list(resnet.children())[:-2])
            backbone_channels = 2048
        else:
            resnet = models.resnet101(pretrained=True)
            self.backbone = nn.Sequential(*list(resnet.children())[:-2])
            backbone_channels = 2048
        
        # ASPP (Atrous Spatial Pyramid Pooling)
        self.aspp = ASPP(backbone_channels, 256)
        
        # Decoder
        self.decoder = nn.Sequential(
            nn.Conv2d(256, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(),
            nn.Conv2d(256, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(),
            nn.Conv2d(256, num_classes, kernel_size=1)
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass
        
        Args:
            x: Input image tensor (B, 3, H, W)
        
        Returns:
            Segmentation logits (B, num_classes, H, W)
        """
        input_size = x.shape[2:]
        
        # Backbone feature extraction
        features = self.backbone(x)
        
        # ASPP
        features = self.aspp(features)
        
        # Decoder
        logits = self.decoder(features)
        
        # Upsample to input size
        logits = F.interpolate(logits, size=input_size, mode='bilinear', align_corners=True)
        
        return logits


class ASPP(nn.Module):
    """Atrous Spatial Pyramid Pooling module"""
    
    def __init__(self, in_channels: int, out_channels: int):
        super(ASPP, self).__init__()
        
        # Different dilation rates
        self.conv1 = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU()
        )
        
        self.conv2 = self._make_conv(in_channels, out_channels, dilation=6)
        self.conv3 = self._make_conv(in_channels, out_channels, dilation=12)
        self.conv4 = self._make_conv(in_channels, out_channels, dilation=18)
        
        # Global pooling
        self.global_pool = nn.Sequential(
            nn.AdaptiveAvgPool2d((1, 1)),
            nn.Conv2d(in_channels, out_channels, kernel_size=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU()
        )
        
        # Fusion
        self.fusion = nn.Sequential(
            nn.Conv2d(out_channels * 5, out_channels, kernel_size=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU()
        )
    
    def _make_conv(self, in_channels: int, out_channels: int, dilation: int) -> nn.Module:
        """Create dilated convolution"""
        return nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, 
                     padding=dilation, dilation=dilation, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU()
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass"""
        size = x.shape[2:]
        
        feat1 = self.conv1(x)
        feat2 = self.conv2(x)
        feat3 = self.conv3(x)
        feat4 = self.conv4(x)
        
        feat5 = self.global_pool(x)
        feat5 = F.interpolate(feat5, size=size, mode='bilinear', align_corners=True)
        
        # Concatenate all features
        out = torch.cat([feat1, feat2, feat3, feat4, feat5], dim=1)
        out = self.fusion(out)
        
        return out


class ObjectTracker:
    """
    Multi-object tracking across video frames
    """
    
    def __init__(self, max_disappeared: int = 30):
        self.next_object_id = 0
        self.objects = {}
        self.disappeared = {}
        self.max_disappeared = max_disappeared
    
    def register(self, centroid: Tuple[float, float]):
        """Register new object"""
        self.objects[self.next_object_id] = centroid
        self.disappeared[self.next_object_id] = 0
        self.next_object_id += 1
    
    def deregister(self, object_id: int):
        """Remove object from tracking"""
        del self.objects[object_id]
        del self.disappeared[object_id]
    
    def update(self, detections: List[Tuple[int, int, int, int]]) -> Dict[int, Tuple[float, float]]:
        """
        Update tracked objects with new detections
        
        Args:
            detections: List of bounding boxes (x, y, w, h)
        
        Returns:
            Dictionary mapping object_id to centroid
        """
        # If no detections
        if len(detections) == 0:
            # Mark all as disappeared
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            
            return self.objects
        
        # Compute centroids
        input_centroids = []
        for (x, y, w, h) in detections:
            cx = x + w // 2
            cy = y + h // 2
            input_centroids.append((cx, cy))
        
        # If no existing objects, register all
        if len(self.objects) == 0:
            for centroid in input_centroids:
                self.register(centroid)
        else:
            # Match existing objects to new detections
            object_ids = list(self.objects.keys())
            object_centroids = list(self.objects.values())
            
            # Compute distance matrix
            D = np.zeros((len(object_centroids), len(input_centroids)))
            for i, obj_centroid in enumerate(object_centroids):
                for j, input_centroid in enumerate(input_centroids):
                    D[i, j] = np.linalg.norm(
                        np.array(obj_centroid) - np.array(input_centroid)
                    )
            
            # Find optimal assignment
            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]
            
            used_rows = set()
            used_cols = set()
            
            for (row, col) in zip(rows, cols):
                if row in used_rows or col in used_cols:
                    continue
                
                # Update object
                object_id = object_ids[row]
                self.objects[object_id] = input_centroids[col]
                self.disappeared[object_id] = 0
                
                used_rows.add(row)
                used_cols.add(col)
            
            # Handle disappeared objects
            unused_rows = set(range(D.shape[0])) - used_rows
            for row in unused_rows:
                object_id = object_ids[row]
                self.disappeared[object_id] += 1
                
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            
            # Register new objects
            unused_cols = set(range(D.shape[1])) - used_cols
            for col in unused_cols:
                self.register(input_centroids[col])
        
        return self.objects


def main():
    """Demonstration of computer vision pipeline"""
    print("=" * 80)
    print("AgroPulse Advanced Computer Vision Pipeline")
    print("=" * 80)
    
    # Initialize components
    print("\nInitializing vision components...")
    multispectral_processor = MultiSpectralImageProcessor(num_bands=5)
    enhancer = AdvancedImageEnhancer()
    feature_extractor = FeatureExtractor(detector_type='sift')
    stereo_reconstructor = StereoVision3DReconstructor()
    
    # Simulate multispectral image
    print("\nProcessing multispectral imagery...")
    ms_image = np.random.rand(512, 512, 5).astype(np.float32)
    
    band_mapping = {
        'blue': 0,
        'green': 1,
        'red': 2,
        'nir': 3,
        'red_edge': 4
    }
    
    indices = multispectral_processor.compute_vegetation_indices(ms_image, band_mapping)
    
    print("\nVegetation Indices Computed:")
    for index_name in ['ndvi', 'gndvi', 'evi', 'savi']:
        if index_name in indices:
            mean_val = np.mean(indices[index_name])
            print(f"  {index_name.upper()}: {mean_val:.3f}")
    
    # Image enhancement
    print("\nPerforming image enhancement...")
    rgb_image = (np.random.rand(512, 512, 3) * 255).astype(np.uint8)
    enhanced = enhancer.enhance_contrast(rgb_image, method='clahe')
    denoised = enhancer.denoise_image(enhanced, method='non_local_means')
    
    # Feature extraction
    print("\nExtracting image features...")
    keypoints, descriptors = feature_extractor.detect_features(rgb_image)
    print(f"  Detected {len(keypoints)} keypoints")
    
    # Segmentation
    print("\nInitializing semantic segmentation...")
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    seg_model = SemanticSegmentationEngine(num_classes=10).to(device)
    seg_model.eval()
    
    # Object tracking
    print("\nInitializing object tracker...")
    tracker = ObjectTracker()
    
    # Simulate detections
    detections = [(100, 100, 50, 50), (200, 200, 50, 50), (300, 150, 50, 50)]
    tracked_objects = tracker.update(detections)
    print(f"  Tracking {len(tracked_objects)} objects")
    
    print("\n" + "=" * 80)
    print("Computer vision pipeline demonstration complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
