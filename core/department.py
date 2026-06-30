"""
Department model for AI Company OS.

A Department is the organizational unit through which all work is executed.
The Executive Engine routes projects and tasks to departments, never directly
to individual agents. Departments own their internal execution: their Director
assigns work to specialist agents, monitors progress, and escalates when needed.

This module defines the Department dataclass, the DepartmentHealth value object,
and the exceptions raised when department operations fail.

Architecture reference: §2 Core Components, §3 Layer 4 (Agent Layer),
§6 Communication Model, Constitution Chapter 5.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from core.department_status import DepartmentStatus
from core.department_type import DepartmentType
from core.director import Director


class DepartmentError(Exception):
    """Base class for all department-level errors."""


class InvalidWorkloadError(DepartmentError):
    """Raised when a workload value is outside the valid range [0.0, 1.0]."""


class InvalidCapacityError(DepartmentError):
    """Raised when a capacity value is not a positive integer."""


class MemberNotFoundError(DepartmentError):
    """Raised when an agent ID is not found in a department's member list."""


@dataclass(frozen=True)
class DepartmentHealth:
    """
    Immutable point-in-time health snapshot for a single department.

    Produced by the DepartmentRegistry's health_report() method. This is
    a value object — it reflects the department's state at the moment the
    report was generated and does not update automatically.

    Attributes:
        department_id: Unique identifier of the department.
        department_name: Human-readable department name.
        department_type: The department's functional type.
        status: Current operational status of the department.
        utilization: Workload expressed as a percentage (0.0–100.0).
        active_projects: Number of projects currently assigned.
        active_tasks: Number of tasks currently in progress.
        capacity: Maximum capacity (agents or concurrent tasks).
        free_capacity: Estimated unused capacity units.
        member_count: Number of agents currently in the department.
        has_director: True if a director is currently assigned.
        bottlenecks: List of identified bottleneck descriptions.
            Empty when the department is healthy.
        overall_health: Human-readable health grade: "OK", "WARNING",
            or "CRITICAL".
    """

    department_id: str
    department_name: str
    department_type: DepartmentType
    status: DepartmentStatus
    utilization: float
    active_projects: int
    active_tasks: int
    capacity: int
    free_capacity: int
    member_count: int
    has_director: bool
    bottlenecks: List[str]
    overall_health: str


@dataclass
class Department:
    """
    Organizational unit through which all work in AI Company OS is executed.

    A Department is mutable because its operational state changes continuously:
    the director is assigned after creation, members join and leave, projects
    and tasks are added and completed, workload fluctuates, and status
    transitions as the department's load changes.

    The id, name, type, and created_at fields are set at construction and
    should not be changed thereafter under normal operation.

    The Executive Engine communicates ONLY with departments — never with
    individual agents. This constraint ensures that the authority hierarchy
    defined in the Constitution (Chapter 5) is structurally enforced.

    Attributes:
        id: Unique identifier (UUID string).
        name: Human-readable department name (e.g., "Backend Department").
        type: Functional type — determines what kind of work this department
            can accept and how the Executive Engine routes to it.
        director: The current Director, or None if unassigned. A department
            without a director is operationally impaired and should be set
            to OFFLINE status.
        members: Ordered list of agent IDs currently assigned to this
            department. The Director manages these agents.
        status: Current operational status.
        capacity: Maximum number of agents or concurrent tasks this
            department can handle. Must be a positive integer.
        active_projects: List of project IDs currently assigned to this
            department. These are in-progress, not queued.
        active_tasks: List of task IDs currently being worked on within
            this department.
        workload: Float in [0.0, 1.0] representing what fraction of
            capacity is currently utilized. 0.0 = idle, 1.0 = fully
            loaded, > 0.9 typically triggers OVERLOADED status.
        created_at: UTC timestamp of when this department was first
            registered with the company.
    """

    id: str
    name: str
    type: DepartmentType
    director: Optional[Director]
    members: List[str]
    status: DepartmentStatus
    capacity: int
    active_projects: List[str]
    active_tasks: List[str]
    workload: float
    created_at: datetime

    def utilization(self) -> float:
        """
        Return workload expressed as a percentage (0.0–100.0).

        Returns:
            Float percentage. 0.0 when idle, 100.0 when fully loaded.
        """
        return round(self.workload * 100.0, 2)

    def free_capacity(self) -> int:
        """
        Return the estimated number of unused capacity units.

        Computed as floor(capacity × (1.0 − workload)). This is an
        approximation — it reflects available capacity, not guaranteed
        availability.

        Returns:
            Non-negative integer. Zero when fully loaded or overloaded.
        """
        return max(0, int(self.capacity * (1.0 - self.workload)))

    def is_available(self) -> bool:
        """
        Return True if this department can receive new work.

        A department is available when it is in READY or WORKING status
        (not BLOCKED, WAITING, OVERLOADED, or OFFLINE) and has remaining
        capacity.

        Returns:
            True if the department should receive new assignments.
        """
        active_statuses = {DepartmentStatus.READY, DepartmentStatus.WORKING}
        return self.status in active_statuses and self.free_capacity() > 0

    def has_director(self) -> bool:
        """
        Return True if a director is currently assigned.

        Returns:
            True when self.director is not None.
        """
        return self.director is not None

    def compute_health(self) -> DepartmentHealth:
        """
        Compute and return an immutable health snapshot for this department.

        Evaluates the current state and produces a DepartmentHealth record
        with a human-readable overall grade and a list of specific bottlenecks.

        Health grades:
            "OK"       — workload < 70 % and no blocking status.
            "WARNING"  — workload 70–89 % or WAITING status.
            "CRITICAL" — workload ≥ 90 % or BLOCKED/OVERLOADED/OFFLINE status.

        Returns:
            A frozen DepartmentHealth snapshot.
        """
        bottlenecks: List[str] = []

        if self.director is None:
            bottlenecks.append("No director assigned — department cannot distribute work.")

        if self.status == DepartmentStatus.OFFLINE:
            bottlenecks.append("Department is offline — no agents or director are operational.")
        elif self.status == DepartmentStatus.BLOCKED:
            bottlenecks.append("Department is blocked — a hard dependency is unresolved.")
        elif self.status == DepartmentStatus.OVERLOADED:
            bottlenecks.append(
                f"Department is overloaded ({self.utilization():.0f}% utilized) "
                "— new work must not be routed here."
            )
        elif self.workload >= 0.90:
            bottlenecks.append(
                f"Workload is critically high ({self.utilization():.0f}%) "
                "— capacity exhaustion imminent."
            )
        elif self.workload >= 0.70:
            bottlenecks.append(
                f"Workload is elevated ({self.utilization():.0f}%) "
                "— monitor closely before assigning additional work."
            )

        if len(self.active_projects) > max(1, self.capacity // 2):
            bottlenecks.append(
                f"High project count ({len(self.active_projects)} active) "
                "relative to capacity."
            )

        # Determine overall health grade.
        critical_statuses = {
            DepartmentStatus.BLOCKED,
            DepartmentStatus.OVERLOADED,
            DepartmentStatus.OFFLINE,
        }
        if self.status in critical_statuses or self.workload >= 0.90:
            overall_health = "CRITICAL"
        elif self.workload >= 0.70 or self.status == DepartmentStatus.WAITING:
            overall_health = "WARNING"
        else:
            overall_health = "OK"

        return DepartmentHealth(
            department_id=self.id,
            department_name=self.name,
            department_type=self.type,
            status=self.status,
            utilization=self.utilization(),
            active_projects=len(self.active_projects),
            active_tasks=len(self.active_tasks),
            capacity=self.capacity,
            free_capacity=self.free_capacity(),
            member_count=len(self.members),
            has_director=self.has_director(),
            bottlenecks=bottlenecks,
            overall_health=overall_health,
        )
