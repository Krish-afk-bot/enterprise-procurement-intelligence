# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please **do not open a public issue**.

Instead, report it privately by opening a [GitHub Security Advisory](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing/privately-reporting-a-security-vulnerability) in this repository, or by emailing the maintainer directly if contact information is available in the repository.

Please include:

- A description of the vulnerability
- Steps to reproduce
- The potential impact
- Any suggested remediation

You can expect an acknowledgment within 5 business days.

---

## Scope

This policy covers:

- The FastAPI backend (`backend/`)
- The React/TypeScript frontend (`frontend/`)
- The authentication and RBAC system (`backend/app/security/`)
- The ingestion pipeline and document handling
- The Docker Compose configuration
- Any CI/CD configuration added in future

---

## Known Current Limitations

The following are known gaps that are not yet fixed. They are tracked in [COMMITS.md](COMMITS.md).

| Area | Status | Notes |
|------|--------|-------|
| Automated security scanning | Planned | No CI pipeline exists yet |
| Production secrets management | Not configured | `.env` approach only; no vault integration |
| Docker image scanning | Planned | App Docker profile does not currently build |
| Dependency vulnerability scanning | Planned | No automated tooling configured |
| Penetration testing | Not performed | Manual audit only |

---

## Secrets Policy

- The default `JWT_SECRET` in `.env.example` is intentionally labelled `dev-insecure-change-me`.
- Never deploy with the default JWT secret.
- Never commit `.env` to the repository.
- Never put real credentials in `.env.example`.
- The `.gitignore` blocks `.env` and `.env.*` (except `.env.example`).

---

## Supported Versions

This project is currently pre-production. There are no versioned releases. All security fixes are applied to `main`.

| Version | Supported |
|---------|-----------|
| `main`  | Yes       |

---

## Disclosure Policy

Once a fix is available, the vulnerability will be disclosed in a security advisory in this repository. There is no coordinated disclosure timeline at this stage; the project will move to a formal policy when it reaches production deployment.
