"""
Alembic migration script
Database initialization
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types
    op.execute("CREATE TYPE userrole AS ENUM ('farmer', 'admin', 'agronomist', 'sensor')")
    op.execute("CREATE TYPE subscriptiontier AS ENUM ('free', 'weekly', 'monthly', 'premium')")
    op.execute("CREATE TYPE sensortype AS ENUM ('esp32_cam', 'raspberry_pi', 'mobile_phone')")
    op.execute("CREATE TYPE sensorstatus AS ENUM ('active', 'inactive', 'maintenance')")
    op.execute("CREATE TYPE alertseverity AS ENUM ('low', 'medium', 'high', 'critical')")
    op.execute("CREATE TYPE alertstatus AS ENUM ('pending', 'acknowledged', 'investigating', 'resolved', 'ignored')")
    op.execute("CREATE TYPE diagnosisstatus AS ENUM ('pending', 'processing', 'completed', 'failed')")
    op.execute("CREATE TYPE diseasecategory AS ENUM ('fungal', 'bacterial', 'viral', 'pest', 'nutrient_deficiency', 'environmental', 'healthy')")
    op.execute("CREATE TYPE permitstatus AS ENUM ('pending', 'minted', 'used', 'expired', 'refunded')")
    op.execute("CREATE TYPE paymentstatus AS ENUM ('pending', 'processing', 'completed', 'failed', 'refunded')")
    op.execute("CREATE TYPE paymentmethod AS ENUM ('mpesa', 'card', 'bank_transfer', 'wallet')")
    op.execute("CREATE TYPE optimizationstatus AS ENUM ('pending', 'processing', 'completed', 'failed')")


def downgrade():
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS subscriptiontier")
    op.execute("DROP TYPE IF EXISTS sensortype")
    op.execute("DROP TYPE IF EXISTS sensorstatus")
    op.execute("DROP TYPE IF EXISTS alertseverity")
    op.execute("DROP TYPE IF EXISTS alertstatus")
    op.execute("DROP TYPE IF EXISTS diagnosisstatus")
    op.execute("DROP TYPE IF EXISTS diseasecategory")
    op.execute("DROP TYPE IF EXISTS permitstatus")
    op.execute("DROP TYPE IF EXISTS paymentstatus")
    op.execute("DROP TYPE IF EXISTS paymentmethod")
    op.execute("DROP TYPE IF EXISTS optimizationstatus")
