"""API smoke test.

Exercises every mounted router over HTTP against the configured database, using a
real bearer token minted for the local admin account. It prints the observed
status codes and a short extract of each payload, so a failure is visible rather
than swallowed.

Usage::

    python scripts/api_smoke.py            # read-only endpoints
    python scripts/api_smoke.py --write    # also run a query and a small evaluation
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.config.settings import get_settings  # noqa: E402
from app.db.session import dispose_engine, init_db, session_scope  # noqa: E402
from app.security.tokens import create_token  # noqa: E402
from app.services import auth as auth_service  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

READ_ENDPOINTS = [
    "/api/v1/health",
    "/api/v1/ready",
    "/api/v1/filters",
    "/api/v1/admin/stats",
    "/api/v1/admin/config",
    "/api/v1/admin/routing",
    "/api/v1/admin/health",
    "/api/v1/admin/indexing",
    "/api/v1/admin/datasources",
    "/api/v1/admin/audit?limit=3",
    "/api/v1/suppliers",
    "/api/v1/contracts",
    "/api/v1/products",
    "/api/v1/prices?limit=5",
    "/api/v1/compliance",
    "/api/v1/graph/overview",
    "/api/v1/graph/nodes?label=Supplier",
    "/api/v1/documents?limit=3",
    "/api/v1/evaluation/experiments",
    "/api/v1/evaluation/dataset",
    "/api/v1/evaluation/runs",
]

WRITE_ENDPOINTS = [
    ("POST", "/api/v1/search", {"query": "Industrial Laptop X200 price", "limit": 5, "rerank": False}),
    ("POST", "/api/v1/query", {"query": "What is Supplier A's current price for the Industrial Laptop X200?"}),
    ("POST", "/api/v1/compare", {"supplier_names": ["Northwind", "Helios"], "product_query": "Laptop"}),
    ("POST", "/api/v1/evaluation/runs", {"experiments": ["dense"], "max_questions": 2, "top_k": 5}),
]


async def main() -> int:
    parser = argparse.ArgumentParser(description="Exercise the HTTP API")
    parser.add_argument("--write", action="store_true", help="also run query/evaluation endpoints")
    parser.add_argument("--email", default="admin@epi.local")
    parser.add_argument("--json", action="store_true", help="print full payloads")
    args = parser.parse_args()

    import httpx

    from app.config.container import get_container

    settings = get_settings()
    await init_db()
    # ASGITransport does not run the app lifespan, so the provider container is
    # started explicitly here — the same startup path uvicorn uses.
    container = get_container()
    await container.startup()
    async with session_scope() as session:
        tenant = await auth_service.get_or_create_default_tenant(session, settings)
        user = await auth_service.get_user_by_email(session, tenant.id, args.email)
        if user is None:
            print(f"No user {args.email}: run the CLI ingest first.", file=sys.stderr)
            return 2
        token, _expires = create_token(
            settings, subject=user.id, tenant_id=user.tenant_id, role=user.role
        )
        headers = {"authorization": f"Bearer {token}"}

    from app.main import create_app

    app = create_app()
    failures: list[str] = []
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://smoke") as client:
        for path in READ_ENDPOINTS:
            response = await client.get(path, headers=headers)
            _report("GET", path, response, args.json)
            if response.status_code >= 400:
                failures.append(f"GET {path} -> {response.status_code}")
        if args.write:
            for method, path, payload in WRITE_ENDPOINTS:
                response = await client.post(path, headers=headers, json=payload)
                _report(method, path, response, args.json)
                if response.status_code >= 400:
                    failures.append(f"{method} {path} -> {response.status_code}")

    await container.shutdown()
    await dispose_engine()
    if failures:
        print("\nFAILURES:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("\nAll exercised endpoints responded successfully.")
    return 0


def _report(method: str, path: str, response, verbose: bool) -> None:
    try:
        payload = response.json()
    except Exception:  # noqa: BLE001
        payload = None
    summary = ""
    if isinstance(payload, dict):
        if "items" in payload:
            summary = f"items={len(payload.get('items') or [])} total={payload.get('total')}"
        elif "answer_text" in payload:
            summary = f"status={payload.get('status')} citations={len(payload.get('citations') or [])}"
        elif "columns" in payload:
            summary = f"columns={len(payload.get('columns') or [])}"
        else:
            summary = ", ".join(list(payload)[:6])
    elif isinstance(payload, list):
        summary = f"{len(payload)} item(s)"
    marker = "ok " if response.status_code < 400 else "ERR"
    print(f"[{marker}] {response.status_code:>3} {method:<4} {path}  {summary}")
    if verbose and payload is not None:
        print(json.dumps(payload, indent=2, default=str)[:4000])


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
