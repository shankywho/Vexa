# Vexa: Autonomous Office of the CFO

> **Investigate. Verify. Close.**

---

### 💡 Inspiration

Ask any corporate controller or accounting team what their least favorite time of the year is, and they won't say tax season—they’ll say **every single month-end**. 

Between 5 and 15 business days at the end of each month are lost to manual reconciliation purgatory. Accountants sit glued to spreadsheets, cross-referencing purchase orders against vendor bills, hunting down missing delivery receipts, untangling currency fluctuations, and trying to figure out why a bank deposit is short by $42.50. 

When autonomous agents surged in popularity, we saw waves of "AI CFO" chatbots and PDF invoice wrappers. But no serious enterprise CFO would ever trust a generic LLM near their general ledger. LLMs hallucinate numbers, fail at basic multi-currency floating-point arithmetic, and lack any institutional concept of internal controls or Sarbanes-Oxley (SOX) compliance.

We asked a foundational question:  
**What if an autonomous system separated reasoning from arithmetic? What if deterministic code calculated financial truth, while bounded AI agents investigated the anomalies?**

That conviction inspired **Vexa**—an engineering-grade, evidence-first autonomous month-end close engine.

---

### ⚙️ What It Does

Vexa automates the end-to-end month-end close workflow. Rather than acting as a chatbot, it operates as an autonomous operational controller:

1. **Deterministic Multi-Pass Reconciliation:** Ingests raw data across six silos (Purchase Orders, Invoices, Goods Receipts, Bank Statements, Payments, and the General Ledger) and runs 10 mathematical matching passes.
2. **Financial Evidence Graph Construction:** Maps every entity, contract line item, and transaction into a unified directed graph (20 node types and 21 edge types) to establish causal relationships across systems.
3. **Forensic Exception Investigation:** When discrepancies occur (e.g., price variances, quantity shortfalls, duplicate billings, or suspicious payment splitting), a bounded CFO Agent analyzes root causes.
4. **Three-Gate Independent Verification:** A completely separate verification agent checks the primary agent's hypothesis, recalculates the arithmetic, and verifies internal policy constraints.
5. **Controlled Autonomy & Reversibility:** Clears safe, immaterial variances autonomously with zero-money-movement compensating entries, while packaging material or risky anomalies into comprehensive escalation dossiers for human review.
6. **Institutional Auditability:** Every single action is stamped with an immutable audit trail mapped directly to SOX compliance controls (`AP-03`, `PROC-04`, `BANK-01`).

---

### 🛠️ How We Built It

Vexa is engineered with **Python 3.12**, **FastAPI**, **PostgreSQL**, and an asynchronous Server-Sent Events (SSE) telemetry bus.

```
Financial Records (Invoices, POs, Receipts, Payments, Bank, GL)
                           │
                           ▼
          [ 10-Pass Deterministic Reconciliation ]
                           │
                           ▼
          [ Exception Detection & Graph Assembly ]
                           │
                           ▼
       [ Investigation Agent — Google Gemini / Mistral ]
                           │
                           ▼
       [ Independent Verification Gate — Groq LPU ]
                           │
                           ▼
      [ Confidence Calibration & Policy Materiality Gate ]
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
   [ Level 3: Auto-Resolve ]   [ Level 1/2: Human Escalation ]
   (Compensating Adjustment)     (Controller/CFO Approval)
              │                         │
              └────────────┬────────────┘
                           ▼
          [ Immutable SOX Audit Logging & SSE Telemetry ]
                           │
                           ▼
         [ Evidence-Backed Close Package (JSON / PDF) ]
```

#### 1. Zero-Arithmetic-Authority Reconciliation
We established an ironclad rule: **LLMs never do math.** All monetary values are handled using fixed-point 64-bit precision decimals. The reconciliation engine runs deterministic passes (such as 3-way matching and bank-to-ledger clearance):

$$\Delta_{\text{variance}} = \left| \left( P_{\text{invoice}} \cdot Q_{\text{billed}} \right) - \left( P_{\text{PO}} \cdot Q_{\text{received}} \right) \right|$$

If $\Delta_{\text{variance}} > \epsilon$ (where $\epsilon = 0.00$), the transaction is isolated into an exception bundle and attached to a graph node.

#### 2. Multi-Hop Graph Traversal via Personalized PageRank
To give the AI agent exact context without overflowing prompt windows, Vexa builds an in-memory directed graph $G = (V, E)$. When an exception occurs on node $u$, we extract a localized subgraph by computing Personalized PageRank scores:

$$\mathbf{p} = (1 - d)\mathbf{v} + d \mathbf{M} \mathbf{p}$$

Where:
- $d = 0.85$ is the damping factor
- $\mathbf{v}$ is the teleportation vector seeded strictly on the anomalous transaction nodes
- $\mathbf{M}$ is the row-normalized adjacency matrix across transaction edges (e.g., `SETTLES`, `FULFILLS`, `AUTHORIZES`)

The top $k$ ranked entities assemble into a bounded `EvidenceDossier`.

#### 3. Heterogeneous Multi-Provider LLM Architecture
To avoid self-grading bias and vendor-correlated reasoning failures, Vexa enforces a strict **Segregation of Duties**:
- **Close Workflow Controller:** Powered by **Google Gemini** (`gemini-3.5-flash-lite` / `gemini-2.0-flash`) orchestrating the state machine and step execution DAG.
- **Forensic Investigation Agent:** Formulates root-cause hypotheses with bounded context.
- **Independent Verification Agent:** Powered by an independent provider (e.g., Groq LPUs) to evaluate the hypothesis and confirm that the cited evidence actually supports the conclusion.
- **Anti-Collusion Check:** If a network failover forces both agents onto the same model provider, the system logs an audit warning and applies a mandatory $-0.10$ confidence penalty.

#### 4. Empirical Confidence Calibration
Raw LLM probabilities are notoriously overconfident. We compute an empirically calibrated confidence score:

$$c_{\text{calibrated}} = c_{\text{raw}} - \sum_{k} \lambda_k \cdot \mathbb{I}_{\text{penalty}_k}$$

Where penalty weights $\lambda_k$ penalize missing citations ($\lambda = 0.15$), cross-model provider overlap ($\lambda = 0.10$), and ambiguous timing differences ($\lambda = 0.05$).

#### 5. Controlled Autonomy Matrix
Vexa restricts autonomy using a 4-tier governance policy:

$$\text{Action} = \begin{cases} 
\text{Level 3 (Execute)} & \text{if } \Delta_{\text{variance}} \le \tau_{\text{mat}} \land c_{\text{calibrated}} \ge 0.95 \land \text{Violations} = \emptyset \\
\text{Level 2 (Stage)} & \text{if } \Delta_{\text{variance}} > \tau_{\text{mat}} \land c_{\text{calibrated}} \ge 0.80 \\
\text{Level 1 (Recommend)} & \text{if } \text{HardPolicyConflict} = \text{True} \lor c_{\text{calibrated}} < 0.80 \\
\text{Level 0 (Observe)} & \text{otherwise}
\end{cases}$$

*(where default corporate materiality threshold $\tau_{\text{mat}} = \$50,000$)*

---

### 🧗 Challenges We Faced

1. **The Hallucination vs. Accounting Balance Dilemma**  
   In accounting, being 99% accurate is a failure. If an LLM invents a single line-item ID or misinterprets a payment reference, it corrupts the audit trail. We engineered a strict `CitationValidator` that intercepts agent outputs before downstream propagation. Any cited entity not present in the pre-compiled `EvidenceDossier` causes the verification step to fail immediately and halts autonomy.

2. **Mitigating "Agent Sycophancy"**  
   When the verification agent shared the same model family as the investigation agent, it routinely agreed with flawed hypotheses. We solved this by enforcing architectural heterogeneity: the investigator and verifier run on completely distinct models and parameter families.

3. **Taming Graph Complexity within Context Windows**  
   A enterprise ledger contains tens of thousands of journal entries. Dumping raw tables into an LLM context creates severe signal-to-noise degradation. Implementing Personalized PageRank bounded subgraphs allowed us to condense massive transactional graphs into tight, 20-node dossiers that provide the exact context needed.

4. **Zero Live-Demo Failure Modes**  
   Nothing kills a hackathon presentation faster than third-party API rate limits or network drops. We built a dual-mode engine: `LIVE` mode (querying live LLMs and DBs) and `REPLAY` mode (streaming recorded trace runs through identical SSE endpoints at authentic typing cadences). The frontend cannot tell the difference, guaranteeing presentation safety.

---

### 🏆 Accomplishments That We're Proud Of

- **Flawless Benchmark Performance:** Evaluated against **CFO-Bench** (35 ground-truth month-end close scenarios ranging from FX variances to invoice structuring fraud), Vexa achieved:
  - **F1 Score:** **$1.0000$** ($35 / 35$ scenarios passed)
  - **Financial Calculation Accuracy:** **$100\%$**
  - **Citation Hallucination Rate:** **$0.00\%$**
  - **Expected Calibration Error ($\text{ECE}$):** **$0.0135$** (well below the $0.05$ threshold)
- **156/156 Passing Automated Tests:** Full test suite covering reconciliation edge cases, graph cycles, and agent recovery mechanisms.
- **Extreme Operational Economics:** The entire 35-scenario month-end close benchmark executes for just **$\$0.023$ (2.3 cents)** in total inference costs, while eliminating an estimated **11.7 hours** of manual accounting work.

---

### 📚 What We Learned

- **Keep Math Deterministic, Keep Language Semantic:** LLMs are exceptional at pattern recognition and forensic reasoning (e.g., discovering that 14 payments of ₹1,00,000 were structured on the same day to bypass single-transaction sign-off limits). But they must never touch raw sums. Bridging deterministic math engines with semantic reasoning agents creates software that is both intelligent and trustworthy.
- **Internal Controls Must Be First-Class Code Constructs:** Separation of duties, maker-checker authorization, and immutable audit logging cannot be prompt instructions—they must be hard architectural barriers in code.

---

### 🚀 What's Next for Vexa

- **Live ERP Connectors:** Direct bidirectional sync adapters for NetSuite, SAP S/4HANA, and QuickBooks Online.
- **Continuous Close:** Moving from a monthly batch process to a streaming reconciliation engine that resolves discrepancies in real time as bank feeds clear.
- **Multi-Entity Global Consolidation:** Automated intercompany elimination entries and FX revaluation for multinational corporate structures.
