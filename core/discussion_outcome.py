"""
Discussion outcome model for AI Company OS.

A DiscussionOutcome is the formal record of what a Discussion concluded.
It is produced by the caller (typically the Discussion facilitator or the
Executive Engine) and passed to DiscussionEngine.close(). It captures the
decision reached, a summary of the deliberation, the actions all parties
agreed to, and any points that remain unresolved.

An outcome is immutable. If the Discussion is reopened (via reopen()), the
previous outcome is cleared — it becomes part of the session history (via
events in future sprints) but is no longer the current outcome. A new close()
with a new outcome is required when the discussion concludes again.

Architecture reference: §2.4 Discussion Engine, §3 Layer 5 (Coordination),
constitution Chapter 9 (Discussion Protocol — every discussion must conclude
with a documented outcome before its conclusions carry authority).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass(frozen=True)
class DiscussionOutcome:
    """
    Immutable record of the conclusions reached in a Discussion.

    Passed to DiscussionEngine.close() by the discussion facilitator.
    The engine attaches it to the Discussion and transitions the
    discussion to CLOSED state. The outcome is the authoritative record
    of the deliberation result — it is what the Executive Engine and
    Approval Engine act upon.

    Attributes:
        decision: The authoritative conclusion reached by the discussion.
            A clear, unambiguous statement of what was decided. This is
            the primary output that subsequent engines consume. Must be
            a non-empty string.
        summary: A concise narrative of how the discussion arrived at the
            decision — the key arguments, the positions that converged,
            and the reasoning that prevailed. Included in CEO-facing
            status reports. Should be one to three sentences.
        agreed_actions: The specific, actionable commitments that all
            participants agreed to follow from this decision. Each item
            is a discrete action with a clear owner (implicit in context).
            May be empty if the decision itself defines the action.
        unresolved_points: Topics or concerns that the discussion could
            not resolve and that require further attention. These are not
            failures — they are honest acknowledgements of what is still
            open. The Approval Engine may flag discussions with many
            unresolved points for elevated review. May be empty if all
            concerns were addressed.
        decided_at: UTC timestamp of when this outcome was recorded by
            the DiscussionEngine (at close() time). Set by the engine.
        decided_by: Identifier of the participant or system that facilitated
            the closing of the discussion and produced this outcome.
            Optional — None if not tracked by the caller.
    """

    decision: str
    summary: str
    agreed_actions: List[str] = field(default_factory=list)
    unresolved_points: List[str] = field(default_factory=list)
    decided_at: Optional[datetime] = None
    decided_by: Optional[str] = None

    def is_fully_resolved(self) -> bool:
        """
        Return True if no unresolved points remain.

        Returns:
            True if unresolved_points is empty.
        """
        return len(self.unresolved_points) == 0

    def action_count(self) -> int:
        """Return the number of agreed actions."""
        return len(self.agreed_actions)

    def unresolved_count(self) -> int:
        """Return the number of unresolved points."""
        return len(self.unresolved_points)

    def has_actions(self) -> bool:
        """Return True if at least one agreed action was recorded."""
        return len(self.agreed_actions) > 0
