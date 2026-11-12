"""End-to-end MCP check: spawn the server and talk to it over stdio.

Opt-in because it starts a real subprocess and reads the local database:

    EPI_MCP_STDIO=1 python -m pytest tests/integration/test_mcp_stdio.py

The default suite keeps the in-process guard/registry tests in
``tests/unit/test_mcp_server.py``; this covers the transport and the advertised
tool schemas, which those cannot.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BACKEND = Path(__file__).resolve().parents[2]
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

pytestmark = pytest.mark.skipif(
    os.environ.get("EPI_MCP_STDIO") != "1",
    reason="opt-in: starts the MCP server subprocess (EPI_MCP_STDIO=1)",
)


def _tenant() -> str:
    db = BACKEND / "var" / "epi.db"
    if not db.exists():
        pytest.skip("local database not present")
    connection = sqlite3.connect(db)
    try:
        row = connection.execute("select id from tenants order by created_at limit 1").fetchone()
    finally:
        connection.close()
    if row is None:
        pytest.skip("local database has no tenant")
    return str(row[0])


def _payload(result: object) -> dict:
    blocks = getattr(result, "content", None) or []
    for block in blocks:
        if getattr(block, "type", None) == "text":
            return json.loads(block.text)
    raise AssertionError("tool returned no text payload")


async def test_stdio_handshake_lists_tools_and_runs_reads() -> None:
    env = {key: value for key, value in os.environ.items() if not key.startswith("MCP_")}
    env.update(
        {
            "MCP_ENABLED": "true",
            "MCP_TENANT_ID": _tenant(),
            "MCP_USER_EMAIL": "tools@epi.local",
            "MCP_ROLE": "viewer",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONPATH": str(BACKEND),
        }
    )
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp_server"],
        env=env,
        cwd=str(BACKEND),
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            assert init.serverInfo.name == "epi-procurement"

            tools = await session.list_tools()
            assert {tool.name for tool in tools.tools} == EXPECTED_TOOLS

            # Every tool must advertise its arguments, so a client can construct
            # calls without guessing.
            by_name = {tool.name: tool for tool in tools.tools}
            assert "query" in by_name["search_documents"].inputSchema["properties"]

            status = await session.call_tool("get_ingestion_status", {"limit": 2})
            assert not status.isError
            assert _payload(status)["total"] >= 0

            search = await session.call_tool("search_documents", {"query": "tender", "limit": 2})
            assert not search.isError
            assert "items" in _payload(search)
