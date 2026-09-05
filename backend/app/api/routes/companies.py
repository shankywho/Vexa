"""Company (tenant) endpoints — foundation CRUD.

Tenant creation is the bootstrap step; almost every other financial object
is tenant-scoped to a company (spec section 30).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.tenancy import Company
from app.db.session import get_session
from app.domain.schemas import CompanyCreate, CompanyRead

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
async def create_company(
    payload: CompanyCreate, session: AsyncSession = Depends(get_session)
) -> Company:
    """Create a new company (tenant)."""
    company = Company(**payload.model_dump())
    session.add(company)
    await session.flush()
    return company


@router.get("", response_model=list[CompanyRead])
async def list_companies(session: AsyncSession = Depends(get_session)) -> list[Company]:
    """List all companies."""
    result = await session.scalars(select(Company).order_by(Company.name))
    return list(result.all())


@router.get("/{company_id}", response_model=CompanyRead)
async def get_company(
    company_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Company:
    """Fetch a single company."""
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company
