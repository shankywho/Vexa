"""Tenancy & identity models (spec sections 29-30).

Every financial object carries ``company_id``. Tenant context must always
come from the authenticated request context — never from agent-supplied
values. Enforcement lives in the repository layer.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPkMixin
from app.domain.enums import Role


class Company(UUIDPkMixin, TimestampMixin, Base):
    """A tenant — the top-level boundary for all financial data."""

    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(255))
    tax_id: Mapped[str | None] = mapped_column(String(64), index=True)
    base_currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    fiscal_year_end: Mapped[str | None] = mapped_column(String(5))
    settings: Mapped[dict | None] = mapped_column(
        "settings_json", Text
    )  # JSON-encoded company policy/settings
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    users: Mapped[list[User]] = relationship(back_populates="company")


class User(UUIDPkMixin, TimestampMixin, Base):
    """A user account attached to a company (tenant)."""

    __tablename__ = "users"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    full_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role, name="role"), default=Role.VIEWER, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    company: Mapped[Company] = relationship(back_populates="users")

    __table_args__ = (UniqueConstraint("company_id", "email", name="uq_users_company_email"),)


class RoleAssignment(UUIDPkMixin, TimestampMixin, Base):
    """Additional role assignments beyond the user's primary role."""

    __tablename__ = "role_assignments"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[Role] = mapped_column(Enum(Role, name="role"), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "user_id", "company_id", "role", name="uq_role_assignments_user_company_role"
        ),
    )
