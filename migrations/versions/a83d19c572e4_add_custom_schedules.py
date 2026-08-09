"""Add custom schedules.

Revision ID: a83d19c572e4
Revises: 6f2a31b8c409
"""
from alembic import op
import sqlalchemy as sa

revision = "a83d19c572e4"
down_revision = "6f2a31b8c409"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scheduled_tasks", sa.Column("cron_expression", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("scheduled_tasks", "cron_expression")
