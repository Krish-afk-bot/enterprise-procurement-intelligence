"""Phase 4 Stage 9: Security smoke tests against the live backend."""

from __future__ import annotations

import asyncio
import os
import sys
import time

API = "http://localhost:8000/api/v1"


async def main() -> None:
    import httpx

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Login once
        r = await client.post(
            f"{API}/auth/login",
            json={
                "email": "admin@epi.local",
                "password": "EpiAdmin2026!",
                "tenant_slug": "acme-procurement",
            },
        )
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        results = []

        # 1. Invalid JWT rejected
        r = await client.get(
            f"{API}/documents", headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.invalid.sig"}
        )
        p = r.status_code == 401
        results.append(("Invalid JWT rejected", p, f"HTTP {r.status_code}"))

        # 2. Expired JWT (manually crafted with old exp — test via wrong secret)
        import jwt as pyjwt

        fake_token = pyjwt.encode(
            {
                "sub": "usr_fake",
                "tid": "ten_fake",
                "role": "admin",
                "typ": "access",
                "exp": 1000000000,
                "iss": "epi",
            },
            "wrong-secret",
            algorithm="HS256",
        )
        r = await client.get(f"{API}/documents", headers={"Authorization": f"Bearer {fake_token}"})
        p = r.status_code == 401
        results.append(("Wrong-secret JWT rejected", p, f"HTTP {r.status_code}"))

        # 3. No token rejected
        r = await client.get(f"{API}/documents")
        p = r.status_code == 401
        results.append(("No-token rejected", p, f"HTTP {r.status_code}"))

        # 4. Wrong tenant cannot retrieve documents
        # Create a query with a different tenant_id in the token (fabricated)
        fake_tenant_token = pyjwt.encode(
            {
                "sub": "usr_fake",
                "tid": "ten_DIFFERENT_TENANT",
                "role": "admin",
                "typ": "access",
                "exp": int(time.time()) + 3600,
                "iss": "epi",
            },
            "dev-insecure-change-me",  # the dev default secret
            algorithm="HS256",
        )
        r = await client.get(f"{API}/documents", headers={"Authorization": f"Bearer {fake_tenant_token}"})
        # The token itself should be valid (signed with dev secret) but returns 0 docs
        # because the DB query filters by tenant_id
        if r.status_code == 200:
            other_tenant_docs = r.json().get("total", 0)
            p = other_tenant_docs == 0
            results.append(
                ("Cross-tenant isolation (different tenant sees 0 docs)", p, f"docs={other_tenant_docs}")
            )
        else:
            results.append(
                (
                    "Cross-tenant isolation (different tenant sees 0 docs)",
                    True,
                    f"HTTP {r.status_code} (rejected)",
                )
            )

        # 5. Prompt injection document was ingested and treated as data
        r = await client.post(
            f"{API}/query",
            json={
                "query": "What does the supplier onboarding note say?",
                "top_k": 5,
            },
            headers=headers,
        )
        ans = r.json()
        answer_text = ans.get("answer_text", "").lower()
        # The answer may QUOTE the injection document (correct behavior — transparency).
        # What must NOT appear is actual system internals: secrets, credentials, the
        # system prompt rules, or internal configuration values.
        system_leakage_keywords = [
            "jwt_secret",
            "llm_api_key",
            "minioadmin",
            "neo4jdev",
            "postgresql://",
            "rules:\n1. use only",
        ]
        injection_leakage = any(kw in answer_text for kw in system_leakage_keywords)
        p = not injection_leakage
        results.append(
            (
                "Prompt injection: system internals not leaked",
                p,
                f"mode={ans.get('generation_mode')} system_leaked={injection_leakage}",
            )
        )

        # 6. Admin endpoint protected from viewer
        # Register a viewer with a unique email to avoid duplicate conflicts
        import time as _time

        viewer_email = f"viewer_phase5_{int(_time.time())}@epi.local"
        r2 = await client.post(
            f"{API}/auth/register",
            json={
                "email": viewer_email,
                "password": "ViewerPass123!",
            },
        )
        if r2.status_code in (200, 201):
            vt = r2.json().get("access_token") or r2.json().get("tokens", {}).get("access_token")
            if not vt:
                # Try login
                r3 = await client.post(
                    f"{API}/auth/login",
                    json={
                        "email": viewer_email,
                        "password": "ViewerPass123!",
                        "tenant_slug": "acme-procurement",
                    },
                )
                vt = r3.json().get("access_token") if r3.status_code == 200 else None

            if vt:
                # Viewers should not be able to perform admin actions
                r_admin = await client.get(f"{API}/admin/stats", headers={"Authorization": f"Bearer {vt}"})
                p = r_admin.status_code in (401, 403)
                results.append(("Admin endpoint requires admin role", p, f"HTTP {r_admin.status_code}"))
            else:
                results.append(("Admin endpoint requires admin role", None, "viewer token not obtained"))
        else:
            results.append(
                (
                    "Admin endpoint requires admin role",
                    None,
                    f"could not register viewer: HTTP {r2.status_code}",
                )
            )

        # 7. Secrets not in logs (can only verify via health — no secrets in response)
        r_health = await client.get(f"{API}/health")
        health_text = str(r_health.json())
        has_secret = any(s in health_text for s in ["minioadmin", "neo4jdev", "EpiAdmin"])
        p = not has_secret
        results.append(("Secrets not in health response", p, "no secrets found" if p else "LEAK DETECTED"))

        # Print results
        print("\n=== SECURITY SMOKE TEST RESULTS ===")
        all_pass = True
        for name, passed, detail in results:
            status = "PASS" if passed is True else ("SKIP" if passed is None else "FAIL")
            if passed is False:
                all_pass = False
            print(f"  [{status}] {name}: {detail}")

        print(f"\nOverall: {'PASS' if all_pass else 'FAIL WITH ISSUES'}")


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    asyncio.run(main())
