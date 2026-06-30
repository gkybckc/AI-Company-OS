"""
Department and Director status enumerations for AI Company OS.

Defines the lifecycle state machines for both departments and their
directors. These states are the primary signals the Executive Engine
uses when deciding whether to route new work to a department.

Architecture reference: §3 Layer 4 (Agent Layer), §12 Failure Recovery,
§5 Agent Lifecycle.
"""

from enum import Enum


class DepartmentStatus(str, Enum):
    """
    Operational lifecycle states for a Department.

    State meanings and transitions:

    READY      — The department is staffed, has capacity, and is waiting
                 for work. The Executive Engine may assign projects here.

    WORKING    — The department has active projects or tasks in progress.
                 It may still accept additional work if capacity allows.

    WAITING    — The department has submitted output and is waiting for
                 a decision from the Approval Engine or for a dependency
                 from another department. It is not idle — it is blocked
                 on a response, not on capacity.

    BLOCKED    — The department cannot proceed because a hard dependency
                 is unresolved. No new work should be routed here until
                 the block is cleared by the Executive Engine.

    OVERLOADED — The department's workload exceeds its capacity. New
                 work must not be routed here. The Executive Engine must
                 either wait, scale the department, or redistribute work.

    OFFLINE    — The department is inactive. No director or agents are
                 operational. The department exists in the registry but
                 cannot receive or process any work.
    """

    READY = "READY"
    WORKING = "WORKING"
    WAITING = "WAITING"
    BLOCKED = "BLOCKED"
    OVERLOADED = "OVERLOADED"
    OFFLINE = "OFFLINE"

    def __str__(self) -> str:
        return self.value


class DirectorStatus(str, Enum):
    """
    Operational lifecycle states for a Department Director.

    A Director is the single point of coordination between the Executive
    Engine and the specialist agents in a department. The Director's status
    reflects whether they are available to accept and distribute work.

    ACTIVE     — The Director is operational and actively managing the
                 department's agents and tasks.

    IDLE       — The Director is operational but has no active tasks to
                 manage. The department is ready for new assignments.

    OVERLOADED — The Director has more work than they can effectively
                 coordinate. The department should not receive new major
                 assignments until the backlog is reduced.

    SUSPENDED  — The Director has been suspended by the Executive Engine
                 or CEO. The department cannot operate without a Director.
                 A replacement or resumption must be arranged.
    """

    ACTIVE = "ACTIVE"
    IDLE = "IDLE"
    OVERLOADED = "OVERLOADED"
    SUSPENDED = "SUSPENDED"

    def __str__(self) -> str:
        return self.value
