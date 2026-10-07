"""Phase 3: MinIO/S3 live verification via the application storage abstraction."""

from __future__ import annotations

import asyncio
import os
import sys

S3_ENDPOINT = "http://localhost:9000"
S3_ACCESS = "minioadmin"
S3_SECRET = "minioadmin"
S3_BUCKET = "epi-documents"
TEST_KEY = "phase3/test_object.txt"
TEST_CONTENT = b"Phase 3 MinIO verification payload. supplier=Acme price=92.00"


async def main() -> None:
    from app.providers.storage import S3Storage

    store = S3Storage(
        bucket=S3_BUCKET,
        endpoint=S3_ENDPOINT,
        access_key=S3_ACCESS,
        secret_key=S3_SECRET,
        region="us-east-1",
    )

    # 1. status
    status = await store.status()
    print(f"status.available={status.available}  detail={status.detail!r}")
    assert status.available, f"MinIO not available: {status.detail}"

    # 2. upload
    uri = await store.put(TEST_KEY, TEST_CONTENT, content_type="text/plain")
    print(f"put returned uri={uri!r}")

    # 3. exists
    exists = await store.exists(TEST_KEY)
    print(f"exists after put: {exists}")
    assert exists, "object should exist after put"

    # 4. retrieve and verify content
    retrieved = await store.get(TEST_KEY)
    print(f"retrieved {len(retrieved)} bytes")
    assert retrieved == TEST_CONTENT, f"content mismatch: {retrieved!r}"

    # 5. url_for
    url = await store.url_for(TEST_KEY)
    print(f"url_for: {url!r}")
    assert url is not None and ("localhost" in url or "minio" in url or S3_BUCKET in url), (
        f"unexpected url: {url!r}"
    )

    # 6. delete
    await store.delete(TEST_KEY)
    gone = await store.exists(TEST_KEY)
    print(f"exists after delete: {gone}")
    assert not gone, "object should not exist after delete"

    # 7. verify bucket is accessible (the init container created it)
    exists_before = await store.exists("non_existent_key_phase3")
    assert not exists_before

    print("✓  MinIO live verification PASSED")


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    asyncio.run(main())
