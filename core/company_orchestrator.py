"""
Company Orchestrator for AI Company OS.

The CompanyOrchestrator is the central coordination authority of the
entire AI Company OS system. It connects every existing module — Planner,
Executive, Department Registry, Workforce Registry, Agent Runtime, and
Discussion Engine — and drives the end-to-end flow from a CEO's natural-
language request to an active, organized project.

The orchestrator NEVER performs work itself. It ONLY orchestrates.
It never writes code, designs UI, authors documents, or executes tasks.
Its sole purpose is to connect the modules that already exist and move
state through the defined pipeline in the correct order.

Pipeline (new_request):
    1. Accept the CEO's request              → emit REQUEST_RECEIVED
    2. Planner analyzes the request          → emit PROJECT_ANALYZED
    3. Executive creates the project         → emit PROJECT_CREATED
    4. For each required department:
       a. Provision department if absent     → emit DEPARTMENT_PROVISIONED
       b. Hire one employee                  → emit EMPLOYEE_HIRED
       c. Create and assign a task           → emit TASK_CREATED, TASK_ASSIGNED
       d. Start an AgentRuntime session      → emit RUNTIME_STARTED
    5. Open a discussion on the project      → emit DISCUSSION_STARTED
    6. Close the discussion with outcome     → emit DISCUSSION_FINISHED
    7. Mark project finished                 → emit PROJECT_FINISHED
    8. Close the session                     → emit REQUEST_COMPLETED

Architecture reference: §2.1 Executive Engine, §2.2 Agent Runtime,
§2.4 Discussion Engine, §3 Layer 5 (Coordination Layer),
§9 Discussion Flow, §11 Task Lifecycle, Constitution Chapter 4.

Rules:
  - No AI calls.
  - No external services.
  - No networking.
  - No async.
  - No databases.
  - No external libraries.
  - Only connect the modules that already exist.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from core.company_context import CompanyContext
from core.company_event import CompanyEvent, CompanyEventType
from core.company_session import CompanySession, SessionStage
from core.department import Department
from core.department_registry import DepartmentAlreadyRegisteredError, DepartmentNotFoundError
from core.department_status import DepartmentStatus, DirectorStatus
from core.department_type import DepartmentType
from core.department_requirement import Department as BlueprintDepartment
from core.director import Director
from core.discussion import Discussion, DiscussionStatus
from core.discussion_engine import DiscussionEngine
from core.discussion_message import DiscussionMessage
from core.discussion_outcome import DiscussionOutcome
from core.discussion_participant import DiscussionParticipant
from core.employee_role import EmployeeRole, Seniority
from core.hire_request import HireRequest
from core.project import ProjectStatus
from core.runtime import CompanyRuntime
from core.runtime_context import RuntimeContext
from core.runtime_state import AgentRuntimeState
from core.agent_runtime import AgentRuntime
from core.task import Priority


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class OrchestratorError(Exception):
    """Base class for all Company Orchestrator errors."""


class OrchestratorNotStartedError(OrchestratorError):
    """
    Raised when an operation requires the company to be started but it is not.

    Call start_company() before calling new_request().
    """


class OrchestratorAlreadyStartedError(OrchestratorError):
    """
    Raised when start_company() is called on an already-running company.

    Call stop_company() before calling start_company() again.
    """


class OrchestratorNotRunningError(OrchestratorError):
    """
    Raised when stop_company() is called on a company that is not running.
    """


class InvalidRequestError(OrchestratorError):
    """
    Raised when new_request() receives an empty or too-short request.
    """


# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------

# Maps blueprint Department enum values to DepartmentType registry enum.
# Both have the same string values, so value-based conversion works.
_DEPT_TYPE_MAP: Dict[str, DepartmentType] = {dt.value: dt for dt in DepartmentType}

# Maps DepartmentType to a sensible default EmployeeRole for auto-provisioned agents.
_DEPT_DEFAULT_ROLE: Dict[DepartmentType, EmployeeRole] = {
    DepartmentType.BACKEND: EmployeeRole.BACKEND_AGENT,
    DepartmentType.FRONTEND: EmployeeRole.FRONTEND_AGENT,
    DepartmentType.ENGINEERING: EmployeeRole.BACKEND_AGENT,
    DepartmentType.DATABASE: EmployeeRole.BACKEND_AGENT,
    DepartmentType.DESIGN: EmployeeRole.UI_DESIGNER,
    DepartmentType.PRODUCT: EmployeeRole.PRODUCT_ANALYST,
    DepartmentType.QA: EmployeeRole.QA_ENGINEER,
    DepartmentType.DEVOPS: EmployeeRole.DEVOPS_ENGINEER,
    DepartmentType.SECURITY: EmployeeRole.SECURITY_SPECIALIST,
    DepartmentType.MARKETING: EmployeeRole.MARKETING_SPECIALIST,
    DepartmentType.LEGAL: EmployeeRole.RESEARCH_ANALYST,
    DepartmentType.FINANCE: EmployeeRole.RESEARCH_ANALYST,
    DepartmentType.RESEARCH: EmployeeRole.RESEARCH_ANALYST,
}

# Default skills used when auto-provisioning an employee.
_DEPT_DEFAULT_SKILLS: Dict[DepartmentType, List[str]] = {
    DepartmentType.BACKEND: ["Python", "REST API", "SQL"],
    DepartmentType.FRONTEND: ["TypeScript", "React", "CSS"],
    DepartmentType.ENGINEERING: ["Python", "System Design"],
    DepartmentType.DATABASE: ["PostgreSQL", "Data Modeling", "SQL"],
    DepartmentType.DESIGN: ["Figma", "Design Systems", "UI/UX"],
    DepartmentType.PRODUCT: ["Product Strategy", "User Stories"],
    DepartmentType.QA: ["Test Planning", "Automation", "Regression"],
    DepartmentType.DEVOPS: ["Docker", "CI/CD", "Cloud Infrastructure"],
    DepartmentType.SECURITY: ["Threat Modeling", "OWASP", "Penetration Testing"],
    DepartmentType.MARKETING: ["SEO", "Content Strategy", "Brand"],
    DepartmentType.LEGAL: ["Contract Review", "Compliance", "IP"],
    DepartmentType.FINANCE: ["Financial Modeling", "Reconciliation"],
    DepartmentType.RESEARCH: ["Research", "Analysis", "Reporting"],
}

_MIN_REQUEST_LENGTH = 10


# ---------------------------------------------------------------------------
# CompanyOrchestrator
# ---------------------------------------------------------------------------

class CompanyOrchestrator:
    """
    Central coordination authority for AI Company OS.

    Connects and drives the full orchestration pipeline: Planner → Executive
    → Department Registry → Workforce Registry → Agent Runtime → Discussion
    Engine. The orchestrator records every step as a CompanyEvent in the
    active CompanySession and manages the session lifecycle.

    One orchestrator is created per company. It holds a CompanyContext
    that gives it access to all subsystems. It manages its own
    DiscussionEngine instance (since Discussion is a Coordination Layer
    concern) and a registry of per-employee AgentRuntime instances.

    The orchestrator is synchronous. It is not thread-safe. It is designed
    for Stage 1 of the architecture (Architecture §13, 1–10 agents).

    Attributes:
        _context: The CompanyContext holding all subsystems.
        _sessions: Ordered list of all CompanySession records, oldest first.
        _current_session_id: ID of the currently active session, or None.
        _agent_runtimes: Dict mapping employee_id → AgentRuntime instance.
        _discussion_engine: DiscussionEngine instance for this company.
        _is_running: True when the company has been started.
    """

    def __init__(self, context: CompanyContext) -> None:
        self._context = context
        self._sessions: List[CompanySession] = []
        self._current_session_id: Optional[str] = None
        self._agent_runtimes: Dict[str, AgentRuntime] = {}
        self._discussion_engine = DiscussionEngine()
        self._is_running: bool = False

    # ------------------------------------------------------------------
    # Company lifecycle
    # ------------------------------------------------------------------

    def start_company(self) -> CompanyContext:
        """
        Start the company runtime, making the company ready to accept requests.

        If the CompanyContext has an attached CompanyRuntime, it is started.
        Records a COMPANY_STARTED event in the global event log (no session).

        Returns:
            The CompanyContext with the runtime now running.

        Raises:
            OrchestratorAlreadyStartedError: If the company is already running.
        """
        if self._is_running:
            raise OrchestratorAlreadyStartedError(
                f"Company '{self._context.company_name}' is already running. "
                "Call stop_company() before calling start_company() again."
            )

        if (
            self._context.active_runtime is not None
            and not self._context.active_runtime._status.value == "RUNNING"
        ):
            try:
                self._context.active_runtime.start()
            except Exception:
                pass  # Runtime may already be running; treat as idempotent.

        self._is_running = True
        return self._context

    def stop_company(self) -> None:
        """
        Stop the company runtime.

        If the CompanyContext has a running CompanyRuntime, it is stopped.
        Any active session is left in its current state (not force-failed).

        Raises:
            OrchestratorNotRunningError: If the company is not running.
        """
        if not self._is_running:
            raise OrchestratorNotRunningError(
                f"Company '{self._context.company_name}' is not running. "
                "Call start_company() before calling stop_company()."
            )

        if self._context.active_runtime is not None:
            try:
                self._context.active_runtime.stop()
            except Exception:
                pass  # Ignore stop errors; treat as idempotent.

        self._is_running = False

    # ------------------------------------------------------------------
    # Request handling
    # ------------------------------------------------------------------

    def new_request(self, request: str) -> CompanySession:
        """
        Accept a CEO request and run the full orchestration pipeline.

        This is the heart of the Company Orchestrator. It:
          1. Validates the request and the company state.
          2. Creates a CompanySession.
          3. Runs each stage of the pipeline in order.
          4. Records every step as a CompanyEvent.
          5. Returns the completed (or failed) CompanySession.

        The method is synchronous and blocking. It will always return a
        CompanySession — if any stage fails, the session is marked FAILED
        and returned rather than raising an exception.

        Args:
            request: Free-text description of what the CEO wants to build.
                Must be at least 10 characters after stripping.

        Returns:
            The completed CompanySession.

        Raises:
            OrchestratorNotStartedError: If start_company() has not been called.
            InvalidRequestError: If the request is empty or too short.
        """
        self._require_running()
        self._validate_request(request)

        session = self._create_session(request)
        self._current_session_id = session.id
        self._sessions.append(session)

        try:
            self._run_pipeline(session)
        except Exception as exc:
            self._fail_session(session, str(exc))

        return session

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def current_session(self) -> Optional[CompanySession]:
        """
        Return the most recently created session, or None if no sessions exist.

        Returns:
            The last CompanySession, or None.
        """
        if not self._sessions:
            return None
        return self._sessions[-1]

    def history(self) -> List[CompanySession]:
        """
        Return all sessions in creation order (oldest first).

        Returns a shallow copy — callers cannot modify the internal list.

        Returns:
            List of all CompanySession records.
        """
        return list(self._sessions)

    def status(self) -> Dict[str, Any]:
        """
        Return a snapshot of the company's current operational state.

        Returns:
            Dict with keys:
                running         — True if the company is started.
                company_name    — Name of the company.
                company_id      — ID of the company.
                total_sessions  — Number of sessions ever created.
                active_session  — Summary dict of the active session, or None.
                departments     — Number of registered departments.
                employees       — Number of active employees.
        """
        active = self.current_session()
        return {
            "running": self._is_running,
            "company_name": self._context.company_name,
            "company_id": self._context.company_id,
            "total_sessions": len(self._sessions),
            "active_session": active.summary() if active else None,
            "departments": self._context.department_count(),
            "employees": self._context.employee_count(),
        }

    def statistics(self) -> Dict[str, Any]:
        """
        Return aggregate statistics across all sessions.

        Returns:
            Dict with keys:
                total_sessions      — All sessions ever created.
                finished_sessions   — Sessions that completed successfully.
                failed_sessions     — Sessions that ended in FAILED state.
                total_projects      — Total projects created.
                total_tasks         — Total tasks created across sessions.
                total_discussions   — Total discussions opened.
                total_runtimes      — Total AgentRuntime sessions started.
                total_events        — Total CompanyEvents recorded.
                departments         — Departments currently registered.
                employees           — Employees currently in the workforce.
        """
        finished = sum(1 for s in self._sessions if s.is_finished())
        failed = sum(1 for s in self._sessions if s.is_failed())
        total_tasks = sum(s.task_count() for s in self._sessions)
        total_discussions = sum(s.discussion_count() for s in self._sessions)
        total_runtimes = sum(s.runtime_count() for s in self._sessions)
        total_events = sum(s.event_count() for s in self._sessions)
        total_projects = sum(1 for s in self._sessions if s.has_project())

        return {
            "total_sessions": len(self._sessions),
            "finished_sessions": finished,
            "failed_sessions": failed,
            "total_projects": total_projects,
            "total_tasks": total_tasks,
            "total_discussions": total_discussions,
            "total_runtimes": total_runtimes,
            "total_events": total_events,
            "departments": self._context.department_count(),
            "employees": self._context.employee_count(),
        }

    # ------------------------------------------------------------------
    # Pipeline stages
    # ------------------------------------------------------------------

    def _run_pipeline(self, session: CompanySession) -> None:
        """Execute all pipeline stages in order for the given session."""

        # Stage 1 — Analyze
        self._stage_analyze(session)

        # Stage 2 — Plan (create project, departments, employees, tasks)
        self._stage_plan(session)

        # Stage 3 — Execute (start runtimes)
        self._stage_execute(session)

        # Stage 4 — Discuss
        self._stage_discuss(session)

        # Stage 5 — Finish
        self._stage_finish(session)

    def _stage_analyze(self, session: CompanySession) -> None:
        """
        Use PlannerEngine to analyze the CEO's request and produce a blueprint.

        Advances session to ANALYZING, calls PlannerEngine.analyze(), stores
        the blueprint, emits PROJECT_ANALYZED, then leaves it ready for PLANNING.
        """
        session.current_stage = SessionStage.ANALYZING

        blueprint = self._context.planner.analyze(session.request)
        session.blueprint = blueprint

        session.add_event(CompanyEvent.create(
            event_type=CompanyEventType.PROJECT_ANALYZED,
            session_id=session.id,
            payload={
                "project_title": blueprint.project_title,
                "project_type": str(blueprint.project_type),
                "complexity_score": blueprint.complexity_score,
                "departments_required": len(blueprint.departments),
                "estimated_sprints": blueprint.estimated_sprint_count,
            },
        ))

    def _stage_plan(self, session: CompanySession) -> None:
        """
        Create the project, provision departments and employees, create tasks.

        Advances session to PLANNING. For each department in the blueprint:
          - Provision the department if not already in the registry.
          - Hire one employee for that department.
          - Create a task for that department's work.
          - Assign the task to the hired employee.
        Emits PROJECT_CREATED, DEPARTMENT_PROVISIONED, EMPLOYEE_HIRED,
        TASK_CREATED, TASK_ASSIGNED events.
        """
        session.current_stage = SessionStage.PLANNING

        blueprint = session.blueprint

        # Create the project via ExecutiveEngine.
        project = self._context.executive.create_project(
            title=blueprint.project_title,
            description=blueprint.description,
            objective=blueprint.objective,
            priority=Priority.HIGH,
        )
        session.project = project
        self._context.active_project = project

        session.add_event(CompanyEvent.create(
            event_type=CompanyEventType.PROJECT_CREATED,
            session_id=session.id,
            payload={
                "project_id": project.id,
                "project_title": project.title,
                "status": str(project.status),
            },
        ))

        # For each required department, provision it and hire an employee.
        for dept_req in blueprint.departments:
            dept_type = self._resolve_dept_type(dept_req.department)

            # Provision the department if it doesn't exist yet.
            try:
                dept = self._context.departments.find_by_type(dept_type)
            except DepartmentNotFoundError:
                dept = self._provision_department(session, dept_type)

            # Hire one employee for this department.
            employee = self._hire_employee(session, dept_type, dept.id)

            # Create a task for this department's work.
            task = self._context.executive.create_task(
                project_id=project.id,
                title=f"{dept_type.value} Sprint 1",
                description=(
                    f"{dept_req.rationale} "
                    f"Complete the {dept_type.value} department's Sprint 1 deliverables."
                ),
                assigned_agent=employee.name,
                priority=Priority.HIGH if dept_req.is_critical else Priority.MEDIUM,
            )
            session.created_tasks.append(task)

            session.add_event(CompanyEvent.create(
                event_type=CompanyEventType.TASK_CREATED,
                session_id=session.id,
                payload={
                    "task_id": task.id,
                    "task_title": task.title,
                    "department": dept_type.value,
                    "assigned_to": employee.name,
                },
            ))

            # Formally assign the task.
            self._context.executive.assign_task(task.id, employee.name)

            session.add_event(CompanyEvent.create(
                event_type=CompanyEventType.TASK_ASSIGNED,
                session_id=session.id,
                payload={
                    "task_id": task.id,
                    "employee_id": employee.id,
                    "employee_name": employee.name,
                    "department": dept_type.value,
                },
            ))

    def _stage_execute(self, session: CompanySession) -> None:
        """
        Start AgentRuntime sessions for each employee assigned a task.

        Advances session to EXECUTING. Iterates over created tasks, finds
        the employee by name, starts an AgentRuntime session, and emits
        RUNTIME_STARTED per employee. Attaches project context to each
        runtime session.
        """
        session.current_stage = SessionStage.EXECUTING

        for task in session.created_tasks:
            # Find the employee by name in the workforce registry.
            employee = self._find_employee_by_name(task.assigned_agent)
            if employee is None:
                continue

            # Get or create an AgentRuntime for this employee.
            if employee.id not in self._agent_runtimes:
                self._agent_runtimes[employee.id] = AgentRuntime(employee.id)
            runtime = self._agent_runtimes[employee.id]

            # Skip if a session is already active for this employee.
            if runtime.has_active_session():
                continue

            # Start a new session and attach project context.
            rt_session = runtime.start_session(
                project_id=session.project.id if session.project else None,
                task_id=task.id,
            )
            session.started_runtimes.append(rt_session.session_id)

            # Advance to WORKING state so the runtime reflects active work.
            if runtime.current_state() == AgentRuntimeState.READY:
                runtime.change_state(AgentRuntimeState.WAITING_TASK)
            if runtime.current_state() == AgentRuntimeState.WAITING_TASK:
                runtime.change_state(AgentRuntimeState.TASK_RECEIVED)
            if runtime.current_state() == AgentRuntimeState.TASK_RECEIVED:
                runtime.change_state(AgentRuntimeState.ANALYZING)
            if runtime.current_state() == AgentRuntimeState.ANALYZING:
                runtime.change_state(AgentRuntimeState.PLANNING)
            if runtime.current_state() == AgentRuntimeState.PLANNING:
                runtime.change_state(AgentRuntimeState.WORKING)

            # Attach project context.
            ctx = RuntimeContext(
                current_task=task.title,
                project=session.project.title if session.project else None,
            )
            runtime.attach_context(ctx)

            session.add_event(CompanyEvent.create(
                event_type=CompanyEventType.RUNTIME_STARTED,
                session_id=session.id,
                payload={
                    "runtime_session_id": rt_session.session_id,
                    "employee_id": employee.id,
                    "employee_name": employee.name,
                    "task_id": task.id,
                    "task_title": task.title,
                },
            ))

    def _stage_discuss(self, session: CompanySession) -> None:
        """
        Open and close a project discussion with the first two employees.

        Advances session to DISCUSSING. Selects up to two employees from
        the workforce, admits them as participants, posts a structured
        opinion + reasoning message from each, then closes the discussion
        with a formal DiscussionOutcome.
        """
        session.current_stage = SessionStage.DISCUSSING

        if session.project is None:
            return

        # Open a discussion on the project topic.
        topic = (
            f"Technical approach for {session.project.title}: "
            f"review architecture and department assignments."
        )
        discussion = self._discussion_engine.start_discussion(
            topic=topic,
            project_id=session.project.id,
            task_id=None,
        )
        session.discussions.append(discussion)

        session.add_event(CompanyEvent.create(
            event_type=CompanyEventType.DISCUSSION_STARTED,
            session_id=session.id,
            payload={
                "discussion_id": discussion.id,
                "topic": topic,
                "project_id": session.project.id,
            },
        ))

        # Admit up to two employees as participants.
        employees = self._context.workforce.list_all()[:2]
        participants = []
        for emp in employees:
            p = DiscussionParticipant(
                participant_id=emp.id,
                name=emp.name,
                role=str(emp.role),
                joined_at=datetime.now(timezone.utc),
            )
            self._discussion_engine.join(discussion.id, p)
            participants.append((emp, p))

        # Post a structured message from each participant.
        for emp, participant in participants:
            opinion = (
                f"The {emp.department.value} department is well-positioned to "
                f"deliver its Sprint 1 tasks for {session.project.title}."
            )
            reasoning = (
                f"The department has the required skills and has been assigned "
                f"a clear task with explicit acceptance criteria. The architecture "
                f"selected by the Planner Engine is appropriate for the project type."
            )
            msg = DiscussionMessage(
                sender=emp.id,
                role=str(emp.role),
                opinion=opinion,
                reasoning=reasoning,
                timestamp=datetime.now(timezone.utc),
            )
            self._discussion_engine.post_message(discussion.id, msg)

        # Close the discussion with a formal outcome.
        outcome = DiscussionOutcome(
            decision=(
                f"Proceed with the planned architecture for {session.project.title}. "
                f"All assigned departments confirmed readiness for Sprint 1."
            ),
            summary=(
                f"All {len(participants)} participating employees reviewed the plan "
                f"and confirmed their department's readiness. No blockers identified. "
                f"Sprint 1 may begin immediately."
            ),
            agreed_actions=[
                "Begin Sprint 1 task execution immediately.",
                "Report progress at the end of the sprint.",
                "Escalate any blockers to the Executive Engine.",
            ],
            unresolved_points=[],
        )
        self._discussion_engine.close(discussion.id, outcome)

        session.add_event(CompanyEvent.create(
            event_type=CompanyEventType.DISCUSSION_FINISHED,
            session_id=session.id,
            payload={
                "discussion_id": discussion.id,
                "participants": len(participants),
                "messages": discussion.message_count(),
                "decision": outcome.decision[:80],
            },
        ))

    def _stage_finish(self, session: CompanySession) -> None:
        """
        Mark the project as finished and the session as FINISHED.

        Emits PROJECT_FINISHED and REQUEST_COMPLETED events.
        Updates the project status to COMPLETED.
        """
        if session.project is not None:
            session.project.status = ProjectStatus.COMPLETED

        session.add_event(CompanyEvent.create(
            event_type=CompanyEventType.PROJECT_FINISHED,
            session_id=session.id,
            payload={
                "project_id": session.project.id if session.project else None,
                "tasks_created": session.task_count(),
                "runtimes_started": session.runtime_count(),
                "discussions": session.discussion_count(),
            },
        ))

        session.current_stage = SessionStage.FINISHED
        session.finished_at = datetime.now(timezone.utc)

        session.add_event(CompanyEvent.create(
            event_type=CompanyEventType.REQUEST_COMPLETED,
            session_id=session.id,
            payload={
                "session_id": session.id,
                "total_events": session.event_count() + 1,
            },
        ))

    # ------------------------------------------------------------------
    # Provisioning helpers
    # ------------------------------------------------------------------

    def _provision_department(
        self,
        session: CompanySession,
        dept_type: DepartmentType,
    ) -> Department:
        """
        Create and register a Department + Director for the given type.

        Called when a blueprint requires a department not yet in the registry.

        Args:
            session: The active CompanySession (for event recording).
            dept_type: The DepartmentType to provision.

        Returns:
            The newly registered Department.
        """
        now = datetime.now(timezone.utc)

        director = Director(
            id=str(uuid4()),
            name=f"{dept_type.value} Director",
            department=dept_type,
            status=DirectorStatus.ACTIVE,
            responsibilities=[
                f"Lead the {dept_type.value} department.",
                "Assign and supervise specialist agents.",
                "Report status to the Executive Engine.",
            ],
            managed_agents=[],
            assigned_at=now,
        )

        department = Department(
            id=str(uuid4()),
            name=f"{dept_type.value} Department",
            type=dept_type,
            director=director,
            members=[],
            status=DepartmentStatus.READY,
            capacity=5,
            active_projects=[],
            active_tasks=[],
            workload=0.0,
            created_at=now,
        )

        self._context.departments.register(department)

        session.add_event(CompanyEvent.create(
            event_type=CompanyEventType.DEPARTMENT_PROVISIONED,
            session_id=session.id,
            payload={
                "department_id": department.id,
                "department_type": dept_type.value,
                "department_name": department.name,
            },
        ))

        return department

    def _hire_employee(
        self,
        session: CompanySession,
        dept_type: DepartmentType,
        dept_id: str,
    ):
        """
        Hire one employee for the given department via the WorkforceRegistry.

        Args:
            session: The active CompanySession (for event recording).
            dept_type: Department type — determines role and skills.
            dept_id: ID of the department (used to find the director).

        Returns:
            The newly hired Employee.
        """
        role = _DEPT_DEFAULT_ROLE.get(dept_type, EmployeeRole.BACKEND_AGENT)
        skills = _DEPT_DEFAULT_SKILLS.get(dept_type, [])

        # Find the director ID if available.
        director_id: Optional[str] = None
        try:
            dept = self._context.departments.get(dept_id)
            if dept.director is not None:
                director_id = dept.director.id
        except Exception:
            pass

        employee_name = f"{dept_type.value} Agent 01"
        hire_request = HireRequest(
            name=employee_name,
            role=role,
            department=dept_type,
            seniority=Seniority.MID,
            skills=skills,
            director_id=director_id,
        )

        employee = self._context.workforce.hire(hire_request)

        session.add_event(CompanyEvent.create(
            event_type=CompanyEventType.EMPLOYEE_HIRED,
            session_id=session.id,
            payload={
                "employee_id": employee.id,
                "employee_name": employee.name,
                "role": str(employee.role),
                "department": dept_type.value,
            },
        ))

        return employee

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_session(self, request: str) -> CompanySession:
        """Create a new CompanySession and emit REQUEST_RECEIVED."""
        session = CompanySession(
            id=str(uuid4()),
            request=request,
            current_stage=SessionStage.CREATED,
            created_at=datetime.now(timezone.utc),
        )
        session.add_event(CompanyEvent.create(
            event_type=CompanyEventType.REQUEST_RECEIVED,
            session_id=session.id,
            payload={"request_preview": request[:120]},
        ))
        return session

    def _fail_session(self, session: CompanySession, reason: str) -> None:
        """Mark the session as FAILED and record a REQUEST_FAILED event."""
        session.current_stage = SessionStage.FAILED
        session.error_message = reason
        session.finished_at = datetime.now(timezone.utc)
        session.add_event(CompanyEvent.create(
            event_type=CompanyEventType.REQUEST_FAILED,
            session_id=session.id,
            payload={"reason": reason},
        ))

    def _require_running(self) -> None:
        """Raise OrchestratorNotStartedError if the company is not started."""
        if not self._is_running:
            raise OrchestratorNotStartedError(
                "The company is not started. Call start_company() first."
            )

    def _validate_request(self, request: str) -> None:
        """Raise InvalidRequestError if the request is invalid."""
        if not request or not request.strip():
            raise InvalidRequestError(
                "The CEO request must not be empty."
            )
        if len(request.strip()) < _MIN_REQUEST_LENGTH:
            raise InvalidRequestError(
                f"The CEO request is too short ({len(request.strip())} chars). "
                f"Provide at least {_MIN_REQUEST_LENGTH} characters."
            )

    def _resolve_dept_type(self, blueprint_dept: BlueprintDepartment) -> DepartmentType:
        """
        Convert a blueprint Department enum value to a DepartmentType enum.

        Both enums share the same string values, so value-based conversion
        is safe and avoids coupling to the blueprint's enum class.

        Args:
            blueprint_dept: The Department value from the blueprint.

        Returns:
            The matching DepartmentType.
        """
        return _DEPT_TYPE_MAP.get(blueprint_dept.value, DepartmentType.ENGINEERING)

    def _find_employee_by_name(self, name: str):
        """
        Find an employee in the workforce registry by display name.

        Args:
            name: The employee's display name to search for.

        Returns:
            The matching Employee, or None if not found.
        """
        for emp in self._context.workforce.list_all():
            if emp.name == name:
                return emp
        return None
