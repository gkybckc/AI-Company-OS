"""
Discussion model and status taxonomy for AI Company OS.

The Discussion is the primary entity managed by the DiscussionEngine.
It holds all state for one deliberation session: the topic, the roster of
admitted participants, the ordered message history, the lifecycle status,
and (once closed) the formal outcome.

DiscussionStatus is defined here alongside Discussion because the two are
semantically inseparable — every operation on a Discussion depends on
its status, and the status is meaningful only in the context of a Discussion.

Architecture reference: §2.4 Discussion Engine, §3 Layer 5 (Coordination),
constitution Chapter 9 (Discussion Protocol).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from core.discussion_message import DiscussionMessage
from core.discussion_outcome import DiscussionOutcome
from core.discussion_participant import DiscussionParticipant


class DiscussionStatus(str, Enum):
    """
    Lifecycle states for a Discussion.

    OPEN    — The discussion is active. Participants may join, leave, and
              post messages. The DiscussionEngine accepts post_message(),
              join(), and leave() only when OPEN.

    CLOSED  — The discussion has concluded. An outcome has been recorded.
              The discussion is a read-only historical record. To continue
              deliberation, the discussion must be reopened via reopen().
    """

    OPEN = "OPEN"
    CLOSED = "CLOSED"

    def __str__(self) -> str:
        return self.value


@dataclass
class Discussion:
    """
    Live record of one structured deliberation session.

    Managed exclusively by the DiscussionEngine. External code should
    read discussion state through the engine's query methods and mutate
    it only through the engine's command methods.

    The Discussion is mutable — participants join and leave, messages are
    appended, status transitions between OPEN and CLOSED — but the id,
    topic, project_id, task_id, and created_at are fixed at creation and
    never change.

    Attributes:
        id: Unique identifier (UUID string). Assigned by the engine.
        topic: The question or decision under deliberation. Non-empty.
            Defines the scope — all messages should address this topic.
        project_id: Optional project this discussion belongs to. Links
            the discussion to a project in the WorkflowEngine.
        task_id: Optional task that triggered this discussion. Links the
            discussion to a specific unit of work.
        participants: List of DiscussionParticipant records for all agents
            currently admitted to this discussion. Ordered by join time
            (oldest first). Participants who have left are not present.
        status: Current lifecycle status. OPEN or CLOSED.
        created_at: UTC timestamp of when the discussion was created.
        closed_at: UTC timestamp of when the discussion was most recently
            closed. None while OPEN. Set by close(), cleared by reopen().
        outcome: The formal DiscussionOutcome recorded at close() time.
            None while OPEN or after reopen(). Set by close().
        messages: Ordered list of DiscussionMessage records, oldest first.
            Append-only — no message is ever edited or removed.
    """

    id: str
    topic: str
    project_id: Optional[str]
    task_id: Optional[str]
    participants: List[DiscussionParticipant]
    status: DiscussionStatus
    created_at: datetime
    closed_at: Optional[datetime] = None
    outcome: Optional[DiscussionOutcome] = None
    messages: List[DiscussionMessage] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------

    def is_open(self) -> bool:
        """Return True if the discussion is currently OPEN."""
        return self.status == DiscussionStatus.OPEN

    def is_closed(self) -> bool:
        """Return True if the discussion is currently CLOSED."""
        return self.status == DiscussionStatus.CLOSED

    # ------------------------------------------------------------------
    # Participant helpers
    # ------------------------------------------------------------------

    def participant_count(self) -> int:
        """Return the number of currently admitted participants."""
        return len(self.participants)

    def participant_ids(self) -> List[str]:
        """Return a list of all current participant IDs."""
        return [p.participant_id for p in self.participants]

    def has_participant(self, participant_id: str) -> bool:
        """
        Return True if a participant with the given ID is currently admitted.

        Args:
            participant_id: The ID to check.

        Returns:
            True if the ID appears in the current participant roster.
        """
        return any(p.participant_id == participant_id for p in self.participants)

    def get_participant(self, participant_id: str) -> Optional[DiscussionParticipant]:
        """
        Return the DiscussionParticipant with the given ID, or None.

        Args:
            participant_id: The ID to look up.

        Returns:
            The matching DiscussionParticipant, or None if not found.
        """
        return next(
            (p for p in self.participants if p.participant_id == participant_id),
            None,
        )

    # ------------------------------------------------------------------
    # Message helpers
    # ------------------------------------------------------------------

    def message_count(self) -> int:
        """Return the total number of messages in this discussion."""
        return len(self.messages)

    def messages_by(self, participant_id: str) -> List[DiscussionMessage]:
        """
        Return all messages posted by the given participant.

        Args:
            participant_id: Filter messages by this sender ID.

        Returns:
            Ordered list (oldest first) of messages from this sender.
        """
        return [m for m in self.messages if m.sender == participant_id]

    def last_message(self) -> Optional[DiscussionMessage]:
        """Return the most recent message, or None if no messages exist."""
        return self.messages[-1] if self.messages else None

    def opinion_map(self) -> Dict[str, List[str]]:
        """
        Return a mapping of participant_id → list of opinions.

        Useful for summarisation and for detecting convergence or divergence.

        Returns:
            Dict where each key is a sender ID and each value is the
            ordered list of opinions that sender has expressed.
        """
        result: Dict[str, List[str]] = {}
        for msg in self.messages:
            result.setdefault(msg.sender, []).append(msg.opinion)
        return result

    def has_outcome(self) -> bool:
        """Return True if a DiscussionOutcome has been recorded."""
        return self.outcome is not None
