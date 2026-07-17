"""
Base.metadata.create_all() only creates tables/types that don't exist yet -
it never ALTERs existing ones. iot_devices was created before
battery_level/sampling_interval_seconds/installation_date were added to the
IoTDevice model (missing columns), and the devicetype enum type was created
before MOISTURE_SENSOR was added (missing enum value). This adds both.

Usage:
    python scripts/patch_iot_devices_table.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db_config import production_engine

STATEMENTS = [
    "ALTER TABLE iot_devices ADD COLUMN IF NOT EXISTS battery_level FLOAT",
    "ALTER TABLE iot_devices ADD COLUMN IF NOT EXISTS sampling_interval_seconds INTEGER",
    "ALTER TABLE iot_devices ADD COLUMN IF NOT EXISTS installation_date DATE",
    "ALTER TYPE devicetype ADD VALUE IF NOT EXISTS 'MOISTURE_SENSOR'",
]


def main():
    with production_engine.begin() as conn:
        for stmt in STATEMENTS:
            print(f"Running: {stmt}")
            conn.execute(text(stmt))
    print("Done.")


if __name__ == "__main__":
    main()
