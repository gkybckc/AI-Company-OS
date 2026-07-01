"""
Tests for the Sprint 14 Event Stream.

Covers:
- StreamChannel enum
- StreamEvent frozen dataclass
- StreamSubscription frozen dataclass
- EventStream exception hierarchy
- EventStream.publish()
- EventStream.subscribe()
- EventStream.unsubscribe()
- EventStream.history()
- EventStream.latest()
- EventStream.statistics()
- EventStream.find_subscription()
- EventStream callbacks
- EventStream.subscribers() / helper methods
- Multi-subscriber scenarios
- Integration flows

Run with:
    .venv\\Scripts\\python.exe -m unittest tests.test_event_stream -v
"""

import unittest
from datetime import datetime, timezone
from typing import List
from unittest.mock import MagicMock

from core.event_stream import (
    DuplicateSubscriberError,
    EventStream,
    EventStreamError,
    InvalidEventError,
    SubscriptionNotFoundError,
)
from core.stream_channel import StreamChannel
from core.stream_event import StreamEvent
from core.stream_subscription import StreamSubscription


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _event(source="Planner", channel=StreamChannel.PROJECT, **kwargs):
    payload = kwargs.get("payload", {})
    return StreamEvent.create(source=source, category=channel, payload=payload)


def _stream():
    return EventStream()


def _subscribed(channels=None, callback=None, subscriber="TestSub"):
    stream = _stream()
    sub = stream.subscribe(
        subscriber,
        channels if channels is not None else list(StreamChannel),
        callback=callback,
    )
    return stream, sub


# ---------------------------------------------------------------------------
# 1. StreamChannel enum
# ---------------------------------------------------------------------------

class TestStreamChannel(unittest.TestCase):

    def test_all_channels_exist(self):
        expected = {"SYSTEM", "PROJECT", "WORKFLOW", "DISCUSSION", "MEMORY", "DECISION", "RUNTIME", "CEO"}
        actual = {c.value for c in StreamChannel}
        self.assertEqual(actual, expected)

    def test_str_returns_value(self):
        for ch in StreamChannel:
            self.assertEqual(str(ch), ch.value)

    def test_system_str(self):
        self.assertEqual(str(StreamChannel.SYSTEM), "SYSTEM")

    def test_project_str(self):
        self.assertEqual(str(StreamChannel.PROJECT), "PROJECT")

    def test_workflow_str(self):
        self.assertEqual(str(StreamChannel.WORKFLOW), "WORKFLOW")

    def test_discussion_str(self):
        self.assertEqual(str(StreamChannel.DISCUSSION), "DISCUSSION")

    def test_memory_str(self):
        self.assertEqual(str(StreamChannel.MEMORY), "MEMORY")

    def test_decision_str(self):
        self.assertEqual(str(StreamChannel.DECISION), "DECISION")

    def test_runtime_str(self):
        self.assertEqual(str(StreamChannel.RUNTIME), "RUNTIME")

    def test_ceo_str(self):
        self.assertEqual(str(StreamChannel.CEO), "CEO")

    def test_is_system_channel_true(self):
        self.assertTrue(StreamChannel.SYSTEM.is_system_channel())

    def test_is_system_channel_false(self):
        for ch in StreamChannel:
            if ch != StreamChannel.SYSTEM:
                self.assertFalse(ch.is_system_channel(), f"{ch} should not be system")

    def test_is_ceo_channel_true(self):
        self.assertTrue(StreamChannel.CEO.is_ceo_channel())

    def test_is_ceo_channel_false(self):
        for ch in StreamChannel:
            if ch != StreamChannel.CEO:
                self.assertFalse(ch.is_ceo_channel(), f"{ch} should not be CEO")

    def test_is_operational_channel_true(self):
        operational = [StreamChannel.PROJECT, StreamChannel.WORKFLOW,
                       StreamChannel.DISCUSSION, StreamChannel.MEMORY,
                       StreamChannel.DECISION, StreamChannel.RUNTIME]
        for ch in operational:
            self.assertTrue(ch.is_operational_channel(), f"{ch} should be operational")

    def test_is_operational_channel_false_system(self):
        self.assertFalse(StreamChannel.SYSTEM.is_operational_channel())

    def test_is_operational_channel_false_ceo(self):
        self.assertFalse(StreamChannel.CEO.is_operational_channel())

    def test_is_governance_channel_ceo(self):
        self.assertTrue(StreamChannel.CEO.is_governance_channel())

    def test_is_governance_channel_system(self):
        self.assertTrue(StreamChannel.SYSTEM.is_governance_channel())

    def test_is_governance_channel_false_project(self):
        self.assertFalse(StreamChannel.PROJECT.is_governance_channel())

    def test_display_name_returns_string(self):
        for ch in StreamChannel:
            self.assertIsInstance(ch.display_name(), str)

    def test_display_name_not_empty(self):
        for ch in StreamChannel:
            self.assertTrue(ch.display_name())

    def test_is_str_subclass(self):
        self.assertIsInstance(StreamChannel.PROJECT, str)

    def test_eight_total_channels(self):
        self.assertEqual(len(StreamChannel), 8)


# ---------------------------------------------------------------------------
# 2. StreamEvent construction
# ---------------------------------------------------------------------------

class TestStreamEventConstruct(unittest.TestCase):

    def test_create_returns_event(self):
        e = StreamEvent.create("Planner", StreamChannel.PROJECT)
        self.assertIsInstance(e, StreamEvent)

    def test_create_id_generated(self):
        e = StreamEvent.create("Planner", StreamChannel.PROJECT)
        self.assertTrue(e.id)

    def test_create_id_is_string(self):
        e = StreamEvent.create("Planner", StreamChannel.PROJECT)
        self.assertIsInstance(e.id, str)

    def test_create_unique_ids(self):
        e1 = StreamEvent.create("A", StreamChannel.PROJECT)
        e2 = StreamEvent.create("A", StreamChannel.PROJECT)
        self.assertNotEqual(e1.id, e2.id)

    def test_create_source_set(self):
        e = StreamEvent.create("Executive", StreamChannel.PROJECT)
        self.assertEqual(e.source, "Executive")

    def test_create_category_set(self):
        e = StreamEvent.create("Planner", StreamChannel.WORKFLOW)
        self.assertEqual(e.category, StreamChannel.WORKFLOW)

    def test_create_timestamp_utc(self):
        e = StreamEvent.create("Planner", StreamChannel.PROJECT)
        self.assertIsNotNone(e.timestamp.tzinfo)

    def test_create_payload_default_empty(self):
        e = StreamEvent.create("Planner", StreamChannel.PROJECT)
        self.assertEqual(e.payload, {})

    def test_create_payload_set(self):
        e = StreamEvent.create("Planner", StreamChannel.PROJECT, payload={"key": "val"})
        self.assertEqual(e.payload["key"], "val")

    def test_direct_construction(self):
        now = datetime.now(timezone.utc)
        e = StreamEvent(
            id="abc",
            source="Test",
            category=StreamChannel.SYSTEM,
            timestamp=now,
        )
        self.assertEqual(e.id, "abc")
        self.assertEqual(e.source, "Test")

    def test_is_frozen(self):
        e = StreamEvent.create("Planner", StreamChannel.PROJECT)
        with self.assertRaises(Exception):
            e.source = "Other"

    def test_is_frozen_category(self):
        e = StreamEvent.create("Planner", StreamChannel.PROJECT)
        with self.assertRaises(Exception):
            e.category = StreamChannel.CEO

    def test_all_channels_usable(self):
        for ch in StreamChannel:
            e = StreamEvent.create("test", ch)
            self.assertEqual(e.category, ch)


# ---------------------------------------------------------------------------
# 3. StreamEvent helpers
# ---------------------------------------------------------------------------

class TestStreamEventHelpers(unittest.TestCase):

    def _e(self, source="Planner", channel=StreamChannel.PROJECT, **kw):
        return StreamEvent.create(source=source, category=channel, payload=kw.get("payload", {}))

    def test_is_from_true(self):
        self.assertTrue(self._e(source="Planner").is_from("Planner"))

    def test_is_from_false(self):
        self.assertFalse(self._e(source="Planner").is_from("Executive"))

    def test_is_in_channel_true(self):
        self.assertTrue(self._e(channel=StreamChannel.PROJECT).is_in_channel(StreamChannel.PROJECT))

    def test_is_in_channel_false(self):
        self.assertFalse(self._e(channel=StreamChannel.PROJECT).is_in_channel(StreamChannel.CEO))

    def test_get_payload_value_present(self):
        e = self._e(payload={"answer": 42})
        self.assertEqual(e.get_payload_value("answer"), 42)

    def test_get_payload_value_absent_default_none(self):
        e = self._e()
        self.assertIsNone(e.get_payload_value("missing"))

    def test_get_payload_value_absent_custom_default(self):
        e = self._e()
        self.assertEqual(e.get_payload_value("missing", "fallback"), "fallback")

    def test_has_payload_true(self):
        e = self._e(payload={"x": 1})
        self.assertTrue(e.has_payload())

    def test_has_payload_false(self):
        e = self._e()
        self.assertFalse(e.has_payload())

    def test_summary_is_dict(self):
        self.assertIsInstance(self._e().summary(), dict)

    def test_summary_has_id(self):
        e = self._e()
        self.assertIn("id", e.summary())

    def test_summary_has_source(self):
        e = self._e()
        self.assertIn("source", e.summary())

    def test_summary_has_category(self):
        e = self._e()
        self.assertIn("category", e.summary())

    def test_summary_has_timestamp(self):
        e = self._e()
        self.assertIn("timestamp", e.summary())

    def test_summary_has_payload_keys(self):
        e = self._e(payload={"k": 1})
        s = e.summary()
        self.assertIn("payload_keys", s)
        self.assertIn("k", s["payload_keys"])

    def test_summary_category_is_string(self):
        e = self._e()
        self.assertIsInstance(e.summary()["category"], str)


# ---------------------------------------------------------------------------
# 4. StreamSubscription construction
# ---------------------------------------------------------------------------

class TestStreamSubscriptionConstruct(unittest.TestCase):

    def test_create_basic(self):
        sub = StreamSubscription(subscriber="A", channels=[StreamChannel.PROJECT])
        self.assertEqual(sub.subscriber, "A")

    def test_channels_set(self):
        chs = [StreamChannel.PROJECT, StreamChannel.WORKFLOW]
        sub = StreamSubscription(subscriber="A", channels=chs)
        self.assertEqual(len(sub.channels), 2)

    def test_empty_channels_allowed(self):
        sub = StreamSubscription(subscriber="A", channels=[])
        self.assertEqual(sub.channel_count(), 0)

    def test_created_at_utc(self):
        sub = StreamSubscription(subscriber="A", channels=[])
        self.assertIsNotNone(sub.created_at.tzinfo)

    def test_created_at_defaults_to_now(self):
        before = datetime.now(timezone.utc)
        sub = StreamSubscription(subscriber="A", channels=[])
        after = datetime.now(timezone.utc)
        self.assertGreaterEqual(sub.created_at, before)
        self.assertLessEqual(sub.created_at, after)

    def test_is_frozen(self):
        sub = StreamSubscription(subscriber="A", channels=[])
        with self.assertRaises(Exception):
            sub.subscriber = "B"

    def test_all_channels_subscription(self):
        sub = StreamSubscription(subscriber="Dashboard", channels=list(StreamChannel))
        self.assertEqual(sub.channel_count(), len(StreamChannel))


# ---------------------------------------------------------------------------
# 5. StreamSubscription helpers
# ---------------------------------------------------------------------------

class TestStreamSubscriptionHelpers(unittest.TestCase):

    def _sub(self, channels=None):
        return StreamSubscription(
            subscriber="TestSub",
            channels=channels if channels is not None else [StreamChannel.PROJECT],
        )

    def test_is_subscribed_to_true(self):
        sub = self._sub([StreamChannel.PROJECT])
        self.assertTrue(sub.is_subscribed_to(StreamChannel.PROJECT))

    def test_is_subscribed_to_false(self):
        sub = self._sub([StreamChannel.PROJECT])
        self.assertFalse(sub.is_subscribed_to(StreamChannel.CEO))

    def test_channel_count_one(self):
        self.assertEqual(self._sub([StreamChannel.PROJECT]).channel_count(), 1)

    def test_channel_count_zero(self):
        self.assertEqual(self._sub([]).channel_count(), 0)

    def test_channel_count_all(self):
        sub = StreamSubscription(subscriber="A", channels=list(StreamChannel))
        self.assertEqual(sub.channel_count(), len(StreamChannel))

    def test_is_subscribed_to_all_true(self):
        sub = StreamSubscription(subscriber="A", channels=list(StreamChannel))
        self.assertTrue(sub.is_subscribed_to_all())

    def test_is_subscribed_to_all_false(self):
        sub = self._sub([StreamChannel.PROJECT])
        self.assertFalse(sub.is_subscribed_to_all())

    def test_is_subscribed_to_all_empty_false(self):
        sub = self._sub([])
        self.assertFalse(sub.is_subscribed_to_all())

    def test_has_channels_true(self):
        self.assertTrue(self._sub([StreamChannel.PROJECT]).has_channels())

    def test_has_channels_false(self):
        self.assertFalse(self._sub([]).has_channels())

    def test_channel_names_returns_strings(self):
        sub = self._sub([StreamChannel.PROJECT, StreamChannel.WORKFLOW])
        names = sub.channel_names()
        self.assertIsInstance(names, list)
        self.assertIn("PROJECT", names)
        self.assertIn("WORKFLOW", names)

    def test_channel_names_empty(self):
        self.assertEqual(self._sub([]).channel_names(), [])

    def test_covers_any_true(self):
        sub = self._sub([StreamChannel.PROJECT])
        self.assertTrue(sub.covers_any([StreamChannel.PROJECT, StreamChannel.CEO]))

    def test_covers_any_false(self):
        sub = self._sub([StreamChannel.PROJECT])
        self.assertFalse(sub.covers_any([StreamChannel.CEO, StreamChannel.SYSTEM]))

    def test_covers_any_empty_list_false(self):
        sub = self._sub([StreamChannel.PROJECT])
        self.assertFalse(sub.covers_any([]))

    def test_summary_is_dict(self):
        self.assertIsInstance(self._sub().summary(), dict)

    def test_summary_has_subscriber(self):
        sub = self._sub()
        self.assertIn("subscriber", sub.summary())

    def test_summary_has_channels(self):
        sub = self._sub()
        self.assertIn("channels", sub.summary())

    def test_summary_has_channel_count(self):
        sub = self._sub()
        self.assertIn("channel_count", sub.summary())

    def test_summary_has_created_at(self):
        sub = self._sub()
        self.assertIn("created_at", sub.summary())

    def test_summary_has_is_subscribed_to_all(self):
        sub = self._sub()
        self.assertIn("is_subscribed_to_all", sub.summary())


# ---------------------------------------------------------------------------
# 6. Exception hierarchy
# ---------------------------------------------------------------------------

class TestExceptionHierarchy(unittest.TestCase):

    def test_event_stream_error_is_exception(self):
        self.assertTrue(issubclass(EventStreamError, Exception))

    def test_subscription_not_found_is_event_stream_error(self):
        self.assertTrue(issubclass(SubscriptionNotFoundError, EventStreamError))

    def test_duplicate_subscriber_is_event_stream_error(self):
        self.assertTrue(issubclass(DuplicateSubscriberError, EventStreamError))

    def test_invalid_event_is_event_stream_error(self):
        self.assertTrue(issubclass(InvalidEventError, EventStreamError))

    def test_raise_subscription_not_found(self):
        with self.assertRaises(SubscriptionNotFoundError):
            raise SubscriptionNotFoundError("not found")

    def test_raise_duplicate_subscriber(self):
        with self.assertRaises(DuplicateSubscriberError):
            raise DuplicateSubscriberError("dup")

    def test_raise_invalid_event(self):
        with self.assertRaises(InvalidEventError):
            raise InvalidEventError("invalid")

    def test_not_found_caught_as_base(self):
        with self.assertRaises(EventStreamError):
            raise SubscriptionNotFoundError("x")

    def test_duplicate_caught_as_base(self):
        with self.assertRaises(EventStreamError):
            raise DuplicateSubscriberError("x")

    def test_invalid_caught_as_base(self):
        with self.assertRaises(EventStreamError):
            raise InvalidEventError("x")

    def test_message_preserved_not_found(self):
        try:
            raise SubscriptionNotFoundError("my message")
        except SubscriptionNotFoundError as e:
            self.assertIn("my message", str(e))


# ---------------------------------------------------------------------------
# 7. EventStream construction
# ---------------------------------------------------------------------------

class TestEventStreamConstruction(unittest.TestCase):

    def test_creates_without_error(self):
        stream = EventStream()
        self.assertIsNotNone(stream)

    def test_empty_history_on_construction(self):
        self.assertEqual(EventStream().history(), [])

    def test_zero_events_on_construction(self):
        self.assertEqual(EventStream().event_count(), 0)

    def test_zero_subscribers_on_construction(self):
        self.assertEqual(EventStream().subscriber_count(), 0)

    def test_empty_subscribers_list(self):
        self.assertEqual(EventStream().subscribers(), [])

    def test_statistics_total_events_zero(self):
        self.assertEqual(EventStream().statistics()["total_events"], 0)

    def test_statistics_total_subscribers_zero(self):
        self.assertEqual(EventStream().statistics()["total_subscribers"], 0)

    def test_latest_returns_none_on_empty(self):
        self.assertIsNone(EventStream().latest())

    def test_latest_channel_returns_none_on_empty(self):
        self.assertIsNone(EventStream().latest(StreamChannel.PROJECT))


# ---------------------------------------------------------------------------
# 8. EventStream.publish()
# ---------------------------------------------------------------------------

class TestPublish(unittest.TestCase):

    def test_publish_stores_event(self):
        stream = _stream()
        e = _event()
        stream.publish(e)
        self.assertIn(e, stream.history())

    def test_publish_increments_count(self):
        stream = _stream()
        stream.publish(_event())
        self.assertEqual(stream.event_count(), 1)

    def test_publish_two_events(self):
        stream = _stream()
        stream.publish(_event())
        stream.publish(_event())
        self.assertEqual(stream.event_count(), 2)

    def test_publish_none_raises(self):
        with self.assertRaises(InvalidEventError):
            _stream().publish(None)

    def test_publish_wrong_type_raises(self):
        with self.assertRaises(InvalidEventError):
            _stream().publish("not an event")

    def test_publish_wrong_type_int_raises(self):
        with self.assertRaises(InvalidEventError):
            _stream().publish(42)

    def test_publish_returns_none(self):
        stream = _stream()
        result = stream.publish(_event())
        self.assertIsNone(result)

    def test_publish_preserves_source(self):
        stream = _stream()
        e = _event(source="WorkflowEngine")
        stream.publish(e)
        self.assertEqual(stream.history()[0].source, "WorkflowEngine")

    def test_publish_preserves_channel(self):
        stream = _stream()
        e = _event(channel=StreamChannel.DECISION)
        stream.publish(e)
        self.assertEqual(stream.history()[0].category, StreamChannel.DECISION)

    def test_publish_order_preserved(self):
        stream = _stream()
        e1 = _event(source="First")
        e2 = _event(source="Second")
        stream.publish(e1)
        stream.publish(e2)
        h = stream.history()
        self.assertEqual(h[0].source, "First")
        self.assertEqual(h[1].source, "Second")

    def test_publish_multiple_channels(self):
        stream = _stream()
        for ch in StreamChannel:
            stream.publish(_event(channel=ch))
        self.assertEqual(stream.event_count(), len(StreamChannel))

    def test_publish_event_with_payload(self):
        stream = _stream()
        e = StreamEvent.create("Test", StreamChannel.PROJECT, payload={"task": "write tests"})
        stream.publish(e)
        self.assertEqual(stream.history()[0].get_payload_value("task"), "write tests")


# ---------------------------------------------------------------------------
# 9. EventStream.subscribe()
# ---------------------------------------------------------------------------

class TestSubscribe(unittest.TestCase):

    def test_subscribe_returns_subscription(self):
        stream = _stream()
        sub = stream.subscribe("A", [StreamChannel.PROJECT])
        self.assertIsInstance(sub, StreamSubscription)

    def test_subscribe_sets_subscriber_name(self):
        stream = _stream()
        sub = stream.subscribe("Dashboard", [StreamChannel.PROJECT])
        self.assertEqual(sub.subscriber, "Dashboard")

    def test_subscribe_stores_channels(self):
        stream = _stream()
        sub = stream.subscribe("A", [StreamChannel.PROJECT, StreamChannel.WORKFLOW])
        self.assertEqual(sub.channel_count(), 2)

    def test_subscribe_empty_channels_allowed(self):
        stream = _stream()
        sub = stream.subscribe("A", [])
        self.assertEqual(sub.channel_count(), 0)

    def test_subscribe_all_channels(self):
        stream = _stream()
        sub = stream.subscribe("A", list(StreamChannel))
        self.assertTrue(sub.is_subscribed_to_all())

    def test_subscribe_empty_name_raises(self):
        with self.assertRaises(InvalidEventError):
            _stream().subscribe("", [StreamChannel.PROJECT])

    def test_subscribe_whitespace_name_raises(self):
        with self.assertRaises(InvalidEventError):
            _stream().subscribe("   ", [StreamChannel.PROJECT])

    def test_subscribe_none_channels_raises(self):
        with self.assertRaises(InvalidEventError):
            _stream().subscribe("A", None)

    def test_subscribe_duplicate_raises(self):
        stream = _stream()
        stream.subscribe("A", [StreamChannel.PROJECT])
        with self.assertRaises(DuplicateSubscriberError):
            stream.subscribe("A", [StreamChannel.CEO])

    def test_subscribe_different_subscribers_allowed(self):
        stream = _stream()
        stream.subscribe("A", [StreamChannel.PROJECT])
        stream.subscribe("B", [StreamChannel.PROJECT])
        self.assertEqual(stream.subscriber_count(), 2)

    def test_subscribe_increments_count(self):
        stream = _stream()
        stream.subscribe("A", [StreamChannel.PROJECT])
        self.assertEqual(stream.subscriber_count(), 1)

    def test_subscribe_strips_name(self):
        stream = _stream()
        sub = stream.subscribe("  Trimmed  ", [StreamChannel.PROJECT])
        self.assertEqual(sub.subscriber, "Trimmed")

    def test_subscribe_with_callback(self):
        stream = _stream()
        cb = MagicMock()
        stream.subscribe("A", [StreamChannel.PROJECT], callback=cb)
        stream.publish(_event(channel=StreamChannel.PROJECT))
        cb.assert_called_once()

    def test_subscribe_without_callback_no_error(self):
        stream = _stream()
        stream.subscribe("A", [StreamChannel.PROJECT])
        stream.publish(_event(channel=StreamChannel.PROJECT))

    def test_subscribe_name_in_subscribers_list(self):
        stream = _stream()
        stream.subscribe("MyService", [StreamChannel.SYSTEM])
        self.assertIn("MyService", stream.subscribers())


# ---------------------------------------------------------------------------
# 10. EventStream.unsubscribe()
# ---------------------------------------------------------------------------

class TestUnsubscribe(unittest.TestCase):

    def test_unsubscribe_removes_subscriber(self):
        stream, _ = _subscribed(subscriber="A")
        stream.unsubscribe("A")
        self.assertFalse(stream.is_subscriber("A"))

    def test_unsubscribe_decrements_count(self):
        stream, _ = _subscribed(subscriber="A")
        stream.unsubscribe("A")
        self.assertEqual(stream.subscriber_count(), 0)

    def test_unsubscribe_not_found_raises(self):
        stream = _stream()
        with self.assertRaises(SubscriptionNotFoundError):
            stream.unsubscribe("nobody")

    def test_unsubscribe_returns_none(self):
        stream, _ = _subscribed(subscriber="A")
        result = stream.unsubscribe("A")
        self.assertIsNone(result)

    def test_unsubscribe_stops_callback(self):
        received = []
        stream = _stream()
        stream.subscribe("A", [StreamChannel.PROJECT], callback=received.append)
        stream.publish(_event(channel=StreamChannel.PROJECT))
        stream.unsubscribe("A")
        stream.publish(_event(channel=StreamChannel.PROJECT))
        self.assertEqual(len(received), 1)

    def test_unsubscribe_does_not_clear_history(self):
        stream = _stream()
        stream.subscribe("A", [StreamChannel.PROJECT])
        stream.publish(_event(channel=StreamChannel.PROJECT))
        stream.unsubscribe("A")
        self.assertEqual(stream.event_count(), 1)

    def test_resubscribe_after_unsubscribe(self):
        stream = _stream()
        stream.subscribe("A", [StreamChannel.PROJECT])
        stream.unsubscribe("A")
        sub = stream.subscribe("A", [StreamChannel.CEO])
        self.assertTrue(sub.is_subscribed_to(StreamChannel.CEO))

    def test_unsubscribe_one_of_many(self):
        stream = _stream()
        stream.subscribe("A", [StreamChannel.PROJECT])
        stream.subscribe("B", [StreamChannel.PROJECT])
        stream.unsubscribe("A")
        self.assertEqual(stream.subscriber_count(), 1)
        self.assertTrue(stream.is_subscriber("B"))

    def test_double_unsubscribe_raises(self):
        stream, _ = _subscribed(subscriber="A")
        stream.unsubscribe("A")
        with self.assertRaises(SubscriptionNotFoundError):
            stream.unsubscribe("A")


# ---------------------------------------------------------------------------
# 11. EventStream.history()
# ---------------------------------------------------------------------------

class TestHistory(unittest.TestCase):

    def test_history_empty(self):
        self.assertEqual(_stream().history(), [])

    def test_history_all_events(self):
        stream = _stream()
        stream.publish(_event(channel=StreamChannel.PROJECT))
        stream.publish(_event(channel=StreamChannel.CEO))
        h = stream.history()
        self.assertEqual(len(h), 2)

    def test_history_filter_channel(self):
        stream = _stream()
        stream.publish(_event(channel=StreamChannel.PROJECT))
        stream.publish(_event(channel=StreamChannel.CEO))
        h = stream.history(channel=StreamChannel.PROJECT)
        self.assertEqual(len(h), 1)
        self.assertEqual(h[0].category, StreamChannel.PROJECT)

    def test_history_filter_channel_no_match(self):
        stream = _stream()
        stream.publish(_event(channel=StreamChannel.PROJECT))
        h = stream.history(channel=StreamChannel.CEO)
        self.assertEqual(h, [])

    def test_history_filter_source(self):
        stream = _stream()
        stream.publish(_event(source="Planner"))
        stream.publish(_event(source="Executive"))
        h = stream.history(source="Planner")
        self.assertEqual(len(h), 1)
        self.assertEqual(h[0].source, "Planner")

    def test_history_filter_source_no_match(self):
        stream = _stream()
        stream.publish(_event(source="Planner"))
        h = stream.history(source="Nobody")
        self.assertEqual(h, [])

    def test_history_filter_channel_and_source(self):
        stream = _stream()
        stream.publish(_event(source="Planner", channel=StreamChannel.PROJECT))
        stream.publish(_event(source="Planner", channel=StreamChannel.DECISION))
        stream.publish(_event(source="Executive", channel=StreamChannel.PROJECT))
        h = stream.history(channel=StreamChannel.PROJECT, source="Planner")
        self.assertEqual(len(h), 1)
        self.assertEqual(h[0].source, "Planner")
        self.assertEqual(h[0].category, StreamChannel.PROJECT)

    def test_history_limit(self):
        stream = _stream()
        for i in range(5):
            stream.publish(_event())
        h = stream.history(limit=3)
        self.assertEqual(len(h), 3)

    def test_history_limit_returns_most_recent(self):
        stream = _stream()
        events = [_event(source=f"S{i}") for i in range(5)]
        for e in events:
            stream.publish(e)
        h = stream.history(limit=2)
        self.assertEqual(h[0].source, "S3")
        self.assertEqual(h[1].source, "S4")

    def test_history_limit_greater_than_total(self):
        stream = _stream()
        stream.publish(_event())
        h = stream.history(limit=100)
        self.assertEqual(len(h), 1)

    def test_history_limit_zero_ignored(self):
        stream = _stream()
        for _ in range(3):
            stream.publish(_event())
        h = stream.history(limit=0)
        self.assertEqual(len(h), 3)

    def test_history_limit_negative_ignored(self):
        stream = _stream()
        for _ in range(3):
            stream.publish(_event())
        h = stream.history(limit=-1)
        self.assertEqual(len(h), 3)

    def test_history_returns_new_list(self):
        stream = _stream()
        stream.publish(_event())
        h1 = stream.history()
        h2 = stream.history()
        self.assertIsNot(h1, h2)

    def test_history_mutation_does_not_affect_stream(self):
        stream = _stream()
        stream.publish(_event())
        h = stream.history()
        h.clear()
        self.assertEqual(stream.event_count(), 1)

    def test_history_oldest_first(self):
        stream = _stream()
        e1 = _event(source="First")
        e2 = _event(source="Second")
        stream.publish(e1)
        stream.publish(e2)
        h = stream.history()
        self.assertEqual(h[0].source, "First")
        self.assertEqual(h[1].source, "Second")

    def test_history_channel_and_limit(self):
        stream = _stream()
        for _ in range(4):
            stream.publish(_event(channel=StreamChannel.PROJECT))
        stream.publish(_event(channel=StreamChannel.CEO))
        h = stream.history(channel=StreamChannel.PROJECT, limit=2)
        self.assertEqual(len(h), 2)
        for e in h:
            self.assertEqual(e.category, StreamChannel.PROJECT)


# ---------------------------------------------------------------------------
# 12. EventStream.latest()
# ---------------------------------------------------------------------------

class TestLatest(unittest.TestCase):

    def test_latest_empty_none(self):
        self.assertIsNone(_stream().latest())

    def test_latest_single_event(self):
        stream = _stream()
        e = _event()
        stream.publish(e)
        self.assertIs(stream.latest(), e)

    def test_latest_returns_most_recent(self):
        stream = _stream()
        e1 = _event(source="First")
        e2 = _event(source="Second")
        stream.publish(e1)
        stream.publish(e2)
        self.assertIs(stream.latest(), e2)

    def test_latest_channel_filter(self):
        stream = _stream()
        ep = _event(channel=StreamChannel.PROJECT)
        ec = _event(channel=StreamChannel.CEO)
        stream.publish(ep)
        stream.publish(ec)
        self.assertIs(stream.latest(StreamChannel.PROJECT), ep)
        self.assertIs(stream.latest(StreamChannel.CEO), ec)

    def test_latest_channel_no_match_none(self):
        stream = _stream()
        stream.publish(_event(channel=StreamChannel.PROJECT))
        self.assertIsNone(stream.latest(StreamChannel.CEO))

    def test_latest_channel_multiple_same_channel(self):
        stream = _stream()
        e1 = _event(source="First", channel=StreamChannel.PROJECT)
        e2 = _event(source="Second", channel=StreamChannel.PROJECT)
        stream.publish(e1)
        stream.publish(e2)
        self.assertIs(stream.latest(StreamChannel.PROJECT), e2)

    def test_latest_no_filter_all_channels(self):
        stream = _stream()
        for ch in StreamChannel:
            stream.publish(_event(channel=ch))
        last_ch = list(StreamChannel)[-1]
        latest = stream.latest()
        self.assertEqual(latest.category, last_ch)

    def test_latest_after_multiple_publishes(self):
        stream = _stream()
        e = None
        for i in range(10):
            e = _event(source=f"S{i}")
            stream.publish(e)
        self.assertIs(stream.latest(), e)


# ---------------------------------------------------------------------------
# 13. EventStream.statistics()
# ---------------------------------------------------------------------------

class TestStatistics(unittest.TestCase):

    def test_stats_has_total_events(self):
        self.assertIn("total_events", _stream().statistics())

    def test_stats_has_total_subscribers(self):
        self.assertIn("total_subscribers", _stream().statistics())

    def test_stats_has_events_by_channel(self):
        self.assertIn("events_by_channel", _stream().statistics())

    def test_stats_has_events_by_source(self):
        self.assertIn("events_by_source", _stream().statistics())

    def test_stats_has_subscribers_by_channel(self):
        self.assertIn("subscribers_by_channel", _stream().statistics())

    def test_stats_has_active_subscribers(self):
        self.assertIn("active_subscribers", _stream().statistics())

    def test_stats_empty_total_events_zero(self):
        self.assertEqual(_stream().statistics()["total_events"], 0)

    def test_stats_empty_total_subscribers_zero(self):
        self.assertEqual(_stream().statistics()["total_subscribers"], 0)

    def test_stats_total_events_after_publish(self):
        stream = _stream()
        stream.publish(_event())
        stream.publish(_event())
        self.assertEqual(stream.statistics()["total_events"], 2)

    def test_stats_total_subscribers_after_subscribe(self):
        stream, _ = _subscribed()
        self.assertEqual(stream.statistics()["total_subscribers"], 1)

    def test_stats_events_by_channel_counts(self):
        stream = _stream()
        stream.publish(_event(channel=StreamChannel.PROJECT))
        stream.publish(_event(channel=StreamChannel.PROJECT))
        stats = stream.statistics()
        self.assertEqual(stats["events_by_channel"]["PROJECT"], 2)

    def test_stats_events_by_channel_all_keys(self):
        stats = _stream().statistics()
        for ch in StreamChannel:
            self.assertIn(ch.value, stats["events_by_channel"])

    def test_stats_events_by_source(self):
        stream = _stream()
        stream.publish(_event(source="Planner"))
        stream.publish(_event(source="Planner"))
        stream.publish(_event(source="Executive"))
        stats = stream.statistics()
        self.assertEqual(stats["events_by_source"]["Planner"], 2)
        self.assertEqual(stats["events_by_source"]["Executive"], 1)

    def test_stats_subscribers_by_channel(self):
        stream = _stream()
        stream.subscribe("A", [StreamChannel.PROJECT])
        stream.subscribe("B", [StreamChannel.PROJECT])
        stats = stream.statistics()
        self.assertEqual(stats["subscribers_by_channel"]["PROJECT"], 2)

    def test_stats_active_subscribers_list(self):
        stream = _stream()
        stream.subscribe("Alpha", [StreamChannel.PROJECT])
        stream.subscribe("Beta", [StreamChannel.CEO])
        stats = stream.statistics()
        self.assertIn("Alpha", stats["active_subscribers"])
        self.assertIn("Beta", stats["active_subscribers"])

    def test_stats_active_subscribers_sorted(self):
        stream = _stream()
        stream.subscribe("Z", [StreamChannel.PROJECT])
        stream.subscribe("A", [StreamChannel.PROJECT])
        stats = stream.statistics()
        names = stats["active_subscribers"]
        self.assertEqual(names, sorted(names))

    def test_stats_after_unsubscribe(self):
        stream, _ = _subscribed(subscriber="A")
        stream.unsubscribe("A")
        self.assertEqual(stream.statistics()["total_subscribers"], 0)

    def test_stats_returns_dict(self):
        self.assertIsInstance(_stream().statistics(), dict)


# ---------------------------------------------------------------------------
# 14. EventStream.find_subscription() and is_subscriber()
# ---------------------------------------------------------------------------

class TestFindSubscription(unittest.TestCase):

    def test_find_returns_subscription(self):
        stream, sub = _subscribed(subscriber="A")
        found = stream.find_subscription("A")
        self.assertIs(found, sub)

    def test_find_not_registered_raises(self):
        with self.assertRaises(SubscriptionNotFoundError):
            _stream().find_subscription("nobody")

    def test_find_after_unsubscribe_raises(self):
        stream, _ = _subscribed(subscriber="A")
        stream.unsubscribe("A")
        with self.assertRaises(SubscriptionNotFoundError):
            stream.find_subscription("A")

    def test_is_subscriber_true(self):
        stream, _ = _subscribed(subscriber="A")
        self.assertTrue(stream.is_subscriber("A"))

    def test_is_subscriber_false(self):
        self.assertFalse(_stream().is_subscriber("nobody"))

    def test_is_subscriber_after_unsubscribe_false(self):
        stream, _ = _subscribed(subscriber="A")
        stream.unsubscribe("A")
        self.assertFalse(stream.is_subscriber("A"))

    def test_subscribers_returns_sorted_list(self):
        stream = _stream()
        stream.subscribe("Z", [StreamChannel.PROJECT])
        stream.subscribe("A", [StreamChannel.PROJECT])
        subs = stream.subscribers()
        self.assertEqual(subs, sorted(subs))

    def test_subscribers_is_copy(self):
        stream, _ = _subscribed(subscriber="A")
        s1 = stream.subscribers()
        s2 = stream.subscribers()
        self.assertIsNot(s1, s2)

    def test_subscribers_mutation_does_not_affect_stream(self):
        stream, _ = _subscribed(subscriber="A")
        s = stream.subscribers()
        s.clear()
        self.assertEqual(stream.subscriber_count(), 1)


# ---------------------------------------------------------------------------
# 15. Callbacks
# ---------------------------------------------------------------------------

class TestCallbacks(unittest.TestCase):

    def test_callback_called_on_matching_publish(self):
        received = []
        stream = _stream()
        stream.subscribe("A", [StreamChannel.PROJECT], callback=received.append)
        stream.publish(_event(channel=StreamChannel.PROJECT))
        self.assertEqual(len(received), 1)

    def test_callback_not_called_on_non_matching_channel(self):
        received = []
        stream = _stream()
        stream.subscribe("A", [StreamChannel.PROJECT], callback=received.append)
        stream.publish(_event(channel=StreamChannel.CEO))
        self.assertEqual(len(received), 0)

    def test_callback_receives_correct_event(self):
        received = []
        stream = _stream()
        stream.subscribe("A", [StreamChannel.PROJECT], callback=received.append)
        e = _event(source="Planner", channel=StreamChannel.PROJECT)
        stream.publish(e)
        self.assertIs(received[0], e)

    def test_callback_called_multiple_times(self):
        received = []
        stream = _stream()
        stream.subscribe("A", [StreamChannel.PROJECT], callback=received.append)
        stream.publish(_event(channel=StreamChannel.PROJECT))
        stream.publish(_event(channel=StreamChannel.PROJECT))
        self.assertEqual(len(received), 2)

    def test_callback_not_called_after_unsubscribe(self):
        received = []
        stream = _stream()
        stream.subscribe("A", [StreamChannel.PROJECT], callback=received.append)
        stream.unsubscribe("A")
        stream.publish(_event(channel=StreamChannel.PROJECT))
        self.assertEqual(len(received), 0)

    def test_callback_error_does_not_crash_publish(self):
        def bad_cb(e):
            raise RuntimeError("boom")

        stream = _stream()
        stream.subscribe("A", [StreamChannel.PROJECT], callback=bad_cb)
        stream.publish(_event(channel=StreamChannel.PROJECT))
        self.assertEqual(stream.event_count(), 1)

    def test_callback_error_does_not_block_other_subscribers(self):
        received = []
        stream = _stream()
        stream.subscribe("A", [StreamChannel.PROJECT], callback=lambda e: (_ for _ in ()).throw(RuntimeError()))
        stream.subscribe("B", [StreamChannel.PROJECT], callback=received.append)
        stream.publish(_event(channel=StreamChannel.PROJECT))
        self.assertEqual(len(received), 1)

    def test_no_callback_still_stores_event(self):
        stream = _stream()
        stream.subscribe("A", [StreamChannel.PROJECT])
        stream.publish(_event(channel=StreamChannel.PROJECT))
        self.assertEqual(stream.event_count(), 1)

    def test_callback_called_for_all_subscribed_channels(self):
        received = []
        stream = _stream()
        stream.subscribe("A", [StreamChannel.PROJECT, StreamChannel.CEO], callback=received.append)
        stream.publish(_event(channel=StreamChannel.PROJECT))
        stream.publish(_event(channel=StreamChannel.CEO))
        self.assertEqual(len(received), 2)

    def test_callback_not_called_for_unsubscribed_channels(self):
        received = []
        stream = _stream()
        stream.subscribe("A", [StreamChannel.PROJECT], callback=received.append)
        for ch in StreamChannel:
            if ch != StreamChannel.PROJECT:
                stream.publish(_event(channel=ch))
        self.assertEqual(len(received), 0)

    def test_multiple_callbacks_all_called(self):
        received_a = []
        received_b = []
        stream = _stream()
        stream.subscribe("A", [StreamChannel.PROJECT], callback=received_a.append)
        stream.subscribe("B", [StreamChannel.PROJECT], callback=received_b.append)
        stream.publish(_event(channel=StreamChannel.PROJECT))
        self.assertEqual(len(received_a), 1)
        self.assertEqual(len(received_b), 1)

    def test_all_channels_callback_receives_all(self):
        received = []
        stream = _stream()
        stream.subscribe("Dashboard", list(StreamChannel), callback=received.append)
        for ch in StreamChannel:
            stream.publish(_event(channel=ch))
        self.assertEqual(len(received), len(StreamChannel))


# ---------------------------------------------------------------------------
# 16. Multi-subscriber scenarios
# ---------------------------------------------------------------------------

class TestMultiSubscriber(unittest.TestCase):

    def test_two_subscribers_same_channel(self):
        received_a = []
        received_b = []
        stream = _stream()
        stream.subscribe("A", [StreamChannel.PROJECT], callback=received_a.append)
        stream.subscribe("B", [StreamChannel.PROJECT], callback=received_b.append)
        stream.publish(_event(channel=StreamChannel.PROJECT))
        self.assertEqual(len(received_a), 1)
        self.assertEqual(len(received_b), 1)

    def test_two_subscribers_different_channels(self):
        received_a = []
        received_b = []
        stream = _stream()
        stream.subscribe("A", [StreamChannel.PROJECT], callback=received_a.append)
        stream.subscribe("B", [StreamChannel.CEO], callback=received_b.append)
        stream.publish(_event(channel=StreamChannel.PROJECT))
        stream.publish(_event(channel=StreamChannel.CEO))
        self.assertEqual(len(received_a), 1)
        self.assertEqual(len(received_b), 1)
        # Cross-delivery should NOT happen
        stream.publish(_event(channel=StreamChannel.PROJECT))
        self.assertEqual(len(received_b), 1)

    def test_subscriber_counts_per_channel(self):
        stream = _stream()
        stream.subscribe("A", [StreamChannel.PROJECT, StreamChannel.CEO])
        stream.subscribe("B", [StreamChannel.PROJECT])
        stats = stream.statistics()
        self.assertEqual(stats["subscribers_by_channel"]["PROJECT"], 2)
        self.assertEqual(stats["subscribers_by_channel"]["CEO"], 1)

    def test_subscriber_unsubscribe_does_not_affect_others(self):
        received_b = []
        stream = _stream()
        stream.subscribe("A", [StreamChannel.PROJECT])
        stream.subscribe("B", [StreamChannel.PROJECT], callback=received_b.append)
        stream.unsubscribe("A")
        stream.publish(_event(channel=StreamChannel.PROJECT))
        self.assertEqual(len(received_b), 1)

    def test_six_subscribers_all_channels(self):
        received = {f"S{i}": [] for i in range(6)}
        stream = _stream()
        for name, inbox in received.items():
            stream.subscribe(name, list(StreamChannel), callback=inbox.append)
        stream.publish(_event(channel=StreamChannel.PROJECT))
        for inbox in received.values():
            self.assertEqual(len(inbox), 1)

    def test_selective_subscribers(self):
        received_all = []
        received_project = []
        stream = _stream()
        stream.subscribe("All", list(StreamChannel), callback=received_all.append)
        stream.subscribe("ProjectOnly", [StreamChannel.PROJECT], callback=received_project.append)
        for ch in StreamChannel:
            stream.publish(_event(channel=ch))
        self.assertEqual(len(received_all), len(StreamChannel))
        self.assertEqual(len(received_project), 1)


# ---------------------------------------------------------------------------
# 17. Integration flows
# ---------------------------------------------------------------------------

class TestIntegration(unittest.TestCase):

    def test_full_producer_consumer_flow(self):
        received = []
        stream = EventStream()

        stream.subscribe("Dashboard", list(StreamChannel), callback=received.append)

        producers = [
            ("Planner", StreamChannel.PROJECT),
            ("Executive", StreamChannel.PROJECT),
            ("WorkflowEngine", StreamChannel.WORKFLOW),
            ("AgentRuntime", StreamChannel.RUNTIME),
            ("DiscussionEngine", StreamChannel.DISCUSSION),
            ("DecisionEngine", StreamChannel.DECISION),
        ]

        for source, channel in producers:
            stream.publish(StreamEvent.create(source, channel, {"step": source}))

        self.assertEqual(len(received), len(producers))

    def test_history_after_full_flow(self):
        stream = EventStream()
        stream.subscribe("A", list(StreamChannel))
        for ch in StreamChannel:
            stream.publish(_event(channel=ch))
        self.assertEqual(len(stream.history()), len(StreamChannel))

    def test_filter_history_after_mixed_publishes(self):
        stream = EventStream()
        for _ in range(3):
            stream.publish(_event(source="Planner", channel=StreamChannel.PROJECT))
        for _ in range(2):
            stream.publish(_event(source="Executive", channel=StreamChannel.RUNTIME))
        h = stream.history(channel=StreamChannel.PROJECT)
        self.assertEqual(len(h), 3)
        h2 = stream.history(source="Executive")
        self.assertEqual(len(h2), 2)

    def test_statistics_after_full_flow(self):
        stream = EventStream()
        stream.subscribe("A", [StreamChannel.PROJECT])
        stream.subscribe("B", list(StreamChannel))
        stream.publish(_event(channel=StreamChannel.PROJECT))
        stream.publish(_event(channel=StreamChannel.CEO))
        stats = stream.statistics()
        self.assertEqual(stats["total_events"], 2)
        self.assertEqual(stats["total_subscribers"], 2)

    def test_resubscribe_flow(self):
        received = []
        stream = EventStream()
        stream.subscribe("A", [StreamChannel.PROJECT], callback=received.append)
        stream.publish(_event(channel=StreamChannel.PROJECT))
        stream.unsubscribe("A")
        stream.subscribe("A", [StreamChannel.CEO], callback=received.append)
        stream.publish(_event(channel=StreamChannel.PROJECT))
        stream.publish(_event(channel=StreamChannel.CEO))
        self.assertEqual(len(received), 2)

    def test_event_count_helper(self):
        stream = _stream()
        self.assertEqual(stream.event_count(), 0)
        stream.publish(_event())
        self.assertEqual(stream.event_count(), 1)

    def test_subscriber_count_helper(self):
        stream = _stream()
        self.assertEqual(stream.subscriber_count(), 0)
        stream.subscribe("A", [StreamChannel.PROJECT])
        self.assertEqual(stream.subscriber_count(), 1)

    def test_memory_channel_events(self):
        received = []
        stream = EventStream()
        stream.subscribe("MemoryWatcher", [StreamChannel.MEMORY], callback=received.append)
        stream.publish(StreamEvent.create("MemoryEngine", StreamChannel.MEMORY, {"action": "store"}))
        stream.publish(StreamEvent.create("MemoryEngine", StreamChannel.MEMORY, {"action": "retrieve"}))
        self.assertEqual(len(received), 2)

    def test_decision_channel_events(self):
        received = []
        stream = EventStream()
        stream.subscribe("DecisionWatcher", [StreamChannel.DECISION], callback=received.append)
        stream.publish(StreamEvent.create("DecisionEngine", StreamChannel.DECISION, {"decision": "approved"}))
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].get_payload_value("decision"), "approved")

    def test_system_channel_events(self):
        received = []
        stream = EventStream()
        stream.subscribe("SystemMonitor", [StreamChannel.SYSTEM], callback=received.append)
        stream.publish(StreamEvent.create("EventStream", StreamChannel.SYSTEM, {"type": "startup"}))
        self.assertEqual(len(received), 1)

    def test_latest_reflects_most_recent(self):
        stream = EventStream()
        for i in range(5):
            stream.publish(StreamEvent.create(f"S{i}", StreamChannel.PROJECT))
        latest = stream.latest(StreamChannel.PROJECT)
        self.assertEqual(latest.source, "S4")

    def test_history_limit_with_source_filter(self):
        stream = EventStream()
        for i in range(5):
            stream.publish(StreamEvent.create("Planner", StreamChannel.PROJECT))
        stream.publish(StreamEvent.create("Executive", StreamChannel.PROJECT))
        h = stream.history(source="Planner", limit=2)
        self.assertEqual(len(h), 2)
        for e in h:
            self.assertEqual(e.source, "Planner")

    def test_subscription_created_at_is_set(self):
        stream = EventStream()
        before = datetime.now(timezone.utc)
        sub = stream.subscribe("A", [StreamChannel.PROJECT])
        after = datetime.now(timezone.utc)
        self.assertGreaterEqual(sub.created_at, before)
        self.assertLessEqual(sub.created_at, after)


# ---------------------------------------------------------------------------
# 18. StreamChannel additional coverage
# ---------------------------------------------------------------------------

class TestStreamChannelAdditional(unittest.TestCase):

    def test_channel_equality(self):
        self.assertEqual(StreamChannel.PROJECT, StreamChannel.PROJECT)

    def test_channel_inequality(self):
        self.assertNotEqual(StreamChannel.PROJECT, StreamChannel.CEO)

    def test_channel_in_set(self):
        s = {StreamChannel.PROJECT, StreamChannel.CEO}
        self.assertIn(StreamChannel.PROJECT, s)

    def test_all_operational_not_governance(self):
        for ch in StreamChannel:
            if ch.is_operational_channel():
                self.assertFalse(ch.is_governance_channel())

    def test_all_governance_not_operational(self):
        for ch in StreamChannel:
            if ch.is_governance_channel():
                self.assertFalse(ch.is_operational_channel())

    def test_no_channel_is_both_system_and_ceo(self):
        for ch in StreamChannel:
            self.assertFalse(ch.is_system_channel() and ch.is_ceo_channel())

    def test_exactly_one_system_channel(self):
        count = sum(1 for ch in StreamChannel if ch.is_system_channel())
        self.assertEqual(count, 1)

    def test_exactly_one_ceo_channel(self):
        count = sum(1 for ch in StreamChannel if ch.is_ceo_channel())
        self.assertEqual(count, 1)

    def test_six_operational_channels(self):
        count = sum(1 for ch in StreamChannel if ch.is_operational_channel())
        self.assertEqual(count, 6)

    def test_two_governance_channels(self):
        count = sum(1 for ch in StreamChannel if ch.is_governance_channel())
        self.assertEqual(count, 2)

    def test_channel_used_as_dict_key(self):
        d = {ch: i for i, ch in enumerate(StreamChannel)}
        self.assertEqual(len(d), 8)

    def test_channel_display_name_not_uppercase(self):
        for ch in StreamChannel:
            dn = ch.display_name()
            self.assertNotEqual(dn, dn.upper())

    def test_workflow_is_operational(self):
        self.assertTrue(StreamChannel.WORKFLOW.is_operational_channel())

    def test_decision_is_operational(self):
        self.assertTrue(StreamChannel.DECISION.is_operational_channel())

    def test_memory_is_operational(self):
        self.assertTrue(StreamChannel.MEMORY.is_operational_channel())

    def test_runtime_is_operational(self):
        self.assertTrue(StreamChannel.RUNTIME.is_operational_channel())

    def test_discussion_is_operational(self):
        self.assertTrue(StreamChannel.DISCUSSION.is_operational_channel())


# ---------------------------------------------------------------------------
# 19. StreamEvent payload edge cases
# ---------------------------------------------------------------------------

class TestStreamEventPayloadEdgeCases(unittest.TestCase):

    def test_nested_payload(self):
        e = StreamEvent.create("A", StreamChannel.PROJECT, payload={"nested": {"k": 1}})
        self.assertEqual(e.get_payload_value("nested"), {"k": 1})

    def test_list_payload_value(self):
        e = StreamEvent.create("A", StreamChannel.PROJECT, payload={"items": [1, 2, 3]})
        self.assertEqual(e.get_payload_value("items"), [1, 2, 3])

    def test_boolean_payload_value(self):
        e = StreamEvent.create("A", StreamChannel.PROJECT, payload={"flag": True})
        self.assertTrue(e.get_payload_value("flag"))

    def test_zero_payload_value(self):
        e = StreamEvent.create("A", StreamChannel.PROJECT, payload={"count": 0})
        self.assertEqual(e.get_payload_value("count"), 0)

    def test_none_payload_value(self):
        e = StreamEvent.create("A", StreamChannel.PROJECT, payload={"val": None})
        self.assertIsNone(e.get_payload_value("val"))

    def test_large_payload(self):
        big = {f"key_{i}": i for i in range(100)}
        e = StreamEvent.create("A", StreamChannel.PROJECT, payload=big)
        self.assertEqual(e.get_payload_value("key_99"), 99)

    def test_summary_payload_keys_list(self):
        e = StreamEvent.create("A", StreamChannel.PROJECT, payload={"x": 1, "y": 2})
        keys = e.summary()["payload_keys"]
        self.assertIn("x", keys)
        self.assertIn("y", keys)

    def test_summary_has_payload_true(self):
        e = StreamEvent.create("A", StreamChannel.PROJECT, payload={"x": 1})
        self.assertTrue(e.summary()["has_payload"])

    def test_summary_has_payload_false(self):
        e = StreamEvent.create("A", StreamChannel.PROJECT)
        self.assertFalse(e.summary()["has_payload"])

    def test_two_events_independent_payloads(self):
        e1 = StreamEvent.create("A", StreamChannel.PROJECT, payload={"x": 1})
        e2 = StreamEvent.create("A", StreamChannel.PROJECT, payload={"y": 2})
        self.assertNotIn("y", e1.payload)
        self.assertNotIn("x", e2.payload)

    def test_source_case_sensitive(self):
        e1 = StreamEvent.create("Planner", StreamChannel.PROJECT)
        e2 = StreamEvent.create("planner", StreamChannel.PROJECT)
        self.assertFalse(e1.is_from("planner"))
        self.assertTrue(e2.is_from("planner"))


# ---------------------------------------------------------------------------
# 20. StreamSubscription covers_any and multi-channel
# ---------------------------------------------------------------------------

class TestStreamSubscriptionMultiChannel(unittest.TestCase):

    def _sub(self, channels):
        return StreamSubscription(subscriber="S", channels=channels)

    def test_multi_channel_is_subscribed_to_each(self):
        chs = [StreamChannel.PROJECT, StreamChannel.WORKFLOW, StreamChannel.CEO]
        sub = self._sub(chs)
        for ch in chs:
            self.assertTrue(sub.is_subscribed_to(ch))

    def test_multi_channel_not_subscribed_to_others(self):
        chs = [StreamChannel.PROJECT, StreamChannel.WORKFLOW]
        sub = self._sub(chs)
        others = [c for c in StreamChannel if c not in chs]
        for ch in others:
            self.assertFalse(sub.is_subscribed_to(ch))

    def test_covers_any_with_overlap(self):
        sub = self._sub([StreamChannel.PROJECT, StreamChannel.WORKFLOW])
        self.assertTrue(sub.covers_any([StreamChannel.WORKFLOW, StreamChannel.CEO]))

    def test_covers_any_no_overlap(self):
        sub = self._sub([StreamChannel.PROJECT])
        self.assertFalse(sub.covers_any([StreamChannel.CEO, StreamChannel.SYSTEM]))

    def test_duplicate_channels_in_subscription(self):
        sub = self._sub([StreamChannel.PROJECT, StreamChannel.PROJECT])
        self.assertTrue(sub.is_subscribed_to(StreamChannel.PROJECT))

    def test_channel_names_all(self):
        sub = self._sub(list(StreamChannel))
        names = sub.channel_names()
        for ch in StreamChannel:
            self.assertIn(str(ch), names)

    def test_is_subscribed_to_all_partial_false(self):
        sub = self._sub([StreamChannel.PROJECT, StreamChannel.WORKFLOW])
        self.assertFalse(sub.is_subscribed_to_all())

    def test_summary_channel_count_matches(self):
        chs = [StreamChannel.PROJECT, StreamChannel.CEO]
        sub = self._sub(chs)
        self.assertEqual(sub.summary()["channel_count"], len(chs))

    def test_summary_channels_are_strings(self):
        sub = self._sub([StreamChannel.PROJECT])
        for c in sub.summary()["channels"]:
            self.assertIsInstance(c, str)


# ---------------------------------------------------------------------------
# 21. EventStream publish advanced
# ---------------------------------------------------------------------------

class TestPublishAdvanced(unittest.TestCase):

    def test_publish_same_event_twice_stored_twice(self):
        stream = EventStream()
        e = StreamEvent.create("A", StreamChannel.PROJECT)
        stream.publish(e)
        stream.publish(e)
        self.assertEqual(stream.event_count(), 2)

    def test_publish_all_eight_channels(self):
        stream = EventStream()
        for ch in StreamChannel:
            stream.publish(StreamEvent.create("Test", ch))
        self.assertEqual(stream.event_count(), 8)

    def test_publish_event_from_dict_raises(self):
        with self.assertRaises(InvalidEventError):
            EventStream().publish({"source": "x", "category": "PROJECT"})

    def test_publish_empty_string_raises(self):
        with self.assertRaises(InvalidEventError):
            EventStream().publish("")

    def test_publish_stores_all_channels_independently(self):
        stream = EventStream()
        for ch in StreamChannel:
            stream.publish(StreamEvent.create("T", ch))
        stats = stream.statistics()["events_by_channel"]
        for ch in StreamChannel:
            self.assertEqual(stats[ch.value], 1)

    def test_publish_does_not_mutate_payload(self):
        original = {"key": "value"}
        e = StreamEvent.create("A", StreamChannel.PROJECT, payload=original)
        stream = EventStream()
        stream.publish(e)
        self.assertEqual(stream.history()[0].payload["key"], "value")


# ---------------------------------------------------------------------------
# 22. EventStream.subscribe() advanced
# ---------------------------------------------------------------------------

class TestSubscribeAdvanced(unittest.TestCase):

    def test_subscribe_ten_different_subscribers(self):
        stream = EventStream()
        for i in range(10):
            stream.subscribe(f"Sub{i}", [StreamChannel.PROJECT])
        self.assertEqual(stream.subscriber_count(), 10)

    def test_subscribe_each_channel_separately(self):
        stream = EventStream()
        for ch in StreamChannel:
            stream.subscribe(f"Sub-{ch.value}", [ch])
        self.assertEqual(stream.subscriber_count(), len(StreamChannel))

    def test_subscribe_returns_correct_channels(self):
        stream = EventStream()
        chs = [StreamChannel.PROJECT, StreamChannel.MEMORY]
        sub = stream.subscribe("A", chs)
        self.assertTrue(sub.is_subscribed_to(StreamChannel.PROJECT))
        self.assertTrue(sub.is_subscribed_to(StreamChannel.MEMORY))
        self.assertFalse(sub.is_subscribed_to(StreamChannel.CEO))

    def test_subscribe_callback_none_allowed(self):
        stream = EventStream()
        sub = stream.subscribe("A", [StreamChannel.PROJECT], callback=None)
        self.assertIsNotNone(sub)

    def test_subscribe_created_at_utc(self):
        stream = EventStream()
        sub = stream.subscribe("A", [StreamChannel.PROJECT])
        self.assertIsNotNone(sub.created_at.tzinfo)


# ---------------------------------------------------------------------------
# 23. EventStream.history() edge cases
# ---------------------------------------------------------------------------

class TestHistoryEdgeCases(unittest.TestCase):

    def test_history_no_events_any_channel(self):
        stream = EventStream()
        for ch in StreamChannel:
            self.assertEqual(stream.history(channel=ch), [])

    def test_history_filter_keeps_all_matching(self):
        stream = EventStream()
        for _ in range(10):
            stream.publish(StreamEvent.create("P", StreamChannel.PROJECT))
        h = stream.history(channel=StreamChannel.PROJECT)
        self.assertEqual(len(h), 10)

    def test_history_limit_one(self):
        stream = EventStream()
        for i in range(5):
            stream.publish(StreamEvent.create(f"S{i}", StreamChannel.PROJECT))
        h = stream.history(limit=1)
        self.assertEqual(len(h), 1)
        self.assertEqual(h[0].source, "S4")

    def test_history_preserves_event_identity(self):
        stream = EventStream()
        e = StreamEvent.create("A", StreamChannel.PROJECT)
        stream.publish(e)
        h = stream.history()
        self.assertIs(h[0], e)

    def test_history_channel_counts_per_type(self):
        stream = EventStream()
        for _ in range(3):
            stream.publish(StreamEvent.create("A", StreamChannel.PROJECT))
        for _ in range(2):
            stream.publish(StreamEvent.create("A", StreamChannel.CEO))
        self.assertEqual(len(stream.history(channel=StreamChannel.PROJECT)), 3)
        self.assertEqual(len(stream.history(channel=StreamChannel.CEO)), 2)

    def test_history_with_none_filters_returns_all(self):
        stream = EventStream()
        for ch in StreamChannel:
            stream.publish(StreamEvent.create("T", ch))
        h = stream.history(channel=None, source=None, limit=None)
        self.assertEqual(len(h), len(StreamChannel))

    def test_history_limit_larger_than_filtered(self):
        stream = EventStream()
        stream.publish(StreamEvent.create("A", StreamChannel.PROJECT))
        h = stream.history(channel=StreamChannel.PROJECT, limit=50)
        self.assertEqual(len(h), 1)


# ---------------------------------------------------------------------------
# 24. EventStream.latest() edge cases
# ---------------------------------------------------------------------------

class TestLatestEdgeCases(unittest.TestCase):

    def test_latest_updates_after_each_publish(self):
        stream = EventStream()
        for i in range(5):
            e = StreamEvent.create(f"S{i}", StreamChannel.PROJECT)
            stream.publish(e)
            self.assertEqual(stream.latest().source, f"S{i}")

    def test_latest_different_channels_independent(self):
        stream = EventStream()
        ep = StreamEvent.create("Planner", StreamChannel.PROJECT)
        ec = StreamEvent.create("CEO", StreamChannel.CEO)
        stream.publish(ep)
        stream.publish(ec)
        self.assertIs(stream.latest(StreamChannel.PROJECT), ep)
        self.assertIs(stream.latest(StreamChannel.CEO), ec)

    def test_latest_overall_after_mixed_publishes(self):
        stream = EventStream()
        stream.publish(StreamEvent.create("A", StreamChannel.PROJECT))
        last = StreamEvent.create("B", StreamChannel.CEO)
        stream.publish(last)
        self.assertIs(stream.latest(), last)

    def test_latest_channel_not_published_to_none(self):
        stream = EventStream()
        stream.publish(StreamEvent.create("A", StreamChannel.PROJECT))
        self.assertIsNone(stream.latest(StreamChannel.MEMORY))


# ---------------------------------------------------------------------------
# 25. EventStream.statistics() edge cases
# ---------------------------------------------------------------------------

class TestStatisticsEdgeCases(unittest.TestCase):

    def test_all_channel_keys_present_empty(self):
        stats = EventStream().statistics()
        for ch in StreamChannel:
            self.assertIn(ch.value, stats["events_by_channel"])

    def test_all_subscriber_channel_keys_present_empty(self):
        stats = EventStream().statistics()
        for ch in StreamChannel:
            self.assertIn(ch.value, stats["subscribers_by_channel"])

    def test_stats_zero_counts_when_empty(self):
        stats = EventStream().statistics()
        for ch in StreamChannel:
            self.assertEqual(stats["events_by_channel"][ch.value], 0)
            self.assertEqual(stats["subscribers_by_channel"][ch.value], 0)

    def test_events_by_source_grows(self):
        stream = EventStream()
        stream.publish(StreamEvent.create("P", StreamChannel.PROJECT))
        stream.publish(StreamEvent.create("P", StreamChannel.PROJECT))
        self.assertEqual(stream.statistics()["events_by_source"]["P"], 2)

    def test_subscribers_by_channel_multi_subscriber(self):
        stream = EventStream()
        stream.subscribe("A", list(StreamChannel))
        stream.subscribe("B", list(StreamChannel))
        stats = stream.statistics()
        for ch in StreamChannel:
            self.assertEqual(stats["subscribers_by_channel"][ch.value], 2)

    def test_active_subscribers_after_unsubscribe(self):
        stream = EventStream()
        stream.subscribe("A", [StreamChannel.PROJECT])
        stream.subscribe("B", [StreamChannel.PROJECT])
        stream.unsubscribe("A")
        stats = stream.statistics()
        self.assertNotIn("A", stats["active_subscribers"])
        self.assertIn("B", stats["active_subscribers"])

    def test_events_by_source_empty_when_no_events(self):
        self.assertEqual(EventStream().statistics()["events_by_source"], {})


# ---------------------------------------------------------------------------
# 26. EventStream helper methods
# ---------------------------------------------------------------------------

class TestEventStreamHelpers(unittest.TestCase):

    def test_event_count_increments(self):
        stream = EventStream()
        for i in range(1, 6):
            stream.publish(StreamEvent.create("A", StreamChannel.PROJECT))
            self.assertEqual(stream.event_count(), i)

    def test_subscriber_count_increments(self):
        stream = EventStream()
        for i in range(1, 4):
            stream.subscribe(f"Sub{i}", [StreamChannel.PROJECT])
            self.assertEqual(stream.subscriber_count(), i)

    def test_subscriber_count_decrements(self):
        stream = EventStream()
        stream.subscribe("A", [StreamChannel.PROJECT])
        stream.subscribe("B", [StreamChannel.PROJECT])
        stream.unsubscribe("A")
        self.assertEqual(stream.subscriber_count(), 1)

    def test_is_subscriber_true_after_subscribe(self):
        stream = EventStream()
        stream.subscribe("Monitor", [StreamChannel.SYSTEM])
        self.assertTrue(stream.is_subscriber("Monitor"))

    def test_is_subscriber_false_for_nonexistent(self):
        self.assertFalse(EventStream().is_subscriber("nobody"))

    def test_subscribers_returns_list(self):
        stream = EventStream()
        self.assertIsInstance(stream.subscribers(), list)

    def test_subscribers_empty_on_new_stream(self):
        self.assertEqual(EventStream().subscribers(), [])

    def test_subscribers_after_subscribe(self):
        stream = EventStream()
        stream.subscribe("A", [StreamChannel.PROJECT])
        self.assertIn("A", stream.subscribers())

    def test_subscribers_after_unsubscribe(self):
        stream = EventStream()
        stream.subscribe("A", [StreamChannel.PROJECT])
        stream.unsubscribe("A")
        self.assertNotIn("A", stream.subscribers())

    def test_find_subscription_returns_correct_channels(self):
        stream = EventStream()
        stream.subscribe("A", [StreamChannel.PROJECT, StreamChannel.CEO])
        sub = stream.find_subscription("A")
        self.assertTrue(sub.is_subscribed_to(StreamChannel.PROJECT))
        self.assertTrue(sub.is_subscribed_to(StreamChannel.CEO))


# ---------------------------------------------------------------------------
# 27. All producers from sprint spec
# ---------------------------------------------------------------------------

class TestAllProducers(unittest.TestCase):
    """Verify each sprint-specified producer can publish to the stream."""

    def setUp(self):
        self.stream = EventStream()
        self.received = []
        self.stream.subscribe("Dashboard", list(StreamChannel), callback=self.received.append)

    def test_planner_publishes(self):
        e = StreamEvent.create("Planner", StreamChannel.PROJECT, {"action": "analyzed"})
        self.stream.publish(e)
        self.assertEqual(len(self.received), 1)
        self.assertEqual(self.received[0].source, "Planner")

    def test_executive_publishes(self):
        e = StreamEvent.create("Executive", StreamChannel.PROJECT, {"action": "created"})
        self.stream.publish(e)
        self.assertEqual(self.received[0].source, "Executive")

    def test_workflow_publishes(self):
        e = StreamEvent.create("WorkflowEngine", StreamChannel.WORKFLOW, {"stage": "Planning"})
        self.stream.publish(e)
        self.assertEqual(self.received[0].category, StreamChannel.WORKFLOW)

    def test_runtime_publishes(self):
        e = StreamEvent.create("AgentRuntime", StreamChannel.RUNTIME, {"agent": "BackendEngineer"})
        self.stream.publish(e)
        self.assertEqual(self.received[0].category, StreamChannel.RUNTIME)

    def test_discussion_publishes(self):
        e = StreamEvent.create("DiscussionEngine", StreamChannel.DISCUSSION, {"topic": "Tech stack"})
        self.stream.publish(e)
        self.assertEqual(self.received[0].category, StreamChannel.DISCUSSION)

    def test_decision_publishes(self):
        e = StreamEvent.create("DecisionEngine", StreamChannel.DECISION, {"decision": "Go"})
        self.stream.publish(e)
        self.assertEqual(self.received[0].category, StreamChannel.DECISION)

    def test_memory_publishes(self):
        e = StreamEvent.create("MemoryEngine", StreamChannel.MEMORY, {"action": "store"})
        self.stream.publish(e)
        self.assertEqual(self.received[0].category, StreamChannel.MEMORY)

    def test_company_orchestrator_publishes(self):
        e = StreamEvent.create("CompanyOrchestrator", StreamChannel.SYSTEM, {"status": "started"})
        self.stream.publish(e)
        self.assertEqual(self.received[0].source, "CompanyOrchestrator")

    def test_dashboard_receives_all_producers(self):
        producers = [
            ("Planner", StreamChannel.PROJECT),
            ("Executive", StreamChannel.PROJECT),
            ("WorkflowEngine", StreamChannel.WORKFLOW),
            ("AgentRuntime", StreamChannel.RUNTIME),
            ("DiscussionEngine", StreamChannel.DISCUSSION),
            ("DecisionEngine", StreamChannel.DECISION),
            ("MemoryEngine", StreamChannel.MEMORY),
            ("CompanyOrchestrator", StreamChannel.SYSTEM),
        ]
        for source, ch in producers:
            self.stream.publish(StreamEvent.create(source, ch))
        self.assertEqual(len(self.received), len(producers))

    def test_history_contains_all_producer_events(self):
        producers = [
            ("Planner", StreamChannel.PROJECT),
            ("Executive", StreamChannel.PROJECT),
            ("WorkflowEngine", StreamChannel.WORKFLOW),
            ("AgentRuntime", StreamChannel.RUNTIME),
            ("DiscussionEngine", StreamChannel.DISCUSSION),
            ("DecisionEngine", StreamChannel.DECISION),
        ]
        for source, ch in producers:
            self.stream.publish(StreamEvent.create(source, ch))
        self.assertEqual(self.stream.event_count(), len(producers))


# ---------------------------------------------------------------------------
# 28. EventStream channel isolation
# ---------------------------------------------------------------------------

class TestChannelIsolation(unittest.TestCase):

    def test_subscriber_on_one_channel_does_not_receive_others(self):
        counts = {ch: [] for ch in StreamChannel}
        stream = EventStream()
        for ch in StreamChannel:
            stream.subscribe(f"Sub-{ch.value}", [ch], callback=counts[ch].append)
        for ch in StreamChannel:
            stream.publish(StreamEvent.create("T", ch))
        for ch in StreamChannel:
            self.assertEqual(len(counts[ch]), 1)
            self.assertEqual(counts[ch][0].category, ch)

    def test_history_per_channel_isolated(self):
        stream = EventStream()
        stream.publish(StreamEvent.create("A", StreamChannel.PROJECT))
        stream.publish(StreamEvent.create("B", StreamChannel.CEO))
        for ch in StreamChannel:
            h = stream.history(channel=ch)
            for e in h:
                self.assertEqual(e.category, ch)

    def test_publish_to_workflow_does_not_appear_in_decision_history(self):
        stream = EventStream()
        stream.publish(StreamEvent.create("WE", StreamChannel.WORKFLOW))
        self.assertEqual(len(stream.history(channel=StreamChannel.DECISION)), 0)

    def test_six_isolated_subscribers_correct_counts(self):
        received = {ch.value: 0 for ch in StreamChannel}
        stream = EventStream()
        for ch in StreamChannel:
            def make_cb(c):
                def cb(e):
                    received[c.value] += 1
                return cb
            stream.subscribe(f"Sub-{ch.value}", [ch], callback=make_cb(ch))
        for ch in StreamChannel:
            for _ in range(3):
                stream.publish(StreamEvent.create("T", ch))
        for ch in StreamChannel:
            self.assertEqual(received[ch.value], 3)


# ---------------------------------------------------------------------------
# 29. EventStream empty payload normalization
# ---------------------------------------------------------------------------

class TestEventStreamPayloadNormalization(unittest.TestCase):

    def test_none_payload_normalizes_to_empty_dict(self):
        e = StreamEvent.create("A", StreamChannel.PROJECT, payload=None)
        self.assertEqual(e.payload, {})

    def test_empty_dict_payload(self):
        e = StreamEvent.create("A", StreamChannel.PROJECT, payload={})
        self.assertEqual(e.payload, {})
        self.assertFalse(e.has_payload())

    def test_create_without_payload_arg(self):
        e = StreamEvent.create("A", StreamChannel.PROJECT)
        self.assertEqual(e.payload, {})

    def test_publish_with_empty_payload_stored(self):
        stream = EventStream()
        e = StreamEvent.create("A", StreamChannel.PROJECT)
        stream.publish(e)
        self.assertEqual(stream.history()[0].payload, {})

    def test_payload_dict_is_not_shared_between_events(self):
        e1 = StreamEvent.create("A", StreamChannel.PROJECT)
        e2 = StreamEvent.create("A", StreamChannel.PROJECT)
        self.assertIsNot(e1.payload, e2.payload)


if __name__ == "__main__":
    unittest.main()
