"""A small, documented Cypher subset.

The local graph provider executes this subset so GraphRAG works without Neo4j;
the Neo4j provider runs the identical query string as real Cypher. Anything
outside the grammar raises ``UnsupportedQueryError`` rather than silently
returning wrong rows.

Grammar::

    MATCH (v:Label {key: $param})                              # anchored start node
          ( -[:REL|REL2]  (v2:Label)? )*                       # fixed relationship hops
       or ( -[:REL*1..2] -> (v2:Label)? )                      # variable-length hop range
    WHERE v2.name CONTAINS $term | v2.prop = $param
    RETURN v, v2, r                                            # variables + path relationships
    LIMIT 10
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.errors import UnsupportedQueryError

_NODE_RE = re.compile(
    r"\(\s*(?P<var>[A-Za-z_]\w*)?\s*(?::\s*(?P<label>[A-Za-z_]\w*))?"
    r"\s*(?:\{\s*(?P<props>[^}]*)\s*\})?\s*\)"
)
_REL_RE = re.compile(
    r"-\[\s*(?::\s*(?P<types>[A-Za-z_|\w\s]*?))?"
    r"\s*(?:\*\s*(?P<min>\d+)?\s*(?:\.\.\s*(?P<max>\d+))?)?\s*\]->"
)
_WHERE_RE = re.compile(
    r"(?P<var>[A-Za-z_]\w*)\.(?P<prop>[A-Za-z_]\w*)\s*(?P<op>CONTAINS|=|<>|>=|<=|>|<)\s*(?P<value>\$\w+|'[^']*'|\"[^\"]*\"|[\w.@:-]+)",
    re.IGNORECASE,
)
_RETURN_RE = re.compile(r"RETURN\s+(?P<items>[A-Za-z_][\w,\s.]*)", re.IGNORECASE)
_LIMIT_RE = re.compile(r"LIMIT\s+(?P<limit>\d+)", re.IGNORECASE)


@dataclass(slots=True)
class NodePattern:
    var: str
    label: str | None = None
    props: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class HopPattern:
    var: str
    label: str | None = None
    types: list[str] = field(default_factory=list)
    min_hops: int = 1
    max_hops: int = 1


@dataclass(slots=True)
class WhereClause:
    var: str
    prop: str
    op: str
    value: str


@dataclass(slots=True)
class ReadQueryPlan:
    start: NodePattern
    hops: list[HopPattern]
    where: list[WhereClause] = field(default_factory=list)
    returns: list[str] = field(default_factory=list)
    limit: int = 25


def _parse_props(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    props: dict[str, str] = {}
    for part in raw.split(","):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        props[key.strip()] = value.strip().strip("'\"")
    return props


def parse_read_query(query: str) -> ReadQueryPlan:
    """Parse the supported Cypher subset or raise ``UnsupportedQueryError``."""
    text = " ".join(query.split())
    if not text.upper().startswith("MATCH"):
        raise UnsupportedQueryError("The local graph provider only executes MATCH ... RETURN read queries.")

    match_section = text
    for marker in ("WHERE", "RETURN", "LIMIT"):
        index = match_section.upper().find(marker)
        if index != -1:
            match_section = match_section[:index]
            break
    match_section = match_section[len("MATCH") :]

    node_matches = list(_NODE_RE.finditer(match_section))
    if not node_matches:
        raise UnsupportedQueryError("The MATCH clause does not contain a node pattern.")

    first = node_matches[0]
    start = NodePattern(
        var=first.group("var") or "n",
        label=first.group("label"),
        props=_parse_props(first.group("props")),
    )
    if not start.label:
        raise UnsupportedQueryError("The start node must be labelled, e.g. (s:Supplier {key: $key}).")

    hops: list[HopPattern] = []
    rel_spans = list(_REL_RE.finditer(match_section))
    for position, rel in enumerate(rel_spans):
        target = node_matches[position + 1] if position + 1 < len(node_matches) else None
        types_raw = (rel.group("types") or "").strip()
        types = [t.strip() for t in types_raw.split("|") if t.strip()]
        min_hops = int(rel.group("min") or 1)
        max_hops = int(rel.group("max") or rel.group("min") or 1)
        hops.append(
            HopPattern(
                var=target.group("var") if target and target.group("var") else f"n{position + 2}",
                label=target.group("label") if target else None,
                types=types,
                min_hops=min_hops,
                max_hops=max_hops,
            )
        )
    if not hops:
        raise UnsupportedQueryError("At least one relationship hop is required for a traversal query.")

    where: list[WhereClause] = []
    where_match = re.search(r"WHERE\s+(.+?)(?=\s+RETURN|\s+LIMIT|$)", text, re.IGNORECASE)
    if where_match:
        for clause in _WHERE_RE.finditer(where_match.group(1)):
            where.append(
                WhereClause(
                    var=clause.group("var"),
                    prop=clause.group("prop"),
                    op=clause.group("op").upper(),
                    value=clause.group("value"),
                )
            )

    returns: list[str] = []
    return_match = _RETURN_RE.search(text)
    if return_match:
        returns = [item.strip() for item in return_match.group("items").split(",") if item.strip()]
    if not returns:
        returns = [start.var, hops[-1].var]

    limit_match = _LIMIT_RE.search(text)
    return ReadQueryPlan(
        start=start,
        hops=hops,
        where=where,
        returns=[r for r in returns if r not in {"r", "relationships", "relationship"}],
        limit=min(int(limit_match.group("limit")) if limit_match else 25, 200),
    )
