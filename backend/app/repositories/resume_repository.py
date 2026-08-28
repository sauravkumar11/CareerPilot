import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.resume import Resume, ResumeAnalysis
from app.repositories.base import BaseRepository


class ResumeRepository(BaseRepository[Resume]):
    def __init__(self, session: AsyncSession):
        super().__init__(Resume, session)

    async def list_for_user(self, user_id: uuid.UUID) -> list[Resume]:
        result = await self.session.execute(select(Resume).where(Resume.user_id == user_id))
        return list(result.scalars().all())

    async def get_primary(self, user_id: uuid.UUID) -> Resume | None:
        result = await self.session.execute(
            select(Resume).where(Resume.user_id == user_id, Resume.is_primary.is_(True))
        )
        return result.scalar_one_or_none()

    async def get_for_user(self, resume_id: uuid.UUID, user_id: uuid.UUID) -> Resume | None:
        result = await self.session.execute(
            select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_lineage(self, root_resume_id: uuid.UUID, user_id: uuid.UUID) -> list[Resume]:
        """
        All versions in a resume's lineage: the root itself plus every
        resume whose parent_resume_id points at it. One level deep is
        sufficient today since customization always derives from the
        canonical uploaded resume, not from another tailored variant.
        """
        result = await self.session.execute(
            select(Resume)
            .where(
                Resume.user_id == user_id,
                or_(Resume.id == root_resume_id, Resume.parent_resume_id == root_resume_id),
            )
            .order_by(Resume.version)
        )
        return list(result.scalars().all())

    async def latest_analysis(self, resume_id: uuid.UUID) -> ResumeAnalysis | None:
        result = await self.session.execute(
            select(ResumeAnalysis)
            .where(ResumeAnalysis.resume_id == resume_id)
            .order_by(ResumeAnalysis.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def add_analysis(self, analysis: ResumeAnalysis) -> ResumeAnalysis:
        self.session.add(analysis)
        await self.session.flush()
        return analysis
