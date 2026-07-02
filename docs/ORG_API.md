# Organisation API

Feature 20 — Dynamic Organisation Management  
Base path: `/api/org`

All write endpoints return `{"success": true, ...}` on success or `{"success": false, "error": "<message>"}` with HTTP 400 on failure.

---

## Departments

### `GET /api/org/departments`
List all departments.

**Response** — `200 OK`
```json
[
  {
    "id": "dept-abc123",
    "name": "Backend Engineering",
    "capacity": 10,
    "status": "active",
    "director_id": "emp-xyz",
    "members": ["emp-xyz", "emp-abc"],
    "projects": [],
    "member_count": 2,
    "workload_pct": 20.0,
    "created_at": "2026-07-01T10:00:00"
  }
]
```

---

### `POST /api/org/departments`
Create a new department.

**Body**
```json
{ "name": "Marketing", "capacity": 8 }
```
`capacity` is optional (default 10). `name` is required and must be unique.

**Response** — `200 OK`
```json
{ "success": true, "department": { ... } }
```

---

### `PUT /api/org/departments/{dept_id}`
Edit an existing department's name or capacity.

**Body** — all fields optional
```json
{ "name": "Growth Team", "capacity": 12 }
```

**Response** — `200 OK`
```json
{ "success": true, "department": { ... } }
```

---

### `POST /api/org/departments/{dept_id}/disable`
Set department status to `"inactive"`. Fails if already inactive.

**Response** — `200 OK`
```json
{ "success": true, "department": { ... } }
```

---

### `POST /api/org/departments/{dept_id}/enable`
Set department status to `"active"`. Fails if already active.

**Response** — `200 OK`
```json
{ "success": true, "department": { ... } }
```

---

### `POST /api/org/departments/{dept_id}/director`
Assign a director to a department. The employee must be active.

**Body**
```json
{ "employee_id": "emp-xyz" }
```

**Response** — `200 OK`
```json
{ "success": true, "department": { ... } }
```

---

## Employees

### `GET /api/org/employees`
List all employees. Each entry is augmented with `role_name` and `department_name` for display.

**Response** — `200 OK`
```json
[
  {
    "id": "emp-abc",
    "name": "Alice Chen",
    "role_id": "role-xyz",
    "role_name": "Backend Agent",
    "department_id": "dept-abc",
    "department_name": "Backend Engineering",
    "skills": ["Python", "FastAPI"],
    "status": "active",
    "provider": "anthropic",
    "current_task": "Build REST API layer",
    "previous_tasks": ["Design core architecture"],
    "created_at": "2026-07-01T10:00:00"
  }
]
```

---

### `POST /api/org/employees`
Hire a new employee.

**Body**
```json
{
  "name": "Zeynep Kaya",
  "role_id": "role-xyz",
  "department_id": "dept-abc",
  "skills": ["Python"],
  "provider": "anthropic"
}
```
`department_id`, `skills`, and `provider` are optional. `provider` defaults to `"mock"`.

**Response** — `200 OK`
```json
{ "success": true, "employee": { ... } }
```

---

### `PUT /api/org/employees/{emp_id}`
Edit an employee's name, role, or provider. Cannot edit a terminated employee.

**Body** — all fields optional
```json
{ "name": "Alice Smith", "role_id": "role-new", "provider": "openai" }
```

**Response** — `200 OK`
```json
{ "success": true, "employee": { ... } }
```

---

### `POST /api/org/employees/{emp_id}/transfer`
Transfer an active employee to a different department.

**Body**
```json
{ "department_id": "dept-new" }
```

**Response** — `200 OK`
```json
{ "success": true, "employee": { ... } }
```

---

### `POST /api/org/employees/{emp_id}/suspend`
Suspend an active employee. Cannot suspend an already-suspended or terminated employee.

**Response** — `200 OK`
```json
{ "success": true, "employee": { ... } }
```

---

### `POST /api/org/employees/{emp_id}/reactivate`
Reactivate a suspended employee.

**Response** — `200 OK`
```json
{ "success": true, "employee": { ... } }
```

---

### `POST /api/org/employees/{emp_id}/terminate`
Permanently terminate an employee. Removes them from their department. Cannot be reversed.

**Response** — `200 OK`
```json
{ "success": true, "employee": { ... } }
```

---

### `POST /api/org/employees/{emp_id}/skills`
Add a skill to an employee's skill list (idempotent).

**Body**
```json
{ "skill": "Blender" }
```

**Response** — `200 OK`
```json
{ "success": true, "employee": { ... } }
```

---

## Roles

### `GET /api/org/roles`
List all roles.

**Response** — `200 OK`
```json
[
  {
    "id": "role-abc",
    "name": "Backend Agent",
    "description": "Builds server-side APIs",
    "created_at": "2026-07-01T10:00:00"
  }
]
```

---

### `POST /api/org/roles`
Create a new role.

**Body**
```json
{ "name": "Unity Engineer", "description": "Builds Unity-based simulations" }
```
`description` is optional. `name` must be unique (case-insensitive).

**Response** — `200 OK`
```json
{ "success": true, "role": { ... } }
```

---

### `PUT /api/org/roles/{role_id}`
Edit a role's name or description.

**Body** — all fields optional
```json
{ "name": "Game Engineer", "description": "Updated description" }
```

**Response** — `200 OK`
```json
{ "success": true, "role": { ... } }
```

---

## Skills

### `GET /api/org/skills`
List all skills.

**Response** — `200 OK`
```json
[
  {
    "id": "skill-abc",
    "name": "Python",
    "category": "Programming",
    "created_at": "2026-07-01T10:00:00"
  }
]
```

---

### `POST /api/org/skills`
Create a new skill.

**Body**
```json
{ "name": "Blender", "category": "3D" }
```
`category` is optional. `name` must be unique (case-insensitive).

**Response** — `200 OK`
```json
{ "success": true, "skill": { ... } }
```

---

### `PUT /api/org/skills/{skill_id}`
Edit a skill's name or category.

**Body** — all fields optional
```json
{ "name": "Blender 4", "category": "Design" }
```

**Response** — `200 OK`
```json
{ "success": true, "skill": { ... } }
```

---

## Statistics

### `GET /api/org/statistics`
Return aggregate organisation statistics.

**Response** — `200 OK`
```json
{
  "total_departments": 4,
  "active_departments": 3,
  "inactive_departments": 1,
  "total_employees": 12,
  "active_employees": 10,
  "suspended_employees": 1,
  "terminated_employees": 1,
  "total_roles": 6,
  "total_skills": 10,
  "departments_with_directors": 3
}
```

---

## Error Format

All error responses use HTTP 400:
```json
{ "success": false, "error": "Human-readable message describing the problem." }
```

Common error classes from `core.org_engine`:
| Exception | Meaning |
|---|---|
| `OrgDepartmentNotFoundError` | `dept_id` does not exist |
| `OrgEmployeeNotFoundError` | `emp_id` does not exist |
| `OrgRoleNotFoundError` | `role_id` does not exist |
| `OrgSkillNotFoundError` | `skill_id` does not exist |
| `OrgInvalidStateError` | Operation not allowed in current state |
| `OrgDuplicateNameError` | Name already exists (case-insensitive) |
