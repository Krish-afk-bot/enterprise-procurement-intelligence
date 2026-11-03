#!/usr/bin/env python3
"""Debug temporal ranking for specific questions to test hypothesis."""
import asyncio
import os
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
EVAL_VAR_ROOT = BACKEND_DIR / "var" / "eval-v2"

# Configure for eval DB
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
    from sqlalchemy import select
    from app.config.container import get_container
    from app.config.settings import get_settings
    from app.db.models import Tenant, User
    from app.db.session import session_scope
    from app.agents.pipeline import AnswerPipeline
    from app.security.rbac import Principal

    settings = get_settings()
    container = get_container()
    await container.startup()

    # Get principal
    async with session_scope() as session:
        tenant = (await session.execute(select(Tenant).limit(1))).scalar_one()
        user = (await session.execute(select(User).where(User.tenant_id == tenant.id).limit(1))).scalar_one()
    
    principal = Principal(
        user_id=user.id,
        tenant_id=tenant.id,
        email=user.email,
        role=user.role,
    )

    # Load questions
    questions_file = PROJECT_ROOT / "data" / "evaluation" / "v2" / "questions_dev.json"
    with open(questions_file) as f:
        questions_data = json.load(f)
    
    questions_by_id = {q["id"]: q for q in questions_data["questions"]}
    
    # Target questions
    target_ids = ["v2-compl-002", "v2-compl-003", "v2-compl-004", "v2-compl-005", "v2-rel-008", "v2-comp-009"]
    
    pipeline = AnswerPipeline(container, settings)
    
    today = date.today()
    print(f"Today's date (for expiry check): {today}")
    print(f"Eval DB: {settings.database_url}")
    print(f"Reranker: {settings.reranker_enabled}")
    print()
    
    for qid in target_ids:
        if qid not in questions_by_id:
            print(f"SKIP {qid}: not in dataset")
            continue
        
        question = questions_by_id[qid]
        print(f"=" * 80)
        print(f"Question: {qid}")
        print(f"Text: {question['question'][:100]}")
        print(f"Expected docs: {question.get('expected_documents', [])}")
        print()
        
        # Run through pipeline up to retrieval
        async with session_scope() as session:
            state = {
                "tenant_id": principal.tenant_id,
                "user_id": principal.user_id,
                "role": principal.role,
                "question": question["question"],
                "filters": {},
                "top_k": 10,
                "strategy": None,
                "max_iterations": 1,
                "debug": False,
            }
            state = await pipeline.runtime.understand(state, session)
            state = await pipeline.runtime.plan(state)
            state = await pipeline.runtime.structured(state, session)
            state = await pipeline.runtime.graph(state, session)
            state = await pipeline.runtime.retrieve(state, session)
            
            plan = state.get("plan", {})
            retrieval = state.get("retrieval", {})
            hits = retrieval.get("hits", [])
            
            print(f"Plan: requires_temporal={plan.get('requires_temporal')}, filters={plan.get('filters', {})}")
            print(f"Retrieved {len(hits)} chunks")
            print()
            
            if not hits:
                print("No hits retrieved\n")
                continue
            
            # Get pre-temporal order (by rerank_score or fused_score)
            chunks_before = sorted(
                hits,
                key=lambda c: c.get("rerank_score") if c.get("rerank_score") is not None else (c.get("fused_score") or 0.0),
                reverse=True
            )
            
            # Apply temporal preference manually
            def sort_key(chunk):
                from datetime import datetime
                expiry = chunk.get("expiry_date")
                if isinstance(expiry, str):
                    try:
                        expiry = datetime.fromisoformat(expiry).date()
                    except:
                        expiry = None
                expired = 1 if (expiry is not None and expiry < today) else 0
                effective = chunk.get("effective_date")
                if isinstance(effective, str):
                    try:
                        effective = datetime.fromisoformat(effective).date()
                    except:
                        effective = None
                effective_ord = effective.toordinal() if effective else 0
                base = chunk.get("rerank_score") if chunk.get("rerank_score") is not None else (chunk.get("fused_score") or 0.0)
                if plan.get("requires_temporal"):
                    return (expired, -effective_ord)
                return (expired, -base)
            
            chunks_after = sorted(hits, key=sort_key)
            
            # Build lookup for ranks
            rank_before = {chunk.get("chunk_id"): idx + 1 for idx, chunk in enumerate(chunks_before)}
            rank_after = {chunk.get("chunk_id"): idx + 1 for idx, chunk in enumerate(chunks_after)}
            
            # Print table
            from datetime import datetime
            print("| Doc Name | Doc Type | Effective | Expiry | Fused | Rerank | Before | After | Expired? |")
            print("|----------|----------|-----------|--------|-------|--------|--------|-------|----------|")
            
            for chunk in chunks_after[:15]:  # Top 15 after temporal
                doc_name = str(chunk.get("document_name", ""))[:20]
                doc_type = str(chunk.get("document_type", ""))[:12]
                effective = str(chunk.get("effective_date")) if chunk.get("effective_date") else "None"
                expiry = str(chunk.get("expiry_date")) if chunk.get("expiry_date") else "None"
                fused = f"{chunk.get('fused_score'):.3f}" if chunk.get("fused_score") else "None"
                rerank = f"{chunk.get('rerank_score'):.3f}" if chunk.get("rerank_score") else "None"
                chunk_id = chunk.get("chunk_id")
                before = rank_before.get(chunk_id, "?")
                after = rank_after.get(chunk_id, "?")
                expiry_date = chunk.get("expiry_date")
                if isinstance(expiry_date, str):
                    try:
                        expiry_date = datetime.fromisoformat(expiry_date).date()
                    except:
                        expiry_date = None
                expired = "YES" if (expiry_date and expiry_date < today) else "no"
                
                print(f"| {doc_name:20} | {doc_type:12} | {effective:10} | {expiry:10} | {fused:5} | {rerank:6} | {before:6} | {after:5} | {expired:8} |")
            
            print()
            
            # Check certificate rank
            from datetime import datetime
            certificate_chunks = [c for c in hits if "certificate" in str(c.get("document_name", "")).lower() or c.get("document_type") == "compliance_certificate"]
            if certificate_chunks:
                print("Certificate chunks:")
                for cert in certificate_chunks:
                    chunk_id = cert.get("chunk_id")
                    before = rank_before.get(chunk_id, "?")
                    after = rank_after.get(chunk_id, "?")
                    expiry = cert.get("expiry_date")
                    if isinstance(expiry, str):
                        try:
                            expiry = datetime.fromisoformat(expiry).date()
                        except:
                            pass
                    expired = "YES" if (expiry and expiry < today) else "no"
                    print(f"  {str(cert.get('document_name', ''))[:40]}: rank {before} → {after}, expiry={expiry}, expired={expired}")
            else:
                print("No certificate chunks found")
            
            print()
            
            # Check Supplier C
            from datetime import datetime
            supplier_c_chunks = [c for c in hits if "supplier_c" in str(c.get("document_name", "")).lower() or "ORC-2021-777" in str(c.get("contract_id", ""))]
            if supplier_c_chunks:
                print("Supplier C chunks:")
                for chunk in supplier_c_chunks:
                    chunk_id = chunk.get("chunk_id")
                    before = rank_before.get(chunk_id, "?")
                    after = rank_after.get(chunk_id, "?")
                    expiry = chunk.get("expiry_date")
                    if isinstance(expiry, str):
                        try:
                            expiry = datetime.fromisoformat(expiry).date()
                        except:
                            pass
                    expired = "YES" if (expiry and expiry < today) else "no"
                    print(f"  {str(chunk.get('document_name', ''))[:40]}: rank {before} → {after}, expiry={expiry}, expired={expired}")
            else:
                print("No Supplier C chunks found")
            
            print()
            
            # Hypothesis check
            from datetime import datetime
            moved_down = []
            for chunk in hits:
                chunk_id = chunk.get("chunk_id")
                before = rank_before.get(chunk_id, 999)
                after = rank_after.get(chunk_id, 999)
                expiry = chunk.get("expiry_date")
                if isinstance(expiry, str):
                    try:
                        expiry = datetime.fromisoformat(expiry).date()
                    except:
                        expiry = None
                if after > before and expiry and expiry < today:
                    moved_down.append((str(chunk.get("document_name", "")), before, after))
            
            if moved_down:
                print(f"[+] HYPOTHESIS CONFIRMED: {len(moved_down)} expired chunks moved down")
                for name, before, after in moved_down[:3]:
                    print(f"  - {name[:40]}: {before} -> {after}")
            else:
                print("[X] HYPOTHESIS NOT CONFIRMED: No expired chunks moved down")
            
            print()
    
    await container.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
