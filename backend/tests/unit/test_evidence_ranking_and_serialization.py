"""Unit tests for EvidenceRanker and deterministic serialization (spec section 7)."""

from __future__ import annotations

import json
import uuid

from app.evidence_graph.graph import FinancialEvidenceGraph
from app.evidence_graph.ranker import EvidenceRanker
from app.evidence_graph.serialization import (
    build_evidence_query_response,
    serialize_query_response_json,
    serialize_subgraph_json,
)
from app.evidence_graph.types import (
    EdgeType,
    EvidenceEdge,
    EvidenceNode,
    EvidenceProvenance,
    EvidenceSubgraph,
    NodeType,
)


def _prov(cid: str, table: str, rec_id: str) -> EvidenceProvenance:
    return EvidenceProvenance(source_table=table, source_id=rec_id, company_id=cid)


def test_evidence_ranking_for_exception_focus():
    cid = str(uuid.uuid4())
    graph = FinancialEvidenceGraph(cid)

    # 1. Exception node
    exc_id = "EXCEPTION:exc-101"
    exc_node = EvidenceNode(
        id=exc_id,
        node_type=NodeType.EXCEPTION,
        record_id="exc-101",
        company_id=cid,
        label="Exception: PO_MISMATCH ($450.00 USD)",
        properties={
            "type": "PO_MISMATCH",
            "financial_impact": "450.00",
            "currency": "USD",
            "severity": "HIGH",
        },
        provenance=_prov(cid, "exceptions", "exc-101"),
    )
    graph.add_node(exc_node)

    # 2. Subject Invoice (with matching amount)
    inv_id = "INVOICE:inv-200"
    inv_node = EvidenceNode(
        id=inv_id,
        node_type=NodeType.INVOICE,
        record_id="inv-200",
        company_id=cid,
        label="Invoice INV-200 ($450.00 USD)",
        properties={"invoice_number": "INV-200", "total": "450.00", "currency": "USD"},
        provenance=_prov(cid, "invoices", "inv-200"),
    )
    graph.add_node(inv_node)

    # 3. Supporting PO
    po_id = "PURCHASE_ORDER:po-300"
    po_node = EvidenceNode(
        id=po_id,
        node_type=NodeType.PURCHASE_ORDER,
        record_id="po-300",
        company_id=cid,
        label="PO: PO-300 ($400.00 USD)",
        properties={"po_number": "PO-300", "total": "400.00", "currency": "USD"},
        provenance=_prov(cid, "purchase_orders", "po-300"),
    )
    graph.add_node(po_node)

    # 4. Connected Vendor (2 hops)
    v_id = "VENDOR:v-500"
    v_node = EvidenceNode(
        id=v_id,
        node_type=NodeType.VENDOR,
        record_id="v-500",
        company_id=cid,
        label="Vendor Acme",
        properties={"name": "Acme"},
        provenance=_prov(cid, "vendors", "v-500"),
    )
    graph.add_node(v_node)

    # Edges
    graph.add_edge(
        EvidenceEdge(
            id="e-exc-inv",
            source_id=exc_id,
            target_id=inv_id,
            edge_type=EdgeType.SUBJECT_OF_EXCEPTION,
            company_id=cid,
        )
    )
    graph.add_edge(
        EvidenceEdge(
            id="e-exc-po",
            source_id=exc_id,
            target_id=po_id,
            edge_type=EdgeType.SUPPORTED_BY_EVIDENCE,
            company_id=cid,
        )
    )
    graph.add_edge(
        EvidenceEdge(
            id="e-inv-po",
            source_id=inv_id,
            target_id=po_id,
            edge_type=EdgeType.REFERENCES_PO,
            company_id=cid,
        )
    )
    graph.add_edge(
        EvidenceEdge(
            id="e-po-v",
            source_id=po_id,
            target_id=v_id,
            edge_type=EdgeType.ISSUED_TO_VENDOR,
            company_id=cid,
        )
    )

    subgraph = graph.get_neighborhood(exc_id, radius=2)
    ranked = EvidenceRanker.rank_subgraph(subgraph, focus_node_id=exc_id)

    assert len(ranked) == 4

    # Rank 1 is the focus exception itself
    assert ranked[0].node.id == exc_id
    assert ranked[0].score >= 0.90

    # Rank 2 is the primary subject invoice (has subject link AND exact amount match)
    assert ranked[1].node.id == inv_id
    assert "Direct subject of exception" in ranked[1].relevance_reason
    assert "Monetary amount exactly matches discrepancy" in ranked[1].relevance_reason

    # Rank 3 is the supporting PO
    assert ranked[2].node.id == po_id
    assert "Direct supporting evidence for exception" in ranked[2].relevance_reason

    # Rank 4 is the vendor at 2 hops
    assert ranked[3].node.id == v_id
    assert ranked[3].distance == 2
    assert ranked[3].score < ranked[1].score


def test_evidence_ranking_determinism():
    """Rankings on identical subgraphs must produce identical scores and ordering."""
    cid = str(uuid.uuid4())
    nodes = [
        EvidenceNode(
            id=f"INVOICE:inv-{i}",
            node_type=NodeType.INVOICE,
            record_id=f"inv-{i}",
            company_id=cid,
            label=f"Invoice {i}",
            properties={"total": f"{100 * i}.00"},
            provenance=_prov(cid, "invoices", f"inv-{i}"),
        )
        for i in range(10)
    ]
    edges = [
        EvidenceEdge(
            id=f"e-{i}->{i + 1}",
            source_id=f"INVOICE:inv-{i}",
            target_id=f"INVOICE:inv-{i + 1}",
            edge_type=EdgeType.REFERENCES_PO,
            company_id=cid,
        )
        for i in range(9)
    ]
    subgraph = EvidenceSubgraph(nodes=nodes, edges=edges, root_node_id="INVOICE:inv-0")

    run1 = EvidenceRanker.rank_subgraph(subgraph, "INVOICE:inv-0")
    run2 = EvidenceRanker.rank_subgraph(subgraph, "INVOICE:inv-0")

    assert [r.node.id for r in run1] == [r.node.id for r in run2]
    assert [r.score for r in run1] == [r.score for r in run2]


def test_deterministic_json_serialization():
    cid = str(uuid.uuid4())
    node = EvidenceNode(
        id="INVOICE:inv-1",
        node_type=NodeType.INVOICE,
        record_id="inv-1",
        company_id=cid,
        label="Invoice #1",
        properties={"total": "12500.50", "currency": "USD"},
        provenance=_prov(cid, "invoices", "inv-1"),
    )
    subgraph = EvidenceSubgraph(nodes=[node], edges=[], root_node_id=node.id)

    json_str = serialize_subgraph_json(subgraph)
    parsed = json.loads(json_str)

    assert parsed["root_node_id"] == "INVOICE:inv-1"
    assert parsed["nodes"][0]["properties"]["total"] == "12500.50"
    assert "provenance" in parsed["nodes"][0]

    # Test round trip into Pydantic
    reconstructed = EvidenceSubgraph.model_validate(parsed)
    assert reconstructed.nodes[0].id == node.id
    assert reconstructed.nodes[0].properties["total"] == "12500.50"


def test_llm_markdown_formatting():
    cid = str(uuid.uuid4())
    exc_node = EvidenceNode(
        id="EXCEPTION:exc-42",
        node_type=NodeType.EXCEPTION,
        record_id="exc-42",
        company_id=cid,
        label="Exception: RECEIPT_MISMATCH ($1,200.00 USD)",
        properties={
            "type": "RECEIPT_MISMATCH",
            "severity": "CRITICAL",
            "financial_impact": "1200.00",
            "currency": "USD",
            "root_cause": "Goods receipt missing 5 units",
        },
        provenance=_prov(cid, "exceptions", "exc-42"),
    )
    il_node = EvidenceNode(
        id="INVOICE_LINE:il-1",
        node_type=NodeType.INVOICE_LINE,
        record_id="il-1",
        company_id=cid,
        label="Line 1: Widget A",
        properties={
            "description": "Widget A",
            "quantity": "25.0000",
            "unit_price": "48.0000",
            "amount": "1200.00",
        },
        provenance=_prov(cid, "invoice_lines", "il-1"),
    )
    rl_node = EvidenceNode(
        id="RECEIPT_LINE:rl-1",
        node_type=NodeType.RECEIPT_LINE,
        record_id="rl-1",
        company_id=cid,
        label="Receipt Line 1: Widget A",
        properties={"description": "Widget A", "quantity_received": "20.0000"},
        provenance=_prov(cid, "receipt_lines", "rl-1"),
    )
    edge = EvidenceEdge(
        id="e-exc-il",
        source_id=exc_node.id,
        target_id=il_node.id,
        edge_type=EdgeType.SUBJECT_OF_EXCEPTION,
        company_id=cid,
    )
    subgraph = EvidenceSubgraph(
        nodes=[exc_node, il_node, rl_node],
        edges=[edge],
        root_node_id=exc_node.id,
        metadata={"company_id": cid},
    )

    response = build_evidence_query_response(
        focus_node_id=exc_node.id,
        subgraph=subgraph,
        query_type="EXCEPTION_INVESTIGATION",
        company_id=cid,
    )

    md = response.llm_context_markdown

    assert "### FINANCIAL EVIDENCE DOSSIER" in md
    assert "Query Type:** EXCEPTION_INVESTIGATION" in md
    assert "Focus Entity:** `EXCEPTION:exc-42`" in md
    assert "#### Ranked Supporting Evidence" in md
    assert "| Rank | Score | Type | Label | Dist | Relevance Reason |" in md
    assert "#### Line Item Inspection & Variance" in md
    assert "`INVOICE_LINE`" in md
    assert "`RECEIPT_LINE`" in md
    assert "Widget A" in md

    # Check JSON serialization of query response
    json_resp = serialize_query_response_json(response)
    data = json.loads(json_resp)
    assert data["focus_node_id"] == exc_node.id
    assert len(data["ranked_evidence"]) == 3
    assert data["llm_context_markdown"] == md
