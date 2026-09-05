"""
LLMRouter: the single place every service goes through to get an
LLMProvider and make a call. Two jobs:

1. Provider selection — reads which provider is configured (currently
   always "gemini", but the registry pattern below means adding a second
   provider later is "register it here", not "touch every service").
2. Telemetry — logs provider/model/latency/success/failure/token counts
   for every call, without ever logging prompt content or API keys (per
   the requirement to capture usage data without storing sensitive
   prompt contents). Implemented as structured logging rather than a new
   database table — practical, additive, doesn't require a schema change
   for what is fundamentally an operational/observability concern.
"""
import logging
import time

from app.core.config import get_settings
from app.services.llm.base import LLMError, LLMProvider, LLMResponse
from app.services.llm.gemini_provider import GeminiProvider

logger = logging.getLogger("app.llm.telemetry")

_provider_instance: LLMProvider | None = None


def _build_provider(provider_name: str) -> LLMProvider:
    settings = get_settings()
    if provider_name == "gemini":
        return GeminiProvider(api_key=settings.GOOGLE_API_KEY, model=settings.GEMINI_MODEL)
    raise LLMError(
        f"Unknown LLM_PROVIDER '{provider_name}'. Supported providers: gemini. "
        "To add a new provider, implement LLMProvider and register it here."
    )


def get_provider() -> LLMProvider:
    """
    Returns the configured provider as a process-wide singleton. Safe to
    cache: unlike the earlier Redis rate-limiter bug (see CHANGELOG),
    LLMProvider instances don't hold an event-loop-bound connection —
    the underlying google-genai client opens connections per-call.
    """
    global _provider_instance
    if _provider_instance is None:
        settings = get_settings()
        _provider_instance = _build_provider(settings.LLM_PROVIDER)
    return _provider_instance


def reset_provider_cache() -> None:
    """Test-only: forces the next get_provider() call to rebuild from
    current settings, mirroring the pattern used for get_settings()."""
    global _provider_instance
    _provider_instance = None


class LLMRouter:
    """
    Thin façade services call instead of touching a provider directly.
    Exists as a class (rather than a bare module function) so services can
    depend on `LLMRouter` as a named collaborator — matching the shape
    asked for (LLMProvider / GeminiProvider / LLMRouter) and giving a
    natural seam for per-instance overrides (e.g. a test double) without
    needing to patch module-level state.
    """

    def __init__(self, provider: LLMProvider | None = None):
        self._provider = provider or get_provider()

    async def generate(
        self,
        *,
        system: str,
        prompt: str,
        max_tokens: int,
        json_mode: bool = False,
        use_web_search: bool = False,
        caller: str = "unknown",
    ) -> LLMResponse:
        """
        `caller` is a short label (e.g. "resume_analysis", "matching") used
        only in telemetry logs to attribute usage per feature — never part
        of the request sent to the provider.
        """
        start = time.monotonic()
        try:
            result = await self._provider.generate(
                system=system,
                prompt=prompt,
                max_tokens=max_tokens,
                json_mode=json_mode,
                use_web_search=use_web_search,
            )
        except LLMError:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.info(
                "llm_call caller=%s provider=%s success=false latency_ms=%.0f",
                caller, self._provider.name, elapsed_ms,
            )
            raise

        logger.info(
            "llm_call caller=%s provider=%s model=%s success=true latency_ms=%.0f "
            "input_tokens=%s output_tokens=%s",
            caller, result.provider, result.model, result.latency_ms,
            result.input_tokens, result.output_tokens,
        )
        return result
