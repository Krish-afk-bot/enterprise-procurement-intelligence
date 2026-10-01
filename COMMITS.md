# Engineering Commit Roadmap

This file is the project's engineering roadmap and commit ledger.

It is **not** a fabricated history. It records only commits that actually exist in the repository.
Every SHA listed here is a real SHA. Every date is the real commit date.

---

## Commit Rules

All commits in this repository follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

[optional body]
[optional footer]
```

Allowed types: `feat` `fix` `docs` `test` `refactor` `perf` `chore` `build` `ci` `security`

Do not use: `update` `changes` `final` `final2` `stuff` `misc` `more changes`

Each commit must be:
- Meaningful — represents a real unit of engineering work
- Atomic — a single concern per commit
- Reviewable — small enough to review in a PR
- Testable — does not break the build or known-passing verification scripts

---

## Future Daily Workflow

When instructed: **"Make the next two commits."**

The agent must:

1. Read this file (`COMMITS.md`).
2. Inspect the actual current repository state.
3. Identify the next two unfinished meaningful tasks from the Planned section below, respecting dependencies.
4. Implement task one.
5. Verify task one (run relevant scripts, build, typecheck).
6. Commit task one.
7. Implement task two.
8. Verify task two.
9. Commit task two.
10. Update this file: move both tasks from Planned to Completed, record the real SHAs and dates.
11. Stop.

Never manufacture work to increase commit count.
Never create empty commits.
Never create fake commits.
Never modify existing commit history.

---

## Completed

### 1. chore(repo): establish repository engineering baseline

**Status:** Completed
**SHA:** 2c95464e60a4a59df03af06cf89e0124158a83ea
**Date:** 2026-10-02
**Branch:** master

**Purpose:**
Establish repository hygiene and engineering conventions for the existing Enterprise Procurement Intelligence codebase.

**Files created:**
- `.gitignore` — covers Node, Python, env secrets (including `.fb_token` JWT), IDE, OS, runtime state (`backend/var/`, SQLite, model weights, embedding caches, logs), and Freebuff IDE artefacts
- `.editorconfig` — UTF-8, LF line endings, 4-space Python, 2-space everything else
- `.gitattributes` — LF normalisation, binary markers for model files and documents
- `CONTRIBUTING.md` — branch/commit conventions, code style commands, testing policy, secrets policy
- `SECURITY.md` — vulnerability reporting, known gaps, secrets policy, supported versions
- `CODE_OF_CONDUCT.md` — professional conduct standards

**Validation:**
- `git diff --staged --stat` confirmed exactly 6 new files, 433 insertions, 0 deletions
- No application code modified
- No secrets committed
- `.fb_token` JWT blocked by `.gitignore`

---

### 2. docs(repo): establish project documentation and engineering roadmap

**Status:** Completed
**SHA:** a9a75bc34e91fa4a7248aade616433b174ee35f0
**Date:** 2026-10-02
**Branch:** master

**Purpose:**
Establish project documentation grounded in the actual verified state of the repository, and create a structured engineering roadmap for future incremental work.

**Files created:**
- `README.md` — project description, honest capability table (Implemented / Not configured / Planned), quickstart, stack, repo structure
- `docs/architecture.md` — query flow, ingestion flow, provider abstraction table, data model, security architecture, evaluation architecture, current vs target comparison, known gaps
- `docs/development.md` — prerequisites, backend setup, frontend setup, environment config, ingestion, migrations, build commands, verification scripts, useful commands summary
- `docs/ci-cd.md` — current state (no CI), intended pipeline (PLANNED), tooling table, gates policy, next steps
- `docs/deployment.md` — local deployment, Docker Compose infra, LLM/VLM configuration, target production architecture (PLANNED), env var reference
- `COMMITS.md` — this file: commit rules, daily workflow instructions, completed ledger, planned roadmap

**Validation:**
- All documentation reflects the audit.md findings, not aspirational claims
- LLM/VLM marked as not configured
- Docker app profile marked as broken
- Automated tests marked as absent
- No application code modified
- No secrets committed

---

## Planned

The tasks below are ordered by logical dependency. When instructed to make the next two commits, the agent reads this file, picks the next two unfinished tasks, implements them, and updates this ledger.

---

### Repository Quality

#### RQ-1: `build(docker): add backend Dockerfile`

**Depends on:** nothing
**Why:** The `docker-compose.yml` references `backend/Dockerfile` which does not exist. The app Docker profile cannot build until this is created. This is the highest-priority infrastructure gap.
**What:** Write a multi-stage `backend/Dockerfile` using a Python 3.11 slim base, install the package with `pip install -e ".[ocr]"`, expose port 8000, and set the default command to `uvicorn app.main:app --host 0.0.0.0 --port 8000`. Verify `docker build -f backend/Dockerfile .` succeeds.

---

#### RQ-2: `chore(deps): pin all backend dependencies to exact versions`

**Depends on:** nothing
**Why:** `pyproject.toml` uses `>=` ranges for all dependencies. Pinning to a lockfile ensures reproducible installs.
**What:** Generate `backend/requirements.txt` (or use `pip-compile` / `uv pip compile`) from the installed environment. Commit the lockfile. Document the update process in `CONTRIBUTING.md`.

---

#### RQ-3: `ci(lint): add GitHub Actions PR workflow for lint and type checks`

**Depends on:** RQ-2 (pinned deps for reproducible CI)
**Why:** First CI gate. Catches formatting and type errors on every PR without requiring tests to exist first.
**What:** Create `.github/workflows/pr.yml` that runs on `pull_request` targeting `main`. Steps: checkout → set up Python → install deps → `ruff format --check` → `ruff check` → `mypy app/` → set up Node → `npm ci` → `npm run typecheck` → `npm run lint`.

---

### Testing

#### TEST-1: `test(backend): add pytest infrastructure and first unit tests`

**Depends on:** nothing (test deps already declared in `pyproject.toml[eval]`)
**Why:** The project has zero automated tests. This is the most significant engineering gap. Start with the lowest-risk, highest-value layer: pure utility functions and schemas.
**What:** Create `backend/tests/__init__.py`, `backend/tests/conftest.py`. Write unit tests for: chunking logic (`ingestion/chunking.py`), RRF fusion (`retrieval/fusion.py`), query understanding entity extraction, and citation validation logic. Target ≥ 15 test functions. Verify `pytest tests/` passes.

---

#### TEST-2: `test(backend): add FastAPI integration tests for auth and document endpoints`

**Depends on:** TEST-1
**Why:** The 29-assertion manual verification harness (`scripts/verify_documents.py`) should become an automated test.
**What:** Use `pytest` + `httpx.AsyncClient` with `TestClient(app)`. Test: POST `/auth/register`, POST `/auth/login`, GET `/auth/me`, POST `/documents/upload` (synthetic fixture), GET `/documents`, GET `/documents/{id}`. Verify `pytest tests/` passes.

---

#### TEST-3: `test(backend): add retrieval pipeline integration tests`

**Depends on:** TEST-2
**Why:** Retrieval is the core value of the system. It should be regression-tested.
**What:** Write integration tests for: hybrid retrieval returning non-empty results, reranking reducing candidate count, structured SQL retrieval returning price rows, graph retrieval returning supplier → contract paths. Use the synthetic corpus as a fixture.

---

#### TEST-4: `test(frontend): add Vitest unit tests for frontend utilities`

**Depends on:** nothing
**Why:** Frontend has zero tests. Start with utilities and store logic.
**What:** Add `vitest` to `devDependencies`. Write unit tests for: API client error handling, auth store login/logout state transitions, query parameter building. Verify `npm run test -- --run` passes.

---

#### TEST-5: `test(rag): convert golden dataset to automated regression suite`

**Depends on:** TEST-2
**Why:** The evaluation framework exists (`evaluation/runner.py`, `data/evaluation/golden_questions.json`). It runs manually via the API. It should run as an automated regression gate.
**What:** Write a pytest integration test that runs the golden question set via the evaluation runner, asserts retrieval recall@5 ≥ 0.6, asserts refusal rate on unanswerable questions ≥ 0.8. Baseline the current extractive-mode metrics.

---

### RAG Quality

#### RAG-1: `fix(retrieval): verify and fix Q3 multi-supplier comparison answer`

**Depends on:** TEST-3
**Why:** The audit identified that Q3 (compare Supplier A vs Supplier B) omits Supplier B's data from the generated answer. The structured comparison endpoint (`POST /compare`) is correct; the agent synthesis is the gap.
**What:** Inspect `agents/generation.py` and the comparison path in `agents/nodes.py`. Fix the multi-supplier context assembly so both suppliers appear in the extractive answer. Add a regression test.

---

#### RAG-2: `fix(retrieval): fix Q4 lowest-price-in-2025 temporal scoping`

**Depends on:** TEST-3
**Why:** The audit identified that Q4 (lowest price in 2025) does not name the supplier and leaks an irrelevant aggregation. Temporal filtering is implemented but not correctly applied in the structured retrieval path for this query type.
**What:** Trace the Q4 query through `retrieval/structured.py`. Fix the time-range filter application and the aggregation result formatting. Add a regression test.

---

#### RAG-3: `feat(ingestion): add backend Dockerfile and verify Docker build`

**Depends on:** RQ-1
**Why:** Unblocks production provider testing.
**What:** (Merged with RQ-1 if done together.) Verify `docker compose --profile app up --build` succeeds end-to-end.

---

### Infrastructure

#### INFRA-1: `build(docker): verify docker compose app profile end to end`

**Depends on:** RQ-1
**Why:** After the Dockerfile is created, verify the full compose stack actually starts and the API is reachable.
**What:** Run `docker compose --profile app up --build`. Verify `GET /api/v1/health` returns 200. Run `scripts/api_smoke.py` against the containerised API. Document any fixes needed.

---

#### INFRA-2: `build(db): verify alembic migration against postgresql`

**Depends on:** INFRA-1
**Why:** The single migration revision (`0001_initial_schema.py`) has never been applied to a live PostgreSQL instance.
**What:** Start the Docker postgres service. Set `DATABASE_URL` to the Postgres URL. Run `alembic upgrade head`. Verify no errors. Run `alembic downgrade base` and `alembic upgrade head` again. Document any schema differences vs the SQLite auto-create path.

---

#### INFRA-3: `chore(config): add production environment configuration guide`

**Depends on:** INFRA-1, INFRA-2
**Why:** Deployment docs currently describe what to set but not how to validate production readiness.
**What:** Add a production readiness checklist to `docs/deployment.md`: JWT secret rotation, `AUTO_CREATE_SCHEMA=false`, `APP_ENV=production`, CORS origins, rate limit tuning, provider validation via `/health`.

---

### CI/CD

#### CI-1: `ci(test): add test gate to GitHub Actions PR workflow`

**Depends on:** RQ-3, TEST-1, TEST-2
**Why:** Once unit and integration tests exist, they should gate pull requests.
**What:** Update `.github/workflows/pr.yml` to add a `test` job that runs `pytest` after lint and type check.

---

#### CI-2: `ci(docker): add Docker build validation to CI`

**Depends on:** RQ-1, CI-1
**Why:** The Docker build should be validated on every PR once the Dockerfile exists.
**What:** Add a `docker-build` job to `.github/workflows/pr.yml` that runs `docker build -f backend/Dockerfile .` and `docker build -f frontend/Dockerfile ./frontend`.

---

#### CI-3: `ci(security): add dependency vulnerability scanning`

**Depends on:** CI-1
**Why:** No dependency scanning currently exists.
**What:** Add `pip-audit` (Python) and `npm audit --audit-level=high` (Node) steps to the PR workflow. Gate on high/critical vulnerabilities.

---

### GitHub Governance

#### GOV-1: `chore(github): add CODEOWNERS file`

**Depends on:** nothing
**Why:** Defines required reviewers per path.
**What:** Create `.github/CODEOWNERS`. Assign `backend/app/security/` and `backend/app/providers/` to the security-sensitive reviewer. Document in `CONTRIBUTING.md`.

---

#### GOV-2: `chore(github): add pull request template`

**Depends on:** nothing
**Why:** Ensures PRs consistently describe what changed, how it was tested, and any gaps.
**What:** Create `.github/pull_request_template.md` with sections: Summary, Changes, Testing, Known Gaps.

---

#### GOV-3: `chore(github): add issue templates`

**Depends on:** nothing
**Why:** Consistent issue reporting for bugs and feature requests.
**What:** Create `.github/ISSUE_TEMPLATE/bug_report.md` and `.github/ISSUE_TEMPLATE/feature_request.md`.

---

### Feature Gaps (identified in audit)

#### FEAT-1: `feat(frontend): implement citation deep-link to document page viewer`

**Depends on:** TEST-2
**Why:** Citations currently display page number and document name but do not link to the page image in the document viewer. The `GET /documents/{id}/pages/{n}/image` endpoint exists.
**What:** In `AnswerView` (or equivalent citation component), make each citation a link to `/documents/{documentId}?page={pageNumber}`. Update `DocumentDetailPage` to accept a `?page=` query param and scroll to or highlight the relevant page.

---

#### FEAT-2: `feat(frontend): implement conversation history UI`

**Depends on:** FEAT-1
**Why:** The conversations API exists (`GET/POST /conversations`, `GET /conversations/{id}/messages`) but has no frontend consumer. The Ask page has no history.
**What:** Add a conversation list panel to the Ask page. Implement `POST /conversations` on new question, `GET /conversations` to list history, `GET /conversations/{id}/messages` to restore a conversation.

---

### Production

#### PROD-1: `feat(observability): configure OTEL exporter`

**Depends on:** INFRA-1
**Why:** Structured logging and DB-stored traces exist but no external exporter is configured.
**What:** Document and implement `OTEL_EXPORTER_OTLP_ENDPOINT` configuration. Add a Jaeger or similar service to `docker-compose.yml` for local observability.

---

#### PROD-2: `feat(observability): configure LangSmith tracing`

**Depends on:** PROD-1
**Why:** LangGraph agent traces are stored in the DB but LangSmith integration exists and is disabled.
**What:** Document how to enable `LANGSMITH_TRACING=true` and configure `LANGSMITH_API_KEY`. Add to the production readiness checklist.

---

*This roadmap will be updated as commits are completed. Do not mark tasks complete until the commit exists and its SHA is recorded above.*
