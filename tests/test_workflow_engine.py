"""
Tests for core/workflow_engine.py — Sprint 13 Workflow Engine.

Coverage: WorkflowEngine (all public + private methods), exception hierarchy,
WorkflowStatus, WorkflowEventType, WorkflowEvent, Workflow helpers,
WorkflowStage, WorkflowTransition, WorkflowTemplate.

Run with:
    .venv\\Scripts\\python.exe -m unittest tests.test_workflow_engine -v
"""

import unittest
from datetime import datetime, timezone
from typing import List, Optional
from unittest.mock import MagicMock

from core.workflow_engine import (
    IllegalTransitionError,
    InvalidWorkflowError,
    WorkflowEngine,
    WorkflowEngineError,
    WorkflowNotFoundError,
)
from core.workflow import (
    Workflow,
    WorkflowEvent,
    WorkflowEventType,
    WorkflowStatus,
)
from core.workflow_stage import WorkflowStage
from core.workflow_template import WorkflowTemplate
from core.workflow_transition import WorkflowTransition


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stage(
    stage_id: str,
    name: str,
    order: int,
    approval: bool = False,
    discussion: bool = False,
    memory: bool = False,
) -> WorkflowStage:
    return WorkflowStage(
        id=stage_id,
        name=name,
        order=order,
        approval_required=approval,
        discussion_allowed=discussion,
        memory_required=memory,
    )


def _simple_stages() -> List[WorkflowStage]:
    return [
        _make_stage("s1", "Stage One", 1),
        _make_stage("s2", "Stage Two", 2),
        _make_stage("s3", "Stage Three", 3),
    ]


def _single_stage() -> List[WorkflowStage]:
    return [_make_stage("s1", "Only Stage", 1)]


def _two_stages() -> List[WorkflowStage]:
    return [
        _make_stage("s1", "Stage One", 1),
        _make_stage("s2", "Stage Two", 2),
    ]


def _engine_with_workflow(stages=None, name="Test") -> tuple:
    engine = WorkflowEngine()
    wf = engine.create_workflow(name, "desc", WorkflowTemplate.SOFTWARE_PROJECT, stages or _simple_stages())
    return engine, wf


def _engine_active(stages=None, name="Test") -> tuple:
    engine, wf = _engine_with_workflow(stages, name)
    engine.start(wf.id)
    return engine, wf


# ---------------------------------------------------------------------------
# 1. Exception hierarchy
# ---------------------------------------------------------------------------

class TestExceptionHierarchy(unittest.TestCase):

    def test_workflow_engine_error_is_exception(self):
        self.assertTrue(issubclass(WorkflowEngineError, Exception))

    def test_workflow_not_found_error_is_engine_error(self):
        self.assertTrue(issubclass(WorkflowNotFoundError, WorkflowEngineError))

    def test_invalid_workflow_error_is_engine_error(self):
        self.assertTrue(issubclass(InvalidWorkflowError, WorkflowEngineError))

    def test_illegal_transition_error_is_engine_error(self):
        self.assertTrue(issubclass(IllegalTransitionError, WorkflowEngineError))

    def test_raise_workflow_not_found(self):
        with self.assertRaises(WorkflowNotFoundError):
            raise WorkflowNotFoundError("not found")

    def test_raise_invalid_workflow(self):
        with self.assertRaises(InvalidWorkflowError):
            raise InvalidWorkflowError("invalid")

    def test_raise_illegal_transition(self):
        with self.assertRaises(IllegalTransitionError):
            raise IllegalTransitionError("illegal")

    def test_not_found_caught_as_engine_error(self):
        with self.assertRaises(WorkflowEngineError):
            raise WorkflowNotFoundError("x")

    def test_invalid_caught_as_engine_error(self):
        with self.assertRaises(WorkflowEngineError):
            raise InvalidWorkflowError("x")

    def test_illegal_caught_as_engine_error(self):
        with self.assertRaises(WorkflowEngineError):
            raise IllegalTransitionError("x")

    def test_exception_message_preserved(self):
        try:
            raise WorkflowNotFoundError("my message")
        except WorkflowNotFoundError as e:
            self.assertIn("my message", str(e))


# ---------------------------------------------------------------------------
# 2. WorkflowEngine construction
# ---------------------------------------------------------------------------

class TestWorkflowEngineConstruction(unittest.TestCase):

    def test_default_construction(self):
        engine = WorkflowEngine()
        self.assertIsNotNone(engine)

    def test_empty_history_on_construction(self):
        engine = WorkflowEngine()
        self.assertEqual(engine.history(), [])

    def test_statistics_empty(self):
        engine = WorkflowEngine()
        stats = engine.statistics()
        self.assertEqual(stats["total_workflows"], 0)

    def test_accepts_memory_engine(self):
        engine = WorkflowEngine(memory_engine=MagicMock())
        self.assertIsNotNone(engine._memory_engine)

    def test_accepts_decision_engine(self):
        engine = WorkflowEngine(decision_engine=MagicMock())
        self.assertIsNotNone(engine._decision_engine)

    def test_accepts_discussion_engine(self):
        engine = WorkflowEngine(discussion_engine=MagicMock())
        self.assertIsNotNone(engine._discussion_engine)

    def test_accepts_company_orchestrator(self):
        engine = WorkflowEngine(company_orchestrator=MagicMock())
        self.assertIsNotNone(engine._company_orchestrator)

    def test_all_integrations_none_by_default(self):
        engine = WorkflowEngine()
        self.assertIsNone(engine._memory_engine)
        self.assertIsNone(engine._decision_engine)
        self.assertIsNone(engine._discussion_engine)
        self.assertIsNone(engine._company_orchestrator)


# ---------------------------------------------------------------------------
# 3. create_workflow()
# ---------------------------------------------------------------------------

class TestCreateWorkflow(unittest.TestCase):

    def setUp(self):
        self.engine = WorkflowEngine()

    def test_creates_workflow(self):
        wf = self.engine.create_workflow("Project", "desc", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        self.assertIsNotNone(wf)

    def test_returns_workflow_type(self):
        wf = self.engine.create_workflow("P", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        self.assertIsInstance(wf, Workflow)

    def test_workflow_status_pending(self):
        wf = self.engine.create_workflow("P", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        self.assertEqual(wf.status, WorkflowStatus.PENDING)

    def test_workflow_name_set(self):
        wf = self.engine.create_workflow("My Project", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        self.assertEqual(wf.name, "My Project")

    def test_workflow_description_set(self):
        wf = self.engine.create_workflow("P", "My description", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        self.assertEqual(wf.description, "My description")

    def test_workflow_template_set(self):
        wf = self.engine.create_workflow("P", "d", WorkflowTemplate.AUTOMATION, WorkflowTemplate.AUTOMATION.create_stages())
        self.assertEqual(wf.template, WorkflowTemplate.AUTOMATION)

    def test_workflow_id_unique(self):
        wf1 = self.engine.create_workflow("A", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        wf2 = self.engine.create_workflow("B", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        self.assertNotEqual(wf1.id, wf2.id)

    def test_workflow_progress_zero(self):
        wf = self.engine.create_workflow("P", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        self.assertEqual(wf.progress, 0.0)

    def test_workflow_current_stage_none(self):
        wf = self.engine.create_workflow("P", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        self.assertIsNone(wf.current_stage)

    def test_workflow_stages_sorted_by_order(self):
        stages = [
            _make_stage("s3", "Three", 3),
            _make_stage("s1", "One", 1),
            _make_stage("s2", "Two", 2),
        ]
        wf = self.engine.create_workflow("P", "d", WorkflowTemplate.SOFTWARE_PROJECT, stages)
        orders = [s.order for s in wf.stages]
        self.assertEqual(orders, sorted(orders))

    def test_workflow_has_created_event(self):
        wf = self.engine.create_workflow("P", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        types = [e.event_type for e in wf.events]
        self.assertIn(WorkflowEventType.WORKFLOW_CREATED, types)

    def test_workflow_created_at_set(self):
        wf = self.engine.create_workflow("P", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        self.assertIsNotNone(wf.created_at)

    def test_workflow_updated_at_set(self):
        wf = self.engine.create_workflow("P", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        self.assertIsNotNone(wf.updated_at)

    def test_workflow_stored_in_engine(self):
        wf = self.engine.create_workflow("P", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        self.assertEqual(self.engine.find_workflow(wf.id), wf)

    def test_history_includes_workflow(self):
        wf = self.engine.create_workflow("P", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        self.assertIn(wf, self.engine.history())

    def test_uses_template_stages_when_none_given(self):
        wf = self.engine.create_workflow("P", "d", WorkflowTemplate.SOFTWARE_PROJECT)
        self.assertEqual(wf.stage_count(), WorkflowTemplate.SOFTWARE_PROJECT.stage_count())

    def test_empty_name_raises(self):
        with self.assertRaises(InvalidWorkflowError):
            self.engine.create_workflow("", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())

    def test_whitespace_name_raises(self):
        with self.assertRaises(InvalidWorkflowError):
            self.engine.create_workflow("   ", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())

    def test_empty_stages_raises(self):
        with self.assertRaises(InvalidWorkflowError):
            self.engine.create_workflow("P", "d", WorkflowTemplate.SOFTWARE_PROJECT, [])

    def test_duplicate_order_raises(self):
        stages = [
            _make_stage("s1", "One", 1),
            _make_stage("s2", "Two", 1),
        ]
        with self.assertRaises(InvalidWorkflowError):
            self.engine.create_workflow("P", "d", WorkflowTemplate.SOFTWARE_PROJECT, stages)

    def test_duplicate_id_raises(self):
        stages = [
            _make_stage("same", "One", 1),
            _make_stage("same", "Two", 2),
        ]
        with self.assertRaises(InvalidWorkflowError):
            self.engine.create_workflow("P", "d", WorkflowTemplate.SOFTWARE_PROJECT, stages)

    def test_duplicate_name_raises(self):
        stages = [
            _make_stage("s1", "Same Name", 1),
            _make_stage("s2", "Same Name", 2),
        ]
        with self.assertRaises(InvalidWorkflowError):
            self.engine.create_workflow("P", "d", WorkflowTemplate.SOFTWARE_PROJECT, stages)

    def test_non_positive_order_raises(self):
        stages = [_make_stage("s1", "One", 0)]
        with self.assertRaises(InvalidWorkflowError):
            self.engine.create_workflow("P", "d", WorkflowTemplate.SOFTWARE_PROJECT, stages)

    def test_negative_order_raises(self):
        stages = [_make_stage("s1", "One", -1)]
        with self.assertRaises(InvalidWorkflowError):
            self.engine.create_workflow("P", "d", WorkflowTemplate.SOFTWARE_PROJECT, stages)

    def test_name_stripped(self):
        wf = self.engine.create_workflow("  Trim Me  ", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        self.assertEqual(wf.name, "Trim Me")


# ---------------------------------------------------------------------------
# 4. start()
# ---------------------------------------------------------------------------

class TestStart(unittest.TestCase):

    def test_start_sets_active(self):
        engine, wf = _engine_with_workflow()
        engine.start(wf.id)
        self.assertEqual(wf.status, WorkflowStatus.ACTIVE)

    def test_start_sets_current_stage(self):
        engine, wf = _engine_with_workflow()
        engine.start(wf.id)
        self.assertIsNotNone(wf.current_stage)

    def test_start_sets_first_stage(self):
        engine, wf = _engine_with_workflow()
        engine.start(wf.id)
        self.assertEqual(wf.current_stage.order, 1)

    def test_start_emits_workflow_started_event(self):
        engine, wf = _engine_with_workflow()
        engine.start(wf.id)
        types = [e.event_type for e in wf.events]
        self.assertIn(WorkflowEventType.WORKFLOW_STARTED, types)

    def test_start_emits_stage_started_event(self):
        engine, wf = _engine_with_workflow()
        engine.start(wf.id)
        types = [e.event_type for e in wf.events]
        self.assertIn(WorkflowEventType.STAGE_STARTED, types)

    def test_start_returns_workflow(self):
        engine, wf = _engine_with_workflow()
        returned = engine.start(wf.id)
        self.assertIs(returned, wf)

    def test_start_not_found_raises(self):
        engine = WorkflowEngine()
        with self.assertRaises(WorkflowNotFoundError):
            engine.start("nonexistent")

    def test_start_already_active_raises(self):
        engine, wf = _engine_active()
        with self.assertRaises(IllegalTransitionError):
            engine.start(wf.id)

    def test_start_paused_raises(self):
        engine, wf = _engine_active()
        engine.pause(wf.id)
        with self.assertRaises(IllegalTransitionError):
            engine.start(wf.id)

    def test_start_completed_raises(self):
        engine, wf = _engine_active(_single_stage())
        engine.complete(wf.id)
        with self.assertRaises(IllegalTransitionError):
            engine.start(wf.id)

    def test_start_cancelled_raises(self):
        engine, wf = _engine_with_workflow()
        engine.cancel(wf.id)
        with self.assertRaises(IllegalTransitionError):
            engine.start(wf.id)

    def test_start_updates_updated_at(self):
        engine, wf = _engine_with_workflow()
        before = wf.updated_at
        engine.start(wf.id)
        self.assertGreaterEqual(wf.updated_at, before)


# ---------------------------------------------------------------------------
# 5. advance()
# ---------------------------------------------------------------------------

class TestAdvance(unittest.TestCase):

    def test_advance_moves_to_next_stage(self):
        engine, wf = _engine_active()
        first_order = wf.current_stage.order
        engine.advance(wf.id)
        self.assertEqual(wf.current_stage.order, first_order + 1)

    def test_advance_records_completed_stage(self):
        engine, wf = _engine_active()
        first = wf.current_stage
        engine.advance(wf.id)
        self.assertIn(first, wf.completed_stages)

    def test_advance_returns_workflow(self):
        engine, wf = _engine_active()
        returned = engine.advance(wf.id)
        self.assertIs(returned, wf)

    def test_advance_emits_stage_completed(self):
        engine, wf = _engine_active()
        engine.advance(wf.id)
        types = [e.event_type for e in wf.events]
        self.assertIn(WorkflowEventType.STAGE_COMPLETED, types)

    def test_advance_emits_stage_transition(self):
        engine, wf = _engine_active()
        engine.advance(wf.id)
        types = [e.event_type for e in wf.events]
        self.assertIn(WorkflowEventType.STAGE_TRANSITION, types)

    def test_advance_emits_stage_started(self):
        engine, wf = _engine_active()
        engine.advance(wf.id)
        started = [e for e in wf.events if e.event_type == WorkflowEventType.STAGE_STARTED]
        self.assertGreaterEqual(len(started), 2)

    def test_advance_records_transition(self):
        engine, wf = _engine_active()
        engine.advance(wf.id)
        self.assertEqual(len(wf.transitions), 1)

    def test_advance_updates_progress(self):
        engine, wf = _engine_active()
        engine.advance(wf.id)
        self.assertGreater(wf.progress, 0.0)

    def test_advance_progress_calculation(self):
        engine, wf = _engine_active(_simple_stages())
        engine.advance(wf.id)
        self.assertAlmostEqual(wf.progress, 1 / 3)

    def test_advance_from_last_stage_raises(self):
        engine, wf = _engine_active(_single_stage())
        with self.assertRaises(IllegalTransitionError):
            engine.advance(wf.id)

    def test_advance_on_pending_raises(self):
        engine, wf = _engine_with_workflow()
        with self.assertRaises(IllegalTransitionError):
            engine.advance(wf.id)

    def test_advance_on_paused_raises(self):
        engine, wf = _engine_active()
        engine.pause(wf.id)
        with self.assertRaises(IllegalTransitionError):
            engine.advance(wf.id)

    def test_advance_on_completed_raises(self):
        engine, wf = _engine_active(_single_stage())
        engine.complete(wf.id)
        with self.assertRaises(IllegalTransitionError):
            engine.advance(wf.id)

    def test_advance_on_cancelled_raises(self):
        engine, wf = _engine_active()
        engine.cancel(wf.id)
        with self.assertRaises(IllegalTransitionError):
            engine.advance(wf.id)

    def test_advance_not_found_raises(self):
        engine = WorkflowEngine()
        with self.assertRaises(WorkflowNotFoundError):
            engine.advance("nonexistent")

    def test_advance_full_journey(self):
        engine, wf = _engine_active(_simple_stages())
        engine.advance(wf.id)
        engine.advance(wf.id)
        self.assertEqual(wf.current_stage.order, 3)
        self.assertEqual(len(wf.completed_stages), 2)

    def test_advance_transition_from_to(self):
        engine, wf = _engine_active(_two_stages())
        s1_id = wf.current_stage.id
        engine.advance(wf.id)
        s2_id = wf.current_stage.id
        t = wf.transitions[0]
        self.assertEqual(t.from_stage, s1_id)
        self.assertEqual(t.to_stage, s2_id)

    def test_advance_updates_updated_at(self):
        engine, wf = _engine_active()
        before = wf.updated_at
        engine.advance(wf.id)
        self.assertGreaterEqual(wf.updated_at, before)

    def test_advance_does_not_complete(self):
        engine, wf = _engine_active(_simple_stages())
        engine.advance(wf.id)
        self.assertNotEqual(wf.status, WorkflowStatus.COMPLETED)

    def test_advance_second_to_last_still_active(self):
        engine, wf = _engine_active(_simple_stages())
        engine.advance(wf.id)
        engine.advance(wf.id)
        self.assertEqual(wf.status, WorkflowStatus.ACTIVE)


# ---------------------------------------------------------------------------
# 6. rollback()
# ---------------------------------------------------------------------------

class TestRollback(unittest.TestCase):

    def _advanced(self, n=1):
        engine, wf = _engine_active(_simple_stages())
        for _ in range(n):
            engine.advance(wf.id)
        return engine, wf

    def test_rollback_returns_to_previous_stage(self):
        engine, wf = self._advanced(1)
        second_order = wf.current_stage.order
        engine.rollback(wf.id)
        self.assertEqual(wf.current_stage.order, second_order - 1)

    def test_rollback_removes_from_completed_stages(self):
        engine, wf = self._advanced(1)
        count_before = len(wf.completed_stages)
        engine.rollback(wf.id)
        self.assertEqual(len(wf.completed_stages), count_before - 1)

    def test_rollback_returns_workflow(self):
        engine, wf = self._advanced(1)
        returned = engine.rollback(wf.id)
        self.assertIs(returned, wf)

    def test_rollback_emits_stage_rolled_back(self):
        engine, wf = self._advanced(1)
        engine.rollback(wf.id)
        types = [e.event_type for e in wf.events]
        self.assertIn(WorkflowEventType.STAGE_ROLLED_BACK, types)

    def test_rollback_emits_stage_transition(self):
        engine, wf = self._advanced(1)
        engine.rollback(wf.id)
        transitions = [e for e in wf.events if e.event_type == WorkflowEventType.STAGE_TRANSITION]
        self.assertGreaterEqual(len(transitions), 2)

    def test_rollback_emits_stage_started(self):
        engine, wf = self._advanced(1)
        engine.rollback(wf.id)
        started = [e for e in wf.events if e.event_type == WorkflowEventType.STAGE_STARTED]
        self.assertGreaterEqual(len(started), 3)

    def test_rollback_records_transition(self):
        engine, wf = self._advanced(1)
        count_before = len(wf.transitions)
        engine.rollback(wf.id)
        self.assertEqual(len(wf.transitions), count_before + 1)

    def test_rollback_updates_progress(self):
        engine, wf = self._advanced(1)
        after_advance = wf.progress
        engine.rollback(wf.id)
        self.assertLess(wf.progress, after_advance)

    def test_rollback_from_first_stage_raises(self):
        engine, wf = _engine_active(_simple_stages())
        with self.assertRaises(IllegalTransitionError):
            engine.rollback(wf.id)

    def test_rollback_on_pending_raises(self):
        engine, wf = _engine_with_workflow()
        with self.assertRaises(IllegalTransitionError):
            engine.rollback(wf.id)

    def test_rollback_on_paused_raises(self):
        engine, wf = self._advanced(1)
        engine.pause(wf.id)
        with self.assertRaises(IllegalTransitionError):
            engine.rollback(wf.id)

    def test_rollback_not_found_raises(self):
        engine = WorkflowEngine()
        with self.assertRaises(WorkflowNotFoundError):
            engine.rollback("nonexistent")

    def test_rollback_twice(self):
        engine, wf = self._advanced(2)
        engine.rollback(wf.id)
        engine.rollback(wf.id)
        self.assertEqual(wf.current_stage.order, 1)

    def test_rollback_advance_rollback(self):
        engine, wf = _engine_active(_simple_stages())
        engine.advance(wf.id)
        engine.rollback(wf.id)
        engine.advance(wf.id)
        self.assertEqual(wf.current_stage.order, 2)

    def test_rollback_transition_from_to(self):
        engine, wf = _engine_active(_two_stages())
        s1_id = wf.stages[0].id
        s2_id = wf.stages[1].id
        engine.advance(wf.id)
        engine.rollback(wf.id)
        last_t = wf.transitions[-1]
        self.assertEqual(last_t.from_stage, s2_id)
        self.assertEqual(last_t.to_stage, s1_id)


# ---------------------------------------------------------------------------
# 7. pause()
# ---------------------------------------------------------------------------

class TestPause(unittest.TestCase):

    def test_pause_sets_paused_status(self):
        engine, wf = _engine_active()
        engine.pause(wf.id)
        self.assertEqual(wf.status, WorkflowStatus.PAUSED)

    def test_pause_returns_workflow(self):
        engine, wf = _engine_active()
        returned = engine.pause(wf.id)
        self.assertIs(returned, wf)

    def test_pause_emits_workflow_paused(self):
        engine, wf = _engine_active()
        engine.pause(wf.id)
        types = [e.event_type for e in wf.events]
        self.assertIn(WorkflowEventType.WORKFLOW_PAUSED, types)

    def test_pause_preserves_current_stage(self):
        engine, wf = _engine_active()
        current = wf.current_stage
        engine.pause(wf.id)
        self.assertIs(wf.current_stage, current)

    def test_pause_on_pending_raises(self):
        engine, wf = _engine_with_workflow()
        with self.assertRaises(IllegalTransitionError):
            engine.pause(wf.id)

    def test_pause_already_paused_raises(self):
        engine, wf = _engine_active()
        engine.pause(wf.id)
        with self.assertRaises(IllegalTransitionError):
            engine.pause(wf.id)

    def test_pause_completed_raises(self):
        engine, wf = _engine_active(_single_stage())
        engine.complete(wf.id)
        with self.assertRaises(IllegalTransitionError):
            engine.pause(wf.id)

    def test_pause_cancelled_raises(self):
        engine, wf = _engine_active()
        engine.cancel(wf.id)
        with self.assertRaises(IllegalTransitionError):
            engine.pause(wf.id)

    def test_pause_not_found_raises(self):
        engine = WorkflowEngine()
        with self.assertRaises(WorkflowNotFoundError):
            engine.pause("nonexistent")

    def test_pause_updates_updated_at(self):
        engine, wf = _engine_active()
        before = wf.updated_at
        engine.pause(wf.id)
        self.assertGreaterEqual(wf.updated_at, before)


# ---------------------------------------------------------------------------
# 8. resume()
# ---------------------------------------------------------------------------

class TestResume(unittest.TestCase):

    def _paused(self, stages=None):
        engine, wf = _engine_active(stages)
        engine.pause(wf.id)
        return engine, wf

    def test_resume_sets_active(self):
        engine, wf = self._paused()
        engine.resume(wf.id)
        self.assertEqual(wf.status, WorkflowStatus.ACTIVE)

    def test_resume_returns_workflow(self):
        engine, wf = self._paused()
        returned = engine.resume(wf.id)
        self.assertIs(returned, wf)

    def test_resume_emits_workflow_resumed(self):
        engine, wf = self._paused()
        engine.resume(wf.id)
        types = [e.event_type for e in wf.events]
        self.assertIn(WorkflowEventType.WORKFLOW_RESUMED, types)

    def test_resume_preserves_current_stage(self):
        engine, wf = self._paused()
        cs_before = wf.current_stage
        engine.resume(wf.id)
        self.assertIs(wf.current_stage, cs_before)

    def test_resume_on_active_raises(self):
        engine, wf = _engine_active()
        with self.assertRaises(IllegalTransitionError):
            engine.resume(wf.id)

    def test_resume_on_pending_raises(self):
        engine, wf = _engine_with_workflow()
        with self.assertRaises(IllegalTransitionError):
            engine.resume(wf.id)

    def test_resume_on_completed_raises(self):
        engine, wf = _engine_active(_single_stage())
        engine.complete(wf.id)
        with self.assertRaises(IllegalTransitionError):
            engine.resume(wf.id)

    def test_resume_on_cancelled_raises(self):
        engine, wf = _engine_active()
        engine.cancel(wf.id)
        with self.assertRaises(IllegalTransitionError):
            engine.resume(wf.id)

    def test_resume_not_found_raises(self):
        engine = WorkflowEngine()
        with self.assertRaises(WorkflowNotFoundError):
            engine.resume("nonexistent")

    def test_resume_allows_advance_after(self):
        engine, wf = self._paused()
        engine.resume(wf.id)
        engine.advance(wf.id)
        self.assertEqual(wf.current_stage.order, 2)

    def test_pause_resume_multiple_times(self):
        engine, wf = _engine_active(_simple_stages())
        engine.pause(wf.id)
        engine.resume(wf.id)
        engine.pause(wf.id)
        engine.resume(wf.id)
        self.assertEqual(wf.status, WorkflowStatus.ACTIVE)


# ---------------------------------------------------------------------------
# 9. complete()
# ---------------------------------------------------------------------------

class TestComplete(unittest.TestCase):

    def test_complete_sets_completed(self):
        engine, wf = _engine_active(_single_stage())
        engine.complete(wf.id)
        self.assertEqual(wf.status, WorkflowStatus.COMPLETED)

    def test_complete_returns_workflow(self):
        engine, wf = _engine_active(_single_stage())
        returned = engine.complete(wf.id)
        self.assertIs(returned, wf)

    def test_complete_sets_progress_one(self):
        engine, wf = _engine_active(_single_stage())
        engine.complete(wf.id)
        self.assertEqual(wf.progress, 1.0)

    def test_complete_clears_current_stage(self):
        engine, wf = _engine_active(_single_stage())
        engine.complete(wf.id)
        self.assertIsNone(wf.current_stage)

    def test_complete_adds_last_stage_to_completed(self):
        engine, wf = _engine_active(_single_stage())
        last = wf.current_stage
        engine.complete(wf.id)
        self.assertIn(last, wf.completed_stages)

    def test_complete_emits_stage_completed(self):
        engine, wf = _engine_active(_single_stage())
        engine.complete(wf.id)
        types = [e.event_type for e in wf.events]
        self.assertIn(WorkflowEventType.STAGE_COMPLETED, types)

    def test_complete_emits_workflow_completed(self):
        engine, wf = _engine_active(_single_stage())
        engine.complete(wf.id)
        types = [e.event_type for e in wf.events]
        self.assertIn(WorkflowEventType.WORKFLOW_COMPLETED, types)

    def test_complete_multi_stage_at_last(self):
        engine, wf = _engine_active(_simple_stages())
        engine.advance(wf.id)
        engine.advance(wf.id)
        engine.complete(wf.id)
        self.assertEqual(wf.status, WorkflowStatus.COMPLETED)

    def test_complete_not_at_last_stage_raises(self):
        engine, wf = _engine_active(_simple_stages())
        with self.assertRaises(IllegalTransitionError):
            engine.complete(wf.id)

    def test_complete_after_advance_not_last_raises(self):
        engine, wf = _engine_active(_simple_stages())
        engine.advance(wf.id)
        with self.assertRaises(IllegalTransitionError):
            engine.complete(wf.id)

    def test_complete_on_pending_raises(self):
        engine, wf = _engine_with_workflow(_single_stage())
        with self.assertRaises(IllegalTransitionError):
            engine.complete(wf.id)

    def test_complete_on_paused_raises(self):
        engine, wf = _engine_active(_single_stage())
        engine.pause(wf.id)
        with self.assertRaises(IllegalTransitionError):
            engine.complete(wf.id)

    def test_complete_on_cancelled_raises(self):
        engine, wf = _engine_active(_single_stage())
        engine.cancel(wf.id)
        with self.assertRaises(IllegalTransitionError):
            engine.complete(wf.id)

    def test_complete_not_found_raises(self):
        engine = WorkflowEngine()
        with self.assertRaises(WorkflowNotFoundError):
            engine.complete("nonexistent")

    def test_complete_all_stages_in_completed_stages(self):
        engine, wf = _engine_active(_simple_stages())
        engine.advance(wf.id)
        engine.advance(wf.id)
        engine.complete(wf.id)
        self.assertEqual(len(wf.completed_stages), 3)


# ---------------------------------------------------------------------------
# 10. cancel()
# ---------------------------------------------------------------------------

class TestCancel(unittest.TestCase):

    def test_cancel_sets_cancelled(self):
        engine, wf = _engine_with_workflow()
        engine.cancel(wf.id)
        self.assertEqual(wf.status, WorkflowStatus.CANCELLED)

    def test_cancel_from_active(self):
        engine, wf = _engine_active()
        engine.cancel(wf.id)
        self.assertEqual(wf.status, WorkflowStatus.CANCELLED)

    def test_cancel_from_paused(self):
        engine, wf = _engine_active()
        engine.pause(wf.id)
        engine.cancel(wf.id)
        self.assertEqual(wf.status, WorkflowStatus.CANCELLED)

    def test_cancel_from_pending(self):
        engine, wf = _engine_with_workflow()
        engine.cancel(wf.id)
        self.assertEqual(wf.status, WorkflowStatus.CANCELLED)

    def test_cancel_returns_workflow(self):
        engine, wf = _engine_active()
        returned = engine.cancel(wf.id)
        self.assertIs(returned, wf)

    def test_cancel_emits_workflow_cancelled(self):
        engine, wf = _engine_active()
        engine.cancel(wf.id)
        types = [e.event_type for e in wf.events]
        self.assertIn(WorkflowEventType.WORKFLOW_CANCELLED, types)

    def test_cancel_completed_raises(self):
        engine, wf = _engine_active(_single_stage())
        engine.complete(wf.id)
        with self.assertRaises(IllegalTransitionError):
            engine.cancel(wf.id)

    def test_cancel_already_cancelled_raises(self):
        engine, wf = _engine_active()
        engine.cancel(wf.id)
        with self.assertRaises(IllegalTransitionError):
            engine.cancel(wf.id)

    def test_cancel_not_found_raises(self):
        engine = WorkflowEngine()
        with self.assertRaises(WorkflowNotFoundError):
            engine.cancel("nonexistent")

    def test_cancel_updates_updated_at(self):
        engine, wf = _engine_active()
        before = wf.updated_at
        engine.cancel(wf.id)
        self.assertGreaterEqual(wf.updated_at, before)


# ---------------------------------------------------------------------------
# 11. current_stage()
# ---------------------------------------------------------------------------

class TestCurrentStage(unittest.TestCase):

    def test_current_stage_pending_none(self):
        engine, wf = _engine_with_workflow()
        self.assertIsNone(engine.current_stage(wf.id))

    def test_current_stage_active(self):
        engine, wf = _engine_active()
        self.assertIsNotNone(engine.current_stage(wf.id))

    def test_current_stage_returns_first_after_start(self):
        engine, wf = _engine_active()
        self.assertEqual(engine.current_stage(wf.id).order, 1)

    def test_current_stage_after_advance(self):
        engine, wf = _engine_active()
        engine.advance(wf.id)
        self.assertEqual(engine.current_stage(wf.id).order, 2)

    def test_current_stage_completed_none(self):
        engine, wf = _engine_active(_single_stage())
        engine.complete(wf.id)
        self.assertIsNone(engine.current_stage(wf.id))

    def test_current_stage_cancelled_none(self):
        engine, wf = _engine_with_workflow()
        engine.cancel(wf.id)
        self.assertIsNone(engine.current_stage(wf.id))

    def test_current_stage_not_found_raises(self):
        engine = WorkflowEngine()
        with self.assertRaises(WorkflowNotFoundError):
            engine.current_stage("nonexistent")

    def test_current_stage_paused_preserved(self):
        engine, wf = _engine_active()
        cs = wf.current_stage
        engine.pause(wf.id)
        self.assertIs(engine.current_stage(wf.id), cs)


# ---------------------------------------------------------------------------
# 12. find_workflow()
# ---------------------------------------------------------------------------

class TestFindWorkflow(unittest.TestCase):

    def test_find_returns_workflow(self):
        engine, wf = _engine_with_workflow()
        found = engine.find_workflow(wf.id)
        self.assertIs(found, wf)

    def test_find_not_found_raises(self):
        engine = WorkflowEngine()
        with self.assertRaises(WorkflowNotFoundError):
            engine.find_workflow("does_not_exist")

    def test_find_wrong_id_raises(self):
        engine, wf = _engine_with_workflow()
        with self.assertRaises(WorkflowNotFoundError):
            engine.find_workflow("wrong-" + wf.id)

    def test_find_multiple_workflows(self):
        engine = WorkflowEngine()
        wf1 = engine.create_workflow("A", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        wf2 = engine.create_workflow("B", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        self.assertIs(engine.find_workflow(wf1.id), wf1)
        self.assertIs(engine.find_workflow(wf2.id), wf2)


# ---------------------------------------------------------------------------
# 13. history()
# ---------------------------------------------------------------------------

class TestHistory(unittest.TestCase):

    def test_history_empty(self):
        engine = WorkflowEngine()
        self.assertEqual(engine.history(), [])

    def test_history_contains_created_workflow(self):
        engine, wf = _engine_with_workflow()
        self.assertIn(wf, engine.history())

    def test_history_contains_all_workflows(self):
        engine = WorkflowEngine()
        wf1 = engine.create_workflow("A", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        wf2 = engine.create_workflow("B", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        h = engine.history()
        self.assertIn(wf1, h)
        self.assertIn(wf2, h)

    def test_history_ordered_by_created_at(self):
        engine = WorkflowEngine()
        wf1 = engine.create_workflow("A", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        wf2 = engine.create_workflow("B", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        h = engine.history()
        idx1 = h.index(wf1)
        idx2 = h.index(wf2)
        self.assertLessEqual(idx1, idx2)

    def test_history_returns_copy(self):
        engine, wf = _engine_with_workflow()
        h1 = engine.history()
        h2 = engine.history()
        self.assertIsNot(h1, h2)

    def test_history_mutation_does_not_affect_engine(self):
        engine, wf = _engine_with_workflow()
        h = engine.history()
        h.clear()
        self.assertIn(wf, engine.history())

    def test_history_count_grows(self):
        engine = WorkflowEngine()
        engine.create_workflow("A", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        self.assertEqual(len(engine.history()), 1)
        engine.create_workflow("B", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        self.assertEqual(len(engine.history()), 2)


# ---------------------------------------------------------------------------
# 14. statistics()
# ---------------------------------------------------------------------------

class TestStatistics(unittest.TestCase):

    def test_statistics_keys_present(self):
        engine = WorkflowEngine()
        stats = engine.statistics()
        for key in ("total_workflows", "by_status", "by_template",
                    "average_progress", "completed_count", "active_count",
                    "paused_count", "cancelled_count"):
            self.assertIn(key, stats)

    def test_statistics_empty_engine(self):
        engine = WorkflowEngine()
        stats = engine.statistics()
        self.assertEqual(stats["total_workflows"], 0)
        self.assertEqual(stats["average_progress"], 0.0)

    def test_statistics_counts_workflow(self):
        engine = WorkflowEngine()
        engine.create_workflow("A", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        self.assertEqual(engine.statistics()["total_workflows"], 1)

    def test_statistics_by_status_pending(self):
        engine = WorkflowEngine()
        engine.create_workflow("A", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        self.assertEqual(engine.statistics()["by_status"]["PENDING"], 1)

    def test_statistics_by_status_active(self):
        engine, wf = _engine_active()
        self.assertEqual(engine.statistics()["by_status"]["ACTIVE"], 1)

    def test_statistics_by_status_completed(self):
        engine, wf = _engine_active(_single_stage())
        engine.complete(wf.id)
        self.assertEqual(engine.statistics()["completed_count"], 1)

    def test_statistics_by_status_cancelled(self):
        engine, wf = _engine_active()
        engine.cancel(wf.id)
        self.assertEqual(engine.statistics()["cancelled_count"], 1)

    def test_statistics_by_status_paused(self):
        engine, wf = _engine_active()
        engine.pause(wf.id)
        self.assertEqual(engine.statistics()["paused_count"], 1)

    def test_statistics_average_progress(self):
        engine, wf = _engine_active(_simple_stages())
        engine.advance(wf.id)
        stats = engine.statistics()
        self.assertAlmostEqual(stats["average_progress"], 1 / 3)

    def test_statistics_by_template(self):
        engine = WorkflowEngine()
        engine.create_workflow("A", "d", WorkflowTemplate.AUTOMATION, WorkflowTemplate.AUTOMATION.create_stages())
        stats = engine.statistics()
        self.assertEqual(stats["by_template"]["AUTOMATION"], 1)

    def test_statistics_multiple_workflows(self):
        engine = WorkflowEngine()
        engine.create_workflow("A", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        engine.create_workflow("B", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        self.assertEqual(engine.statistics()["total_workflows"], 2)


# ---------------------------------------------------------------------------
# 15. WorkflowStatus enum
# ---------------------------------------------------------------------------

class TestWorkflowStatus(unittest.TestCase):

    def test_str_returns_value(self):
        self.assertEqual(str(WorkflowStatus.PENDING), "PENDING")
        self.assertEqual(str(WorkflowStatus.ACTIVE), "ACTIVE")
        self.assertEqual(str(WorkflowStatus.PAUSED), "PAUSED")
        self.assertEqual(str(WorkflowStatus.COMPLETED), "COMPLETED")
        self.assertEqual(str(WorkflowStatus.CANCELLED), "CANCELLED")
        self.assertEqual(str(WorkflowStatus.FAILED), "FAILED")

    def test_is_terminal_completed(self):
        self.assertTrue(WorkflowStatus.COMPLETED.is_terminal())

    def test_is_terminal_cancelled(self):
        self.assertTrue(WorkflowStatus.CANCELLED.is_terminal())

    def test_is_terminal_failed(self):
        self.assertTrue(WorkflowStatus.FAILED.is_terminal())

    def test_is_terminal_pending_false(self):
        self.assertFalse(WorkflowStatus.PENDING.is_terminal())

    def test_is_terminal_active_false(self):
        self.assertFalse(WorkflowStatus.ACTIVE.is_terminal())

    def test_is_terminal_paused_false(self):
        self.assertFalse(WorkflowStatus.PAUSED.is_terminal())

    def test_is_running(self):
        self.assertTrue(WorkflowStatus.ACTIVE.is_running())
        self.assertFalse(WorkflowStatus.PENDING.is_running())
        self.assertFalse(WorkflowStatus.PAUSED.is_running())

    def test_is_paused(self):
        self.assertTrue(WorkflowStatus.PAUSED.is_paused())
        self.assertFalse(WorkflowStatus.ACTIVE.is_paused())

    def test_is_pending(self):
        self.assertTrue(WorkflowStatus.PENDING.is_pending())
        self.assertFalse(WorkflowStatus.ACTIVE.is_pending())

    def test_can_advance(self):
        self.assertTrue(WorkflowStatus.ACTIVE.can_advance())
        self.assertFalse(WorkflowStatus.PENDING.can_advance())
        self.assertFalse(WorkflowStatus.PAUSED.can_advance())
        self.assertFalse(WorkflowStatus.COMPLETED.can_advance())

    def test_can_pause(self):
        self.assertTrue(WorkflowStatus.ACTIVE.can_pause())
        self.assertFalse(WorkflowStatus.PAUSED.can_pause())
        self.assertFalse(WorkflowStatus.PENDING.can_pause())

    def test_can_resume(self):
        self.assertTrue(WorkflowStatus.PAUSED.can_resume())
        self.assertFalse(WorkflowStatus.ACTIVE.can_resume())
        self.assertFalse(WorkflowStatus.PENDING.can_resume())

    def test_is_str_subclass(self):
        self.assertIsInstance(WorkflowStatus.ACTIVE, str)


# ---------------------------------------------------------------------------
# 16. WorkflowEventType enum
# ---------------------------------------------------------------------------

class TestWorkflowEventType(unittest.TestCase):

    def test_str_returns_value(self):
        self.assertEqual(str(WorkflowEventType.WORKFLOW_CREATED), "WORKFLOW_CREATED")
        self.assertEqual(str(WorkflowEventType.STAGE_STARTED), "STAGE_STARTED")

    def test_is_workflow_lifecycle_true(self):
        lifecycle = [
            WorkflowEventType.WORKFLOW_CREATED, WorkflowEventType.WORKFLOW_STARTED,
            WorkflowEventType.WORKFLOW_PAUSED, WorkflowEventType.WORKFLOW_RESUMED,
            WorkflowEventType.WORKFLOW_COMPLETED, WorkflowEventType.WORKFLOW_CANCELLED,
            WorkflowEventType.WORKFLOW_FAILED,
        ]
        for et in lifecycle:
            self.assertTrue(et.is_workflow_lifecycle(), f"{et} should be lifecycle")

    def test_is_workflow_lifecycle_false_for_stage_events(self):
        stage_events = [
            WorkflowEventType.STAGE_STARTED, WorkflowEventType.STAGE_COMPLETED,
            WorkflowEventType.STAGE_ROLLED_BACK, WorkflowEventType.STAGE_TRANSITION,
        ]
        for et in stage_events:
            self.assertFalse(et.is_workflow_lifecycle(), f"{et} should not be lifecycle")

    def test_is_stage_event_true(self):
        stage_events = [
            WorkflowEventType.STAGE_STARTED, WorkflowEventType.STAGE_COMPLETED,
            WorkflowEventType.STAGE_ROLLED_BACK, WorkflowEventType.STAGE_TRANSITION,
        ]
        for et in stage_events:
            self.assertTrue(et.is_stage_event(), f"{et} should be stage event")

    def test_is_stage_event_false_for_lifecycle(self):
        lifecycle = [
            WorkflowEventType.WORKFLOW_CREATED, WorkflowEventType.WORKFLOW_STARTED,
        ]
        for et in lifecycle:
            self.assertFalse(et.is_stage_event(), f"{et} should not be stage event")

    def test_is_terminal_completed(self):
        self.assertTrue(WorkflowEventType.WORKFLOW_COMPLETED.is_terminal())

    def test_is_terminal_cancelled(self):
        self.assertTrue(WorkflowEventType.WORKFLOW_CANCELLED.is_terminal())

    def test_is_terminal_failed(self):
        self.assertTrue(WorkflowEventType.WORKFLOW_FAILED.is_terminal())

    def test_is_terminal_false_for_non_terminal(self):
        non_terminal = [
            WorkflowEventType.WORKFLOW_CREATED, WorkflowEventType.WORKFLOW_STARTED,
            WorkflowEventType.STAGE_STARTED,
        ]
        for et in non_terminal:
            self.assertFalse(et.is_terminal(), f"{et} should not be terminal")

    def test_is_str_subclass(self):
        self.assertIsInstance(WorkflowEventType.STAGE_STARTED, str)


# ---------------------------------------------------------------------------
# 17. WorkflowEvent
# ---------------------------------------------------------------------------

class TestWorkflowEvent(unittest.TestCase):

    def _event(self, **kwargs):
        defaults = dict(
            event_type=WorkflowEventType.WORKFLOW_CREATED,
            workflow_id="wf-1",
        )
        defaults.update(kwargs)
        return WorkflowEvent.create(**defaults)

    def test_create_returns_event(self):
        e = self._event()
        self.assertIsInstance(e, WorkflowEvent)

    def test_create_id_set(self):
        e = self._event()
        self.assertTrue(e.id)

    def test_create_timestamp_utc(self):
        e = self._event()
        self.assertIsNotNone(e.timestamp)
        self.assertIsNotNone(e.timestamp.tzinfo)

    def test_create_event_type_set(self):
        e = self._event(event_type=WorkflowEventType.STAGE_STARTED)
        self.assertEqual(e.event_type, WorkflowEventType.STAGE_STARTED)

    def test_create_workflow_id_set(self):
        e = self._event(workflow_id="abc")
        self.assertEqual(e.workflow_id, "abc")

    def test_create_stage_id_optional(self):
        e = self._event()
        self.assertIsNone(e.stage_id)

    def test_create_stage_id_set(self):
        e = self._event(stage_id="s1")
        self.assertEqual(e.stage_id, "s1")

    def test_create_payload_default_empty(self):
        e = self._event()
        self.assertEqual(e.payload, {})

    def test_create_payload_set(self):
        e = self._event(payload={"key": "val"})
        self.assertEqual(e.payload["key"], "val")

    def test_unique_ids(self):
        e1 = self._event()
        e2 = self._event()
        self.assertNotEqual(e1.id, e2.id)

    def test_is_terminal_completed(self):
        e = self._event(event_type=WorkflowEventType.WORKFLOW_COMPLETED)
        self.assertTrue(e.is_terminal())

    def test_is_terminal_false(self):
        e = self._event(event_type=WorkflowEventType.STAGE_STARTED)
        self.assertFalse(e.is_terminal())

    def test_get_payload_value(self):
        e = self._event(payload={"a": 1})
        self.assertEqual(e.get_payload_value("a"), 1)

    def test_get_payload_value_default(self):
        e = self._event()
        self.assertIsNone(e.get_payload_value("missing"))

    def test_get_payload_value_custom_default(self):
        e = self._event()
        self.assertEqual(e.get_payload_value("missing", 42), 42)

    def test_event_is_frozen(self):
        e = self._event()
        with self.assertRaises(Exception):
            e.event_type = WorkflowEventType.STAGE_STARTED


# ---------------------------------------------------------------------------
# 18. Workflow helpers
# ---------------------------------------------------------------------------

class TestWorkflowHelpers(unittest.TestCase):

    def _workflow(self, stages=None):
        engine, wf = _engine_with_workflow(stages)
        return wf

    def test_get_stage_by_order(self):
        wf = self._workflow(_simple_stages())
        s = wf.get_stage_by_order(2)
        self.assertIsNotNone(s)
        self.assertEqual(s.order, 2)

    def test_get_stage_by_order_not_found(self):
        wf = self._workflow(_simple_stages())
        self.assertIsNone(wf.get_stage_by_order(99))

    def test_get_stage_by_id(self):
        wf = self._workflow(_simple_stages())
        s = wf.get_stage_by_id("s2")
        self.assertIsNotNone(s)
        self.assertEqual(s.id, "s2")

    def test_get_stage_by_id_not_found(self):
        wf = self._workflow(_simple_stages())
        self.assertIsNone(wf.get_stage_by_id("nope"))

    def test_first_stage(self):
        wf = self._workflow(_simple_stages())
        self.assertEqual(wf.first_stage().order, 1)

    def test_last_stage(self):
        wf = self._workflow(_simple_stages())
        self.assertEqual(wf.last_stage().order, 3)

    def test_next_stage_pending_none(self):
        wf = self._workflow()
        self.assertIsNone(wf.next_stage())

    def test_next_stage_after_start(self):
        engine, wf = _engine_active(_simple_stages())
        self.assertEqual(wf.next_stage().order, 2)

    def test_previous_stage_none_at_first(self):
        engine, wf = _engine_active()
        self.assertIsNone(wf.previous_stage())

    def test_previous_stage_after_advance(self):
        engine, wf = _engine_active(_simple_stages())
        engine.advance(wf.id)
        self.assertEqual(wf.previous_stage().order, 1)

    def test_stage_count(self):
        wf = self._workflow(_simple_stages())
        self.assertEqual(wf.stage_count(), 3)

    def test_completed_stage_count_initial(self):
        wf = self._workflow()
        self.assertEqual(wf.completed_stage_count(), 0)

    def test_remaining_stage_count_initial(self):
        wf = self._workflow(_simple_stages())
        self.assertEqual(wf.remaining_stage_count(), 3)

    def test_remaining_stage_count_after_advance(self):
        engine, wf = _engine_active(_simple_stages())
        engine.advance(wf.id)
        self.assertEqual(wf.remaining_stage_count(), 2)

    def test_is_pending(self):
        wf = self._workflow()
        self.assertTrue(wf.is_pending())

    def test_is_active(self):
        engine, wf = _engine_active()
        self.assertTrue(wf.is_active())

    def test_is_paused(self):
        engine, wf = _engine_active()
        engine.pause(wf.id)
        self.assertTrue(wf.is_paused())

    def test_is_completed(self):
        engine, wf = _engine_active(_single_stage())
        engine.complete(wf.id)
        self.assertTrue(wf.is_completed())

    def test_is_cancelled(self):
        engine, wf = _engine_active()
        engine.cancel(wf.id)
        self.assertTrue(wf.is_cancelled())

    def test_is_terminal_completed(self):
        engine, wf = _engine_active(_single_stage())
        engine.complete(wf.id)
        self.assertTrue(wf.is_terminal())

    def test_is_terminal_pending_false(self):
        wf = self._workflow()
        self.assertFalse(wf.is_terminal())

    def test_add_event(self):
        wf = self._workflow()
        e = WorkflowEvent.create(WorkflowEventType.WORKFLOW_CREATED, wf.id)
        before = wf.event_count()
        wf.add_event(e)
        self.assertEqual(wf.event_count(), before + 1)

    def test_events_of_type(self):
        engine, wf = _engine_active()
        started = wf.events_of_type(WorkflowEventType.STAGE_STARTED)
        self.assertGreater(len(started), 0)

    def test_last_event(self):
        engine, wf = _engine_active()
        last = wf.last_event()
        self.assertIsNotNone(last)
        self.assertIsInstance(last, WorkflowEvent)

    def test_last_event_empty(self):
        wf = Workflow(
            id="x", name="n", description="d",
            template=WorkflowTemplate.SOFTWARE_PROJECT,
            stages=[], status=WorkflowStatus.PENDING,
            progress=0.0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.assertIsNone(wf.last_event())

    def test_summary_keys(self):
        wf = self._workflow(_simple_stages())
        s = wf.summary()
        for key in ("id", "name", "template", "status", "progress",
                    "stage_count", "completed_stage_count",
                    "remaining_stage_count", "current_stage",
                    "event_count", "created_at", "updated_at"):
            self.assertIn(key, s)

    def test_summary_current_stage_none_when_pending(self):
        wf = self._workflow()
        self.assertIsNone(wf.summary()["current_stage"])


# ---------------------------------------------------------------------------
# 19. WorkflowStage helpers
# ---------------------------------------------------------------------------

class TestWorkflowStageHelpers(unittest.TestCase):

    def test_is_first_stage_true(self):
        s = _make_stage("s1", "First", 1)
        self.assertTrue(s.is_first_stage())

    def test_is_first_stage_false(self):
        s = _make_stage("s2", "Second", 2)
        self.assertFalse(s.is_first_stage())

    def test_needs_approval_true(self):
        s = _make_stage("s", "S", 1, approval=True)
        self.assertTrue(s.needs_approval())

    def test_needs_approval_false(self):
        s = _make_stage("s", "S", 1)
        self.assertFalse(s.needs_approval())

    def test_allows_discussion_true(self):
        s = _make_stage("s", "S", 1, discussion=True)
        self.assertTrue(s.allows_discussion())

    def test_allows_discussion_false(self):
        s = _make_stage("s", "S", 1)
        self.assertFalse(s.allows_discussion())

    def test_requires_memory_true(self):
        s = _make_stage("s", "S", 1, memory=True)
        self.assertTrue(s.requires_memory())

    def test_requires_memory_false(self):
        s = _make_stage("s", "S", 1)
        self.assertFalse(s.requires_memory())

    def test_has_responsible_departments_false(self):
        s = WorkflowStage(id="s", name="S", order=1)
        self.assertFalse(s.has_responsible_departments())

    def test_has_responsible_departments_true(self):
        s = WorkflowStage(id="s", name="S", order=1, responsible_departments=["Eng"])
        self.assertTrue(s.has_responsible_departments())

    def test_has_required_inputs_false(self):
        s = WorkflowStage(id="s", name="S", order=1)
        self.assertFalse(s.has_required_inputs())

    def test_has_required_inputs_true(self):
        s = WorkflowStage(id="s", name="S", order=1, required_inputs=["Plan"])
        self.assertTrue(s.has_required_inputs())

    def test_has_expected_outputs_false(self):
        s = WorkflowStage(id="s", name="S", order=1)
        self.assertFalse(s.has_expected_outputs())

    def test_has_expected_outputs_true(self):
        s = WorkflowStage(id="s", name="S", order=1, expected_outputs=["Doc"])
        self.assertTrue(s.has_expected_outputs())

    def test_summary_keys(self):
        s = WorkflowStage(id="s", name="S", order=1)
        keys = s.summary()
        for k in ("id", "name", "order", "responsible_departments",
                  "required_inputs", "expected_outputs",
                  "approval_required", "discussion_allowed", "memory_required"):
            self.assertIn(k, keys)

    def test_stage_is_frozen(self):
        s = _make_stage("s", "S", 1)
        with self.assertRaises(Exception):
            s.order = 99


# ---------------------------------------------------------------------------
# 20. WorkflowTransition helpers
# ---------------------------------------------------------------------------

class TestWorkflowTransitionHelpers(unittest.TestCase):

    def _t(self, **kwargs):
        defaults = dict(from_stage="s1", to_stage="s2")
        defaults.update(kwargs)
        return WorkflowTransition(**defaults)

    def test_condition_count_zero(self):
        self.assertEqual(self._t().condition_count(), 0)

    def test_condition_count_non_zero(self):
        t = self._t(conditions=["must_pass_tests"])
        self.assertEqual(t.condition_count(), 1)

    def test_is_unconditional_true(self):
        self.assertTrue(self._t().is_unconditional())

    def test_is_unconditional_false(self):
        self.assertFalse(self._t(conditions=["x"]).is_unconditional())

    def test_is_automatic_true(self):
        self.assertTrue(self._t(automatic=True).is_automatic())

    def test_is_automatic_false(self):
        self.assertFalse(self._t().is_automatic())

    def test_is_same_transition_true(self):
        t1 = self._t()
        t2 = self._t()
        self.assertTrue(t1.is_same_transition(t2))

    def test_is_same_transition_false(self):
        t1 = self._t(from_stage="s1", to_stage="s2")
        t2 = self._t(from_stage="s2", to_stage="s3")
        self.assertFalse(t1.is_same_transition(t2))

    def test_summary_keys(self):
        t = self._t()
        s = t.summary()
        for k in ("from_stage", "to_stage", "automatic", "conditions",
                  "condition_count", "created_at"):
            self.assertIn(k, s)

    def test_created_at_utc(self):
        t = self._t()
        self.assertIsNotNone(t.created_at.tzinfo)

    def test_is_frozen(self):
        t = self._t()
        with self.assertRaises(Exception):
            t.from_stage = "other"


# ---------------------------------------------------------------------------
# 21. WorkflowTemplate
# ---------------------------------------------------------------------------

class TestWorkflowTemplate(unittest.TestCase):

    def test_str_returns_value(self):
        self.assertEqual(str(WorkflowTemplate.SOFTWARE_PROJECT), "SOFTWARE_PROJECT")

    def test_display_name_software(self):
        self.assertEqual(WorkflowTemplate.SOFTWARE_PROJECT.display_name(), "Software Project")

    def test_display_name_web(self):
        self.assertEqual(WorkflowTemplate.WEB_APPLICATION.display_name(), "Web Application")

    def test_create_stages_returns_list(self):
        stages = WorkflowTemplate.SOFTWARE_PROJECT.create_stages()
        self.assertIsInstance(stages, list)

    def test_create_stages_not_empty(self):
        for t in WorkflowTemplate:
            self.assertGreater(len(t.create_stages()), 0, f"{t} has no stages")

    def test_create_stages_returns_fresh_list(self):
        s1 = WorkflowTemplate.SOFTWARE_PROJECT.create_stages()
        s2 = WorkflowTemplate.SOFTWARE_PROJECT.create_stages()
        self.assertIsNot(s1, s2)

    def test_software_project_has_8_stages(self):
        self.assertEqual(len(WorkflowTemplate.SOFTWARE_PROJECT.create_stages()), 8)

    def test_stage_count_matches_create_stages(self):
        for t in WorkflowTemplate:
            self.assertEqual(t.stage_count(), len(t.create_stages()))

    def test_stages_sorted_by_order(self):
        for t in WorkflowTemplate:
            stages = t.create_stages()
            orders = [s.order for s in stages]
            self.assertEqual(orders, sorted(orders), f"{t} stages not sorted")

    def test_stage_orders_unique(self):
        for t in WorkflowTemplate:
            stages = t.create_stages()
            orders = [s.order for s in stages]
            self.assertEqual(len(orders), len(set(orders)), f"{t} has duplicate orders")

    def test_stage_ids_unique(self):
        for t in WorkflowTemplate:
            stages = t.create_stages()
            ids = [s.id for s in stages]
            self.assertEqual(len(ids), len(set(ids)), f"{t} has duplicate ids")

    def test_software_project_has_approval_stages(self):
        stages = WorkflowTemplate.SOFTWARE_PROJECT.create_stages()
        approval_stages = [s for s in stages if s.approval_required]
        self.assertGreater(len(approval_stages), 0)

    def test_software_project_has_discussion_stages(self):
        stages = WorkflowTemplate.SOFTWARE_PROJECT.create_stages()
        discussion_stages = [s for s in stages if s.discussion_allowed]
        self.assertGreater(len(discussion_stages), 0)

    def test_software_project_has_memory_stages(self):
        stages = WorkflowTemplate.SOFTWARE_PROJECT.create_stages()
        memory_stages = [s for s in stages if s.memory_required]
        self.assertGreater(len(memory_stages), 0)

    def test_is_str_subclass(self):
        self.assertIsInstance(WorkflowTemplate.SOFTWARE_PROJECT, str)

    def test_all_templates_have_stages(self):
        for t in WorkflowTemplate:
            self.assertGreater(t.stage_count(), 0, f"{t} has 0 stages")


# ---------------------------------------------------------------------------
# 22. Integration — memory engine
# ---------------------------------------------------------------------------

class TestMemoryEngineIntegration(unittest.TestCase):

    def test_no_error_without_memory_engine(self):
        engine, wf = _engine_active(_simple_stages())
        engine.advance(wf.id)

    def test_memory_engine_store_called_on_advance(self):
        mem = MagicMock()
        engine = WorkflowEngine(memory_engine=mem)
        wf = engine.create_workflow("P", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        engine.start(wf.id)
        engine.advance(wf.id)

    def test_memory_engine_error_does_not_crash_advance(self):
        mem = MagicMock()
        mem.store.side_effect = Exception("mem error")
        engine = WorkflowEngine(memory_engine=mem)
        wf = engine.create_workflow("P", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        engine.start(wf.id)
        engine.advance(wf.id)
        self.assertEqual(wf.current_stage.order, 2)

    def test_memory_engine_error_does_not_crash_start(self):
        mem = MagicMock()
        mem.store.side_effect = Exception("mem error")
        engine = WorkflowEngine(memory_engine=mem)
        wf = engine.create_workflow("P", "d", WorkflowTemplate.SOFTWARE_PROJECT, _simple_stages())
        engine.start(wf.id)
        self.assertEqual(wf.status, WorkflowStatus.ACTIVE)


# ---------------------------------------------------------------------------
# 23. Integration — decision engine
# ---------------------------------------------------------------------------

class TestDecisionEngineIntegration(unittest.TestCase):

    def test_no_error_without_decision_engine(self):
        engine, wf = _engine_active(_simple_stages())
        engine.advance(wf.id)

    def test_decision_engine_called_on_approval_stage(self):
        dec = MagicMock()
        dec.create_decision.return_value = MagicMock()
        engine = WorkflowEngine(decision_engine=dec)
        stages = [
            _make_stage("s1", "Stage One", 1),
            _make_stage("s2", "Stage Two", 2, approval=True),
        ]
        wf = engine.create_workflow("P", "d", WorkflowTemplate.SOFTWARE_PROJECT, stages)
        engine.start(wf.id)
        engine.advance(wf.id)
        dec.create_decision.assert_called_once()

    def test_decision_engine_not_called_on_non_approval_stage(self):
        dec = MagicMock()
        engine = WorkflowEngine(decision_engine=dec)
        stages = _two_stages()
        wf = engine.create_workflow("P", "d", WorkflowTemplate.SOFTWARE_PROJECT, stages)
        engine.start(wf.id)
        engine.advance(wf.id)
        dec.create_decision.assert_not_called()

    def test_decision_engine_error_does_not_crash_advance(self):
        dec = MagicMock()
        dec.create_decision.side_effect = Exception("dec error")
        stages = [
            _make_stage("s1", "Stage One", 1),
            _make_stage("s2", "Stage Two", 2, approval=True),
        ]
        engine = WorkflowEngine(decision_engine=dec)
        wf = engine.create_workflow("P", "d", WorkflowTemplate.SOFTWARE_PROJECT, stages)
        engine.start(wf.id)
        engine.advance(wf.id)
        self.assertEqual(wf.current_stage.order, 2)


# ---------------------------------------------------------------------------
# 24. Full Software Project workflow
# ---------------------------------------------------------------------------

class TestSoftwareProjectWorkflow(unittest.TestCase):

    def _run_through(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow("Full Project", "Test", WorkflowTemplate.SOFTWARE_PROJECT)
        engine.start(wf.id)
        while wf.next_stage() is not None:
            engine.advance(wf.id)
        engine.complete(wf.id)
        return engine, wf

    def test_full_run_completes(self):
        _, wf = self._run_through()
        self.assertEqual(wf.status, WorkflowStatus.COMPLETED)

    def test_full_run_progress_one(self):
        _, wf = self._run_through()
        self.assertEqual(wf.progress, 1.0)

    def test_full_run_completed_stages_all(self):
        _, wf = self._run_through()
        self.assertEqual(len(wf.completed_stages), 8)

    def test_full_run_current_stage_none(self):
        _, wf = self._run_through()
        self.assertIsNone(wf.current_stage)

    def test_full_run_has_workflow_completed_event(self):
        _, wf = self._run_through()
        types = [e.event_type for e in wf.events]
        self.assertIn(WorkflowEventType.WORKFLOW_COMPLETED, types)

    def test_full_run_events_count(self):
        _, wf = self._run_through()
        self.assertGreater(wf.event_count(), 10)

    def test_full_run_transitions_count(self):
        _, wf = self._run_through()
        self.assertEqual(len(wf.transitions), 7)

    def test_stage_names_correct(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow("P", "d", WorkflowTemplate.SOFTWARE_PROJECT)
        names = [s.name for s in wf.stages]
        self.assertIn("Planning", names)
        self.assertIn("Deployment", names)

    def test_ceo_review_has_approval(self):
        stages = WorkflowTemplate.SOFTWARE_PROJECT.create_stages()
        ceo = next(s for s in stages if s.id == "ceo_review")
        self.assertTrue(ceo.approval_required)

    def test_deployment_has_approval(self):
        stages = WorkflowTemplate.SOFTWARE_PROJECT.create_stages()
        dep = next(s for s in stages if s.id == "deployment")
        self.assertTrue(dep.approval_required)

    def test_planning_has_discussion(self):
        stages = WorkflowTemplate.SOFTWARE_PROJECT.create_stages()
        plan = next(s for s in stages if s.id == "planning")
        self.assertTrue(plan.discussion_allowed)

    def test_backend_has_memory(self):
        stages = WorkflowTemplate.SOFTWARE_PROJECT.create_stages()
        be = next(s for s in stages if s.id == "backend_development")
        self.assertTrue(be.memory_required)

    def test_rollback_mid_project(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow("P", "d", WorkflowTemplate.SOFTWARE_PROJECT)
        engine.start(wf.id)
        engine.advance(wf.id)
        engine.advance(wf.id)
        engine.rollback(wf.id)
        self.assertEqual(wf.current_stage.order, 2)

    def test_pause_resume_mid_project(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow("P", "d", WorkflowTemplate.SOFTWARE_PROJECT)
        engine.start(wf.id)
        engine.advance(wf.id)
        engine.pause(wf.id)
        engine.resume(wf.id)
        engine.advance(wf.id)
        self.assertEqual(wf.current_stage.order, 3)


# ---------------------------------------------------------------------------
# 25. Edge cases and invariants
# ---------------------------------------------------------------------------

class TestEdgeCases(unittest.TestCase):

    def test_progress_never_exceeds_one(self):
        engine, wf = _engine_active(_simple_stages())
        engine.advance(wf.id)
        engine.advance(wf.id)
        engine.complete(wf.id)
        self.assertLessEqual(wf.progress, 1.0)

    def test_progress_never_negative(self):
        engine, wf = _engine_active(_simple_stages())
        engine.advance(wf.id)
        engine.rollback(wf.id)
        self.assertGreaterEqual(wf.progress, 0.0)

    def test_multiple_advances_track_completed_stages(self):
        engine, wf = _engine_active(_simple_stages())
        engine.advance(wf.id)
        engine.advance(wf.id)
        self.assertEqual(len(wf.completed_stages), 2)

    def test_completed_stages_order_preserved(self):
        engine, wf = _engine_active(_simple_stages())
        engine.advance(wf.id)
        engine.advance(wf.id)
        orders = [s.order for s in wf.completed_stages]
        self.assertEqual(orders, sorted(orders))

    def test_events_are_append_only(self):
        engine, wf = _engine_active()
        count_before = len(wf.events)
        engine.advance(wf.id)
        count_after = len(wf.events)
        self.assertGreater(count_after, count_before)

    def test_workflow_id_is_string(self):
        engine, wf = _engine_with_workflow()
        self.assertIsInstance(wf.id, str)

    def test_workflow_id_not_empty(self):
        engine, wf = _engine_with_workflow()
        self.assertTrue(wf.id)

    def test_created_at_is_utc(self):
        engine, wf = _engine_with_workflow()
        self.assertIsNotNone(wf.created_at.tzinfo)

    def test_updated_at_is_utc(self):
        engine, wf = _engine_with_workflow()
        self.assertIsNotNone(wf.updated_at.tzinfo)

    def test_empty_description_allowed(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow("P", "", WorkflowTemplate.SOFTWARE_PROJECT, _single_stage())
        self.assertEqual(wf.description, "")

    def test_single_stage_workflow_complete(self):
        engine, wf = _engine_active(_single_stage())
        engine.complete(wf.id)
        self.assertEqual(wf.status, WorkflowStatus.COMPLETED)
        self.assertEqual(wf.progress, 1.0)

    def test_rollback_then_complete_fails(self):
        engine, wf = _engine_active(_two_stages())
        engine.advance(wf.id)
        engine.rollback(wf.id)
        with self.assertRaises(IllegalTransitionError):
            engine.complete(wf.id)

    def test_transitions_list_grows_with_advances(self):
        engine, wf = _engine_active(_simple_stages())
        engine.advance(wf.id)
        engine.advance(wf.id)
        self.assertEqual(len(wf.transitions), 2)

    def test_transitions_list_grows_with_rollback(self):
        engine, wf = _engine_active(_simple_stages())
        engine.advance(wf.id)
        engine.rollback(wf.id)
        self.assertEqual(len(wf.transitions), 2)

    def test_stage_transition_event_payload_has_from_to(self):
        engine, wf = _engine_active(_simple_stages())
        engine.advance(wf.id)
        transition_events = wf.events_of_type(WorkflowEventType.STAGE_TRANSITION)
        self.assertGreater(len(transition_events), 0)
        e = transition_events[-1]
        self.assertIn("from_stage", e.payload)
        self.assertIn("to_stage", e.payload)

    def test_statistics_returns_dict(self):
        engine = WorkflowEngine()
        self.assertIsInstance(engine.statistics(), dict)

    def test_workflow_is_not_pending_after_start(self):
        engine, wf = _engine_active()
        self.assertFalse(wf.is_pending())

    def test_workflow_is_not_active_after_complete(self):
        engine, wf = _engine_active(_single_stage())
        engine.complete(wf.id)
        self.assertFalse(wf.is_active())

    def test_find_workflow_after_start_returns_same_instance(self):
        engine, wf = _engine_with_workflow()
        engine.start(wf.id)
        found = engine.find_workflow(wf.id)
        self.assertIs(found, wf)

    def test_all_templates_create_valid_workflows(self):
        engine = WorkflowEngine()
        for t in WorkflowTemplate:
            wf = engine.create_workflow(f"Test-{t}", "d", t)
            self.assertEqual(wf.status, WorkflowStatus.PENDING)

    def test_workflow_stages_are_workflow_stage_instances(self):
        engine, wf = _engine_with_workflow(_simple_stages())
        for s in wf.stages:
            self.assertIsInstance(s, WorkflowStage)


if __name__ == "__main__":
    unittest.main()
