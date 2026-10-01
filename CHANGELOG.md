# Changelog

All notable changes to this project are documented here.

This project follows [Conventional Commits](https://www.conventionalcommits.org/)
and the format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Added

- GitHub Actions workflows: `ci.yml`, `backend-tests.yml`, `frontend.yml`,
  `security.yml`, `dependency-review.yml`, `docker.yml`, `release.yml`,
  `deploy-staging.yml`, `deploy-production.yml`
- GitHub governance: `CODEOWNERS`, `pull_request_template.md`,
  `ISSUE_TEMPLATE/bug_report.md`, `ISSUE_TEMPLATE/feature_request.md`,
  `dependabot.yml`
- Backend test scaffolding: `backend/tests/{unit,integration,retrieval,ingestion,security}/`
- Frontend test scaffolding: `frontend/tests/`
- `docs/rollback.md` — rollback and recovery procedures
- `scripts/repo_health.py` — local repository health check script
- `CHANGELOG.md` — this file

---

## [0.1.0] — 2026-10-02

### Added

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
