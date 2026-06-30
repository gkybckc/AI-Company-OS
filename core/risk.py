"""
Risk model for AI Company OS.

Defines the risk taxonomy used by the Planner Engine when performing
deterministic risk analysis on a CEO request. Every Risk is immutable
once created — it is a finding produced during planning, not a mutable
tracking record.

Architecture reference: §2.1 Executive Engine, §12 Failure Recovery.
"""

from dataclasses import dataclass
from enum import Enum


class RiskLevel(str, Enum):
    """
    Severity classification for a detected risk.

    Levels are ordered from least to most severe:
        LOW → MEDIUM → HIGH → CRITICAL

    CRITICAL risks must be addressed in the project blueprint before work
    begins. HIGH risks require explicit mitigation plans. MEDIUM risks are
    monitored. LOW risks are noted for awareness.
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    def __str__(self) -> str:
        return self.value


class RiskCategory(str, Enum):
    """
    Technical domain categories for risks identified by the Planner Engine.

    Each category corresponds to a class of engineering challenge that
    consistently introduces complexity, cost, or failure modes when not
    addressed deliberately at the planning stage.
    """

    AUTHENTICATION = "Authentication"
    PAYMENTS = "Payments"
    REAL_TIME = "Real-Time"
    NOTIFICATIONS = "Notifications"
    MAPS = "Maps"
    AI_INTEGRATION = "AI Integration"
    SCALING = "Scaling"
    VIDEO_STREAMING = "Video Streaming"
    DATA_PRIVACY = "Data Privacy"
    FILE_STORAGE = "File Storage"
    THIRD_PARTY_INTEGRATIONS = "Third-Party Integrations"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Risk:
    """
    Immutable record of a single risk identified during project analysis.

    Produced by the Planner Engine's deterministic risk analysis and stored
    in the ProjectBlueprint. Risks are findings — they describe what has
    been detected, not what should be done (recommendations are stored
    separately in the blueprint).

    Attributes:
        category: The technical domain this risk belongs to.
        level: The severity classification of this risk.
        description: A concise, accurate description of why this risk exists
            and what engineering challenges it introduces.
    """

    category: RiskCategory
    level: RiskLevel
    description: str
