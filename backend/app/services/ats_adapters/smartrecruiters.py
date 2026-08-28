"""
SmartRecruiters Posting API adapter.

Docs: https://developers.smartrecruiters.com/docs/postings-api
Public, unauthenticated, read-only endpoint:
  GET https://api.smartrecruiters.com/v1/companies/{company_identifier}/postings

`company_identifier` is the SmartRecruiters company identifier (e.g.
"Cisco"), found in the company's SmartRecruiters careers page URL.
"""
from __future__ import annotations

from datetime import datetime

from app.services.ats_adapters.base import BaseATSAdapter, NormalizedPosting

SMARTRECRUITERS_BASE_URL = "https://api.smartrecruiters.com/v1/companies"


class SmartRecruitersAdapter(BaseATSAdapter):
    provider_name = "smartrecruiters"

    async def fetch_postings(self, company_identifier: str) -> list[NormalizedPosting]:
        postings: list[NormalizedPosting] = []
        offset = 0
        limit = 100

        while True:
            url = f"{SMARTRECRUITERS_BASE_URL}/{company_identifier}/postings"
            data = await self._get_json(url, params={"limit": limit, "offset": offset})
            batch = data.get("content", [])
            if not batch:
                break

            for job in batch:
                location_obj = job.get("location") or {}
                location = ", ".join(
                    part for part in [location_obj.get("city"), location_obj.get("country")] if part
                ) or None
                posted_at = None
                if job.get("releasedDate"):
                    try:
                        posted_at = datetime.fromisoformat(job["releasedDate"].replace("Z", "+00:00"))
                    except ValueError:
                        posted_at = None

                postings.append(
                    NormalizedPosting(
                        external_id=str(job.get("id")),
                        title=(job.get("name") or "").strip(),
                        description_raw=(job.get("jobAd", {}).get("sections", {}).get("jobDescription", {}) or {}).get(
                            "text", ""
                        ),
                        location=location,
                        apply_url=job.get("applyUrl") or job.get("ref", ""),
                        department=(job.get("department") or {}).get("label"),
                        posted_at=posted_at,
                        tags=[],
                        remote=bool(location_obj.get("remote")),
                    )
                )

            total = data.get("totalFound", len(batch))
            offset += limit
            if offset >= total:
                break

        return postings
