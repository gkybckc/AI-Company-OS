"""
Decision result model for AI Company OS.

A DecisionResult is the immutable output of the Decision Engine's
recommendation pipeline. It names the selected option, explains the
reasoning, quantifies confidence, and signals whether the CEO must approve
before the recommendation can be acted upon.

The Decision Engine NEVER approves decisions. It only recommends. The CEO
retains sole authority over strategic decisions (Constitution §15,
Architecture §2.4). The requires_ceo_approval flag communicates this
constraint to downstream components.

Architecture reference: §2.4 Decision Engine, §3 Layer 2 (Business Logic),
Constitution §15 (CEO authority), §7.5 (decisions are recorded).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

from core.decision_option import DecisionOption


@dataclass(frozen=True)
class DecisionResult:
    """
    Immutable record of the Decision Engine's recommendation for a Decision.

    Produced by DecisionEngine.recommend() after the engine has scored all
    options against the active rules and identified the winning option.

    The result is a recommendation only — it does not constitute approval or
    authorisation. For decisions whose recommended option carries HIGH or
    CRITICAL risk, requires_ceo_approval is True and the CEO must explicitly
    approve before any action is taken.

    Attributes:
        selected_option:        The option the engine recommends. This is the
                                option that achieved the highest total weighted
                                score across all applied rules.
        reasoning:              Deterministic, human-readable explanation of
                                why this option was selected. Includes the
                                option's score, runner-up score, rules applied,
                                and confidence level. Generated without AI.
        confidence:             Float in [0.5, 1.0] quantifying how clearly
                                the winning option outscored the alternatives.
                                0.5 = tie or single option;
                                1.0 = decisive single winner.
        requires_ceo_approval:  True if the recommended option's estimated_risk
                                is HIGH or CRITICAL, meaning the CEO must
                                approve before the recommendation is acted upon.
        evaluated_at:           UTC timestamp when this result was produced.
        supporting_memory:      List of MemoryEntry IDs from the Memory Engine
                                that are relevant to the decision (may be empty
                                if no Memory Engine is attached or no entries
                                exist for the project).
        supporting_discussions: List of Discussion IDs from the Discussion
                                Engine that were considered during evaluation
                                (may be empty).
    """

    selected_option: DecisionOption
    reasoning: str
    confidence: float
    requires_ceo_approval: bool
    evaluated_at: datetime
    supporting_memory: List[str] = field(default_factory=list)
    supporting_discussions: List[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Confidence helpers
    # ------------------------------------------------------------------

    def is_high_confidence(self) -> bool:
        """Return True if confidence is at or above 0.8."""
        return self.confidence >= 0.8

    def is_low_confidence(self) -> bool:
        """Return True if confidence is at or below 0.6."""
        return self.confidence <= 0.6

    # ------------------------------------------------------------------
    # Evidence helpers
    # ------------------------------------------------------------------

    def has_supporting_evidence(self) -> bool:
        """Return True if any supporting memory or discussion IDs are referenced."""
        return bool(self.supporting_memory) or bool(self.supporting_discussions)

    def supporting_evidence_count(self) -> int:
        """Return total count of referenced supporting memory and discussions."""
        return len(self.supporting_memory) + len(self.supporting_discussions)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        """Return a compact dict suitable for reports and status checks."""
        return {
            "selected_option": self.selected_option.title,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "requires_ceo_approval": self.requires_ceo_approval,
            "supporting_memory_count": len(self.supporting_memory),
            "supporting_discussions_count": len(self.supporting_discussions),
            "evaluated_at": self.evaluated_at.isoformat(),
        }
