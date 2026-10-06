"""Versioned API router.

Routers are mounted here as each capability lands, so the exposed API surface
never advertises functionality that is not implemented yet.
"""

from fastapi import APIRouter

from app.api.v1 import admin, auth, documents, evaluation, graph, health, procurement, query

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(query.router)
api_router.include_router(documents.router)
api_router.include_router(procurement.router)
api_router.include_router(graph.router)
api_router.include_router(evaluation.router)
api_router.include_router(admin.router)

__all__ = ["api_router"]
