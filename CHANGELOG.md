# Changelog

All notable changes to this project are documented here.

This project follows [Conventional Commits](https://www.conventionalcommits.org/)
and the format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

---

## [0.1.0] — Phase 1 Stabilization — 2026-10-06

### Fixed

- **Security**: Added production startup guard — `validate_startup_security()` now raises `RuntimeError` if `APP_ENV=production` with a known-weak or short JWT secret; development mode logs a warning instead of failing.
- **Bug (F821)**: `neo4j.py` `traverse()` was passing undefined `key` instead of `start_key` to the Cypher query parameter dict.
- **Bug**: Ruff format and lint: 62 files reformatted, 72 lint issues fixed (25 unused imports, 21 import ordering, 16 datetime-timezone, 3 unused variables, and more).
- **Bug**: `Intent` and `Task` enums now use `StrEnum` instead of `(str, Enum)` (UP042).
- **Bug**: `ingestion_worker.py` unused `tenant_id` variable removed.
- **Dependency**: `email-validator` was used by `app/schemas/email.py` but was missing from `pyproject.toml` and `requirements.txt`. Added `email-validator>=2.1` to both files.

### Added

- **Tests — security**: `tests/security/test_startup_security.py` — 9 tests verifying production startup refuses weak JWT secrets.
- **Tests — integration**: `tests/integration/test_auth.py` — 14 tests covering user creation, authentication, token issuance, and account-enumeration protection.
- **Tests — retrieval regression**: `tests/retrieval/test_structured_retrieval.py` — 22 tests verifying supplier comparison includes all named suppliers (Issue A) and lowest-price query names supplier + product + year (Issue B).
- **Frontend — ESLint**: Added ESLint 9 (`eslint.config.js` flat config) with `typescript-eslint`, `eslint-plugin-react-hooks`, `globals`. `npm run lint` now passes with 0 errors.
- **Pytest**: Set `asyncio_default_fixture_loop_scope = "function"` to suppress pytest-asyncio deprecation warning.

### Changed

- **Python version**: Aligned `pyproject.toml`, CI workflows, and documentation to **Python 3.12** (the Dockerfile was already 3.12; CI said 3.11).
- **CI** (`ci.yml`): Updated to use `requirements.txt` for reproducible dependency install; removed "no tests yet" guard from backend-tests job; both backend and frontend jobs now run on Python 3.12 / Node 20.
- **CI** (`pr.yml`): Updated to Python 3.12; uses `requirements.txt`.
- **CI** (`docker.yml`): Removed "Dockerfile doesn't exist" guard (Dockerfile now present); added `requirements.txt` to path triggers.
- **Dockerfile** (`backend/Dockerfile`): Now installs from `requirements.txt` before the application source copy for better layer caching and reproducibility.
- **`requirements.txt`**: Added `email-validator==2.3.0`; improved header comment documenting the dependency strategy (pyproject.toml = authoritative with `>=`, requirements.txt = pinned snapshot for CI/Docker).
- **`.env.example`**: Clarified that `JWT_SECRET` is required in production with generation instructions; documents startup refusal behavior.
- **`package.json`** (frontend): Updated lint script from `eslint . --ext .ts,.tsx` to `eslint .` for ESLint 9 flat config.

### Total test count after Phase 1

- 86 unit tests (chunking, fusion, security tokens, query understanding, tokens)
- 9 security tests (startup JWT guard)
- 14 integration tests (auth service)
- 13 retrieval regression tests (supplier comparison, lowest-price query, citations)

**Total: 122 tests, all passing.**

---

## [0.0.6] — 2026-10-02

- Repository engineering baseline: `.gitignore`, `.editorconfig`,
  `.gitattributes`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`
- Project documentation: `README.md`, `docs/architecture.md`,
  `docs/development.md`, `docs/ci-cd.md`, `docs/deployment.md`
- Engineering roadmap: `COMMITS.md`

### Notes

- This is the first tracked version. The application itself was implemented
  prior to this release and is described in detail in `audit.md`.
- LLM and VLM endpoints are not configured. The system runs in extractive mode.
- Docker app profile is not functional (`backend/Dockerfile` missing).
- Automated tests are absent. Manual verification scripts in `scripts/` pass.

---

[Unreleased]: https://github.com/Krish-afk-bot/enterprise-procurement-intelligence/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Krish-afk-bot/enterprise-procurement-intelligence/releases/tag/v0.1.0
