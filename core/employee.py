"""
Employee model for AI Company OS.

An Employee is the record of a single agent in the workforce. Every agent
that performs work inside AI Company OS is represented as an Employee in the
WorkforceRegistry. The Employee record tracks their identity, role, department
assignment, status, skills, seniority, and current workload.

Employees do not execute work themselves — this module is the data model only.
Execution is handled by the Agent Runtime. The WorkforceRegistry manages state
transitions. This module defines only the structure and domain methods.

Architecture reference: §2.2 Agent Runtime, §3 Layer 4 (Agent Layer),
§5 Agent Lifecycle, Constitution Chapter 5 (Hierarchy and Roles).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from core.department_type import DepartmentType
from core.employee_role import EmployeeRole, Seniority
from core.employee_status import EmployeeStatus


class EmployeeError(Exception):
    """Base class for all employee-level errors in the workforce system."""


class InvalidWorkloadError(EmployeeError):
    """Raised when a workload value is outside the valid range [0.0, 1.0]."""


class EmployeeNotFoundError(EmployeeError):
    """Raised when an employee ID cannot be resolved in the WorkforceRegistry."""


class EmployeeAlreadyTerminatedError(EmployeeError):
    """
    Raised when an operation is attempted on a TERMINATED employee.

    A terminated employee's record is read-only. No status transitions,
    assignments, or workload updates may be applied to a terminated employee.
    """


class EmployeeNotSuspendedError(EmployeeError):
    """
    Raised when reactivate() is called on a non-SUSPENDED employee.

    Reactivation is only meaningful for SUSPENDED employees. Calling it
    on an ACTIVE, IDLE, WORKING, WAITING, or TERMINATED employee is a
    logic error in the calling code.
    """


class EmployeeAlreadySuspendedError(EmployeeError):
    """
    Raised when suspend() is called on an already-SUSPENDED employee.

    Suspending a suspended employee is a no-op that indicates a logic
    error — the caller should check status before suspending.
    """


@dataclass
class Employee:
    """
    Record of a single agent in the AI Company OS workforce.

    The Employee record is mutable — its status, workload, department, and
    director change frequently during normal company operation. The id, name,
    role, and created_at are set at hire time and do not change.

    The WorkforceRegistry is the sole authority for state transitions. External
    code should not modify Employee fields directly; it should use the registry
    methods which enforce the lifecycle rules.

    Attributes:
        id: Unique identifier (UUID string). Assigned by the registry at hire.
        name: Human-readable display name. Set from the HireRequest and does
            not change across the employee's lifecycle.
        role: The specialist role this employee fills (e.g., BACKEND_AGENT).
            Role defines what task types this employee may be assigned.
        department: The DepartmentType this employee currently belongs to.
            Changes when the employee is transferred.
        director: The ID of the Director currently managing this employee,
            or None if unassigned. A string ID is used to avoid coupling this
            module to the Director dataclass from the department system.
        status: Current lifecycle status. Managed by WorkforceRegistry.
        skills: Ordered list of specific competencies this employee possesses.
            Used by the Executive Engine to match employees to task requirements.
        seniority: Experience and authority level. Influences task assignment
            complexity and the degree of Director oversight required.
        workload: Float in [0.0, 1.0] representing what fraction of this
            employee's capacity is currently committed. 0.0 = completely idle,
            1.0 = fully committed. Updated by the WorkforceRegistry as tasks
            are assigned and completed.
        created_at: UTC timestamp of when this employee record was created
            in the WorkforceRegistry (i.e., when they were hired).
    """

    id: str
    name: str
    role: EmployeeRole
    department: DepartmentType
    director: Optional[str]
    status: EmployeeStatus
    skills: List[str]
    seniority: Seniority
    workload: float
    created_at: datetime

    def is_available(self) -> bool:
        """
        Return True if this employee can accept a new task assignment.

        An employee is available when their status is ACTIVE or IDLE and
        their current workload leaves capacity for additional work (< 1.0).
        WORKING and WAITING employees are occupied; SUSPENDED, TRANSFERRED,
        and TERMINATED employees cannot receive work.

        Returns:
            True if the employee should be considered for new assignments.
        """
        available_statuses = {EmployeeStatus.ACTIVE, EmployeeStatus.IDLE}
        return self.status in available_statuses and self.workload < 1.0

    def is_active_workforce(self) -> bool:
        """
        Return True if this employee is an active member of the workforce.

        Active workforce members are those contributing to or available for
        company operations. CANDIDATE, SUSPENDED, TRANSFERRED, and TERMINATED
        employees do not count.

        Returns:
            True for ACTIVE, IDLE, WORKING, and WAITING employees.
        """
        return self.status.is_active_workforce()

    def utilization(self) -> float:
        """
        Return workload as a percentage (0.0–100.0).

        Returns:
            Float percentage, rounded to 2 decimal places.
        """
        return round(self.workload * 100.0, 2)

    def has_skill(self, skill: str) -> bool:
        """
        Return True if this employee possesses the named skill.

        Comparison is case-insensitive to avoid mismatches from capitalization
        differences between how skills are stored vs. how they are queried.

        Args:
            skill: The skill name to check.

        Returns:
            True if the skill appears in this employee's skill list.
        """
        skill_lower = skill.lower()
        return any(s.lower() == skill_lower for s in self.skills)
