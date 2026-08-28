"""initial schema (Sprint 1)

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-02

This is the first real Alembic migration for the project. Sprint 1 was
developed against `scripts/init_db.py` (Base.metadata.create_all) rather
than versioned migrations. This revision captures that schema as-is so
production deployments have a real migration history to build on; Sprint 2
additions land in 0002 as a separate, additive-only revision.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.db.base import GUID

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("github_url", sa.String(500), nullable=True),
        sa.Column("linkedin_url", sa.String(500), nullable=True),
        sa.Column("portfolio_url", sa.String(500), nullable=True),
        sa.Column("notice_period_days", sa.Integer(), nullable=True),
        sa.Column(
            "work_authorization",
            sa.Enum("citizen", "permanent_resident", "visa_required", "other", name="workauthorization"),
            nullable=True,
        ),
        sa.Column("preferred_min_salary", sa.Integer(), nullable=True),
        sa.Column("preferred_countries", sa.String(500), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "companies",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("slug", sa.String(255), nullable=False, unique=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("industry", sa.String(255), nullable=True),
        sa.Column("ats_provider", sa.String(50), nullable=True),
        sa.Column("ats_identifier", sa.String(255), nullable=True),
    )
    op.create_index("ix_companies_name", "companies", ["name"])
    op.create_index("ix_companies_slug", "companies", ["slug"])
    op.create_index("ix_companies_ats_provider", "companies", ["ats_provider"])

    op.create_table(
        "resumes",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("content", sa.JSON(), nullable=False),
    )
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"])

    op.create_table(
        "jobs",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("company_id", GUID(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column(
            "ats_provider",
            sa.Enum("greenhouse", "lever", "ashby", "smartrecruiters", "workday", "manual", name="atsprovider"),
            nullable=False,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description_raw", sa.Text(), nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column(
            "work_mode",
            sa.Enum("remote", "hybrid", "onsite", "unknown", name="workmode"),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("department", sa.String(255), nullable=True),
        sa.Column("seniority", sa.String(100), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(10), nullable=True),
        sa.Column("visa_sponsorship", sa.Boolean(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("apply_url", sa.String(1000), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_jobs_company_id", "jobs", ["company_id"])
    op.create_index("ix_jobs_external_id", "jobs", ["external_id"])
    op.create_index("ix_jobs_ats_provider", "jobs", ["ats_provider"])
    op.create_index("ix_jobs_title", "jobs", ["title"])

    op.create_table(
        "job_match_scores",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("job_id", GUID(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("resume_id", GUID(), sa.ForeignKey("resumes.id"), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("missing_skills", sa.JSON(), nullable=False),
        sa.Column("interview_likelihood", sa.String(50), nullable=False),
        sa.Column("difficulty", sa.String(50), nullable=False),
        sa.Column("ats_compatibility", sa.Integer(), nullable=False),
        sa.Column("expected_salary_estimate", sa.String(100), nullable=True),
    )
    op.create_index("ix_job_match_scores_job_id", "job_match_scores", ["job_id"])
    op.create_index("ix_job_match_scores_user_id", "job_match_scores", ["user_id"])

    op.create_table(
        "documents",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("source_resume_id", GUID(), sa.ForeignKey("resumes.id"), nullable=True),
        sa.Column("job_id", GUID(), sa.ForeignKey("jobs.id"), nullable=True),
        sa.Column(
            "document_type", sa.Enum("tailored_resume", "cover_letter", name="documenttype"), nullable=False
        ),
        sa.Column("document_format", sa.Enum("pdf", "docx", name="documentformat"), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("generation_prompt_summary", sa.Text(), nullable=True),
    )
    op.create_index("ix_documents_user_id", "documents", ["user_id"])

    op.create_table(
        "applications",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("job_id", GUID(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("resume_id", GUID(), sa.ForeignKey("resumes.id"), nullable=True),
        sa.Column("cover_letter_document_id", GUID(), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "saved", "applied", "oa", "interview", "offer", "accepted", "rejected", "withdrawn",
                name="applicationstatus",
            ),
            nullable=False,
            server_default="saved",
        ),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_applications_user_id", "applications", ["user_id"])
    op.create_index("ix_applications_job_id", "applications", ["job_id"])
    op.create_index("ix_applications_status", "applications", ["status"])

    op.create_table(
        "application_status_history",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("application_id", GUID(), sa.ForeignKey("applications.id"), nullable=False),
        sa.Column(
            "from_status",
            sa.Enum(
                "saved", "applied", "oa", "interview", "offer", "accepted", "rejected", "withdrawn",
                name="applicationstatus",
            ),
            nullable=True,
        ),
        sa.Column(
            "to_status",
            sa.Enum(
                "saved", "applied", "oa", "interview", "offer", "accepted", "rejected", "withdrawn",
                name="applicationstatus",
            ),
            nullable=False,
        ),
    )
    op.create_index("ix_application_status_history_application_id", "application_status_history", ["application_id"])

    op.create_table(
        "interview_preps",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("application_id", GUID(), sa.ForeignKey("applications.id"), nullable=False, unique=True),
        sa.Column("company_summary", sa.Text(), nullable=False),
        sa.Column("latest_news", sa.JSON(), nullable=False),
        sa.Column("tech_stack", sa.JSON(), nullable=False),
        sa.Column("likely_rounds", sa.JSON(), nullable=False),
        sa.Column("behavioral_questions", sa.JSON(), nullable=False),
        sa.Column("coding_questions", sa.JSON(), nullable=False),
        sa.Column("system_design_questions", sa.JSON(), nullable=False),
        sa.Column("frontend_questions", sa.JSON(), nullable=False),
        sa.Column("lld_questions", sa.JSON(), nullable=False),
        sa.Column("hld_questions", sa.JSON(), nullable=False),
    )

    op.create_table(
        "notifications",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "channel",
            sa.Enum("email", "slack", "discord", "telegram", "in_app", name="notificationchannel"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sent_successfully", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("interview_preps")
    op.drop_table("application_status_history")
    op.drop_table("applications")
    op.drop_table("documents")
    op.drop_table("job_match_scores")
    op.drop_table("jobs")
    op.drop_table("resumes")
    op.drop_table("companies")
    op.drop_table("users")

    # op.drop_table() does not drop the Postgres ENUM types that
    # op.create_table() auto-created for Enum-typed columns above — those
    # are separate catalog objects. Without this, downgrading then
    # upgrading again fails with "type X already exists" (reproduced
    # against a real Postgres instance during verification).
    bind = op.get_bind()
    sa.Enum(name="notificationchannel").drop(bind, checkfirst=True)
    sa.Enum(name="applicationstatus").drop(bind, checkfirst=True)
    sa.Enum(name="documentformat").drop(bind, checkfirst=True)
    sa.Enum(name="documenttype").drop(bind, checkfirst=True)
    sa.Enum(name="atsprovider").drop(bind, checkfirst=True)
    sa.Enum(name="workmode").drop(bind, checkfirst=True)
    sa.Enum(name="workauthorization").drop(bind, checkfirst=True)
