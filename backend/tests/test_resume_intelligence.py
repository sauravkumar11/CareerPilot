import json
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.asyncio


def _mock_anthropic_response(payload: dict):
    """Builds a fake AsyncAnthropic().messages.create() response."""
    block = type("Block", (), {"type": "text", "text": json.dumps(payload)})()
    response = type("Response", (), {"content": [block]})()
    return response


async def _register_and_login(client, email="resume-user@example.com"):
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret123", "full_name": "Resume User"},
    )
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret123"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


SAMPLE_RESUME_CONTENT = {
    "contact": {"full_name": "Resume User", "email": "resume-user@example.com"},
    "summary": "Backend engineer.",
    "skills": ["Python", "FastAPI"],
    "experience": [
        {
            "company": "Acme",
            "title": "Backend Engineer",
            "start_date": "2022",
            "end_date": "Present",
            "bullets": ["Built REST APIs"],
        }
    ],
    "education": [],
    "projects": [],
    "achievements": [],
    "languages": [],
}


async def test_create_resume_from_structured_content(client):
    headers = await _register_and_login(client)
    resp = await client.post(
        "/api/v1/resumes",
        json={"label": "Primary", "content": SAMPLE_RESUME_CONTENT, "is_primary": True},
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["label"] == "Primary"
    assert body["version"] == 1
    assert body["parent_resume_id"] is None
    assert body["parse_status"] == "parsed"


async def test_analyze_resume_returns_structured_result(client):
    headers = await _register_and_login(client, "analyze-user@example.com")
    create_resp = await client.post(
        "/api/v1/resumes",
        json={"label": "Primary", "content": SAMPLE_RESUME_CONTENT, "is_primary": True},
        headers=headers,
    )
    resume_id = create_resp.json()["id"]

    fake_response = _mock_anthropic_response(
        {
            "ats_score": 78,
            "extracted_skills": ["Python", "FastAPI"],
            "strengths": ["Clear ownership of backend services"],
            "weaknesses": ["No quantified impact metrics"],
        }
    )

    with patch("app.services.resume_analysis_service.AsyncAnthropic") as MockClient:
        MockClient.return_value.messages.create = AsyncMock(return_value=fake_response)
        resp = await client.post(f"/api/v1/resumes/{resume_id}/analyze", json={}, headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["ats_score"] == 78
    assert "Python" in body["extracted_skills"]


async def test_analyze_resume_not_owned_by_user_returns_404(client):
    headers_a = await _register_and_login(client, "owner-a@example.com")
    headers_b = await _register_and_login(client, "owner-b@example.com")

    create_resp = await client.post(
        "/api/v1/resumes",
        json={"label": "Primary", "content": SAMPLE_RESUME_CONTENT, "is_primary": True},
        headers=headers_a,
    )
    resume_id = create_resp.json()["id"]

    resp = await client.post(f"/api/v1/resumes/{resume_id}/analyze", json={}, headers=headers_b)
    assert resp.status_code == 404


async def test_analyze_resume_handles_non_json_ai_response(client):
    headers = await _register_and_login(client, "badjson-user@example.com")
    create_resp = await client.post(
        "/api/v1/resumes",
        json={"label": "Primary", "content": SAMPLE_RESUME_CONTENT, "is_primary": True},
        headers=headers,
    )
    resume_id = create_resp.json()["id"]

    block = type("Block", (), {"type": "text", "text": "not valid json"})()
    bad_response = type("Response", (), {"content": [block]})()

    with patch("app.services.resume_analysis_service.AsyncAnthropic") as MockClient:
        MockClient.return_value.messages.create = AsyncMock(return_value=bad_response)
        resp = await client.post(f"/api/v1/resumes/{resume_id}/analyze", json={}, headers=headers)

    assert resp.status_code == 502


async def test_export_resume_pdf(client):
    headers = await _register_and_login(client, "export-user@example.com")
    create_resp = await client.post(
        "/api/v1/resumes",
        json={"label": "Primary", "content": SAMPLE_RESUME_CONTENT, "is_primary": True},
        headers=headers,
    )
    resume_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/resumes/{resume_id}/export", json={"document_format": "pdf"}, headers=headers
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["document_format"] == "pdf"
    assert body["document_type"] == "tailored_resume"
    assert body["storage_path"]


async def test_upload_rejects_disallowed_mime_type(client):
    headers = await _register_and_login(client, "upload-user@example.com")
    resp = await client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.txt", b"plain text resume", "text/plain")},
        headers=headers,
    )
    assert resp.status_code == 415


async def test_upload_rejects_empty_file(client):
    headers = await _register_and_login(client, "empty-upload-user@example.com")
    resp = await client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.pdf", b"", "application/pdf")},
        headers=headers,
    )
    assert resp.status_code == 400
