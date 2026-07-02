"""
core/collaboration — Agent Collaboration Hub (Feature 21)

Provides real multi-agent conversation infrastructure built on top of the
existing Discussion Engine. Agents discuss, review, question, agree,
disagree, and propose improvements through typed, structured messages
governed by data-driven policies.

Public surface (everything you need to import):

    from core.collaboration.conversation_participant import ConversationParticipant
    from core.collaboration.conversation_message import ConversationMessage, MessageCategory
    from core.collaboration.conversation_summary import ConversationSummary
    from core.collaboration.conversation import Conversation, ConversationStatus
    from core.collaboration.collaboration_session import CollaborationSession, SessionStatus
    from core.collaboration.conversation_policy import ConversationPolicy, PolicyEngine, PolicyViolation
    from core.collaboration.conversation_templates import ConversationTemplate, TemplateType, BUILT_IN_TEMPLATES
    from core.collaboration.collaboration_manager import (
        CollaborationHub,
        CollaborationHubError, ConversationNotFoundError,
        ConversationClosedError, ParticipantAlreadyError,
        ParticipantNotFoundError, SessionNotFoundError,
    )
"""
