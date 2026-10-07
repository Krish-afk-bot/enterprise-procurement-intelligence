"""Phase 3: Qdrant live verification.

Tests: connect, collection create, upsert, search, metadata filter, delete.
Cleans up all test data.  Never touches production collections.
"""

from __future__ import annotations

import asyncio
import sys

TEST_COLLECTION = "phase3_test_384d"
DIM = 384
QDRANT_URL = "http://localhost:6333"


async def main() -> None:
    from app.providers.types import VectorPoint
    from app.providers.vector.qdrant import QdrantVectorStore

    store = QdrantVectorStore(QDRANT_URL, api_key=None)

    # 1. status
    status = await store.status()
    print(f"status.available = {status.available}  detail={status.detail!r}")
    assert status.available, f"Qdrant not available: {status.detail}"

    # 2. ensure collection
    await store.ensure_collection(TEST_COLLECTION, DIM)
    print(f"collection '{TEST_COLLECTION}' ensured at dim={DIM}")

    # 3. upsert two points
    v1 = [1.0] + [0.0] * (DIM - 1)
    v2 = [0.0, 1.0] + [0.0] * (DIM - 2)
    points = [
        VectorPoint(
            id="test_pt_1",
            vector=v1,
            payload={"doc_type": "contract", "tenant_id": "t1", "document_id": "doc_001"},
        ),
        VectorPoint(
            id="test_pt_2",
            vector=v2,
            payload={"doc_type": "invoice", "tenant_id": "t1", "document_id": "doc_002"},
        ),
    ]
    n = await store.upsert(TEST_COLLECTION, points)
    print(f"upserted {n} points")
    assert n == 2

    # 4. count
    count = await store.count(TEST_COLLECTION)
    print(f"count after upsert = {count}")
    assert count == 2

    # 5. search — nearest to v1 should be test_pt_1
    hits = await store.search(TEST_COLLECTION, v1, limit=2)
    print(f"search results: {[(h.id, round(h.score, 4)) for h in hits]}")
    assert hits, "search returned no results"
    assert hits[0].id == "test_pt_1", f"expected test_pt_1, got {hits[0].id}"

    # 6. metadata filter — only contract docs
    hits_filtered = await store.search(
        TEST_COLLECTION,
        v1,
        limit=10,
        filters={"doc_type": "contract"},
    )
    print(f"filtered hits (doc_type=contract): {[h.id for h in hits_filtered]}")
    assert all(h.payload.get("doc_type") == "contract" for h in hits_filtered), (
        "filter leaked non-contract hit"
    )
    assert any(h.id == "test_pt_1" for h in hits_filtered)

    # 7. delete by document id
    removed = await store.delete_by_document(TEST_COLLECTION, "doc_001")
    print(f"delete_by_document(doc_001) removed {removed}")
    assert removed >= 1

    # 8. verify count dropped
    count_after = await store.count(TEST_COLLECTION)
    print(f"count after delete = {count_after}")
    assert count_after == 1

    # 9. cleanup — delete remaining point and collection
    await store.delete(TEST_COLLECTION, ["test_pt_2"])

    # Qdrant has no delete_collection on the abstract API; call async client directly
    client = store._client  # type: ignore[attr-defined]
    if client is not None:
        try:
            await client.delete_collection(TEST_COLLECTION)
            print(f"collection '{TEST_COLLECTION}' deleted")
        except Exception as exc:
            print(f"cleanup warning (non-fatal): {exc}")

    print("\n✓  Qdrant live verification PASSED")


if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    asyncio.run(main())
