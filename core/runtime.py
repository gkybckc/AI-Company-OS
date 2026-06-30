"""
Company Runtime for AI Company OS.

The CompanyRuntime is the central coordinator of the runtime infrastructure.
It governs the operational lifecycle of the company: it can be started and
stopped, accepts component registrations, broadcasts observable events,
tracks health, and exposes uptime. It knows nothing about agents, tasks, or
projects — it is the foundation on which the Coordination Layer (L5) builds.

This module corresponds to the Infrastructure Layer (L3) of the seven-layer
architecture. It is synchronous, stateful, and purely in-memory.

Architecture reference: §3 Layered Architecture (L3 Infrastructure),
§12 Failure Recovery, §13 Scalability Stage 1.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.runtime_events import RuntimeEvent, RuntimeEventType
from core.runtime_registry import (
    ComponentAlreadyRegisteredError,  # re-exported for callers
    ComponentNotFoundError,           # re-exported for callers
    ComponentRecord,
    ComponentStatus,
    RuntimeRegistry,
)
from core.runtime_state import RuntimeState, RuntimeStatus

# Silence unused-import linters — these are intentional re-exports.
__all__ = [
    "CompanyRuntime",
    "RuntimeAlreadyRunningError",
    "RuntimeNotRunningError",
    "ComponentAlreadyRegisteredError",
    "ComponentNotFoundError",
    "ComponentStatus",
]


class RuntimeAlreadyRunningError(Exception):
    """Raised when start() is called on an already-running runtime."""


class RuntimeNotRunningError(Exception):
    """Raised when an operation requires the runtime to be in RUNNING state."""


class CompanyRuntime:
    """
    Central runtime coordinator for AI Company OS.

    Manages the operational lifecycle of the company's infrastructure layer:
    component registration, runtime event broadcasting, health reporting,
    and uptime tracking. Higher-level systems (Executive Engine, Agent
    Runtime) depend on this foundation being started before they operate.

    State machine (stable observable states):
        STOPPED → RUNNING   (via start())
        RUNNING → STOPPED   (via stop())

    STARTING and STOPPING are transient states traversed synchronously
    inside start() and stop(). Callers do not observe them unless they
    inspect get_state() mid-call, which cannot happen without concurrency.

    The event log is append-only. Every lifecycle transition, component
    registration, and health check produces a durable event record that
    accumulates for the life of the runtime object.

    Attributes:
        _status: Current lifecycle status.
        _started_at: UTC timestamp of the most recent start(), or None.
        _stopped_at: UTC timestamp of the most recent stop(), or None.
        _error_message: Description of the last error, or None.
        _registry: Authoritative directory of registered components.
        _event_log: Append-only log of all runtime events.
    """

    def __init__(self) -> None:
        self._status: RuntimeStatus = RuntimeStatus.STOPPED
        self._started_at: Optional[datetime] = None
        self._stopped_at: Optional[datetime] = None
        self._error_message: Optional[str] = None
        self._registry: RuntimeRegistry = RuntimeRegistry()
        self._event_log: List[RuntimeEvent] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """
        Start the runtime, transitioning it to RUNNING state.

        Clears any previous stop timestamp and error message, records the
        start timestamp, and emits a RUNTIME_STARTED event. The runtime
        is ready to accept component registrations and broadcast events
        immediately when this method returns.

        Raises:
            RuntimeAlreadyRunningError: If the runtime is already RUNNING.
                Call stop() before calling start() again.
        """
        if self._status == RuntimeStatus.RUNNING:
            raise RuntimeAlreadyRunningError(
                "The runtime is already running. "
                "Call stop() before calling start() again."
            )

        self._status = RuntimeStatus.STARTING
        self._started_at = datetime.now(timezone.utc)
        self._stopped_at = None
        self._error_message = None

        self._status = RuntimeStatus.RUNNING
        self._record_event(
            RuntimeEventType.RUNTIME_STARTED,
            {"started_at": self._started_at.isoformat()},
        )

    def stop(self) -> None:
        """
        Stop the runtime, transitioning it to STOPPED state.

        Records the stop timestamp and emits a RUNTIME_STOPPED event before
        entering STOPPED state. Component registry and event log are preserved
        so the runtime can be inspected after shutdown.

        Raises:
            RuntimeNotRunningError: If the runtime is not in RUNNING state.
        """
        if self._status != RuntimeStatus.RUNNING:
            raise RuntimeNotRunningError(
                f"Cannot stop the runtime from state '{self._status.value}'. "
                "The runtime must be RUNNING to be stopped."
            )

        self._status = RuntimeStatus.STOPPING
        self._stopped_at = datetime.now(timezone.utc)

        self._record_event(
            RuntimeEventType.RUNTIME_STOPPED,
            {"stopped_at": self._stopped_at.isoformat()},
        )
        self._status = RuntimeStatus.STOPPED

    # ------------------------------------------------------------------
    # Component management
    # ------------------------------------------------------------------

    def register_component(
        self,
        name: str,
        component_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ComponentRecord:
        """
        Register a component with the runtime.

        The runtime must be RUNNING. Each component must have a unique name.
        Emits a COMPONENT_REGISTERED event on success.

        Args:
            name: Unique identifier for this component within the runtime.
            component_type: Human-readable type label (e.g. "EventBus").
            metadata: Optional key-value context stored on the record.

        Returns:
            The newly created ComponentRecord.

        Raises:
            RuntimeNotRunningError: If the runtime is not RUNNING.
            ComponentAlreadyRegisteredError: If name is already registered.
        """
        self._require_running("register_component")
        record = self._registry.register(
            name=name,
            component_type=component_type,
            metadata=metadata,
        )
        self._record_event(
            RuntimeEventType.COMPONENT_REGISTERED,
            {"name": name, "component_type": component_type},
        )
        return record

    def deregister_component(self, name: str) -> ComponentRecord:
        """
        Remove a component from the runtime registry.

        The runtime must be RUNNING. Emits a COMPONENT_DEREGISTERED event
        on success.

        Args:
            name: Name of the component to remove.

        Returns:
            The ComponentRecord that was removed.

        Raises:
            RuntimeNotRunningError: If the runtime is not RUNNING.
            ComponentNotFoundError: If name is not registered.
        """
        self._require_running("deregister_component")
        record = self._registry.deregister(name)
        self._record_event(
            RuntimeEventType.COMPONENT_DEREGISTERED,
            {"name": name, "component_type": record.component_type},
        )
        return record

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------

    def get_state(self) -> RuntimeState:
        """
        Return a frozen point-in-time snapshot of the runtime's lifecycle state.

        The returned RuntimeState does not update as the runtime continues
        to operate; callers who need current state must call get_state() again.

        Returns:
            A frozen RuntimeState reflecting the state at call time.
        """
        return RuntimeState(
            status=self._status,
            started_at=self._started_at,
            stopped_at=self._stopped_at,
            error_message=self._error_message,
        )

    def get_uptime(self) -> Optional[float]:
        """
        Return the elapsed seconds since the runtime was started.

        Uptime is measured from started_at to the current wall-clock time.
        Returns None when the runtime is not in RUNNING state or has never
        been started.

        Returns:
            Elapsed seconds as a float, or None if not running.
        """
        if self._status != RuntimeStatus.RUNNING or self._started_at is None:
            return None
        return (datetime.now(timezone.utc) - self._started_at).total_seconds()

    def get_health(self) -> Dict[str, Any]:
        """
        Return a structured health report and record a HEALTH_CHECK event.

        Summarises the runtime status, uptime, and all registered components.
        A HEALTH_CHECK event is appended to the event log on every call,
        providing an observable audit trail of health inspections.

        This method works in any runtime state; it does not require RUNNING.

        Returns:
            A dictionary with the following keys:

            status (str): Current RuntimeStatus value.
            uptime_seconds (Optional[float]): Seconds since start, or None.
            component_count (int): Number of registered components.
            event_count (int): Number of events in the log (including this
                HEALTH_CHECK event).
            components (List[Dict]): Per-component summary, each with keys
                'name' (str), 'type' (str), and 'status' (str).
        """
        uptime = self.get_uptime()
        components = [
            {
                "name": record.name,
                "type": record.component_type,
                "status": record.status.value,
            }
            for record in self._registry.list_all()
        ]
        self._record_event(
            RuntimeEventType.HEALTH_CHECK,
            {"status": self._status.value},
        )
        return {
            "status": self._status.value,
            "uptime_seconds": uptime,
            "component_count": self._registry.count(),
            "event_count": len(self._event_log),
            "components": components,
        }

    def get_events(self) -> List[RuntimeEvent]:
        """
        Return all runtime events in the order they were recorded.

        Returns a shallow copy of the event log. Mutating the returned list
        does not affect the internal log; individual RuntimeEvent objects are
        frozen and cannot be modified.

        Returns:
            Ordered list of RuntimeEvent instances. Empty if none exist yet.
        """
        return list(self._event_log)

    def broadcast_event(
        self,
        event_type: RuntimeEventType,
        payload: Optional[Dict[str, Any]] = None,
    ) -> RuntimeEvent:
        """
        Broadcast a runtime event from an external caller.

        Public API for components and higher-level systems to emit
        runtime-layer events. The runtime must be RUNNING; events cannot
        be broadcast when the runtime is stopped or starting.

        Args:
            event_type: The category of event to emit.
            payload: Optional key-value context. Defaults to an empty dict.

        Returns:
            The RuntimeEvent that was created and appended to the log.

        Raises:
            RuntimeNotRunningError: If the runtime is not in RUNNING state.
        """
        self._require_running("broadcast_event")
        return self._record_event(event_type, payload)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _require_running(self, operation: str) -> None:
        """
        Assert the runtime is RUNNING or raise RuntimeNotRunningError.

        Args:
            operation: Calling method name, included in the error message.

        Raises:
            RuntimeNotRunningError: If the current status is not RUNNING.
        """
        if self._status != RuntimeStatus.RUNNING:
            raise RuntimeNotRunningError(
                f"'{operation}' requires the runtime to be RUNNING. "
                f"Current state: '{self._status.value}'. Call start() first."
            )

    def _record_event(
        self,
        event_type: RuntimeEventType,
        payload: Optional[Dict[str, Any]] = None,
    ) -> RuntimeEvent:
        """
        Create a RuntimeEvent, append it to the log, and return it.

        Unlike broadcast_event(), this method does not check runtime state.
        It is used for lifecycle events (RUNTIME_STARTED, RUNTIME_STOPPED)
        that must be recorded during state transitions.

        Args:
            event_type: Category of the event.
            payload: Key-value context. None is normalised to an empty dict.

        Returns:
            The newly created and logged RuntimeEvent.
        """
        event = RuntimeEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            payload=payload if payload is not None else {},
        )
        self._event_log.append(event)
        return event
