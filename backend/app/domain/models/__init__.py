"""
Import every model module so SQLAlchemy's declarative registry (and
therefore Base.metadata, used by Alembic autogenerate and test fixtures)
is fully populated as soon as `app.domain.models` is imported.
"""
from app.domain.models.application import Application, ApplicationStatusHistory  # noqa: F401
from app.domain.models.company import Company  # noqa: F401
from app.domain.models.interview_prep import InterviewPrep  # noqa: F401
from app.domain.models.job import Job, JobMatchScore  # noqa: F401
from app.domain.models.notification import Notification  # noqa: F401
from app.domain.models.resume import Document, Resume, ResumeAnalysis  # noqa: F401
from app.domain.models.user import User  # noqa: F401

__all__ = [
    "User",
    "Company",
    "Job",
    "JobMatchScore",
    "Application",
    "ApplicationStatusHistory",
    "Resume",
    "ResumeAnalysis",
    "Document",
    "Notification",
    "InterviewPrep",
]
