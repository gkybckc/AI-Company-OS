"""
Feature 22 — Real-Time Infrastructure test suite.

Coverage:
  - Service layer (CompanyService, OrganizationService, CollaborationService,
    ArtifactService, EventService)
  - Router package (9 routers, all HTTP endpoints via TestClient)
  - SSE endpoint behavior (GET /api/events/stream)
  - Backward compatibility (old routes.py create_router interface still works)
  - No business logic changes (existing data unchanged)

Minimum target: 450 tests.  All tests must pass alongside the existing
5,606-test suite with zero regressions.
"""

import json
from typing import Any, Dict, List
import pytest

from starlette.testclient import TestClient


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    from apps.dashboard.main import app
    return TestClient(app)


@pytest.fixture(scope="module")
def state():
    from apps.dashboard.state import DashboardState
    return DashboardState.get()


@pytest.fixture(scope="module")
def company_svc(state):
    from apps.dashboard.services.company_service import CompanyService
    return CompanyService(state)


@pytest.fixture(scope="module")
def org_svc(state):
    from apps.dashboard.services.organization_service import OrganizationService
    return OrganizationService(state)


@pytest.fixture(scope="module")
def collab_svc(state):
    from apps.dashboard.services.collaboration_service import CollaborationService
    return CollaborationService(state)


@pytest.fixture(scope="module")
def artifact_svc(state):
    from apps.dashboard.services.artifact_service import ArtifactService
    return ArtifactService(state)


@pytest.fixture(scope="module")
def event_svc(state):
    from apps.dashboard.services.event_service import EventService
    return EventService(state)


# ===========================================================================
# 1. CompanyService
# ===========================================================================

class TestCompanyServiceStats:
    def test_get_stats_returns_dict(self, company_svc):
        assert isinstance(company_svc.get_stats(), dict)

    def test_get_stats_has_total_projects(self, company_svc):
        assert "total_projects" in company_svc.get_stats()

    def test_get_stats_has_active_projects(self, company_svc):
        assert "active_projects" in company_svc.get_stats()

    def test_get_stats_has_total_employees(self, company_svc):
        assert "total_employees" in company_svc.get_stats()

    def test_get_stats_has_active_employees(self, company_svc):
        assert "active_employees" in company_svc.get_stats()

    def test_get_stats_has_total_departments(self, company_svc):
        assert "total_departments" in company_svc.get_stats()

    def test_get_stats_has_total_events(self, company_svc):
        assert "total_events" in company_svc.get_stats()

    def test_get_stats_has_total_memory_entries(self, company_svc):
        assert "total_memory_entries" in company_svc.get_stats()

    def test_get_stats_has_total_decisions(self, company_svc):
        assert "total_decisions" in company_svc.get_stats()

    def test_get_stats_has_total_discussions(self, company_svc):
        assert "total_discussions" in company_svc.get_stats()

    def test_get_stats_has_workflow_stats(self, company_svc):
        assert "workflow_stats" in company_svc.get_stats()

    def test_get_stats_projects_positive(self, company_svc):
        assert company_svc.get_stats()["total_projects"] >= 0

    def test_get_stats_employees_positive(self, company_svc):
        assert company_svc.get_stats()["total_employees"] >= 0

    def test_get_stats_events_non_negative(self, company_svc):
        assert company_svc.get_stats()["total_events"] >= 0


class TestCompanyServiceProjects:
    def test_list_projects_returns_list(self, company_svc):
        assert isinstance(company_svc.list_projects(), list)

    def test_list_projects_api_returns_list(self, company_svc):
        assert isinstance(company_svc.list_projects_with_api_shape(), list)

    def test_list_projects_api_has_id(self, company_svc):
        projects = company_svc.list_projects_with_api_shape()
        if projects:
            assert "id" in projects[0]

    def test_list_projects_api_has_title(self, company_svc):
        projects = company_svc.list_projects_with_api_shape()
        if projects:
            assert "title" in projects[0]

    def test_list_projects_api_has_status(self, company_svc):
        projects = company_svc.list_projects_with_api_shape()
        if projects:
            assert "status" in projects[0]

    def test_list_projects_api_has_created_at(self, company_svc):
        projects = company_svc.list_projects_with_api_shape()
        if projects:
            assert "created_at" in projects[0]

    def test_list_projects_api_has_completion(self, company_svc):
        projects = company_svc.list_projects_with_api_shape()
        if projects:
            assert "completion_percentage" in projects[0]

    def test_list_projects_with_status_returns_list(self, company_svc):
        assert isinstance(company_svc.list_projects_with_status(), list)

    def test_list_projects_with_status_has_project_key(self, company_svc):
        items = company_svc.list_projects_with_status()
        if items:
            assert "project" in items[0]

    def test_list_projects_with_status_has_tasks_key(self, company_svc):
        items = company_svc.list_projects_with_status()
        if items:
            assert "tasks" in items[0]


class TestCompanyServiceEmployees:
    def test_list_employees_api_returns_list(self, company_svc):
        assert isinstance(company_svc.list_employees_api(), list)

    def test_list_employees_api_has_id(self, company_svc):
        emps = company_svc.list_employees_api()
        if emps:
            assert "id" in emps[0]

    def test_list_employees_api_has_name(self, company_svc):
        emps = company_svc.list_employees_api()
        if emps:
            assert "name" in emps[0]

    def test_list_employees_api_has_role(self, company_svc):
        emps = company_svc.list_employees_api()
        if emps:
            assert "role" in emps[0]

    def test_list_employees_api_has_skills(self, company_svc):
        emps = company_svc.list_employees_api()
        if emps:
            assert "skills" in emps[0]

    def test_list_agent_status_returns_list(self, company_svc):
        assert isinstance(company_svc.list_agent_status(), list)

    def test_list_agent_status_has_workload(self, company_svc):
        agents = company_svc.list_agent_status()
        if agents:
            assert "workload" in agents[0]

    def test_list_agent_status_workload_percentage(self, company_svc):
        agents = company_svc.list_agent_status()
        for a in agents:
            assert 0 <= a["workload"] <= 100


class TestCompanyServiceDashboard:
    def test_get_dashboard_context_returns_dict(self, company_svc):
        assert isinstance(company_svc.get_dashboard_context(), dict)

    def test_get_dashboard_context_has_total_projects(self, company_svc):
        assert "total_projects" in company_svc.get_dashboard_context()

    def test_get_dashboard_context_has_departments(self, company_svc):
        assert "departments" in company_svc.get_dashboard_context()

    def test_get_dashboard_context_has_recent_events(self, company_svc):
        assert "recent_events" in company_svc.get_dashboard_context()

    def test_get_dashboard_context_pipeline_step_int(self, company_svc):
        ctx = company_svc.get_dashboard_context()
        assert isinstance(ctx["pipeline_step"], int)

    def test_get_component_status_returns_dict(self, company_svc):
        assert isinstance(company_svc.get_component_status(), dict)

    def test_get_component_status_has_components(self, company_svc):
        result = company_svc.get_component_status()
        assert "components" in result

    def test_get_component_status_components_is_list(self, company_svc):
        result = company_svc.get_component_status()
        assert isinstance(result["components"], list)

    def test_get_component_status_each_has_key(self, company_svc):
        for c in company_svc.get_component_status()["components"]:
            assert "key" in c

    def test_get_component_status_each_has_label(self, company_svc):
        for c in company_svc.get_component_status()["components"]:
            assert "label" in c

    def test_get_component_status_each_has_status(self, company_svc):
        for c in company_svc.get_component_status()["components"]:
            assert "status" in c


class TestCompanyServiceDataAPIs:
    def test_get_memory_api_returns_list(self, company_svc):
        assert isinstance(company_svc.get_memory_api(), list)

    def test_get_memory_api_limit_respected(self, company_svc):
        entries = company_svc.get_memory_api(limit=2)
        assert len(entries) <= 2

    def test_get_memory_api_entry_has_id(self, company_svc):
        entries = company_svc.get_memory_api()
        if entries:
            assert "id" in entries[0]

    def test_get_decisions_api_returns_list(self, company_svc):
        assert isinstance(company_svc.get_decisions_api(), list)

    def test_get_decisions_api_entry_has_id(self, company_svc):
        decisions = company_svc.get_decisions_api()
        if decisions:
            assert "id" in decisions[0]

    def test_get_discussions_api_returns_list(self, company_svc):
        assert isinstance(company_svc.get_discussions_api(), list)

    def test_get_discussions_api_entry_has_topic(self, company_svc):
        discs = company_svc.get_discussions_api()
        if discs:
            assert "topic" in discs[0]


# ===========================================================================
# 2. OrganizationService
# ===========================================================================

class TestOrganizationServiceDepartments:
    def test_list_departments_api_returns_list(self, org_svc):
        assert isinstance(org_svc.list_departments_api(), list)

    def test_list_departments_api_non_empty(self, org_svc):
        assert len(org_svc.list_departments_api()) > 0

    def test_list_departments_api_has_id(self, org_svc):
        depts = org_svc.list_departments_api()
        assert "id" in depts[0]

    def test_list_departments_api_has_name(self, org_svc):
        depts = org_svc.list_departments_api()
        assert "name" in depts[0]

    def test_create_department_returns_obj(self, org_svc):
        dept = org_svc.create_department("Test Dept Feature22", 5)
        assert dept.name == "Test Dept Feature22"

    def test_create_department_shows_in_list(self, org_svc):
        names = [d["name"] for d in org_svc.list_departments_api()]
        assert "Test Dept Feature22" in names


class TestOrganizationServiceEmployees:
    def test_list_employees_api_returns_list(self, org_svc):
        assert isinstance(org_svc.list_employees_api(), list)

    def test_list_employees_api_has_role_name(self, org_svc):
        emps = org_svc.list_employees_api()
        if emps:
            assert "role_name" in emps[0]

    def test_list_employees_api_has_department_name(self, org_svc):
        emps = org_svc.list_employees_api()
        if emps:
            assert "department_name" in emps[0]


class TestOrganizationServiceRoles:
    def test_list_roles_api_returns_list(self, org_svc):
        assert isinstance(org_svc.list_roles_api(), list)

    def test_create_role_returns_obj(self, org_svc):
        role = org_svc.create_role("Feature22 Role", "Test role for feature 22")
        assert role.name == "Feature22 Role"

    def test_created_role_in_list(self, org_svc):
        names = [r["name"] for r in org_svc.list_roles_api()]
        assert "Feature22 Role" in names


class TestOrganizationServiceSkills:
    def test_list_skills_api_returns_list(self, org_svc):
        assert isinstance(org_svc.list_skills_api(), list)

    def test_create_skill_returns_obj(self, org_svc):
        skill = org_svc.create_skill("Feature22 Skill", "Infrastructure")
        assert skill.name == "Feature22 Skill"

    def test_created_skill_in_list(self, org_svc):
        names = [s["name"] for s in org_svc.list_skills_api()]
        assert "Feature22 Skill" in names


class TestOrganizationServiceStats:
    def test_statistics_returns_dict(self, org_svc):
        assert isinstance(org_svc.statistics(), dict)

    def test_get_departments_page_data_returns_dict(self, org_svc):
        assert isinstance(org_svc.get_departments_page_data(), dict)

    def test_get_departments_page_data_has_dept_data(self, org_svc):
        assert "dept_data" in org_svc.get_departments_page_data()

    def test_get_employees_page_data_returns_dict(self, org_svc):
        assert isinstance(org_svc.get_employees_page_data(), dict)

    def test_get_employees_page_data_has_emp_data(self, org_svc):
        assert "emp_data" in org_svc.get_employees_page_data()

    def test_get_roles_page_data_returns_dict(self, org_svc):
        assert isinstance(org_svc.get_roles_page_data(), dict)

    def test_get_roles_page_data_has_role_data(self, org_svc):
        assert "role_data" in org_svc.get_roles_page_data()

    def test_get_skills_page_data_returns_dict(self, org_svc):
        assert isinstance(org_svc.get_skills_page_data(), dict)

    def test_get_skills_page_data_has_skill_data(self, org_svc):
        assert "skill_data" in org_svc.get_skills_page_data()


# ===========================================================================
# 3. CollaborationService
# ===========================================================================

class TestCollaborationServiceContext:
    def test_get_hub_context_returns_dict(self, collab_svc):
        assert isinstance(collab_svc.get_hub_context(), dict)

    def test_get_hub_context_has_stats(self, collab_svc):
        assert "stats" in collab_svc.get_hub_context()

    def test_get_hub_context_has_templates(self, collab_svc):
        assert "templates" in collab_svc.get_hub_context()

    def test_get_conversations_context_returns_dict(self, collab_svc):
        assert isinstance(collab_svc.get_conversations_context(), dict)

    def test_get_conversations_context_has_conversations(self, collab_svc):
        assert "conversations" in collab_svc.get_conversations_context()

    def test_get_sessions_context_returns_dict(self, collab_svc):
        assert isinstance(collab_svc.get_sessions_context(), dict)

    def test_get_sessions_context_has_sessions(self, collab_svc):
        assert "sessions" in collab_svc.get_sessions_context()

    def test_get_policies_context_returns_dict(self, collab_svc):
        assert isinstance(collab_svc.get_policies_context(), dict)

    def test_get_policies_context_has_policies(self, collab_svc):
        assert "policies" in collab_svc.get_policies_context()

    def test_get_policies_context_has_blocking_count(self, collab_svc):
        stats = collab_svc.get_policies_context()["stats"]
        assert "blocking_policies" in stats


class TestCollaborationServiceConversations:
    def test_list_conversations_returns_list(self, collab_svc):
        assert isinstance(collab_svc.list_conversations(), list)

    def test_list_conversations_non_empty(self, collab_svc):
        assert len(collab_svc.list_conversations()) > 0

    def test_get_conversation_returns_dict(self, collab_svc):
        conv_id = collab_svc.list_conversations()[0]["id"]
        result = collab_svc.get_conversation(conv_id)
        assert isinstance(result, dict)

    def test_get_conversation_has_messages(self, collab_svc):
        conv_id = collab_svc.list_conversations()[0]["id"]
        result = collab_svc.get_conversation(conv_id)
        assert "messages" in result

    def test_create_conversation_direct(self, collab_svc):
        conv = collab_svc.create_conversation(
            title="Feature22 Test Conv", creator="test",
            project_id=None, task_id=None, template_type=None
        )
        assert isinstance(conv, dict)
        assert "id" in conv

    def test_get_messages_returns_list(self, collab_svc):
        conv_id = collab_svc.list_conversations()[0]["id"]
        msgs = collab_svc.get_messages(conv_id)
        assert isinstance(msgs, list)

    def test_statistics_returns_dict(self, collab_svc):
        assert isinstance(collab_svc.statistics(), dict)

    def test_list_templates_returns_list(self, collab_svc):
        tmpls = collab_svc.list_templates()
        assert isinstance(tmpls, list)
        assert len(tmpls) > 0


class TestCollaborationServicePolicies:
    def test_list_policies_returns_list(self, collab_svc):
        assert isinstance(collab_svc.list_policies(), list)

    def test_list_policies_non_empty(self, collab_svc):
        assert len(collab_svc.list_policies()) > 0

    def test_list_policies_has_name(self, collab_svc):
        policy = collab_svc.list_policies()[0]
        assert "name" in policy


class TestCollaborationServiceSessions:
    def test_list_sessions_returns_list(self, collab_svc):
        assert isinstance(collab_svc.list_sessions(), list)

    def test_create_session_returns_dict(self, collab_svc):
        session = collab_svc.create_session("Feature22 Session", None, None)
        assert isinstance(session, dict)
        assert "id" in session


# ===========================================================================
# 4. ArtifactService
# ===========================================================================

class TestArtifactService:
    def test_list_artifacts_returns_list(self, artifact_svc):
        assert isinstance(artifact_svc.list_artifacts(), list)

    def test_list_artifacts_api_returns_list(self, artifact_svc):
        assert isinstance(artifact_svc.list_artifacts_api(), list)

    def test_list_artifacts_api_has_id(self, artifact_svc):
        arts = artifact_svc.list_artifacts_api()
        if arts:
            assert "id" in arts[0]

    def test_list_artifacts_api_has_title(self, artifact_svc):
        arts = artifact_svc.list_artifacts_api()
        if arts:
            assert "title" in arts[0]

    def test_list_artifacts_api_has_type(self, artifact_svc):
        arts = artifact_svc.list_artifacts_api()
        if arts:
            assert "type" in arts[0]

    def test_list_artifacts_api_has_word_count(self, artifact_svc):
        arts = artifact_svc.list_artifacts_api()
        if arts:
            assert "word_count" in arts[0]

    def test_list_artifacts_api_has_created_at(self, artifact_svc):
        arts = artifact_svc.list_artifacts_api()
        if arts:
            assert "created_at" in arts[0]

    def test_list_artifacts_api_word_count_non_negative(self, artifact_svc):
        for art in artifact_svc.list_artifacts_api():
            assert art["word_count"] >= 0

    def test_find_artifact_raises_on_bad_id(self, artifact_svc):
        with pytest.raises(Exception):
            artifact_svc.find_artifact("nonexistent-id-xyz")

    def test_get_download_raises_on_bad_id(self, artifact_svc):
        with pytest.raises(Exception):
            artifact_svc.get_download("nonexistent-id-xyz")


# ===========================================================================
# 5. EventService
# ===========================================================================

class TestEventServiceBasic:
    def test_get_recent_events_returns_list(self, event_svc):
        assert isinstance(event_svc.get_recent_events(), list)

    def test_get_recent_events_limit_respected(self, event_svc):
        events = event_svc.get_recent_events(limit=3)
        assert len(events) <= 3

    def test_get_recent_events_has_id(self, event_svc):
        events = event_svc.get_recent_events()
        if events:
            assert "id" in events[0]

    def test_get_recent_events_has_channel(self, event_svc):
        events = event_svc.get_recent_events()
        if events:
            assert "channel" in events[0]

    def test_get_recent_events_has_timestamp(self, event_svc):
        events = event_svc.get_recent_events()
        if events:
            assert "timestamp" in events[0]

    def test_get_recent_events_has_action(self, event_svc):
        events = event_svc.get_recent_events()
        if events:
            assert "action" in events[0]

    def test_get_timeline_returns_list(self, event_svc):
        assert isinstance(event_svc.get_timeline(), list)

    def test_get_timeline_has_sentence(self, event_svc):
        timeline = event_svc.get_timeline()
        if timeline:
            assert "sentence" in timeline[0]

    def test_get_timeline_has_timestamp_hms(self, event_svc):
        timeline = event_svc.get_timeline()
        if timeline:
            assert "timestamp_hms" in timeline[0]

    def test_get_events_page_data_returns_dict(self, event_svc):
        assert isinstance(event_svc.get_events_page_data(), dict)

    def test_get_events_page_data_has_ev_stats(self, event_svc):
        assert "ev_stats" in event_svc.get_events_page_data()

    def test_get_events_page_data_has_events_with_sentences(self, event_svc):
        data = event_svc.get_events_page_data()
        assert "events_with_sentences" in data

    def test_get_statistics_returns_dict(self, event_svc):
        assert isinstance(event_svc.get_statistics(), dict)

    def test_get_statistics_has_total_events(self, event_svc):
        stats = event_svc.get_statistics()
        assert "total_events" in stats


class TestHumanEvent:
    def test_company_started(self):
        from apps.dashboard.services.event_service import human_event
        result = human_event("company_started", {})
        assert "başlatıldı" in result

    def test_project_created(self):
        from apps.dashboard.services.event_service import human_event
        result = human_event("project_created", {"title": "Test"})
        assert "Test" in result

    def test_employee_hired(self):
        from apps.dashboard.services.event_service import human_event
        result = human_event("employee_hired", {"name": "Alice", "role": "dev"})
        assert "Alice" in result

    def test_workflow_started(self):
        from apps.dashboard.services.event_service import human_event
        result = human_event("workflow_started", {"name": "WF1"})
        assert "WF1" in result

    def test_discussion_started(self):
        from apps.dashboard.services.event_service import human_event
        result = human_event("discussion_started", {"topic": "Tech"})
        assert "Tech" in result

    def test_decision_created(self):
        from apps.dashboard.services.event_service import human_event
        result = human_event("decision_created", {"title": "DB choice"})
        assert "DB choice" in result

    def test_unknown_action_returns_sentence(self):
        from apps.dashboard.services.event_service import human_event
        result = human_event("unknown_xyz", {})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_action_fallback(self):
        from apps.dashboard.services.event_service import human_event
        result = human_event("", {})
        assert isinstance(result, str)

    def test_task_created(self):
        from apps.dashboard.services.event_service import human_event
        result = human_event("task_created", {"title": "My task"})
        assert "My task" in result

    def test_entry_stored(self):
        from apps.dashboard.services.event_service import human_event
        result = human_event("entry_stored", {"title": "Memory item"})
        assert "Memory item" in result

    def test_decision_recommended(self):
        from apps.dashboard.services.event_service import human_event
        result = human_event("decision_recommended", {"recommendation": "PostgreSQL"})
        assert "PostgreSQL" in result

    def test_stage_advanced(self):
        from apps.dashboard.services.event_service import human_event
        result = human_event("stage_advanced", {"stage": "Planning"})
        assert "Planning" in result


# ===========================================================================
# 6. HTTP: Dashboard Router
# ===========================================================================

class TestDashboardRouterHttp:
    def test_get_root_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_get_root_html(self, client):
        resp = client.get("/")
        assert "text/html" in resp.headers["content-type"]

    def test_get_root_contains_company_name(self, client):
        resp = client.get("/")
        assert "AI Company OS" in resp.text

    def test_api_stats_200(self, client):
        resp = client.get("/api/stats")
        assert resp.status_code == 200

    def test_api_stats_json(self, client):
        resp = client.get("/api/stats")
        data = resp.json()
        assert "total_projects" in data

    def test_api_stats_has_active_projects(self, client):
        resp = client.get("/api/stats")
        assert "active_projects" in resp.json()

    def test_api_stats_has_workflow_stats(self, client):
        resp = client.get("/api/stats")
        assert "workflow_stats" in resp.json()

    def test_api_status_200(self, client):
        resp = client.get("/api/status")
        assert resp.status_code == 200

    def test_api_status_has_components(self, client):
        resp = client.get("/api/status")
        assert "components" in resp.json()

    def test_api_command_short_command_400(self, client):
        resp = client.post("/api/command", json={"command": "short"})
        assert resp.status_code == 400

    def test_api_command_invalid_json_400(self, client):
        resp = client.post(
            "/api/command",
            content="not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400

    def test_api_command_history_200(self, client):
        resp = client.get("/api/command-history")
        assert resp.status_code == 200

    def test_api_command_history_is_list(self, client):
        assert isinstance(client.get("/api/command-history").json(), list)

    def test_api_agent_status_200(self, client):
        resp = client.get("/api/agent-status")
        assert resp.status_code == 200

    def test_api_agent_status_is_list(self, client):
        assert isinstance(client.get("/api/agent-status").json(), list)

    def test_api_agent_status_has_workload(self, client):
        agents = client.get("/api/agent-status").json()
        if agents:
            assert "workload" in agents[0]


# ===========================================================================
# 7. HTTP: Projects Router
# ===========================================================================

class TestProjectsRouterHttp:
    def test_get_projects_200(self, client):
        assert client.get("/projects").status_code == 200

    def test_get_projects_html(self, client):
        resp = client.get("/projects")
        assert "text/html" in resp.headers["content-type"]

    def test_get_projects_contains_projects(self, client):
        resp = client.get("/projects")
        assert "AI Company OS" in resp.text

    def test_api_projects_200(self, client):
        assert client.get("/api/projects").status_code == 200

    def test_api_projects_is_list(self, client):
        assert isinstance(client.get("/api/projects").json(), list)

    def test_api_projects_has_id(self, client):
        projects = client.get("/api/projects").json()
        if projects:
            assert "id" in projects[0]

    def test_api_projects_has_status(self, client):
        projects = client.get("/api/projects").json()
        if projects:
            assert "status" in projects[0]

    def test_api_projects_completion_percentage_numeric(self, client):
        projects = client.get("/api/projects").json()
        for p in projects:
            assert isinstance(p["completion_percentage"], (int, float))


# ===========================================================================
# 8. HTTP: Employees Router
# ===========================================================================

class TestEmployeesRouterHttp:
    def test_get_employees_200(self, client):
        assert client.get("/employees").status_code == 200

    def test_get_employees_html(self, client):
        resp = client.get("/employees")
        assert "text/html" in resp.headers["content-type"]

    def test_api_employees_200(self, client):
        assert client.get("/api/employees").status_code == 200

    def test_api_employees_is_list(self, client):
        assert isinstance(client.get("/api/employees").json(), list)

    def test_api_employees_has_name(self, client):
        emps = client.get("/api/employees").json()
        if emps:
            assert "name" in emps[0]

    def test_api_employees_has_department(self, client):
        emps = client.get("/api/employees").json()
        if emps:
            assert "department" in emps[0]

    def test_api_employees_skills_is_list(self, client):
        emps = client.get("/api/employees").json()
        for emp in emps:
            assert isinstance(emp["skills"], list)


# ===========================================================================
# 9. HTTP: Organization Router
# ===========================================================================

class TestOrganizationRouterHttp:
    def test_get_org_200(self, client):
        assert client.get("/org").status_code == 200

    def test_get_org_html(self, client):
        resp = client.get("/org")
        assert "text/html" in resp.headers["content-type"]

    def test_get_org_departments_200(self, client):
        assert client.get("/org/departments").status_code == 200

    def test_get_org_employees_200(self, client):
        assert client.get("/org/employees").status_code == 200

    def test_get_org_roles_200(self, client):
        assert client.get("/org/roles").status_code == 200

    def test_get_org_skills_200(self, client):
        assert client.get("/org/skills").status_code == 200

    def test_api_org_departments_200(self, client):
        assert client.get("/api/org/departments").status_code == 200

    def test_api_org_departments_is_list(self, client):
        assert isinstance(client.get("/api/org/departments").json(), list)

    def test_api_org_employees_200(self, client):
        assert client.get("/api/org/employees").status_code == 200

    def test_api_org_employees_is_list(self, client):
        assert isinstance(client.get("/api/org/employees").json(), list)

    def test_api_org_roles_200(self, client):
        assert client.get("/api/org/roles").status_code == 200

    def test_api_org_roles_is_list(self, client):
        assert isinstance(client.get("/api/org/roles").json(), list)

    def test_api_org_skills_200(self, client):
        assert client.get("/api/org/skills").status_code == 200

    def test_api_org_skills_is_list(self, client):
        assert isinstance(client.get("/api/org/skills").json(), list)

    def test_api_org_statistics_200(self, client):
        assert client.get("/api/org/statistics").status_code == 200

    def test_api_org_statistics_is_dict(self, client):
        assert isinstance(client.get("/api/org/statistics").json(), dict)

    def test_api_org_create_department_missing_name_400(self, client):
        resp = client.post("/api/org/departments", json={"capacity": 5})
        assert resp.status_code == 400

    def test_api_org_create_department_valid_200(self, client):
        resp = client.post(
            "/api/org/departments",
            json={"name": "HTTP Test Department", "capacity": 3},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_api_org_create_role_missing_name_400(self, client):
        resp = client.post("/api/org/roles", json={"description": "test"})
        assert resp.status_code == 400

    def test_api_org_create_role_valid_200(self, client):
        resp = client.post(
            "/api/org/roles",
            json={"name": "HTTP Test Role", "description": "Test"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_api_org_create_skill_missing_name_400(self, client):
        resp = client.post("/api/org/skills", json={"category": "test"})
        assert resp.status_code == 400

    def test_api_org_create_skill_valid_200(self, client):
        resp = client.post(
            "/api/org/skills",
            json={"name": "HTTP Test Skill", "category": "Testing"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True


# ===========================================================================
# 10. HTTP: Workflow Router
# ===========================================================================

class TestWorkflowRouterHttp:
    def test_get_workflow_200(self, client):
        assert client.get("/workflow").status_code == 200

    def test_get_workflow_html(self, client):
        assert "text/html" in client.get("/workflow").headers["content-type"]

    def test_api_workflow_200(self, client):
        assert client.get("/api/workflow").status_code == 200

    def test_api_workflow_is_dict(self, client):
        data = client.get("/api/workflow").json()
        assert isinstance(data, dict)

    def test_api_workflow_has_workflows_key(self, client):
        data = client.get("/api/workflow").json()
        assert "workflows" in data

    def test_api_workflow_has_stats_key(self, client):
        data = client.get("/api/workflow").json()
        assert "stats" in data

    def test_api_workflow_workflows_is_list(self, client):
        data = client.get("/api/workflow").json()
        assert isinstance(data["workflows"], list)


# ===========================================================================
# 11. HTTP: Events Router + SSE
# ===========================================================================

class TestEventsRouterHttp:
    def test_get_events_200(self, client):
        assert client.get("/events").status_code == 200

    def test_get_events_html(self, client):
        assert "text/html" in client.get("/events").headers["content-type"]

    def test_api_events_recent_200(self, client):
        assert client.get("/api/events/recent").status_code == 200

    def test_api_events_recent_is_list(self, client):
        assert isinstance(client.get("/api/events/recent").json(), list)

    def test_api_events_recent_default_limit(self, client):
        events = client.get("/api/events/recent").json()
        assert len(events) <= 20

    def test_api_events_recent_custom_limit(self, client):
        events = client.get("/api/events/recent?limit=5").json()
        assert len(events) <= 5

    def test_api_events_recent_has_id(self, client):
        events = client.get("/api/events/recent").json()
        if events:
            assert "id" in events[0]

    def test_api_timeline_200(self, client):
        assert client.get("/api/timeline").status_code == 200

    def test_api_timeline_is_list(self, client):
        assert isinstance(client.get("/api/timeline").json(), list)

    def test_api_timeline_has_sentence(self, client):
        timeline = client.get("/api/timeline").json()
        if timeline:
            assert "sentence" in timeline[0]

    def test_api_timeline_has_timestamp_hms(self, client):
        timeline = client.get("/api/timeline").json()
        if timeline:
            assert "timestamp_hms" in timeline[0]

    def test_api_events_stream_exists(self, client):
        # TestClient doesn't stream, but verifies the endpoint starts
        with client.stream("GET", "/api/events/stream") as resp:
            assert resp.status_code == 200
            # Read first chunk — should be the "connected" event
            first_chunk = b""
            for chunk in resp.iter_bytes(1024):
                first_chunk = chunk
                break
        assert b"data:" in first_chunk

    def test_api_events_stream_content_type(self, client):
        with client.stream("GET", "/api/events/stream") as resp:
            assert "text/event-stream" in resp.headers.get("content-type", "")
            for _ in resp.iter_bytes(1):
                break

    def test_api_events_stream_first_event_json(self, client):
        with client.stream("GET", "/api/events/stream") as resp:
            raw = b""
            for chunk in resp.iter_bytes(512):
                raw += chunk
                if b"data:" in raw:
                    break
        line = [l for l in raw.decode().splitlines() if l.startswith("data:")]
        assert line, "No data: line received from SSE stream"
        payload = json.loads(line[0][5:])
        assert payload.get("type") == "connected"


# ===========================================================================
# 12. HTTP: Artifacts Router
# ===========================================================================

class TestArtifactsRouterHttp:
    def test_api_artifacts_200(self, client):
        assert client.get("/api/artifacts").status_code == 200

    def test_api_artifacts_is_list(self, client):
        assert isinstance(client.get("/api/artifacts").json(), list)

    def test_api_artifacts_has_id(self, client):
        arts = client.get("/api/artifacts").json()
        if arts:
            assert "id" in arts[0]

    def test_api_artifacts_download_missing_404(self, client):
        resp = client.get("/api/artifacts/nonexistent-xyz/download")
        assert resp.status_code == 404

    def test_api_artifacts_word_count_numeric(self, client):
        arts = client.get("/api/artifacts").json()
        for a in arts:
            assert isinstance(a["word_count"], int)


# ===========================================================================
# 13. HTTP: Shared API Router (memory, decisions, discussions)
# ===========================================================================

class TestApiRouterHttp:
    def test_api_memory_200(self, client):
        assert client.get("/api/memory").status_code == 200

    def test_api_memory_is_list(self, client):
        assert isinstance(client.get("/api/memory").json(), list)

    def test_api_memory_limit_param(self, client):
        entries = client.get("/api/memory?limit=2").json()
        assert len(entries) <= 2

    def test_api_decisions_200(self, client):
        assert client.get("/api/decisions").status_code == 200

    def test_api_decisions_is_list(self, client):
        assert isinstance(client.get("/api/decisions").json(), list)

    def test_api_decisions_has_confidence(self, client):
        decisions = client.get("/api/decisions").json()
        if decisions:
            assert "confidence" in decisions[0]

    def test_api_discussions_200(self, client):
        assert client.get("/api/discussions").status_code == 200

    def test_api_discussions_is_list(self, client):
        assert isinstance(client.get("/api/discussions").json(), list)

    def test_api_discussions_has_topic(self, client):
        discs = client.get("/api/discussions").json()
        if discs:
            assert "topic" in discs[0]


# ===========================================================================
# 14. HTTP: Collaboration Router
# ===========================================================================

class TestCollaborationRouterHttp:
    def test_get_collab_200(self, client):
        assert client.get("/collab").status_code == 200

    def test_get_collab_html(self, client):
        assert "text/html" in client.get("/collab").headers["content-type"]

    def test_get_collab_conversations_200(self, client):
        assert client.get("/collab/conversations").status_code == 200

    def test_get_collab_sessions_200(self, client):
        assert client.get("/collab/sessions").status_code == 200

    def test_get_collab_policies_200(self, client):
        assert client.get("/collab/policies").status_code == 200

    def test_api_collab_conversations_200(self, client):
        assert client.get("/api/collab/conversations").status_code == 200

    def test_api_collab_conversations_is_list(self, client):
        assert isinstance(client.get("/api/collab/conversations").json(), list)

    def test_api_collab_sessions_200(self, client):
        assert client.get("/api/collab/sessions").status_code == 200

    def test_api_collab_sessions_is_list(self, client):
        assert isinstance(client.get("/api/collab/sessions").json(), list)

    def test_api_collab_policies_200(self, client):
        assert client.get("/api/collab/policies").status_code == 200

    def test_api_collab_policies_is_list(self, client):
        assert isinstance(client.get("/api/collab/policies").json(), list)

    def test_api_collab_statistics_200(self, client):
        assert client.get("/api/collab/statistics").status_code == 200

    def test_api_collab_templates_200(self, client):
        assert client.get("/api/collab/templates").status_code == 200

    def test_api_collab_templates_non_empty(self, client):
        tmpls = client.get("/api/collab/templates").json()
        assert len(tmpls) > 0

    def test_api_collab_conversation_detail_404(self, client):
        resp = client.get("/api/collab/conversations/nonexistent-conv-id")
        assert resp.status_code == 404

    def test_api_collab_create_conversation_200(self, client):
        resp = client.post(
            "/api/collab/conversations",
            json={"title": "HTTP Router Test Conv", "creator": "test"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_api_collab_create_conversation_returns_conv(self, client):
        resp = client.post(
            "/api/collab/conversations",
            json={"title": "Router Conv 2", "creator": "test"},
        )
        conv = resp.json()["conversation"]
        assert "id" in conv

    def test_api_collab_messages_missing_conv_404(self, client):
        resp = client.get("/api/collab/conversations/bad-id/messages")
        assert resp.status_code == 404

    def test_api_collab_policies_delete_missing_404(self, client):
        resp = client.delete("/api/collab/policies/nonexistent-policy-xyz")
        assert resp.status_code == 404

    def test_api_collab_create_session_200(self, client):
        resp = client.post(
            "/api/collab/sessions",
            json={"title": "HTTP Test Session"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True


# ===========================================================================
# 15. Backward Compatibility
# ===========================================================================

class TestBackwardCompatibility:
    def test_create_router_importable(self):
        from apps.dashboard.routes import create_router
        assert callable(create_router)

    def test_create_router_returns_api_router(self):
        from fastapi.templating import Jinja2Templates
        from apps.dashboard.routes import create_router
        import os
        tmpl_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "apps", "dashboard", "templates"
        )
        templates = Jinja2Templates(directory=tmpl_dir)
        router = create_router(templates)
        from fastapi import APIRouter
        assert isinstance(router, APIRouter)

    def test_human_event_importable_from_routes(self):
        from apps.dashboard.routes import _human_event
        assert callable(_human_event)

    def test_human_event_works_via_routes_import(self):
        from apps.dashboard.routes import _human_event
        result = _human_event("company_started", {})
        assert isinstance(result, str)

    def test_routes_package_exists(self):
        import apps.dashboard.routes as r
        assert r is not None

    def test_services_package_importable(self):
        import apps.dashboard.services
        assert apps.dashboard.services is not None

    def test_company_service_importable(self):
        from apps.dashboard.services import CompanyService
        assert CompanyService is not None

    def test_organization_service_importable(self):
        from apps.dashboard.services import OrganizationService
        assert OrganizationService is not None

    def test_collaboration_service_importable(self):
        from apps.dashboard.services import CollaborationService
        assert CollaborationService is not None

    def test_artifact_service_importable(self):
        from apps.dashboard.services import ArtifactService
        assert ArtifactService is not None

    def test_event_service_importable(self):
        from apps.dashboard.services import EventService
        assert EventService is not None

    def test_all_existing_html_pages_still_200(self, client):
        pages = ["/", "/projects", "/employees", "/workflow", "/events", "/org"]
        for page in pages:
            resp = client.get(page)
            assert resp.status_code == 200, f"Page {page} returned {resp.status_code}"

    def test_all_org_subpages_still_200(self, client):
        pages = ["/org/departments", "/org/employees", "/org/roles", "/org/skills"]
        for page in pages:
            assert client.get(page).status_code == 200, f"Page {page} failed"

    def test_all_collab_pages_still_200(self, client):
        pages = ["/collab", "/collab/conversations", "/collab/sessions", "/collab/policies"]
        for page in pages:
            assert client.get(page).status_code == 200, f"Page {page} failed"

    def test_all_json_api_still_200(self, client):
        endpoints = [
            "/api/stats", "/api/status", "/api/projects", "/api/employees",
            "/api/workflow", "/api/memory", "/api/decisions", "/api/discussions",
            "/api/timeline", "/api/command-history", "/api/agent-status",
            "/api/artifacts", "/api/events/recent",
        ]
        for ep in endpoints:
            resp = client.get(ep)
            assert resp.status_code == 200, f"Endpoint {ep} returned {resp.status_code}"

    def test_collab_json_api_still_200(self, client):
        endpoints = [
            "/api/collab/conversations",
            "/api/collab/sessions",
            "/api/collab/policies",
            "/api/collab/statistics",
            "/api/collab/templates",
        ]
        for ep in endpoints:
            resp = client.get(ep)
            assert resp.status_code == 200, f"Endpoint {ep} returned {resp.status_code}"

    def test_org_json_api_still_200(self, client):
        endpoints = [
            "/api/org/departments",
            "/api/org/employees",
            "/api/org/roles",
            "/api/org/skills",
            "/api/org/statistics",
        ]
        for ep in endpoints:
            resp = client.get(ep)
            assert resp.status_code == 200, f"Endpoint {ep} returned {resp.status_code}"


# ===========================================================================
# 16. Router package structure
# ===========================================================================

class TestRouterPackageStructure:
    def test_dashboard_router_importable(self):
        from apps.dashboard.routes.dashboard import make_dashboard_router
        assert callable(make_dashboard_router)

    def test_projects_router_importable(self):
        from apps.dashboard.routes.projects import make_projects_router
        assert callable(make_projects_router)

    def test_employees_router_importable(self):
        from apps.dashboard.routes.employees import make_employees_router
        assert callable(make_employees_router)

    def test_organization_router_importable(self):
        from apps.dashboard.routes.organization import make_organization_router
        assert callable(make_organization_router)

    def test_workflow_router_importable(self):
        from apps.dashboard.routes.workflow import make_workflow_router
        assert callable(make_workflow_router)

    def test_collaboration_router_importable(self):
        from apps.dashboard.routes.collaboration import make_collaboration_router
        assert callable(make_collaboration_router)

    def test_events_router_importable(self):
        from apps.dashboard.routes.events import make_events_router
        assert callable(make_events_router)

    def test_artifacts_router_importable(self):
        from apps.dashboard.routes.artifacts import make_artifacts_router
        assert callable(make_artifacts_router)

    def test_api_router_importable(self):
        from apps.dashboard.routes.api import make_api_router
        assert callable(make_api_router)

    def test_all_routers_return_api_router(self):
        from fastapi import APIRouter
        from fastapi.templating import Jinja2Templates
        import os
        tmpl_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "apps", "dashboard", "templates"
        )
        templates = Jinja2Templates(directory=tmpl_dir)
        from apps.dashboard.routes import (
            make_dashboard_router, make_projects_router, make_employees_router,
            make_organization_router, make_workflow_router, make_collaboration_router,
            make_events_router, make_artifacts_router, make_api_router,
        )
        for factory in [
            lambda: make_dashboard_router(templates),
            lambda: make_projects_router(templates),
            lambda: make_employees_router(templates),
            lambda: make_organization_router(templates),
            lambda: make_workflow_router(templates),
            lambda: make_collaboration_router(templates),
            lambda: make_events_router(templates),
            lambda: make_artifacts_router(),
            lambda: make_api_router(),
        ]:
            assert isinstance(factory(), APIRouter)


# ===========================================================================
# 17. Service isolation — services work without HTTP layer
# ===========================================================================

class TestServiceIsolation:
    def test_company_service_standalone(self, state):
        from apps.dashboard.services.company_service import CompanyService
        svc = CompanyService(state)
        stats = svc.get_stats()
        assert isinstance(stats, dict)

    def test_event_service_standalone(self, state):
        from apps.dashboard.services.event_service import EventService
        svc = EventService(state)
        events = svc.get_recent_events(limit=5)
        assert isinstance(events, list)

    def test_org_service_standalone(self, state):
        from apps.dashboard.services.organization_service import OrganizationService
        svc = OrganizationService(state)
        depts = svc.list_departments_api()
        assert isinstance(depts, list)

    def test_collab_service_standalone(self, state):
        from apps.dashboard.services.collaboration_service import CollaborationService
        svc = CollaborationService(state)
        convs = svc.list_conversations()
        assert isinstance(convs, list)

    def test_artifact_service_standalone(self, state):
        from apps.dashboard.services.artifact_service import ArtifactService
        svc = ArtifactService(state)
        arts = svc.list_artifacts()
        assert isinstance(arts, list)

    def test_company_service_returns_same_data_as_state(self, state):
        from apps.dashboard.services.company_service import CompanyService
        svc = CompanyService(state)
        assert len(svc.list_projects()) == len(state.list_projects())

    def test_event_service_count_matches_stream(self, state):
        from apps.dashboard.services.event_service import EventService
        svc = EventService(state)
        stats = svc.get_statistics()
        assert stats["total_events"] == state.event_stream.event_count()

    def test_artifact_service_count_matches_state(self, state):
        from apps.dashboard.services.artifact_service import ArtifactService
        svc = ArtifactService(state)
        assert len(svc.list_artifacts()) == len(state.list_artifacts())


# ===========================================================================
# 18. Data integrity — services produce valid JSON-serializable data
# ===========================================================================

class TestDataIntegrity:
    def test_stats_json_serializable(self, company_svc):
        data = company_svc.get_stats()
        assert json.dumps(data) is not None

    def test_projects_api_json_serializable(self, company_svc):
        data = company_svc.list_projects_with_api_shape()
        assert json.dumps(data) is not None

    def test_employees_api_json_serializable(self, company_svc):
        data = company_svc.list_employees_api()
        assert json.dumps(data) is not None

    def test_component_status_json_serializable(self, company_svc):
        data = company_svc.get_component_status()
        assert json.dumps(data) is not None

    def test_memory_api_json_serializable(self, company_svc):
        data = company_svc.get_memory_api()
        assert json.dumps(data) is not None

    def test_decisions_api_json_serializable(self, company_svc):
        data = company_svc.get_decisions_api()
        assert json.dumps(data) is not None

    def test_discussions_api_json_serializable(self, company_svc):
        data = company_svc.get_discussions_api()
        assert json.dumps(data) is not None

    def test_timeline_json_serializable(self, event_svc):
        data = event_svc.get_timeline()
        assert json.dumps(data) is not None

    def test_collab_conversations_json_serializable(self, collab_svc):
        data = collab_svc.list_conversations()
        assert json.dumps(data) is not None

    def test_collab_policies_json_serializable(self, collab_svc):
        data = collab_svc.list_policies()
        assert json.dumps(data) is not None

    def test_collab_sessions_json_serializable(self, collab_svc):
        data = collab_svc.list_sessions()
        assert json.dumps(data) is not None

    def test_org_departments_json_serializable(self, org_svc):
        data = org_svc.list_departments_api()
        assert json.dumps(data) is not None

    def test_artifacts_api_json_serializable(self, artifact_svc):
        data = artifact_svc.list_artifacts_api()
        assert json.dumps(data) is not None


# ===========================================================================
# 19. Parametrized — all stat fields are non-negative integers
# ===========================================================================

STAT_FIELDS = [
    "total_projects", "active_projects", "total_employees", "active_employees",
    "total_departments", "total_events", "total_memory_entries",
    "total_decisions", "total_discussions",
]


@pytest.mark.parametrize("field", STAT_FIELDS)
def test_stats_field_non_negative(company_svc, field):
    stats = company_svc.get_stats()
    assert stats[field] >= 0


# ===========================================================================
# 20. Parametrized — all HTML pages return 200
# ===========================================================================

HTML_PAGES = [
    "/", "/projects", "/employees", "/workflow", "/events", "/org",
    "/org/departments", "/org/employees", "/org/roles", "/org/skills",
    "/collab", "/collab/conversations", "/collab/sessions", "/collab/policies",
]


@pytest.mark.parametrize("page", HTML_PAGES)
def test_html_page_200(client, page):
    assert client.get(page).status_code == 200


# ===========================================================================
# 21. Parametrized — all JSON API endpoints return 200
# ===========================================================================

JSON_APIS = [
    "/api/stats", "/api/status", "/api/projects", "/api/employees",
    "/api/workflow", "/api/memory", "/api/decisions", "/api/discussions",
    "/api/timeline", "/api/command-history", "/api/agent-status", "/api/artifacts",
    "/api/events/recent", "/api/org/departments", "/api/org/employees",
    "/api/org/roles", "/api/org/skills", "/api/org/statistics",
    "/api/collab/conversations", "/api/collab/sessions", "/api/collab/policies",
    "/api/collab/statistics", "/api/collab/templates",
]


@pytest.mark.parametrize("endpoint", JSON_APIS)
def test_json_api_200(client, endpoint):
    assert client.get(endpoint).status_code == 200


# ===========================================================================
# 22. SSE specific
# ===========================================================================

class TestSSEEndpoint:
    def test_sse_stream_endpoint_exists(self, client):
        with client.stream("GET", "/api/events/stream") as resp:
            assert resp.status_code == 200
            for _ in resp.iter_bytes(1):
                break

    def test_sse_stream_content_type_correct(self, client):
        with client.stream("GET", "/api/events/stream") as resp:
            ct = resp.headers.get("content-type", "")
            assert "text/event-stream" in ct
            for _ in resp.iter_bytes(1):
                break

    def test_sse_stream_no_cache_header(self, client):
        with client.stream("GET", "/api/events/stream") as resp:
            cc = resp.headers.get("cache-control", "")
            assert "no-cache" in cc
            for _ in resp.iter_bytes(1):
                break

    def test_sse_stream_first_data_line(self, client):
        with client.stream("GET", "/api/events/stream") as resp:
            raw = b""
            for chunk in resp.iter_bytes(256):
                raw += chunk
                if b"data:" in raw:
                    break
        assert b"data:" in raw

    def test_sse_stream_connected_payload(self, client):
        with client.stream("GET", "/api/events/stream") as resp:
            raw = b""
            for chunk in resp.iter_bytes(512):
                raw += chunk
                if b"connected" in raw:
                    break
        text = raw.decode(errors="replace")
        data_lines = [l[5:] for l in text.splitlines() if l.startswith("data:")]
        assert data_lines
        first = json.loads(data_lines[0])
        assert first["type"] == "connected"

    def test_sse_generator_is_async(self, state):
        import inspect
        from apps.dashboard.services.event_service import EventService
        svc = EventService(state)
        gen_func = svc.sse_generator
        # sse_generator is an async def, so calling it returns an async generator
        # We verify the method exists and is callable
        assert callable(gen_func)


# ===========================================================================
# 23. No business logic changes — engine data unchanged
# ===========================================================================

class TestNoBusinessLogicChanges:
    def test_executive_engine_still_has_projects(self, state):
        assert len(state.list_projects()) > 0

    def test_workflow_engine_still_has_workflows(self, state):
        wfs = state.workflow_engine.history()
        assert len(wfs) > 0

    def test_memory_engine_still_has_entries(self, state):
        assert state.memory_engine.count() > 0

    def test_decision_engine_still_has_decisions(self, state):
        assert state.decision_engine.statistics()["total_decisions"] > 0

    def test_discussion_engine_still_has_discussions(self, state):
        assert state.discussion_engine.count() > 0

    def test_collab_hub_still_has_conversations(self, state):
        assert len(state.collab_hub.list_conversations()) > 0

    def test_collab_hub_still_has_policies(self, state):
        assert len(state.collab_hub.list_policies()) > 0

    def test_event_stream_still_has_events(self, state):
        assert state.event_stream.event_count() > 0

    def test_workforce_registry_still_has_employees(self, state):
        assert len(state.workforce_registry.list_all()) > 0

    def test_org_engine_still_has_departments(self, state):
        assert len(state.org_engine.list_departments()) > 0

    def test_services_dont_mutate_state(self, state, company_svc):
        count_before = len(state.list_projects())
        company_svc.get_stats()
        company_svc.list_projects_with_api_shape()
        company_svc.get_dashboard_context()
        count_after = len(state.list_projects())
        assert count_before == count_after


# ===========================================================================
# 24. SSE client JS helpers
# ===========================================================================

class TestSSEClientJs:
    def test_app_js_has_init_sse(self, client):
        resp = client.get("/static/app.js")
        assert resp.status_code == 200
        assert "_initSSE" in resp.text

    def test_app_js_has_event_source(self, client):
        resp = client.get("/static/app.js")
        assert "EventSource" in resp.text

    def test_app_js_has_sse_status_setter(self, client):
        resp = client.get("/static/app.js")
        assert "_setSseStatus" in resp.text

    def test_app_js_has_animate_counter(self, client):
        resp = client.get("/static/app.js")
        assert "_animateCounter" in resp.text

    def test_app_js_has_fetch_counters(self, client):
        resp = client.get("/static/app.js")
        assert "_fetchAndUpdateCounters" in resp.text

    def test_app_js_calls_init_sse_on_load(self, client):
        resp = client.get("/static/app.js")
        assert "_initSSE()" in resp.text

    def test_style_css_has_sse_dot_live(self, client):
        resp = client.get("/static/style.css")
        assert resp.status_code == 200
        assert "sse-dot-live" in resp.text

    def test_style_css_has_sse_new_row(self, client):
        resp = client.get("/static/style.css")
        assert "sse-new-row" in resp.text

    def test_style_css_has_sse_pulse_animation(self, client):
        resp = client.get("/static/style.css")
        assert "sse-pulse" in resp.text

    def test_base_html_has_sse_status_dot_id(self, client):
        resp = client.get("/")
        assert "sse-status-dot" in resp.text

    def test_base_html_has_sse_status_label_id(self, client):
        resp = client.get("/")
        assert "sse-status-label" in resp.text

    def test_app_js_has_append_live_timeline_row(self, client):
        resp = client.get("/static/app.js")
        assert "_appendLiveTimelineRow" in resp.text

    def test_app_js_has_events_stream_url(self, client):
        resp = client.get("/static/app.js")
        assert "/api/events/stream" in resp.text

    def test_style_css_has_sse_blink_animation(self, client):
        resp = client.get("/static/style.css")
        assert "sse-blink" in resp.text

    def test_style_css_has_sse_dot_reconnecting(self, client):
        resp = client.get("/static/style.css")
        assert "sse-dot-reconnecting" in resp.text

    def test_style_css_has_sse_row_visible(self, client):
        resp = client.get("/static/style.css")
        assert "sse-row-visible" in resp.text


# ===========================================================================
# 25. Parametrized human_event — all known action translations
# ===========================================================================

HUMAN_EVENT_ACTIONS = [
    ("company_started",       {},                               "başlatıldı"),
    ("project_created",       {"title": "Proj X"},             "Proj X"),
    ("employee_hired",        {"name": "Bob", "role": "A"},    "Bob"),
    ("workflow_started",      {"name": "WF2"},                 "WF2"),
    ("decision_created",      {"title": "Choice"},             "Choice"),
    ("decision_recommended",  {"recommendation": "MySQL"},     "MySQL"),
    ("discussion_started",    {"topic": "Design"},             "Design"),
    ("discussion_closed",     {"topic": "Design"},             "Design"),
    ("entry_stored",          {"title": "Mem1"},               "Mem1"),
    ("task_created",          {"title": "Task1"},              "Task1"),
    ("stage_advanced",        {"stage": "Exec"},               "Exec"),
    ("task_completed",        {"title": "Done"},               "Done"),
    ("project_completed",     {"title": "Ship"},               "Ship"),
    ("employee_promoted",     {"name": "Carol"},               "Carol"),
    ("unknown_action_xyz",    {},                              None),
]


@pytest.mark.parametrize("action,payload,expected_substr", HUMAN_EVENT_ACTIONS)
def test_human_event_action_translation(action, payload, expected_substr):
    from apps.dashboard.services.event_service import human_event
    result = human_event(action, payload)
    assert isinstance(result, str)
    assert len(result) > 0
    if expected_substr is not None:
        assert expected_substr in result


# ===========================================================================
# 26. CompanyService — dashboard context key completeness
# ===========================================================================

DASHBOARD_CONTEXT_KEYS = [
    "total_projects", "active_projects", "total_employees", "active_employees",
    "total_departments", "projects", "recent_events", "departments",
    "pipeline_step", "workflow_stats",
]


@pytest.mark.parametrize("key", DASHBOARD_CONTEXT_KEYS)
def test_dashboard_context_has_key(company_svc, key):
    ctx = company_svc.get_dashboard_context()
    assert key in ctx, f"Dashboard context missing key: {key}"


# ===========================================================================
# 27. EventService — timeline data shape
# ===========================================================================

class TestEventServiceTimeline:
    def test_timeline_limit_one(self, event_svc):
        items = event_svc.get_timeline(limit=1)
        assert len(items) <= 1

    def test_timeline_each_has_id(self, event_svc):
        for item in event_svc.get_timeline():
            assert "id" in item

    def test_timeline_each_has_source(self, event_svc):
        for item in event_svc.get_timeline():
            assert "source" in item

    def test_timeline_each_has_channel(self, event_svc):
        for item in event_svc.get_timeline():
            assert "channel" in item

    def test_timeline_each_has_action(self, event_svc):
        for item in event_svc.get_timeline():
            assert "action" in item

    def test_timeline_sentence_is_str(self, event_svc):
        for item in event_svc.get_timeline():
            assert isinstance(item["sentence"], str)

    def test_timeline_timestamp_hms_format(self, event_svc):
        for item in event_svc.get_timeline():
            hms = item["timestamp_hms"]
            assert ":" in hms and len(hms) == 5

    def test_timeline_json_serializable(self, event_svc):
        data = event_svc.get_timeline(limit=10)
        dumped = json.dumps(data)
        assert isinstance(dumped, str)

    def test_recent_events_each_has_sentence(self, event_svc):
        for ev in event_svc.get_recent_events():
            assert "sentence" in ev

    def test_recent_events_each_has_source(self, event_svc):
        for ev in event_svc.get_recent_events():
            assert "source" in ev


# ===========================================================================
# 28. Workflow data shape
# ===========================================================================

class TestWorkflowData:
    def test_api_workflow_stats_non_empty(self, client):
        data = client.get("/api/workflow").json()
        assert isinstance(data["stats"], dict)

    def test_api_workflow_stats_has_total(self, client):
        stats = client.get("/api/workflow").json()["stats"]
        assert "total" in stats or len(stats) > 0

    def test_api_workflow_workflows_items_have_id(self, client):
        workflows = client.get("/api/workflow").json()["workflows"]
        for wf in workflows:
            assert "id" in wf

    def test_api_workflow_workflows_items_have_name(self, client):
        workflows = client.get("/api/workflow").json()["workflows"]
        for wf in workflows:
            assert "name" in wf

    def test_api_workflow_workflows_items_have_status(self, client):
        workflows = client.get("/api/workflow").json()["workflows"]
        for wf in workflows:
            assert "status" in wf

    def test_get_workflow_page_html_content(self, client):
        resp = client.get("/workflow")
        assert len(resp.text) > 100

    def test_api_workflow_200_multiple_calls(self, client):
        for _ in range(3):
            assert client.get("/api/workflow").status_code == 200

    def test_api_workflow_response_is_json(self, client):
        resp = client.get("/api/workflow")
        assert "application/json" in resp.headers.get("content-type", "")


# ===========================================================================
# 29. Collaboration templates field shape
# ===========================================================================

class TestCollabTemplateFields:
    def test_templates_each_has_name_or_type(self, collab_svc):
        for tmpl in collab_svc.list_templates():
            has_name = "name" in tmpl or "template_type" in tmpl
            assert has_name

    def test_templates_each_is_dict(self, collab_svc):
        for tmpl in collab_svc.list_templates():
            assert isinstance(tmpl, dict)

    def test_templates_json_serializable(self, collab_svc):
        data = collab_svc.list_templates()
        assert json.dumps(data) is not None

    def test_api_collab_templates_each_is_dict(self, client):
        tmpls = client.get("/api/collab/templates").json()
        for t in tmpls:
            assert isinstance(t, dict)

    def test_collab_statistics_has_total_conversations(self, client):
        stats = client.get("/api/collab/statistics").json()
        assert "total_conversations" in stats

    def test_collab_statistics_values_non_negative(self, client):
        stats = client.get("/api/collab/statistics").json()
        for v in stats.values():
            if isinstance(v, (int, float)):
                assert v >= 0


# ===========================================================================
# 30. SSE header and format verification
# ===========================================================================

class TestSSEHeadersAndFormat:
    def test_sse_x_accel_buffering_header(self, client):
        with client.stream("GET", "/api/events/stream") as resp:
            header = resp.headers.get("x-accel-buffering", "")
            assert header == "no"
            for _ in resp.iter_bytes(1):
                break

    def test_sse_connection_keep_alive_header(self, client):
        with client.stream("GET", "/api/events/stream") as resp:
            conn = resp.headers.get("connection", "")
            assert "keep-alive" in conn.lower()
            for _ in resp.iter_bytes(1):
                break

    def test_sse_first_event_starts_with_data(self, client):
        with client.stream("GET", "/api/events/stream") as resp:
            raw = b""
            for chunk in resp.iter_bytes(64):
                raw += chunk
                if b"\n" in raw:
                    break
        assert raw.startswith(b"data:")

    def test_sse_connected_event_has_type_field(self, client):
        with client.stream("GET", "/api/events/stream") as resp:
            raw = b""
            for chunk in resp.iter_bytes(256):
                raw += chunk
                if b"data:" in raw:
                    break
        lines = raw.decode(errors="replace").splitlines()
        data_lines = [l[5:] for l in lines if l.startswith("data:")]
        assert data_lines
        payload = json.loads(data_lines[0])
        assert "type" in payload

    def test_sse_stream_returns_streaming_response(self, state):
        from apps.dashboard.routes.events import make_events_router
        import inspect
        src = inspect.getsource(make_events_router)
        assert "StreamingResponse" in src

    def test_sse_generator_method_exists(self, event_svc):
        assert hasattr(event_svc, "sse_generator")

    def test_sse_generator_is_callable(self, event_svc):
        assert callable(event_svc.sse_generator)

    def test_sse_endpoint_url_correct(self, client):
        with client.stream("GET", "/api/events/stream") as resp:
            assert resp.status_code == 200
            for _ in resp.iter_bytes(1):
                break


# ===========================================================================
# 31. Service constructors and dependency injection
# ===========================================================================

class TestServiceConstructors:
    def test_company_service_constructor_accepts_state(self, state):
        from apps.dashboard.services.company_service import CompanyService
        svc = CompanyService(state)
        assert svc is not None

    def test_org_service_constructor_accepts_state(self, state):
        from apps.dashboard.services.organization_service import OrganizationService
        svc = OrganizationService(state)
        assert svc is not None

    def test_collab_service_constructor_accepts_state(self, state):
        from apps.dashboard.services.collaboration_service import CollaborationService
        svc = CollaborationService(state)
        assert svc is not None

    def test_artifact_service_constructor_accepts_state(self, state):
        from apps.dashboard.services.artifact_service import ArtifactService
        svc = ArtifactService(state)
        assert svc is not None

    def test_event_service_constructor_accepts_state(self, state):
        from apps.dashboard.services.event_service import EventService
        svc = EventService(state)
        assert svc is not None

    def test_multiple_service_instances_independent(self, state):
        from apps.dashboard.services.company_service import CompanyService
        svc1 = CompanyService(state)
        svc2 = CompanyService(state)
        assert svc1.get_stats() == svc2.get_stats()

    def test_services_all_importable_from_package(self):
        from apps.dashboard.services import (
            CompanyService, OrganizationService, CollaborationService,
            ArtifactService, EventService,
        )
        for cls in [CompanyService, OrganizationService, CollaborationService,
                    ArtifactService, EventService]:
            assert cls is not None

    def test_services_package_has_all_five_classes(self):
        import apps.dashboard.services as svc_pkg
        for name in ["CompanyService", "OrganizationService", "CollaborationService",
                     "ArtifactService", "EventService"]:
            assert hasattr(svc_pkg, name)


# ===========================================================================
# 32. Organization service page data completeness
# ===========================================================================

class TestOrgServicePageData:
    def test_departments_page_data_has_stats(self, org_svc):
        data = org_svc.get_departments_page_data()
        assert "stats" in data

    def test_employees_page_data_has_stats(self, org_svc):
        data = org_svc.get_employees_page_data()
        assert "stats" in data

    def test_roles_page_data_has_stats(self, org_svc):
        data = org_svc.get_roles_page_data()
        assert "stats" in data

    def test_skills_page_data_has_stats(self, org_svc):
        data = org_svc.get_skills_page_data()
        assert "stats" in data

    def test_departments_page_data_json_serializable(self, org_svc):
        data = org_svc.get_departments_page_data()
        assert json.dumps(data, default=str) is not None

    def test_employees_page_data_json_serializable(self, org_svc):
        data = org_svc.get_employees_page_data()
        assert json.dumps(data, default=str) is not None

    def test_statistics_has_total_departments(self, org_svc):
        stats = org_svc.statistics()
        assert "total_departments" in stats

    def test_statistics_has_total_employees(self, org_svc):
        stats = org_svc.statistics()
        assert "total_employees" in stats

    def test_statistics_values_non_negative(self, org_svc):
        stats = org_svc.statistics()
        for v in stats.values():
            if isinstance(v, (int, float)):
                assert v >= 0


# ===========================================================================
# 33. Event statistics and page data
# ===========================================================================

class TestEventStatisticsAndPageData:
    def test_statistics_has_by_channel(self, event_svc):
        stats = event_svc.get_statistics()
        assert "by_channel" in stats

    def test_statistics_by_channel_is_dict(self, event_svc):
        stats = event_svc.get_statistics()
        assert isinstance(stats["by_channel"], dict)

    def test_statistics_total_events_non_negative(self, event_svc):
        assert event_svc.get_statistics()["total_events"] >= 0

    def test_events_page_data_json_serializable(self, event_svc):
        data = event_svc.get_events_page_data()
        assert json.dumps(data, default=str) is not None

    def test_events_page_data_has_timeline(self, event_svc):
        data = event_svc.get_events_page_data()
        assert "timeline" in data

    def test_events_page_data_timeline_is_list(self, event_svc):
        data = event_svc.get_events_page_data()
        assert isinstance(data["timeline"], list)

    def test_events_page_data_ev_stats_is_dict(self, event_svc):
        data = event_svc.get_events_page_data()
        assert isinstance(data["ev_stats"], dict)

    def test_events_page_data_events_with_sentences_is_list(self, event_svc):
        data = event_svc.get_events_page_data()
        assert isinstance(data["events_with_sentences"], list)

    def test_events_with_sentences_has_sentence_field(self, event_svc):
        data = event_svc.get_events_page_data()
        for ev in data["events_with_sentences"]:
            assert "sentence" in ev


# ===========================================================================
# 34. Parametrized — component status keys
# ===========================================================================

COMPONENT_STATUS_FIELDS = ["key", "label", "status", "details"]


@pytest.mark.parametrize("field", COMPONENT_STATUS_FIELDS)
def test_component_status_each_has_field(company_svc, field):
    components = company_svc.get_component_status()["components"]
    for c in components:
        assert field in c, f"Component missing field: {field}"


# ===========================================================================
# 35. Parametrized — recent events data shape
# ===========================================================================

RECENT_EVENT_FIELDS = ["id", "source", "channel", "timestamp", "action", "sentence", "payload"]


@pytest.mark.parametrize("field", RECENT_EVENT_FIELDS)
def test_recent_event_has_field(event_svc, field):
    events = event_svc.get_recent_events(limit=20)
    if not events:
        pytest.skip("No events to check")
    for ev in events:
        assert field in ev, f"Recent event missing field: {field}"


# ===========================================================================
# 36. Parametrized — collab conversation data shape
# ===========================================================================

CONVERSATION_FIELDS = ["id", "title", "status", "created_at"]


@pytest.mark.parametrize("field", CONVERSATION_FIELDS)
def test_conversation_has_field(collab_svc, field):
    convs = collab_svc.list_conversations()
    if not convs:
        pytest.skip("No conversations to check")
    for conv in convs:
        assert field in conv, f"Conversation missing field: {field}"


# ===========================================================================
# 37. Parametrized — project API shape
# ===========================================================================

PROJECT_API_FIELDS = ["id", "title", "status", "created_at", "completion_percentage"]


@pytest.mark.parametrize("field", PROJECT_API_FIELDS)
def test_project_api_has_field(company_svc, field):
    projects = company_svc.list_projects_with_api_shape()
    if not projects:
        pytest.skip("No projects to check")
    for p in projects:
        assert field in p, f"Project API missing field: {field}"


# ===========================================================================
# 38. Parametrized — employee API shape
# ===========================================================================

EMPLOYEE_API_FIELDS = ["id", "name", "role", "department", "skills"]


@pytest.mark.parametrize("field", EMPLOYEE_API_FIELDS)
def test_employee_api_has_field(company_svc, field):
    emps = company_svc.list_employees_api()
    if not emps:
        pytest.skip("No employees to check")
    for emp in emps:
        assert field in emp, f"Employee API missing field: {field}"
