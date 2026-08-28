import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.core.rate_limit import RateLimitExceeded, check_rate_limit
from app.domain.schemas.interview_prep import InterviewPrepGenerateRequest, InterviewPrepRead
from app.repositories.application_repository import ApplicationRepository
from app.repositories.interview_prep_repository import InterviewPrepRepository
from app.services.interview_prep_service import InterviewPrepGenerationError, InterviewPrepService

router = APIRouter(prefix="/applications", tags=["interview-prep"])


@router.post("/{application_id}/interview-prep", response_model=InterviewPrepRead, status_code=status.HTTP_200_OK)
async def generate_interview_prep(
    application_id: uuid.UUID,
    payload: InterviewPrepGenerateRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    try:
        await check_rate_limit(current_user.id, "interview_prep")
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {exc.retry_after_seconds} seconds.",
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc

    application_repo = ApplicationRepository(db)
    application = await application_repo.get_for_user(application_id, current_user.id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    prep_repo = InterviewPrepRepository(db)
    existing = await prep_repo.get_for_application(application_id)

    service = InterviewPrepService()
    company_name = application.job.company.name if application.job.company else "the company"

    if existing and not payload.force_refresh_news:
        latest_news = existing.latest_news
    else:
        latest_news = await service.fetch_latest_news(company_name)

    try:
        result = await service.generate_prep(application.job, latest_news)
    except InterviewPrepGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    prep = await prep_repo.upsert(
        application_id,
        {
            "company_summary": result["company_summary"],
            "latest_news": latest_news,
            "tech_stack": result["tech_stack"],
            "likely_rounds": result["likely_rounds"],
            "behavioral_questions": result["behavioral_questions"],
            "coding_questions": result["coding_questions"],
            "system_design_questions": result["system_design_questions"],
            "frontend_questions": result["frontend_questions"],
            "lld_questions": result["lld_questions"],
            "hld_questions": result["hld_questions"],
        },
    )
    await db.commit()
    return prep


@router.get("/{application_id}/interview-prep", response_model=InterviewPrepRead)
async def get_interview_prep(application_id: uuid.UUID, db: DbSession, current_user: CurrentUser):
    application_repo = ApplicationRepository(db)
    application = await application_repo.get_for_user(application_id, current_user.id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    prep_repo = InterviewPrepRepository(db)
    prep = await prep_repo.get_for_application(application_id)
    if not prep:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No interview prep generated yet")
    return prep
