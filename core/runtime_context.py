"""
Runtime context model for the Agent Runtime.

A RuntimeContext is the read-only snapshot of the agent's operating
environment for a given session. It is produced by the Executive Engine
or Director and attached to an active session via AgentRuntime.attach_context().

The context is immutable once attached. If the operating environment
changes (e.g., the task is updated), a new RuntimeContext must be built
and attached — the runtime records the attachment event so the history
of context changes is observable.

Architecture reference: §2.2 Agent Runtime, §3 Layer 4 (Agent Layer),
§6 Communication Model (context arrives via the Event Bus).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from core.department_type import DepartmentType


@dataclass(frozen=True)
class RuntimeContext:
    """
    Immutable snapshot of the environment in which an agent session runs.

    Produced by the Executive Engine after a task is assigned. Attached
    to the session via AgentRuntime.attach_context(). All values in the
    context are advisory — the Agent Runtime does not enforce constraints
    derived from the context; that is the job of the Governance Layer.

    Attributes:
        current_task: Identifier of the task this session is executing.
            None when the context is attached before a task is assigned
            (e.g., a preparation context).
        project: Identifier of the project this task belongs to.
            None for tasks that are not part of a tracked project.
        department: The DepartmentType the agent is currently operating
            within. Determines which Director authority applies and which
            department-level shared memory is accessible.
        director_id: Identifier of the Director who assigned or is
            supervising this session. None if the session was assigned
            directly by the Executive Engine without a department Director.
        metadata: Arbitrary key-value pairs providing additional context
            to the agent — e.g., approved technology constraints, project
            phase, output format requirements. Schema is not enforced here;
            validation is the responsibility of the consuming component.
    """

    current_task: Optional[str] = None
    project: Optional[str] = None
    department: Optional[DepartmentType] = None
    director_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def has_task(self) -> bool:
        """Return True if a task ID is present in this context."""
        return self.current_task is not None

    def has_project(self) -> bool:
        """Return True if a project ID is present in this context."""
        return self.project is not None

    def has_director(self) -> bool:
        """Return True if a directing authority is identified in this context."""
        return self.director_id is not None

    def has_department(self) -> bool:
        """Return True if a department is specified in this context."""
        return self.department is not None

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Return a metadata value by key.

        Args:
            key: The metadata key to retrieve.
            default: Value to return if the key is absent.

        Returns:
            The metadata value for the key, or default if not present.
        """
        return self.metadata.get(key, default)
