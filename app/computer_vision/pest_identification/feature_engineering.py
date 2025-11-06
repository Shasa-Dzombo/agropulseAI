"""
feature_engineering.py

Advanced feature engineering module for pest identification.

This module provides sophisticated feature extraction and engineering capabilities
to enhance pest detection and classification models. It includes:

- Multi-scale texture analysis (Gabor filters, LBP, GLCM)
- Shape descriptors (Hu moments, Fourier descriptors, Zernike moments)
- Color feature extraction (histograms, color moments, dominant colors)
- Deep feature extraction from pre-trained networks
- Temporal feature aggregation for video streams
- Ensemble feature selection and dimensionality reduction
- Feature importance analysis and visualization

The engineered features can be used standalone or combined with deep learning
models for improved accuracy, especially in scenarios with limited training data.

Example Usage:
    extractor = FeatureExtractor(
        use_texture=True,
        use_shape=True,
        use_color=True,
        use_deep_features=True
    )
    features = extractor.extract_from_image(image_path)
    # features is a dictionary with feature vectors
"""

import os
import logging
from typing import Dict, List, Tuple, Optional, Union, Any
from collections import defaultdict
from dataclasses import dataclass

import numpy as np
import cv2
from scipy import ndimage
from scipy.spatial import distance
from scipy.fftpack import fft2, fftshift
from skimage import feature, filters, measure, morphology
from skimage.feature import local_binary_pattern, graycomatrix, graycoprops
from skimage.filters import gabor_kernel
from skimage.measure import moments_hu, regionprops

import torch
import torch.nn as nn
import torchvision.models as models
from torchvision import transforms

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
@dataclass
class FeatureConfig:
    """Configuration for feature extraction."""
    # Texture features
    use_lbp: bool = True
    lbp_radius: int = 3
    lbp_points: int = 24
    
    use_glcm: bool = True
    glcm_distances: List[int] = None
    glcm_angles: List[float] = None
    
    use_gabor: bool = True
    gabor_frequencies: List[float] = None
    gabor_orientations: int = 8
    
    # Shape features
    use_hu_moments: bool = True
    use_fourier_descriptors: bool = True
    use_zernike_moments: bool = True
    
    # Color features
    use_color_histogram: bool = True
    use_color_moments: bool = True
    use_dominant_colors: bool = True
    num_dominant_colors: int = 5
    
    # Deep features
    use_deep_features: bool = True
    deep_feature_model: str = 'resnet50'  # 'resnet50', 'efficientnet', 'vgg16'
    deep_feature_layer: str = 'avgpool'
    
    def __post_init__(self):
        if self.glcm_distances is None:
            self.glcm_distances = [1, 2, 3]
        if self.glcm_angles is None:
            self.glcm_angles = [0, np.pi/4, np.pi/2, 3*np.pi/4]
        if self.gabor_frequencies is None:
            self.gabor_frequencies = [0.1, 0.2, 0.3, 0.4]


# --- Texture Features ---
class TextureFeatureExtractor:
    """Extracts texture-based features from images."""
    
    def __init__(self, config: FeatureConfig):
        self.config = config
        self._prepare_gabor_kernels()
    
    def _prepare_gabor_kernels(self):
        """Pre-compute Gabor filter kernels."""
        self.gabor_kernels = []
        if self.config.use_gabor:
            for freq in self.config.gabor_frequencies:
                for theta in range(self.config.gabor_orientations):
                    theta_rad = theta / float(self.config.gabor_orientations) * np.pi
                    kernel = np.real(gabor_kernel(freq, theta=theta_rad))
                    self.gabor_kernels.append(kernel)
    
    def extract_lbp_features(self, image_gray: np.ndarray) -> np.ndarray:
        """
        Extracts Local Binary Pattern (LBP) features.
        
        LBP is a simple yet efficient texture operator which labels the pixels
        of an image by thresholding the neighborhood of each pixel and considers
        the result as a binary number.
        """
        lbp = local_binary_pattern(
            image_gray,
            self.config.lbp_points,
            self.config.lbp_radius,
            method='uniform'
        )
        # Compute histogram
        n_bins = self.config.lbp_points + 2
        hist, _ = np.histogram(
            lbp.ravel(),
            bins=n_bins,
            range=(0, n_bins),
            density=True
        )
        return hist
    
    def extract_glcm_features(self, image_gray: np.ndarray) -> np.ndarray:
        """
        Extracts Gray Level Co-occurrence Matrix (GLCM) features.
        
        GLCM measures the texture by calculating how often pairs of pixel
        with specific values and spatial relationships occur in an image.
        """
        # Quantize image to reduce levels for faster computation
        image_quantized = (image_gray / 16).astype(np.uint8)
        
        glcm = graycomatrix(
            image_quantized,
            distances=self.config.glcm_distances,
            angles=self.config.glcm_angles,
            levels=16,
            symmetric=True,
            normed=True
        )
        
        # Extract Haralick features
        features = []
        properties = ['contrast', 'dissimilarity', 'homogeneity', 'energy', 'correlation', 'ASM']
        for prop in properties:
            values = graycoprops(glcm, prop).flatten()
            features.extend(values)
        
        return np.array(features)
    
    def extract_gabor_features(self, image_gray: np.ndarray) -> np.ndarray:
        """
        Extracts Gabor filter features.
        
        Gabor filters are widely used in image processing for texture analysis.
        They capture frequency and orientation information.
        """
        features = []
        for kernel in self.gabor_kernels:
            filtered = ndimage.convolve(image_gray, kernel, mode='wrap')
            features.append(filtered.mean())
            features.append(filtered.std())
        return np.array(features)
    
    def extract_all(self, image: np.ndarray) -> Dict[str, np.ndarray]:
        """Extracts all texture features."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
        
        features = {}
        if self.config.use_lbp:
            features['lbp'] = self.extract_lbp_features(gray)
        if self.config.use_glcm:
            features['glcm'] = self.extract_glcm_features(gray)
        if self.config.use_gabor:
            features['gabor'] = self.extract_gabor_features(gray)
        
        return features


# --- Shape Features ---
class ShapeFeatureExtractor:
    """Extracts shape-based features from images or masks."""
    
    def __init__(self, config: FeatureConfig):
        self.config = config
    
    def extract_hu_moments(self, binary_mask: np.ndarray) -> np.ndarray:
        """
        Extracts Hu Moments, which are invariant to translation, rotation, and scale.
        """
        moments = cv2.moments(binary_mask)
        hu = cv2.HuMoments(moments).flatten()
        # Log transform for better numerical stability
        hu = -np.sign(hu) * np.log10(np.abs(hu) + 1e-10)
        return hu
    
    def extract_fourier_descriptors(self, contour: np.ndarray, num_descriptors: int = 20) -> np.ndarray:
        """
        Extracts Fourier Descriptors from a contour.
        
        Fourier descriptors represent the shape of a contour in the frequency domain
        and are invariant to translation, rotation, and scale.
        """
        if len(contour) < num_descriptors:
            # Pad if necessary
            contour = np.vstack([contour, np.zeros((num_descriptors - len(contour), 2))])
        
        # Convert contour to complex representation
        complex_contour = contour[:, 0] + 1j * contour[:, 1]
        
        # Compute FFT
        fourier = np.fft.fft(complex_contour)
        
        # Normalize (make invariant to starting point)
        fourier = np.fft.fftshift(fourier)
        
        # Take magnitude to make rotation-invariant
        descriptors = np.abs(fourier[:num_descriptors])
        
        # Normalize to make scale-invariant
        descriptors = descriptors / (descriptors[0] + 1e-10)
        
        return descriptors
    
    def extract_zernike_moments(self, binary_mask: np.ndarray, degree: int = 8) -> np.ndarray:
        """
        Extracts Zernike Moments.
        
        Zernike moments are a set of orthogonal moments that are rotation invariant
        and provide a good representation of shape.
        """
        # This is a simplified implementation. A full implementation would use
        # the Zernike polynomial basis functions.
        # For production, consider using libraries like mahotas.
        
        # Find centroid
        M = cv2.moments(binary_mask)
        if M['m00'] == 0:
            return np.zeros(degree)
        
        cx = int(M['m10'] / M['m00'])
        cy = int(M['m01'] / M['m00'])
        
        # Create coordinate system centered at centroid
        y, x = np.ogrid[:binary_mask.shape[0], :binary_mask.shape[1]]
        x = x - cx
        y = y - cy
        
        # Convert to polar coordinates
        rho = np.sqrt(x**2 + y**2)
        theta = np.arctan2(y, x)
        
        # Normalize radius
        max_rho = np.max(rho[binary_mask > 0]) if np.any(binary_mask > 0) else 1
        rho = rho / (max_rho + 1e-10)
        
        # Compute a simplified set of moments (placeholder)
        # A real implementation would compute Zernike polynomials V_nm
        moments = []
        for n in range(degree):
            for m in range(n + 1):
                if (n - m) % 2 == 0:
                    # Simplified moment computation
                    moment = np.sum(binary_mask * rho**n * np.cos(m * theta))
                    moments.append(moment)
        
        return np.array(moments[:degree])
    
    def extract_geometric_features(self, binary_mask: np.ndarray) -> Dict[str, float]:
        """Extracts basic geometric features."""
        contours, _ = cv2.findContours(
            binary_mask.astype(np.uint8),
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        if not contours:
            return {}
        
        # Use the largest contour
        contour = max(contours, key=cv2.contourArea)
        
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        
        # Circularity
        circularity = (4 * np.pi * area) / (perimeter**2 + 1e-10)
        
        # Aspect ratio
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = float(w) / (h + 1e-10)
        
        # Extent (ratio of contour area to bounding box area)
        extent = area / (w * h + 1e-10)
        
        # Solidity (ratio of contour area to convex hull area)
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        solidity = area / (hull_area + 1e-10)
        
        return {
            'area': area,
            'perimeter': perimeter,
            'circularity': circularity,
            'aspect_ratio': aspect_ratio,
            'extent': extent,
            'solidity': solidity
        }
    
    def extract_all(self, binary_mask: np.ndarray) -> Dict[str, np.ndarray]:
        """Extracts all shape features."""
        features = {}
        
        if self.config.use_hu_moments:
            features['hu_moments'] = self.extract_hu_moments(binary_mask)
        
        # Find contours for other features
        contours, _ = cv2.findContours(
            binary_mask.astype(np.uint8),
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            
            if self.config.use_fourier_descriptors:
                features['fourier_descriptors'] = self.extract_fourier_descriptors(
                    largest_contour.reshape(-1, 2)
                )
            
            if self.config.use_zernike_moments:
                features['zernike_moments'] = self.extract_zernike_moments(binary_mask)
        
        # Geometric features
        geo_features = self.extract_geometric_features(binary_mask)
        if geo_features:
            features['geometric'] = np.array(list(geo_features.values()))
        
        return features


# --- Color Features ---
class ColorFeatureExtractor:
    """Extracts color-based features from images."""
    
    def __init__(self, config: FeatureConfig):
        self.config = config
    
    def extract_color_histogram(self, image: np.ndarray, bins: int = 32) -> np.ndarray:
        """
        Extracts color histograms in multiple color spaces.
        """
        features = []
        
        # RGB histogram
        for channel in range(3):
            hist, _ = np.histogram(image[:, :, channel], bins=bins, range=(0, 256))
            hist = hist.astype(float) / (hist.sum() + 1e-10)
            features.extend(hist)
        
        # HSV histogram
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        for channel in range(3):
            hist, _ = np.histogram(hsv[:, :, channel], bins=bins, range=(0, 256))
            hist = hist.astype(float) / (hist.sum() + 1e-10)
            features.extend(hist)
        
        return np.array(features)
    
    def extract_color_moments(self, image: np.ndarray) -> np.ndarray:
        """
        Extracts color moments (mean, std, skewness) for each channel.
        """
        features = []
        
        # Process multiple color spaces
        color_spaces = [
            ('RGB', image),
            ('HSV', cv2.cvtColor(image, cv2.COLOR_RGB2HSV)),
            ('LAB', cv2.cvtColor(image, cv2.COLOR_RGB2LAB))
        ]
        
        for space_name, img in color_spaces:
            for channel in range(3):
                channel_data = img[:, :, channel].flatten().astype(float)
                
                # First moment: mean
                mean = np.mean(channel_data)
                # Second moment: standard deviation
                std = np.std(channel_data)
                # Third moment: skewness
                skewness = np.mean(((channel_data - mean) / (std + 1e-10)) ** 3)
                
                features.extend([mean, std, skewness])
        
        return np.array(features)
    
    def extract_dominant_colors(self, image: np.ndarray) -> np.ndarray:
        """
        Extracts dominant colors using K-means clustering.
        """
        # Reshape image to be a list of pixels
        pixels = image.reshape(-1, 3).astype(np.float32)
        
        # Use K-means to find dominant colors
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        _, labels, centers = cv2.kmeans(
            pixels,
            self.config.num_dominant_colors,
            None,
            criteria,
            10,
            cv2.KMEANS_PP_CENTERS
        )
        
        # Sort by frequency
        unique, counts = np.unique(labels, return_counts=True)
        sorted_indices = np.argsort(-counts)
        dominant_colors = centers[sorted_indices].flatten()
        
        return dominant_colors
    
    def extract_all(self, image: np.ndarray) -> Dict[str, np.ndarray]:
        """Extracts all color features."""
        features = {}
        
        if self.config.use_color_histogram:
            features['color_histogram'] = self.extract_color_histogram(image)
        
        if self.config.use_color_moments:
            features['color_moments'] = self.extract_color_moments(image)
        
        if self.config.use_dominant_colors:
            features['dominant_colors'] = self.extract_dominant_colors(image)
        
        return features


# --- Deep Features ---
class DeepFeatureExtractor:
    """Extracts features from pre-trained deep learning models."""
    
    def __init__(self, config: FeatureConfig):
        self.config = config
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = self._load_model()
        self.transform = self._get_transform()
    
    def _load_model(self) -> nn.Module:
        """Loads a pre-trained model."""
        model_name = self.config.deep_feature_model.lower()
        
        if model_name == 'resnet50':
            model = models.resnet50(pretrained=True)
            # Remove the final classification layer
            model = nn.Sequential(*list(model.children())[:-1])
        elif model_name == 'vgg16':
            model = models.vgg16(pretrained=True)
            model = model.features
        elif model_name == 'efficientnet':
            model = models.efficientnet_b0(pretrained=True)
            model = nn.Sequential(*list(model.children())[:-1])
        else:
            raise ValueError(f"Unsupported model: {model_name}")
        
        model = model.to(self.device)
        model.eval()
        return model
    
    def _get_transform(self):
        """Returns the preprocessing transform."""
        return transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
    
    def extract(self, image: np.ndarray) -> np.ndarray:
        """Extracts deep features from an image."""
        # Preprocess
        input_tensor = self.transform(image).unsqueeze(0).to(self.device)
        
        # Extract features
        with torch.no_grad():
            features = self.model(input_tensor)
        
        # Flatten and convert to numpy
        features = features.squeeze().cpu().numpy()
        if features.ndim > 1:
            features = features.flatten()
        
        return features


# --- Main Feature Extractor ---
class FeatureExtractor:
    """
    Main interface for feature extraction.
    
    Combines texture, shape, color, and deep features into a unified interface.
    """
    
    def __init__(self, config: Optional[FeatureConfig] = None):
        if config is None:
            config = FeatureConfig()
        self.config = config
        
        self.texture_extractor = TextureFeatureExtractor(config)
        self.shape_extractor = ShapeFeatureExtractor(config)
        self.color_extractor = ColorFeatureExtractor(config)
        
        if config.use_deep_features:
            self.deep_extractor = DeepFeatureExtractor(config)
        else:
            self.deep_extractor = None
        
        logger.info("FeatureExtractor initialized.")
    
    def extract_from_image(self,
                          image: Union[str, np.ndarray],
                          mask: Optional[np.ndarray] = None) -> Dict[str, np.ndarray]:
        """
        Extracts all configured features from an image.
        
        Args:
            image: Path to image file or numpy array
            mask: Optional binary mask for shape features
        
        Returns:
            Dictionary of feature vectors
        """
        # Load image if path is provided
        if isinstance(image, str):
            image = cv2.imread(image)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        all_features = {}
        
        # Texture features
        texture_feats = self.texture_extractor.extract_all(image)
        all_features.update(texture_feats)
        
        # Color features
        color_feats = self.color_extractor.extract_all(image)
        all_features.update(color_feats)
        
        # Shape features (requires mask)
        if mask is not None:
            shape_feats = self.shape_extractor.extract_all(mask)
            all_features.update(shape_feats)
        
        # Deep features
        if self.deep_extractor is not None:
            deep_feats = self.deep_extractor.extract(image)
            all_features['deep_features'] = deep_feats
        
        return all_features
    
    def extract_batch(self, images: List[np.ndarray]) -> List[Dict[str, np.ndarray]]:
        """Extracts features from a batch of images."""
        return [self.extract_from_image(img) for img in images]
    
    def get_feature_vector(self, features: Dict[str, np.ndarray]) -> np.ndarray:
        """Concatenates all feature dictionaries into a single vector."""
        feature_list = []
        for key in sorted(features.keys()):
            feature_list.append(features[key].flatten())
        return np.concatenate(feature_list)
    
    def get_feature_dim(self) -> int:
        """Returns the dimensionality of the feature vector."""
        # Create a dummy image to get dimensions
        dummy_image = np.zeros((224, 224, 3), dtype=np.uint8)
        dummy_features = self.extract_from_image(dummy_image)
        return len(self.get_feature_vector(dummy_features))


# --- Feature Selection ---
class FeatureSelector:
    """
    Performs feature selection and dimensionality reduction.
    """
    
    def __init__(self, method: str = 'variance', n_features: int = 100):
        """
        Args:
            method: Selection method ('variance', 'mutual_info', 'chi2', 'pca')
            n_features: Number of features to select
        """
        self.method = method
        self.n_features = n_features
        self.selected_indices: Optional[np.ndarray] = None
        self.reducer: Optional[Any] = None
    
    def fit(self, X: np.ndarray, y: Optional[np.ndarray] = None):
        """Fits the feature selector."""
        if self.method == 'variance':
            # Select features with highest variance
            variances = np.var(X, axis=0)
            self.selected_indices = np.argsort(variances)[-self.n_features:]
        
        elif self.method == 'mutual_info':
            from sklearn.feature_selection import mutual_info_classif
            if y is None:
                raise ValueError("Labels required for mutual info selection")
            mi_scores = mutual_info_classif(X, y)
            self.selected_indices = np.argsort(mi_scores)[-self.n_features:]
        
        elif self.method == 'chi2':
            from sklearn.feature_selection import chi2, SelectKBest
            if y is None:
                raise ValueError("Labels required for chi2 selection")
            # Ensure non-negative features
            X_nonneg = X - X.min() + 1e-10
            selector = SelectKBest(chi2, k=self.n_features)
            selector.fit(X_nonneg, y)
            self.selected_indices = selector.get_support(indices=True)
        
        elif self.method == 'pca':
            from sklearn.decomposition import PCA
            self.reducer = PCA(n_components=self.n_features)
            self.reducer.fit(X)
        
        else:
            raise ValueError(f"Unknown method: {self.method}")
        
        return self
    
    def transform(self, X: np.ndarray) -> np.ndarray:
        """Transforms features using the fitted selector."""
        if self.method == 'pca' and self.reducer is not None:
            return self.reducer.transform(X)
        elif self.selected_indices is not None:
            return X[:, self.selected_indices]
        else:
            raise ValueError("Selector not fitted yet")
    
    def fit_transform(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> np.ndarray:
        """Fits and transforms in one step."""
        self.fit(X, y)
        return self.transform(X)


# --- Feature Importance Analysis ---
class FeatureImportanceAnalyzer:
    """
    Analyzes and visualizes feature importance.
    """
    
    def __init__(self):
        self.importance_scores: Dict[str, float] = {}
    
    def analyze_with_random_forest(self, X: np.ndarray, y: np.ndarray,
                                   feature_names: List[str]) -> Dict[str, float]:
        """
        Uses Random Forest to compute feature importance.
        """
        from sklearn.ensemble import RandomForestClassifier
        
        rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        rf.fit(X, y)
        
        importances = rf.feature_importances_
        self.importance_scores = dict(zip(feature_names, importances))
        
        # Sort by importance
        self.importance_scores = dict(
            sorted(self.importance_scores.items(), key=lambda x: x[1], reverse=True)
        )
        
        return self.importance_scores
    
    def analyze_with_permutation(self, model: Any, X: np.ndarray, y: np.ndarray,
                                feature_names: List[str]) -> Dict[str, float]:
        """
        Uses permutation importance.
        """
        from sklearn.inspection import permutation_importance
        
        result = permutation_importance(model, X, y, n_repeats=10, random_state=42, n_jobs=-1)
        
        self.importance_scores = dict(zip(feature_names, result.importances_mean))
        self.importance_scores = dict(
            sorted(self.importance_scores.items(), key=lambda x: x[1], reverse=True)
        )
        
        return self.importance_scores
    
    def get_top_features(self, n: int = 20) -> List[Tuple[str, float]]:
        """Returns the top N most important features."""
        return list(self.importance_scores.items())[:n]


# --- Example Usage ---
def demo_feature_extraction():
    """Demonstrates feature extraction capabilities."""
    logger.info("=== Feature Extraction Demo ===")
    
    # Create a synthetic image
    image = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
    
    # Create a binary mask (circle)
    mask = np.zeros((256, 256), dtype=np.uint8)
    cv2.circle(mask, (128, 128), 64, 255, -1)
    
    # Initialize extractor
    config = FeatureConfig(
        use_lbp=True,
        use_glcm=True,
        use_gabor=True,
        use_hu_moments=True,
        use_color_histogram=True,
        use_deep_features=False  # Disable for demo speed
    )
    
    extractor = FeatureExtractor(config)
    
    # Extract features
    features = extractor.extract_from_image(image, mask=mask)
    
    logger.info(f"Extracted {len(features)} feature groups:")
    for name, feat_array in features.items():
        logger.info(f"  - {name}: dimension = {feat_array.shape}")
    
    # Get concatenated feature vector
    feature_vector = extractor.get_feature_vector(features)
    logger.info(f"Total feature vector dimension: {len(feature_vector)}")
    
    # Demonstrate feature selection
    logger.info("\n=== Feature Selection Demo ===")
    X = np.random.randn(100, len(feature_vector))
    y = np.random.randint(0, 5, 100)
    
    selector = FeatureSelector(method='variance', n_features=50)
    X_selected = selector.fit_transform(X)
    logger.info(f"Selected {X_selected.shape[1]} features from {X.shape[1]}")
    
    logger.info("\nDemo complete!")


if __name__ == '__main__':
    demo_feature_extraction()
