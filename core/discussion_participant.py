"""
Discussion participant model for AI Company OS.

A DiscussionParticipant represents one agent, director, or component that
has been admitted to a specific Discussion by the DiscussionEngine. The
participant record captures identity and role at the moment of joining —
it is not a live reference to the Employee or Director objects in the
workforce system.

One agent may participate in many discussions concurrently. Joining a
discussion creates a new DiscussionParticipant record for that specific
discussion context; it does not alter any other system state.

Architecture reference: §2.4 Discussion Engine, §3 Layer 5 (Coordination),
constitution Chapter 9 (Discussion Protocol).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class DiscussionParticipant:
    """
    Record of a single participant's membership in a Discussion.

    Created by the caller and passed to DiscussionEngine.join(). The
    engine validates the participant and registers them in the discussion.
    The record is mutable only by the engine; external code should treat
    it as read-only once registered.

    Attributes:
        participant_id: Unique identifier for this participant within the
            system — typically the employee ID from WorkforceRegistry, a
            director ID, or a named subsystem (e.g., "executive_engine").
            Used by the engine to validate message senders and to enforce
            one-participant-per-id uniqueness within a discussion.
        name: Human-readable display name (e.g., "Alice — Backend Lead").
            Used in discussion summaries and history rendering.
        role: The organizational role this participant holds at the time
            of joining. Captured here so the discussion record remains
            interpretable even if the participant's role changes later.
            Typically matches the EmployeeRole string value for agent
            participants, or "Director", "Executive AI", etc. for senior
            participants.
        joined_at: UTC timestamp of when this participant was admitted to
            the discussion. Set by the DiscussionEngine on join().
    """

    participant_id: str
    name: str
    role: str
    joined_at: Optional[datetime] = None

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DiscussionParticipant):
            return self.participant_id == other.participant_id
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.participant_id)

    def __repr__(self) -> str:
        return (
            f"DiscussionParticipant("
            f"id={self.participant_id!r}, "
            f"name={self.name!r}, "
            f"role={self.role!r})"
        )
