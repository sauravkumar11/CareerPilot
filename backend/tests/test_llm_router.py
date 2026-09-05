"""
Tests for the LLM abstraction layer itself (app/services/llm/) — provider
selection, the json_mode + use_web_search guard (a real Gemini API
constraint discovered during the Anthropic -> Gemini migration, not an
assumption), and error propagation.
"""
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.asyncio


@pytest.fixture
def clean_provider_cache():
    from app.services.llm.router import reset_provider_cache

    reset_provider_cache()
    yield
    reset_provider_cache()


async def test_router_delegates_to_configured_provider():
    from app.services.llm import LLMResponse, LLMRouter

    fake_provider = AsyncMock()
    fake_provider.name = "gemini"
    fake_provider.generate.return_value = LLMResponse(
        text="hello", provider="gemini", model="gemini-2.5-flash", latency_ms=5.0
    )

    router = LLMRouter(provider=fake_provider)
    result = await router.generate(system="sys", prompt="hi", max_tokens=100, caller="test")

    assert result.text == "hello"
    fake_provider.generate.assert_awaited_once_with(
        system="sys", prompt="hi", max_tokens=100, json_mode=False, use_web_search=False
    )


async def test_router_propagates_llm_errors():
    from app.services.llm import LLMRouter, LLMUnavailableError

    fake_provider = AsyncMock()
    fake_provider.name = "gemini"
    fake_provider.generate.side_effect = LLMUnavailableError("provider down")

    router = LLMRouter(provider=fake_provider)
    with pytest.raises(LLMUnavailableError):
        await router.generate(system="sys", prompt="hi", max_tokens=100, caller="test")


async def test_get_provider_builds_gemini_by_default(clean_provider_cache, monkeypatch):
    """Real config -> real provider construction (network call itself is
    what's untestable here, not the wiring — GeminiProvider's __init__
    doesn't make any network call, it just constructs a client)."""
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-key-for-construction-test")
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    import app.core.config as config_module

    config_module.get_settings.cache_clear()

    from app.services.llm import GeminiProvider
    from app.services.llm.router import get_provider

    provider = get_provider()
    assert isinstance(provider, GeminiProvider)
    assert provider.name == "gemini"

    config_module.get_settings.cache_clear()


async def test_get_provider_rejects_unknown_provider(clean_provider_cache, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "some-future-provider-not-yet-implemented")
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    import app.core.config as config_module

    config_module.get_settings.cache_clear()

    from app.services.llm import LLMError
    from app.services.llm.router import get_provider

    with pytest.raises(LLMError, match="Unknown LLM_PROVIDER"):
        get_provider()

    config_module.get_settings.cache_clear()


async def test_gemini_provider_rejects_json_mode_with_web_search():
    """Confirmed real Gemini API behavior, not an assumption: the API
    rejects response_mime_type='application/json' combined with tools in
    the same request (400 INVALID_ARGUMENT). This guard prevents any
    future caller from hitting that error at request time instead of at
    development time."""
    from app.services.llm import GeminiProvider, LLMError

    provider = GeminiProvider(api_key="fake-key", model="gemini-2.5-flash")

    with pytest.raises(LLMError, match="json_mode and use_web_search together"):
        await provider.generate(
            system="sys", prompt="hi", max_tokens=100, json_mode=True, use_web_search=True
        )


async def test_gemini_provider_requires_api_key():
    from app.services.llm import GeminiProvider, LLMError

    with pytest.raises(LLMError, match="GOOGLE_API_KEY is not set"):
        GeminiProvider(api_key="", model="gemini-2.5-flash")


async def test_gemini_provider_wraps_api_errors_as_llm_unavailable():
    """Verifies the exception-mapping logic directly, since we can't make
    a real network call to Gemini from this environment (confirmed
    blocked — see CHANGELOG) to trigger a genuine APIError."""
    from google.genai import errors as genai_errors

    from app.services.llm import GeminiProvider, LLMUnavailableError

    provider = GeminiProvider(api_key="fake-key", model="gemini-2.5-flash")

    with patch.object(
        provider._client.aio.models,
        "generate_content",
        AsyncMock(
            side_effect=genai_errors.ClientError(
                code=429, response_json={"error": {"message": "rate limit exceeded"}}
            )
        ),
    ):
        with pytest.raises(LLMUnavailableError, match="Gemini API call failed"):
            await provider.generate(system="sys", prompt="hi", max_tokens=100)


async def test_gemini_provider_wraps_network_errors_as_llm_unavailable():
    import httpx

    from app.services.llm import GeminiProvider, LLMUnavailableError

    provider = GeminiProvider(api_key="fake-key", model="gemini-2.5-flash")

    with patch.object(
        provider._client.aio.models,
        "generate_content",
        AsyncMock(side_effect=httpx.ConnectError("connection refused")),
    ):
        with pytest.raises(LLMUnavailableError, match="Could not reach Gemini API"):
            await provider.generate(system="sys", prompt="hi", max_tokens=100)
