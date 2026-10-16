"""Reproduce the compare endpoint 500 and capture the server traceback."""

import asyncio

import httpx

API = "http://localhost:8000/api/v1"


async def main() -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Login
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

        # Get supplier IDs
        sups = (await client.get(f"{API}/suppliers", headers=headers)).json()
        items = sups["items"]
        print(f"Suppliers: {[s['name'] for s in items]}")

        s1 = next((s["id"] for s in items if "Northwind" in s["name"]), None)
        s2 = next((s["id"] for s in items if "Helios" in s["name"]), None)

        if not s1 or not s2:
            print("ERROR: Could not find Northwind/Helios")
            return

        print(f"Comparing {s1[:20]} vs {s2[:20]}")
        r2 = await client.post(
            f"{API}/compare",
            json={"supplier_ids": [s1, s2]},
            headers={**headers, "Content-Type": "application/json"},
        )
        print(f"Status: {r2.status_code}")
        if r2.status_code == 500:
            print(f"ERROR BODY: {r2.text[:2000]}")
        else:
            data = r2.json()
            print(f"OK: {len(data.get('columns', []))} columns")


if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    asyncio.run(main())
