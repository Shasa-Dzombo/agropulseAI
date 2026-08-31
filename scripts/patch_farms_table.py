"""
Base.metadata.create_all() only creates tables/types that don't exist yet -
it never ALTERs existing ones. The real `farms` table (Universe B,
app/models/database.py) is missing several columns that app/api/farms.py's
create/update/list/detail endpoints and app/repositories/farm.py already
assume exist: primary_crop, farm_type, has_irrigation, verification_status,
cultivated_area_acres. Without these, POST /farms 500s outright (the Farm()
constructor rejects unknown kwargs) and several other endpoints silently
drop data. This adds them.

Usage:
    python scripts/patch_farms_table.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db_config import production_engine

STATEMENTS = [
    "ALTER TABLE farms ADD COLUMN IF NOT EXISTS primary_crop VARCHAR(100)",
    "ALTER TABLE farms ADD COLUMN IF NOT EXISTS farm_type VARCHAR(50)",
    "ALTER TABLE farms ADD COLUMN IF NOT EXISTS has_irrigation BOOLEAN DEFAULT FALSE",
    "ALTER TABLE farms ADD COLUMN IF NOT EXISTS verification_status VARCHAR(50) NOT NULL DEFAULT 'pending'",
    "ALTER TABLE farms ADD COLUMN IF NOT EXISTS cultivated_area_acres FLOAT",
]


def main():
    with production_engine.begin() as conn:
        for stmt in STATEMENTS:
            print(f"Running: {stmt}")
            conn.execute(text(stmt))
    print("Done.")


if __name__ == "__main__":
    main()
