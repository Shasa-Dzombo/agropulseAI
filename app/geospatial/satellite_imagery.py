"""
Satellite Imagery Processing System

Comprehensive satellite data processing for agriculture monitoring:
- Sentinel-2 and Landsat 8/9 integration
- Vegetation indices (NDVI, NDWI, EVI, SAVI, MSAVI, etc.)
- Cloud masking and atmospheric correction
- Time-series analysis
- Change detection
- Crop health monitoring
- Yield prediction from satellite data

Supports multiple data sources and processing workflows.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
import requests
from scipy import ndimage
from scipy.stats import linregress
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import geopandas as gpd
from shapely.geometry import box, shape
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SatelliteDataSource:
    """Base class for satellite data sources"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SATELLITE_API_KEY")
    
    def search_scenes(
        self,
        bbox: Tuple[float, float, float, float],
        start_date: datetime,
        end_date: datetime,
        cloud_cover_max: float = 20.0
    ) -> List[Dict[str, Any]]:
        """Search for scenes in area and time range"""
        raise NotImplementedError
    
    def download_scene(self, scene_id: str, output_path: str) -> bool:
        """Download scene data"""
        raise NotImplementedError


class Sentinel2DataSource(SatelliteDataSource):
    """Sentinel-2 satellite data source"""
    
    BASE_URL = "https://scihub.copernicus.eu/dhus/search"
    
    def __init__(self, username: str, password: str):
        super().__init__()
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = (username, password)
    
    def search_scenes(
        self,
        bbox: Tuple[float, float, float, float],
        start_date: datetime,
        end_date: datetime,
        cloud_cover_max: float = 20.0
    ) -> List[Dict[str, Any]]:
        """Search Sentinel-2 scenes"""
        
        # Build query
        footprint = f"POLYGON(({bbox[0]} {bbox[1]},{bbox[2]} {bbox[1]},{bbox[2]} {bbox[3]},{bbox[0]} {bbox[3]},{bbox[0]} {bbox[1]}))"
        
        query = {
            "platformname": "Sentinel-2",
            "producttype": "S2MSI2A",  # Level-2A (atmospherically corrected)
            "footprint": f'"Intersects({footprint})"',
            "beginPosition": f"[{start_date.isoformat()}Z TO {end_date.isoformat()}Z]",
            "cloudcoverpercentage": f"[0 TO {cloud_cover_max}]"
        }
        
        try:
            # Build query string
            query_str = " AND ".join([f"{k}:{v}" for k, v in query.items()])
            
            params = {
                "q": query_str,
                "rows": 100,
                "start": 0,
                "format": "json"
            }
            
            response = self.session.get(self.BASE_URL, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            scenes = []
            if "entry" in data.get("feed", {}):
                entries = data["feed"]["entry"]
                if not isinstance(entries, list):
                    entries = [entries]
                
                for entry in entries:
                    scene = {
                        "id": entry["id"],
                        "title": entry["title"],
                        "date": entry["date"][0]["content"] if "date" in entry else None,
                        "cloud_cover": float(entry.get("double", {}).get("cloudcoverpercentage", 100)),
                        "footprint": entry.get("str", {}).get("footprint", ""),
                        "download_url": entry["link"][0]["href"] if "link" in entry else None
                    }
                    scenes.append(scene)
            
            logger.info(f"Found {len(scenes)} Sentinel-2 scenes")
            return scenes
            
        except Exception as e:
            logger.error(f"Failed to search Sentinel-2 scenes: {e}")
            return []
    
    def download_scene(self, scene_id: str, output_path: str) -> bool:
        """Download Sentinel-2 scene"""
        try:
            # In real implementation, download from Copernicus Hub
            # This is a simplified version
            
            url = f"https://scihub.copernicus.eu/dhus/odata/v1/Products('{scene_id}')/$value"
            
            response = self.session.get(url, stream=True)
            response.raise_for_status()
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded scene {scene_id} to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download scene: {e}")
            return False


class Landsat8DataSource(SatelliteDataSource):
    """Landsat 8/9 data source via USGS Earth Explorer API"""
    
    BASE_URL = "https://m2m.cr.usgs.gov/api/api/json/stable"
    
    def __init__(self, username: str, password: str):
        super().__init__()
        self.username = username
        self.password = password
        self.api_key = None
        self._login()
    
    def _login(self) -> bool:
        """Login to USGS API"""
        try:
            payload = {
                "username": self.username,
                "password": self.password
            }
            
            response = requests.post(f"{self.BASE_URL}/login", json=payload)
            response.raise_for_status()
            
            result = response.json()
            if result.get("errorCode"):
                logger.error(f"Login failed: {result.get('errorMessage')}")
                return False
            
            self.api_key = result.get("data")
            logger.info("Logged in to USGS API")
            return True
            
        except Exception as e:
            logger.error(f"Failed to login: {e}")
            return False
    
    def search_scenes(
        self,
        bbox: Tuple[float, float, float, float],
        start_date: datetime,
        end_date: datetime,
        cloud_cover_max: float = 20.0
    ) -> List[Dict[str, Any]]:
        """Search Landsat 8/9 scenes"""
        
        try:
            payload = {
                "datasetName": "landsat_ot_c2_l2",  # Landsat 8-9 Collection 2 Level-2
                "maxResults": 100,
                "startingNumber": 1,
                "sceneFilter": {
                    "spatialFilter": {
                        "filterType": "mbr",  # Minimum bounding rectangle
                        "lowerLeft": {"latitude": bbox[1], "longitude": bbox[0]},
                        "upperRight": {"latitude": bbox[3], "longitude": bbox[2]}
                    },
                    "acquisitionFilter": {
                        "start": start_date.strftime("%Y-%m-%d"),
                        "end": end_date.strftime("%Y-%m-%d")
                    },
                    "cloudCoverFilter": {
                        "max": cloud_cover_max,
                        "min": 0,
                        "includeUnknown": False
                    }
                }
            }
            
            headers = {"X-Auth-Token": self.api_key}
            
            response = requests.post(
                f"{self.BASE_URL}/scene-search",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            
            result = response.json()
            
            scenes = []
            if result.get("data") and result["data"].get("results"):
                for scene in result["data"]["results"]:
                    scenes.append({
                        "id": scene["entityId"],
                        "display_id": scene["displayId"],
                        "date": scene["temporalCoverage"]["startDate"],
                        "cloud_cover": scene.get("cloudCover", 100),
                        "path": scene.get("wrsPath"),
                        "row": scene.get("wrsRow")
                    })
            
            logger.info(f"Found {len(scenes)} Landsat scenes")
            return scenes
            
        except Exception as e:
            logger.error(f"Failed to search Landsat scenes: {e}")
            return []
    
    def download_scene(self, scene_id: str, output_path: str) -> bool:
        """Download Landsat scene"""
        try:
            # Get download options
            payload = {
                "datasetName": "landsat_ot_c2_l2",
                "entityIds": [scene_id]
            }
            
            headers = {"X-Auth-Token": self.api_key}
            
            response = requests.post(
                f"{self.BASE_URL}/download-options",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Request download
            if result.get("data"):
                download_id = result["data"][0]["id"]
                
                download_payload = {
                    "downloads": [{"entityId": scene_id, "productId": download_id}]
                }
                
                download_response = requests.post(
                    f"{self.BASE_URL}/download-request",
                    json=download_payload,
                    headers=headers
                )
                download_response.raise_for_status()
                
                download_result = download_response.json()
                
                if download_result.get("data") and download_result["data"].get("availableDownloads"):
                    url = download_result["data"]["availableDownloads"][0]["url"]
                    
                    # Download file
                    file_response = requests.get(url, stream=True)
                    file_response.raise_for_status()
                    
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    
                    with open(output_path, 'wb') as f:
                        for chunk in file_response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    logger.info(f"Downloaded scene {scene_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to download scene: {e}")
            return False


class VegetationIndexCalculator:
    """Calculate various vegetation indices from satellite bands"""
    
    @staticmethod
    def ndvi(red: np.ndarray, nir: np.ndarray) -> np.ndarray:
        """
        Normalized Difference Vegetation Index
        NDVI = (NIR - Red) / (NIR + Red)
        Range: -1 to 1 (higher = more vegetation)
        """
        with np.errstate(divide='ignore', invalid='ignore'):
            ndvi = (nir - red) / (nir + red)
            ndvi = np.where(np.isfinite(ndvi), ndvi, 0)
        return ndvi
    
    @staticmethod
    def evi(blue: np.ndarray, red: np.ndarray, nir: np.ndarray) -> np.ndarray:
        """
        Enhanced Vegetation Index
        EVI = 2.5 * ((NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1))
        More sensitive to canopy variations
        """
        with np.errstate(divide='ignore', invalid='ignore'):
            evi = 2.5 * ((nir - red) / (nir + 6 * red - 7.5 * blue + 1))
            evi = np.where(np.isfinite(evi), evi, 0)
        return evi
    
    @staticmethod
    def ndwi(green: np.ndarray, nir: np.ndarray) -> np.ndarray:
        """
        Normalized Difference Water Index
        NDWI = (Green - NIR) / (Green + NIR)
        Detects water content in vegetation
        """
        with np.errstate(divide='ignore', invalid='ignore'):
            ndwi = (green - nir) / (green + nir)
            ndwi = np.where(np.isfinite(ndwi), ndwi, 0)
        return ndwi
    
    @staticmethod
    def savi(red: np.ndarray, nir: np.ndarray, L: float = 0.5) -> np.ndarray:
        """
        Soil Adjusted Vegetation Index
        SAVI = ((NIR - Red) / (NIR + Red + L)) * (1 + L)
        Minimizes soil brightness effects
        """
        with np.errstate(divide='ignore', invalid='ignore'):
            savi = ((nir - red) / (nir + red + L)) * (1 + L)
            savi = np.where(np.isfinite(savi), savi, 0)
        return savi
    
    @staticmethod
    def msavi(red: np.ndarray, nir: np.ndarray) -> np.ndarray:
        """
        Modified Soil Adjusted Vegetation Index
        MSAVI = (2*NIR + 1 - sqrt((2*NIR+1)^2 - 8*(NIR-Red))) / 2
        Better for low vegetation cover
        """
        with np.errstate(divide='ignore', invalid='ignore'):
            msavi = (2 * nir + 1 - np.sqrt((2 * nir + 1)**2 - 8 * (nir - red))) / 2
            msavi = np.where(np.isfinite(msavi), msavi, 0)
        return msavi
    
    @staticmethod
    def gndvi(green: np.ndarray, nir: np.ndarray) -> np.ndarray:
        """
        Green Normalized Difference Vegetation Index
        GNDVI = (NIR - Green) / (NIR + Green)
        More sensitive to chlorophyll variation
        """
        with np.errstate(divide='ignore', invalid='ignore'):
            gndvi = (nir - green) / (nir + green)
            gndvi = np.where(np.isfinite(gndvi), gndvi, 0)
        return gndvi
    
    @staticmethod
    def arvi(blue: np.ndarray, red: np.ndarray, nir: np.ndarray) -> np.ndarray:
        """
        Atmospherically Resistant Vegetation Index
        ARVI = (NIR - (2*Red - Blue)) / (NIR + (2*Red - Blue))
        Resistant to atmospheric effects
        """
        with np.errstate(divide='ignore', invalid='ignore'):
            rb = 2 * red - blue
            arvi = (nir - rb) / (nir + rb)
            arvi = np.where(np.isfinite(arvi), arvi, 0)
        return arvi
    
    @staticmethod
    def sipi(red: np.ndarray, nir: np.ndarray, blue: np.ndarray) -> np.ndarray:
        """
        Structure Insensitive Pigment Index
        SIPI = (NIR - Blue) / (NIR - Red)
        Sensitive to carotenoid/chlorophyll ratio
        """
        with np.errstate(divide='ignore', invalid='ignore'):
            sipi = (nir - blue) / (nir - red)
            sipi = np.where(np.isfinite(sipi), sipi, 0)
        return sipi


class CloudMaskProcessor:
    """Cloud detection and masking"""
    
    @staticmethod
    def create_cloud_mask_sentinel2(scene_data: Dict[str, np.ndarray]) -> np.ndarray:
        """
        Create cloud mask for Sentinel-2 using QA band
        Sentinel-2 Level-2A includes Scene Classification Layer (SCL)
        """
        if "SCL" in scene_data:
            scl = scene_data["SCL"]
            
            # SCL values:
            # 0 = No Data, 1 = Saturated/Defective, 2 = Dark Area Pixels
            # 3 = Cloud Shadows, 4 = Vegetation, 5 = Not Vegetated
            # 6 = Water, 7 = Unclassified, 8 = Cloud Medium Probability
            # 9 = Cloud High Probability, 10 = Thin Cirrus, 11 = Snow/Ice
            
            cloud_mask = np.isin(scl, [0, 1, 3, 8, 9, 10])
            return cloud_mask
        else:
            # Fallback to simple threshold method
            return CloudMaskProcessor._simple_cloud_mask(scene_data)
    
    @staticmethod
    def create_cloud_mask_landsat8(scene_data: Dict[str, np.ndarray]) -> np.ndarray:
        """
        Create cloud mask for Landsat 8 using QA_PIXEL band
        """
        if "QA_PIXEL" in scene_data:
            qa = scene_data["QA_PIXEL"]
            
            # Bit positions for Landsat 8 QA_PIXEL:
            # Bit 1: Dilated Cloud
            # Bit 3: Cloud
            # Bit 4: Cloud Shadow
            # Bit 5: Snow
            
            cloud_mask = (
                ((qa & (1 << 1)) > 0) |  # Dilated cloud
                ((qa & (1 << 3)) > 0) |  # Cloud
                ((qa & (1 << 4)) > 0) |  # Cloud shadow
                ((qa & (1 << 5)) > 0)    # Snow
            )
            
            return cloud_mask
        else:
            return CloudMaskProcessor._simple_cloud_mask(scene_data)
    
    @staticmethod
    def _simple_cloud_mask(scene_data: Dict[str, np.ndarray]) -> np.ndarray:
        """
        Simple cloud detection using thresholds
        Clouds are bright in visible bands
        """
        if "blue" in scene_data and "red" in scene_data:
            blue = scene_data["blue"]
            red = scene_data["red"]
            
            # Clouds have high reflectance in all visible bands
            # Normalize to 0-1 if needed
            blue_norm = blue / np.max(blue) if np.max(blue) > 1 else blue
            red_norm = red / np.max(red) if np.max(red) > 1 else red
            
            # Simple threshold
            cloud_mask = (blue_norm > 0.7) & (red_norm > 0.7)
            
            # Morphological operations to refine mask
            cloud_mask = ndimage.binary_dilation(cloud_mask, iterations=2)
            cloud_mask = ndimage.binary_erosion(cloud_mask, iterations=1)
            
            return cloud_mask
        
        return np.zeros((100, 100), dtype=bool)  # Default empty mask
    
    @staticmethod
    def apply_mask(data: np.ndarray, mask: np.ndarray, fill_value: float = np.nan) -> np.ndarray:
        """Apply mask to data"""
        masked = data.copy()
        masked[mask] = fill_value
        return masked


class AtmosphericCorrection:
    """Atmospheric correction for satellite imagery"""
    
    @staticmethod
    def dark_object_subtraction(band: np.ndarray, percentile: float = 1.0) -> np.ndarray:
        """
        Dark Object Subtraction (DOS) method
        Assumes darkest pixels should be near zero
        """
        # Find dark object value
        dark_value = np.percentile(band[band > 0], percentile)
        
        # Subtract from all pixels
        corrected = band - dark_value
        corrected = np.maximum(corrected, 0)  # No negative values
        
        return corrected
    
    @staticmethod
    def rayleigh_correction(
        band: np.ndarray,
        wavelength: float,
        solar_zenith: float,
        altitude: float = 0.0
    ) -> np.ndarray:
        """
        Rayleigh scattering correction
        
        Args:
            band: Input band data
            wavelength: Band wavelength in nanometers
            solar_zenith: Solar zenith angle in degrees
            altitude: Target altitude in meters
        """
        # Rayleigh optical thickness
        tau_r = 0.008569 * (wavelength / 1000) ** (-4) * (1 + 0.0113 * (wavelength / 1000) ** (-2) + 0.00013 * (wavelength / 1000) ** (-4))
        
        # Atmospheric transmittance
        cos_theta = np.cos(np.radians(solar_zenith))
        transmittance = np.exp(-tau_r / cos_theta)
        
        # Apply correction
        corrected = band / transmittance
        
        return corrected
    
    @staticmethod
    def topographic_correction(
        band: np.ndarray,
        dem: np.ndarray,
        solar_azimuth: float,
        solar_zenith: float
    ) -> np.ndarray:
        """
        Topographic (terrain) correction using C-correction method
        
        Args:
            band: Input band data
            dem: Digital elevation model
            solar_azimuth: Solar azimuth angle in degrees
            solar_zenith: Solar zenith angle in degrees
        """
        # Calculate slope and aspect from DEM
        dy, dx = np.gradient(dem)
        slope = np.arctan(np.sqrt(dx**2 + dy**2))
        aspect = np.arctan2(dy, dx)
        
        # Calculate illumination
        solar_azimuth_rad = np.radians(solar_azimuth)
        solar_zenith_rad = np.radians(solar_zenith)
        
        cos_i = (
            np.cos(solar_zenith_rad) * np.cos(slope) +
            np.sin(solar_zenith_rad) * np.sin(slope) * np.cos(solar_azimuth_rad - aspect)
        )
        
        # C-correction
        c = np.mean(band) / np.mean(cos_i)
        corrected = band * (np.cos(solar_zenith_rad) + c) / (cos_i + c)
        
        return corrected


class TimeSeriesAnalyzer:
    """Analyze time series of satellite imagery"""
    
    def __init__(self):
        self.time_series: List[Tuple[datetime, np.ndarray]] = []
    
    def add_observation(self, date: datetime, data: np.ndarray) -> None:
        """Add observation to time series"""
        self.time_series.append((date, data))
        self.time_series.sort(key=lambda x: x[0])
    
    def calculate_trend(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculate temporal trend using linear regression
        
        Returns:
            slope: Rate of change per day
            intercept: Initial value
            r_squared: Goodness of fit
        """
        if len(self.time_series) < 2:
            raise ValueError("Need at least 2 observations for trend analysis")
        
        # Convert dates to days since first observation
        first_date = self.time_series[0][0]
        x = np.array([(date - first_date).days for date, _ in self.time_series])
        
        # Stack all observations
        shape = self.time_series[0][1].shape
        y = np.array([data.flatten() for _, data in self.time_series])
        
        # Perform linear regression for each pixel
        slope = np.zeros(shape)
        intercept = np.zeros(shape)
        r_squared = np.zeros(shape)
        
        for i in range(shape[0]):
            for j in range(shape[1]):
                pixel_values = y[:, i * shape[1] + j]
                
                # Skip if all NaN
                if np.all(np.isnan(pixel_values)):
                    slope[i, j] = np.nan
                    intercept[i, j] = np.nan
                    r_squared[i, j] = np.nan
                    continue
                
                # Remove NaN values
                valid_mask = ~np.isnan(pixel_values)
                if np.sum(valid_mask) < 2:
                    slope[i, j] = np.nan
                    intercept[i, j] = np.nan
                    r_squared[i, j] = np.nan
                    continue
                
                x_valid = x[valid_mask]
                y_valid = pixel_values[valid_mask]
                
                # Linear regression
                result = linregress(x_valid, y_valid)
                slope[i, j] = result.slope
                intercept[i, j] = result.intercept
                r_squared[i, j] = result.rvalue ** 2
        
        return slope, intercept, r_squared
    
    def detect_anomalies(self, threshold: float = 2.0) -> List[Tuple[datetime, np.ndarray]]:
        """
        Detect anomalous observations using z-score
        
        Args:
            threshold: Z-score threshold for anomaly detection
        
        Returns:
            List of (date, anomaly_mask) tuples
        """
        if len(self.time_series) < 3:
            return []
        
        # Stack all observations
        data_stack = np.array([data for _, data in self.time_series])
        
        # Calculate mean and std across time
        mean = np.nanmean(data_stack, axis=0)
        std = np.nanstd(data_stack, axis=0)
        
        # Find anomalies
        anomalies = []
        for date, data in self.time_series:
            z_score = np.abs((data - mean) / std)
            anomaly_mask = z_score > threshold
            
            if np.any(anomaly_mask):
                anomalies.append((date, anomaly_mask))
        
        return anomalies
    
    def calculate_phenology_metrics(self) -> Dict[str, Any]:
        """
        Calculate phenological metrics from time series
        
        Returns:
            Dictionary with metrics:
            - green_up_date: Start of growing season
            - peak_date: Peak vegetation date
            - senescence_date: Start of senescence
            - dormancy_date: End of growing season
            - season_length: Length of growing season (days)
            - max_value: Maximum vegetation index value
            - amplitude: Difference between peak and baseline
        """
        if len(self.time_series) < 4:
            return {}
        
        # Calculate average across spatial dimensions
        dates = [date for date, _ in self.time_series]
        values = [np.nanmean(data) for _, data in self.time_series]
        
        # Find baseline (winter minimum)
        baseline = np.min(values)
        
        # Find peak
        peak_idx = np.argmax(values)
        peak_date = dates[peak_idx]
        max_value = values[peak_idx]
        
        # Calculate amplitude
        amplitude = max_value - baseline
        
        # Define thresholds
        green_up_threshold = baseline + 0.2 * amplitude
        senescence_threshold = baseline + 0.8 * amplitude
        
        # Find green-up (first crossing of threshold)
        green_up_date = None
        for i, value in enumerate(values):
            if value >= green_up_threshold:
                green_up_date = dates[i]
                break
        
        # Find senescence (last crossing of high threshold before decline)
        senescence_date = None
        for i in range(peak_idx, len(values)):
            if values[i] <= senescence_threshold:
                senescence_date = dates[i]
                break
        
        # Find dormancy (return to baseline)
        dormancy_date = None
        if senescence_date:
            for i in range(peak_idx, len(values)):
                if values[i] <= baseline + 0.1 * amplitude:
                    dormancy_date = dates[i]
                    break
        
        # Calculate season length
        season_length = None
        if green_up_date and dormancy_date:
            season_length = (dormancy_date - green_up_date).days
        
        return {
            "green_up_date": green_up_date,
            "peak_date": peak_date,
            "senescence_date": senescence_date,
            "dormancy_date": dormancy_date,
            "season_length": season_length,
            "max_value": max_value,
            "amplitude": amplitude,
            "baseline": baseline
        }


class ChangeDetectionAnalyzer:
    """Detect changes between satellite images"""
    
    @staticmethod
    def image_differencing(
        image1: np.ndarray,
        image2: np.ndarray,
        threshold: Optional[float] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Simple image differencing
        
        Returns:
            difference: Difference image
            change_mask: Binary change mask
        """
        difference = image2 - image1
        
        if threshold is None:
            # Auto-threshold using Otsu's method
            from skimage.filters import threshold_otsu
            threshold = threshold_otsu(np.abs(difference))
        
        change_mask = np.abs(difference) > threshold
        
        return difference, change_mask
    
    @staticmethod
    def change_vector_analysis(
        image1_bands: List[np.ndarray],
        image2_bands: List[np.ndarray],
        threshold: Optional[float] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Change Vector Analysis (CVA) using multiple bands
        
        Returns:
            magnitude: Magnitude of change vector
            direction: Direction of change vector
        """
        # Calculate change vectors
        changes = [band2 - band1 for band1, band2 in zip(image1_bands, image2_bands)]
        
        # Calculate magnitude
        magnitude = np.sqrt(sum(change**2 for change in changes))
        
        # Calculate direction (angle in n-dimensional space)
        if len(changes) == 2:
            direction = np.arctan2(changes[1], changes[0])
        else:
            # For >2 bands, use first two principal components
            from sklearn.decomposition import PCA
            pca = PCA(n_components=2)
            change_stack = np.stack(changes, axis=-1)
            shape = change_stack.shape[:2]
            change_flat = change_stack.reshape(-1, len(changes))
            pca_result = pca.fit_transform(change_flat)
            direction = np.arctan2(pca_result[:, 1], pca_result[:, 0]).reshape(shape)
        
        # Threshold
        if threshold is None:
            threshold = np.percentile(magnitude, 95)
        
        change_mask = magnitude > threshold
        
        return magnitude, change_mask
    
    @staticmethod
    def post_classification_comparison(
        class1: np.ndarray,
        class2: np.ndarray
    ) -> Tuple[np.ndarray, Dict[Tuple[int, int], int]]:
        """
        Post-classification comparison
        
        Returns:
            change_map: Map showing class transitions
            transition_matrix: Count of pixels for each transition
        """
        # Create change map (class1 * 1000 + class2 for unique combinations)
        change_map = class1.astype(int) * 1000 + class2.astype(int)
        
        # Calculate transition matrix
        transitions = {}
        unique_transitions = np.unique(change_map)
        
        for transition in unique_transitions:
            from_class = transition // 1000
            to_class = transition % 1000
            count = np.sum(change_map == transition)
            transitions[(from_class, to_class)] = count
        
        return change_map, transitions


class CropHealthMonitor:
    """Monitor crop health from satellite data"""
    
    def __init__(self):
        self.vi_calculator = VegetationIndexCalculator()
    
    def assess_health(
        self,
        bands: Dict[str, np.ndarray],
        crop_type: str
    ) -> Dict[str, Any]:
        """
        Assess crop health using multiple indicators
        
        Returns:
            Dictionary with health metrics
        """
        # Calculate vegetation indices
        ndvi = self.vi_calculator.ndvi(bands["red"], bands["nir"])
        evi = self.vi_calculator.evi(bands["blue"], bands["red"], bands["nir"])
        
        # Define health thresholds by crop type
        thresholds = self._get_health_thresholds(crop_type)
        
        # Classify health
        health_classes = np.zeros_like(ndvi, dtype=int)
        health_classes[ndvi < thresholds["poor"]] = 0  # Poor
        health_classes[(ndvi >= thresholds["poor"]) & (ndvi < thresholds["moderate"])] = 1  # Moderate
        health_classes[(ndvi >= thresholds["moderate"]) & (ndvi < thresholds["good"])] = 2  # Good
        health_classes[ndvi >= thresholds["good"]] = 3  # Excellent
        
        # Calculate statistics
        total_pixels = ndvi.size
        poor_pct = np.sum(health_classes == 0) / total_pixels * 100
        moderate_pct = np.sum(health_classes == 1) / total_pixels * 100
        good_pct = np.sum(health_classes == 2) / total_pixels * 100
        excellent_pct = np.sum(health_classes == 3) / total_pixels * 100
        
        # Overall health score (0-100)
        health_score = (
            poor_pct * 0 +
            moderate_pct * 33 +
            good_pct * 66 +
            excellent_pct * 100
        )
        
        return {
            "health_score": health_score,
            "health_classes": health_classes,
            "poor_percentage": poor_pct,
            "moderate_percentage": moderate_pct,
            "good_percentage": good_pct,
            "excellent_percentage": excellent_pct,
            "mean_ndvi": np.nanmean(ndvi),
            "mean_evi": np.nanmean(evi),
            "std_ndvi": np.nanstd(ndvi),
            "min_ndvi": np.nanmin(ndvi),
            "max_ndvi": np.nanmax(ndvi)
        }
    
    def _get_health_thresholds(self, crop_type: str) -> Dict[str, float]:
        """Get NDVI thresholds for crop type"""
        # Default thresholds (can be customized per crop)
        default = {
            "poor": 0.3,
            "moderate": 0.5,
            "good": 0.7
        }
        
        # Crop-specific thresholds
        thresholds = {
            "corn": {"poor": 0.4, "moderate": 0.6, "good": 0.75},
            "wheat": {"poor": 0.35, "moderate": 0.55, "good": 0.7},
            "soybean": {"poor": 0.4, "moderate": 0.6, "good": 0.75},
            "rice": {"poor": 0.3, "moderate": 0.5, "good": 0.65},
        }
        
        return thresholds.get(crop_type.lower(), default)
    
    def detect_stress(
        self,
        current_ndvi: np.ndarray,
        historical_ndvi: np.ndarray,
        threshold: float = 0.15
    ) -> np.ndarray:
        """
        Detect crop stress by comparing to historical average
        
        Args:
            current_ndvi: Current NDVI image
            historical_ndvi: Historical average NDVI
            threshold: Difference threshold for stress detection
        
        Returns:
            stress_mask: Binary mask of stressed areas
        """
        difference = historical_ndvi - current_ndvi
        stress_mask = difference > threshold
        
        return stress_mask


class YieldPredictor:
    """Predict crop yield from satellite data"""
    
    def __init__(self):
        self.models: Dict[str, Any] = {}
    
    def train_model(
        self,
        features: np.ndarray,
        yields: np.ndarray,
        crop_type: str
    ) -> None:
        """
        Train yield prediction model
        
        Args:
            features: Array of vegetation indices and other features (n_samples, n_features)
            yields: Actual yield values (n_samples,)
            crop_type: Type of crop
        """
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.model_selection import train_test_split
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            features, yields, test_size=0.2, random_state=42
        )
        
        # Train model
        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        model.fit(X_train, y_train)
        
        # Evaluate
        train_score = model.score(X_train, y_train)
        test_score = model.score(X_test, y_test)
        
        logger.info(f"Trained yield model for {crop_type}: R²={test_score:.3f}")
        
        self.models[crop_type] = {
            "model": model,
            "train_score": train_score,
            "test_score": test_score
        }
    
    def predict_yield(
        self,
        bands: Dict[str, np.ndarray],
        crop_type: str,
        additional_features: Optional[Dict[str, np.ndarray]] = None
    ) -> np.ndarray:
        """
        Predict yield from satellite bands
        
        Returns:
            yield_map: Predicted yield for each pixel
        """
        if crop_type not in self.models:
            raise ValueError(f"No trained model for crop type: {crop_type}")
        
        # Calculate vegetation indices
        vi_calc = VegetationIndexCalculator()
        ndvi = vi_calc.ndvi(bands["red"], bands["nir"])
        evi = vi_calc.evi(bands["blue"], bands["red"], bands["nir"])
        
        # Stack features
        feature_stack = [ndvi, evi]
        
        if additional_features:
            for feature in additional_features.values():
                feature_stack.append(feature)
        
        # Reshape for prediction
        shape = ndvi.shape
        features = np.stack(feature_stack, axis=-1)
        features_flat = features.reshape(-1, features.shape[-1])
        
        # Predict
        model = self.models[crop_type]["model"]
        predictions_flat = model.predict(features_flat)
        yield_map = predictions_flat.reshape(shape)
        
        return yield_map


class SatelliteImageryProcessor:
    """Main processor coordinating all satellite operations"""
    
    def __init__(
        self,
        sentinel2_credentials: Optional[Tuple[str, str]] = None,
        landsat_credentials: Optional[Tuple[str, str]] = None
    ):
        self.sentinel2 = None
        self.landsat = None
        
        if sentinel2_credentials:
            self.sentinel2 = Sentinel2DataSource(*sentinel2_credentials)
        
        if landsat_credentials:
            self.landsat = Landsat8DataSource(*landsat_credentials)
        
        self.vi_calculator = VegetationIndexCalculator()
        self.cloud_mask_processor = CloudMaskProcessor()
        self.atmos_correction = AtmosphericCorrection()
        self.ts_analyzer = TimeSeriesAnalyzer()
        self.change_detector = ChangeDetectionAnalyzer()
        self.health_monitor = CropHealthMonitor()
        self.yield_predictor = YieldPredictor()
    
    def process_field(
        self,
        field_geometry: Any,
        start_date: datetime,
        end_date: datetime,
        source: str = "sentinel2"
    ) -> Dict[str, Any]:
        """
        Complete processing workflow for a field
        
        Args:
            field_geometry: Shapely geometry of field boundary
            start_date: Start date for imagery search
            end_date: End date for imagery search
            source: Data source ("sentinel2" or "landsat")
        
        Returns:
            Dictionary with processing results
        """
        # Get field bounding box
        bbox = field_geometry.bounds
        
        # Search for scenes
        if source == "sentinel2" and self.sentinel2:
            scenes = self.sentinel2.search_scenes(bbox, start_date, end_date)
        elif source == "landsat" and self.landsat:
            scenes = self.landsat.search_scenes(bbox, start_date, end_date)
        else:
            raise ValueError(f"Invalid source or credentials not provided: {source}")
        
        logger.info(f"Found {len(scenes)} scenes for field")
        
        # Process each scene
        results = []
        for scene in scenes[:5]:  # Limit to 5 scenes for example
            # Download and process scene
            # (In real implementation, download and load bands)
            
            # For demonstration, create mock data
            mock_bands = self._create_mock_bands()
            
            # Calculate vegetation indices
            ndvi = self.vi_calculator.ndvi(mock_bands["red"], mock_bands["nir"])
            evi = self.vi_calculator.evi(mock_bands["blue"], mock_bands["red"], mock_bands["nir"])
            
            # Create cloud mask
            cloud_mask = self.cloud_mask_processor.create_cloud_mask_sentinel2(mock_bands)
            
            # Apply cloud mask
            ndvi_masked = self.cloud_mask_processor.apply_mask(ndvi, cloud_mask)
            
            # Add to time series
            scene_date = datetime.fromisoformat(scene["date"].replace("Z", ""))
            self.ts_analyzer.add_observation(scene_date, ndvi_masked)
            
            results.append({
                "date": scene_date,
                "scene_id": scene["id"],
                "ndvi": ndvi_masked,
                "evi": evi,
                "cloud_cover": scene["cloud_cover"]
            })
        
        # Time series analysis
        if len(results) >= 2:
            slope, intercept, r_squared = self.ts_analyzer.calculate_trend()
            phenology = self.ts_analyzer.calculate_phenology_metrics()
        else:
            slope = intercept = r_squared = None
            phenology = {}
        
        return {
            "scenes": results,
            "trend_slope": slope,
            "trend_intercept": intercept,
            "trend_r_squared": r_squared,
            "phenology": phenology
        }
    
    def _create_mock_bands(self, size: Tuple[int, int] = (512, 512)) -> Dict[str, np.ndarray]:
        """Create mock satellite bands for testing"""
        np.random.seed(42)
        
        return {
            "blue": np.random.rand(*size) * 0.3 + 0.1,
            "green": np.random.rand(*size) * 0.4 + 0.1,
            "red": np.random.rand(*size) * 0.3 + 0.05,
            "nir": np.random.rand(*size) * 0.6 + 0.3,
            "SCL": np.random.randint(0, 12, size)
        }


# Example usage
def example_usage():
    """Demonstrate satellite imagery processing"""
    
    # Initialize processor
    processor = SatelliteImageryProcessor(
        sentinel2_credentials=("username", "password"),
        landsat_credentials=("username", "password")
    )
    
    # Define field geometry
    from shapely.geometry import Polygon
    field = Polygon([
        (-93.0, 42.0),
        (-93.0, 42.1),
        (-92.9, 42.1),
        (-92.9, 42.0),
        (-93.0, 42.0)
    ])
    
    # Process field
    results = processor.process_field(
        field_geometry=field,
        start_date=datetime(2024, 5, 1),
        end_date=datetime(2024, 9, 30),
        source="sentinel2"
    )
    
    print(f"Processed {len(results['scenes'])} scenes")
    print(f"Phenology metrics: {results['phenology']}")
    
    # Health assessment
    if results['scenes']:
        latest_scene = results['scenes'][-1]
        mock_bands = processor._create_mock_bands()
        
        health = processor.health_monitor.assess_health(mock_bands, "corn")
        print(f"Health score: {health['health_score']:.1f}")
        print(f"Mean NDVI: {health['mean_ndvi']:.3f}")


if __name__ == "__main__":
    example_usage()
