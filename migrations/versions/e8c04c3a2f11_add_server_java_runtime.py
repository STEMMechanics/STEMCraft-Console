"""Add per-server Java runtime selection.

Revision ID: e8c04c3a2f11
Revises: d14b6a037c92
"""
from alembic import op
import sqlalchemy as sa


revision = "e8c04c3a2f11"
down_revision = "d14b6a037c92"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "servers",
        sa.Column("java_path", sa.String(500), nullable=False, server_default="java"),
    )


def downgrade() -> None:
    op.drop_column("servers", "java_path")
