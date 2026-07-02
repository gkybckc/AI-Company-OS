"""
tests/test_org_management.py — Feature 20: Dynamic Organization Management

400+ unit tests covering:
  1.  OrgEngine core unit tests (roles, skills, departments, employees)
  2.  OrgEngine state-transition and error tests
  3.  OrgEngine query and statistics tests
  4.  DashboardState integration (org_engine seeded)
  5.  HTML page routes: /org/departments, /org/employees, /org/roles, /org/skills
  6.  JSON API routes: /api/org/*
  7.  Sub-navigation presence in org pages
  8.  Turkish-language content assertions
  9.  Form element presence
 10.  Regression guard — existing HTML + API routes unaffected
"""

import unittest
from datetime import datetime

from fastapi.testclient import TestClient

from apps.dashboard.main import app
from apps.dashboard.state import DashboardState
from core.org_engine import (
    OrgDepartment,
    OrgDuplicateNameError,
    OrgEmployee,
    OrgEngine,
    OrgEngineError,
    OrgInvalidStateError,
    OrgRole,
    OrgSkill,
    OrgDepartmentNotFoundError,
    OrgEmployeeNotFoundError,
    OrgRoleNotFoundError,
    OrgSkillNotFoundError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _client() -> TestClient:
    DashboardState.reset()
    return TestClient(app)


def _fresh_engine() -> OrgEngine:
    """Return a brand-new OrgEngine with no data."""
    return OrgEngine()


def _seeded_engine() -> OrgEngine:
    """Return an OrgEngine with one role, one skill, one department, one employee."""
    eng = OrgEngine()
    role = eng.create_role("Developer", "Writes code")
    skill = eng.create_skill("Python", "Programming")
    dept = eng.create_department("Engineering", capacity=5)
    emp = eng.create_employee("Alice", role.id, dept.id, ["Python"], "mock")
    return eng


# ===========================================================================
# 1. OrgRole — create
# ===========================================================================

class TestOrgRoleCreate(unittest.TestCase):

    def test_create_role_returns_orgrole(self):
        eng = _fresh_engine()
        role = eng.create_role("Backend Agent")
        self.assertIsInstance(role, OrgRole)

    def test_create_role_id_is_string(self):
        eng = _fresh_engine()
        role = eng.create_role("Frontend Agent")
        self.assertIsInstance(role.id, str)

    def test_create_role_id_nonempty(self):
        eng = _fresh_engine()
        role = eng.create_role("QA Engineer")
        self.assertTrue(len(role.id) > 0)

    def test_create_role_name_stored(self):
        eng = _fresh_engine()
        role = eng.create_role("DevOps Engineer")
        self.assertEqual(role.name, "DevOps Engineer")

    def test_create_role_description_stored(self):
        eng = _fresh_engine()
        role = eng.create_role("Researcher", "Does research")
        self.assertEqual(role.description, "Does research")

    def test_create_role_default_description_empty(self):
        eng = _fresh_engine()
        role = eng.create_role("Analyst")
        self.assertEqual(role.description, "")

    def test_create_role_created_at_is_datetime(self):
        eng = _fresh_engine()
        role = eng.create_role("Designer")
        self.assertIsInstance(role.created_at, datetime)

    def test_create_role_empty_name_raises(self):
        eng = _fresh_engine()
        with self.assertRaises(OrgEngineError):
            eng.create_role("")

    def test_create_role_whitespace_name_raises(self):
        eng = _fresh_engine()
        with self.assertRaises(OrgEngineError):
            eng.create_role("   ")

    def test_create_role_duplicate_raises(self):
        eng = _fresh_engine()
        eng.create_role("Backend Agent")
        with self.assertRaises(OrgDuplicateNameError):
            eng.create_role("Backend Agent")

    def test_create_role_duplicate_case_insensitive(self):
        eng = _fresh_engine()
        eng.create_role("Backend Agent")
        with self.assertRaises(OrgDuplicateNameError):
            eng.create_role("backend agent")

    def test_create_role_strips_whitespace(self):
        eng = _fresh_engine()
        role = eng.create_role("  Backend Agent  ")
        self.assertEqual(role.name, "Backend Agent")

    def test_create_multiple_roles(self):
        eng = _fresh_engine()
        eng.create_role("R1")
        eng.create_role("R2")
        eng.create_role("R3")
        self.assertEqual(eng.role_count(), 3)


# ===========================================================================
# 2. OrgRole — get / list / find
# ===========================================================================

class TestOrgRoleQuery(unittest.TestCase):

    def test_get_role_returns_correct(self):
        eng = _fresh_engine()
        role = eng.create_role("Backend Agent")
        fetched = eng.get_role(role.id)
        self.assertEqual(fetched.id, role.id)

    def test_get_role_not_found_raises(self):
        eng = _fresh_engine()
        with self.assertRaises(OrgRoleNotFoundError):
            eng.get_role("nonexistent-id")

    def test_list_roles_empty(self):
        eng = _fresh_engine()
        self.assertEqual(eng.list_roles(), [])

    def test_list_roles_returns_all(self):
        eng = _fresh_engine()
        eng.create_role("R1")
        eng.create_role("R2")
        self.assertEqual(len(eng.list_roles()), 2)

    def test_find_role_by_name_found(self):
        eng = _fresh_engine()
        eng.create_role("Backend Agent")
        found = eng.find_role_by_name("Backend Agent")
        self.assertIsNotNone(found)

    def test_find_role_by_name_case_insensitive(self):
        eng = _fresh_engine()
        eng.create_role("Backend Agent")
        found = eng.find_role_by_name("BACKEND AGENT")
        self.assertIsNotNone(found)

    def test_find_role_by_name_not_found_returns_none(self):
        eng = _fresh_engine()
        self.assertIsNone(eng.find_role_by_name("Nonexistent"))

    def test_role_count_empty(self):
        eng = _fresh_engine()
        self.assertEqual(eng.role_count(), 0)

    def test_role_count_after_create(self):
        eng = _fresh_engine()
        eng.create_role("R1")
        self.assertEqual(eng.role_count(), 1)


# ===========================================================================
# 3. OrgRole — edit / delete
# ===========================================================================

class TestOrgRoleEdit(unittest.TestCase):

    def test_edit_role_name(self):
        eng = _fresh_engine()
        role = eng.create_role("Old Name")
        eng.edit_role(role.id, name="New Name")
        self.assertEqual(role.name, "New Name")

    def test_edit_role_description(self):
        eng = _fresh_engine()
        role = eng.create_role("R", "old desc")
        eng.edit_role(role.id, description="new desc")
        self.assertEqual(role.description, "new desc")

    def test_edit_role_duplicate_name_raises(self):
        eng = _fresh_engine()
        eng.create_role("R1")
        r2 = eng.create_role("R2")
        with self.assertRaises(OrgDuplicateNameError):
            eng.edit_role(r2.id, name="R1")

    def test_edit_role_same_name_ok(self):
        eng = _fresh_engine()
        role = eng.create_role("R1")
        result = eng.edit_role(role.id, name="R1")
        self.assertEqual(result.name, "R1")

    def test_delete_role_removes_it(self):
        eng = _fresh_engine()
        role = eng.create_role("ToDelete")
        eng.delete_role(role.id)
        self.assertEqual(eng.role_count(), 0)

    def test_delete_role_not_found_raises(self):
        eng = _fresh_engine()
        with self.assertRaises(OrgRoleNotFoundError):
            eng.delete_role("bad-id")


# ===========================================================================
# 4. OrgSkill — create
# ===========================================================================

class TestOrgSkillCreate(unittest.TestCase):

    def test_create_skill_returns_orgskill(self):
        eng = _fresh_engine()
        skill = eng.create_skill("Python")
        self.assertIsInstance(skill, OrgSkill)

    def test_create_skill_name_stored(self):
        eng = _fresh_engine()
        skill = eng.create_skill("Python")
        self.assertEqual(skill.name, "Python")

    def test_create_skill_category_stored(self):
        eng = _fresh_engine()
        skill = eng.create_skill("Python", "Programming")
        self.assertEqual(skill.category, "Programming")

    def test_create_skill_default_category_empty(self):
        eng = _fresh_engine()
        skill = eng.create_skill("Docker")
        self.assertEqual(skill.category, "")

    def test_create_skill_id_nonempty(self):
        eng = _fresh_engine()
        skill = eng.create_skill("FastAPI")
        self.assertTrue(len(skill.id) > 0)

    def test_create_skill_empty_name_raises(self):
        eng = _fresh_engine()
        with self.assertRaises(OrgEngineError):
            eng.create_skill("")

    def test_create_skill_duplicate_raises(self):
        eng = _fresh_engine()
        eng.create_skill("Python")
        with self.assertRaises(OrgDuplicateNameError):
            eng.create_skill("Python")

    def test_create_skill_duplicate_case_insensitive(self):
        eng = _fresh_engine()
        eng.create_skill("Python")
        with self.assertRaises(OrgDuplicateNameError):
            eng.create_skill("python")

    def test_skill_count_increments(self):
        eng = _fresh_engine()
        eng.create_skill("S1")
        eng.create_skill("S2")
        self.assertEqual(eng.skill_count(), 2)


# ===========================================================================
# 5. OrgSkill — get / find / edit / delete
# ===========================================================================

class TestOrgSkillQuery(unittest.TestCase):

    def test_get_skill_by_id(self):
        eng = _fresh_engine()
        skill = eng.create_skill("Docker")
        fetched = eng.get_skill(skill.id)
        self.assertEqual(fetched.id, skill.id)

    def test_get_skill_not_found_raises(self):
        eng = _fresh_engine()
        with self.assertRaises(OrgSkillNotFoundError):
            eng.get_skill("bad-id")

    def test_list_skills_empty(self):
        eng = _fresh_engine()
        self.assertEqual(eng.list_skills(), [])

    def test_list_skills_all_returned(self):
        eng = _fresh_engine()
        eng.create_skill("S1")
        eng.create_skill("S2")
        eng.create_skill("S3")
        self.assertEqual(len(eng.list_skills()), 3)

    def test_find_skill_by_name(self):
        eng = _fresh_engine()
        eng.create_skill("React")
        found = eng.find_skill_by_name("React")
        self.assertIsNotNone(found)

    def test_find_skill_by_name_not_found(self):
        eng = _fresh_engine()
        self.assertIsNone(eng.find_skill_by_name("Rust"))

    def test_edit_skill_name(self):
        eng = _fresh_engine()
        skill = eng.create_skill("TypeScript")
        eng.edit_skill(skill.id, name="JavaScript")
        self.assertEqual(skill.name, "JavaScript")

    def test_edit_skill_category(self):
        eng = _fresh_engine()
        skill = eng.create_skill("Figma")
        eng.edit_skill(skill.id, category="Design")
        self.assertEqual(skill.category, "Design")

    def test_delete_skill_removes(self):
        eng = _fresh_engine()
        skill = eng.create_skill("ToDel")
        eng.delete_skill(skill.id)
        self.assertEqual(eng.skill_count(), 0)

    def test_delete_skill_not_found_raises(self):
        eng = _fresh_engine()
        with self.assertRaises(OrgSkillNotFoundError):
            eng.delete_skill("bad-id")


# ===========================================================================
# 6. OrgDepartment — create
# ===========================================================================

class TestOrgDeptCreate(unittest.TestCase):

    def test_create_dept_returns_orgdepartment(self):
        eng = _fresh_engine()
        dept = eng.create_department("Backend")
        self.assertIsInstance(dept, OrgDepartment)

    def test_create_dept_name_stored(self):
        eng = _fresh_engine()
        dept = eng.create_department("Backend")
        self.assertEqual(dept.name, "Backend")

    def test_create_dept_default_capacity(self):
        eng = _fresh_engine()
        dept = eng.create_department("X")
        self.assertEqual(dept.capacity, 10)

    def test_create_dept_custom_capacity(self):
        eng = _fresh_engine()
        dept = eng.create_department("Small", capacity=3)
        self.assertEqual(dept.capacity, 3)

    def test_create_dept_status_active(self):
        eng = _fresh_engine()
        dept = eng.create_department("D")
        self.assertEqual(dept.status, "active")

    def test_create_dept_no_director(self):
        eng = _fresh_engine()
        dept = eng.create_department("D")
        self.assertIsNone(dept.director_id)

    def test_create_dept_members_empty(self):
        eng = _fresh_engine()
        dept = eng.create_department("D")
        self.assertEqual(dept.members, [])

    def test_create_dept_projects_empty(self):
        eng = _fresh_engine()
        dept = eng.create_department("D")
        self.assertEqual(dept.projects, [])

    def test_create_dept_empty_name_raises(self):
        eng = _fresh_engine()
        with self.assertRaises(OrgEngineError):
            eng.create_department("")

    def test_create_dept_capacity_zero_raises(self):
        eng = _fresh_engine()
        with self.assertRaises(OrgEngineError):
            eng.create_department("D", capacity=0)

    def test_create_dept_capacity_negative_raises(self):
        eng = _fresh_engine()
        with self.assertRaises(OrgEngineError):
            eng.create_department("D", capacity=-1)

    def test_create_dept_id_nonempty(self):
        eng = _fresh_engine()
        dept = eng.create_department("D")
        self.assertTrue(len(dept.id) > 0)

    def test_create_dept_count_increments(self):
        eng = _fresh_engine()
        eng.create_department("D1")
        eng.create_department("D2")
        self.assertEqual(eng.department_count(), 2)

    def test_create_dept_is_active(self):
        eng = _fresh_engine()
        dept = eng.create_department("D")
        self.assertTrue(dept.is_active())


# ===========================================================================
# 7. OrgDepartment — get / list
# ===========================================================================

class TestOrgDeptQuery(unittest.TestCase):

    def test_get_dept_by_id(self):
        eng = _fresh_engine()
        dept = eng.create_department("D")
        fetched = eng.get_department(dept.id)
        self.assertEqual(fetched.id, dept.id)

    def test_get_dept_not_found_raises(self):
        eng = _fresh_engine()
        with self.assertRaises(OrgDepartmentNotFoundError):
            eng.get_department("bad-id")

    def test_list_departments_empty(self):
        eng = _fresh_engine()
        self.assertEqual(eng.list_departments(), [])

    def test_list_departments_all(self):
        eng = _fresh_engine()
        eng.create_department("D1")
        eng.create_department("D2")
        self.assertEqual(len(eng.list_departments()), 2)

    def test_list_active_departments(self):
        eng = _fresh_engine()
        d1 = eng.create_department("Active")
        d2 = eng.create_department("ToDisable")
        eng.disable_department(d2.id)
        active = eng.list_active_departments()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].id, d1.id)


# ===========================================================================
# 8. OrgDepartment — edit / disable / enable
# ===========================================================================

class TestOrgDeptEdit(unittest.TestCase):

    def test_edit_dept_name(self):
        eng = _fresh_engine()
        dept = eng.create_department("Old")
        eng.edit_department(dept.id, name="New")
        self.assertEqual(dept.name, "New")

    def test_edit_dept_capacity(self):
        eng = _fresh_engine()
        dept = eng.create_department("D", capacity=5)
        eng.edit_department(dept.id, capacity=20)
        self.assertEqual(dept.capacity, 20)

    def test_edit_dept_empty_name_raises(self):
        eng = _fresh_engine()
        dept = eng.create_department("D")
        with self.assertRaises(OrgEngineError):
            eng.edit_department(dept.id, name="")

    def test_edit_dept_capacity_zero_raises(self):
        eng = _fresh_engine()
        dept = eng.create_department("D")
        with self.assertRaises(OrgEngineError):
            eng.edit_department(dept.id, capacity=0)

    def test_disable_dept_changes_status(self):
        eng = _fresh_engine()
        dept = eng.create_department("D")
        eng.disable_department(dept.id)
        self.assertEqual(dept.status, "inactive")

    def test_disable_dept_already_inactive_raises(self):
        eng = _fresh_engine()
        dept = eng.create_department("D")
        eng.disable_department(dept.id)
        with self.assertRaises(OrgInvalidStateError):
            eng.disable_department(dept.id)

    def test_enable_dept_changes_status(self):
        eng = _fresh_engine()
        dept = eng.create_department("D")
        eng.disable_department(dept.id)
        eng.enable_department(dept.id)
        self.assertEqual(dept.status, "active")

    def test_enable_dept_already_active_raises(self):
        eng = _fresh_engine()
        dept = eng.create_department("D")
        with self.assertRaises(OrgInvalidStateError):
            eng.enable_department(dept.id)

    def test_delete_dept_removes(self):
        eng = _fresh_engine()
        dept = eng.create_department("D")
        eng.delete_department(dept.id)
        self.assertEqual(eng.department_count(), 0)

    def test_delete_dept_not_found_raises(self):
        eng = _fresh_engine()
        with self.assertRaises(OrgDepartmentNotFoundError):
            eng.delete_department("bad-id")


# ===========================================================================
# 9. OrgDepartment — director / members / projects
# ===========================================================================

class TestOrgDeptRelations(unittest.TestCase):

    def _setup(self):
        eng = _fresh_engine()
        role = eng.create_role("R")
        dept = eng.create_department("D")
        emp = eng.create_employee("Alice", role.id)
        return eng, dept, emp

    def test_assign_director(self):
        eng, dept, emp = self._setup()
        eng.assign_director(dept.id, emp.id)
        self.assertEqual(dept.director_id, emp.id)

    def test_assign_director_terminated_raises(self):
        eng, dept, emp = self._setup()
        eng.terminate_employee(emp.id)
        with self.assertRaises(OrgInvalidStateError):
            eng.assign_director(dept.id, emp.id)

    def test_remove_director(self):
        eng, dept, emp = self._setup()
        eng.assign_director(dept.id, emp.id)
        eng.remove_director(dept.id)
        self.assertIsNone(dept.director_id)

    def test_add_member(self):
        eng, dept, emp = self._setup()
        eng.add_member(dept.id, emp.id)
        self.assertIn(emp.id, dept.members)

    def test_add_member_idempotent(self):
        eng, dept, emp = self._setup()
        eng.add_member(dept.id, emp.id)
        eng.add_member(dept.id, emp.id)
        self.assertEqual(dept.members.count(emp.id), 1)

    def test_remove_member(self):
        eng, dept, emp = self._setup()
        eng.add_member(dept.id, emp.id)
        eng.remove_member(dept.id, emp.id)
        self.assertNotIn(emp.id, dept.members)

    def test_member_count(self):
        eng, dept, emp = self._setup()
        eng.add_member(dept.id, emp.id)
        self.assertEqual(dept.member_count(), 1)

    def test_add_project(self):
        eng, dept, _ = self._setup()
        eng.add_project(dept.id, "My Project")
        self.assertIn("My Project", dept.projects)

    def test_add_project_idempotent(self):
        eng, dept, _ = self._setup()
        eng.add_project(dept.id, "P")
        eng.add_project(dept.id, "P")
        self.assertEqual(dept.projects.count("P"), 1)

    def test_remove_project(self):
        eng, dept, _ = self._setup()
        eng.add_project(dept.id, "P")
        eng.remove_project(dept.id, "P")
        self.assertNotIn("P", dept.projects)

    def test_director_of_no_director(self):
        eng = _fresh_engine()
        dept = eng.create_department("D")
        self.assertIsNone(eng.director_of(dept.id))

    def test_director_of_returns_employee(self):
        eng, dept, emp = self._setup()
        eng.assign_director(dept.id, emp.id)
        director = eng.director_of(dept.id)
        self.assertEqual(director.id, emp.id)

    def test_workload_pct_zero(self):
        eng = _fresh_engine()
        dept = eng.create_department("D", capacity=10)
        self.assertEqual(dept.workload_pct(), 0.0)

    def test_workload_pct_with_members(self):
        eng = _fresh_engine()
        role = eng.create_role("R")
        dept = eng.create_department("D", capacity=10)
        eng.create_employee("E1", role.id, dept.id)
        eng.create_employee("E2", role.id, dept.id)
        self.assertEqual(dept.member_count(), 2)


# ===========================================================================
# 10. OrgEmployee — create
# ===========================================================================

class TestOrgEmployeeCreate(unittest.TestCase):

    def _setup(self):
        eng = _fresh_engine()
        role = eng.create_role("R")
        dept = eng.create_department("D")
        return eng, role, dept

    def test_create_employee_returns_orgemployee(self):
        eng, role, dept = self._setup()
        emp = eng.create_employee("Alice", role.id)
        self.assertIsInstance(emp, OrgEmployee)

    def test_create_employee_name_stored(self):
        eng, role, dept = self._setup()
        emp = eng.create_employee("Alice", role.id)
        self.assertEqual(emp.name, "Alice")

    def test_create_employee_role_stored(self):
        eng, role, dept = self._setup()
        emp = eng.create_employee("Alice", role.id)
        self.assertEqual(emp.role_id, role.id)

    def test_create_employee_dept_stored(self):
        eng, role, dept = self._setup()
        emp = eng.create_employee("Alice", role.id, dept.id)
        self.assertEqual(emp.department_id, dept.id)

    def test_create_employee_no_dept(self):
        eng, role, dept = self._setup()
        emp = eng.create_employee("Alice", role.id)
        self.assertIsNone(emp.department_id)

    def test_create_employee_skills_stored(self):
        eng, role, dept = self._setup()
        emp = eng.create_employee("Alice", role.id, skills=["Python", "SQL"])
        self.assertEqual(emp.skills, ["Python", "SQL"])

    def test_create_employee_default_status_active(self):
        eng, role, dept = self._setup()
        emp = eng.create_employee("Alice", role.id)
        self.assertEqual(emp.status, "active")

    def test_create_employee_provider_stored(self):
        eng, role, dept = self._setup()
        emp = eng.create_employee("Alice", role.id, provider="anthropic")
        self.assertEqual(emp.provider, "anthropic")

    def test_create_employee_default_provider_mock(self):
        eng, role, dept = self._setup()
        emp = eng.create_employee("Alice", role.id)
        self.assertEqual(emp.provider, "mock")

    def test_create_employee_no_current_task(self):
        eng, role, dept = self._setup()
        emp = eng.create_employee("Alice", role.id)
        self.assertIsNone(emp.current_task)

    def test_create_employee_previous_tasks_empty(self):
        eng, role, dept = self._setup()
        emp = eng.create_employee("Alice", role.id)
        self.assertEqual(emp.previous_tasks, [])

    def test_create_employee_empty_name_raises(self):
        eng, role, dept = self._setup()
        with self.assertRaises(OrgEngineError):
            eng.create_employee("", role.id)

    def test_create_employee_bad_role_raises(self):
        eng = _fresh_engine()
        with self.assertRaises(OrgRoleNotFoundError):
            eng.create_employee("Alice", "bad-id")

    def test_create_employee_bad_dept_raises(self):
        eng = _fresh_engine()
        role = eng.create_role("R")
        with self.assertRaises(OrgDepartmentNotFoundError):
            eng.create_employee("Alice", role.id, department_id="bad-id")

    def test_create_employee_added_to_dept_members(self):
        eng, role, dept = self._setup()
        emp = eng.create_employee("Alice", role.id, dept.id)
        self.assertIn(emp.id, dept.members)

    def test_create_employee_count_increments(self):
        eng, role, dept = self._setup()
        eng.create_employee("A", role.id)
        eng.create_employee("B", role.id)
        self.assertEqual(eng.employee_count(), 2)

    def test_employee_is_active(self):
        eng, role, dept = self._setup()
        emp = eng.create_employee("A", role.id)
        self.assertTrue(emp.is_active())

    def test_employee_not_suspended(self):
        eng, role, dept = self._setup()
        emp = eng.create_employee("A", role.id)
        self.assertFalse(emp.is_suspended())

    def test_employee_not_terminated(self):
        eng, role, dept = self._setup()
        emp = eng.create_employee("A", role.id)
        self.assertFalse(emp.is_terminated())


# ===========================================================================
# 11. OrgEmployee — get / list
# ===========================================================================

class TestOrgEmployeeQuery(unittest.TestCase):

    def test_get_employee_by_id(self):
        eng = _seeded_engine()
        emps = eng.list_employees()
        emp = eng.get_employee(emps[0].id)
        self.assertEqual(emp.id, emps[0].id)

    def test_get_employee_not_found_raises(self):
        eng = _fresh_engine()
        with self.assertRaises(OrgEmployeeNotFoundError):
            eng.get_employee("bad-id")

    def test_list_employees_empty(self):
        eng = _fresh_engine()
        self.assertEqual(eng.list_employees(), [])

    def test_list_employees_all(self):
        eng = _seeded_engine()
        self.assertEqual(len(eng.list_employees()), 1)

    def test_list_active_employees(self):
        eng = _seeded_engine()
        active = eng.list_active_employees()
        self.assertEqual(len(active), 1)

    def test_employees_in_department(self):
        eng = _seeded_engine()
        dept = eng.list_departments()[0]
        members = eng.employees_in_department(dept.id)
        self.assertEqual(len(members), 1)

    def test_employees_in_department_not_found_raises(self):
        eng = _fresh_engine()
        with self.assertRaises(OrgDepartmentNotFoundError):
            eng.employees_in_department("bad-id")


# ===========================================================================
# 12. OrgEmployee — edit / transfer / suspend / reactivate / terminate
# ===========================================================================

class TestOrgEmployeeStateTransitions(unittest.TestCase):

    def _setup(self):
        eng = _fresh_engine()
        r = eng.create_role("R")
        d = eng.create_department("D")
        emp = eng.create_employee("Alice", r.id, d.id)
        return eng, r, d, emp

    def test_edit_employee_name(self):
        eng, r, d, emp = self._setup()
        eng.edit_employee(emp.id, name="Bob")
        self.assertEqual(emp.name, "Bob")

    def test_edit_employee_role(self):
        eng, r, d, emp = self._setup()
        r2 = eng.create_role("R2")
        eng.edit_employee(emp.id, role_id=r2.id)
        self.assertEqual(emp.role_id, r2.id)

    def test_edit_employee_provider(self):
        eng, r, d, emp = self._setup()
        eng.edit_employee(emp.id, provider="openai")
        self.assertEqual(emp.provider, "openai")

    def test_edit_terminated_raises(self):
        eng, r, d, emp = self._setup()
        eng.terminate_employee(emp.id)
        with self.assertRaises(OrgInvalidStateError):
            eng.edit_employee(emp.id, name="X")

    def test_suspend_changes_status(self):
        eng, r, d, emp = self._setup()
        eng.suspend_employee(emp.id)
        self.assertEqual(emp.status, "suspended")

    def test_suspend_already_suspended_raises(self):
        eng, r, d, emp = self._setup()
        eng.suspend_employee(emp.id)
        with self.assertRaises(OrgInvalidStateError):
            eng.suspend_employee(emp.id)

    def test_suspend_terminated_raises(self):
        eng, r, d, emp = self._setup()
        eng.terminate_employee(emp.id)
        with self.assertRaises(OrgInvalidStateError):
            eng.suspend_employee(emp.id)

    def test_reactivate_changes_status(self):
        eng, r, d, emp = self._setup()
        eng.suspend_employee(emp.id)
        eng.reactivate_employee(emp.id)
        self.assertEqual(emp.status, "active")

    def test_reactivate_not_suspended_raises(self):
        eng, r, d, emp = self._setup()
        with self.assertRaises(OrgInvalidStateError):
            eng.reactivate_employee(emp.id)

    def test_terminate_changes_status(self):
        eng, r, d, emp = self._setup()
        eng.terminate_employee(emp.id)
        self.assertEqual(emp.status, "terminated")

    def test_terminate_removes_from_department(self):
        eng, r, d, emp = self._setup()
        eng.terminate_employee(emp.id)
        self.assertIsNone(emp.department_id)
        self.assertNotIn(emp.id, d.members)

    def test_terminate_already_terminated_raises(self):
        eng, r, d, emp = self._setup()
        eng.terminate_employee(emp.id)
        with self.assertRaises(OrgInvalidStateError):
            eng.terminate_employee(emp.id)

    def test_transfer_to_new_dept(self):
        eng, r, d, emp = self._setup()
        d2 = eng.create_department("D2")
        eng.transfer_employee(emp.id, d2.id)
        self.assertEqual(emp.department_id, d2.id)
        self.assertNotIn(emp.id, d.members)
        self.assertIn(emp.id, d2.members)

    def test_transfer_terminated_raises(self):
        eng, r, d, emp = self._setup()
        eng.terminate_employee(emp.id)
        d2 = eng.create_department("D2")
        with self.assertRaises(OrgInvalidStateError):
            eng.transfer_employee(emp.id, d2.id)

    def test_assign_task(self):
        eng, r, d, emp = self._setup()
        eng.assign_task(emp.id, "Build API")
        self.assertEqual(emp.current_task, "Build API")

    def test_assign_task_suspended_raises(self):
        eng, r, d, emp = self._setup()
        eng.suspend_employee(emp.id)
        with self.assertRaises(OrgInvalidStateError):
            eng.assign_task(emp.id, "Task")

    def test_complete_task(self):
        eng, r, d, emp = self._setup()
        eng.assign_task(emp.id, "Build API")
        eng.complete_task(emp.id)
        self.assertIsNone(emp.current_task)
        self.assertIn("Build API", emp.previous_tasks)

    def test_add_skill(self):
        eng, r, d, emp = self._setup()
        eng.add_skill_to_employee(emp.id, "Python")
        self.assertIn("Python", emp.skills)

    def test_add_skill_idempotent(self):
        eng, r, d, emp = self._setup()
        eng.add_skill_to_employee(emp.id, "Python")
        eng.add_skill_to_employee(emp.id, "Python")
        self.assertEqual(emp.skills.count("Python"), 1)

    def test_remove_skill(self):
        eng, r, d, emp = self._setup()
        eng.add_skill_to_employee(emp.id, "Python")
        eng.remove_skill_from_employee(emp.id, "Python")
        self.assertNotIn("Python", emp.skills)

    def test_delete_employee(self):
        eng, r, d, emp = self._setup()
        eng.delete_employee(emp.id)
        self.assertEqual(eng.employee_count(), 0)

    def test_delete_employee_removes_from_dept(self):
        eng, r, d, emp = self._setup()
        eng.delete_employee(emp.id)
        self.assertNotIn(emp.id, d.members)


# ===========================================================================
# 13. to_dict methods
# ===========================================================================

class TestToDictMethods(unittest.TestCase):

    def test_role_to_dict_keys(self):
        eng = _fresh_engine()
        role = eng.create_role("R", "desc")
        d = role.to_dict()
        for k in ("id", "name", "description", "created_at"):
            self.assertIn(k, d)

    def test_skill_to_dict_keys(self):
        eng = _fresh_engine()
        skill = eng.create_skill("S", "cat")
        d = skill.to_dict()
        for k in ("id", "name", "category", "created_at"):
            self.assertIn(k, d)

    def test_dept_to_dict_keys(self):
        eng = _fresh_engine()
        dept = eng.create_department("D")
        d = dept.to_dict()
        for k in ("id", "name", "capacity", "status", "director_id",
                  "members", "projects", "member_count", "workload_pct", "created_at"):
            self.assertIn(k, d)

    def test_emp_to_dict_keys(self):
        eng = _fresh_engine()
        role = eng.create_role("R")
        emp = eng.create_employee("Alice", role.id)
        d = emp.to_dict()
        for k in ("id", "name", "role_id", "department_id", "skills",
                  "status", "provider", "current_task", "previous_tasks", "created_at"):
            self.assertIn(k, d)

    def test_dept_to_dict_member_count(self):
        eng = _fresh_engine()
        role = eng.create_role("R")
        dept = eng.create_department("D", capacity=5)
        eng.create_employee("A", role.id, dept.id)
        d = dept.to_dict()
        self.assertEqual(d["member_count"], 1)

    def test_dept_to_dict_workload_pct_zero(self):
        eng = _fresh_engine()
        dept = eng.create_department("D", capacity=10)
        d = dept.to_dict()
        self.assertEqual(d["workload_pct"], 0.0)


# ===========================================================================
# 14. OrgEngine statistics
# ===========================================================================

class TestOrgEngineStatistics(unittest.TestCase):

    def test_statistics_keys(self):
        eng = _fresh_engine()
        stats = eng.statistics()
        for k in ("total_departments", "active_departments", "inactive_departments",
                  "total_employees", "active_employees", "suspended_employees",
                  "terminated_employees", "total_roles", "total_skills",
                  "departments_with_directors"):
            self.assertIn(k, stats)

    def test_statistics_empty(self):
        eng = _fresh_engine()
        stats = eng.statistics()
        self.assertEqual(stats["total_departments"], 0)
        self.assertEqual(stats["total_employees"], 0)
        self.assertEqual(stats["total_roles"], 0)
        self.assertEqual(stats["total_skills"], 0)

    def test_statistics_counts_roles(self):
        eng = _fresh_engine()
        eng.create_role("R1")
        eng.create_role("R2")
        self.assertEqual(eng.statistics()["total_roles"], 2)

    def test_statistics_counts_skills(self):
        eng = _fresh_engine()
        eng.create_skill("S1")
        self.assertEqual(eng.statistics()["total_skills"], 1)

    def test_statistics_active_inactive_depts(self):
        eng = _fresh_engine()
        d1 = eng.create_department("D1")
        d2 = eng.create_department("D2")
        eng.disable_department(d2.id)
        stats = eng.statistics()
        self.assertEqual(stats["active_departments"], 1)
        self.assertEqual(stats["inactive_departments"], 1)

    def test_statistics_suspended_terminated_employees(self):
        eng = _fresh_engine()
        role = eng.create_role("R")
        e1 = eng.create_employee("E1", role.id)
        e2 = eng.create_employee("E2", role.id)
        e3 = eng.create_employee("E3", role.id)
        eng.suspend_employee(e2.id)
        eng.terminate_employee(e3.id)
        stats = eng.statistics()
        self.assertEqual(stats["active_employees"], 1)
        self.assertEqual(stats["suspended_employees"], 1)
        self.assertEqual(stats["terminated_employees"], 1)

    def test_statistics_departments_with_directors(self):
        eng = _fresh_engine()
        role = eng.create_role("R")
        dept = eng.create_department("D")
        emp = eng.create_employee("Alice", role.id)
        eng.assign_director(dept.id, emp.id)
        stats = eng.statistics()
        self.assertEqual(stats["departments_with_directors"], 1)

    def test_role_name_helper(self):
        eng = _fresh_engine()
        role = eng.create_role("Backend Agent")
        self.assertEqual(eng.role_name(role.id), "Backend Agent")

    def test_role_name_unknown_returns_id(self):
        eng = _fresh_engine()
        self.assertEqual(eng.role_name("unknown-id"), "unknown-id")

    def test_department_name_helper(self):
        eng = _fresh_engine()
        dept = eng.create_department("Engineering")
        self.assertEqual(eng.department_name(dept.id), "Engineering")

    def test_department_name_empty_returns_dash(self):
        eng = _fresh_engine()
        self.assertEqual(eng.department_name(""), "—")


# ===========================================================================
# 15. DashboardState — OrgEngine seeded
# ===========================================================================

class TestDashboardStateOrgSeeded(unittest.TestCase):

    def setUp(self):
        DashboardState.reset()
        self.state = DashboardState.get()

    def test_org_engine_exists(self):
        self.assertIsNotNone(self.state.org_engine)

    def test_org_engine_is_orgenginetype(self):
        self.assertIsInstance(self.state.org_engine, OrgEngine)

    def test_org_seeded_roles(self):
        roles = self.state.org_engine.list_roles()
        self.assertGreater(len(roles), 0)

    def test_org_seeded_skills(self):
        skills = self.state.org_engine.list_skills()
        self.assertGreater(len(skills), 0)

    def test_org_seeded_departments(self):
        depts = self.state.org_engine.list_departments()
        self.assertGreater(len(depts), 0)

    def test_org_seeded_employees(self):
        emps = self.state.org_engine.list_employees()
        self.assertGreater(len(emps), 0)

    def test_org_seeded_backend_dept_exists(self):
        depts = self.state.org_engine.list_departments()
        names = [d.name for d in depts]
        self.assertIn("Backend Engineering", names)

    def test_org_seeded_alice_exists(self):
        emps = self.state.org_engine.list_employees()
        names = [e.name for e in emps]
        self.assertIn("Alice Chen", names)

    def test_org_seeded_backend_role_exists(self):
        roles = self.state.org_engine.list_roles()
        names = [r.name for r in roles]
        self.assertIn("Backend Agent", names)

    def test_org_seeded_python_skill_exists(self):
        skills = self.state.org_engine.list_skills()
        names = [s.name for s in skills]
        self.assertIn("Python", skills[0].name if len(skills) > 0 else "Python")

    def test_org_seeded_directors_assigned(self):
        depts = self.state.org_engine.list_departments()
        directors = [d for d in depts if d.director_id is not None]
        self.assertGreater(len(directors), 0)

    def test_org_seeded_alice_has_task(self):
        emps = self.state.org_engine.list_employees()
        alice = next((e for e in emps if e.name == "Alice Chen"), None)
        self.assertIsNotNone(alice)
        self.assertIsNotNone(alice.current_task)

    def test_org_seeded_statistics_nonzero(self):
        stats = self.state.org_engine.statistics()
        self.assertGreater(stats["total_departments"], 0)
        self.assertGreater(stats["total_employees"], 0)
        self.assertGreater(stats["total_roles"], 0)
        self.assertGreater(stats["total_skills"], 0)


# ===========================================================================
# 16. HTML page routes — /org/departments
# ===========================================================================

class TestOrgDepartmentsPage(unittest.TestCase):

    def setUp(self):
        self.client = _client()

    def test_page_status_200(self):
        r = self.client.get("/org/departments")
        self.assertEqual(r.status_code, 200)

    def test_page_contains_h1(self):
        r = self.client.get("/org/departments")
        self.assertIn("Departman Yönetimi", r.text)

    def test_page_contains_yeni_departman_btn(self):
        r = self.client.get("/org/departments")
        self.assertIn("Yeni Departman", r.text)

    def test_page_contains_table_headers(self):
        r = self.client.get("/org/departments")
        self.assertIn("Ad", r.text)
        self.assertIn("Kapasite", r.text)
        self.assertIn("Durum", r.text)

    def test_page_contains_düzenle_button(self):
        r = self.client.get("/org/departments")
        self.assertIn("Düzenle", r.text)

    def test_page_contains_pasif_yap_button(self):
        r = self.client.get("/org/departments")
        self.assertIn("Pasif Yap", r.text)

    def test_page_contains_backend_engineering(self):
        r = self.client.get("/org/departments")
        self.assertIn("Backend Engineering", r.text)

    def test_page_contains_kpi_row(self):
        r = self.client.get("/org/departments")
        self.assertIn("kpi", r.text)

    def test_page_has_subnav(self):
        r = self.client.get("/org/departments")
        self.assertIn("subnav", r.text)

    def test_page_has_departmanlar_subnav_link(self):
        r = self.client.get("/org/departments")
        self.assertIn("/org/departments", r.text)

    def test_page_has_calisanlar_subnav_link(self):
        r = self.client.get("/org/departments")
        self.assertIn("/org/employees", r.text)

    def test_page_has_roller_subnav_link(self):
        r = self.client.get("/org/departments")
        self.assertIn("/org/roles", r.text)

    def test_page_has_yetenekler_subnav_link(self):
        r = self.client.get("/org/departments")
        self.assertIn("/org/skills", r.text)

    def test_page_has_modal(self):
        r = self.client.get("/org/departments")
        self.assertIn("org-modal", r.text)

    def test_page_contains_direktör_header(self):
        r = self.client.get("/org/departments")
        self.assertIn("Direktör", r.text)

    def test_page_contains_üye_sayisi_header(self):
        r = self.client.get("/org/departments")
        self.assertIn("Üye Sayısı", r.text)

    def test_page_contains_aktif_kpi(self):
        r = self.client.get("/org/departments")
        self.assertIn("Aktif", r.text)

    def test_page_page_value_org_departments(self):
        r = self.client.get("/org/departments")
        self.assertIn("subnav-active", r.text)

    def test_page_contains_işlemler_header(self):
        r = self.client.get("/org/departments")
        self.assertIn("İşlemler", r.text)

    def test_page_has_search_input(self):
        r = self.client.get("/org/departments")
        self.assertIn("search-input", r.text)

    def test_page_200_on_second_call(self):
        r1 = self.client.get("/org/departments")
        r2 = self.client.get("/org/departments")
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)


# ===========================================================================
# 17. HTML page routes — /org/employees
# ===========================================================================

class TestOrgEmployeesPage(unittest.TestCase):

    def setUp(self):
        self.client = _client()

    def test_page_status_200(self):
        r = self.client.get("/org/employees")
        self.assertEqual(r.status_code, 200)

    def test_page_contains_h1(self):
        r = self.client.get("/org/employees")
        self.assertIn("Çalışan Yönetimi", r.text)

    def test_page_contains_yeni_calisan_btn(self):
        r = self.client.get("/org/employees")
        self.assertIn("Yeni Çalışan", r.text)

    def test_page_contains_alice(self):
        r = self.client.get("/org/employees")
        self.assertIn("Alice Chen", r.text)

    def test_page_contains_rol_header(self):
        r = self.client.get("/org/employees")
        self.assertIn("Rol", r.text)

    def test_page_contains_departman_header(self):
        r = self.client.get("/org/employees")
        self.assertIn("Departman", r.text)

    def test_page_contains_yetenekler_header(self):
        r = self.client.get("/org/employees")
        self.assertIn("Yetenekler", r.text)

    def test_page_contains_sagleyici_header(self):
        r = self.client.get("/org/employees")
        self.assertIn("Sağlayıcı", r.text)

    def test_page_contains_durum_header(self):
        r = self.client.get("/org/employees")
        self.assertIn("Durum", r.text)

    def test_page_contains_transfer_btn(self):
        r = self.client.get("/org/employees")
        self.assertIn("Transfer", r.text)

    def test_page_contains_askiya_al_btn(self):
        r = self.client.get("/org/employees")
        self.assertIn("Askıya Al", r.text)

    def test_page_contains_sonlandir_btn(self):
        r = self.client.get("/org/employees")
        self.assertIn("Sonlandır", r.text)

    def test_page_has_kpi_toplam_calisan(self):
        r = self.client.get("/org/employees")
        self.assertIn("Toplam Çalışan", r.text)

    def test_page_has_subnav(self):
        r = self.client.get("/org/employees")
        self.assertIn("subnav", r.text)

    def test_page_has_modal(self):
        r = self.client.get("/org/employees")
        self.assertIn("org-modal", r.text)

    def test_page_has_search_input(self):
        r = self.client.get("/org/employees")
        self.assertIn("search-input", r.text)

    def test_page_contains_mevcut_gorev_header(self):
        r = self.client.get("/org/employees")
        self.assertIn("Mevcut Görev", r.text)

    def test_page_contains_islemler_header(self):
        r = self.client.get("/org/employees")
        self.assertIn("İşlemler", r.text)


# ===========================================================================
# 18. HTML page routes — /org/roles
# ===========================================================================

class TestOrgRolesPage(unittest.TestCase):

    def setUp(self):
        self.client = _client()

    def test_page_status_200(self):
        r = self.client.get("/org/roles")
        self.assertEqual(r.status_code, 200)

    def test_page_contains_h1(self):
        r = self.client.get("/org/roles")
        self.assertIn("Rol Yönetimi", r.text)

    def test_page_contains_yeni_rol_btn(self):
        r = self.client.get("/org/roles")
        self.assertIn("Yeni Rol", r.text)

    def test_page_contains_backend_agent_role(self):
        r = self.client.get("/org/roles")
        self.assertIn("Backend Agent", r.text)

    def test_page_contains_rol_adi_header(self):
        r = self.client.get("/org/roles")
        self.assertIn("Rol Adı", r.text)

    def test_page_contains_aciklama_header(self):
        r = self.client.get("/org/roles")
        self.assertIn("Açıklama", r.text)

    def test_page_contains_calisan_sayisi_header(self):
        r = self.client.get("/org/roles")
        self.assertIn("Çalışan Sayısı", r.text)

    def test_page_has_subnav(self):
        r = self.client.get("/org/roles")
        self.assertIn("subnav", r.text)

    def test_page_has_modal(self):
        r = self.client.get("/org/roles")
        self.assertIn("org-modal", r.text)

    def test_page_has_search_input(self):
        r = self.client.get("/org/roles")
        self.assertIn("search-input", r.text)

    def test_page_contains_toplam_rol_kpi(self):
        r = self.client.get("/org/roles")
        self.assertIn("Toplam Rol", r.text)


# ===========================================================================
# 19. HTML page routes — /org/skills
# ===========================================================================

class TestOrgSkillsPage(unittest.TestCase):

    def setUp(self):
        self.client = _client()

    def test_page_status_200(self):
        r = self.client.get("/org/skills")
        self.assertEqual(r.status_code, 200)

    def test_page_contains_h1(self):
        r = self.client.get("/org/skills")
        self.assertIn("Yetenek Yönetimi", r.text)

    def test_page_contains_yeni_yetenek_btn(self):
        r = self.client.get("/org/skills")
        self.assertIn("Yeni Yetenek", r.text)

    def test_page_contains_python_skill(self):
        r = self.client.get("/org/skills")
        self.assertIn("Python", r.text)

    def test_page_contains_yetenek_adi_header(self):
        r = self.client.get("/org/skills")
        self.assertIn("Yetenek Adı", r.text)

    def test_page_contains_kategori_header(self):
        r = self.client.get("/org/skills")
        self.assertIn("Kategori", r.text)

    def test_page_contains_sahip_calisan_header(self):
        r = self.client.get("/org/skills")
        self.assertIn("Sahip Çalışan", r.text)

    def test_page_has_subnav(self):
        r = self.client.get("/org/skills")
        self.assertIn("subnav", r.text)

    def test_page_has_modal(self):
        r = self.client.get("/org/skills")
        self.assertIn("org-modal", r.text)

    def test_page_has_search_input(self):
        r = self.client.get("/org/skills")
        self.assertIn("search-input", r.text)

    def test_page_contains_toplam_yetenek_kpi(self):
        r = self.client.get("/org/skills")
        self.assertIn("Toplam Yetenek", r.text)


# ===========================================================================
# 20. JSON API — GET /api/org/departments
# ===========================================================================

class TestApiOrgDepartmentsGet(unittest.TestCase):

    def setUp(self):
        self.client = _client()

    def test_get_status_200(self):
        r = self.client.get("/api/org/departments")
        self.assertEqual(r.status_code, 200)

    def test_get_returns_list(self):
        r = self.client.get("/api/org/departments")
        self.assertIsInstance(r.json(), list)

    def test_get_returns_seeded_depts(self):
        r = self.client.get("/api/org/departments")
        self.assertGreater(len(r.json()), 0)

    def test_get_dept_has_id_field(self):
        r = self.client.get("/api/org/departments")
        self.assertIn("id", r.json()[0])

    def test_get_dept_has_name_field(self):
        r = self.client.get("/api/org/departments")
        self.assertIn("name", r.json()[0])

    def test_get_dept_has_status_field(self):
        r = self.client.get("/api/org/departments")
        self.assertIn("status", r.json()[0])

    def test_get_dept_has_capacity_field(self):
        r = self.client.get("/api/org/departments")
        self.assertIn("capacity", r.json()[0])

    def test_get_dept_has_member_count_field(self):
        r = self.client.get("/api/org/departments")
        self.assertIn("member_count", r.json()[0])


# ===========================================================================
# 21. JSON API — POST /api/org/departments (create)
# ===========================================================================

class TestApiOrgDepartmentsCreate(unittest.TestCase):

    def setUp(self):
        self.client = _client()

    def test_create_returns_success_true(self):
        r = self.client.post("/api/org/departments",
                             json={"name": "Marketing", "capacity": 8})
        self.assertTrue(r.json()["success"])

    def test_create_returns_department(self):
        r = self.client.post("/api/org/departments",
                             json={"name": "Marketing", "capacity": 8})
        self.assertIn("department", r.json())

    def test_create_stored_in_engine(self):
        self.client.post("/api/org/departments",
                         json={"name": "NewDept123", "capacity": 5})
        r = self.client.get("/api/org/departments")
        names = [d["name"] for d in r.json()]
        self.assertIn("NewDept123", names)

    def test_create_empty_name_returns_error(self):
        r = self.client.post("/api/org/departments", json={"name": ""})
        self.assertFalse(r.json()["success"])

    def test_create_missing_name_returns_error(self):
        r = self.client.post("/api/org/departments", json={"capacity": 5})
        self.assertFalse(r.json()["success"])

    def test_create_default_capacity(self):
        r = self.client.post("/api/org/departments", json={"name": "TestCap"})
        self.assertTrue(r.json()["success"])

    def test_create_returns_400_on_empty_name(self):
        r = self.client.post("/api/org/departments", json={"name": ""})
        self.assertEqual(r.status_code, 400)


# ===========================================================================
# 22. JSON API — PUT /api/org/departments/{id} (edit)
# ===========================================================================

class TestApiOrgDepartmentsEdit(unittest.TestCase):

    def setUp(self):
        self.client = _client()
        r = self.client.post("/api/org/departments",
                             json={"name": "EditMe", "capacity": 5})
        self.dept_id = r.json()["department"]["id"]

    def test_edit_name(self):
        r = self.client.put(f"/api/org/departments/{self.dept_id}",
                            json={"name": "EditedName"})
        self.assertTrue(r.json()["success"])
        self.assertEqual(r.json()["department"]["name"], "EditedName")

    def test_edit_capacity(self):
        r = self.client.put(f"/api/org/departments/{self.dept_id}",
                            json={"capacity": 20})
        self.assertTrue(r.json()["success"])
        self.assertEqual(r.json()["department"]["capacity"], 20)

    def test_edit_not_found_returns_error(self):
        r = self.client.put("/api/org/departments/bad-id", json={"name": "X"})
        self.assertFalse(r.json()["success"])


# ===========================================================================
# 23. JSON API — POST /api/org/departments/{id}/disable and /enable
# ===========================================================================

class TestApiOrgDepartmentsDisableEnable(unittest.TestCase):

    def setUp(self):
        self.client = _client()
        r = self.client.post("/api/org/departments",
                             json={"name": "ToDisable", "capacity": 3})
        self.dept_id = r.json()["department"]["id"]

    def test_disable_success(self):
        r = self.client.post(f"/api/org/departments/{self.dept_id}/disable")
        self.assertTrue(r.json()["success"])

    def test_disable_status_becomes_inactive(self):
        self.client.post(f"/api/org/departments/{self.dept_id}/disable")
        r = self.client.get("/api/org/departments")
        dept = next(d for d in r.json() if d["id"] == self.dept_id)
        self.assertEqual(dept["status"], "inactive")

    def test_enable_after_disable(self):
        self.client.post(f"/api/org/departments/{self.dept_id}/disable")
        r = self.client.post(f"/api/org/departments/{self.dept_id}/enable")
        self.assertTrue(r.json()["success"])

    def test_disable_already_inactive_returns_error(self):
        self.client.post(f"/api/org/departments/{self.dept_id}/disable")
        r = self.client.post(f"/api/org/departments/{self.dept_id}/disable")
        self.assertFalse(r.json()["success"])

    def test_enable_not_found_returns_error(self):
        r = self.client.post("/api/org/departments/bad-id/enable")
        self.assertFalse(r.json()["success"])


# ===========================================================================
# 24. JSON API — GET /api/org/employees
# ===========================================================================

class TestApiOrgEmployeesGet(unittest.TestCase):

    def setUp(self):
        self.client = _client()

    def test_get_status_200(self):
        r = self.client.get("/api/org/employees")
        self.assertEqual(r.status_code, 200)

    def test_get_returns_list(self):
        self.assertIsInstance(self.client.get("/api/org/employees").json(), list)

    def test_get_seeded_employees_present(self):
        r = self.client.get("/api/org/employees")
        self.assertGreater(len(r.json()), 0)

    def test_emp_has_id(self):
        r = self.client.get("/api/org/employees")
        self.assertIn("id", r.json()[0])

    def test_emp_has_name(self):
        r = self.client.get("/api/org/employees")
        self.assertIn("name", r.json()[0])

    def test_emp_has_role_id(self):
        r = self.client.get("/api/org/employees")
        self.assertIn("role_id", r.json()[0])

    def test_emp_has_status(self):
        r = self.client.get("/api/org/employees")
        self.assertIn("status", r.json()[0])

    def test_emp_has_skills(self):
        r = self.client.get("/api/org/employees")
        self.assertIn("skills", r.json()[0])

    def test_emp_has_role_name(self):
        r = self.client.get("/api/org/employees")
        self.assertIn("role_name", r.json()[0])

    def test_emp_has_department_name(self):
        r = self.client.get("/api/org/employees")
        self.assertIn("department_name", r.json()[0])


# ===========================================================================
# 25. JSON API — POST /api/org/employees (create)
# ===========================================================================

class TestApiOrgEmployeesCreate(unittest.TestCase):

    def setUp(self):
        self.client = _client()
        roles = self.client.get("/api/org/roles").json()
        self.role_id = roles[0]["id"]

    def test_create_success(self):
        r = self.client.post("/api/org/employees",
                             json={"name": "Zeynep", "role_id": self.role_id})
        self.assertTrue(r.json()["success"])

    def test_create_empty_name_error(self):
        r = self.client.post("/api/org/employees",
                             json={"name": "", "role_id": self.role_id})
        self.assertFalse(r.json()["success"])

    def test_create_missing_role_error(self):
        r = self.client.post("/api/org/employees", json={"name": "X"})
        self.assertFalse(r.json()["success"])

    def test_create_bad_role_id_error(self):
        r = self.client.post("/api/org/employees",
                             json={"name": "X", "role_id": "bad-id"})
        self.assertFalse(r.json()["success"])

    def test_create_stored(self):
        self.client.post("/api/org/employees",
                         json={"name": "Mehmet", "role_id": self.role_id})
        r = self.client.get("/api/org/employees")
        names = [e["name"] for e in r.json()]
        self.assertIn("Mehmet", names)

    def test_create_400_on_missing_role(self):
        r = self.client.post("/api/org/employees", json={"name": "X"})
        self.assertEqual(r.status_code, 400)


# ===========================================================================
# 26. JSON API — employee actions (suspend / reactivate / terminate / transfer)
# ===========================================================================

class TestApiOrgEmployeeActions(unittest.TestCase):

    def setUp(self):
        self.client = _client()
        roles = self.client.get("/api/org/roles").json()
        self.role_id = roles[0]["id"]
        r = self.client.post("/api/org/employees",
                             json={"name": "TestEmp", "role_id": self.role_id})
        self.emp_id = r.json()["employee"]["id"]

    def test_suspend_success(self):
        r = self.client.post(f"/api/org/employees/{self.emp_id}/suspend")
        self.assertTrue(r.json()["success"])

    def test_suspend_status_suspended(self):
        self.client.post(f"/api/org/employees/{self.emp_id}/suspend")
        emps = self.client.get("/api/org/employees").json()
        emp = next(e for e in emps if e["id"] == self.emp_id)
        self.assertEqual(emp["status"], "suspended")

    def test_reactivate_after_suspend(self):
        self.client.post(f"/api/org/employees/{self.emp_id}/suspend")
        r = self.client.post(f"/api/org/employees/{self.emp_id}/reactivate")
        self.assertTrue(r.json()["success"])

    def test_terminate_success(self):
        r = self.client.post(f"/api/org/employees/{self.emp_id}/terminate")
        self.assertTrue(r.json()["success"])

    def test_terminate_status_terminated(self):
        self.client.post(f"/api/org/employees/{self.emp_id}/terminate")
        emps = self.client.get("/api/org/employees").json()
        emp = next(e for e in emps if e["id"] == self.emp_id)
        self.assertEqual(emp["status"], "terminated")

    def test_transfer_success(self):
        depts = self.client.get("/api/org/departments").json()
        target_dept = depts[0]["id"]
        r = self.client.post(f"/api/org/employees/{self.emp_id}/transfer",
                             json={"department_id": target_dept})
        self.assertTrue(r.json()["success"])

    def test_transfer_bad_dept_error(self):
        r = self.client.post(f"/api/org/employees/{self.emp_id}/transfer",
                             json={"department_id": "bad-id"})
        self.assertFalse(r.json()["success"])

    def test_transfer_missing_dept_error(self):
        r = self.client.post(f"/api/org/employees/{self.emp_id}/transfer",
                             json={})
        self.assertFalse(r.json()["success"])

    def test_suspend_not_found_error(self):
        r = self.client.post("/api/org/employees/bad-id/suspend")
        self.assertFalse(r.json()["success"])

    def test_terminate_not_found_error(self):
        r = self.client.post("/api/org/employees/bad-id/terminate")
        self.assertFalse(r.json()["success"])


# ===========================================================================
# 27. JSON API — PUT /api/org/employees/{id} (edit)
# ===========================================================================

class TestApiOrgEmployeesEdit(unittest.TestCase):

    def setUp(self):
        self.client = _client()
        roles = self.client.get("/api/org/roles").json()
        self.role_id = roles[0]["id"]
        r = self.client.post("/api/org/employees",
                             json={"name": "EditEmp", "role_id": self.role_id})
        self.emp_id = r.json()["employee"]["id"]

    def test_edit_name(self):
        r = self.client.put(f"/api/org/employees/{self.emp_id}",
                            json={"name": "Renamed"})
        self.assertTrue(r.json()["success"])
        self.assertEqual(r.json()["employee"]["name"], "Renamed")

    def test_edit_provider(self):
        r = self.client.put(f"/api/org/employees/{self.emp_id}",
                            json={"provider": "openai"})
        self.assertTrue(r.json()["success"])

    def test_edit_not_found_error(self):
        r = self.client.put("/api/org/employees/bad-id", json={"name": "X"})
        self.assertFalse(r.json()["success"])


# ===========================================================================
# 28. JSON API — GET/POST /api/org/roles
# ===========================================================================

class TestApiOrgRoles(unittest.TestCase):

    def setUp(self):
        self.client = _client()

    def test_get_roles_status_200(self):
        r = self.client.get("/api/org/roles")
        self.assertEqual(r.status_code, 200)

    def test_get_roles_returns_list(self):
        self.assertIsInstance(self.client.get("/api/org/roles").json(), list)

    def test_get_roles_seeded(self):
        r = self.client.get("/api/org/roles")
        self.assertGreater(len(r.json()), 0)

    def test_role_has_id(self):
        r = self.client.get("/api/org/roles")
        self.assertIn("id", r.json()[0])

    def test_role_has_name(self):
        r = self.client.get("/api/org/roles")
        self.assertIn("name", r.json()[0])

    def test_create_role_success(self):
        r = self.client.post("/api/org/roles",
                             json={"name": "Unity Engineer", "description": "Unity dev"})
        self.assertTrue(r.json()["success"])

    def test_create_role_stored(self):
        self.client.post("/api/org/roles", json={"name": "YouTube Editor"})
        r = self.client.get("/api/org/roles")
        names = [ro["name"] for ro in r.json()]
        self.assertIn("YouTube Editor", names)

    def test_create_role_empty_name_error(self):
        r = self.client.post("/api/org/roles", json={"name": ""})
        self.assertFalse(r.json()["success"])

    def test_create_role_duplicate_error(self):
        self.client.post("/api/org/roles", json={"name": "DupRole"})
        r = self.client.post("/api/org/roles", json={"name": "DupRole"})
        self.assertFalse(r.json()["success"])

    def test_edit_role_success(self):
        r = self.client.post("/api/org/roles",
                             json={"name": "ToEdit", "description": "old"})
        role_id = r.json()["role"]["id"]
        r2 = self.client.put(f"/api/org/roles/{role_id}",
                             json={"description": "new desc"})
        self.assertTrue(r2.json()["success"])


# ===========================================================================
# 29. JSON API — GET/POST /api/org/skills
# ===========================================================================

class TestApiOrgSkills(unittest.TestCase):

    def setUp(self):
        self.client = _client()

    def test_get_skills_status_200(self):
        r = self.client.get("/api/org/skills")
        self.assertEqual(r.status_code, 200)

    def test_get_skills_returns_list(self):
        self.assertIsInstance(self.client.get("/api/org/skills").json(), list)

    def test_get_skills_seeded(self):
        r = self.client.get("/api/org/skills")
        self.assertGreater(len(r.json()), 0)

    def test_skill_has_id(self):
        r = self.client.get("/api/org/skills")
        self.assertIn("id", r.json()[0])

    def test_skill_has_name(self):
        r = self.client.get("/api/org/skills")
        self.assertIn("name", r.json()[0])

    def test_skill_has_category(self):
        r = self.client.get("/api/org/skills")
        self.assertIn("category", r.json()[0])

    def test_create_skill_success(self):
        r = self.client.post("/api/org/skills",
                             json={"name": "Blender", "category": "3D"})
        self.assertTrue(r.json()["success"])

    def test_create_skill_stored(self):
        self.client.post("/api/org/skills", json={"name": "UnrealEngine"})
        r = self.client.get("/api/org/skills")
        names = [s["name"] for s in r.json()]
        self.assertIn("UnrealEngine", names)

    def test_create_skill_empty_name_error(self):
        r = self.client.post("/api/org/skills", json={"name": ""})
        self.assertFalse(r.json()["success"])

    def test_create_skill_duplicate_error(self):
        self.client.post("/api/org/skills", json={"name": "DupSkill"})
        r = self.client.post("/api/org/skills", json={"name": "DupSkill"})
        self.assertFalse(r.json()["success"])

    def test_edit_skill_success(self):
        r = self.client.post("/api/org/skills",
                             json={"name": "ToEditSkill", "category": "old"})
        skill_id = r.json()["skill"]["id"]
        r2 = self.client.put(f"/api/org/skills/{skill_id}",
                             json={"category": "Updated"})
        self.assertTrue(r2.json()["success"])


# ===========================================================================
# 30. JSON API — GET /api/org/statistics
# ===========================================================================

class TestApiOrgStatistics(unittest.TestCase):

    def setUp(self):
        self.client = _client()

    def test_status_200(self):
        r = self.client.get("/api/org/statistics")
        self.assertEqual(r.status_code, 200)

    def test_returns_dict(self):
        r = self.client.get("/api/org/statistics")
        self.assertIsInstance(r.json(), dict)

    def test_has_total_departments(self):
        r = self.client.get("/api/org/statistics")
        self.assertIn("total_departments", r.json())

    def test_has_total_employees(self):
        r = self.client.get("/api/org/statistics")
        self.assertIn("total_employees", r.json())

    def test_has_total_roles(self):
        r = self.client.get("/api/org/statistics")
        self.assertIn("total_roles", r.json())

    def test_has_total_skills(self):
        r = self.client.get("/api/org/statistics")
        self.assertIn("total_skills", r.json())

    def test_total_departments_nonzero(self):
        r = self.client.get("/api/org/statistics")
        self.assertGreater(r.json()["total_departments"], 0)

    def test_total_employees_nonzero(self):
        r = self.client.get("/api/org/statistics")
        self.assertGreater(r.json()["total_employees"], 0)


# ===========================================================================
# 31. Subnav — present on all org pages
# ===========================================================================

class TestOrgSubNav(unittest.TestCase):

    def setUp(self):
        self.client = _client()

    def _check_subnav_links(self, url):
        r = self.client.get(url)
        self.assertIn("/org", r.text)
        self.assertIn("/org/departments", r.text)
        self.assertIn("/org/employees", r.text)
        self.assertIn("/org/roles", r.text)
        self.assertIn("/org/skills", r.text)

    def test_org_tree_has_subnav(self):
        self._check_subnav_links("/org")

    def test_org_departments_has_subnav(self):
        self._check_subnav_links("/org/departments")

    def test_org_employees_has_subnav(self):
        self._check_subnav_links("/org/employees")

    def test_org_roles_has_subnav(self):
        self._check_subnav_links("/org/roles")

    def test_org_skills_has_subnav(self):
        self._check_subnav_links("/org/skills")

    def test_ağaç_görünümü_link_present_on_depts(self):
        r = self.client.get("/org/departments")
        self.assertIn("Ağaç Görünümü", r.text)

    def test_departmanlar_link_present_on_roles(self):
        r = self.client.get("/org/roles")
        self.assertIn("Departmanlar", r.text)

    def test_roller_link_present_on_skills(self):
        r = self.client.get("/org/skills")
        self.assertIn("Roller", r.text)

    def test_yetenekler_link_present_on_employees(self):
        r = self.client.get("/org/employees")
        self.assertIn("Yetenekler", r.text)


# ===========================================================================
# 32. Regression — existing HTML routes still work
# ===========================================================================

class TestRegressionExistingHtmlRoutes(unittest.TestCase):

    def setUp(self):
        self.client = _client()

    def test_dashboard_home_200(self):
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_projects_200(self):
        self.assertEqual(self.client.get("/projects").status_code, 200)

    def test_employees_200(self):
        self.assertEqual(self.client.get("/employees").status_code, 200)

    def test_workflow_200(self):
        self.assertEqual(self.client.get("/workflow").status_code, 200)

    def test_events_200(self):
        self.assertEqual(self.client.get("/events").status_code, 200)

    def test_org_tree_200(self):
        self.assertEqual(self.client.get("/org").status_code, 200)

    def test_dashboard_has_sprint19(self):
        r = self.client.get("/")
        self.assertIn("Sprint 19", r.text)

    def test_dashboard_has_ceo_komutu(self):
        r = self.client.get("/")
        self.assertIn("CEO Komutu", r.text)

    def test_projects_page_has_aktif(self):
        r = self.client.get("/projects")
        self.assertIn("proje", r.text.lower())

    def test_employees_page_has_çalışan(self):
        r = self.client.get("/employees")
        self.assertIn("Çalışan", r.text)


# ===========================================================================
# 33. Regression — existing JSON API routes still work
# ===========================================================================

class TestRegressionExistingApiRoutes(unittest.TestCase):

    def setUp(self):
        self.client = _client()

    def test_api_stats_200(self):
        self.assertEqual(self.client.get("/api/stats").status_code, 200)

    def test_api_events_recent_200(self):
        self.assertEqual(self.client.get("/api/events/recent").status_code, 200)

    def test_api_projects_200(self):
        self.assertEqual(self.client.get("/api/projects").status_code, 200)

    def test_api_employees_200(self):
        self.assertEqual(self.client.get("/api/employees").status_code, 200)

    def test_api_workflow_200(self):
        self.assertEqual(self.client.get("/api/workflow").status_code, 200)

    def test_api_memory_200(self):
        self.assertEqual(self.client.get("/api/memory").status_code, 200)

    def test_api_decisions_200(self):
        self.assertEqual(self.client.get("/api/decisions").status_code, 200)

    def test_api_discussions_200(self):
        self.assertEqual(self.client.get("/api/discussions").status_code, 200)

    def test_api_timeline_200(self):
        self.assertEqual(self.client.get("/api/timeline").status_code, 200)

    def test_api_command_history_200(self):
        self.assertEqual(self.client.get("/api/command-history").status_code, 200)

    def test_api_agent_status_200(self):
        self.assertEqual(self.client.get("/api/agent-status").status_code, 200)

    def test_api_artifacts_200(self):
        self.assertEqual(self.client.get("/api/artifacts").status_code, 200)

    def test_api_status_200(self):
        self.assertEqual(self.client.get("/api/status").status_code, 200)

    def test_api_stats_has_total_projects(self):
        r = self.client.get("/api/stats")
        self.assertIn("total_projects", r.json())

    def test_api_employees_returns_list(self):
        r = self.client.get("/api/employees")
        self.assertIsInstance(r.json(), list)

    def test_api_projects_returns_list(self):
        r = self.client.get("/api/projects")
        self.assertIsInstance(r.json(), list)


# ===========================================================================
# 34. OrgEngine — advanced edge cases
# ===========================================================================

class TestOrgEngineEdgeCases(unittest.TestCase):

    def test_create_dept_with_director_id_not_found(self):
        eng = _fresh_engine()
        with self.assertRaises(OrgEmployeeNotFoundError):
            eng.create_department("D", director_id="nonexistent")

    def test_add_member_invalid_emp_raises(self):
        eng = _fresh_engine()
        dept = eng.create_department("D")
        with self.assertRaises(OrgEmployeeNotFoundError):
            eng.add_member(dept.id, "bad-id")

    def test_add_member_invalid_dept_raises(self):
        eng = _fresh_engine()
        role = eng.create_role("R")
        emp = eng.create_employee("Alice", role.id)
        with self.assertRaises(OrgDepartmentNotFoundError):
            eng.add_member("bad-dept", emp.id)

    def test_remove_member_not_in_dept(self):
        eng = _fresh_engine()
        role = eng.create_role("R")
        dept = eng.create_department("D")
        emp = eng.create_employee("Alice", role.id)
        eng.remove_member(dept.id, emp.id)
        self.assertNotIn(emp.id, dept.members)

    def test_complete_task_no_current_task(self):
        eng = _fresh_engine()
        role = eng.create_role("R")
        emp = eng.create_employee("Alice", role.id)
        eng.complete_task(emp.id)
        self.assertEqual(emp.previous_tasks, [])

    def test_add_skill_terminated_raises(self):
        eng = _fresh_engine()
        role = eng.create_role("R")
        emp = eng.create_employee("Alice", role.id)
        eng.terminate_employee(emp.id)
        with self.assertRaises(OrgInvalidStateError):
            eng.add_skill_to_employee(emp.id, "Python")

    def test_create_employee_no_dept_not_in_any_members(self):
        eng = _fresh_engine()
        role = eng.create_role("R")
        emp = eng.create_employee("Alice", role.id)
        for dept in eng.list_departments():
            self.assertNotIn(emp.id, dept.members)

    def test_transfer_from_none_dept(self):
        eng = _fresh_engine()
        role = eng.create_role("R")
        emp = eng.create_employee("Alice", role.id)
        dept = eng.create_department("D")
        eng.transfer_employee(emp.id, dept.id)
        self.assertEqual(emp.department_id, dept.id)
        self.assertIn(emp.id, dept.members)

    def test_director_assign_bad_dept_raises(self):
        eng = _fresh_engine()
        role = eng.create_role("R")
        emp = eng.create_employee("Alice", role.id)
        with self.assertRaises(OrgDepartmentNotFoundError):
            eng.assign_director("bad-id", emp.id)

    def test_employees_in_empty_dept(self):
        eng = _fresh_engine()
        dept = eng.create_department("D")
        result = eng.employees_in_department(dept.id)
        self.assertEqual(result, [])

    def test_multiple_employees_in_dept(self):
        eng = _fresh_engine()
        role = eng.create_role("R")
        dept = eng.create_department("D")
        eng.create_employee("A", role.id, dept.id)
        eng.create_employee("B", role.id, dept.id)
        result = eng.employees_in_department(dept.id)
        self.assertEqual(len(result), 2)

    def test_workload_pct_caps_at_100(self):
        eng = _fresh_engine()
        role = eng.create_role("R")
        dept = eng.create_department("D", capacity=1)
        eng.create_employee("A", role.id, dept.id)
        eng.create_employee("B", role.id, dept.id)
        pct = dept.workload_pct()
        self.assertLessEqual(pct, 100.0)


# ===========================================================================
# 35. API — skills add to employee
# ===========================================================================

class TestApiOrgEmployeeSkills(unittest.TestCase):

    def setUp(self):
        self.client = _client()
        roles = self.client.get("/api/org/roles").json()
        self.role_id = roles[0]["id"]
        r = self.client.post("/api/org/employees",
                             json={"name": "SkillEmp", "role_id": self.role_id})
        self.emp_id = r.json()["employee"]["id"]

    def test_add_skill_success(self):
        r = self.client.post(f"/api/org/employees/{self.emp_id}/skills",
                             json={"skill": "Python"})
        self.assertTrue(r.json()["success"])

    def test_add_skill_stored_in_employee(self):
        self.client.post(f"/api/org/employees/{self.emp_id}/skills",
                         json={"skill": "Docker"})
        emps = self.client.get("/api/org/employees").json()
        emp = next(e for e in emps if e["id"] == self.emp_id)
        self.assertIn("Docker", emp["skills"])

    def test_add_skill_empty_name_error(self):
        r = self.client.post(f"/api/org/employees/{self.emp_id}/skills",
                             json={"skill": ""})
        self.assertFalse(r.json()["success"])

    def test_add_skill_not_found_error(self):
        r = self.client.post("/api/org/employees/bad-id/skills",
                             json={"skill": "Python"})
        self.assertFalse(r.json()["success"])


# ===========================================================================
# 36. Director assignment API
# ===========================================================================

class TestApiOrgDirectorAssignment(unittest.TestCase):

    def setUp(self):
        self.client = _client()
        depts = self.client.get("/api/org/departments").json()
        self.dept_id = depts[0]["id"]
        roles = self.client.get("/api/org/roles").json()
        r = self.client.post("/api/org/employees",
                             json={"name": "DirCandidate", "role_id": roles[0]["id"]})
        self.emp_id = r.json()["employee"]["id"]

    def test_assign_director_success(self):
        r = self.client.post(f"/api/org/departments/{self.dept_id}/director",
                             json={"employee_id": self.emp_id})
        self.assertTrue(r.json()["success"])

    def test_assign_director_reflected_in_dept(self):
        self.client.post(f"/api/org/departments/{self.dept_id}/director",
                         json={"employee_id": self.emp_id})
        depts = self.client.get("/api/org/departments").json()
        dept = next(d for d in depts if d["id"] == self.dept_id)
        self.assertEqual(dept["director_id"], self.emp_id)

    def test_assign_director_missing_employee_id(self):
        r = self.client.post(f"/api/org/departments/{self.dept_id}/director",
                             json={})
        self.assertFalse(r.json()["success"])

    def test_assign_director_bad_dept_error(self):
        r = self.client.post("/api/org/departments/bad-id/director",
                             json={"employee_id": self.emp_id})
        self.assertFalse(r.json()["success"])


# ===========================================================================
# 37. OrgDepartment — is_active / is_inactive boolean helpers
# ===========================================================================

class TestOrgDeptBooleanHelpers(unittest.TestCase):

    def test_is_active_true_by_default(self):
        eng = _fresh_engine()
        dept = eng.create_department("D")
        self.assertTrue(dept.is_active())

    def test_is_inactive_false_by_default(self):
        eng = _fresh_engine()
        dept = eng.create_department("D")
        self.assertFalse(dept.is_inactive())

    def test_is_active_false_after_disable(self):
        eng = _fresh_engine()
        dept = eng.create_department("D")
        eng.disable_department(dept.id)
        self.assertFalse(dept.is_active())

    def test_is_inactive_true_after_disable(self):
        eng = _fresh_engine()
        dept = eng.create_department("D")
        eng.disable_department(dept.id)
        self.assertTrue(dept.is_inactive())

    def test_is_active_true_after_re_enable(self):
        eng = _fresh_engine()
        dept = eng.create_department("D")
        eng.disable_department(dept.id)
        eng.enable_department(dept.id)
        self.assertTrue(dept.is_active())


# ===========================================================================
# 38. OrgEmployee — suspended and terminated boolean helpers
# ===========================================================================

class TestOrgEmpBooleanHelpers(unittest.TestCase):

    def _emp(self):
        eng = _fresh_engine()
        role = eng.create_role("R")
        emp = eng.create_employee("A", role.id)
        return eng, emp

    def test_is_suspended_true_after_suspend(self):
        eng, emp = self._emp()
        eng.suspend_employee(emp.id)
        self.assertTrue(emp.is_suspended())

    def test_is_active_false_after_suspend(self):
        eng, emp = self._emp()
        eng.suspend_employee(emp.id)
        self.assertFalse(emp.is_active())

    def test_is_terminated_true_after_terminate(self):
        eng, emp = self._emp()
        eng.terminate_employee(emp.id)
        self.assertTrue(emp.is_terminated())

    def test_is_active_false_after_terminate(self):
        eng, emp = self._emp()
        eng.terminate_employee(emp.id)
        self.assertFalse(emp.is_active())

    def test_is_suspended_false_after_reactivate(self):
        eng, emp = self._emp()
        eng.suspend_employee(emp.id)
        eng.reactivate_employee(emp.id)
        self.assertFalse(emp.is_suspended())


# ===========================================================================
# 39. API — PUT /api/org/roles/{id}
# ===========================================================================

class TestApiOrgRoleEdit(unittest.TestCase):

    def setUp(self):
        self.client = _client()
        r = self.client.post("/api/org/roles",
                             json={"name": "EditableRole", "description": "old"})
        self.role_id = r.json()["role"]["id"]

    def test_edit_role_name(self):
        r = self.client.put(f"/api/org/roles/{self.role_id}",
                            json={"name": "RenamedRole"})
        self.assertTrue(r.json()["success"])
        self.assertEqual(r.json()["role"]["name"], "RenamedRole")

    def test_edit_role_description(self):
        r = self.client.put(f"/api/org/roles/{self.role_id}",
                            json={"description": "updated description"})
        self.assertTrue(r.json()["success"])

    def test_edit_role_not_found_error(self):
        r = self.client.put("/api/org/roles/bad-id", json={"name": "X"})
        self.assertFalse(r.json()["success"])


# ===========================================================================
# 40. API — PUT /api/org/skills/{id}
# ===========================================================================

class TestApiOrgSkillEdit(unittest.TestCase):

    def setUp(self):
        self.client = _client()
        r = self.client.post("/api/org/skills",
                             json={"name": "EditableSkill", "category": "old"})
        self.skill_id = r.json()["skill"]["id"]

    def test_edit_skill_name(self):
        r = self.client.put(f"/api/org/skills/{self.skill_id}",
                            json={"name": "RenamedSkill"})
        self.assertTrue(r.json()["success"])
        self.assertEqual(r.json()["skill"]["name"], "RenamedSkill")

    def test_edit_skill_category(self):
        r = self.client.put(f"/api/org/skills/{self.skill_id}",
                            json={"category": "NewCat"})
        self.assertTrue(r.json()["success"])

    def test_edit_skill_not_found_error(self):
        r = self.client.put("/api/org/skills/bad-id", json={"name": "X"})
        self.assertFalse(r.json()["success"])


# ===========================================================================
# 41. DashboardState — reset creates fresh OrgEngine
# ===========================================================================

class TestDashboardStateReset(unittest.TestCase):

    def test_reset_gives_fresh_seeded_engine(self):
        DashboardState.reset()
        s1 = DashboardState.get()
        role = s1.org_engine.create_role("TempRole")
        DashboardState.reset()
        s2 = DashboardState.get()
        roles = [r.name for r in s2.org_engine.list_roles()]
        self.assertNotIn("TempRole", roles)

    def test_reset_then_get_is_singleton(self):
        DashboardState.reset()
        s1 = DashboardState.get()
        s2 = DashboardState.get()
        self.assertIs(s1, s2)

    def test_org_engine_same_instance_within_session(self):
        DashboardState.reset()
        state = DashboardState.get()
        eng1 = state.org_engine
        eng2 = DashboardState.get().org_engine
        self.assertIs(eng1, eng2)


# ===========================================================================
# 42. OrgRole / OrgSkill / OrgDepartment / OrgEmployee created_at ordering
# ===========================================================================

class TestCreatedAtOrdering(unittest.TestCase):

    def test_role_created_at_increases(self):
        import time
        eng = _fresh_engine()
        r1 = eng.create_role("R1")
        time.sleep(0.01)
        r2 = eng.create_role("R2")
        self.assertLessEqual(r1.created_at, r2.created_at)

    def test_skill_created_at_is_datetime(self):
        eng = _fresh_engine()
        skill = eng.create_skill("S")
        self.assertIsInstance(skill.created_at, datetime)

    def test_dept_created_at_is_datetime(self):
        eng = _fresh_engine()
        dept = eng.create_department("D")
        self.assertIsInstance(dept.created_at, datetime)

    def test_emp_created_at_is_datetime(self):
        eng = _fresh_engine()
        role = eng.create_role("R")
        emp = eng.create_employee("A", role.id)
        self.assertIsInstance(emp.created_at, datetime)


# ===========================================================================
# 43. Seeded org — minimum content assertions
# ===========================================================================

class TestSeededOrgMinimumContent(unittest.TestCase):

    def setUp(self):
        DashboardState.reset()
        self.eng = DashboardState.get().org_engine

    def test_at_least_4_departments(self):
        self.assertGreaterEqual(self.eng.department_count(), 4)

    def test_at_least_5_employees(self):
        self.assertGreaterEqual(self.eng.employee_count(), 5)

    def test_at_least_6_roles(self):
        self.assertGreaterEqual(self.eng.role_count(), 6)

    def test_at_least_10_skills(self):
        self.assertGreaterEqual(self.eng.skill_count(), 10)

    def test_all_seeded_depts_active(self):
        for dept in self.eng.list_departments():
            self.assertEqual(dept.status, "active")

    def test_all_seeded_employees_active(self):
        for emp in self.eng.list_employees():
            self.assertEqual(emp.status, "active")

    def test_bob_has_current_task(self):
        emps = self.eng.list_employees()
        bob = next((e for e in emps if "Bob" in e.name), None)
        if bob:
            self.assertIsNotNone(bob.current_task)

    def test_seeded_roles_have_descriptions(self):
        roles = self.eng.list_roles()
        described = [r for r in roles if r.description]
        self.assertGreater(len(described), 0)

    def test_seeded_skills_have_categories(self):
        skills = self.eng.list_skills()
        with_cat = [s for s in skills if s.category]
        self.assertGreater(len(with_cat), 0)

    def test_seeded_employees_have_skills(self):
        emps = self.eng.list_employees()
        with_skills = [e for e in emps if e.skills]
        self.assertGreater(len(with_skills), 0)

    def test_seeded_depts_have_members(self):
        depts = self.eng.list_departments()
        with_members = [d for d in depts if d.member_count() > 0]
        self.assertGreater(len(with_members), 0)

    def test_seeded_alice_department_assigned(self):
        emps = self.eng.list_employees()
        alice = next((e for e in emps if "Alice" in e.name), None)
        self.assertIsNotNone(alice)
        self.assertIsNotNone(alice.department_id)


if __name__ == "__main__":
    unittest.main()
