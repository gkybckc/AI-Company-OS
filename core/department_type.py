"""
Department type taxonomy for AI Company OS.

Defines the complete set of functional departments that can exist inside
the company. Each DepartmentType maps to a distinct domain of expertise.
The Executive Engine uses these types to route work to the correct
department. The DepartmentRegistry enforces one-per-type uniqueness.

Architecture reference: §2 Core Components, §3 Layer 4 (Agent Layer),
Constitution Chapter 5 (Department Authority).
"""

from enum import Enum


class DepartmentType(str, Enum):
    """
    Recognized functional departments in AI Company OS.

    The type is the department's identity contract. Two departments of the
    same type cannot coexist in the registry because the Executive Engine
    routes by type — ambiguity is a routing failure.
    """

    ENGINEERING = "Engineering"
    FRONTEND = "Frontend"
    BACKEND = "Backend"
    DATABASE = "Database"
    DESIGN = "Design"
    PRODUCT = "Product"
    MARKETING = "Marketing"
    QA = "QA"
    SECURITY = "Security"
    LEGAL = "Legal"
    FINANCE = "Finance"
    DEVOPS = "DevOps"
    RESEARCH = "Research"

    def __str__(self) -> str:
        return self.value
