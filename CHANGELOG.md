# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0-alpha] - 2026-11-03

### 🚀 Initial Alpha Release

First functional release of the Enterprise Procurement Intelligence system. This is an **alpha release** for early testing and feedback.

### ✨ Features

#### Backend
- **Retrieval Pipeline**: Hybrid BM25 + semantic search with cross-encoder reranking
- **Query Understanding**: Intent classification, entity extraction, question decomposition
- **Generation**: LLM-powered answer generation with citation binding
- **Verification**: Coverage and grounding checks with refusal on insufficient evidence
- **Evaluation Framework**: V2 evaluation harness with 130-question test set (90 dev / 40 held-out)
- **Database**: SQLite with Alembic migrations, document ingestion tracking
- **API**: FastAPI endpoints for document ingestion and question answering

#### Frontend
- **Chat Interface**: Real-time question answering with streaming responses
- **Document Management**: Upload and ingest RFPs and supplier documentation
- **Citation Display**: Source references with page numbers and excerpts
- **Response Status**: Visual indicators for answers, refusals, and errors

#### Infrastructure
- **CI/CD**: Comprehensive GitHub Actions workflows (lint, tests, type checking, security)
- **Docker**: Containerized development and deployment setup
- **Documentation**: PRD, contribution guidelines, code of conduct, evaluation methodology

### 📊 Current Performance (Phase 2 Baseline)

Measured on 130-question evaluation set with local LLM (`qwen2.5-coder:7b`):

| Metric | Value |
|--------|-------|
| **Answer Correctness** | 68.3% (71/104 answerable) |
| **Refusal Precision** | 47.8% (22 tp / 46 total refusals) |
| **Refusal Recall** | 84.6% (22 tp / 26 unanswerable) |
| **Citation Precision** | 54.5% |
| **Retrieval Recall@10** | 73.4% |
| **Latency p50** | 6.9s |
| **Latency p95** | 10.5s |

### ⚠️ Known Limitations

#### Over-Refusal Issue
- **Primary Issue**: 28 refusal failures (77% of all failures)
- **Root Cause**: Answerable questions incorrectly refused after coverage/binding checks
- **Status**: Systematic fix workflow in progress (see `docs/evaluation-workflow.md`)
- **Impact**: False refusal rate of ~52% (24 false positives / 46 total refusals)

#### Evaluation Trustworthiness
- **Dev/Held-out Split**: Recently implemented to prevent overfitting
- **Statistical Validation**: Paired bootstrap testing framework added but not yet applied
- **Oracle Analysis**: In progress to separate retrieval vs generation failures

#### Deployment
- No production deployment workflows (placeholders removed)
- Manual deployment required
- No monitoring or observability infrastructure

#### Security
- Token-based authentication is basic placeholder
- No rate limiting or DDoS protection
- No input sanitization hardening

### 🔧 Technical Details

**Dependencies**:
- Python 3.12 with FastAPI, LlamaIndex, Sentence-Transformers
- Node.js 20 with React, TypeScript, Vite
- Local LLM endpoint (OpenAI-compatible API)

**Infrastructure**:
- 3 GitHub Actions workflows: CI (lint/test/build), Security (scanning), Dependency Review
- Development environment requires local LLM setup

### 📖 Documentation

- `README.md`: Quick start and overview
- `prd.md`: Product requirements and architecture
- `CONTRIBUTING.md`: Development workflow
- `docs/RESULTS.md`: Detailed evaluation results
- `docs/evaluation-workflow.md`: 9-phase improvement methodology

### 🐛 Known Issues

1. **High false refusal rate**: ~52% of refusals are incorrect (over-refusal)
2. **Citation precision**: Only 54.5% (needs improvement)
3. **Retrieval gaps**: 26.6% of questions missing relevant documents in top-10
4. **Generation errors**: 1 remaining case of fluent-but-wrong answers

### 🎯 What's Next

Priority improvements tracked in `docs/evaluation-workflow.md`:
1. Oracle evaluation to quantify retrieval vs generation gap
2. Over-refusal root cause analysis and targeted fixes
3. Statistical validation of improvements with paired bootstrap
4. Held-out set validation to confirm generalization

### 🙏 Feedback Welcome

This is an alpha release. We're actively seeking feedback on:
- Answer quality and correctness
- Refusal behavior (both over-refusal and under-refusal cases)
- Citation relevance and accuracy
- UI/UX improvements
- Performance and latency

Please use GitHub Issues to report bugs or suggest improvements.

---

## Release Notes

**Git Tag**: `v0.1.0-alpha`  
**Branch**: Created from `master`  
**Commit**: TBD (to be tagged after review)

