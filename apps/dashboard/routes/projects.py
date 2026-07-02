"""Project routes — /projects page and /api/projects."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from apps.dashboard.services.company_service import CompanyService
from apps.dashboard.state import DashboardState


def make_projects_router(templates: Jinja2Templates) -> APIRouter:
    router = APIRouter()

    @router.get("/projects", response_class=HTMLResponse)
    async def projects_page(request: Request) -> HTMLResponse:
        svc = CompanyService(DashboardState.get())
        project_statuses = svc.list_projects_with_status()
        return templates.TemplateResponse(
            request,
            "projects.html",
            {
                "page": "projects",
                "company_name": "AI Company OS",
                "project_statuses": project_statuses,
                "total_projects": len(svc.list_projects()),
            },
        )

    @router.get("/api/projects")
    async def api_projects() -> JSONResponse:
        return JSONResponse(
            CompanyService(DashboardState.get()).list_projects_with_api_shape()
        )

    return router
