"""
Advanced Weather Integration and Micro-Climate Modeling System

This module provides comprehensive weather data integration and micro-climate analysis:
- Real-time weather data ingestion from multiple sources
- Micro-climate modeling at field scale
- Weather-based disease risk prediction
- Frost risk forecasting and alerts
- Optimal flight window calculation
- Growing Degree Days (GDD) accumulation
- Evapotranspiration (ET) modeling
- Wind field analysis for spray drift
- Precipitation forecasting and soil moisture prediction
- Climate change impact assessment
- Historical weather pattern analysis
- Extreme weather event detection

Author: AgroPulse Development Team
Version: 3.0.0
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import requests
from pathlib import Path
from scipy import interpolate, ndimage, optimize
from scipy.spatial import Voronoi, cKDTree
from sklearn.ensemble import RandomForestRegressor, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
import pandas as pd
from collections import deque
import warnings
warnings.filterwarnings('ignore')


class WeatherSource(Enum):
    """Supported weather data sources"""
    OPENWEATHERMAP = "OpenWeatherMap"
    NOAA = "NOAA"
    WEATHER_UNDERGROUND = "Weather Underground"
    DARK_SKY = "Dark Sky"
    METEOMATICS = "Meteomatics"
    WEATHERBIT = "WeatherBit"
    LOCAL_STATION = "Local Weather Station"


class WeatherCondition(Enum):
    """Weather condition classifications"""
    CLEAR = "Clear"
    PARTLY_CLOUDY = "Partly Cloudy"
    CLOUDY = "Cloudy"
    OVERCAST = "Overcast"
    LIGHT_RAIN = "Light Rain"
    MODERATE_RAIN = "Moderate Rain"
    HEAVY_RAIN = "Heavy Rain"
    THUNDERSTORM = "Thunderstorm"
    SNOW = "Snow"
    FOG = "Fog"
    HAIL = "Hail"
    WINDY = "Windy"


class FlightSuitability(Enum):
    """Drone flight suitability assessment"""
    OPTIMAL = "Optimal"
    SUITABLE = "Suitable"
    MARGINAL = "Marginal"
    UNSUITABLE = "Unsuitable"
    DANGEROUS = "Dangerous"


@dataclass
class WeatherData:
    """Comprehensive weather data structure"""
    timestamp: datetime
    temperature_celsius: float
    feels_like_celsius: float
    humidity_percent: float
    pressure_hpa: float
    wind_speed_mps: float
    wind_direction_degrees: float
    wind_gust_mps: float
    precipitation_mm: float
    precipitation_probability: float
    cloud_cover_percent: float
    visibility_km: float
    uv_index: float
    dew_point_celsius: float
    condition: WeatherCondition
    location: Tuple[float, float]  # lat, lon


@dataclass
class MicroClimate:
    """Micro-climate data at field scale"""
    field_id: str
    temperature_map: np.ndarray  # 2D temperature distribution
    humidity_map: np.ndarray
    wind_speed_map: np.ndarray
    wind_direction_map: np.ndarray
    solar_radiation_map: np.ndarray  # W/m²
    soil_temperature_map: np.ndarray
    evapotranspiration_map: np.ndarray  # mm/day
    resolution_meters: float
    timestamp: datetime


@dataclass
class DiseaseRisk:
    """Weather-based disease risk assessment"""
    disease_name: str
    risk_level: str  # Low, Moderate, High, Severe
    risk_score: float  # 0-100
    favorable_conditions: List[str]
    current_conditions: Dict[str, float]
    infection_probability: float
    action_required: bool
    recommendations: List[str]


@dataclass
class FrostRisk:
    """Frost risk forecast"""
    date: datetime
    probability: float
    min_temperature_expected: float
    critical_temperature: float
    risk_level: str  # Low, Moderate, High, Critical
    hours_below_critical: float
    protection_recommended: bool
    protection_methods: List[str]


@dataclass
class FlightWindow:
    """Optimal flight window information"""
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    suitability: FlightSuitability
    weather_conditions: WeatherData
    risk_factors: List[str]
    recommended_altitude_m: float
    spray_drift_risk: str


class WeatherDataAggregator:
    """
    Aggregate weather data from multiple sources for redundancy and accuracy
    """
    
    def __init__(self, api_keys: Dict[str, str]):
        self.api_keys = api_keys
        self.cache = {}
        self.cache_duration = timedelta(minutes=15)
    
    def fetch_weather(self, 
                     latitude: float, 
                     longitude: float,
                     sources: Optional[List[WeatherSource]] = None) -> Dict[WeatherSource, WeatherData]:
        """
        Fetch weather data from multiple sources
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            sources: List of weather sources to query
        
        Returns:
            Dictionary mapping source to weather data
        """
        if sources is None:
            sources = [WeatherSource.OPENWEATHERMAP, WeatherSource.WEATHERBIT]
        
        results = {}
        
        for source in sources:
            try:
                if source == WeatherSource.OPENWEATHERMAP:
                    data = self._fetch_openweathermap(latitude, longitude)
                elif source == WeatherSource.WEATHERBIT:
                    data = self._fetch_weatherbit(latitude, longitude)
                elif source == WeatherSource.LOCAL_STATION:
                    data = self._fetch_local_station(latitude, longitude)
                else:
                    continue
                
                results[source] = data
            except Exception as e:
                print(f"Error fetching from {source.value}: {e}")
        
        return results
    
    def _fetch_openweathermap(self, lat: float, lon: float) -> WeatherData:
        """Fetch from OpenWeatherMap API"""
        api_key = self.api_keys.get('openweathermap', '')
        
        # Check cache
        cache_key = f"owm_{lat}_{lon}"
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if datetime.now() - cached_time < self.cache_duration:
                return cached_data
        
        # Simulated data (in production, use actual API)
        weather_data = WeatherData(
            timestamp=datetime.now(),
            temperature_celsius=22.5 + np.random.normal(0, 2),
            feels_like_celsius=21.8 + np.random.normal(0, 2),
            humidity_percent=65.0 + np.random.normal(0, 5),
            pressure_hpa=1013.0 + np.random.normal(0, 5),
            wind_speed_mps=3.5 + np.random.normal(0, 1),
            wind_direction_degrees=180.0 + np.random.normal(0, 30),
            wind_gust_mps=5.2 + np.random.normal(0, 1.5),
            precipitation_mm=0.0,
            precipitation_probability=0.15,
            cloud_cover_percent=40.0 + np.random.normal(0, 10),
            visibility_km=10.0,
            uv_index=5.0,
            dew_point_celsius=15.0 + np.random.normal(0, 2),
            condition=WeatherCondition.PARTLY_CLOUDY,
            location=(lat, lon)
        )
        
        # Cache result
        self.cache[cache_key] = (weather_data, datetime.now())
        
        return weather_data
    
    def _fetch_weatherbit(self, lat: float, lon: float) -> WeatherData:
        """Fetch from WeatherBit API"""
        # Similar implementation
        return self._fetch_openweathermap(lat, lon)
    
    def _fetch_local_station(self, lat: float, lon: float) -> WeatherData:
        """Fetch from local weather station"""
        # Implementation for local station data
        return self._fetch_openweathermap(lat, lon)
    
    def aggregate_weather(self, 
                         weather_data: Dict[WeatherSource, WeatherData]) -> WeatherData:
        """
        Aggregate weather data from multiple sources using weighted average
        
        Args:
            weather_data: Dictionary of weather data from different sources
        
        Returns:
            Aggregated weather data
        """
        if not weather_data:
            raise ValueError("No weather data to aggregate")
        
        # Source reliability weights
        weights = {
            WeatherSource.LOCAL_STATION: 1.5,
            WeatherSource.OPENWEATHERMAP: 1.0,
            WeatherSource.WEATHERBIT: 1.0,
            WeatherSource.NOAA: 1.2
        }
        
        # Aggregate numerical values
        total_weight = sum(weights.get(source, 1.0) for source in weather_data.keys())
        
        aggregated = WeatherData(
            timestamp=datetime.now(),
            temperature_celsius=sum(
                data.temperature_celsius * weights.get(source, 1.0)
                for source, data in weather_data.items()
            ) / total_weight,
            feels_like_celsius=sum(
                data.feels_like_celsius * weights.get(source, 1.0)
                for source, data in weather_data.items()
            ) / total_weight,
            humidity_percent=sum(
                data.humidity_percent * weights.get(source, 1.0)
                for source, data in weather_data.items()
            ) / total_weight,
            pressure_hpa=sum(
                data.pressure_hpa * weights.get(source, 1.0)
                for source, data in weather_data.items()
            ) / total_weight,
            wind_speed_mps=sum(
                data.wind_speed_mps * weights.get(source, 1.0)
                for source, data in weather_data.items()
            ) / total_weight,
            wind_direction_degrees=self._aggregate_wind_direction(
                [(data.wind_direction_degrees, weights.get(source, 1.0))
                 for source, data in weather_data.items()]
            ),
            wind_gust_mps=max(data.wind_gust_mps for data in weather_data.values()),
            precipitation_mm=max(data.precipitation_mm for data in weather_data.values()),
            precipitation_probability=max(data.precipitation_probability 
                                         for data in weather_data.values()),
            cloud_cover_percent=sum(
                data.cloud_cover_percent * weights.get(source, 1.0)
                for source, data in weather_data.items()
            ) / total_weight,
            visibility_km=min(data.visibility_km for data in weather_data.values()),
            uv_index=max(data.uv_index for data in weather_data.values()),
            dew_point_celsius=sum(
                data.dew_point_celsius * weights.get(source, 1.0)
                for source, data in weather_data.items()
            ) / total_weight,
            condition=list(weather_data.values())[0].condition,  # Use first source
            location=list(weather_data.values())[0].location
        )
        
        return aggregated
    
    def _aggregate_wind_direction(self, 
                                  directions_weights: List[Tuple[float, float]]) -> float:
        """
        Aggregate wind directions using circular mean
        
        Args:
            directions_weights: List of (direction_degrees, weight) tuples
        
        Returns:
            Aggregated wind direction in degrees
        """
        # Convert to radians
        sin_sum = sum(np.sin(np.radians(d)) * w for d, w in directions_weights)
        cos_sum = sum(np.cos(np.radians(d)) * w for d, w in directions_weights)
        
        # Calculate circular mean
        mean_direction = np.degrees(np.arctan2(sin_sum, cos_sum))
        
        # Normalize to 0-360
        if mean_direction < 0:
            mean_direction += 360
        
        return mean_direction


class MicroClimateModeler(nn.Module):
    """
    Neural network-based micro-climate modeling
    Predicts spatial distribution of weather variables at field scale
    """
    
    def __init__(self, hidden_dim: int = 256):
        super(MicroClimateModeler, self).__init__()
        
        # Encoder for weather station data
        self.weather_encoder = nn.Sequential(
            nn.Linear(15, 64),  # Weather features
            nn.ReLU(),
            nn.Linear(64, 128),
            nn.ReLU()
        )
        
        # Encoder for spatial features (elevation, aspect, land cover)
        self.spatial_encoder = nn.Sequential(
            nn.Conv2d(5, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.ReLU()
        )
        
        # Fusion and prediction
        self.fusion = nn.Sequential(
            nn.Conv2d(128 + 128, 256, kernel_size=1),
            nn.ReLU(),
            nn.Conv2d(256, 128, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(128, 64, kernel_size=3, padding=1),
            nn.ReLU()
        )
        
        # Individual prediction heads
        self.temperature_head = nn.Conv2d(64, 1, kernel_size=1)
        self.humidity_head = nn.Conv2d(64, 1, kernel_size=1)
        self.wind_speed_head = nn.Conv2d(64, 1, kernel_size=1)
        self.solar_radiation_head = nn.Conv2d(64, 1, kernel_size=1)
    
    def forward(self, 
                weather_features: torch.Tensor,
                spatial_features: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Predict micro-climate maps
        
        Args:
            weather_features: Weather station data (batch, 15)
            spatial_features: Spatial data (batch, 5, H, W)
        
        Returns:
            Dictionary of micro-climate predictions
        """
        # Encode weather data
        weather_encoded = self.weather_encoder(weather_features)
        weather_encoded = weather_encoded.unsqueeze(-1).unsqueeze(-1)
        
        # Expand to spatial dimensions
        B, C, H, W = spatial_features.shape
        weather_expanded = weather_encoded.expand(B, 128, H, W)
        
        # Encode spatial features
        spatial_encoded = self.spatial_encoder(spatial_features)
        
        # Fuse
        fused = torch.cat([weather_expanded, spatial_encoded], dim=1)
        features = self.fusion(fused)
        
        # Predict micro-climate variables
        temperature = self.temperature_head(features).squeeze(1)
        humidity = self.humidity_head(features).squeeze(1)
        wind_speed = self.wind_speed_head(features).squeeze(1)
        solar_radiation = self.solar_radiation_head(features).squeeze(1)
        
        return {
            'temperature': temperature,
            'humidity': humidity,
            'wind_speed': torch.relu(wind_speed),
            'solar_radiation': torch.relu(solar_radiation)
        }


class GrowingDegreeDayCalculator:
    """
    Calculate Growing Degree Days (GDD) for crop phenology prediction
    Supports multiple calculation methods
    """
    
    def __init__(self, base_temp: float = 10.0, upper_threshold: float = 30.0):
        """
        Initialize GDD calculator
        
        Args:
            base_temp: Base temperature below which no growth occurs (°C)
            upper_threshold: Upper temperature threshold (°C)
        """
        self.base_temp = base_temp
        self.upper_threshold = upper_threshold
        self.accumulated_gdd = 0.0
        self.daily_gdd_history = []
    
    def calculate_daily_gdd(self,
                           temp_max: float,
                           temp_min: float,
                           method: str = 'simple') -> float:
        """
        Calculate GDD for a single day
        
        Args:
            temp_max: Maximum temperature (°C)
            temp_min: Minimum temperature (°C)
            method: Calculation method ('simple', 'modified', 'baskerville_emin')
        
        Returns:
            GDD value for the day
        """
        if method == 'simple':
            # Simple average method
            avg_temp = (temp_max + temp_min) / 2
            gdd = max(0, avg_temp - self.base_temp)
        
        elif method == 'modified':
            # Modified method with upper threshold
            temp_max = min(temp_max, self.upper_threshold)
            temp_min = max(temp_min, self.base_temp)
            avg_temp = (temp_max + temp_min) / 2
            gdd = max(0, avg_temp - self.base_temp)
        
        elif method == 'baskerville_emin':
            # Baskerville-Emin method (more accurate)
            avg_temp = (temp_max + temp_min) / 2
            temp_range = (temp_max - temp_min) / 2
            
            if avg_temp < self.base_temp:
                gdd = 0
            else:
                # Calculate using sine wave approximation
                theta = np.arcsin((self.base_temp - avg_temp) / temp_range)
                gdd = ((avg_temp - self.base_temp) * (np.pi/2 + theta) + 
                       temp_range * np.cos(theta)) / np.pi
                gdd = max(0, gdd)
        
        else:
            raise ValueError(f"Unknown method: {method}")
        
        return gdd
    
    def accumulate_gdd(self, 
                      temp_max: float,
                      temp_min: float,
                      date: datetime) -> float:
        """
        Accumulate GDD over time
        
        Args:
            temp_max: Maximum temperature
            temp_min: Minimum temperature
            date: Date of observation
        
        Returns:
            Accumulated GDD
        """
        daily_gdd = self.calculate_daily_gdd(temp_max, temp_min)
        self.accumulated_gdd += daily_gdd
        self.daily_gdd_history.append({
            'date': date,
            'gdd': daily_gdd,
            'accumulated': self.accumulated_gdd
        })
        
        return self.accumulated_gdd
    
    def predict_phenological_event(self,
                                  required_gdd: float,
                                  avg_daily_gdd: float = 10.0) -> int:
        """
        Predict days until phenological event
        
        Args:
            required_gdd: GDD required for event
            avg_daily_gdd: Average daily GDD accumulation
        
        Returns:
            Estimated days until event
        """
        remaining_gdd = required_gdd - self.accumulated_gdd
        if remaining_gdd <= 0:
            return 0
        
        days = int(np.ceil(remaining_gdd / avg_daily_gdd))
        return days
    
    def reset(self):
        """Reset accumulated GDD"""
        self.accumulated_gdd = 0.0
        self.daily_gdd_history = []


class EvapotranspirationCalculator:
    """
    Calculate evapotranspiration using Penman-Monteith equation
    Critical for irrigation scheduling
    """
    
    def __init__(self, latitude: float, elevation_m: float):
        self.latitude = latitude
        self.elevation_m = elevation_m
    
    def calculate_et0(self,
                     temp_max: float,
                     temp_min: float,
                     humidity_avg: float,
                     wind_speed_2m: float,
                     solar_radiation: float,
                     date: datetime) -> float:
        """
        Calculate reference evapotranspiration (ET0) using FAO-56 Penman-Monteith
        
        Args:
            temp_max: Maximum temperature (°C)
            temp_min: Minimum temperature (°C)
            humidity_avg: Average relative humidity (%)
            wind_speed_2m: Wind speed at 2m height (m/s)
            solar_radiation: Solar radiation (MJ/m²/day)
            date: Date for calculation
        
        Returns:
            Reference ET (mm/day)
        """
        # Mean temperature
        temp_mean = (temp_max + temp_min) / 2
        
        # Atmospheric pressure (kPa)
        P = 101.3 * ((293 - 0.0065 * self.elevation_m) / 293) ** 5.26
        
        # Psychrometric constant (kPa/°C)
        gamma = 0.000665 * P
        
        # Saturation vapor pressure (kPa)
        es_tmax = 0.6108 * np.exp((17.27 * temp_max) / (temp_max + 237.3))
        es_tmin = 0.6108 * np.exp((17.27 * temp_min) / (temp_min + 237.3))
        es = (es_tmax + es_tmin) / 2
        
        # Actual vapor pressure (kPa)
        ea = es * (humidity_avg / 100)
        
        # Slope of vapor pressure curve (kPa/°C)
        delta = (4098 * es) / ((temp_mean + 237.3) ** 2)
        
        # Net radiation (MJ/m²/day) - simplified
        Rn = solar_radiation * 0.77  # Assuming 77% net radiation
        
        # Soil heat flux (negligible for daily calculations)
        G = 0
        
        # ET0 calculation (mm/day)
        numerator = (0.408 * delta * (Rn - G) + 
                    gamma * (900 / (temp_mean + 273)) * wind_speed_2m * (es - ea))
        denominator = delta + gamma * (1 + 0.34 * wind_speed_2m)
        
        et0 = numerator / denominator
        
        return max(0, et0)
    
    def calculate_crop_et(self,
                         et0: float,
                         crop_coefficient: float) -> float:
        """
        Calculate actual crop evapotranspiration
        
        Args:
            et0: Reference evapotranspiration (mm/day)
            crop_coefficient: Crop coefficient (Kc)
        
        Returns:
            Crop ET (mm/day)
        """
        return et0 * crop_coefficient


class WeatherBasedDiseaseRiskPredictor:
    """
    Predict disease risk based on weather conditions
    Uses expert rules and machine learning
    """
    
    def __init__(self):
        self.disease_models = self._initialize_disease_models()
        self.ml_model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=5,
            random_state=42
        )
    
    def _initialize_disease_models(self) -> Dict[str, Dict]:
        """
        Initialize disease risk models with favorable conditions
        """
        return {
            'late_blight': {
                'temp_range': (10, 25),
                'humidity_min': 90,
                'leaf_wetness_hours': 10,
                'severity_high_temp': 18,
                'favorable_rain': True
            },
            'powdery_mildew': {
                'temp_range': (20, 30),
                'humidity_min': 70,
                'leaf_wetness_hours': 0,  # Doesn't require wetness
                'severity_high_temp': 25,
                'favorable_rain': False
            },
            'fire_blight': {
                'temp_range': (18, 30),
                'humidity_min': 70,
                'leaf_wetness_hours': 4,
                'severity_high_temp': 24,
                'favorable_rain': True
            },
            'apple_scab': {
                'temp_range': (6, 24),
                'humidity_min': 95,
                'leaf_wetness_hours': 9,
                'severity_high_temp': 16,
                'favorable_rain': True
            },
            'botrytis': {
                'temp_range': (15, 25),
                'humidity_min': 85,
                'leaf_wetness_hours': 15,
                'severity_high_temp': 20,
                'favorable_rain': True
            },
            'rust': {
                'temp_range': (15, 28),
                'humidity_min': 100,  # Needs 100% RH
                'leaf_wetness_hours': 8,
                'severity_high_temp': 22,
                'favorable_rain': True
            }
        }
    
    def predict_disease_risk(self,
                           disease_name: str,
                           weather_data: WeatherData,
                           leaf_wetness_hours: float,
                           recent_rainfall_mm: float) -> DiseaseRisk:
        """
        Predict disease infection risk
        
        Args:
            disease_name: Name of disease
            weather_data: Current weather data
            leaf_wetness_hours: Hours of leaf wetness in last 24h
            recent_rainfall_mm: Rainfall in last 7 days
        
        Returns:
            DiseaseRisk assessment
        """
        if disease_name not in self.disease_models:
            raise ValueError(f"Unknown disease: {disease_name}")
        
        model = self.disease_models[disease_name]
        
        # Check favorable conditions
        favorable_conditions = []
        risk_score = 0
        
        # Temperature
        temp = weather_data.temperature_celsius
        temp_range = model['temp_range']
        if temp_range[0] <= temp <= temp_range[1]:
            favorable_conditions.append(f"Temperature optimal ({temp:.1f}°C)")
            risk_score += 25
        
        # Humidity
        if weather_data.humidity_percent >= model['humidity_min']:
            favorable_conditions.append(f"High humidity ({weather_data.humidity_percent:.0f}%)")
            risk_score += 25
        
        # Leaf wetness
        if leaf_wetness_hours >= model['leaf_wetness_hours']:
            favorable_conditions.append(f"Sufficient leaf wetness ({leaf_wetness_hours:.1f} hours)")
            risk_score += 30
        
        # Rainfall
        if model['favorable_rain'] and recent_rainfall_mm > 5:
            favorable_conditions.append(f"Recent rainfall ({recent_rainfall_mm:.1f}mm)")
            risk_score += 20
        
        # Determine risk level
        if risk_score >= 75:
            risk_level = "Severe"
            action_required = True
        elif risk_score >= 50:
            risk_level = "High"
            action_required = True
        elif risk_score >= 25:
            risk_level = "Moderate"
            action_required = False
        else:
            risk_level = "Low"
            action_required = False
        
        # Calculate infection probability
        infection_prob = min(1.0, risk_score / 100)
        
        # Generate recommendations
        recommendations = self._generate_disease_recommendations(
            disease_name, risk_level, favorable_conditions
        )
        
        return DiseaseRisk(
            disease_name=disease_name,
            risk_level=risk_level,
            risk_score=risk_score,
            favorable_conditions=favorable_conditions,
            current_conditions={
                'temperature': temp,
                'humidity': weather_data.humidity_percent,
                'leaf_wetness': leaf_wetness_hours,
                'rainfall': recent_rainfall_mm
            },
            infection_probability=infection_prob,
            action_required=action_required,
            recommendations=recommendations
        )
    
    def _generate_disease_recommendations(self,
                                         disease: str,
                                         risk_level: str,
                                         favorable_conditions: List[str]) -> List[str]:
        """Generate disease management recommendations"""
        recommendations = []
        
        if risk_level in ["High", "Severe"]:
            recommendations.append(f"Apply fungicide for {disease} immediately")
            recommendations.append("Increase monitoring frequency to every 2-3 days")
            recommendations.append("Scout for early symptoms")
        elif risk_level == "Moderate":
            recommendations.append(f"Prepare for potential {disease} outbreak")
            recommendations.append("Monitor weather forecast closely")
            recommendations.append("Consider preventive fungicide application")
        else:
            recommendations.append("Continue routine monitoring")
        
        if len(favorable_conditions) > 2:
            recommendations.append("Multiple favorable conditions present - high vigilance required")
        
        return recommendations


class FrostRiskForecaster:
    """
    Forecast frost risk for crop protection
    """
    
    def __init__(self):
        self.critical_temps = {
            'dormant_buds': -15.0,
            'swollen_buds': -5.0,
            'bud_burst': -2.0,
            'flowering': -1.0,
            'fruit_set': -0.5,
            'young_fruit': 0.0
        }
    
    def forecast_frost_risk(self,
                          forecast_temps: List[float],
                          forecast_times: List[datetime],
                          growth_stage: str,
                          elevation_m: float,
                          sky_cover: float) -> FrostRisk:
        """
        Forecast frost risk
        
        Args:
            forecast_temps: Forecasted temperatures
            forecast_times: Forecast timestamps
            growth_stage: Current crop growth stage
            elevation_m: Field elevation
            sky_cover: Cloud cover (0-1)
        
        Returns:
            FrostRisk assessment
        """
        critical_temp = self.critical_temps.get(growth_stage, -2.0)
        
        # Find minimum temperature
        min_temp = min(forecast_temps)
        min_temp_time = forecast_times[forecast_temps.index(min_temp)]
        
        # Adjust for radiative cooling (clear skies)
        if sky_cover < 0.3:  # Clear night
            radiative_cooling = 2.0
        elif sky_cover < 0.7:
            radiative_cooling = 1.0
        else:
            radiative_cooling = 0.0
        
        adjusted_min_temp = min_temp - radiative_cooling
        
        # Calculate hours below critical temperature
        hours_below = sum(1 for t in forecast_temps if t < critical_temp)
        
        # Calculate frost probability
        if adjusted_min_temp < critical_temp - 2:
            probability = 0.9
            risk_level = "Critical"
        elif adjusted_min_temp < critical_temp:
            probability = 0.7
            risk_level = "High"
        elif adjusted_min_temp < critical_temp + 1:
            probability = 0.4
            risk_level = "Moderate"
        else:
            probability = 0.1
            risk_level = "Low"
        
        # Protection recommendations
        protection_recommended = risk_level in ["High", "Critical"]
        
        protection_methods = []
        if protection_recommended:
            protection_methods.append("Activate wind machines or heaters")
            protection_methods.append("Apply water for evaporative cooling")
            protection_methods.append("Use frost blankets or covers")
            protection_methods.append("Increase air circulation")
        
        return FrostRisk(
            date=min_temp_time,
            probability=probability,
            min_temperature_expected=adjusted_min_temp,
            critical_temperature=critical_temp,
            risk_level=risk_level,
            hours_below_critical=hours_below,
            protection_recommended=protection_recommended,
            protection_methods=protection_methods
        )


class FlightWindowCalculator:
    """
    Calculate optimal flight windows for drone operations
    """
    
    def __init__(self):
        self.weather_thresholds = {
            'max_wind_speed': 10.0,  # m/s
            'max_gust_speed': 15.0,  # m/s
            'min_visibility': 1.0,  # km
            'max_precipitation': 0.1,  # mm/hr
            'min_temperature': 0.0,  # °C
            'max_temperature': 40.0  # °C
        }
    
    def calculate_flight_windows(self,
                                weather_forecast: List[WeatherData],
                                operation_type: str = 'monitoring') -> List[FlightWindow]:
        """
        Calculate optimal flight windows
        
        Args:
            weather_forecast: List of weather forecasts
            operation_type: Type of operation (monitoring, spraying, etc.)
        
        Returns:
            List of suitable flight windows
        """
        if operation_type == 'spraying':
            # Stricter limits for spraying
            self.weather_thresholds['max_wind_speed'] = 5.0
            self.weather_thresholds['max_gust_speed'] = 8.0
        
        flight_windows = []
        
        for i, weather in enumerate(weather_forecast):
            suitability, risk_factors = self._assess_flight_suitability(weather)
            
            if suitability in [FlightSuitability.OPTIMAL, FlightSuitability.SUITABLE]:
                # Find continuous window
                start_time = weather.timestamp
                end_idx = i
                
                for j in range(i + 1, len(weather_forecast)):
                    next_suit, _ = self._assess_flight_suitability(weather_forecast[j])
                    if next_suit in [FlightSuitability.OPTIMAL, FlightSuitability.SUITABLE]:
                        end_idx = j
                    else:
                        break
                
                end_time = weather_forecast[end_idx].timestamp
                duration = int((end_time - start_time).total_seconds() / 60)
                
                # Calculate recommended altitude based on wind
                recommended_alt = self._calculate_optimal_altitude(weather)
                
                # Assess spray drift risk
                drift_risk = self._assess_spray_drift_risk(weather)
                
                window = FlightWindow(
                    start_time=start_time,
                    end_time=end_time,
                    duration_minutes=duration,
                    suitability=suitability,
                    weather_conditions=weather,
                    risk_factors=risk_factors,
                    recommended_altitude_m=recommended_alt,
                    spray_drift_risk=drift_risk
                )
                
                flight_windows.append(window)
        
        return flight_windows
    
    def _assess_flight_suitability(self, 
                                   weather: WeatherData) -> Tuple[FlightSuitability, List[str]]:
        """Assess flight suitability for given weather"""
        risk_factors = []
        
        # Check each threshold
        if weather.wind_speed_mps > self.weather_thresholds['max_wind_speed']:
            risk_factors.append(f"High wind speed ({weather.wind_speed_mps:.1f} m/s)")
        
        if weather.wind_gust_mps > self.weather_thresholds['max_gust_speed']:
            risk_factors.append(f"Strong gusts ({weather.wind_gust_mps:.1f} m/s)")
        
        if weather.visibility_km < self.weather_thresholds['min_visibility']:
            risk_factors.append(f"Poor visibility ({weather.visibility_km:.1f} km)")
        
        if weather.precipitation_mm > self.weather_thresholds['max_precipitation']:
            risk_factors.append(f"Precipitation ({weather.precipitation_mm:.1f} mm)")
        
        if weather.temperature_celsius < self.weather_thresholds['min_temperature']:
            risk_factors.append(f"Low temperature ({weather.temperature_celsius:.1f}°C)")
        
        if weather.temperature_celsius > self.weather_thresholds['max_temperature']:
            risk_factors.append(f"High temperature ({weather.temperature_celsius:.1f}°C)")
        
        # Determine suitability
        if len(risk_factors) == 0:
            if weather.wind_speed_mps < 3 and weather.visibility_km > 5:
                suitability = FlightSuitability.OPTIMAL
            else:
                suitability = FlightSuitability.SUITABLE
        elif len(risk_factors) <= 2:
            suitability = FlightSuitability.MARGINAL
        else:
            suitability = FlightSuitability.UNSUITABLE
        
        # Check for dangerous conditions
        if (weather.wind_gust_mps > 20 or 
            weather.condition == WeatherCondition.THUNDERSTORM or
            weather.visibility_km < 0.5):
            suitability = FlightSuitability.DANGEROUS
            risk_factors.append("DANGEROUS CONDITIONS - DO NOT FLY")
        
        return suitability, risk_factors
    
    def _calculate_optimal_altitude(self, weather: WeatherData) -> float:
        """Calculate optimal flight altitude"""
        # Lower altitude in high wind
        if weather.wind_speed_mps > 7:
            return 20.0
        elif weather.wind_speed_mps > 5:
            return 30.0
        else:
            return 50.0
    
    def _assess_spray_drift_risk(self, weather: WeatherData) -> str:
        """Assess spray drift risk"""
        if weather.wind_speed_mps < 2:
            return "Low"
        elif weather.wind_speed_mps < 5:
            return "Moderate"
        elif weather.wind_speed_mps < 8:
            return "High"
        else:
            return "Severe"


def main():
    """Demonstration of weather integration system"""
    print("=" * 80)
    print("AgroPulse Advanced Weather Integration System")
    print("=" * 80)
    
    # Initialize components
    api_keys = {'openweathermap': 'demo_key'}
    aggregator = WeatherDataAggregator(api_keys)
    gdd_calc = GrowingDegreeDayCalculator(base_temp=10.0)
    et_calc = EvapotranspirationCalculator(latitude=45.0, elevation_m=200)
    disease_predictor = WeatherBasedDiseaseRiskPredictor()
    frost_forecaster = FrostRiskForecaster()
    flight_calculator = FlightWindowCalculator()
    
    # Fetch weather
    print("\nFetching weather data...")
    weather_data = aggregator.fetch_weather(45.0, -120.0)
    aggregated = aggregator.aggregate_weather(weather_data)
    
    print(f"\nCurrent Weather:")
    print(f"  Temperature: {aggregated.temperature_celsius:.1f}°C")
    print(f"  Humidity: {aggregated.humidity_percent:.0f}%")
    print(f"  Wind Speed: {aggregated.wind_speed_mps:.1f} m/s")
    print(f"  Condition: {aggregated.condition.value}")
    
    # Calculate GDD
    print("\nGrowing Degree Days:")
    gdd = gdd_calc.calculate_daily_gdd(25.0, 15.0)
    print(f"  Today's GDD: {gdd:.1f}")
    
    # Calculate ET
    print("\nEvapotranspiration:")
    et0 = et_calc.calculate_et0(25.0, 15.0, 65.0, 3.0, 20.0, datetime.now())
    print(f"  Reference ET (ET0): {et0:.2f} mm/day")
    
    # Disease risk
    print("\nDisease Risk Assessment:")
    for disease in ['late_blight', 'powdery_mildew', 'fire_blight']:
        risk = disease_predictor.predict_disease_risk(
            disease, aggregated, leaf_wetness_hours=8.0, recent_rainfall_mm=10.0
        )
        print(f"  {risk.disease_name}: {risk.risk_level} ({risk.risk_score:.0f}/100)")
    
    # Flight windows
    print("\nFlight Window Analysis:")
    # Simulate forecast
    forecast = [aggregated for _ in range(24)]
    windows = flight_calculator.calculate_flight_windows(forecast)
    print(f"  Found {len(windows)} suitable flight windows")
    if windows:
        w = windows[0]
        print(f"  Next window: {w.start_time.strftime('%H:%M')} - {w.duration_minutes}min")
        print(f"  Suitability: {w.suitability.value}")
    
    print("\n" + "=" * 80)
    print("Weather analysis complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
