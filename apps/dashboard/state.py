"""
Dashboard state singleton for AI Company OS CEO Control Center.

Initializes all engines and seeds them with representative data so the
dashboard has real data to display.  The singleton pattern means all
FastAPI route handlers share the same engine instances.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from core.artifact_engine import ArtifactEngine
from core.org_engine import OrgEngine
from core.collaboration.collaboration_manager import CollaborationHub
from core.collaboration.conversation_message import MessageCategory, ConversationMessage
from core.collaboration.conversation_participant import ConversationParticipant
from core.collaboration.conversation_templates import TemplateType, default_policies
from core.company_context import CompanyContext
from core.company_orchestrator import CompanyOrchestrator
from core.decision_engine import DecisionEngine
from core.decision_option import DecisionOption
from core.department import Department
from core.department_registry import DepartmentRegistry
from core.department_status import DepartmentStatus, DirectorStatus
from core.department_type import DepartmentType
from core.director import Director
from core.discussion_engine import DiscussionEngine
from core.discussion_message import DiscussionMessage
from core.discussion_outcome import DiscussionOutcome
from core.discussion_participant import DiscussionParticipant
from core.employee_role import EmployeeRole, Seniority
from core.event_stream import EventStream
from core.executive_engine import ExecutiveEngine
from core.hire_request import HireRequest
from core.memory_category import MemoryCategory
from core.memory_engine import MemoryEngine
from core.memory_entry import MemoryEntry
from core.memory_scope import MemoryScope
from core.planner_engine import PlannerEngine
from core.project import Project
from core.stream_channel import StreamChannel
from core.stream_event import StreamEvent
from core.task import Priority
from core.workflow_engine import WorkflowEngine
from core.workflow_template import WorkflowTemplate
from core.workforce_registry import WorkforceRegistry


class DashboardState:
    """
    Central state holder for the CEO Control Center dashboard.

    Creates and seeds all AI Company OS engine instances at construction
    time so that every route handler works with consistent, real data.
    Use DashboardState.get() to retrieve the process-wide singleton.
    """

    _instance: Optional["DashboardState"] = None

    def __init__(self) -> None:
        self.memory_engine = MemoryEngine()
        self.decision_engine = DecisionEngine(memory_engine=self.memory_engine)
        self.discussion_engine = DiscussionEngine()
        self.department_registry = DepartmentRegistry()
        self.workforce_registry = WorkforceRegistry()
        self.executive_engine = ExecutiveEngine()
        self.workflow_engine = WorkflowEngine(
            memory_engine=self.memory_engine,
            decision_engine=self.decision_engine,
        )
        self.event_stream = EventStream()

        self.planner_engine = PlannerEngine()
        self.artifact_engine = ArtifactEngine(
            executive_engine=self.executive_engine,
            workflow_engine=self.workflow_engine,
            memory_engine=self.memory_engine,
            decision_engine=self.decision_engine,
            planner_engine=self.planner_engine,
        )
        _ctx = CompanyContext(
            company_id=str(uuid4()),
            company_name="AI Company OS",
            executive=self.executive_engine,
            planner=self.planner_engine,
            departments=self.department_registry,
            workforce=self.workforce_registry,
        )
        self.orchestrator = CompanyOrchestrator(_ctx)
        self.orchestrator.start_company()
        self.last_command: Optional[str] = None
        self.last_session: Optional[Any] = None
        self.command_history: List[Dict[str, Any]] = []

        self.org_engine = OrgEngine()
        self.collab_hub = CollaborationHub(seed_default_policies=True)

        self._seed()

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get(cls) -> "DashboardState":
        """Return the process-wide singleton, creating it on first call."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Destroy the singleton so the next get() creates a fresh one."""
        cls._instance = None

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    def new_request(self, command: str) -> Any:
        """Execute a CEO command via the CompanyOrchestrator."""
        self.last_command = command
        started_at = datetime.now(timezone.utc)
        session = self.orchestrator.new_request(command)
        finished_at = datetime.now(timezone.utc)
        self.last_session = session
        self.command_history.append({
            "command": command,
            "session_id": session.id,
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_seconds": round((finished_at - started_at).total_seconds(), 2),
            "success": session.is_finished(),
            "stage": str(session.current_stage),
            "event_count": session.event_count(),
        })
        return session

    def list_artifacts(self) -> List[Any]:
        """Return all artifacts produced by the ArtifactEngine."""
        return self.artifact_engine.history()

    def list_projects(self) -> List[Project]:
        """Return all projects registered in the Executive Engine."""
        return list(self.executive_engine._projects.values())

    def get_event_stats(self) -> Dict[str, Any]:
        """Return EventStream statistics."""
        return self.event_stream.statistics()

    def get_memory_stats(self) -> Dict[str, Any]:
        """Return MemoryEngine statistics."""
        return self.memory_engine.statistics()

    def get_decision_stats(self) -> Dict[str, Any]:
        """Return DecisionEngine statistics."""
        return self.decision_engine.statistics()

    def get_discussion_stats(self) -> Dict[str, Any]:
        """Return DiscussionEngine statistics."""
        return self.discussion_engine.statistics()

    def get_workflow_stats(self) -> Dict[str, Any]:
        """Return WorkflowEngine statistics."""
        return self.workflow_engine.statistics()

    # ------------------------------------------------------------------
    # Seed helpers
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        self._seed_departments()
        self._seed_employees()
        self._seed_projects()
        self._seed_workflows()
        self._seed_discussions()
        self._seed_decisions()
        self._seed_memory()
        self._seed_events()
        self._seed_org()

    def _seed_departments(self) -> None:
        dept_configs = [
            (DepartmentType.BACKEND, "Backend Engineering"),
            (DepartmentType.FRONTEND, "Frontend Engineering"),
            (DepartmentType.QA, "Quality Assurance"),
            (DepartmentType.DEVOPS, "DevOps"),
        ]
        for dept_type, dept_name in dept_configs:
            director = Director(
                id=str(uuid4()),
                name=f"{dept_name} Director",
                department=dept_type,
                status=DirectorStatus.ACTIVE,
                responsibilities=["Task assignment", "Progress monitoring", "Escalation"],
                managed_agents=[],
                assigned_at=datetime.now(timezone.utc),
            )
            dept = Department(
                id=str(uuid4()),
                name=dept_name,
                type=dept_type,
                director=director,
                members=[],
                status=DepartmentStatus.WORKING,
                capacity=10,
                active_projects=[],
                active_tasks=[],
                workload=0.6,
                created_at=datetime.now(timezone.utc),
            )
            self.department_registry.register(dept)

    def _seed_employees(self) -> None:
        hire_configs = [
            ("Alice Chen", EmployeeRole.BACKEND_AGENT, DepartmentType.BACKEND,
             Seniority.SENIOR, ["Python", "FastAPI", "PostgreSQL"]),
            ("Bob Kumar", EmployeeRole.BACKEND_AGENT, DepartmentType.BACKEND,
             Seniority.MID, ["Python", "REST API", "SQL"]),
            ("Carol Diaz", EmployeeRole.FRONTEND_AGENT, DepartmentType.FRONTEND,
             Seniority.SENIOR, ["TypeScript", "React", "CSS"]),
            ("Dave Park", EmployeeRole.QA_ENGINEER, DepartmentType.QA,
             Seniority.MID, ["Test Planning", "Automation", "Regression"]),
            ("Eve Singh", EmployeeRole.DEVOPS_ENGINEER, DepartmentType.DEVOPS,
             Seniority.SENIOR, ["Docker", "CI/CD", "Cloud Infrastructure"]),
        ]
        for name, role, dept, seniority, skills in hire_configs:
            request = HireRequest(
                name=name,
                role=role,
                department=dept,
                seniority=seniority,
                skills=skills,
            )
            self.workforce_registry.hire(request)

    def _seed_projects(self) -> None:
        self._project1 = self.executive_engine.create_project(
            title="AI Company OS Platform",
            description="Build the core infrastructure for the AI Company OS autonomous operations",
            objective="Establish the foundational platform for autonomous AI company operations",
            priority=Priority.HIGH,
        )
        t1 = self.executive_engine.create_task(
            self._project1.id,
            "Design Core Architecture",
            "Define the system architecture for all core modules",
            "Alice Chen",
            Priority.HIGH,
        )
        t2 = self.executive_engine.create_task(
            self._project1.id,
            "Implement Memory Engine",
            "Build the memory storage and retrieval system",
            "Bob Kumar",
            Priority.MEDIUM,
            dependencies=[t1.id],
        )
        self.executive_engine.assign_task(t1.id, "Alice Chen")
        self.executive_engine.assign_task(t2.id, "Bob Kumar")
        self._project1_id = self._project1.id

        self._project2 = self.executive_engine.create_project(
            title="CEO Dashboard V1",
            description="Web interface for real-time monitoring of AI Company OS",
            objective="Give the CEO real-time visibility into all company operations",
            priority=Priority.HIGH,
        )
        t3 = self.executive_engine.create_task(
            self._project2.id,
            "Design Dashboard Layout",
            "Create wireframes and component structure for the CEO dashboard",
            "Carol Diaz",
            Priority.HIGH,
        )
        t4 = self.executive_engine.create_task(
            self._project2.id,
            "Implement Dashboard Routes",
            "Build FastAPI routes and Jinja2 templates",
            "Alice Chen",
            Priority.HIGH,
            dependencies=[t3.id],
        )
        self.executive_engine.assign_task(t3.id, "Carol Diaz")
        self.executive_engine.assign_task(t4.id, "Alice Chen")
        self._project2_id = self._project2.id

    def _seed_workflows(self) -> None:
        wf = self.workflow_engine.create_workflow(
            name="AI Company OS Platform Build",
            description="Full software development lifecycle for the AI Company OS platform",
            template=WorkflowTemplate.SOFTWARE_PROJECT,
        )
        self._workflow_id = wf.id
        self.workflow_engine.start(wf.id)
        self.workflow_engine.advance(wf.id)

    def _seed_discussions(self) -> None:
        creator = DiscussionParticipant(
            participant_id="executive",
            name="Executive Engine",
            role="Coordinator",
            joined_at=datetime.now(timezone.utc),
        )
        disc = self.discussion_engine.start_discussion(
            topic="Tech stack selection for AI Company OS backend",
            project_id=self._project1_id,
            creator=creator,
        )
        p2 = DiscussionParticipant(
            participant_id="cto_agent",
            name="CTO Agent",
            role="Technical Lead",
            joined_at=datetime.now(timezone.utc),
        )
        self.discussion_engine.join(disc.id, p2)
        msg = DiscussionMessage(
            sender="executive",
            role="Coordinator",
            opinion="We should use FastAPI for all backend web interfaces.",
            reasoning="FastAPI provides async support, automatic OpenAPI documentation, "
                      "type safety via Pydantic, and excellent performance benchmarks.",
            timestamp=datetime.now(timezone.utc),
        )
        self.discussion_engine.post_message(disc.id, msg)
        outcome = DiscussionOutcome(
            decision="Adopt FastAPI as the primary backend framework",
            summary="Team agreed FastAPI provides the best balance of performance and "
                    "developer experience for the AI Company OS project requirements.",
            agreed_actions=["Configure FastAPI app structure", "Set up Pydantic models",
                            "Establish testing patterns with TestClient"],
            decided_by="CEO",
        )
        self.discussion_engine.close(disc.id, outcome)

        creator2 = DiscussionParticipant(
            participant_id="pm_agent",
            name="Product Manager",
            role="Product Owner",
            joined_at=datetime.now(timezone.utc),
        )
        self.discussion_engine.start_discussion(
            topic="Sprint 16 scope and feature priorities",
            project_id=self._project2_id,
            creator=creator2,
        )

    def _seed_decisions(self) -> None:
        opt_a = DecisionOption(
            title="PostgreSQL",
            advantages=["ACID compliance", "Rich query language", "Proven at scale", "JSON support"],
            disadvantages=["Requires server setup"],
            estimated_risk="LOW",
            estimated_cost="LOW",
        )
        opt_b = DecisionOption(
            title="SQLite",
            advantages=["Zero configuration", "Simple deployment", "Embedded"],
            disadvantages=["Limited concurrency", "Not production-ready at scale"],
            estimated_risk="MEDIUM",
            estimated_cost="LOW",
        )
        dec = self.decision_engine.create_decision(
            title="Choose primary database for AI Company OS",
            options=[opt_a, opt_b],
            project_id=self._project1_id,
        )
        self.decision_engine.evaluate(dec.id)
        self.decision_engine.recommend(dec.id)
        self._decision_id = dec.id

    def _seed_memory(self) -> None:
        entries = [
            MemoryEntry(
                id=str(uuid4()),
                title="Architecture Decision: Python Dataclasses for all models",
                category=MemoryCategory.DECISION,
                scope=MemoryScope.GLOBAL,
                author="CEO",
                content="All domain models use Python dataclasses for type safety, clarity, "
                        "and zero external dependency overhead.",
                tags=["architecture", "python", "dataclasses", "design"],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            MemoryEntry(
                id=str(uuid4()),
                title="Sprint 13 Completion: Workflow Engine delivered",
                category=MemoryCategory.PROJECT,
                scope=MemoryScope.GLOBAL,
                author="WorkflowEngine",
                content="Workflow Engine implemented with 320 unit tests. All green. "
                        "Supports 6 templates, approval gates, and memory integration.",
                tags=["sprint", "workflow", "completed", "milestone"],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            MemoryEntry(
                id=str(uuid4()),
                title="Sprint 14 Completion: Event Stream delivered",
                category=MemoryCategory.PROJECT,
                scope=MemoryScope.GLOBAL,
                author="EventStream",
                content="Central real-time event pipeline implemented with 314 unit tests. "
                        "Supports 8 channels with publish/subscribe and callback delivery.",
                tags=["sprint", "event-stream", "completed", "milestone"],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            MemoryEntry(
                id=str(uuid4()),
                title="Lesson Learned: Frozen dataclasses prevent mutation bugs",
                category=MemoryCategory.LESSON,
                scope=MemoryScope.GLOBAL,
                author="ExecutiveEngine",
                content="Using frozen=True on value objects (WorkflowStage, StreamEvent) "
                        "catches accidental mutation at runtime rather than introducing subtle bugs.",
                tags=["lesson", "design", "immutability", "best-practice"],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
        ]
        for entry in entries:
            self.memory_engine.store(entry)

    def _seed_events(self) -> None:
        events = [
            ("CompanyOrchestrator", StreamChannel.SYSTEM,
             {"action": "company_started", "company": "AI Company OS"}),
            ("ExecutiveEngine", StreamChannel.PROJECT,
             {"action": "project_created", "title": "AI Company OS Platform"}),
            ("WorkforceRegistry", StreamChannel.SYSTEM,
             {"action": "employee_hired", "name": "Alice Chen", "role": "BACKEND_AGENT"}),
            ("WorkforceRegistry", StreamChannel.SYSTEM,
             {"action": "employee_hired", "name": "Carol Diaz", "role": "FRONTEND_AGENT"}),
            ("WorkflowEngine", StreamChannel.WORKFLOW,
             {"action": "workflow_started", "name": "AI Company OS Platform Build"}),
            ("WorkflowEngine", StreamChannel.WORKFLOW,
             {"action": "stage_advanced", "stage": "Architecture Design"}),
            ("DiscussionEngine", StreamChannel.DISCUSSION,
             {"action": "discussion_started", "topic": "Tech stack selection"}),
            ("DiscussionEngine", StreamChannel.DISCUSSION,
             {"action": "discussion_closed", "topic": "Tech stack selection"}),
            ("DecisionEngine", StreamChannel.DECISION,
             {"action": "decision_created", "title": "Choose primary database"}),
            ("DecisionEngine", StreamChannel.DECISION,
             {"action": "decision_recommended", "title": "Choose primary database",
              "recommendation": "PostgreSQL"}),
            ("ExecutiveEngine", StreamChannel.PROJECT,
             {"action": "project_created", "title": "CEO Dashboard V1"}),
            ("MemoryEngine", StreamChannel.MEMORY,
             {"action": "entry_stored", "category": "DECISION",
              "title": "Architecture Decision: Python Dataclasses"}),
        ]
        for source, channel, payload in events:
            self.event_stream.publish(StreamEvent.create(source, channel, payload))

    def _seed_org(self) -> None:
        """Seed the OrgEngine with default roles, skills, departments, and employees."""
        # Roles
        backend_role = self.org_engine.create_role("Backend Agent", "Server-side development")
        frontend_role = self.org_engine.create_role("Frontend Agent", "Client-side development")
        qa_role = self.org_engine.create_role("QA Engineer", "Quality assurance and testing")
        devops_role = self.org_engine.create_role("DevOps Engineer", "Infrastructure and CI/CD")
        designer_role = self.org_engine.create_role("UI Designer", "Interface design and UX")
        researcher_role = self.org_engine.create_role("Research Analyst", "Market and technical research")

        # Skills
        self.org_engine.create_skill("Python", "Programming")
        self.org_engine.create_skill("FastAPI", "Framework")
        self.org_engine.create_skill("PostgreSQL", "Database")
        self.org_engine.create_skill("React", "Framework")
        self.org_engine.create_skill("TypeScript", "Programming")
        self.org_engine.create_skill("CSS", "Styling")
        self.org_engine.create_skill("Docker", "Infrastructure")
        self.org_engine.create_skill("CI/CD", "DevOps")
        self.org_engine.create_skill("Figma", "Design")
        self.org_engine.create_skill("SEO", "Marketing")

        # Departments
        backend_dept = self.org_engine.create_department("Backend Engineering", capacity=10)
        frontend_dept = self.org_engine.create_department("Frontend Engineering", capacity=8)
        qa_dept = self.org_engine.create_department("Quality Assurance", capacity=6)
        devops_dept = self.org_engine.create_department("DevOps", capacity=5)

        # Employees
        alice = self.org_engine.create_employee(
            "Alice Chen", backend_role.id, backend_dept.id,
            ["Python", "FastAPI", "PostgreSQL"], "anthropic"
        )
        bob = self.org_engine.create_employee(
            "Bob Kumar", backend_role.id, backend_dept.id,
            ["Python", "REST API", "SQL"], "anthropic"
        )
        carol = self.org_engine.create_employee(
            "Carol Diaz", frontend_role.id, frontend_dept.id,
            ["TypeScript", "React", "CSS"], "anthropic"
        )
        dave = self.org_engine.create_employee(
            "Dave Park", qa_role.id, qa_dept.id,
            ["Test Planning", "Automation", "Regression"], "anthropic"
        )
        eve = self.org_engine.create_employee(
            "Eve Singh", devops_role.id, devops_dept.id,
            ["Docker", "CI/CD", "Cloud Infrastructure"], "anthropic"
        )

        # Assign directors
        self.org_engine.assign_director(backend_dept.id, alice.id)
        self.org_engine.assign_director(frontend_dept.id, carol.id)
        self.org_engine.assign_director(qa_dept.id, dave.id)
        self.org_engine.assign_director(devops_dept.id, eve.id)

        # Assign current tasks (matching existing seeded project tasks)
        self.org_engine.assign_task(alice.id, "Design Core Architecture")
        self.org_engine.assign_task(bob.id, "Implement Memory Engine")

        self._seed_collab()

    def _seed_collab(self) -> None:
        """Seed the CollaborationHub with representative conversations."""
        hub = self.collab_hub

        # ── Security Review conversation ──────────────────────────────
        sec_conv = hub.create_from_template(
            TemplateType.SECURITY_REVIEW,
            creator="alice",
            title_override="API Authentication Security Review",
        )
        alice_p = ConversationParticipant("alice", "Alice Chen", "Backend Agent", "Backend Engineering")
        bob_p   = ConversationParticipant("bob",   "Bob Kumar",  "Security",       "Security")
        dave_p  = ConversationParticipant("dave",  "Dave Park",  "QA Engineer",    "Quality Assurance")
        hub.join(sec_conv.id, alice_p)
        hub.join(sec_conv.id, bob_p)
        hub.join(sec_conv.id, dave_p)

        hub.broadcast(sec_conv.id, "alice", MessageCategory.PROPOSAL,
                      "Proposing JWT RS256 for API authentication with 24-hour rotation.")
        hub.broadcast(sec_conv.id, "bob", MessageCategory.REVIEW,
                      "RS256 approved. Ensure JWKS endpoint is public and tokens are revocable.")
        hub.broadcast(sec_conv.id, "bob", MessageCategory.WARNING,
                      "Refresh tokens must be stored server-side, not in localStorage.")
        hub.broadcast(sec_conv.id, "dave", MessageCategory.REVIEW,
                      "QA will cover token expiry, rotation edge cases, and revocation paths.")
        hub.broadcast(sec_conv.id, "alice", MessageCategory.DECISION,
                      "Adopting JWT RS256 with 24h rotation, server-side refresh token store.")
        hub.summarize(sec_conv.id)

        # ── Architecture Review conversation ─────────────────────────
        arch_conv = hub.create_from_template(
            TemplateType.ARCHITECTURE_REVIEW,
            creator="alice",
            title_override="Microservices vs Monolith Architecture Decision",
        )
        carol_p = ConversationParticipant("carol", "Carol Diaz", "Frontend Agent", "Frontend Engineering")
        eve_p   = ConversationParticipant("eve",   "Eve Singh",  "DevOps Engineer","DevOps")
        hub.join(arch_conv.id, alice_p)
        hub.join(arch_conv.id, carol_p)
        hub.join(arch_conv.id, eve_p)
        hub.join(arch_conv.id, bob_p)

        hub.broadcast(arch_conv.id, "alice", MessageCategory.PROPOSAL,
                      "Recommend modular monolith for MVP. Decompose to microservices post-PMF.")
        hub.broadcast(arch_conv.id, "eve",   MessageCategory.REVIEW,
                      "Monolith reduces DevOps complexity at this stage. Agree with proposal.")
        hub.broadcast(arch_conv.id, "bob",   MessageCategory.RISK,
                      "Single deployment unit increases blast radius on security incidents.")
        hub.broadcast(arch_conv.id, "carol", MessageCategory.QUESTION,
                      "Will the API gateway still be a separate service?")
        hub.broadcast(arch_conv.id, "alice", MessageCategory.ANSWER,
                      "Yes — API gateway stays separate to allow independent scaling.")

        # ── Sprint Planning ───────────────────────────────────────────
        sprint_conv = hub.create_from_template(
            TemplateType.SPRINT_PLANNING,
            creator="exec",
            title_override="Sprint 22 Planning",
        )
        exec_p = ConversationParticipant("exec", "Executive AI", "Executive", "C-Suite")
        hub.join(sprint_conv.id, exec_p)
        hub.join(sprint_conv.id, alice_p)
        hub.join(sprint_conv.id, carol_p)
        hub.broadcast(sprint_conv.id, "exec",  MessageCategory.PROPOSAL,
                      "Sprint 22 goal: ship Collaboration Hub dashboard and run regression suite.")
        hub.broadcast(sprint_conv.id, "alice", MessageCategory.ANSWER,
                      "Backend capacity: 4 story points. Auth work spills from Sprint 21.")
        hub.broadcast(sprint_conv.id, "carol", MessageCategory.ANSWER,
                      "Frontend capacity: 5 story points. No blockers.")
        hub.broadcast(sprint_conv.id, "exec",  MessageCategory.DECISION,
                      "Sprint 22 approved. Backend: auth + API. Frontend: collaboration UI.")
