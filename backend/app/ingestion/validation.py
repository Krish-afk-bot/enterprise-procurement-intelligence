"""Upload validation (PRD s.66).

Extension, declared MIME type, *sniffed* content type and size are all checked.
A file that fails validation never reaches a parser.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.config.settings import Settings
from app.core.errors import FileValidationError
from app.ingestion.archive import OOXML_EXTENSIONS, ArchiveSummary, inspect_ooxml

#: Magic-number prefixes per supported format.
_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"%PDF-", "application/pdf"),
    (b"PK\x03\x04", "application/zip"),  # docx/xlsx are zip containers
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"II*\x00", "image/tiff"),
    (b"MM\x00*", "image/tiff"),
    (b"GIF8", "image/gif"),
)

_EXTENSION_MIME: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xlsm": "application/vnd.ms-excel.sheet.macroEnabled.12",
    ".csv": "text/csv",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".html": "text/html",
    ".htm": "text/html",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}

SUPPORTED_MIME_TYPES = sorted(set(_EXTENSION_MIME.values()))


@dataclass(slots=True)
class ValidatedUpload:
    filename: str
    extension: str
    declared_mime: str | None
    detected_mime: str
    size_bytes: int
    sha256: str
    content: bytes
    archive: ArchiveSummary | None = None

    @property
    def is_image(self) -> bool:
        return self.detected_mime.startswith("image/")

    @property
    def is_pdf(self) -> bool:
        return self.detected_mime == "application/pdf"


def sniff_mime(content: bytes, filename: str) -> str:
    for signature, mime in _SIGNATURES:
        if content.startswith(signature):
            if mime == "application/zip":
                extension = Path(filename).suffix.lower()
                return _EXTENSION_MIME.get(extension, "application/zip")
            return mime
    extension = Path(filename).suffix.lower()
    if extension in _EXTENSION_MIME:
        return _EXTENSION_MIME[extension]
    # Text formats have no magic number.
    try:
        content[:2048].decode("utf-8")
        return "text/plain"
    except UnicodeDecodeError as exc:
        raise FileValidationError(
            "The file type could not be identified.", details={"filename": filename}
        ) from exc


def validate_upload(
    *,
    filename: str,
    content: bytes,
    declared_mime: str | None,
    settings: Settings,
) -> ValidatedUpload:
    from app.core.ids import sha256_hex

    if not filename:
        raise FileValidationError("A filename is required.")
    extension = Path(filename).suffix.lower()
    if extension not in {e.lower() for e in settings.allowed_extensions}:
        raise FileValidationError(
            f"Unsupported file extension '{extension or '(none)'}'.",
            details={"allowed_extensions": settings.allowed_extensions},
        )
    if not content:
        raise FileValidationError("The uploaded file is empty.")

    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.max_upload_mb:
        raise FileValidationError(
            f"File is {size_mb:.1f} MB which exceeds the {settings.max_upload_mb} MB limit.",
            details={"max_upload_mb": settings.max_upload_mb},
        )

    detected = sniff_mime(content, filename)
    expected = _EXTENSION_MIME.get(extension)
    if expected and detected != expected:
        # zip container ambiguity (docx vs xlsx) is resolved by extension inside sniff_mime
        if detected not in {expected, "application/zip"}:
            raise FileValidationError(
                f"File content ({detected}) does not match the '{extension}' extension.",
                details={"detected_mime": detected, "expected_mime": expected},
            )

    # OOXML files are ZIP containers: check entry count, declared expansion,
    # compression ratio, path safety and the marker part before any parser sees
    # the bytes. Nothing is extracted here.
    archive: ArchiveSummary | None = None
    if extension in OOXML_EXTENSIONS:
        archive = inspect_ooxml(content, extension=extension, settings=settings, filename=filename)

    return ValidatedUpload(
        filename=Path(filename).name,
        extension=extension,
        declared_mime=declared_mime,
        detected_mime=detected,
        size_bytes=len(content),
        sha256=sha256_hex(content),
        content=content,
        archive=archive,
    )


#: Read size per chunk while streaming an upload. One megabyte keeps memory flat
#: for large PDFs without turning the read into thousands of tiny calls.
UPLOAD_CHUNK_BYTES = 1024 * 1024


async def read_upload_bounded(
    upload: object,
    *,
    settings: Settings,
    chunk_bytes: int = UPLOAD_CHUNK_BYTES,
) -> bytes:
    """Stream an upload into memory, refusing it as soon as it exceeds the limit.

    ``await upload.read()`` loads the whole body before any size check runs, so a
    client could force an arbitrarily large allocation. This reads in bounded
    chunks and raises ``FileValidationError`` on the chunk that crosses the
    configured limit, before the remaining body is consumed.
    """
    limit_bytes = settings.max_upload_mb * 1024 * 1024
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(chunk_bytes)  # type: ignore[attr-defined]
        if not chunk:
            break
        total += len(chunk)
        if total > limit_bytes:
            raise FileValidationError(
                f"File is larger than the {settings.max_upload_mb} MB limit.",
                details={"max_upload_mb": settings.max_upload_mb},
            )
        chunks.append(chunk)
    return b"".join(chunks)
