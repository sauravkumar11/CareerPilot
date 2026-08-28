import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from app.db.base import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class WorkMode(str, enum.Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNKNOWN = "unknown"


class ATSProvider(str, enum.Enum):
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ASHBY = "ashby"
    SMARTRECRUITERS = "smartrecruiters"
    WORKDAY = "workday"
    MANUAL = "manual"


class Job(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    A normalized job posting, regardless of which ATS it was sourced from.
    `external_id` + `ats_provider` uniquely identify the source posting so
    re-syncing never creates duplicates.
    """

    __tablename__ = "jobs"
    __table_args__ = ()

    company_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    company: Mapped["Company"] = relationship(back_populates="jobs")

    external_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ats_provider: Mapped[ATSProvider] = mapped_column(
        Enum(ATSProvider, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    description_raw: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    work_mode: Mapped[WorkMode] = mapped_column(
        Enum(WorkMode, values_callable=lambda x: [e.value for e in x]), default=WorkMode.UNKNOWN, nullable=False
    )

    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    seniority: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    salary_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    visa_sponsorship: Mapped[Optional[bool]] = mapped_column(nullable=True)

    tags: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)  # e.g. ["react", "typescript"]

    apply_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    applications: Mapped[list["Application"]] = relationship(back_populates="job")
    match_scores: Mapped[list["JobMatchScore"]] = relationship(back_populates="job", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Job {self.title} @ {self.company_id}>"


class JobMatchScore(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    AI-computed match between a specific user's resume and a job. Cached so
    we don't re-call the LLM every time the dashboard is rendered.
    """

    __tablename__ = "job_match_scores"

    job_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("jobs.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    resume_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("resumes.id"), nullable=False)

    score: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-100
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    missing_skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    interview_likelihood: Mapped[str] = mapped_column(String(50), nullable=False)  # low/medium/high
    difficulty: Mapped[str] = mapped_column(String(50), nullable=False)
    ats_compatibility: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-100
    expected_salary_estimate: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    job: Mapped["Job"] = relationship(back_populates="match_scores")
