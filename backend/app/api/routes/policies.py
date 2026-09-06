"""Financial close policy management endpoints (spec section 12)."""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, status

from app.api.dependencies import TenantContext, get_tenant_context
from app.close_workflow.types import ClosePolicy
from app.domain.schemas import ClosePolicyRead, ClosePolicyUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/policies", tags=["policies"])

# Tenant-scoped close policies cache
_tenant_policies: dict[uuid.UUID, ClosePolicyRead] = {}


def _get_or_create_policy(company_id: uuid.UUID) -> ClosePolicyRead:
    if company_id not in _tenant_policies:
        default = ClosePolicy()
        _tenant_policies[company_id] = ClosePolicyRead(
            policy_version_id=default.policy_version_id,
            max_auto_resolution_amount=str(default.max_auto_resolution_amount),
            materiality_threshold=str(default.materiality_threshold),
            min_confidence=str(default.min_confidence),
            approval_timeout_hours=24,
            required_approvers_material=["CFO", "CONTROLLER"],
        )
    return _tenant_policies[company_id]


@router.get("", response_model=ClosePolicyRead)
async def get_policy(
    tenant: TenantContext = Depends(get_tenant_context),
) -> ClosePolicyRead:
    """Retrieve the active financial close policy for the current tenant."""
    return _get_or_create_policy(tenant.company_id)


@router.post("", response_model=ClosePolicyRead, status_code=status.HTTP_200_OK)
async def update_policy(
    payload: ClosePolicyUpdate,
    tenant: TenantContext = Depends(get_tenant_context),
) -> ClosePolicyRead:
    """Update financial close policy parameters and thresholds."""
    current = _get_or_create_policy(tenant.company_id)
    updated_dict = current.model_dump()

    if payload.max_auto_resolution_amount is not None:
        updated_dict["max_auto_resolution_amount"] = str(
            Decimal(payload.max_auto_resolution_amount)
        )
    if payload.materiality_threshold is not None:
        updated_dict["materiality_threshold"] = str(Decimal(payload.materiality_threshold))
    if payload.min_confidence is not None:
        updated_dict["min_confidence"] = str(Decimal(payload.min_confidence))
    if payload.approval_timeout_hours is not None:
        updated_dict["approval_timeout_hours"] = payload.approval_timeout_hours
    if payload.required_approvers_material is not None:
        updated_dict["required_approvers_material"] = payload.required_approvers_material

    updated_policy = ClosePolicyRead(**updated_dict)
    _tenant_policies[tenant.company_id] = updated_policy
    logger.info("Updated close policy for company %s", tenant.company_id)
    return updated_policy
