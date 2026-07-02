"""
Execution Context for AI Company OS Agent Executor.

The ExecutionContext carries everything the AgentExecutor needs to run a
company task from start to finish: who is executing, which project they are
working on, what stage the work is in, and what task must be completed.

This is the input object for AgentExecutor.execute(). The executor reads the
context fields, converts them to a PromptContext, builds a ProviderRequest,
and coordinates the full execution pipeline.

The context accepts either structured Project/Task objects from the existing
company engines OR plain strings/dicts for lightweight usage and testing.
All helper methods degrade gracefully when fields are absent.

Architecture reference: §2 Core Components, §3 Layer 2 (Intelligence Layer),
§2.10 LLM Gateway.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ExecutionContextError(Exception):
    """Raised when ExecutionContext.validate() detects a required field missing."""


# ---------------------------------------------------------------------------
# ExecutionContext
# ---------------------------------------------------------------------------

@dataclass
class ExecutionContext:
    """
    Structured input for a single agent task execution.

    Fields:
        employee_id    Unique identifier for the agent performing the task.
        employee_role  Display role of the agent (e.g. "Backend Agent").
        department     Department the agent belongs to.
        project        Project object, dict, or None. The executor extracts
                       project_name, project_description, and project_id from
                       it via attribute or key lookup.
        workflow_stage Current stage in the project workflow.
        task           Task object, dict, string, or None. The executor
                       extracts the task description from it.
        constraints    Optional list of execution constraints.
        seniority      Optional seniority level (e.g. "Senior", "Lead").
        context        Optional additional background context string.
    """

    employee_id: str
    employee_role: str
    department: str
    project: Any
    workflow_stage: str
    task: Any
    constraints: List[str] = field(default_factory=list)
    seniority: str = ""
    context: str = ""

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> None:
        """
        Raise ExecutionContextError if any required field is blank.

        Required: employee_id, employee_role, department, workflow_stage,
        and the derived task description.

        Raises:
            ExecutionContextError: On first set of blank required fields.
        """
        errors: List[str] = []
        if not self.employee_id or not str(self.employee_id).strip():
            errors.append("'employee_id' must not be blank.")
        if not self.employee_role or not str(self.employee_role).strip():
            errors.append("'employee_role' must not be blank.")
        if not self.department or not str(self.department).strip():
            errors.append("'department' must not be blank.")
        if not self.workflow_stage or not str(self.workflow_stage).strip():
            errors.append("'workflow_stage' must not be blank.")
        if not self.task_description().strip():
            errors.append("'task' must provide a non-blank description.")
        if errors:
            raise ExecutionContextError(
                "ExecutionContext validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

    # ------------------------------------------------------------------
    # Project accessors
    # ------------------------------------------------------------------

    def has_project(self) -> bool:
        """Return True if a project object is attached."""
        return self.project is not None

    def project_id(self) -> Optional[str]:
        """
        Return the project ID string if available.

        Tries: project.id, project["id"]. Returns None if absent or blank.
        """
        if self.project is None:
            return None
        pid = getattr(self.project, "id", None)
        if pid is None and isinstance(self.project, dict):
            pid = self.project.get("id")
        if pid and str(pid).strip():
            return str(pid)
        return None

    def project_name(self) -> str:
        """
        Return the project display name.

        Tries: project as str, project.title, project.name, project["title"],
        project["name"]. Falls back to "".
        """
        if self.project is None:
            return ""
        if isinstance(self.project, str):
            return self.project
        title = getattr(self.project, "title", None)
        if not (title and str(title).strip()):
            title = getattr(self.project, "name", None)
        if not (title and str(title).strip()) and isinstance(self.project, dict):
            title = self.project.get("title") or self.project.get("name")
        return str(title).strip() if (title and str(title).strip()) else ""

    def project_description(self) -> str:
        """
        Return the project description.

        Tries: project.description, project["description"]. Falls back to "".
        """
        if self.project is None:
            return ""
        if isinstance(self.project, str):
            return self.project
        desc = getattr(self.project, "description", None)
        if desc is None and isinstance(self.project, dict):
            desc = self.project.get("description", "")
        return str(desc) if desc else ""

    # ------------------------------------------------------------------
    # Task accessors
    # ------------------------------------------------------------------

    def has_task(self) -> bool:
        """Return True if a task object is attached."""
        return self.task is not None

    def task_id(self) -> Optional[str]:
        """
        Return the task ID string if available.

        Tries: task.id, task["id"]. Returns None if absent or blank.
        """
        if self.task is None:
            return None
        tid = getattr(self.task, "id", None)
        if tid is None and isinstance(self.task, dict):
            tid = self.task.get("id")
        if tid and str(tid).strip():
            return str(tid)
        return None

    def task_description(self) -> str:
        """
        Return the task description.

        Tries: task as str, task.description, task["description"],
        task.title, task["title"]. Falls back to "".
        """
        if self.task is None:
            return ""
        if isinstance(self.task, str):
            return self.task
        desc = getattr(self.task, "description", None)
        if desc is None and isinstance(self.task, dict):
            desc = self.task.get("description")
        if desc and str(desc).strip():
            return str(desc)
        title = getattr(self.task, "title", None)
        if title is None and isinstance(self.task, dict):
            title = self.task.get("title")
        if title and str(title).strip():
            return str(title)
        return ""

    def task_title(self) -> str:
        """
        Return a short task title (at most 60 characters).

        Tries: task.title, task["title"], first 60 chars of task_description().
        """
        if self.task is None:
            return ""
        if isinstance(self.task, str):
            return self.task[:60]
        title = getattr(self.task, "title", None)
        if title is None and isinstance(self.task, dict):
            title = self.task.get("title")
        if title and str(title).strip():
            return str(title)[:60]
        desc = self.task_description()
        return desc[:60] if desc else ""

    # ------------------------------------------------------------------
    # Constraint helpers
    # ------------------------------------------------------------------

    def has_constraints(self) -> bool:
        """Return True if at least one constraint is set."""
        return bool(self.constraints)

    def constraint_count(self) -> int:
        """Return the number of constraints."""
        return len(self.constraints)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain-dict representation of this context."""
        return {
            "employee_id": self.employee_id,
            "employee_role": self.employee_role,
            "department": self.department,
            "workflow_stage": self.workflow_stage,
            "seniority": self.seniority,
            "context": self.context,
            "project_id": self.project_id(),
            "project_name": self.project_name(),
            "project_description": self.project_description(),
            "task_id": self.task_id(),
            "task_description": self.task_description(),
            "task_title": self.task_title(),
            "constraint_count": self.constraint_count(),
            "constraints": list(self.constraints),
        }

    def summary(self) -> str:
        """Return a one-line summary of this context."""
        role = self.employee_role or "Unknown Role"
        dept = self.department or "Unknown Dept"
        stage = self.workflow_stage or "Unknown Stage"
        task = (self.task_description() or "No task")[:50]
        return f"[{role} / {dept}] Stage={stage} Task={task!r}"
