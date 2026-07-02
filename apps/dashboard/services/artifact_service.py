"""
Artifact service for the AI Company OS dashboard.

Wraps ArtifactEngine operations for artifact route handlers.
"""

from typing import Any, Dict, List, Tuple

from apps.dashboard.state import DashboardState


class ArtifactService:
    """Service layer over ArtifactEngine for dashboard route handlers."""

    def __init__(self, state: DashboardState) -> None:
        self._state = state

    def list_artifacts(self) -> List[Any]:
        return self._state.list_artifacts()

    def list_artifacts_api(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": a.id,
                "title": a.title,
                "type": a.type.value,
                "version": a.version,
                "word_count": a.word_count(),
                "generated_by": a.generated_by,
                "created_at": a.created_at.isoformat(),
                "project_id": a.project_id,
            }
            for a in self._state.list_artifacts()
        ]

    def find_artifact(self, artifact_id: str) -> Any:
        return self._state.artifact_engine.find_artifact(artifact_id)

    def get_download(self, artifact_id: str) -> Tuple[str, str]:
        """Return (content, safe_title) for artifact download."""
        artifact = self._state.artifact_engine.find_artifact(artifact_id)
        safe_title = artifact.title.replace("/", "-").replace("\\", "-")
        return artifact.content, safe_title
