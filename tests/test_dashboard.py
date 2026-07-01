"""
Sprint 15 — CEO Control Center (Web Dashboard V1)
Tests for all dashboard routes, JSON API endpoints, and DashboardState logic.

Run:
    .venv\\Scripts\\python.exe -m unittest tests.test_dashboard -v
"""

import json
import unittest

from fastapi.testclient import TestClient

from apps.dashboard.main import app, create_app
from apps.dashboard.state import DashboardState


# ---------------------------------------------------------------------------
# Shared client fixture (one DashboardState per test module)
# ---------------------------------------------------------------------------

def _get_client() -> TestClient:
    DashboardState.reset()
    return TestClient(app)


# ===========================================================================
# TestDashboardStateInit
# ===========================================================================

class TestDashboardStateInit(unittest.TestCase):
    """DashboardState singleton creation and seed data."""

    def setUp(self):
        DashboardState.reset()
        self.state = DashboardState.get()

    def tearDown(self):
        DashboardState.reset()

    def test_singleton_returns_same_instance(self):
        s1 = DashboardState.get()
        s2 = DashboardState.get()
        self.assertIs(s1, s2)

    def test_reset_creates_fresh_instance(self):
        s1 = DashboardState.get()
        DashboardState.reset()
        s2 = DashboardState.get()
        self.assertIsNot(s1, s2)

    def test_engines_initialized(self):
        self.assertIsNotNone(self.state.memory_engine)
        self.assertIsNotNone(self.state.decision_engine)
        self.assertIsNotNone(self.state.discussion_engine)
        self.assertIsNotNone(self.state.department_registry)
        self.assertIsNotNone(self.state.workforce_registry)
        self.assertIsNotNone(self.state.executive_engine)
        self.assertIsNotNone(self.state.workflow_engine)
        self.assertIsNotNone(self.state.event_stream)

    def test_projects_seeded(self):
        projects = self.state.list_projects()
        self.assertGreater(len(projects), 0)

    def test_exactly_two_projects(self):
        self.assertEqual(len(self.state.list_projects()), 2)

    def test_employees_seeded(self):
        self.assertGreater(self.state.workforce_registry.count(), 0)

    def test_exactly_five_employees(self):
        self.assertEqual(self.state.workforce_registry.count(), 5)

    def test_departments_seeded(self):
        self.assertGreater(self.state.department_registry.count(), 0)

    def test_exactly_four_departments(self):
        self.assertEqual(self.state.department_registry.count(), 4)

    def test_discussions_seeded(self):
        self.assertGreater(self.state.discussion_engine.count(), 0)

    def test_at_least_one_open_discussion(self):
        open_discs = self.state.discussion_engine.list_open()
        self.assertGreater(len(open_discs), 0)

    def test_at_least_one_closed_discussion(self):
        closed_discs = self.state.discussion_engine.list_closed()
        self.assertGreater(len(closed_discs), 0)

    def test_decisions_seeded(self):
        stats = self.state.decision_engine.statistics()
        self.assertGreater(stats["total_decisions"], 0)

    def test_memory_entries_seeded(self):
        self.assertGreater(self.state.memory_engine.count(), 0)

    def test_events_seeded(self):
        self.assertGreater(self.state.event_stream.event_count(), 0)

    def test_workflow_seeded(self):
        wfs = self.state.workflow_engine.history()
        self.assertGreater(len(wfs), 0)

    def test_workflow_is_active(self):
        wfs = self.state.workflow_engine.history()
        statuses = [wf.status.value for wf in wfs]
        self.assertIn("ACTIVE", statuses)

    def test_list_projects_returns_list(self):
        result = self.state.list_projects()
        self.assertIsInstance(result, list)

    def test_project_titles_present(self):
        titles = [p.title for p in self.state.list_projects()]
        self.assertIn("AI Company OS Platform", titles)
        self.assertIn("CEO Dashboard V1", titles)


# ===========================================================================
# TestDashboardStateStats
# ===========================================================================

class TestDashboardStateStats(unittest.TestCase):
    """DashboardState aggregate stats methods."""

    def setUp(self):
        DashboardState.reset()
        self.state = DashboardState.get()

    def tearDown(self):
        DashboardState.reset()

    def test_get_event_stats_returns_dict(self):
        stats = self.state.get_event_stats()
        self.assertIsInstance(stats, dict)

    def test_get_event_stats_total_events(self):
        stats = self.state.get_event_stats()
        self.assertIn("total_events", stats)
        self.assertGreater(stats["total_events"], 0)

    def test_get_event_stats_total_subscribers(self):
        stats = self.state.get_event_stats()
        self.assertIn("total_subscribers", stats)

    def test_get_event_stats_events_by_channel(self):
        stats = self.state.get_event_stats()
        self.assertIn("events_by_channel", stats)
        self.assertIsInstance(stats["events_by_channel"], dict)

    def test_get_memory_stats_returns_dict(self):
        stats = self.state.get_memory_stats()
        self.assertIsInstance(stats, dict)

    def test_get_memory_stats_total_entries(self):
        stats = self.state.get_memory_stats()
        self.assertIn("total_entries", stats)
        self.assertGreater(stats["total_entries"], 0)

    def test_get_decision_stats_returns_dict(self):
        stats = self.state.get_decision_stats()
        self.assertIsInstance(stats, dict)

    def test_get_decision_stats_total(self):
        stats = self.state.get_decision_stats()
        self.assertIn("total_decisions", stats)

    def test_get_discussion_stats_returns_dict(self):
        stats = self.state.get_discussion_stats()
        self.assertIsInstance(stats, dict)

    def test_get_discussion_stats_total(self):
        stats = self.state.get_discussion_stats()
        self.assertIn("total", stats)

    def test_get_workflow_stats_returns_dict(self):
        stats = self.state.get_workflow_stats()
        self.assertIsInstance(stats, dict)

    def test_get_workflow_stats_total(self):
        stats = self.state.get_workflow_stats()
        self.assertIn("total_workflows", stats)
        self.assertGreater(stats["total_workflows"], 0)


# ===========================================================================
# TestCreateApp
# ===========================================================================

class TestCreateApp(unittest.TestCase):
    """FastAPI application factory."""

    def test_create_app_returns_app(self):
        from fastapi import FastAPI
        a = create_app()
        self.assertIsInstance(a, FastAPI)

    def test_app_has_routes(self):
        a = create_app()
        paths = [r.path for r in a.routes if hasattr(r, "path")]
        self.assertTrue(any("/" in p for p in paths))

    def test_app_title(self):
        a = create_app()
        self.assertIn("CEO", a.title)


# ===========================================================================
# TestHTMLPageStatus
# ===========================================================================

class TestHTMLPageStatus(unittest.TestCase):
    """All HTML pages return 200 OK."""

    @classmethod
    def setUpClass(cls):
        DashboardState.reset()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        DashboardState.reset()

    def test_dashboard_root_ok(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)

    def test_projects_page_ok(self):
        r = self.client.get("/projects")
        self.assertEqual(r.status_code, 200)

    def test_employees_page_ok(self):
        r = self.client.get("/employees")
        self.assertEqual(r.status_code, 200)

    def test_workflow_page_ok(self):
        r = self.client.get("/workflow")
        self.assertEqual(r.status_code, 200)

    def test_events_page_ok(self):
        r = self.client.get("/events")
        self.assertEqual(r.status_code, 200)


# ===========================================================================
# TestHTMLPageContentType
# ===========================================================================

class TestHTMLPageContentType(unittest.TestCase):
    """HTML pages return text/html content type."""

    @classmethod
    def setUpClass(cls):
        DashboardState.reset()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        DashboardState.reset()

    def test_dashboard_content_type(self):
        r = self.client.get("/")
        self.assertIn("text/html", r.headers["content-type"])

    def test_projects_content_type(self):
        r = self.client.get("/projects")
        self.assertIn("text/html", r.headers["content-type"])

    def test_employees_content_type(self):
        r = self.client.get("/employees")
        self.assertIn("text/html", r.headers["content-type"])

    def test_workflow_content_type(self):
        r = self.client.get("/workflow")
        self.assertIn("text/html", r.headers["content-type"])

    def test_events_content_type(self):
        r = self.client.get("/events")
        self.assertIn("text/html", r.headers["content-type"])


# ===========================================================================
# TestHTMLPageContents
# ===========================================================================

class TestHTMLPageContents(unittest.TestCase):
    """HTML pages contain expected structural elements."""

    @classmethod
    def setUpClass(cls):
        DashboardState.reset()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        DashboardState.reset()

    def test_dashboard_has_navbar(self):
        r = self.client.get("/")
        self.assertIn("navbar", r.text)

    def test_dashboard_has_company_name(self):
        r = self.client.get("/")
        self.assertIn("AI Company OS", r.text)

    def test_dashboard_has_htmx_link(self):
        r = self.client.get("/")
        self.assertIn("htmx", r.text)

    def test_dashboard_has_static_css(self):
        r = self.client.get("/")
        self.assertIn("style.css", r.text)

    def test_dashboard_has_projects_kpi(self):
        r = self.client.get("/")
        self.assertIn("Projects", r.text)

    def test_dashboard_has_employees_kpi(self):
        r = self.client.get("/")
        self.assertIn("Employees", r.text)

    def test_dashboard_has_departments(self):
        r = self.client.get("/")
        self.assertIn("Departments", r.text)

    def test_dashboard_has_event_timeline(self):
        r = self.client.get("/")
        self.assertIn("Event Timeline", r.text)

    def test_dashboard_has_recent_decisions(self):
        r = self.client.get("/")
        self.assertIn("Recent Decisions", r.text)

    def test_dashboard_has_recent_memory(self):
        r = self.client.get("/")
        self.assertIn("Recent Memory", r.text)

    def test_projects_page_has_project_title(self):
        r = self.client.get("/projects")
        self.assertIn("AI Company OS Platform", r.text)

    def test_projects_page_has_tasks_section(self):
        r = self.client.get("/projects")
        self.assertIn("Tasks", r.text)

    def test_projects_page_shows_progress(self):
        r = self.client.get("/projects")
        self.assertIn("Progress", r.text)

    def test_employees_page_has_table(self):
        r = self.client.get("/employees")
        self.assertIn("data-table", r.text)

    def test_employees_page_has_alice(self):
        r = self.client.get("/employees")
        self.assertIn("Alice Chen", r.text)

    def test_employees_page_has_department_section(self):
        r = self.client.get("/employees")
        self.assertIn("Departments", r.text)

    def test_workflow_page_has_stages(self):
        r = self.client.get("/workflow")
        self.assertIn("stage", r.text.lower())

    def test_workflow_page_has_progress(self):
        r = self.client.get("/workflow")
        self.assertIn("Progress", r.text)

    def test_events_page_has_channel_stats(self):
        r = self.client.get("/events")
        self.assertIn("Channel Statistics", r.text)

    def test_events_page_has_timeline(self):
        r = self.client.get("/events")
        self.assertIn("Event Timeline", r.text)

    def test_events_page_has_htmx_polling(self):
        r = self.client.get("/events")
        self.assertIn("hx-get", r.text)

    def test_nav_links_present(self):
        r = self.client.get("/")
        self.assertIn('href="/projects"', r.text)
        self.assertIn('href="/employees"', r.text)
        self.assertIn('href="/workflow"', r.text)
        self.assertIn('href="/events"', r.text)


# ===========================================================================
# TestAPIStatsEndpoint
# ===========================================================================

class TestAPIStatsEndpoint(unittest.TestCase):
    """GET /api/stats"""

    @classmethod
    def setUpClass(cls):
        DashboardState.reset()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        DashboardState.reset()

    def test_status_200(self):
        r = self.client.get("/api/stats")
        self.assertEqual(r.status_code, 200)

    def test_returns_json(self):
        r = self.client.get("/api/stats")
        self.assertIn("application/json", r.headers["content-type"])

    def test_total_projects_key(self):
        data = self.client.get("/api/stats").json()
        self.assertIn("total_projects", data)

    def test_total_projects_value(self):
        data = self.client.get("/api/stats").json()
        self.assertEqual(data["total_projects"], 2)

    def test_active_projects_key(self):
        data = self.client.get("/api/stats").json()
        self.assertIn("active_projects", data)

    def test_active_projects_nonzero(self):
        data = self.client.get("/api/stats").json()
        self.assertGreater(data["active_projects"], 0)

    def test_total_employees_key(self):
        data = self.client.get("/api/stats").json()
        self.assertIn("total_employees", data)

    def test_total_employees_value(self):
        data = self.client.get("/api/stats").json()
        self.assertEqual(data["total_employees"], 5)

    def test_active_employees_key(self):
        data = self.client.get("/api/stats").json()
        self.assertIn("active_employees", data)

    def test_total_departments_key(self):
        data = self.client.get("/api/stats").json()
        self.assertIn("total_departments", data)

    def test_total_departments_value(self):
        data = self.client.get("/api/stats").json()
        self.assertEqual(data["total_departments"], 4)

    def test_total_events_key(self):
        data = self.client.get("/api/stats").json()
        self.assertIn("total_events", data)

    def test_total_events_nonzero(self):
        data = self.client.get("/api/stats").json()
        self.assertGreater(data["total_events"], 0)

    def test_total_memory_entries_key(self):
        data = self.client.get("/api/stats").json()
        self.assertIn("total_memory_entries", data)

    def test_total_decisions_key(self):
        data = self.client.get("/api/stats").json()
        self.assertIn("total_decisions", data)

    def test_total_discussions_key(self):
        data = self.client.get("/api/stats").json()
        self.assertIn("total_discussions", data)

    def test_workflow_stats_key(self):
        data = self.client.get("/api/stats").json()
        self.assertIn("workflow_stats", data)

    def test_workflow_stats_is_dict(self):
        data = self.client.get("/api/stats").json()
        self.assertIsInstance(data["workflow_stats"], dict)

    def test_all_values_non_negative(self):
        data = self.client.get("/api/stats").json()
        for key in ("total_projects", "total_employees", "total_departments", "total_events"):
            self.assertGreaterEqual(data[key], 0, msg=f"{key} is negative")


# ===========================================================================
# TestAPIEventsRecentEndpoint
# ===========================================================================

class TestAPIEventsRecentEndpoint(unittest.TestCase):
    """GET /api/events/recent"""

    @classmethod
    def setUpClass(cls):
        DashboardState.reset()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        DashboardState.reset()

    def test_status_200(self):
        r = self.client.get("/api/events/recent")
        self.assertEqual(r.status_code, 200)

    def test_returns_list(self):
        data = self.client.get("/api/events/recent").json()
        self.assertIsInstance(data, list)

    def test_default_limit_respected(self):
        data = self.client.get("/api/events/recent").json()
        self.assertLessEqual(len(data), 20)

    def test_custom_limit(self):
        data = self.client.get("/api/events/recent?limit=5").json()
        self.assertLessEqual(len(data), 5)

    def test_custom_limit_zero_returns_nothing(self):
        data = self.client.get("/api/events/recent?limit=0").json()
        self.assertIsInstance(data, list)

    def test_event_has_id_field(self):
        data = self.client.get("/api/events/recent").json()
        if data:
            self.assertIn("id", data[0])

    def test_event_has_source_field(self):
        data = self.client.get("/api/events/recent").json()
        if data:
            self.assertIn("source", data[0])

    def test_event_has_channel_field(self):
        data = self.client.get("/api/events/recent").json()
        if data:
            self.assertIn("channel", data[0])

    def test_event_has_timestamp_field(self):
        data = self.client.get("/api/events/recent").json()
        if data:
            self.assertIn("timestamp", data[0])

    def test_event_has_payload_field(self):
        data = self.client.get("/api/events/recent").json()
        if data:
            self.assertIn("payload", data[0])

    def test_event_has_action_field(self):
        data = self.client.get("/api/events/recent").json()
        if data:
            self.assertIn("action", data[0])

    def test_events_not_empty(self):
        data = self.client.get("/api/events/recent").json()
        self.assertGreater(len(data), 0)

    def test_channel_values_are_strings(self):
        data = self.client.get("/api/events/recent").json()
        for ev in data:
            self.assertIsInstance(ev["channel"], str)

    def test_source_values_are_strings(self):
        data = self.client.get("/api/events/recent").json()
        for ev in data:
            self.assertIsInstance(ev["source"], str)

    def test_limit_1_returns_one_item(self):
        data = self.client.get("/api/events/recent?limit=1").json()
        self.assertEqual(len(data), 1)

    def test_limit_100_returns_all(self):
        data = self.client.get("/api/events/recent?limit=100").json()
        self.assertGreater(len(data), 0)


# ===========================================================================
# TestAPIProjectsEndpoint
# ===========================================================================

class TestAPIProjectsEndpoint(unittest.TestCase):
    """GET /api/projects"""

    @classmethod
    def setUpClass(cls):
        DashboardState.reset()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        DashboardState.reset()

    def test_status_200(self):
        r = self.client.get("/api/projects")
        self.assertEqual(r.status_code, 200)

    def test_returns_list(self):
        data = self.client.get("/api/projects").json()
        self.assertIsInstance(data, list)

    def test_exactly_two_projects(self):
        data = self.client.get("/api/projects").json()
        self.assertEqual(len(data), 2)

    def test_project_has_id(self):
        data = self.client.get("/api/projects").json()
        self.assertIn("id", data[0])

    def test_project_has_title(self):
        data = self.client.get("/api/projects").json()
        self.assertIn("title", data[0])

    def test_project_has_status(self):
        data = self.client.get("/api/projects").json()
        self.assertIn("status", data[0])

    def test_project_has_priority(self):
        data = self.client.get("/api/projects").json()
        self.assertIn("priority", data[0])

    def test_project_has_total_tasks(self):
        data = self.client.get("/api/projects").json()
        self.assertIn("total_tasks", data[0])

    def test_project_has_completion_percentage(self):
        data = self.client.get("/api/projects").json()
        self.assertIn("completion_percentage", data[0])

    def test_project_has_created_at(self):
        data = self.client.get("/api/projects").json()
        self.assertIn("created_at", data[0])

    def test_project_titles_contain_platform(self):
        data = self.client.get("/api/projects").json()
        titles = [p["title"] for p in data]
        self.assertIn("AI Company OS Platform", titles)

    def test_project_status_is_string(self):
        data = self.client.get("/api/projects").json()
        self.assertIsInstance(data[0]["status"], str)

    def test_completion_percentage_in_range(self):
        data = self.client.get("/api/projects").json()
        for p in data:
            self.assertGreaterEqual(p["completion_percentage"], 0.0)
            self.assertLessEqual(p["completion_percentage"], 100.0)


# ===========================================================================
# TestAPIEmployeesEndpoint
# ===========================================================================

class TestAPIEmployeesEndpoint(unittest.TestCase):
    """GET /api/employees"""

    @classmethod
    def setUpClass(cls):
        DashboardState.reset()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        DashboardState.reset()

    def test_status_200(self):
        r = self.client.get("/api/employees")
        self.assertEqual(r.status_code, 200)

    def test_returns_list(self):
        data = self.client.get("/api/employees").json()
        self.assertIsInstance(data, list)

    def test_exactly_five_employees(self):
        data = self.client.get("/api/employees").json()
        self.assertEqual(len(data), 5)

    def test_employee_has_id(self):
        data = self.client.get("/api/employees").json()
        self.assertIn("id", data[0])

    def test_employee_has_name(self):
        data = self.client.get("/api/employees").json()
        self.assertIn("name", data[0])

    def test_employee_has_role(self):
        data = self.client.get("/api/employees").json()
        self.assertIn("role", data[0])

    def test_employee_has_department(self):
        data = self.client.get("/api/employees").json()
        self.assertIn("department", data[0])

    def test_employee_has_seniority(self):
        data = self.client.get("/api/employees").json()
        self.assertIn("seniority", data[0])

    def test_employee_has_status(self):
        data = self.client.get("/api/employees").json()
        self.assertIn("status", data[0])

    def test_employee_has_skills(self):
        data = self.client.get("/api/employees").json()
        self.assertIn("skills", data[0])

    def test_skills_is_list(self):
        data = self.client.get("/api/employees").json()
        self.assertIsInstance(data[0]["skills"], list)

    def test_alice_chen_present(self):
        data = self.client.get("/api/employees").json()
        names = [e["name"] for e in data]
        self.assertIn("Alice Chen", names)

    def test_carol_diaz_present(self):
        data = self.client.get("/api/employees").json()
        names = [e["name"] for e in data]
        self.assertIn("Carol Diaz", names)

    def test_employee_status_is_string(self):
        data = self.client.get("/api/employees").json()
        for emp in data:
            self.assertIsInstance(emp["status"], str)

    def test_departments_covered(self):
        data = self.client.get("/api/employees").json()
        depts = {e["department"] for e in data}
        self.assertGreater(len(depts), 1)


# ===========================================================================
# TestAPIWorkflowEndpoint
# ===========================================================================

class TestAPIWorkflowEndpoint(unittest.TestCase):
    """GET /api/workflow"""

    @classmethod
    def setUpClass(cls):
        DashboardState.reset()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        DashboardState.reset()

    def test_status_200(self):
        r = self.client.get("/api/workflow")
        self.assertEqual(r.status_code, 200)

    def test_returns_dict(self):
        data = self.client.get("/api/workflow").json()
        self.assertIsInstance(data, dict)

    def test_has_workflows_key(self):
        data = self.client.get("/api/workflow").json()
        self.assertIn("workflows", data)

    def test_has_stats_key(self):
        data = self.client.get("/api/workflow").json()
        self.assertIn("stats", data)

    def test_workflows_is_list(self):
        data = self.client.get("/api/workflow").json()
        self.assertIsInstance(data["workflows"], list)

    def test_at_least_one_workflow(self):
        data = self.client.get("/api/workflow").json()
        self.assertGreater(len(data["workflows"]), 0)

    def test_workflow_has_id(self):
        data = self.client.get("/api/workflow").json()
        wf = data["workflows"][0]
        self.assertIn("id", wf)

    def test_workflow_has_name(self):
        data = self.client.get("/api/workflow").json()
        wf = data["workflows"][0]
        self.assertIn("name", wf)

    def test_workflow_has_status(self):
        data = self.client.get("/api/workflow").json()
        wf = data["workflows"][0]
        self.assertIn("status", wf)

    def test_workflow_has_progress(self):
        data = self.client.get("/api/workflow").json()
        wf = data["workflows"][0]
        self.assertIn("progress", wf)

    def test_workflow_progress_in_range(self):
        data = self.client.get("/api/workflow").json()
        for wf in data["workflows"]:
            self.assertGreaterEqual(wf["progress"], 0.0)
            self.assertLessEqual(wf["progress"], 100.0)

    def test_workflow_has_total_stages(self):
        data = self.client.get("/api/workflow").json()
        wf = data["workflows"][0]
        self.assertIn("total_stages", wf)

    def test_stats_has_total_workflows(self):
        data = self.client.get("/api/workflow").json()
        self.assertIn("total_workflows", data["stats"])

    def test_total_stages_positive(self):
        data = self.client.get("/api/workflow").json()
        for wf in data["workflows"]:
            self.assertGreater(wf["total_stages"], 0)


# ===========================================================================
# TestAPIMemoryEndpoint
# ===========================================================================

class TestAPIMemoryEndpoint(unittest.TestCase):
    """GET /api/memory"""

    @classmethod
    def setUpClass(cls):
        DashboardState.reset()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        DashboardState.reset()

    def test_status_200(self):
        r = self.client.get("/api/memory")
        self.assertEqual(r.status_code, 200)

    def test_returns_list(self):
        data = self.client.get("/api/memory").json()
        self.assertIsInstance(data, list)

    def test_entries_not_empty(self):
        data = self.client.get("/api/memory").json()
        self.assertGreater(len(data), 0)

    def test_entry_has_id(self):
        data = self.client.get("/api/memory").json()
        self.assertIn("id", data[0])

    def test_entry_has_title(self):
        data = self.client.get("/api/memory").json()
        self.assertIn("title", data[0])

    def test_entry_has_category(self):
        data = self.client.get("/api/memory").json()
        self.assertIn("category", data[0])

    def test_entry_has_author(self):
        data = self.client.get("/api/memory").json()
        self.assertIn("author", data[0])

    def test_entry_has_tags(self):
        data = self.client.get("/api/memory").json()
        self.assertIn("tags", data[0])

    def test_tags_is_list(self):
        data = self.client.get("/api/memory").json()
        self.assertIsInstance(data[0]["tags"], list)

    def test_entry_has_created_at(self):
        data = self.client.get("/api/memory").json()
        self.assertIn("created_at", data[0])

    def test_default_limit_20(self):
        data = self.client.get("/api/memory").json()
        self.assertLessEqual(len(data), 20)

    def test_custom_limit(self):
        data = self.client.get("/api/memory?limit=2").json()
        self.assertLessEqual(len(data), 2)

    def test_category_is_string(self):
        data = self.client.get("/api/memory").json()
        for entry in data:
            self.assertIsInstance(entry["category"], str)


# ===========================================================================
# TestAPIDecisionsEndpoint
# ===========================================================================

class TestAPIDecisionsEndpoint(unittest.TestCase):
    """GET /api/decisions"""

    @classmethod
    def setUpClass(cls):
        DashboardState.reset()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        DashboardState.reset()

    def test_status_200(self):
        r = self.client.get("/api/decisions")
        self.assertEqual(r.status_code, 200)

    def test_returns_list(self):
        data = self.client.get("/api/decisions").json()
        self.assertIsInstance(data, list)

    def test_at_least_one_decision(self):
        data = self.client.get("/api/decisions").json()
        self.assertGreater(len(data), 0)

    def test_decision_has_id(self):
        data = self.client.get("/api/decisions").json()
        self.assertIn("id", data[0])

    def test_decision_has_title(self):
        data = self.client.get("/api/decisions").json()
        self.assertIn("title", data[0])

    def test_decision_has_status(self):
        data = self.client.get("/api/decisions").json()
        self.assertIn("status", data[0])

    def test_decision_has_recommendation(self):
        data = self.client.get("/api/decisions").json()
        self.assertIn("recommendation", data[0])

    def test_decision_has_confidence(self):
        data = self.client.get("/api/decisions").json()
        self.assertIn("confidence", data[0])

    def test_decision_has_risk_level(self):
        data = self.client.get("/api/decisions").json()
        self.assertIn("risk_level", data[0])

    def test_decision_has_requires_ceo_approval(self):
        data = self.client.get("/api/decisions").json()
        self.assertIn("requires_ceo_approval", data[0])

    def test_decision_has_option_count(self):
        data = self.client.get("/api/decisions").json()
        self.assertIn("option_count", data[0])

    def test_decision_has_created_at(self):
        data = self.client.get("/api/decisions").json()
        self.assertIn("created_at", data[0])

    def test_confidence_in_range(self):
        data = self.client.get("/api/decisions").json()
        for d in data:
            self.assertGreaterEqual(d["confidence"], 0.0)
            self.assertLessEqual(d["confidence"], 1.0)

    def test_option_count_positive(self):
        data = self.client.get("/api/decisions").json()
        for d in data:
            self.assertGreater(d["option_count"], 0)

    def test_status_is_string(self):
        data = self.client.get("/api/decisions").json()
        for d in data:
            self.assertIsInstance(d["status"], str)

    def test_recommendation_is_postgresql(self):
        data = self.client.get("/api/decisions").json()
        recs = [d["recommendation"] for d in data if d["recommendation"]]
        self.assertIn("PostgreSQL", recs)


# ===========================================================================
# TestAPIDiscussionsEndpoint
# ===========================================================================

class TestAPIDiscussionsEndpoint(unittest.TestCase):
    """GET /api/discussions"""

    @classmethod
    def setUpClass(cls):
        DashboardState.reset()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        DashboardState.reset()

    def test_status_200(self):
        r = self.client.get("/api/discussions")
        self.assertEqual(r.status_code, 200)

    def test_returns_list(self):
        data = self.client.get("/api/discussions").json()
        self.assertIsInstance(data, list)

    def test_at_least_two_discussions(self):
        data = self.client.get("/api/discussions").json()
        self.assertGreaterEqual(len(data), 2)

    def test_discussion_has_id(self):
        data = self.client.get("/api/discussions").json()
        self.assertIn("id", data[0])

    def test_discussion_has_topic(self):
        data = self.client.get("/api/discussions").json()
        self.assertIn("topic", data[0])

    def test_discussion_has_status(self):
        data = self.client.get("/api/discussions").json()
        self.assertIn("status", data[0])

    def test_discussion_has_participant_count(self):
        data = self.client.get("/api/discussions").json()
        self.assertIn("participant_count", data[0])

    def test_discussion_has_message_count(self):
        data = self.client.get("/api/discussions").json()
        self.assertIn("message_count", data[0])

    def test_discussion_has_has_outcome(self):
        data = self.client.get("/api/discussions").json()
        self.assertIn("has_outcome", data[0])

    def test_discussion_has_created_at(self):
        data = self.client.get("/api/discussions").json()
        self.assertIn("created_at", data[0])

    def test_both_open_and_closed_present(self):
        data = self.client.get("/api/discussions").json()
        statuses = {d["status"] for d in data}
        self.assertIn("OPEN", statuses)
        self.assertIn("CLOSED", statuses)

    def test_participant_count_non_negative(self):
        data = self.client.get("/api/discussions").json()
        for d in data:
            self.assertGreaterEqual(d["participant_count"], 0)

    def test_message_count_non_negative(self):
        data = self.client.get("/api/discussions").json()
        for d in data:
            self.assertGreaterEqual(d["message_count"], 0)


# ===========================================================================
# TestStaticAssets
# ===========================================================================

class TestStaticAssets(unittest.TestCase):
    """Static assets are served correctly."""

    @classmethod
    def setUpClass(cls):
        DashboardState.reset()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        DashboardState.reset()

    def test_css_file_served(self):
        r = self.client.get("/static/style.css")
        self.assertEqual(r.status_code, 200)

    def test_css_content_type(self):
        r = self.client.get("/static/style.css")
        self.assertIn("css", r.headers["content-type"])

    def test_js_file_served(self):
        r = self.client.get("/static/app.js")
        self.assertEqual(r.status_code, 200)

    def test_js_content_type(self):
        r = self.client.get("/static/app.js")
        ct = r.headers["content-type"]
        self.assertTrue("javascript" in ct or "text" in ct)

    def test_css_not_empty(self):
        r = self.client.get("/static/style.css")
        self.assertGreater(len(r.text), 100)

    def test_js_not_empty(self):
        r = self.client.get("/static/app.js")
        self.assertGreater(len(r.text), 10)

    def test_missing_static_404(self):
        r = self.client.get("/static/nonexistent.css")
        self.assertEqual(r.status_code, 404)


# ===========================================================================
# TestHTMXPolling
# ===========================================================================

class TestHTMXPolling(unittest.TestCase):
    """HTMX polling attributes present on relevant pages."""

    @classmethod
    def setUpClass(cls):
        DashboardState.reset()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        DashboardState.reset()

    def test_dashboard_has_hx_get(self):
        r = self.client.get("/")
        self.assertIn("hx-get", r.text)

    def test_dashboard_polling_target(self):
        r = self.client.get("/")
        self.assertIn("/api/events/recent", r.text)

    def test_events_page_has_hx_get(self):
        r = self.client.get("/events")
        self.assertIn("hx-get", r.text)

    def test_events_page_polling_target(self):
        r = self.client.get("/events")
        self.assertIn("/api/events/recent", r.text)

    def test_events_page_has_hx_trigger(self):
        r = self.client.get("/events")
        self.assertIn("hx-trigger", r.text)

    def test_events_page_has_every_trigger(self):
        r = self.client.get("/events")
        self.assertIn("every 5s", r.text)

    def test_dashboard_has_hx_swap(self):
        r = self.client.get("/")
        self.assertIn("hx-swap", r.text)


# ===========================================================================
# TestAPIEventsLimitEdgeCases
# ===========================================================================

class TestAPIEventsLimitEdgeCases(unittest.TestCase):
    """Edge cases for the events/recent limit parameter."""

    @classmethod
    def setUpClass(cls):
        DashboardState.reset()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        DashboardState.reset()

    def test_limit_1(self):
        data = self.client.get("/api/events/recent?limit=1").json()
        self.assertEqual(len(data), 1)

    def test_limit_3(self):
        data = self.client.get("/api/events/recent?limit=3").json()
        self.assertLessEqual(len(data), 3)

    def test_limit_50(self):
        data = self.client.get("/api/events/recent?limit=50").json()
        self.assertGreater(len(data), 0)

    def test_events_ordered_newest_first(self):
        data = self.client.get("/api/events/recent?limit=10").json()
        if len(data) >= 2:
            ts0 = data[0]["timestamp"]
            ts1 = data[1]["timestamp"]
            self.assertGreaterEqual(ts0, ts1)

    def test_all_events_have_valid_channel(self):
        valid_channels = {"SYSTEM", "PROJECT", "WORKFLOW", "DISCUSSION",
                          "MEMORY", "DECISION", "RUNTIME", "CEO"}
        data = self.client.get("/api/events/recent?limit=50").json()
        for ev in data:
            self.assertIn(ev["channel"], valid_channels)


# ===========================================================================
# TestDashboardSeedDataIntegrity
# ===========================================================================

class TestDashboardSeedDataIntegrity(unittest.TestCase):
    """Verify that seeded data is consistent across engines."""

    @classmethod
    def setUpClass(cls):
        DashboardState.reset()
        cls.state = DashboardState.get()

    @classmethod
    def tearDownClass(cls):
        DashboardState.reset()

    def test_project1_has_tasks(self):
        projects = self.state.list_projects()
        p1 = next(p for p in projects if p.title == "AI Company OS Platform")
        tasks = self.state.executive_engine.list_tasks(p1.id)
        self.assertGreater(len(tasks), 0)

    def test_project2_has_tasks(self):
        projects = self.state.list_projects()
        p2 = next(p for p in projects if p.title == "CEO Dashboard V1")
        tasks = self.state.executive_engine.list_tasks(p2.id)
        self.assertGreater(len(tasks), 0)

    def test_decisions_have_recommendations(self):
        decisions = self.state.decision_engine.history()
        for dec in decisions:
            if dec.status.value == "RECOMMENDED":
                self.assertIsNotNone(dec.recommendation)

    def test_closed_discussions_have_outcomes(self):
        closed = self.state.discussion_engine.list_closed()
        for disc in closed:
            self.assertTrue(disc.has_outcome())

    def test_workflow_has_stages(self):
        wfs = self.state.workflow_engine.history()
        for wf in wfs:
            self.assertGreater(len(wf.stages), 0)

    def test_employees_have_skills(self):
        employees = self.state.workforce_registry.list_all()
        for emp in employees:
            self.assertGreater(len(emp.skills), 0)

    def test_departments_have_directors(self):
        depts = self.state.department_registry.list_all()
        for dept in depts:
            self.assertIsNotNone(dept.director)

    def test_memory_entries_have_content(self):
        entries = self.state.memory_engine.list_all()
        for entry in entries:
            self.assertGreater(len(entry.content), 0)

    def test_event_stream_has_system_events(self):
        from core.stream_channel import StreamChannel
        events = self.state.event_stream.history(channel=StreamChannel.SYSTEM)
        self.assertGreater(len(events), 0)

    def test_event_stream_has_project_events(self):
        from core.stream_channel import StreamChannel
        events = self.state.event_stream.history(channel=StreamChannel.PROJECT)
        self.assertGreater(len(events), 0)

    def test_event_stream_has_workflow_events(self):
        from core.stream_channel import StreamChannel
        events = self.state.event_stream.history(channel=StreamChannel.WORKFLOW)
        self.assertGreater(len(events), 0)

    def test_event_stream_has_decision_events(self):
        from core.stream_channel import StreamChannel
        events = self.state.event_stream.history(channel=StreamChannel.DECISION)
        self.assertGreater(len(events), 0)

    def test_active_employees_count_matches(self):
        employees = self.state.workforce_registry.list_all()
        active = [e for e in employees if e.status.value == "ACTIVE"]
        api_data = self.state.get_event_stats()
        self.assertGreaterEqual(len(active), 0)


# ===========================================================================
# TestAPINotFound
# ===========================================================================

class TestAPINotFound(unittest.TestCase):
    """404 for unknown routes."""

    @classmethod
    def setUpClass(cls):
        DashboardState.reset()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        DashboardState.reset()

    def test_unknown_html_route_404(self):
        r = self.client.get("/nonexistent-page")
        self.assertEqual(r.status_code, 404)

    def test_unknown_api_route_404(self):
        r = self.client.get("/api/nonexistent")
        self.assertEqual(r.status_code, 404)

    def test_wrong_method_405(self):
        r = self.client.post("/")
        self.assertEqual(r.status_code, 405)

    def test_api_stats_post_405(self):
        r = self.client.post("/api/stats")
        self.assertEqual(r.status_code, 405)


# ===========================================================================
# TestAPIResponseStructureConsistency
# ===========================================================================

class TestAPIResponseStructureConsistency(unittest.TestCase):
    """All JSON API responses are consistent across multiple calls."""

    @classmethod
    def setUpClass(cls):
        DashboardState.reset()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        DashboardState.reset()

    def test_stats_stable_across_calls(self):
        d1 = self.client.get("/api/stats").json()
        d2 = self.client.get("/api/stats").json()
        self.assertEqual(d1["total_projects"], d2["total_projects"])
        self.assertEqual(d1["total_employees"], d2["total_employees"])

    def test_projects_stable(self):
        d1 = self.client.get("/api/projects").json()
        d2 = self.client.get("/api/projects").json()
        self.assertEqual(len(d1), len(d2))

    def test_employees_stable(self):
        d1 = self.client.get("/api/employees").json()
        d2 = self.client.get("/api/employees").json()
        self.assertEqual(len(d1), len(d2))

    def test_decisions_stable(self):
        d1 = self.client.get("/api/decisions").json()
        d2 = self.client.get("/api/decisions").json()
        self.assertEqual(len(d1), len(d2))

    def test_discussions_stable(self):
        d1 = self.client.get("/api/discussions").json()
        d2 = self.client.get("/api/discussions").json()
        self.assertEqual(len(d1), len(d2))

    def test_workflow_stable(self):
        d1 = self.client.get("/api/workflow").json()
        d2 = self.client.get("/api/workflow").json()
        self.assertEqual(len(d1["workflows"]), len(d2["workflows"]))


# ===========================================================================
# TestWorkflowPageContent
# ===========================================================================

class TestWorkflowPageContent(unittest.TestCase):
    """Workflow page renders workflow data correctly."""

    @classmethod
    def setUpClass(cls):
        DashboardState.reset()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        DashboardState.reset()

    def test_workflow_page_has_kpi_row(self):
        r = self.client.get("/workflow")
        self.assertIn("kpi-row", r.text)

    def test_workflow_page_has_total_workflows(self):
        r = self.client.get("/workflow")
        self.assertIn("Total Workflows", r.text)

    def test_workflow_page_has_status_labels(self):
        r = self.client.get("/workflow")
        self.assertIn("Active", r.text)

    def test_workflow_page_shows_workflow_name(self):
        r = self.client.get("/workflow")
        self.assertIn("AI Company OS Platform Build", r.text)

    def test_workflow_page_has_stage_timeline(self):
        r = self.client.get("/workflow")
        self.assertIn("stage-timeline", r.text)

    def test_workflow_page_has_progress_bar(self):
        r = self.client.get("/workflow")
        self.assertIn("progress-bar", r.text)

    def test_workflow_page_footer_present(self):
        r = self.client.get("/workflow")
        self.assertIn("footer", r.text)


# ===========================================================================
# TestEventsPageContent
# ===========================================================================

class TestEventsPageContent(unittest.TestCase):
    """Events page renders event data correctly."""

    @classmethod
    def setUpClass(cls):
        DashboardState.reset()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        DashboardState.reset()

    def test_events_page_has_total_events(self):
        r = self.client.get("/events")
        self.assertIn("Total Events", r.text)

    def test_events_page_has_subscriber_info(self):
        r = self.client.get("/events")
        self.assertIn("Subscribers", r.text)

    def test_events_page_has_event_channels(self):
        r = self.client.get("/events")
        self.assertIn("event-channel", r.text)

    def test_events_page_has_hx_swap(self):
        r = self.client.get("/events")
        self.assertIn("hx-swap", r.text)

    def test_events_page_has_live_feed(self):
        r = self.client.get("/events")
        self.assertIn("live-event-feed", r.text)

    def test_events_page_has_event_timeline_section(self):
        r = self.client.get("/events")
        self.assertIn("Event Timeline", r.text)


# ===========================================================================
# TestAPIWorkflowStats
# ===========================================================================

class TestAPIWorkflowStats(unittest.TestCase):
    """Workflow stats returned by /api/workflow are meaningful."""

    @classmethod
    def setUpClass(cls):
        DashboardState.reset()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        DashboardState.reset()

    def test_stats_has_by_status(self):
        data = self.client.get("/api/workflow").json()
        self.assertIn("by_status", data["stats"])

    def test_stats_has_average_progress(self):
        data = self.client.get("/api/workflow").json()
        self.assertIn("average_progress", data["stats"])

    def test_average_progress_in_range(self):
        data = self.client.get("/api/workflow").json()
        avg = data["stats"]["average_progress"]
        self.assertGreaterEqual(avg, 0.0)
        self.assertLessEqual(avg, 1.0)

    def test_workflow_completed_count_non_negative(self):
        data = self.client.get("/api/workflow").json()
        for wf in data["workflows"]:
            self.assertGreaterEqual(wf["completed_stages"], 0)

    def test_workflow_name_is_string(self):
        data = self.client.get("/api/workflow").json()
        for wf in data["workflows"]:
            self.assertIsInstance(wf["name"], str)
            self.assertGreater(len(wf["name"]), 0)


# ===========================================================================
# TestAPIMemoryEdgeCases
# ===========================================================================

class TestAPIMemoryEdgeCases(unittest.TestCase):
    """Edge cases for the memory API endpoint."""

    @classmethod
    def setUpClass(cls):
        DashboardState.reset()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        DashboardState.reset()

    def test_limit_1(self):
        data = self.client.get("/api/memory?limit=1").json()
        self.assertEqual(len(data), 1)

    def test_all_entries_have_scope(self):
        data = self.client.get("/api/memory").json()
        for entry in data:
            self.assertIn("scope", entry)
            self.assertIsInstance(entry["scope"], str)

    def test_architecture_decision_present(self):
        data = self.client.get("/api/memory").json()
        titles = [e["title"] for e in data]
        self.assertTrue(any("Architecture" in t for t in titles))

    def test_sprint_entry_present(self):
        data = self.client.get("/api/memory").json()
        titles = [e["title"] for e in data]
        self.assertTrue(any("Sprint" in t for t in titles))


# ===========================================================================
# TestDashboardCompanyInfo
# ===========================================================================

class TestDashboardCompanyInfo(unittest.TestCase):
    """Dashboard pages display correct company information."""

    @classmethod
    def setUpClass(cls):
        DashboardState.reset()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        DashboardState.reset()

    def test_company_name_on_dashboard(self):
        r = self.client.get("/")
        self.assertIn("AI Company OS", r.text)

    def test_company_name_on_projects(self):
        r = self.client.get("/projects")
        self.assertIn("AI Company OS", r.text)

    def test_company_name_on_employees(self):
        r = self.client.get("/employees")
        self.assertIn("AI Company OS", r.text)

    def test_company_name_on_workflow(self):
        r = self.client.get("/workflow")
        self.assertIn("AI Company OS", r.text)

    def test_company_name_on_events(self):
        r = self.client.get("/events")
        self.assertIn("AI Company OS", r.text)

    def test_dashboard_nav_active_class(self):
        r = self.client.get("/")
        self.assertIn("active", r.text)

    def test_footer_on_dashboard(self):
        r = self.client.get("/")
        self.assertIn("Sprint 15", r.text)


if __name__ == "__main__":
    unittest.main()
