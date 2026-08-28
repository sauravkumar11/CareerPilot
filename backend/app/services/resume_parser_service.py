"""
ResumeParserService turns an uploaded PDF/DOCX into structured
`ResumeContent`. Text extraction is done locally (no AI call needed for
that part); structuring the free-form extracted text into the
ResumeContent shape uses Claude with a strict instruction to transcribe
only — never invent, infer, or embellish anything not present in the
source text.
"""
import io
import json
import logging

import anthropic
import docx
from anthropic import AsyncAnthropic
from pypdf import PdfReader

from app.core.config import get_settings
from app.domain.schemas.resume import ResumeContent

logger = logging.getLogger(__name__)

_STRUCTURING_SYSTEM_PROMPT = """You transcribe resume text into a structured JSON format. You do not \
write, invent, infer, or embellish any content. Every fact in your output must be traceable to the \
exact input text. If a field isn't present in the source, omit it or leave it empty — never guess.

Respond with ONLY a JSON object (no markdown fences, no preamble) matching this shape:
{
  "contact": {"full_name": str, "email": str|null, "phone": str|null, "location": str|null,
              "github_url": str|null, "linkedin_url": str|null, "portfolio_url": str|null},
  "summary": str|null,
  "skills": [str],
  "experience": [{"company": str, "title": str, "start_date": str|null, "end_date": str|null,
                   "location": str|null, "bullets": [str]}],
  "education": [{"institution": str, "degree": str|null, "field_of_study": str|null,
                  "start_date": str|null, "end_date": str|null}],
  "projects": [{"name": str, "description": str|null, "bullets": [str], "tech_stack": [str], "url": str|null}],
  "achievements": [str],
  "languages": [str]
}"""


class ResumeParsingError(Exception):
    pass


class ResumeParserService:
    def __init__(self):
        settings = get_settings()
        self._client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = settings.ANTHROPIC_MODEL

    @staticmethod
    def extract_text(file_bytes: bytes, mime_type: str) -> str:
        if mime_type == "application/pdf":
            return ResumeParserService._extract_pdf_text(file_bytes)
        if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return ResumeParserService._extract_docx_text(file_bytes)
        raise ResumeParsingError(f"Unsupported MIME type: {mime_type}")

    @staticmethod
    def _extract_pdf_text(file_bytes: bytes) -> str:
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            pages = [page.extract_text() or "" for page in reader.pages]
        except Exception as exc:
            raise ResumeParsingError("Could not read PDF — it may be corrupted or password-protected") from exc

        text = "\n".join(pages).strip()
        if not text:
            raise ResumeParsingError(
                "No extractable text found in PDF (it may be a scanned image without a text layer)"
            )
        return text

    @staticmethod
    def _extract_docx_text(file_bytes: bytes) -> str:
        try:
            document = docx.Document(io.BytesIO(file_bytes))
            paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
        except Exception as exc:
            raise ResumeParsingError("Could not read DOCX — it may be corrupted") from exc

        text = "\n".join(paragraphs).strip()
        if not text:
            raise ResumeParsingError("No extractable text found in DOCX")
        return text

    async def structure_text(self, raw_text: str) -> ResumeContent:
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=2000,
                system=_STRUCTURING_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": raw_text[:20000]}],
            )
        except anthropic.APIError as exc:
            logger.error("ResumeParserService Anthropic API call failed: %s", exc)
            raise ResumeParsingError(f"Resume structuring is temporarily unavailable: {exc}") from exc

        raw_output = "".join(block.text for block in response.content if block.type == "text")

        try:
            parsed = json.loads(raw_output)
        except json.JSONDecodeError as exc:
            logger.error("ResumeParserService got non-JSON response: %s", raw_output[:500])
            raise ResumeParsingError("Could not structure resume content — please try again") from exc

        try:
            return ResumeContent.model_validate(parsed)
        except Exception as exc:
            logger.error("ResumeParserService structured output failed validation: %s", parsed)
            raise ResumeParsingError("Structured resume content did not match the expected shape") from exc

    async def parse(self, file_bytes: bytes, mime_type: str) -> ResumeContent:
        raw_text = self.extract_text(file_bytes, mime_type)
        return await self.structure_text(raw_text)
