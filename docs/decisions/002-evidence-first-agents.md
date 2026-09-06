# ADR 002: Evidence-First Agents

## Context
When investigating complex accounting exceptions (e.g. why an invoice amount differs from a purchase order), an agent requires context across related documents, counterparties, payments, and bank transactions.

## Problem
Naively querying databases or vector search indices allows agents to ingest unrelated records, hallucinate phantom transactions, or leak confidential cross-tenant information into prompt context windows.

## Decision
Implement the **Evidence-First Bounded Dossier Pattern**:
1. All relationships are modeled in an in-memory directed `FinancialEvidenceGraph` with 20 typed nodes and 21 typed edges.
2. For every exception, the system extracts a focused subgraph using personalized PageRank relevance scoring (up to 4 hops).
3. The context is frozen into an immutable `EvidenceDossier` containing a strict whitelist of `valid_record_ids`.
4. A deterministic `CitationValidator` rejects any agent finding that cites an identifier outside this whitelist.

## Alternatives Considered
* **Vector RAG (Embeddings):** Chunking financial documents and querying a vector database. Rejected because vector embeddings discard numerical precision, lose multi-hop structural relationships (PO $\rightarrow$ Receipt $\rightarrow$ Bill $\rightarrow$ Payment), and easily retrieve irrelevant context.
* **Open SQL Agent:** Equipping the agent with SQL query tools to explore the schema freely. Rejected due to latency spikes, unbounded execution loops, and SQL injection / cross-tenant leakage risks.

## Consequences
* **Positive:** Zero hallucinated citations; mathematically bounded context; deterministic provenance for every fact and inference.
* **Trade-off:** Requires pre-building graph builder and dossier serializer infrastructure before agent invocation.
