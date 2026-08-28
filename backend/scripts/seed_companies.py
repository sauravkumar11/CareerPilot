"""
Seeds the companies table with a starter set of well-known companies that
publish jobs through one of the four supported public ATS APIs.

Board tokens / identifiers can change over time and vary by company —
verify against the company's live careers page before relying on this list
in production. Run with: `python -m scripts.seed_companies`.
"""
import asyncio

from app.db.session import AsyncSessionLocal
from app.repositories.company_repository import CompanyRepository
from slugify import slugify

SEED_COMPANIES = [
    # (name, ats_provider, ats_identifier, website)
    ("Stripe", "greenhouse", "stripe", "https://stripe.com"),
    ("Airbnb", "greenhouse", "airbnb", "https://www.airbnb.com"),
    ("Cloudflare", "greenhouse", "cloudflare", "https://www.cloudflare.com"),
    ("Databricks", "greenhouse", "databricks", "https://www.databricks.com"),
    ("Anthropic", "greenhouse", "anthropic", "https://www.anthropic.com"),
    ("Netflix", "lever", "netflix", "https://www.netflix.com"),
    ("Figma", "greenhouse", "figma", "https://www.figma.com"),
    ("Snowflake", "lever", "snowflake", "https://www.snowflake.com"),
]


async def main() -> None:
    async with AsyncSessionLocal() as session:
        repo = CompanyRepository(session)
        created = 0
        for name, provider, identifier, website in SEED_COMPANIES:
            slug = slugify(name)
            if await repo.get_by_slug(slug):
                continue
            await repo.create(
                name=name,
                slug=slug,
                website=website,
                ats_provider=provider,
                ats_identifier=identifier,
            )
            created += 1
        await repo.commit()
        print(f"Seeded {created} new companies ({len(SEED_COMPANIES) - created} already existed).")


if __name__ == "__main__":
    asyncio.run(main())
