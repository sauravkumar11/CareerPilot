import enum
import uuid
from typing import Optional

from sqlalchemy import JSON, Boolean, Enum, ForeignKey, Integer, String, Text
from app.db.base import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ParseStatus(str, enum.Enum):
    PENDING = "pending"
    PARSED = "parsed"
    FAILED = "failed"


class Resume(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    A user's resume content. `version`/`parent_resume_id` form a lineage:
    the original upload is version 1 with no parent; each AI-customized
    variant (see ResumeCustomizationService) is a new row pointing back at
    the resume it was derived from, so nothing is ever overwritten in
    place and match/analysis history stays attributable to the exact
    version it was computed against.

    We never fabricate experience — customization only reorganizes and
    highlights what's already in `content`.
    """

    __tablename__ = "resumes"

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. "Backend / Python"
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    parent_resume_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("resumes.id"), nullable=True)
    source_file_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    parse_status: Mapped[ParseStatus] = mapped_column(
        Enum(ParseStatus, values_callable=lambda x: [e.value for e in x]),
        default=ParseStatus.PARSED,
        nullable=False,
    )

    # Structured resume content (source of truth) — validated by
    # app.domain.schemas.resume.ResumeContent before being persisted here.
    content: Mapped[dict] = mapped_column(JSON, nullable=False)

    user: Mapped["User"] = relationship(back_populates="resumes")
    analyses: Mapped[list["ResumeAnalysis"]] = relationship(back_populates="resume", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Resume {self.label} v{self.version} user={self.user_id}>"


class ResumeAnalysis(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    AI-computed standalone analysis of a resume (not tied to a specific
    job — see JobMatchScore for that). Cached the same way JobMatchScore
    is, so the dashboard doesn't re-call the LLM on every view.
    """

    __tablename__ = "resume_analyses"

    resume_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("resumes.id"), nullable=False, index=True)
    target_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("jobs.id"), nullable=True)

    ats_score: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-100
    extracted_skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    missing_skills_by_role: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    strengths: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    weaknesses: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    raw_model_output_ref: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    resume: Mapped["Resume"] = relationship(back_populates="analyses")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ResumeAnalysis resume={self.resume_id} score={self.ats_score}>"


class DocumentType(str, enum.Enum):
    TAILORED_RESUME = "tailored_resume"
    COVER_LETTER = "cover_letter"


class DocumentFormat(str, enum.Enum):
    PDF = "pdf"
    DOCX = "docx"


class Document(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A generated, downloadable artifact (tailored resume or cover letter)."""

    __tablename__ = "documents"

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    source_resume_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("resumes.id"), nullable=True)
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("jobs.id"), nullable=True)

    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    document_format: Mapped[DocumentFormat] = mapped_column(
        Enum(DocumentFormat, values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    generation_prompt_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Document {self.document_type} {self.id}>"
