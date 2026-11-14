# Enterprise Procurement Intelligence

**Procurement Intelligence. Powered by Evidence.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3-61DAFB.svg)](https://reactjs.org/)

> Graph-enhanced RAG platform with multi-agent orchestration, hybrid retrieval, model routing, and MCP interoperability for procurement intelligence.

**Live Demo:** [enterprise-procurement-intelligence-n04pc4po3.vercel.app](https://enterprise-procurement-intelligence-n04pc4po3.vercel.app)  
**API:** [enterprise-procurement-intelligence.onrender.com](https://enterprise-procurement-intelligence.onrender.com)  
**API Docs:** [/docs](https://enterprise-procurement-intelligence.onrender.com/docs)

---

## The Problem

Procurement data lives fragmented across systems—contracts in document repositories, supplier records in ERP databases, compliance certificates in email, pricing schedules in spreadsheets. Traditional keyword search cannot answer *"Which suppliers have active ISO 27001 certificates and pricing below £50k?"* because evidence spans multiple sources and requires reasoning over entity relationships, temporal validity, and numerical comparisons.

## The Solution

EPI unifies documents, structured procurement data, and entity relationships into a queryable intelligence layer. The system classifies incoming queries by intent and complexity, routes them through specialized retrieval strategies (dense vectors, BM25 sparse, graph traversal, SQL aggregations), and grounds every answer in source evidence with page-level citations. A LangGraph agent orchestrates parallel evidence gathering, evaluation, optional query rewriting, generation, and grounding verification in a corrective loop that stops when evidence is sufficient or iteration limits are reached.

---

## Core Capabilities

**Multi-Agent Orchestration (LangGraph)**
- 11-node agent graph: understand → plan → parallel evidence → vision → evaluate → (rewrite loop) → generate → verify → finalize
- Query understanding with entity linking against tenant vocabulary (suppliers, products, contracts)
- Parallel evidence gathering: dense retrieval, BM25 sparse, graph traversal, SQL aggregations execute concurrently
- Evidence evaluation with sufficiency scoring and conflict detection
- Bounded corrective loop (max 2 iterations by default) with query rewriting
- Grounding verification: claim extraction, evidence binding, unsupported claim detection
- Extractive fallback when no LLM is configured

**Intelligent Classification & Model Routing**
- **Query Intent Classification** (9 categories): price_lookup, contract_terms, comparison, temporal_change, compliance_check, aggregation, relationship, document_lookup, general
- **Model Task Routing** (8 routing tasks): classify, plan, rewrite, generate, compare, verify, vision, extract
- **Complexity-based tiering**: routes high-complexity tasks to large LLM, simple extractions to small LLM
- **Deterministic engines**: Python for arithmetic, SQL for aggregations, Neo4j Cypher for graph traversal
- **Fallback handling**: Vision unavailable → text evidence; LLM unavailable → extractive mode

**Hybrid Retrieval Engineering**
- **Dense retrieval**: BAAI/bge-m3 embeddings (1024-dim) via sentence-transformers, cosine similarity
- **Sparse retrieval**: BM25 keyword matching via rank-bm25
- **Reciprocal Rank Fusion (RRF)**: combines dense and sparse rankings with configurable k=45
- **Cross-encoder reranking**: BAAI/bge-reranker-v2-m3 for precision (reranks top-50 to top-15)
- **Measured performance** (150-question benchmark v4, rebuilt corpus): Recall@10: **98.0%**, MRR: **0.878**, nDCG@10: **0.903**; answer accuracy 44.0% literal (38.3% → 46.9% on the identical 120 questions, within noise)

**Knowledge Graph & GraphRAG**
- Neo4j property graph: 9 node types (Supplier, Contract, Buyer, Product, Price, Compliance, Document, Clause, Obligation)
- Entity extraction during document ingestion with rule-based and optional LLM parsers
- Entity normalization and linking to tenant vocabulary
- Multi-hop graph traversal (1-3 hops) with temporal filtering (as_of date support)
- Graph-enhanced retrieval: entity expansion → vector search → reranking → synthesis
- Provenance tracking: all nodes include tenant_id and source_doc_id

**Document Intelligence**
- **Supported formats**: PDF (native + scanned OCR), DOCX, XLSX, JPG/PNG (PaddleOCR)
- **Parsing**: PyMuPDF for PDF text/tables/images, python-docx for Word, openpyxl for Excel
- **Semantic chunking**: 320-token target, 700-token max, 60-token overlap, sentence-boundary-aware
- **Metadata extraction**: Contract number, parties, dates, values, CPV codes, clause detection
- **Chunk enrichment**: Prepends document metadata (title, supplier, date) for improved context
- **Pipeline**: Upload → validation → S3/MinIO storage → parsing → OCR → chunking → embedding → vector index + graph index

**Model Context Protocol (MCP) Server**
- **9 registered tools** exposing read-only procurement intelligence
- **stdio transport**: Compatible with Claude Desktop, Cline, and MCP-enabled assistants
- **Authorization**: Every tool call validates tenant context and RBAC permissions
- **Audit logging**: All invocations logged to audit_logs table with timestamp, principal, inputs, outcomes
- **Tools**: search_documents, get_document, search_contracts, get_supplier_profile, get_contract_amendments, get_ingestion_status, get_evaluation_metrics, search_graph, get_entity_neighbours

**Security & Multi-Tenancy**
- JWT authentication (HS256, 15-min access tokens, 7-day refresh tokens in httpOnly cookies)
- Role-based access control: admin, analyst, viewer with permission checks (e.g., docs:read, query:ask)
- Tenant isolation at database, vector store, and graph layers
- Document-level authorization with access_level field
- Audit logging with structured events (authentication, document access, query execution, admin actions)
- Argon2 password hashing, CORS whitelist, request ID tracing, Pydantic input validation

---

## System Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[React SPA<br/>TypeScript + Vite<br/>15+ pages]
    end

    subgraph "API Gateway"
        API[FastAPI<br/>70+ REST endpoints]
        Auth[JWT + RBAC<br/>Tenant isolation]
        API --> Auth
    end

    subgraph "LangGraph Agent Orchestration"
        Understand[Query Understanding<br/>Entity linking]
        Plan[Query Planning<br/>Intent + routing]
        Parallel[Parallel Evidence<br/>Dense ‖ Sparse ‖ Graph ‖ SQL]
        Vision[Vision Processing<br/>VLM for images]
        Evaluate[Evidence Evaluation<br/>Sufficiency + conflicts]
        Rewrite[Query Rewriting<br/>Corrective loop]
        Generate[Answer Generation<br/>LLM or extractive]
        Verify[Grounding Verification<br/>Claim-evidence binding]
        
        Understand --> Plan --> Parallel --> Vision --> Evaluate
        Evaluate -->|Insufficient| Rewrite --> Parallel
        Evaluate -->|Sufficient| Generate --> Verify
    end

    subgraph "Model Router"
        IntentClass[Intent Classifier<br/>9 query types]
        TaskRoute[Task Router<br/>8 routing tasks]
        ModelTier[Model Tier Selection<br/>LLM/Small/VLM/SQL/Graph]
        
        Plan --> IntentClass --> TaskRoute --> ModelTier
    end

    subgraph "Retrieval Engine"
        Dense[Dense Search<br/>bge-m3 embeddings<br/>Top-50]
        Sparse[BM25 Sparse<br/>rank-bm25<br/>Top-50]
        GraphTrav[Graph Traversal<br/>Neo4j Cypher<br/>Multi-hop]
        SQLQuery[SQL Aggregations<br/>PostgreSQL<br/>Exact answers]
        RRF[Reciprocal Rank Fusion<br/>k=45]
        Rerank[Cross-Encoder Reranking<br/>bge-reranker-v2-m3<br/>Top-15]
        
        Parallel --> Dense
        Parallel --> Sparse
        Parallel --> GraphTrav
        Parallel --> SQLQuery
        Dense --> RRF
        Sparse --> RRF
        RRF --> Rerank
    end

    subgraph "MCP Tool Boundary"
        MCPServer[MCP Server<br/>stdio transport]
        MCPTools[9 Read Tools<br/>search/get/profile]
        MCPGuard[Authorization Guard<br/>Tenant context + RBAC]
        
        MCPServer --> MCPGuard --> MCPTools
    end

    subgraph "Document Intelligence Pipeline"
        Upload[Upload & Validate<br/>Size, type, malware]
        Parse[Format Parser<br/>PDF/DOCX/XLSX/OCR]
        Extract[Metadata Extraction<br/>Contract data, clauses]
        Chunk[Semantic Chunking<br/>320 tokens, 60 overlap]
        Embed[Embedding Generation<br/>bge-m3]
        VIndex[Vector Indexing<br/>Qdrant or local]
        GIndex[Graph Indexing<br/>Neo4j entities]
        
        Upload --> Parse --> Extract --> Chunk --> Embed --> VIndex
        Extract --> GIndex
    end

    subgraph "Storage Layer"
        PG[(PostgreSQL<br/>24 tables<br/>Relational data)]
        VDB[(Qdrant<br/>Dense vectors<br/>1024-dim)]
        Neo[(Neo4j<br/>Property graph<br/>9 node types)]
        S3[(S3/MinIO<br/>Document blobs)]
        Redis[(Redis<br/>Response cache)]
    end

    UI -->|HTTP/SSE| API
    API --> Understand
    Rerank --> Generate
    Parse --> S3
    Embed --> VDB
    Extract --> Neo
    Generate --> PG
    MCPTools --> PG
    MCPTools --> VDB
    MCPTools --> Neo
    
    GraphTrav -.->|Cypher| Neo
    SQLQuery -.->|SQL| PG
    Dense -.->|Vector search| VDB
    
    style Understand fill:#4a90e2
    style ModelTier fill:#e25050
    style RRF fill:#50c878
    style Neo fill:#e25050
    style MCPServer fill:#f39c12
```

**Architecture Notes:**
- **Logical vs Deployed**: Diagram shows complete architecture. Current Render deployment uses SQLite (not PostgreSQL), local vectors (not Qdrant), local graph (not Neo4j). Configurable via environment variables.
- **MCP as Tool Boundary**: MCP server is separate from core retrieval—it exposes read tools over protocol, not a retrieval algorithm.
- **Parallel Evidence**: Dense, sparse, graph, and SQL execute concurrently in agent's parallel node.

---

## Intelligent Classification & Model Routing

EPI implements a **two-level routing system**:

1. **Query Intent Classification** → Determines **what** the user is asking (business logic)
2. **Model Task Routing** → Determines **which model/engine** to use (infrastructure)

### Level 1: Query Intent Classification (9 Categories)

Implemented in `backend/app/retrieval/query_understanding.py` as `Intent` enum.

**Classification Method:** Rule-based regex patterns + tenant vocabulary entity linking (suppliers, products, contracts from database). Optional LLM fallback when configured.

| Intent | Triggers | Processing Strategy | Example |
|--------|---------|--------------------|---------| 
| **PRICE_LOOKUP** | "price", "cost", product mentions | SQL price table + dense retrieval | *"What's the unit price for Product X?"* |
| **CONTRACT_TERMS** | "terms", "payment", clause keywords | Dense + sparse hybrid | *"Payment terms in the Acme contract"* |
| **COMPARISON** | "compare", "vs", "cheaper", "better" | Multi-document dense + LLM synthesis | *"Compare supplier A vs supplier B pricing"* |
| **TEMPORAL_CHANGE** | "current", "changed", "amendment", "after" | Temporal filtering + graph traversal | *"What changed in the latest amendment?"* |
| **COMPLIANCE_CHECK** | "ISO", "certified", "compliance", "valid" | Graph traversal (HAS_CERT edges) + documents | *"Which suppliers have ISO 27001?"* |
| **AGGREGATION** | "total", "average", "count", "sum" | SQL aggregation (exact answers) | *"Total contract value by supplier"* |
| **RELATIONSHIP** | "which suppliers", "connected", "contracts with" | Graph multi-hop traversal + entity expansion | *"Suppliers with active contracts for buyer Y"* |
| **DOCUMENT_LOOKUP** | Document type keywords, file references | Dense + sparse retrieval, no LLM needed | *"Find the master services agreement"* |
| **GENERAL** | Open-ended, no clear intent | Full hybrid RAG pipeline with LLM | *"Tell me about recent procurement activity"* |

**Entity Linking:** Query understanding extracts mentions of suppliers, products, contracts, and SKUs, then links them to actual database IDs using fuzzy name matching and initials resolution against a tenant-specific vocabulary cache.

### Level 2: Model Task Routing (8 Routing Tasks)

Implemented in `backend/app/providers/router.py` as `Task` enum and `ModelRouter` class.

**Routing Logic:**
```python
def route(task: Task, complexity: str = None, requires_vision: bool = False) -> RouteDecision:
    if requires_vision and vlm_available:
        return RouteDecision(task, ENGINE_VLM, vlm_model)
    if task in [CLASSIFY, REWRITE, EXTRACT] and small_llm_configured:
        return RouteDecision(task, ENGINE_SMALL_LLM, small_llm_model)
    if complexity == "high":
        return RouteDecision(task, ENGINE_LLM, llm_model)
    return RouteDecision(task, default_engine(task), default_model(task))
```

| Routing Task | Default Engine | Purpose | Fallback |
|--------------|----------------|---------|----------|
| **CLASSIFY** | Small LLM | Cheap structure extraction (intent, entities) | LLM if no small model |
| **PLAN** | LLM | Query planning and tool selection | None (required for agent) |
| **REWRITE** | Small LLM | Query expansion in corrective loop | LLM if no small model |
| **GENERATE** | LLM | Final grounded answer generation | Extractive mode if no LLM |
| **COMPARE** | LLM | Multi-document synthesis and comparison | Extractive concatenation |
| **VERIFY** | LLM | Grounding verification and claim extraction | Rule-based citation check |
| **VISION** | VLM | Page image understanding (charts, tables) | Text evidence from OCR |
| **EXTRACT** | Small LLM | Table/metadata extraction from unstructured text | Rule-based extraction |

**Additional Engines:**
- `ENGINE_PYTHON`: Deterministic arithmetic (unit conversions, date math)
- `ENGINE_SQL`: PostgreSQL aggregations (SUM, COUNT, AVG with exact answers)
- `ENGINE_GRAPH`: Neo4j Cypher traversal (relationship queries, multi-hop paths)

**Fallback Behavior:**
- No LLM configured → Extractive mode (returns top-ranked evidence chunks with confidence scores)
- Vision unavailable → Uses OCR text from PaddleOCR instead of VLM understanding
- Small LLM not configured → Routes small tasks to primary LLM (increased cost/latency)

### Query Processing Flow

```mermaid
sequenceDiagram
    participant User
    participant Agent as LangGraph Agent
    participant Understand as Query Understanding
    participant IntentClass as Intent Classifier
    participant Router as Model Router
    participant Dense as Dense Retrieval
    participant Sparse as Sparse Retrieval
    participant Graph as Graph Traversal
    participant SQL as SQL Aggregation
    participant Fusion as RRF Fusion
    participant Rerank as Cross-Encoder
    participant LLM as LLM Generation

    User->>Agent: "Which suppliers have ISO 27001?"
    Agent->>Understand: Extract entities & keywords
    Understand->>IntentClass: Analyze query patterns
    IntentClass-->>Agent: Intent: COMPLIANCE_CHECK
    Agent->>Router: Route task=PLAN, complexity=medium
    Router-->>Agent: Engine: LLM
    Agent->>Dense: Search "ISO 27001 certified"
    Agent->>Sparse: BM25 "ISO 27001"
    Agent->>Graph: MATCH (s:Supplier)-[:HAS_CERT]->(:Compliance {cert_type: 'ISO 27001'})
    Agent->>SQL: SELECT DISTINCT supplier_id FROM compliance_certificates WHERE cert_type='ISO 27001'
    Dense-->>Fusion: 50 candidates (vector scores)
    Sparse-->>Fusion: 50 candidates (BM25 scores)
    Fusion->>Rerank: 80 unique candidates (fused scores)
    Rerank-->>Agent: Top-15 reranked chunks
    Graph-->>Agent: [supplier_123, supplier_456] + metadata
    SQL-->>Agent: [supplier_123, supplier_789]
    Agent->>Router: Route task=GENERATE, complexity=low
    Router-->>Agent: Engine: LLM
    Agent->>LLM: Generate answer from evidence
    LLM-->>Agent: "Suppliers with ISO 27001: Acme Corp, Global Supplies..."
    Agent->>Agent: Verify grounding (claim-evidence binding)
    Agent-->>User: Answer + Citations + Confidence
```

---

## Hybrid Retrieval & Reciprocal Rank Fusion

### Retrieval Pipeline

```mermaid
graph LR
    Query[Query + Plan] --> Dense[Dense Search<br/>bge-m3<br/>Top-50]
    Query --> Sparse[Sparse Search<br/>BM25<br/>Top-50]
    Dense --> Fusion[Reciprocal Rank Fusion<br/>k=45]
    Sparse --> Fusion
    Fusion --> Rerank[Cross-Encoder<br/>bge-reranker-v2-m3<br/>Top-15]
    Rerank --> Context[Context Builder<br/>Select top-12<br/>Max 6K tokens]
    Context --> Generation[Answer Generation]
    
    style Fusion fill:#50c878
    style Rerank fill:#e25050
```

**Implementation:** `backend/app/retrieval/retriever.py` (HybridRetriever), `backend/app/retrieval/fusion.py` (reciprocal_rank_fusion)

### Reciprocal Rank Fusion (RRF)

**Formula:** `score = w_dense / (k + rank_dense) + w_sparse / (k + rank_sparse)`

**Configuration:**
- **k = 45** (down from 60 to weight top documents more heavily)
- **weights = (1.0, 1.0)** (equal weighting of dense and sparse)
- **Dense top-K = 50**, **Sparse top-K = 50**, **Fused output = unique candidates**

**Why RRF:** Dense cosine scores and BM25 scores are not comparable in magnitude. RRF combines *ranks*, which is stable, needs no score normalization, and is documented as the fusion algorithm for this platform (PRD s.29).

### Benchmark Results (150-Question Dataset, v4)

Measured 2026-11-14 on the rebuilt corpus, after a full re-ingestion of every source document. Full report and per-question traces: `data/evaluation/benchmark_v4/REPORT.md` and `results/run_A/rows.jsonl`.

**Dataset:** 150 questions (`data/evaluation/benchmark_v4/questions.json`, SHA-256 `0f6fa03d…f53606d3`): 94 answerable, 41 unanswerable, 15 carried-over v3 items still marked `needs_review`; 120 from v3 plus 30 new labels verified against the cited page text. No label is human-adjudicated.

**Corpus:** 20 source documents (19 indexed, 1 empty portal page), 42 pages, 655 chunks. Character coverage 98.1%; the 22-page UKRI PDF reaches 93.9% because page headers/footers are stripped without a boilerplate tag, and one DOCX exposes only 409 characters of text (content in an embedded object).

**Retrieval** (98 questions with a known source document; top-k 10, dense 50 + BM25 50, reranked to 15):

| Metric | Value |
| --- | --- |
| Recall@1 | 81.6% |
| Recall@3 | 92.9% |
| Recall@5 | 94.9% |
| Recall@10 | 98.0% |
| MRR | 0.878 |
| nDCG@10 | 0.903 |

**Answer quality** (109 answerable questions with labelled facts):

| Metric | Value |
| --- | --- |
| Literal fact containment | 44.0% (48/109; 95% CI 35.1–53.4%) |
| Normalized fact match | 44.0% |
| Same-model LLM judge | 32.5% (13/40; not independent) |
| Citation precision / recall | 69.6% / 75.5% (85 questions) |
| Pipeline faithfulness | 67.3% (99 questions); unsupported-claim rate 32.7% |

**Refusals** (refuse = positive class, 150 questions):

| Metric | Value |
| --- | --- |
| Correct refusals / false refusals | 33 / 34 |
| False answers | 8 |
| Precision | 49.3% |
| Recall | 80.5% |
| Accuracy | 72.0% (64.3–78.6%) |

**Baseline comparison on the same 120 questions (Run B):** answer accuracy 38.3% → 46.9% (+8.6 pp; confidence intervals overlap, so this is **within noise**); Recall@10 86.8% → 97.1% and MRR 0.779 → 0.886 (**real** — the retriever is deterministic and the intervals do not overlap); refusal precision 42.9% → 53.5% (not separable from noise). The old 86.8% Recall@5 = Recall@10 was verified as real, not a cut-off bug.

**Performance:** p50 9,316 ms, p95 29,479 ms, p99 46,042 ms, max 48,445 ms; 280,736 prompt and 11,221 completion tokens; no cost is configured for the local model.

**Configuration:** qwen2.5-coder:7b (Ollama, temperature 0.1), BAAI/bge-small-en-v1.5 (384-dim, CUDA), BAAI/bge-reranker-v2-m3, RRF k=45, context 12 chunks / 6000 tokens, chunking 320/700/60. No small LLM is installed and the VLM endpoint has no vision model.

**Limitations:** labels are machine-verified, not human-adjudicated; the judge shares the generator model; variance was measured on a 50-question subset (answer accuracy 36.1–38.9%, retrieval identical); one DOCX's text is missing from its text layer; 20 documents of one procurement type limit generalisation.

**No Regression Framework:** EPI does not currently have automated baseline-vs-candidate regression testing. Benchmark runs are stored in `evaluation_runs` table for manual comparison via `/api/v1/evaluation/compare` endpoint.

---

## Knowledge Graph & GraphRAG

**Implementation:** `backend/app/graph/builder.py` (graph construction), `backend/app/providers/graph/` (Neo4j + SQLite providers)

### Graph Schema

```mermaid
graph LR
    Buyer[Buyer<br/>name, id, sector] -->|PROCURES| Contract[Contract<br/>id, value, dates, status]
    Supplier[Supplier<br/>name, address, contact] -->|SUPPLIES| Contract
    Contract -->|FOR_PRODUCT| Product[Product<br/>name, category, spec]
    Product -->|HAS_PRICE| Price[Price<br/>amount, currency, date]
    Supplier -->|HAS_CERT| Compliance[Compliance<br/>cert_type, issuer, valid_until]
    Contract -->|CONTAINS| Clause[Clause<br/>number, title, category]
    Clause -->|CREATES| Obligation[Obligation<br/>party, action, deadline]
    Contract -->|HAS_AMENDMENT| Amendment[Amendment<br/>version, effective_date]
    Document[Document<br/>id, title, type] -->|REFERENCES| Contract
    Document -->|MENTIONS| Supplier
    Clause -->|IN_DOCUMENT| Document
    
    style Contract fill:#4a90e2
    style Supplier fill:#50c878
    style Document fill:#9b59b6
```

### Node Types (9 Labels)

| Node Label | Properties | Count (Data) | Status |
|------------|-----------|--------------|--------|
| **Supplier** | name, id, address, contact, sector | 65,406 | Loaded from OCDS |
| **Buyer** | name, id, sector, location | 83,724 records | Loaded from OCDS |
| **Contract** | id, number, value, currency, start_date, end_date, status | Variable | Created during doc ingestion |
| **Product** | name, category, specification, cpv_code | 7 | Sample data |
| **Price** | amount, currency, unit, effective_date, valid_until | 18 | Sample data |
| **Compliance** | cert_type, issuer, issue_date, valid_until | 119 | Sample data |
| **Document** | id, title, filename, type, upload_date | 0 in production | Ready for upload |
| **Clause** | number, title, text, category, extracted_date | Extracted during parsing | Implementation ready |
| **Obligation** | party, action, deadline, penalty, status | Extracted from clauses | Implementation ready |

**Note on Node Counts:** Supplier and Buyer counts reflect OCDS procurement records loaded into the system. Contract, Clause, and Obligation nodes are created dynamically during document ingestion. Current production deployment has 0 user-uploaded documents.

### Relationship Types (11 Types)

- **PROCURES**: Buyer → Contract (who is procuring)
- **SUPPLIES**: Supplier → Contract (who is supplying)
- **FOR_PRODUCT**: Contract → Product (what is being procured)
- **HAS_PRICE**: Product → Price (pricing information)
- **HAS_CERT**: Supplier → Compliance (certifications held)
- **CONTAINS**: Contract → Clause (contract sections)
- **CREATES**: Clause → Obligation (obligations defined in clauses)
- **REFERENCES**: Document → Contract/Supplier/Product (document mentions)
- **MENTIONS**: Document → Entity (entity appears in document)
- **HAS_AMENDMENT**: Contract → Amendment (contract modifications)
- **IN_DOCUMENT**: Clause → Document (clause source provenance)

### Graph Construction Pipeline

1. **Entity Extraction** (during document ingestion):
   - Rule-based: Regex patterns for contract numbers, supplier names, dates, monetary values
   - Optional LLM: Structured extraction when configured
   
2. **Entity Normalization**:
   - Name cleaning (whitespace, case, punctuation)
   - Date parsing to ISO format
   - Currency normalization
   
3. **Entity Resolution**:
   - Fuzzy matching against existing supplier/product/contract records
   - Initials resolution (e.g., "FCA" → "Financial Conduct Authority")
   - Tenant vocabulary cache for fast lookups
   
4. **Relationship Extraction**:
   - Supplier-Contract links from document metadata
   - Product-Price links from pricing tables
   - Clause-Obligation links from contract sections
   - Document-Entity links from chunk mentions
   
5. **Graph Indexing**:
   - Nodes created with `tenant_id` for isolation
   - Nodes include `source_doc_id` for provenance
   - Temporal properties: `effective_date`, `valid_until`, `superseded_by`
   - All writes use Neo4j transactions (or SQLite graph store locally)

### GraphRAG Query Example

**Question:** *"Which suppliers have active ISO 27001 certificates and contracts with the Home Office?"*

**Step 1: Graph Traversal**
```cypher
MATCH (s:Supplier)-[:HAS_CERT]->(cert:Compliance {cert_type: 'ISO 27001'})
WHERE cert.valid_until > date()
MATCH (s)-[:SUPPLIES]->(c:Contract)<-[:PROCURES]-(b:Buyer {name: 'Home Office'})
WHERE c.status = 'active'
RETURN s.name, s.id, cert.valid_until, c.contract_number, c.value
```

**Step 2: Entity Expansion**
- Graph query returns: `[supplier_123, supplier_456]`
- Expand to related document IDs: `[doc_a, doc_b, doc_c]`

**Step 3: Vector Search**
- Dense retrieval filtered by: `supplier_id IN [supplier_123, supplier_456]`
- Query: "ISO 27001 certified suppliers Home Office contracts"
- Returns top-50 chunks mentioning these entities

**Step 4: Reranking**
- Cross-encoder reranks combined graph + vector results
- Keeps top-15 most relevant chunks

**Step 5: Answer Generation**
- Context includes: Graph data (supplier names, cert dates, contract numbers) + Document evidence (contract text, certificate mentions)
- LLM synthesizes answer with both graph facts and document quotes
- Verification binds claims to both graph properties and document citations

**Hybrid Execution Value:** GraphRAG provides **structured facts** (exact supplier IDs, cert expiry dates, contract numbers) that complement **unstructured evidence** (contract clauses, certificate descriptions). This prevents hallucination of entity names and ensures temporal accuracy.

---

## Model Context Protocol (MCP) Integration

**Implementation:** `backend/app/mcp_server/` (FastMCP server over stdio)

### MCP Server Architecture

```mermaid
graph LR
    Client[AI Assistant<br/>Claude Desktop, Cline] -->|stdio<br/>JSON-RPC| MCP[MCP Server<br/>FastMCP]
    MCP --> Guard[Tool Guard<br/>Authorization]
    Guard -->|Validates| Tenant[Tenant Context<br/>Principal]
    Tenant -->|Permissions| Tools[Tool Registry<br/>9 tools]
    Tools --> DocSvc[Document Service]
    Tools --> ProcSvc[Procurement Service]
    Tools --> GraphSvc[Graph Service]
    DocSvc --> DB[(Database)]
    ProcSvc --> DB
    GraphSvc --> Neo[(Neo4j)]
    Guard --> Audit[Audit Logger<br/>audit_logs table]
    
    style MCP fill:#f39c12
    style Guard fill:#e25050
    style Tools fill:#4a90e2
```

### Registered MCP Tools (9 Tools)

| Tool | Permission | Input | Output | Purpose |
|------|-----------|-------|--------|---------|
| **search_documents** | docs:read | `query: str, limit: int` | List of documents with id, title, filename, type, status | Full-text search across document titles and filenames |
| **get_document** | docs:read | `document_id: str` | Document metadata: id, title, filename, type, status, stage, version, dates, supplier_id, contract_id | Retrieve single document detail with all metadata |
| **search_contracts** | procurement:read | `query: str, limit: int` | List of contracts with number, title, supplier, value, dates | Search contracts by number or title |
| **get_supplier_profile** | procurement:read | `supplier_id: str` | Supplier record with name, address, contact, contracts[], document_count | Supplier detail with related contracts and doc counts |
| **get_contract_amendments** | procurement:read | `contract_id: str` | List of amendments with id, number, title, version, effective_date, status | Amendment history for a contract, newest first |
| **get_ingestion_status** | docs:read | `limit: int` | Recent ingestion jobs with id, document_id, document_title, status, stage, progress, attempts, error_message | Monitor document processing pipeline |
| **get_evaluation_metrics** | evaluation:read | `limit: int` | Completed evaluation runs with id, experiment, dataset, questions, metrics, finished_at | Retrieve benchmark results and metrics |
| **search_graph** | graph:read | `label: str, query: str, limit: int` | Graph nodes by label with key, properties | Find entities in knowledge graph (Supplier, Contract, Product, Price, Document, Compliance, Amendment) |
| **get_entity_neighbours** | graph:read | `label: str, key: str, max_hops: int, as_of: str` | Entity relationships with type, start, end, properties | Typed relationships around entity, supports temporal as_of queries |

**Allowed Graph Labels:** Supplier, Contract, Amendment, Product, Price, ComplianceCertificate, Document, Category (hardcoded whitelist prevents arbitrary label probing)

### Authorization & Security

**Tool Guard:** Every tool call passes through `ToolGuard` (`backend/app/mcp_server/guards.py`) which enforces:
- **Tenant Context**: All queries scoped to configured `MCP_TENANT_ID`
- **Principal Permissions**: Validates user has required permission (e.g., `docs:read`, `procurement:read`)
- **Timeout**: Configurable per-tool timeout (default: 30 seconds)
- **Rate Limiting**: Calls per minute limit (default: 60/min)
- **Audit Logging**: Every invocation logged to `audit_logs` table with timestamp, principal, tool name, inputs, outcome

**Tenant Binding:** MCP server is deployed per-tenant. Environment variables `MCP_TENANT_ID` and `MCP_USER_EMAIL` are set at deployment time, so no client can access another tenant's data.

### Usage Example (Claude Desktop)

**Configuration:** Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "epi-procurement": {
      "command": "python",
      "args": ["-m", "app.mcp_server"],
      "cwd": "/path/to/backend",
      "env": {
        "DATABASE_URL": "postgresql://...",
        "MCP_ENABLED": "true",
        "MCP_TENANT_ID": "tenant_acme",
        "MCP_USER_EMAIL": "tools@acme.com",
        "MCP_TENANT_DEFAULT_ROLE": "analyst"
      }
    }
  }
}
```

**Tool Invocation:**
```
User: "Which suppliers in the system have ISO 27001 certificates?"

Claude: Let me search the graph for suppliers with ISO 27001 certifications.
[Calls: search_graph(label="Supplier", query="ISO 27001", limit=10)]

MCP Response: {
  "label": "Supplier",
  "query": "ISO 27001",
  "items": [
    {"label": "Supplier", "key": "sup_123", "properties": {"name": "Acme Corp", "sector": "IT"}},
    {"label": "Supplier", "key": "sup_456", "properties": {"name": "Global Tech", "sector": "Services"}}
  ],
  "total": 2
}

Claude: I found 2 suppliers with ISO 27001 certifications:
1. Acme Corp (IT sector)
2. Global Tech (Services sector)

Would you like me to get more details about their contracts?
```

### MCP vs Direct API

| Aspect | MCP Tools | Direct API |
|--------|-----------|------------|
| **Transport** | stdio (JSON-RPC) | HTTP REST |
| **Authentication** | Environment-bound (single tenant/user) | JWT per request |
| **Use Case** | AI assistant integration | Web/mobile apps, integrations |
| **Write Operations** | None (read-only by design) | Full CRUD via API |
| **Tool Discovery** | MCP protocol (server advertises tools) | OpenAPI schema |
| **Audience** | Claude Desktop, Cline, MCP clients | Developers, custom apps |

---

## Document Intelligence Pipeline

**Implementation:** `backend/app/ingestion/pipeline.py` (IngestionPipeline), `backend/app/ingestion/parsers/` (format-specific parsers)

```mermaid
graph TD
    Upload[Document Upload<br/>POST /documents/upload] --> Validate[Validation<br/>Size, type, malware check]
    Validate --> Store[Object Storage<br/>S3/MinIO/local filesystem]
    Store --> Job[Create Ingestion Job<br/>Status: pending]
    Job --> Worker[Background Worker<br/>Picks up job]
    Worker --> Parse[Format Parser<br/>PDF/DOCX/XLSX/Image]
    Parse --> OCR[OCR if Scanned<br/>PaddleOCR]
    OCR --> Layout[Layout Analysis<br/>Tables, sections, headings]
    Layout --> Extract[Metadata Extraction<br/>Contract #, parties, dates, $]
    Extract --> Clause[Clause Detection<br/>Payment terms, obligations]
    Clause --> Chunk[Semantic Chunking<br/>320 tokens, 60 overlap]
    Chunk --> Enrich[Chunk Enrichment<br/>Prepend doc metadata]
    Enrich --> Embed[Embedding Generation<br/>bge-m3, batch=16]
    Embed --> VIndex[Vector Indexing<br/>Qdrant or local]
    Extract --> GIndex[Graph Indexing<br/>Neo4j entities + relationships]
    VIndex --> Complete[Job Status: completed<br/>Document status: indexed]
    GIndex --> Complete
    Complete --> Ready[Ready for Retrieval]
    
    style Parse fill:#4a90e2
    style Embed fill:#50c878
    style GIndex fill:#e25050
```

### Supported Formats & Parsers

| Format | Parser Library | Capabilities | Status |
|--------|---------------|--------------|--------|
| **PDF (native)** | PyMuPDF (fitz) | Text extraction, table detection, images, metadata | ✅ Implemented |
| **PDF (scanned)** | PyMuPDF + PaddleOCR | OCR text extraction, layout preservation, confidence scores | ✅ Implemented |
| **DOCX** | python-docx | Text, tables, headings, styles, document properties | ✅ Implemented |
| **XLSX** | openpyxl | Tables, formulas, named ranges, multi-sheet | ✅ Implemented |
| **JPG/PNG** | PaddleOCR | Text extraction from images, bounding boxes | ✅ Implemented |
| **HTML** | BeautifulSoup | Text, tables, structure (for OCDS tender notices) | ✅ Implemented |

### Chunking Strategy

**Configuration** (`backend/app/config/settings.py`):
- **Target tokens:** 320
- **Max tokens:** 700
- **Overlap tokens:** 60
- **Method:** Sentence-boundary-aware semantic chunking
- **Tokenizer:** tiktoken cl100k_base (GPT-4 tokenizer)

**Algorithm:**
1. Split document by sentence boundaries (nltk or spaCy)
2. Accumulate sentences until ~320 tokens
3. If next sentence would exceed 700 tokens, finalize chunk
4. Add 60-token overlap from end of previous chunk
5. Never split mid-sentence

**Chunk Enrichment:** Each chunk is prepended with document metadata to provide context:
```
Document: Master Services Agreement
Supplier: Acme Corporation
Contract Number: CNT-2025-001
Effective Date: 2025-01-15

[Chunk text starts here...]
```

This improves retrieval quality when user queries mention entity names or document types.

### Metadata Extraction

**Contract Metadata** (rule-based + optional LLM):
- Contract number, title
- Parties: buyer name, supplier name, addresses
- Financial: contract value, currency, payment terms
- Temporal: effective date, expiry date, renewal dates
- Classification: CPV codes, product categories, service types
- Compliance: Required certificates, insurance, regulations

**Clause Detection** (regex patterns + section analysis):
- **Payment Terms**: "Net 30", "Payment within X days", milestone payments
- **Delivery Schedules**: Delivery dates, shipment terms, Incoterms
- **Termination Clauses**: Termination for convenience, breach conditions, notice periods
- **Liability Limits**: Indemnification amounts, liability caps, force majeure
- **Intellectual Property**: IP ownership, licensing terms, confidentiality
- **Warranties**: Product warranties, service level agreements, guarantees

**Pricing Schedules** (table extraction):
- Unit prices per product/service
- Volume discounts and tiered pricing
- Price escalation clauses (CPI adjustments, fuel surcharges)
- Renewal pricing and options

### Ingestion Job Lifecycle

```python
class IngestionJob:
    status: str  # pending, processing, completed, failed
    stage: str   # parsing, ocr, chunking, embedding, indexing
    progress: float  # 0.0 to 1.0
    attempts: int  # Retry count
    error_message: str | None
    
    # Job leases for distributed workers
    lease_holder: str | None  # Worker ID
    leased_until: datetime | None
```

**Job Processing:**
1. Worker queries for `status=pending AND (leased_until IS NULL OR leased_until < now())`
2. Worker acquires lease by setting `lease_holder` and `leased_until` (120 seconds)
3. Worker updates `status=processing`, `stage=parsing`
4. Worker processes document step-by-step, updating `stage` and `progress`
5. On success: `status=completed`, release lease
6. On failure: `status=failed` if `attempts >= 3`, else retry with exponential backoff
7. Lease expires if worker crashes → another worker can pick up job

**Idempotency:** Each document has a `version` field. Re-indexing same document with same version skips duplicate work. Version changes (amendments) trigger new chunks with provenance links.

---

## Quality, Evaluation & Security

### Quality Metrics

**Retrieval Evaluation** (measured against 70 labeled questions):
- **Recall@K**: Proportion of queries where correct document appears in top-K results
- **Precision@K**: Proportion of top-K results that are correct (less relevant for recall-focused systems)
- **MRR (Mean Reciprocal Rank)**: Average of 1/rank where rank is position of first correct result
- **nDCG@K**: Normalized Discounted Cumulative Gain, rewards correct documents appearing earlier
- **Page Coverage**: When correct document is retrieved, whether correct page is included

**Answer Quality Evaluation** (measured against 78 answerable questions):
- **Answer Correctness**: Literal fact containment (expected_facts ⊆ generated_answer)
- **Fact Coverage**: Proportion of expected facts present in answer
- **Citation Precision**: Correct citations / total citations produced
- **Citation Recall**: Correct citations / expected citations from labels
- **Faithfulness**: Pipeline's self-reported evidence grounding score (0-1)
- **Unsupported Claim Rate**: Claims in answer without supporting evidence

**Refusal Quality** (measured against 39 unanswerable + 81 answerable questions):
- **Refusal Precision**: True negatives / (true negatives + false positives)
- **Refusal Recall**: Detected unanswerable / total unanswerable
- **Correct Refusal Accuracy**: (TP + TN) / Total questions

**System Performance**:
- **Latency**: p50, p95, p99, max response time (milliseconds)
- **Token Usage**: Prompt tokens, completion tokens per query
- **Cost**: Estimated cost per query (when using paid APIs)
- **Throughput**: Queries per second under load

### Evaluation Framework

**Golden Dataset:** `data/evaluation/benchmark_v3/questions.json`
- **120 questions** hand-crafted by engineering team
- **12 categories**: document_metadata, parties, dates_and_duration, payment_terms, pricing_schedules, clauses, amendments, obligations, supplier_buyer_relationships, graph_multi_hop, historical_temporal, unanswerable
- **Verification methods**: verbatim_page_text+raw_html (46), verbatim_page_text (20), corpus_absence (39), database_row (9), graph_store (6)
- **Labels**: Auto-verified by string matching (not human-adjudicated)
- **Corpus**: 20 real UK Find a Tender OCDS notices, 19 indexed, 655 chunks

**Experiment Tracking:**
- Evaluation runs stored in `evaluation_runs` table with full reproducibility
- Tracks: model, settings, dataset version, strategy, timestamps
- Individual question results stored in `evaluation_results` table
- Comparison tool: `/api/v1/evaluation/compare?run_ids=run1,run2`

**No Automated Regression:** EPI does not have automated baseline-vs-candidate regression testing. Developers manually run benchmarks and compare metrics. Future work: Automated regression with pass/fail thresholds.

### Security Implementation

**Authentication (JWT):**
- **Algorithm**: HS256 (symmetric signing)
- **Access Token**: 15-minute TTL, includes user_id, tenant_id, role, permissions
- **Refresh Token**: 7-day TTL, stored in httpOnly cookie (SameSite=Strict), single-use (revoked after refresh)
- **Password Hashing**: Argon2id with memory=65536, time=3, parallelism=4
- **Token Revocation**: Logout adds token to revocation store (Redis if configured, memory otherwise)

**Authorization (RBAC):**
- **Roles**: admin, analyst, viewer
- **Permissions**: resource:action format (e.g., `docs:read`, `docs:write`, `query:ask`, `admin:read`)
- **Permission Checks**: Every API endpoint decorated with `@require_permission("resource:action")`
- **Tenant Isolation**: All database queries include `WHERE tenant_id = :tenant_id`
- **Document-level Authorization**: Documents have `access_level` field, users have `readable_access_levels`

**Audit Logging:**
- **Events**: authentication (login, logout, refresh), document access (upload, view, delete), query execution, admin actions
- **Schema**: timestamp, tenant_id, user_id, action, resource_type, resource_id, outcome (success/failure), detail (JSON)
- **Storage**: `audit_logs` table (SQLite dev, PostgreSQL prod)
- **Not encrypted at rest**: Limitation—audit logs stored in plaintext in database

**API Security:**
- **CORS**: Whitelist of allowed origins (configurable via `CORS_ORIGINS`)
- **Request ID Tracing**: Every request assigned unique ID for log correlation
- **Rate Limiting**: Configured (20/min login, 60/min upload, 120/min query) but **not enforced in current deployment**
- **Input Validation**: Pydantic schemas validate all request bodies, query params
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries
- **Upload Security**: File type validation, size limits, malware scanning placeholder (not implemented)

**Data Security:**
- **Secrets**: Managed via environment variables, never committed to code
- **Object Storage**: S3/MinIO with bucket-level access control
- **TLS/HTTPS**: Required in production (not enforced in dev mode)
- **Database Encryption**: Not implemented (plaintext at rest)

**Security Limitations:**
- ❌ No multi-factor authentication (MFA)
- ❌ Rate limiting configured but not enforced
- ❌ Cypher injection protection incomplete (uses parameterization but lacks input sanitization for label/property names)
- ❌ Audit logs not encrypted at rest
- ❌ No secrets rotation automation
- ❌ Upload malware scanning not implemented (placeholder only)

---

## Technology Stack

### Backend (124 Python Files)

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Web Framework** | FastAPI | 0.141+ | REST API, WebSocket, SSE streaming, OpenAPI docs |
| **Agent Orchestration** | LangGraph | 0.2+ | StateGraph for multi-step reasoning |
| **LLM Integration** | LangChain Core | 0.3+ | Prompt templates, message formatting |
| **Database** | SQLAlchemy (async) | 2.0.35+ | ORM with asyncio support |
| **DB Drivers** | asyncpg (PostgreSQL), aiosqlite (SQLite) | Latest | Async database drivers |
| **Migrations** | Alembic | 1.13+ | Schema versioning |
| **Vector Store** | Qdrant Client | 1.10+ | Dense retrieval (or local numpy index) |
| **Graph Database** | Neo4j Driver | 5.24+ | Property graph (or local SQLite graph) |
| **Cache** | Redis (async) | 5.0+ | Response caching (or in-memory) |
| **Object Storage** | boto3 (S3) | 1.34+ | Document storage (or local filesystem) |
| **Embeddings** | sentence-transformers | 3.0+ | BAAI/bge-m3 (1024-dim) |
| **Reranking** | sentence-transformers CrossEncoder | 3.0+ | bge-reranker-v2-m3 |
| **Sparse Retrieval** | rank-bm25 | 0.2.2+ | BM25 scoring algorithm |
| **PDF Parsing** | PyMuPDF (fitz) | 1.24+ | Text, tables, images extraction |
| **DOCX Parsing** | python-docx | 1.1+ | Word document processing |
| **XLSX Parsing** | openpyxl | 3.1+ | Excel spreadsheet processing |
| **OCR** | PaddleOCR | 2.7+ | Scanned document text extraction |
| **Authentication** | PyJWT | 2.15+ | JWT token generation/validation |
| **Password Hashing** | argon2-cffi | 23.1+ | Argon2id password hashing |
| **MCP Server** | mcp (FastMCP) | 1.21+ | Model Context Protocol server |
| **Logging** | structlog | 24.1+ | Structured JSON logging |

**Total Files:** 124 Python files in `backend/app/`

### Frontend

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Framework** | React | 18.3 | UI library with hooks |
| **Language** | TypeScript | 5.7 | Type safety and IDE support |
| **Build Tool** | Vite | 6.4 | Fast dev server, HMR, optimized bundling |
| **Routing** | react-router-dom | 6.30 | SPA routing with nested routes |
| **State Management** | Zustand | 5.0 | Lightweight global state |
| **Server State** | TanStack Query | 5.62 | Data fetching, caching, synchronization |
| **UI Components** | Radix UI | Various | Accessible headless components |
| **Styling** | Tailwind CSS | 3.4 | Utility-first CSS framework |
| **Icons** | lucide-react | 0.469 | Icon library |
| **Charts** | Recharts | 2.15 | Data visualization |
| **Form Validation** | Zod | Latest | Runtime type validation |
| **HTTP Client** | axios | Latest | API communication |
| **3D Graphics** | Three.js + React Three Fiber | Latest | Optional 3D globe visualization |

**Total Files:** 150+ TypeScript/TSX files in `frontend/src/`

---

## Local Development

### Prerequisites

- **Python 3.12+** (asyncio, type hints support)
- **Node.js 18+** (modern JavaScript features)
- **Docker & Docker Compose** (optional, for infrastructure services)
- **Git** (version control)

### Quick Start

**1. Clone repository:**
```bash
git clone https://github.com/Krish-afk-bot/enterprise-procurement-intelligence.git
cd enterprise-procurement-intelligence
```

**2. Backend setup:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
cp ../.env.example ../.env
# Edit .env: Set JWT_SECRET, configure providers
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**3. Frontend setup:**
```bash
cd frontend
npm install
npm run dev
```

**4. Access:**
- **Frontend:** http://localhost:5173
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/api/v1/health

### Docker Infrastructure (Optional)

```bash
docker compose up -d postgres qdrant neo4j redis minio
```

Starts supporting services. Configure backend `.env` to use them:
```bash
VECTOR_PROVIDER=qdrant
GRAPH_PROVIDER=neo4j
CACHE_PROVIDER=redis
STORAGE_PROVIDER=s3
```

### Environment Configuration

**Minimal Development** (all local providers):
```bash
# Security
JWT_SECRET=dev-insecure-change-me  # OK for local only

# Database
DATABASE_URL=sqlite+aiosqlite:///./var/epi.db

# Providers (all local, no external services)
VECTOR_PROVIDER=local
GRAPH_PROVIDER=local
CACHE_PROVIDER=memory
STORAGE_PROVIDER=local

# Optional: Connect to local Ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.1:8b

# Embeddings (downloads model on first use)
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DEVICE=auto  # Uses CUDA if available
```

**Production-Ready** (external providers):
```bash
# Security (REQUIRED)
JWT_SECRET=<48+ char random string>  # python -c "import secrets; print(secrets.token_urlsafe(48))"

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/epi

# Providers
VECTOR_PROVIDER=qdrant
QDRANT_URL=https://xyz.qdrant.io:6333
QDRANT_API_KEY=<key>

GRAPH_PROVIDER=neo4j
NEO4J_URI=bolt://neo4j.host:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<password>

CACHE_PROVIDER=redis
REDIS_URL=redis://redis.host:6379/0

STORAGE_PROVIDER=s3
S3_ENDPOINT=https://s3.amazonaws.com
S3_BUCKET=epi-documents
S3_ACCESS_KEY=<key>
S3_SECRET_KEY=<secret>
```

### Running Tests

```bash
cd backend
pytest                                    # All tests
pytest --cov=app --cov-report=html        # With coverage
pytest tests/integration/                 # Integration tests only
pytest -v -k "retrieval"                  # Specific pattern
pytest -m "not slow"                      # Skip slow tests
```

**Test Status:** 473/493 tests passing (96.0%), 13 failures (mock configuration), 7 skipped

**Test Structure:**
- `tests/unit/` - Unit tests (pure logic, no I/O)
- `tests/integration/` - Integration tests (database, APIs)
- `tests/ingestion/` - Document processing tests
- `tests/reliability/` - Failure injection, job leases
- `tests/security/` - Auth, RBAC, tenant isolation

---

## Deployment

### Current Production Deployment

**Frontend (Vercel):**
- **URL:** https://enterprise-procurement-intelligence-n04pc4po3.vercel.app
- **Deployment:** Automatic on git push to master
- **Configuration:** `frontend/vercel.json`

**Backend (Render.com):**
- **URL:** https://enterprise-procurement-intelligence.onrender.com
- **API Docs:** https://enterprise-procurement-intelligence.onrender.com/docs
- **Configuration:** `render.yaml`
- **Services:** Web service only (no background worker deployed)

**Deployed Infrastructure:**
- **Database:** SQLite (local file in Render persistent disk)
- **Vector Store:** Local numpy index (in-memory)
- **Graph Store:** Local SQLite graph (not Neo4j)
- **Cache:** In-memory (not Redis)
- **Object Storage:** Local filesystem (not S3)
- **LLM:** Not configured (extractive mode only)

**Implications:**
- ✅ Hosted UI accessible for demos
- ✅ API documentation browsable
- ⚠️ Local providers limit scalability (single instance, no horizontal scaling)
- ⚠️ No LLM configured → extractive answers only (returns evidence chunks, no generation)
- ⚠️ No background worker → document uploads queue but don't process automatically
- ⚠️ Persistent disk subject to Render's retention policy

### Deploying to Render (Production-Ready)

**1. Configure render.yaml:**
- Set `VECTOR_PROVIDER=qdrant`, configure Qdrant Cloud URL and API key
- Set `GRAPH_PROVIDER=neo4j`, configure Neo4j Aura credentials
- Set `CACHE_PROVIDER=redis`, configure Redis Cloud URL
- Set `STORAGE_PROVIDER=s3`, configure S3 bucket
- Set `LLM_BASE_URL` and `LLM_MODEL` for answer generation

**2. Create Render services:**
- **epi-api** (Web Service): Root Directory = `backend`, Dockerfile path = `./backend/Dockerfile`
- **epi-worker** (Background Worker): Root Directory = `backend`, Command = `python -m app.workers.ingestion_worker`

**3. Set environment variables:**
- Add to `epi-backend` env var group in Render dashboard
- All services inherit from group

**4. Deploy:**
- Push to master branch
- Render auto-deploys on push

### Docker Deployment

**Full Stack:**
```bash
docker compose up -d
docker compose logs -f api
```

**Production Dockerfile:**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY backend/pyproject.toml .
RUN pip install -e .
COPY backend/ .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$PORT"]
```

---

## Roadmap

### Completed ✓
- [x] Hybrid retrieval (dense + sparse + RRF)
- [x] Cross-encoder reranking
- [x] LangGraph 11-node agent pipeline with corrective loop
- [x] Evidence grounding and claim verification
- [x] MCP server with 9 tools
- [x] RBAC and tenant isolation
- [x] 120-question benchmark evaluation
- [x] Knowledge graph with 9 node types
- [x] Document ingestion (PDF, DOCX, XLSX, OCR)
- [x] Production deployment (Vercel + Render)

### In Progress 🔄
- [ ] Improving refusal precision (currently 42.9%, target 70%+)
- [ ] Answer correctness optimization (44.0% literal on the 150-question v4 set; 46.9% on the 120 v3 questions; target 60%+)
- [ ] Automated regression testing framework
- [ ] Query rewriting effectiveness (current implementation basic)

### Planned (Q1-Q2 2025) 📋
- [ ] Human evaluation of benchmark dataset
- [ ] Fine-tuned reranker for procurement domain
- [ ] Vision-language model integration (charts, diagrams, handwritten annotations)
- [ ] Bulk document upload with batch processing
- [ ] Advanced graph algorithms (PageRank, community detection, path scoring)
- [ ] Clause classification model (payment, liability, IP, termination)
- [ ] Export to Excel/PDF with evidence provenance
- [ ] Slack/Teams integration for conversational search

### Future (Q3-Q4 2025) 🔮
- [ ] Fine-tuned embedding model (domain-specific, trained on procurement corpus)
- [ ] Real-time document change detection and incremental reindexing
- [ ] Federated search across multiple tenants (with privacy controls)
- [ ] Mobile app (React Native)
- [ ] Advanced temporal reasoning (contract lifecycle, amendment chains)
- [ ] Supplier risk scoring (compliance history, contract performance)

---

## Contributing

Contributions welcome! Open an issue or pull request.

**Development Guidelines:**
- Follow PEP 8 (Python), ESLint rules (TypeScript)
- Add tests for new features (maintain 95%+ coverage)
- Update documentation (README, audit.md, docstrings)
- Use conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `perf:`, `chore:`

**Commit Examples:**
```bash
feat(agents): add clause extraction node to pipeline
fix(retrieval): correct RRF k parameter from 60 to 45
docs(readme): update MCP tool count to 9
test(ingestion): add PDF parsing failure recovery test
```

---

## License

**MIT License** - See [LICENSE](LICENSE) file.

**OCDS Data:** UK Find a Tender procurement data licensed under Open Data Commons Open Database License (ODbL). Attribution required when using.

---

## Support

**Documentation:**
- **Complete Audit:** [audit.md](audit.md) - 70+ API endpoints, architecture details
- **Deployment Guide:** `docs/deployment/` (if exists)
- **Testing Guide:** `docs/testing/` (if exists)

**Links:**
- **Repository:** https://github.com/Krish-afk-bot/enterprise-procurement-intelligence
- **Issues:** https://github.com/Krish-afk-bot/enterprise-procurement-intelligence/issues
- **API Docs:** https://enterprise-procurement-intelligence.onrender.com/docs

**Health Check:**
```bash
curl https://enterprise-procurement-intelligence.onrender.com/api/v1/health
```

---

**Built with FastAPI, LangGraph, React, Neo4j, and Qdrant. Powered by evidence, not hallucination.**
 EPI does not currently have automated baseline-vs-candidate regression testing. Benchmark runs are stored in `evaluation_runs` table for manual comparison via `/api/v1/evaluation/compare` endpoint.

---

## Knowledge Graph & GraphRAG

**Implementation:** `backend/app/graph/builder.py` (graph construction), `backend/app/providers/graph/` (Neo4j + SQLite providers)

### Graph Schema

```mermaid
graph LR
    Buyer[Buyer<br/>name, id, sector] -->|PROCURES| Contract[Contract<br/>id, value, dates, status]
    Supplier[Supplier<br/>name, address, contact] -->|SUPPLIES| Contract
    Contract -->|FOR_PRODUCT| Product[Product<br/>name, category, spec]
    Product -->|HAS_PRICE| Price[Price<br/>amount, currency, date]
    Supplier -->|HAS_CERT| Compliance[Compliance<br/>cert_type, issuer, valid_until]
    Contract -->|CONTAINS| Clause[Clause<br/>number, title, category]
    Clause -->|CREATES| Obligation[Obligation<br/>party, action, deadline]
    Contract -->|HAS_AMENDMENT| Amendment[Amendment<br/>version, effective_date]
    Document[Document<br/>id, title, type] -->|REFERENCES| Contract
    Document -->|MENTIONS| Supplier
    Clause -->|IN_DOCUMENT| Document
    
    style Contract fill:#4a90e2
    style Supplier fill:#50c878
    style Document fill:#9b59b6
```

### Node Types (9 Labels)

| Node Label | Properties | Count (Data) | Status |
|------------|-----------|--------------|--------|
| **Supplier** | name, id, address, contact, sector | 65,406 | Loaded from OCDS |
| **Buyer** | name, id, sector, location | 83,724 records | Loaded from OCDS |
| **Contract** | id, number, value, currency, start_date, end_date, status | Variable | Created during doc ingestion |
| **Product** | name, category, specification, cpv_code | 7 | Sample data |
| **Price** | amount, currency, unit, effective_date, valid_until | 18 | Sample data |
| **Compliance** | cert_type, issuer, issue_date, valid_until | 119 | Sample data |
| **Document** | id, title, filename, type, upload_date | 0 in production | Ready for upload |
| **Clause** | number, title, text, category, extracted_date | Extracted during parsing | Implementation ready |
| **Obligation** | party, action, deadline, penalty, status | Extracted from clauses | Implementation ready |

**Note on Node Counts:** Supplier and Buyer counts reflect OCDS procurement records loaded into the system. Contract, Clause, and Obligation nodes are created dynamically during document ingestion. Current production deployment has 0 user-uploaded documents.

### Relationship Types (11 Types)

- **PROCURES**: Buyer → Contract (who is procuring)
- **SUPPLIES**: Supplier → Contract (who is supplying)
- **FOR_PRODUCT**: Contract → Product (what is being procured)
- **HAS_PRICE**: Product → Price (pricing information)
- **HAS_CERT**: Supplier → Compliance (certifications held)
- **CONTAINS**: Contract → Clause (contract sections)
- **CREATES**: Clause → Obligation (obligations defined in clauses)
- **REFERENCES**: Document → Contract/Supplier/Product (document mentions)
- **MENTIONS**: Document → Entity (entity appears in document)
- **HAS_AMENDMENT**: Contract → Amendment (contract modifications)
- **IN_DOCUMENT**: Clause → Document (clause source provenance)

### Graph Construction Pipeline

1. **Entity Extraction** (during document ingestion):
   - Rule-based: Regex patterns for contract numbers, supplier names, dates, monetary values
   - Optional LLM: Structured extraction when configured
   
2. **Entity Normalization**:
   - Name cleaning (whitespace, case, punctuation)
   - Date parsing to ISO format
   - Currency normalization
   
3. **Entity Resolution**:
   - Fuzzy matching against existing supplier/product/contract records
   - Initials resolution (e.g., "FCA" → "Financial Conduct Authority")
   - Tenant vocabulary cache for fast lookups
   
4. **Relationship Extraction**:
   - Supplier-Contract links from document metadata
   - Product-Price links from pricing tables
   - Clause-Obligation links from contract sections
   - Document-Entity links from chunk mentions
   
5. **Graph Indexing**:
   - Nodes created with `tenant_id` for isolation
   - Nodes include `source_doc_id` for provenance
   - Temporal properties: `effective_date`, `valid_until`, `superseded_by`
   - All writes use Neo4j transactions (or SQLite graph store locally)

### GraphRAG Query Example

**Question:** *"Which suppliers have active ISO 27001 certificates and contracts with the Home Office?"*

**Step 1: Graph Traversal**
```cypher
MATCH (s:Supplier)-[:HAS_CERT]->(cert:Compliance {cert_type: 'ISO 27001'})
WHERE cert.valid_until > date()
MATCH (s)-[:SUPPLIES]->(c:Contract)<-[:PROCURES]-(b:Buyer {name: 'Home Office'})
WHERE c.status = 'active'
RETURN s.name, s.id, cert.valid_until, c.contract_number, c.value
```

**Step 2: Entity Expansion**
- Graph query returns: `[supplier_123, supplier_456]`
- Expand to related document IDs: `[doc_a, doc_b, doc_c]`

**Step 3: Vector Search**
- Dense retrieval filtered by: `supplier_id IN [supplier_123, supplier_456]`
- Query: "ISO 27001 certified suppliers Home Office contracts"
- Returns top-50 chunks mentioning these entities

**Step 4: Reranking**
- Cross-encoder reranks combined graph + vector results
- Keeps top-15 most relevant chunks

**Step 5: Answer Generation**
- Context includes: Graph data (supplier names, cert dates, contract numbers) + Document evidence (contract text, certificate mentions)
- LLM synthesizes answer with both graph facts and document quotes
- Verification binds claims to both graph properties and document citations

**Hybrid Execution Value:** GraphRAG provides **structured facts** (exact supplier IDs, cert expiry dates, contract numbers) that complement **unstructured evidence** (contract clauses, certificate descriptions). This prevents hallucination of entity names and ensures temporal accuracy.

---

## Model Context Protocol (MCP) Integration

**Implementation:** `backend/app/mcp_server/` (FastMCP server over stdio)

### MCP Server Architecture

```mermaid
graph LR
    Client[AI Assistant<br/>Claude Desktop, Cline] -->|stdio<br/>JSON-RPC| MCP[MCP Server<br/>FastMCP]
    MCP --> Guard[Tool Guard<br/>Authorization]
    Guard -->|Validates| Tenant[Tenant Context<br/>Principal]
    Tenant -->|Permissions| Tools[Tool Registry<br/>9 tools]
    Tools --> DocSvc[Document Service]
    Tools --> ProcSvc[Procurement Service]
    Tools --> GraphSvc[Graph Service]
    DocSvc --> DB[(Database)]
    ProcSvc --> DB
    GraphSvc --> Neo[(Neo4j)]
    Guard --> Audit[Audit Logger<br/>audit_logs table]
    
    style MCP fill:#f39c12
    style Guard fill:#e25050
    style Tools fill:#4a90e2
```

### Registered MCP Tools (9 Tools)

| Tool | Permission | Input | Output | Purpose |
|------|-----------|-------|--------|---------|
| **search_documents** | docs:read | `query: str, limit: int` | List of documents with id, title, filename, type, status | Full-text search across document titles and filenames |
| **get_document** | docs:read | `document_id: str` | Document metadata: id, title, filename, type, status, stage, version, dates, supplier_id, contract_id | Retrieve single document detail with all metadata |
| **search_contracts** | procurement:read | `query: str, limit: int` | List of contracts with number, title, supplier, value, dates | Search contracts by number or title |
| **get_supplier_profile** | procurement:read | `supplier_id: str` | Supplier record with name, address, contact, contracts[], document_count | Supplier detail with related contracts and doc counts |
| **get_contract_amendments** | procurement:read | `contract_id: str` | List of amendments with id, number, title, version, effective_date, status | Amendment history for a contract, newest first |
| **get_ingestion_status** | docs:read | `limit: int` | Recent ingestion jobs with id, document_id, document_title, status, stage, progress, attempts, error_message | Monitor document processing pipeline |
| **get_evaluation_metrics** | evaluation:read | `limit: int` | Completed evaluation runs with id, experiment, dataset, questions, metrics, finished_at | Retrieve benchmark results and metrics |
| **search_graph** | graph:read | `label: str, query: str, limit: int` | Graph nodes by label with key, properties | Find entities in knowledge graph (Supplier, Contract, Product, Price, Document, Compliance, Amendment) |
| **get_entity_neighbours** | graph:read | `label: str, key: str, max_hops: int, as_of: str` | Entity relationships with type, start, end, properties | Typed relationships around entity, supports temporal as_of queries |

**Allowed Graph Labels:** Supplier, Contract, Amendment, Product, Price, ComplianceCertificate, Document, Category (hardcoded whitelist prevents arbitrary label probing)

### Authorization & Security

**Tool Guard:** Every tool call passes through `ToolGuard` (`backend/app/mcp_server/guards.py`) which enforces:
- **Tenant Context**: All queries scoped to configured `MCP_TENANT_ID`
- **Principal Permissions**: Validates user has required permission (e.g., `docs:read`, `procurement:read`)
- **Timeout**: Configurable per-tool timeout (default: 30 seconds)
- **Rate Limiting**: Calls per minute limit (default: 60/min)
- **Audit Logging**: Every invocation logged to `audit_logs` table with timestamp, principal, tool name, inputs, outcome

**Tenant Binding:** MCP server is deployed per-tenant. Environment variables `MCP_TENANT_ID` and `MCP_USER_EMAIL` are set at deployment time, so no client can access another tenant's data.

### Usage Example (Claude Desktop)

**Configuration:** Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "epi-procurement": {
      "command": "python",
      "args": ["-m", "app.mcp_server"],
      "cwd": "/path/to/backend",
      "env": {
        "DATABASE_URL": "postgresql://...",
        "MCP_ENABLED": "true",
        "MCP_TENANT_ID": "tenant_acme",
        "MCP_USER_EMAIL": "tools@acme.com",
        "MCP_TENANT_DEFAULT_ROLE": "analyst"
      }
    }
  }
}
```

**Tool Invocation:**
```
User: "Which suppliers in the system have ISO 27001 certificates?"

Claude: Let me search the graph for suppliers with ISO 27001 certifications.
[Calls: search_graph(label="Supplier", query="ISO 27001", limit=10)]

MCP Response: {
  "label": "Supplier",
  "query": "ISO 27001",
  "items": [
    {"label": "Supplier", "key": "sup_123", "properties": {"name": "Acme Corp", "sector": "IT"}},
    {"label": "Supplier", "key": "sup_456", "properties": {"name": "Global Tech", "sector": "Services"}}
  ],
  "total": 2
}

Claude: I found 2 suppliers with ISO 27001 certifications:
1. Acme Corp (IT sector)
2. Global Tech (Services sector)

Would you like me to get more details about their contracts?
```

### MCP vs Direct API

| Aspect | MCP Tools | Direct API |
|--------|-----------|------------|
| **Transport** | stdio (JSON-RPC) | HTTP REST |
| **Authentication** | Environment-bound (single tenant/user) | JWT per request |
| **Use Case** | AI assistant integration | Web/mobile apps, integrations |
| **Write Operations** | None (read-only by design) | Full CRUD via API |
| **Tool Discovery** | MCP protocol (server advertises tools) | OpenAPI schema |
| **Audience** | Claude Desktop, Cline, MCP clients | Developers, custom apps |

---

## Document Intelligence Pipeline

**Implementation:** `backend/app/ingestion/pipeline.py` (IngestionPipeline), `backend/app/ingestion/parsers/` (format-specific parsers)

```mermaid
graph TD
    Upload[Document Upload<br/>POST /documents/upload] --> Validate[Validation<br/>Size, type, malware check]
    Validate --> Store[Object Storage<br/>S3/MinIO/local filesystem]
    Store --> Job[Create Ingestion Job<br/>Status: pending]
    Job --> Worker[Background Worker<br/>Picks up job]
    Worker --> Parse[Format Parser<br/>PDF/DOCX/XLSX/Image]
    Parse --> OCR[OCR if Scanned<br/>PaddleOCR]
    OCR --> Layout[Layout Analysis<br/>Tables, sections, headings]
    Layout --> Extract[Metadata Extraction<br/>Contract #, parties, dates, $]
    Extract --> Clause[Clause Detection<br/>Payment terms, obligations]
    Clause --> Chunk[Semantic Chunking<br/>320 tokens, 60 overlap]
    Chunk --> Enrich[Chunk Enrichment<br/>Prepend doc metadata]
    Enrich --> Embed[Embedding Generation<br/>bge-m3, batch=16]
    Embed --> VIndex[Vector Indexing<br/>Qdrant or local]
    Extract --> GIndex[Graph Indexing<br/>Neo4j entities + relationships]
    VIndex --> Complete[Job Status: completed<br/>Document status: indexed]
    GIndex --> Complete
    Complete --> Ready[Ready for Retrieval]
    
    style Parse fill:#4a90e2
    style Embed fill:#50c878
    style GIndex fill:#e25050
```

### Supported Formats & Parsers

| Format | Parser Library | Capabilities | Status |
|--------|---------------|--------------|--------|
| **PDF (native)** | PyMuPDF (fitz) | Text extraction, table detection, images, metadata | ✅ Implemented |
| **PDF (scanned)** | PyMuPDF + PaddleOCR | OCR text extraction, layout preservation, confidence scores | ✅ Implemented |
| **DOCX** | python-docx | Text, tables, headings, styles, document properties | ✅ Implemented |
| **XLSX** | openpyxl | Tables, formulas, named ranges, multi-sheet | ✅ Implemented |
| **JPG/PNG** | PaddleOCR | Text extraction from images, bounding boxes | ✅ Implemented |
| **HTML** | BeautifulSoup | Text, tables, structure (for OCDS tender notices) | ✅ Implemented |

### Chunking Strategy

**Configuration** (`backend/app/config/settings.py`):
- **Target tokens:** 320
- **Max tokens:** 700
- **Overlap tokens:** 60
- **Method:** Sentence-boundary-aware semantic chunking
- **Tokenizer:** tiktoken cl100k_base (GPT-4 tokenizer)

**Algorithm:**
1. Split document by sentence boundaries (nltk or spaCy)
2. Accumulate sentences until ~320 tokens
3. If next sentence would exceed 700 tokens, finalize chunk
4. Add 60-token overlap from end of previous chunk
5. Never split mid-sentence

**Chunk Enrichment:** Each chunk is prepended with document metadata to provide context:
```
Document: Master Services Agreement
Supplier: Acme Corporation
Contract Number: CNT-2025-001
Effective Date: 2025-01-15

[Chunk text starts here...]
```

This improves retrieval quality when user queries mention entity names or document types.

### Metadata Extraction

**Contract Metadata** (rule-based + optional LLM):
- Contract number, title
- Parties: buyer name, supplier name, addresses
- Financial: contract value, currency, payment terms
- Temporal: effective date, expiry date, renewal dates
- Classification: CPV codes, product categories, service types
- Compliance: Required certificates, insurance, regulations

**Clause Detection** (regex patterns + section analysis):
- **Payment Terms**: "Net 30", "Payment within X days", milestone payments
- **Delivery Schedules**: Delivery dates, shipment terms, Incoterms
- **Termination Clauses**: Termination for convenience, breach conditions, notice periods
- **Liability Limits**: Indemnification amounts, liability caps, force majeure
- **Intellectual Property**: IP ownership, licensing terms, confidentiality
- **Warranties**: Product warranties, service level agreements, guarantees

**Pricing Schedules** (table extraction):
- Unit prices per product/service
- Volume discounts and tiered pricing
- Price escalation clauses (CPI adjustments, fuel surcharges)
- Renewal pricing and options

### Ingestion Job Lifecycle

```python
class IngestionJob:
    status: str  # pending, processing, completed, failed
    stage: str   # parsing, ocr, chunking, embedding, indexing
    progress: float  # 0.0 to 1.0
    attempts: int  # Retry count
    error_message: str | None
    
    # Job leases for distributed workers
    lease_holder: str | None  # Worker ID
    leased_until: datetime | None
```

**Job Processing:**
1. Worker queries for `status=pending AND (leased_until IS NULL OR leased_until < now())`
2. Worker acquires lease by setting `lease_holder` and `leased_until` (120 seconds)
3. Worker updates `status=processing`, `stage=parsing`
4. Worker processes document step-by-step, updating `stage` and `progress`
5. On success: `status=completed`, release lease
6. On failure: `status=failed` if `attempts >= 3`, else retry with exponential backoff
7. Lease expires if worker crashes → another worker can pick up job

**Idempotency:** Each document has a `version` field. Re-indexing same document with same version skips duplicate work. Version changes (amendments) trigger new chunks with provenance links.

---

## Quality, Evaluation & Security

### Quality Metrics

**Retrieval Evaluation** (measured against 70 labeled questions):
- **Recall@K**: Proportion of queries where correct document appears in top-K results
- **Precision@K**: Proportion of top-K results that are correct (less relevant for recall-focused systems)
- **MRR (Mean Reciprocal Rank)**: Average of 1/rank where rank is position of first correct result
- **nDCG@K**: Normalized Discounted Cumulative Gain, rewards correct documents appearing earlier
- **Page Coverage**: When correct document is retrieved, whether correct page is included

**Answer Quality Evaluation** (measured against 78 answerable questions):
- **Answer Correctness**: Literal fact containment (expected_facts ⊆ generated_answer)
- **Fact Coverage**: Proportion of expected facts present in answer
- **Citation Precision**: Correct citations / total citations produced
- **Citation Recall**: Correct citations / expected citations from labels
- **Faithfulness**: Pipeline's self-reported evidence grounding score (0-1)
- **Unsupported Claim Rate**: Claims in answer without supporting evidence

**Refusal Quality** (measured against 39 unanswerable + 81 answerable questions):
- **Refusal Precision**: True negatives / (true negatives + false positives)
- **Refusal Recall**: Detected unanswerable / total unanswerable
- **Correct Refusal Accuracy**: (TP + TN) / Total questions

**System Performance**:
- **Latency**: p50, p95, p99, max response time (milliseconds)
- **Token Usage**: Prompt tokens, completion tokens per query
- **Cost**: Estimated cost per query (when using paid APIs)
- **Throughput**: Queries per second under load

### Evaluation Framework

**Golden Dataset:** `data/evaluation/benchmark_v3/questions.json`
- **120 questions** hand-crafted by engineering team
- **12 categories**: document_metadata, parties, dates_and_duration, payment_terms, pricing_schedules, clauses, amendments, obligations, supplier_buyer_relationships, graph_multi_hop, historical_temporal, unanswerable
- **Verification methods**: verbatim_page_text+raw_html (46), verbatim_page_text (20), corpus_absence (39), database_row (9), graph_store (6)
- **Labels**: Auto-verified by string matching (not human-adjudicated)
- **Corpus**: 20 real UK Find a Tender OCDS notices, 19 indexed, 655 chunks

**Experiment Tracking:**
- Evaluation runs stored in `evaluation_runs` table with full reproducibility
- Tracks: model, settings, dataset version, strategy, timestamps
- Individual question results stored in `evaluation_results` table
- Comparison tool: `/api/v1/evaluation/compare?run_ids=run1,run2`

**No Automated Regression:** EPI does not have automated baseline-vs-candidate regression testing. Developers manually run benchmarks and compare metrics. Future work: Automated regression with pass/fail thresholds.

### Security Implementation

**Authentication (JWT):**
- **Algorithm**: HS256 (symmetric signing)
- **Access Token**: 15-minute TTL, includes user_id, tenant_id, role, permissions
- **Refresh Token**: 7-day TTL, stored in httpOnly cookie (SameSite=Strict), single-use (revoked after refresh)
- **Password Hashing**: Argon2id with memory=65536, time=3, parallelism=4
- **Token Revocation**: Logout adds token to revocation store (Redis if configured, memory otherwise)

**Authorization (RBAC):**
- **Roles**: admin, analyst, viewer
- **Permissions**: resource:action format (e.g., `docs:read`, `docs:write`, `query:ask`, `admin:read`)
- **Permission Checks**: Every API endpoint decorated with `@require_permission("resource:action")`
- **Tenant Isolation**: All database queries include `WHERE tenant_id = :tenant_id`
- **Document-level Authorization**: Documents have `access_level` field, users have `readable_access_levels`

**Audit Logging:**
- **Events**: authentication (login, logout, refresh), document access (upload, view, delete), query execution, admin actions
- **Schema**: timestamp, tenant_id, user_id, action, resource_type, resource_id, outcome (success/failure), detail (JSON)
- **Storage**: `audit_logs` table (SQLite dev, PostgreSQL prod)
- **Not encrypted at rest**: Limitation—audit logs stored in plaintext in database

**API Security:**
- **CORS**: Whitelist of allowed origins (configurable via `CORS_ORIGINS`)
- **Request ID Tracing**: Every request assigned unique ID for log correlation
- **Rate Limiting**: Configured (20/min login, 60/min upload, 120/min query) but **not enforced in current deployment**
- **Input Validation**: Pydantic schemas validate all request bodies, query params
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries
- **Upload Security**: File type validation, size limits, malware scanning placeholder (not implemented)

**Data Security:**
- **Secrets**: Managed via environment variables, never committed to code
- **Object Storage**: S3/MinIO with bucket-level access control
- **TLS/HTTPS**: Required in production (not enforced in dev mode)
- **Database Encryption**: Not implemented (plaintext at rest)

**Security Limitations:**
- ❌ No multi-factor authentication (MFA)
- ❌ Rate limiting configured but not enforced
- ❌ Cypher injection protection incomplete (uses parameterization but lacks input sanitization for label/property names)
- ❌ Audit logs not encrypted at rest
- ❌ No secrets rotation automation
- ❌ Upload malware scanning not implemented (placeholder only)

---

## Technology Stack

### Backend (124 Python Files)

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Web Framework** | FastAPI | 0.141+ | REST API, WebSocket, SSE streaming, OpenAPI docs |
| **Agent Orchestration** | LangGraph | 0.2+ | StateGraph for multi-step reasoning |
| **LLM Integration** | LangChain Core | 0.3+ | Prompt templates, message formatting |
| **Database** | SQLAlchemy (async) | 2.0.35+ | ORM with asyncio support |
| **DB Drivers** | asyncpg (PostgreSQL), aiosqlite (SQLite) | Latest | Async database drivers |
| **Migrations** | Alembic | 1.13+ | Schema versioning |
| **Vector Store** | Qdrant Client | 1.10+ | Dense retrieval (or local numpy index) |
| **Graph Database** | Neo4j Driver | 5.24+ | Property graph (or local SQLite graph) |
| **Cache** | Redis (async) | 5.0+ | Response caching (or in-memory) |
| **Object Storage** | boto3 (S3) | 1.34+ | Document storage (or local filesystem) |
| **Embeddings** | sentence-transformers | 3.0+ | BAAI/bge-m3 (1024-dim) |
| **Reranking** | sentence-transformers CrossEncoder | 3.0+ | bge-reranker-v2-m3 |
| **Sparse Retrieval** | rank-bm25 | 0.2.2+ | BM25 scoring algorithm |
| **PDF Parsing** | PyMuPDF (fitz) | 1.24+ | Text, tables, images extraction |
| **DOCX Parsing** | python-docx | 1.1+ | Word document processing |
| **XLSX Parsing** | openpyxl | 3.1+ | Excel spreadsheet processing |
| **OCR** | PaddleOCR | 2.7+ | Scanned document text extraction |
| **Authentication** | PyJWT | 2.15+ | JWT token generation/validation |
| **Password Hashing** | argon2-cffi | 23.1+ | Argon2id password hashing |
| **MCP Server** | mcp (FastMCP) | 1.21+ | Model Context Protocol server |
| **Logging** | structlog | 24.1+ | Structured JSON logging |

**Total Files:** 124 Python files in `backend/app/`

### Frontend

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Framework** | React | 18.3 | UI library with hooks |
| **Language** | TypeScript | 5.7 | Type safety and IDE support |
| **Build Tool** | Vite | 6.4 | Fast dev server, HMR, optimized bundling |
| **Routing** | react-router-dom | 6.30 | SPA routing with nested routes |
| **State Management** | Zustand | 5.0 | Lightweight global state |
| **Server State** | TanStack Query | 5.62 | Data fetching, caching, synchronization |
| **UI Components** | Radix UI | Various | Accessible headless components |
| **Styling** | Tailwind CSS | 3.4 | Utility-first CSS framework |
| **Icons** | lucide-react | 0.469 | Icon library |
| **Charts** | Recharts | 2.15 | Data visualization |
| **Form Validation** | Zod | Latest | Runtime type validation |
| **HTTP Client** | axios | Latest | API communication |
| **3D Graphics** | Three.js + React Three Fiber | Latest | Optional 3D globe visualization |

**Total Files:** 150+ TypeScript/TSX files in `frontend/src/`

---

## Local Development

### Prerequisites

- **Python 3.12+** (asyncio, type hints support)
- **Node.js 18+** (modern JavaScript features)
- **Docker & Docker Compose** (optional, for infrastructure services)
- **Git** (version control)

### Quick Start

**1. Clone repository:**
```bash
git clone https://github.com/Krish-afk-bot/enterprise-procurement-intelligence.git
cd enterprise-procurement-intelligence
```

**2. Backend setup:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
cp ../.env.example ../.env
# Edit .env: Set JWT_SECRET, configure providers
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**3. Frontend setup:**
```bash
cd frontend
npm install
npm run dev
```

**4. Access:**
- **Frontend:** http://localhost:5173
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/api/v1/health

### Docker Infrastructure (Optional)

```bash
docker compose up -d postgres qdrant neo4j redis minio
```

Starts supporting services. Configure backend `.env` to use them:
```bash
VECTOR_PROVIDER=qdrant
GRAPH_PROVIDER=neo4j
CACHE_PROVIDER=redis
STORAGE_PROVIDER=s3
```

### Environment Configuration

**Minimal Development** (all local providers):
```bash
# Security
JWT_SECRET=dev-insecure-change-me  # OK for local only

# Database
DATABASE_URL=sqlite+aiosqlite:///./var/epi.db

# Providers (all local, no external services)
VECTOR_PROVIDER=local
GRAPH_PROVIDER=local
CACHE_PROVIDER=memory
STORAGE_PROVIDER=local

# Optional: Connect to local Ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.1:8b

# Embeddings (downloads model on first use)
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DEVICE=auto  # Uses CUDA if available
```

**Production-Ready** (external providers):
```bash
# Security (REQUIRED)
JWT_SECRET=<48+ char random string>  # python -c "import secrets; print(secrets.token_urlsafe(48))"

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/epi

# Providers
VECTOR_PROVIDER=qdrant
QDRANT_URL=https://xyz.qdrant.io:6333
QDRANT_API_KEY=<key>

GRAPH_PROVIDER=neo4j
NEO4J_URI=bolt://neo4j.host:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<password>

CACHE_PROVIDER=redis
REDIS_URL=redis://redis.host:6379/0

STORAGE_PROVIDER=s3
S3_ENDPOINT=https://s3.amazonaws.com
S3_BUCKET=epi-documents
S3_ACCESS_KEY=<key>
S3_SECRET_KEY=<secret>
```

### Running Tests

```bash
cd backend
pytest                                    # All tests
pytest --cov=app --cov-report=html        # With coverage
pytest tests/integration/                 # Integration tests only
pytest -v -k "retrieval"                  # Specific pattern
pytest -m "not slow"                      # Skip slow tests
```

**Test Status:** 473/493 tests passing (96.0%), 13 failures (mock configuration), 7 skipped

**Test Structure:**
- `tests/unit/` - Unit tests (pure logic, no I/O)
- `tests/integration/` - Integration tests (database, APIs)
- `tests/ingestion/` - Document processing tests
- `tests/reliability/` - Failure injection, job leases
- `tests/security/` - Auth, RBAC, tenant isolation

---

## Deployment

### Current Production Deployment

**Frontend (Vercel):**
- **URL:** https://enterprise-procurement-intelligence-n04pc4po3.vercel.app
- **Deployment:** Automatic on git push to master
- **Configuration:** `frontend/vercel.json`

**Backend (Render.com):**
- **URL:** https://enterprise-procurement-intelligence.onrender.com
- **API Docs:** https://enterprise-procurement-intelligence.onrender.com/docs
- **Configuration:** `render.yaml`
- **Services:** Web service only (no background worker deployed)

**Deployed Infrastructure:**
- **Database:** SQLite (local file in Render persistent disk)
- **Vector Store:** Local numpy index (in-memory)
- **Graph Store:** Local SQLite graph (not Neo4j)
- **Cache:** In-memory (not Redis)
- **Object Storage:** Local filesystem (not S3)
- **LLM:** Not configured (extractive mode only)

**Implications:**
- ✅ Hosted UI accessible for demos
- ✅ API documentation browsable
- ⚠️ Local providers limit scalability (single instance, no horizontal scaling)
- ⚠️ No LLM configured → extractive answers only (returns evidence chunks, no generation)
- ⚠️ No background worker → document uploads queue but don't process automatically
- ⚠️ Persistent disk subject to Render's retention policy

### Deploying to Render (Production-Ready)

**1. Configure render.yaml:**
- Set `VECTOR_PROVIDER=qdrant`, configure Qdrant Cloud URL and API key
- Set `GRAPH_PROVIDER=neo4j`, configure Neo4j Aura credentials
- Set `CACHE_PROVIDER=redis`, configure Redis Cloud URL
- Set `STORAGE_PROVIDER=s3`, configure S3 bucket
- Set `LLM_BASE_URL` and `LLM_MODEL` for answer generation

**2. Create Render services:**
- **epi-api** (Web Service): Root Directory = `backend`, Dockerfile path = `./backend/Dockerfile`
- **epi-worker** (Background Worker): Root Directory = `backend`, Command = `python -m app.workers.ingestion_worker`

**3. Set environment variables:**
- Add to `epi-backend` env var group in Render dashboard
- All services inherit from group

**4. Deploy:**
- Push to master branch
- Render auto-deploys on push

### Docker Deployment

**Full Stack:**
```bash
docker compose up -d
docker compose logs -f api
```

**Production Dockerfile:**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY backend/pyproject.toml .
RUN pip install -e .
COPY backend/ .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$PORT"]
```

---

## Roadmap

### Completed ✓
- [x] Hybrid retrieval (dense + sparse + RRF)
- [x] Cross-encoder reranking
- [x] LangGraph 11-node agent pipeline with corrective loop
- [x] Evidence grounding and claim verification
- [x] MCP server with 9 tools
- [x] RBAC and tenant isolation
- [x] 120-question benchmark evaluation
- [x] Knowledge graph with 9 node types
- [x] Document ingestion (PDF, DOCX, XLSX, OCR)
- [x] Production deployment (Vercel + Render)

### In Progress 🔄
- [ ] Improving refusal precision (currently 42.9%, target 70%+)
- [ ] Answer correctness optimization (44.0% literal on the 150-question v4 set; 46.9% on the 120 v3 questions; target 60%+)
- [ ] Automated regression testing framework
- [ ] Query rewriting effectiveness (current implementation basic)

### Planned (Q1-Q2 2025) 📋
- [ ] Human evaluation of benchmark dataset
- [ ] Fine-tuned reranker for procurement domain
- [ ] Vision-language model integration (charts, diagrams, handwritten annotations)
- [ ] Bulk document upload with batch processing
- [ ] Advanced graph algorithms (PageRank, community detection, path scoring)
- [ ] Clause classification model (payment, liability, IP, termination)
- [ ] Export to Excel/PDF with evidence provenance
- [ ] Slack/Teams integration for conversational search

### Future (Q3-Q4 2025) 🔮
- [ ] Fine-tuned embedding model (domain-specific, trained on procurement corpus)
- [ ] Real-time document change detection and incremental reindexing
- [ ] Federated search across multiple tenants (with privacy controls)
- [ ] Mobile app (React Native)
- [ ] Advanced temporal reasoning (contract lifecycle, amendment chains)
- [ ] Supplier risk scoring (compliance history, contract performance)

---

## Contributing

Contributions welcome! Open an issue or pull request.

**Development Guidelines:**
- Follow PEP 8 (Python), ESLint rules (TypeScript)
- Add tests for new features (maintain 95%+ coverage)
- Update documentation (README, audit.md, docstrings)
- Use conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `perf:`, `chore:`

**Commit Examples:**
```bash
feat(agents): add clause extraction node to pipeline
fix(retrieval): correct RRF k parameter from 60 to 45
docs(readme): update MCP tool count to 9
test(ingestion): add PDF parsing failure recovery test
```

---

## License

**MIT License** - See [LICENSE](LICENSE) file.

**OCDS Data:** UK Find a Tender procurement data licensed under Open Data Commons Open Database License (ODbL). Attribution required when using.

---

## Support

**Documentation:**
- **Complete Audit:** [audit.md](audit.md) - 70+ API endpoints, architecture details
- **Deployment Guide:** `docs/deployment/` (if exists)
- **Testing Guide:** `docs/testing/` (if exists)

**Links:**
- **Repository:** https://github.com/Krish-afk-bot/enterprise-procurement-intelligence
- **Issues:** https://github.com/Krish-afk-bot/enterprise-procurement-intelligence/issues
- **API Docs:** https://enterprise-procurement-intelligence.onrender.com/docs

**Health Check:**
```bash
curl https://enterprise-procurement-intelligence.onrender.com/api/v1/health
```

---

**Built with FastAPI, LangGraph, React, Neo4j, and Qdrant. Powered by evidence, not hallucination.**
