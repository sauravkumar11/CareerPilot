import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.domain.models.application import Application, ApplicationStatus
from app.domain.schemas.application import ApplicationCreate, ApplicationRead, ApplicationStatusUpdate
from app.repositories.application_repository import ApplicationRepository
from app.repositories.job_repository import JobRepository

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("", response_model=list[ApplicationRead])
async def list_applications(
    db: DbSession,
    current_user: CurrentUser,
    status_filter: ApplicationStatus | None = None,
):
    repo = ApplicationRepository(db)
    applications = await repo.list_for_user(current_user.id, status_filter)
    return applications


@router.post("", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
async def create_application(payload: ApplicationCreate, db: DbSession, current_user: CurrentUser):
    job_repo = JobRepository(db)
    job = await job_repo.get_with_company(payload.job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    repo = ApplicationRepository(db)
    application = Application(
        user_id=current_user.id,
        job_id=payload.job_id,
        resume_id=payload.resume_id,
        notes=payload.notes,
        status=ApplicationStatus.SAVED,
    )
    db.add(application)
    await db.flush()
    await repo.transition_status(application, ApplicationStatus.SAVED)
    await db.commit()

    return await repo.get_for_user(application.id, current_user.id)


@router.patch("/{application_id}/status", response_model=ApplicationRead)
async def update_application_status(
    application_id: uuid.UUID,
    payload: ApplicationStatusUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    repo = ApplicationRepository(db)
    application = await repo.get_for_user(application_id, current_user.id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    await repo.transition_status(application, payload.status)
    if payload.status == ApplicationStatus.APPLIED and not application.applied_at:
        application.applied_at = datetime.now(timezone.utc)
    if payload.notes is not None:
        application.notes = payload.notes

    await db.commit()
    return await repo.get_for_user(application_id, current_user.id)


@router.get("/pipeline-summary")
async def pipeline_summary(db: DbSession, current_user: CurrentUser):
    repo = ApplicationRepository(db)
    return await repo.status_counts_for_user(current_user.id)


@router.get("/{application_id}", response_model=ApplicationRead)
async def get_application(application_id: uuid.UUID, db: DbSession, current_user: CurrentUser):
    """
    Registered after /pipeline-summary deliberately — a dynamic
    /{application_id} route registered first would shadow the static
    /pipeline-summary path (FastAPI matches routes in registration order).
    """
    repo = ApplicationRepository(db)
    application = await repo.get_for_user(application_id, current_user.id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return application
