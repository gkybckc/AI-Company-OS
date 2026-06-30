"""
Comprehensive unit tests for Sprint 8 — Collaboration Core.

Covers: CollaborationType, CollaborationStatus, CollaborationRequest,
CollaborationResponse, and CollaborationManager (all public methods and
all lifecycle transitions).

Run with:
    .venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_collaboration_core.py" -v
"""

import unittest
from datetime import datetime, timezone

from core.collaboration_manager import (
    CollaborationError,
    CollaborationManager,
    InvalidRequestError,
    RequestNotFoundError,
    RequestNotPendingError,
)
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
# Shared factories
# ---------------------------------------------------------------------------

def _manager() -> CollaborationManager:
    return CollaborationManager()


def _create(
    manager: CollaborationManager | None = None,
    requester: str = "agent-001",
    target: str = "director-backend",
    collab_type: CollaborationType = CollaborationType.INFORMATION_REQUEST,
    message: str = "What is the current API version?",
    project_id: str | None = None,
    task_id: str | None = None,
    priority: int = 3,
) -> tuple[CollaborationManager, CollaborationRequest]:
    mgr = manager or _manager()
    req = mgr.create_request(
        requester=requester,
        target=target,
        collaboration_type=collab_type,
        message=message,
        project_id=project_id,
        task_id=task_id,
        priority=priority,
    )
    return mgr, req


def _respond_ok(
    manager: CollaborationManager,
    request_id: str,
    responder: str = "director-backend",
    summary: str = "The current API version is v3.",
    payload: dict | None = None,
) -> CollaborationResponse:
    return manager.respond(
        request_id=request_id,
        responder=responder,
        status=CollaborationStatus.COMPLETED,
        summary=summary,
        payload=payload or {"version": "v3"},
    )


# ---------------------------------------------------------------------------
# TestCollaborationType
# ---------------------------------------------------------------------------

class TestCollaborationType(unittest.TestCase):

    def test_four_types_exist(self) -> None:
        names = {t.name for t in CollaborationType}
        self.assertEqual(
            names,
            {"DISCUSSION", "MEMORY_LOOKUP", "APPROVAL", "INFORMATION_REQUEST"},
        )

    def test_str_returns_value(self) -> None:
        for ct in CollaborationType:
            self.assertEqual(str(ct), ct.value)

    def test_is_str_subclass(self) -> None:
        self.assertIsInstance(CollaborationType.DISCUSSION, str)

    def test_string_comparison(self) -> None:
        self.assertEqual(CollaborationType.APPROVAL, "APPROVAL")
        self.assertEqual(CollaborationType.MEMORY_LOOKUP, "MEMORY_LOOKUP")

    def test_requires_formal_engine_true(self) -> None:
        for ct in (
            CollaborationType.DISCUSSION,
            CollaborationType.MEMORY_LOOKUP,
            CollaborationType.APPROVAL,
        ):
            self.assertTrue(ct.requires_formal_engine(), msg=ct.value)

    def test_requires_formal_engine_false_for_information_request(self) -> None:
        self.assertFalse(
            CollaborationType.INFORMATION_REQUEST.requires_formal_engine()
        )

    def test_values_are_uppercase_strings(self) -> None:
        for ct in CollaborationType:
            self.assertEqual(ct.value, ct.value.upper())

    def test_enum_members_are_distinct(self) -> None:
        values = [ct.value for ct in CollaborationType]
        self.assertEqual(len(values), len(set(values)))


# ---------------------------------------------------------------------------
# TestCollaborationStatus
# ---------------------------------------------------------------------------

class TestCollaborationStatus(unittest.TestCase):

    def test_five_statuses_exist(self) -> None:
        names = {s.name for s in CollaborationStatus}
        self.assertEqual(
            names,
            {"PENDING", "COMPLETED", "CANCELLED", "REJECTED", "FAILED"},
        )

    def test_str_returns_value(self) -> None:
        for cs in CollaborationStatus:
            self.assertEqual(str(cs), cs.value)

    def test_is_str_subclass(self) -> None:
        self.assertIsInstance(CollaborationStatus.PENDING, str)

    def test_is_terminal_true(self) -> None:
        for status in (
            CollaborationStatus.COMPLETED,
            CollaborationStatus.CANCELLED,
            CollaborationStatus.REJECTED,
            CollaborationStatus.FAILED,
        ):
            self.assertTrue(status.is_terminal(), msg=status.value)

    def test_is_terminal_false_for_pending(self) -> None:
        self.assertFalse(CollaborationStatus.PENDING.is_terminal())

    def test_is_pending_true(self) -> None:
        self.assertTrue(CollaborationStatus.PENDING.is_pending())

    def test_is_pending_false(self) -> None:
        for status in (
            CollaborationStatus.COMPLETED,
            CollaborationStatus.CANCELLED,
            CollaborationStatus.REJECTED,
            CollaborationStatus.FAILED,
        ):
            self.assertFalse(status.is_pending(), msg=status.value)

    def test_is_successful_true_only_for_completed(self) -> None:
        self.assertTrue(CollaborationStatus.COMPLETED.is_successful())
        for status in CollaborationStatus:
            if status != CollaborationStatus.COMPLETED:
                self.assertFalse(status.is_successful(), msg=status.value)

    def test_valid_response_statuses_are_terminal(self) -> None:
        for status in VALID_RESPONSE_STATUSES:
            self.assertTrue(status.is_terminal())

    def test_pending_not_in_valid_response_statuses(self) -> None:
        self.assertNotIn(CollaborationStatus.PENDING, VALID_RESPONSE_STATUSES)

    def test_cancelled_not_in_valid_response_statuses(self) -> None:
        self.assertNotIn(CollaborationStatus.CANCELLED, VALID_RESPONSE_STATUSES)

    def test_priority_constants(self) -> None:
        self.assertEqual(PRIORITY_MIN, 1)
        self.assertEqual(PRIORITY_MAX, 5)
        self.assertLess(PRIORITY_MIN, PRIORITY_MAX)


# ---------------------------------------------------------------------------
# TestCollaborationRequest
# ---------------------------------------------------------------------------

class TestCollaborationRequest(unittest.TestCase):

    def setUp(self) -> None:
        self.mgr, self.req = _create(
            requester="agent-A",
            target="director-backend",
            collab_type=CollaborationType.APPROVAL,
            message="Please approve the API design.",
            project_id="proj-001",
            task_id="task-042",
            priority=2,
        )

    def test_fields_stored(self) -> None:
        r = self.req
        self.assertEqual(r.requester, "agent-A")
        self.assertEqual(r.target, "director-backend")
        self.assertEqual(r.collaboration_type, CollaborationType.APPROVAL)
        self.assertEqual(r.message, "Please approve the API design.")
        self.assertEqual(r.project_id, "proj-001")
        self.assertEqual(r.task_id, "task-042")
        self.assertEqual(r.priority, 2)

    def test_id_is_uuid_string(self) -> None:
        self.assertIsInstance(self.req.id, str)
        self.assertEqual(len(self.req.id), 36)

    def test_created_at_is_utc(self) -> None:
        self.assertIsNotNone(self.req.created_at.tzinfo)

    def test_is_frozen(self) -> None:
        with self.assertRaises(Exception):
            self.req.message = "changed"  # type: ignore[misc]

    def test_is_approval(self) -> None:
        self.assertTrue(self.req.is_approval())
        self.assertFalse(self.req.is_discussion())
        self.assertFalse(self.req.is_memory_lookup())
        self.assertFalse(self.req.is_information_request())

    def test_is_discussion(self) -> None:
        _, r = _create(collab_type=CollaborationType.DISCUSSION)
        self.assertTrue(r.is_discussion())

    def test_is_memory_lookup(self) -> None:
        _, r = _create(collab_type=CollaborationType.MEMORY_LOOKUP)
        self.assertTrue(r.is_memory_lookup())

    def test_is_information_request(self) -> None:
        _, r = _create(collab_type=CollaborationType.INFORMATION_REQUEST)
        self.assertTrue(r.is_information_request())

    def test_is_high_priority_true(self) -> None:
        _, r = _create(priority=1)
        self.assertTrue(r.is_high_priority())

    def test_is_high_priority_false(self) -> None:
        _, r = _create(priority=3)
        self.assertFalse(r.is_high_priority())

    def test_has_project_true(self) -> None:
        self.assertTrue(self.req.has_project())

    def test_has_project_false(self) -> None:
        _, r = _create(project_id=None)
        self.assertFalse(r.has_project())

    def test_has_task_true(self) -> None:
        self.assertTrue(self.req.has_task())

    def test_has_task_false(self) -> None:
        _, r = _create(task_id=None)
        self.assertFalse(r.has_task())

    def test_unique_ids_per_request(self) -> None:
        mgr = _manager()
        ids = {mgr.create_request(
            requester="a", target="b",
            collaboration_type=CollaborationType.INFORMATION_REQUEST,
            message="msg",
        ).id for _ in range(10)}
        self.assertEqual(len(ids), 10)

    def test_created_at_between_before_and_after(self) -> None:
        before = datetime.now(timezone.utc)
        _, r = _create()
        after = datetime.now(timezone.utc)
        self.assertGreaterEqual(r.created_at, before)
        self.assertLessEqual(r.created_at, after)


# ---------------------------------------------------------------------------
# TestCollaborationResponse
# ---------------------------------------------------------------------------

class TestCollaborationResponse(unittest.TestCase):

    def setUp(self) -> None:
        self.mgr, self.req = _create()
        self.resp = _respond_ok(self.mgr, self.req.id)

    def test_fields_stored(self) -> None:
        r = self.resp
        self.assertEqual(r.request_id, self.req.id)
        self.assertEqual(r.responder, "director-backend")
        self.assertEqual(r.status, CollaborationStatus.COMPLETED)
        self.assertIn("version", r.payload)
        self.assertIsNotNone(r.created_at)

    def test_summary_stored(self) -> None:
        self.assertEqual(self.resp.summary, "The current API version is v3.")

    def test_is_frozen(self) -> None:
        with self.assertRaises(Exception):
            self.resp.summary = "changed"  # type: ignore[misc]

    def test_is_successful_completed(self) -> None:
        self.assertTrue(self.resp.is_successful())

    def test_is_successful_false_for_rejected(self) -> None:
        mgr, req = _create()
        resp = mgr.respond(
            req.id, "dir", CollaborationStatus.REJECTED, "Not in scope."
        )
        self.assertFalse(resp.is_successful())

    def test_is_rejected(self) -> None:
        mgr, req = _create()
        resp = mgr.respond(
            req.id, "dir", CollaborationStatus.REJECTED, "Rejected."
        )
        self.assertTrue(resp.is_rejected())
        self.assertFalse(self.resp.is_rejected())

    def test_is_failed(self) -> None:
        mgr, req = _create()
        resp = mgr.respond(
            req.id, "dir", CollaborationStatus.FAILED, "Error occurred."
        )
        self.assertTrue(resp.is_failed())

    def test_has_payload_true(self) -> None:
        self.assertTrue(self.resp.has_payload())

    def test_has_payload_false(self) -> None:
        mgr, req = _create()
        resp = mgr.respond(req.id, "dir", CollaborationStatus.COMPLETED, "Done.")
        self.assertFalse(resp.has_payload())

    def test_get_payload_value(self) -> None:
        self.assertEqual(self.resp.get_payload_value("version"), "v3")

    def test_get_payload_value_missing_returns_default(self) -> None:
        self.assertIsNone(self.resp.get_payload_value("no_such_key"))
        self.assertEqual(
            self.resp.get_payload_value("no_such_key", "fallback"), "fallback"
        )

    def test_empty_payload_default(self) -> None:
        mgr, req = _create()
        resp = mgr.respond(req.id, "dir", CollaborationStatus.COMPLETED, "Done.")
        self.assertEqual(resp.payload, {})

    def test_created_at_is_utc(self) -> None:
        self.assertIsNotNone(self.resp.created_at.tzinfo)


# ---------------------------------------------------------------------------
# TestManagerCreateRequest
# ---------------------------------------------------------------------------

class TestManagerCreateRequest(unittest.TestCase):

    def test_create_returns_request(self) -> None:
        mgr, req = _create()
        self.assertIsInstance(req, CollaborationRequest)

    def test_create_increments_count(self) -> None:
        mgr = _manager()
        self.assertEqual(mgr.count(), 0)
        mgr.create_request(
            "a", "b", CollaborationType.INFORMATION_REQUEST, "msg"
        )
        self.assertEqual(mgr.count(), 1)

    def test_create_stores_all_fields(self) -> None:
        mgr, req = _create(
            requester="R1",
            target="T1",
            collab_type=CollaborationType.DISCUSSION,
            message="Let us discuss.",
            project_id="P1",
            task_id="TASK1",
            priority=1,
        )
        self.assertEqual(req.requester, "R1")
        self.assertEqual(req.target, "T1")
        self.assertEqual(req.collaboration_type, CollaborationType.DISCUSSION)
        self.assertEqual(req.message, "Let us discuss.")
        self.assertEqual(req.project_id, "P1")
        self.assertEqual(req.task_id, "TASK1")
        self.assertEqual(req.priority, 1)

    def test_create_default_priority_is_three(self) -> None:
        mgr = _manager()
        req = mgr.create_request("a", "b", CollaborationType.APPROVAL, "msg")
        self.assertEqual(req.priority, 3)

    def test_create_empty_requester_raises(self) -> None:
        mgr = _manager()
        with self.assertRaises(InvalidRequestError):
            mgr.create_request("", "b", CollaborationType.APPROVAL, "msg")

    def test_create_whitespace_requester_raises(self) -> None:
        mgr = _manager()
        with self.assertRaises(InvalidRequestError):
            mgr.create_request("   ", "b", CollaborationType.APPROVAL, "msg")

    def test_create_empty_target_raises(self) -> None:
        mgr = _manager()
        with self.assertRaises(InvalidRequestError):
            mgr.create_request("a", "", CollaborationType.APPROVAL, "msg")

    def test_create_whitespace_target_raises(self) -> None:
        mgr = _manager()
        with self.assertRaises(InvalidRequestError):
            mgr.create_request("a", "   ", CollaborationType.APPROVAL, "msg")

    def test_create_empty_message_raises(self) -> None:
        mgr = _manager()
        with self.assertRaises(InvalidRequestError):
            mgr.create_request("a", "b", CollaborationType.APPROVAL, "")

    def test_create_whitespace_message_raises(self) -> None:
        mgr = _manager()
        with self.assertRaises(InvalidRequestError):
            mgr.create_request("a", "b", CollaborationType.APPROVAL, "   ")

    def test_create_priority_zero_raises(self) -> None:
        mgr = _manager()
        with self.assertRaises(InvalidRequestError):
            mgr.create_request("a", "b", CollaborationType.APPROVAL, "msg", priority=0)

    def test_create_priority_six_raises(self) -> None:
        mgr = _manager()
        with self.assertRaises(InvalidRequestError):
            mgr.create_request("a", "b", CollaborationType.APPROVAL, "msg", priority=6)

    def test_create_priority_negative_raises(self) -> None:
        mgr = _manager()
        with self.assertRaises(InvalidRequestError):
            mgr.create_request("a", "b", CollaborationType.APPROVAL, "msg", priority=-1)

    def test_create_priority_one_allowed(self) -> None:
        mgr = _manager()
        req = mgr.create_request("a", "b", CollaborationType.APPROVAL, "msg", priority=1)
        self.assertEqual(req.priority, 1)

    def test_create_priority_five_allowed(self) -> None:
        mgr = _manager()
        req = mgr.create_request("a", "b", CollaborationType.APPROVAL, "msg", priority=5)
        self.assertEqual(req.priority, 5)

    def test_create_request_is_immediately_pending(self) -> None:
        mgr, req = _create()
        self.assertEqual(mgr.get_status(req.id), CollaborationStatus.PENDING)

    def test_create_all_collaboration_types(self) -> None:
        mgr = _manager()
        for ct in CollaborationType:
            req = mgr.create_request("a", "b", ct, "test message")
            self.assertEqual(req.collaboration_type, ct)

    def test_multiple_requests_unique_ids(self) -> None:
        mgr = _manager()
        ids = set()
        for _ in range(20):
            r = mgr.create_request("a", "b", CollaborationType.APPROVAL, "m")
            ids.add(r.id)
        self.assertEqual(len(ids), 20)

    def test_create_without_optional_fields(self) -> None:
        mgr = _manager()
        req = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "msg")
        self.assertIsNone(req.project_id)
        self.assertIsNone(req.task_id)

    def test_error_hierarchy(self) -> None:
        self.assertTrue(issubclass(InvalidRequestError, CollaborationError))
        self.assertTrue(issubclass(RequestNotFoundError, CollaborationError))
        self.assertTrue(issubclass(RequestNotPendingError, CollaborationError))


# ---------------------------------------------------------------------------
# TestManagerRespond
# ---------------------------------------------------------------------------

class TestManagerRespond(unittest.TestCase):

    def test_respond_returns_response(self) -> None:
        mgr, req = _create()
        resp = _respond_ok(mgr, req.id)
        self.assertIsInstance(resp, CollaborationResponse)

    def test_respond_links_to_request(self) -> None:
        mgr, req = _create()
        resp = _respond_ok(mgr, req.id)
        self.assertEqual(resp.request_id, req.id)

    def test_respond_stores_responder(self) -> None:
        mgr, req = _create()
        resp = mgr.respond(req.id, "resp-001", CollaborationStatus.COMPLETED, "Done.")
        self.assertEqual(resp.responder, "resp-001")

    def test_respond_completed_status(self) -> None:
        mgr, req = _create()
        resp = _respond_ok(mgr, req.id)
        self.assertEqual(resp.status, CollaborationStatus.COMPLETED)

    def test_respond_rejected_status(self) -> None:
        mgr, req = _create()
        resp = mgr.respond(req.id, "dir", CollaborationStatus.REJECTED, "Not in scope.")
        self.assertEqual(resp.status, CollaborationStatus.REJECTED)

    def test_respond_failed_status(self) -> None:
        mgr, req = _create()
        resp = mgr.respond(req.id, "dir", CollaborationStatus.FAILED, "Error.")
        self.assertEqual(resp.status, CollaborationStatus.FAILED)

    def test_respond_transitions_request_to_completed(self) -> None:
        mgr, req = _create()
        _respond_ok(mgr, req.id)
        self.assertEqual(mgr.get_status(req.id), CollaborationStatus.COMPLETED)

    def test_respond_transitions_request_to_rejected(self) -> None:
        mgr, req = _create()
        mgr.respond(req.id, "dir", CollaborationStatus.REJECTED, "No.")
        self.assertEqual(mgr.get_status(req.id), CollaborationStatus.REJECTED)

    def test_respond_transitions_request_to_failed(self) -> None:
        mgr, req = _create()
        mgr.respond(req.id, "dir", CollaborationStatus.FAILED, "Err.")
        self.assertEqual(mgr.get_status(req.id), CollaborationStatus.FAILED)

    def test_respond_moves_from_pending_to_completed(self) -> None:
        mgr, req = _create()
        self.assertIn(req, mgr.list_pending())
        _respond_ok(mgr, req.id)
        self.assertNotIn(req, mgr.list_pending())
        self.assertIn(req, mgr.list_completed())

    def test_respond_twice_raises(self) -> None:
        mgr, req = _create()
        _respond_ok(mgr, req.id)
        with self.assertRaises(RequestNotPendingError):
            _respond_ok(mgr, req.id)

    def test_respond_unknown_request_raises(self) -> None:
        mgr = _manager()
        with self.assertRaises(RequestNotFoundError):
            mgr.respond("no-such-id", "dir", CollaborationStatus.COMPLETED, "Done.")

    def test_respond_cancelled_request_raises(self) -> None:
        mgr, req = _create()
        mgr.cancel(req.id)
        with self.assertRaises(RequestNotPendingError):
            _respond_ok(mgr, req.id)

    def test_respond_empty_responder_raises(self) -> None:
        mgr, req = _create()
        with self.assertRaises(InvalidRequestError):
            mgr.respond(req.id, "", CollaborationStatus.COMPLETED, "Done.")

    def test_respond_whitespace_responder_raises(self) -> None:
        mgr, req = _create()
        with self.assertRaises(InvalidRequestError):
            mgr.respond(req.id, "   ", CollaborationStatus.COMPLETED, "Done.")

    def test_respond_empty_summary_raises(self) -> None:
        mgr, req = _create()
        with self.assertRaises(InvalidRequestError):
            mgr.respond(req.id, "dir", CollaborationStatus.COMPLETED, "")

    def test_respond_whitespace_summary_raises(self) -> None:
        mgr, req = _create()
        with self.assertRaises(InvalidRequestError):
            mgr.respond(req.id, "dir", CollaborationStatus.COMPLETED, "   ")

    def test_respond_pending_status_raises(self) -> None:
        mgr, req = _create()
        with self.assertRaises(InvalidRequestError):
            mgr.respond(req.id, "dir", CollaborationStatus.PENDING, "Still pending.")

    def test_respond_cancelled_status_raises(self) -> None:
        mgr, req = _create()
        with self.assertRaises(InvalidRequestError):
            mgr.respond(req.id, "dir", CollaborationStatus.CANCELLED, "Cancelled.")

    def test_respond_with_payload(self) -> None:
        mgr, req = _create()
        resp = mgr.respond(
            req.id, "dir", CollaborationStatus.COMPLETED, "Done.",
            payload={"decision": "approved", "comment": "LGTM"},
        )
        self.assertEqual(resp.get_payload_value("decision"), "approved")

    def test_respond_payload_is_copied(self) -> None:
        mgr, req = _create()
        original = {"x": 1}
        mgr.respond(req.id, "dir", CollaborationStatus.COMPLETED, "Done.", payload=original)
        original["x"] = 999  # mutate original
        resp = mgr.get_response(req.id)
        self.assertEqual(resp.get_payload_value("x"), 1)

    def test_respond_created_at_is_utc(self) -> None:
        mgr, req = _create()
        resp = _respond_ok(mgr, req.id)
        self.assertIsNotNone(resp.created_at.tzinfo)


# ---------------------------------------------------------------------------
# TestManagerCancel
# ---------------------------------------------------------------------------

class TestManagerCancel(unittest.TestCase):

    def test_cancel_returns_request(self) -> None:
        mgr, req = _create()
        result = mgr.cancel(req.id)
        self.assertIs(result, req)

    def test_cancel_sets_cancelled_status(self) -> None:
        mgr, req = _create()
        mgr.cancel(req.id)
        self.assertEqual(mgr.get_status(req.id), CollaborationStatus.CANCELLED)

    def test_cancel_removes_from_pending(self) -> None:
        mgr, req = _create()
        mgr.cancel(req.id)
        self.assertNotIn(req, mgr.list_pending())

    def test_cancel_moves_to_completed(self) -> None:
        mgr, req = _create()
        mgr.cancel(req.id)
        self.assertIn(req, mgr.list_completed())

    def test_cancel_unknown_raises(self) -> None:
        mgr = _manager()
        with self.assertRaises(RequestNotFoundError):
            mgr.cancel("no-such-id")

    def test_cancel_twice_raises(self) -> None:
        mgr, req = _create()
        mgr.cancel(req.id)
        with self.assertRaises(RequestNotPendingError):
            mgr.cancel(req.id)

    def test_cancel_already_responded_raises(self) -> None:
        mgr, req = _create()
        _respond_ok(mgr, req.id)
        with self.assertRaises(RequestNotPendingError):
            mgr.cancel(req.id)

    def test_cancel_does_not_modify_request(self) -> None:
        mgr, req = _create(message="Original message.")
        mgr.cancel(req.id)
        found = mgr.find(req.id)
        self.assertEqual(found.message, "Original message.")

    def test_cancel_with_reason(self) -> None:
        mgr, req = _create()
        mgr.cancel(req.id, reason="Task was abandoned.")
        self.assertEqual(mgr.get_status(req.id), CollaborationStatus.CANCELLED)

    def test_cancel_with_empty_reason_allowed(self) -> None:
        mgr, req = _create()
        mgr.cancel(req.id, reason="")
        self.assertEqual(mgr.get_status(req.id), CollaborationStatus.CANCELLED)

    def test_cancel_error_message_includes_status(self) -> None:
        mgr, req = _create()
        _respond_ok(mgr, req.id)
        try:
            mgr.cancel(req.id)
            self.fail("Expected RequestNotPendingError")
        except RequestNotPendingError as e:
            self.assertIn("COMPLETED", str(e))

    def test_cancel_partial_list(self) -> None:
        mgr = _manager()
        r1 = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m1")
        r2 = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m2")
        r3 = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m3")
        mgr.cancel(r2.id)
        pending = mgr.list_pending()
        self.assertIn(r1, pending)
        self.assertNotIn(r2, pending)
        self.assertIn(r3, pending)


# ---------------------------------------------------------------------------
# TestManagerListPending
# ---------------------------------------------------------------------------

class TestManagerListPending(unittest.TestCase):

    def test_empty_initially(self) -> None:
        mgr = _manager()
        self.assertEqual(mgr.list_pending(), [])

    def test_new_request_is_pending(self) -> None:
        mgr, req = _create()
        self.assertIn(req, mgr.list_pending())

    def test_responded_request_excluded(self) -> None:
        mgr, req = _create()
        _respond_ok(mgr, req.id)
        self.assertNotIn(req, mgr.list_pending())

    def test_cancelled_request_excluded(self) -> None:
        mgr, req = _create()
        mgr.cancel(req.id)
        self.assertNotIn(req, mgr.list_pending())

    def test_returns_copy(self) -> None:
        mgr, _ = _create()
        lst = mgr.list_pending()
        lst.clear()
        self.assertEqual(mgr.count(), 1)

    def test_sorted_by_priority_ascending(self) -> None:
        mgr = _manager()
        r5 = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m", priority=5)
        r1 = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m", priority=1)
        r3 = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m", priority=3)
        pending = mgr.list_pending()
        self.assertEqual(pending[0].id, r1.id)
        self.assertEqual(pending[1].id, r3.id)
        self.assertEqual(pending[2].id, r5.id)

    def test_same_priority_sorted_by_created_at(self) -> None:
        mgr = _manager()
        r1 = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "first", priority=2)
        r2 = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "second", priority=2)
        pending = mgr.list_pending()
        self.assertLessEqual(pending.index(r1), pending.index(r2))

    def test_only_pending_included(self) -> None:
        mgr = _manager()
        r_pending = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m")
        r_done = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m")
        r_cancelled = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m")
        _respond_ok(mgr, r_done.id)
        mgr.cancel(r_cancelled.id)
        pending = mgr.list_pending()
        self.assertIn(r_pending, pending)
        self.assertNotIn(r_done, pending)
        self.assertNotIn(r_cancelled, pending)


# ---------------------------------------------------------------------------
# TestManagerListCompleted
# ---------------------------------------------------------------------------

class TestManagerListCompleted(unittest.TestCase):

    def test_empty_initially(self) -> None:
        mgr = _manager()
        self.assertEqual(mgr.list_completed(), [])

    def test_responded_request_appears(self) -> None:
        mgr, req = _create()
        _respond_ok(mgr, req.id)
        self.assertIn(req, mgr.list_completed())

    def test_rejected_request_appears(self) -> None:
        mgr, req = _create()
        mgr.respond(req.id, "dir", CollaborationStatus.REJECTED, "No.")
        self.assertIn(req, mgr.list_completed())

    def test_failed_request_appears(self) -> None:
        mgr, req = _create()
        mgr.respond(req.id, "dir", CollaborationStatus.FAILED, "Err.")
        self.assertIn(req, mgr.list_completed())

    def test_cancelled_request_appears(self) -> None:
        mgr, req = _create()
        mgr.cancel(req.id)
        self.assertIn(req, mgr.list_completed())

    def test_pending_request_excluded(self) -> None:
        mgr, req = _create()
        self.assertNotIn(req, mgr.list_completed())

    def test_returns_copy(self) -> None:
        mgr, req = _create()
        _respond_ok(mgr, req.id)
        lst = mgr.list_completed()
        lst.clear()
        self.assertIn(req, mgr.list_completed())

    def test_completed_plus_pending_equals_total(self) -> None:
        mgr = _manager()
        for i in range(5):
            r = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, f"m{i}")
            if i % 2 == 0:
                _respond_ok(mgr, r.id)
        total = mgr.count()
        pending = len(mgr.list_pending())
        completed = len(mgr.list_completed())
        self.assertEqual(pending + completed, total)


# ---------------------------------------------------------------------------
# TestManagerFind
# ---------------------------------------------------------------------------

class TestManagerFind(unittest.TestCase):

    def test_find_returns_request(self) -> None:
        mgr, req = _create()
        found = mgr.find(req.id)
        self.assertIs(found, req)

    def test_find_after_completion(self) -> None:
        mgr, req = _create()
        _respond_ok(mgr, req.id)
        found = mgr.find(req.id)
        self.assertIs(found, req)

    def test_find_after_cancellation(self) -> None:
        mgr, req = _create()
        mgr.cancel(req.id)
        found = mgr.find(req.id)
        self.assertIs(found, req)

    def test_find_unknown_raises(self) -> None:
        mgr = _manager()
        with self.assertRaises(RequestNotFoundError):
            mgr.find("no-such-id")

    def test_find_error_includes_id(self) -> None:
        mgr = _manager()
        try:
            mgr.find("missing-id-XYZ")
            self.fail("Expected RequestNotFoundError")
        except RequestNotFoundError as e:
            self.assertIn("missing-id-XYZ", str(e))

    def test_get_response_none_for_pending(self) -> None:
        mgr, req = _create()
        self.assertIsNone(mgr.get_response(req.id))

    def test_get_response_returns_response(self) -> None:
        mgr, req = _create()
        resp = _respond_ok(mgr, req.id)
        self.assertIs(mgr.get_response(req.id), resp)

    def test_get_response_none_for_cancelled(self) -> None:
        mgr, req = _create()
        mgr.cancel(req.id)
        self.assertIsNone(mgr.get_response(req.id))

    def test_get_response_unknown_request_raises(self) -> None:
        mgr = _manager()
        with self.assertRaises(RequestNotFoundError):
            mgr.get_response("no-such-id")

    def test_get_status_pending(self) -> None:
        mgr, req = _create()
        self.assertEqual(mgr.get_status(req.id), CollaborationStatus.PENDING)

    def test_get_status_completed(self) -> None:
        mgr, req = _create()
        _respond_ok(mgr, req.id)
        self.assertEqual(mgr.get_status(req.id), CollaborationStatus.COMPLETED)

    def test_get_status_cancelled(self) -> None:
        mgr, req = _create()
        mgr.cancel(req.id)
        self.assertEqual(mgr.get_status(req.id), CollaborationStatus.CANCELLED)

    def test_get_status_rejected(self) -> None:
        mgr, req = _create()
        mgr.respond(req.id, "dir", CollaborationStatus.REJECTED, "No.")
        self.assertEqual(mgr.get_status(req.id), CollaborationStatus.REJECTED)

    def test_get_status_failed(self) -> None:
        mgr, req = _create()
        mgr.respond(req.id, "dir", CollaborationStatus.FAILED, "Err.")
        self.assertEqual(mgr.get_status(req.id), CollaborationStatus.FAILED)

    def test_get_status_unknown_raises(self) -> None:
        mgr = _manager()
        with self.assertRaises(RequestNotFoundError):
            mgr.get_status("no-such-id")


# ---------------------------------------------------------------------------
# TestManagerStatistics
# ---------------------------------------------------------------------------

class TestManagerStatistics(unittest.TestCase):

    def test_empty_manager_statistics(self) -> None:
        stats = _manager().statistics()
        self.assertEqual(stats["total_requests"], 0)
        self.assertEqual(stats["pending_count"], 0)
        self.assertEqual(stats["completed_count"], 0)
        self.assertEqual(stats["cancelled_count"], 0)
        self.assertAlmostEqual(stats["response_rate"], 0.0)
        self.assertAlmostEqual(stats["success_rate"], 0.0)

    def test_statistics_required_keys(self) -> None:
        stats = _manager().statistics()
        for key in (
            "total_requests", "pending_count", "completed_count",
            "rejected_count", "failed_count", "cancelled_count",
            "by_type", "by_priority", "by_requester",
            "response_rate", "success_rate",
        ):
            self.assertIn(key, stats)

    def test_statistics_total_requests(self) -> None:
        mgr = _manager()
        for i in range(5):
            mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, f"m{i}")
        self.assertEqual(mgr.statistics()["total_requests"], 5)

    def test_statistics_pending_count(self) -> None:
        mgr = _manager()
        r1 = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m1")
        mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m2")
        _respond_ok(mgr, r1.id)
        self.assertEqual(mgr.statistics()["pending_count"], 1)

    def test_statistics_completed_count(self) -> None:
        mgr = _manager()
        r1 = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m1")
        r2 = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m2")
        _respond_ok(mgr, r1.id)
        mgr.respond(r2.id, "dir", CollaborationStatus.REJECTED, "No.")
        stats = mgr.statistics()
        self.assertEqual(stats["completed_count"], 1)
        self.assertEqual(stats["rejected_count"], 1)

    def test_statistics_cancelled_count(self) -> None:
        mgr = _manager()
        r = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m")
        mgr.cancel(r.id)
        self.assertEqual(mgr.statistics()["cancelled_count"], 1)

    def test_statistics_failed_count(self) -> None:
        mgr = _manager()
        r = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m")
        mgr.respond(r.id, "dir", CollaborationStatus.FAILED, "Error.")
        self.assertEqual(mgr.statistics()["failed_count"], 1)

    def test_statistics_by_type_covers_all_types(self) -> None:
        stats = _manager().statistics()
        for ct in CollaborationType:
            self.assertIn(ct.value, stats["by_type"])

    def test_statistics_by_type_counts_correctly(self) -> None:
        mgr = _manager()
        mgr.create_request("a", "b", CollaborationType.DISCUSSION, "m")
        mgr.create_request("a", "b", CollaborationType.DISCUSSION, "m")
        mgr.create_request("a", "b", CollaborationType.APPROVAL, "m")
        stats = mgr.statistics()
        self.assertEqual(stats["by_type"]["DISCUSSION"], 2)
        self.assertEqual(stats["by_type"]["APPROVAL"], 1)

    def test_statistics_by_priority_covers_all_levels(self) -> None:
        stats = _manager().statistics()
        for p in range(PRIORITY_MIN, PRIORITY_MAX + 1):
            self.assertIn(p, stats["by_priority"])

    def test_statistics_by_priority_counts_correctly(self) -> None:
        mgr = _manager()
        mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m", priority=1)
        mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m", priority=1)
        mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m", priority=5)
        stats = mgr.statistics()
        self.assertEqual(stats["by_priority"][1], 2)
        self.assertEqual(stats["by_priority"][5], 1)

    def test_statistics_by_requester(self) -> None:
        mgr = _manager()
        mgr.create_request("alice", "b", CollaborationType.INFORMATION_REQUEST, "m")
        mgr.create_request("alice", "b", CollaborationType.INFORMATION_REQUEST, "m")
        mgr.create_request("bob", "b", CollaborationType.INFORMATION_REQUEST, "m")
        stats = mgr.statistics()
        self.assertEqual(stats["by_requester"]["alice"], 2)
        self.assertEqual(stats["by_requester"]["bob"], 1)

    def test_statistics_response_rate(self) -> None:
        mgr = _manager()
        r1 = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m")
        r2 = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m")
        mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m")
        _respond_ok(mgr, r1.id)
        mgr.respond(r2.id, "dir", CollaborationStatus.REJECTED, "No.")
        stats = mgr.statistics()
        self.assertAlmostEqual(stats["response_rate"], 2 / 3, places=5)

    def test_statistics_success_rate(self) -> None:
        mgr = _manager()
        r1 = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m")
        r2 = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m")
        _respond_ok(mgr, r1.id)
        mgr.respond(r2.id, "dir", CollaborationStatus.REJECTED, "No.")
        stats = mgr.statistics()
        self.assertAlmostEqual(stats["success_rate"], 0.5, places=5)

    def test_statistics_pending_plus_completed_plus_cancelled_equals_total(self) -> None:
        mgr = _manager()
        for _ in range(6):
            r = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m")
            import random
            choice = _ % 3
            if choice == 0:
                _respond_ok(mgr, r.id)
            elif choice == 1:
                mgr.cancel(r.id)
        stats = mgr.statistics()
        accounted = (
            stats["pending_count"]
            + stats["completed_count"]
            + stats["rejected_count"]
            + stats["failed_count"]
            + stats["cancelled_count"]
        )
        self.assertEqual(accounted, stats["total_requests"])


# ---------------------------------------------------------------------------
# TestIntegration
# ---------------------------------------------------------------------------

class TestIntegration(unittest.TestCase):

    def test_full_approval_lifecycle(self) -> None:
        mgr = _manager()
        req = mgr.create_request(
            requester="backend-agent-001",
            target="approval_engine",
            collaboration_type=CollaborationType.APPROVAL,
            message="Requesting approval for the REST API design document.",
            project_id="proj-saas",
            task_id="task-api-design",
            priority=2,
        )
        self.assertEqual(mgr.get_status(req.id), CollaborationStatus.PENDING)
        self.assertIn(req, mgr.list_pending())

        resp = mgr.respond(
            request_id=req.id,
            responder="approval_engine",
            status=CollaborationStatus.COMPLETED,
            summary="API design approved by the Director.",
            payload={"approved_by": "director-backend", "notes": "LGTM"},
        )
        self.assertEqual(resp.status, CollaborationStatus.COMPLETED)
        self.assertEqual(mgr.get_status(req.id), CollaborationStatus.COMPLETED)
        self.assertNotIn(req, mgr.list_pending())
        self.assertIn(req, mgr.list_completed())

    def test_discussion_then_follow_up_approval(self) -> None:
        mgr = _manager()

        disc_req = mgr.create_request(
            "agent-A", "agent-B", CollaborationType.DISCUSSION,
            "Should we use REST or GraphQL for the API?",
            project_id="proj-1", priority=3,
        )
        mgr.respond(
            disc_req.id, "agent-B", CollaborationStatus.COMPLETED,
            "Consensus: REST for external API, GraphQL for internal.",
            payload={"consensus": "REST+GraphQL"},
        )

        appr_req = mgr.create_request(
            "agent-A", "approval_engine", CollaborationType.APPROVAL,
            "Approve REST+GraphQL decision.",
            project_id="proj-1", priority=2,
        )
        mgr.respond(
            appr_req.id, "approval_engine", CollaborationStatus.COMPLETED,
            "Approved.", payload={"approved": True},
        )

        stats = mgr.statistics()
        self.assertEqual(stats["total_requests"], 2)
        self.assertEqual(stats["completed_count"], 2)
        self.assertEqual(stats["pending_count"], 0)

    def test_rejection_and_resubmission(self) -> None:
        mgr = _manager()
        req1 = mgr.create_request(
            "agent-A", "director", CollaborationType.APPROVAL,
            "Initial API spec — draft.", priority=3,
        )
        mgr.respond(
            req1.id, "director", CollaborationStatus.REJECTED,
            "Needs more detail on error codes.",
        )
        self.assertEqual(mgr.get_status(req1.id), CollaborationStatus.REJECTED)

        req2 = mgr.create_request(
            "agent-A", "director", CollaborationType.APPROVAL,
            "Revised API spec with error codes documented.", priority=2,
        )
        mgr.respond(req2.id, "director", CollaborationStatus.COMPLETED, "Approved.")

        stats = mgr.statistics()
        self.assertEqual(stats["rejected_count"], 1)
        self.assertEqual(stats["completed_count"], 1)
        self.assertEqual(stats["by_requester"].get("agent-A", 0), 2)

    def test_memory_lookup_workflow(self) -> None:
        mgr = _manager()
        req = mgr.create_request(
            "backend-agent", "memory_engine", CollaborationType.MEMORY_LOOKUP,
            "Retrieve the approved database schema for project-saas.",
            project_id="proj-saas", priority=1,
        )
        mgr.respond(
            req.id, "memory_engine", CollaborationStatus.COMPLETED,
            "Schema retrieved from project memory.",
            payload={"schema_version": "v2", "tables": ["users", "products"]},
        )
        resp = mgr.get_response(req.id)
        self.assertEqual(resp.get_payload_value("schema_version"), "v2")

    def test_multiple_requesters_tracked_independently(self) -> None:
        mgr = _manager()
        for i in range(3):
            r = mgr.create_request(
                f"agent-{i}", "director",
                CollaborationType.INFORMATION_REQUEST,
                f"Request from agent {i}",
            )
            if i == 0:
                _respond_ok(mgr, r.id)

        stats = mgr.statistics()
        self.assertEqual(stats["total_requests"], 3)
        self.assertEqual(stats["pending_count"], 2)
        self.assertEqual(stats["completed_count"], 1)

    def test_cancel_workflow(self) -> None:
        mgr = _manager()
        r = mgr.create_request(
            "agent-X", "agent-Y", CollaborationType.DISCUSSION,
            "Discuss the database migration approach.",
        )
        self.assertIn(r, mgr.list_pending())

        mgr.cancel(r.id, "Task was superseded by a new directive from the CEO.")
        self.assertNotIn(r, mgr.list_pending())
        self.assertIn(r, mgr.list_completed())
        self.assertIsNone(mgr.get_response(r.id))
        self.assertEqual(mgr.get_status(r.id), CollaborationStatus.CANCELLED)

    def test_high_volume_requests(self) -> None:
        mgr = _manager()
        requests = []
        for i in range(50):
            r = mgr.create_request(
                f"agent-{i % 5}", "director",
                CollaborationType.INFORMATION_REQUEST,
                f"Request {i}",
                priority=(i % 5) + 1,
            )
            requests.append(r)

        for i, r in enumerate(requests):
            if i % 3 == 0:
                _respond_ok(mgr, r.id)
            elif i % 3 == 1:
                mgr.cancel(r.id)

        stats = mgr.statistics()
        accounted = (
            stats["pending_count"]
            + stats["completed_count"]
            + stats["rejected_count"]
            + stats["failed_count"]
            + stats["cancelled_count"]
        )
        self.assertEqual(accounted, 50)

    def test_list_pending_ordering_stability(self) -> None:
        mgr = _manager()
        reqs = [
            mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST,
                               f"msg {i}", priority=3)
            for i in range(5)
        ]
        pending = mgr.list_pending()
        for r in reqs:
            self.assertIn(r, pending)
        # All same priority — order should be by created_at (stable)
        pending_ids = [r.id for r in pending]
        for expected, actual in zip([r.id for r in reqs], pending_ids):
            self.assertEqual(expected, actual)

    def test_manager_isolation(self) -> None:
        mgr1 = _manager()
        mgr2 = _manager()
        mgr1.create_request("a", "b", CollaborationType.APPROVAL, "m")
        self.assertEqual(mgr1.count(), 1)
        self.assertEqual(mgr2.count(), 0)


# ---------------------------------------------------------------------------
# TestEdgeCasesAndAdditional
# ---------------------------------------------------------------------------

class TestEdgeCasesAndAdditional(unittest.TestCase):

    # ---- CollaborationRequest domain methods ----------------------------

    def test_request_is_high_priority_at_boundary(self) -> None:
        _, r1 = _create(priority=1)
        _, r2 = _create(priority=2)
        self.assertTrue(r1.is_high_priority())
        self.assertFalse(r2.is_high_priority())

    def test_request_has_project_and_task(self) -> None:
        _, r = _create(project_id="P", task_id="T")
        self.assertTrue(r.has_project())
        self.assertTrue(r.has_task())

    def test_request_no_project_no_task(self) -> None:
        _, r = _create(project_id=None, task_id=None)
        self.assertFalse(r.has_project())
        self.assertFalse(r.has_task())

    def test_request_type_helpers_mutually_exclusive(self) -> None:
        for ct in CollaborationType:
            _, r = _create(collab_type=ct)
            true_count = sum([
                r.is_discussion(),
                r.is_approval(),
                r.is_memory_lookup(),
                r.is_information_request(),
            ])
            self.assertEqual(true_count, 1, msg=f"Exactly one type helper should be True for {ct}")

    # ---- CollaborationResponse domain methods ---------------------------

    def test_response_is_successful_only_completed(self) -> None:
        for status in VALID_RESPONSE_STATUSES:
            mgr, req = _create()
            resp = mgr.respond(req.id, "dir", status, "summary")
            expected = (status == CollaborationStatus.COMPLETED)
            self.assertEqual(resp.is_successful(), expected, msg=status.value)

    def test_response_is_rejected_only_rejected(self) -> None:
        for status in VALID_RESPONSE_STATUSES:
            mgr, req = _create()
            resp = mgr.respond(req.id, "dir", status, "summary")
            expected = (status == CollaborationStatus.REJECTED)
            self.assertEqual(resp.is_rejected(), expected, msg=status.value)

    def test_response_is_failed_only_failed(self) -> None:
        for status in VALID_RESPONSE_STATUSES:
            mgr, req = _create()
            resp = mgr.respond(req.id, "dir", status, "summary")
            expected = (status == CollaborationStatus.FAILED)
            self.assertEqual(resp.is_failed(), expected, msg=status.value)

    # ---- Manager lifecycle completeness --------------------------------

    def test_all_terminal_statuses_appear_in_list_completed(self) -> None:
        mgr = _manager()
        r_comp = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m")
        r_rej  = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m")
        r_fail = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m")
        r_canc = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m")
        _respond_ok(mgr, r_comp.id)
        mgr.respond(r_rej.id, "dir", CollaborationStatus.REJECTED, "No.")
        mgr.respond(r_fail.id, "dir", CollaborationStatus.FAILED, "Err.")
        mgr.cancel(r_canc.id)
        completed = mgr.list_completed()
        for r in (r_comp, r_rej, r_fail, r_canc):
            self.assertIn(r, completed)

    def test_respond_to_each_valid_status(self) -> None:
        for status in VALID_RESPONSE_STATUSES:
            mgr, req = _create()
            resp = mgr.respond(req.id, "dir", status, "Done.")
            self.assertEqual(resp.status, status)
            self.assertEqual(mgr.get_status(req.id), status)

    def test_create_request_not_in_completed_initially(self) -> None:
        mgr, req = _create()
        self.assertNotIn(req, mgr.list_completed())

    def test_count_reflects_creates(self) -> None:
        mgr = _manager()
        for i in range(7):
            mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, f"m{i}")
            self.assertEqual(mgr.count(), i + 1)

    def test_find_preserves_all_fields(self) -> None:
        mgr, req = _create(
            requester="req-1", target="tgt-1",
            collab_type=CollaborationType.MEMORY_LOOKUP,
            message="Find schema.", project_id="P1", task_id="T1", priority=4,
        )
        found = mgr.find(req.id)
        self.assertEqual(found.requester, "req-1")
        self.assertEqual(found.target, "tgt-1")
        self.assertEqual(found.collaboration_type, CollaborationType.MEMORY_LOOKUP)
        self.assertEqual(found.message, "Find schema.")
        self.assertEqual(found.project_id, "P1")
        self.assertEqual(found.task_id, "T1")
        self.assertEqual(found.priority, 4)

    def test_cancel_error_message_contains_request_id(self) -> None:
        mgr = _manager()
        try:
            mgr.cancel("nonexistent-id-ABC")
            self.fail("Expected RequestNotFoundError")
        except RequestNotFoundError as e:
            self.assertIn("nonexistent-id-ABC", str(e))

    def test_respond_error_message_contains_request_id(self) -> None:
        mgr = _manager()
        try:
            mgr.respond("nonexistent-id-XYZ", "dir", CollaborationStatus.COMPLETED, "Done.")
            self.fail("Expected RequestNotFoundError")
        except RequestNotFoundError as e:
            self.assertIn("nonexistent-id-XYZ", str(e))

    def test_statistics_response_rate_one_when_all_responded(self) -> None:
        mgr = _manager()
        for i in range(4):
            r = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, f"m{i}")
            _respond_ok(mgr, r.id)
        self.assertAlmostEqual(mgr.statistics()["response_rate"], 1.0)

    def test_statistics_success_rate_zero_when_all_rejected(self) -> None:
        mgr = _manager()
        for i in range(3):
            r = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, f"m{i}")
            mgr.respond(r.id, "dir", CollaborationStatus.REJECTED, "No.")
        self.assertAlmostEqual(mgr.statistics()["success_rate"], 0.0)

    def test_all_priority_levels_accepted(self) -> None:
        mgr = _manager()
        for p in range(PRIORITY_MIN, PRIORITY_MAX + 1):
            r = mgr.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m", priority=p)
            self.assertEqual(r.priority, p)

    def test_request_not_pending_error_is_raised_for_double_respond(self) -> None:
        mgr, req = _create()
        _respond_ok(mgr, req.id)
        try:
            _respond_ok(mgr, req.id)
            self.fail("Expected RequestNotPendingError")
        except RequestNotPendingError as e:
            self.assertIn("COMPLETED", str(e))

    def test_collaboration_status_string_comparison(self) -> None:
        self.assertEqual(CollaborationStatus.COMPLETED, "COMPLETED")
        self.assertEqual(CollaborationStatus.FAILED, "FAILED")
        self.assertEqual(CollaborationStatus.CANCELLED, "CANCELLED")

    def test_collaboration_type_info_request_no_formal_engine(self) -> None:
        self.assertFalse(
            CollaborationType.INFORMATION_REQUEST.requires_formal_engine()
        )

    def test_manager_separate_instances_are_isolated(self) -> None:
        mgr_a = _manager()
        mgr_b = _manager()
        for _ in range(5):
            mgr_a.create_request("a", "b", CollaborationType.INFORMATION_REQUEST, "m")
        self.assertEqual(mgr_a.count(), 5)
        self.assertEqual(mgr_b.count(), 0)

    def test_by_requester_grows_with_creates(self) -> None:
        mgr = _manager()
        mgr.create_request("alice", "b", CollaborationType.APPROVAL, "m1")
        mgr.create_request("alice", "b", CollaborationType.APPROVAL, "m2")
        mgr.create_request("alice", "b", CollaborationType.APPROVAL, "m3")
        stats = mgr.statistics()
        self.assertEqual(stats["by_requester"]["alice"], 3)

    def test_valid_response_statuses_frozenset(self) -> None:
        self.assertIsInstance(VALID_RESPONSE_STATUSES, frozenset)
        self.assertEqual(len(VALID_RESPONSE_STATUSES), 3)

    def test_collaboration_type_all_values_are_strings(self) -> None:
        for ct in CollaborationType:
            self.assertIsInstance(ct.value, str)
            self.assertGreater(len(ct.value), 0)

    def test_collaboration_status_all_values_are_strings(self) -> None:
        for cs in CollaborationStatus:
            self.assertIsInstance(cs.value, str)
            self.assertGreater(len(cs.value), 0)


if __name__ == "__main__":
    unittest.main()
