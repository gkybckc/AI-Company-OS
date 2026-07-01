"""
Workflow domain model for AI Company OS.

Defines the Workflow mutable record together with the WorkflowStatus and
WorkflowEventType enumerations that govern its lifecycle, and the
WorkflowEvent immutable record that captures every observable step the
Workflow Engine takes.

A Workflow progresses through statuses: PENDING → ACTIVE → (PAUSED →
ACTIVE →) COMPLETED | CANCELLED | FAILED. Every status transition and
every stage transition emits a WorkflowEvent that is appended to the
workflow's append-only event log.

Architecture reference: §2.7 Workflow Engine, §3 Layer 5 (Coordination
Layer), §10 Event Flow, Constitution §11 (Project Principles).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from core.workflow_stage import WorkflowStage
from core.workflow_transition import WorkflowTransition
from core.workflow_template import WorkflowTemplate


# ---------------------------------------------------------------------------
# WorkflowStatus
# ---------------------------------------------------------------------------

class WorkflowStatus(str, Enum):
    """
    Lifecycle status of a Workflow managed by the Workflow Engine.

    Transitions:
        PENDING   → ACTIVE     via start()
        ACTIVE    → PAUSED     via pause()
        ACTIVE    → COMPLETED  via complete()
        ACTIVE    → CANCELLED  via cancel()
        ACTIVE    → FAILED     (internal engine failure path)
        PAUSED    → ACTIVE     via resume()
        PAUSED    → CANCELLED  via cancel()

    Terminal statuses: COMPLETED, CANCELLED, FAILED. No transitions are
    permitted from these statuses.
    """

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"

    def __str__(self) -> str:
        return self.value

    def is_terminal(self) -> bool:
        """Return True if the workflow has reached a final, unchangeable state."""
        return self in {
            WorkflowStatus.COMPLETED,
            WorkflowStatus.CANCELLED,
            WorkflowStatus.FAILED,
        }

    def is_running(self) -> bool:
        """Return True if the workflow is currently being worked on (ACTIVE)."""
        return self == WorkflowStatus.ACTIVE

    def is_paused(self) -> bool:
        """Return True if the workflow has been temporarily suspended."""
        return self == WorkflowStatus.PAUSED

    def is_pending(self) -> bool:
        """Return True if the workflow has not yet been started."""
        return self == WorkflowStatus.PENDING

    def can_advance(self) -> bool:
        """Return True if stage transitions (advance/rollback) are permitted."""
        return self == WorkflowStatus.ACTIVE

    def can_pause(self) -> bool:
        """Return True if the workflow may be paused."""
        return self == WorkflowStatus.ACTIVE

    def can_resume(self) -> bool:
        """Return True if the workflow may be resumed."""
        return self == WorkflowStatus.PAUSED


# ---------------------------------------------------------------------------
# WorkflowEventType
# ---------------------------------------------------------------------------

class WorkflowEventType(str, Enum):
    """
    All observable event types emitted by the Workflow Engine.

    Workflow lifecycle events:
        WORKFLOW_CREATED   — create_workflow() called successfully.
        WORKFLOW_STARTED   — start() called; first stage entered.
        WORKFLOW_PAUSED    — pause() called; work suspended.
        WORKFLOW_RESUMED   — resume() called; work restarted.
        WORKFLOW_COMPLETED — complete() called; all stages done.
        WORKFLOW_CANCELLED — cancel() called; workflow abandoned.
        WORKFLOW_FAILED    — Internal failure recorded.

    Stage events (emitted on every stage transition):
        STAGE_STARTED      — A stage became active.
        STAGE_COMPLETED    — A stage was advanced past.
        STAGE_ROLLED_BACK  — A stage was undone via rollback().
        STAGE_TRANSITION   — Records the from/to pair of a transition.
    """

    WORKFLOW_CREATED = "WORKFLOW_CREATED"
    WORKFLOW_STARTED = "WORKFLOW_STARTED"
    WORKFLOW_PAUSED = "WORKFLOW_PAUSED"
    WORKFLOW_RESUMED = "WORKFLOW_RESUMED"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"
    WORKFLOW_CANCELLED = "WORKFLOW_CANCELLED"
    WORKFLOW_FAILED = "WORKFLOW_FAILED"
    STAGE_STARTED = "STAGE_STARTED"
    STAGE_COMPLETED = "STAGE_COMPLETED"
    STAGE_ROLLED_BACK = "STAGE_ROLLED_BACK"
    STAGE_TRANSITION = "STAGE_TRANSITION"

    def __str__(self) -> str:
        return self.value

    def is_workflow_lifecycle(self) -> bool:
        """Return True if this event describes a workflow-level status change."""
        return self in {
            WorkflowEventType.WORKFLOW_CREATED,
            WorkflowEventType.WORKFLOW_STARTED,
            WorkflowEventType.WORKFLOW_PAUSED,
            WorkflowEventType.WORKFLOW_RESUMED,
            WorkflowEventType.WORKFLOW_COMPLETED,
            WorkflowEventType.WORKFLOW_CANCELLED,
            WorkflowEventType.WORKFLOW_FAILED,
        }

    def is_stage_event(self) -> bool:
        """Return True if this event describes a stage-level occurrence."""
        return self in {
            WorkflowEventType.STAGE_STARTED,
            WorkflowEventType.STAGE_COMPLETED,
            WorkflowEventType.STAGE_ROLLED_BACK,
            WorkflowEventType.STAGE_TRANSITION,
        }

    def is_terminal(self) -> bool:
        """Return True if this event marks the end of a workflow."""
        return self in {
            WorkflowEventType.WORKFLOW_COMPLETED,
            WorkflowEventType.WORKFLOW_CANCELLED,
            WorkflowEventType.WORKFLOW_FAILED,
        }


# ---------------------------------------------------------------------------
# WorkflowEvent
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WorkflowEvent:
    """
    Immutable record of a single observable step performed by the engine.

    Every status transition and stage transition that the Workflow Engine
    performs is captured as a WorkflowEvent and appended to the owning
    Workflow's events list. Events are never modified or removed.

    Attributes:
        id:          Unique identifier (UUID string).
        event_type:  Category of the event.
        workflow_id: ID of the workflow this event belongs to.
        timestamp:   UTC timestamp of when this event was emitted.
        stage_id:    ID of the stage this event relates to. None for
                     workflow-lifecycle events that are not stage-specific.
        payload:     Optional step-specific detail. Always a dict;
                     empty for events with no additional context.
    """

    id: str
    event_type: WorkflowEventType
    workflow_id: str
    timestamp: datetime
    stage_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        event_type: WorkflowEventType,
        workflow_id: str,
        stage_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> "WorkflowEvent":
        """
        Factory method producing a new WorkflowEvent with a generated ID
        and the current UTC timestamp.

        Args:
            event_type:  The type of event to record.
            workflow_id: ID of the workflow this event belongs to.
            stage_id:    Optional stage this event relates to.
            payload:     Optional payload dict. Defaults to empty dict.

        Returns:
            A new, immutable WorkflowEvent.
        """
        return cls(
            id=str(uuid4()),
            event_type=event_type,
            workflow_id=workflow_id,
            timestamp=datetime.now(timezone.utc),
            stage_id=stage_id,
            payload=payload or {},
        )

    def is_terminal(self) -> bool:
        """Delegate to event_type.is_terminal()."""
        return self.event_type.is_terminal()

    def get_payload_value(self, key: str, default: Any = None) -> Any:
        """Return a value from the payload by key, or default."""
        return self.payload.get(key, default)


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

@dataclass
class Workflow:
    """
    Mutable record representing one workflow instance managed by the engine.

    A Workflow is created by WorkflowEngine.create_workflow() and
    progressed through its lifecycle by the engine's methods. External
    code reads workflow state through the engine's query methods or by
    inspecting the returned Workflow object directly.

    The stages list contains all WorkflowStage objects in their defined
    order. The completed_stages list accumulates stages as advance() is
    called. current_stage holds the stage actively being worked on.
    transitions records every stage movement (forward and backward).
    events is the append-only event log.

    Attributes:
        id:               Unique identifier (UUID string).
        name:             Human-readable workflow name.
        description:      Description of what this workflow achieves.
        template:         The template this workflow was created from.
        stages:           Ordered list of all stages (sorted by order).
        status:           Current lifecycle status.
        progress:         Float in [0.0, 1.0] — ratio of completed stages
                          to total stages.
        created_at:       UTC timestamp of workflow creation.
        updated_at:       UTC timestamp of the most recent state change.
        current_stage:    The stage currently being worked on. None when
                          PENDING or after COMPLETED/CANCELLED/FAILED.
        completed_stages: Stages that have been advanced past, in order.
        events:           Append-only ordered log of WorkflowEvents.
        transitions:      Ordered log of WorkflowTransitions recorded.
    """

    id: str
    name: str
    description: str
    template: WorkflowTemplate
    stages: List[WorkflowStage]
    status: WorkflowStatus
    progress: float
    created_at: datetime
    updated_at: datetime
    current_stage: Optional[WorkflowStage] = None
    completed_stages: List[WorkflowStage] = field(default_factory=list)
    events: List[WorkflowEvent] = field(default_factory=list)
    transitions: List[WorkflowTransition] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Stage navigation
    # ------------------------------------------------------------------

    def get_stage_by_order(self, order: int) -> Optional[WorkflowStage]:
        """Return the stage with the given order value, or None."""
        for s in self.stages:
            if s.order == order:
                return s
        return None

    def get_stage_by_id(self, stage_id: str) -> Optional[WorkflowStage]:
        """Return the stage with the given ID, or None."""
        for s in self.stages:
            if s.id == stage_id:
                return s
        return None

    def next_stage(self) -> Optional[WorkflowStage]:
        """
        Return the stage immediately after current_stage by order.

        Returns None if current_stage is None (not started or completed)
        or if current_stage is the last stage.
        """
        if self.current_stage is None:
            return None
        return self.get_stage_by_order(self.current_stage.order + 1)

    def previous_stage(self) -> Optional[WorkflowStage]:
        """
        Return the stage immediately before current_stage by order.

        Returns None if current_stage is None or is the first stage.
        """
        if self.current_stage is None:
            return None
        if self.current_stage.order <= 1:
            return None
        return self.get_stage_by_order(self.current_stage.order - 1)

    def first_stage(self) -> Optional[WorkflowStage]:
        """Return the stage with order=1, or None if no stages exist."""
        return self.get_stage_by_order(1)

    def last_stage(self) -> Optional[WorkflowStage]:
        """Return the stage with the highest order value."""
        if not self.stages:
            return None
        return max(self.stages, key=lambda s: s.order)

    # ------------------------------------------------------------------
    # Count helpers
    # ------------------------------------------------------------------

    def stage_count(self) -> int:
        """Return the total number of stages in this workflow."""
        return len(self.stages)

    def completed_stage_count(self) -> int:
        """Return the number of stages that have been advanced past."""
        return len(self.completed_stages)

    def remaining_stage_count(self) -> int:
        """Return the number of stages not yet completed."""
        return self.stage_count() - self.completed_stage_count()

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------

    def is_pending(self) -> bool:
        """Return True if the workflow has not yet been started."""
        return self.status == WorkflowStatus.PENDING

    def is_active(self) -> bool:
        """Return True if the workflow is currently running."""
        return self.status == WorkflowStatus.ACTIVE

    def is_paused(self) -> bool:
        """Return True if the workflow is temporarily suspended."""
        return self.status == WorkflowStatus.PAUSED

    def is_completed(self) -> bool:
        """Return True if all stages have been completed."""
        return self.status == WorkflowStatus.COMPLETED

    def is_cancelled(self) -> bool:
        """Return True if the workflow was cancelled."""
        return self.status == WorkflowStatus.CANCELLED

    def is_failed(self) -> bool:
        """Return True if the workflow failed."""
        return self.status == WorkflowStatus.FAILED

    def is_terminal(self) -> bool:
        """Return True if the workflow is in a terminal state."""
        return self.status.is_terminal()

    # ------------------------------------------------------------------
    # Event helpers
    # ------------------------------------------------------------------

    def add_event(self, event: WorkflowEvent) -> None:
        """Append a WorkflowEvent to the append-only event log."""
        self.events.append(event)

    def event_count(self) -> int:
        """Return the total number of events recorded."""
        return len(self.events)

    def events_of_type(
        self, event_type: WorkflowEventType
    ) -> List[WorkflowEvent]:
        """Return all events matching the given event type."""
        return [e for e in self.events if e.event_type == event_type]

    def last_event(self) -> Optional[WorkflowEvent]:
        """Return the most recent event, or None if none exist."""
        return self.events[-1] if self.events else None

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        """Return a compact dict suitable for reports and status checks."""
        return {
            "id": self.id,
            "name": self.name,
            "template": str(self.template),
            "status": str(self.status),
            "progress": self.progress,
            "stage_count": self.stage_count(),
            "completed_stage_count": self.completed_stage_count(),
            "remaining_stage_count": self.remaining_stage_count(),
            "current_stage": (
                self.current_stage.name if self.current_stage else None
            ),
            "event_count": self.event_count(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
