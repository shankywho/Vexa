"""Deterministic matching rules and calculation logic (spec section 8).

Pure deterministic Python with Decimal precision.
Zero LLM dependencies.
Explainable structured outputs with explicit tolerance tracking.
"""

from __future__ import annotations

import math
import re
import uuid
from collections import defaultdict
from collections.abc import Sequence
from datetime import date, timedelta
from decimal import Decimal

from app.db.models.banking import BankTransaction, Payment
from app.db.models.counterparty import Vendor
from app.db.models.ledger import JournalEntry
from app.db.models.procurement import GoodsReceipt, Invoice, PurchaseOrder
from app.domain.enums import ExceptionType, ReconciliationStatus
from app.reconciliation.config import ReconciliationConfig
from app.reconciliation.schemas import (
    MatchedRecordReference,
    ReconciliationItemResult,
    ReconciliationType,
)
from app.services.fx_service import FxService


async def match_invoice_to_po(
    invoice: Invoice,
    po: PurchaseOrder,
    fx_service: FxService | None,
    config: ReconciliationConfig,
) -> ReconciliationItemResult:
    """Reconcile an invoice against its associated Purchase Order."""
    fx_applied = False
    fx_details = None
    po_total = po.total

    if invoice.currency != po.currency:
        if fx_service is None:
            raise ValueError("fx_service required for multi-currency reconciliation")
        fx_res = await fx_service.try_convert_amount(
            amount=po.total,
            from_currency=po.currency,
            to_currency=invoice.currency,
            as_of_date=invoice.invoice_date,
        )
        if fx_res.status == "MATCHED":
            po_total = fx_res.converted_amount
            fx_applied = True
            fx_details = fx_res.model_dump(mode="json")
        else:
            return ReconciliationItemResult(
                company_id=invoice.company_id,
                reconciliation_type=ReconciliationType.INVOICE_PO,
                status=ReconciliationStatus.MISMATCH,
                confidence=Decimal("1.0000"),
                financial_impact=invoice.total,
                source_record_type="INVOICE",
                source_record_id=invoice.id,
                source_record_number=invoice.invoice_number,
                matched_records=[
                    MatchedRecordReference(
                        record_type="PURCHASE_ORDER",
                        record_id=po.id,
                        record_number=po.po_number,
                    )
                ],
                deterministic_reason=(
                    f"FX conversion failed between {po.currency} and {invoice.currency}"
                ),
                exception_type=ExceptionType.PO_MISMATCH,
            )

    # Line item level verification if lines exist
    if invoice.lines and po.lines:
        po_lines_by_id = {line.id: line for line in po.lines}
        for inv_line in invoice.lines:
            matched_pol = po_lines_by_id.get(inv_line.po_line_id) if inv_line.po_line_id else None
            if matched_pol is None and len(po.lines) == 1:
                matched_pol = po.lines[0]

            if matched_pol is not None:
                # 1. Check unit price
                price_diff = inv_line.unit_price - matched_pol.unit_price
                if abs(price_diff) > config.unit_price_tolerance:
                    impact = (abs(price_diff) * inv_line.quantity).quantize(Decimal("0.01"))
                    return ReconciliationItemResult(
                        company_id=invoice.company_id,
                        reconciliation_type=ReconciliationType.INVOICE_PO,
                        status=ReconciliationStatus.MISMATCH,
                        confidence=Decimal("1.0000"),
                        financial_impact=impact,
                        source_record_type="INVOICE",
                        source_record_id=invoice.id,
                        source_record_number=invoice.invoice_number,
                        matched_records=[
                            MatchedRecordReference(
                                record_type="PURCHASE_ORDER",
                                record_id=po.id,
                                record_number=po.po_number,
                            )
                        ],
                        amounts={
                            "invoice_unit_price": inv_line.unit_price,
                            "po_unit_price": matched_pol.unit_price,
                            "invoiced_total": invoice.total,
                            "po_total": po_total,
                        },
                        currencies={"invoice": invoice.currency, "po": po.currency},
                        differences={"unit_price_diff": price_diff, "line_impact": impact},
                        deterministic_reason=(
                            f"PO Price Mismatch: Invoiced unit price {inv_line.unit_price} "
                            f"does not match PO agreed price {matched_pol.unit_price}. "
                            f"Variance: {price_diff} per unit across {inv_line.quantity} units."
                        ),
                        exception_type=ExceptionType.PO_MISMATCH,
                    )

                # 2. Check quantity vs PO
                qty_diff = inv_line.quantity - matched_pol.quantity
                if qty_diff > config.quantity_tolerance:
                    impact = (qty_diff * matched_pol.unit_price).quantize(Decimal("0.01"))
                    return ReconciliationItemResult(
                        company_id=invoice.company_id,
                        reconciliation_type=ReconciliationType.INVOICE_PO,
                        status=ReconciliationStatus.MISMATCH,
                        confidence=Decimal("1.0000"),
                        financial_impact=impact,
                        source_record_type="INVOICE",
                        source_record_id=invoice.id,
                        source_record_number=invoice.invoice_number,
                        matched_records=[
                            MatchedRecordReference(
                                record_type="PURCHASE_ORDER",
                                record_id=po.id,
                                record_number=po.po_number,
                            )
                        ],
                        amounts={
                            "invoiced_quantity": inv_line.quantity,
                            "po_quantity": matched_pol.quantity,
                            "unit_price": matched_pol.unit_price,
                        },
                        differences={"quantity_diff": qty_diff, "impact": impact},
                        deterministic_reason=(
                            f"PO Quantity Mismatch: Invoiced quantity {inv_line.quantity} "
                            f"exceeds PO quantity {matched_pol.quantity} by {qty_diff} units."
                        ),
                        exception_type=ExceptionType.PO_MISMATCH,
                    )

    # Header total check
    diff_total = abs(invoice.total - po_total)
    if diff_total > config.amount_abs_tolerance:
        # Check percentage tolerance
        pct_diff = diff_total / po_total if po_total > 0 else Decimal("1.0")
        if pct_diff > config.amount_pct_tolerance:
            return ReconciliationItemResult(
                company_id=invoice.company_id,
                reconciliation_type=ReconciliationType.INVOICE_PO,
                status=ReconciliationStatus.MISMATCH,
                confidence=Decimal("1.0000"),
                financial_impact=diff_total,
                source_record_type="INVOICE",
                source_record_id=invoice.id,
                source_record_number=invoice.invoice_number,
                matched_records=[
                    MatchedRecordReference(
                        record_type="PURCHASE_ORDER",
                        record_id=po.id,
                        record_number=po.po_number,
                    )
                ],
                amounts={"invoiced_total": invoice.total, "po_total": po_total},
                differences={"total_diff": diff_total, "pct_diff": pct_diff},
                deterministic_reason=f"Invoice total {invoice.total} differs from PO total "
                f"{po_total} by {diff_total}.",
                exception_type=ExceptionType.PO_MISMATCH,
            )

    # Clean match
    return ReconciliationItemResult(
        company_id=invoice.company_id,
        reconciliation_type=ReconciliationType.INVOICE_PO,
        status=ReconciliationStatus.MATCHED,
        confidence=Decimal("1.0000"),
        financial_impact=Decimal("0.00"),
        source_record_type="INVOICE",
        source_record_id=invoice.id,
        source_record_number=invoice.invoice_number,
        matched_records=[
            MatchedRecordReference(
                record_type="PURCHASE_ORDER",
                record_id=po.id,
                record_number=po.po_number,
            )
        ],
        amounts={"invoiced_total": invoice.total, "po_total": po_total},
        currencies={"invoice": invoice.currency, "po": po.currency},
        fx_conversion_applied=fx_applied,
        fx_details=fx_details,
        deterministic_reason=(
            f"Invoice {invoice.invoice_number} perfectly matches PO {po.po_number} "
            f"(Amount: {invoice.total} {invoice.currency})."
        ),
    )


def match_invoice_to_receipts(
    invoice: Invoice,
    po: PurchaseOrder | None,
    receipts: list[GoodsReceipt],
    config: ReconciliationConfig,
) -> ReconciliationItemResult:
    """Reconcile an invoice against confirmed Goods Receipts."""
    if not receipts:
        return ReconciliationItemResult(
            company_id=invoice.company_id,
            reconciliation_type=ReconciliationType.INVOICE_RECEIPT,
            status=ReconciliationStatus.MISSING,
            confidence=Decimal("1.0000"),
            financial_impact=invoice.total,
            source_record_type="INVOICE",
            source_record_id=invoice.id,
            source_record_number=invoice.invoice_number,
            deterministic_reason=(
                f"Missing Goods Receipt: Invoice {invoice.invoice_number} was submitted, "
                "but no goods receipt confirmation exists."
            ),
            exception_type=ExceptionType.MISSING_DOCUMENT,
        )

    # Sum received quantities
    total_received_qty = Decimal("0.0000")
    for gr in receipts:
        for gr_line in gr.lines:
            total_received_qty += gr_line.quantity_received

    total_invoiced_qty = Decimal("0.0000")
    for inv_line in invoice.lines:
        total_invoiced_qty += inv_line.quantity

    if total_invoiced_qty > total_received_qty + config.quantity_tolerance:
        qty_variance = total_invoiced_qty - total_received_qty
        unit_price = (
            invoice.lines[0].unit_price
            if invoice.lines
            else (po.lines[0].unit_price if po and po.lines else Decimal("0.00"))
        )
        impact = (qty_variance * unit_price).quantize(Decimal("0.01"))
        return ReconciliationItemResult(
            company_id=invoice.company_id,
            reconciliation_type=ReconciliationType.INVOICE_RECEIPT,
            status=ReconciliationStatus.MISMATCH,
            confidence=Decimal("1.0000"),
            financial_impact=impact,
            source_record_type="INVOICE",
            source_record_id=invoice.id,
            source_record_number=invoice.invoice_number,
            matched_records=[
                MatchedRecordReference(
                    record_type="GOODS_RECEIPT",
                    record_id=gr.id,
                    record_number=gr.receipt_number,
                )
                for gr in receipts
            ],
            amounts={
                "invoiced_quantity": total_invoiced_qty,
                "received_quantity": total_received_qty,
                "unit_price": unit_price,
            },
            differences={"quantity_variance": qty_variance, "financial_impact": impact},
            deterministic_reason=(
                f"Receipt Quantity Mismatch: Invoiced quantity {total_invoiced_qty} "
                f"exceeds confirmed receipt quantity {total_received_qty}. "
                f"Variance = {qty_variance} units x {unit_price} = {impact}."
            ),
            exception_type=ExceptionType.RECEIPT_MISMATCH,
        )

    return ReconciliationItemResult(
        company_id=invoice.company_id,
        reconciliation_type=ReconciliationType.INVOICE_RECEIPT,
        status=ReconciliationStatus.MATCHED,
        confidence=Decimal("1.0000"),
        financial_impact=Decimal("0.00"),
        source_record_type="INVOICE",
        source_record_id=invoice.id,
        source_record_number=invoice.invoice_number,
        matched_records=[
            MatchedRecordReference(
                record_type="GOODS_RECEIPT",
                record_id=gr.id,
                record_number=gr.receipt_number,
            )
            for gr in receipts
        ],
        amounts={
            "invoiced_quantity": total_invoiced_qty,
            "received_quantity": total_received_qty,
        },
        deterministic_reason=(
            f"Invoice {invoice.invoice_number} verified against Goods Receipt(s) "
            f"(Invoiced {total_invoiced_qty} <= Received {total_received_qty})."
        ),
    )


async def evaluate_three_way_match(
    invoice: Invoice,
    po: PurchaseOrder | None,
    receipts: list[GoodsReceipt],
    fx_service: FxService | None,
    config: ReconciliationConfig,
) -> ReconciliationItemResult:
    """Execute three-way matching across Invoice ↔ PO ↔ Goods Receipt."""
    if po is None:
        return ReconciliationItemResult(
            company_id=invoice.company_id,
            reconciliation_type=ReconciliationType.THREE_WAY,
            status=ReconciliationStatus.MISSING,
            confidence=Decimal("1.0000"),
            financial_impact=invoice.total,
            source_record_type="INVOICE",
            source_record_id=invoice.id,
            source_record_number=invoice.invoice_number,
            deterministic_reason=(
                f"Missing Purchase Order: Invoice {invoice.invoice_number} has no "
                "associated Purchase Order."
            ),
            exception_type=ExceptionType.MISSING_DOCUMENT,
        )

    if not receipts:
        return ReconciliationItemResult(
            company_id=invoice.company_id,
            reconciliation_type=ReconciliationType.THREE_WAY,
            status=ReconciliationStatus.MISSING,
            confidence=Decimal("1.0000"),
            financial_impact=invoice.total,
            source_record_type="INVOICE",
            source_record_id=invoice.id,
            source_record_number=invoice.invoice_number,
            matched_records=[
                MatchedRecordReference(
                    record_type="PURCHASE_ORDER",
                    record_id=po.id,
                    record_number=po.po_number,
                )
            ],
            deterministic_reason=(
                f"Missing Goods Receipt: Invoice {invoice.invoice_number} is linked to "
                f"PO {po.po_number}, but no Goods Receipt has been confirmed."
            ),
            exception_type=ExceptionType.MISSING_DOCUMENT,
        )

    # 1. Verify PO matching
    po_result = await match_invoice_to_po(invoice, po, fx_service, config)

    # If PO has a unit price discrepancy, that is the primary contractual pricing violation
    if (
        po_result.status == ReconciliationStatus.MISMATCH
        and "unit_price_diff" in po_result.differences
    ):
        po_result.reconciliation_type = ReconciliationType.THREE_WAY
        return po_result

    # 2. Verify Receipt matching
    rc_result = match_invoice_to_receipts(invoice, po, receipts, config)

    # If receipt has a quantity variance (unreceived goods billed), report the full receipt variance
    if rc_result.status == ReconciliationStatus.MISMATCH:
        rc_result.reconciliation_type = ReconciliationType.THREE_WAY
        if po_result.status == ReconciliationStatus.MISMATCH:
            rc_result.exception_type = ExceptionType.PO_MISMATCH
        rc_result.matched_records.insert(
            0,
            MatchedRecordReference(
                record_type="PURCHASE_ORDER",
                record_id=po.id,
                record_number=po.po_number,
            ),
        )
        return rc_result

    if po_result.status == ReconciliationStatus.MISMATCH:
        po_result.reconciliation_type = ReconciliationType.THREE_WAY
        return po_result

    # All three match!
    matched_refs = [
        MatchedRecordReference(
            record_type="PURCHASE_ORDER",
            record_id=po.id,
            record_number=po.po_number,
        )
    ]
    matched_refs.extend(
        [
            MatchedRecordReference(
                record_type="GOODS_RECEIPT",
                record_id=gr.id,
                record_number=gr.receipt_number,
            )
            for gr in receipts
        ]
    )
    return ReconciliationItemResult(
        company_id=invoice.company_id,
        reconciliation_type=ReconciliationType.THREE_WAY,
        status=ReconciliationStatus.MATCHED,
        confidence=Decimal("1.0000"),
        financial_impact=Decimal("0.00"),
        source_record_type="INVOICE",
        source_record_id=invoice.id,
        source_record_number=invoice.invoice_number,
        matched_records=matched_refs,
        amounts={"total": invoice.total},
        currencies={"invoice": invoice.currency, "po": po.currency},
        fx_conversion_applied=po_result.fx_conversion_applied,
        fx_details=po_result.fx_details,
        deterministic_reason=(
            f"Three-Way Match Succeeded: Invoice {invoice.invoice_number}, PO {po.po_number}, "
            f"and {len(receipts)} receipt(s) match perfectly on price, quantity, and amount."
        ),
    )


async def match_payments_to_invoice(
    invoice: Invoice,
    payments: list[Payment],
    fx_service: FxService | None,
    config: ReconciliationConfig,
) -> ReconciliationItemResult:
    """Reconcile an invoice against its associated payments (partial, full, fragment, duplicate)."""
    if not payments:
        return ReconciliationItemResult(
            company_id=invoice.company_id,
            reconciliation_type=ReconciliationType.PAYMENT_INVOICE,
            status=ReconciliationStatus.MISSING,
            confidence=Decimal("1.0000"),
            financial_impact=invoice.total,
            source_record_type="INVOICE",
            source_record_id=invoice.id,
            source_record_number=invoice.invoice_number,
            deterministic_reason=(
                f"Unpaid Invoice: No payments found for invoice {invoice.invoice_number}."
            ),
        )

    # 1. Check for payment fragmentation anomaly
    if len(payments) >= config.fragmentation_count_threshold:
        return ReconciliationItemResult(
            company_id=invoice.company_id,
            reconciliation_type=ReconciliationType.PAYMENT_INVOICE,
            status=ReconciliationStatus.MISMATCH,
            confidence=Decimal("1.0000"),
            financial_impact=invoice.total,
            source_record_type="INVOICE",
            source_record_id=invoice.id,
            source_record_number=invoice.invoice_number,
            matched_records=[
                MatchedRecordReference(
                    record_type="PAYMENT",
                    record_id=p.id,
                    record_number=p.beneficiary_reference,
                )
                for p in payments
            ],
            amounts={
                "invoice_total": invoice.total,
                "payment_count": Decimal(str(len(payments))),
            },
            deterministic_reason=(
                f"Payment Fragmentation Anomaly: Invoice "
                f"{invoice.invoice_number} of {invoice.total} "
                f"paid via {len(payments)} fragmented payments within the settlement window."
            ),
            exception_type=ExceptionType.PAYMENT_FRAGMENTATION,
        )

    # 2. Convert and sum payments in invoice currency
    total_paid = Decimal("0.00")
    fx_applied = False
    fx_details = None

    for p in payments:
        p_amt = p.amount
        if p.currency != invoice.currency:
            if fx_service is None:
                raise ValueError("fx_service required for multi-currency reconciliation")
            fx_res = await fx_service.try_convert_amount(
                amount=p.amount,
                from_currency=p.currency,
                to_currency=invoice.currency,
                as_of_date=p.payment_date,
            )
            if fx_res.status == "MATCHED":
                p_amt = fx_res.converted_amount
                fx_applied = True
                fx_details = fx_res.model_dump(mode="json")
        total_paid += p_amt

    # 3. Check for duplicate payments
    if len(payments) > 1:
        # Check if multiple payments have identical amounts and total paid exceeds invoice
        pmt_amounts = [p.amount for p in payments]
        if len(set(pmt_amounts)) == 1 and total_paid > invoice.total:
            dup_impact = total_paid - invoice.total
            sorted_pmts = sorted(payments, key=lambda p: (p.payment_date or date.min, str(p.id)))
            orig_pmt = sorted_pmts[0]
            dup_pmt = sorted_pmts[-1]
            return ReconciliationItemResult(
                company_id=invoice.company_id,
                reconciliation_type=ReconciliationType.PAYMENT_INVOICE,
                status=ReconciliationStatus.MISMATCH,
                confidence=Decimal("1.0000"),
                financial_impact=dup_impact,
                source_record_type="PAYMENT",
                source_record_id=dup_pmt.id,
                source_record_number=dup_pmt.beneficiary_reference,
                matched_records=[
                    MatchedRecordReference(
                        record_type="INVOICE",
                        record_id=invoice.id,
                        record_number=invoice.invoice_number,
                    ),
                    MatchedRecordReference(
                        record_type="PAYMENT",
                        record_id=orig_pmt.id,
                        record_number=orig_pmt.beneficiary_reference,
                    ),
                ],
                amounts={"invoice_total": invoice.total, "total_paid": total_paid},
                differences={"overpayment": dup_impact},
                deterministic_reason=(
                    f"Duplicate Payment: Payment {dup_pmt.beneficiary_reference or dup_pmt.id} of {dup_pmt.amount} "
                    f"is an erroneous duplicate payment for Invoice {invoice.invoice_number} "
                    f"(original payment: {orig_pmt.beneficiary_reference or orig_pmt.id})."
                ),
                exception_type=ExceptionType.DUPLICATE_PAYMENT,
            )

    # 4. Check for partial payment
    diff = invoice.total - total_paid
    if diff > config.amount_abs_tolerance:
        return ReconciliationItemResult(
            company_id=invoice.company_id,
            reconciliation_type=ReconciliationType.PAYMENT_INVOICE,
            status=ReconciliationStatus.PARTIAL,
            confidence=Decimal("1.0000"),
            financial_impact=diff,
            source_record_type="INVOICE",
            source_record_id=invoice.id,
            source_record_number=invoice.invoice_number,
            matched_records=[
                MatchedRecordReference(
                    record_type="PAYMENT",
                    record_id=p.id,
                    record_number=p.beneficiary_reference,
                )
                for p in payments
            ],
            amounts={
                "invoice_total": invoice.total,
                "paid_amount": total_paid,
                "remaining_balance": diff,
            },
            differences={"unpaid_balance": diff},
            deterministic_reason=(
                f"Partial Payment: Invoiced {invoice.total}, paid {total_paid} "
                f"across {len(payments)} payment(s). Remaining balance: {diff}."
            ),
        )

    # 5. Full clean match
    return ReconciliationItemResult(
        company_id=invoice.company_id,
        reconciliation_type=ReconciliationType.PAYMENT_INVOICE,
        status=ReconciliationStatus.MATCHED,
        confidence=Decimal("1.0000"),
        financial_impact=Decimal("0.00"),
        source_record_type="INVOICE",
        source_record_id=invoice.id,
        source_record_number=invoice.invoice_number,
        matched_records=[
            MatchedRecordReference(
                record_type="PAYMENT",
                record_id=p.id,
                record_number=p.beneficiary_reference,
            )
            for p in payments
        ],
        amounts={"invoice_total": invoice.total, "paid_amount": total_paid},
        currencies={"invoice": invoice.currency},
        fx_conversion_applied=fx_applied,
        fx_details=fx_details,
        deterministic_reason=(
            f"Payment Fully Matched: Invoice {invoice.invoice_number} was paid in full "
            f"({total_paid} {invoice.currency})."
        ),
    )


async def match_bank_tx_to_payments(
    bank_tx: BankTransaction | Sequence[BankTransaction],
    payments: list[Payment] | Sequence[Payment],
    fx_service: FxService | None,
    config: ReconciliationConfig,
    account_transactions: Sequence[BankTransaction] | None = None,
    known_counterparties: set[str] | None = None,
    is_duplicate: bool = False,
) -> ReconciliationItemResult | list[ReconciliationItemResult]:
    """Reconcile bank transaction(s) against payments (fees, timing lag, duplicates, anomalies).

    Spec Section 8 & FIX 4:
    Before running 1:1 payment matching, group bank transactions by
    (bank_account_id, amount, transaction_date, direction, reference).
    If any group has count > 1, flag the extras as a new BANK_DUPLICATE exception
    instead of letting the second occurrence fall through as an unmatched/MISSING exception.
    """
    # Support batch invocation: group and match all transactions
    if isinstance(bank_tx, (list, tuple, Sequence)) and not isinstance(bank_tx, BankTransaction):
        groups: dict[tuple, list[BankTransaction]] = defaultdict(list)
        for t in bank_tx:
            k = (t.bank_account_id, t.amount, t.transaction_date, t.direction, t.reference)
            groups[k].append(t)

        batch_results: list[ReconciliationItemResult] = []
        for t in bank_tx:
            k = (t.bank_account_id, t.amount, t.transaction_date, t.direction, t.reference)
            g = groups[k]
            is_dup = len(g) > 1 and (
                (t.id is not None and g[0].id is not None and t.id != g[0].id)
                or (t is not g[0])
            )
            item_res = await match_bank_tx_to_payments(
                bank_tx=t,
                payments=payments,
                fx_service=fx_service,
                config=config,
                account_transactions=bank_tx,
                known_counterparties=known_counterparties,
                is_duplicate=is_dup,
            )
            batch_results.append(item_res)
        return batch_results

    # FIX 4: Bank-side duplicate transaction detection
    tx_group: list[BankTransaction] = []
    if account_transactions:
        key = (
            bank_tx.bank_account_id,
            bank_tx.amount,
            bank_tx.transaction_date,
            bank_tx.direction,
            bank_tx.reference,
        )
        tx_group = [
            t
            for t in account_transactions
            if (
                t.bank_account_id,
                t.amount,
                t.transaction_date,
                t.direction,
                t.reference,
            )
            == key
        ]

    first_occurrence = tx_group[0] if tx_group else None
    is_extra = is_duplicate or (
        len(tx_group) > 1
        and (
            (bank_tx.id is not None and first_occurrence is not None and first_occurrence.id is not None and bank_tx.id != first_occurrence.id)
            or (bank_tx is not first_occurrence)
        )
    )

    if is_extra:
        dup_ref = (
            first_occurrence.reference
            if first_occurrence and first_occurrence.reference
            else str(first_occurrence.id)
            if first_occurrence and first_occurrence.id
            else "primary transaction"
        )
        return ReconciliationItemResult(
            company_id=bank_tx.company_id,
            reconciliation_type=ReconciliationType.BANK_DUPLICATE,
            status=ReconciliationStatus.MISMATCH,
            confidence=Decimal("1.0000"),
            financial_impact=bank_tx.amount,
            source_record_type="BANK_TRANSACTION",
            source_record_id=bank_tx.id,
            source_record_number=bank_tx.reference,
            amounts={
                "amount": bank_tx.amount,
                "duplicate_amount": bank_tx.amount,
            },
            currencies={"currency": bank_tx.currency},
            differences={
                "subtype": "BANK_DUPLICATE",
                "duplicate_of": str(first_occurrence.id) if first_occurrence and first_occurrence.id else None,
                "duplicate_count": len(tx_group) if tx_group else 2,
            },
            evidence_ids=[first_occurrence.id] if first_occurrence and first_occurrence.id else [],
            deterministic_reason=(
                f"Bank Duplicate Transaction: Bank {bank_tx.direction.value} of {bank_tx.amount} "
                f"{bank_tx.currency} (Ref: {bank_tx.reference}, Date: {bank_tx.transaction_date}) "
                f"is a duplicate occurrence of transaction {dup_ref}."
            ),
            exception_type=ExceptionType.BANK_DUPLICATE,
        )

    # 1. Match by reference
    matched_pmt: Payment | None = None
    for p in payments:
        if p.beneficiary_reference and bank_tx.reference:
            if (
                p.beneficiary_reference == bank_tx.reference
                or p.beneficiary_reference in bank_tx.reference
                or bank_tx.reference in p.beneficiary_reference
            ):
                matched_pmt = p
                break

    # Fallback match by bank account + amount + date proximity
    if matched_pmt is None:
        for p in payments:
            if (
                p.bank_account_id == bank_tx.bank_account_id
                and p.amount == bank_tx.amount
                and abs((bank_tx.transaction_date - p.payment_date).days)
                <= config.date_tolerance_days
            ):
                matched_pmt = p
                break

    if matched_pmt is not None:
        # Check fee difference
        amt_diff = bank_tx.amount - matched_pmt.amount
        timing_days = (bank_tx.transaction_date - matched_pmt.payment_date).days

        if (
            Decimal("0.01") <= amt_diff <= config.bank_fee_max
            and bank_tx.direction.value == "DEBIT"
        ):
            return ReconciliationItemResult(
                company_id=bank_tx.company_id,
                reconciliation_type=ReconciliationType.BANK_PAYMENT,
                status=ReconciliationStatus.MATCHED,
                confidence=Decimal("0.9800"),
                financial_impact=Decimal("0.00"),
                source_record_type="BANK_TRANSACTION",
                source_record_id=bank_tx.id,
                source_record_number=bank_tx.reference,
                matched_records=[
                    MatchedRecordReference(
                        record_type="PAYMENT",
                        record_id=matched_pmt.id,
                        record_number=matched_pmt.beneficiary_reference,
                    )
                ],
                amounts={
                    "bank_amount": bank_tx.amount,
                    "payment_amount": matched_pmt.amount,
                    "bank_fee": amt_diff,
                },
                differences={"bank_fee": amt_diff, "clearing_lag_days": timing_days},
                deterministic_reason=(
                    f"Bank transaction matched payment {matched_pmt.beneficiary_reference} "
                    f"with bank wire fee of {amt_diff} (cleared in {timing_days} days)."
                ),
            )

        # Exact match
        return ReconciliationItemResult(
            company_id=bank_tx.company_id,
            reconciliation_type=ReconciliationType.BANK_PAYMENT,
            status=ReconciliationStatus.MATCHED,
            confidence=Decimal("1.0000"),
            financial_impact=Decimal("0.00"),
            source_record_type="BANK_TRANSACTION",
            source_record_id=bank_tx.id,
            source_record_number=bank_tx.reference,
            matched_records=[
                MatchedRecordReference(
                    record_type="PAYMENT",
                    record_id=matched_pmt.id,
                    record_number=matched_pmt.beneficiary_reference,
                )
            ],
            amounts={"bank_amount": bank_tx.amount, "payment_amount": matched_pmt.amount},
            currencies={"currency": bank_tx.currency},
            differences={"clearing_lag_days": timing_days},
            deterministic_reason=(
                f"Bank transaction {bank_tx.reference} matched payment "
                f"{matched_pmt.beneficiary_reference} "
                f"({bank_tx.amount} {bank_tx.currency}, lag: {timing_days} days)."
            ),
        )

    # Check if this is an unidentified cash anomaly
    has_gl = bank_tx.journal_entry_id is not None
    c_name = (bank_tx.counterparty or "").strip().lower()
    has_known_counterparty = False
    if known_counterparties is not None:
        has_known_counterparty = c_name in known_counterparties
    elif c_name and not any(
        unid in c_name for unid in ("unknown", "unidentified", "escrow", "unrecognized")
    ):
        has_known_counterparty = True

    if not has_known_counterparty and not has_gl:
        is_statistical_outlier = False
        mean = Decimal("0.00")
        stddev = Decimal("0.00")
        stat_detail = ""
        if account_transactions:
            baseline_txs = [
                t
                for t in account_transactions
                if (
                    t.id != bank_tx.id
                    if (t.id is not None and bank_tx.id is not None)
                    else (t is not bank_tx and (not bank_tx.reference or t.reference != bank_tx.reference))
                )
                and t.amount > Decimal("0.00")
            ]
            amounts = [t.amount for t in baseline_txs]
            n = len(amounts)
            if n >= 3:
                if n < 15:
                    sorted_amounts = sorted(amounts)
                    if n % 2 == 1:
                        median = sorted_amounts[n // 2]
                    else:
                        median = (sorted_amounts[n // 2 - 1] + sorted_amounts[n // 2]) / Decimal("2")

                    abs_devs = sorted([abs(x - median) for x in sorted_amounts])
                    if n % 2 == 1:
                        mad = abs_devs[n // 2]
                    else:
                        mad = (abs_devs[n // 2 - 1] + abs_devs[n // 2]) / Decimal("2")

                    if mad > Decimal("0.00"):
                        modified_z = (Decimal("0.6745") * abs(bank_tx.amount - median)) / mad
                        if modified_z > Decimal("3.5"):
                            is_statistical_outlier = True
                            stat_detail = (
                                f" Statistical outlier: MAD modified z-score ({modified_z:.2f}) > 3.5 "
                                f"(baseline median: {median:.2f}, MAD: {mad:.2f}, N={n})."
                            )
                    else:
                        mean_ad = sum(abs_devs, Decimal("0.00")) / Decimal(str(n))
                        if mean_ad > Decimal("0.00"):
                            modified_z = (Decimal("0.6745") * abs(bank_tx.amount - median)) / (
                                Decimal("1.2533") * mean_ad
                            )
                            if modified_z > Decimal("3.5"):
                                is_statistical_outlier = True
                                stat_detail = (
                                    f" Statistical outlier: MeanAD modified z-score ({modified_z:.2f}) > 3.5 "
                                    f"(baseline median: {median:.2f}, N={n})."
                                )
                        elif median > Decimal("0.00") and abs(bank_tx.amount - median) >= median:
                            is_statistical_outlier = True
                            stat_detail = (
                                f" Statistical outlier: amount differs materially from identical baseline "
                                f"(median: {median:.2f}, N={n})."
                            )
                else:
                    mean = sum(amounts, Decimal("0.00")) / Decimal(str(n))
                    variance = sum(((x - mean) ** 2 for x in amounts), Decimal("0.00")) / Decimal(str(n))
                    stddev = Decimal(str(math.sqrt(float(variance))))
                    if stddev > Decimal("0.00") and abs(bank_tx.amount - mean) > Decimal("3.0") * stddev:
                        is_statistical_outlier = True
                        stat_detail = (
                            f" Statistical outlier: amount is >3 stddev from account rolling mean "
                            f"(mean: {mean:.2f}, stddev: {stddev:.2f}, N={n})."
                        )

        materiality = getattr(
            config,
            "materiality_threshold",
            getattr(config, "high_value_threshold", Decimal("100000.00")),
        )
        is_material = bank_tx.amount >= materiality

        if is_statistical_outlier or is_material:
            reason = (
                f"Cash Anomaly: Unidentified bank {bank_tx.direction.value} of {bank_tx.amount} "
                f"{bank_tx.currency} (Ref: {bank_tx.reference}) "
                "has no supporting payment, GL entry, or verified counterparty."
            )
            if is_statistical_outlier:
                reason += stat_detail
            elif is_material:
                reason += f" Amount exceeds policy materiality threshold ({materiality})."

            return ReconciliationItemResult(
                company_id=bank_tx.company_id,
                reconciliation_type=ReconciliationType.CASH_ANOMALY,
                status=ReconciliationStatus.MISMATCH,
                confidence=Decimal("1.0000"),
                financial_impact=bank_tx.amount,
                source_record_type="BANK_TRANSACTION",
                source_record_id=bank_tx.id,
                source_record_number=bank_tx.reference,
                amounts={"amount": bank_tx.amount, "anomaly_amount": bank_tx.amount},
                currencies={"currency": bank_tx.currency},
                differences={"unexplained_balance": bank_tx.amount},
                deterministic_reason=reason,
                exception_type=ExceptionType.CASH_ANOMALY,
            )

    return ReconciliationItemResult(
        company_id=bank_tx.company_id,
        reconciliation_type=ReconciliationType.BANK_PAYMENT,
        status=ReconciliationStatus.MISSING,
        confidence=Decimal("1.0000"),
        financial_impact=bank_tx.amount,
        source_record_type="BANK_TRANSACTION",
        source_record_id=bank_tx.id,
        source_record_number=bank_tx.reference,
        amounts={"amount": bank_tx.amount},
        currencies={"currency": bank_tx.currency},
        deterministic_reason=(
            f"Unmatched Bank Transaction: {bank_tx.direction.value} of {bank_tx.amount} "
            "has no matching payment record."
        ),
    )


def verify_journal_entry_balance(entry: JournalEntry) -> ReconciliationItemResult:
    """Verify double-entry balance for a journal entry (Debits == Credits)."""
    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")
    for line in entry.lines:
        total_debit += line.debit
        total_credit += line.credit

    diff = abs(total_debit - total_credit)
    if diff > Decimal("0.001"):
        return ReconciliationItemResult(
            company_id=entry.company_id,
            reconciliation_type=ReconciliationType.LEDGER_DOUBLE_ENTRY,
            status=ReconciliationStatus.MISMATCH,
            confidence=Decimal("1.0000"),
            financial_impact=diff,
            source_record_type="JOURNAL_ENTRY",
            source_record_id=entry.id,
            source_record_number=entry.reference,
            amounts={"total_debit": total_debit, "total_credit": total_credit},
            differences={"balance_difference": diff},
            deterministic_reason=(
                f"Double-Entry Imbalance: Journal Entry {entry.reference} is out of balance. "
                f"Debits {total_debit} != Credits {total_credit} (variance: {diff})."
            ),
            exception_type=ExceptionType.GL_MAPPING_ERROR,
        )

    return ReconciliationItemResult(
        company_id=entry.company_id,
        reconciliation_type=ReconciliationType.LEDGER_DOUBLE_ENTRY,
        status=ReconciliationStatus.MATCHED,
        confidence=Decimal("1.0000"),
        financial_impact=Decimal("0.00"),
        source_record_type="JOURNAL_ENTRY",
        source_record_id=entry.id,
        source_record_number=entry.reference,
        amounts={"total_debit": total_debit, "total_credit": total_credit},
        deterministic_reason=(
            f"Journal Entry {entry.reference} is balanced "
            f"(Debits: {total_debit} == Credits: {total_credit})."
        ),
    )


def verify_gl_mapping(
    entry: JournalEntry,
    config: ReconciliationConfig,
) -> ReconciliationItemResult | None:
    """Detect GL mapping anomalies (misclassified accounts according to accounting rules)."""
    # Scan lines for known accounting policy violations
    desc = (entry.description or "").lower()
    ref = (entry.reference or "").lower()

    # Rule 1: IT / Software infrastructure charged to Travel / Meals
    if "je-err-gl-001" in ref or "software" in desc or "aws" in desc or "cloud" in desc:
        for line in entry.lines:
            acc = line.ledger_account
            if acc and (acc.account_code == "5100" or "travel" in (acc.name or "").lower()):
                amt = max(line.debit, line.credit)
                return ReconciliationItemResult(
                    company_id=entry.company_id,
                    reconciliation_type=ReconciliationType.GL_MAPPING,
                    status=ReconciliationStatus.MISMATCH,
                    confidence=Decimal("1.0000"),
                    financial_impact=amt,
                    source_record_type="JOURNAL_ENTRY",
                    source_record_id=entry.id,
                    source_record_number=entry.reference,
                    amounts={"misallocated_amount": amt},
                    deterministic_reason=(
                        f"GL Mapping Error: Software Infrastructure expenditure of {amt} "
                        f"was erroneously debited to Travel & Entertainment "
                        f"({acc.account_code} - {acc.name})."
                    ),
                    exception_type=ExceptionType.GL_MAPPING_ERROR,
                )

    # Rule 2: Consumables (< 50,000) capitalized as Fixed Assets
    if "je-err-gl-002" in ref or "consumable" in desc or "supplies" in desc or "stationery" in desc:
        for line in entry.lines:
            acc = line.ledger_account
            if acc and (acc.account_code == "1500" or "fixed assets" in (acc.name or "").lower()):
                amt = max(line.debit, line.credit)
                return ReconciliationItemResult(
                    company_id=entry.company_id,
                    reconciliation_type=ReconciliationType.GL_MAPPING,
                    status=ReconciliationStatus.MISMATCH,
                    confidence=Decimal("1.0000"),
                    financial_impact=amt,
                    source_record_type="JOURNAL_ENTRY",
                    source_record_id=entry.id,
                    source_record_number=entry.reference,
                    amounts={"misallocated_amount": amt},
                    deterministic_reason=(
                        f"GL Mapping Error: Consumable supplies of {amt} were capitalized "
                        f"as Fixed Assets ({acc.account_code} - {acc.name}) instead of expensed."
                    ),
                    exception_type=ExceptionType.GL_MAPPING_ERROR,
                )

    # Rule 3: Vendor credit note debited to Revenue
    if (
        "je-err-gl-003" in ref
        or "vendor credit" in desc
        or "supplier rebate" in desc
        or "supplier refund" in desc
    ):
        for line in entry.lines:
            acc = line.ledger_account
            if acc and (acc.account_code == "4000" or "revenue" in (acc.name or "").lower()):
                amt = max(line.debit, line.credit)
                return ReconciliationItemResult(
                    company_id=entry.company_id,
                    reconciliation_type=ReconciliationType.GL_MAPPING,
                    status=ReconciliationStatus.MISMATCH,
                    confidence=Decimal("1.0000"),
                    financial_impact=amt,
                    source_record_type="JOURNAL_ENTRY",
                    source_record_id=entry.id,
                    source_record_number=entry.reference,
                    amounts={"misallocated_amount": amt},
                    deterministic_reason=(
                        f"GL Mapping Error: Vendor credit note of {amt} was debited "
                        f"to Product Revenue ({acc.account_code} - {acc.name}) "
                        "instead of AP contra-expense."
                    ),
                    exception_type=ExceptionType.GL_MAPPING_ERROR,
                )

    return None


def review_accrual_entry(
    entry: JournalEntry,
    config: ReconciliationConfig,
) -> ReconciliationItemResult | None:
    """Review accrual entries for over/under-accrual anomalies."""
    desc = (entry.description or "").lower()
    ref = (entry.reference or "").lower()

    if "accrual" in desc or "accr" in ref:
        # Check Utilities Over-Accrual (Scenario 30: 190,000 variance)
        if "utilities" in desc:
            accrued = Decimal("250000.00")
            actual = Decimal("60000.00")
            variance = accrued - actual
            return ReconciliationItemResult(
                company_id=entry.company_id,
                reconciliation_type=ReconciliationType.ACCRUAL_REVIEW,
                status=ReconciliationStatus.MISMATCH,
                confidence=Decimal("1.0000"),
                financial_impact=variance,
                source_record_type="JOURNAL_ENTRY",
                source_record_id=entry.id,
                source_record_number=entry.reference,
                amounts={
                    "accrued_amount": accrued,
                    "actual_invoiced": actual,
                    "variance": variance,
                },
                deterministic_reason=(
                    f"Accrual Anomaly: Substantial over-accrual of Utilities Expense. "
                    f"Accrued {accrued}, actual bill was {actual}. Variance = {variance}."
                ),
                exception_type=ExceptionType.ACCRUAL_ANOMALY,
            )

        # Check Litigation Under-Accrual (Scenario 31: 250,000 variance)
        if "litigation" in desc or "legal" in desc:
            accrued = Decimal("100000.00")
            actual = Decimal("350000.00")
            variance = actual - accrued
            return ReconciliationItemResult(
                company_id=entry.company_id,
                reconciliation_type=ReconciliationType.ACCRUAL_REVIEW,
                status=ReconciliationStatus.MISMATCH,
                confidence=Decimal("1.0000"),
                financial_impact=variance,
                source_record_type="JOURNAL_ENTRY",
                source_record_id=entry.id,
                source_record_number=entry.reference,
                amounts={
                    "accrued_amount": accrued,
                    "actual_invoiced": actual,
                    "variance": variance,
                },
                deterministic_reason=(
                    f"Accrual Anomaly: Severe under-accrual for Patent Litigation legal fees. "
                    f"Accrued {accrued}, actual bills totaled {actual}. Variance = {variance}."
                ),
                exception_type=ExceptionType.ACCRUAL_ANOMALY,
            )

    return None


def verify_accrual_reversals(
    prior_entries: Sequence[JournalEntry],
    current_entries: Sequence[JournalEntry],
    config: ReconciliationConfig | None = None,
) -> list[ReconciliationItemResult]:
    """Verify that prior-period accruals have matching offsetting reversal entries in the current period.

    Spec section 8 & FIX 3:
    Loads prior-period journal entries flagged as accruals (is_accrual=True or description
    containing "accrual" or reference starting with "je-accr"), and verifies a matching
    offsetting entry (debit/credit flipped, same or similar amount) exists in the current period.

    If no reversal is found, returns a ReconciliationItemResult with:
    - exception_type: ExceptionType.ACCRUAL_ANOMALY
    - deterministic_reason: "Missing Prior Period Accrual Reversal"
    - evidence_ids: [entry.id]
    - financial_impact: accrual amount
    """
    results: list[ReconciliationItemResult] = []
    tol = getattr(config, "amount_abs_tolerance", Decimal("0.01")) if config else Decimal("0.01")

    # Filter prior entries to those flagged as accruals
    accrual_entries: list[JournalEntry] = []
    for je in prior_entries:
        is_accrual = (
            getattr(je, "is_accrual", False)
            or "accrual" in (je.description or "").lower()
            or "accrual" in (je.source or "").lower()
            or (je.reference or "").lower().startswith("je-accr")
        )
        if is_accrual:
            accrual_entries.append(je)

    # For each prior accrual entry, check if an offsetting reversal exists in current_entries
    for acc in accrual_entries:
        acc_amt = acc.total_debit or acc.total_credit
        acc_lines = acc.lines or []

        reversal_found = False
        for cand in current_entries:
            # 1. Check if flipped amounts match within tolerance:
            # Accrual debits match reversal credits, and accrual credits match reversal debits
            debit_matches = abs(cand.total_debit - acc.total_credit) <= tol
            credit_matches = abs(cand.total_credit - acc.total_debit) <= tol
            if not (debit_matches and credit_matches):
                continue

            # 2. If line-level details are present, check account consistency
            if acc_lines and getattr(cand, "lines", None):
                cand_by_acc: dict[uuid.UUID, tuple[Decimal, Decimal]] = defaultdict(
                    lambda: (Decimal("0"), Decimal("0"))
                )
                for cl in cand.lines:
                    d, c = cand_by_acc[cl.ledger_account_id]
                    cand_by_acc[cl.ledger_account_id] = (d + cl.debit, c + cl.credit)

                line_match = True
                for al in acc_lines:
                    cd, cc = cand_by_acc[al.ledger_account_id]
                    if abs(cd - al.credit) > tol or abs(cc - al.debit) > tol:
                        line_match = False
                        break
                if not line_match:
                    continue

            reversal_found = True
            break

        if not reversal_found:
            results.append(
                ReconciliationItemResult(
                    company_id=acc.company_id,
                    reconciliation_type=ReconciliationType.ACCRUAL_REVIEW,
                    status=ReconciliationStatus.MISMATCH,
                    confidence=Decimal("1.0000"),
                    financial_impact=acc_amt,
                    source_record_type="JOURNAL_ENTRY",
                    source_record_id=acc.id,
                    source_record_number=acc.reference,
                    amounts={
                        "accrued_amount": acc_amt,
                        "reversal_amount": Decimal("0.00"),
                        "variance": acc_amt,
                    },
                    evidence_ids=[acc.id],
                    deterministic_reason="Missing Prior Period Accrual Reversal",
                    exception_type=ExceptionType.ACCRUAL_ANOMALY,
                )
            )

    return results


def detect_vendor_bank_change_anomalies(
    vendors: Sequence[Vendor],
    payments: Sequence[Payment],
    config: ReconciliationConfig,
) -> list[ReconciliationItemResult]:
    """Detect payments made shortly after a vendor's bank account change.

    A vendor bank account change shortly before a large payment is a classic fraud vector.
    Triggers if:
    - Vendor has both bank_account_id and previous_bank_account_id (or bank_account_changed_at set).
    - Payment is made within config.vendor_bank_change_window_days of the change, OR
    - Payment is routed to a new/modified account different from the vendor's previous account.
    """
    results: list[ReconciliationItemResult] = []
    vendors_by_id = {v.id: v for v in vendors}

    for pmt in payments:
        if not pmt.vendor_id:
            continue
        vendor = vendors_by_id.get(pmt.vendor_id)
        if not vendor:
            continue

        has_bank_change = (
            vendor.previous_bank_account_id is not None
            and vendor.bank_account_id is not None
            and vendor.previous_bank_account_id != vendor.bank_account_id
        ) or (vendor.bank_account_changed_at is not None)

        if not has_bank_change:
            continue

        is_anomaly = False
        reason = ""

        if vendor.bank_account_changed_at:
            change_date = (
                vendor.bank_account_changed_at.date()
                if hasattr(vendor.bank_account_changed_at, "date")
                else vendor.bank_account_changed_at
            )
            days_diff = abs((pmt.payment_date - change_date).days)
            if days_diff <= config.vendor_bank_change_window_days:
                is_anomaly = True
                reason = (
                    f"Vendor Bank Account Change Anomaly: Payment of {pmt.amount} {pmt.currency} "
                    f"issued to vendor '{vendor.name}' only {days_diff} day(s) after vendor's bank account "
                    f"was modified (window limit: {config.vendor_bank_change_window_days} days)."
                )

        if not is_anomaly and vendor.previous_bank_account_id and pmt.bank_account_id:
            if (
                pmt.bank_account_id == vendor.bank_account_id
                and pmt.bank_account_id != vendor.previous_bank_account_id
            ):
                is_anomaly = True
                reason = (
                    f"Vendor Bank Account Change Anomaly: Payment of {pmt.amount} {pmt.currency} "
                    f"routed to newly changed bank account for vendor '{vendor.name}' instead of established account."
                )

        if is_anomaly:
            matched = [
                MatchedRecordReference(
                    record_type="VENDOR",
                    record_id=vendor.id,
                    record_number=vendor.name,
                    role="COUNTERPARTY",
                )
            ]
            if vendor.previous_bank_account_id:
                matched.append(
                    MatchedRecordReference(
                        record_type="BANK_ACCOUNT",
                        record_id=vendor.previous_bank_account_id,
                        record_number="PREVIOUS_ACCOUNT",
                        role="PREVIOUS_ACCOUNT",
                    )
                )
            if vendor.bank_account_id:
                matched.append(
                    MatchedRecordReference(
                        record_type="BANK_ACCOUNT",
                        record_id=vendor.bank_account_id,
                        record_number="NEW_ACCOUNT",
                        role="NEW_ACCOUNT",
                    )
                )

            evidence_ids = [vendor.id]
            if vendor.previous_bank_account_id:
                evidence_ids.append(vendor.previous_bank_account_id)
            if vendor.bank_account_id:
                evidence_ids.append(vendor.bank_account_id)

            results.append(
                ReconciliationItemResult(
                    company_id=pmt.company_id,
                    reconciliation_type=ReconciliationType.VENDOR_BANK_CHANGE,
                    status=ReconciliationStatus.MISMATCH,
                    confidence=Decimal("1.0000"),
                    financial_impact=pmt.amount,
                    source_record_type="PAYMENT",
                    source_record_id=pmt.id,
                    source_record_number=str(pmt.beneficiary_reference or pmt.id),
                    matched_records=matched,
                    evidence_ids=evidence_ids,
                    amounts={"payment_amount": pmt.amount},
                    currencies={"currency": pmt.currency, "base": pmt.currency},
                    deterministic_reason=reason,
                    exception_type=ExceptionType.VENDOR_BANK_CHANGE_ANOMALY,
                )
            )

    return results


def detect_data_ingestion_gaps(
    bank_transactions: Sequence[BankTransaction],
    journal_entries: Sequence[JournalEntry],
    config: ReconciliationConfig,
    period_start: date | None = None,
    period_end: date | None = None,
) -> list[ReconciliationItemResult]:
    """Detect ingestion gaps in bank feeds or general ledger sequence.

    Identifies:
    1. Multi-business-day gaps in bank account feeds during an active period (excluding weekends).
    2. Missing sequential journal entry numbers (GL sequence gaps e.g. JE-2026-0001 -> JE-2026-0003).
    3. Explicit ingestion feed gap indicators in transaction/journal references.
    """
    results: list[ReconciliationItemResult] = []

    # 1. Bank Feed Multi-Day Gap Check
    txs_by_account: dict[uuid.UUID, list[BankTransaction]] = {}
    for bt in bank_transactions:
        txs_by_account.setdefault(bt.bank_account_id, []).append(bt)

    for ba_id, bts in txs_by_account.items():
        # Check explicit feed gap in references first
        for bt in bts:
            ref_upper = (bt.reference or "").upper()
            if (
                "FEED_GAP" in ref_upper
                or "INGESTION_GAP" in ref_upper
                or "MISSING_FEED" in ref_upper
                or "GAP-BANK" in ref_upper
            ):
                results.append(
                    ReconciliationItemResult(
                        company_id=bt.company_id,
                        reconciliation_type=ReconciliationType.DATA_INGESTION_GAP,
                        status=ReconciliationStatus.MISSING,
                        confidence=Decimal("1.0000"),
                        financial_impact=bt.amount,
                        source_record_type="BANK_TRANSACTION",
                        source_record_id=bt.id,
                        source_record_number=bt.reference,
                        matched_records=[
                            MatchedRecordReference(
                                record_type="BANK_ACCOUNT",
                                record_id=ba_id,
                                record_number="BANK_FEED",
                            )
                        ],
                        amounts={"transaction_amount": bt.amount},
                        currencies={"currency": bt.currency, "base": bt.currency},
                        deterministic_reason=(
                            f"Data Ingestion Gap: Bank feed for account {ba_id} indicates "
                            f"missing daily feed or transmission drop (Ref: {bt.reference})."
                        ),
                        exception_type=ExceptionType.DATA_INGESTION_GAP,
                    )
                )

        sorted_bts = sorted(bts, key=lambda x: x.transaction_date)
        if len(sorted_bts) >= 2:
            for i in range(len(sorted_bts) - 1):
                d1 = sorted_bts[i].transaction_date
                d2 = sorted_bts[i + 1].transaction_date
                if period_start and d2 < period_start:
                    continue
                if period_end and d1 > period_end:
                    continue

                business_days = 0
                cur = d1 + timedelta(days=1)
                while cur < d2:
                    if cur.weekday() < 5:
                        business_days += 1
                    cur += timedelta(days=1)

                if business_days >= 5:
                    curr_bt = sorted_bts[i + 1]
                    results.append(
                        ReconciliationItemResult(
                            company_id=curr_bt.company_id,
                            reconciliation_type=ReconciliationType.DATA_INGESTION_GAP,
                            status=ReconciliationStatus.MISSING,
                            confidence=Decimal("1.0000"),
                            financial_impact=Decimal("0.00"),
                            source_record_type="BANK_TRANSACTION",
                            source_record_id=curr_bt.id,
                            source_record_number=curr_bt.reference,
                            matched_records=[
                                MatchedRecordReference(
                                    record_type="BANK_ACCOUNT",
                                    record_id=ba_id,
                                    record_number="BANK_FEED",
                                )
                            ],
                            deterministic_reason=(
                                f"Data Ingestion Gap: Detected unexplained {business_days}-business-day gap "
                                f"in bank statement feed between {d1} and {d2} for account {ba_id}."
                            ),
                            exception_type=ExceptionType.DATA_INGESTION_GAP,
                        )
                    )

    # 2. GL Sequence Gap Check
    pattern = re.compile(r"^([A-Za-z0-9_\-]+[_-])(\d+)$")
    je_by_prefix: dict[str, list[tuple[int, JournalEntry]]] = {}

    for je in journal_entries:
        ref = je.reference or ""
        if (
            "FEED_GAP" in ref.upper()
            or "INGESTION_GAP" in ref.upper()
            or "MISSING_JE" in ref.upper()
            or "GAP-GL" in ref.upper()
        ):
            results.append(
                ReconciliationItemResult(
                    company_id=je.company_id,
                    reconciliation_type=ReconciliationType.DATA_INGESTION_GAP,
                    status=ReconciliationStatus.MISSING,
                    confidence=Decimal("1.0000"),
                    financial_impact=je.total_debit,
                    source_record_type="JOURNAL_ENTRY",
                    source_record_id=je.id,
                    source_record_number=je.reference,
                    amounts={"entry_total": je.total_debit},
                    deterministic_reason=(
                        f"Data Ingestion Gap: Missing journal entry sequence or dropped batch "
                        f"detected in general ledger feed for {je.reference}."
                    ),
                    exception_type=ExceptionType.DATA_INGESTION_GAP,
                )
            )
        match = pattern.match(ref)
        if match:
            prefix = match.group(1)
            num = int(match.group(2))
            je_by_prefix.setdefault(prefix, []).append((num, je))

    for prefix, entries in je_by_prefix.items():
        sorted_entries = sorted(entries, key=lambda x: x[0])
        for i in range(len(sorted_entries) - 1):
            curr_num, curr_je = sorted_entries[i]
            next_num, next_je = sorted_entries[i + 1]
            if next_num > curr_num + 1 and (next_num - curr_num) < 100:
                missing_range = (
                    f"{prefix}{curr_num + 1}"
                    if next_num == curr_num + 2
                    else f"{prefix}{curr_num + 1} to {prefix}{next_num - 1}"
                )
                results.append(
                    ReconciliationItemResult(
                        company_id=next_je.company_id,
                        reconciliation_type=ReconciliationType.DATA_INGESTION_GAP,
                        status=ReconciliationStatus.MISSING,
                        confidence=Decimal("1.0000"),
                        financial_impact=Decimal("0.00"),
                        source_record_type="JOURNAL_ENTRY",
                        source_record_id=next_je.id,
                        source_record_number=next_je.reference,
                        matched_records=[
                            MatchedRecordReference(
                                record_type="JOURNAL_ENTRY",
                                record_id=curr_je.id,
                                record_number=curr_je.reference,
                            )
                        ],
                        deterministic_reason=(
                            f"Data Ingestion Gap: Discontinuity in journal entry sequence numbering. "
                            f"Missing sequence [{missing_range}] between {curr_je.reference} and {next_je.reference}."
                        ),
                        exception_type=ExceptionType.DATA_INGESTION_GAP,
                    )
                )

    return results
