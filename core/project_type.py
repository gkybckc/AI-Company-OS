"""
Project type taxonomy for AI Company OS.

Defines the full set of project categories the Planner Engine can detect
and classify from a CEO request. Every ProjectBlueprint carries exactly
one ProjectType, which drives department selection, complexity baseline,
sprint estimation, and default recommendations.

Architecture reference: §2.1 Executive Engine, §5 Coordination Layer.
"""

from enum import Enum


class ProjectType(str, Enum):
    """
    Recognized categories of software projects.

    Each category represents a distinct class of technical work with its
    own typical department composition, risk profile, and complexity range.
    The Planner Engine uses keyword scoring to assign the most likely type
    to a CEO request.
    """

    SAAS = "SaaS"
    MOBILE_APP = "Mobile App"
    WEB_PLATFORM = "Web Platform"
    AUTOMATION = "Automation"
    DESKTOP_APP = "Desktop App"
    AI_TOOL = "AI Tool"
    API = "API"
    ECOMMERCE = "E-Commerce"
    DATA_PIPELINE = "Data Pipeline"
    GAME = "Game"

    def __str__(self) -> str:
        return self.value
