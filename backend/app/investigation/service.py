"""Investigation service providing high-level interface for exception investigations."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.close_workflow.types import ClosePolicy
from app.db.models.agent import AgentRun
from app.db.repository import AgentRunRepository, ExceptionRepository
from app.evidence_graph.builder import FinancialEvidenceGraphBuilder
from app.evidence_graph.graph import FinancialEvidenceGraph
from app.investigation.agent import CFOInvestigationAgent
from app.investigation.dossier_builder import EvidenceDossierBuilder
from app.investigation.llm_provider import LLMProvider
from app.investigation.prompt import PROMPT_VERSION_ID
from app.investigation.types import (
    InvestigationFinding,
    InvestigationRequest,
)


class InvestigationService:
    """Service providing end-to-end exception investigation workflows."""

    def __init__(self, session: AsyncSession, company_id: uuid.UUID) -> None:
        self.session = session
        self.company_id = company_id
        self.dossier_builder = EvidenceDossierBuilder(session, company_id)
        self.exc_repo = ExceptionRepository(session, company_id)
        self.agent_repo = AgentRunRepository(session, company_id)

    async def investigate_exception(
        self,
        exception_id: uuid.UUID,
        policy: ClosePolicy | None = None,
        provider: LLMProvider | None = None,
        graph: FinancialEvidenceGraph | None = None,
        timeout_seconds: float = 10.0,
    ) -> InvestigationFinding:
        """Investigate a single exception using a bounded evidence dossier."""
        # 1. Build bounded dossier
        dossier = await self.dossier_builder.build_dossier(exception_id=exception_id, graph=graph)

        # 2. Formulate request
        request = InvestigationRequest(
            exception_id=exception_id,
            company_id=self.company_id,
            close_run_id=dossier.close_run_id,
            dossier=dossier,
            policy=policy or ClosePolicy(),
            prompt_version_id=PROMPT_VERSION_ID,
            timeout_seconds=timeout_seconds,
        )

        # 3. Execute investigation
        agent = CFOInvestigationAgent(
            session=self.session,
            company_id=self.company_id,
            provider=provider,
        )
        return await agent.investigate(request)

    async def investigate_close_run(
        self,
        close_run_id: uuid.UUID,
        policy: ClosePolicy | None = None,
        provider: LLMProvider | None = None,
        limit: int | None = None,
    ) -> list[InvestigationFinding]:
        """Investigate all exceptions associated with a close run."""
        exceptions = await self.exc_repo.list_by_close_run(close_run_id)
        if limit:
            exceptions = list(exceptions)[:limit]

        if not exceptions:
            return []

        # Build graph once for all exceptions in close run
        builder = FinancialEvidenceGraphBuilder(self.session, self.company_id)
        graph = await builder.build()

        findings: list[InvestigationFinding] = []
        for exc in exceptions:
            finding = await self.investigate_exception(
                exception_id=exc.id,
                policy=policy,
                provider=provider,
                graph=graph,
            )
            findings.append(finding)

        return findings

    async def get_agent_run(self, run_id: uuid.UUID) -> AgentRun | None:
        """Retrieve agent run with all executed steps."""
        return await self.agent_repo.get_with_steps(run_id)

    async def list_agent_runs_for_exception(self, exception_id: uuid.UUID) -> Sequence[AgentRun]:
        """List historical agent runs for an exception."""
        return await self.agent_repo.list_by_exception(exception_id)

    async def list_agent_runs_for_close_run(self, close_run_id: uuid.UUID) -> Sequence[AgentRun]:
        """List all agent runs for a close run."""
        return await self.agent_repo.list_by_close_run(close_run_id)
