"""
Decision Engine for AI Company OS.

The DecisionEngine evaluates structured decisions by scoring candidate options
against named rules with weights and identifying the option with the highest
total weighted score. It produces a deterministic recommendation without using
AI, embeddings, external services, or any non-deterministic process.

The engine NEVER approves decisions. It only recommends. Only the CEO can
approve strategic decisions (Constitution §15, Architecture §2.4). The
requires_ceo_approval flag on DecisionResult communicates this constraint to
downstream components when the recommended option carries HIGH or CRITICAL risk.

Scoring algorithm
-----------------
For each decision option, each active rule contributes a weighted score:

    LOWEST_RISK:          option.risk_score()           (0-3, higher = safer)
    MOST_ADVANTAGES:      option.advantage_count()      (0+, higher = better)
    FEWEST_DISADVANTAGES: -option.disadvantage_count()  (0 to -inf, higher = better)
    LOWEST_COST:          option.cost_score()            (0-2, higher = cheaper)
    BEST_BALANCE:         option.balance_score()         (adv_count - disadv_count)

    total_score(option) = sum(rule.weight * scorer(option) for rule in rules)

Confidence formula
------------------
    gap    = top_score - second_score
    range_ = top_score - min_score
    confidence = 0.5 + (gap / range_) * 0.5   (if range_ > 0)
    confidence = 0.5                            (if range_ == 0, i.e., all tied)

    Result: 0.5 for a tie, approaching 1.0 as the margin of victory grows.

Architecture reference: §2.4 Decision Engine, §3 Layer 2 (Business Logic),
Constitution §15 (CEO authority), §7.5 (decisions recorded in memory).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from core.decision import Decision, DecisionRiskLevel, DecisionStatus
from core.decision_option import DecisionOption
from core.decision_result import DecisionResult
from core.decision_rule import DecisionRule


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class DecisionEngineError(Exception):
    """Base class for all Decision Engine errors."""


class DecisionNotFoundError(DecisionEngineError):
    """
    Raised when an operation references a decision ID that does not exist.

    Raised by evaluate(), recommend(), and find_decision() when the given
    decision_id is not present in the engine.
    """


class InvalidDecisionError(DecisionEngineError):
    """
    Raised when create_decision() receives invalid arguments.

    Covers: empty title, fewer than two options, duplicate option titles,
    options with empty titles.
    """


class DecisionAlreadyRecommendedError(DecisionEngineError):
    """
    Raised when evaluate() is called on a RECOMMENDED decision.

    RECOMMENDED is the terminal state. Re-evaluation is not permitted after
    recommend() has been called.
    """


class DecisionNotEvaluatedError(DecisionEngineError):
    """
    Raised when recommend() is called on a PENDING decision.

    evaluate() must be called before recommend() so that option scores and
    the recommendation field are populated.
    """


# ---------------------------------------------------------------------------
# Rule scoring map
# ---------------------------------------------------------------------------

# Maps rule name -> function(DecisionOption) -> float.
# Rules with names not in this map are accepted but contribute 0 to the score.
_RULE_SCORERS: Dict[str, Any] = {
    "LOWEST_RISK": lambda opt: float(opt.risk_score()),
    "MOST_ADVANTAGES": lambda opt: float(opt.advantage_count()),
    "FEWEST_DISADVANTAGES": lambda opt: float(-opt.disadvantage_count()),
    "LOWEST_COST": lambda opt: float(opt.cost_score()),
    "BEST_BALANCE": lambda opt: float(opt.balance_score()),
}

# Default rule set used when no rules are supplied to evaluate().
_DEFAULT_RULES: List[DecisionRule] = [
    DecisionRule.lowest_risk(),
    DecisionRule.most_advantages(),
    DecisionRule.fewest_disadvantages(),
    DecisionRule.lowest_cost(),
    DecisionRule.best_balance(),
]

# Maps estimated_risk string -> DecisionRiskLevel enum.
_RISK_LEVEL_MAP: Dict[str, DecisionRiskLevel] = {
    "LOW": DecisionRiskLevel.LOW,
    "MEDIUM": DecisionRiskLevel.MEDIUM,
    "HIGH": DecisionRiskLevel.HIGH,
    "CRITICAL": DecisionRiskLevel.CRITICAL,
}


# ---------------------------------------------------------------------------
# DecisionEngine
# ---------------------------------------------------------------------------

class DecisionEngine:
    """
    Central authority for structured decision evaluation and recommendation.

    The engine accepts decisions, scores their options deterministically
    against named rules, and produces a recommendation identifying the
    highest-scoring option. It records every decision in an in-process store
    so that history and statistics are always available.

    Optional integrations
    ---------------------
    - memory_engine:     If provided, relevant MemoryEntry IDs from the project
                         are attached to the DecisionResult as supporting_memory.
    - discussion_engine: If provided and the decision carries a discussion_id,
                         the Discussion ID is attached to the DecisionResult
                         as supporting_discussions.

    These integrations are entirely optional. The engine is fully functional
    without them.

    Usage pattern:
        engine = DecisionEngine()

        opt_a = DecisionOption(
            title="Option A",
            advantages=["Fast", "Cheap"],
            disadvantages=["Risky"],
            estimated_risk="HIGH",
            estimated_cost="LOW",
        )
        opt_b = DecisionOption(
            title="Option B",
            advantages=["Stable", "Proven"],
            disadvantages=[],
            estimated_risk="LOW",
            estimated_cost="MEDIUM",
        )

        decision = engine.create_decision("Choose backend", [opt_a, opt_b])
        engine.evaluate(decision.id)
        result = engine.recommend(decision.id)
        print(result.selected_option.title)   # deterministic output
        print(result.requires_ceo_approval)   # True if HIGH/CRITICAL risk

    Attributes:
        _decisions:         Dict[str, Decision] — all decisions keyed by ID.
        _memory_engine:     Optional MemoryEngine for supporting_memory lookup.
        _discussion_engine: Optional DiscussionEngine for discussion lookup.
    """

    def __init__(
        self,
        memory_engine: Optional[Any] = None,
        discussion_engine: Optional[Any] = None,
    ) -> None:
        self._decisions: Dict[str, Decision] = {}
        self._memory_engine = memory_engine
        self._discussion_engine = discussion_engine

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_decision(
        self,
        title: str,
        options: List[DecisionOption],
        *,
        project_id: Optional[str] = None,
        discussion_id: Optional[str] = None,
    ) -> Decision:
        """
        Register a new structured decision with its candidate options.

        The decision is created with PENDING status. No scoring is performed
        at this stage. Call evaluate() to score the options.

        Args:
            title:         Short human-readable description of the decision.
                           Must be non-empty.
            options:       List of at least two DecisionOption objects.
                           Each option title must be unique within the list
                           and non-empty.
            project_id:    Optional project this decision belongs to. When
                           provided and a MemoryEngine is attached, project
                           memory entries are gathered at recommend() time.
            discussion_id: Optional Discussion ID this decision emerged from.
                           When provided and a DiscussionEngine is attached,
                           the discussion is referenced in the result.

        Returns:
            The newly created Decision with PENDING status.

        Raises:
            InvalidDecisionError: If title is empty, fewer than two options
                are provided, option titles are not unique, or any option
                title is empty.
        """
        self._validate_create(title, options)

        decision = Decision(
            id=str(uuid4()),
            title=title.strip(),
            created_at=datetime.now(timezone.utc),
            options=list(options),
            project_id=project_id,
            discussion_id=discussion_id,
        )
        self._decisions[decision.id] = decision
        return decision

    def evaluate(
        self,
        decision_id: str,
        *,
        rules: Optional[List[DecisionRule]] = None,
    ) -> Decision:
        """
        Score all options and record the recommendation on the decision.

        Applies each rule in rules (or the default rule set if rules is None)
        to every option, sums the weighted scores, and identifies the option
        with the highest total. Ties are broken by insertion order of the
        options list (first inserted wins).

        Updates the decision in place:
            - status:       EVALUATED
            - recommendation: title of the highest-scoring option
            - risk_level:   derived from the winning option's estimated_risk
            - confidence:   computed by the confidence formula
            - evaluated_at: current UTC time
            - rules_applied: names of the applied rules
            - reasoning:    deterministic explanation string

        Can be called on PENDING or EVALUATED decisions (re-evaluation with
        different rules is allowed). Raises if the decision is RECOMMENDED
        (terminal state).

        Args:
            decision_id: ID of the decision to evaluate.
            rules:       List of DecisionRule objects to apply. If None, all
                         five default rules are applied with equal weight.

        Returns:
            The updated Decision with EVALUATED status.

        Raises:
            DecisionNotFoundError:         If decision_id does not exist.
            DecisionAlreadyRecommendedError: If the decision is RECOMMENDED.
            InvalidDecisionError:          If the decision has no options.
        """
        decision = self._require_decision(decision_id)

        if decision.status == DecisionStatus.RECOMMENDED:
            raise DecisionAlreadyRecommendedError(
                f"Decision '{decision_id}' is already RECOMMENDED and cannot "
                "be re-evaluated. RECOMMENDED is the terminal state."
            )

        if not decision.options:
            raise InvalidDecisionError(
                f"Decision '{decision_id}' has no options to evaluate."
            )

        applied_rules = rules if rules is not None else list(_DEFAULT_RULES)

        scores = self._score_options(decision.options, applied_rules)
        best_title = max(scores, key=lambda k: scores[k])
        best_option = decision.get_option(best_title)

        confidence = self._compute_confidence(scores)
        risk_level = self._derive_risk_level(best_option)
        reasoning = self._build_reasoning(best_option, scores, applied_rules, confidence)
        now = datetime.now(timezone.utc)

        decision.recommendation = best_title
        decision.risk_level = risk_level
        decision.confidence = confidence
        decision.evaluated_at = now
        decision.status = DecisionStatus.EVALUATED
        decision.rules_applied = [r.name for r in applied_rules]
        decision.reasoning = reasoning

        return decision

    def recommend(self, decision_id: str) -> DecisionResult:
        """
        Produce and store a DecisionResult for an evaluated decision.

        Gathers optional supporting evidence from attached engines, constructs
        the DecisionResult, stores it on the decision, and advances the status
        to RECOMMENDED. If the decision is already RECOMMENDED, the existing
        result is returned (idempotent).

        The engine NEVER approves the decision. The result's
        requires_ceo_approval flag is True when the recommended option's
        risk is HIGH or CRITICAL.

        Args:
            decision_id: ID of the decision to recommend.

        Returns:
            The DecisionResult containing the recommendation.

        Raises:
            DecisionNotFoundError:   If decision_id does not exist.
            DecisionNotEvaluatedError: If the decision is still PENDING.
                                       Call evaluate() first.
        """
        decision = self._require_decision(decision_id)

        if decision.status == DecisionStatus.PENDING:
            raise DecisionNotEvaluatedError(
                f"Decision '{decision_id}' has not been evaluated. "
                "Call evaluate() before recommend()."
            )

        if decision.status == DecisionStatus.RECOMMENDED and decision.result is not None:
            return decision.result

        supporting_memory: List[str] = []
        supporting_discussions: List[str] = []

        if self._memory_engine is not None and decision.project_id:
            try:
                entries = self._memory_engine.find_by_project(decision.project_id)
                supporting_memory = [e.id for e in entries]
            except Exception:
                pass

        if self._discussion_engine is not None and decision.discussion_id:
            try:
                disc = self._discussion_engine.find(decision.discussion_id)
                supporting_discussions = [disc.id]
            except Exception:
                pass

        winning_option = decision.get_option(decision.recommendation)

        result = DecisionResult(
            selected_option=winning_option,
            reasoning=decision.reasoning,
            confidence=decision.confidence,
            requires_ceo_approval=decision.requires_ceo_approval(),
            evaluated_at=decision.evaluated_at,
            supporting_memory=supporting_memory,
            supporting_discussions=supporting_discussions,
        )

        decision.result = result
        decision.status = DecisionStatus.RECOMMENDED

        return result

    def find_decision(self, decision_id: str) -> Decision:
        """
        Return the Decision with the given ID.

        Args:
            decision_id: The ID to look up.

        Returns:
            The Decision.

        Raises:
            DecisionNotFoundError: If no decision with this ID exists.
        """
        return self._require_decision(decision_id)

    def history(self) -> List[Decision]:
        """
        Return all decisions in the engine, ordered by created_at ascending.

        Returns a list sorted from oldest to newest decision. The list is a
        new list object (shallow copy of the dict values) so the caller cannot
        modify the engine's internal store, but the Decision objects themselves
        are the same instances.

        Returns:
            List of all Decision objects, oldest first.
        """
        return sorted(self._decisions.values(), key=lambda d: d.created_at)

    def statistics(self) -> Dict[str, Any]:
        """
        Return aggregate statistics across all decisions in the engine.

        Returns:
            Dict with keys:
                total_decisions       — Total number of decisions registered.
                by_status             — Dict mapping status value -> count.
                by_risk_level         — Dict mapping risk level value -> count
                                        (only counts evaluated decisions).
                requiring_ceo_approval — Count of decisions whose risk is HIGH
                                        or CRITICAL.
                high_confidence_count — Count of RECOMMENDED decisions whose
                                        result.confidence >= 0.8.
                average_confidence    — Mean confidence across all decisions
                                        (0.0 for unvaluated decisions).
                average_option_count  — Mean number of options per decision.
        """
        by_status: Dict[str, int] = {s.value: 0 for s in DecisionStatus}
        by_risk: Dict[str, int] = {r.value: 0 for r in DecisionRiskLevel}
        requiring_ceo = 0
        high_confidence = 0
        total_confidence = 0.0
        total_options = 0

        for d in self._decisions.values():
            by_status[d.status.value] = by_status.get(d.status.value, 0) + 1
            if d.risk_level is not None:
                by_risk[d.risk_level.value] = by_risk.get(d.risk_level.value, 0) + 1
            if d.requires_ceo_approval():
                requiring_ceo += 1
            if d.result is not None and d.result.is_high_confidence():
                high_confidence += 1
            total_confidence += d.confidence
            total_options += d.option_count()

        count = len(self._decisions)
        return {
            "total_decisions": count,
            "by_status": dict(by_status),
            "by_risk_level": dict(by_risk),
            "requiring_ceo_approval": requiring_ceo,
            "high_confidence_count": high_confidence,
            "average_confidence": total_confidence / count if count > 0 else 0.0,
            "average_option_count": float(total_options) / count if count > 0 else 0.0,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_decision(self, decision_id: str) -> Decision:
        """Return the decision or raise DecisionNotFoundError."""
        decision = self._decisions.get(decision_id)
        if decision is None:
            raise DecisionNotFoundError(
                f"No Decision with id '{decision_id}' exists in the engine."
            )
        return decision

    def _validate_create(
        self,
        title: str,
        options: List[DecisionOption],
    ) -> None:
        """Validate arguments for create_decision()."""
        if not title or not title.strip():
            raise InvalidDecisionError("Decision title must not be empty.")

        if len(options) < 2:
            raise InvalidDecisionError(
                f"A decision requires at least 2 options; got {len(options)}."
            )

        titles = [o.title for o in options]
        if len(titles) != len(set(titles)):
            raise InvalidDecisionError(
                "All decision options must have unique titles."
            )

        for opt in options:
            if not opt.title or not opt.title.strip():
                raise InvalidDecisionError(
                    "All decision options must have non-empty titles."
                )

    def _score_options(
        self,
        options: List[DecisionOption],
        rules: List[DecisionRule],
    ) -> Dict[str, float]:
        """
        Compute the total weighted score for each option under the given rules.

        Returns a dict mapping option title -> total weighted score.
        """
        scores: Dict[str, float] = {}
        for option in options:
            total = 0.0
            for rule in rules:
                scorer = _RULE_SCORERS.get(rule.name)
                if scorer is not None:
                    total += rule.weight * scorer(option)
            scores[option.title] = total
        return scores

    def _compute_confidence(self, scores: Dict[str, float]) -> float:
        """
        Compute confidence from the score distribution.

        confidence = 0.5 + (gap / range_) * 0.5
            gap    = top_score - second_score
            range_ = top_score - min_score

        Returns 0.5 when all options tie (range_ == 0).
        Returns 1.0 when only one option exists or one option is the sole
        maximum with all others tied at the minimum.
        """
        if len(scores) < 2:
            return 1.0

        sorted_vals = sorted(scores.values(), reverse=True)
        top = sorted_vals[0]
        second = sorted_vals[1]
        min_score = sorted_vals[-1]

        range_ = top - min_score
        if range_ == 0.0:
            return 0.5

        gap = top - second
        return 0.5 + (gap / range_) * 0.5

    def _derive_risk_level(self, option: DecisionOption) -> DecisionRiskLevel:
        """Derive a DecisionRiskLevel from the winning option's estimated_risk."""
        return _RISK_LEVEL_MAP.get(
            option.estimated_risk.upper(),
            DecisionRiskLevel.HIGH,
        )

    def _build_reasoning(
        self,
        winning: DecisionOption,
        scores: Dict[str, float],
        rules: List[DecisionRule],
        confidence: float,
    ) -> str:
        """
        Build a deterministic reasoning string explaining the recommendation.

        Given the same inputs, this method always returns the same string.
        """
        rule_names = ", ".join(r.name for r in rules)
        sorted_options = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        winning_score = scores[winning.title]

        parts = [
            f"Option '{winning.title}' was selected with a score of "
            f"{winning_score:.2f}.",
            f"Rules applied: {rule_names}.",
            f"Confidence: {confidence:.2f}.",
        ]

        if len(sorted_options) > 1:
            runner_up_title, runner_up_score = sorted_options[1]
            parts.append(
                f"Runner-up '{runner_up_title}' scored {runner_up_score:.2f}."
            )

        return " ".join(parts)
