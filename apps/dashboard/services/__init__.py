"""
Dashboard service layer for AI Company OS CEO Control Center.

Services sit between route handlers and DashboardState/engine instances.
They encapsulate data aggregation and formatting logic so routes stay thin.

Import pattern:
    from apps.dashboard.services import CompanyService, EventService, ...
"""

from apps.dashboard.services.artifact_service import ArtifactService
from apps.dashboard.services.collaboration_service import CollaborationService
from apps.dashboard.services.company_service import CompanyService
from apps.dashboard.services.event_service import EventService
from apps.dashboard.services.organization_service import OrganizationService

__all__ = [
    "ArtifactService",
    "CollaborationService",
    "CompanyService",
    "EventService",
    "OrganizationService",
]
