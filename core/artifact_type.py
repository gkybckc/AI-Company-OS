"""
Artifact type enumeration for AI Company OS.

Defines the eight classes of structured document artifacts that the
ArtifactEngine can generate deterministically from company state.
"""

from enum import Enum


class ArtifactType(str, Enum):
    """
    Classifies the document type of a generated Artifact.

    Each type maps to a distinct document class with its own schema,
    sections, and intended audience.
    """

    PRD = "PRD"
    TECHNICAL_SPECIFICATION = "TECHNICAL_SPECIFICATION"
    API_SPECIFICATION = "API_SPECIFICATION"
    DATABASE_SCHEMA = "DATABASE_SCHEMA"
    PROJECT_STRUCTURE = "PROJECT_STRUCTURE"
    TASK_REPORT = "TASK_REPORT"
    CEO_REPORT = "CEO_REPORT"
    SPRINT_REPORT = "SPRINT_REPORT"

    def __str__(self) -> str:
        return self.value

    def label(self) -> str:
        """Return a human-readable document label for this artifact type."""
        _labels = {
            ArtifactType.PRD: "Product Requirements Document",
            ArtifactType.TECHNICAL_SPECIFICATION: "Technical Specification",
            ArtifactType.API_SPECIFICATION: "API Specification",
            ArtifactType.DATABASE_SCHEMA: "Database Schema",
            ArtifactType.PROJECT_STRUCTURE: "Project Structure",
            ArtifactType.TASK_REPORT: "Task Report",
            ArtifactType.CEO_REPORT: "CEO Report",
            ArtifactType.SPRINT_REPORT: "Sprint Report",
        }
        return _labels[self]
