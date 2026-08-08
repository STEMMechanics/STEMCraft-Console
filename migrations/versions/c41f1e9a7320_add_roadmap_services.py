"""Add process backend, schedules, task audit and historical metrics.

Revision ID: c41f1e9a7320
Revises: 92e447a82d0c
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c41f1e9a7320"
down_revision: Union[str, Sequence[str], None] = "92e447a82d0c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("servers", sa.Column("process_backend", sa.String(20), nullable=False, server_default="subprocess"))
    op.create_table(
        "scheduled_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column("task_type", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("command", sa.String(500), nullable=True),
        sa.Column("interval_minutes", sa.Integer(), nullable=False),
        sa.Column("retention_count", sa.Integer(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["server_id"], ["servers.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_scheduled_tasks_server_id", "scheduled_tasks", ["server_id"])
    op.create_index("ix_scheduled_tasks_next_run_at", "scheduled_tasks", ["next_run_at"])
    op.create_table(
        "task_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column("task_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("detail", sa.String(1000), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["scheduled_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["server_id"], ["servers.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_task_runs_task_id", "task_runs", ["task_id"])
    op.create_index("ix_task_runs_server_id", "task_runs", ["server_id"])
    op.create_table(
        "server_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.Column("running", sa.Boolean(), nullable=False),
        sa.Column("cpu_percent", sa.Integer(), nullable=False),
        sa.Column("memory_bytes", sa.Integer(), nullable=False),
        sa.Column("player_count", sa.Integer(), nullable=True),
        sa.Column("uptime_seconds", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["server_id"], ["servers.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_server_metrics_server_id", "server_metrics", ["server_id"])
    op.create_index("ix_server_metrics_recorded_at", "server_metrics", ["recorded_at"])


def downgrade() -> None:
    op.drop_table("server_metrics")
    op.drop_table("task_runs")
    op.drop_table("scheduled_tasks")
    op.drop_column("servers", "process_backend")
