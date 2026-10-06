"""Structured procurement endpoints: suppliers, contracts, products, prices,
compliance certificates and the supplier comparison workspace.

Everything returned here is read from stored rows for the caller's tenant and is
filtered by the caller's access ceiling. Unresolved lookups are reported as
unresolved, never guessed.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ContainerDep, PrincipalDep, get_client_ip
from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.procurement import (
    ComparisonOut,
    ComparisonRequest,
    ComplianceOut,
    ContractDetailOut,
    ContractOut,
    PriceOut,
    ProductOut,
    SupplierDetailOut,
    SupplierOut,
)
from app.security import audit
from app.security.rbac import (
    PERM_COMPARE,
    PERM_CONTRACTS_READ,
    PERM_SUPPLIERS_READ,
    Principal,
)
from app.services import procurement as service

router = APIRouter(tags=["procurement"])


@router.get("/suppliers", response_model=Page[SupplierOut], summary="List suppliers")
async def list_suppliers(
    search: str | None = None,
    status: str | None = None,
    category: str | None = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
) -> Page[SupplierOut]:
    principal.require(PERM_SUPPLIERS_READ)
    items, total = await service.list_suppliers(
        session, principal, search=search, status=status, category=category, limit=limit, offset=offset
    )
    return Page[SupplierOut](
        items=[SupplierOut(**item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(items) < total,
    )


@router.get("/suppliers/{supplier_id}", response_model=SupplierDetailOut, summary="Supplier detail")
async def supplier_detail(
    supplier_id: str,
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
) -> SupplierDetailOut:
    principal.require(PERM_SUPPLIERS_READ)
    payload = await service.supplier_detail(session, principal, supplier_id)
    return SupplierDetailOut(**payload)


@router.get("/contracts", response_model=Page[ContractOut], summary="List contracts")
async def list_contracts(
    search: str | None = None,
    supplier_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
) -> Page[ContractOut]:
    principal.require(PERM_CONTRACTS_READ)
    items, total = await service.list_contracts(
        session, principal, search=search, supplier_id=supplier_id, status=status, limit=limit, offset=offset
    )
    return Page[ContractOut](
        items=[ContractOut(**item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(items) < total,
    )


@router.get(
    "/contracts/{contract_id}", response_model=ContractDetailOut, summary="Contract detail with versions"
)
async def contract_detail(
    contract_id: str,
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
) -> ContractDetailOut:
    principal.require(PERM_CONTRACTS_READ)
    payload = await service.contract_detail(session, principal, contract_id)
    return ContractDetailOut(**payload)


@router.get("/products", response_model=Page[ProductOut], summary="List products")
async def list_products(
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
) -> Page[ProductOut]:
    principal.require(PERM_SUPPLIERS_READ)
    items, total = await service.list_products(session, principal, search=search, limit=limit, offset=offset)
    return Page[ProductOut](
        items=[ProductOut(**item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(items) < total,
    )


@router.get("/prices", response_model=Page[PriceOut], summary="List negotiated prices")
async def list_prices(
    supplier_id: str | None = None,
    product_id: str | None = None,
    contract_id: str | None = None,
    as_of: date | None = None,
    current_only: bool = False,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
) -> Page[PriceOut]:
    principal.require(PERM_SUPPLIERS_READ)
    items, total = await service.list_prices(
        session,
        principal,
        supplier_id=supplier_id,
        product_id=product_id,
        contract_id=contract_id,
        as_of=as_of,
        current_only=current_only,
        limit=limit,
        offset=offset,
    )
    return Page[PriceOut](
        items=[PriceOut(**item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(items) < total,
    )


@router.get("/compliance", response_model=Page[ComplianceOut], summary="List compliance certificates")
async def list_compliance(
    supplier_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
) -> Page[ComplianceOut]:
    principal.require(PERM_CONTRACTS_READ)
    from sqlalchemy import func, select

    from app.db.models import ComplianceCertificate

    statement = select(ComplianceCertificate).where(ComplianceCertificate.tenant_id == principal.tenant_id)
    if supplier_id:
        statement = statement.where(ComplianceCertificate.supplier_id == supplier_id)
    total = int(await session.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = list(
        (
            await session.execute(
                statement.order_by(ComplianceCertificate.certificate_type).offset(offset).limit(limit)
            )
        ).scalars()
    )
    return Page[ComplianceOut](
        items=[ComplianceOut(**service.compliance_payload(row)) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(rows) < total,
    )


@router.post("/compare", response_model=ComparisonOut, summary="Compare suppliers on structured dimensions")
async def compare_suppliers(
    payload: ComparisonRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
    container=ContainerDep,
) -> ComparisonOut:
    principal.require(PERM_COMPARE)
    matrix = await service.compare(
        session,
        principal,
        supplier_ids=payload.supplier_ids,
        supplier_names=payload.supplier_names,
        product_ids=payload.product_ids,
        product_query=payload.product_query,
        as_of=payload.as_of,
    )
    await audit.record_principal_action(
        session,
        principal,
        action=audit.ACTION_COMPARE,
        resource_type="comparison",
        resource_id=",".join(payload.supplier_ids + payload.supplier_names)[:200],
        ip_address=get_client_ip(request),
        detail={"columns": len(matrix.get("columns") or []), "unresolved": matrix.get("unresolved")},
    )
    dimensions = payload.dimensions
    columns = []
    for column in matrix.get("columns") or []:
        cells = {key: value for key, value in (column.get("cells") or {}).items() if key in dimensions}
        columns.append({**column, "cells": cells})
    return ComparisonOut(
        dimensions=dimensions,
        columns=columns,
        product=matrix.get("product"),
        generated_at=matrix.get("generated_at"),
        notes=matrix.get("notes") or [],
        unresolved=matrix.get("unresolved") or [],
    )
