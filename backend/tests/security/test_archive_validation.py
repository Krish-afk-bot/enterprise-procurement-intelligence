"""Archive hardening for DOCX/XLSX uploads.

Each test builds a real ZIP container in memory. A hostile container must be
rejected from its central directory, without being extracted.
"""

from __future__ import annotations

import io
import zipfile

import pytest

from app.config.settings import Settings
from app.core.errors import FileValidationError
from app.ingestion.archive import inspect_ooxml
from app.ingestion.validation import validate_upload


def settings(**overrides) -> Settings:
    return Settings(
        app_env="test",
        jwt_secret="test-secret-not-for-production",
        **overrides,
    )


def docx_bytes(entries: dict[str, bytes] | None = None, compression: int = zipfile.ZIP_DEFLATED) -> bytes:
    entries = entries if entries is not None else {"word/document.xml": b"<w:document/>"}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=compression) as archive:
        archive.writestr("[Content_Types].xml", b"<Types/>")
        for name, data in entries.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def test_valid_docx_passes_and_reports_container_summary() -> None:
    content = docx_bytes()
    summary = inspect_ooxml(content, extension=".docx", settings=settings())
    assert summary.entry_count == 2
    assert summary.uncompressed_bytes > 0

    validated = validate_upload(
        filename="notice.docx",
        content=content,
        declared_mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        settings=settings(),
    )
    assert validated.archive is not None
    assert validated.detected_mime.endswith("wordprocessingml.document")


def test_zip_bomb_is_rejected_on_declared_expansion() -> None:
    content = docx_bytes({"word/document.xml": b"0" * (2 * 1024 * 1024)})
    with pytest.raises(FileValidationError) as excinfo:
        inspect_ooxml(content, extension=".docx", settings=settings(max_archive_uncompressed_mb=1))
    assert "expands beyond" in str(excinfo.value)


def test_high_compression_ratio_is_rejected() -> None:
    # 20 MB of zeros compresses to a few KB: a classic bomb shape.
    content = docx_bytes({"word/document.xml": b"\0" * (20 * 1024 * 1024)})
    with pytest.raises(FileValidationError) as excinfo:
        inspect_ooxml(
            content,
            extension=".docx",
            settings=settings(max_archive_uncompressed_mb=500, max_archive_compression_ratio=50),
        )
    assert "compression ratio" in str(excinfo.value)


def test_too_many_entries_is_rejected() -> None:
    entries = {f"word/part{i}.xml": b"x" for i in range(20)}
    content = docx_bytes(entries)
    with pytest.raises(FileValidationError) as excinfo:
        inspect_ooxml(content, extension=".docx", settings=settings(max_archive_entries=10))
    assert "too many embedded parts" in str(excinfo.value)


@pytest.mark.parametrize("name", ["../evil.xml", "/etc/passwd", "word/../../escape.xml"])
def test_path_traversal_entries_are_rejected(name: str) -> None:
    content = docx_bytes({name: b"x"})
    with pytest.raises(FileValidationError) as excinfo:
        inspect_ooxml(content, extension=".docx", settings=settings())
    assert "unsafe path" in str(excinfo.value)


def test_disguised_zip_without_the_marker_part_is_rejected() -> None:
    content = docx_bytes({"payload.exe": b"MZ"})
    with pytest.raises(FileValidationError) as excinfo:
        inspect_ooxml(content, extension=".docx", settings=settings())
    assert "missing word/document.xml" in str(excinfo.value)


def test_xlsx_renamed_to_docx_is_rejected_by_validation() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", b"<Types/>")
        archive.writestr("xl/workbook.xml", b"<workbook/>")
    with pytest.raises(FileValidationError):
        validate_upload(
            filename="actually-a-spreadsheet.docx",
            content=buffer.getvalue(),
            declared_mime=None,
            settings=settings(),
        )


def test_non_zip_bytes_with_docx_extension_are_rejected() -> None:
    with pytest.raises(FileValidationError):
        inspect_ooxml(b"not a zip", extension=".docx", settings=settings())
