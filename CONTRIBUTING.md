# Contributing to Enterprise Procurement Intelligence

Thank you for contributing. This document explains how to work with the codebase and submit changes.

---

## Prerequisites

- Python 3.11 or later
- Node.js 20 or later
- Git

See [docs/development.md](docs/development.md) for the full setup guide.

---

## Branch Conventions

- Base all branches on `main`.
- Use descriptive branch names: `feat/citation-deep-links`, `fix/ocr-onednn-flag`, `test/backend-unit-tests`.
- Never push directly to `main`. Open a pull request.

---

## Commit Conventions

This project uses [Conventional Commits](https://www.conventionalcommits.org/).

```
<type>(<scope>): <short description>

[optional body]

[optional footer]
```

### Allowed types

| Type       | When to use                                                  |
|------------|--------------------------------------------------------------|
| `feat`     | A new user-visible feature                                   |
| `fix`      | A bug fix                                                    |
| `docs`     | Documentation changes only                                   |
| `test`     | Adding or updating tests                                     |
| `refactor` | Code change that is neither a feature nor a bug fix          |
| `perf`     | Performance improvement                                      |
| `chore`    | Maintenance tasks, dependency updates, tooling               |
| `build`    | Build system or external dependency changes                  |
| `ci`       | CI/CD pipeline changes                                       |
| `security` | Security fixes or hardening                                  |

### Examples

```
feat(query): add citation deep-link to document viewer
fix(ocr): disable oneDNN flag on CPU-only builds
test(retrieval): add hybrid retrieval unit tests
chore(deps): pin sentence-transformers to 3.3.1
```

### Do not use

- `update`
- `changes`
- `final`
- `final2`
- `misc`
- `stuff`

---

## Pull Request Process

1. Open a draft PR early if you want early feedback.
2. Ensure the title follows Conventional Commits format.
3. Fill in the PR description: what changed, how it was tested, any known gaps.
4. All CI checks must pass before merging (once CI is configured).
5. Request review from at least one other contributor.

---

## Code Style

### Python

- Formatter: `ruff format` (line length 110, configured in `pyproject.toml`).
- Linter: `ruff check` with the rule set defined in `pyproject.toml`.
- Type checking: `mypy` (configuration in `pyproject.toml`).

Run locally:

```bash
cd backend
ruff format .
ruff check .
mypy app/
```

### TypeScript / Frontend

- Linter: `eslint` (configured in `frontend/`).
- Type checking: `tsc --noEmit`.

Run locally:

```bash
cd frontend
npm run lint
npm run typecheck
```

---

## Testing

The automated test suite is currently **planned but not yet implemented**.

Until it exists, use the manual verification scripts in `scripts/`:

```bash
# Backend API smoke test (requires running backend)
python scripts/api_smoke.py

# Document API verification
python scripts/verify_documents.py

# Full acceptance check
python scripts/acceptance_check.py
```

See [COMMITS.md](COMMITS.md) for the test implementation roadmap.

---

## Secrets Policy

- Never commit real secrets, API keys, passwords, or tokens.
- Use `.env` for local configuration. `.env` is in `.gitignore`.
- `.env.example` is the only committed environment file and must never contain real values.
- If you accidentally commit a secret, rotate it immediately and rewrite the commit before it is pushed.

---

## Questions

Open an issue or start a discussion in the repository.
