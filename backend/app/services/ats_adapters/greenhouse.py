"""
Greenhouse Job Board API adapter.

Docs: https://developers.greenhouse.io/job-board.html
Public, unauthenticated, read-only endpoint:
  GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true

`company_identifier` is the Greenhouse "board token" (e.g. "stripe",
"airbnb", "cloudflare") — visible in a company's careers page URL, which is
what should be stored as Company.ats_identifier.
"""
from __future__ import annotations

from datetime import datetime

from app.services.ats_adapters.base import BaseATSAdapter, NormalizedPosting

GREENHOUSE_BASE_URL = "https://boards-api.greenhouse.io/v1/boards"


class GreenhouseAdapter(BaseATSAdapter):
    provider_name = "greenhouse"

    async def fetch_postings(self, company_identifier: str) -> list[NormalizedPosting]:
        url = f"{GREENHOUSE_BASE_URL}/{company_identifier}/jobs"
        data = await self._get_json(url, params={"content": "true"})

        postings: list[NormalizedPosting] = []
        for job in data.get("jobs", []):
            location = (job.get("location") or {}).get("name")
            posted_at = None
            if job.get("updated_at"):
                try:
                    posted_at = datetime.fromisoformat(job["updated_at"].replace("Z", "+00:00"))
                except ValueError:
                    posted_at = None

            postings.append(
                NormalizedPosting(
                    external_id=str(job["id"]),
                    title=job.get("title", "").strip(),
                    description_raw=job.get("content", "") or "",
                    location=location,
                    apply_url=job.get("absolute_url", ""),
                    department=", ".join(d["name"] for d in job.get("departments", []) if d.get("name")) or None,
                    posted_at=posted_at,
                    tags=[],
                    remote=bool(location and "remote" in location.lower()),
                )
            )
        return postings
