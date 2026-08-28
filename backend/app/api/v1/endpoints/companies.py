import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, ConfigDict
from slugify import slugify

from app.api.deps import CurrentUser, DbSession
from app.domain.models.company import Company
from app.repositories.company_repository import CompanyRepository
from app.services.job_discovery_service import JobDiscoveryService

router = APIRouter(prefix="/companies", tags=["companies"])


class CompanyCreate(BaseModel):
    name: str
    ats_provider: str  # greenhouse | lever | ashby | smartrecruiters
    ats_identifier: str
    website: str | None = None


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    ats_provider: str | None
    ats_identifier: str | None
    website: str | None


@router.get("", response_model=list[CompanyRead])
async def list_companies(db: DbSession, current_user: CurrentUser):
    repo = CompanyRepository(db)
    return await repo.list(limit=500)


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
async def add_company(payload: CompanyCreate, db: DbSession, current_user: CurrentUser):
    repo = CompanyRepository(db)
    slug = slugify(payload.name)
    if await repo.get_by_slug(slug):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Company already exists")

    company = await repo.create(
        name=payload.name,
        slug=slug,
        website=payload.website,
        ats_provider=payload.ats_provider,
        ats_identifier=payload.ats_identifier,
    )
    await repo.commit()
    return company


@router.post("/{company_id}/sync", status_code=status.HTTP_202_ACCEPTED)
async def sync_company_jobs(
    company_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
):
    repo = CompanyRepository(db)
    company = await repo.get(company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    service = JobDiscoveryService(db)
    stats = await service.sync_company(company)
    return {"company": company.slug, "stats": stats}
