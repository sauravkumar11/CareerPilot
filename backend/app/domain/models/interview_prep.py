import uuid

from sqlalchemy import JSON, ForeignKey, Text
from app.db.base import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class InterviewPrep(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    AI-generated prep material for a single application. One-to-one with
    Application; regenerated on demand if the job or company info changes.
    """

    __tablename__ = "interview_preps"

    application_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("applications.id"), unique=True, nullable=False
    )

    company_summary: Mapped[str] = mapped_column(Text, nullable=False)
    latest_news: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    tech_stack: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    likely_rounds: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    behavioral_questions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    coding_questions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    system_design_questions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    frontend_questions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    lld_questions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    hld_questions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    application: Mapped["Application"] = relationship(back_populates="interview_prep")
