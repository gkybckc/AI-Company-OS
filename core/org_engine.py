"""
OrgEngine — Dynamic Organization Management for AI Company OS.

Provides full CRUD for departments, employees, roles, and skills
that the CEO manages from the dashboard.  All state is held in-memory
and is independent of the read-only DepartmentRegistry / WorkforceRegistry
so that existing engine APIs remain untouched.

Architecture reference: Constitution Chapter 5, §2 Core Components.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class OrgEngineError(Exception):
    """Base exception for all OrgEngine errors."""


class OrgDepartmentNotFoundError(OrgEngineError):
    """Raised when a department ID cannot be resolved."""


class OrgEmployeeNotFoundError(OrgEngineError):
    """Raised when an employee ID cannot be resolved."""


class OrgRoleNotFoundError(OrgEngineError):
    """Raised when a role ID cannot be resolved."""


class OrgSkillNotFoundError(OrgEngineError):
    """Raised when a skill ID cannot be resolved."""


class OrgInvalidStateError(OrgEngineError):
    """Raised when a requested state transition is not valid."""


class OrgDuplicateNameError(OrgEngineError):
    """Raised when a name that must be unique is already taken."""


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class OrgDepartment:
    """A dynamically managed department in the org chart."""

    id: str
    name: str
    capacity: int
    status: str                    # "active" | "inactive"
    director_id: Optional[str]     # OrgEmployee.id
    members: List[str]             # OrgEmployee IDs
    projects: List[str]            # project names (informational)
    created_at: datetime

    def is_active(self) -> bool:
        return self.status == "active"

    def is_inactive(self) -> bool:
        return self.status == "inactive"

    def member_count(self) -> int:
        return len(self.members)

    def workload_pct(self) -> float:
        """Rough workload estimate: members / capacity × 100."""
        if self.capacity <= 0:
            return 0.0
        return round(min(len(self.members) / self.capacity * 100, 100.0), 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "capacity": self.capacity,
            "status": self.status,
            "director_id": self.director_id,
            "members": list(self.members),
            "projects": list(self.projects),
            "member_count": self.member_count(),
            "workload_pct": self.workload_pct(),
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class OrgRole:
    """A custom employee role definition."""

    id: str
    name: str
    description: str
    created_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class OrgSkill:
    """A skill that employees can possess."""

    id: str
    name: str
    category: str
    created_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class OrgEmployee:
    """A dynamically managed employee in the org chart."""

    id: str
    name: str
    role_id: str                   # OrgRole.id
    department_id: Optional[str]   # OrgDepartment.id
    skills: List[str]              # skill names (free text or OrgSkill.name)
    status: str                    # "active" | "suspended" | "terminated"
    provider: str                  # e.g. "anthropic", "openai", "mock"
    current_task: Optional[str]
    previous_tasks: List[str]
    created_at: datetime

    def is_active(self) -> bool:
        return self.status == "active"

    def is_suspended(self) -> bool:
        return self.status == "suspended"

    def is_terminated(self) -> bool:
        return self.status == "terminated"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role_id": self.role_id,
            "department_id": self.department_id,
            "skills": list(self.skills),
            "status": self.status,
            "provider": self.provider,
            "current_task": self.current_task,
            "previous_tasks": list(self.previous_tasks),
            "created_at": self.created_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# OrgEngine
# ---------------------------------------------------------------------------

class OrgEngine:
    """
    Central engine for dynamic organization management.

    Maintains four independent stores: departments, employees, roles, and
    skills.  All mutation methods validate state before applying changes and
    raise descriptive exceptions on failure.
    """

    def __init__(self) -> None:
        self._departments: Dict[str, OrgDepartment] = {}
        self._employees: Dict[str, OrgEmployee] = {}
        self._roles: Dict[str, OrgRole] = {}
        self._skills: Dict[str, OrgSkill] = {}

    # ------------------------------------------------------------------
    # Role CRUD
    # ------------------------------------------------------------------

    def create_role(self, name: str, description: str = "") -> OrgRole:
        """Create a new role.  Name must be unique (case-insensitive)."""
        if not name or not name.strip():
            raise OrgEngineError("Role name cannot be empty.")
        name = name.strip()
        if self.find_role_by_name(name) is not None:
            raise OrgDuplicateNameError(f"A role named '{name}' already exists.")
        role = OrgRole(
            id=str(uuid.uuid4()),
            name=name,
            description=description.strip(),
            created_at=datetime.now(timezone.utc),
        )
        self._roles[role.id] = role
        return role

    def get_role(self, role_id: str) -> OrgRole:
        """Return the role with the given ID or raise OrgRoleNotFoundError."""
        role = self._roles.get(role_id)
        if role is None:
            raise OrgRoleNotFoundError(f"Role '{role_id}' not found.")
        return role

    def list_roles(self) -> List[OrgRole]:
        """Return all roles in creation order."""
        return list(self._roles.values())

    def find_role_by_name(self, name: str) -> Optional[OrgRole]:
        """Return the first role whose name matches (case-insensitive), or None."""
        name_lower = name.strip().lower()
        for role in self._roles.values():
            if role.name.lower() == name_lower:
                return role
        return None

    def edit_role(self, role_id: str, name: Optional[str] = None,
                  description: Optional[str] = None) -> OrgRole:
        """Edit an existing role's name or description."""
        role = self.get_role(role_id)
        if name is not None:
            name = name.strip()
            if not name:
                raise OrgEngineError("Role name cannot be empty.")
            existing = self.find_role_by_name(name)
            if existing is not None and existing.id != role_id:
                raise OrgDuplicateNameError(f"A role named '{name}' already exists.")
            role.name = name
        if description is not None:
            role.description = description.strip()
        return role

    def delete_role(self, role_id: str) -> OrgRole:
        """Remove a role from the registry and return it."""
        role = self.get_role(role_id)
        del self._roles[role_id]
        return role

    def role_count(self) -> int:
        return len(self._roles)

    # ------------------------------------------------------------------
    # Skill CRUD
    # ------------------------------------------------------------------

    def create_skill(self, name: str, category: str = "") -> OrgSkill:
        """Create a new skill.  Name must be unique (case-insensitive)."""
        if not name or not name.strip():
            raise OrgEngineError("Skill name cannot be empty.")
        name = name.strip()
        if self.find_skill_by_name(name) is not None:
            raise OrgDuplicateNameError(f"A skill named '{name}' already exists.")
        skill = OrgSkill(
            id=str(uuid.uuid4()),
            name=name,
            category=category.strip(),
            created_at=datetime.now(timezone.utc),
        )
        self._skills[skill.id] = skill
        return skill

    def get_skill(self, skill_id: str) -> OrgSkill:
        """Return the skill with the given ID or raise OrgSkillNotFoundError."""
        skill = self._skills.get(skill_id)
        if skill is None:
            raise OrgSkillNotFoundError(f"Skill '{skill_id}' not found.")
        return skill

    def list_skills(self) -> List[OrgSkill]:
        """Return all skills in creation order."""
        return list(self._skills.values())

    def find_skill_by_name(self, name: str) -> Optional[OrgSkill]:
        """Return the first skill whose name matches (case-insensitive), or None."""
        name_lower = name.strip().lower()
        for skill in self._skills.values():
            if skill.name.lower() == name_lower:
                return skill
        return None

    def edit_skill(self, skill_id: str, name: Optional[str] = None,
                   category: Optional[str] = None) -> OrgSkill:
        """Edit an existing skill."""
        skill = self.get_skill(skill_id)
        if name is not None:
            name = name.strip()
            if not name:
                raise OrgEngineError("Skill name cannot be empty.")
            existing = self.find_skill_by_name(name)
            if existing is not None and existing.id != skill_id:
                raise OrgDuplicateNameError(f"A skill named '{name}' already exists.")
            skill.name = name
        if category is not None:
            skill.category = category.strip()
        return skill

    def delete_skill(self, skill_id: str) -> OrgSkill:
        """Remove a skill from the registry and return it."""
        skill = self.get_skill(skill_id)
        del self._skills[skill_id]
        return skill

    def skill_count(self) -> int:
        return len(self._skills)

    # ------------------------------------------------------------------
    # Department CRUD
    # ------------------------------------------------------------------

    def create_department(self, name: str, capacity: int = 10,
                          director_id: Optional[str] = None) -> OrgDepartment:
        """Create a new department."""
        if not name or not name.strip():
            raise OrgEngineError("Department name cannot be empty.")
        name = name.strip()
        if capacity < 1:
            raise OrgEngineError("Department capacity must be at least 1.")
        if director_id is not None and director_id not in self._employees:
            raise OrgEmployeeNotFoundError(
                f"Director candidate '{director_id}' not found."
            )
        dept = OrgDepartment(
            id=str(uuid.uuid4()),
            name=name,
            capacity=capacity,
            status="active",
            director_id=director_id,
            members=[],
            projects=[],
            created_at=datetime.now(timezone.utc),
        )
        self._departments[dept.id] = dept
        return dept

    def get_department(self, dept_id: str) -> OrgDepartment:
        """Return the department or raise OrgDepartmentNotFoundError."""
        dept = self._departments.get(dept_id)
        if dept is None:
            raise OrgDepartmentNotFoundError(f"Department '{dept_id}' not found.")
        return dept

    def list_departments(self) -> List[OrgDepartment]:
        """Return all departments in creation order."""
        return list(self._departments.values())

    def list_active_departments(self) -> List[OrgDepartment]:
        """Return only active departments."""
        return [d for d in self._departments.values() if d.is_active()]

    def edit_department(self, dept_id: str, name: Optional[str] = None,
                        capacity: Optional[int] = None) -> OrgDepartment:
        """Edit an existing department's name and/or capacity."""
        dept = self.get_department(dept_id)
        if name is not None:
            name = name.strip()
            if not name:
                raise OrgEngineError("Department name cannot be empty.")
            dept.name = name
        if capacity is not None:
            if capacity < 1:
                raise OrgEngineError("Department capacity must be at least 1.")
            dept.capacity = capacity
        return dept

    def disable_department(self, dept_id: str) -> OrgDepartment:
        """Set department status to inactive."""
        dept = self.get_department(dept_id)
        if dept.status == "inactive":
            raise OrgInvalidStateError(
                f"Department '{dept.name}' is already inactive."
            )
        dept.status = "inactive"
        return dept

    def enable_department(self, dept_id: str) -> OrgDepartment:
        """Set department status back to active."""
        dept = self.get_department(dept_id)
        if dept.status == "active":
            raise OrgInvalidStateError(
                f"Department '{dept.name}' is already active."
            )
        dept.status = "active"
        return dept

    def assign_director(self, dept_id: str, emp_id: str) -> OrgDepartment:
        """Assign an employee as director of a department."""
        dept = self.get_department(dept_id)
        emp = self.get_employee(emp_id)
        if emp.is_terminated():
            raise OrgInvalidStateError(
                f"Terminated employee '{emp.name}' cannot be assigned as director."
            )
        dept.director_id = emp_id
        return dept

    def remove_director(self, dept_id: str) -> OrgDepartment:
        """Remove the director assignment from a department."""
        dept = self.get_department(dept_id)
        dept.director_id = None
        return dept

    def add_member(self, dept_id: str, emp_id: str) -> OrgDepartment:
        """Add an employee to a department's member list (idempotent)."""
        dept = self.get_department(dept_id)
        self.get_employee(emp_id)
        if emp_id not in dept.members:
            dept.members.append(emp_id)
        return dept

    def remove_member(self, dept_id: str, emp_id: str) -> OrgDepartment:
        """Remove an employee from a department's member list."""
        dept = self.get_department(dept_id)
        if emp_id in dept.members:
            dept.members.remove(emp_id)
        return dept

    def add_project(self, dept_id: str, project_name: str) -> OrgDepartment:
        """Associate a project name with a department (idempotent)."""
        dept = self.get_department(dept_id)
        if project_name not in dept.projects:
            dept.projects.append(project_name)
        return dept

    def remove_project(self, dept_id: str, project_name: str) -> OrgDepartment:
        """Remove a project association from a department."""
        dept = self.get_department(dept_id)
        if project_name in dept.projects:
            dept.projects.remove(project_name)
        return dept

    def department_count(self) -> int:
        return len(self._departments)

    def delete_department(self, dept_id: str) -> OrgDepartment:
        """Permanently remove a department."""
        dept = self.get_department(dept_id)
        del self._departments[dept_id]
        return dept

    # ------------------------------------------------------------------
    # Employee CRUD
    # ------------------------------------------------------------------

    def create_employee(self, name: str, role_id: str,
                        department_id: Optional[str] = None,
                        skills: Optional[List[str]] = None,
                        provider: str = "mock") -> OrgEmployee:
        """Hire a new employee."""
        if not name or not name.strip():
            raise OrgEngineError("Employee name cannot be empty.")
        name = name.strip()
        self.get_role(role_id)
        if department_id is not None:
            self.get_department(department_id)
        emp = OrgEmployee(
            id=str(uuid.uuid4()),
            name=name,
            role_id=role_id,
            department_id=department_id,
            skills=list(skills or []),
            status="active",
            provider=provider.strip() or "mock",
            current_task=None,
            previous_tasks=[],
            created_at=datetime.now(timezone.utc),
        )
        self._employees[emp.id] = emp
        if department_id is not None:
            self.add_member(department_id, emp.id)
        return emp

    def get_employee(self, emp_id: str) -> OrgEmployee:
        """Return the employee or raise OrgEmployeeNotFoundError."""
        emp = self._employees.get(emp_id)
        if emp is None:
            raise OrgEmployeeNotFoundError(f"Employee '{emp_id}' not found.")
        return emp

    def list_employees(self) -> List[OrgEmployee]:
        """Return all employees in creation order."""
        return list(self._employees.values())

    def list_active_employees(self) -> List[OrgEmployee]:
        """Return only active employees."""
        return [e for e in self._employees.values() if e.is_active()]

    def edit_employee(self, emp_id: str, name: Optional[str] = None,
                      role_id: Optional[str] = None,
                      provider: Optional[str] = None) -> OrgEmployee:
        """Edit employee name, role, or provider."""
        emp = self.get_employee(emp_id)
        if emp.is_terminated():
            raise OrgInvalidStateError(
                f"Terminated employee '{emp.name}' cannot be edited."
            )
        if name is not None:
            name = name.strip()
            if not name:
                raise OrgEngineError("Employee name cannot be empty.")
            emp.name = name
        if role_id is not None:
            self.get_role(role_id)
            emp.role_id = role_id
        if provider is not None:
            emp.provider = provider.strip() or "mock"
        return emp

    def transfer_employee(self, emp_id: str,
                          new_dept_id: str) -> OrgEmployee:
        """Move an employee to a different department."""
        emp = self.get_employee(emp_id)
        if emp.is_terminated():
            raise OrgInvalidStateError(
                f"Terminated employee '{emp.name}' cannot be transferred."
            )
        new_dept = self.get_department(new_dept_id)
        old_dept_id = emp.department_id
        if old_dept_id is not None:
            self.remove_member(old_dept_id, emp_id)
        emp.department_id = new_dept_id
        self.add_member(new_dept_id, emp_id)
        return emp

    def suspend_employee(self, emp_id: str) -> OrgEmployee:
        """Suspend an active employee."""
        emp = self.get_employee(emp_id)
        if emp.is_terminated():
            raise OrgInvalidStateError(
                f"Terminated employee '{emp.name}' cannot be suspended."
            )
        if emp.is_suspended():
            raise OrgInvalidStateError(
                f"Employee '{emp.name}' is already suspended."
            )
        emp.status = "suspended"
        return emp

    def reactivate_employee(self, emp_id: str) -> OrgEmployee:
        """Reactivate a suspended employee."""
        emp = self.get_employee(emp_id)
        if not emp.is_suspended():
            raise OrgInvalidStateError(
                f"Employee '{emp.name}' is not suspended."
            )
        emp.status = "active"
        return emp

    def terminate_employee(self, emp_id: str) -> OrgEmployee:
        """Permanently terminate an employee."""
        emp = self.get_employee(emp_id)
        if emp.is_terminated():
            raise OrgInvalidStateError(
                f"Employee '{emp.name}' is already terminated."
            )
        emp.status = "terminated"
        if emp.department_id is not None:
            self.remove_member(emp.department_id, emp_id)
            emp.department_id = None
        return emp

    def assign_task(self, emp_id: str, task_name: str) -> OrgEmployee:
        """Assign a task to an employee."""
        emp = self.get_employee(emp_id)
        if not emp.is_active():
            raise OrgInvalidStateError(
                f"Cannot assign task to employee with status '{emp.status}'."
            )
        emp.current_task = task_name
        return emp

    def complete_task(self, emp_id: str) -> OrgEmployee:
        """Mark the employee's current task as complete."""
        emp = self.get_employee(emp_id)
        if emp.current_task:
            emp.previous_tasks.append(emp.current_task)
            emp.current_task = None
        return emp

    def add_skill_to_employee(self, emp_id: str, skill_name: str) -> OrgEmployee:
        """Add a skill to an employee's skill list (idempotent)."""
        emp = self.get_employee(emp_id)
        if emp.is_terminated():
            raise OrgInvalidStateError(
                f"Cannot add skill to terminated employee '{emp.name}'."
            )
        if skill_name not in emp.skills:
            emp.skills.append(skill_name)
        return emp

    def remove_skill_from_employee(self, emp_id: str,
                                   skill_name: str) -> OrgEmployee:
        """Remove a skill from an employee's skill list."""
        emp = self.get_employee(emp_id)
        if skill_name in emp.skills:
            emp.skills.remove(skill_name)
        return emp

    def employee_count(self) -> int:
        return len(self._employees)

    def delete_employee(self, emp_id: str) -> OrgEmployee:
        """Permanently remove an employee record."""
        emp = self.get_employee(emp_id)
        if emp.department_id is not None:
            self.remove_member(emp.department_id, emp_id)
        del self._employees[emp_id]
        return emp

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def employees_in_department(self, dept_id: str) -> List[OrgEmployee]:
        """Return all employees assigned to a given department."""
        self.get_department(dept_id)
        return [e for e in self._employees.values()
                if e.department_id == dept_id]

    def director_of(self, dept_id: str) -> Optional[OrgEmployee]:
        """Return the director employee of a department, or None."""
        dept = self.get_department(dept_id)
        if dept.director_id is None:
            return None
        return self._employees.get(dept.director_id)

    def role_name(self, role_id: str) -> str:
        """Return the display name of a role, or its ID if not found."""
        role = self._roles.get(role_id)
        return role.name if role else role_id

    def department_name(self, dept_id: str) -> str:
        """Return the display name of a department, or its ID if not found."""
        dept = self._departments.get(dept_id)
        return dept.name if dept else (dept_id or "—")

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def statistics(self) -> Dict[str, Any]:
        """Return aggregate org statistics."""
        employees = self.list_employees()
        departments = self.list_departments()
        return {
            "total_departments": len(departments),
            "active_departments": sum(1 for d in departments if d.is_active()),
            "inactive_departments": sum(1 for d in departments if not d.is_active()),
            "total_employees": len(employees),
            "active_employees": sum(1 for e in employees if e.is_active()),
            "suspended_employees": sum(1 for e in employees if e.is_suspended()),
            "terminated_employees": sum(1 for e in employees if e.is_terminated()),
            "total_roles": len(self._roles),
            "total_skills": len(self._skills),
            "departments_with_directors": sum(
                1 for d in departments if d.director_id is not None
            ),
        }
