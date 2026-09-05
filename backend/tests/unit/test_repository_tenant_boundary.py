"""Tenant boundary enforcement (spec section 30).

Company A must never read, list, count, or write Company B's rows through
the repository layer.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.counterparty import Vendor
from app.db.models.tenancy import Company
from app.db.repository import CompanyRepository, TenantRepository


class VendorRepository(TenantRepository):
    model = Vendor


async def _make_company(db: AsyncSession, name: str) -> Company:
    company = Company(name=name, base_currency="USD", is_active=True)
    db.add(company)
    await db.flush()
    return company


async def _make_vendor(db: AsyncSession, company_id: uuid.UUID, name: str) -> Vendor:
    vendor = Vendor(company_id=company_id, name=name)
    db.add(vendor)
    await db.flush()
    return vendor


async def test_repository_scopes_reads_to_tenant(db: AsyncSession) -> None:
    company_a = await _make_company(db, "Company A")
    company_b = await _make_company(db, "Company B")
    vendor_a = await _make_vendor(db, company_a.id, "Vendor A")
    await _make_vendor(db, company_b.id, "Vendor B")
    await db.flush()

    repo_a = VendorRepository(db, company_id=company_a.id)

    # get() must not leak company B's rows.
    assert await repo_a.get(vendor_a.id) is not None
    # list() must only return tenant A's rows.
    rows = await repo_a.list()
    assert {v.name for v in rows} == {"Vendor A"}
    # count() must respect the boundary.
    assert await repo_a.count() == 1


async def test_repository_add_forces_tenant_column(db: AsyncSession) -> None:
    company_a = await _make_company(db, "Company A")
    company_b = await _make_company(db, "Company B")

    repo_a = VendorRepository(db, company_id=company_a.id)
    # Caller tries to smuggle company B's tenant id via the object.
    smuggled = Vendor(company_id=company_b.id, name="Smuggled Vendor")
    await repo_a.add(smuggled)

    assert smuggled.company_id == company_a.id, "tenant column must be forced"


async def test_company_repository_lists_all(db: AsyncSession) -> None:
    await _make_company(db, "Company A")
    await _make_company(db, "Company B")
    await db.flush()

    repo = CompanyRepository(db)
    companies = await repo.list()
    assert len(companies) == 2
