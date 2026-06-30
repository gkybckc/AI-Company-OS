"""
Unit tests for Sprint 12 — Decision Engine.

Covers:
    core/decision_rule.py      — DecisionRule
    core/decision_option.py    — DecisionOption
    core/decision_result.py    — DecisionResult
    core/decision.py           — DecisionRiskLevel, DecisionStatus, Decision
    core/decision_engine.py    — DecisionEngine and exception hierarchy
"""

import unittest
from datetime import datetime, timezone
from uuid import uuid4

from core.decision_rule import DecisionRule
from core.decision_option import DecisionOption
from core.decision_result import DecisionResult
from core.decision import Decision, DecisionRiskLevel, DecisionStatus
from core.decision_engine import (
    DecisionEngine,
    DecisionEngineError,
    DecisionNotFoundError,
    InvalidDecisionError,
    DecisionAlreadyRecommendedError,
    DecisionNotEvaluatedError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _opt(
    title: str = "Option A",
    advantages=None,
    disadvantages=None,
    risk: str = "LOW",
    cost: str = "LOW",
) -> DecisionOption:
    return DecisionOption(
        title=title,
        advantages=advantages if advantages is not None else [],
        disadvantages=disadvantages if disadvantages is not None else [],
        estimated_risk=risk,
        estimated_cost=cost,
    )


def _two_opts() -> list:
    return [_opt("Option A"), _opt("Option B")]


def _engine() -> DecisionEngine:
    return DecisionEngine()


# ---------------------------------------------------------------------------
# DecisionRule
# ---------------------------------------------------------------------------

class TestDecisionRuleCreation(unittest.TestCase):

    def test_create_with_all_fields(self):
        rule = DecisionRule(name="MY_RULE", description="Test rule", weight=2.0)
        self.assertEqual(rule.name, "MY_RULE")
        self.assertEqual(rule.description, "Test rule")
        self.assertEqual(rule.weight, 2.0)

    def test_default_weight_is_one(self):
        rule = DecisionRule(name="R", description="D")
        self.assertEqual(rule.weight, 1.0)

    def test_frozen(self):
        rule = DecisionRule(name="R", description="D")
        with self.assertRaises(Exception):
            rule.name = "X"

    def test_equality_same_fields(self):
        r1 = DecisionRule(name="R", description="D", weight=1.0)
        r2 = DecisionRule(name="R", description="D", weight=1.0)
        self.assertEqual(r1, r2)

    def test_inequality_different_weight(self):
        r1 = DecisionRule(name="R", description="D", weight=1.0)
        r2 = DecisionRule(name="R", description="D", weight=2.0)
        self.assertNotEqual(r1, r2)

    def test_inequality_different_name(self):
        r1 = DecisionRule(name="A", description="D")
        r2 = DecisionRule(name="B", description="D")
        self.assertNotEqual(r1, r2)

    def test_is_weighted_false_for_default(self):
        rule = DecisionRule(name="R", description="D", weight=1.0)
        self.assertFalse(rule.is_weighted())

    def test_is_weighted_true_for_non_default(self):
        rule = DecisionRule(name="R", description="D", weight=2.5)
        self.assertTrue(rule.is_weighted())

    def test_scaled_score_basic(self):
        rule = DecisionRule(name="R", description="D", weight=2.0)
        self.assertAlmostEqual(rule.scaled_score(3.0), 6.0)

    def test_scaled_score_default_weight(self):
        rule = DecisionRule(name="R", description="D")
        self.assertAlmostEqual(rule.scaled_score(5.0), 5.0)

    def test_scaled_score_zero(self):
        rule = DecisionRule(name="R", description="D", weight=10.0)
        self.assertAlmostEqual(rule.scaled_score(0.0), 0.0)

    def test_name_and_description_preserved(self):
        rule = DecisionRule(name="LOWEST_RISK", description="Prefer safe options")
        self.assertEqual(rule.name, "LOWEST_RISK")
        self.assertIn("safe", rule.description)


class TestDecisionRuleFactories(unittest.TestCase):

    def test_lowest_risk_name(self):
        self.assertEqual(DecisionRule.lowest_risk().name, "LOWEST_RISK")

    def test_most_advantages_name(self):
        self.assertEqual(DecisionRule.most_advantages().name, "MOST_ADVANTAGES")

    def test_fewest_disadvantages_name(self):
        self.assertEqual(DecisionRule.fewest_disadvantages().name, "FEWEST_DISADVANTAGES")

    def test_lowest_cost_name(self):
        self.assertEqual(DecisionRule.lowest_cost().name, "LOWEST_COST")

    def test_best_balance_name(self):
        self.assertEqual(DecisionRule.best_balance().name, "BEST_BALANCE")

    def test_all_factories_default_weight(self):
        for rule in [
            DecisionRule.lowest_risk(),
            DecisionRule.most_advantages(),
            DecisionRule.fewest_disadvantages(),
            DecisionRule.lowest_cost(),
            DecisionRule.best_balance(),
        ]:
            self.assertEqual(rule.weight, 1.0)

    def test_all_factories_have_description(self):
        for rule in [
            DecisionRule.lowest_risk(),
            DecisionRule.most_advantages(),
            DecisionRule.fewest_disadvantages(),
            DecisionRule.lowest_cost(),
            DecisionRule.best_balance(),
        ]:
            self.assertTrue(len(rule.description) > 0)

    def test_factories_return_frozen_instances(self):
        rule = DecisionRule.lowest_risk()
        with self.assertRaises(Exception):
            rule.weight = 5.0

    def test_two_factory_calls_equal(self):
        self.assertEqual(DecisionRule.lowest_risk(), DecisionRule.lowest_risk())

    def test_different_factories_not_equal(self):
        self.assertNotEqual(DecisionRule.lowest_risk(), DecisionRule.lowest_cost())

    def test_is_not_weighted_by_default(self):
        for rule in [
            DecisionRule.lowest_risk(),
            DecisionRule.most_advantages(),
            DecisionRule.fewest_disadvantages(),
            DecisionRule.lowest_cost(),
            DecisionRule.best_balance(),
        ]:
            self.assertFalse(rule.is_weighted())

    def test_five_distinct_factories(self):
        names = {
            DecisionRule.lowest_risk().name,
            DecisionRule.most_advantages().name,
            DecisionRule.fewest_disadvantages().name,
            DecisionRule.lowest_cost().name,
            DecisionRule.best_balance().name,
        }
        self.assertEqual(len(names), 5)


# ---------------------------------------------------------------------------
# DecisionOption
# ---------------------------------------------------------------------------

class TestDecisionOptionCreation(unittest.TestCase):

    def test_create_minimal(self):
        opt = DecisionOption(title="Option A")
        self.assertEqual(opt.title, "Option A")
        self.assertEqual(opt.advantages, [])
        self.assertEqual(opt.disadvantages, [])
        self.assertEqual(opt.estimated_risk, "LOW")
        self.assertEqual(opt.estimated_cost, "LOW")

    def test_create_full(self):
        opt = DecisionOption(
            title="Build in-house",
            advantages=["Control", "Custom"],
            disadvantages=["Expensive"],
            estimated_risk="MEDIUM",
            estimated_cost="HIGH",
        )
        self.assertEqual(opt.title, "Build in-house")
        self.assertEqual(len(opt.advantages), 2)
        self.assertEqual(len(opt.disadvantages), 1)
        self.assertEqual(opt.estimated_risk, "MEDIUM")
        self.assertEqual(opt.estimated_cost, "HIGH")

    def test_frozen(self):
        opt = DecisionOption(title="A")
        with self.assertRaises(Exception):
            opt.title = "B"

    def test_empty_advantages_by_default(self):
        opt = DecisionOption(title="X")
        self.assertEqual(opt.advantage_count(), 0)

    def test_empty_disadvantages_by_default(self):
        opt = DecisionOption(title="X")
        self.assertEqual(opt.disadvantage_count(), 0)


class TestDecisionOptionScores(unittest.TestCase):

    def test_risk_score_low(self):
        opt = DecisionOption(title="A", estimated_risk="LOW")
        self.assertEqual(opt.risk_score(), 3)

    def test_risk_score_medium(self):
        opt = DecisionOption(title="A", estimated_risk="MEDIUM")
        self.assertEqual(opt.risk_score(), 2)

    def test_risk_score_high(self):
        opt = DecisionOption(title="A", estimated_risk="HIGH")
        self.assertEqual(opt.risk_score(), 1)

    def test_risk_score_critical(self):
        opt = DecisionOption(title="A", estimated_risk="CRITICAL")
        self.assertEqual(opt.risk_score(), 0)

    def test_risk_score_case_insensitive(self):
        self.assertEqual(DecisionOption(title="A", estimated_risk="low").risk_score(), 3)
        self.assertEqual(DecisionOption(title="A", estimated_risk="Low").risk_score(), 3)

    def test_risk_score_unknown_defaults_to_zero(self):
        opt = DecisionOption(title="A", estimated_risk="UNKNOWN")
        self.assertEqual(opt.risk_score(), 0)

    def test_cost_score_low(self):
        opt = DecisionOption(title="A", estimated_cost="LOW")
        self.assertEqual(opt.cost_score(), 2)

    def test_cost_score_medium(self):
        opt = DecisionOption(title="A", estimated_cost="MEDIUM")
        self.assertEqual(opt.cost_score(), 1)

    def test_cost_score_high(self):
        opt = DecisionOption(title="A", estimated_cost="HIGH")
        self.assertEqual(opt.cost_score(), 0)

    def test_cost_score_case_insensitive(self):
        self.assertEqual(DecisionOption(title="A", estimated_cost="low").cost_score(), 2)

    def test_cost_score_unknown_defaults_to_zero(self):
        opt = DecisionOption(title="A", estimated_cost="CHEAP")
        self.assertEqual(opt.cost_score(), 0)

    def test_balance_score_positive(self):
        opt = DecisionOption(title="A", advantages=["a", "b", "c"], disadvantages=["x"])
        self.assertEqual(opt.balance_score(), 2)

    def test_balance_score_negative(self):
        opt = DecisionOption(title="A", advantages=[], disadvantages=["x", "y", "z"])
        self.assertEqual(opt.balance_score(), -3)

    def test_balance_score_zero(self):
        opt = DecisionOption(title="A", advantages=["a"], disadvantages=["x"])
        self.assertEqual(opt.balance_score(), 0)

    def test_balance_empty(self):
        opt = DecisionOption(title="A")
        self.assertEqual(opt.balance_score(), 0)


class TestDecisionOptionHelpers(unittest.TestCase):

    def test_advantage_count(self):
        opt = DecisionOption(title="A", advantages=["a", "b"])
        self.assertEqual(opt.advantage_count(), 2)

    def test_disadvantage_count(self):
        opt = DecisionOption(title="A", disadvantages=["x"])
        self.assertEqual(opt.disadvantage_count(), 1)

    def test_advantage_count_empty(self):
        self.assertEqual(DecisionOption(title="A").advantage_count(), 0)

    def test_disadvantage_count_empty(self):
        self.assertEqual(DecisionOption(title="A").disadvantage_count(), 0)

    def test_summary_keys(self):
        opt = _opt("A")
        s = opt.summary()
        for key in ["title", "advantages", "disadvantages", "estimated_risk",
                    "estimated_cost", "advantage_count", "disadvantage_count",
                    "balance_score", "risk_score", "cost_score"]:
            self.assertIn(key, s)

    def test_summary_values_match(self):
        opt = DecisionOption(
            title="X",
            advantages=["a"],
            disadvantages=["b", "c"],
            estimated_risk="HIGH",
            estimated_cost="MEDIUM",
        )
        s = opt.summary()
        self.assertEqual(s["title"], "X")
        self.assertEqual(s["advantage_count"], 1)
        self.assertEqual(s["disadvantage_count"], 2)
        self.assertEqual(s["balance_score"], -1)
        self.assertEqual(s["risk_score"], 1)
        self.assertEqual(s["cost_score"], 1)

    def test_summary_advantages_copy(self):
        opt = DecisionOption(title="A", advantages=["a"])
        s = opt.summary()
        s["advantages"].append("extra")
        self.assertEqual(opt.advantage_count(), 1)

    def test_two_options_different_titles_not_equal(self):
        a = DecisionOption(title="A")
        b = DecisionOption(title="B")
        self.assertNotEqual(a, b)

    def test_identical_options_equal(self):
        a = DecisionOption(title="A", advantages=["x"], estimated_risk="LOW")
        b = DecisionOption(title="A", advantages=["x"], estimated_risk="LOW")
        self.assertEqual(a, b)


# ---------------------------------------------------------------------------
# DecisionResult
# ---------------------------------------------------------------------------

class TestDecisionResultCreation(unittest.TestCase):

    def _make_result(self, **kwargs):
        defaults = dict(
            selected_option=_opt("A"),
            reasoning="Option A won.",
            confidence=0.8,
            requires_ceo_approval=False,
            evaluated_at=_now(),
        )
        defaults.update(kwargs)
        return DecisionResult(**defaults)

    def test_create_minimal(self):
        r = self._make_result()
        self.assertEqual(r.selected_option.title, "A")
        self.assertEqual(r.reasoning, "Option A won.")
        self.assertAlmostEqual(r.confidence, 0.8)
        self.assertFalse(r.requires_ceo_approval)
        self.assertEqual(r.supporting_memory, [])
        self.assertEqual(r.supporting_discussions, [])

    def test_create_with_supporting_evidence(self):
        r = self._make_result(
            supporting_memory=["mem-1", "mem-2"],
            supporting_discussions=["disc-1"],
        )
        self.assertEqual(len(r.supporting_memory), 2)
        self.assertEqual(len(r.supporting_discussions), 1)

    def test_frozen(self):
        r = self._make_result()
        with self.assertRaises(Exception):
            r.confidence = 0.5

    def test_requires_ceo_approval_true(self):
        r = self._make_result(requires_ceo_approval=True)
        self.assertTrue(r.requires_ceo_approval)

    def test_evaluated_at_preserved(self):
        t = _now()
        r = self._make_result(evaluated_at=t)
        self.assertEqual(r.evaluated_at, t)


class TestDecisionResultHelpers(unittest.TestCase):

    def _r(self, confidence: float, ceo: bool = False, mem=None, disc=None):
        return DecisionResult(
            selected_option=_opt(),
            reasoning="r",
            confidence=confidence,
            requires_ceo_approval=ceo,
            evaluated_at=_now(),
            supporting_memory=mem or [],
            supporting_discussions=disc or [],
        )

    def test_high_confidence_at_0_8(self):
        self.assertTrue(self._r(0.8).is_high_confidence())

    def test_high_confidence_above_0_8(self):
        self.assertTrue(self._r(0.95).is_high_confidence())

    def test_not_high_confidence_below(self):
        self.assertFalse(self._r(0.79).is_high_confidence())

    def test_low_confidence_at_0_6(self):
        self.assertTrue(self._r(0.6).is_low_confidence())

    def test_low_confidence_at_0_5(self):
        self.assertTrue(self._r(0.5).is_low_confidence())

    def test_not_low_confidence_above(self):
        self.assertFalse(self._r(0.61).is_low_confidence())

    def test_has_supporting_evidence_memory_only(self):
        r = self._r(0.7, mem=["m1"])
        self.assertTrue(r.has_supporting_evidence())

    def test_has_supporting_evidence_discussion_only(self):
        r = self._r(0.7, disc=["d1"])
        self.assertTrue(r.has_supporting_evidence())

    def test_no_supporting_evidence(self):
        self.assertFalse(self._r(0.7).has_supporting_evidence())

    def test_supporting_evidence_count(self):
        r = self._r(0.7, mem=["m1", "m2"], disc=["d1"])
        self.assertEqual(r.supporting_evidence_count(), 3)

    def test_summary_keys(self):
        r = self._r(0.75)
        s = r.summary()
        for key in ["selected_option", "reasoning", "confidence",
                    "requires_ceo_approval", "supporting_memory_count",
                    "supporting_discussions_count", "evaluated_at"]:
            self.assertIn(key, s)

    def test_summary_selected_option_is_title(self):
        r = self._r(0.75)
        self.assertEqual(r.summary()["selected_option"], "Option A")


# ---------------------------------------------------------------------------
# DecisionRiskLevel
# ---------------------------------------------------------------------------

class TestDecisionRiskLevelEnum(unittest.TestCase):

    def test_all_values_exist(self):
        for v in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
            level = DecisionRiskLevel(v)
            self.assertEqual(str(level), v)

    def test_str_returns_value(self):
        self.assertEqual(str(DecisionRiskLevel.LOW), "LOW")
        self.assertEqual(str(DecisionRiskLevel.CRITICAL), "CRITICAL")

    def test_requires_ceo_approval_high(self):
        self.assertTrue(DecisionRiskLevel.HIGH.requires_ceo_approval())

    def test_requires_ceo_approval_critical(self):
        self.assertTrue(DecisionRiskLevel.CRITICAL.requires_ceo_approval())

    def test_not_requires_ceo_approval_low(self):
        self.assertFalse(DecisionRiskLevel.LOW.requires_ceo_approval())

    def test_not_requires_ceo_approval_medium(self):
        self.assertFalse(DecisionRiskLevel.MEDIUM.requires_ceo_approval())

    def test_is_severe_high(self):
        self.assertTrue(DecisionRiskLevel.HIGH.is_severe())

    def test_is_severe_critical(self):
        self.assertTrue(DecisionRiskLevel.CRITICAL.is_severe())

    def test_not_severe_low(self):
        self.assertFalse(DecisionRiskLevel.LOW.is_severe())

    def test_not_severe_medium(self):
        self.assertFalse(DecisionRiskLevel.MEDIUM.is_severe())

    def test_str_enum_isinstance(self):
        self.assertIsInstance(DecisionRiskLevel.LOW, str)

    def test_four_levels(self):
        self.assertEqual(len(DecisionRiskLevel), 4)


# ---------------------------------------------------------------------------
# DecisionStatus
# ---------------------------------------------------------------------------

class TestDecisionStatusEnum(unittest.TestCase):

    def test_all_values_exist(self):
        for v in ["PENDING", "EVALUATED", "RECOMMENDED"]:
            status = DecisionStatus(v)
            self.assertEqual(str(status), v)

    def test_str_returns_value(self):
        self.assertEqual(str(DecisionStatus.PENDING), "PENDING")

    def test_is_terminal_recommended(self):
        self.assertTrue(DecisionStatus.RECOMMENDED.is_terminal())

    def test_not_terminal_pending(self):
        self.assertFalse(DecisionStatus.PENDING.is_terminal())

    def test_not_terminal_evaluated(self):
        self.assertFalse(DecisionStatus.EVALUATED.is_terminal())

    def test_is_actionable_recommended(self):
        self.assertTrue(DecisionStatus.RECOMMENDED.is_actionable())

    def test_not_actionable_pending(self):
        self.assertFalse(DecisionStatus.PENDING.is_actionable())

    def test_not_actionable_evaluated(self):
        self.assertFalse(DecisionStatus.EVALUATED.is_actionable())

    def test_str_enum_isinstance(self):
        self.assertIsInstance(DecisionStatus.PENDING, str)

    def test_three_statuses(self):
        self.assertEqual(len(DecisionStatus), 3)


# ---------------------------------------------------------------------------
# Decision dataclass
# ---------------------------------------------------------------------------

class TestDecisionDataclass(unittest.TestCase):

    def _make(self, **kwargs):
        defaults = dict(id=str(uuid4()), title="My Decision", created_at=_now())
        defaults.update(kwargs)
        return Decision(**defaults)

    def test_create_minimal(self):
        d = self._make()
        self.assertEqual(d.status, DecisionStatus.PENDING)
        self.assertIsNone(d.project_id)
        self.assertIsNone(d.discussion_id)
        self.assertIsNone(d.recommendation)
        self.assertIsNone(d.risk_level)
        self.assertAlmostEqual(d.confidence, 0.0)
        self.assertIsNone(d.evaluated_at)
        self.assertIsNone(d.result)
        self.assertEqual(d.rules_applied, [])
        self.assertEqual(d.reasoning, "")

    def test_default_status_pending(self):
        self.assertEqual(self._make().status, DecisionStatus.PENDING)

    def test_options_empty_by_default(self):
        self.assertEqual(self._make().option_count(), 0)

    def test_mutable_status(self):
        d = self._make()
        d.status = DecisionStatus.EVALUATED
        self.assertEqual(d.status, DecisionStatus.EVALUATED)

    def test_mutable_recommendation(self):
        d = self._make()
        d.recommendation = "Option A"
        self.assertEqual(d.recommendation, "Option A")

    def test_options_stored(self):
        opts = [_opt("A"), _opt("B")]
        d = self._make(options=opts)
        self.assertEqual(d.option_count(), 2)

    def test_project_id_stored(self):
        d = self._make(project_id="proj-1")
        self.assertEqual(d.project_id, "proj-1")

    def test_discussion_id_stored(self):
        d = self._make(discussion_id="disc-1")
        self.assertEqual(d.discussion_id, "disc-1")

    def test_id_preserved(self):
        uid = str(uuid4())
        d = self._make(id=uid)
        self.assertEqual(d.id, uid)

    def test_created_at_preserved(self):
        t = _now()
        d = self._make(created_at=t)
        self.assertEqual(d.created_at, t)

    def test_rules_applied_mutable(self):
        d = self._make()
        d.rules_applied = ["LOWEST_RISK"]
        self.assertEqual(d.rules_applied, ["LOWEST_RISK"])

    def test_reasoning_mutable(self):
        d = self._make()
        d.reasoning = "Because A won."
        self.assertEqual(d.reasoning, "Because A won.")


class TestDecisionHelpers(unittest.TestCase):

    def _make(self, **kwargs):
        defaults = dict(id=str(uuid4()), title="D", created_at=_now())
        defaults.update(kwargs)
        return Decision(**defaults)

    def test_is_pending_true(self):
        d = self._make()
        self.assertTrue(d.is_pending())

    def test_is_pending_false(self):
        d = self._make(status=DecisionStatus.EVALUATED)
        self.assertFalse(d.is_pending())

    def test_is_evaluated_true(self):
        d = self._make(status=DecisionStatus.EVALUATED)
        self.assertTrue(d.is_evaluated())

    def test_is_recommended_true(self):
        d = self._make(status=DecisionStatus.RECOMMENDED)
        self.assertTrue(d.is_recommended())

    def test_get_option_found(self):
        opts = [_opt("Alpha"), _opt("Beta")]
        d = self._make(options=opts)
        self.assertEqual(d.get_option("Alpha").title, "Alpha")

    def test_get_option_not_found(self):
        opts = [_opt("Alpha")]
        d = self._make(options=opts)
        self.assertIsNone(d.get_option("Missing"))

    def test_requires_ceo_approval_no_risk(self):
        d = self._make()
        self.assertFalse(d.requires_ceo_approval())

    def test_requires_ceo_approval_high_risk(self):
        d = self._make(risk_level=DecisionRiskLevel.HIGH)
        self.assertTrue(d.requires_ceo_approval())

    def test_requires_ceo_approval_critical(self):
        d = self._make(risk_level=DecisionRiskLevel.CRITICAL)
        self.assertTrue(d.requires_ceo_approval())

    def test_requires_ceo_approval_low_false(self):
        d = self._make(risk_level=DecisionRiskLevel.LOW)
        self.assertFalse(d.requires_ceo_approval())

    def test_summary_keys(self):
        d = self._make()
        s = d.summary()
        for key in ["id", "title", "status", "project_id", "discussion_id",
                    "option_count", "recommendation", "risk_level", "confidence",
                    "requires_ceo_approval", "rules_applied", "created_at",
                    "evaluated_at"]:
            self.assertIn(key, s)

    def test_summary_status_is_string(self):
        d = self._make()
        self.assertIsInstance(d.summary()["status"], str)

    def test_summary_evaluated_at_none_initially(self):
        self.assertIsNone(self._make().summary()["evaluated_at"])


# ---------------------------------------------------------------------------
# DecisionEngine init
# ---------------------------------------------------------------------------

class TestDecisionEngineInit(unittest.TestCase):

    def test_creates_empty_engine(self):
        engine = DecisionEngine()
        self.assertEqual(len(engine.history()), 0)

    def test_statistics_empty(self):
        engine = DecisionEngine()
        stats = engine.statistics()
        self.assertEqual(stats["total_decisions"], 0)

    def test_history_empty_list(self):
        engine = DecisionEngine()
        self.assertEqual(engine.history(), [])

    def test_no_memory_engine_by_default(self):
        engine = DecisionEngine()
        self.assertIsNone(engine._memory_engine)

    def test_no_discussion_engine_by_default(self):
        engine = DecisionEngine()
        self.assertIsNone(engine._discussion_engine)

    def test_memory_engine_stored(self):
        sentinel = object()
        engine = DecisionEngine(memory_engine=sentinel)
        self.assertIs(engine._memory_engine, sentinel)

    def test_discussion_engine_stored(self):
        sentinel = object()
        engine = DecisionEngine(discussion_engine=sentinel)
        self.assertIs(engine._discussion_engine, sentinel)

    def test_multiple_engines_independent(self):
        e1 = DecisionEngine()
        e2 = DecisionEngine()
        e1.create_decision("D", _two_opts())
        self.assertEqual(len(e2.history()), 0)


# ---------------------------------------------------------------------------
# create_decision
# ---------------------------------------------------------------------------

class TestCreateDecision(unittest.TestCase):

    def setUp(self):
        self.engine = _engine()

    def test_returns_decision(self):
        d = self.engine.create_decision("My decision", _two_opts())
        self.assertIsInstance(d, Decision)

    def test_status_is_pending(self):
        d = self.engine.create_decision("D", _two_opts())
        self.assertEqual(d.status, DecisionStatus.PENDING)

    def test_title_stored(self):
        d = self.engine.create_decision("My Decision", _two_opts())
        self.assertEqual(d.title, "My Decision")

    def test_title_stripped(self):
        d = self.engine.create_decision("  My Decision  ", _two_opts())
        self.assertEqual(d.title, "My Decision")

    def test_options_stored(self):
        opts = _two_opts()
        d = self.engine.create_decision("D", opts)
        self.assertEqual(d.option_count(), 2)

    def test_id_assigned(self):
        d = self.engine.create_decision("D", _two_opts())
        self.assertTrue(len(d.id) > 0)

    def test_unique_ids(self):
        d1 = self.engine.create_decision("D1", _two_opts())
        d2 = self.engine.create_decision("D2", _two_opts())
        self.assertNotEqual(d1.id, d2.id)

    def test_project_id_stored(self):
        d = self.engine.create_decision("D", _two_opts(), project_id="p1")
        self.assertEqual(d.project_id, "p1")

    def test_discussion_id_stored(self):
        d = self.engine.create_decision("D", _two_opts(), discussion_id="disc-1")
        self.assertEqual(d.discussion_id, "disc-1")

    def test_no_project_id_by_default(self):
        d = self.engine.create_decision("D", _two_opts())
        self.assertIsNone(d.project_id)

    def test_no_discussion_id_by_default(self):
        d = self.engine.create_decision("D", _two_opts())
        self.assertIsNone(d.discussion_id)

    def test_raises_empty_title(self):
        with self.assertRaises(InvalidDecisionError):
            self.engine.create_decision("", _two_opts())

    def test_raises_whitespace_title(self):
        with self.assertRaises(InvalidDecisionError):
            self.engine.create_decision("   ", _two_opts())

    def test_raises_single_option(self):
        with self.assertRaises(InvalidDecisionError):
            self.engine.create_decision("D", [_opt("Only")])

    def test_raises_zero_options(self):
        with self.assertRaises(InvalidDecisionError):
            self.engine.create_decision("D", [])

    def test_raises_duplicate_option_titles(self):
        opts = [_opt("Same"), _opt("Same")]
        with self.assertRaises(InvalidDecisionError):
            self.engine.create_decision("D", opts)

    def test_three_options_allowed(self):
        opts = [_opt("A"), _opt("B"), _opt("C")]
        d = self.engine.create_decision("D", opts)
        self.assertEqual(d.option_count(), 3)

    def test_appears_in_history(self):
        self.engine.create_decision("D", _two_opts())
        self.assertEqual(len(self.engine.history()), 1)


# ---------------------------------------------------------------------------
# evaluate
# ---------------------------------------------------------------------------

class TestEvaluateDecision(unittest.TestCase):

    def setUp(self):
        self.engine = _engine()

    def test_returns_decision(self):
        d = self.engine.create_decision("D", _two_opts())
        result = self.engine.evaluate(d.id)
        self.assertIsInstance(result, Decision)

    def test_status_becomes_evaluated(self):
        d = self.engine.create_decision("D", _two_opts())
        self.engine.evaluate(d.id)
        self.assertEqual(d.status, DecisionStatus.EVALUATED)

    def test_recommendation_set(self):
        d = self.engine.create_decision("D", _two_opts())
        self.engine.evaluate(d.id)
        self.assertIsNotNone(d.recommendation)

    def test_confidence_set(self):
        d = self.engine.create_decision("D", _two_opts())
        self.engine.evaluate(d.id)
        self.assertGreaterEqual(d.confidence, 0.5)

    def test_evaluated_at_set(self):
        d = self.engine.create_decision("D", _two_opts())
        self.engine.evaluate(d.id)
        self.assertIsNotNone(d.evaluated_at)

    def test_risk_level_set(self):
        d = self.engine.create_decision("D", _two_opts())
        self.engine.evaluate(d.id)
        self.assertIsNotNone(d.risk_level)
        self.assertIsInstance(d.risk_level, DecisionRiskLevel)

    def test_rules_applied_set(self):
        d = self.engine.create_decision("D", _two_opts())
        self.engine.evaluate(d.id)
        self.assertTrue(len(d.rules_applied) > 0)

    def test_reasoning_set(self):
        d = self.engine.create_decision("D", _two_opts())
        self.engine.evaluate(d.id)
        self.assertTrue(len(d.reasoning) > 0)

    def test_custom_rules_applied(self):
        d = self.engine.create_decision("D", _two_opts())
        rules = [DecisionRule.lowest_risk()]
        self.engine.evaluate(d.id, rules=rules)
        self.assertEqual(d.rules_applied, ["LOWEST_RISK"])

    def test_raises_not_found(self):
        with self.assertRaises(DecisionNotFoundError):
            self.engine.evaluate("nonexistent-id")

    def test_raises_already_recommended(self):
        d = self.engine.create_decision("D", _two_opts())
        self.engine.evaluate(d.id)
        self.engine.recommend(d.id)
        with self.assertRaises(DecisionAlreadyRecommendedError):
            self.engine.evaluate(d.id)

    def test_can_reevaluate_evaluated(self):
        d = self.engine.create_decision("D", _two_opts())
        self.engine.evaluate(d.id)
        self.engine.evaluate(d.id, rules=[DecisionRule.lowest_risk()])
        self.assertEqual(d.rules_applied, ["LOWEST_RISK"])

    def test_deterministic_winner_high_risk_beats_no_advantages(self):
        opt_safe = DecisionOption(
            title="Safe", advantages=["Proven"], disadvantages=[],
            estimated_risk="LOW", estimated_cost="LOW",
        )
        opt_risky = DecisionOption(
            title="Risky", advantages=[], disadvantages=["Risky"],
            estimated_risk="CRITICAL", estimated_cost="HIGH",
        )
        d = self.engine.create_decision("D", [opt_safe, opt_risky])
        self.engine.evaluate(d.id)
        self.assertEqual(d.recommendation, "Safe")

    def test_all_equal_options_recommendation_is_first(self):
        opt_a = DecisionOption(title="A")
        opt_b = DecisionOption(title="B")
        d = self.engine.create_decision("D", [opt_a, opt_b])
        self.engine.evaluate(d.id)
        self.assertEqual(d.recommendation, "A")

    def test_default_rules_five_rules(self):
        d = self.engine.create_decision("D", _two_opts())
        self.engine.evaluate(d.id)
        self.assertEqual(len(d.rules_applied), 5)

    def test_recommended_option_is_in_options(self):
        opts = [_opt("X"), _opt("Y"), _opt("Z")]
        d = self.engine.create_decision("D", opts)
        self.engine.evaluate(d.id)
        titles = [o.title for o in d.options]
        self.assertIn(d.recommendation, titles)

    def test_risk_level_derives_from_winner(self):
        safe = DecisionOption(title="Safe", advantages=["a", "b", "c"],
                              estimated_risk="LOW", estimated_cost="LOW")
        risky = DecisionOption(title="Risky", disadvantages=["x"],
                               estimated_risk="CRITICAL", estimated_cost="HIGH")
        d = self.engine.create_decision("D", [safe, risky])
        self.engine.evaluate(d.id)
        self.assertEqual(d.risk_level, DecisionRiskLevel.LOW)


# ---------------------------------------------------------------------------
# recommend
# ---------------------------------------------------------------------------

class TestRecommendDecision(unittest.TestCase):

    def setUp(self):
        self.engine = _engine()

    def _prepare(self, opts=None):
        d = self.engine.create_decision("D", opts or _two_opts())
        self.engine.evaluate(d.id)
        return d

    def test_returns_decision_result(self):
        d = self._prepare()
        r = self.engine.recommend(d.id)
        self.assertIsInstance(r, DecisionResult)

    def test_status_becomes_recommended(self):
        d = self._prepare()
        self.engine.recommend(d.id)
        self.assertEqual(d.status, DecisionStatus.RECOMMENDED)

    def test_result_stored_on_decision(self):
        d = self._prepare()
        r = self.engine.recommend(d.id)
        self.assertIsNotNone(d.result)
        self.assertIs(d.result, r)

    def test_selected_option_matches_recommendation(self):
        d = self._prepare()
        r = self.engine.recommend(d.id)
        self.assertEqual(r.selected_option.title, d.recommendation)

    def test_reasoning_non_empty(self):
        d = self._prepare()
        r = self.engine.recommend(d.id)
        self.assertTrue(len(r.reasoning) > 0)

    def test_confidence_in_range(self):
        d = self._prepare()
        r = self.engine.recommend(d.id)
        self.assertGreaterEqual(r.confidence, 0.5)
        self.assertLessEqual(r.confidence, 1.0)

    def test_raises_not_found(self):
        with self.assertRaises(DecisionNotFoundError):
            self.engine.recommend("nonexistent")

    def test_raises_not_evaluated(self):
        d = self.engine.create_decision("D", _two_opts())
        with self.assertRaises(DecisionNotEvaluatedError):
            self.engine.recommend(d.id)

    def test_idempotent_returns_same_result(self):
        d = self._prepare()
        r1 = self.engine.recommend(d.id)
        r2 = self.engine.recommend(d.id)
        self.assertIs(r1, r2)

    def test_idempotent_status_stays_recommended(self):
        d = self._prepare()
        self.engine.recommend(d.id)
        self.engine.recommend(d.id)
        self.assertEqual(d.status, DecisionStatus.RECOMMENDED)

    def test_requires_ceo_false_for_low_risk(self):
        safe = DecisionOption(title="Safe", advantages=["a", "b", "c"],
                              estimated_risk="LOW", estimated_cost="LOW")
        risky = DecisionOption(title="Risky", disadvantages=["x"],
                               estimated_risk="CRITICAL", estimated_cost="HIGH")
        d = self.engine.create_decision("D", [safe, risky])
        self.engine.evaluate(d.id)
        r = self.engine.recommend(d.id)
        self.assertFalse(r.requires_ceo_approval)

    def test_requires_ceo_true_for_high_risk(self):
        risky_a = DecisionOption(title="A", advantages=["a", "b", "c", "d"],
                                 estimated_risk="HIGH", estimated_cost="LOW")
        risky_b = DecisionOption(title="B", estimated_risk="CRITICAL",
                                 estimated_cost="HIGH")
        d = self.engine.create_decision("D", [risky_a, risky_b])
        self.engine.evaluate(d.id, rules=[DecisionRule.most_advantages()])
        r = self.engine.recommend(d.id)
        self.assertTrue(r.requires_ceo_approval)

    def test_evaluated_at_matches_decision(self):
        d = self._prepare()
        r = self.engine.recommend(d.id)
        self.assertEqual(r.evaluated_at, d.evaluated_at)

    def test_no_supporting_evidence_without_engines(self):
        d = self._prepare()
        r = self.engine.recommend(d.id)
        self.assertFalse(r.has_supporting_evidence())

    def test_confidence_matches_decision(self):
        d = self._prepare()
        r = self.engine.recommend(d.id)
        self.assertAlmostEqual(r.confidence, d.confidence)


# ---------------------------------------------------------------------------
# CEO Approval
# ---------------------------------------------------------------------------

class TestDecisionEngineCEOApproval(unittest.TestCase):

    def setUp(self):
        self.engine = _engine()

    def _evaluate_winner(self, winner_risk: str):
        loser = DecisionOption(title="Loser", estimated_risk="CRITICAL", estimated_cost="HIGH")
        winner = DecisionOption(
            title="Winner",
            advantages=["a", "b", "c", "d", "e"],
            estimated_risk=winner_risk,
            estimated_cost="LOW",
        )
        d = self.engine.create_decision("D", [winner, loser])
        self.engine.evaluate(d.id)
        return d

    def test_low_risk_no_ceo_approval(self):
        d = self._evaluate_winner("LOW")
        self.assertFalse(d.requires_ceo_approval())

    def test_medium_risk_no_ceo_approval(self):
        d = self._evaluate_winner("MEDIUM")
        self.assertFalse(d.requires_ceo_approval())

    def test_high_risk_requires_ceo(self):
        risky = DecisionOption(title="Risky", advantages=["a"] * 10,
                               estimated_risk="HIGH", estimated_cost="LOW")
        safe = DecisionOption(title="Safe", estimated_risk="LOW",
                              estimated_cost="LOW")
        d = self.engine.create_decision("D", [risky, safe])
        self.engine.evaluate(d.id, rules=[DecisionRule.most_advantages()])
        self.assertTrue(d.requires_ceo_approval())

    def test_critical_risk_requires_ceo(self):
        critical = DecisionOption(title="Critical", advantages=["a"] * 10,
                                  estimated_risk="CRITICAL", estimated_cost="LOW")
        safe = DecisionOption(title="Safe", estimated_risk="LOW", estimated_cost="LOW")
        d = self.engine.create_decision("D", [critical, safe])
        self.engine.evaluate(d.id, rules=[DecisionRule.most_advantages()])
        self.assertTrue(d.requires_ceo_approval())

    def test_result_ceo_approval_true(self):
        risky = DecisionOption(title="Risky", advantages=["a"] * 10,
                               estimated_risk="HIGH", estimated_cost="LOW")
        safe = DecisionOption(title="Safe", estimated_risk="LOW", estimated_cost="LOW")
        d = self.engine.create_decision("D", [risky, safe])
        self.engine.evaluate(d.id, rules=[DecisionRule.most_advantages()])
        r = self.engine.recommend(d.id)
        self.assertTrue(r.requires_ceo_approval)

    def test_result_ceo_approval_false_for_low_risk_winner(self):
        d = self._evaluate_winner("LOW")
        r = self.engine.recommend(d.id)
        self.assertFalse(r.requires_ceo_approval)

    def test_ceo_approval_false_before_evaluation(self):
        d = self.engine.create_decision("D", _two_opts())
        self.assertFalse(d.requires_ceo_approval())

    def test_risk_level_high_sets_approval(self):
        d = self.engine.create_decision("D", _two_opts())
        d.risk_level = DecisionRiskLevel.HIGH
        self.assertTrue(d.requires_ceo_approval())

    def test_risk_level_low_clears_approval(self):
        d = self.engine.create_decision("D", _two_opts())
        d.risk_level = DecisionRiskLevel.LOW
        self.assertFalse(d.requires_ceo_approval())

    def test_engine_never_approves_only_recommends(self):
        d = self.engine.create_decision("D", _two_opts())
        self.engine.evaluate(d.id)
        r = self.engine.recommend(d.id)
        self.assertIsInstance(r, DecisionResult)
        self.assertNotEqual(d.status, "APPROVED")
        self.assertNotIn("APPROVED", [s.value for s in DecisionStatus])


# ---------------------------------------------------------------------------
# history
# ---------------------------------------------------------------------------

class TestDecisionEngineHistory(unittest.TestCase):

    def setUp(self):
        self.engine = _engine()

    def test_empty_initially(self):
        self.assertEqual(self.engine.history(), [])

    def test_one_decision(self):
        self.engine.create_decision("D", _two_opts())
        self.assertEqual(len(self.engine.history()), 1)

    def test_multiple_decisions(self):
        for i in range(5):
            self.engine.create_decision(f"D{i}", _two_opts())
        self.assertEqual(len(self.engine.history()), 5)

    def test_ordered_by_created_at(self):
        for i in range(3):
            self.engine.create_decision(f"D{i}", _two_opts())
        h = self.engine.history()
        for i in range(len(h) - 1):
            self.assertLessEqual(h[i].created_at, h[i + 1].created_at)

    def test_returns_new_list(self):
        self.engine.create_decision("D", _two_opts())
        h1 = self.engine.history()
        h2 = self.engine.history()
        self.assertIsNot(h1, h2)

    def test_includes_recommended_decisions(self):
        d = self.engine.create_decision("D", _two_opts())
        self.engine.evaluate(d.id)
        self.engine.recommend(d.id)
        self.assertEqual(len(self.engine.history()), 1)

    def test_decision_objects_are_same_instances(self):
        d = self.engine.create_decision("D", _two_opts())
        h = self.engine.history()
        self.assertIs(h[0], d)

    def test_history_count_matches_total_decisions(self):
        for i in range(7):
            self.engine.create_decision(f"D{i}", _two_opts())
        self.assertEqual(len(self.engine.history()), self.engine.statistics()["total_decisions"])


# ---------------------------------------------------------------------------
# statistics
# ---------------------------------------------------------------------------

class TestDecisionEngineStatistics(unittest.TestCase):

    def setUp(self):
        self.engine = _engine()

    def test_empty_stats(self):
        s = self.engine.statistics()
        self.assertEqual(s["total_decisions"], 0)
        self.assertEqual(s["requiring_ceo_approval"], 0)
        self.assertEqual(s["high_confidence_count"], 0)
        self.assertAlmostEqual(s["average_confidence"], 0.0)
        self.assertAlmostEqual(s["average_option_count"], 0.0)

    def test_total_decisions(self):
        for i in range(3):
            self.engine.create_decision(f"D{i}", _two_opts())
        self.assertEqual(self.engine.statistics()["total_decisions"], 3)

    def test_by_status_pending(self):
        for i in range(2):
            self.engine.create_decision(f"D{i}", _two_opts())
        s = self.engine.statistics()
        self.assertEqual(s["by_status"]["PENDING"], 2)

    def test_by_status_evaluated(self):
        d = self.engine.create_decision("D", _two_opts())
        self.engine.evaluate(d.id)
        s = self.engine.statistics()
        self.assertEqual(s["by_status"]["EVALUATED"], 1)

    def test_by_status_recommended(self):
        d = self.engine.create_decision("D", _two_opts())
        self.engine.evaluate(d.id)
        self.engine.recommend(d.id)
        s = self.engine.statistics()
        self.assertEqual(s["by_status"]["RECOMMENDED"], 1)

    def test_by_risk_level_populated(self):
        d = self.engine.create_decision("D", _two_opts())
        self.engine.evaluate(d.id)
        s = self.engine.statistics()
        total = sum(s["by_risk_level"].values())
        self.assertEqual(total, 1)

    def test_requiring_ceo_approval_count(self):
        risky = DecisionOption(title="Risky", advantages=["a"] * 10,
                               estimated_risk="HIGH", estimated_cost="LOW")
        safe = DecisionOption(title="Safe", estimated_risk="LOW", estimated_cost="LOW")
        d = self.engine.create_decision("D", [risky, safe])
        self.engine.evaluate(d.id, rules=[DecisionRule.most_advantages()])
        self.assertEqual(self.engine.statistics()["requiring_ceo_approval"], 1)

    def test_average_option_count(self):
        self.engine.create_decision("D1", [_opt("A"), _opt("B")])
        self.engine.create_decision("D2", [_opt("X"), _opt("Y"), _opt("Z")])
        s = self.engine.statistics()
        self.assertAlmostEqual(s["average_option_count"], 2.5)

    def test_stats_keys_present(self):
        s = self.engine.statistics()
        for key in ["total_decisions", "by_status", "by_risk_level",
                    "requiring_ceo_approval", "high_confidence_count",
                    "average_confidence", "average_option_count"]:
            self.assertIn(key, s)

    def test_by_status_all_keys_present(self):
        s = self.engine.statistics()
        for status in ["PENDING", "EVALUATED", "RECOMMENDED"]:
            self.assertIn(status, s["by_status"])

    def test_by_risk_level_all_keys_present(self):
        s = self.engine.statistics()
        for level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
            self.assertIn(level, s["by_risk_level"])

    def test_high_confidence_count(self):
        safe = DecisionOption(title="Safe", advantages=["a", "b", "c"],
                              estimated_risk="LOW", estimated_cost="LOW")
        other = DecisionOption(title="Other", estimated_risk="CRITICAL",
                               estimated_cost="HIGH")
        d = self.engine.create_decision("D", [safe, other])
        self.engine.evaluate(d.id)
        self.engine.recommend(d.id)
        s = self.engine.statistics()
        if d.result.is_high_confidence():
            self.assertEqual(s["high_confidence_count"], 1)


# ---------------------------------------------------------------------------
# Confidence formula
# ---------------------------------------------------------------------------

class TestDecisionEngineConfidence(unittest.TestCase):

    def setUp(self):
        self.engine = _engine()

    def _confidence_for(self, opts, rules=None):
        d = self.engine.create_decision("D", opts)
        self.engine.evaluate(d.id, rules=rules)
        return d.confidence

    def test_tie_gives_0_5(self):
        opts = [DecisionOption(title="A"), DecisionOption(title="B")]
        conf = self._confidence_for(opts)
        self.assertAlmostEqual(conf, 0.5)

    def test_decisive_win_approaches_1(self):
        winner = DecisionOption(title="W", advantages=["a", "b", "c", "d"],
                                disadvantages=[], estimated_risk="LOW", estimated_cost="LOW")
        loser = DecisionOption(title="L", advantages=[],
                               disadvantages=["x", "y", "z"],
                               estimated_risk="CRITICAL", estimated_cost="HIGH")
        conf = self._confidence_for([winner, loser])
        self.assertGreater(conf, 0.8)

    def test_confidence_always_at_least_0_5(self):
        for _ in range(5):
            opts = [_opt(f"O{i}") for i in range(3)]
            d = self.engine.create_decision(f"D-{uuid4()}", opts)
            self.engine.evaluate(d.id)
            self.assertGreaterEqual(d.confidence, 0.5)

    def test_confidence_at_most_1_0(self):
        for _ in range(5):
            opts = [_opt(f"O{i}") for i in range(2)]
            d = self.engine.create_decision(f"D-{uuid4()}", opts)
            self.engine.evaluate(d.id)
            self.assertLessEqual(d.confidence, 1.0)

    def test_two_options_decisive(self):
        winner = DecisionOption(title="W", advantages=["a", "b"],
                                estimated_risk="LOW", estimated_cost="LOW")
        loser = DecisionOption(title="L", disadvantages=["x"],
                               estimated_risk="CRITICAL", estimated_cost="HIGH")
        conf = self._confidence_for([winner, loser])
        self.assertGreater(conf, 0.5)

    def test_three_tied_options(self):
        opts = [DecisionOption(title=t) for t in ["A", "B", "C"]]
        conf = self._confidence_for(opts)
        self.assertAlmostEqual(conf, 0.5)

    def test_single_rule_risk_only(self):
        low = DecisionOption(title="Low", estimated_risk="LOW")
        crit = DecisionOption(title="Crit", estimated_risk="CRITICAL")
        opts = [low, crit]
        conf = self._confidence_for(opts, rules=[DecisionRule.lowest_risk()])
        self.assertGreater(conf, 0.5)

    def test_confidence_stored_on_decision(self):
        d = self.engine.create_decision("D", _two_opts())
        self.engine.evaluate(d.id)
        self.assertGreaterEqual(d.confidence, 0.5)
        self.assertLessEqual(d.confidence, 1.0)

    def test_winner_with_all_rules_advantage(self):
        winner = DecisionOption(
            title="Winner",
            advantages=["a", "b", "c"],
            disadvantages=[],
            estimated_risk="LOW",
            estimated_cost="LOW",
        )
        loser = DecisionOption(
            title="Loser",
            advantages=[],
            disadvantages=["x", "y"],
            estimated_risk="HIGH",
            estimated_cost="HIGH",
        )
        conf = self._confidence_for([winner, loser])
        self.assertEqual(conf, 1.0)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

class TestDecisionEngineScoring(unittest.TestCase):

    def setUp(self):
        self.engine = _engine()

    def test_lowest_risk_rule_selects_safest(self):
        safe = DecisionOption(title="Safe", estimated_risk="LOW")
        risky = DecisionOption(title="Risky", estimated_risk="CRITICAL")
        d = self.engine.create_decision("D", [safe, risky])
        self.engine.evaluate(d.id, rules=[DecisionRule.lowest_risk()])
        self.assertEqual(d.recommendation, "Safe")

    def test_most_advantages_rule_selects_most_advantages(self):
        many = DecisionOption(title="Many", advantages=["a", "b", "c"])
        few = DecisionOption(title="Few", advantages=["x"])
        d = self.engine.create_decision("D", [many, few])
        self.engine.evaluate(d.id, rules=[DecisionRule.most_advantages()])
        self.assertEqual(d.recommendation, "Many")

    def test_fewest_disadvantages_rule(self):
        clean = DecisionOption(title="Clean", disadvantages=[])
        messy = DecisionOption(title="Messy", disadvantages=["x", "y", "z"])
        d = self.engine.create_decision("D", [clean, messy])
        self.engine.evaluate(d.id, rules=[DecisionRule.fewest_disadvantages()])
        self.assertEqual(d.recommendation, "Clean")

    def test_lowest_cost_rule(self):
        cheap = DecisionOption(title="Cheap", estimated_cost="LOW")
        expensive = DecisionOption(title="Expensive", estimated_cost="HIGH")
        d = self.engine.create_decision("D", [cheap, expensive])
        self.engine.evaluate(d.id, rules=[DecisionRule.lowest_cost()])
        self.assertEqual(d.recommendation, "Cheap")

    def test_best_balance_rule(self):
        positive = DecisionOption(title="Pos", advantages=["a", "b", "c"], disadvantages=["x"])
        negative = DecisionOption(title="Neg", advantages=["a"], disadvantages=["x", "y", "z"])
        d = self.engine.create_decision("D", [positive, negative])
        self.engine.evaluate(d.id, rules=[DecisionRule.best_balance()])
        self.assertEqual(d.recommendation, "Pos")

    def test_heavy_weight_dominates(self):
        mostly_safe = DecisionOption(title="MostlySafe", advantages=["a"],
                                     estimated_risk="MEDIUM")
        very_risky = DecisionOption(title="VeryRisky", advantages=["a", "b", "c"],
                                    estimated_risk="CRITICAL")
        rules = [
            DecisionRule(name="LOWEST_RISK", description="Risk", weight=10.0),
            DecisionRule(name="MOST_ADVANTAGES", description="Adv", weight=1.0),
        ]
        d = self.engine.create_decision("D", [mostly_safe, very_risky])
        self.engine.evaluate(d.id, rules=rules)
        self.assertEqual(d.recommendation, "MostlySafe")

    def test_unknown_rule_name_ignored(self):
        opts = _two_opts()
        d = self.engine.create_decision("D", opts)
        rules = [DecisionRule(name="UNKNOWN_RULE", description="Unknown", weight=100.0)]
        self.engine.evaluate(d.id, rules=rules)
        self.assertIsNotNone(d.recommendation)

    def test_deterministic_same_result_repeated(self):
        opts = [
            DecisionOption(title="A", advantages=["a", "b"], estimated_risk="LOW"),
            DecisionOption(title="B", advantages=["x"], estimated_risk="HIGH"),
        ]
        d1 = self.engine.create_decision("D1", opts)
        self.engine.evaluate(d1.id)

        engine2 = _engine()
        d2 = engine2.create_decision("D2", opts)
        engine2.evaluate(d2.id)

        self.assertEqual(d1.recommendation, d2.recommendation)
        self.assertAlmostEqual(d1.confidence, d2.confidence)

    def test_three_options_correct_winner(self):
        best = DecisionOption(title="Best", advantages=["a", "b", "c"],
                              disadvantages=[], estimated_risk="LOW", estimated_cost="LOW")
        mid = DecisionOption(title="Mid", advantages=["a"],
                             disadvantages=["x"], estimated_risk="MEDIUM", estimated_cost="MEDIUM")
        worst = DecisionOption(title="Worst", advantages=[],
                               disadvantages=["x", "y"], estimated_risk="HIGH", estimated_cost="HIGH")
        d = self.engine.create_decision("D", [best, mid, worst])
        self.engine.evaluate(d.id)
        self.assertEqual(d.recommendation, "Best")

    def test_risk_level_of_winner_reflects_option(self):
        safe = DecisionOption(title="Safe", advantages=["a", "b", "c"],
                              estimated_risk="LOW")
        risky = DecisionOption(title="Risky", estimated_risk="CRITICAL")
        d = self.engine.create_decision("D", [safe, risky])
        self.engine.evaluate(d.id)
        self.assertEqual(d.risk_level, DecisionRiskLevel.LOW)

    def test_reasoning_contains_winner_title(self):
        opts = [_opt("Alpha"), _opt("Beta")]
        d = self.engine.create_decision("D", opts)
        self.engine.evaluate(d.id)
        self.assertIn(d.recommendation, d.reasoning)

    def test_reasoning_contains_rule_names(self):
        d = self.engine.create_decision("D", _two_opts())
        self.engine.evaluate(d.id, rules=[DecisionRule.lowest_risk()])
        self.assertIn("LOWEST_RISK", d.reasoning)

    def test_custom_rule_set_five_rules(self):
        d = self.engine.create_decision("D", _two_opts())
        all_rules = [
            DecisionRule.lowest_risk(),
            DecisionRule.most_advantages(),
            DecisionRule.fewest_disadvantages(),
            DecisionRule.lowest_cost(),
            DecisionRule.best_balance(),
        ]
        self.engine.evaluate(d.id, rules=all_rules)
        self.assertEqual(len(d.rules_applied), 5)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestDecisionEngineErrors(unittest.TestCase):

    def setUp(self):
        self.engine = _engine()

    def test_exception_hierarchy_not_found(self):
        self.assertTrue(issubclass(DecisionNotFoundError, DecisionEngineError))

    def test_exception_hierarchy_invalid(self):
        self.assertTrue(issubclass(InvalidDecisionError, DecisionEngineError))

    def test_exception_hierarchy_already_recommended(self):
        self.assertTrue(issubclass(DecisionAlreadyRecommendedError, DecisionEngineError))

    def test_exception_hierarchy_not_evaluated(self):
        self.assertTrue(issubclass(DecisionNotEvaluatedError, DecisionEngineError))

    def test_find_decision_not_found(self):
        with self.assertRaises(DecisionNotFoundError):
            self.engine.find_decision("bad-id")

    def test_find_decision_found(self):
        d = self.engine.create_decision("D", _two_opts())
        found = self.engine.find_decision(d.id)
        self.assertIs(found, d)

    def test_evaluate_raises_for_missing_id(self):
        with self.assertRaises(DecisionNotFoundError):
            self.engine.evaluate("missing")

    def test_recommend_raises_for_missing_id(self):
        with self.assertRaises(DecisionNotFoundError):
            self.engine.recommend("missing")

    def test_create_invalid_title_raises(self):
        with self.assertRaises(InvalidDecisionError):
            self.engine.create_decision("", _two_opts())

    def test_create_too_few_options_raises(self):
        with self.assertRaises(InvalidDecisionError):
            self.engine.create_decision("D", [_opt("Solo")])

    def test_create_duplicate_titles_raises(self):
        opts = [_opt("Same"), _opt("Same")]
        with self.assertRaises(InvalidDecisionError):
            self.engine.create_decision("D", opts)

    def test_evaluate_already_recommended_raises(self):
        d = self.engine.create_decision("D", _two_opts())
        self.engine.evaluate(d.id)
        self.engine.recommend(d.id)
        with self.assertRaises(DecisionAlreadyRecommendedError):
            self.engine.evaluate(d.id)

    def test_recommend_pending_raises(self):
        d = self.engine.create_decision("D", _two_opts())
        with self.assertRaises(DecisionNotEvaluatedError):
            self.engine.recommend(d.id)


# ---------------------------------------------------------------------------
# Memory Engine integration
# ---------------------------------------------------------------------------

class _MockMemoryEngine:
    """Minimal stub for MemoryEngine used in integration tests."""

    def __init__(self, entries=None):
        self._entries = entries or []

    def find_by_project(self, project_id):
        return [e for e in self._entries if getattr(e, "project_id", None) == project_id]


class _MockEntry:
    def __init__(self, entry_id, project_id):
        self.id = entry_id
        self.project_id = project_id


class TestDecisionEngineWithMemory(unittest.TestCase):

    def setUp(self):
        entries = [
            _MockEntry("mem-1", "proj-1"),
            _MockEntry("mem-2", "proj-1"),
            _MockEntry("mem-3", "proj-2"),
        ]
        self.mem = _MockMemoryEngine(entries)
        self.engine = DecisionEngine(memory_engine=self.mem)

    def test_supporting_memory_attached(self):
        d = self.engine.create_decision("D", _two_opts(), project_id="proj-1")
        self.engine.evaluate(d.id)
        r = self.engine.recommend(d.id)
        self.assertEqual(sorted(r.supporting_memory), ["mem-1", "mem-2"])

    def test_no_supporting_memory_wrong_project(self):
        d = self.engine.create_decision("D", _two_opts(), project_id="no-match")
        self.engine.evaluate(d.id)
        r = self.engine.recommend(d.id)
        self.assertEqual(r.supporting_memory, [])

    def test_no_supporting_memory_no_project_id(self):
        d = self.engine.create_decision("D", _two_opts())
        self.engine.evaluate(d.id)
        r = self.engine.recommend(d.id)
        self.assertEqual(r.supporting_memory, [])

    def test_supporting_memory_correct_project(self):
        d = self.engine.create_decision("D", _two_opts(), project_id="proj-2")
        self.engine.evaluate(d.id)
        r = self.engine.recommend(d.id)
        self.assertEqual(r.supporting_memory, ["mem-3"])

    def test_has_supporting_evidence_with_memory(self):
        d = self.engine.create_decision("D", _two_opts(), project_id="proj-1")
        self.engine.evaluate(d.id)
        r = self.engine.recommend(d.id)
        self.assertTrue(r.has_supporting_evidence())

    def test_memory_engine_stored(self):
        self.assertIs(self.engine._memory_engine, self.mem)

    def test_engine_works_without_memory_engine(self):
        plain = DecisionEngine()
        d = plain.create_decision("D", _two_opts())
        plain.evaluate(d.id)
        r = plain.recommend(d.id)
        self.assertEqual(r.supporting_memory, [])


# ---------------------------------------------------------------------------
# Discussion Engine integration
# ---------------------------------------------------------------------------

class _MockDiscussion:
    def __init__(self, disc_id):
        self.id = disc_id


class _MockDiscussionEngine:
    def __init__(self, discussions=None):
        self._store = {d.id: d for d in (discussions or [])}

    def find(self, disc_id):
        if disc_id not in self._store:
            raise KeyError(f"Discussion {disc_id} not found")
        return self._store[disc_id]


class TestDecisionEngineWithDiscussion(unittest.TestCase):

    def setUp(self):
        disc = _MockDiscussion("disc-1")
        self.disc_engine = _MockDiscussionEngine([disc])
        self.engine = DecisionEngine(discussion_engine=self.disc_engine)

    def test_supporting_discussion_attached(self):
        d = self.engine.create_decision("D", _two_opts(), discussion_id="disc-1")
        self.engine.evaluate(d.id)
        r = self.engine.recommend(d.id)
        self.assertEqual(r.supporting_discussions, ["disc-1"])

    def test_no_supporting_discussion_without_id(self):
        d = self.engine.create_decision("D", _two_opts())
        self.engine.evaluate(d.id)
        r = self.engine.recommend(d.id)
        self.assertEqual(r.supporting_discussions, [])

    def test_no_supporting_discussion_missing(self):
        d = self.engine.create_decision("D", _two_opts(), discussion_id="missing")
        self.engine.evaluate(d.id)
        r = self.engine.recommend(d.id)
        self.assertEqual(r.supporting_discussions, [])

    def test_has_supporting_evidence_with_discussion(self):
        d = self.engine.create_decision("D", _two_opts(), discussion_id="disc-1")
        self.engine.evaluate(d.id)
        r = self.engine.recommend(d.id)
        self.assertTrue(r.has_supporting_evidence())

    def test_engine_works_without_discussion_engine(self):
        plain = DecisionEngine()
        d = plain.create_decision("D", _two_opts(), discussion_id="disc-1")
        plain.evaluate(d.id)
        r = plain.recommend(d.id)
        self.assertEqual(r.supporting_discussions, [])

    def test_discussion_engine_stored(self):
        self.assertIs(self.engine._discussion_engine, self.disc_engine)

    def test_both_engines_combined(self):
        entries = [_MockEntry("mem-1", "proj-1")]
        mem = _MockMemoryEngine(entries)
        engine = DecisionEngine(memory_engine=mem, discussion_engine=self.disc_engine)
        d = engine.create_decision("D", _two_opts(),
                                   project_id="proj-1", discussion_id="disc-1")
        engine.evaluate(d.id)
        r = engine.recommend(d.id)
        self.assertIn("mem-1", r.supporting_memory)
        self.assertIn("disc-1", r.supporting_discussions)


# ---------------------------------------------------------------------------
# End-to-end pipeline
# ---------------------------------------------------------------------------

class TestDecisionEnginePipeline(unittest.TestCase):

    def setUp(self):
        self.engine = _engine()

    def test_full_pipeline_pending_to_recommended(self):
        d = self.engine.create_decision("Architecture choice", _two_opts())
        self.assertEqual(d.status, DecisionStatus.PENDING)

        self.engine.evaluate(d.id)
        self.assertEqual(d.status, DecisionStatus.EVALUATED)

        r = self.engine.recommend(d.id)
        self.assertEqual(d.status, DecisionStatus.RECOMMENDED)
        self.assertIsNotNone(r)

    def test_multiple_decisions_independent(self):
        d1 = self.engine.create_decision("D1", [_opt("A"), _opt("B")])
        d2 = self.engine.create_decision("D2", [_opt("X"), _opt("Y")])

        self.engine.evaluate(d1.id)
        self.assertEqual(d2.status, DecisionStatus.PENDING)

        self.engine.recommend(d1.id)
        self.assertEqual(d2.status, DecisionStatus.PENDING)
        self.assertEqual(len(self.engine.history()), 2)

    def test_six_options_best_wins(self):
        opts = [
            DecisionOption(title=f"Opt{i}",
                           advantages=["a"] * i,
                           estimated_risk="LOW",
                           estimated_cost="LOW")
            for i in range(6)
        ]
        d = self.engine.create_decision("D", opts)
        self.engine.evaluate(d.id, rules=[DecisionRule.most_advantages()])
        self.assertEqual(d.recommendation, "Opt5")

    def test_reevaluate_changes_recommendation(self):
        many_adv = DecisionOption(title="ManyAdv", advantages=["a", "b", "c"],
                                  estimated_risk="CRITICAL", estimated_cost="HIGH")
        safe = DecisionOption(title="Safe", advantages=[],
                              estimated_risk="LOW", estimated_cost="LOW")
        d = self.engine.create_decision("D", [many_adv, safe])

        self.engine.evaluate(d.id, rules=[DecisionRule.most_advantages()])
        self.assertEqual(d.recommendation, "ManyAdv")

        self.engine.evaluate(d.id, rules=[DecisionRule.lowest_risk()])
        self.assertEqual(d.recommendation, "Safe")

    def test_result_option_in_original_options(self):
        opts = [_opt("Alpha"), _opt("Beta"), _opt("Gamma")]
        d = self.engine.create_decision("D", opts)
        self.engine.evaluate(d.id)
        r = self.engine.recommend(d.id)
        titles = [o.title for o in d.options]
        self.assertIn(r.selected_option.title, titles)

    def test_statistics_reflect_pipeline_progress(self):
        d1 = self.engine.create_decision("D1", _two_opts())
        d2 = self.engine.create_decision("D2", _two_opts())
        self.engine.evaluate(d1.id)
        self.engine.recommend(d1.id)

        s = self.engine.statistics()
        self.assertEqual(s["total_decisions"], 2)
        self.assertEqual(s["by_status"]["RECOMMENDED"], 1)
        self.assertEqual(s["by_status"]["PENDING"], 1)

    def test_full_ceo_approval_flow(self):
        critical = DecisionOption(title="Critical", advantages=["a"] * 10,
                                  estimated_risk="CRITICAL", estimated_cost="LOW")
        safe = DecisionOption(title="Safe", estimated_risk="LOW", estimated_cost="LOW")

        d = self.engine.create_decision("Risky decision", [critical, safe])
        self.engine.evaluate(d.id, rules=[DecisionRule.most_advantages()])
        r = self.engine.recommend(d.id)

        self.assertEqual(r.selected_option.title, "Critical")
        self.assertTrue(r.requires_ceo_approval)
        self.assertEqual(d.risk_level, DecisionRiskLevel.CRITICAL)

    def test_summary_complete_after_pipeline(self):
        d = self.engine.create_decision("D", _two_opts())
        self.engine.evaluate(d.id)
        self.engine.recommend(d.id)
        s = d.summary()
        self.assertIsNotNone(s["recommendation"])
        self.assertIsNotNone(s["risk_level"])
        self.assertIsNotNone(s["evaluated_at"])
        self.assertEqual(s["status"], "RECOMMENDED")


if __name__ == "__main__":
    unittest.main()
