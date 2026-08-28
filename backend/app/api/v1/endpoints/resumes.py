import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession, require_owner
from app.domain.models.resume import ParseStatus
from app.domain.schemas.resume import ResumeCreate, ResumeRead
from app.repositories.resume_repository import ResumeRepository

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.get("", response_model=list[ResumeRead])
async def list_resumes(db: DbSession, current_user: CurrentUser):
    repo = ResumeRepository(db)
    return await repo.list_for_user(current_user.id)


@router.post("", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
async def create_resume(payload: ResumeCreate, db: DbSession, current_user: CurrentUser):
    """
    Create a resume directly from structured content (no file). For
    uploading a PDF/DOCX to be parsed automatically, use
    POST /resumes/upload instead (see resume_intelligence.py).
    """
    repo = ResumeRepository(db)

    if payload.is_primary:
        existing_primary = await repo.get_primary(current_user.id)
        if existing_primary:
            existing_primary.is_primary = False

    resume = await repo.create(
        user_id=current_user.id,
        label=payload.label,
        content=payload.content.model_dump(),
        is_primary=payload.is_primary,
        version=1,
        parent_resume_id=None,
        source_file_path=None,
        parse_status=ParseStatus.PARSED,
    )
    await repo.commit()
    return resume


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(resume_id: uuid.UUID, db: DbSession, current_user: CurrentUser):
    repo = ResumeRepository(db)
    resume = await repo.get(resume_id)
    require_owner(resume, current_user, not_found_detail="Resume not found")
    await repo.delete(resume)
    await repo.commit()
