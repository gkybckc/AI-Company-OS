"""
Company-level service for the AI Company OS dashboard.

Aggregates data from the core company engines (executive, workflow,
workforce, department, memory, decision, discussion) for use by route
handlers.  Routes call this service; the service accesses DashboardState.
"""

from typing import Any, Dict, List

from apps.dashboard.state import DashboardState


class CompanyService:
    """Read-oriented service for company-wide dashboard data."""

    def __init__(self, state: DashboardState) -> None:
        self._state = state

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate company statistics for /api/stats."""
        projects = self._state.list_projects()
        employees = self._state.workforce_registry.list_all()
        departments = self._state.department_registry.list_all()
        return {
            "total_projects": len(projects),
            "active_projects": len(
                [p for p in projects if p.status.value == "ACTIVE"]
            ),
            "total_employees": len(employees),
            "active_employees": len(
                [e for e in employees if e.status.value == "ACTIVE"]
            ),
            "total_departments": len(departments),
            "total_events": self._state.event_stream.event_count(),
            "total_memory_entries": self._state.memory_engine.count(),
            "total_decisions": self._state.decision_engine.statistics()[
                "total_decisions"
            ],
            "total_discussions": self._state.discussion_engine.count(),
            "workflow_stats": self._state.get_workflow_stats(),
        }

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    def list_projects(self) -> List[Any]:
        return self._state.list_projects()

    def list_projects_with_api_shape(self) -> List[Dict[str, Any]]:
        """Return projects serialized for /api/projects."""
        result = []
        for proj in self._state.list_projects():
            ps = self._state.executive_engine.project_status(proj.id)
            result.append(
                {
                    "id": proj.id,
                    "title": proj.title,
                    "description": proj.description,
                    "status": proj.status.value,
                    "priority": proj.priority.value,
                    "total_tasks": ps["total_tasks"],
                    "completion_percentage": ps["completion_percentage"],
                    "created_at": proj.created_at.isoformat(),
                }
            )
        return result

    def list_projects_with_status(self) -> List[Dict[str, Any]]:
        """Return enriched project data for the /projects page."""
        all_artifacts = self._state.list_artifacts()
        all_discussions = (
            self._state.discussion_engine.list_open()
            + self._state.discussion_engine.list_closed()
        )
        all_decisions = self._state.decision_engine.history()

        result = []
        for proj in self._state.list_projects():
            status = self._state.executive_engine.project_status(proj.id)
            result.append(
                {
                    "project": proj,
                    "status": status,
                    "tasks": self._state.executive_engine.list_tasks(proj.id),
                    "artifacts": [
                        a for a in all_artifacts if a.project_id == proj.id
                    ],
                    "discussions": [
                        d for d in all_discussions if d.project_id == proj.id
                    ],
                    "decisions": [
                        d for d in all_decisions if d.project_id == proj.id
                    ],
                }
            )
        return result

    # ------------------------------------------------------------------
    # Employees
    # ------------------------------------------------------------------

    def list_employees_api(self) -> List[Dict[str, Any]]:
        """Return employees serialized for /api/employees."""
        return [
            {
                "id": e.id,
                "name": e.name,
                "role": e.role.value,
                "department": e.department.value,
                "seniority": e.seniority.value,
                "status": e.status.value,
                "skills": list(e.skills),
            }
            for e in self._state.workforce_registry.list_all()
        ]

    def list_agent_status(self) -> List[Dict[str, Any]]:
        """Return agent cards with live task assignment for /api/agent-status."""
        current_tasks: Dict[str, Any] = {}
        for proj in self._state.list_projects():
            for task in self._state.executive_engine.list_tasks(proj.id):
                if task.assigned_agent and task.status.value in (
                    "ASSIGNED",
                    "WORKING",
                ):
                    if task.assigned_agent not in current_tasks:
                        current_tasks[task.assigned_agent] = {
                            "title": task.title,
                            "status": task.status.value,
                            "priority": task.priority.value,
                        }

        result = []
        for emp in self._state.workforce_registry.list_all():
            result.append(
                {
                    "id": emp.id,
                    "name": emp.name,
                    "role": emp.role.value,
                    "department": emp.department.value,
                    "seniority": emp.seniority.value,
                    "status": emp.status.value,
                    "workload": round(emp.workload * 100),
                    "skills": list(emp.skills),
                    "current_task": current_tasks.get(emp.name),
                }
            )
        return result

    # ------------------------------------------------------------------
    # Dashboard overview context
    # ------------------------------------------------------------------

    def get_dashboard_context(self) -> Dict[str, Any]:
        """Return the full context dict for the / dashboard page."""
        projects = self._state.list_projects()
        active_projects = [p for p in projects if p.status.value == "ACTIVE"]
        employees = self._state.workforce_registry.list_all()
        departments = self._state.department_registry.list_all()
        discussions = (
            self._state.discussion_engine.list_open()
            + self._state.discussion_engine.list_closed()
        )
        decisions = self._state.decision_engine.history()
        memory_entries = self._state.memory_engine.list_all()
        recent_events = self._state.event_stream.history(limit=10)
        wf_stats = self._state.get_workflow_stats()
        artifacts = self._state.list_artifacts()

        _stage_to_step = {
            "CREATED": 0,
            "ANALYZING": 1,
            "PLANNING": 2,
            "EXECUTING": 4,
            "DISCUSSING": 4,
            "FINISHED": 7,
            "FAILED": 7,
        }
        last_stage = (
            str(self._state.last_session.current_stage)
            if self._state.last_session
            else None
        )
        pipeline_step = (
            _stage_to_step.get(last_stage, -1) if last_stage else -1
        )

        return {
            "total_projects": len(projects),
            "active_projects": active_projects,
            "total_employees": len(employees),
            "active_employees": len(
                [e for e in employees if e.status.value == "ACTIVE"]
            ),
            "total_departments": len(departments),
            "departments": departments,
            "recent_discussions": list(reversed(discussions))[:5],
            "recent_decisions": list(reversed(decisions))[:5],
            "recent_memory": list(reversed(memory_entries))[:5],
            "recent_events": list(reversed(recent_events))[:8],
            "wf_stats": wf_stats,
            "artifacts": artifacts,
            "last_command": self._state.last_command,
            "last_session": self._state.last_session,
            "pipeline_step": pipeline_step,
            "command_history": list(reversed(self._state.command_history))[:5],
            "total_artifacts": len(artifacts),
        }

    # ------------------------------------------------------------------
    # Live component status
    # ------------------------------------------------------------------

    def get_component_status(self) -> Dict[str, Any]:
        """Return component status for /api/status."""
        projects = self._state.list_projects()
        wf_stats = self._state.get_workflow_stats()
        mem_count = self._state.memory_engine.count()
        dec_count = self._state.decision_engine.statistics()["total_decisions"]
        disc_count = self._state.discussion_engine.count()

        dept_status: Dict[str, str] = {}
        for dept in self._state.department_registry.list_all():
            dept_status[dept.type.value] = dept.status.value

        def _dept_status(key: str) -> str:
            s = dept_status.get(key, "")
            if s == "WORKING":
                return "ACTIVE"
            return "WAITING" if not s else "ACTIVE"

        components = [
            {"key": "planner", "label": "Planlayıcı", "status": "ACTIVE"},
            {
                "key": "executive",
                "label": "Yönetici",
                "status": "ACTIVE" if projects else "WAITING",
            },
            {
                "key": "workflow",
                "label": "İş Akışı",
                "status": (
                    "ACTIVE"
                    if wf_stats.get("total_workflows", 0) > 0
                    else "WAITING"
                ),
            },
            {"key": "backend", "label": "Arka Uç", "status": _dept_status("Backend")},
            {"key": "frontend", "label": "Ön Uç", "status": _dept_status("Frontend")},
            {"key": "qa", "label": "Test", "status": _dept_status("QA")},
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
        return {
            "components": components,
            "orchestrator_running": self._state.orchestrator._is_running,
            "last_command": self._state.last_command,
            "last_session_id": (
                self._state.last_session.id
                if self._state.last_session
                else None
            ),
        }

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------

    def get_memory_api(self, limit: int = 20) -> List[Dict[str, Any]]:
        entries = self._state.memory_engine.list_all()
        recent = list(reversed(entries))[:limit]
        return [
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
        ]

    def get_decisions_api(self) -> List[Dict[str, Any]]:
        return [
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
            for d in self._state.decision_engine.history()
        ]

    def get_discussions_api(self) -> List[Dict[str, Any]]:
        all_discs = (
            self._state.discussion_engine.list_open()
            + self._state.discussion_engine.list_closed()
        )
        return [
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
        ]
