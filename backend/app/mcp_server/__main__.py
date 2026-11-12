"""Entry point for the EPI MCP server over stdio.

    MCP_ENABLED=true MCP_TENANT_ID=ten_... MCP_USER_EMAIL=tools@epi.local \
        python -m app.mcp_server

The process serves exactly one tenant and one account, configured by the
deployment. Nothing a client sends can change that.
"""

from __future__ import annotations

import sys

from app.mcp_server.guards import McpConfigError
from app.mcp_server.server import build_server


def main() -> int:
    try:
        server = build_server()
    except McpConfigError as exc:
        print(f"epi-mcp: {exc}", file=sys.stderr)
        return 2
    server.run("stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
