"""Exception routing and evidence-pack routing for autonomous close (spec sections 7, 9, 11, 12)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.close_workflow.types import ClosePolicy, ExceptionRoutingDecision
from app.db.models.exception import ExceptionRecord
from app.domain.enums import AutonomyLevel, ExceptionStatus
from app.evidence_graph.builder import FinancialEvidenceGraphBuilder
from app.evidence_graph.graph import FinancialEvidenceGraph
from app.evidence_graph.ranker import EvidenceRanker
from app.evidence_graph.serialization import (
    format_evidence_markdown,
    serialize_subgraph_json,
)
from app.evidence_graph.types import EvidenceNode, NodeType


class ExceptionRouter:
    """Evaluates exceptions against policy and determines autonomy level and routing path."""

    def __init__(self, policy: ClosePolicy | None = None) -> None:
        self.policy = policy or ClosePolicy()

    def route_exception(
        self, exception: ExceptionRecord, policy: ClosePolicy | None = None
    ) -> ExceptionRoutingDecision:
        """Route a single exception to AUTO_RESOLVE, HUMAN_REVIEW, or CFO_ESCALATION."""
        pol = policy or self.policy
        impact = exception.financial_impact or Decimal("0.00")
        conf = exception.confidence or Decimal("1.0000")

        # Collect linked evidence identifiers
        evidence_ids: list[str] = []
        if exception.evidence:
            evidence_ids = [str(ev.evidence_ref_id) for ev in exception.evidence]

        # 1. CFO Escalation: High financial impact or severe anomaly types (spec section 11/12)
        if impact >= pol.materiality_threshold or exception.type in pol.blocking_exception_types:
            routing = "CFO_ESCALATION"
            autonomy = AutonomyLevel.RECOMMEND
            # Resolved or auto-resolved exceptions are not blocking
            is_blocking = exception.status not in (
                ExceptionStatus.RESOLVED,
                ExceptionStatus.AUTO_RESOLVED,
            )
            reason = (
                f"Exception '{exception.type.value}' with impact {impact} {exception.currency} "
                f"requires CFO escalation due to materiality or high-risk classification."
            )
        # 2. Human Review: Impact above auto-resolve threshold or confidence below threshold
        elif impact > pol.max_auto_resolution_amount or conf < pol.min_confidence:
            routing = "HUMAN_REVIEW"
            autonomy = AutonomyLevel.STAGE
            is_blocking = exception.status not in (
                ExceptionStatus.RESOLVED,
                ExceptionStatus.AUTO_RESOLVED,
            )
            reason = (
                f"Impact {impact} exceeds auto-resolution limit ({pol.max_auto_resolution_amount}) "
                f"or confidence ({conf}) is below policy threshold ({pol.min_confidence})."
            )
        # 3. Auto-Resolve: Low-risk, high confidence within policy limits
        else:
            routing = "AUTO_RESOLVE"
            autonomy = AutonomyLevel.EXECUTE
            is_blocking = False
            reason = (
                f"Routine exception within policy auto-resolution limit "
                f"({impact} <= {pol.max_auto_resolution_amount})."
            )

        return ExceptionRoutingDecision(
            exception_id=exception.id,
            exception_type=exception.type,
            severity=exception.severity,
            financial_impact=impact,
            routing=routing,
            autonomy_level=autonomy,
            is_blocking=is_blocking,
            reason=reason,
            evidence_ids=evidence_ids,
            evidence_summary=exception.root_cause,
        )

    def route_all(
        self,
        exceptions: Sequence[ExceptionRecord],
        policy: ClosePolicy | None = None,
    ) -> list[ExceptionRoutingDecision]:
        """Route a collection of exceptions deterministically."""
        return [self.route_exception(exc, policy) for exc in exceptions]


class EvidencePackRouter:
    """Generates structured evidence packs for exceptions using the Financial Evidence Graph."""

    def __init__(self, ranker: EvidenceRanker | None = None) -> None:
        self.ranker = ranker or EvidenceRanker()

    async def generate_evidence_pack(
        self,
        session: AsyncSession,
        company_id: uuid.UUID,
        exception: ExceptionRecord,
        graph: FinancialEvidenceGraph | None = None,
    ) -> dict[str, Any]:
        """Generate a complete evidence pack (JSON & Markdown) for an exception."""
        ev_graph = graph
        if ev_graph is None:
            builder = FinancialEvidenceGraphBuilder(session, company_id)
            ev_graph = await builder.build()

        # Gather evidence subgraph
        subgraph = ev_graph.explain_exception(exception.id)
        focus_node_id = EvidenceNode.make_id(NodeType.EXCEPTION, str(exception.id))

        if not subgraph.nodes:
            # Fallback to source references
            for ntype, candidate in [
                (NodeType.INVOICE, exception.source_invoice_id),
                (NodeType.PURCHASE_ORDER, exception.source_po_id),
                (NodeType.PAYMENT, exception.source_payment_id),
                (NodeType.BANK_TRANSACTION, exception.source_bank_txn_id),
                (NodeType.GOODS_RECEIPT, exception.source_receipt_id),
                (NodeType.JOURNAL_ENTRY, exception.source_journal_entry_id),
            ]:
                if candidate:
                    cand_id = EvidenceNode.make_id(ntype, str(candidate))
                    if ev_graph.has_node(cand_id):
                        subgraph = ev_graph.get_neighborhood(cand_id, radius=2)
                        focus_node_id = cand_id
                        break

        # Rank evidence
        ranked_items = EvidenceRanker.rank_subgraph(
            subgraph,
            focus_node_id=focus_node_id,
            query_context={"monetary_impact": str(exception.financial_impact)},
        )

        # Serialize
        json_pack = serialize_subgraph_json(subgraph)
        markdown_dossier = format_evidence_markdown(
            focus_node_id=focus_node_id,
            subgraph=subgraph,
            ranked_items=ranked_items,
            query_type=exception.type.value,
            company_id=str(company_id),
        )

        return {
            "exception_id": str(exception.id),
            "exception_type": exception.type.value,
            "financial_impact": str(exception.financial_impact),
            "ranked_nodes_count": len(ranked_items),
            "evidence_json": json_pack,
            "markdown_dossier": markdown_dossier,
        }
