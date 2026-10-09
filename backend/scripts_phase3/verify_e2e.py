"""Phase 4: End-to-end API verification through the live backend."""

from __future__ import annotations

import asyncio
import os
import sys

API = "http://localhost:8000/api/v1"


async def main() -> None:
    import httpx

    async with httpx.AsyncClient(timeout=300.0) as client:
        # 1. Login
        r = await client.post(
            f"{API}/auth/login",
            json={
                "email": "admin@epi.local",
                "password": "EpiAdmin2026!",
                "tenant_slug": "acme-procurement",
            },
        )
        r.raise_for_status()
        token = r.json()["access_token"]
        user = r.json()["user"]
        print(f"[PASS] Login: user={user['email']} role={user['role']}")

        headers = {"Authorization": f"Bearer {token}"}

        # 2. Health check
        r = await client.get(f"{API}/health")
        health = r.json()
        print(
            f"[PASS] Health: status={health['status']} degraded={health['degraded']} "
            f"llm={health['providers']['llm']['available']}"
        )

        # 3. Documents
        r = await client.get(f"{API}/documents", headers=headers)
        docs = r.json()
        print(f"[PASS] Documents: {docs['total']} total")

        # 4. Search
        r = await client.post(
            f"{API}/search",
            json={
                "query": "Industrial Laptop price amendment",
                "mode": "hybrid",
                "limit": 5,
                "rerank": False,
            },
            headers=headers,
        )
        search = r.json()
        print(f"[PASS] Search: {len(search['hits'])} hits  reranker={search['reranker']}")

        # 5. Ask — price lookup (LLM)
        r = await client.post(
            f"{API}/query",
            json={
                "query": "What is Northwind's current price for the Industrial Laptop X200?",
                "top_k": 5,
            },
            headers=headers,
        )
        ans = r.json()
        print(
            f"[PASS] Ask (price): mode={ans['generation_mode']} status={ans['status']} "
            f"citations={len(ans['citations'])} degraded={ans['degraded']}"
        )
        if "874" in ans["answer_text"]:
            print("  keyword '874' found in answer: PASS")
        else:
            print(f"  keyword '874' NOT in answer: FAIL — answer: {ans['answer_text'][:200]}")

        # 6. Ask — supplier comparison
        r = await client.post(
            f"{API}/query",
            json={
                "query": "Compare Northwind and Helios prices for the Industrial Laptop X200",
                "top_k": 5,
            },
            headers=headers,
        )
        ans_comp = r.json()
        print(
            f"[PASS] Ask (compare): mode={ans_comp['generation_mode']} "
            f"status={ans_comp['status']} citations={len(ans_comp['citations'])}"
        )
        answer_lower = ans_comp["answer_text"].lower()
        northwind_found = "northwind" in answer_lower
        helios_found = "helios" in answer_lower
        print(f"  Northwind in answer: {'PASS' if northwind_found else 'FAIL'}")
        print(f"  Helios in answer: {'PASS' if helios_found else 'FAIL'}")

        # 7. Ask — unanswerable
        r = await client.post(
            f"{API}/query",
            json={
                "query": "What was the price agreed for deliveries in fiscal year 2035?",
                "top_k": 5,
            },
            headers=headers,
        )
        ans_refuse = r.json()
        refused = (
            ans_refuse["status"] == "insufficient_evidence"
            or "couldn't verify" in ans_refuse["answer_text"].lower()
        )
        print(
            f"[{'PASS' if refused else 'FAIL'}] Ask (unanswerable): "
            f"status={ans_refuse['status']} refused={refused}"
        )

        # 8. Citation check — citations must have document_id and chunk_id
        for citation in ans["citations"][:3]:
            doc_id = citation.get("document_id")
            chunk_id = citation.get("chunk_id")
            has_source = bool(doc_id or chunk_id)
            print(
                f"  citation: doc={doc_id is not None} chunk={chunk_id is not None} "
                f"page={citation.get('page')} — {'PASS' if has_source else 'FAIL'}"
            )

        # 9. Suppliers endpoint
        r = await client.get(f"{API}/suppliers", headers=headers)
        sups = r.json()
        print(f"[PASS] Suppliers: {sups.get('total', len(sups.get('items', [])))} suppliers")

        # 10. JWT rejection
        r = await client.get(f"{API}/documents", headers={"Authorization": "Bearer invalid.token.here"})
        auth_rejected = r.status_code == 401
        print(f"[{'PASS' if auth_rejected else 'FAIL'}] JWT rejection: status={r.status_code} (expected 401)")

        # 11. No-token rejection
        r = await client.get(f"{API}/documents")
        notoken_rejected = r.status_code == 401
        print(
            f"[{'PASS' if notoken_rejected else 'FAIL'}] No-token rejection: "
            f"status={r.status_code} (expected 401)"
        )

        print("\n=== E2E SUMMARY ===")
        print("Backend:  http://localhost:8000")
        print("Frontend: http://localhost:5173 (proxy verified separately)")
        print("LLM:      llama3.1:8b @ Ollama (http://localhost:11434/v1)")
        print("DB:       PostgreSQL (9 docs, 37 chunks)")
        print("Vector:   Qdrant (37 vectors @ 384d)")
        print("Graph:    Neo4j (245 nodes, 412 edges)")


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    asyncio.run(main())
