from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.domain.models.company import Company
from app.domain.models.job import Job
from app.services.ats_adapters.base import NormalizedPosting
from app.services.ats_adapters.greenhouse import GreenhouseAdapter
from app.services.job_discovery_service import JobDiscoveryService

pytestmark = pytest.mark.asyncio


async def _make_company(db_session) -> Company:
    company = Company(
        name="Acme",
        slug="acme",
        ats_provider="greenhouse",
        ats_identifier="acme",
    )
    db_session.add(company)
    await db_session.flush()
    return company


def _posting(external_id: str, title: str) -> NormalizedPosting:
    return NormalizedPosting(
        external_id=external_id,
        title=title,
        description_raw="A job.",
        location="Remote",
        apply_url=f"https://example.com/{external_id}",
        remote=True,
    )


async def test_duplicate_sync_does_not_duplicate_jobs(db_session):
    company = await _make_company(db_session)
    service = JobDiscoveryService(db_session)

    with patch.object(GreenhouseAdapter, "fetch_postings", new=AsyncMock(return_value=[_posting("1", "Backend Engineer")])):
        stats_first = await service.sync_company(company)
        stats_second = await service.sync_company(company)

    assert stats_first == {"created": 1, "updated": 0, "deactivated": 0, "errors": 0}
    assert stats_second == {"created": 0, "updated": 1, "deactivated": 0, "errors": 0}

    result = await db_session.execute(select(Job).where(Job.company_id == company.id))
    jobs = result.scalars().all()
    assert len(jobs) == 1, f"Expected exactly 1 job after 2 syncs of the same posting, got {len(jobs)}"


async def test_sync_updates_existing_posting_fields(db_session):
    company = await _make_company(db_session)
    service = JobDiscoveryService(db_session)

    with patch.object(GreenhouseAdapter, "fetch_postings", new=AsyncMock(return_value=[_posting("1", "Backend Engineer")])):
        await service.sync_company(company)

    with patch.object(GreenhouseAdapter, "fetch_postings", new=AsyncMock(return_value=[_posting("1", "Staff Backend Engineer")])):
        await service.sync_company(company)

    result = await db_session.execute(select(Job).where(Job.company_id == company.id))
    jobs = result.scalars().all()
    assert len(jobs) == 1
    assert jobs[0].title == "Staff Backend Engineer"


async def test_sync_deactivates_postings_removed_upstream(db_session):
    company = await _make_company(db_session)
    service = JobDiscoveryService(db_session)

    with patch.object(
        GreenhouseAdapter,
        "fetch_postings",
        new=AsyncMock(return_value=[_posting("1", "Backend Engineer"), _posting("2", "Frontend Engineer")]),
    ):
        await service.sync_company(company)

    with patch.object(GreenhouseAdapter, "fetch_postings", new=AsyncMock(return_value=[_posting("1", "Backend Engineer")])):
        stats = await service.sync_company(company)

    assert stats["deactivated"] == 1

    result = await db_session.execute(select(Job).where(Job.company_id == company.id, Job.external_id == "2"))
    job = result.scalar_one()
    assert job.is_active is False

    result = await db_session.execute(select(Job).where(Job.company_id == company.id, Job.external_id == "1"))
    job = result.scalar_one()
    assert job.is_active is True


async def test_sync_handles_adapter_failure_gracefully(db_session):
    """A network/API failure during sync should be caught, logged into
    stats, and NOT crash the caller (verified live: this exact path was
    exercised against a real blocked-network ATS call during manual
    verification and behaved correctly)."""
    company = await _make_company(db_session)
    service = JobDiscoveryService(db_session)

    with patch.object(GreenhouseAdapter, "fetch_postings", new=AsyncMock(side_effect=RuntimeError("network unreachable"))):
        stats = await service.sync_company(company)

    assert stats["errors"] == 1
    assert stats["created"] == 0
