"""Organization routes — /org pages and /api/org/* CRUD endpoints."""

from typing import Dict

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from apps.dashboard.services.organization_service import OrganizationService
from apps.dashboard.state import DashboardState


def make_organization_router(templates: Jinja2Templates) -> APIRouter:
    router = APIRouter()

    # ------------------------------------------------------------------
    # HTML pages
    # ------------------------------------------------------------------

    @router.get("/org", response_class=HTMLResponse)
    async def org_page(request: Request) -> HTMLResponse:
        state = DashboardState.get()
        employees = state.workforce_registry.list_all()
        departments = state.department_registry.list_all()
        org_data = []
        for dept in departments:
            dept_employees = [
                e for e in employees if e.department.value == dept.type.value
            ]
            org_data.append({"department": dept, "employees": dept_employees})
        return templates.TemplateResponse(
            request,
            "org.html",
            {
                "page": "org",
                "company_name": "AI Company OS",
                "org_data": org_data,
                "total_employees": len(employees),
                "total_departments": len(departments),
            },
        )

    @router.get("/org/departments", response_class=HTMLResponse)
    async def org_departments_page(request: Request) -> HTMLResponse:
        svc = OrganizationService(DashboardState.get())
        ctx = svc.get_departments_page_data()
        ctx.update({"page": "org_departments", "company_name": "AI Company OS"})
        return templates.TemplateResponse(request, "org/departments.html", ctx)

    @router.get("/org/employees", response_class=HTMLResponse)
    async def org_employees_page(request: Request) -> HTMLResponse:
        svc = OrganizationService(DashboardState.get())
        ctx = svc.get_employees_page_data()
        ctx.update({"page": "org_employees", "company_name": "AI Company OS"})
        return templates.TemplateResponse(request, "org/employees.html", ctx)

    @router.get("/org/roles", response_class=HTMLResponse)
    async def org_roles_page(request: Request) -> HTMLResponse:
        svc = OrganizationService(DashboardState.get())
        ctx = svc.get_roles_page_data()
        ctx.update({"page": "org_roles", "company_name": "AI Company OS"})
        return templates.TemplateResponse(request, "org/roles.html", ctx)

    @router.get("/org/skills", response_class=HTMLResponse)
    async def org_skills_page(request: Request) -> HTMLResponse:
        svc = OrganizationService(DashboardState.get())
        ctx = svc.get_skills_page_data()
        ctx.update({"page": "org_skills", "company_name": "AI Company OS"})
        return templates.TemplateResponse(request, "org/skills.html", ctx)

    # ------------------------------------------------------------------
    # Departments API
    # ------------------------------------------------------------------

    @router.get("/api/org/departments")
    async def api_org_departments() -> JSONResponse:
        return JSONResponse(
            OrganizationService(DashboardState.get()).list_departments_api()
        )

    @router.post("/api/org/departments")
    async def api_org_departments_create(request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"success": False, "error": "Geçersiz JSON."}, status_code=400)
        name = str(data.get("name") or "").strip()
        if not name:
            return JSONResponse(
                {"success": False, "error": "Departman adı gerekli."}, status_code=400
            )
        capacity = int(data.get("capacity") or 10)
        try:
            dept = OrganizationService(DashboardState.get()).create_department(name, capacity)
            return JSONResponse({"success": True, "department": dept.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.put("/api/org/departments/{dept_id}")
    async def api_org_departments_edit(dept_id: str, request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"success": False, "error": "Geçersiz JSON."}, status_code=400)
        try:
            name = data.get("name") or None
            capacity = int(data["capacity"]) if "capacity" in data else None
            dept = OrganizationService(DashboardState.get()).edit_department(
                dept_id, name=name, capacity=capacity
            )
            return JSONResponse({"success": True, "department": dept.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/org/departments/{dept_id}/disable")
    async def api_org_departments_disable(dept_id: str) -> JSONResponse:
        try:
            dept = OrganizationService(DashboardState.get()).disable_department(dept_id)
            return JSONResponse({"success": True, "department": dept.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/org/departments/{dept_id}/enable")
    async def api_org_departments_enable(dept_id: str) -> JSONResponse:
        try:
            dept = OrganizationService(DashboardState.get()).enable_department(dept_id)
            return JSONResponse({"success": True, "department": dept.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/org/departments/{dept_id}/director")
    async def api_org_departments_assign_director(
        dept_id: str, request: Request
    ) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"success": False, "error": "Geçersiz JSON."}, status_code=400)
        emp_id = str(data.get("employee_id") or "").strip()
        if not emp_id:
            return JSONResponse(
                {"success": False, "error": "employee_id gerekli."}, status_code=400
            )
        try:
            dept = OrganizationService(DashboardState.get()).assign_director(
                dept_id, emp_id
            )
            return JSONResponse({"success": True, "department": dept.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    # ------------------------------------------------------------------
    # Employees API
    # ------------------------------------------------------------------

    @router.get("/api/org/employees")
    async def api_org_employees() -> JSONResponse:
        return JSONResponse(
            OrganizationService(DashboardState.get()).list_employees_api()
        )

    @router.post("/api/org/employees")
    async def api_org_employees_create(request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"success": False, "error": "Geçersiz JSON."}, status_code=400)
        name = str(data.get("name") or "").strip()
        role_id = str(data.get("role_id") or "").strip()
        if not name:
            return JSONResponse(
                {"success": False, "error": "Çalışan adı gerekli."}, status_code=400
            )
        if not role_id:
            return JSONResponse(
                {"success": False, "error": "Rol gerekli."}, status_code=400
            )
        try:
            emp = OrganizationService(DashboardState.get()).create_employee(
                name, role_id,
                data.get("department_id") or None,
                data.get("skills") or [],
                str(data.get("provider") or "mock").strip(),
            )
            return JSONResponse({"success": True, "employee": emp.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.put("/api/org/employees/{emp_id}")
    async def api_org_employees_edit(emp_id: str, request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"success": False, "error": "Geçersiz JSON."}, status_code=400)
        try:
            emp = OrganizationService(DashboardState.get()).edit_employee(
                emp_id,
                name=data.get("name"),
                role_id=data.get("role_id"),
                provider=data.get("provider"),
            )
            return JSONResponse({"success": True, "employee": emp.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/org/employees/{emp_id}/transfer")
    async def api_org_employees_transfer(emp_id: str, request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"success": False, "error": "Geçersiz JSON."}, status_code=400)
        new_dept_id = str(data.get("department_id") or "").strip()
        if not new_dept_id:
            return JSONResponse(
                {"success": False, "error": "department_id gerekli."}, status_code=400
            )
        try:
            emp = OrganizationService(DashboardState.get()).transfer_employee(
                emp_id, new_dept_id
            )
            return JSONResponse({"success": True, "employee": emp.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/org/employees/{emp_id}/suspend")
    async def api_org_employees_suspend(emp_id: str) -> JSONResponse:
        try:
            emp = OrganizationService(DashboardState.get()).suspend_employee(emp_id)
            return JSONResponse({"success": True, "employee": emp.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/org/employees/{emp_id}/reactivate")
    async def api_org_employees_reactivate(emp_id: str) -> JSONResponse:
        try:
            emp = OrganizationService(DashboardState.get()).reactivate_employee(emp_id)
            return JSONResponse({"success": True, "employee": emp.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/org/employees/{emp_id}/terminate")
    async def api_org_employees_terminate(emp_id: str) -> JSONResponse:
        try:
            emp = OrganizationService(DashboardState.get()).terminate_employee(emp_id)
            return JSONResponse({"success": True, "employee": emp.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/org/employees/{emp_id}/skills")
    async def api_org_employees_add_skill(emp_id: str, request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"success": False, "error": "Geçersiz JSON."}, status_code=400)
        skill_name = str(data.get("skill") or "").strip()
        if not skill_name:
            return JSONResponse(
                {"success": False, "error": "skill gerekli."}, status_code=400
            )
        try:
            emp = OrganizationService(DashboardState.get()).add_skill_to_employee(
                emp_id, skill_name
            )
            return JSONResponse({"success": True, "employee": emp.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    # ------------------------------------------------------------------
    # Roles API
    # ------------------------------------------------------------------

    @router.get("/api/org/roles")
    async def api_org_roles() -> JSONResponse:
        return JSONResponse(
            OrganizationService(DashboardState.get()).list_roles_api()
        )

    @router.post("/api/org/roles")
    async def api_org_roles_create(request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"success": False, "error": "Geçersiz JSON."}, status_code=400)
        name = str(data.get("name") or "").strip()
        if not name:
            return JSONResponse(
                {"success": False, "error": "Rol adı gerekli."}, status_code=400
            )
        try:
            role = OrganizationService(DashboardState.get()).create_role(
                name, str(data.get("description") or "").strip()
            )
            return JSONResponse({"success": True, "role": role.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.put("/api/org/roles/{role_id}")
    async def api_org_roles_edit(role_id: str, request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"success": False, "error": "Geçersiz JSON."}, status_code=400)
        try:
            role = OrganizationService(DashboardState.get()).edit_role(
                role_id,
                name=data.get("name"),
                description=data.get("description"),
            )
            return JSONResponse({"success": True, "role": role.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    # ------------------------------------------------------------------
    # Skills API
    # ------------------------------------------------------------------

    @router.get("/api/org/skills")
    async def api_org_skills() -> JSONResponse:
        return JSONResponse(
            OrganizationService(DashboardState.get()).list_skills_api()
        )

    @router.post("/api/org/skills")
    async def api_org_skills_create(request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"success": False, "error": "Geçersiz JSON."}, status_code=400)
        name = str(data.get("name") or "").strip()
        if not name:
            return JSONResponse(
                {"success": False, "error": "Yetenek adı gerekli."}, status_code=400
            )
        try:
            skill = OrganizationService(DashboardState.get()).create_skill(
                name, str(data.get("category") or "").strip()
            )
            return JSONResponse({"success": True, "skill": skill.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.put("/api/org/skills/{skill_id}")
    async def api_org_skills_edit(skill_id: str, request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"success": False, "error": "Geçersiz JSON."}, status_code=400)
        try:
            skill = OrganizationService(DashboardState.get()).edit_skill(
                skill_id,
                name=data.get("name"),
                category=data.get("category"),
            )
            return JSONResponse({"success": True, "skill": skill.to_dict()})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    @router.get("/api/org/statistics")
    async def api_org_statistics() -> JSONResponse:
        return JSONResponse(OrganizationService(DashboardState.get()).statistics())

    return router
