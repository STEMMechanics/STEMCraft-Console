"""Add per-task schedule timezones.

Revision ID: 19ca4ad6f805
Revises: e8c04c3a2f11
"""
from alembic import op
import sqlalchemy as sa


revision = "19ca4ad6f805"
down_revision = "e8c04c3a2f11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scheduled_tasks", sa.Column("schedule_timezone", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("scheduled_tasks", "schedule_timezone")
