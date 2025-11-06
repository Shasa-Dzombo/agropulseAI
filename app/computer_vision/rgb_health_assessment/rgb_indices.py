# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\rgb_health_assessment\rgb_indices.py

"""
RGB-Based Vegetation Indices for Crop Health Assessment
=======================================================

This module provides a collection of functions to calculate various vegetation
indices using only the Red, Green, and Blue bands of a standard RGB image.
These indices are crucial for assessing crop health when multispectral or
hyperspectral data is not available, making them ideal for use with images
from consumer-grade cameras, smartphones, and CCTVs.

Unlike traditional indices like NDVI which require a Near-Infrared (NIR) band,
RGB indices leverage the differential reflection of light in the visible
spectrum to approximate vegetation properties like canopy density, chlorophyll
content, and stress levels.

The core of this module is a registry pattern, similar to the one used for
multispectral indices, which allows for easy extension and flexible calculation.
Each index function is designed to work with NumPy arrays representing the
R, G, and B channels of an image.

Key Features:
-------------
-   **Comprehensive Library**: Implements a wide range of popular and effective
    RGB vegetation indices.
-   **Normalized Inputs**: Assumes input channels are normalized to a floating-point
    range (e.g., 0.0 to 1.0) for consistent calculations.
-   **Dispatcher Function**: A central `calculate_rgb_indices` function that can
    compute multiple indices at once from a dictionary of bands.
-   **Extensibility**: The `RGB_INDEX_REGISTRY` allows new indices to be easily
    added without modifying the core logic.
-   **Numerical Stability**: Includes `EPSILON` handling to prevent division-by-zero
    errors in index formulas.

Available Indices:
------------------
-   **VARI (Visible Atmospherically Resistant Index)**: Measures the "greenness"
    of vegetation, designed to be less sensitive to atmospheric effects.
-   **NGRDI (Normalized Green-Red Difference Index)**: Similar to NDVI, but uses
    the green and red bands. Higher values indicate healthier vegetation.
-   **GLI (Green Leaf Index)**: Emphasizes the green portion of the spectrum to
    estimate leaf area and chlorophyll content.
-   **TGI (Triangular Greenness Index)**: Estimates chlorophyll content based on
    the area of a triangle formed by red, green, and blue wavelengths.
-   **ExG (Excess Green Index)**: A widely used index that highlights green
    vegetation against a soil background.
-   **ExR (Excess Red Index)**: Complements ExG by highlighting red tones, which
    can be useful for identifying senescent or stressed vegetation.
-   **CIVE (Color Index of Vegetation Extraction)**: Designed to highlight green
    vegetation while suppressing the effects of soil and shadows.
-   **VEG (Vegetative Index)**: Another index that separates green vegetation by
    leveraging the green band's relationship with red and blue.
-   **COM (Combined Index)**: A combination of ExG, CIVE, and VEG to create a
    more robust vegetation segmentation.
-   **MGRVI (Modified Green-Red Vegetation Index)**: A modification of NGRDI that
    squares the bands to enhance the contrast between vegetation and background.
-   **RGRI (Red-Green Ratio Index)**: A simple ratio that is sensitive to
    chlorophyll content.

Core Functionality:
-------------------
-   `calculate_rgb_indices(bands: Dict[str, np.ndarray], indices: List[str])`:
    The main entry point for calculating one or more indices.
-   `RGB_INDEX_REGISTRY`: A dictionary mapping index names to their respective
    calculation functions and required bands.
"""

import numpy as np
from typing import Dict, List, Callable, Tuple

# Epsilon for numerical stability to avoid division by zero
EPSILON = 1e-8

# --- Index Calculation Functions ---

def _calculate_vari(R: np.ndarray, G: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Calculates Visible Atmospherically Resistant Index (VARI)."""
    return (G - R) / (G + R - B + EPSILON)

def _calculate_ngrdi(R: np.ndarray, G: np.ndarray) -> np.ndarray:
    """Calculates Normalized Green-Red Difference Index (NGRDI)."""
    return (G - R) / (G + R + EPSILON)

def _calculate_gli(R: np.ndarray, G: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Calculates Green Leaf Index (GLI)."""
    return (2 * G - R - B) / (2 * G + R + B + EPSILON)

def _calculate_tgi(R: np.ndarray, G: np.ndarray, B: np.ndarray) -> np.ndarray:
    """
    Calculates Triangular Greenness Index (TGI).
    Assumes specific wavelengths for R (670nm), G (550nm), B (480nm).
    The formula is scale-invariant, so it works on normalized RGB values.
    """
    # The formula is -0.5 * [ (lambda_R - lambda_B) * (R - G) - (lambda_R - lambda_G) * (R - B) ]
    # lambda_R = 670, lambda_G = 550, lambda_B = 480
    # (670 - 480) = 190
    # (670 - 550) = 120
    # Simplified: -0.5 * [ 190 * (R - G) - 120 * (R - B) ]
    return -0.5 * (190 * (R - G) - 120 * (R - B))

def _calculate_exg(R: np.ndarray, G: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Calculates Excess Green (ExG) Index."""
    return 2 * G - R - B

def _calculate_exr(R: np.ndarray, G: np.ndarray) -> np.ndarray:
    """Calculates Excess Red (ExR) Index."""
    return 1.4 * R - G

def _calculate_cive(R: np.ndarray, G: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Calculates Color Index of Vegetation Extraction (CIVE)."""
    return 0.441 * R - 0.811 * G + 0.385 * B + 18.78745

def _calculate_veg(R: np.ndarray, G: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Calculates Vegetative (VEG) Index."""
    # Ensure R is not zero before division
    return G / (np.power(R, 0.667) * np.power(B, 0.333) + EPSILON)

def _calculate_mgrvi(R: np.ndarray, G: np.ndarray) -> np.ndarray:
    """Calculates Modified Green-Red Vegetation Index (MGRVI)."""
    return (np.power(G, 2) - np.power(R, 2)) / (np.power(G, 2) + np.power(R, 2) + EPSILON)

def _calculate_rgri(R: np.ndarray, G: np.ndarray) -> np.ndarray:
    """Calculates Red-Green Ratio Index (RGRI)."""
    return R / (G + EPSILON)

# --- Combined Index ---

def _calculate_com(bands: Dict[str, np.ndarray]) -> np.ndarray:
    """
    Calculates a Combined Index (COM) for robust vegetation segmentation.
    This is a custom index that aggregates the results of ExG, CIVE, and VEG.
    """
    exg = _calculate_exg(bands['R'], bands['G'], bands['B'])
    cive = _calculate_cive(bands['R'], bands['G'], bands['B'])
    veg = _calculate_veg(bands['R'], bands['G'], bands['B'])
    
    # Normalize each index to a 0-1 range before combining to balance their contributions
    exg_norm = (exg - np.min(exg)) / (np.max(exg) - np.min(exg) + EPSILON)
    cive_norm = (cive - np.min(cive)) / (np.max(cive) - np.min(cive) + EPSILON)
    veg_norm = (veg - np.min(veg)) / (np.max(veg) - np.min(veg) + EPSILON)
    
    # Combine them. A simple average is a good starting point.
    com = 0.25 * exg_norm + 0.3 * cive_norm + 0.45 * veg_norm
    return com


# --- Index Registry ---

RGB_INDEX_REGISTRY: Dict[str, Tuple[Callable, List[str]]] = {
    'VARI': (_calculate_vari, ['R', 'G', 'B']),
    'NGRDI': (_calculate_ngrdi, ['R', 'G']),
    'GLI': (_calculate_gli, ['R', 'G', 'B']),
    'TGI': (_calculate_tgi, ['R', 'G', 'B']),
    'ExG': (_calculate_exg, ['R', 'G', 'B']),
    'ExR': (_calculate_exr, ['R', 'G']),
    'CIVE': (_calculate_cive, ['R', 'G', 'B']),
    'VEG': (_calculate_veg, ['R', 'G', 'B']),
    'MGRVI': (_calculate_mgrvi, ['R', 'G']),
    'RGRI': (_calculate_rgri, ['R', 'G']),
    # Special case for combined index that needs the whole band dictionary
    'COM': (lambda R, G, B, **kwargs: _calculate_com(kwargs['bands']), ['R', 'G', 'B']),
}

def get_available_rgb_indices() -> List[str]:
    """Returns a list of all available RGB index names."""
    return list(RGB_INDEX_REGISTRY.keys())

def calculate_rgb_indices(
    bands: Dict[str, np.ndarray],
    indices: List[str]
) -> Dict[str, np.ndarray]:
    """
    Calculates multiple RGB-based vegetation indices from a dictionary of bands.

    Args:
        bands (Dict[str, np.ndarray]): A dictionary where keys are band names
            (e.g., 'R', 'G', 'B') and values are NumPy arrays of the same shape.
            The band values should be normalized (e.g., 0.0 to 1.0).
        indices (List[str]): A list of index names to calculate.

    Returns:
        Dict[str, np.ndarray]: A dictionary where keys are the calculated
            index names and values are the resulting NumPy arrays.
            
    Raises:
        ValueError: If an unknown index is requested or a required band is missing.
    """
    results = {}
    band_keys = bands.keys()

    for index_name in indices:
        index_name_upper = index_name.upper()
        if index_name_upper not in RGB_INDEX_REGISTRY:
            raise ValueError(f"Unknown RGB index '{index_name}'. Available indices: {get_available_rgb_indices()}")

        func, required_bands = RGB_INDEX_REGISTRY[index_name_upper]

        # Check if all required bands are present
        if not all(band in band_keys for band in required_bands):
            raise ValueError(f"Index '{index_name_upper}' requires bands {required_bands}, but only {list(band_keys)} were provided.")

        # Prepare arguments for the calculation function
        kwargs = {band: bands[band] for band in required_bands}
        
        # Special handling for combined indices that need the full `bands` dict
        if index_name_upper == 'COM':
            kwargs['bands'] = bands

        # Calculate and store the result
        results[index_name_upper] = func(**kwargs)
        
    return results

# --- Example Usage ---
if __name__ == '__main__':
    print("--- RGB Vegetation Index Module Demo ---")

    # 1. Create dummy RGB image data (normalized to 0-1)
    # Let's simulate a 10x10 image with a "vegetation" patch and a "soil" patch
    image_shape = (10, 10)
    R = np.full(image_shape, 0.5)  # Soil: brownish
    G = np.full(image_shape, 0.3)
    B = np.full(image_shape, 0.1)

    # Vegetation patch (more green, less red)
    R[2:8, 2:8] = 0.1
    G[2:8, 2:8] = 0.6
    B[2:8, 2:8] = 0.2
    
    bands_dict = {'R': R, 'G': G, 'B': B}
    print(f"Created a dummy {image_shape} image with a vegetation patch.")

    # 2. Define the list of indices to calculate
    indices_to_calculate = ['VARI', 'NGRDI', 'ExG', 'TGI']
    print(f"\nCalculating indices: {indices_to_calculate}")

    # 3. Calculate the indices
    try:
        calculated_indices = calculate_rgb_indices(bands_dict, indices_to_calculate)

        # 4. Print the mean values for vegetation and soil areas for one index
        print("\n--- Analysis of VARI Index ---")
        vari_map = calculated_indices['VARI']
        
        veg_mask = np.zeros(image_shape, dtype=bool)
        veg_mask[2:8, 2:8] = True
        
        soil_mask = ~veg_mask

        mean_vari_veg = np.mean(vari_map[veg_mask])
        mean_vari_soil = np.mean(vari_map[soil_mask])

        print(f"Mean VARI for vegetation patch: {mean_vari_veg:.4f}")
        print(f"Mean VARI for soil patch: {mean_vari_soil:.4f}")

        if mean_vari_veg > mean_vari_soil:
            print("As expected, VARI is higher for the vegetation patch.")
        else:
            print("Warning: VARI was not higher for the vegetation patch, check formula.")

        print("\n--- Analysis of ExG Index ---")
        exg_map = calculated_indices['ExG']
        mean_exg_veg = np.mean(exg_map[veg_mask])
        mean_exg_soil = np.mean(exg_map[soil_mask])
        
        print(f"Mean ExG for vegetation patch: {mean_exg_veg:.4f}")
        print(f"Mean ExG for soil patch: {mean_exg_soil:.4f}")

        if mean_exg_veg > mean_exg_soil:
            print("As expected, ExG is higher for the vegetation patch.")
        else:
            print("Warning: ExG was not higher for the vegetation patch, check formula.")

    except ValueError as e:
        print(f"An error occurred: {e}")

    # 5. Demonstrate error handling
    print("\n--- Testing Error Handling ---")
    try:
        # Request an unknown index
        calculate_rgb_indices(bands_dict, ['FAKE_INDEX'])
    except ValueError as e:
        print(f"Successfully caught error for unknown index: {e}")

    try:
        # Provide incomplete bands
        incomplete_bands = {'R': R, 'B': B}
        calculate_rgb_indices(incomplete_bands, ['VARI'])
    except ValueError as e:
        print(f"Successfully caught error for missing bands: {e}")
```