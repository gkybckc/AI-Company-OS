"""Collaboration Hub routes — /collab pages and /api/collab/* endpoints."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from apps.dashboard.services.collaboration_service import CollaborationService
from apps.dashboard.state import DashboardState
from core.collaboration.collaboration_manager import CollaborationHubError
from core.collaboration.conversation_message import MessageCategory
from core.collaboration.conversation_policy import ConversationPolicy
from core.collaboration.conversation_templates import TemplateType


def make_collaboration_router(templates: Jinja2Templates) -> APIRouter:
    router = APIRouter()

    # ------------------------------------------------------------------
    # HTML pages
    # ------------------------------------------------------------------

    @router.get("/collab", response_class=HTMLResponse)
    async def collab_hub_page(request: Request) -> HTMLResponse:
        svc = CollaborationService(DashboardState.get())
        ctx = svc.get_hub_context()
        ctx.update({"page": "collab", "company_name": "AI Company OS"})
        return templates.TemplateResponse(request, "collab/hub.html", ctx)

    @router.get("/collab/conversations", response_class=HTMLResponse)
    async def collab_conversations_page(request: Request) -> HTMLResponse:
        svc = CollaborationService(DashboardState.get())
        ctx = svc.get_conversations_context()
        ctx.update({"page": "collab_conversations", "company_name": "AI Company OS"})
        return templates.TemplateResponse(request, "collab/conversations.html", ctx)

    @router.get("/collab/sessions", response_class=HTMLResponse)
    async def collab_sessions_page(request: Request) -> HTMLResponse:
        svc = CollaborationService(DashboardState.get())
        ctx = svc.get_sessions_context()
        ctx.update({"page": "collab_sessions", "company_name": "AI Company OS"})
        return templates.TemplateResponse(request, "collab/sessions.html", ctx)

    @router.get("/collab/policies", response_class=HTMLResponse)
    async def collab_policies_page(request: Request) -> HTMLResponse:
        svc = CollaborationService(DashboardState.get())
        ctx = svc.get_policies_context()
        ctx.update({"page": "collab_policies", "company_name": "AI Company OS"})
        return templates.TemplateResponse(request, "collab/policies.html", ctx)

    # ------------------------------------------------------------------
    # Conversations API
    # ------------------------------------------------------------------

    @router.get("/api/collab/conversations")
    async def api_collab_conversations() -> JSONResponse:
        return JSONResponse(CollaborationService(DashboardState.get()).list_conversations())

    @router.get("/api/collab/conversations/{conv_id}")
    async def api_collab_conversation_detail(conv_id: str) -> JSONResponse:
        try:
            return JSONResponse(
                CollaborationService(DashboardState.get()).get_conversation(conv_id)
            )
        except CollaborationHubError as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=404)

    @router.post("/api/collab/conversations")
    async def api_collab_conversations_create(request: Request) -> JSONResponse:
        try:
            data = await request.json()
            title = data.get("title", "").strip()
            creator = data.get("creator", "ceo").strip()
            project_id = data.get("project_id") or None
            task_id = data.get("task_id") or None
            template_str = data.get("template_type", "")
            template_type = None
            if template_str:
                try:
                    template_type = TemplateType(template_str)
                except ValueError:
                    pass
            conv = CollaborationService(DashboardState.get()).create_conversation(
                title, creator, project_id, task_id, template_type
            )
            return JSONResponse({"success": True, "conversation": conv})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/collab/conversations/{conv_id}/join")
    async def api_collab_join(conv_id: str, request: Request) -> JSONResponse:
        try:
            data = await request.json()
            CollaborationService(DashboardState.get()).join_conversation(
                conv_id,
                participant_id=data.get("participant_id", "").strip(),
                name=data.get("name", data.get("participant_id", "")).strip(),
                role=data.get("role", "Agent").strip(),
                department=data.get("department", "").strip(),
            )
            return JSONResponse({"success": True})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/collab/conversations/{conv_id}/leave")
    async def api_collab_leave(conv_id: str, request: Request) -> JSONResponse:
        try:
            data = await request.json()
            CollaborationService(DashboardState.get()).leave_conversation(
                conv_id, data.get("participant_id", "").strip()
            )
            return JSONResponse({"success": True})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/collab/conversations/{conv_id}/messages")
    async def api_collab_send_message(conv_id: str, request: Request) -> JSONResponse:
        try:
            data = await request.json()
            cat_str = data.get("category", "proposal").strip()
            try:
                category = MessageCategory(cat_str)
            except ValueError:
                category = MessageCategory.PROPOSAL
            msg = CollaborationService(DashboardState.get()).send_message(
                conv_id,
                sender=data.get("sender", "").strip(),
                receiver=data.get("receiver", "all").strip() or "all",
                category=category,
                content=data.get("content", "").strip(),
            )
            return JSONResponse({"success": True, "message": msg})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/collab/conversations/{conv_id}/broadcast")
    async def api_collab_broadcast(conv_id: str, request: Request) -> JSONResponse:
        try:
            data = await request.json()
            cat_str = data.get("category", "proposal").strip()
            try:
                category = MessageCategory(cat_str)
            except ValueError:
                category = MessageCategory.PROPOSAL
            CollaborationService(DashboardState.get()).broadcast(
                conv_id,
                sender=data.get("sender", "").strip(),
                category=category,
                content=data.get("content", "").strip(),
            )
            return JSONResponse({"success": True})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/collab/conversations/{conv_id}/summarize")
    async def api_collab_summarize(conv_id: str) -> JSONResponse:
        try:
            summary = CollaborationService(DashboardState.get()).summarize(conv_id)
            return JSONResponse({"success": True, "summary": summary})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/collab/conversations/{conv_id}/close")
    async def api_collab_close(conv_id: str) -> JSONResponse:
        try:
            conv = CollaborationService(DashboardState.get()).close_conversation(conv_id)
            return JSONResponse({"success": True, "conversation": conv})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/collab/conversations/{conv_id}/request-review")
    async def api_collab_request_review(conv_id: str) -> JSONResponse:
        try:
            status = CollaborationService(DashboardState.get()).request_review(conv_id)
            return JSONResponse({"success": True, "status": status})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/collab/conversations/{conv_id}/approve")
    async def api_collab_approve(conv_id: str) -> JSONResponse:
        try:
            status = CollaborationService(DashboardState.get()).approve_conversation(conv_id)
            return JSONResponse({"success": True, "status": status})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.get("/api/collab/conversations/{conv_id}/messages")
    async def api_collab_history(conv_id: str) -> JSONResponse:
        try:
            return JSONResponse(
                CollaborationService(DashboardState.get()).get_messages(conv_id)
            )
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=404)

    @router.get("/api/collab/conversations/{conv_id}/policies")
    async def api_collab_policy_check(conv_id: str) -> JSONResponse:
        try:
            return JSONResponse(
                CollaborationService(DashboardState.get()).evaluate_policies(conv_id)
            )
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=404)

    # ------------------------------------------------------------------
    # Sessions API
    # ------------------------------------------------------------------

    @router.get("/api/collab/sessions")
    async def api_collab_sessions() -> JSONResponse:
        return JSONResponse(CollaborationService(DashboardState.get()).list_sessions())

    @router.post("/api/collab/sessions")
    async def api_collab_sessions_create(request: Request) -> JSONResponse:
        try:
            data = await request.json()
            session = CollaborationService(DashboardState.get()).create_session(
                data.get("title", "").strip(),
                data.get("project_id") or None,
                data.get("task_id") or None,
            )
            return JSONResponse({"success": True, "session": session})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/collab/sessions/{session_id}/close")
    async def api_collab_sessions_close(session_id: str) -> JSONResponse:
        try:
            session = CollaborationService(DashboardState.get()).close_session(session_id)
            return JSONResponse({"success": True, "session": session})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.post("/api/collab/sessions/{session_id}/add")
    async def api_collab_sessions_add(session_id: str, request: Request) -> JSONResponse:
        try:
            data = await request.json()
            session = CollaborationService(DashboardState.get()).add_to_session(
                session_id, data.get("conversation_id", "").strip()
            )
            return JSONResponse({"success": True, "session": session})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    # ------------------------------------------------------------------
    # Policies API
    # ------------------------------------------------------------------

    @router.get("/api/collab/policies")
    async def api_collab_policies() -> JSONResponse:
        return JSONResponse(CollaborationService(DashboardState.get()).list_policies())

    @router.post("/api/collab/policies")
    async def api_collab_policies_create(request: Request) -> JSONResponse:
        try:
            data = await request.json()
            policy = ConversationPolicy(
                name=data.get("name", "").strip(),
                description=data.get("description", "").strip(),
                trigger_role=data.get("trigger_role", "").strip(),
                trigger_category=data.get("trigger_category", "").strip(),
                required_reviewer_role=data.get("required_reviewer_role", "").strip(),
                required_response_category=data.get("required_response_category", "").strip(),
                is_blocking=bool(data.get("is_blocking", True)),
            )
            result = CollaborationService(DashboardState.get()).create_policy(policy)
            return JSONResponse({"success": True, "policy": result})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    @router.delete("/api/collab/policies/{policy_name}")
    async def api_collab_policies_delete(policy_name: str) -> JSONResponse:
        try:
            CollaborationService(DashboardState.get()).delete_policy(policy_name)
            return JSONResponse({"success": True})
        except Exception as exc:
            return JSONResponse({"success": False, "error": str(exc)}, status_code=404)

    # ------------------------------------------------------------------
    # Statistics + Templates
    # ------------------------------------------------------------------

    @router.get("/api/collab/statistics")
    async def api_collab_statistics() -> JSONResponse:
        return JSONResponse(CollaborationService(DashboardState.get()).statistics())

    @router.get("/api/collab/templates")
    async def api_collab_templates() -> JSONResponse:
        return JSONResponse(CollaborationService(DashboardState.get()).list_templates())

    return router
