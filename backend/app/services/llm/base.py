"""
LLM provider abstraction.

Every AI-calling service in this app (matching, resume parsing/analysis/
customization, cover letters, interview prep) goes through this interface
instead of importing a specific vendor's SDK directly. This is what makes
the Anthropic -> Gemini migration a swap at the config/router level rather
than a rewrite of six services.

Design intentionally stays close to what the services already need (a
system prompt + a user prompt in, structured text out, optional JSON mode,
optional web-search grounding) rather than exposing every capability of
every provider's SDK. If a provider-specific feature is ever needed that
doesn't fit here, that's a sign the interface needs to grow deliberately,
not that a service should reach around it.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    latency_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None


class LLMError(Exception):
    """Base class for all LLM-layer errors. Services catch this (or the
    more specific subclasses below) instead of any provider-specific
    exception type."""


class LLMUnavailableError(LLMError):
    """The provider could not be reached or refused the request for a
    reason outside the caller's control: invalid/missing API key, rate
    limit, quota exceeded, timeout, network failure, or a safety refusal.
    Endpoints should generally map this to a 502/503, not a 500 — it's an
    upstream dependency problem, not a bug in this app."""


class LLMMalformedResponseError(LLMError):
    """The provider responded successfully, but the content didn't match
    what was asked for (e.g. invalid JSON when JSON was required). This is
    different from LLMUnavailableError: the call itself succeeded, the
    *content* is the problem."""


class LLMProvider(ABC):
    """Every concrete provider (GeminiProvider, etc.) implements this."""

    name: str

    @abstractmethod
    async def generate(
        self,
        *,
        system: str,
        prompt: str,
        max_tokens: int,
        json_mode: bool = False,
        use_web_search: bool = False,
    ) -> LLMResponse:
        """
        Send a single-turn request (system instruction + user prompt) and
        return the model's text response.

        Raises LLMUnavailableError if the call itself fails (auth, quota,
        rate limit, timeout, network, safety refusal). Never raises for a
        malformed *response* — callers that need strict JSON validate
        `.text` themselves (matching existing services' established
        pattern of parsing + validating the response body), since what
        "malformed" means is domain-specific per service.

        `json_mode` and `use_web_search` cannot both be True in a single
        call — confirmed against Gemini's actual API behavior, not
        assumed: it rejects response_mime_type="application/json"
        combined with tools with a 400 error. Callers needing both search
        grounding and strict JSON must make two calls: search first (text
        response), then a separate JSON-mode call using the search
        results as context (see InterviewPrepService for the pattern this
        project uses).
        """
        raise NotImplementedError
