"""Financial Evidence Graph package (spec section 7).

Typed, tenant-isolated evidence graph connecting Vexa financial records,
reconciliation results, and exceptions for autonomous investigation agents.
"""

from __future__ import annotations

from app.evidence_graph.builder import FinancialEvidenceGraphBuilder
from app.evidence_graph.graph import FinancialEvidenceGraph
from app.evidence_graph.ranker import EvidenceRanker
from app.evidence_graph.serialization import (
    build_evidence_query_response,
    format_evidence_markdown,
    serialize_query_response_json,
    serialize_subgraph_json,
)
from app.evidence_graph.types import (
    EdgeDirection,
    EdgeType,
    EvidenceEdge,
    EvidenceItem,
    EvidenceNode,
    EvidencePath,
    EvidenceProvenance,
    EvidenceQueryResponse,
    EvidenceSubgraph,
    NodeType,
    TenantIsolationViolationError,
)

__all__ = [
    "EdgeDirection",
    "EdgeType",
    "EvidenceEdge",
    "EvidenceItem",
    "EvidenceNode",
    "EvidencePath",
    "EvidenceProvenance",
    "EvidenceQueryResponse",
    "EvidenceRanker",
    "EvidenceSubgraph",
    "FinancialEvidenceGraph",
    "FinancialEvidenceGraphBuilder",
    "NodeType",
    "TenantIsolationViolationError",
    "build_evidence_query_response",
    "format_evidence_markdown",
    "serialize_query_response_json",
    "serialize_subgraph_json",
]
