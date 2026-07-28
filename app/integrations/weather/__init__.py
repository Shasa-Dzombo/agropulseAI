"""
Weather API Integration Module
==============================

Integrations with weather data providers for agricultural weather
intelligence.

Only OpenWeatherMapClient is real. This package previously imported five
sibling modules (accuweather, tomorrow_io, african_services,
weather_aggregator, historical_data, alerts) that don't exist anywhere in
this directory - that made `import app.integrations.weather` fail outright.
Add real modules back here only once they're actually built.
"""

from .openweather import AgriculturalAlert, ForecastData, OpenWeatherMapClient, WeatherData

__all__ = [
    'OpenWeatherMapClient',
    'WeatherData',
    'ForecastData',
    'AgriculturalAlert',
]
