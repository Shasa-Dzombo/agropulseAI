"""
Exercises app.services.weather_service's threshold logic directly against
hand-built WeatherData - no DB, no real OpenWeatherMap call.
"""

from datetime import datetime

from app.integrations.weather.openweather import WeatherData
from app.services.weather_service import assess_disease_pressure, assess_flight_conditions


def _weather(**overrides) -> WeatherData:
    defaults = dict(
        timestamp=datetime(2026, 7, 22, 12, 0, 0),
        temperature=22.0,
        feels_like=22.0,
        humidity=50,
        pressure=1013,
        wind_speed=3.0,
        wind_direction=180,
        cloudiness=10,
        rainfall=0.0,
        description="clear sky",
        icon="01d",
        location="Test Farm",
        latitude=-1.0,
        longitude=36.0,
    )
    defaults.update(overrides)
    return WeatherData(**defaults)


def test_calm_dry_conditions_are_suitable_with_no_warnings():
    result = assess_flight_conditions(_weather(wind_speed=3.0, rainfall=0.0))

    assert result.suitable is True
    assert result.warnings == []


def test_moderate_wind_is_suitable_but_flags_a_caution_warning():
    result = assess_flight_conditions(_weather(wind_speed=8.0))

    assert result.suitable is True
    assert any("caution" in w.lower() for w in result.warnings)


def test_high_wind_is_unsuitable():
    result = assess_flight_conditions(_weather(wind_speed=12.0))

    assert result.suitable is False
    assert any("wind" in w.lower() for w in result.warnings)


def test_active_rainfall_is_unsuitable():
    result = assess_flight_conditions(_weather(wind_speed=2.0, rainfall=1.5))

    assert result.suitable is False
    assert any("precipitation" in w.lower() or "rain" in w.lower() for w in result.warnings)


def test_high_humidity_and_moderate_temperature_produce_high_disease_pressure():
    result = assess_disease_pressure(_weather(humidity=85, temperature=22.0))

    assert result.risk_level == "high"
    assert any("humidity" in i.lower() for i in result.indicators)


def test_dry_hot_conditions_produce_low_disease_pressure():
    result = assess_disease_pressure(_weather(humidity=30, temperature=35.0))

    assert result.risk_level == "low"
    assert result.indicators == []
