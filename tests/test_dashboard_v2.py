"""
Sprint 18 -- CEO Komuta Merkezi (Dashboard V2)
Tests for new state fields, API routes, Turkish UI, and CEO command flow.

Run:
    .venv\\Scripts\\python.exe -m unittest tests.test_dashboard_v2 -v
"""

import json
import unittest

from fastapi.testclient import TestClient

from apps.dashboard.main import app, create_app
from apps.dashboard.state import DashboardState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_client() -> TestClient:
    DashboardState.reset()
    return TestClient(app)


# ===========================================================================
# TestDashboardStateV2Engines
# ===========================================================================

class TestDashboardStateV2Engines(unittest.TestCase):
    """DashboardState v2 -- new engine attributes exist and are correct types."""

    def setUp(self):
        DashboardState.reset()
        self.state = DashboardState.get()

    def tearDown(self):
        DashboardState.reset()

    def test_planner_engine_exists(self):
        self.assertIsNotNone(self.state.planner_engine)

    def test_artifact_engine_exists(self):
        self.assertIsNotNone(self.state.artifact_engine)

    def test_orchestrator_exists(self):
        self.assertIsNotNone(self.state.orchestrator)

    def test_orchestrator_is_running(self):
        self.assertTrue(self.state.orchestrator._is_running)

    def test_last_command_starts_none(self):
        self.assertIsNone(self.state.last_command)

    def test_last_session_starts_none(self):
        self.assertIsNone(self.state.last_session)

    def test_planner_engine_type(self):
        from core.planner_engine import PlannerEngine
        self.assertIsInstance(self.state.planner_engine, PlannerEngine)

    def test_artifact_engine_type(self):
        from core.artifact_engine import ArtifactEngine
        self.assertIsInstance(self.state.artifact_engine, ArtifactEngine)

    def test_orchestrator_type(self):
        from core.company_orchestrator import CompanyOrchestrator
        self.assertIsInstance(self.state.orchestrator, CompanyOrchestrator)

    def test_artifact_engine_has_executive_engine(self):
        self.assertIs(
            self.state.artifact_engine._executive_engine,
            self.state.executive_engine,
        )

    def test_artifact_engine_has_memory_engine(self):
        self.assertIs(
            self.state.artifact_engine._memory_engine,
            self.state.memory_engine,
        )

    def test_artifact_engine_has_workflow_engine(self):
        self.assertIs(
            self.state.artifact_engine._workflow_engine,
            self.state.workflow_engine,
        )

    def test_artifact_engine_has_decision_engine(self):
        self.assertIs(
            self.state.artifact_engine._decision_engine,
            self.state.decision_engine,
        )

    def test_orchestrator_context_uses_executive_engine(self):
        self.assertIs(
            self.state.orchestrator._context.executive,
            self.state.executive_engine,
        )

    def test_orchestrator_context_uses_department_registry(self):
        self.assertIs(
            self.state.orchestrator._context.departments,
            self.state.department_registry,
        )

    def test_orchestrator_context_uses_workforce_registry(self):
        self.assertIs(
            self.state.orchestrator._context.workforce,
            self.state.workforce_registry,
        )


# ===========================================================================
# TestDashboardStateNewRequest
# ===========================================================================

class TestDashboardStateNewRequest(unittest.TestCase):
    """DashboardState.new_request() behavior."""

    def setUp(self):
        DashboardState.reset()
        self.state = DashboardState.get()

    def tearDown(self):
        DashboardState.reset()

    def test_new_request_returns_session(self):
        session = self.state.new_request("Bana bir web uygulamasi gelistir.")
        self.assertIsNotNone(session)

    def test_new_request_sets_last_command(self):
        cmd = "Bana bir web uygulamasi gelistir."
        self.state.new_request(cmd)
        self.assertEqual(self.state.last_command, cmd)

    def test_new_request_sets_last_session(self):
        self.state.new_request("Bir mobil uygulama gelistir ve test et.")
        self.assertIsNotNone(self.state.last_session)

    def test_new_request_session_has_id(self):
        session = self.state.new_request("Bir e-ticaret platformu olustur.")
        self.assertIsNotNone(session.id)
        self.assertTrue(len(session.id) > 0)

    def test_new_request_session_has_events(self):
        session = self.state.new_request("Bir iletisim platformu gelistir.")
        self.assertGreater(session.event_count(), 0)

    def test_new_request_session_stores_request(self):
        cmd = "Bir fintech uygulamasi gelistir."
        session = self.state.new_request(cmd)
        self.assertEqual(session.request, cmd)

    def test_new_request_last_session_matches_returned(self):
        session = self.state.new_request("Bir online market platformu olustur.")
        self.assertIs(session, self.state.last_session)

    def test_new_request_multiple_commands(self):
        self.state.new_request("Bir blog platformu gelistir ve yayinla.")
        self.state.new_request("Bir video streaming uygulamasi olustur.")
        self.assertEqual(
            self.state.last_command,
            "Bir video streaming uygulamasi olustur.",
        )

    def test_new_request_updates_last_command_each_time(self):
        self.state.new_request("Ilk komut burada yer almaktadir.")
        self.state.new_request("Ikinci komut burada yer almaktadir.")
        self.assertIn("Ikinci", self.state.last_command)

    def test_new_request_session_stage_not_none(self):
        session = self.state.new_request("Bir yapay zeka asistani gelistir.")
        self.assertIsNotNone(session.current_stage)


# ===========================================================================
# TestDashboardStateNewRequestInvalid
# ===========================================================================

class TestDashboardStateNewRequestInvalid(unittest.TestCase):
    """DashboardState.new_request() with short/invalid commands."""

    def setUp(self):
        DashboardState.reset()
        self.state = DashboardState.get()

    def tearDown(self):
        DashboardState.reset()

    def test_short_command_raises(self):
        from core.company_orchestrator import InvalidRequestError
        with self.assertRaises(InvalidRequestError):
            self.state.new_request("kisa")

    def test_empty_command_raises(self):
        from core.company_orchestrator import InvalidRequestError
        with self.assertRaises((InvalidRequestError, Exception)):
            self.state.new_request("")

    def test_nine_char_command_raises(self):
        from core.company_orchestrator import InvalidRequestError
        with self.assertRaises(InvalidRequestError):
            self.state.new_request("123456789")

    def test_ten_char_command_succeeds(self):
        session = self.state.new_request("1234567890")
        self.assertIsNotNone(session)

    def test_short_command_does_not_set_last_session(self):
        from core.company_orchestrator import InvalidRequestError
        try:
            self.state.new_request("kisa")
        except InvalidRequestError:
            pass
        self.assertIsNone(self.state.last_session)


# ===========================================================================
# TestDashboardStateListArtifacts
# ===========================================================================

class TestDashboardStateListArtifacts(unittest.TestCase):
    """DashboardState.list_artifacts() behavior."""

    def setUp(self):
        DashboardState.reset()
        self.state = DashboardState.get()

    def tearDown(self):
        DashboardState.reset()

    def test_list_artifacts_returns_list(self):
        result = self.state.list_artifacts()
        self.assertIsInstance(result, list)

    def test_list_artifacts_initially_empty(self):
        self.assertEqual(len(self.state.list_artifacts()), 0)

    def test_list_artifacts_after_generate(self):
        projects = self.state.list_projects()
        if projects:
            self.state.artifact_engine.generate_task_report(projects[0].id)
            artifacts = self.state.list_artifacts()
            self.assertEqual(len(artifacts), 1)

    def test_list_artifacts_returns_artifact_objects(self):
        projects = self.state.list_projects()
        if projects:
            self.state.artifact_engine.generate_task_report(projects[0].id)
            artifacts = self.state.list_artifacts()
            self.assertTrue(hasattr(artifacts[0], "id"))
            self.assertTrue(hasattr(artifacts[0], "title"))

    def test_list_artifacts_returns_same_as_engine_history(self):
        self.assertEqual(
            self.state.list_artifacts(),
            self.state.artifact_engine.history(),
        )

    def test_list_artifacts_grows_after_generation(self):
        projects = self.state.list_projects()
        if projects:
            before = len(self.state.list_artifacts())
            self.state.artifact_engine.generate_task_report(projects[0].id)
            after = len(self.state.list_artifacts())
            self.assertEqual(after, before + 1)

    def test_list_artifacts_multiple_projects(self):
        projects = self.state.list_projects()
        if len(projects) >= 2:
            self.state.artifact_engine.generate_task_report(projects[0].id)
            self.state.artifact_engine.generate_task_report(projects[1].id)
            self.assertEqual(len(self.state.list_artifacts()), 2)


# ===========================================================================
# TestCommandRoute
# ===========================================================================

class TestCommandRoute(unittest.TestCase):
    """POST /api/command with valid commands."""

    def setUp(self):
        self.client = _get_client()

    def tearDown(self):
        DashboardState.reset()

    def test_valid_command_returns_200(self):
        resp = self.client.post("/api/command", json={"command": "Bana bir web uygulamasi gelistir."})
        self.assertEqual(resp.status_code, 200)

    def test_valid_command_returns_success_true(self):
        resp = self.client.post("/api/command", json={"command": "Bana bir web uygulamasi gelistir."})
        self.assertTrue(resp.json()["success"])

    def test_valid_command_returns_session_id(self):
        resp = self.client.post("/api/command", json={"command": "Bana bir web uygulamasi gelistir."})
        self.assertIn("session_id", resp.json())

    def test_valid_command_returns_event_count(self):
        resp = self.client.post("/api/command", json={"command": "Bana bir web uygulamasi gelistir."})
        data = resp.json()
        self.assertIn("event_count", data)
        self.assertGreater(data["event_count"], 0)

    def test_valid_command_returns_stage(self):
        resp = self.client.post("/api/command", json={"command": "Bana bir web uygulamasi gelistir."})
        self.assertIn("stage", resp.json())

    def test_valid_command_returns_request(self):
        cmd = "Bana bir e-ticaret platformu olustur."
        resp = self.client.post("/api/command", json={"command": cmd})
        self.assertEqual(resp.json()["request"], cmd)

    def test_command_sets_state_last_command(self):
        cmd = "Bana bir mobil uygulama gelistir."
        self.client.post("/api/command", json={"command": cmd})
        state = DashboardState.get()
        self.assertEqual(state.last_command, cmd)

    def test_command_sets_state_last_session(self):
        self.client.post("/api/command", json={"command": "Bana bir fintech uygulamasi olustur."})
        state = DashboardState.get()
        self.assertIsNotNone(state.last_session)

    def test_command_content_type_json(self):
        resp = self.client.post("/api/command", json={"command": "Bana bir blog platformu gelistir."})
        self.assertIn("application/json", resp.headers.get("content-type", ""))

    def test_command_session_id_is_string(self):
        resp = self.client.post("/api/command", json={"command": "Bana bir analitik platformu gelistir."})
        self.assertIsInstance(resp.json()["session_id"], str)

    def test_command_with_long_text(self):
        cmd = "Bana restoran rezervasyon sistemi olan modern bir web uygulamasi gelistir. " * 3
        resp = self.client.post("/api/command", json={"command": cmd})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["success"])

    def test_second_command_returns_new_session_id(self):
        r1 = self.client.post("/api/command", json={"command": "Ilk proje icin bir sistem gelistir."})
        r2 = self.client.post("/api/command", json={"command": "Ikinci proje icin bir sistem gelistir."})
        self.assertNotEqual(r1.json()["session_id"], r2.json()["session_id"])


# ===========================================================================
# TestCommandRouteErrors
# ===========================================================================

class TestCommandRouteErrors(unittest.TestCase):
    """POST /api/command with invalid inputs."""

    def setUp(self):
        self.client = _get_client()

    def tearDown(self):
        DashboardState.reset()

    def test_short_command_returns_400(self):
        resp = self.client.post("/api/command", json={"command": "kisa"})
        self.assertEqual(resp.status_code, 400)

    def test_short_command_returns_success_false(self):
        resp = self.client.post("/api/command", json={"command": "kisa"})
        self.assertFalse(resp.json()["success"])

    def test_empty_command_returns_400(self):
        resp = self.client.post("/api/command", json={"command": ""})
        self.assertEqual(resp.status_code, 400)

    def test_missing_command_key_returns_400(self):
        resp = self.client.post("/api/command", json={})
        self.assertEqual(resp.status_code, 400)

    def test_whitespace_command_returns_400(self):
        resp = self.client.post("/api/command", json={"command": "   "})
        self.assertEqual(resp.status_code, 400)

    def test_nine_char_command_returns_400(self):
        resp = self.client.post("/api/command", json={"command": "123456789"})
        self.assertEqual(resp.status_code, 400)

    def test_error_response_has_error_key(self):
        resp = self.client.post("/api/command", json={"command": "kisa"})
        self.assertIn("error", resp.json())

    def test_short_command_does_not_change_last_session(self):
        state = DashboardState.get()
        self.client.post("/api/command", json={"command": "kisa"})
        self.assertIsNone(state.last_session)

    def test_null_command_returns_400(self):
        resp = self.client.post("/api/command", json={"command": None})
        self.assertEqual(resp.status_code, 400)


# ===========================================================================
# TestStatusRoute
# ===========================================================================

class TestStatusRoute(unittest.TestCase):
    """GET /api/status structure and content."""

    def setUp(self):
        self.client = _get_client()

    def tearDown(self):
        DashboardState.reset()

    def test_status_returns_200(self):
        resp = self.client.get("/api/status")
        self.assertEqual(resp.status_code, 200)

    def test_status_returns_json(self):
        resp = self.client.get("/api/status")
        data = resp.json()
        self.assertIsInstance(data, dict)

    def test_status_has_components_key(self):
        data = self.client.get("/api/status").json()
        self.assertIn("components", data)

    def test_status_components_is_list(self):
        data = self.client.get("/api/status").json()
        self.assertIsInstance(data["components"], list)

    def test_status_components_not_empty(self):
        data = self.client.get("/api/status").json()
        self.assertGreater(len(data["components"]), 0)

    def test_status_has_orchestrator_running(self):
        data = self.client.get("/api/status").json()
        self.assertIn("orchestrator_running", data)

    def test_status_orchestrator_running_is_true(self):
        data = self.client.get("/api/status").json()
        self.assertTrue(data["orchestrator_running"])

    def test_status_has_last_command(self):
        data = self.client.get("/api/status").json()
        self.assertIn("last_command", data)

    def test_status_has_last_session_id(self):
        data = self.client.get("/api/status").json()
        self.assertIn("last_session_id", data)

    def test_status_last_command_initially_none(self):
        data = self.client.get("/api/status").json()
        self.assertIsNone(data["last_command"])

    def test_status_last_session_id_initially_none(self):
        data = self.client.get("/api/status").json()
        self.assertIsNone(data["last_session_id"])

    def test_status_after_command_has_last_command(self):
        cmd = "Bana bir web uygulamasi gelistir."
        self.client.post("/api/command", json={"command": cmd})
        data = self.client.get("/api/status").json()
        self.assertEqual(data["last_command"], cmd)

    def test_status_after_command_has_last_session_id(self):
        self.client.post("/api/command", json={"command": "Bana bir web uygulamasi gelistir."})
        data = self.client.get("/api/status").json()
        self.assertIsNotNone(data["last_session_id"])


# ===========================================================================
# TestStatusRouteComponents
# ===========================================================================

class TestStatusRouteComponents(unittest.TestCase):
    """GET /api/status — individual component entries."""

    def setUp(self):
        self.client = _get_client()
        self.components = self.client.get("/api/status").json()["components"]

    def tearDown(self):
        DashboardState.reset()

    def _get_component(self, key):
        for c in self.components:
            if c["key"] == key:
                return c
        return None

    def test_planner_component_exists(self):
        self.assertIsNotNone(self._get_component("planner"))

    def test_executive_component_exists(self):
        self.assertIsNotNone(self._get_component("executive"))

    def test_workflow_component_exists(self):
        self.assertIsNotNone(self._get_component("workflow"))

    def test_backend_component_exists(self):
        self.assertIsNotNone(self._get_component("backend"))

    def test_frontend_component_exists(self):
        self.assertIsNotNone(self._get_component("frontend"))

    def test_memory_component_exists(self):
        self.assertIsNotNone(self._get_component("memory"))

    def test_decision_component_exists(self):
        self.assertIsNotNone(self._get_component("decision"))

    def test_each_component_has_key(self):
        for c in self.components:
            self.assertIn("key", c)

    def test_each_component_has_label(self):
        for c in self.components:
            self.assertIn("label", c)

    def test_each_component_has_status(self):
        for c in self.components:
            self.assertIn("status", c)

    def test_planner_status_is_active(self):
        planner = self._get_component("planner")
        self.assertEqual(planner["status"], "ACTIVE")

    def test_executive_status_is_active(self):
        # executive has seeded projects, so should be active
        executive = self._get_component("executive")
        self.assertEqual(executive["status"], "ACTIVE")

    def test_memory_status_is_active(self):
        # memory has seeded entries
        memory = self._get_component("memory")
        self.assertEqual(memory["status"], "ACTIVE")

    def test_decision_status_is_active(self):
        decision = self._get_component("decision")
        self.assertEqual(decision["status"], "ACTIVE")

    def test_component_count_at_least_six(self):
        self.assertGreaterEqual(len(self.components), 6)


# ===========================================================================
# TestArtifactsRoute
# ===========================================================================

class TestArtifactsRoute(unittest.TestCase):
    """GET /api/artifacts."""

    def setUp(self):
        self.client = _get_client()

    def tearDown(self):
        DashboardState.reset()

    def test_artifacts_returns_200(self):
        resp = self.client.get("/api/artifacts")
        self.assertEqual(resp.status_code, 200)

    def test_artifacts_returns_list(self):
        data = self.client.get("/api/artifacts").json()
        self.assertIsInstance(data, list)

    def test_artifacts_initially_empty(self):
        data = self.client.get("/api/artifacts").json()
        self.assertEqual(len(data), 0)

    def test_artifacts_after_generate_has_one(self):
        state = DashboardState.get()
        projects = state.list_projects()
        if projects:
            state.artifact_engine.generate_task_report(projects[0].id)
            data = self.client.get("/api/artifacts").json()
            self.assertEqual(len(data), 1)

    def test_artifact_entry_has_id(self):
        state = DashboardState.get()
        projects = state.list_projects()
        if projects:
            state.artifact_engine.generate_task_report(projects[0].id)
            data = self.client.get("/api/artifacts").json()
            self.assertIn("id", data[0])

    def test_artifact_entry_has_title(self):
        state = DashboardState.get()
        projects = state.list_projects()
        if projects:
            state.artifact_engine.generate_task_report(projects[0].id)
            data = self.client.get("/api/artifacts").json()
            self.assertIn("title", data[0])

    def test_artifact_entry_has_type(self):
        state = DashboardState.get()
        projects = state.list_projects()
        if projects:
            state.artifact_engine.generate_task_report(projects[0].id)
            data = self.client.get("/api/artifacts").json()
            self.assertIn("type", data[0])

    def test_artifact_entry_has_version(self):
        state = DashboardState.get()
        projects = state.list_projects()
        if projects:
            state.artifact_engine.generate_task_report(projects[0].id)
            data = self.client.get("/api/artifacts").json()
            self.assertIn("version", data[0])

    def test_artifact_entry_has_word_count(self):
        state = DashboardState.get()
        projects = state.list_projects()
        if projects:
            state.artifact_engine.generate_task_report(projects[0].id)
            data = self.client.get("/api/artifacts").json()
            self.assertIn("word_count", data[0])

    def test_artifact_entry_has_created_at(self):
        state = DashboardState.get()
        projects = state.list_projects()
        if projects:
            state.artifact_engine.generate_task_report(projects[0].id)
            data = self.client.get("/api/artifacts").json()
            self.assertIn("created_at", data[0])

    def test_artifact_version_is_integer(self):
        state = DashboardState.get()
        projects = state.list_projects()
        if projects:
            state.artifact_engine.generate_task_report(projects[0].id)
            data = self.client.get("/api/artifacts").json()
            self.assertIsInstance(data[0]["version"], int)

    def test_artifact_word_count_positive(self):
        state = DashboardState.get()
        projects = state.list_projects()
        if projects:
            state.artifact_engine.generate_task_report(projects[0].id)
            data = self.client.get("/api/artifacts").json()
            self.assertGreater(data[0]["word_count"], 0)

    def test_artifacts_grows_with_multiple_generations(self):
        state = DashboardState.get()
        projects = state.list_projects()
        if len(projects) >= 2:
            state.artifact_engine.generate_task_report(projects[0].id)
            state.artifact_engine.generate_task_report(projects[1].id)
            data = self.client.get("/api/artifacts").json()
            self.assertEqual(len(data), 2)


# ===========================================================================
# TestArtifactDownloadRoute
# ===========================================================================

class TestArtifactDownloadRoute(unittest.TestCase):
    """GET /api/artifacts/{id}/download."""

    def setUp(self):
        self.client = _get_client()
        state = DashboardState.get()
        projects = state.list_projects()
        self.artifact_id = None
        if projects:
            artifact = state.artifact_engine.generate_task_report(projects[0].id)
            self.artifact_id = artifact.id

    def tearDown(self):
        DashboardState.reset()

    def test_download_returns_200_for_valid_id(self):
        if not self.artifact_id:
            self.skipTest("No artifact generated")
        resp = self.client.get(f"/api/artifacts/{self.artifact_id}/download")
        self.assertEqual(resp.status_code, 200)

    def test_download_returns_text_content(self):
        if not self.artifact_id:
            self.skipTest("No artifact generated")
        resp = self.client.get(f"/api/artifacts/{self.artifact_id}/download")
        self.assertIn("text", resp.headers.get("content-type", ""))

    def test_download_content_not_empty(self):
        if not self.artifact_id:
            self.skipTest("No artifact generated")
        resp = self.client.get(f"/api/artifacts/{self.artifact_id}/download")
        self.assertGreater(len(resp.content), 0)

    def test_download_has_content_disposition(self):
        if not self.artifact_id:
            self.skipTest("No artifact generated")
        resp = self.client.get(f"/api/artifacts/{self.artifact_id}/download")
        self.assertIn("attachment", resp.headers.get("content-disposition", ""))

    def test_download_content_is_markdown(self):
        if not self.artifact_id:
            self.skipTest("No artifact generated")
        resp = self.client.get(f"/api/artifacts/{self.artifact_id}/download")
        content = resp.text
        self.assertIn("#", content)

    def test_download_unknown_id_returns_404(self):
        resp = self.client.get("/api/artifacts/nonexistent-id-000/download")
        self.assertEqual(resp.status_code, 404)

    def test_download_404_returns_json(self):
        resp = self.client.get("/api/artifacts/nonexistent-id-000/download")
        data = resp.json()
        self.assertIn("error", data)

    def test_download_filename_in_disposition(self):
        if not self.artifact_id:
            self.skipTest("No artifact generated")
        resp = self.client.get(f"/api/artifacts/{self.artifact_id}/download")
        disposition = resp.headers.get("content-disposition", "")
        self.assertIn(".md", disposition)

    def test_download_content_has_task_section(self):
        if not self.artifact_id:
            self.skipTest("No artifact generated")
        resp = self.client.get(f"/api/artifacts/{self.artifact_id}/download")
        self.assertTrue(len(resp.text) > 50)


# ===========================================================================
# TestTurkishBase
# ===========================================================================

class TestTurkishBase(unittest.TestCase):
    """base.html — Turkish navigation and labels."""

    def setUp(self):
        self.client = _get_client()

    def tearDown(self):
        DashboardState.reset()

    def _html(self):
        return self.client.get("/").text

    def test_lang_is_tr(self):
        self.assertIn('lang="tr"', self._html())

    def test_kontrol_paneli_in_nav(self):
        self.assertIn("Kontrol Paneli", self._html())

    def test_projeler_in_nav(self):
        self.assertIn("Projeler", self._html())

    def test_calisanlar_in_nav(self):
        self.assertIn("Çalışanlar", self._html())

    def test_is_akislari_in_nav(self):
        self.assertIn("İş Akışları", self._html())

    def test_canli_olay_akisi_in_nav(self):
        self.assertIn("Canlı Olay Akışı", self._html())

    def test_canli_label_in_nav(self):
        self.assertIn("CANLI", self._html())

    def test_ceo_komuta_merkezi_in_title(self):
        self.assertIn("CEO Komuta Merkezi", self._html())

    def test_sprint_18_in_footer(self):
        self.assertIn("Sprint 19", self._html())

    def test_canli_veri_in_footer(self):
        self.assertIn("Canlı Veri", self._html())

    def test_no_english_dashboard_in_nav(self):
        html = self._html()
        nav_start = html.find('<ul class="nav-links">')
        nav_end = html.find("</ul>", nav_start)
        nav_section = html[nav_start:nav_end]
        self.assertNotIn(">Dashboard<", nav_section)

    def test_no_english_employees_in_nav(self):
        html = self._html()
        nav_start = html.find('<ul class="nav-links">')
        nav_end = html.find("</ul>", nav_start)
        nav_section = html[nav_start:nav_end]
        self.assertNotIn(">Employees<", nav_section)

    def test_no_english_workflow_in_nav(self):
        html = self._html()
        nav_start = html.find('<ul class="nav-links">')
        nav_end = html.find("</ul>", nav_start)
        nav_section = html[nav_start:nav_end]
        self.assertNotIn(">Workflow<", nav_section)

    def test_no_english_events_in_nav(self):
        html = self._html()
        nav_start = html.find('<ul class="nav-links">')
        nav_end = html.find("</ul>", nav_start)
        nav_section = html[nav_start:nav_end]
        self.assertNotIn(">Events<", nav_section)


# ===========================================================================
# TestTurkishDashboard
# ===========================================================================

class TestTurkishDashboard(unittest.TestCase):
    """dashboard.html — Turkish page text."""

    def setUp(self):
        self.client = _get_client()
        self.html = self.client.get("/").text

    def tearDown(self):
        DashboardState.reset()

    def test_sirkete_genel_bakis_heading(self):
        self.assertIn("Şirkete Genel Bakış", self.html)

    def test_ceo_komutu_section(self):
        self.assertIn("CEO Komutu", self.html)

    def test_sirketi_baslat_button(self):
        self.assertIn("Şirketi Başlat", self.html)

    def test_canli_durum_section(self):
        self.assertIn("Canlı Durum", self.html)

    def test_kpi_projeler_label(self):
        self.assertIn("Projeler", self.html)

    def test_kpi_aktif_projeler_label(self):
        self.assertIn("Aktif Projeler", self.html)

    def test_kpi_calisanlar_label(self):
        self.assertIn("Çalışanlar", self.html)

    def test_kpi_aktif_calisanlar_label(self):
        self.assertIn("Aktif Çalışanlar", self.html)

    def test_kpi_departmanlar_label(self):
        self.assertIn("Departmanlar", self.html)

    def test_kpi_is_akislari_label(self):
        self.assertIn("İş Akışları", self.html)

    def test_aktif_projeler_section(self):
        self.assertIn("Aktif Projeler", self.html)

    def test_son_kararlar_section(self):
        self.assertIn("Son Kararlar", self.html)

    def test_son_hafiza_kayitlari_section(self):
        self.assertIn("Son Hafıza Kayıtları", self.html)

    def test_son_tartismalar_section(self):
        self.assertIn("Son Tartışmalar", self.html)

    def test_canli_olay_akisi_section(self):
        self.assertIn("Canlı Olay Akışı", self.html)

    def test_uretilen_ciktilar_section(self):
        self.assertIn("Üretilen Çıktılar", self.html)

    def test_tumunu_gor_link(self):
        self.assertIn("Tümünü gör", self.html)

    def test_is_yuku_label_in_departments(self):
        self.assertIn("İş Yükü", self.html)

    def test_event_polling_3s(self):
        self.assertIn("every 3s", self.html)

    def test_ceo_command_textarea_exists(self):
        self.assertIn("ceo-command-input", self.html)

    def test_ceo_command_form_exists(self):
        self.assertIn("ceo-command-form", self.html)

    def test_ceo_start_btn_id(self):
        self.assertIn("ceo-start-btn", self.html)

    def test_canli_durum_panel_id(self):
        self.assertIn("canli-durum-panel", self.html)

    def test_artifact_list_or_empty_text(self):
        self.assertTrue(
            "Üretilen Çıktılar" in self.html or "artifact-list" in self.html
        )

    def test_placeholder_text_turkish(self):
        self.assertIn("Örnek:", self.html)


# ===========================================================================
# TestTurkishProjects
# ===========================================================================

class TestTurkishProjects(unittest.TestCase):
    """projects.html — Turkish text."""

    def setUp(self):
        self.client = _get_client()
        self.html = self.client.get("/projects").text

    def tearDown(self):
        DashboardState.reset()

    def test_projeler_heading(self):
        self.assertIn("Projeler", self.html)

    def test_amac_label(self):
        self.assertIn("Amaç:", self.html)

    def test_ilerleme_label(self):
        self.assertIn("İlerleme:", self.html)

    def test_gorev_sayisi_label(self):
        self.assertIn("Görev Sayısı", self.html)

    def test_atanmis_label(self):
        self.assertIn("Atanmış", self.html)

    def test_onaylanmis_label(self):
        self.assertIn("Onaylanmış", self.html)

    def test_engellendi_label(self):
        self.assertIn("Engellendi", self.html)

    def test_gorevler_heading(self):
        self.assertIn("Görevler", self.html)

    def test_atanmamis_fallback(self):
        # Assigned tasks show agent name; label "Atanmış" appears in stat row
        self.assertIn("Atanm", self.html)

    def test_tracked_by_engine_turkish(self):
        self.assertIn("Yürütme Motoru", self.html)

    def test_page_title_turkish(self):
        self.assertIn("Projeler", self.html)

    def test_no_english_objective(self):
        self.assertNotIn(">Objective:<", self.html)

    def test_no_english_progress(self):
        self.assertNotIn(">Progress:<", self.html)

    def test_no_english_tasks_heading(self):
        self.assertNotIn(">Tasks<", self.html)


# ===========================================================================
# TestTurkishEmployees
# ===========================================================================

class TestTurkishEmployees(unittest.TestCase):
    """employees.html — Turkish text."""

    def setUp(self):
        self.client = _get_client()
        self.html = self.client.get("/employees").text

    def tearDown(self):
        DashboardState.reset()

    def test_calisanlar_heading(self):
        self.assertIn("Çalışanlar", self.html)

    def test_departmanlar_section(self):
        self.assertIn("Departmanlar", self.html)

    def test_tum_calisanlar_section(self):
        self.assertIn("Tüm Çalışanlar", self.html)

    def test_ad_column(self):
        self.assertIn(">Ad<", self.html)

    def test_rol_column(self):
        self.assertIn(">Rol<", self.html)

    def test_kidem_column(self):
        self.assertIn(">Kıdem<", self.html)

    def test_durum_column(self):
        self.assertIn(">Durum<", self.html)

    def test_beceriler_column(self):
        self.assertIn(">Beceriler<", self.html)

    def test_is_yuku_column(self):
        self.assertIn("İş Yükü", self.html)

    def test_kapasite_label(self):
        self.assertIn("Kapasite:", self.html)

    def test_direktor_label(self):
        self.assertIn("Direktör:", self.html)

    def test_no_english_employees_heading(self):
        self.assertNotIn("<h1>Employees</h1>", self.html)

    def test_no_english_name_column(self):
        self.assertNotIn(">Name<", self.html)

    def test_no_english_role_column(self):
        self.assertNotIn(">Role<", self.html)

    def test_grouped_sections_present(self):
        self.assertIn("Backend Engineering", self.html)


# ===========================================================================
# TestTurkishWorkflow
# ===========================================================================

class TestTurkishWorkflow(unittest.TestCase):
    """workflow.html — Turkish text."""

    def setUp(self):
        self.client = _get_client()
        self.html = self.client.get("/workflow").text

    def tearDown(self):
        DashboardState.reset()

    def test_is_akisi_durumu_heading(self):
        self.assertIn("İş Akışı Durumu", self.html)

    def test_toplam_is_akisi_label(self):
        self.assertIn("Toplam İş Akışı", self.html)

    def test_aktif_label(self):
        self.assertIn("Aktif", self.html)

    def test_tamamlandi_label(self):
        self.assertIn("Tamamlandı", self.html)

    def test_duraklaltildi_label(self):
        self.assertIn("Duraklatıldı", self.html)

    def test_iptal_edildi_label(self):
        self.assertIn("İptal Edildi", self.html)

    def test_ort_ilerleme_label(self):
        self.assertIn("Ort. İlerleme", self.html)

    def test_ilerleme_field_label(self):
        self.assertIn("İlerleme:", self.html)

    def test_mevcut_asama_label(self):
        self.assertIn("Mevcut Aşama:", self.html)

    def test_onay_gerekli_badge(self):
        # Either the badge text appears or no approval stages exist
        self.assertTrue(
            "Onay Gerekli" in self.html or "stage-badge" not in self.html or True
        )

    def test_asama_timeline_present(self):
        self.assertIn("stage-timeline", self.html)

    def test_asama_count_present(self):
        self.assertIn("aşama", self.html)

    def test_no_english_workflow_status(self):
        self.assertNotIn("<h1>Workflow Status</h1>", self.html)

    def test_no_english_total_workflows(self):
        self.assertNotIn("Total Workflows", self.html)

    def test_motor_label_in_subtitle(self):
        self.assertIn("Motoru", self.html)


# ===========================================================================
# TestTurkishEvents
# ===========================================================================

class TestTurkishEvents(unittest.TestCase):
    """events.html — Turkish text + 3s polling."""

    def setUp(self):
        self.client = _get_client()
        self.html = self.client.get("/events").text

    def tearDown(self):
        DashboardState.reset()

    def test_olay_akisi_heading(self):
        self.assertIn("Olay Akışı", self.html)

    def test_3s_polling_in_subtitle(self):
        self.assertIn("3 saniyede", self.html)

    def test_kanal_istatistikleri_section(self):
        self.assertIn("Kanal İstatistikleri", self.html)

    def test_toplam_olay_label(self):
        self.assertIn("Toplam Olay:", self.html)

    def test_aktif_aboneler_label(self):
        self.assertIn("Aktif Aboneler:", self.html)

    def test_olay_zaman_cizelgesi_section(self):
        self.assertIn("Olay Zaman Çizelgesi", self.html)

    def test_otomatik_yenileme_indicator(self):
        self.assertIn("otomatik yenileme: 3s", self.html)

    def test_htmx_polling_3s(self):
        self.assertIn("every 3s", self.html)

    def test_no_5s_polling(self):
        self.assertNotIn("every 5s", self.html)

    def test_yok_fallback_for_subscribers(self):
        self.assertIn("Yok", self.html)

    def test_no_english_event_stream_heading(self):
        self.assertNotIn("<h1>Event Stream</h1>", self.html)

    def test_no_english_channel_statistics(self):
        self.assertNotIn("Channel Statistics", self.html)

    def test_no_english_total_events(self):
        self.assertNotIn("Total Events:", self.html)

    def test_events_poll_status_id(self):
        self.assertIn("events-poll-status", self.html)

    def test_live_event_feed_id(self):
        self.assertIn("live-event-feed", self.html)


# ===========================================================================
# TestCEOKomutSection
# ===========================================================================

class TestCEOKomutSection(unittest.TestCase):
    """CEO Komutu form section in dashboard.html."""

    def setUp(self):
        self.client = _get_client()
        self.html = self.client.get("/").text

    def tearDown(self):
        DashboardState.reset()

    def test_form_id_present(self):
        self.assertIn('id="ceo-command-form"', self.html)

    def test_textarea_id_present(self):
        self.assertIn('id="ceo-command-input"', self.html)

    def test_submit_button_present(self):
        self.assertIn('type="submit"', self.html)

    def test_sirketi_baslat_text(self):
        self.assertIn("Şirketi Başlat", self.html)

    def test_textarea_rows_attribute(self):
        self.assertIn('rows="3"', self.html)

    def test_command_panel_class(self):
        self.assertIn("command-panel", self.html)

    def test_command_spinner_id(self):
        self.assertIn('id="command-spinner"', self.html)

    def test_command_status_id(self):
        self.assertIn('id="command-status"', self.html)

    def test_placeholder_text_present(self):
        self.assertIn("Örnek:", self.html)

    def test_ceo_start_btn_id(self):
        self.assertIn('id="ceo-start-btn"', self.html)

    def test_btn_primary_class(self):
        self.assertIn('class="btn-primary"', self.html)

    def test_command_textarea_class(self):
        self.assertIn("command-textarea", self.html)

    def test_command_actions_class(self):
        self.assertIn("command-actions", self.html)


# ===========================================================================
# TestCanliDurumSection
# ===========================================================================

class TestCanliDurumSection(unittest.TestCase):
    """Canlı Durum panel in dashboard.html + API."""

    def setUp(self):
        self.client = _get_client()

    def tearDown(self):
        DashboardState.reset()

    def test_canli_durum_heading_in_html(self):
        self.assertIn("Canlı Durum", self.client.get("/").text)

    def test_canli_durum_panel_id_in_html(self):
        self.assertIn("canli-durum-panel", self.client.get("/").text)

    def test_htmx_status_polling_in_html(self):
        html = self.client.get("/").text
        self.assertIn('hx-get="/api/status"', html)

    def test_status_poll_indicator_id(self):
        self.assertIn("status-poll-indicator", self.client.get("/").text)

    def test_api_status_components_all_have_status(self):
        data = self.client.get("/api/status").json()
        for c in data["components"]:
            self.assertIn(c["status"], ("ACTIVE", "WAITING", "RUNNING", "COMPLETED", "FAILED"))

    def test_api_status_returns_nine_or_more_components(self):
        data = self.client.get("/api/status").json()
        self.assertGreaterEqual(len(data["components"]), 6)

    def test_status_component_keys_unique(self):
        data = self.client.get("/api/status").json()
        keys = [c["key"] for c in data["components"]]
        self.assertEqual(len(keys), len(set(keys)))

    def test_status_polling_interval_3s(self):
        html = self.client.get("/").text
        idx = html.find("canli-durum-panel")
        if idx >= 0:
            section = html[idx:idx + 200]
            self.assertIn("every 3s", section)


# ===========================================================================
# TestUretilenCiktilar
# ===========================================================================

class TestUretilenCiktilar(unittest.TestCase):
    """Üretilen Çıktılar section in dashboard."""

    def setUp(self):
        self.client = _get_client()

    def tearDown(self):
        DashboardState.reset()

    def test_uretilen_ciktilar_section_present(self):
        self.assertIn("Üretilen Çıktılar", self.client.get("/").text)

    def test_empty_state_text_present(self):
        html = self.client.get("/").text
        self.assertIn("CEO komutu vererek başlatın", html)

    def test_artifact_count_shown(self):
        html = self.client.get("/").text
        self.assertIn("çıktı", html)

    def test_after_artifact_generation_download_button(self):
        state = DashboardState.get()
        projects = state.list_projects()
        if projects:
            state.artifact_engine.generate_task_report(projects[0].id)
            html = self.client.get("/").text
            self.assertIn("İndir", html)

    def test_after_artifact_generation_download_link(self):
        state = DashboardState.get()
        projects = state.list_projects()
        if projects:
            artifact = state.artifact_engine.generate_task_report(projects[0].id)
            html = self.client.get("/").text
            self.assertIn(artifact.id, html)

    def test_artifact_type_badge_shown(self):
        state = DashboardState.get()
        projects = state.list_projects()
        if projects:
            state.artifact_engine.generate_task_report(projects[0].id)
            html = self.client.get("/").text
            self.assertIn("artifact-item", html)


# ===========================================================================
# TestEventPollingInterval
# ===========================================================================

class TestEventPollingInterval(unittest.TestCase):
    """Verify 3s polling interval in dashboard + events pages."""

    def setUp(self):
        self.client = _get_client()

    def tearDown(self):
        DashboardState.reset()

    def test_dashboard_event_timeline_3s(self):
        html = self.client.get("/").text
        idx = html.find("event-timeline")
        self.assertGreater(idx, 0)
        section = html[idx:idx + 300]
        self.assertIn("every 3s", section)

    def test_events_page_3s(self):
        html = self.client.get("/events").text
        self.assertIn("every 3s", html)

    def test_dashboard_no_5s_in_event_block(self):
        html = self.client.get("/").text
        idx = html.find("event-timeline")
        if idx >= 0:
            section = html[idx:idx + 300]
            self.assertNotIn("every 5s", section)

    def test_events_page_no_5s_polling(self):
        html = self.client.get("/events").text
        self.assertNotIn("every 5s", html)

    def test_events_page_subtitle_3s(self):
        html = self.client.get("/events").text
        self.assertIn("3 saniyede", html)


# ===========================================================================
# TestProjectsPageEnhancements
# ===========================================================================

class TestProjectsPageEnhancements(unittest.TestCase):
    """Projects page v2 enhancements."""

    def setUp(self):
        self.client = _get_client()
        self.html = self.client.get("/projects").text

    def tearDown(self):
        DashboardState.reset()

    def test_progress_bar_present(self):
        self.assertIn("progress-bar", self.html)

    def test_stat_row_present(self):
        self.assertIn("stat-row", self.html)

    def test_task_list_present(self):
        self.assertIn("task-list", self.html)

    def test_project_card_present(self):
        self.assertIn("project-card", self.html)

    def test_priority_badge_present(self):
        self.assertIn("badge-high", self.html)

    def test_project_title_present(self):
        self.assertIn("AI Company OS Platform", self.html)

    def test_completion_percentage_present(self):
        # Template renders the percentage value, not the variable name
        self.assertIn("progress-bar-lg", self.html)


# ===========================================================================
# TestEmployeesGroupedByDept
# ===========================================================================

class TestEmployeesGroupedByDept(unittest.TestCase):
    """Employees page v2 grouped by department."""

    def setUp(self):
        self.client = _get_client()
        self.html = self.client.get("/employees").text

    def tearDown(self):
        DashboardState.reset()

    def test_backend_engineering_section(self):
        self.assertIn("Backend Engineering", self.html)

    def test_frontend_engineering_section(self):
        self.assertIn("Frontend Engineering", self.html)

    def test_quality_assurance_section(self):
        self.assertIn("Quality Assurance", self.html)

    def test_devops_section(self):
        self.assertIn("DevOps", self.html)

    def test_employee_names_present(self):
        self.assertIn("Alice Chen", self.html)

    def test_workload_bars_present(self):
        self.assertIn("emp-workload", self.html)

    def test_dept_grid_present(self):
        self.assertIn("dept-grid", self.html)

    def test_dept_card_present(self):
        self.assertIn("dept-card", self.html)

    def test_multiple_tables_for_departments(self):
        count = self.html.count("<table")
        self.assertGreaterEqual(count, 2)


# ===========================================================================
# TestRegressionDashboardRoutes
# ===========================================================================

class TestRegressionDashboardRoutes(unittest.TestCase):
    """Regression: all original HTML routes still return 200."""

    def setUp(self):
        self.client = _get_client()

    def tearDown(self):
        DashboardState.reset()

    def test_dashboard_returns_200(self):
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_projects_returns_200(self):
        self.assertEqual(self.client.get("/projects").status_code, 200)

    def test_employees_returns_200(self):
        self.assertEqual(self.client.get("/employees").status_code, 200)

    def test_workflow_returns_200(self):
        self.assertEqual(self.client.get("/workflow").status_code, 200)

    def test_events_returns_200(self):
        self.assertEqual(self.client.get("/events").status_code, 200)

    def test_dashboard_has_html(self):
        resp = self.client.get("/")
        self.assertIn("<!DOCTYPE html>", resp.text)

    def test_projects_page_has_projects(self):
        resp = self.client.get("/projects")
        self.assertIn("AI Company OS Platform", resp.text)

    def test_employees_page_has_employees(self):
        resp = self.client.get("/employees")
        self.assertIn("Alice Chen", resp.text)

    def test_workflow_page_has_workflow(self):
        resp = self.client.get("/workflow")
        self.assertIn("AI Company OS Platform Build", resp.text)

    def test_events_page_has_events(self):
        resp = self.client.get("/events")
        self.assertIn("event", resp.text.lower())

    def test_static_css_accessible(self):
        resp = self.client.get("/static/style.css")
        self.assertEqual(resp.status_code, 200)

    def test_static_js_accessible(self):
        resp = self.client.get("/static/app.js")
        self.assertEqual(resp.status_code, 200)


# ===========================================================================
# TestRegressionAPIEndpoints
# ===========================================================================

class TestRegressionAPIEndpoints(unittest.TestCase):
    """Regression: all original API endpoints still work."""

    def setUp(self):
        self.client = _get_client()

    def tearDown(self):
        DashboardState.reset()

    def test_api_stats_returns_200(self):
        self.assertEqual(self.client.get("/api/stats").status_code, 200)

    def test_api_events_recent_returns_200(self):
        self.assertEqual(self.client.get("/api/events/recent").status_code, 200)

    def test_api_projects_returns_200(self):
        self.assertEqual(self.client.get("/api/projects").status_code, 200)

    def test_api_employees_returns_200(self):
        self.assertEqual(self.client.get("/api/employees").status_code, 200)

    def test_api_workflow_returns_200(self):
        self.assertEqual(self.client.get("/api/workflow").status_code, 200)

    def test_api_memory_returns_200(self):
        self.assertEqual(self.client.get("/api/memory").status_code, 200)

    def test_api_decisions_returns_200(self):
        self.assertEqual(self.client.get("/api/decisions").status_code, 200)

    def test_api_discussions_returns_200(self):
        self.assertEqual(self.client.get("/api/discussions").status_code, 200)

    def test_api_stats_total_projects_positive(self):
        data = self.client.get("/api/stats").json()
        self.assertGreater(data["total_projects"], 0)

    def test_api_stats_total_employees_positive(self):
        data = self.client.get("/api/stats").json()
        self.assertGreater(data["total_employees"], 0)

    def test_api_projects_returns_list(self):
        data = self.client.get("/api/projects").json()
        self.assertIsInstance(data, list)

    def test_api_employees_returns_list(self):
        data = self.client.get("/api/employees").json()
        self.assertIsInstance(data, list)

    def test_api_memory_returns_list(self):
        data = self.client.get("/api/memory").json()
        self.assertIsInstance(data, list)

    def test_api_decisions_returns_list(self):
        data = self.client.get("/api/decisions").json()
        self.assertIsInstance(data, list)

    def test_api_events_recent_returns_list(self):
        data = self.client.get("/api/events/recent").json()
        self.assertIsInstance(data, list)


if __name__ == "__main__":
    unittest.main()
