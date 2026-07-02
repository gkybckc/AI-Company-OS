"""
Extended tests for Feature 21 — Agent Collaboration Hub.
Parametrized and HTTP API tests to supplement test_collaboration_hub.py.
"""

import pytest
from datetime import datetime, timezone

from core.collaboration.conversation_message import MessageCategory, ConversationMessage
from core.collaboration.conversation_participant import ConversationParticipant
from core.collaboration.conversation_summary import ConversationSummary
from core.collaboration.conversation import ConversationStatus
from core.collaboration.collaboration_session import SessionStatus
from core.collaboration.conversation_policy import (
    ConversationPolicy, PolicyEngine, PolicyViolation,
)
from core.collaboration.conversation_templates import (
    ConversationTemplate, TemplateType, get_template, list_templates,
    default_policies, BUILT_IN_TEMPLATES,
)
from core.collaboration.collaboration_manager import (
    CollaborationHub,
    ConversationNotFoundError, ConversationClosedError,
    ParticipantAlreadyError, ParticipantNotFoundError,
    SessionNotFoundError, SessionClosedError, InvalidConversationError,
)


def _p(pid="alice", name="Alice", role="dev") -> ConversationParticipant:
    return ConversationParticipant(pid, name, role)


def _hub() -> CollaborationHub:
    return CollaborationHub()


# ===========================================================================
# Parametrized MessageCategory
# ===========================================================================

class TestMessageCategoryParametrized:
    @pytest.mark.parametrize("cat", list(MessageCategory))
    def test_label_returns_str(self, cat):
        assert isinstance(cat.label(), str)

    @pytest.mark.parametrize("cat", list(MessageCategory))
    def test_css_class_starts_bubble(self, cat):
        assert cat.css_class().startswith("bubble-")

    @pytest.mark.parametrize("cat", list(MessageCategory))
    def test_is_blocking_returns_bool(self, cat):
        assert isinstance(cat.is_blocking_category(), bool)

    @pytest.mark.parametrize("cat", list(MessageCategory))
    def test_str_equals_value(self, cat):
        assert str(cat) == cat.value

    @pytest.mark.parametrize("cat", list(MessageCategory))
    def test_message_create_category(self, cat):
        msg = ConversationMessage.create("a", "all", cat, "content")
        assert msg.category == cat

    @pytest.mark.parametrize("cat", list(MessageCategory))
    def test_to_dict_category_label(self, cat):
        msg = ConversationMessage.create("a", "all", cat, "x")
        assert msg.to_dict()["category_label"] == cat.label()

    @pytest.mark.parametrize("cat", list(MessageCategory))
    def test_broadcast_with_any_category(self, cat):
        hub = _hub()
        conv = hub.create_conversation("T", "alice")
        hub.join(conv.id, _p("alice"))
        hub.broadcast(conv.id, "alice", cat, "msg")
        assert conv.last_message().category == cat

    @pytest.mark.parametrize("cat", list(MessageCategory))
    def test_messages_by_category_filter(self, cat):
        hub = _hub()
        conv = hub.create_conversation("T", "alice")
        hub.join(conv.id, _p("alice"))
        hub.broadcast(conv.id, "alice", cat, "msg")
        results = conv.messages_by_category(cat)
        assert len(results) >= 1

    @pytest.mark.parametrize("cat", list(MessageCategory))
    def test_category_value_lowercase(self, cat):
        assert cat.value == cat.value.lower()


# ===========================================================================
# Parametrized TemplateType
# ===========================================================================

class TestTemplateTypeParametrized:
    @pytest.mark.parametrize("tt", list(TemplateType))
    def test_label_non_empty(self, tt):
        assert tt.label() != ""

    @pytest.mark.parametrize("tt", list(TemplateType))
    def test_get_template_correct_type(self, tt):
        tmpl = get_template(tt)
        assert tmpl.template_type == tt

    @pytest.mark.parametrize("tt", list(TemplateType))
    def test_create_from_template_active(self, tt):
        hub = _hub()
        conv = hub.create_from_template(tt, "alice")
        assert conv.is_active()

    @pytest.mark.parametrize("tt", list(TemplateType))
    def test_create_from_template_has_message(self, tt):
        hub = _hub()
        conv = hub.create_from_template(tt, "alice")
        assert conv.message_count() >= 1

    @pytest.mark.parametrize("tt", list(TemplateType))
    def test_template_has_opening_message(self, tt):
        tmpl = get_template(tt)
        assert tmpl.opening_message != ""

    @pytest.mark.parametrize("tt", list(TemplateType))
    def test_template_has_description(self, tt):
        tmpl = get_template(tt)
        assert tmpl.description != ""


# ===========================================================================
# Parametrized ConversationStatus
# ===========================================================================

class TestConversationStatusParametrized:
    @pytest.mark.parametrize("status", list(ConversationStatus))
    def test_label_non_empty(self, status):
        assert status.label() != ""

    @pytest.mark.parametrize("status", list(ConversationStatus))
    def test_value_lowercase(self, status):
        assert status.value == status.value.lower()

    @pytest.mark.parametrize("status", list(ConversationStatus))
    def test_str_equals_value(self, status):
        assert str(status) == status.value


# ===========================================================================
# Parametrized SessionStatus
# ===========================================================================

class TestSessionStatusParametrized:
    @pytest.mark.parametrize("status", list(SessionStatus))
    def test_label_non_empty(self, status):
        assert status.label() != ""

    @pytest.mark.parametrize("status", list(SessionStatus))
    def test_value_lowercase(self, status):
        assert status.value == status.value.lower()


# ===========================================================================
# PolicyEngine parametrized
# ===========================================================================

class TestPolicyEngineParametrized:
    @pytest.mark.parametrize("cat", list(MessageCategory))
    def test_wildcard_policy_matches_any_category(self, cat):
        eng = PolicyEngine()
        eng.add_policy(ConversationPolicy("p", "d", trigger_category=""))
        results = eng.get_applicable_policies("any", cat.value)
        assert len(results) >= 1

    @pytest.mark.parametrize("cat", list(MessageCategory))
    def test_specific_policy_matches_only_own_category(self, cat):
        eng = PolicyEngine()
        eng.add_policy(ConversationPolicy("p", "d", trigger_category=cat.value))
        for other_cat in MessageCategory:
            results = eng.get_applicable_policies("any", other_cat.value)
            if other_cat == cat:
                assert len(results) >= 1
            else:
                assert len(results) == 0


# ===========================================================================
# HTTP API tests
# ===========================================================================

@pytest.fixture(scope="module")
def test_client():
    from apps.dashboard.main import app
    from starlette.testclient import TestClient
    return TestClient(app)


class TestCollabHTTP:
    def test_get_conversations(self, test_client):
        r = test_client.get("/api/collab/conversations")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_conversation(self, test_client):
        r = test_client.post("/api/collab/conversations", json={
            "title": "Test Conv HTTP",
            "creator": "tester",
        })
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_create_conversation_with_template(self, test_client):
        r = test_client.post("/api/collab/conversations", json={
            "title": "Template Conv",
            "creator": "tester",
            "template_type": "security_review",
        })
        assert r.status_code == 200

    def test_get_conversation_by_id(self, test_client):
        r = test_client.post("/api/collab/conversations", json={
            "title": "ID Test", "creator": "alice",
        })
        cid = r.json()["conversation"]["id"]
        r2 = test_client.get(f"/api/collab/conversations/{cid}")
        assert r2.status_code == 200
        assert r2.json()["id"] == cid

    def test_get_conversation_missing(self, test_client):
        r = test_client.get("/api/collab/conversations/no-such-id")
        assert r.status_code == 404

    def test_join_participant(self, test_client):
        r = test_client.post("/api/collab/conversations", json={
            "title": "Join Test", "creator": "alice",
        })
        cid = r.json()["conversation"]["id"]
        r2 = test_client.post(f"/api/collab/conversations/{cid}/join", json={
            "participant_id": "bob", "name": "Bob", "role": "qa",
        })
        assert r2.status_code == 200

    def test_broadcast_message(self, test_client):
        r = test_client.post("/api/collab/conversations", json={
            "title": "Broadcast Test", "creator": "alice",
        })
        cid = r.json()["conversation"]["id"]
        test_client.post(f"/api/collab/conversations/{cid}/join", json={
            "participant_id": "alice", "name": "Alice", "role": "dev",
        })
        r2 = test_client.post(f"/api/collab/conversations/{cid}/broadcast", json={
            "sender": "alice", "category": "proposal", "content": "Proposal text",
        })
        assert r2.status_code == 200

    def test_get_history(self, test_client):
        r = test_client.post("/api/collab/conversations", json={
            "title": "History Test", "creator": "alice",
        })
        cid = r.json()["conversation"]["id"]
        r2 = test_client.get(f"/api/collab/conversations/{cid}/messages")
        assert r2.status_code == 200
        assert isinstance(r2.json(), list)

    def test_summarize(self, test_client):
        r = test_client.post("/api/collab/conversations", json={
            "title": "Summary Test", "creator": "alice",
        })
        cid = r.json()["conversation"]["id"]
        r2 = test_client.post(f"/api/collab/conversations/{cid}/summarize")
        assert r2.status_code == 200

    def test_request_review(self, test_client):
        r = test_client.post("/api/collab/conversations", json={
            "title": "Review Test", "creator": "alice",
        })
        cid = r.json()["conversation"]["id"]
        r2 = test_client.post(f"/api/collab/conversations/{cid}/request-review")
        assert r2.status_code == 200
        assert r2.json()["success"] is True

    def test_approve(self, test_client):
        r = test_client.post("/api/collab/conversations", json={
            "title": "Approve Test", "creator": "alice",
        })
        cid = r.json()["conversation"]["id"]
        test_client.post(f"/api/collab/conversations/{cid}/request-review")
        r2 = test_client.post(f"/api/collab/conversations/{cid}/approve")
        assert r2.status_code == 200

    def test_close_conversation(self, test_client):
        r = test_client.post("/api/collab/conversations", json={
            "title": "Close Test", "creator": "alice",
        })
        cid = r.json()["conversation"]["id"]
        r2 = test_client.post(f"/api/collab/conversations/{cid}/close")
        assert r2.status_code == 200
        assert r2.json()["success"] is True

    def test_evaluate_policies(self, test_client):
        r = test_client.post("/api/collab/conversations", json={
            "title": "Eval Test", "creator": "alice",
        })
        cid = r.json()["conversation"]["id"]
        r2 = test_client.get(f"/api/collab/conversations/{cid}/policies")
        assert r2.status_code == 200
        assert "violations" in r2.json()

    def test_get_statistics(self, test_client):
        r = test_client.get("/api/collab/statistics")
        assert r.status_code == 200
        assert "total_conversations" in r.json()

    def test_get_templates(self, test_client):
        r = test_client.get("/api/collab/templates")
        assert r.status_code == 200
        assert len(r.json()) == 6

    def test_get_sessions(self, test_client):
        r = test_client.get("/api/collab/sessions")
        assert r.status_code == 200

    def test_create_session(self, test_client):
        r = test_client.post("/api/collab/sessions", json={"title": "HTTP Session"})
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_close_session(self, test_client):
        r = test_client.post("/api/collab/sessions", json={"title": "To Close"})
        sid = r.json()["session"]["id"]
        r2 = test_client.post(f"/api/collab/sessions/{sid}/close")
        assert r2.status_code == 200

    def test_get_policies(self, test_client):
        r = test_client.get("/api/collab/policies")
        assert r.status_code == 200

    def test_create_policy(self, test_client):
        r = test_client.post("/api/collab/policies", json={
            "name": "ext-test-policy",
            "description": "Extended test",
            "trigger_category": "risk",
            "is_blocking": False,
        })
        assert r.status_code == 200

    def test_delete_policy(self, test_client):
        test_client.post("/api/collab/policies", json={
            "name": "ext-delete-me",
            "description": "Will be deleted",
        })
        r = test_client.delete("/api/collab/policies/ext-delete-me")
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_add_to_session(self, test_client):
        rc = test_client.post("/api/collab/conversations", json={
            "title": "Session Conv", "creator": "alice",
        })
        cid = rc.json()["conversation"]["id"]
        rs = test_client.post("/api/collab/sessions", json={"title": "Session X"})
        sid = rs.json()["session"]["id"]
        r = test_client.post(f"/api/collab/sessions/{sid}/add", json={
            "conversation_id": cid,
        })
        assert r.status_code == 200


# ===========================================================================
# Dashboard page renders
# ===========================================================================

class TestCollabPageRenders:
    def test_hub_page(self, test_client):
        r = test_client.get("/collab")
        assert r.status_code == 200

    def test_conversations_page(self, test_client):
        r = test_client.get("/collab/conversations")
        assert r.status_code == 200

    def test_sessions_page(self, test_client):
        r = test_client.get("/collab/sessions")
        assert r.status_code == 200

    def test_policies_page(self, test_client):
        r = test_client.get("/collab/policies")
        assert r.status_code == 200

    def test_hub_html_contains_kpi(self, test_client):
        r = test_client.get("/collab")
        assert "kpi" in r.text.lower() or "Toplam" in r.text or "Aktif" in r.text

    def test_conversations_html_contains_konusmalar(self, test_client):
        r = test_client.get("/collab/conversations")
        assert "onusma" in r.text

    def test_sessions_html_contains_oturum(self, test_client):
        r = test_client.get("/collab/sessions")
        assert "turum" in r.text

    def test_policies_html_contains_politika(self, test_client):
        r = test_client.get("/collab/policies")
        assert "olitika" in r.text


# ===========================================================================
# Data integrity extras
# ===========================================================================

class TestDataIntegrityExtended:
    def test_conversation_ids_unique_at_scale(self):
        hub = _hub()
        ids = [hub.create_conversation(f"T{i}", "alice").id for i in range(30)]
        assert len(set(ids)) == 30

    def test_message_ids_unique_at_scale(self):
        hub = _hub()
        conv = hub.create_conversation("T", "alice")
        hub.join(conv.id, _p("alice"))
        for i in range(30):
            hub.broadcast(conv.id, "alice", MessageCategory.QUESTION, f"q{i}")
        ids = [m.id for m in conv.messages]
        assert len(set(ids)) == 30

    def test_session_ids_unique_at_scale(self):
        hub = _hub()
        ids = [hub.create_session(f"S{i}").id for i in range(30)]
        assert len(set(ids)) == 30

    def test_leave_and_rejoin_cycle(self):
        hub = _hub()
        conv = hub.create_conversation("T", "alice")
        for _ in range(3):
            hub.join(conv.id, _p("alice"))
            hub.leave(conv.id, "alice")
        # After 3 cycles should not be a participant
        assert not conv.has_participant("alice")

    def test_conversation_default_project_id_none(self):
        hub = _hub()
        conv = hub.create_conversation("T", "alice")
        assert conv.project_id is None

    def test_conversation_default_task_id_none(self):
        hub = _hub()
        conv = hub.create_conversation("T", "alice")
        assert conv.task_id is None

    def test_broadcast_sets_receiver_all(self):
        hub = _hub()
        conv = hub.create_conversation("T", "alice")
        hub.join(conv.id, _p("alice"))
        hub.broadcast(conv.id, "alice", MessageCategory.QUESTION, "q?")
        assert conv.last_message().receiver == "all"

    def test_send_directed_message(self):
        hub = _hub()
        conv = hub.create_conversation("T", "alice")
        hub.join(conv.id, _p("alice"))
        hub.join(conv.id, _p("bob", "Bob", "qa"))
        msg = ConversationMessage.create("alice", "bob", MessageCategory.ANSWER, "a")
        hub.send_message(conv.id, msg)
        assert conv.last_message().receiver == "bob"

    def test_statistics_messages_by_category_all_keys(self):
        hub = _hub()
        conv = hub.create_conversation("T", "alice")
        hub.join(conv.id, _p("alice"))
        for cat in MessageCategory:
            hub.broadcast(conv.id, "alice", cat, "x")
        stats = hub.statistics()
        for cat in MessageCategory:
            assert cat.value in stats["messages_by_category"]

    def test_policy_violation_frozen(self):
        v = PolicyViolation("p", "d", True)
        with pytest.raises((AttributeError, TypeError)):
            v.is_blocking = False

    def test_participant_to_dict_includes_joined_at(self):
        p = ConversationParticipant("alice", "Alice", "dev")
        d = p.to_dict()
        assert "joined_at" in d

    def test_conversation_to_dict_has_creator(self):
        hub = _hub()
        conv = hub.create_conversation("T", "creator123")
        d = conv.to_dict()
        assert d.get("creator") == "creator123"

    def test_conversation_to_dict_has_title(self):
        hub = _hub()
        conv = hub.create_conversation("My Unique Title", "alice")
        d = conv.to_dict()
        assert d["title"] == "My Unique Title"
