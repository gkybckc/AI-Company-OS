"""
Collaboration request model for AI Company OS.

A CollaborationRequest is the formal record of one inter-agent
collaboration request. It is produced by CollaborationManager.create_request()
and is immutable from the moment of creation — the fields capture the
exact intent of the requester at the moment the request was submitted.

Requests do not carry their own status. The CollaborationManager is the
sole owner of request lifecycle state; callers observe status through
the manager's query methods (list_pending(), list_completed(), etc.).

Architecture reference: §2.6 Communication Model, §3 Layer 3 (Infrastructure),
constitution Chapter 14 (Collaboration protocols).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.collaboration_type import CollaborationType


@dataclass(frozen=True)
class CollaborationRequest:
    """
    Immutable record of a single inter-agent collaboration request.

    Created by CollaborationManager.create_request(). The manager assigns
    the id and created_at; all other fields are provided by the caller.

    Attributes:
        id: Unique identifier for this request (UUID string). Assigned
            by the manager at creation time. Never changes.
        requester: Identifier of the agent, component, or session that
            initiated the request (e.g., employee ID, runtime session ID,
            or a named subsystem like "executive_engine").
        target: Identifier of the agent, component, or subsystem that
            should respond to this request. May be a specific agent ID,
            a role (e.g., "director:backend"), or a subsystem name
            (e.g., "memory_engine", "approval_engine").
        project_id: Optional identifier of the project this collaboration
            is associated with. None for collaboration not tied to a
            specific project.
        task_id: Optional identifier of the task that triggered this
            collaboration. None for collaboration originating outside
            of a task context.
        collaboration_type: The category of collaboration being requested.
            Determines which engine (if any) will process it in future sprints.
        priority: Integer priority in the range [1, 5]. 1 is the highest
            priority (most urgent). 5 is the lowest (background). The
            manager uses priority to order list_pending() results.
        message: The human-readable content of the request. The exact
            format and schema depend on the collaboration_type. For
            APPROVAL requests this describes what is being submitted for
            approval; for MEMORY_LOOKUP it describes what is being queried;
            for DISCUSSION it frames the question; for INFORMATION_REQUEST
            it states what data is needed.
        created_at: UTC timestamp of when this request was created.
            Assigned by the manager.
    """

    id: str
    requester: str
    target: str
    project_id: Optional[str]
    task_id: Optional[str]
    collaboration_type: CollaborationType
    priority: int
    message: str
    created_at: datetime

    def is_high_priority(self) -> bool:
        """
        Return True if this request has the highest priority level.

        Returns:
            True if priority == 1.
        """
        return self.priority == 1

    def is_discussion(self) -> bool:
        """Return True if this is a DISCUSSION collaboration request."""
        return self.collaboration_type == CollaborationType.DISCUSSION

    def is_approval(self) -> bool:
        """Return True if this is an APPROVAL collaboration request."""
        return self.collaboration_type == CollaborationType.APPROVAL

    def is_memory_lookup(self) -> bool:
        """Return True if this is a MEMORY_LOOKUP collaboration request."""
        return self.collaboration_type == CollaborationType.MEMORY_LOOKUP

    def is_information_request(self) -> bool:
        """Return True if this is an INFORMATION_REQUEST collaboration."""
        return self.collaboration_type == CollaborationType.INFORMATION_REQUEST

    def has_project(self) -> bool:
        """Return True if this request is associated with a project."""
        return self.project_id is not None

    def has_task(self) -> bool:
        """Return True if this request originated within a task context."""
        return self.task_id is not None
