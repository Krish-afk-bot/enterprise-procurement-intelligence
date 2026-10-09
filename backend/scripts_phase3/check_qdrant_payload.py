"""Check what metadata fields are in the Qdrant vector payload."""

import asyncio
import os
import sys

os.environ.setdefault("VECTOR_PROVIDER", "qdrant")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config.settings import reset_settings_cache  # noqa: E402

reset_settings_cache()


async def main() -> None:
    from app.providers.vector.qdrant import QdrantVectorStore

    store = QdrantVectorStore("http://localhost:6333")
    client = store._get_client()

    # Search for all points and look at a sample
    points, _ = await client.scroll(
        "procurement_chunks",
        limit=5,
        with_payload=True,
        with_vectors=False,
    )
    print(f"Sample Qdrant payloads ({len(points)} shown):")
    for pt in points:
        print(f"\n  id={pt.id}")
        for k, v in (pt.payload or {}).items():
            print(f"    {k}: {v!r}")


if __name__ == "__main__":
    asyncio.run(main())
