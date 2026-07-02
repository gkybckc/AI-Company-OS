"""
Route handlers for the AI Company OS CEO Control Center dashboard.

HTML pages:
    GET /               -> dashboard overview
    GET /projects       -> projects list
    GET /employees      -> employees list
    GET /workflow       -> workflow status
    GET /events         -> event stream timeline
    GET /org            -> company organization tree

JSON API endpoints (used by HTMX polling):
    GET /api/stats          -> company-level aggregate stats
    GET /api/events/recent  -> last N events (default 20)
    GET /api/projects       -> projects list as JSON
    GET /api/employees      -> employees list as JSON
    GET /api/workflow       -> workflow stats as JSON
    GET /api/memory         -> recent memory entries as JSON
    GET /api/decisions      -> decision history as JSON
    GET /api/discussions    -> discussions as JSON
    GET /api/timeline       -> human-readable Turkish event timeline
    GET /api/command-history -> CEO command history
    GET /api/agent-status   -> live employee/agent status cards
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates

from apps.dashboard.state import DashboardState
from core.collaboration.collaboration_manager import CollaborationHubError
from core.collaboration.conversation import ConversationStatus
from core.collaboration.conversation_message import MessageCategory, ConversationMessage
from core.collaboration.conversation_participant import ConversationParticipant
from core.collaboration.conversation_policy import ConversationPolicy
from core.collaboration.conversation_templates import TemplateType, list_templates


# ---------------------------------------------------------------------------
# Event translation helper
# ---------------------------------------------------------------------------

def _human_event(action: str, payload: Dict[str, Any], source: str = "") -> str:
    """Convert a stream event action and payload to a Turkish sentence."""
    _map: Dict[str, Any] = {
        "company_started": lambda p: "Şirket başlatıldı.",
        "project_created": lambda p: f"Yeni proje oluşturuldu: {p.get('title', '')}.",
        "employee_hired": lambda p: f"{p.get('name', '')} işe alındı ({p.get('role', '')}).",
        "workflow_started": lambda p: f"İş akışı başlatıldı: {p.get('name', '')}.",
        "stage_advanced": lambda p: f"İş akışı aşaması ilerledi: {p.get('stage', '')}.",
        "discussion_started": lambda p: f"Tartışma başlatıldı: {p.get('topic', '')}.",
        "discussion_closed": lambda p: f"Tartışma tamamlandı: {p.get('topic', '')}.",
        "decision_created": lambda p: f"Karar oluşturuldu: {p.get('title', '')}.",
        "decision_recommended": lambda p: f"Karar verildi: {p.get('recommendation', '')}.",
        "task_created": lambda p: f"Görev oluşturuldu: {p.get('title', '')}.",
        "task_assigned": lambda p: "Görev çalışana atandı.",
        "entry_stored": lambda p: f"Hafıza kaydı oluşturuldu: {p.get('title', '')}.",
        "session_started": lambda p: "CEO komutu işleme başlandı.",
        "session_finished": lambda p: "CEO komutu başarıyla tamamlandı.",
        "session_failed": lambda p: "CEO komutu başarısız oldu.",
        "department_created": lambda p: f"Departman kuruldu: {p.get('name', '')}.",
        "workflow_advanced": lambda p: "İş akışı bir sonraki aşamaya geçti.",
        "workflow_completed": lambda p: "İş akışı tamamlandı.",
        "agent_started": lambda p: f"Ajan başlatıldı: {p.get('name', '')}.",
        "discussion_posted": lambda p: "Tartışmaya yeni mesaj eklendi.",
    }
    fn = _map.get(action)
    if fn:
        return fn(payload)
    if action:
        return f"Sistem olayı: {action.replace('_', ' ')}."
    return "Sistem olayı."


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
        artifacts = state.list_artifacts()

        _stage_to_step = {
            "CREATED": 0, "ANALYZING": 1, "PLANNING": 2,
            "EXECUTING": 4, "DISCUSSING": 4, "FINISHED": 7, "FAILED": 7,
        }
        last_stage = str(state.last_session.current_stage) if state.last_session else None
        pipeline_step = _stage_to_step.get(last_stage, -1) if last_stage else -1

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
            "artifacts": artifacts,
            "last_command": state.last_command,
            "last_session": state.last_session,
            "pipeline_step": pipeline_step,
            "command_history": list(reversed(state.command_history))[:5],
            "total_artifacts": len(artifacts),
        })

    @router.get("/projects", response_class=HTMLResponse)
    async def projects_page(request: Request) -> HTMLResponse:
        state = DashboardState.get()
        projects = state.list_projects()
        all_artifacts = state.list_artifacts()
        all_discussions = state.discussion_engine.list_open() + state.discussion_engine.list_closed()
        all_decisions = state.decision_engine.history()

        project_statuses = []
        for proj in projects:
            status = state.executive_engine.project_status(proj.id)
            proj_artifacts = [a for a in all_artifacts if a.project_id == proj.id]
            proj_discussions = [d for d in all_discussions if d.project_id == proj.id]
            proj_decisions = [d for d in all_decisions if d.project_id == proj.id]
            project_statuses.append({
                "project": proj,
                "status": status,
                "tasks": state.executive_engine.list_tasks(proj.id),
                "artifacts": proj_artifacts,
                "discussions": proj_discussions,
                "decisions": proj_decisions,
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
        raw_events = list(reversed(state.event_stream.history()))
        events_with_sentences = []
        for ev in raw_events[:50]:
            action = ev.payload.get("action", "")
            events_with_sentences.append({
                "event": ev,
                "sentence": _human_event(action, ev.payload, ev.source),
            })
        ev_stats = state.get_event_stats()

        return templates.TemplateResponse(request, "events.html", {
            "page": "events",
            "company_name": "AI Company OS",
            "events_with_sentences": events_with_sentences,
            "ev_stats": ev_stats,
        })

    @router.get("/org", response_class=HTMLResponse)
    async def org_page(request: Request) -> HTMLResponse:
        state = DashboardState.get()
        employees = state.workforce_registry.list_all()
        departments = state.department_registry.list_all()
        org_data = []
        for dept in departments:
            dept_employees = [e for e in employees if e.department.value == dept.type.value]
            org_data.append({
                "department": dept,
                "employees": dept_employees,
            })

        return templates.TemplateResponse(request, "org.html", {
            "page": "org",
            "company_name": "AI Company OS",
            "org_data": org_data,
            "total_employees": len(employees),
            "total_departments": len(departments),
        })

    @router.get("/org/departments", response_class=HTMLResponse)
    async def org_departments_page(request: Request) -> HTMLResponse:
        state = DashboardState.get()
        departments = state.org_engine.list_departments()
        employees = state.org_engine.list_employees()
        roles = state.org_engine.list_roles()
        emp_map = {e.id: e for e in employees}

        dept_data = []
        for dept in departments:
            director = emp_map.get(dept.director_id) if dept.director_id else None
            members = [emp_map[m] for m in dept.members if m in emp_map]
            dept_data.append({
                "dept": dept,
                "director": director,
                "members": members,
            })

        return templates.TemplateResponse(request, "org/departments.html", {
            "page": "org_departments",
            "company_name": "AI Company OS",
            "dept_data": dept_data,
            "employees": employees,
            "roles": roles,
            "stats": state.org_engine.statistics(),
        })

    @router.get("/org/employees", response_class=HTMLResponse)
    async def org_employees_page(request: Request) -> HTMLResponse:
        state = DashboardState.get()
        employees = state.org_engine.list_employees()
        departments = state.org_engine.list_departments()
        roles = state.org_engine.list_roles()
        dept_map = {d.id: d for d in departments}
        role_map = {r.id: r for r in roles}

        emp_data = []
        for emp in employees:
            dept = dept_map.get(emp.department_id) if emp.department_id else None
            role = role_map.get(emp.role_id)
            emp_data.append({
                "emp": emp,
                "dept": dept,
                "role": role,
            })

        return templates.TemplateResponse(request, "org/employees.html", {
            "page": "org_employees",
            "company_name": "AI Company OS",
            "emp_data": emp_data,
            "departments": departments,
            "roles": roles,
            "skills": state.org_engine.list_skills(),
            "stats": state.org_engine.statistics(),
        })

    @router.get("/org/roles", response_class=HTMLResponse)
    async def org_roles_page(request: Request) -> HTMLResponse:
        state = DashboardState.get()
        roles = state.org_engine.list_roles()
        employees = state.org_engine.list_employees()
        role_counts: Dict[str, int] = {}
        for emp in employees:
            role_counts[emp.role_id] = role_counts.get(emp.role_id, 0) + 1

        role_data = []
        for role in roles:
            role_data.append({
                "role": role,
                "employee_count": role_counts.get(role.id, 0),
            })

        return templates.TemplateResponse(request, "org/roles.html", {
            "page": "org_roles",
            "company_name": "AI Company OS",
            "role_data": role_data,
            "stats": state.org_engine.statistics(),
        })

    @router.get("/org/skills", response_class=HTMLResponse)
    async def org_skills_page(request: Request) -> HTMLResponse:
        state = DashboardState.get()
        skills = state.org_engine.list_skills()
        employees = state.org_engine.list_employees()
        skill_counts: Dict[str, int] = {}
        for emp in employees:
            for sk in emp.skills:
                skill_counts[sk] = skill_counts.get(sk, 0) + 1

        skill_data = []
        for skill in skills:
            skill_data.append({
                "skill": skill,
                "employee_count": skill_counts.get(skill.name, 0),
            })

        return templates.TemplateResponse(request, "org/skills.html", {
            "page": "org_skills",
            "company_name": "AI Company OS",
            "skill_data": skill_data,
            "stats": state.org_engine.statistics(),
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

    @router.post("/api/command")
    async def api_command(request: Request) -> JSONResponse:
        """Accept a CEO command and execute it via the CompanyOrchestrator."""
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"success": False, "error": "Gecersiz JSON."}, status_code=400)

        command = str(data.get("command") or "").strip()
        if len(command) < 10:
            return JSONResponse(
                {"success": False, "error": "Komut en az 10 karakter olmalidir."},
                status_code=400,
            )

        state = DashboardState.get()
        try:
            session = state.new_request(command)
            return JSONResponse({
                "success": True,
                "session_id": session.id,
                "request": session.request,
                "event_count": session.event_count(),
                "stage": str(session.current_stage),
            })
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=500)

    @router.get("/api/status")
    async def api_status() -> JSONResponse:
        """Return live component status for the Canli Durum panel."""
        state = DashboardState.get()

        projects = state.list_projects()
        wf_stats = state.get_workflow_stats()
        mem_count = state.memory_engine.count()
        dec_count = state.decision_engine.statistics()["total_decisions"]
        disc_count = state.discussion_engine.count()

        dept_status: Dict[str, str] = {}
        for dept in state.department_registry.list_all():
            dept_status[dept.type.value] = dept.status.value

        def _dept_component_status(key: str) -> str:
            s = dept_status.get(key, "")
            if s == "WORKING":
                return "ACTIVE"
            if s in ("IDLE", "STANDBY"):
                return "WAITING"
            return "WAITING" if not s else "ACTIVE"

        components = [
            {
                "key": "planner",
                "label": "Planlayıcı",
                "status": "ACTIVE",
            },
            {
                "key": "executive",
                "label": "Yönetici",
                "status": "ACTIVE" if projects else "WAITING",
            },
            {
                "key": "workflow",
                "label": "İş Akışı",
                "status": "ACTIVE" if wf_stats.get("total_workflows", 0) > 0 else "WAITING",
            },
            {
                "key": "backend",
                "label": "Arka Uç",
                "status": _dept_component_status("Backend"),
            },
            {
                "key": "frontend",
                "label": "Ön Uç",
                "status": _dept_component_status("Frontend"),
            },
            {
                "key": "qa",
                "label": "Test",
                "status": _dept_component_status("QA"),
            },
            {
                "key": "memory",
                "label": "Kurumsal Hafıza",
                "status": "ACTIVE" if mem_count > 0 else "WAITING",
            },
            {
                "key": "decision",
                "label": "Karar Motoru",
                "status": "ACTIVE" if dec_count > 0 else "WAITING",
            },
            {
                "key": "discussion",
                "label": "Tartişma",
                "status": "ACTIVE" if disc_count > 0 else "WAITING",
            },
        ]

        return JSONResponse({
            "components": components,
            "orchestrator_running": state.orchestrator._is_running,
            "last_command": state.last_command,
            "last_session_id": state.last_session.id if state.last_session else None,
        })

    @router.get("/api/artifacts")
    async def api_artifacts() -> JSONResponse:
        """Return all generated artifacts as JSON."""
        state = DashboardState.get()
        artifacts = state.list_artifacts()
        return JSONResponse([
            {
                "id": a.id,
                "title": a.title,
                "type": a.type.value,
                "version": a.version,
                "word_count": a.word_count(),
                "generated_by": a.generated_by,
                "created_at": a.created_at.isoformat(),
                "project_id": a.project_id,
            }
            for a in artifacts
        ])

    @router.get("/api/artifacts/{artifact_id}/download")
    async def api_artifact_download(artifact_id: str) -> Response:
        """Download an artifact as a Markdown file."""
        state = DashboardState.get()
        try:
            artifact = state.artifact_engine.find_artifact(artifact_id)
        except Exception:
            return JSONResponse({"error": "Artifact bulunamadi."}, status_code=404)

        safe_title = artifact.title.replace("/", "-").replace("\\", "-")
        return Response(
            content=artifact.content,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_title}.md"'
            },
        )

    @router.get("/api/timeline")
    async def api_timeline(limit: int = 20) -> JSONResponse:
        """Return human-readable Turkish event timeline (newest first)."""
        state = DashboardState.get()
        events = state.event_stream.history(limit=limit)
        result = []
        for ev in reversed(events):
            action = ev.payload.get("action", "")
            result.append({
                "id": ev.id,
                "source": ev.source,
                "channel": str(ev.category),
                "timestamp": ev.timestamp.isoformat(),
                "timestamp_hms": ev.timestamp.strftime("%H:%M"),
                "sentence": _human_event(action, ev.payload, ev.source),
                "action": action,
            })
        return JSONResponse(result)

    @router.get("/api/command-history")
    async def api_command_history() -> JSONResponse:
        """Return CEO command history, newest first."""
        state = DashboardState.get()
        return JSONResponse(list(reversed(state.command_history)))

    @router.get("/api/agent-status")
    async def api_agent_status() -> JSONResponse:
        """Return live status cards for every employee/agent."""
        state = DashboardState.get()
        employees = state.workforce_registry.list_all()

        current_tasks: Dict[str, Any] = {}
        for proj in state.list_projects():
            for task in state.executive_engine.list_tasks(proj.id):
                if task.assigned_agent and task.status.value in ("ASSIGNED", "WORKING"):
                    if task.assigned_agent not in current_tasks:
                        current_tasks[task.assigned_agent] = {
                            "title": task.title,
                            "status": task.status.value,
                            "priority": task.priority.value,
                        }

        result = []
        for emp in employees:
            result.append({
                "id": emp.id,
                "name": emp.name,
                "role": emp.role.value,
                "department": emp.department.value,
                "seniority": emp.seniority.value,
                "status": emp.status.value,
                "workload": round(emp.workload * 100),
                "skills": list(emp.skills),
                "current_task": current_tasks.get(emp.name),
            })
        return JSONResponse(result)

    # ------------------------------------------------------------------
    # Org JSON API — Departments
    # ------------------------------------------------------------------

    @router.get("/api/org/departments")
    async def api_org_departments() -> JSONResponse:
        state = DashboardState.get()
        return JSONResponse([d.to_dict() for d in state.org_engine.list_departments()])

    @router.post("/api/org/departments")
    async def api_org_departments_create(request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"success": False, "error": "Geçersiz JSON."}, status_code=400)
        name = str(data.get("name") or "").strip()
        if not name:
            return JSONResponse({"success": False, "error": "Departman adı gerekli."}, status_code=400)
        capacity = int(data.get("capacity") or 10)
        state = DashboardState.get()
        try:
            dept = state.org_engine.create_department(name, capacity)
            return JSONResponse({"success": True, "department": dept.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.put("/api/org/departments/{dept_id}")
    async def api_org_departments_edit(dept_id: str, request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"success": False, "error": "Geçersiz JSON."}, status_code=400)
        state = DashboardState.get()
        try:
            name = data.get("name") or None
            capacity = int(data["capacity"]) if "capacity" in data else None
            dept = state.org_engine.edit_department(dept_id, name=name, capacity=capacity)
            return JSONResponse({"success": True, "department": dept.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/org/departments/{dept_id}/disable")
    async def api_org_departments_disable(dept_id: str) -> JSONResponse:
        state = DashboardState.get()
        try:
            dept = state.org_engine.disable_department(dept_id)
            return JSONResponse({"success": True, "department": dept.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/org/departments/{dept_id}/enable")
    async def api_org_departments_enable(dept_id: str) -> JSONResponse:
        state = DashboardState.get()
        try:
            dept = state.org_engine.enable_department(dept_id)
            return JSONResponse({"success": True, "department": dept.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/org/departments/{dept_id}/director")
    async def api_org_departments_assign_director(
        dept_id: str, request: Request
    ) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"success": False, "error": "Geçersiz JSON."}, status_code=400)
        emp_id = str(data.get("employee_id") or "").strip()
        if not emp_id:
            return JSONResponse({"success": False, "error": "employee_id gerekli."}, status_code=400)
        state = DashboardState.get()
        try:
            dept = state.org_engine.assign_director(dept_id, emp_id)
            return JSONResponse({"success": True, "department": dept.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    # ------------------------------------------------------------------
    # Org JSON API — Employees
    # ------------------------------------------------------------------

    @router.get("/api/org/employees")
    async def api_org_employees() -> JSONResponse:
        state = DashboardState.get()
        employees = state.org_engine.list_employees()
        result = []
        for emp in employees:
            d = emp.to_dict()
            d["role_name"] = state.org_engine.role_name(emp.role_id)
            d["department_name"] = state.org_engine.department_name(emp.department_id or "")
            result.append(d)
        return JSONResponse(result)

    @router.post("/api/org/employees")
    async def api_org_employees_create(request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"success": False, "error": "Geçersiz JSON."}, status_code=400)
        name = str(data.get("name") or "").strip()
        role_id = str(data.get("role_id") or "").strip()
        if not name:
            return JSONResponse({"success": False, "error": "Çalışan adı gerekli."}, status_code=400)
        if not role_id:
            return JSONResponse({"success": False, "error": "Rol gerekli."}, status_code=400)
        department_id = data.get("department_id") or None
        skills = data.get("skills") or []
        provider = str(data.get("provider") or "mock").strip()
        state = DashboardState.get()
        try:
            emp = state.org_engine.create_employee(
                name, role_id, department_id, skills, provider
            )
            return JSONResponse({"success": True, "employee": emp.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.put("/api/org/employees/{emp_id}")
    async def api_org_employees_edit(emp_id: str, request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"success": False, "error": "Geçersiz JSON."}, status_code=400)
        state = DashboardState.get()
        try:
            emp = state.org_engine.edit_employee(
                emp_id,
                name=data.get("name"),
                role_id=data.get("role_id"),
                provider=data.get("provider"),
            )
            return JSONResponse({"success": True, "employee": emp.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/org/employees/{emp_id}/transfer")
    async def api_org_employees_transfer(emp_id: str, request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"success": False, "error": "Geçersiz JSON."}, status_code=400)
        new_dept_id = str(data.get("department_id") or "").strip()
        if not new_dept_id:
            return JSONResponse({"success": False, "error": "department_id gerekli."}, status_code=400)
        state = DashboardState.get()
        try:
            emp = state.org_engine.transfer_employee(emp_id, new_dept_id)
            return JSONResponse({"success": True, "employee": emp.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/org/employees/{emp_id}/suspend")
    async def api_org_employees_suspend(emp_id: str) -> JSONResponse:
        state = DashboardState.get()
        try:
            emp = state.org_engine.suspend_employee(emp_id)
            return JSONResponse({"success": True, "employee": emp.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/org/employees/{emp_id}/reactivate")
    async def api_org_employees_reactivate(emp_id: str) -> JSONResponse:
        state = DashboardState.get()
        try:
            emp = state.org_engine.reactivate_employee(emp_id)
            return JSONResponse({"success": True, "employee": emp.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/org/employees/{emp_id}/terminate")
    async def api_org_employees_terminate(emp_id: str) -> JSONResponse:
        state = DashboardState.get()
        try:
            emp = state.org_engine.terminate_employee(emp_id)
            return JSONResponse({"success": True, "employee": emp.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/org/employees/{emp_id}/skills")
    async def api_org_employees_add_skill(emp_id: str, request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"success": False, "error": "Geçersiz JSON."}, status_code=400)
        skill_name = str(data.get("skill") or "").strip()
        if not skill_name:
            return JSONResponse({"success": False, "error": "skill gerekli."}, status_code=400)
        state = DashboardState.get()
        try:
            emp = state.org_engine.add_skill_to_employee(emp_id, skill_name)
            return JSONResponse({"success": True, "employee": emp.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    # ------------------------------------------------------------------
    # Org JSON API — Roles
    # ------------------------------------------------------------------

    @router.get("/api/org/roles")
    async def api_org_roles() -> JSONResponse:
        state = DashboardState.get()
        return JSONResponse([r.to_dict() for r in state.org_engine.list_roles()])

    @router.post("/api/org/roles")
    async def api_org_roles_create(request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"success": False, "error": "Geçersiz JSON."}, status_code=400)
        name = str(data.get("name") or "").strip()
        if not name:
            return JSONResponse({"success": False, "error": "Rol adı gerekli."}, status_code=400)
        description = str(data.get("description") or "").strip()
        state = DashboardState.get()
        try:
            role = state.org_engine.create_role(name, description)
            return JSONResponse({"success": True, "role": role.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.put("/api/org/roles/{role_id}")
    async def api_org_roles_edit(role_id: str, request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"success": False, "error": "Geçersiz JSON."}, status_code=400)
        state = DashboardState.get()
        try:
            role = state.org_engine.edit_role(
                role_id,
                name=data.get("name"),
                description=data.get("description"),
            )
            return JSONResponse({"success": True, "role": role.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    # ------------------------------------------------------------------
    # Org JSON API — Skills
    # ------------------------------------------------------------------

    @router.get("/api/org/skills")
    async def api_org_skills() -> JSONResponse:
        state = DashboardState.get()
        return JSONResponse([s.to_dict() for s in state.org_engine.list_skills()])

    @router.post("/api/org/skills")
    async def api_org_skills_create(request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"success": False, "error": "Geçersiz JSON."}, status_code=400)
        name = str(data.get("name") or "").strip()
        if not name:
            return JSONResponse({"success": False, "error": "Yetenek adı gerekli."}, status_code=400)
        category = str(data.get("category") or "").strip()
        state = DashboardState.get()
        try:
            skill = state.org_engine.create_skill(name, category)
            return JSONResponse({"success": True, "skill": skill.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.put("/api/org/skills/{skill_id}")
    async def api_org_skills_edit(skill_id: str, request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"success": False, "error": "Geçersiz JSON."}, status_code=400)
        state = DashboardState.get()
        try:
            skill = state.org_engine.edit_skill(
                skill_id,
                name=data.get("name"),
                category=data.get("category"),
            )
            return JSONResponse({"success": True, "skill": skill.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    # ------------------------------------------------------------------
    # Org JSON API — Statistics
    # ------------------------------------------------------------------

    @router.get("/api/org/statistics")
    async def api_org_statistics() -> JSONResponse:
        state = DashboardState.get()
        return JSONResponse(state.org_engine.statistics())

    # ==================================================================
    # Collaboration Hub — HTML pages
    # ==================================================================

    @router.get("/collab", response_class=HTMLResponse)
    async def collab_hub_page(request: Request) -> HTMLResponse:
        state = DashboardState.get()
        hub = state.collab_hub
        stats = hub.statistics()
        active = hub.list_active()
        pending = hub.list_pending_review()
        all_convs = hub.list_conversations()
        sessions = hub.list_sessions()
        policies = hub.list_policies()
        tmpl_list = list_templates()
        return templates.TemplateResponse(request, "collab/hub.html", {
            "page": "collab",
            "company_name": "AI Company OS",
            "stats": stats,
            "active_conversations": active,
            "pending_review": pending,
            "all_conversations": all_convs,
            "sessions": sessions,
            "policies": policies,
            "templates": tmpl_list,
        })

    @router.get("/collab/conversations", response_class=HTMLResponse)
    async def collab_conversations_page(request: Request) -> HTMLResponse:
        state = DashboardState.get()
        hub = state.collab_hub
        conversations = hub.list_conversations()
        stats = hub.statistics()
        all_templates = list_templates()
        return templates.TemplateResponse(request, "collab/conversations.html", {
            "page": "collab_conversations",
            "company_name": "AI Company OS",
            "conversations": conversations,
            "stats": stats,
            "all_templates": all_templates,
        })

    @router.get("/collab/sessions", response_class=HTMLResponse)
    async def collab_sessions_page(request: Request) -> HTMLResponse:
        state = DashboardState.get()
        hub = state.collab_hub
        sessions = hub.list_sessions()
        conversations = hub.list_conversations()
        stats = hub.statistics()
        return templates.TemplateResponse(request, "collab/sessions.html", {
            "page": "collab_sessions",
            "company_name": "AI Company OS",
            "sessions": sessions,
            "all_conversations": conversations,
            "stats": stats,
        })

    @router.get("/collab/policies", response_class=HTMLResponse)
    async def collab_policies_page(request: Request) -> HTMLResponse:
        state = DashboardState.get()
        hub = state.collab_hub
        policies = hub.list_policies()
        all_templates = list_templates()
        all_conversations = hub.list_conversations()
        stats_raw = hub.statistics()
        blocking = sum(1 for p in policies if p.is_blocking)
        stats_raw["blocking_policies"] = blocking
        stats_raw["non_blocking_policies"] = len(policies) - blocking
        stats_raw["total_policies"] = len(policies)
        return templates.TemplateResponse(request, "collab/policies.html", {
            "page": "collab_policies",
            "company_name": "AI Company OS",
            "policies": policies,
            "all_templates": all_templates,
            "all_conversations": all_conversations,
            "stats": stats_raw,
        })

    # ==================================================================
    # Collaboration Hub — JSON API
    # ==================================================================

    @router.get("/api/collab/conversations")
    async def api_collab_conversations() -> JSONResponse:
        state = DashboardState.get()
        convs = state.collab_hub.list_conversations()
        return JSONResponse([c.to_dict(include_messages=False) for c in convs])

    @router.get("/api/collab/conversations/{conv_id}")
    async def api_collab_conversation_detail(conv_id: str) -> JSONResponse:
        state = DashboardState.get()
        try:
            conv = state.collab_hub.get_conversation(conv_id)
            return JSONResponse(conv.to_dict(include_messages=True))
        except CollaborationHubError as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=404)

    @router.post("/api/collab/conversations")
    async def api_collab_conversations_create(request: Request) -> JSONResponse:
        state = DashboardState.get()
        try:
            data = await request.json()
            title = data.get("title", "").strip()
            creator = data.get("creator", "ceo").strip()
            project_id = data.get("project_id") or None
            task_id = data.get("task_id") or None
            template_str = data.get("template_type", "")
            template_type = None
            if template_str:
                try:
                    template_type = TemplateType(template_str)
                except ValueError:
                    pass
            if template_type:
                conv = state.collab_hub.create_from_template(
                    template_type, creator=creator,
                    project_id=project_id, task_id=task_id,
                    title_override=title or None,
                )
            else:
                conv = state.collab_hub.create_conversation(
                    title=title, creator=creator,
                    project_id=project_id, task_id=task_id,
                )
            return JSONResponse({"success": True, "conversation": conv.to_dict(include_messages=True)})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/collab/conversations/{conv_id}/join")
    async def api_collab_join(conv_id: str, request: Request) -> JSONResponse:
        state = DashboardState.get()
        try:
            data = await request.json()
            pid  = data.get("participant_id", "").strip()
            name = data.get("name", pid).strip()
            role = data.get("role", "Agent").strip()
            dept = data.get("department", "").strip()
            p = ConversationParticipant(pid, name, role, dept)
            state.collab_hub.join(conv_id, p)
            return JSONResponse({"success": True})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/collab/conversations/{conv_id}/leave")
    async def api_collab_leave(conv_id: str, request: Request) -> JSONResponse:
        state = DashboardState.get()
        try:
            data = await request.json()
            pid = data.get("participant_id", "").strip()
            state.collab_hub.leave(conv_id, pid)
            return JSONResponse({"success": True})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/collab/conversations/{conv_id}/messages")
    async def api_collab_send_message(conv_id: str, request: Request) -> JSONResponse:
        state = DashboardState.get()
        try:
            data = await request.json()
            sender   = data.get("sender", "").strip()
            receiver = data.get("receiver", "all").strip() or "all"
            cat_str  = data.get("category", "proposal").strip()
            content  = data.get("content", "").strip()
            try:
                category = MessageCategory(cat_str)
            except ValueError:
                category = MessageCategory.PROPOSAL
            msg = ConversationMessage.create(
                sender=sender, receiver=receiver,
                category=category, content=content,
            )
            state.collab_hub.send_message(conv_id, msg)
            return JSONResponse({"success": True, "message": msg.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/collab/conversations/{conv_id}/broadcast")
    async def api_collab_broadcast(conv_id: str, request: Request) -> JSONResponse:
        state = DashboardState.get()
        try:
            data    = await request.json()
            sender  = data.get("sender", "").strip()
            cat_str = data.get("category", "proposal").strip()
            content = data.get("content", "").strip()
            try:
                category = MessageCategory(cat_str)
            except ValueError:
                category = MessageCategory.PROPOSAL
            state.collab_hub.broadcast(conv_id, sender, category, content)
            return JSONResponse({"success": True})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/collab/conversations/{conv_id}/summarize")
    async def api_collab_summarize(conv_id: str) -> JSONResponse:
        state = DashboardState.get()
        try:
            summary = state.collab_hub.summarize(conv_id)
            return JSONResponse({"success": True, "summary": summary.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/collab/conversations/{conv_id}/close")
    async def api_collab_close(conv_id: str) -> JSONResponse:
        state = DashboardState.get()
        try:
            conv = state.collab_hub.close_conversation(conv_id)
            return JSONResponse({"success": True, "conversation": conv.to_dict(include_messages=False)})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/collab/conversations/{conv_id}/request-review")
    async def api_collab_request_review(conv_id: str) -> JSONResponse:
        state = DashboardState.get()
        try:
            conv = state.collab_hub.request_review(conv_id)
            return JSONResponse({"success": True, "status": conv.status.value})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/collab/conversations/{conv_id}/approve")
    async def api_collab_approve(conv_id: str) -> JSONResponse:
        state = DashboardState.get()
        try:
            conv = state.collab_hub.approve_conversation(conv_id)
            return JSONResponse({"success": True, "status": conv.status.value})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.get("/api/collab/conversations/{conv_id}/messages")
    async def api_collab_history(conv_id: str) -> JSONResponse:
        state = DashboardState.get()
        try:
            msgs = state.collab_hub.history(conv_id)
            return JSONResponse([m.to_dict() for m in msgs])
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=404)

    @router.get("/api/collab/conversations/{conv_id}/policies")
    async def api_collab_policy_check(conv_id: str) -> JSONResponse:
        state = DashboardState.get()
        try:
            violations = state.collab_hub.evaluate_policies(conv_id)
            return JSONResponse({
                "violations": [v.to_dict() for v in violations],
                "has_blocking": any(v.is_blocking for v in violations),
            })
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=404)

    # Sessions
    @router.get("/api/collab/sessions")
    async def api_collab_sessions() -> JSONResponse:
        state = DashboardState.get()
        return JSONResponse([s.to_dict() for s in state.collab_hub.list_sessions()])

    @router.post("/api/collab/sessions")
    async def api_collab_sessions_create(request: Request) -> JSONResponse:
        state = DashboardState.get()
        try:
            data = await request.json()
            title = data.get("title", "").strip()
            project_id = data.get("project_id") or None
            task_id = data.get("task_id") or None
            session = state.collab_hub.create_session(title, project_id, task_id)
            return JSONResponse({"success": True, "session": session.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/collab/sessions/{session_id}/close")
    async def api_collab_sessions_close(session_id: str) -> JSONResponse:
        state = DashboardState.get()
        try:
            session = state.collab_hub.close_session(session_id)
            return JSONResponse({"success": True, "session": session.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/collab/sessions/{session_id}/add")
    async def api_collab_sessions_add(session_id: str, request: Request) -> JSONResponse:
        state = DashboardState.get()
        try:
            data = await request.json()
            conv_id = data.get("conversation_id", "").strip()
            session = state.collab_hub.add_to_session(session_id, conv_id)
            return JSONResponse({"success": True, "session": session.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    # Policies
    @router.get("/api/collab/policies")
    async def api_collab_policies() -> JSONResponse:
        state = DashboardState.get()
        return JSONResponse([p.to_dict() for p in state.collab_hub.list_policies()])

    @router.post("/api/collab/policies")
    async def api_collab_policies_create(request: Request) -> JSONResponse:
        state = DashboardState.get()
        try:
            data = await request.json()
            policy = ConversationPolicy(
                name=data.get("name", "").strip(),
                description=data.get("description", "").strip(),
                trigger_role=data.get("trigger_role", "").strip(),
                trigger_category=data.get("trigger_category", "").strip(),
                required_reviewer_role=data.get("required_reviewer_role", "").strip(),
                required_response_category=data.get("required_response_category", "").strip(),
                is_blocking=bool(data.get("is_blocking", True)),
            )
            state.collab_hub.add_policy(policy)
            return JSONResponse({"success": True, "policy": policy.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.delete("/api/collab/policies/{policy_name}")
    async def api_collab_policies_delete(policy_name: str) -> JSONResponse:
        state = DashboardState.get()
        try:
            state.collab_hub.remove_policy(policy_name)
            return JSONResponse({"success": True})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=404)

    # Statistics
    @router.get("/api/collab/statistics")
    async def api_collab_statistics() -> JSONResponse:
        state = DashboardState.get()
        return JSONResponse(state.collab_hub.statistics())

    # Templates
    @router.get("/api/collab/templates")
    async def api_collab_templates() -> JSONResponse:
        return JSONResponse([t.to_dict() for t in list_templates()])

    return router
