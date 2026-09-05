"""In-memory financial evidence graph with typed traversal and tenant isolation (spec section 7).

Pure deterministic financial evidence graph.
Enforces tenant isolation on all queries and mutations.
"""

from __future__ import annotations

import uuid
from collections import defaultdict, deque
from typing import Any

from app.evidence_graph.types import (
    EdgeDirection,
    EdgeType,
    EvidenceEdge,
    EvidenceNode,
    EvidencePath,
    EvidenceSubgraph,
    NodeType,
    TenantIsolationViolationError,
)


class FinancialEvidenceGraph:
    """A typed, tenant-isolated directed evidence graph for financial investigation."""

    def __init__(self, company_id: str | uuid.UUID) -> None:
        self._company_id = str(company_id)
        self._nodes: dict[str, EvidenceNode] = {}
        self._edges: dict[str, EvidenceEdge] = {}
        self._outgoing: dict[str, list[EvidenceEdge]] = defaultdict(list)
        self._incoming: dict[str, list[EvidenceEdge]] = defaultdict(list)
        self._nodes_by_type: dict[NodeType, list[str]] = defaultdict(list)
        self._edges_by_type: dict[EdgeType, list[str]] = defaultdict(list)

    @property
    def company_id(self) -> str:
        """The tenant ID bounding this graph."""
        return self._company_id

    @property
    def nodes(self) -> dict[str, EvidenceNode]:
        """Dictionary of all nodes in graph indexed by ID."""
        return self._nodes

    @property
    def edges(self) -> dict[str, EvidenceEdge]:
        """Dictionary of all edges in graph indexed by ID."""
        return self._edges

    # -------------------------------------------------------------------------
    # Mutation & Ingestion
    # -------------------------------------------------------------------------

    def add_node(self, node: EvidenceNode) -> None:
        """Add a typed node, verifying tenant isolation."""
        if str(node.company_id) != self._company_id:
            msg = (
                f"Cannot add node with company_id={node.company_id} to graph bounded by "
                f"{self._company_id}"
            )
            raise TenantIsolationViolationError(msg)
        if node.id in self._nodes:
            # Idempotent update
            old_type = self._nodes[node.id].node_type
            if old_type != node.node_type and node.id in self._nodes_by_type[old_type]:
                self._nodes_by_type[old_type].remove(node.id)
        else:
            self._nodes_by_type[node.node_type].append(node.id)

        self._nodes[node.id] = node

    def add_edge(self, edge: EvidenceEdge) -> bool:
        """Add a typed edge between two existing nodes, verifying tenant isolation."""
        if str(edge.company_id) != self._company_id:
            msg = (
                f"Cannot add edge with company_id={edge.company_id} to graph bounded by "
                f"{self._company_id}"
            )
            raise TenantIsolationViolationError(msg)

        # Both endpoints must belong to this graph
        if edge.source_id not in self._nodes or edge.target_id not in self._nodes:
            return False

        if edge.id in self._edges:
            return False  # Already present

        self._edges[edge.id] = edge
        self._outgoing[edge.source_id].append(edge)
        self._incoming[edge.target_id].append(edge)
        self._edges_by_type[edge.edge_type].append(edge.id)
        return True

    # -------------------------------------------------------------------------
    # Lookups
    # -------------------------------------------------------------------------

    def get_node(self, node_id: str) -> EvidenceNode | None:
        """Retrieve node by ID if it exists in the tenant graph."""
        return self._nodes.get(node_id)

    def has_node(self, node_id: str) -> bool:
        """Check if node ID exists in graph."""
        return node_id in self._nodes

    def get_edge(self, edge_id: str) -> EvidenceEdge | None:
        """Retrieve edge by ID."""
        return self._edges.get(edge_id)

    def get_nodes_by_type(self, node_type: NodeType) -> list[EvidenceNode]:
        """Retrieve all nodes matching a specific NodeType."""
        node_ids = self._nodes_by_type.get(node_type, [])
        return [self._nodes[nid] for nid in node_ids if nid in self._nodes]

    def get_edges_by_type(self, edge_type: EdgeType) -> list[EvidenceEdge]:
        """Retrieve all edges matching a specific EdgeType."""
        edge_ids = self._edges_by_type.get(edge_type, [])
        return [self._edges[eid] for eid in edge_ids if eid in self._edges]

    def get_adjacent_edges(
        self,
        node_id: str,
        direction: EdgeDirection = EdgeDirection.BOTH,
        allowed_edge_types: set[EdgeType] | None = None,
        excluded_edge_types: set[EdgeType] | None = None,
    ) -> list[EvidenceEdge]:
        """Get connected edges respecting direction and type filters."""
        if node_id not in self._nodes:
            return []

        edges: list[EvidenceEdge] = []
        if direction in (EdgeDirection.OUTGOING, EdgeDirection.BOTH):
            edges.extend(self._outgoing.get(node_id, []))
        if direction in (EdgeDirection.INCOMING, EdgeDirection.BOTH):
            edges.extend(self._incoming.get(node_id, []))

        # Filter
        result: list[EvidenceEdge] = []
        for e in edges:
            if allowed_edge_types is not None and e.edge_type not in allowed_edge_types:
                continue
            if excluded_edge_types is not None and e.edge_type in excluded_edge_types:
                continue
            result.append(e)

        return result

    def get_adjacent_nodes(
        self,
        node_id: str,
        direction: EdgeDirection = EdgeDirection.BOTH,
        allowed_edge_types: set[EdgeType] | None = None,
        allowed_node_types: set[NodeType] | None = None,
        excluded_edge_types: set[EdgeType] | None = None,
    ) -> list[EvidenceNode]:
        """Get connected neighbor nodes respecting direction, edge, and node type filters."""
        edges = self.get_adjacent_edges(
            node_id=node_id,
            direction=direction,
            allowed_edge_types=allowed_edge_types,
            excluded_edge_types=excluded_edge_types,
        )

        neighbors: list[EvidenceNode] = []
        seen: set[str] = set()
        for e in edges:
            neighbor_id = e.target_id if e.source_id == node_id else e.source_id
            if neighbor_id in seen or neighbor_id not in self._nodes:
                continue
            node = self._nodes[neighbor_id]
            if allowed_node_types is not None and node.node_type not in allowed_node_types:
                continue
            seen.add(neighbor_id)
            neighbors.append(node)

        return neighbors

    # -------------------------------------------------------------------------
    # Graph Traversals & Search
    # -------------------------------------------------------------------------

    def get_neighborhood(
        self,
        node_id: str,
        radius: int = 1,
        allowed_edge_types: set[EdgeType] | None = None,
        allowed_node_types: set[NodeType] | None = None,
        excluded_edge_types: set[EdgeType] | None = None,
    ) -> EvidenceSubgraph:
        """Retrieve all nodes and edges within `radius` hops of `node_id`.

        By default, excludes `BELONGS_TO_COMPANY` to prevent hub explosion across the tenant.
        """
        if excluded_edge_types is None:
            # Protect against company hub traversal unless explicitly permitted
            excluded_edge_types = {EdgeType.BELONGS_TO_COMPANY}

        return self.bfs_traversal(
            start_id=node_id,
            max_depth=radius,
            direction=EdgeDirection.BOTH,
            allowed_edge_types=allowed_edge_types,
            allowed_node_types=allowed_node_types,
            excluded_edge_types=excluded_edge_types,
        )

    def bfs_traversal(
        self,
        start_id: str,
        max_depth: int = 2,
        direction: EdgeDirection = EdgeDirection.BOTH,
        allowed_edge_types: set[EdgeType] | None = None,
        allowed_node_types: set[NodeType] | None = None,
        excluded_edge_types: set[EdgeType] | None = None,
    ) -> EvidenceSubgraph:
        """Perform a cycle-free breadth-first traversal up to `max_depth`."""
        if start_id not in self._nodes:
            return EvidenceSubgraph(nodes=[], edges=[], root_node_id=start_id, depth=max_depth)

        visited_nodes: set[str] = {start_id}
        collected_edges: dict[str, EvidenceEdge] = {}
        queue: deque[tuple[str, int]] = deque([(start_id, 0)])

        while queue:
            curr_id, curr_depth = queue.popleft()
            if curr_depth >= max_depth:
                continue

            adj_edges = self.get_adjacent_edges(
                node_id=curr_id,
                direction=direction,
                allowed_edge_types=allowed_edge_types,
                excluded_edge_types=excluded_edge_types,
            )

            for e in adj_edges:
                neighbor_id = e.target_id if e.source_id == curr_id else e.source_id
                if neighbor_id not in self._nodes:
                    continue

                neighbor_node = self._nodes[neighbor_id]
                if (
                    allowed_node_types is not None
                    and neighbor_node.node_type not in allowed_node_types
                ):
                    continue

                collected_edges[e.id] = e
                if neighbor_id not in visited_nodes:
                    visited_nodes.add(neighbor_id)
                    queue.append((neighbor_id, curr_depth + 1))

        nodes_list = [self._nodes[nid] for nid in sorted(visited_nodes)]
        edges_list = [collected_edges[eid] for eid in sorted(collected_edges.keys())]

        return EvidenceSubgraph(
            nodes=nodes_list,
            edges=edges_list,
            root_node_id=start_id,
            depth=max_depth,
            metadata={
                "total_nodes": len(nodes_list),
                "total_edges": len(edges_list),
                "company_id": self._company_id,
            },
        )

    def find_shortest_path(
        self,
        start_id: str,
        target_id: str,
        direction: EdgeDirection = EdgeDirection.BOTH,
        allowed_edge_types: set[EdgeType] | None = None,
        excluded_edge_types: set[EdgeType] | None = None,
    ) -> EvidencePath | None:
        """Find the shortest path between two records via BFS.

        Returns EvidencePath with sequence of nodes and edges, or None if unreachable.
        """
        if start_id not in self._nodes or target_id not in self._nodes:
            return None

        if start_id == target_id:
            node = self._nodes[start_id]
            return EvidencePath(
                source_id=start_id,
                target_id=target_id,
                hop_count=0,
                nodes=[node],
                edges=[],
                summary=f"Direct match on record {start_id}",
            )

        if excluded_edge_types is None:
            # Exclude company hub by default so paths reflect transactional causality
            excluded_edge_types = {EdgeType.BELONGS_TO_COMPANY}

        # Queue element: (current_node_id, path_edges, path_node_ids)
        queue: deque[tuple[str, list[EvidenceEdge], list[str]]] = deque(
            [(start_id, [], [start_id])]
        )
        visited: set[str] = {start_id}

        while queue:
            curr_id, path_edges, path_nodes = queue.popleft()

            adj_edges = self.get_adjacent_edges(
                node_id=curr_id,
                direction=direction,
                allowed_edge_types=allowed_edge_types,
                excluded_edge_types=excluded_edge_types,
            )

            # Sort deterministically
            adj_edges.sort(key=lambda e: e.id)

            for edge in adj_edges:
                neighbor_id = edge.target_id if edge.source_id == curr_id else edge.source_id
                if neighbor_id not in self._nodes:
                    continue

                if neighbor_id == target_id:
                    final_edges = path_edges + [edge]
                    final_node_ids = path_nodes + [neighbor_id]
                    final_nodes = [self._nodes[nid] for nid in final_node_ids]

                    summary_parts = []
                    for i, nid in enumerate(final_node_ids):
                        summary_parts.append(nid)
                        if i < len(final_edges):
                            summary_parts.append(f"──({final_edges[i].edge_type.value})──>")
                    summary = " ".join(summary_parts)

                    return EvidencePath(
                        source_id=start_id,
                        target_id=target_id,
                        hop_count=len(final_edges),
                        nodes=final_nodes,
                        edges=final_edges,
                        summary=summary,
                    )

                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, path_edges + [edge], path_nodes + [neighbor_id]))

        return None

    # -------------------------------------------------------------------------
    # Specialized High-Level Investigation Traversals
    # -------------------------------------------------------------------------

    def trace_payment_flow(self, payment_id: str | uuid.UUID) -> EvidenceSubgraph:
        """Trace a payment's complete causal flow: upstream invoices/POs and downstream bank/GL."""
        p_id = str(payment_id)
        if not p_id.startswith("PAYMENT:"):
            p_id = EvidenceNode.make_id(NodeType.PAYMENT, p_id)

        allowed_edges = {
            EdgeType.PAID_BY_PAYMENT,
            EdgeType.PAYMENT_PAYS_INVOICE,
            EdgeType.PAYMENT_TO_VENDOR,
            EdgeType.PAYMENT_ON_ACCOUNT,
            EdgeType.REFERENCES_PO,
            EdgeType.FULFILLED_BY_RECEIPT,
            EdgeType.ISSUED_BY_VENDOR,
            EdgeType.ISSUED_TO_VENDOR,
            EdgeType.APPEARS_AS_BANK_TX,
            EdgeType.RECORDED_ON_BANK_ACCOUNT,
            EdgeType.MAPPED_TO_JOURNAL_ENTRY,
            EdgeType.POSTS_TO_LEDGER,
            EdgeType.CONTAINS_LINE,
            EdgeType.MATCHED_IN_RECONCILIATION,
            EdgeType.EVALUATES_RECORD,
            EdgeType.SUBJECT_OF_EXCEPTION,
            EdgeType.SUPPORTED_BY_EVIDENCE,
        }
        return self.bfs_traversal(
            start_id=p_id,
            max_depth=4,
            direction=EdgeDirection.BOTH,
            allowed_edge_types=allowed_edges,
        )

    def trace_procurement_flow(self, invoice_id: str | uuid.UUID) -> EvidenceSubgraph:
        """Trace an invoice's complete 3-way matching and settlement flow."""
        inv_id = str(invoice_id)
        if not inv_id.startswith("INVOICE:"):
            inv_id = EvidenceNode.make_id(NodeType.INVOICE, inv_id)

        allowed_edges = {
            EdgeType.ISSUED_BY_VENDOR,
            EdgeType.REFERENCES_PO,
            EdgeType.ISSUED_TO_VENDOR,
            EdgeType.CONTAINS_LINE,
            EdgeType.REFERENCES_PO_LINE,
            EdgeType.RECEIPT_FULFILLS_PO_LINE,
            EdgeType.FULFILLED_BY_RECEIPT,
            EdgeType.PAID_BY_PAYMENT,
            EdgeType.PAYMENT_PAYS_INVOICE,
            EdgeType.APPEARS_AS_BANK_TX,
            EdgeType.MATCHED_IN_RECONCILIATION,
            EdgeType.EVALUATES_RECORD,
            EdgeType.SUBJECT_OF_EXCEPTION,
            EdgeType.SUPPORTED_BY_EVIDENCE,
        }
        return self.bfs_traversal(
            start_id=inv_id,
            max_depth=4,
            direction=EdgeDirection.BOTH,
            allowed_edge_types=allowed_edges,
        )

    def explain_exception(self, exception_id: str | uuid.UUID, radius: int = 2) -> EvidenceSubgraph:
        """Extract the exception, direct subjects, evidence, and 1-2 hop neighborhood."""
        exc_id = str(exception_id)
        if not exc_id.startswith("EXCEPTION:"):
            exc_id = EvidenceNode.make_id(NodeType.EXCEPTION, exc_id)

        if exc_id not in self._nodes:
            return EvidenceSubgraph(nodes=[], edges=[], root_node_id=exc_id)

        # 1. Start from exception
        nodes_collected: dict[str, EvidenceNode] = {exc_id: self._nodes[exc_id]}
        edges_collected: dict[str, EvidenceEdge] = {}

        # 2. Get all direct exception edges (subjects, supporting evidence, reconciliation results)
        direct_edges = self.get_adjacent_edges(exc_id, direction=EdgeDirection.BOTH)
        for e in direct_edges:
            edges_collected[e.id] = e
            other_id = e.target_id if e.source_id == exc_id else e.source_id
            if other_id in self._nodes:
                nodes_collected[other_id] = self._nodes[other_id]

        # 3. For each subject record, expand neighborhood by radius to discover context
        for subject_id in list(nodes_collected.keys()):
            if subject_id == exc_id:
                continue
            sub = self.get_neighborhood(
                node_id=subject_id,
                radius=radius,
                excluded_edge_types={EdgeType.BELONGS_TO_COMPANY},
            )
            for n in sub.nodes:
                nodes_collected[n.id] = n
            for e in sub.edges:
                edges_collected[e.id] = e

        return EvidenceSubgraph(
            nodes=[nodes_collected[k] for k in sorted(nodes_collected.keys())],
            edges=[edges_collected[k] for k in sorted(edges_collected.keys())],
            root_node_id=exc_id,
            depth=radius + 1,
            metadata={
                "exception_id": exc_id,
                "total_nodes": len(nodes_collected),
                "total_edges": len(edges_collected),
            },
        )

    def get_vendor_activity(self, vendor_id: str | uuid.UUID) -> EvidenceSubgraph:
        """Gather all contracts, purchase orders, invoices, and payments for a vendor."""
        v_id = str(vendor_id)
        if not v_id.startswith("VENDOR:"):
            v_id = EvidenceNode.make_id(NodeType.VENDOR, v_id)

        allowed_edges = {
            EdgeType.ISSUED_BY_VENDOR,
            EdgeType.ISSUED_TO_VENDOR,
            EdgeType.CONTRACT_WITH_VENDOR,
            EdgeType.PAYMENT_TO_VENDOR,
            EdgeType.VENDOR_BANK_ACCOUNT,
            EdgeType.PAID_BY_PAYMENT,
            EdgeType.PAYMENT_PAYS_INVOICE,
            EdgeType.REFERENCES_PO,
        }
        return self.bfs_traversal(
            start_id=v_id,
            max_depth=2,
            direction=EdgeDirection.BOTH,
            allowed_edge_types=allowed_edges,
        )

    # -------------------------------------------------------------------------
    # Statistics & Inspection
    # -------------------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """Summary metrics of the tenant evidence graph."""
        n_count = len(self._nodes)
        e_count = len(self._edges)
        density = (e_count / (n_count * (n_count - 1))) if n_count > 1 else 0.0

        nodes_by_type = {t.value: len(ids) for t, ids in self._nodes_by_type.items()}
        edges_by_type = {t.value: len(ids) for t, ids in self._edges_by_type.items()}

        return {
            "company_id": self._company_id,
            "total_nodes": n_count,
            "total_edges": e_count,
            "density": round(density, 6),
            "nodes_by_type": nodes_by_type,
            "edges_by_type": edges_by_type,
        }
