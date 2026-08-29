"""
Regression tests for app/core/config.py.

BACKEND_CORS_ORIGINS and ALLOWED_RESUME_MIME_TYPES were originally typed as
List[str] with a custom field_validator to split comma-separated strings.
That validator was silently dead code for real environment variables:
pydantic-settings attempts to JSON-decode any List[...]-typed env var
*before* custom validators run, so a plain string (not a JSON array) raised
a SettingsError at import time — which crashed the entire app on startup.
This was invisible in every prior test run because tests never set these
env vars explicitly (they always fell back to the Python-level default,
which is already a proper value, never round-tripped through env-var
JSON-decoding). Found via a real Render deployment failure, not by
inspection. Fixed by keeping these as plain str fields and exposing the
parsed list via a property instead.
"""
import importlib
import os

import pytest


@pytest.fixture
def clean_settings_cache():
    """get_settings() is @lru_cache'd — clear it so each test gets a fresh
    Settings() built from that test's own env vars, not a cached instance
    from an earlier test."""
    import app.core.config as config_module

    config_module.get_settings.cache_clear()
    yield
    config_module.get_settings.cache_clear()


def test_cors_origins_single_value_from_real_env_var(clean_settings_cache, monkeypatch):
    """This exact scenario crashed the app on a real Render deploy."""
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "https://frontend-vert-nu-40.vercel.app")
    from app.core.config import get_settings

    settings = get_settings()
    assert settings.cors_origins == ["https://frontend-vert-nu-40.vercel.app"]


def test_cors_origins_multiple_comma_separated_values(clean_settings_cache, monkeypatch):
    monkeypatch.setenv(
        "BACKEND_CORS_ORIGINS", "https://frontend-vert-nu-40.vercel.app,http://localhost:3000"
    )
    from app.core.config import get_settings

    settings = get_settings()
    assert settings.cors_origins == [
        "https://frontend-vert-nu-40.vercel.app",
        "http://localhost:3000",
    ]


def test_cors_origins_default_when_unset(clean_settings_cache, monkeypatch):
    monkeypatch.delenv("BACKEND_CORS_ORIGINS", raising=False)
    from app.core.config import get_settings

    settings = get_settings()
    assert settings.cors_origins == ["http://localhost:3000"]


def test_allowed_resume_mime_types_from_real_env_var(clean_settings_cache, monkeypatch):
    """Same underlying bug pattern as BACKEND_CORS_ORIGINS — not yet hit in
    production only because nothing currently overrides it via env, but the
    identical failure mode would apply the moment something did."""
    monkeypatch.setenv("ALLOWED_RESUME_MIME_TYPES", "application/pdf")
    from app.core.config import get_settings

    settings = get_settings()
    assert settings.allowed_resume_mime_types == ["application/pdf"]


def test_allowed_resume_mime_types_default_when_unset(clean_settings_cache, monkeypatch):
    monkeypatch.delenv("ALLOWED_RESUME_MIME_TYPES", raising=False)
    from app.core.config import get_settings

    settings = get_settings()
    assert "application/pdf" in settings.allowed_resume_mime_types
    assert (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        in settings.allowed_resume_mime_types
    )
