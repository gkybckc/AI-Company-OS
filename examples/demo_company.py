"""
AI Company OS - Full Orchestration Demo

Demonstrates the Company Orchestrator running a complete end-to-end flow
for a CEO request to build a Netflix-like streaming platform.

Every step in the orchestration pipeline is printed to the console in order,
providing a narrative view of what the company is doing at each stage.

Run with:
    .venv\\Scripts\\python.exe examples/demo_company.py

No AI, no networking, no external services. Fully deterministic.
"""

import sys
import os

# Allow importing from the project root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.company_context import CompanyContext
from core.company_event import CompanyEventType
from core.company_orchestrator import CompanyOrchestrator


def sep(char="=", width=60):
    return char * width


def section(title):
    print("\n" + sep())
    print("  " + title)
    print(sep())


def step(label, detail=""):
    if detail:
        print("  >> " + label + ": " + str(detail))
    else:
        print("  >> " + label)


def sub(label):
    print("       - " + label)


def main():
    # -------------------------------------------------------------------
    # Header
    # -------------------------------------------------------------------
    print(sep())
    print("  AI Company OS")
    print(sep())
    print()
    print("  Scenario: CEO requests a Netflix-like streaming platform.")
    print("  The orchestrator drives every step of the pipeline.")
    print()

    # -------------------------------------------------------------------
    # 1. Initialise the company
    # -------------------------------------------------------------------
    section("STEP 1 - Initialize Company")

    context = CompanyContext.create(company_name="StreamCo AI")
    orchestrator = CompanyOrchestrator(context)

    step("Company created", context.company_name)
    step("Company ID", context.company_id)
    step("Subsystems initialized")
    sub("PlannerEngine      - ready")
    sub("ExecutiveEngine    - ready")
    sub("DepartmentRegistry - empty")
    sub("WorkforceRegistry  - empty")
    sub("CompanyRuntime     - STOPPED")

    # -------------------------------------------------------------------
    # 2. Start the company
    # -------------------------------------------------------------------
    section("STEP 2 - Starting company...")

    orchestrator.start_company()
    step("Company runtime started")
    step("Company status", "RUNNING")
    print()
    print("  AI Company OS is now running.")
    print("  Ready to accept CEO directives.")

    # -------------------------------------------------------------------
    # 3. CEO directive
    # -------------------------------------------------------------------
    section("STEP 3 - CEO Directive")

    ceo_request = (
        "Build a Netflix-like streaming platform with user authentication, "
        "video streaming, subscription billing, and a recommendation engine."
    )

    print()
    print("  CEO: \"" + ceo_request + "\"")
    print()
    print("  Passing request to Company Orchestrator...")

    # -------------------------------------------------------------------
    # 4. Run the orchestration pipeline
    # -------------------------------------------------------------------
    section("STEP 4 - Orchestration Pipeline")

    print()
    print("  [Stage: ANALYZING]")
    print("  Planner analyzing request...")

    session = orchestrator.new_request(ceo_request)

    # Walk the event log and narrate each step.
    for event in session.events:
        et = event.event_type
        p = event.payload

        if et == CompanyEventType.REQUEST_RECEIVED:
            print()
            sub("Request accepted -> session " + session.id[:8] + "...")

        elif et == CompanyEventType.PROJECT_ANALYZED:
            print()
            print("  Blueprint generated.")
            sub("Project type      : " + str(p.get("project_type", "")))
            sub("Project title     : " + str(p.get("project_title", "")))
            sub("Complexity score  : " + str(p.get("complexity_score", "")) + " / 10")
            sub("Departments needed: " + str(p.get("departments_required", "")))
            sub("Estimated sprints : " + str(p.get("estimated_sprints", "")))

        elif et == CompanyEventType.PROJECT_CREATED:
            print()
            print("  Executive created project.")
            sub("Project title  : " + str(p.get("project_title", "")))
            sub("Project ID     : " + str(p.get("project_id", ""))[:8] + "...")
            sub("Status         : " + str(p.get("status", "")))

        elif et == CompanyEventType.DEPARTMENT_PROVISIONED:
            sub("Department provisioned: " + str(p.get("department_type", "")))

        elif et == CompanyEventType.EMPLOYEE_HIRED:
            name = str(p.get("employee_name", ""))
            role = str(p.get("role", ""))
            dept = str(p.get("department", ""))
            sub("Hired: " + name + " [" + role + " / " + dept + "]")

        elif et == CompanyEventType.TASK_CREATED:
            pass  # Reported at TASK_ASSIGNED for conciseness.

        elif et == CompanyEventType.TASK_ASSIGNED:
            name = str(p.get("employee_name", ""))
            dept = str(p.get("department", ""))
            sub("Task assigned -> " + name + " (" + dept + ")")

        elif et == CompanyEventType.RUNTIME_STARTED:
            rts = [e for e in session.events
                   if e.event_type == CompanyEventType.RUNTIME_STARTED]
            if event is rts[0]:
                print()
                print("  Runtime session started.")
            name = str(p.get("employee_name", ""))
            rt_id = str(p.get("runtime_session_id", ""))[:8]
            sub("Runtime: " + name + " -> session " + rt_id + "...")

        elif et == CompanyEventType.DISCUSSION_STARTED:
            print()
            print("  Discussion opened.")
            topic = str(p.get("topic", ""))
            sub("Topic: " + topic[:70] + ("..." if len(topic) > 70 else ""))

        elif et == CompanyEventType.DISCUSSION_FINISHED:
            print("  Discussion completed.")
            sub("Participants: " + str(p.get("participants", "")))
            sub("Messages    : " + str(p.get("messages", "")))
            decision = str(p.get("decision", ""))
            sub("Decision    : " + decision[:60] + ("..." if len(decision) > 60 else ""))

        elif et == CompanyEventType.PROJECT_FINISHED:
            print()
            print("  Project finished.")
            sub("Tasks created   : " + str(p.get("tasks_created", "")))
            sub("Runtimes started: " + str(p.get("runtimes_started", "")))
            sub("Discussions     : " + str(p.get("discussions", "")))

        elif et == CompanyEventType.REQUEST_COMPLETED:
            print()
            sub("Session " + session.id[:8] + "... completed successfully.")
            sub("Total events logged: " + str(p.get("total_events", "")))

    # -------------------------------------------------------------------
    # 5. Current company status
    # -------------------------------------------------------------------
    section("STEP 5 - Current company status.")

    status = orchestrator.status()
    print()
    step("Running", str(status["running"]))
    step("Company", status["company_name"])
    step("Sessions", str(status["total_sessions"]))
    step("Departments active", str(status["departments"]))
    step("Employees hired", str(status["employees"]))

    # -------------------------------------------------------------------
    # 6. Statistics
    # -------------------------------------------------------------------
    section("STEP 6 - Statistics")

    stats = orchestrator.statistics()
    print()
    for key, value in stats.items():
        label = key.replace("_", " ").title()
        sub(label + ": " + str(value))

    # -------------------------------------------------------------------
    # 7. Blueprint summary
    # -------------------------------------------------------------------
    section("STEP 7 - Blueprint Summary")

    if session.blueprint:
        bp = session.blueprint
        print()
        sub("Project : " + bp.project_title)
        sub("Type    : " + str(bp.project_type))
        sub("Complexity: " + str(bp.complexity_score) + "/10")
        print()
        print("  Risks identified:")
        for risk in bp.risks:
            sub("[" + risk.level.value + "] " + risk.category.value)
        print()
        print("  Departments selected:")
        for dr in bp.departments:
            flag = "CRITICAL" if dr.is_critical else "optional"
            sub(dr.department.value + " (" + flag + ")")

    # -------------------------------------------------------------------
    # 8. Company ready / stop
    # -------------------------------------------------------------------
    section("STEP 8 - Company ready.")

    orchestrator.stop_company()
    step("Company runtime stopped")
    step("Company status", "STOPPED")

    # -------------------------------------------------------------------
    # Footer
    # -------------------------------------------------------------------
    print()
    print(sep())
    print("  Demo complete.")
    print("  AI Company OS orchestrated a complete project lifecycle.")
    print("  No AI was called. No networking occurred. Fully deterministic.")
    print(sep())
    print()


if __name__ == "__main__":
    main()
