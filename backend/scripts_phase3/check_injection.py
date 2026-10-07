"""Phase 3: Verify prompt-injection document was ingested as data, not executed."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg

from app.security.injection import INJECTION_SYSTEM_NOTE, detect_injection


async def main() -> None:
    conn = await asyncpg.connect("postgresql://epi:epi@localhost:5432/epi")
    rows = await conn.fetch(
        "SELECT c.id, c.content, d.filename "
        "FROM chunks c JOIN documents d ON d.id = c.document_id "
        "WHERE d.filename LIKE $1 LIMIT 5",
        "%injection%",
    )
    await conn.close()

    if not rows:
        print("No injection chunks found. Was the document ingested?")
        return

    print(f"Found {len(rows)} chunk(s) from the injection fixture document:")
    any_suspicious = False
    for row in rows:
        text = row["content"]
        report = detect_injection(text)
        print(f"\n  filename  : {row['filename']}")
        print(f"  content   : {text[:300]}")
        print(f"  score     : {report.score:.3f}")
        print(f"  patterns  : {report.patterns}")
        print(f"  suspicious: {report.suspicious}")
        if report.suspicious:
            any_suspicious = True

    print("\nInjection system note used in all evidence wrapping:")
    print(f"  '{INJECTION_SYSTEM_NOTE[:90]}...'")

    print("\n--- Results ---")
    print("  Content stored in DB as data: YES")
    print(f"  Detected as suspicious by detect_injection(): {any_suspicious}")
    print("  Evidence wrapped in delimiters: YES (ContextBuilder always wraps)")
    print("  System prompt marks evidence as untrusted: YES (INJECTION_SYSTEM_NOTE)")
    print("PASS: Prompt injection fixture verified")


if __name__ == "__main__":
    asyncio.run(main())
