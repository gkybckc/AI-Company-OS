"""
Feature 20 Demo — Dynamic Organization Engine

Demonstrates the full lifecycle of the OrgEngine:
  • Create roles and skills
  • Create departments with directors
  • Hire, transfer, suspend, reactivate, and terminate employees
  • Assign tasks and track previous tasks
  • Query statistics

Run with:
    .venv\\Scripts\\python.exe examples/demo_org.py
"""

from core.org_engine import OrgEngine


def separator(char="-", width=64):
    print(char * width)


def main():
    print("=" * 64)
    print("  AI Company OS — Dynamic Organization Engine Demo")
    print("  Feature 20: Runtime CRUD for Departments, Roles & Skills")
    print("=" * 64)

    eng = OrgEngine()

    # ── 1. Roles ─────────────────────────────────────────────────────
    separator()
    print("[1] Creating roles")
    r_backend  = eng.create_role("Backend Agent",    "Builds server-side APIs and core logic")
    r_frontend = eng.create_role("Frontend Agent",   "Builds UI templates and client-side behaviour")
    r_qa       = eng.create_role("QA Engineer",      "Writes and runs test suites")
    r_devops   = eng.create_role("DevOps Engineer",  "Manages CI/CD, infra, and deployments")
    r_research = eng.create_role("Research Analyst", "Gathers data and produces technical reports")
    print(f"  Roles created : {eng.role_count()}")
    for role in eng.list_roles():
        print(f"    [{role.id[:8]}] {role.name}")

    # ── 2. Skills ────────────────────────────────────────────────────
    separator()
    print("[2] Creating skills")
    eng.create_skill("Python",     "Programming")
    eng.create_skill("FastAPI",    "Programming")
    eng.create_skill("TypeScript", "Programming")
    eng.create_skill("React",      "Programming")
    eng.create_skill("Docker",     "DevOps")
    eng.create_skill("CI/CD",      "DevOps")
    eng.create_skill("Figma",      "Design")
    eng.create_skill("SEO",        "Marketing")
    print(f"  Skills created : {eng.skill_count()}")

    # ── 3. Departments ───────────────────────────────────────────────
    separator()
    print("[3] Creating departments")
    d_backend  = eng.create_department("Backend Engineering",  capacity=8)
    d_frontend = eng.create_department("Frontend Engineering", capacity=6)
    d_qa       = eng.create_department("Quality Assurance",    capacity=5)
    d_devops   = eng.create_department("DevOps",               capacity=4)
    print(f"  Departments created : {eng.department_count()}")

    # ── 4. Employees ─────────────────────────────────────────────────
    separator()
    print("[4] Hiring employees")
    alice = eng.create_employee("Alice Chen",  r_backend.id,  d_backend.id,
                                ["Python", "FastAPI"], "anthropic")
    bob   = eng.create_employee("Bob Kumar",   r_backend.id,  d_backend.id,
                                ["Python"], "anthropic")
    carol = eng.create_employee("Carol Diaz",  r_frontend.id, d_frontend.id,
                                ["TypeScript", "React", "Figma"], "openai")
    dave  = eng.create_employee("Dave Park",   r_qa.id,       d_qa.id,
                                ["Python", "CI/CD"], "anthropic")
    eve   = eng.create_employee("Eve Singh",   r_devops.id,   d_devops.id,
                                ["Docker", "CI/CD"], "openai")

    print(f"  Employees hired : {eng.employee_count()}")

    # ── 5. Directors ─────────────────────────────────────────────────
    separator()
    print("[5] Assigning directors")
    eng.assign_director(d_backend.id,  alice.id)
    eng.assign_director(d_frontend.id, carol.id)
    eng.assign_director(d_qa.id,       dave.id)
    eng.assign_director(d_devops.id,   eve.id)
    for dept in eng.list_departments():
        director = eng.director_of(dept.id)
        dname = director.name if director else "—"
        print(f"  {dept.name:<26} director: {dname}")

    # ── 6. Tasks ─────────────────────────────────────────────────────
    separator()
    print("[6] Assigning and completing tasks")
    eng.assign_task(alice.id, "Design core architecture")
    eng.assign_task(bob.id,   "Implement Memory Engine")
    print(f"  Alice's current task : {alice.current_task}")
    print(f"  Bob's current task   : {bob.current_task}")

    eng.complete_task(alice.id)
    eng.assign_task(alice.id, "Build REST API layer")
    print(f"  Alice previous tasks : {alice.previous_tasks}")
    print(f"  Alice new task       : {alice.current_task}")

    # ── 7. Transfer ──────────────────────────────────────────────────
    separator()
    print("[7] Transferring Bob to Quality Assurance")
    print(f"  Bob department before : {eng.department_name(bob.department_id or '')}")
    eng.transfer_employee(bob.id, d_qa.id)
    print(f"  Bob department after  : {eng.department_name(bob.department_id or '')}")
    print(f"  QA members now        : {d_qa.member_count()}")

    # ── 8. Suspend / Reactivate ───────────────────────────────────────
    separator()
    print("[8] Suspend and reactivate Carol")
    eng.suspend_employee(carol.id)
    print(f"  Carol status after suspend    : {carol.status}")
    eng.reactivate_employee(carol.id)
    print(f"  Carol status after reactivate : {carol.status}")

    # ── 9. Terminate ─────────────────────────────────────────────────
    separator()
    r_temp = eng.create_role("Temp Contractor")
    temp   = eng.create_employee("Zara Moss", r_temp.id)
    print("[9] Terminate temp contractor Zara")
    eng.terminate_employee(temp.id)
    print(f"  Zara status     : {temp.status}")
    print(f"  Zara department : {temp.department_id}")   # None after termination

    # ── 10. Disable / Re-enable department ───────────────────────────
    separator()
    print("[10] Disable and re-enable DevOps department")
    print(f"  DevOps status before : {d_devops.status}")
    eng.disable_department(d_devops.id)
    print(f"  DevOps status after disable : {d_devops.status}")
    eng.enable_department(d_devops.id)
    print(f"  DevOps status after enable  : {d_devops.status}")

    # ── 11. Workload ─────────────────────────────────────────────────
    separator()
    print("[11] Department workload summary")
    for dept in eng.list_active_departments():
        bar = "#" * int(dept.workload_pct() / 10)
        print(f"  {dept.name:<26} {bar:<10} {dept.member_count()}/{dept.capacity} "
              f"({dept.workload_pct():.0f}%)")

    # ── 12. Statistics ───────────────────────────────────────────────
    separator()
    print("[12] Organisation statistics")
    stats = eng.statistics()
    print(f"  Total departments        : {stats['total_departments']}")
    print(f"  Active departments       : {stats['active_departments']}")
    print(f"  Departments with director: {stats['departments_with_directors']}")
    print(f"  Total employees          : {stats['total_employees']}")
    print(f"  Active employees         : {stats['active_employees']}")
    print(f"  Suspended employees      : {stats['suspended_employees']}")
    print(f"  Terminated employees     : {stats['terminated_employees']}")
    print(f"  Total roles              : {stats['total_roles']}")
    print(f"  Total skills             : {stats['total_skills']}")

    separator("=")
    print("  Demo complete.")
    separator("=")


if __name__ == "__main__":
    main()
