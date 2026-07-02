"""Workflow routes — /workflow page and /api/workflow."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from apps.dashboard.state import DashboardState


def make_workflow_router(templates: Jinja2Templates) -> APIRouter:
    router = APIRouter()

    @router.get("/workflow", response_class=HTMLResponse)
    async def workflow_page(request: Request) -> HTMLResponse:
        state = DashboardState.get()
        workflows = state.workflow_engine.history()
        wf_stats = state.get_workflow_stats()
        wf_details = []
        for wf in workflows:
            current = state.workflow_engine.current_stage(wf.id)
            wf_details.append(
                {
                    "workflow": wf,
                    "current_stage": current,
                    "progress_pct": round(wf.progress * 100, 1),
                    "completed_count": len(wf.completed_stages),
                    "total_stages": len(wf.stages),
                }
            )
        return templates.TemplateResponse(
            request,
            "workflow.html",
            {
                "page": "workflow",
                "company_name": "AI Company OS",
                "wf_details": wf_details,
                "wf_stats": wf_stats,
            },
        )

    @router.get("/api/workflow")
    async def api_workflow() -> JSONResponse:
        state = DashboardState.get()
        workflows = state.workflow_engine.history()
        wf_data = []
        for wf in workflows:
            current = state.workflow_engine.current_stage(wf.id)
            wf_data.append(
                {
                    "id": wf.id,
                    "name": wf.name,
                    "status": wf.status.value,
                    "progress": round(wf.progress * 100, 1),
                    "current_stage": current.name if current else None,
                    "completed_stages": len(wf.completed_stages),
                    "total_stages": len(wf.stages),
                }
            )
        return JSONResponse({"workflows": wf_data, "stats": state.get_workflow_stats()})

    return router
