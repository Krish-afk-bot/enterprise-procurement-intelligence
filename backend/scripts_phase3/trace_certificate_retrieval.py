#!/usr/bin/env python3
"""Trace certificate retrieval through each pipeline stage."""
import asyncio
import os
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
EVAL_VAR_ROOT = BACKEND_DIR / "var" / "eval-v2"

os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{(EVAL_VAR_ROOT / 'eval.db').as_posix()}")
os.environ.setdefault("VAR_DIR", (EVAL_VAR_ROOT / "var").as_posix())
os.environ.setdefault("LOCAL_STORAGE_DIR", (EVAL_VAR_ROOT / "storage").as_posix())
os.environ.setdefault("VECTOR_PROVIDER", "local")
os.environ.setdefault("GRAPH_PROVIDER", "local")
os.environ.setdefault("CACHE_PROVIDER", "memory")
os.environ.setdefault("STORAGE_PROVIDER", "local")
os.environ.setdefault("OCR_ENABLED", "false")
os.environ.setdefault("VLM_ENABLED", "false")
os.environ.setdefault("EMBEDDING_PROVIDER", "sentence_transformers")
os.environ.setdefault("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
os.environ.setdefault("RERANKER_ENABLED", "true")
os.environ.setdefault("RERANKER_PROVIDER", "cross_encoder")
os.environ.setdefault("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")

sys.path.insert(0, str(BACKEND_DIR))

from app.config.settings import reset_settings_cache
reset_settings_cache()


async def main():
    import json
    from datetime import datetime
    from sqlalchemy import select
    from app.config.container import get_container
    from app.config.settings import get_settings
    from app.db.models import Tenant, User, Chunk
    from app.db.session import session_scope
    from app.retrieval.retriever import HybridRetriever
    from app.retrieval.fusion import reciprocal_rank_fusion
    from app.security.scope import build_retrieval_filters
    from app.agents.pipeline import AnswerPipeline
    from app.security.rbac import Principal

    settings = get_settings()
    container = get_container()
    await container.startup()

    async with session_scope() as session:
        tenant = (await session.execute(select(Tenant).limit(1))).scalar_one()
        user = (await session.execute(select(User).where(User.tenant_id == tenant.id).limit(1))).scalar_one()
    
    principal = Principal(
        user_id=user.id,
        tenant_id=tenant.id,
        email=user.email,
        role=user.role,
    )

    # Get all chunk IDs for certificate
    async with session_scope() as session:
        cert_chunks = (await session.execute(
            select(Chunk.id).where(
                Chunk.tenant_id == tenant.id,
                Chunk.document_id.in_(
                    select(Chunk.document_id).where(
                        Chunk.tenant_id == tenant.id
                    ).where(
                        Chunk.content.like('%ISO 9001%') | Chunk.content.like('%ISO 14001%')
                    )
                )
            )
        )).scalars().all()
        
        # Also get by document name
        from app.db.models import Document
        cert_doc = (await session.execute(
            select(Document).where(
                Document.tenant_id == tenant.id,
                Document.filename.like('%compliance_certificate%')
            )
        )).scalar_one_or_none()
        
        if cert_doc:
            cert_chunks_by_doc = (await session.execute(
                select(Chunk.id, Chunk.content, Chunk.expiry_date).where(
                    Chunk.document_id == cert_doc.id
                )
            )).all()
            cert_chunk_ids = {c[0] for c in cert_chunks_by_doc}
            print(f"Certificate document: {cert_doc.filename}")
            print(f"Certificate chunks: {len(cert_chunk_ids)}")
            if cert_chunks_by_doc:
                print(f"  First chunk content: {cert_chunks_by_doc[0][1][:100]}")
                print(f"  Expiry date: {cert_chunks_by_doc[0][2]}")
        else:
            cert_chunk_ids = set()
            print("No certificate document found")

    questions_file = PROJECT_ROOT / "data" / "evaluation" / "v2" / "questions_dev.json"
    with open(questions_file) as f:
        questions_data = json.load(f)
    
    questions_by_id = {q["id"]: q for q in questions_data["questions"]}
    
    # Test questions + 1 control
    target_ids = ["v2-compl-002", "v2-compl-003", "v2-compl-004", "v2-compl-005", "v2-rel-008", "v2-comp-009"]
    
    # Find a control question that retrieves master contract successfully
    control_id = "v2-agg-002"  # Uses supplier_a documents
    target_ids.append(control_id)
    
    today = date.today()
    print(f"\nToday's date for expiry check: {today}")
    print(f"Settings: fusion_top_k={settings.fusion_top_k}, rerank_top_n={settings.rerank_top_n}, rrf_k={settings.rrf_k}")
    print()
    
    retriever = HybridRetriever(container, settings)
    
    for qid in target_ids:
        if qid not in questions_by_id:
            continue
        
        question = questions_by_id[qid]
        print(f"{'='*80}")
        print(f"Question: {qid}")
        print(f"Text: {question['question'][:80]}")
        print(f"Expected docs: {question.get('expected_documents', [])}")
        
        # Get query plan using runtime
        pipeline = AnswerPipeline(container, settings)
        async with session_scope() as session:
            state = {
                "tenant_id": principal.tenant_id,
                "user_id": principal.user_id,
                "role": principal.role,
                "question": question["question"],
                "filters": {},
            }
            state = await pipeline.runtime.understand(state, session)
            state = await pipeline.runtime.plan(state)
            plan = state.get("plan", {})
        
        # Build scoped filters
        plan_extras = {}
        supplier_ids = plan.get("supplier_ids", [])
        if len(supplier_ids) == 1:
            plan_extras["supplier_id"] = supplier_ids[0]
        scoped_filters = build_retrieval_filters(principal, **plan_extras)
        
        requires_temporal = plan.get("requires_temporal", False)
        print(f"Plan: requires_temporal={requires_temporal}, supplier_ids={supplier_ids}")
        print(f"Scoped filters: {scoped_filters}")
        print()
        
        # Stage 1: Dense search
        async with session_scope() as session:
            dense_hits, dense_step = await retriever._dense_search(question["question"], scoped_filters)
        
        cert_in_dense = [i+1 for i, h in enumerate(dense_hits) if h.id in cert_chunk_ids]
        dense_status = f"rank {cert_in_dense[0]}" if cert_in_dense else "NOT FOUND"
        
        # Stage 2: Sparse search
        async with session_scope() as session:
            sparse_hits, sparse_step = await retriever._sparse_search(question["question"], principal, scoped_filters)
        
        cert_in_sparse = [i+1 for i, h in enumerate(sparse_hits) if h.id in cert_chunk_ids]
        sparse_status = f"rank {cert_in_sparse[0]}" if cert_in_sparse else "NOT FOUND"
        
        # Stage 3: Fusion
        fused = reciprocal_rank_fusion(dense_hits, sparse_hits, k=settings.rrf_k)
        cert_in_fused = [i+1 for i, h in enumerate(fused) if h.id in cert_chunk_ids]
        fused_status = f"rank {cert_in_fused[0]}" if cert_in_fused else "NOT FOUND"
        
        # Stage 4: Take fusion_top_k
        candidates = fused[:settings.fusion_top_k]
        cert_in_candidates = [i+1 for i, h in enumerate(candidates) if h.id in cert_chunk_ids]
        candidates_status = f"rank {cert_in_candidates[0]}" if cert_in_candidates else "NOT FOUND"
        
        # Stage 5: Load chunks (authorization)
        async with session_scope() as session:
            chunks = await retriever._load_chunks(session, principal, candidates)
        
        cert_in_loaded = [i+1 for i, c in enumerate(chunks) if c.chunk_id in cert_chunk_ids]
        loaded_status = f"rank {cert_in_loaded[0]}" if cert_in_loaded else "NOT FOUND"
        dropped_count = len(candidates) - len(chunks)
        
        # Stage 6: Rerank
        if settings.reranker_enabled:
            if settings.rerank_gate_enabled and retriever._rerank_confident(chunks):
                rerank_status = "GATED"
                cert_in_reranked = cert_in_loaded
                reranked_status = loaded_status
                chunks_after_rerank = chunks
            else:
                chunks_after_rerank, rerank_step = await retriever._rerank(question["question"], chunks)
                cert_in_reranked = [i+1 for i, c in enumerate(chunks_after_rerank) if c.chunk_id in cert_chunk_ids]
                reranked_status = f"rank {cert_in_reranked[0]}" if cert_in_reranked else "NOT FOUND"
                rerank_status = "RERANKED"
        else:
            rerank_status = "DISABLED"
            chunks_after_rerank = chunks
            cert_in_reranked = cert_in_loaded
            reranked_status = loaded_status
        
        # Stage 7: Temporal preference (create mock plan object)
        chunks_before_temporal = list(chunks_after_rerank)
        
        # Create a simple object with requires_temporal attribute
        class SimplePlan:
            def __init__(self, requires_temporal):
                self.requires_temporal = requires_temporal
        
        simple_plan = SimplePlan(requires_temporal)
        chunks_after_temporal = retriever._apply_temporal_preference(chunks_after_rerank, simple_plan)
        
        cert_before_temporal = [i+1 for i, c in enumerate(chunks_before_temporal) if c.chunk_id in cert_chunk_ids]
        cert_after_temporal = [i+1 for i, c in enumerate(chunks_after_temporal) if c.chunk_id in cert_chunk_ids]
        
        before_temp_status = f"rank {cert_before_temporal[0]}" if cert_before_temporal else "NOT FOUND"
        after_temp_status = f"rank {cert_after_temporal[0]}" if cert_after_temporal else "NOT FOUND"
        
        # Check which chunks are expired
        expired_chunks = []
        for c in chunks_after_temporal[:20]:
            if c.expiry_date:
                try:
                    exp_date = c.expiry_date if isinstance(c.expiry_date, date) else datetime.fromisoformat(str(c.expiry_date)).date()
                    if exp_date < today:
                        expired_chunks.append((c.chunk_id, exp_date))
                except:
                    pass
        
        # Stage 8: Top-n cut
        final_chunks = chunks_after_temporal[:settings.rerank_top_n]
        cert_in_final = [i+1 for i, c in enumerate(final_chunks) if c.chunk_id in cert_chunk_ids]
        final_status = f"rank {cert_in_final[0]}" if cert_in_final else "NOT FOUND"
        
        # Print table
        print("| Stage | Status | Certificate | Details |")
        print("|-------|--------|------------|---------|")
        print(f"| Dense search | DONE | {dense_status} | {len(dense_hits)} hits |")
        print(f"| Sparse search | DONE | {sparse_status} | {len(sparse_hits)} hits |")
        print(f"| Fusion (RRF) | DONE | {fused_status} | {len(fused)} fused |")
        print(f"| Top {settings.fusion_top_k} candidates | DONE | {candidates_status} | {len(candidates)} kept |")
        print(f"| Auth filter | DONE | {loaded_status} | {dropped_count} dropped |")
        print(f"| Rerank | {rerank_status} | {reranked_status} | {len(chunks_after_rerank)} chunks |")
        print(f"| Before temporal | DONE | {before_temp_status} | requires_temporal={requires_temporal} |")
        print(f"| After temporal | DONE | {after_temp_status} | {len(expired_chunks)} expired chunks |")
        print(f"| Top-{settings.rerank_top_n} cut | DONE | {final_status} | final result |")
        print()
        
        # Determine where certificate was lost
        if "NOT FOUND" in dense_status and "NOT FOUND" in sparse_status:
            loss_stage = "STAGE 1-2: Not in dense or sparse search results"
        elif "NOT FOUND" in fused_status:
            loss_stage = "STAGE 3: Lost during fusion (present in search but not fused)"
        elif "NOT FOUND" in candidates_status:
            loss_stage = f"STAGE 4: Ranked below position {settings.fusion_top_k} in fusion"
        elif "NOT FOUND" in loaded_status:
            loss_stage = "STAGE 5: Filtered out by authorization check"
        elif "NOT FOUND" in reranked_status:
            loss_stage = "STAGE 6: Lost during reranking"
        elif "NOT FOUND" in after_temp_status:
            loss_stage = "STAGE 7: Lost during temporal preference sorting"
        elif "NOT FOUND" in final_status:
            loss_stage = f"STAGE 8: Ranked below position {settings.rerank_top_n} after temporal"
        else:
            loss_stage = "PRESENT in final results"
        
        print(f"**Certificate first lost at: {loss_stage}**")
        
        if expired_chunks:
            print(f"\nExpired chunks found: {len(expired_chunks)}")
            for chunk_id, exp_date in expired_chunks[:3]:
                print(f"  - {chunk_id[:20]}... expired {exp_date}")
        
        print()
    
    await container.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
