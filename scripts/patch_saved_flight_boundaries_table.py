"""
Creates saved_flight_boundaries - see app/models/database.py's
SavedFlightBoundary for the real schema this mirrors, and
app/api/farm_inputs.py for the endpoints.

Usage:
    python scripts/patch_saved_flight_boundaries_table.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db_config import production_engine

STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS saved_flight_boundaries (
        id SERIAL PRIMARY KEY,
        farm_id INTEGER NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
        created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        name VARCHAR(200) NOT NULL,
        polygon JSON NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        deleted_at TIMESTAMPTZ,
        is_deleted BOOLEAN NOT NULL DEFAULT false
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_saved_boundary_farm ON saved_flight_boundaries (farm_id)",
]


def main():
    with production_engine.begin() as conn:
        for stmt in STATEMENTS:
            print(f"Running: {stmt.strip()[:80]}...")
            conn.execute(text(stmt))
    print("Done.")


if __name__ == "__main__":
    main()
