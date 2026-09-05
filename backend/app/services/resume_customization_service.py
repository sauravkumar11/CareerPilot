"""
ResumeCustomizationService produces a tailored variant of a resume for a
specific job: reordering/reweighting existing bullets and skills toward
what the job asks for. It never adds an employer, title, school, project,
or skill that isn't already in the source content — enforced by the
system prompt *and* verified by `fabrication_guard` before the result is
ever persisted.
"""
import json
import logging

from app.domain.models.job import Job
from app.domain.schemas.resume import ResumeContent
from app.services.fabrication_guard import FabricationDetectedError, check_for_fabrication
from app.services.llm import LLMRouter, LLMUnavailableError

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You tailor an existing software engineering resume for a specific job posting. \
You may ONLY reorder, reweight, and rephrase content that already exists in the source resume — \
you must NEVER add a company, job title, school, project, skill, or achievement that isn't already \
present in the source. You may rewrite bullet phrasing to better match the job's language, but the \
underlying fact must remain unchanged (e.g. you can rephrase "built an API" as "designed and shipped \
a REST API" only if that's a fair rephrasing of a bullet that's actually there — don't add new claims).

Respond with ONLY a JSON object matching the exact same shape as the input resume (same top-level keys: \
contact, summary, skills, experience, education, projects, achievements, languages). Reorder `skills` \
to prioritize what the job wants. Reorder `experience`/`projects` bullets to lead with what's most \
relevant. You may shorten or drop bullets that are irrelevant, but never invent new ones."""


class ResumeCustomizationError(Exception):
    pass


class ResumeCustomizationService:
    def __init__(self, router: LLMRouter | None = None):
        self._router = router or LLMRouter()

    async def customize(self, source_content: ResumeContent, target_job: Job) -> ResumeContent:
        user_prompt = (
            f"SOURCE RESUME (structured JSON):\n{json.dumps(source_content.model_dump(), indent=2)}\n\n"
            f"TARGET JOB TITLE: {target_job.title}\n"
            f"TARGET JOB DESCRIPTION:\n{target_job.description_raw[:6000]}"
        )

        try:
            response = await self._router.generate(
                system=_SYSTEM_PROMPT,
                prompt=user_prompt,
                max_tokens=3000,
                json_mode=True,
                caller="resume_customization",
            )
        except LLMUnavailableError as exc:
            logger.error("ResumeCustomizationService LLM call failed: %s", exc)
            raise ResumeCustomizationError(f"Resume customization is temporarily unavailable: {exc}") from exc

        try:
            parsed = json.loads(response.text)
        except json.JSONDecodeError as exc:
            logger.error("ResumeCustomizationService got non-JSON response: %s", response.text[:500])
            raise ResumeCustomizationError("Could not generate a tailored resume — please try again") from exc

        try:
            customized = ResumeContent.model_validate(parsed)
        except Exception as exc:
            logger.error("ResumeCustomizationService output failed schema validation: %s", parsed)
            raise ResumeCustomizationError("Tailored resume content did not match the expected shape") from exc

        # Verify no new facts were introduced before this is ever persisted.
        serialized = json.dumps(customized.model_dump())
        try:
            check_for_fabrication(source_content, serialized)
        except FabricationDetectedError as exc:
            logger.error(
                "ResumeCustomizationService output flagged as potential fabrication: %s", exc.suspect_terms
            )
            raise ResumeCustomizationError(
                "Generated resume appears to introduce content not present in your original resume "
                f"(flagged terms: {', '.join(exc.suspect_terms[:5])}). Please try again."
            ) from exc

        return customized
