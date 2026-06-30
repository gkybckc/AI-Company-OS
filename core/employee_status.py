"""
Employee status lifecycle for AI Company OS.

Defines the complete set of states an employee (agent) can be in from
the moment they enter the workforce system until their final termination.
The WorkforceRegistry enforces valid transitions between these states.

Architecture reference: §2.2 Agent Runtime, §5 Agent Lifecycle,
Constitution Chapter 5 (Hierarchy and Roles).
"""

from enum import Enum


class EmployeeStatus(str, Enum):
    """
    Lifecycle states for an Employee in AI Company OS.

    State meanings and valid transitions:

    CANDIDATE   — The employee record has been created but the hire has
                  not yet been formally activated. The employee exists in
                  the registry but cannot receive tasks. This state exists
                  to support pre-hire queuing and onboarding flows.
                  Transition: → ACTIVE (via hire activation).

    ACTIVE      — The employee is fully operational and available to
                  accept assignments. This is the primary healthy state.
                  Transition: → IDLE | WORKING | WAITING | SUSPENDED | TRANSFERRED | TERMINATED.

    IDLE        — The employee is operational but currently has no task
                  assignment. Distinct from ACTIVE in that IDLE explicitly
                  signals an unoccupied agent that needs to be assigned work.
                  Transition: → WORKING | ACTIVE | SUSPENDED | TRANSFERRED | TERMINATED.

    WORKING     — The employee is actively executing a task. The Director
                  and Executive Engine can observe this state to assess
                  department throughput.
                  Transition: → IDLE | WAITING | ACTIVE | SUSPENDED.

    WAITING     — The employee has completed their portion of work and is
                  blocked on an external dependency: a peer's output, an
                  Approval Engine decision, or a Director instruction.
                  Transition: → WORKING | IDLE | ACTIVE | SUSPENDED.

    SUSPENDED   — The employee has been explicitly deactivated by the
                  Executive Engine or CEO. The employee record is retained
                  and can be reactivated. Suspension is not termination.
                  Transition: → IDLE (via reactivate()).

    TRANSFERRED — The employee has been formally moved to a new department.
                  This state marks the transition window between departments.
                  The employee cannot receive new tasks while in this state.
                  Transition: → ACTIVE | IDLE (after settling into new department).

    TERMINATED  — The employee has been permanently decommissioned. The
                  record is retained for historical reference. A terminated
                  employee cannot transition to any other state.
                  Transition: (none — this is a terminal state).
    """

    CANDIDATE = "CANDIDATE"
    ACTIVE = "ACTIVE"
    IDLE = "IDLE"
    WORKING = "WORKING"
    WAITING = "WAITING"
    SUSPENDED = "SUSPENDED"
    TRANSFERRED = "TRANSFERRED"
    TERMINATED = "TERMINATED"

    def __str__(self) -> str:
        return self.value

    def is_active_workforce(self) -> bool:
        """
        Return True if this status represents an active member of the workforce.

        Active workforce members are those who can receive assignments and
        contribute to department capacity. SUSPENDED, TERMINATED, TRANSFERRED,
        and CANDIDATE employees do not count toward active headcount.

        Returns:
            True for ACTIVE, IDLE, WORKING, and WAITING.
        """
        return self in {
            EmployeeStatus.ACTIVE,
            EmployeeStatus.IDLE,
            EmployeeStatus.WORKING,
            EmployeeStatus.WAITING,
        }

    def is_terminal(self) -> bool:
        """
        Return True if this is a terminal state (no further transitions allowed).

        Returns:
            True only for TERMINATED.
        """
        return self == EmployeeStatus.TERMINATED
