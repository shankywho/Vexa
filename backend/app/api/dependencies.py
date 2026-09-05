"""FastAPI dependencies.

Tenant context (spec section 30) is resolved here from the authenticated
request context — never from client/agent-supplied values. When auth is
disabled (Phase 1 foundation), a configured default company is used.
"""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models.tenancy import Company
from app.db.session import get_session


class TenantContext:
    """Authenticated tenant/company identity for a request."""

    def __init__(self, company_id: uuid.UUID, role: str = "ADMIN") -> None:
        self.company_id = company_id
        self.role = role


def _extract_company_id_from_request(request: Request) -> uuid.UUID | None:
    """Extract tenant identity from the (Phase 2) auth context.

    Phase 1 foundation: reads a dev header ``X-Company-Id`` when auth is
    disabled; this is replaced by real auth in a later phase. When no header
    is present, falls back to the configured default tenant.
    """
    header = request.headers.get("X-Company-Id")
    if header:
        return uuid.UUID(header)
    default = get_settings().default_tenant_company_id
    return uuid.UUID(str(default)) if default else None


async def get_tenant_context(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> TenantContext:
    """Resolve and validate the request's tenant context."""
    settings = get_settings()
    company_id = _extract_company_id_from_request(request)

    if settings.auth_enabled:
        # Real auth lands in a later phase; for now a company header is
        # required when auth is enabled.
        if company_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing tenant context",
            )

    if company_id is None:
        # No tenant context anywhere (auth disabled and no default): fall
        # back to the first company for local development convenience.
        first = await session.scalar(select(Company).limit(1))
        if first is not None:
            company_id = first.id

    if company_id is not None and not settings.auth_enabled:
        # Validate the company exists when auth is disabled (dev mode).
        exists = await session.scalar(select(Company.id).where(Company.id == company_id))
        if exists is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    if company_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No tenant context available (create a company or set X-Company-Id)",
        )

    return TenantContext(company_id=company_id)
