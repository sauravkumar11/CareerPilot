"""
Dev/local convenience: create all tables directly from the ORM metadata.

Production deployments should use Alembic migrations instead
(`alembic upgrade head`) so schema changes are versioned and reversible.
Run with: `python -m scripts.init_db` from the backend/ directory.
"""
import asyncio

from app.db.base import Base
from app.db.session import engine
from app.domain import models  # noqa: F401


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created.")


if __name__ == "__main__":
    asyncio.run(main())
