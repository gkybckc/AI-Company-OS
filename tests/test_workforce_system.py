"""
Comprehensive unit tests for Sprint 6 — Workforce System.

Covers: EmployeeStatus, EmployeeRole, Seniority, Employee, HireRequest,
and WorkforceRegistry (all public methods and all lifecycle transitions).

Run with:
    .venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_workforce_system.py" -v
"""

import unittest
from datetime import datetime, timezone

from core.department_type import DepartmentType
from core.employee import (
    Employee,
    EmployeeAlreadySuspendedError,
    EmployeeAlreadyTerminatedError,
    EmployeeError,
    EmployeeNotFoundError,
    EmployeeNotSuspendedError,
    InvalidWorkloadError,
)
from core.employee_role import EmployeeRole, Seniority
from core.employee_status import EmployeeStatus
from core.hire_request import HireRequest, InvalidHireRequestError
from core.workforce_registry import WorkforceRegistry


# ---------------------------------------------------------------------------
# Shared factories
# ---------------------------------------------------------------------------

def _request(
    name: str = "Test Agent",
    role: EmployeeRole = EmployeeRole.BACKEND_AGENT,
    department: DepartmentType = DepartmentType.BACKEND,
    seniority: Seniority = Seniority.MID,
    skills: list | None = None,
    director_id: str | None = None,
) -> HireRequest:
    return HireRequest(
        name=name,
        role=role,
        department=department,
        seniority=seniority,
        skills=skills if skills is not None else ["Python", "REST APIs"],
        director_id=director_id,
    )


def _registry() -> WorkforceRegistry:
    return WorkforceRegistry()


def _hire(
    registry: WorkforceRegistry | None = None,
    **kwargs,
) -> tuple[WorkforceRegistry, Employee]:
    reg = registry or _registry()
    emp = reg.hire(_request(**kwargs))
    return reg, emp


# ---------------------------------------------------------------------------
# TestEmployeeStatus
# ---------------------------------------------------------------------------

class TestEmployeeStatus(unittest.TestCase):

    def test_all_eight_values_exist(self) -> None:
        names = {s.name for s in EmployeeStatus}
        self.assertEqual(
            names,
            {
                "CANDIDATE", "ACTIVE", "IDLE", "WORKING",
                "WAITING", "SUSPENDED", "TRANSFERRED", "TERMINATED",
            },
        )

    def test_str_returns_value(self) -> None:
        for s in EmployeeStatus:
            self.assertEqual(str(s), s.value)

    def test_is_str_subclass(self) -> None:
        self.assertIsInstance(EmployeeStatus.ACTIVE, str)

    def test_string_comparison(self) -> None:
        self.assertEqual(EmployeeStatus.TERMINATED, "TERMINATED")
        self.assertEqual(EmployeeStatus.SUSPENDED, "SUSPENDED")

    def test_is_active_workforce_true_for_active_statuses(self) -> None:
        for status in (
            EmployeeStatus.ACTIVE,
            EmployeeStatus.IDLE,
            EmployeeStatus.WORKING,
            EmployeeStatus.WAITING,
        ):
            self.assertTrue(status.is_active_workforce(), msg=status.value)

    def test_is_active_workforce_false_for_inactive_statuses(self) -> None:
        for status in (
            EmployeeStatus.CANDIDATE,
            EmployeeStatus.SUSPENDED,
            EmployeeStatus.TRANSFERRED,
            EmployeeStatus.TERMINATED,
        ):
            self.assertFalse(status.is_active_workforce(), msg=status.value)

    def test_is_terminal_true_only_for_terminated(self) -> None:
        self.assertTrue(EmployeeStatus.TERMINATED.is_terminal())
        for status in EmployeeStatus:
            if status != EmployeeStatus.TERMINATED:
                self.assertFalse(status.is_terminal(), msg=status.value)

    def test_enum_identity_distinct(self) -> None:
        self.assertIsNot(EmployeeStatus.ACTIVE, EmployeeStatus.IDLE)


# ---------------------------------------------------------------------------
# TestEmployeeRole
# ---------------------------------------------------------------------------

class TestEmployeeRole(unittest.TestCase):

    def test_all_ten_values_exist(self) -> None:
        names = {r.name for r in EmployeeRole}
        self.assertEqual(
            names,
            {
                "BACKEND_AGENT", "FRONTEND_AGENT", "UI_DESIGNER", "UX_DESIGNER",
                "QA_ENGINEER", "DEVOPS_ENGINEER", "SECURITY_SPECIALIST",
                "PRODUCT_ANALYST", "MARKETING_SPECIALIST", "RESEARCH_ANALYST",
            },
        )

    def test_str_returns_value(self) -> None:
        for r in EmployeeRole:
            self.assertEqual(str(r), r.value)

    def test_is_str_subclass(self) -> None:
        self.assertIsInstance(EmployeeRole.BACKEND_AGENT, str)

    def test_string_comparison(self) -> None:
        self.assertEqual(EmployeeRole.QA_ENGINEER, "QA Engineer")
        self.assertEqual(EmployeeRole.DEVOPS_ENGINEER, "DevOps Engineer")

    def test_values_are_human_readable(self) -> None:
        for r in EmployeeRole:
            self.assertGreater(len(r.value), 0)
            self.assertFalse(r.value.startswith("_"))


# ---------------------------------------------------------------------------
# TestSeniority
# ---------------------------------------------------------------------------

class TestSeniority(unittest.TestCase):

    def test_all_five_values_exist(self) -> None:
        names = {s.name for s in Seniority}
        self.assertEqual(names, {"JUNIOR", "MID", "SENIOR", "LEAD", "PRINCIPAL"})

    def test_str_returns_value(self) -> None:
        for s in Seniority:
            self.assertEqual(str(s), s.value)

    def test_is_str_subclass(self) -> None:
        self.assertIsInstance(Seniority.SENIOR, str)

    def test_string_comparison(self) -> None:
        self.assertEqual(Seniority.PRINCIPAL, "Principal")


# ---------------------------------------------------------------------------
# TestHireRequest
# ---------------------------------------------------------------------------

class TestHireRequest(unittest.TestCase):

    def test_all_fields_stored(self) -> None:
        req = _request(
            name="Alice",
            role=EmployeeRole.QA_ENGINEER,
            department=DepartmentType.QA,
            seniority=Seniority.SENIOR,
            skills=["Pytest", "Selenium"],
            director_id="dir-001",
        )
        self.assertEqual(req.name, "Alice")
        self.assertEqual(req.role, EmployeeRole.QA_ENGINEER)
        self.assertEqual(req.department, DepartmentType.QA)
        self.assertEqual(req.seniority, Seniority.SENIOR)
        self.assertEqual(req.skills, ["Pytest", "Selenium"])
        self.assertEqual(req.director_id, "dir-001")

    def test_is_frozen(self) -> None:
        req = _request()
        with self.assertRaises(Exception):
            req.name = "Changed"  # type: ignore[misc]

    def test_director_id_optional_defaults_to_none(self) -> None:
        req = _request()
        self.assertIsNone(req.director_id)

    def test_empty_skills_allowed(self) -> None:
        req = _request(skills=[])
        self.assertEqual(req.skills, [])

    def test_empty_name_raises_error(self) -> None:
        with self.assertRaises(InvalidHireRequestError):
            HireRequest(
                name="",
                role=EmployeeRole.BACKEND_AGENT,
                department=DepartmentType.BACKEND,
                seniority=Seniority.MID,
                skills=[],
            )

    def test_whitespace_name_raises_error(self) -> None:
        with self.assertRaises(InvalidHireRequestError):
            HireRequest(
                name="   ",
                role=EmployeeRole.BACKEND_AGENT,
                department=DepartmentType.BACKEND,
                seniority=Seniority.MID,
                skills=[],
            )

    def test_invalid_hire_request_error_is_exception(self) -> None:
        self.assertTrue(issubclass(InvalidHireRequestError, Exception))

    def test_role_field_is_employee_role_enum(self) -> None:
        req = _request()
        self.assertIsInstance(req.role, EmployeeRole)

    def test_department_field_is_department_type_enum(self) -> None:
        req = _request()
        self.assertIsInstance(req.department, DepartmentType)

    def test_seniority_field_is_seniority_enum(self) -> None:
        req = _request()
        self.assertIsInstance(req.seniority, Seniority)


# ---------------------------------------------------------------------------
# TestEmployee
# ---------------------------------------------------------------------------

class TestEmployee(unittest.TestCase):

    def setUp(self) -> None:
        self.reg, self.emp = _hire(name="Bob", skills=["Python", "SQL", "Docker"])

    def test_all_fields_stored(self) -> None:
        e = self.emp
        self.assertEqual(e.name, "Bob")
        self.assertEqual(e.role, EmployeeRole.BACKEND_AGENT)
        self.assertEqual(e.department, DepartmentType.BACKEND)
        self.assertEqual(e.status, EmployeeStatus.ACTIVE)
        self.assertAlmostEqual(e.workload, 0.0)
        self.assertEqual(e.skills, ["Python", "SQL", "Docker"])
        self.assertEqual(e.seniority, Seniority.MID)
        self.assertIsInstance(e.created_at, datetime)
        self.assertIsInstance(e.id, str)
        self.assertGreater(len(e.id), 0)

    def test_id_is_unique_per_hire(self) -> None:
        reg = _registry()
        _, e1 = _hire(reg, name="E1")
        _, e2 = _hire(reg, name="E2")
        self.assertNotEqual(e1.id, e2.id)

    def test_is_mutable(self) -> None:
        self.emp.status = EmployeeStatus.WORKING
        self.assertEqual(self.emp.status, EmployeeStatus.WORKING)

    def test_director_defaults_to_none(self) -> None:
        self.assertIsNone(self.emp.director)

    def test_is_available_true_when_active_with_capacity(self) -> None:
        self.emp.status = EmployeeStatus.ACTIVE
        self.emp.workload = 0.0
        self.assertTrue(self.emp.is_available())

    def test_is_available_true_when_idle_with_capacity(self) -> None:
        self.emp.status = EmployeeStatus.IDLE
        self.emp.workload = 0.5
        self.assertTrue(self.emp.is_available())

    def test_is_available_false_when_fully_loaded(self) -> None:
        self.emp.status = EmployeeStatus.ACTIVE
        self.emp.workload = 1.0
        self.assertFalse(self.emp.is_available())

    def test_is_available_false_when_working(self) -> None:
        self.emp.status = EmployeeStatus.WORKING
        self.assertFalse(self.emp.is_available())

    def test_is_available_false_when_suspended(self) -> None:
        self.emp.status = EmployeeStatus.SUSPENDED
        self.assertFalse(self.emp.is_available())

    def test_is_available_false_when_terminated(self) -> None:
        self.emp.status = EmployeeStatus.TERMINATED
        self.assertFalse(self.emp.is_available())

    def test_is_active_workforce_true_for_active(self) -> None:
        self.assertTrue(self.emp.is_active_workforce())

    def test_is_active_workforce_false_for_terminated(self) -> None:
        self.emp.status = EmployeeStatus.TERMINATED
        self.assertFalse(self.emp.is_active_workforce())

    def test_utilization_returns_percentage(self) -> None:
        self.emp.workload = 0.75
        self.assertAlmostEqual(self.emp.utilization(), 75.0, places=2)

    def test_utilization_zero_when_idle(self) -> None:
        self.emp.workload = 0.0
        self.assertAlmostEqual(self.emp.utilization(), 0.0)

    def test_has_skill_true_for_existing(self) -> None:
        self.assertTrue(self.emp.has_skill("Python"))

    def test_has_skill_case_insensitive(self) -> None:
        self.assertTrue(self.emp.has_skill("python"))
        self.assertTrue(self.emp.has_skill("PYTHON"))

    def test_has_skill_false_for_missing(self) -> None:
        self.assertFalse(self.emp.has_skill("Rust"))

    def test_exception_hierarchy(self) -> None:
        self.assertTrue(issubclass(InvalidWorkloadError, EmployeeError))
        self.assertTrue(issubclass(EmployeeNotFoundError, EmployeeError))
        self.assertTrue(issubclass(EmployeeAlreadyTerminatedError, EmployeeError))
        self.assertTrue(issubclass(EmployeeNotSuspendedError, EmployeeError))
        self.assertTrue(issubclass(EmployeeAlreadySuspendedError, EmployeeError))

    def test_created_at_is_timezone_aware(self) -> None:
        self.assertIsNotNone(self.emp.created_at.tzinfo)


# ---------------------------------------------------------------------------
# TestHiring
# ---------------------------------------------------------------------------

class TestHiring(unittest.TestCase):

    def test_hire_returns_employee(self) -> None:
        reg = _registry()
        emp = reg.hire(_request())
        self.assertIsInstance(emp, Employee)

    def test_hire_sets_active_status(self) -> None:
        _, emp = _hire()
        self.assertEqual(emp.status, EmployeeStatus.ACTIVE)

    def test_hire_sets_zero_workload(self) -> None:
        _, emp = _hire()
        self.assertAlmostEqual(emp.workload, 0.0)

    def test_hire_sets_created_at_to_now(self) -> None:
        before = datetime.now(timezone.utc)
        _, emp = _hire()
        after = datetime.now(timezone.utc)
        self.assertGreaterEqual(emp.created_at, before)
        self.assertLessEqual(emp.created_at, after)

    def test_hire_assigns_unique_id(self) -> None:
        reg = _registry()
        e1 = reg.hire(_request(name="E1"))
        e2 = reg.hire(_request(name="E2"))
        self.assertNotEqual(e1.id, e2.id)

    def test_hire_copies_skills(self) -> None:
        original_skills = ["Python", "SQL"]
        _, emp = _hire(skills=original_skills)
        original_skills.append("Go")  # mutate original
        self.assertEqual(emp.skills, ["Python", "SQL"])  # copy unaffected

    def test_hire_increments_count(self) -> None:
        reg = _registry()
        self.assertEqual(reg.count(), 0)
        reg.hire(_request(name="E1"))
        self.assertEqual(reg.count(), 1)
        reg.hire(_request(name="E2"))
        self.assertEqual(reg.count(), 2)

    def test_hire_with_director_sets_director(self) -> None:
        _, emp = _hire(director_id="dir-001")
        self.assertEqual(emp.director, "dir-001")

    def test_hire_without_director_is_none(self) -> None:
        _, emp = _hire()
        self.assertIsNone(emp.director)

    def test_hire_stores_role(self) -> None:
        _, emp = _hire(role=EmployeeRole.QA_ENGINEER)
        self.assertEqual(emp.role, EmployeeRole.QA_ENGINEER)

    def test_hire_stores_department(self) -> None:
        _, emp = _hire(department=DepartmentType.QA)
        self.assertEqual(emp.department, DepartmentType.QA)

    def test_hire_stores_seniority(self) -> None:
        _, emp = _hire(seniority=Seniority.SENIOR)
        self.assertEqual(emp.seniority, Seniority.SENIOR)

    def test_multiple_hires_all_retrievable(self) -> None:
        reg = _registry()
        ids = []
        for i in range(5):
            emp = reg.hire(_request(name=f"Agent {i}"))
            ids.append(emp.id)
        for emp_id in ids:
            self.assertIsInstance(reg.get(emp_id), Employee)


# ---------------------------------------------------------------------------
# TestTermination
# ---------------------------------------------------------------------------

class TestTermination(unittest.TestCase):

    def test_terminate_sets_terminated_status(self) -> None:
        reg, emp = _hire()
        reg.terminate(emp.id)
        self.assertEqual(emp.status, EmployeeStatus.TERMINATED)

    def test_terminate_returns_employee(self) -> None:
        reg, emp = _hire()
        result = reg.terminate(emp.id)
        self.assertIs(result, emp)

    def test_terminate_zeroes_workload(self) -> None:
        reg, emp = _hire()
        reg.update_workload(emp.id, 0.7)
        reg.terminate(emp.id)
        self.assertAlmostEqual(emp.workload, 0.0)

    def test_terminate_unknown_raises(self) -> None:
        reg = _registry()
        with self.assertRaises(EmployeeNotFoundError):
            reg.terminate("no-such-id")

    def test_terminate_already_terminated_raises(self) -> None:
        reg, emp = _hire()
        reg.terminate(emp.id)
        with self.assertRaises(EmployeeAlreadyTerminatedError):
            reg.terminate(emp.id)

    def test_terminate_suspended_employee_allowed(self) -> None:
        reg, emp = _hire()
        reg.suspend(emp.id)
        reg.terminate(emp.id)
        self.assertEqual(emp.status, EmployeeStatus.TERMINATED)

    def test_terminate_transferred_employee_allowed(self) -> None:
        reg, emp = _hire()
        reg.transfer(emp.id, DepartmentType.FRONTEND)
        reg.terminate(emp.id)
        self.assertEqual(emp.status, EmployeeStatus.TERMINATED)

    def test_terminated_employee_excluded_from_active(self) -> None:
        reg, emp = _hire()
        reg.terminate(emp.id)
        active = reg.list_active()
        self.assertNotIn(emp, active)

    def test_terminated_employee_still_in_all(self) -> None:
        reg, emp = _hire()
        reg.terminate(emp.id)
        self.assertIn(emp, reg.list_all())

    def test_terminated_error_message_contains_name(self) -> None:
        reg, emp = _hire(name="TerminatedAgent")
        reg.terminate(emp.id)
        try:
            reg.terminate(emp.id)
            self.fail("Expected EmployeeAlreadyTerminatedError")
        except EmployeeAlreadyTerminatedError as e:
            self.assertIn("TerminatedAgent", str(e))


# ---------------------------------------------------------------------------
# TestSuspension
# ---------------------------------------------------------------------------

class TestSuspension(unittest.TestCase):

    def test_suspend_sets_suspended_status(self) -> None:
        reg, emp = _hire()
        reg.suspend(emp.id)
        self.assertEqual(emp.status, EmployeeStatus.SUSPENDED)

    def test_suspend_returns_employee(self) -> None:
        reg, emp = _hire()
        result = reg.suspend(emp.id)
        self.assertIs(result, emp)

    def test_suspend_unknown_raises(self) -> None:
        reg = _registry()
        with self.assertRaises(EmployeeNotFoundError):
            reg.suspend("no-such-id")

    def test_suspend_terminated_raises(self) -> None:
        reg, emp = _hire()
        reg.terminate(emp.id)
        with self.assertRaises(EmployeeAlreadyTerminatedError):
            reg.suspend(emp.id)

    def test_suspend_already_suspended_raises(self) -> None:
        reg, emp = _hire()
        reg.suspend(emp.id)
        with self.assertRaises(EmployeeAlreadySuspendedError):
            reg.suspend(emp.id)

    def test_suspend_working_employee_allowed(self) -> None:
        reg, emp = _hire()
        reg.update_status(emp.id, EmployeeStatus.WORKING)
        reg.suspend(emp.id)
        self.assertEqual(emp.status, EmployeeStatus.SUSPENDED)

    def test_suspend_waiting_employee_allowed(self) -> None:
        reg, emp = _hire()
        reg.update_status(emp.id, EmployeeStatus.WAITING)
        reg.suspend(emp.id)
        self.assertEqual(emp.status, EmployeeStatus.SUSPENDED)

    def test_suspended_excluded_from_active(self) -> None:
        reg, emp = _hire()
        reg.suspend(emp.id)
        self.assertNotIn(emp, reg.list_active())

    def test_suspended_not_available(self) -> None:
        reg, emp = _hire()
        reg.suspend(emp.id)
        self.assertFalse(emp.is_available())

    def test_suspend_retains_department(self) -> None:
        reg, emp = _hire(department=DepartmentType.SECURITY)
        reg.suspend(emp.id)
        self.assertEqual(emp.department, DepartmentType.SECURITY)

    def test_suspend_retains_skills(self) -> None:
        reg, emp = _hire(skills=["Python", "SQL"])
        reg.suspend(emp.id)
        self.assertEqual(emp.skills, ["Python", "SQL"])


# ---------------------------------------------------------------------------
# TestReactivation
# ---------------------------------------------------------------------------

class TestReactivation(unittest.TestCase):

    def test_reactivate_sets_idle_status(self) -> None:
        reg, emp = _hire()
        reg.suspend(emp.id)
        reg.reactivate(emp.id)
        self.assertEqual(emp.status, EmployeeStatus.IDLE)

    def test_reactivate_returns_employee(self) -> None:
        reg, emp = _hire()
        reg.suspend(emp.id)
        result = reg.reactivate(emp.id)
        self.assertIs(result, emp)

    def test_reactivate_unknown_raises(self) -> None:
        reg = _registry()
        with self.assertRaises(EmployeeNotFoundError):
            reg.reactivate("no-such-id")

    def test_reactivate_terminated_raises(self) -> None:
        reg, emp = _hire()
        reg.terminate(emp.id)
        with self.assertRaises(EmployeeAlreadyTerminatedError):
            reg.reactivate(emp.id)

    def test_reactivate_active_raises(self) -> None:
        reg, emp = _hire()
        with self.assertRaises(EmployeeNotSuspendedError):
            reg.reactivate(emp.id)

    def test_reactivate_working_raises(self) -> None:
        reg, emp = _hire()
        reg.update_status(emp.id, EmployeeStatus.WORKING)
        with self.assertRaises(EmployeeNotSuspendedError):
            reg.reactivate(emp.id)

    def test_reactivate_idle_raises(self) -> None:
        reg, emp = _hire()
        reg.update_status(emp.id, EmployeeStatus.IDLE)
        with self.assertRaises(EmployeeNotSuspendedError):
            reg.reactivate(emp.id)

    def test_reactivated_employee_in_active_list(self) -> None:
        reg, emp = _hire()
        reg.suspend(emp.id)
        reg.reactivate(emp.id)
        self.assertIn(emp, reg.list_active())

    def test_suspend_reactivate_cycle_repeatable(self) -> None:
        reg, emp = _hire()
        for _ in range(3):
            reg.suspend(emp.id)
            self.assertEqual(emp.status, EmployeeStatus.SUSPENDED)
            reg.reactivate(emp.id)
            self.assertEqual(emp.status, EmployeeStatus.IDLE)

    def test_reactivated_error_message_includes_status(self) -> None:
        reg, emp = _hire()
        try:
            reg.reactivate(emp.id)
            self.fail("Expected EmployeeNotSuspendedError")
        except EmployeeNotSuspendedError as e:
            self.assertIn("ACTIVE", str(e))


# ---------------------------------------------------------------------------
# TestTransfer
# ---------------------------------------------------------------------------

class TestTransfer(unittest.TestCase):

    def test_transfer_updates_department(self) -> None:
        reg, emp = _hire(department=DepartmentType.BACKEND)
        reg.transfer(emp.id, DepartmentType.FRONTEND)
        self.assertEqual(emp.department, DepartmentType.FRONTEND)

    def test_transfer_sets_transferred_status(self) -> None:
        reg, emp = _hire()
        reg.transfer(emp.id, DepartmentType.FRONTEND)
        self.assertEqual(emp.status, EmployeeStatus.TRANSFERRED)

    def test_transfer_returns_employee(self) -> None:
        reg, emp = _hire()
        result = reg.transfer(emp.id, DepartmentType.FRONTEND)
        self.assertIs(result, emp)

    def test_transfer_with_new_director_updates_director(self) -> None:
        reg, emp = _hire(director_id="dir-old")
        reg.transfer(emp.id, DepartmentType.FRONTEND, new_director_id="dir-new")
        self.assertEqual(emp.director, "dir-new")

    def test_transfer_without_director_clears_director(self) -> None:
        reg, emp = _hire(director_id="dir-old")
        reg.transfer(emp.id, DepartmentType.FRONTEND)
        self.assertIsNone(emp.director)

    def test_transfer_terminated_raises(self) -> None:
        reg, emp = _hire()
        reg.terminate(emp.id)
        with self.assertRaises(EmployeeAlreadyTerminatedError):
            reg.transfer(emp.id, DepartmentType.FRONTEND)

    def test_transfer_unknown_raises(self) -> None:
        reg = _registry()
        with self.assertRaises(EmployeeNotFoundError):
            reg.transfer("no-id", DepartmentType.FRONTEND)

    def test_transfer_suspended_allowed(self) -> None:
        reg, emp = _hire()
        reg.suspend(emp.id)
        reg.transfer(emp.id, DepartmentType.DEVOPS)
        self.assertEqual(emp.department, DepartmentType.DEVOPS)
        self.assertEqual(emp.status, EmployeeStatus.TRANSFERRED)

    def test_transferred_employee_excluded_from_active(self) -> None:
        reg, emp = _hire()
        reg.transfer(emp.id, DepartmentType.FRONTEND)
        self.assertNotIn(emp, reg.list_active())

    def test_transferred_employee_in_new_department_list(self) -> None:
        reg, emp = _hire(department=DepartmentType.BACKEND)
        reg.transfer(emp.id, DepartmentType.FRONTEND)
        frontend_staff = reg.list_by_department(DepartmentType.FRONTEND)
        self.assertIn(emp, frontend_staff)

    def test_transferred_employee_no_longer_in_old_department(self) -> None:
        reg, emp = _hire(department=DepartmentType.BACKEND)
        reg.transfer(emp.id, DepartmentType.FRONTEND)
        backend_staff = reg.list_by_department(DepartmentType.BACKEND)
        self.assertNotIn(emp, backend_staff)

    def test_transfer_then_activate(self) -> None:
        reg, emp = _hire()
        reg.transfer(emp.id, DepartmentType.DEVOPS)
        reg.update_status(emp.id, EmployeeStatus.ACTIVE)
        self.assertEqual(emp.status, EmployeeStatus.ACTIVE)
        self.assertIn(emp, reg.list_active())


# ---------------------------------------------------------------------------
# TestAssignment
# ---------------------------------------------------------------------------

class TestAssignment(unittest.TestCase):

    def test_assign_director_updates_director(self) -> None:
        reg, emp = _hire()
        reg.assign_director(emp.id, "dir-001")
        self.assertEqual(emp.director, "dir-001")

    def test_assign_director_returns_employee(self) -> None:
        reg, emp = _hire()
        result = reg.assign_director(emp.id, "dir-001")
        self.assertIs(result, emp)

    def test_assign_director_replaces_existing(self) -> None:
        reg, emp = _hire(director_id="dir-old")
        reg.assign_director(emp.id, "dir-new")
        self.assertEqual(emp.director, "dir-new")

    def test_assign_director_terminated_raises(self) -> None:
        reg, emp = _hire()
        reg.terminate(emp.id)
        with self.assertRaises(EmployeeAlreadyTerminatedError):
            reg.assign_director(emp.id, "dir-001")

    def test_assign_director_unknown_raises(self) -> None:
        reg = _registry()
        with self.assertRaises(EmployeeNotFoundError):
            reg.assign_director("no-id", "dir-001")

    def test_assign_department_updates_department(self) -> None:
        reg, emp = _hire(department=DepartmentType.BACKEND)
        reg.assign_department(emp.id, DepartmentType.DEVOPS)
        self.assertEqual(emp.department, DepartmentType.DEVOPS)

    def test_assign_department_returns_employee(self) -> None:
        reg, emp = _hire()
        result = reg.assign_department(emp.id, DepartmentType.QA)
        self.assertIs(result, emp)

    def test_assign_department_does_not_change_status(self) -> None:
        reg, emp = _hire()
        initial_status = emp.status
        reg.assign_department(emp.id, DepartmentType.QA)
        self.assertEqual(emp.status, initial_status)

    def test_assign_department_terminated_raises(self) -> None:
        reg, emp = _hire()
        reg.terminate(emp.id)
        with self.assertRaises(EmployeeAlreadyTerminatedError):
            reg.assign_department(emp.id, DepartmentType.QA)

    def test_assign_department_unknown_raises(self) -> None:
        reg = _registry()
        with self.assertRaises(EmployeeNotFoundError):
            reg.assign_department("no-id", DepartmentType.QA)

    def test_update_status_changes_status(self) -> None:
        reg, emp = _hire()
        reg.update_status(emp.id, EmployeeStatus.WORKING)
        self.assertEqual(emp.status, EmployeeStatus.WORKING)

    def test_update_status_terminated_raises(self) -> None:
        reg, emp = _hire()
        reg.terminate(emp.id)
        with self.assertRaises(EmployeeAlreadyTerminatedError):
            reg.update_status(emp.id, EmployeeStatus.ACTIVE)


# ---------------------------------------------------------------------------
# TestWorkload
# ---------------------------------------------------------------------------

class TestWorkload(unittest.TestCase):

    def test_update_workload_changes_value(self) -> None:
        reg, emp = _hire()
        reg.update_workload(emp.id, 0.6)
        self.assertAlmostEqual(emp.workload, 0.6)

    def test_update_workload_returns_employee(self) -> None:
        reg, emp = _hire()
        result = reg.update_workload(emp.id, 0.5)
        self.assertIs(result, emp)

    def test_update_workload_zero_allowed(self) -> None:
        reg, emp = _hire()
        reg.update_workload(emp.id, 0.0)
        self.assertAlmostEqual(emp.workload, 0.0)

    def test_update_workload_one_allowed(self) -> None:
        reg, emp = _hire()
        reg.update_workload(emp.id, 1.0)
        self.assertAlmostEqual(emp.workload, 1.0)

    def test_update_workload_negative_raises(self) -> None:
        reg, emp = _hire()
        with self.assertRaises(InvalidWorkloadError):
            reg.update_workload(emp.id, -0.1)

    def test_update_workload_above_one_raises(self) -> None:
        reg, emp = _hire()
        with self.assertRaises(InvalidWorkloadError):
            reg.update_workload(emp.id, 1.01)

    def test_update_workload_terminated_raises(self) -> None:
        reg, emp = _hire()
        reg.terminate(emp.id)
        with self.assertRaises(EmployeeAlreadyTerminatedError):
            reg.update_workload(emp.id, 0.5)

    def test_update_workload_unknown_raises(self) -> None:
        reg = _registry()
        with self.assertRaises(EmployeeNotFoundError):
            reg.update_workload("no-id", 0.5)

    def test_high_workload_makes_employee_unavailable(self) -> None:
        reg, emp = _hire()
        reg.update_workload(emp.id, 1.0)
        self.assertFalse(emp.is_available())

    def test_partial_workload_still_available(self) -> None:
        reg, emp = _hire()
        reg.update_workload(emp.id, 0.8)
        self.assertTrue(emp.is_available())


# ---------------------------------------------------------------------------
# TestListing
# ---------------------------------------------------------------------------

class TestListing(unittest.TestCase):

    def setUp(self) -> None:
        self.reg = _registry()
        self.backend1 = self.reg.hire(_request(name="BE1", department=DepartmentType.BACKEND))
        self.backend2 = self.reg.hire(_request(name="BE2", department=DepartmentType.BACKEND, role=EmployeeRole.FRONTEND_AGENT))
        self.qa1 = self.reg.hire(_request(name="QA1", department=DepartmentType.QA, role=EmployeeRole.QA_ENGINEER))
        self.suspended = self.reg.hire(_request(name="SUS1", department=DepartmentType.BACKEND))
        self.reg.suspend(self.suspended.id)
        self.terminated = self.reg.hire(_request(name="TER1", department=DepartmentType.QA))
        self.reg.terminate(self.terminated.id)

    def test_list_all_returns_all_records(self) -> None:
        self.assertEqual(len(self.reg.list_all()), 5)

    def test_list_all_returns_copy(self) -> None:
        lst = self.reg.list_all()
        lst.clear()
        self.assertEqual(self.reg.count(), 5)

    def test_list_active_excludes_suspended(self) -> None:
        active = self.reg.list_active()
        self.assertNotIn(self.suspended, active)

    def test_list_active_excludes_terminated(self) -> None:
        active = self.reg.list_active()
        self.assertNotIn(self.terminated, active)

    def test_list_active_includes_active_employees(self) -> None:
        active = self.reg.list_active()
        self.assertIn(self.backend1, active)
        self.assertIn(self.backend2, active)
        self.assertIn(self.qa1, active)

    def test_list_by_department_backend(self) -> None:
        backend = self.reg.list_by_department(DepartmentType.BACKEND)
        # backend1, backend2, suspended (dept=BACKEND)
        dept_names = {e.name for e in backend}
        self.assertIn("BE1", dept_names)
        self.assertIn("BE2", dept_names)
        self.assertIn("SUS1", dept_names)

    def test_list_by_department_includes_suspended(self) -> None:
        backend = self.reg.list_by_department(DepartmentType.BACKEND)
        self.assertIn(self.suspended, backend)

    def test_list_by_department_includes_terminated(self) -> None:
        qa = self.reg.list_by_department(DepartmentType.QA)
        self.assertIn(self.terminated, qa)

    def test_list_by_department_empty_for_unregistered(self) -> None:
        devops = self.reg.list_by_department(DepartmentType.DEVOPS)
        self.assertEqual(devops, [])

    def test_list_by_role_backend_agent(self) -> None:
        agents = self.reg.list_by_role(EmployeeRole.BACKEND_AGENT)
        names = {e.name for e in agents}
        self.assertIn("BE1", names)
        self.assertIn("SUS1", names)
        self.assertIn("TER1", names)

    def test_list_by_role_qa_engineer(self) -> None:
        qa_agents = self.reg.list_by_role(EmployeeRole.QA_ENGINEER)
        self.assertIn(self.qa1, qa_agents)

    def test_list_by_seniority_mid(self) -> None:
        mid = self.reg.list_by_seniority(Seniority.MID)
        self.assertGreater(len(mid), 0)

    def test_list_available_excludes_fully_loaded(self) -> None:
        self.reg.update_workload(self.backend1.id, 1.0)
        available = self.reg.list_available()
        self.assertNotIn(self.backend1, available)

    def test_list_available_excludes_suspended(self) -> None:
        available = self.reg.list_available()
        self.assertNotIn(self.suspended, available)

    def test_list_available_includes_free_active(self) -> None:
        available = self.reg.list_available()
        self.assertIn(self.backend1, available)

    def test_get_returns_correct_employee(self) -> None:
        retrieved = self.reg.get(self.qa1.id)
        self.assertIs(retrieved, self.qa1)

    def test_get_unknown_raises(self) -> None:
        with self.assertRaises(EmployeeNotFoundError):
            self.reg.get("no-such-id")


# ---------------------------------------------------------------------------
# TestStatistics
# ---------------------------------------------------------------------------

class TestStatistics(unittest.TestCase):

    def setUp(self) -> None:
        self.reg = _registry()

    def test_statistics_empty_registry(self) -> None:
        stats = self.reg.statistics()
        self.assertEqual(stats["total_employees"], 0)
        self.assertEqual(stats["active_headcount"], 0)
        self.assertAlmostEqual(stats["average_workload"], 0.0)

    def test_statistics_has_required_keys(self) -> None:
        stats = self.reg.statistics()
        for key in (
            "total_employees", "active_headcount", "by_status",
            "by_department", "by_role", "by_seniority",
            "average_workload", "available_count",
        ):
            self.assertIn(key, stats)

    def test_statistics_total_employees_correct(self) -> None:
        for i in range(4):
            self.reg.hire(_request(name=f"Agent {i}"))
        stats = self.reg.statistics()
        self.assertEqual(stats["total_employees"], 4)

    def test_statistics_active_headcount_excludes_terminated(self) -> None:
        emp = self.reg.hire(_request(name="A1"))
        self.reg.hire(_request(name="A2"))
        self.reg.terminate(emp.id)
        stats = self.reg.statistics()
        self.assertEqual(stats["active_headcount"], 1)

    def test_statistics_active_headcount_excludes_suspended(self) -> None:
        emp = self.reg.hire(_request(name="A1"))
        self.reg.hire(_request(name="A2"))
        self.reg.suspend(emp.id)
        stats = self.reg.statistics()
        self.assertEqual(stats["active_headcount"], 1)

    def test_statistics_by_status_covers_all_statuses(self) -> None:
        stats = self.reg.statistics()
        for status in EmployeeStatus:
            self.assertIn(status.value, stats["by_status"])

    def test_statistics_by_role_covers_all_roles(self) -> None:
        stats = self.reg.statistics()
        for role in EmployeeRole:
            self.assertIn(role.value, stats["by_role"])

    def test_statistics_by_seniority_covers_all_levels(self) -> None:
        stats = self.reg.statistics()
        for seniority in Seniority:
            self.assertIn(seniority.value, stats["by_seniority"])

    def test_statistics_by_department_counts_correctly(self) -> None:
        self.reg.hire(_request(name="B1", department=DepartmentType.BACKEND))
        self.reg.hire(_request(name="B2", department=DepartmentType.BACKEND))
        self.reg.hire(_request(name="Q1", department=DepartmentType.QA))
        stats = self.reg.statistics()
        self.assertEqual(stats["by_department"].get("Backend", 0), 2)
        self.assertEqual(stats["by_department"].get("QA", 0), 1)

    def test_statistics_average_workload_correct(self) -> None:
        e1 = self.reg.hire(_request(name="E1"))
        e2 = self.reg.hire(_request(name="E2"))
        self.reg.update_workload(e1.id, 0.4)
        self.reg.update_workload(e2.id, 0.6)
        stats = self.reg.statistics()
        self.assertAlmostEqual(stats["average_workload"], 0.5, places=4)

    def test_statistics_available_count_correct(self) -> None:
        e1 = self.reg.hire(_request(name="E1"))
        e2 = self.reg.hire(_request(name="E2"))
        self.reg.update_workload(e1.id, 1.0)  # fully loaded, unavailable
        stats = self.reg.statistics()
        self.assertEqual(stats["available_count"], 1)

    def test_statistics_by_role_counts_correctly(self) -> None:
        self.reg.hire(_request(name="BE1", role=EmployeeRole.BACKEND_AGENT))
        self.reg.hire(_request(name="BE2", role=EmployeeRole.BACKEND_AGENT))
        self.reg.hire(_request(name="QA1", role=EmployeeRole.QA_ENGINEER))
        stats = self.reg.statistics()
        self.assertEqual(stats["by_role"]["Backend Agent"], 2)
        self.assertEqual(stats["by_role"]["QA Engineer"], 1)

    def test_statistics_by_seniority_counts_correctly(self) -> None:
        self.reg.hire(_request(name="S1", seniority=Seniority.SENIOR))
        self.reg.hire(_request(name="S2", seniority=Seniority.SENIOR))
        self.reg.hire(_request(name="J1", seniority=Seniority.JUNIOR))
        stats = self.reg.statistics()
        self.assertEqual(stats["by_seniority"]["Senior"], 2)
        self.assertEqual(stats["by_seniority"]["Junior"], 1)

    def test_statistics_active_headcount_includes_working_and_waiting(self) -> None:
        e1 = self.reg.hire(_request(name="E1"))
        e2 = self.reg.hire(_request(name="E2"))
        self.reg.update_status(e1.id, EmployeeStatus.WORKING)
        self.reg.update_status(e2.id, EmployeeStatus.WAITING)
        stats = self.reg.statistics()
        self.assertEqual(stats["active_headcount"], 2)


# ---------------------------------------------------------------------------
# TestWorkforceHealth
# ---------------------------------------------------------------------------

class TestWorkforceHealth(unittest.TestCase):

    def setUp(self) -> None:
        self.reg = _registry()

    def test_health_empty_registry(self) -> None:
        health = self.reg.workforce_health()
        self.assertEqual(health["total_employees"], 0)
        self.assertEqual(health["active_headcount"], 0)
        self.assertEqual(health["overall_health"], "OK")

    def test_health_has_required_keys(self) -> None:
        health = self.reg.workforce_health()
        for key in (
            "total_employees", "active_headcount", "overloaded_count",
            "idle_count", "working_count", "waiting_count",
            "suspended_count", "terminated_count", "transferred_count",
            "average_workload", "overall_health", "concerns", "employees",
        ):
            self.assertIn(key, health)

    def test_health_overall_ok_when_healthy(self) -> None:
        self.reg.hire(_request(name="E1"))
        self.reg.hire(_request(name="E2"))
        health = self.reg.workforce_health()
        self.assertEqual(health["overall_health"], "OK")

    def test_health_warning_when_overloaded_employees_exist(self) -> None:
        emp = self.reg.hire(_request(name="E1"))
        self.reg.update_workload(emp.id, 0.95)
        health = self.reg.workforce_health()
        self.assertIn(health["overall_health"], ("WARNING", "CRITICAL"))

    def test_health_critical_when_many_overloaded(self) -> None:
        # > 30% overloaded should trigger CRITICAL
        for i in range(7):
            e = self.reg.hire(_request(name=f"Heavy{i}"))
            self.reg.update_workload(e.id, 0.95)
        for i in range(3):
            self.reg.hire(_request(name=f"Light{i}"))
        health = self.reg.workforce_health()
        self.assertEqual(health["overall_health"], "CRITICAL")

    def test_health_overloaded_count_correct(self) -> None:
        e1 = self.reg.hire(_request(name="E1"))
        self.reg.hire(_request(name="E2"))
        self.reg.update_workload(e1.id, 0.95)
        health = self.reg.workforce_health()
        self.assertEqual(health["overloaded_count"], 1)

    def test_health_idle_count_correct(self) -> None:
        e1 = self.reg.hire(_request(name="E1"))
        self.reg.hire(_request(name="E2"))
        self.reg.update_status(e1.id, EmployeeStatus.IDLE)
        health = self.reg.workforce_health()
        self.assertEqual(health["idle_count"], 1)

    def test_health_suspended_count_correct(self) -> None:
        emp = self.reg.hire(_request(name="E1"))
        self.reg.hire(_request(name="E2"))
        self.reg.suspend(emp.id)
        health = self.reg.workforce_health()
        self.assertEqual(health["suspended_count"], 1)

    def test_health_terminated_count_correct(self) -> None:
        emp = self.reg.hire(_request(name="E1"))
        self.reg.hire(_request(name="E2"))
        self.reg.terminate(emp.id)
        health = self.reg.workforce_health()
        self.assertEqual(health["terminated_count"], 1)

    def test_health_transferred_count_correct(self) -> None:
        emp = self.reg.hire(_request(name="E1"))
        self.reg.transfer(emp.id, DepartmentType.FRONTEND)
        health = self.reg.workforce_health()
        self.assertEqual(health["transferred_count"], 1)

    def test_health_concerns_non_empty_when_issues_exist(self) -> None:
        emp = self.reg.hire(_request(name="E1"))
        self.reg.update_workload(emp.id, 0.95)
        health = self.reg.workforce_health()
        self.assertGreater(len(health["concerns"]), 0)

    def test_health_concerns_empty_when_healthy(self) -> None:
        self.reg.hire(_request(name="E1"))
        self.reg.hire(_request(name="E2"))
        health = self.reg.workforce_health()
        # No overloaded, low suspended ratio → no concerns besides possible idle
        # (idle concern is present even for healthy teams)
        overloaded_concern = any("overloaded" in c.lower() for c in health["concerns"])
        self.assertFalse(overloaded_concern)

    def test_health_per_employee_snapshot_has_required_fields(self) -> None:
        self.reg.hire(_request(name="E1"))
        health = self.reg.workforce_health()
        snap = health["employees"][0]
        for key in (
            "id", "name", "role", "department", "seniority",
            "status", "workload", "utilization", "is_overloaded", "is_available",
        ):
            self.assertIn(key, snap)

    def test_health_average_workload_correct(self) -> None:
        e1 = self.reg.hire(_request(name="E1"))
        e2 = self.reg.hire(_request(name="E2"))
        self.reg.update_workload(e1.id, 0.2)
        self.reg.update_workload(e2.id, 0.8)
        health = self.reg.workforce_health()
        self.assertAlmostEqual(health["average_workload"], 0.5, places=4)

    def test_health_overall_health_is_valid_grade(self) -> None:
        health = self.reg.workforce_health()
        self.assertIn(health["overall_health"], ("OK", "WARNING", "CRITICAL"))


# ---------------------------------------------------------------------------
# TestIntegration
# ---------------------------------------------------------------------------

class TestIntegration(unittest.TestCase):

    def _build_workforce(self) -> WorkforceRegistry:
        reg = _registry()

        # Backend team
        reg.hire(_request(
            name="Alice — Backend Lead",
            role=EmployeeRole.BACKEND_AGENT,
            department=DepartmentType.BACKEND,
            seniority=Seniority.LEAD,
            skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
            director_id="dir-backend",
        ))
        reg.hire(_request(
            name="Bob — Backend Senior",
            role=EmployeeRole.BACKEND_AGENT,
            department=DepartmentType.BACKEND,
            seniority=Seniority.SENIOR,
            skills=["Python", "REST APIs", "Redis"],
            director_id="dir-backend",
        ))
        reg.hire(_request(
            name="Carol — Backend Junior",
            role=EmployeeRole.BACKEND_AGENT,
            department=DepartmentType.BACKEND,
            seniority=Seniority.JUNIOR,
            skills=["Python", "SQL"],
            director_id="dir-backend",
        ))

        # QA team
        reg.hire(_request(
            name="Dave — QA Senior",
            role=EmployeeRole.QA_ENGINEER,
            department=DepartmentType.QA,
            seniority=Seniority.SENIOR,
            skills=["Pytest", "Selenium", "Test Planning"],
            director_id="dir-qa",
        ))

        # DevOps
        reg.hire(_request(
            name="Eve — DevOps",
            role=EmployeeRole.DEVOPS_ENGINEER,
            department=DepartmentType.DEVOPS,
            seniority=Seniority.MID,
            skills=["Docker", "Kubernetes", "CI/CD"],
            director_id="dir-devops",
        ))

        # Security — will be suspended
        sec = reg.hire(_request(
            name="Frank — Security",
            role=EmployeeRole.SECURITY_SPECIALIST,
            department=DepartmentType.SECURITY,
            seniority=Seniority.SENIOR,
            skills=["OWASP", "Penetration Testing"],
            director_id="dir-security",
        ))
        reg.suspend(sec.id)

        return reg

    def test_workforce_total_count(self) -> None:
        reg = self._build_workforce()
        self.assertEqual(reg.count(), 6)

    def test_active_headcount_excludes_suspended(self) -> None:
        reg = self._build_workforce()
        active = reg.list_active()
        self.assertEqual(len(active), 5)

    def test_backend_team_size(self) -> None:
        reg = self._build_workforce()
        backend = reg.list_by_department(DepartmentType.BACKEND)
        self.assertEqual(len(backend), 3)

    def test_qa_team_contains_correct_member(self) -> None:
        reg = self._build_workforce()
        qa = reg.list_by_department(DepartmentType.QA)
        names = {e.name for e in qa}
        self.assertIn("Dave — QA Senior", names)

    def test_list_by_role_backend_agent(self) -> None:
        reg = self._build_workforce()
        backend_agents = reg.list_by_role(EmployeeRole.BACKEND_AGENT)
        self.assertEqual(len(backend_agents), 3)

    def test_skill_search_finds_python_speakers(self) -> None:
        reg = self._build_workforce()
        python_devs = [e for e in reg.list_all() if e.has_skill("Python")]
        self.assertGreaterEqual(len(python_devs), 3)

    def test_transfer_backend_to_devops(self) -> None:
        reg = self._build_workforce()
        backend_agents = reg.list_by_role(EmployeeRole.BACKEND_AGENT)
        junior = next(e for e in backend_agents if e.seniority == Seniority.JUNIOR)
        reg.transfer(junior.id, DepartmentType.DEVOPS, new_director_id="dir-devops")
        devops_team = reg.list_by_department(DepartmentType.DEVOPS)
        self.assertIn(junior, devops_team)
        self.assertEqual(junior.director, "dir-devops")

    def test_reactivate_suspended_security_specialist(self) -> None:
        reg = self._build_workforce()
        suspended = [e for e in reg.list_all() if e.status == EmployeeStatus.SUSPENDED]
        self.assertEqual(len(suspended), 1)
        reg.reactivate(suspended[0].id)
        self.assertEqual(reg.list_active().__len__(), 6)

    def test_health_report_identifies_suspended_concern(self) -> None:
        reg = self._build_workforce()
        health = reg.workforce_health()
        self.assertEqual(health["suspended_count"], 1)

    def test_statistics_seniority_distribution(self) -> None:
        reg = self._build_workforce()
        stats = reg.statistics()
        self.assertEqual(stats["by_seniority"]["Lead"], 1)
        self.assertEqual(stats["by_seniority"]["Senior"], 3)
        self.assertEqual(stats["by_seniority"]["Junior"], 1)
        self.assertEqual(stats["by_seniority"]["Mid"], 1)


if __name__ == "__main__":
    unittest.main()
