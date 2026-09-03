"""
Repoints the drone tables' foreign keys from the dead "Universe A" tables
(app_farms, app_users, app_diagnoses - tracked by Alembic, but unreachable
by any real login since real auth/farms/diagnoses all moved to "Universe B":
app.db_config's sync session + app.models.database's Farm/User/Diagnosis,
same as app/api/farms.py and app/api/diagnoses.py) to the real ones
(farms, users, diagnoses) that app/api/drones.py now targets.

drone_flights had exactly 4 rows before this ran, all leftover test data
from an abandoned MAVLink/simulated-autopilot design (see
app/services/drone_ai_service.py's module docstring - those backends were
removed; every real flight is MANUAL_INGEST now) - farm_id=1/requested_by_id=1
for all four, zero associated drone_images/analyses/telemetry on any of
them. Deleted rather than remapped: there's no real flight history to
preserve, and remapping would just point them at whichever Universe B
farm/user happens to have id=1, which is almost certainly the wrong one.

Usage:
    python scripts/patch_drone_universe_b_fks.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db_config import production_engine

STATEMENTS = [
    "DELETE FROM drone_flights",

    "ALTER TABLE drone_flights DROP CONSTRAINT drone_flights_farm_id_fkey",
    "ALTER TABLE drone_flights ADD CONSTRAINT drone_flights_farm_id_fkey "
    "FOREIGN KEY (farm_id) REFERENCES farms(id)",

    "ALTER TABLE drone_flights DROP CONSTRAINT drone_flights_requested_by_id_fkey",
    "ALTER TABLE drone_flights ADD CONSTRAINT drone_flights_requested_by_id_fkey "
    "FOREIGN KEY (requested_by_id) REFERENCES users(id)",

    "ALTER TABLE drone_images DROP CONSTRAINT drone_images_diagnosis_id_fkey",
    "ALTER TABLE drone_images ADD CONSTRAINT drone_images_diagnosis_id_fkey "
    "FOREIGN KEY (diagnosis_id) REFERENCES diagnoses(id) ON DELETE SET NULL",
]


def main():
    with production_engine.begin() as conn:
        for stmt in STATEMENTS:
            print(f"Running: {stmt}")
            conn.execute(text(stmt))
    print("Done.")


if __name__ == "__main__":
    main()
