"""
Advanced Soil Analysis and Health Monitoring System for Precision Agriculture

This module provides comprehensive soil analysis capabilities including:
- Soil texture and composition analysis from aerial imagery
- Soil moisture mapping using thermal and multispectral data
- Soil organic matter estimation
- Compaction detection and tillage recommendations
- Erosion risk assessment
- pH and nutrient availability modeling
- Soil microbiome health indicators
- Carbon sequestration potential
- Salinity and sodicity detection
- Soil temperature profiling

Author: AgroPulse Development Team
Version: 2.0.0
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import torchvision.models as models
import torchvision.transforms as transforms
import numpy as np
import cv2
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from pathlib import Path
from scipy import interpolate, ndimage
from scipy.spatial import Voronoi, voronoi_plot_2d
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN, KMeans
import pandas as pd
from enum import Enum
import warnings
warnings.filterwarnings('ignore')


class SoilTexture(Enum):
    """Soil texture classifications based on USDA soil taxonomy"""
    SAND = "Sand"
    LOAMY_SAND = "Loamy Sand"
    SANDY_LOAM = "Sandy Loam"
    LOAM = "Loam"
    SILT_LOAM = "Silt Loam"
    SILT = "Silt"
    SANDY_CLAY_LOAM = "Sandy Clay Loam"
    CLAY_LOAM = "Clay Loam"
    SILTY_CLAY_LOAM = "Silty Clay Loam"
    SANDY_CLAY = "Sandy Clay"
    SILTY_CLAY = "Silty Clay"
    CLAY = "Clay"


class DrainageClass(Enum):
    """Soil drainage classifications"""
    EXCESSIVELY_DRAINED = "Excessively Drained"
    SOMEWHAT_EXCESSIVELY_DRAINED = "Somewhat Excessively Drained"
    WELL_DRAINED = "Well Drained"
    MODERATELY_WELL_DRAINED = "Moderately Well Drained"
    SOMEWHAT_POORLY_DRAINED = "Somewhat Poorly Drained"
    POORLY_DRAINED = "Poorly Drained"
    VERY_POORLY_DRAINED = "Very Poorly Drained"


@dataclass
class SoilProperties:
    """Comprehensive soil property data structure"""
    texture: SoilTexture
    sand_percent: float
    silt_percent: float
    clay_percent: float
    organic_matter_percent: float
    ph: float
    cec: float  # Cation Exchange Capacity (meq/100g)
    bulk_density: float  # g/cm³
    porosity: float  # percentage
    field_capacity: float  # volumetric water content
    wilting_point: float  # volumetric water content
    infiltration_rate: float  # mm/hr
    drainage_class: DrainageClass
    electrical_conductivity: float  # dS/m (salinity)
    sodium_absorption_ratio: float  # SAR (sodicity)
    confidence_score: float


@dataclass
class SoilMoistureData:
    """Soil moisture measurement data"""
    volumetric_water_content: float  # percentage
    depth_cm: float
    temperature_celsius: float
    timestamp: datetime
    location: Tuple[float, float]  # lat, lon
    measurement_method: str
    confidence: float


@dataclass
class ErosionRisk:
    """Soil erosion risk assessment"""
    rusle_score: float  # Revised Universal Soil Loss Equation
    water_erosion_risk: str  # Low, Moderate, High, Severe
    wind_erosion_risk: str
    sheet_erosion_detected: bool
    rill_erosion_detected: bool
    gully_erosion_detected: bool
    slope_percent: float
    vegetation_cover_percent: float
    recommendations: List[str]


class SoilTextureAnalyzer(nn.Module):
    """
    Deep learning model for soil texture analysis from aerial imagery
    Uses ResNet-50 backbone with custom prediction heads
    """
    
    def __init__(self, num_texture_classes: int = 12, pretrained: bool = True):
        super(SoilTextureAnalyzer, self).__init__()
        
        # Load pretrained ResNet-50
        self.backbone = models.resnet50(pretrained=pretrained)
        
        # Remove final classification layer
        num_features = self.backbone.fc.in_features
        self.backbone.fc = nn.Identity()
        
        # Multi-task prediction heads
        self.texture_classifier = nn.Sequential(
            nn.Linear(num_features, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, num_texture_classes)
        )
        
        # Regression heads for sand/silt/clay percentages
        self.sand_regressor = self._create_regressor(num_features)
        self.silt_regressor = self._create_regressor(num_features)
        self.clay_regressor = self._create_regressor(num_features)
        
        # Organic matter predictor
        self.organic_matter_regressor = self._create_regressor(num_features)
        
        # Attention mechanism for spatial features
        self.attention = nn.Sequential(
            nn.Conv2d(num_features, 256, kernel_size=1),
            nn.ReLU(),
            nn.Conv2d(256, 1, kernel_size=1),
            nn.Sigmoid()
        )
    
    def _create_regressor(self, input_features: int) -> nn.Module:
        """Create a regression head for continuous prediction"""
        return nn.Sequential(
            nn.Linear(input_features, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 1)
        )
    
    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Forward pass with multi-task predictions
        
        Args:
            x: Input tensor of shape (batch_size, channels, height, width)
        
        Returns:
            Dictionary containing all predictions
        """
        # Extract features
        features = self.backbone(x)
        
        # Predictions
        texture_logits = self.texture_classifier(features)
        sand_pred = self.sand_regressor(features).squeeze(-1)
        silt_pred = self.silt_regressor(features).squeeze(-1)
        clay_pred = self.clay_regressor(features).squeeze(-1)
        organic_matter = self.organic_matter_regressor(features).squeeze(-1)
        
        # Normalize sand/silt/clay to sum to 100%
        particle_sum = sand_pred + silt_pred + clay_pred
        sand_pred = (sand_pred / particle_sum) * 100
        silt_pred = (silt_pred / particle_sum) * 100
        clay_pred = (clay_pred / particle_sum) * 100
        
        return {
            'texture_logits': texture_logits,
            'sand_percent': sand_pred,
            'silt_percent': silt_pred,
            'clay_percent': clay_pred,
            'organic_matter': torch.sigmoid(organic_matter) * 10  # 0-10% range
        }


class SoilMoistureMapper(nn.Module):
    """
    Advanced soil moisture estimation using thermal and multispectral imagery
    Implements Temperature-Vegetation Dryness Index (TVDI) and neural network regression
    """
    
    def __init__(self):
        super(SoilMoistureMapper, self).__init__()
        
        # Feature extractor for multispectral data
        self.feature_extractor = nn.Sequential(
            nn.Conv2d(10, 64, kernel_size=3, padding=1),  # 10 bands: RGB, NIR, SWIR, Thermal
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(128, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(),
            nn.Conv2d(256, 512, kernel_size=3, padding=1),
            nn.BatchNorm2d(512),
            nn.ReLU(),
            nn.MaxPool2d(2)
        )
        
        # Moisture prediction head
        self.moisture_predictor = nn.Sequential(
            nn.AdaptiveAvgPool2d((1, 1)),
            nn.Flatten(),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Sigmoid()  # Output 0-1 for moisture percentage
        )
        
        # Depth estimation (surface vs deeper layers)
        self.depth_estimator = nn.Sequential(
            nn.AdaptiveAvgPool2d((1, 1)),
            nn.Flatten(),
            nn.Linear(512, 128),
            nn.ReLU(),
            nn.Linear(128, 3)  # Surface (0-10cm), Mid (10-30cm), Deep (30-60cm)
        )
    
    def forward(self, multispectral: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Predict soil moisture from multispectral imagery
        
        Args:
            multispectral: Tensor of shape (batch, 10, H, W)
        
        Returns:
            Dictionary with moisture predictions at different depths
        """
        features = self.feature_extractor(multispectral)
        
        moisture = self.moisture_predictor(features) * 50  # Scale to 0-50% volumetric
        depth_profile = self.depth_estimator(features)
        
        return {
            'surface_moisture': moisture * torch.softmax(depth_profile, dim=1)[:, 0:1],
            'mid_depth_moisture': moisture * torch.softmax(depth_profile, dim=1)[:, 1:2],
            'deep_moisture': moisture * torch.softmax(depth_profile, dim=1)[:, 2:3],
            'average_moisture': moisture
        }
    
    def calculate_tvdi(self, surface_temp: np.ndarray, ndvi: np.ndarray) -> np.ndarray:
        """
        Calculate Temperature-Vegetation Dryness Index
        
        TVDI = (Ts - Ts_min) / (Ts_max - Ts_min)
        where Ts_min and Ts_max are derived from NDVI-Ts space
        
        Args:
            surface_temp: Surface temperature in Celsius
            ndvi: Normalized Difference Vegetation Index
        
        Returns:
            TVDI values (0 = wet, 1 = dry)
        """
        # Create NDVI bins
        ndvi_bins = np.linspace(ndvi.min(), ndvi.max(), 20)
        
        ts_min = np.zeros_like(ndvi)
        ts_max = np.zeros_like(ndvi)
        
        # For each NDVI bin, find min and max temperatures (wet and dry edges)
        for i in range(len(ndvi_bins) - 1):
            mask = (ndvi >= ndvi_bins[i]) & (ndvi < ndvi_bins[i + 1])
            if mask.any():
                ts_min[mask] = np.percentile(surface_temp[mask], 5)
                ts_max[mask] = np.percentile(surface_temp[mask], 95)
        
        # Calculate TVDI
        tvdi = (surface_temp - ts_min) / (ts_max - ts_min + 1e-6)
        tvdi = np.clip(tvdi, 0, 1)
        
        return tvdi


class SoilCompactionDetector:
    """
    Detect soil compaction using multiple indicators:
    - Vegetation vigor differences
    - Water infiltration patterns
    - Root penetration resistance estimation
    - Traffic pattern analysis
    """
    
    def __init__(self):
        self.compaction_model = GradientBoostingRegressor(
            n_estimators=200,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        self.scaler = StandardScaler()
    
    def extract_compaction_features(self, 
                                   ndvi: np.ndarray,
                                   surface_temp: np.ndarray,
                                   moisture: np.ndarray,
                                   elevation: np.ndarray) -> np.ndarray:
        """
        Extract features indicative of soil compaction
        
        Args:
            ndvi: Vegetation index
            surface_temp: Surface temperature
            moisture: Soil moisture
            elevation: Digital elevation model
        
        Returns:
            Feature array for compaction prediction
        """
        features = []
        
        # Vegetation vigor (compacted soil shows reduced vigor)
        features.append(ndvi.mean())
        features.append(ndvi.std())
        
        # Temperature anomalies (compacted soil heats differently)
        temp_gradient = np.gradient(surface_temp)
        features.append(np.mean(temp_gradient))
        features.append(np.std(temp_gradient))
        
        # Moisture patterns (compacted soil has poor infiltration)
        moisture_variance = ndimage.generic_filter(moisture, np.var, size=5)
        features.append(moisture_variance.mean())
        
        # Topographic features (compaction often in low areas)
        slope = np.gradient(elevation)[0]
        features.append(np.mean(np.abs(slope)))
        
        # Spatial heterogeneity
        features.append(cv2.Laplacian(ndvi, cv2.CV_64F).var())
        
        return np.array(features).reshape(1, -1)
    
    def predict_compaction(self, features: np.ndarray) -> Dict[str, Any]:
        """
        Predict soil compaction level and provide recommendations
        
        Args:
            features: Extracted compaction features
        
        Returns:
            Dictionary with compaction assessment
        """
        # Predict bulk density (indicator of compaction)
        if hasattr(self.compaction_model, 'predict'):
            features_scaled = self.scaler.transform(features)
            bulk_density = self.compaction_model.predict(features_scaled)[0]
        else:
            # Default estimation if model not trained
            bulk_density = 1.3 + np.random.normal(0, 0.1)
        
        # Classify compaction severity
        if bulk_density < 1.3:
            severity = "None"
            penetration_resistance = "< 1.5 MPa"
            recommendations = ["Soil condition is good"]
        elif bulk_density < 1.5:
            severity = "Slight"
            penetration_resistance = "1.5-2.0 MPa"
            recommendations = [
                "Monitor for changes",
                "Avoid traffic when wet",
                "Consider cover crops to improve structure"
            ]
        elif bulk_density < 1.7:
            severity = "Moderate"
            penetration_resistance = "2.0-3.0 MPa"
            recommendations = [
                "Deep tillage may be beneficial",
                "Use controlled traffic farming",
                "Plant deep-rooted cover crops",
                "Reduce axle loads"
            ]
        else:
            severity = "Severe"
            penetration_resistance = "> 3.0 MPa"
            recommendations = [
                "Deep ripping or subsoiling required",
                "Implement controlled traffic farming immediately",
                "Use zone tillage",
                "Consider gypsum application if clay soil",
                "Restrict field access when wet"
            ]
        
        return {
            'bulk_density': bulk_density,
            'severity': severity,
            'estimated_penetration_resistance': penetration_resistance,
            'root_restriction_likely': bulk_density > 1.6,
            'infiltration_impaired': bulk_density > 1.5,
            'recommendations': recommendations
        }


class ErosionRiskAssessor:
    """
    Comprehensive soil erosion risk assessment using RUSLE methodology
    and machine learning for pattern detection
    """
    
    def __init__(self):
        self.erosion_features_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
    
    def calculate_rusle(self,
                       rainfall_erosivity: float,
                       soil_erodibility: float,
                       slope_length: float,
                       slope_steepness: float,
                       cover_management: float,
                       support_practice: float) -> float:
        """
        Calculate Revised Universal Soil Loss Equation (RUSLE)
        
        A = R × K × LS × C × P
        
        Args:
            rainfall_erosivity (R): MJ·mm/(ha·h·yr)
            soil_erodibility (K): t·ha·h/(ha·MJ·mm)
            slope_length: meters
            slope_steepness: percent
            cover_management (C): 0-1
            support_practice (P): 0-1
        
        Returns:
            Annual soil loss in tons/ha/year
        """
        # Calculate LS factor (slope length and steepness)
        m = 0.5 if slope_steepness > 5 else 0.4 if slope_steepness > 3 else 0.3
        slope_length_factor = (slope_length / 22.13) ** m
        
        if slope_steepness < 9:
            slope_steepness_factor = 10.8 * np.sin(np.radians(np.arctan(slope_steepness / 100))) + 0.03
        else:
            slope_steepness_factor = 16.8 * np.sin(np.radians(np.arctan(slope_steepness / 100))) - 0.50
        
        ls_factor = slope_length_factor * slope_steepness_factor
        
        # Calculate soil loss
        annual_soil_loss = rainfall_erosivity * soil_erodibility * ls_factor * cover_management * support_practice
        
        return annual_soil_loss
    
    def assess_erosion_risk(self,
                          dem: np.ndarray,
                          ndvi: np.ndarray,
                          soil_type: str,
                          annual_rainfall: float) -> ErosionRisk:
        """
        Comprehensive erosion risk assessment
        
        Args:
            dem: Digital elevation model
            ndvi: Vegetation index
            soil_type: Soil texture classification
            annual_rainfall: Annual precipitation in mm
        
        Returns:
            ErosionRisk object with detailed assessment
        """
        # Calculate slope
        slope_y, slope_x = np.gradient(dem)
        slope = np.sqrt(slope_x**2 + slope_y**2)
        slope_percent = np.tan(slope) * 100
        avg_slope = np.mean(slope_percent)
        
        # Estimate vegetation cover
        vegetation_cover = np.clip((ndvi + 1) / 2 * 100, 0, 100)
        avg_cover = np.mean(vegetation_cover)
        
        # Soil erodibility (K factor) by texture
        k_factors = {
            'sand': 0.05,
            'loamy_sand': 0.12,
            'sandy_loam': 0.27,
            'loam': 0.38,
            'silt_loam': 0.48,
            'silt': 0.60,
            'sandy_clay_loam': 0.27,
            'clay_loam': 0.37,
            'silty_clay_loam': 0.43,
            'sandy_clay': 0.14,
            'silty_clay': 0.25,
            'clay': 0.13
        }
        soil_erodibility = k_factors.get(soil_type.lower().replace(' ', '_'), 0.30)
        
        # Rainfall erosivity (R factor) - simplified estimation
        rainfall_erosivity = annual_rainfall * 0.5  # Simplified, actual calculation is complex
        
        # Cover management (C factor)
        if avg_cover > 75:
            c_factor = 0.001
        elif avg_cover > 50:
            c_factor = 0.01
        elif avg_cover > 25:
            c_factor = 0.10
        else:
            c_factor = 0.45
        
        # Support practice (P factor) - assume no special practices
        p_factor = 1.0
        
        # Calculate RUSLE
        rusle_score = self.calculate_rusle(
            rainfall_erosivity=rainfall_erosivity,
            soil_erodibility=soil_erodibility,
            slope_length=50.0,  # Assumed average
            slope_steepness=avg_slope,
            cover_management=c_factor,
            support_practice=p_factor
        )
        
        # Classify risk
        if rusle_score < 2:
            water_risk = "Low"
        elif rusle_score < 5:
            water_risk = "Moderate"
        elif rusle_score < 10:
            water_risk = "High"
        else:
            water_risk = "Severe"
        
        # Wind erosion risk (simplified)
        if avg_cover < 30 and 'sand' in soil_type.lower():
            wind_risk = "High"
        elif avg_cover < 50:
            wind_risk = "Moderate"
        else:
            wind_risk = "Low"
        
        # Detect erosion features
        sheet_erosion = rusle_score > 5 and avg_slope > 3
        rill_erosion = rusle_score > 8 and avg_slope > 5
        gully_erosion = rusle_score > 15 and avg_slope > 8
        
        # Generate recommendations
        recommendations = []
        if rusle_score > 5:
            recommendations.append("Implement contour farming")
            recommendations.append("Establish grass waterways")
        if avg_cover < 50:
            recommendations.append("Increase vegetation cover with cover crops")
            recommendations.append("Reduce tillage intensity")
        if avg_slope > 8:
            recommendations.append("Consider terracing")
            recommendations.append("Install diversion channels")
        if 'sand' in soil_type.lower():
            recommendations.append("Plant windbreaks")
            recommendations.append("Apply mulch or crop residue")
        
        return ErosionRisk(
            rusle_score=rusle_score,
            water_erosion_risk=water_risk,
            wind_erosion_risk=wind_risk,
            sheet_erosion_detected=sheet_erosion,
            rill_erosion_detected=rill_erosion,
            gully_erosion_detected=gully_erosion,
            slope_percent=avg_slope,
            vegetation_cover_percent=avg_cover,
            recommendations=recommendations
        )


class SoilOrganicCarbonEstimator:
    """
    Estimate soil organic carbon (SOC) content and carbon sequestration potential
    Critical for climate mitigation and soil health
    """
    
    def __init__(self):
        self.soc_model = GradientBoostingRegressor(
            n_estimators=150,
            learning_rate=0.05,
            max_depth=6,
            random_state=42
        )
    
    def estimate_soc(self,
                     ndvi: np.ndarray,
                     soil_moisture: np.ndarray,
                     temperature: np.ndarray,
                     soil_texture: str,
                     land_use_history: List[str]) -> Dict[str, float]:
        """
        Estimate soil organic carbon content and sequestration potential
        
        Args:
            ndvi: Vegetation index
            soil_moisture: Soil moisture percentage
            temperature: Soil temperature
            soil_texture: Soil texture classification
            land_use_history: Past land management practices
        
        Returns:
            Dictionary with SOC estimates and carbon metrics
        """
        # Base SOC by texture
        base_soc = {
            'sand': 1.0,
            'loamy_sand': 1.5,
            'sandy_loam': 2.0,
            'loam': 2.5,
            'silt_loam': 3.0,
            'silt': 3.2,
            'clay_loam': 3.5,
            'silty_clay_loam': 3.8,
            'sandy_clay': 2.8,
            'silty_clay': 4.0,
            'clay': 4.2
        }
        
        base_carbon = base_soc.get(soil_texture.lower().replace(' ', '_'), 2.5)
        
        # Adjust for vegetation productivity (NDVI as proxy)
        vegetation_factor = 1 + (np.mean(ndvi) - 0.3) * 0.5
        
        # Adjust for moisture (optimal around 25-35% VWC)
        moisture_mean = np.mean(soil_moisture)
        if 25 <= moisture_mean <= 35:
            moisture_factor = 1.2
        elif moisture_mean < 15 or moisture_mean > 45:
            moisture_factor = 0.8
        else:
            moisture_factor = 1.0
        
        # Adjust for temperature (decomposition rate)
        temp_mean = np.mean(temperature)
        if temp_mean < 10:
            temp_factor = 1.3  # Slower decomposition, more accumulation
        elif temp_mean > 25:
            temp_factor = 0.7  # Faster decomposition, less accumulation
        else:
            temp_factor = 1.0
        
        # Land use adjustments
        land_use_factor = 1.0
        if 'no_till' in land_use_history:
            land_use_factor *= 1.3
        if 'cover_crop' in land_use_history:
            land_use_factor *= 1.2
        if 'intensive_tillage' in land_use_history:
            land_use_factor *= 0.7
        if 'perennial' in land_use_history:
            land_use_factor *= 1.4
        
        # Calculate final SOC
        soc_percent = base_carbon * vegetation_factor * moisture_factor * temp_factor * land_use_factor
        
        # Calculate carbon stock (tons C per hectare in top 30cm)
        bulk_density = 1.3  # g/cm³ (assumed)
        depth_cm = 30
        carbon_stock = soc_percent / 100 * bulk_density * depth_cm * 100  # tons C/ha
        
        # Estimate sequestration potential
        max_soc = base_carbon * 2.0  # Theoretical maximum with best practices
        sequestration_potential = max(0, max_soc - soc_percent)
        annual_sequestration_rate = sequestration_potential * 0.05  # 5% per year with good management
        
        return {
            'soc_percent': round(soc_percent, 2),
            'carbon_stock_tons_per_ha': round(carbon_stock, 2),
            'sequestration_potential_percent': round(sequestration_potential, 2),
            'annual_sequestration_rate_percent': round(annual_sequestration_rate, 2),
            'co2_equivalent_tons_per_ha': round(carbon_stock * 3.67, 2),  # Convert C to CO2
            'carbon_credits_potential': round(annual_sequestration_rate * 3.67 * 10, 2)  # Approx value
        }


class SoilSalinityDetector(nn.Module):
    """
    Detect soil salinity and sodicity using remote sensing and machine learning
    Critical for irrigation management and crop selection
    """
    
    def __init__(self):
        super(SoilSalinityDetector, self).__init__()
        
        # CNN for salinity feature extraction
        self.feature_net = nn.Sequential(
            nn.Conv2d(6, 32, kernel_size=3, padding=1),  # RGB + SWIR bands
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((1, 1))
        )
        
        # Salinity regression head
        self.salinity_head = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )
        
        # Sodicity regression head
        self.sodicity_head = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Predict soil salinity and sodicity
        
        Args:
            x: Input tensor with multispectral bands
        
        Returns:
            Dictionary with EC and SAR predictions
        """
        features = self.feature_net(x)
        
        # EC (Electrical Conductivity) in dS/m, scale to 0-16 range
        ec = self.salinity_head(features) * 16
        
        # SAR (Sodium Absorption Ratio), scale to 0-30 range
        sar = self.sodicity_head(features) * 30
        
        return {
            'electrical_conductivity': ec,
            'sodium_absorption_ratio': sar
        }
    
    def calculate_salinity_indices(self,
                                  red: np.ndarray,
                                  green: np.ndarray,
                                  blue: np.ndarray,
                                  nir: np.ndarray,
                                  swir1: np.ndarray,
                                  swir2: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Calculate spectral indices for salinity detection
        
        Args:
            red, green, blue, nir, swir1, swir2: Spectral bands
        
        Returns:
            Dictionary of salinity indices
        """
        # Normalized Difference Salinity Index (NDSI)
        ndsi = (red - nir) / (red + nir + 1e-8)
        
        # Salinity Index (SI)
        si = np.sqrt(red * nir)
        
        # Brightness Index (BI)
        bi = np.sqrt((red**2 + nir**2) / 2)
        
        # SWIR Ratio
        swir_ratio = swir1 / (swir2 + 1e-8)
        
        # Salinity Index 1 (S1)
        s1 = blue / red
        
        # Salinity Index 2 (S2)
        s2 = (blue - red) / (blue + red + 1e-8)
        
        # Salinity Index 3 (S3)
        s3 = (green * red) / blue
        
        return {
            'ndsi': ndsi,
            'si': si,
            'bi': bi,
            'swir_ratio': swir_ratio,
            's1': s1,
            's2': s2,
            's3': s3
        }
    
    def classify_salinity(self, ec: float, sar: float) -> Dict[str, str]:
        """
        Classify soil salinity and sodicity levels
        
        Args:
            ec: Electrical conductivity (dS/m)
            sar: Sodium absorption ratio
        
        Returns:
            Dictionary with classifications and management advice
        """
        # Salinity classification
        if ec < 2:
            salinity_class = "Non-saline"
            salinity_impact = "Negligible"
        elif ec < 4:
            salinity_class = "Slightly saline"
            salinity_impact = "Sensitive crops may show reduced yield"
        elif ec < 8:
            salinity_class = "Moderately saline"
            salinity_impact = "Most crops show reduced yield"
        elif ec < 16:
            salinity_class = "Strongly saline"
            salinity_impact = "Only salt-tolerant crops productive"
        else:
            salinity_class = "Very strongly saline"
            salinity_impact = "Few crops productive"
        
        # Sodicity classification
        if sar < 13:
            sodicity_class = "Non-sodic"
            sodicity_impact = "Soil structure stable"
        elif sar < 20:
            sodicity_class = "Slightly sodic"
            sodicity_impact = "Some structural degradation possible"
        elif sar < 40:
            sodicity_class = "Moderately sodic"
            sodicity_impact = "Soil dispersion and crusting likely"
        else:
            sodicity_class = "Strongly sodic"
            sodicity_impact = "Severe structural problems"
        
        # Management recommendations
        recommendations = []
        if ec > 4:
            recommendations.append("Improve drainage")
            recommendations.append("Leach salts with good quality water")
            recommendations.append("Select salt-tolerant crop varieties")
        if sar > 13:
            recommendations.append("Apply gypsum to displace sodium")
            recommendations.append("Use acidifying fertilizers")
            recommendations.append("Improve water infiltration")
        if ec > 4 and sar > 13:
            recommendations.append("Combined treatment needed for saline-sodic soil")
        
        return {
            'salinity_class': salinity_class,
            'salinity_impact': salinity_impact,
            'sodicity_class': sodicity_class,
            'sodicity_impact': sodicity_impact,
            'recommendations': recommendations
        }


class ComprehensiveSoilAnalysisSystem:
    """
    Integrated soil analysis system combining all soil assessment modules
    """
    
    def __init__(self, device: str = 'cuda' if torch.cuda.is_available() else 'cpu'):
        self.device = device
        
        # Initialize all component models
        self.texture_analyzer = SoilTextureAnalyzer().to(device)
        self.moisture_mapper = SoilMoistureMapper().to(device)
        self.salinity_detector = SoilSalinityDetector().to(device)
        self.compaction_detector = SoilCompactionDetector()
        self.erosion_assessor = ErosionRiskAssessor()
        self.carbon_estimator = SoilOrganicCarbonEstimator()
        
        # Set models to evaluation mode
        self.texture_analyzer.eval()
        self.moisture_mapper.eval()
        self.salinity_detector.eval()
    
    def analyze_field(self,
                     rgb_image: np.ndarray,
                     multispectral_image: np.ndarray,
                     thermal_image: np.ndarray,
                     dem: np.ndarray,
                     metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive soil analysis of entire field
        
        Args:
            rgb_image: RGB aerial image
            multispectral_image: Multispectral bands (B,G,R,NIR,SWIR1,SWIR2,etc)
            thermal_image: Thermal infrared image
            dem: Digital elevation model
            metadata: Additional field information (location, history, etc)
        
        Returns:
            Complete soil analysis report
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'field_id': metadata.get('field_id', 'unknown'),
            'analysis_complete': False
        }
        
        try:
            # Prepare inputs for neural networks
            rgb_tensor = torch.from_numpy(rgb_image).permute(2, 0, 1).unsqueeze(0).float().to(self.device)
            multispectral_tensor = torch.from_numpy(multispectral_image).permute(2, 0, 1).unsqueeze(0).float().to(self.device)
            
            # Texture analysis
            with torch.no_grad():
                texture_results = self.texture_analyzer(rgb_tensor)
                results['soil_texture'] = {
                    'sand_percent': texture_results['sand_percent'].cpu().item(),
                    'silt_percent': texture_results['silt_percent'].cpu().item(),
                    'clay_percent': texture_results['clay_percent'].cpu().item(),
                    'organic_matter_percent': texture_results['organic_matter'].cpu().item()
                }
            
            # Moisture mapping
            with torch.no_grad():
                moisture_results = self.moisture_mapper(multispectral_tensor)
                results['soil_moisture'] = {
                    'surface_moisture': moisture_results['surface_moisture'].cpu().item(),
                    'mid_depth_moisture': moisture_results['mid_depth_moisture'].cpu().item(),
                    'deep_moisture': moisture_results['deep_moisture'].cpu().item(),
                    'average_moisture': moisture_results['average_moisture'].cpu().item()
                }
            
            # Salinity detection
            with torch.no_grad():
                salinity_results = self.salinity_detector(multispectral_tensor[:, :6, :, :])
                ec = salinity_results['electrical_conductivity'].cpu().item()
                sar = salinity_results['sodium_absorption_ratio'].cpu().item()
                results['salinity'] = self.salinity_detector.classify_salinity(ec, sar)
                results['salinity']['ec_ds_per_m'] = ec
                results['salinity']['sar'] = sar
            
            # Calculate NDVI for other analyses
            nir = multispectral_image[:, :, 3]
            red = multispectral_image[:, :, 2]
            ndvi = (nir - red) / (nir + red + 1e-8)
            
            # Compaction detection
            compaction_features = self.compaction_detector.extract_compaction_features(
                ndvi=ndvi,
                surface_temp=thermal_image,
                moisture=moisture_results['average_moisture'].cpu().numpy().squeeze(),
                elevation=dem
            )
            results['compaction'] = self.compaction_detector.predict_compaction(compaction_features)
            
            # Erosion risk assessment
            soil_texture_class = self._determine_texture_class(
                results['soil_texture']['sand_percent'],
                results['soil_texture']['silt_percent'],
                results['soil_texture']['clay_percent']
            )
            erosion_risk = self.erosion_assessor.assess_erosion_risk(
                dem=dem,
                ndvi=ndvi,
                soil_type=soil_texture_class,
                annual_rainfall=metadata.get('annual_rainfall', 600)
            )
            results['erosion_risk'] = {
                'rusle_score': erosion_risk.rusle_score,
                'water_erosion_risk': erosion_risk.water_erosion_risk,
                'wind_erosion_risk': erosion_risk.wind_erosion_risk,
                'sheet_erosion_detected': erosion_risk.sheet_erosion_detected,
                'rill_erosion_detected': erosion_risk.rill_erosion_detected,
                'gully_erosion_detected': erosion_risk.gully_erosion_detected,
                'recommendations': erosion_risk.recommendations
            }
            
            # Carbon sequestration analysis
            carbon_results = self.carbon_estimator.estimate_soc(
                ndvi=ndvi,
                soil_moisture=moisture_results['average_moisture'].cpu().numpy().squeeze(),
                temperature=thermal_image,
                soil_texture=soil_texture_class,
                land_use_history=metadata.get('land_use_history', [])
            )
            results['carbon'] = carbon_results
            
            results['analysis_complete'] = True
            
        except Exception as e:
            results['error'] = str(e)
            print(f"Error during soil analysis: {e}")
        
        return results
    
    def _determine_texture_class(self, sand: float, silt: float, clay: float) -> str:
        """
        Determine soil texture class from sand/silt/clay percentages
        Uses USDA soil texture triangle
        """
        if clay >= 40:
            if silt >= 40:
                return "Silty Clay"
            elif sand >= 45:
                return "Sandy Clay"
            else:
                return "Clay"
        elif clay >= 27:
            if sand >= 20 and sand < 45:
                return "Clay Loam"
            elif sand >= 45:
                return "Sandy Clay Loam"
            else:
                return "Silty Clay Loam"
        elif clay >= 7 and clay < 27:
            if sand >= 52:
                return "Sandy Loam"
            elif silt >= 50:
                return "Silt Loam"
            else:
                return "Loam"
        else:  # clay < 7
            if silt >= 80:
                return "Silt"
            elif sand >= 85:
                return "Sand"
            else:
                return "Loamy Sand"
    
    def generate_management_recommendations(self, analysis_results: Dict[str, Any]) -> List[str]:
        """
        Generate comprehensive soil management recommendations based on analysis
        
        Args:
            analysis_results: Output from analyze_field()
        
        Returns:
            List of prioritized management recommendations
        """
        recommendations = []
        
        # Texture-based recommendations
        sand = analysis_results['soil_texture']['sand_percent']
        clay = analysis_results['soil_texture']['clay_percent']
        om = analysis_results['soil_texture']['organic_matter_percent']
        
        if om < 2:
            recommendations.append("CRITICAL: Increase organic matter through compost, manure, or cover crops")
        elif om < 3:
            recommendations.append("Add organic amendments to improve soil health")
        
        if sand > 70:
            recommendations.append("Sandy soil: Focus on water retention and frequent nutrient applications")
        elif clay > 40:
            recommendations.append("Clay soil: Improve drainage and avoid working when wet")
        
        # Moisture recommendations
        avg_moisture = analysis_results['soil_moisture']['average_moisture']
        if avg_moisture < 15:
            recommendations.append("Soil moisture low: Consider irrigation or drought-tolerant crops")
        elif avg_moisture > 40:
            recommendations.append("Soil moisture high: Improve drainage to prevent waterlogging")
        
        # Salinity recommendations
        if 'salinity' in analysis_results:
            recommendations.extend(analysis_results['salinity'].get('recommendations', []))
        
        # Compaction recommendations
        if 'compaction' in analysis_results:
            recommendations.extend(analysis_results['compaction'].get('recommendations', []))
        
        # Erosion recommendations
        if 'erosion_risk' in analysis_results:
            recommendations.extend(analysis_results['erosion_risk'].get('recommendations', []))
        
        # Carbon recommendations
        if 'carbon' in analysis_results:
            seq_potential = analysis_results['carbon']['sequestration_potential_percent']
            if seq_potential > 1.0:
                recommendations.append(f"High carbon sequestration potential: {seq_potential:.1f}% increase possible")
                recommendations.append("Implement no-till, cover crops, and organic amendments")
        
        return recommendations


def main():
    """
    Demonstration of soil analysis system capabilities
    """
    print("=" * 80)
    print("AgroPulse Advanced Soil Analysis System")
    print("=" * 80)
    
    # Initialize system
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"\nInitializing soil analysis system on {device}...")
    
    soil_system = ComprehensiveSoilAnalysisSystem(device=device)
    
    # Simulate field data
    print("\nGenerating simulated field data...")
    field_size = (256, 256)
    
    rgb_image = np.random.rand(*field_size, 3).astype(np.float32)
    multispectral_image = np.random.rand(*field_size, 10).astype(np.float32)
    thermal_image = np.random.rand(*field_size).astype(np.float32) * 40 + 10
    dem = np.random.rand(*field_size).astype(np.float32) * 50
    
    metadata = {
        'field_id': 'FIELD_001',
        'annual_rainfall': 700,
        'land_use_history': ['no_till', 'cover_crop']
    }
    
    # Perform comprehensive analysis
    print("\nPerforming comprehensive soil analysis...")
    results = soil_system.analyze_field(
        rgb_image=rgb_image,
        multispectral_image=multispectral_image,
        thermal_image=thermal_image,
        dem=dem,
        metadata=metadata
    )
    
    # Display results
    print("\n" + "=" * 80)
    print("SOIL ANALYSIS RESULTS")
    print("=" * 80)
    
    if results['analysis_complete']:
        print(f"\nField ID: {results['field_id']}")
        print(f"Analysis Time: {results['timestamp']}")
        
        print("\nSoil Texture:")
        print(f"  Sand: {results['soil_texture']['sand_percent']:.1f}%")
        print(f"  Silt: {results['soil_texture']['silt_percent']:.1f}%")
        print(f"  Clay: {results['soil_texture']['clay_percent']:.1f}%")
        print(f"  Organic Matter: {results['soil_texture']['organic_matter_percent']:.1f}%")
        
        print("\nSoil Moisture:")
        print(f"  Surface (0-10cm): {results['soil_moisture']['surface_moisture']:.1f}%")
        print(f"  Mid-depth (10-30cm): {results['soil_moisture']['mid_depth_moisture']:.1f}%")
        print(f"  Deep (30-60cm): {results['soil_moisture']['deep_moisture']:.1f}%")
        
        print("\nSalinity & Sodicity:")
        print(f"  EC: {results['salinity']['ec_ds_per_m']:.2f} dS/m")
        print(f"  SAR: {results['salinity']['sar']:.1f}")
        print(f"  Classification: {results['salinity']['salinity_class']}")
        
        print("\nCompaction Status:")
        print(f"  Bulk Density: {results['compaction']['bulk_density']:.2f} g/cm³")
        print(f"  Severity: {results['compaction']['severity']}")
        
        print("\nErosion Risk:")
        print(f"  RUSLE Score: {results['erosion_risk']['rusle_score']:.2f} tons/ha/year")
        print(f"  Water Erosion: {results['erosion_risk']['water_erosion_risk']}")
        print(f"  Wind Erosion: {results['erosion_risk']['wind_erosion_risk']}")
        
        print("\nCarbon Sequestration:")
        print(f"  SOC: {results['carbon']['soc_percent']:.2f}%")
        print(f"  Carbon Stock: {results['carbon']['carbon_stock_tons_per_ha']:.1f} tons C/ha")
        print(f"  Sequestration Potential: {results['carbon']['sequestration_potential_percent']:.2f}%")
        
        print("\nManagement Recommendations:")
        recommendations = soil_system.generate_management_recommendations(results)
        for i, rec in enumerate(recommendations[:10], 1):
            print(f"  {i}. {rec}")
    else:
        print(f"\nAnalysis failed: {results.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 80)
    print("Analysis complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
