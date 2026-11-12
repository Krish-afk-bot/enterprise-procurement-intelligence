"""Read-only audit of supplier names that look like prose rather than entities.

The extraction fix stops new records such as "the council" from being created,
but records written before the fix are still in the database. This script lists
them so an operator can review and merge them deliberately. It never deletes or
changes anything.

    python scripts/audit_graph_entities.py --db var/epi.db
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingestion.metadata import _looks_like_party_name  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="var/epi.db", help="SQLite database path")
    parser.add_argument("--limit", type=int, default=25, help="How many candidates to print")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output")
    args = parser.parse_args()

    path = Path(args.db)
    if not path.exists():
        print(f"database not found: {path}", file=sys.stderr)
        return 2

    connection = sqlite3.connect(path)
    try:
        rows = connection.execute(
            "SELECT id, name, tenant_id, source FROM suppliers ORDER BY name"
        ).fetchall()
    finally:
        connection.close()

    suspects = [row for row in rows if not _looks_like_party_name(row[1] or "")]
    payload = {
        "database": str(path),
        "suppliers": len(rows),
        "suspects": len(suspects),
        "candidates": [
            {"id": row[0], "name": row[1], "tenant_id": row[2], "source": row[3]}
            for row in suspects[: args.limit]
        ],
        "note": (
            "Review candidates only. Names are matched by a rule for capitalised, "
            "non-generic phrasing; foreign-language or all-lowercase supplier names "
            "can appear here and be legitimate."
        ),
    }
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"{payload['suppliers']} supplier record(s); {payload['suspects']} look like prose.")
    for candidate in payload["candidates"]:
        print(f"  {candidate['name']!r}  (source={candidate['source']}, tenant={candidate['tenant_id']})")
    print(payload["note"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
