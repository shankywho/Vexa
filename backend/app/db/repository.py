"""Repository layer with tenant isolation (spec section 30).

Every financial object carries ``company_id``. Tenant context must come
from the authenticated request context — never from user/agent-supplied
values. This repository base enforces the boundary at query time.

Tenant scoping strategy: a repository is constructed with an explicit
``company_id`` and all queries are automatically filtered to that company.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.db.base import Base
from app.db.models.tenancy import Company


class TenantBoundaryError(ValueError):
    """Raised when an operation crosses the tenant boundary."""


class TenantRepository:
    """Base repository enforcing the company/tenant boundary.

    Subclasses declare their scoped model via ``model`` and may constrain
    ``company_attr`` when the column name differs from ``company_id``.
    """

    model: type[Base] | None = None
    company_attr: str = "company_id"

    def __init__(self, session: AsyncSession, company_id: uuid.UUID) -> None:
        if self.model is None:
            raise TypeError(f"{type(self).__name__} must define 'model' before use")
        self.session = session
        self.company_id = company_id
        self._company_column: InstrumentedAttribute = getattr(self.model, self.company_attr)

    def _tenant_filter(self, *criteria) -> list:  # noqa: ANN002
        """Return the tenant filter combined with caller criteria."""
        return [self._company_column == self.company_id, *criteria]

    async def get(self, obj_id: uuid.UUID) -> Base | None:
        """Fetch a row by id, scoped to the tenant. Returns None if the row
        belongs to a different tenant (no cross-tenant leakage)."""
        stmt = select(self.model).where(
            self._company_column == self.company_id, self.model.id == obj_id
        )
        return await self.session.scalar(stmt)

    async def list(
        self, *criteria, limit: int = 100, offset: int = 0, order_by: str | None = None
    ) -> Sequence[Base]:
        """List rows scoped to the tenant."""
        stmt = select(self.model).where(*self._tenant_filter(*criteria))
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.scalars(stmt)
        return result.all()

    async def count(self, *criteria) -> int:
        """Count rows scoped to the tenant."""
        from sqlalchemy import func

        stmt = select(func.count()).select_from(self.model).where(*self._tenant_filter(*criteria))
        return int(await self.session.scalar(stmt) or 0)

    async def add(self, obj: Base) -> Base:
        """Persist a new row, forcing the tenant column to the repository's
        company so a caller can never write another tenant's data."""
        if hasattr(obj, self.company_attr):
            setattr(obj, self.company_attr, self.company_id)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def delete(self, obj: Base) -> None:
        """Delete a row (must already be tenant-scoped)."""
        await self.session.delete(obj)


class CompanyRepository(TenantRepository):
    """Repository for company-scoped rows that do not themselves carry a
    company_id (i.e. the Company table). Used with a ``None`` company id."""

    model = Company

    def __init__(self, session: AsyncSession, company_id: uuid.UUID | None = None) -> None:
        self.session = session
        self.company_id = company_id
        self._company_column = None  # type: ignore[assignment]

    def _tenant_filter(self, *criteria):  # noqa: ANN002
        return list(criteria)
