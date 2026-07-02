"""
ConversationSummary — structured conclusion record for a Conversation.

Captures key decisions, open questions, risks, recommendations, and an
executive-level one-paragraph summary that CEOs can read without raw JSON.
No AI, no networking, no async.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List


@dataclass
class ConversationSummary:
    """
    Structured outcome of a Conversation.

    Created by CollaborationHub.summarize() or supplied manually when
    closing a conversation. Designed so the executive_summary field
    can be shown directly in the CEO Briefing without further processing.

    Attributes:
        key_decisions: Binding decisions that emerged from the conversation.
        open_questions: Questions that were raised but not answered.
        risks: Risks identified during the conversation.
        recommendations: Actionable recommendations for next steps.
        executive_summary: One-paragraph human-readable summary for CEO.
        generated_at: UTC timestamp of when this summary was produced.
    """

    key_decisions: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    executive_summary: str = ""
    generated_at: datetime = field(default_factory=lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc))

    # ------------------------------------------------------------------
    # Predicates
    # ------------------------------------------------------------------

    def has_open_items(self) -> bool:
        """True if there are unresolved questions or unaddressed risks."""
        return bool(self.open_questions or self.risks)

    def is_complete(self) -> bool:
        """True if the summary has an executive summary and at least one decision."""
        return bool(self.executive_summary.strip() and self.key_decisions)

    def total_items(self) -> int:
        """Total number of items across all categories."""
        return (
            len(self.key_decisions)
            + len(self.open_questions)
            + len(self.risks)
            + len(self.recommendations)
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict:
        return {
            "key_decisions": list(self.key_decisions),
            "open_questions": list(self.open_questions),
            "risks": list(self.risks),
            "recommendations": list(self.recommendations),
            "executive_summary": self.executive_summary,
            "generated_at": self.generated_at.isoformat(),
            "has_open_items": self.has_open_items(),
            "is_complete": self.is_complete(),
            "total_items": self.total_items(),
        }

    @classmethod
    def empty(cls) -> "ConversationSummary":
        """Return an empty (placeholder) summary."""
        from datetime import timezone
        return cls(generated_at=datetime.now(timezone.utc))

    @classmethod
    def auto_generate(cls, conversation: "Any") -> "ConversationSummary":
        """
        Produce a deterministic summary from a Conversation without AI.

        Reads the message history and categorises content by MessageCategory:
          - DECISION messages   → key_decisions
          - RISK messages       → risks
          - QUESTION messages without a following ANSWER → open_questions
          - PROPOSAL messages   → recommendations
          - everything else     → executive_summary paragraph

        Args:
            conversation: A Conversation instance.

        Returns:
            A ConversationSummary derived from the message history.
        """
        from datetime import timezone
        from core.collaboration.conversation_message import MessageCategory

        decisions: List[str] = []
        open_qs: List[str] = []
        risks: List[str] = []
        recommendations: List[str] = []
        other_lines: List[str] = []

        answered_questions = set()
        question_map = {}

        for msg in conversation.messages:
            if msg.category == MessageCategory.ANSWER:
                # mark the most recent unanswered question as answered
                for qid, qmsg in list(question_map.items()):
                    if qid not in answered_questions:
                        if msg.is_directed_to(qmsg.sender) or msg.is_broadcast():
                            answered_questions.add(qid)
                            break

        for msg in conversation.messages:
            cat = msg.category
            snippet = msg.content[:120].strip()
            if cat == MessageCategory.DECISION:
                decisions.append(f"[{msg.sender}] {snippet}")
            elif cat == MessageCategory.RISK:
                risks.append(f"[{msg.sender}] {snippet}")
            elif cat == MessageCategory.QUESTION:
                question_map[msg.id] = msg
            elif cat == MessageCategory.PROPOSAL:
                recommendations.append(f"[{msg.sender}] {snippet}")
            else:
                other_lines.append(f"[{msg.sender}/{cat.value}] {snippet}")

        for qid, qmsg in question_map.items():
            if qid not in answered_questions:
                open_qs.append(f"[{qmsg.sender}] {qmsg.content[:100].strip()}")

        parts = [f"Conversation: '{conversation.title}'."]
        parts.append(f"{len(conversation.participants)} participant(s), "
                     f"{conversation.message_count()} message(s).")
        if decisions:
            parts.append(f"{len(decisions)} decision(s) recorded.")
        if risks:
            parts.append(f"{len(risks)} risk(s) identified.")
        if open_qs:
            parts.append(f"{len(open_qs)} open question(s) remain.")
        if recommendations:
            parts.append(f"{len(recommendations)} proposal(s) made.")

        return cls(
            key_decisions=decisions,
            open_questions=open_qs,
            risks=risks,
            recommendations=recommendations,
            executive_summary=" ".join(parts),
            generated_at=datetime.now(timezone.utc),
        )


from typing import Any  # noqa: E402
