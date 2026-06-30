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
from typing import Optional


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
