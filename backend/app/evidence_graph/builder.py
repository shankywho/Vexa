"""Deterministic financial evidence graph builder from PostgreSQL (spec section 7).

Extracts tenant financial records and reconciliation matches from PostgreSQL,
producing a typed FinancialEvidenceGraph with full provenance and tenant isolation.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.banking import BankAccount, BankTransaction, Payment
from app.db.models.counterparty import Customer, Vendor
from app.db.models.exception import ExceptionRecord, ReconciliationResult
from app.db.models.fx import FxRate
from app.db.models.ledger import JournalEntry, LedgerAccount
from app.db.models.procurement import (
    Contract,
    ExpenseReport,
    GoodsReceipt,
    Invoice,
    PurchaseOrder,
)
from app.db.models.tenancy import Company
from app.evidence_graph.graph import FinancialEvidenceGraph
from app.evidence_graph.types import (
    EdgeType,
    EvidenceEdge,
    EvidenceNode,
    EvidenceProvenance,
    NodeType,
)


class FinancialEvidenceGraphBuilder:
    """Constructs a deterministic FinancialEvidenceGraph for a tenant from PostgreSQL."""

    def __init__(self, session: AsyncSession, company_id: uuid.UUID | str) -> None:
        self.session = session
        self.company_id = uuid.UUID(str(company_id))
        self._cid_str = str(self.company_id)

    def _provenance(
        self, table: str, record_id: uuid.UUID | str, description: str | None = None
    ) -> EvidenceProvenance:
        return EvidenceProvenance(
            source_table=table,
            source_id=str(record_id),
            company_id=self._cid_str,
            description=description,
        )

    async def build(self) -> FinancialEvidenceGraph:
        """Build the complete, tenant-isolated financial evidence graph."""
        graph = FinancialEvidenceGraph(self._cid_str)

        # 1. Company
        company = await self.session.scalar(select(Company).where(Company.id == self.company_id))
        if company is not None:
            comp_node_id = EvidenceNode.make_id(NodeType.COMPANY, company.id)
            graph.add_node(
                EvidenceNode(
                    id=comp_node_id,
                    node_type=NodeType.COMPANY,
                    record_id=str(company.id),
                    company_id=self._cid_str,
                    label=f"Company: {company.name} ({company.base_currency})",
                    properties={
                        "name": company.name,
                        "base_currency": company.base_currency,
                        "tax_id": company.tax_id,
                    },
                    provenance=self._provenance("companies", company.id),
                )
            )

        # 2. Bank Accounts
        bank_accounts = (
            await self.session.scalars(
                select(BankAccount)
                .where(BankAccount.company_id == self.company_id)
                .order_by(BankAccount.id)
            )
        ).all()
        for ba in bank_accounts:
            ba_id = EvidenceNode.make_id(NodeType.BANK_ACCOUNT, ba.id)
            graph.add_node(
                EvidenceNode(
                    id=ba_id,
                    node_type=NodeType.BANK_ACCOUNT,
                    record_id=str(ba.id),
                    company_id=self._cid_str,
                    label=f"Bank Account: {ba.account_name} ({ba.currency})",
                    properties={
                        "account_name": ba.account_name,
                        "account_number": ba.account_number,
                        "currency": ba.currency,
                        "is_active": ba.is_active,
                    },
                    provenance=self._provenance("bank_accounts", ba.id),
                )
            )
            if company is not None:
                graph.add_edge(
                    EvidenceEdge(
                        id=EvidenceEdge.make_id(comp_node_id, EdgeType.BELONGS_TO_COMPANY, ba_id),
                        source_id=comp_node_id,
                        target_id=ba_id,
                        edge_type=EdgeType.BELONGS_TO_COMPANY,
                        company_id=self._cid_str,
                        provenance=self._provenance("bank_accounts", ba.id),
                    )
                )

        # 3. Ledger Accounts
        ledger_accounts = (
            await self.session.scalars(
                select(LedgerAccount)
                .where(LedgerAccount.company_id == self.company_id)
                .order_by(LedgerAccount.account_code)
            )
        ).all()
        for la in ledger_accounts:
            la_id = EvidenceNode.make_id(NodeType.LEDGER_ACCOUNT, la.id)
            graph.add_node(
                EvidenceNode(
                    id=la_id,
                    node_type=NodeType.LEDGER_ACCOUNT,
                    record_id=str(la.id),
                    company_id=self._cid_str,
                    label=f"GL Account: {la.account_code} - {la.name}",
                    properties={
                        "account_code": la.account_code,
                        "name": la.name,
                        "account_type": la.account_type,
                        "currency": la.currency,
                    },
                    provenance=self._provenance("ledger_accounts", la.id),
                )
            )
            if company is not None:
                graph.add_edge(
                    EvidenceEdge(
                        id=EvidenceEdge.make_id(comp_node_id, EdgeType.BELONGS_TO_COMPANY, la_id),
                        source_id=comp_node_id,
                        target_id=la_id,
                        edge_type=EdgeType.BELONGS_TO_COMPANY,
                        company_id=self._cid_str,
                        provenance=self._provenance("ledger_accounts", la.id),
                    )
                )

        # 4. Vendors
        vendors = (
            await self.session.scalars(
                select(Vendor).where(Vendor.company_id == self.company_id).order_by(Vendor.name)
            )
        ).all()
        for v in vendors:
            v_id = EvidenceNode.make_id(NodeType.VENDOR, v.id)
            graph.add_node(
                EvidenceNode(
                    id=v_id,
                    node_type=NodeType.VENDOR,
                    record_id=str(v.id),
                    company_id=self._cid_str,
                    label=f"Vendor: {v.name}",
                    properties={
                        "name": v.name,
                        "tax_id": v.tax_id,
                        "status": v.status.value,
                    },
                    provenance=self._provenance("vendors", v.id),
                )
            )
            if company is not None:
                graph.add_edge(
                    EvidenceEdge(
                        id=EvidenceEdge.make_id(comp_node_id, EdgeType.BELONGS_TO_COMPANY, v_id),
                        source_id=comp_node_id,
                        target_id=v_id,
                        edge_type=EdgeType.BELONGS_TO_COMPANY,
                        company_id=self._cid_str,
                        provenance=self._provenance("vendors", v.id),
                    )
                )
            if v.bank_account_id:
                ba_node_id = EvidenceNode.make_id(NodeType.BANK_ACCOUNT, v.bank_account_id)
                if graph.has_node(ba_node_id):
                    graph.add_edge(
                        EvidenceEdge(
                            id=EvidenceEdge.make_id(v_id, EdgeType.VENDOR_BANK_ACCOUNT, ba_node_id),
                            source_id=v_id,
                            target_id=ba_node_id,
                            edge_type=EdgeType.VENDOR_BANK_ACCOUNT,
                            company_id=self._cid_str,
                            provenance=self._provenance("vendors", v.id),
                        )
                    )

        # 5. Customers
        customers = (
            await self.session.scalars(
                select(Customer)
                .where(Customer.company_id == self.company_id)
                .order_by(Customer.name)
            )
        ).all()
        for cust in customers:
            cust_id = EvidenceNode.make_id(NodeType.CUSTOMER, cust.id)
            graph.add_node(
                EvidenceNode(
                    id=cust_id,
                    node_type=NodeType.CUSTOMER,
                    record_id=str(cust.id),
                    company_id=self._cid_str,
                    label=f"Customer: {cust.name}",
                    properties={"name": cust.name, "status": cust.status.value},
                    provenance=self._provenance("customers", cust.id),
                )
            )
            if company is not None:
                graph.add_edge(
                    EvidenceEdge(
                        id=EvidenceEdge.make_id(
                            comp_node_id, EdgeType.CUSTOMER_OF_COMPANY, cust_id
                        ),
                        source_id=comp_node_id,
                        target_id=cust_id,
                        edge_type=EdgeType.CUSTOMER_OF_COMPANY,
                        company_id=self._cid_str,
                        provenance=self._provenance("customers", cust.id),
                    )
                )

        # 6. Purchase Orders & Lines
        pos = (
            await self.session.scalars(
                select(PurchaseOrder)
                .options(selectinload(PurchaseOrder.lines))
                .where(PurchaseOrder.company_id == self.company_id)
                .order_by(PurchaseOrder.order_date, PurchaseOrder.id)
            )
        ).all()
        for po in pos:
            po_id = EvidenceNode.make_id(NodeType.PURCHASE_ORDER, po.id)
            graph.add_node(
                EvidenceNode(
                    id=po_id,
                    node_type=NodeType.PURCHASE_ORDER,
                    record_id=str(po.id),
                    company_id=self._cid_str,
                    label=f"PO: {po.po_number} ({po.total} {po.currency})",
                    properties={
                        "po_number": po.po_number,
                        "order_date": str(po.order_date),
                        "currency": po.currency,
                        "total": str(po.total),
                        "status": po.status.value,
                    },
                    provenance=self._provenance("purchase_orders", po.id),
                )
            )
            v_id = EvidenceNode.make_id(NodeType.VENDOR, po.vendor_id)
            if graph.has_node(v_id):
                graph.add_edge(
                    EvidenceEdge(
                        id=EvidenceEdge.make_id(po_id, EdgeType.ISSUED_TO_VENDOR, v_id),
                        source_id=po_id,
                        target_id=v_id,
                        edge_type=EdgeType.ISSUED_TO_VENDOR,
                        company_id=self._cid_str,
                        provenance=self._provenance("purchase_orders", po.id),
                    )
                )

            for pol in po.lines:
                pol_id = EvidenceNode.make_id(NodeType.PO_LINE, pol.id)
                graph.add_node(
                    EvidenceNode(
                        id=pol_id,
                        node_type=NodeType.PO_LINE,
                        record_id=str(pol.id),
                        company_id=self._cid_str,
                        label=f"PO Line: {pol.description} (qty={pol.quantity}, amt={pol.amount})",
                        properties={
                            "description": pol.description,
                            "quantity": str(pol.quantity),
                            "unit_price": str(pol.unit_price),
                            "amount": str(pol.amount),
                        },
                        provenance=self._provenance("purchase_order_lines", pol.id),
                    )
                )
                graph.add_edge(
                    EvidenceEdge(
                        id=EvidenceEdge.make_id(po_id, EdgeType.CONTAINS_LINE, pol_id),
                        source_id=po_id,
                        target_id=pol_id,
                        edge_type=EdgeType.CONTAINS_LINE,
                        company_id=self._cid_str,
                        provenance=self._provenance("purchase_order_lines", pol.id),
                    )
                )

        # 7. Invoices & Lines
        invoices = (
            await self.session.scalars(
                select(Invoice)
                .options(selectinload(Invoice.lines))
                .where(Invoice.company_id == self.company_id)
                .order_by(Invoice.invoice_date, Invoice.id)
            )
        ).all()
        for inv in invoices:
            inv_id = EvidenceNode.make_id(NodeType.INVOICE, inv.id)
            graph.add_node(
                EvidenceNode(
                    id=inv_id,
                    node_type=NodeType.INVOICE,
                    record_id=str(inv.id),
                    company_id=self._cid_str,
                    label=f"Invoice: {inv.invoice_number} ({inv.total} {inv.currency})",
                    properties={
                        "invoice_number": inv.invoice_number,
                        "invoice_date": str(inv.invoice_date),
                        "due_date": str(inv.due_date) if inv.due_date else None,
                        "currency": inv.currency,
                        "subtotal": str(inv.subtotal),
                        "tax": str(inv.tax),
                        "total": str(inv.total),
                        "status": inv.status.value,
                        "source_document_id": inv.source_document_id,
                    },
                    provenance=self._provenance("invoices", inv.id),
                )
            )
            v_id = EvidenceNode.make_id(NodeType.VENDOR, inv.vendor_id)
            if graph.has_node(v_id):
                graph.add_edge(
                    EvidenceEdge(
                        id=EvidenceEdge.make_id(inv_id, EdgeType.ISSUED_BY_VENDOR, v_id),
                        source_id=inv_id,
                        target_id=v_id,
                        edge_type=EdgeType.ISSUED_BY_VENDOR,
                        company_id=self._cid_str,
                        provenance=self._provenance("invoices", inv.id),
                    )
                )
            if inv.po_id:
                po_id = EvidenceNode.make_id(NodeType.PURCHASE_ORDER, inv.po_id)
                if graph.has_node(po_id):
                    graph.add_edge(
                        EvidenceEdge(
                            id=EvidenceEdge.make_id(inv_id, EdgeType.REFERENCES_PO, po_id),
                            source_id=inv_id,
                            target_id=po_id,
                            edge_type=EdgeType.REFERENCES_PO,
                            company_id=self._cid_str,
                            provenance=self._provenance("invoices", inv.id),
                        )
                    )

            for il in inv.lines:
                il_id = EvidenceNode.make_id(NodeType.INVOICE_LINE, il.id)
                graph.add_node(
                    EvidenceNode(
                        id=il_id,
                        node_type=NodeType.INVOICE_LINE,
                        record_id=str(il.id),
                        company_id=self._cid_str,
                        label=(
                            f"Invoice Line: {il.description} (qty={il.quantity}, amt={il.amount})"
                        ),
                        properties={
                            "description": il.description,
                            "quantity": str(il.quantity),
                            "unit_price": str(il.unit_price),
                            "amount": str(il.amount),
                        },
                        provenance=self._provenance("invoice_lines", il.id),
                    )
                )
                graph.add_edge(
                    EvidenceEdge(
                        id=EvidenceEdge.make_id(inv_id, EdgeType.CONTAINS_LINE, il_id),
                        source_id=inv_id,
                        target_id=il_id,
                        edge_type=EdgeType.CONTAINS_LINE,
                        company_id=self._cid_str,
                        provenance=self._provenance("invoice_lines", il.id),
                    )
                )
                if il.po_line_id:
                    pol_id = EvidenceNode.make_id(NodeType.PO_LINE, il.po_line_id)
                    if graph.has_node(pol_id):
                        graph.add_edge(
                            EvidenceEdge(
                                id=EvidenceEdge.make_id(il_id, EdgeType.REFERENCES_PO_LINE, pol_id),
                                source_id=il_id,
                                target_id=pol_id,
                                edge_type=EdgeType.REFERENCES_PO_LINE,
                                company_id=self._cid_str,
                                provenance=self._provenance("invoice_lines", il.id),
                            )
                        )

        # 8. Goods Receipts & Lines
        receipts = (
            await self.session.scalars(
                select(GoodsReceipt)
                .options(selectinload(GoodsReceipt.lines))
                .where(GoodsReceipt.company_id == self.company_id)
                .order_by(GoodsReceipt.receipt_date, GoodsReceipt.id)
            )
        ).all()
        for gr in receipts:
            gr_id = EvidenceNode.make_id(NodeType.GOODS_RECEIPT, gr.id)
            graph.add_node(
                EvidenceNode(
                    id=gr_id,
                    node_type=NodeType.GOODS_RECEIPT,
                    record_id=str(gr.id),
                    company_id=self._cid_str,
                    label=f"Goods Receipt: {gr.receipt_number} ({gr.receipt_date})",
                    properties={
                        "receipt_number": gr.receipt_number,
                        "receipt_date": str(gr.receipt_date),
                        "status": gr.status.value,
                    },
                    provenance=self._provenance("goods_receipts", gr.id),
                )
            )
            if gr.po_id:
                po_id = EvidenceNode.make_id(NodeType.PURCHASE_ORDER, gr.po_id)
                if graph.has_node(po_id):
                    graph.add_edge(
                        EvidenceEdge(
                            id=EvidenceEdge.make_id(po_id, EdgeType.FULFILLED_BY_RECEIPT, gr_id),
                            source_id=po_id,
                            target_id=gr_id,
                            edge_type=EdgeType.FULFILLED_BY_RECEIPT,
                            company_id=self._cid_str,
                            provenance=self._provenance("goods_receipts", gr.id),
                        )
                    )

            for grl in gr.lines:
                grl_id = EvidenceNode.make_id(NodeType.RECEIPT_LINE, grl.id)
                graph.add_node(
                    EvidenceNode(
                        id=grl_id,
                        node_type=NodeType.RECEIPT_LINE,
                        record_id=str(grl.id),
                        company_id=self._cid_str,
                        label=f"Receipt Line: {grl.description} (qty_rec={grl.quantity_received})",
                        properties={
                            "description": grl.description,
                            "quantity_received": str(grl.quantity_received),
                        },
                        provenance=self._provenance("goods_receipt_lines", grl.id),
                    )
                )
                graph.add_edge(
                    EvidenceEdge(
                        id=EvidenceEdge.make_id(gr_id, EdgeType.CONTAINS_LINE, grl_id),
                        source_id=gr_id,
                        target_id=grl_id,
                        edge_type=EdgeType.CONTAINS_LINE,
                        company_id=self._cid_str,
                        provenance=self._provenance("goods_receipt_lines", grl.id),
                    )
                )
                if grl.po_line_id:
                    pol_id = EvidenceNode.make_id(NodeType.PO_LINE, grl.po_line_id)
                    if graph.has_node(pol_id):
                        graph.add_edge(
                            EvidenceEdge(
                                id=EvidenceEdge.make_id(
                                    grl_id, EdgeType.RECEIPT_FULFILLS_PO_LINE, pol_id
                                ),
                                source_id=grl_id,
                                target_id=pol_id,
                                edge_type=EdgeType.RECEIPT_FULFILLS_PO_LINE,
                                company_id=self._cid_str,
                                provenance=self._provenance("goods_receipt_lines", grl.id),
                            )
                        )

        # 9. Payments
        payments = (
            await self.session.scalars(
                select(Payment)
                .where(Payment.company_id == self.company_id)
                .order_by(Payment.payment_date, Payment.id)
            )
        ).all()
        for pmt in payments:
            pmt_id = EvidenceNode.make_id(NodeType.PAYMENT, pmt.id)
            graph.add_node(
                EvidenceNode(
                    id=pmt_id,
                    node_type=NodeType.PAYMENT,
                    record_id=str(pmt.id),
                    company_id=self._cid_str,
                    label=f"Payment: {pmt.amount} {pmt.currency} ({pmt.payment_date})",
                    properties={
                        "amount": str(pmt.amount),
                        "currency": pmt.currency,
                        "payment_date": str(pmt.payment_date),
                        "status": pmt.status.value,
                        "reference": pmt.beneficiary_reference,
                    },
                    provenance=self._provenance("payments", pmt.id),
                )
            )
            if pmt.invoice_id:
                inv_id = EvidenceNode.make_id(NodeType.INVOICE, pmt.invoice_id)
                if graph.has_node(inv_id):
                    graph.add_edge(
                        EvidenceEdge(
                            id=EvidenceEdge.make_id(inv_id, EdgeType.PAID_BY_PAYMENT, pmt_id),
                            source_id=inv_id,
                            target_id=pmt_id,
                            edge_type=EdgeType.PAID_BY_PAYMENT,
                            company_id=self._cid_str,
                            provenance=self._provenance("payments", pmt.id),
                        )
                    )
                    graph.add_edge(
                        EvidenceEdge(
                            id=EvidenceEdge.make_id(pmt_id, EdgeType.PAYMENT_PAYS_INVOICE, inv_id),
                            source_id=pmt_id,
                            target_id=inv_id,
                            edge_type=EdgeType.PAYMENT_PAYS_INVOICE,
                            company_id=self._cid_str,
                            provenance=self._provenance("payments", pmt.id),
                        )
                    )
            if pmt.vendor_id:
                v_id = EvidenceNode.make_id(NodeType.VENDOR, pmt.vendor_id)
                if graph.has_node(v_id):
                    graph.add_edge(
                        EvidenceEdge(
                            id=EvidenceEdge.make_id(pmt_id, EdgeType.PAYMENT_TO_VENDOR, v_id),
                            source_id=pmt_id,
                            target_id=v_id,
                            edge_type=EdgeType.PAYMENT_TO_VENDOR,
                            company_id=self._cid_str,
                            provenance=self._provenance("payments", pmt.id),
                        )
                    )
            if pmt.bank_account_id:
                ba_id = EvidenceNode.make_id(NodeType.BANK_ACCOUNT, pmt.bank_account_id)
                if graph.has_node(ba_id):
                    graph.add_edge(
                        EvidenceEdge(
                            id=EvidenceEdge.make_id(pmt_id, EdgeType.PAYMENT_ON_ACCOUNT, ba_id),
                            source_id=pmt_id,
                            target_id=ba_id,
                            edge_type=EdgeType.PAYMENT_ON_ACCOUNT,
                            company_id=self._cid_str,
                            provenance=self._provenance("payments", pmt.id),
                        )
                    )

        # 10. Bank Transactions
        bank_txs = (
            await self.session.scalars(
                select(BankTransaction)
                .where(BankTransaction.company_id == self.company_id)
                .order_by(BankTransaction.transaction_date, BankTransaction.id)
            )
        ).all()
        for bt in bank_txs:
            bt_id = EvidenceNode.make_id(NodeType.BANK_TRANSACTION, bt.id)
            graph.add_node(
                EvidenceNode(
                    id=bt_id,
                    node_type=NodeType.BANK_TRANSACTION,
                    record_id=str(bt.id),
                    company_id=self._cid_str,
                    label=(
                        f"Bank Tx: {bt.amount} {bt.currency} ({bt.direction.value}) "
                        f"ref={bt.reference}"
                    ),
                    properties={
                        "amount": str(bt.amount),
                        "currency": bt.currency,
                        "direction": bt.direction.value,
                        "counterparty": bt.counterparty,
                        "reference": bt.reference,
                        "transaction_date": str(bt.transaction_date),
                        "status": bt.status.value,
                    },
                    provenance=self._provenance("bank_transactions", bt.id),
                )
            )
            if bt.bank_account_id:
                ba_id = EvidenceNode.make_id(NodeType.BANK_ACCOUNT, bt.bank_account_id)
                if graph.has_node(ba_id):
                    graph.add_edge(
                        EvidenceEdge(
                            id=EvidenceEdge.make_id(
                                bt_id, EdgeType.RECORDED_ON_BANK_ACCOUNT, ba_id
                            ),
                            source_id=bt_id,
                            target_id=ba_id,
                            edge_type=EdgeType.RECORDED_ON_BANK_ACCOUNT,
                            company_id=self._cid_str,
                            provenance=self._provenance("bank_transactions", bt.id),
                        )
                    )

        # Link Payments to Bank Transactions
        bt_by_ref: dict[tuple[str, Decimal, str], BankTransaction] = {}
        for bt in bank_txs:
            if bt.reference:
                bt_by_ref[(bt.reference, bt.amount, bt.currency)] = bt

        for pmt in payments:
            target_bt_id = None
            if pmt.bank_transaction_id:
                candidate_id = EvidenceNode.make_id(
                    NodeType.BANK_TRANSACTION, pmt.bank_transaction_id
                )
                if graph.has_node(candidate_id):
                    target_bt_id = candidate_id
            elif pmt.beneficiary_reference:
                matched_bt = bt_by_ref.get((pmt.beneficiary_reference, pmt.amount, pmt.currency))
                if matched_bt:
                    candidate_id = EvidenceNode.make_id(NodeType.BANK_TRANSACTION, matched_bt.id)
                    if graph.has_node(candidate_id):
                        target_bt_id = candidate_id

            if target_bt_id:
                pmt_id = EvidenceNode.make_id(NodeType.PAYMENT, pmt.id)
                graph.add_edge(
                    EvidenceEdge(
                        id=EvidenceEdge.make_id(pmt_id, EdgeType.APPEARS_AS_BANK_TX, target_bt_id),
                        source_id=pmt_id,
                        target_id=target_bt_id,
                        edge_type=EdgeType.APPEARS_AS_BANK_TX,
                        company_id=self._cid_str,
                        provenance=self._provenance("payments", pmt.id),
                    )
                )

        # 11. Journal Entries & Lines
        journal_entries = (
            await self.session.scalars(
                select(JournalEntry)
                .options(selectinload(JournalEntry.lines))
                .where(JournalEntry.company_id == self.company_id)
                .order_by(JournalEntry.entry_date, JournalEntry.id)
            )
        ).all()
        for je in journal_entries:
            je_id = EvidenceNode.make_id(NodeType.JOURNAL_ENTRY, je.id)
            graph.add_node(
                EvidenceNode(
                    id=je_id,
                    node_type=NodeType.JOURNAL_ENTRY,
                    record_id=str(je.id),
                    company_id=self._cid_str,
                    label=f"Journal Entry: {je.reference or 'JE'} ({je.entry_date})",
                    properties={
                        "reference": je.reference,
                        "description": je.description,
                        "entry_date": str(je.entry_date),
                        "status": je.status.value,
                        "source": je.source,
                        "total_debit": str(je.total_debit),
                        "total_credit": str(je.total_credit),
                    },
                    provenance=self._provenance("journal_entries", je.id),
                )
            )
            for jel in je.lines:
                jel_id = EvidenceNode.make_id(NodeType.JOURNAL_ENTRY_LINE, jel.id)
                graph.add_node(
                    EvidenceNode(
                        id=jel_id,
                        node_type=NodeType.JOURNAL_ENTRY_LINE,
                        record_id=str(jel.id),
                        company_id=self._cid_str,
                        label=f"JE Line: dr={jel.debit} cr={jel.credit}",
                        properties={
                            "debit": str(jel.debit),
                            "credit": str(jel.credit),
                            "description": jel.description,
                        },
                        provenance=self._provenance("journal_entry_lines", jel.id),
                    )
                )
                graph.add_edge(
                    EvidenceEdge(
                        id=EvidenceEdge.make_id(je_id, EdgeType.CONTAINS_LINE, jel_id),
                        source_id=je_id,
                        target_id=jel_id,
                        edge_type=EdgeType.CONTAINS_LINE,
                        company_id=self._cid_str,
                        provenance=self._provenance("journal_entry_lines", jel.id),
                    )
                )
                la_id = EvidenceNode.make_id(NodeType.LEDGER_ACCOUNT, jel.ledger_account_id)
                if graph.has_node(la_id):
                    graph.add_edge(
                        EvidenceEdge(
                            id=EvidenceEdge.make_id(jel_id, EdgeType.POSTS_TO_LEDGER, la_id),
                            source_id=jel_id,
                            target_id=la_id,
                            edge_type=EdgeType.POSTS_TO_LEDGER,
                            company_id=self._cid_str,
                            provenance=self._provenance("journal_entry_lines", jel.id),
                        )
                    )

        # Link Bank Transactions to Journal Entries
        for bt in bank_txs:
            if bt.journal_entry_id:
                bt_id = EvidenceNode.make_id(NodeType.BANK_TRANSACTION, bt.id)
                je_id = EvidenceNode.make_id(NodeType.JOURNAL_ENTRY, bt.journal_entry_id)
                if graph.has_node(bt_id) and graph.has_node(je_id):
                    graph.add_edge(
                        EvidenceEdge(
                            id=EvidenceEdge.make_id(bt_id, EdgeType.MAPPED_TO_JOURNAL_ENTRY, je_id),
                            source_id=bt_id,
                            target_id=je_id,
                            edge_type=EdgeType.MAPPED_TO_JOURNAL_ENTRY,
                            company_id=self._cid_str,
                            provenance=self._provenance("bank_transactions", bt.id),
                        )
                    )

        # 12. Contracts
        contracts = (
            await self.session.scalars(
                select(Contract).where(Contract.company_id == self.company_id).order_by(Contract.id)
            )
        ).all()
        for c in contracts:
            c_id = EvidenceNode.make_id(NodeType.CONTRACT, c.id)
            graph.add_node(
                EvidenceNode(
                    id=c_id,
                    node_type=NodeType.CONTRACT,
                    record_id=str(c.id),
                    company_id=self._cid_str,
                    label=f"Contract: {c.contract_number} (val={c.value})",
                    properties={
                        "contract_number": c.contract_number,
                        "start_date": str(c.start_date),
                        "end_date": str(c.end_date) if c.end_date else None,
                        "value": str(c.value) if c.value is not None else None,
                        "status": c.status.value,
                    },
                    provenance=self._provenance("contracts", c.id),
                )
            )
            if c.counterparty_id:
                v_id = EvidenceNode.make_id(NodeType.VENDOR, c.counterparty_id)
                if graph.has_node(v_id):
                    graph.add_edge(
                        EvidenceEdge(
                            id=EvidenceEdge.make_id(c_id, EdgeType.CONTRACT_WITH_VENDOR, v_id),
                            source_id=c_id,
                            target_id=v_id,
                            edge_type=EdgeType.CONTRACT_WITH_VENDOR,
                            company_id=self._cid_str,
                            provenance=self._provenance("contracts", c.id),
                        )
                    )

        # 13. Expense Reports
        expenses = (
            await self.session.scalars(
                select(ExpenseReport)
                .where(ExpenseReport.company_id == self.company_id)
                .order_by(ExpenseReport.id)
            )
        ).all()
        for er in expenses:
            er_id = EvidenceNode.make_id(NodeType.EXPENSE_REPORT, er.id)
            graph.add_node(
                EvidenceNode(
                    id=er_id,
                    node_type=NodeType.EXPENSE_REPORT,
                    record_id=str(er.id),
                    company_id=self._cid_str,
                    label=f"Expense: {er.report_number} ({er.total} {er.currency})",
                    properties={
                        "report_number": er.report_number,
                        "expense_date": str(er.expense_date),
                        "currency": er.currency,
                        "total": str(er.total),
                        "status": er.status.value,
                    },
                    provenance=self._provenance("expense_reports", er.id),
                )
            )
            if company is not None:
                graph.add_edge(
                    EvidenceEdge(
                        id=EvidenceEdge.make_id(comp_node_id, EdgeType.BELONGS_TO_COMPANY, er_id),
                        source_id=comp_node_id,
                        target_id=er_id,
                        edge_type=EdgeType.BELONGS_TO_COMPANY,
                        company_id=self._cid_str,
                        provenance=self._provenance("expense_reports", er.id),
                    )
                )

        # 14. FX Rates (Reference nodes for multi-currency transactions)
        fx_rates = (
            await self.session.scalars(select(FxRate).order_by(FxRate.effective_date))
        ).all()

        # Add FX rate nodes for all pairs matching tenant currencies
        for fx in fx_rates:
            if company and (
                fx.base_currency == company.base_currency
                or fx.quote_currency == company.base_currency
            ):
                fx_id = EvidenceNode.make_id(NodeType.FX_RATE, fx.id)
                if not graph.has_node(fx_id):
                    graph.add_node(
                        EvidenceNode(
                            id=fx_id,
                            node_type=NodeType.FX_RATE,
                            record_id=str(fx.id),
                            company_id=self._cid_str,
                            label=(
                                f"FX: {fx.base_currency}/{fx.quote_currency} = {fx.rate} "
                                f"({fx.effective_date})"
                            ),
                            properties={
                                "base_currency": fx.base_currency,
                                "quote_currency": fx.quote_currency,
                                "rate": str(fx.rate),
                                "effective_date": str(fx.effective_date),
                            },
                            provenance=self._provenance("fx_rates", fx.id),
                        )
                    )

        fx_lookup: dict[tuple[str, str, Any], FxRate] = {}
        for r in fx_rates:
            fx_lookup[(r.base_currency, r.quote_currency, r.effective_date)] = r
            fx_lookup[(r.quote_currency, r.base_currency, r.effective_date)] = r

        for inv in invoices:
            if company and inv.currency != company.base_currency:
                fx = fx_lookup.get((inv.currency, company.base_currency, inv.invoice_date))
                if fx:
                    fx_id = EvidenceNode.make_id(NodeType.FX_RATE, fx.id)
                    inv_id = EvidenceNode.make_id(NodeType.INVOICE, inv.id)
                    if graph.has_node(fx_id):
                        graph.add_edge(
                            EvidenceEdge(
                                id=EvidenceEdge.make_id(inv_id, EdgeType.CONVERTED_WITH_FX, fx_id),
                                source_id=inv_id,
                                target_id=fx_id,
                                edge_type=EdgeType.CONVERTED_WITH_FX,
                                company_id=self._cid_str,
                                provenance=self._provenance("fx_rates", fx.id),
                            )
                        )

        # 15. Reconciliation Results & Matches
        rec_results = (
            await self.session.scalars(
                select(ReconciliationResult)
                .options(selectinload(ReconciliationResult.matches))
                .where(ReconciliationResult.company_id == self.company_id)
                .order_by(ReconciliationResult.created_at, ReconciliationResult.id)
            )
        ).all()
        for rr in rec_results:
            rr_id = EvidenceNode.make_id(NodeType.RECONCILIATION_RESULT, rr.id)
            graph.add_node(
                EvidenceNode(
                    id=rr_id,
                    node_type=NodeType.RECONCILIATION_RESULT,
                    record_id=str(rr.id),
                    company_id=self._cid_str,
                    label=(
                        f"Rec Result: {rr.reconciliation_type} ({rr.status.value}) "
                        f"impact={rr.financial_impact}"
                    ),
                    properties={
                        "reconciliation_type": rr.reconciliation_type,
                        "status": rr.status.value,
                        "confidence": str(rr.confidence) if rr.confidence else None,
                        "financial_impact": str(rr.financial_impact),
                        "fx_conversion_applied": rr.fx_conversion_applied,
                        "details": rr.details,
                    },
                    provenance=self._provenance("reconciliation_results", rr.id),
                )
            )

            # Link matches
            for m in rr.matches:
                left_id = f"{m.left_ref_type}:{m.left_ref_id}"
                right_id = f"{m.right_ref_type}:{m.right_ref_id}"

                # Link reconciliation result to both records
                if graph.has_node(left_id):
                    graph.add_edge(
                        EvidenceEdge(
                            id=EvidenceEdge.make_id(rr_id, EdgeType.EVALUATES_RECORD, left_id),
                            source_id=rr_id,
                            target_id=left_id,
                            edge_type=EdgeType.EVALUATES_RECORD,
                            company_id=self._cid_str,
                            properties={"match_type": m.match_type},
                            provenance=self._provenance("reconciliation_matches", m.id),
                        )
                    )
                if graph.has_node(right_id):
                    graph.add_edge(
                        EvidenceEdge(
                            id=EvidenceEdge.make_id(rr_id, EdgeType.EVALUATES_RECORD, right_id),
                            source_id=rr_id,
                            target_id=right_id,
                            edge_type=EdgeType.EVALUATES_RECORD,
                            company_id=self._cid_str,
                            properties={"match_type": m.match_type},
                            provenance=self._provenance("reconciliation_matches", m.id),
                        )
                    )

                # Link left and right match records directly
                if graph.has_node(left_id) and graph.has_node(right_id):
                    graph.add_edge(
                        EvidenceEdge(
                            id=EvidenceEdge.make_id(
                                left_id, EdgeType.MATCHED_IN_RECONCILIATION, right_id
                            ),
                            source_id=left_id,
                            target_id=right_id,
                            edge_type=EdgeType.MATCHED_IN_RECONCILIATION,
                            company_id=self._cid_str,
                            properties={
                                "match_type": m.match_type,
                                "reconciliation_result_id": str(rr.id),
                            },
                            provenance=self._provenance("reconciliation_matches", m.id),
                        )
                    )

        # 16. Exceptions & Supporting Evidence
        exceptions = (
            await self.session.scalars(
                select(ExceptionRecord)
                .options(selectinload(ExceptionRecord.evidence))
                .where(ExceptionRecord.company_id == self.company_id)
                .order_by(ExceptionRecord.created_at, ExceptionRecord.id)
            )
        ).all()
        for exc in exceptions:
            exc_id = EvidenceNode.make_id(NodeType.EXCEPTION, exc.id)
            graph.add_node(
                EvidenceNode(
                    id=exc_id,
                    node_type=NodeType.EXCEPTION,
                    record_id=str(exc.id),
                    company_id=self._cid_str,
                    label=(
                        f"Exception: {exc.type.value} ({exc.severity.value}) "
                        f"impact={exc.financial_impact} {exc.currency}"
                    ),
                    properties={
                        "type": exc.type.value,
                        "severity": exc.severity.value,
                        "status": exc.status.value,
                        "financial_impact": str(exc.financial_impact),
                        "currency": exc.currency,
                        "confidence": str(exc.confidence) if exc.confidence else None,
                        "root_cause": exc.root_cause,
                        "recommended_action": exc.recommended_action,
                    },
                    provenance=self._provenance("exceptions", exc.id),
                )
            )

            # Link primary subjects
            source_map = [
                (exc.source_invoice_id, NodeType.INVOICE),
                (exc.source_po_id, NodeType.PURCHASE_ORDER),
                (exc.source_receipt_id, NodeType.GOODS_RECEIPT),
                (exc.source_payment_id, NodeType.PAYMENT),
                (exc.source_bank_txn_id, NodeType.BANK_TRANSACTION),
                (exc.source_journal_entry_id, NodeType.JOURNAL_ENTRY),
            ]
            for src_id, node_type in source_map:
                if src_id:
                    target_node_id = EvidenceNode.make_id(node_type, src_id)
                    if graph.has_node(target_node_id):
                        graph.add_edge(
                            EvidenceEdge(
                                id=EvidenceEdge.make_id(
                                    exc_id, EdgeType.SUBJECT_OF_EXCEPTION, target_node_id
                                ),
                                source_id=exc_id,
                                target_id=target_node_id,
                                edge_type=EdgeType.SUBJECT_OF_EXCEPTION,
                                company_id=self._cid_str,
                                provenance=self._provenance("exceptions", exc.id),
                            )
                        )

            # Link supporting evidence items
            for ev in exc.evidence:
                ev_target_id = f"{ev.evidence_type}:{ev.evidence_ref_id}"
                if graph.has_node(ev_target_id):
                    edge_type = (
                        EdgeType.GENERATED_BY_RECONCILIATION
                        if ev.evidence_type == "RECONCILIATION_RESULT"
                        else EdgeType.SUPPORTED_BY_EVIDENCE
                    )
                    graph.add_edge(
                        EvidenceEdge(
                            id=EvidenceEdge.make_id(exc_id, edge_type, ev_target_id),
                            source_id=exc_id,
                            target_id=ev_target_id,
                            edge_type=edge_type,
                            company_id=self._cid_str,
                            properties={"description": ev.description},
                            provenance=self._provenance("exception_evidence", ev.id),
                        )
                    )

        return graph
