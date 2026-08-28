import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession
from app.domain.models.job import JobMatchScore, WorkMode
from app.domain.schemas.job import JobFilterParams, JobRead, MatchScoreRead
from app.repositories.job_repository import JobRepository
from app.repositories.resume_repository import ResumeRepository
from app.services.matching_service import MatchingError, MatchingService

router = APIRouter(prefix="/jobs", tags=["jobs"])


class PaginatedJobs(BaseModel):
    items: list[JobRead]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get("", response_model=PaginatedJobs)
async def search_jobs(
    db: DbSession,
    current_user: CurrentUser,
    keyword: str | None = None,
    location: str | None = None,
    work_mode: WorkMode | None = None,
    posted_within_days: int | None = None,
    min_salary: int | None = None,
    visa_sponsorship: bool | None = None,
    page: int = 1,
    page_size: int = 20,
):
    filters = JobFilterParams(
        keyword=keyword,
        location=location,
        work_mode=work_mode,
        posted_within_days=posted_within_days,
        min_salary=min_salary,
        visa_sponsorship=visa_sponsorship,
        page=page,
        page_size=page_size,
    )
    job_repo = JobRepository(db)
    jobs, total = await job_repo.search(filters)

    items = []
    for job in jobs:
        job_read = JobRead.model_validate(job)
        items.append(job_read)

    return PaginatedJobs(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
    )


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: uuid.UUID, db: DbSession, current_user: CurrentUser):
    job_repo = JobRepository(db)
    job = await job_repo.get_with_company(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobRead.model_validate(job)


@router.post("/{job_id}/match", response_model=MatchScoreRead)
async def compute_match(
    job_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
    resume_id: uuid.UUID | None = None,
):
    job_repo = JobRepository(db)
    resume_repo = ResumeRepository(db)

    job = await job_repo.get_with_company(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    resume = await resume_repo.get(resume_id) if resume_id else await resume_repo.get_primary(current_user.id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid resume found for this user")

    matching_service = MatchingService()
    try:
        result = await matching_service.score_match(resume, job)
    except MatchingError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    match_score = JobMatchScore(
        job_id=job.id,
        user_id=current_user.id,
        resume_id=resume.id,
        score=result["score"],
        reasoning=result["reasoning"],
        missing_skills=result["missing_skills"],
        interview_likelihood=result["interview_likelihood"],
        difficulty=result["difficulty"],
        ats_compatibility=result["ats_compatibility"],
        expected_salary_estimate=result.get("expected_salary_estimate"),
    )
    db.add(match_score)
    await db.commit()

    return MatchScoreRead.model_validate(match_score)
