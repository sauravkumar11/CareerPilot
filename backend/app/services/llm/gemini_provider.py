"""
GeminiProvider: the LLMProvider implementation backing the app's primary
(and currently only) AI provider, Google Gemini.

Uses the official `google-genai` SDK (`from google import genai` — not the
older, now-deprecated `google-generativeai` package). API surface verified
directly against the installed package rather than assumed from
documentation, since SDK docs can lag behind what's actually shipped:
  - async calls go through `client.aio.models.generate_content(...)`
  - JSON mode: `GenerateContentConfig(response_mime_type="application/json")`
  - web search grounding: `Tool(google_search=GoogleSearch())`
  - errors: `google.genai.errors.APIError` (covers auth/quota/rate-limit/
    malformed-request failures reported by Google's API)
"""
import logging
import time

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.services.llm.base import LLMError, LLMProvider, LLMResponse, LLMUnavailableError

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise LLMError(
                "GOOGLE_API_KEY is not set. Gemini-backed AI features will fail until it is configured."
            )
        self._client = genai.Client(api_key=api_key)
        self._model = model

    async def generate(
        self,
        *,
        system: str,
        prompt: str,
        max_tokens: int,
        json_mode: bool = False,
        use_web_search: bool = False,
    ) -> LLMResponse:
        config_kwargs: dict = {
            "system_instruction": system,
            "max_output_tokens": max_tokens,
        }
        if json_mode and use_web_search:
            # Confirmed via Gemini API behavior (not an assumption): the API
            # rejects response_mime_type="application/json" combined with
            # tools in the same request with a 400 INVALID_ARGUMENT
            # ("Function calling with a response mime type: 'application/
            # json' is unsupported"). Callers needing both must make two
            # calls (search first, then a separate JSON-mode call using the
            # search results as context) — see InterviewPrepService for the
            # pattern this project already uses.
            raise LLMError(
                "Gemini does not support json_mode and use_web_search together in a single call "
                "(confirmed API limitation, not an SDK bug) — split into two calls instead."
            )
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"
        if use_web_search:
            config_kwargs["tools"] = [types.Tool(google_search=types.GoogleSearch())]

        start = time.monotonic()
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(**config_kwargs),
            )
        except genai_errors.APIError as exc:
            # Covers invalid/missing key (401/403), rate limit (429),
            # quota exceeded, malformed request (400), and Google-side
            # server errors (5xx) — all surfaced by the SDK as APIError
            # subclasses (ClientError/ServerError) with a real status code
            # and message attached.
            logger.error("Gemini API call failed (provider=gemini, model=%s): %s", self._model, exc)
            raise LLMUnavailableError(f"Gemini API call failed: {exc}") from exc
        except httpx.HTTPError as exc:
            # Raw transport-level failures (DNS, connection refused,
            # timeout) that never got far enough to become an APIError.
            logger.error("Gemini network error (provider=gemini, model=%s): %s", self._model, exc)
            raise LLMUnavailableError(f"Could not reach Gemini API: {exc}") from exc

        latency_ms = (time.monotonic() - start) * 1000

        text = response.text
        if text is None:
            # Empty response with no exception typically means a safety
            # refusal (the model declined to answer) rather than a
            # transport failure — surface it the same way callers already
            # handle "the AI didn't give us usable content".
            finish_reason = None
            if response.candidates:
                finish_reason = getattr(response.candidates[0], "finish_reason", None)
            logger.warning(
                "Gemini returned no text (provider=gemini, model=%s, finish_reason=%s)",
                self._model,
                finish_reason,
            )
            raise LLMUnavailableError(
                f"Gemini returned no usable content (finish_reason={finish_reason})"
            )

        usage = response.usage_metadata
        return LLMResponse(
            text=text,
            provider=self.name,
            model=self._model,
            latency_ms=latency_ms,
            input_tokens=getattr(usage, "prompt_token_count", None) if usage else None,
            output_tokens=getattr(usage, "candidates_token_count", None) if usage else None,
        )
