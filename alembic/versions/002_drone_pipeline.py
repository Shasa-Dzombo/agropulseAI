"""
Alembic migration script
Drone orchard survey pipeline - enum types

Matches 001_initial.py's convention: this migration only creates the
Postgres enum types used by the drone models. Actual tables are created via
Base.metadata.create_all(), same as every other table in this schema (see
main.py's lifespan and the other model files) - Alembic here isn't yet
wired to create tables directly (see 001_initial.py).
"""
from alembic import op

# revision identifiers
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE TYPE dronebackendtype AS ENUM ('simulated', 'mavlink')")
    op.execute("CREATE TYPE droneflightstatus AS ENUM ('planned', 'in_progress', 'completed', 'aborted', 'failed')")


def downgrade():
    op.execute("DROP TYPE IF EXISTS dronebackendtype")
    op.execute("DROP TYPE IF EXISTS droneflightstatus")
