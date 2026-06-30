"""
Decision option model for AI Company OS.

A DecisionOption is an immutable representation of one candidate choice
within a structured decision. Options carry a title, enumerated advantages
and disadvantages, and rough estimates of risk and cost. The Decision Engine
scores options deterministically using these fields through DecisionRule
criteria — no AI, no embeddings, no external services.

Architecture reference: §2.4 Decision Engine, §3 Layer 2 (Business Logic).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


# Deterministic numeric scores for risk and cost labels.
# Higher score = more favourable (lower risk / lower cost).
_RISK_SCORES: Dict[str, int] = {
    "LOW": 3,
    "MEDIUM": 2,
    "HIGH": 1,
    "CRITICAL": 0,
}

_COST_SCORES: Dict[str, int] = {
    "LOW": 2,
    "MEDIUM": 1,
    "HIGH": 0,
}


@dataclass(frozen=True)
class DecisionOption:
    """
    Immutable description of a single candidate option in a Decision.

    Created by the caller and passed to DecisionEngine.create_decision().
    The Decision Engine never modifies options; it only reads them to compute
    scores and derive a recommendation.

    Attributes:
        title:          Short, unique identifier for this option within the
                        decision. Must be non-empty.
        advantages:     List of positive characteristics or benefits. May be
                        empty if the option has no identified advantages.
        disadvantages:  List of negative characteristics or drawbacks. May be
                        empty if the option has no identified disadvantages.
        estimated_risk: Qualitative risk estimate: "LOW", "MEDIUM", "HIGH",
                        or "CRITICAL". Case-insensitive. Defaults to "LOW".
        estimated_cost: Qualitative cost estimate: "LOW", "MEDIUM", or "HIGH".
                        Case-insensitive. Defaults to "LOW".
    """

    title: str
    advantages: List[str] = field(default_factory=list)
    disadvantages: List[str] = field(default_factory=list)
    estimated_risk: str = "LOW"
    estimated_cost: str = "LOW"

    # ------------------------------------------------------------------
    # Count helpers
    # ------------------------------------------------------------------

    def advantage_count(self) -> int:
        """Return the number of stated advantages."""
        return len(self.advantages)

    def disadvantage_count(self) -> int:
        """Return the number of stated disadvantages."""
        return len(self.disadvantages)

    # ------------------------------------------------------------------
    # Score helpers (used by DecisionEngine rule scorers)
    # ------------------------------------------------------------------

    def balance_score(self) -> int:
        """
        Return advantage_count minus disadvantage_count.

        A positive balance indicates more advantages than disadvantages.
        A negative balance indicates more disadvantages than advantages.
        """
        return self.advantage_count() - self.disadvantage_count()

    def risk_score(self) -> int:
        """
        Return a numeric risk score derived from estimated_risk.

        Higher scores indicate lower (more favourable) risk:
            LOW=3, MEDIUM=2, HIGH=1, CRITICAL=0.
        Unrecognised values default to 0 (CRITICAL-level caution).
        """
        return _RISK_SCORES.get(self.estimated_risk.upper(), 0)

    def cost_score(self) -> int:
        """
        Return a numeric cost score derived from estimated_cost.

        Higher scores indicate lower (more favourable) cost:
            LOW=2, MEDIUM=1, HIGH=0.
        Unrecognised values default to 0 (HIGH-cost caution).
        """
        return _COST_SCORES.get(self.estimated_cost.upper(), 0)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        """Return a compact dict representation of this option and its scores."""
        return {
            "title": self.title,
            "advantages": list(self.advantages),
            "disadvantages": list(self.disadvantages),
            "estimated_risk": self.estimated_risk,
            "estimated_cost": self.estimated_cost,
            "advantage_count": self.advantage_count(),
            "disadvantage_count": self.disadvantage_count(),
            "balance_score": self.balance_score(),
            "risk_score": self.risk_score(),
            "cost_score": self.cost_score(),
        }
