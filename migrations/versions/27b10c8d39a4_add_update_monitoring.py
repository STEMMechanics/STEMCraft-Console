"""Add shared update cache, checks, notifications and scheduler lease.

Revision ID: 27b10c8d39a4
Revises: 5bb3c8a91120
"""
from alembic import op
import sqlalchemy as sa

revision = '27b10c8d39a4'
down_revision = '5bb3c8a91120'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('upstream_update_cache',
        sa.Column('key', sa.String(200), primary_key=True),
        sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('checked_at', sa.DateTime(), nullable=False),
        sa.Column('error', sa.String(255)))
    op.create_table('server_update_checks',
        sa.Column('server_id', sa.Integer(), sa.ForeignKey('servers.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('component', sa.String(255), primary_key=True),
        sa.Column('payload', sa.Text(), nullable=False))
    op.create_table('update_notifications',
        sa.Column('server_id', sa.Integer(), sa.ForeignKey('servers.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('component', sa.String(200), primary_key=True),
        sa.Column('recipient', sa.String(255), primary_key=True),
        sa.Column('version', sa.String(200), primary_key=True),
        sa.Column('sent_at', sa.DateTime(), nullable=False))
    op.create_table('update_monitor_lease',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('last_scheduled_at', sa.DateTime()))


def downgrade():
    for table in ('update_monitor_lease', 'update_notifications', 'server_update_checks', 'upstream_update_cache'):
        op.drop_table(table)
