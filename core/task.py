"""
Task model for AI Company OS.

Defines the atomic unit of work — the Task — and the enumerations that
govern its lifecycle state and scheduling priority. Every task in the system
must be created and owned by the Executive Engine; no agent creates tasks
directly.

Architecture reference: §2.6 Task Engine, §11 Task Lifecycle.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List


class TaskStatus(str, Enum):
    """
    Valid lifecycle states for a Task.

    States follow the six-phase lifecycle defined in Architecture §11:
    CREATED → ASSIGNED → WORKING → REVIEW → APPROVED → ARCHIVED.
    REJECTED is a feedback state that returns a task to ASSIGNED for revision.
    """

    CREATED = "CREATED"
    ASSIGNED = "ASSIGNED"
    WORKING = "WORKING"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"

    def __str__(self) -> str:
        return self.value


class Priority(str, Enum):
    """
    Priority levels shared by Task and Project.

    Priority influences scheduling order within the Task Engine but does
    not override dependency constraints.
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    def __str__(self) -> str:
        return self.value


@dataclass
class Task:
    """
    Atomic unit of work in AI Company OS.

    A Task is created by the Executive Engine in response to a CEO directive
    decomposed into actionable steps. It is assigned to a specific agent,
    executed, reviewed by the Approval Engine, and archived on completion.

    No Task may be considered done until it reaches APPROVED state through
    the Approval Engine, as required by Constitution Chapter 8 and §11 Phase 5.

    Attributes:
        id: Unique identifier (UUID string).
        title: Short, descriptive name for the task.
        description: Full specification of the required output and
            acceptance criteria.
        assigned_agent: Name of the agent responsible for execution.
            Empty string if not yet formally assigned.
        status: Current lifecycle state of the task.
        priority: Execution priority relative to other tasks in the project.
        dependencies: IDs of tasks that must reach APPROVED state before
            this task may begin execution.
        created_at: UTC timestamp of task creation.
    """

    id: str
    title: str
    description: str
    assigned_agent: str
    status: TaskStatus
    priority: Priority
    dependencies: List[str]
    created_at: datetime
