# v0.1.0-alpha Release Preparation Report

**Date**: 2026-11-03  
**Branch**: `release/v0.1.0-alpha` (created from `master`)  
**Worktree**: `C:\Users\user\OneDrive\Desktop\Sprint2-ci-release`

## Summary

Prepared v0.1.0-alpha release with simplified CI/CD and comprehensive documentation of known limitations. CI consolidated from 10 workflows to 3, with 7 redundant workflows deleted.

## Changes Made

### 1. CI/CD Consolidation ✅

**Workflows Kept (3)**:
- `ci.yml` - Comprehensive backend (lint, tests, mypy) + frontend (lint, typecheck, build, test)
- `security.yml` - Security scanning (pip-audit, npm-audit, trufflehog)
- `dependency-review.yml` - PR dependency scanning

**Workflows Deleted (7)**:
- `pr.yml` - Exact duplicate of ci.yml
- `backend-tests.yml` - Redundant with ci.yml backend jobs
- `frontend.yml` - Redundant with ci.yml frontend jobs
- `docker.yml` - No Docker deployment, builds unused
- `deploy-staging.yml` - Placeholder only, no implementation
- `deploy-production.yml` - Placeholder only, no implementation
- `release.yml` - Premature for alpha, can add when needed

**Rationale**: Full audit in `docs/ci-audit.md`

**Code reduction**: -904 lines, +333 lines (net -571 lines)

### 2. Release Documentation ✅

**CHANGELOG.md**:
- v0.1.0-alpha release notes with feature highlights
- Current performance metrics (68.3% answer correctness, 47.8% refusal precision)
- Known limitations section with over-refusal issue (52% false refusal rate)
- What's Next roadmap with evaluation improvement phases
- Feedback guidelines for alpha testers

**Alpha Feedback Template**:
- Created `.github/ISSUE_TEMPLATE/alpha_feedback.md`
- Structured feedback form for testers covering:
  - Document ingestion and question answering
  - Over-refusal and under-refusal examples
  - Citation quality
  - Performance and UI/UX
- Links to known limitations in CHANGELOG and docs/RESULTS.md

### 3. .gitignore Verification ✅

Confirmed proper exclusions already in place:
- ✅ `.fb_token` and `*.fb_token` (Freebuff IDE artifacts)
- ✅ `backend/var/` (runtime state, vector index, databases)
- ✅ `.cache/`, model weight caches, `.ruff_cache/`, `.mypy_cache/`
- ✅ `.freebuff/` directory
- ✅ `data/evaluation/runs/` and `data/evaluation/outputs/` (generated eval results)

## Local CI Check

### Backend Tests (master branch)
```
Status: 18 FAILED, 293 PASSED, 6 SKIPPED
```

**Failed tests** (all in `tests/ingestion/`):
- Checkpoint1: candidate version persistence, active safety invariant (2 failures)
- Checkpoint2: version isolation, durable checkpoint tracking (3 failures)
- Checkpoint3: activation, CAS operations, outbox reconciliation (13 failures)

**Analysis**: These failures are expected on `master` branch. The ingestion versioning system was implemented in Phase 7.3 (commit `50d0947`) which is ahead of origin/master. These tests will pass once Phase 2 work is merged.

**Decision**: Document as known limitation for alpha. Tests pass on `phase-2-pipeline-fixes` branch where development work happened.

### V2 Evaluation Framework
- **Status**: Not available on master branch
- **Location**: V2 eval framework (`eval_v2.py`, `V2Runner`, analysis scripts) exists only on `phase-2-pipeline-fixes`
- **Impact**: eval-gate.yml workflow cannot run on this branch
- **Recommendation**: Merge phase-2-pipeline-fixes before cutting release tag, OR note in CHANGELOG that eval-gate will be added in next release

## Branch Status

```
Current branch: release/v0.1.0-alpha
Commits ahead of origin/master: 2
  - f76cfcb: feat: prepare v0.1.0-alpha release (this work)
  - 50d0947: feat(ingestion): versioned procurement data (from phase-2-pipeline-fixes)

Working tree: clean
```

## Required GitHub Status Checks

**Action needed**: If your repository has branch protection rules requiring specific status checks, update them to reflect the consolidated workflows:

**Old checks to remove**:
- `Backend — Tests` (from pr.yml or backend-tests.yml)
- `Frontend — Lint, Tests & Build` (from frontend.yml)
- `backend-lint`, `backend-tests`, `backend-mypy` (from backend-tests.yml)
- `frontend-checks` (from frontend.yml)

**New checks to require**:
- `Backend — Lint & Format` (from ci.yml)
- `Backend — Tests` (from ci.yml)
- `Backend — mypy` (from ci.yml)
- `Frontend — Lint, Tests & Build` (from ci.yml)
- `security` (from security.yml, if desired)

## Next Steps

### Before Tagging

1. **Merge evaluation work** (recommended):
   ```bash
   # Option A: Merge phase-2-pipeline-fixes into release branch
   git merge phase-2-pipeline-fixes --no-ff -m "feat: merge evaluation improvements"
   
   # Option B: Cherry-pick specific commits
   git cherry-pick <eval-commit-range>
   ```

2. **Run full test suite** on merged branch to confirm all tests pass

3. **Update CHANGELOG.md** to reflect whether eval-gate is included

### Tagging and Release

```bash
# Create annotated tag
git tag -a v0.1.0-alpha -m "v0.1.0-alpha: Initial alpha release

First functional release of Enterprise Procurement Intelligence system.

Highlights:
- Hybrid retrieval with cross-encoder reranking
- Query understanding with intent classification
- LLM-powered answer generation with citation binding
- Coverage and grounding verification
- 130-question evaluation framework (90 dev / 40 held-out)

Known limitations:
- Over-refusal: ~52% false refusal rate (primary improvement target)
- Citation precision: 54.5%
- Retrieval recall@10: 73.4%
- No production deployment infrastructure

See CHANGELOG.md for full details."

# Push branch and tag
git push origin release/v0.1.0-alpha
git push origin v0.1.0-alpha

# Create GitHub release
gh release create v0.1.0-alpha \
  --title "v0.1.0-alpha: Initial Alpha Release" \
  --notes-file CHANGELOG.md \
  --prerelease
```

### After Release

1. **Update master branch** (if release branch has new work):
   ```bash
   git checkout master
   git merge release/v0.1.0-alpha --ff-only
   git push origin master
   ```

2. **Update branch protection rules** to require new consolidated workflow checks

3. **Monitor alpha feedback** via GitHub Issues with `alpha-feedback` label

4. **Continue evaluation improvement workflow** on `phase-2-pipeline-fixes`:
   - Wait for oracle evaluation to complete (~70% done)
   - Run Phase 3 analysis (over-refusal diagnostics)
   - Implement targeted fixes
   - Validate with paired bootstrap tests
   - Report on held-out set

## Files Changed

### Created
- `CHANGELOG.md` - Release notes and known limitations
- `.github/ISSUE_TEMPLATE/alpha_feedback.md` - Structured feedback template
- `docs/ci-audit.md` - CI consolidation rationale
- `docs/release-prep-report.md` - This document

### Deleted
- 7 workflow files (904 lines)

### Modified
- None (all changes are additions or deletions)

## Commit Summary

```
commit f76cfcb5eebd229944c756b2d7cf6a38c001606f
Author: Krish-afk-bot <krishagarwal52139@gmail.com>
Date:   Tue Nov 3 01:18:24 2026 +0530

feat: prepare v0.1.0-alpha release

- Delete 7 redundant workflows
- Keep 3 essential workflows
- Add CHANGELOG.md with v0.1.0-alpha release notes
- Add alpha feedback issue template
- Document CI/CD consolidation rationale

10 files changed, 333 insertions(+), 904 deletions(-)
```

## Recommendations

### For Alpha Release (Now)

✅ **Can proceed** with tagging `v0.1.0-alpha` on this branch if:
- Alpha users don't need eval-gate workflow
- 18 ingestion test failures are acceptable for alpha (document in release notes)
- Focus is on RAG functionality testing, not versioned ingestion testing

⚠️ **Should merge phase-2 first** if:
- Want all tests passing on release branch
- Want eval-gate included for continuous quality monitoring
- Want to show evaluation improvements in release notes

### For Production Release (Later)

Must have before v1.0.0:
- All tests passing (merge phase-2-pipeline-fixes)
- Eval-gate workflow with quality thresholds
- Over-refusal issue resolved (<10% false refusal rate)
- Citation precision >80%
- Production deployment workflows
- Authentication/authorization hardening
- Rate limiting and monitoring

## Status

✅ **Release preparation complete**  
⏸️ **Awaiting decision**: Merge phase-2-pipeline-fixes before tagging, or proceed with alpha as-is?

