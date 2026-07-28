"""
Real weather context for the drone survey pipeline, via OpenWeatherMap
(app.integrations.weather.openweather.OpenWeatherMapClient - real HTTP calls,
no simulation). Advisory only: nothing here ever blocks a mission, it only
enriches a DroneFlight with real conditions at the time it flew.

OPENWEATHER_API_KEY is optional - unset means these features skip silently
(one log line), same graceful-degradation contract as
app.services.kindwise_disease_service.get_kindwise_client().
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Literal, Optional, Tuple

from app.config import settings
from app.integrations.weather.openweather import OpenWeatherMapClient, WeatherData

logger = logging.getLogger(__name__)

# Agricultural UAVs (DJI Phantom/Mavic class) publish wind-resistance ratings
# well below the general "crop damage" wind threshold OpenWeatherMapClient's
# own get_agricultural_alerts() uses (15 m/s) - ~10 m/s (~36 km/h) is a
# commonly used conservative operational ceiling for this class of aircraft.
_MAX_SAFE_WIND_MS = 10.0
_CAUTION_WIND_MS = 7.0
_MIN_SAFE_TEMPERATURE_C = 0.0  # icing / battery risk below freezing
_MAX_SAFE_TEMPERATURE_C = 40.0  # battery thermal risk


@dataclass
class FlightConditionAssessment:
    suitable: bool
    warnings: List[str] = field(default_factory=list)


@dataclass
class DiseasePressureAssessment:
    risk_level: Literal["low", "moderate", "high"]
    indicators: List[str] = field(default_factory=list)


def get_openweather_client() -> Optional[OpenWeatherMapClient]:
    """Returns None (and logs) if OPENWEATHER_API_KEY isn't configured."""
    if not settings.OPENWEATHER_API_KEY:
        logger.warning("OPENWEATHER_API_KEY not configured - weather context disabled for this mission")
        return None
    return OpenWeatherMapClient(api_key=settings.OPENWEATHER_API_KEY)


async def fetch_weather_snapshot(client: OpenWeatherMapClient, latitude: float, longitude: float) -> Optional[WeatherData]:
    """Blocking HTTP call off the event loop. get_current_weather() already
    catches its own request/parse failures and returns None - this never
    raises."""
    try:
        return await asyncio.to_thread(client.get_current_weather, latitude, longitude)
    except Exception:
        logger.exception("OpenWeatherMap get_current_weather call raised unexpectedly")
        return None


async def geocode_location(client: OpenWeatherMapClient, location_name: str) -> Optional[Tuple[float, float]]:
    """Blocking HTTP call off the event loop. client.geocode() already
    catches its own request/parse failures and returns None - this never
    raises. Used as a fallback for GET /drones/weather when a farm has no
    latitude/longitude set but does have a real place name in Farm.location."""
    try:
        return await asyncio.to_thread(client.geocode, location_name)
    except Exception:
        logger.exception("OpenWeatherMap geocode call raised unexpectedly")
        return None


def assess_flight_conditions(weather: WeatherData) -> FlightConditionAssessment:
    """Real threshold logic over real current-conditions data - not a
    trained model, honestly labeled the same way as
    app.services.plant_stress_assessment.assess_plant_stress()."""
    warnings: List[str] = []
    suitable = True

    if weather.wind_speed > _MAX_SAFE_WIND_MS:
        suitable = False
        warnings.append(
            f"Wind speed {weather.wind_speed:.1f} m/s exceeds the {_MAX_SAFE_WIND_MS:.0f} m/s "
            "operational ceiling for small agricultural UAVs"
        )
    elif weather.wind_speed > _CAUTION_WIND_MS:
        warnings.append(f"Wind speed {weather.wind_speed:.1f} m/s is approaching the safe ceiling - fly with caution")

    if weather.rainfall > 0:
        suitable = False
        warnings.append(f"Active precipitation ({weather.rainfall:.1f} mm/h) - most consumer/prosumer drones are not rated for flight in rain")

    if weather.temperature < _MIN_SAFE_TEMPERATURE_C:
        suitable = False
        warnings.append(f"Temperature {weather.temperature:.1f}°C is below freezing - icing and battery risk")
    elif weather.temperature > _MAX_SAFE_TEMPERATURE_C:
        suitable = False
        warnings.append(f"Temperature {weather.temperature:.1f}°C exceeds {_MAX_SAFE_TEMPERATURE_C:.0f}°C - battery thermal risk")

    return FlightConditionAssessment(suitable=suitable, warnings=warnings)


def assess_disease_pressure(weather: WeatherData) -> DiseasePressureAssessment:
    """Humidity/temperature-driven fungal-risk proxy (a leaf-wetness-duration
    heuristic, not a trained model or a diagnosis) - advisory agronomic
    context to sit next to, not replace, Kindwise's real per-photo disease
    identification (app.services.kindwise_disease_service)."""
    indicators: List[str] = []

    high_humidity = weather.humidity >= 80
    moderate_temp = 15.0 <= weather.temperature <= 30.0

    if high_humidity and moderate_temp:
        risk_level = "high"
        indicators.append(
            f"High humidity ({weather.humidity}%) with moderate temperature ({weather.temperature:.1f}°C) "
            "favors extended leaf wetness and fungal spore germination"
        )
    elif weather.humidity >= 65:
        risk_level = "moderate"
        indicators.append(f"Elevated humidity ({weather.humidity}%) - monitor for early fungal disease symptoms")
    else:
        risk_level = "low"

    if weather.rainfall > 0 and weather.humidity >= 65:
        if risk_level == "low":
            risk_level = "moderate"
        indicators.append("Recent rainfall combined with elevated humidity extends leaf wetness duration")

    return DiseasePressureAssessment(risk_level=risk_level, indicators=indicators)
