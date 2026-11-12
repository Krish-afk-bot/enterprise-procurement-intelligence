"""Bounded upload reads.

An upload must be refused as soon as it exceeds the configured size, without
buffering the rest of the body first.
"""

from __future__ import annotations

import pytest

from app.config.settings import Settings
from app.core.errors import FileValidationError
from app.ingestion.validation import read_upload_bounded


class _StreamingUpload:
    """Minimal stand-in for FastAPI's UploadFile, serving fixed-size chunks."""

    def __init__(self, total_bytes: int, chunk_bytes: int = 64 * 1024) -> None:
        self._remaining = total_bytes
        self._chunk = chunk_bytes
        self.served = 0

    async def read(self, size: int = -1) -> bytes:
        if self._remaining <= 0:
            return b""
        take = min(size if size and size > 0 else self._chunk, self._remaining)
        self._remaining -= take
        self.served += take
        return b"x" * take


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env="test",
        max_upload_mb=1,
        jwt_secret="test-secret-not-for-production",
    )


@pytest.mark.asyncio
async def test_upload_over_the_limit_is_refused_while_streaming(settings):
    upload = _StreamingUpload(total_bytes=5 * 1024 * 1024)

    with pytest.raises(FileValidationError):
        await read_upload_bounded(upload, settings=settings)

    # It must stop near the limit instead of consuming the whole body.
    assert upload.served <= 1024 * 1024 + 1024 * 1024
    assert upload.served < 5 * 1024 * 1024


@pytest.mark.asyncio
async def test_upload_at_the_limit_is_accepted(settings):
    upload = _StreamingUpload(total_bytes=1024 * 1024)
    content = await read_upload_bounded(upload, settings=settings)
    assert len(content) == 1024 * 1024


@pytest.mark.asyncio
async def test_empty_upload_returns_empty_bytes(settings):
    upload = _StreamingUpload(total_bytes=0)
    assert await read_upload_bounded(upload, settings=settings) == b""
