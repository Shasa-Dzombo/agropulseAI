"""
Base.metadata.create_all() only creates tables/types that don't exist yet -
it never ALTERs existing ones. drone_flights and the dronebackendtype enum
were created before manual DJI ground-ingestion support (no waypoint plan,
no FlightBackend - app.services.drone_ai_service.start_manual_flight) was
added. This adds the new enum value and relaxes the two columns that don't
apply to a manually-flown mission.

The ADD VALUE statement must run in its own standalone transaction - Postgres
does not allow a newly added enum value to be used within the same
transaction that added it, so it's kept separate from the ALTER TABLE
statements below (same gotcha flagged when DeviceType.MOISTURE_SENSOR was
added earlier).

Usage:
    python scripts/patch_drone_manual_ingest.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db_config import production_engine

ADD_ENUM_VALUE = "ALTER TYPE dronebackendtype ADD VALUE IF NOT EXISTS 'manual_ingest'"

STATEMENTS = [
    "ALTER TABLE drone_flights ALTER COLUMN target_altitude_m DROP NOT NULL",
    "ALTER TABLE drone_flights ALTER COLUMN mission_plan DROP NOT NULL",
]


def main():
    with production_engine.begin() as conn:
        print(f"Running: {ADD_ENUM_VALUE}")
        conn.execute(text(ADD_ENUM_VALUE))

    with production_engine.begin() as conn:
        for stmt in STATEMENTS:
            print(f"Running: {stmt}")
            conn.execute(text(stmt))
    print("Done.")


if __name__ == "__main__":
    main()
