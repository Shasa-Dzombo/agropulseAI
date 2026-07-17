"""
Creates every table defined in app.models.database (the separate, richer
model stack seed_database.py and the "advanced_features" side of the app
use - referred to elsewhere in this project's notes as "Universe B", distinct
from app.database's Base used by the actually-registered API routers).

Requires the PostGIS extension to be enabled first (Universe B's User/Farm/
Field/IoTDevice models use geoalchemy2 Geography/Geometry columns):
    psql -U postgres -h localhost -d agropulse -c "CREATE EXTENSION IF NOT EXISTS postgis;"

Usage:
    python scripts/create_universe_b_tables.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import Base
from app.db_config import production_engine


def main():
    Base.metadata.create_all(production_engine)
    print(f"Tables created: {sorted(Base.metadata.tables.keys())}")


if __name__ == "__main__":
    main()
