"""Dashboard overview routes — GET / and core API endpoints."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from apps.dashboard.services.company_service import CompanyService
from apps.dashboard.state import DashboardState


def make_dashboard_router(templates: Jinja2Templates) -> APIRouter:
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse)
    async def dashboard_home(request: Request) -> HTMLResponse:
        state = DashboardState.get()
        svc = CompanyService(state)
        ctx = svc.get_dashboard_context()
        ctx["page"] = "dashboard"
        ctx["company_name"] = "AI Company OS"
        return templates.TemplateResponse(request, "dashboard.html", ctx)

    @router.get("/api/stats")
    async def api_stats() -> JSONResponse:
        return JSONResponse(CompanyService(DashboardState.get()).get_stats())

    @router.post("/api/command")
    async def api_command(request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            return JSONResponse(
                {"success": False, "error": "Gecersiz JSON."}, status_code=400
            )

        command = str(data.get("command") or "").strip()
        if len(command) < 10:
            return JSONResponse(
                {"success": False, "error": "Komut en az 10 karakter olmalidir."},
                status_code=400,
            )

        state = DashboardState.get()
        try:
            session = state.new_request(command)
            return JSONResponse(
                {
                    "success": True,
                    "session_id": session.id,
                    "request": session.request,
                    "event_count": session.event_count(),
                    "stage": str(session.current_stage),
                }
            )
        except Exception as exc:
            return JSONResponse(
                {"success": False, "error": str(exc)}, status_code=500
            )

    @router.get("/api/status")
    async def api_status() -> JSONResponse:
        return JSONResponse(
            CompanyService(DashboardState.get()).get_component_status()
        )

    @router.get("/api/command-history")
    async def api_command_history() -> JSONResponse:
        state = DashboardState.get()
        return JSONResponse(list(reversed(state.command_history)))

    @router.get("/api/agent-status")
    async def api_agent_status() -> JSONResponse:
        return JSONResponse(
            CompanyService(DashboardState.get()).list_agent_status()
        )

    return router
