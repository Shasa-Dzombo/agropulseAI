"""
One-off table creation for local development. main.py's lifespan has
Base.metadata.create_all commented out (Alembic isn't fully wired to create
tables yet - see alembic/versions/001_initial.py, which only creates enum
types). This script creates every table the currently-registered API routers
actually use (Universe A: app.database's Base) against your real DATABASE_URL.

Usage:
    python scripts/create_drone_tables.py
"""

import asyncio
import sys

sys.path.insert(0, ".")

from app.database import Base, engine
import app.models.user  # noqa: F401
import app.models.sensor  # noqa: F401
import app.models.diagnosis  # noqa: F401
import app.models.permit  # noqa: F401
import app.models.drone  # noqa: F401


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print(f"Tables created: {sorted(Base.metadata.tables.keys())}")


if __name__ == "__main__":
    asyncio.run(main())
