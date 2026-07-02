"""Artifact routes — /api/artifacts list and download."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response

from apps.dashboard.services.artifact_service import ArtifactService
from apps.dashboard.state import DashboardState


def make_artifacts_router() -> APIRouter:
    router = APIRouter()

    @router.get("/api/artifacts")
    async def api_artifacts() -> JSONResponse:
        return JSONResponse(ArtifactService(DashboardState.get()).list_artifacts_api())

    @router.get("/api/artifacts/{artifact_id}/download")
    async def api_artifact_download(artifact_id: str) -> Response:
        svc = ArtifactService(DashboardState.get())
        try:
            content, safe_title = svc.get_download(artifact_id)
        except Exception:
            return JSONResponse({"error": "Artifact bulunamadi."}, status_code=404)
        return Response(
            content=content,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_title}.md"'
            },
        )

    return router
