"""
Geospatial Utilities for Yield Estimation
=========================================

This module provides a suite of utility functions for handling geospatial data,
which is a common requirement in agricultural yield estimation, especially when
working with satellite or drone imagery. These functions help in converting
between different coordinate systems, calculating geometric properties, and
handling raster data.

Core Functionalities:
---------------------
1.  **Coordinate Transformations**:
    -   Functions to convert between pixel coordinates (row, col) in an image
      and real-world geographic coordinates (latitude, longitude).
    -   This is essential for georeferencing predictions and aligning data from
      different sources. It requires the geotransform metadata from a raster
      file (e.g., a GeoTIFF).

2.  **Geometric Calculations**:
    -   `haversine_distance`: Calculates the great-circle distance between two
      points on the Earth's surface, given their latitudes and longitudes. This
      is more accurate than Euclidean distance for geographic coordinates.
    -   `calculate_area`: Computes the real-world area of a polygon defined by a
      set of geographic coordinates. This is crucial for estimating yield based
      on the area of segmented regions.

3.  **Raster I/O**:
    -   Wrapper functions around libraries like `rasterio` or `gdal` to simplify
      the reading of GeoTIFF files.
    -   These functions can extract the image data (as a NumPy array), the
      geotransform, and the coordinate reference system (CRS).

4.  **Vector Operations**:
    -   Utilities for working with vector data formats like Shapefiles or GeoJSON.
    -   `get_bounds_from_shapefile`: Extracts the bounding box of a farm or field
      from a shapefile, which can be used to clip raster data to a specific
      area of interest.

Dependencies:
-------------
This module relies on established geospatial libraries:
-   **GDAL/Rasterio**: For reading and writing raster data formats.
-   **Pyproj**: For performing cartographic projections and transformations.
-   **Shapely**: For geometric operations on vector data.
-   **Numpy**: For numerical operations.

These utilities form a foundational layer that enables the yield estimation
pipeline to be spatially aware, allowing for accurate and meaningful analysis of
agricultural data in a real-world context.
"""

import numpy as np
from typing import Tuple, List

# Attempt to import core geospatial libraries. Provide helpful errors if not installed.
try:
    from osgeo import gdal, osr
except ImportError:
    gdal = None
    osr = None
    # logging.warning("GDAL/osgeo library not found. Geospatial functions will be unavailable.")

try:
    import pyproj
except ImportError:
    pyproj = None
    # logging.warning("pyproj library not found. Coordinate transformation functions will be unavailable.")

try:
    from shapely.geometry import Polygon
    from shapely.ops import transform as shapely_transform
except ImportError:
    Polygon = None
    shapely_transform = None
    # logging.warning("Shapely library not found. Geometric area calculations will be unavailable.")


# --- Coordinate and Projection Functions ---

def get_raster_info(raster_path: str) -> Tuple[gdal.Dataset, np.ndarray, Tuple, str]:
    """
    Reads a raster file and returns its dataset object, data array, geotransform, and projection.

    Args:
        raster_path (str): Path to the raster file (e.g., GeoTIFF).

    Returns:
        A tuple containing:
        - gdal.Dataset: The opened GDAL dataset object.
        - np.ndarray: The raster data as a NumPy array.
        - Tuple: The geotransform tuple (top-left-x, pixel-width, 0, top-left-y, 0, pixel-height).
        - str: The projection in Well-Known Text (WKT) format.
    """
    if gdal is None:
        raise ImportError("GDAL/osgeo is required for raster operations.")
    
    dataset = gdal.Open(raster_path)
    if dataset is None:
        raise FileNotFoundError(f"Could not open raster file at: {raster_path}")
        
    geotransform = dataset.GetGeoTransform()
    projection = dataset.GetProjection()
    band = dataset.GetRasterBand(1) # Assuming single-band for simplicity, extend if needed
    array = band.ReadAsArray()
    
    return dataset, array, geotransform, projection

def pixel_to_geo(px: int, py: int, geotransform: Tuple) -> Tuple[float, float]:
    """
    Converts pixel coordinates (x, y) to geographic coordinates.

    Args:
        px (int): Pixel x-coordinate (column).
        py (int): Pixel y-coordinate (row).
        geotransform (Tuple): The geotransform tuple from a GDAL dataset.

    Returns:
        A tuple (longitude, latitude).
    """
    ul_x, x_res, _, ul_y, _, y_res = geotransform
    lon = ul_x + (px * x_res)
    lat = ul_y + (py * y_res)
    return lon, lat

def geo_to_pixel(lon: float, lat: float, geotransform: Tuple) -> Tuple[int, int]:
    """
    Converts geographic coordinates (longitude, latitude) to pixel coordinates.

    Args:
        lon (float): Longitude.
        lat (float): Latitude.
        geotransform (Tuple): The geotransform tuple from a GDAL dataset.

    Returns:
        A tuple (pixel_x, pixel_y).
    """
    ul_x, x_res, _, ul_y, _, y_res = geotransform
    px = int((lon - ul_x) / x_res)
    py = int((lat - ul_y) / y_res)
    return px, py

def reproject_coordinates(lons: List[float], lats: List[float], src_crs: str, dst_crs: str) -> Tuple[List[float], List[float]]:
    """
    Reprojects a list of coordinates from a source CRS to a destination CRS.

    Args:
        lons (List[float]): List of longitudes.
        lats (List[float]): List of latitudes.
        src_crs (str): Source Coordinate Reference System (e.g., 'EPSG:4326' for WGS84).
        dst_crs (str): Destination Coordinate Reference System (e.g., 'EPSG:32632' for a UTM zone).

    Returns:
        A tuple of two lists: (reprojected_lons, reprojected_lats).
    """
    if pyproj is None:
        raise ImportError("pyproj is required for coordinate reprojection.")

    transformer = pyproj.Transformer.from_crs(src_crs, dst_crs, always_xy=True)
    new_lons, new_lats = transformer.transform(lons, lats)
    return new_lons, new_lats

# --- Geometric Calculations ---

def haversine_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """
    Calculate the great-circle distance between two points on the earth (specified in decimal degrees).

    Args:
        lon1, lat1: Longitude and latitude of the first point.
        lon2, lat2: Longitude and latitude of the second point.

    Returns:
        The distance in kilometers.
    """
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    r = 6371  # Radius of Earth in kilometers
    return c * r

def calculate_polygon_area(coords: List[Tuple[float, float]], crs: str = 'EPSG:4326') -> float:
    """
    Calculates the area of a polygon defined by geographic coordinates.
    The polygon is reprojected to an equal-area projection for accuracy.

    Args:
        coords (List[Tuple[float, float]]): A list of (lon, lat) tuples defining the polygon vertices.
        crs (str): The Coordinate Reference System of the input coordinates.

    Returns:
        The area of the polygon in square meters.
    """
    if Polygon is None or shapely_transform is None or pyproj is None:
        raise ImportError("Shapely and pyproj are required for area calculation.")

    polygon_geom = Polygon(coords)
    
    # Define source and destination CRS
    source_crs = pyproj.CRS(crs)
    # Use a world-wide equal area projection for accurate area calculation
    # World Mollweide projection
    equal_area_crs = pyproj.CRS("+proj=moll +lon_0=0 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs")

    # Define the transformation
    project = pyproj.Transformer.from_crs(source_crs, equal_area_crs, always_xy=True).transform

    # Apply the transformation to the polygon
    transformed_polygon = shapely_transform(project, polygon_geom)

    return transformed_polygon.area


# --- Example Usage ---
if __name__ == '__main__':
    print("--- Geospatial Utilities Demo ---")

    # Note: Running this demo requires a dummy raster file and GDAL installed.
    # We will simulate the geotransform for demonstration purposes.
    
    # 1. Coordinate Conversion Demo
    print("\n[1. Coordinate Conversion]")
    # Typical geotransform for a satellite image tile
    # Top-left X, X-resolution, 0, Top-left Y, 0, Y-resolution
    mock_geotransform = (499980.0, 10.0, 0.0, 5400000.0, 0.0, -10.0)
    
    px, py = 100, 200
    lon, lat = pixel_to_geo(px, py, mock_geotransform)
    print(f"  Pixel ({px}, {py}) -> Geo ({lon:.2f}, {lat:.2f})")
    
    back_px, back_py = geo_to_pixel(lon, lat, mock_geotransform)
    print(f"  Geo ({lon:.2f}, {lat:.2f}) -> Pixel ({back_px}, {back_py})")
    assert (px, py) == (back_px, back_py)
    print("  Conversion successful.")

    # 2. Haversine Distance Demo
    print("\n[2. Haversine Distance]")
    # New York to London
    ny_lon, ny_lat = -74.0060, 40.7128
    ldn_lon, ldn_lat = -0.1278, 51.5074
    distance = haversine_distance(ny_lon, ny_lat, ldn_lon, ldn_lat)
    print(f"  Distance from New York to London: {distance:.2f} km")
    assert 5500 < distance < 5600

    # 3. Polygon Area Calculation Demo
    print("\n[3. Polygon Area Calculation]")
    if Polygon and pyproj:
        # A small square approximately 1km x 1km near the equator
        square_coords = [
            (0.0, 0.0),
            (0.01, 0.0),
            (0.01, 0.01),
            (0.0, 0.01),
            (0.0, 0.0)
        ]
        area_sq_meters = calculate_polygon_area(square_coords)
        area_sq_km = area_sq_meters / 1_000_000
        print(f"  Area of a ~0.01x0.01 degree square: {area_sq_meters:.2f} m^2 (~{area_sq_km:.2f} km^2)")
        # Should be roughly 1.23 sq km
        assert 1.2e6 < area_sq_meters < 1.3e6
        print("  Area calculation successful.")
    else:
        print("  Skipping area calculation demo (Shapely or pyproj not installed).")
        
    print("\nGeospatial utilities demo finished.")
