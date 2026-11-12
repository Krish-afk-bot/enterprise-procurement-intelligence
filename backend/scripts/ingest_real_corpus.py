"""Import the real procurement corpus through the public API.

The corpus in ``data/real_procurement_ocds/sample/document_validation`` holds
tender notices downloaded from the UK Find a Tender Service (OCDS). Importing it
through the HTTP API rather than by writing rows directly keeps tenant scoping,
upload validation, audit logging and the ingestion queue in the loop — the same
path a real user's upload takes.

Every upload records provenance: the local file, its SHA-256, the OCDS ``ocid``,
the document type, the original portal URL and the licence. The result is written
to a manifest next to the corpus so an imported document can always be traced
back to the published notice it came from.

Usage (API running locally):

    python scripts/ingest_real_corpus.py --wait
    python scripts/ingest_real_corpus.py --dir ../data/.../document_validation --no-wait
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

SOURCE_NAME = "UK Find a Tender Service (OCDS)"
LICENSE = "OGL-UK-3.0"
SUPPORTED = {".pdf", ".docx", ".xlsx", ".xlsm", ".csv", ".txt", ".md", ".html", ".htm", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}
ACTIVE_STATUSES = {
    "uploaded",
    "queued",
    "pending",
    "processing",
    "parsing",
    "chunking",
    "embedding",
    "indexing",
    "activating",
    "running",
}
TERMINAL_FAILURES = {"failed", "cancelled", "error"}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_manifest(corpus: Path) -> dict[str, dict]:
    """Index the download manifest by checksum and by basename."""
    candidates = [
        corpus.parent / "document_download_manifest.json",
        corpus / "document_download_manifest.json",
    ]
    index: dict[str, dict] = {}
    for candidate in candidates:
        if not candidate.exists():
            continue
        raw = json.loads(candidate.read_text(encoding="utf-8"))
        for entry in raw.get("downloads", []):
            checksum = (entry.get("sha256_checksum") or "").lower()
            if checksum:
                index[checksum] = entry
        break
    return index


def login(client: httpx.Client, email: str, password: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    response.raise_for_status()
    token = response.json().get("access_token")
    if not token:
        raise SystemExit("Login succeeded but no access_token was returned.")
    return token


def document_status(client: httpx.Client, headers: dict[str, str], document_id: str) -> dict:
    response = client.get(f"/documents/{document_id}", headers=headers)
    if response.status_code >= 400:
        return {"status": f"http_{response.status_code}"}
    payload = response.json()
    return {
        "status": payload.get("status"),
        "pages": payload.get("page_count") or payload.get("pages_count"),
        "chunks": payload.get("chunk_count") or payload.get("chunks_count"),
        "error": payload.get("error_message"),
    }


def wait_for_ingestion(
    client: httpx.Client, headers: dict[str, str], ids: list[str], *, timeout: float, poll: float
) -> dict[str, dict]:
    deadline = time.time() + timeout
    statuses: dict[str, dict] = {doc_id: {} for doc_id in ids}
    while time.time() < deadline:
        pending = 0
        for doc_id in ids:
            info = document_status(client, headers, doc_id)
            statuses[doc_id] = info
            if (info.get("status") or "").lower() in ACTIVE_STATUSES:
                pending += 1
        if pending == 0:
            return statuses
        time.sleep(poll)
    return statuses


def reconcile(corpus: Path, client: httpx.Client, headers: dict[str, str], records: list[dict]) -> None:
    """Attach document ids/status to records already uploaded.

    Uploads that were accepted before the response envelope was parsed correctly
    still created documents, so provenance is rebuilt from the workspace's own
    document list by content checksum rather than re-uploading duplicates.
    """
    # The documents endpoint caps `limit`; 100 is the accepted maximum.
    response = client.get("/documents", params={"limit": 100}, headers=headers)
    response.raise_for_status()
    items = response.json().get("items", [])
    by_checksum = {item.get("checksum"): item for item in items if item.get("checksum")}
    for record in records:
        item = by_checksum.get(record["sha256"])
        if not item:
            record["detail"] = record.get("detail") or "no document with this checksum"
            continue
        record["document_id"] = item.get("id")
        record["upload_status"] = record.get("upload_status") or "already_present"
        record["final_status"] = item.get("status")
        record["pages"] = item.get("page_count")
        record["chunks"] = item.get("chunk_count")
        record["error"] = item.get("error_message")


def main() -> int:
    parser = argparse.ArgumentParser(description="Import the real OCDS tender corpus")
    parser.add_argument(
        "--dir",
        default="../data/real_procurement_ocds/sample/document_validation",
        help="corpus directory (relative to this script's parent)",
    )
    parser.add_argument("--api", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument("--email", default="admin@epi.local")
    parser.add_argument("--password", default="admin-local-password")
    parser.add_argument("--wait", dest="wait", action="store_true", default=True)
    parser.add_argument("--no-wait", dest="wait", action="store_false")
    parser.add_argument("--timeout", type=float, default=1800.0)
    parser.add_argument("--manifest-out", default=None)
    parser.add_argument(
        "--reconcile",
        action="store_true",
        help="skip uploading; rebuild the provenance manifest from documents already stored",
    )
    args = parser.parse_args()

    corpus = Path(args.dir)
    if not corpus.is_absolute():
        corpus = (Path(__file__).resolve().parent.parent / args.dir).resolve()
    if not corpus.exists():
        print(f"Corpus directory not found: {corpus}", file=sys.stderr)
        return 2

    files = sorted(path for path in corpus.iterdir() if path.is_file())
    importable = [path for path in files if path.suffix.lower() in SUPPORTED]
    skipped = [path.name for path in files if path.suffix.lower() not in SUPPORTED]
    downloads = load_manifest(corpus)

    records: list[dict] = []
    ids: list[str] = []
    with httpx.Client(base_url=args.api, timeout=180.0) as client:
        token = login(client, args.email, args.password)
        headers = {"Authorization": f"Bearer {token}"}

        if args.reconcile:
            records = [
                {
                    "file": path.name,
                    "sha256": sha256_of(path),
                    "bytes": path.stat().st_size,
                    "document_type": "tender",
                    "source": SOURCE_NAME,
                    "license": LICENSE,
                }
                for path in importable
            ]
            downloads = load_manifest(corpus)
            for record in records:
                entry = downloads.get(record["sha256"], {})
                record["ocid"] = entry.get("ocid")
                record["source_url"] = entry.get("original_url")
            importable = []

        for path in importable:
            checksum = sha256_of(path)
            entry = downloads.get(checksum, {})
            record = {
                "file": path.name,
                "sha256": checksum,
                "bytes": path.stat().st_size,
                "ocid": entry.get("ocid"),
                "document_type": entry.get("doc_type") or "tender",
                "source": SOURCE_NAME,
                "source_url": entry.get("original_url"),
                "license": LICENSE,
                "document_id": None,
                "upload_status": None,
                "detail": None,
            }
            try:
                with path.open("rb") as handle:
                    response = client.post(
                        "/documents/upload",
                        headers=headers,
                        files={"file": (path.name, handle, None)},
                        data={
                            "document_type": "tender",
                            "title": path.stem,
                            "source": SOURCE_NAME,
                            "source_url": entry.get("original_url") or "",
                            "license": LICENSE,
                            "original_id": entry.get("ocid") or "",
                            "is_synthetic": "false",
                        },
                    )
                record["upload_status"] = response.status_code
                if response.status_code >= 400:
                    record["detail"] = response.text[:300]
                else:
                    payload = response.json()
                    # The upload endpoint answers with an envelope:
                    # {"document": {...}, "job": {...}, "duplicate_of": ...}
                    document = payload.get("document") or payload
                    record["document_id"] = document.get("id")
                    record["initial_status"] = document.get("status")
                    record["duplicate_of"] = payload.get("duplicate_of")
                    if document.get("id"):
                        ids.append(document["id"])
            except Exception as exc:  # noqa: BLE001 - one bad file must not stop the import
                record["upload_status"] = "exception"
                record["detail"] = f"{type(exc).__name__}: {exc}"
            records.append(record)
            print(f"{path.name}: upload={record['upload_status']} id={record['document_id']}")

        if args.reconcile:
            print(f"Reconciling {len(records)} corpus files against stored documents ...")
            reconcile(corpus, client, headers, records)
            ids = [record["document_id"] for record in records if record.get("document_id")]

        statuses: dict[str, dict] = {}
        if args.wait and ids:
            print(f"Waiting for {len(ids)} documents to finish ingesting ...")
            statuses = wait_for_ingestion(client, headers, ids, timeout=args.timeout, poll=5.0)
            if args.reconcile:
                reconcile(corpus, client, headers, records)

    for record in records:
        doc_id = record.get("document_id")
        if doc_id and doc_id in statuses:
            record["final_status"] = statuses[doc_id].get("status")
            record["pages"] = statuses[doc_id].get("pages")
            record["chunks"] = statuses[doc_id].get("chunks")
            record["error"] = statuses[doc_id].get("error")

    summary = {
        "imported_at": datetime.now(UTC).isoformat(),
        "api": args.api,
        "mode": "reconcile" if args.reconcile else "upload",
        "corpus_directory": str(corpus),
        "source": SOURCE_NAME,
        "license": LICENSE,
        "files_found": len(files),
        "files_imported": len(records) if args.reconcile else len(importable),
        "files_skipped_unsupported": skipped,
        "documents": records,
    }
    out = Path(args.manifest_out) if args.manifest_out else corpus.parent / "ingestion_provenance.json"
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Provenance manifest: {out}")

    resolved = sum(1 for record in records if record.get("document_id"))
    accepted_upload = (200, 201, 202, "already_present")
    failed = [
        record["file"]
        for record in records
        if record.get("final_status") in TERMINAL_FAILURES
        or record.get("upload_status") not in accepted_upload
    ]
    verb = "Resolved" if args.reconcile else "Uploaded"
    print(f"{verb} {resolved}/{len(records)}; failures: {failed or 'none'}")
    return 0 if resolved and not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
