"""
Collaboration service for the AI Company OS dashboard.

Wraps CollaborationHub operations for collab route handlers.
"""

from typing import Any, Dict, List, Optional

from apps.dashboard.state import DashboardState
from core.collaboration.conversation_message import MessageCategory, ConversationMessage
from core.collaboration.conversation_participant import ConversationParticipant
from core.collaboration.conversation_policy import ConversationPolicy
from core.collaboration.conversation_templates import TemplateType, list_templates


class CollaborationService:
    """Service layer over CollaborationHub for dashboard route handlers."""

    def __init__(self, state: DashboardState) -> None:
        self._state = state

    @property
    def _hub(self):
        return self._state.collab_hub

    # ------------------------------------------------------------------
    # Hub overview
    # ------------------------------------------------------------------

    def get_hub_context(self) -> Dict[str, Any]:
        return {
            "stats": self._hub.statistics(),
            "active_conversations": self._hub.list_active(),
            "pending_review": self._hub.list_pending_review(),
            "all_conversations": self._hub.list_conversations(),
            "sessions": self._hub.list_sessions(),
            "policies": self._hub.list_policies(),
            "templates": list_templates(),
        }

    def get_conversations_context(self) -> Dict[str, Any]:
        return {
            "conversations": self._hub.list_conversations(),
            "stats": self._hub.statistics(),
            "all_templates": list_templates(),
        }

    def get_sessions_context(self) -> Dict[str, Any]:
        return {
            "sessions": self._hub.list_sessions(),
            "all_conversations": self._hub.list_conversations(),
            "stats": self._hub.statistics(),
        }

    def get_policies_context(self) -> Dict[str, Any]:
        policies = self._hub.list_policies()
        stats = self._hub.statistics()
        blocking = sum(1 for p in policies if p.is_blocking)
        stats["blocking_policies"] = blocking
        stats["non_blocking_policies"] = len(policies) - blocking
        stats["total_policies"] = len(policies)
        return {
            "policies": policies,
            "all_templates": list_templates(),
            "all_conversations": self._hub.list_conversations(),
            "stats": stats,
        }

    # ------------------------------------------------------------------
    # Conversations API
    # ------------------------------------------------------------------

    def list_conversations(self) -> List[Dict[str, Any]]:
        return [c.to_dict(include_messages=False) for c in self._hub.list_conversations()]

    def get_conversation(self, conv_id: str) -> Dict[str, Any]:
        return self._hub.get_conversation(conv_id).to_dict(include_messages=True)

    def create_conversation(
        self,
        title: str,
        creator: str,
        project_id: Optional[str],
        task_id: Optional[str],
        template_type: Optional[TemplateType],
    ) -> Dict[str, Any]:
        if template_type:
            conv = self._hub.create_from_template(
                template_type,
                creator=creator,
                project_id=project_id,
                task_id=task_id,
                title_override=title or None,
            )
        else:
            conv = self._hub.create_conversation(
                title=title, creator=creator, project_id=project_id, task_id=task_id
            )
        return conv.to_dict(include_messages=True)

    def join_conversation(
        self,
        conv_id: str,
        participant_id: str,
        name: str,
        role: str,
        department: str,
    ) -> None:
        p = ConversationParticipant(participant_id, name, role, department)
        self._hub.join(conv_id, p)

    def leave_conversation(self, conv_id: str, participant_id: str) -> None:
        self._hub.leave(conv_id, participant_id)

    def send_message(
        self,
        conv_id: str,
        sender: str,
        receiver: str,
        category: MessageCategory,
        content: str,
    ) -> Dict[str, Any]:
        msg = ConversationMessage.create(
            sender=sender, receiver=receiver, category=category, content=content
        )
        self._hub.send_message(conv_id, msg)
        return msg.to_dict()

    def broadcast(
        self,
        conv_id: str,
        sender: str,
        category: MessageCategory,
        content: str,
    ) -> None:
        self._hub.broadcast(conv_id, sender, category, content)

    def summarize(self, conv_id: str) -> Dict[str, Any]:
        return self._hub.summarize(conv_id).to_dict()

    def close_conversation(self, conv_id: str) -> Dict[str, Any]:
        return self._hub.close_conversation(conv_id).to_dict(include_messages=False)

    def request_review(self, conv_id: str) -> str:
        return self._hub.request_review(conv_id).status.value

    def approve_conversation(self, conv_id: str) -> str:
        return self._hub.approve_conversation(conv_id).status.value

    def get_messages(self, conv_id: str) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in self._hub.history(conv_id)]

    def evaluate_policies(self, conv_id: str) -> Dict[str, Any]:
        violations = self._hub.evaluate_policies(conv_id)
        return {
            "violations": [v.to_dict() for v in violations],
            "has_blocking": any(v.is_blocking for v in violations),
        }

    # ------------------------------------------------------------------
    # Sessions API
    # ------------------------------------------------------------------

    def list_sessions(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._hub.list_sessions()]

    def create_session(
        self, title: str, project_id: Optional[str], task_id: Optional[str]
    ) -> Dict[str, Any]:
        return self._hub.create_session(title, project_id, task_id).to_dict()

    def close_session(self, session_id: str) -> Dict[str, Any]:
        return self._hub.close_session(session_id).to_dict()

    def add_to_session(self, session_id: str, conv_id: str) -> Dict[str, Any]:
        return self._hub.add_to_session(session_id, conv_id).to_dict()

    # ------------------------------------------------------------------
    # Policies API
    # ------------------------------------------------------------------

    def list_policies(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self._hub.list_policies()]

    def create_policy(self, policy: ConversationPolicy) -> Dict[str, Any]:
        self._hub.add_policy(policy)
        return policy.to_dict()

    def delete_policy(self, policy_name: str) -> None:
        self._hub.remove_policy(policy_name)

    # ------------------------------------------------------------------
    # Statistics + templates
    # ------------------------------------------------------------------

    def statistics(self) -> Dict[str, Any]:
        return self._hub.statistics()

    def list_templates(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in list_templates()]
