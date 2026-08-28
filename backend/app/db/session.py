"""
Async database engine and session factory.

Uses SQLAlchemy 2.0 async ORM with asyncpg. `get_db` is the FastAPI
dependency every request-scoped repository/service should use.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

# pool_size/max_overflow are QueuePool-only kwargs. SQLite's async engine
# (used by the test suite via DATABASE_URL=sqlite+aiosqlite:///:memory:)
# defaults to StaticPool, which rejects them outright — this used to break
# every test at import time. Postgres (production) still gets pooling.
_engine_kwargs: dict = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,
}
if not settings.DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
