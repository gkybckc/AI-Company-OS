"""
Artifact Generation Engine for AI Company OS.

The ArtifactEngine produces deterministic, structured project artifacts from
current company state. It reads data from whichever engines are injected at
construction time and generates Markdown documents without any AI, networking,
or randomness.

Supported artifact types
------------------------
- PRD                    Product Requirements Document
- TECHNICAL_SPECIFICATION System architecture and implementation design
- API_SPECIFICATION       REST endpoint catalog with schemas
- DATABASE_SCHEMA         Entity/table definitions derived from project domain
- PROJECT_STRUCTURE       Directory and module layout
- TASK_REPORT             Task breakdown with status metrics
- CEO_REPORT              Company-wide executive status report
- SPRINT_REPORT           Sprint-level summary for a project

All injected engines are optional. When an engine is absent, the corresponding
section of the generated artifact falls back to minimal placeholder content
derived from the arguments provided to the generate method.

Architecture reference: §2 Core Components, §3 Layered Architecture.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from core.artifact import Artifact
from core.artifact_registry import ArtifactNotFoundError, ArtifactRegistry
from core.artifact_template import ArtifactTemplate
from core.artifact_type import ArtifactType


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ArtifactEngineError(Exception):
    """Base class for all ArtifactEngine errors."""


class InvalidArtifactRequestError(ArtifactEngineError):
    """Raised when a generate call receives invalid arguments."""


class ArtifactNotFoundError(ArtifactEngineError):
    """Raised when find_artifact() cannot locate the requested ID."""


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

_GENERATED_BY = "ArtifactEngine"


class ArtifactEngine:
    """
    Deterministic artifact generator for AI Company OS.

    Reads live state from injected engines and produces versioned Markdown
    artifacts. Each generated artifact is stored in an internal
    ArtifactRegistry so it can be retrieved later via history() or
    find_artifact().

    All generate_* methods are idempotent in the sense that calling them
    multiple times for the same (project_id, type) pair always produces a
    new artifact with an incremented version number.

    Constructor keyword arguments (all optional):
        executive_engine:     Source for Project and Task data.
        planner_engine:       Source for ProjectBlueprint (via analyze()).
        workflow_engine:      Source for Workflow history and statistics.
        memory_engine:        Source for MemoryEntry list.
        decision_engine:      Source for Decision history.
        company_orchestrator: Stored for reference; not currently queried.
    """

    def __init__(
        self,
        *,
        executive_engine: Any = None,
        planner_engine: Any = None,
        workflow_engine: Any = None,
        memory_engine: Any = None,
        decision_engine: Any = None,
        company_orchestrator: Any = None,
    ) -> None:
        self._executive_engine = executive_engine
        self._planner_engine = planner_engine
        self._workflow_engine = workflow_engine
        self._memory_engine = memory_engine
        self._decision_engine = decision_engine
        self._company_orchestrator = company_orchestrator

        self._registry = ArtifactRegistry()
        self._version_counters: Dict[Tuple[Optional[str], ArtifactType], int] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _next_version(self, project_id: Optional[str], artifact_type: ArtifactType) -> int:
        key = (project_id, artifact_type)
        current = self._version_counters.get(key, 0)
        self._version_counters[key] = current + 1
        return current + 1

    def _get_project(self, project_id: str) -> Optional[Any]:
        if self._executive_engine is None:
            return None
        return self._executive_engine._projects.get(project_id)

    def _get_tasks(self, project_id: str) -> List[Any]:
        if self._executive_engine is None:
            return []
        try:
            return self._executive_engine.list_tasks(project_id)
        except Exception:
            return []

    def _get_blueprint(self, project: Any, provided: Optional[Any]) -> Optional[Any]:
        if provided is not None:
            return provided
        if self._planner_engine is None or project is None:
            return None
        try:
            return self._planner_engine.analyze(project.objective)
        except Exception:
            return None

    def _get_all_projects(self) -> List[Any]:
        if self._executive_engine is None:
            return []
        return list(self._executive_engine._projects.values())

    def _get_workflows(self) -> List[Any]:
        if self._workflow_engine is None:
            return []
        try:
            return self._workflow_engine.history()
        except Exception:
            return []

    def _get_memory_entries(self) -> List[Any]:
        if self._memory_engine is None:
            return []
        try:
            return self._memory_engine.list_all()
        except Exception:
            return []

    def _get_decisions(self) -> List[Any]:
        if self._decision_engine is None:
            return []
        try:
            return self._decision_engine.history()
        except Exception:
            return []

    def _make_artifact(
        self,
        title: str,
        artifact_type: ArtifactType,
        project_id: Optional[str],
        content: str,
    ) -> Artifact:
        version = self._next_version(project_id, artifact_type)
        artifact = Artifact(
            id=str(uuid4()),
            title=title,
            type=artifact_type,
            project_id=project_id,
            generated_by=_GENERATED_BY,
            content=content,
            created_at=datetime.now(timezone.utc),
            version=version,
        )
        self._registry.register(artifact)
        return artifact

    # ------------------------------------------------------------------
    # Project artifact generators
    # ------------------------------------------------------------------

    def generate_prd(self, project_id: str, *, blueprint: Any = None) -> Artifact:
        """
        Generate a Product Requirements Document for the given project.

        Uses project data from executive_engine and blueprint data from
        planner_engine (or the provided blueprint parameter). Falls back
        to minimal content when engines are unavailable.

        Args:
            project_id: ID of the project to document.
            blueprint:  Optional pre-computed ProjectBlueprint. If omitted
                        and a planner_engine is attached, one is generated
                        from the project's objective.

        Returns:
            The generated Artifact (also stored in the internal registry).

        Raises:
            InvalidArtifactRequestError: If project_id is blank.
        """
        if not project_id or not project_id.strip():
            raise InvalidArtifactRequestError("project_id must not be blank.")

        project = self._get_project(project_id)
        tasks = self._get_tasks(project_id)
        bp = self._get_blueprint(project, blueprint)

        title = project.title if project else f"Project {project_id[:8]}"
        description = project.description if project else "Project description not available."
        objective = project.objective if project else "Objective not available."
        priority = project.priority.value if project and hasattr(project.priority, "value") else "MEDIUM"

        # Metadata block
        meta: Dict[str, Any] = {"Status": project.status.value if project and hasattr(project.status, "value") else "ACTIVE",
                                 "Priority": priority}
        if bp:
            meta["Project Type"] = str(bp.project_type)
            meta["Complexity"] = f"{bp.complexity_score}/10"
            meta["Estimated Tasks"] = bp.estimated_task_count
            meta["Estimated Sprints"] = bp.estimated_sprint_count
            meta["Team Size"] = bp.estimated_team_size

        # Build sections
        sections = []
        sections.append(
            ArtifactTemplate.render_section(
                "1. Executive Summary",
                f"{description}\n\n**Strategic Objective:** {objective}\n\n"
                + ArtifactTemplate.render_key_value(meta),
            )
        )

        sections.append(
            ArtifactTemplate.render_section(
                "2. Problem Statement",
                f"This Product Requirements Document defines the scope and requirements "
                f"for **{title}**. "
                + (f"The project is classified as a **{bp.project_type}** initiative." if bp else "")
                + f"\n\nThe primary driver is: {objective}",
            )
        )

        recommendations = bp.recommendations if bp else [
            "Define acceptance criteria for each functional requirement.",
            "Ensure all blocking dependencies are resolved before work begins.",
            "Review this document with all department leads before execution.",
        ]
        sections.append(
            ArtifactTemplate.render_section(
                "3. Goals and Objectives",
                f"**Primary Goal:** {objective}\n\n"
                "**Key Outcomes:**\n\n"
                + ArtifactTemplate.render_numbered_list(recommendations),
            )
        )

        dept_content = (
            ArtifactTemplate.render_department_list(bp.departments)
            if bp
            else "_Department breakdown requires planner_engine._"
        )
        sections.append(
            ArtifactTemplate.render_section(
                "4. Scope",
                "**In Scope:**\n\n"
                + dept_content
                + "\n\n**Out of Scope:**\n\n"
                "- Enhancements not described in the project objective\n"
                "- Infrastructure changes outside the stated architecture\n"
                "- Integrations not explicitly listed in the requirements",
            )
        )

        sections.append(
            ArtifactTemplate.render_section(
                "5. Functional Requirements",
                "The following tasks define the functional requirements:\n\n"
                + ArtifactTemplate.render_task_table(tasks),
            )
        )

        if bp and bp.risks:
            nfr_content = (
                "The following non-functional requirements are derived from the risk analysis:\n\n"
                + ArtifactTemplate.render_risk_list(bp.risks)
            )
        else:
            nfr_content = (
                "- Performance: System must respond within acceptable latency thresholds.\n"
                "- Security: All data must be handled in accordance with company standards.\n"
                "- Reliability: System must achieve high availability for production workloads.\n"
                "- Maintainability: Code must follow established patterns and include tests."
            )
        sections.append(ArtifactTemplate.render_section("6. Non-Functional Requirements", nfr_content))

        if bp and bp.risks:
            sections.append(
                ArtifactTemplate.render_section(
                    "7. Risk Assessment",
                    ArtifactTemplate.render_risk_list(bp.risks),
                )
            )

        sections.append(
            ArtifactTemplate.render_section(
                "8. Success Criteria",
                "- Project status reaches COMPLETED\n"
                "- All tasks in APPROVED or ARCHIVED state\n"
                "- Strategic objective achieved as defined by the CEO\n"
                "- Zero critical unresolved risks at delivery\n"
                "- All department leads sign off on their deliverables",
            )
        )

        header = ArtifactTemplate.render_header(
            ArtifactType.PRD.label(), title, project_id,
            _GENERATED_BY, self._version_counters.get((project_id, ArtifactType.PRD), 0) + 1,
            datetime.now(timezone.utc),
        )
        content = header + "".join(sections) + ArtifactTemplate.render_footer(_GENERATED_BY)

        return self._make_artifact(title, ArtifactType.PRD, project_id, content)

    def generate_technical_specification(
        self, project_id: str, *, blueprint: Any = None
    ) -> Artifact:
        """
        Generate a Technical Specification for the given project.

        Documents system architecture, module boundaries, data models,
        and integration points derived from project tasks and the blueprint.

        Args:
            project_id: ID of the project to document.
            blueprint:  Optional pre-computed ProjectBlueprint.

        Returns:
            The generated Artifact.

        Raises:
            InvalidArtifactRequestError: If project_id is blank.
        """
        if not project_id or not project_id.strip():
            raise InvalidArtifactRequestError("project_id must not be blank.")

        project = self._get_project(project_id)
        tasks = self._get_tasks(project_id)
        bp = self._get_blueprint(project, blueprint)

        title = project.title if project else f"Project {project_id[:8]}"
        objective = project.objective if project else "Objective not available."
        description = project.description if project else "Description not available."

        sections = []
        sections.append(
            ArtifactTemplate.render_section(
                "1. Overview",
                f"{description}\n\n**Technical Objective:** {objective}",
            )
        )

        tech_stack_rows = []
        if bp:
            for dr in bp.departments:
                dept = dr.department.value if hasattr(dr.department, "value") else str(dr.department)
                tech_stack_rows.append((dept, dr.rationale))
        if tech_stack_rows:
            stack_content = ArtifactTemplate.render_two_column_table(
                "Department", "Responsibility", tech_stack_rows
            )
        else:
            stack_content = (
                "- **Backend:** Core business logic, data processing, API layer\n"
                "- **Frontend:** User interface, client-side rendering\n"
                "- **QA:** Testing strategy, quality gates, regression coverage\n"
                "- **DevOps:** Build pipeline, deployment, infrastructure"
            )
        sections.append(ArtifactTemplate.render_section("2. System Architecture", stack_content))

        sections.append(
            ArtifactTemplate.render_section(
                "3. Module Breakdown",
                "The following tasks define the implementation modules:\n\n"
                + ArtifactTemplate.render_task_table(tasks),
            )
        )

        complexity = bp.complexity_score if bp else "N/A"
        sections.append(
            ArtifactTemplate.render_section(
                "4. Complexity and Estimates",
                ArtifactTemplate.render_key_value({
                    "Complexity Score": f"{complexity}/10",
                    "Estimated Tasks": bp.estimated_task_count if bp else len(tasks),
                    "Estimated Sprints": bp.estimated_sprint_count if bp else "TBD",
                    "Team Size": bp.estimated_team_size if bp else "TBD",
                    "Project Type": str(bp.project_type) if bp else "TBD",
                }),
            )
        )

        if bp and bp.risks:
            sections.append(
                ArtifactTemplate.render_section(
                    "5. Technical Risks",
                    ArtifactTemplate.render_risk_list(bp.risks),
                )
            )
        else:
            sections.append(
                ArtifactTemplate.render_section(
                    "5. Technical Risks",
                    "- Conduct risk analysis via PlannerEngine for a full risk profile.\n"
                    "- General risks: integration complexity, data consistency, deployment.",
                )
            )

        if bp and bp.recommendations:
            sections.append(
                ArtifactTemplate.render_section(
                    "6. Engineering Recommendations",
                    ArtifactTemplate.render_numbered_list(bp.recommendations),
                )
            )

        sections.append(
            ArtifactTemplate.render_section(
                "7. Testing Strategy",
                "- Unit tests for all core modules (minimum 90% branch coverage)\n"
                "- Integration tests exercising cross-module interactions\n"
                "- End-to-end tests for critical user-facing workflows\n"
                "- Performance benchmarks for high-traffic endpoints",
            )
        )

        header = ArtifactTemplate.render_header(
            ArtifactType.TECHNICAL_SPECIFICATION.label(), title, project_id,
            _GENERATED_BY,
            self._version_counters.get((project_id, ArtifactType.TECHNICAL_SPECIFICATION), 0) + 1,
            datetime.now(timezone.utc),
        )
        content = header + "".join(sections) + ArtifactTemplate.render_footer(_GENERATED_BY)
        return self._make_artifact(
            title, ArtifactType.TECHNICAL_SPECIFICATION, project_id, content
        )

    def generate_api_specification(
        self, project_id: str, *, blueprint: Any = None
    ) -> Artifact:
        """
        Generate an API Specification for the given project.

        Produces an endpoint catalog with HTTP methods, paths, request/response
        schemas, and error codes derived from the project type and tasks.

        Args:
            project_id: ID of the project to document.
            blueprint:  Optional pre-computed ProjectBlueprint.

        Returns:
            The generated Artifact.

        Raises:
            InvalidArtifactRequestError: If project_id is blank.
        """
        if not project_id or not project_id.strip():
            raise InvalidArtifactRequestError("project_id must not be blank.")

        project = self._get_project(project_id)
        tasks = self._get_tasks(project_id)
        bp = self._get_blueprint(project, blueprint)

        title = project.title if project else f"Project {project_id[:8]}"
        project_type = str(bp.project_type) if bp else "Generic"

        sections = []
        sections.append(
            ArtifactTemplate.render_section(
                "1. Overview",
                ArtifactTemplate.render_key_value({
                    "Base URL": "/api/v1",
                    "Protocol": "HTTPS",
                    "Authentication": "Bearer token (JWT)",
                    "Content-Type": "application/json",
                    "Project Type": project_type,
                }),
            )
        )

        endpoint_rows = [
            ("GET /api/v1/health", "Health check and system status"),
            ("GET /api/v1/status", "Application status and version"),
        ]
        for task in tasks:
            safe_name = task.title.lower().replace(" ", "-").replace("_", "-")
            endpoint_rows.append((f"POST /api/v1/{safe_name}", task.description[:60] + "..."))

        sections.append(
            ArtifactTemplate.render_section(
                "2. Endpoint Catalog",
                ArtifactTemplate.render_two_column_table("Endpoint", "Description", endpoint_rows),
            )
        )

        sections.append(
            ArtifactTemplate.render_section(
                "3. Standard Request Format",
                "```json\n"
                "{\n"
                '  "data": { ... },\n'
                '  "meta": {\n'
                '    "request_id": "uuid",\n'
                '    "timestamp": "ISO-8601"\n'
                "  }\n"
                "}\n"
                "```",
            )
        )

        sections.append(
            ArtifactTemplate.render_section(
                "4. Standard Response Format",
                "```json\n"
                "{\n"
                '  "success": true,\n'
                '  "data": { ... },\n'
                '  "meta": {\n'
                '    "request_id": "uuid",\n'
                '    "generated_at": "ISO-8601",\n'
                '    "version": "1.0.0"\n'
                "  }\n"
                "}\n"
                "```",
            )
        )

        sections.append(
            ArtifactTemplate.render_section(
                "5. Error Codes",
                ArtifactTemplate.render_two_column_table(
                    "HTTP Status", "Meaning",
                    [
                        ("200 OK", "Request succeeded"),
                        ("201 Created", "Resource created successfully"),
                        ("400 Bad Request", "Invalid request payload"),
                        ("401 Unauthorized", "Missing or invalid authentication"),
                        ("403 Forbidden", "Insufficient permissions"),
                        ("404 Not Found", "Resource does not exist"),
                        ("409 Conflict", "Duplicate resource or state conflict"),
                        ("422 Unprocessable Entity", "Validation error"),
                        ("500 Internal Server Error", "Unexpected server error"),
                    ],
                ),
            )
        )

        if bp and bp.risks:
            sections.append(
                ArtifactTemplate.render_section(
                    "6. Security Considerations",
                    ArtifactTemplate.render_risk_list(bp.risks),
                )
            )

        header = ArtifactTemplate.render_header(
            ArtifactType.API_SPECIFICATION.label(), title, project_id,
            _GENERATED_BY,
            self._version_counters.get((project_id, ArtifactType.API_SPECIFICATION), 0) + 1,
            datetime.now(timezone.utc),
        )
        content = header + "".join(sections) + ArtifactTemplate.render_footer(_GENERATED_BY)
        return self._make_artifact(
            title, ArtifactType.API_SPECIFICATION, project_id, content
        )

    def generate_database_schema(
        self, project_id: str, *, blueprint: Any = None
    ) -> Artifact:
        """
        Generate a Database Schema document for the given project.

        Produces entity definitions derived from the project domain, task
        titles, and project type detected by the planner.

        Args:
            project_id: ID of the project to document.
            blueprint:  Optional pre-computed ProjectBlueprint.

        Returns:
            The generated Artifact.

        Raises:
            InvalidArtifactRequestError: If project_id is blank.
        """
        if not project_id or not project_id.strip():
            raise InvalidArtifactRequestError("project_id must not be blank.")

        project = self._get_project(project_id)
        tasks = self._get_tasks(project_id)
        bp = self._get_blueprint(project, blueprint)

        title = project.title if project else f"Project {project_id[:8]}"

        sections = []
        sections.append(
            ArtifactTemplate.render_section(
                "1. Overview",
                ArtifactTemplate.render_key_value({
                    "Database Engine": "PostgreSQL (recommended)",
                    "Schema Version": "1.0",
                    "Project": title,
                    "Project Type": str(bp.project_type) if bp else "Generic",
                }),
            )
        )

        # Core entities derived from tasks
        entity_rows = [("id", "UUID PRIMARY KEY", "Unique identifier")]
        entity_rows += [("created_at", "TIMESTAMPTZ NOT NULL", "UTC creation timestamp")]
        entity_rows += [("updated_at", "TIMESTAMPTZ NOT NULL", "UTC last-modified timestamp")]
        entity_rows += [("status", "VARCHAR(32) NOT NULL", "Record lifecycle status")]

        sections.append(
            ArtifactTemplate.render_section(
                "2. Common Fields (all tables)",
                ArtifactTemplate.render_two_column_table(
                    "Column", "Type",
                    [(col, typ) for col, typ, _ in entity_rows],
                ),
            )
        )

        # Build a table per task (each task maps to a domain entity)
        entity_tables = []
        for task in tasks:
            safe_name = task.title.lower().replace(" ", "_")
            entity_tables.append(
                f"### Table: `{safe_name}`\n\n"
                f"_Derived from task: {task.title}_\n\n"
                "| Column | Type | Notes |\n"
                "|--------|------|-------|\n"
                "| id | UUID PRIMARY KEY | Unique identifier |\n"
                f"| title | VARCHAR(255) NOT NULL | {task.title} |\n"
                "| description | TEXT | Detailed description |\n"
                "| status | VARCHAR(32) NOT NULL | Lifecycle state |\n"
                f"| assigned_to | VARCHAR(255) | Assigned agent: {task.assigned_agent} |\n"
                "| created_at | TIMESTAMPTZ NOT NULL | UTC creation time |\n"
                "| updated_at | TIMESTAMPTZ NOT NULL | UTC modification time |\n"
            )
        if entity_tables:
            sections.append(
                ArtifactTemplate.render_section(
                    "3. Entity Definitions",
                    "\n".join(entity_tables),
                )
            )
        else:
            sections.append(
                ArtifactTemplate.render_section(
                    "3. Entity Definitions",
                    "_No tasks available to derive entities. Add tasks to project first._",
                )
            )

        sections.append(
            ArtifactTemplate.render_section(
                "4. Indexing Strategy",
                "- All primary keys use UUID with B-Tree index\n"
                "- `status` columns carry partial indexes for active-record queries\n"
                "- `created_at` carries a B-Tree index for range scans\n"
                "- Foreign keys carry indexes to support JOIN performance",
            )
        )

        sections.append(
            ArtifactTemplate.render_section(
                "5. Migration Strategy",
                "- Use sequential numbered migration files (e.g., `0001_initial.sql`)\n"
                "- All schema changes are applied via migration scripts\n"
                "- Never modify production data directly\n"
                "- Each migration must be reversible with a corresponding rollback script",
            )
        )

        header = ArtifactTemplate.render_header(
            ArtifactType.DATABASE_SCHEMA.label(), title, project_id,
            _GENERATED_BY,
            self._version_counters.get((project_id, ArtifactType.DATABASE_SCHEMA), 0) + 1,
            datetime.now(timezone.utc),
        )
        content = header + "".join(sections) + ArtifactTemplate.render_footer(_GENERATED_BY)
        return self._make_artifact(
            title, ArtifactType.DATABASE_SCHEMA, project_id, content
        )

    def generate_project_structure(
        self, project_id: str, *, blueprint: Any = None
    ) -> Artifact:
        """
        Generate a Project Structure document for the given project.

        Produces a recommended directory layout and module organization
        derived from the project type and department composition.

        Args:
            project_id: ID of the project to document.
            blueprint:  Optional pre-computed ProjectBlueprint.

        Returns:
            The generated Artifact.

        Raises:
            InvalidArtifactRequestError: If project_id is blank.
        """
        if not project_id or not project_id.strip():
            raise InvalidArtifactRequestError("project_id must not be blank.")

        project = self._get_project(project_id)
        bp = self._get_blueprint(project, blueprint)

        title = project.title if project else f"Project {project_id[:8]}"
        safe_name = title.lower().replace(" ", "_")

        sections = []
        sections.append(
            ArtifactTemplate.render_section(
                "1. Overview",
                ArtifactTemplate.render_key_value({
                    "Project": title,
                    "Project Type": str(bp.project_type) if bp else "Generic",
                    "Primary Language": "Python 3.10+",
                    "Package Manager": "pip / venv",
                }),
            )
        )

        dept_dirs = []
        if bp:
            for dr in bp.departments:
                dept = dr.department.value if hasattr(dr.department, "value") else str(dr.department)
                dept_dirs.append(f"    {dept.lower()}/          # {dr.rationale}")
        else:
            dept_dirs = [
                "    backend/            # Core business logic",
                "    frontend/           # User interface",
                "    tests/              # Automated test suite",
            ]

        tree = (
            "```\n"
            f"{safe_name}/\n"
            "    core/               # Domain models and business logic\n"
            + "\n".join(dept_dirs) + "\n"
            "    tests/              # Unit and integration tests\n"
            "    examples/           # Usage examples and demos\n"
            "    docs/               # Project documentation\n"
            "    .ai/                # AI Company OS project configuration\n"
            "    requirements.txt    # Python dependencies\n"
            "    README.md           # Project overview\n"
            "    setup.py            # Package configuration\n"
            "```\n"
        )
        sections.append(ArtifactTemplate.render_section("2. Directory Layout", tree))

        sections.append(
            ArtifactTemplate.render_section(
                "3. Naming Conventions",
                "- Module files: `snake_case.py`\n"
                "- Classes: `PascalCase`\n"
                "- Functions/methods: `snake_case`\n"
                "- Constants: `UPPER_SNAKE_CASE`\n"
                "- Test files: `test_<module>.py` under `tests/`\n"
                "- Example files: `demo_<feature>.py` under `examples/`",
            )
        )

        sections.append(
            ArtifactTemplate.render_section(
                "4. Module Organization",
                "- Each domain concept lives in its own module file\n"
                "- Engines and registries are separate from their domain models\n"
                "- All public APIs are defined at module top level\n"
                "- No circular imports between core modules",
            )
        )

        header = ArtifactTemplate.render_header(
            ArtifactType.PROJECT_STRUCTURE.label(), title, project_id,
            _GENERATED_BY,
            self._version_counters.get((project_id, ArtifactType.PROJECT_STRUCTURE), 0) + 1,
            datetime.now(timezone.utc),
        )
        content = header + "".join(sections) + ArtifactTemplate.render_footer(_GENERATED_BY)
        return self._make_artifact(
            title, ArtifactType.PROJECT_STRUCTURE, project_id, content
        )

    def generate_task_report(self, project_id: str) -> Artifact:
        """
        Generate a Task Report for the given project.

        Documents all tasks with their statuses, blocked tasks, and
        completion metrics.

        Args:
            project_id: ID of the project to report on.

        Returns:
            The generated Artifact.

        Raises:
            InvalidArtifactRequestError: If project_id is blank.
        """
        if not project_id or not project_id.strip():
            raise InvalidArtifactRequestError("project_id must not be blank.")

        project = self._get_project(project_id)
        tasks = self._get_tasks(project_id)

        title = project.title if project else f"Project {project_id[:8]}"

        # Build status metrics
        status_counts: Dict[str, int] = {}
        for task in tasks:
            key = task.status.value if hasattr(task.status, "value") else str(task.status)
            status_counts[key] = status_counts.get(key, 0) + 1

        total = len(tasks)
        approved = status_counts.get("APPROVED", 0)
        completion_pct = round((approved / total * 100.0) if total > 0 else 0.0, 2)

        # Blocked tasks (have dependencies not yet APPROVED)
        approved_ids = {t.id for t in tasks if t.status.value == "APPROVED"} if tasks else set()
        blocked = [t for t in tasks if t.dependencies and
                   any(dep not in approved_ids for dep in t.dependencies)]

        sections = []
        sections.append(
            ArtifactTemplate.render_section(
                "1. Summary",
                ArtifactTemplate.render_key_value({
                    "Project": title,
                    "Total Tasks": total,
                    "Completion": f"{completion_pct}%",
                    "Approved Tasks": approved,
                    "Blocked Tasks": len(blocked),
                    "Status": project.status.value if project and hasattr(project.status, "value") else "ACTIVE",
                }),
            )
        )

        sections.append(
            ArtifactTemplate.render_section(
                "2. Status Breakdown",
                ArtifactTemplate.render_key_value(status_counts) if status_counts
                else "_No tasks._",
            )
        )

        sections.append(
            ArtifactTemplate.render_section(
                "3. Task Details",
                ArtifactTemplate.render_task_table(tasks),
            )
        )

        if blocked:
            blocked_lines = [
                f"- **{t.title}** (ID: `{t.id[:8]}...`) — waiting on {len(t.dependencies)} dependency/ies"
                for t in blocked
            ]
            sections.append(
                ArtifactTemplate.render_section(
                    "4. Blocked Tasks",
                    "\n".join(blocked_lines),
                )
            )
        else:
            sections.append(
                ArtifactTemplate.render_section(
                    "4. Blocked Tasks",
                    "_No blocked tasks._",
                )
            )

        header = ArtifactTemplate.render_header(
            ArtifactType.TASK_REPORT.label(), title, project_id,
            _GENERATED_BY,
            self._version_counters.get((project_id, ArtifactType.TASK_REPORT), 0) + 1,
            datetime.now(timezone.utc),
        )
        content = header + "".join(sections) + ArtifactTemplate.render_footer(_GENERATED_BY)
        return self._make_artifact(title, ArtifactType.TASK_REPORT, project_id, content)

    def generate_sprint_report(
        self, project_id: str, *, sprint_number: int = 1
    ) -> Artifact:
        """
        Generate a Sprint Report for the given project.

        Documents sprint-level progress, velocity, and next-sprint goals
        based on task states and project data.

        Args:
            project_id:    ID of the project.
            sprint_number: Sprint number being reported. Defaults to 1.

        Returns:
            The generated Artifact.

        Raises:
            InvalidArtifactRequestError: If project_id is blank or
                sprint_number is less than 1.
        """
        if not project_id or not project_id.strip():
            raise InvalidArtifactRequestError("project_id must not be blank.")
        if sprint_number < 1:
            raise InvalidArtifactRequestError("sprint_number must be >= 1.")

        project = self._get_project(project_id)
        tasks = self._get_tasks(project_id)

        title = project.title if project else f"Project {project_id[:8]}"
        sprint_title = f"Sprint {sprint_number} Report — {title}"

        total = len(tasks)
        approved = sum(1 for t in tasks if t.status.value == "APPROVED")
        working = sum(1 for t in tasks if t.status.value in ("WORKING", "REVIEW"))
        remaining = total - approved
        velocity = approved  # tasks approved = velocity for this report

        sections = []
        sections.append(
            ArtifactTemplate.render_section(
                f"1. Sprint {sprint_number} Summary",
                ArtifactTemplate.render_key_value({
                    "Project": title,
                    "Sprint Number": sprint_number,
                    "Total Tasks": total,
                    "Completed (APPROVED)": approved,
                    "In Progress": working,
                    "Remaining": remaining,
                    "Velocity (tasks approved)": velocity,
                    "Completion": f"{round((approved/total*100.0) if total > 0 else 0.0, 2)}%",
                }),
            )
        )

        sections.append(
            ArtifactTemplate.render_section(
                "2. Task Status",
                ArtifactTemplate.render_task_table(tasks),
            )
        )

        completed_tasks = [t for t in tasks if t.status.value == "APPROVED"]
        if completed_tasks:
            done_lines = [f"- {t.title} (assigned: {t.assigned_agent})" for t in completed_tasks]
            sections.append(
                ArtifactTemplate.render_section(
                    "3. Completed This Sprint",
                    "\n".join(done_lines),
                )
            )
        else:
            sections.append(
                ArtifactTemplate.render_section(
                    "3. Completed This Sprint",
                    "_No tasks approved yet._",
                )
            )

        in_progress = [t for t in tasks if t.status.value in ("WORKING", "REVIEW", "ASSIGNED")]
        if in_progress:
            ip_lines = [f"- {t.title} [{t.status.value}] (assigned: {t.assigned_agent})"
                        for t in in_progress]
            sections.append(
                ArtifactTemplate.render_section(
                    "4. In Progress",
                    "\n".join(ip_lines),
                )
            )

        sections.append(
            ArtifactTemplate.render_section(
                f"5. Next Sprint (Sprint {sprint_number + 1}) Goals",
                f"- Continue work on {remaining} remaining tasks\n"
                "- Resolve any blocked dependencies\n"
                "- Conduct sprint retrospective\n"
                "- Update task priorities based on CEO feedback",
            )
        )

        header = ArtifactTemplate.render_header(
            ArtifactType.SPRINT_REPORT.label(), sprint_title, project_id,
            _GENERATED_BY,
            self._version_counters.get((project_id, ArtifactType.SPRINT_REPORT), 0) + 1,
            datetime.now(timezone.utc),
        )
        content = header + "".join(sections) + ArtifactTemplate.render_footer(_GENERATED_BY)
        return self._make_artifact(sprint_title, ArtifactType.SPRINT_REPORT, project_id, content)

    # ------------------------------------------------------------------
    # Company-wide artifact generators
    # ------------------------------------------------------------------

    def generate_ceo_report(self, company_name: str = "AI Company OS") -> Artifact:
        """
        Generate a company-wide CEO Report.

        Aggregates data from all injected engines to produce an executive
        status report covering projects, workforce, workflows, decisions,
        and memory.

        Args:
            company_name: Name of the company. Defaults to "AI Company OS".

        Returns:
            The generated Artifact (project_id is None for company-wide reports).
        """
        if not company_name or not company_name.strip():
            company_name = "AI Company OS"

        all_projects = self._get_all_projects()
        all_decisions = self._get_decisions()
        all_memory = self._get_memory_entries()
        all_workflows = self._get_workflows()

        active_projects = [p for p in all_projects
                           if hasattr(p.status, "value") and p.status.value == "ACTIVE"]

        sections = []

        # Executive summary
        project_count = len(all_projects)
        active_count = len(active_projects)
        sections.append(
            ArtifactTemplate.render_section(
                "1. Executive Summary",
                ArtifactTemplate.render_key_value({
                    "Company": company_name,
                    "Total Projects": project_count,
                    "Active Projects": active_count,
                    "Total Decisions": len(all_decisions),
                    "Memory Entries": len(all_memory),
                    "Active Workflows": len(all_workflows),
                }),
            )
        )

        # Projects overview
        if all_projects:
            proj_rows = []
            for p in all_projects:
                status = p.status.value if hasattr(p.status, "value") else str(p.status)
                priority = p.priority.value if hasattr(p.priority, "value") else str(p.priority)
                task_count = len(p.tasks) if hasattr(p, "tasks") else "N/A"
                proj_rows.append((p.title, f"{status} | {priority} | {task_count} tasks"))
            sections.append(
                ArtifactTemplate.render_section(
                    "2. Projects",
                    ArtifactTemplate.render_two_column_table("Project", "Status | Priority | Tasks", proj_rows),
                )
            )
        else:
            sections.append(
                ArtifactTemplate.render_section("2. Projects", "_No projects registered._")
            )

        # Workflow status
        if all_workflows:
            sections.append(
                ArtifactTemplate.render_section(
                    "3. Workflow Status",
                    ArtifactTemplate.render_workflow_list(all_workflows),
                )
            )
        else:
            sections.append(
                ArtifactTemplate.render_section("3. Workflow Status", "_No workflows found._")
            )

        # Decision history
        if all_decisions:
            sections.append(
                ArtifactTemplate.render_section(
                    "4. Recent Decisions",
                    ArtifactTemplate.render_decision_list(all_decisions[-5:]),
                )
            )
        else:
            sections.append(
                ArtifactTemplate.render_section("4. Recent Decisions", "_No decisions found._")
            )

        # Memory highlights
        if all_memory:
            sections.append(
                ArtifactTemplate.render_section(
                    "5. Memory Highlights",
                    ArtifactTemplate.render_memory_list(all_memory[-5:]),
                )
            )
        else:
            sections.append(
                ArtifactTemplate.render_section("5. Memory Highlights", "_No memory entries found._")
            )

        # Workflow engine stats
        if self._workflow_engine is not None:
            try:
                wf_stats = self._workflow_engine.statistics()
                sections.append(
                    ArtifactTemplate.render_section(
                        "6. Workflow Statistics",
                        ArtifactTemplate.render_key_value(wf_stats),
                    )
                )
            except Exception:
                pass

        # Decision engine stats
        if self._decision_engine is not None:
            try:
                dec_stats = self._decision_engine.statistics()
                sections.append(
                    ArtifactTemplate.render_section(
                        "7. Decision Statistics",
                        ArtifactTemplate.render_key_value(dec_stats),
                    )
                )
            except Exception:
                pass

        sections.append(
            ArtifactTemplate.render_section(
                "8. Recommendations",
                "- Review all ACTIVE projects for blockers\n"
                "- Ensure all PENDING decisions have been evaluated\n"
                "- Archive completed projects to maintain registry clarity\n"
                "- Review memory entries for learnable patterns",
            )
        )

        title = f"{company_name} CEO Report"
        header = ArtifactTemplate.render_header(
            ArtifactType.CEO_REPORT.label(), title, None,
            _GENERATED_BY,
            self._version_counters.get((None, ArtifactType.CEO_REPORT), 0) + 1,
            datetime.now(timezone.utc),
        )
        content = header + "".join(sections) + ArtifactTemplate.render_footer(_GENERATED_BY)
        return self._make_artifact(title, ArtifactType.CEO_REPORT, None, content)

    # ------------------------------------------------------------------
    # Registry accessors
    # ------------------------------------------------------------------

    def history(self) -> List[Artifact]:
        """Return all generated artifacts in creation order."""
        return self._registry.list_all()

    def statistics(self) -> Dict[str, Any]:
        """Return generation statistics across all artifact types."""
        reg_stats = self._registry.statistics()
        return {
            "total_artifacts": reg_stats["total_artifacts"],
            "type_counts": reg_stats["type_counts"],
            "unique_projects": reg_stats["unique_projects"],
            "unique_generators": reg_stats["unique_generators"],
            "version_counters": {
                f"{str(t)}:{pid}": v
                for (pid, t), v in self._version_counters.items()
            },
        }

    def find_artifact(self, artifact_id: str) -> Artifact:
        """
        Retrieve a previously generated artifact by its ID.

        Args:
            artifact_id: ID of the artifact to retrieve.

        Returns:
            The matching Artifact.

        Raises:
            ArtifactNotFoundError: If the ID is not found in history.
        """
        try:
            return self._registry.get(artifact_id)
        except Exception:
            raise ArtifactNotFoundError(
                f"Artifact '{artifact_id}' not found in engine history."
            )
