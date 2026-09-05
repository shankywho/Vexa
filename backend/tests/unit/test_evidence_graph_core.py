"""Unit tests for the core FinancialEvidenceGraph operations, traversals, and algorithms."""

from __future__ import annotations

import uuid

import pytest

from app.evidence_graph.graph import FinancialEvidenceGraph
from app.evidence_graph.types import (
    EdgeDirection,
    EdgeType,
    EvidenceEdge,
    EvidenceNode,
    EvidenceProvenance,
    NodeType,
    TenantIsolationViolationError,
)


def _prov(cid: str, table: str, rec_id: str) -> EvidenceProvenance:
    return EvidenceProvenance(source_table=table, source_id=rec_id, company_id=cid)


def test_graph_node_and_edge_addition_and_lookups():
    cid = str(uuid.uuid4())
    graph = FinancialEvidenceGraph(cid)

    # 1. Add vendor node
    v_id = EvidenceNode.make_id(NodeType.VENDOR, "v-001")
    v_node = EvidenceNode(
        id=v_id,
        node_type=NodeType.VENDOR,
        record_id="v-001",
        company_id=cid,
        label="Acme Supplies",
        properties={"name": "Acme Supplies", "tax_id": "XX-123"},
        provenance=_prov(cid, "vendors", "v-001"),
    )
    graph.add_node(v_node)

    # 2. Add invoice node
    inv_id = EvidenceNode.make_id(NodeType.INVOICE, "inv-001")
    inv_node = EvidenceNode(
        id=inv_id,
        node_type=NodeType.INVOICE,
        record_id="inv-001",
        company_id=cid,
        label="Invoice INV-001 ($500.00 USD)",
        properties={"invoice_number": "INV-001", "total": "500.00", "currency": "USD"},
        provenance=_prov(cid, "invoices", "inv-001"),
    )
    graph.add_node(inv_node)

    # Lookups
    assert graph.has_node(v_id)
    assert graph.has_node(inv_id)
    assert not graph.has_node("INVOICE:non-existent")
    assert graph.get_node(v_id) == v_node
    assert len(graph.get_nodes_by_type(NodeType.VENDOR)) == 1
    assert len(graph.get_nodes_by_type(NodeType.INVOICE)) == 1

    # 3. Add edge: INVOICE -> VENDOR
    edge_id = EvidenceEdge.make_id(inv_id, EdgeType.ISSUED_BY_VENDOR, v_id)
    edge = EvidenceEdge(
        id=edge_id,
        source_id=inv_id,
        target_id=v_id,
        edge_type=EdgeType.ISSUED_BY_VENDOR,
        company_id=cid,
        provenance=_prov(cid, "invoices", "inv-001"),
    )
    added = graph.add_edge(edge)
    assert added is True

    # Duplicate edge addition returns False
    assert graph.add_edge(edge) is False

    # Edge lookups
    assert graph.get_edge(edge_id) == edge
    assert len(graph.get_edges_by_type(EdgeType.ISSUED_BY_VENDOR)) == 1

    # Adjacent edges
    out_edges = graph.get_adjacent_edges(inv_id, direction=EdgeDirection.OUTGOING)
    assert len(out_edges) == 1
    assert out_edges[0].id == edge_id

    in_edges = graph.get_adjacent_edges(v_id, direction=EdgeDirection.INCOMING)
    assert len(in_edges) == 1
    assert in_edges[0].id == edge_id

    both_v = graph.get_adjacent_edges(v_id, direction=EdgeDirection.BOTH)
    assert len(both_v) == 1


def test_tenant_isolation_enforcement_on_mutations():
    cid_a = str(uuid.uuid4())
    cid_b = str(uuid.uuid4())
    graph_a = FinancialEvidenceGraph(cid_a)

    # Adding node with foreign company_id raises TenantIsolationViolationError
    node_b = EvidenceNode(
        id=EvidenceNode.make_id(NodeType.VENDOR, "v-b"),
        node_type=NodeType.VENDOR,
        record_id="v-b",
        company_id=cid_b,
        label="Foreign Vendor",
        provenance=_prov(cid_b, "vendors", "v-b"),
    )
    with pytest.raises(TenantIsolationViolationError, match="bounded by"):
        graph_a.add_node(node_b)

    # Adding edge with foreign company_id raises TenantIsolationViolationError
    node_a = EvidenceNode(
        id=EvidenceNode.make_id(NodeType.VENDOR, "v-a"),
        node_type=NodeType.VENDOR,
        record_id="v-a",
        company_id=cid_a,
        label="Local Vendor",
        provenance=_prov(cid_a, "vendors", "v-a"),
    )
    graph_a.add_node(node_a)

    edge_foreign = EvidenceEdge(
        id=EvidenceEdge.make_id(node_a.id, EdgeType.BELONGS_TO_COMPANY, "COMPANY:comp-b"),
        source_id=node_a.id,
        target_id="COMPANY:comp-b",
        edge_type=EdgeType.BELONGS_TO_COMPANY,
        company_id=cid_b,
    )
    with pytest.raises(TenantIsolationViolationError, match="bounded by"):
        graph_a.add_edge(edge_foreign)


def test_cycle_detection_and_bfs_traversal():
    cid = str(uuid.uuid4())
    graph = FinancialEvidenceGraph(cid)

    # Create a cyclic graph: A -> B -> C -> A
    n_a = EvidenceNode(
        id="A",
        node_type=NodeType.INVOICE,
        record_id="a",
        company_id=cid,
        label="Node A",
        provenance=_prov(cid, "test", "a"),
    )
    n_b = EvidenceNode(
        id="B",
        node_type=NodeType.PURCHASE_ORDER,
        record_id="b",
        company_id=cid,
        label="Node B",
        provenance=_prov(cid, "test", "b"),
    )
    n_c = EvidenceNode(
        id="C",
        node_type=NodeType.GOODS_RECEIPT,
        record_id="c",
        company_id=cid,
        label="Node C",
        provenance=_prov(cid, "test", "c"),
    )
    for n in (n_a, n_b, n_c):
        graph.add_node(n)

    graph.add_edge(
        EvidenceEdge(
            id="e1",
            source_id="A",
            target_id="B",
            edge_type=EdgeType.REFERENCES_PO,
            company_id=cid,
        )
    )
    graph.add_edge(
        EvidenceEdge(
            id="e2",
            source_id="B",
            target_id="C",
            edge_type=EdgeType.FULFILLED_BY_RECEIPT,
            company_id=cid,
        )
    )
    graph.add_edge(
        EvidenceEdge(
            id="e3",
            source_id="C",
            target_id="A",
            edge_type=EdgeType.MATCHED_IN_RECONCILIATION,
            company_id=cid,
        )
    )

    # BFS traversal from A must terminate cleanly without infinite loop
    subgraph = graph.bfs_traversal("A", max_depth=10)
    assert len(subgraph.nodes) == 3
    assert len(subgraph.edges) == 3
    node_ids = {n.id for n in subgraph.nodes}
    assert node_ids == {"A", "B", "C"}


def test_shortest_path_search():
    cid = str(uuid.uuid4())
    graph = FinancialEvidenceGraph(cid)

    # Chain: Payment -> BankTx -> JournalEntry -> LedgerAccount
    nodes = [
        EvidenceNode(
            id="PAYMENT:p1",
            node_type=NodeType.PAYMENT,
            record_id="p1",
            company_id=cid,
            label="Payment",
            provenance=_prov(cid, "payments", "p1"),
        ),
        EvidenceNode(
            id="BANK_TX:bt1",
            node_type=NodeType.BANK_TRANSACTION,
            record_id="bt1",
            company_id=cid,
            label="Bank Tx",
            provenance=_prov(cid, "bank_tx", "bt1"),
        ),
        EvidenceNode(
            id="JE:je1",
            node_type=NodeType.JOURNAL_ENTRY,
            record_id="je1",
            company_id=cid,
            label="JE",
            provenance=_prov(cid, "je", "je1"),
        ),
        EvidenceNode(
            id="LA:la1",
            node_type=NodeType.LEDGER_ACCOUNT,
            record_id="la1",
            company_id=cid,
            label="GL Account",
            provenance=_prov(cid, "la", "la1"),
        ),
        EvidenceNode(
            id="VENDOR:v1",
            node_type=NodeType.VENDOR,
            record_id="v1",
            company_id=cid,
            label="Isolated Vendor",
            provenance=_prov(cid, "v", "v1"),
        ),
    ]
    for n in nodes:
        graph.add_node(n)

    graph.add_edge(
        EvidenceEdge(
            id="e-p-bt",
            source_id="PAYMENT:p1",
            target_id="BANK_TX:bt1",
            edge_type=EdgeType.APPEARS_AS_BANK_TX,
            company_id=cid,
        )
    )
    graph.add_edge(
        EvidenceEdge(
            id="e-bt-je",
            source_id="BANK_TX:bt1",
            target_id="JE:je1",
            edge_type=EdgeType.MAPPED_TO_JOURNAL_ENTRY,
            company_id=cid,
        )
    )
    graph.add_edge(
        EvidenceEdge(
            id="e-je-la",
            source_id="JE:je1",
            target_id="LA:la1",
            edge_type=EdgeType.POSTS_TO_LEDGER,
            company_id=cid,
        )
    )

    # 1. Shortest path from Payment to LedgerAccount: 3 hops
    path = graph.find_shortest_path("PAYMENT:p1", "LA:la1")
    assert path is not None
    assert path.hop_count == 3
    assert len(path.nodes) == 4
    assert len(path.edges) == 3
    assert [n.id for n in path.nodes] == ["PAYMENT:p1", "BANK_TX:bt1", "JE:je1", "LA:la1"]
    assert "──(APPEARS_AS_BANK_TX)──>" in path.summary

    # 2. Identical start and target: 0 hops
    same_path = graph.find_shortest_path("PAYMENT:p1", "PAYMENT:p1")
    assert same_path is not None
    assert same_path.hop_count == 0
    assert len(same_path.nodes) == 1

    # 3. Disconnected node returns None
    disc_path = graph.find_shortest_path("PAYMENT:p1", "VENDOR:v1")
    assert disc_path is None


def test_company_hub_exclusion_default():
    cid = str(uuid.uuid4())
    graph = FinancialEvidenceGraph(cid)

    comp_id = f"COMPANY:{cid}"
    graph.add_node(
        EvidenceNode(
            id=comp_id,
            node_type=NodeType.COMPANY,
            record_id=cid,
            company_id=cid,
            label="Company Hub",
            provenance=_prov(cid, "companies", cid),
        )
    )

    # 10 independent invoices connected to Company
    for i in range(10):
        inv_id = f"INVOICE:inv-{i}"
        graph.add_node(
            EvidenceNode(
                id=inv_id,
                node_type=NodeType.INVOICE,
                record_id=f"inv-{i}",
                company_id=cid,
                label=f"Invoice {i}",
                provenance=_prov(cid, "invoices", f"inv-{i}"),
            )
        )
        graph.add_edge(
            EvidenceEdge(
                id=f"e-comp-{i}",
                source_id=comp_id,
                target_id=inv_id,
                edge_type=EdgeType.BELONGS_TO_COMPANY,
                company_id=cid,
            )
        )

    # Neighborhood of INVOICE:inv-0 must NOT cross BELONGS_TO_COMPANY into other invoices!
    subgraph = graph.get_neighborhood("INVOICE:inv-0", radius=2)
    assert len(subgraph.nodes) == 1  # Only inv-0, no company explosion
    assert subgraph.nodes[0].id == "INVOICE:inv-0"

    # When BELONGS_TO_COMPANY is explicitly allowed, company is reachable
    subgraph_with_hub = graph.get_neighborhood("INVOICE:inv-0", radius=2, excluded_edge_types=set())
    assert len(subgraph_with_hub.nodes) == 11  # inv-0 + company + all 9 other invoices
