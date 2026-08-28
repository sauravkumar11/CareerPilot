"""
CoverLetterService generates a personalized, company- and role-specific
cover letter from the user's real resume content. Same no-fabrication
contract as ResumeCustomizationService: only references experience,
projects, and skills that actually appear in the source resume.
"""
import logging

import anthropic
from anthropic import AsyncAnthropic

from app.core.config import get_settings
from app.domain.models.job import Job
from app.domain.schemas.resume import ResumeContent
from app.services.fabrication_guard import FabricationDetectedError, check_for_fabrication

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT_TEMPLATE = """You write a personalized cover letter for a software engineering job \
application. You may ONLY reference companies, projects, skills, and achievements that are explicitly \
present in the candidate's resume content provided below — never invent or embellish experience. \
Mention the target company name, the role title, and 1-3 specific, real projects/achievements from the \
resume that are genuinely relevant to this role. Tone: {tone}. Length: 3-4 short paragraphs. Do not use \
placeholder brackets like [Company Name] — write the actual letter. Do not include a letterhead/date \
block, just the letter body starting with a greeting."""


class CoverLetterGenerationError(Exception):
    pass


class CoverLetterService:
    def __init__(self):
        settings = get_settings()
        self._client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = settings.ANTHROPIC_MODEL

    async def generate(self, resume_content: ResumeContent, job: Job, tone: str = "professional") -> str:
        tone_instruction = "warm, professional, and confident" if tone == "professional" else "natural and conversational, like a genuine human wrote it, while still professional"
        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(tone=tone_instruction)

        company_name = job.company.name if job.company else "the company"
        user_prompt = (
            f"CANDIDATE RESUME (structured JSON):\n{resume_content.model_dump_json(indent=2)}\n\n"
            f"TARGET COMPANY: {company_name}\n"
            f"TARGET ROLE: {job.title}\n"
            f"JOB DESCRIPTION:\n{job.description_raw[:6000]}"
        )

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=1200,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except anthropic.APIError as exc:
            logger.error("CoverLetterService Anthropic API call failed: %s", exc)
            raise CoverLetterGenerationError(f"Cover letter generation is temporarily unavailable: {exc}") from exc

        letter_text = "".join(block.text for block in response.content if block.type == "text").strip()

        if not letter_text:
            raise CoverLetterGenerationError("AI returned an empty cover letter")

        # Company name, role title, and generic cover-letter vocabulary are
        # legitimately expected to appear even though they're not "from"
        # the resume — allow them explicitly before flagging anything else.
        extra_allowed = _words_of(company_name) | _words_of(job.title) | _COVER_LETTER_VOCAB

        try:
            check_for_fabrication(resume_content, letter_text, extra_allowed_terms=extra_allowed)
        except FabricationDetectedError as exc:
            logger.error("CoverLetterService output flagged as potential fabrication: %s", exc.suspect_terms)
            raise CoverLetterGenerationError(
                "Generated cover letter appears to reference experience not present in your resume "
                f"(flagged terms: {', '.join(exc.suspect_terms[:5])}). Please try again."
            ) from exc

        return letter_text


def _words_of(text: str) -> set[str]:
    return {w.lower() for w in text.replace(",", " ").split() if len(w) > 2}


_COVER_LETTER_VOCAB = {
    "sincerely", "regards", "dear", "hiring", "manager", "team", "opportunity",
    "excited", "passionate", "contribute", "thank", "consideration", "application",
}
