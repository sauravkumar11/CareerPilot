import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.domain.models.job import ATSProvider, WorkMode


class CompanyBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    logo_url: Optional[str] = None


class MatchScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    score: int
    reasoning: str
    missing_skills: list[str]
    interview_likelihood: str
    difficulty: str
    ats_compatibility: int
    expected_salary_estimate: Optional[str] = None


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    location: Optional[str] = None
    work_mode: WorkMode
    department: Optional[str] = None
    seniority: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    visa_sponsorship: Optional[bool] = None
    tags: Optional[list[str]] = None
    apply_url: str
    posted_at: Optional[datetime] = None
    ats_provider: ATSProvider
    company: CompanyBrief
    match: Optional[MatchScoreRead] = None


class JobFilterParams(BaseModel):
    keyword: Optional[str] = None
    location: Optional[str] = None
    work_mode: Optional[WorkMode] = None
    posted_within_days: Optional[int] = None
    min_salary: Optional[int] = None
    visa_sponsorship: Optional[bool] = None
    tags: Optional[list[str]] = None
    page: int = 1
    page_size: int = 20
