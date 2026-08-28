import httpx
import pytest

from app.services.ats_adapters.greenhouse import GreenhouseAdapter
from app.services.ats_adapters.lever import LeverAdapter

GREENHOUSE_SAMPLE = {
    "jobs": [
        {
            "id": 12345,
            "title": "Senior Backend Engineer",
            "content": "<p>We build payments infra.</p>",
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/12345",
            "updated_at": "2026-07-20T10:00:00-07:00",
            "location": {"name": "Remote - US"},
            "departments": [{"name": "Engineering"}],
        }
    ]
}

LEVER_SAMPLE = [
    {
        "id": "abc-123",
        "text": "Frontend Engineer",
        "descriptionPlain": "Build our design system.",
        "hostedUrl": "https://jobs.lever.co/acme/abc-123",
        "createdAt": 1753000000000,
        "categories": {"location": "San Francisco", "team": "Product", "commitment": "Full-time"},
        "lists": [],
    }
]


@pytest.mark.asyncio
async def test_greenhouse_adapter_normalizes_postings():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "boards-api.greenhouse.io" in str(request.url)
        return httpx.Response(200, json=GREENHOUSE_SAMPLE)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        adapter = GreenhouseAdapter(http_client=http_client)
        async with adapter:
            postings = await adapter.fetch_postings("acme")

    assert len(postings) == 1
    posting = postings[0]
    assert posting.external_id == "12345"
    assert posting.title == "Senior Backend Engineer"
    assert posting.location == "Remote - US"
    assert posting.remote is True
    assert posting.department == "Engineering"


@pytest.mark.asyncio
async def test_lever_adapter_normalizes_postings():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "api.lever.co" in str(request.url)
        return httpx.Response(200, json=LEVER_SAMPLE)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        adapter = LeverAdapter(http_client=http_client)
        async with adapter:
            postings = await adapter.fetch_postings("acme")

    assert len(postings) == 1
    posting = postings[0]
    assert posting.external_id == "abc-123"
    assert posting.title == "Frontend Engineer"
    assert posting.department == "Product"
    assert posting.location == "San Francisco"
