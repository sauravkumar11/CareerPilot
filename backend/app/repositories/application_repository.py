import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.domain.models.application import Application, ApplicationStatus, ApplicationStatusHistory
from app.domain.models.job import Job
from app.repositories.base import BaseRepository


class ApplicationRepository(BaseRepository[Application]):
    def __init__(self, session: AsyncSession):
        super().__init__(Application, session)

    async def list_for_user(self, user_id: uuid.UUID, status: ApplicationStatus | None = None) -> list[Application]:
        stmt = (
            select(Application)
            .options(joinedload(Application.job).joinedload(Job.company))
            .where(Application.user_id == user_id)
        )
        if status:
            stmt = stmt.where(Application.status == status)
        result = await self.session.execute(stmt)
        return list(result.unique().scalars().all())

    async def get_for_user(self, application_id: uuid.UUID, user_id: uuid.UUID) -> Application | None:
        stmt = (
            select(Application)
            .options(joinedload(Application.job).joinedload(Job.company))
            .where(Application.id == application_id, Application.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def transition_status(self, application: Application, new_status: ApplicationStatus) -> Application:
        old_status = application.status
        application.status = new_status
        self.session.add(
            ApplicationStatusHistory(application_id=application.id, from_status=old_status, to_status=new_status)
        )
        await self.session.flush()
        return application

    async def status_counts_for_user(self, user_id: uuid.UUID) -> dict[str, int]:
        stmt = (
            select(Application.status, func.count(Application.id))
            .where(Application.user_id == user_id)
            .group_by(Application.status)
        )
        result = await self.session.execute(stmt)
        return {status.value: count for status, count in result.all()}
