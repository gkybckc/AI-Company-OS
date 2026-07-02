"""Employee routes — /employees page and /api/employees."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from apps.dashboard.services.company_service import CompanyService
from apps.dashboard.state import DashboardState


def make_employees_router(templates: Jinja2Templates) -> APIRouter:
    router = APIRouter()

    @router.get("/employees", response_class=HTMLResponse)
    async def employees_page(request: Request) -> HTMLResponse:
        state = DashboardState.get()
        employees = state.workforce_registry.list_all()
        departments = state.department_registry.list_all()
        dept_map = {d.type.value: d.name for d in departments}
        return templates.TemplateResponse(
            request,
            "employees.html",
            {
                "page": "employees",
                "company_name": "AI Company OS",
                "employees": employees,
                "departments": departments,
                "dept_map": dept_map,
                "total_employees": len(employees),
                "active_employees": len(
                    [e for e in employees if e.status.value == "ACTIVE"]
                ),
            },
        )

    @router.get("/api/employees")
    async def api_employees() -> JSONResponse:
        return JSONResponse(
            CompanyService(DashboardState.get()).list_employees_api()
        )

    return router
