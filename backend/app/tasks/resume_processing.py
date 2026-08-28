"""
Celery entrypoints for resume processing. Follows the same pattern as
tasks/job_sync.py: each task drives its own asyncio event loop around the
async SQLAlchemy session and AI services.
"""
import asyncio
import logging
import uuid

from app.core.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.domain.models.resume import ParseStatus
from app.domain.schemas.resume import ResumeContent
from app.repositories.job_repository import JobRepository
from app.repositories.resume_repository import ResumeRepository
from app.services.resume_analysis_service import ResumeAnalysisService
from app.services.resume_parser_service import ResumeParserService, ResumeParsingError
from app.services.storage_service import get_storage

logger = logging.getLogger(__name__)


async def _parse_resume_async(resume_id: str, mime_type: str) -> dict:
    async with AsyncSessionLocal() as session:
        repo = ResumeRepository(session)
        resume = await repo.get(uuid.UUID(resume_id))
        if not resume:
            return {"error": f"resume {resume_id} not found"}

        storage = get_storage()
        try:
            file_bytes = await storage.read(resume.source_file_path)
            parser = ResumeParserService()
            content = await parser.parse(file_bytes, mime_type)
            resume.content = content.model_dump()
            resume.parse_status = ParseStatus.PARSED
            await session.commit()
            return {"resume_id": resume_id, "status": "parsed"}
        except ResumeParsingError as exc:
            logger.warning("Resume parsing failed for %s: %s", resume_id, exc)
            resume.parse_status = ParseStatus.FAILED
            await session.commit()
            return {"resume_id": resume_id, "status": "failed", "error": str(exc)}
        except Exception:
            logger.exception("Unexpected error parsing resume %s", resume_id)
            resume.parse_status = ParseStatus.FAILED
            await session.commit()
            return {"resume_id": resume_id, "status": "failed", "error": "unexpected error"}


async def _analyze_resume_async(resume_id: str, user_id: str, target_job_id: str | None) -> dict:
    async with AsyncSessionLocal() as session:
        resume_repo = ResumeRepository(session)
        resume = await resume_repo.get_for_user(uuid.UUID(resume_id), uuid.UUID(user_id))
        if not resume:
            return {"error": "resume not found"}

        target_job = None
        if target_job_id:
            job_repo = JobRepository(session)
            target_job = await job_repo.get_with_company(uuid.UUID(target_job_id))

        content = ResumeContent.model_validate(resume.content)
        service = ResumeAnalysisService()
        result = await service.analyze(content, target_job=target_job)

        from app.domain.models.resume import ResumeAnalysis

        analysis = ResumeAnalysis(
            resume_id=resume.id,
            target_job_id=target_job.id if target_job else None,
            ats_score=result["ats_score"],
            extracted_skills=result["extracted_skills"],
            missing_skills_by_role=result.get("missing_skills_by_role"),
            strengths=result["strengths"],
            weaknesses=result["weaknesses"],
        )
        await resume_repo.add_analysis(analysis)
        await session.commit()
        return {"resume_id": resume_id, "analysis_id": str(analysis.id)}


@celery_app.task(name="app.tasks.resume_processing.parse_resume_task")
def parse_resume_task(resume_id: str, mime_type: str) -> dict:
    return asyncio.run(_parse_resume_async(resume_id, mime_type))


@celery_app.task(name="app.tasks.resume_processing.analyze_resume_task")
def analyze_resume_task(resume_id: str, user_id: str, target_job_id: str | None = None) -> dict:
    return asyncio.run(_analyze_resume_async(resume_id, user_id, target_job_id))
