"""
Greenhouse CO2 Distribution Visualization and Optimization Module

Analyzes CO2 concentration distribution across greenhouse zones using
thermal imaging, gas sensors, and computer vision for optimal photosynthesis.

Features:
- Multi-point CO2 concentration mapping
- CO2 uniformity analysis across zones
- Dead zone detection (poor circulation areas)
- Photosynthesis efficiency prediction
- CO2 injection system optimization
- Stratification detection (vertical CO2 gradients)
- Cost-effectiveness scoring for CO2 enrichment

Author: AgroPulse Greenhouse Vision Team
Date: November 3, 2025
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CO2InjectionStrategy(Enum):
    """CO2 injection optimization strategies"""
    CONTINUOUS = "continuous"
    PULSED = "pulsed"
    DEMAND_BASED = "demand_based"
    PHOTOPERIOD_SYNC = "photoperiod_sync"
    AMBIENT_ONLY = "ambient_only"


class CirculationQuality(Enum):
    """Air circulation quality assessment"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


class PhotosynthesisEfficiency(Enum):
    """Photosynthesis efficiency levels"""
    OPTIMAL = "optimal"
    GOOD = "good"
    SUBOPTIMAL = "suboptimal"
    LIMITED = "limited"
    SEVERELY_LIMITED = "severely_limited"


@dataclass
class CO2Reading:
    """Individual CO2 sensor reading"""
    sensor_id: str
    x: int
    y: int
    z_height: float  # Height above floor (meters)
    co2_ppm: float
    temperature: float
    par_light: float  # μmol/m²/s
    timestamp: datetime


@dataclass
class CO2DeadZone:
    """Area with insufficient CO2 concentration"""
    zone_id: str
    center_x: int
    center_y: int
    area_m2: float
    avg_co2_ppm: float
    co2_deficit_ppm: float  # Below target
    affected_plant_count: int
    yield_loss_estimate_percent: float
    recommendations: List[str]


@dataclass
class CO2StratificationLayer:
    """Vertical CO2 concentration layer"""
    height_range: Tuple[float, float]  # (min, max) meters
    avg_co2_ppm: float
    temperature: float
    gradient_strength: float  # ppm per meter
    circulation_needed: bool


@dataclass
class CO2OptimizationPlan:
    """Optimized CO2 injection plan"""
    strategy: CO2InjectionStrategy
    target_co2_ppm: float
    injection_rate_kg_per_hour: float
    injection_locations: List[Tuple[int, int]]  # (x, y) coordinates
    injection_schedule: Dict[str, bool]  # Hour: inject boolean
    estimated_cost_per_day: float
    expected_yield_increase_percent: float
    payback_period_days: float


@dataclass
class CO2DistributionResult:
    """Complete CO2 analysis results"""
    timestamp: datetime
    greenhouse_zone: str
    
    # Concentration metrics
    avg_co2_ppm: float
    min_co2_ppm: float
    max_co2_ppm: float
    co2_std_dev: float
    target_co2_ppm: float
    
    # Spatial distribution
    co2_map: np.ndarray  # 2D concentration map
    uniformity_coefficient: float  # Christiansen's coefficient
    dead_zones: List[CO2DeadZone]
    
    # Vertical analysis
    stratification_layers: List[CO2StratificationLayer]
    stratification_severity: float  # 0-1
    
    # Circulation assessment
    circulation_quality: CirculationQuality
    air_exchange_rate: float  # ACH (air changes per hour)
    mixing_efficiency: float  # 0-1
    
    # Photosynthesis analysis
    photosynthesis_efficiency: PhotosynthesisEfficiency
    light_co2_correlation: float  # -1 to 1
    avg_photosynthetic_rate: float  # μmol CO2/m²/s
    
    # Optimization
    optimization_plan: CO2OptimizationPlan
    current_utilization_efficiency: float  # 0-1
    potential_savings_per_day: float  # Currency
    
    # Visualization
    co2_heatmap: np.ndarray
    stratification_profile: np.ndarray
    dead_zone_overlay: np.ndarray


class CO2DistributionVisualizer:
    """
    Analyzes and visualizes CO2 distribution in greenhouse environments.
    
    Uses multiple CO2 sensors, thermal imaging, and PAR sensors to
    optimize CO2 enrichment for maximum photosynthesis efficiency.
    """
    
    def __init__(self,
                 greenhouse_volume_m3: float = 1500.0,
                 crop_type: str = "tomato",
                 co2_cost_per_kg: float = 0.50):
        """
        Initialize CO2 analyzer.
        
        Args:
            greenhouse_volume_m3: Total greenhouse volume
            crop_type: Type of crop being grown
            co2_cost_per_kg: Cost of CO2 per kilogram
        """
        self.greenhouse_volume_m3 = greenhouse_volume_m3
        self.crop_type = crop_type
        self.co2_cost_per_kg = co2_cost_per_kg
        
        # Crop-specific CO2 response curves
        self.crop_co2_params = self._load_crop_co2_parameters()
        
        # Historical data
        self.co2_history: List[float] = []
        self.photosynthesis_history: List[float] = []
        
        # Physical constants
        self.ambient_co2_ppm = 420.0  # Current atmospheric CO2
        self.co2_molecular_weight = 44.01  # g/mol
        
        logger.info(f"Initialized CO2DistributionVisualizer for {crop_type}")
    
    def _load_crop_co2_parameters(self) -> Dict:
        """Load crop-specific CO2 response parameters"""
        params = {
            "tomato": {
                "optimal_co2": (800, 1200),
                "saturation_co2": 1500,
                "compensation_point": 50,
                "max_photosynthesis_rate": 30.0,  # μmol CO2/m²/s
                "light_saturation_par": 600,
                "yield_increase_per_100ppm": 5.0  # % yield increase
            },
            "lettuce": {
                "optimal_co2": (800, 1200),
                "saturation_co2": 1400,
                "compensation_point": 50,
                "max_photosynthesis_rate": 25.0,
                "light_saturation_par": 300,
                "yield_increase_per_100ppm": 4.0
            },
            "cucumber": {
                "optimal_co2": (900, 1400),
                "saturation_co2": 1600,
                "compensation_point": 50,
                "max_photosynthesis_rate": 35.0,
                "light_saturation_par": 600,
                "yield_increase_per_100ppm": 6.0
            },
            "pepper": {
                "optimal_co2": (900, 1300),
                "saturation_co2": 1500,
                "compensation_point": 50,
                "max_photosynthesis_rate": 28.0,
                "light_saturation_par": 500,
                "yield_increase_per_100ppm": 5.5
            },
            "strawberry": {
                "optimal_co2": (700, 1000),
                "saturation_co2": 1200,
                "compensation_point": 50,
                "max_photosynthesis_rate": 20.0,
                "light_saturation_par": 400,
                "yield_increase_per_100ppm": 4.5
            },
            "basil": {
                "optimal_co2": (800, 1200),
                "saturation_co2": 1400,
                "compensation_point": 50,
                "max_photosynthesis_rate": 22.0,
                "light_saturation_par": 350,
                "yield_increase_per_100ppm": 4.0
            }
        }
        return params.get(self.crop_type, params["tomato"])
    
    def interpolate_co2_map(self,
                           sensor_readings: List[CO2Reading],
                           grid_width: int = 640,
                           grid_height: int = 480) -> np.ndarray:
        """
        Create 2D CO2 concentration map from sparse sensor readings.
        
        Args:
            sensor_readings: List of CO2 sensor readings
            grid_width: Output map width
            grid_height: Output map height
        
        Returns:
            2D array of CO2 concentrations (ppm)
        """
        if len(sensor_readings) == 0:
            return np.full((grid_height, grid_width), self.ambient_co2_ppm)
        
        # Extract sensor positions and values
        points = np.array([[r.x, r.y] for r in sensor_readings])
        values = np.array([r.co2_ppm for r in sensor_readings])
        
        # Create grid for interpolation
        grid_x, grid_y = np.meshgrid(
            np.linspace(0, grid_width - 1, grid_width),
            np.linspace(0, grid_height - 1, grid_height)
        )
        
        # Inverse distance weighting interpolation
        co2_map = np.zeros((grid_height, grid_width))
        
        for i in range(grid_height):
            for j in range(grid_width):
                distances = np.sqrt((points[:, 0] - j)**2 + (points[:, 1] - i)**2)
                
                # Avoid division by zero
                distances = np.maximum(distances, 1.0)
                
                # Inverse distance weighting
                weights = 1.0 / (distances ** 2)
                weights /= np.sum(weights)
                
                co2_map[i, j] = np.sum(weights * values)
        
        return co2_map
    
    def calculate_uniformity_coefficient(self, co2_map: np.ndarray) -> float:
        """
        Calculate Christiansen's Uniformity Coefficient for CO2 distribution.
        
        CU = 100 * (1 - (sum of absolute deviations) / (2 * n * mean))
        
        Args:
            co2_map: 2D CO2 concentration map
        
        Returns:
            Uniformity coefficient (0-1, higher is better)
        """
        values = co2_map.flatten()
        mean_co2 = np.mean(values)
        
        if mean_co2 < 1e-6:
            return 0.0
        
        abs_deviations = np.abs(values - mean_co2)
        cu = 1.0 - (np.sum(abs_deviations) / (2.0 * len(values) * mean_co2))
        
        return np.clip(cu, 0, 1)
    
    def detect_dead_zones(self,
                         co2_map: np.ndarray,
                         target_co2: float,
                         pixels_per_m2: float = 100) -> List[CO2DeadZone]:
        """
        Detect areas with insufficient CO2 concentration.
        
        Args:
            co2_map: 2D CO2 concentration map
            target_co2: Target CO2 concentration (ppm)
            pixels_per_m2: Pixels per square meter for area calculation
        
        Returns:
            List of detected dead zones
        """
        dead_zones = []
        
        # Define dead zone threshold (20% below target)
        threshold = target_co2 * 0.8
        
        # Create binary mask of dead zones
        dead_zone_mask = (co2_map < threshold).astype(np.uint8)
        
        # Find connected components
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        dead_zone_mask = cv2.morphologyEx(dead_zone_mask, cv2.MORPH_CLOSE, kernel)
        
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            dead_zone_mask, connectivity=8
        )
        
        for i in range(1, num_labels):  # Skip background
            area_pixels = stats[i, cv2.CC_STAT_AREA]
            
            # Filter small zones
            if area_pixels < 50:
                continue
            
            # Get zone statistics
            mask = (labels == i)
            zone_co2 = co2_map[mask]
            avg_co2 = np.mean(zone_co2)
            co2_deficit = target_co2 - avg_co2
            
            # Estimate affected plants and yield loss
            area_m2 = area_pixels / pixels_per_m2
            affected_plants = int(area_m2 * 2.5)  # Assume 2.5 plants/m²
            
            # Yield loss estimation (simplified)
            deficit_percent = (co2_deficit / target_co2) * 100
            yield_loss = min(deficit_percent * 0.5, 30.0)  # Cap at 30%
            
            # Generate recommendations
            recommendations = [
                f"Install additional CO2 injector near ({int(centroids[i][0])}, {int(centroids[i][1])})",
                "Increase circulation fan speed in this zone",
                f"Target CO2 boost: {co2_deficit:.0f} ppm",
                "Check for air leaks or poor duct placement"
            ]
            
            zone = CO2DeadZone(
                zone_id=f"DEAD_ZONE_{i}",
                center_x=int(centroids[i][0]),
                center_y=int(centroids[i][1]),
                area_m2=area_m2,
                avg_co2_ppm=avg_co2,
                co2_deficit_ppm=co2_deficit,
                affected_plant_count=affected_plants,
                yield_loss_estimate_percent=yield_loss,
                recommendations=recommendations
            )
            
            dead_zones.append(zone)
        
        return dead_zones
    
    def analyze_stratification(self,
                              sensor_readings: List[CO2Reading]) -> List[CO2StratificationLayer]:
        """
        Analyze vertical CO2 stratification (layering).
        
        Args:
            sensor_readings: Sensor readings with height data
        
        Returns:
            List of stratification layers
        """
        if len(sensor_readings) < 2:
            return []
        
        # Sort by height
        readings_sorted = sorted(sensor_readings, key=lambda r: r.z_height)
        
        # Group into height layers (0-1m, 1-2m, 2-3m, etc.)
        max_height = max(r.z_height for r in readings_sorted)
        num_layers = max(2, int(np.ceil(max_height)))
        
        layers = []
        for i in range(num_layers):
            height_min = i
            height_max = i + 1
            
            # Get readings in this layer
            layer_readings = [r for r in readings_sorted 
                            if height_min <= r.z_height < height_max]
            
            if len(layer_readings) == 0:
                continue
            
            avg_co2 = np.mean([r.co2_ppm for r in layer_readings])
            avg_temp = np.mean([r.temperature for r in layer_readings])
            
            # Calculate gradient
            if i > 0 and len(layers) > 0:
                prev_co2 = layers[-1].avg_co2_ppm
                gradient = (avg_co2 - prev_co2) / 1.0  # ppm per meter
            else:
                gradient = 0.0
            
            # Determine if circulation is needed
            circulation_needed = abs(gradient) > 100  # >100 ppm/m difference
            
            layer = CO2StratificationLayer(
                height_range=(height_min, height_max),
                avg_co2_ppm=avg_co2,
                temperature=avg_temp,
                gradient_strength=gradient,
                circulation_needed=circulation_needed
            )
            
            layers.append(layer)
        
        return layers
    
    def calculate_photosynthesis_rate(self,
                                     co2_ppm: float,
                                     par_light: float,
                                     temperature: float) -> float:
        """
        Calculate photosynthetic rate using Farquhar model (simplified).
        
        Args:
            co2_ppm: CO2 concentration
            par_light: PAR light intensity (μmol/m²/s)
            temperature: Leaf temperature (Celsius)
        
        Returns:
            Photosynthetic rate (μmol CO2/m²/s)
        """
        params = self.crop_co2_params
        
        # CO2 response (Michaelis-Menten kinetics)
        vmax = params["max_photosynthesis_rate"]
        km = 300.0  # Half-saturation constant
        co2_factor = (co2_ppm - params["compensation_point"]) / \
                     (co2_ppm + km)
        co2_factor = max(0, co2_factor)
        
        # Light response (non-rectangular hyperbola)
        alpha = 0.05  # Quantum efficiency
        light_sat = params["light_saturation_par"]
        theta = 0.7  # Curvature factor
        
        light_factor = (alpha * par_light + vmax - 
                       np.sqrt((alpha * par_light + vmax)**2 - 
                              4 * theta * alpha * par_light * vmax)) / \
                      (2 * theta)
        light_factor = light_factor / vmax
        
        # Temperature response (Q10 = 2)
        temp_factor = 2.0 ** ((temperature - 25.0) / 10.0)
        temp_factor = np.clip(temp_factor, 0.5, 1.5)
        
        # Combined rate
        rate = vmax * co2_factor * light_factor * temp_factor
        
        return max(0, rate)
    
    def assess_circulation_quality(self,
                                  uniformity: float,
                                  stratification_severity: float) -> CirculationQuality:
        """
        Assess air circulation quality based on CO2 distribution.
        
        Args:
            uniformity: Uniformity coefficient (0-1)
            stratification_severity: Stratification severity (0-1)
        
        Returns:
            CirculationQuality enum
        """
        # Calculate combined score
        score = (uniformity * 0.6) + ((1 - stratification_severity) * 0.4)
        
        if score >= 0.9:
            return CirculationQuality.EXCELLENT
        elif score >= 0.75:
            return CirculationQuality.GOOD
        elif score >= 0.6:
            return CirculationQuality.FAIR
        elif score >= 0.4:
            return CirculationQuality.POOR
        else:
            return CirculationQuality.CRITICAL
    
    def optimize_co2_injection(self,
                              co2_map: np.ndarray,
                              par_map: np.ndarray,
                              current_avg_co2: float,
                              dead_zones: List[CO2DeadZone]) -> CO2OptimizationPlan:
        """
        Generate optimized CO2 injection plan.
        
        Args:
            co2_map: Current CO2 distribution
            par_map: PAR light distribution
            current_avg_co2: Current average CO2
            dead_zones: Detected dead zones
        
        Returns:
            Optimization plan
        """
        target_co2 = np.mean(self.crop_co2_params["optimal_co2"])
        
        # Determine injection strategy
        if len(dead_zones) > 3:
            strategy = CO2InjectionStrategy.DEMAND_BASED
        elif current_avg_co2 < target_co2 * 0.5:
            strategy = CO2InjectionStrategy.CONTINUOUS
        else:
            strategy = CO2InjectionStrategy.PULSED
        
        # Calculate required injection rate
        co2_deficit = max(0, target_co2 - current_avg_co2)
        volume_deficit = (co2_deficit * 1e-6) * self.greenhouse_volume_m3  # m³
        
        # Convert to kg (1 m³ CO2 at STP = 1.98 kg)
        kg_needed = volume_deficit * 1.98
        
        # Account for losses and air exchange (50% efficiency)
        injection_rate = kg_needed * 2.0  # kg/hour
        
        # Determine injection locations
        injection_locations = []
        
        # Add injectors at dead zone centers
        for zone in dead_zones[:3]:  # Top 3 dead zones
            injection_locations.append((zone.center_x, zone.center_y))
        
        # If no dead zones, use central injection
        if len(injection_locations) == 0:
            height, width = co2_map.shape
            injection_locations.append((width // 2, height // 2))
        
        # Generate injection schedule (inject during daylight hours)
        schedule = {f"{h:02d}:00": (6 <= h <= 18) for h in range(24)}
        
        # Calculate costs and benefits
        daily_co2_kg = injection_rate * 12  # 12 hours of injection
        daily_cost = daily_co2_kg * self.co2_cost_per_kg
        
        # Expected yield increase
        co2_increase = target_co2 - self.ambient_co2_ppm
        yield_increase = (co2_increase / 100) * \
                        self.crop_co2_params["yield_increase_per_100ppm"]
        
        # Payback calculation (simplified)
        # Assume 10% yield increase = $1000/day additional revenue
        daily_revenue_increase = (yield_increase / 10.0) * 1000
        payback_days = daily_cost / max(1, daily_revenue_increase - daily_cost)
        
        plan = CO2OptimizationPlan(
            strategy=strategy,
            target_co2_ppm=target_co2,
            injection_rate_kg_per_hour=injection_rate,
            injection_locations=injection_locations,
            injection_schedule=schedule,
            estimated_cost_per_day=daily_cost,
            expected_yield_increase_percent=yield_increase,
            payback_period_days=max(1, payback_days)
        )
        
        return plan
    
    def create_visualizations(self,
                             co2_map: np.ndarray,
                             stratification_layers: List[CO2StratificationLayer],
                             dead_zones: List[CO2DeadZone]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Create visualization images.
        
        Returns:
            Tuple of (co2_heatmap, stratification_profile, dead_zone_overlay)
        """
        height, width = co2_map.shape
        
        # CO2 heatmap
        co2_normalized = cv2.normalize(co2_map, None, 0, 255, cv2.NORM_MINMAX)
        co2_heatmap = cv2.applyColorMap(co2_normalized.astype(np.uint8), cv2.COLORMAP_JET)
        
        # Add concentration labels
        cv2.putText(co2_heatmap, f"Max: {np.max(co2_map):.0f} ppm",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(co2_heatmap, f"Min: {np.min(co2_map):.0f} ppm",
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Stratification profile (vertical slice)
        profile_width = 200
        profile_height = height
        stratification_profile = np.zeros((profile_height, profile_width, 3), dtype=np.uint8)
        
        if len(stratification_layers) > 0:
            layer_height = profile_height // len(stratification_layers)
            for i, layer in enumerate(stratification_layers):
                y_start = i * layer_height
                y_end = (i + 1) * layer_height
                
                # Color based on CO2 level
                co2_norm = layer.avg_co2_ppm / 1500.0
                color_val = int(co2_norm * 255)
                stratification_profile[y_start:y_end, :] = (color_val, 128, 255 - color_val)
                
                # Add text
                cv2.putText(stratification_profile, f"{layer.avg_co2_ppm:.0f} ppm",
                           (10, y_start + layer_height // 2),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Dead zone overlay
        dead_zone_overlay = co2_heatmap.copy()
        
        for zone in dead_zones:
            # Draw circle at dead zone center
            cv2.circle(dead_zone_overlay, (zone.center_x, zone.center_y), 30, (0, 0, 255), 3)
            cv2.putText(dead_zone_overlay, f"-{zone.co2_deficit_ppm:.0f} ppm",
                       (zone.center_x - 40, zone.center_y + 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        return co2_heatmap, stratification_profile, dead_zone_overlay
    
    def analyze(self,
               sensor_readings: List[CO2Reading],
               par_map: Optional[np.ndarray] = None,
               temperature_map: Optional[np.ndarray] = None,
               greenhouse_zone: str = "main") -> CO2DistributionResult:
        """
        Perform complete CO2 distribution analysis.
        
        Args:
            sensor_readings: List of CO2 sensor readings
            par_map: Optional PAR light distribution map
            temperature_map: Optional temperature map
            greenhouse_zone: Zone identifier
        
        Returns:
            Complete analysis results
        """
        logger.info(f"Analyzing CO2 distribution for zone: {greenhouse_zone}")
        
        # Create CO2 concentration map
        co2_map = self.interpolate_co2_map(sensor_readings)
        
        # Calculate basic statistics
        avg_co2 = np.mean([r.co2_ppm for r in sensor_readings]) if sensor_readings else self.ambient_co2_ppm
        min_co2 = np.min(co2_map)
        max_co2 = np.max(co2_map)
        co2_std = np.std(co2_map)
        
        target_co2 = np.mean(self.crop_co2_params["optimal_co2"])
        
        # Calculate uniformity
        uniformity = self.calculate_uniformity_coefficient(co2_map)
        
        # Detect dead zones
        pixels_per_m2 = (co2_map.shape[0] * co2_map.shape[1]) / (self.greenhouse_volume_m3 / 3.0)  # Assume 3m height
        dead_zones = self.detect_dead_zones(co2_map, target_co2, pixels_per_m2)
        
        # Analyze stratification
        stratification_layers = self.analyze_stratification(sensor_readings)
        
        # Calculate stratification severity
        if len(stratification_layers) > 1:
            gradients = [abs(layer.gradient_strength) for layer in stratification_layers]
            stratification_severity = np.mean(gradients) / 200.0  # Normalize
            stratification_severity = np.clip(stratification_severity, 0, 1)
        else:
            stratification_severity = 0.0
        
        # Assess circulation
        circulation_quality = self.assess_circulation_quality(uniformity, stratification_severity)
        
        # Calculate photosynthesis metrics
        if par_map is None:
            par_map = np.full_like(co2_map, 400.0)  # Default PAR
        if temperature_map is None:
            temperature_map = np.full_like(co2_map, 22.0)  # Default temp
        
        photosynthesis_rates = np.zeros_like(co2_map)
        for i in range(co2_map.shape[0]):
            for j in range(co2_map.shape[1]):
                photosynthesis_rates[i, j] = self.calculate_photosynthesis_rate(
                    co2_map[i, j], par_map[i, j], temperature_map[i, j]
                )
        
        avg_photosynthesis = np.mean(photosynthesis_rates)
        
        # Assess photosynthesis efficiency
        max_possible = self.crop_co2_params["max_photosynthesis_rate"]
        efficiency_ratio = avg_photosynthesis / max_possible
        
        if efficiency_ratio >= 0.85:
            ps_efficiency = PhotosynthesisEfficiency.OPTIMAL
        elif efficiency_ratio >= 0.7:
            ps_efficiency = PhotosynthesisEfficiency.GOOD
        elif efficiency_ratio >= 0.5:
            ps_efficiency = PhotosynthesisEfficiency.SUBOPTIMAL
        elif efficiency_ratio >= 0.3:
            ps_efficiency = PhotosynthesisEfficiency.LIMITED
        else:
            ps_efficiency = PhotosynthesisEfficiency.SEVERELY_LIMITED
        
        # Calculate light-CO2 correlation
        co2_flat = co2_map.flatten()
        par_flat = par_map.flatten()
        light_co2_correlation = np.corrcoef(co2_flat, par_flat)[0, 1]
        
        # Generate optimization plan
        optimization_plan = self.optimize_co2_injection(
            co2_map, par_map, avg_co2, dead_zones
        )
        
        # Calculate utilization efficiency
        utilization = min(1.0, avg_co2 / target_co2) * uniformity
        
        # Create visualizations
        co2_heatmap, stratification_profile, dead_zone_overlay = \
            self.create_visualizations(co2_map, stratification_layers, dead_zones)
        
        result = CO2DistributionResult(
            timestamp=datetime.now(),
            greenhouse_zone=greenhouse_zone,
            avg_co2_ppm=avg_co2,
            min_co2_ppm=min_co2,
            max_co2_ppm=max_co2,
            co2_std_dev=co2_std,
            target_co2_ppm=target_co2,
            co2_map=co2_map,
            uniformity_coefficient=uniformity,
            dead_zones=dead_zones,
            stratification_layers=stratification_layers,
            stratification_severity=stratification_severity,
            circulation_quality=circulation_quality,
            air_exchange_rate=1.0,  # Placeholder
            mixing_efficiency=uniformity * (1 - stratification_severity),
            photosynthesis_efficiency=ps_efficiency,
            light_co2_correlation=light_co2_correlation,
            avg_photosynthetic_rate=avg_photosynthesis,
            optimization_plan=optimization_plan,
            current_utilization_efficiency=utilization,
            potential_savings_per_day=0.0,  # Calculate based on optimization
            co2_heatmap=co2_heatmap,
            stratification_profile=stratification_profile,
            dead_zone_overlay=dead_zone_overlay
        )
        
        logger.info(f"Analysis complete: Avg CO2={avg_co2:.0f} ppm, "
                   f"Uniformity={uniformity:.2f}, Dead zones={len(dead_zones)}")
        
        return result


def main():
    """Example usage"""
    analyzer = CO2DistributionVisualizer(
        greenhouse_volume_m3=1500.0,
        crop_type="tomato",
        co2_cost_per_kg=0.50
    )
    
    # Simulate sensor readings
    sensor_readings = [
        CO2Reading("S1", 100, 100, 1.5, 850, 22, 450, datetime.now()),
        CO2Reading("S2", 300, 100, 1.5, 900, 22, 480, datetime.now()),
        CO2Reading("S3", 500, 100, 1.5, 820, 22, 420, datetime.now()),
        CO2Reading("S4", 100, 300, 1.5, 880, 22, 460, datetime.now()),
        CO2Reading("S5", 300, 300, 1.5, 950, 22, 500, datetime.now()),
        CO2Reading("S6", 500, 300, 1.5, 870, 22, 440, datetime.now()),
    ]
    
    result = analyzer.analyze(sensor_readings)
    
    print(f"Average CO2: {result.avg_co2_ppm:.0f} ppm")
    print(f"Uniformity: {result.uniformity_coefficient:.2f}")
    print(f"Dead zones: {len(result.dead_zones)}")
    print(f"Circulation: {result.circulation_quality.value}")
    print(f"Photosynthesis: {result.photosynthesis_efficiency.value}")
    print(f"Injection rate: {result.optimization_plan.injection_rate_kg_per_hour:.2f} kg/h")


if __name__ == "__main__":
    main()
