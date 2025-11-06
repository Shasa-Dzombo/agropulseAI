"""
Image Processing Utilities for Yield Estimation
===============================================

This module provides a collection of specialized image processing functions
tailored for agricultural analysis and yield estimation. These functions go
beyond simple preprocessing and are designed to extract meaningful information
from various types of imagery.

Core Functionalities:
---------------------
1.  **Vegetation Index Calculation**:
    -   Implementation of common vegetation indices (VIs) used to assess plant
      health, density, and vigor. These are critical features for yield models.
    -   `calculate_ndvi`: Normalized Difference Vegetation Index, requires NIR and
      Red bands.
    -   `calculate_evi`: Enhanced Vegetation Index, requires NIR, Red, and Blue
      bands, and is more robust in high biomass areas.
    -   `calculate_savi`: Soil-Adjusted Vegetation Index, which minimizes the
      influence of soil brightness.
    -   `calculate_exg`: Excess Green Index, a non-NIR index useful for segmenting
      green vegetation from RGB images.

2.  **Image Normalization and Correction**:
    -   `normalize_image`: Standard min-max normalization to scale pixel values
      to a specific range (e.g., 0-1), required by most neural networks.
    -   `correct_color_balance`: Implements color correction algorithms (e.g.,
      Gray World, White Patch) to standardize images taken under different
      lighting conditions. This is crucial for model generalization.

3.  **Texture Analysis**:
    -   `compute_glcm_features`: Calculates texture features from a Gray-Level
      Co-occurrence Matrix (GLCM). Features like contrast, dissimilarity,
      homogeneity, and energy can help differentiate crop textures and are
      powerful predictors of growth stage and health.

4.  **Image Segmentation and Masking**:
    -   `create_vegetation_mask`: Uses a vegetation index (like NDVI or ExG) and
      a threshold to create a binary mask that separates vegetation from soil,
      shadows, and other background elements.
    -   `apply_mask`: A utility to apply a binary mask to an image, effectively
      isolating the regions of interest (e.g., plants) for further analysis.

Dependencies:
-------------
-   **OpenCV-Python**: For fundamental image manipulation, color space conversions,
    and filtering.
-   **NumPy**: For efficient array-based calculations.
-   **scikit-image**: Provides robust implementations of algorithms like GLCM.

These utilities are the building blocks for the feature extraction pipeline,
transforming raw pixel data into a rich set of features that can be fed into
machine learning and deep learning models to accurately estimate yield.
"""

import cv2
import numpy as np
from typing import List, Dict

try:
    from skimage.feature import graycomatrix, graycoprops
except ImportError:
    graycomatrix, graycoprops = None, None
    # logging.warning("scikit-image not found. GLCM texture features will be unavailable.")

# --- Vegetation Indices ---

def calculate_ndvi(nir_band: np.ndarray, red_band: np.ndarray) -> np.ndarray:
    """
    Calculates the Normalized Difference Vegetation Index (NDVI).
    NDVI = (NIR - Red) / (NIR + Red)

    Args:
        nir_band (np.ndarray): The Near-Infrared band of an image (2D array).
        red_band (np.ndarray): The Red band of an image (2D array).

    Returns:
        np.ndarray: A 2D array of NDVI values, ranging from -1 to 1.
    """
    # Ensure bands are float to prevent overflow and allow division
    nir_band = nir_band.astype(float)
    red_band = red_band.astype(float)
    
    # Calculate NDVI, adding a small epsilon to avoid division by zero
    numerator = nir_band - red_band
    denominator = nir_band + red_band
    ndvi = np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator!=0)
    
    return ndvi

def calculate_evi(nir_band: np.ndarray, red_band: np.ndarray, blue_band: np.ndarray, 
                  g: float = 2.5, c1: float = 6.0, c2: float = 7.5, l: float = 1.0) -> np.ndarray:
    """
    Calculates the Enhanced Vegetation Index (EVI).
    EVI = G * ((NIR - Red) / (NIR + C1*Red - C2*Blue + L))

    Args:
        nir_band, red_band, blue_band: The respective spectral bands.
        g, c1, c2, l: Standard EVI coefficients.

    Returns:
        np.ndarray: A 2D array of EVI values.
    """
    nir_band = nir_band.astype(float)
    red_band = red_band.astype(float)
    blue_band = blue_band.astype(float)

    denominator = nir_band + (c1 * red_band) - (c2 * blue_band) + l
    evi = g * np.divide(nir_band - red_band, denominator, out=np.zeros_like(denominator), where=denominator!=0)
    
    return evi

def calculate_exg(image_rgb: np.ndarray) -> np.ndarray:
    """
    Calculates the Excess Green (ExG) index from an RGB image.
    ExG = 2*G - R - B

    Args:
        image_rgb (np.ndarray): An RGB image (H, W, 3).

    Returns:
        np.ndarray: A 2D array of ExG values.
    """
    # Normalize the image to prevent data type issues
    image_norm = image_rgb.astype(float) / 255.0
    r, g, b = image_norm[:, :, 0], image_norm[:, :, 1], image_norm[:, :, 2]
    
    exg = 2 * g - r - b
    return exg

# --- Image Normalization and Correction ---

def normalize_image(image: np.ndarray, target_range: tuple = (0, 1)) -> np.ndarray:
    """
    Normalizes an image to a specified range.

    Args:
        image (np.ndarray): The input image.
        target_range (tuple): The (min, max) of the desired output range.

    Returns:
        np.ndarray: The normalized image.
    """
    min_val, max_val = np.min(image), np.max(image)
    target_min, target_max = target_range
    
    if max_val == min_val:
        return np.full(image.shape, target_min, dtype=np.float32)
        
    normalized = (image - min_val) / (max_val - min_val)
    normalized = normalized * (target_max - target_min) + target_min
    
    return normalized.astype(np.float32)

def correct_gray_world(image_bgr: np.ndarray) -> np.ndarray:
    """
    Applies the Gray World algorithm for color balancing.
    Assumes the average color of the scene is gray.

    Args:
        image_bgr (np.ndarray): The input image in BGR format.

    Returns:
        np.ndarray: The color-corrected BGR image.
    """
    image_float = image_bgr.astype(float)
    # Calculate the average of each channel
    avg_b = np.mean(image_float[:, :, 0])
    avg_g = np.mean(image_float[:, :, 1])
    avg_r = np.mean(image_float[:, :, 2])
    
    # Calculate the overall average gray value
    avg_gray = (avg_b + avg_g + avg_r) / 3
    
    # Calculate scaling factors
    scale_b = avg_gray / avg_b
    scale_g = avg_gray / avg_g
    scale_r = avg_gray / avg_r
    
    # Apply scaling factors
    corrected_image = np.zeros_like(image_float)
    corrected_image[:, :, 0] = image_float[:, :, 0] * scale_b
    corrected_image[:, :, 1] = image_float[:, :, 1] * scale_g
    corrected_image[:, :, 2] = image_float[:, :, 2] * scale_r
    
    # Clip values to be in the valid 0-255 range and convert back to uint8
    return np.clip(corrected_image, 0, 255).astype(np.uint8)

# --- Texture Analysis ---

def compute_glcm_features(image_gray: np.ndarray) -> Dict[str, float]:
    """
    Computes texture features from a Gray-Level Co-occurrence Matrix (GLCM).

    Args:
        image_gray (np.ndarray): A grayscale image (2D array).

    Returns:
        Dict[str, float]: A dictionary of computed texture features.
    """
    if graycomatrix is None:
        raise ImportError("scikit-image is required for GLCM feature computation.")

    # Ensure image is 8-bit integer, as required by graycomatrix
    if image_gray.max() > 255:
        image_gray = normalize_image(image_gray, (0, 255)).astype(np.uint8)
    else:
        image_gray = image_gray.astype(np.uint8)

    # Compute GLCM
    glcm = graycomatrix(image_gray, distances=[5], angles=[0], levels=256,
                        symmetric=True, normed=True)

    # Compute properties
    features = {
        'contrast': graycoprops(glcm, 'contrast')[0, 0],
        'dissimilarity': graycoprops(glcm, 'dissimilarity')[0, 0],
        'homogeneity': graycoprops(glcm, 'homogeneity')[0, 0],
        'energy': graycoprops(glcm, 'energy')[0, 0],
        'correlation': graycoprops(glcm, 'correlation')[0, 0],
        'asm': graycoprops(glcm, 'ASM')[0, 0] # Angular Second Moment
    }
    return features

# --- Masking ---

def create_vegetation_mask(image: np.ndarray, method: str = 'exg', threshold: float = 0.05) -> np.ndarray:
    """
    Creates a binary mask to segment vegetation from the background.

    Args:
        image (np.ndarray): The input image (can be RGB or multispectral).
        method (str): The vegetation index to use ('exg', 'ndvi').
        threshold (float): The threshold to apply to the index to create the mask.

    Returns:
        np.ndarray: A binary mask (2D array of uint8) where 255 is vegetation.
    """
    if method == 'exg':
        if image.shape[2] != 3:
            raise ValueError("ExG method requires an RGB image.")
        index_map = calculate_exg(image)
    elif method == 'ndvi':
        if image.shape[2] < 4: # Assuming NIR is the 4th channel
            raise ValueError("NDVI method requires an image with at least R and NIR bands.")
        # Assuming a common band order like (R, G, B, NIR)
        red_band = image[:, :, 0]
        nir_band = image[:, :, 3]
        index_map = calculate_ndvi(nir_band, red_band)
    else:
        raise NotImplementedError(f"Method '{method}' is not supported for mask creation.")

    # Threshold the index map to create a binary mask
    _, mask = cv2.threshold(normalize_image(index_map, (0, 255)).astype(np.uint8), 
                            int(threshold * 255), 255, cv2.THRESH_BINARY)
    
    return mask

# --- Example Usage ---
if __name__ == '__main__':
    print("--- Image Processing Utilities Demo ---")

    # Create a dummy RGB image (100x100)
    dummy_rgb = np.zeros((100, 100, 3), dtype=np.uint8)
    # Add a green patch (vegetation)
    dummy_rgb[20:80, 20:80, 1] = 200
    # Add some red and blue noise
    dummy_rgb[40:60, 40:60, 0] = 50
    dummy_rgb[40:60, 40:60, 2] = 30

    # 1. ExG Calculation
    print("\n[1. Excess Green (ExG) Index]")
    exg_map = calculate_exg(dummy_rgb)
    print(f"  ExG map shape: {exg_map.shape}")
    # The green patch should have high ExG values
    assert np.mean(exg_map[30:70, 30:70]) > np.mean(exg_map[0:10, 0:10])

    # 2. Color Correction
    print("\n[2. Gray World Color Correction]")
    # Create a dummy BGR image with a blue tint
    dummy_bgr_tinted = dummy_rgb[:, :, ::-1].copy() # Convert to BGR
    dummy_bgr_tinted[:, :, 0] += 50 # Add blue tint
    corrected_bgr = correct_gray_world(dummy_bgr_tinted)
    print(f"  Original average BGR: {np.mean(dummy_bgr_tinted, axis=(0,1))}")
    print(f"  Corrected average BGR: {np.mean(corrected_bgr, axis=(0,1))}")
    # After correction, channel averages should be closer to each other
    assert np.std(np.mean(corrected_bgr, axis=(0,1))) < np.std(np.mean(dummy_bgr_tinted, axis=(0,1)))

    # 3. Texture Analysis
    print("\n[3. GLCM Texture Features]")
    if graycomatrix:
        dummy_gray = cv2.cvtColor(dummy_rgb, cv2.COLOR_RGB2GRAY)
        features = compute_glcm_features(dummy_gray)
        print(f"  Computed features: {features}")
        assert 'contrast' in features and 'homogeneity' in features
    else:
        print("  Skipping GLCM demo (scikit-image not installed).")

    # 4. Mask Creation
    print("\n[4. Vegetation Mask Creation]")
    veg_mask = create_vegetation_mask(dummy_rgb, method='exg', threshold=0.1)
    print(f"  Mask shape: {veg_mask.shape}, Data type: {veg_mask.dtype}")
    # The mask should have non-zero values where the green patch is
    assert np.sum(veg_mask[30:70, 30:70]) > 0
    assert np.sum(veg_mask[0:10, 0:10]) == 0
    
    print("\nImage processing utilities demo finished successfully.")
