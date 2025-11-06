"""
Computational Multispectral Sensing Module

Virtual multispectral sensor implementation using computational photography
and LED-based active illumination for NDVI calculation and chlorophyll analysis.

This module enables low-cost devices (CCTV, mobile phones) to perform
multispectral analysis without expensive hardware sensors.

Key Features:
- Virtual multispectral sensing via LED flash patterns
- NDVI (Normalized Difference Vegetation Index) calculation
- Chlorophyll content estimation
- Plant stress detection and quantification
- Temporal health monitoring
- Spatial stress mapping
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import cv2
from enum import Enum


class IlluminationType(Enum):
    """LED illumination types for multispectral capture."""
    RED = "red"  # 660nm
    GREEN = "green"  # 530nm
    BLUE = "blue"  # 470nm
    NIR = "near_infrared"  # 850nm
    WHITE = "white"
    AMBIENT = "ambient"


class HealthStatus(Enum):
    """Plant health classification."""
    EXCELLENT = "excellent"  # NDVI > 0.8
    HEALTHY = "healthy"  # NDVI 0.6-0.8
    MODERATE = "moderate"  # NDVI 0.4-0.6
    STRESSED = "stressed"  # NDVI 0.2-0.4
    CRITICAL = "critical"  # NDVI < 0.2


@dataclass
class MultispectralCapture:
    """Multispectral image capture data."""
    timestamp: datetime
    red_channel: np.ndarray
    nir_channel: np.ndarray
    green_channel: Optional[np.ndarray] = None
    blue_channel: Optional[np.ndarray] = None
    ambient_channel: Optional[np.ndarray] = None
    exposure_time: float = 0.0
    gain: float = 1.0
    device_id: str = ""
    location: Optional[Tuple[float, float]] = None
    metadata: Dict = None


@dataclass
class NDVIResult:
    """NDVI calculation result."""
    ndvi_value: float
    ndvi_map: np.ndarray
    health_status: HealthStatus
    chlorophyll_estimate: float
    stress_level: float
    confidence: float
    timestamp: datetime
    metadata: Dict = None


@dataclass
class ChlorophyllMeasurement:
    """Chlorophyll content measurement."""
    total_chlorophyll: float  # μg/cm²
    chlorophyll_a: float
    chlorophyll_b: float
    carotenoids: float
    health_index: float
    measurement_area: float
    confidence: float
    timestamp: datetime


class MultispectralSensor:
    """
    Virtual multispectral sensor using computational photography.
    
    Uses LED flash patterns and AI to simulate expensive multispectral cameras.
    Works with low-cost CCTV cameras and mobile phone cameras.
    """
    
    def __init__(
        self,
        calibration_data: Optional[Dict] = None,
        device_type: str = "generic"
    ):
        """
        Initialize multispectral sensor.
        
        Args:
            calibration_data: Camera and LED calibration parameters
            device_type: 'cctv', 'mobile', or 'generic'
        """
        self.calibration_data = calibration_data or {}
        self.device_type = device_type
        self.spectral_response = self._load_spectral_response()
        self.calibration_matrix = self._build_calibration_matrix()
        
    def _load_spectral_response(self) -> Dict[str, np.ndarray]:
        """Load spectral response curves for the sensor."""
        # Typical CMOS sensor spectral response
        wavelengths = np.linspace(400, 1000, 600)
        
        # Red channel response (peak ~600nm)
        red_response = np.exp(-((wavelengths - 600) ** 2) / (2 * 50 ** 2))
        
        # Green channel response (peak ~530nm)
        green_response = np.exp(-((wavelengths - 530) ** 2) / (2 * 40 ** 2))
        
        # Blue channel response (peak ~470nm)
        blue_response = np.exp(-((wavelengths - 470) ** 2) / (2 * 40 ** 2))
        
        # NIR response (extended red sensitivity)
        nir_response = np.exp(-((wavelengths - 850) ** 2) / (2 * 80 ** 2))
        
        return {
            'wavelengths': wavelengths,
            'red': red_response,
            'green': green_response,
            'blue': blue_response,
            'nir': nir_response
        }
    
    def _build_calibration_matrix(self) -> np.ndarray:
        """Build calibration matrix for spectral unmixing."""
        if 'calibration_matrix' in self.calibration_data:
            return self.calibration_data['calibration_matrix']
        
        # Default calibration matrix (identity with scaling)
        return np.array([
            [1.0, 0.1, 0.05, 0.0],  # Red channel
            [0.1, 1.0, 0.1, 0.0],   # Green channel
            [0.05, 0.1, 1.0, 0.0],  # Blue channel
            [0.2, 0.1, 0.05, 1.0]   # NIR channel
        ])
    
    def capture_multispectral(
        self,
        capture_function: callable,
        flash_sequence: List[IlluminationType] = None
    ) -> MultispectralCapture:
        """
        Capture multispectral image using LED flash sequence.
        
        Args:
            capture_function: Function to capture image with specific LED
            flash_sequence: Sequence of LED illuminations
            
        Returns:
            MultispectralCapture object with all channels
        """
        if flash_sequence is None:
            flash_sequence = [
                IlluminationType.RED,
                IlluminationType.NIR,
                IlluminationType.GREEN,
                IlluminationType.AMBIENT
            ]
        
        captures = {}
        
        for illumination in flash_sequence:
            # Capture image with specific LED illumination
            image = capture_function(illumination)
            captures[illumination.value] = image
        
        # Extract spectral channels
        red_channel = self._extract_channel(
            captures.get('red'),
            captures.get('ambient'),
            'red'
        )
        
        nir_channel = self._extract_channel(
            captures.get('near_infrared'),
            captures.get('ambient'),
            'nir'
        )
        
        green_channel = self._extract_channel(
            captures.get('green'),
            captures.get('ambient'),
            'green'
        )
        
        return MultispectralCapture(
            timestamp=datetime.now(),
            red_channel=red_channel,
            nir_channel=nir_channel,
            green_channel=green_channel,
            ambient_channel=captures.get('ambient')
        )
    
    def _extract_channel(
        self,
        illuminated: Optional[np.ndarray],
        ambient: Optional[np.ndarray],
        channel: str
    ) -> np.ndarray:
        """
        Extract specific spectral channel from illuminated image.
        
        Args:
            illuminated: Image with LED illumination
            ambient: Image with ambient light only
            channel: Channel type ('red', 'nir', 'green', 'blue')
            
        Returns:
            Extracted spectral channel
        """
        if illuminated is None:
            return np.zeros((480, 640), dtype=np.float32)
        
        # Convert to grayscale if needed
        if len(illuminated.shape) == 3:
            # Weight channels based on target spectrum
            if channel == 'red':
                extracted = illuminated[:, :, 2].astype(np.float32)
            elif channel == 'green':
                extracted = illuminated[:, :, 1].astype(np.float32)
            elif channel == 'blue':
                extracted = illuminated[:, :, 0].astype(np.float32)
            elif channel == 'nir':
                # NIR is captured as red channel with IR-pass filter
                extracted = illuminated[:, :, 2].astype(np.float32)
            else:
                extracted = cv2.cvtColor(illuminated, cv2.COLOR_BGR2GRAY).astype(np.float32)
        else:
            extracted = illuminated.astype(np.float32)
        
        # Subtract ambient contribution if available
        if ambient is not None:
            if len(ambient.shape) == 3:
                ambient_gray = cv2.cvtColor(ambient, cv2.COLOR_BGR2GRAY).astype(np.float32)
            else:
                ambient_gray = ambient.astype(np.float32)
            
            extracted = np.maximum(extracted - ambient_gray * 0.5, 0)
        
        # Normalize
        extracted = extracted / 255.0
        
        return extracted
    
    def calibrate(
        self,
        reference_targets: List[Dict],
        captured_values: List[np.ndarray]
    ) -> Dict:
        """
        Calibrate sensor using reference targets with known reflectance.
        
        Args:
            reference_targets: Known reflectance values
            captured_values: Captured sensor values
            
        Returns:
            Calibration parameters
        """
        # Build linear regression model
        X = np.array([cap.flatten() for cap in captured_values])
        y = np.array([ref['reflectance'] for ref in reference_targets])
        
        # Solve for calibration matrix
        calibration_matrix, residuals, rank, s = np.linalg.lstsq(X, y, rcond=None)
        
        calibration_params = {
            'calibration_matrix': calibration_matrix,
            'residuals': residuals,
            'timestamp': datetime.now(),
            'device_type': self.device_type
        }
        
        return calibration_params
    
    def apply_spectral_unmixing(
        self,
        capture: MultispectralCapture
    ) -> Dict[str, np.ndarray]:
        """
        Apply spectral unmixing to separate pure spectral components.
        
        Args:
            capture: Multispectral capture data
            
        Returns:
            Dictionary of unmixed spectral components
        """
        # Stack channels
        channels = []
        if capture.red_channel is not None:
            channels.append(capture.red_channel)
        if capture.green_channel is not None:
            channels.append(capture.green_channel)
        if capture.blue_channel is not None:
            channels.append(capture.blue_channel)
        if capture.nir_channel is not None:
            channels.append(capture.nir_channel)
        
        stacked = np.stack(channels, axis=-1)
        shape = stacked.shape
        
        # Reshape for matrix multiplication
        pixels = stacked.reshape(-1, len(channels))
        
        # Apply calibration matrix
        unmixed = pixels @ self.calibration_matrix[:len(channels), :len(channels)]
        
        # Reshape back
        unmixed = unmixed.reshape(*shape[:2], len(channels))
        
        return {
            'vegetation': unmixed[..., 0],
            'soil': unmixed[..., 1] if len(channels) > 1 else np.zeros(shape[:2]),
            'water': unmixed[..., 2] if len(channels) > 2 else np.zeros(shape[:2]),
            'other': unmixed[..., 3] if len(channels) > 3 else np.zeros(shape[:2])
        }


class NDVICalculator:
    """
    NDVI (Normalized Difference Vegetation Index) calculator.
    
    NDVI = (NIR - Red) / (NIR + Red)
    
    NDVI ranges from -1 to +1:
    - Dense vegetation: 0.6 to 0.9
    - Sparse vegetation: 0.2 to 0.5
    - Non-vegetation: -0.1 to 0.1
    """
    
    def __init__(self):
        """Initialize NDVI calculator."""
        self.epsilon = 1e-8  # Prevent division by zero
        
    def calculate_ndvi(
        self,
        nir_channel: np.ndarray,
        red_channel: np.ndarray,
        mask: Optional[np.ndarray] = None
    ) -> NDVIResult:
        """
        Calculate NDVI from NIR and Red channels.
        
        Args:
            nir_channel: Near-infrared reflectance (0-1)
            red_channel: Red reflectance (0-1)
            mask: Optional mask to exclude regions
            
        Returns:
            NDVIResult with NDVI map and analysis
        """
        # Calculate NDVI
        numerator = nir_channel - red_channel
        denominator = nir_channel + red_channel + self.epsilon
        ndvi_map = numerator / denominator
        
        # Clip to valid range
        ndvi_map = np.clip(ndvi_map, -1.0, 1.0)
        
        # Apply mask if provided
        if mask is not None:
            ndvi_map = ndvi_map * mask
        
        # Calculate statistics
        valid_pixels = ndvi_map[ndvi_map > 0] if mask is None else ndvi_map[mask > 0]
        mean_ndvi = float(np.mean(valid_pixels)) if len(valid_pixels) > 0 else 0.0
        
        # Classify health status
        health_status = self._classify_health(mean_ndvi)
        
        # Estimate chlorophyll content
        chlorophyll = self._estimate_chlorophyll(mean_ndvi)
        
        # Calculate stress level
        stress_level = max(0.0, 1.0 - (mean_ndvi / 0.8))
        
        # Calculate confidence based on image quality
        confidence = self._calculate_confidence(ndvi_map, valid_pixels)
        
        return NDVIResult(
            ndvi_value=mean_ndvi,
            ndvi_map=ndvi_map,
            health_status=health_status,
            chlorophyll_estimate=chlorophyll,
            stress_level=stress_level,
            confidence=confidence,
            timestamp=datetime.now()
        )
    
    def _classify_health(self, ndvi: float) -> HealthStatus:
        """Classify plant health based on NDVI value."""
        if ndvi >= 0.8:
            return HealthStatus.EXCELLENT
        elif ndvi >= 0.6:
            return HealthStatus.HEALTHY
        elif ndvi >= 0.4:
            return HealthStatus.MODERATE
        elif ndvi >= 0.2:
            return HealthStatus.STRESSED
        else:
            return HealthStatus.CRITICAL
    
    def _estimate_chlorophyll(self, ndvi: float) -> float:
        """
        Estimate chlorophyll content from NDVI.
        
        Returns:
            Chlorophyll content estimate (0-100 scale)
        """
        # Empirical relationship: Chlorophyll ∝ NDVI
        # Normalized to 0-100 scale
        chlorophyll = np.clip((ndvi + 0.2) / 1.2 * 100, 0, 100)
        return float(chlorophyll)
    
    def _calculate_confidence(
        self,
        ndvi_map: np.ndarray,
        valid_pixels: np.ndarray
    ) -> float:
        """Calculate confidence score for NDVI measurement."""
        if len(valid_pixels) == 0:
            return 0.0
        
        # Factors affecting confidence:
        # 1. Number of valid pixels
        pixel_ratio = len(valid_pixels) / ndvi_map.size
        
        # 2. Uniformity (low variance = higher confidence)
        variance = float(np.var(valid_pixels))
        uniformity = 1.0 / (1.0 + variance)
        
        # 3. Value range (values near extremes may be artifacts)
        in_normal_range = np.sum((valid_pixels >= 0.1) & (valid_pixels <= 0.9))
        range_score = in_normal_range / len(valid_pixels)
        
        # Combined confidence
        confidence = (pixel_ratio * 0.3 + uniformity * 0.4 + range_score * 0.3)
        
        return float(np.clip(confidence, 0.0, 1.0))
    
    def calculate_temporal_ndvi(
        self,
        ndvi_series: List[NDVIResult],
        window_days: int = 7
    ) -> Dict:
        """
        Calculate temporal NDVI trends.
        
        Args:
            ndvi_series: Time series of NDVI measurements
            window_days: Moving average window
            
        Returns:
            Temporal analysis results
        """
        if len(ndvi_series) < 2:
            return {
                'trend': 'insufficient_data',
                'rate_of_change': 0.0,
                'forecast': None
            }
        
        # Extract values and timestamps
        values = [r.ndvi_value for r in ndvi_series]
        timestamps = [r.timestamp for r in ndvi_series]
        
        # Calculate trend
        if len(values) >= 3:
            # Linear regression
            x = np.arange(len(values))
            z = np.polyfit(x, values, 1)
            slope = z[0]
            
            if slope > 0.01:
                trend = 'improving'
            elif slope < -0.01:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            slope = 0.0
            trend = 'unknown'
        
        # Calculate rate of change
        if len(values) >= 2:
            time_diff = (timestamps[-1] - timestamps[0]).days
            value_diff = values[-1] - values[0]
            rate_of_change = value_diff / max(time_diff, 1)
        else:
            rate_of_change = 0.0
        
        return {
            'trend': trend,
            'rate_of_change': float(rate_of_change),
            'current_value': values[-1],
            'mean_value': float(np.mean(values)),
            'std_value': float(np.std(values)),
            'forecast': self._forecast_ndvi(values) if len(values) >= 7 else None
        }
    
    def _forecast_ndvi(self, values: List[float], periods: int = 3) -> List[float]:
        """Forecast future NDVI values using simple exponential smoothing."""
        if len(values) < 3:
            return [values[-1]] * periods
        
        # Simple exponential smoothing
        alpha = 0.3
        forecast = [values[0]]
        
        for i in range(1, len(values)):
            forecast.append(alpha * values[i] + (1 - alpha) * forecast[-1])
        
        # Project forward
        future = []
        last_forecast = forecast[-1]
        for _ in range(periods):
            future.append(last_forecast)
        
        return future


class ChlorophyllAnalyzer:
    """
    Advanced chlorophyll content analyzer using spectral indices.
    
    Estimates chlorophyll a, chlorophyll b, and carotenoids using
    multiple spectral indices beyond just NDVI.
    """
    
    def __init__(self):
        """Initialize chlorophyll analyzer."""
        self.ndvi_calc = NDVICalculator()
        
    def analyze_chlorophyll(
        self,
        capture: MultispectralCapture,
        leaf_area: Optional[float] = None
    ) -> ChlorophyllMeasurement:
        """
        Comprehensive chlorophyll analysis.
        
        Args:
            capture: Multispectral image capture
            leaf_area: Leaf area in cm² (for absolute content)
            
        Returns:
            ChlorophyllMeasurement with detailed estimates
        """
        # Calculate NDVI
        ndvi_result = self.ndvi_calc.calculate_ndvi(
            capture.nir_channel,
            capture.red_channel
        )
        
        # Calculate additional indices
        indices = self._calculate_vegetation_indices(capture)
        
        # Estimate chlorophyll components
        chl_a = self._estimate_chlorophyll_a(indices)
        chl_b = self._estimate_chlorophyll_b(indices)
        carotenoids = self._estimate_carotenoids(indices)
        
        # Total chlorophyll
        total_chl = chl_a + chl_b
        
        # Health index (0-100)
        health_index = self._calculate_health_index(indices)
        
        # Measurement area
        measurement_area = leaf_area if leaf_area else 1.0
        
        return ChlorophyllMeasurement(
            total_chlorophyll=total_chl,
            chlorophyll_a=chl_a,
            chlorophyll_b=chl_b,
            carotenoids=carotenoids,
            health_index=health_index,
            measurement_area=measurement_area,
            confidence=ndvi_result.confidence,
            timestamp=datetime.now()
        )
    
    def _calculate_vegetation_indices(
        self,
        capture: MultispectralCapture
    ) -> Dict[str, float]:
        """Calculate multiple vegetation indices."""
        nir = np.mean(capture.nir_channel)
        red = np.mean(capture.red_channel)
        green = np.mean(capture.green_channel) if capture.green_channel is not None else 0
        blue = np.mean(capture.blue_channel) if capture.blue_channel is not None else 0
        
        epsilon = 1e-8
        
        # NDVI: (NIR - Red) / (NIR + Red)
        ndvi = (nir - red) / (nir + red + epsilon)
        
        # GNDVI: (NIR - Green) / (NIR + Green) - sensitive to chlorophyll
        gndvi = (nir - green) / (nir + green + epsilon) if green > 0 else 0
        
        # NDRE: (NIR - RedEdge) / (NIR + RedEdge) - chlorophyll content
        # Approximated with red channel
        ndre = ndvi * 0.95
        
        # MCARI: Modified Chlorophyll Absorption Ratio Index
        # Approximation: function of red and green
        mcari = ((red - green) - 0.2 * (red + green)) * (red / (green + epsilon)) if green > 0 else 0
        
        # CIgreen: Chlorophyll Index Green
        ci_green = (nir / (green + epsilon)) - 1 if green > 0 else 0
        
        # VARI: Visible Atmospherically Resistant Index
        vari = (green - red) / (green + red - blue + epsilon) if blue > 0 else 0
        
        return {
            'ndvi': float(ndvi),
            'gndvi': float(gndvi),
            'ndre': float(ndre),
            'mcari': float(mcari),
            'ci_green': float(ci_green),
            'vari': float(vari)
        }
    
    def _estimate_chlorophyll_a(self, indices: Dict[str, float]) -> float:
        """
        Estimate chlorophyll a content (μg/cm²).
        
        Chlorophyll a is the primary photosynthetic pigment.
        """
        # Empirical relationship with NDVI and GNDVI
        ndvi = indices.get('ndvi', 0)
        gndvi = indices.get('gndvi', 0)
        ci_green = indices.get('ci_green', 0)
        
        # Weighted combination
        chl_a = (ndvi * 30 + gndvi * 25 + ci_green * 5) / 2
        
        return max(0, min(chl_a, 100))  # Typical range: 0-100 μg/cm²
    
    def _estimate_chlorophyll_b(self, indices: Dict[str, float]) -> float:
        """
        Estimate chlorophyll b content (μg/cm²).
        
        Chlorophyll b is an accessory pigment.
        """
        # Typically 25-40% of chlorophyll a
        ndvi = indices.get('ndvi', 0)
        gndvi = indices.get('gndvi', 0)
        
        chl_b = (ndvi * 10 + gndvi * 8) / 2
        
        return max(0, min(chl_b, 40))  # Typical range: 0-40 μg/cm²
    
    def _estimate_carotenoids(self, indices: Dict[str, float]) -> float:
        """Estimate carotenoid content (μg/cm²)."""
        # Carotenoids protect chlorophyll
        vari = indices.get('vari', 0)
        ci_green = indices.get('ci_green', 0)
        
        carotenoids = (vari * 5 + ci_green * 3) / 2
        
        return max(0, min(carotenoids, 20))  # Typical range: 0-20 μg/cm²
    
    def _calculate_health_index(self, indices: Dict[str, float]) -> float:
        """Calculate overall plant health index (0-100)."""
        # Weighted combination of indices
        weights = {
            'ndvi': 0.3,
            'gndvi': 0.25,
            'ndre': 0.2,
            'ci_green': 0.15,
            'vari': 0.1
        }
        
        health_score = 0
        for index, weight in weights.items():
            value = indices.get(index, 0)
            # Normalize to 0-1 range
            normalized = (value + 1) / 2  # Most indices range -1 to 1
            health_score += normalized * weight * 100
        
        return float(np.clip(health_score, 0, 100))


class StressDetector:
    """
    Plant stress detection and classification.
    
    Detects various types of plant stress:
    - Water stress (drought)
    - Nutrient deficiency
    - Disease/pest stress
    - Temperature stress
    - Light stress
    """
    
    def __init__(self):
        """Initialize stress detector."""
        self.ndvi_calc = NDVICalculator()
        self.chl_analyzer = ChlorophyllAnalyzer()
        
    def detect_stress(
        self,
        capture: MultispectralCapture,
        historical_ndvi: Optional[List[float]] = None
    ) -> Dict:
        """
        Detect and classify plant stress.
        
        Args:
            capture: Current multispectral capture
            historical_ndvi: Historical NDVI values for comparison
            
        Returns:
            Stress detection results
        """
        # Calculate current NDVI
        ndvi_result = self.ndvi_calc.calculate_ndvi(
            capture.nir_channel,
            capture.red_channel
        )
        
        # Analyze chlorophyll
        chl_measurement = self.chl_analyzer.analyze_chlorophyll(capture)
        
        # Detect specific stress types
        stress_types = []
        stress_severity = {}
        
        # Water stress detection
        water_stress = self._detect_water_stress(
            ndvi_result,
            chl_measurement,
            historical_ndvi
        )
        if water_stress['detected']:
            stress_types.append('water_stress')
            stress_severity['water_stress'] = water_stress['severity']
        
        # Nutrient stress detection
        nutrient_stress = self._detect_nutrient_stress(chl_measurement)
        if nutrient_stress['detected']:
            stress_types.append('nutrient_deficiency')
            stress_severity['nutrient_deficiency'] = nutrient_stress['severity']
        
        # Overall stress level
        overall_stress = ndvi_result.stress_level
        
        return {
            'stress_detected': len(stress_types) > 0,
            'stress_types': stress_types,
            'stress_severity': stress_severity,
            'overall_stress_level': overall_stress,
            'ndvi_value': ndvi_result.ndvi_value,
            'health_status': ndvi_result.health_status.value,
            'chlorophyll_health': chl_measurement.health_index,
            'recommendations': self._generate_recommendations(stress_types, stress_severity),
            'confidence': ndvi_result.confidence
        }
    
    def _detect_water_stress(
        self,
        ndvi_result: NDVIResult,
        chl_measurement: ChlorophyllMeasurement,
        historical_ndvi: Optional[List[float]]
    ) -> Dict:
        """Detect water stress indicators."""
        detected = False
        severity = 0.0
        
        # Indicator 1: Low NDVI
        if ndvi_result.ndvi_value < 0.5:
            detected = True
            severity += 0.3
        
        # Indicator 2: Rapid NDVI decline
        if historical_ndvi and len(historical_ndvi) >= 3:
            recent_decline = historical_ndvi[-1] - historical_ndvi[-3]
            if recent_decline < -0.1:
                detected = True
                severity += 0.4
        
        # Indicator 3: High stress level
        if ndvi_result.stress_level > 0.6:
            detected = True
            severity += 0.3
        
        return {
            'detected': detected,
            'severity': min(severity, 1.0),
            'indicators': ['low_ndvi', 'rapid_decline', 'high_stress']
        }
    
    def _detect_nutrient_stress(
        self,
        chl_measurement: ChlorophyllMeasurement
    ) -> Dict:
        """Detect nutrient deficiency stress."""
        detected = False
        severity = 0.0
        deficient_nutrients = []
        
        # Low chlorophyll indicates nutrient deficiency
        if chl_measurement.total_chlorophyll < 40:
            detected = True
            severity += 0.4
        
        # Low chlorophyll a (nitrogen deficiency)
        if chl_measurement.chlorophyll_a < 25:
            detected = True
            severity += 0.3
            deficient_nutrients.append('nitrogen')
        
        # Abnormal chlorophyll a/b ratio
        if chl_measurement.chlorophyll_a > 0:
            ratio = chl_measurement.chlorophyll_b / chl_measurement.chlorophyll_a
            if ratio < 0.2 or ratio > 0.5:
                detected = True
                severity += 0.2
                deficient_nutrients.append('multiple')
        
        # Low carotenoids
        if chl_measurement.carotenoids < 5:
            detected = True
            severity += 0.1
        
        return {
            'detected': detected,
            'severity': min(severity, 1.0),
            'deficient_nutrients': deficient_nutrients
        }
    
    def _generate_recommendations(
        self,
        stress_types: List[str],
        stress_severity: Dict[str, float]
    ) -> List[str]:
        """Generate actionable recommendations based on detected stress."""
        recommendations = []
        
        if 'water_stress' in stress_types:
            severity = stress_severity.get('water_stress', 0)
            if severity > 0.7:
                recommendations.append("URGENT: Immediate irrigation required")
            elif severity > 0.4:
                recommendations.append("Increase irrigation frequency")
            else:
                recommendations.append("Monitor soil moisture closely")
        
        if 'nutrient_deficiency' in stress_types:
            recommendations.append("Soil test recommended")
            recommendations.append("Consider nitrogen-rich fertilizer application")
            recommendations.append("Check pH levels")
        
        if not stress_types:
            recommendations.append("Plant health is good - maintain current practices")
        
        return recommendations
    
    def create_stress_map(
        self,
        ndvi_map: np.ndarray,
        threshold: float = 0.5
    ) -> Dict:
        """
        Create spatial stress map highlighting stressed areas.
        
        Args:
            ndvi_map: NDVI values for each pixel
            threshold: NDVI threshold for stress detection
            
        Returns:
            Stress map and statistics
        """
        # Identify stressed pixels
        stress_mask = ndvi_map < threshold
        
        # Calculate stress intensity (inverse of NDVI)
        stress_intensity = np.where(stress_mask, 1.0 - ndvi_map / threshold, 0)
        
        # Spatial statistics
        total_pixels = ndvi_map.size
        stressed_pixels = np.sum(stress_mask)
        stress_percentage = (stressed_pixels / total_pixels) * 100
        
        # Find stress hotspots (connected regions)
        stress_mask_uint8 = (stress_mask * 255).astype(np.uint8)
        num_hotspots, labels = cv2.connectedComponents(stress_mask_uint8)
        
        return {
            'stress_map': stress_intensity,
            'stress_mask': stress_mask,
            'stress_percentage': float(stress_percentage),
            'stressed_pixels': int(stressed_pixels),
            'total_pixels': int(total_pixels),
            'num_hotspots': int(num_hotspots - 1),  # Subtract background
            'hotspot_labels': labels
        }
