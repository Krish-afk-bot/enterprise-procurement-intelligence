#!/usr/bin/env python3
"""Log verifier decisions for questions with expected doc retrieved but refused/partial."""
import asyncio
import json
import os
import sys
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
os.environ.setdefault("EVAL_AS_OF_DATE", "2026-02-15")

sys.path.insert(0, str(BACKEND_DIR))

from app.config.settings import reset_settings_cache
reset_settings_cache()


async def main():
    results_file = PROJECT_ROOT / "data" / "evaluation" / "v2" / "dev-baseline_dev_current_qwen2.5-coder-7b.json"
    questions_file = PROJECT_ROOT / "data" / "evaluation" / "v2" / "questions_dev.json"
    
    with open(results_file) as f:
        results = json.load(f)
    
    with open(questions_file) as f:
        questions_data = json.load(f)
    
    questions_by_id = {q["id"]: q for q in questions_data["questions"]}
    
    print("Verifier Log: Questions with Expected Doc Retrieved but Refused/Partial\n")
    print("="*80)
    
    count = 0
    for row in results["rows"]:
        question = questions_by_id.get(row["id"])
        if not question:
            continue
        
        # Skip unanswerable questions
        if question.get("expected_refusal", False):
            continue
        
        # Check if expected doc was retrieved
        expected_docs = set(question.get("expected_documents", []))
        retrieved_docs = set(row.get("retrieved_documents", []))
        
        if not (expected_docs & retrieved_docs):
            continue  # Expected doc not retrieved
        
        # Check if refused or partial
        status = row.get("status", "")
        if status not in ("insufficient_evidence", "partial", "refused"):
            continue
        
        count += 1
        print(f"\n{'='*80}")
        print(f"Question ID: {row['id']}")
        print(f"Question: {row.get('question', '')[:100]}")
        print(f"Status: {status}")
        print(f"Expected docs: {list(expected_docs)}")
        print(f"Retrieved docs: {list(retrieved_docs)}")
        print(f"Expected & Retrieved: {list(expected_docs & retrieved_docs)}")
        
        # Get state from row if available
        state = row.get("state", {})
        verification = state.get("verification", {})
        
        # Try to get answer draft
        answer_text = row.get("answer_text", "")
        print(f"\nAnswer draft: {answer_text[:200] if answer_text else '(none)'}")
        
        # Grounding details
        grounding_supported = row.get("grounding_supported", 0)
        grounding_total = row.get("grounding_total", 0)
        print(f"\nGrounding: {grounding_supported}/{grounding_total} claims supported")
        
        # Try to get claim details from grounding_details
        grounding_details = row.get("grounding_details")
        if grounding_details and isinstance(grounding_details, list):
            print("\nClaim verdicts:")
            for i, claim_detail in enumerate(grounding_details[:5], 1):
                if isinstance(claim_detail, dict):
                    claim_text = claim_detail.get("claim", "")[:80]
                    verdict = claim_detail.get("verdict", "unknown")
                    binding = claim_detail.get("binding", "unknown")
                    print(f"  {i}. [{binding}/{verdict}] {claim_text}")
        
        # Check which decide_status rule fired
        answerability = row.get("answerability", {})
        if isinstance(answerability, dict):
            level = answerability.get("level", "")
            reason = answerability.get("reason", "")
            print(f"\nAnswerability: level={level}, reason={reason}")
        else:
            print(f"\nAnswerability: {answerability}")
        
        # Check planner supplier_id filter
        plan = state.get("plan", {})
        supplier_ids = plan.get("supplier_ids", [])
        print(f"\nPlanner supplier_id filter: {supplier_ids}")
        
        # Check if any relevant chunk has NULL supplier_id
        retrieval_state = state.get("retrieval", {})
        hits = retrieval_state.get("hits", [])
        null_supplier_chunks = [
            h.get("document_name", "")[:40]
            for h in hits[:15]
            if h.get("supplier_id") is None
        ]
        if null_supplier_chunks:
            print(f"\nChunks with NULL supplier_id in top-15: {len(null_supplier_chunks)}")
            for doc in null_supplier_chunks[:3]:
                print(f"  - {doc}")
    
    print(f"\n{'='*80}")
    print(f"Total questions with expected doc retrieved but refused/partial: {count}")

if __name__ == "__main__":
    asyncio.run(main())
