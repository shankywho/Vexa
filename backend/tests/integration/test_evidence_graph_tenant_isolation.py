"""Integration tests for tenant isolation in FinancialEvidenceGraph (spec section 7 & 30)."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.generator import seed_financial_transactions
from app.data.seed import seed_company
from app.db.models.banking import BankAccount, Payment
from app.db.models.counterparty import Vendor
from app.db.models.exception import ExceptionRecord
from app.db.models.procurement import Invoice, PurchaseOrder, PurchaseOrderLine
from app.db.models.tenancy import Company
from app.domain.enums import DocumentStatus, ExceptionSeverity, ExceptionStatus, ExceptionType
from app.evidence_graph.builder import FinancialEvidenceGraphBuilder
from app.evidence_graph.types import (
    EdgeType,
    EvidenceEdge,
    NodeType,
    TenantIsolationViolationError,
)
from app.reconciliation.engine import DeterministicReconciliationEngine


@pytest.mark.asyncio
async def test_evidence_graph_strict_tenant_isolation(db: AsyncSession):
    """Company A graph operations must NEVER leak or query Company B nodes or edges."""
    # 1. Company Alpha (full seeded demo company)
    comp_a = await seed_company(db, seed=42, include_transactions=False)
    await seed_financial_transactions(db, comp_a, seed=42)

    eng_a = DeterministicReconciliationEngine(db, comp_a.id)
    await eng_a.run_full_reconciliation(persist=True)

    # 2. Company Beta (independent tenant created in the same database)
    comp_b = Company(
        id=uuid.uuid4(),
        name="Company Beta Isolated",
        base_currency="USD",
        is_active=True,
    )
    db.add(comp_b)
    await db.flush()

    vendor_b = Vendor(
        id=uuid.uuid4(),
        company_id=comp_b.id,
        name="Beta Logistics LLC",
        status=DocumentStatus.OPEN,
    )
    bank_b = BankAccount(
        id=uuid.uuid4(),
        company_id=comp_b.id,
        account_name="Beta Operating",
        account_number="BETA-9999",
        currency="USD",
        is_active=True,
    )
    db.add_all([vendor_b, bank_b])
    await db.flush()

    po_b = PurchaseOrder(
        id=uuid.uuid4(),
        company_id=comp_b.id,
        vendor_id=vendor_b.id,
        po_number="PO-BETA-001",
        order_date=date(2026, 2, 1),
        currency="USD",
        total=Decimal("8500.00"),
        status=DocumentStatus.OPEN,
    )
    po_b.lines = [
        PurchaseOrderLine(
            id=uuid.uuid4(),
            description="Beta Industrial Pumps",
            quantity=Decimal("10.0000"),
            unit_price=Decimal("850.0000"),
            amount=Decimal("8500.00"),
        )
    ]
    db.add(po_b)
    await db.flush()

    inv_b = Invoice(
        id=uuid.uuid4(),
        company_id=comp_b.id,
        vendor_id=vendor_b.id,
        po_id=po_b.id,
        invoice_number="INV-BETA-001",
        invoice_date=date(2026, 2, 5),
        currency="USD",
        subtotal=Decimal("8500.00"),
        tax=Decimal("0.00"),
        total=Decimal("8500.00"),
        status=DocumentStatus.OPEN,
    )
    db.add(inv_b)
    await db.flush()

    pmt_b = Payment(
        id=uuid.uuid4(),
        company_id=comp_b.id,
        vendor_id=vendor_b.id,
        invoice_id=inv_b.id,
        bank_account_id=bank_b.id,
        amount=Decimal("8500.00"),
        currency="USD",
        payment_date=date(2026, 2, 10),
        status=DocumentStatus.POSTED,
    )
    db.add(pmt_b)

    exc_b = ExceptionRecord(
        id=uuid.uuid4(),
        company_id=comp_b.id,
        type=ExceptionType.PO_MISMATCH,
        severity=ExceptionSeverity.HIGH,
        status=ExceptionStatus.OPEN,
        financial_impact=Decimal("500.00"),
        currency="USD",
        source_invoice_id=inv_b.id,
        source_po_id=po_b.id,
    )
    db.add(exc_b)
    await db.flush()

    # 3. Build evidence graph for each tenant
    builder_a = FinancialEvidenceGraphBuilder(db, comp_a.id)
    graph_a = await builder_a.build()

    builder_b = FinancialEvidenceGraphBuilder(db, comp_b.id)
    graph_b = await builder_b.build()

    cid_a = str(comp_a.id)
    cid_b = str(comp_b.id)

    # 4. Verify graph boundary
    assert graph_a.company_id == cid_a
    assert graph_b.company_id == cid_b
    assert cid_a != cid_b

    # 5. Assert 100% of nodes and edges in graph_a belong exclusively to comp_a
    stats_a = graph_a.stats()
    assert stats_a["total_nodes"] > 3000
    for node in graph_a.get_nodes_by_type(NodeType.INVOICE):
        assert node.company_id == cid_a
        assert node.provenance.company_id == cid_a

    for node in graph_a.get_nodes_by_type(NodeType.VENDOR):
        assert node.company_id == cid_a

    for node in graph_a.get_nodes_by_type(NodeType.EXCEPTION):
        assert node.company_id == cid_a

    for edge in graph_a.get_edges_by_type(EdgeType.REFERENCES_PO):
        assert edge.company_id == cid_a

    # 6. Assert 100% of nodes and edges in graph_b belong exclusively to comp_b
    stats_b = graph_b.stats()
    assert stats_b["total_nodes"] >= 6
    for node in graph_b.get_nodes_by_type(NodeType.INVOICE):
        assert node.company_id == cid_b
        assert node.provenance.company_id == cid_b

    for node in graph_b.get_nodes_by_type(NodeType.VENDOR):
        assert node.company_id == cid_b

    for node in graph_b.get_nodes_by_type(NodeType.EXCEPTION):
        assert node.company_id == cid_b

    # 7. Assert cross-tenant lookup returns False / None
    nodes_b = graph_b.get_nodes_by_type(NodeType.INVOICE)
    assert len(nodes_b) > 0
    sample_b_node = nodes_b[0]

    assert not graph_a.has_node(sample_b_node.id)
    assert graph_a.get_node(sample_b_node.id) is None

    nodes_a = graph_a.get_nodes_by_type(NodeType.INVOICE)
    assert len(nodes_a) > 0
    sample_a_node = nodes_a[0]

    assert not graph_b.has_node(sample_a_node.id)
    assert graph_b.get_node(sample_a_node.id) is None

    # 8. Cross-tenant shortest path must be None
    cross_path = graph_a.find_shortest_path(sample_a_node.id, sample_b_node.id)
    assert cross_path is None

    # 9. Cross-tenant traversal returns empty subgraph
    cross_subgraph = graph_a.get_neighborhood(sample_b_node.id, radius=2)
    assert len(cross_subgraph.nodes) == 0
    assert len(cross_subgraph.edges) == 0

    # 10. Attempting to inject a Company B node or edge into Company A graph raises error
    with pytest.raises(TenantIsolationViolationError, match="bounded by"):
        graph_a.add_node(sample_b_node)

    illegal_edge = EvidenceEdge(
        id=EvidenceEdge.make_id(sample_a_node.id, EdgeType.PAID_BY_PAYMENT, sample_b_node.id),
        source_id=sample_a_node.id,
        target_id=sample_b_node.id,
        edge_type=EdgeType.PAID_BY_PAYMENT,
        company_id=cid_b,  # Tenant mismatch!
    )
    with pytest.raises(TenantIsolationViolationError, match="bounded by"):
        graph_a.add_edge(illegal_edge)
