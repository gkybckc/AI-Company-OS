"""
Event routes — /events page, /api/events/stream (SSE), /api/events/recent,
and /api/timeline.

The SSE endpoint at GET /api/events/stream replaces HTMX polling for
real-time event delivery.  Clients connect once via EventSource and receive
new events as they are published to the EventStream.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from apps.dashboard.services.event_service import EventService
from apps.dashboard.state import DashboardState


def make_events_router(templates: Jinja2Templates) -> APIRouter:
    router = APIRouter()

    @router.get("/events", response_class=HTMLResponse)
    async def events_page(request: Request) -> HTMLResponse:
        svc = EventService(DashboardState.get())
        ctx = svc.get_events_page_data()
        ctx.update({"page": "events", "company_name": "AI Company OS"})
        return templates.TemplateResponse(request, "events.html", ctx)

    @router.get("/api/events/stream")
    async def api_events_stream(request: Request) -> StreamingResponse:
        """
        Server-Sent Events endpoint for real-time event delivery.

        Clients connect with:
            var es = new EventSource('/api/events/stream');
            es.onmessage = function(e) { var data = JSON.parse(e.data); ... };

        Each data payload is a JSON object with fields:
            type          — "connected" (first event) or "event"
            id            — StreamEvent UUID
            source        — publishing component name
            channel       — StreamChannel value
            timestamp     — ISO-8601 UTC timestamp
            timestamp_hms — HH:MM display string
            action        — raw action key from payload
            sentence      — Turkish human-readable translation
            payload       — full StreamEvent payload dict
        """
        svc = EventService(DashboardState.get())
        return StreamingResponse(
            svc.sse_generator(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @router.get("/api/events/recent")
    async def api_events_recent(limit: int = 20) -> JSONResponse:
        return JSONResponse(EventService(DashboardState.get()).get_recent_events(limit))

    @router.get("/api/timeline")
    async def api_timeline(limit: int = 20) -> JSONResponse:
        return JSONResponse(EventService(DashboardState.get()).get_timeline(limit))

    return router
