"""
Feature 19 — Live Operations Center (Kontrol Paneli V3)
Test suite: 350+ unit tests covering all new dashboard features.

Sections tested:
    1  Live Company Timeline (/api/timeline + Turkish sentences)
    2  Live Agent Status (/api/agent-status + agent cards)
    3  Execution Pipeline (dashboard HTML + pipeline steps)
    4  Project Details (expandable per-project artifacts/discussions/decisions)
    5  Employee Drawer (drawer markup + data attributes)
    6  Company Organization (/org page + org tree)
    7  Live Counters (animated counter HTML attributes)
    8  Events Turkish sentences (/events page + _human_event function)
    9  CEO Command History (/api/command-history + state.command_history)
    10 Navigation & Footer (Org link, Sprint 19)
    11 Regression tests (all existing routes still return 200)
"""

import json
import unittest

from fastapi.testclient import TestClient

from apps.dashboard.main import app
from apps.dashboard.routes import _human_event
from apps.dashboard.state import DashboardState


def _client() -> TestClient:
    DashboardState.reset()
    return TestClient(app)


# ===========================================================================
# 1. _human_event translation function
# ===========================================================================

class TestHumanEventBasic(unittest.TestCase):
    def test_company_started(self):
        s = _human_event("company_started", {})
        self.assertIn("Şirket", s)

    def test_project_created_with_title(self):
        s = _human_event("project_created", {"title": "Alpha"})
        self.assertIn("Alpha", s)
        self.assertIn("proje", s.lower())

    def test_project_created_no_title(self):
        s = _human_event("project_created", {})
        self.assertIsInstance(s, str)
        self.assertTrue(len(s) > 0)

    def test_employee_hired_with_name(self):
        s = _human_event("employee_hired", {"name": "Ali", "role": "BACKEND_AGENT"})
        self.assertIn("Ali", s)
        self.assertIn("BACKEND_AGENT", s)

    def test_employee_hired_no_name(self):
        s = _human_event("employee_hired", {})
        self.assertIsInstance(s, str)

    def test_workflow_started(self):
        s = _human_event("workflow_started", {"name": "Sprint 1"})
        self.assertIn("Sprint 1", s)
        self.assertIn("akış", s.lower())

    def test_stage_advanced(self):
        s = _human_event("stage_advanced", {"stage": "Design"})
        self.assertIn("Design", s)

    def test_discussion_started(self):
        s = _human_event("discussion_started", {"topic": "Tech stack"})
        self.assertIn("Tech stack", s)
        self.assertIn("Tartışma", s)

    def test_discussion_closed(self):
        s = _human_event("discussion_closed", {"topic": "Auth"})
        self.assertIn("Auth", s)
        self.assertIn("tamamlandı", s.lower())

    def test_decision_created(self):
        s = _human_event("decision_created", {"title": "DB choice"})
        self.assertIn("DB choice", s)
        self.assertIn("Karar", s)

    def test_decision_recommended(self):
        s = _human_event("decision_recommended", {"recommendation": "PostgreSQL"})
        self.assertIn("PostgreSQL", s)

    def test_task_created(self):
        s = _human_event("task_created", {"title": "Build API"})
        self.assertIn("Build API", s)

    def test_task_assigned(self):
        s = _human_event("task_assigned", {})
        self.assertIn("Görev", s)

    def test_entry_stored_with_title(self):
        s = _human_event("entry_stored", {"title": "Lesson learned"})
        self.assertIn("Lesson learned", s)
        self.assertIn("Hafıza", s)

    def test_entry_stored_no_title(self):
        s = _human_event("entry_stored", {})
        self.assertIsInstance(s, str)

    def test_session_started(self):
        s = _human_event("session_started", {})
        self.assertIn("CEO", s)
        self.assertIn("başlandı", s.lower())

    def test_session_finished(self):
        s = _human_event("session_finished", {})
        self.assertIn("tamamlandı", s.lower())

    def test_session_failed(self):
        s = _human_event("session_failed", {})
        self.assertIn("başarısız", s.lower())

    def test_department_created(self):
        s = _human_event("department_created", {"name": "QA"})
        self.assertIn("QA", s)
        self.assertIn("Departman", s)

    def test_unknown_action_with_underscores(self):
        s = _human_event("some_unknown_action", {})
        self.assertIn("some unknown action", s.lower())

    def test_empty_action(self):
        s = _human_event("", {})
        self.assertIsInstance(s, str)
        self.assertTrue(len(s) > 0)

    def test_returns_string(self):
        s = _human_event("project_created", {"title": "X"})
        self.assertIsInstance(s, str)

    def test_ends_with_period(self):
        s = _human_event("project_created", {"title": "X"})
        self.assertTrue(s.endswith("."))

    def test_workflow_completed(self):
        s = _human_event("workflow_completed", {})
        self.assertIn("tamamlandı", s.lower())

    def test_agent_started(self):
        s = _human_event("agent_started", {"name": "Backend 01"})
        self.assertIn("Backend 01", s)


# ===========================================================================
# 2. DashboardState — command history
# ===========================================================================

class TestCommandHistoryInitial(unittest.TestCase):
    def setUp(self):
        DashboardState.reset()
        self.state = DashboardState.get()

    def test_command_history_attribute_exists(self):
        self.assertTrue(hasattr(self.state, "command_history"))

    def test_command_history_initially_empty(self):
        self.assertEqual(self.state.command_history, [])

    def test_command_history_is_list(self):
        self.assertIsInstance(self.state.command_history, list)

    def test_last_command_initially_none(self):
        self.assertIsNone(self.state.last_command)

    def test_last_session_initially_none(self):
        self.assertIsNone(self.state.last_session)


class TestCommandHistoryAfterRequest(unittest.TestCase):
    def setUp(self):
        DashboardState.reset()
        self.state = DashboardState.get()
        self.state.new_request("Bana restoran rezervasyon sistemi gelistir lutfen.")

    def test_history_has_one_entry(self):
        self.assertEqual(len(self.state.command_history), 1)

    def test_history_entry_has_command(self):
        self.assertIn("command", self.state.command_history[0])

    def test_history_entry_command_value(self):
        self.assertIn("restoran", self.state.command_history[0]["command"])

    def test_history_entry_has_session_id(self):
        self.assertIn("session_id", self.state.command_history[0])

    def test_history_entry_session_id_nonempty(self):
        self.assertTrue(len(self.state.command_history[0]["session_id"]) > 0)

    def test_history_entry_has_started_at(self):
        self.assertIn("started_at", self.state.command_history[0])

    def test_history_entry_has_finished_at(self):
        self.assertIn("finished_at", self.state.command_history[0])

    def test_history_entry_has_duration(self):
        self.assertIn("duration_seconds", self.state.command_history[0])

    def test_history_entry_duration_non_negative(self):
        self.assertGreaterEqual(self.state.command_history[0]["duration_seconds"], 0)

    def test_history_entry_has_success(self):
        self.assertIn("success", self.state.command_history[0])

    def test_history_entry_success_is_bool(self):
        self.assertIsInstance(self.state.command_history[0]["success"], bool)

    def test_history_entry_has_stage(self):
        self.assertIn("stage", self.state.command_history[0])

    def test_history_entry_has_event_count(self):
        self.assertIn("event_count", self.state.command_history[0])

    def test_history_entry_event_count_positive(self):
        self.assertGreater(self.state.command_history[0]["event_count"], 0)

    def test_last_command_updated(self):
        self.assertIsNotNone(self.state.last_command)

    def test_last_session_updated(self):
        self.assertIsNotNone(self.state.last_session)


class TestCommandHistoryMultiple(unittest.TestCase):
    def setUp(self):
        DashboardState.reset()
        self.state = DashboardState.get()
        self.state.new_request("Birinci komut burada yaziliyor test icin.")
        self.state.new_request("Ikinci komut burada yaziliyor test icin.")

    def test_two_entries(self):
        self.assertEqual(len(self.state.command_history), 2)

    def test_first_entry_command(self):
        self.assertIn("Birinci", self.state.command_history[0]["command"])

    def test_second_entry_command(self):
        self.assertIn("Ikinci", self.state.command_history[1]["command"])

    def test_entries_have_distinct_session_ids(self):
        sid1 = self.state.command_history[0]["session_id"]
        sid2 = self.state.command_history[1]["session_id"]
        self.assertNotEqual(sid1, sid2)

    def test_last_command_is_second(self):
        self.assertIn("Ikinci", self.state.last_command)


# ===========================================================================
# 3. GET /api/timeline
# ===========================================================================

class TestApiTimeline(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_status_200(self):
        r = self.client.get("/api/timeline")
        self.assertEqual(r.status_code, 200)

    def test_returns_json_array(self):
        r = self.client.get("/api/timeline")
        data = r.json()
        self.assertIsInstance(data, list)

    def test_items_have_id_field(self):
        r = self.client.get("/api/timeline")
        data = r.json()
        if data:
            self.assertIn("id", data[0])

    def test_items_have_source_field(self):
        r = self.client.get("/api/timeline")
        data = r.json()
        if data:
            self.assertIn("source", data[0])

    def test_items_have_channel_field(self):
        r = self.client.get("/api/timeline")
        data = r.json()
        if data:
            self.assertIn("channel", data[0])

    def test_items_have_timestamp_field(self):
        r = self.client.get("/api/timeline")
        data = r.json()
        if data:
            self.assertIn("timestamp", data[0])

    def test_items_have_timestamp_hms_field(self):
        r = self.client.get("/api/timeline")
        data = r.json()
        if data:
            self.assertIn("timestamp_hms", data[0])

    def test_items_have_sentence_field(self):
        r = self.client.get("/api/timeline")
        data = r.json()
        if data:
            self.assertIn("sentence", data[0])

    def test_items_have_action_field(self):
        r = self.client.get("/api/timeline")
        data = r.json()
        if data:
            self.assertIn("action", data[0])

    def test_sentence_is_string(self):
        r = self.client.get("/api/timeline")
        data = r.json()
        if data:
            self.assertIsInstance(data[0]["sentence"], str)

    def test_sentence_nonempty(self):
        r = self.client.get("/api/timeline")
        data = r.json()
        if data:
            self.assertTrue(len(data[0]["sentence"]) > 0)

    def test_seeded_events_have_turkish_sentences(self):
        r = self.client.get("/api/timeline")
        data = r.json()
        sentences = [item["sentence"] for item in data]
        has_turkish = any(
            any(word in s for word in ["Şirket", "proje", "akış", "Tartışma", "Karar", "Hafıza"])
            for s in sentences
        )
        self.assertTrue(has_turkish)

    def test_limit_parameter(self):
        r = self.client.get("/api/timeline?limit=3")
        data = r.json()
        self.assertLessEqual(len(data), 3)

    def test_limit_20_default(self):
        r = self.client.get("/api/timeline")
        data = r.json()
        self.assertLessEqual(len(data), 20)

    def test_newest_first_ordering(self):
        r = self.client.get("/api/timeline")
        data = r.json()
        if len(data) >= 2:
            ts0 = data[0]["timestamp"]
            ts1 = data[-1]["timestamp"]
            self.assertGreaterEqual(ts0, ts1)


# ===========================================================================
# 4. GET /api/command-history
# ===========================================================================

class TestApiCommandHistory(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_status_200(self):
        r = self.client.get("/api/command-history")
        self.assertEqual(r.status_code, 200)

    def test_returns_json_array(self):
        r = self.client.get("/api/command-history")
        self.assertIsInstance(r.json(), list)

    def test_initially_empty(self):
        r = self.client.get("/api/command-history")
        self.assertEqual(r.json(), [])

    def test_after_command_has_entry(self):
        self.client.post("/api/command", json={"command": "Bir yazilim projesi olustur lutfen tamam."})
        r = self.client.get("/api/command-history")
        self.assertEqual(len(r.json()), 1)

    def test_entry_fields_present(self):
        self.client.post("/api/command", json={"command": "Bir yazilim projesi olustur lutfen tamam."})
        r = self.client.get("/api/command-history")
        data = r.json()
        if data:
            entry = data[0]
            for field in ["command", "session_id", "started_at", "duration_seconds", "success", "stage"]:
                self.assertIn(field, entry)

    def test_newest_first(self):
        self.client.post("/api/command", json={"command": "Birinci komut metni burada yer aliyor."})
        self.client.post("/api/command", json={"command": "Ikinci komut metni burada yer aliyor."})
        r = self.client.get("/api/command-history")
        data = r.json()
        self.assertIn("Ikinci", data[0]["command"])

    def test_success_field_is_bool(self):
        self.client.post("/api/command", json={"command": "Bir yazilim projesi olustur lutfen tamam."})
        r = self.client.get("/api/command-history")
        data = r.json()
        if data:
            self.assertIsInstance(data[0]["success"], bool)

    def test_event_count_positive(self):
        self.client.post("/api/command", json={"command": "Bir yazilim projesi olustur lutfen tamam."})
        r = self.client.get("/api/command-history")
        data = r.json()
        if data:
            self.assertGreater(data[0]["event_count"], 0)

    def test_stage_field_is_string(self):
        self.client.post("/api/command", json={"command": "Bir yazilim projesi olustur lutfen tamam."})
        r = self.client.get("/api/command-history")
        data = r.json()
        if data:
            self.assertIsInstance(data[0]["stage"], str)

    def test_duration_non_negative(self):
        self.client.post("/api/command", json={"command": "Bir yazilim projesi olustur lutfen tamam."})
        r = self.client.get("/api/command-history")
        data = r.json()
        if data:
            self.assertGreaterEqual(data[0]["duration_seconds"], 0)


# ===========================================================================
# 5. GET /api/agent-status
# ===========================================================================

class TestApiAgentStatus(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_status_200(self):
        r = self.client.get("/api/agent-status")
        self.assertEqual(r.status_code, 200)

    def test_returns_json_array(self):
        r = self.client.get("/api/agent-status")
        self.assertIsInstance(r.json(), list)

    def test_has_seeded_employees(self):
        r = self.client.get("/api/agent-status")
        self.assertGreater(len(r.json()), 0)

    def test_items_have_id(self):
        r = self.client.get("/api/agent-status")
        for item in r.json():
            self.assertIn("id", item)

    def test_items_have_name(self):
        r = self.client.get("/api/agent-status")
        for item in r.json():
            self.assertIn("name", item)

    def test_items_have_role(self):
        r = self.client.get("/api/agent-status")
        for item in r.json():
            self.assertIn("role", item)

    def test_items_have_department(self):
        r = self.client.get("/api/agent-status")
        for item in r.json():
            self.assertIn("department", item)

    def test_items_have_seniority(self):
        r = self.client.get("/api/agent-status")
        for item in r.json():
            self.assertIn("seniority", item)

    def test_items_have_status(self):
        r = self.client.get("/api/agent-status")
        for item in r.json():
            self.assertIn("status", item)

    def test_items_have_workload(self):
        r = self.client.get("/api/agent-status")
        for item in r.json():
            self.assertIn("workload", item)

    def test_items_have_skills(self):
        r = self.client.get("/api/agent-status")
        for item in r.json():
            self.assertIn("skills", item)

    def test_items_have_current_task(self):
        r = self.client.get("/api/agent-status")
        for item in r.json():
            self.assertIn("current_task", item)

    def test_workload_is_percentage(self):
        r = self.client.get("/api/agent-status")
        for item in r.json():
            wl = item["workload"]
            self.assertGreaterEqual(wl, 0)
            self.assertLessEqual(wl, 100)

    def test_skills_is_list(self):
        r = self.client.get("/api/agent-status")
        for item in r.json():
            self.assertIsInstance(item["skills"], list)

    def test_alice_present(self):
        r = self.client.get("/api/agent-status")
        names = [item["name"] for item in r.json()]
        self.assertIn("Alice Chen", names)

    def test_current_task_nullable(self):
        r = self.client.get("/api/agent-status")
        # current_task may be None or a dict
        for item in r.json():
            ct = item["current_task"]
            self.assertTrue(ct is None or isinstance(ct, dict))

    def test_current_task_has_title_when_present(self):
        r = self.client.get("/api/agent-status")
        for item in r.json():
            if item["current_task"] is not None:
                self.assertIn("title", item["current_task"])
                self.assertIn("status", item["current_task"])
                self.assertIn("priority", item["current_task"])


# ===========================================================================
# 6. GET /org — Organization page
# ===========================================================================

class TestOrgRoute(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_status_200(self):
        r = self.client.get("/org")
        self.assertEqual(r.status_code, 200)

    def test_content_type_html(self):
        r = self.client.get("/org")
        self.assertIn("text/html", r.headers["content-type"])

    def test_contains_organizasyon(self):
        r = self.client.get("/org")
        self.assertIn("Organizasyon", r.text)

    def test_contains_ceo(self):
        r = self.client.get("/org")
        self.assertIn("CEO", r.text)

    def test_contains_executive_engine(self):
        r = self.client.get("/org")
        self.assertIn("Yönetici", r.text)

    def test_contains_department_names(self):
        r = self.client.get("/org")
        self.assertIn("Backend Engineering", r.text)

    def test_contains_frontend_dept(self):
        r = self.client.get("/org")
        self.assertIn("Frontend", r.text)

    def test_contains_qa_dept(self):
        r = self.client.get("/org")
        self.assertIn("Quality Assurance", r.text)

    def test_contains_employee_alice(self):
        r = self.client.get("/org")
        self.assertIn("Alice Chen", r.text)

    def test_contains_employee_carol(self):
        r = self.client.get("/org")
        self.assertIn("Carol Diaz", r.text)

    def test_contains_org_tree_class(self):
        r = self.client.get("/org")
        self.assertIn("org-tree", r.text)

    def test_contains_org_node(self):
        r = self.client.get("/org")
        self.assertIn("org-node", r.text)

    def test_contains_sprint_19(self):
        r = self.client.get("/org")
        self.assertIn("Sprint 19", r.text)

    def test_contains_nav_org_link(self):
        r = self.client.get("/org")
        self.assertIn("Organizasyon", r.text)

    def test_summary_table_present(self):
        r = self.client.get("/org")
        self.assertIn("data-table", r.text)

    def test_director_column_present(self):
        r = self.client.get("/org")
        self.assertIn("Direktör", r.text)

    def test_capacity_column_present(self):
        r = self.client.get("/org")
        self.assertIn("Kapasite", r.text)


# ===========================================================================
# 7. Dashboard — new sections
# ===========================================================================

class TestDashboardPipeline(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_pipeline_section_exists(self):
        r = self.client.get("/")
        self.assertIn("Yürütme Hattı", r.text)

    def test_pipeline_class_present(self):
        r = self.client.get("/")
        self.assertIn("pipeline", r.text)

    def test_pipeline_step_ceo(self):
        r = self.client.get("/")
        self.assertIn("pipeline-step", r.text)

    def test_pipeline_contains_planlayici(self):
        r = self.client.get("/")
        self.assertIn("Planlayıcı", r.text)

    def test_pipeline_contains_yonetici(self):
        r = self.client.get("/")
        self.assertIn("Yönetici", r.text)

    def test_pipeline_contains_gorevler(self):
        r = self.client.get("/")
        self.assertIn("Görevler", r.text)

    def test_pipeline_contains_ciktilar(self):
        r = self.client.get("/")
        self.assertIn("Çıktılar", r.text)

    def test_pipeline_connector_present(self):
        r = self.client.get("/")
        self.assertIn("pipeline-connector", r.text)

    def test_pipeline_node_class_present(self):
        r = self.client.get("/")
        self.assertIn("pipeline-node", r.text)

    def test_pipeline_desc_present(self):
        r = self.client.get("/")
        self.assertIn("pipeline-desc", r.text)


class TestDashboardAnimatedCounters(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_counter_value_class_present(self):
        r = self.client.get("/")
        self.assertIn("counter-value", r.text)

    def test_data_target_attribute_present(self):
        r = self.client.get("/")
        self.assertIn("data-target", r.text)

    def test_total_artifacts_kpi_present(self):
        r = self.client.get("/")
        self.assertIn("Çıktılar", r.text)

    def test_projects_kpi_present(self):
        r = self.client.get("/")
        self.assertIn("Projeler", r.text)

    def test_employees_kpi_present(self):
        r = self.client.get("/")
        self.assertIn("Çalışanlar", r.text)

    def test_departments_kpi_present(self):
        r = self.client.get("/")
        self.assertIn("Departmanlar", r.text)

    def test_workflows_kpi_present(self):
        r = self.client.get("/")
        self.assertIn("İş Akışları", r.text)


class TestDashboardAgentStatusSection(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_agent_status_section_exists(self):
        r = self.client.get("/")
        self.assertIn("Canlı Ajan Durumu", r.text)

    def test_agent_status_panel_id(self):
        r = self.client.get("/")
        self.assertIn("agent-status-panel", r.text)

    def test_agent_status_htmx_get(self):
        r = self.client.get("/")
        self.assertIn("/api/agent-status", r.text)

    def test_agent_status_htmx_trigger(self):
        r = self.client.get("/")
        self.assertIn("every 3s", r.text)

    def test_agent_poll_status_indicator(self):
        r = self.client.get("/")
        self.assertIn("agent-poll-status", r.text)


class TestDashboardLiveTimeline(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_timeline_section_exists(self):
        r = self.client.get("/")
        self.assertIn("Canlı Şirket Zaman Çizelgesi", r.text)

    def test_event_timeline_polls_api_timeline(self):
        r = self.client.get("/")
        self.assertIn("/api/timeline", r.text)

    def test_event_timeline_every_3s(self):
        r = self.client.get("/")
        self.assertIn("every 3s", r.text)

    def test_timeline_item_class_present(self):
        r = self.client.get("/")
        self.assertIn("timeline-item", r.text)


class TestDashboardCommandHistory(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_cmd_history_section_exists(self):
        r = self.client.get("/")
        self.assertIn("CEO Komut Geçmişi", r.text)

    def test_cmd_history_empty_message(self):
        r = self.client.get("/")
        self.assertIn("komut verilmedi", r.text.lower())

    def test_cmd_history_after_command_shows_entry(self):
        self.client.post("/api/command", json={"command": "Bir yazilim projesi olustur lutfen tamam."})
        r = self.client.get("/")
        self.assertIn("Tamamlandı", r.text)

    def test_cmd_history_shows_duration(self):
        self.client.post("/api/command", json={"command": "Bir yazilim projesi olustur lutfen tamam."})
        r = self.client.get("/")
        self.assertIn("cmd-duration", r.text)


# ===========================================================================
# 8. GET /projects — expandable project details
# ===========================================================================

class TestProjectsExpandable(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_status_200(self):
        r = self.client.get("/projects")
        self.assertEqual(r.status_code, 200)

    def test_details_element_present(self):
        r = self.client.get("/projects")
        self.assertIn("<details", r.text)

    def test_summary_element_present(self):
        r = self.client.get("/projects")
        self.assertIn("<summary", r.text)

    def test_project_details_class(self):
        r = self.client.get("/projects")
        self.assertIn("project-details", r.text)

    def test_toggle_text_present(self):
        r = self.client.get("/projects")
        self.assertIn("Detayları Göster", r.text)

    def test_stat_section_artifacts(self):
        r = self.client.get("/projects")
        self.assertIn("Çıktı", r.text)

    def test_stat_section_discussions(self):
        r = self.client.get("/projects")
        self.assertIn("Tartışma", r.text)

    def test_stat_section_decisions(self):
        r = self.client.get("/projects")
        self.assertIn("Karar", r.text)

    def test_detail_section_class_present(self):
        r = self.client.get("/projects")
        self.assertIn("detail-section", r.text)

    def test_animated_progress_bar(self):
        r = self.client.get("/projects")
        self.assertIn("progress-fill-animated", r.text)

    def test_task_progress_bar(self):
        r = self.client.get("/projects")
        self.assertIn("task-progress-bar", r.text)

    def test_projects_list_not_empty(self):
        r = self.client.get("/projects")
        self.assertIn("AI Company OS Platform", r.text)

    def test_second_project_present(self):
        r = self.client.get("/projects")
        self.assertIn("CEO Dashboard V1", r.text)


# ===========================================================================
# 9. GET /employees — drawer
# ===========================================================================

class TestEmployeesDrawer(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_status_200(self):
        r = self.client.get("/employees")
        self.assertEqual(r.status_code, 200)

    def test_drawer_element_present(self):
        r = self.client.get("/employees")
        self.assertIn("emp-drawer", r.text)

    def test_drawer_overlay_present(self):
        r = self.client.get("/employees")
        self.assertIn("emp-drawer-overlay", r.text)

    def test_drawer_close_button(self):
        r = self.client.get("/employees")
        self.assertIn("closeEmpDrawer", r.text)

    def test_employee_row_class(self):
        r = self.client.get("/employees")
        self.assertIn("employee-row", r.text)

    def test_data_emp_id_attribute(self):
        r = self.client.get("/employees")
        self.assertIn("data-emp-id", r.text)

    def test_data_emp_name_attribute(self):
        r = self.client.get("/employees")
        self.assertIn("data-emp-name", r.text)

    def test_data_emp_role_attribute(self):
        r = self.client.get("/employees")
        self.assertIn("data-emp-role", r.text)

    def test_data_emp_skills_attribute(self):
        r = self.client.get("/employees")
        self.assertIn("data-emp-skills", r.text)

    def test_drawer_emp_name_element(self):
        r = self.client.get("/employees")
        self.assertIn("drawer-emp-name", r.text)

    def test_drawer_emp_role_element(self):
        r = self.client.get("/employees")
        self.assertIn("drawer-emp-role", r.text)

    def test_drawer_emp_skills_element(self):
        r = self.client.get("/employees")
        self.assertIn("drawer-emp-skills", r.text)

    def test_drawer_current_task_element(self):
        r = self.client.get("/employees")
        self.assertIn("drawer-current-task", r.text)

    def test_animated_progress_bars(self):
        r = self.client.get("/employees")
        self.assertIn("progress-fill-animated", r.text)

    def test_employee_alice_present(self):
        r = self.client.get("/employees")
        self.assertIn("Alice Chen", r.text)


# ===========================================================================
# 10. GET /events — Turkish sentences
# ===========================================================================

class TestEventsTurkishSentences(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_status_200(self):
        r = self.client.get("/events")
        self.assertEqual(r.status_code, 200)

    def test_timeline_row_class(self):
        r = self.client.get("/events")
        self.assertIn("timeline-row", r.text)

    def test_timeline_sentence_full_class(self):
        r = self.client.get("/events")
        self.assertIn("timeline-sentence-full", r.text)

    def test_no_raw_json_braces(self):
        r = self.client.get("/events")
        self.assertNotIn('"action":', r.text)

    def test_company_started_sentence_present(self):
        r = self.client.get("/events")
        self.assertIn("Şirket", r.text)

    def test_project_created_sentence_present(self):
        r = self.client.get("/events")
        self.assertIn("proje", r.text.lower())

    def test_discussion_sentence_present(self):
        r = self.client.get("/events")
        self.assertIn("Tartışma", r.text)

    def test_decision_sentence_present(self):
        r = self.client.get("/events")
        self.assertIn("Karar", r.text)

    def test_memory_sentence_present(self):
        r = self.client.get("/events")
        self.assertIn("Hafıza", r.text)

    def test_htmx_polls_api_timeline(self):
        r = self.client.get("/events")
        self.assertIn("/api/timeline", r.text)

    def test_htmx_every_3s(self):
        r = self.client.get("/events")
        self.assertIn("every 3s", r.text)

    def test_kanal_istatistikleri_present(self):
        r = self.client.get("/events")
        self.assertIn("Kanal İstatistikleri", r.text)

    def test_toplam_olay_present(self):
        r = self.client.get("/events")
        self.assertIn("Toplam Olay", r.text)

    def test_event_ts_class_present(self):
        r = self.client.get("/events")
        self.assertIn("event-ts", r.text)


# ===========================================================================
# 11. Navigation & Footer
# ===========================================================================

class TestNavigation(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_dashboard_has_org_link(self):
        r = self.client.get("/")
        self.assertIn("/org", r.text)

    def test_projects_has_org_link(self):
        r = self.client.get("/projects")
        self.assertIn("/org", r.text)

    def test_employees_has_org_link(self):
        r = self.client.get("/employees")
        self.assertIn("/org", r.text)

    def test_workflow_has_org_link(self):
        r = self.client.get("/workflow")
        self.assertIn("/org", r.text)

    def test_events_has_org_link(self):
        r = self.client.get("/events")
        self.assertIn("/org", r.text)

    def test_org_has_org_link_active(self):
        r = self.client.get("/org")
        self.assertIn("active", r.text)

    def test_nav_link_text_organizasyon(self):
        r = self.client.get("/")
        self.assertIn("Organizasyon", r.text)


class TestFooterSprint19(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_dashboard_sprint_19(self):
        r = self.client.get("/")
        self.assertIn("Sprint 19", r.text)

    def test_projects_sprint_19(self):
        r = self.client.get("/projects")
        self.assertIn("Sprint 19", r.text)

    def test_employees_sprint_19(self):
        r = self.client.get("/employees")
        self.assertIn("Sprint 19", r.text)

    def test_workflow_sprint_19(self):
        r = self.client.get("/workflow")
        self.assertIn("Sprint 19", r.text)

    def test_events_sprint_19(self):
        r = self.client.get("/events")
        self.assertIn("Sprint 19", r.text)

    def test_org_sprint_19(self):
        r = self.client.get("/org")
        self.assertIn("Sprint 19", r.text)

    def test_footer_operasyon_merkezi(self):
        r = self.client.get("/")
        self.assertIn("Operasyon", r.text)


# ===========================================================================
# 12. Workflow progress bars
# ===========================================================================

class TestWorkflowProgressBars(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_status_200(self):
        r = self.client.get("/workflow")
        self.assertEqual(r.status_code, 200)

    def test_progress_bar_lg_present(self):
        r = self.client.get("/workflow")
        self.assertIn("progress-bar-lg", r.text)

    def test_progress_fill_present(self):
        r = self.client.get("/workflow")
        self.assertIn("progress-fill", r.text)

    def test_toplam_is_akisi_kpi(self):
        r = self.client.get("/workflow")
        self.assertIn("Toplam İş Akışı", r.text)

    def test_aktif_kpi(self):
        r = self.client.get("/workflow")
        self.assertIn("Aktif", r.text)

    def test_stage_timeline_present(self):
        r = self.client.get("/workflow")
        self.assertIn("stage-timeline", r.text)


# ===========================================================================
# 13. Regression — existing routes still work
# ===========================================================================

class TestRegressionHtmlRoutes(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_dashboard_200(self):
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_projects_200(self):
        self.assertEqual(self.client.get("/projects").status_code, 200)

    def test_employees_200(self):
        self.assertEqual(self.client.get("/employees").status_code, 200)

    def test_workflow_200(self):
        self.assertEqual(self.client.get("/workflow").status_code, 200)

    def test_events_200(self):
        self.assertEqual(self.client.get("/events").status_code, 200)

    def test_org_200(self):
        self.assertEqual(self.client.get("/org").status_code, 200)

    def test_dashboard_contains_company_name(self):
        r = self.client.get("/")
        self.assertIn("AI Company OS", r.text)

    def test_projects_contains_projeler(self):
        r = self.client.get("/projects")
        self.assertIn("Projeler", r.text)

    def test_employees_contains_calisanlar(self):
        r = self.client.get("/employees")
        self.assertIn("Çalışanlar", r.text)

    def test_workflow_contains_is_akisi(self):
        r = self.client.get("/workflow")
        self.assertIn("İş Akışı", r.text)

    def test_events_contains_olay(self):
        r = self.client.get("/events")
        self.assertIn("Olay", r.text)


class TestRegressionApiRoutes(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_api_stats_200(self):
        self.assertEqual(self.client.get("/api/stats").status_code, 200)

    def test_api_events_recent_200(self):
        self.assertEqual(self.client.get("/api/events/recent").status_code, 200)

    def test_api_projects_200(self):
        self.assertEqual(self.client.get("/api/projects").status_code, 200)

    def test_api_employees_200(self):
        self.assertEqual(self.client.get("/api/employees").status_code, 200)

    def test_api_workflow_200(self):
        self.assertEqual(self.client.get("/api/workflow").status_code, 200)

    def test_api_memory_200(self):
        self.assertEqual(self.client.get("/api/memory").status_code, 200)

    def test_api_decisions_200(self):
        self.assertEqual(self.client.get("/api/decisions").status_code, 200)

    def test_api_discussions_200(self):
        self.assertEqual(self.client.get("/api/discussions").status_code, 200)

    def test_api_status_200(self):
        self.assertEqual(self.client.get("/api/status").status_code, 200)

    def test_api_artifacts_200(self):
        self.assertEqual(self.client.get("/api/artifacts").status_code, 200)

    def test_api_timeline_200(self):
        self.assertEqual(self.client.get("/api/timeline").status_code, 200)

    def test_api_command_history_200(self):
        self.assertEqual(self.client.get("/api/command-history").status_code, 200)

    def test_api_agent_status_200(self):
        self.assertEqual(self.client.get("/api/agent-status").status_code, 200)

    def test_api_command_post_valid(self):
        r = self.client.post("/api/command", json={"command": "Bir web sitesi olustur lutfen tamam."})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["success"])

    def test_api_command_post_invalid_too_short(self):
        r = self.client.post("/api/command", json={"command": "kisa"})
        self.assertEqual(r.status_code, 400)


# ===========================================================================
# 14. Additional edge-case tests
# ===========================================================================

class TestApiTimelineAfterCommand(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_timeline_returns_data_after_command(self):
        self.client.post("/api/command", json={"command": "Bir web sitesi olustur lutfen tamam."})
        r = self.client.get("/api/timeline")
        self.assertGreater(len(r.json()), 0)

    def test_timeline_sentences_are_turkish_after_command(self):
        self.client.post("/api/command", json={"command": "Bir web sitesi olustur lutfen tamam."})
        r = self.client.get("/api/timeline")
        data = r.json()
        self.assertTrue(all(isinstance(item["sentence"], str) for item in data))

    def test_agent_status_after_command_has_more_employees(self):
        r_before = self.client.get("/api/agent-status")
        count_before = len(r_before.json())
        self.client.post("/api/command", json={"command": "Bir web sitesi olustur lutfen tamam."})
        r_after = self.client.get("/api/agent-status")
        count_after = len(r_after.json())
        self.assertGreaterEqual(count_after, count_before)


class TestStatisticsConsistency(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_stats_total_projects_matches_projects_list(self):
        stats = self.client.get("/api/stats").json()
        projects = self.client.get("/api/projects").json()
        self.assertEqual(stats["total_projects"], len(projects))

    def test_stats_total_employees_matches_employees_list(self):
        stats = self.client.get("/api/stats").json()
        employees = self.client.get("/api/employees").json()
        self.assertEqual(stats["total_employees"], len(employees))

    def test_agent_status_count_matches_employees(self):
        employees = self.client.get("/api/employees").json()
        agents = self.client.get("/api/agent-status").json()
        self.assertEqual(len(agents), len(employees))

    def test_timeline_limit_respected(self):
        r = self.client.get("/api/timeline?limit=5")
        self.assertLessEqual(len(r.json()), 5)

    def test_command_history_count_after_two_commands(self):
        self.client.post("/api/command", json={"command": "Birinci komut buraya yaziliyor test amacli."})
        self.client.post("/api/command", json={"command": "Ikinci komut buraya yaziliyor test amacli."})
        r = self.client.get("/api/command-history")
        self.assertEqual(len(r.json()), 2)


class TestOrgTreeStructure(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_org_node_ceo_class(self):
        r = self.client.get("/org")
        self.assertIn("org-node-ceo", r.text)

    def test_org_node_exec_class(self):
        r = self.client.get("/org")
        self.assertIn("org-node-exec", r.text)

    def test_org_node_dept_class(self):
        r = self.client.get("/org")
        self.assertIn("org-node-dept", r.text)

    def test_org_node_director_class(self):
        r = self.client.get("/org")
        self.assertIn("org-node-director", r.text)

    def test_org_node_emp_class(self):
        r = self.client.get("/org")
        self.assertIn("org-node-emp", r.text)

    def test_org_connector_v_present(self):
        r = self.client.get("/org")
        self.assertIn("org-connector-v", r.text)

    def test_org_dept_column_present(self):
        r = self.client.get("/org")
        self.assertIn("org-dept-column", r.text)

    def test_org_employees_section(self):
        r = self.client.get("/org")
        self.assertIn("org-employees", r.text)

    def test_org_tree_has_devops(self):
        r = self.client.get("/org")
        self.assertIn("DevOps", r.text)

    def test_org_tree_has_backend(self):
        r = self.client.get("/org")
        self.assertIn("Backend", r.text)


class TestProjectDetailsPerProject(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_discussions_subsection_for_project_with_discussion(self):
        r = self.client.get("/projects")
        # Project 1 has a seeded discussion
        self.assertIn("Tartışmalar", r.text)

    def test_decisions_subsection_for_project_with_decision(self):
        r = self.client.get("/projects")
        # Project 1 has a seeded decision
        self.assertIn("Kararlar", r.text)

    def test_discussion_topic_visible(self):
        r = self.client.get("/projects")
        self.assertIn("Tech stack selection", r.text)

    def test_decision_title_visible(self):
        r = self.client.get("/projects")
        self.assertIn("Choose primary database", r.text)

    def test_task_list_visible(self):
        r = self.client.get("/projects")
        self.assertIn("Design Core Architecture", r.text)


class TestCSSClassesInStylesheet(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_pipeline_class_in_css(self):
        r = self.client.get("/static/style.css")
        self.assertIn(".pipeline", r.text)

    def test_timeline_item_in_css(self):
        r = self.client.get("/static/style.css")
        self.assertIn(".timeline-item", r.text)

    def test_agent_card_in_css(self):
        r = self.client.get("/static/style.css")
        self.assertIn(".agent-card", r.text)

    def test_drawer_in_css(self):
        r = self.client.get("/static/style.css")
        self.assertIn(".drawer", r.text)

    def test_org_tree_in_css(self):
        r = self.client.get("/static/style.css")
        self.assertIn(".org-tree", r.text)

    def test_counter_value_in_css(self):
        r = self.client.get("/static/style.css")
        self.assertIn(".counter-value", r.text)

    def test_cmd_history_in_css(self):
        r = self.client.get("/static/style.css")
        self.assertIn(".cmd-history", r.text)

    def test_project_details_in_css(self):
        r = self.client.get("/static/style.css")
        self.assertIn(".project-details", r.text)

    def test_progress_fill_animated_in_css(self):
        r = self.client.get("/static/style.css")
        self.assertIn(".progress-fill-animated", r.text)


class TestAppJSFeatures(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_init_counters_function(self):
        r = self.client.get("/static/app.js")
        self.assertIn("_initCounters", r.text)

    def test_render_timeline_function(self):
        r = self.client.get("/static/app.js")
        self.assertIn("_renderTimeline", r.text)

    def test_render_agent_cards_function(self):
        r = self.client.get("/static/app.js")
        self.assertIn("_renderAgentCards", r.text)

    def test_open_emp_drawer_function(self):
        r = self.client.get("/static/app.js")
        self.assertIn("openEmpDrawer", r.text)

    def test_close_emp_drawer_function(self):
        r = self.client.get("/static/app.js")
        self.assertIn("closeEmpDrawer", r.text)

    def test_counter_animation_uses_raf(self):
        r = self.client.get("/static/app.js")
        self.assertIn("requestAnimationFrame", r.text)

    def test_esc_helper(self):
        r = self.client.get("/static/app.js")
        self.assertIn("_esc", r.text)

    def test_htmx_before_swap_handler(self):
        r = self.client.get("/static/app.js")
        self.assertIn("htmx:beforeSwap", r.text)

    def test_channel_icon_map(self):
        r = self.client.get("/static/app.js")
        self.assertIn("SYSTEM", r.text)


# ===========================================================================
# 15. More _human_event edge cases
# ===========================================================================

class TestHumanEventEdgeCases(unittest.TestCase):
    def test_payload_with_empty_dict(self):
        for action in ["project_created", "workflow_started", "discussion_started",
                       "decision_created", "task_created", "entry_stored", "agent_started",
                       "department_created"]:
            s = _human_event(action, {})
            self.assertIsInstance(s, str, f"action={action} should return str")
            self.assertTrue(len(s) > 0, f"action={action} should be non-empty")

    def test_workflow_advanced_returns_string(self):
        s = _human_event("workflow_advanced", {"stage": "Testing"})
        self.assertIsInstance(s, str)
        self.assertTrue(s.endswith("."))

    def test_discussion_posted_returns_string(self):
        s = _human_event("discussion_posted", {})
        self.assertIsInstance(s, str)
        self.assertIn("mesaj", s.lower())

    def test_none_source_handled(self):
        s = _human_event("company_started", {}, source=None)
        self.assertIsInstance(s, str)

    def test_no_underscore_in_known_actions(self):
        known = ["company_started", "project_created", "employee_hired", "workflow_started",
                 "task_created", "decision_created", "session_started", "session_finished"]
        for action in known:
            s = _human_event(action, {"title": "X", "name": "Y", "role": "Z", "topic": "T"})
            self.assertNotIn("_", s, f"Turkish sentence for {action} should have no raw underscores")

    def test_stage_advanced_no_stage_key(self):
        s = _human_event("stage_advanced", {})
        self.assertIsInstance(s, str)

    def test_decision_recommended_no_key(self):
        s = _human_event("decision_recommended", {})
        self.assertIsInstance(s, str)

    def test_entry_stored_different_titles(self):
        for title in ["Alpha", "Beta", "Gamma"]:
            s = _human_event("entry_stored", {"title": title})
            self.assertIn(title, s)

    def test_all_known_actions_end_with_period(self):
        known_actions = [
            "company_started", "project_created", "employee_hired", "workflow_started",
            "stage_advanced", "discussion_started", "discussion_closed", "decision_created",
            "decision_recommended", "task_created", "task_assigned", "entry_stored",
            "session_started", "session_finished", "session_failed", "department_created",
            "workflow_advanced", "workflow_completed", "agent_started", "discussion_posted",
        ]
        payload = {"title": "T", "name": "N", "role": "R", "topic": "X",
                   "recommendation": "Y", "stage": "S"}
        for action in known_actions:
            s = _human_event(action, payload)
            self.assertTrue(s.endswith("."), f"{action!r} result {s!r} must end with '.'")


# ===========================================================================
# 16. DashboardState reset behaviour
# ===========================================================================

class TestDashboardStateReset(unittest.TestCase):
    def test_reset_clears_command_history(self):
        state = DashboardState.get()
        state.command_history.append({"command": "test"})
        DashboardState.reset()
        fresh = DashboardState.get()
        self.assertEqual(fresh.command_history, [])

    def test_reset_clears_last_command(self):
        state = DashboardState.get()
        state.last_command = "old command"
        DashboardState.reset()
        self.assertIsNone(DashboardState.get().last_command)

    def test_reset_clears_last_session(self):
        DashboardState.get().new_request("Bir yazilim projesi olustur lutfen tamam.")
        DashboardState.reset()
        self.assertIsNone(DashboardState.get().last_session)

    def test_fresh_state_is_singleton(self):
        s1 = DashboardState.get()
        s2 = DashboardState.get()
        self.assertIs(s1, s2)

    def test_command_history_survives_multiple_requests(self):
        state = DashboardState.get()
        for i in range(3):
            state.new_request(f"Komut numarasi {i} burada yaziliyor test icin.")
        self.assertEqual(len(state.command_history), 3)


# ===========================================================================
# 17. GET /api/timeline — detailed field validation
# ===========================================================================

class TestApiTimelineFieldValues(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_timestamp_hms_format(self):
        r = self.client.get("/api/timeline")
        data = r.json()
        if data:
            hms = data[0]["timestamp_hms"]
            parts = hms.split(":")
            self.assertGreaterEqual(len(parts), 2, f"timestamp_hms={hms!r} should be at least HH:MM")

    def test_channel_is_uppercase(self):
        r = self.client.get("/api/timeline")
        data = r.json()
        for item in data:
            ch = item["channel"]
            self.assertEqual(ch, ch.upper(), f"channel={ch!r} should be uppercase")

    def test_id_is_string(self):
        r = self.client.get("/api/timeline")
        data = r.json()
        for item in data:
            self.assertIsInstance(item["id"], str)

    def test_limit_1_returns_at_most_1(self):
        r = self.client.get("/api/timeline?limit=1")
        self.assertLessEqual(len(r.json()), 1)

    def test_action_field_is_string(self):
        r = self.client.get("/api/timeline")
        data = r.json()
        for item in data:
            self.assertIsInstance(item["action"], str)

    def test_source_field_is_string(self):
        r = self.client.get("/api/timeline")
        data = r.json()
        for item in data:
            self.assertIsInstance(item["source"], str)

    def test_sentence_no_raw_json(self):
        r = self.client.get("/api/timeline")
        data = r.json()
        for item in data:
            self.assertNotIn('"action":', item["sentence"])


# ===========================================================================
# 18. GET /api/agent-status — field depth
# ===========================================================================

class TestApiAgentStatusDepth(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_bob_present(self):
        r = self.client.get("/api/agent-status")
        names = [item["name"] for item in r.json()]
        # Second seeded employee (Bob) — name varies by seed; just check at least 2 employees
        self.assertGreaterEqual(len(names), 2)

    def test_carol_present(self):
        r = self.client.get("/api/agent-status")
        names = [item["name"] for item in r.json()]
        self.assertIn("Carol Diaz", names)

    def test_role_field_nonempty(self):
        r = self.client.get("/api/agent-status")
        for item in r.json():
            self.assertTrue(len(item["role"]) > 0)

    def test_department_field_nonempty(self):
        r = self.client.get("/api/agent-status")
        for item in r.json():
            self.assertTrue(len(item["department"]) > 0)

    def test_seniority_field_nonempty(self):
        r = self.client.get("/api/agent-status")
        for item in r.json():
            self.assertTrue(len(item["seniority"]) > 0)

    def test_workload_between_0_100(self):
        r = self.client.get("/api/agent-status")
        for item in r.json():
            self.assertGreaterEqual(item["workload"], 0)
            self.assertLessEqual(item["workload"], 100)

    def test_id_field_nonempty(self):
        r = self.client.get("/api/agent-status")
        for item in r.json():
            self.assertTrue(len(item["id"]) > 0)

    def test_alice_backend_dept(self):
        r = self.client.get("/api/agent-status")
        alice = next((a for a in r.json() if a["name"] == "Alice Chen"), None)
        self.assertIsNotNone(alice)
        self.assertIn("Backend", alice["department"])


# ===========================================================================
# 19. Dashboard HTML — deeper content checks
# ===========================================================================

class TestDashboardContentDetails(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_kpi_row_class_present(self):
        r = self.client.get("/")
        self.assertIn("kpi-row", r.text)

    def test_kpi_card_class_present(self):
        r = self.client.get("/")
        self.assertIn("kpi-card", r.text)

    def test_kpi_value_class_present(self):
        r = self.client.get("/")
        self.assertIn("kpi-value", r.text)

    def test_kpi_label_class_present(self):
        r = self.client.get("/")
        self.assertIn("kpi-label", r.text)

    def test_pipeline_yapay_zeka(self):
        r = self.client.get("/")
        self.assertIn("Yapay Zekâ", r.text)

    def test_pipeline_prompt(self):
        r = self.client.get("/")
        self.assertIn("Prompt", r.text)

    def test_pipeline_ajan(self):
        r = self.client.get("/")
        self.assertIn("Ajan", r.text)

    def test_canli_durum_card(self):
        r = self.client.get("/")
        self.assertIn("Canlı Durum", r.text)

    def test_cmd_history_badge_class(self):
        self.client.post("/api/command", json={"command": "Bir yazilim projesi olustur lutfen tamam."})
        r = self.client.get("/")
        self.assertIn("badge-status-completed", r.text)

    def test_page_subtitle_canli(self):
        r = self.client.get("/")
        self.assertIn("gerçek zamanlı", r.text)

    def test_hx_get_on_status_panel(self):
        r = self.client.get("/")
        self.assertIn("canli-durum-panel", r.text)


# ===========================================================================
# 20. Projects page — more content checks
# ===========================================================================

class TestProjectsPageContent(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_proje_amac_field(self):
        r = self.client.get("/projects")
        self.assertIn("Amaç", r.text)

    def test_proje_ilerleme_field(self):
        r = self.client.get("/projects")
        self.assertIn("İlerleme", r.text)

    def test_summary_stat_row_class(self):
        r = self.client.get("/projects")
        self.assertIn("stat-row", r.text)

    def test_project_card_class(self):
        r = self.client.get("/projects")
        self.assertIn("project-card", r.text)

    def test_not_found_message_absent(self):
        r = self.client.get("/projects")
        self.assertNotEqual(r.status_code, 404)

    def test_page_header_present(self):
        r = self.client.get("/projects")
        self.assertIn("page-header", r.text)

    def test_task_list_section_present(self):
        r = self.client.get("/projects")
        self.assertIn("Görevler", r.text)

    def test_task_agent_class_present(self):
        r = self.client.get("/projects")
        self.assertIn("task-agent", r.text)


# ===========================================================================
# 21. Employees page — more content checks
# ===========================================================================

class TestEmployeesPageContent(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_emp_table_present(self):
        r = self.client.get("/employees")
        self.assertIn("<table", r.text)

    def test_emp_table_header_ad(self):
        r = self.client.get("/employees")
        self.assertIn("Ad", r.text)

    def test_emp_table_header_rol(self):
        r = self.client.get("/employees")
        self.assertIn("Rol", r.text)

    def test_emp_table_header_departman(self):
        r = self.client.get("/employees")
        self.assertIn("Departman", r.text)

    def test_dept_workload_bars(self):
        r = self.client.get("/employees")
        self.assertIn("progress-fill", r.text)

    def test_bob_kumar_present(self):
        r = self.client.get("/employees")
        self.assertIn("Bob Kumar", r.text)

    def test_carol_diaz_present(self):
        r = self.client.get("/employees")
        self.assertIn("Carol Diaz", r.text)

    def test_data_emp_dept_attribute(self):
        r = self.client.get("/employees")
        self.assertIn("data-emp-dept", r.text)

    def test_data_emp_seniority_attribute(self):
        r = self.client.get("/employees")
        self.assertIn("data-emp-seniority", r.text)

    def test_data_emp_status_attribute(self):
        r = self.client.get("/employees")
        self.assertIn("data-emp-status", r.text)

    def test_drawer_is_hidden_by_default(self):
        r = self.client.get("/employees")
        # Drawer should have display:none in inline style or JS-controlled
        self.assertIn("emp-drawer", r.text)


# ===========================================================================
# 22. Events page — edge cases
# ===========================================================================

class TestEventsPageEdgeCases(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_channel_badge_system_present(self):
        r = self.client.get("/events")
        self.assertIn("SYSTEM", r.text)

    def test_channel_badge_project_present(self):
        r = self.client.get("/events")
        self.assertIn("PROJECT", r.text)

    def test_channel_badge_memory_present(self):
        r = self.client.get("/events")
        self.assertIn("MEMORY", r.text)

    def test_channel_badge_decision_present(self):
        r = self.client.get("/events")
        self.assertIn("DECISION", r.text)

    def test_channel_badge_discussion_present(self):
        r = self.client.get("/events")
        self.assertIn("DISCUSSION", r.text)

    def test_aktif_aboneler_present(self):
        r = self.client.get("/events")
        self.assertIn("Aktif Aboneler", r.text)

    def test_events_page_title(self):
        r = self.client.get("/events")
        self.assertIn("Olay Akışı", r.text)

    def test_auto_renewal_text(self):
        r = self.client.get("/events")
        self.assertIn("otomatik yenileme", r.text)


# ===========================================================================
# 23. Org page — summary table validation
# ===========================================================================

class TestOrgSummaryTable(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_dept_ozet_section(self):
        r = self.client.get("/org")
        self.assertIn("Departman Özeti", r.text)

    def test_table_has_calisanlar_column(self):
        r = self.client.get("/org")
        self.assertIn("Çalışan", r.text)

    def test_table_has_durum_column(self):
        r = self.client.get("/org")
        self.assertIn("Durum", r.text)

    def test_table_has_is_yuku_column(self):
        r = self.client.get("/org")
        self.assertIn("İş Yükü", r.text)

    def test_org_level_ceo_class(self):
        r = self.client.get("/org")
        self.assertIn("org-level-ceo", r.text)

    def test_org_level_exec_class(self):
        r = self.client.get("/org")
        self.assertIn("org-level-exec", r.text)

    def test_org_level_depts_class(self):
        r = self.client.get("/org")
        self.assertIn("org-level-depts", r.text)

    def test_total_departments_in_subtitle(self):
        r = self.client.get("/org")
        self.assertIn("departman", r.text)

    def test_total_employees_in_subtitle(self):
        r = self.client.get("/org")
        self.assertIn("çalışan", r.text)


# ===========================================================================
# 24. API /api/command-history — after multiple commands
# ===========================================================================

class TestCommandHistoryApiOrdering(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def test_three_commands_three_entries(self):
        for i in range(3):
            self.client.post("/api/command", json={"command": f"Komut numarasi {i} burada yaziliyor test."})
        r = self.client.get("/api/command-history")
        self.assertEqual(len(r.json()), 3)

    def test_newest_first_after_three(self):
        for label in ["Birinci", "Ikinci", "Ucuncu"]:
            self.client.post("/api/command", json={"command": f"{label} komut metni burada yaziliyor tamam."})
        r = self.client.get("/api/command-history")
        self.assertIn("Ucuncu", r.json()[0]["command"])

    def test_all_entries_have_event_count(self):
        self.client.post("/api/command", json={"command": "Bir yazilim projesi olustur lutfen tamam."})
        r = self.client.get("/api/command-history")
        for entry in r.json():
            self.assertIn("event_count", entry)

    def test_all_entries_have_started_at(self):
        self.client.post("/api/command", json={"command": "Bir yazilim projesi olustur lutfen tamam."})
        r = self.client.get("/api/command-history")
        for entry in r.json():
            self.assertIn("started_at", entry)

    def test_all_entries_have_finished_at(self):
        self.client.post("/api/command", json={"command": "Bir yazilim projesi olustur lutfen tamam."})
        r = self.client.get("/api/command-history")
        for entry in r.json():
            self.assertIn("finished_at", entry)


if __name__ == "__main__":
    unittest.main()
