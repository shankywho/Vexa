"""Evidence ranking and relevance scoring for financial investigation queries (spec section 7).

Scores and ranks evidence nodes relative to an investigation focus (e.g. exception or invoice)
using topological distance, causal link types, and financial discrepancy alignment.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from app.evidence_graph.types import (
    EdgeType,
    EvidenceItem,
    EvidenceNode,
    EvidenceSubgraph,
    NodeType,
)


class EvidenceRanker:
    """Ranks subgraph evidence nodes deterministically for LLM investigation prompts."""

    @classmethod
    def rank_subgraph(
        cls,
        subgraph: EvidenceSubgraph,
        focus_node_id: str,
        query_context: dict[str, Any] | None = None,
        max_results: int | None = None,
    ) -> list[EvidenceItem]:
        """Compute relevance scores and rank evidence nodes deterministically."""
        if not subgraph.nodes:
            return []

        node_map: dict[str, EvidenceNode] = {n.id: n for n in subgraph.nodes}
        focus_node = node_map.get(focus_node_id)
        if not focus_node and subgraph.root_node_id:
            focus_node = node_map.get(subgraph.root_node_id)
            if focus_node:
                focus_node_id = focus_node.id

        # 1. Build adjacency within subgraph
        adj: dict[str, list[tuple[str, EdgeType, str]]] = defaultdict(list)
        for e in subgraph.edges:
            if e.source_id in node_map and e.target_id in node_map:
                adj[e.source_id].append((e.target_id, e.edge_type, "OUT"))
                adj[e.target_id].append((e.source_id, e.edge_type, "IN"))

        # 2. Compute hop distances and shortest paths from focus_node_id via BFS
        distances: dict[str, int] = {focus_node_id: 0}
        paths: dict[str, list[str]] = {focus_node_id: [focus_node_id]}
        edge_types_on_path: dict[str, list[EdgeType]] = {focus_node_id: []}

        queue: deque[str] = deque([focus_node_id])
        while queue:
            curr = queue.popleft()
            curr_dist = distances[curr]

            for neighbor, etype, _ in sorted(adj[curr], key=lambda x: (x[0], x[1])):
                if neighbor not in distances:
                    distances[neighbor] = curr_dist + 1
                    paths[neighbor] = paths[curr] + [neighbor]
                    edge_types_on_path[neighbor] = edge_types_on_path[curr] + [etype]
                    queue.append(neighbor)

        # 3. Score each node
        ranked_items: list[EvidenceItem] = []
        target_impact_str = None
        if focus_node and "financial_impact" in focus_node.properties:
            target_impact_str = str(focus_node.properties.get("financial_impact"))
        elif query_context and "financial_impact" in query_context:
            target_impact_str = str(query_context["financial_impact"])

        for node in subgraph.nodes:
            dist = distances.get(node.id, 5)
            # Base topological proximity (decay over hops)
            proximity = 1.0 / (1.0 + 0.6 * dist)

            context_bonus = 0.0
            reasons: list[str] = []

            if node.id == focus_node_id:
                reasons.append("Primary investigation focus record")
                final_score = 1.0
            else:
                # Relationship bonuses based on edge types connecting to focus
                node_edges = [
                    e
                    for e in subgraph.edges
                    if (e.source_id == focus_node_id and e.target_id == node.id)
                    or (e.target_id == focus_node_id and e.source_id == node.id)
                ]
                direct_types = {e.edge_type for e in node_edges}

                if EdgeType.SUBJECT_OF_EXCEPTION in direct_types:
                    context_bonus += 0.35
                    reasons.append("Direct subject of exception")
                if EdgeType.SUPPORTED_BY_EVIDENCE in direct_types:
                    context_bonus += 0.30
                    reasons.append("Direct supporting evidence for exception")
                if EdgeType.GENERATED_BY_RECONCILIATION in direct_types:
                    context_bonus += 0.25
                    reasons.append("Reconciliation result flagging exception")
                if EdgeType.MATCHED_IN_RECONCILIATION in direct_types:
                    context_bonus += 0.25
                    reasons.append("Reconciliation match partner")
                if (
                    EdgeType.REFERENCES_PO in direct_types
                    or EdgeType.FULFILLED_BY_RECEIPT in direct_types
                ):
                    context_bonus += 0.20
                    reasons.append("Direct procurement document linkage")
                if (
                    EdgeType.PAID_BY_PAYMENT in direct_types
                    or EdgeType.PAYMENT_PAYS_INVOICE in direct_types
                ):
                    context_bonus += 0.20
                    reasons.append("Direct payment/settlement linkage")
                if EdgeType.APPEARS_AS_BANK_TX in direct_types:
                    context_bonus += 0.20
                    reasons.append("Direct bank statement representation")

                # Monetary impact match
                if target_impact_str and target_impact_str != "0.00":
                    node_amt = (
                        node.properties.get("total")
                        or node.properties.get("amount")
                        or node.properties.get("financial_impact")
                    )
                    if node_amt and str(node_amt) == target_impact_str:
                        context_bonus += 0.20
                        reasons.append(
                            f"Monetary amount exactly matches discrepancy ({target_impact_str})"
                        )

                # Exception status bonus
                if node.node_type == NodeType.EXCEPTION and node.id != focus_node_id:
                    context_bonus += 0.25
                    reasons.append(f"Associated active exception ({node.properties.get('type')})")
                elif node.node_type == NodeType.RECONCILIATION_RESULT and node.id != focus_node_id:
                    status = node.properties.get("status")
                    if status in ("MISMATCH", "PARTIAL", "MISSING"):
                        context_bonus += 0.20
                        reasons.append(f"Associated reconciliation discrepancy ({status})")

                # Entity type weighting
                if node.node_type in (
                    NodeType.INVOICE,
                    NodeType.PURCHASE_ORDER,
                    NodeType.GOODS_RECEIPT,
                    NodeType.PAYMENT,
                    NodeType.BANK_TRANSACTION,
                ):
                    context_bonus += 0.08
                elif node.node_type in (
                    NodeType.INVOICE_LINE,
                    NodeType.PO_LINE,
                    NodeType.RECEIPT_LINE,
                ):
                    context_bonus += 0.05
                elif node.node_type == NodeType.COMPANY:
                    context_bonus -= 0.15

                if not reasons:
                    reasons.append(f"Contextually linked at distance {dist} hops")

                final_score = min(0.99, max(0.05, proximity * 0.45 + context_bonus * 0.55))
            rounded_score = round(final_score, 4)

            ranked_items.append(
                EvidenceItem(
                    node=node,
                    score=rounded_score,
                    distance=dist,
                    path_summary=paths.get(node.id, [node.id]),
                    relevance_reason="; ".join(reasons),
                )
            )

        # 4. Deterministic sort: score desc, distance asc, node_type, id
        ranked_items.sort(
            key=lambda item: (
                -item.score,
                item.distance,
                item.node.node_type.value,
                item.node.id,
            )
        )

        if max_results is not None and max_results > 0:
            return ranked_items[:max_results]

        return ranked_items
