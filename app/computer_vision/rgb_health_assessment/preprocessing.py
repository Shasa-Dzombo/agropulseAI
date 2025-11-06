# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\rgb_health_assessment\preprocessing.py

"""
Image Preprocessing and Feature Extraction for RGB Health Assessment
===================================================================

This module provides a comprehensive pipeline for preprocessing standard RGB
images of plants and extracting a rich set of features suitable for machine
learning models. This is a critical step in assessing crop health from CCTV
or mobile phone cameras, as it handles the significant variability in lighting,
background, and image quality.

The pipeline is designed to be modular, allowing different techniques for each
step to be selected and configured.

Core Components:
----------------
1.  **`ColorCorrector`**:
    -   **Purpose**: To standardize image colors and mitigate the effects of
      varying lighting conditions, which is essential for consistent feature
      extraction.
    -   **Methods**:
        -   **Gray World**: Assumes the average color of the scene is gray and
          adjusts the image accordingly.
        -   **White Patch**: Assumes the brightest pixel in the image should be
          white and scales other colors relative to it.
        -   **Color Checker-based**: A highly accurate method that uses a standard
          color checker (like an X-Rite ColorChecker) placed in the scene to
          derive a precise color transformation matrix.

2.  **`PlantSegmenter`**:
    -   **Purpose**: To accurately separate plant pixels from the background
      (e.g., soil, pots, benches). This is arguably the most crucial step, as
      inaccurate segmentation will lead to noisy and unreliable features.
    -   **Methods**:
        -   **Index Thresholding**: A simple and fast method that uses an RGB
          vegetation index (like ExG) to create a binary mask. Effective in
          high-contrast scenes.
        -   **Color-based (HSV)**: Segments plants by defining a range of hue,
          saturation, and value that corresponds to green vegetation.
        -   **DeepLabV3+ Segmentation**: A powerful deep learning approach that
          uses a pre-trained semantic segmentation model (DeepLabV3+ with a
          MobileNetV3 backbone) to generate a precise plant mask. This method
          is robust to complex backgrounds and lighting variations.

3.  **`FeatureExtractor`**:
    -   **Purpose**: To compute a quantitative feature vector from the segmented
      plant pixels. This vector will be the input to the health assessment model.
    -   **Feature Sets**:
        -   **RGB Indices**: Calculates the mean and standard deviation of all
          available RGB indices from the `rgb_indices` module over the plant mask.
        -   **Color Histograms**: Computes histograms in multiple color spaces
          (RGB, HSV, L*a*b*), capturing the distribution of colors in the plant.
        -   **Texture Features (GLCM)**: Calculates texture properties like
          contrast, dissimilarity, homogeneity, energy, and correlation from a
          Gray-Level Co-occurrence Matrix (GLCM). These features can help detect
          patterns related to disease or stress.
        -   **Morphological Features**: Computes basic shape and size features
          of the segmented plant mask, such as area, perimeter, and compactness.

4.  **`RGBDataPipeline`**:
    -   **Purpose**: An orchestrator class that ties all the preprocessing steps
      together into a single, configurable pipeline.
    -   **Process**: Takes a raw image path as input and returns a dictionary
      containing the processed images (e.g., corrected, masked) and the final
      feature vector.

Dependencies:
-------------
-   `OpenCV (cv2)`: For image loading, color space conversions, and morphological operations.
-   `scikit-image`: For GLCM-based texture feature extraction.
-   `PyTorch` & `TorchVision`: For running the deep learning-based segmentation model.
-   `NumPy`: For all numerical operations.
"""

import cv2
import numpy as np
import torch
from torchvision.models.segmentation import deeplabv3_mobilenet_v3_large, DeepLabV3_MobileNet_V3_Large_Weights
from skimage.feature import graycomatrix, graycoprops
from typing import Dict, List, Tuple, Optional, Any
import logging

from .rgb_indices import calculate_rgb_indices, get_available_rgb_indices

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
EPSILON = 1e-8

# --- 1. Color Correction ---

class ColorCorrector:
    """A class to perform color correction on RGB images."""

    def __init__(self, method: str = 'gray_world', **kwargs):
        """
        Args:
            method (str): The correction method to use. One of ['gray_world',
                'white_patch', 'color_checker'].
            **kwargs: Additional parameters for specific methods.
                For 'color_checker': `checker_coords` (list of top-left corners
                of checker patches) and `reference_colors` (the known RGB values).
        """
        self.method = method
        self.params = kwargs
        logging.info(f"Initialized ColorCorrector with method: {self.method}")

    def correct(self, image: np.ndarray) -> np.ndarray:
        """
        Applies the selected color correction method.

        Args:
            image (np.ndarray): The input BGR image (as loaded by OpenCV), in uint8 format.

        Returns:
            np.ndarray: The color-corrected BGR image in uint8 format.
        """
        # Convert image to float for calculations
        img_float = image.astype(np.float32) / 255.0

        if self.method == 'gray_world':
            corrected_img = self._gray_world(img_float)
        elif self.method == 'white_patch':
            corrected_img = self._white_patch(img_float)
        elif self.method == 'color_checker':
            if 'checker_coords' not in self.params or 'reference_colors' not in self.params:
                raise ValueError("Color checker method requires 'checker_coords' and 'reference_colors'.")
            corrected_img = self._color_checker_correction(img_float)
        else:
            raise ValueError(f"Unknown color correction method: {self.method}")

        # Clip values to [0, 1] range and convert back to uint8
        corrected_img = np.clip(corrected_img, 0, 1)
        return (corrected_img * 255).astype(np.uint8)

    def _gray_world(self, image: np.ndarray) -> np.ndarray:
        """Assumes the average color in the scene is gray."""
        # Calculate the average of each channel (BGR)
        avg_b, avg_g, avg_r = np.mean(image[:, :, 0]), np.mean(image[:, :, 1]), np.mean(image[:, :, 2])
        
        # Calculate the overall average intensity
        avg_gray = (avg_b + avg_g + avg_r) / 3.0
        
        # Calculate scaling factors for each channel
        scale_b = avg_gray / (avg_b + EPSILON)
        scale_g = avg_gray / (avg_g + EPSILON)
        scale_r = avg_gray / (avg_r + EPSILON)
        
        # Apply the scaling
        corrected_image = image.copy()
        corrected_image[:, :, 0] *= scale_b
        corrected_image[:, :, 1] *= scale_g
        corrected_image[:, :, 2] *= scale_r
        
        return corrected_image

    def _white_patch(self, image: np.ndarray) -> np.ndarray:
        """Assumes the brightest pixel in the image is white."""
        max_b, max_g, max_r = np.max(image[:, :, 0]), np.max(image[:, :, 1]), np.max(image[:, :, 2])
        
        # Calculate scaling factors to make the brightest pixel white (1.0)
        scale_b = 1.0 / (max_b + EPSILON)
        scale_g = 1.0 / (max_g + EPSILON)
        scale_r = 1.0 / (max_r + EPSILON)
        
        corrected_image = image.copy()
        corrected_image[:, :, 0] *= scale_b
        corrected_image[:, :, 1] *= scale_g
        corrected_image[:, :, 2] *= scale_r
        
        return corrected_image

    def _color_checker_correction(self, image: np.ndarray) -> np.ndarray:
        """
        Performs color correction using a color checker.
        This is a simplified implementation. A robust version would involve
        finding the checker automatically. Here we assume its location is given.
        """
        # In a real implementation, we would find the checker patches,
        # average their colors, and then compute a transformation matrix
        # (e.g., a 3x3 matrix or a more complex polynomial transform)
        # that maps the measured colors to the reference colors.
        logging.warning("Color checker correction is a placeholder. "
                        "It currently applies a simple white balance as a demo.")
        return self._white_patch(image)


# --- 2. Plant Segmentation ---

class PlantSegmenter:
    """A class to segment plants from the background in an RGB image."""

    def __init__(self, method: str = 'deeplab', **kwargs):
        """
        Args:
            method (str): The segmentation method. One of ['index_threshold',
                'hsv_threshold', 'deeplab'].
            **kwargs: Additional parameters for specific methods.
                For 'index_threshold': `index_name` (e.g., 'ExG'), `threshold`.
                For 'hsv_threshold': `lower_green`, `upper_green`.
        """
        self.method = method
        self.params = kwargs
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model = None

        if self.method == 'deeplab':
            logging.info("Loading DeepLabV3 model for segmentation...")
            weights = DeepLabV3_MobileNet_V3_Large_Weights.DEFAULT
            self.model = deeplabv3_mobilenet_v3_large(weights=weights).to(self.device)
            self.model.eval()
            self.transforms = weights.transforms()
            # COCO dataset class for 'potted plant' is 64. We might need to
            # fine-tune for general vegetation. For now, we can look for this class.
            self.plant_class_id = 64 
        logging.info(f"Initialized PlantSegmenter with method: {self.method}")

    def segment(self, image: np.ndarray) -> np.ndarray:
        """
        Generates a binary mask of the plant.

        Args:
            image (np.ndarray): The input BGR image (uint8).

        Returns:
            np.ndarray: A binary mask (0 or 255) of the same height and width,
                        where 255 indicates plant pixels.
        """
        if self.method == 'index_threshold':
            return self._segment_by_index(image)
        elif self.method == 'hsv_threshold':
            return self._segment_by_hsv(image)
        elif self.method == 'deeplab':
            return self._segment_by_deeplab(image)
        else:
            raise ValueError(f"Unknown segmentation method: {self.method}")

    def _segment_by_index(self, image: np.ndarray) -> np.ndarray:
        """Segments using a threshold on an RGB index."""
        index_name = self.params.get('index_name', 'ExG').upper()
        threshold = self.params.get('threshold', 0.1)

        # Normalize image to 0-1 and convert to RGB
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) / 255.0
        bands = {'R': img_rgb[:, :, 0], 'G': img_rgb[:, :, 1], 'B': img_rgb[:, :, 2]}
        
        index_map = calculate_rgb_indices(bands, [index_name])[index_name]
        
        # Normalize index map for consistent thresholding if needed
        if np.min(index_map) < 0 or np.max(index_map) > 1:
             index_map = (index_map - np.min(index_map)) / (np.max(index_map) - np.min(index_map) + EPSILON)

        _, mask = cv2.threshold((index_map * 255).astype(np.uint8), int(threshold * 255), 255, cv2.THRESH_BINARY)
        return self._clean_mask(mask)

    def _segment_by_hsv(self, image: np.ndarray) -> np.ndarray:
        """Segments using a color range in HSV space."""
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        lower_green = self.params.get('lower_green', np.array([30, 40, 40]))
        upper_green = self.params.get('upper_green', np.array([90, 255, 255]))
        
        mask = cv2.inRange(hsv_image, lower_green, upper_green)
        return self._clean_mask(mask)

    def _segment_by_deeplab(self, image: np.ndarray) -> np.ndarray:
        """Segments using a pre-trained DeepLabV3 model."""
        if self.model is None:
            raise RuntimeError("DeepLabV3 model is not loaded.")
            
        # Convert BGR to RGB and create a batch
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        batch = self.transforms(img_rgb).unsqueeze(0).to(self.device)

        with torch.no_grad():
            output = self.model(batch)['out']
        
        # Get the class predictions and create a mask for the plant class
        sem_classes = output.argmax(dim=1).squeeze().cpu().numpy()
        mask = np.where(sem_classes == self.plant_class_id, 255, 0).astype(np.uint8)
        
        # Resize mask to original image size
        mask = cv2.resize(mask, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)
        return self._clean_mask(mask)

    def _clean_mask(self, mask: np.ndarray) -> np.ndarray:
        """Applies morphological operations to clean up a binary mask."""
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        # Fill small holes
        cleaned_mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        # Remove small noise
        cleaned_mask = cv2.morphologyEx(cleaned_mask, cv2.MORPH_OPEN, kernel, iterations=2)
        return cleaned_mask


# --- 3. Feature Extraction ---

class FeatureExtractor:
    """Extracts a feature vector from a segmented plant image."""

    def __init__(self, feature_sets: List[str]):
        """
        Args:
            feature_sets (List[str]): A list of feature types to extract.
                Supported: ['indices', 'histograms', 'texture', 'morphology'].
        """
        self.feature_sets = feature_sets
        logging.info(f"Initialized FeatureExtractor with sets: {self.feature_sets}")

    def extract(self, image: np.ndarray, mask: np.ndarray) -> Dict[str, float]:
        """
        Computes the feature vector.

        Args:
            image (np.ndarray): The original BGR image (uint8).
            mask (np.ndarray): The binary plant mask (0 or 255).

        Returns:
            Dict[str, float]: A dictionary of named features.
        """
        features = {}
        num_plant_pixels = np.sum(mask == 255)

        if num_plant_pixels == 0:
            logging.warning("No plant pixels found in the mask. Returning empty features.")
            return {}

        if 'indices' in self.feature_sets:
            features.update(self._extract_index_features(image, mask))
        if 'histograms' in self.feature_sets:
            features.update(self._extract_histogram_features(image, mask))
        if 'texture' in self.feature_sets:
            features.update(self._extract_texture_features(image, mask))
        if 'morphology' in self.feature_sets:
            features.update(self._extract_morphological_features(mask))
            
        return features

    def _extract_index_features(self, image: np.ndarray, mask: np.ndarray) -> Dict[str, float]:
        """Calculates statistics of RGB indices over the plant area."""
        img_rgb_norm = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) / 255.0
        bands = {'R': img_rgb_norm[:, :, 0], 'G': img_rgb_norm[:, :, 1], 'B': img_rgb_norm[:, :, 2]}
        
        index_features = {}
        all_indices = get_available_rgb_indices()
        
        try:
            calculated = calculate_rgb_indices(bands, all_indices)
            for name, index_map in calculated.items():
                plant_pixels = index_map[mask == 255]
                index_features[f'index_{name}_mean'] = float(np.mean(plant_pixels))
                index_features[f'index_{name}_std'] = float(np.std(plant_pixels))
        except Exception as e:
            logging.error(f"Could not calculate index features: {e}")
            
        return index_features

    def _extract_histogram_features(self, image: np.ndarray, mask: np.ndarray) -> Dict[str, float]:
        """Calculates color histogram statistics."""
        hist_features = {}
        
        # RGB color space
        for i, color in enumerate(['B', 'G', 'R']):
            hist = cv2.calcHist([image], [i], mask, [256], [0, 256])
            hist_features[f'hist_{color}_mean'] = float(np.mean(np.where(hist > 0)[0]))
            hist_features[f'hist_{color}_std'] = float(np.std(np.where(hist > 0)[0]))

        # HSV color space
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        for i, color in enumerate(['H', 'S', 'V']):
            hist = cv2.calcHist([hsv_image], [i], mask, [256], [0, 256])
            hist_features[f'hist_{color}_mean'] = float(np.mean(np.where(hist > 0)[0]))
            hist_features[f'hist_{color}_std'] = float(np.std(np.where(hist > 0)[0]))
            
        return hist_features

    def _extract_texture_features(self, image: np.ndarray, mask: np.ndarray) -> Dict[str, float]:
        """Calculates GLCM texture features."""
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Create a masked grayscale image
        masked_gray = gray_image.copy()
        masked_gray[mask == 0] = 0
        
        # Compute GLCM on the bounding box of the mask to save computation
        rows, cols = np.where(mask == 255)
        if len(rows) == 0: return {}
        
        roi = masked_gray[np.min(rows):np.max(rows)+1, np.min(cols):np.max(cols)+1]
        if roi.size == 0: return {}

        glcm = graycomatrix(roi, distances=[1, 2, 3], angles=[0, np.pi/4, np.pi/2, 3*np.pi/4],
                            levels=256, symmetric=True, normed=True)
        
        texture_features = {}
        props = ['contrast', 'dissimilarity', 'homogeneity', 'energy', 'correlation', 'ASM']
        for prop in props:
            try:
                values = graycoprops(glcm, prop)
                texture_features[f'texture_{prop}_mean'] = float(np.mean(values))
                texture_features[f'texture_{prop}_std'] = float(np.std(values))
            except Exception as e:
                logging.error(f"Could not compute texture property {prop}: {e}")
                
        return texture_features

    def _extract_morphological_features(self, mask: np.ndarray) -> Dict[str, float]:
        """Calculates shape-based features from the mask."""
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return {}
            
        # Assume the largest contour is the plant
        main_contour = max(contours, key=cv2.contourArea)
        
        area = cv2.contourArea(main_contour)
        perimeter = cv2.arcLength(main_contour, True)
        
        # Bounding box
        x, y, w, h = cv2.boundingRect(main_contour)
        aspect_ratio = w / (h + EPSILON)
        
        # Convex hull
        hull = cv2.convexHull(main_contour)
        hull_area = cv2.contourArea(hull)
        solidity = area / (hull_area + EPSILON)
        
        return {
            'morph_area': float(area),
            'morph_perimeter': float(perimeter),
            'morph_aspect_ratio': float(aspect_ratio),
            'morph_solidity': float(solidity),
        }


# --- 4. Main Data Pipeline ---

class RGBDataPipeline:
    """Orchestrates the full preprocessing and feature extraction workflow."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.color_corrector = ColorCorrector(**config.get('color_correction', {}))
        self.segmenter = PlantSegmenter(**config.get('segmentation', {}))
        self.feature_extractor = FeatureExtractor(**config.get('feature_extraction', {}))
        logging.info("Initialized RGBDataPipeline with provided configuration.")

    def process_image(self, image_path: str) -> Dict[str, Any]:
        """
        Runs a single image through the entire pipeline.

        Args:
            image_path (str): Path to the input image.

        Returns:
            Dict[str, Any]: A dictionary containing the results, including
                'original_image', 'corrected_image', 'mask', 'masked_image',
                and 'features'.
        """
        # 1. Load Image
        original_image = cv2.imread(image_path)
        if original_image is None:
            raise FileNotFoundError(f"Image not found at {image_path}")

        # 2. Color Correction
        corrected_image = self.color_corrector.correct(original_image)

        # 3. Segmentation
        mask = self.segmenter.segment(corrected_image)

        # 4. Feature Extraction
        features = self.feature_extractor.extract(corrected_image, mask)

        # 5. Create masked image for visualization
        masked_image = cv2.bitwise_and(corrected_image, corrected_image, mask=mask)

        return {
            "original_image": original_image,
            "corrected_image": corrected_image,
            "mask": mask,
            "masked_image": masked_image,
            "features": features,
        }

# --- Example Usage ---
if __name__ == '__main__':
    print("--- RGB Preprocessing and Feature Extraction Demo ---")

    # Create a dummy image for demonstration
    dummy_image = np.zeros((300, 400, 3), dtype=np.uint8)
    # Background (dark soil)
    dummy_image[:] = (30, 42, 45) # BGR
    # Plant (green circle) with some noise
    cv2.circle(dummy_image, (200, 150), 80, (50, 180, 70), -1)
    # Add some yellow-ish stress spots
    cv2.circle(dummy_image, (180, 130), 10, (40, 170, 190), -1)
    
    dummy_image_path = "dummy_plant_image.png"
    cv2.imwrite(dummy_image_path, dummy_image)
    print(f"Created a dummy image: {dummy_image_path}")

    # Define a pipeline configuration
    pipeline_config = {
        "color_correction": {"method": "gray_world"},
        "segmentation": {"method": "hsv_threshold"},
        "feature_extraction": {"feature_sets": ['indices', 'histograms', 'texture', 'morphology']}
    }
    
    # Initialize and run the pipeline
    try:
        pipeline = RGBDataPipeline(pipeline_config)
        results = pipeline.process_image(dummy_image_path)

        print("\n--- Pipeline Results ---")
        print(f"Successfully processed the image.")
        
        # Check features
        features = results['features']
        print(f"Extracted {len(features)} features.")
        if features:
            print("Sample features:")
            for i, (key, value) in enumerate(features.items()):
                if i >= 5: break
                print(f"  - {key}: {value:.4f}")
        
        # Save output images for inspection
        cv2.imwrite("corrected_image.png", results['corrected_image'])
        cv2.imwrite("segmentation_mask.png", results['mask'])
        cv2.imwrite("masked_plant.png", results['masked_image'])
        print("\nSaved 'corrected_image.png', 'segmentation_mask.png', and 'masked_plant.png' for review.")

    except Exception as e:
        logging.error(f"An error occurred during the demo pipeline run: {e}", exc_info=True)

```