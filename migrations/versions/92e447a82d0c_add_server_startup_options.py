"""Add configurable server startup options.

Revision ID: 92e447a82d0c
Revises: ea225d31fff6
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "92e447a82d0c"
down_revision: Union[str, Sequence[str], None] = "ea225d31fff6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "servers",
        sa.Column("jar_name", sa.String(255), nullable=False, server_default="paper.jar"),
    )
    op.add_column(
        "servers",
        sa.Column("java_args", sa.String(1000), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("servers", "java_args")
    op.drop_column("servers", "jar_name")
