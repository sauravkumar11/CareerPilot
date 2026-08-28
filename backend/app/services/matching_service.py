"""
AI Match Engine.

Calls Claude with the user's resume content + a job description and asks
for a structured, strictly-JSON match assessment. We never let the model
invent skills/experience for the resume side (that's ResumeAIService's
job and it has its own no-fabrication rule) — this service only *scores*.
"""
import json
import logging

import anthropic
from anthropic import AsyncAnthropic

from app.core.config import get_settings
from app.domain.models.job import Job
from app.domain.models.resume import Resume

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
    def __init__(self):
        settings = get_settings()
        self._client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = settings.ANTHROPIC_MODEL

    async def score_match(self, resume: Resume, job: Job) -> dict:
        user_prompt = (
            f"RESUME CONTENT (structured JSON):\n{json.dumps(resume.content, indent=2)}\n\n"
            f"JOB TITLE: {job.title}\n"
            f"COMPANY: {job.company.name if job.company else 'Unknown'}\n"
            f"LOCATION: {job.location or 'Not specified'}\n"
            f"JOB DESCRIPTION:\n{job.description_raw[:8000]}"
        )

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=1000,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except anthropic.APIError as exc:
            logger.error("MatchingService Anthropic API call failed: %s", exc)
            raise MatchingError(f"AI match scoring is temporarily unavailable: {exc}") from exc

        raw_text = "".join(block.text for block in response.content if block.type == "text")

        try:
            result = json.loads(raw_text)
        except json.JSONDecodeError:
            logger.error("MatchingService got non-JSON response: %s", raw_text[:500])
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
