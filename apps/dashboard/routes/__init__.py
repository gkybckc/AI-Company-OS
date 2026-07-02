"""
Dashboard routes package for AI Company OS CEO Control Center.

This package replaces the monolithic routes.py with feature-scoped routers.
The create_router() function is preserved for backward compatibility — all
existing imports continue to work:

    from apps.dashboard.routes import create_router

Internal layout:
    dashboard.py    — overview, stats, command
    projects.py     — project pages and API
    employees.py    — employee pages and API
    organization.py — org tree, CRUD for departments/employees/roles/skills
    workflow.py     — workflow pages and API
    collaboration.py— collaboration hub pages and API
    events.py       — event timeline, SSE stream endpoint
    artifacts.py    — artifact list and download
    api.py          — shared data APIs (memory, decisions, discussions)
"""

from fastapi import APIRouter
from fastapi.templating import Jinja2Templates

from apps.dashboard.routes.api import make_api_router
from apps.dashboard.routes.artifacts import make_artifacts_router
from apps.dashboard.routes.collaboration import make_collaboration_router
from apps.dashboard.routes.dashboard import make_dashboard_router
from apps.dashboard.routes.employees import make_employees_router
from apps.dashboard.routes.events import make_events_router
from apps.dashboard.routes.organization import make_organization_router
from apps.dashboard.routes.projects import make_projects_router
from apps.dashboard.routes.workflow import make_workflow_router
from apps.dashboard.services.event_service import human_event as _human_event


def create_router(templates: Jinja2Templates) -> APIRouter:
    """
    Return an APIRouter with all dashboard routes registered.

    This function signature is backward compatible with the original
    routes.py create_router() and is consumed by apps/dashboard/main.py.
    """
    router = APIRouter()

    router.include_router(make_dashboard_router(templates))
    router.include_router(make_projects_router(templates))
    router.include_router(make_employees_router(templates))
    router.include_router(make_organization_router(templates))
    router.include_router(make_workflow_router(templates))
    router.include_router(make_collaboration_router(templates))
    router.include_router(make_events_router(templates))
    router.include_router(make_artifacts_router())
    router.include_router(make_api_router())

    return router


__all__ = [
    "create_router",
    "_human_event",
    "make_dashboard_router",
    "make_projects_router",
    "make_employees_router",
    "make_organization_router",
    "make_workflow_router",
    "make_collaboration_router",
    "make_events_router",
    "make_artifacts_router",
    "make_api_router",
]
