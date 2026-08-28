"""
Orchestrates fetching postings from each company's configured ATS and
upserting them as normalized Job rows. Idempotent: re-running a sync only
inserts new postings and refreshes existing ones (never duplicates), and
marks postings that disappeared from the source as inactive.
"""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.company import Company
from app.domain.models.job import ATSProvider, Job, WorkMode
from app.repositories.job_repository import JobRepository
from app.services.ats_adapters.factory import get_adapter

logger = logging.getLogger(__name__)


class JobDiscoveryService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.job_repo = JobRepository(session)

    async def sync_company(self, company: Company) -> dict[str, int]:
        """Fetch and upsert all postings for a single company. Returns sync stats."""
        if not company.ats_provider or not company.ats_identifier:
            raise ValueError(f"Company {company.name} has no ATS provider/identifier configured")

        provider = ATSProvider(company.ats_provider)
        adapter = get_adapter(provider)

        stats = {"created": 0, "updated": 0, "deactivated": 0, "errors": 0}

        try:
            async with adapter:
                postings = await adapter.fetch_postings(company.ats_identifier)
        except Exception:
            logger.exception("Failed to fetch postings for company=%s provider=%s", company.name, provider)
            stats["errors"] += 1
            return stats

        seen_external_ids: set[str] = set()

        for posting in postings:
            seen_external_ids.add(posting.external_id)
            existing = await self.job_repo.get_by_external_id(company.id, provider, posting.external_id)

            work_mode = WorkMode.REMOTE if posting.remote else WorkMode.UNKNOWN
            if posting.location and not posting.remote:
                lower = posting.location.lower()
                if "hybrid" in lower:
                    work_mode = WorkMode.HYBRID
                elif "remote" not in lower:
                    work_mode = WorkMode.ONSITE

            if existing:
                existing.title = posting.title
                existing.description_raw = posting.description_raw
                existing.location = posting.location
                existing.work_mode = work_mode
                existing.department = posting.department
                existing.apply_url = posting.apply_url
                existing.posted_at = posting.posted_at
                existing.tags = posting.tags
                existing.salary_min = posting.salary_min
                existing.salary_max = posting.salary_max
                existing.salary_currency = posting.salary_currency
                existing.is_active = True
                stats["updated"] += 1
            else:
                await self.job_repo.create(
                    company_id=company.id,
                    external_id=posting.external_id,
                    ats_provider=provider,
                    title=posting.title,
                    description_raw=posting.description_raw,
                    location=posting.location,
                    work_mode=work_mode,
                    department=posting.department,
                    apply_url=posting.apply_url,
                    posted_at=posting.posted_at,
                    tags=posting.tags,
                    salary_min=posting.salary_min,
                    salary_max=posting.salary_max,
                    salary_currency=posting.salary_currency,
                    is_active=True,
                )
                stats["created"] += 1

        # Deactivate postings that no longer appear upstream.
        existing_jobs = await self.session.execute(
            Job.__table__.select().where(Job.company_id == company.id, Job.ats_provider == provider)
        )
        for row in existing_jobs.mappings():
            if row["external_id"] not in seen_external_ids and row["is_active"]:
                job = await self.job_repo.get(row["id"])
                if job:
                    job.is_active = False
                    stats["deactivated"] += 1

        await self.session.commit()
        logger.info("Synced company=%s provider=%s stats=%s", company.name, provider, stats)
        return stats

    async def sync_all(self, companies: list[Company]) -> dict[str, dict[str, int]]:
        results: dict[str, dict[str, int]] = {}
        for company in companies:
            results[company.slug] = await self.sync_company(company)
        return results
