"""
Discussion Engine for AI Company OS.

The DiscussionEngine is the sole authority for creating, managing, and
closing structured multi-agent deliberations. It enforces the protocol
defined in Constitution Chapter 9: every message must carry a justified
position, every discussion must conclude with a documented outcome, and
no action may be taken on an informal exchange.

The engine is deterministic and stateless with respect to external systems.
It holds all discussion state in memory. It does not call AI, access
networks, perform I/O, or use async constructs.

Lifecycle enforced by this engine:
    start_discussion() → OPEN
    OPEN: join(), leave(), post_message(), summarize(), close()
    CLOSED: reopen(), history(), summarize()
    OPEN (after reopen): join(), leave(), post_message(), close()

Architecture reference: §2.4 Discussion Engine, §3 Layer 5 (Coordination),
constitution Chapter 9 (Discussion Protocol).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from core.discussion import Discussion, DiscussionStatus
from core.discussion_message import DiscussionMessage
from core.discussion_outcome import DiscussionOutcome
from core.discussion_participant import DiscussionParticipant


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

class DiscussionError(Exception):
    """Base class for all Discussion Engine errors."""


class DiscussionNotFoundError(DiscussionError):
    """
    Raised when a discussion_id cannot be resolved in the engine.

    Call start_discussion() to create a discussion before referencing it
    with join(), post_message(), close(), or any other method.
    """


class DiscussionClosedError(DiscussionError):
    """
    Raised when an operation that requires OPEN status is attempted on a
    CLOSED discussion.

    Covers join(), leave(), and post_message(). To resume a closed
    discussion, call reopen() first.
    """


class DiscussionAlreadyOpenError(DiscussionError):
    """
    Raised when reopen() is called on a discussion that is already OPEN.

    A discussion can only be reopened if it is currently CLOSED.
    """


class ParticipantAlreadyInDiscussionError(DiscussionError):
    """
    Raised when join() is called with a participant_id that is already
    admitted to the discussion.

    Each participant may appear at most once in any given discussion.
    """


class ParticipantNotInDiscussionError(DiscussionError):
    """
    Raised when leave() or post_message() references a participant_id that
    is not currently in the discussion's participant roster.

    For post_message(): the sender must be an admitted participant.
    For leave(): the participant must be admitted in order to be removed.
    """


class InvalidMessageError(DiscussionError):
    """
    Raised when post_message() receives a DiscussionMessage with an empty
    opinion or empty reasoning field.

    Both fields are mandatory per the Discussion Protocol. A message without
    a position (opinion) or without a justification (reasoning) is not a
    valid deliberative contribution and will not be recorded.
    """


class InvalidTopicError(DiscussionError):
    """
    Raised when start_discussion() receives an empty or whitespace-only topic.

    Every discussion must have a clear, non-empty topic that defines the
    scope of the deliberation.
    """


class InvalidOutcomeError(DiscussionError):
    """
    Raised when close() receives a DiscussionOutcome with an empty decision
    or empty summary.

    Both fields are mandatory for a valid outcome. The decision and summary
    must be non-empty strings.
    """


# ---------------------------------------------------------------------------
# DiscussionEngine
# ---------------------------------------------------------------------------

class DiscussionEngine:
    """
    Structured deliberation manager for AI Company OS.

    Manages the full lifecycle of Discussion objects: creation, participant
    management, message validation, summarisation, and closing. All state
    is held in-memory; the engine is fully isolated and safe to instantiate
    independently in tests.

    Usage example (standard deliberation flow):
        engine = DiscussionEngine()
        disc = engine.start_discussion(
            topic="Should the API use REST or GraphQL?",
            project_id="proj-saas",
        )
        alice = DiscussionParticipant("alice", "Alice", "Backend Lead", ...)
        bob   = DiscussionParticipant("bob",   "Bob",   "QA Engineer",  ...)
        engine.join(disc.id, alice)
        engine.join(disc.id, bob)

        engine.post_message(disc.id, DiscussionMessage(
            sender="alice", role="Backend Lead",
            opinion="REST is simpler to maintain.",
            reasoning="REST has better tooling and more predictable caching.",
            timestamp=datetime.now(timezone.utc),
        ))
        engine.post_message(disc.id, DiscussionMessage(
            sender="bob", role="QA Engineer",
            opinion="GraphQL reduces over-fetching for our test clients.",
            reasoning="Our integration tests pull many fields from the API.",
            timestamp=datetime.now(timezone.utc),
        ))

        summary = engine.summarize(disc.id)
        outcome = DiscussionOutcome(
            decision="Use REST for external API, GraphQL for internal tooling.",
            summary="REST preferred for maintainability; GraphQL approved for internal clients.",
            agreed_actions=["Implement REST endpoints first", "Evaluate GraphQL in Sprint 15"],
            unresolved_points=["Subscription support not yet decided"],
        )
        engine.close(disc.id, outcome)
    """

    def __init__(self) -> None:
        self._discussions: Dict[str, Discussion] = {}

    # ------------------------------------------------------------------
    # Command methods
    # ------------------------------------------------------------------

    def start_discussion(
        self,
        topic: str,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        creator: Optional[DiscussionParticipant] = None,
    ) -> Discussion:
        """
        Create and register a new discussion in OPEN state.

        If a creator participant is provided, they are immediately admitted
        to the discussion (equivalent to calling join() after start).

        Args:
            topic: Non-empty string defining the question or decision under
                deliberation. All messages should address this topic.
            project_id: Optional project this discussion is part of.
            task_id: Optional task that triggered this discussion.
            creator: Optional DiscussionParticipant to admit as the first
                participant. Convenience parameter — equivalent to calling
                join() after start().

        Returns:
            The newly created Discussion in OPEN state.

        Raises:
            InvalidTopicError: If topic is empty or whitespace-only.
        """
        if not topic or not topic.strip():
            raise InvalidTopicError(
                "Discussion topic must be a non-empty string. "
                "Every discussion must have a defined scope."
            )

        now = datetime.now(timezone.utc)
        participants: List[DiscussionParticipant] = []

        if creator is not None:
            if creator.joined_at is None:
                creator.joined_at = now
            participants.append(creator)

        discussion = Discussion(
            id=str(uuid4()),
            topic=topic,
            project_id=project_id,
            task_id=task_id,
            participants=participants,
            status=DiscussionStatus.OPEN,
            created_at=now,
        )
        self._discussions[discussion.id] = discussion
        return discussion

    def join(
        self,
        discussion_id: str,
        participant: DiscussionParticipant,
    ) -> Discussion:
        """
        Admit a participant to an open discussion.

        Args:
            discussion_id: ID of the target discussion.
            participant: The DiscussionParticipant to admit. joined_at is
                set to the current UTC time by the engine if it is None.

        Returns:
            The updated Discussion with the new participant admitted.

        Raises:
            DiscussionNotFoundError: If discussion_id does not exist.
            DiscussionClosedError: If the discussion is CLOSED.
            ParticipantAlreadyInDiscussionError: If a participant with this
                participant_id is already in the discussion.
        """
        discussion = self._resolve(discussion_id)
        self._require_open(discussion)

        if discussion.has_participant(participant.participant_id):
            raise ParticipantAlreadyInDiscussionError(
                f"Participant '{participant.participant_id}' is already "
                f"in discussion '{discussion_id}'."
            )

        if participant.joined_at is None:
            participant.joined_at = datetime.now(timezone.utc)

        discussion.participants.append(participant)
        return discussion

    def leave(
        self,
        discussion_id: str,
        participant_id: str,
    ) -> Discussion:
        """
        Remove a participant from an open discussion.

        Removing a participant does not delete their posted messages —
        the message history is permanent. The participant will no longer
        be able to post new messages unless they rejoin.

        Args:
            discussion_id: ID of the target discussion.
            participant_id: ID of the participant to remove.

        Returns:
            The updated Discussion with the participant removed.

        Raises:
            DiscussionNotFoundError: If discussion_id does not exist.
            DiscussionClosedError: If the discussion is CLOSED.
            ParticipantNotInDiscussionError: If the participant is not
                currently in the discussion.
        """
        discussion = self._resolve(discussion_id)
        self._require_open(discussion)

        if not discussion.has_participant(participant_id):
            raise ParticipantNotInDiscussionError(
                f"Participant '{participant_id}' is not in "
                f"discussion '{discussion_id}'."
            )

        discussion.participants = [
            p for p in discussion.participants
            if p.participant_id != participant_id
        ]
        return discussion

    def post_message(
        self,
        discussion_id: str,
        message: DiscussionMessage,
    ) -> Discussion:
        """
        Record a structured message in an open discussion.

        The engine validates:
        1. The discussion exists and is OPEN.
        2. The message's opinion field is non-empty.
        3. The message's reasoning field is non-empty.
        4. The message's sender is a currently admitted participant.

        Args:
            discussion_id: ID of the target discussion.
            message: The DiscussionMessage to record.

        Returns:
            The updated Discussion with the message appended.

        Raises:
            DiscussionNotFoundError: If discussion_id does not exist.
            DiscussionClosedError: If the discussion is CLOSED.
            InvalidMessageError: If opinion or reasoning is empty.
            ParticipantNotInDiscussionError: If the sender is not a
                currently admitted participant.
        """
        discussion = self._resolve(discussion_id)
        self._require_open(discussion)

        if not message.opinion or not message.opinion.strip():
            raise InvalidMessageError(
                "DiscussionMessage.opinion must be non-empty. "
                "Every message must state a position on the topic."
            )
        if not message.reasoning or not message.reasoning.strip():
            raise InvalidMessageError(
                "DiscussionMessage.reasoning must be non-empty. "
                "Every message must justify its position."
            )
        if not discussion.has_participant(message.sender):
            raise ParticipantNotInDiscussionError(
                f"Sender '{message.sender}' is not an admitted participant "
                f"in discussion '{discussion_id}'. "
                f"Call join() before posting."
            )

        discussion.messages.append(message)
        return discussion

    def summarize(self, discussion_id: str) -> str:
        """
        Produce a deterministic, structured textual summary of the discussion.

        The summary is generated from the message history without AI.
        It includes the topic, status, participant roster, each participant's
        recorded positions, and the current outcome (if closed). The output
        is consistent: given the same discussion state, the summary is
        identical every time.

        Works on both OPEN and CLOSED discussions.

        Args:
            discussion_id: ID of the discussion to summarise.

        Returns:
            A multi-line string summary of the discussion state.

        Raises:
            DiscussionNotFoundError: If discussion_id does not exist.
        """
        discussion = self._resolve(discussion_id)
        lines: List[str] = []

        lines.append(f"DISCUSSION SUMMARY")
        lines.append(f"Topic   : {discussion.topic}")
        lines.append(f"Status  : {discussion.status}")
        lines.append(f"Participants ({discussion.participant_count()}): "
                     + (", ".join(p.name for p in discussion.participants)
                        if discussion.participants else "none"))
        lines.append(f"Messages: {discussion.message_count()}")

        if discussion.messages:
            lines.append("--- Positions ---")
            opinion_map = discussion.opinion_map()
            for pid, opinions in opinion_map.items():
                participant = discussion.get_participant(pid)
                display = participant.name if participant else pid
                role = participant.role if participant else "unknown"
                for i, op in enumerate(opinions, 1):
                    prefix = f"  [{display} / {role}]"
                    if len(opinions) > 1:
                        prefix += f" ({i}/{len(opinions)})"
                    lines.append(f"{prefix}: {op}")
        else:
            lines.append("--- No messages posted yet ---")

        if discussion.outcome:
            lines.append("--- Outcome ---")
            lines.append(f"Decision  : {discussion.outcome.decision}")
            lines.append(f"Summary   : {discussion.outcome.summary}")
            if discussion.outcome.agreed_actions:
                lines.append("Agreed actions:")
                for action in discussion.outcome.agreed_actions:
                    lines.append(f"  • {action}")
            if discussion.outcome.unresolved_points:
                lines.append("Unresolved:")
                for point in discussion.outcome.unresolved_points:
                    lines.append(f"  ? {point}")

        return "\n".join(lines)

    def close(
        self,
        discussion_id: str,
        outcome: DiscussionOutcome,
    ) -> Discussion:
        """
        Close an open discussion with a formal outcome.

        The discussion transitions from OPEN to CLOSED. No further
        messages may be posted unless the discussion is reopened.

        The outcome's decided_at is set to the current UTC time by the
        engine if it is None.

        Args:
            discussion_id: ID of the discussion to close.
            outcome: The DiscussionOutcome recording the conclusion.
                decision and summary must be non-empty strings.

        Returns:
            The closed Discussion with the outcome attached.

        Raises:
            DiscussionNotFoundError: If discussion_id does not exist.
            DiscussionClosedError: If the discussion is already CLOSED.
            InvalidOutcomeError: If outcome.decision or outcome.summary
                is empty or whitespace-only.
        """
        discussion = self._resolve(discussion_id)
        self._require_open(discussion)

        if not outcome.decision or not outcome.decision.strip():
            raise InvalidOutcomeError(
                "DiscussionOutcome.decision must be non-empty. "
                "Every outcome must state a clear decision."
            )
        if not outcome.summary or not outcome.summary.strip():
            raise InvalidOutcomeError(
                "DiscussionOutcome.summary must be non-empty. "
                "Every outcome must include a summary of the deliberation."
            )

        now = datetime.now(timezone.utc)

        if outcome.decided_at is None:
            outcome = DiscussionOutcome(
                decision=outcome.decision,
                summary=outcome.summary,
                agreed_actions=list(outcome.agreed_actions),
                unresolved_points=list(outcome.unresolved_points),
                decided_at=now,
                decided_by=outcome.decided_by,
            )

        discussion.status = DiscussionStatus.CLOSED
        discussion.closed_at = now
        discussion.outcome = outcome
        return discussion

    def reopen(
        self,
        discussion_id: str,
        reason: str = "",
    ) -> Discussion:
        """
        Reopen a closed discussion for continued deliberation.

        The discussion transitions from CLOSED back to OPEN. The previous
        outcome is cleared — the message history is preserved. A new
        close() call with a new outcome is required to conclude the
        discussion again.

        Args:
            discussion_id: ID of the discussion to reopen.
            reason: Optional human-readable reason for reopening.

        Returns:
            The reopened Discussion in OPEN state, with outcome cleared.

        Raises:
            DiscussionNotFoundError: If discussion_id does not exist.
            DiscussionAlreadyOpenError: If the discussion is already OPEN.
        """
        discussion = self._resolve(discussion_id)

        if discussion.is_open():
            raise DiscussionAlreadyOpenError(
                f"Discussion '{discussion_id}' is already OPEN. "
                f"Only CLOSED discussions can be reopened."
            )

        discussion.status = DiscussionStatus.OPEN
        discussion.closed_at = None
        discussion.outcome = None
        return discussion

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def history(self, discussion_id: str) -> List[DiscussionMessage]:
        """
        Return the complete ordered message history for a discussion.

        Works on both OPEN and CLOSED discussions.

        Args:
            discussion_id: ID of the discussion.

        Returns:
            Shallow copy of the message list (oldest message first).

        Raises:
            DiscussionNotFoundError: If discussion_id does not exist.
        """
        discussion = self._resolve(discussion_id)
        return list(discussion.messages)

    def find(self, discussion_id: str) -> Discussion:
        """
        Return a discussion by ID.

        Args:
            discussion_id: The id to look up.

        Returns:
            The Discussion with the given ID.

        Raises:
            DiscussionNotFoundError: If no discussion with this id exists.
        """
        return self._resolve(discussion_id)

    def list_open(self) -> List[Discussion]:
        """
        Return all OPEN discussions, sorted by created_at (oldest first).

        Returns:
            Shallow copy of the list of open Discussion objects.
        """
        return sorted(
            [d for d in self._discussions.values() if d.is_open()],
            key=lambda d: d.created_at,
        )

    def list_closed(self) -> List[Discussion]:
        """
        Return all CLOSED discussions, sorted by closed_at (oldest first).

        Returns:
            Shallow copy of the list of closed Discussion objects.
        """
        return sorted(
            [d for d in self._discussions.values() if d.is_closed()],
            key=lambda d: (d.closed_at or d.created_at),
        )

    def count(self) -> int:
        """Return the total number of discussions managed by this engine."""
        return len(self._discussions)

    def statistics(self) -> Dict[str, Any]:
        """
        Return a snapshot of the engine's current state.

        Returns:
            Dict with keys: total, open_count, closed_count,
            total_messages, total_participants (current active),
            discussions_with_outcomes, average_messages_per_discussion.
        """
        total = len(self._discussions)
        open_count = sum(1 for d in self._discussions.values() if d.is_open())
        closed_count = total - open_count
        total_messages = sum(d.message_count() for d in self._discussions.values())
        total_participants = sum(
            d.participant_count() for d in self._discussions.values()
        )
        with_outcomes = sum(
            1 for d in self._discussions.values() if d.has_outcome()
        )
        avg_messages = total_messages / total if total > 0 else 0.0

        return {
            "total": total,
            "open_count": open_count,
            "closed_count": closed_count,
            "total_messages": total_messages,
            "total_participants": total_participants,
            "discussions_with_outcomes": with_outcomes,
            "average_messages_per_discussion": avg_messages,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve(self, discussion_id: str) -> Discussion:
        """
        Return the discussion with the given ID or raise DiscussionNotFoundError.

        Raises:
            DiscussionNotFoundError: If discussion_id is not in _discussions.
        """
        discussion = self._discussions.get(discussion_id)
        if discussion is None:
            raise DiscussionNotFoundError(
                f"No discussion with id '{discussion_id}' found in this engine."
            )
        return discussion

    def _require_open(self, discussion: Discussion) -> None:
        """
        Raise DiscussionClosedError if the discussion is not OPEN.

        Raises:
            DiscussionClosedError: If discussion.status is CLOSED.
        """
        if discussion.is_closed():
            raise DiscussionClosedError(
                f"Discussion '{discussion.id}' is CLOSED. "
                f"Call reopen() to resume deliberation."
            )
