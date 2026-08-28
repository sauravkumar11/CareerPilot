import json
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.asyncio


def _text_response(payload):
    text = json.dumps(payload) if not isinstance(payload, str) else payload
    block = type("Block", (), {"type": "text", "text": text})()
    return type("Response", (), {"content": [block]})()


async def _register_and_login(client, email="prep-user@example.com"):
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret123", "full_name": "Prep User"},
    )
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret123"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_company(client, headers):
    company_resp = await client.post(
        "/api/v1/companies",
        json={"name": "Acme Corp", "ats_provider": "greenhouse", "ats_identifier": "acme"},
        headers=headers,
    )
    assert company_resp.status_code == 201
    return company_resp.json()


PREP_PAYLOAD = {
    "company_summary": "Acme Corp builds developer tools.",
    "tech_stack": ["Python", "Kubernetes"],
    "likely_rounds": ["Recruiter screen", "Technical phone screen", "Onsite"],
    "behavioral_questions": ["Tell me about a conflict you resolved."],
    "coding_questions": ["Implement a LRU cache."],
    "system_design_questions": ["Design a rate limiter."],
    "frontend_questions": [],
    "lld_questions": ["Design a parking lot system."],
    "hld_questions": ["Design a URL shortener."],
}


async def _seed_job_and_application(db_session, user_id, company_id):
    """Directly inserts a Job + Application via the test DB session, since
    job creation normally happens through ATS sync (tested elsewhere)."""
    import uuid as uuid_mod

    from app.domain.models.application import Application, ApplicationStatus
    from app.domain.models.job import ATSProvider, Job, WorkMode

    job = Job(
        company_id=uuid_mod.UUID(company_id),
        external_id="ext-1",
        ats_provider=ATSProvider.GREENHOUSE,
        title="Senior Backend Engineer",
        description_raw="We need a backend engineer skilled in Python and Kubernetes.",
        location="Remote",
        work_mode=WorkMode.REMOTE,
        apply_url="https://example.com/apply",
        is_active=True,
    )
    db_session.add(job)
    await db_session.flush()

    application = Application(
        user_id=uuid_mod.UUID(user_id),
        job_id=job.id,
        status=ApplicationStatus.APPLIED,
    )
    db_session.add(application)
    await db_session.commit()
    return str(application.id)


async def test_generate_interview_prep(client, db_session):
    headers = await _register_and_login(client)
    me = await client.get("/api/v1/users/me", headers=headers)
    user_id = me.json()["id"]

    company = await _create_company(client, headers)
    application_id = await _seed_job_and_application(db_session, user_id, company["id"])

    news_response = _text_response(["Acme Corp raised a $50M Series C in March 2026."])
    prep_response = _text_response(PREP_PAYLOAD)

    with patch("app.services.interview_prep_service.AsyncAnthropic") as MockClient:
        mock_create = AsyncMock(side_effect=[news_response, prep_response])
        MockClient.return_value.messages.create = mock_create

        resp = await client.post(
            f"/api/v1/applications/{application_id}/interview-prep", json={}, headers=headers
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["company_summary"] == PREP_PAYLOAD["company_summary"]
    assert body["tech_stack"] == PREP_PAYLOAD["tech_stack"]
    assert len(body["latest_news"]) == 1
    assert mock_create.call_count == 2  # one web-search call, one strict-JSON call


async def test_regenerate_reuses_cached_news_by_default(client, db_session):
    headers = await _register_and_login(client, "reuse-user@example.com")
    me = await client.get("/api/v1/users/me", headers=headers)
    user_id = me.json()["id"]

    company = await _create_company(client, headers)
    application_id = await _seed_job_and_application(db_session, user_id, company["id"])

    news_response = _text_response(["First news item."])
    prep_response = _text_response(PREP_PAYLOAD)

    with patch("app.services.interview_prep_service.AsyncAnthropic") as MockClient:
        MockClient.return_value.messages.create = AsyncMock(side_effect=[news_response, prep_response])
        first = await client.post(
            f"/api/v1/applications/{application_id}/interview-prep", json={}, headers=headers
        )
    assert first.status_code == 200

    prep_response_2 = _text_response(PREP_PAYLOAD)
    with patch("app.services.interview_prep_service.AsyncAnthropic") as MockClient:
        mock_create = AsyncMock(side_effect=[prep_response_2])
        MockClient.return_value.messages.create = mock_create
        second = await client.post(
            f"/api/v1/applications/{application_id}/interview-prep", json={}, headers=headers
        )

    assert second.status_code == 200
    assert second.json()["latest_news"] == ["First news item."]
    assert mock_create.call_count == 1


async def test_get_interview_prep_before_generation_returns_404(client, db_session):
    headers = await _register_and_login(client, "notyet-user@example.com")
    me = await client.get("/api/v1/users/me", headers=headers)
    user_id = me.json()["id"]

    company = await _create_company(client, headers)
    application_id = await _seed_job_and_application(db_session, user_id, company["id"])

    resp = await client.get(f"/api/v1/applications/{application_id}/interview-prep", headers=headers)
    assert resp.status_code == 404


async def test_interview_prep_not_owned_returns_404(client, db_session):
    headers_a = await _register_and_login(client, "prep-owner-a@example.com")
    headers_b = await _register_and_login(client, "prep-owner-b@example.com")

    me_a = await client.get("/api/v1/users/me", headers=headers_a)
    user_a_id = me_a.json()["id"]

    company = await _create_company(client, headers_a)
    application_id = await _seed_job_and_application(db_session, user_a_id, company["id"])

    resp = await client.post(
        f"/api/v1/applications/{application_id}/interview-prep", json={}, headers=headers_b
    )
    assert resp.status_code == 404


async def test_web_search_failure_does_not_block_generation(client, db_session):
    """If the web-search call raises, fetch_latest_news should swallow it
    and return an empty list rather than failing the whole request."""
    headers = await _register_and_login(client, "searchfail-user@example.com")
    me = await client.get("/api/v1/users/me", headers=headers)
    user_id = me.json()["id"]

    company = await _create_company(client, headers)
    application_id = await _seed_job_and_application(db_session, user_id, company["id"])

    prep_response = _text_response(PREP_PAYLOAD)

    async def _create_side_effect(*args, **kwargs):
        if kwargs.get("tools"):
            raise RuntimeError("web search unavailable")
        return prep_response

    with patch("app.services.interview_prep_service.AsyncAnthropic") as MockClient:
        MockClient.return_value.messages.create = AsyncMock(side_effect=_create_side_effect)
        resp = await client.post(
            f"/api/v1/applications/{application_id}/interview-prep", json={}, headers=headers
        )

    assert resp.status_code == 200
    assert resp.json()["latest_news"] == []
