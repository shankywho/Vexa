"""Integration tests for FinancialEvidenceGraphBuilder over seeded data (spec section 7)."""

from __future__ import annotations

import time

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.generator import seed_financial_transactions
from app.data.seed import seed_company
from app.evidence_graph.builder import FinancialEvidenceGraphBuilder
from app.evidence_graph.serialization import build_evidence_query_response
from app.evidence_graph.types import (
    EdgeDirection,
    EdgeType,
    NodeType,
)
from app.reconciliation.engine import DeterministicReconciliationEngine


@pytest.mark.asyncio
async def test_evidence_graph_construction_and_entity_coverage(db: AsyncSession):
    """Demonstrate graph construction over seeded company data and assert full entity coverage."""
    # 1. Seed tenant and transactions
    company = await seed_company(db, seed=42, include_transactions=False)
    await seed_financial_transactions(db, company, seed=42)

    # 2. Run reconciliation with persistence to populate reconciliation results and exceptions
    rec_engine = DeterministicReconciliationEngine(db, company.id)
    summary = await rec_engine.run_full_reconciliation(persist=True)
    assert summary.total_items_processed > 0
    assert summary.total_exceptions > 0

    # 3. Build the evidence graph from PostgreSQL with performance benchmark
    t0 = time.perf_counter()
    builder = FinancialEvidenceGraphBuilder(db, company.id)
    graph = await builder.build()
    construction_duration = time.perf_counter() - t0

    # Performance benchmark: graph construction should be fast (< 3.0s in test environment)
    assert construction_duration < 3.0, (
        f"Construction took {construction_duration:.3f}s (expected < 3.0s)"
    )

    # 4. Verify graph statistics
    stats = graph.stats()
    assert stats["company_id"] == str(company.id)
    assert stats["total_nodes"] > 3000, f"Expected >3000 nodes, got {stats['total_nodes']}"
    assert stats["total_edges"] > 3000, f"Expected >3000 edges, got {stats['total_edges']}"
    assert stats["density"] > 0.0

    nodes_by_type = stats["nodes_by_type"]

    # Verify coverage of the 20 financial entities
    expected_types = [
        NodeType.COMPANY,
        NodeType.VENDOR,
        NodeType.CUSTOMER,
        NodeType.INVOICE,
        NodeType.INVOICE_LINE,
        NodeType.PURCHASE_ORDER,
        NodeType.PO_LINE,
        NodeType.GOODS_RECEIPT,
        NodeType.RECEIPT_LINE,
        NodeType.PAYMENT,
        NodeType.BANK_ACCOUNT,
        NodeType.BANK_TRANSACTION,
        NodeType.LEDGER_ACCOUNT,
        NodeType.JOURNAL_ENTRY,
        NodeType.JOURNAL_ENTRY_LINE,
        NodeType.EXPENSE_REPORT,
        NodeType.CONTRACT,
        NodeType.FX_RATE,
        NodeType.RECONCILIATION_RESULT,
        NodeType.EXCEPTION,
    ]
    for ntype in expected_types:
        count = nodes_by_type.get(ntype.value, 0)
        assert count > 0, f"Entity {ntype.value} has 0 nodes in graph!"

    print(
        f"\n[EVIDENCE GRAPH STATS] Nodes: {stats['total_nodes']}, Edges: {stats['total_edges']}, "
        f"Built in: {construction_duration * 1000:.1f}ms"
    )


@pytest.mark.asyncio
async def test_evidence_graph_multi_hop_traversals(db: AsyncSession):
    """Demonstrate required multi-hop traversals:

    1. payment -> invoice -> PO -> vendor
    2. bank transaction -> payment -> invoice -> goods receipt
    3. exception -> supporting evidence -> root records
    """
    company = await seed_company(db, seed=42, include_transactions=False)
    await seed_financial_transactions(db, company, seed=42)

    rec_engine = DeterministicReconciliationEngine(db, company.id)
    await rec_engine.run_full_reconciliation(persist=True)

    builder = FinancialEvidenceGraphBuilder(db, company.id)
    graph = await builder.build()

    # -------------------------------------------------------------------------
    # Traversal 1: payment -> invoice -> PO -> vendor
    # -------------------------------------------------------------------------
    payments = graph.get_nodes_by_type(NodeType.PAYMENT)
    assert len(payments) > 0

    found_p_inv_po_v = False
    for pmt in payments[:50]:
        # Outgoing edges from payment
        inv_neighbors = graph.get_adjacent_nodes(
            pmt.id,
            allowed_node_types={NodeType.INVOICE},
            allowed_edge_types={EdgeType.PAID_BY_PAYMENT, EdgeType.PAYMENT_PAYS_INVOICE},
        )
        for inv in inv_neighbors:
            po_neighbors = graph.get_adjacent_nodes(
                inv.id,
                allowed_node_types={NodeType.PURCHASE_ORDER},
                allowed_edge_types={EdgeType.REFERENCES_PO},
            )
            for po in po_neighbors:
                vendor_neighbors = graph.get_adjacent_nodes(
                    po.id,
                    allowed_node_types={NodeType.VENDOR},
                    allowed_edge_types={EdgeType.ISSUED_TO_VENDOR},
                )
                if vendor_neighbors:
                    found_p_inv_po_v = True
                    # Verify multi-hop path from Payment to PO and Vendor via PO
                    path_to_po = graph.find_shortest_path(pmt.id, po.id)
                    assert path_to_po is not None
                    assert path_to_po.hop_count == 2
                    assert [n.node_type for n in path_to_po.nodes] == [
                        NodeType.PAYMENT,
                        NodeType.INVOICE,
                        NodeType.PURCHASE_ORDER,
                    ]

                    path = graph.find_shortest_path(
                        pmt.id,
                        vendor_neighbors[0].id,
                        excluded_edge_types={
                            EdgeType.BELONGS_TO_COMPANY,
                            EdgeType.PAYMENT_TO_VENDOR,
                            EdgeType.ISSUED_BY_VENDOR,
                        },
                    )
                    assert path is not None
                    assert path.hop_count == 3
                    assert [n.node_type for n in path.nodes] == [
                        NodeType.PAYMENT,
                        NodeType.INVOICE,
                        NodeType.PURCHASE_ORDER,
                        NodeType.VENDOR,
                    ]
                    assert pmt.id in path.summary
                    assert vendor_neighbors[0].id in path.summary
                    break
            if found_p_inv_po_v:
                break
        if found_p_inv_po_v:
            break

    assert found_p_inv_po_v, "Failed to traverse payment -> invoice -> PO -> vendor"

    # -------------------------------------------------------------------------
    # Traversal 2: bank transaction -> payment -> invoice -> goods receipt
    # -------------------------------------------------------------------------
    found_bt_p_inv_gr = False
    bank_txs = graph.get_nodes_by_type(NodeType.BANK_TRANSACTION)
    for bt in bank_txs:
        pmt_neighbors = graph.get_adjacent_nodes(
            bt.id,
            allowed_node_types={NodeType.PAYMENT},
            allowed_edge_types={EdgeType.APPEARS_AS_BANK_TX},
        )
        for pmt in pmt_neighbors:
            inv_neighbors = graph.get_adjacent_nodes(
                pmt.id,
                allowed_node_types={NodeType.INVOICE},
                allowed_edge_types={EdgeType.PAID_BY_PAYMENT, EdgeType.PAYMENT_PAYS_INVOICE},
            )
            for inv in inv_neighbors:
                po_neighbors = graph.get_adjacent_nodes(
                    inv.id,
                    allowed_node_types={NodeType.PURCHASE_ORDER},
                    allowed_edge_types={EdgeType.REFERENCES_PO},
                )
                for po in po_neighbors:
                    gr_neighbors = graph.get_adjacent_nodes(
                        po.id,
                        allowed_node_types={NodeType.GOODS_RECEIPT},
                        allowed_edge_types={EdgeType.FULFILLED_BY_RECEIPT},
                    )
                    if gr_neighbors:
                        found_bt_p_inv_gr = True
                        path = graph.find_shortest_path(bt.id, gr_neighbors[0].id)
                        assert path is not None
                        assert path.hop_count >= 3
                        break
                if found_bt_p_inv_gr:
                    break
            if found_bt_p_inv_gr:
                break
        if found_bt_p_inv_gr:
            break

    assert found_bt_p_inv_gr, (
        "Failed to traverse bank transaction -> payment -> invoice -> goods receipt"
    )

    # -------------------------------------------------------------------------
    # Traversal 3: exception -> supporting evidence -> root records
    # -------------------------------------------------------------------------
    exceptions = graph.get_nodes_by_type(NodeType.EXCEPTION)
    assert len(exceptions) > 0

    found_exc_evidence = False
    for exc in exceptions:
        sub = graph.explain_exception(exc.id, radius=2)
        assert len(sub.nodes) > 1
        assert sub.root_node_id == exc.id

        # Verify exception has direct subjects or supporting evidence
        direct_edges = graph.get_adjacent_edges(exc.id, direction=EdgeDirection.BOTH)
        evidence_types = {e.edge_type for e in direct_edges}
        has_subject_or_evidence = (
            EdgeType.SUBJECT_OF_EXCEPTION in evidence_types
            or EdgeType.SUPPORTED_BY_EVIDENCE in evidence_types
            or EdgeType.GENERATED_BY_RECONCILIATION in evidence_types
        )
        if has_subject_or_evidence:
            found_exc_evidence = True

            # Generate query response and verify LLM Markdown dossier
            response = build_evidence_query_response(
                focus_node_id=exc.id,
                subgraph=sub,
                query_type="EXCEPTION_INVESTIGATION",
                company_id=str(company.id),
            )
            assert response.focus_node_id == exc.id
            assert len(response.ranked_evidence) > 1
            assert "### FINANCIAL EVIDENCE DOSSIER" in response.llm_context_markdown
            assert exc.properties["type"] in response.llm_context_markdown
            break

    assert found_exc_evidence, "Failed to link exception to supporting evidence or root records"


@pytest.mark.asyncio
async def test_evidence_graph_query_helpers_and_performance(db: AsyncSession):
    """Test high-level domain query helpers and benchmark query latencies."""
    company = await seed_company(db, seed=42, include_transactions=False)
    await seed_financial_transactions(db, company, seed=42)

    rec_engine = DeterministicReconciliationEngine(db, company.id)
    await rec_engine.run_full_reconciliation(persist=True)

    builder = FinancialEvidenceGraphBuilder(db, company.id)
    graph = await builder.build()

    # 1. Trace payment flow
    pmts = graph.get_nodes_by_type(NodeType.PAYMENT)
    assert len(pmts) > 0
    t0 = time.perf_counter()
    p_sub = graph.trace_payment_flow(pmts[0].id)
    p_lat = time.perf_counter() - t0
    assert len(p_sub.nodes) > 0
    assert p_lat < 0.05, f"Payment trace took {p_lat * 1000:.2f}ms (expected < 50ms)"

    # 2. Trace procurement flow
    invs = graph.get_nodes_by_type(NodeType.INVOICE)
    assert len(invs) > 0
    t0 = time.perf_counter()
    inv_sub = graph.trace_procurement_flow(invs[0].id)
    inv_lat = time.perf_counter() - t0
    assert len(inv_sub.nodes) > 0
    assert inv_lat < 0.05

    # 3. Vendor activity
    vendors = graph.get_nodes_by_type(NodeType.VENDOR)
    assert len(vendors) > 0
    t0 = time.perf_counter()
    v_sub = graph.get_vendor_activity(vendors[0].id)
    v_lat = time.perf_counter() - t0
    assert len(v_sub.nodes) > 0
    assert v_lat < 0.05

    # 4. Explain exception
    excs = graph.get_nodes_by_type(NodeType.EXCEPTION)
    assert len(excs) > 0
    t0 = time.perf_counter()
    exc_sub = graph.explain_exception(excs[0].id, radius=2)
    exc_lat = time.perf_counter() - t0
    assert len(exc_sub.nodes) > 0
    assert exc_lat < 0.05
