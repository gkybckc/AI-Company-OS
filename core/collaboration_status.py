"""
Collaboration lifecycle status taxonomy for AI Company OS.

Defines the states a CollaborationRequest passes through from creation
to termination, and the outcome codes a CollaborationResponse may carry.

The CollaborationManager is the sole authority for assigning and
transitioning request statuses. External callers observe status through
the manager's query methods; they do not set status directly.

Architecture reference: §2.6 Communication Model, §3 Layer 3 (Infrastructure),
constitution Chapter 14 (Collaboration protocols).
"""

from enum import Enum
from typing import FrozenSet


class CollaborationStatus(str, Enum):
    """
    Lifecycle states and response outcomes for collaboration requests.

    Request lifecycle states (assigned by the CollaborationManager):

    PENDING     — The request has been created and is waiting for a
                  responder to process it. This is the initial state of
                  every request. Requests remain PENDING until they are
                  responded to, cancelled, or failed.

    CANCELLED   — The request was explicitly cancelled by the requester
                  or the manager before a response was provided. No
                  response exists for a CANCELLED request. Terminal.

    Response outcome states (carried by a CollaborationResponse):

    COMPLETED   — The collaboration was resolved successfully. The
                  responder has provided the requested information,
                  approval decision, discussion outcome, or memory
                  payload. Terminal.

    REJECTED    — The target declined the request. This may occur when
                  the request is outside the target's domain, the target
                  does not have the required information, or the request
                  was rejected by the Approval Engine. Terminal.

    FAILED      — The collaboration attempt terminated due to an error in
                  processing. The response payload describes the failure.
                  Terminal.
    """

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"

    def __str__(self) -> str:
        return self.value

    def is_terminal(self) -> bool:
        """
        Return True if this status represents an end-of-lifecycle state.

        Terminal statuses cannot transition to any other status. A request
        or response in a terminal status is an immutable historical record.

        Returns:
            True for COMPLETED, CANCELLED, REJECTED, and FAILED.
        """
        return self in {
            CollaborationStatus.COMPLETED,
            CollaborationStatus.CANCELLED,
            CollaborationStatus.REJECTED,
            CollaborationStatus.FAILED,
        }

    def is_pending(self) -> bool:
        """Return True if the request is still awaiting a response."""
        return self == CollaborationStatus.PENDING

    def is_successful(self) -> bool:
        """
        Return True if the collaboration concluded with a positive outcome.

        COMPLETED is the only "success" terminal state. REJECTED and FAILED
        are negative outcomes; CANCELLED is a void without an outcome.

        Returns:
            True only for COMPLETED.
        """
        return self == CollaborationStatus.COMPLETED


# ---------------------------------------------------------------------------
# Valid status sets — used by the manager for validation.
# ---------------------------------------------------------------------------

#: Statuses that may appear on a CollaborationResponse.
#: A response cannot be PENDING or CANCELLED — those are request-side states.
VALID_RESPONSE_STATUSES: FrozenSet[CollaborationStatus] = frozenset({
    CollaborationStatus.COMPLETED,
    CollaborationStatus.REJECTED,
    CollaborationStatus.FAILED,
})

#: Priority range enforced by CollaborationManager.
PRIORITY_MIN: int = 1
PRIORITY_MAX: int = 5
