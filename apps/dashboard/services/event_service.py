"""
Event service for the AI Company OS dashboard.

Wraps EventStream operations including SSE formatting and timeline helpers.
"""

import json
from typing import Any, AsyncGenerator, Dict, List, Optional

from apps.dashboard.state import DashboardState


# ---------------------------------------------------------------------------
# Turkish event translation helper
# ---------------------------------------------------------------------------

def human_event(action: str, payload: Dict[str, Any], source: str = "") -> str:
    """Translate a raw stream event action to a Turkish sentence."""
    _map: Dict[str, Any] = {
        "company_started":     lambda p: "Şirket başlatıldı.",
        "project_created":     lambda p: f"Yeni proje oluşturuldu: {p.get('title', '')}.",
        "employee_hired":      lambda p: f"{p.get('name', '')} işe alındı ({p.get('role', '')}).",
        "workflow_started":    lambda p: f"İş akışı başlatıldı: {p.get('name', '')}.",
        "stage_advanced":      lambda p: f"İş akışı aşaması ilerledi: {p.get('stage', '')}.",
        "discussion_started":  lambda p: f"Tartışma başlatıldı: {p.get('topic', '')}.",
        "discussion_closed":   lambda p: f"Tartışma tamamlandı: {p.get('topic', '')}.",
        "decision_created":    lambda p: f"Karar oluşturuldu: {p.get('title', '')}.",
        "decision_recommended":lambda p: f"Karar verildi: {p.get('recommendation', '')}.",
        "task_created":        lambda p: f"Görev oluşturuldu: {p.get('title', '')}.",
        "task_assigned":       lambda p: "Görev çalışana atandı.",
        "entry_stored":        lambda p: f"Hafıza kaydı oluşturuldu: {p.get('title', '')}.",
        "session_started":     lambda p: "CEO komutu işleme başlandı.",
        "session_finished":    lambda p: "CEO komutu başarıyla tamamlandı.",
        "session_failed":      lambda p: "CEO komutu başarısız oldu.",
        "department_created":  lambda p: f"Departman kuruldu: {p.get('name', '')}.",
        "workflow_advanced":   lambda p: "İş akışı bir sonraki aşamaya geçti.",
        "workflow_completed":  lambda p: "İş akışı tamamlandı.",
        "agent_started":       lambda p: f"Ajan başlatıldı: {p.get('name', '')}.",
        "discussion_posted":   lambda p: "Tartışmaya yeni mesaj eklendi.",
        "task_completed":      lambda p: f"Görev tamamlandı: {p.get('title', '')}.",
        "project_completed":   lambda p: f"Proje tamamlandı: {p.get('title', '')}.",
        "employee_promoted":   lambda p: f"{p.get('name', '')} terfi etti.",
    }
    fn = _map.get(action)
    if fn:
        return fn(payload)
    if action:
        return f"Sistem olayı: {action.replace('_', ' ')}."
    return "Sistem olayı."


class EventService:
    """Service layer over EventStream for dashboard route handlers."""

    def __init__(self, state: DashboardState) -> None:
        self._state = state

    @property
    def _stream(self):
        return self._state.event_stream

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_recent_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        events = self._stream.history(limit=limit)
        result = []
        for e in reversed(events):
            action = e.get_payload_value("action", "")
            result.append(
                {
                    "id": e.id,
                    "source": e.source,
                    "channel": str(e.category),
                    "timestamp": e.timestamp.isoformat(),
                    "payload": e.payload,
                    "action": action,
                    "sentence": human_event(action, e.payload, e.source),
                }
            )
        return result

    def get_timeline(self, limit: int = 20) -> List[Dict[str, Any]]:
        events = self._stream.history(limit=limit)
        result = []
        for ev in reversed(events):
            action = ev.payload.get("action", "")
            result.append(
                {
                    "id": ev.id,
                    "source": ev.source,
                    "channel": str(ev.category),
                    "timestamp": ev.timestamp.isoformat(),
                    "timestamp_hms": ev.timestamp.strftime("%H:%M"),
                    "sentence": human_event(action, ev.payload, ev.source),
                    "action": action,
                }
            )
        return result

    def get_events_page_data(self) -> Dict[str, Any]:
        raw_events = list(reversed(self._stream.history()))
        events_with_sentences = []
        for ev in raw_events[:50]:
            action = ev.payload.get("action", "")
            events_with_sentences.append(
                {
                    "event": ev,
                    "sentence": human_event(action, ev.payload, ev.source),
                }
            )
        return {
            "events_with_sentences": events_with_sentences,
            "ev_stats": self._state.get_event_stats(),
            "timeline": self.get_timeline(limit=20),
        }

    def get_statistics(self) -> Dict[str, Any]:
        raw = self._stream.statistics()
        # Expose by_channel as an alias for events_by_channel for convenience
        result = dict(raw)
        result["by_channel"] = raw.get("events_by_channel", {})
        return result

    # ------------------------------------------------------------------
    # SSE stream generator
    # ------------------------------------------------------------------

    async def sse_generator(self, request: Any) -> AsyncGenerator[str, None]:
        """
        Async generator that yields SSE-formatted strings.

        Polls the EventStream for new events every second and pushes them
        to connected clients.  Sends a keepalive heartbeat comment when
        there are no new events to prevent proxy timeout.
        """
        import asyncio

        last_count = self._stream.event_count()

        # Connection confirmation event
        yield "data: " + json.dumps({"type": "connected"}) + "\n\n"

        while True:
            if await request.is_disconnected():
                break

            await asyncio.sleep(1)

            events = self._stream.history()
            current_count = len(events)

            if current_count > last_count:
                new_events = events[last_count:]
                for ev in new_events:
                    action = ev.payload.get("action", "")
                    data = {
                        "type": "event",
                        "id": ev.id,
                        "source": ev.source,
                        "channel": str(ev.category),
                        "timestamp": ev.timestamp.isoformat(),
                        "timestamp_hms": ev.timestamp.strftime("%H:%M"),
                        "action": action,
                        "sentence": human_event(action, ev.payload, ev.source),
                        "payload": ev.payload,
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                last_count = current_count
            else:
                yield ": heartbeat\n\n"
