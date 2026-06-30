"""
Comprehensive unit tests for Sprint 9 — Discussion Engine.

Covers: DiscussionStatus, DiscussionParticipant, DiscussionMessage,
DiscussionOutcome, Discussion, and DiscussionEngine (all public methods
and all lifecycle transitions).

Run with:
    .venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_discussion_engine.py" -v
"""

import unittest
from datetime import datetime, timezone
from typing import Optional

from core.discussion import Discussion, DiscussionStatus
from core.discussion_engine import (
    DiscussionAlreadyOpenError,
    DiscussionClosedError,
    DiscussionEngine,
    DiscussionError,
    DiscussionNotFoundError,
    InvalidMessageError,
    InvalidOutcomeError,
    InvalidTopicError,
    ParticipantAlreadyInDiscussionError,
    ParticipantNotInDiscussionError,
)
from core.discussion_message import DiscussionMessage
from core.discussion_outcome import DiscussionOutcome
from core.discussion_participant import DiscussionParticipant


# ---------------------------------------------------------------------------
# Shared factories
# ---------------------------------------------------------------------------

def _engine() -> DiscussionEngine:
    return DiscussionEngine()


def _participant(
    pid: str = "agent-001",
    name: str = "Alice",
    role: str = "Backend Agent",
) -> DiscussionParticipant:
    return DiscussionParticipant(
        participant_id=pid,
        name=name,
        role=role,
        joined_at=datetime.now(timezone.utc),
    )


def _message(
    sender: str = "agent-001",
    role: str = "Backend Agent",
    opinion: str = "We should use REST.",
    reasoning: str = "REST is simpler to maintain and has better tooling.",
) -> DiscussionMessage:
    return DiscussionMessage(
        sender=sender,
        role=role,
        opinion=opinion,
        reasoning=reasoning,
        timestamp=datetime.now(timezone.utc),
    )


def _outcome(
    decision: str = "Use REST for the external API.",
    summary: str = "REST chosen for maintainability and tooling support.",
    actions: list | None = None,
    unresolved: list | None = None,
) -> DiscussionOutcome:
    return DiscussionOutcome(
        decision=decision,
        summary=summary,
        agreed_actions=actions or ["Implement REST endpoints in Sprint 10"],
        unresolved_points=unresolved or [],
    )


def _start(
    engine: DiscussionEngine | None = None,
    topic: str = "Should we use REST or GraphQL?",
    project_id: str | None = "proj-001",
    task_id: str | None = None,
    creator: DiscussionParticipant | None = None,
) -> tuple[DiscussionEngine, Discussion]:
    eng = engine or _engine()
    disc = eng.start_discussion(
        topic=topic,
        project_id=project_id,
        task_id=task_id,
        creator=creator,
    )
    return eng, disc


def _start_with_participant(
    engine: DiscussionEngine | None = None,
    participant: DiscussionParticipant | None = None,
) -> tuple[DiscussionEngine, Discussion, DiscussionParticipant]:
    eng, disc = _start(engine=engine)
    p = participant or _participant()
    eng.join(disc.id, p)
    return eng, disc, p


def _post(eng: DiscussionEngine, disc_id: str, **kwargs) -> DiscussionMessage:
    msg = _message(**kwargs)
    eng.post_message(disc_id, msg)
    return msg


def _close_with_outcome(
    eng: DiscussionEngine,
    disc_id: str,
    outcome: DiscussionOutcome | None = None,
) -> Discussion:
    return eng.close(disc_id, outcome or _outcome())


# ---------------------------------------------------------------------------
# TestDiscussionStatus
# ---------------------------------------------------------------------------

class TestDiscussionStatus(unittest.TestCase):

    def test_two_values_exist(self) -> None:
        names = {s.name for s in DiscussionStatus}
        self.assertEqual(names, {"OPEN", "CLOSED"})

    def test_str_returns_value(self) -> None:
        for s in DiscussionStatus:
            self.assertEqual(str(s), s.value)

    def test_is_str_subclass(self) -> None:
        self.assertIsInstance(DiscussionStatus.OPEN, str)

    def test_string_comparison(self) -> None:
        self.assertEqual(DiscussionStatus.OPEN, "OPEN")
        self.assertEqual(DiscussionStatus.CLOSED, "CLOSED")

    def test_values_are_distinct(self) -> None:
        self.assertNotEqual(DiscussionStatus.OPEN, DiscussionStatus.CLOSED)


# ---------------------------------------------------------------------------
# TestDiscussionParticipant
# ---------------------------------------------------------------------------

class TestDiscussionParticipant(unittest.TestCase):

    def test_fields_stored(self) -> None:
        now = datetime.now(timezone.utc)
        p = DiscussionParticipant("p1", "Alice", "Backend Agent", now)
        self.assertEqual(p.participant_id, "p1")
        self.assertEqual(p.name, "Alice")
        self.assertEqual(p.role, "Backend Agent")
        self.assertEqual(p.joined_at, now)

    def test_is_mutable(self) -> None:
        p = _participant()
        p.name = "Changed"
        self.assertEqual(p.name, "Changed")

    def test_equality_by_id(self) -> None:
        p1 = _participant(pid="x", name="Alice")
        p2 = _participant(pid="x", name="Bob")
        self.assertEqual(p1, p2)

    def test_inequality_different_ids(self) -> None:
        self.assertNotEqual(_participant("a"), _participant("b"))

    def test_hash_by_id(self) -> None:
        p1 = _participant(pid="x")
        p2 = _participant(pid="x")
        self.assertEqual(hash(p1), hash(p2))

    def test_can_be_used_in_set(self) -> None:
        participants = {_participant("a"), _participant("b"), _participant("a")}
        self.assertEqual(len(participants), 2)

    def test_repr_contains_id_and_name(self) -> None:
        p = _participant(pid="abc-123", name="Alice")
        r = repr(p)
        self.assertIn("abc-123", r)
        self.assertIn("Alice", r)

    def test_joined_at_is_datetime(self) -> None:
        p = _participant()
        self.assertIsInstance(p.joined_at, datetime)


# ---------------------------------------------------------------------------
# TestDiscussionMessage
# ---------------------------------------------------------------------------

class TestDiscussionMessage(unittest.TestCase):

    def test_fields_stored(self) -> None:
        now = datetime.now(timezone.utc)
        msg = DiscussionMessage("s1", "QA", "Use mocks.", "Faster tests.", now)
        self.assertEqual(msg.sender, "s1")
        self.assertEqual(msg.role, "QA")
        self.assertEqual(msg.opinion, "Use mocks.")
        self.assertEqual(msg.reasoning, "Faster tests.")
        self.assertEqual(msg.timestamp, now)

    def test_is_frozen(self) -> None:
        msg = _message()
        with self.assertRaises(Exception):
            msg.opinion = "changed"  # type: ignore[misc]

    def test_is_from_true(self) -> None:
        msg = _message(sender="alice")
        self.assertTrue(msg.is_from("alice"))

    def test_is_from_false(self) -> None:
        msg = _message(sender="alice")
        self.assertFalse(msg.is_from("bob"))

    def test_has_strong_reasoning_true(self) -> None:
        msg = _message(reasoning="A" * 25)
        self.assertTrue(msg.has_strong_reasoning())

    def test_has_strong_reasoning_false_short(self) -> None:
        msg = _message(reasoning="Short.")
        self.assertFalse(msg.has_strong_reasoning())

    def test_has_strong_reasoning_custom_threshold(self) -> None:
        msg = _message(reasoning="Ten chars!")
        self.assertTrue(msg.has_strong_reasoning(min_length=10))
        self.assertFalse(msg.has_strong_reasoning(min_length=11))

    def test_timestamp_is_datetime(self) -> None:
        self.assertIsInstance(_message().timestamp, datetime)

    def test_multiple_messages_with_same_sender(self) -> None:
        m1 = _message(sender="alice", opinion="Option A")
        m2 = _message(sender="alice", opinion="Option B")
        self.assertNotEqual(m1.opinion, m2.opinion)
        self.assertTrue(m1.is_from("alice") and m2.is_from("alice"))


# ---------------------------------------------------------------------------
# TestDiscussionOutcome
# ---------------------------------------------------------------------------

class TestDiscussionOutcome(unittest.TestCase):

    def test_fields_stored(self) -> None:
        o = _outcome(
            decision="Use REST.",
            summary="REST chosen.",
            actions=["Implement REST"],
            unresolved=["Subscriptions"],
        )
        self.assertEqual(o.decision, "Use REST.")
        self.assertEqual(o.summary, "REST chosen.")
        self.assertEqual(o.agreed_actions, ["Implement REST"])
        self.assertEqual(o.unresolved_points, ["Subscriptions"])

    def test_is_frozen(self) -> None:
        o = _outcome()
        with self.assertRaises(Exception):
            o.decision = "changed"  # type: ignore[misc]

    def test_defaults_empty_lists(self) -> None:
        o = DiscussionOutcome(decision="X", summary="Y")
        self.assertEqual(o.agreed_actions, [])
        self.assertEqual(o.unresolved_points, [])

    def test_is_fully_resolved_true(self) -> None:
        o = DiscussionOutcome(decision="X", summary="Y", unresolved_points=[])
        self.assertTrue(o.is_fully_resolved())

    def test_is_fully_resolved_false(self) -> None:
        o = DiscussionOutcome(decision="X", summary="Y", unresolved_points=["open"])
        self.assertFalse(o.is_fully_resolved())

    def test_action_count(self) -> None:
        o = DiscussionOutcome(decision="X", summary="Y", agreed_actions=["a", "b", "c"])
        self.assertEqual(o.action_count(), 3)

    def test_unresolved_count(self) -> None:
        o = DiscussionOutcome(decision="X", summary="Y", unresolved_points=["p1", "p2"])
        self.assertEqual(o.unresolved_count(), 2)

    def test_has_actions_true(self) -> None:
        self.assertTrue(_outcome(actions=["do something"]).has_actions())

    def test_has_actions_false(self) -> None:
        o = DiscussionOutcome(decision="X", summary="Y", agreed_actions=[])
        self.assertFalse(o.has_actions())

    def test_decided_at_optional(self) -> None:
        o = DiscussionOutcome(decision="X", summary="Y")
        self.assertIsNone(o.decided_at)

    def test_decided_by_optional(self) -> None:
        o = DiscussionOutcome(decision="X", summary="Y")
        self.assertIsNone(o.decided_by)


# ---------------------------------------------------------------------------
# TestDiscussion
# ---------------------------------------------------------------------------

class TestDiscussion(unittest.TestCase):

    def setUp(self) -> None:
        self.eng, self.disc = _start()

    def test_fields_stored(self) -> None:
        d = self.disc
        self.assertEqual(d.topic, "Should we use REST or GraphQL?")
        self.assertEqual(d.project_id, "proj-001")
        self.assertEqual(d.status, DiscussionStatus.OPEN)
        self.assertIsInstance(d.created_at, datetime)
        self.assertIsNone(d.closed_at)
        self.assertIsNone(d.outcome)
        self.assertEqual(d.messages, [])

    def test_id_is_uuid(self) -> None:
        self.assertEqual(len(self.disc.id), 36)

    def test_is_open_true(self) -> None:
        self.assertTrue(self.disc.is_open())

    def test_is_open_false_when_closed(self) -> None:
        self.eng.join(self.disc.id, _participant())
        _close_with_outcome(self.eng, self.disc.id)
        self.assertFalse(self.disc.is_open())

    def test_is_closed_false_when_open(self) -> None:
        self.assertFalse(self.disc.is_closed())

    def test_is_closed_true_when_closed(self) -> None:
        self.eng.join(self.disc.id, _participant())
        _close_with_outcome(self.eng, self.disc.id)
        self.assertTrue(self.disc.is_closed())

    def test_participant_count(self) -> None:
        self.assertEqual(self.disc.participant_count(), 0)
        self.eng.join(self.disc.id, _participant("a"))
        self.assertEqual(self.disc.participant_count(), 1)

    def test_participant_ids(self) -> None:
        self.eng.join(self.disc.id, _participant("a"))
        self.eng.join(self.disc.id, _participant("b"))
        ids = self.disc.participant_ids()
        self.assertIn("a", ids)
        self.assertIn("b", ids)

    def test_has_participant_true(self) -> None:
        self.eng.join(self.disc.id, _participant("x"))
        self.assertTrue(self.disc.has_participant("x"))

    def test_has_participant_false(self) -> None:
        self.assertFalse(self.disc.has_participant("nonexistent"))

    def test_get_participant_returns_correct(self) -> None:
        p = _participant("abc")
        self.eng.join(self.disc.id, p)
        found = self.disc.get_participant("abc")
        self.assertIs(found, p)

    def test_get_participant_missing_returns_none(self) -> None:
        self.assertIsNone(self.disc.get_participant("not-here"))

    def test_message_count(self) -> None:
        self.assertEqual(self.disc.message_count(), 0)

    def test_messages_by_sender(self) -> None:
        self.eng.join(self.disc.id, _participant("a"))
        self.eng.join(self.disc.id, _participant("b"))
        self.eng.post_message(self.disc.id, _message(sender="a", opinion="A1"))
        self.eng.post_message(self.disc.id, _message(sender="b", opinion="B1"))
        self.eng.post_message(self.disc.id, _message(sender="a", opinion="A2"))
        by_a = self.disc.messages_by("a")
        self.assertEqual(len(by_a), 2)
        self.assertTrue(all(m.sender == "a" for m in by_a))

    def test_last_message_none_when_empty(self) -> None:
        self.assertIsNone(self.disc.last_message())

    def test_last_message_returns_latest(self) -> None:
        self.eng.join(self.disc.id, _participant("a"))
        self.eng.post_message(self.disc.id, _message(sender="a", opinion="First"))
        self.eng.post_message(self.disc.id, _message(sender="a", opinion="Second"))
        self.assertEqual(self.disc.last_message().opinion, "Second")

    def test_opinion_map_empty(self) -> None:
        self.assertEqual(self.disc.opinion_map(), {})

    def test_opinion_map_groups_by_sender(self) -> None:
        self.eng.join(self.disc.id, _participant("a"))
        self.eng.join(self.disc.id, _participant("b"))
        self.eng.post_message(self.disc.id, _message(sender="a", opinion="Pos A"))
        self.eng.post_message(self.disc.id, _message(sender="b", opinion="Pos B"))
        self.eng.post_message(self.disc.id, _message(sender="a", opinion="Pos A2"))
        omap = self.disc.opinion_map()
        self.assertEqual(omap["a"], ["Pos A", "Pos A2"])
        self.assertEqual(omap["b"], ["Pos B"])

    def test_has_outcome_false_initially(self) -> None:
        self.assertFalse(self.disc.has_outcome())

    def test_has_outcome_true_after_close(self) -> None:
        self.eng.join(self.disc.id, _participant())
        _close_with_outcome(self.eng, self.disc.id)
        self.assertTrue(self.disc.has_outcome())


# ---------------------------------------------------------------------------
# TestEngineStartDiscussion
# ---------------------------------------------------------------------------

class TestEngineStartDiscussion(unittest.TestCase):

    def test_start_returns_discussion(self) -> None:
        _, disc = _start()
        self.assertIsInstance(disc, Discussion)

    def test_start_status_is_open(self) -> None:
        _, disc = _start()
        self.assertEqual(disc.status, DiscussionStatus.OPEN)

    def test_start_topic_stored(self) -> None:
        _, disc = _start(topic="What DB engine should we use?")
        self.assertEqual(disc.topic, "What DB engine should we use?")

    def test_start_project_id_stored(self) -> None:
        _, disc = _start(project_id="proj-XYZ")
        self.assertEqual(disc.project_id, "proj-XYZ")

    def test_start_task_id_stored(self) -> None:
        _, disc = _start(task_id="task-99")
        self.assertEqual(disc.task_id, "task-99")

    def test_start_empty_participants_by_default(self) -> None:
        _, disc = _start()
        self.assertEqual(disc.participant_count(), 0)

    def test_start_with_creator_adds_participant(self) -> None:
        creator = _participant("creator-1", "CEO", "Executive")
        _, disc = _start(creator=creator)
        self.assertEqual(disc.participant_count(), 1)
        self.assertTrue(disc.has_participant("creator-1"))

    def test_start_increments_count(self) -> None:
        eng = _engine()
        self.assertEqual(eng.count(), 0)
        eng.start_discussion("topic 1")
        self.assertEqual(eng.count(), 1)
        eng.start_discussion("topic 2")
        self.assertEqual(eng.count(), 2)

    def test_start_empty_topic_raises(self) -> None:
        eng = _engine()
        with self.assertRaises(InvalidTopicError):
            eng.start_discussion("")

    def test_start_whitespace_topic_raises(self) -> None:
        eng = _engine()
        with self.assertRaises(InvalidTopicError):
            eng.start_discussion("   ")

    def test_start_unique_ids(self) -> None:
        eng = _engine()
        ids = {eng.start_discussion(f"topic {i}").id for i in range(10)}
        self.assertEqual(len(ids), 10)

    def test_start_created_at_is_utc(self) -> None:
        before = datetime.now(timezone.utc)
        _, disc = _start()
        after = datetime.now(timezone.utc)
        self.assertGreaterEqual(disc.created_at, before)
        self.assertLessEqual(disc.created_at, after)

    def test_start_without_optional_fields(self) -> None:
        eng = _engine()
        disc = eng.start_discussion("Some topic")
        self.assertIsNone(disc.project_id)
        self.assertIsNone(disc.task_id)

    def test_start_appears_in_list_open(self) -> None:
        eng, disc = _start()
        self.assertIn(disc, eng.list_open())

    def test_start_not_in_list_closed(self) -> None:
        eng, disc = _start()
        self.assertNotIn(disc, eng.list_closed())

    def test_error_hierarchy(self) -> None:
        self.assertTrue(issubclass(InvalidTopicError, DiscussionError))
        self.assertTrue(issubclass(DiscussionNotFoundError, DiscussionError))
        self.assertTrue(issubclass(DiscussionClosedError, DiscussionError))
        self.assertTrue(issubclass(DiscussionAlreadyOpenError, DiscussionError))
        self.assertTrue(issubclass(ParticipantAlreadyInDiscussionError, DiscussionError))
        self.assertTrue(issubclass(ParticipantNotInDiscussionError, DiscussionError))
        self.assertTrue(issubclass(InvalidMessageError, DiscussionError))
        self.assertTrue(issubclass(InvalidOutcomeError, DiscussionError))


# ---------------------------------------------------------------------------
# TestEngineJoin
# ---------------------------------------------------------------------------

class TestEngineJoin(unittest.TestCase):

    def test_join_returns_discussion(self) -> None:
        eng, disc = _start()
        result = eng.join(disc.id, _participant())
        self.assertIs(result, disc)

    def test_join_adds_participant(self) -> None:
        eng, disc = _start()
        eng.join(disc.id, _participant("x"))
        self.assertTrue(disc.has_participant("x"))

    def test_join_increments_participant_count(self) -> None:
        eng, disc = _start()
        self.assertEqual(disc.participant_count(), 0)
        eng.join(disc.id, _participant("a"))
        self.assertEqual(disc.participant_count(), 1)
        eng.join(disc.id, _participant("b"))
        self.assertEqual(disc.participant_count(), 2)

    def test_join_sets_joined_at(self) -> None:
        eng, disc = _start()
        p = DiscussionParticipant("p1", "Alice", "Agent", None)
        before = datetime.now(timezone.utc)
        eng.join(disc.id, p)
        after = datetime.now(timezone.utc)
        self.assertIsNotNone(p.joined_at)
        self.assertGreaterEqual(p.joined_at, before)
        self.assertLessEqual(p.joined_at, after)

    def test_join_does_not_override_existing_joined_at(self) -> None:
        eng, disc = _start()
        preset_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        p = _participant()
        p.joined_at = preset_time
        eng.join(disc.id, p)
        self.assertEqual(p.joined_at, preset_time)

    def test_join_unknown_discussion_raises(self) -> None:
        eng = _engine()
        with self.assertRaises(DiscussionNotFoundError):
            eng.join("no-such-id", _participant())

    def test_join_closed_discussion_raises(self) -> None:
        eng, disc = _start()
        eng.join(disc.id, _participant())
        _close_with_outcome(eng, disc.id)
        with self.assertRaises(DiscussionClosedError):
            eng.join(disc.id, _participant("b"))

    def test_join_duplicate_participant_raises(self) -> None:
        eng, disc = _start()
        eng.join(disc.id, _participant("x"))
        with self.assertRaises(ParticipantAlreadyInDiscussionError):
            eng.join(disc.id, _participant("x"))

    def test_join_error_includes_participant_id(self) -> None:
        eng, disc = _start()
        eng.join(disc.id, _participant("dupe"))
        try:
            eng.join(disc.id, _participant("dupe"))
            self.fail("Expected ParticipantAlreadyInDiscussionError")
        except ParticipantAlreadyInDiscussionError as e:
            self.assertIn("dupe", str(e))

    def test_join_multiple_participants(self) -> None:
        eng, disc = _start()
        for i in range(5):
            eng.join(disc.id, _participant(f"p{i}"))
        self.assertEqual(disc.participant_count(), 5)

    def test_rejoin_after_leave_allowed(self) -> None:
        eng, disc = _start()
        p = _participant("a")
        eng.join(disc.id, p)
        eng.leave(disc.id, "a")
        eng.join(disc.id, _participant("a"))
        self.assertTrue(disc.has_participant("a"))


# ---------------------------------------------------------------------------
# TestEngineLeave
# ---------------------------------------------------------------------------

class TestEngineLeave(unittest.TestCase):

    def test_leave_returns_discussion(self) -> None:
        eng, disc, p = _start_with_participant()
        result = eng.leave(disc.id, p.participant_id)
        self.assertIs(result, disc)

    def test_leave_removes_participant(self) -> None:
        eng, disc, p = _start_with_participant()
        eng.leave(disc.id, p.participant_id)
        self.assertFalse(disc.has_participant(p.participant_id))

    def test_leave_decrements_count(self) -> None:
        eng, disc = _start()
        eng.join(disc.id, _participant("a"))
        eng.join(disc.id, _participant("b"))
        eng.leave(disc.id, "a")
        self.assertEqual(disc.participant_count(), 1)

    def test_leave_preserves_other_participants(self) -> None:
        eng, disc = _start()
        eng.join(disc.id, _participant("a"))
        eng.join(disc.id, _participant("b"))
        eng.leave(disc.id, "a")
        self.assertTrue(disc.has_participant("b"))

    def test_leave_preserves_messages(self) -> None:
        eng, disc, p = _start_with_participant()
        eng.post_message(disc.id, _message(sender=p.participant_id))
        eng.leave(disc.id, p.participant_id)
        self.assertEqual(disc.message_count(), 1)

    def test_leave_unknown_discussion_raises(self) -> None:
        eng = _engine()
        with self.assertRaises(DiscussionNotFoundError):
            eng.leave("no-such-id", "p1")

    def test_leave_closed_discussion_raises(self) -> None:
        eng, disc, p = _start_with_participant()
        _close_with_outcome(eng, disc.id)
        with self.assertRaises(DiscussionClosedError):
            eng.leave(disc.id, p.participant_id)

    def test_leave_not_in_discussion_raises(self) -> None:
        eng, disc = _start()
        with self.assertRaises(ParticipantNotInDiscussionError):
            eng.leave(disc.id, "ghost-agent")

    def test_leave_error_includes_participant_id(self) -> None:
        eng, disc = _start()
        try:
            eng.leave(disc.id, "ghost-XYZ")
            self.fail("Expected ParticipantNotInDiscussionError")
        except ParticipantNotInDiscussionError as e:
            self.assertIn("ghost-XYZ", str(e))

    def test_leave_all_participants_allows_empty_roster(self) -> None:
        eng, disc = _start()
        eng.join(disc.id, _participant("a"))
        eng.leave(disc.id, "a")
        self.assertEqual(disc.participant_count(), 0)


# ---------------------------------------------------------------------------
# TestEnginePostMessage
# ---------------------------------------------------------------------------

class TestEnginePostMessage(unittest.TestCase):

    def test_post_returns_discussion(self) -> None:
        eng, disc, p = _start_with_participant()
        result = eng.post_message(disc.id, _message(sender=p.participant_id))
        self.assertIs(result, disc)

    def test_post_appends_message(self) -> None:
        eng, disc, p = _start_with_participant()
        msg = _message(sender=p.participant_id)
        eng.post_message(disc.id, msg)
        self.assertIn(msg, disc.messages)

    def test_post_increments_message_count(self) -> None:
        eng, disc, p = _start_with_participant()
        self.assertEqual(disc.message_count(), 0)
        eng.post_message(disc.id, _message(sender=p.participant_id, opinion="A"))
        self.assertEqual(disc.message_count(), 1)
        eng.post_message(disc.id, _message(sender=p.participant_id, opinion="B"))
        self.assertEqual(disc.message_count(), 2)

    def test_post_preserves_message_order(self) -> None:
        eng, disc, p = _start_with_participant()
        for i in range(5):
            eng.post_message(disc.id, _message(
                sender=p.participant_id, opinion=f"Opinion {i}"
            ))
        for i, msg in enumerate(disc.messages):
            self.assertEqual(msg.opinion, f"Opinion {i}")

    def test_post_unknown_discussion_raises(self) -> None:
        eng = _engine()
        with self.assertRaises(DiscussionNotFoundError):
            eng.post_message("no-such-id", _message())

    def test_post_closed_discussion_raises(self) -> None:
        eng, disc, p = _start_with_participant()
        _close_with_outcome(eng, disc.id)
        with self.assertRaises(DiscussionClosedError):
            eng.post_message(disc.id, _message(sender=p.participant_id))

    def test_post_empty_opinion_raises(self) -> None:
        eng, disc, p = _start_with_participant()
        msg = DiscussionMessage(p.participant_id, "Role", "", "Valid reasoning.", datetime.now(timezone.utc))
        with self.assertRaises(InvalidMessageError):
            eng.post_message(disc.id, msg)

    def test_post_whitespace_opinion_raises(self) -> None:
        eng, disc, p = _start_with_participant()
        msg = DiscussionMessage(p.participant_id, "Role", "   ", "Valid reasoning.", datetime.now(timezone.utc))
        with self.assertRaises(InvalidMessageError):
            eng.post_message(disc.id, msg)

    def test_post_empty_reasoning_raises(self) -> None:
        eng, disc, p = _start_with_participant()
        msg = DiscussionMessage(p.participant_id, "Role", "Valid opinion.", "", datetime.now(timezone.utc))
        with self.assertRaises(InvalidMessageError):
            eng.post_message(disc.id, msg)

    def test_post_whitespace_reasoning_raises(self) -> None:
        eng, disc, p = _start_with_participant()
        msg = DiscussionMessage(p.participant_id, "Role", "Valid opinion.", "   ", datetime.now(timezone.utc))
        with self.assertRaises(InvalidMessageError):
            eng.post_message(disc.id, msg)

    def test_post_sender_not_participant_raises(self) -> None:
        eng, disc = _start()
        eng.join(disc.id, _participant("alice"))
        with self.assertRaises(ParticipantNotInDiscussionError):
            eng.post_message(disc.id, _message(sender="ghost"))

    def test_post_error_includes_sender(self) -> None:
        eng, disc = _start()
        eng.join(disc.id, _participant("alice"))
        try:
            eng.post_message(disc.id, _message(sender="mystery-agent"))
            self.fail("Expected ParticipantNotInDiscussionError")
        except ParticipantNotInDiscussionError as e:
            self.assertIn("mystery-agent", str(e))

    def test_post_multiple_participants(self) -> None:
        eng, disc = _start()
        eng.join(disc.id, _participant("a", "Alice", "Backend"))
        eng.join(disc.id, _participant("b", "Bob", "QA"))
        eng.post_message(disc.id, _message(sender="a", opinion="REST preferred"))
        eng.post_message(disc.id, _message(sender="b", opinion="GraphQL preferred"))
        self.assertEqual(disc.message_count(), 2)

    def test_post_many_messages_preserves_all(self) -> None:
        eng, disc, p = _start_with_participant()
        for i in range(10):
            eng.post_message(disc.id, _message(sender=p.participant_id, opinion=f"Op{i}"))
        self.assertEqual(disc.message_count(), 10)

    def test_post_after_reopen_works(self) -> None:
        eng, disc, p = _start_with_participant()
        _close_with_outcome(eng, disc.id)
        eng.reopen(disc.id)
        eng.post_message(disc.id, _message(sender=p.participant_id, opinion="New opinion."))
        self.assertEqual(disc.message_count(), 1)


# ---------------------------------------------------------------------------
# TestEngineSummarize
# ---------------------------------------------------------------------------

class TestEngineSummarize(unittest.TestCase):

    def test_summarize_returns_string(self) -> None:
        eng, disc = _start()
        result = eng.summarize(disc.id)
        self.assertIsInstance(result, str)

    def test_summarize_unknown_discussion_raises(self) -> None:
        eng = _engine()
        with self.assertRaises(DiscussionNotFoundError):
            eng.summarize("no-such-id")

    def test_summarize_contains_topic(self) -> None:
        eng, disc = _start(topic="Best database for the project?")
        result = eng.summarize(disc.id)
        self.assertIn("Best database for the project?", result)

    def test_summarize_contains_status(self) -> None:
        eng, disc = _start()
        result = eng.summarize(disc.id)
        self.assertIn("OPEN", result)

    def test_summarize_contains_message_count(self) -> None:
        eng, disc, p = _start_with_participant()
        eng.post_message(disc.id, _message(sender=p.participant_id, opinion="My view."))
        result = eng.summarize(disc.id)
        self.assertIn("1", result)

    def test_summarize_contains_participant_name(self) -> None:
        eng, disc = _start()
        eng.join(disc.id, _participant("a", "Dr. Alice", "Lead"))
        result = eng.summarize(disc.id)
        self.assertIn("Dr. Alice", result)

    def test_summarize_contains_opinions(self) -> None:
        eng, disc, p = _start_with_participant(participant=_participant("a", "Alice", "Lead"))
        eng.post_message(disc.id, _message(sender="a", opinion="I strongly prefer REST."))
        result = eng.summarize(disc.id)
        self.assertIn("I strongly prefer REST.", result)

    def test_summarize_works_on_closed_discussion(self) -> None:
        eng, disc, p = _start_with_participant()
        _close_with_outcome(eng, disc.id)
        result = eng.summarize(disc.id)
        self.assertIsInstance(result, str)
        self.assertIn("CLOSED", result)

    def test_summarize_contains_decision_when_closed(self) -> None:
        eng, disc, p = _start_with_participant()
        outcome = _outcome(decision="Use PostgreSQL.")
        eng.close(disc.id, outcome)
        result = eng.summarize(disc.id)
        self.assertIn("Use PostgreSQL.", result)

    def test_summarize_no_messages_handles_gracefully(self) -> None:
        eng, disc = _start()
        result = eng.summarize(disc.id)
        self.assertIn("No messages", result)

    def test_summarize_deterministic(self) -> None:
        eng, disc, p = _start_with_participant()
        eng.post_message(disc.id, _message(sender=p.participant_id, opinion="Consistent."))
        r1 = eng.summarize(disc.id)
        r2 = eng.summarize(disc.id)
        self.assertEqual(r1, r2)

    def test_summarize_contains_agreed_actions(self) -> None:
        eng, disc, p = _start_with_participant()
        outcome = _outcome(actions=["Deploy to staging ASAP."])
        eng.close(disc.id, outcome)
        result = eng.summarize(disc.id)
        self.assertIn("Deploy to staging ASAP.", result)

    def test_summarize_contains_unresolved_points(self) -> None:
        eng, disc, p = _start_with_participant()
        outcome = _outcome(unresolved=["Auth flow not decided."])
        eng.close(disc.id, outcome)
        result = eng.summarize(disc.id)
        self.assertIn("Auth flow not decided.", result)


# ---------------------------------------------------------------------------
# TestEngineClose
# ---------------------------------------------------------------------------

class TestEngineClose(unittest.TestCase):

    def test_close_returns_discussion(self) -> None:
        eng, disc, p = _start_with_participant()
        result = _close_with_outcome(eng, disc.id)
        self.assertIs(result, disc)

    def test_close_sets_status_closed(self) -> None:
        eng, disc, p = _start_with_participant()
        _close_with_outcome(eng, disc.id)
        self.assertEqual(disc.status, DiscussionStatus.CLOSED)

    def test_close_sets_outcome(self) -> None:
        eng, disc, p = _start_with_participant()
        outcome = _outcome(decision="Final choice.")
        eng.close(disc.id, outcome)
        self.assertIsNotNone(disc.outcome)

    def test_close_sets_closed_at(self) -> None:
        eng, disc, p = _start_with_participant()
        before = datetime.now(timezone.utc)
        _close_with_outcome(eng, disc.id)
        after = datetime.now(timezone.utc)
        self.assertIsNotNone(disc.closed_at)
        self.assertGreaterEqual(disc.closed_at, before)
        self.assertLessEqual(disc.closed_at, after)

    def test_close_fills_decided_at_when_none(self) -> None:
        eng, disc, p = _start_with_participant()
        o = DiscussionOutcome(decision="D", summary="S")
        eng.close(disc.id, o)
        self.assertIsNotNone(disc.outcome.decided_at)

    def test_close_preserves_decided_at_when_set(self) -> None:
        eng, disc, p = _start_with_participant()
        preset = datetime(2025, 6, 1, tzinfo=timezone.utc)
        o = DiscussionOutcome(decision="D", summary="S", decided_at=preset)
        eng.close(disc.id, o)
        self.assertEqual(disc.outcome.decided_at, preset)

    def test_close_moves_to_list_closed(self) -> None:
        eng, disc, p = _start_with_participant()
        _close_with_outcome(eng, disc.id)
        self.assertIn(disc, eng.list_closed())

    def test_close_removes_from_list_open(self) -> None:
        eng, disc, p = _start_with_participant()
        _close_with_outcome(eng, disc.id)
        self.assertNotIn(disc, eng.list_open())

    def test_close_unknown_discussion_raises(self) -> None:
        eng = _engine()
        with self.assertRaises(DiscussionNotFoundError):
            eng.close("no-id", _outcome())

    def test_close_already_closed_raises(self) -> None:
        eng, disc, p = _start_with_participant()
        _close_with_outcome(eng, disc.id)
        with self.assertRaises(DiscussionClosedError):
            eng.close(disc.id, _outcome())

    def test_close_empty_decision_raises(self) -> None:
        eng, disc, p = _start_with_participant()
        bad = DiscussionOutcome(decision="", summary="Valid summary.")
        with self.assertRaises(InvalidOutcomeError):
            eng.close(disc.id, bad)

    def test_close_whitespace_decision_raises(self) -> None:
        eng, disc, p = _start_with_participant()
        bad = DiscussionOutcome(decision="   ", summary="Valid summary.")
        with self.assertRaises(InvalidOutcomeError):
            eng.close(disc.id, bad)

    def test_close_empty_summary_raises(self) -> None:
        eng, disc, p = _start_with_participant()
        bad = DiscussionOutcome(decision="Valid decision.", summary="")
        with self.assertRaises(InvalidOutcomeError):
            eng.close(disc.id, bad)

    def test_close_with_no_messages_allowed(self) -> None:
        eng, disc = _start()
        eng.close(disc.id, _outcome())
        self.assertTrue(disc.is_closed())

    def test_close_with_unresolved_points(self) -> None:
        eng, disc = _start()
        o = _outcome(unresolved=["Point A", "Point B"])
        eng.close(disc.id, o)
        self.assertEqual(disc.outcome.unresolved_count(), 2)

    def test_close_preserves_message_history(self) -> None:
        eng, disc, p = _start_with_participant()
        eng.post_message(disc.id, _message(sender=p.participant_id))
        _close_with_outcome(eng, disc.id)
        self.assertEqual(disc.message_count(), 1)


# ---------------------------------------------------------------------------
# TestEngineReopen
# ---------------------------------------------------------------------------

class TestEngineReopen(unittest.TestCase):

    def _closed(self) -> tuple[DiscussionEngine, Discussion]:
        eng, disc = _start()
        eng.close(disc.id, _outcome())
        return eng, disc

    def test_reopen_returns_discussion(self) -> None:
        eng, disc = self._closed()
        result = eng.reopen(disc.id)
        self.assertIs(result, disc)

    def test_reopen_sets_status_open(self) -> None:
        eng, disc = self._closed()
        eng.reopen(disc.id)
        self.assertEqual(disc.status, DiscussionStatus.OPEN)

    def test_reopen_clears_closed_at(self) -> None:
        eng, disc = self._closed()
        eng.reopen(disc.id)
        self.assertIsNone(disc.closed_at)

    def test_reopen_clears_outcome(self) -> None:
        eng, disc = self._closed()
        eng.reopen(disc.id)
        self.assertIsNone(disc.outcome)

    def test_reopen_preserves_messages(self) -> None:
        eng, disc = _start()
        eng.join(disc.id, _participant("a"))
        eng.post_message(disc.id, _message(sender="a", opinion="My view."))
        eng.close(disc.id, _outcome())
        eng.reopen(disc.id)
        self.assertEqual(disc.message_count(), 1)

    def test_reopen_preserves_participants(self) -> None:
        eng, disc = _start()
        eng.join(disc.id, _participant("a"))
        eng.close(disc.id, _outcome())
        eng.reopen(disc.id)
        self.assertTrue(disc.has_participant("a"))

    def test_reopen_unknown_discussion_raises(self) -> None:
        eng = _engine()
        with self.assertRaises(DiscussionNotFoundError):
            eng.reopen("no-such-id")

    def test_reopen_already_open_raises(self) -> None:
        eng, disc = _start()
        with self.assertRaises(DiscussionAlreadyOpenError):
            eng.reopen(disc.id)

    def test_reopen_allows_new_messages(self) -> None:
        eng, disc = _start()
        eng.join(disc.id, _participant("a"))
        eng.close(disc.id, _outcome())
        eng.reopen(disc.id)
        eng.post_message(disc.id, _message(sender="a", opinion="New perspective."))
        self.assertEqual(disc.message_count(), 1)

    def test_reopen_then_close_again(self) -> None:
        eng, disc = _start()
        eng.close(disc.id, _outcome(decision="First decision."))
        eng.reopen(disc.id)
        eng.close(disc.id, _outcome(decision="Final decision."))
        self.assertEqual(disc.outcome.decision, "Final decision.")

    def test_reopen_moves_back_to_list_open(self) -> None:
        eng, disc = _start()
        eng.close(disc.id, _outcome())
        eng.reopen(disc.id)
        self.assertIn(disc, eng.list_open())
        self.assertNotIn(disc, eng.list_closed())

    def test_reopen_error_message_indicates_open(self) -> None:
        eng, disc = _start()
        try:
            eng.reopen(disc.id)
            self.fail("Expected DiscussionAlreadyOpenError")
        except DiscussionAlreadyOpenError as e:
            self.assertIn("OPEN", str(e))

    def test_multiple_reopen_close_cycles(self) -> None:
        eng, disc = _start()
        eng.join(disc.id, _participant("a"))
        for i in range(3):
            eng.close(disc.id, _outcome(decision=f"Decision {i}"))
            self.assertTrue(disc.is_closed())
            eng.reopen(disc.id)
            self.assertTrue(disc.is_open())


# ---------------------------------------------------------------------------
# TestEngineHistory
# ---------------------------------------------------------------------------

class TestEngineHistory(unittest.TestCase):

    def test_history_empty_initially(self) -> None:
        eng, disc = _start()
        self.assertEqual(eng.history(disc.id), [])

    def test_history_returns_messages_in_order(self) -> None:
        eng, disc, p = _start_with_participant()
        msgs = [_message(sender=p.participant_id, opinion=f"Op{i}") for i in range(3)]
        for msg in msgs:
            eng.post_message(disc.id, msg)
        h = eng.history(disc.id)
        for i, msg in enumerate(msgs):
            self.assertIs(h[i], msg)

    def test_history_returns_copy(self) -> None:
        eng, disc, p = _start_with_participant()
        eng.post_message(disc.id, _message(sender=p.participant_id))
        h = eng.history(disc.id)
        h.clear()
        self.assertEqual(disc.message_count(), 1)

    def test_history_works_on_closed(self) -> None:
        eng, disc, p = _start_with_participant()
        eng.post_message(disc.id, _message(sender=p.participant_id))
        _close_with_outcome(eng, disc.id)
        h = eng.history(disc.id)
        self.assertEqual(len(h), 1)

    def test_history_unknown_raises(self) -> None:
        eng = _engine()
        with self.assertRaises(DiscussionNotFoundError):
            eng.history("no-such-id")

    def test_history_after_reopen_includes_pre_reopen_messages(self) -> None:
        eng, disc, p = _start_with_participant()
        eng.post_message(disc.id, _message(sender=p.participant_id, opinion="Before close."))
        _close_with_outcome(eng, disc.id)
        eng.reopen(disc.id)
        eng.post_message(disc.id, _message(sender=p.participant_id, opinion="After reopen."))
        h = eng.history(disc.id)
        self.assertEqual(len(h), 2)
        opinions = [m.opinion for m in h]
        self.assertIn("Before close.", opinions)
        self.assertIn("After reopen.", opinions)


# ---------------------------------------------------------------------------
# TestEngineQueries
# ---------------------------------------------------------------------------

class TestEngineQueries(unittest.TestCase):

    def test_find_returns_discussion(self) -> None:
        eng, disc = _start()
        found = eng.find(disc.id)
        self.assertIs(found, disc)

    def test_find_unknown_raises(self) -> None:
        with self.assertRaises(DiscussionNotFoundError):
            _engine().find("no-such")

    def test_list_open_returns_only_open(self) -> None:
        eng = _engine()
        d1 = eng.start_discussion("T1")
        d2 = eng.start_discussion("T2")
        eng.close(d1.id, _outcome())
        open_list = eng.list_open()
        self.assertNotIn(d1, open_list)
        self.assertIn(d2, open_list)

    def test_list_closed_returns_only_closed(self) -> None:
        eng = _engine()
        d1 = eng.start_discussion("T1")
        d2 = eng.start_discussion("T2")
        eng.close(d1.id, _outcome())
        closed_list = eng.list_closed()
        self.assertIn(d1, closed_list)
        self.assertNotIn(d2, closed_list)

    def test_count_grows_with_starts(self) -> None:
        eng = _engine()
        for i in range(5):
            eng.start_discussion(f"topic {i}")
            self.assertEqual(eng.count(), i + 1)

    def test_statistics_required_keys(self) -> None:
        stats = _engine().statistics()
        for key in (
            "total", "open_count", "closed_count", "total_messages",
            "total_participants", "discussions_with_outcomes",
            "average_messages_per_discussion",
        ):
            self.assertIn(key, stats)

    def test_statistics_empty_engine(self) -> None:
        stats = _engine().statistics()
        self.assertEqual(stats["total"], 0)
        self.assertEqual(stats["open_count"], 0)
        self.assertAlmostEqual(stats["average_messages_per_discussion"], 0.0)

    def test_statistics_counts_correctly(self) -> None:
        eng = _engine()
        d1 = eng.start_discussion("T1")
        eng.start_discussion("T2")
        eng.join(d1.id, _participant("a"))
        eng.post_message(d1.id, _message(sender="a"))
        eng.close(d1.id, _outcome())
        stats = eng.statistics()
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["open_count"], 1)
        self.assertEqual(stats["closed_count"], 1)
        self.assertEqual(stats["total_messages"], 1)
        self.assertEqual(stats["discussions_with_outcomes"], 1)


# ---------------------------------------------------------------------------
# TestIntegration
# ---------------------------------------------------------------------------

class TestIntegration(unittest.TestCase):

    def test_full_rest_vs_graphql_discussion(self) -> None:
        eng = DiscussionEngine()
        disc = eng.start_discussion(
            topic="Should we use REST or GraphQL for the external API?",
            project_id="proj-saas",
            task_id="task-api-design",
        )

        alice = _participant("alice", "Alice — Backend Lead", "Backend Lead")
        bob   = _participant("bob",   "Bob — QA Engineer",   "QA Engineer")
        carol = _participant("carol", "Carol — Frontend Dev", "Frontend Agent")
        for p in (alice, bob, carol):
            eng.join(disc.id, p)

        eng.post_message(disc.id, DiscussionMessage(
            "alice", "Backend Lead",
            "REST is the right choice for the external API.",
            "REST has better tooling, more predictable caching behaviour, "
            "and is simpler to document with OpenAPI.",
            datetime.now(timezone.utc),
        ))
        eng.post_message(disc.id, DiscussionMessage(
            "bob", "QA Engineer",
            "I agree with REST for external, but we should consider GraphQL internally.",
            "Our integration tests pull many fields and GraphQL would reduce over-fetching "
            "significantly, improving test performance.",
            datetime.now(timezone.utc),
        ))
        eng.post_message(disc.id, DiscussionMessage(
            "carol", "Frontend Agent",
            "REST is fine for external. Internal GraphQL would help the dashboard.",
            "The dashboard makes many related queries; GraphQL would allow us to "
            "batch them into single requests.",
            datetime.now(timezone.utc),
        ))

        summary = eng.summarize(disc.id)
        self.assertIn("REST", summary)
        self.assertIn("Alice — Backend Lead", summary)

        outcome = DiscussionOutcome(
            decision="Use REST for the external API; GraphQL for internal tooling.",
            summary="Consensus reached: REST for external (maintainability, tooling); "
                    "GraphQL for internal (dashboard, test efficiency).",
            agreed_actions=[
                "Implement REST endpoints for the public API",
                "Pilot GraphQL for the internal dashboard in Sprint 14",
            ],
            unresolved_points=["Subscription support (websockets vs. SSE) not yet decided"],
        )
        eng.close(disc.id, outcome)

        self.assertTrue(disc.is_closed())
        self.assertEqual(disc.outcome.decision, outcome.decision)
        self.assertEqual(disc.message_count(), 3)
        self.assertFalse(disc.outcome.is_fully_resolved())
        self.assertEqual(disc.outcome.action_count(), 2)

    def test_rejected_then_reopened_then_resolved(self) -> None:
        eng = DiscussionEngine()
        disc = eng.start_discussion("Choose database engine.")
        eng.join(disc.id, _participant("a", "Alice", "Architect"))
        eng.join(disc.id, _participant("b", "Bob", "DBA"))

        eng.post_message(disc.id, _message("a", "Architect", "Use Postgres.", "Battle-tested, ACID."))
        eng.post_message(disc.id, _message("b", "DBA", "Use MySQL.", "Team familiarity."))

        eng.close(disc.id, DiscussionOutcome(
            decision="Postgres chosen.",
            summary="Architect's reasoning prevailed.",
        ))
        self.assertTrue(disc.is_closed())

        eng.reopen(disc.id, reason="CEO requested further review of licensing costs.")
        self.assertTrue(disc.is_open())
        self.assertIsNone(disc.outcome)

        eng.post_message(disc.id, _message("b", "DBA", "After cost review, also agree to Postgres.", "Open source, no licensing fees."))

        eng.close(disc.id, DiscussionOutcome(
            decision="Postgres — unanimous after cost review.",
            summary="All participants agreed after reviewing licensing implications.",
            agreed_actions=["Set up Postgres 16 in staging by end of sprint."],
        ))
        self.assertEqual(disc.outcome.action_count(), 1)
        self.assertEqual(disc.message_count(), 3)

    def test_engine_isolation(self) -> None:
        eng1 = DiscussionEngine()
        eng2 = DiscussionEngine()
        eng1.start_discussion("Topic A")
        eng1.start_discussion("Topic B")
        self.assertEqual(eng1.count(), 2)
        self.assertEqual(eng2.count(), 0)

    def test_participant_messages_tracked_by_sender(self) -> None:
        eng, disc = _start()
        eng.join(disc.id, _participant("a", "Alice", "Lead"))
        eng.join(disc.id, _participant("b", "Bob", "Junior"))
        for i in range(3):
            eng.post_message(disc.id, _message("a", opinion=f"Alice op {i}"))
        for i in range(2):
            eng.post_message(disc.id, _message("b", opinion=f"Bob op {i}"))
        self.assertEqual(len(disc.messages_by("a")), 3)
        self.assertEqual(len(disc.messages_by("b")), 2)
        omap = disc.opinion_map()
        self.assertEqual(len(omap["a"]), 3)

    def test_list_ordering_by_created_at(self) -> None:
        eng = DiscussionEngine()
        d1 = eng.start_discussion("First")
        d2 = eng.start_discussion("Second")
        d3 = eng.start_discussion("Third")
        open_list = eng.list_open()
        ids = [d.id for d in open_list]
        self.assertEqual(ids, [d1.id, d2.id, d3.id])

    def test_statistics_after_full_workflow(self) -> None:
        eng = DiscussionEngine()
        for i in range(4):
            d = eng.start_discussion(f"Topic {i}")
            if i % 2 == 0:
                eng.join(d.id, _participant(f"p{i}"))
                eng.post_message(d.id, _message(f"p{i}"))
                eng.close(d.id, _outcome())
        stats = eng.statistics()
        self.assertEqual(stats["total"], 4)
        self.assertEqual(stats["closed_count"], 2)
        self.assertEqual(stats["open_count"], 2)
        self.assertEqual(stats["discussions_with_outcomes"], 2)
        self.assertAlmostEqual(stats["average_messages_per_discussion"], 0.5)


# ---------------------------------------------------------------------------
# TestEdgeCases
# ---------------------------------------------------------------------------

class TestEdgeCases(unittest.TestCase):

    def test_start_discussion_with_all_optional_fields_none(self) -> None:
        eng = DiscussionEngine()
        disc = eng.start_discussion("Topic")
        self.assertIsNone(disc.project_id)
        self.assertIsNone(disc.task_id)
        self.assertIsNone(disc.closed_at)
        self.assertIsNone(disc.outcome)

    def test_message_sender_references_left_participant(self) -> None:
        """Messages from a participant who has since left are still in history."""
        eng, disc = _start()
        eng.join(disc.id, _participant("a"))
        eng.post_message(disc.id, _message(sender="a", opinion="Before leaving."))
        eng.leave(disc.id, "a")
        self.assertEqual(disc.message_count(), 1)
        self.assertEqual(disc.messages[0].sender, "a")

    def test_close_outcome_with_many_actions(self) -> None:
        eng, disc = _start()
        actions = [f"Action {i}" for i in range(10)]
        o = DiscussionOutcome(
            decision="Multi-action decision.",
            summary="Many things to do.",
            agreed_actions=actions,
        )
        eng.close(disc.id, o)
        self.assertEqual(disc.outcome.action_count(), 10)

    def test_close_outcome_with_many_unresolved(self) -> None:
        eng, disc = _start()
        unresolved = [f"Open point {i}" for i in range(7)]
        o = DiscussionOutcome(
            decision="Partial decision.",
            summary="Many open points.",
            unresolved_points=unresolved,
        )
        eng.close(disc.id, o)
        self.assertEqual(disc.outcome.unresolved_count(), 7)
        self.assertFalse(disc.outcome.is_fully_resolved())

    def test_two_discussions_dont_share_participants(self) -> None:
        eng = _engine()
        d1 = eng.start_discussion("T1")
        d2 = eng.start_discussion("T2")
        eng.join(d1.id, _participant("a"))
        self.assertTrue(d1.has_participant("a"))
        self.assertFalse(d2.has_participant("a"))

    def test_two_discussions_dont_share_messages(self) -> None:
        eng = _engine()
        d1 = eng.start_discussion("T1")
        d2 = eng.start_discussion("T2")
        eng.join(d1.id, _participant("a"))
        eng.post_message(d1.id, _message(sender="a", opinion="Only in D1."))
        self.assertEqual(d1.message_count(), 1)
        self.assertEqual(d2.message_count(), 0)

    def test_participant_equality_ignores_name_and_role(self) -> None:
        p1 = _participant(pid="same-id", name="Alice", role="Backend")
        p2 = _participant(pid="same-id", name="Different Name", role="QA")
        self.assertEqual(p1, p2)

    def test_outcome_agreed_actions_stored_correctly(self) -> None:
        actions = ["Action A", "Action B"]
        o = DiscussionOutcome(decision="D", summary="S", agreed_actions=actions)
        self.assertEqual(o.action_count(), 2)
        self.assertEqual(o.agreed_actions[0], "Action A")
        self.assertEqual(o.agreed_actions[1], "Action B")

    def test_message_timestamp_preserved_exactly(self) -> None:
        ts = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        msg = DiscussionMessage("a", "Role", "Op.", "Reasoning text.", ts)
        self.assertEqual(msg.timestamp, ts)

    def test_empty_engine_list_open_returns_empty(self) -> None:
        self.assertEqual(_engine().list_open(), [])

    def test_empty_engine_list_closed_returns_empty(self) -> None:
        self.assertEqual(_engine().list_closed(), [])

    def test_close_and_reopen_many_times_count_unchanged(self) -> None:
        eng, disc = _start()
        for _ in range(5):
            eng.close(disc.id, _outcome())
            eng.reopen(disc.id)
        self.assertEqual(eng.count(), 1)

    def test_join_participant_with_long_role(self) -> None:
        eng, disc = _start()
        long_role = "Principal Senior Distinguished Staff Software Reliability Engineer"
        p = _participant("x", "Very Long Role Agent", long_role)
        eng.join(disc.id, p)
        self.assertEqual(disc.get_participant("x").role, long_role)

    def test_summarize_after_leave_shows_fallback_sender(self) -> None:
        """summarize() uses sender ID as fallback when participant has left."""
        eng, disc = _start()
        eng.join(disc.id, _participant("temp-agent"))
        eng.post_message(disc.id, _message(sender="temp-agent", opinion="My view."))
        eng.leave(disc.id, "temp-agent")
        summary = eng.summarize(disc.id)
        self.assertIn("temp-agent", summary)

    def test_error_not_found_message_contains_id(self) -> None:
        eng = _engine()
        try:
            eng.find("missing-XYZ-123")
            self.fail("Expected DiscussionNotFoundError")
        except DiscussionNotFoundError as e:
            self.assertIn("missing-XYZ-123", str(e))

    def test_discussion_id_is_36_chars_uuid_format(self) -> None:
        eng = _engine()
        for i in range(5):
            disc = eng.start_discussion(f"T{i}")
            self.assertEqual(len(disc.id), 36)
            parts = disc.id.split("-")
            self.assertEqual(len(parts), 5)

    def test_post_message_from_creator(self) -> None:
        creator = _participant("creator", "Director", "Executive")
        eng, disc = _start(creator=creator)
        eng.post_message(disc.id, _message(sender="creator", opinion="Start with this."))
        self.assertEqual(disc.message_count(), 1)

    def test_discussion_created_at_is_utc(self) -> None:
        _, disc = _start()
        self.assertIsNotNone(disc.created_at.tzinfo)

    def test_participant_joined_at_auto_set_to_utc(self) -> None:
        eng, disc = _start()
        p = DiscussionParticipant("p99", "Test", "Agent", None)
        before = datetime.now(timezone.utc)
        eng.join(disc.id, p)
        after = datetime.now(timezone.utc)
        self.assertIsNotNone(p.joined_at)
        self.assertIsNotNone(p.joined_at.tzinfo)
        self.assertGreaterEqual(p.joined_at, before)
        self.assertLessEqual(p.joined_at, after)

    def test_statistics_total_participants_sums_active(self) -> None:
        eng = _engine()
        d1 = eng.start_discussion("T1")
        d2 = eng.start_discussion("T2")
        eng.join(d1.id, _participant("a"))
        eng.join(d1.id, _participant("b"))
        eng.join(d2.id, _participant("c"))
        stats = eng.statistics()
        self.assertEqual(stats["total_participants"], 3)

    def test_statistics_average_messages(self) -> None:
        eng = _engine()
        d1 = eng.start_discussion("T1")
        d2 = eng.start_discussion("T2")
        eng.join(d1.id, _participant("a"))
        eng.post_message(d1.id, _message("a", opinion="M1"))
        eng.post_message(d1.id, _message("a", opinion="M2"))
        # d2 has 0 messages
        stats = eng.statistics()
        self.assertAlmostEqual(stats["average_messages_per_discussion"], 1.0)


# ---------------------------------------------------------------------------
# TestDiscussionEngineContracts
# ---------------------------------------------------------------------------

class TestDiscussionEngineContracts(unittest.TestCase):
    """Tests verifying the engine's public contract boundaries."""

    def test_post_message_with_only_whitespace_opinion_and_valid_reasoning_raises(self) -> None:
        eng, disc, p = _start_with_participant()
        msg = DiscussionMessage(p.participant_id, "Role", "\t\n ", "Valid reasoning here.", datetime.now(timezone.utc))
        with self.assertRaises(InvalidMessageError):
            eng.post_message(disc.id, msg)

    def test_post_message_with_valid_opinion_and_only_whitespace_reasoning_raises(self) -> None:
        eng, disc, p = _start_with_participant()
        msg = DiscussionMessage(p.participant_id, "Role", "Valid opinion.", "\t\n ", datetime.now(timezone.utc))
        with self.assertRaises(InvalidMessageError):
            eng.post_message(disc.id, msg)

    def test_close_with_whitespace_summary_raises(self) -> None:
        eng, disc = _start()
        bad = DiscussionOutcome(decision="Valid decision.", summary="   ")
        with self.assertRaises(InvalidOutcomeError):
            eng.close(disc.id, bad)

    def test_find_after_close_still_works(self) -> None:
        eng, disc = _start()
        eng.close(disc.id, _outcome())
        found = eng.find(disc.id)
        self.assertIs(found, disc)

    def test_history_returns_new_list_not_internal(self) -> None:
        eng, disc, p = _start_with_participant()
        eng.post_message(disc.id, _message(sender=p.participant_id))
        h1 = eng.history(disc.id)
        h2 = eng.history(disc.id)
        self.assertIsNot(h1, h2)

    def test_list_open_returns_new_list(self) -> None:
        eng, disc = _start()
        l1 = eng.list_open()
        l2 = eng.list_open()
        self.assertIsNot(l1, l2)

    def test_list_closed_returns_new_list(self) -> None:
        eng, disc = _start()
        eng.close(disc.id, _outcome())
        l1 = eng.list_closed()
        l2 = eng.list_closed()
        self.assertIsNot(l1, l2)

    def test_start_discussion_different_engines_same_topic_distinct_ids(self) -> None:
        eng1, d1 = _start(topic="Same Topic")
        eng2, d2 = _start(topic="Same Topic")
        self.assertNotEqual(d1.id, d2.id)

    def test_all_exception_classes_are_exception_subclasses(self) -> None:
        for cls in (
            DiscussionError,
            DiscussionNotFoundError,
            DiscussionClosedError,
            DiscussionAlreadyOpenError,
            ParticipantAlreadyInDiscussionError,
            ParticipantNotInDiscussionError,
            InvalidMessageError,
            InvalidTopicError,
            InvalidOutcomeError,
        ):
            self.assertTrue(issubclass(cls, Exception), f"{cls.__name__} must be Exception subclass")

    def test_close_sets_outcome_decided_at_to_utc(self) -> None:
        eng, disc = _start()
        before = datetime.now(timezone.utc)
        eng.close(disc.id, _outcome())
        after = datetime.now(timezone.utc)
        self.assertIsNotNone(disc.outcome.decided_at)
        self.assertIsNotNone(disc.outcome.decided_at.tzinfo)
        self.assertGreaterEqual(disc.outcome.decided_at, before)
        self.assertLessEqual(disc.outcome.decided_at, after)

    def test_message_is_from_false_empty_string(self) -> None:
        msg = _message(sender="alice")
        self.assertFalse(msg.is_from(""))

    def test_reopen_reason_not_required(self) -> None:
        eng, disc = _start()
        eng.close(disc.id, _outcome())
        eng.reopen(disc.id)
        self.assertTrue(disc.is_open())

    def test_start_with_whitespace_only_topic_raises(self) -> None:
        eng = _engine()
        for ws in ("\t", "\n", "  \t  ", "\r\n"):
            with self.subTest(ws=repr(ws)):
                with self.assertRaises(InvalidTopicError):
                    eng.start_discussion(ws)


if __name__ == "__main__":
    unittest.main()
