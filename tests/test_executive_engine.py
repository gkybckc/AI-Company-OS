"""
Unit tests for the Executive Engine and its supporting models.

Covers:
- Task and Project dataclass correctness
- ExecutiveEngine.create_project
- ExecutiveEngine.create_task
- ExecutiveEngine.assign_task and its state-transition rules
- ExecutiveEngine.project_status (counts, completion, blockers)
- ExecutiveEngine.list_tasks
- ExecutiveEngine.generate_report
- Error handling for invalid IDs and disallowed state transitions

Run from the project root:
    python -m pytest tests/test_executive_engine.py -v
"""

import unittest
from datetime import datetime, timezone

from core.executive_engine import (
    ExecutiveEngine,
    InvalidTaskTransitionError,
    ProjectNotFoundError,
    TaskNotFoundError,
)
from core.project import Project, ProjectStatus
from core.task import Priority, Task, TaskStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_task(**overrides) -> Task:
    """Build a Task dataclass with sensible defaults for isolated tests."""
    defaults: dict = dict(
        id="task-001",
        title="Default Task",
        description="Default description",
        assigned_agent="TestAgent",
        status=TaskStatus.CREATED,
        priority=Priority.MEDIUM,
        dependencies=[],
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Task(**defaults)


def _make_project(**overrides) -> Project:
    """Build a Project dataclass with sensible defaults for isolated tests."""
    defaults: dict = dict(
        id="proj-001",
        title="Default Project",
        description="Default description",
        objective="Default objective",
        status=ProjectStatus.ACTIVE,
        priority=Priority.HIGH,
        created_at=datetime.now(timezone.utc),
        tasks=[],
    )
    defaults.update(overrides)
    return Project(**defaults)


# ---------------------------------------------------------------------------
# Task model
# ---------------------------------------------------------------------------

class TestTaskModel(unittest.TestCase):
    """Validate the Task dataclass and its enumerations."""

    def test_task_fields_are_stored_correctly(self) -> None:
        task = _make_task(title="Build API", assigned_agent="David")
        self.assertEqual(task.title, "Build API")
        self.assertEqual(task.assigned_agent, "David")

    def test_task_status_is_task_status_enum(self) -> None:
        task = _make_task()
        self.assertIsInstance(task.status, TaskStatus)

    def test_task_priority_is_priority_enum(self) -> None:
        task = _make_task()
        self.assertIsInstance(task.priority, Priority)

    def test_task_dependencies_default_is_empty_list(self) -> None:
        task = _make_task()
        self.assertEqual(task.dependencies, [])

    def test_task_status_enum_string_values(self) -> None:
        self.assertEqual(TaskStatus.CREATED.value, "CREATED")
        self.assertEqual(TaskStatus.ASSIGNED.value, "ASSIGNED")
        self.assertEqual(TaskStatus.WORKING.value, "WORKING")
        self.assertEqual(TaskStatus.REVIEW.value, "REVIEW")
        self.assertEqual(TaskStatus.APPROVED.value, "APPROVED")
        self.assertEqual(TaskStatus.REJECTED.value, "REJECTED")
        self.assertEqual(TaskStatus.ARCHIVED.value, "ARCHIVED")

    def test_priority_enum_string_values(self) -> None:
        self.assertEqual(Priority.LOW.value, "LOW")
        self.assertEqual(Priority.MEDIUM.value, "MEDIUM")
        self.assertEqual(Priority.HIGH.value, "HIGH")
        self.assertEqual(Priority.CRITICAL.value, "CRITICAL")

    def test_task_status_is_str_subclass(self) -> None:
        self.assertEqual(TaskStatus.CREATED, "CREATED")

    def test_task_with_dependencies(self) -> None:
        task = _make_task(dependencies=["dep-1", "dep-2"])
        self.assertIn("dep-1", task.dependencies)
        self.assertIn("dep-2", task.dependencies)
        self.assertEqual(len(task.dependencies), 2)


# ---------------------------------------------------------------------------
# Project model
# ---------------------------------------------------------------------------

class TestProjectModel(unittest.TestCase):
    """Validate the Project dataclass and its enumerations."""

    def test_project_fields_are_stored_correctly(self) -> None:
        project = _make_project(title="SaaS MVP", objective="Generate revenue")
        self.assertEqual(project.title, "SaaS MVP")
        self.assertEqual(project.objective, "Generate revenue")

    def test_project_status_is_project_status_enum(self) -> None:
        project = _make_project()
        self.assertIsInstance(project.status, ProjectStatus)

    def test_project_tasks_defaults_to_empty_list(self) -> None:
        project = _make_project()
        self.assertEqual(project.tasks, [])

    def test_project_status_enum_string_values(self) -> None:
        self.assertEqual(ProjectStatus.PENDING.value, "PENDING")
        self.assertEqual(ProjectStatus.ACTIVE.value, "ACTIVE")
        self.assertEqual(ProjectStatus.ON_HOLD.value, "ON_HOLD")
        self.assertEqual(ProjectStatus.COMPLETED.value, "COMPLETED")
        self.assertEqual(ProjectStatus.ARCHIVED.value, "ARCHIVED")

    def test_project_with_tasks(self) -> None:
        task = _make_task()
        project = _make_project(tasks=[task])
        self.assertIn(task, project.tasks)
        self.assertEqual(len(project.tasks), 1)


# ---------------------------------------------------------------------------
# ExecutiveEngine.create_project
# ---------------------------------------------------------------------------

class TestCreateProject(unittest.TestCase):
    """Tests for ExecutiveEngine.create_project."""

    def setUp(self) -> None:
        self.engine = ExecutiveEngine()

    def test_returns_project_instance(self) -> None:
        project = self.engine.create_project("P", "D", "O")
        self.assertIsInstance(project, Project)

    def test_stores_title_description_objective(self) -> None:
        project = self.engine.create_project(
            title="Agent System",
            description="Build core agents",
            objective="Enable autonomous company operation",
        )
        self.assertEqual(project.title, "Agent System")
        self.assertEqual(project.description, "Build core agents")
        self.assertEqual(project.objective, "Enable autonomous company operation")

    def test_default_status_is_active(self) -> None:
        project = self.engine.create_project("P", "D", "O")
        self.assertEqual(project.status, ProjectStatus.ACTIVE)

    def test_default_priority_is_medium(self) -> None:
        project = self.engine.create_project("P", "D", "O")
        self.assertEqual(project.priority, Priority.MEDIUM)

    def test_custom_priority_is_stored(self) -> None:
        project = self.engine.create_project("P", "D", "O", priority=Priority.CRITICAL)
        self.assertEqual(project.priority, Priority.CRITICAL)

    def test_generates_non_empty_id(self) -> None:
        project = self.engine.create_project("P", "D", "O")
        self.assertTrue(project.id)

    def test_generates_unique_ids(self) -> None:
        p1 = self.engine.create_project("P1", "D", "O")
        p2 = self.engine.create_project("P2", "D", "O")
        self.assertNotEqual(p1.id, p2.id)

    def test_task_list_starts_empty(self) -> None:
        project = self.engine.create_project("P", "D", "O")
        self.assertEqual(project.tasks, [])

    def test_created_at_is_recent_utc(self) -> None:
        before = datetime.now(timezone.utc)
        project = self.engine.create_project("P", "D", "O")
        after = datetime.now(timezone.utc)
        self.assertGreaterEqual(project.created_at, before)
        self.assertLessEqual(project.created_at, after)

    def test_multiple_projects_are_all_retrievable(self) -> None:
        p1 = self.engine.create_project("P1", "D", "O")
        p2 = self.engine.create_project("P2", "D", "O")
        s1 = self.engine.project_status(p1.id)
        s2 = self.engine.project_status(p2.id)
        self.assertEqual(s1["title"], "P1")
        self.assertEqual(s2["title"], "P2")


# ---------------------------------------------------------------------------
# ExecutiveEngine.create_task
# ---------------------------------------------------------------------------

class TestCreateTask(unittest.TestCase):
    """Tests for ExecutiveEngine.create_task."""

    def setUp(self) -> None:
        self.engine = ExecutiveEngine()
        self.project = self.engine.create_project("Test Project", "Desc", "Obj")

    def test_returns_task_instance(self) -> None:
        task = self.engine.create_task(self.project.id, "T", "D", "Agent")
        self.assertIsInstance(task, Task)

    def test_initial_status_is_created(self) -> None:
        task = self.engine.create_task(self.project.id, "T", "D", "Agent")
        self.assertEqual(task.status, TaskStatus.CREATED)

    def test_task_appended_to_project(self) -> None:
        task = self.engine.create_task(self.project.id, "T", "D", "Agent")
        self.assertIn(task, self.project.tasks)

    def test_task_count_in_project_grows(self) -> None:
        self.engine.create_task(self.project.id, "T1", "D", "Agent")
        self.engine.create_task(self.project.id, "T2", "D", "Agent")
        self.assertEqual(len(self.project.tasks), 2)

    def test_stores_title_description_assigned_agent(self) -> None:
        task = self.engine.create_task(
            self.project.id,
            title="Build REST API",
            description="Create CRUD endpoints for user resource",
            assigned_agent="David",
        )
        self.assertEqual(task.title, "Build REST API")
        self.assertEqual(task.description, "Create CRUD endpoints for user resource")
        self.assertEqual(task.assigned_agent, "David")

    def test_default_priority_is_medium(self) -> None:
        task = self.engine.create_task(self.project.id, "T", "D", "Agent")
        self.assertEqual(task.priority, Priority.MEDIUM)

    def test_custom_priority_stored(self) -> None:
        task = self.engine.create_task(
            self.project.id, "T", "D", "Agent", priority=Priority.HIGH
        )
        self.assertEqual(task.priority, Priority.HIGH)

    def test_default_dependencies_is_empty_list(self) -> None:
        task = self.engine.create_task(self.project.id, "T", "D", "Agent")
        self.assertEqual(task.dependencies, [])

    def test_dependencies_are_stored(self) -> None:
        t1 = self.engine.create_task(self.project.id, "T1", "D", "Agent")
        t2 = self.engine.create_task(
            self.project.id, "T2", "D", "Agent", dependencies=[t1.id]
        )
        self.assertEqual(t2.dependencies, [t1.id])

    def test_generates_unique_task_ids(self) -> None:
        t1 = self.engine.create_task(self.project.id, "T1", "D", "A")
        t2 = self.engine.create_task(self.project.id, "T2", "D", "A")
        self.assertNotEqual(t1.id, t2.id)

    def test_invalid_project_id_raises_project_not_found(self) -> None:
        with self.assertRaises(ProjectNotFoundError):
            self.engine.create_task(
                project_id="does-not-exist",
                title="T",
                description="D",
                assigned_agent="Agent",
            )

    def test_task_created_at_is_recent_utc(self) -> None:
        before = datetime.now(timezone.utc)
        task = self.engine.create_task(self.project.id, "T", "D", "Agent")
        after = datetime.now(timezone.utc)
        self.assertGreaterEqual(task.created_at, before)
        self.assertLessEqual(task.created_at, after)


# ---------------------------------------------------------------------------
# ExecutiveEngine.assign_task
# ---------------------------------------------------------------------------

class TestAssignTask(unittest.TestCase):
    """Tests for ExecutiveEngine.assign_task and its state-transition rules."""

    def setUp(self) -> None:
        self.engine = ExecutiveEngine()
        self.project = self.engine.create_project("P", "D", "O")
        self.task = self.engine.create_task(
            self.project.id, "Build UI", "Create dashboard", "Emily"
        )

    def test_advances_status_to_assigned(self) -> None:
        self.engine.assign_task(self.task.id, "Emily")
        self.assertEqual(self.task.status, TaskStatus.ASSIGNED)

    def test_updates_assigned_agent(self) -> None:
        self.engine.assign_task(self.task.id, "Alexander")
        self.assertEqual(self.task.assigned_agent, "Alexander")

    def test_returns_updated_task(self) -> None:
        result = self.engine.assign_task(self.task.id, "Emily")
        self.assertIsInstance(result, Task)
        self.assertEqual(result.id, self.task.id)
        self.assertEqual(result.status, TaskStatus.ASSIGNED)

    def test_reassign_rejected_task_succeeds(self) -> None:
        self.task.status = TaskStatus.REJECTED
        self.engine.assign_task(self.task.id, "DifferentAgent")
        self.assertEqual(self.task.status, TaskStatus.ASSIGNED)
        self.assertEqual(self.task.assigned_agent, "DifferentAgent")

    def test_invalid_task_id_raises_task_not_found(self) -> None:
        with self.assertRaises(TaskNotFoundError):
            self.engine.assign_task("does-not-exist", "Agent")

    def test_assign_from_working_raises_invalid_transition(self) -> None:
        self.task.status = TaskStatus.WORKING
        with self.assertRaises(InvalidTaskTransitionError):
            self.engine.assign_task(self.task.id, "Agent")

    def test_assign_from_review_raises_invalid_transition(self) -> None:
        self.task.status = TaskStatus.REVIEW
        with self.assertRaises(InvalidTaskTransitionError):
            self.engine.assign_task(self.task.id, "Agent")

    def test_assign_from_approved_raises_invalid_transition(self) -> None:
        self.task.status = TaskStatus.APPROVED
        with self.assertRaises(InvalidTaskTransitionError):
            self.engine.assign_task(self.task.id, "Agent")

    def test_assign_from_archived_raises_invalid_transition(self) -> None:
        self.task.status = TaskStatus.ARCHIVED
        with self.assertRaises(InvalidTaskTransitionError):
            self.engine.assign_task(self.task.id, "Agent")

    def test_assign_from_assigned_raises_invalid_transition(self) -> None:
        self.engine.assign_task(self.task.id, "Emily")
        with self.assertRaises(InvalidTaskTransitionError):
            self.engine.assign_task(self.task.id, "Emily")

    def test_error_message_names_the_task(self) -> None:
        self.task.status = TaskStatus.WORKING
        with self.assertRaises(InvalidTaskTransitionError) as ctx:
            self.engine.assign_task(self.task.id, "Agent")
        self.assertIn("Build UI", str(ctx.exception))


# ---------------------------------------------------------------------------
# ExecutiveEngine.project_status
# ---------------------------------------------------------------------------

class TestProjectStatus(unittest.TestCase):
    """Tests for ExecutiveEngine.project_status."""

    def setUp(self) -> None:
        self.engine = ExecutiveEngine()
        self.project = self.engine.create_project("Dashboard", "Build it", "CEO goal")

    def test_returns_dict(self) -> None:
        result = self.engine.project_status(self.project.id)
        self.assertIsInstance(result, dict)

    def test_contains_all_required_keys(self) -> None:
        result = self.engine.project_status(self.project.id)
        expected_keys = {
            "project_id", "title", "status", "priority",
            "total_tasks", "task_counts", "completion_percentage", "blocked_tasks",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_empty_project_has_zero_totals(self) -> None:
        result = self.engine.project_status(self.project.id)
        self.assertEqual(result["total_tasks"], 0)
        self.assertEqual(result["completion_percentage"], 0.0)
        self.assertEqual(result["blocked_tasks"], [])

    def test_total_tasks_matches_task_count(self) -> None:
        self.engine.create_task(self.project.id, "T1", "D", "A")
        self.engine.create_task(self.project.id, "T2", "D", "A")
        result = self.engine.project_status(self.project.id)
        self.assertEqual(result["total_tasks"], 2)

    def test_completion_is_zero_when_no_tasks_approved(self) -> None:
        self.engine.create_task(self.project.id, "T", "D", "A")
        result = self.engine.project_status(self.project.id)
        self.assertEqual(result["completion_percentage"], 0.0)

    def test_completion_fifty_percent_when_half_approved(self) -> None:
        t1 = self.engine.create_task(self.project.id, "T1", "D", "A")
        self.engine.create_task(self.project.id, "T2", "D", "A")
        t1.status = TaskStatus.APPROVED
        result = self.engine.project_status(self.project.id)
        self.assertEqual(result["completion_percentage"], 50.0)

    def test_completion_one_hundred_when_all_approved(self) -> None:
        t1 = self.engine.create_task(self.project.id, "T1", "D", "A")
        t2 = self.engine.create_task(self.project.id, "T2", "D", "A")
        t1.status = TaskStatus.APPROVED
        t2.status = TaskStatus.APPROVED
        result = self.engine.project_status(self.project.id)
        self.assertEqual(result["completion_percentage"], 100.0)

    def test_task_counts_reflect_statuses(self) -> None:
        t1 = self.engine.create_task(self.project.id, "T1", "D", "A")
        t2 = self.engine.create_task(self.project.id, "T2", "D", "A")
        t1.status = TaskStatus.APPROVED
        result = self.engine.project_status(self.project.id)
        self.assertEqual(result["task_counts"]["APPROVED"], 1)
        self.assertEqual(result["task_counts"]["CREATED"], 1)

    def test_task_counts_contain_all_statuses(self) -> None:
        result = self.engine.project_status(self.project.id)
        for status in TaskStatus:
            self.assertIn(status.value, result["task_counts"])

    def test_blocked_task_detected_when_dependency_not_approved(self) -> None:
        t1 = self.engine.create_task(self.project.id, "T1", "D", "A")
        t2 = self.engine.create_task(
            self.project.id, "T2", "D", "A", dependencies=[t1.id]
        )
        result = self.engine.project_status(self.project.id)
        self.assertIn(t2.id, result["blocked_tasks"])
        self.assertNotIn(t1.id, result["blocked_tasks"])

    def test_blocked_task_cleared_when_dependency_approved(self) -> None:
        t1 = self.engine.create_task(self.project.id, "T1", "D", "A")
        t2 = self.engine.create_task(
            self.project.id, "T2", "D", "A", dependencies=[t1.id]
        )
        t1.status = TaskStatus.APPROVED
        result = self.engine.project_status(self.project.id)
        self.assertNotIn(t2.id, result["blocked_tasks"])

    def test_task_without_dependencies_is_never_blocked(self) -> None:
        self.engine.create_task(self.project.id, "T", "D", "A")
        result = self.engine.project_status(self.project.id)
        self.assertEqual(result["blocked_tasks"], [])

    def test_project_id_and_title_in_result(self) -> None:
        result = self.engine.project_status(self.project.id)
        self.assertEqual(result["project_id"], self.project.id)
        self.assertEqual(result["title"], "Dashboard")

    def test_invalid_project_id_raises_project_not_found(self) -> None:
        with self.assertRaises(ProjectNotFoundError):
            self.engine.project_status("does-not-exist")


# ---------------------------------------------------------------------------
# ExecutiveEngine.list_tasks
# ---------------------------------------------------------------------------

class TestListTasks(unittest.TestCase):
    """Tests for ExecutiveEngine.list_tasks."""

    def setUp(self) -> None:
        self.engine = ExecutiveEngine()
        self.project = self.engine.create_project("P", "D", "O")

    def test_returns_empty_list_for_new_project(self) -> None:
        tasks = self.engine.list_tasks(self.project.id)
        self.assertEqual(tasks, [])

    def test_returns_all_tasks_in_creation_order(self) -> None:
        t1 = self.engine.create_task(self.project.id, "T1", "D", "A")
        t2 = self.engine.create_task(self.project.id, "T2", "D", "A")
        tasks = self.engine.list_tasks(self.project.id)
        self.assertEqual(len(tasks), 2)
        self.assertIs(tasks[0], t1)
        self.assertIs(tasks[1], t2)

    def test_returns_shallow_copy_not_original_list(self) -> None:
        self.engine.create_task(self.project.id, "T", "D", "A")
        tasks = self.engine.list_tasks(self.project.id)
        tasks.clear()
        self.assertEqual(len(self.project.tasks), 1)

    def test_task_objects_are_live_references(self) -> None:
        task = self.engine.create_task(self.project.id, "T", "D", "A")
        tasks = self.engine.list_tasks(self.project.id)
        tasks[0].status = TaskStatus.WORKING
        self.assertEqual(task.status, TaskStatus.WORKING)

    def test_invalid_project_id_raises_project_not_found(self) -> None:
        with self.assertRaises(ProjectNotFoundError):
            self.engine.list_tasks("does-not-exist")


# ---------------------------------------------------------------------------
# ExecutiveEngine.generate_report
# ---------------------------------------------------------------------------

class TestGenerateReport(unittest.TestCase):
    """Tests for ExecutiveEngine.generate_report."""

    def setUp(self) -> None:
        self.engine = ExecutiveEngine()
        self.project = self.engine.create_project(
            title="SaaS MVP",
            description="Build the first product",
            objective="Generate the first dollar of revenue",
        )

    def test_returns_string(self) -> None:
        report = self.engine.generate_report(self.project.id)
        self.assertIsInstance(report, str)

    def test_report_is_non_empty(self) -> None:
        report = self.engine.generate_report(self.project.id)
        self.assertGreater(len(report), 50)

    def test_contains_project_title(self) -> None:
        report = self.engine.generate_report(self.project.id)
        self.assertIn("SaaS MVP", report)

    def test_contains_objective(self) -> None:
        report = self.engine.generate_report(self.project.id)
        self.assertIn("Generate the first dollar of revenue", report)

    def test_contains_task_title_and_agent(self) -> None:
        self.engine.create_task(
            self.project.id, "Build REST API", "Create endpoints", "David"
        )
        report = self.engine.generate_report(self.project.id)
        self.assertIn("Build REST API", report)
        self.assertIn("David", report)

    def test_contains_completion_percentage(self) -> None:
        t1 = self.engine.create_task(self.project.id, "T1", "D", "A")
        self.engine.create_task(self.project.id, "T2", "D", "A")
        t1.status = TaskStatus.APPROVED
        report = self.engine.generate_report(self.project.id)
        self.assertIn("50.0%", report)

    def test_contains_blockers_section_when_blocked(self) -> None:
        t1 = self.engine.create_task(self.project.id, "T1", "D", "A")
        self.engine.create_task(
            self.project.id, "T2", "D", "A", dependencies=[t1.id]
        )
        report = self.engine.generate_report(self.project.id)
        self.assertIn("Blocker", report)

    def test_no_blockers_section_when_all_clear(self) -> None:
        self.engine.create_task(self.project.id, "T", "D", "A")
        report = self.engine.generate_report(self.project.id)
        self.assertNotIn("Blocker", report)

    def test_blockers_section_absent_when_dependencies_approved(self) -> None:
        t1 = self.engine.create_task(self.project.id, "T1", "D", "A")
        self.engine.create_task(
            self.project.id, "T2", "D", "A", dependencies=[t1.id]
        )
        t1.status = TaskStatus.APPROVED
        report = self.engine.generate_report(self.project.id)
        self.assertNotIn("Blocker", report)

    def test_contains_project_id(self) -> None:
        report = self.engine.generate_report(self.project.id)
        self.assertIn(self.project.id, report)

    def test_invalid_project_id_raises_project_not_found(self) -> None:
        with self.assertRaises(ProjectNotFoundError):
            self.engine.generate_report("does-not-exist")


# ---------------------------------------------------------------------------
# Cross-method integration scenarios
# ---------------------------------------------------------------------------

class TestIntegrationScenarios(unittest.TestCase):
    """
    Multi-step scenarios that exercise the full task lifecycle
    across multiple public methods.
    """

    def setUp(self) -> None:
        self.engine = ExecutiveEngine()

    def test_full_task_lifecycle_through_approval(self) -> None:
        project = self.engine.create_project("Full Lifecycle", "D", "O")
        task = self.engine.create_task(project.id, "Build API", "D", "David")

        self.assertEqual(task.status, TaskStatus.CREATED)

        self.engine.assign_task(task.id, "David")
        self.assertEqual(task.status, TaskStatus.ASSIGNED)

        task.status = TaskStatus.WORKING
        task.status = TaskStatus.REVIEW
        task.status = TaskStatus.APPROVED

        status = self.engine.project_status(project.id)
        self.assertEqual(status["completion_percentage"], 100.0)
        self.assertEqual(status["task_counts"]["APPROVED"], 1)

    def test_dependency_chain_blocks_then_unblocks(self) -> None:
        project = self.engine.create_project("Chain", "D", "O")
        t1 = self.engine.create_task(project.id, "Step 1", "D", "A")
        t2 = self.engine.create_task(project.id, "Step 2", "D", "A", dependencies=[t1.id])
        t3 = self.engine.create_task(project.id, "Step 3", "D", "A", dependencies=[t2.id])

        status = self.engine.project_status(project.id)
        self.assertIn(t2.id, status["blocked_tasks"])
        self.assertIn(t3.id, status["blocked_tasks"])

        t1.status = TaskStatus.APPROVED
        status = self.engine.project_status(project.id)
        self.assertNotIn(t2.id, status["blocked_tasks"])
        self.assertIn(t3.id, status["blocked_tasks"])

        t2.status = TaskStatus.APPROVED
        status = self.engine.project_status(project.id)
        self.assertNotIn(t3.id, status["blocked_tasks"])

    def test_rejected_task_can_be_reassigned_and_reapproved(self) -> None:
        project = self.engine.create_project("Rejection Cycle", "D", "O")
        task = self.engine.create_task(project.id, "Design UI", "D", "Emily")
        self.engine.assign_task(task.id, "Emily")

        task.status = TaskStatus.REJECTED

        self.engine.assign_task(task.id, "NewDesigner")
        self.assertEqual(task.assigned_agent, "NewDesigner")
        self.assertEqual(task.status, TaskStatus.ASSIGNED)

        task.status = TaskStatus.APPROVED
        status = self.engine.project_status(project.id)
        self.assertEqual(status["completion_percentage"], 100.0)

    def test_two_independent_projects_do_not_interfere(self) -> None:
        p1 = self.engine.create_project("Project Alpha", "D", "O")
        p2 = self.engine.create_project("Project Beta", "D", "O")

        t1 = self.engine.create_task(p1.id, "Alpha Task", "D", "A")
        t2 = self.engine.create_task(p2.id, "Beta Task", "D", "A")

        t1.status = TaskStatus.APPROVED

        s1 = self.engine.project_status(p1.id)
        s2 = self.engine.project_status(p2.id)

        self.assertEqual(s1["completion_percentage"], 100.0)
        self.assertEqual(s2["completion_percentage"], 0.0)
        self.assertEqual(self.engine.list_tasks(p1.id), [t1])
        self.assertEqual(self.engine.list_tasks(p2.id), [t2])

    def test_report_reflects_live_task_state(self) -> None:
        project = self.engine.create_project("Live State", "D", "O")
        task = self.engine.create_task(project.id, "Code Review", "D", "Agent")

        report_before = self.engine.generate_report(project.id)
        self.assertIn("CREATED", report_before)

        task.status = TaskStatus.APPROVED
        report_after = self.engine.generate_report(project.id)
        self.assertIn("APPROVED", report_after)
        self.assertIn("100.0%", report_after)


if __name__ == "__main__":
    unittest.main()
