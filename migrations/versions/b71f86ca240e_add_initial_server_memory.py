"""Add independently configurable initial server memory.

Revision ID: b71f86ca240e
Revises: 30c8d40e2b91
"""

from alembic import op
import sqlalchemy as sa


revision = "b71f86ca240e"
down_revision = "30c8d40e2b91"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "servers",
        sa.Column("min_memory", sa.String(20), nullable=True),
    )
    op.execute("UPDATE servers SET min_memory = memory")
    with op.batch_alter_table("servers") as batch:
        batch.alter_column(
            "min_memory",
            existing_type=sa.String(20),
            nullable=False,
            server_default="2G",
        )


def downgrade() -> None:
    op.drop_column("servers", "min_memory")
