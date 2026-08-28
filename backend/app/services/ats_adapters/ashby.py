"""
Ashby Job Board API adapter.

Docs: https://developers.ashbyhq.com/reference/jobpostingsync
Public, unauthenticated, read-only endpoint (POST, despite being a read):
  POST https://api.ashbyhq.com/posting-api/job-board/{job_board_name}

`company_identifier` is the Ashby job board name (e.g. "ramp"), visible in
a company's Ashby careers page URL: jobs.ashbyhq.com/{job_board_name}.
"""
from __future__ import annotations

from datetime import datetime

from app.services.ats_adapters.base import BaseATSAdapter, NormalizedPosting

ASHBY_BASE_URL = "https://api.ashbyhq.com/posting-api/job-board"


class AshbyAdapter(BaseATSAdapter):
    provider_name = "ashby"

    async def fetch_postings(self, company_identifier: str) -> list[NormalizedPosting]:
        url = f"{ASHBY_BASE_URL}/{company_identifier}"
        response = await self.client.post(url, params={"includeCompensation": "true"})
        response.raise_for_status()
        data = response.json()

        postings: list[NormalizedPosting] = []
        for job in data.get("jobs", []):
            posted_at = None
            if job.get("publishedAt"):
                try:
                    posted_at = datetime.fromisoformat(job["publishedAt"].replace("Z", "+00:00"))
                except ValueError:
                    posted_at = None

            comp = job.get("compensation") or {}
            summary_components = comp.get("summaryComponents") or []
            salary_min = salary_max = None
            currency = None
            for component in summary_components:
                if component.get("minValue") is not None:
                    salary_min = int(component["minValue"])
                    salary_max = int(component.get("maxValue") or component["minValue"])
                    currency = component.get("currencyCode")
                    break

            postings.append(
                NormalizedPosting(
                    external_id=str(job.get("id")),
                    title=job.get("title", "").strip(),
                    description_raw=job.get("descriptionPlain") or job.get("descriptionHtml", "") or "",
                    location=job.get("location"),
                    apply_url=job.get("jobUrl") or job.get("applyUrl", ""),
                    department=job.get("department"),
                    posted_at=posted_at,
                    tags=job.get("employmentType", "") and [job["employmentType"]] or [],
                    salary_min=salary_min,
                    salary_max=salary_max,
                    salary_currency=currency,
                    remote=bool(job.get("isRemote")),
                )
            )
        return postings
