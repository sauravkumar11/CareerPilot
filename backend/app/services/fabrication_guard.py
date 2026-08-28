"""
Shared guardrail used by ResumeCustomizationService and CoverLetterService:
verifies that AI-generated content doesn't introduce employers, titles,
schools, skills, or project names absent from the user's source resume.

This is a real check, not just a prompt instruction — the prompt asks the
model to only reorganize/highlight, and this function verifies it actually
did. A prompt instruction alone is not a guarantee.
"""
import json
import re

from app.domain.schemas.resume import ResumeContent

_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+#.\-]{2,}")


class FabricationDetectedError(Exception):
    def __init__(self, suspect_terms: list[str]):
        self.suspect_terms = suspect_terms
        super().__init__(f"Generated content references terms not found in source resume: {suspect_terms}")


def _significant_words(text: str) -> set[str]:
    """Lowercased tokens of length >= 3, skipping common stopwords."""
    stopwords = {
        "the", "and", "for", "with", "that", "this", "from", "your", "our", "are", "was",
        "were", "have", "has", "had", "will", "would", "can", "could", "should", "role",
        "team", "company", "position", "job", "years", "experience", "work", "using",
        "including", "such", "into", "about", "you", "we", "they", "their", "its",
    }
    return {w.lower() for w in _WORD_RE.findall(text) if w.lower() not in stopwords}


def check_for_fabrication(
    source_content: ResumeContent,
    generated_text: str,
    *,
    extra_allowed_terms: set[str] | None = None,
) -> None:
    """
    Raises FabricationDetectedError if `generated_text` (a cover letter, or
    the serialized text of a customized resume) contains proper-noun-like
    terms — capitalized multi-char tokens — that don't appear anywhere in
    the source resume's factual tokens or free text. This intentionally
    only flags capitalized tokens (likely names/companies/technologies)
    to avoid false positives on ordinary connecting prose.
    """
    source_tokens = source_content.all_factual_tokens()
    # Cover every word anywhere in the source resume (contact info, dates,
    # locations, bullet text, etc.) — not just the curated "factual tokens"
    # subset — so legitimate restatements of source content are never
    # flagged, only genuinely new terms.
    full_source_text = json.dumps(source_content.model_dump())
    source_text_words = _significant_words(full_source_text)
    allowed = source_tokens | source_text_words | (extra_allowed_terms or set())

    # Only check capitalized tokens in the generated text (candidate proper
    # nouns: company names, technologies, schools) — lowercase connective
    # prose is not a fabrication risk.
    capitalized_tokens = re.findall(r"\b[A-Z][a-zA-Z0-9+#.\-]{2,}\b", generated_text)

    suspects = []
    for token in capitalized_tokens:
        lowered = token.lower()
        if lowered in allowed:
            continue
        # Allow common sentence-starter words and generic business terms.
        if lowered in _COMMON_ALLOWED_WORDS:
            continue
        suspects.append(token)

    # De-duplicate while preserving order.
    seen: set[str] = set()
    unique_suspects = []
    for s in suspects:
        if s.lower() not in seen:
            seen.add(s.lower())
            unique_suspects.append(s)

    if unique_suspects:
        raise FabricationDetectedError(unique_suspects)


_COMMON_ALLOWED_WORDS = {
    "i", "dear", "sincerely", "regards", "best", "hiring", "manager", "team",
    "engineering", "engineer", "software", "company", "role", "position",
    "thank", "you", "when", "which", "what", "why", "how", "as", "in", "at",
    "my", "your", "our", "this", "that", "these", "those",
}
