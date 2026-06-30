"""
Runtime session and session event models for the Agent Runtime.

A RuntimeSession is the live record of one execution session for an
agent. Sessions are created by AgentRuntime.start_session() and
terminated by finish() or fail(). Each agent may have many sessions
across its lifetime; the AgentRuntime tracks them all.

RuntimeEvent is the internal audit trail for a session. Every state
transition, context attachment, and progress update appends an event
to the session's events list. Events are immutable once created.

Architecture reference: §2.2 Agent Runtime, §3 Layer 4 (Agent Layer),
§2.8 Event Bus (session events are internal; they may be published to
the bus in future sprints), §5 Agent Lifecycle.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from core.runtime_context import RuntimeContext
from core.runtime_result import RuntimeResult
from core.runtime_state import AgentRuntimeState


class RuntimeEventType(str, Enum):
    """
    Event types recorded in a RuntimeSession's event log.

    Every observable action in an agent session appends one of these
    events. The events list is the authoritative history of the session.

    SESSION_STARTED     — Emitted when start_session() creates the session.
    STATE_CHANGED       — Emitted on every valid state transition via
                          change_state(), finish(), or fail().
    CONTEXT_ATTACHED    — Emitted when attach_context() updates the context.
    PROGRESS_UPDATED    — Emitted when update_progress() changes the value.
    SESSION_STOPPED     — Emitted when stop_session() forces the session to end.
    """

    SESSION_STARTED = "SESSION_STARTED"
    STATE_CHANGED = "STATE_CHANGED"
    CONTEXT_ATTACHED = "CONTEXT_ATTACHED"
    PROGRESS_UPDATED = "PROGRESS_UPDATED"
    SESSION_STOPPED = "SESSION_STOPPED"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class RuntimeEvent:
    """
    Immutable audit record for a single occurrence within a RuntimeSession.

    Appended to RuntimeSession.events by AgentRuntime on every observable
    action. Once created, events are never modified. The list as a whole
    is the complete observable history of the session.

    Attributes:
        event_id: Unique identifier for this event (UUID string).
        event_type: The category of action this event represents.
        timestamp: UTC timestamp of when the event was recorded.
        from_state: The session state before the event. Populated for
            STATE_CHANGED events. None for non-transition events.
        to_state: The session state after the event. Populated for
            STATE_CHANGED events. None for non-transition events.
        details: Arbitrary key-value pairs providing event-specific
            detail — e.g., failure reason, new progress value, or
            metadata from the attached context.
    """

    event_id: str
    event_type: RuntimeEventType
    timestamp: datetime
    from_state: Optional[AgentRuntimeState] = None
    to_state: Optional[AgentRuntimeState] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuntimeSession:
    """
    Live execution record for one agent session.

    A session begins when AgentRuntime.start_session() is called and ends
    when either finish() or fail() (or stop_session()) transitions it to a
    terminal state. The session is the unit of traceability: every task
    execution maps to exactly one session, and every action within that
    execution is recorded in the session's event log.

    One employee may accumulate many sessions across their lifetime. Sessions
    are never deleted — terminated sessions remain in the AgentRuntime's
    history and can be retrieved via get_session().

    Attributes:
        session_id: Unique identifier for this session (UUID string).
            Assigned by AgentRuntime.start_session() at creation time.
        employee_id: ID of the Employee (from WorkforceRegistry) whose
            runtime this session belongs to.
        project_id: Optional ID of the project this session is working on.
            None for sessions not associated with a tracked project.
        task_id: Optional ID of the specific task this session is executing.
            None until a task is assigned (i.e., until TASK_RECEIVED state).
        current_state: The current AgentRuntimeState of this session.
            Transitions are enforced by AgentRuntime.change_state().
        progress: Float in [0.0, 1.0] representing the agent's self-reported
            progress toward completing the current task. 0.0 at session start;
            1.0 when the task output is complete. This is advisory — the
            state machine, not progress, determines when a session is done.
        started_at: UTC timestamp of session creation.
        finished_at: UTC timestamp of when the session entered a terminal
            state (FINISHED or FAILED). None while the session is active.
        events: Ordered list of RuntimeEvent records. Append-only; the list
            grows with every observable action. Never cleared during the
            session's lifetime.
        context: The current RuntimeContext for this session. Attached via
            attach_context(); replaced on each call (old context is not
            archived here, but the CONTEXT_ATTACHED event records the change).
        result: The RuntimeResult attached at finish() time. None until the
            session reaches FINISHED state. Populated by AgentRuntime.finish().
    """

    session_id: str
    employee_id: str
    project_id: Optional[str]
    task_id: Optional[str]
    current_state: AgentRuntimeState
    progress: float
    started_at: datetime
    finished_at: Optional[datetime]
    events: List[RuntimeEvent]
    context: Optional[RuntimeContext] = None
    result: Optional[RuntimeResult] = None

    def is_active(self) -> bool:
        """Return True if the session has not yet reached a terminal state."""
        return not self.current_state.is_terminal()

    def is_finished(self) -> bool:
        """Return True if the session completed successfully."""
        return self.current_state == AgentRuntimeState.FINISHED

    def is_failed(self) -> bool:
        """Return True if the session terminated with a failure."""
        return self.current_state == AgentRuntimeState.FAILED

    def duration_seconds(self) -> Optional[float]:
        """
        Return the session's wall-clock duration in seconds.

        Returns:
            Seconds from started_at to finished_at if the session is
            terminal, or None if the session is still active.
        """
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()

    def event_count(self) -> int:
        """Return the number of events recorded in this session."""
        return len(self.events)

    def last_event(self) -> Optional[RuntimeEvent]:
        """Return the most recent event, or None if no events have been recorded."""
        return self.events[-1] if self.events else None

    def events_of_type(self, event_type: RuntimeEventType) -> List[RuntimeEvent]:
        """
        Return all events matching the given type.

        Args:
            event_type: The RuntimeEventType to filter by.

        Returns:
            List of matching events in chronological order.
        """
        return [e for e in self.events if e.event_type == event_type]

    def state_transitions(self) -> List[RuntimeEvent]:
        """Return all STATE_CHANGED events in chronological order."""
        return self.events_of_type(RuntimeEventType.STATE_CHANGED)
