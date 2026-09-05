"""Builder for bounded EvidenceDossier (spec sections 10, 11, 21-25).

Assembles the bounded financial evidence dossier for an exception:
- Retrieves the exception record and linked evidence
- Queries the Financial Evidence Graph around the exception/primary record
- Explicitly establishes the set of valid record IDs and evidence IDs
- Formats structured JSON and LLM-ready Markdown context
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import ExceptionRepository
from app.evidence_graph.builder import FinancialEvidenceGraphBuilder
from app.evidence_graph.graph import FinancialEvidenceGraph
from app.evidence_graph.ranker import EvidenceRanker
from app.evidence_graph.serialization import format_evidence_markdown
from app.evidence_graph.types import EvidenceNode, NodeType
from app.investigation.types import EvidenceDossier


class EvidenceDossierBuilder:
    """Constructs bounded financial evidence dossiers for the Investigation Agent."""

    def __init__(self, session: AsyncSession, company_id: uuid.UUID) -> None:
        self.session = session
        self.company_id = company_id
        self.exc_repo = ExceptionRepository(session, company_id)

    async def build_dossier(
        self,
        exception_id: uuid.UUID,
        graph: FinancialEvidenceGraph | None = None,
        radius: int = 2,
    ) -> EvidenceDossier:
        """Assemble a bounded evidence dossier for a given exception."""
        exception = await self.exc_repo.get_with_evidence(exception_id)
        if not exception:
            raise ValueError(f"Exception {exception_id} not found for company {self.company_id}")

        ev_graph = graph
        if ev_graph is None:
            builder = FinancialEvidenceGraphBuilder(self.session, self.company_id)
            ev_graph = await builder.build()

        exc_node_id = EvidenceNode.make_id(NodeType.EXCEPTION, str(exception.id))
        focus_node_id = exc_node_id

        # 1. Attempt graph explanation from exception node
        subgraph = ev_graph.explain_exception(exception.id)

        # 2. Fallback to primary candidate record if exception node is disconnected
        candidates = [
            (NodeType.INVOICE, exception.source_invoice_id),
            (NodeType.PURCHASE_ORDER, exception.source_po_id),
            (NodeType.PAYMENT, exception.source_payment_id),
            (NodeType.BANK_TRANSACTION, exception.source_bank_txn_id),
            (NodeType.GOODS_RECEIPT, exception.source_receipt_id),
            (NodeType.JOURNAL_ENTRY, exception.source_journal_entry_id),
        ]

        if not subgraph.nodes:
            for ntype, cand_uuid in candidates:
                if cand_uuid:
                    cand_id = EvidenceNode.make_id(ntype, str(cand_uuid))
                    if ev_graph.has_node(cand_id):
                        subgraph = ev_graph.get_neighborhood(cand_id, radius=radius)
                        focus_node_id = cand_id
                        break

        # 3. Collect valid record IDs and evidence IDs
        valid_record_ids: set[str] = set()
        valid_evidence_ids: set[str] = set()

        # Add exception itself
        valid_record_ids.add(str(exception.id))
        valid_evidence_ids.add(exc_node_id)

        # Add candidate direct source IDs
        for _, cand_uuid in candidates:
            if cand_uuid:
                valid_record_ids.add(str(cand_uuid))

        vendor_id = getattr(exception, "vendor_id", None)
        if vendor_id:
            valid_record_ids.add(str(vendor_id))
            valid_evidence_ids.add(EvidenceNode.make_id(NodeType.VENDOR, str(vendor_id)))
        customer_id = getattr(exception, "customer_id", None)
        if customer_id:
            valid_record_ids.add(str(customer_id))
            valid_evidence_ids.add(EvidenceNode.make_id(NodeType.CUSTOMER, str(customer_id)))

        # Add linked evidence records
        if exception.evidence:
            for ev in exception.evidence:
                if ev.evidence_ref_id:
                    valid_evidence_ids.add(str(ev.evidence_ref_id))
                    valid_record_ids.add(str(ev.evidence_ref_id))
                if ev.id:
                    valid_evidence_ids.add(str(ev.id))

        # Add all nodes in subgraph
        primary_record: dict[str, Any] = {}
        related_records: list[dict[str, Any]] = []

        for node in subgraph.nodes:
            valid_evidence_ids.add(node.id)
            valid_record_ids.add(node.record_id)
            node_dict = {
                "node_id": node.id,
                "node_type": node.node_type.value,
                "record_id": node.record_id,
                "label": node.label,
                "properties": node.properties,
            }
            if node.id == focus_node_id or (
                focus_node_id == exc_node_id
                and node.node_type != NodeType.EXCEPTION
                and not primary_record
            ):
                primary_record = node_dict
            else:
                related_records.append(node_dict)

        # If primary record still empty, construct minimal from exception
        if not primary_record:
            primary_record = {
                "node_id": exc_node_id,
                "node_type": "exception",
                "record_id": str(exception.id),
                "label": f"Exception {exception.id}",
                "properties": {
                    "type": exception.type.value,
                    "severity": exception.severity.value,
                    "financial_impact": str(exception.financial_impact),
                    "description": exception.description,
                },
            }

        # 4. Rank evidence nodes
        ranked_items = EvidenceRanker.rank_subgraph(
            subgraph,
            focus_node_id=focus_node_id,
            query_context={"monetary_impact": str(exception.financial_impact)},
        )

        # 5. Format LLM markdown dossier
        markdown_dossier = format_evidence_markdown(
            focus_node_id=focus_node_id,
            subgraph=subgraph,
            ranked_items=ranked_items,
            query_type=exception.type.value,
            company_id=str(self.company_id),
        )

        # 6. Serialize edges
        edges_data = [
            {
                "id": edge.id,
                "source": edge.source_id,
                "target": edge.target_id,
                "edge_type": edge.edge_type.value,
                "properties": edge.properties,
            }
            for edge in subgraph.edges
        ]

        ranked_nodes_data = [
            {
                "node_id": item.node.id,
                "node_type": item.node.node_type.value,
                "score": float(item.score),
                "label": item.node.label,
                "relevance_reason": item.relevance_reason,
            }
            for item in ranked_items
        ]

        return EvidenceDossier(
            exception_id=exception.id,
            company_id=self.company_id,
            close_run_id=exception.close_run_id,
            exception_type=exception.type,
            severity=exception.severity,
            financial_impact=exception.financial_impact or Decimal("0.00"),
            currency="USD",
            valid_record_ids=valid_record_ids,
            valid_evidence_ids=valid_evidence_ids,
            primary_record=primary_record,
            related_records=related_records,
            ranked_nodes=ranked_nodes_data,
            graph_edges=edges_data,
            markdown_dossier=markdown_dossier,
        )
