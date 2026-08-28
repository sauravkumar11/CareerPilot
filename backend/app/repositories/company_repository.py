from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.company import Company
from app.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    def __init__(self, session: AsyncSession):
        super().__init__(Company, session)

    async def get_by_slug(self, slug: str) -> Company | None:
        result = await self.session.execute(select(Company).where(Company.slug == slug))
        return result.scalar_one_or_none()

    async def list_with_ats(self) -> list[Company]:
        """Companies configured with an ATS provider + identifier, i.e. syncable."""
        result = await self.session.execute(
            select(Company).where(Company.ats_provider.is_not(None), Company.ats_identifier.is_not(None))
        )
        return list(result.scalars().all())
