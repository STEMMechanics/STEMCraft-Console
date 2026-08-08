"""Initial schema

Revision ID: 786f21b7582d
Revises:
Create Date: 2026-08-08 09:28:55.556269

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '786f21b7582d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_table(
        "servers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("directory", sa.String(500), nullable=False, unique=True),
        sa.Column("service_name", sa.String(150), nullable=False, unique=True),
        sa.Column("minecraft_version", sa.String(40), nullable=True),
        sa.Column("paper_build", sa.String(40), nullable=True),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("memory", sa.String(20), nullable=False),
        sa.Column("plugins_dirty", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "user_server_access",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["server_id"], ["servers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "server_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("user_server_access")
    op.drop_table("servers")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
