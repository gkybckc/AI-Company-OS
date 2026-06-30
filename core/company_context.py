"""
Company context model for AI Company OS.

The CompanyContext is the root container for all initialized subsystems
that the Company Orchestrator coordinates. It holds live references to the
PlannerEngine, ExecutiveEngine, DepartmentRegistry, WorkforceRegistry,
and the optional CompanyRuntime. It also tracks which project and runtime
session are currently active company-wide.

The context is created once at company startup and passed to the
CompanyOrchestrator. Subsystems are populated at creation time via the
factory method CompanyContext.create(); they can also be set manually
for testing or custom configurations.

Architecture reference: §2.1 Executive Engine, §2.2 Agent Runtime,
§3 Layers 3–5, §13 Scalability Stage 1.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from core.department_registry import DepartmentRegistry
from core.executive_engine import ExecutiveEngine
from core.planner_engine import PlannerEngine
from core.project import Project
from core.runtime import CompanyRuntime
from core.workforce_registry import WorkforceRegistry


@dataclass
class CompanyContext:
    """
    Root container for all live subsystems managed by the Company Orchestrator.

    The context is the single source of truth for which modules are attached
    to the running company. The orchestrator reads and writes through this
    object to ensure all operations target the same subsystem instances.

    The mandatory fields (company_id, company_name, executive, planner,
    departments, workforce) are set at creation and do not change. The
    optional fields (active_project, active_runtime) change as the company
    progresses through requests.

    Attributes:
        company_id: Unique identifier for this company instance (UUID string).
        company_name: Human-readable name for the company.
        executive: ExecutiveEngine instance — creates and manages projects
            and tasks.
        planner: PlannerEngine instance — analyzes CEO requests and produces
            ProjectBlueprints.
        departments: DepartmentRegistry instance — authoritative directory
            of all departments.
        workforce: WorkforceRegistry instance — authoritative directory of
            all employees.
        active_project: The Project currently being worked on by the company.
            None when no project is in progress. Set by the orchestrator when
            a new request creates a project; cleared when the session finishes.
        active_runtime: The CompanyRuntime governing the infrastructure layer.
            None until start_company() is called. Set by the orchestrator
            on startup; cleared on stop.
        created_at: UTC timestamp of when this context was instantiated.
        metadata: Optional key-value store for arbitrary company-level
            configuration or context. Never used by the orchestrator's core
            logic — available for extensions and plugins.
    """

    company_id: str
    company_name: str
    executive: ExecutiveEngine
    planner: PlannerEngine
    departments: DepartmentRegistry
    workforce: WorkforceRegistry
    active_project: Optional[Project] = None
    active_runtime: Optional[CompanyRuntime] = None
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(cls, company_name: str) -> "CompanyContext":
        """
        Factory method: create a fully initialized context for a new company.

        Instantiates all subsystems (PlannerEngine, ExecutiveEngine,
        DepartmentRegistry, WorkforceRegistry, CompanyRuntime) and wires
        them into a ready-to-use context. The CompanyRuntime is created
        but not yet started — call CompanyOrchestrator.start_company()
        to start it.

        Args:
            company_name: Human-readable name for this company.

        Returns:
            A CompanyContext with all subsystems initialized and an
            unstarted CompanyRuntime attached.
        """
        return cls(
            company_id=str(uuid4()),
            company_name=company_name,
            executive=ExecutiveEngine(),
            planner=PlannerEngine(),
            departments=DepartmentRegistry(),
            workforce=WorkforceRegistry(),
            active_project=None,
            active_runtime=CompanyRuntime(),
            created_at=datetime.now(timezone.utc),
        )

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def has_active_project(self) -> bool:
        """Return True if a project is currently active."""
        return self.active_project is not None

    def has_active_runtime(self) -> bool:
        """Return True if a CompanyRuntime is attached."""
        return self.active_runtime is not None

    def department_count(self) -> int:
        """Return the number of departments currently registered."""
        return len(self.departments.list_all())

    def employee_count(self) -> int:
        """Return the total number of employees currently in the workforce."""
        return len(self.workforce.list_all())

    def summary(self) -> Dict[str, Any]:
        """
        Return a snapshot summary of the context's current state.

        Returns:
            Dict with keys: company_id, company_name, departments,
            employees, has_active_project, has_active_runtime.
        """
        return {
            "company_id": self.company_id,
            "company_name": self.company_name,
            "departments": self.department_count(),
            "employees": self.employee_count(),
            "has_active_project": self.has_active_project(),
            "has_active_runtime": self.has_active_runtime(),
        }
