"""
Project model for AI Company OS.

A Project is the top-level container for a cohesive body of work directed
by a CEO goal. The Executive Engine creates and owns all projects. Agents
never create or modify projects directly.

Architecture reference: §2.1 Executive Engine, §7.5 Project Memory.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List

from core.task import Priority, Task


class ProjectStatus(str, Enum):
    """
    Valid lifecycle states for a Project.

    A project begins ACTIVE when created and progresses toward COMPLETED
    as its tasks are approved. ON_HOLD is set by the CEO or Executive Engine
    when a project must pause. ARCHIVED is the terminal state.
    """

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"

    def __str__(self) -> str:
        return self.value


@dataclass
class Project:
    """
    Top-level container for a cohesive body of work.

    A Project is created by the Executive Engine when the CEO issues a
    directive that requires coordinated multi-task execution. It owns an
    ordered list of Tasks and advances through status states as those tasks
    progress through their lifecycle.

    A Project may not be marked COMPLETED until all of its Tasks have
    reached APPROVED or ARCHIVED state, as required by the Definition of
    Done in Constitution Chapter 16.

    Attributes:
        id: Unique identifier (UUID string).
        title: Short descriptive name.
        description: What this project will deliver as a concrete outcome.
        objective: The strategic CEO goal this project serves. Links the
            project back to the original directive in CEO Memory.
        status: Current lifecycle state of the project.
        priority: Priority relative to other active projects.
        created_at: UTC timestamp of project creation.
        tasks: Ordered list of all tasks belonging to this project.
            Tasks appear in creation order. The Executive Engine is the
            only authority that may add tasks to this list.
    """

    id: str
    title: str
    description: str
    objective: str
    status: ProjectStatus
    priority: Priority
    created_at: datetime
    tasks: List[Task]
