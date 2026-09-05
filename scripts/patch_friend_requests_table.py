"""
Creates friend_requests - see app/models/database.py's FriendRequest for the
real schema this mirrors, and app/api/friends.py for the endpoints.

Usage:
    python scripts/patch_friend_requests_table.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db_config import production_engine

STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS friend_requests (
        id SERIAL PRIMARY KEY,
        requester_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        recipient_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        responded_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT uq_friend_request_pair UNIQUE (requester_id, recipient_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_friend_request_recipient ON friend_requests (recipient_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_friend_request_requester ON friend_requests (requester_id, status)",
]


def main():
    with production_engine.begin() as conn:
        for stmt in STATEMENTS:
            print(f"Running: {stmt.strip()[:80]}...")
            conn.execute(text(stmt))
    print("Done.")


if __name__ == "__main__":
    main()
