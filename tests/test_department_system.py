"""
Comprehensive unit tests for Sprint 5 — Department System.

Covers: DepartmentType, DepartmentStatus, DirectorStatus, Director,
Department, DepartmentHealth, and DepartmentRegistry (all methods).

Run with:
    .venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_department_system.py" -v
"""

import unittest
import uuid
from datetime import datetime, timezone

from core.department import (
    Department,
    DepartmentError,
    DepartmentHealth,
    InvalidCapacityError,
    InvalidWorkloadError,
    MemberNotFoundError,
)
from core.department_registry import (
    DepartmentAlreadyRegisteredError,
    DepartmentNotFoundError,
    DepartmentRegistry,
)
from core.department_status import DepartmentStatus, DirectorStatus
from core.department_type import DepartmentType
from core.director import Director, DirectorAlreadyAssignedError, DirectorNotFoundError


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _make_director(
    department: DepartmentType = DepartmentType.BACKEND,
    name: str = "Backend Director",
    status: DirectorStatus = DirectorStatus.IDLE,
    responsibilities: list | None = None,
    managed_agents: list | None = None,
) -> Director:
    return Director(
        id=str(uuid.uuid4()),
        name=name,
        department=department,
        status=status,
        responsibilities=responsibilities if responsibilities is not None else ["Oversee backend development."],
        managed_agents=managed_agents if managed_agents is not None else [],
        assigned_at=datetime.now(timezone.utc),
    )


def _make_department(
    dept_type: DepartmentType = DepartmentType.BACKEND,
    name: str = "Backend Department",
    status: DepartmentStatus = DepartmentStatus.READY,
    capacity: int = 10,
    workload: float = 0.0,
    director: Director | None = None,
    members: list | None = None,
    active_projects: list | None = None,
    active_tasks: list | None = None,
) -> Department:
    return Department(
        id=str(uuid.uuid4()),
        name=name,
        type=dept_type,
        director=director,
        members=members or [],
        status=status,
        capacity=capacity,
        active_projects=active_projects or [],
        active_tasks=active_tasks or [],
        workload=workload,
        created_at=datetime.now(timezone.utc),
    )


def _registry_with_dept(**kwargs) -> tuple[DepartmentRegistry, Department]:
    reg = DepartmentRegistry()
    dept = _make_department(**kwargs)
    reg.register(dept)
    return reg, dept


# ---------------------------------------------------------------------------
# TestDepartmentType
# ---------------------------------------------------------------------------

class TestDepartmentType(unittest.TestCase):

    def test_all_thirteen_values_exist(self) -> None:
        names = {dt.name for dt in DepartmentType}
        self.assertEqual(
            names,
            {
                "ENGINEERING", "FRONTEND", "BACKEND", "DATABASE",
                "DESIGN", "PRODUCT", "MARKETING", "QA",
                "SECURITY", "LEGAL", "FINANCE", "DEVOPS", "RESEARCH",
            },
        )

    def test_str_returns_value(self) -> None:
        for dt in DepartmentType:
            self.assertEqual(str(dt), dt.value)

    def test_is_str_subclass(self) -> None:
        self.assertIsInstance(DepartmentType.BACKEND, str)

    def test_string_comparison(self) -> None:
        self.assertEqual(DepartmentType.QA, "QA")
        self.assertEqual(DepartmentType.DEVOPS, "DevOps")

    def test_values_are_human_readable(self) -> None:
        for dt in DepartmentType:
            self.assertGreater(len(dt.value), 0)
            self.assertFalse(dt.value.startswith("_"))


# ---------------------------------------------------------------------------
# TestDepartmentStatus
# ---------------------------------------------------------------------------

class TestDepartmentStatus(unittest.TestCase):

    def test_all_six_values_exist(self) -> None:
        names = {s.name for s in DepartmentStatus}
        self.assertEqual(
            names,
            {"READY", "WORKING", "WAITING", "BLOCKED", "OVERLOADED", "OFFLINE"},
        )

    def test_str_returns_value(self) -> None:
        for s in DepartmentStatus:
            self.assertEqual(str(s), s.value)

    def test_is_str_subclass(self) -> None:
        self.assertIsInstance(DepartmentStatus.READY, str)

    def test_string_comparison(self) -> None:
        self.assertEqual(DepartmentStatus.OVERLOADED, "OVERLOADED")
        self.assertEqual(DepartmentStatus.OFFLINE, "OFFLINE")

    def test_enum_identity(self) -> None:
        self.assertIsNot(DepartmentStatus.READY, DepartmentStatus.WORKING)


# ---------------------------------------------------------------------------
# TestDirectorStatus
# ---------------------------------------------------------------------------

class TestDirectorStatus(unittest.TestCase):

    def test_all_four_values_exist(self) -> None:
        names = {s.name for s in DirectorStatus}
        self.assertEqual(names, {"ACTIVE", "IDLE", "OVERLOADED", "SUSPENDED"})

    def test_str_returns_value(self) -> None:
        for s in DirectorStatus:
            self.assertEqual(str(s), s.value)

    def test_is_str_subclass(self) -> None:
        self.assertIsInstance(DirectorStatus.ACTIVE, str)

    def test_string_comparison(self) -> None:
        self.assertEqual(DirectorStatus.SUSPENDED, "SUSPENDED")


# ---------------------------------------------------------------------------
# TestDirector
# ---------------------------------------------------------------------------

class TestDirector(unittest.TestCase):

    def setUp(self) -> None:
        self.director = _make_director(
            department=DepartmentType.BACKEND,
            name="Backend Director",
            status=DirectorStatus.IDLE,
            responsibilities=["Oversee API development.", "Code review."],
            managed_agents=["agent-001", "agent-002"],
        )

    def test_all_fields_stored(self) -> None:
        d = self.director
        self.assertEqual(d.name, "Backend Director")
        self.assertEqual(d.department, DepartmentType.BACKEND)
        self.assertEqual(d.status, DirectorStatus.IDLE)
        self.assertEqual(d.responsibilities, ["Oversee API development.", "Code review."])
        self.assertEqual(d.managed_agents, ["agent-001", "agent-002"])
        self.assertIsInstance(d.assigned_at, datetime)
        self.assertIsInstance(d.id, str)
        self.assertGreater(len(d.id), 0)

    def test_is_mutable(self) -> None:
        self.director.status = DirectorStatus.ACTIVE
        self.assertEqual(self.director.status, DirectorStatus.ACTIVE)

    def test_add_agent_appends(self) -> None:
        self.director.add_agent("agent-003")
        self.assertIn("agent-003", self.director.managed_agents)

    def test_add_agent_idempotent(self) -> None:
        before = self.director.agent_count()
        self.director.add_agent("agent-001")  # already present
        self.assertEqual(self.director.agent_count(), before)

    def test_remove_agent_removes(self) -> None:
        self.director.remove_agent("agent-001")
        self.assertNotIn("agent-001", self.director.managed_agents)

    def test_remove_agent_idempotent(self) -> None:
        self.director.remove_agent("agent-999")  # not present — should not raise
        self.assertEqual(self.director.agent_count(), 2)

    def test_agent_count_returns_correct_count(self) -> None:
        self.assertEqual(self.director.agent_count(), 2)

    def test_agent_count_zero_for_empty(self) -> None:
        d = _make_director(managed_agents=[])
        self.assertEqual(d.agent_count(), 0)

    def test_empty_responsibilities_allowed(self) -> None:
        d = _make_director(responsibilities=[])
        self.assertEqual(d.responsibilities, [])

    def test_department_type_is_enum(self) -> None:
        self.assertIsInstance(self.director.department, DepartmentType)

    def test_status_is_enum(self) -> None:
        self.assertIsInstance(self.director.status, DirectorStatus)

    def test_exceptions_are_importable(self) -> None:
        self.assertTrue(issubclass(DirectorNotFoundError, Exception))
        self.assertTrue(issubclass(DirectorAlreadyAssignedError, Exception))


# ---------------------------------------------------------------------------
# TestDepartment
# ---------------------------------------------------------------------------

class TestDepartment(unittest.TestCase):

    def setUp(self) -> None:
        self.director = _make_director()
        self.dept = _make_department(
            dept_type=DepartmentType.BACKEND,
            name="Backend Department",
            status=DepartmentStatus.READY,
            capacity=10,
            workload=0.5,
            director=self.director,
            members=["agent-001", "agent-002"],
            active_projects=["proj-001"],
            active_tasks=["task-001", "task-002"],
        )

    def test_all_fields_stored(self) -> None:
        d = self.dept
        self.assertEqual(d.name, "Backend Department")
        self.assertEqual(d.type, DepartmentType.BACKEND)
        self.assertEqual(d.status, DepartmentStatus.READY)
        self.assertEqual(d.capacity, 10)
        self.assertAlmostEqual(d.workload, 0.5)
        self.assertEqual(d.members, ["agent-001", "agent-002"])
        self.assertEqual(d.active_projects, ["proj-001"])
        self.assertEqual(d.active_tasks, ["task-001", "task-002"])
        self.assertIsInstance(d.created_at, datetime)
        self.assertIsInstance(d.id, str)

    def test_is_mutable(self) -> None:
        self.dept.status = DepartmentStatus.WORKING
        self.assertEqual(self.dept.status, DepartmentStatus.WORKING)
        self.dept.workload = 0.8
        self.assertAlmostEqual(self.dept.workload, 0.8)

    def test_director_can_be_none(self) -> None:
        dept = _make_department(director=None)
        self.assertIsNone(dept.director)

    def test_director_can_be_assigned_after_creation(self) -> None:
        dept = _make_department(director=None)
        dept.director = self.director
        self.assertIsNotNone(dept.director)

    def test_utilization_method_returns_percentage(self) -> None:
        dept = _make_department(workload=0.75)
        self.assertAlmostEqual(dept.utilization(), 75.0, places=2)

    def test_utilization_zero_when_idle(self) -> None:
        dept = _make_department(workload=0.0)
        self.assertAlmostEqual(dept.utilization(), 0.0)

    def test_utilization_hundred_when_full(self) -> None:
        dept = _make_department(workload=1.0)
        self.assertAlmostEqual(dept.utilization(), 100.0)

    def test_free_capacity_returns_correct_value(self) -> None:
        dept = _make_department(capacity=10, workload=0.5)
        self.assertEqual(dept.free_capacity(), 5)

    def test_free_capacity_zero_when_full(self) -> None:
        dept = _make_department(capacity=10, workload=1.0)
        self.assertEqual(dept.free_capacity(), 0)

    def test_free_capacity_non_negative_when_overloaded(self) -> None:
        dept = _make_department(capacity=10, workload=1.0)
        self.assertGreaterEqual(dept.free_capacity(), 0)

    def test_is_available_true_when_ready_with_capacity(self) -> None:
        dept = _make_department(status=DepartmentStatus.READY, workload=0.0, capacity=10)
        self.assertTrue(dept.is_available())

    def test_is_available_true_when_working_with_capacity(self) -> None:
        dept = _make_department(status=DepartmentStatus.WORKING, workload=0.5, capacity=10)
        self.assertTrue(dept.is_available())

    def test_is_available_false_when_blocked(self) -> None:
        dept = _make_department(status=DepartmentStatus.BLOCKED, workload=0.0, capacity=10)
        self.assertFalse(dept.is_available())

    def test_is_available_false_when_overloaded(self) -> None:
        dept = _make_department(status=DepartmentStatus.OVERLOADED, workload=1.0, capacity=10)
        self.assertFalse(dept.is_available())

    def test_is_available_false_when_offline(self) -> None:
        dept = _make_department(status=DepartmentStatus.OFFLINE, workload=0.0, capacity=10)
        self.assertFalse(dept.is_available())

    def test_is_available_false_when_no_capacity(self) -> None:
        dept = _make_department(status=DepartmentStatus.WORKING, workload=1.0, capacity=10)
        self.assertFalse(dept.is_available())

    def test_has_director_true_when_director_set(self) -> None:
        self.assertTrue(self.dept.has_director())

    def test_has_director_false_when_none(self) -> None:
        dept = _make_department(director=None)
        self.assertFalse(dept.has_director())

    def test_members_is_list(self) -> None:
        self.assertIsInstance(self.dept.members, list)

    def test_active_projects_is_list(self) -> None:
        self.assertIsInstance(self.dept.active_projects, list)

    def test_active_tasks_is_list(self) -> None:
        self.assertIsInstance(self.dept.active_tasks, list)

    def test_exception_hierarchy(self) -> None:
        self.assertTrue(issubclass(InvalidWorkloadError, DepartmentError))
        self.assertTrue(issubclass(InvalidCapacityError, DepartmentError))
        self.assertTrue(issubclass(MemberNotFoundError, DepartmentError))


# ---------------------------------------------------------------------------
# TestDepartmentHealth
# ---------------------------------------------------------------------------

class TestDepartmentHealth(unittest.TestCase):

    def test_compute_health_returns_department_health(self) -> None:
        dept = _make_department()
        health = dept.compute_health()
        self.assertIsInstance(health, DepartmentHealth)

    def test_health_is_frozen(self) -> None:
        dept = _make_department()
        health = dept.compute_health()
        with self.assertRaises(Exception):
            health.overall_health = "MODIFIED"  # type: ignore[misc]

    def test_idle_healthy_department_grades_ok(self) -> None:
        director = _make_director()
        dept = _make_department(
            status=DepartmentStatus.READY,
            workload=0.0,
            director=director,
        )
        health = dept.compute_health()
        self.assertEqual(health.overall_health, "OK")

    def test_elevated_workload_grades_warning(self) -> None:
        director = _make_director()
        dept = _make_department(
            status=DepartmentStatus.WORKING,
            workload=0.75,
            director=director,
        )
        health = dept.compute_health()
        self.assertEqual(health.overall_health, "WARNING")

    def test_critical_workload_grades_critical(self) -> None:
        director = _make_director()
        dept = _make_department(
            status=DepartmentStatus.WORKING,
            workload=0.95,
            director=director,
        )
        health = dept.compute_health()
        self.assertEqual(health.overall_health, "CRITICAL")

    def test_blocked_status_grades_critical(self) -> None:
        director = _make_director()
        dept = _make_department(status=DepartmentStatus.BLOCKED, director=director)
        health = dept.compute_health()
        self.assertEqual(health.overall_health, "CRITICAL")

    def test_overloaded_status_grades_critical(self) -> None:
        director = _make_director()
        dept = _make_department(status=DepartmentStatus.OVERLOADED, workload=1.0, director=director)
        health = dept.compute_health()
        self.assertEqual(health.overall_health, "CRITICAL")

    def test_offline_status_grades_critical(self) -> None:
        dept = _make_department(status=DepartmentStatus.OFFLINE)
        health = dept.compute_health()
        self.assertEqual(health.overall_health, "CRITICAL")

    def test_waiting_status_grades_warning(self) -> None:
        director = _make_director()
        dept = _make_department(status=DepartmentStatus.WAITING, workload=0.3, director=director)
        health = dept.compute_health()
        self.assertEqual(health.overall_health, "WARNING")

    def test_no_director_adds_bottleneck(self) -> None:
        dept = _make_department(director=None)
        health = dept.compute_health()
        self.assertTrue(len(health.bottlenecks) > 0)
        self.assertTrue(any("director" in b.lower() for b in health.bottlenecks))

    def test_healthy_department_has_no_bottlenecks(self) -> None:
        director = _make_director()
        dept = _make_department(
            status=DepartmentStatus.READY,
            workload=0.3,
            director=director,
            active_projects=["proj-001"],
        )
        health = dept.compute_health()
        self.assertEqual(health.bottlenecks, [])

    def test_blocked_status_adds_bottleneck(self) -> None:
        dept = _make_department(status=DepartmentStatus.BLOCKED)
        health = dept.compute_health()
        self.assertTrue(any("blocked" in b.lower() for b in health.bottlenecks))

    def test_overloaded_status_adds_bottleneck(self) -> None:
        dept = _make_department(status=DepartmentStatus.OVERLOADED, workload=1.0)
        health = dept.compute_health()
        self.assertTrue(any("overloaded" in b.lower() for b in health.bottlenecks))

    def test_utilization_field_is_percentage(self) -> None:
        dept = _make_department(workload=0.6)
        health = dept.compute_health()
        self.assertAlmostEqual(health.utilization, 60.0, places=1)

    def test_active_projects_field_is_count(self) -> None:
        dept = _make_department(active_projects=["p1", "p2", "p3"])
        health = dept.compute_health()
        self.assertEqual(health.active_projects, 3)

    def test_active_tasks_field_is_count(self) -> None:
        dept = _make_department(active_tasks=["t1", "t2"])
        health = dept.compute_health()
        self.assertEqual(health.active_tasks, 2)

    def test_free_capacity_in_health_is_non_negative(self) -> None:
        dept = _make_department(capacity=10, workload=1.0)
        health = dept.compute_health()
        self.assertGreaterEqual(health.free_capacity, 0)

    def test_member_count_in_health_correct(self) -> None:
        dept = _make_department(members=["a1", "a2", "a3"])
        health = dept.compute_health()
        self.assertEqual(health.member_count, 3)

    def test_has_director_in_health_true(self) -> None:
        director = _make_director()
        dept = _make_department(director=director)
        health = dept.compute_health()
        self.assertTrue(health.has_director)

    def test_has_director_in_health_false(self) -> None:
        dept = _make_department(director=None)
        health = dept.compute_health()
        self.assertFalse(health.has_director)


# ---------------------------------------------------------------------------
# TestRegistryRegistration
# ---------------------------------------------------------------------------

class TestRegistryRegistration(unittest.TestCase):

    def test_register_returns_department(self) -> None:
        reg = DepartmentRegistry()
        dept = _make_department()
        result = reg.register(dept)
        self.assertIs(result, dept)

    def test_count_increases_after_register(self) -> None:
        reg = DepartmentRegistry()
        self.assertEqual(reg.count(), 0)
        reg.register(_make_department(dept_type=DepartmentType.BACKEND))
        self.assertEqual(reg.count(), 1)
        reg.register(_make_department(dept_type=DepartmentType.FRONTEND, name="Frontend"))
        self.assertEqual(reg.count(), 2)

    def test_duplicate_type_raises_error(self) -> None:
        reg = DepartmentRegistry()
        reg.register(_make_department(dept_type=DepartmentType.BACKEND))
        with self.assertRaises(DepartmentAlreadyRegisteredError):
            reg.register(_make_department(dept_type=DepartmentType.BACKEND))

    def test_all_thirteen_types_can_be_registered(self) -> None:
        reg = DepartmentRegistry()
        for i, dt in enumerate(DepartmentType):
            dept = _make_department(dept_type=dt, name=f"{dt.value} Department")
            reg.register(dept)
        self.assertEqual(reg.count(), 13)

    def test_remove_returns_department(self) -> None:
        reg, dept = _registry_with_dept()
        removed = reg.remove(dept.id)
        self.assertIs(removed, dept)

    def test_remove_decrements_count(self) -> None:
        reg, dept = _registry_with_dept()
        reg.remove(dept.id)
        self.assertEqual(reg.count(), 0)

    def test_remove_allows_reregistration_of_same_type(self) -> None:
        reg, dept = _registry_with_dept(dept_type=DepartmentType.BACKEND)
        reg.remove(dept.id)
        new_dept = _make_department(dept_type=DepartmentType.BACKEND)
        reg.register(new_dept)
        self.assertEqual(reg.count(), 1)

    def test_remove_unknown_raises_error(self) -> None:
        reg = DepartmentRegistry()
        with self.assertRaises(DepartmentNotFoundError):
            reg.remove("non-existent-id")

    def test_is_registered_true_after_register(self) -> None:
        reg, dept = _registry_with_dept(dept_type=DepartmentType.QA)
        self.assertTrue(reg.is_registered(DepartmentType.QA))

    def test_is_registered_false_before_register(self) -> None:
        reg = DepartmentRegistry()
        self.assertFalse(reg.is_registered(DepartmentType.QA))

    def test_is_registered_false_after_remove(self) -> None:
        reg, dept = _registry_with_dept(dept_type=DepartmentType.QA)
        reg.remove(dept.id)
        self.assertFalse(reg.is_registered(DepartmentType.QA))

    def test_empty_registry_has_zero_count(self) -> None:
        reg = DepartmentRegistry()
        self.assertEqual(reg.count(), 0)


# ---------------------------------------------------------------------------
# TestRegistryLookup
# ---------------------------------------------------------------------------

class TestRegistryLookup(unittest.TestCase):

    def test_get_returns_correct_department(self) -> None:
        reg, dept = _registry_with_dept()
        fetched = reg.get(dept.id)
        self.assertIs(fetched, dept)

    def test_get_unknown_raises_error(self) -> None:
        reg = DepartmentRegistry()
        with self.assertRaises(DepartmentNotFoundError):
            reg.get("no-such-id")

    def test_find_by_type_returns_correct_department(self) -> None:
        reg, dept = _registry_with_dept(dept_type=DepartmentType.QA, name="QA Department")
        found = reg.find_by_type(DepartmentType.QA)
        self.assertIs(found, dept)

    def test_find_by_type_raises_when_not_registered(self) -> None:
        reg = DepartmentRegistry()
        with self.assertRaises(DepartmentNotFoundError):
            reg.find_by_type(DepartmentType.SECURITY)

    def test_list_all_empty_when_no_departments(self) -> None:
        reg = DepartmentRegistry()
        self.assertEqual(reg.list_all(), [])

    def test_list_all_returns_all_departments(self) -> None:
        reg = DepartmentRegistry()
        d1 = _make_department(dept_type=DepartmentType.BACKEND, name="Backend")
        d2 = _make_department(dept_type=DepartmentType.FRONTEND, name="Frontend")
        reg.register(d1)
        reg.register(d2)
        result = reg.list_all()
        self.assertIn(d1, result)
        self.assertIn(d2, result)
        self.assertEqual(len(result), 2)

    def test_list_all_returns_copy(self) -> None:
        reg, dept = _registry_with_dept()
        lst = reg.list_all()
        lst.clear()
        self.assertEqual(reg.count(), 1)

    def test_list_all_preserves_registration_order(self) -> None:
        reg = DepartmentRegistry()
        d1 = _make_department(dept_type=DepartmentType.BACKEND, name="Backend")
        d2 = _make_department(dept_type=DepartmentType.FRONTEND, name="Frontend")
        d3 = _make_department(dept_type=DepartmentType.QA, name="QA")
        reg.register(d1)
        reg.register(d2)
        reg.register(d3)
        result = reg.list_all()
        self.assertEqual(result[0], d1)
        self.assertEqual(result[1], d2)
        self.assertEqual(result[2], d3)


# ---------------------------------------------------------------------------
# TestRegistryWorkloadAndCapacity
# ---------------------------------------------------------------------------

class TestRegistryWorkloadAndCapacity(unittest.TestCase):

    def test_update_workload_changes_value(self) -> None:
        reg, dept = _registry_with_dept(workload=0.0)
        reg.update_workload(dept.id, 0.5)
        self.assertAlmostEqual(dept.workload, 0.5)

    def test_update_workload_returns_department(self) -> None:
        reg, dept = _registry_with_dept()
        result = reg.update_workload(dept.id, 0.3)
        self.assertIs(result, dept)

    def test_update_workload_negative_raises(self) -> None:
        reg, dept = _registry_with_dept()
        with self.assertRaises(InvalidWorkloadError):
            reg.update_workload(dept.id, -0.1)

    def test_update_workload_above_one_raises(self) -> None:
        reg, dept = _registry_with_dept()
        with self.assertRaises(InvalidWorkloadError):
            reg.update_workload(dept.id, 1.01)

    def test_update_workload_zero_sets_ready_status(self) -> None:
        reg, dept = _registry_with_dept(status=DepartmentStatus.WORKING, workload=0.5)
        reg.update_workload(dept.id, 0.0)
        self.assertEqual(dept.status, DepartmentStatus.READY)

    def test_update_workload_mid_sets_working_status(self) -> None:
        reg, dept = _registry_with_dept(status=DepartmentStatus.READY, workload=0.0)
        reg.update_workload(dept.id, 0.5)
        self.assertEqual(dept.status, DepartmentStatus.WORKING)

    def test_update_workload_high_sets_overloaded_status(self) -> None:
        reg, dept = _registry_with_dept(status=DepartmentStatus.WORKING, workload=0.5)
        reg.update_workload(dept.id, 0.95)
        self.assertEqual(dept.status, DepartmentStatus.OVERLOADED)

    def test_update_workload_does_not_clear_blocked_status(self) -> None:
        reg, dept = _registry_with_dept(status=DepartmentStatus.BLOCKED, workload=0.5)
        reg.update_workload(dept.id, 0.1)
        self.assertEqual(dept.status, DepartmentStatus.BLOCKED)

    def test_update_workload_does_not_clear_offline_status(self) -> None:
        reg, dept = _registry_with_dept(status=DepartmentStatus.OFFLINE, workload=0.0)
        reg.update_workload(dept.id, 0.3)
        self.assertEqual(dept.status, DepartmentStatus.OFFLINE)

    def test_update_workload_one_exactly_allowed(self) -> None:
        reg, dept = _registry_with_dept(status=DepartmentStatus.WORKING)
        reg.update_workload(dept.id, 1.0)
        self.assertAlmostEqual(dept.workload, 1.0)

    def test_update_workload_unknown_raises(self) -> None:
        reg = DepartmentRegistry()
        with self.assertRaises(DepartmentNotFoundError):
            reg.update_workload("no-id", 0.5)

    def test_update_capacity_changes_value(self) -> None:
        reg, dept = _registry_with_dept(capacity=5)
        reg.update_capacity(dept.id, 20)
        self.assertEqual(dept.capacity, 20)

    def test_update_capacity_returns_department(self) -> None:
        reg, dept = _registry_with_dept()
        result = reg.update_capacity(dept.id, 15)
        self.assertIs(result, dept)

    def test_update_capacity_zero_raises(self) -> None:
        reg, dept = _registry_with_dept()
        with self.assertRaises(InvalidCapacityError):
            reg.update_capacity(dept.id, 0)

    def test_update_capacity_negative_raises(self) -> None:
        reg, dept = _registry_with_dept()
        with self.assertRaises(InvalidCapacityError):
            reg.update_capacity(dept.id, -1)

    def test_update_capacity_one_is_valid(self) -> None:
        reg, dept = _registry_with_dept()
        reg.update_capacity(dept.id, 1)
        self.assertEqual(dept.capacity, 1)

    def test_update_capacity_unknown_raises(self) -> None:
        reg = DepartmentRegistry()
        with self.assertRaises(DepartmentNotFoundError):
            reg.update_capacity("no-id", 10)


# ---------------------------------------------------------------------------
# TestRegistryStatusAndDirector
# ---------------------------------------------------------------------------

class TestRegistryStatusAndDirector(unittest.TestCase):

    def test_update_status_changes_status(self) -> None:
        reg, dept = _registry_with_dept(status=DepartmentStatus.READY)
        reg.update_status(dept.id, DepartmentStatus.BLOCKED)
        self.assertEqual(dept.status, DepartmentStatus.BLOCKED)

    def test_update_status_returns_department(self) -> None:
        reg, dept = _registry_with_dept()
        result = reg.update_status(dept.id, DepartmentStatus.WAITING)
        self.assertIs(result, dept)

    def test_update_status_unknown_raises(self) -> None:
        reg = DepartmentRegistry()
        with self.assertRaises(DepartmentNotFoundError):
            reg.update_status("no-id", DepartmentStatus.BLOCKED)

    def test_assign_director_sets_director(self) -> None:
        reg, dept = _registry_with_dept(director=None)
        director = _make_director()
        reg.assign_director(dept.id, director)
        self.assertIs(dept.director, director)

    def test_assign_director_transitions_offline_to_ready(self) -> None:
        reg, dept = _registry_with_dept(director=None, status=DepartmentStatus.OFFLINE)
        director = _make_director()
        reg.assign_director(dept.id, director)
        self.assertEqual(dept.status, DepartmentStatus.READY)

    def test_assign_director_does_not_change_non_offline_status(self) -> None:
        reg, dept = _registry_with_dept(director=None, status=DepartmentStatus.BLOCKED)
        director = _make_director()
        reg.assign_director(dept.id, director)
        self.assertEqual(dept.status, DepartmentStatus.BLOCKED)

    def test_assign_director_replaces_existing(self) -> None:
        old_director = _make_director(name="Old Director")
        reg, dept = _registry_with_dept(director=old_director)
        new_director = _make_director(name="New Director")
        reg.assign_director(dept.id, new_director)
        self.assertEqual(dept.director.name, "New Director")

    def test_assign_director_unknown_raises(self) -> None:
        reg = DepartmentRegistry()
        with self.assertRaises(DepartmentNotFoundError):
            reg.assign_director("no-id", _make_director())


# ---------------------------------------------------------------------------
# TestRegistryMembersAndProjects
# ---------------------------------------------------------------------------

class TestRegistryMembersAndProjects(unittest.TestCase):

    def test_add_member_appends(self) -> None:
        reg, dept = _registry_with_dept()
        reg.add_member(dept.id, "agent-001")
        self.assertIn("agent-001", dept.members)

    def test_add_member_idempotent(self) -> None:
        reg, dept = _registry_with_dept()
        reg.add_member(dept.id, "agent-001")
        reg.add_member(dept.id, "agent-001")
        self.assertEqual(dept.members.count("agent-001"), 1)

    def test_add_member_returns_department(self) -> None:
        reg, dept = _registry_with_dept()
        result = reg.add_member(dept.id, "agent-001")
        self.assertIs(result, dept)

    def test_add_member_unknown_dept_raises(self) -> None:
        reg = DepartmentRegistry()
        with self.assertRaises(DepartmentNotFoundError):
            reg.add_member("no-id", "agent-001")

    def test_remove_member_removes(self) -> None:
        reg, dept = _registry_with_dept(members=["agent-001"])
        reg.remove_member(dept.id, "agent-001")
        self.assertNotIn("agent-001", dept.members)

    def test_remove_member_not_found_raises(self) -> None:
        reg, dept = _registry_with_dept()
        with self.assertRaises(MemberNotFoundError):
            reg.remove_member(dept.id, "ghost-agent")

    def test_remove_member_unknown_dept_raises(self) -> None:
        reg = DepartmentRegistry()
        with self.assertRaises(DepartmentNotFoundError):
            reg.remove_member("no-id", "agent-001")

    def test_add_active_project_appends(self) -> None:
        reg, dept = _registry_with_dept()
        reg.add_active_project(dept.id, "proj-001")
        self.assertIn("proj-001", dept.active_projects)

    def test_add_active_project_idempotent(self) -> None:
        reg, dept = _registry_with_dept()
        reg.add_active_project(dept.id, "proj-001")
        reg.add_active_project(dept.id, "proj-001")
        self.assertEqual(dept.active_projects.count("proj-001"), 1)

    def test_remove_active_project_removes(self) -> None:
        reg, dept = _registry_with_dept(active_projects=["proj-001"])
        reg.remove_active_project(dept.id, "proj-001")
        self.assertNotIn("proj-001", dept.active_projects)

    def test_remove_active_project_idempotent_when_not_found(self) -> None:
        reg, dept = _registry_with_dept()
        reg.remove_active_project(dept.id, "proj-999")  # should not raise
        self.assertEqual(dept.active_projects, [])

    def test_add_active_task_appends(self) -> None:
        reg, dept = _registry_with_dept()
        reg.add_active_task(dept.id, "task-001")
        self.assertIn("task-001", dept.active_tasks)

    def test_add_active_task_idempotent(self) -> None:
        reg, dept = _registry_with_dept()
        reg.add_active_task(dept.id, "task-001")
        reg.add_active_task(dept.id, "task-001")
        self.assertEqual(dept.active_tasks.count("task-001"), 1)

    def test_remove_active_task_removes(self) -> None:
        reg, dept = _registry_with_dept(active_tasks=["task-001"])
        reg.remove_active_task(dept.id, "task-001")
        self.assertNotIn("task-001", dept.active_tasks)

    def test_remove_active_task_idempotent_when_not_found(self) -> None:
        reg, dept = _registry_with_dept()
        reg.remove_active_task(dept.id, "task-999")  # should not raise
        self.assertEqual(dept.active_tasks, [])


# ---------------------------------------------------------------------------
# TestRegistryHealthReport
# ---------------------------------------------------------------------------

class TestRegistryHealthReport(unittest.TestCase):

    def test_health_report_empty_registry(self) -> None:
        reg = DepartmentRegistry()
        report = reg.health_report()
        self.assertEqual(report["total_departments"], 0)
        self.assertEqual(report["healthy"], 0)
        self.assertEqual(report["warning"], 0)
        self.assertEqual(report["critical"], 0)
        self.assertEqual(report["departments"], [])

    def test_health_report_has_required_keys(self) -> None:
        reg, dept = _registry_with_dept()
        report = reg.health_report()
        for key in ("total_departments", "healthy", "warning", "critical", "departments"):
            self.assertIn(key, report)

    def test_health_report_counts_sum_to_total(self) -> None:
        reg = DepartmentRegistry()
        for dt in DepartmentType:
            reg.register(_make_department(dept_type=dt, name=f"{dt.value} Department"))
        report = reg.health_report()
        self.assertEqual(
            report["healthy"] + report["warning"] + report["critical"],
            report["total_departments"],
        )

    def test_health_report_per_dept_has_required_fields(self) -> None:
        director = _make_director()
        reg, dept = _registry_with_dept(director=director)
        report = reg.health_report()
        entry = report["departments"][0]
        for key in (
            "department_id", "department_name", "department_type", "status",
            "utilization", "active_projects", "active_tasks", "capacity",
            "free_capacity", "member_count", "has_director", "bottlenecks",
            "overall_health",
        ):
            self.assertIn(key, entry)

    def test_health_report_blocked_dept_counted_as_critical(self) -> None:
        reg, dept = _registry_with_dept(status=DepartmentStatus.BLOCKED)
        report = reg.health_report()
        self.assertEqual(report["critical"], 1)
        self.assertEqual(report["healthy"], 0)

    def test_health_report_idle_dept_counted_as_healthy(self) -> None:
        director = _make_director()
        reg, dept = _registry_with_dept(
            status=DepartmentStatus.READY, workload=0.0, director=director
        )
        report = reg.health_report()
        self.assertEqual(report["healthy"], 1)
        self.assertEqual(report["critical"], 0)

    def test_health_report_bottlenecks_is_list(self) -> None:
        reg, dept = _registry_with_dept()
        report = reg.health_report()
        self.assertIsInstance(report["departments"][0]["bottlenecks"], list)

    def test_health_report_overall_health_is_valid_grade(self) -> None:
        reg, dept = _registry_with_dept()
        report = reg.health_report()
        for entry in report["departments"]:
            self.assertIn(entry["overall_health"], ("OK", "WARNING", "CRITICAL"))


# ---------------------------------------------------------------------------
# TestRegistryStatistics
# ---------------------------------------------------------------------------

class TestRegistryStatistics(unittest.TestCase):

    def test_statistics_empty_registry(self) -> None:
        reg = DepartmentRegistry()
        stats = reg.statistics()
        self.assertEqual(stats["total_departments"], 0)
        self.assertEqual(stats["total_capacity"], 0)
        self.assertAlmostEqual(stats["average_workload"], 0.0)
        self.assertEqual(stats["registered_types"], [])

    def test_statistics_has_required_keys(self) -> None:
        reg = DepartmentRegistry()
        stats = reg.statistics()
        for key in (
            "total_departments", "total_capacity", "total_members",
            "total_active_projects", "total_active_tasks", "average_workload",
            "overloaded_departments", "offline_departments",
            "departments_by_status", "registered_types",
        ):
            self.assertIn(key, stats)

    def test_statistics_counts_correct_members(self) -> None:
        reg, dept = _registry_with_dept(members=["a1", "a2", "a3"])
        stats = reg.statistics()
        self.assertEqual(stats["total_members"], 3)

    def test_statistics_counts_total_capacity(self) -> None:
        reg = DepartmentRegistry()
        reg.register(_make_department(dept_type=DepartmentType.BACKEND, capacity=5))
        reg.register(_make_department(dept_type=DepartmentType.FRONTEND, name="Frontend", capacity=8))
        stats = reg.statistics()
        self.assertEqual(stats["total_capacity"], 13)

    def test_statistics_average_workload_correct(self) -> None:
        reg = DepartmentRegistry()
        reg.register(_make_department(dept_type=DepartmentType.BACKEND, workload=0.4))
        reg.register(_make_department(dept_type=DepartmentType.FRONTEND, name="Frontend", workload=0.6))
        stats = reg.statistics()
        self.assertAlmostEqual(stats["average_workload"], 0.5, places=4)

    def test_statistics_overloaded_count_correct(self) -> None:
        reg = DepartmentRegistry()
        reg.register(_make_department(
            dept_type=DepartmentType.BACKEND, status=DepartmentStatus.OVERLOADED
        ))
        reg.register(_make_department(
            dept_type=DepartmentType.FRONTEND, name="Frontend", status=DepartmentStatus.READY
        ))
        stats = reg.statistics()
        self.assertEqual(stats["overloaded_departments"], 1)

    def test_statistics_offline_count_correct(self) -> None:
        reg = DepartmentRegistry()
        reg.register(_make_department(
            dept_type=DepartmentType.BACKEND, status=DepartmentStatus.OFFLINE
        ))
        stats = reg.statistics()
        self.assertEqual(stats["offline_departments"], 1)

    def test_statistics_departments_by_status_covers_all_statuses(self) -> None:
        reg = DepartmentRegistry()
        stats = reg.statistics()
        for status in DepartmentStatus:
            self.assertIn(status.value, stats["departments_by_status"])

    def test_statistics_registered_types_lists_types(self) -> None:
        reg = DepartmentRegistry()
        reg.register(_make_department(dept_type=DepartmentType.QA, name="QA"))
        reg.register(_make_department(dept_type=DepartmentType.DEVOPS, name="DevOps"))
        stats = reg.statistics()
        self.assertIn("QA", stats["registered_types"])
        self.assertIn("DevOps", stats["registered_types"])

    def test_statistics_total_active_projects(self) -> None:
        reg = DepartmentRegistry()
        reg.register(_make_department(
            dept_type=DepartmentType.BACKEND, active_projects=["p1", "p2"]
        ))
        reg.register(_make_department(
            dept_type=DepartmentType.FRONTEND, name="Frontend", active_projects=["p3"]
        ))
        stats = reg.statistics()
        self.assertEqual(stats["total_active_projects"], 3)

    def test_statistics_total_active_tasks(self) -> None:
        reg = DepartmentRegistry()
        reg.register(_make_department(
            dept_type=DepartmentType.BACKEND, active_tasks=["t1", "t2", "t3"]
        ))
        stats = reg.statistics()
        self.assertEqual(stats["total_active_tasks"], 3)


# ---------------------------------------------------------------------------
# TestIntegrationScenarios
# ---------------------------------------------------------------------------

class TestIntegrationScenarios(unittest.TestCase):

    def _build_company(self) -> DepartmentRegistry:
        """Build a representative company structure for integration tests."""
        reg = DepartmentRegistry()

        # Engineering department — active and healthy
        backend_director = _make_director(
            department=DepartmentType.BACKEND,
            name="Backend Director",
            status=DirectorStatus.ACTIVE,
            responsibilities=["REST API development", "Database integration", "Code review"],
            managed_agents=["agent-be-001", "agent-be-002", "agent-be-003"],
        )
        backend = _make_department(
            dept_type=DepartmentType.BACKEND,
            name="Backend Department",
            status=DepartmentStatus.WORKING,
            capacity=10,
            workload=0.6,
            director=backend_director,
            members=["agent-be-001", "agent-be-002", "agent-be-003"],
            active_projects=["proj-alpha"],
            active_tasks=["task-001", "task-002"],
        )
        reg.register(backend)

        # QA department — light load
        qa_director = _make_director(
            department=DepartmentType.QA,
            name="QA Director",
            status=DirectorStatus.IDLE,
            responsibilities=["Test planning", "Quality assurance", "Bug triage"],
            managed_agents=["agent-qa-001"],
        )
        qa = _make_department(
            dept_type=DepartmentType.QA,
            name="QA Department",
            status=DepartmentStatus.READY,
            capacity=5,
            workload=0.2,
            director=qa_director,
            members=["agent-qa-001"],
        )
        reg.register(qa)

        # Security department — blocked on dependency
        security_director = _make_director(
            department=DepartmentType.SECURITY,
            name="Security Director",
            status=DirectorStatus.ACTIVE,
            responsibilities=["Security audits", "Vulnerability assessments"],
        )
        security = _make_department(
            dept_type=DepartmentType.SECURITY,
            name="Security Department",
            status=DepartmentStatus.BLOCKED,
            capacity=4,
            workload=0.3,
            director=security_director,
        )
        reg.register(security)

        return reg

    def test_company_has_correct_count(self) -> None:
        reg = self._build_company()
        self.assertEqual(reg.count(), 3)

    def test_find_each_department_by_type(self) -> None:
        reg = self._build_company()
        backend = reg.find_by_type(DepartmentType.BACKEND)
        qa = reg.find_by_type(DepartmentType.QA)
        security = reg.find_by_type(DepartmentType.SECURITY)
        self.assertEqual(backend.name, "Backend Department")
        self.assertEqual(qa.name, "QA Department")
        self.assertEqual(security.name, "Security Department")

    def test_health_report_reflects_mixed_health(self) -> None:
        reg = self._build_company()
        report = reg.health_report()
        self.assertEqual(report["total_departments"], 3)
        self.assertGreater(report["healthy"] + report["warning"] + report["critical"], 0)
        # Security is BLOCKED → CRITICAL
        self.assertGreaterEqual(report["critical"], 1)

    def test_statistics_total_members_accurate(self) -> None:
        reg = self._build_company()
        stats = reg.statistics()
        self.assertEqual(stats["total_members"], 4)  # 3 backend + 1 qa + 0 security

    def test_update_workload_propagates_to_statistics(self) -> None:
        reg = self._build_company()
        backend = reg.find_by_type(DepartmentType.BACKEND)
        reg.update_workload(backend.id, 0.95)
        stats = reg.statistics()
        self.assertGreaterEqual(stats["overloaded_departments"], 1)

    def test_add_and_remove_member_lifecycle(self) -> None:
        reg = self._build_company()
        backend = reg.find_by_type(DepartmentType.BACKEND)
        initial_count = len(backend.members)
        reg.add_member(backend.id, "agent-be-new")
        self.assertEqual(len(backend.members), initial_count + 1)
        reg.remove_member(backend.id, "agent-be-new")
        self.assertEqual(len(backend.members), initial_count)

    def test_director_agent_lifecycle(self) -> None:
        reg = self._build_company()
        backend = reg.find_by_type(DepartmentType.BACKEND)
        director = backend.director
        initial_count = director.agent_count()
        director.add_agent("agent-be-new")
        self.assertEqual(director.agent_count(), initial_count + 1)
        director.remove_agent("agent-be-new")
        self.assertEqual(director.agent_count(), initial_count)

    def test_resolve_block_transitions_to_working(self) -> None:
        reg = self._build_company()
        security = reg.find_by_type(DepartmentType.SECURITY)
        self.assertEqual(security.status, DepartmentStatus.BLOCKED)
        reg.update_status(security.id, DepartmentStatus.WORKING)
        self.assertEqual(security.status, DepartmentStatus.WORKING)

    def test_offline_dept_comes_online_with_director(self) -> None:
        reg = DepartmentRegistry()
        dept = _make_department(
            dept_type=DepartmentType.RESEARCH,
            name="Research Department",
            status=DepartmentStatus.OFFLINE,
            director=None,
        )
        reg.register(dept)
        self.assertFalse(dept.has_director())
        director = _make_director(department=DepartmentType.RESEARCH, name="Research Director")
        reg.assign_director(dept.id, director)
        self.assertTrue(dept.has_director())
        self.assertEqual(dept.status, DepartmentStatus.READY)

    def test_full_company_health_report_structure(self) -> None:
        reg = self._build_company()
        report = reg.health_report()
        for entry in report["departments"]:
            self.assertIsInstance(entry["department_id"], str)
            self.assertIsInstance(entry["department_name"], str)
            self.assertIsInstance(entry["utilization"], float)
            self.assertGreaterEqual(entry["utilization"], 0.0)
            self.assertLessEqual(entry["utilization"], 100.0)
            self.assertIsInstance(entry["bottlenecks"], list)
            self.assertIn(entry["overall_health"], ("OK", "WARNING", "CRITICAL"))


if __name__ == "__main__":
    unittest.main()
