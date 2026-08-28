"""
Resume domain schemas.

`ResumeContent` is the structured contract for `Resume.content` — previously
an untyped dict. Every service that reads or writes resume content should
go through this schema so downstream consumers (parser, analysis,
customization, export) can rely on a shape instead of hoping the JSON blob
looks a certain way.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models.resume import DocumentFormat, DocumentType, ParseStatus


# --- Structured resume content contract -----------------------------------


class ResumeContact(BaseModel):
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None


class ResumeExperienceEntry(BaseModel):
    company: str
    title: str
    start_date: Optional[str] = None  # free text, e.g. "Jan 2022"
    end_date: Optional[str] = None  # None or "Present"
    location: Optional[str] = None
    bullets: list[str] = Field(default_factory=list)


class ResumeEducationEntry(BaseModel):
    institution: str
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class ResumeProjectEntry(BaseModel):
    name: str
    description: Optional[str] = None
    bullets: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    url: Optional[str] = None


class ResumeContent(BaseModel):
    """
    The structured, source-of-truth shape for a resume. `ResumeParserService`
    produces this from an uploaded file; `ResumeCustomizationService`
    reorganizes an existing instance of this without adding new facts.
    """

    contact: ResumeContact
    summary: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    experience: list[ResumeExperienceEntry] = Field(default_factory=list)
    education: list[ResumeEducationEntry] = Field(default_factory=list)
    projects: list[ResumeProjectEntry] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)

    def all_factual_tokens(self) -> set[str]:
        """
        A flattened set of every concrete noun-like fact in this resume
        (companies, titles, schools, skills, project names, tech). Used by
        the fabrication guard to check that a customized/derived version
        doesn't introduce facts absent from the source.
        """
        tokens: set[str] = set()
        tokens.update(s.lower() for s in self.skills)
        tokens.update(s.lower() for s in self.languages)
        for exp in self.experience:
            tokens.add(exp.company.lower())
            tokens.add(exp.title.lower())
        for edu in self.education:
            tokens.add(edu.institution.lower())
            if edu.degree:
                tokens.add(edu.degree.lower())
        for proj in self.projects:
            tokens.add(proj.name.lower())
            tokens.update(t.lower() for t in proj.tech_stack)
        return tokens


# --- Resume CRUD / versioning ----------------------------------------------


class ResumeCreate(BaseModel):
    label: str
    content: ResumeContent
    is_primary: bool = False


class ResumeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    label: str
    is_primary: bool
    version: int
    parent_resume_id: Optional[uuid.UUID] = None
    parse_status: ParseStatus
    content: dict
    created_at: datetime
    updated_at: datetime


class ResumeUploadResponse(BaseModel):
    id: uuid.UUID
    parse_status: ParseStatus
    message: str = "Resume uploaded. Parsing in progress."


class ResumeCustomizeRequest(BaseModel):
    job_id: uuid.UUID
    label: Optional[str] = None  # defaults to "<original label> (tailored)"


# --- Resume analysis ---------------------------------------------------


class ResumeAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    resume_id: uuid.UUID
    created_at: datetime
    ats_score: int
    extracted_skills: list[str]
    missing_skills_by_role: Optional[list[str]] = None
    strengths: list[str]
    weaknesses: list[str]


class ResumeAnalyzeRequest(BaseModel):
    target_job_id: Optional[uuid.UUID] = None


# --- Document export / cover letters ----------------------------------------


class DocumentExportRequest(BaseModel):
    document_format: DocumentFormat


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_type: DocumentType
    document_format: DocumentFormat
    storage_path: str
    created_at: datetime


class CoverLetterRequest(BaseModel):
    resume_id: Optional[uuid.UUID] = None  # defaults to user's primary resume
    tone: str = Field(default="professional", pattern="^(professional|natural)$")
