"""
AI Match Engine.

Calls the configured LLM provider (via LLMRouter) with the user's resume
content + a job description and asks for a structured, strictly-JSON match
assessment. We never let the model invent skills/experience for the resume
side (that's the resume services' job and they have their own
no-fabrication rule) — this service only *scores*.
"""
import json
import logging

from app.domain.models.job import Job
from app.domain.models.resume import Resume
from app.services.llm import LLMRouter, LLMUnavailableError

logger = logging.getLogger(__name__)


class MatchingError(Exception):
    pass


_SYSTEM_PROMPT = """You are an expert technical recruiter and ATS specialist evaluating how well a \
candidate's resume matches a specific software engineering job posting.

Respond with ONLY a JSON object (no markdown fences, no preamble) with exactly these keys:
{
  "score": <int 0-100, overall fit>,
  "reasoning": "<2-4 sentence explanation of the score, referencing specific resume content and job requirements>",
  "missing_skills": [<list of specific skills/technologies the job wants that the resume does not show>],
  "interview_likelihood": "<one of: low, medium, high>",
  "difficulty": "<one of: easy, medium, hard, very_hard>",
  "ats_compatibility": <int 0-100, how well the resume's structure/keywords would pass an ATS keyword filter for this posting>,
  "expected_salary_estimate": "<short string estimate or null if not enough info>"
}

Base the score only on what's actually in the resume. Do not assume skills that aren't listed or implied \
by real project/work history."""


class MatchingService:
    def __init__(self, router: LLMRouter | None = None):
        self._router = router or LLMRouter()

    async def score_match(self, resume: Resume, job: Job) -> dict:
        user_prompt = (
            f"RESUME CONTENT (structured JSON):\n{json.dumps(resume.content, indent=2)}\n\n"
            f"JOB TITLE: {job.title}\n"
            f"COMPANY: {job.company.name if job.company else 'Unknown'}\n"
            f"LOCATION: {job.location or 'Not specified'}\n"
            f"JOB DESCRIPTION:\n{job.description_raw[:8000]}"
        )

        try:
            response = await self._router.generate(
                system=_SYSTEM_PROMPT,
                prompt=user_prompt,
                max_tokens=1000,
                json_mode=True,
                caller="matching",
            )
        except LLMUnavailableError as exc:
            logger.error("MatchingService LLM call failed: %s", exc)
            raise MatchingError(f"AI match scoring is temporarily unavailable: {exc}") from exc

        try:
            result = json.loads(response.text)
        except json.JSONDecodeError:
            logger.error("MatchingService got non-JSON response: %s", response.text[:500])
            raise MatchingError("AI match scoring returned an unparseable response")

        return self._validate(result)

    @staticmethod
    def _validate(result: dict) -> dict:
        required_keys = {
            "score",
            "reasoning",
            "missing_skills",
            "interview_likelihood",
            "difficulty",
            "ats_compatibility",
            "expected_salary_estimate",
        }
        missing = required_keys - result.keys()
        if missing:
            raise ValueError(f"AI match response missing keys: {missing}")

        result["score"] = max(0, min(100, int(result["score"])))
        result["ats_compatibility"] = max(0, min(100, int(result["ats_compatibility"])))
        return result
