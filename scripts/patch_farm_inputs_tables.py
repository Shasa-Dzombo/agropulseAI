"""
Creates farm_input_records and farm_yield_records - see
app/models/database.py's FarmInputRecord/FarmYieldRecord for the real
schema this mirrors, and app/api/farm_inputs.py for the endpoints.

Usage:
    python scripts/patch_farm_inputs_tables.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db_config import production_engine

STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS farm_input_records (
        id SERIAL PRIMARY KEY,
        farm_id INTEGER NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
        created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        entry_type VARCHAR(20) NOT NULL,
        category VARCHAR(20) NOT NULL,
        item_name VARCHAR(200) NOT NULL,
        quantity FLOAT,
        unit VARCHAR(50),
        cost_ksh DECIMAL(10, 2),
        notes TEXT,
        entry_date DATE NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        deleted_at TIMESTAMPTZ,
        is_deleted BOOLEAN NOT NULL DEFAULT false
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_farm_input_farm_date ON farm_input_records (farm_id, entry_date)",
    "CREATE INDEX IF NOT EXISTS idx_farm_input_entry_type ON farm_input_records (entry_type)",
    """
    CREATE TABLE IF NOT EXISTS farm_yield_records (
        id SERIAL PRIMARY KEY,
        farm_id INTEGER NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
        created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        crop VARCHAR(100) NOT NULL,
        season_label VARCHAR(50) NOT NULL,
        planted_date DATE,
        expected_yield_kg FLOAT,
        actual_yield_kg FLOAT,
        harvest_date DATE,
        notes TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        deleted_at TIMESTAMPTZ,
        is_deleted BOOLEAN NOT NULL DEFAULT false
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_farm_yield_farm_season ON farm_yield_records (farm_id, season_label)",
]


def main():
    with production_engine.begin() as conn:
        for stmt in STATEMENTS:
            print(f"Running: {stmt.strip()[:80]}...")
            conn.execute(text(stmt))
    print("Done.")


if __name__ == "__main__":
    main()
