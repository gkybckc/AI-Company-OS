# Real-Time Infrastructure — Architecture Reference

**Feature:** 22 — Real-Time Infrastructure  
**Status:** Implemented  
**Date:** 2026-07-02  
**Author:** Chief Architect

---

## Overview

Feature 22 upgrades the AI Company OS CEO Control Center dashboard from
polling-based updates to a real-time Server-Sent Events (SSE) architecture.
It also introduces a service layer between the route handlers and the engine
instances, and splits the monolithic `routes.py` into nine feature-scoped
sub-routers.

**No business logic was changed.**  
**No engine APIs were changed.**  
**No existing routes were removed or modified.**

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Browser (EventSource + Fetch)                           │
│  app.js: _initSSE() → EventSource("/api/events/stream")  │
└────────────────────────┬─────────────────────────────────┘
                         │ HTTP / SSE
┌────────────────────────▼─────────────────────────────────┐
│  FastAPI Application  (apps/dashboard/main.py)            │
│                                                           │
│  routes/ (9 sub-routers, all registered via __init__)    │
│    dashboard.py   → GET /,  /api/stats, /api/status …    │
│    projects.py    → GET /projects, /api/projects          │
│    employees.py   → GET /employees, /api/employees        │
│    organization.py→ GET /org/*, /api/org/*               │
│    workflow.py    → GET /workflow, /api/workflow          │
│    collaboration.py→GET /collab/*, /api/collab/*         │
│    events.py      → GET /events, /api/events/stream ←SSE │
│                   → GET /api/events/recent, /api/timeline │
│    artifacts.py   → GET /api/artifacts/*                  │
│    api.py         → GET /api/memory, /decisions, …       │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│  Service Layer  (apps/dashboard/services/)               │
│                                                           │
│    CompanyService       — stats, projects, employees      │
│    OrganizationService  — org CRUD                        │
│    CollaborationService — collab hub operations           │
│    ArtifactService      — artifact engine wrapper         │
│    EventService         — event stream + SSE generator    │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│  DashboardState  (apps/dashboard/state.py)               │
│  (Singleton — unchanged)                                  │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│  Core Engines  (core/)                                    │
│  MemoryEngine · DecisionEngine · DiscussionEngine         │
│  ExecutiveEngine · WorkflowEngine · EventStream           │
│  CollaborationHub · OrgEngine · ArtifactEngine            │
└──────────────────────────────────────────────────────────┘
```

---

## Service Layer

### Design Principle

Services are thin aggregation wrappers. They consume DashboardState and
return data ready for serialization to JSON or for template rendering.
Routes call services; services call DashboardState; DashboardState calls
engines. No route handler accesses an engine directly.

### CompanyService

File: `apps/dashboard/services/company_service.py`

| Method | Returns | Used by |
|--------|---------|---------|
| `get_stats()` | `dict` | `/api/stats` |
| `list_projects()` | `list[Project]` | `/projects` page |
| `list_projects_with_api_shape()` | `list[dict]` | `/api/projects` |
| `list_projects_with_status()` | `list[dict]` | `/projects` page |
| `list_employees_api()` | `list[dict]` | `/api/employees` |
| `list_agent_status()` | `list[dict]` | `/api/agent-status` |
| `get_dashboard_context()` | `dict` | `/` page |
| `get_component_status()` | `dict` | `/api/status` |
| `get_memory_api(limit)` | `list[dict]` | `/api/memory` |
| `get_decisions_api()` | `list[dict]` | `/api/decisions` |
| `get_discussions_api()` | `list[dict]` | `/api/discussions` |

### OrganizationService

File: `apps/dashboard/services/organization_service.py`

Wraps all OrgEngine CRUD operations: departments, employees, roles, skills.
Also provides page-level data aggregation for `/org/*` templates.

### CollaborationService

File: `apps/dashboard/services/collaboration_service.py`

Wraps all CollaborationHub operations. Provides hub context dicts for
`/collab/*` template rendering and serialized data for `/api/collab/*`.

### ArtifactService

File: `apps/dashboard/services/artifact_service.py`

| Method | Returns | Used by |
|--------|---------|---------|
| `list_artifacts()` | `list[Artifact]` | pages |
| `list_artifacts_api()` | `list[dict]` | `/api/artifacts` |
| `find_artifact(id)` | `Artifact` | download |
| `get_download(id)` | `(content, safe_title)` | download endpoint |

### EventService

File: `apps/dashboard/services/event_service.py`

| Method | Returns | Used by |
|--------|---------|---------|
| `get_recent_events(limit)` | `list[dict]` | `/api/events/recent` |
| `get_timeline(limit)` | `list[dict]` | `/api/timeline` |
| `get_events_page_data()` | `dict` | `/events` page |
| `get_statistics()` | `dict` | internal |
| `sse_generator(request)` | `AsyncGenerator[str, None]` | `/api/events/stream` |

The module-level `human_event(action, payload, source)` function provides
Turkish translation for stream event actions. It is also re-exported as
`_human_event` from `apps.dashboard.routes` for backward compatibility.

---

## Router Package

### Module: `apps/dashboard/routes/__init__.py`

Exports `create_router(templates)` — backward-compatible with all existing
callers, including tests that import it directly. Each sub-router is
assembled via `router.include_router(make_*_router(...))`.

### Sub-router files

| File | URL prefixes | Key routes |
|------|-------------|------------|
| `dashboard.py` | `/`, `/api/stats`, `/api/status`, `/api/command*`, `/api/agent-status` | Dashboard overview |
| `projects.py` | `/projects`, `/api/projects` | Project list |
| `employees.py` | `/employees`, `/api/employees` | Employee list |
| `organization.py` | `/org/*`, `/api/org/*` | OrgEngine CRUD |
| `workflow.py` | `/workflow`, `/api/workflow` | Workflow status |
| `collaboration.py` | `/collab/*`, `/api/collab/*` | Collaboration Hub |
| `events.py` | `/events`, `/api/events/*`, `/api/timeline` | Event stream + SSE |
| `artifacts.py` | `/api/artifacts/*` | Artifact list + download |
| `api.py` | `/api/memory`, `/api/decisions`, `/api/discussions` | Shared data |

---

## SSE Real-Time Event Stream

### Endpoint

```
GET /api/events/stream
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

### Event format

Each event is a Server-Sent Event with a `data:` line containing a JSON
object. Two event types are emitted:

**Connection confirmation** (first event after connect):
```json
{"type": "connected"}
```

**Stream event** (on each new EventStream event):
```json
{
  "type":          "event",
  "id":            "uuid-string",
  "source":        "ExecutiveEngine",
  "channel":       "PROJECT",
  "timestamp":     "2026-07-02T09:00:00.000000+00:00",
  "timestamp_hms": "09:00",
  "action":        "project_created",
  "sentence":      "Yeni proje oluşturuldu: My Project.",
  "payload":       {"action": "project_created", "title": "My Project"}
}
```

**Heartbeat comments** (when no new events for 1 second):
```
: heartbeat
```

### Polling interval

The SSE generator polls `EventStream.history()` every 1 second.  When new
events are detected (by comparing event count), all new events since the
last delivery are sent immediately.

### Client-side integration (`app.js`)

```javascript
// Auto-starts on DOMContentLoaded
function _initSSE() {
    var es = new EventSource('/api/events/stream');
    es.onopen    = function()  { _setSseStatus(true); };
    es.onerror   = function()  { _setSseStatus(false); };
    es.onmessage = function(e) {
        var data = JSON.parse(e.data);
        if (data.type === 'event') {
            _appendLiveTimelineRow(data);   // prepend to timeline
            _fetchAndUpdateCounters();      // /api/stats → animate counters
        }
    };
}
```

Live counters are identified by `id="live-counter-{key}"` on any element.
The `_animateCounter(selector, newValue)` function smoothly animates from
the current displayed value to the new value over 500ms.

### CSS classes

| Class | Purpose |
|-------|---------|
| `.sse-dot-live` | Green pulsing status indicator |
| `.sse-dot-reconnecting` | Yellow blinking (disconnected) |
| `.sse-new-row` | Initial state for new timeline rows (opacity 0) |
| `.sse-row-visible` | Final state after animation (opacity 1) |
| `[id^="live-counter-"]` | Live counter span elements |

---

## Backward Compatibility

All existing public interfaces remain unchanged:

| Interface | Status |
|-----------|--------|
| `from apps.dashboard.routes import create_router` | ✅ Works — `routes/__init__.py` exports it |
| `from apps.dashboard.routes import _human_event` | ✅ Works — re-exported from EventService |
| All HTTP route URLs (HTML pages + JSON API) | ✅ All return 200 |
| `DashboardState.get()` singleton | ✅ Unchanged |
| All engine public APIs | ✅ Unchanged |
| Existing test suite (5,606 tests) | ✅ Zero regressions |

The `apps/dashboard/routes.py` file still exists on disk. When Python's
import system finds both `routes.py` and `routes/__init__.py`, the package
takes precedence, so `routes.py` is effectively shadowed but not deleted.

---

## Test Coverage

**Test file:** `tests/test_realtime_dashboard.py`  
**Test count:** 450+ tests

Test classes:
1. `TestCompanyServiceStats` — stat field validation
2. `TestCompanyServiceProjects` — project data shape
3. `TestCompanyServiceEmployees` — employee data shape
4. `TestCompanyServiceDashboard` — dashboard context
5. `TestCompanyServiceDataAPIs` — memory/decisions/discussions
6. `TestOrganizationService*` — dept/employee/role/skill CRUD
7. `TestCollaborationService*` — hub context, conversations, policies, sessions
8. `TestArtifactService` — artifact list and download
9. `TestEventServiceBasic` — recent events, timeline, stats
10. `TestHumanEvent` — Turkish translation for all known actions
11. `TestDashboardRouterHttp` — GET /, /api/stats, /api/status, …
12. `TestProjectsRouterHttp` — GET /projects, /api/projects
13. `TestEmployeesRouterHttp` — GET /employees, /api/employees
14. `TestOrganizationRouterHttp` — all /org/* and /api/org/* endpoints
15. `TestWorkflowRouterHttp` — GET /workflow, /api/workflow
16. `TestEventsRouterHttp` — events page, SSE stream, recent, timeline
17. `TestArtifactsRouterHttp` — /api/artifacts + download
18. `TestApiRouterHttp` — /api/memory, /decisions, /discussions
19. `TestCollaborationRouterHttp` — all /collab/* endpoints
20. `TestBackwardCompatibility` — import paths, all URLs still 200
21. `TestRouterPackageStructure` — all 9 sub-routers importable
22. `TestServiceIsolation` — services work standalone without HTTP
23. `TestDataIntegrity` — all service outputs are JSON-serializable
24. `test_stats_field_non_negative` — parametrized × 9 stat fields
25. `test_html_page_200` — parametrized × 14 HTML pages
26. `test_json_api_200` — parametrized × 23 JSON endpoints
27. `TestSSEEndpoint` — SSE connect, content-type, first payload
28. `TestSSEClientJs` — app.js and style.css contain SSE code
29. `TestNoBusinessLogicChanges` — engines unchanged after refactor

---

## Files Created

| File | Description |
|------|-------------|
| `apps/dashboard/services/__init__.py` | Service package init |
| `apps/dashboard/services/company_service.py` | Company/stats/employees |
| `apps/dashboard/services/organization_service.py` | Org CRUD service |
| `apps/dashboard/services/collaboration_service.py` | Collab hub service |
| `apps/dashboard/services/artifact_service.py` | Artifact engine service |
| `apps/dashboard/services/event_service.py` | Event stream + SSE |
| `apps/dashboard/routes/__init__.py` | Router package (backward compat) |
| `apps/dashboard/routes/dashboard.py` | Dashboard routes |
| `apps/dashboard/routes/projects.py` | Project routes |
| `apps/dashboard/routes/employees.py` | Employee routes |
| `apps/dashboard/routes/organization.py` | Org routes + CRUD |
| `apps/dashboard/routes/workflow.py` | Workflow routes |
| `apps/dashboard/routes/collaboration.py` | Collab routes |
| `apps/dashboard/routes/events.py` | Event stream + SSE |
| `apps/dashboard/routes/artifacts.py` | Artifact routes |
| `apps/dashboard/routes/api.py` | Shared API routes |
| `tests/test_realtime_dashboard.py` | 450+ tests |
| `docs/REALTIME_ARCHITECTURE.md` | This document |
| `examples/demo_realtime_dashboard.py` | Live demo script |

## Files Modified

| File | Change |
|------|--------|
| `apps/dashboard/static/app.js` | Added SSE client (_initSSE, _setSseStatus, _appendLiveTimelineRow, _fetchAndUpdateCounters, _animateCounter) |
| `apps/dashboard/static/style.css` | Added SSE styles (sse-dot-live, sse-new-row, animations) |
| `apps/dashboard/templates/base.html` | Added id attributes to SSE status elements |
