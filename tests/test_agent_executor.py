"""
Tests for Feature 17.3 -- Agent Executor.

Covers ExecutionContext, ExecutionResult, ExecutionHistory, ExecutionRecord,
and AgentExecutor across construction, validation, pipeline execution,
optional engines, history, statistics, and end-to-end scenarios.

Run from the repo root:
    python -m unittest tests.test_agent_executor -v
"""

import sys
import os
import unittest
from dataclasses import dataclass
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai.execution_context import ExecutionContext, ExecutionContextError
from core.ai.execution_result import ExecutionResult
from core.ai.execution_history import ExecutionHistory, ExecutionRecord
from core.ai.agent_executor import (
    AgentExecutor,
    ExecutionError,
    AgentInvalidContextError,
    MissingProviderError,
)
from core.ai.provider_registry import ProviderRegistry
from core.ai.mock_provider import MockProvider
from core.ai.provider_response import ProviderResponse
from core.ai.prompt_builder import PromptBuilder
from core.artifact_engine import ArtifactEngine
from core.memory_engine import MemoryEngine
from core.memory_category import MemoryCategory
from core.memory_scope import MemoryScope


# ---------------------------------------------------------------------------
# Test helper objects
# ---------------------------------------------------------------------------

@dataclass
class FakeProject:
    id: str
    title: str
    description: str


@dataclass
class FakeTask:
    id: str
    title: str
    description: str


def _make_project(
    pid: str = "proj-001",
    title: str = "Test Project",
    description: str = "A project for testing purposes.",
) -> FakeProject:
    return FakeProject(id=pid, title=title, description=description)


def _make_task(
    tid: str = "task-001",
    title: str = "Auth Task",
    description: str = "Implement authentication API with JWT tokens.",
) -> FakeTask:
    return FakeTask(id=tid, title=title, description=description)


def _make_context(**kwargs) -> ExecutionContext:
    defaults = {
        "employee_id": "agent-001",
        "employee_role": "Backend Agent",
        "department": "Engineering",
        "project": _make_project(),
        "workflow_stage": "Implementation",
        "task": _make_task(),
    }
    defaults.update(kwargs)
    return ExecutionContext(**defaults)


def _make_registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register(MockProvider())
    return registry


def _make_executor(**kwargs) -> AgentExecutor:
    defaults = {"provider_registry": _make_registry()}
    defaults.update(kwargs)
    return AgentExecutor(**defaults)


def _make_result(success: bool = True, **kwargs) -> ExecutionResult:
    defaults = {
        "success": success,
        "provider_response": None,
        "generated_artifacts": [],
        "memory_entries": [],
        "execution_time": 0.05,
        "warnings": [],
        "errors": [],
    }
    defaults.update(kwargs)
    return ExecutionResult(**defaults)


# ---------------------------------------------------------------------------
# Class 1: TestExecutionContextConstruction (8 tests)
# ---------------------------------------------------------------------------

class TestExecutionContextConstruction(unittest.TestCase):

    def test_basic_construction(self):
        ctx = _make_context()
        self.assertEqual(ctx.employee_id, "agent-001")
        self.assertEqual(ctx.employee_role, "Backend Agent")
        self.assertEqual(ctx.department, "Engineering")
        self.assertEqual(ctx.workflow_stage, "Implementation")

    def test_default_constraints(self):
        ctx = _make_context()
        self.assertEqual(ctx.constraints, [])

    def test_default_seniority(self):
        ctx = _make_context()
        self.assertEqual(ctx.seniority, "")

    def test_default_context(self):
        ctx = _make_context()
        self.assertEqual(ctx.context, "")

    def test_with_constraints(self):
        ctx = _make_context(constraints=["No external libs", "Use bcrypt"])
        self.assertEqual(ctx.constraints, ["No external libs", "Use bcrypt"])

    def test_with_seniority(self):
        ctx = _make_context(seniority="Senior")
        self.assertEqual(ctx.seniority, "Senior")

    def test_with_context(self):
        ctx = _make_context(context="PostgreSQL 15 in use.")
        self.assertEqual(ctx.context, "PostgreSQL 15 in use.")

    def test_project_and_task_stored(self):
        project = _make_project()
        task = _make_task()
        ctx = ExecutionContext(
            employee_id="e1", employee_role="QA Engineer",
            department="QA", project=project,
            workflow_stage="Testing", task=task,
        )
        self.assertIs(ctx.project, project)
        self.assertIs(ctx.task, task)


# ---------------------------------------------------------------------------
# Class 2: TestExecutionContextValidate (8 tests)
# ---------------------------------------------------------------------------

class TestExecutionContextValidate(unittest.TestCase):

    def test_valid_context_no_error(self):
        ctx = _make_context()
        ctx.validate()  # must not raise

    def test_blank_employee_id_raises(self):
        ctx = _make_context(employee_id="")
        with self.assertRaises(ExecutionContextError):
            ctx.validate()

    def test_blank_employee_role_raises(self):
        ctx = _make_context(employee_role="")
        with self.assertRaises(ExecutionContextError):
            ctx.validate()

    def test_blank_department_raises(self):
        ctx = _make_context(department="")
        with self.assertRaises(ExecutionContextError):
            ctx.validate()

    def test_blank_workflow_stage_raises(self):
        ctx = _make_context(workflow_stage="")
        with self.assertRaises(ExecutionContextError):
            ctx.validate()

    def test_blank_task_raises(self):
        ctx = _make_context(task=None)
        with self.assertRaises(ExecutionContextError):
            ctx.validate()

    def test_multiple_blank_fields_single_raise(self):
        ctx = _make_context(employee_id="", department="")
        with self.assertRaises(ExecutionContextError) as cm:
            ctx.validate()
        msg = str(cm.exception)
        self.assertIn("employee_id", msg)
        self.assertIn("department", msg)

    def test_whitespace_only_employee_id_raises(self):
        ctx = _make_context(employee_id="   ")
        with self.assertRaises(ExecutionContextError):
            ctx.validate()


# ---------------------------------------------------------------------------
# Class 3: TestExecutionContextProjectAttribute (8 tests)
# ---------------------------------------------------------------------------

class TestExecutionContextProjectAttribute(unittest.TestCase):

    def test_has_project_true(self):
        ctx = _make_context()
        self.assertTrue(ctx.has_project())

    def test_has_project_false_when_none(self):
        ctx = _make_context(project=None)
        self.assertFalse(ctx.has_project())

    def test_project_id_from_attribute(self):
        ctx = _make_context(project=_make_project(pid="proj-xyz"))
        self.assertEqual(ctx.project_id(), "proj-xyz")

    def test_project_name_from_title_attribute(self):
        ctx = _make_context(project=_make_project(title="Auth Service"))
        self.assertEqual(ctx.project_name(), "Auth Service")

    def test_project_description_from_attribute(self):
        ctx = _make_context(project=_make_project(description="Handles auth."))
        self.assertEqual(ctx.project_description(), "Handles auth.")

    def test_project_id_none_when_no_project(self):
        ctx = _make_context(project=None)
        self.assertIsNone(ctx.project_id())

    def test_project_name_empty_when_no_project(self):
        ctx = _make_context(project=None)
        self.assertEqual(ctx.project_name(), "")

    def test_project_description_empty_when_no_project(self):
        ctx = _make_context(project=None)
        self.assertEqual(ctx.project_description(), "")


# ---------------------------------------------------------------------------
# Class 4: TestExecutionContextProjectDict (6 tests)
# ---------------------------------------------------------------------------

class TestExecutionContextProjectDict(unittest.TestCase):

    def test_project_id_from_dict(self):
        ctx = _make_context(project={"id": "d-proj-1", "title": "Dict Project", "description": "desc"})
        self.assertEqual(ctx.project_id(), "d-proj-1")

    def test_project_name_from_dict_title(self):
        ctx = _make_context(project={"id": "x", "title": "Dict Title", "description": ""})
        self.assertEqual(ctx.project_name(), "Dict Title")

    def test_project_description_from_dict(self):
        ctx = _make_context(project={"id": "x", "title": "T", "description": "Dict desc"})
        self.assertEqual(ctx.project_description(), "Dict desc")

    def test_project_name_from_dict_name_key(self):
        ctx = _make_context(project={"id": "x", "name": "Alt Name"})
        self.assertEqual(ctx.project_name(), "Alt Name")

    def test_project_id_blank_in_dict_returns_none(self):
        ctx = _make_context(project={"id": "  ", "title": "P"})
        self.assertIsNone(ctx.project_id())

    def test_dict_project_has_project_true(self):
        ctx = _make_context(project={"id": "x", "title": "P"})
        self.assertTrue(ctx.has_project())


# ---------------------------------------------------------------------------
# Class 5: TestExecutionContextProjectNoneAndString (6 tests)
# ---------------------------------------------------------------------------

class TestExecutionContextProjectNoneAndString(unittest.TestCase):

    def test_project_id_blank_attribute_returns_none(self):
        ctx = _make_context(project=_make_project(pid=""))
        self.assertIsNone(ctx.project_id())

    def test_project_name_from_string_project(self):
        ctx = _make_context(project="String Project Name")
        self.assertEqual(ctx.project_name(), "String Project Name")

    def test_project_description_from_string_project(self):
        ctx = _make_context(project="Some project string")
        self.assertEqual(ctx.project_description(), "Some project string")

    def test_project_none_not_has_project(self):
        ctx = _make_context(project=None)
        self.assertFalse(ctx.has_project())

    def test_project_blank_id_attribute_none(self):
        p = _make_project(pid="   ")
        ctx = _make_context(project=p)
        self.assertIsNone(ctx.project_id())

    def test_dict_project_missing_id_key(self):
        ctx = _make_context(project={"title": "No ID"})
        self.assertIsNone(ctx.project_id())


# ---------------------------------------------------------------------------
# Class 6: TestExecutionContextTaskString (6 tests)
# ---------------------------------------------------------------------------

class TestExecutionContextTaskString(unittest.TestCase):

    def test_task_description_from_plain_string(self):
        ctx = _make_context(task="Build the login endpoint.")
        self.assertEqual(ctx.task_description(), "Build the login endpoint.")

    def test_task_title_from_plain_string(self):
        ctx = _make_context(task="Build the login endpoint.")
        self.assertEqual(ctx.task_title(), "Build the login endpoint.")

    def test_task_id_none_for_string_task(self):
        ctx = _make_context(task="Some task text")
        self.assertIsNone(ctx.task_id())

    def test_has_task_true_for_string(self):
        ctx = _make_context(task="Some text")
        self.assertTrue(ctx.has_task())

    def test_has_task_false_for_none(self):
        ctx = _make_context(task=None)
        self.assertFalse(ctx.has_task())

    def test_task_description_empty_for_none(self):
        ctx = _make_context(task=None)
        self.assertEqual(ctx.task_description(), "")


# ---------------------------------------------------------------------------
# Class 7: TestExecutionContextTaskAttribute (8 tests)
# ---------------------------------------------------------------------------

class TestExecutionContextTaskAttribute(unittest.TestCase):

    def test_task_description_from_description_attribute(self):
        task = _make_task(description="Implement auth.")
        ctx = _make_context(task=task)
        self.assertEqual(ctx.task_description(), "Implement auth.")

    def test_task_id_from_attribute(self):
        task = _make_task(tid="task-999")
        ctx = _make_context(task=task)
        self.assertEqual(ctx.task_id(), "task-999")

    def test_task_title_from_attribute(self):
        task = _make_task(title="Auth Implementation")
        ctx = _make_context(task=task)
        self.assertEqual(ctx.task_title(), "Auth Implementation")

    def test_task_description_prefers_description_over_title(self):
        task = _make_task(description="Full description.", title="Short title")
        ctx = _make_context(task=task)
        self.assertEqual(ctx.task_description(), "Full description.")

    def test_task_description_falls_back_to_title(self):
        task = FakeTask(id="t1", title="Title Only", description="")
        ctx = _make_context(task=task)
        self.assertEqual(ctx.task_description(), "Title Only")

    def test_task_id_blank_returns_none(self):
        task = FakeTask(id="", title="T", description="desc")
        ctx = _make_context(task=task)
        self.assertIsNone(ctx.task_id())

    def test_task_title_truncated_at_60(self):
        long_title = "A" * 100
        task = FakeTask(id="t1", title=long_title, description="")
        ctx = _make_context(task=task)
        self.assertLessEqual(len(ctx.task_title()), 60)

    def test_has_task_true_for_object(self):
        ctx = _make_context(task=_make_task())
        self.assertTrue(ctx.has_task())


# ---------------------------------------------------------------------------
# Class 8: TestExecutionContextTaskDict (6 tests)
# ---------------------------------------------------------------------------

class TestExecutionContextTaskDict(unittest.TestCase):

    def test_task_description_from_dict(self):
        ctx = _make_context(task={"id": "t1", "title": "T", "description": "Dict task desc"})
        self.assertEqual(ctx.task_description(), "Dict task desc")

    def test_task_id_from_dict(self):
        ctx = _make_context(task={"id": "t-dict-1", "description": "desc"})
        self.assertEqual(ctx.task_id(), "t-dict-1")

    def test_task_title_from_dict(self):
        ctx = _make_context(task={"id": "t1", "title": "Dict Title", "description": "desc"})
        self.assertEqual(ctx.task_title(), "Dict Title")

    def test_task_description_fallback_to_title_in_dict(self):
        ctx = _make_context(task={"id": "t1", "title": "Dict Title"})
        self.assertEqual(ctx.task_description(), "Dict Title")

    def test_task_id_blank_dict_returns_none(self):
        ctx = _make_context(task={"id": "  ", "description": "desc"})
        self.assertIsNone(ctx.task_id())

    def test_has_task_true_for_dict(self):
        ctx = _make_context(task={"id": "t1", "description": "desc"})
        self.assertTrue(ctx.has_task())


# ---------------------------------------------------------------------------
# Class 9: TestExecutionContextConstraintHelpers (5 tests)
# ---------------------------------------------------------------------------

class TestExecutionContextConstraintHelpers(unittest.TestCase):

    def test_has_constraints_false_by_default(self):
        ctx = _make_context()
        self.assertFalse(ctx.has_constraints())

    def test_has_constraints_true_when_set(self):
        ctx = _make_context(constraints=["c1"])
        self.assertTrue(ctx.has_constraints())

    def test_constraint_count_zero(self):
        ctx = _make_context()
        self.assertEqual(ctx.constraint_count(), 0)

    def test_constraint_count_matches(self):
        ctx = _make_context(constraints=["c1", "c2", "c3"])
        self.assertEqual(ctx.constraint_count(), 3)

    def test_constraint_count_one(self):
        ctx = _make_context(constraints=["only one"])
        self.assertEqual(ctx.constraint_count(), 1)


# ---------------------------------------------------------------------------
# Class 10: TestExecutionContextToDict (6 tests)
# ---------------------------------------------------------------------------

class TestExecutionContextToDict(unittest.TestCase):

    def test_to_dict_returns_dict(self):
        ctx = _make_context()
        self.assertIsInstance(ctx.to_dict(), dict)

    def test_to_dict_contains_employee_id(self):
        ctx = _make_context(employee_id="agent-42")
        d = ctx.to_dict()
        self.assertEqual(d["employee_id"], "agent-42")

    def test_to_dict_contains_project_fields(self):
        ctx = _make_context(project=_make_project(pid="p1", title="P1"))
        d = ctx.to_dict()
        self.assertEqual(d["project_id"], "p1")
        self.assertEqual(d["project_name"], "P1")

    def test_to_dict_contains_task_description(self):
        ctx = _make_context(task="My task desc")
        d = ctx.to_dict()
        self.assertEqual(d["task_description"], "My task desc")

    def test_to_dict_constraints_is_list(self):
        ctx = _make_context(constraints=["c1", "c2"])
        d = ctx.to_dict()
        self.assertIsInstance(d["constraints"], list)
        self.assertEqual(d["constraint_count"], 2)

    def test_to_dict_has_expected_keys(self):
        d = _make_context().to_dict()
        for key in ["employee_id", "employee_role", "department",
                    "workflow_stage", "project_id", "project_name",
                    "task_description", "constraint_count"]:
            self.assertIn(key, d)


# ---------------------------------------------------------------------------
# Class 11: TestExecutionContextSummary (5 tests)
# ---------------------------------------------------------------------------

class TestExecutionContextSummary(unittest.TestCase):

    def test_summary_is_string(self):
        ctx = _make_context()
        self.assertIsInstance(ctx.summary(), str)

    def test_summary_contains_role(self):
        ctx = _make_context(employee_role="QA Engineer")
        self.assertIn("QA Engineer", ctx.summary())

    def test_summary_contains_department(self):
        ctx = _make_context(department="QA")
        self.assertIn("QA", ctx.summary())

    def test_summary_contains_stage(self):
        ctx = _make_context(workflow_stage="Testing")
        self.assertIn("Testing", ctx.summary())

    def test_summary_non_empty(self):
        ctx = _make_context()
        self.assertGreater(len(ctx.summary()), 0)


# ---------------------------------------------------------------------------
# Class 12: TestExecutionResultConstruction (8 tests)
# ---------------------------------------------------------------------------

class TestExecutionResultConstruction(unittest.TestCase):

    def test_basic_success(self):
        r = _make_result(success=True)
        self.assertTrue(r.success)

    def test_basic_failure(self):
        r = _make_result(success=False)
        self.assertFalse(r.success)

    def test_empty_artifacts(self):
        r = _make_result()
        self.assertEqual(r.generated_artifacts, [])

    def test_empty_memory_entries(self):
        r = _make_result()
        self.assertEqual(r.memory_entries, [])

    def test_empty_warnings(self):
        r = _make_result()
        self.assertEqual(r.warnings, [])

    def test_empty_errors(self):
        r = _make_result()
        self.assertEqual(r.errors, [])

    def test_with_warnings(self):
        r = _make_result(warnings=["Artifact skipped"])
        self.assertEqual(r.warnings, ["Artifact skipped"])

    def test_with_errors(self):
        r = _make_result(success=False, errors=["No provider"])
        self.assertEqual(r.errors, ["No provider"])


# ---------------------------------------------------------------------------
# Class 13: TestExecutionResultPresenceHelpers (10 tests)
# ---------------------------------------------------------------------------

class TestExecutionResultPresenceHelpers(unittest.TestCase):

    def test_has_artifacts_false(self):
        self.assertFalse(_make_result().has_artifacts())

    def test_has_artifacts_true(self):
        r = _make_result(generated_artifacts=["stub"])
        self.assertTrue(r.has_artifacts())

    def test_has_memory_entries_false(self):
        self.assertFalse(_make_result().has_memory_entries())

    def test_has_memory_entries_true(self):
        r = _make_result(memory_entries=["entry"])
        self.assertTrue(r.has_memory_entries())

    def test_has_warnings_false(self):
        self.assertFalse(_make_result().has_warnings())

    def test_has_warnings_true(self):
        r = _make_result(warnings=["warn"])
        self.assertTrue(r.has_warnings())

    def test_has_errors_false(self):
        self.assertFalse(_make_result().has_errors())

    def test_has_errors_true(self):
        r = _make_result(success=False, errors=["err"])
        self.assertTrue(r.has_errors())

    def test_has_response_false(self):
        self.assertFalse(_make_result(provider_response=None).has_response())

    def test_has_response_true(self):
        resp = ProviderResponse(content="x", tokens_used=1, provider_name="M",
                                execution_time=0.01)
        r = _make_result(provider_response=resp)
        self.assertTrue(r.has_response())


# ---------------------------------------------------------------------------
# Class 14: TestExecutionResultCountHelpers (6 tests)
# ---------------------------------------------------------------------------

class TestExecutionResultCountHelpers(unittest.TestCase):

    def test_artifact_count_zero(self):
        self.assertEqual(_make_result().artifact_count(), 0)

    def test_artifact_count_nonzero(self):
        r = _make_result(generated_artifacts=["a", "b"])
        self.assertEqual(r.artifact_count(), 2)

    def test_memory_count_zero(self):
        self.assertEqual(_make_result().memory_count(), 0)

    def test_memory_count_nonzero(self):
        r = _make_result(memory_entries=["m"])
        self.assertEqual(r.memory_count(), 1)

    def test_warning_count_zero(self):
        self.assertEqual(_make_result().warning_count(), 0)

    def test_error_count_nonzero(self):
        r = _make_result(success=False, errors=["e1", "e2", "e3"])
        self.assertEqual(r.error_count(), 3)


# ---------------------------------------------------------------------------
# Class 15: TestExecutionResultResponseHelpers (6 tests)
# ---------------------------------------------------------------------------

class TestExecutionResultResponseHelpers(unittest.TestCase):

    def setUp(self):
        self.resp = ProviderResponse(
            content="Generated content here.",
            tokens_used=42,
            provider_name="MockProvider",
            execution_time=0.07,
        )

    def test_response_content_with_response(self):
        r = _make_result(provider_response=self.resp)
        self.assertEqual(r.response_content(), "Generated content here.")

    def test_response_content_without_response(self):
        self.assertEqual(_make_result().response_content(), "")

    def test_response_token_count_with_response(self):
        r = _make_result(provider_response=self.resp)
        self.assertEqual(r.response_token_count(), 42)

    def test_response_token_count_without_response(self):
        self.assertEqual(_make_result().response_token_count(), 0)

    def test_response_provider_name_with_response(self):
        r = _make_result(provider_response=self.resp)
        self.assertEqual(r.response_provider_name(), "MockProvider")

    def test_response_provider_name_without_response(self):
        self.assertEqual(_make_result().response_provider_name(), "")


# ---------------------------------------------------------------------------
# Class 16: TestExecutionResultToDict (5 tests)
# ---------------------------------------------------------------------------

class TestExecutionResultToDict(unittest.TestCase):

    def test_to_dict_returns_dict(self):
        self.assertIsInstance(_make_result().to_dict(), dict)

    def test_to_dict_success_key(self):
        d = _make_result(success=True).to_dict()
        self.assertTrue(d["success"])

    def test_to_dict_counts(self):
        r = _make_result(warnings=["w1"], generated_artifacts=["a"])
        d = r.to_dict()
        self.assertEqual(d["warning_count"], 1)
        self.assertEqual(d["artifact_count"], 1)

    def test_to_dict_has_expected_keys(self):
        d = _make_result().to_dict()
        for key in ["success", "execution_time", "has_response",
                    "artifact_count", "memory_count", "warning_count",
                    "error_count", "warnings", "errors"]:
            self.assertIn(key, d)

    def test_to_dict_warnings_is_list(self):
        r = _make_result(warnings=["a", "b"])
        d = r.to_dict()
        self.assertIsInstance(d["warnings"], list)
        self.assertEqual(len(d["warnings"]), 2)


# ---------------------------------------------------------------------------
# Class 17: TestExecutionResultSummary (4 tests)
# ---------------------------------------------------------------------------

class TestExecutionResultSummary(unittest.TestCase):

    def test_summary_is_string(self):
        self.assertIsInstance(_make_result().summary(), str)

    def test_summary_ok_on_success(self):
        self.assertIn("OK", _make_result(success=True).summary())

    def test_summary_failed_on_failure(self):
        self.assertIn("FAILED", _make_result(success=False).summary())

    def test_summary_non_empty(self):
        self.assertGreater(len(_make_result().summary()), 0)


# ---------------------------------------------------------------------------
# Class 18: TestExecutionRecordBasics (8 tests)
# ---------------------------------------------------------------------------

class TestExecutionRecordBasics(unittest.TestCase):

    def setUp(self):
        self.ctx = _make_context()
        self.res = _make_result()
        self.rec = ExecutionRecord(
            context=self.ctx,
            result=self.res,
            recorded_at=datetime.now(timezone.utc),
        )

    def test_construction(self):
        self.assertIs(self.rec.context, self.ctx)
        self.assertIs(self.rec.result, self.res)

    def test_recorded_at_is_datetime(self):
        self.assertIsInstance(self.rec.recorded_at, datetime)

    def test_to_dict_returns_dict(self):
        self.assertIsInstance(self.rec.to_dict(), dict)

    def test_to_dict_has_recorded_at(self):
        self.assertIn("recorded_at", self.rec.to_dict())

    def test_to_dict_has_context(self):
        self.assertIn("context", self.rec.to_dict())

    def test_to_dict_has_result(self):
        self.assertIn("result", self.rec.to_dict())

    def test_summary_is_string(self):
        self.assertIsInstance(self.rec.summary(), str)

    def test_summary_non_empty(self):
        self.assertGreater(len(self.rec.summary()), 0)


# ---------------------------------------------------------------------------
# Class 19: TestExecutionHistoryBasics (8 tests)
# ---------------------------------------------------------------------------

class TestExecutionHistoryBasics(unittest.TestCase):

    def setUp(self):
        self.history = ExecutionHistory()

    def test_initial_count_zero(self):
        self.assertEqual(self.history.count(), 0)

    def test_all_returns_empty_list(self):
        self.assertEqual(self.history.all(), [])

    def test_last_returns_none_when_empty(self):
        self.assertIsNone(self.history.last())

    def test_record_increases_count(self):
        self.history.record(_make_context(), _make_result())
        self.assertEqual(self.history.count(), 1)

    def test_all_returns_list_after_record(self):
        self.history.record(_make_context(), _make_result())
        self.assertIsInstance(self.history.all(), list)
        self.assertEqual(len(self.history.all()), 1)

    def test_last_returns_record_after_record(self):
        self.history.record(_make_context(), _make_result())
        self.assertIsNotNone(self.history.last())

    def test_record_returns_execution_record(self):
        rec = self.history.record(_make_context(), _make_result())
        self.assertIsInstance(rec, ExecutionRecord)

    def test_all_returns_copy(self):
        self.history.record(_make_context(), _make_result())
        lst1 = self.history.all()
        lst2 = self.history.all()
        self.assertIsNot(lst1, lst2)


# ---------------------------------------------------------------------------
# Class 20: TestExecutionHistorySuccessFailure (8 tests)
# ---------------------------------------------------------------------------

class TestExecutionHistorySuccessFailure(unittest.TestCase):

    def setUp(self):
        self.history = ExecutionHistory()

    def test_successes_zero_initially(self):
        self.assertEqual(self.history.successes(), 0)

    def test_failures_zero_initially(self):
        self.assertEqual(self.history.failures(), 0)

    def test_successes_counts_successful(self):
        self.history.record(_make_context(), _make_result(success=True))
        self.history.record(_make_context(), _make_result(success=True))
        self.assertEqual(self.history.successes(), 2)

    def test_failures_counts_failed(self):
        self.history.record(_make_context(), _make_result(success=False))
        self.assertEqual(self.history.failures(), 1)

    def test_mixed_success_failure(self):
        self.history.record(_make_context(), _make_result(success=True))
        self.history.record(_make_context(), _make_result(success=False))
        self.history.record(_make_context(), _make_result(success=True))
        self.assertEqual(self.history.successes(), 2)
        self.assertEqual(self.history.failures(), 1)

    def test_successes_plus_failures_equals_count(self):
        for s in [True, False, True, False, True]:
            self.history.record(_make_context(), _make_result(success=s))
        total = self.history.count()
        self.assertEqual(self.history.successes() + self.history.failures(), total)

    def test_all_success(self):
        for _ in range(4):
            self.history.record(_make_context(), _make_result(success=True))
        self.assertEqual(self.history.failures(), 0)

    def test_all_failure(self):
        for _ in range(3):
            self.history.record(_make_context(), _make_result(success=False))
        self.assertEqual(self.history.successes(), 0)


# ---------------------------------------------------------------------------
# Class 21: TestExecutionHistoryStatisticsEmpty (5 tests)
# ---------------------------------------------------------------------------

class TestExecutionHistoryStatisticsEmpty(unittest.TestCase):

    def setUp(self):
        self.stats = ExecutionHistory().statistics()

    def test_total_zero(self):
        self.assertEqual(self.stats["total"], 0)

    def test_success_rate_zero(self):
        self.assertEqual(self.stats["success_rate"], 0.0)

    def test_avg_time_zero(self):
        self.assertEqual(self.stats["avg_execution_time"], 0.0)

    def test_roles_empty(self):
        self.assertEqual(self.stats["roles"], [])

    def test_departments_empty(self):
        self.assertEqual(self.stats["departments"], [])


# ---------------------------------------------------------------------------
# Class 22: TestExecutionHistoryStatisticsFull (12 tests)
# ---------------------------------------------------------------------------

class TestExecutionHistoryStatisticsFull(unittest.TestCase):

    def setUp(self):
        self.history = ExecutionHistory()
        self.history.record(
            _make_context(employee_role="Backend Agent", department="Engineering",
                          workflow_stage="Implementation"),
            _make_result(success=True, execution_time=0.1),
        )
        self.history.record(
            _make_context(employee_role="QA Engineer", department="QA",
                          workflow_stage="Testing"),
            _make_result(success=True, execution_time=0.2),
        )
        self.history.record(
            _make_context(employee_role="Backend Agent", department="Engineering",
                          workflow_stage="Implementation"),
            _make_result(success=False, execution_time=0.05),
        )
        self.stats = self.history.statistics()

    def test_total_correct(self):
        self.assertEqual(self.stats["total"], 3)

    def test_successes_correct(self):
        self.assertEqual(self.stats["successes"], 2)

    def test_failures_correct(self):
        self.assertEqual(self.stats["failures"], 1)

    def test_success_rate_correct(self):
        self.assertAlmostEqual(self.stats["success_rate"], 0.667, places=2)

    def test_avg_execution_time_correct(self):
        expected = round((0.1 + 0.2 + 0.05) / 3, 3)
        self.assertAlmostEqual(self.stats["avg_execution_time"], expected, places=3)

    def test_roles_sorted(self):
        self.assertEqual(self.stats["roles"], ["Backend Agent", "QA Engineer"])

    def test_departments_sorted(self):
        self.assertEqual(self.stats["departments"], ["Engineering", "QA"])

    def test_stages_sorted(self):
        self.assertIn("Implementation", self.stats["stages"])
        self.assertIn("Testing", self.stats["stages"])

    def test_total_artifacts_zero(self):
        self.assertEqual(self.stats["total_artifacts"], 0)

    def test_total_memory_entries_zero(self):
        self.assertEqual(self.stats["total_memory_entries"], 0)

    def test_total_warnings_zero(self):
        self.assertEqual(self.stats["total_warnings"], 0)

    def test_roles_unique(self):
        self.assertEqual(len(self.stats["roles"]), len(set(self.stats["roles"])))


# ---------------------------------------------------------------------------
# Class 23: TestAgentExecutorConstruction (8 tests)
# ---------------------------------------------------------------------------

class TestAgentExecutorConstruction(unittest.TestCase):

    def test_basic_construction(self):
        ex = _make_executor()
        self.assertIsNotNone(ex)

    def test_default_prompt_builder_is_created(self):
        ex = _make_executor()
        self.assertIsNotNone(ex._prompt_builder)
        self.assertIsInstance(ex._prompt_builder, PromptBuilder)

    def test_custom_prompt_builder_accepted(self):
        pb = PromptBuilder()
        ex = _make_executor(prompt_builder=pb)
        self.assertIs(ex._prompt_builder, pb)

    def test_without_artifact_engine(self):
        ex = _make_executor()
        self.assertIsNone(ex._artifact_engine)

    def test_without_memory_engine(self):
        ex = _make_executor()
        self.assertIsNone(ex._memory_engine)

    def test_with_artifact_engine(self):
        ae = ArtifactEngine()
        ex = _make_executor(artifact_engine=ae)
        self.assertIs(ex._artifact_engine, ae)

    def test_with_memory_engine(self):
        me = MemoryEngine()
        ex = _make_executor(memory_engine=me)
        self.assertIs(ex._memory_engine, me)

    def test_history_initially_empty(self):
        ex = _make_executor()
        self.assertEqual(len(ex.history()), 0)


# ---------------------------------------------------------------------------
# Class 24: TestAgentExecutorValidate (12 tests)
# ---------------------------------------------------------------------------

class TestAgentExecutorValidate(unittest.TestCase):

    def setUp(self):
        self.executor = _make_executor()

    def test_valid_context_no_errors(self):
        errors = self.executor.validate(_make_context())
        self.assertEqual(errors, [])

    def test_blank_employee_id(self):
        errors = self.executor.validate(_make_context(employee_id=""))
        self.assertTrue(any("employee_id" in e for e in errors))

    def test_blank_employee_role(self):
        errors = self.executor.validate(_make_context(employee_role=""))
        self.assertTrue(any("employee_role" in e for e in errors))

    def test_blank_department(self):
        errors = self.executor.validate(_make_context(department=""))
        self.assertTrue(any("department" in e for e in errors))

    def test_blank_workflow_stage(self):
        errors = self.executor.validate(_make_context(workflow_stage=""))
        self.assertTrue(any("workflow_stage" in e for e in errors))

    def test_blank_task(self):
        errors = self.executor.validate(_make_context(task=None))
        self.assertTrue(any("task" in e for e in errors))

    def test_multiple_errors_returned(self):
        errors = self.executor.validate(_make_context(employee_id="", department=""))
        self.assertGreaterEqual(len(errors), 2)

    def test_validate_returns_list(self):
        result = self.executor.validate(_make_context())
        self.assertIsInstance(result, list)

    def test_validate_never_raises(self):
        ctx = _make_context(employee_id="", employee_role="", department="")
        try:
            self.executor.validate(ctx)
        except Exception:
            self.fail("validate() raised unexpectedly")

    def test_whitespace_employee_id_error(self):
        errors = self.executor.validate(_make_context(employee_id="   "))
        self.assertGreater(len(errors), 0)

    def test_string_task_valid(self):
        errors = self.executor.validate(_make_context(task="Implement login"))
        self.assertEqual(errors, [])

    def test_empty_string_task_error(self):
        errors = self.executor.validate(_make_context(task=""))
        self.assertTrue(any("task" in e for e in errors))


# ---------------------------------------------------------------------------
# Class 25: TestAgentExecutorValidateProviderCheck (5 tests)
# ---------------------------------------------------------------------------

class TestAgentExecutorValidateProviderCheck(unittest.TestCase):

    def test_no_active_provider_error(self):
        registry = ProviderRegistry()  # empty registry
        ex = AgentExecutor(provider_registry=registry)
        errors = ex.validate(_make_context())
        self.assertTrue(any("provider" in e.lower() for e in errors))

    def test_with_active_provider_no_provider_error(self):
        ex = _make_executor()
        errors = ex.validate(_make_context())
        self.assertFalse(any("provider" in e.lower() for e in errors))

    def test_provider_check_independent_of_context_errors(self):
        registry = ProviderRegistry()
        ex = AgentExecutor(provider_registry=registry)
        errors = ex.validate(_make_context(employee_id=""))
        self.assertGreaterEqual(len(errors), 2)

    def test_empty_context_and_no_provider_multiple_errors(self):
        registry = ProviderRegistry()
        ex = AgentExecutor(provider_registry=registry)
        errors = ex.validate(_make_context(employee_id="", department=""))
        self.assertGreaterEqual(len(errors), 3)

    def test_all_valid_with_active_provider(self):
        errors = _make_executor().validate(_make_context())
        self.assertEqual(errors, [])


# ---------------------------------------------------------------------------
# Class 26: TestAgentExecutorExecuteSuccess (12 tests)
# ---------------------------------------------------------------------------

class TestAgentExecutorExecuteSuccess(unittest.TestCase):

    def setUp(self):
        self.executor = _make_executor()
        self.ctx = _make_context()

    def test_execute_returns_execution_result(self):
        result = self.executor.execute(self.ctx)
        self.assertIsInstance(result, ExecutionResult)

    def test_execute_success_true(self):
        result = self.executor.execute(self.ctx)
        self.assertTrue(result.success)

    def test_execute_has_response(self):
        result = self.executor.execute(self.ctx)
        self.assertTrue(result.has_response())

    def test_execute_provider_response_not_none(self):
        result = self.executor.execute(self.ctx)
        self.assertIsNotNone(result.provider_response)

    def test_execute_no_errors_on_success(self):
        result = self.executor.execute(self.ctx)
        self.assertEqual(result.errors, [])

    def test_execute_execution_time_non_negative(self):
        result = self.executor.execute(self.ctx)
        self.assertGreaterEqual(result.execution_time, 0.0)

    def test_execute_records_history(self):
        self.executor.execute(self.ctx)
        self.assertEqual(len(self.executor.history()), 1)

    def test_execute_no_artifacts_without_engine(self):
        result = self.executor.execute(self.ctx)
        self.assertEqual(result.artifact_count(), 0)

    def test_execute_no_memory_without_engine(self):
        result = self.executor.execute(self.ctx)
        self.assertEqual(result.memory_count(), 0)

    def test_execute_response_has_content(self):
        result = self.executor.execute(self.ctx)
        self.assertGreater(len(result.response_content()), 0)

    def test_execute_response_provider_is_mock(self):
        result = self.executor.execute(self.ctx)
        self.assertEqual(result.response_provider_name(), "MockProvider")

    def test_execute_no_warnings_without_optional_engines(self):
        result = self.executor.execute(self.ctx)
        self.assertEqual(result.warnings, [])


# ---------------------------------------------------------------------------
# Class 27: TestAgentExecutorExecuteValidationFailure (10 tests)
# ---------------------------------------------------------------------------

class TestAgentExecutorExecuteValidationFailure(unittest.TestCase):

    def setUp(self):
        self.executor = _make_executor()

    def test_blank_employee_id_fails(self):
        result = self.executor.execute(_make_context(employee_id=""))
        self.assertFalse(result.success)

    def test_blank_role_fails(self):
        result = self.executor.execute(_make_context(employee_role=""))
        self.assertFalse(result.success)

    def test_blank_department_fails(self):
        result = self.executor.execute(_make_context(department=""))
        self.assertFalse(result.success)

    def test_blank_stage_fails(self):
        result = self.executor.execute(_make_context(workflow_stage=""))
        self.assertFalse(result.success)

    def test_null_task_fails(self):
        result = self.executor.execute(_make_context(task=None))
        self.assertFalse(result.success)

    def test_failure_result_has_errors(self):
        result = self.executor.execute(_make_context(employee_id=""))
        self.assertGreater(len(result.errors), 0)

    def test_failure_response_is_none(self):
        result = self.executor.execute(_make_context(employee_id=""))
        self.assertIsNone(result.provider_response)

    def test_failure_still_records_history(self):
        self.executor.execute(_make_context(employee_id=""))
        self.assertEqual(len(self.executor.history()), 1)

    def test_failure_result_no_artifacts(self):
        result = self.executor.execute(_make_context(task=None))
        self.assertEqual(result.artifact_count(), 0)

    def test_no_active_provider_fails(self):
        ex = AgentExecutor(provider_registry=ProviderRegistry())
        result = ex.execute(_make_context())
        self.assertFalse(result.success)


# ---------------------------------------------------------------------------
# Class 28: TestAgentExecutorWithStringTask (5 tests)
# ---------------------------------------------------------------------------

class TestAgentExecutorWithStringTask(unittest.TestCase):

    def setUp(self):
        self.executor = _make_executor()

    def test_string_task_succeeds(self):
        ctx = _make_context(task="Implement the authentication API with JWT.")
        result = self.executor.execute(ctx)
        self.assertTrue(result.success)

    def test_string_task_has_response(self):
        ctx = _make_context(task="Implement the authentication API with JWT.")
        result = self.executor.execute(ctx)
        self.assertIsNotNone(result.provider_response)

    def test_string_task_response_content_non_empty(self):
        ctx = _make_context(task="Implement the authentication API with JWT.")
        result = self.executor.execute(ctx)
        self.assertGreater(len(result.response_content()), 0)

    def test_short_string_task_succeeds(self):
        ctx = _make_context(task="Write unit tests.")
        result = self.executor.execute(ctx)
        self.assertTrue(result.success)

    def test_empty_string_task_fails(self):
        ctx = _make_context(task="")
        result = self.executor.execute(ctx)
        self.assertFalse(result.success)


# ---------------------------------------------------------------------------
# Class 29: TestAgentExecutorWithDictProject (5 tests)
# ---------------------------------------------------------------------------

class TestAgentExecutorWithDictProject(unittest.TestCase):

    def setUp(self):
        self.executor = _make_executor()

    def test_dict_project_succeeds(self):
        ctx = _make_context(project={"id": "p1", "title": "API Project",
                                     "description": "REST API service"})
        result = self.executor.execute(ctx)
        self.assertTrue(result.success)

    def test_dict_project_has_response(self):
        ctx = _make_context(project={"id": "p1", "title": "API Project",
                                     "description": "REST API service"})
        result = self.executor.execute(ctx)
        self.assertIsNotNone(result.provider_response)

    def test_no_project_succeeds_with_fallback(self):
        ctx = _make_context(project=None)
        result = self.executor.execute(ctx)
        self.assertTrue(result.success)

    def test_project_none_no_project_id_for_artifacts(self):
        ae = ArtifactEngine()
        ex = _make_executor(artifact_engine=ae)
        ctx = _make_context(project=None)
        result = ex.execute(ctx)
        self.assertTrue(result.success)
        self.assertEqual(result.artifact_count(), 0)
        self.assertTrue(result.has_warnings())

    def test_dict_project_no_id_skips_artifact(self):
        ae = ArtifactEngine()
        ex = _make_executor(artifact_engine=ae)
        ctx = _make_context(project={"title": "No ID Project"})
        result = ex.execute(ctx)
        self.assertEqual(result.artifact_count(), 0)


# ---------------------------------------------------------------------------
# Class 30: TestAgentExecutorWithArtifactEngine (10 tests)
# ---------------------------------------------------------------------------

class TestAgentExecutorWithArtifactEngine(unittest.TestCase):

    def setUp(self):
        self.ae = ArtifactEngine()
        self.executor = _make_executor(artifact_engine=self.ae)
        self.ctx = _make_context()  # has project_id="proj-001"

    def test_artifact_generated(self):
        result = self.executor.execute(self.ctx)
        self.assertTrue(result.has_artifacts())

    def test_artifact_count_one(self):
        result = self.executor.execute(self.ctx)
        self.assertEqual(result.artifact_count(), 1)

    def test_artifact_in_result_list(self):
        result = self.executor.execute(self.ctx)
        self.assertEqual(len(result.generated_artifacts), 1)

    def test_execution_still_successful(self):
        result = self.executor.execute(self.ctx)
        self.assertTrue(result.success)

    def test_no_errors_with_artifact_engine(self):
        result = self.executor.execute(self.ctx)
        self.assertEqual(result.errors, [])

    def test_artifact_no_warning_on_success(self):
        result = self.executor.execute(self.ctx)
        self.assertFalse(any("Artifact" in w for w in result.warnings))

    def test_artifact_engine_warning_when_no_project_id(self):
        ctx = _make_context(project=None)
        result = self.executor.execute(ctx)
        self.assertTrue(any("project_id" in w for w in result.warnings))

    def test_artifact_not_generated_when_no_project_id(self):
        ctx = _make_context(project=None)
        result = self.executor.execute(ctx)
        self.assertEqual(result.artifact_count(), 0)

    def test_multiple_executions_separate_artifacts(self):
        r1 = self.executor.execute(self.ctx)
        r2 = self.executor.execute(self.ctx)
        self.assertEqual(r1.artifact_count(), 1)
        self.assertEqual(r2.artifact_count(), 1)

    def test_artifact_engine_failure_not_fatal(self):
        class FailingEngine:
            def generate_task_report(self, pid):
                raise RuntimeError("Engine crashed")
        ex = _make_executor(artifact_engine=FailingEngine())
        result = ex.execute(self.ctx)
        self.assertTrue(result.success)
        self.assertTrue(result.has_warnings())
        self.assertEqual(result.artifact_count(), 0)


# ---------------------------------------------------------------------------
# Class 31: TestAgentExecutorArtifactNoProjectId (5 tests)
# ---------------------------------------------------------------------------

class TestAgentExecutorArtifactNoProjectId(unittest.TestCase):

    def setUp(self):
        self.executor = _make_executor(artifact_engine=ArtifactEngine())

    def test_no_project_id_gives_warning(self):
        ctx = _make_context(project=None)
        result = self.executor.execute(ctx)
        self.assertTrue(result.has_warnings())

    def test_no_project_id_warning_message(self):
        ctx = _make_context(project=None)
        result = self.executor.execute(ctx)
        self.assertTrue(any("project_id" in w for w in result.warnings))

    def test_success_despite_no_project_id(self):
        ctx = _make_context(project=None)
        result = self.executor.execute(ctx)
        self.assertTrue(result.success)

    def test_zero_artifacts_without_project_id(self):
        ctx = _make_context(project=None)
        result = self.executor.execute(ctx)
        self.assertEqual(result.artifact_count(), 0)

    def test_blank_project_id_also_skips(self):
        ctx = _make_context(project=_make_project(pid=""))
        result = self.executor.execute(ctx)
        self.assertEqual(result.artifact_count(), 0)


# ---------------------------------------------------------------------------
# Class 32: TestAgentExecutorWithMemoryEngine (10 tests)
# ---------------------------------------------------------------------------

class TestAgentExecutorWithMemoryEngine(unittest.TestCase):

    def setUp(self):
        self.me = MemoryEngine()
        self.executor = _make_executor(memory_engine=self.me)
        self.ctx = _make_context()

    def test_memory_entry_stored(self):
        result = self.executor.execute(self.ctx)
        self.assertTrue(result.has_memory_entries())

    def test_memory_count_one(self):
        result = self.executor.execute(self.ctx)
        self.assertEqual(result.memory_count(), 1)

    def test_execution_successful_with_memory(self):
        result = self.executor.execute(self.ctx)
        self.assertTrue(result.success)

    def test_no_errors_with_memory_engine(self):
        result = self.executor.execute(self.ctx)
        self.assertEqual(result.errors, [])

    def test_memory_entry_category_is_task(self):
        result = self.executor.execute(self.ctx)
        entry = result.memory_entries[0]
        self.assertEqual(entry.category, MemoryCategory.TASK)

    def test_memory_entry_has_content(self):
        result = self.executor.execute(self.ctx)
        entry = result.memory_entries[0]
        self.assertGreater(len(entry.content), 0)

    def test_memory_entry_scope_project_when_project_id(self):
        result = self.executor.execute(self.ctx)
        entry = result.memory_entries[0]
        self.assertEqual(entry.scope, MemoryScope.PROJECT)

    def test_memory_entry_scope_employee_when_no_project_id(self):
        ctx = _make_context(project=None)
        result = self.executor.execute(ctx)
        self.assertTrue(result.has_memory_entries())
        entry = result.memory_entries[0]
        self.assertEqual(entry.scope, MemoryScope.EMPLOYEE)

    def test_memory_engine_failure_not_fatal(self):
        class FailingMemory:
            def store(self, entry):
                raise RuntimeError("Memory crashed")
        ex = _make_executor(memory_engine=FailingMemory())
        result = ex.execute(self.ctx)
        self.assertTrue(result.success)
        self.assertTrue(result.has_warnings())
        self.assertEqual(result.memory_count(), 0)

    def test_memory_no_warning_on_success(self):
        result = self.executor.execute(self.ctx)
        self.assertFalse(any("Memory" in w for w in result.warnings))


# ---------------------------------------------------------------------------
# Class 33: TestAgentExecutorHistory (8 tests)
# ---------------------------------------------------------------------------

class TestAgentExecutorHistory(unittest.TestCase):

    def setUp(self):
        self.executor = _make_executor()

    def test_history_empty_initially(self):
        self.assertEqual(self.executor.history(), [])

    def test_history_after_execute(self):
        self.executor.execute(_make_context())
        self.assertEqual(len(self.executor.history()), 1)

    def test_history_count_increases(self):
        for _ in range(3):
            self.executor.execute(_make_context())
        self.assertEqual(len(self.executor.history()), 3)

    def test_history_contains_execution_records(self):
        self.executor.execute(_make_context())
        rec = self.executor.history()[0]
        self.assertIsInstance(rec, ExecutionRecord)

    def test_history_contains_result(self):
        self.executor.execute(_make_context())
        rec = self.executor.history()[0]
        self.assertIsInstance(rec.result, ExecutionResult)

    def test_history_failure_recorded(self):
        self.executor.execute(_make_context(employee_id=""))
        rec = self.executor.history()[0]
        self.assertFalse(rec.result.success)

    def test_history_returns_copy(self):
        self.executor.execute(_make_context())
        h1 = self.executor.history()
        h2 = self.executor.history()
        self.assertIsNot(h1, h2)

    def test_history_order_sequential(self):
        self.executor.execute(_make_context(employee_role="Backend Agent"))
        self.executor.execute(_make_context(employee_role="QA Engineer"))
        h = self.executor.history()
        self.assertEqual(h[0].context.employee_role, "Backend Agent")
        self.assertEqual(h[1].context.employee_role, "QA Engineer")


# ---------------------------------------------------------------------------
# Class 34: TestAgentExecutorStatistics (10 tests)
# ---------------------------------------------------------------------------

class TestAgentExecutorStatistics(unittest.TestCase):

    def setUp(self):
        self.executor = _make_executor()

    def test_statistics_returns_dict(self):
        self.assertIsInstance(self.executor.statistics(), dict)

    def test_statistics_total_zero_initially(self):
        self.assertEqual(self.executor.statistics()["total"], 0)

    def test_statistics_total_after_execute(self):
        self.executor.execute(_make_context())
        self.assertEqual(self.executor.statistics()["total"], 1)

    def test_statistics_has_artifact_engine_false(self):
        self.assertFalse(self.executor.statistics()["has_artifact_engine"])

    def test_statistics_has_artifact_engine_true(self):
        ex = _make_executor(artifact_engine=ArtifactEngine())
        self.assertTrue(ex.statistics()["has_artifact_engine"])

    def test_statistics_has_memory_engine_false(self):
        self.assertFalse(self.executor.statistics()["has_memory_engine"])

    def test_statistics_has_memory_engine_true(self):
        ex = _make_executor(memory_engine=MemoryEngine())
        self.assertTrue(ex.statistics()["has_memory_engine"])

    def test_statistics_active_provider(self):
        stats = self.executor.statistics()
        self.assertEqual(stats["active_provider"], "MockProvider")

    def test_statistics_provider_count(self):
        stats = self.executor.statistics()
        self.assertEqual(stats["provider_count"], 1)

    def test_statistics_executor_version(self):
        stats = self.executor.statistics()
        self.assertIn("executor_version", stats)
        self.assertIsInstance(stats["executor_version"], str)


# ---------------------------------------------------------------------------
# Class 35: TestAgentExecutorMultipleExecutions (8 tests)
# ---------------------------------------------------------------------------

class TestAgentExecutorMultipleExecutions(unittest.TestCase):

    def setUp(self):
        self.executor = _make_executor()

    def test_three_executions_three_history(self):
        for _ in range(3):
            self.executor.execute(_make_context())
        self.assertEqual(len(self.executor.history()), 3)

    def test_statistics_counts_all(self):
        for _ in range(5):
            self.executor.execute(_make_context())
        self.assertEqual(self.executor.statistics()["total"], 5)

    def test_success_count_in_stats(self):
        for _ in range(3):
            self.executor.execute(_make_context())
        self.executor.execute(_make_context(employee_id=""))
        stats = self.executor.statistics()
        self.assertEqual(stats["successes"], 3)
        self.assertEqual(stats["failures"], 1)

    def test_different_roles_tracked(self):
        self.executor.execute(_make_context(employee_role="Backend Agent"))
        self.executor.execute(_make_context(employee_role="QA Engineer"))
        stats = self.executor.statistics()
        self.assertIn("Backend Agent", stats["roles"])
        self.assertIn("QA Engineer", stats["roles"])

    def test_different_departments_tracked(self):
        self.executor.execute(_make_context(department="Engineering"))
        self.executor.execute(_make_context(department="QA"))
        stats = self.executor.statistics()
        self.assertIn("Engineering", stats["departments"])
        self.assertIn("QA", stats["departments"])

    def test_history_preserves_all_results(self):
        ctx1 = _make_context(employee_role="Backend Agent")
        ctx2 = _make_context(employee_role="QA Engineer")
        self.executor.execute(ctx1)
        self.executor.execute(ctx2)
        roles = [r.context.employee_role for r in self.executor.history()]
        self.assertIn("Backend Agent", roles)
        self.assertIn("QA Engineer", roles)

    def test_mixed_success_failure_tracked(self):
        self.executor.execute(_make_context())
        self.executor.execute(_make_context(employee_id=""))
        self.executor.execute(_make_context())
        h = self.executor.history()
        self.assertTrue(h[0].result.success)
        self.assertFalse(h[1].result.success)
        self.assertTrue(h[2].result.success)

    def test_avg_execution_time_in_stats(self):
        for _ in range(3):
            self.executor.execute(_make_context())
        stats = self.executor.statistics()
        self.assertGreaterEqual(stats["avg_execution_time"], 0.0)


# ---------------------------------------------------------------------------
# Class 36: TestAgentExecutorDeterminism (5 tests)
# ---------------------------------------------------------------------------

class TestAgentExecutorDeterminism(unittest.TestCase):

    def setUp(self):
        self.executor = _make_executor()

    def test_same_task_same_content(self):
        ctx = _make_context(task="Implement authentication with JWT tokens.")
        r1 = self.executor.execute(ctx)
        r2 = self.executor.execute(ctx)
        self.assertEqual(r1.response_content(), r2.response_content())

    def test_same_context_same_provider_name(self):
        ctx = _make_context()
        r1 = self.executor.execute(ctx)
        r2 = self.executor.execute(ctx)
        self.assertEqual(r1.response_provider_name(), r2.response_provider_name())

    def test_same_context_same_token_count(self):
        ctx = _make_context()
        r1 = self.executor.execute(ctx)
        r2 = self.executor.execute(ctx)
        self.assertEqual(r1.response_token_count(), r2.response_token_count())

    def test_different_task_different_content(self):
        ctx_auth = _make_context(task="Implement authentication with JWT tokens.")
        ctx_test = _make_context(task="Write unit tests for the login module.")
        r1 = self.executor.execute(ctx_auth)
        r2 = self.executor.execute(ctx_test)
        self.assertNotEqual(r1.response_content(), r2.response_content())

    def test_different_role_same_task_may_differ(self):
        ctx1 = _make_context(employee_role="Backend Agent",
                              task="Implement authentication with JWT tokens.")
        ctx2 = _make_context(employee_role="QA Engineer",
                              task="Implement authentication with JWT tokens.")
        r1 = self.executor.execute(ctx1)
        r2 = self.executor.execute(ctx2)
        # Results may or may not differ; both should succeed
        self.assertTrue(r1.success)
        self.assertTrue(r2.success)


# ---------------------------------------------------------------------------
# Class 37: TestAgentExecutorNoOptionalEngines (5 tests)
# ---------------------------------------------------------------------------

class TestAgentExecutorNoOptionalEngines(unittest.TestCase):

    def setUp(self):
        self.executor = AgentExecutor(provider_registry=_make_registry())

    def test_execute_succeeds_without_optional_engines(self):
        result = self.executor.execute(_make_context())
        self.assertTrue(result.success)

    def test_no_artifacts_without_artifact_engine(self):
        result = self.executor.execute(_make_context())
        self.assertEqual(result.artifact_count(), 0)

    def test_no_memory_entries_without_memory_engine(self):
        result = self.executor.execute(_make_context())
        self.assertEqual(result.memory_count(), 0)

    def test_no_warnings_without_optional_engines(self):
        result = self.executor.execute(_make_context())
        self.assertEqual(result.warnings, [])

    def test_has_response_without_optional_engines(self):
        result = self.executor.execute(_make_context())
        self.assertTrue(result.has_response())


# ---------------------------------------------------------------------------
# Class 38: TestAgentExecutorPromptBuilderIntegration (8 tests)
# ---------------------------------------------------------------------------

class TestAgentExecutorPromptBuilderIntegration(unittest.TestCase):

    def setUp(self):
        self.builder = PromptBuilder()
        self.executor = _make_executor(prompt_builder=self.builder)

    def test_builder_build_count_increments(self):
        self.executor.execute(_make_context())
        self.assertEqual(self.builder.total_builds(), 1)

    def test_builder_build_count_multi(self):
        for _ in range(4):
            self.executor.execute(_make_context())
        self.assertEqual(self.builder.total_builds(), 4)

    def test_builder_history_populated(self):
        self.executor.execute(_make_context())
        self.assertEqual(len(self.builder.history()), 1)

    def test_custom_builder_shared_state(self):
        ctx1 = _make_context(employee_role="Backend Agent")
        ctx2 = _make_context(employee_role="QA Engineer")
        self.executor.execute(ctx1)
        self.executor.execute(ctx2)
        roles = [r.metadata["employee_role"] for r in self.builder.history()]
        self.assertIn("Backend Agent", roles)
        self.assertIn("QA Engineer", roles)

    def test_default_builder_created_when_none(self):
        ex = AgentExecutor(provider_registry=_make_registry())
        ex.execute(_make_context())
        self.assertIsInstance(ex._prompt_builder, PromptBuilder)
        self.assertEqual(ex._prompt_builder.total_builds(), 1)

    def test_builder_last_result_accessible(self):
        self.executor.execute(_make_context())
        last = self.builder.last_result()
        self.assertIsNotNone(last)
        self.assertGreater(len(last.system_prompt), 0)

    def test_builder_result_has_valid_system_prompt(self):
        self.executor.execute(_make_context())
        last = self.builder.last_result()
        self.assertGreater(len(last.system_prompt.strip()), 0)

    def test_builder_result_has_valid_user_prompt(self):
        self.executor.execute(_make_context())
        last = self.builder.last_result()
        self.assertGreater(len(last.user_prompt.strip()), 0)


# ---------------------------------------------------------------------------
# Class 39: TestAgentExecutorAllEngines (8 tests)
# ---------------------------------------------------------------------------

class TestAgentExecutorAllEngines(unittest.TestCase):

    def setUp(self):
        self.ae = ArtifactEngine()
        self.me = MemoryEngine()
        self.executor = _make_executor(artifact_engine=self.ae, memory_engine=self.me)
        self.ctx = _make_context()

    def test_execute_succeeds(self):
        result = self.executor.execute(self.ctx)
        self.assertTrue(result.success)

    def test_artifact_generated(self):
        result = self.executor.execute(self.ctx)
        self.assertTrue(result.has_artifacts())

    def test_memory_stored(self):
        result = self.executor.execute(self.ctx)
        self.assertTrue(result.has_memory_entries())

    def test_has_response(self):
        result = self.executor.execute(self.ctx)
        self.assertTrue(result.has_response())

    def test_no_errors(self):
        result = self.executor.execute(self.ctx)
        self.assertEqual(result.errors, [])

    def test_statistics_both_engines_true(self):
        stats = self.executor.statistics()
        self.assertTrue(stats["has_artifact_engine"])
        self.assertTrue(stats["has_memory_engine"])

    def test_both_engines_tracked_in_stats(self):
        self.executor.execute(self.ctx)
        stats = self.executor.statistics()
        self.assertEqual(stats["total_artifacts"], 1)
        self.assertEqual(stats["total_memory_entries"], 1)

    def test_history_has_both_counts(self):
        self.executor.execute(self.ctx)
        rec = self.executor.history()[0]
        self.assertEqual(rec.result.artifact_count(), 1)
        self.assertEqual(rec.result.memory_count(), 1)


# ---------------------------------------------------------------------------
# Class 40: TestAgentExecutorExceptionClasses (5 tests)
# ---------------------------------------------------------------------------

class TestAgentExecutorExceptionClasses(unittest.TestCase):

    def test_execution_error_is_exception(self):
        self.assertTrue(issubclass(ExecutionError, Exception))

    def test_agent_invalid_context_error_is_execution_error(self):
        self.assertTrue(issubclass(AgentInvalidContextError, ExecutionError))

    def test_missing_provider_error_is_execution_error(self):
        self.assertTrue(issubclass(MissingProviderError, ExecutionError))

    def test_execution_context_error_is_exception(self):
        self.assertTrue(issubclass(ExecutionContextError, Exception))

    def test_errors_can_be_raised(self):
        with self.assertRaises(ExecutionError):
            raise AgentInvalidContextError("test")


# ---------------------------------------------------------------------------
# Class 41: TestExecutionContextTaskEdgeCases (6 tests)
# ---------------------------------------------------------------------------

class TestExecutionContextTaskEdgeCases(unittest.TestCase):

    def test_task_with_only_whitespace_description(self):
        t = FakeTask(id="t1", title="Title", description="   ")
        ctx = _make_context(task=t)
        # Whitespace-only description falls through to title
        self.assertEqual(ctx.task_description(), "Title")

    def test_task_with_whitespace_title_and_description(self):
        t = FakeTask(id="t1", title="   ", description="   ")
        ctx = _make_context(task=t)
        self.assertEqual(ctx.task_description(), "")

    def test_task_description_none_attribute_uses_title(self):
        class TaskWithNoneDesc:
            id = "t1"
            title = "My Title"
            description = None
        ctx = _make_context(task=TaskWithNoneDesc())
        self.assertEqual(ctx.task_description(), "My Title")

    def test_project_without_id_attribute(self):
        class ProjectNoId:
            title = "No ID Project"
            description = "Some desc"
        ctx = _make_context(project=ProjectNoId())
        self.assertIsNone(ctx.project_id())

    def test_project_with_whitespace_title(self):
        p = FakeProject(id="p1", title="   ", description="desc")
        ctx = _make_context(project=p)
        self.assertEqual(ctx.project_name(), "")

    def test_task_dict_missing_both_keys_empty(self):
        ctx = _make_context(task={"id": "t1"})
        self.assertEqual(ctx.task_description(), "")


# ---------------------------------------------------------------------------
# Class 42: TestEndToEnd (10 tests)
# ---------------------------------------------------------------------------

class TestEndToEnd(unittest.TestCase):

    def test_auth_task_pipeline(self):
        ex = AgentExecutor(
            provider_registry=_make_registry(),
            prompt_builder=PromptBuilder(),
            artifact_engine=ArtifactEngine(),
            memory_engine=MemoryEngine(),
        )
        ctx = ExecutionContext(
            employee_id="agent-001",
            employee_role="Backend Agent",
            department="Engineering",
            project=FakeProject("proj-001", "Auth Service", "JWT auth service"),
            workflow_stage="Implementation",
            task=FakeTask("task-001", "Auth API", "Implement JWT authentication API"),
            constraints=["RS256 JWT", "bcrypt cost=12"],
        )
        result = ex.execute(ctx)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.provider_response)
        self.assertEqual(result.artifact_count(), 1)
        self.assertEqual(result.memory_count(), 1)
        self.assertEqual(result.errors, [])

    def test_test_task_pipeline(self):
        ex = _make_executor()
        ctx = _make_context(
            task="Write unit tests for the authentication module.",
            workflow_stage="Testing",
        )
        result = ex.execute(ctx)
        self.assertTrue(result.success)
        self.assertIn("test", result.response_content().lower())

    def test_deploy_task_pipeline(self):
        ex = _make_executor()
        ctx = _make_context(
            task="Deploy the authentication service to production.",
            workflow_stage="Deployment",
        )
        result = ex.execute(ctx)
        self.assertTrue(result.success)

    def test_history_accumulates_across_pipeline(self):
        ex = AgentExecutor(
            provider_registry=_make_registry(),
            artifact_engine=ArtifactEngine(),
            memory_engine=MemoryEngine(),
        )
        for i in range(3):
            ex.execute(_make_context(
                employee_id=f"agent-{i:03d}",
                task=f"Implement feature {i} with authentication.",
            ))
        self.assertEqual(len(ex.history()), 3)

    def test_statistics_reflect_all_executions(self):
        ex = _make_executor()
        ex.execute(_make_context(employee_role="Backend Agent", department="Engineering"))
        ex.execute(_make_context(employee_role="QA Engineer", department="QA"))
        ex.execute(_make_context(employee_id=""))  # failure
        stats = ex.statistics()
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["successes"], 2)
        self.assertEqual(stats["failures"], 1)

    def test_response_content_not_empty(self):
        ex = _make_executor()
        result = ex.execute(_make_context())
        self.assertGreater(len(result.response_content()), 10)

    def test_multiple_agents_same_registry(self):
        registry = _make_registry()
        ex1 = AgentExecutor(provider_registry=registry)
        ex2 = AgentExecutor(provider_registry=registry)
        r1 = ex1.execute(_make_context(employee_role="Backend Agent"))
        r2 = ex2.execute(_make_context(employee_role="QA Engineer"))
        self.assertTrue(r1.success)
        self.assertTrue(r2.success)
        self.assertEqual(len(ex1.history()), 1)
        self.assertEqual(len(ex2.history()), 1)

    def test_full_pipeline_with_constraints(self):
        ex = _make_executor(memory_engine=MemoryEngine())
        ctx = _make_context(
            constraints=["No external libs", "Python 3.12+", "FastAPI only"],
        )
        result = ex.execute(ctx)
        self.assertTrue(result.success)
        self.assertEqual(result.memory_count(), 1)
        entry = result.memory_entries[0]
        self.assertGreater(len(entry.content), 0)

    def test_full_pipeline_memory_entry_author_is_employee_id(self):
        ex = _make_executor(memory_engine=MemoryEngine())
        result = ex.execute(_make_context(employee_id="agent-007"))
        entry = result.memory_entries[0]
        self.assertEqual(entry.author, "agent-007")

    def test_execution_time_is_float(self):
        ex = _make_executor()
        result = ex.execute(_make_context())
        self.assertIsInstance(result.execution_time, float)


if __name__ == "__main__":
    unittest.main()
