"""Shared data API routes — memory, decisions, discussions."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.dashboard.services.company_service import CompanyService
from apps.dashboard.state import DashboardState


def make_api_router() -> APIRouter:
    router = APIRouter()

    @router.get("/api/memory")
    async def api_memory(limit: int = 20) -> JSONResponse:
        return JSONResponse(
            CompanyService(DashboardState.get()).get_memory_api(limit)
        )

    @router.get("/api/decisions")
    async def api_decisions() -> JSONResponse:
        return JSONResponse(CompanyService(DashboardState.get()).get_decisions_api())

    @router.get("/api/discussions")
    async def api_discussions() -> JSONResponse:
        return JSONResponse(CompanyService(DashboardState.get()).get_discussions_api())

    return router
