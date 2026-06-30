"""
Company session model for AI Company OS.

A CompanySession is the full record of one CEO request from the moment
it is accepted to the moment it is resolved (finished or failed). It acts
as the audit trail for that request: every significant step is recorded
as a CompanyEvent in the session's event log, and every artifact produced
(blueprint, project, tasks, discussions, runtime sessions) is attached to
the session record.

Sessions are created by the Company Orchestrator's new_request() method
and progressed through stages by the orchestrator's internal pipeline.
External code reads session state through the orchestrator's query methods.

Architecture reference: §2.1 Executive Engine, §7.5 Project Memory,
§10 Event Flow, §11 Task Lifecycle.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from core.company_event import CompanyEvent
from core.discussion import Discussion
from core.project import Project
from core.project_blueprint import ProjectBlueprint
from core.task import Task


class SessionStage(str, Enum):
    """
    Ordered lifecycle stages of a CompanySession.

    Each stage represents a distinct phase in the orchestration pipeline.
    The Company Orchestrator advances the session through these stages
    in order; it may skip DISCUSSING if no discussion is required.

    CREATED   — Session record created. No processing has started.
    ANALYZING — PlannerEngine is analyzing the CEO's request.
    PLANNING  — ExecutiveEngine is creating the project, departments,
                employees, and tasks based on the blueprint.
    EXECUTING — AgentRuntime sessions are being started for assigned
                employees. Work has begun.
    DISCUSSING — A DiscussionEngine discussion is in progress.
    FINISHED  — All orchestration steps completed successfully.
    FAILED    — The orchestration encountered an unrecoverable error.
                error_message contains the failure reason.
    """

    CREATED = "CREATED"
    ANALYZING = "ANALYZING"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    DISCUSSING = "DISCUSSING"
    FINISHED = "FINISHED"
    FAILED = "FAILED"

    def __str__(self) -> str:
        return self.value

    def is_terminal(self) -> bool:
        """Return True if the session has reached a final state."""
        return self in {SessionStage.FINISHED, SessionStage.FAILED}

    def is_active(self) -> bool:
        """Return True if the session is still being processed."""
        return not self.is_terminal()


@dataclass
class CompanySession:
    """
    Complete record of one CEO request and its orchestration results.

    Created by the Company Orchestrator when new_request() is called.
    Progressed through stages by the orchestrator's pipeline. Contains all
    artifacts produced during the request and the ordered event log.

    The session is mutable during orchestration — the orchestrator updates
    current_stage, appends events, and attaches artifacts as the pipeline
    progresses. Once the session reaches a terminal stage (FINISHED or
    FAILED), it is immutable by convention.

    Attributes:
        id: Unique identifier (UUID string). Assigned by the orchestrator.
        request: The original CEO request string. Preserved verbatim.
        current_stage: The stage the session is currently in or last
            reached. Advances as the orchestrator pipeline progresses.
        created_at: UTC timestamp of when this session was created.
        finished_at: UTC timestamp of when the session reached a terminal
            stage. None while the session is active.
        blueprint: The ProjectBlueprint produced by the PlannerEngine
            during the ANALYZING stage. None until that stage completes.
        project: The Project created by the ExecutiveEngine during the
            PLANNING stage. None until that stage completes.
        created_tasks: Ordered list of Task records created for this
            request. Appended in the PLANNING stage.
        started_runtimes: IDs of AgentRuntime sessions started during
            the EXECUTING stage, one per assigned employee.
        discussions: Discussion records created by the DiscussionEngine
            during the DISCUSSING stage. Appended as discussions are opened.
        events: Ordered, append-only log of all CompanyEvents emitted
            during this session. The authoritative history of what the
            orchestrator did for this request.
        error_message: Human-readable description of the failure if the
            session reached FAILED state. None for successful sessions.
    """

    id: str
    request: str
    current_stage: SessionStage
    created_at: datetime
    finished_at: Optional[datetime] = None
    blueprint: Optional[ProjectBlueprint] = None
    project: Optional[Project] = None
    created_tasks: List[Task] = field(default_factory=list)
    started_runtimes: List[str] = field(default_factory=list)
    discussions: List[Discussion] = field(default_factory=list)
    events: List[CompanyEvent] = field(default_factory=list)
    error_message: Optional[str] = None

    # ------------------------------------------------------------------
    # Stage helpers
    # ------------------------------------------------------------------

    def is_active(self) -> bool:
        """Return True if the session has not yet reached a terminal stage."""
        return self.current_stage.is_active()

    def is_finished(self) -> bool:
        """Return True if the session completed successfully."""
        return self.current_stage == SessionStage.FINISHED

    def is_failed(self) -> bool:
        """Return True if the session terminated with a failure."""
        return self.current_stage == SessionStage.FAILED

    # ------------------------------------------------------------------
    # Event helpers
    # ------------------------------------------------------------------

    def add_event(self, event: CompanyEvent) -> None:
        """
        Append a CompanyEvent to the session's event log.

        This is the only way events should be added. The orchestrator calls
        this method whenever it completes a step.

        Args:
            event: The event to append.
        """
        self.events.append(event)

    def event_count(self) -> int:
        """Return the total number of events recorded so far."""
        return len(self.events)

    def events_of_type(self, event_type: Any) -> List[CompanyEvent]:
        """
        Return all events matching the given event type.

        Args:
            event_type: A CompanyEventType value to filter by.

        Returns:
            Ordered list of matching events.
        """
        return [e for e in self.events if e.event_type == event_type]

    def last_event(self) -> Optional[CompanyEvent]:
        """Return the most recent event, or None if no events exist."""
        return self.events[-1] if self.events else None

    # ------------------------------------------------------------------
    # Artifact helpers
    # ------------------------------------------------------------------

    def task_count(self) -> int:
        """Return the number of tasks created for this session."""
        return len(self.created_tasks)

    def runtime_count(self) -> int:
        """Return the number of AgentRuntime sessions started."""
        return len(self.started_runtimes)

    def discussion_count(self) -> int:
        """Return the number of discussions opened during this session."""
        return len(self.discussions)

    def has_blueprint(self) -> bool:
        """Return True if a ProjectBlueprint was produced."""
        return self.blueprint is not None

    def has_project(self) -> bool:
        """Return True if a Project was created."""
        return self.project is not None

    def duration_seconds(self) -> Optional[float]:
        """
        Return the total duration of this session in seconds.

        Returns the time from created_at to finished_at for terminal
        sessions, or None if the session is still active.

        Returns:
            Float seconds, or None if not yet finished.
        """
        if self.finished_at is None:
            return None
        return (self.finished_at - self.created_at).total_seconds()

    def summary(self) -> Dict[str, Any]:
        """
        Return a human-readable summary dict of the session's state.

        Returns:
            Dict with keys: id, request_preview, stage, tasks, runtimes,
            discussions, events, finished, error.
        """
        return {
            "id": self.id,
            "request_preview": self.request[:60] + ("..." if len(self.request) > 60 else ""),
            "stage": str(self.current_stage),
            "tasks": self.task_count(),
            "runtimes": self.runtime_count(),
            "discussions": self.discussion_count(),
            "events": self.event_count(),
            "finished": self.is_finished(),
            "error": self.error_message,
        }
