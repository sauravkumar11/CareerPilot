"""
InterviewPrepService generates interview preparation material for a
specific application. Two LLM calls:

1. `fetch_latest_news` — uses search grounding (use_web_search=True) via
   LLMRouter. This is deliberately the one place in the app that does a
   live web search, because "latest news" is exactly the kind of claim
   that goes stale the moment it's answered from training data alone.
   Note this call cannot also request json_mode: Gemini's API rejects
   combining tools with response_mime_type="application/json" (confirmed
   API behavior, not an assumption) — so this call relies on the system
   prompt's instruction to produce a JSON array as plain text, and parses
   it defensively (already necessary anyway, since even JSON-mode calls
   only guarantee *valid* JSON, not that the model followed instructions
   about content).
2. `generate_prep` — a strict-JSON call (json_mode=True, no web search;
   same contract style as MatchingService/ResumeAnalysisService) that
   produces the company summary, tech stack, likely interview rounds, and
   question sets, grounded in the job description and the news gathered
   in step 1.

If web search is unavailable or returns nothing useful, generation still
proceeds — `latest_news` is simply an empty list, not a hard failure.
"""
import json
import logging

from app.domain.models.job import Job
from app.services.llm import LLMRouter, LLMUnavailableError

logger = logging.getLogger(__name__)

_NEWS_SYSTEM_PROMPT = """You are a research assistant gathering recent, genuinely current news about a \
company for someone preparing for a job interview there. Use web search to find real, recent items -- \
funding, product launches, layoffs, leadership changes, major incidents, etc. \
Respond with ONLY a JSON array of up to 5 short strings (no markdown fences, no preamble), each a single \
factual news item with an approximate date if known. If you find nothing genuinely recent or notable, \
respond with an empty JSON array []. Do not invent news."""

_PREP_SYSTEM_PROMPT = """You are an expert technical interview coach preparing a candidate for a \
specific software engineering interview.

Respond with ONLY a JSON object (no markdown fences, no preamble) with exactly these keys:
{
  "company_summary": "<2-4 sentence overview of what the company does and its market position>",
  "tech_stack": [<technologies this company is known to use, inferred from the job description and general knowledge>],
  "likely_rounds": [<likely interview stages for this role, e.g. "Recruiter screen", "Technical phone screen", "Onsite: system design", "Onsite: coding">],
  "behavioral_questions": [<5-8 realistic behavioral questions for this role/company>],
  "coding_questions": [<5-8 realistic coding/algorithm questions or topics for this role's level>],
  "system_design_questions": [<3-5 system design questions/topics appropriate for this role's seniority - empty list if this is a junior/entry role where system design isn't typically asked>],
  "frontend_questions": [<3-6 frontend-specific questions if this is a frontend/fullstack role, otherwise empty list>],
  "lld_questions": [<2-4 low-level/object-oriented design questions appropriate for this role, otherwise empty list>],
  "hld_questions": [<2-4 high-level design questions appropriate for this role's seniority, otherwise empty list>]
}

Tailor everything to the specific job description and seniority level given. Don't include question \
categories that wouldn't realistically come up for this role (e.g. skip system design for an entry-level \
role, skip frontend questions for a pure backend role)."""


class InterviewPrepGenerationError(Exception):
    pass


class InterviewPrepService:
    def __init__(self, router: LLMRouter | None = None):
        self._router = router or LLMRouter()

    async def fetch_latest_news(self, company_name: str) -> list[str]:
        try:
            response = await self._router.generate(
                system=_NEWS_SYSTEM_PROMPT,
                prompt=f"Recent news about: {company_name}",
                max_tokens=1000,
                use_web_search=True,
                caller="interview_prep_news",
            )
        except Exception:
            logger.exception("Web search for company news failed for %s; continuing without it", company_name)
            return []

        raw_output = response.text.strip()

        if not raw_output:
            return []

        try:
            news = json.loads(raw_output)
        except json.JSONDecodeError:
            logger.warning("Company news response was not valid JSON, discarding: %s", raw_output[:300])
            return []

        if not isinstance(news, list):
            return []
        return [str(item) for item in news][:5]

    async def generate_prep(self, job: Job, latest_news: list[str]) -> dict:
        company_name = job.company.name if job.company else "the company"
        user_prompt = (
            f"COMPANY: {company_name}\n"
            f"ROLE: {job.title}\n"
            f"SENIORITY (if known): {job.seniority or 'not specified'}\n"
            f"JOB DESCRIPTION:\n{job.description_raw[:8000]}\n\n"
            f"RECENT NEWS ABOUT THE COMPANY:\n"
            + ("\n".join(f"- {item}" for item in latest_news) if latest_news else "No recent news found.")
        )

        try:
            response = await self._router.generate(
                system=_PREP_SYSTEM_PROMPT,
                prompt=user_prompt,
                max_tokens=3000,
                json_mode=True,
                caller="interview_prep_generate",
            )
        except LLMUnavailableError as exc:
            logger.error("InterviewPrepService LLM call failed: %s", exc)
            raise InterviewPrepGenerationError(f"Interview prep generation is temporarily unavailable: {exc}") from exc

        try:
            result = json.loads(response.text)
        except json.JSONDecodeError as exc:
            logger.error("InterviewPrepService got non-JSON response: %s", response.text[:500])
            raise InterviewPrepGenerationError("Could not generate interview prep — please try again") from exc

        return self._validate(result)

    @staticmethod
    def _validate(result: dict) -> dict:
        required_keys = {
            "company_summary", "tech_stack", "likely_rounds", "behavioral_questions",
            "coding_questions", "system_design_questions", "frontend_questions",
            "lld_questions", "hld_questions",
        }
        missing = required_keys - result.keys()
        if missing:
            raise InterviewPrepGenerationError(f"AI prep response missing keys: {missing}")

        list_fields = [
            "tech_stack", "likely_rounds", "behavioral_questions", "coding_questions",
            "system_design_questions", "frontend_questions", "lld_questions", "hld_questions",
        ]
        for field in list_fields:
            if not isinstance(result[field], list):
                raise InterviewPrepGenerationError(f"Expected '{field}' to be a list")

        return result
