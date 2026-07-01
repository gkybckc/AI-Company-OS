"""
Unit tests for the Artifact Generation Engine (Sprint 16).

Covers:
  - ArtifactType enum
  - Artifact dataclass
  - ArtifactTemplate static helpers
  - ArtifactRegistry CRUD and filtering
  - ArtifactEngine all generate_* methods (standalone and with real engines)
  - ArtifactEngine history(), statistics(), find_artifact()
  - Versioning behaviour
  - Edge cases and error paths
"""

import unittest
from datetime import datetime, timezone
from uuid import uuid4

from core.artifact import Artifact
from core.artifact_engine import (
    ArtifactEngine,
    ArtifactEngineError,
    ArtifactNotFoundError as EngineArtifactNotFoundError,
    InvalidArtifactRequestError,
)
from core.artifact_registry import (
    ArtifactNotFoundError,
    ArtifactRegistry,
    DuplicateArtifactError,
)
from core.artifact_template import ArtifactTemplate
from core.artifact_type import ArtifactType

# ---------------------------------------------------------------------------
# Real engine imports (integration)
# ---------------------------------------------------------------------------
from core.decision_engine import DecisionEngine
from core.decision_option import DecisionOption
from core.executive_engine import ExecutiveEngine
from core.memory_engine import MemoryEngine
from core.memory_entry import MemoryEntry
from core.memory_category import MemoryCategory
from core.memory_scope import MemoryScope
from core.planner_engine import PlannerEngine
from core.task import Priority
from core.workflow_engine import WorkflowEngine
from core.workflow_template import WorkflowTemplate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_artifact(
    art_id=None,
    title="Test Artifact",
    artifact_type=ArtifactType.PRD,
    project_id="proj-1",
    generated_by="TestEngine",
    content="Test content line one.\nLine two.\nLine three.",
    version=1,
) -> Artifact:
    return Artifact(
        id=art_id or str(uuid4()),
        title=title,
        type=artifact_type,
        project_id=project_id,
        generated_by=generated_by,
        content=content,
        created_at=datetime.now(timezone.utc),
        version=version,
    )


def _make_engine_with_project():
    """Return (ArtifactEngine, project_id) with a seeded ExecutiveEngine."""
    ee = ExecutiveEngine()
    proj = ee.create_project(
        title="Test Project",
        description="A test project description.",
        objective="Deliver a working test system.",
        priority=Priority.HIGH,
    )
    t1 = ee.create_task(proj.id, "Design Module", "Design the core module.", "Alice", Priority.HIGH)
    ee.create_task(proj.id, "Implement Module", "Build the module.", "Bob", Priority.MEDIUM,
                   dependencies=[t1.id])
    return ArtifactEngine(executive_engine=ee), proj.id


def _make_full_engine():
    """Return (ArtifactEngine, project_id) with all engines attached."""
    ee = ExecutiveEngine()
    proj = ee.create_project(
        title="Full Engine Project",
        description="Testing full artifact generation pipeline.",
        objective="Build an e-commerce platform with payments and authentication.",
        priority=Priority.HIGH,
    )
    t1 = ee.create_task(proj.id, "Auth Module", "Implement authentication.", "Alice", Priority.HIGH)
    ee.create_task(proj.id, "Payment Gateway", "Integrate payment provider.", "Bob",
                   Priority.HIGH, dependencies=[t1.id])

    me = MemoryEngine()
    me.store(MemoryEntry(
        id=str(uuid4()),
        title="Test memory entry",
        category=MemoryCategory.DECISION,
        scope=MemoryScope.GLOBAL,
        author="TestAgent",
        content="Test memory content.",
        tags={"test"},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    ))

    de = DecisionEngine(memory_engine=me)
    dec = de.create_decision(
        title="Choose framework",
        options=[
            DecisionOption(title="FastAPI", advantages=["fast", "typed"], disadvantages=[], estimated_risk="LOW", estimated_cost="LOW"),
            DecisionOption(title="Flask", advantages=["simple"], disadvantages=["no typing"], estimated_risk="LOW", estimated_cost="LOW"),
        ],
        project_id=proj.id,
    )
    de.evaluate(dec.id)
    de.recommend(dec.id)

    we = WorkflowEngine(memory_engine=me, decision_engine=de)
    wf = we.create_workflow(
        name="Test Workflow",
        description="Test workflow for artifact engine.",
        template=WorkflowTemplate.SOFTWARE_PROJECT,
    )
    we.start(wf.id)

    pe = PlannerEngine()

    engine = ArtifactEngine(
        executive_engine=ee,
        planner_engine=pe,
        workflow_engine=we,
        memory_engine=me,
        decision_engine=de,
    )
    return engine, proj.id


# ===========================================================================
# TestArtifactTypeEnum
# ===========================================================================

class TestArtifactTypeEnum(unittest.TestCase):

    def test_prd_value(self):
        self.assertEqual(ArtifactType.PRD.value, "PRD")

    def test_technical_spec_value(self):
        self.assertEqual(ArtifactType.TECHNICAL_SPECIFICATION.value, "TECHNICAL_SPECIFICATION")

    def test_api_spec_value(self):
        self.assertEqual(ArtifactType.API_SPECIFICATION.value, "API_SPECIFICATION")

    def test_database_schema_value(self):
        self.assertEqual(ArtifactType.DATABASE_SCHEMA.value, "DATABASE_SCHEMA")

    def test_project_structure_value(self):
        self.assertEqual(ArtifactType.PROJECT_STRUCTURE.value, "PROJECT_STRUCTURE")

    def test_task_report_value(self):
        self.assertEqual(ArtifactType.TASK_REPORT.value, "TASK_REPORT")

    def test_ceo_report_value(self):
        self.assertEqual(ArtifactType.CEO_REPORT.value, "CEO_REPORT")

    def test_sprint_report_value(self):
        self.assertEqual(ArtifactType.SPRINT_REPORT.value, "SPRINT_REPORT")

    def test_str_prd(self):
        self.assertEqual(str(ArtifactType.PRD), "PRD")

    def test_str_ceo_report(self):
        self.assertEqual(str(ArtifactType.CEO_REPORT), "CEO_REPORT")

    def test_label_prd(self):
        self.assertEqual(ArtifactType.PRD.label(), "Product Requirements Document")

    def test_label_technical_specification(self):
        self.assertEqual(ArtifactType.TECHNICAL_SPECIFICATION.label(), "Technical Specification")

    def test_label_api_specification(self):
        self.assertEqual(ArtifactType.API_SPECIFICATION.label(), "API Specification")

    def test_label_database_schema(self):
        self.assertEqual(ArtifactType.DATABASE_SCHEMA.label(), "Database Schema")

    def test_label_project_structure(self):
        self.assertEqual(ArtifactType.PROJECT_STRUCTURE.label(), "Project Structure")

    def test_label_task_report(self):
        self.assertEqual(ArtifactType.TASK_REPORT.label(), "Task Report")

    def test_label_ceo_report(self):
        self.assertEqual(ArtifactType.CEO_REPORT.label(), "CEO Report")

    def test_label_sprint_report(self):
        self.assertEqual(ArtifactType.SPRINT_REPORT.label(), "Sprint Report")

    def test_is_string_instance(self):
        self.assertIsInstance(ArtifactType.PRD, str)

    def test_total_types(self):
        self.assertEqual(len(ArtifactType), 8)

    def test_membership_prd(self):
        self.assertIn(ArtifactType.PRD, ArtifactType)

    def test_membership_ceo_report(self):
        self.assertIn(ArtifactType.CEO_REPORT, ArtifactType)

    def test_equality_with_string(self):
        self.assertEqual(ArtifactType.PRD, "PRD")


# ===========================================================================
# TestArtifactDataclass
# ===========================================================================

class TestArtifactDataclass(unittest.TestCase):

    def setUp(self):
        self.artifact = _make_artifact(
            content="Word one two three.\nSecond line here.\nThird line."
        )

    def test_id_is_string(self):
        self.assertIsInstance(self.artifact.id, str)

    def test_title(self):
        self.assertEqual(self.artifact.title, "Test Artifact")

    def test_type(self):
        self.assertEqual(self.artifact.type, ArtifactType.PRD)

    def test_project_id(self):
        self.assertEqual(self.artifact.project_id, "proj-1")

    def test_generated_by(self):
        self.assertEqual(self.artifact.generated_by, "TestEngine")

    def test_version_default(self):
        self.assertEqual(self.artifact.version, 1)

    def test_version_custom(self):
        a = _make_artifact(version=5)
        self.assertEqual(a.version, 5)

    def test_created_at_is_datetime(self):
        self.assertIsInstance(self.artifact.created_at, datetime)

    def test_content_stored(self):
        self.assertIn("Word one", self.artifact.content)

    def test_word_count_positive(self):
        self.assertGreater(self.artifact.word_count(), 0)

    def test_word_count_empty_content(self):
        a = _make_artifact(content="")
        self.assertEqual(a.word_count(), 0)

    def test_word_count_whitespace_only(self):
        a = _make_artifact(content="   ")
        self.assertEqual(a.word_count(), 0)

    def test_word_count_single_word(self):
        a = _make_artifact(content="hello")
        self.assertEqual(a.word_count(), 1)

    def test_line_count_positive(self):
        self.assertGreater(self.artifact.line_count(), 0)

    def test_line_count_single_line(self):
        a = _make_artifact(content="single line no newline")
        self.assertEqual(a.line_count(), 1)

    def test_line_count_multi_line(self):
        a = _make_artifact(content="line1\nline2\nline3")
        self.assertEqual(a.line_count(), 3)

    def test_line_count_empty_content(self):
        a = _make_artifact(content="")
        self.assertEqual(a.line_count(), 0)

    def test_summary_is_dict(self):
        s = self.artifact.summary()
        self.assertIsInstance(s, dict)

    def test_summary_has_id(self):
        self.assertIn("id", self.artifact.summary())

    def test_summary_has_title(self):
        self.assertIn("title", self.artifact.summary())

    def test_summary_has_type(self):
        s = self.artifact.summary()
        self.assertEqual(s["type"], "PRD")

    def test_summary_has_project_id(self):
        s = self.artifact.summary()
        self.assertEqual(s["project_id"], "proj-1")

    def test_summary_has_generated_by(self):
        s = self.artifact.summary()
        self.assertEqual(s["generated_by"], "TestEngine")

    def test_summary_has_version(self):
        s = self.artifact.summary()
        self.assertEqual(s["version"], 1)

    def test_summary_has_word_count(self):
        s = self.artifact.summary()
        self.assertIn("word_count", s)
        self.assertIsInstance(s["word_count"], int)

    def test_summary_has_line_count(self):
        s = self.artifact.summary()
        self.assertIn("line_count", s)

    def test_summary_has_created_at(self):
        s = self.artifact.summary()
        self.assertIn("created_at", s)

    def test_is_for_project_true(self):
        self.assertTrue(self.artifact.is_for_project("proj-1"))

    def test_is_for_project_false(self):
        self.assertFalse(self.artifact.is_for_project("other-proj"))

    def test_is_for_project_none(self):
        a = _make_artifact(project_id=None)
        self.assertFalse(a.is_for_project("proj-1"))

    def test_none_project_id(self):
        a = _make_artifact(project_id=None)
        self.assertIsNone(a.project_id)


# ===========================================================================
# TestArtifactTemplate
# ===========================================================================

class TestArtifactTemplate(unittest.TestCase):

    def test_render_header_contains_title(self):
        result = ArtifactTemplate.render_header(
            "PRD", "My Project", "proj-1", "ArtifactEngine", 1,
            datetime.now(timezone.utc)
        )
        self.assertIn("My Project", result)

    def test_render_header_contains_type_label(self):
        result = ArtifactTemplate.render_header(
            "Product Requirements Document", "Title", "proj-1",
            "ArtifactEngine", 1, datetime.now(timezone.utc)
        )
        self.assertIn("Product Requirements Document", result)

    def test_render_header_contains_project_id(self):
        result = ArtifactTemplate.render_header(
            "PRD", "Title", "proj-abc", "ArtifactEngine", 1,
            datetime.now(timezone.utc)
        )
        self.assertIn("proj-abc", result)

    def test_render_header_no_project_id(self):
        result = ArtifactTemplate.render_header(
            "CEO Report", "Company Report", None, "ArtifactEngine", 1,
            datetime.now(timezone.utc)
        )
        self.assertIn("N/A", result)

    def test_render_header_contains_generated_by(self):
        result = ArtifactTemplate.render_header(
            "PRD", "Title", "proj-1", "TestEngine", 1,
            datetime.now(timezone.utc)
        )
        self.assertIn("TestEngine", result)

    def test_render_header_contains_version(self):
        result = ArtifactTemplate.render_header(
            "PRD", "Title", "proj-1", "ArtifactEngine", 3,
            datetime.now(timezone.utc)
        )
        self.assertIn("3", result)

    def test_render_header_contains_timestamp(self):
        ts = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = ArtifactTemplate.render_header(
            "PRD", "Title", "proj-1", "ArtifactEngine", 1, ts
        )
        self.assertIn("2026-07-01", result)

    def test_render_header_contains_divider(self):
        result = ArtifactTemplate.render_header(
            "PRD", "Title", "proj-1", "ArtifactEngine", 1,
            datetime.now(timezone.utc)
        )
        self.assertIn("---", result)

    def test_render_section_contains_heading(self):
        result = ArtifactTemplate.render_section("My Section", "Some content")
        self.assertIn("My Section", result)

    def test_render_section_contains_content(self):
        result = ArtifactTemplate.render_section("Heading", "actual content here")
        self.assertIn("actual content here", result)

    def test_render_section_default_level(self):
        result = ArtifactTemplate.render_section("Test", "content")
        self.assertIn("## Test", result)

    def test_render_section_level_3(self):
        result = ArtifactTemplate.render_section("Test", "content", level=3)
        self.assertIn("### Test", result)

    def test_render_key_value_empty(self):
        result = ArtifactTemplate.render_key_value({})
        self.assertIn("No data", result)

    def test_render_key_value_single_entry(self):
        result = ArtifactTemplate.render_key_value({"Key": "Value"})
        self.assertIn("Key", result)
        self.assertIn("Value", result)

    def test_render_key_value_multiple_entries(self):
        result = ArtifactTemplate.render_key_value({"A": 1, "B": 2})
        self.assertIn("A", result)
        self.assertIn("B", result)

    def test_render_key_value_uses_bold(self):
        result = ArtifactTemplate.render_key_value({"Key": "Val"})
        self.assertIn("**Key:**", result)

    def test_render_task_table_empty(self):
        result = ArtifactTemplate.render_task_table([])
        self.assertIn("No tasks", result)

    def test_render_task_table_has_header(self):
        from core.task import Task, TaskStatus
        tasks = [Task(
            id=str(uuid4()), title="Task A", description="Desc",
            assigned_agent="Alice", status=TaskStatus.ASSIGNED,
            priority=Priority.HIGH, dependencies=[], created_at=datetime.now(timezone.utc)
        )]
        result = ArtifactTemplate.render_task_table(tasks)
        self.assertIn("Title", result)

    def test_render_task_table_has_task_title(self):
        from core.task import Task, TaskStatus
        tasks = [Task(
            id=str(uuid4()), title="Build API", description="Desc",
            assigned_agent="Bob", status=TaskStatus.WORKING,
            priority=Priority.MEDIUM, dependencies=[], created_at=datetime.now(timezone.utc)
        )]
        result = ArtifactTemplate.render_task_table(tasks)
        self.assertIn("Build API", result)

    def test_render_task_table_has_agent_name(self):
        from core.task import Task, TaskStatus
        tasks = [Task(
            id=str(uuid4()), title="T", description="D",
            assigned_agent="Carol", status=TaskStatus.CREATED,
            priority=Priority.LOW, dependencies=[], created_at=datetime.now(timezone.utc)
        )]
        result = ArtifactTemplate.render_task_table(tasks)
        self.assertIn("Carol", result)

    def test_render_bullet_list_empty(self):
        result = ArtifactTemplate.render_bullet_list([])
        self.assertIn("None", result)

    def test_render_bullet_list_items(self):
        result = ArtifactTemplate.render_bullet_list(["alpha", "beta"])
        self.assertIn("alpha", result)
        self.assertIn("beta", result)

    def test_render_bullet_list_uses_dash(self):
        result = ArtifactTemplate.render_bullet_list(["item"])
        self.assertIn("- item", result)

    def test_render_bullet_list_custom_empty(self):
        result = ArtifactTemplate.render_bullet_list([], empty_message="Nothing here.")
        self.assertIn("Nothing here.", result)

    def test_render_numbered_list_empty(self):
        result = ArtifactTemplate.render_numbered_list([])
        self.assertIn("None", result)

    def test_render_numbered_list_items(self):
        result = ArtifactTemplate.render_numbered_list(["first", "second"])
        self.assertIn("1. first", result)
        self.assertIn("2. second", result)

    def test_render_risk_list_empty(self):
        result = ArtifactTemplate.render_risk_list([])
        self.assertIn("No risks", result)

    def test_render_risk_list_has_header(self):
        from core.risk import Risk, RiskCategory, RiskLevel
        risks = [Risk(
            category=RiskCategory.AUTHENTICATION,
            level=RiskLevel.HIGH,
            description="Auth is complex.",
        )]
        result = ArtifactTemplate.render_risk_list(risks)
        self.assertIn("Category", result)

    def test_render_risk_list_has_description(self):
        from core.risk import Risk, RiskCategory, RiskLevel
        risks = [Risk(
            category=RiskCategory.PAYMENTS,
            level=RiskLevel.CRITICAL,
            description="Payment integration risk.",
        )]
        result = ArtifactTemplate.render_risk_list(risks)
        self.assertIn("Payment integration risk.", result)

    def test_render_department_list_empty(self):
        result = ArtifactTemplate.render_department_list([])
        self.assertIn("No departments", result)

    def test_render_department_list_has_dept_name(self):
        from core.department_requirement import Department, DepartmentRequirement
        drs = [DepartmentRequirement(
            department=Department.BACKEND,
            rationale="Core logic",
            is_critical=True,
        )]
        result = ArtifactTemplate.render_department_list(drs)
        self.assertIn("Backend", result)

    def test_render_department_list_critical_badge(self):
        from core.department_requirement import Department, DepartmentRequirement
        drs = [DepartmentRequirement(
            department=Department.SECURITY,
            rationale="Security needed.",
            is_critical=True,
        )]
        result = ArtifactTemplate.render_department_list(drs)
        self.assertIn("Critical", result)

    def test_render_department_list_not_critical(self):
        from core.department_requirement import Department, DepartmentRequirement
        drs = [DepartmentRequirement(
            department=Department.MARKETING,
            rationale="Marketing helpful.",
            is_critical=False,
        )]
        result = ArtifactTemplate.render_department_list(drs)
        self.assertNotIn("**(Critical)**", result)

    def test_render_decision_list_empty(self):
        result = ArtifactTemplate.render_decision_list([])
        self.assertIn("No decisions", result)

    def test_render_memory_list_empty(self):
        result = ArtifactTemplate.render_memory_list([])
        self.assertIn("No memory", result)

    def test_render_workflow_list_empty(self):
        result = ArtifactTemplate.render_workflow_list([])
        self.assertIn("No workflows", result)

    def test_render_footer_contains_generator(self):
        result = ArtifactTemplate.render_footer("MyEngine")
        self.assertIn("MyEngine", result)

    def test_render_footer_has_ai_company_os(self):
        result = ArtifactTemplate.render_footer("X")
        self.assertIn("AI Company OS", result)

    def test_render_two_column_table_empty(self):
        result = ArtifactTemplate.render_two_column_table("A", "B", [])
        self.assertIn("No data", result)

    def test_render_two_column_table_has_headers(self):
        result = ArtifactTemplate.render_two_column_table("Left", "Right", [("a", "b")])
        self.assertIn("Left", result)
        self.assertIn("Right", result)

    def test_render_two_column_table_has_data(self):
        result = ArtifactTemplate.render_two_column_table("L", "R", [("foo", "bar")])
        self.assertIn("foo", result)
        self.assertIn("bar", result)


# ===========================================================================
# TestArtifactRegistry
# ===========================================================================

class TestArtifactRegistry(unittest.TestCase):

    def setUp(self):
        self.registry = ArtifactRegistry()

    def test_empty_count(self):
        self.assertEqual(self.registry.count(), 0)

    def test_register_single(self):
        a = _make_artifact()
        self.registry.register(a)
        self.assertEqual(self.registry.count(), 1)

    def test_register_returns_artifact(self):
        a = _make_artifact()
        result = self.registry.register(a)
        self.assertIs(result, a)

    def test_get_after_register(self):
        a = _make_artifact()
        self.registry.register(a)
        self.assertIs(self.registry.get(a.id), a)

    def test_has_true_after_register(self):
        a = _make_artifact()
        self.registry.register(a)
        self.assertTrue(self.registry.has(a.id))

    def test_has_false_for_unknown(self):
        self.assertFalse(self.registry.has("non-existent-id"))

    def test_list_all_empty(self):
        self.assertEqual(self.registry.list_all(), [])

    def test_list_all_single(self):
        a = _make_artifact()
        self.registry.register(a)
        self.assertEqual(len(self.registry.list_all()), 1)

    def test_list_all_multiple_preserves_order(self):
        arts = [_make_artifact(art_id=str(uuid4())) for _ in range(3)]
        for a in arts:
            self.registry.register(a)
        listed = self.registry.list_all()
        self.assertEqual([a.id for a in listed], [a.id for a in arts])

    def test_find_by_type_empty(self):
        self.assertEqual(self.registry.find_by_type(ArtifactType.PRD), [])

    def test_find_by_type_single_match(self):
        a = _make_artifact(artifact_type=ArtifactType.PRD)
        self.registry.register(a)
        results = self.registry.find_by_type(ArtifactType.PRD)
        self.assertEqual(len(results), 1)
        self.assertIs(results[0], a)

    def test_find_by_type_no_match(self):
        a = _make_artifact(artifact_type=ArtifactType.PRD)
        self.registry.register(a)
        self.assertEqual(self.registry.find_by_type(ArtifactType.CEO_REPORT), [])

    def test_find_by_type_multiple(self):
        for _ in range(3):
            self.registry.register(_make_artifact(artifact_type=ArtifactType.TASK_REPORT))
        self.registry.register(_make_artifact(artifact_type=ArtifactType.PRD))
        self.assertEqual(len(self.registry.find_by_type(ArtifactType.TASK_REPORT)), 3)

    def test_find_by_project_empty(self):
        self.assertEqual(self.registry.find_by_project("proj-x"), [])

    def test_find_by_project_match(self):
        a = _make_artifact(project_id="proj-abc")
        self.registry.register(a)
        results = self.registry.find_by_project("proj-abc")
        self.assertEqual(len(results), 1)

    def test_find_by_project_no_match(self):
        a = _make_artifact(project_id="proj-1")
        self.registry.register(a)
        self.assertEqual(self.registry.find_by_project("proj-2"), [])

    def test_find_by_generated_by(self):
        a = _make_artifact(generated_by="EngineA")
        b = _make_artifact(generated_by="EngineB")
        self.registry.register(a)
        self.registry.register(b)
        results = self.registry.find_by_generated_by("EngineA")
        self.assertEqual(len(results), 1)
        self.assertIs(results[0], a)

    def test_remove_decrements_count(self):
        a = _make_artifact()
        self.registry.register(a)
        self.registry.remove(a.id)
        self.assertEqual(self.registry.count(), 0)

    def test_remove_returns_artifact(self):
        a = _make_artifact()
        self.registry.register(a)
        removed = self.registry.remove(a.id)
        self.assertIs(removed, a)

    def test_has_false_after_remove(self):
        a = _make_artifact()
        self.registry.register(a)
        self.registry.remove(a.id)
        self.assertFalse(self.registry.has(a.id))

    def test_statistics_total(self):
        for _ in range(3):
            self.registry.register(_make_artifact())
        stats = self.registry.statistics()
        self.assertEqual(stats["total_artifacts"], 3)

    def test_statistics_type_counts_all_present(self):
        stats = self.registry.statistics()
        for t in ArtifactType:
            self.assertIn(t.value, stats["type_counts"])

    def test_statistics_type_counts_correct(self):
        self.registry.register(_make_artifact(artifact_type=ArtifactType.PRD))
        self.registry.register(_make_artifact(artifact_type=ArtifactType.PRD))
        self.registry.register(_make_artifact(artifact_type=ArtifactType.CEO_REPORT))
        stats = self.registry.statistics()
        self.assertEqual(stats["type_counts"]["PRD"], 2)
        self.assertEqual(stats["type_counts"]["CEO_REPORT"], 1)

    def test_statistics_unique_projects(self):
        self.registry.register(_make_artifact(project_id="p1"))
        self.registry.register(_make_artifact(project_id="p2"))
        self.registry.register(_make_artifact(project_id="p1"))
        stats = self.registry.statistics()
        self.assertEqual(stats["unique_projects"], 2)

    def test_statistics_unique_generators(self):
        self.registry.register(_make_artifact(generated_by="E1"))
        self.registry.register(_make_artifact(generated_by="E2"))
        stats = self.registry.statistics()
        self.assertEqual(stats["unique_generators"], 2)

    def test_statistics_company_wide_artifact_not_counted_in_projects(self):
        self.registry.register(_make_artifact(project_id=None))
        stats = self.registry.statistics()
        self.assertEqual(stats["unique_projects"], 0)


# ===========================================================================
# TestArtifactRegistryErrors
# ===========================================================================

class TestArtifactRegistryErrors(unittest.TestCase):

    def setUp(self):
        self.registry = ArtifactRegistry()

    def test_get_not_found_raises(self):
        with self.assertRaises(ArtifactNotFoundError):
            self.registry.get("missing-id")

    def test_remove_not_found_raises(self):
        with self.assertRaises(ArtifactNotFoundError):
            self.registry.remove("missing-id")

    def test_duplicate_register_raises(self):
        a = _make_artifact(art_id="dup-id")
        self.registry.register(a)
        with self.assertRaises(DuplicateArtifactError):
            self.registry.register(a)

    def test_duplicate_register_different_object_same_id_raises(self):
        a1 = _make_artifact(art_id="same-id")
        a2 = _make_artifact(art_id="same-id")
        self.registry.register(a1)
        with self.assertRaises(DuplicateArtifactError):
            self.registry.register(a2)

    def test_not_found_error_message(self):
        try:
            self.registry.get("ghost")
        except ArtifactNotFoundError as e:
            self.assertIn("ghost", str(e))

    def test_duplicate_error_message(self):
        a = _make_artifact(art_id="dup")
        self.registry.register(a)
        try:
            self.registry.register(a)
        except DuplicateArtifactError as e:
            self.assertIn("dup", str(e))

    def test_not_found_error_is_registry_error(self):
        from core.artifact_registry import ArtifactRegistryError
        with self.assertRaises(ArtifactRegistryError):
            self.registry.get("missing")

    def test_duplicate_error_is_registry_error(self):
        from core.artifact_registry import ArtifactRegistryError
        a = _make_artifact()
        self.registry.register(a)
        with self.assertRaises(ArtifactRegistryError):
            self.registry.register(a)


# ===========================================================================
# TestArtifactEngineInit
# ===========================================================================

class TestArtifactEngineInit(unittest.TestCase):

    def test_no_engines(self):
        engine = ArtifactEngine()
        self.assertIsNotNone(engine)

    def test_with_executive_engine(self):
        ee = ExecutiveEngine()
        engine = ArtifactEngine(executive_engine=ee)
        self.assertIsNotNone(engine)

    def test_with_planner_engine(self):
        pe = PlannerEngine()
        engine = ArtifactEngine(planner_engine=pe)
        self.assertIsNotNone(engine)

    def test_with_all_engines(self):
        me = MemoryEngine()
        de = DecisionEngine(memory_engine=me)
        ee = ExecutiveEngine()
        we = WorkflowEngine()
        pe = PlannerEngine()
        engine = ArtifactEngine(
            executive_engine=ee,
            planner_engine=pe,
            workflow_engine=we,
            memory_engine=me,
            decision_engine=de,
            company_orchestrator=None,
        )
        self.assertIsNotNone(engine)

    def test_history_empty_on_init(self):
        engine = ArtifactEngine()
        self.assertEqual(engine.history(), [])

    def test_statistics_empty_on_init(self):
        engine = ArtifactEngine()
        stats = engine.statistics()
        self.assertEqual(stats["total_artifacts"], 0)

    def test_statistics_type_counts_zero(self):
        engine = ArtifactEngine()
        stats = engine.statistics()
        for t in ArtifactType:
            self.assertEqual(stats["type_counts"][t.value], 0)


# ===========================================================================
# TestArtifactEngineGeneratePRD
# ===========================================================================

class TestArtifactEngineGeneratePRD(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine, cls.project_id = _make_engine_with_project()

    def test_returns_artifact(self):
        a = self.engine.generate_prd(self.project_id)
        self.assertIsInstance(a, Artifact)

    def test_artifact_type_is_prd(self):
        a = self.engine.generate_prd(self.project_id)
        self.assertEqual(a.type, ArtifactType.PRD)

    def test_artifact_has_project_id(self):
        a = self.engine.generate_prd(self.project_id)
        self.assertEqual(a.project_id, self.project_id)

    def test_artifact_has_generated_by(self):
        a = self.engine.generate_prd(self.project_id)
        self.assertEqual(a.generated_by, "ArtifactEngine")

    def test_artifact_has_content(self):
        a = self.engine.generate_prd(self.project_id)
        self.assertIsInstance(a.content, str)
        self.assertGreater(len(a.content), 0)

    def test_content_contains_project_title(self):
        a = self.engine.generate_prd(self.project_id)
        self.assertIn("Test Project", a.content)

    def test_content_contains_prd_label(self):
        a = self.engine.generate_prd(self.project_id)
        self.assertIn("Product Requirements Document", a.content)

    def test_content_contains_executive_summary(self):
        a = self.engine.generate_prd(self.project_id)
        self.assertIn("Executive Summary", a.content)

    def test_content_contains_functional_requirements(self):
        a = self.engine.generate_prd(self.project_id)
        self.assertIn("Functional Requirements", a.content)

    def test_content_contains_success_criteria(self):
        a = self.engine.generate_prd(self.project_id)
        self.assertIn("Success Criteria", a.content)

    def test_version_starts_at_1(self):
        eng, pid = _make_engine_with_project()
        a = eng.generate_prd(pid)
        self.assertEqual(a.version, 1)

    def test_version_increments(self):
        eng, pid = _make_engine_with_project()
        a1 = eng.generate_prd(pid)
        a2 = eng.generate_prd(pid)
        self.assertEqual(a1.version, 1)
        self.assertEqual(a2.version, 2)

    def test_stored_in_history(self):
        eng, pid = _make_engine_with_project()
        a = eng.generate_prd(pid)
        self.assertIn(a, eng.history())

    def test_prd_without_engines(self):
        engine = ArtifactEngine()
        a = engine.generate_prd("any-project-id")
        self.assertIsInstance(a, Artifact)
        self.assertEqual(a.type, ArtifactType.PRD)

    def test_prd_without_engines_has_content(self):
        engine = ArtifactEngine()
        a = engine.generate_prd("proj-123")
        self.assertGreater(len(a.content), 100)

    def test_blank_project_id_raises(self):
        engine = ArtifactEngine()
        with self.assertRaises(InvalidArtifactRequestError):
            engine.generate_prd("")

    def test_whitespace_project_id_raises(self):
        engine = ArtifactEngine()
        with self.assertRaises(InvalidArtifactRequestError):
            engine.generate_prd("   ")

    def test_invalid_raises_artifact_engine_error(self):
        engine = ArtifactEngine()
        with self.assertRaises(ArtifactEngineError):
            engine.generate_prd("")

    def test_different_project_ids_different_artifacts(self):
        eng, _ = _make_engine_with_project()
        a1 = eng.generate_prd("proj-aaa")
        a2 = eng.generate_prd("proj-bbb")
        self.assertNotEqual(a1.id, a2.id)

    def test_artifact_has_unique_id(self):
        eng, pid = _make_engine_with_project()
        a1 = eng.generate_prd(pid)
        a2 = eng.generate_prd(pid)
        self.assertNotEqual(a1.id, a2.id)

    def test_artifact_created_at_is_utc(self):
        eng, pid = _make_engine_with_project()
        a = eng.generate_prd(pid)
        self.assertIsNotNone(a.created_at.tzinfo)

    def test_content_contains_footer(self):
        eng, pid = _make_engine_with_project()
        a = eng.generate_prd(pid)
        self.assertIn("Generated by", a.content)


# ===========================================================================
# TestArtifactEngineGenerateTechSpec
# ===========================================================================

class TestArtifactEngineGenerateTechSpec(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine, cls.project_id = _make_engine_with_project()

    def test_returns_artifact(self):
        a = self.engine.generate_technical_specification(self.project_id)
        self.assertIsInstance(a, Artifact)

    def test_artifact_type(self):
        a = self.engine.generate_technical_specification(self.project_id)
        self.assertEqual(a.type, ArtifactType.TECHNICAL_SPECIFICATION)

    def test_content_non_empty(self):
        a = self.engine.generate_technical_specification(self.project_id)
        self.assertGreater(len(a.content), 100)

    def test_content_has_architecture(self):
        a = self.engine.generate_technical_specification(self.project_id)
        self.assertIn("Architecture", a.content)

    def test_content_has_tech_spec_label(self):
        a = self.engine.generate_technical_specification(self.project_id)
        self.assertIn("Technical Specification", a.content)

    def test_content_has_module_breakdown(self):
        a = self.engine.generate_technical_specification(self.project_id)
        self.assertIn("Module", a.content)

    def test_version_is_1_on_first_call(self):
        eng, pid = _make_engine_with_project()
        a = eng.generate_technical_specification(pid)
        self.assertEqual(a.version, 1)

    def test_version_increments(self):
        eng, pid = _make_engine_with_project()
        a1 = eng.generate_technical_specification(pid)
        a2 = eng.generate_technical_specification(pid)
        self.assertEqual(a2.version, 2)

    def test_blank_project_id_raises(self):
        engine = ArtifactEngine()
        with self.assertRaises(InvalidArtifactRequestError):
            engine.generate_technical_specification("")

    def test_no_engines_still_works(self):
        engine = ArtifactEngine()
        a = engine.generate_technical_specification("proj-x")
        self.assertIsInstance(a, Artifact)

    def test_stored_in_history(self):
        eng, pid = _make_engine_with_project()
        a = eng.generate_technical_specification(pid)
        self.assertIn(a, eng.history())

    def test_testing_strategy_section(self):
        a = self.engine.generate_technical_specification(self.project_id)
        self.assertIn("Testing", a.content)

    def test_complexity_section(self):
        a = self.engine.generate_technical_specification(self.project_id)
        self.assertIn("Complexity", a.content)


# ===========================================================================
# TestArtifactEngineGenerateAPISpec
# ===========================================================================

class TestArtifactEngineGenerateAPISpec(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine, cls.project_id = _make_engine_with_project()

    def test_returns_artifact(self):
        a = self.engine.generate_api_specification(self.project_id)
        self.assertIsInstance(a, Artifact)

    def test_artifact_type(self):
        a = self.engine.generate_api_specification(self.project_id)
        self.assertEqual(a.type, ArtifactType.API_SPECIFICATION)

    def test_content_has_api_spec_label(self):
        a = self.engine.generate_api_specification(self.project_id)
        self.assertIn("API Specification", a.content)

    def test_content_has_endpoint_catalog(self):
        a = self.engine.generate_api_specification(self.project_id)
        self.assertIn("Endpoint", a.content)

    def test_content_has_error_codes(self):
        a = self.engine.generate_api_specification(self.project_id)
        self.assertIn("Error", a.content)

    def test_content_has_base_url(self):
        a = self.engine.generate_api_specification(self.project_id)
        self.assertIn("/api/v1", a.content)

    def test_blank_project_id_raises(self):
        engine = ArtifactEngine()
        with self.assertRaises(InvalidArtifactRequestError):
            engine.generate_api_specification("")

    def test_no_engines_works(self):
        engine = ArtifactEngine()
        a = engine.generate_api_specification("proj-x")
        self.assertIsInstance(a, Artifact)

    def test_response_format_section(self):
        a = self.engine.generate_api_specification(self.project_id)
        self.assertIn("Response", a.content)

    def test_request_format_section(self):
        a = self.engine.generate_api_specification(self.project_id)
        self.assertIn("Request", a.content)

    def test_version_increments(self):
        eng, pid = _make_engine_with_project()
        a1 = eng.generate_api_specification(pid)
        a2 = eng.generate_api_specification(pid)
        self.assertEqual(a1.version, 1)
        self.assertEqual(a2.version, 2)

    def test_stored_in_history(self):
        eng, pid = _make_engine_with_project()
        a = eng.generate_api_specification(pid)
        self.assertIn(a, eng.history())


# ===========================================================================
# TestArtifactEngineGenerateDatabaseSchema
# ===========================================================================

class TestArtifactEngineGenerateDatabaseSchema(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine, cls.project_id = _make_engine_with_project()

    def test_returns_artifact(self):
        a = self.engine.generate_database_schema(self.project_id)
        self.assertIsInstance(a, Artifact)

    def test_artifact_type(self):
        a = self.engine.generate_database_schema(self.project_id)
        self.assertEqual(a.type, ArtifactType.DATABASE_SCHEMA)

    def test_content_has_label(self):
        a = self.engine.generate_database_schema(self.project_id)
        self.assertIn("Database Schema", a.content)

    def test_content_has_table_definition(self):
        a = self.engine.generate_database_schema(self.project_id)
        self.assertIn("Table", a.content)

    def test_content_has_indexing_strategy(self):
        a = self.engine.generate_database_schema(self.project_id)
        self.assertIn("Index", a.content)

    def test_content_has_migration_strategy(self):
        a = self.engine.generate_database_schema(self.project_id)
        self.assertIn("Migration", a.content)

    def test_blank_project_id_raises(self):
        engine = ArtifactEngine()
        with self.assertRaises(InvalidArtifactRequestError):
            engine.generate_database_schema("")

    def test_no_tasks_gives_placeholder(self):
        ee = ExecutiveEngine()
        proj = ee.create_project("Empty", "Desc", "Obj", Priority.LOW)
        engine = ArtifactEngine(executive_engine=ee)
        a = engine.generate_database_schema(proj.id)
        self.assertIn("No tasks", a.content)

    def test_version_starts_at_1(self):
        eng, pid = _make_engine_with_project()
        a = eng.generate_database_schema(pid)
        self.assertEqual(a.version, 1)

    def test_stored_in_history(self):
        eng, pid = _make_engine_with_project()
        a = eng.generate_database_schema(pid)
        self.assertIn(a, eng.history())

    def test_postgresql_mentioned(self):
        a = self.engine.generate_database_schema(self.project_id)
        self.assertIn("PostgreSQL", a.content)


# ===========================================================================
# TestArtifactEngineGenerateProjectStructure
# ===========================================================================

class TestArtifactEngineGenerateProjectStructure(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine, cls.project_id = _make_engine_with_project()

    def test_returns_artifact(self):
        a = self.engine.generate_project_structure(self.project_id)
        self.assertIsInstance(a, Artifact)

    def test_artifact_type(self):
        a = self.engine.generate_project_structure(self.project_id)
        self.assertEqual(a.type, ArtifactType.PROJECT_STRUCTURE)

    def test_content_has_label(self):
        a = self.engine.generate_project_structure(self.project_id)
        self.assertIn("Project Structure", a.content)

    def test_content_has_directory_layout(self):
        a = self.engine.generate_project_structure(self.project_id)
        self.assertIn("Directory", a.content)

    def test_content_has_naming_conventions(self):
        a = self.engine.generate_project_structure(self.project_id)
        self.assertIn("Naming", a.content)

    def test_content_has_tests_dir(self):
        a = self.engine.generate_project_structure(self.project_id)
        self.assertIn("tests", a.content)

    def test_blank_project_id_raises(self):
        engine = ArtifactEngine()
        with self.assertRaises(InvalidArtifactRequestError):
            engine.generate_project_structure("")

    def test_version_starts_at_1(self):
        eng, pid = _make_engine_with_project()
        a = eng.generate_project_structure(pid)
        self.assertEqual(a.version, 1)

    def test_stored_in_history(self):
        eng, pid = _make_engine_with_project()
        a = eng.generate_project_structure(pid)
        self.assertIn(a, eng.history())


# ===========================================================================
# TestArtifactEngineGenerateTaskReport
# ===========================================================================

class TestArtifactEngineGenerateTaskReport(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine, cls.project_id = _make_engine_with_project()

    def test_returns_artifact(self):
        a = self.engine.generate_task_report(self.project_id)
        self.assertIsInstance(a, Artifact)

    def test_artifact_type(self):
        a = self.engine.generate_task_report(self.project_id)
        self.assertEqual(a.type, ArtifactType.TASK_REPORT)

    def test_content_has_label(self):
        a = self.engine.generate_task_report(self.project_id)
        self.assertIn("Task Report", a.content)

    def test_content_has_summary(self):
        a = self.engine.generate_task_report(self.project_id)
        self.assertIn("Summary", a.content)

    def test_content_has_total_tasks(self):
        a = self.engine.generate_task_report(self.project_id)
        self.assertIn("Total Tasks", a.content)

    def test_content_has_task_details(self):
        a = self.engine.generate_task_report(self.project_id)
        self.assertIn("Task Details", a.content)

    def test_content_has_blocked_section(self):
        a = self.engine.generate_task_report(self.project_id)
        self.assertIn("Blocked", a.content)

    def test_blank_project_id_raises(self):
        engine = ArtifactEngine()
        with self.assertRaises(InvalidArtifactRequestError):
            engine.generate_task_report("")

    def test_no_engines_still_works(self):
        engine = ArtifactEngine()
        a = engine.generate_task_report("proj-x")
        self.assertIsInstance(a, Artifact)

    def test_completion_percentage_in_content(self):
        a = self.engine.generate_task_report(self.project_id)
        self.assertIn("Completion", a.content)

    def test_version_starts_at_1(self):
        eng, pid = _make_engine_with_project()
        a = eng.generate_task_report(pid)
        self.assertEqual(a.version, 1)

    def test_version_increments(self):
        eng, pid = _make_engine_with_project()
        a1 = eng.generate_task_report(pid)
        a2 = eng.generate_task_report(pid)
        self.assertEqual(a2.version, 2)

    def test_stored_in_history(self):
        eng, pid = _make_engine_with_project()
        a = eng.generate_task_report(pid)
        self.assertIn(a, eng.history())

    def test_empty_project_has_no_tasks_message(self):
        ee = ExecutiveEngine()
        proj = ee.create_project("Empty", "D", "O", Priority.LOW)
        engine = ArtifactEngine(executive_engine=ee)
        a = engine.generate_task_report(proj.id)
        self.assertIn("0", a.content)

    def test_project_id_set_correctly(self):
        eng, pid = _make_engine_with_project()
        a = eng.generate_task_report(pid)
        self.assertEqual(a.project_id, pid)


# ===========================================================================
# TestArtifactEngineGenerateCEOReport
# ===========================================================================

class TestArtifactEngineGenerateCEOReport(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine, cls.project_id = _make_full_engine()

    def test_returns_artifact(self):
        a = self.engine.generate_ceo_report()
        self.assertIsInstance(a, Artifact)

    def test_artifact_type(self):
        a = self.engine.generate_ceo_report()
        self.assertEqual(a.type, ArtifactType.CEO_REPORT)

    def test_project_id_is_none(self):
        a = self.engine.generate_ceo_report()
        self.assertIsNone(a.project_id)

    def test_content_has_label(self):
        a = self.engine.generate_ceo_report()
        self.assertIn("CEO Report", a.content)

    def test_content_has_executive_summary(self):
        a = self.engine.generate_ceo_report()
        self.assertIn("Executive Summary", a.content)

    def test_content_has_projects(self):
        a = self.engine.generate_ceo_report()
        self.assertIn("Projects", a.content)

    def test_content_has_workflow_status(self):
        a = self.engine.generate_ceo_report()
        self.assertIn("Workflow", a.content)

    def test_content_has_decisions(self):
        a = self.engine.generate_ceo_report()
        self.assertIn("Decision", a.content)

    def test_content_has_memory(self):
        a = self.engine.generate_ceo_report()
        self.assertIn("Memory", a.content)

    def test_content_has_recommendations(self):
        a = self.engine.generate_ceo_report()
        self.assertIn("Recommendation", a.content)

    def test_custom_company_name(self):
        a = self.engine.generate_ceo_report(company_name="ACME Corp")
        self.assertIn("ACME Corp", a.content)

    def test_default_company_name(self):
        a = self.engine.generate_ceo_report()
        self.assertIn("AI Company OS", a.content)

    def test_no_engines_works(self):
        engine = ArtifactEngine()
        a = engine.generate_ceo_report()
        self.assertIsInstance(a, Artifact)

    def test_version_starts_at_1(self):
        engine = ArtifactEngine()
        a = engine.generate_ceo_report()
        self.assertEqual(a.version, 1)

    def test_version_increments(self):
        engine = ArtifactEngine()
        a1 = engine.generate_ceo_report()
        a2 = engine.generate_ceo_report()
        self.assertEqual(a1.version, 1)
        self.assertEqual(a2.version, 2)

    def test_stored_in_history(self):
        engine = ArtifactEngine()
        a = engine.generate_ceo_report()
        self.assertIn(a, engine.history())

    def test_blank_company_name_uses_default(self):
        engine = ArtifactEngine()
        a = engine.generate_ceo_report(company_name="")
        self.assertIn("AI Company OS", a.content)

    def test_content_has_project_count(self):
        a = self.engine.generate_ceo_report()
        self.assertIn("Total Projects", a.content)

    def test_generated_by_artifact_engine(self):
        a = self.engine.generate_ceo_report()
        self.assertEqual(a.generated_by, "ArtifactEngine")


# ===========================================================================
# TestArtifactEngineGenerateSprintReport
# ===========================================================================

class TestArtifactEngineGenerateSprintReport(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine, cls.project_id = _make_engine_with_project()

    def test_returns_artifact(self):
        a = self.engine.generate_sprint_report(self.project_id)
        self.assertIsInstance(a, Artifact)

    def test_artifact_type(self):
        a = self.engine.generate_sprint_report(self.project_id)
        self.assertEqual(a.type, ArtifactType.SPRINT_REPORT)

    def test_content_has_sprint_label(self):
        a = self.engine.generate_sprint_report(self.project_id)
        self.assertIn("Sprint Report", a.content)

    def test_content_has_sprint_summary(self):
        a = self.engine.generate_sprint_report(self.project_id)
        self.assertIn("Summary", a.content)

    def test_content_has_task_status(self):
        a = self.engine.generate_sprint_report(self.project_id)
        self.assertIn("Task Status", a.content)

    def test_content_has_next_sprint_goals(self):
        a = self.engine.generate_sprint_report(self.project_id)
        self.assertIn("Next Sprint", a.content)

    def test_sprint_number_default_1(self):
        a = self.engine.generate_sprint_report(self.project_id)
        self.assertIn("Sprint 1", a.content)

    def test_sprint_number_custom(self):
        a = self.engine.generate_sprint_report(self.project_id, sprint_number=5)
        self.assertIn("Sprint 5", a.content)

    def test_invalid_sprint_number_raises(self):
        engine = ArtifactEngine()
        with self.assertRaises(InvalidArtifactRequestError):
            engine.generate_sprint_report("proj-x", sprint_number=0)

    def test_negative_sprint_raises(self):
        engine = ArtifactEngine()
        with self.assertRaises(InvalidArtifactRequestError):
            engine.generate_sprint_report("proj-x", sprint_number=-1)

    def test_blank_project_id_raises(self):
        engine = ArtifactEngine()
        with self.assertRaises(InvalidArtifactRequestError):
            engine.generate_sprint_report("")

    def test_version_starts_at_1(self):
        eng, pid = _make_engine_with_project()
        a = eng.generate_sprint_report(pid)
        self.assertEqual(a.version, 1)

    def test_version_increments(self):
        eng, pid = _make_engine_with_project()
        a1 = eng.generate_sprint_report(pid)
        a2 = eng.generate_sprint_report(pid)
        self.assertEqual(a2.version, 2)

    def test_stored_in_history(self):
        eng, pid = _make_engine_with_project()
        a = eng.generate_sprint_report(pid)
        self.assertIn(a, eng.history())

    def test_project_id_set_correctly(self):
        eng, pid = _make_engine_with_project()
        a = eng.generate_sprint_report(pid)
        self.assertEqual(a.project_id, pid)

    def test_no_engines_still_works(self):
        engine = ArtifactEngine()
        a = engine.generate_sprint_report("proj-x")
        self.assertIsInstance(a, Artifact)

    def test_velocity_in_content(self):
        a = self.engine.generate_sprint_report(self.project_id)
        self.assertIn("Velocity", a.content)

    def test_completion_in_content(self):
        a = self.engine.generate_sprint_report(self.project_id)
        self.assertIn("Completion", a.content)


# ===========================================================================
# TestArtifactEngineHistory
# ===========================================================================

class TestArtifactEngineHistory(unittest.TestCase):

    def test_empty_history(self):
        engine = ArtifactEngine()
        self.assertEqual(engine.history(), [])

    def test_history_after_prd(self):
        engine = ArtifactEngine()
        a = engine.generate_prd("proj-1")
        self.assertIn(a, engine.history())

    def test_history_length_after_multiple_generates(self):
        engine = ArtifactEngine()
        engine.generate_prd("p1")
        engine.generate_task_report("p1")
        engine.generate_ceo_report()
        self.assertEqual(len(engine.history()), 3)

    def test_history_preserves_order(self):
        engine = ArtifactEngine()
        a1 = engine.generate_prd("p1")
        a2 = engine.generate_task_report("p1")
        h = engine.history()
        self.assertEqual(h[0].id, a1.id)
        self.assertEqual(h[1].id, a2.id)

    def test_history_returns_list(self):
        engine = ArtifactEngine()
        self.assertIsInstance(engine.history(), list)

    def test_history_all_are_artifacts(self):
        engine = ArtifactEngine()
        engine.generate_prd("p1")
        engine.generate_ceo_report()
        for a in engine.history():
            self.assertIsInstance(a, Artifact)

    def test_history_different_types(self):
        engine = ArtifactEngine()
        engine.generate_prd("p1")
        engine.generate_ceo_report()
        engine.generate_sprint_report("p1")
        types = {a.type for a in engine.history()}
        self.assertIn(ArtifactType.PRD, types)
        self.assertIn(ArtifactType.CEO_REPORT, types)
        self.assertIn(ArtifactType.SPRINT_REPORT, types)

    def test_history_is_copy(self):
        engine = ArtifactEngine()
        engine.generate_prd("p1")
        h1 = engine.history()
        h2 = engine.history()
        self.assertIsNot(h1, h2)


# ===========================================================================
# TestArtifactEngineStatistics
# ===========================================================================

class TestArtifactEngineStatistics(unittest.TestCase):

    def test_initial_statistics(self):
        engine = ArtifactEngine()
        stats = engine.statistics()
        self.assertEqual(stats["total_artifacts"], 0)

    def test_statistics_after_prd(self):
        engine = ArtifactEngine()
        engine.generate_prd("p1")
        stats = engine.statistics()
        self.assertEqual(stats["total_artifacts"], 1)
        self.assertEqual(stats["type_counts"]["PRD"], 1)

    def test_statistics_type_counts_all_present(self):
        engine = ArtifactEngine()
        stats = engine.statistics()
        for t in ArtifactType:
            self.assertIn(t.value, stats["type_counts"])

    def test_statistics_unique_projects_after_prd(self):
        engine = ArtifactEngine()
        engine.generate_prd("proj-a")
        engine.generate_prd("proj-b")
        stats = engine.statistics()
        self.assertEqual(stats["unique_projects"], 2)

    def test_statistics_ceo_report_not_counted_in_projects(self):
        engine = ArtifactEngine()
        engine.generate_ceo_report()
        stats = engine.statistics()
        self.assertEqual(stats["unique_projects"], 0)

    def test_statistics_has_version_counters(self):
        engine = ArtifactEngine()
        stats = engine.statistics()
        self.assertIn("version_counters", stats)

    def test_statistics_multiple_types(self):
        engine = ArtifactEngine()
        engine.generate_prd("p1")
        engine.generate_task_report("p1")
        engine.generate_ceo_report()
        stats = engine.statistics()
        self.assertEqual(stats["total_artifacts"], 3)
        self.assertEqual(stats["type_counts"]["PRD"], 1)
        self.assertEqual(stats["type_counts"]["TASK_REPORT"], 1)
        self.assertEqual(stats["type_counts"]["CEO_REPORT"], 1)

    def test_statistics_unique_generators(self):
        engine = ArtifactEngine()
        engine.generate_prd("p1")
        stats = engine.statistics()
        self.assertEqual(stats["unique_generators"], 1)


# ===========================================================================
# TestArtifactEngineFindArtifact
# ===========================================================================

class TestArtifactEngineFindArtifact(unittest.TestCase):

    def test_find_after_generate(self):
        engine = ArtifactEngine()
        a = engine.generate_prd("p1")
        found = engine.find_artifact(a.id)
        self.assertIs(found, a)

    def test_find_ceo_report(self):
        engine = ArtifactEngine()
        a = engine.generate_ceo_report()
        found = engine.find_artifact(a.id)
        self.assertIs(found, a)

    def test_not_found_raises(self):
        engine = ArtifactEngine()
        with self.assertRaises(EngineArtifactNotFoundError):
            engine.find_artifact("non-existent-id")

    def test_find_by_different_ids(self):
        engine = ArtifactEngine()
        a1 = engine.generate_prd("p1")
        a2 = engine.generate_task_report("p1")
        self.assertIs(engine.find_artifact(a1.id), a1)
        self.assertIs(engine.find_artifact(a2.id), a2)

    def test_not_found_is_engine_error(self):
        engine = ArtifactEngine()
        with self.assertRaises(ArtifactEngineError):
            engine.find_artifact("missing")


# ===========================================================================
# TestArtifactEngineVersioning
# ===========================================================================

class TestArtifactEngineVersioning(unittest.TestCase):

    def test_version_1_on_first_prd(self):
        engine = ArtifactEngine()
        a = engine.generate_prd("p1")
        self.assertEqual(a.version, 1)

    def test_version_2_on_second_prd_same_project(self):
        engine = ArtifactEngine()
        engine.generate_prd("p1")
        a2 = engine.generate_prd("p1")
        self.assertEqual(a2.version, 2)

    def test_version_reset_for_different_project(self):
        engine = ArtifactEngine()
        engine.generate_prd("p1")
        a2 = engine.generate_prd("p2")
        self.assertEqual(a2.version, 1)

    def test_version_independent_per_type(self):
        engine = ArtifactEngine()
        engine.generate_prd("p1")
        a_tr = engine.generate_task_report("p1")
        self.assertEqual(a_tr.version, 1)

    def test_version_independent_prd_vs_tech_spec(self):
        engine = ArtifactEngine()
        engine.generate_prd("p1")
        engine.generate_prd("p1")
        a_ts = engine.generate_technical_specification("p1")
        self.assertEqual(a_ts.version, 1)

    def test_ceo_report_version_increments(self):
        engine = ArtifactEngine()
        a1 = engine.generate_ceo_report()
        a2 = engine.generate_ceo_report()
        a3 = engine.generate_ceo_report()
        self.assertEqual(a1.version, 1)
        self.assertEqual(a2.version, 2)
        self.assertEqual(a3.version, 3)


# ===========================================================================
# TestArtifactEngineWithRealEngines
# ===========================================================================

class TestArtifactEngineWithRealEngines(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine, cls.project_id = _make_full_engine()
        # Pre-generate several artifacts for query tests
        cls.prd = cls.engine.generate_prd(cls.project_id)
        cls.tech_spec = cls.engine.generate_technical_specification(cls.project_id)
        cls.api_spec = cls.engine.generate_api_specification(cls.project_id)
        cls.task_report = cls.engine.generate_task_report(cls.project_id)
        cls.sprint_report = cls.engine.generate_sprint_report(cls.project_id)
        cls.ceo_report = cls.engine.generate_ceo_report()

    def test_prd_contains_project_title(self):
        self.assertIn("Full Engine Project", self.prd.content)

    def test_prd_contains_objective(self):
        self.assertIn("e-commerce", self.prd.content.lower())

    def test_tech_spec_contains_title(self):
        self.assertIn("Full Engine Project", self.tech_spec.content)

    def test_api_spec_has_endpoint_from_tasks(self):
        # Task "Auth Module" -> endpoint /api/v1/auth-module
        self.assertIn("auth-module", self.api_spec.content.lower())

    def test_task_report_has_task_names(self):
        self.assertIn("Auth Module", self.task_report.content)

    def test_task_report_has_payment_gateway(self):
        self.assertIn("Payment Gateway", self.task_report.content)

    def test_sprint_report_has_project_tasks(self):
        self.assertIn("Auth Module", self.sprint_report.content)

    def test_ceo_report_has_project_name(self):
        self.assertIn("Full Engine Project", self.ceo_report.content)

    def test_ceo_report_has_workflow(self):
        self.assertIn("Test Workflow", self.ceo_report.content)

    def test_ceo_report_has_decision(self):
        self.assertIn("Choose framework", self.ceo_report.content)

    def test_ceo_report_has_memory_entry(self):
        self.assertIn("Test memory entry", self.ceo_report.content)

    def test_history_has_all_artifacts(self):
        h = self.engine.history()
        ids = {a.id for a in h}
        self.assertIn(self.prd.id, ids)
        self.assertIn(self.tech_spec.id, ids)
        self.assertIn(self.api_spec.id, ids)
        self.assertIn(self.ceo_report.id, ids)

    def test_find_prd_by_id(self):
        found = self.engine.find_artifact(self.prd.id)
        self.assertIs(found, self.prd)

    def test_statistics_counts_all_types(self):
        stats = self.engine.statistics()
        self.assertGreaterEqual(stats["total_artifacts"], 6)

    def test_prd_with_real_planner(self):
        ee = ExecutiveEngine()
        proj = ee.create_project(
            title="Auth Platform",
            description="Build an authentication platform.",
            objective="Build a secure authentication system with JWT, OAuth2, and MFA.",
            priority=Priority.HIGH,
        )
        pe = PlannerEngine()
        engine = ArtifactEngine(executive_engine=ee, planner_engine=pe)
        a = engine.generate_prd(proj.id)
        self.assertIn("Auth Platform", a.content)
        self.assertIn("Product Requirements Document", a.content)

    def test_prd_with_planner_has_risks_section(self):
        ee = ExecutiveEngine()
        proj = ee.create_project(
            title="Payment API",
            description="Process payments.",
            objective="Build a payment processing API with Stripe integration and fraud detection.",
            priority=Priority.CRITICAL,
        )
        pe = PlannerEngine()
        engine = ArtifactEngine(executive_engine=ee, planner_engine=pe)
        a = engine.generate_prd(proj.id)
        # Payment project should trigger risk detection
        self.assertIn("Risk", a.content)

    def test_tech_spec_with_real_planner(self):
        ee = ExecutiveEngine()
        proj = ee.create_project(
            title="Data Pipeline",
            description="ETL data pipeline.",
            objective="Build a real-time data pipeline for analytics processing.",
            priority=Priority.HIGH,
        )
        pe = PlannerEngine()
        engine = ArtifactEngine(executive_engine=ee, planner_engine=pe)
        a = engine.generate_technical_specification(proj.id)
        self.assertIn("Technical Specification", a.content)

    def test_database_schema_with_tasks(self):
        eng, pid = _make_engine_with_project()
        a = eng.generate_database_schema(pid)
        self.assertIn("design_module", a.content.lower())

    def test_project_structure_with_planner(self):
        ee = ExecutiveEngine()
        proj = ee.create_project(
            title="E-Commerce Store",
            description="Online store.",
            objective="Build an e-commerce platform with product catalog, cart, and checkout.",
            priority=Priority.HIGH,
        )
        pe = PlannerEngine()
        engine = ArtifactEngine(executive_engine=ee, planner_engine=pe)
        a = engine.generate_project_structure(proj.id)
        self.assertIn("Project Structure", a.content)

    def test_sprint_report_sprint_2(self):
        eng, pid = _make_engine_with_project()
        a = eng.generate_sprint_report(pid, sprint_number=2)
        self.assertIn("Sprint 2", a.content)
        self.assertIn("Sprint 3", a.content)  # next sprint goal

    def test_all_artifact_types_can_be_generated(self):
        eng, pid = _make_engine_with_project()
        methods = [
            lambda: eng.generate_prd(pid),
            lambda: eng.generate_technical_specification(pid),
            lambda: eng.generate_api_specification(pid),
            lambda: eng.generate_database_schema(pid),
            lambda: eng.generate_project_structure(pid),
            lambda: eng.generate_task_report(pid),
            lambda: eng.generate_sprint_report(pid),
            lambda: eng.generate_ceo_report(),
        ]
        for method in methods:
            a = method()
            self.assertIsInstance(a, Artifact)
            self.assertGreater(len(a.content), 50)

    def test_no_same_ids_across_all_artifacts(self):
        eng, pid = _make_engine_with_project()
        artifacts = [
            eng.generate_prd(pid),
            eng.generate_technical_specification(pid),
            eng.generate_api_specification(pid),
            eng.generate_database_schema(pid),
            eng.generate_project_structure(pid),
            eng.generate_task_report(pid),
            eng.generate_sprint_report(pid),
            eng.generate_ceo_report(),
        ]
        ids = [a.id for a in artifacts]
        self.assertEqual(len(ids), len(set(ids)))


# ===========================================================================
# TestArtifactEngineEdgeCases
# ===========================================================================

class TestArtifactEngineEdgeCases(unittest.TestCase):

    def test_generate_all_types_multiple_times(self):
        engine = ArtifactEngine()
        for _ in range(3):
            engine.generate_prd("p1")
        self.assertEqual(len(engine.history()), 3)

    def test_ceo_report_no_projects(self):
        engine = ArtifactEngine()
        a = engine.generate_ceo_report()
        self.assertIn("No projects", a.content)

    def test_ceo_report_with_only_memory(self):
        me = MemoryEngine()
        me.store(MemoryEntry(
            id=str(uuid4()),
            title="A memory",
            category=MemoryCategory.DECISION,
            scope=MemoryScope.GLOBAL,
            author="Test",
            content="Content",
            tags=set(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ))
        engine = ArtifactEngine(memory_engine=me)
        a = engine.generate_ceo_report()
        self.assertIn("A memory", a.content)

    def test_generate_prd_for_nonexistent_project_no_crash(self):
        engine = ArtifactEngine(executive_engine=ExecutiveEngine())
        a = engine.generate_prd("non-existent-proj-id")
        self.assertIsInstance(a, Artifact)

    def test_long_project_id_handled(self):
        engine = ArtifactEngine()
        long_id = "a" * 100
        a = engine.generate_prd(long_id)
        self.assertIsInstance(a, Artifact)

    def test_content_is_string(self):
        engine = ArtifactEngine()
        a = engine.generate_prd("p1")
        self.assertIsInstance(a.content, str)

    def test_all_artifacts_have_non_empty_content(self):
        engine = ArtifactEngine()
        pid = "test-project"
        for a in [
            engine.generate_prd(pid),
            engine.generate_technical_specification(pid),
            engine.generate_api_specification(pid),
            engine.generate_database_schema(pid),
            engine.generate_project_structure(pid),
            engine.generate_task_report(pid),
            engine.generate_sprint_report(pid),
            engine.generate_ceo_report(),
        ]:
            self.assertGreater(len(a.content.strip()), 0)

    def test_sprint_1_generates_sprint_2_goal(self):
        engine = ArtifactEngine()
        a = engine.generate_sprint_report("p1", sprint_number=1)
        self.assertIn("Sprint 2", a.content)

    def test_sprint_10_generates_sprint_11_goal(self):
        engine = ArtifactEngine()
        a = engine.generate_sprint_report("p1", sprint_number=10)
        self.assertIn("Sprint 11", a.content)

    def test_word_count_is_positive_for_all_types(self):
        engine = ArtifactEngine()
        pid = "p1"
        for a in [
            engine.generate_prd(pid),
            engine.generate_technical_specification(pid),
            engine.generate_api_specification(pid),
            engine.generate_database_schema(pid),
            engine.generate_project_structure(pid),
            engine.generate_task_report(pid),
            engine.generate_sprint_report(pid),
            engine.generate_ceo_report(),
        ]:
            self.assertGreater(a.word_count(), 0)


# ===========================================================================
# TestArtifactBlueprintIntegration
# ===========================================================================

class TestArtifactBlueprintIntegration(unittest.TestCase):
    """Tests that pass an explicit blueprint to generate methods."""

    def _get_blueprint(self):
        pe = PlannerEngine()
        return pe.analyze("Build a mobile app with authentication and payments.")

    def test_prd_with_explicit_blueprint(self):
        bp = self._get_blueprint()
        engine = ArtifactEngine()
        a = engine.generate_prd("proj-x", blueprint=bp)
        self.assertIsInstance(a, Artifact)
        self.assertEqual(a.type, ArtifactType.PRD)

    def test_prd_explicit_blueprint_has_recommendations(self):
        bp = self._get_blueprint()
        engine = ArtifactEngine()
        a = engine.generate_prd("proj-x", blueprint=bp)
        self.assertIn("Goals", a.content)

    def test_tech_spec_with_explicit_blueprint(self):
        bp = self._get_blueprint()
        engine = ArtifactEngine()
        a = engine.generate_technical_specification("proj-x", blueprint=bp)
        self.assertIsInstance(a, Artifact)

    def test_api_spec_with_explicit_blueprint(self):
        bp = self._get_blueprint()
        engine = ArtifactEngine()
        a = engine.generate_api_specification("proj-x", blueprint=bp)
        self.assertIsInstance(a, Artifact)

    def test_database_schema_with_explicit_blueprint(self):
        bp = self._get_blueprint()
        engine = ArtifactEngine()
        a = engine.generate_database_schema("proj-x", blueprint=bp)
        self.assertIsInstance(a, Artifact)

    def test_project_structure_with_explicit_blueprint(self):
        bp = self._get_blueprint()
        engine = ArtifactEngine()
        a = engine.generate_project_structure("proj-x", blueprint=bp)
        self.assertIsInstance(a, Artifact)

    def test_blueprint_risks_in_prd_content(self):
        bp = self._get_blueprint()
        # Mobile app with auth+payments should detect some risks
        if bp.risks:
            engine = ArtifactEngine()
            a = engine.generate_prd("proj-x", blueprint=bp)
            self.assertIn("Risk", a.content)

    def test_blueprint_departments_in_tech_spec(self):
        bp = self._get_blueprint()
        if bp.departments:
            engine = ArtifactEngine()
            a = engine.generate_technical_specification("proj-x", blueprint=bp)
            # At least one department should appear
            dept_name = str(bp.departments[0].department)
            self.assertIn(dept_name, a.content)

    def test_prd_blueprint_complexity_in_content(self):
        bp = self._get_blueprint()
        engine = ArtifactEngine()
        a = engine.generate_prd("proj-x", blueprint=bp)
        self.assertIn(str(bp.complexity_score), a.content)


# ===========================================================================
# TestArtifactSummaryAndMetrics
# ===========================================================================

class TestArtifactSummaryAndMetrics(unittest.TestCase):

    def test_prd_summary_has_correct_type(self):
        engine = ArtifactEngine()
        a = engine.generate_prd("p1")
        s = a.summary()
        self.assertEqual(s["type"], "PRD")

    def test_ceo_report_summary_project_id_none(self):
        engine = ArtifactEngine()
        a = engine.generate_ceo_report()
        s = a.summary()
        self.assertIsNone(s["project_id"])

    def test_task_report_summary_has_project_id(self):
        engine = ArtifactEngine()
        a = engine.generate_task_report("my-proj")
        s = a.summary()
        self.assertEqual(s["project_id"], "my-proj")

    def test_word_count_grows_with_tasks(self):
        ee_empty = ExecutiveEngine()
        proj_empty = ee_empty.create_project("E", "D", "O", Priority.LOW)
        eng_empty = ArtifactEngine(executive_engine=ee_empty)
        a_empty = eng_empty.generate_task_report(proj_empty.id)

        ee_full = ExecutiveEngine()
        proj_full = ee_full.create_project("F", "D", "O", Priority.HIGH)
        for i in range(5):
            ee_full.create_task(proj_full.id, f"Task {i}", "Desc", "Agent", Priority.MEDIUM)
        eng_full = ArtifactEngine(executive_engine=ee_full)
        a_full = eng_full.generate_task_report(proj_full.id)

        self.assertGreater(a_full.word_count(), a_empty.word_count())

    def test_line_count_positive_for_prd(self):
        engine = ArtifactEngine()
        a = engine.generate_prd("p1")
        self.assertGreater(a.line_count(), 5)

    def test_summary_word_count_matches(self):
        engine = ArtifactEngine()
        a = engine.generate_prd("p1")
        s = a.summary()
        self.assertEqual(s["word_count"], a.word_count())

    def test_is_for_project_prd(self):
        engine = ArtifactEngine()
        a = engine.generate_prd("my-project-id")
        self.assertTrue(a.is_for_project("my-project-id"))

    def test_is_for_project_ceo_report(self):
        engine = ArtifactEngine()
        a = engine.generate_ceo_report()
        self.assertFalse(a.is_for_project("any-project"))


if __name__ == "__main__":
    unittest.main()
