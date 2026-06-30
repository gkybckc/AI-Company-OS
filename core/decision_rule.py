"""
Decision rule model for AI Company OS.

A DecisionRule is an immutable evaluation criterion used by the Decision Engine
to score decision options. Each rule represents one measurable dimension of
option quality (risk, cost, advantages, etc.). Rules carry a weight that
controls how strongly the criterion influences the final recommendation when
multiple rules are combined.

Architecture reference: §2.4 Decision Engine, §3 Layer 2 (Business Logic),
Constitution §7.5 (decisions are recorded), §15 (CEO retains final authority).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DecisionRule:
    """
    Immutable evaluation criterion for the Decision Engine scoring pipeline.

    Each DecisionRule names a measurable property of a DecisionOption and
    assigns a weight to that property. The Decision Engine applies all active
    rules, multiplies each raw score by its rule's weight, and sums the
    products to produce a total weighted score for each option.

    Only rules whose name matches a known scorer in the engine are applied.
    Rules with unrecognised names are ignored silently — this allows
    forward-compatible rule sets where new rules can be added without
    breaking existing engines.

    Attributes:
        name:        Short identifier for the rule. Standard names:
                     LOWEST_RISK, MOST_ADVANTAGES, FEWEST_DISADVANTAGES,
                     LOWEST_COST, BEST_BALANCE.
        description: Human-readable explanation of what this rule measures.
        weight:      Positive multiplier applied to this rule's contribution.
                     Default 1.0 (equal weight with other 1.0-weight rules).
                     Higher values make this rule dominate the recommendation.
    """

    name: str
    description: str
    weight: float = 1.0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def is_weighted(self) -> bool:
        """Return True if the rule carries a non-default weight (weight != 1.0)."""
        return self.weight != 1.0

    def scaled_score(self, raw_score: float) -> float:
        """Return raw_score multiplied by this rule's weight."""
        return raw_score * self.weight

    # ------------------------------------------------------------------
    # Standard rule factories
    # ------------------------------------------------------------------

    @classmethod
    def lowest_risk(cls) -> "DecisionRule":
        """Standard rule: prefer options with the lowest estimated risk."""
        return cls(
            name="LOWEST_RISK",
            description=(
                "Prefer the option with the lowest estimated risk level. "
                "Scores: LOW=3, MEDIUM=2, HIGH=1, CRITICAL=0."
            ),
            weight=1.0,
        )

    @classmethod
    def most_advantages(cls) -> "DecisionRule":
        """Standard rule: prefer options with the most stated advantages."""
        return cls(
            name="MOST_ADVANTAGES",
            description=(
                "Prefer the option with the greatest number of listed advantages."
            ),
            weight=1.0,
        )

    @classmethod
    def fewest_disadvantages(cls) -> "DecisionRule":
        """Standard rule: prefer options with the fewest stated disadvantages."""
        return cls(
            name="FEWEST_DISADVANTAGES",
            description=(
                "Prefer the option with the fewest listed disadvantages. "
                "Score is the negative of disadvantage_count."
            ),
            weight=1.0,
        )

    @classmethod
    def lowest_cost(cls) -> "DecisionRule":
        """Standard rule: prefer options with the lowest estimated cost."""
        return cls(
            name="LOWEST_COST",
            description=(
                "Prefer the option with the lowest estimated cost. "
                "Scores: LOW=2, MEDIUM=1, HIGH=0."
            ),
            weight=1.0,
        )

    @classmethod
    def best_balance(cls) -> "DecisionRule":
        """Standard rule: prefer options with the best balance of advantages over disadvantages."""
        return cls(
            name="BEST_BALANCE",
            description=(
                "Prefer the option with the highest balance score "
                "(advantage_count minus disadvantage_count)."
            ),
            weight=1.0,
        )
