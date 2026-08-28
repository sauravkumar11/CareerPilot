"""
Lever Postings API adapter.

Docs: https://github.com/lever/postings-api
Public, unauthenticated, read-only endpoint:
  GET https://api.lever.co/v0/postings/{company}?mode=json

`company_identifier` is the Lever site identifier (e.g. "netflix"),
visible in a company's Lever careers page URL.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.services.ats_adapters.base import BaseATSAdapter, NormalizedPosting

LEVER_BASE_URL = "https://api.lever.co/v0/postings"


class LeverAdapter(BaseATSAdapter):
    provider_name = "lever"

    async def fetch_postings(self, company_identifier: str) -> list[NormalizedPosting]:
        url = f"{LEVER_BASE_URL}/{company_identifier}"
        data = await self._get_json(url, params={"mode": "json"})

        postings: list[NormalizedPosting] = []
        for job in data:
            categories = job.get("categories", {}) or {}
            location = categories.get("location")
            posted_at = None
            if job.get("createdAt"):
                try:
                    posted_at = datetime.fromtimestamp(int(job["createdAt"]) / 1000, tz=timezone.utc)
                except (ValueError, OSError):
                    posted_at = None

            description_parts = [job.get("descriptionPlain", "") or job.get("description", "") or ""]
            for list_block in job.get("lists", []) or []:
                if list_block.get("text"):
                    description_parts.append(list_block["text"])

            postings.append(
                NormalizedPosting(
                    external_id=str(job["id"]),
                    title=job.get("text", "").strip(),
                    description_raw="\n\n".join(p for p in description_parts if p),
                    location=location,
                    apply_url=job.get("applyUrl") or job.get("hostedUrl", ""),
                    department=categories.get("team") or categories.get("department"),
                    posted_at=posted_at,
                    tags=[t for t in [categories.get("commitment")] if t],
                    remote=bool(location and "remote" in location.lower()),
                )
            )
        return postings
