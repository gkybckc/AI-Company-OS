"""
CollaborationSession — groups related Conversations for one task or sprint.

A session acts as a container for multiple conversations. It tracks overall
progress and can be closed once all contained conversations are resolved.
No AI, no networking, no async.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class SessionStatus(str, Enum):
    """
    OPEN      — Session is active; conversations may be added.
    REVIEWING — All conversations closed; pending executive sign-off.
    CLOSED    — Session finalised; immutable historical record.
    """

    OPEN = "open"
    REVIEWING = "reviewing"
    CLOSED = "closed"

    def __str__(self) -> str:
        return self.value

    def label(self) -> str:
        labels = {"open": "Acik", "reviewing": "Incelemede", "closed": "Kapali"}
        return labels.get(self.value, self.value)


@dataclass
class CollaborationSession:
    """
    Container grouping related Conversations for a task or sprint.

    Attributes:
        id: UUID string, assigned at creation.
        title: Human-readable session title.
        project_id: Optional project link.
        task_id: Optional task link.
        conversation_ids: Ordered list of Conversation IDs in this session.
        status: Current SessionStatus.
        created_at: UTC creation timestamp.
        closed_at: UTC close timestamp; None while open.
        metadata: Arbitrary key-value store for extension without schema changes.
    """

    id: str
    title: str
    project_id: Optional[str]
    task_id: Optional[str]
    conversation_ids: List[str]
    status: SessionStatus
    created_at: datetime
    closed_at: Optional[datetime] = None
    metadata: Dict = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------

    def is_open(self) -> bool:
        return self.status == SessionStatus.OPEN

    def is_reviewing(self) -> bool:
        return self.status == SessionStatus.REVIEWING

    def is_closed(self) -> bool:
        return self.status == SessionStatus.CLOSED

    # ------------------------------------------------------------------
    # Conversation helpers
    # ------------------------------------------------------------------

    def conversation_count(self) -> int:
        return len(self.conversation_ids)

    def has_conversation(self, conversation_id: str) -> bool:
        return conversation_id in self.conversation_ids

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "conversation_ids": list(self.conversation_ids),
            "conversation_count": self.conversation_count(),
            "status": self.status.value,
            "status_label": self.status.label(),
            "created_at": self.created_at.isoformat(),
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "metadata": dict(self.metadata),
        }
