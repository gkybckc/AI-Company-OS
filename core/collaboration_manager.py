"""
Collaboration Manager for AI Company OS.

The CollaborationManager is the single point of coordination for all
inter-agent collaboration requests. It enforces the lifecycle of every
request, validates every response, and provides the query surface that
consumers use to find and monitor collaboration activity.

The manager is an in-memory registry — it has no persistence and no
networking. It is a deterministic state machine: given the same sequence
of calls, it will always produce the same results.

Lifecycle enforced by this manager:
    PENDING  → COMPLETED  (via respond())
    PENDING  → REJECTED   (via respond() with status=REJECTED)
    PENDING  → FAILED     (via respond() with status=FAILED)
    PENDING  → CANCELLED  (via cancel())
    Any terminal state → no further transitions (immutable)

Architecture reference: §2.6 Communication Model, §3 Layer 3 (Infrastructure),
constitution Chapter 14 (Collaboration protocols).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from core.collaboration_request import CollaborationRequest
from core.collaboration_response import CollaborationResponse
from core.collaboration_status import (
    PRIORITY_MAX,
    PRIORITY_MIN,
    VALID_RESPONSE_STATUSES,
    CollaborationStatus,
)
from core.collaboration_type import CollaborationType


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

class CollaborationError(Exception):
    """Base class for all Collaboration Core errors."""


class RequestNotFoundError(CollaborationError):
    """
    Raised when a request_id cannot be resolved in the manager.

    Callers must create requests via create_request() before referencing
    them with find(), respond(), or cancel().
    """


class RequestNotPendingError(CollaborationError):
    """
    Raised when respond() or cancel() targets a non-pending request.

    A request is non-pending when it has already received a response
    (status is COMPLETED, REJECTED, or FAILED) or has been cancelled.
    The message includes the current status to aid debugging.
    """


class InvalidRequestError(CollaborationError):
    """
    Raised when create_request() or respond() receives invalid input.

    Covers: empty requester or target identifiers, empty message,
    priority outside [1, 5], invalid response status, and empty
    responder identifier.
    """


# ---------------------------------------------------------------------------
# CollaborationManager
# ---------------------------------------------------------------------------

class CollaborationManager:
    """
    In-memory registry and lifecycle enforcer for collaboration requests.

    One CollaborationManager instance may serve the entire company, or
    a separate instance may be created per project or per department.
    The manager has no shared state outside of its own instance — it is
    fully isolated and safe to use in tests without teardown concerns.

    Internal structure:
        _requests   — Dict[str, CollaborationRequest]  by request ID
        _responses  — Dict[str, CollaborationResponse] by request ID
        _cancelled  — Dict[str, str]                   request ID → reason

    A request's effective status is derived by the manager:
        - No response, not in _cancelled  → PENDING
        - In _cancelled                   → CANCELLED
        - Has response                    → the response's status
    """

    def __init__(self) -> None:
        self._requests: Dict[str, CollaborationRequest] = {}
        self._responses: Dict[str, CollaborationResponse] = {}
        self._cancelled: Dict[str, str] = {}  # request_id → cancellation reason

    # ------------------------------------------------------------------
    # Command methods
    # ------------------------------------------------------------------

    def create_request(
        self,
        requester: str,
        target: str,
        collaboration_type: CollaborationType,
        message: str,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        priority: int = 3,
    ) -> CollaborationRequest:
        """
        Create and register a new collaboration request.

        The manager assigns a UUID and a UTC timestamp. The request is
        immediately available for querying via find() and list_pending().

        Args:
            requester: Non-empty identifier of the requesting agent or
                component.
            target: Non-empty identifier of the intended responder.
            collaboration_type: The category of collaboration needed.
            message: Non-empty human-readable request content.
            project_id: Optional project this request is associated with.
            task_id: Optional task that triggered this request.
            priority: Integer in [1, 5]. 1 = highest urgency.
                Default: 3 (medium).

        Returns:
            The newly created CollaborationRequest in PENDING state.

        Raises:
            InvalidRequestError: If requester, target, or message is empty,
                or if priority is outside [1, 5].
        """
        if not requester or not requester.strip():
            raise InvalidRequestError(
                "requester must be a non-empty identifier."
            )
        if not target or not target.strip():
            raise InvalidRequestError(
                "target must be a non-empty identifier."
            )
        if not message or not message.strip():
            raise InvalidRequestError(
                "message must be a non-empty string."
            )
        if not (PRIORITY_MIN <= priority <= PRIORITY_MAX):
            raise InvalidRequestError(
                f"priority must be in [{PRIORITY_MIN}, {PRIORITY_MAX}]; "
                f"received {priority}."
            )

        request = CollaborationRequest(
            id=str(uuid4()),
            requester=requester,
            target=target,
            project_id=project_id,
            task_id=task_id,
            collaboration_type=collaboration_type,
            priority=priority,
            message=message,
            created_at=datetime.now(timezone.utc),
        )
        self._requests[request.id] = request
        return request

    def respond(
        self,
        request_id: str,
        responder: str,
        status: CollaborationStatus,
        summary: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> CollaborationResponse:
        """
        Record a response to a pending collaboration request.

        Exactly one response may be recorded per request. The request
        must be in PENDING state at the time of the call.

        Args:
            request_id: ID of the CollaborationRequest to respond to.
            responder: Non-empty identifier of the responding agent or
                component.
            status: The outcome status. Must be one of COMPLETED, REJECTED,
                or FAILED. PENDING and CANCELLED are not valid response
                statuses.
            summary: Non-empty human-readable description of the response.
            payload: Optional structured response data. Defaults to an
                empty dict.

        Returns:
            The newly created CollaborationResponse, permanently linked
            to the request.

        Raises:
            RequestNotFoundError: If request_id does not exist.
            RequestNotPendingError: If the request is not in PENDING state.
            InvalidRequestError: If responder or summary is empty, or if
                status is not a valid response status.
        """
        request = self._resolve(request_id)
        current_status = self._compute_status(request_id)

        if not current_status.is_pending():
            raise RequestNotPendingError(
                f"Request '{request_id}' is not pending "
                f"(current status: {current_status}). "
                f"Only pending requests can receive a response."
            )

        if not responder or not responder.strip():
            raise InvalidRequestError(
                "responder must be a non-empty identifier."
            )
        if status not in VALID_RESPONSE_STATUSES:
            raise InvalidRequestError(
                f"Response status must be one of "
                f"{[s.value for s in VALID_RESPONSE_STATUSES]}; "
                f"received '{status}'."
            )
        if not summary or not summary.strip():
            raise InvalidRequestError(
                "summary must be a non-empty string."
            )

        response = CollaborationResponse(
            request_id=request_id,
            responder=responder,
            status=status,
            summary=summary,
            payload=dict(payload) if payload else {},
            created_at=datetime.now(timezone.utc),
        )
        self._responses[request_id] = response
        return response

    def cancel(
        self,
        request_id: str,
        reason: str = "",
    ) -> CollaborationRequest:
        """
        Cancel a pending collaboration request.

        Only pending requests can be cancelled. Cancellation is
        irrevocable — a cancelled request cannot be reactivated.

        Args:
            request_id: ID of the request to cancel.
            reason: Optional human-readable reason for the cancellation.

        Returns:
            The original CollaborationRequest (unchanged — the request
            is immutable; the manager records the cancellation separately).

        Raises:
            RequestNotFoundError: If request_id does not exist.
            RequestNotPendingError: If the request is not in PENDING state.
        """
        request = self._resolve(request_id)
        current_status = self._compute_status(request_id)

        if not current_status.is_pending():
            raise RequestNotPendingError(
                f"Request '{request_id}' cannot be cancelled "
                f"(current status: {current_status}). "
                f"Only pending requests can be cancelled."
            )

        self._cancelled[request_id] = reason
        return request

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def list_pending(self) -> List[CollaborationRequest]:
        """
        Return all requests currently in PENDING state.

        Results are sorted by priority (ascending — priority 1 first),
        then by created_at (ascending — oldest first within the same
        priority level).

        Returns:
            Shallow copy of the list of pending CollaborationRequest objects.
        """
        pending = [
            r for r in self._requests.values()
            if self._compute_status(r.id).is_pending()
        ]
        return sorted(pending, key=lambda r: (r.priority, r.created_at))

    def list_completed(self) -> List[CollaborationRequest]:
        """
        Return all requests that are no longer pending.

        "Completed" in this context means any terminal state:
        COMPLETED, REJECTED, FAILED, or CANCELLED.

        Results are sorted by the response or cancellation time. Since
        requests are immutable, the sort uses the request's created_at
        as a proxy (oldest request first).

        Returns:
            Shallow copy of the list of non-pending CollaborationRequest
            objects.
        """
        done = [
            r for r in self._requests.values()
            if not self._compute_status(r.id).is_pending()
        ]
        return sorted(done, key=lambda r: r.created_at)

    def find(self, request_id: str) -> CollaborationRequest:
        """
        Return a request by ID.

        All requests — pending, completed, and cancelled — are accessible.

        Args:
            request_id: The id of the CollaborationRequest to retrieve.

        Returns:
            The CollaborationRequest with the given id.

        Raises:
            RequestNotFoundError: If no request with this id exists.
        """
        return self._resolve(request_id)

    def get_response(self, request_id: str) -> Optional[CollaborationResponse]:
        """
        Return the response for a request, or None if not yet responded.

        Args:
            request_id: The id of the CollaborationRequest to look up.

        Returns:
            The CollaborationResponse if one exists, otherwise None.

        Raises:
            RequestNotFoundError: If the request_id does not exist.
        """
        self._resolve(request_id)  # validates existence
        return self._responses.get(request_id)

    def get_status(self, request_id: str) -> CollaborationStatus:
        """
        Return the current lifecycle status of a request.

        Args:
            request_id: The id of the CollaborationRequest.

        Returns:
            The current CollaborationStatus.

        Raises:
            RequestNotFoundError: If the request_id does not exist.
        """
        self._resolve(request_id)
        return self._compute_status(request_id)

    def statistics(self) -> Dict[str, Any]:
        """
        Return a snapshot of the manager's current state.

        Returns a dict with the following keys:

            total_requests      — int: total number of requests ever created.
            pending_count       — int: number of currently pending requests.
            completed_count     — int: requests with a COMPLETED response.
            rejected_count      — int: requests with a REJECTED response.
            failed_count        — int: requests with a FAILED response.
            cancelled_count     — int: cancelled requests.
            by_type             — Dict[str, int]: request counts per
                                  CollaborationType value.
            by_priority         — Dict[int, int]: request counts per
                                  priority level (1–5).
            by_requester        — Dict[str, int]: request counts per
                                  requester identifier.
            response_rate       — float: fraction of total requests that have
                                  received any response (including rejections
                                  and failures). 0.0 if no requests exist.
            success_rate        — float: fraction of responded-to requests
                                  that were COMPLETED. 0.0 if no responses.

        Returns:
            Dict with the statistics described above.
        """
        total = len(self._requests)
        pending_count = 0
        completed_count = 0
        rejected_count = 0
        failed_count = 0
        cancelled_count = len(self._cancelled)

        by_type: Dict[str, int] = {ct.value: 0 for ct in CollaborationType}
        by_priority: Dict[int, int] = {p: 0 for p in range(PRIORITY_MIN, PRIORITY_MAX + 1)}
        by_requester: Dict[str, int] = {}

        for req in self._requests.values():
            by_type[req.collaboration_type.value] += 1
            by_priority[req.priority] = by_priority.get(req.priority, 0) + 1
            by_requester[req.requester] = by_requester.get(req.requester, 0) + 1

            status = self._compute_status(req.id)
            if status == CollaborationStatus.PENDING:
                pending_count += 1
            elif status == CollaborationStatus.COMPLETED:
                completed_count += 1
            elif status == CollaborationStatus.REJECTED:
                rejected_count += 1
            elif status == CollaborationStatus.FAILED:
                failed_count += 1

        responded = completed_count + rejected_count + failed_count
        response_rate = responded / total if total > 0 else 0.0
        success_rate = completed_count / responded if responded > 0 else 0.0

        return {
            "total_requests": total,
            "pending_count": pending_count,
            "completed_count": completed_count,
            "rejected_count": rejected_count,
            "failed_count": failed_count,
            "cancelled_count": cancelled_count,
            "by_type": by_type,
            "by_priority": by_priority,
            "by_requester": by_requester,
            "response_rate": response_rate,
            "success_rate": success_rate,
        }

    def count(self) -> int:
        """Return the total number of requests in this manager."""
        return len(self._requests)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve(self, request_id: str) -> CollaborationRequest:
        """
        Return the request with the given id, or raise RequestNotFoundError.

        Raises:
            RequestNotFoundError: If the id is not in _requests.
        """
        request = self._requests.get(request_id)
        if request is None:
            raise RequestNotFoundError(
                f"No collaboration request with id '{request_id}' exists."
            )
        return request

    def _compute_status(self, request_id: str) -> CollaborationStatus:
        """
        Derive the effective lifecycle status of a request from manager state.

        Priority of determination:
        1. If a response exists → return response.status
        2. If cancelled         → return CANCELLED
        3. Otherwise            → return PENDING

        Args:
            request_id: The ID of the request to check. Must exist.

        Returns:
            The effective CollaborationStatus.
        """
        if request_id in self._responses:
            return self._responses[request_id].status
        if request_id in self._cancelled:
            return CollaborationStatus.CANCELLED
        return CollaborationStatus.PENDING
