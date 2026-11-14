"""
End-to-end verification - uses the actual tenant ID from the DB.
"""
import asyncio
import sys

sys.path.insert(0, ".")

from app.config.container import get_container
from app.config.settings import get_settings
from app.agents.pipeline import AnswerPipeline
from app.db.session import session_scope
from app.db.models import Tenant
from sqlalchemy import select


async def run_test():
    settings = get_settings()
    container = get_container()
    await container.startup()

    # Resolve the real tenant ID from the DB (matches slugs like "acme-procurement")
    async with session_scope() as session:
        result = await session.execute(select(Tenant).where(Tenant.slug == settings.default_tenant_slug))
        tenant = result.scalar_one_or_none()
        if tenant is None:
            print(f"ERROR: No tenant found with slug '{settings.default_tenant_slug}'")
            return
        tenant_id = tenant.id
        print(f"Tenant: {tenant.name} | ID: {tenant_id}")

    from app.security.rbac import Principal
    principal = Principal(
        user_id="usr_0a30292c55594b489f17b87fad0d1daf",   # admin@epi.local
        tenant_id=tenant_id,
        email="admin@epi.local",
        role="admin",
    )

    pipeline = AnswerPipeline(container, settings)

    test_queries = [
        ("PARTY-001", "Which contracting body published tender 04f6f2_tender_10?"),
        ("SUPPLIER-001", "What contracts does Apex Industrial have?"),
        ("PRICE-001", "What is the price of Nitrile Examination Gloves?"),
        ("REFUSAL-001", "What is the capital of France?"),
    ]

    print("\n" + "=" * 80)
    print("RUNNING END-TO-END PIPELINE AUDIT")
    print("=" * 80)

    for qid, query in test_queries:
        print(f"\n--- [{qid}] Question: '{query}' ---")
        try:
            state = await pipeline.answer_state(principal=principal, question=query, debug=True)

            plan = state.get("plan")
            pd = plan.as_dict() if hasattr(plan, "as_dict") else (plan or {})
            print(f"  Intent: {pd.get('intent')} | Complexity: {pd.get('complexity')} | Method: {pd.get('method')}")
            print(f"  Suppliers linked: {pd.get('suppliers')} | Products: {pd.get('products')}")
            print(f"  Status: {state.get('status')} | Confidence: {state.get('confidence_score')}")
            answer = str(state.get("answer_text") or state.get("answer") or "")
            print(f"  Answer: {answer[:180]}...")
            citations = state.get("citations", [])
            print(f"  Citations: {len(citations)}")
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback; traceback.print_exc()

    await container.shutdown()


if __name__ == "__main__":
    asyncio.run(run_test())
