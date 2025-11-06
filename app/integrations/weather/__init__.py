"""
Weather API Integration Module
==============================

Integrations with multiple weather data providers for comprehensive
agricultural weather intelligence.

Providers:
- OpenWeatherMap: Global coverage, hourly/daily forecasts
- AccuWeather: High accuracy, severe weather alerts
- Tomorrow.io (ClimaCell): Hyperlocal forecasts, field-level data
- African weather services: ICPAC, AGRHYMET, local met departments
"""

from .openweather import OpenWeatherMapClient
from .accuweather import AccuWeatherClient
from .tomorrow_io import TomorrowIOClient
from .african_services import (
    ICPACClient,
    AGRHYMETClient,
    LocalMeteorologicalClient,
)
from .weather_aggregator import WeatherAggregator
from .historical_data import HistoricalWeatherService
from .alerts import WeatherAlertService

__all__ = [
    'OpenWeatherMapClient',
    'AccuWeatherClient',
    'TomorrowIOClient',
    'ICPACClient',
    'AGRHYMETClient',
    'LocalMeteorologicalClient',
    'WeatherAggregator',
    'HistoricalWeatherService',
    'WeatherAlertService',
]
