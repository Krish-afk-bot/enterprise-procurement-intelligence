#!/usr/bin/env python3
"""
repo_health.py — Local repository health check.

Checks that the repository is in a clean, expected state and reports
any gaps or issues. Run from the repository root.

Usage:
    python scripts/repo_health.py

Exit code 0 = all checks passed.
Exit code 1 = one or more checks failed (details printed to stdout).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

PASS = "\033[32m✓\033[0m"
FAIL = "\033[31m✗\033[0m"
WARN = "\033[33m⚠\033[0m"
INFO = "\033[34mℹ\033[0m"


def check(label: str, ok: bool, message: str = "", warning: bool = False) -> bool:
    icon = PASS if ok else (WARN if warning else FAIL)
    suffix = f" — {message}" if message else ""
    print(f"  {icon}  {label}{suffix}")
    return ok


def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=cwd or ROOT
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def section(title: str) -> None:
    print(f"\n{title}")
    print("─" * len(title))


def main() -> int:
    failures = 0

    print("Enterprise Procurement Intelligence — Repository Health Check")
    print("=" * 62)

    # ---------------------------------------------------------------- git
    section("Git")
    code, branch = run(["git", "branch", "--show-current"])
    check("On a branch", code == 0, branch)

    code, out = run(["git", "status", "--porcelain"])
    staged = [l for l in out.splitlines() if l and not l.startswith("??")]
    check("No staged/modified tracked files", len(staged) == 0,
          f"{len(staged)} changed file(s)" if staged else "")

    code, remote = run(["git", "remote", "get-url", "origin"])
    check("origin remote configured", code == 0, remote if code == 0 else "not set")

    # ---------------------------------------------------------------- required files
    section("Required files")
    required = [
        ".gitignore",
        ".editorconfig",
        ".gitattributes",
        "README.md",
        "COMMITS.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        ".env.example",
        "docker-compose.yml",
        "backend/pyproject.toml",
        "frontend/package.json",
        "docs/architecture.md",
        "docs/development.md",
        "docs/ci-cd.md",
        "docs/deployment.md",
        "docs/rollback.md",
        ".github/CODEOWNERS",
        ".github/dependabot.yml",
        ".github/pull_request_template.md",
        ".github/ISSUE_TEMPLATE/bug_report.md",
        ".github/ISSUE_TEMPLATE/feature_request.md",
        ".github/workflows/ci.yml",
        ".github/workflows/backend-tests.yml",
        ".github/workflows/frontend.yml",
        ".github/workflows/security.yml",
        ".github/workflows/docker.yml",
        ".github/workflows/release.yml",
        ".github/workflows/deploy-staging.yml",
        ".github/workflows/deploy-production.yml",
        ".github/workflows/dependency-review.yml",
    ]
    for rel in required:
        exists = (ROOT / rel).exists()
        if not exists:
            failures += 1
        check(rel, exists)

    # ---------------------------------------------------------------- sensitive files absent from git
    section("Secrets not committed")
    sensitive = [".env", ".fb_token"]
    for rel in sensitive:
        path = ROOT / rel
        if not path.exists():
            check(rel, True, "not present")
            continue
        code, out = run(["git", "ls-files", rel])
        tracked = bool(out.strip())
        if tracked:
            failures += 1
        check(f"{rel} not tracked by git", not tracked,
              "TRACKED — potential secret exposure!" if tracked else "")

    # ---------------------------------------------------------------- backend
    section("Backend")
    dockerfile = (ROOT / "backend" / "Dockerfile").exists()
    check(
        "backend/Dockerfile exists",
        dockerfile,
        "MISSING — Docker app profile will fail. See COMMITS.md RQ-1.",
        warning=not dockerfile,
    )
    if not dockerfile:
        failures += 1  # treat as hard failure

    tests_exist = any((ROOT / "backend" / "tests").rglob("test_*.py"))
    check(
        "backend/tests/ has test files",
        tests_exist,
        "No tests written yet. See COMMITS.md TEST-1." if not tests_exist else "",
        warning=not tests_exist,
    )

    code, _ = run(["python", "-c", "import app"], cwd=ROOT / "backend")
    check("backend package importable", code == 0,
          "Run: pip install -e backend/" if code != 0 else "")

    # ---------------------------------------------------------------- frontend
    section("Frontend")
    node_modules = (ROOT / "frontend" / "node_modules").exists()
    check("frontend/node_modules exists", node_modules,
          "Run: cd frontend && npm install" if not node_modules else "")

    dist = (ROOT / "frontend" / "dist").exists()
    check("frontend/dist exists (built)", dist,
          "Run: cd frontend && npm run build" if not dist else "",
          warning=not dist)

    # ---------------------------------------------------------------- environment
    section("Environment")
    env_file = (ROOT / ".env").exists()
    check(
        ".env file present",
        env_file,
        "Copy .env.example to .env and configure." if not env_file else "",
        warning=not env_file,
    )

    code, db_url = run(["python", "-c",
        "from app.config.settings import get_settings; print(get_settings().DATABASE_URL)"],
        cwd=ROOT / "backend")
    if code == 0:
        check("DATABASE_URL configured", True, db_url[:60])
    else:
        check("DATABASE_URL readable", False, "Could not read settings", warning=True)

    # ---------------------------------------------------------------- summary
    print(f"\n{'=' * 62}")
    if failures == 0:
        print(f"{PASS}  All checks passed.")
    else:
        print(f"{FAIL}  {failures} check(s) failed. Review the output above.")

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
