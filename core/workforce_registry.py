"""
Workforce Registry for AI Company OS.

The WorkforceRegistry is the authoritative directory of every employee
(agent) in the company. It manages the complete lifecycle of each employee
from initial hire through termination, enforces valid status transitions,
and provides company-wide workforce analytics.

The Workforce System sits at Layer 4 (Agent Layer) in the architecture. It
does not execute work — it manages who is available to do work and in what
organizational context. The Executive Engine consults the registry to find
available employees before issuing task assignments.

Architecture reference: §2.1 Executive Engine, §2.2 Agent Runtime,
§3 Layer 4, §5 Agent Lifecycle, Constitution Chapter 5.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.department_type import DepartmentType
from core.employee import (
    Employee,
    EmployeeAlreadySuspendedError,
    EmployeeAlreadyTerminatedError,
    EmployeeNotFoundError,
    EmployeeNotSuspendedError,
    InvalidWorkloadError,
)
from core.employee_role import EmployeeRole, Seniority
from core.employee_status import EmployeeStatus
from core.hire_request import HireRequest


class WorkforceRegistry:
    """
    Authoritative directory of all employees in AI Company OS.

    Maintains a single primary store keyed by employee ID. All mutation
    methods enforce lifecycle rules before modifying any employee record,
    raising descriptive exceptions when a requested transition is invalid.

    The registry is the sole authority for employee state transitions. No
    external code should modify Employee fields directly.

    Attributes:
        _employees: Dict[str, Employee] — all employee records, keyed by UUID.
    """

    def __init__(self) -> None:
        self._employees: Dict[str, Employee] = {}

    # ------------------------------------------------------------------
    # Hiring
    # ------------------------------------------------------------------

    def hire(self, request: HireRequest) -> Employee:
        """
        Formally hire a new employee from an approved HireRequest.

        Creates an Employee record with a new UUID, status ACTIVE, workload
        0.0, and created_at set to the current UTC time. The employee is
        immediately part of the active workforce and can receive assignments.

        Args:
            request: A validated HireRequest produced by the Executive Engine
                after CEO approval of the staffing decision.

        Returns:
            The newly created and registered Employee.
        """
        employee = Employee(
            id=str(uuid.uuid4()),
            name=request.name,
            role=request.role,
            department=request.department,
            director=request.director_id,
            status=EmployeeStatus.ACTIVE,
            skills=list(request.skills),
            seniority=request.seniority,
            workload=0.0,
            created_at=datetime.now(timezone.utc),
        )
        self._employees[employee.id] = employee
        return employee

    # ------------------------------------------------------------------
    # Lifecycle transitions
    # ------------------------------------------------------------------

    def terminate(self, employee_id: str) -> Employee:
        """
        Permanently decommission an employee.

        The employee record is retained for historical reference. TERMINATED
        is a terminal state — no further transitions are possible. The employee
        no longer counts toward active headcount.

        Both active and suspended employees may be terminated. CANDIDATE and
        TRANSFERRED employees may also be terminated.

        Args:
            employee_id: The ID of the employee to terminate.

        Returns:
            The updated Employee with status TERMINATED.

        Raises:
            EmployeeNotFoundError: If the ID is not in the registry.
            EmployeeAlreadyTerminatedError: If already TERMINATED.
        """
        employee = self._resolve(employee_id)
        if employee.status == EmployeeStatus.TERMINATED:
            raise EmployeeAlreadyTerminatedError(
                f"Employee '{employee.name}' (ID: {employee_id}) is already terminated. "
                "A terminated employee's record cannot be modified."
            )
        employee.status = EmployeeStatus.TERMINATED
        employee.workload = 0.0
        return employee

    def suspend(self, employee_id: str) -> Employee:
        """
        Temporarily deactivate an employee.

        The employee retains their department, director, and skills. They
        can be reactivated. SUSPENDED employees do not count toward active
        headcount or available capacity.

        Args:
            employee_id: The ID of the employee to suspend.

        Returns:
            The updated Employee with status SUSPENDED.

        Raises:
            EmployeeNotFoundError: If the ID is not in the registry.
            EmployeeAlreadyTerminatedError: If the employee is TERMINATED.
            EmployeeAlreadySuspendedError: If already SUSPENDED.
        """
        employee = self._resolve(employee_id)
        self._require_not_terminated(employee)
        if employee.status == EmployeeStatus.SUSPENDED:
            raise EmployeeAlreadySuspendedError(
                f"Employee '{employee.name}' (ID: {employee_id}) is already suspended."
            )
        employee.status = EmployeeStatus.SUSPENDED
        return employee

    def reactivate(self, employee_id: str) -> Employee:
        """
        Restore a suspended employee to the active workforce.

        Sets the employee's status to IDLE, signalling that they are
        operational but not yet assigned. The Director should assign work
        or the Executive Engine should queue them for assignment.

        Args:
            employee_id: The ID of the employee to reactivate.

        Returns:
            The updated Employee with status IDLE.

        Raises:
            EmployeeNotFoundError: If the ID is not in the registry.
            EmployeeAlreadyTerminatedError: If the employee is TERMINATED.
            EmployeeNotSuspendedError: If the employee is not SUSPENDED.
        """
        employee = self._resolve(employee_id)
        self._require_not_terminated(employee)
        if employee.status != EmployeeStatus.SUSPENDED:
            raise EmployeeNotSuspendedError(
                f"Employee '{employee.name}' (ID: {employee_id}) is not suspended "
                f"(current status: {employee.status.value}). "
                "Only SUSPENDED employees can be reactivated."
            )
        employee.status = EmployeeStatus.IDLE
        return employee

    def transfer(
        self,
        employee_id: str,
        new_department: DepartmentType,
        new_director_id: Optional[str] = None,
    ) -> Employee:
        """
        Formally transfer an employee to a new department.

        Updates the employee's department to new_department and optionally
        updates their Director assignment. Sets the employee's status to
        TRANSFERRED, marking the transition period. The employee cannot
        receive new task assignments while in TRANSFERRED status. The
        Director or Executive Engine must call update_status() or
        reactivate() to put the employee back into an assignable state.

        Args:
            employee_id: The ID of the employee to transfer.
            new_department: The DepartmentType to move the employee into.
            new_director_id: Optional ID of the Director in the new
                department. Pass None to clear the director assignment;
                pass a string to update it.

        Returns:
            The updated Employee with the new department and TRANSFERRED status.

        Raises:
            EmployeeNotFoundError: If the ID is not in the registry.
            EmployeeAlreadyTerminatedError: If the employee is TERMINATED.
        """
        employee = self._resolve(employee_id)
        self._require_not_terminated(employee)
        employee.department = new_department
        employee.director = new_director_id
        employee.status = EmployeeStatus.TRANSFERRED
        return employee

    # ------------------------------------------------------------------
    # Assignment updates
    # ------------------------------------------------------------------

    def assign_director(self, employee_id: str, director_id: str) -> Employee:
        """
        Assign or update the Director responsible for this employee.

        This is an administrative assignment and does not change the
        employee's status or workload. It can be applied to employees
        in any non-terminal state.

        Args:
            employee_id: The ID of the employee to update.
            director_id: The ID of the Director to assign.

        Returns:
            The updated Employee.

        Raises:
            EmployeeNotFoundError: If the ID is not in the registry.
            EmployeeAlreadyTerminatedError: If the employee is TERMINATED.
        """
        employee = self._resolve(employee_id)
        self._require_not_terminated(employee)
        employee.director = director_id
        return employee

    def assign_department(
        self, employee_id: str, department: DepartmentType
    ) -> Employee:
        """
        Administratively assign an employee to a department.

        Unlike transfer(), this method does not change the employee's status
        or mark a transition period. Use this for initial department placement
        or administrative corrections. Use transfer() for formal organizational
        moves that should be recorded as transitions.

        Args:
            employee_id: The ID of the employee to update.
            department: The DepartmentType to assign the employee to.

        Returns:
            The updated Employee.

        Raises:
            EmployeeNotFoundError: If the ID is not in the registry.
            EmployeeAlreadyTerminatedError: If the employee is TERMINATED.
        """
        employee = self._resolve(employee_id)
        self._require_not_terminated(employee)
        employee.department = department
        return employee

    def update_status(
        self, employee_id: str, status: EmployeeStatus
    ) -> Employee:
        """
        Directly set an employee's operational status.

        This method bypasses lifecycle guards and sets the status directly.
        Use it for fine-grained control when the specific lifecycle methods
        (suspend, reactivate, transfer) do not cover the required transition.
        For example, transitioning an employee from TRANSFERRED to ACTIVE
        after they have settled into their new department.

        Cannot transition a TERMINATED employee to any other status.

        Args:
            employee_id: The ID of the employee to update.
            status: The new EmployeeStatus to set.

        Returns:
            The updated Employee.

        Raises:
            EmployeeNotFoundError: If the ID is not in the registry.
            EmployeeAlreadyTerminatedError: If the employee is TERMINATED.
        """
        employee = self._resolve(employee_id)
        self._require_not_terminated(employee)
        employee.status = status
        return employee

    def update_workload(
        self, employee_id: str, workload: float
    ) -> Employee:
        """
        Update an employee's current workload fraction.

        Called by the Task Engine or Executive Engine as tasks are assigned
        and completed. The workload represents what fraction of this employee's
        capacity is committed (0.0 = free, 1.0 = fully committed).

        Args:
            employee_id: The ID of the employee to update.
            workload: New workload value in [0.0, 1.0].

        Returns:
            The updated Employee.

        Raises:
            EmployeeNotFoundError: If the ID is not in the registry.
            EmployeeAlreadyTerminatedError: If the employee is TERMINATED.
            InvalidWorkloadError: If workload is outside [0.0, 1.0].
        """
        if not (0.0 <= workload <= 1.0):
            raise InvalidWorkloadError(
                f"Workload must be in [0.0, 1.0]. Received: {workload}."
            )
        employee = self._resolve(employee_id)
        self._require_not_terminated(employee)
        employee.workload = workload
        return employee

    # ------------------------------------------------------------------
    # Lookup and listing
    # ------------------------------------------------------------------

    def get(self, employee_id: str) -> Employee:
        """
        Retrieve an employee by their unique ID.

        Args:
            employee_id: The UUID string of the employee to retrieve.

        Returns:
            The matching Employee (live reference).

        Raises:
            EmployeeNotFoundError: If the ID is not in the registry.
        """
        return self._resolve(employee_id)

    def count(self) -> int:
        """
        Return the total number of employee records in the registry.

        Includes ALL employees regardless of status (ACTIVE, SUSPENDED,
        TERMINATED, etc.). For active headcount use list_active().

        Returns:
            Integer count. Zero when the registry is empty.
        """
        return len(self._employees)

    def list_all(self) -> List[Employee]:
        """
        Return all employee records in hire order.

        Returns a shallow copy. The returned list can be mutated without
        affecting the registry; Employee objects inside are live references.

        Returns:
            Ordered list of all Employee instances.
        """
        return list(self._employees.values())

    def list_active(self) -> List[Employee]:
        """
        Return all employees who are currently active workforce members.

        Active workforce members are those whose status is ACTIVE, IDLE,
        WORKING, or WAITING. CANDIDATE, SUSPENDED, TRANSFERRED, and
        TERMINATED employees are excluded.

        Returns:
            List of active Employee instances in hire order.
        """
        return [e for e in self._employees.values() if e.is_active_workforce()]

    def list_by_department(self, department: DepartmentType) -> List[Employee]:
        """
        Return all employees assigned to the given department.

        Returns all employees regardless of status — including SUSPENDED
        and TRANSFERRED employees. Use this to understand full department
        composition. Filter the result by status if active-only is needed.

        Args:
            department: The DepartmentType to filter by.

        Returns:
            List of Employee instances in this department, in hire order.
        """
        return [
            e for e in self._employees.values() if e.department == department
        ]

    def list_by_role(self, role: EmployeeRole) -> List[Employee]:
        """
        Return all employees with the given specialist role.

        Returns employees regardless of status. Useful for capability
        discovery — e.g., finding all QA_ENGINEER employees regardless
        of which department they currently belong to.

        Args:
            role: The EmployeeRole to filter by.

        Returns:
            List of Employee instances with this role, in hire order.
        """
        return [e for e in self._employees.values() if e.role == role]

    def list_by_seniority(self, seniority: Seniority) -> List[Employee]:
        """
        Return all employees at the given seniority level.

        Args:
            seniority: The Seniority level to filter by.

        Returns:
            List of Employee instances at this seniority, in hire order.
        """
        return [e for e in self._employees.values() if e.seniority == seniority]

    def list_available(self) -> List[Employee]:
        """
        Return all employees who can immediately accept a new task.

        An employee is available when their status is ACTIVE or IDLE and
        their workload is less than 1.0. This is the subset of the active
        workforce that the Task Engine can assign work to right now.

        Returns:
            List of available Employee instances in hire order.
        """
        return [e for e in self._employees.values() if e.is_available()]

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def statistics(self) -> Dict[str, Any]:
        """
        Return aggregate operational statistics for the entire workforce.

        Provides a numeric overview suitable for dashboards and the Executive
        Engine's status reporting. Does not compute health grades — for that,
        use workforce_health().

        Returns:
            A dictionary with the following keys:

            total_employees (int): All records in the registry.
            active_headcount (int): ACTIVE + IDLE + WORKING + WAITING.
            by_status (Dict[str, int]): Count per EmployeeStatus value.
            by_department (Dict[str, int]): Count per DepartmentType value,
                for all employees regardless of status.
            by_role (Dict[str, int]): Count per EmployeeRole value.
            by_seniority (Dict[str, int]): Count per Seniority value.
            average_workload (float): Mean workload across active workforce.
                0.0 when no active employees exist.
            available_count (int): Employees who can accept new assignments.
        """
        employees = self.list_all()
        active = self.list_active()

        by_status: Dict[str, int] = {s.value: 0 for s in EmployeeStatus}
        by_role: Dict[str, int] = {r.value: 0 for r in EmployeeRole}
        by_seniority: Dict[str, int] = {s.value: 0 for s in Seniority}
        by_department: Dict[str, int] = {}

        for emp in employees:
            by_status[emp.status.value] += 1
            by_role[emp.role.value] += 1
            by_seniority[emp.seniority.value] += 1
            dept_key = emp.department.value
            by_department[dept_key] = by_department.get(dept_key, 0) + 1

        avg_workload = (
            sum(e.workload for e in active) / len(active) if active else 0.0
        )

        return {
            "total_employees": len(employees),
            "active_headcount": len(active),
            "by_status": by_status,
            "by_department": by_department,
            "by_role": by_role,
            "by_seniority": by_seniority,
            "average_workload": round(avg_workload, 4),
            "available_count": len(self.list_available()),
        }

    def workforce_health(self) -> Dict[str, Any]:
        """
        Generate a comprehensive workforce health report.

        Evaluates every employee in the active workforce and identifies
        health concerns: overloaded individuals, idle capacity, and
        employees in problematic states. Produces an overall health grade
        for the workforce.

        Health grade logic:
            "OK"       — No overloaded employees, suspension count within
                         acceptable bounds (< 20% of total active).
            "WARNING"  — Some overloaded employees, or elevated suspension
                         count (20–40% of total active).
            "CRITICAL" — Many overloaded employees (> 30% of active) or
                         suspension count exceeds 40% of total active.

        Returns:
            A dictionary with the following keys:

            total_employees (int): All records in the registry.
            active_headcount (int): ACTIVE + IDLE + WORKING + WAITING.
            overloaded_count (int): Active employees with workload >= 0.9.
            idle_count (int): Employees with IDLE status.
            working_count (int): Employees with WORKING status.
            waiting_count (int): Employees with WAITING status.
            suspended_count (int): Employees with SUSPENDED status.
            terminated_count (int): Employees with TERMINATED status.
            transferred_count (int): Employees with TRANSFERRED status.
            average_workload (float): Mean workload of active workforce.
            overall_health (str): "OK", "WARNING", or "CRITICAL".
            concerns (List[str]): Identified workforce concerns.
            employees (List[Dict]): Per-employee health snapshot.
        """
        all_employees = self.list_all()
        active = self.list_active()

        overloaded = [e for e in active if e.workload >= 0.9]
        idle_emps = [e for e in all_employees if e.status == EmployeeStatus.IDLE]
        working_emps = [e for e in all_employees if e.status == EmployeeStatus.WORKING]
        waiting_emps = [e for e in all_employees if e.status == EmployeeStatus.WAITING]
        suspended_emps = [e for e in all_employees if e.status == EmployeeStatus.SUSPENDED]
        terminated_emps = [e for e in all_employees if e.status == EmployeeStatus.TERMINATED]
        transferred_emps = [e for e in all_employees if e.status == EmployeeStatus.TRANSFERRED]

        avg_workload = (
            round(sum(e.workload for e in active) / len(active), 4) if active else 0.0
        )

        # Identify concerns.
        concerns: List[str] = []
        if overloaded:
            pct = len(overloaded) / len(active) * 100 if active else 0
            concerns.append(
                f"{len(overloaded)} employee(s) are overloaded "
                f"({pct:.0f}% of active workforce at ≥ 90% workload)."
            )
        if len(idle_emps) > 0:
            concerns.append(
                f"{len(idle_emps)} employee(s) are idle — consider assigning work."
            )
        if suspended_emps:
            concerns.append(
                f"{len(suspended_emps)} employee(s) are suspended "
                "and not contributing to capacity."
            )
        if transferred_emps:
            concerns.append(
                f"{len(transferred_emps)} employee(s) are in TRANSFERRED state "
                "and awaiting department assignment confirmation."
            )

        # Compute overall health grade.
        active_count = len(active)
        overloaded_ratio = len(overloaded) / active_count if active_count > 0 else 0.0
        suspended_ratio = len(suspended_emps) / active_count if active_count > 0 else 0.0

        if overloaded_ratio > 0.30 or suspended_ratio > 0.40:
            overall_health = "CRITICAL"
        elif overloaded_ratio > 0 or suspended_ratio > 0.20:
            overall_health = "WARNING"
        else:
            overall_health = "OK"

        # Per-employee snapshots.
        employee_snapshots: List[Dict[str, Any]] = []
        for emp in all_employees:
            is_overloaded = emp.is_active_workforce() and emp.workload >= 0.9
            employee_snapshots.append({
                "id": emp.id,
                "name": emp.name,
                "role": emp.role.value,
                "department": emp.department.value,
                "seniority": emp.seniority.value,
                "status": emp.status.value,
                "workload": emp.workload,
                "utilization": emp.utilization(),
                "is_overloaded": is_overloaded,
                "is_available": emp.is_available(),
                "skill_count": len(emp.skills),
            })

        return {
            "total_employees": len(all_employees),
            "active_headcount": active_count,
            "overloaded_count": len(overloaded),
            "idle_count": len(idle_emps),
            "working_count": len(working_emps),
            "waiting_count": len(waiting_emps),
            "suspended_count": len(suspended_emps),
            "terminated_count": len(terminated_emps),
            "transferred_count": len(transferred_emps),
            "average_workload": avg_workload,
            "overall_health": overall_health,
            "concerns": concerns,
            "employees": employee_snapshots,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve(self, employee_id: str) -> Employee:
        """
        Return the Employee for the given ID or raise EmployeeNotFoundError.

        Args:
            employee_id: The employee UUID to resolve.

        Returns:
            The matching Employee.

        Raises:
            EmployeeNotFoundError: If the ID is not in the registry.
        """
        employee = self._employees.get(employee_id)
        if employee is None:
            raise EmployeeNotFoundError(
                f"No employee found with ID '{employee_id}'."
            )
        return employee

    def _require_not_terminated(self, employee: Employee) -> None:
        """
        Raise EmployeeAlreadyTerminatedError if the employee is TERMINATED.

        Used as a guard at the start of every mutation method to prevent
        modification of terminal records.

        Args:
            employee: The Employee to check.

        Raises:
            EmployeeAlreadyTerminatedError: If employee.status is TERMINATED.
        """
        if employee.status == EmployeeStatus.TERMINATED:
            raise EmployeeAlreadyTerminatedError(
                f"Employee '{employee.name}' (ID: {employee.id}) is terminated. "
                "Terminated employee records are read-only."
            )
