"""
Decision domain model for AI Company OS.

Defines the Decision mutable record together with the DecisionRiskLevel and
DecisionStatus enumerations that describe a decision's current position in
the evaluation pipeline.

A Decision is created by DecisionEngine.create_decision() and progresses
through three statuses: PENDING → EVALUATED → RECOMMENDED. Once RECOMMENDED,
the decision is in its terminal state and holds a DecisionResult that
captures the engine's full recommendation.

Architecture reference: §2.4 Decision Engine, §3 Layer 2 (Business Logic),
Constitution §15 (CEO retains final authority on strategic decisions).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from core.decision_option import DecisionOption
from core.decision_result import DecisionResult


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class DecisionRiskLevel(str, Enum):
    """
    Overall risk level assigned to a Decision after evaluation.

    Derived from the winning option's estimated_risk value. The risk level
    governs whether the CEO must approve before the recommendation is enacted.

    Levels:
        LOW      — Minimal organisational risk; no CEO approval required.
        MEDIUM   — Moderate risk; no CEO approval required, but should be
                   monitored.
        HIGH     — Significant risk; CEO approval required before action.
        CRITICAL — Maximum risk; CEO approval mandatory; action should not
                   proceed without explicit sign-off.
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    def __str__(self) -> str:
        return self.value

    def requires_ceo_approval(self) -> bool:
        """Return True if this risk level requires CEO approval (HIGH or CRITICAL)."""
        return self in {DecisionRiskLevel.HIGH, DecisionRiskLevel.CRITICAL}

    def is_severe(self) -> bool:
        """Return True if the risk level is HIGH or CRITICAL."""
        return self in {DecisionRiskLevel.HIGH, DecisionRiskLevel.CRITICAL}


class DecisionStatus(str, Enum):
    """
    Lifecycle status of a Decision within the Decision Engine pipeline.

    Transitions:
        PENDING    — Initial state after create_decision(). Options have been
                     registered but no scoring has been performed.
        EVALUATED  — evaluate() has been called. Options have been scored and
                     a recommendation (option title) has been identified.
        RECOMMENDED — recommend() has been called. A DecisionResult has been
                     produced and stored. Terminal state.
    """

    PENDING = "PENDING"
    EVALUATED = "EVALUATED"
    RECOMMENDED = "RECOMMENDED"

    def __str__(self) -> str:
        return self.value

    def is_terminal(self) -> bool:
        """Return True if the decision has reached the final RECOMMENDED state."""
        return self == DecisionStatus.RECOMMENDED

    def is_actionable(self) -> bool:
        """Return True if the decision has a finalised recommendation (RECOMMENDED)."""
        return self == DecisionStatus.RECOMMENDED


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------

@dataclass
class Decision:
    """
    Mutable record representing a structured decision under evaluation.

    A Decision tracks the full lifecycle of an option-scoring cycle: from
    creation with a set of candidate options through evaluation and final
    recommendation. It is owned and mutated exclusively by the DecisionEngine.

    The recommendation field holds the title of the winning option after
    evaluate() is called. The result field holds the full DecisionResult
    after recommend() is called.

    Callers must not mutate Decision objects directly after they are returned
    by the engine — use engine methods to advance the decision through its
    lifecycle.

    Attributes:
        id:             Unique identifier (UUID string).
        title:          Short, human-readable description of the decision.
        created_at:     UTC timestamp of when the decision was created.
        options:        Ordered list of candidate options.
        status:         Current lifecycle status.
        project_id:     Optional project this decision belongs to.
        discussion_id:  Optional Discussion ID this decision emerged from.
        recommendation: Title of the recommended option after evaluation.
                        None until evaluate() is called.
        risk_level:     Risk level derived from the recommended option's
                        estimated_risk. None until evaluate() is called.
        confidence:     Score in [0.5, 1.0] from the confidence formula.
                        0.0 until evaluate() is called.
        evaluated_at:   UTC timestamp of the most recent evaluate() call.
                        None until evaluate() is called.
        result:         Full DecisionResult from the most recent recommend()
                        call. None until recommend() is called.
        rules_applied:  Names of the rules used in the most recent evaluate().
                        Empty list until evaluate() is called.
        reasoning:      Deterministic reasoning string built during evaluate().
                        Empty string until evaluate() is called.
    """

    id: str
    title: str
    created_at: datetime
    options: List[DecisionOption] = field(default_factory=list)
    status: DecisionStatus = DecisionStatus.PENDING
    project_id: Optional[str] = None
    discussion_id: Optional[str] = None
    recommendation: Optional[str] = None
    risk_level: Optional[DecisionRiskLevel] = None
    confidence: float = 0.0
    evaluated_at: Optional[datetime] = None
    result: Optional[DecisionResult] = None
    rules_applied: List[str] = field(default_factory=list)
    reasoning: str = ""

    # ------------------------------------------------------------------
    # Approval
    # ------------------------------------------------------------------

    def requires_ceo_approval(self) -> bool:
        """
        Return True if the evaluated risk level requires CEO sign-off.

        Returns False if the decision has not yet been evaluated (risk_level
        is None). Returns True when risk_level is HIGH or CRITICAL.
        """
        if self.risk_level is None:
            return False
        return self.risk_level.requires_ceo_approval()

    # ------------------------------------------------------------------
    # Option access
    # ------------------------------------------------------------------

    def get_option(self, title: str) -> Optional[DecisionOption]:
        """Return the option with the given title, or None if not found."""
        for option in self.options:
            if option.title == title:
                return option
        return None

    def option_count(self) -> int:
        """Return the number of options registered on this decision."""
        return len(self.options)

    # ------------------------------------------------------------------
    # Status checks
    # ------------------------------------------------------------------

    def is_pending(self) -> bool:
        """Return True if the decision has not yet been evaluated."""
        return self.status == DecisionStatus.PENDING

    def is_evaluated(self) -> bool:
        """Return True if the decision has been evaluated but not yet recommended."""
        return self.status == DecisionStatus.EVALUATED

    def is_recommended(self) -> bool:
        """Return True if the decision has a finalised recommendation."""
        return self.status == DecisionStatus.RECOMMENDED

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        """Return a compact dict suitable for listings and status reports."""
        return {
            "id": self.id,
            "title": self.title,
            "status": str(self.status),
            "project_id": self.project_id,
            "discussion_id": self.discussion_id,
            "option_count": self.option_count(),
            "recommendation": self.recommendation,
            "risk_level": str(self.risk_level) if self.risk_level else None,
            "confidence": self.confidence,
            "requires_ceo_approval": self.requires_ceo_approval(),
            "rules_applied": list(self.rules_applied),
            "created_at": self.created_at.isoformat(),
            "evaluated_at": (
                self.evaluated_at.isoformat() if self.evaluated_at else None
            ),
        }
