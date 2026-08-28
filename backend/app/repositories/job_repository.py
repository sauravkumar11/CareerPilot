import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.domain.models.job import ATSProvider, Job, WorkMode
from app.domain.schemas.job import JobFilterParams
from app.repositories.base import BaseRepository


class JobRepository(BaseRepository[Job]):
    def __init__(self, session: AsyncSession):
        super().__init__(Job, session)

    async def get_by_external_id(self, company_id: uuid.UUID, ats_provider: ATSProvider, external_id: str) -> Job | None:
        result = await self.session.execute(
            select(Job).where(
                and_(
                    Job.company_id == company_id,
                    Job.ats_provider == ats_provider,
                    Job.external_id == external_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def search(self, filters: JobFilterParams) -> tuple[list[Job], int]:
        base_stmt = select(Job).where(Job.is_active.is_(True))

        if filters.keyword:
            like = f"%{filters.keyword}%"
            base_stmt = base_stmt.where(Job.title.ilike(like))
        if filters.location:
            base_stmt = base_stmt.where(Job.location.ilike(f"%{filters.location}%"))
        if filters.work_mode:
            base_stmt = base_stmt.where(Job.work_mode == filters.work_mode)
        if filters.posted_within_days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=filters.posted_within_days)
            base_stmt = base_stmt.where(Job.posted_at >= cutoff)
        if filters.min_salary:
            base_stmt = base_stmt.where(Job.salary_max >= filters.min_salary)
        if filters.visa_sponsorship is not None:
            base_stmt = base_stmt.where(Job.visa_sponsorship == filters.visa_sponsorship)
        if filters.tags:
            for tag in filters.tags:
                base_stmt = base_stmt.where(Job.tags.contains([tag]))

        # Real DB-level pagination: COUNT via a subquery of the filtered
        # statement (so the count always matches the filters exactly,
        # without duplicating the filter logic), then a separate
        # LIMIT/OFFSET query for just the requested page. Previously this
        # loaded every matching row into Python and paginated by slicing
        # the resulting list — correct but does not scale.
        count_stmt = select(func.count()).select_from(base_stmt.with_only_columns(Job.id).subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        offset = (filters.page - 1) * filters.page_size
        page_stmt = (
            base_stmt.options(joinedload(Job.company))
            .order_by(Job.posted_at.desc().nullslast(), Job.id)
            .limit(filters.page_size)
            .offset(offset)
        )
        result = await self.session.execute(page_stmt)
        page_items = result.unique().scalars().all()

        return list(page_items), total

    async def get_with_company(self, job_id: uuid.UUID) -> Job | None:
        result = await self.session.execute(
            select(Job).options(joinedload(Job.company)).where(Job.id == job_id)
        )
        return result.unique().scalar_one_or_none()
