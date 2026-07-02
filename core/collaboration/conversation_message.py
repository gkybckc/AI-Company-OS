"""
ConversationMessage — typed, immutable message atom for the Collaboration Hub.

Eight structured categories replace free-form text: every message declares
its intent (Question, Proposal, Risk, …) so policies can act on category,
not keyword matching. No AI, no networking, no async.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Optional
from uuid import uuid4


class MessageCategory(str, Enum):
    """
    Semantic type of a ConversationMessage.

    QUESTION         — Sender seeks information or clarification.
    ANSWER           — Sender responds to a QUESTION.
    PROPOSAL         — Sender proposes a course of action or change.
    REVIEW           — Sender evaluates prior work or a PROPOSAL.
    APPROVAL_REQUEST — Sender formally requests sign-off from a receiver.
    WARNING          — Sender flags a concern that does not yet block work.
    RISK             — Sender identifies a blocking or high-impact risk.
    DECISION         — Sender records a binding decision.
    """

    QUESTION = "question"
    ANSWER = "answer"
    PROPOSAL = "proposal"
    REVIEW = "review"
    APPROVAL_REQUEST = "approval_request"
    WARNING = "warning"
    RISK = "risk"
    DECISION = "decision"

    def __str__(self) -> str:
        return self.value

    def label(self) -> str:
        """Human-readable Turkish label for UI display."""
        labels = {
            "question": "Soru",
            "answer": "Yanit",
            "proposal": "Oneri",
            "review": "Inceleme",
            "approval_request": "Onay Istegi",
            "warning": "Uyari",
            "risk": "Risk",
            "decision": "Karar",
        }
        return labels.get(self.value, self.value.title())

    def css_class(self) -> str:
        """CSS bubble class for dashboard chat rendering."""
        classes = {
            "question": "bubble-question",
            "answer": "bubble-answer",
            "proposal": "bubble-proposal",
            "review": "bubble-review",
            "approval_request": "bubble-approval",
            "warning": "bubble-warning",
            "risk": "bubble-risk",
            "decision": "bubble-decision",
        }
        return classes.get(self.value, "bubble-default")

    def is_blocking_category(self) -> bool:
        """True for categories that typically require a mandatory response."""
        return self in {
            MessageCategory.APPROVAL_REQUEST,
            MessageCategory.RISK,
        }


@dataclass(frozen=True)
class ConversationMessage:
    """
    Immutable record of one participant's typed contribution.

    Attributes:
        id: UUID string assigned at creation.
        sender: participant_id of the author.
        receiver: participant_id of the target, or "all" for broadcast.
        timestamp: UTC datetime of the message.
        category: Semantic type (one of MessageCategory).
        content: The message body; must be non-empty.
    """

    id: str
    sender: str
    receiver: str
    timestamp: datetime
    category: MessageCategory
    content: str

    @classmethod
    def create(
        cls,
        sender: str,
        receiver: str,
        category: MessageCategory,
        content: str,
        timestamp: Optional["datetime"] = None,
    ) -> "ConversationMessage":
        """
        Factory method — assigns a UUID and defaults timestamp to now.

        Args:
            sender: participant_id of the author.
            receiver: participant_id of the target or "all".
            category: One of MessageCategory.
            content: Non-empty message body.
            timestamp: UTC datetime; defaults to datetime.utcnow().

        Returns:
            A new immutable ConversationMessage.
        """
        from datetime import timezone
        ts = timestamp or datetime.now(timezone.utc)
        return cls(
            id=str(uuid4()),
            sender=sender,
            receiver=receiver,
            timestamp=ts,
            category=category,
            content=content,
        )

    # ------------------------------------------------------------------
    # Predicates
    # ------------------------------------------------------------------

    def is_broadcast(self) -> bool:
        """True if this message was sent to all participants."""
        return self.receiver == "all"

    def is_directed_to(self, participant_id: str) -> bool:
        """True if this message targets the given participant or is broadcast."""
        return self.receiver == "all" or self.receiver == participant_id

    def is_from(self, participant_id: str) -> bool:
        """True if this message was sent by the given participant."""
        return self.sender == participant_id

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "sender": self.sender,
            "receiver": self.receiver,
            "timestamp": self.timestamp.isoformat(),
            "category": self.category.value,
            "category_label": self.category.label(),
            "css_class": self.category.css_class(),
            "content": self.content,
            "is_broadcast": self.is_broadcast(),
        }


# Optional import guard for the factory classmethod
