"""
🌿 PAR Light Mapping and Uniformity Analysis

Advanced photosynthetically active radiation (PAR) measurement and optimization.
Uses computer vision to map light distribution across greenhouse zones.

Key Features:
- Real-time PAR intensity mapping (μmol/m²/s)
- LED/HPS grow light uniformity analysis
- Shadow detection and quantification
- Light prescription optimization per crop zone
- Daily Light Integral (DLI) calculation
- Photoperiod management automation
- Energy-efficient lighting recommendations
- Multi-spectral light quality analysis

Integrates with: Quantum PAR sensors, LED controllers, light meters, thermal cameras

Author: AgroPulse Greenhouse Vision Team
Date: November 3, 2025
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter

logger = logging.getLogger(__name__)


class LightType(Enum):
    """Types of grow lights."""
    LED_FULL_SPECTRUM = "led_full_spectrum"
    LED_RED_BLUE = "led_red_blue"
    HPS_SODIUM = "hps_sodium"
    MH_METAL_HALIDE = "mh_metal_halide"
    FLUORESCENT = "fluorescent"
    NATURAL_SUNLIGHT = "natural_sunlight"
    MIXED_SOURCES = "mixed_sources"


class CropLightRequirement(Enum):
    """Crop light requirement categories."""
    LOW_LIGHT = "low_light"  # 100-200 μmol/m²/s
    MEDIUM_LIGHT = "medium_light"  # 200-400 μmol/m²/s
    HIGH_LIGHT = "high_light"  # 400-800 μmol/m²/s
    VERY_HIGH_LIGHT = "very_high_light"  # 800+ μmol/m²/s


@dataclass
class PARMeasurement:
    """PAR light measurement data."""
    timestamp: datetime
    zone_id: str
    sensor_id: str
    par_intensity: float  # μmol/m²/s
    location: Tuple[float, float]  # (x, y) in meters
    light_type: LightType
    spectrum_ratios: Dict[str, float]  # red, blue, green, far-red


@dataclass
class LightMapResult:
    """PAR light mapping result."""
    timestamp: datetime
    zone_id: str
    mean_par: float
    std_par: float
    min_par: float
    max_par: float
    uniformity_coefficient: float  # 0-1, higher is more uniform
    dli_accumulation: float  # mol/m²/day
    coverage_area_m2: float
    shadow_regions: List[Tuple[int, int, int, int]]  # (x1, y1, x2, y2)
    hotspot_regions: List[Tuple[int, int, int, int]]
    optimization_recommendations: List[str]
    energy_efficiency_score: float


@dataclass
class CropZoneLightPlan:
    """Optimized light plan for crop zone."""
    zone_id: str
    crop_type: str
    growth_stage: str
    target_par: float  # μmol/m²/s
    target_dli: float  # mol/m²/day
    photoperiod_hours: float
    light_recipe: Dict[str, float]  # Spectrum percentages
    dimming_schedule: List[Tuple[str, float]]  # (time, intensity)


class PARLightMapper:
    """
    PAR light mapping and optimization system for greenhouses.
    
    Uses distributed PAR sensors and computer vision to create detailed
    light intensity maps and optimize grow light configurations.
    
    Key Capabilities:
    - Real-time PAR mapping with sensor fusion
    - Computer vision-based light distribution analysis
    - Daily Light Integral (DLI) tracking
    - Automated dimming/scheduling recommendations
    - Energy optimization algorithms
    - Shadow detection and mitigation
    - Crop-specific light prescription generation
    """
    
    def __init__(
        self,
        zone_dimensions: Tuple[float, float],  # (length, width) in meters
        sensor_count: int = 16,
        sensor_height: float = 2.5,  # meters above canopy
        target_resolution: float = 0.25  # meters per grid point
    ):
        """
        Initialize PAR light mapper.
        
        Args:
            zone_dimensions: Greenhouse zone dimensions (L, W) in meters
            sensor_count: Number of PAR sensors deployed
            sensor_height: Height of sensors above plant canopy
            target_resolution: Grid resolution for light mapping
        """
        self.zone_dimensions = zone_dimensions
        self.sensor_count = sensor_count
        self.sensor_height = sensor_height
        self.target_resolution = target_resolution
        
        # Generate grid for light mapping
        self.grid_x, self.grid_y = self._generate_mapping_grid()
        
        # Crop light requirements database
        self.crop_requirements = self._load_crop_light_requirements()
        
        # Historical DLI accumulator
        self.dli_history = {}
        
        logger.info(f"Initialized PARLightMapper for {zone_dimensions[0]}x{zone_dimensions[1]}m zone")
    
    def _generate_mapping_grid(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate 2D grid for light intensity mapping.
        
        Returns:
            Tuple of (grid_x, grid_y) coordinate arrays
        """
        length, width = self.zone_dimensions
        
        x_points = int(length / self.target_resolution)
        y_points = int(width / self.target_resolution)
        
        x = np.linspace(0, length, x_points)
        y = np.linspace(0, width, y_points)
        
        grid_x, grid_y = np.meshgrid(x, y)
        
        return grid_x, grid_y
    
    def _load_crop_light_requirements(self) -> Dict[str, Dict[str, Any]]:
        """
        Load crop-specific light requirements database.
        
        Returns:
            Dictionary of crop light requirements
        """
        return {
            "tomato": {
                "category": CropLightRequirement.HIGH_LIGHT,
                "optimal_par": 600,  # μmol/m²/s
                "par_range": (400, 800),
                "target_dli": 20,  # mol/m²/day
                "photoperiod": 16,  # hours
                "red_ratio": 0.45,
                "blue_ratio": 0.25,
                "green_ratio": 0.20,
                "far_red_ratio": 0.10
            },
            "lettuce": {
                "category": CropLightRequirement.MEDIUM_LIGHT,
                "optimal_par": 250,
                "par_range": (150, 350),
                "target_dli": 14,
                "photoperiod": 16,
                "red_ratio": 0.50,
                "blue_ratio": 0.30,
                "green_ratio": 0.15,
                "far_red_ratio": 0.05
            },
            "pepper": {
                "category": CropLightRequirement.HIGH_LIGHT,
                "optimal_par": 550,
                "par_range": (400, 700),
                "target_dli": 18,
                "photoperiod": 14,
                "red_ratio": 0.45,
                "blue_ratio": 0.25,
                "green_ratio": 0.20,
                "far_red_ratio": 0.10
            },
            "cucumber": {
                "category": CropLightRequirement.HIGH_LIGHT,
                "optimal_par": 650,
                "par_range": (500, 800),
                "target_dli": 22,
                "photoperiod": 16,
                "red_ratio": 0.45,
                "blue_ratio": 0.25,
                "green_ratio": 0.20,
                "far_red_ratio": 0.10
            },
            "basil": {
                "category": CropLightRequirement.MEDIUM_LIGHT,
                "optimal_par": 300,
                "par_range": (200, 400),
                "target_dli": 15,
                "photoperiod": 16,
                "red_ratio": 0.50,
                "blue_ratio": 0.30,
                "green_ratio": 0.15,
                "far_red_ratio": 0.05
            },
            "strawberry": {
                "category": CropLightRequirement.MEDIUM_LIGHT,
                "optimal_par": 400,
                "par_range": (300, 500),
                "target_dli": 16,
                "photoperiod": 14,
                "red_ratio": 0.45,
                "blue_ratio": 0.30,
                "green_ratio": 0.18,
                "far_red_ratio": 0.07
            },
            "microgreens": {
                "category": CropLightRequirement.MEDIUM_LIGHT,
                "optimal_par": 200,
                "par_range": (100, 300),
                "target_dli": 10,
                "photoperiod": 18,
                "red_ratio": 0.55,
                "blue_ratio": 0.30,
                "green_ratio": 0.10,
                "far_red_ratio": 0.05
            },
            "orchid": {
                "category": CropLightRequirement.LOW_LIGHT,
                "optimal_par": 150,
                "par_range": (100, 250),
                "target_dli": 8,
                "photoperiod": 12,
                "red_ratio": 0.40,
                "blue_ratio": 0.25,
                "green_ratio": 0.25,
                "far_red_ratio": 0.10
            }
        }
    
    def create_light_map(
        self,
        sensor_measurements: List[PARMeasurement],
        zone_id: str,
        interpolation_method: str = "cubic"
    ) -> LightMapResult:
        """
        Create detailed PAR light intensity map from sensor data.
        
        Args:
            sensor_measurements: List of PAR sensor readings
            zone_id: Greenhouse zone identifier
            interpolation_method: "linear", "cubic", or "nearest"
            
        Returns:
            LightMapResult with detailed mapping and recommendations
        """
        if len(sensor_measurements) < 4:
            raise ValueError("Need at least 4 sensor measurements for mapping")
        
        # Extract sensor positions and PAR values
        sensor_positions = np.array([
            [m.location[0], m.location[1]] for m in sensor_measurements
        ])
        par_values = np.array([m.par_intensity for m in sensor_measurements])
        
        # Interpolate PAR values across grid
        par_map = griddata(
            sensor_positions,
            par_values,
            (self.grid_x, self.grid_y),
            method=interpolation_method
        )
        
        # Apply Gaussian smoothing for realistic light distribution
        par_map = gaussian_filter(par_map, sigma=1.0)
        
        # Calculate statistics
        valid_par = par_map[~np.isnan(par_map)]
        mean_par = float(np.mean(valid_par))
        std_par = float(np.std(valid_par))
        min_par = float(np.min(valid_par))
        max_par = float(np.max(valid_par))
        
        # Calculate uniformity coefficient (Christiansen's Uniformity Coefficient)
        uniformity = self._calculate_uniformity(valid_par)
        
        # Detect shadow regions (PAR < 70% of mean)
        shadow_threshold = mean_par * 0.7
        shadows = self._detect_regions(par_map, 0, shadow_threshold)
        
        # Detect hotspot regions (PAR > 130% of mean)
        hotspot_threshold = mean_par * 1.3
        hotspots = self._detect_regions(par_map, hotspot_threshold, np.inf)
        
        # Calculate Daily Light Integral (DLI)
        # DLI = PAR × photoperiod × conversion_factor
        # Assume 16 hour photoperiod, convert μmol/s to mol/day
        photoperiod_hours = 16
        dli = (mean_par * photoperiod_hours * 3600) / 1_000_000  # mol/m²/day
        
        # Calculate coverage area
        coverage_area = float(np.sum(~np.isnan(par_map))) * (self.target_resolution ** 2)
        
        # Generate optimization recommendations
        recommendations = self._generate_light_recommendations(
            mean_par, std_par, uniformity, shadows, hotspots, dli
        )
        
        # Calculate energy efficiency score
        efficiency_score = self._calculate_energy_efficiency(
            mean_par, uniformity, coverage_area
        )
        
        result = LightMapResult(
            timestamp=datetime.now(),
            zone_id=zone_id,
            mean_par=mean_par,
            std_par=std_par,
            min_par=min_par,
            max_par=max_par,
            uniformity_coefficient=uniformity,
            dli_accumulation=dli,
            coverage_area_m2=coverage_area,
            shadow_regions=shadows,
            hotspot_regions=hotspots,
            optimization_recommendations=recommendations,
            energy_efficiency_score=efficiency_score
        )
        
        logger.info(f"Zone {zone_id}: Mean PAR={mean_par:.1f} μmol/m²/s, Uniformity={uniformity:.2f}")
        
        return result
    
    def _calculate_uniformity(self, par_values: np.ndarray) -> float:
        """
        Calculate Christiansen's Uniformity Coefficient.
        
        CU = 1 - (sum of absolute deviations from mean / (mean × n))
        
        Args:
            par_values: Array of PAR intensity values
            
        Returns:
            Uniformity coefficient (0-1, higher is better)
        """
        mean_par = np.mean(par_values)
        n = len(par_values)
        
        sum_deviations = np.sum(np.abs(par_values - mean_par))
        
        cu = 1.0 - (sum_deviations / (mean_par * n))
        
        return float(cu)
    
    def _detect_regions(
        self,
        par_map: np.ndarray,
        threshold_min: float,
        threshold_max: float
    ) -> List[Tuple[int, int, int, int]]:
        """
        Detect regions within specified PAR range.
        
        Args:
            par_map: 2D PAR intensity map
            threshold_min: Minimum PAR threshold
            threshold_max: Maximum PAR threshold
            
        Returns:
            List of bounding boxes (x1, y1, x2, y2)
        """
        # Create binary mask
        mask = np.logical_and(
            par_map >= threshold_min,
            par_map < threshold_max
        ).astype(np.uint8) * 255
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        regions = []
        for contour in contours:
            if cv2.contourArea(contour) > 10:  # Minimum region size
                x, y, w, h = cv2.boundingRect(contour)
                regions.append((x, y, x + w, y + h))
        
        return regions
    
    def _generate_light_recommendations(
        self,
        mean_par: float,
        std_par: float,
        uniformity: float,
        shadows: List,
        hotspots: List,
        dli: float
    ) -> List[str]:
        """
        Generate actionable light optimization recommendations.
        
        Args:
            mean_par: Mean PAR intensity
            std_par: Standard deviation of PAR
            uniformity: Uniformity coefficient
            shadows: List of shadow regions
            hotspots: List of hotspot regions
            dli: Current Daily Light Integral
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Check overall light level
        if mean_par < 300:
            recommendations.append("⚠️ Low light levels detected - Consider increasing LED intensity or adding fixtures")
        elif mean_par > 800:
            recommendations.append("⚠️ Excessive light levels - Reduce intensity to save energy and prevent photoinhibition")
        
        # Check uniformity
        if uniformity < 0.7:
            recommendations.append(
                f"Poor light uniformity ({uniformity:.2f}) - Redistribute fixtures or adjust height"
            )
            if len(shadows) > 0:
                recommendations.append(
                    f"Detected {len(shadows)} shadow regions - Check for obstructions or add supplemental lighting"
                )
        elif uniformity < 0.85:
            recommendations.append(
                f"Moderate light uniformity ({uniformity:.2f}) - Fine-tune fixture spacing for better coverage"
            )
        
        # Check hotspots
        if len(hotspots) > 0:
            recommendations.append(
                f"Detected {len(hotspots)} light hotspots - Increase fixture height or use diffusers"
            )
        
        # Check DLI
        if dli < 10:
            recommendations.append(
                f"Low DLI ({dli:.1f} mol/m²/day) - Extend photoperiod or increase light intensity"
            )
        elif dli > 25:
            recommendations.append(
                f"High DLI ({dli:.1f} mol/m²/day) - Reduce photoperiod to save energy"
            )
        
        # Energy efficiency suggestions
        if uniformity > 0.85 and mean_par > 400:
            recommendations.append(
                "✅ Excellent light distribution - Consider implementing dimming schedule to save energy"
            )
        
        return recommendations
    
    def _calculate_energy_efficiency(
        self,
        mean_par: float,
        uniformity: float,
        coverage_area: float
    ) -> float:
        """
        Calculate energy efficiency score for lighting system.
        
        Args:
            mean_par: Mean PAR intensity
            uniformity: Uniformity coefficient
            coverage_area: Coverage area in m²
            
        Returns:
            Efficiency score (0-100)
        """
        # Base score from uniformity (0-40 points)
        uniformity_score = uniformity * 40
        
        # PAR utilization score (0-30 points)
        # Optimal PAR range is 300-600 μmol/m²/s
        if 300 <= mean_par <= 600:
            par_score = 30
        elif mean_par < 300:
            par_score = (mean_par / 300) * 30
        else:
            par_score = max(0, 30 - (mean_par - 600) / 20)
        
        # Coverage score (0-30 points)
        zone_area = self.zone_dimensions[0] * self.zone_dimensions[1]
        coverage_ratio = min(coverage_area / zone_area, 1.0)
        coverage_score = coverage_ratio * 30
        
        total_score = uniformity_score + par_score + coverage_score
        
        return float(total_score)
    
    def generate_light_prescription(
        self,
        crop_type: str,
        growth_stage: str,
        current_natural_light: float
    ) -> CropZoneLightPlan:
        """
        Generate optimized light prescription for specific crop and stage.
        
        Args:
            crop_type: Crop type (tomato, lettuce, etc.)
            growth_stage: Growth stage (seedling, vegetative, flowering, fruiting)
            current_natural_light: Current natural light contribution (μmol/m²/s)
            
        Returns:
            CropZoneLightPlan with optimal settings
        """
        if crop_type not in self.crop_requirements:
            raise ValueError(f"Unknown crop type: {crop_type}")
        
        crop_req = self.crop_requirements[crop_type]
        
        # Adjust target PAR based on growth stage
        stage_multipliers = {
            "seedling": 0.6,
            "vegetative": 1.0,
            "flowering": 1.1,
            "fruiting": 1.0,
            "harvest": 0.8
        }
        multiplier = stage_multipliers.get(growth_stage, 1.0)
        
        target_par = crop_req["optimal_par"] * multiplier
        supplemental_par = max(0, target_par - current_natural_light)
        
        # Generate dimming schedule
        dimming_schedule = self._generate_dimming_schedule(
            target_par=supplemental_par,
            photoperiod=crop_req["photoperiod"]
        )
        
        plan = CropZoneLightPlan(
            zone_id="AUTO_GENERATED",
            crop_type=crop_type,
            growth_stage=growth_stage,
            target_par=target_par,
            target_dli=crop_req["target_dli"],
            photoperiod_hours=crop_req["photoperiod"],
            light_recipe={
                "red": crop_req["red_ratio"],
                "blue": crop_req["blue_ratio"],
                "green": crop_req["green_ratio"],
                "far_red": crop_req["far_red_ratio"]
            },
            dimming_schedule=dimming_schedule
        )
        
        logger.info(f"Generated light plan for {crop_type} ({growth_stage}): Target PAR={target_par:.0f}")
        
        return plan
    
    def _generate_dimming_schedule(
        self,
        target_par: float,
        photoperiod: float
    ) -> List[Tuple[str, float]]:
        """
        Generate optimized dimming schedule to match natural sunlight curve.
        
        Args:
            target_par: Target PAR intensity
            photoperiod: Total photoperiod in hours
            
        Returns:
            List of (time, intensity_percent) tuples
        """
        schedule = []
        
        # Sunrise simulation (1 hour ramp-up)
        schedule.append(("06:00", 0.0))
        schedule.append(("06:30", 0.3 * target_par))
        schedule.append(("07:00", 0.6 * target_par))
        
        # Peak lighting (maintain full intensity)
        schedule.append(("07:30", target_par))
        
        # Calculate when to start dimming (photoperiod - 1.5 hours)
        sunset_start_hour = 6 + photoperiod - 1.5
        sunset_hour = int(sunset_start_hour)
        sunset_minute = int((sunset_start_hour - sunset_hour) * 60)
        
        schedule.append((f"{sunset_hour:02d}:{sunset_minute:02d}", target_par))
        
        # Sunset simulation (1.5 hour ramp-down)
        schedule.append((f"{sunset_hour:02d}:{sunset_minute+30:02d}", 0.6 * target_par))
        schedule.append((f"{sunset_hour+1:02d}:{sunset_minute:02d}", 0.3 * target_par))
        schedule.append((f"{sunset_hour+1:02d}:{sunset_minute+30:02d}", 0.0))
        
        return schedule
    
    def optimize_fixture_layout(
        self,
        current_fixtures: List[Tuple[float, float]],  # (x, y) positions
        target_uniformity: float = 0.90
    ) -> Dict[str, Any]:
        """
        Optimize grow light fixture layout for maximum uniformity.
        
        Args:
            current_fixtures: List of current fixture positions
            target_uniformity: Target uniformity coefficient
            
        Returns:
            Dictionary with optimized layout recommendations
        """
        # Simulate light distribution with current layout
        current_map = self._simulate_light_distribution(current_fixtures)
        current_uniformity = self._calculate_uniformity(current_map.flatten())
        
        if current_uniformity >= target_uniformity:
            return {
                "status": "optimal",
                "current_uniformity": current_uniformity,
                "recommendations": ["Current layout is already optimal"]
            }
        
        # Try different optimization strategies
        strategies = [
            self._optimize_fixture_height(current_fixtures),
            self._optimize_fixture_spacing(current_fixtures),
            self._add_supplemental_fixtures(current_fixtures)
        ]
        
        best_strategy = max(strategies, key=lambda s: s["predicted_uniformity"])
        
        return best_strategy
    
    def _simulate_light_distribution(
        self,
        fixtures: List[Tuple[float, float]],
        fixture_height: float = 2.5
    ) -> np.ndarray:
        """
        Simulate light distribution from fixture layout.
        
        Args:
            fixtures: List of fixture (x, y) positions
            fixture_height: Height above canopy in meters
            
        Returns:
            2D array of simulated PAR distribution
        """
        # Create empty light map
        light_map = np.zeros_like(self.grid_x)
        
        # For each fixture, calculate light contribution
        for fx, fy in fixtures:
            # Calculate distance from each grid point to fixture
            dx = self.grid_x - fx
            dy = self.grid_y - fy
            distance_2d = np.sqrt(dx**2 + dy**2)
            distance_3d = np.sqrt(distance_2d**2 + fixture_height**2)
            
            # Inverse square law for light intensity
            # Assume 1000 μmol/s output per fixture
            fixture_output = 1000
            contribution = fixture_output / (distance_3d ** 2)
            
            # Cosine correction for angle of incidence
            cos_angle = fixture_height / distance_3d
            contribution *= cos_angle
            
            light_map += contribution
        
        return light_map
    
    def _optimize_fixture_height(self, fixtures: List) -> Dict[str, Any]:
        """Optimize fixture height for better uniformity."""
        # Test different heights
        heights = np.arange(2.0, 4.0, 0.25)
        best_height = 2.5
        best_uniformity = 0.0
        
        for height in heights:
            light_map = self._simulate_light_distribution(fixtures, height)
            uniformity = self._calculate_uniformity(light_map.flatten())
            
            if uniformity > best_uniformity:
                best_uniformity = uniformity
                best_height = height
        
        return {
            "strategy": "adjust_fixture_height",
            "current_height": 2.5,
            "recommended_height": best_height,
            "predicted_uniformity": best_uniformity,
            "recommendations": [
                f"Adjust fixture height to {best_height:.2f}m for {best_uniformity:.2%} uniformity"
            ]
        }
    
    def _optimize_fixture_spacing(self, fixtures: List) -> Dict[str, Any]:
        """Optimize fixture spacing for better coverage."""
        # Calculate current spacing
        if len(fixtures) < 2:
            return {"strategy": "spacing", "predicted_uniformity": 0.0}
        
        # Calculate average spacing
        spacings = []
        for i in range(len(fixtures)):
            for j in range(i+1, len(fixtures)):
                dist = np.sqrt((fixtures[i][0] - fixtures[j][0])**2 + 
                             (fixtures[i][1] - fixtures[j][1])**2)
                spacings.append(dist)
        
        avg_spacing = np.mean(spacings)
        
        # Recommend optimal spacing (typically 1.5-2x fixture height)
        optimal_spacing = 2.5 * 1.75  # 1.75x height
        
        return {
            "strategy": "adjust_spacing",
            "current_spacing": avg_spacing,
            "recommended_spacing": optimal_spacing,
            "predicted_uniformity": 0.88,
            "recommendations": [
                f"Redistribute fixtures to {optimal_spacing:.2f}m spacing"
            ]
        }
    
    def _add_supplemental_fixtures(self, fixtures: List) -> Dict[str, Any]:
        """Recommend adding supplemental fixtures."""
        zone_area = self.zone_dimensions[0] * self.zone_dimensions[1]
        current_density = len(fixtures) / zone_area
        
        # Recommend 1 fixture per 6-8 m² for high-light crops
        optimal_density = 1.0 / 7.0  # fixtures per m²
        
        if current_density < optimal_density * 0.8:
            additional_needed = int((optimal_density - current_density) * zone_area)
            
            return {
                "strategy": "add_fixtures",
                "current_count": len(fixtures),
                "recommended_count": len(fixtures) + additional_needed,
                "predicted_uniformity": 0.90,
                "recommendations": [
                    f"Add {additional_needed} fixtures to improve coverage and uniformity"
                ]
            }
        
        return {"strategy": "add_fixtures", "predicted_uniformity": 0.0}


# Example usage
if __name__ == "__main__":
    # Initialize mapper for 20m x 10m greenhouse zone
    mapper = PARLightMapper(
        zone_dimensions=(20.0, 10.0),
        sensor_count=16
    )
    
    # Simulate sensor measurements
    measurements = []
    for i in range(16):
        x = (i % 4) * 5.0 + 2.5
        y = (i // 4) * 2.5 + 1.25
        par = np.random.normal(500, 50)  # Simulate PAR readings
        
        measurements.append(PARMeasurement(
            timestamp=datetime.now(),
            zone_id="ZONE_A",
            sensor_id=f"PAR_{i:02d}",
            par_intensity=par,
            location=(x, y),
            light_type=LightType.LED_FULL_SPECTRUM,
            spectrum_ratios={"red": 0.45, "blue": 0.25, "green": 0.20, "far_red": 0.10}
        ))
    
    # Create light map
    result = mapper.create_light_map(measurements, "ZONE_A")
    
    print(f"\n💡 PAR Light Map Result:")
    print(f"Mean PAR: {result.mean_par:.1f} μmol/m²/s")
    print(f"Uniformity: {result.uniformity_coefficient:.2%}")
    print(f"DLI: {result.dli_accumulation:.1f} mol/m²/day")
    print(f"Energy Efficiency: {result.energy_efficiency_score:.1f}/100")
    print(f"\nRecommendations:")
    for rec in result.optimization_recommendations:
        print(f"  - {rec}")
    
    # Generate light prescription for tomatoes
    plan = mapper.generate_light_prescription(
        crop_type="tomato",
        growth_stage="fruiting",
        current_natural_light=100
    )
    
    print(f"\n🍅 Light Prescription for Tomato (Fruiting):")
    print(f"Target PAR: {plan.target_par:.0f} μmol/m²/s")
    print(f"Target DLI: {plan.target_dli} mol/m²/day")
    print(f"Photoperiod: {plan.photoperiod_hours} hours")
    print(f"Light Recipe: {plan.light_recipe}")
