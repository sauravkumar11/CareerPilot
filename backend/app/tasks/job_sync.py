"""
Celery entrypoints for job syncing. Celery tasks are sync by nature, so
each task spins up its own asyncio event loop to drive the async
SQLAlchemy session and ATS adapters.
"""
import asyncio
import logging

from app.core.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.repositories.company_repository import CompanyRepository
from app.services.job_discovery_service import JobDiscoveryService

logger = logging.getLogger(__name__)


async def _sync_all_companies_async() -> dict:
    async with AsyncSessionLocal() as session:
        company_repo = CompanyRepository(session)
        companies = await company_repo.list_with_ats()
        service = JobDiscoveryService(session)
        return await service.sync_all(companies)


async def _sync_single_company_async(company_id: str) -> dict:
    import uuid

    async with AsyncSessionLocal() as session:
        company_repo = CompanyRepository(session)
        company = await company_repo.get(uuid.UUID(company_id))
        if not company:
            return {"error": f"company {company_id} not found"}
        service = JobDiscoveryService(session)
        return await service.sync_company(company)


@celery_app.task(name="app.tasks.job_sync.sync_all_companies")
def sync_all_companies() -> dict:
    logger.info("Starting scheduled sync for all companies")
    return asyncio.run(_sync_all_companies_async())


@celery_app.task(name="app.tasks.job_sync.sync_single_company")
def sync_single_company(company_id: str) -> dict:
    return asyncio.run(_sync_single_company_async(company_id))
