#!/usr/bin/env python3
"""
Create demo users for testing different roles.

Usage:
    python scripts/create_demo_users.py
    
Creates:
    - admin@epi.local (admin role)
    - buyer@epi.local (buyer role)
    - supplier@epi.local (supplier role)
    - reader@epi.local (reader role)
"""
import asyncio
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.settings import get_settings
from app.db.session import init_db, session_scope
from app.services import auth as auth_service


DEMO_USERS = [
    {
        "email": "admin@epi.local",
        "password": "admin-local-password",
        "full_name": "Platform Administrator",
        "role": "admin",
    },
    {
        "email": "buyer@epi.local",
        "password": "buyer123",
        "full_name": "Sarah Johnson",
        "role": "buyer",
    },
    {
        "email": "supplier@epi.local",
        "password": "supplier123",
        "full_name": "TechCorp Supplier Account",
        "role": "supplier",
    },
    {
        "email": "reader@epi.local",
        "password": "reader123",
        "full_name": "John Viewer",
        "role": "reader",
    },
]


async def main() -> None:
    """Create demo users for all roles."""
    settings = get_settings()
    await init_db()

    print("🔧 Creating demo users for EPI platform...\n")

    async with session_scope() as session:
        # Get or create default tenant
        tenant = await auth_service.get_or_create_default_tenant(session, settings)
        print(f"✓ Using tenant: {tenant.name} ({tenant.slug})\n")

        created = 0
        skipped = 0

        for user_data in DEMO_USERS:
            # Check if user already exists
            existing = await auth_service.get_user_by_email(
                session, tenant.id, user_data["email"]
            )

            if existing:
                print(f"⊘ {user_data['email']} - Already exists (ID: {existing.id})")
                skipped += 1
                continue

            # Create user
            try:
                user = await auth_service.create_user(
                    session,
                    tenant_id=tenant.id,
                    email=user_data["email"],
                    password=user_data["password"],
                    full_name=user_data["full_name"],
                    role=user_data["role"],
                )
                print(f"✓ {user_data['email']} - Created successfully")
                print(f"  Role: {user.role}")
                print(f"  Name: {user.full_name}")
                print(f"  ID: {user.id}")
                print()
                created += 1
            except Exception as exc:
                print(f"✗ {user_data['email']} - Failed: {exc}")
                print()

    print("\n" + "=" * 60)
    print(f"Summary: {created} created, {skipped} already existed")
    print("=" * 60)
    print("\n📋 Login Credentials:\n")

    for user in DEMO_USERS:
        print(f"  {user['role'].upper():10} → {user['email']:25} / {user['password']}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
