"""
Every ATS adapter implements `fetch_postings()` and returns a list of
`NormalizedPosting`. This is the seam that lets the job discovery service
stay ignorant of which ATS a company uses.

Only public, documented job-board endpoints are used here (Greenhouse,
Lever, Ashby and SmartRecruiters all publish read-only public job-board
JSON APIs intended for consumption by third parties). No authentication,
scraping of HTML, or CAPTCHA bypass is involved. Adding a new provider
that requires login or violates its ToS should NOT be added here.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


@dataclass
class NormalizedPosting:
    external_id: str
    title: str
    description_raw: str
    location: Optional[str]
    apply_url: str
    department: Optional[str] = None
    posted_at: Optional[datetime] = None
    tags: list[str] = field(default_factory=list)
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    remote: Optional[bool] = None


class BaseATSAdapter(ABC):
    provider_name: str

    def __init__(self, http_client: httpx.AsyncClient | None = None):
        self._client = http_client
        self._owns_client = http_client is None

    async def __aenter__(self) -> "BaseATSAdapter":
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=20.0, headers={"User-Agent": "CareerPilotAI/1.0"})
        return self

    async def __aexit__(self, *exc):
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("ATS adapter must be used as an async context manager")
        return self._client

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
    )
    async def _get_json(self, url: str, params: dict | None = None) -> dict:
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    @abstractmethod
    async def fetch_postings(self, company_identifier: str) -> list[NormalizedPosting]:
        """Fetch and normalize all currently open postings for a company."""
        raise NotImplementedError
