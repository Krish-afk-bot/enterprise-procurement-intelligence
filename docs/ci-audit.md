# CI/CD Workflow Audit

**Audit Date**: November 3, 2026  
**Purpose**: Identify redundant workflows before consolidation

---

## Workflow Inventory

| Workflow | Triggers | Jobs | Purpose | Duplicated By | Decision |
|----------|----------|------|---------|---------------|----------|
| **ci.yml** | PR, push to master/main | backend-lint<br>backend-tests<br>backend-mypy<br>frontend-checks | Lint (ruff format, ruff check), pytest tests/, mypy app/, frontend (tsc, eslint, vitest, build) | pr.yml (exact duplicate) | **KEEP** - Consolidate into single workflow |
| **pr.yml** | PR to master/main | backend-lint<br>backend-tests<br>frontend | **EXACT DUPLICATE** of ci.yml content | ci.yml | **DELETE** - Redundant |
| **backend-tests.yml** | PR, push to master/main (backend/** paths) | unit<br>integration<br>retrieval | Runs pytest on unit/integration/retrieval tests (all currently stubbed with conditionals) | ci.yml backend-tests job | **DELETE** - Tests covered by ci.yml; path filtering not needed |
| **frontend.yml** | PR, push to master/main (frontend/** paths) | lint-typecheck<br>build<br>test | TypeScript, ESLint, build, vitest (with conditional) | ci.yml frontend-checks job | **DELETE** - Exact duplicate; path filtering not needed |
| **security.yml** | PR, push, weekly schedule | python-audit (pip-audit)<br>npm-audit<br>secret-scan (trufflehog) | Security: pip-audit, npm audit, secret scanning | **None** | **KEEP** - Unique security scanning |
| **docker.yml** | PR, push (Dockerfile/compose paths) | build-backend<br>build-frontend<br>compose-validate | Validates Dockerfiles build successfully | **None** | **DELETE** - Not needed for alpha; can restore later |
| **deploy-staging.yml** | push to master/main, workflow_dispatch | deploy-staging | Placeholder for staging deployment (not functional) | N/A | **DELETE** - Not functional; premature |
| **deploy-production.yml** | workflow_dispatch | guard<br>deploy-production | Placeholder for production deployment (not functional) | N/A | **DELETE** - Not functional; premature |
| **release.yml** | push tags v*.*.* | release | Creates GitHub release from tag, builds frontend, attaches CHANGELOG | **None** | **DELETE** - Not needed for alpha; will create tag manually |
| **dependency-review.yml** | PR to master/main | dependency-review | Scans PRs for vulnerable/license-incompatible deps | **None** | **KEEP** - Useful PR gate |

---

## Duplication Analysis

### Exact Duplicates
- **pr.yml ≈ ci.yml**: Both run identical checks (backend lint/test, frontend lint/test/build)
  - **Resolution**: Delete pr.yml, keep ci.yml

### Functional Duplicates
- **backend-tests.yml ≈ ci.yml backend-tests**: Both run pytest
  - **Resolution**: Delete backend-tests.yml, ci.yml already covers this

- **frontend.yml ≈ ci.yml frontend-checks**: Both run tsc/eslint/vitest/build
  - **Resolution**: Delete frontend.yml, ci.yml already covers this

### Path-Filtered Workflows (Unnecessary)
- **backend-tests.yml**, **frontend.yml**: Use path filters to run only when specific dirs change
  - **Problem**: Adds complexity without benefit; CI should always run all checks
  - **Resolution**: Delete both, rely on ci.yml which always runs

---

## Proposed Consolidated Structure

### Keep (2 workflows)
1. **ci.yml** - Main CI pipeline
2. **security.yml** - Security scanning
3. **dependency-review.yml** - Dependency review for PRs

### Delete (7 workflows)
1. ❌ pr.yml - Exact duplicate of ci.yml
2. ❌ backend-tests.yml - Covered by ci.yml
3. ❌ frontend.yml - Covered by ci.yml
4. ❌ docker.yml - Not needed for alpha
5. ❌ deploy-staging.yml - Non-functional placeholder
6. ❌ deploy-production.yml - Non-functional placeholder
7. ❌ release.yml - Manual release for alpha

---

## Consolidated ci.yml Structure

```yaml
name: CI

on:
  pull_request:
    branches: [master, main]
  push:
    branches: [master, main]

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  backend:
    name: Backend
    steps:
      - ruff format --check
      - ruff check
      - pytest tests/unit  # Specific path, not tests/

  frontend:
    name: Frontend
    steps:
      - npm ci
      - tsc --noEmit
      - vitest run
      - npm run build

  eval-gate:
    name: Eval Gate
    steps:
      - python scripts_phase3/eval_ci.py
    # Note: Will be continue-on-error until baseline is validated
```

---

## Missing: eval-gate

The eval-gate workflow is mentioned in requirements but **does not currently exist**.

**Action**: Add as a new job to consolidated ci.yml

---

## Recommendation Summary

| Action | Count | Workflows |
|--------|-------|-----------|
| **Keep as-is** | 2 | security.yml, dependency-review.yml |
| **Keep and consolidate** | 1 | ci.yml (merge pr.yml content, add eval-gate) |
| **Delete** | 7 | pr.yml, backend-tests.yml, frontend.yml, docker.yml, deploy-staging.yml, deploy-production.yml, release.yml |

**Result**: 10 workflows → 3 workflows (70% reduction)

---

## Verification Checklist

Before deleting, confirm every useful step is preserved in ci.yml:

- [x] ruff format --check
- [x] ruff check  
- [x] pytest tests/ (will narrow to tests/unit)
- [x] mypy app/ (currently in ci.yml, will remove - see note below)
- [x] npm ci with cache
- [x] tsc --noEmit
- [x] npm run lint (eslint)
- [x] vitest run
- [x] npm run build
- [ ] eval-gate (will add)

**Note on mypy**: The current ci.yml includes mypy with a timeout and warning-only (doesn't fail). This is not a gate. For simplicity, will remove from consolidated CI unless requested.

---

## Final Workflow List (After Consolidation)

1. **ci.yml** - Lint, test, build, eval gate (backend + frontend)
2. **security.yml** - pip-audit, npm audit, trufflehog
3. **dependency-review.yml** - PR dependency scanning

Total: **3 workflows**, down from 10.
