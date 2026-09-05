"""Seed entrypoints.

``seed_demo.py`` usage:

    VEXA_DB_URL=... uv run python -m app.data.seed   # seeds NovaScale AI

Seeding is deterministic by default (``VEXA_SEED_RANDOM_SEED``).
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.config import get_settings
from app.data.generator import seed_company
from app.db.models.tenancy import Company
from app.db.session import create_engine_and_sessionmaker


async def demo_seed(seed: int | None = None) -> Company:
    """Seed the NovaScale AI demo company into the configured database."""
    settings = get_settings()
    engine, maker = create_engine_and_sessionmaker()
    async with maker() as session:
        seed_int = settings.seed_random_seed if seed is None else seed

        existing = await session.scalar(select(Company).where(Company.name == "NovaScale AI"))
        if existing is not None:
            print(f"Company 'NovaScale AI' already exists (id={existing.id}); skipping.")
            return existing

        company = await seed_company(session, seed=seed_int, include_transactions=True)
        await session.commit()
        print(
            f"Seeded 'NovaScale AI' (id={company.id}) with financial data & "
            f"ground truth (seed={seed_int})."
        )
        return company


def main() -> None:
    company = asyncio.run(demo_seed())
    print(f"Done. company_id={company.id}")


if __name__ == "__main__":
    main()
