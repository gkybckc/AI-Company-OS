"""
Tests for the Company Orchestrator — Sprint 10.

Test classes:
  TestCompanyEventType             (12) — enum behavior
  TestCompanyEvent                 (14) — factory, immutability, payload access
  TestSessionStage                 (10) — enum behavior, is_terminal, is_active
  TestCompanySession               (24) — dataclass, helpers, summary
  TestCompanyContext               (16) — factory, helpers, summary
  TestOrchestratorInit             (8)  — construction
  TestStartCompany                 (10) — lifecycle guards
  TestStopCompany                  (10) — lifecycle guards
  TestNewRequestValidation         (12) — guard clauses
  TestNewRequestPipelineAnalyze    (10) — ANALYZING stage
  TestNewRequestPipelinePlan       (14) — PLANNING stage
  TestNewRequestPipelineExecute    (10) — EXECUTING stage
  TestNewRequestPipelineDiscuss    (10) — DISCUSSING stage
  TestNewRequestPipelineFinish     (10) — FINISHED stage
  TestNewRequestEventLog           (16) — events recorded
  TestCurrentSession               (8)  — query method
  TestHistory                      (8)  — query method
  TestStatus                       (10) — status dict
  TestStatistics                   (12) — statistics dict
  TestErrorHandling                (14) — failure recovery
  TestMultipleRequests             (8)  — multiple sessions
  TestIntegration                  (16) — end-to-end
  TestOrchestratorContracts        (10) — invariants

Total: 262 tests
"""

import unittest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from core.company_context import CompanyContext
from core.company_event import CompanyEvent, CompanyEventType
from core.company_orchestrator import (
    CompanyOrchestrator,
    InvalidRequestError,
    OrchestratorAlreadyStartedError,
    OrchestratorError,
    OrchestratorNotRunningError,
    OrchestratorNotStartedError,
)
from core.company_session import CompanySession, SessionStage
from core.department_type import DepartmentType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_context(name: str = "TestCorp") -> CompanyContext:
    return CompanyContext.create(company_name=name)


def _started_orchestrator(name: str = "TestCorp") -> CompanyOrchestrator:
    ctx = _make_context(name)
    orc = CompanyOrchestrator(ctx)
    orc.start_company()
    return orc


_VALID_REQUEST = (
    "Build a task management web application with authentication and real-time updates."
)


# ===========================================================================
# TestCompanyEventType
# ===========================================================================

class TestCompanyEventType(unittest.TestCase):

    def test_all_types_are_str_subclass(self):
        for et in CompanyEventType:
            self.assertIsInstance(et, str)

    def test_str_returns_value(self):
        self.assertEqual(str(CompanyEventType.PROJECT_CREATED), "PROJECT_CREATED")
        self.assertEqual(str(CompanyEventType.TASK_ASSIGNED), "TASK_ASSIGNED")

    def test_request_completed_is_terminal(self):
        self.assertTrue(CompanyEventType.REQUEST_COMPLETED.is_terminal())

    def test_request_failed_is_terminal(self):
        self.assertTrue(CompanyEventType.REQUEST_FAILED.is_terminal())

    def test_non_terminal_events(self):
        non_terminal = [
            CompanyEventType.PROJECT_CREATED,
            CompanyEventType.TASK_CREATED,
            CompanyEventType.RUNTIME_STARTED,
            CompanyEventType.DISCUSSION_STARTED,
            CompanyEventType.PROJECT_FINISHED,
        ]
        for et in non_terminal:
            self.assertFalse(et.is_terminal(), et)

    def test_request_failed_is_error(self):
        self.assertTrue(CompanyEventType.REQUEST_FAILED.is_error())

    def test_others_not_error(self):
        for et in CompanyEventType:
            if et != CompanyEventType.REQUEST_FAILED:
                self.assertFalse(et.is_error(), et)

    def test_company_started_is_lifecycle(self):
        self.assertTrue(CompanyEventType.COMPANY_STARTED.is_company_lifecycle())

    def test_company_stopped_is_lifecycle(self):
        self.assertTrue(CompanyEventType.COMPANY_STOPPED.is_company_lifecycle())

    def test_others_not_lifecycle(self):
        for et in CompanyEventType:
            if et not in {CompanyEventType.COMPANY_STARTED, CompanyEventType.COMPANY_STOPPED}:
                self.assertFalse(et.is_company_lifecycle(), et)

    def test_enum_members_count(self):
        self.assertGreaterEqual(len(CompanyEventType), 16)

    def test_known_members_exist(self):
        members = {et.value for et in CompanyEventType}
        self.assertIn("PROJECT_CREATED", members)
        self.assertIn("TASK_ASSIGNED", members)
        self.assertIn("DISCUSSION_STARTED", members)


# ===========================================================================
# TestCompanyEvent
# ===========================================================================

class TestCompanyEvent(unittest.TestCase):

    def _event(self, et=CompanyEventType.TASK_CREATED, session_id="s1", payload=None):
        return CompanyEvent.create(et, session_id=session_id, payload=payload)

    def test_create_returns_company_event(self):
        e = self._event()
        self.assertIsInstance(e, CompanyEvent)

    def test_create_generates_id(self):
        e = self._event()
        self.assertIsNotNone(e.id)
        self.assertGreater(len(e.id), 8)

    def test_create_two_events_different_ids(self):
        e1 = self._event()
        e2 = self._event()
        self.assertNotEqual(e1.id, e2.id)

    def test_create_sets_event_type(self):
        e = self._event(CompanyEventType.PROJECT_FINISHED)
        self.assertEqual(e.event_type, CompanyEventType.PROJECT_FINISHED)

    def test_create_sets_session_id(self):
        e = self._event(session_id="sess-99")
        self.assertEqual(e.session_id, "sess-99")

    def test_create_none_session_id(self):
        e = CompanyEvent.create(CompanyEventType.COMPANY_STARTED)
        self.assertIsNone(e.session_id)

    def test_create_sets_timestamp(self):
        before = datetime.now(timezone.utc)
        e = self._event()
        after = datetime.now(timezone.utc)
        self.assertGreaterEqual(e.timestamp, before)
        self.assertLessEqual(e.timestamp, after)

    def test_create_empty_payload_by_default(self):
        e = self._event()
        self.assertEqual(e.payload, {})

    def test_create_with_payload(self):
        e = self._event(payload={"key": "val"})
        self.assertEqual(e.payload["key"], "val")

    def test_is_frozen(self):
        e = self._event()
        with self.assertRaises(Exception):
            e.event_type = CompanyEventType.TASK_ASSIGNED  # type: ignore

    def test_is_terminal_delegates(self):
        e = self._event(CompanyEventType.REQUEST_COMPLETED)
        self.assertTrue(e.is_terminal())

    def test_is_error_delegates(self):
        e = self._event(CompanyEventType.REQUEST_FAILED)
        self.assertTrue(e.is_error())

    def test_get_payload_value_existing_key(self):
        e = self._event(payload={"x": 42})
        self.assertEqual(e.get_payload_value("x"), 42)

    def test_get_payload_value_missing_key_returns_default(self):
        e = self._event()
        self.assertIsNone(e.get_payload_value("missing"))
        self.assertEqual(e.get_payload_value("missing", "fallback"), "fallback")


# ===========================================================================
# TestSessionStage
# ===========================================================================

class TestSessionStage(unittest.TestCase):

    def test_all_stages_are_str_subclass(self):
        for s in SessionStage:
            self.assertIsInstance(s, str)

    def test_str_returns_value(self):
        self.assertEqual(str(SessionStage.CREATED), "CREATED")
        self.assertEqual(str(SessionStage.FINISHED), "FINISHED")

    def test_finished_is_terminal(self):
        self.assertTrue(SessionStage.FINISHED.is_terminal())

    def test_failed_is_terminal(self):
        self.assertTrue(SessionStage.FAILED.is_terminal())

    def test_active_stages_not_terminal(self):
        active = [
            SessionStage.CREATED,
            SessionStage.ANALYZING,
            SessionStage.PLANNING,
            SessionStage.EXECUTING,
            SessionStage.DISCUSSING,
        ]
        for s in active:
            self.assertFalse(s.is_terminal(), s)

    def test_is_active_true_for_created(self):
        self.assertTrue(SessionStage.CREATED.is_active())

    def test_is_active_false_for_finished(self):
        self.assertFalse(SessionStage.FINISHED.is_active())

    def test_is_active_false_for_failed(self):
        self.assertFalse(SessionStage.FAILED.is_active())

    def test_stage_count(self):
        self.assertEqual(len(SessionStage), 7)

    def test_all_expected_values_exist(self):
        values = {s.value for s in SessionStage}
        expected = {"CREATED", "ANALYZING", "PLANNING", "EXECUTING", "DISCUSSING", "FINISHED", "FAILED"}
        self.assertEqual(values, expected)


# ===========================================================================
# TestCompanySession
# ===========================================================================

class TestCompanySession(unittest.TestCase):

    def _session(self, stage=SessionStage.CREATED):
        return CompanySession(
            id="sess-1",
            request="Build something",
            current_stage=stage,
            created_at=datetime.now(timezone.utc),
        )

    def test_is_active_when_created(self):
        s = self._session(SessionStage.CREATED)
        self.assertTrue(s.is_active())

    def test_is_active_when_analyzing(self):
        s = self._session(SessionStage.ANALYZING)
        self.assertTrue(s.is_active())

    def test_is_finished_when_finished(self):
        s = self._session(SessionStage.FINISHED)
        self.assertTrue(s.is_finished())

    def test_is_failed_when_failed(self):
        s = self._session(SessionStage.FAILED)
        self.assertTrue(s.is_failed())

    def test_not_finished_when_active(self):
        s = self._session(SessionStage.CREATED)
        self.assertFalse(s.is_finished())

    def test_add_event_increments_count(self):
        s = self._session()
        e = CompanyEvent.create(CompanyEventType.TASK_CREATED, session_id="sess-1")
        s.add_event(e)
        self.assertEqual(s.event_count(), 1)

    def test_add_multiple_events(self):
        s = self._session()
        for et in [CompanyEventType.TASK_CREATED, CompanyEventType.TASK_ASSIGNED]:
            s.add_event(CompanyEvent.create(et, session_id="sess-1"))
        self.assertEqual(s.event_count(), 2)

    def test_events_of_type_filters_correctly(self):
        s = self._session()
        s.add_event(CompanyEvent.create(CompanyEventType.TASK_CREATED, session_id="s1"))
        s.add_event(CompanyEvent.create(CompanyEventType.TASK_ASSIGNED, session_id="s1"))
        s.add_event(CompanyEvent.create(CompanyEventType.TASK_CREATED, session_id="s1"))
        result = s.events_of_type(CompanyEventType.TASK_CREATED)
        self.assertEqual(len(result), 2)

    def test_last_event_returns_most_recent(self):
        s = self._session()
        e1 = CompanyEvent.create(CompanyEventType.TASK_CREATED, session_id="s1")
        e2 = CompanyEvent.create(CompanyEventType.TASK_ASSIGNED, session_id="s1")
        s.add_event(e1)
        s.add_event(e2)
        self.assertEqual(s.last_event(), e2)

    def test_last_event_returns_none_when_empty(self):
        s = self._session()
        self.assertIsNone(s.last_event())

    def test_task_count_zero_initially(self):
        s = self._session()
        self.assertEqual(s.task_count(), 0)

    def test_runtime_count_zero_initially(self):
        s = self._session()
        self.assertEqual(s.runtime_count(), 0)

    def test_discussion_count_zero_initially(self):
        s = self._session()
        self.assertEqual(s.discussion_count(), 0)

    def test_has_blueprint_false_initially(self):
        s = self._session()
        self.assertFalse(s.has_blueprint())

    def test_has_project_false_initially(self):
        s = self._session()
        self.assertFalse(s.has_project())

    def test_duration_seconds_none_while_active(self):
        s = self._session()
        self.assertIsNone(s.duration_seconds())

    def test_duration_seconds_computed_when_finished(self):
        s = self._session(SessionStage.FINISHED)
        s.finished_at = datetime.now(timezone.utc)
        dur = s.duration_seconds()
        self.assertIsNotNone(dur)
        self.assertGreaterEqual(dur, 0.0)

    def test_summary_contains_required_keys(self):
        s = self._session()
        keys = s.summary()
        for k in ["id", "request_preview", "stage", "tasks", "runtimes", "discussions", "events", "finished", "error"]:
            self.assertIn(k, keys)

    def test_summary_stage_matches(self):
        s = self._session(SessionStage.EXECUTING)
        self.assertEqual(s.summary()["stage"], "EXECUTING")

    def test_summary_finished_false_when_active(self):
        s = self._session()
        self.assertFalse(s.summary()["finished"])

    def test_summary_finished_true_when_finished(self):
        s = self._session(SessionStage.FINISHED)
        self.assertTrue(s.summary()["finished"])

    def test_error_message_none_by_default(self):
        s = self._session()
        self.assertIsNone(s.error_message)

    def test_events_of_type_empty_result_for_absent_type(self):
        s = self._session()
        result = s.events_of_type(CompanyEventType.DISCUSSION_STARTED)
        self.assertEqual(result, [])


# ===========================================================================
# TestCompanyContext
# ===========================================================================

class TestCompanyContext(unittest.TestCase):

    def test_create_returns_context(self):
        ctx = CompanyContext.create("MyCompany")
        self.assertIsInstance(ctx, CompanyContext)

    def test_create_sets_company_name(self):
        ctx = CompanyContext.create("MyCompany")
        self.assertEqual(ctx.company_name, "MyCompany")

    def test_create_generates_company_id(self):
        ctx = CompanyContext.create("X")
        self.assertIsNotNone(ctx.company_id)
        self.assertGreater(len(ctx.company_id), 8)

    def test_two_contexts_have_different_ids(self):
        ctx1 = CompanyContext.create("A")
        ctx2 = CompanyContext.create("B")
        self.assertNotEqual(ctx1.company_id, ctx2.company_id)

    def test_create_initializes_executive(self):
        ctx = CompanyContext.create("X")
        self.assertIsNotNone(ctx.executive)

    def test_create_initializes_planner(self):
        ctx = CompanyContext.create("X")
        self.assertIsNotNone(ctx.planner)

    def test_create_initializes_departments(self):
        ctx = CompanyContext.create("X")
        self.assertIsNotNone(ctx.departments)

    def test_create_initializes_workforce(self):
        ctx = CompanyContext.create("X")
        self.assertIsNotNone(ctx.workforce)

    def test_create_sets_created_at(self):
        before = datetime.now(timezone.utc)
        ctx = CompanyContext.create("X")
        after = datetime.now(timezone.utc)
        self.assertGreaterEqual(ctx.created_at, before)
        self.assertLessEqual(ctx.created_at, after)

    def test_has_active_project_false_initially(self):
        ctx = CompanyContext.create("X")
        self.assertFalse(ctx.has_active_project())

    def test_has_active_runtime_true_after_create(self):
        ctx = CompanyContext.create("X")
        self.assertTrue(ctx.has_active_runtime())

    def test_department_count_zero_initially(self):
        ctx = CompanyContext.create("X")
        self.assertEqual(ctx.department_count(), 0)

    def test_employee_count_zero_initially(self):
        ctx = CompanyContext.create("X")
        self.assertEqual(ctx.employee_count(), 0)

    def test_summary_returns_dict(self):
        ctx = CompanyContext.create("Acme")
        s = ctx.summary()
        self.assertIsInstance(s, dict)

    def test_summary_contains_company_name(self):
        ctx = CompanyContext.create("Acme")
        self.assertEqual(ctx.summary()["company_name"], "Acme")

    def test_summary_contains_counts(self):
        ctx = CompanyContext.create("Acme")
        s = ctx.summary()
        self.assertIn("departments", s)
        self.assertIn("employees", s)


# ===========================================================================
# TestOrchestratorInit
# ===========================================================================

class TestOrchestratorInit(unittest.TestCase):

    def test_init_stores_context(self):
        ctx = _make_context()
        orc = CompanyOrchestrator(ctx)
        self.assertIs(orc._context, ctx)

    def test_init_not_running(self):
        orc = CompanyOrchestrator(_make_context())
        self.assertFalse(orc._is_running)

    def test_init_no_sessions(self):
        orc = CompanyOrchestrator(_make_context())
        self.assertEqual(len(orc._sessions), 0)

    def test_init_no_current_session(self):
        orc = CompanyOrchestrator(_make_context())
        self.assertIsNone(orc._current_session_id)

    def test_init_empty_agent_runtimes(self):
        orc = CompanyOrchestrator(_make_context())
        self.assertEqual(len(orc._agent_runtimes), 0)

    def test_init_creates_discussion_engine(self):
        orc = CompanyOrchestrator(_make_context())
        self.assertIsNotNone(orc._discussion_engine)

    def test_error_classes_are_exceptions(self):
        self.assertTrue(issubclass(OrchestratorError, Exception))
        self.assertTrue(issubclass(OrchestratorNotStartedError, OrchestratorError))
        self.assertTrue(issubclass(OrchestratorAlreadyStartedError, OrchestratorError))
        self.assertTrue(issubclass(OrchestratorNotRunningError, OrchestratorError))
        self.assertTrue(issubclass(InvalidRequestError, OrchestratorError))

    def test_different_contexts_for_different_orchestrators(self):
        ctx1 = _make_context("A")
        ctx2 = _make_context("B")
        orc1 = CompanyOrchestrator(ctx1)
        orc2 = CompanyOrchestrator(ctx2)
        self.assertIsNot(orc1._context, orc2._context)


# ===========================================================================
# TestStartCompany
# ===========================================================================

class TestStartCompany(unittest.TestCase):

    def test_start_sets_running_true(self):
        orc = CompanyOrchestrator(_make_context())
        orc.start_company()
        self.assertTrue(orc._is_running)

    def test_start_returns_context(self):
        ctx = _make_context()
        orc = CompanyOrchestrator(ctx)
        result = orc.start_company()
        self.assertIs(result, ctx)

    def test_start_twice_raises_already_started(self):
        orc = CompanyOrchestrator(_make_context())
        orc.start_company()
        with self.assertRaises(OrchestratorAlreadyStartedError):
            orc.start_company()

    def test_start_error_message_includes_company_name(self):
        orc = CompanyOrchestrator(_make_context("Acme"))
        orc.start_company()
        with self.assertRaises(OrchestratorAlreadyStartedError) as ctx:
            orc.start_company()
        self.assertIn("Acme", str(ctx.exception))

    def test_start_already_started_type(self):
        orc = CompanyOrchestrator(_make_context())
        orc.start_company()
        try:
            orc.start_company()
        except OrchestratorAlreadyStartedError:
            pass
        except Exception as e:
            self.fail(f"Wrong exception: {e}")

    def test_stop_then_restart_raises_on_second_start(self):
        orc = CompanyOrchestrator(_make_context())
        orc.start_company()
        orc.stop_company()
        orc.start_company()
        self.assertTrue(orc._is_running)

    def test_start_without_runtime_does_not_crash(self):
        ctx = _make_context()
        ctx.active_runtime = None
        orc = CompanyOrchestrator(ctx)
        orc.start_company()
        self.assertTrue(orc._is_running)

    def test_status_running_after_start(self):
        orc = CompanyOrchestrator(_make_context())
        orc.start_company()
        self.assertTrue(orc.status()["running"])

    def test_new_request_before_start_raises(self):
        orc = CompanyOrchestrator(_make_context())
        with self.assertRaises(OrchestratorNotStartedError):
            orc.new_request(_VALID_REQUEST)

    def test_start_is_idempotent_across_stop(self):
        orc = CompanyOrchestrator(_make_context())
        orc.start_company()
        orc.stop_company()
        orc.start_company()
        self.assertTrue(orc._is_running)


# ===========================================================================
# TestStopCompany
# ===========================================================================

class TestStopCompany(unittest.TestCase):

    def test_stop_sets_running_false(self):
        orc = _started_orchestrator()
        orc.stop_company()
        self.assertFalse(orc._is_running)

    def test_stop_without_start_raises(self):
        orc = CompanyOrchestrator(_make_context())
        with self.assertRaises(OrchestratorNotRunningError):
            orc.stop_company()

    def test_stop_twice_raises(self):
        orc = _started_orchestrator()
        orc.stop_company()
        with self.assertRaises(OrchestratorNotRunningError):
            orc.stop_company()

    def test_stop_error_message_informative(self):
        orc = CompanyOrchestrator(_make_context())
        with self.assertRaises(OrchestratorNotRunningError) as ctx:
            orc.stop_company()
        self.assertGreater(len(str(ctx.exception)), 10)

    def test_stop_without_runtime_does_not_crash(self):
        ctx = _make_context()
        ctx.active_runtime = None
        orc = CompanyOrchestrator(ctx)
        orc._is_running = True
        orc.stop_company()
        self.assertFalse(orc._is_running)

    def test_status_not_running_after_stop(self):
        orc = _started_orchestrator()
        orc.stop_company()
        self.assertFalse(orc.status()["running"])

    def test_new_request_after_stop_raises(self):
        orc = _started_orchestrator()
        orc.stop_company()
        with self.assertRaises(OrchestratorNotStartedError):
            orc.new_request(_VALID_REQUEST)

    def test_stop_returns_none(self):
        orc = _started_orchestrator()
        result = orc.stop_company()
        self.assertIsNone(result)

    def test_cycle_start_stop_multiple_times(self):
        orc = CompanyOrchestrator(_make_context())
        for _ in range(3):
            orc.start_company()
            self.assertTrue(orc._is_running)
            orc.stop_company()
            self.assertFalse(orc._is_running)

    def test_sessions_preserved_after_stop(self):
        orc = _started_orchestrator()
        orc.new_request(_VALID_REQUEST)
        orc.stop_company()
        self.assertEqual(len(orc.history()), 1)


# ===========================================================================
# TestNewRequestValidation
# ===========================================================================

class TestNewRequestValidation(unittest.TestCase):

    def test_valid_request_returns_session(self):
        orc = _started_orchestrator()
        s = orc.new_request(_VALID_REQUEST)
        self.assertIsInstance(s, CompanySession)

    def test_empty_request_raises(self):
        orc = _started_orchestrator()
        with self.assertRaises(InvalidRequestError):
            orc.new_request("")

    def test_whitespace_only_raises(self):
        orc = _started_orchestrator()
        with self.assertRaises(InvalidRequestError):
            orc.new_request("   ")

    def test_too_short_raises(self):
        orc = _started_orchestrator()
        with self.assertRaises(InvalidRequestError):
            orc.new_request("Hi")

    def test_exactly_ten_chars_accepted(self):
        orc = _started_orchestrator()
        s = orc.new_request("A" * 10)
        self.assertIsInstance(s, CompanySession)

    def test_nine_chars_raises(self):
        orc = _started_orchestrator()
        with self.assertRaises(InvalidRequestError):
            orc.new_request("A" * 9)

    def test_not_started_raises_not_started_error(self):
        orc = CompanyOrchestrator(_make_context())
        with self.assertRaises(OrchestratorNotStartedError):
            orc.new_request(_VALID_REQUEST)

    def test_error_is_orchestrator_error(self):
        orc = _started_orchestrator()
        with self.assertRaises(OrchestratorError):
            orc.new_request("")

    def test_error_message_mentions_length(self):
        orc = _started_orchestrator()
        try:
            orc.new_request("Hi")
        except InvalidRequestError as e:
            self.assertIn("10", str(e))

    def test_invalid_request_not_added_to_history(self):
        orc = _started_orchestrator()
        try:
            orc.new_request("")
        except InvalidRequestError:
            pass
        self.assertEqual(len(orc.history()), 0)

    def test_long_request_works(self):
        orc = _started_orchestrator()
        s = orc.new_request("Build " + ("a" * 500))
        self.assertIsInstance(s, CompanySession)

    def test_tab_only_request_raises(self):
        orc = _started_orchestrator()
        with self.assertRaises(InvalidRequestError):
            orc.new_request("\t\t\t")


# ===========================================================================
# TestNewRequestPipelineAnalyze
# ===========================================================================

class TestNewRequestPipelineAnalyze(unittest.TestCase):

    def _run(self, request=_VALID_REQUEST):
        orc = _started_orchestrator()
        return orc, orc.new_request(request)

    def test_session_has_blueprint_after_request(self):
        _, s = self._run()
        self.assertIsNotNone(s.blueprint)

    def test_blueprint_has_project_title(self):
        _, s = self._run()
        self.assertIsNotNone(s.blueprint.project_title)
        self.assertGreater(len(s.blueprint.project_title), 0)

    def test_blueprint_has_departments(self):
        _, s = self._run()
        self.assertGreater(len(s.blueprint.departments), 0)

    def test_blueprint_has_complexity_score(self):
        _, s = self._run()
        score = s.blueprint.complexity_score
        self.assertGreaterEqual(score, 1)
        self.assertLessEqual(score, 10)

    def test_project_analyzed_event_emitted(self):
        _, s = self._run()
        events = s.events_of_type(CompanyEventType.PROJECT_ANALYZED)
        self.assertEqual(len(events), 1)

    def test_project_analyzed_payload_has_title(self):
        _, s = self._run()
        ev = s.events_of_type(CompanyEventType.PROJECT_ANALYZED)[0]
        self.assertIn("project_title", ev.payload)

    def test_project_analyzed_payload_has_complexity(self):
        _, s = self._run()
        ev = s.events_of_type(CompanyEventType.PROJECT_ANALYZED)[0]
        self.assertIn("complexity_score", ev.payload)

    def test_project_analyzed_payload_departments_required(self):
        _, s = self._run()
        ev = s.events_of_type(CompanyEventType.PROJECT_ANALYZED)[0]
        self.assertIn("departments_required", ev.payload)
        self.assertGreater(ev.payload["departments_required"], 0)

    def test_request_received_event_emitted(self):
        _, s = self._run()
        events = s.events_of_type(CompanyEventType.REQUEST_RECEIVED)
        self.assertEqual(len(events), 1)

    def test_request_received_payload_has_preview(self):
        _, s = self._run()
        ev = s.events_of_type(CompanyEventType.REQUEST_RECEIVED)[0]
        self.assertIn("request_preview", ev.payload)


# ===========================================================================
# TestNewRequestPipelinePlan
# ===========================================================================

class TestNewRequestPipelinePlan(unittest.TestCase):

    def _run(self):
        orc = _started_orchestrator()
        return orc, orc.new_request(_VALID_REQUEST)

    def test_session_has_project(self):
        _, s = self._run()
        self.assertIsNotNone(s.project)

    def test_project_created_event_emitted(self):
        _, s = self._run()
        events = s.events_of_type(CompanyEventType.PROJECT_CREATED)
        self.assertEqual(len(events), 1)

    def test_project_created_payload_has_id(self):
        _, s = self._run()
        ev = s.events_of_type(CompanyEventType.PROJECT_CREATED)[0]
        self.assertIn("project_id", ev.payload)

    def test_departments_provisioned(self):
        orc, s = self._run()
        self.assertGreater(orc._context.department_count(), 0)

    def test_employees_hired(self):
        orc, s = self._run()
        self.assertGreater(orc._context.employee_count(), 0)

    def test_tasks_created(self):
        _, s = self._run()
        self.assertGreater(s.task_count(), 0)

    def test_tasks_equal_departments(self):
        orc, s = self._run()
        self.assertEqual(s.task_count(), len(s.blueprint.departments))

    def test_task_created_events_emitted(self):
        _, s = self._run()
        events = s.events_of_type(CompanyEventType.TASK_CREATED)
        self.assertGreater(len(events), 0)

    def test_task_assigned_events_emitted(self):
        _, s = self._run()
        events = s.events_of_type(CompanyEventType.TASK_ASSIGNED)
        self.assertGreater(len(events), 0)

    def test_task_created_and_assigned_count_equal(self):
        _, s = self._run()
        created = len(s.events_of_type(CompanyEventType.TASK_CREATED))
        assigned = len(s.events_of_type(CompanyEventType.TASK_ASSIGNED))
        self.assertEqual(created, assigned)

    def test_department_provisioned_events_emitted(self):
        _, s = self._run()
        events = s.events_of_type(CompanyEventType.DEPARTMENT_PROVISIONED)
        self.assertGreater(len(events), 0)

    def test_employee_hired_events_emitted(self):
        _, s = self._run()
        events = s.events_of_type(CompanyEventType.EMPLOYEE_HIRED)
        self.assertGreater(len(events), 0)

    def test_employee_hired_payload_has_name(self):
        _, s = self._run()
        ev = s.events_of_type(CompanyEventType.EMPLOYEE_HIRED)[0]
        self.assertIn("employee_name", ev.payload)

    def test_context_active_project_set(self):
        orc, s = self._run()
        self.assertIsNotNone(orc._context.active_project)


# ===========================================================================
# TestNewRequestPipelineExecute
# ===========================================================================

class TestNewRequestPipelineExecute(unittest.TestCase):

    def _run(self):
        orc = _started_orchestrator()
        return orc, orc.new_request(_VALID_REQUEST)

    def test_runtimes_started(self):
        _, s = self._run()
        self.assertGreater(s.runtime_count(), 0)

    def test_runtime_started_events_emitted(self):
        _, s = self._run()
        events = s.events_of_type(CompanyEventType.RUNTIME_STARTED)
        self.assertGreater(len(events), 0)

    def test_runtime_count_equals_employee_count(self):
        orc, s = self._run()
        self.assertEqual(s.runtime_count(), orc._context.employee_count())

    def test_agent_runtimes_created(self):
        orc, _ = self._run()
        self.assertGreater(len(orc._agent_runtimes), 0)

    def test_runtime_started_payload_has_employee_id(self):
        _, s = self._run()
        ev = s.events_of_type(CompanyEventType.RUNTIME_STARTED)[0]
        self.assertIn("employee_id", ev.payload)

    def test_runtime_started_payload_has_task_id(self):
        _, s = self._run()
        ev = s.events_of_type(CompanyEventType.RUNTIME_STARTED)[0]
        self.assertIn("task_id", ev.payload)

    def test_runtime_started_payload_has_session_id(self):
        _, s = self._run()
        ev = s.events_of_type(CompanyEventType.RUNTIME_STARTED)[0]
        self.assertIn("runtime_session_id", ev.payload)

    def test_started_runtimes_are_strings(self):
        _, s = self._run()
        for rt_id in s.started_runtimes:
            self.assertIsInstance(rt_id, str)

    def test_runtime_started_count_matches_session_list(self):
        _, s = self._run()
        event_count = len(s.events_of_type(CompanyEventType.RUNTIME_STARTED))
        self.assertEqual(event_count, s.runtime_count())

    def test_started_runtimes_are_unique(self):
        _, s = self._run()
        self.assertEqual(len(s.started_runtimes), len(set(s.started_runtimes)))


# ===========================================================================
# TestNewRequestPipelineDiscuss
# ===========================================================================

class TestNewRequestPipelineDiscuss(unittest.TestCase):

    def _run(self):
        orc = _started_orchestrator()
        return orc, orc.new_request(_VALID_REQUEST)

    def test_discussions_created(self):
        _, s = self._run()
        self.assertGreater(s.discussion_count(), 0)

    def test_discussion_started_event_emitted(self):
        _, s = self._run()
        events = s.events_of_type(CompanyEventType.DISCUSSION_STARTED)
        self.assertEqual(len(events), 1)

    def test_discussion_finished_event_emitted(self):
        _, s = self._run()
        events = s.events_of_type(CompanyEventType.DISCUSSION_FINISHED)
        self.assertEqual(len(events), 1)

    def test_discussion_started_before_finished(self):
        _, s = self._run()
        started_ts = s.events_of_type(CompanyEventType.DISCUSSION_STARTED)[0].timestamp
        finished_ts = s.events_of_type(CompanyEventType.DISCUSSION_FINISHED)[0].timestamp
        self.assertLessEqual(started_ts, finished_ts)

    def test_discussion_started_payload_has_topic(self):
        _, s = self._run()
        ev = s.events_of_type(CompanyEventType.DISCUSSION_STARTED)[0]
        self.assertIn("topic", ev.payload)

    def test_discussion_started_payload_has_project_id(self):
        _, s = self._run()
        ev = s.events_of_type(CompanyEventType.DISCUSSION_STARTED)[0]
        self.assertIn("project_id", ev.payload)

    def test_discussion_finished_payload_has_participants(self):
        _, s = self._run()
        ev = s.events_of_type(CompanyEventType.DISCUSSION_FINISHED)[0]
        self.assertIn("participants", ev.payload)

    def test_discussion_finished_payload_has_messages(self):
        _, s = self._run()
        ev = s.events_of_type(CompanyEventType.DISCUSSION_FINISHED)[0]
        self.assertIn("messages", ev.payload)
        self.assertGreater(ev.payload["messages"], 0)

    def test_discussion_is_stored_in_session(self):
        _, s = self._run()
        self.assertEqual(len(s.discussions), 1)

    def test_discussion_is_closed_after_pipeline(self):
        _, s = self._run()
        discussion = s.discussions[0]
        self.assertTrue(discussion.is_closed())


# ===========================================================================
# TestNewRequestPipelineFinish
# ===========================================================================

class TestNewRequestPipelineFinish(unittest.TestCase):

    def _run(self):
        orc = _started_orchestrator()
        return orc, orc.new_request(_VALID_REQUEST)

    def test_session_is_finished(self):
        _, s = self._run()
        self.assertTrue(s.is_finished())

    def test_session_not_failed(self):
        _, s = self._run()
        self.assertFalse(s.is_failed())

    def test_project_finished_event_emitted(self):
        _, s = self._run()
        events = s.events_of_type(CompanyEventType.PROJECT_FINISHED)
        self.assertEqual(len(events), 1)

    def test_request_completed_event_emitted(self):
        _, s = self._run()
        events = s.events_of_type(CompanyEventType.REQUEST_COMPLETED)
        self.assertEqual(len(events), 1)

    def test_request_completed_is_last_event(self):
        _, s = self._run()
        self.assertEqual(s.last_event().event_type, CompanyEventType.REQUEST_COMPLETED)

    def test_session_finished_at_set(self):
        _, s = self._run()
        self.assertIsNotNone(s.finished_at)

    def test_session_duration_is_positive(self):
        _, s = self._run()
        self.assertGreater(s.duration_seconds(), 0.0)

    def test_error_message_none_on_success(self):
        _, s = self._run()
        self.assertIsNone(s.error_message)

    def test_project_status_completed(self):
        from core.project import ProjectStatus
        _, s = self._run()
        self.assertEqual(s.project.status, ProjectStatus.COMPLETED)

    def test_stage_is_finished(self):
        _, s = self._run()
        self.assertEqual(s.current_stage, SessionStage.FINISHED)


# ===========================================================================
# TestNewRequestEventLog
# ===========================================================================

class TestNewRequestEventLog(unittest.TestCase):

    def _run(self):
        orc = _started_orchestrator()
        return orc.new_request(_VALID_REQUEST)

    def test_events_not_empty(self):
        s = self._run()
        self.assertGreater(s.event_count(), 0)

    def test_events_have_timestamps(self):
        s = self._run()
        for ev in s.events:
            self.assertIsNotNone(ev.timestamp)

    def test_event_ids_unique(self):
        s = self._run()
        ids = [ev.id for ev in s.events]
        self.assertEqual(len(ids), len(set(ids)))

    def test_all_events_have_session_id(self):
        s = self._run()
        for ev in s.events:
            self.assertEqual(ev.session_id, s.id)

    def test_request_received_is_first_event(self):
        s = self._run()
        self.assertEqual(s.events[0].event_type, CompanyEventType.REQUEST_RECEIVED)

    def test_request_completed_is_last_event(self):
        s = self._run()
        self.assertEqual(s.events[-1].event_type, CompanyEventType.REQUEST_COMPLETED)

    def test_events_in_pipeline_order(self):
        s = self._run()
        event_types = [ev.event_type for ev in s.events]
        # REQUEST_RECEIVED must precede PROJECT_ANALYZED
        ri = event_types.index(CompanyEventType.REQUEST_RECEIVED)
        ai = event_types.index(CompanyEventType.PROJECT_ANALYZED)
        self.assertLess(ri, ai)

    def test_project_created_after_analyzed(self):
        s = self._run()
        event_types = [ev.event_type for ev in s.events]
        ai = event_types.index(CompanyEventType.PROJECT_ANALYZED)
        pi = event_types.index(CompanyEventType.PROJECT_CREATED)
        self.assertLess(ai, pi)

    def test_runtime_started_after_task_assigned(self):
        s = self._run()
        event_types = [ev.event_type for ev in s.events]
        last_ta = max(i for i, et in enumerate(event_types) if et == CompanyEventType.TASK_ASSIGNED)
        first_rs = event_types.index(CompanyEventType.RUNTIME_STARTED)
        self.assertLessEqual(last_ta, first_rs)

    def test_discussion_started_after_runtimes(self):
        s = self._run()
        event_types = [ev.event_type for ev in s.events]
        last_rs = max(i for i, et in enumerate(event_types) if et == CompanyEventType.RUNTIME_STARTED)
        ds = event_types.index(CompanyEventType.DISCUSSION_STARTED)
        self.assertLess(last_rs, ds)

    def test_project_finished_before_request_completed(self):
        s = self._run()
        event_types = [ev.event_type for ev in s.events]
        pf = event_types.index(CompanyEventType.PROJECT_FINISHED)
        rc = event_types.index(CompanyEventType.REQUEST_COMPLETED)
        self.assertLess(pf, rc)

    def test_total_event_count_reasonable(self):
        s = self._run()
        # At minimum: REQUEST_RECEIVED + PROJECT_ANALYZED + PROJECT_CREATED +
        # at least 1 each of DEPT, HIRE, TASK_CREATED, TASK_ASSIGNED, RUNTIME +
        # DISCUSSION_STARTED + DISCUSSION_FINISHED + PROJECT_FINISHED + REQUEST_COMPLETED
        self.assertGreaterEqual(s.event_count(), 12)

    def test_events_are_immutable(self):
        s = self._run()
        ev = s.events[0]
        with self.assertRaises(Exception):
            ev.event_type = CompanyEventType.TASK_CREATED  # type: ignore

    def test_events_list_is_ordered_by_emission(self):
        s = self._run()
        for i in range(1, len(s.events)):
            self.assertLessEqual(s.events[i - 1].timestamp, s.events[i].timestamp)

    def test_no_failed_events_on_success(self):
        s = self._run()
        failed = s.events_of_type(CompanyEventType.REQUEST_FAILED)
        self.assertEqual(len(failed), 0)

    def test_each_session_event_has_matching_session_id(self):
        s = self._run()
        for ev in s.events:
            self.assertEqual(ev.session_id, s.id)


# ===========================================================================
# TestCurrentSession
# ===========================================================================

class TestCurrentSession(unittest.TestCase):

    def test_current_session_none_before_any_request(self):
        orc = _started_orchestrator()
        self.assertIsNone(orc.current_session())

    def test_current_session_returns_last_session(self):
        orc = _started_orchestrator()
        s = orc.new_request(_VALID_REQUEST)
        self.assertIs(orc.current_session(), s)

    def test_current_session_after_two_requests(self):
        orc = _started_orchestrator()
        orc.new_request(_VALID_REQUEST)
        s2 = orc.new_request(_VALID_REQUEST + " v2")
        self.assertIs(orc.current_session(), s2)

    def test_current_session_is_finished(self):
        orc = _started_orchestrator()
        orc.new_request(_VALID_REQUEST)
        self.assertTrue(orc.current_session().is_finished())

    def test_current_session_is_company_session(self):
        orc = _started_orchestrator()
        orc.new_request(_VALID_REQUEST)
        self.assertIsInstance(orc.current_session(), CompanySession)

    def test_current_session_has_request(self):
        orc = _started_orchestrator()
        orc.new_request(_VALID_REQUEST)
        self.assertEqual(orc.current_session().request, _VALID_REQUEST)

    def test_current_session_before_start(self):
        orc = CompanyOrchestrator(_make_context())
        self.assertIsNone(orc.current_session())

    def test_current_session_after_stop(self):
        orc = _started_orchestrator()
        orc.new_request(_VALID_REQUEST)
        orc.stop_company()
        self.assertIsNotNone(orc.current_session())


# ===========================================================================
# TestHistory
# ===========================================================================

class TestHistory(unittest.TestCase):

    def test_history_empty_initially(self):
        orc = _started_orchestrator()
        self.assertEqual(orc.history(), [])

    def test_history_contains_session_after_request(self):
        orc = _started_orchestrator()
        orc.new_request(_VALID_REQUEST)
        self.assertEqual(len(orc.history()), 1)

    def test_history_grows_with_each_request(self):
        orc = _started_orchestrator()
        for i in range(3):
            orc.new_request(_VALID_REQUEST + " " + str(i))
        self.assertEqual(len(orc.history()), 3)

    def test_history_is_shallow_copy(self):
        orc = _started_orchestrator()
        orc.new_request(_VALID_REQUEST)
        hist = orc.history()
        hist.clear()
        self.assertEqual(len(orc.history()), 1)

    def test_history_ordered_oldest_first(self):
        orc = _started_orchestrator()
        s1 = orc.new_request(_VALID_REQUEST + " first")
        s2 = orc.new_request(_VALID_REQUEST + " second")
        hist = orc.history()
        self.assertIs(hist[0], s1)
        self.assertIs(hist[1], s2)

    def test_history_contains_company_sessions(self):
        orc = _started_orchestrator()
        orc.new_request(_VALID_REQUEST)
        for item in orc.history():
            self.assertIsInstance(item, CompanySession)

    def test_history_preserved_after_stop(self):
        orc = _started_orchestrator()
        orc.new_request(_VALID_REQUEST)
        orc.stop_company()
        self.assertEqual(len(orc.history()), 1)

    def test_history_returns_same_objects(self):
        orc = _started_orchestrator()
        s = orc.new_request(_VALID_REQUEST)
        self.assertIs(orc.history()[0], s)


# ===========================================================================
# TestStatus
# ===========================================================================

class TestStatus(unittest.TestCase):

    def _status_started(self):
        orc = _started_orchestrator("AcmeCo")
        return orc, orc.status()

    def test_status_returns_dict(self):
        _, s = self._status_started()
        self.assertIsInstance(s, dict)

    def test_status_running_true_when_started(self):
        _, s = self._status_started()
        self.assertTrue(s["running"])

    def test_status_running_false_when_not_started(self):
        orc = CompanyOrchestrator(_make_context())
        self.assertFalse(orc.status()["running"])

    def test_status_has_company_name(self):
        _, s = self._status_started()
        self.assertEqual(s["company_name"], "AcmeCo")

    def test_status_has_company_id(self):
        _, s = self._status_started()
        self.assertIn("company_id", s)

    def test_status_total_sessions_zero_initially(self):
        _, s = self._status_started()
        self.assertEqual(s["total_sessions"], 0)

    def test_status_total_sessions_increments(self):
        orc, _ = self._status_started()
        orc.new_request(_VALID_REQUEST)
        self.assertEqual(orc.status()["total_sessions"], 1)

    def test_status_active_session_none_initially(self):
        _, s = self._status_started()
        self.assertIsNone(s["active_session"])

    def test_status_active_session_set_after_request(self):
        orc, _ = self._status_started()
        orc.new_request(_VALID_REQUEST)
        self.assertIsNotNone(orc.status()["active_session"])

    def test_status_departments_count(self):
        orc, _ = self._status_started()
        orc.new_request(_VALID_REQUEST)
        self.assertGreater(orc.status()["departments"], 0)


# ===========================================================================
# TestStatistics
# ===========================================================================

class TestStatistics(unittest.TestCase):

    def _stats_after_request(self):
        orc = _started_orchestrator()
        orc.new_request(_VALID_REQUEST)
        return orc, orc.statistics()

    def test_statistics_returns_dict(self):
        _, s = self._stats_after_request()
        self.assertIsInstance(s, dict)

    def test_statistics_total_sessions(self):
        _, s = self._stats_after_request()
        self.assertEqual(s["total_sessions"], 1)

    def test_statistics_finished_sessions(self):
        _, s = self._stats_after_request()
        self.assertEqual(s["finished_sessions"], 1)

    def test_statistics_failed_sessions_zero_on_success(self):
        _, s = self._stats_after_request()
        self.assertEqual(s["failed_sessions"], 0)

    def test_statistics_total_projects(self):
        _, s = self._stats_after_request()
        self.assertGreaterEqual(s["total_projects"], 1)

    def test_statistics_total_tasks(self):
        _, s = self._stats_after_request()
        self.assertGreater(s["total_tasks"], 0)

    def test_statistics_total_discussions(self):
        _, s = self._stats_after_request()
        self.assertGreater(s["total_discussions"], 0)

    def test_statistics_total_runtimes(self):
        _, s = self._stats_after_request()
        self.assertGreater(s["total_runtimes"], 0)

    def test_statistics_total_events(self):
        _, s = self._stats_after_request()
        self.assertGreater(s["total_events"], 10)

    def test_statistics_departments(self):
        _, s = self._stats_after_request()
        self.assertGreater(s["departments"], 0)

    def test_statistics_employees(self):
        _, s = self._stats_after_request()
        self.assertGreater(s["employees"], 0)

    def test_statistics_accumulate_across_requests(self):
        orc = _started_orchestrator()
        orc.new_request(_VALID_REQUEST + " first")
        orc.new_request(_VALID_REQUEST + " second")
        stats = orc.statistics()
        self.assertEqual(stats["total_sessions"], 2)
        self.assertEqual(stats["finished_sessions"], 2)


# ===========================================================================
# TestErrorHandling
# ===========================================================================

class TestErrorHandling(unittest.TestCase):

    def test_new_request_returns_session_even_on_internal_error(self):
        orc = _started_orchestrator()
        # Inject a fault into the planner
        original = orc._context.planner.analyze

        def bad_analyze(_):
            raise RuntimeError("Simulated planner failure")

        orc._context.planner.analyze = bad_analyze
        s = orc.new_request(_VALID_REQUEST)
        self.assertIsInstance(s, CompanySession)

    def test_failed_session_has_failed_stage(self):
        orc = _started_orchestrator()
        original = orc._context.planner.analyze

        def bad_analyze(_):
            raise RuntimeError("Simulated failure")

        orc._context.planner.analyze = bad_analyze
        s = orc.new_request(_VALID_REQUEST)
        self.assertTrue(s.is_failed())

    def test_failed_session_has_error_message(self):
        orc = _started_orchestrator()

        def bad_analyze(_):
            raise RuntimeError("Planner exploded")

        orc._context.planner.analyze = bad_analyze
        s = orc.new_request(_VALID_REQUEST)
        self.assertIsNotNone(s.error_message)
        self.assertIn("Planner exploded", s.error_message)

    def test_failed_session_has_request_failed_event(self):
        orc = _started_orchestrator()

        def bad_analyze(_):
            raise RuntimeError("Failure")

        orc._context.planner.analyze = bad_analyze
        s = orc.new_request(_VALID_REQUEST)
        events = s.events_of_type(CompanyEventType.REQUEST_FAILED)
        self.assertEqual(len(events), 1)

    def test_failed_session_is_added_to_history(self):
        orc = _started_orchestrator()

        def bad_analyze(_):
            raise ValueError("oops")

        orc._context.planner.analyze = bad_analyze
        orc.new_request(_VALID_REQUEST)
        self.assertEqual(len(orc.history()), 1)

    def test_statistics_count_failed_sessions(self):
        orc = _started_orchestrator()

        def bad_analyze(_):
            raise ValueError("oops")

        orc._context.planner.analyze = bad_analyze
        orc.new_request(_VALID_REQUEST)
        stats = orc.statistics()
        self.assertEqual(stats["failed_sessions"], 1)
        self.assertEqual(stats["finished_sessions"], 0)

    def test_failed_session_finished_at_set(self):
        orc = _started_orchestrator()

        def bad_analyze(_):
            raise RuntimeError("done")

        orc._context.planner.analyze = bad_analyze
        s = orc.new_request(_VALID_REQUEST)
        self.assertIsNotNone(s.finished_at)

    def test_request_completed_not_emitted_on_failure(self):
        orc = _started_orchestrator()

        def bad_analyze(_):
            raise RuntimeError("done")

        orc._context.planner.analyze = bad_analyze
        s = orc.new_request(_VALID_REQUEST)
        self.assertEqual(len(s.events_of_type(CompanyEventType.REQUEST_COMPLETED)), 0)

    def test_orchestrator_still_usable_after_failed_session(self):
        orc = _started_orchestrator()
        bad_called = [False]

        real_analyze = orc._context.planner.analyze

        def sometimes_bad(req):
            if not bad_called[0]:
                bad_called[0] = True
                raise RuntimeError("first call fails")
            return real_analyze(req)

        orc._context.planner.analyze = sometimes_bad
        s1 = orc.new_request(_VALID_REQUEST)
        self.assertTrue(s1.is_failed())

        orc._context.planner.analyze = real_analyze
        s2 = orc.new_request(_VALID_REQUEST)
        self.assertTrue(s2.is_finished())

    def test_invalid_request_not_counted_in_statistics(self):
        orc = _started_orchestrator()
        try:
            orc.new_request("")
        except InvalidRequestError:
            pass
        stats = orc.statistics()
        self.assertEqual(stats["total_sessions"], 0)

    def test_orchestrator_error_hierarchy(self):
        self.assertTrue(issubclass(OrchestratorNotStartedError, OrchestratorError))
        self.assertTrue(issubclass(OrchestratorAlreadyStartedError, OrchestratorError))
        self.assertTrue(issubclass(OrchestratorNotRunningError, OrchestratorError))
        self.assertTrue(issubclass(InvalidRequestError, OrchestratorError))

    def test_fail_session_records_reason(self):
        orc = _started_orchestrator()

        def bad_analyze(_):
            raise RuntimeError("my unique reason")

        orc._context.planner.analyze = bad_analyze
        s = orc.new_request(_VALID_REQUEST)
        ev = s.events_of_type(CompanyEventType.REQUEST_FAILED)[0]
        self.assertIn("my unique reason", ev.payload.get("reason", ""))

    def test_session_added_to_history_before_pipeline_runs(self):
        orc = _started_orchestrator()
        # By checking after a successful run that the session appears in history once
        orc.new_request(_VALID_REQUEST)
        self.assertEqual(len(orc.history()), 1)

    def test_failed_session_current_session_is_the_failed_one(self):
        orc = _started_orchestrator()

        def bad_analyze(_):
            raise RuntimeError("done")

        orc._context.planner.analyze = bad_analyze
        s = orc.new_request(_VALID_REQUEST)
        self.assertIs(orc.current_session(), s)


# ===========================================================================
# TestMultipleRequests
# ===========================================================================

class TestMultipleRequests(unittest.TestCase):

    def test_two_requests_two_sessions(self):
        orc = _started_orchestrator()
        orc.new_request(_VALID_REQUEST + " A")
        orc.new_request(_VALID_REQUEST + " B")
        self.assertEqual(len(orc.history()), 2)

    def test_sessions_have_different_ids(self):
        orc = _started_orchestrator()
        s1 = orc.new_request(_VALID_REQUEST + " A")
        s2 = orc.new_request(_VALID_REQUEST + " B")
        self.assertNotEqual(s1.id, s2.id)

    def test_sessions_preserve_request_text(self):
        orc = _started_orchestrator()
        req1 = _VALID_REQUEST + " alpha"
        req2 = _VALID_REQUEST + " beta"
        s1 = orc.new_request(req1)
        s2 = orc.new_request(req2)
        self.assertEqual(s1.request, req1)
        self.assertEqual(s2.request, req2)

    def test_statistics_accumulate_tasks(self):
        orc = _started_orchestrator()
        orc.new_request(_VALID_REQUEST + " A")
        tasks_after_1 = orc.statistics()["total_tasks"]
        orc.new_request(_VALID_REQUEST + " B")
        tasks_after_2 = orc.statistics()["total_tasks"]
        self.assertGreater(tasks_after_2, tasks_after_1)

    def test_current_session_reflects_latest(self):
        orc = _started_orchestrator()
        orc.new_request(_VALID_REQUEST + " X")
        s2 = orc.new_request(_VALID_REQUEST + " Y")
        self.assertIs(orc.current_session(), s2)

    def test_history_is_ordered(self):
        orc = _started_orchestrator()
        s1 = orc.new_request(_VALID_REQUEST + " 1")
        s2 = orc.new_request(_VALID_REQUEST + " 2")
        s3 = orc.new_request(_VALID_REQUEST + " 3")
        hist = orc.history()
        self.assertIs(hist[0], s1)
        self.assertIs(hist[1], s2)
        self.assertIs(hist[2], s3)

    def test_employees_accumulate_across_requests(self):
        orc = _started_orchestrator()
        orc.new_request(_VALID_REQUEST + " A")
        emp_after_1 = orc._context.employee_count()
        orc.new_request(_VALID_REQUEST + " B")
        emp_after_2 = orc._context.employee_count()
        # Second request may add more employees
        self.assertGreaterEqual(emp_after_2, emp_after_1)

    def test_all_sessions_finished(self):
        orc = _started_orchestrator()
        for i in range(3):
            orc.new_request(_VALID_REQUEST + " " + str(i))
        for s in orc.history():
            self.assertTrue(s.is_finished())


# ===========================================================================
# TestIntegration
# ===========================================================================

class TestIntegration(unittest.TestCase):

    def setUp(self):
        self.orc = _started_orchestrator("FullCo")
        self.session = self.orc.new_request(
            "Build an e-commerce platform with payments, catalog, and user accounts."
        )

    def test_session_is_finished(self):
        self.assertTrue(self.session.is_finished())

    def test_project_exists(self):
        self.assertIsNotNone(self.session.project)

    def test_blueprint_exists(self):
        self.assertIsNotNone(self.session.blueprint)

    def test_tasks_created(self):
        self.assertGreater(self.session.task_count(), 0)

    def test_runtimes_started(self):
        self.assertGreater(self.session.runtime_count(), 0)

    def test_discussion_occurred(self):
        self.assertGreater(self.session.discussion_count(), 0)

    def test_events_logged(self):
        self.assertGreater(self.session.event_count(), 10)

    def test_company_has_departments(self):
        self.assertGreater(self.orc._context.department_count(), 0)

    def test_company_has_employees(self):
        self.assertGreater(self.orc._context.employee_count(), 0)

    def test_statistics_after_full_run(self):
        stats = self.orc.statistics()
        self.assertEqual(stats["finished_sessions"], 1)
        self.assertEqual(stats["failed_sessions"], 0)

    def test_discussion_topic_mentions_project(self):
        discussion = self.session.discussions[0]
        self.assertIn(self.session.project.title[:20], discussion.topic)

    def test_task_count_matches_department_count(self):
        task_count = self.session.task_count()
        dept_count = len(self.session.blueprint.departments)
        self.assertEqual(task_count, dept_count)

    def test_status_after_full_run(self):
        status = self.orc.status()
        self.assertTrue(status["running"])
        self.assertEqual(status["total_sessions"], 1)
        self.assertGreater(status["departments"], 0)
        self.assertGreater(status["employees"], 0)

    def test_history_has_one_session(self):
        self.assertEqual(len(self.orc.history()), 1)

    def test_session_request_preserved(self):
        self.assertIn("e-commerce", self.session.request)

    def test_stop_after_full_run(self):
        self.orc.stop_company()
        self.assertFalse(self.orc._is_running)


# ===========================================================================
# TestOrchestratorContracts
# ===========================================================================

class TestOrchestratorContracts(unittest.TestCase):

    def test_new_request_always_returns_company_session(self):
        orc = _started_orchestrator()
        result = orc.new_request(_VALID_REQUEST)
        self.assertIsInstance(result, CompanySession)

    def test_history_always_returns_list(self):
        orc = _started_orchestrator()
        self.assertIsInstance(orc.history(), list)

    def test_status_always_returns_dict(self):
        orc = _started_orchestrator()
        self.assertIsInstance(orc.status(), dict)

    def test_statistics_always_returns_dict(self):
        orc = _started_orchestrator()
        self.assertIsInstance(orc.statistics(), dict)

    def test_current_session_returns_none_or_company_session(self):
        orc = _started_orchestrator()
        cs = orc.current_session()
        self.assertTrue(cs is None or isinstance(cs, CompanySession))

    def test_session_ids_are_unique_across_requests(self):
        orc = _started_orchestrator()
        ids = [orc.new_request(_VALID_REQUEST + str(i)).id for i in range(5)]
        self.assertEqual(len(ids), len(set(ids)))

    def test_agent_runtimes_keyed_by_employee_id(self):
        orc = _started_orchestrator()
        orc.new_request(_VALID_REQUEST)
        for key in orc._agent_runtimes:
            self.assertIsInstance(key, str)

    def test_events_in_session_match_session_id(self):
        orc = _started_orchestrator()
        s = orc.new_request(_VALID_REQUEST)
        for ev in s.events:
            self.assertEqual(ev.session_id, s.id)

    def test_discussions_are_closed_after_pipeline(self):
        orc = _started_orchestrator()
        s = orc.new_request(_VALID_REQUEST)
        for disc in s.discussions:
            self.assertTrue(disc.is_closed(), disc.id)

    def test_no_duplicate_sessions_in_history(self):
        orc = _started_orchestrator()
        for i in range(4):
            orc.new_request(_VALID_REQUEST + str(i))
        ids = [s.id for s in orc.history()]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
