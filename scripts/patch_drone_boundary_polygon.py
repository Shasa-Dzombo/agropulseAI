"""
Adds boundary_polygon to drone_flights - see app/models/drone.py's
DroneFlight.boundary_polygon for what it stores and why it's separate from
mission_plan.

Usage:
    python scripts/patch_drone_boundary_polygon.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db_config import production_engine

STATEMENTS = [
    "ALTER TABLE drone_flights ADD COLUMN IF NOT EXISTS boundary_polygon JSON",
]


def main():
    with production_engine.begin() as conn:
        for stmt in STATEMENTS:
            print(f"Running: {stmt.strip()[:80]}...")
            conn.execute(text(stmt))
    print("Done.")


if __name__ == "__main__":
    main()
