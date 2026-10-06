"""Focused probe for the new document-management endpoints.

Covers: metadata update (PATCH), version history (/versions), upload-as-new-version
(replaces_document_id), validation failures, and role enforcement for a buyer.

Run from the repository root:  python scripts/verify_documents.py
Writes backend/var/verify_documents.json and cleans up the documents it creates.
Needs one non-admin account (``buyer@epi.local``) to prove role enforcement:

    cd backend && python -m app.cli create-user --email buyer@epi.local \
        --password buyer-local-password --name "Buyer verification account" --role buyer
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000/api/v1"
OUT = Path(__file__).resolve().parents[1] / "backend" / "var" / "verify_documents.json"
ADMIN = ("admin@epi.local", "admin-local-password")
BUYER = ("buyer@epi.local", "buyer-local-password")

results: list[dict] = []


def record(name: str, ok: bool, detail: object) -> None:
    results.append({"check": name, "ok": ok, "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def login(client: httpx.Client, email: str, password: str) -> str:
    response = client.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    response.raise_for_status()
    token = response.json()["access_token"]
    client.headers["authorization"] = f"Bearer {token}"
    return token


def main() -> int:
    cleanup: list[str] = []
    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
        login(client, *ADMIN)

        suppliers = client.get(f"{BASE}/suppliers", params={"limit": 5}).json()["items"]
        supplier_id = suppliers[0]["id"] if suppliers else None

        probe = OUT.with_name("verify_document_body.txt")
        probe.write_text(
            "Probe pricing note\n\n"
            "Industrial Laptop X200 unit price 1234.00 USD, minimum order quantity 50, "
            "effective 2026-01-01 for the probe verification run.\n",
            encoding="utf-8",
        )
        # The replacement carries different text: an identical file is the same
        # document (the upload endpoint returns the existing row for a known
        # checksum) and must not be counted as a new version.
        probe_v2 = OUT.with_name("verify_document_body_v2.txt")
        probe_v2.write_text(
            "Probe pricing note, second version\n\n"
            "Industrial Laptop X200 unit price 1289.00 USD, minimum order quantity 50, "
            "effective 2026-06-01 for the probe verification run.\n",
            encoding="utf-8",
        )

        # ---------------------------------------------------------------- upload
        with probe.open("rb") as handle:
            upload = client.post(
                f"{BASE}/documents/upload",
                files={"file": (probe.name, handle, "text/plain")},
                data={"document_type": "pricing_agreement", "title": "Probe pricing note"},
            )
        record("upload accepted", upload.status_code == 200, upload.status_code)
        document = upload.json()["document"]
        document_id = document["id"]
        cleanup.append(document_id)
        record("upload records version 1", document["version"] == 1, document["version"])

        # ------------------------------------------------------- metadata update
        patch = client.patch(
            f"{BASE}/documents/{document_id}",
            json={
                "title": "Probe pricing note (edited)",
                "document_type": "contract",
                "supplier_id": supplier_id,
                "effective_date": "2026-01-01",
                "expiry_date": "2027-12-31",
                "access_level": "internal",
                "revision_label": "probe rev A",
            },
        )
        record("metadata update returns 200", patch.status_code == 200, patch.status_code)
        patched = patch.json() if patch.status_code == 200 else {}
        record("title persisted", patched.get("title") == "Probe pricing note (edited)", patched.get("title"))
        record("document type persisted", patched.get("document_type") == "contract", patched.get("document_type"))
        record("revision label persisted", patched.get("revision_label") == "probe rev A", patched.get("revision_label"))
        if supplier_id:
            record(
                "supplier resolved to a name",
                patched.get("supplier_id") == supplier_id and bool(patched.get("supplier_name")),
                {"supplier_id": patched.get("supplier_id"), "supplier_name": patched.get("supplier_name")},
            )
        record("dates persisted", (patched.get("effective_date"), patched.get("expiry_date")) == ("2026-01-01", "2027-12-31"), (patched.get("effective_date"), patched.get("expiry_date")))

        reread = client.get(f"{BASE}/documents/{document_id}").json()
        record("update survives a re-read", reread["title"] == "Probe pricing note (edited)", reread["title"])
        record(
            "edit recorded in the document's own history",
            isinstance(reread.get("extraction_metadata", {}).get("metadata_edits"), list)
            and len(reread["extraction_metadata"]["metadata_edits"]) >= 1,
            reread.get("extraction_metadata", {}).get("metadata_edits"),
        )

        # ------------------------------------------------------------ validation
        bad_dates = client.patch(
            f"{BASE}/documents/{document_id}", json={"effective_date": "2027-01-01", "expiry_date": "2026-01-01"}
        )
        # 422 is this API's status for a rejected value (app.core.errors.ValidationError).
        record("expiry before effective rejected", bad_dates.status_code == 422, bad_dates.status_code)
        bad_type = client.patch(f"{BASE}/documents/{document_id}", json={"document_type": "not_a_real_type"})
        record("unknown document type rejected", bad_type.status_code == 422, bad_type.status_code)
        bad_level = client.patch(f"{BASE}/documents/{document_id}", json={"access_level": "secret"})
        record("unknown access level rejected", bad_level.status_code == 422, bad_level.status_code)
        missing = client.patch(f"{BASE}/documents/doc_does_not_exist", json={"title": "nope"})
        record("unknown document rejected", missing.status_code == 404, missing.status_code)

        # ---------------------------------------------------------------- versions
        versions = client.get(f"{BASE}/documents/{document_id}/versions")
        record("version history responds", versions.status_code == 200, versions.status_code)
        record(
            "single version before replacement",
            versions.status_code == 200 and len(versions.json()) == 1 and versions.json()[0]["is_current"] is True,
            versions.json() if versions.status_code == 200 else None,
        )

        with probe_v2.open("rb") as handle:
            replacement = client.post(
                f"{BASE}/documents/upload",
                files={"file": (probe_v2.name, handle, "text/plain")},
                data={
                    "document_type": "contract",
                    "title": "Probe pricing note (second version)",
                    "replaces_document_id": document_id,
                    "revision_label": "probe rev B",
                },
            )
        replacement_body = replacement.json() if replacement.status_code == 200 else {}
        record("replacement upload accepted", replacement.status_code == 200, replacement.status_code)
        if replacement.status_code == 200:
            if replacement_body.get("duplicate_of"):
                record("replacement is not treated as a duplicate", False, replacement_body.get("message"))
            else:
                new_document = replacement_body["document"]
                cleanup.append(new_document["id"])
                record(
                    "replacement becomes the next version",
                    new_document["version"] == 2,
                    {"version": new_document["version"], "id": new_document["id"]},
                )
                old = client.get(f"{BASE}/documents/{document_id}").json()
                record(
                    "replaced document points at its successor",
                    old.get("superseded_by_id") == new_document["id"],
                    old.get("superseded_by_id"),
                )
                chain = client.get(f"{BASE}/documents/{document_id}/versions").json()
                record(
                    "lineage lists both versions oldest first",
                    [row["version"] for row in chain] == [1, 2],
                    [{"version": row["version"], "is_current": row["is_current"], "id": row["id"]} for row in chain],
                )
                record(
                    "only the newest version is current",
                    [row["is_current"] for row in chain] == [False, True],
                    [row["is_current"] for row in chain],
                )
                record(
                    "earlier version keeps its own pages",
                    len(old.get("pages") or []) >= 1 or old.get("page_count", 0) == 0,
                    {"pages": len(old.get("pages") or []), "page_count": old.get("page_count")},
                )

        # ------------------------------------------------------------- list joins
        listing = client.get(f"{BASE}/documents", params={"search": "Probe pricing note", "limit": 10}).json()
        names = {item["title"]: item.get("supplier_name") for item in listing["items"]}
        # Only documents that actually carry a supplier id can resolve to a name.
        record(
            "list resolves supplier names for linked documents",
            bool(names) and all(value is not None for value in names.values() if value is not None) and any(
                value is not None for value in names.values()
            ),
            names,
        )

        # ------------------------------------------------------------- permissions
        with httpx.Client(timeout=60.0) as buyer_client:
            try:
                login(buyer_client, *BUYER)
                denied = buyer_client.patch(f"{BASE}/documents/{document_id}", json={"title": "buyer edit"})
                record("buyer cannot edit metadata (403)", denied.status_code == 403, denied.status_code)
                denied_upload = buyer_client.post(
                    f"{BASE}/documents/upload",
                    files={"file": ("buyer.txt", b"buyer upload attempt", "text/plain")},
                )
                record("buyer cannot upload (403)", denied_upload.status_code == 403, denied_upload.status_code)
                allowed_read = buyer_client.get(f"{BASE}/documents/{document_id}")
                record("buyer can read a document", allowed_read.status_code == 200, allowed_read.status_code)
                denied_admin = buyer_client.get(f"{BASE}/admin/stats")
                record("buyer cannot reach administration data (403)", denied_admin.status_code == 403, denied_admin.status_code)
            except httpx.HTTPStatusError as exc:
                record("buyer account exists", False, f"login failed: {exc}")

        # ----------------------------------------------------------------- cleanup
        for document_id in dict.fromkeys(cleanup):
            response = client.delete(f"{BASE}/documents/{document_id}")
            record(f"cleanup {document_id}", response.status_code in {204, 404}, response.status_code)
        probe.unlink(missing_ok=True)
        probe_v2.unlink(missing_ok=True)

    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    failed = [row for row in results if not row["ok"]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed. Written to {OUT}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
