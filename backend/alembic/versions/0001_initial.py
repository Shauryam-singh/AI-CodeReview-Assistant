"""initial tables: repos, pull_requests, jobs, findings, reviews

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "repos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("html_url", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_repos"),
    )
    op.create_index("ix_repos_full_name", "repos", ["full_name"], unique=True)

    op.create_table(
        "pull_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repo_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("state", sa.String(length=32), nullable=True),
        sa.Column("html_url", sa.String(length=512), nullable=True),
        sa.Column("head_sha", sa.String(length=64), nullable=True),
        sa.Column("base_sha", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["repo_id"], ["repos.id"], name="fk_pull_requests_repo_id_repos",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_pull_requests"),
        sa.UniqueConstraint("repo_id", "number", name="uq_pull_requests_repo_id_number"),
    )
    op.create_index("ix_pull_requests_repo_id", "pull_requests", ["repo_id"])

    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("arq_job_id", sa.String(length=64), nullable=True),
        sa.Column("repo_id", sa.Integer(), nullable=True),
        sa.Column("pull_request_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="queued", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("enqueued_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["repo_id"], ["repos.id"], name="fk_jobs_repo_id_repos",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["pull_request_id"], ["pull_requests.id"],
            name="fk_jobs_pull_request_id_pull_requests", ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_jobs"),
    )
    op.create_index("ix_jobs_arq_job_id", "jobs", ["arq_job_id"], unique=True)
    op.create_index("ix_jobs_repo_id", "jobs", ["repo_id"])
    op.create_index("ix_jobs_pull_request_id", "jobs", ["pull_request_id"])

    op.create_table(
        "findings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("pull_request_id", sa.Integer(), nullable=True),
        sa.Column("file", sa.String(length=512), nullable=False),
        sa.Column("line", sa.Integer(), nullable=True),
        sa.Column("severity", sa.String(length=16), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("tool", sa.String(length=64), nullable=True),
        sa.Column("risk", sa.Text(), nullable=True),
        sa.Column("suggestion", sa.Text(), nullable=True),
        sa.Column("code_snippet", sa.Text(), nullable=True),
        sa.Column("inlined", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name="fk_findings_job_id_jobs",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["pull_request_id"], ["pull_requests.id"],
            name="fk_findings_pull_request_id_pull_requests", ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_findings"),
    )
    op.create_index("ix_findings_job_id", "findings", ["job_id"])
    op.create_index("ix_findings_pull_request_id", "findings", ["pull_request_id"])
    op.create_index("ix_findings_file", "findings", ["file"])

    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pull_request_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("github_id", sa.BigInteger(), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("inline_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["pull_request_id"], ["pull_requests.id"],
            name="fk_reviews_pull_request_id_pull_requests", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name="fk_reviews_job_id_jobs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_reviews"),
    )
    op.create_index("ix_reviews_pull_request_id", "reviews", ["pull_request_id"])
    op.create_index("ix_reviews_job_id", "reviews", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_reviews_job_id", table_name="reviews")
    op.drop_index("ix_reviews_pull_request_id", table_name="reviews")
    op.drop_table("reviews")

    op.drop_index("ix_findings_file", table_name="findings")
    op.drop_index("ix_findings_pull_request_id", table_name="findings")
    op.drop_index("ix_findings_job_id", table_name="findings")
    op.drop_table("findings")

    op.drop_index("ix_jobs_pull_request_id", table_name="jobs")
    op.drop_index("ix_jobs_repo_id", table_name="jobs")
    op.drop_index("ix_jobs_arq_job_id", table_name="jobs")
    op.drop_table("jobs")

    op.drop_index("ix_pull_requests_repo_id", table_name="pull_requests")
    op.drop_table("pull_requests")

    op.drop_index("ix_repos_full_name", table_name="repos")
    op.drop_table("repos")
