"""Archive-container validation for OOXML uploads.

A DOCX/XLSX is a ZIP container, and the MIME sniff in ``validation.py`` can only
see the first four bytes. That leaves three attacks that never touch a parser:

* a **ZIP bomb** — a tiny upload that expands to gigabytes;
* **path traversal** — entries named ``../../etc/passwd`` whose names are later
  used to write files;
* a **disguised container** — an arbitrary ZIP renamed to ``.docx`` and handed
  to the extractor.

Everything here is checked from the central directory, before any entry is
decompressed, so a malicious archive is rejected without allocating its declared
size. This module never extracts the archive.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from app.config.settings import Settings
from app.core.errors import FileValidationError

#: Entry that must exist for the container to be the format its extension claims.
OOXML_REQUIRED: dict[str, str] = {
    ".docx": "word/document.xml",
    ".xlsx": "xl/workbook.xml",
    ".xlsm": "xl/workbook.xml",
}

OOXML_EXTENSIONS = frozenset(OOXML_REQUIRED)


@dataclass(slots=True)
class ArchiveSummary:
    entry_count: int
    uncompressed_bytes: int
    compressed_bytes: int
    compression_ratio: float

    def as_dict(self) -> dict[str, object]:
        return {
            "entry_count": self.entry_count,
            "uncompressed_bytes": self.uncompressed_bytes,
            "compressed_bytes": self.compressed_bytes,
            "compression_ratio": round(self.compression_ratio, 2),
        }


def _unsafe_name(name: str) -> bool:
    if not name or name.startswith(("/", "\\")):
        return True
    # Windows drive letters and UNC paths.
    if Path(name).is_absolute() or (len(name) > 1 and name[1] == ":"):
        return True
    parts = PurePosixPath(name.replace("\\", "/")).parts
    return any(part == ".." for part in parts)


def inspect_ooxml(
    content: bytes,
    *,
    extension: str,
    settings: Settings,
    filename: str | None = None,
) -> ArchiveSummary:
    """Reject a hostile or malformed OOXML container.

    The checks run against the central directory only; no entry is extracted, so
    the declared uncompressed size is never allocated by this function.
    """
    extension = extension.lower()
    label = filename or f"upload{extension}"
    if not zipfile.is_zipfile(io.BytesIO(content)):
        raise FileValidationError(
            "The file is not a valid document container.", details={"filename": label}
        )
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            infos = archive.infolist()
            if len(infos) > settings.max_archive_entries:
                raise FileValidationError(
                    "The document contains too many embedded parts.",
                    details={"entries": len(infos), "limit": settings.max_archive_entries},
                )
            names: set[str] = set()
            uncompressed = 0
            compressed = 0
            for info in infos:
                if _unsafe_name(info.filename):
                    raise FileValidationError(
                        "The document contains a part with an unsafe path.",
                        details={"filename": label},
                    )
                if info.flag_bits & 0x1:
                    raise FileValidationError(
                        "Encrypted document containers are not supported.",
                        details={"filename": label},
                    )
                uncompressed += int(info.file_size)
                compressed += int(info.compress_size)
                names.add(info.filename.replace("\\", "/").lstrip("./").lower())
    except zipfile.BadZipFile as exc:
        raise FileValidationError(
            "The document container is corrupt.", details={"filename": label}
        ) from exc

    limit_bytes = settings.max_archive_uncompressed_mb * 1024 * 1024
    if uncompressed > limit_bytes:
        raise FileValidationError(
            "The document expands beyond the allowed size.",
            details={
                "uncompressed_mb": round(uncompressed / (1024 * 1024), 1),
                "limit_mb": settings.max_archive_uncompressed_mb,
            },
        )
    ratio = uncompressed / max(1, compressed)
    if uncompressed > 10 * 1024 * 1024 and ratio > settings.max_archive_compression_ratio:
        raise FileValidationError(
            "The document's compression ratio is unsafe.",
            details={"ratio": round(ratio, 1), "limit": settings.max_archive_compression_ratio},
        )

    required = OOXML_REQUIRED.get(extension)
    if required and required not in names:
        raise FileValidationError(
            f"The file is not a valid {extension.lstrip('.')} document: "
            f"it is missing {required}.",
            details={"filename": label},
        )
    return ArchiveSummary(
        entry_count=len(infos),
        uncompressed_bytes=uncompressed,
        compressed_bytes=compressed,
        compression_ratio=ratio,
    )


__all__ = ["ArchiveSummary", "OOXML_EXTENSIONS", "OOXML_REQUIRED", "inspect_ooxml"]
