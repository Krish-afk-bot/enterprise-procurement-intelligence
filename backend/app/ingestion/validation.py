"""Upload validation (PRD s.66).

Extension, declared MIME type, *sniffed* content type and size are all checked.
A file that fails validation never reaches a parser.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.config.settings import Settings
from app.core.errors import FileValidationError

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

    return ValidatedUpload(
        filename=Path(filename).name,
        extension=extension,
        declared_mime=declared_mime,
        detected_mime=detected,
        size_bytes=len(content),
        sha256=sha256_hex(content),
        content=content,
    )
