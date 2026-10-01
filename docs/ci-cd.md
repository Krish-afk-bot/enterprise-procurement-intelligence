# CI/CD Pipeline

This document describes the current state of CI/CD for the Enterprise Procurement Intelligence platform and the planned pipeline.

---

## Current State

**There is no automated CI/CD pipeline.** No GitHub Actions workflows exist. No linting, type checking, or test gates run automatically on pull requests.

The current safety net consists of the manual verification scripts in `scripts/`:

| Script | What it checks |
|---|---|
| `scripts/api_smoke.py` | Auth, health, and key API endpoints |
| `scripts/verify_documents.py` | 29 document API assertions |
| `scripts/acceptance_check.py` | End-to-end acceptance flows |
| `scripts/final_verification.py` | Comprehensive manual verification harness |

These run manually against a locally running backend. They are not gated on any commit or pull request.

---

## Intended Pipeline (PLANNED)

The following pipeline is the target. None of it is implemented yet. Components are marked **PLANNED**.

### Pull Request Pipeline

```
PR opened / push to branch
           │
           ▼
  ┌─────────────────────┐
  │  Formatting / Lint  │  PLANNED
  │  ruff format --check │
  │  ruff check .        │
  │  eslint              │
  └──────────┬──────────┘
             │
             ▼
  ┌─────────────────────┐
  │   Type Checking     │  PLANNED
  │   mypy app/         │
  │   tsc --noEmit      │
  └──────────┬──────────┘
             │
             ▼
  ┌─────────────────────┐
  │   Backend Unit      │  PLANNED (tests not yet written)
  │   Tests             │
  │   pytest tests/     │
  └──────────┬──────────┘
             │
             ▼
  ┌─────────────────────┐
  │   Frontend Tests    │  PLANNED (tests not yet written)
  │   vitest --run      │
  └──────────┬──────────┘
             │
             ▼
  ┌─────────────────────┐
  │   Integration       │  PLANNED
  │   Tests             │
  └──────────┬──────────┘
             │
             ▼
  ┌─────────────────────┐
  │   RAG Regression    │  PLANNED
  │   Tests             │
  │   (golden dataset)  │
  └──────────┬──────────┘
             │
             ▼
  ┌─────────────────────┐
  │   Security Checks   │  PLANNED
  │   pip-audit         │
  │   npm audit         │
  │   secret scanning   │
  └──────────┬──────────┘
             │
             ▼
  ┌─────────────────────┐
  │   Docker Build      │  PLANNED (backend/Dockerfile missing)
  │   Validation        │
  └──────────┬──────────┘
             │
             ▼
  PR checks pass → ready to merge
```

### Main Branch Pipeline (PLANNED)

```
Merge to main
      │
      ▼
  All PR checks (re-run)
      │
      ▼
  Build Docker images
      │
      ▼
  Push to registry
      │
      ▼
  Deploy to staging
      │
      ▼
  Smoke test staging
      │
      ▼
  Deploy to production (manual approval gate)
```

---

## Planned Tooling

| Area | Tooling | Status |
|---|---|---|
| Python linting / formatting | ruff (already configured in `pyproject.toml`) | Config exists, no CI yet |
| Python type checking | mypy (already configured) | Config exists, no CI yet |
| Frontend linting | eslint (already in `package.json` scripts) | Config exists, no CI yet |
| Frontend type checking | tsc (already in `package.json` scripts) | Config exists, no CI yet |
| Backend unit tests | pytest + pytest-asyncio (in `pyproject.toml[eval]`) | Dep declared, no tests written |
| Frontend tests | vitest (not yet added) | Not yet added |
| API / integration tests | pytest + httpx TestClient | Not yet written |
| RAG regression tests | custom harness (golden dataset exists) | Manual only |
| Secret scanning | GitHub secret scanning / trufflehog | Not configured |
| Dependency scanning | pip-audit + npm audit | Not configured |
| Docker image scanning | trivy | Not configured |
| CI platform | GitHub Actions | No workflows yet |

---

## CI Gates Policy (PLANNED)

When CI is implemented, the following gates will block merges:

1. Formatting check must pass (zero ruff / eslint format violations).
2. Lint must pass (zero ruff / eslint errors).
3. Type checks must pass (mypy and tsc both clean).
4. All unit tests must pass.
5. All integration tests must pass.
6. RAG regression suite must not regress below the baseline metric thresholds.
7. No new high/critical security vulnerabilities.
8. Docker build must succeed.

---

## Next Steps

See [COMMITS.md](../COMMITS.md) for the planned sequence of engineering commits that will implement this pipeline incrementally.

Priority order:

1. Add `backend/Dockerfile` (unblocks Docker validation and the app compose profile).
2. Write first backend unit tests (unblocks the test gate).
3. Add GitHub Actions PR workflow with lint + type check gates.
4. Add test gate to the PR workflow.
5. Add RAG regression gate.
6. Add security scanning.
7. Add staging deployment workflow.
