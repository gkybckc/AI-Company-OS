"""
Department Registry for AI Company OS.

The DepartmentRegistry is the authoritative directory of all departments
active within the company. It enforces the rule that each DepartmentType
may have at most one registered department at a time, provides O(1)
lookup by type, and exposes company-wide health reporting and statistics.

The Executive Engine uses the registry to route work: it looks up a
department by type, verifies availability, and delegates. The registry
does not make routing decisions — it only exposes the state that enables
those decisions.

Architecture reference: §2 Core Components, §3 Layer 5 (Coordination),
§13 Scalability, Constitution Chapter 5.
"""

from typing import Any, Dict, List

from core.department import (
    Department,
    DepartmentHealth,
    InvalidCapacityError,
    InvalidWorkloadError,
    MemberNotFoundError,
)
from core.department_status import DepartmentStatus
from core.department_type import DepartmentType
from core.director import Director


class DepartmentAlreadyRegisteredError(Exception):
    """Raised when a DepartmentType is already present in the registry."""


class DepartmentNotFoundError(Exception):
    """Raised when a department ID or type cannot be resolved in the registry."""


class DepartmentRegistry:
    """
    Authoritative directory of all departments in the company.

    Maintains two internal indices:
      - _departments: Dict[str, Department]        — keyed by department ID
      - _type_index:  Dict[DepartmentType, str]    — maps type → department ID

    The type index enforces uniqueness per DepartmentType and enables O(1)
    lookup by type. The department dict preserves registration order.

    The registry is the single point of truth for what departments exist,
    what their current state is, and how healthy the company's organizational
    structure is at any moment.

    Attributes:
        _departments: Primary store, keyed by UUID department ID.
        _type_index: Secondary index, keyed by DepartmentType.
    """

    def __init__(self) -> None:
        self._departments: Dict[str, Department] = {}
        self._type_index: Dict[DepartmentType, str] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, department: Department) -> Department:
        """
        Register a department with the company.

        Each DepartmentType may appear at most once. If a department of
        the same type is already registered, the registration is rejected.

        Args:
            department: The Department instance to register.

        Returns:
            The registered Department (same object passed in).

        Raises:
            DepartmentAlreadyRegisteredError: If a department of this type
                is already in the registry.
        """
        if department.type in self._type_index:
            raise DepartmentAlreadyRegisteredError(
                f"A '{department.type.value}' department is already registered. "
                "Remove the existing department before registering a new one."
            )
        self._departments[department.id] = department
        self._type_index[department.type] = department.id
        return department

    def remove(self, department_id: str) -> Department:
        """
        Remove a department from the registry.

        Args:
            department_id: The ID of the department to remove.

        Returns:
            The Department that was removed.

        Raises:
            DepartmentNotFoundError: If department_id is not in the registry.
        """
        department = self._resolve_id(department_id)
        del self._type_index[department.type]
        del self._departments[department_id]
        return department

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, department_id: str) -> Department:
        """
        Retrieve a department by its unique ID.

        Args:
            department_id: The UUID string identifying the department.

        Returns:
            The matching Department (live reference).

        Raises:
            DepartmentNotFoundError: If the ID is not in the registry.
        """
        return self._resolve_id(department_id)

    def find_by_type(self, department_type: DepartmentType) -> Department:
        """
        Retrieve the department of a given type.

        Args:
            department_type: The DepartmentType to look up.

        Returns:
            The Department of that type (live reference).

        Raises:
            DepartmentNotFoundError: If no department of this type is registered.
        """
        dept_id = self._type_index.get(department_type)
        if dept_id is None:
            raise DepartmentNotFoundError(
                f"No '{department_type.value}' department is registered."
            )
        return self._departments[dept_id]

    def list_all(self) -> List[Department]:
        """
        Return all registered departments in registration order.

        Returns a shallow copy of the department list. Mutating the
        returned list does not affect the registry; Department objects
        within it are live references and remain mutable.

        Returns:
            Ordered list of Department instances. Empty if none registered.
        """
        return list(self._departments.values())

    def count(self) -> int:
        """
        Return the number of departments currently registered.

        Returns:
            Integer count. Zero when the registry is empty.
        """
        return len(self._departments)

    def is_registered(self, department_type: DepartmentType) -> bool:
        """
        Check whether a department of the given type is registered.

        Args:
            department_type: The type to check.

        Returns:
            True if a department of this type is registered.
        """
        return department_type in self._type_index

    # ------------------------------------------------------------------
    # State updates
    # ------------------------------------------------------------------

    def update_workload(self, department_id: str, workload: float) -> Department:
        """
        Update a department's workload and automatically adjust its status.

        Workload must be in [0.0, 1.0]. After updating, the department's
        status is adjusted using the following rules (only when the current
        status is READY, WORKING, or OVERLOADED — BLOCKED, WAITING, and
        OFFLINE statuses require explicit changes):

            workload >= 0.9  → OVERLOADED
            0.0 < workload < 0.9  → WORKING
            workload == 0.0  → READY

        Args:
            department_id: The department to update.
            workload: New workload value, in [0.0, 1.0].

        Returns:
            The updated Department.

        Raises:
            DepartmentNotFoundError: If department_id is not registered.
            InvalidWorkloadError: If workload is outside [0.0, 1.0].
        """
        if not (0.0 <= workload <= 1.0):
            raise InvalidWorkloadError(
                f"Workload must be in [0.0, 1.0]. Received: {workload}."
            )
        department = self._resolve_id(department_id)
        department.workload = workload

        workload_driven_statuses = {
            DepartmentStatus.READY,
            DepartmentStatus.WORKING,
            DepartmentStatus.OVERLOADED,
        }
        if department.status in workload_driven_statuses:
            if workload >= 0.9:
                department.status = DepartmentStatus.OVERLOADED
            elif workload > 0.0:
                department.status = DepartmentStatus.WORKING
            else:
                department.status = DepartmentStatus.READY

        return department

    def update_capacity(self, department_id: str, capacity: int) -> Department:
        """
        Update a department's maximum capacity.

        Args:
            department_id: The department to update.
            capacity: New capacity value. Must be a positive integer.

        Returns:
            The updated Department.

        Raises:
            DepartmentNotFoundError: If department_id is not registered.
            InvalidCapacityError: If capacity is less than 1.
        """
        if capacity < 1:
            raise InvalidCapacityError(
                f"Capacity must be a positive integer (≥ 1). Received: {capacity}."
            )
        department = self._resolve_id(department_id)
        department.capacity = capacity
        return department

    def update_status(self, department_id: str, status: DepartmentStatus) -> Department:
        """
        Explicitly set a department's operational status.

        Unlike update_workload(), this method sets the status directly
        without checking workload. Use this for transitions to BLOCKED,
        WAITING, or OFFLINE that are driven by operational conditions
        rather than load.

        Args:
            department_id: The department to update.
            status: The new operational status.

        Returns:
            The updated Department.

        Raises:
            DepartmentNotFoundError: If department_id is not registered.
        """
        department = self._resolve_id(department_id)
        department.status = status
        return department

    def assign_director(self, department_id: str, director: Director) -> Department:
        """
        Assign a Director to a department.

        Replaces any existing director assignment. If the department
        was OFFLINE due to having no director, it transitions to READY.

        Args:
            department_id: The department to update.
            director: The Director to assign.

        Returns:
            The updated Department.

        Raises:
            DepartmentNotFoundError: If department_id is not registered.
        """
        department = self._resolve_id(department_id)
        department.director = director
        if department.status == DepartmentStatus.OFFLINE:
            department.status = DepartmentStatus.READY
        return department

    def add_member(self, department_id: str, agent_id: str) -> Department:
        """
        Add an agent to a department's member list.

        Idempotent — if the agent is already a member, the call succeeds
        without duplicating the entry.

        Args:
            department_id: The department to update.
            agent_id: The agent ID to add.

        Returns:
            The updated Department.

        Raises:
            DepartmentNotFoundError: If department_id is not registered.
        """
        department = self._resolve_id(department_id)
        if agent_id not in department.members:
            department.members.append(agent_id)
        return department

    def remove_member(self, department_id: str, agent_id: str) -> Department:
        """
        Remove an agent from a department's member list.

        Args:
            department_id: The department to update.
            agent_id: The agent ID to remove.

        Returns:
            The updated Department.

        Raises:
            DepartmentNotFoundError: If department_id is not registered.
            MemberNotFoundError: If agent_id is not in the department's
                member list.
        """
        department = self._resolve_id(department_id)
        if agent_id not in department.members:
            raise MemberNotFoundError(
                f"Agent '{agent_id}' is not a member of department '{department.name}'."
            )
        department.members.remove(agent_id)
        return department

    def add_active_project(self, department_id: str, project_id: str) -> Department:
        """
        Record that a project is now active in this department.

        Idempotent — if the project is already tracked, no duplicate is added.

        Args:
            department_id: The department to update.
            project_id: The project ID to add.

        Returns:
            The updated Department.

        Raises:
            DepartmentNotFoundError: If department_id is not registered.
        """
        department = self._resolve_id(department_id)
        if project_id not in department.active_projects:
            department.active_projects.append(project_id)
        return department

    def remove_active_project(self, department_id: str, project_id: str) -> Department:
        """
        Record that a project is no longer active in this department.

        Args:
            department_id: The department to update.
            project_id: The project ID to remove.

        Returns:
            The updated Department. If the project was not tracked,
            the department is returned unchanged (idempotent removal).

        Raises:
            DepartmentNotFoundError: If department_id is not registered.
        """
        department = self._resolve_id(department_id)
        if project_id in department.active_projects:
            department.active_projects.remove(project_id)
        return department

    def add_active_task(self, department_id: str, task_id: str) -> Department:
        """
        Record that a task is now active in this department.

        Idempotent — if the task is already tracked, no duplicate is added.

        Args:
            department_id: The department to update.
            task_id: The task ID to add.

        Returns:
            The updated Department.

        Raises:
            DepartmentNotFoundError: If department_id is not registered.
        """
        department = self._resolve_id(department_id)
        if task_id not in department.active_tasks:
            department.active_tasks.append(task_id)
        return department

    def remove_active_task(self, department_id: str, task_id: str) -> Department:
        """
        Record that a task is no longer active in this department.

        Args:
            department_id: The department to update.
            task_id: The task ID to remove.

        Returns:
            The updated Department. If the task was not tracked,
            the department is returned unchanged (idempotent removal).

        Raises:
            DepartmentNotFoundError: If department_id is not registered.
        """
        department = self._resolve_id(department_id)
        if task_id in department.active_tasks:
            department.active_tasks.remove(task_id)
        return department

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def health_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive company-wide department health report.

        Evaluates every registered department and produces a structured
        summary showing which departments are healthy, which are degraded,
        and which are critically impaired.

        Returns:
            A dictionary with the following keys:

            total_departments (int): Number of registered departments.
            healthy (int): Departments graded "OK".
            warning (int): Departments graded "WARNING".
            critical (int): Departments graded "CRITICAL".
            departments (List[Dict]): Per-department health detail,
                each entry being a dict representation of DepartmentHealth
                with all keys from that dataclass converted to strings
                or primitives.
        """
        departments = self.list_all()
        per_department: List[Dict[str, Any]] = []
        healthy = warning = critical = 0

        for dept in departments:
            health: DepartmentHealth = dept.compute_health()
            per_department.append({
                "department_id": health.department_id,
                "department_name": health.department_name,
                "department_type": health.department_type.value,
                "status": health.status.value,
                "utilization": health.utilization,
                "active_projects": health.active_projects,
                "active_tasks": health.active_tasks,
                "capacity": health.capacity,
                "free_capacity": health.free_capacity,
                "member_count": health.member_count,
                "has_director": health.has_director,
                "bottlenecks": list(health.bottlenecks),
                "overall_health": health.overall_health,
            })
            if health.overall_health == "OK":
                healthy += 1
            elif health.overall_health == "WARNING":
                warning += 1
            else:
                critical += 1

        return {
            "total_departments": len(departments),
            "healthy": healthy,
            "warning": warning,
            "critical": critical,
            "departments": per_department,
        }

    def statistics(self) -> Dict[str, Any]:
        """
        Return aggregate operational statistics for the entire company.

        Does not evaluate health grades — this is a raw numeric summary
        suitable for dashboards and monitoring.

        Returns:
            A dictionary with the following keys:

            total_departments (int): Number of registered departments.
            total_capacity (int): Sum of all department capacities.
            total_members (int): Total agent count across all departments.
            total_active_projects (int): Sum of active project counts.
            total_active_tasks (int): Sum of active task counts.
            average_workload (float): Mean workload across all departments.
                0.0 when no departments are registered.
            overloaded_departments (int): Count of OVERLOADED departments.
            offline_departments (int): Count of OFFLINE departments.
            departments_by_status (Dict[str, int]): Count per status value.
            registered_types (List[str]): List of registered DepartmentType
                values in registration order.
        """
        departments = self.list_all()
        total = len(departments)

        avg_workload = (
            sum(d.workload for d in departments) / total if total > 0 else 0.0
        )

        by_status = {s.value: 0 for s in DepartmentStatus}
        for dept in departments:
            by_status[dept.status.value] += 1

        return {
            "total_departments": total,
            "total_capacity": sum(d.capacity for d in departments),
            "total_members": sum(len(d.members) for d in departments),
            "total_active_projects": sum(len(d.active_projects) for d in departments),
            "total_active_tasks": sum(len(d.active_tasks) for d in departments),
            "average_workload": round(avg_workload, 4),
            "overloaded_departments": by_status.get(DepartmentStatus.OVERLOADED.value, 0),
            "offline_departments": by_status.get(DepartmentStatus.OFFLINE.value, 0),
            "departments_by_status": by_status,
            "registered_types": [d.type.value for d in departments],
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_id(self, department_id: str) -> Department:
        """
        Return the Department for the given ID or raise DepartmentNotFoundError.

        Args:
            department_id: The department ID to resolve.

        Returns:
            The matching Department.

        Raises:
            DepartmentNotFoundError: If the ID is not in the registry.
        """
        department = self._departments.get(department_id)
        if department is None:
            raise DepartmentNotFoundError(
                f"No department found with ID '{department_id}'."
            )
        return department
