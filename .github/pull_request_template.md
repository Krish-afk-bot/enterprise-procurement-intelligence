## Summary

<!-- One or two sentences describing what this PR does and why. -->

## Changes

<!-- List the files / components changed and what was done to each. -->

-
-
-

## Type of change

- [ ] `feat` — new user-visible feature
- [ ] `fix` — bug fix
- [ ] `docs` — documentation only
- [ ] `test` — adding or updating tests
- [ ] `refactor` — code change that is neither a feature nor a bug fix
- [ ] `perf` — performance improvement
- [ ] `chore` — maintenance, tooling, dependencies
- [ ] `build` — build system changes
- [ ] `ci` — CI/CD pipeline changes
- [ ] `security` — security fix or hardening

## Testing

<!-- Describe how this was tested. What scripts / tests were run? -->

- [ ] `python scripts/api_smoke.py` passes
- [ ] `python scripts/verify_documents.py` passes (29/29)
- [ ] `cd frontend && npm run typecheck` passes
- [ ] `cd frontend && npm run build` passes
- [ ] `cd backend && ruff check .` passes
- [ ] Backend unit tests pass (once they exist)
- [ ] Other: <!-- describe -->

## Security checklist

- [ ] No secrets or credentials committed
- [ ] `.env` is not committed
- [ ] New dependencies reviewed for known vulnerabilities
- [ ] No new endpoints bypass RBAC
- [ ] No user-controlled data reaches the LLM context without sanitisation

## Known gaps / follow-up

<!-- Anything intentionally left out of this PR that should be addressed later. -->

## Related issues

<!-- Closes #<issue number> -->
