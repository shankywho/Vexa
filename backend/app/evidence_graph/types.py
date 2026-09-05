"""Typed graph nodes, edges, provenance, and query models (spec section 7).

Pure deterministic financial evidence graph definitions.
Tenant isolation enforced on every node and edge.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TenantIsolationViolationError(ValueError):
    """Raised when a graph operation attempts to cross company/tenant boundaries."""


class NodeType(StrEnum):
    """All 20 typed nodes participating in the Vexa financial evidence graph."""

    COMPANY = "COMPANY"
    VENDOR = "VENDOR"
    CUSTOMER = "CUSTOMER"
    INVOICE = "INVOICE"
    INVOICE_LINE = "INVOICE_LINE"
    PURCHASE_ORDER = "PURCHASE_ORDER"
    PO_LINE = "PO_LINE"
    GOODS_RECEIPT = "GOODS_RECEIPT"
    RECEIPT_LINE = "RECEIPT_LINE"
    PAYMENT = "PAYMENT"
    BANK_ACCOUNT = "BANK_ACCOUNT"
    BANK_TRANSACTION = "BANK_TRANSACTION"
    LEDGER_ACCOUNT = "LEDGER_ACCOUNT"
    JOURNAL_ENTRY = "JOURNAL_ENTRY"
    JOURNAL_ENTRY_LINE = "JOURNAL_ENTRY_LINE"
    EXPENSE_REPORT = "EXPENSE_REPORT"
    CONTRACT = "CONTRACT"
    FX_RATE = "FX_RATE"
    RECONCILIATION_RESULT = "RECONCILIATION_RESULT"
    EXCEPTION = "EXCEPTION"


class EdgeType(StrEnum):
    """Semantic typed relationships connecting financial records."""

    # Structural & Master Data
    BELONGS_TO_COMPANY = "BELONGS_TO_COMPANY"
    CUSTOMER_OF_COMPANY = "CUSTOMER_OF_COMPANY"
    CONTRACT_WITH_VENDOR = "CONTRACT_WITH_VENDOR"
    VENDOR_BANK_ACCOUNT = "VENDOR_BANK_ACCOUNT"

    # Procurement & Settlement Flow
    ISSUED_BY_VENDOR = "ISSUED_BY_VENDOR"
    ISSUED_TO_VENDOR = "ISSUED_TO_VENDOR"
    REFERENCES_PO = "REFERENCES_PO"
    CONTAINS_LINE = "CONTAINS_LINE"
    FULFILLED_BY_RECEIPT = "FULFILLED_BY_RECEIPT"
    REFERENCES_PO_LINE = "REFERENCES_PO_LINE"
    RECEIPT_FULFILLS_PO_LINE = "RECEIPT_FULFILLS_PO_LINE"

    # Payments & Banking
    PAID_BY_PAYMENT = "PAID_BY_PAYMENT"
    PAYMENT_PAYS_INVOICE = "PAYMENT_PAYS_INVOICE"
    PAYMENT_TO_VENDOR = "PAYMENT_TO_VENDOR"
    PAYMENT_ON_ACCOUNT = "PAYMENT_ON_ACCOUNT"
    EXPENSE_PAID_BY = "EXPENSE_PAID_BY"
    APPEARS_AS_BANK_TX = "APPEARS_AS_BANK_TX"
    RECORDED_ON_BANK_ACCOUNT = "RECORDED_ON_BANK_ACCOUNT"

    # General Ledger & Accounting
    MAPPED_TO_JOURNAL_ENTRY = "MAPPED_TO_JOURNAL_ENTRY"
    POSTS_TO_LEDGER = "POSTS_TO_LEDGER"
    SUBMITTED_BY_USER = "SUBMITTED_BY_USER"
    CONVERTED_WITH_FX = "CONVERTED_WITH_FX"

    # Reconciliation & Exceptions
    EVALUATES_RECORD = "EVALUATES_RECORD"
    MATCHED_IN_RECONCILIATION = "MATCHED_IN_RECONCILIATION"
    GENERATED_BY_RECONCILIATION = "GENERATED_BY_RECONCILIATION"
    SUBJECT_OF_EXCEPTION = "SUBJECT_OF_EXCEPTION"
    SUPPORTED_BY_EVIDENCE = "SUPPORTED_BY_EVIDENCE"


class EdgeDirection(StrEnum):
    """Direction for graph traversals."""

    OUTGOING = "OUTGOING"
    INCOMING = "INCOMING"
    BOTH = "BOTH"


class EvidenceProvenance(BaseModel):
    """Provenance trail pinpointing the exact origin of a graph element."""

    model_config = ConfigDict(from_attributes=True)

    source_table: str
    source_id: str
    company_id: str
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    description: str | None = None


class EvidenceNode(BaseModel):
    """A typed entity node within the tenant financial evidence graph."""

    model_config = ConfigDict(from_attributes=True)

    id: str  # Format: "{node_type}:{record_id}"
    node_type: NodeType
    record_id: str
    company_id: str
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)
    provenance: EvidenceProvenance

    @classmethod
    def make_id(cls, node_type: NodeType | str, record_id: str | uuid.UUID) -> str:
        t = node_type.value if isinstance(node_type, NodeType) else str(node_type)
        return f"{t}:{record_id}"


class EvidenceEdge(BaseModel):
    """A typed directed edge connecting two financial records."""

    model_config = ConfigDict(from_attributes=True)

    id: str  # Format: "{source_id}->{edge_type}->{target_id}"
    source_id: str
    target_id: str
    edge_type: EdgeType
    company_id: str
    properties: dict[str, Any] = Field(default_factory=dict)
    provenance: EvidenceProvenance | None = None

    @classmethod
    def make_id(cls, source_id: str, edge_type: EdgeType | str, target_id: str) -> str:
        t = edge_type.value if isinstance(edge_type, EdgeType) else str(edge_type)
        return f"{source_id}->{t}->{target_id}"


class EvidenceSubgraph(BaseModel):
    """A localized subgraph of financial evidence extracted from the tenant graph."""

    model_config = ConfigDict(from_attributes=True)

    nodes: list[EvidenceNode] = Field(default_factory=list)
    edges: list[EvidenceEdge] = Field(default_factory=list)
    root_node_id: str | None = None
    depth: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidencePath(BaseModel):
    """Shortest or causal path connecting two financial records."""

    model_config = ConfigDict(from_attributes=True)

    source_id: str
    target_id: str
    hop_count: int
    nodes: list[EvidenceNode] = Field(default_factory=list)
    edges: list[EvidenceEdge] = Field(default_factory=list)
    summary: str


class EvidenceItem(BaseModel):
    """An individual piece of ranked evidence with relevance score and explanation."""

    model_config = ConfigDict(from_attributes=True)

    node: EvidenceNode
    score: float
    distance: int
    path_summary: list[str] = Field(default_factory=list)
    relevance_reason: str


class EvidenceQueryResponse(BaseModel):
    """High-level structured response for agent investigation queries."""

    model_config = ConfigDict(from_attributes=True)

    company_id: str
    query_type: str
    focus_node_id: str
    subgraph: EvidenceSubgraph
    ranked_evidence: list[EvidenceItem]
    summary_narrative: str
    llm_context_markdown: str
