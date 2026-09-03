"""
Adds user_chama_association.status ('pending' | 'active' | leftover rows
default to 'active', since the only real rows in this table before this
migration were already-approved members - see app/api/chamas.py's join_chama,
now a request that a chairperson/treasurer/secretary approves instead of
instant membership.

Usage:
    python scripts/patch_chama_membership_status.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db_config import production_engine

STATEMENTS = [
    "ALTER TABLE user_chama_association ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'active'",
]


def main():
    with production_engine.begin() as conn:
        for stmt in STATEMENTS:
            print(f"Running: {stmt}")
            conn.execute(text(stmt))
    print("Done.")


if __name__ == "__main__":
    main()
