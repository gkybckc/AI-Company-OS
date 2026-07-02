"""
Conversation — primary entity of the Agent Collaboration Hub.

A Conversation is a typed, multi-party exchange between agent participants.
Unlike the Discussion Engine (which enforces opinion + reasoning per
message), a Conversation uses MessageCategory to classify intent and
supports directed (one-to-one) as well as broadcast messages.

No AI, no networking, no async.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from core.collaboration.conversation_message import ConversationMessage, MessageCategory
from core.collaboration.conversation_participant import ConversationParticipant
from core.collaboration.conversation_summary import ConversationSummary


class ConversationStatus(str, Enum):
    """
    Lifecycle states for a Conversation.

    ACTIVE         — Open for messages and new participants.
    PENDING_REVIEW — Closed to new messages; awaiting formal review sign-off.
    APPROVED       — All required reviews accepted; ready for CEO briefing.
    CLOSED         — Archived. No further activity.
    """

    ACTIVE = "active"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    CLOSED = "closed"

    def __str__(self) -> str:
        return self.value

    def label(self) -> str:
        labels = {
            "active": "Aktif",
            "pending_review": "Inceleme Bekliyor",
            "approved": "Onaylandi",
            "closed": "Kapali",
        }
        return labels.get(self.value, self.value)


@dataclass
class Conversation:
    """
    Live record of one typed multi-party agent conversation.

    Managed exclusively by CollaborationHub. External code should read
    state through the hub's query methods.

    Attributes:
        id: UUID string, assigned at creation.
        title: Human-readable title for the conversation.
        project_id: Optional project link.
        task_id: Optional task link.
        creator: participant_id of the agent who created the conversation.
        participants: Currently admitted participants (ordered by join time).
        messages: Append-only ordered message history.
        summary: ConversationSummary if generated; None otherwise.
        created_at: UTC creation timestamp.
        updated_at: UTC timestamp of last message or status change.
        status: Current ConversationStatus.
        template_type: Optional template that was used to create this conv.
    """

    id: str
    title: str
    project_id: Optional[str]
    task_id: Optional[str]
    creator: str
    participants: List[ConversationParticipant]
    messages: List[ConversationMessage]
    summary: Optional[ConversationSummary]
    created_at: datetime
    updated_at: datetime
    status: ConversationStatus
    template_type: Optional[str] = None

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------

    def is_active(self) -> bool:
        return self.status == ConversationStatus.ACTIVE

    def is_closed(self) -> bool:
        return self.status == ConversationStatus.CLOSED

    def is_pending_review(self) -> bool:
        return self.status == ConversationStatus.PENDING_REVIEW

    def is_approved(self) -> bool:
        return self.status == ConversationStatus.APPROVED

    def is_open_for_messages(self) -> bool:
        """True for ACTIVE and PENDING_REVIEW (review messages still allowed)."""
        return self.status in {ConversationStatus.ACTIVE, ConversationStatus.PENDING_REVIEW}

    # ------------------------------------------------------------------
    # Participant helpers
    # ------------------------------------------------------------------

    def participant_count(self) -> int:
        return len(self.participants)

    def has_participant(self, participant_id: str) -> bool:
        return any(p.participant_id == participant_id for p in self.participants)

    def get_participant(self, participant_id: str) -> Optional[ConversationParticipant]:
        return next(
            (p for p in self.participants if p.participant_id == participant_id),
            None,
        )

    def participant_ids(self) -> List[str]:
        return [p.participant_id for p in self.participants]

    # ------------------------------------------------------------------
    # Message helpers
    # ------------------------------------------------------------------

    def message_count(self) -> int:
        return len(self.messages)

    def last_message(self) -> Optional[ConversationMessage]:
        return self.messages[-1] if self.messages else None

    def messages_by_category(self, category: MessageCategory) -> List[ConversationMessage]:
        return [m for m in self.messages if m.category == category]

    def messages_by_sender(self, sender_id: str) -> List[ConversationMessage]:
        return [m for m in self.messages if m.sender == sender_id]

    def messages_for(self, participant_id: str) -> List[ConversationMessage]:
        """Messages directed to this participant or broadcast."""
        return [m for m in self.messages if m.is_directed_to(participant_id)]

    def unread_count(self, participant_id: str, since: Optional[datetime] = None) -> int:
        """
        Count messages directed at participant_id after `since`.

        If `since` is None, count messages from participants other than
        participant_id (i.e. everything that is not the participant's own).
        """
        msgs = [m for m in self.messages if m.is_directed_to(participant_id)
                and m.sender != participant_id]
        if since is not None:
            msgs = [m for m in msgs if m.timestamp > since]
        return len(msgs)

    def has_category(self, category: MessageCategory) -> bool:
        """True if at least one message with this category exists."""
        return any(m.category == category for m in self.messages)

    def pending_approvals(self) -> List[ConversationMessage]:
        """All APPROVAL_REQUEST messages (may or may not have been fulfilled)."""
        return self.messages_by_category(MessageCategory.APPROVAL_REQUEST)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self, include_messages: bool = True) -> Dict:
        d: Dict = {
            "id": self.id,
            "title": self.title,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "creator": self.creator,
            "status": self.status.value,
            "status_label": self.status.label(),
            "template_type": self.template_type,
            "participant_count": self.participant_count(),
            "message_count": self.message_count(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "participants": [p.to_dict() for p in self.participants],
            "summary": self.summary.to_dict() if self.summary else None,
        }
        if include_messages:
            d["messages"] = [m.to_dict() for m in self.messages]
        else:
            last = self.last_message()
            d["last_message"] = last.to_dict() if last else None
        return d
