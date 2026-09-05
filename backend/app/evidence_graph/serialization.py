"""Deterministic serialization of financial evidence graphs (spec section 7).

Provides decimal-safe, deterministic JSON serialization and structured Markdown formatting
tailored for LLM agent prompt injection (Investigation Agent, Verification Agent).
"""

from __future__ import annotations

import json

from app.evidence_graph.ranker import EvidenceRanker
from app.evidence_graph.types import (
    EvidenceItem,
    EvidenceNode,
    EvidenceQueryResponse,
    EvidenceSubgraph,
    NodeType,
)


def serialize_subgraph_json(subgraph: EvidenceSubgraph) -> str:
    """Serialize an EvidenceSubgraph to deterministic, pretty-printed JSON."""
    return json.dumps(subgraph.model_dump(mode="json"), sort_keys=True, indent=2, default=str)


def serialize_query_response_json(response: EvidenceQueryResponse) -> str:
    """Serialize an EvidenceQueryResponse to deterministic, pretty-printed JSON."""
    return json.dumps(response.model_dump(mode="json"), sort_keys=True, indent=2, default=str)


def format_evidence_markdown(
    focus_node_id: str,
    subgraph: EvidenceSubgraph,
    ranked_items: list[EvidenceItem] | None = None,
    query_type: str = "INVESTIGATION",
    company_id: str | None = None,
) -> str:
    """Format structured evidence into an LLM-ready Markdown context block."""
    cid = company_id or (subgraph.metadata.get("company_id", "UNKNOWN"))
    if ranked_items is None:
        ranked_items = EvidenceRanker.rank_subgraph(subgraph, focus_node_id)

    node_map: dict[str, EvidenceNode] = {n.id: n for n in subgraph.nodes}
    focus_node = node_map.get(focus_node_id)

    md_lines: list[str] = [
        "### FINANCIAL EVIDENCE DOSSIER",
        f"- **Query Type:** {query_type}",
        f"- **Focus Entity:** `{focus_node_id}`",
        f"- **Company ID:** `{cid}`",
        f"- **Evidence Scope:** {len(subgraph.nodes)} nodes, {len(subgraph.edges)} edges",
        "",
    ]

    # Focus Record Summary
    if focus_node:
        md_lines.append(f"#### Focus Record: {focus_node.label}")
        for k in sorted(focus_node.properties.keys()):
            val = focus_node.properties[k]
            if val is not None and k not in ("details", "risk_metadata_json"):
                md_lines.append(f"  - **{k.replace('_', ' ').title()}:** `{val}`")
        md_lines.append("")

    # Ranked Evidence Table
    md_lines.append("#### Ranked Supporting Evidence")
    md_lines.append("| Rank | Score | Type | Label | Dist | Relevance Reason |")
    md_lines.append("|:---:|:---:|:---|:---|:---:|:---|")

    for idx, item in enumerate(ranked_items[:15], 1):
        n = item.node
        label_truncated = (n.label[:45] + "...") if len(n.label) > 48 else n.label
        reason_truncated = (
            (item.relevance_reason[:60] + "...")
            if len(item.relevance_reason) > 63
            else item.relevance_reason
        )
        table_row = (
            f"| {idx} | `{item.score:.4f}` | `{n.node_type.value}` | "
            f"{label_truncated} | {item.distance} | {reason_truncated} |"
        )
        md_lines.append(table_row)
    md_lines.append("")

    # Line Item Comparison if lines exist in subgraph
    inv_lines = [n for n in subgraph.nodes if n.node_type == NodeType.INVOICE_LINE]
    po_lines = [n for n in subgraph.nodes if n.node_type == NodeType.PO_LINE]
    rec_lines = [n for n in subgraph.nodes if n.node_type == NodeType.RECEIPT_LINE]

    if inv_lines or po_lines or rec_lines:
        md_lines.append("#### Line Item Inspection & Variance")
        md_lines.append("| Source Type | Line Description | Quantity | Unit Price | Amount |")
        md_lines.append("|:---|:---|:---:|:---:|:---:|")

        for il in sorted(inv_lines, key=lambda x: x.id):
            desc = il.properties.get("description", "N/A")
            qty = il.properties.get("quantity", "N/A")
            price = il.properties.get("unit_price", "N/A")
            amt = il.properties.get("amount", "N/A")
            md_lines.append(f"| `INVOICE_LINE` | {desc} | `{qty}` | `{price}` | `{amt}` |")

        for pol in sorted(po_lines, key=lambda x: x.id):
            desc = pol.properties.get("description", "N/A")
            qty = pol.properties.get("quantity", "N/A")
            price = pol.properties.get("unit_price", "N/A")
            amt = pol.properties.get("amount", "N/A")
            md_lines.append(f"| `PO_LINE` | {desc} | `{qty}` | `{price}` | `{amt}` |")

        for grl in sorted(rec_lines, key=lambda x: x.id):
            desc = grl.properties.get("description", "N/A")
            qty = grl.properties.get("quantity_received", "N/A")
            md_lines.append(f"| `RECEIPT_LINE` | {desc} | `{qty}` | `—` | `—` |")

        md_lines.append("")

    # Key Evidence Traversal Paths
    md_lines.append("#### Verified Traversal Paths")
    displayed_paths = 0
    for item in ranked_items:
        if item.node.id != focus_node_id and len(item.path_summary) > 1 and displayed_paths < 6:
            chain = " ──> ".join([f"`{step}`" for step in item.path_summary])
            md_lines.append(f"- {chain}")
            displayed_paths += 1

    if displayed_paths == 0:
        md_lines.append("- *(No multi-hop paths active in this localized subgraph)*")

    md_lines.append("")
    return "\n".join(md_lines)


def build_evidence_query_response(
    focus_node_id: str,
    subgraph: EvidenceSubgraph,
    query_type: str = "INVESTIGATION",
    company_id: str | None = None,
    max_ranked_items: int = 15,
) -> EvidenceQueryResponse:
    """Build a complete EvidenceQueryResponse containing subgraph, ranking, and Markdown context."""
    cid = company_id or (subgraph.metadata.get("company_id", "UNKNOWN"))
    ranked_items = EvidenceRanker.rank_subgraph(
        subgraph=subgraph,
        focus_node_id=focus_node_id,
        max_results=max_ranked_items,
    )
    markdown_context = format_evidence_markdown(
        focus_node_id=focus_node_id,
        subgraph=subgraph,
        ranked_items=ranked_items,
        query_type=query_type,
        company_id=cid,
    )

    node_map = {n.id: n for n in subgraph.nodes}
    focus_node = node_map.get(focus_node_id)
    focus_label = focus_node.label if focus_node else focus_node_id

    summary_narrative = (
        f"Retrieved {len(subgraph.nodes)} nodes and {len(subgraph.edges)} edges "
        f"for focus record {focus_label}. Identified {len(ranked_items)} "
        "prioritized evidence records."
    )

    return EvidenceQueryResponse(
        company_id=cid,
        query_type=query_type,
        focus_node_id=focus_node_id,
        subgraph=subgraph,
        ranked_evidence=ranked_items,
        summary_narrative=summary_narrative,
        llm_context_markdown=markdown_context,
    )
