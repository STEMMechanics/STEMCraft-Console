"""Add off-site backup schedule fields.

Revision ID: d14b6a037c92
Revises: a83d19c572e4
"""
from alembic import op
import sqlalchemy as sa

revision = "d14b6a037c92"
down_revision = "a83d19c572e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scheduled_tasks", sa.Column("remote_destination", sa.String(500), nullable=True))
    op.add_column("scheduled_tasks", sa.Column("remote_retention_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("scheduled_tasks", "remote_retention_count")
    op.drop_column("scheduled_tasks", "remote_destination")
