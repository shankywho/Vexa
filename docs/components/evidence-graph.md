# Evidence Graph Component Deep Dive

The Evidence Graph component builds and traverses an in-memory directed knowledge graph of all financial records for a given tenant company.

---

## 1. Package Structure

Located at [`backend/app/evidence_graph/`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/evidence_graph/):

```
app/evidence_graph/
├── __init__.py
├── builder.py          # FinancialEvidenceGraphBuilder (PostgreSQL -> In-memory graph)
├── graph.py            # FinancialEvidenceGraph (Directed graph, adjacency, traversals)
├── ranker.py           # EvidenceRanker (PageRank scoring & subgraph extraction)
├── serialization.py    # Graph serializers (JSON, GraphML, Cytoscape, Markdown)
└── types.py            # NodeType (20), EdgeType (21), EvidenceNode, EvidenceEdge
```

---

## 2. In-Memory Graph Implementation

The [`FinancialEvidenceGraph`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/evidence_graph/graph.py) maintains dual adjacency structures in memory:
* **Forward Adjacency:** `_adj: dict[str, dict[str, EvidenceEdge]]` mapping `source_id -> {target_id: edge}`.
* **Reverse Adjacency:** `_rev_adj: dict[str, dict[str, EvidenceEdge]]` mapping `target_id -> {source_id: edge}`.
* **Nodes Index:** `_nodes: dict[str, EvidenceNode]` mapping `node_id -> node`.

### Core Traversal Operations
* **`get_neighbors(node_id, direction, edge_types)`**: Fast $O(1)$ neighbor lookup filtering by direction (`OUTGOING`, `INCOMING`, `BOTH`) and edge categories.
* **`find_path(source_id, target_id, max_depth)`**: Bidirectional Breadth-First Search (BFS) computing the shortest causal path between two transactions.
* **`extract_subgraph(center_node_id, max_depth)`**: BFS bounded subgraph extractor isolating entities within $K$ hops of an exception.

---

## 3. Personalized PageRank Relevance Algorithm

The [`EvidenceRanker`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/evidence_graph/ranker.py) computes relevance scores for every node relative to an exception's root entity:

```python
# app/evidence_graph/ranker.py
# Power iteration with personalization vector
p_vector = {root_node_id: 1.0}  # All initial probability mass on focus node
scores = dict(p_vector)

for iteration in range(iterations):
    next_scores = defaultdict(float)
    for node_id, current_score in scores.items():
        neighbors = graph.get_neighbors(node_id, direction=EdgeDirection.BOTH)
        if neighbors:
            distributed = (current_score * damping) / len(neighbors)
            for neighbor_id in neighbors:
                next_scores[neighbor_id] += distributed
        else:
            next_scores[root_node_id] += current_score * damping
            
    # Add restart mass
    for node_id in graph.nodes:
        next_scores[node_id] += (1.0 - damping) * p_vector.get(node_id, 0.0)
    scores = next_scores
```

* **Distance Damping:** Raw PageRank scores are discounted by distance from the root:
  $$\text{FinalScore}(u) = \text{Score}(u) \cdot e^{-0.5 \cdot \text{distance}}$$
* **Threshold Filtering:** Only nodes scoring $\ge 0.05$ are included in the final investigation dossier, keeping context token budgets compact and highly relevant.

---

## 4. Multi-Tenant Safety Invariant

Every method touching nodes or edges asserts tenant isolation:
```python
if node.company_id != self.company_id:
    raise TenantIsolationViolationError(
        f"Cross-tenant node rejected: {node.company_id} != {self.company_id}"
    )
```
Cross-tenant query contamination is impossible at runtime.
