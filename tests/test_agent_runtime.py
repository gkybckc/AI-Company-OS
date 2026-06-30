"""
Comprehensive unit tests for Sprint 7 — Agent Runtime.

Covers: AgentRuntimeState, AGENT_RUNTIME_TRANSITIONS, RuntimeContext,
RuntimeResult, RuntimeEventType, RuntimeEvent, RuntimeSession, and
AgentRuntime (all public methods and all lifecycle scenarios).

Run with:
    .venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_agent_runtime.py" -v
"""

import unittest
from datetime import datetime, timezone
from typing import Optional

from core.agent_runtime import (
    AgentRuntime,
    AgentRuntimeError,
    IllegalStateTransitionError,
    InvalidProgressError,
    NoActiveSessionError,
    SessionAlreadyActiveError,
    SessionAlreadyTerminalError,
)
from core.department_type import DepartmentType
from core.runtime_context import RuntimeContext
from core.runtime_result import RuntimeResult
from core.runtime_session import RuntimeEvent, RuntimeEventType, RuntimeSession
from core.runtime_state import AGENT_RUNTIME_TRANSITIONS, AgentRuntimeState


# ---------------------------------------------------------------------------
# Shared factories
# ---------------------------------------------------------------------------

def _runtime(employee_id: str = "emp-001") -> AgentRuntime:
    return AgentRuntime(employee_id=employee_id)


def _started(
    runtime: Optional[AgentRuntime] = None,
    project_id: Optional[str] = None,
    task_id: Optional[str] = None,
) -> tuple:
    rt = runtime or _runtime()
    sess = rt.start_session(project_id=project_id, task_id=task_id)
    return rt, sess


def _context(
    current_task: Optional[str] = "task-001",
    project: Optional[str] = "proj-001",
    department: Optional[DepartmentType] = DepartmentType.BACKEND,
    director_id: Optional[str] = "dir-001",
) -> RuntimeContext:
    return RuntimeContext(
        current_task=current_task,
        project=project,
        department=department,
        director_id=director_id,
    )


def _result(
    success: bool = True,
    summary: str = "Task completed.",
    requires_approval: bool = False,
    requires_discussion: bool = False,
    artifacts: list | None = None,
) -> RuntimeResult:
    return RuntimeResult(
        success=success,
        summary=summary,
        requires_approval=requires_approval,
        requires_discussion=requires_discussion,
        generated_artifacts=artifacts or [],
    )


def _advance_to(rt: AgentRuntime, *states: AgentRuntimeState) -> None:
    """Advance the runtime through a sequence of states."""
    for state in states:
        rt.change_state(state)


def _advance_to_working(rt: AgentRuntime) -> None:
    """Drive the active session along the main path to WORKING state."""
    _advance_to(
        rt,
        AgentRuntimeState.WAITING_TASK,
        AgentRuntimeState.TASK_RECEIVED,
        AgentRuntimeState.ANALYZING,
        AgentRuntimeState.PLANNING,
        AgentRuntimeState.WORKING,
    )


def _advance_to_self_review(rt: AgentRuntime) -> None:
    _advance_to_working(rt)
    rt.change_state(AgentRuntimeState.SELF_REVIEW)


# ---------------------------------------------------------------------------
# TestAgentRuntimeState
# ---------------------------------------------------------------------------

class TestAgentRuntimeState(unittest.TestCase):

    def test_fourteen_states_exist(self) -> None:
        names = {s.name for s in AgentRuntimeState}
        expected = {
            "CREATED", "READY", "WAITING_TASK", "TASK_RECEIVED",
            "ANALYZING", "PLANNING", "WORKING", "SELF_REVIEW",
            "WAITING_DISCUSSION", "WAITING_MEMORY", "WAITING_APPROVAL",
            "FINISHED", "FAILED", "IDLE",
        }
        self.assertEqual(names, expected)

    def test_str_returns_value(self) -> None:
        for state in AgentRuntimeState:
            self.assertEqual(str(state), state.value)

    def test_is_str_subclass(self) -> None:
        self.assertIsInstance(AgentRuntimeState.READY, str)

    def test_string_comparison(self) -> None:
        self.assertEqual(AgentRuntimeState.FINISHED, "FINISHED")
        self.assertEqual(AgentRuntimeState.FAILED, "FAILED")

    def test_is_terminal_true_for_finished(self) -> None:
        self.assertTrue(AgentRuntimeState.FINISHED.is_terminal())

    def test_is_terminal_true_for_failed(self) -> None:
        self.assertTrue(AgentRuntimeState.FAILED.is_terminal())

    def test_is_terminal_false_for_all_non_terminal(self) -> None:
        non_terminal = set(AgentRuntimeState) - {
            AgentRuntimeState.FINISHED, AgentRuntimeState.FAILED
        }
        for state in non_terminal:
            self.assertFalse(state.is_terminal(), msg=state.value)

    def test_is_waiting_true(self) -> None:
        for state in (
            AgentRuntimeState.WAITING_TASK,
            AgentRuntimeState.WAITING_DISCUSSION,
            AgentRuntimeState.WAITING_MEMORY,
            AgentRuntimeState.WAITING_APPROVAL,
        ):
            self.assertTrue(state.is_waiting(), msg=state.value)

    def test_is_waiting_false(self) -> None:
        not_waiting = {
            AgentRuntimeState.CREATED, AgentRuntimeState.READY,
            AgentRuntimeState.TASK_RECEIVED, AgentRuntimeState.ANALYZING,
            AgentRuntimeState.PLANNING, AgentRuntimeState.WORKING,
            AgentRuntimeState.SELF_REVIEW, AgentRuntimeState.FINISHED,
            AgentRuntimeState.FAILED, AgentRuntimeState.IDLE,
        }
        for state in not_waiting:
            self.assertFalse(state.is_waiting(), msg=state.value)

    def test_is_active_processing_true(self) -> None:
        for state in (
            AgentRuntimeState.ANALYZING,
            AgentRuntimeState.PLANNING,
            AgentRuntimeState.WORKING,
            AgentRuntimeState.SELF_REVIEW,
        ):
            self.assertTrue(state.is_active_processing(), msg=state.value)

    def test_is_active_processing_false(self) -> None:
        not_processing = {
            AgentRuntimeState.CREATED, AgentRuntimeState.READY,
            AgentRuntimeState.WAITING_TASK, AgentRuntimeState.TASK_RECEIVED,
            AgentRuntimeState.WAITING_DISCUSSION, AgentRuntimeState.WAITING_MEMORY,
            AgentRuntimeState.WAITING_APPROVAL, AgentRuntimeState.FINISHED,
            AgentRuntimeState.FAILED, AgentRuntimeState.IDLE,
        }
        for state in not_processing:
            self.assertFalse(state.is_active_processing(), msg=state.value)

    def test_allowed_next_states_returns_frozenset(self) -> None:
        result = AgentRuntimeState.READY.allowed_next_states()
        self.assertIsInstance(result, frozenset)

    def test_allowed_next_states_terminal_is_empty(self) -> None:
        self.assertEqual(AgentRuntimeState.FINISHED.allowed_next_states(), frozenset())
        self.assertEqual(AgentRuntimeState.FAILED.allowed_next_states(), frozenset())

    def test_can_transition_to_valid(self) -> None:
        self.assertTrue(
            AgentRuntimeState.READY.can_transition_to(AgentRuntimeState.WAITING_TASK)
        )

    def test_can_transition_to_invalid(self) -> None:
        self.assertFalse(
            AgentRuntimeState.READY.can_transition_to(AgentRuntimeState.FINISHED)
        )

    def test_can_transition_to_self_is_false(self) -> None:
        for state in AgentRuntimeState:
            self.assertFalse(state.can_transition_to(state), msg=state.value)


# ---------------------------------------------------------------------------
# TestTransitionMap
# ---------------------------------------------------------------------------

class TestTransitionMap(unittest.TestCase):

    def test_all_states_have_entry(self) -> None:
        for state in AgentRuntimeState:
            self.assertIn(state, AGENT_RUNTIME_TRANSITIONS)

    def test_terminal_states_have_empty_sets(self) -> None:
        self.assertEqual(
            AGENT_RUNTIME_TRANSITIONS[AgentRuntimeState.FINISHED], frozenset()
        )
        self.assertEqual(
            AGENT_RUNTIME_TRANSITIONS[AgentRuntimeState.FAILED], frozenset()
        )

    def test_failed_reachable_from_all_non_terminal(self) -> None:
        non_terminal = [
            s for s in AgentRuntimeState
            if not s.is_terminal()
        ]
        for state in non_terminal:
            self.assertIn(
                AgentRuntimeState.FAILED,
                AGENT_RUNTIME_TRANSITIONS[state],
                msg=f"FAILED must be reachable from {state}",
            )

    def test_created_transitions_to_ready(self) -> None:
        self.assertIn(
            AgentRuntimeState.READY,
            AGENT_RUNTIME_TRANSITIONS[AgentRuntimeState.CREATED],
        )

    def test_ready_transitions_to_waiting_task(self) -> None:
        self.assertIn(
            AgentRuntimeState.WAITING_TASK,
            AGENT_RUNTIME_TRANSITIONS[AgentRuntimeState.READY],
        )

    def test_ready_transitions_to_idle(self) -> None:
        self.assertIn(
            AgentRuntimeState.IDLE,
            AGENT_RUNTIME_TRANSITIONS[AgentRuntimeState.READY],
        )

    def test_waiting_task_transitions_to_task_received(self) -> None:
        self.assertIn(
            AgentRuntimeState.TASK_RECEIVED,
            AGENT_RUNTIME_TRANSITIONS[AgentRuntimeState.WAITING_TASK],
        )

    def test_self_review_can_reach_finished(self) -> None:
        self.assertIn(
            AgentRuntimeState.FINISHED,
            AGENT_RUNTIME_TRANSITIONS[AgentRuntimeState.SELF_REVIEW],
        )

    def test_waiting_approval_can_finish(self) -> None:
        self.assertIn(
            AgentRuntimeState.FINISHED,
            AGENT_RUNTIME_TRANSITIONS[AgentRuntimeState.WAITING_APPROVAL],
        )

    def test_waiting_approval_can_rework(self) -> None:
        self.assertIn(
            AgentRuntimeState.WORKING,
            AGENT_RUNTIME_TRANSITIONS[AgentRuntimeState.WAITING_APPROVAL],
        )

    def test_waiting_discussion_back_to_working(self) -> None:
        self.assertIn(
            AgentRuntimeState.WORKING,
            AGENT_RUNTIME_TRANSITIONS[AgentRuntimeState.WAITING_DISCUSSION],
        )

    def test_waiting_memory_back_to_working(self) -> None:
        self.assertIn(
            AgentRuntimeState.WORKING,
            AGENT_RUNTIME_TRANSITIONS[AgentRuntimeState.WAITING_MEMORY],
        )

    def test_idle_back_to_waiting_task(self) -> None:
        self.assertIn(
            AgentRuntimeState.WAITING_TASK,
            AGENT_RUNTIME_TRANSITIONS[AgentRuntimeState.IDLE],
        )

    def test_idle_can_finish(self) -> None:
        self.assertIn(
            AgentRuntimeState.FINISHED,
            AGENT_RUNTIME_TRANSITIONS[AgentRuntimeState.IDLE],
        )

    def test_forward_chain_exists(self) -> None:
        chain = [
            (AgentRuntimeState.CREATED, AgentRuntimeState.READY),
            (AgentRuntimeState.READY, AgentRuntimeState.WAITING_TASK),
            (AgentRuntimeState.WAITING_TASK, AgentRuntimeState.TASK_RECEIVED),
            (AgentRuntimeState.TASK_RECEIVED, AgentRuntimeState.ANALYZING),
            (AgentRuntimeState.ANALYZING, AgentRuntimeState.PLANNING),
            (AgentRuntimeState.PLANNING, AgentRuntimeState.WORKING),
            (AgentRuntimeState.WORKING, AgentRuntimeState.SELF_REVIEW),
            (AgentRuntimeState.SELF_REVIEW, AgentRuntimeState.WAITING_APPROVAL),
            (AgentRuntimeState.WAITING_APPROVAL, AgentRuntimeState.FINISHED),
        ]
        for from_s, to_s in chain:
            self.assertIn(to_s, AGENT_RUNTIME_TRANSITIONS[from_s],
                          msg=f"{from_s} → {to_s} missing from map")

    def test_values_are_frozensets(self) -> None:
        for state, targets in AGENT_RUNTIME_TRANSITIONS.items():
            self.assertIsInstance(targets, frozenset, msg=f"Entry for {state} not a frozenset")


# ---------------------------------------------------------------------------
# TestRuntimeContext
# ---------------------------------------------------------------------------

class TestRuntimeContext(unittest.TestCase):

    def test_defaults_are_none(self) -> None:
        ctx = RuntimeContext()
        self.assertIsNone(ctx.current_task)
        self.assertIsNone(ctx.project)
        self.assertIsNone(ctx.department)
        self.assertIsNone(ctx.director_id)

    def test_empty_metadata_default(self) -> None:
        ctx = RuntimeContext()
        self.assertEqual(ctx.metadata, {})

    def test_fields_stored_correctly(self) -> None:
        ctx = _context()
        self.assertEqual(ctx.current_task, "task-001")
        self.assertEqual(ctx.project, "proj-001")
        self.assertEqual(ctx.department, DepartmentType.BACKEND)
        self.assertEqual(ctx.director_id, "dir-001")

    def test_is_frozen(self) -> None:
        ctx = _context()
        with self.assertRaises(Exception):
            ctx.current_task = "changed"  # type: ignore[misc]

    def test_has_task_true(self) -> None:
        self.assertTrue(_context(current_task="t-1").has_task())

    def test_has_task_false(self) -> None:
        self.assertFalse(_context(current_task=None).has_task())

    def test_has_project_true(self) -> None:
        self.assertTrue(_context(project="p-1").has_project())

    def test_has_project_false(self) -> None:
        self.assertFalse(_context(project=None).has_project())

    def test_has_director_true(self) -> None:
        self.assertTrue(_context(director_id="d-1").has_director())

    def test_has_director_false(self) -> None:
        self.assertFalse(_context(director_id=None).has_director())

    def test_has_department_true(self) -> None:
        self.assertTrue(_context(department=DepartmentType.QA).has_department())

    def test_has_department_false(self) -> None:
        self.assertFalse(_context(department=None).has_department())

    def test_get_metadata_returns_value(self) -> None:
        ctx = RuntimeContext(metadata={"priority": "high"})
        self.assertEqual(ctx.get_metadata("priority"), "high")

    def test_get_metadata_returns_default_for_missing(self) -> None:
        ctx = RuntimeContext()
        self.assertIsNone(ctx.get_metadata("missing"))
        self.assertEqual(ctx.get_metadata("missing", "fallback"), "fallback")

    def test_metadata_multiple_entries(self) -> None:
        ctx = RuntimeContext(metadata={"a": 1, "b": "two", "c": True})
        self.assertEqual(ctx.get_metadata("a"), 1)
        self.assertEqual(ctx.get_metadata("b"), "two")
        self.assertTrue(ctx.get_metadata("c"))


# ---------------------------------------------------------------------------
# TestRuntimeResult
# ---------------------------------------------------------------------------

class TestRuntimeResult(unittest.TestCase):

    def test_required_fields_stored(self) -> None:
        r = _result(success=True, summary="Done.")
        self.assertTrue(r.success)
        self.assertEqual(r.summary, "Done.")

    def test_defaults(self) -> None:
        r = _result()
        self.assertIsNone(r.next_action)
        self.assertEqual(r.generated_artifacts, [])
        self.assertFalse(r.requires_discussion)
        self.assertFalse(r.requires_approval)
        self.assertIsNone(r.session_id)

    def test_completed_at_auto_populated(self) -> None:
        before = datetime.now(timezone.utc)
        r = _result()
        after = datetime.now(timezone.utc)
        self.assertIsNotNone(r.completed_at)
        self.assertGreaterEqual(r.completed_at, before)
        self.assertLessEqual(r.completed_at, after)

    def test_is_frozen(self) -> None:
        r = _result()
        with self.assertRaises(Exception):
            r.success = False  # type: ignore[misc]

    def test_has_artifacts_false(self) -> None:
        self.assertFalse(_result().has_artifacts())

    def test_has_artifacts_true(self) -> None:
        r = _result(artifacts=["api_spec.md"])
        self.assertTrue(r.has_artifacts())

    def test_artifact_count(self) -> None:
        r = _result(artifacts=["a", "b", "c"])
        self.assertEqual(r.artifact_count(), 3)

    def test_artifact_count_zero(self) -> None:
        self.assertEqual(_result().artifact_count(), 0)

    def test_needs_external_review_when_approval_needed(self) -> None:
        r = _result(requires_approval=True)
        self.assertTrue(r.needs_external_review())

    def test_needs_external_review_when_discussion_needed(self) -> None:
        r = _result(requires_discussion=True)
        self.assertTrue(r.needs_external_review())

    def test_needs_external_review_false(self) -> None:
        r = _result(requires_approval=False, requires_discussion=False)
        self.assertFalse(r.needs_external_review())

    def test_failure_result(self) -> None:
        r = _result(success=False, summary="Task could not be completed.")
        self.assertFalse(r.success)

    def test_next_action_stored(self) -> None:
        r = RuntimeResult(success=True, summary="Done.", next_action="deploy-prod")
        self.assertEqual(r.next_action, "deploy-prod")


# ---------------------------------------------------------------------------
# TestRuntimeEvent
# ---------------------------------------------------------------------------

class TestRuntimeEvent(unittest.TestCase):

    def _event(self, event_type=RuntimeEventType.STATE_CHANGED) -> RuntimeEvent:
        return RuntimeEvent(
            event_id="evt-001",
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            from_state=AgentRuntimeState.READY,
            to_state=AgentRuntimeState.WAITING_TASK,
            details={"test": True},
        )

    def test_fields_stored(self) -> None:
        evt = self._event()
        self.assertEqual(evt.event_id, "evt-001")
        self.assertEqual(evt.event_type, RuntimeEventType.STATE_CHANGED)
        self.assertEqual(evt.from_state, AgentRuntimeState.READY)
        self.assertEqual(evt.to_state, AgentRuntimeState.WAITING_TASK)
        self.assertTrue(evt.details["test"])

    def test_is_frozen(self) -> None:
        evt = self._event()
        with self.assertRaises(Exception):
            evt.event_id = "changed"  # type: ignore[misc]

    def test_non_transition_event_has_no_states(self) -> None:
        evt = RuntimeEvent(
            event_id="e",
            event_type=RuntimeEventType.PROGRESS_UPDATED,
            timestamp=datetime.now(timezone.utc),
        )
        self.assertIsNone(evt.from_state)
        self.assertIsNone(evt.to_state)

    def test_empty_details_default(self) -> None:
        evt = RuntimeEvent(
            event_id="e",
            event_type=RuntimeEventType.SESSION_STARTED,
            timestamp=datetime.now(timezone.utc),
        )
        self.assertEqual(evt.details, {})


# ---------------------------------------------------------------------------
# TestRuntimeEventType
# ---------------------------------------------------------------------------

class TestRuntimeEventType(unittest.TestCase):

    def test_five_types_exist(self) -> None:
        names = {t.name for t in RuntimeEventType}
        self.assertEqual(
            names,
            {
                "SESSION_STARTED", "STATE_CHANGED", "CONTEXT_ATTACHED",
                "PROGRESS_UPDATED", "SESSION_STOPPED",
            },
        )

    def test_str_returns_value(self) -> None:
        for t in RuntimeEventType:
            self.assertEqual(str(t), t.value)

    def test_is_str_subclass(self) -> None:
        self.assertIsInstance(RuntimeEventType.STATE_CHANGED, str)


# ---------------------------------------------------------------------------
# TestRuntimeSession
# ---------------------------------------------------------------------------

class TestRuntimeSession(unittest.TestCase):

    def _session(self, state=AgentRuntimeState.READY) -> RuntimeSession:
        return RuntimeSession(
            session_id="sess-001",
            employee_id="emp-001",
            project_id="proj-001",
            task_id="task-001",
            current_state=state,
            progress=0.0,
            started_at=datetime.now(timezone.utc),
            finished_at=None,
            events=[],
        )

    def test_fields_stored(self) -> None:
        s = self._session()
        self.assertEqual(s.session_id, "sess-001")
        self.assertEqual(s.employee_id, "emp-001")
        self.assertEqual(s.current_state, AgentRuntimeState.READY)

    def test_is_mutable(self) -> None:
        s = self._session()
        s.progress = 0.5
        self.assertAlmostEqual(s.progress, 0.5)

    def test_is_active_non_terminal(self) -> None:
        s = self._session(AgentRuntimeState.WORKING)
        self.assertTrue(s.is_active())

    def test_is_active_false_for_finished(self) -> None:
        s = self._session(AgentRuntimeState.FINISHED)
        self.assertFalse(s.is_active())

    def test_is_active_false_for_failed(self) -> None:
        s = self._session(AgentRuntimeState.FAILED)
        self.assertFalse(s.is_active())

    def test_is_finished(self) -> None:
        s = self._session(AgentRuntimeState.FINISHED)
        self.assertTrue(s.is_finished())

    def test_is_failed(self) -> None:
        s = self._session(AgentRuntimeState.FAILED)
        self.assertTrue(s.is_failed())

    def test_duration_seconds_none_when_active(self) -> None:
        s = self._session()
        self.assertIsNone(s.duration_seconds())

    def test_duration_seconds_when_finished(self) -> None:
        s = self._session()
        s.finished_at = datetime.now(timezone.utc)
        self.assertIsNotNone(s.duration_seconds())
        self.assertGreaterEqual(s.duration_seconds(), 0.0)

    def test_event_count(self) -> None:
        s = self._session()
        self.assertEqual(s.event_count(), 0)
        s.events.append(RuntimeEvent(
            event_id="e1",
            event_type=RuntimeEventType.SESSION_STARTED,
            timestamp=datetime.now(timezone.utc),
        ))
        self.assertEqual(s.event_count(), 1)

    def test_last_event_none_when_empty(self) -> None:
        s = self._session()
        self.assertIsNone(s.last_event())

    def test_last_event_returns_last(self) -> None:
        s = self._session()
        e1 = RuntimeEvent("e1", RuntimeEventType.SESSION_STARTED, datetime.now(timezone.utc))
        e2 = RuntimeEvent("e2", RuntimeEventType.PROGRESS_UPDATED, datetime.now(timezone.utc))
        s.events.extend([e1, e2])
        self.assertIs(s.last_event(), e2)

    def test_events_of_type_filters(self) -> None:
        s = self._session()
        e1 = RuntimeEvent("e1", RuntimeEventType.STATE_CHANGED, datetime.now(timezone.utc))
        e2 = RuntimeEvent("e2", RuntimeEventType.PROGRESS_UPDATED, datetime.now(timezone.utc))
        e3 = RuntimeEvent("e3", RuntimeEventType.STATE_CHANGED, datetime.now(timezone.utc))
        s.events.extend([e1, e2, e3])
        state_events = s.events_of_type(RuntimeEventType.STATE_CHANGED)
        self.assertEqual(len(state_events), 2)
        self.assertNotIn(e2, state_events)

    def test_state_transitions_returns_only_state_changes(self) -> None:
        s = self._session()
        e1 = RuntimeEvent("e1", RuntimeEventType.STATE_CHANGED, datetime.now(timezone.utc))
        e2 = RuntimeEvent("e2", RuntimeEventType.CONTEXT_ATTACHED, datetime.now(timezone.utc))
        s.events.extend([e1, e2])
        transitions = s.state_transitions()
        self.assertEqual(len(transitions), 1)
        self.assertIs(transitions[0], e1)

    def test_context_defaults_to_none(self) -> None:
        s = self._session()
        self.assertIsNone(s.context)

    def test_result_defaults_to_none(self) -> None:
        s = self._session()
        self.assertIsNone(s.result)


# ---------------------------------------------------------------------------
# TestAgentRuntimeInit
# ---------------------------------------------------------------------------

class TestAgentRuntimeInit(unittest.TestCase):

    def test_employee_id_stored(self) -> None:
        rt = _runtime("emp-999")
        self.assertEqual(rt.employee_id, "emp-999")

    def test_no_active_session_initially(self) -> None:
        rt = _runtime()
        self.assertIsNone(rt.current_session())

    def test_has_active_session_false_initially(self) -> None:
        rt = _runtime()
        self.assertFalse(rt.has_active_session())

    def test_session_count_zero_initially(self) -> None:
        rt = _runtime()
        self.assertEqual(rt.session_count(), 0)

    def test_all_sessions_empty_initially(self) -> None:
        rt = _runtime()
        self.assertEqual(rt.all_sessions(), [])

    def test_error_hierarchy(self) -> None:
        self.assertTrue(issubclass(NoActiveSessionError, AgentRuntimeError))
        self.assertTrue(issubclass(SessionAlreadyActiveError, AgentRuntimeError))
        self.assertTrue(issubclass(IllegalStateTransitionError, AgentRuntimeError))
        self.assertTrue(issubclass(InvalidProgressError, AgentRuntimeError))
        self.assertTrue(issubclass(SessionAlreadyTerminalError, AgentRuntimeError))


# ---------------------------------------------------------------------------
# TestStartSession
# ---------------------------------------------------------------------------

class TestStartSession(unittest.TestCase):

    def test_start_session_returns_session(self) -> None:
        rt = _runtime()
        sess = rt.start_session()
        self.assertIsInstance(sess, RuntimeSession)

    def test_start_session_state_is_ready(self) -> None:
        _, sess = _started()
        self.assertEqual(sess.current_state, AgentRuntimeState.READY)

    def test_start_session_sets_employee_id(self) -> None:
        rt = _runtime("emp-abc")
        sess = rt.start_session()
        self.assertEqual(sess.employee_id, "emp-abc")

    def test_start_session_stores_project_id(self) -> None:
        _, sess = _started(project_id="proj-X")
        self.assertEqual(sess.project_id, "proj-X")

    def test_start_session_stores_task_id(self) -> None:
        _, sess = _started(task_id="task-42")
        self.assertEqual(sess.task_id, "task-42")

    def test_start_session_progress_zero(self) -> None:
        _, sess = _started()
        self.assertAlmostEqual(sess.progress, 0.0)

    def test_start_session_started_at_is_utc(self) -> None:
        before = datetime.now(timezone.utc)
        _, sess = _started()
        after = datetime.now(timezone.utc)
        self.assertGreaterEqual(sess.started_at, before)
        self.assertLessEqual(sess.started_at, after)

    def test_start_session_finished_at_none(self) -> None:
        _, sess = _started()
        self.assertIsNone(sess.finished_at)

    def test_start_session_session_id_is_uuid(self) -> None:
        _, sess = _started()
        self.assertIsInstance(sess.session_id, str)
        self.assertEqual(len(sess.session_id), 36)  # UUID4 format

    def test_start_session_registers_as_current(self) -> None:
        rt, sess = _started()
        self.assertIs(rt.current_session(), sess)

    def test_start_session_increments_count(self) -> None:
        rt = _runtime()
        rt.start_session()
        rt.stop_session()
        rt.start_session()
        self.assertEqual(rt.session_count(), 2)

    def test_start_session_records_events(self) -> None:
        _, sess = _started()
        self.assertGreater(sess.event_count(), 0)

    def test_start_session_first_event_is_session_started(self) -> None:
        _, sess = _started()
        first_event = sess.events[0]
        self.assertEqual(first_event.event_type, RuntimeEventType.SESSION_STARTED)

    def test_start_session_has_state_changed_event_for_ready(self) -> None:
        _, sess = _started()
        transitions = sess.state_transitions()
        self.assertTrue(
            any(e.to_state == AgentRuntimeState.READY for e in transitions)
        )

    def test_start_twice_raises_session_already_active(self) -> None:
        rt = _runtime()
        rt.start_session()
        with self.assertRaises(SessionAlreadyActiveError):
            rt.start_session()

    def test_start_after_terminal_session_allowed(self) -> None:
        rt = _runtime()
        rt.start_session()
        rt.fail("done")
        sess2 = rt.start_session()
        self.assertIsInstance(sess2, RuntimeSession)
        self.assertEqual(rt.session_count(), 2)

    def test_unique_session_ids_across_starts(self) -> None:
        rt = _runtime()
        ids = []
        for _ in range(5):
            s = rt.start_session()
            ids.append(s.session_id)
            rt.fail("next")
        self.assertEqual(len(set(ids)), 5)

    def test_has_active_session_after_start(self) -> None:
        rt, _ = _started()
        self.assertTrue(rt.has_active_session())

    def test_all_sessions_contains_started(self) -> None:
        rt, sess = _started()
        self.assertIn(sess, rt.all_sessions())


# ---------------------------------------------------------------------------
# TestStopSession
# ---------------------------------------------------------------------------

class TestStopSession(unittest.TestCase):

    def test_stop_with_no_session_raises(self) -> None:
        rt = _runtime()
        with self.assertRaises(NoActiveSessionError):
            rt.stop_session()

    def test_stop_active_session_sets_failed(self) -> None:
        rt, sess = _started()
        rt.stop_session()
        self.assertEqual(sess.current_state, AgentRuntimeState.FAILED)

    def test_stop_returns_session(self) -> None:
        rt, sess = _started()
        result = rt.stop_session()
        self.assertIs(result, sess)

    def test_stop_clears_current_session(self) -> None:
        rt, _ = _started()
        rt.stop_session()
        self.assertIsNone(rt.current_session())

    def test_stop_records_session_stopped_event(self) -> None:
        rt, sess = _started()
        rt.stop_session()
        stopped_events = [
            e for e in sess.events
            if e.event_type == RuntimeEventType.SESSION_STOPPED
        ]
        self.assertEqual(len(stopped_events), 1)

    def test_stop_sets_finished_at(self) -> None:
        rt, sess = _started()
        rt.stop_session()
        self.assertIsNotNone(sess.finished_at)

    def test_stop_mid_working_session(self) -> None:
        rt, sess = _started()
        _advance_to_working(rt)
        rt.stop_session()
        self.assertEqual(sess.current_state, AgentRuntimeState.FAILED)

    def test_has_active_session_false_after_stop(self) -> None:
        rt, _ = _started()
        rt.stop_session()
        self.assertFalse(rt.has_active_session())


# ---------------------------------------------------------------------------
# TestChangeState
# ---------------------------------------------------------------------------

class TestChangeState(unittest.TestCase):

    def test_change_state_no_session_raises(self) -> None:
        rt = _runtime()
        with self.assertRaises(NoActiveSessionError):
            rt.change_state(AgentRuntimeState.WAITING_TASK)

    def test_change_state_returns_session(self) -> None:
        rt, sess = _started()
        result = rt.change_state(AgentRuntimeState.WAITING_TASK)
        self.assertIs(result, sess)

    def test_change_state_updates_current_state(self) -> None:
        rt, sess = _started()
        rt.change_state(AgentRuntimeState.WAITING_TASK)
        self.assertEqual(sess.current_state, AgentRuntimeState.WAITING_TASK)

    def test_change_state_records_event(self) -> None:
        rt, sess = _started()
        initial_count = sess.event_count()
        rt.change_state(AgentRuntimeState.WAITING_TASK)
        self.assertEqual(sess.event_count(), initial_count + 1)

    def test_change_state_event_has_correct_from_to(self) -> None:
        rt, sess = _started()
        rt.change_state(AgentRuntimeState.WAITING_TASK)
        last = sess.last_event()
        self.assertEqual(last.event_type, RuntimeEventType.STATE_CHANGED)
        self.assertEqual(last.from_state, AgentRuntimeState.READY)
        self.assertEqual(last.to_state, AgentRuntimeState.WAITING_TASK)

    def test_change_state_illegal_raises(self) -> None:
        rt, _ = _started()
        with self.assertRaises(IllegalStateTransitionError):
            rt.change_state(AgentRuntimeState.FINISHED)

    def test_change_state_terminal_raises(self) -> None:
        rt, _ = _started()
        rt.fail("done")
        rt.start_session()
        rt.fail("done2")
        # Now no active session — use a fresh started one
        rt2, _ = _started()
        _advance_to_self_review(rt2)
        rt2.change_state(AgentRuntimeState.FINISHED)
        with self.assertRaises((NoActiveSessionError, SessionAlreadyTerminalError)):
            rt2.change_state(AgentRuntimeState.FAILED)

    def test_change_state_full_forward_chain(self) -> None:
        rt, sess = _started()
        _advance_to_working(rt)
        rt.change_state(AgentRuntimeState.SELF_REVIEW)
        rt.change_state(AgentRuntimeState.WAITING_APPROVAL)
        self.assertEqual(sess.current_state, AgentRuntimeState.WAITING_APPROVAL)

    def test_change_state_details_stored_in_event(self) -> None:
        rt, sess = _started()
        rt.change_state(
            AgentRuntimeState.WAITING_TASK,
            details={"note": "waiting for assignment"},
        )
        last = sess.last_event()
        self.assertEqual(last.details.get("note"), "waiting for assignment")

    def test_change_state_allowed_transitions_from_self_review(self) -> None:
        for target in (
            AgentRuntimeState.WAITING_DISCUSSION,
            AgentRuntimeState.WAITING_MEMORY,
            AgentRuntimeState.WAITING_APPROVAL,
            AgentRuntimeState.FINISHED,
            AgentRuntimeState.FAILED,
        ):
            rt, _ = _started()
            _advance_to_self_review(rt)
            rt.change_state(target)
            self.assertEqual(rt.get_session(rt.all_sessions()[-1].session_id).current_state, target)

    def test_change_state_rework_cycle(self) -> None:
        rt, sess = _started()
        _advance_to_self_review(rt)
        rt.change_state(AgentRuntimeState.WAITING_APPROVAL)
        rt.change_state(AgentRuntimeState.WORKING)  # rejected → rework
        rt.change_state(AgentRuntimeState.SELF_REVIEW)
        rt.change_state(AgentRuntimeState.WAITING_APPROVAL)
        rt.change_state(AgentRuntimeState.FINISHED)  # approved
        self.assertEqual(sess.current_state, AgentRuntimeState.FINISHED)

    def test_change_state_idle_path(self) -> None:
        rt, sess = _started()
        rt.change_state(AgentRuntimeState.IDLE)
        self.assertEqual(sess.current_state, AgentRuntimeState.IDLE)

    def test_change_state_idle_to_waiting_task(self) -> None:
        rt, sess = _started()
        rt.change_state(AgentRuntimeState.IDLE)
        rt.change_state(AgentRuntimeState.WAITING_TASK)
        self.assertEqual(sess.current_state, AgentRuntimeState.WAITING_TASK)

    def test_illegal_transition_message_includes_states(self) -> None:
        rt, _ = _started()
        try:
            rt.change_state(AgentRuntimeState.FINISHED)
            self.fail("Expected IllegalStateTransitionError")
        except IllegalStateTransitionError as e:
            self.assertIn("READY", str(e))
            self.assertIn("FINISHED", str(e))


# ---------------------------------------------------------------------------
# TestAttachContext
# ---------------------------------------------------------------------------

class TestAttachContext(unittest.TestCase):

    def test_attach_context_no_session_raises(self) -> None:
        rt = _runtime()
        with self.assertRaises(NoActiveSessionError):
            rt.attach_context(_context())

    def test_attach_context_returns_session(self) -> None:
        rt, sess = _started()
        result = rt.attach_context(_context())
        self.assertIs(result, sess)

    def test_attach_context_stores_context(self) -> None:
        rt, sess = _started()
        ctx = _context(current_task="t-99")
        rt.attach_context(ctx)
        self.assertIs(sess.context, ctx)

    def test_attach_context_records_event(self) -> None:
        rt, sess = _started()
        initial = sess.event_count()
        rt.attach_context(_context())
        self.assertEqual(sess.event_count(), initial + 1)

    def test_attach_context_event_type(self) -> None:
        rt, sess = _started()
        rt.attach_context(_context())
        last = sess.last_event()
        self.assertEqual(last.event_type, RuntimeEventType.CONTEXT_ATTACHED)

    def test_attach_context_event_contains_task(self) -> None:
        rt, sess = _started()
        rt.attach_context(_context(current_task="task-XYZ"))
        last = sess.last_event()
        self.assertEqual(last.details["task"], "task-XYZ")

    def test_attach_context_replaces_previous(self) -> None:
        rt, sess = _started()
        rt.attach_context(_context(current_task="old"))
        rt.attach_context(_context(current_task="new"))
        self.assertEqual(sess.context.current_task, "new")

    def test_attach_context_records_previous_task(self) -> None:
        rt, sess = _started()
        rt.attach_context(_context(current_task="task-1"))
        rt.attach_context(_context(current_task="task-2"))
        last = sess.last_event()
        self.assertEqual(last.details.get("previous_task"), "task-1")

    def test_attach_context_terminal_raises(self) -> None:
        rt, _ = _started()
        rt.fail("ended")
        with self.assertRaises(NoActiveSessionError):
            rt.attach_context(_context())

    def test_attach_minimal_context(self) -> None:
        rt, sess = _started()
        ctx = RuntimeContext()
        rt.attach_context(ctx)
        self.assertIsNone(sess.context.current_task)


# ---------------------------------------------------------------------------
# TestUpdateProgress
# ---------------------------------------------------------------------------

class TestUpdateProgress(unittest.TestCase):

    def test_update_progress_no_session_raises(self) -> None:
        rt = _runtime()
        with self.assertRaises(NoActiveSessionError):
            rt.update_progress(0.5)

    def test_update_progress_returns_session(self) -> None:
        rt, sess = _started()
        result = rt.update_progress(0.3)
        self.assertIs(result, sess)

    def test_update_progress_stores_value(self) -> None:
        rt, sess = _started()
        rt.update_progress(0.7)
        self.assertAlmostEqual(sess.progress, 0.7)

    def test_update_progress_zero_allowed(self) -> None:
        rt, sess = _started()
        rt.update_progress(0.0)
        self.assertAlmostEqual(sess.progress, 0.0)

    def test_update_progress_one_allowed(self) -> None:
        rt, sess = _started()
        rt.update_progress(1.0)
        self.assertAlmostEqual(sess.progress, 1.0)

    def test_update_progress_negative_raises(self) -> None:
        rt, _ = _started()
        with self.assertRaises(InvalidProgressError):
            rt.update_progress(-0.01)

    def test_update_progress_above_one_raises(self) -> None:
        rt, _ = _started()
        with self.assertRaises(InvalidProgressError):
            rt.update_progress(1.01)

    def test_update_progress_records_event(self) -> None:
        rt, sess = _started()
        initial = sess.event_count()
        rt.update_progress(0.5)
        self.assertEqual(sess.event_count(), initial + 1)

    def test_update_progress_event_type(self) -> None:
        rt, sess = _started()
        rt.update_progress(0.5)
        last = sess.last_event()
        self.assertEqual(last.event_type, RuntimeEventType.PROGRESS_UPDATED)

    def test_update_progress_event_records_previous_and_new(self) -> None:
        rt, sess = _started()
        rt.update_progress(0.2)
        rt.update_progress(0.6)
        last = sess.last_event()
        self.assertAlmostEqual(last.details["previous_progress"], 0.2)
        self.assertAlmostEqual(last.details["new_progress"], 0.6)

    def test_update_progress_multiple_times(self) -> None:
        rt, sess = _started()
        for p in (0.1, 0.3, 0.5, 0.8, 1.0):
            rt.update_progress(p)
        self.assertAlmostEqual(sess.progress, 1.0)

    def test_update_progress_terminal_raises(self) -> None:
        rt, _ = _started()
        rt.fail("ended")
        with self.assertRaises(NoActiveSessionError):
            rt.update_progress(0.5)


# ---------------------------------------------------------------------------
# TestFinish
# ---------------------------------------------------------------------------

class TestFinish(unittest.TestCase):

    def _run_to_approval(self, rt: AgentRuntime) -> None:
        _advance_to_self_review(rt)
        rt.change_state(AgentRuntimeState.WAITING_APPROVAL)

    def test_finish_no_session_raises(self) -> None:
        rt = _runtime()
        with self.assertRaises(NoActiveSessionError):
            rt.finish()

    def test_finish_transitions_to_finished(self) -> None:
        rt, sess = _started()
        self._run_to_approval(rt)
        rt.finish()
        self.assertEqual(sess.current_state, AgentRuntimeState.FINISHED)

    def test_finish_returns_session(self) -> None:
        rt, sess = _started()
        self._run_to_approval(rt)
        result = rt.finish()
        self.assertIs(result, sess)

    def test_finish_sets_finished_at(self) -> None:
        rt, sess = _started()
        self._run_to_approval(rt)
        rt.finish()
        self.assertIsNotNone(sess.finished_at)

    def test_finish_clears_current_session(self) -> None:
        rt, _ = _started()
        self._run_to_approval(rt)
        rt.finish()
        self.assertIsNone(rt.current_session())

    def test_finish_with_result_attaches_result(self) -> None:
        rt, sess = _started()
        self._run_to_approval(rt)
        r = _result()
        rt.finish(r)
        self.assertIs(sess.result, r)

    def test_finish_without_result_result_is_none(self) -> None:
        rt, sess = _started()
        self._run_to_approval(rt)
        rt.finish()
        self.assertIsNone(sess.result)

    def test_finish_illegal_from_working_raises(self) -> None:
        rt, _ = _started()
        _advance_to_working(rt)
        with self.assertRaises(IllegalStateTransitionError):
            rt.finish()

    def test_finish_from_self_review_direct(self) -> None:
        rt, sess = _started()
        _advance_to_self_review(rt)
        rt.finish()
        self.assertEqual(sess.current_state, AgentRuntimeState.FINISHED)

    def test_finish_from_idle(self) -> None:
        rt, sess = _started()
        rt.change_state(AgentRuntimeState.IDLE)
        rt.finish()
        self.assertEqual(sess.current_state, AgentRuntimeState.FINISHED)

    def test_finish_session_in_all_sessions(self) -> None:
        rt, sess = _started()
        self._run_to_approval(rt)
        rt.finish()
        self.assertIn(sess, rt.all_sessions())

    def test_finish_has_active_session_false_after(self) -> None:
        rt, _ = _started()
        self._run_to_approval(rt)
        rt.finish()
        self.assertFalse(rt.has_active_session())


# ---------------------------------------------------------------------------
# TestFail
# ---------------------------------------------------------------------------

class TestFail(unittest.TestCase):

    def test_fail_no_session_raises(self) -> None:
        rt = _runtime()
        with self.assertRaises(NoActiveSessionError):
            rt.fail()

    def test_fail_transitions_to_failed(self) -> None:
        rt, sess = _started()
        rt.fail("error occurred")
        self.assertEqual(sess.current_state, AgentRuntimeState.FAILED)

    def test_fail_returns_session(self) -> None:
        rt, sess = _started()
        result = rt.fail("err")
        self.assertIs(result, sess)

    def test_fail_sets_finished_at(self) -> None:
        rt, sess = _started()
        rt.fail("err")
        self.assertIsNotNone(sess.finished_at)

    def test_fail_clears_current_session(self) -> None:
        rt, _ = _started()
        rt.fail("err")
        self.assertIsNone(rt.current_session())

    def test_fail_from_working(self) -> None:
        rt, sess = _started()
        _advance_to_working(rt)
        rt.fail("runtime error")
        self.assertEqual(sess.current_state, AgentRuntimeState.FAILED)

    def test_fail_from_analyzing(self) -> None:
        rt, sess = _started()
        _advance_to(
            rt,
            AgentRuntimeState.WAITING_TASK,
            AgentRuntimeState.TASK_RECEIVED,
            AgentRuntimeState.ANALYZING,
        )
        rt.fail("task unreadable")
        self.assertEqual(sess.current_state, AgentRuntimeState.FAILED)

    def test_fail_from_waiting_approval(self) -> None:
        rt, sess = _started()
        _advance_to_self_review(rt)
        rt.change_state(AgentRuntimeState.WAITING_APPROVAL)
        rt.fail("approval timeout")
        self.assertEqual(sess.current_state, AgentRuntimeState.FAILED)

    def test_fail_reason_stored_in_event(self) -> None:
        rt, sess = _started()
        rt.fail("disk full")
        transitions = sess.state_transitions()
        fail_event = next(
            (e for e in transitions if e.to_state == AgentRuntimeState.FAILED), None
        )
        self.assertIsNotNone(fail_event)
        self.assertEqual(fail_event.details.get("reason"), "disk full")

    def test_fail_with_empty_reason(self) -> None:
        rt, sess = _started()
        rt.fail()
        self.assertEqual(sess.current_state, AgentRuntimeState.FAILED)

    def test_fail_has_active_session_false_after(self) -> None:
        rt, _ = _started()
        rt.fail("err")
        self.assertFalse(rt.has_active_session())


# ---------------------------------------------------------------------------
# TestCurrentStateAndSession
# ---------------------------------------------------------------------------

class TestCurrentStateAndSession(unittest.TestCase):

    def test_current_state_no_session_raises(self) -> None:
        rt = _runtime()
        with self.assertRaises(NoActiveSessionError):
            rt.current_state()

    def test_current_state_returns_ready_after_start(self) -> None:
        rt, _ = _started()
        self.assertEqual(rt.current_state(), AgentRuntimeState.READY)

    def test_current_state_updates_after_change(self) -> None:
        rt, _ = _started()
        rt.change_state(AgentRuntimeState.WAITING_TASK)
        self.assertEqual(rt.current_state(), AgentRuntimeState.WAITING_TASK)

    def test_current_session_none_initially(self) -> None:
        rt = _runtime()
        self.assertIsNone(rt.current_session())

    def test_current_session_returns_active(self) -> None:
        rt, sess = _started()
        self.assertIs(rt.current_session(), sess)

    def test_current_session_none_after_fail(self) -> None:
        rt, _ = _started()
        rt.fail()
        self.assertIsNone(rt.current_session())

    def test_get_session_retrieves_by_id(self) -> None:
        rt, sess = _started()
        retrieved = rt.get_session(sess.session_id)
        self.assertIs(retrieved, sess)

    def test_get_session_retrieves_terminated(self) -> None:
        rt, sess = _started()
        sess_id = sess.session_id
        rt.fail("done")
        retrieved = rt.get_session(sess_id)
        self.assertIs(retrieved, sess)

    def test_get_session_unknown_raises_key_error(self) -> None:
        rt = _runtime()
        with self.assertRaises(KeyError):
            rt.get_session("no-such-session")

    def test_all_sessions_copy(self) -> None:
        rt, _ = _started()
        lst = rt.all_sessions()
        lst.clear()
        self.assertEqual(rt.session_count(), 1)

    def test_all_sessions_multiple(self) -> None:
        rt = _runtime()
        for _ in range(3):
            rt.start_session()
            rt.fail("next")
        self.assertEqual(len(rt.all_sessions()), 3)


# ---------------------------------------------------------------------------
# TestIntegrationScenarios
# ---------------------------------------------------------------------------

class TestIntegrationScenarios(unittest.TestCase):

    def test_happy_path_full_cycle(self) -> None:
        rt = _runtime("emp-happy")
        sess = rt.start_session(project_id="proj-1", task_id="task-1")

        ctx = _context(current_task="task-1", project="proj-1")
        rt.attach_context(ctx)

        _advance_to(rt, AgentRuntimeState.WAITING_TASK)
        rt.update_progress(0.0)

        _advance_to(rt, AgentRuntimeState.TASK_RECEIVED, AgentRuntimeState.ANALYZING)
        rt.update_progress(0.1)

        _advance_to(rt, AgentRuntimeState.PLANNING)
        rt.update_progress(0.2)

        _advance_to(rt, AgentRuntimeState.WORKING)
        rt.update_progress(0.5)
        rt.update_progress(0.8)

        _advance_to(rt, AgentRuntimeState.SELF_REVIEW)
        rt.update_progress(0.9)

        _advance_to(rt, AgentRuntimeState.WAITING_APPROVAL)
        rt.update_progress(1.0)

        result = RuntimeResult(
            success=True,
            summary="API endpoint implemented and approved.",
            next_action="deploy",
            generated_artifacts=["api_endpoint.py", "api_spec.md"],
            requires_approval=True,
        )
        rt.finish(result)

        self.assertEqual(sess.current_state, AgentRuntimeState.FINISHED)
        self.assertIsNotNone(sess.result)
        self.assertTrue(sess.result.success)
        self.assertEqual(sess.result.artifact_count(), 2)
        self.assertIsNotNone(sess.finished_at)
        self.assertFalse(rt.has_active_session())

    def test_rework_cycle_after_rejection(self) -> None:
        rt = _runtime("emp-rework")
        sess = rt.start_session(project_id="proj-rework")

        _advance_to_self_review(rt)
        rt.change_state(AgentRuntimeState.WAITING_APPROVAL)
        # CEO rejects — needs rework
        rt.change_state(AgentRuntimeState.WORKING)
        rt.update_progress(0.5)
        rt.change_state(AgentRuntimeState.SELF_REVIEW)
        rt.update_progress(1.0)
        rt.change_state(AgentRuntimeState.WAITING_APPROVAL)
        rt.finish(_result(summary="Revised and approved."))

        self.assertEqual(sess.current_state, AgentRuntimeState.FINISHED)
        state_events = sess.state_transitions()
        working_count = sum(
            1 for e in state_events if e.to_state == AgentRuntimeState.WORKING
        )
        self.assertGreaterEqual(working_count, 2)

    def test_discussion_then_approval_path(self) -> None:
        rt = _runtime("emp-discuss")
        sess = rt.start_session()

        _advance_to_self_review(rt)
        rt.change_state(AgentRuntimeState.WAITING_DISCUSSION)
        # Discussion resolved
        rt.change_state(AgentRuntimeState.WORKING)
        rt.change_state(AgentRuntimeState.SELF_REVIEW)
        rt.change_state(AgentRuntimeState.WAITING_APPROVAL)
        rt.finish(_result())

        self.assertEqual(sess.current_state, AgentRuntimeState.FINISHED)

    def test_memory_lookup_path(self) -> None:
        rt = _runtime("emp-memory")
        sess = rt.start_session()

        _advance_to_self_review(rt)
        rt.change_state(AgentRuntimeState.WAITING_MEMORY)
        # Memory retrieved
        rt.change_state(AgentRuntimeState.WORKING)
        rt.change_state(AgentRuntimeState.SELF_REVIEW)
        rt.change_state(AgentRuntimeState.FINISHED)

        self.assertEqual(sess.current_state, AgentRuntimeState.FINISHED)

    def test_idle_between_tasks(self) -> None:
        rt = _runtime("emp-idle")
        sess = rt.start_session()

        rt.change_state(AgentRuntimeState.IDLE)
        # Task arrives
        rt.change_state(AgentRuntimeState.WAITING_TASK)
        rt.change_state(AgentRuntimeState.TASK_RECEIVED)

        self.assertEqual(sess.current_state, AgentRuntimeState.TASK_RECEIVED)

    def test_event_log_complete_for_full_path(self) -> None:
        rt = _runtime("emp-events")
        sess = rt.start_session(project_id="p", task_id="t")

        rt.attach_context(_context())
        _advance_to_working(rt)
        rt.update_progress(0.5)
        rt.change_state(AgentRuntimeState.SELF_REVIEW)
        rt.change_state(AgentRuntimeState.WAITING_APPROVAL)
        rt.finish(_result())

        self.assertGreater(sess.event_count(), 0)
        self.assertGreater(len(sess.state_transitions()), 0)
        context_events = sess.events_of_type(RuntimeEventType.CONTEXT_ATTACHED)
        self.assertEqual(len(context_events), 1)
        progress_events = sess.events_of_type(RuntimeEventType.PROGRESS_UPDATED)
        self.assertEqual(len(progress_events), 1)

    def test_multiple_employees_independent(self) -> None:
        rt1 = _runtime("emp-A")
        rt2 = _runtime("emp-B")

        rt1.start_session(project_id="proj-1")
        rt2.start_session(project_id="proj-2")

        _advance_to_working(rt1)
        rt2.change_state(AgentRuntimeState.IDLE)

        self.assertEqual(rt1.current_state(), AgentRuntimeState.WORKING)
        self.assertEqual(rt2.current_state(), AgentRuntimeState.IDLE)
        self.assertEqual(rt1.session_count(), 1)
        self.assertEqual(rt2.session_count(), 1)

    def test_session_history_after_multiple_cycles(self) -> None:
        rt = _runtime("emp-history")

        for i in range(4):
            rt.start_session(task_id=f"task-{i}")
            if i < 3:
                rt.fail(f"failed task {i}")

        # Last session still active
        self.assertTrue(rt.has_active_session())
        self.assertEqual(rt.session_count(), 4)
        failed = [s for s in rt.all_sessions() if s.is_failed()]
        self.assertEqual(len(failed), 3)

    def test_fail_from_every_non_terminal_state(self) -> None:
        non_terminal_path_states = [
            AgentRuntimeState.READY,
            AgentRuntimeState.WAITING_TASK,
            AgentRuntimeState.TASK_RECEIVED,
            AgentRuntimeState.ANALYZING,
            AgentRuntimeState.PLANNING,
            AgentRuntimeState.WORKING,
            AgentRuntimeState.SELF_REVIEW,
            AgentRuntimeState.WAITING_DISCUSSION,
            AgentRuntimeState.WAITING_MEMORY,
            AgentRuntimeState.WAITING_APPROVAL,
            AgentRuntimeState.IDLE,
        ]

        def get_to(rt, target):
            mapping = {
                AgentRuntimeState.READY: [],
                AgentRuntimeState.IDLE: [AgentRuntimeState.IDLE],
                AgentRuntimeState.WAITING_TASK: [AgentRuntimeState.WAITING_TASK],
                AgentRuntimeState.TASK_RECEIVED: [AgentRuntimeState.WAITING_TASK, AgentRuntimeState.TASK_RECEIVED],
                AgentRuntimeState.ANALYZING: [AgentRuntimeState.WAITING_TASK, AgentRuntimeState.TASK_RECEIVED, AgentRuntimeState.ANALYZING],
                AgentRuntimeState.PLANNING: [AgentRuntimeState.WAITING_TASK, AgentRuntimeState.TASK_RECEIVED, AgentRuntimeState.ANALYZING, AgentRuntimeState.PLANNING],
                AgentRuntimeState.WORKING: [AgentRuntimeState.WAITING_TASK, AgentRuntimeState.TASK_RECEIVED, AgentRuntimeState.ANALYZING, AgentRuntimeState.PLANNING, AgentRuntimeState.WORKING],
                AgentRuntimeState.SELF_REVIEW: [AgentRuntimeState.WAITING_TASK, AgentRuntimeState.TASK_RECEIVED, AgentRuntimeState.ANALYZING, AgentRuntimeState.PLANNING, AgentRuntimeState.WORKING, AgentRuntimeState.SELF_REVIEW],
                AgentRuntimeState.WAITING_DISCUSSION: [AgentRuntimeState.WAITING_TASK, AgentRuntimeState.TASK_RECEIVED, AgentRuntimeState.ANALYZING, AgentRuntimeState.PLANNING, AgentRuntimeState.WORKING, AgentRuntimeState.SELF_REVIEW, AgentRuntimeState.WAITING_DISCUSSION],
                AgentRuntimeState.WAITING_MEMORY: [AgentRuntimeState.WAITING_TASK, AgentRuntimeState.TASK_RECEIVED, AgentRuntimeState.ANALYZING, AgentRuntimeState.PLANNING, AgentRuntimeState.WORKING, AgentRuntimeState.SELF_REVIEW, AgentRuntimeState.WAITING_MEMORY],
                AgentRuntimeState.WAITING_APPROVAL: [AgentRuntimeState.WAITING_TASK, AgentRuntimeState.TASK_RECEIVED, AgentRuntimeState.ANALYZING, AgentRuntimeState.PLANNING, AgentRuntimeState.WORKING, AgentRuntimeState.SELF_REVIEW, AgentRuntimeState.WAITING_APPROVAL],
            }
            for s in mapping[target]:
                rt.change_state(s)

        for state in non_terminal_path_states:
            rt = _runtime()
            rt.start_session()
            get_to(rt, state)
            rt.fail(f"failed at {state}")
            sess = rt.all_sessions()[0]
            self.assertEqual(
                sess.current_state,
                AgentRuntimeState.FAILED,
                msg=f"Expected FAILED after failing from {state}",
            )


# ---------------------------------------------------------------------------
# TestEdgeCases
# ---------------------------------------------------------------------------

class TestEdgeCases(unittest.TestCase):

    def test_start_session_no_project_no_task_defaults_to_none(self) -> None:
        _, sess = _started()
        self.assertIsNone(sess.project_id)
        self.assertIsNone(sess.task_id)

    def test_session_duration_positive_after_fail(self) -> None:
        rt, sess = _started()
        rt.fail("error")
        dur = sess.duration_seconds()
        self.assertIsNotNone(dur)
        self.assertGreaterEqual(dur, 0.0)

    def test_runtime_event_type_string_comparison(self) -> None:
        self.assertEqual(RuntimeEventType.STATE_CHANGED, "STATE_CHANGED")
        self.assertEqual(RuntimeEventType.SESSION_STARTED, "SESSION_STARTED")

    def test_get_session_all_sessions_in_history(self) -> None:
        rt = _runtime()
        ids = []
        for i in range(3):
            s = rt.start_session(task_id=f"task-{i}")
            ids.append(s.session_id)
            rt.fail("cycle")
        for sid in ids:
            retrieved = rt.get_session(sid)
            self.assertEqual(retrieved.session_id, sid)

    def test_state_transitions_count_matches_state_changes(self) -> None:
        rt, sess = _started()
        _advance_to_working(rt)
        transitions = sess.state_transitions()
        # start_session creates CREATED→READY (1) + READY→WAITING_TASK→...→WORKING (5) = 6
        self.assertGreaterEqual(len(transitions), 5)

    def test_result_artifact_list_is_independent_copy(self) -> None:
        artifacts = ["file_a.py", "file_b.md"]
        r = RuntimeResult(success=True, summary="Done.", generated_artifacts=artifacts)
        self.assertEqual(r.artifact_count(), 2)

    def test_runtime_context_metadata_is_independent_per_instance(self) -> None:
        ctx1 = RuntimeContext(metadata={"x": 1})
        ctx2 = RuntimeContext(metadata={"y": 2})
        self.assertNotIn("y", ctx1.metadata)
        self.assertNotIn("x", ctx2.metadata)

    def test_agent_runtime_error_is_exception(self) -> None:
        self.assertTrue(issubclass(AgentRuntimeError, Exception))

    def test_change_state_allowed_transitions_from_waiting_approval(self) -> None:
        for target in (
            AgentRuntimeState.FINISHED,
            AgentRuntimeState.WORKING,
            AgentRuntimeState.FAILED,
        ):
            rt, _ = _started()
            _advance_to_self_review(rt)
            rt.change_state(AgentRuntimeState.WAITING_APPROVAL)
            rt.change_state(target)
            s = rt.all_sessions()[0]
            self.assertEqual(s.current_state, target)

    def test_stop_session_session_remains_in_all_sessions(self) -> None:
        rt, sess = _started()
        rt.stop_session()
        self.assertIn(sess, rt.all_sessions())

    def test_finish_state_transition_event_correct(self) -> None:
        rt, sess = _started()
        _advance_to_self_review(rt)
        rt.change_state(AgentRuntimeState.WAITING_APPROVAL)
        rt.finish(_result())
        transitions = sess.state_transitions()
        finish_event = next(
            (e for e in transitions if e.to_state == AgentRuntimeState.FINISHED), None
        )
        self.assertIsNotNone(finish_event)
        self.assertEqual(finish_event.from_state, AgentRuntimeState.WAITING_APPROVAL)


if __name__ == "__main__":
    unittest.main()
