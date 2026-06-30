"""
Department requirement model for AI Company OS.

Defines the department taxonomy and the DepartmentRequirement record used
by the Planner Engine to specify which departments a project needs and why.
The Planner never assigns work to departments — it only declares that a
department is required and provides the rationale for that declaration.

Architecture reference: §2 Core Components, §3 Layered Architecture.
"""

from dataclasses import dataclass
from enum import Enum


class Department(str, Enum):
    """
    Functional departments available within AI Company OS.

    Each department maps to a distinct domain of expertise. The Planner
    Engine selects the relevant subset for each project based on the
    project type and detected signals.
    """

    ENGINEERING = "Engineering"
    FRONTEND = "Frontend"
    BACKEND = "Backend"
    DATABASE = "Database"
    DESIGN = "Design"
    MARKETING = "Marketing"
    QA = "QA"
    DEVOPS = "DevOps"
    LEGAL = "Legal"
    SECURITY = "Security"
    FINANCE = "Finance"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class DepartmentRequirement:
    """
    Immutable declaration that a department is required for a project.

    Produced by the Planner Engine and stored in the ProjectBlueprint.
    The rationale field explains specifically why this department is needed
    for this particular project, not just what the department does in general.

    Attributes:
        department: The department being required.
        rationale: Project-specific explanation of why this department is
            needed. Used by the Executive Engine when staffing the project.
        is_critical: True when the project cannot proceed without this
            department. False when the department adds value but is not
            a blocking dependency.
    """

    department: Department
    rationale: str
    is_critical: bool
