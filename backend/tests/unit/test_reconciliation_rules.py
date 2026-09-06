"""Unit tests for deterministic reconciliation rules and calculators."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from app.db.models.banking import BankTransaction, Payment
from app.db.models.ledger import JournalEntry, JournalEntryLine, LedgerAccount
from app.db.models.procurement import (
    GoodsReceipt,
    GoodsReceiptLine,
    Invoice,
    InvoiceLine,
    PurchaseOrder,
    PurchaseOrderLine,
)
from app.domain.enums import (
    BankTransactionDirection,
    DocumentStatus,
    ExceptionType,
    ReconciliationStatus,
)
from app.reconciliation.config import ReconciliationConfig
from app.reconciliation.rules import (
    evaluate_three_way_match,
    match_bank_tx_to_payments,
    match_invoice_to_po,
    match_invoice_to_receipts,
    match_payments_to_invoice,
    review_accrual_entry,
    verify_accrual_reversals,
    verify_gl_mapping,
    verify_journal_entry_balance,
)


async def test_match_invoice_to_po_exact():
    cid = uuid.uuid4()
    po = PurchaseOrder(
        id=uuid.uuid4(),
        company_id=cid,
        po_number="PO-100",
        order_date=date(2026, 1, 10),
        currency="USD",
        total=Decimal("5000.00"),
        status=DocumentStatus.OPEN,
    )
    po.lines = [
        PurchaseOrderLine(
            id=uuid.uuid4(),
            purchase_order_id=po.id,
            description="Servers",
            quantity=Decimal("10.0000"),
            unit_price=Decimal("500.0000"),
            amount=Decimal("5000.00"),
        )
    ]
    inv = Invoice(
        id=uuid.uuid4(),
        company_id=cid,
        po_id=po.id,
        invoice_number="INV-100",
        invoice_date=date(2026, 1, 15),
        currency="USD",
        total=Decimal("5000.00"),
        status=DocumentStatus.OPEN,
    )
    inv.lines = [
        InvoiceLine(
            id=uuid.uuid4(),
            invoice_id=inv.id,
            po_line_id=po.lines[0].id,
            description="Servers",
            quantity=Decimal("10.0000"),
            unit_price=Decimal("500.0000"),
            amount=Decimal("5000.00"),
        )
    ]

    res = await match_invoice_to_po(inv, po, None, ReconciliationConfig())
    assert res.status == ReconciliationStatus.MATCHED
    assert res.financial_impact == Decimal("0.00")


async def test_match_invoice_to_po_price_mismatch():
    cid = uuid.uuid4()
    pol_id = uuid.uuid4()
    po = PurchaseOrder(
        id=uuid.uuid4(),
        company_id=cid,
        po_number="PO-101",
        order_date=date(2026, 1, 10),
        currency="USD",
        total=Decimal("5000.00"),
    )
    po.lines = [
        PurchaseOrderLine(
            id=pol_id,
            purchase_order_id=po.id,
            quantity=Decimal("10.0000"),
            unit_price=Decimal("500.0000"),
            amount=Decimal("5000.00"),
        )
    ]
    inv = Invoice(
        id=uuid.uuid4(),
        company_id=cid,
        po_id=po.id,
        invoice_number="INV-101",
        invoice_date=date(2026, 1, 15),
        currency="USD",
        total=Decimal("6500.00"),
    )
    inv.lines = [
        InvoiceLine(
            id=uuid.uuid4(),
            invoice_id=inv.id,
            po_line_id=pol_id,
            quantity=Decimal("10.0000"),
            unit_price=Decimal("650.0000"),  # 150 higher
            amount=Decimal("6500.00"),
        )
    ]

    res = await match_invoice_to_po(inv, po, None, ReconciliationConfig())
    assert res.status == ReconciliationStatus.MISMATCH
    assert res.exception_type == ExceptionType.PO_MISMATCH
    assert res.financial_impact == Decimal("1500.00")  # 150 * 10


def test_match_invoice_to_receipts_mismatch():
    cid = uuid.uuid4()
    inv = Invoice(
        id=uuid.uuid4(),
        company_id=cid,
        invoice_number="INV-200",
        total=Decimal("10000.00"),
    )
    inv.lines = [
        InvoiceLine(
            id=uuid.uuid4(),
            invoice_id=inv.id,
            quantity=Decimal("100.0000"),
            unit_price=Decimal("100.0000"),
            amount=Decimal("10000.00"),
        )
    ]
    gr = GoodsReceipt(
        id=uuid.uuid4(),
        company_id=cid,
        receipt_number="GR-200",
    )
    gr.lines = [
        GoodsReceiptLine(
            id=uuid.uuid4(),
            goods_receipt_id=gr.id,
            quantity_received=Decimal("80.0000"),  # Short by 20 units
        )
    ]

    res = match_invoice_to_receipts(inv, None, [gr], ReconciliationConfig())
    assert res.status == ReconciliationStatus.MISMATCH
    assert res.exception_type == ExceptionType.RECEIPT_MISMATCH
    assert res.financial_impact == Decimal("2000.00")  # 20 * 100


async def test_three_way_match_clean():
    cid = uuid.uuid4()
    pol_id = uuid.uuid4()
    po = PurchaseOrder(
        id=uuid.uuid4(),
        company_id=cid,
        po_number="PO-3WAY",
        currency="INR",
        total=Decimal("250000.00"),
    )
    po.lines = [
        PurchaseOrderLine(
            id=pol_id,
            purchase_order_id=po.id,
            quantity=Decimal("250.0000"),
            unit_price=Decimal("1000.0000"),
            amount=Decimal("250000.00"),
        )
    ]
    gr = GoodsReceipt(
        id=uuid.uuid4(),
        company_id=cid,
        po_id=po.id,
        receipt_number="GR-3WAY",
    )
    gr.lines = [
        GoodsReceiptLine(
            id=uuid.uuid4(),
            goods_receipt_id=gr.id,
            quantity_received=Decimal("250.0000"),
        )
    ]
    inv = Invoice(
        id=uuid.uuid4(),
        company_id=cid,
        po_id=po.id,
        invoice_number="INV-3WAY",
        currency="INR",
        total=Decimal("250000.00"),
    )
    inv.lines = [
        InvoiceLine(
            id=uuid.uuid4(),
            invoice_id=inv.id,
            po_line_id=pol_id,
            quantity=Decimal("250.0000"),
            unit_price=Decimal("1000.0000"),
            amount=Decimal("250000.00"),
        )
    ]

    res = await evaluate_three_way_match(inv, po, [gr], None, ReconciliationConfig())
    assert res.status == ReconciliationStatus.MATCHED
    assert res.financial_impact == Decimal("0.00")


async def test_three_way_match_missing_po():
    cid = uuid.uuid4()
    inv = Invoice(
        id=uuid.uuid4(),
        company_id=cid,
        po_id=None,
        invoice_number="INV-NOPO",
        total=Decimal("175000.00"),
    )
    res = await evaluate_three_way_match(inv, None, [], None, ReconciliationConfig())
    assert res.status == ReconciliationStatus.MISSING
    assert res.exception_type == ExceptionType.MISSING_DOCUMENT
    assert res.financial_impact == Decimal("175000.00")


async def test_payment_matching_partial():
    cid = uuid.uuid4()
    inv = Invoice(
        id=uuid.uuid4(),
        company_id=cid,
        invoice_number="INV-PART",
        currency="INR",
        total=Decimal("100000.00"),
    )
    p = Payment(
        id=uuid.uuid4(),
        company_id=cid,
        invoice_id=inv.id,
        amount=Decimal("70000.00"),
        currency="INR",
        payment_date=date(2026, 1, 20),
    )

    res = await match_payments_to_invoice(inv, [p], None, ReconciliationConfig())
    assert res.status == ReconciliationStatus.PARTIAL
    assert res.financial_impact == Decimal("30000.00")  # 30k remaining


async def test_payment_matching_duplicate():
    cid = uuid.uuid4()
    inv = Invoice(
        id=uuid.uuid4(),
        company_id=cid,
        invoice_number="INV-DUP",
        currency="INR",
        total=Decimal("120000.00"),
    )
    p1 = Payment(
        id=uuid.uuid4(),
        company_id=cid,
        invoice_id=inv.id,
        amount=Decimal("120000.00"),
        currency="INR",
        payment_date=date(2026, 1, 20),
    )
    p2 = Payment(
        id=uuid.uuid4(),
        company_id=cid,
        invoice_id=inv.id,
        amount=Decimal("120000.00"),
        currency="INR",
        payment_date=date(2026, 1, 22),
    )

    res = await match_payments_to_invoice(inv, [p1, p2], None, ReconciliationConfig())
    assert res.status == ReconciliationStatus.MISMATCH
    assert res.exception_type == ExceptionType.DUPLICATE_PAYMENT
    assert res.financial_impact == Decimal("120000.00")


async def test_payment_matching_fragmentation():
    cid = uuid.uuid4()
    inv = Invoice(
        id=uuid.uuid4(),
        company_id=cid,
        invoice_number="INV-FRAG",
        currency="INR",
        total=Decimal("1450000.00"),
    )
    pmts = [
        Payment(
            id=uuid.uuid4(),
            company_id=cid,
            invoice_id=inv.id,
            amount=Decimal("100000.00"),
            currency="INR",
            payment_date=date(2026, 1, 20),
        )
        for _ in range(14)
    ]

    res = await match_payments_to_invoice(inv, pmts, None, ReconciliationConfig())
    assert res.status == ReconciliationStatus.MISMATCH
    assert res.exception_type == ExceptionType.PAYMENT_FRAGMENTATION
    assert res.financial_impact == Decimal("1450000.00")


async def test_bank_payment_fee_deduction():
    cid = uuid.uuid4()
    b_acc_id = uuid.uuid4()
    p = Payment(
        id=uuid.uuid4(),
        company_id=cid,
        bank_account_id=b_acc_id,
        amount=Decimal("5000.00"),
        currency="USD",
        payment_date=date(2026, 2, 1),
        beneficiary_reference="REF-WIRE-01",
    )
    bt = BankTransaction(
        id=uuid.uuid4(),
        company_id=cid,
        bank_account_id=b_acc_id,
        amount=Decimal("5025.00"),  #  wire fee
        currency="USD",
        direction=BankTransactionDirection.DEBIT,
        transaction_date=date(2026, 2, 2),
        reference="REF-WIRE-01",
    )

    res = await match_bank_tx_to_payments(bt, [p], None, ReconciliationConfig())
    assert res.status == ReconciliationStatus.MATCHED
    assert res.differences.get("bank_fee") == Decimal("25.00")


async def test_bank_cash_anomaly():
    cid = uuid.uuid4()
    bt = BankTransaction(
        id=uuid.uuid4(),
        company_id=cid,
        amount=Decimal("300000.00"),
        currency="INR",
        direction=BankTransactionDirection.DEBIT,
        transaction_date=date(2026, 2, 10),
        reference="TXN-UNIDENT-WIRE-OUT-001",
    )

    res = await match_bank_tx_to_payments(bt, [], None, ReconciliationConfig())
    assert res.status == ReconciliationStatus.MISMATCH
    assert res.exception_type == ExceptionType.CASH_ANOMALY
    assert res.financial_impact == Decimal("300000.00")


def test_verify_journal_entry_balance():
    cid = uuid.uuid4()
    je = JournalEntry(
        id=uuid.uuid4(),
        company_id=cid,
        reference="JE-001",
    )
    je.lines = [
        JournalEntryLine(
            id=uuid.uuid4(),
            debit=Decimal("1000.00"),
            credit=Decimal("0.00"),
        ),
        JournalEntryLine(
            id=uuid.uuid4(),
            debit=Decimal("0.00"),
            credit=Decimal("1000.00"),
        ),
    ]

    res = verify_journal_entry_balance(je)
    assert res.status == ReconciliationStatus.MATCHED

    # Out of balance
    je.lines[1].credit = Decimal("900.00")
    res2 = verify_journal_entry_balance(je)
    assert res2.status == ReconciliationStatus.MISMATCH
    assert res2.financial_impact == Decimal("100.00")


def test_verify_gl_mapping_errors():
    cid = uuid.uuid4()
    acc_travel = LedgerAccount(id=uuid.uuid4(), account_code="5100", name="Travel & Entertainment")
    je = JournalEntry(
        id=uuid.uuid4(),
        company_id=cid,
        reference="JE-ERR-001",
        description="Software Infrastructure AWS Cloud",
    )
    je.lines = [
        JournalEntryLine(
            id=uuid.uuid4(),
            ledger_account=acc_travel,
            debit=Decimal("185000.00"),
            credit=Decimal("0.00"),
        )
    ]

    res = verify_gl_mapping(je, ReconciliationConfig())
    assert res is not None
    assert res.status == ReconciliationStatus.MISMATCH
    assert res.exception_type == ExceptionType.GL_MAPPING_ERROR
    assert res.financial_impact == Decimal("185000.00")


def test_review_accrual_entry_anomaly():
    cid = uuid.uuid4()
    je = JournalEntry(
        id=uuid.uuid4(),
        company_id=cid,
        reference="JE-ACCR-001",
        description="Monthly Accrual - Utilities Electricity and Water",
    )
    res = review_accrual_entry(je, ReconciliationConfig())
    assert res is not None
    assert res.status == ReconciliationStatus.MISMATCH
    assert res.exception_type == ExceptionType.ACCRUAL_ANOMALY
    assert res.financial_impact == Decimal("190000.00")


def test_verify_accrual_reversals_missing():
    cid = uuid.uuid4()
    exp_acc_id = uuid.uuid4()
    liab_acc_id = uuid.uuid4()

    prior_je = JournalEntry(
        id=uuid.uuid4(),
        company_id=cid,
        reference="JE-ACCR-PRIOR-01",
        description="Prior Period Legal Services Accrual",
        entry_date=date(2026, 1, 31),
    )
    prior_je.lines = [
        JournalEntryLine(
            id=uuid.uuid4(),
            journal_entry_id=prior_je.id,
            ledger_account_id=exp_acc_id,
            debit=Decimal("45000.00"),
            credit=Decimal("0.00"),
        ),
        JournalEntryLine(
            id=uuid.uuid4(),
            journal_entry_id=prior_je.id,
            ledger_account_id=liab_acc_id,
            debit=Decimal("0.00"),
            credit=Decimal("45000.00"),
        ),
    ]

    # Current period has no reversal
    current_entries: list[JournalEntry] = []

    results = verify_accrual_reversals([prior_je], current_entries, ReconciliationConfig())
    assert len(results) == 1
    res = results[0]
    assert res.status == ReconciliationStatus.MISMATCH
    assert res.exception_type == ExceptionType.ACCRUAL_ANOMALY
    assert res.deterministic_reason == "Missing Prior Period Accrual Reversal"
    assert res.financial_impact == Decimal("45000.00")
    assert res.evidence_ids == [prior_je.id]


def test_verify_accrual_reversals_matching():
    cid = uuid.uuid4()
    exp_acc_id = uuid.uuid4()
    liab_acc_id = uuid.uuid4()

    prior_je = JournalEntry(
        id=uuid.uuid4(),
        company_id=cid,
        reference="JE-ACCR-PRIOR-02",
        description="Prior Period Bonus Accrual",
        entry_date=date(2026, 1, 31),
    )
    prior_je.lines = [
        JournalEntryLine(
            id=uuid.uuid4(),
            journal_entry_id=prior_je.id,
            ledger_account_id=exp_acc_id,
            debit=Decimal("30000.00"),
            credit=Decimal("0.00"),
        ),
        JournalEntryLine(
            id=uuid.uuid4(),
            journal_entry_id=prior_je.id,
            ledger_account_id=liab_acc_id,
            debit=Decimal("0.00"),
            credit=Decimal("30000.00"),
        ),
    ]

    # Current period has proper reversing entry (debit/credit flipped on accounts)
    curr_rev_je = JournalEntry(
        id=uuid.uuid4(),
        company_id=cid,
        reference="JE-REV-02",
        description="Reversal of Prior Period Bonus Accrual",
        entry_date=date(2026, 2, 1),
    )
    curr_rev_je.lines = [
        JournalEntryLine(
            id=uuid.uuid4(),
            journal_entry_id=curr_rev_je.id,
            ledger_account_id=liab_acc_id,
            debit=Decimal("30000.00"),
            credit=Decimal("0.00"),
        ),
        JournalEntryLine(
            id=uuid.uuid4(),
            journal_entry_id=curr_rev_je.id,
            ledger_account_id=exp_acc_id,
            debit=Decimal("0.00"),
            credit=Decimal("30000.00"),
        ),
    ]

    results = verify_accrual_reversals([prior_je], [curr_rev_je], ReconciliationConfig())
    assert len(results) == 0


async def test_bank_duplicate_transaction_detection():
    """FIX 4: Bank-side duplicate transaction detection.

    Before 1:1 payment matching, group bank transactions by
    (bank_account_id, amount, transaction_date, direction, reference).
    Extras must be flagged as ExceptionType.BANK_DUPLICATE instead of falling
    through as unmatched/MISSING.
    """
    cid = uuid.uuid4()
    ba_id = uuid.uuid4()
    tx_date = date(2026, 2, 5)

    bt_orig = BankTransaction(
        id=uuid.uuid4(),
        company_id=cid,
        bank_account_id=ba_id,
        amount=Decimal("15000.00"),
        currency="USD",
        direction=BankTransactionDirection.DEBIT,
        transaction_date=tx_date,
        reference="TXN-WIRE-DUP-01",
    )
    bt_duplicate = BankTransaction(
        id=uuid.uuid4(),
        company_id=cid,
        bank_account_id=ba_id,
        amount=Decimal("15000.00"),
        currency="USD",
        direction=BankTransactionDirection.DEBIT,
        transaction_date=tx_date,
        reference="TXN-WIRE-DUP-01",
    )

    pmt = Payment(
        id=uuid.uuid4(),
        company_id=cid,
        bank_account_id=ba_id,
        amount=Decimal("15000.00"),
        currency="USD",
        payment_date=tx_date,
        beneficiary_reference="TXN-WIRE-DUP-01",
        status=DocumentStatus.PAID,
    )

    account_txs = [bt_orig, bt_duplicate]

    # First transaction matches the payment
    res_orig = await match_bank_tx_to_payments(
        bt_orig, [pmt], None, ReconciliationConfig(), account_transactions=account_txs
    )
    assert res_orig.status == ReconciliationStatus.MATCHED
    assert res_orig.financial_impact == Decimal("0.00")

    # Second transaction is detected as a bank duplicate exception
    res_dup = await match_bank_tx_to_payments(
        bt_duplicate, [pmt], None, ReconciliationConfig(), account_transactions=account_txs
    )
    assert res_dup.status == ReconciliationStatus.MISMATCH
    assert res_dup.exception_type == ExceptionType.BANK_DUPLICATE
    assert res_dup.financial_impact == Decimal("15000.00")
    assert res_dup.differences.get("subtype") == "BANK_DUPLICATE"
    assert "duplicate" in res_dup.deterministic_reason.lower()


async def test_bank_duplicate_transaction_detection_batch():
    """FIX 4: Batch invocation grouping and duplicate detection."""
    cid = uuid.uuid4()
    ba_id = uuid.uuid4()
    tx_date = date(2026, 2, 8)

    bt1 = BankTransaction(
        id=uuid.uuid4(),
        company_id=cid,
        bank_account_id=ba_id,
        amount=Decimal("5000.00"),
        currency="USD",
        direction=BankTransactionDirection.CREDIT,
        transaction_date=tx_date,
        reference="TXN-BATCH-DUP-01",
    )
    bt2 = BankTransaction(
        id=uuid.uuid4(),
        company_id=cid,
        bank_account_id=ba_id,
        amount=Decimal("5000.00"),
        currency="USD",
        direction=BankTransactionDirection.CREDIT,
        transaction_date=tx_date,
        reference="TXN-BATCH-DUP-01",
    )

    batch_res = await match_bank_tx_to_payments(
        [bt1, bt2], [], None, ReconciliationConfig()
    )
    assert len(batch_res) == 2
    # Second item in batch must be flagged as BANK_DUPLICATE
    assert batch_res[1].exception_type == ExceptionType.BANK_DUPLICATE
    assert batch_res[1].status == ReconciliationStatus.MISMATCH
    assert batch_res[1].financial_impact == Decimal("5000.00")

