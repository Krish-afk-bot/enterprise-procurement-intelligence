"""The EPI MCP server.

Exposes a small, typed set of read tools over the Model Context Protocol so an
agent can ask the procurement workspace questions without a bespoke protocol.
The server is a *thin boundary*: tools call the same tenant-scoped session and
service layer the HTTP API uses, and every call passes through ``ToolGuard``.

Run it over stdio:

    MCP_ENABLED=true MCP_TENANT_ID=... MCP_USER_EMAIL=... python -m app.mcp_server

Deliberately absent: unrestricted SQL, filesystem access, arbitrary Cypher and
any write or delete tool. Those are out of scope for the tool boundary, not
pending work.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from mcp.server.fastmcp import FastMCP
from sqlalchemy import desc, select

from app.config.settings import Settings, get_settings
from app.db.models import Contract, Document, EvaluationRun, IngestionJob
from app.db.session import session_scope
from app.config.container import get_container
from app.mcp_server.guards import ToolGuard, ToolPolicy, bind_principal, validate_policies
from app.providers.graph.temporal import edge_valid_at, normalise_as_of
from app.security.audit import record_principal_action
from app.security.rbac import (
    PERM_CONTRACTS_READ,
    PERM_DOCUMENTS_READ,
    PERM_EVALUATION_READ,
    PERM_GRAPH_READ,
    PERM_SUPPLIERS_READ,
    Principal,
)
from app.services import procurement

POLICIES: dict[str, ToolPolicy] = {
    "search_documents": ToolPolicy(
        name="search_documents",
        permission=PERM_DOCUMENTS_READ,
        description="Find documents in this workspace by title or file name.",
    ),
    "get_document": ToolPolicy(
        name="get_document",
        permission=PERM_DOCUMENTS_READ,
        description="Metadata for one document: status, type, version, dates and links.",
    ),
    "search_contracts": ToolPolicy(
        name="search_contracts",
        permission=PERM_CONTRACTS_READ,
        description="Find contracts in this workspace by number or title.",
    ),
    "get_supplier_profile": ToolPolicy(
        name="get_supplier_profile",
        permission=PERM_SUPPLIERS_READ,
        description="Supplier record with its contracts and document counts.",
    ),
    "get_contract_amendments": ToolPolicy(
        name="get_contract_amendments",
        permission=PERM_CONTRACTS_READ,
        description="Amendments recorded against a contract, newest first.",
    ),
    "get_ingestion_status": ToolPolicy(
        name="get_ingestion_status",
        permission=PERM_DOCUMENTS_READ,
        description="Recent ingestion jobs and the documents they belong to.",
    ),
    "get_evaluation_metrics": ToolPolicy(
        name="get_evaluation_metrics",
        permission=PERM_EVALUATION_READ,
        description="Completed evaluation runs with the metrics they recorded.",
    ),
    "search_graph": ToolPolicy(
        name="search_graph",
        permission=PERM_GRAPH_READ,
        description="Find graph entities by label and name (Supplier, Contract, Product, Price,"
        " Document, ComplianceCertificate, Amendment).",
    ),
    "get_entity_neighbours": ToolPolicy(
        name="get_entity_neighbours",
        permission=PERM_GRAPH_READ,
        description="Typed relationships around a graph entity, optionally as of a historical date.",
    ),
}

#: Labels a caller may ask for. Anything else is refused rather than passed to
#: the provider, so the tool cannot probe the store with arbitrary labels.
ALLOWED_LABELS = (
    "Supplier",
    "Contract",
    "Amendment",
    "Product",
    "Price",
    "ComplianceCertificate",
    "Document",
    "Category",
)


def _iso(value: Any) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None


def _unpack(result: Any) -> tuple[list[Any], int | None]:
    """Services return ``(items, total)``; tolerate a bare list too."""
    if isinstance(result, tuple) and len(result) == 2:
        items, total = result
        return list(items), int(total)
    return list(result), None


# --------------------------------------------------------------------- bodies
async def _search_documents(principal: Principal, *, query: str, limit: int = 10) -> dict[str, Any]:
    async with session_scope() as session:
        pattern = f"%{query.lower()}%"
        rows = (
            await session.execute(
                select(Document)
                .where(
                    Document.tenant_id == principal.tenant_id,
                    Document.access_level.in_(principal.readable_access_levels),
                )
                .where(Document.title.ilike(pattern) | Document.filename.ilike(pattern))
                .order_by(desc(Document.updated_at))
                .limit(max(1, min(limit, 50)))
            )
        ).scalars()
        items = [
            {
                "id": row.id,
                "title": row.title or row.filename,
                "filename": row.filename,
                "document_type": row.document_type,
                "status": row.status,
            }
            for row in rows
        ]
        return {"query": query, "items": items, "total": len(items)}


async def _get_document(principal: Principal, *, document_id: str) -> dict[str, Any]:
    async with session_scope() as session:
        document = await session.get(Document, document_id)
        if (
            document is None
            or document.tenant_id != principal.tenant_id
            or not principal.can_read_level(document.access_level)
        ):
            # The same answer for "absent" and "not yours": existence is not disclosed.
            raise LookupError("document not found in this workspace")
        return {
            "id": document.id,
            "title": document.title or document.filename,
            "filename": document.filename,
            "document_type": document.document_type,
            "status": document.status,
            "stage": document.stage,
            "version": document.version,
            "access_level": document.access_level,
            "supplier_id": document.supplier_id,
            "contract_id": document.contract_id,
            "effective_date": _iso(document.effective_date),
            "expiry_date": _iso(document.expiry_date),
            "updated_at": _iso(document.updated_at),
        }


async def _search_contracts(principal: Principal, *, query: str, limit: int = 10) -> dict[str, Any]:
    async with session_scope() as session:
        items, total = _unpack(
            await procurement.list_contracts(
                session, principal, search=query, limit=max(1, min(limit, 50))
            )
        )
        return {"query": query, "items": items, "total": total or len(items)}


async def _get_supplier_profile(principal: Principal, *, supplier_id: str) -> dict[str, Any]:
    async with session_scope() as session:
        return await procurement.supplier_detail(session, principal, supplier_id)


async def _get_contract_amendments(principal: Principal, *, contract_id: str) -> dict[str, Any]:
    async with session_scope() as session:
        parent = await session.get(Contract, contract_id)
        if parent is None or parent.tenant_id != principal.tenant_id:
            raise LookupError("contract not found in this workspace")
        rows = list(
            (
                await session.execute(
                    select(Contract)
                    .where(
                        Contract.tenant_id == principal.tenant_id,
                        Contract.parent_contract_id == contract_id,
                    )
                    .order_by(desc(Contract.effective_date))
                )
            ).scalars()
        )
        return {
            "contract_id": contract_id,
            "contract_number": parent.contract_number,
            "amendments": [
                {
                    "id": row.id,
                    "number": row.contract_number,
                    "title": row.title,
                    "version": row.version,
                    "effective_date": _iso(row.effective_date),
                    "status": row.status,
                }
                for row in rows
            ],
            "total": len(rows),
        }


async def _get_ingestion_status(principal: Principal, *, limit: int = 20) -> dict[str, Any]:
    async with session_scope() as session:
        rows = list(
            (
                await session.execute(
                    select(IngestionJob)
                    .where(IngestionJob.tenant_id == principal.tenant_id)
                    .order_by(desc(IngestionJob.created_at))
                    .limit(max(1, min(limit, 100)))
                )
            ).scalars()
        )
        document_ids = {row.document_id for row in rows}
        titles: dict[str, str] = {}
        if document_ids:
            for document in (
                await session.execute(
                    select(Document).where(
                        Document.tenant_id == principal.tenant_id, Document.id.in_(document_ids)
                    )
                )
            ).scalars():
                titles[document.id] = document.title or document.filename
        return {
            "jobs": [
                {
                    "id": row.id,
                    "document_id": row.document_id,
                    "document_title": titles.get(row.document_id),
                    "status": row.status,
                    "stage": row.stage,
                    "progress": row.progress,
                    "attempts": row.attempts,
                    "error_message": (row.error_message or "")[:300] or None,
                    "finished_at": _iso(row.finished_at),
                }
                for row in rows
            ],
            "total": len(rows),
        }


async def _get_evaluation_metrics(principal: Principal, *, limit: int = 5) -> dict[str, Any]:
    async with session_scope() as session:
        rows = list(
            (
                await session.execute(
                    select(EvaluationRun)
                    .where(
                        EvaluationRun.tenant_id == principal.tenant_id,
                        EvaluationRun.status == "completed",
                    )
                    .order_by(desc(EvaluationRun.finished_at))
                    .limit(max(1, min(limit, 25)))
                )
            ).scalars()
        )
        return {
            "runs": [
                {
                    "id": row.id,
                    "experiment": row.experiment,
                    "dataset": row.dataset_name,
                    "questions": row.question_count,
                    "metrics": row.summary,
                    "finished_at": _iso(row.finished_at),
                }
                for row in rows
            ],
            "total": len(rows),
            "note": "Metrics are what the run recorded; unmeasured values are absent, not zero.",
        }


async def _search_graph(
    principal: Principal, *, label: str, query: str, limit: int = 10
) -> dict[str, Any]:
    """Entity search over the derived graph, scoped to the caller's tenant."""
    if label not in ALLOWED_LABELS:
        raise ValueError(f"unknown graph label {label!r}; expected one of {', '.join(ALLOWED_LABELS)}")
    graph = get_container().graph_store()
    nodes = await graph.find_nodes(
        label,
        name_contains=query,
        limit=max(1, min(int(limit), 25)),
        tenant_id=principal.tenant_id,
    )
    return {
        "label": label,
        "query": query,
        "items": [
            {"label": node.label, "key": node.key, "properties": node.properties} for node in nodes
        ],
        "total": len(nodes),
    }


async def _get_entity_neighbours(
    principal: Principal,
    *,
    label: str,
    key: str,
    max_hops: int = 1,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Relationships around one entity, with optional historical validity."""
    if label not in ALLOWED_LABELS:
        raise ValueError(f"unknown graph label {label!r}; expected one of {', '.join(ALLOWED_LABELS)}")
    day = normalise_as_of(as_of)
    graph = get_container().graph_store()
    hops = max(1, min(int(max_hops), 3))
    if hops == 1:
        edges = await graph.neighbors(label, key, direction="both")
        # ``neighbors`` is not tenant-aware, so the scope check happens here.
        edges = [
            edge
            for edge in edges
            if edge.properties.get("tenant_id") in {None, principal.tenant_id}
            and edge_valid_at(edge.properties, day)
        ]
    else:
        edges = await graph.traverse(
            label, key, max_hops=hops, tenant_id=principal.tenant_id, as_of=day
        )
    return {
        "root": {"label": label, "key": key},
        "as_of": day,
        "hops": hops,
        "edges": [
            {
                "type": edge.type,
                "start": {"label": edge.start_label, "key": edge.start_key},
                "end": {"label": edge.end_label, "key": edge.end_key},
                "properties": edge.properties,
            }
            for edge in edges
        ],
        "total": len(edges),
    }


# ---------------------------------------------------------------------- server
def build_server(
    settings: Settings | None = None,
    *,
    principal: Principal | None = None,
) -> FastMCP:
    settings = settings or get_settings()
    validate_policies(POLICIES)
    bound = principal or bind_principal(settings)

    async def write_audit(record: dict[str, Any]) -> None:
        async with session_scope() as session:
            await record_principal_action(
                session,
                bound,
                action=str(record["action"]),
                resource_type="mcp_tool",
                outcome=str(record["outcome"]),
                detail=dict(record.get("detail") or {}),
            )
            await session.commit()

    guard = ToolGuard(
        principal=bound,
        timeout_seconds=settings.mcp_tool_timeout_seconds,
        rate_limit_per_minute=settings.mcp_rate_limit_per_minute,
        audit_writer=write_audit,
    )

    server = FastMCP(
        name="epi-procurement",
        instructions=(
            "Read-only access to one procurement workspace. Every result is scoped to the tenant "
            "this server runs as and to the access levels that account may read. Cite documents by "
            "id and do not infer values the tools did not return."
        ),
    )

    # Each wrapper keeps an explicit signature: the SDK builds the tool schema
    # from it, and the body runs under the guard so no tool can bypass a check.
    async def search_documents(query: str, limit: int = 10) -> dict[str, Any]:
        """Find documents in this workspace by title or file name."""
        return await guard.call(
            POLICIES["search_documents"], _search_documents, principal=bound, query=query, limit=limit
        )

    async def get_document(document_id: str) -> dict[str, Any]:
        """Metadata for one document: status, type, version, dates and links."""
        return await guard.call(
            POLICIES["get_document"], _get_document, principal=bound, document_id=document_id
        )

    async def search_contracts(query: str, limit: int = 10) -> dict[str, Any]:
        """Find contracts in this workspace by number or title."""
        return await guard.call(
            POLICIES["search_contracts"], _search_contracts, principal=bound, query=query, limit=limit
        )

    async def get_supplier_profile(supplier_id: str) -> dict[str, Any]:
        """Supplier record with its contracts and document counts."""
        return await guard.call(
            POLICIES["get_supplier_profile"],
            _get_supplier_profile,
            principal=bound,
            supplier_id=supplier_id,
        )

    async def get_contract_amendments(contract_id: str) -> dict[str, Any]:
        """Amendments recorded against a contract, newest first."""
        return await guard.call(
            POLICIES["get_contract_amendments"],
            _get_contract_amendments,
            principal=bound,
            contract_id=contract_id,
        )

    async def get_ingestion_status(limit: int = 20) -> dict[str, Any]:
        """Recent ingestion jobs and the documents they belong to."""
        return await guard.call(
            POLICIES["get_ingestion_status"], _get_ingestion_status, principal=bound, limit=limit
        )

    async def get_evaluation_metrics(limit: int = 5) -> dict[str, Any]:
        """Completed evaluation runs with the metrics they recorded."""
        return await guard.call(
            POLICIES["get_evaluation_metrics"], _get_evaluation_metrics, principal=bound, limit=limit
        )

    async def search_graph(label: str, query: str, limit: int = 10) -> dict[str, Any]:
        """Find graph entities by label and name."""
        return await guard.call(
            POLICIES["search_graph"], _search_graph, principal=bound, label=label, query=query, limit=limit
        )

    async def get_entity_neighbours(
        label: str, key: str, max_hops: int = 1, as_of: str | None = None
    ) -> dict[str, Any]:
        """Typed relationships around a graph entity, optionally as of a date."""
        return await guard.call(
            POLICIES["get_entity_neighbours"],
            _get_entity_neighbours,
            principal=bound,
            label=label,
            key=key,
            max_hops=max_hops,
            as_of=as_of,
        )

    for fn in (
        search_documents,
        get_document,
        search_contracts,
        get_supplier_profile,
        get_contract_amendments,
        get_ingestion_status,
        get_evaluation_metrics,
        search_graph,
        get_entity_neighbours,
    ):
        server.add_tool(fn, name=fn.__name__, description=POLICIES[fn.__name__].description)

    return server


__all__ = ["POLICIES", "build_server"]
