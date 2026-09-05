import json
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.asyncio


def _mock_llm_response(text: str):
    """Builds a fake LLMResponse, as returned by LLMRouter.generate()."""
    from app.services.llm import LLMResponse

    return LLMResponse(text=text, provider="gemini", model="gemini-3.6-flash", latency_ms=10.0)


def _patch_llm_router(return_text: str | None = None, side_effect=None):
    """
    Patches app.services.llm.router.get_provider — the single seam every
    AI-calling service goes through via LLMRouter(). Patching here instead
    of per-service (as the pre-migration AsyncAnthropic patches did) covers
    every service uniformly, since they all construct LLMRouter() the same
    way.
    """
    mock_provider = AsyncMock()
    if side_effect is not None:
        mock_provider.generate.side_effect = side_effect
    else:
        mock_provider.generate.return_value = _mock_llm_response(return_text)
    mock_provider.name = "gemini"
    return patch("app.services.llm.router.get_provider", return_value=mock_provider)


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

    with _patch_llm_router(return_text=json.dumps({
        "ats_score": 78,
        "extracted_skills": ["Python", "FastAPI"],
        "strengths": ["Clear ownership of backend services"],
        "weaknesses": ["No quantified impact metrics"],
    })):
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

    with _patch_llm_router(return_text="not valid json"):
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
