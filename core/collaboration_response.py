"""
Collaboration response model for AI Company OS.

A CollaborationResponse is the formal record of one responder's answer
to a CollaborationRequest. It is produced by CollaborationManager.respond()
and is immutable from the moment of creation — every response is a
permanent record of what the responder communicated at that moment.

Responses are linked to requests via request_id. The manager validates
that the linked request exists and is still pending before recording a
response. Only one response may be recorded per request.

Architecture reference: §2.6 Communication Model, §3 Layer 3 (Infrastructure),
constitution Chapter 14 (Collaboration protocols).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from core.collaboration_status import CollaborationStatus


@dataclass(frozen=True)
class CollaborationResponse:
    """
    Immutable record of a responder's answer to a collaboration request.

    Created by CollaborationManager.respond(). The manager assigns
    created_at; all other fields are provided by the caller.

    Once created, a CollaborationResponse is never modified. The request
    it answers is also not modified — the manager records the association
    between request and response internally.

    Attributes:
        request_id: The id of the CollaborationRequest this response
            answers. Must match a known pending request in the manager.
        responder: Identifier of the agent, component, or engine that
            produced this response (e.g., an employee ID, "approval_engine",
            "memory_engine", "director:backend").
        status: The outcome of the collaboration. Must be one of
            COMPLETED, REJECTED, or FAILED. PENDING and CANCELLED are
            request-side lifecycle states and are not valid response
            statuses. The manager validates this before recording.
        summary: Human-readable description of the response outcome.
            Included in CEO-facing status reports and stored in project
            memory. Should be concise but complete enough for the
            requester to act on without reading the full payload.
        payload: Structured response data. The schema is collaboration-type
            specific: for APPROVAL it may contain the decision and rationale;
            for MEMORY_LOOKUP it may contain the retrieved memory records;
            for DISCUSSION it may contain the consensus outcome; for
            INFORMATION_REQUEST it may contain the requested data directly.
            The payload is not validated or interpreted by the manager —
            it is passed through as-is to the requester.
        created_at: UTC timestamp of when this response was recorded by
            the manager.
    """

    request_id: str
    responder: str
    status: CollaborationStatus
    summary: str
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

    def is_successful(self) -> bool:
        """
        Return True if this response represents a positive outcome.

        Returns:
            True if status is COMPLETED.
        """
        return self.status.is_successful()

    def is_rejected(self) -> bool:
        """Return True if the target explicitly rejected the request."""
        return self.status == CollaborationStatus.REJECTED

    def is_failed(self) -> bool:
        """Return True if the collaboration failed due to an error."""
        return self.status == CollaborationStatus.FAILED

    def has_payload(self) -> bool:
        """Return True if the response carries a non-empty payload."""
        return bool(self.payload)

    def get_payload_value(self, key: str, default: Any = None) -> Any:
        """
        Return a value from the payload by key.

        Args:
            key: The payload key to retrieve.
            default: Value to return if the key is absent.

        Returns:
            The payload value, or default if the key is not present.
        """
        return self.payload.get(key, default)
