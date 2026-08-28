"""resume intelligence: versioning + analysis (Sprint 2)

Revision ID: 0002_resume_intelligence
Revises: 0001_initial_schema
Create Date: 2026-08-05

Additive only: new nullable/defaulted columns on `resumes`, one new table
`resume_analyses`. No existing column is dropped, renamed, or narrowed, so
this is safe to run against a database already holding Sprint 1 data.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.db.base import GUID

revision: str = "0002_resume_intelligence"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("resumes", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("resumes", sa.Column("parent_resume_id", GUID(), sa.ForeignKey("resumes.id"), nullable=True))
    op.add_column("resumes", sa.Column("source_file_path", sa.String(1000), nullable=True))

    # op.create_table() auto-creates Postgres ENUM types as a side effect of
    # the CREATE TABLE it emits, but a bare add_column() on an *existing*
    # table does not — it only references the type by name. The type must
    # be created explicitly first or this fails with
    # "type parsestatus does not exist" against a real Postgres database
    # (this was caught by actually running the migration, not by inspection).
    parse_status_enum = sa.Enum("pending", "parsed", "failed", name="parsestatus")
    parse_status_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "resumes",
        sa.Column(
            "parse_status",
            parse_status_enum,
            nullable=False,
            server_default="parsed",  # existing Sprint 1 resumes were created via structured JSON, already "parsed"
        ),
    )

    op.create_table(
        "resume_analyses",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resume_id", GUID(), sa.ForeignKey("resumes.id"), nullable=False),
        sa.Column("target_job_id", GUID(), sa.ForeignKey("jobs.id"), nullable=True),
        sa.Column("ats_score", sa.Integer(), nullable=False),
        sa.Column("extracted_skills", sa.JSON(), nullable=False),
        sa.Column("missing_skills_by_role", sa.JSON(), nullable=True),
        sa.Column("strengths", sa.JSON(), nullable=False),
        sa.Column("weaknesses", sa.JSON(), nullable=False),
        sa.Column("raw_model_output_ref", sa.Text(), nullable=True),
    )
    op.create_index("ix_resume_analyses_resume_id", "resume_analyses", ["resume_id"])


def downgrade() -> None:
    op.drop_table("resume_analyses")
    op.drop_column("resumes", "parse_status")

    parse_status_enum = sa.Enum("pending", "parsed", "failed", name="parsestatus")
    parse_status_enum.drop(op.get_bind(), checkfirst=True)

    op.drop_column("resumes", "source_file_path")
    op.drop_column("resumes", "parent_resume_id")
    op.drop_column("resumes", "version")
