"""
Artifact Registry for AI Company OS.

The ArtifactRegistry is an in-memory store for Artifact instances generated
by the ArtifactEngine. It supports O(1) lookup by ID and linear-time
filtering by artifact type, project, and generating component.
"""

from typing import Any, Dict, List

from core.artifact import Artifact
from core.artifact_type import ArtifactType


class ArtifactRegistryError(Exception):
    """Base class for all ArtifactRegistry errors."""


class ArtifactNotFoundError(ArtifactRegistryError):
    """Raised when an artifact ID cannot be resolved in the registry."""


class DuplicateArtifactError(ArtifactRegistryError):
    """Raised when an artifact with the same ID is registered twice."""


class ArtifactRegistry:
    """
    In-memory store for generated Artifact instances.

    Maintains insertion order for list_all() and history-style operations.
    All filtering methods return lists ordered by registration time.
    """

    def __init__(self) -> None:
        self._artifacts: Dict[str, Artifact] = {}

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def register(self, artifact: Artifact) -> Artifact:
        """
        Register an artifact.

        Args:
            artifact: The Artifact instance to store.

        Returns:
            The same Artifact (for chaining).

        Raises:
            DuplicateArtifactError: If artifact.id is already registered.
        """
        if artifact.id in self._artifacts:
            raise DuplicateArtifactError(
                f"Artifact '{artifact.id}' is already registered."
            )
        self._artifacts[artifact.id] = artifact
        return artifact

    def remove(self, artifact_id: str) -> Artifact:
        """
        Remove and return an artifact by ID.

        Args:
            artifact_id: ID of the artifact to remove.

        Returns:
            The removed Artifact.

        Raises:
            ArtifactNotFoundError: If the ID is not in the registry.
        """
        if artifact_id not in self._artifacts:
            raise ArtifactNotFoundError(
                f"Artifact '{artifact_id}' not found in registry."
            )
        return self._artifacts.pop(artifact_id)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, artifact_id: str) -> Artifact:
        """
        Retrieve an artifact by ID.

        Args:
            artifact_id: ID to look up.

        Returns:
            The matching Artifact.

        Raises:
            ArtifactNotFoundError: If the ID is not in the registry.
        """
        if artifact_id not in self._artifacts:
            raise ArtifactNotFoundError(
                f"Artifact '{artifact_id}' not found in registry."
            )
        return self._artifacts[artifact_id]

    def has(self, artifact_id: str) -> bool:
        """Return True if artifact_id is present in the registry."""
        return artifact_id in self._artifacts

    def find_by_type(self, artifact_type: ArtifactType) -> List[Artifact]:
        """Return all artifacts of the given type, in registration order."""
        return [a for a in self._artifacts.values() if a.type == artifact_type]

    def find_by_project(self, project_id: str) -> List[Artifact]:
        """Return all artifacts for the given project, in registration order."""
        return [a for a in self._artifacts.values() if a.project_id == project_id]

    def find_by_generated_by(self, generated_by: str) -> List[Artifact]:
        """Return all artifacts produced by the named component."""
        return [a for a in self._artifacts.values() if a.generated_by == generated_by]

    def list_all(self) -> List[Artifact]:
        """Return all registered artifacts in registration order."""
        return list(self._artifacts.values())

    # ------------------------------------------------------------------
    # Aggregates
    # ------------------------------------------------------------------

    def count(self) -> int:
        """Return the total number of registered artifacts."""
        return len(self._artifacts)

    def statistics(self) -> Dict[str, Any]:
        """Return a summary of registry contents."""
        type_counts: Dict[str, int] = {t.value: 0 for t in ArtifactType}
        project_ids: set = set()
        generators: set = set()

        for a in self._artifacts.values():
            type_counts[a.type.value] += 1
            if a.project_id:
                project_ids.add(a.project_id)
            generators.add(a.generated_by)

        return {
            "total_artifacts": self.count(),
            "type_counts": type_counts,
            "unique_projects": len(project_ids),
            "unique_generators": len(generators),
        }
