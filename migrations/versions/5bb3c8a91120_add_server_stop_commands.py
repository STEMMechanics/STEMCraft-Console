"""Add configurable server pre-stop commands."""

from alembic import op
import sqlalchemy as sa


revision = "5bb3c8a91120"
down_revision = "19ca4ad6f805"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "servers",
        sa.Column("stop_commands", sa.Text(), nullable=False, server_default=""),
    )


def downgrade():
    op.drop_column("servers", "stop_commands")
