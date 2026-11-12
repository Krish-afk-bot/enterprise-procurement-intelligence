"""Verify the MCP server through a real client session over stdio.

This is the check the unit tests cannot make: it spawns ``python -m app.mcp_server``
as a separate process, performs the protocol handshake, lists the tools the server
actually advertises, and calls two of them over the wire.

    python scripts/verify_mcp_stdio.py --tenant ten_... [--role admin]

The tenant defaults to the only tenant in ``var/epi.db``. Exit status is 0 only if
the handshake, the tool list and both calls succeed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sqlite3
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BACKEND = Path(__file__).resolve().parents[1]
EXPECTED_TOOLS = {
    "search_documents",
    "get_document",
    "search_contracts",
    "get_supplier_profile",
    "get_contract_amendments",
    "get_ingestion_status",
    "get_evaluation_metrics",
    "search_graph",
    "get_entity_neighbours",
}


def default_tenant(db: Path) -> str:
    connection = sqlite3.connect(db)
    try:
        row = connection.execute("select id from tenants order by created_at limit 1").fetchone()
    finally:
        connection.close()
    if row is None:
        raise SystemExit("no tenant found in the local database; pass --tenant")
    return str(row[0])


def server_env(tenant: str, email: str, role: str) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("MCP_")}
    env.update(
        {
            "MCP_ENABLED": "true",
            "MCP_TENANT_ID": tenant,
            "MCP_USER_EMAIL": email,
            "MCP_ROLE": role,
            "PYTHONIOENCODING": "utf-8",
            "PYTHONPATH": str(BACKEND),
        }
    )
    return env


def payload(result: object) -> str:
    """The text of an MCP call result, whatever the content block shape."""
    blocks = getattr(result, "content", None) or []
    texts = [block.text for block in blocks if getattr(block, "type", None) == "text"]
    return texts[0] if texts else json.dumps({"content": str(result)})


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", default=None)
    parser.add_argument("--email", default="tools@epi.local")
    parser.add_argument("--role", default="admin")
    args = parser.parse_args()

    tenant = args.tenant or default_tenant(BACKEND / "var" / "epi.db")
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp_server"],
        env=server_env(tenant, args.email, args.role),
        cwd=str(BACKEND),
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print(f"handshake: server={init.serverInfo.name} version={init.serverInfo.version}")

            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            print(f"tools: {len(names)} -> {', '.join(sorted(names))}")
            missing = EXPECTED_TOOLS - names
            if missing:
                print(f"FAIL: missing tools {sorted(missing)}", file=sys.stderr)
                return 1

            status = await session.call_tool("get_ingestion_status", {"limit": 2})
            status_body = json.loads(payload(status))
            print(f"get_ingestion_status: {status_body.get('total')} jobs")
            if status.isError:
                print(f"FAIL: get_ingestion_status errored: {payload(status)}", file=sys.stderr)
                return 1

            search = await session.call_tool("search_documents", {"query": "tender", "limit": 3})
            search_body = json.loads(payload(search))
            print(f"search_documents: {search_body.get('total')} results")
            if search.isError:
                print(f"FAIL: search_documents errored: {payload(search)}", file=sys.stderr)
                return 1

            if args.role != "viewer":
                graph = await session.call_tool(
                    "search_graph", {"label": "Supplier", "query": "e", "limit": 3}
                )
                if graph.isError:
                    print(f"FAIL: search_graph errored: {payload(graph)}", file=sys.stderr)
                    return 1
                graph_body = json.loads(payload(graph))
                print(f"search_graph: {graph_body.get('total')} suppliers")
                if not graph_body.get("items"):
                    print("FAIL: no graph entities returned", file=sys.stderr)
                    return 1
                node = graph_body["items"][0]
                neighbours = await session.call_tool(
                    "get_entity_neighbours",
                    {"label": node["label"], "key": node["key"], "max_hops": 2},
                )
                if neighbours.isError:
                    print(f"FAIL: neighbours errored: {payload(neighbours)}", file=sys.stderr)
                    return 1
                neighbour_body = json.loads(payload(neighbours))
                print(f"get_entity_neighbours: {neighbour_body.get('total')} edges")

            # A tool the role may not use must be refused on the wire, not just
            # in the guard's own unit test.
            if args.role == "viewer":
                for name, arguments in (
                    ("get_supplier_profile", {"supplier_id": "sup_missing"}),
                    ("search_graph", {"label": "Supplier", "query": "e", "limit": 1}),
                ):
                    denied = await session.call_tool(name, arguments)
                    text = payload(denied).lower()
                    if not denied.isError and "permission" not in text:
                        print(f"FAIL: viewer was not refused {name}: {text[:200]}", file=sys.stderr)
                        return 1
                print("viewer refusal: enforced for supplier and graph tools")

    print("MCP_STDIO_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
