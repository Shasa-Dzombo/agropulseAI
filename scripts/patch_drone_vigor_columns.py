"""
Base.metadata.create_all() only creates tables/types that don't exist yet -
it never ALTERs existing ones. drone_image_analyses was created before
canopy vigor/coverage screening (app.services.canopy_vigor_assessment) was
added. This adds the 4 new columns.

Usage:
    python scripts/patch_drone_vigor_columns.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db_config import production_engine

STATEMENTS = [
    "ALTER TABLE drone_image_analyses ADD COLUMN IF NOT EXISTS canopy_coverage_pct FLOAT",
    "ALTER TABLE drone_image_analyses ADD COLUMN IF NOT EXISTS vigor_level VARCHAR(20)",
    "ALTER TABLE drone_image_analyses ADD COLUMN IF NOT EXISTS vigor_indicators JSON",
    "ALTER TABLE drone_image_analyses ADD COLUMN IF NOT EXISTS low_vigor_regions JSON",
    "ALTER TABLE drone_image_analyses ADD COLUMN IF NOT EXISTS total_canopy_area_m2 FLOAT",
    "ALTER TABLE drone_image_analyses ADD COLUMN IF NOT EXISTS overlay_url VARCHAR(500)",
]


def main():
    with production_engine.begin() as conn:
        for stmt in STATEMENTS:
            print(f"Running: {stmt}")
            conn.execute(text(stmt))
    print("Done.")


if __name__ == "__main__":
    main()
