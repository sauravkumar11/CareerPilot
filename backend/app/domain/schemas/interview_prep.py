import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class InterviewPrepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    company_summary: str
    latest_news: list[str]
    tech_stack: list[str]
    likely_rounds: list[str]

    behavioral_questions: list[str]
    coding_questions: list[str]
    system_design_questions: list[str]
    frontend_questions: list[str]
    lld_questions: list[str]
    hld_questions: list[str]


class InterviewPrepGenerateRequest(BaseModel):
    force_refresh_news: bool = False
