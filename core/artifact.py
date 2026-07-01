"""
Artifact model for AI Company OS.

An Artifact is a versioned, structured document produced deterministically
by the ArtifactEngine from current company state. Once created, an Artifact
is an immutable record of what the engine computed at a given point in time.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from core.artifact_type import ArtifactType


@dataclass
class Artifact:
    """
    A structured document generated deterministically from company state.

    Attributes:
        id:           Unique identifier (UUID string).
        title:        Short descriptive title of the artifact.
        type:         Document type classification.
        project_id:   ID of the project this artifact belongs to, or None
                      for company-wide artifacts such as CEO_REPORT.
        generated_by: Name of the engine or component that created it.
        content:      Full Markdown-formatted document body.
        created_at:   UTC timestamp of generation.
        version:      Monotonically increasing version counter per
                      (project_id, type) pair. Starts at 1.
    """

    id: str
    title: str
    type: ArtifactType
    project_id: Optional[str]
    generated_by: str
    content: str
    created_at: datetime
    version: int = 1

    def word_count(self) -> int:
        """Return the number of whitespace-delimited tokens in the content."""
        return len(self.content.split())

    def line_count(self) -> int:
        """Return the number of lines in the content."""
        return len(self.content.splitlines())

    def summary(self) -> Dict[str, Any]:
        """Return a lightweight dictionary summary suitable for display."""
        return {
            "id": self.id,
            "title": self.title,
            "type": str(self.type),
            "project_id": self.project_id,
            "generated_by": self.generated_by,
            "version": self.version,
            "word_count": self.word_count(),
            "line_count": self.line_count(),
            "created_at": self.created_at.isoformat(),
        }

    def is_for_project(self, project_id: str) -> bool:
        """Return True when this artifact belongs to the given project."""
        return self.project_id == project_id
