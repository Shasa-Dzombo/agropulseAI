"""
Base.metadata.create_all() only creates tables/types that don't exist yet -
it never ALTERs existing ones. drone_flights/drone_images/drone_image_analyses
and app_diagnoses were created before Kindwise disease detection and plant
stress assessment support was added. This adds the new opt-in flag, the
yield-projection placeholders, the DroneImage -> Diagnosis link, the plant
stress columns, and relaxes app_diagnoses.permit_id to nullable (drone-
triggered diagnoses have no purchased permit, unlike the paid /diagnoses
endpoint flow).

Usage:
    python scripts/patch_drone_disease_detection.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db_config import production_engine

STATEMENTS = [
    "ALTER TABLE drone_flights ADD COLUMN IF NOT EXISTS disease_detection_enabled BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE drone_flights ADD COLUMN IF NOT EXISTS projected_yield_kg_per_hectare FLOAT",
    "ALTER TABLE drone_flights ADD COLUMN IF NOT EXISTS yield_projection_model_version VARCHAR(50)",
    "ALTER TABLE drone_images ADD COLUMN IF NOT EXISTS diagnosis_id INTEGER REFERENCES app_diagnoses(id) ON DELETE SET NULL",
    "ALTER TABLE drone_image_analyses ADD COLUMN IF NOT EXISTS stress_level VARCHAR(20)",
    "ALTER TABLE drone_image_analyses ADD COLUMN IF NOT EXISTS stress_indicators JSON",
    "ALTER TABLE app_diagnoses ALTER COLUMN permit_id DROP NOT NULL",
]


def main():
    with production_engine.begin() as conn:
        for stmt in STATEMENTS:
            print(f"Running: {stmt}")
            conn.execute(text(stmt))
    print("Done.")


if __name__ == "__main__":
    main()
