"""
Adds Chama.mpesa_paybill_number - a reference number members pay into
manually via their own M-Pesa app. Not a real payment integration; see the
column's comment in app/models/database.py for why.

Usage:
    python scripts/patch_chama_paybill.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db_config import production_engine

STATEMENTS = [
    "ALTER TABLE chamas ADD COLUMN IF NOT EXISTS mpesa_paybill_number VARCHAR(20)",
]


def main():
    with production_engine.begin() as conn:
        for stmt in STATEMENTS:
            print(f"Running: {stmt}")
            conn.execute(text(stmt))
    print("Done.")


if __name__ == "__main__":
    main()
