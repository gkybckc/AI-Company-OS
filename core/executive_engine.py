"""
Executive Engine for AI Company OS.

The ExecutiveEngine is the operational brain of the company. It is the
software implementation of the Executive AI agent described in Architecture
§2.1 and Constitution Chapter 4.

Responsibilities:
- Receive CEO directives and translate them into structured projects.
- Decompose projects into tasks and assign each to the appropriate agent.
- Track task and project progress across the full lifecycle.
- Detect blocked tasks caused by unresolved dependencies.
- Generate human-readable project reports for CEO review.

The ExecutiveEngine never performs work itself. It only manages.
It never designs, codes, writes, or creates. It coordinates.

Architecture reference: §2.1 Executive Engine, §11 Task Lifecycle,
Constitution Chapter 4.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.project import Project, ProjectStatus
from core.task import Priority, Task, TaskStatus


class ProjectNotFoundError(Exception):
    """Raised when a project ID cannot be resolved in the engine registry."""


class TaskNotFoundError(Exception):
    """Raised when a task ID cannot be resolved across all projects."""


class InvalidTaskTransitionError(ValueError):
    """Raised when a task assignment is attempted from a disallowed state."""


class ExecutiveEngine:
    """
    The operational brain of AI Company OS.

    Implements the coordination layer component described in Architecture §2.1.
    Maintains an authoritative registry of all active projects and a task
    index for O(1) task resolution across projects.

    The engine is synchronous and stateful. In the current architecture phase
    (Stage 1, Architecture §13), it operates without concurrency. Later stages
    will layer concurrency controls on top of this foundation.

    Attributes:
        _projects: Registry of all projects keyed by project ID.
        _task_index: Maps every task ID to its parent project ID for fast
            cross-project task lookup.
    """

    def __init__(self) -> None:
        self._projects: Dict[str, Project] = {}
        self._task_index: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_project(
        self,
        title: str,
        description: str,
        objective: str,
        priority: Priority = Priority.MEDIUM,
    ) -> Project:
        """
        Create a new project in response to a CEO directive.

        The project is registered immediately and enters ACTIVE status,
        ready to receive tasks. The objective field captures the CEO's
        original intent and links this project to CEO Memory.

        Args:
            title: Short descriptive name for the project.
            description: Concrete description of what this project delivers.
            objective: The strategic CEO goal this project serves.
            priority: Priority relative to other projects. Defaults to MEDIUM.

        Returns:
            The newly created and registered Project.
        """
        project = Project(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            objective=objective,
            status=ProjectStatus.ACTIVE,
            priority=priority,
            created_at=datetime.now(timezone.utc),
            tasks=[],
        )
        self._projects[project.id] = project
        return project

    def create_task(
        self,
        project_id: str,
        title: str,
        description: str,
        assigned_agent: str,
        priority: Priority = Priority.MEDIUM,
        dependencies: Optional[List[str]] = None,
    ) -> Task:
        """
        Create a task and attach it to an existing project.

        The task enters CREATED state. It is not yet formally delivered to
        an agent — that happens in assign_task(). The assigned_agent field
        at creation time represents the intended recipient; formal assignment
        is a separate step that advances the task to ASSIGNED state.

        Dependency IDs should reference other tasks within the same project.
        Blocked tasks are surfaced in project_status() and generate_report().

        Args:
            project_id: ID of the project this task belongs to.
            title: Short descriptive name for the task.
            description: Full specification of the required output and
                acceptance criteria.
            assigned_agent: Name of the agent intended to perform this task.
            priority: Execution priority. Defaults to MEDIUM.
            dependencies: IDs of tasks that must reach APPROVED before this
                task may begin. Defaults to an empty list.

        Returns:
            The newly created Task, already appended to the project.

        Raises:
            ProjectNotFoundError: If project_id does not exist in the registry.
        """
        project = self._get_project(project_id)

        task = Task(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            assigned_agent=assigned_agent,
            status=TaskStatus.CREATED,
            priority=priority,
            dependencies=dependencies if dependencies is not None else [],
            created_at=datetime.now(timezone.utc),
        )

        project.tasks.append(task)
        self._task_index[task.id] = project_id
        return task

    def assign_task(self, task_id: str, agent_name: str) -> Task:
        """
        Formally assign a task to an agent, advancing it to ASSIGNED state.

        This is Phase 2 of the task lifecycle (Architecture §11). Formal
        assignment constitutes delivery of the task to the agent. The task
        must be in CREATED or REJECTED state; any other state indicates
        the task is already in progress, completed, or archived and cannot
        be reassigned without an explicit state correction by the CEO.

        A REJECTED task may be reassigned to a different agent when the
        original agent is not the right choice for the revision.

        Args:
            task_id: ID of the task to assign.
            agent_name: Name of the agent receiving the formal assignment.

        Returns:
            The updated Task with status ASSIGNED and agent_name set.

        Raises:
            TaskNotFoundError: If task_id does not exist across any project.
            InvalidTaskTransitionError: If the task is not in CREATED or
                REJECTED state.
        """
        task = self._get_task(task_id)

        if task.status not in (TaskStatus.CREATED, TaskStatus.REJECTED):
            raise InvalidTaskTransitionError(
                f"Task '{task.title}' (ID: {task_id}) cannot be assigned "
                f"from its current state '{task.status.value}'. "
                f"Only tasks in CREATED or REJECTED state may be assigned."
            )

        task.assigned_agent = agent_name
        task.status = TaskStatus.ASSIGNED
        return task

    def project_status(self, project_id: str) -> Dict[str, Any]:
        """
        Return a structured status summary for a project.

        Calculates completion percentage based on APPROVED tasks, identifies
        tasks blocked by unresolved dependencies, and provides a full
        breakdown of task counts by status. This is the Executive Engine's
        primary monitoring instrument.

        Completion percentage is defined as:
            (number of APPROVED tasks / total tasks) * 100

        A task is considered blocked when at least one of its declared
        dependency IDs does not belong to the set of currently APPROVED
        task IDs in the same project.

        Args:
            project_id: ID of the project to inspect.

        Returns:
            A dictionary with the following keys:
                project_id (str): The project's unique identifier.
                title (str): The project title.
                status (str): Current ProjectStatus value.
                priority (str): Current Priority value.
                total_tasks (int): Total number of tasks in the project.
                task_counts (Dict[str, int]): Task count per TaskStatus value.
                    All TaskStatus values are present; unused statuses are 0.
                completion_percentage (float): Percentage of tasks APPROVED,
                    rounded to two decimal places. 0.0 for empty projects.
                blocked_tasks (List[str]): IDs of tasks with unmet dependencies.

        Raises:
            ProjectNotFoundError: If project_id does not exist.
        """
        project = self._get_project(project_id)

        approved_ids: set[str] = {
            t.id for t in project.tasks if t.status == TaskStatus.APPROVED
        }

        task_counts: Dict[str, int] = {s.value: 0 for s in TaskStatus}
        blocked_task_ids: List[str] = []

        for task in project.tasks:
            task_counts[task.status.value] += 1

            if task.dependencies:
                unmet = [dep for dep in task.dependencies if dep not in approved_ids]
                if unmet:
                    blocked_task_ids.append(task.id)

        total = len(project.tasks)
        approved_count = task_counts[TaskStatus.APPROVED.value]
        completion = round((approved_count / total * 100.0) if total > 0 else 0.0, 2)

        return {
            "project_id": project.id,
            "title": project.title,
            "status": project.status.value,
            "priority": project.priority.value,
            "total_tasks": total,
            "task_counts": task_counts,
            "completion_percentage": completion,
            "blocked_tasks": blocked_task_ids,
        }

    def list_tasks(self, project_id: str) -> List[Task]:
        """
        Return all tasks belonging to a project, in creation order.

        Returns a shallow copy of the project's task list. Mutating the
        returned list does not affect the project's internal task list.
        Individual Task objects within the list are live references.

        Args:
            project_id: ID of the project to inspect.

        Returns:
            Ordered list of Task instances. Empty list if no tasks exist.

        Raises:
            ProjectNotFoundError: If project_id does not exist.
        """
        project = self._get_project(project_id)
        return list(project.tasks)

    def generate_report(self, project_id: str) -> str:
        """
        Generate a human-readable Markdown status report for CEO review.

        The report contains the project header, strategic objective, a
        completion summary, a task-by-task breakdown, and a dedicated
        section for any blocked tasks. It is intended to be passed directly
        to the CEO Interface for review and approval decisions.

        Args:
            project_id: ID of the project to report on.

        Returns:
            A formatted Markdown string. Always non-empty.

        Raises:
            ProjectNotFoundError: If project_id does not exist.
        """
        project = self._get_project(project_id)
        status = self.project_status(project_id)

        lines: List[str] = [
            f"# Project Report: {project.title}",
            "",
            f"**Project ID:** `{project.id}`",
            f"**Status:** {status['status']}",
            f"**Priority:** {status['priority']}",
            f"**Created:** {project.created_at.strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Objective:** {project.objective}",
            "",
            "---",
            "",
            "## Summary",
            "",
            f"- **Total Tasks:** {status['total_tasks']}",
            f"- **Completion:** {status['completion_percentage']}%",
            f"- **Blocked Tasks:** {len(status['blocked_tasks'])}",
            "",
            "## Task Breakdown",
            "",
        ]

        for status_label, count in status["task_counts"].items():
            if count > 0:
                lines.append(f"- **{status_label}:** {count}")

        if project.tasks:
            lines += ["", "## Task List", ""]
            for task in project.tasks:
                agent_label = task.assigned_agent if task.assigned_agent else "Unassigned"
                dep_note = ""
                if task.dependencies:
                    dep_note = f" _(depends on: {', '.join(task.dependencies)})_"
                lines.append(
                    f"- `[{task.status.value}]` **{task.title}**"
                    f" → {agent_label}{dep_note}"
                )

        if status["blocked_tasks"]:
            lines += [
                "",
                "## Blockers",
                "",
                "The following tasks cannot begin until their dependencies are approved:",
                "",
            ]
            for blocked_id in status["blocked_tasks"]:
                blocked_task = self._get_task(blocked_id)
                unmet_labels = [
                    dep for dep in blocked_task.dependencies
                    if dep not in {
                        t.id for t in project.tasks if t.status == TaskStatus.APPROVED
                    }
                ]
                lines.append(
                    f"- **{blocked_task.title}** (`{blocked_id}`) "
                    f"— waiting on: {', '.join(f'`{d}`' for d in unmet_labels)}"
                )

        lines += [
            "",
            "---",
            "",
            f"_Report generated by Executive Engine — "
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_",
        ]

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_project(self, project_id: str) -> Project:
        """
        Retrieve a project by ID or raise ProjectNotFoundError.

        Args:
            project_id: The project identifier to resolve.

        Returns:
            The matching Project instance.

        Raises:
            ProjectNotFoundError: If no project with the given ID exists.
        """
        project = self._projects.get(project_id)
        if project is None:
            raise ProjectNotFoundError(
                f"No project found with ID '{project_id}'."
            )
        return project

    def _get_task(self, task_id: str) -> Task:
        """
        Retrieve a task by ID across all projects or raise TaskNotFoundError.

        Uses the task index for O(1) project resolution, followed by a
        linear scan within the project's task list to return the live object.

        Args:
            task_id: The task identifier to resolve.

        Returns:
            The matching Task instance.

        Raises:
            TaskNotFoundError: If no task with the given ID exists.
        """
        project_id = self._task_index.get(task_id)
        if project_id is None:
            raise TaskNotFoundError(
                f"No task found with ID '{task_id}'."
            )
        project = self._projects[project_id]
        for task in project.tasks:
            if task.id == task_id:
                return task
        raise TaskNotFoundError(
            f"Task index inconsistency: task '{task_id}' indexed under "
            f"project '{project_id}' but absent from project task list."
        )
