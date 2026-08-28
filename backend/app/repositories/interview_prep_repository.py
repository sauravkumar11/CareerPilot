import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.interview_prep import InterviewPrep
from app.repositories.base import BaseRepository


class InterviewPrepRepository(BaseRepository[InterviewPrep]):
    def __init__(self, session: AsyncSession):
        super().__init__(InterviewPrep, session)

    async def get_for_application(self, application_id: uuid.UUID) -> InterviewPrep | None:
        result = await self.session.execute(
            select(InterviewPrep).where(InterviewPrep.application_id == application_id)
        )
        return result.scalar_one_or_none()

    async def upsert(self, application_id: uuid.UUID, fields: dict) -> InterviewPrep:
        """
        Insert or update the single InterviewPrep row for `application_id`.
        `InterviewPrep.application_id` has a unique constraint, so a plain
        create() on a second generation would violate it -- this always
        overwrites in place instead, since prep material is meant to be
        regenerated as the job/company context changes, not versioned.
        """
        existing = await self.get_for_application(application_id)
        if existing:
            for key, value in fields.items():
                setattr(existing, key, value)
            await self.session.flush()
            return existing

        prep = InterviewPrep(application_id=application_id, **fields)
        self.session.add(prep)
        await self.session.flush()
        return prep
