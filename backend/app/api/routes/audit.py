"""Audit endpoints — foundation read paths for the audit trail."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import TenantContext, get_tenant_context
from app.audit.service import AuditService
from app.db.session import get_session
from app.domain.enums import AuditEventType
from app.domain.schemas import AuditEventRead

router = APIRouter(prefix="/audit-events", tags=["audit"])


@router.get("", response_model=list[AuditEventRead])
async def list_audit_events(
    event_type: AuditEventType | None = None,
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant_context),
) -> list[AuditEventRead]:
    """List tenant-scoped audit events, newest first."""
    service = AuditService(session, company_id=tenant.company_id)
    events = await service.list(event_type=event_type, limit=limit, offset=offset)
    return [AuditEventRead.model_validate(e, from_attributes=True) for e in events]
