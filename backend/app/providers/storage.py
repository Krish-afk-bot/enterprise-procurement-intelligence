"""Object storage providers.

The original uploaded file, rendered page images, OCR artifacts and table
extracts all live here — never inside the database (PRD s.48).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from app.observability.logging import get_logger
from app.providers.types import ProviderStatus

logger = get_logger(__name__)

_SAFE_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_/.")


def safe_key(key: str) -> str:
    """Reject traversal attempts in storage keys."""
    cleaned = key.replace("\\", "/").lstrip("/")
    if ".." in cleaned.split("/") or any(ch not in _SAFE_CHARS for ch in cleaned):
        raise ValueError(f"unsafe storage key: {key!r}")
    return cleaned


class LocalStorage:
    name = "local"

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.root / safe_key(key)

    async def put(self, key: str, data: bytes, *, content_type: str | None = None) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_bytes, data)
        return key

    async def get(self, key: str) -> bytes:
        return await asyncio.to_thread(self._path(key).read_bytes)

    async def exists(self, key: str) -> bool:
        return self._path(key).exists()

    async def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            await asyncio.to_thread(path.unlink)

    async def url_for(self, key: str) -> str | None:
        return f"/api/v1/documents/files/{safe_key(key)}"

    async def status(self) -> ProviderStatus:
        return ProviderStatus.of("storage", self.name, True, detail=f"filesystem at {self.root}")


class S3Storage:
    name = "s3"

    def __init__(
        self,
        *,
        bucket: str,
        endpoint: str | None,
        access_key: str | None,
        secret_key: str | None,
        region: str = "us-east-1",
    ) -> None:
        self.bucket = bucket
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self._client = None

    def _get_client(self):
        if self._client is None:
            import boto3

            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
            )
        return self._client

    def _ensure_bucket(self) -> None:
        client = self._get_client()
        try:
            client.head_bucket(Bucket=self.bucket)
        except Exception:  # noqa: BLE001 - create when missing
            client.create_bucket(Bucket=self.bucket)

    async def put(self, key: str, data: bytes, *, content_type: str | None = None) -> str:
        def _run() -> str:
            self._ensure_bucket()
            self._get_client().put_object(
                Bucket=self.bucket,
                Key=safe_key(key),
                Body=data,
                ContentType=content_type or "application/octet-stream",
            )
            return key

        return await asyncio.to_thread(_run)

    async def get(self, key: str) -> bytes:
        def _run() -> bytes:
            response = self._get_client().get_object(Bucket=self.bucket, Key=safe_key(key))
            return response["Body"].read()

        return await asyncio.to_thread(_run)

    async def exists(self, key: str) -> bool:
        def _run() -> bool:
            try:
                self._get_client().head_object(Bucket=self.bucket, Key=safe_key(key))
                return True
            except Exception:  # noqa: BLE001
                return False

        return await asyncio.to_thread(_run)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(
            lambda: self._get_client().delete_object(Bucket=self.bucket, Key=safe_key(key))
        )

    async def url_for(self, key: str) -> str | None:
        def _run() -> str:
            return self._get_client().generate_presigned_url(
                "get_object", Params={"Bucket": self.bucket, "Key": safe_key(key)}, ExpiresIn=900
            )

        try:
            return await asyncio.to_thread(_run)
        except Exception:  # noqa: BLE001
            return None

    async def status(self) -> ProviderStatus:
        try:
            await asyncio.to_thread(self._ensure_bucket)
            return ProviderStatus.of(
                "storage", self.name, True, detail=f"bucket '{self.bucket}' at {self.endpoint}"
            )
        except Exception as exc:  # noqa: BLE001
            return ProviderStatus.of("storage", self.name, False, detail=f"unreachable: {type(exc).__name__}")
