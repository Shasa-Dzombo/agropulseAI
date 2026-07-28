"""
Base.metadata.create_all() only creates tables/types that don't exist yet -
it never ALTERs existing ones. drone_flights was created before real
OpenWeatherMap conditions (app.services.weather_service) were added. This
adds the 8 advisory weather_* columns.

Usage:
    python scripts/patch_drone_weather.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db_config import production_engine

STATEMENTS = [
    "ALTER TABLE drone_flights ADD COLUMN IF NOT EXISTS weather_temperature_c FLOAT",
    "ALTER TABLE drone_flights ADD COLUMN IF NOT EXISTS weather_humidity_pct INTEGER",
    "ALTER TABLE drone_flights ADD COLUMN IF NOT EXISTS weather_wind_speed_ms FLOAT",
    "ALTER TABLE drone_flights ADD COLUMN IF NOT EXISTS weather_conditions VARCHAR(100)",
    "ALTER TABLE drone_flights ADD COLUMN IF NOT EXISTS weather_flight_suitable BOOLEAN",
    "ALTER TABLE drone_flights ADD COLUMN IF NOT EXISTS weather_warnings JSON",
    "ALTER TABLE drone_flights ADD COLUMN IF NOT EXISTS weather_disease_pressure VARCHAR(20)",
    "ALTER TABLE drone_flights ADD COLUMN IF NOT EXISTS weather_checked_at TIMESTAMPTZ",
]


def main():
    with production_engine.begin() as conn:
        for stmt in STATEMENTS:
            print(f"Running: {stmt}")
            conn.execute(text(stmt))
    print("Done.")


if __name__ == "__main__":
    main()
