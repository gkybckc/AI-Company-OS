"""
Route handlers for the AI Company OS CEO Control Center dashboard.

HTML pages:
    GET /               -> dashboard overview
    GET /projects       -> projects list
    GET /employees      -> employees list
    GET /workflow       -> workflow status
    GET /events         -> event stream timeline

JSON API endpoints (used by HTMX polling):
    GET /api/stats          -> company-level aggregate stats
    GET /api/events/recent  -> last N events (default 20)
    GET /api/projects       -> projects list as JSON
    GET /api/employees      -> employees list as JSON
    GET /api/workflow       -> workflow stats as JSON
    GET /api/memory         -> recent memory entries as JSON
    GET /api/decisions      -> decision history as JSON
    GET /api/discussions    -> discussions as JSON
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from apps.dashboard.state import DashboardState


def create_router(templates: Jinja2Templates) -> APIRouter:
    """Return an APIRouter with all dashboard routes registered."""

    router = APIRouter()

    # ------------------------------------------------------------------
    # HTML pages
    # ------------------------------------------------------------------

    @router.get("/", response_class=HTMLResponse)
    async def dashboard_home(request: Request) -> HTMLResponse:
        state = DashboardState.get()
        projects = state.list_projects()
        active_projects = [p for p in projects if p.status.value == "ACTIVE"]
        employees = state.workforce_registry.list_all()
        departments = state.department_registry.list_all()
        discussions = state.discussion_engine.list_open() + state.discussion_engine.list_closed()
        decisions = state.decision_engine.history()
        memory_entries = state.memory_engine.list_all()
        recent_events = state.event_stream.history(limit=10)
        wf_stats = state.get_workflow_stats()

        return templates.TemplateResponse(request, "dashboard.html", {
            "page": "dashboard",
            "company_name": "AI Company OS",
            "total_projects": len(projects),
            "active_projects": active_projects,
            "total_employees": len(employees),
            "active_employees": len([e for e in employees if e.status.value == "ACTIVE"]),
            "total_departments": len(departments),
            "departments": departments,
            "recent_discussions": list(reversed(discussions))[:5],
            "recent_decisions": list(reversed(decisions))[:5],
            "recent_memory": list(reversed(memory_entries))[:5],
            "recent_events": list(reversed(recent_events))[:8],
            "wf_stats": wf_stats,
        })

    @router.get("/projects", response_class=HTMLResponse)
    async def projects_page(request: Request) -> HTMLResponse:
        state = DashboardState.get()
        projects = state.list_projects()
        project_statuses = []
        for proj in projects:
            status = state.executive_engine.project_status(proj.id)
            project_statuses.append({
                "project": proj,
                "status": status,
                "tasks": state.executive_engine.list_tasks(proj.id),
            })

        return templates.TemplateResponse(request, "projects.html", {
            "page": "projects",
            "company_name": "AI Company OS",
            "project_statuses": project_statuses,
            "total_projects": len(projects),
        })

    @router.get("/employees", response_class=HTMLResponse)
    async def employees_page(request: Request) -> HTMLResponse:
        state = DashboardState.get()
        employees = state.workforce_registry.list_all()
        departments = state.department_registry.list_all()
        dept_map = {d.type.value: d.name for d in departments}

        return templates.TemplateResponse(request, "employees.html", {
            "page": "employees",
            "company_name": "AI Company OS",
            "employees": employees,
            "departments": departments,
            "dept_map": dept_map,
            "total_employees": len(employees),
            "active_employees": len([e for e in employees if e.status.value == "ACTIVE"]),
        })

    @router.get("/workflow", response_class=HTMLResponse)
    async def workflow_page(request: Request) -> HTMLResponse:
        state = DashboardState.get()
        workflows = state.workflow_engine.history()
        wf_stats = state.get_workflow_stats()
        wf_details = []
        for wf in workflows:
            current = state.workflow_engine.current_stage(wf.id)
            wf_details.append({
                "workflow": wf,
                "current_stage": current,
                "progress_pct": round(wf.progress * 100, 1),
                "completed_count": len(wf.completed_stages),
                "total_stages": len(wf.stages),
            })

        return templates.TemplateResponse(request, "workflow.html", {
            "page": "workflow",
            "company_name": "AI Company OS",
            "wf_details": wf_details,
            "wf_stats": wf_stats,
        })

    @router.get("/events", response_class=HTMLResponse)
    async def events_page(request: Request) -> HTMLResponse:
        state = DashboardState.get()
        events = list(reversed(state.event_stream.history()))
        ev_stats = state.get_event_stats()

        return templates.TemplateResponse(request, "events.html", {
            "page": "events",
            "company_name": "AI Company OS",
            "events": events[:50],
            "ev_stats": ev_stats,
        })

    # ------------------------------------------------------------------
    # JSON API endpoints
    # ------------------------------------------------------------------

    @router.get("/api/stats")
    async def api_stats() -> JSONResponse:
        state = DashboardState.get()
        projects = state.list_projects()
        employees = state.workforce_registry.list_all()
        departments = state.department_registry.list_all()
        return JSONResponse({
            "total_projects": len(projects),
            "active_projects": len([p for p in projects if p.status.value == "ACTIVE"]),
            "total_employees": len(employees),
            "active_employees": len([e for e in employees if e.status.value == "ACTIVE"]),
            "total_departments": len(departments),
            "total_events": state.event_stream.event_count(),
            "total_memory_entries": state.memory_engine.count(),
            "total_decisions": state.decision_engine.statistics()["total_decisions"],
            "total_discussions": state.discussion_engine.count(),
            "workflow_stats": state.get_workflow_stats(),
        })

    @router.get("/api/events/recent")
    async def api_events_recent(limit: int = 20) -> JSONResponse:
        state = DashboardState.get()
        events = state.event_stream.history(limit=limit)
        return JSONResponse([
            {
                "id": e.id,
                "source": e.source,
                "channel": str(e.category),
                "timestamp": e.timestamp.isoformat(),
                "payload": e.payload,
                "action": e.get_payload_value("action", ""),
            }
            for e in reversed(events)
        ])

    @router.get("/api/projects")
    async def api_projects() -> JSONResponse:
        state = DashboardState.get()
        projects = state.list_projects()
        result = []
        for proj in projects:
            ps = state.executive_engine.project_status(proj.id)
            result.append({
                "id": proj.id,
                "title": proj.title,
                "description": proj.description,
                "status": proj.status.value,
                "priority": proj.priority.value,
                "total_tasks": ps["total_tasks"],
                "completion_percentage": ps["completion_percentage"],
                "created_at": proj.created_at.isoformat(),
            })
        return JSONResponse(result)

    @router.get("/api/employees")
    async def api_employees() -> JSONResponse:
        state = DashboardState.get()
        employees = state.workforce_registry.list_all()
        return JSONResponse([
            {
                "id": e.id,
                "name": e.name,
                "role": e.role.value,
                "department": e.department.value,
                "seniority": e.seniority.value,
                "status": e.status.value,
                "skills": list(e.skills),
            }
            for e in employees
        ])

    @router.get("/api/workflow")
    async def api_workflow() -> JSONResponse:
        state = DashboardState.get()
        workflows = state.workflow_engine.history()
        wf_data = []
        for wf in workflows:
            current = state.workflow_engine.current_stage(wf.id)
            wf_data.append({
                "id": wf.id,
                "name": wf.name,
                "status": wf.status.value,
                "progress": round(wf.progress * 100, 1),
                "current_stage": current.name if current else None,
                "completed_stages": len(wf.completed_stages),
                "total_stages": len(wf.stages),
            })
        return JSONResponse({
            "workflows": wf_data,
            "stats": state.get_workflow_stats(),
        })

    @router.get("/api/memory")
    async def api_memory(limit: int = 20) -> JSONResponse:
        state = DashboardState.get()
        entries = state.memory_engine.list_all()
        recent = list(reversed(entries))[:limit]
        return JSONResponse([
            {
                "id": e.id,
                "title": e.title,
                "category": e.category.value,
                "scope": e.scope.value,
                "author": e.author,
                "tags": list(e.tags),
                "created_at": e.created_at.isoformat(),
            }
            for e in recent
        ])

    @router.get("/api/decisions")
    async def api_decisions() -> JSONResponse:
        state = DashboardState.get()
        decisions = state.decision_engine.history()
        return JSONResponse([
            {
                "id": d.id,
                "title": d.title,
                "status": d.status.value,
                "recommendation": d.recommendation,
                "confidence": round(d.confidence, 3),
                "risk_level": d.risk_level.value if d.risk_level else None,
                "requires_ceo_approval": d.requires_ceo_approval(),
                "option_count": d.option_count(),
                "created_at": d.created_at.isoformat(),
            }
            for d in decisions
        ])

    @router.get("/api/discussions")
    async def api_discussions() -> JSONResponse:
        state = DashboardState.get()
        open_discs = state.discussion_engine.list_open()
        closed_discs = state.discussion_engine.list_closed()
        all_discs = open_discs + closed_discs

        return JSONResponse([
            {
                "id": d.id,
                "topic": d.topic,
                "status": d.status.value,
                "participant_count": d.participant_count(),
                "message_count": d.message_count(),
                "has_outcome": d.has_outcome(),
                "project_id": d.project_id,
                "created_at": d.created_at.isoformat(),
            }
            for d in all_discs
        ])

    return router
