"""
Per-user, per-endpoint-family rate limiting for expensive (AI-calling)
endpoints. Uses a Redis fixed-window counter — simple, adequate for the
current traffic profile, easy to swap for a sliding window later without
changing the call sites (they only see `check_rate_limit`).

Fails OPEN (allows the request, logs a warning) if Redis is unreachable —
a rate-limiter outage should degrade gracefully, not take the whole API
down. This also means tests that don't spin up Redis still pass.

A fresh client is created per call rather than cached as a module-level
singleton: redis.asyncio's client ties its connection to the event loop
active when it first sends a command, and reusing it across a different
loop raises "Future attached to a different loop" / "Event loop is
closed". This is exactly the failure mode of `asyncio.run()`-per-call
patterns — which includes both pytest-asyncio (fresh loop per test) and
this project's own Celery tasks (tasks/job_sync.py, tasks/resume_processing.py
both call asyncio.run() per task invocation). Verified: this bug was
invisible in every prior test run because Redis was unreachable, so the
fail-open path was always taken before a real connection was ever
established; it surfaced only once tested against a real, running Redis.
"""
import logging
import uuid

import redis.asyncio as redis
from redis.exceptions import RedisError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Rate limit exceeded, retry after {retry_after_seconds}s")


async def check_rate_limit(user_id: uuid.UUID, bucket: str, limit_per_hour: int | None = None) -> None:
    """
    Raises RateLimitExceeded if the user has exceeded `limit_per_hour` calls
    to `bucket` (e.g. "resume_analysis", "resume_customization",
    "cover_letter") within the current hour window.
    """
    settings = get_settings()
    limit = limit_per_hour or settings.AI_CALL_RATE_LIMIT_PER_HOUR

    client = redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=1)
    try:
        key = f"ratelimit:{bucket}:{user_id}"

        current = await client.incr(key)
        if current == 1:
            await client.expire(key, 3600)

        if current > limit:
            ttl = await client.ttl(key)
            raise RateLimitExceeded(retry_after_seconds=max(ttl, 1))
    except RedisError:
        logger.warning("Rate limiter unavailable (Redis unreachable); allowing request for bucket=%s", bucket)
    finally:
        await client.aclose()
