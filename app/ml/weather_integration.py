"""
Weather Integration and Analysis Module

This module provides comprehensive weather data integration and analysis:
- External API integration (OpenWeatherMap, Weather.com, etc.)
- Historical weather data processing
- Weather forecast analysis
- Growing Degree Days (GDD) calculation
- Rainfall accumulation tracking
- Extreme weather alerts
- Weather-based recommendations
- Climate pattern analysis
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)


class WeatherCondition(Enum):
    """Weather conditions."""
    CLEAR = "clear"
    PARTLY_CLOUDY = "partly_cloudy"
    CLOUDY = "cloudy"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    THUNDERSTORM = "thunderstorm"
    DRIZZLE = "drizzle"
    FOG = "fog"
    HAIL = "hail"


class AlertSeverity(Enum):
    """Weather alert severity levels."""
    INFO = "info"
    ADVISORY = "advisory"
    WARNING = "warning"
    SEVERE = "severe"
    EXTREME = "extreme"


@dataclass
class WeatherData:
    """
    Weather data point.
    
    Attributes:
        timestamp: Data timestamp
        temperature: Temperature (Celsius)
        humidity: Relative humidity (%)
        rainfall: Rainfall (mm)
        wind_speed: Wind speed (km/h)
        pressure: Atmospheric pressure (hPa)
        condition: Weather condition
        cloud_cover: Cloud cover (%)
    """
    timestamp: datetime
    temperature: float
    humidity: float
    rainfall: float
    wind_speed: float
    pressure: float
    condition: WeatherCondition
    cloud_cover: float


@dataclass
class WeatherForecast:
    """
    Weather forecast.
    
    Attributes:
        forecast_date: Date of forecast
        temperature_min: Minimum temperature
        temperature_max: Maximum temperature
        temperature_avg: Average temperature
        rainfall_probability: Probability of rain (0-1)
        expected_rainfall: Expected rainfall (mm)
        humidity_avg: Average humidity
        wind_speed_avg: Average wind speed
        condition: Expected weather condition
        confidence: Forecast confidence (0-1)
    """
    forecast_date: datetime
    temperature_min: float
    temperature_max: float
    temperature_avg: float
    rainfall_probability: float
    expected_rainfall: float
    humidity_avg: float
    wind_speed_avg: float
    condition: WeatherCondition
    confidence: float


@dataclass
class WeatherAlert:
    """
    Weather alert.
    
    Attributes:
        alert_type: Type of alert
        severity: Alert severity
        title: Alert title
        description: Detailed description
        start_time: Alert start time
        end_time: Alert end time
        recommendations: Recommended actions
    """
    alert_type: str
    severity: AlertSeverity
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    recommendations: List[str]


class WeatherAPIClient:
    """
    Client for weather API integration.
    """
    
    def __init__(self, api_key: Optional[str] = None, provider: str = "openweathermap"):
        """
        Initialize weather API client.
        
        Args:
            api_key: API key for weather service
            provider: Weather data provider
        """
        self.api_key = api_key
        self.provider = provider
        self.base_url = self._get_base_url(provider)
        logger.info(f"Weather API Client initialized for {provider}")
    
    def _get_base_url(self, provider: str) -> str:
        """Get base URL for provider."""
        urls = {
            "openweathermap": "https://api.openweathermap.org/data/2.5",
            "weatherapi": "https://api.weatherapi.com/v1",
            "climacell": "https://api.climacell.co/v3"
        }
        return urls.get(provider, urls["openweathermap"])
    
    def get_current_weather(self, latitude: float, longitude: float) -> WeatherData:
        """
        Get current weather for location.
        
        Args:
            latitude: Latitude
            longitude: Longitude
            
        Returns:
            Current weather data
        """
        logger.info(f"Fetching current weather for ({latitude}, {longitude})")
        
        # In production, would make actual API call
        # For now, simulate weather data
        return self._simulate_current_weather()
    
    def get_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 7
    ) -> List[WeatherForecast]:
        """
        Get weather forecast.
        
        Args:
            latitude: Latitude
            longitude: Longitude
            days: Number of days to forecast
            
        Returns:
            List of daily forecasts
        """
        logger.info(f"Fetching {days}-day forecast for ({latitude}, {longitude})")
        
        # Simulate forecast
        forecasts = []
        for i in range(days):
            forecast_date = datetime.now() + timedelta(days=i+1)
            forecasts.append(self._simulate_forecast(forecast_date, i))
        
        return forecasts
    
    def get_historical_weather(
        self,
        latitude: float,
        longitude: float,
        start_date: datetime,
        end_date: datetime
    ) -> List[WeatherData]:
        """
        Get historical weather data.
        
        Args:
            latitude: Latitude
            longitude: Longitude
            start_date: Start date
            end_date: End date
            
        Returns:
            List of historical weather data
        """
        logger.info(f"Fetching historical weather from {start_date} to {end_date}")
        
        # Simulate historical data
        data = []
        current_date = start_date
        while current_date <= end_date:
            data.append(self._simulate_historical_weather(current_date))
            current_date += timedelta(days=1)
        
        return data
    
    def _simulate_current_weather(self) -> WeatherData:
        """Simulate current weather data."""
        return WeatherData(
            timestamp=datetime.now(),
            temperature=np.random.uniform(18, 30),
            humidity=np.random.uniform(40, 80),
            rainfall=np.random.exponential(2),
            wind_speed=np.random.uniform(5, 20),
            pressure=np.random.uniform(1010, 1020),
            condition=np.random.choice(list(WeatherCondition)),
            cloud_cover=np.random.uniform(0, 100)
        )
    
    def _simulate_forecast(self, date: datetime, day_offset: int) -> WeatherForecast:
        """Simulate weather forecast."""
        temp_base = 25 - day_offset * 0.5
        
        return WeatherForecast(
            forecast_date=date,
            temperature_min=temp_base - 5,
            temperature_max=temp_base + 5,
            temperature_avg=temp_base,
            rainfall_probability=min(1.0, 0.3 + day_offset * 0.1),
            expected_rainfall=np.random.exponential(5),
            humidity_avg=np.random.uniform(50, 75),
            wind_speed_avg=np.random.uniform(8, 15),
            condition=np.random.choice([WeatherCondition.CLEAR, WeatherCondition.RAIN, WeatherCondition.CLOUDY]),
            confidence=max(0.5, 0.95 - day_offset * 0.05)
        )
    
    def _simulate_historical_weather(self, date: datetime) -> WeatherData:
        """Simulate historical weather."""
        return WeatherData(
            timestamp=date,
            temperature=np.random.uniform(18, 30),
            humidity=np.random.uniform(40, 80),
            rainfall=np.random.exponential(3),
            wind_speed=np.random.uniform(5, 20),
            pressure=np.random.uniform(1010, 1020),
            condition=np.random.choice(list(WeatherCondition)),
            cloud_cover=np.random.uniform(0, 100)
        )


class WeatherAnalyzer:
    """
    Analyze weather data for agricultural insights.
    """
    
    def __init__(self):
        """Initialize weather analyzer."""
        logger.info("Weather Analyzer initialized")
    
    def calculate_gdd(
        self,
        temperature_min: float,
        temperature_max: float,
        base_temperature: float = 10.0,
        upper_threshold: float = 30.0
    ) -> float:
        """
        Calculate Growing Degree Days (GDD).
        
        Args:
            temperature_min: Daily minimum temperature
            temperature_max: Daily maximum temperature
            base_temperature: Base temperature for crop
            upper_threshold: Upper temperature threshold
            
        Returns:
            GDD value
        """
        # Average temperature
        temp_avg = (temperature_min + temperature_max) / 2
        
        # Cap temperatures
        temp_avg = min(temp_avg, upper_threshold)
        temp_avg = max(temp_avg, base_temperature)
        
        # Calculate GDD
        gdd = max(0, temp_avg - base_temperature)
        
        return gdd
    
    def calculate_accumulated_gdd(
        self,
        weather_data: List[WeatherData],
        base_temperature: float = 10.0
    ) -> float:
        """
        Calculate accumulated GDD over period.
        
        Args:
            weather_data: List of weather data points
            base_temperature: Base temperature
            
        Returns:
            Accumulated GDD
        """
        total_gdd = 0
        
        for data in weather_data:
            # Assume temp is average for the day
            daily_gdd = max(0, data.temperature - base_temperature)
            total_gdd += daily_gdd
        
        return total_gdd
    
    def calculate_rainfall_accumulation(
        self,
        weather_data: List[WeatherData],
        days: Optional[int] = None
    ) -> float:
        """
        Calculate rainfall accumulation.
        
        Args:
            weather_data: Weather data
            days: Number of recent days (None for all)
            
        Returns:
            Total rainfall (mm)
        """
        if days:
            recent_data = weather_data[-days:] if len(weather_data) > days else weather_data
        else:
            recent_data = weather_data
        
        total_rainfall = sum(d.rainfall for d in recent_data)
        return total_rainfall
    
    def detect_drought_conditions(
        self,
        weather_data: List[WeatherData],
        threshold_days: int = 14,
        rainfall_threshold: float = 10.0
    ) -> bool:
        """
        Detect drought conditions.
        
        Args:
            weather_data: Weather data
            threshold_days: Number of days to check
            rainfall_threshold: Minimum rainfall (mm)
            
        Returns:
            True if drought detected
        """
        recent_data = weather_data[-threshold_days:] if len(weather_data) > threshold_days else weather_data
        total_rainfall = sum(d.rainfall for d in recent_data)
        
        return total_rainfall < rainfall_threshold
    
    def detect_heat_stress(
        self,
        weather_data: List[WeatherData],
        temperature_threshold: float = 35.0,
        consecutive_days: int = 3
    ) -> bool:
        """
        Detect heat stress conditions.
        
        Args:
            weather_data: Weather data
            temperature_threshold: Temperature threshold
            consecutive_days: Required consecutive days
            
        Returns:
            True if heat stress detected
        """
        if len(weather_data) < consecutive_days:
            return False
        
        recent_data = weather_data[-consecutive_days:]
        high_temp_days = sum(1 for d in recent_data if d.temperature > temperature_threshold)
        
        return high_temp_days >= consecutive_days
    
    def calculate_evapotranspiration(
        self,
        temperature: float,
        humidity: float,
        wind_speed: float,
        solar_radiation: Optional[float] = None
    ) -> float:
        """
        Calculate reference evapotranspiration (ET0) using simplified Penman-Monteith.
        
        Args:
            temperature: Temperature (Celsius)
            humidity: Relative humidity (%)
            wind_speed: Wind speed (km/h)
            solar_radiation: Solar radiation (MJ/m²/day)
            
        Returns:
            ET0 (mm/day)
        """
        # Simplified ET calculation (full Penman-Monteith requires more parameters)
        
        # Saturation vapor pressure
        e_sat = 0.6108 * np.exp(17.27 * temperature / (temperature + 237.3))
        
        # Actual vapor pressure
        e_actual = e_sat * humidity / 100
        
        # Vapor pressure deficit
        vpd = e_sat - e_actual
        
        # Convert wind speed to m/s
        wind_ms = wind_speed / 3.6
        
        # Simplified ET0 estimation
        et0 = 0.408 * vpd * (1 + 0.34 * wind_ms)
        
        return max(0, et0)
    
    def analyze_weather_suitability(
        self,
        weather_data: List[WeatherData],
        crop_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze weather suitability for crop.
        
        Args:
            weather_data: Historical weather data
            crop_requirements: Crop weather requirements
            
        Returns:
            Suitability analysis
        """
        if not weather_data:
            return {"suitability": "unknown", "score": 0}
        
        # Calculate averages
        avg_temp = np.mean([d.temperature for d in weather_data])
        total_rainfall = sum(d.rainfall for d in weather_data)
        avg_humidity = np.mean([d.humidity for d in weather_data])
        
        # Check temperature suitability
        temp_range = crop_requirements.get("temperature_range", (15, 30))
        temp_suitable = temp_range[0] <= avg_temp <= temp_range[1]
        
        # Check rainfall suitability
        rainfall_range = crop_requirements.get("rainfall_requirement", (400, 800))
        # Annualize rainfall
        days_in_data = len(weather_data)
        annual_rainfall = total_rainfall * (365 / days_in_data) if days_in_data > 0 else 0
        rainfall_suitable = rainfall_range[0] <= annual_rainfall <= rainfall_range[1]
        
        # Calculate suitability score
        score = 0
        if temp_suitable:
            score += 50
        else:
            # Penalty based on deviation
            temp_deviation = min(
                abs(avg_temp - temp_range[0]),
                abs(avg_temp - temp_range[1])
            )
            score += max(0, 50 - temp_deviation * 5)
        
        if rainfall_suitable:
            score += 50
        else:
            # Penalty based on deviation
            rainfall_target = np.mean(rainfall_range)
            rainfall_deviation_pct = abs(annual_rainfall - rainfall_target) / rainfall_target
            score += max(0, 50 - rainfall_deviation_pct * 50)
        
        # Classify suitability
        if score >= 80:
            suitability = "excellent"
        elif score >= 60:
            suitability = "good"
        elif score >= 40:
            suitability = "moderate"
        else:
            suitability = "poor"
        
        return {
            "suitability": suitability,
            "score": score,
            "temperature_suitable": temp_suitable,
            "rainfall_suitable": rainfall_suitable,
            "avg_temperature": avg_temp,
            "annual_rainfall_estimate": annual_rainfall,
            "avg_humidity": avg_humidity
        }


class WeatherAlertSystem:
    """
    Generate weather alerts for farmers.
    """
    
    def __init__(self):
        """Initialize weather alert system."""
        logger.info("Weather Alert System initialized")
    
    def generate_alerts(
        self,
        current_weather: WeatherData,
        forecast: List[WeatherForecast],
        crop_stage: Optional[str] = None
    ) -> List[WeatherAlert]:
        """
        Generate weather alerts.
        
        Args:
            current_weather: Current weather
            forecast: Weather forecast
            crop_stage: Current crop growth stage
            
        Returns:
            List of weather alerts
        """
        alerts = []
        
        # Check for extreme heat
        if current_weather.temperature > 38:
            alerts.append(self._create_heat_alert(current_weather))
        
        # Check for heavy rain
        heavy_rain_days = [f for f in forecast if f.expected_rainfall > 50]
        if heavy_rain_days:
            alerts.append(self._create_heavy_rain_alert(heavy_rain_days))
        
        # Check for drought
        total_forecast_rain = sum(f.expected_rainfall for f in forecast)
        if total_forecast_rain < 5:
            alerts.append(self._create_drought_alert(forecast))
        
        # Check for frost risk (low temperature)
        frost_risk = [f for f in forecast if f.temperature_min < 5]
        if frost_risk:
            alerts.append(self._create_frost_alert(frost_risk))
        
        # Check for high winds
        if current_weather.wind_speed > 40:
            alerts.append(self._create_wind_alert(current_weather))
        
        return alerts
    
    def _create_heat_alert(self, weather: WeatherData) -> WeatherAlert:
        """Create heat alert."""
        return WeatherAlert(
            alert_type="extreme_heat",
            severity=AlertSeverity.WARNING,
            title="Extreme Heat Warning",
            description=f"Temperature has reached {weather.temperature:.1f}°C. Crops may experience heat stress.",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(hours=12),
            recommendations=[
                "Increase irrigation frequency",
                "Apply mulch to conserve soil moisture",
                "Provide shade for sensitive crops if possible",
                "Avoid fertilizer application during heat stress"
            ]
        )
    
    def _create_heavy_rain_alert(self, forecast_days: List[WeatherForecast]) -> WeatherAlert:
        """Create heavy rain alert."""
        total_rain = sum(f.expected_rainfall for f in forecast_days)
        
        return WeatherAlert(
            alert_type="heavy_rainfall",
            severity=AlertSeverity.ADVISORY,
            title="Heavy Rainfall Expected",
            description=f"Heavy rainfall expected: {total_rain:.1f}mm over next {len(forecast_days)} days.",
            start_time=forecast_days[0].forecast_date,
            end_time=forecast_days[-1].forecast_date,
            recommendations=[
                "Ensure proper drainage in fields",
                "Postpone fertilizer application",
                "Harvest mature crops before heavy rains",
                "Check for waterlogging after rains"
            ]
        )
    
    def _create_drought_alert(self, forecast: List[WeatherForecast]) -> WeatherAlert:
        """Create drought alert."""
        return WeatherAlert(
            alert_type="drought_conditions",
            severity=AlertSeverity.WARNING,
            title="Dry Conditions Expected",
            description=f"Little to no rainfall expected in next {len(forecast)} days.",
            start_time=datetime.now(),
            end_time=forecast[-1].forecast_date,
            recommendations=[
                "Implement water conservation measures",
                "Plan irrigation schedule",
                "Apply mulch to reduce evaporation",
                "Consider drought-resistant crop varieties for next season"
            ]
        )
    
    def _create_frost_alert(self, forecast_days: List[WeatherForecast]) -> WeatherAlert:
        """Create frost alert."""
        return WeatherAlert(
            alert_type="frost_risk",
            severity=AlertSeverity.SEVERE,
            title="Frost Risk Alert",
            description=f"Temperatures may drop below 5°C on {len(forecast_days)} day(s).",
            start_time=forecast_days[0].forecast_date,
            end_time=forecast_days[-1].forecast_date,
            recommendations=[
                "Cover sensitive crops overnight",
                "Water plants before cold nights (wet soil retains heat)",
                "Avoid pruning before cold periods",
                "Harvest frost-sensitive crops immediately"
            ]
        )
    
    def _create_wind_alert(self, weather: WeatherData) -> WeatherAlert:
        """Create wind alert."""
        return WeatherAlert(
            alert_type="high_winds",
            severity=AlertSeverity.ADVISORY,
            title="High Wind Advisory",
            description=f"Wind speeds of {weather.wind_speed:.1f} km/h detected.",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(hours=6),
            recommendations=[
                "Secure loose items and equipment",
                "Check staking of tall crops",
                "Postpone spraying operations",
                "Inspect structures after wind subsides"
            ]
        )


class WeatherRecommendationEngine:
    """
    Generate weather-based farming recommendations.
    """
    
    def __init__(self):
        """Initialize recommendation engine."""
        self.analyzer = WeatherAnalyzer()
        logger.info("Weather Recommendation Engine initialized")
    
    def get_irrigation_recommendation(
        self,
        current_weather: WeatherData,
        forecast: List[WeatherForecast],
        soil_moisture: float,
        crop_type: str
    ) -> Dict[str, Any]:
        """
        Get irrigation recommendations.
        
        Args:
            current_weather: Current weather
            forecast: Weather forecast
            soil_moisture: Current soil moisture (%)
            crop_type: Type of crop
            
        Returns:
            Irrigation recommendation
        """
        # Calculate ET0
        et0 = self.analyzer.calculate_evapotranspiration(
            current_weather.temperature,
            current_weather.humidity,
            current_weather.wind_speed
        )
        
        # Check forecast rainfall
        forecast_rainfall = sum(f.expected_rainfall for f in forecast[:3])  # Next 3 days
        
        # Determine irrigation need
        if soil_moisture < 30:
            need = "urgent"
            amount = 30  # mm
        elif soil_moisture < 50 and forecast_rainfall < 10:
            need = "recommended"
            amount = 20
        elif soil_moisture < 70 and forecast_rainfall < 5:
            need = "optional"
            amount = 10
        else:
            need = "not_needed"
            amount = 0
        
        return {
            "irrigation_need": need,
            "recommended_amount_mm": amount,
            "evapotranspiration_mm_day": et0,
            "forecast_rainfall_3day_mm": forecast_rainfall,
            "current_soil_moisture_pct": soil_moisture,
            "timing_recommendation": "Early morning or evening" if need != "not_needed" else None
        }
    
    def get_planting_recommendation(
        self,
        forecast: List[WeatherForecast],
        soil_conditions: Dict[str, Any],
        crop: str
    ) -> Dict[str, Any]:
        """
        Get planting recommendations based on weather.
        
        Args:
            forecast: Weather forecast
            soil_conditions: Soil conditions
            crop: Crop to plant
            
        Returns:
            Planting recommendation
        """
        # Check forecast
        avg_temp = np.mean([f.temperature_avg for f in forecast])
        total_rain = sum(f.expected_rainfall for f in forecast)
        rain_days = sum(1 for f in forecast if f.expected_rainfall > 5)
        
        # Determine planting window
        suitable = True
        reasons = []
        
        if avg_temp < 15:
            suitable = False
            reasons.append("Temperature too low for optimal germination")
        elif avg_temp > 35:
            suitable = False
            reasons.append("Temperature too high - risk of seed failure")
        
        if total_rain < 20:
            reasons.append("Low rainfall expected - irrigation recommended")
        elif total_rain > 100:
            suitable = False
            reasons.append("Heavy rainfall expected - risk of waterlogging")
        
        soil_moisture = soil_conditions.get("moisture", 50)
        if soil_moisture < 30:
            reasons.append("Soil moisture low - irrigate before planting")
        elif soil_moisture > 80:
            suitable = False
            reasons.append("Soil too wet for planting")
        
        recommendation = "recommended" if suitable else "wait"
        if suitable and len(reasons) > 0:
            recommendation = "proceed_with_caution"
        
        return {
            "recommendation": recommendation,
            "suitable_for_planting": suitable,
            "reasons": reasons,
            "optimal_planting_days": [
                f.forecast_date.strftime("%Y-%m-%d")
                for f in forecast[:7]
                if 15 < f.temperature_avg < 30 and 5 < f.expected_rainfall < 20
            ],
            "avg_temperature_forecast": avg_temp,
            "total_rainfall_forecast": total_rain
        }
    
    def get_harvest_recommendation(
        self,
        forecast: List[WeatherForecast],
        crop_maturity: str,
        days_to_maturity: int
    ) -> Dict[str, Any]:
        """
        Get harvest timing recommendations.
        
        Args:
            forecast: Weather forecast
            crop_maturity: Crop maturity level
            days_to_maturity: Days until maturity
            
        Returns:
            Harvest recommendation
        """
        # Check if crop is ready
        if crop_maturity != "mature" and days_to_maturity > 7:
            return {
                "recommendation": "wait",
                "reason": f"Crop not yet mature - {days_to_maturity} days remaining",
                "optimal_harvest_window": None
            }
        
        # Find optimal harvest window
        dry_days = [
            f for f in forecast[:7]
            if f.expected_rainfall < 5 and f.humidity_avg < 70
        ]
        
        if not dry_days:
            return {
                "recommendation": "harvest_urgently",
                "reason": "No dry weather expected in forecast - harvest now to avoid crop damage",
                "optimal_harvest_window": "immediately"
            }
        
        optimal_day = dry_days[0]
        
        return {
            "recommendation": "plan_harvest",
            "reason": f"Optimal conditions on {optimal_day.forecast_date.strftime('%Y-%m-%d')}",
            "optimal_harvest_window": optimal_day.forecast_date.strftime("%Y-%m-%d"),
            "temperature": optimal_day.temperature_avg,
            "rainfall_probability": optimal_day.rainfall_probability,
            "preparation_days": (optimal_day.forecast_date - datetime.now()).days
        }
