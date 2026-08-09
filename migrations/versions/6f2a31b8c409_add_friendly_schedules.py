"""Add friendly schedule fields.

Revision ID: 6f2a31b8c409
Revises: b71f86ca240e
"""
from alembic import op
import sqlalchemy as sa

revision = "6f2a31b8c409"
down_revision = "b71f86ca240e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scheduled_tasks", sa.Column("frequency", sa.String(20), nullable=True))
    op.add_column("scheduled_tasks", sa.Column("run_hour", sa.Integer(), nullable=True))
    op.add_column("scheduled_tasks", sa.Column("run_weekday", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("scheduled_tasks", "run_weekday")
    op.drop_column("scheduled_tasks", "run_hour")
    op.drop_column("scheduled_tasks", "frequency")
