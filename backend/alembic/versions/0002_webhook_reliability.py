"""webhook reliability: jobs.delivery_id (dedupe) and jobs.attempts

Revision ID: 0002_webhook_reliability
Revises: 0001_initial
Create Date: 2026-10-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_webhook_reliability"
down_revision: str | None = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("delivery_id", sa.String(length=64), nullable=True))
    op.add_column(
        "jobs",
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="1"),
    )
    # Unique but nullable: jobs without a GitHub delivery id stay NULL,
    # which both PostgreSQL and SQLite allow multiple times in a unique index.
    op.create_index("ix_jobs_delivery_id", "jobs", ["delivery_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_jobs_delivery_id", table_name="jobs")
    op.drop_column("jobs", "attempts")
    op.drop_column("jobs", "delivery_id")
