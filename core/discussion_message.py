"""
Discussion message model for AI Company OS.

A DiscussionMessage is the atomic unit of structured communication within
a Discussion. Every message MUST include both an opinion (a position) and
reasoning (the justification for that position). Messages without both
fields are rejected by the DiscussionEngine.

This is not a free-form chat message. It is a formal deliberative
contribution — the agent is required to state a position AND explain why
they hold it. This design enforces the Discussion Engine's purpose: to
produce structured, reasoned debate, not informal conversation.

Architecture reference: §2.4 Discussion Engine, §3 Layer 5 (Coordination),
constitution Chapter 9 (Discussion Protocol — every position must be justified).
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DiscussionMessage:
    """
    Immutable record of one participant's structured contribution to a Discussion.

    Created by the caller and posted via DiscussionEngine.post_message().
    The engine validates that both opinion and reasoning are non-empty, and
    that the sender is a current participant, before recording the message.

    Messages are immutable once recorded. The discussion's message list is
    append-only — no message may be edited or deleted. This is the
    authoritative historical record of the deliberation.

    Attributes:
        sender: The participant_id of the agent submitting this message.
            The DiscussionEngine validates that this sender is a registered
            and currently active participant in the discussion before
            accepting the message.
        role: The organizational role of the sender at the time of
            submission. Captured in the message so the role context is
            preserved in the historical record even if the participant's
            role changes later.
        opinion: The participant's position on the discussion topic.
            Must be a non-empty string. This is the "what" — the conclusion
            the participant has reached. Examples: "We should use REST",
            "The current approach has unacceptable security risk", "I
            support Option B with the proposed modifications."
        reasoning: The justification for the opinion. Must be a non-empty
            string. This is the "why" — the evidence, analysis, or
            principle behind the position. The Discussion Engine will not
            accept a message without reasoning; an opinion without
            justification carries no deliberative weight.
        timestamp: UTC timestamp of when this message was posted.
            Set by the DiscussionEngine; callers provide this value.
    """

    sender: str
    role: str
    opinion: str
    reasoning: str
    timestamp: datetime

    def is_from(self, participant_id: str) -> bool:
        """
        Return True if this message was sent by the given participant.

        Args:
            participant_id: The ID to compare against this message's sender.

        Returns:
            True if sender matches participant_id.
        """
        return self.sender == participant_id

    def has_strong_reasoning(self, min_length: int = 20) -> bool:
        """
        Return True if the reasoning exceeds the minimum length threshold.

        A simple heuristic for whether the reasoning field contains
        substantive content rather than a minimal acknowledgement.

        Args:
            min_length: Minimum character count for "strong" reasoning.
                Default: 20.

        Returns:
            True if len(reasoning) >= min_length.
        """
        return len(self.reasoning) >= min_length
