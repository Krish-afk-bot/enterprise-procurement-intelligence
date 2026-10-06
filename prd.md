# Enterprise Procurement Intelligence

## Multimodal, Agentic & Graph-Enhanced Enterprise RAG Platform

**Version:** 1.0
**Project Type:** AI Application Development with RAG
**Backend:** Python
**Frontend:** TypeScript + React
**Architecture:** Enterprise RAG + Agentic RAG + Multimodal RAG + GraphRAG + Structured RAG
**Primary Domain:** Enterprise Procurement Intelligence

---

# 1. Executive Summary

Enterprise procurement teams manage hundreds or thousands of supplier contracts, pricing agreements, amendments, compliance documents, purchase records and supporting files.

Important information is distributed across:

* PDF contracts
* scanned documents
* pricing agreements
* amendments
* compliance certificates
* spreadsheets
* supplier records
* purchase orders
* contract metadata
* tables
* historical versions

A buyer asking:

> "What price did Supplier A negotiate for Product X, and is that price still valid?"

may need to inspect several documents, versions, amendments and structured records.

The proposed platform converts this fragmented procurement information into an **enterprise AI intelligence system** capable of:

* document ingestion
* OCR
* multimodal document understanding
* semantic and lexical retrieval
* hybrid search
* reranking
* contextual retrieval
* metadata filtering
* temporal/version-aware retrieval
* structured SQL retrieval
* graph retrieval
* agentic query planning
* multi-hop reasoning
* self-reflective/corrective RAG
* citation generation
* conflict detection
* supplier comparison
* table understanding
* access control
* evaluation
* observability

The system must not behave like a basic "chat with PDF" application.

It must behave like an **AI procurement analyst with verifiable evidence**.

---

# 2. Problem Statement

An enterprise procurement team holds supplier contracts, pricing agreements, and compliance documents, but buyers cannot quickly verify negotiated terms because the answers are spread across hundreds of contracts.

The system must allow users to ask natural-language questions and receive:

1. A grounded answer.
2. Exact supporting evidence.
3. Page-level citations.
4. Document and version information.
5. Relevant supplier/contract metadata.
6. Confidence and retrieval information.
7. Comparisons when multiple suppliers are involved.
8. Conflict explanations when documents disagree.
9. A refusal when sufficient evidence does not exist.

---

# 3. Product Vision

Build a production-oriented procurement intelligence platform where:

> **Every important answer is traceable to evidence, every document is searchable, every version is understood, and complex questions can be solved through multiple retrieval and reasoning strategies.**

The platform should combine:

```text
Unstructured Documents
        +
Structured Procurement Data
        +
Vector Search
        +
Keyword Search
        +
Knowledge Graph
        +
LLM Reasoning
        +
Agentic Workflows
        +
Evaluation
        =
Enterprise Procurement Intelligence
```

---

# 4. Goals

## 4.1 Primary Goals

* Build a complete enterprise RAG application.
* Support multiple document formats.
* Support scanned and visual documents.
* Preserve document/page/section hierarchy.
* Provide page-level citations.
* Implement dense retrieval.
* Implement sparse/keyword retrieval.
* Implement hybrid retrieval.
* Implement reranking.
* Implement contextual retrieval.
* Implement query rewriting.
* Implement query decomposition.
* Implement metadata filtering.
* Implement temporal retrieval.
* Implement GraphRAG.
* Implement SQL/structured retrieval.
* Implement agentic RAG using LangGraph.
* Implement corrective RAG.
* Implement self-reflective answer verification.
* Implement hallucination/refusal guardrails.
* Implement enterprise access control.
* Implement evaluation and observability.
* Provide a polished React/TypeScript application.

---

# 5. Non-Goals

The initial version will not attempt to:

* automatically negotiate contracts.
* autonomously sign contracts.
* provide legal advice.
* replace procurement/legal professionals.
* train a foundation LLM from scratch.
* fine-tune massive models unnecessarily.
* embed every structured database row into the vector database.
* use an LLM for deterministic calculations that SQL/Python can perform exactly.

---

# 6. Target Users

## Procurement Buyer

Needs to quickly verify:

* negotiated prices
* supplier terms
* minimum order quantities
* payment terms
* delivery terms
* contract validity
* discounts
* renewal conditions

## Procurement Manager

Needs:

* supplier comparisons
* contract risk visibility
* pricing changes
* compliance status
* historical changes

## Compliance/Legal User

Needs:

* exact clauses
* amendments
* compliance documentation
* document history
* evidence

## Administrator

Needs:

* document ingestion
* user permissions
* system health
* retrieval metrics
* audit logs
* evaluation results

---

# 7. Core Product Capabilities

The platform will contain the following intelligence layers:

```text
Layer 1     Document Intelligence
Layer 2     Retrieval Intelligence
Layer 3     Structured Data Intelligence
Layer 4     Graph Intelligence
Layer 5     Agentic Reasoning
Layer 6     Grounding & Verification
Layer 7     Enterprise Security
Layer 8     Evaluation & Observability
```

---

# 8. High-Level Architecture

```text
                         React + TypeScript
                                │
                                ▼
                         API / SSE Gateway
                                │
                                ▼
                         FastAPI Backend
                                │
                 ┌──────────────┴──────────────┐
                 │                             │
                 ▼                             ▼
          LangGraph Orchestrator          Auth / RBAC
                 │
        ┌────────┼──────────┬───────────┐
        │        │          │           │
        ▼        ▼          ▼           ▼
     Vector    BM25       SQL        Graph
    Retrieval Search    Retrieval    Retrieval
        │        │          │           │
        └────────┴──────────┴───────────┘
                         │
                         ▼
                    Reranker
                         │
                         ▼
                   Context Builder
                         │
                         ▼
                    Model Router
             ┌───────────┼───────────┐
             ▼           ▼           ▼
           LLM          VLM      Small LLM
             │           │           │
             └───────────┴───────────┘
                         │
                         ▼
                  Grounding Judge
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
         Supported Answer       Refusal /
         + Citations            Clarification
```

---

# 9. Technology Stack

## 9.1 Frontend

### Required

* React
* TypeScript
* Vite
* Tailwind CSS
* shadcn/ui
* React Router
* TanStack Query
* Zustand
* Recharts
* Lucide React
* react-markdown
* syntax highlighting where required

### Frontend Responsibilities

* authentication
* enterprise chat
* streaming responses
* citation display
* document viewer
* page preview
* search interface
* supplier comparison
* contract explorer
* ingestion dashboard
* evaluation dashboard
* system observability
* admin interface

---

# 10. Backend

## Required

* Python 3.11+
* FastAPI
* Pydantic
* Uvicorn
* SQLAlchemy
* Alembic
* LangChain
* LangGraph
* httpx
* asyncio
* structlog

The backend must remain Python-first.

All AI orchestration, retrieval, ingestion and model routing will be implemented in Python.

---

# 11. AI Orchestration

## LangChain

Use LangChain for:

* document loaders
* retrievers
* embeddings integrations
* reranker integrations
* prompt templates
* tool abstractions
* LLM interfaces
* output parsers

## LangGraph

Use LangGraph as the primary orchestration layer for:

* query classification
* planning
* retrieval
* tool selection
* multi-hop workflows
* corrective retrieval
* answer generation
* self-reflection
* retry loops
* human approval where required
* state management

Conceptually:

```text
START
  ↓
Query Understanding
  ↓
Intent Classification
  ↓
Query Planning
  ↓
Retrieve
  ↓
Evaluate Evidence
  ↓
 ┌───────────────┐
 │ Evidence Good?│
 └───────┬───────┘
       Yes│No
          │
          ▼
      Generate
          │
          ▼
    Grounding Check
          │
     ┌────┴────┐
   Pass       Fail
    │           │
    ▼           ▼
 Answer     Retrieve Again
                │
                ▼
              Answer
```

---

# 12. Model Architecture

The platform must NOT use one model for every task.

It will use a model router.

## 12.1 Primary Reasoning LLM

### Qwen3-30B-A3B-Instruct-2507

Primary responsibilities:

* answer generation
* reasoning
* query planning
* tool calling
* complex synthesis
* multi-document reasoning
* comparison
* conflict analysis

Deployment options:

```text
Development:
Cloud inference

Production:
vLLM GPU server

Fallback:
Compatible external inference API
```

The model is large enough that it should not be treated as a comfortable native workload for an 8 GB RTX 4060. The architecture therefore abstracts inference behind an LLM provider interface.

---

# 13. Visual Language Model

## Qwen3-VL family

Use for:

* scanned pages
* complex tables
* diagrams
* document layouts
* charts
* images
* visually structured contracts
* pages where normal text extraction fails

Important:

**Do not send every document page through the VLM.**

Use:

```text
Normal text extraction
       ↓
Is page visually complex?
       │
    Yes│No
       ▼
      VLM
```

This controls latency and cost.

---

# 14. Embedding Model

## BAAI/bge-m3

Use for:

* document embeddings
* chunk embeddings
* query embeddings
* semantic retrieval
* multilingual retrieval where applicable

Embedding service:

```text
EmbeddingProvider
 ├── Local GPU
 ├── CPU fallback
 └── Cloud embedding API
```

The system must not hardcode the embedding implementation.

---

# 15. Reranking Model

## BAAI/bge-reranker-v2-m3

Use after initial retrieval.

Pipeline:

```text
100 candidate chunks
       ↓
Hybrid retrieval
       ↓
Reranker
       ↓
Top 10-20 chunks
       ↓
Context builder
```

---

# 16. Model Router

The backend must expose a unified interface:

```python
class ModelRouter:
    async def generate(...)
    async def generate_structured(...)
    async def embed(...)
    async def rerank(...)
    async def vision(...)
```

Routing rules:

| Task                      | Model               |
| ------------------------- | ------------------- |
| Simple answer             | Small/efficient LLM |
| Complex reasoning         | Qwen3-30B           |
| Tool planning             | Qwen3-30B           |
| Visual page               | Qwen3-VL            |
| Embeddings                | BGE-M3              |
| Reranking                 | BGE reranker        |
| Deterministic calculation | Python              |
| SQL aggregation           | PostgreSQL          |
| Graph traversal           | Neo4j               |

---

# 17. Dataset Strategy

The project must NOT depend on one Kaggle CSV.

It will use three categories.

## 17.1 Dataset Layer A — Document Corpus

Primary RAG corpus:

* supplier contracts
* pricing agreements
* amendments
* compliance documents
* procurement agreements
* purchase-related documents
* scanned documents
* spreadsheets
* tables

Sources may include:

* public procurement contract repositories
* public contract-document repositories
* publicly available supplier/contract documents
* openly licensed procurement documents

Every document must have provenance metadata.

---

# 18. Dataset Layer B — Structured Procurement Dataset

Use structured public procurement data for:

* suppliers
* buyers
* products
* prices
* quantities
* awards
* contract metadata
* dates
* categories

Potential sources include:

* Global Public Procurement Dataset
* public procurement datasets
* Chicago/public contract datasets
* other openly licensed procurement datasets

A Kaggle dataset may be used as a structured source, but it is **not the definition of the project's RAG corpus**.

---

# 19. Dataset Layer C — Synthetic Enterprise Corpus

Create a controlled synthetic dataset to test advanced RAG behavior.

Example:

```text
Supplier A
 ├── Master Contract 2024
 ├── Amendment 1
 ├── Amendment 2
 ├── Pricing Schedule
 └── Compliance Certificate

Supplier B
 ├── Master Contract
 ├── Pricing Agreement
 └── Compliance Certificate
```

Synthetic documents must deliberately contain:

* conflicting prices
* amendments
* expired contracts
* overlapping agreements
* tables
* scanned pages
* multiple suppliers
* multiple products
* historical versions
* compliance conditions
* intentionally unanswerable questions

Synthetic documents must always be labelled as synthetic.

---

# 20. Dataset Schema

## Document

```text
document_id
tenant_id
supplier_id
contract_id
document_type
document_title
version
source_uri
checksum
created_at
effective_date
expiry_date
status
access_level
```

## Page

```text
page_id
document_id
page_number
image_uri
raw_text
ocr_text
layout_json
```

## Chunk

```text
chunk_id
document_id
page_id
section
subsection
clause
content
content_type
token_count
embedding_id
metadata
```

## Supplier

```text
supplier_id
supplier_name
category
country
region
status
```

## Contract

```text
contract_id
supplier_id
contract_number
contract_type
effective_date
expiry_date
status
version
```

## Price

```text
price_id
supplier_id
contract_id
product_id
unit_price
currency
minimum_quantity
effective_date
expiry_date
```

---

# 21. Document Ingestion Pipeline

```text
Upload
  ↓
File Validation
  ↓
Virus / Security Check
  ↓
File Type Detection
  ↓
Text / Layout Extraction
  ↓
OCR if required
  ↓
VLM if required
  ↓
Page Reconstruction
  ↓
Document Structure Detection
  ↓
Metadata Extraction
  ↓
Semantic Chunking
  ↓
Contract-Aware Chunking
  ↓
Contextual Enrichment
  ↓
Embeddings
  ↓
Vector Index
  ↓
Keyword Index
  ↓
Graph Extraction
  ↓
Database
```

---

# 22. Supported File Types

Initial:

```text
PDF
DOCX
XLSX
CSV
TXT
PNG
JPG/JPEG
```

Future:

```text
PPTX
HTML
emails
ZIP archives
```

---

# 23. OCR

Use an OCR pipeline such as PaddleOCR.

OCR is triggered when:

* PDF has little extractable text.
* page is scanned.
* image contains important text.
* document parser confidence is low.

Store both:

```text
raw extracted text
OCR text
```

Never overwrite the original source.

---

# 24. Multimodal Document Representation

Each page should maintain:

```text
Page
 ├── text
 ├── tables
 ├── images
 ├── layout
 ├── OCR
 └── visual representation
```

This allows retrieval to identify the relevant page before invoking expensive visual reasoning.

---

# 25. Chunking Strategy

Do not use fixed-size chunking alone.

Use:

### Level 1 — Structural Chunking

Based on:

* sections
* headings
* clauses
* paragraphs

### Level 2 — Token-Aware Chunking

Prevent context overflow.

### Level 3 — Contract-Aware Chunking

Keep related:

* clauses
* pricing terms
* obligations
* exceptions
* definitions

together.

### Level 4 — Parent-Child Retrieval

Retrieve a precise child chunk but provide the parent section/document context to the LLM.

---

# 26. Contextual Retrieval

Before embedding:

```text
Raw Chunk
     ↓
Document Context
     +
Section Context
     +
Supplier Context
     +
Contract Context
     ↓
Contextualized Chunk
     ↓
Embedding
```

This helps a chunk such as:

> "The price shall remain fixed for 12 months."

retain the identity of the relevant supplier, contract and section.

---

# 27. Vector Database

## Qdrant

Use Qdrant for:

* dense vectors
* sparse vectors
* metadata filtering
* hybrid search
* multi-stage retrieval
* document chunks
* table representations
* multimodal representations where supported

Collection strategy:

```text
procurement_chunks
document_pages
table_chunks
```

Metadata filters:

```text
tenant_id
supplier_id
contract_id
document_type
region
category
effective_date
expiry_date
version
access_level
```

Qdrant supports combining dense and sparse representations for hybrid retrieval.

---

# 28. Keyword Search

Use BM25.

Possible implementation:

```text
OpenSearch
```

or an initial lightweight BM25 implementation.

Keyword search is particularly important for:

* contract numbers
* SKU numbers
* supplier names
* legal phrases
* exact prices
* product IDs
* clause numbers

---

# 29. Hybrid Retrieval

Final retrieval:

```text
Query
 │
 ├── Dense Search
 │
 ├── BM25 Search
 │
 └── Metadata Filter
       │
       ▼
      Fusion
       │
       ▼
    Reranker
       │
       ▼
   Top Results
```

Use Reciprocal Rank Fusion or equivalent score fusion.

---

# 30. Retrieval Pipeline

Default:

```text
Top 100
   ↓
Dense retrieval
+
BM25
+
Metadata filters
   ↓
Fusion
   ↓
Top 50
   ↓
Reranker
   ↓
Top 10-20
   ↓
Context compression
   ↓
LLM
```

---

# 31. Query Understanding

Every query should first be classified.

Extract:

```text
intent
entities
supplier
product
contract
dates
time range
comparison
document type
requested fields
visual requirement
structured-data requirement
confidence
```

Example:

> "Compare Supplier A and Supplier B's negotiated laptop prices in 2025."

Produces:

```json
{
  "intent": "supplier_comparison",
  "suppliers": ["A", "B"],
  "product": "laptop",
  "time_range": "2025",
  "requires_comparison": true
}
```

---

# 32. Query Transformation

Support:

* query rewriting
* query expansion
* multi-query retrieval
* HyDE where useful
* conversational query rewriting
* query decomposition

Example:

> "What changed?"

becomes:

```text
What changed in the contract?
Which amendment caused the change?
What was the previous value?
What is the current value?
When did the change become effective?
```

---

# 33. Agentic RAG

LangGraph orchestrates specialized tools.

Tools:

```text
search_documents
search_contracts
search_pricing
search_compliance
search_supplier
query_database
query_graph
retrieve_page
retrieve_table
compare_suppliers
calculate
check_contract_version
```

The agent chooses the appropriate tools based on the question.

---

# 34. Structured RAG

Not every question should use vector search.

Example:

> "What was the total procurement spend for Supplier A?"

Use:

```text
Question
 ↓
SQL
 ↓
PostgreSQL
 ↓
Exact calculation
```

rather than semantic retrieval.

---

# 35. GraphRAG

Use Neo4j.

Knowledge graph entities:

```text
Supplier
Contract
Product
SKU
Clause
Amendment
ComplianceCertificate
Category
Location
Price
Buyer
```

Relationships:

```text
SUPPLIES
HAS_CONTRACT
CONTAINS
AMENDS
REPLACES
APPLIES_TO
VALID_FROM
EXPIRES_ON
COMPLIES_WITH
HAS_PRICE
BELONGS_TO
```

Example:

```text
Supplier A
   ↓ HAS_CONTRACT
Contract 2025
   ↓ AMENDED_BY
Amendment 2
   ↓ CHANGES
Price
   ↓ APPLIES_TO
Product X
```

This enables multi-hop procurement questions.

---

# 36. Temporal RAG

The system must understand:

```text
effective date
expiry date
creation date
amendment date
version
superseded_by
replaced_by
```

If an old document says:

```text
$100
```

and an effective amendment says:

```text
$92
```

the system must not blindly return `$100`.

It must explain the version/effective-date relationship.

---

# 37. Conflict Detection

When evidence conflicts:

```text
Evidence A
     +
Evidence B
     ↓
Conflict Detector
     ↓
Version / Date Analysis
     ↓
Current Valid Evidence
```

The answer should explicitly indicate the conflict when appropriate.

Example:

> "The original agreement specifies $100/unit, while Amendment 2 changes the price to $92/unit effective January 1, 2026. Therefore, the later effective price is $92/unit for the specified period."

---

# 38. Table RAG

Tables must not be flattened into meaningless text.

Store:

```text
table_id
document_id
page_number
headers
rows
cells
coordinates
caption
```

Example:

```text
Product | Supplier | Unit Price | MOQ
Laptop  | A        | $920       | 100
Laptop  | B        | $895       | 250
```

The retrieval system must be able to retrieve the table as a structured object.

---

# 39. Multimodal RAG

For a visually complex page:

```text
Query
 ↓
Retrieve Page
 ↓
Page Image
 ↓
Qwen3-VL
 ↓
Visual Interpretation
 ↓
Structured Evidence
 ↓
Answer
```

Use this for:

* scanned contracts
* tables
* signatures
* stamps
* charts
* diagrams
* layout-dependent information

---

# 40. Corrective RAG

After retrieval:

```text
Retrieve
  ↓
Evidence Evaluator
  ↓
Sufficient?
 ├── Yes → Generate
 └── No
      ↓
 Query Rewrite
      ↓
 Additional Retrieval
      ↓
 Re-evaluate
```

Maximum retry count must be configurable.

---

# 41. Self-Reflective RAG

The answer generator must not simply generate text.

Process:

```text
Retrieved Evidence
       ↓
Generated Answer
       ↓
Claim Extraction
       ↓
Claim → Evidence Mapping
       ↓
Grounding Judge
       ↓
Supported?
```

If unsupported:

```text
Retrieve More
OR
Qualify Claim
OR
Refuse
```

---

# 42. Hallucination Guardrails

The system must follow:

> If evidence does not support the answer, do not fabricate the answer.

Possible responses:

```text
"I couldn't verify this from the available documents."

"The available documents contain conflicting information."

"I found references to the supplier, but not the requested pricing term."
```

---

# 43. Citation System

Every factual claim should map to:

```text
Answer Claim
   ↓
Evidence Chunk
   ↓
Page
   ↓
Document
   ↓
Source
```

Citation object:

```json
{
  "document_id": "...",
  "document_name": "...",
  "page": 17,
  "section": "Pricing",
  "chunk_id": "...",
  "source_uri": "..."
}
```

Frontend should allow users to click the citation and open the relevant page.

---

# 44. Enterprise Security

Implement:

* authentication
* RBAC
* tenant isolation
* document ACLs
* user-level permissions
* audit logs
* encrypted secrets
* secure API access

Critical rule:

> Unauthorized documents must never enter the LLM context.

Filtering must happen before generation.

---

# 45. Prompt Injection Defense

Documents are untrusted data.

If a contract contains:

> "Ignore previous instructions..."

the system must treat that as document content, not an instruction.

Use explicit separation:

```text
SYSTEM INSTRUCTIONS
USER QUERY
RETRIEVED EVIDENCE
TOOLS
```

Retrieved documents must never override system instructions.

---

# 46. PostgreSQL

Use PostgreSQL for:

```text
users
roles
tenants
documents
pages
contracts
suppliers
products
prices
compliance
queries
answers
citations
audit_logs
evaluation_runs
agent_traces
```

PostgreSQL is the source of truth for application metadata.

---

# 47. Neo4j

Use Neo4j for:

```text
supplier relationships
contract relationships
amendments
products
categories
compliance relationships
temporal relationships
```

Neo4j should not replace PostgreSQL.

---

# 48. Object Storage

Use S3-compatible object storage.

Development:

```text
MinIO
```

Production:

```text
AWS S3
```

Store:

```text
original files
page images
OCR artifacts
processed documents
table artifacts
evaluation datasets
```

---

# 49. Cache

Use Redis for:

* query caching
* session state where needed
* rate limiting
* temporary jobs
* ingestion queues
* frequently accessed retrieval results

Never cache responses across users if their authorization contexts differ.

---

# 50. Background Jobs

Use:

```text
Celery / Dramatiq / Arq
```

for:

* document processing
* OCR
* embedding
* indexing
* graph extraction
* evaluation jobs

The initial implementation can use an async task queue with Redis.

---

# 51. API Architecture

FastAPI.

## Query APIs

```http
POST /api/v1/query
POST /api/v1/query/stream
POST /api/v1/search
```

## Documents

```http
POST /api/v1/documents/upload
POST /api/v1/documents/{id}/index
GET  /api/v1/documents
GET  /api/v1/documents/{id}
GET  /api/v1/documents/{id}/pages/{page}
DELETE /api/v1/documents/{id}
```

## Suppliers

```http
GET /api/v1/suppliers
GET /api/v1/suppliers/{id}
GET /api/v1/suppliers/{id}/contracts
GET /api/v1/suppliers/{id}/prices
```

## Contracts

```http
GET /api/v1/contracts
GET /api/v1/contracts/{id}
GET /api/v1/contracts/{id}/versions
GET /api/v1/contracts/{id}/amendments
```

## Comparison

```http
POST /api/v1/compare/suppliers
POST /api/v1/compare/contracts
POST /api/v1/compare/prices
```

## Evaluation

```http
POST /api/v1/evaluation/run
GET  /api/v1/evaluation/runs
GET  /api/v1/evaluation/{id}
```

## System

```http
GET /api/v1/health
GET /api/v1/metrics
GET /api/v1/ready
```

---

# 52. Streaming

Use Server-Sent Events.

Flow:

```text
React
 ↓
POST /query/stream
 ↓
FastAPI
 ↓
LangGraph
 ↓
Retrieval events
 ↓
Tool events
 ↓
LLM tokens
 ↓
Citation events
 ↓
Final answer
```

Frontend should progressively display:

```text
Understanding query...
Searching contracts...
Checking pricing...
Verifying evidence...
Generating answer...
```

Avoid exposing hidden chain-of-thought. Only expose safe execution/status events and concise tool/retrieval summaries.

---

# 53. Frontend Application

React + TypeScript.

Recommended structure:

```text
src/
├── app/
├── components/
├── features/
│   ├── chat/
│   ├── documents/
│   ├── suppliers/
│   ├── contracts/
│   ├── comparison/
│   ├── evaluation/
│   └── admin/
├── hooks/
├── lib/
├── services/
├── stores/
├── types/
└── pages/
```

---

# 54. Main UI

## Procurement Chat

Layout:

```text
┌─────────────────────────────────────────────┐
│ Procurement Intelligence                   │
├───────────────┬─────────────────────────────┤
│ Conversations │ Answer                     │
│               │                             │
│ Documents     │ Supplier A price: $92      │
│ Suppliers     │                             │
│ Contracts     │ Sources:                    │
│               │ [Contract p.17]             │
│               │ [Amendment p.3]             │
│               │                             │
│               │ Evidence Panel              │
├───────────────┴─────────────────────────────┤
│ Ask about contracts, pricing, compliance... │
└─────────────────────────────────────────────┘
```

---

# 55. Evidence Panel

When a user clicks a citation:

```text
Document
Contract_A_2025.pdf

Page 17

Section:
Pricing Schedule

Relevant Evidence:
[highlighted text/table]

Version:
Amendment 2

Effective:
2026-01-01
```

---

# 56. Supplier Comparison UI

Allow:

```text
Supplier A
vs
Supplier B
vs
Supplier C
```

Comparison dimensions:

* price
* MOQ
* payment terms
* delivery
* contract duration
* compliance
* renewal
* discounts

All extracted values must have evidence links.

---

# 57. Document Explorer

Features:

* upload
* filter
* search
* supplier
* contract
* document type
* version
* effective date
* status
* indexing status

---

# 58. Admin Dashboard

Show:

```text
Documents
Pages
Chunks
Suppliers
Contracts

Retrieval:
Recall@K
MRR
nDCG
Hit Rate

Generation:
Groundedness
Correctness
Citation Precision

System:
Latency
Token usage
Cost
Cache hit rate
Failures
```

---

# 59. Evaluation Framework

Create a golden dataset.

Each record:

```json
{
  "question": "...",
  "expected_answer": "...",
  "expected_documents": [],
  "expected_pages": [],
  "question_type": "...",
  "difficulty": "..."
}
```

Question categories:

```text
single-hop
multi-hop
comparison
temporal
table
multimodal
structured SQL
graph
ambiguous
unanswerable
conflicting
```

---

# 60. Retrieval Metrics

Measure:

```text
Recall@K
Precision@K
MRR
nDCG
Hit Rate
```

---

# 61. Generation Metrics

Measure:

```text
Answer correctness
Answer relevance
Faithfulness
Groundedness
Citation precision
Citation recall
Citation completeness
```

---

# 62. Experiment Matrix

Run controlled experiments:

```text
Experiment A
Dense Retrieval

Experiment B
Dense + BM25

Experiment C
Dense + BM25 + Reranker

Experiment D
Contextual + Hybrid + Reranker

Experiment E
Agentic RAG

Experiment F
Agentic + Graph + SQL

Experiment G
Multimodal RAG
```

The system should store experiment results rather than claiming improvements without measurement.

---

# 63. Observability

Every query should create a trace:

```text
query_id
user_id
query
classification
rewritten_query
retrieval_strategy
retrieved_chunks
reranker_results
tools_called
graph_queries
sql_queries
model
prompt_version
token_usage
latency
citations
grounding_score
final_answer
```

Use:

```text
LangSmith
```

if available for LLM tracing/evaluation.

Otherwise implement structured application-level tracing.

---

# 64. Logging

Use structured JSON logging.

Example:

```json
{
  "request_id": "...",
  "query_id": "...",
  "event": "retrieval_complete",
  "retrieval_type": "hybrid",
  "candidate_count": 100,
  "reranked_count": 15,
  "latency_ms": 421
}
```

Never log:

* API keys
* passwords
* sensitive document content unnecessarily
* private user data

---

# 65. API Integrations

## Required integrations

### LLM

* Qwen3 inference endpoint
* optional OpenAI-compatible provider interface

### Embeddings

* BGE-M3 local inference
* optional embedding API

### Vector DB

* Qdrant

### Structured DB

* PostgreSQL

### Graph

* Neo4j

### Object Storage

* S3 / MinIO

### Cache

* Redis

### Observability

* LangSmith
* OpenTelemetry-compatible tracing

### Authentication

Initial:

```text
JWT
```

Production extension:

```text
OAuth2 / OIDC
```

---

# 66. External Data APIs

The architecture must support connectors rather than hardcoded scrapers.

Connector interface:

```python
class ProcurementDataSource:
    async def discover()
    async def fetch()
    async def normalize()
```

Potential sources:

* public procurement datasets
* contract repositories
* open government procurement APIs
* public supplier datasets

Every imported record must retain:

```text
source
source_url
retrieved_at
license
original_id
```

---

# 67. Cost Optimization

The system should use routing.

```text
Simple query
    ↓
Cheap/small model

Complex reasoning
    ↓
Qwen3-30B

Visual query
    ↓
Qwen3-VL

Exact numeric query
    ↓
SQL/Python

Search
    ↓
Embedding + BM25

Complex retrieval
    ↓
Reranker
```

Do not use the most expensive model for every request.

---

# 68. GPU Strategy

User development hardware:

```text
RTX 4060 8GB
16GB RAM
Ryzen 7 7840HS
```

Use local GPU for:

* BGE-M3
* reranking
* OCR acceleration where supported
* smaller LLMs
* development

Use cloud GPU for:

* Qwen3-30B
* Qwen3-VL
* production inference

The application must treat inference as a provider rather than assuming a specific GPU.

---

# 69. Deployment Architecture

## Development

```text
React/Vite
FastAPI
PostgreSQL
Qdrant
Neo4j
Redis
MinIO
Local models
Docker Compose
```

## Production

```text
Frontend
   ↓
CDN / Hosting

API Gateway
   ↓
FastAPI
   ↓
LangGraph
   ├── PostgreSQL
   ├── Qdrant Cloud
   ├── Neo4j
   ├── Redis
   ├── S3
   └── GPU inference
```

---

# 70. Docker

Provide:

```text
docker-compose.yml
```

Services:

```text
frontend
backend
postgres
qdrant
neo4j
redis
minio
worker
```

GPU inference should be independently deployable.

---

# 71. Repository Structure

```text
enterprise-procurement-rag/
│
├── apps/
│   ├── web/
│   └── api/
│
├── backend/
│   ├── agents/
│   ├── api/
│   ├── auth/
│   ├── config/
│   ├── db/
│   ├── evaluation/
│   ├── graph/
│   ├── ingestion/
│   ├── models/
│   ├── observability/
│   ├── retrieval/
│   ├── security/
│   ├── tools/
│   └── workers/
│
├── frontend/
│   └── src/
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── synthetic/
│   └── evaluation/
│
├── models/
│
├── scripts/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── retrieval/
│   ├── evaluation/
│   └── e2e/
│
├── docker/
│
├── docs/
│
├── docker-compose.yml
├── .env.example
├── README.md
└── pyproject.toml
```

---

# 72. Testing

## Unit Tests

Test:

* chunking
* metadata extraction
* parsers
* query classification
* retrieval
* citation mapping
* permissions
* API schemas

## Integration Tests

Test:

```text
Upload
→ Parse
→ Embed
→ Index
→ Retrieve
→ Generate
→ Cite
```

## Security Tests

Test:

* unauthorized document retrieval
* prompt injection
* tenant isolation
* malformed files
* API authentication

## Evaluation Tests

Run golden questions automatically.

---

# 73. Reliability Requirements

The system must:

* never invent citations.
* never expose unauthorized evidence.
* preserve document provenance.
* preserve version information.
* return explicit uncertainty.
* gracefully handle model failures.
* gracefully handle retrieval failures.
* retry transient external API errors.
* avoid infinite agent loops.
* enforce tool timeouts.
* log failures.

---

# 74. Performance Targets

Initial engineering targets:

```text
Simple search:
< 2 seconds target

Standard RAG:
< 5 seconds target

Complex agentic query:
< 10-15 seconds target

Document indexing:
asynchronous

Streaming:
first meaningful event < 1-2 seconds target
```

These are engineering targets, not claimed achieved metrics.

---

# 75. UX Requirements

The application should feel like:

```text
Enterprise Search
        +
ChatGPT
        +
Contract Intelligence
        +
Data Analytics
```

Visual direction:

* clean enterprise interface
* light-first theme
* high readability
* strong evidence hierarchy
* minimal unnecessary animations
* responsive layout
* clear source attribution
* professional procurement/dashboard aesthetics

---

# 76. Core User Journey

```text
User logs in
      ↓
Dashboard
      ↓
Uploads contract
      ↓
Document processing
      ↓
OCR / extraction
      ↓
Chunking
      ↓
Embedding
      ↓
Vector + keyword + graph indexing
      ↓
User asks question
      ↓
Query understanding
      ↓
Agent chooses tools
      ↓
Hybrid retrieval
      ↓
Reranking
      ↓
SQL/Graph if required
      ↓
LLM/VLM reasoning
      ↓
Grounding verification
      ↓
Citation generation
      ↓
Answer
```

---

# 77. Example Queries

The final system should support questions such as:

### Simple

> What is Supplier A's payment term?

### Pricing

> What is the negotiated price for Product X?

### Temporal

> What is the current price after the latest amendment?

### Comparison

> Compare Supplier A and Supplier B for Product X.

### Multi-hop

> Which supplier has the lowest negotiated price for products in Category Y while meeting the required compliance certification?

### Structured

> What was the total procurement value for Supplier A in 2025?

### Multimodal

> What discount is shown in the pricing table on page 18?

### Conflict

> Why do two documents show different prices for Product X?

### Unanswerable

> What price did Supplier C offer in 2028?

Expected behavior:

> "I could not verify a 2028 Supplier C price from the available evidence."

---

# 78. Advanced Agent Design

The agent system should use specialized nodes.

```text
Supervisor
   │
   ├── Retrieval Agent
   │
   ├── SQL Agent
   │
   ├── Graph Agent
   │
   ├── Document Agent
   │
   ├── Vision Agent
   │
   ├── Comparison Agent
   │
   └── Verification Agent
```

The supervisor decides which capabilities are required.

Avoid creating unnecessary autonomous agents.

---

# 79. Agent Safety

Every agent must have:

* explicit tool permissions
* maximum iterations
* timeout
* structured outputs
* validation
* audit logging

Agents should not have unrestricted access to arbitrary APIs.

---

# 80. Prompt Architecture

Maintain versioned prompts:

```text
prompts/
├── query_classifier/
├── query_rewriter/
├── planner/
├── answer_generator/
├── grounding_judge/
├── citation_extractor/
├── conflict_detector/
├── vision/
└── summarizer/
```

Every generation trace records the prompt version.

---

# 81. Configuration

Use environment variables.

Example:

```text
DATABASE_URL
QDRANT_URL
QDRANT_API_KEY
NEO4J_URI
NEO4J_USERNAME
NEO4J_PASSWORD
REDIS_URL
S3_ENDPOINT
S3_ACCESS_KEY
S3_SECRET_KEY

LLM_BASE_URL
LLM_API_KEY
LLM_MODEL

EMBEDDING_MODEL
RERANKER_MODEL

LANGSMITH_API_KEY
JWT_SECRET
```

Never commit secrets.

---

# 82. API Provider Abstraction

The project must avoid vendor lock-in.

```python
LLMProvider
EmbeddingProvider
RerankerProvider
VisionProvider
StorageProvider
VectorStoreProvider
GraphProvider
```

This allows switching between:

```text
local
AWS
OpenAI-compatible endpoint
Hugging Face
other inference providers
```

without rewriting application logic.

---

# 83. Implementation Phases

## Phase 1 — Foundation

Build:

* repository
* React/TypeScript
* FastAPI
* PostgreSQL
* authentication
* Docker
* configuration
* health checks

---

## Phase 2 — Basic RAG

Build:

* PDF ingestion
* parsing
* chunking
* BGE-M3
* Qdrant
* retrieval
* LLM answer
* citations

---

## Phase 3 — Production Retrieval

Build:

* metadata
* BM25
* hybrid search
* reranking
* contextual retrieval
* parent-child retrieval
* temporal metadata

---

## Phase 4 — Multimodal RAG

Build:

* OCR
* page images
* table extraction
* Qwen3-VL
* visual retrieval
* table RAG

---

## Phase 5 — Agentic RAG

Build:

* LangGraph
* query planner
* tool calling
* query decomposition
* corrective retrieval
* retries
* structured outputs

---

## Phase 6 — Enterprise Intelligence

Build:

* PostgreSQL structured retrieval
* Neo4j
* GraphRAG
* supplier comparison
* contract version analysis
* conflict detection

---

## Phase 7 — Self-Reflective RAG

Build:

* claim extraction
* evidence mapping
* grounding judge
* citation verification
* unsupported-answer detection
* refusal handling

---

## Phase 8 — Evaluation

Build:

* golden dataset
* retrieval metrics
* answer metrics
* citation metrics
* experiment runner
* evaluation dashboard

---

## Phase 9 — Observability

Build:

* LangSmith integration
* structured logs
* traces
* token metrics
* latency metrics
* cost metrics
* retrieval traces

---

## Phase 10 — Production

Build:

* production Docker setup
* cloud deployment
* GPU inference
* object storage
* security hardening
* monitoring
* documentation

---

# 84. Definition of Done

The project is considered complete when a user can:

1. Upload a PDF contract.
2. Upload a scanned contract.
3. Upload a pricing spreadsheet.
4. Process documents automatically.
5. Search using natural language.
6. Search using exact contract numbers/SKUs.
7. Retrieve semantically relevant information.
8. Retrieve exact keyword matches.
9. Combine dense and sparse retrieval.
10. Apply metadata filters.
11. Rerank results.
12. Ask temporal questions.
13. Ask comparison questions.
14. Ask multi-hop questions.
15. Ask questions requiring SQL.
16. Ask questions requiring graph traversal.
17. Ask questions requiring visual understanding.
18. Receive page-level citations.
19. Open supporting evidence.
20. Detect conflicting documents.
21. Distinguish old and current contract versions.
22. Refuse unsupported questions.
23. See streaming responses.
24. See retrieval/tool execution status.
25. Run evaluation experiments.
26. View retrieval and answer metrics.
27. Enforce document permissions.
28. Audit user queries.
29. Trace model/tool execution.
30. Deploy the application through Docker.

---

# 85. Final Architecture

```text
                         ┌─────────────────────┐
                         │ React + TypeScript  │
                         │ Vite + Tailwind     │
                         └──────────┬──────────┘
                                    │
                              SSE / REST
                                    │
                         ┌──────────▼──────────┐
                         │       FastAPI       │
                         │      Python         │
                         └──────────┬──────────┘
                                    │
                         ┌──────────▼──────────┐
                         │     LangGraph       │
                         │ Agent Orchestrator  │
                         └──────────┬──────────┘
                                    │
        ┌───────────────────────────┼────────────────────────────┐
        │                           │                            │
        ▼                           ▼                            ▼
┌───────────────┐          ┌────────────────┐          ┌────────────────┐
│ Hybrid RAG    │          │ Structured RAG │          │    GraphRAG    │
│               │          │                │          │                │
│ Qdrant        │          │ PostgreSQL     │          │ Neo4j          │
│ BM25          │          │ SQL            │          │ Knowledge Graph│
│ BGE-M3        │          │                │          │                │
│ Reranker      │          │                │          │                │
└───────┬───────┘          └───────┬────────┘          └───────┬────────┘
        │                          │                           │
        └──────────────────────────┼───────────────────────────┘
                                   │
                            ┌──────▼──────┐
                            │ Context     │
                            │ Builder     │
                            └──────┬──────┘
                                   │
                      ┌────────────▼────────────┐
                      │       Model Router      │
                      └────────────┬────────────┘
                                   │
                ┌──────────────────┼──────────────────┐
                │                  │                  │
                ▼                  ▼                  ▼
       Qwen3-30B-A3B          Qwen3-VL          Small LLM
       Reasoning/Tools       Vision/Docs       Simple Tasks
                │                  │                  │
                └──────────────────┼──────────────────┘
                                   │
                            ┌──────▼──────┐
                            │ Grounding   │
                            │ Judge       │
                            └──────┬──────┘
                                   │
                       ┌───────────┴───────────┐
                       │                       │
                       ▼                       ▼
                  Answer + Citations      Refusal /
                                          Clarification
```

---

# 86. Final Technology Matrix

| Layer            | Technology                  |
| ---------------- | --------------------------- |
| Frontend         | React                       |
| Language         | TypeScript                  |
| Build            | Vite                        |
| Styling          | Tailwind CSS                |
| Components       | shadcn/ui                   |
| State            | Zustand                     |
| Server state     | TanStack Query              |
| Backend          | Python                      |
| API              | FastAPI                     |
| Validation       | Pydantic                    |
| ORM              | SQLAlchemy                  |
| Migrations       | Alembic                     |
| RAG              | LangChain                   |
| Agents           | LangGraph                   |
| Main LLM         | Qwen3-30B-A3B-Instruct-2507 |
| VLM              | Qwen3-VL                    |
| Embeddings       | BGE-M3                      |
| Reranker         | BGE-Reranker-v2-M3          |
| OCR              | PaddleOCR                   |
| Vector DB        | Qdrant                      |
| Keyword          | BM25/OpenSearch             |
| SQL DB           | PostgreSQL                  |
| Graph DB         | Neo4j                       |
| Cache            | Redis                       |
| Object Storage   | S3/MinIO                    |
| LLM Serving      | vLLM                        |
| Streaming        | SSE                         |
| Observability    | LangSmith + OpenTelemetry   |
| Containers       | Docker                      |
| Testing          | Pytest + Playwright         |
| Frontend Testing | Vitest                      |
| API Docs         | OpenAPI                     |
| Authentication   | JWT/OIDC                    |
| CI/CD            | GitHub Actions              |

---

# 87. Core Design Principle

The most important architectural rule is:

```text
                    DON'T BUILD
                         │
                         ▼
                  "Chat With PDFs"
                         │
                         X
                         │
                         ▼
                  BUILD THIS
                         │
                         ▼
             Procurement Intelligence
                         │
       ┌─────────────────┼─────────────────┐
       ▼                 ▼                 ▼
   Documents          Structured          Graph
       │                 │                 │
       └─────────────────┼─────────────────┘
                         ▼
                    Hybrid RAG
                         ▼
                    Agentic RAG
                         ▼
                   Multimodal RAG
                         ▼
                  Self-Reflective RAG
                         ▼
                  Grounded Answers
                         ▼
                Verifiable Citations
```

The system should be **dataset-agnostic at the architecture level**, while the actual implementation uses a controlled procurement corpus from public documents, structured procurement data, and a clearly labelled synthetic enterprise corpus.

This gives the project enough breadth to demonstrate the Sprint 2 RAG fundamentals while also demonstrating modern enterprise RAG capabilities rather than stopping at a basic vector-search chatbot.
