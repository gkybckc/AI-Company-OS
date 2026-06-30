"""
Agent Runtime — the execution engine for a single employee's sessions.

AgentRuntime manages the complete lifecycle of RuntimeSession objects for
one employee. It is the authoritative enforcer of the agent state machine:
only state transitions defined in AGENT_RUNTIME_TRANSITIONS are allowed,
and every action is recorded as a RuntimeEvent in the active session.

One AgentRuntime instance maps to one employee (identified by employee_id).
An employee may accumulate many sessions over their lifetime; all sessions
are retained in the runtime's history and can be retrieved by ID.

Rules (enforced here, not by callers):
  - Only one session may be active (non-terminal) at a time.
  - All state transitions must be valid per AGENT_RUNTIME_TRANSITIONS.
  - Terminal sessions (FINISHED, FAILED) cannot be further modified.
  - Progress must be in [0.0, 1.0].
  - Every mutation records an event on the active session.

This module does NOT: execute tasks, call LLMs, access APIs, communicate
externally, implement Discussion, Memory, or Approval protocols. It provides
the deterministic runtime scaffolding that those future layers will drive.

Architecture reference: §2.2 Agent Runtime, §3 Layer 4 (Agent Layer),
§5 Agent Lifecycle, §6 Communication Model.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from core.runtime_context import RuntimeContext
from core.runtime_result import RuntimeResult
from core.runtime_session import RuntimeEvent, RuntimeEventType, RuntimeSession
from core.runtime_state import AGENT_RUNTIME_TRANSITIONS, AgentRuntimeState


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

class AgentRuntimeError(Exception):
    """Base class for all Agent Runtime errors."""


class NoActiveSessionError(AgentRuntimeError):
    """
    Raised when an operation requires an active session but none exists.

    Call start_session() before calling change_state(), attach_context(),
    update_progress(), finish(), or fail().
    """


class SessionAlreadyActiveError(AgentRuntimeError):
    """
    Raised when start_session() is called while a non-terminal session exists.

    Stop or finish the current session before starting a new one.
    """


class IllegalStateTransitionError(AgentRuntimeError):
    """
    Raised when change_state() is called with an invalid target state.

    The transition (from_state → to_state) is not present in the
    AGENT_RUNTIME_TRANSITIONS map. Only transitions in the map are allowed.

    The error message includes both states to aid debugging.
    """


class InvalidProgressError(AgentRuntimeError):
    """
    Raised when update_progress() receives a value outside [0.0, 1.0].

    Progress is a fraction of task completion. Values below 0.0 or above
    1.0 are programming errors in the calling code.
    """


class SessionAlreadyTerminalError(AgentRuntimeError):
    """
    Raised when a mutation is attempted on a terminal session.

    Terminal sessions (FINISHED or FAILED) are immutable historical records.
    No further state changes, context updates, or progress updates are
    permitted on a terminal session.
    """


# ---------------------------------------------------------------------------
# AgentRuntime
# ---------------------------------------------------------------------------

class AgentRuntime:
    """
    Execution engine for a single employee's agent sessions.

    Manages the creation, state-machine enforcement, and termination of
    RuntimeSession objects. Every mutation is recorded as a RuntimeEvent
    so the full history of each session is observable and auditable.

    Usage example (normal task flow):
        runtime = AgentRuntime(employee_id="emp-001")
        session = runtime.start_session(project_id="proj-1", task_id="task-42")
        runtime.change_state(AgentRuntimeState.WAITING_TASK)
        runtime.change_state(AgentRuntimeState.TASK_RECEIVED)
        runtime.change_state(AgentRuntimeState.ANALYZING)
        runtime.change_state(AgentRuntimeState.PLANNING)
        runtime.change_state(AgentRuntimeState.WORKING)
        runtime.update_progress(0.5)
        runtime.change_state(AgentRuntimeState.SELF_REVIEW)
        runtime.update_progress(1.0)
        runtime.change_state(AgentRuntimeState.WAITING_APPROVAL)
        result = RuntimeResult(success=True, summary="Task complete.")
        runtime.finish(result)

    Attributes:
        employee_id: The ID of the Employee this runtime belongs to. Set
            at construction and does not change.
    """

    def __init__(self, employee_id: str) -> None:
        """
        Create a new AgentRuntime for the given employee.

        Args:
            employee_id: The WorkforceRegistry ID of the employee whose
                runtime this instance manages.
        """
        self._employee_id: str = employee_id
        self._sessions: Dict[str, RuntimeSession] = {}
        self._current_session_id: Optional[str] = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def employee_id(self) -> str:
        """Return the employee ID this runtime is bound to."""
        return self._employee_id

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def start_session(
        self,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> RuntimeSession:
        """
        Create and activate a new runtime session.

        The session is created in CREATED state and immediately advanced
        to READY — CREATED is an internal initialization state and is
        never the resting state observed by callers.

        Args:
            project_id: Optional identifier of the project this session
                will work on. May be set later via attach_context().
            task_id: Optional identifier of the task this session will
                execute. May be set later via attach_context().

        Returns:
            The new RuntimeSession in READY state, recorded as the
            active session.

        Raises:
            SessionAlreadyActiveError: If a non-terminal session is
                already active. Stop or finish the current session first.
        """
        if self._current_session_id is not None:
            active = self._sessions[self._current_session_id]
            if active.is_active():
                raise SessionAlreadyActiveError(
                    f"Employee '{self._employee_id}' already has an active session "
                    f"'{self._current_session_id}' in state "
                    f"'{active.current_state}'. Stop or finish it before starting "
                    f"a new one."
                )

        now = datetime.now(timezone.utc)
        session_id = str(uuid4())

        session = RuntimeSession(
            session_id=session_id,
            employee_id=self._employee_id,
            project_id=project_id,
            task_id=task_id,
            current_state=AgentRuntimeState.CREATED,
            progress=0.0,
            started_at=now,
            finished_at=None,
            events=[],
        )

        session.events.append(RuntimeEvent(
            event_id=str(uuid4()),
            event_type=RuntimeEventType.SESSION_STARTED,
            timestamp=now,
            from_state=None,
            to_state=AgentRuntimeState.CREATED,
            details={
                "employee_id": self._employee_id,
                "project_id": project_id,
                "task_id": task_id,
            },
        ))

        self._sessions[session_id] = session
        self._current_session_id = session_id

        # Advance to READY immediately — CREATED is transient.
        self._transition(session, AgentRuntimeState.READY)

        return session

    def stop_session(self) -> RuntimeSession:
        """
        Force-stop the current active session.

        If the session is non-terminal, it is transitioned to FAILED with
        a "session stopped" reason and finished_at is recorded. If the
        session is already terminal, it is simply deactivated as the
        current session (it remains accessible via get_session()).

        After stop_session() returns, current_session() will return None.

        Returns:
            The stopped (now terminal) RuntimeSession.

        Raises:
            NoActiveSessionError: If there is no current session to stop.
        """
        session = self._require_active_session()

        if session.is_active():
            self._fail_session(session, "Session stopped externally.")

        session.events.append(RuntimeEvent(
            event_id=str(uuid4()),
            event_type=RuntimeEventType.SESSION_STOPPED,
            timestamp=datetime.now(timezone.utc),
            from_state=None,
            to_state=session.current_state,
            details={"reason": "stop_session() called"},
        ))

        self._current_session_id = None
        return session

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    def change_state(
        self,
        new_state: AgentRuntimeState,
        details: Optional[Dict[str, Any]] = None,
    ) -> RuntimeSession:
        """
        Transition the active session to a new state.

        The transition is validated against AGENT_RUNTIME_TRANSITIONS before
        any change is made. On success, a STATE_CHANGED event is appended to
        the session's event log.

        Args:
            new_state: The target AgentRuntimeState. Must be reachable from
                the session's current state per the transition map.
            details: Optional dictionary of metadata to record in the event.

        Returns:
            The modified RuntimeSession (same object, mutated in place).

        Raises:
            NoActiveSessionError: If there is no active session.
            SessionAlreadyTerminalError: If the current session is already
                in a terminal state (FINISHED or FAILED).
            IllegalStateTransitionError: If the transition from the current
                state to new_state is not permitted by the state machine.
        """
        session = self._require_active_session()
        self._require_not_terminal(session)
        self._transition(session, new_state, details)
        return session

    def attach_context(self, context: RuntimeContext) -> RuntimeSession:
        """
        Attach a RuntimeContext to the active session.

        Replaces any previously attached context. Records a CONTEXT_ATTACHED
        event. The previous context is not archived on the session object
        (it is accessible only through the event log's history).

        Args:
            context: The RuntimeContext to attach.

        Returns:
            The modified RuntimeSession.

        Raises:
            NoActiveSessionError: If there is no active session.
            SessionAlreadyTerminalError: If the session is terminal.
        """
        session = self._require_active_session()
        self._require_not_terminal(session)

        previous_task = session.context.current_task if session.context else None
        session.context = context

        session.events.append(RuntimeEvent(
            event_id=str(uuid4()),
            event_type=RuntimeEventType.CONTEXT_ATTACHED,
            timestamp=datetime.now(timezone.utc),
            from_state=None,
            to_state=None,
            details={
                "task": context.current_task,
                "project": context.project,
                "department": str(context.department) if context.department else None,
                "director_id": context.director_id,
                "previous_task": previous_task,
            },
        ))

        return session

    def update_progress(self, progress: float) -> RuntimeSession:
        """
        Update the active session's progress fraction.

        Args:
            progress: Float in [0.0, 1.0]. 0.0 = no progress; 1.0 = complete.

        Returns:
            The modified RuntimeSession.

        Raises:
            NoActiveSessionError: If there is no active session.
            SessionAlreadyTerminalError: If the session is terminal.
            InvalidProgressError: If progress is outside [0.0, 1.0].
        """
        session = self._require_active_session()
        self._require_not_terminal(session)

        if not (0.0 <= progress <= 1.0):
            raise InvalidProgressError(
                f"Progress must be in [0.0, 1.0]; received {progress}."
            )

        previous = session.progress
        session.progress = progress

        session.events.append(RuntimeEvent(
            event_id=str(uuid4()),
            event_type=RuntimeEventType.PROGRESS_UPDATED,
            timestamp=datetime.now(timezone.utc),
            from_state=None,
            to_state=None,
            details={
                "previous_progress": previous,
                "new_progress": progress,
            },
        ))

        return session

    def finish(self, result: Optional[RuntimeResult] = None) -> RuntimeSession:
        """
        Transition the active session to FINISHED and attach the result.

        The transition must be valid per the state machine. Typically called
        from SELF_REVIEW, WAITING_APPROVAL, or IDLE.

        Args:
            result: Optional RuntimeResult describing what the session
                produced. If provided, stored on the session for retrieval.
                If None, the session is marked finished with no result record.

        Returns:
            The terminated RuntimeSession in FINISHED state.

        Raises:
            NoActiveSessionError: If there is no active session.
            SessionAlreadyTerminalError: If the session is already terminal.
            IllegalStateTransitionError: If the current state cannot
                transition to FINISHED per the state machine.
        """
        session = self._require_active_session()
        self._require_not_terminal(session)

        self._transition(
            session,
            AgentRuntimeState.FINISHED,
            details={"result_attached": result is not None},
        )

        session.finished_at = datetime.now(timezone.utc)
        session.result = result

        if result is not None and result.session_id is None:
            # Allow callers to omit session_id — we can patch it post-freeze
            # because frozen dataclasses are enforced at field-level; we use
            # object.__setattr__ only when session_id is genuinely absent.
            try:
                object.__setattr__(result, "session_id", session.session_id)
            except Exception:
                pass  # If already set or immutable, leave as-is.

        self._current_session_id = None
        return session

    def fail(self, reason: str = "") -> RuntimeSession:
        """
        Transition the active session to FAILED.

        FAILED is reachable from any non-terminal state — failure can occur
        at any phase of execution. Records the reason in the transition event.

        After fail() returns, current_session() will return None.

        Args:
            reason: Human-readable description of why the session failed.
                Stored in the STATE_CHANGED event's details dict.

        Returns:
            The terminated RuntimeSession in FAILED state.

        Raises:
            NoActiveSessionError: If there is no active session.
            SessionAlreadyTerminalError: If the session is already terminal.
        """
        session = self._require_active_session()
        self._require_not_terminal(session)
        self._fail_session(session, reason)
        self._current_session_id = None
        return session

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def current_state(self) -> AgentRuntimeState:
        """
        Return the current state of the active session.

        Returns:
            The AgentRuntimeState of the current session.

        Raises:
            NoActiveSessionError: If there is no active session.
        """
        return self._require_active_session().current_state

    def current_session(self) -> Optional[RuntimeSession]:
        """
        Return the currently active session, or None if no session is active.

        A session is "current" from start_session() until finish(), fail(),
        or stop_session() terminates it.

        Returns:
            The active RuntimeSession, or None.
        """
        if self._current_session_id is None:
            return None
        return self._sessions.get(self._current_session_id)

    def get_session(self, session_id: str) -> RuntimeSession:
        """
        Return a session by ID.

        All sessions — including historical terminated ones — are accessible.

        Args:
            session_id: The session_id of the session to retrieve.

        Returns:
            The RuntimeSession with the given ID.

        Raises:
            KeyError: If no session with this ID exists in this runtime.
        """
        try:
            return self._sessions[session_id]
        except KeyError:
            raise KeyError(
                f"No session '{session_id}' found in runtime for "
                f"employee '{self._employee_id}'."
            )

    def all_sessions(self) -> List[RuntimeSession]:
        """
        Return all sessions for this employee, in creation order.

        Returns a shallow copy of the internal list to prevent external
        mutation of the registry structure.

        Returns:
            List of RuntimeSession objects (active and terminated).
        """
        return list(self._sessions.values())

    def session_count(self) -> int:
        """Return the total number of sessions (active and terminated)."""
        return len(self._sessions)

    def has_active_session(self) -> bool:
        """Return True if a non-terminal session is currently active."""
        if self._current_session_id is None:
            return False
        session = self._sessions.get(self._current_session_id)
        return session is not None and session.is_active()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_active_session(self) -> RuntimeSession:
        """
        Return the current session or raise NoActiveSessionError.

        Raises:
            NoActiveSessionError: If _current_session_id is None or the
                session has already been deactivated.
        """
        if self._current_session_id is None:
            raise NoActiveSessionError(
                f"Employee '{self._employee_id}' has no active session. "
                f"Call start_session() first."
            )
        return self._sessions[self._current_session_id]

    def _require_not_terminal(self, session: RuntimeSession) -> None:
        """
        Raise SessionAlreadyTerminalError if the session is terminal.

        Args:
            session: The session to check.

        Raises:
            SessionAlreadyTerminalError: If current_state is FINISHED or FAILED.
        """
        if session.current_state.is_terminal():
            raise SessionAlreadyTerminalError(
                f"Session '{session.session_id}' is already in terminal state "
                f"'{session.current_state}'. Terminal sessions are immutable."
            )

    def _transition(
        self,
        session: RuntimeSession,
        new_state: AgentRuntimeState,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Perform a validated state transition on session.

        Validates that (session.current_state → new_state) is in the
        transition map, then updates the session state and appends a
        STATE_CHANGED event.

        Args:
            session: The session to transition.
            new_state: The target state.
            details: Optional metadata for the event.

        Raises:
            IllegalStateTransitionError: If the transition is invalid.
        """
        from_state = session.current_state

        if not from_state.can_transition_to(new_state):
            allowed = {str(s) for s in AGENT_RUNTIME_TRANSITIONS.get(from_state, frozenset())}
            raise IllegalStateTransitionError(
                f"Illegal state transition: {from_state} → {new_state}. "
                f"Allowed from {from_state}: {allowed or 'none (terminal state)'}."
            )

        session.current_state = new_state
        session.events.append(RuntimeEvent(
            event_id=str(uuid4()),
            event_type=RuntimeEventType.STATE_CHANGED,
            timestamp=datetime.now(timezone.utc),
            from_state=from_state,
            to_state=new_state,
            details=details or {},
        ))

    def _fail_session(self, session: RuntimeSession, reason: str) -> None:
        """
        Unconditionally transition session to FAILED.

        Internal method used by both fail() and stop_session(). Records
        the reason in the event's details.

        Args:
            session: The session to fail. Must be non-terminal.
            reason: Why the session is being failed.
        """
        self._transition(
            session,
            AgentRuntimeState.FAILED,
            details={"reason": reason},
        )
        session.finished_at = datetime.now(timezone.utc)
