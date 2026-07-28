"""
OpenWeatherMap API Client
=========================

Comprehensive integration with OpenWeatherMap for current weather,
forecasts, and agricultural alerts.
"""

import requests
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
import redis
import json

logger = logging.getLogger(__name__)


@dataclass
class WeatherData:
    """Current weather data."""
    timestamp: datetime
    temperature: float  # °C
    feels_like: float
    humidity: int  # %
    pressure: int  # hPa
    wind_speed: float  # m/s
    wind_direction: int  # degrees
    cloudiness: int  # %
    rainfall: float  # mm (last hour)
    description: str
    icon: str
    location: str
    latitude: float
    longitude: float


@dataclass
class ForecastData:
    """Weather forecast data."""
    timestamp: datetime
    temperature: float
    temperature_min: float
    temperature_max: float
    humidity: int
    pressure: int
    wind_speed: float
    rainfall: float
    rainfall_probability: float  # 0-1
    description: str
    icon: str


@dataclass
class AgriculturalAlert:
    """Agricultural weather alert."""
    alert_type: str  # 'frost', 'heat', 'drought', 'flood', 'wind'
    severity: str  # 'low', 'medium', 'high', 'critical'
    start_time: datetime
    end_time: datetime
    description: str
    recommendations: List[str]


class OpenWeatherMapClient:
    """
    OpenWeatherMap API client for agricultural weather data.
    
    Features:
    - Current weather conditions
    - 5-day/3-hour forecasts
    - 16-day daily forecasts
    - Historical weather data
    - Weather alerts
    - Agricultural indices (growing degree days, etc.)
    
    API Tiers:
    - Free: 1,000 calls/day
    - Startup: $40/month, 100,000 calls/day
    - Developer: $110/month, 1,000,000 calls/day
    """
    
    def __init__(
        self,
        api_key: str,
        redis_client: Optional[redis.Redis] = None,
        cache_ttl: int = 600,  # 10 minutes
        units: str = 'metric',
    ):
        """
        Initialize OpenWeatherMap client.
        
        Args:
            api_key: OpenWeatherMap API key
            redis_client: Redis for caching
            cache_ttl: Cache TTL in seconds
            units: 'metric', 'imperial', or 'standard'
        """
        self.api_key = api_key
        self.redis_client = redis_client
        self.cache_ttl = cache_ttl
        self.units = units
        
        # API endpoints
        self.base_url = 'https://api.openweathermap.org/data/2.5'
        self.onecall_url = 'https://api.openweathermap.org/data/3.0/onecall'
        self.geocode_url = 'https://api.openweathermap.org/geo/1.0/direct'

        # Agricultural API (requires special subscription)
        self.agro_url = 'https://api.openweathermap.org/agro/1.0'

    def geocode(self, location_name: str) -> Optional[Tuple[float, float]]:
        """
        Resolve a real place name (e.g. 'Nairobi,KE' or 'Thika') to
        (latitude, longitude) via OpenWeatherMap's free Geocoding API - part
        of the same free tier as current weather, no separate subscription.

        Args:
            location_name: A city/town name, optionally 'City,CountryCode'.

        Returns:
            (latitude, longitude), or None if no match was found or the
            request failed.
        """
        params = {
            'q': location_name,
            'limit': 1,
            'appid': self.api_key,
        }

        try:
            response = requests.get(self.geocode_url, params=params, timeout=10)
            response.raise_for_status()

            results = response.json()
            if not results:
                logger.warning(f"Geocoding found no match for '{location_name}'")
                return None

            latitude, longitude = results[0]['lat'], results[0]['lon']
            logger.info(f"Geocoded '{location_name}' -> {latitude},{longitude}")
            return latitude, longitude

        except Exception as e:
            logger.error(f"Failed to geocode '{location_name}': {e}")
            return None

    def get_current_weather(
        self,
        latitude: float,
        longitude: float,
        location_name: str = '',
    ) -> Optional[WeatherData]:
        """
        Get current weather for a location.
        
        Args:
            latitude: Latitude
            longitude: Longitude
            location_name: Optional location name
            
        Returns:
            WeatherData object or None
        """
        # Check cache
        cache_key = f"weather:current:{latitude}:{longitude}"
        if self.redis_client:
            cached = self.redis_client.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for current weather at {latitude}, {longitude}")
                data = json.loads(cached)
                return WeatherData(**data)
                
        # Call API
        params = {
            'lat': latitude,
            'lon': longitude,
            'appid': self.api_key,
            'units': self.units,
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/weather",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            weather = WeatherData(
                timestamp=datetime.fromtimestamp(data['dt']),
                temperature=data['main']['temp'],
                feels_like=data['main']['feels_like'],
                humidity=data['main']['humidity'],
                pressure=data['main']['pressure'],
                wind_speed=data['wind']['speed'],
                wind_direction=data['wind'].get('deg', 0),
                cloudiness=data['clouds']['all'],
                rainfall=data.get('rain', {}).get('1h', 0.0),
                description=data['weather'][0]['description'],
                icon=data['weather'][0]['icon'],
                location=location_name or data.get('name', 'Unknown'),
                latitude=latitude,
                longitude=longitude,
            )
            
            # Cache result
            if self.redis_client:
                weather_dict = {
                    'timestamp': weather.timestamp.isoformat(),
                    'temperature': weather.temperature,
                    'feels_like': weather.feels_like,
                    'humidity': weather.humidity,
                    'pressure': weather.pressure,
                    'wind_speed': weather.wind_speed,
                    'wind_direction': weather.wind_direction,
                    'cloudiness': weather.cloudiness,
                    'rainfall': weather.rainfall,
                    'description': weather.description,
                    'icon': weather.icon,
                    'location': weather.location,
                    'latitude': weather.latitude,
                    'longitude': weather.longitude,
                }
                self.redis_client.setex(
                    cache_key,
                    self.cache_ttl,
                    json.dumps(weather_dict)
                )
                
            logger.info(f"Current weather for {latitude},{longitude}: {weather.temperature}°C, {weather.description}")
            return weather
            
        except Exception as e:
            logger.error(f"Failed to get current weather: {e}")
            return None
            
    def get_5day_forecast(
        self,
        latitude: float,
        longitude: float,
    ) -> List[ForecastData]:
        """
        Get 5-day/3-hour forecast.
        
        Args:
            latitude: Latitude
            longitude: Longitude
            
        Returns:
            List of ForecastData objects (40 data points)
        """
        params = {
            'lat': latitude,
            'lon': longitude,
            'appid': self.api_key,
            'units': self.units,
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/forecast",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            forecasts = []
            for item in data['list']:
                forecast = ForecastData(
                    timestamp=datetime.fromtimestamp(item['dt']),
                    temperature=item['main']['temp'],
                    temperature_min=item['main']['temp_min'],
                    temperature_max=item['main']['temp_max'],
                    humidity=item['main']['humidity'],
                    pressure=item['main']['pressure'],
                    wind_speed=item['wind']['speed'],
                    rainfall=item.get('rain', {}).get('3h', 0.0),
                    rainfall_probability=item.get('pop', 0.0),
                    description=item['weather'][0]['description'],
                    icon=item['weather'][0]['icon'],
                )
                forecasts.append(forecast)
                
            logger.info(f"Retrieved {len(forecasts)} forecast data points")
            return forecasts
            
        except Exception as e:
            logger.error(f"Failed to get 5-day forecast: {e}")
            return []
            
    def get_one_call_data(
        self,
        latitude: float,
        longitude: float,
        exclude: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get comprehensive weather data (One Call API 3.0).
        
        Includes:
        - Current weather
        - Minutely forecast (1 hour)
        - Hourly forecast (48 hours)
        - Daily forecast (8 days)
        - Weather alerts
        
        Args:
            latitude: Latitude
            longitude: Longitude
            exclude: Parts to exclude ('current', 'minutely', 'hourly', 'daily', 'alerts')
            
        Returns:
            Complete weather data dictionary
        """
        params = {
            'lat': latitude,
            'lon': longitude,
            'appid': self.api_key,
            'units': self.units,
        }
        
        if exclude:
            params['exclude'] = ','.join(exclude)
            
        try:
            response = requests.get(
                self.onecall_url,
                params=params,
                timeout=15
            )
            response.raise_for_status()
            
            data = response.json()
            
            logger.info(f"Retrieved One Call data for {latitude},{longitude}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to get One Call data: {e}")
            return {}
            
    def get_agricultural_alerts(
        self,
        latitude: float,
        longitude: float,
        current_weather: Optional[WeatherData] = None,
        forecast: Optional[List[ForecastData]] = None,
    ) -> List[AgriculturalAlert]:
        """
        Generate agricultural alerts based on weather conditions.
        
        Args:
            latitude: Latitude
            longitude: Longitude
            current_weather: Current weather data
            forecast: Forecast data
            
        Returns:
            List of agricultural alerts
        """
        alerts = []
        
        # Get weather data if not provided
        if not current_weather:
            current_weather = self.get_current_weather(latitude, longitude)
            
        if not forecast:
            forecast = self.get_5day_forecast(latitude, longitude)
            
        if not current_weather or not forecast:
            return alerts
            
        # Frost alert (temperature < 2°C)
        if current_weather.temperature < 2:
            alerts.append(AgriculturalAlert(
                alert_type='frost',
                severity='critical',
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(hours=12),
                description='Frost conditions detected. Crops at risk.',
                recommendations=[
                    'Cover sensitive plants',
                    'Use frost protection methods',
                    'Delay planting',
                    'Harvest vulnerable crops immediately',
                ],
            ))
            
        # Heat stress alert (temperature > 35°C)
        if current_weather.temperature > 35:
            alerts.append(AgriculturalAlert(
                alert_type='heat',
                severity='high',
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(hours=8),
                description='Extreme heat. Crop stress likely.',
                recommendations=[
                    'Increase irrigation frequency',
                    'Provide shade if possible',
                    'Monitor crop health closely',
                    'Avoid field work during peak heat',
                ],
            ))
            
        # Drought alert (no rain in forecast + low humidity)
        rain_forecast = [f.rainfall for f in forecast[:8]]  # Next 24 hours
        total_rain = sum(rain_forecast)
        
        if total_rain < 2 and current_weather.humidity < 40:
            alerts.append(AgriculturalAlert(
                alert_type='drought',
                severity='medium',
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(days=3),
                description='Dry conditions expected. Limited rainfall.',
                recommendations=[
                    'Implement water conservation',
                    'Prioritize critical crops for irrigation',
                    'Mulch to retain soil moisture',
                    'Monitor soil moisture levels',
                ],
            ))
            
        # Heavy rain alert (>20mm in 3 hours)
        if total_rain > 20:
            alerts.append(AgriculturalAlert(
                alert_type='flood',
                severity='high',
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(hours=24),
                description='Heavy rainfall expected. Flooding risk.',
                recommendations=[
                    'Clear drainage channels',
                    'Protect young plants',
                    'Delay irrigation',
                    'Harvest ripe crops before rain',
                ],
            ))
            
        # Wind alert (wind speed > 15 m/s = 54 km/h)
        if current_weather.wind_speed > 15:
            alerts.append(AgriculturalAlert(
                alert_type='wind',
                severity='medium',
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(hours=6),
                description='High winds detected. Crop damage possible.',
                recommendations=[
                    'Secure greenhouses and structures',
                    'Stake tall plants',
                    'Postpone spraying operations',
                    'Check for wind damage after event',
                ],
            ))
            
        logger.info(f"Generated {len(alerts)} agricultural alerts")
        return alerts
        
    def calculate_growing_degree_days(
        self,
        forecast: List[ForecastData],
        base_temperature: float = 10.0,
        max_temperature: float = 30.0,
    ) -> float:
        """
        Calculate Growing Degree Days (GDD) from forecast.
        
        GDD = (Tmax + Tmin) / 2 - Tbase
        
        Args:
            forecast: Forecast data
            base_temperature: Base temperature for crop (°C)
            max_temperature: Maximum effective temperature (°C)
            
        Returns:
            Total GDD value
        """
        total_gdd = 0.0
        
        for item in forecast:
            t_max = min(item.temperature_max, max_temperature)
            t_min = max(item.temperature_min, base_temperature)
            
            daily_gdd = ((t_max + t_min) / 2) - base_temperature
            daily_gdd = max(0, daily_gdd)  # GDD cannot be negative
            
            total_gdd += daily_gdd
            
        logger.info(f"Calculated GDD: {total_gdd:.1f}")
        return total_gdd
        
    def get_evapotranspiration(
        self,
        latitude: float,
        longitude: float,
        crop_coefficient: float = 1.0,
    ) -> float:
        """
        Calculate reference evapotranspiration (ET0) using Penman-Monteith equation.
        
        Args:
            latitude: Latitude
            longitude: Longitude
            crop_coefficient: Crop coefficient (Kc)
            
        Returns:
            ET0 in mm/day
        """
        weather = self.get_current_weather(latitude, longitude)
        
        if not weather:
            return 0.0
            
        # Simplified Penman-Monteith (would need more data for full equation)
        # This is a rough approximation
        temperature = weather.temperature
        humidity = weather.humidity
        wind_speed = weather.wind_speed
        solar_radiation = 25  # Assumed average (would need actual data)
        
        # Saturation vapor pressure
        es = 0.6108 * (2.7183 ** ((17.27 * temperature) / (temperature + 237.3)))
        
        # Actual vapor pressure
        ea = es * (humidity / 100)
        
        # Vapor pressure deficit
        vpd = es - ea
        
        # Simplified ET0 calculation
        et0 = (0.408 * solar_radiation + vpd * wind_speed) / (temperature + 15)
        
        # Crop evapotranspiration
        etc = et0 * crop_coefficient
        
        logger.info(f"Calculated ET0: {et0:.2f} mm/day, ETc: {etc:.2f} mm/day")
        return etc
        
    def get_historical_weather(
        self,
        latitude: float,
        longitude: float,
        start_date: datetime,
        end_date: datetime,
    ) -> List[WeatherData]:
        """
        Get historical weather data (requires paid subscription).
        
        Args:
            latitude: Latitude
            longitude: Longitude
            start_date: Start date
            end_date: End date
            
        Returns:
            List of historical weather data
        """
        # Placeholder - requires OpenWeatherMap History API subscription
        logger.warning("Historical weather API requires paid subscription")
        return []
