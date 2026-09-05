"""
ResumeAnalysisService scores a resume standalone (not against a specific
job — see MatchingService for that) for ATS compatibility, extracts the
skills it actually demonstrates, and surfaces strengths/weaknesses.
Mirrors MatchingService's strict-JSON contract and validation pattern.
"""
import json
import logging

from app.domain.models.job import Job
from app.domain.schemas.resume import ResumeContent
from app.services.llm import LLMRouter, LLMUnavailableError

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert technical resume reviewer and ATS (applicant tracking system) \
specialist evaluating a software engineering resume.

Respond with ONLY a JSON object (no markdown fences, no preamble) with exactly these keys:
{
  "ats_score": <int 0-100, how well this resume's structure and keyword density would survive an ATS filter>,
  "extracted_skills": [<specific skills/technologies genuinely demonstrated by the resume content, not guessed>],
  "strengths": [<2-5 specific strengths, referencing actual resume content>],
  "weaknesses": [<2-5 specific, actionable weaknesses - e.g. "no quantified impact in bullet 2", not generic advice>]
}

Base everything only on what's actually in the resume. Do not invent context that isn't there."""

_SYSTEM_PROMPT_WITH_TARGET = _SYSTEM_PROMPT + """

You are additionally given a target job description. Also include:
"missing_skills_by_role": [<specific skills/technologies the target job wants that this resume does not show>]
"""


class ResumeAnalysisError(Exception):
    pass


class ResumeAnalysisService:
    def __init__(self, router: LLMRouter | None = None):
        self._router = router or LLMRouter()

    async def analyze(self, content: ResumeContent, target_job: Job | None = None) -> dict:
        system_prompt = _SYSTEM_PROMPT_WITH_TARGET if target_job else _SYSTEM_PROMPT

        user_prompt = f"RESUME CONTENT (structured JSON):\n{json.dumps(content.model_dump(), indent=2)}"
        if target_job:
            user_prompt += (
                f"\n\nTARGET JOB TITLE: {target_job.title}\n"
                f"TARGET JOB DESCRIPTION:\n{target_job.description_raw[:6000]}"
            )

        try:
            response = await self._router.generate(
                system=system_prompt,
                prompt=user_prompt,
                max_tokens=1200,
                json_mode=True,
                caller="resume_analysis",
            )
        except LLMUnavailableError as exc:
            logger.error("ResumeAnalysisService LLM call failed: %s", exc)
            raise ResumeAnalysisError(f"Resume analysis is temporarily unavailable: {exc}") from exc

        try:
            result = json.loads(response.text)
        except json.JSONDecodeError as exc:
            logger.error("ResumeAnalysisService got non-JSON response: %s", response.text[:500])
            raise ResumeAnalysisError("AI resume analysis returned an unparseable response") from exc

        return self._validate(result, expect_target=target_job is not None)

    @staticmethod
    def _validate(result: dict, expect_target: bool) -> dict:
        required_keys = {"ats_score", "extracted_skills", "strengths", "weaknesses"}
        missing = required_keys - result.keys()
        if missing:
            raise ResumeAnalysisError(f"AI analysis response missing keys: {missing}")

        result["ats_score"] = max(0, min(100, int(result["ats_score"])))
        if expect_target and "missing_skills_by_role" not in result:
            result["missing_skills_by_role"] = []

        return result
