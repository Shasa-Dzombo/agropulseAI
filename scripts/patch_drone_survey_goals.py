"""
Adds survey_goals/survey_notes to drone_flights - see
app/models/drone.py's DroneFlight for the real schema this mirrors.

Usage:
    python scripts/patch_drone_survey_goals.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db_config import production_engine

STATEMENTS = [
    "ALTER TABLE drone_flights ADD COLUMN IF NOT EXISTS survey_goals JSON",
    "ALTER TABLE drone_flights ADD COLUMN IF NOT EXISTS survey_notes TEXT",
]


def main():
    with production_engine.begin() as conn:
        for stmt in STATEMENTS:
            print(f"Running: {stmt}")
            conn.execute(text(stmt))
    print("Done.")


if __name__ == "__main__":
    main()
