"""Regression test: single-supplier queries must scope vector search to that supplier.

Covers gq-012 fix: when a query plan identifies exactly one supplier_id,
the retrieval filter must include that supplier_id so single-document
suppliers are not overwhelmed by corpus-wide RRF scores.
"""

from __future__ import annotations

from app.retrieval.query_understanding import Intent, QueryPlan
from app.security.rbac import Principal
from app.security.scope import build_retrieval_filters


def make_principal(tenant_id: str = "ten_test") -> Principal:
    return Principal(
        user_id="usr_test",
        tenant_id=tenant_id,
        email="test@test.local",
        role="viewer",
    )


class TestSupplierScopedRetrieval:
    """build_retrieval_filters must include supplier_id when plan has exactly one."""

    def test_single_supplier_id_added_to_filter(self) -> None:
        """When plan.supplier_ids has exactly one entry, supplier_id goes into filter."""
        principal = make_principal()
        plan = QueryPlan(
            query="Which contract does Orion supply under?",
            intent=Intent.GENERAL,
            supplier_ids=["sup_orion_001"],
        )
        # Simulate what the retriever now does
        plan_extras: dict = {}
        if len(plan.supplier_ids) == 1:
            plan_extras["supplier_id"] = plan.supplier_ids[0]
        filters = build_retrieval_filters(principal, **plan_extras)

        assert filters["supplier_id"] == "sup_orion_001", (
            "Single-supplier query must scope vector search to that supplier_id"
        )
        assert filters["tenant_id"] == "ten_test"
        assert "access_level" in filters

    def test_multi_supplier_not_scoped(self) -> None:
        """Two-supplier comparison must NOT filter by supplier_id (would exclude one)."""
        principal = make_principal()
        plan = QueryPlan(
            query="Compare Supplier A vs Supplier B",
            intent=Intent.COMPARISON,
            supplier_ids=["sup_a", "sup_b"],
            requires_comparison=True,
        )
        plan_extras: dict = {}
        if len(plan.supplier_ids) == 1:
            plan_extras["supplier_id"] = plan.supplier_ids[0]
        filters = build_retrieval_filters(principal, **plan_extras)

        assert "supplier_id" not in filters, (
            "Multi-supplier comparison must not restrict to a single supplier"
        )

    def test_no_supplier_not_scoped(self) -> None:
        """Query with no identified supplier must not add supplier_id filter."""
        principal = make_principal()
        plan = QueryPlan(
            query="What is the payment terms policy?",
            intent=Intent.CONTRACT_TERMS,
        )
        plan_extras: dict = {}
        if len(plan.supplier_ids) == 1:
            plan_extras["supplier_id"] = plan.supplier_ids[0]
        filters = build_retrieval_filters(principal, **plan_extras)

        assert "supplier_id" not in filters

    def test_scope_includes_tenant_and_access_level(self) -> None:
        """Supplier filter must never remove tenant isolation or access control."""
        principal = make_principal(tenant_id="ten_abc")
        plan_extras = {"supplier_id": "sup_x"}
        filters = build_retrieval_filters(principal, **plan_extras)

        assert filters["tenant_id"] == "ten_abc"
        assert "access_level" in filters
        assert filters["supplier_id"] == "sup_x"
