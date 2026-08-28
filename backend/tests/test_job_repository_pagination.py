import pytest

from app.domain.models.company import Company
from app.domain.models.job import ATSProvider, Job, WorkMode
from app.domain.schemas.job import JobFilterParams
from app.repositories.job_repository import JobRepository

pytestmark = pytest.mark.asyncio


async def _seed_jobs(db_session, count: int) -> Company:
    company = Company(name="PagedCo", slug="pagedco", ats_provider="greenhouse", ats_identifier="pagedco")
    db_session.add(company)
    await db_session.flush()

    for i in range(count):
        job = Job(
            company_id=company.id,
            external_id=f"job-{i}",
            ats_provider=ATSProvider.GREENHOUSE,
            title=f"Engineer {i}",
            description_raw="desc",
            work_mode=WorkMode.REMOTE,
            apply_url=f"https://example.com/{i}",
            is_active=True,
        )
        db_session.add(job)
    await db_session.commit()
    return company


async def test_pagination_splits_results_correctly_across_pages(db_session):
    await _seed_jobs(db_session, count=5)
    repo = JobRepository(db_session)

    page1, total1 = await repo.search(JobFilterParams(page=1, page_size=2))
    page2, total2 = await repo.search(JobFilterParams(page=2, page_size=2))
    page3, total3 = await repo.search(JobFilterParams(page=3, page_size=2))

    assert total1 == total2 == total3 == 5
    assert len(page1) == 2
    assert len(page2) == 2
    assert len(page3) == 1

    all_ids = {j.id for j in page1} | {j.id for j in page2} | {j.id for j in page3}
    assert len(all_ids) == 5


async def test_pagination_respects_filters_in_count_and_page(db_session):
    await _seed_jobs(db_session, count=5)
    repo = JobRepository(db_session)

    items, total = await repo.search(JobFilterParams(keyword="Engineer 3", page=1, page_size=10))
    assert total == 1
    assert len(items) == 1
    assert items[0].title == "Engineer 3"


async def test_pagination_excludes_inactive_jobs(db_session):
    await _seed_jobs(db_session, count=3)
    repo = JobRepository(db_session)

    items, _ = await repo.search(JobFilterParams(page=1, page_size=10))
    job_to_deactivate = items[0]
    job_to_deactivate.is_active = False
    await db_session.commit()

    items, total = await repo.search(JobFilterParams(page=1, page_size=10))
    assert total == 2
    assert all(j.is_active for j in items)


async def test_empty_results_return_zero_total_and_empty_page(db_session):
    repo = JobRepository(db_session)
    items, total = await repo.search(JobFilterParams(page=1, page_size=10))
    assert total == 0
    assert items == []
