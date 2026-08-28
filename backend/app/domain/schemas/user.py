import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.domain.models.user import WorkAuthorization


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    is_verified: bool
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    notice_period_days: Optional[int] = None
    work_authorization: Optional[WorkAuthorization] = None
    preferred_min_salary: Optional[int] = None
    preferred_countries: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    notice_period_days: Optional[int] = None
    work_authorization: Optional[WorkAuthorization] = None
    preferred_min_salary: Optional[int] = None
    preferred_countries: Optional[str] = None
