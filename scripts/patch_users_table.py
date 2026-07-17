"""
Base.metadata.create_all() only creates tables/types that don't exist yet -
it never ALTERs existing ones. The real `users` table (Universe B,
app/models/database.py) was created before the `username` column was added
to the User model to support app/api/auth.py's register/login flow. This
adds it.

Usage:
    python scripts/patch_users_table.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db_config import production_engine

STATEMENTS = [
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(50) UNIQUE",
]


def main():
    with production_engine.begin() as conn:
        for stmt in STATEMENTS:
            print(f"Running: {stmt}")
            conn.execute(text(stmt))
    print("Done.")


if __name__ == "__main__":
    main()
