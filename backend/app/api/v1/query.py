"""Ask / search / conversation endpoints.

Answers are produced by the agent pipeline and persisted with their citations and
verification outcome. Streaming emits *status events* (which engine ran, how many
candidates came back, whether verification passed) — never hidden reasoning.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.pipeline import AnswerPipeline
from app.api.deps import ContainerDep, PrincipalDep, get_client_ip, rate_limit
from app.config.settings import Settings, get_settings
from app.core.errors import NotFoundError
from app.db.models import Conversation, Message
from app.db.session import get_db
from app.retrieval.query_understanding import document_type_inventory
from app.retrieval.retriever import HybridRetriever
from app.schemas.query import (
    AnswerOut,
    ConversationOut,
    QueryRequest,
    SearchRequest,
    SearchResponse,
    SearchHitOut,
    retrieval_filter_payload,
)
from app.schemas.common import Page
from app.security import audit
from app.security.rbac import PERM_QUERY, Principal

router = APIRouter(tags=["query"])


@router.post("/query", response_model=AnswerOut, summary="Ask a question")
async def ask(
    payload: QueryRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
    container=ContainerDep,
    settings: Settings = Depends(get_settings),
    _limit: None = Depends(rate_limit("query", "rate_limit_query")),
) -> AnswerOut:
    principal.require(PERM_QUERY)
    pipeline = AnswerPipeline(container, settings)
    answer = await pipeline.answer(
        principal,
        payload.query,
        filters=payload.filters,
        strategy=payload.strategy,
        top_k=payload.top_k,
        max_iterations=payload.max_iterations,
        conversation_id=payload.conversation_id,
        debug=payload.include_trace,
    )
    await audit.record_principal_action(
        session,
        principal,
        action=audit.ACTION_QUERY,
        resource_type="query",
        resource_id=answer.query_id,
        ip_address=get_client_ip(request),
        detail={"status": answer.status, "strategy": payload.strategy, "citations": len(answer.citations)},
    )
    return answer


@router.post("/query/stream", summary="Ask a question, streaming status events (SSE)")
async def ask_stream(
    payload: QueryRequest,
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
    container=ContainerDep,
    settings: Settings = Depends(get_settings),
    _limit: None = Depends(rate_limit("query", "rate_limit_query")),
) -> StreamingResponse:
    principal.require(PERM_QUERY)
    pipeline = AnswerPipeline(container, settings)

    async def events() -> AsyncIterator[str]:
        try:
            async for event in pipeline.stream(
                principal,
                payload.query,
                filters=payload.filters,
                strategy=payload.strategy,
                top_k=payload.top_k,
                max_iterations=payload.max_iterations,
                conversation_id=payload.conversation_id,
                debug=payload.include_trace,
            ):
                yield f"data: {json.dumps(event, default=str)}\n\n"
        except Exception as exc:  # noqa: BLE001 - the stream must always terminate cleanly
            yield f"data: {json.dumps({'type': 'error', 'error': {'code': 'STREAM_FAILED', 'message': str(exc)[:300]}})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"cache-control": "no-cache", "x-accel-buffering": "no"},
    )


@router.post("/search", response_model=SearchResponse, summary="Retrieve evidence without generating an answer")
async def search(
    payload: SearchRequest,
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
    container=ContainerDep,
    settings: Settings = Depends(get_settings),
) -> SearchResponse:
    principal.require(PERM_QUERY)
    from app.retrieval.query_understanding import understand_query

    plan = await understand_query(payload.query, session=session, tenant_id=principal.tenant_id, router=None, use_llm=False)
    retriever = HybridRetriever(container, settings)
    result = await retriever.retrieve(
        session,
        principal,
        plan,
        mode=payload.mode,
        limit=payload.limit,
        # The same translation the answer pipeline uses, so a UI flag or an
        # unset list can never become a corpus constraint here either.
        filters=retrieval_filter_payload(payload.filters) if payload.filters else None,
        rerank=payload.rerank,
    )
    from app.schemas.query import RetrievalStepOut

    hits = [
        SearchHitOut(
            chunk_id=hit.chunk_id,
            document_id=hit.document_id,
            document_name=hit.document_name,
            document_type=hit.document_type,
            page=hit.page,
            section=hit.section,
            clause=hit.clause,
            content=hit.content,
            content_type=hit.content_type,
            score=hit.rerank_score or hit.fused_score or hit.dense_score,
            dense_score=hit.dense_score,
            sparse_score=hit.sparse_score,
            rerank_score=hit.rerank_score,
            fused_score=hit.fused_score,
            rank=hit.rank,
            is_synthetic=hit.is_synthetic,
            access_level=hit.access_level,
            effective_date=hit.effective_date,
            expiry_date=hit.expiry_date,
            version=hit.version,
            matched_by=hit.matched_by or [],
        )
        for hit in result.hits
    ]
    return SearchResponse(
        query=payload.query,
        mode=result.mode,
        hits=hits,
        total=len(hits),
        steps=[RetrievalStepOut(**step.as_dict()) for step in result.steps],
        reranker=result.reranker,
        embedding_model=result.embedding_model,
    )


@router.get("/filters", summary="Available filter values for the search workspace")
async def filter_options(
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    principal.require(PERM_QUERY)
    from app.retrieval.query_understanding import load_vocabulary

    vocabulary = await load_vocabulary(session, principal.tenant_id)
    return {
        "suppliers": [{"id": supplier_id, "name": name} for supplier_id, name in vocabulary.suppliers],
        "products": [{"id": product_id, "name": name, "sku": sku} for product_id, name, sku in vocabulary.products],
        "contracts": [{"id": contract_id, "number": number} for contract_id, number in vocabulary.contracts],
        "regions": vocabulary.regions,
        "categories": vocabulary.categories,
        "document_types": await document_type_inventory(session, principal.tenant_id),
        "strategies": ["dense", "sparse", "hybrid", "hybrid_rerank", "hybrid_rerank_contextual", "agentic"],
        "limits": {
            "context_max_chunks": settings.context_max_chunks,
            "rerank_top_n": settings.rerank_top_n,
            "max_agent_iterations": settings.max_agent_iterations,
        },
    }


@router.get("/conversations", response_model=Page[ConversationOut], summary="List conversations")
async def list_conversations(
    limit: int = 25,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
) -> Page[ConversationOut]:
    principal.require(PERM_QUERY)
    statement = select(Conversation).where(
        Conversation.tenant_id == principal.tenant_id, Conversation.user_id == principal.user_id
    )
    total = await session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = (
        await session.execute(
            statement.order_by(Conversation.updated_at.desc()).offset(offset).limit(limit)
        )
    ).scalars()
    items = [
        ConversationOut(
            id=row.id, title=row.title, summary=row.summary, message_count=row.message_count or 0
        )
        for row in rows
    ]
    return Page[ConversationOut](
        items=items, total=int(total), limit=limit, offset=offset, has_more=offset + len(items) < int(total)
    )


@router.post("/conversations", response_model=ConversationOut, summary="Create a conversation")
async def create_conversation(
    title: str | None = None,
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
) -> ConversationOut:
    principal.require(PERM_QUERY)
    conversation = Conversation(
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        title=title or "New conversation",
    )
    session.add(conversation)
    await session.flush()
    return ConversationOut(
        id=conversation.id, title=conversation.title, summary=None, message_count=0
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=Page[dict],
    summary="Conversation transcript",
)
async def conversation_messages(
    conversation_id: str,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
) -> Page[dict]:
    principal.require(PERM_QUERY)
    conversation = await session.get(Conversation, conversation_id)
    if conversation is None or conversation.tenant_id != principal.tenant_id:
        raise NotFoundError("Conversation not found.", details={"conversation_id": conversation_id})
    statement = select(Message).where(Message.conversation_id == conversation_id)
    total = await session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = (await session.execute(statement.order_by(Message.created_at).offset(offset).limit(limit))).scalars()
    items = [
        {
            "id": row.id,
            "role": row.role,
            "content": row.content,
            "query_id": row.query_id,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]
    return Page[dict](
        items=items, total=int(total), limit=limit, offset=offset, has_more=offset + len(items) < int(total)
    )
