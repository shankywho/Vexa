"""Verification service providing high-level verification operations."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.close_workflow.types import ClosePolicy
from app.db.repository import ExceptionRepository
from app.evidence_graph.graph import FinancialEvidenceGraph
from app.investigation.dossier_builder import EvidenceDossierBuilder
from app.investigation.service import InvestigationService
from app.investigation.types import InvestigationFinding
from app.verification.agent import VerificationAgent
from app.verification.types import VerificationRequest, VerificationResult


class VerificationService:
    """Service providing independent verification workflows for financial exceptions."""

    def __init__(self, session: AsyncSession, company_id: uuid.UUID) -> None:
        self.session = session
        self.company_id = company_id
        self.dossier_builder = EvidenceDossierBuilder(session, company_id)
        self.investigation_service = InvestigationService(session, company_id)
        self.agent = VerificationAgent(session, company_id)
        self.exc_repo = ExceptionRepository(session, company_id)

    async def verify_exception(
        self,
        exception_id: uuid.UUID,
        policy: ClosePolicy | None = None,
        graph: FinancialEvidenceGraph | None = None,
        finding: InvestigationFinding | None = None,
    ) -> VerificationResult:
        """Verify an investigation finding independently against database ground truth."""
        active_policy = policy or ClosePolicy()

        # 1. If finding not provided, run investigation first
        if finding is None:
            finding = await self.investigation_service.investigate_exception(
                exception_id=exception_id,
                policy=active_policy,
                graph=graph,
            )

        # 2. Build dossier for independent verification
        dossier = await self.dossier_builder.build_dossier(exception_id=exception_id, graph=graph)

        # 3. Create request and execute verification
        request = VerificationRequest(
            exception_id=exception_id,
            company_id=self.company_id,
            close_run_id=dossier.close_run_id,
            finding=finding,
            dossier=dossier,
            policy=active_policy,
        )

        return await self.agent.verify(request)
