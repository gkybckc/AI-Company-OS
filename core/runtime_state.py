"""
Runtime state model for AI Company OS.

Defines the lifecycle state machine for the CompanyRuntime and the
immutable RuntimeState snapshot that consumers receive from
CompanyRuntime.get_state(). The state machine is described in the
transition table on RuntimeStatus; the dataclass captures a frozen
point-in-time view, not a live reference.

Architecture reference: §3 Layered Architecture (Infrastructure Layer, L3).
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, FrozenSet, Optional


class RuntimeStatus(str, Enum):
    """
    Valid lifecycle states for the CompanyRuntime.

    Transitions enforced by CompanyRuntime:
        STOPPED  → STARTING  (start() called)
        STARTING → RUNNING   (startup complete)
        RUNNING  → STOPPING  (stop() called)
        STOPPING → STOPPED   (shutdown complete)
        Any      → ERROR     (unhandled failure — reserved for future use)

    STARTING and STOPPING are transient; they are traversed synchronously
    inside start() and stop() respectively. External callers will only
    observe STOPPED, RUNNING, or ERROR as stable states.
    """

    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    ERROR = "ERROR"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class RuntimeState:
    """
    Immutable point-in-time snapshot of the CompanyRuntime's lifecycle state.

    Returned by CompanyRuntime.get_state(). This is a value object; it
    reflects the state at the moment of the call and does not update as
    the runtime continues to operate. Callers who need current state must
    call get_state() again.

    Attributes:
        status: The runtime's lifecycle status at snapshot time.
        started_at: UTC timestamp of the most recent start() call.
            None if the runtime has never been started.
        stopped_at: UTC timestamp of the most recent stop() call.
            None while the runtime is running or if it was never stopped.
        error_message: Human-readable description of the failure when
            status is ERROR. None in all other states.
    """

    status: RuntimeStatus
    started_at: Optional[datetime]
    stopped_at: Optional[datetime]
    error_message: Optional[str]


# ---------------------------------------------------------------------------
# Agent Runtime state machine — Sprint 7
# ---------------------------------------------------------------------------

class AgentRuntimeState(str, Enum):
    """
    Lifecycle states for an individual Agent Runtime session.

    Each value represents a discrete, observable phase in the agent's
    execution cycle. The AgentRuntime enforces that only transitions listed
    in AGENT_RUNTIME_TRANSITIONS are permitted; all others raise
    IllegalStateTransitionError.

    Transition topology (forward path):
        CREATED → READY → WAITING_TASK → TASK_RECEIVED
          → ANALYZING → PLANNING → WORKING → SELF_REVIEW
            → WAITING_DISCUSSION ──┐
            → WAITING_MEMORY     ──┼→ WORKING (rework) | WAITING_APPROVAL
            → WAITING_APPROVAL   ──┘
              → FINISHED (approved) | WORKING (rejected, rework)
            → FINISHED (direct, no external dependency)
        READY / WAITING_TASK ↔ IDLE
        Any non-terminal state → FAILED

    CREATED         — Session object created; not yet initialised for work.
    READY           — Session initialised; agent online, no task assigned.
    WAITING_TASK    — Actively waiting for a task from the Executive Engine.
    TASK_RECEIVED   — Task delivered; about to begin analysis.
    ANALYZING       — Parsing task requirements, scope, and constraints.
    PLANNING        — Constructing an execution plan and output strategy.
    WORKING         — Actively producing output according to the plan.
    SELF_REVIEW     — Reviewing draft output against acceptance criteria.
    WAITING_DISCUSSION — Blocked on a Discussion Engine response from peers.
    WAITING_MEMORY  — Blocked on a Memory Engine read or write.
    WAITING_APPROVAL — Output submitted; blocked on Approval Engine decision.
    FINISHED        — Session completed successfully. Terminal.
    FAILED          — Session terminated with failure. Terminal.
    IDLE            — Session active but no current task; between assignments.
    """

    CREATED = "CREATED"
    READY = "READY"
    WAITING_TASK = "WAITING_TASK"
    TASK_RECEIVED = "TASK_RECEIVED"
    ANALYZING = "ANALYZING"
    PLANNING = "PLANNING"
    WORKING = "WORKING"
    SELF_REVIEW = "SELF_REVIEW"
    WAITING_DISCUSSION = "WAITING_DISCUSSION"
    WAITING_MEMORY = "WAITING_MEMORY"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    FINISHED = "FINISHED"
    FAILED = "FAILED"
    IDLE = "IDLE"

    def __str__(self) -> str:
        return self.value

    def is_terminal(self) -> bool:
        """Return True if this is a terminal state (FINISHED or FAILED)."""
        return self in {AgentRuntimeState.FINISHED, AgentRuntimeState.FAILED}

    def is_waiting(self) -> bool:
        """Return True if the session is blocked on an external response."""
        return self in {
            AgentRuntimeState.WAITING_TASK,
            AgentRuntimeState.WAITING_DISCUSSION,
            AgentRuntimeState.WAITING_MEMORY,
            AgentRuntimeState.WAITING_APPROVAL,
        }

    def is_active_processing(self) -> bool:
        """Return True if the session is actively producing output."""
        return self in {
            AgentRuntimeState.ANALYZING,
            AgentRuntimeState.PLANNING,
            AgentRuntimeState.WORKING,
            AgentRuntimeState.SELF_REVIEW,
        }

    def allowed_next_states(self) -> FrozenSet["AgentRuntimeState"]:
        """Return the frozenset of states this state may legally transition to."""
        return AGENT_RUNTIME_TRANSITIONS.get(self, frozenset())

    def can_transition_to(self, target: "AgentRuntimeState") -> bool:
        """Return True if transitioning to target is valid per the state machine."""
        return target in self.allowed_next_states()


# ---------------------------------------------------------------------------
# Transition map — the single source of truth for the agent state machine.
# FAILED is reachable from every non-terminal state (failure can occur
# at any phase). Each entry lists only the states reachable from the key.
# ---------------------------------------------------------------------------

AGENT_RUNTIME_TRANSITIONS: Dict[AgentRuntimeState, FrozenSet[AgentRuntimeState]] = {
    AgentRuntimeState.CREATED: frozenset({
        AgentRuntimeState.READY,
        AgentRuntimeState.FAILED,
    }),
    AgentRuntimeState.READY: frozenset({
        AgentRuntimeState.WAITING_TASK,
        AgentRuntimeState.IDLE,
        AgentRuntimeState.FAILED,
    }),
    AgentRuntimeState.WAITING_TASK: frozenset({
        AgentRuntimeState.TASK_RECEIVED,
        AgentRuntimeState.IDLE,
        AgentRuntimeState.FAILED,
    }),
    AgentRuntimeState.TASK_RECEIVED: frozenset({
        AgentRuntimeState.ANALYZING,
        AgentRuntimeState.FAILED,
    }),
    AgentRuntimeState.ANALYZING: frozenset({
        AgentRuntimeState.PLANNING,
        AgentRuntimeState.FAILED,
    }),
    AgentRuntimeState.PLANNING: frozenset({
        AgentRuntimeState.WORKING,
        AgentRuntimeState.FAILED,
    }),
    AgentRuntimeState.WORKING: frozenset({
        AgentRuntimeState.SELF_REVIEW,
        AgentRuntimeState.FAILED,
    }),
    AgentRuntimeState.SELF_REVIEW: frozenset({
        AgentRuntimeState.WAITING_DISCUSSION,
        AgentRuntimeState.WAITING_MEMORY,
        AgentRuntimeState.WAITING_APPROVAL,
        AgentRuntimeState.FINISHED,
        AgentRuntimeState.FAILED,
    }),
    AgentRuntimeState.WAITING_DISCUSSION: frozenset({
        AgentRuntimeState.WORKING,
        AgentRuntimeState.WAITING_APPROVAL,
        AgentRuntimeState.FAILED,
    }),
    AgentRuntimeState.WAITING_MEMORY: frozenset({
        AgentRuntimeState.WORKING,
        AgentRuntimeState.WAITING_APPROVAL,
        AgentRuntimeState.FAILED,
    }),
    AgentRuntimeState.WAITING_APPROVAL: frozenset({
        AgentRuntimeState.FINISHED,
        AgentRuntimeState.WORKING,
        AgentRuntimeState.FAILED,
    }),
    AgentRuntimeState.IDLE: frozenset({
        AgentRuntimeState.WAITING_TASK,
        AgentRuntimeState.FINISHED,
        AgentRuntimeState.FAILED,
    }),
    AgentRuntimeState.FINISHED: frozenset(),
    AgentRuntimeState.FAILED: frozenset(),
}
