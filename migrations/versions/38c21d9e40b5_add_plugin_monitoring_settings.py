"""Add per-server plugin update source preferences."""
from alembic import op
import sqlalchemy as sa

revision = '38c21d9e40b5'
down_revision = '27b10c8d39a4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('plugin_monitoring_settings',
        sa.Column('server_id', sa.Integer(), sa.ForeignKey('servers.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('plugin_name', sa.String(200), primary_key=True),
        sa.Column('mode', sa.String(20), nullable=False),
        sa.Column('provider', sa.String(30), nullable=False),
        sa.Column('project', sa.String(150), nullable=False))


def downgrade():
    op.drop_table('plugin_monitoring_settings')
