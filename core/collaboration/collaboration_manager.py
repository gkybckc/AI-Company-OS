"""
CollaborationHub — central manager for the Agent Collaboration Hub.

Manages the full lifecycle of Conversations and CollaborationSessions.
Delegates policy enforcement to PolicyEngine.
Builds on top of (but does not replace) the existing Discussion Engine.

No AI, no networking, no async. Pure in-memory orchestration.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from core.collaboration.collaboration_session import CollaborationSession, SessionStatus
from core.collaboration.conversation import Conversation, ConversationStatus
from core.collaboration.conversation_message import ConversationMessage, MessageCategory
from core.collaboration.conversation_participant import ConversationParticipant
from core.collaboration.conversation_policy import (
    ConversationPolicy,
    PolicyEngine,
    PolicyViolation,
)
from core.collaboration.conversation_summary import ConversationSummary
from core.collaboration.conversation_templates import (
    ConversationTemplate,
    TemplateType,
    default_policies,
    get_template,
)


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

class CollaborationHubError(Exception):
    """Base class for all CollaborationHub errors."""


class ConversationNotFoundError(CollaborationHubError):
    """Raised when a conversation_id cannot be resolved."""


class ConversationClosedError(CollaborationHubError):
    """Raised when an operation requires an ACTIVE conversation."""


class ParticipantAlreadyError(CollaborationHubError):
    """Raised when join() is called for an already-admitted participant."""


class ParticipantNotFoundError(CollaborationHubError):
    """Raised when leave() or send_message() references an unknown participant."""


class SessionNotFoundError(CollaborationHubError):
    """Raised when a session_id cannot be resolved."""


class SessionClosedError(CollaborationHubError):
    """Raised when an operation requires an open session."""


class InvalidConversationError(CollaborationHubError):
    """Raised for invalid input to create_conversation() or send_message()."""


# ---------------------------------------------------------------------------
# CollaborationHub
# ---------------------------------------------------------------------------

class CollaborationHub:
    """
    Central manager for agent conversations and collaboration sessions.

    All state is in-memory. The hub is fully isolated and safe to
    instantiate independently in tests without teardown concerns.

    Key design:
      - Conversations hold typed messages (MessageCategory).
      - Sessions group related conversations for a task/sprint.
      - PolicyEngine enforces data-driven governance rules.
      - Templates provide reusable conversation blueprints.
      - Existing Discussion Engine is NOT replaced — it remains the
        formal deliberation system; CollaborationHub handles richer
        multi-party chat-like exchanges.

    Typical usage:
        hub = CollaborationHub()
        # (optional) register default policies
        for policy in default_policies():
            hub.add_policy(policy)

        conv = hub.create_conversation(
            title="Backend API Security Review",
            creator="alice",
            template_type=TemplateType.SECURITY_REVIEW,
        )
        alice = ConversationParticipant("alice", "Alice Chen", "Backend Agent")
        bob   = ConversationParticipant("bob",   "Bob Kumar",  "Security")
        hub.join(conv.id, alice)
        hub.join(conv.id, bob)

        hub.send_message(conv.id, ConversationMessage.create(
            sender="alice", receiver="all",
            category=MessageCategory.PROPOSAL,
            content="Proposing JWT with RS256 for auth tokens.",
        ))
        hub.send_message(conv.id, ConversationMessage.create(
            sender="bob", receiver="alice",
            category=MessageCategory.REVIEW,
            content="RS256 approved. Add token rotation every 24h.",
        ))

        summary = hub.summarize(conv.id)
        hub.close_conversation(conv.id)
    """

    def __init__(self, seed_default_policies: bool = False) -> None:
        self._conversations: Dict[str, Conversation] = {}
        self._sessions: Dict[str, CollaborationSession] = {}
        self._policy_engine: PolicyEngine = PolicyEngine()

        if seed_default_policies:
            for policy in default_policies():
                self._policy_engine.add_policy(policy)

    # ==================================================================
    # Conversation — create / join / leave
    # ==================================================================

    def create_conversation(
        self,
        title: str,
        creator: str,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        template_type: Optional[TemplateType] = None,
    ) -> Conversation:
        """
        Create and register a new ACTIVE Conversation.

        Args:
            title: Non-empty human-readable title.
            creator: participant_id of the creating agent.
            project_id: Optional project link.
            task_id: Optional task link.
            template_type: Optional TemplateType; sets the conversation's
                template_type field used by policy evaluation.

        Returns:
            The new Conversation in ACTIVE status.

        Raises:
            InvalidConversationError: If title or creator is empty.
        """
        if not title or not title.strip():
            raise InvalidConversationError("Conversation title must be non-empty.")
        if not creator or not creator.strip():
            raise InvalidConversationError("Conversation creator must be non-empty.")

        now = datetime.now(timezone.utc)
        conv = Conversation(
            id=str(uuid4()),
            title=title.strip(),
            project_id=project_id,
            task_id=task_id,
            creator=creator,
            participants=[],
            messages=[],
            summary=None,
            created_at=now,
            updated_at=now,
            status=ConversationStatus.ACTIVE,
            template_type=template_type.value if template_type else None,
        )
        self._conversations[conv.id] = conv
        return conv

    def create_from_template(
        self,
        template_type: TemplateType,
        creator: str,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        title_override: Optional[str] = None,
    ) -> Conversation:
        """
        Create a Conversation pre-populated from a built-in template.

        The conversation's title defaults to the template's name.
        The opening message from the template is automatically posted
        as a broadcast PROPOSAL from the creator.

        Args:
            template_type: One of TemplateType.
            creator: participant_id of the creating agent.
            project_id: Optional project link.
            task_id: Optional task link.
            title_override: If provided, use this title instead of the
                template's default name.

        Returns:
            The new Conversation in ACTIVE status with one opening message.

        Raises:
            InvalidConversationError: If creator is empty.
        """
        tmpl = get_template(template_type)
        title = title_override or tmpl.name
        conv = self.create_conversation(
            title=title,
            creator=creator,
            project_id=project_id,
            task_id=task_id,
            template_type=template_type,
        )

        # Post the opening message as a broadcast from creator
        opening = ConversationMessage.create(
            sender=creator,
            receiver="all",
            category=MessageCategory.PROPOSAL,
            content=tmpl.opening_message,
        )
        # Temporarily bypass participant check for the opening message
        conv.messages.append(opening)
        conv.updated_at = opening.timestamp

        return conv

    def join(
        self,
        conversation_id: str,
        participant: ConversationParticipant,
    ) -> Conversation:
        """
        Admit a participant to an ACTIVE conversation.

        Args:
            conversation_id: ID of the target conversation.
            participant: ConversationParticipant to admit. joined_at is
                set to the current UTC time if not already set.

        Returns:
            The updated Conversation.

        Raises:
            ConversationNotFoundError: If conversation_id does not exist.
            ConversationClosedError: If the conversation is CLOSED.
            ParticipantAlreadyError: If the participant is already admitted.
        """
        conv = self._resolve(conversation_id)
        if conv.is_closed():
            raise ConversationClosedError(
                f"Conversation '{conversation_id}' is CLOSED."
            )
        if conv.has_participant(participant.participant_id):
            raise ParticipantAlreadyError(
                f"Participant '{participant.participant_id}' is already "
                f"in conversation '{conversation_id}'."
            )
        if participant.joined_at is None:
            participant.joined_at = datetime.now(timezone.utc)
        conv.participants.append(participant)
        conv.updated_at = datetime.now(timezone.utc)
        return conv

    def leave(
        self,
        conversation_id: str,
        participant_id: str,
    ) -> Conversation:
        """
        Remove a participant from an ACTIVE conversation.

        Message history from the participant is preserved.

        Args:
            conversation_id: ID of the target conversation.
            participant_id: ID of the participant to remove.

        Returns:
            The updated Conversation.

        Raises:
            ConversationNotFoundError: If conversation_id does not exist.
            ConversationClosedError: If the conversation is CLOSED.
            ParticipantNotFoundError: If the participant is not in the conversation.
        """
        conv = self._resolve(conversation_id)
        if conv.is_closed():
            raise ConversationClosedError(
                f"Conversation '{conversation_id}' is CLOSED."
            )
        if not conv.has_participant(participant_id):
            raise ParticipantNotFoundError(
                f"Participant '{participant_id}' is not in "
                f"conversation '{conversation_id}'."
            )
        conv.participants = [
            p for p in conv.participants if p.participant_id != participant_id
        ]
        conv.updated_at = datetime.now(timezone.utc)
        return conv

    # ==================================================================
    # Conversation — messaging
    # ==================================================================

    def send_message(
        self,
        conversation_id: str,
        message: ConversationMessage,
    ) -> Conversation:
        """
        Record a typed message in a conversation.

        The sender must be an admitted participant OR the conversation
        must have at least one participant with any role (to allow the
        creator to send the opening message before joining).

        Args:
            conversation_id: ID of the target conversation.
            message: The ConversationMessage to record. content must be
                non-empty.

        Returns:
            The updated Conversation.

        Raises:
            ConversationNotFoundError: If conversation_id does not exist.
            ConversationClosedError: If the conversation status is CLOSED.
            InvalidConversationError: If message content is empty.
            ParticipantNotFoundError: If sender is not a participant and the
                conversation has at least one participant admitted.
        """
        conv = self._resolve(conversation_id)
        if conv.is_closed():
            raise ConversationClosedError(
                f"Conversation '{conversation_id}' is CLOSED."
            )
        if not message.content or not message.content.strip():
            raise InvalidConversationError(
                "Message content must be non-empty."
            )
        # If there are admitted participants, enforce sender membership
        if conv.participants and not conv.has_participant(message.sender):
            raise ParticipantNotFoundError(
                f"Sender '{message.sender}' is not an admitted participant "
                f"in conversation '{conversation_id}'. Call join() first."
            )
        conv.messages.append(message)
        conv.updated_at = message.timestamp
        return conv

    def broadcast(
        self,
        conversation_id: str,
        sender_id: str,
        category: MessageCategory,
        content: str,
    ) -> Conversation:
        """
        Convenience wrapper — send a broadcast message from sender_id to "all".

        Args:
            conversation_id: ID of the target conversation.
            sender_id: participant_id of the sender.
            category: MessageCategory for the message.
            content: Non-empty message body.

        Returns:
            The updated Conversation.
        """
        msg = ConversationMessage.create(
            sender=sender_id,
            receiver="all",
            category=category,
            content=content,
        )
        return self.send_message(conversation_id, msg)

    # ==================================================================
    # Conversation — summarise / close / status transitions
    # ==================================================================

    def summarize(self, conversation_id: str) -> ConversationSummary:
        """
        Auto-generate and attach a ConversationSummary.

        Works on ACTIVE and PENDING_REVIEW conversations. The summary
        is attached to conversation.summary and returned.

        Args:
            conversation_id: ID of the target conversation.

        Returns:
            The generated ConversationSummary.

        Raises:
            ConversationNotFoundError: If conversation_id does not exist.
        """
        conv = self._resolve(conversation_id)
        summary = ConversationSummary.auto_generate(conv)
        conv.summary = summary
        conv.updated_at = datetime.now(timezone.utc)
        return summary

    def request_review(self, conversation_id: str) -> Conversation:
        """
        Transition an ACTIVE conversation to PENDING_REVIEW.

        Args:
            conversation_id: ID of the target conversation.

        Returns:
            The updated Conversation.

        Raises:
            ConversationNotFoundError: If conversation_id does not exist.
            ConversationClosedError: If the conversation is already CLOSED.
        """
        conv = self._resolve(conversation_id)
        if conv.is_closed():
            raise ConversationClosedError(
                f"Conversation '{conversation_id}' is already CLOSED."
            )
        conv.status = ConversationStatus.PENDING_REVIEW
        conv.updated_at = datetime.now(timezone.utc)
        return conv

    def approve_conversation(self, conversation_id: str) -> Conversation:
        """
        Transition a PENDING_REVIEW conversation to APPROVED.

        Args:
            conversation_id: ID of the target conversation.

        Returns:
            The updated Conversation.

        Raises:
            ConversationNotFoundError: If conversation_id does not exist.
            InvalidConversationError: If the conversation is not PENDING_REVIEW.
        """
        conv = self._resolve(conversation_id)
        if not conv.is_pending_review():
            raise InvalidConversationError(
                f"Conversation '{conversation_id}' is not PENDING_REVIEW "
                f"(status: {conv.status.value})."
            )
        conv.status = ConversationStatus.APPROVED
        conv.updated_at = datetime.now(timezone.utc)
        return conv

    def close_conversation(
        self,
        conversation_id: str,
        summary: Optional[ConversationSummary] = None,
    ) -> Conversation:
        """
        Close a conversation (any non-CLOSED status allowed).

        If summary is provided, it overrides any existing auto-generated
        summary. If not provided and no summary exists, one is auto-generated.

        Args:
            conversation_id: ID of the target conversation.
            summary: Optional ConversationSummary to attach.

        Returns:
            The closed Conversation.

        Raises:
            ConversationNotFoundError: If conversation_id does not exist.
            ConversationClosedError: If already CLOSED.
        """
        conv = self._resolve(conversation_id)
        if conv.is_closed():
            raise ConversationClosedError(
                f"Conversation '{conversation_id}' is already CLOSED."
            )
        if summary is not None:
            conv.summary = summary
        elif conv.summary is None:
            conv.summary = ConversationSummary.auto_generate(conv)
        conv.status = ConversationStatus.CLOSED
        conv.updated_at = datetime.now(timezone.utc)
        return conv

    # ==================================================================
    # Conversation — queries
    # ==================================================================

    def get_conversation(self, conversation_id: str) -> Conversation:
        """Return a conversation by ID."""
        return self._resolve(conversation_id)

    def list_conversations(
        self, status: Optional[ConversationStatus] = None
    ) -> List[Conversation]:
        """
        Return all conversations, optionally filtered by status.

        Results are sorted by updated_at (most recently active first).
        """
        convs = list(self._conversations.values())
        if status is not None:
            convs = [c for c in convs if c.status == status]
        return sorted(convs, key=lambda c: c.updated_at, reverse=True)

    def list_active(self) -> List[Conversation]:
        """Return all ACTIVE conversations."""
        return self.list_conversations(ConversationStatus.ACTIVE)

    def list_pending_review(self) -> List[Conversation]:
        """Return all PENDING_REVIEW conversations."""
        return self.list_conversations(ConversationStatus.PENDING_REVIEW)

    def history(self, conversation_id: str) -> List[ConversationMessage]:
        """Return the full ordered message history for a conversation."""
        conv = self._resolve(conversation_id)
        return list(conv.messages)

    def conversation_count(self) -> int:
        return len(self._conversations)

    # ==================================================================
    # Sessions
    # ==================================================================

    def create_session(
        self,
        title: str,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> CollaborationSession:
        """
        Create and register a new OPEN CollaborationSession.

        Args:
            title: Non-empty session title.
            project_id: Optional project link.
            task_id: Optional task link.

        Returns:
            The new CollaborationSession.

        Raises:
            InvalidConversationError: If title is empty.
        """
        if not title or not title.strip():
            raise InvalidConversationError("Session title must be non-empty.")
        session = CollaborationSession(
            id=str(uuid4()),
            title=title.strip(),
            project_id=project_id,
            task_id=task_id,
            conversation_ids=[],
            status=SessionStatus.OPEN,
            created_at=datetime.now(timezone.utc),
        )
        self._sessions[session.id] = session
        return session

    def add_to_session(
        self, session_id: str, conversation_id: str
    ) -> CollaborationSession:
        """
        Add an existing conversation to a session.

        Args:
            session_id: ID of the CollaborationSession.
            conversation_id: ID of the Conversation to add.

        Returns:
            The updated CollaborationSession.

        Raises:
            SessionNotFoundError: If session_id does not exist.
            SessionClosedError: If the session is CLOSED.
            ConversationNotFoundError: If conversation_id does not exist.
        """
        session = self._resolve_session(session_id)
        if session.is_closed():
            raise SessionClosedError(
                f"Session '{session_id}' is CLOSED."
            )
        self._resolve(conversation_id)  # validate existence
        if not session.has_conversation(conversation_id):
            session.conversation_ids.append(conversation_id)
        return session

    def get_session(self, session_id: str) -> CollaborationSession:
        """Return a session by ID."""
        return self._resolve_session(session_id)

    def list_sessions(
        self, status: Optional[SessionStatus] = None
    ) -> List[CollaborationSession]:
        """Return all sessions, optionally filtered by status, sorted by created_at."""
        sessions = list(self._sessions.values())
        if status is not None:
            sessions = [s for s in sessions if s.status == status]
        return sorted(sessions, key=lambda s: s.created_at, reverse=True)

    def close_session(self, session_id: str) -> CollaborationSession:
        """
        Close an open or reviewing session.

        Args:
            session_id: ID of the session to close.

        Returns:
            The closed CollaborationSession.

        Raises:
            SessionNotFoundError: If session_id does not exist.
            SessionClosedError: If already CLOSED.
        """
        session = self._resolve_session(session_id)
        if session.is_closed():
            raise SessionClosedError(
                f"Session '{session_id}' is already CLOSED."
            )
        session.status = SessionStatus.CLOSED
        session.closed_at = datetime.now(timezone.utc)
        return session

    def session_count(self) -> int:
        return len(self._sessions)

    # ==================================================================
    # Policy management (delegated to PolicyEngine)
    # ==================================================================

    def add_policy(self, policy: ConversationPolicy) -> None:
        """Register a ConversationPolicy with the PolicyEngine."""
        self._policy_engine.add_policy(policy)

    def remove_policy(self, name: str) -> None:
        """Remove a policy by name."""
        self._policy_engine.remove_policy(name)

    def list_policies(self) -> List[ConversationPolicy]:
        """Return all registered policies."""
        return self._policy_engine.list_policies()

    def get_policy(self, name: str) -> ConversationPolicy:
        """Return a policy by name."""
        return self._policy_engine.get_policy(name)

    def evaluate_policies(self, conversation_id: str) -> List[PolicyViolation]:
        """
        Evaluate all policies against the given conversation.

        Args:
            conversation_id: ID of the conversation to evaluate.

        Returns:
            List of PolicyViolation objects (empty if all policies satisfied).
        """
        conv = self._resolve(conversation_id)
        return self._policy_engine.evaluate(conv)

    def has_blocking_violations(self, conversation_id: str) -> bool:
        """True if any blocking policy is violated in this conversation."""
        conv = self._resolve(conversation_id)
        return self._policy_engine.has_blocking_violations(conv)

    # ==================================================================
    # Statistics
    # ==================================================================

    def statistics(self) -> Dict[str, Any]:
        """
        Return a snapshot of the hub's current state.

        Returns:
            Dict with keys:
                total_conversations, active_conversations,
                pending_review_conversations, approved_conversations,
                closed_conversations, total_sessions, open_sessions,
                closed_sessions, total_messages, total_participants,
                total_policies, messages_by_category (dict).
        """
        convs = list(self._conversations.values())
        sessions = list(self._sessions.values())

        total_msgs = sum(c.message_count() for c in convs)
        total_parts = sum(c.participant_count() for c in convs)

        by_cat: Dict[str, int] = {cat.value: 0 for cat in MessageCategory}
        for conv in convs:
            for msg in conv.messages:
                by_cat[msg.category.value] = by_cat.get(msg.category.value, 0) + 1

        return {
            "total_conversations": len(convs),
            "active_conversations": sum(1 for c in convs if c.is_active()),
            "pending_review_conversations": sum(1 for c in convs if c.is_pending_review()),
            "approved_conversations": sum(1 for c in convs if c.is_approved()),
            "closed_conversations": sum(1 for c in convs if c.is_closed()),
            "total_sessions": len(sessions),
            "open_sessions": sum(1 for s in sessions if s.is_open()),
            "closed_sessions": sum(1 for s in sessions if s.is_closed()),
            "total_messages": total_msgs,
            "total_participants": total_parts,
            "total_policies": self._policy_engine.policy_count(),
            "messages_by_category": by_cat,
        }

    # ==================================================================
    # Internal helpers
    # ==================================================================

    def _resolve(self, conversation_id: str) -> Conversation:
        conv = self._conversations.get(conversation_id)
        if conv is None:
            raise ConversationNotFoundError(
                f"No conversation with id '{conversation_id}'."
            )
        return conv

    def _resolve_session(self, session_id: str) -> CollaborationSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(
                f"No session with id '{session_id}'."
            )
        return session
