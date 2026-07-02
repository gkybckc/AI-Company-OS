"""
Organization service for the AI Company OS dashboard.

Wraps org_engine CRUD operations for departments, employees, roles, skills.
"""

from typing import Any, Dict, List, Optional

from apps.dashboard.state import DashboardState


class OrganizationService:
    """CRUD service for the OrgEngine, used by org route handlers."""

    def __init__(self, state: DashboardState) -> None:
        self._state = state

    @property
    def _org(self):
        return self._state.org_engine

    # ------------------------------------------------------------------
    # Read helpers for page templates
    # ------------------------------------------------------------------

    def get_departments_page_data(self) -> Dict[str, Any]:
        departments = self._org.list_departments()
        employees = self._org.list_employees()
        roles = self._org.list_roles()
        emp_map = {e.id: e for e in employees}

        dept_data = []
        for dept in departments:
            director = emp_map.get(dept.director_id) if dept.director_id else None
            members = [emp_map[m] for m in dept.members if m in emp_map]
            dept_data.append({"dept": dept, "director": director, "members": members})

        return {
            "dept_data": dept_data,
            "employees": employees,
            "roles": roles,
            "stats": self._org.statistics(),
        }

    def get_employees_page_data(self) -> Dict[str, Any]:
        employees = self._org.list_employees()
        departments = self._org.list_departments()
        roles = self._org.list_roles()
        dept_map = {d.id: d for d in departments}
        role_map = {r.id: r for r in roles}

        emp_data = []
        for emp in employees:
            dept = dept_map.get(emp.department_id) if emp.department_id else None
            role = role_map.get(emp.role_id)
            emp_data.append({"emp": emp, "dept": dept, "role": role})

        return {
            "emp_data": emp_data,
            "departments": departments,
            "roles": roles,
            "skills": self._org.list_skills(),
            "stats": self._org.statistics(),
        }

    def get_roles_page_data(self) -> Dict[str, Any]:
        roles = self._org.list_roles()
        employees = self._org.list_employees()
        role_counts: Dict[str, int] = {}
        for emp in employees:
            role_counts[emp.role_id] = role_counts.get(emp.role_id, 0) + 1

        return {
            "role_data": [
                {"role": r, "employee_count": role_counts.get(r.id, 0)}
                for r in roles
            ],
            "stats": self._org.statistics(),
        }

    def get_skills_page_data(self) -> Dict[str, Any]:
        skills = self._org.list_skills()
        employees = self._org.list_employees()
        skill_counts: Dict[str, int] = {}
        for emp in employees:
            for sk in emp.skills:
                skill_counts[sk] = skill_counts.get(sk, 0) + 1

        return {
            "skill_data": [
                {"skill": s, "employee_count": skill_counts.get(s.name, 0)}
                for s in skills
            ],
            "stats": self._org.statistics(),
        }

    # ------------------------------------------------------------------
    # Department CRUD
    # ------------------------------------------------------------------

    def list_departments_api(self) -> List[Dict[str, Any]]:
        return [d.to_dict() for d in self._org.list_departments()]

    def create_department(self, name: str, capacity: int) -> Any:
        return self._org.create_department(name, capacity)

    def edit_department(
        self, dept_id: str, name: Optional[str], capacity: Optional[int]
    ) -> Any:
        return self._org.edit_department(dept_id, name=name, capacity=capacity)

    def disable_department(self, dept_id: str) -> Any:
        return self._org.disable_department(dept_id)

    def enable_department(self, dept_id: str) -> Any:
        return self._org.enable_department(dept_id)

    def assign_director(self, dept_id: str, emp_id: str) -> Any:
        return self._org.assign_director(dept_id, emp_id)

    # ------------------------------------------------------------------
    # Employee CRUD
    # ------------------------------------------------------------------

    def list_employees_api(self) -> List[Dict[str, Any]]:
        result = []
        for emp in self._org.list_employees():
            d = emp.to_dict()
            d["role_name"] = self._org.role_name(emp.role_id)
            d["department_name"] = self._org.department_name(
                emp.department_id or ""
            )
            result.append(d)
        return result

    def create_employee(
        self,
        name: str,
        role_id: str,
        department_id: Optional[str],
        skills: List[str],
        provider: str,
    ) -> Any:
        return self._org.create_employee(name, role_id, department_id, skills, provider)

    def edit_employee(
        self,
        emp_id: str,
        name: Optional[str],
        role_id: Optional[str],
        provider: Optional[str],
    ) -> Any:
        return self._org.edit_employee(
            emp_id, name=name, role_id=role_id, provider=provider
        )

    def transfer_employee(self, emp_id: str, new_dept_id: str) -> Any:
        return self._org.transfer_employee(emp_id, new_dept_id)

    def suspend_employee(self, emp_id: str) -> Any:
        return self._org.suspend_employee(emp_id)

    def reactivate_employee(self, emp_id: str) -> Any:
        return self._org.reactivate_employee(emp_id)

    def terminate_employee(self, emp_id: str) -> Any:
        return self._org.terminate_employee(emp_id)

    def add_skill_to_employee(self, emp_id: str, skill_name: str) -> Any:
        return self._org.add_skill_to_employee(emp_id, skill_name)

    # ------------------------------------------------------------------
    # Role CRUD
    # ------------------------------------------------------------------

    def list_roles_api(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._org.list_roles()]

    def create_role(self, name: str, description: str) -> Any:
        return self._org.create_role(name, description)

    def edit_role(
        self,
        role_id: str,
        name: Optional[str],
        description: Optional[str],
    ) -> Any:
        return self._org.edit_role(role_id, name=name, description=description)

    # ------------------------------------------------------------------
    # Skill CRUD
    # ------------------------------------------------------------------

    def list_skills_api(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._org.list_skills()]

    def create_skill(self, name: str, category: str) -> Any:
        return self._org.create_skill(name, category)

    def edit_skill(
        self,
        skill_id: str,
        name: Optional[str],
        category: Optional[str],
    ) -> Any:
        return self._org.edit_skill(skill_id, name=name, category=category)

    def statistics(self) -> Dict[str, Any]:
        return self._org.statistics()
