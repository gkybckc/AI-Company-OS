"""
Collaboration type taxonomy for AI Company OS.

Defines the four categories of structured inter-agent collaboration
supported by the Collaboration Core. Each type represents a distinct
communication pattern with its own semantics and expected response shape.

The type is set at request creation and does not change. It is used by
the CollaborationManager to route, filter, and report on requests.

Architecture reference: §2.6 Communication Model, §3 Layer 3 (Infrastructure),
§8 Approval Flow, §7 Memory Model, constitution Chapter 14 (Collaboration).
"""

from enum import Enum


class CollaborationType(str, Enum):
    """
    The category of a CollaborationRequest.

    Each value describes what kind of inter-agent collaboration the
    requester needs:

    DISCUSSION          — The requester needs structured input from one or
                          more peer agents before it can finalize its output.
                          Typical trigger: cross-department scope, architectural
                          trade-off, or quality concern that the requester
                          cannot resolve within its own domain.
                          Future engine: Discussion Engine.

    MEMORY_LOOKUP       — The requester needs information stored in the Memory
                          Engine (long-term, shared, or project memory). The
                          target is the Memory Engine or a specific memory
                          scope owner.
                          Future engine: Memory Engine.

    APPROVAL            — The requester has produced an output that must be
                          reviewed and approved before it can be treated as
                          final. The target may be a Director, the Executive
                          AI, or the CEO depending on the output's authority
                          level requirements.
                          Future engine: Approval Engine.

    INFORMATION_REQUEST — The requester needs a factual response from another
                          agent or component — a status report, a count, a
                          configuration value, or any other point-in-time
                          data that does not require the formal approval or
                          discussion protocol.
                          Future engine: None (handled inline by the target).
    """

    DISCUSSION = "DISCUSSION"
    MEMORY_LOOKUP = "MEMORY_LOOKUP"
    APPROVAL = "APPROVAL"
    INFORMATION_REQUEST = "INFORMATION_REQUEST"

    def __str__(self) -> str:
        return self.value

    def requires_formal_engine(self) -> bool:
        """
        Return True if this type will be processed by a dedicated engine.

        DISCUSSION, MEMORY_LOOKUP, and APPROVAL are routed to their
        respective engines in future sprints. INFORMATION_REQUEST is
        handled inline by the target agent.

        Returns:
            True for DISCUSSION, MEMORY_LOOKUP, and APPROVAL.
        """
        return self in {
            CollaborationType.DISCUSSION,
            CollaborationType.MEMORY_LOOKUP,
            CollaborationType.APPROVAL,
        }
