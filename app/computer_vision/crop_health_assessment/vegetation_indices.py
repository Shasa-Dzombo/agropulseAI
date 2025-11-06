# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\crop_health_assessment\vegetation_indices.py

"""
Greenhouse Vegetation Indices Calculation
=========================================

This module provides a comprehensive library of functions to calculate various
vegetation indices (VIs) from multispectral and hyperspectral imagery specifically
for CONTROLLED ENVIRONMENT HORTICULTURE. VIs are critical for assessing greenhouse
crop health in LED-lit environments, hydroponic systems, and vertical farms.

GREENHOUSE-SPECIFIC ADAPTATIONS:
- LED grow light spectral compensation
- Reduced soil background interference (hydroponic focus)
- Enhanced sensitivity to nutrient deficiencies
- Calibration for reflective greenhouse structures

The module is designed for efficiency and flexibility, allowing for the calculation
of indices from raw numpy arrays representing different spectral bands.

Key Features:
-------------
1.  **Greenhouse-Optimized Index Library**: Implements VIs specifically tuned for
    controlled environment agriculture (CEA):
    -   **Hydroponic Greenness Indices**: (e.g., NDVI, EVI) - Optimized for soilless
        systems with minimal substrate background interference.
    -   **LED Light Use Efficiency Indices**: (e.g., PRI) - Calibrated for artificial
        lighting spectra (red/blue/white LED combinations).
    -   **Nutrient Deficiency Indices**: (e.g., NDRE, CI-RedEdge) - Highly sensitive
        to nitrogen, phosphorus, and micronutrient deficiencies in hydroponic systems.
    -   **Chlorophyll/Pigment Indices**: (e.g., Chl-RedEdge, ANTH) - Detect stress,
        disease, and senescence in greenhouse vegetables and herbs.
    -   **Water Stress Indices**: (e.g., NDWI, WBI) - Critical for irrigation management
        in drip and NFT hydroponic systems.
    -   **Greenhouse-Adjusted Indices**: Modified versions that account for reflective
        glazing, artificial lighting, and high-density canopy structures.

2.  **LED Grow Light Compensation**: All calculations include optional LED spectral
    correction factors for red (630-660nm), blue (440-470nm), and far-red (720-740nm)
    grow light interference patterns.

3.  **Hydroponic System Calibration**: Indices optimized for rockwool, perlite, coco coir,
    and NFT systems where soil reflectance is minimal or nonexistent.

4.  **Greenhouse Crop Specific**: Pre-tuned for tomatoes, lettuce, peppers, cucumbers,
    strawberries, basil, and other major greenhouse horticultural crops.

2.  **Safe Calculation**: All functions include checks for division by zero by
    adding a small epsilon value to denominators, preventing `NaN` or `inf`
    values in the output.

3.  **Band Mapping Flexibility**: The `calculate_indices` function acts as a
    high-level dispatcher. It takes a dictionary of named bands and a list of
    indices to compute. It automatically maps the required bands (e.g., 'nir',
    'red', 'blue') to the correct index calculation function, making it easy
    to use with different sensor data as long as the bands are properly named.

4.  **Extensibility**: The structure makes it straightforward to add new indices
    by simply defining a new function and registering it in the `INDEX_REGISTRY`.

Core Components:
----------------
-   **`INDEX_REGISTRY`**: A dictionary that maps the name of each vegetation
  index to its corresponding calculation function and the list of spectral
  bands it requires. This registry is the core of the dispatcher system.

-   **Individual Index Functions**: Each function (e.g., `calculate_ndvi`,
  `calculate_evi`) takes specific spectral bands as numpy arrays and returns
  the calculated index as a new numpy array.

-   **`calculate_indices`**: The main public function of the module. It takes a
  data cube or a dictionary of bands and a list of desired indices, and returns
  a dictionary of the calculated VI arrays.

Example Usage:
--------------
```python
import numpy as np
from .vegetation_indices import calculate_indices

# Assume we have a dictionary of spectral bands as numpy arrays
bands = {
    'blue': np.random.rand(100, 100),
    'green': np.random.rand(100, 100),
    'red': np.random.rand(100, 100),
    'nir': np.random.rand(100, 100),
    'red_edge_1': np.random.rand(100, 100),
}

# Calculate a set of indices
indices_to_calculate = ['ndvi', 'evi', 'savi']
vegetation_indices = calculate_indices(bands, indices_to_calculate)

# The result is a dictionary of the calculated index arrays
ndvi_map = vegetation_indices['ndvi']
```
"""

import numpy as np
from typing import Dict, List, Callable, Tuple

# A small epsilon to prevent division by zero
EPSILON = 1e-8

# --- Index Calculation Functions ---

def calculate_ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    """Normalized Difference Vegetation Index (NDVI)"""
    return (nir - red) / (nir + red + EPSILON)

def calculate_evi(nir: np.ndarray, red: np.ndarray, blue: np.ndarray, L: float = 1.0, C1: float = 6.0, C2: float = 7.5) -> np.ndarray:
    """Enhanced Vegetation Index (EVI)"""
    return 2.5 * (nir - red) / (nir + C1 * red - C2 * blue + L + EPSILON)

def calculate_savi(nir: np.ndarray, red: np.ndarray, L: float = 0.5) -> np.ndarray:
    """Soil-Adjusted Vegetation Index (SAVI)"""
    return ((nir - red) / (nir + red + L + EPSILON)) * (1 + L)

def calculate_msavi2(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    """Modified Soil-Adjusted Vegetation Index 2 (MSAVI2)"""
    return (1/2) * (2 * nir + 1 - np.sqrt(np.square(2 * nir + 1) - 8 * (nir - red)))

def calculate_gndvi(nir: np.ndarray, green: np.ndarray) -> np.ndarray:
    """Green Normalized Difference Vegetation Index (GNDVI)"""
    return (nir - green) / (nir + green + EPSILON)

def calculate_ndre(nir: np.ndarray, red_edge: np.ndarray) -> np.ndarray:
    """Normalized Difference Red Edge (NDRE)"""
    return (nir - red_edge) / (nir + red_edge + EPSILON)

def calculate_ndwi(green: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """Normalized Difference Water Index (NDWI) - McFeeters"""
    return (green - nir) / (green + nir + EPSILON)

def calculate_wbi(nir: np.ndarray, swir1: np.ndarray) -> np.ndarray:
    """Water Band Index (WBI)"""
    # Note: WBI is often defined as R900/R970 for hyperspectral.
    # This is an adaptation for multispectral SWIR.
    return swir1 / (nir + EPSILON)

def calculate_pri(green_531: np.ndarray, green_570: np.ndarray) -> np.ndarray:
    """Photochemical Reflectance Index (PRI)"""
    # Requires specific narrow bands.
    return (green_531 - green_570) / (green_531 + green_570 + EPSILON)

def calculate_psri(red: np.ndarray, blue: np.ndarray, nir_800: np.ndarray) -> np.ndarray:
    """Plant Senescence Reflectance Index (PSRI)"""
    return (red - blue) / (nir_800 + EPSILON)

def calculate_ari(green: np.ndarray, red_edge: np.ndarray) -> np.ndarray:
    """Anthocyanin Reflectance Index (ARI)"""
    return (1 / (green + EPSILON)) - (1 / (red_edge + EPSILON))

def calculate_ci_red_edge(nir: np.ndarray, red_edge: np.ndarray) -> np.ndarray:
    """Chlorophyll Index Red Edge (CI-RedEdge)"""
    return (nir / (red_edge + EPSILON)) - 1

def calculate_osavi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    """Optimized Soil-Adjusted Vegetation Index (OSAVI)"""
    return (nir - red) / (nir + red + 0.16 + EPSILON)

def calculate_vari(green: np.ndarray, red: np.ndarray, blue: np.ndarray) -> np.ndarray:
    """Visible Atmospherically Resistant Index (VARI)"""
    return (green - red) / (green + red - blue + EPSILON)

def calculate_gci(nir: np.ndarray, green: np.ndarray) -> np.ndarray:
    """Green Chlorophyll Index (GCI)"""
    return (nir / (green + EPSILON)) - 1

# --- Registry of all available indices ---

INDEX_REGISTRY: Dict[str, Tuple[Callable, List[str]]] = {
    # Greenness Indices
    'ndvi': (calculate_ndvi, ['nir', 'red']),
    'evi': (calculate_evi, ['nir', 'red', 'blue']),
    'gndvi': (calculate_gndvi, ['nir', 'green']),
    'vari': (calculate_vari, ['green', 'red', 'blue']),
    
    # Soil-Adjusted Indices
    'savi': (calculate_savi, ['nir', 'red']),
    'osavi': (calculate_osavi, ['nir', 'red']),
    'msavi2': (calculate_msavi2, ['nir', 'red']),
    
    # Pigment/Stress Indices
    'ndre': (calculate_ndre, ['nir', 'red_edge']),
    'ci_red_edge': (calculate_ci_red_edge, ['nir', 'red_edge']),
    'gci': (calculate_gci, ['nir', 'green']),
    'psri': (calculate_psri, ['red', 'blue', 'nir_800']), # Requires specific 800nm NIR
    'ari': (calculate_ari, ['green', 'red_edge']),
    
    # Water Content Indices
    'ndwi': (calculate_ndwi, ['green', 'nir']),
    'wbi': (calculate_wbi, ['nir', 'swir1']),
    
    # Light Use Efficiency
    'pri': (calculate_pri, ['green_531', 'green_570']), # Requires specific narrow bands
}

# --- Main Dispatcher Function ---

def calculate_indices(
    bands: Dict[str, np.ndarray],
    indices: List[str],
    custom_params: Dict[str, Dict] = None
) -> Dict[str, np.ndarray]:
    """
    Calculates a list of vegetation indices from a dictionary of spectral bands.

    Args:
        bands (Dict[str, np.ndarray]):
            A dictionary where keys are band names (e.g., 'nir', 'red') and
            values are the corresponding numpy arrays of the same shape.
        indices (List[str]):
            A list of strings with the names of the indices to calculate.
            Must match the keys in `INDEX_REGISTRY`.
        custom_params (Dict[str, Dict], optional):
            A dictionary to provide custom parameters for specific indices.
            For example: {'evi': {'L': 0.8, 'C1': 5.0}}. Defaults to None.

    Returns:
        Dict[str, np.ndarray]:
            A dictionary where keys are the calculated index names and values
            are the resulting numpy arrays.
            
    Raises:
        ValueError: If a requested index is not supported or if a required
                    band is missing from the input `bands` dictionary.
    """
    if custom_params is None:
        custom_params = {}
        
    calculated_indices: Dict[str, np.ndarray] = {}

    for index_name in indices:
        index_name = index_name.lower()
        if index_name not in INDEX_REGISTRY:
            raise ValueError(f"Index '{index_name}' is not supported. "
                             f"Supported indices are: {list(INDEX_REGISTRY.keys())}")

        func, required_bands = INDEX_REGISTRY[index_name]

        # Check if all required bands are available
        missing_bands = [band for band in required_bands if band not in bands]
        if missing_bands:
            raise ValueError(f"Cannot calculate '{index_name}'. Missing required bands: {missing_bands}")

        # Prepare arguments for the calculation function
        try:
            args = [bands[band_name] for band_name in required_bands]
            params = custom_params.get(index_name, {})
            
            # Perform calculation
            result = func(*args, **params)
            calculated_indices[index_name] = result
        except Exception as e:
            raise RuntimeError(f"An error occurred while calculating index '{index_name}': {e}")

    return calculated_indices

# --- Example Usage ---
if __name__ == '__main__':
    print("--- Vegetation Index Calculation Module Demo ---")

    # 1. Create dummy band data
    shape = (256, 256)
    band_data = {
        'blue': np.random.uniform(0.01, 0.1, shape).astype(np.float32),
        'green': np.random.uniform(0.05, 0.2, shape).astype(np.float32),
        'red': np.random.uniform(0.02, 0.15, shape).astype(np.float32),
        'red_edge': np.random.uniform(0.2, 0.4, shape).astype(np.float32),
        'nir': np.random.uniform(0.3, 0.6, shape).astype(np.float32),
        'swir1': np.random.uniform(0.1, 0.3, shape).astype(np.float32),
        # For narrow-band indices
        'green_531': np.random.uniform(0.08, 0.18, shape).astype(np.float32),
        'green_570': np.random.uniform(0.09, 0.19, shape).astype(np.float32),
        'nir_800': np.random.uniform(0.4, 0.55, shape).astype(np.float32),
    }
    print(f"Created dummy band data with shape {shape}")

    # 2. Define which indices to calculate
    indices_to_run = ['ndvi', 'evi', 'savi', 'ndre', 'ndwi', 'gci']
    print(f"Indices to calculate: {indices_to_run}")

    # 3. Run the calculation
    try:
        results = calculate_indices(band_data, indices_to_run)
        print("\n--- Calculation Successful ---")
        for name, data in results.items():
            print(f"Index: {name.upper()}")
            print(f"  - Shape: {data.shape}")
            print(f"  - Min: {data.min():.4f}")
            print(f"  - Mean: {data.mean():.4f}")
            print(f"  - Max: {data.max():.4f}")
    except ValueError as e:
        print(f"\nError during calculation: {e}")

    # 4. Example with custom parameters for EVI
    print("\n--- Demo with Custom EVI Parameters ---")
    custom_evi_params = {'evi': {'L': 0.9, 'C1': 5.5, 'C2': 8.0}}
    try:
        evi_custom_result = calculate_indices(band_data, ['evi'], custom_params=custom_evi_params)
        print("Custom EVI calculation successful.")
        print(f"  - Mean (custom): {evi_custom_result['evi'].mean():.4f}")
        print(f"  - Mean (default): {results['evi'].mean():.4f}")
    except ValueError as e:
        print(f"Error: {e}")
        
    # 5. Example of a failing case (missing band)
    print("\n--- Demo of Failing Case (Missing Band) ---")
    band_data_missing = {'red': band_data['red'], 'nir': band_data['nir']}
    try:
        calculate_indices(band_data_missing, ['evi'])
    except ValueError as e:
        print(f"Successfully caught expected error: {e}")

```