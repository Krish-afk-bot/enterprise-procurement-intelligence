"""Call all nine MCP tools over a real stdio session, plus negative cases.

Writes ``data/evaluation/benchmark_v4/mcp_report.json``.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BACKEND = Path(__file__).resolve().parents[1]
DB = BACKEND / "var" / "epi.db"
OUT = BACKEND.parent / "data" / "evaluation" / "benchmark_v4"


def db_ids() -> dict[str, str]:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    tenant = con.execute("select id from tenants limit 1").fetchone()[0]
    document = con.execute("select id from documents where status='indexed' limit 1").fetchone()[0]
    contract = con.execute("select id from contracts limit 1").fetchone()[0]
    supplier = con.execute(
        "select id from suppliers where tenant_id = ? limit 1", (tenant,)
    ).fetchone()[0]
    graph = sqlite3.connect(BACKEND / "var" / "graph.db")
    graph.row_factory = sqlite3.Row
    node = graph.execute("select label,key from graph_nodes limit 1").fetchone()
    con.close()
    return {
        "tenant": tenant,
        "document": document,
        "contract": contract,
        "supplier": supplier,
        "label": node["label"] if node else "Supplier",
        "key": node["key"] if node else "",
    }


async def main() -> int:
    ids = db_ids()
    env = {key: value for key, value in os.environ.items() if not key.startswith("MCP_")}
    env.update(
        {
            "MCP_ENABLED": "true",
            "MCP_TENANT_ID": ids["tenant"],
            "MCP_USER_EMAIL": "admin@epi.local",
            "MCP_ROLE": "admin",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONPATH": str(BACKEND),
        }
    )
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "app.mcp_server"], env=env, cwd=str(BACKEND)
    )
    calls = [
        ("search_documents", {"query": "tender", "limit": 5}),
        ("get_document", {"document_id": ids["document"]}),
        ("search_contracts", {"query": "contract", "limit": 5}),
        ("get_supplier_profile", {"supplier_id": ids["supplier"]}),
        ("get_contract_amendments", {"contract_id": ids["contract"]}),
        ("get_ingestion_status", {"limit": 5}),
        ("get_evaluation_metrics", {"limit": 5}),
        ("search_graph", {"label": ids["label"], "query": "", "limit": 5}),
        ("get_entity_neighbours", {"label": ids["label"], "key": ids["key"], "max_hops": 1}),
    ]
    results = []
    negatives = []
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            available = sorted(tool.name for tool in listed.tools)
            for name, arguments in calls:
                try:
                    response = await session.call_tool(name, arguments)
                    text = "".join(
                        getattr(block, "text", "") for block in (response.content or [])
                    )
                    parsed = json.loads(text) if text.strip().startswith(("{", "[")) else text
                    ok = not response.isError
                    results.append(
                        {
                            "tool": name,
                            "ok": ok,
                            "is_error": bool(response.isError),
                            "summary": (
                                {k: parsed[k] for k in list(parsed)[:6]}
                                if isinstance(parsed, dict)
                                else str(parsed)[:200]
                            ),
                        }
                    )
                except Exception as exc:  # noqa: BLE001
                    results.append({"tool": name, "ok": False, "error": f"{type(exc).__name__}: {exc}"})

            for name, arguments in [
                ("delete_everything", {}),
                ("get_document", {"document_id": "doc_does_not_exist"}),
                ("search_graph", {"label": "SecretTable", "query": "", "limit": 5}),
                ("search_documents", {"query": "tender", "limit": "not-a-number"}),
            ]:
                try:
                    response = await session.call_tool(name, arguments)
                    negatives.append(
                        {
                            "tool": name,
                            "arguments": arguments,
                            "rejected": bool(response.isError),
                        }
                    )
                except Exception as exc:  # noqa: BLE001
                    negatives.append(
                        {
                            "tool": name,
                            "arguments": arguments,
                            "rejected": True,
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )

    con = sqlite3.connect(DB)
    audit = con.execute(
        "select count(*) from audit_logs where resource_type='mcp_tool'"
    ).fetchone()[0]
    con.close()
    payload = {
        "available_tools": available,
        "expected_nine_present": len(available) == 9,
        "tool_calls": results,
        "successful": sum(1 for row in results if row.get("ok")),
        "total": len(results),
        "negative_cases": negatives,
        "audit_log_rows_for_mcp": audit,
        "not_tested": [
            "tenant mismatch (only one tenant exists and creating one would modify source data)",
            "rate-limit exhaustion (would require >60 calls in a minute against a read-only dev database)",
            "timeout (no deterministic slow tool in this environment)",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "mcp_report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("available_tools", "successful", "total", "negative_cases", "audit_log_rows_for_mcp")}, indent=2))
    return 0 if payload["successful"] == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
