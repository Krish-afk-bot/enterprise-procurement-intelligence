# Enterprise Procurement Intelligence

**Procurement Intelligence. Powered by Evidence.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3-61DAFB.svg)](https://reactjs.org/)

> Multi-agent RAG platform for procurement intelligence with hybrid retrieval, knowledge graphs, and evidence grounding.

**Live Demo:** [enterprise-procurement-intelligence-n04pc4po3.vercel.app](https://enterprise-procurement-intelligence-n04pc4po3.vercel.app)  
**API:** [enterprise-procurement-intelligence.onrender.com](https://enterprise-procurement-intelligence.onrender.com)  
**Docs:** [/docs](https://enterprise-procurement-intelligence.onrender.com/docs)

---

## The Problem

Procurement data lives in fragmented silos—contracts in document management systems, supplier information in ERP databases, compliance certificates in email attachments, pricing schedules in spreadsheets. Traditional keyword search cannot answer questions like *"Which suppliers have active ISO 27001 certificates and pricing below market rate?"* because the evidence spans multiple sources and requires reasoning over relationships.

## The Solution

EPI is a graph-enhanced RAG platform that unifies documents, structured data, and entity relationships into a queryable intelligence layer. Every answer is grounded in source evidence with page-level citations. The system routes queries through specialized retrieval strategies—dense vectors for semantic similarity, BM25 for precise keyword matching, graph traversal for multi-hop entity relationships, and SQL for structured aggregations.

---

## Platform Capabilities

**Document Intelligence**
- Parse and index procurement documents (PDF, DOCX, XLSX, scanned images)
- OCR with PaddleOCR for text extraction from images
- Layout-aware parsing preserving tables, sections, and formatting
- Semantic chunking with 320-token targets and 60-token overlap
- Chunk enrichment with document metadata for improved context

**Retrieval Engineering**
- **Dense retrieval**: BAAI/bge-m3 embeddings (1024-dim) via sentence-transformers
- **Sparse retrieval**: BM25 keyword matching via rank-bm25
- **Cross-encoder reranking**: BAAI/bge-reranker-v2-m3 for precision
- **Reciprocal Rank Fusion**: Hybrid combination of dense and sparse results
- **Measured performance**: Recall@10: 86.8%, MRR: 0.802, nDCG@10: 0.819 (120-question benchmark)

**Knowledge Graph & GraphRAG**
- Neo4j property graph connecting suppliers, contracts, buyers, products, prices, compliance certificates, documents, clauses, and obligations
- Entity extraction and normalization during ingestion
- Multi-hop graph traversal for relationship queries
- Graph-enhanced retrieval combining vector search with entity expansion
- Provenance tracking for all extracted entities

**Multi-Agent Orchestration**
- LangGraph pipeline with query understanding, planning, parallel retrieval, evidence evaluation, generation, and verification nodes
- Intelligent task routing selecting optimal retrieval strategies per query type
- Evidence-grounded generation with claim-to-citation binding
- Confidence scoring and unsupported claim detection
- Extractive fallback when no LLM is configured

**Model Context Protocol (MCP)**
- MCP server exposing procurement intelligence tools
- Standard tool schemas for document search, contract retrieval, supplier lookup, and structured queries
- Authorization and tenant context enforcement
- Audit trail for all tool invocations

**Security & Multi-Tenancy**
- JWT-based authentication with access and refresh tokens
- Role-based access control (RBAC): admin, analyst, viewer
- Tenant isolation at database, vector, and graph layers
- Document-level authorization
- Audit logging with structured event capture

---

## Architecture

```mermaid
graph TB
    subgraph Frontend
        UI[React SPA<br/>TypeScript + Vite]
    end

    subgraph "API Layer"
        API[FastAPI REST API<br/>70+ endpoints]
        Auth[JWT Auth & RBAC]
        API --> Auth
    end

    subgraph "Agent Orchestration"
        LG[LangGraph Pipeline]
        Plan[Query Planning]
        Retrieve[Evidence Retrieval]
        Generate[Answer Generation]
        Verify[Grounding Verification]
        
        LG --> Plan --> Retrieve --> Generate --> Verify
    end

    subgraph "Retrieval Engine"
        Dense[Dense Search<br/>bge-m3 embeddings]
        Sparse[BM25 Sparse<br/>rank-bm25]
        Graph[Graph Traversal<br/>Cypher queries]
        SQL[Structured Queries<br/>PostgreSQL]
        Rerank[Cross-Encoder<br/>bge-reranker-v2-m3]
        
        Retrieve --> Dense
        Retrieve --> Sparse
        Retrieve --> Graph
        Retrieve --> SQL
        Dense --> Rerank
        Sparse --> Rerank
    end

    subgraph "Document Intelligence"
        Upload[Document Upload]
        Parse[Parser<br/>PDF/DOCX/XLSX/OCR]
        Chunk[Semantic Chunking]
        Embed[Embedding Generation]
        Index[Vector Indexing]
        
        Upload --> Parse --> Chunk --> Embed --> Index
    end

    subgraph "Storage Layer"
        PG[(PostgreSQL<br/>24 tables)]
        VDB[(Qdrant<br/>Vector Store)]
        Neo[(Neo4j<br/>Property Graph)]
        S3[(S3/MinIO<br/>Documents)]
        
        Index --> VDB
        Parse --> S3
        Generate --> PG
    end

    UI -.HTTP/SSE.-> API
    API --> LG
    Rerank --> Generate
    Parse --> Neo
    Chunk --> PG

    style LG fill:#4a90e2
    style Rerank fill:#50c878
    style Neo fill:#e25050
    style VDB fill:#9b59b6
```

---

## Intelligent Task Classification & Model Routing

EPI implements **task-aware routing** that selects retrieval strategies and model tiers based on query characteristics:

### Task Classification Pipeline

```mermaid
graph LR
    Query[User Query] --> Understand[Query Understanding]
    Understand --> Extract[Entity Extraction]
    Understand --> Intent[Intent Classification]
    Extract --> Plan[Query Planning]
    Intent --> Plan
    Plan --> Route{Task Router}
    
    Route -->|Factual Lookup| Dense[Dense Retrieval]
    Route -->|Precise Match| Sparse[BM25 Sparse]
    Route -->|Entity Relationship| Graph[Graph Traversal]
    Route -->|Aggregation| SQL[Structured Query]
    Route -->|Complex Reasoning| Multi[Multi-Strategy]
    
    style Route fill:#e25050
    style Plan fill:#4a90e2
```

### Supported Task Categories

| Task Type | Classification Signals | Retrieval Strategy | Example Query |
|-----------|----------------------|-------------------|---------------|
| **Factual Lookup** | Single entity, specific fact | Dense → Rerank | *"What is the contract value for supplier X?"* |
| **Document Search** | Document-level request | Dense + Sparse hybrid | *"Find contracts mentioning ISO 27001"* |
| **Entity Relationship** | Multiple entities, relationships | Graph traversal + Dense | *"Which suppliers have contracts with buyer Y?"* |
| **Temporal Query** | Date constraints, time ranges | Temporal filtering + Dense | *"Active contracts as of 2025-06-01"* |
| **Aggregation** | Counts, sums, averages | SQL structured query | *"Total contract value by supplier"* |
| **Multi-Hop Reasoning** | Chained relationships | Graph + Dense fusion | *"Suppliers with ISO cert AND pricing <£50k"* |
| **Clause Extraction** | Contract-specific sections | Sparse + Layout-aware | *"Payment terms in the Acme contract"* |
| **Unanswerable** | Insufficient evidence | Confidence threshold → Refusal | *"What is the CEO's favorite color?"* |

### Model Tier Selection

```python
# Task routing logic (app/providers/router.py)
def route(task: Task, complexity: str) -> RouteDecision:
    if complexity == "high":
        return RouteDecision(task, ENGINE_LLM, settings.llm_model)
    return RouteDecision(task, default_engine(task), default_model(task))
```

**Available Engines:**
- `ENGINE_LLM`: Full LLM generation (OpenAI-compatible endpoints, Ollama, etc.)
- `ENGINE_EXTRACTIVE`: Keyword-based extraction from top-ranked chunks
- `ENGINE_STRUCTURED`: SQL query execution for aggregations
- `ENGINE_VLM`: Vision-language model for image-based evidence (planned)

**Fallback Behavior:** If no LLM is configured, EPI falls back to extractive mode, returning evidence chunks with confidence scores rather than generated answers.

---

## Hybrid RAG & Retrieval Engineering

### Retrieval Flow

```mermaid
sequenceDiagram
    participant Query
    participant Plan as Query Planner
    participant Dense as Dense Search
    participant Sparse as BM25 Sparse
    participant Fusion as RRF Fusion
    participant Rerank as Cross-Encoder
    participant Context as Context Builder

    Query->>Plan: Analyze query
    Plan->>Dense: Retrieve top-50 (cosine)
    Plan->>Sparse: Retrieve top-50 (BM25)
    Dense-->>Fusion: 50 candidates
    Sparse-->>Fusion: 50 candidates
    Fusion->>Rerank: Fused candidates
    Rerank->>Context: Reranked top-15
    Context-->>Query: Top-12 chunks (6K tokens)
```

### Benchmark Results (120-Question Dataset)

**Retrieval Quality** (70 answerable questions with known documents):

| Metric | Score | Notes |
|--------|-------|-------|
| **Recall@5** | 86.8% | Correct document in top-5: 59/68 queries |
| **Recall@10** | 86.8% | Correct document in top-10: 59/68 queries |
| **MRR** | 0.802 | Mean Reciprocal Rank |
| **nDCG@10** | 0.819 | Normalized Discounted Cumulative Gain |
| **Page Coverage** | 93.8% | Correct page retrieved when document found |

**Answer Quality** (78 answerable questions):

| Metric | Score | Notes |
|--------|-------|-------|
| **Answer Correctness** | 39.7% | Literal fact containment (strict) |
| **Citation Precision** | 77.4% | Correct citations / total citations |
| **Citation Recall** | 55.9% | Correct citations / expected citations |
| **Faithfulness** | 69.4% | Self-reported grounding (not independent judge) |
| **Unsupported Claim Rate** | 30.6% | Claims without evidence support |

**Refusal Behavior** (39 unanswerable questions):

| Metric | Score | Notes |
|--------|-------|-------|
| **Refusal Precision** | 42.9% | True negatives / (TP + FP) |
| **Refusal Recall** | 76.9% | Detected unanswerable / total unanswerable |
| **Correct Refusal Accuracy** | 58.1% | Overall refusal decision correctness |

**Performance:**

| Metric | Value |
|--------|-------|
| **Latency (p50)** | 9.2s |
| **Latency (p95)** | 16.3s |
| **Latency (max)** | 32.2s |
| **Tokens (prompt mean)** | 1,675 |
| **Tokens (completion mean)** | 61 |

**Evaluation Configuration:**
- **Dataset:** 120 questions (66 answerable, 39 unanswerable, 15 needs review)
- **Model:** qwen2.5-coder:7b (local Ollama)
- **Embeddings:** BAAI/bge-small-en-v1.5
- **Reranker:** bge-reranker-v2-m3 (cross-encoder)
- **Top-K:** Dense 50, Sparse 50, Rerank 15, Context 12
- **Benchmark Date:** 2026-11-12
- **Source:** `data/evaluation/benchmark_v3/results/baseline/`

**Limitations of Current Benchmark:**
- Labels are auto-verified by string matching, not human-adjudicated
- Answer correctness uses literal fact containment (correct paraphrases scored as misses)
- Faithfulness is self-reported by the pipeline, not an independent evaluator
- Refusal failure rate is high (49/120) due to overly defensive thresholds
- Small corpus (20 documents, 655 chunks) limits generalization

---

## Knowledge Graph & GraphRAG

### Graph Schema

```mermaid
graph LR
    Buyer[Buyer] -->|PROCURES| Contract[Contract]
    Supplier[Supplier] -->|SUPPLIES| Contract
    Contract -->|CONTAINS| Clause[Clause]
    Clause -->|CREATES| Obligation[Obligation]
    Contract -->|HAS_AMENDMENT| Amendment[Amendment]
    Contract -->|FOR_PRODUCT| Product[Product]
    Product -->|HAS_PRICE| Price[Price]
    Supplier -->|HAS_CERT| Compliance[Compliance Cert]
    Document[Document] -->|REFERENCES| Contract
    Document -->|MENTIONS| Supplier
    Clause -->|IN_DOCUMENT| Document
    
    style Contract fill:#4a90e2
    style Supplier fill:#50c878
    style Document fill:#9b59b6
```

### Node Types

| Node Label | Properties | Count (Sample) |
|------------|-----------|----------------|
| `Supplier` | name, id, address, contact | 65,402 |
| `Buyer` | name, id, sector | 83,724 records |
| `Contract` | id, value, start_date, end_date, status | Ingested from docs |
| `Product` | name, category, specification | 7 |
| `Price` | amount, currency, unit, effective_date | 18 |
| `Compliance` | cert_type, issuer, valid_until | 119 |
| `Document` | id, title, type, upload_date | Ready for production |
| `Clause` | number, title, text, category | Extracted during parsing |
| `Obligation` | party, action, deadline, penalty | Extracted from clauses |

### Relationship Types

- `PROCURES`: Buyer → Contract
- `SUPPLIES`: Supplier → Contract
- `FOR_PRODUCT`: Contract → Product
- `HAS_PRICE`: Product → Price
- `HAS_CERT`: Supplier → Compliance
- `CONTAINS`: Contract → Clause
- `CREATES`: Clause → Obligation
- `REFERENCES`: Document → Contract/Supplier/Product
- `MENTIONS`: Document → Entity
- `HAS_AMENDMENT`: Contract → Amendment

### GraphRAG Query Example

**Question:** *"Which suppliers have ISO 27001 certificates and active contracts?"*

**Cypher Query:**
```cypher
MATCH (s:Supplier)-[:HAS_CERT]->(cert:Compliance {cert_type: 'ISO 27001'})
WHERE cert.valid_until > date()
MATCH (s)-[:SUPPLIES]->(c:Contract)
WHERE c.status = 'active'
RETURN s.name, cert.valid_until, c.id, c.value
```

**Hybrid Execution:**
1. Graph traversal returns entity IDs: `[supplier_123, supplier_456]`
2. Vector search retrieves relevant chunks mentioning these entities
3. Reranker combines graph context with document evidence
4. Answer generator produces grounded response with citations

**Graph Construction:** Entities and relationships are extracted during document ingestion using rule-based parsers and optional LLM extraction. All graph nodes include `tenant_id` for isolation and `source_doc_id` for provenance.

---

## MCP Integration

EPI exposes a **Model Context Protocol (MCP) server** at `backend/app/mcp_server/`, allowing AI assistants (Claude Desktop, Cline, etc.) to invoke procurement intelligence tools.

### Registered Tools

| Tool | Purpose | Input | Output |
|------|---------|-------|--------|
| `search_documents` | Full-text document search | `query: str, limit: int` | List of documents with excerpts |
| `get_document` | Retrieve single document | `document_id: str` | Document detail with pages and metadata |
| `search_contracts` | Contract search and filtering | `query: str, limit: int` | List of contracts with suppliers and values |

### MCP Server Architecture

```mermaid
graph LR
    Client[AI Assistant] -->|stdio| MCP[MCP Server]
    MCP -->|Authorization| Auth[Tenant Context]
    Auth -->|Validated Request| Tools[Tool Registry]
    Tools -->|search_documents| DocService[Document Service]
    Tools -->|get_document| DocService
    Tools -->|search_contracts| ProcService[Procurement Service]
    DocService --> DB[(Database)]
    ProcService --> DB
    
    style MCP fill:#e25050
    style Auth fill:#f39c12
```

**Authorization:** Every tool invocation includes a `Principal` with tenant context and permissions. Tools validate `docs:read` or `procurement:read` permissions before execution.

**Audit Trail:** All tool calls are logged to `audit_logs` table with timestamp, principal, tool name, inputs, and outcomes.

**Usage Example (Claude Desktop):**
```json
{
  "mcpServers": {
    "epi": {
      "command": "python",
      "args": ["-m", "app.mcp_server"],
      "cwd": "/path/to/backend",
      "env": {
        "DATABASE_URL": "postgresql://...",
        "MCP_TENANT_ID": "tenant_abc123"
      }
    }
  }
}
```

---

## Document Intelligence Pipeline

```mermaid
graph TD
    Upload[Document Upload] --> Validate[Validation<br/>Size, Type, Malware]
    Validate --> Store[S3/MinIO Storage]
    Store --> Parse[Parser Selection<br/>PDF, DOCX, XLSX, Image]
    Parse --> OCR[OCR if Scanned<br/>PaddleOCR]
    OCR --> Layout[Layout Analysis<br/>Tables, Sections]
    Layout --> Extract[Metadata Extraction<br/>Supplier, Date, Value]
    Extract --> Chunk[Semantic Chunking<br/>320 tokens, 60 overlap]
    Chunk --> Enrich[Chunk Enrichment<br/>Prepend doc metadata]
    Enrich --> Embed[Embedding Generation<br/>BAAI/bge-m3]
    Embed --> VecIndex[Vector Indexing<br/>Qdrant]
    Extract --> GraphIndex[Graph Indexing<br/>Neo4j entities]
    VecIndex --> Ready[Ready for Retrieval]
    GraphIndex --> Ready
    
    style Parse fill:#4a90e2
    style Embed fill:#50c878
    style GraphIndex fill:#e25050
```

### Supported Formats

| Format | Parser | Capabilities |
|--------|--------|-------------|
| **PDF** | PyMuPDF | Text, tables, images, metadata |
| **PDF (scanned)** | PyMuPDF + PaddleOCR | OCR text extraction, layout preservation |
| **DOCX** | python-docx | Text, tables, headings, styles |
| **XLSX** | openpyxl | Tables, formulas, named ranges |
| **Images** | PaddleOCR | Text extraction from JPG, PNG |

### Chunking Strategy

- **Target:** 320 tokens per chunk
- **Max:** 700 tokens
- **Overlap:** 60 tokens
- **Method:** Sentence-boundary-aware semantic chunking
- **Enrichment:** Prepends document metadata (title, supplier, date) to each chunk for context

### Metadata Extraction

**Contract Metadata:**
- Contract number, title, parties (buyer, supplier)
- Contract value, currency, effective dates
- Product/service categories, CPV codes
- Compliance requirements, certificate references

**Clause Detection:**
- Payment terms, delivery schedules, termination clauses
- Liability limits, warranties, indemnification
- Intellectual property rights, confidentiality obligations

**Pricing Schedules:**
- Unit prices, quantity discounts, price escalation clauses
- Renewal pricing, tiered pricing structures

---

## Quality, Evaluation & Security

### Quality Metrics (Measured)

**Retrieval Metrics:**
- Recall@K: Proportion of queries where correct document appears in top-K
- Precision@K: Proportion of top-K results that are correct
- MRR (Mean Reciprocal Rank): Average 1/rank of first correct result
- nDCG (Normalized Discounted Cumulative Gain): Ranking quality with position discount

**Answer Metrics:**
- Answer Correctness: Literal fact containment (strict matching)
- Citation Precision: Correct citations / total citations
- Citation Recall: Correct citations / expected citations
- Faithfulness: Self-reported evidence grounding
- Unsupported Claim Rate: Generated claims without evidence support

**System Metrics:**
- Latency: p50, p95, max response times
- Token Usage: Prompt and completion token counts
- Cost: Estimated cost per query (when using paid APIs)

### Evaluation Framework

**Golden Dataset:** 120 hand-crafted questions across 12 categories (document_metadata, parties, dates_and_duration, payment_terms, pricing_schedules, clauses, amendments, obligations, supplier_buyer_relationships, graph_multi_hop, historical_temporal, unanswerable)

**Verification Methods:**
- `verbatim_page_text+raw_html`: Evidence quote matched in stored page text and original HTML
- `database_row`: Answer verified against structured database record
- `graph_store`: Answer verified via Cypher query result
- `corpus_absence`: Unanswerable question with no evidence in corpus

**Experiment Tracking:** Evaluation runs stored in `evaluation_runs` and `evaluation_results` tables with full reproducibility (model, settings, dataset version, timestamps)

**Comparison Tool:** API endpoint `/api/v1/evaluation/compare?run_ids=run1,run2` generates side-by-side metric comparison

### Security (Implemented)

**Authentication:**
- JWT tokens with HS256 signing
- Access tokens: 15-minute TTL
- Refresh tokens: 7-day TTL, httpOnly cookies
- Argon2 password hashing

**Authorization:**
- Role-based access control (RBAC): admin, analyst, viewer
- Permission format: `resource:action` (e.g., `docs:write`, `query:ask`)
- Tenant isolation at database, vector store, and graph layers
- Document-level authorization checks

**Audit & Compliance:**
- Structured audit logging to `audit_logs` table
- Events: authentication, document access, query execution, admin actions
- Immutable audit trail with timestamps, principals, resources, outcomes

**API Security:**
- CORS whitelist (configurable origins)
- Request ID tracing for all endpoints
- Rate limiting configuration (not enforced in current deployment)
- Input validation via Pydantic schemas

**Data Security:**
- Secrets managed via environment variables
- No credentials in source code or logs
- S3/MinIO object storage with access control
- TLS/HTTPS required in production (not enforced in dev)

**Limitations:**
- No multi-factor authentication (MFA)
- Rate limiting configured but not enforced
- Cypher injection protection not implemented (graph queries use parameterization but lack input sanitization)
- Audit logs not encrypted at rest

---

## Technology Stack

### Backend (124 Python files)

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Web Framework** | FastAPI 0.141+ | REST API, WebSocket, SSE streaming |
| **Agent Orchestration** | LangGraph 0.2+ | Multi-step reasoning graph |
| **Database** | PostgreSQL + asyncpg / SQLite + aiosqlite | Transactional data, async ORM |
| **Migrations** | Alembic 1.13+ | Schema versioning |
| **Vector Store** | Qdrant 1.10+ | Dense retrieval |
| **Graph Database** | Neo4j 5.24+ | Entity relationships |
| **Cache** | Redis 5.0+ | Response caching |
| **Object Storage** | MinIO / S3 | Document storage |
| **Embeddings** | sentence-transformers 3.0+ | BAAI/bge-m3 (1024-dim) |
| **Reranker** | sentence-transformers CrossEncoder | bge-reranker-v2-m3 |
| **Sparse Retrieval** | rank-bm25 0.2.2+ | BM25 scoring |
| **PDF Parsing** | PyMuPDF 1.24+ | Text, tables, images |
| **OCR** | PaddleOCR 2.7+ | Scanned document text extraction |
| **Authentication** | PyJWT 2.15+, argon2-cffi 23.1+ | Token auth, password hashing |
| **Logging** | structlog 24.1+ | Structured logging |

### Frontend

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Framework** | React 18.3 | UI library |
| **Language** | TypeScript 5.7 | Type safety |
| **Build Tool** | Vite 6.4 | Fast dev server and bundling |
| **Routing** | react-router-dom 6.30 | SPA routing |
| **State Management** | Zustand 5.0 | Global state |
| **Server State** | TanStack Query 5.62 | Data fetching, caching |
| **UI Components** | Radix UI | Accessible primitives |
| **Styling** | Tailwind CSS 3.4 | Utility-first CSS |
| **Icons** | lucide-react 0.469 | Icon library |
| **Charts** | Recharts 2.15 | Data visualization |
| **3D Graphics** | Three.js + React Three Fiber | 3D globe visualization (optional) |

---

## Project Structure (Top-Level)

```
enterprise-procurement-intelligence/
├── backend/                      # FastAPI backend (124 Python files)
│   ├── alembic/                  # Database migrations (4 versions)
│   ├── app/                      # Application code
│   │   ├── agents/               # LangGraph nodes (7 files)
│   │   ├── api/v1/               # REST endpoints (8 route files, 70+ endpoints)
│   │   ├── config/               # Settings & dependency injection
│   │   ├── db/models/            # SQLAlchemy models (6 files, 24 tables)
│   │   ├── evaluation/           # Evaluation framework
│   │   ├── graph/                # Neo4j graph operations
│   │   ├── ingestion/            # Document pipeline (12 files)
│   │   ├── mcp_server/           # Model Context Protocol server
│   │   ├── providers/            # LLM, embeddings, vector, graph providers (15 files)
│   │   ├── retrieval/            # Hybrid retrieval engine (8 files)
│   │   ├── schemas/              # Pydantic request/response models
│   │   ├── security/             # Auth, RBAC, audit logging
│   │   └── main.py               # FastAPI app entrypoint
│   ├── tests/                    # Test suite (68 test files, 473+ tests)
│   ├── var/                      # Runtime data (database, logs, indexes)
│   ├── Dockerfile                # Production Docker image
│   └── pyproject.toml            # Python dependencies
│
├── frontend/                     # React frontend
│   ├── src/
│   │   ├── components/           # React components
│   │   ├── pages/                # Page components (15+ routes)
│   │   └── lib/                  # Utilities
│   ├── Dockerfile                # Frontend Docker image
│   ├── package.json              # Node dependencies
│   └── vite.config.ts            # Vite configuration
│
├── data/                         # Data directory
│   ├── evaluation/               # Evaluation datasets
│   │   ├── benchmark_v3/         # 120-question benchmark
│   │   └── golden_questions.json
│   └── real_procurement_ocds/    # UK OCDS procurement data (83,724 records)
│
├── .env.example                  # Environment variables template
├── docker-compose.yml            # Local development stack
├── render.yaml                   # Render.com deployment config
├── LICENSE                       # MIT License
├── audit.md                      # Complete system audit
└── README.md                     # This file
```

---

## Local Development

### Prerequisites

- Python 3.12+
- Node.js 18+
- Docker & Docker Compose (optional, for infrastructure)

### Quick Start

**1. Clone repository**
```bash
git clone https://github.com/Krish-afk-bot/enterprise-procurement-intelligence.git
cd enterprise-procurement-intelligence
```

**2. Backend setup**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
cp ../.env.example ../.env  # Configure environment variables
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**3. Frontend setup**
```bash
cd frontend
npm install
npm run dev
```

**4. Access**
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/v1/health

### Docker Setup (Infrastructure Only)

```bash
docker compose up -d postgres qdrant neo4j redis minio
```

### Environment Configuration

Key environment variables (see `.env.example` for full list):

```bash
# Security
JWT_SECRET=your-secret-key-here  # Generate: python -c "import secrets; print(secrets.token_urlsafe(48))"

# Database
DATABASE_URL=sqlite+aiosqlite:///./var/epi.db  # Dev
# DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/epi  # Prod

# Providers
VECTOR_PROVIDER=local            # local | qdrant
GRAPH_PROVIDER=local             # local | neo4j
LLM_BASE_URL=http://localhost:11434/v1  # Optional (Ollama, OpenAI-compatible)
LLM_MODEL=llama3.1:8b

# Embeddings
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DEVICE=auto            # auto | cpu | cuda
```

### Running Tests

```bash
cd backend
pytest                           # All tests
pytest --cov=app --cov-report=html  # With coverage
pytest tests/integration/        # Integration tests only
pytest -v -k "retrieval"         # Specific test pattern
```

**Current Status:** 473/493 tests passing (96.0%), 13 failures (mock configuration issues), 7 skipped

---

## Deployment

### Render.com (Backend)

1. Push to GitHub
2. Create Web Service on Render:
   - Root Directory: `backend`
   - Build Command: `pip install -e .`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Set environment variables (see `.env.example`)
4. Deploy

**Live Backend:** [enterprise-procurement-intelligence.onrender.com](https://enterprise-procurement-intelligence.onrender.com)

### Vercel (Frontend)

```bash
cd frontend
npm i -g vercel
vercel --prod
```

**Live Frontend:** [enterprise-procurement-intelligence-n04pc4po3.vercel.app](https://enterprise-procurement-intelligence-n04pc4po3.vercel.app)

### Docker

```bash
docker compose up -d  # Full stack
docker compose logs -f api  # View logs
```

**Note:** Current deployment uses local providers (SQLite, in-memory vectors, SQLite graph). For production, configure PostgreSQL, Qdrant, Neo4j, and Redis via environment variables.

---

## Roadmap

### Completed ✓
- Hybrid retrieval (dense + sparse + graph)
- Cross-encoder reranking
- LangGraph multi-agent pipeline
- Evidence grounding and citation
- MCP server integration
- RBAC and tenant isolation
- 120-question benchmark evaluation
- Production deployment (Render + Vercel)

### In Progress 🔄
- Improving refusal precision (currently 42.9%)
- Answer correctness optimization (currently 39.7%)
- Clause extraction accuracy
- Multi-hop graph reasoning

### Planned 📋
- **Q1 2025:**
  - Human evaluation of benchmark dataset
  - Fine-tuned reranker for procurement domain
  - Query rewriting for improved retrieval
  - Bulk document upload
- **Q2 2025:**
  - Vision-language model integration for charts/diagrams
  - Advanced graph algorithms (PageRank, community detection)
  - Federated search across multiple tenants
  - Export to Excel/PDF
- **Q3 2025:**
  - Fine-tuned embedding model (bge-m3 → domain-specific)
  - Real-time document change detection
  - Slack/Teams integration
  - Mobile app (React Native)

---

## Contributing

Contributions welcome! Please open an issue or pull request.

**Development Guidelines:**
- Follow PEP 8 (Python) and ESLint rules (TypeScript)
- Add tests for new features
- Update documentation
- Use conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`

---

## License

**MIT License**

Copyright (c) 2024 Enterprise Procurement Intelligence

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

**OCDS Data:** Open Contracting Data Standard (OCDS) data is licensed under the Open Data Commons Open Database License (ODbL). Attribution to UK Find a Tender Service required when using procurement data.

---

## Support

**Documentation:** See `audit.md` for complete system documentation  
**Issues:** [GitHub Issues](https://github.com/Krish-afk-bot/enterprise-procurement-intelligence/issues)  
**Repository:** [github.com/Krish-afk-bot/enterprise-procurement-intelligence](https://github.com/Krish-afk-bot/enterprise-procurement-intelligence)

---

*Built with FastAPI, LangGraph, React, Neo4j, and Qdrant. Powered by evidence.*
