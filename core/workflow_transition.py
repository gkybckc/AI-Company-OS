"""
Workflow transition model for AI Company OS.

A WorkflowTransition is an immutable record of a permitted or recorded
movement between two workflow stages. Forward transitions (advance) and
backward transitions (rollback) both produce a WorkflowTransition record
that is appended to the Workflow's transitions list.

Transitions serve a dual purpose:
  1. Audit record — the transitions list shows the exact path a workflow
     took through its stages, including any rollbacks and re-advances.
  2. Constraint declaration — transitions can carry optional conditions
     that document what must be true before the movement is allowed.
     Condition enforcement is the responsibility of the Workflow Engine.

Architecture reference: §2.7 Workflow Engine, §3 Layer 5 (Coordination Layer),
Constitution §11 (Project Principles), §10 Event Flow.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass(frozen=True)
class WorkflowTransition:
    """
    Immutable record of a movement between two workflow stages.

    Created by the Workflow Engine whenever advance() or rollback() is
    called successfully. Each instance captures the source stage, the
    destination stage, whether the transition occurred automatically or
    required manual intervention, any conditions that governed it, and the
    UTC timestamp of when it occurred.

    Attributes:
        from_stage: ID of the stage being departed.
        to_stage:   ID of the stage being entered.
        automatic:  True if the engine triggered this transition without
                    explicit operator action (reserved for future use).
                    False for all transitions initiated by advance() or
                    rollback().
        conditions: Textual descriptions of prerequisites that were
                    evaluated before this transition was allowed. Empty
                    for unconditional transitions.
        created_at: UTC timestamp of when this transition occurred.
                    Defaults to the current UTC time at construction.
    """

    from_stage: str
    to_stage: str
    automatic: bool = False
    conditions: List[str] = field(default_factory=list)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def condition_count(self) -> int:
        """Return the number of conditions listed on this transition."""
        return len(self.conditions)

    def is_unconditional(self) -> bool:
        """Return True if no conditions are listed."""
        return len(self.conditions) == 0

    def is_automatic(self) -> bool:
        """Return True if this transition was triggered automatically."""
        return self.automatic

    def is_same_transition(self, other: "WorkflowTransition") -> bool:
        """
        Return True if other describes the same from/to stage pair.

        Does not compare timestamps or conditions — only the stage IDs.
        """
        return self.from_stage == other.from_stage and self.to_stage == other.to_stage

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        """Return a compact dict representation of this transition."""
        return {
            "from_stage": self.from_stage,
            "to_stage": self.to_stage,
            "automatic": self.automatic,
            "conditions": list(self.conditions),
            "condition_count": self.condition_count(),
            "created_at": self.created_at.isoformat(),
        }
