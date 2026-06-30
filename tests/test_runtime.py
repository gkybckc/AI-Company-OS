"""
Comprehensive unit tests for Sprint 3 — Company Runtime.

Covers: RuntimeStatus, RuntimeState, RuntimeEventType, RuntimeEvent,
ComponentStatus, ComponentRecord, RuntimeRegistry, and CompanyRuntime.

Run with:
    .venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_runtime.py" -v
"""

import unittest
from datetime import datetime, timezone

from core.runtime_events import RuntimeEvent, RuntimeEventType
from core.runtime_registry import (
    ComponentAlreadyRegisteredError,
    ComponentNotFoundError,
    ComponentRecord,
    ComponentStatus,
    RuntimeRegistry,
)
from core.runtime_state import RuntimeState, RuntimeStatus
from core.runtime import (
    CompanyRuntime,
    RuntimeAlreadyRunningError,
    RuntimeNotRunningError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_runtime_event(
    event_type: RuntimeEventType = RuntimeEventType.RUNTIME_STARTED,
) -> RuntimeEvent:
    return RuntimeEvent(
        id="test-id",
        event_type=event_type,
        timestamp=datetime.now(timezone.utc),
        payload={"key": "value"},
    )


def _make_component_record(
    name: str = "test-component",
    component_type: str = "TestType",
    status: ComponentStatus = ComponentStatus.REGISTERED,
) -> ComponentRecord:
    return ComponentRecord(
        name=name,
        component_type=component_type,
        status=status,
        registered_at=datetime.now(timezone.utc),
        metadata={},
    )


def _started_runtime() -> CompanyRuntime:
    rt = CompanyRuntime()
    rt.start()
    return rt


# ---------------------------------------------------------------------------
# TestRuntimeStatus
# ---------------------------------------------------------------------------

class TestRuntimeStatus(unittest.TestCase):

    def test_all_five_values_exist(self) -> None:
        names = {s.name for s in RuntimeStatus}
        self.assertEqual(
            names,
            {"STOPPED", "STARTING", "RUNNING", "STOPPING", "ERROR"},
        )

    def test_str_returns_value(self) -> None:
        for status in RuntimeStatus:
            self.assertEqual(str(status), status.value)

    def test_is_str_subclass(self) -> None:
        self.assertIsInstance(RuntimeStatus.RUNNING, str)

    def test_string_comparison_works(self) -> None:
        self.assertEqual(RuntimeStatus.STOPPED, "STOPPED")
        self.assertEqual(RuntimeStatus.RUNNING, "RUNNING")

    def test_values_are_uppercase_strings(self) -> None:
        for status in RuntimeStatus:
            self.assertEqual(status.value, status.value.upper())


# ---------------------------------------------------------------------------
# TestRuntimeState
# ---------------------------------------------------------------------------

class TestRuntimeState(unittest.TestCase):

    def test_all_fields_stored(self) -> None:
        ts = datetime.now(timezone.utc)
        state = RuntimeState(
            status=RuntimeStatus.RUNNING,
            started_at=ts,
            stopped_at=None,
            error_message=None,
        )
        self.assertEqual(state.status, RuntimeStatus.RUNNING)
        self.assertEqual(state.started_at, ts)
        self.assertIsNone(state.stopped_at)
        self.assertIsNone(state.error_message)

    def test_is_frozen(self) -> None:
        state = RuntimeState(
            status=RuntimeStatus.STOPPED,
            started_at=None,
            stopped_at=None,
            error_message=None,
        )
        with self.assertRaises(Exception):
            state.status = RuntimeStatus.RUNNING  # type: ignore[misc]

    def test_none_fields_allowed(self) -> None:
        state = RuntimeState(
            status=RuntimeStatus.STOPPED,
            started_at=None,
            stopped_at=None,
            error_message=None,
        )
        self.assertIsNone(state.started_at)
        self.assertIsNone(state.stopped_at)
        self.assertIsNone(state.error_message)

    def test_error_message_stored(self) -> None:
        state = RuntimeState(
            status=RuntimeStatus.ERROR,
            started_at=None,
            stopped_at=None,
            error_message="something went wrong",
        )
        self.assertEqual(state.error_message, "something went wrong")

    def test_both_timestamps_can_be_set(self) -> None:
        start = datetime.now(timezone.utc)
        stop = datetime.now(timezone.utc)
        state = RuntimeState(
            status=RuntimeStatus.STOPPED,
            started_at=start,
            stopped_at=stop,
            error_message=None,
        )
        self.assertEqual(state.started_at, start)
        self.assertEqual(state.stopped_at, stop)


# ---------------------------------------------------------------------------
# TestRuntimeEventType
# ---------------------------------------------------------------------------

class TestRuntimeEventType(unittest.TestCase):

    def test_all_six_values_exist(self) -> None:
        names = {e.name for e in RuntimeEventType}
        self.assertEqual(
            names,
            {
                "RUNTIME_STARTED",
                "RUNTIME_STOPPED",
                "RUNTIME_ERROR",
                "COMPONENT_REGISTERED",
                "COMPONENT_DEREGISTERED",
                "HEALTH_CHECK",
            },
        )

    def test_str_returns_value(self) -> None:
        for event_type in RuntimeEventType:
            self.assertEqual(str(event_type), event_type.value)

    def test_is_str_subclass(self) -> None:
        self.assertIsInstance(RuntimeEventType.RUNTIME_STARTED, str)


# ---------------------------------------------------------------------------
# TestRuntimeEvent
# ---------------------------------------------------------------------------

class TestRuntimeEvent(unittest.TestCase):

    def test_all_fields_stored(self) -> None:
        ts = datetime.now(timezone.utc)
        event = RuntimeEvent(
            id="abc-123",
            event_type=RuntimeEventType.RUNTIME_STARTED,
            timestamp=ts,
            payload={"key": "val"},
        )
        self.assertEqual(event.id, "abc-123")
        self.assertEqual(event.event_type, RuntimeEventType.RUNTIME_STARTED)
        self.assertEqual(event.timestamp, ts)
        self.assertEqual(event.payload, {"key": "val"})

    def test_is_frozen(self) -> None:
        event = _make_runtime_event()
        with self.assertRaises(Exception):
            event.id = "different-id"  # type: ignore[misc]

    def test_empty_payload_allowed(self) -> None:
        event = RuntimeEvent(
            id="x",
            event_type=RuntimeEventType.HEALTH_CHECK,
            timestamp=datetime.now(timezone.utc),
            payload={},
        )
        self.assertEqual(event.payload, {})

    def test_event_type_is_runtime_event_type_enum(self) -> None:
        event = _make_runtime_event(RuntimeEventType.COMPONENT_REGISTERED)
        self.assertIsInstance(event.event_type, RuntimeEventType)

    def test_timestamp_is_datetime(self) -> None:
        event = _make_runtime_event()
        self.assertIsInstance(event.timestamp, datetime)


# ---------------------------------------------------------------------------
# TestComponentStatus
# ---------------------------------------------------------------------------

class TestComponentStatus(unittest.TestCase):

    def test_all_four_values_exist(self) -> None:
        names = {s.name for s in ComponentStatus}
        self.assertEqual(names, {"REGISTERED", "ACTIVE", "INACTIVE", "ERROR"})

    def test_str_returns_value(self) -> None:
        for status in ComponentStatus:
            self.assertEqual(str(status), status.value)

    def test_is_str_subclass(self) -> None:
        self.assertIsInstance(ComponentStatus.ACTIVE, str)


# ---------------------------------------------------------------------------
# TestComponentRecord
# ---------------------------------------------------------------------------

class TestComponentRecord(unittest.TestCase):

    def test_all_fields_stored(self) -> None:
        ts = datetime.now(timezone.utc)
        record = ComponentRecord(
            name="event-bus",
            component_type="EventBus",
            status=ComponentStatus.REGISTERED,
            registered_at=ts,
            metadata={"version": "1"},
        )
        self.assertEqual(record.name, "event-bus")
        self.assertEqual(record.component_type, "EventBus")
        self.assertEqual(record.status, ComponentStatus.REGISTERED)
        self.assertEqual(record.registered_at, ts)
        self.assertEqual(record.metadata, {"version": "1"})

    def test_status_is_mutable(self) -> None:
        record = _make_component_record()
        record.status = ComponentStatus.ACTIVE
        self.assertEqual(record.status, ComponentStatus.ACTIVE)

    def test_empty_metadata_allowed(self) -> None:
        record = _make_component_record()
        record.metadata = {}
        self.assertEqual(record.metadata, {})

    def test_status_is_component_status_enum(self) -> None:
        record = _make_component_record()
        self.assertIsInstance(record.status, ComponentStatus)


# ---------------------------------------------------------------------------
# TestRuntimeRegistry
# ---------------------------------------------------------------------------

class TestRuntimeRegistry(unittest.TestCase):

    def setUp(self) -> None:
        self.registry = RuntimeRegistry()

    def test_register_returns_component_record(self) -> None:
        record = self.registry.register("bus", "EventBus")
        self.assertIsInstance(record, ComponentRecord)

    def test_register_stores_name_and_type(self) -> None:
        record = self.registry.register("bus", "EventBus")
        self.assertEqual(record.name, "bus")
        self.assertEqual(record.component_type, "EventBus")

    def test_register_initial_status_is_registered(self) -> None:
        record = self.registry.register("bus", "EventBus")
        self.assertEqual(record.status, ComponentStatus.REGISTERED)

    def test_register_stores_metadata(self) -> None:
        record = self.registry.register("bus", "EventBus", metadata={"v": "2"})
        self.assertEqual(record.metadata, {"v": "2"})

    def test_register_none_metadata_becomes_empty_dict(self) -> None:
        record = self.registry.register("bus", "EventBus", metadata=None)
        self.assertEqual(record.metadata, {})

    def test_register_duplicate_raises_error(self) -> None:
        self.registry.register("bus", "EventBus")
        with self.assertRaises(ComponentAlreadyRegisteredError):
            self.registry.register("bus", "EventBus")

    def test_deregister_removes_component(self) -> None:
        self.registry.register("bus", "EventBus")
        self.registry.deregister("bus")
        self.assertFalse(self.registry.is_registered("bus"))

    def test_deregister_returns_removed_record(self) -> None:
        self.registry.register("bus", "EventBus")
        record = self.registry.deregister("bus")
        self.assertEqual(record.name, "bus")

    def test_deregister_unknown_raises_error(self) -> None:
        with self.assertRaises(ComponentNotFoundError):
            self.registry.deregister("nonexistent")

    def test_get_returns_record(self) -> None:
        self.registry.register("bus", "EventBus")
        record = self.registry.get("bus")
        self.assertEqual(record.name, "bus")

    def test_get_unknown_raises_error(self) -> None:
        with self.assertRaises(ComponentNotFoundError):
            self.registry.get("nonexistent")

    def test_list_all_returns_all_records(self) -> None:
        self.registry.register("a", "TypeA")
        self.registry.register("b", "TypeB")
        records = self.registry.list_all()
        self.assertEqual(len(records), 2)
        names = {r.name for r in records}
        self.assertEqual(names, {"a", "b"})

    def test_list_all_is_a_copy(self) -> None:
        self.registry.register("a", "TypeA")
        copy = self.registry.list_all()
        copy.clear()
        self.assertEqual(self.registry.count(), 1)

    def test_update_status_changes_status(self) -> None:
        self.registry.register("bus", "EventBus")
        self.registry.update_status("bus", ComponentStatus.ACTIVE)
        record = self.registry.get("bus")
        self.assertEqual(record.status, ComponentStatus.ACTIVE)

    def test_update_status_unknown_raises_error(self) -> None:
        with self.assertRaises(ComponentNotFoundError):
            self.registry.update_status("nonexistent", ComponentStatus.ACTIVE)

    def test_count_is_zero_initially(self) -> None:
        self.assertEqual(self.registry.count(), 0)

    def test_count_increments_on_register(self) -> None:
        self.registry.register("a", "TypeA")
        self.registry.register("b", "TypeB")
        self.assertEqual(self.registry.count(), 2)

    def test_count_decrements_on_deregister(self) -> None:
        self.registry.register("a", "TypeA")
        self.registry.deregister("a")
        self.assertEqual(self.registry.count(), 0)

    def test_is_registered_true(self) -> None:
        self.registry.register("bus", "EventBus")
        self.assertTrue(self.registry.is_registered("bus"))

    def test_is_registered_false(self) -> None:
        self.assertFalse(self.registry.is_registered("nonexistent"))

    def test_reregister_after_deregister_succeeds(self) -> None:
        self.registry.register("bus", "EventBus")
        self.registry.deregister("bus")
        record = self.registry.register("bus", "EventBus")
        self.assertEqual(record.name, "bus")


# ---------------------------------------------------------------------------
# TestCompanyRuntimeLifecycle
# ---------------------------------------------------------------------------

class TestCompanyRuntimeLifecycle(unittest.TestCase):

    def setUp(self) -> None:
        self.rt = CompanyRuntime()

    def test_initial_status_is_stopped(self) -> None:
        self.assertEqual(self.rt.get_state().status, RuntimeStatus.STOPPED)

    def test_start_transitions_to_running(self) -> None:
        self.rt.start()
        self.assertEqual(self.rt.get_state().status, RuntimeStatus.RUNNING)

    def test_start_records_started_at(self) -> None:
        before = datetime.now(timezone.utc)
        self.rt.start()
        after = datetime.now(timezone.utc)
        started_at = self.rt.get_state().started_at
        self.assertIsNotNone(started_at)
        self.assertGreaterEqual(started_at, before)
        self.assertLessEqual(started_at, after)

    def test_start_clears_stopped_at(self) -> None:
        self.rt.start()
        self.rt.stop()
        self.rt.start()
        self.assertIsNone(self.rt.get_state().stopped_at)

    def test_start_when_already_running_raises_error(self) -> None:
        self.rt.start()
        with self.assertRaises(RuntimeAlreadyRunningError):
            self.rt.start()

    def test_start_emits_runtime_started_event(self) -> None:
        self.rt.start()
        events = self.rt.get_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, RuntimeEventType.RUNTIME_STARTED)

    def test_stop_transitions_to_stopped(self) -> None:
        self.rt.start()
        self.rt.stop()
        self.assertEqual(self.rt.get_state().status, RuntimeStatus.STOPPED)

    def test_stop_records_stopped_at(self) -> None:
        self.rt.start()
        before = datetime.now(timezone.utc)
        self.rt.stop()
        after = datetime.now(timezone.utc)
        stopped_at = self.rt.get_state().stopped_at
        self.assertIsNotNone(stopped_at)
        self.assertGreaterEqual(stopped_at, before)
        self.assertLessEqual(stopped_at, after)

    def test_stop_emits_runtime_stopped_event(self) -> None:
        self.rt.start()
        self.rt.stop()
        events = self.rt.get_events()
        types = [e.event_type for e in events]
        self.assertIn(RuntimeEventType.RUNTIME_STOPPED, types)

    def test_stop_when_not_running_raises_error(self) -> None:
        with self.assertRaises(RuntimeNotRunningError):
            self.rt.stop()

    def test_can_restart_after_stop(self) -> None:
        self.rt.start()
        self.rt.stop()
        self.rt.start()
        self.assertEqual(self.rt.get_state().status, RuntimeStatus.RUNNING)

    def test_error_message_is_none_after_clean_start(self) -> None:
        self.rt.start()
        self.assertIsNone(self.rt.get_state().error_message)


# ---------------------------------------------------------------------------
# TestCompanyRuntimeComponents
# ---------------------------------------------------------------------------

class TestCompanyRuntimeComponents(unittest.TestCase):

    def setUp(self) -> None:
        self.rt = _started_runtime()

    def test_register_component_returns_record(self) -> None:
        record = self.rt.register_component("bus", "EventBus")
        self.assertIsInstance(record, ComponentRecord)

    def test_register_component_name_and_type_stored(self) -> None:
        record = self.rt.register_component("bus", "EventBus")
        self.assertEqual(record.name, "bus")
        self.assertEqual(record.component_type, "EventBus")

    def test_register_component_emits_event(self) -> None:
        self.rt.register_component("bus", "EventBus")
        types = [e.event_type for e in self.rt.get_events()]
        self.assertIn(RuntimeEventType.COMPONENT_REGISTERED, types)

    def test_register_component_when_stopped_raises_error(self) -> None:
        self.rt.stop()
        with self.assertRaises(RuntimeNotRunningError):
            self.rt.register_component("bus", "EventBus")

    def test_register_duplicate_component_raises_error(self) -> None:
        self.rt.register_component("bus", "EventBus")
        with self.assertRaises(ComponentAlreadyRegisteredError):
            self.rt.register_component("bus", "EventBus")

    def test_deregister_component_returns_record(self) -> None:
        self.rt.register_component("bus", "EventBus")
        record = self.rt.deregister_component("bus")
        self.assertEqual(record.name, "bus")

    def test_deregister_component_emits_event(self) -> None:
        self.rt.register_component("bus", "EventBus")
        self.rt.deregister_component("bus")
        types = [e.event_type for e in self.rt.get_events()]
        self.assertIn(RuntimeEventType.COMPONENT_DEREGISTERED, types)

    def test_deregister_component_when_stopped_raises_error(self) -> None:
        self.rt.register_component("bus", "EventBus")
        self.rt.stop()
        with self.assertRaises(RuntimeNotRunningError):
            self.rt.deregister_component("bus")

    def test_deregister_unknown_component_raises_error(self) -> None:
        with self.assertRaises(ComponentNotFoundError):
            self.rt.deregister_component("nonexistent")

    def test_register_component_with_metadata(self) -> None:
        record = self.rt.register_component(
            "bus", "EventBus", metadata={"version": "1.0"}
        )
        self.assertEqual(record.metadata, {"version": "1.0"})


# ---------------------------------------------------------------------------
# TestCompanyRuntimeObservation
# ---------------------------------------------------------------------------

class TestCompanyRuntimeObservation(unittest.TestCase):

    def setUp(self) -> None:
        self.rt = CompanyRuntime()

    def test_get_state_returns_runtime_state_instance(self) -> None:
        self.assertIsInstance(self.rt.get_state(), RuntimeState)

    def test_get_state_reflects_stopped_before_start(self) -> None:
        self.assertEqual(self.rt.get_state().status, RuntimeStatus.STOPPED)

    def test_get_state_is_snapshot_not_live(self) -> None:
        snapshot = self.rt.get_state()
        self.rt.start()
        self.assertEqual(snapshot.status, RuntimeStatus.STOPPED)

    def test_get_uptime_is_none_when_stopped(self) -> None:
        self.assertIsNone(self.rt.get_uptime())

    def test_get_uptime_is_positive_float_when_running(self) -> None:
        self.rt.start()
        uptime = self.rt.get_uptime()
        self.assertIsNotNone(uptime)
        self.assertGreaterEqual(uptime, 0.0)

    def test_get_uptime_is_none_after_stop(self) -> None:
        self.rt.start()
        self.rt.stop()
        self.assertIsNone(self.rt.get_uptime())

    def test_get_health_contains_required_keys(self) -> None:
        self.rt.start()
        health = self.rt.get_health()
        for key in ("status", "uptime_seconds", "component_count", "event_count", "components"):
            self.assertIn(key, health)

    def test_get_health_status_matches_current_state(self) -> None:
        self.rt.start()
        health = self.rt.get_health()
        self.assertEqual(health["status"], "RUNNING")

    def test_get_health_component_count_is_accurate(self) -> None:
        self.rt.start()
        self.rt.register_component("bus", "EventBus")
        self.rt.register_component("memory", "MemoryEngine")
        health = self.rt.get_health()
        self.assertEqual(health["component_count"], 2)

    def test_get_health_records_health_check_event(self) -> None:
        self.rt.start()
        count_before = len(self.rt.get_events())
        self.rt.get_health()
        count_after = len(self.rt.get_events())
        self.assertEqual(count_after, count_before + 1)
        last_event = self.rt.get_events()[-1]
        self.assertEqual(last_event.event_type, RuntimeEventType.HEALTH_CHECK)

    def test_get_health_components_list_structure(self) -> None:
        self.rt.start()
        self.rt.register_component("bus", "EventBus")
        health = self.rt.get_health()
        self.assertEqual(len(health["components"]), 1)
        comp = health["components"][0]
        self.assertIn("name", comp)
        self.assertIn("type", comp)
        self.assertIn("status", comp)

    def test_get_health_works_when_stopped(self) -> None:
        health = self.rt.get_health()
        self.assertEqual(health["status"], "STOPPED")
        self.assertIsNone(health["uptime_seconds"])

    def test_get_events_empty_before_any_action(self) -> None:
        self.assertEqual(self.rt.get_events(), [])

    def test_get_events_returns_copy(self) -> None:
        self.rt.start()
        copy = self.rt.get_events()
        copy.clear()
        self.assertGreater(len(self.rt.get_events()), 0)


# ---------------------------------------------------------------------------
# TestCompanyRuntimeBroadcast
# ---------------------------------------------------------------------------

class TestCompanyRuntimeBroadcast(unittest.TestCase):

    def setUp(self) -> None:
        self.rt = _started_runtime()

    def test_broadcast_event_returns_runtime_event(self) -> None:
        event = self.rt.broadcast_event(RuntimeEventType.HEALTH_CHECK)
        self.assertIsInstance(event, RuntimeEvent)

    def test_broadcast_event_appears_in_log(self) -> None:
        self.rt.broadcast_event(RuntimeEventType.HEALTH_CHECK, {"source": "test"})
        events = self.rt.get_events()
        types = [e.event_type for e in events]
        self.assertIn(RuntimeEventType.HEALTH_CHECK, types)

    def test_broadcast_event_stores_payload(self) -> None:
        payload = {"source": "test", "detail": "ok"}
        event = self.rt.broadcast_event(RuntimeEventType.HEALTH_CHECK, payload)
        self.assertEqual(event.payload, payload)

    def test_broadcast_event_none_payload_becomes_empty_dict(self) -> None:
        event = self.rt.broadcast_event(RuntimeEventType.HEALTH_CHECK, None)
        self.assertEqual(event.payload, {})

    def test_broadcast_event_when_stopped_raises_error(self) -> None:
        self.rt.stop()
        with self.assertRaises(RuntimeNotRunningError):
            self.rt.broadcast_event(RuntimeEventType.HEALTH_CHECK)

    def test_broadcast_event_has_unique_id(self) -> None:
        e1 = self.rt.broadcast_event(RuntimeEventType.HEALTH_CHECK)
        e2 = self.rt.broadcast_event(RuntimeEventType.HEALTH_CHECK)
        self.assertNotEqual(e1.id, e2.id)

    def test_broadcast_event_has_recent_timestamp(self) -> None:
        before = datetime.now(timezone.utc)
        event = self.rt.broadcast_event(RuntimeEventType.HEALTH_CHECK)
        after = datetime.now(timezone.utc)
        self.assertGreaterEqual(event.timestamp, before)
        self.assertLessEqual(event.timestamp, after)


# ---------------------------------------------------------------------------
# TestIntegrationScenarios
# ---------------------------------------------------------------------------

class TestIntegrationScenarios(unittest.TestCase):

    def test_full_lifecycle_start_register_stop(self) -> None:
        rt = CompanyRuntime()

        rt.start()
        self.assertEqual(rt.get_state().status, RuntimeStatus.RUNNING)

        rt.register_component("event-bus", "EventBus")
        rt.register_component("memory", "MemoryEngine")
        health = rt.get_health()
        self.assertEqual(health["component_count"], 2)

        rt.stop()
        self.assertEqual(rt.get_state().status, RuntimeStatus.STOPPED)

        state = rt.get_state()
        self.assertIsNotNone(state.started_at)
        self.assertIsNotNone(state.stopped_at)
        self.assertGreater(state.stopped_at, state.started_at)

    def test_event_log_accumulates_across_full_session(self) -> None:
        rt = CompanyRuntime()

        rt.start()
        rt.register_component("bus", "EventBus")
        rt.broadcast_event(RuntimeEventType.HEALTH_CHECK)
        rt.deregister_component("bus")
        rt.stop()

        events = rt.get_events()
        types = [e.event_type for e in events]
        self.assertIn(RuntimeEventType.RUNTIME_STARTED, types)
        self.assertIn(RuntimeEventType.COMPONENT_REGISTERED, types)
        self.assertIn(RuntimeEventType.HEALTH_CHECK, types)
        self.assertIn(RuntimeEventType.COMPONENT_DEREGISTERED, types)
        self.assertIn(RuntimeEventType.RUNTIME_STOPPED, types)

    def test_restart_resets_uptime_clock(self) -> None:
        rt = CompanyRuntime()
        rt.start()
        first_start = rt.get_state().started_at
        rt.stop()
        rt.start()
        second_start = rt.get_state().started_at
        self.assertGreaterEqual(second_start, first_start)

    def test_multiple_independent_runtimes_do_not_share_state(self) -> None:
        rt1 = CompanyRuntime()
        rt2 = CompanyRuntime()

        rt1.start()
        rt1.register_component("bus", "EventBus")

        self.assertEqual(rt1.get_state().status, RuntimeStatus.RUNNING)
        self.assertEqual(rt2.get_state().status, RuntimeStatus.STOPPED)
        self.assertEqual(rt2.get_events(), [])

    def test_registry_preserved_after_stop(self) -> None:
        rt = CompanyRuntime()
        rt.start()
        rt.register_component("bus", "EventBus")
        rt.stop()

        health = rt.get_health()
        self.assertEqual(health["component_count"], 1)
        self.assertEqual(health["components"][0]["name"], "bus")


if __name__ == "__main__":
    unittest.main()
