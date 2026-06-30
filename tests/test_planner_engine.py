"""
Comprehensive unit tests for Sprint 4 — Planner Engine.

Covers: ProjectType, RiskLevel, RiskCategory, Risk, Department,
DepartmentRequirement, ProjectBlueprint, and PlannerEngine (all methods
tested through the public analyze() API).

Run with:
    .venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_planner_engine.py" -v
"""

import unittest
from datetime import datetime, timezone

from core.department_requirement import Department, DepartmentRequirement
from core.project_blueprint import ProjectBlueprint
from core.project_type import ProjectType
from core.risk import Risk, RiskCategory, RiskLevel
from core.planner_engine import PlannerEngine, RequestAnalysisError


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _engine() -> PlannerEngine:
    return PlannerEngine()


def _analyze(request: str) -> ProjectBlueprint:
    return _engine().analyze(request)


# ---------------------------------------------------------------------------
# TestProjectType
# ---------------------------------------------------------------------------

class TestProjectType(unittest.TestCase):

    def test_all_ten_values_exist(self) -> None:
        names = {pt.name for pt in ProjectType}
        self.assertEqual(
            names,
            {
                "SAAS", "MOBILE_APP", "WEB_PLATFORM", "AUTOMATION",
                "DESKTOP_APP", "AI_TOOL", "API", "ECOMMERCE",
                "DATA_PIPELINE", "GAME",
            },
        )

    def test_str_returns_value(self) -> None:
        for pt in ProjectType:
            self.assertEqual(str(pt), pt.value)

    def test_is_str_subclass(self) -> None:
        self.assertIsInstance(ProjectType.SAAS, str)

    def test_string_comparison(self) -> None:
        self.assertEqual(ProjectType.API, "API")
        self.assertEqual(ProjectType.GAME, "Game")

    def test_values_are_human_readable(self) -> None:
        for pt in ProjectType:
            self.assertGreater(len(pt.value), 0)
            self.assertFalse(pt.value.startswith("_"))


# ---------------------------------------------------------------------------
# TestRiskLevel
# ---------------------------------------------------------------------------

class TestRiskLevel(unittest.TestCase):

    def test_all_four_values_exist(self) -> None:
        names = {r.name for r in RiskLevel}
        self.assertEqual(names, {"LOW", "MEDIUM", "HIGH", "CRITICAL"})

    def test_str_returns_value(self) -> None:
        for level in RiskLevel:
            self.assertEqual(str(level), level.value)

    def test_is_str_subclass(self) -> None:
        self.assertIsInstance(RiskLevel.HIGH, str)

    def test_string_comparison(self) -> None:
        self.assertEqual(RiskLevel.CRITICAL, "CRITICAL")


# ---------------------------------------------------------------------------
# TestRiskCategory
# ---------------------------------------------------------------------------

class TestRiskCategory(unittest.TestCase):

    def test_all_eleven_values_exist(self) -> None:
        names = {r.name for r in RiskCategory}
        self.assertEqual(
            names,
            {
                "AUTHENTICATION", "PAYMENTS", "REAL_TIME", "NOTIFICATIONS",
                "MAPS", "AI_INTEGRATION", "SCALING", "VIDEO_STREAMING",
                "DATA_PRIVACY", "FILE_STORAGE", "THIRD_PARTY_INTEGRATIONS",
            },
        )

    def test_str_returns_value(self) -> None:
        for cat in RiskCategory:
            self.assertEqual(str(cat), cat.value)

    def test_is_str_subclass(self) -> None:
        self.assertIsInstance(RiskCategory.PAYMENTS, str)


# ---------------------------------------------------------------------------
# TestRisk
# ---------------------------------------------------------------------------

class TestRisk(unittest.TestCase):

    def _make_risk(self) -> Risk:
        return Risk(
            category=RiskCategory.AUTHENTICATION,
            level=RiskLevel.HIGH,
            description="Test description.",
        )

    def test_all_fields_stored(self) -> None:
        risk = self._make_risk()
        self.assertEqual(risk.category, RiskCategory.AUTHENTICATION)
        self.assertEqual(risk.level, RiskLevel.HIGH)
        self.assertEqual(risk.description, "Test description.")

    def test_is_frozen(self) -> None:
        risk = self._make_risk()
        with self.assertRaises(Exception):
            risk.level = RiskLevel.LOW  # type: ignore[misc]

    def test_category_is_risk_category_enum(self) -> None:
        risk = self._make_risk()
        self.assertIsInstance(risk.category, RiskCategory)

    def test_level_is_risk_level_enum(self) -> None:
        risk = self._make_risk()
        self.assertIsInstance(risk.level, RiskLevel)

    def test_description_is_string(self) -> None:
        risk = self._make_risk()
        self.assertIsInstance(risk.description, str)


# ---------------------------------------------------------------------------
# TestDepartment
# ---------------------------------------------------------------------------

class TestDepartment(unittest.TestCase):

    def test_all_eleven_values_exist(self) -> None:
        names = {d.name for d in Department}
        self.assertEqual(
            names,
            {
                "ENGINEERING", "FRONTEND", "BACKEND", "DATABASE",
                "DESIGN", "MARKETING", "QA", "DEVOPS",
                "LEGAL", "SECURITY", "FINANCE",
            },
        )

    def test_str_returns_value(self) -> None:
        for dept in Department:
            self.assertEqual(str(dept), dept.value)

    def test_is_str_subclass(self) -> None:
        self.assertIsInstance(Department.BACKEND, str)

    def test_string_comparison(self) -> None:
        self.assertEqual(Department.QA, "QA")
        self.assertEqual(Department.DEVOPS, "DevOps")


# ---------------------------------------------------------------------------
# TestDepartmentRequirement
# ---------------------------------------------------------------------------

class TestDepartmentRequirement(unittest.TestCase):

    def _make_req(self) -> DepartmentRequirement:
        return DepartmentRequirement(
            department=Department.BACKEND,
            rationale="Handles API and business logic.",
            is_critical=True,
        )

    def test_all_fields_stored(self) -> None:
        req = self._make_req()
        self.assertEqual(req.department, Department.BACKEND)
        self.assertEqual(req.rationale, "Handles API and business logic.")
        self.assertTrue(req.is_critical)

    def test_is_frozen(self) -> None:
        req = self._make_req()
        with self.assertRaises(Exception):
            req.is_critical = False  # type: ignore[misc]

    def test_non_critical_stored(self) -> None:
        req = DepartmentRequirement(
            department=Department.MARKETING,
            rationale="Growth campaigns.",
            is_critical=False,
        )
        self.assertFalse(req.is_critical)

    def test_department_is_enum(self) -> None:
        req = self._make_req()
        self.assertIsInstance(req.department, Department)

    def test_rationale_is_string(self) -> None:
        req = self._make_req()
        self.assertIsInstance(req.rationale, str)


# ---------------------------------------------------------------------------
# TestProjectBlueprint
# ---------------------------------------------------------------------------

class TestProjectBlueprint(unittest.TestCase):

    def _make_blueprint(self) -> ProjectBlueprint:
        return ProjectBlueprint(
            project_title="Test Project",
            objective="Test objective.",
            description="Test description.",
            project_type=ProjectType.API,
            departments=[
                DepartmentRequirement(Department.BACKEND, "Core API.", True),
            ],
            estimated_task_count=20,
            estimated_sprint_count=4,
            estimated_team_size=3,
            complexity_score=2,
            risks=[],
            recommendations=["Use versioning from day one."],
            generated_at=datetime.now(timezone.utc),
            raw_request="Build an API",
        )

    def test_all_fields_stored(self) -> None:
        bp = self._make_blueprint()
        self.assertEqual(bp.project_title, "Test Project")
        self.assertEqual(bp.project_type, ProjectType.API)
        self.assertEqual(bp.complexity_score, 2)
        self.assertEqual(bp.estimated_sprint_count, 4)
        self.assertEqual(bp.raw_request, "Build an API")

    def test_is_frozen_on_scalar_fields(self) -> None:
        bp = self._make_blueprint()
        with self.assertRaises(Exception):
            bp.complexity_score = 9  # type: ignore[misc]

    def test_departments_is_list(self) -> None:
        bp = self._make_blueprint()
        self.assertIsInstance(bp.departments, list)

    def test_risks_is_list(self) -> None:
        bp = self._make_blueprint()
        self.assertIsInstance(bp.risks, list)

    def test_recommendations_is_list(self) -> None:
        bp = self._make_blueprint()
        self.assertIsInstance(bp.recommendations, list)

    def test_generated_at_is_datetime(self) -> None:
        bp = self._make_blueprint()
        self.assertIsInstance(bp.generated_at, datetime)

    def test_project_type_is_enum(self) -> None:
        bp = self._make_blueprint()
        self.assertIsInstance(bp.project_type, ProjectType)


# ---------------------------------------------------------------------------
# TestRequestValidation
# ---------------------------------------------------------------------------

class TestRequestValidation(unittest.TestCase):

    def test_empty_string_raises_error(self) -> None:
        with self.assertRaises(RequestAnalysisError):
            _analyze("")

    def test_whitespace_only_raises_error(self) -> None:
        with self.assertRaises(RequestAnalysisError):
            _analyze("   ")

    def test_too_short_raises_error(self) -> None:
        with self.assertRaises(RequestAnalysisError):
            _analyze("App")

    def test_minimum_valid_request_succeeds(self) -> None:
        bp = _analyze("Build an API service")
        self.assertIsInstance(bp, ProjectBlueprint)

    def test_error_message_is_descriptive(self) -> None:
        try:
            _analyze("")
        except RequestAnalysisError as e:
            self.assertGreater(len(str(e)), 10)


# ---------------------------------------------------------------------------
# TestBlueprintStructure
# ---------------------------------------------------------------------------

class TestBlueprintStructure(unittest.TestCase):

    def setUp(self) -> None:
        self.bp = _analyze("Build a Netflix-like streaming platform")

    def test_returns_project_blueprint_instance(self) -> None:
        self.assertIsInstance(self.bp, ProjectBlueprint)

    def test_project_title_is_non_empty_string(self) -> None:
        self.assertIsInstance(self.bp.project_title, str)
        self.assertGreater(len(self.bp.project_title), 0)

    def test_objective_is_non_empty_string(self) -> None:
        self.assertGreater(len(self.bp.objective), 0)

    def test_description_is_non_empty_string(self) -> None:
        self.assertGreater(len(self.bp.description), 0)

    def test_complexity_score_in_valid_range(self) -> None:
        self.assertGreaterEqual(self.bp.complexity_score, 1)
        self.assertLessEqual(self.bp.complexity_score, 10)

    def test_sprint_count_is_positive(self) -> None:
        self.assertGreater(self.bp.estimated_sprint_count, 0)

    def test_task_count_is_positive(self) -> None:
        self.assertGreater(self.bp.estimated_task_count, 0)

    def test_team_size_is_positive(self) -> None:
        self.assertGreater(self.bp.estimated_team_size, 0)

    def test_departments_not_empty(self) -> None:
        self.assertGreater(len(self.bp.departments), 0)

    def test_recommendations_not_empty(self) -> None:
        self.assertGreater(len(self.bp.recommendations), 0)

    def test_raw_request_preserved(self) -> None:
        self.assertEqual(self.bp.raw_request, "Build a Netflix-like streaming platform")

    def test_generated_at_is_recent(self) -> None:
        before = datetime.now(timezone.utc)
        bp = _analyze("Build a simple API")
        after = datetime.now(timezone.utc)
        self.assertGreaterEqual(bp.generated_at, before)
        self.assertLessEqual(bp.generated_at, after)


# ---------------------------------------------------------------------------
# TestProjectTypeDetection
# ---------------------------------------------------------------------------

class TestProjectTypeDetection(unittest.TestCase):

    def test_detects_web_platform_from_streaming(self) -> None:
        bp = _analyze("Build a Netflix-like streaming platform")
        self.assertEqual(bp.project_type, ProjectType.WEB_PLATFORM)

    def test_detects_mobile_app_from_android(self) -> None:
        bp = _analyze("Build an Android app for food ordering")
        self.assertEqual(bp.project_type, ProjectType.MOBILE_APP)

    def test_detects_mobile_app_from_ios(self) -> None:
        bp = _analyze("Create an iOS app for personal finance tracking")
        self.assertEqual(bp.project_type, ProjectType.MOBILE_APP)

    def test_detects_saas_from_crm(self) -> None:
        bp = _analyze("Build a CRM for enterprise sales teams")
        self.assertEqual(bp.project_type, ProjectType.SAAS)

    def test_detects_saas_from_subscription(self) -> None:
        bp = _analyze("Create a subscription-based project management tool")
        self.assertEqual(bp.project_type, ProjectType.SAAS)

    def test_detects_automation_from_keyword(self) -> None:
        bp = _analyze("Build an automation system for invoice processing")
        self.assertEqual(bp.project_type, ProjectType.AUTOMATION)

    def test_detects_api_from_rest_api(self) -> None:
        bp = _analyze("Design and build a REST API for order management")
        self.assertEqual(bp.project_type, ProjectType.API)

    def test_detects_ai_tool_from_machine_learning(self) -> None:
        bp = _analyze("Build a machine learning platform for image classification")
        self.assertEqual(bp.project_type, ProjectType.AI_TOOL)

    def test_detects_ecommerce_from_keyword(self) -> None:
        bp = _analyze("Build an e-commerce marketplace for handmade products")
        self.assertEqual(bp.project_type, ProjectType.ECOMMERCE)

    def test_detects_game_from_keyword(self) -> None:
        bp = _analyze("Create a multiplayer game with leaderboards and levels")
        self.assertEqual(bp.project_type, ProjectType.GAME)

    def test_detects_desktop_app_from_keyword(self) -> None:
        bp = _analyze("Build a desktop application for video editing")
        self.assertEqual(bp.project_type, ProjectType.DESKTOP_APP)

    def test_detection_is_case_insensitive(self) -> None:
        bp1 = _analyze("Build an ANDROID app for delivery")
        bp2 = _analyze("Build an android app for delivery")
        self.assertEqual(bp1.project_type, bp2.project_type)

    def test_no_match_defaults_to_web_platform(self) -> None:
        bp = _analyze("Build something amazing and innovative")
        self.assertEqual(bp.project_type, ProjectType.WEB_PLATFORM)

    def test_microservice_detected_as_api(self) -> None:
        bp = _analyze("Build a microservice for user authentication")
        self.assertEqual(bp.project_type, ProjectType.API)


# ---------------------------------------------------------------------------
# TestRiskDetection
# ---------------------------------------------------------------------------

class TestRiskDetection(unittest.TestCase):

    def _risk_categories(self, request: str) -> set:
        bp = _analyze(request)
        return {r.category for r in bp.risks}

    def test_streaming_detects_video_streaming_risk(self) -> None:
        cats = self._risk_categories("Build a video streaming platform")
        self.assertIn(RiskCategory.VIDEO_STREAMING, cats)

    def test_netflix_detects_video_streaming_risk(self) -> None:
        cats = self._risk_categories("Build a Netflix-like streaming platform")
        self.assertIn(RiskCategory.VIDEO_STREAMING, cats)

    def test_payment_keyword_detects_payments_risk(self) -> None:
        cats = self._risk_categories("Build a subscription billing platform")
        self.assertIn(RiskCategory.PAYMENTS, cats)

    def test_stripe_detects_payments_risk(self) -> None:
        cats = self._risk_categories("Build an app with Stripe payment integration")
        self.assertIn(RiskCategory.PAYMENTS, cats)

    def test_user_keyword_detects_auth_risk(self) -> None:
        cats = self._risk_categories("Build a platform for user management and profiles")
        self.assertIn(RiskCategory.AUTHENTICATION, cats)

    def test_platform_detects_auth_risk(self) -> None:
        cats = self._risk_categories("Build a data analysis platform")
        self.assertIn(RiskCategory.AUTHENTICATION, cats)

    def test_realtime_keyword_detects_realtime_risk(self) -> None:
        cats = self._risk_categories("Build a real-time chat application")
        self.assertIn(RiskCategory.REAL_TIME, cats)

    def test_map_keyword_detects_maps_risk(self) -> None:
        cats = self._risk_categories("Build a location-based delivery tracking app")
        self.assertIn(RiskCategory.MAPS, cats)

    def test_notification_keyword_detects_notifications_risk(self) -> None:
        cats = self._risk_categories("Build an app that sends email notifications")
        self.assertIn(RiskCategory.NOTIFICATIONS, cats)

    def test_ai_keyword_detects_ai_integration_risk(self) -> None:
        cats = self._risk_categories("Build a product recommendation engine using AI")
        self.assertIn(RiskCategory.AI_INTEGRATION, cats)

    def test_no_duplicate_risk_categories(self) -> None:
        bp = _analyze("Build a Netflix-like streaming platform with payments and user auth")
        categories = [r.category for r in bp.risks]
        self.assertEqual(len(categories), len(set(categories)))

    def test_risks_sorted_critical_first(self) -> None:
        bp = _analyze("Build a video streaming platform with user authentication")
        levels = [r.level for r in bp.risks]
        if len(levels) >= 2:
            level_order = [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]
            for i in range(len(levels) - 1):
                self.assertLessEqual(
                    level_order.index(levels[i]),
                    level_order.index(levels[i + 1]),
                )

    def test_video_streaming_risk_is_critical(self) -> None:
        bp = _analyze("Build a video streaming service")
        streaming_risks = [r for r in bp.risks if r.category == RiskCategory.VIDEO_STREAMING]
        self.assertEqual(len(streaming_risks), 1)
        self.assertEqual(streaming_risks[0].level, RiskLevel.CRITICAL)

    def test_risk_description_is_non_empty(self) -> None:
        bp = _analyze("Build a platform with user authentication")
        for risk in bp.risks:
            self.assertGreater(len(risk.description), 0)

    def test_simple_api_request_has_no_critical_risks(self) -> None:
        bp = _analyze("Build a simple REST API for getting weather data")
        critical = [r for r in bp.risks if r.level == RiskLevel.CRITICAL]
        self.assertEqual(len(critical), 0)


# ---------------------------------------------------------------------------
# TestDepartmentDetection
# ---------------------------------------------------------------------------

class TestDepartmentDetection(unittest.TestCase):

    def _dept_set(self, request: str) -> set:
        return {d.department for d in _analyze(request).departments}

    def test_backend_included_for_web_platform(self) -> None:
        depts = self._dept_set("Build a Netflix-like streaming platform")
        self.assertIn(Department.BACKEND, depts)

    def test_frontend_included_for_web_platform(self) -> None:
        depts = self._dept_set("Build a Netflix-like streaming platform")
        self.assertIn(Department.FRONTEND, depts)

    def test_database_included_for_web_platform(self) -> None:
        depts = self._dept_set("Build a Netflix-like streaming platform")
        self.assertIn(Department.DATABASE, depts)

    def test_qa_included_for_web_platform(self) -> None:
        depts = self._dept_set("Build a Netflix-like streaming platform")
        self.assertIn(Department.QA, depts)

    def test_devops_included_for_web_platform(self) -> None:
        depts = self._dept_set("Build a Netflix-like streaming platform")
        self.assertIn(Department.DEVOPS, depts)

    def test_security_added_when_auth_risk_detected(self) -> None:
        depts = self._dept_set("Build a platform for user login and profiles")
        self.assertIn(Department.SECURITY, depts)

    def test_finance_added_when_payment_risk_detected(self) -> None:
        depts = self._dept_set("Build a subscription billing service with payment processing")
        self.assertIn(Department.FINANCE, depts)

    def test_marketing_added_for_consumer_platform(self) -> None:
        depts = self._dept_set("Build a Netflix-like streaming platform")
        self.assertIn(Department.MARKETING, depts)

    def test_legal_added_for_streaming_content(self) -> None:
        depts = self._dept_set("Build a streaming video platform")
        self.assertIn(Department.LEGAL, depts)

    def test_no_duplicate_departments(self) -> None:
        bp = _analyze("Build a Netflix-like streaming platform")
        dept_list = [d.department for d in bp.departments]
        self.assertEqual(len(dept_list), len(set(dept_list)))

    def test_departments_have_non_empty_rationale(self) -> None:
        bp = _analyze("Build a Netflix-like streaming platform")
        for req in bp.departments:
            self.assertGreater(len(req.rationale), 0)

    def test_departments_have_is_critical_field(self) -> None:
        bp = _analyze("Build a Netflix-like streaming platform")
        for req in bp.departments:
            self.assertIsInstance(req.is_critical, bool)

    def test_api_project_includes_backend(self) -> None:
        depts = self._dept_set("Build a REST API for user management")
        self.assertIn(Department.BACKEND, depts)

    def test_ecommerce_includes_finance_and_legal(self) -> None:
        depts = self._dept_set("Build an e-commerce marketplace")
        self.assertIn(Department.FINANCE, depts)
        self.assertIn(Department.LEGAL, depts)

    def test_mobile_app_includes_engineering(self) -> None:
        depts = self._dept_set("Build an Android app for fitness tracking")
        self.assertIn(Department.ENGINEERING, depts)


# ---------------------------------------------------------------------------
# TestComplexityEstimation
# ---------------------------------------------------------------------------

class TestComplexityEstimation(unittest.TestCase):

    def test_complexity_always_in_range_one_to_ten(self) -> None:
        requests = [
            "Build a REST API",
            "Build a Netflix-like streaming platform",
            "Build an AI-powered SaaS with real-time video streaming and payments",
            "Create a simple data automation script",
        ]
        for req in requests:
            bp = _analyze(req)
            self.assertGreaterEqual(bp.complexity_score, 1, msg=req)
            self.assertLessEqual(bp.complexity_score, 10, msg=req)

    def test_complex_project_scores_higher_than_simple(self) -> None:
        simple = _analyze("Build a simple REST API endpoint")
        complex_ = _analyze(
            "Build a Netflix-like streaming platform with real-time features, "
            "user authentication, payment processing, and AI-powered recommendations"
        )
        self.assertGreater(complex_.complexity_score, simple.complexity_score)

    def test_streaming_platform_has_high_complexity(self) -> None:
        bp = _analyze("Build a Netflix-like streaming platform")
        self.assertGreaterEqual(bp.complexity_score, 8)

    def test_simple_api_has_low_complexity(self) -> None:
        bp = _analyze("Build a simple REST API for weather data")
        self.assertLessEqual(bp.complexity_score, 4)

    def test_sprint_count_grows_with_complexity(self) -> None:
        simple = _analyze("Build a simple REST API")
        complex_ = _analyze("Build a Netflix-like streaming platform")
        self.assertGreater(
            complex_.estimated_sprint_count,
            simple.estimated_sprint_count,
        )

    def test_task_count_is_positive_for_all_projects(self) -> None:
        bp = _analyze("Build a basic API")
        self.assertGreater(bp.estimated_task_count, 0)

    def test_team_size_minimum_is_three(self) -> None:
        bp = _analyze("Build a minimal REST API")
        self.assertGreaterEqual(bp.estimated_team_size, 3)

    def test_complex_project_has_larger_team(self) -> None:
        simple = _analyze("Build a simple REST API")
        complex_ = _analyze("Build a Netflix-like streaming platform")
        self.assertGreater(complex_.estimated_team_size, simple.estimated_team_size)


# ---------------------------------------------------------------------------
# TestRecommendations
# ---------------------------------------------------------------------------

class TestRecommendations(unittest.TestCase):

    def test_recommendations_list_is_not_empty(self) -> None:
        bp = _analyze("Build a Netflix-like streaming platform")
        self.assertGreater(len(bp.recommendations), 0)

    def test_each_recommendation_is_non_empty_string(self) -> None:
        bp = _analyze("Build a Netflix-like streaming platform")
        for rec in bp.recommendations:
            self.assertIsInstance(rec, str)
            self.assertGreater(len(rec), 0)

    def test_no_duplicate_recommendations(self) -> None:
        bp = _analyze("Build a Netflix-like streaming platform")
        self.assertEqual(len(bp.recommendations), len(set(bp.recommendations)))

    def test_streaming_platform_has_video_recommendation(self) -> None:
        bp = _analyze("Build a video streaming platform")
        text = " ".join(bp.recommendations).lower()
        self.assertTrue(
            "stream" in text or "cdn" in text or "hls" in text or "adaptive" in text,
        )

    def test_payment_project_has_payment_recommendation(self) -> None:
        bp = _analyze("Build a subscription platform with billing and payments")
        text = " ".join(bp.recommendations).lower()
        self.assertTrue(
            "payment" in text or "billing" in text or "pci" in text or "subscription" in text,
        )

    def test_auth_project_has_auth_recommendation(self) -> None:
        bp = _analyze("Build a platform with user login and authentication")
        text = " ".join(bp.recommendations).lower()
        self.assertTrue(
            "auth" in text or "jwt" in text or "oauth" in text or "credential" in text,
        )

    def test_universal_recommendations_always_present(self) -> None:
        for request in [
            "Build a simple REST API",
            "Build a Netflix-like streaming platform",
            "Build a mobile app for fitness",
        ]:
            bp = _analyze(request)
            text = " ".join(bp.recommendations).lower()
            self.assertIn("ci/cd", text, msg=f"Missing CI/CD rec for: {request}")

    def test_more_risks_produce_more_recommendations(self) -> None:
        simple = _analyze("Build a simple REST API")
        complex_ = _analyze(
            "Build a Netflix-like streaming platform with user authentication, "
            "real-time notifications, payment processing, and map integration"
        )
        self.assertGreater(len(complex_.recommendations), len(simple.recommendations))


# ---------------------------------------------------------------------------
# TestTitleExtraction
# ---------------------------------------------------------------------------

class TestTitleExtraction(unittest.TestCase):

    def test_strips_build_prefix(self) -> None:
        bp = _analyze("Build a streaming platform for video content")
        self.assertNotIn("Build", bp.project_title)

    def test_strips_create_prefix(self) -> None:
        bp = _analyze("Create an e-commerce marketplace for handmade goods")
        self.assertFalse(bp.project_title.lower().startswith("create"))

    def test_strips_leading_article(self) -> None:
        bp = _analyze("Build a Netflix-like streaming platform")
        self.assertFalse(bp.project_title.lower().startswith(" a "))

    def test_title_is_title_cased(self) -> None:
        bp = _analyze("Build a streaming platform for online video")
        first_char = bp.project_title.lstrip()[0]
        self.assertTrue(first_char.isupper())

    def test_title_preserves_proper_nouns(self) -> None:
        bp = _analyze("Build a Netflix-like streaming platform")
        self.assertIn("Netflix", bp.project_title)

    def test_title_is_non_empty(self) -> None:
        bp = _analyze("Build a streaming platform")
        self.assertGreater(len(bp.project_title), 0)


# ---------------------------------------------------------------------------
# TestObjectiveAndDescription
# ---------------------------------------------------------------------------

class TestObjectiveAndDescription(unittest.TestCase):

    def test_objective_mentions_ceo_approval(self) -> None:
        bp = _analyze("Build a Netflix-like streaming platform")
        self.assertIn("CEO", bp.objective)

    def test_objective_mentions_quality(self) -> None:
        bp = _analyze("Build a Netflix-like streaming platform")
        text = bp.objective.lower()
        self.assertIn("quality", text)

    def test_description_mentions_departments(self) -> None:
        bp = _analyze("Build a Netflix-like streaming platform")
        text = bp.description.lower()
        self.assertIn("department", text)

    def test_description_mentions_project_type_context(self) -> None:
        bp = _analyze("Build a Netflix-like streaming platform")
        text = bp.description.lower()
        self.assertTrue("web" in text or "platform" in text or "browser" in text)

    def test_description_is_paragraph_length(self) -> None:
        bp = _analyze("Build a Netflix-like streaming platform")
        self.assertGreater(len(bp.description), 100)


# ---------------------------------------------------------------------------
# TestDeterminism
# ---------------------------------------------------------------------------

class TestDeterminism(unittest.TestCase):

    def test_same_request_produces_same_type(self) -> None:
        engine = _engine()
        request = "Build a Netflix-like streaming platform"
        bp1 = engine.analyze(request)
        bp2 = engine.analyze(request)
        self.assertEqual(bp1.project_type, bp2.project_type)

    def test_same_request_produces_same_complexity(self) -> None:
        engine = _engine()
        request = "Build a Netflix-like streaming platform"
        bp1 = engine.analyze(request)
        bp2 = engine.analyze(request)
        self.assertEqual(bp1.complexity_score, bp2.complexity_score)

    def test_same_request_produces_same_sprint_count(self) -> None:
        engine = _engine()
        request = "Build a Netflix-like streaming platform"
        bp1 = engine.analyze(request)
        bp2 = engine.analyze(request)
        self.assertEqual(bp1.estimated_sprint_count, bp2.estimated_sprint_count)

    def test_same_request_produces_same_risk_categories(self) -> None:
        engine = _engine()
        request = "Build a Netflix-like streaming platform"
        bp1 = engine.analyze(request)
        bp2 = engine.analyze(request)
        cats1 = {r.category for r in bp1.risks}
        cats2 = {r.category for r in bp2.risks}
        self.assertEqual(cats1, cats2)

    def test_same_request_produces_same_department_set(self) -> None:
        engine = _engine()
        request = "Build a Netflix-like streaming platform"
        bp1 = engine.analyze(request)
        bp2 = engine.analyze(request)
        depts1 = {d.department for d in bp1.departments}
        depts2 = {d.department for d in bp2.departments}
        self.assertEqual(depts1, depts2)

    def test_multiple_independent_analyses_do_not_interfere(self) -> None:
        engine = _engine()
        bp_api = engine.analyze("Build a REST API")
        bp_streaming = engine.analyze("Build a Netflix-like streaming platform")
        self.assertNotEqual(bp_api.project_type, bp_streaming.project_type)
        self.assertLess(bp_api.complexity_score, bp_streaming.complexity_score)


# ---------------------------------------------------------------------------
# TestNetflixBlueprint — full end-to-end scenario
# ---------------------------------------------------------------------------

class TestNetflixBlueprint(unittest.TestCase):

    def setUp(self) -> None:
        self.bp = _analyze("Build a Netflix-like streaming platform")

    def test_detected_as_web_platform(self) -> None:
        self.assertEqual(self.bp.project_type, ProjectType.WEB_PLATFORM)

    def test_has_video_streaming_risk(self) -> None:
        cats = {r.category for r in self.bp.risks}
        self.assertIn(RiskCategory.VIDEO_STREAMING, cats)

    def test_has_authentication_risk(self) -> None:
        cats = {r.category for r in self.bp.risks}
        self.assertIn(RiskCategory.AUTHENTICATION, cats)

    def test_has_payments_risk(self) -> None:
        cats = {r.category for r in self.bp.risks}
        self.assertIn(RiskCategory.PAYMENTS, cats)

    def test_has_scaling_risk(self) -> None:
        cats = {r.category for r in self.bp.risks}
        self.assertIn(RiskCategory.SCALING, cats)

    def test_video_streaming_risk_is_critical(self) -> None:
        streaming = next(r for r in self.bp.risks if r.category == RiskCategory.VIDEO_STREAMING)
        self.assertEqual(streaming.level, RiskLevel.CRITICAL)

    def test_complexity_is_at_maximum(self) -> None:
        self.assertEqual(self.bp.complexity_score, 10)

    def test_sprint_count_is_substantial(self) -> None:
        self.assertGreaterEqual(self.bp.estimated_sprint_count, 20)

    def test_department_count_is_large(self) -> None:
        self.assertGreaterEqual(len(self.bp.departments), 8)

    def test_has_backend_department(self) -> None:
        depts = {d.department for d in self.bp.departments}
        self.assertIn(Department.BACKEND, depts)

    def test_has_frontend_department(self) -> None:
        depts = {d.department for d in self.bp.departments}
        self.assertIn(Department.FRONTEND, depts)

    def test_has_security_department(self) -> None:
        depts = {d.department for d in self.bp.departments}
        self.assertIn(Department.SECURITY, depts)

    def test_has_finance_department(self) -> None:
        depts = {d.department for d in self.bp.departments}
        self.assertIn(Department.FINANCE, depts)

    def test_has_legal_department(self) -> None:
        depts = {d.department for d in self.bp.departments}
        self.assertIn(Department.LEGAL, depts)

    def test_has_marketing_department(self) -> None:
        depts = {d.department for d in self.bp.departments}
        self.assertIn(Department.MARKETING, depts)

    def test_recommendations_include_streaming_advice(self) -> None:
        text = " ".join(self.bp.recommendations).lower()
        self.assertTrue("stream" in text or "cdn" in text or "adaptive" in text)

    def test_title_contains_streaming_or_platform(self) -> None:
        title_lower = self.bp.project_title.lower()
        self.assertTrue("streaming" in title_lower or "platform" in title_lower)

    def test_task_count_exceeds_sprint_count(self) -> None:
        self.assertGreater(self.bp.estimated_task_count, self.bp.estimated_sprint_count)

    def test_blueprint_is_frozen(self) -> None:
        with self.assertRaises(Exception):
            self.bp.complexity_score = 1  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
