"""
Hire request value object for AI Company OS.

A HireRequest is the formal instruction to the WorkforceRegistry to bring
a new employee into the company. It is produced by the Executive Engine
after the CEO has approved a staffing decision and passed to WorkforceRegistry.hire().

The HireRequest is frozen — it represents a decision that has already been
approved and must not be modified in transit. Any change to the hiring
plan requires a new HireRequest.

Architecture reference: §2.1 Executive Engine, §3 Layer 5 (Coordination),
Constitution Chapter 3 (CEO Rights — all hiring requires CEO approval).
"""

from dataclasses import dataclass
from typing import List, Optional

from core.department_type import DepartmentType
from core.employee_role import EmployeeRole, Seniority


class InvalidHireRequestError(Exception):
    """Raised when a HireRequest fails validation before hire is executed."""


@dataclass(frozen=True)
class HireRequest:
    """
    Immutable instruction to hire a new employee into the workforce.

    Created by the Executive Engine once the CEO has authorized the hire.
    Passed to WorkforceRegistry.hire() which validates it and produces an
    Employee record.

    All fields except director_id are required. The director assignment
    can be deferred to after the employee is onboarded — some departments
    may be building their leadership structure at the same time as hiring.

    Attributes:
        name: Human-readable display name for this employee
            (e.g., "Alice — Backend Agent 01"). Must be non-empty.
        role: The specialist role this employee will fill.
        department: The department this employee is hired into.
        seniority: The experience and authority level of this employee.
        skills: Ordered list of specific skills this employee brings.
            May be empty if skills will be profiled after onboarding.
        director_id: Optional ID of the Director who will manage this
            employee. If None, the employee is hired without a Director
            assignment and one must be provided via assign_director().
    """

    name: str
    role: EmployeeRole
    department: DepartmentType
    seniority: Seniority
    skills: List[str]
    director_id: Optional[str] = None

    def __post_init__(self) -> None:
        """
        Validate the hire request on construction.

        Raises:
            InvalidHireRequestError: If name is empty or whitespace-only.
        """
        if not self.name or not self.name.strip():
            raise InvalidHireRequestError(
                "HireRequest.name must be a non-empty string. "
                "Every employee must have a display name."
            )
