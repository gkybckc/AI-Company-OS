"""
Workflow Engine for AI Company OS.

The WorkflowEngine defines, validates, executes, and tracks standardised
company workflows. A workflow represents the ordered stages required to
complete a project. The engine controls process execution — it does NOT
perform any work itself.

Lifecycle
---------
1. create_workflow() — register a new workflow in PENDING status.
2. start()          — activate the workflow; enter the first stage.
3. advance()        — mark the current stage done; enter the next stage.
4. rollback()       — undo the last advance; return to the previous stage.
5. pause()          — suspend an active workflow.
6. resume()         — reactivate a paused workflow.
7. complete()       — finalise the workflow from the last stage.
8. cancel()         — abandon a workflow at any point.

Every stage transition emits WorkflowEvent records that are appended to
the workflow's append-only event log.

Illegal transitions (e.g. advancing a paused workflow, rolling back from
the first stage) raise IllegalTransitionError.

Optional integrations
---------------------
All four integration parameters accept None — the engine is fully
functional without any of them.

  memory_engine:     When provided and a stage has memory_required=True,
                     a MemoryEntry is stored on stage entry.
                     Separately, on every advance(), a TASK-category
                     MemoryEntry records the stage transition.
  decision_engine:   When provided and a stage has approval_required=True,
                     a Decision is created with "Approve and proceed" vs
                     "Request revision" options.
  discussion_engine: Stored for callers to reference; the engine does not
                     auto-start discussions (participants are unknown here).
  company_orchestrator: Stored for callers to reference.

Architecture reference: §2.7 Workflow Engine, §3 Layer 5 (Coordination
Layer), Constitution §11 (Project Principles).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from core.workflow import (
    Workflow,
    WorkflowEvent,
    WorkflowEventType,
    WorkflowStatus,
)
from core.workflow_stage import WorkflowStage
from core.workflow_template import WorkflowTemplate
from core.workflow_transition import WorkflowTransition


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class WorkflowEngineError(Exception):
    """Base class for all Workflow Engine errors."""


class WorkflowNotFoundError(WorkflowEngineError):
    """
    Raised when an operation references a workflow ID that does not exist.

    Raised by start(), advance(), rollback(), pause(), resume(), complete(),
    cancel(), current_stage(), and find_workflow() when the given workflow_id
    is not present in the engine.
    """


class InvalidWorkflowError(WorkflowEngineError):
    """
    Raised when create_workflow() receives invalid arguments.

    Covers: empty name, empty stage list, duplicate stage orders,
    duplicate stage IDs, duplicate stage names, non-positive orders.
    """


class IllegalTransitionError(WorkflowEngineError):
    """
    Raised when a requested state transition is not permitted.

    Examples:
        - Calling advance() on a PAUSED or COMPLETED workflow.
        - Calling rollback() when already at the first stage.
        - Calling complete() when not at the final stage.
        - Calling start() on an already-ACTIVE workflow.
        - Calling pause() on a non-ACTIVE workflow.
        - Calling resume() on a non-PAUSED workflow.
        - Calling cancel() on an already-terminal workflow.
    """


# ---------------------------------------------------------------------------
# WorkflowEngine
# ---------------------------------------------------------------------------

class WorkflowEngine:
    """
    Central authority for workflow lifecycle management.

    The engine stores all workflows, enforces valid transitions, emits
    structured events on every state change, and optionally integrates
    with the Memory Engine and Decision Engine to record stage entries
    and create approval decisions.

    The engine does NOT perform any business work. It only controls
    process execution — advancing, rolling back, pausing, resuming,
    and completing ordered sequences of stages.

    Usage pattern:
        engine = WorkflowEngine()
        wf = engine.create_workflow(
            "Build Platform",
            "Full product lifecycle.",
            WorkflowTemplate.SOFTWARE_PROJECT,
        )
        engine.start(wf.id)
        while wf.next_stage():
            engine.advance(wf.id)
        engine.complete(wf.id)
        print(wf.status)   # COMPLETED
        print(wf.progress) # 1.0

    Attributes:
        _workflows:          Dict[str, Workflow] — all registered workflows.
        _memory_engine:      Optional MemoryEngine for transition records.
        _decision_engine:    Optional DecisionEngine for approval decisions.
        _discussion_engine:  Optional DiscussionEngine (reference only).
        _company_orchestrator: Optional CompanyOrchestrator (reference only).
    """

    def __init__(
        self,
        memory_engine: Optional[Any] = None,
        decision_engine: Optional[Any] = None,
        discussion_engine: Optional[Any] = None,
        company_orchestrator: Optional[Any] = None,
    ) -> None:
        self._workflows: Dict[str, Workflow] = {}
        self._memory_engine = memory_engine
        self._decision_engine = decision_engine
        self._discussion_engine = discussion_engine
        self._company_orchestrator = company_orchestrator

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_workflow(
        self,
        name: str,
        description: str,
        template: WorkflowTemplate,
        stages: Optional[List[WorkflowStage]] = None,
    ) -> Workflow:
        """
        Register a new workflow in PENDING status.

        If stages is None, the template's default stages are used via
        WorkflowTemplate.create_stages(). Custom stage lists override the
        template's defaults.

        Args:
            name:        Human-readable workflow name. Must be non-empty.
            description: Purpose of this workflow. May be empty.
            template:    The WorkflowTemplate this workflow is based on.
            stages:      Optional custom stage list. Must contain at least
                         one stage. Orders, IDs, and names must be unique.
                         If None, defaults to template.create_stages().

        Returns:
            The newly created Workflow in PENDING status.

        Raises:
            InvalidWorkflowError: If name is empty, stages is empty,
                stage orders/IDs/names are not unique, or any stage has
                a non-positive order or empty name.
        """
        if not name or not name.strip():
            raise InvalidWorkflowError("Workflow name must not be empty.")

        resolved_stages = stages if stages is not None else template.create_stages()
        self._validate_stages(resolved_stages)

        sorted_stages = sorted(resolved_stages, key=lambda s: s.order)
        now = datetime.now(timezone.utc)

        workflow = Workflow(
            id=str(uuid4()),
            name=name.strip(),
            description=description,
            template=template,
            stages=sorted_stages,
            status=WorkflowStatus.PENDING,
            progress=0.0,
            created_at=now,
            updated_at=now,
        )

        workflow.add_event(WorkflowEvent.create(
            WorkflowEventType.WORKFLOW_CREATED,
            workflow_id=workflow.id,
            payload={
                "template": str(template),
                "stage_count": len(sorted_stages),
            },
        ))

        self._workflows[workflow.id] = workflow
        return workflow

    def start(self, workflow_id: str) -> Workflow:
        """
        Activate the workflow and enter its first stage.

        The workflow must be in PENDING status. After start(), the workflow
        is ACTIVE and current_stage is the stage with the lowest order.

        Args:
            workflow_id: ID of the workflow to start.

        Returns:
            The updated Workflow in ACTIVE status.

        Raises:
            WorkflowNotFoundError: If workflow_id does not exist.
            IllegalTransitionError: If the workflow is not PENDING.
        """
        workflow = self._require_workflow(workflow_id)
        if workflow.status != WorkflowStatus.PENDING:
            raise IllegalTransitionError(
                f"Workflow '{workflow_id}' cannot be started: "
                f"current status is {workflow.status}. "
                "Only PENDING workflows can be started."
            )

        first = workflow.first_stage()
        now = datetime.now(timezone.utc)

        workflow.current_stage = first
        workflow.status = WorkflowStatus.ACTIVE
        workflow.updated_at = now

        workflow.add_event(WorkflowEvent.create(
            WorkflowEventType.WORKFLOW_STARTED,
            workflow_id=workflow_id,
            payload={"first_stage": first.id if first else None},
        ))
        if first:
            workflow.add_event(WorkflowEvent.create(
                WorkflowEventType.STAGE_STARTED,
                workflow_id=workflow_id,
                stage_id=first.id,
                payload={"stage_name": first.name, "order": first.order},
            ))
            self._maybe_store_memory(
                workflow,
                "stage_started",
                f"Workflow '{workflow.name}' started at stage '{first.name}'.",
            )

        return workflow

    def advance(self, workflow_id: str) -> Workflow:
        """
        Mark the current stage done and enter the next stage.

        The workflow must be ACTIVE. If the current stage is the final
        stage, advance() raises IllegalTransitionError — call complete()
        to finalise the workflow from the last stage.

        Creates three events: STAGE_COMPLETED, STAGE_TRANSITION,
        STAGE_STARTED. Appends the completed stage to completed_stages.
        Recalculates progress. Records a WorkflowTransition.

        If a decision_engine is attached and the next stage has
        approval_required=True, a Decision record is created.

        If a memory_engine is attached, a MemoryEntry recording the
        transition is stored.

        Args:
            workflow_id: ID of the workflow to advance.

        Returns:
            The updated Workflow with current_stage pointing to the
            next stage.

        Raises:
            WorkflowNotFoundError:    If workflow_id does not exist.
            IllegalTransitionError:   If the workflow is not ACTIVE, or
                                      if already at the final stage
                                      (use complete()).
        """
        workflow = self._require_workflow(workflow_id)
        self._require_active(workflow)

        next_s = workflow.next_stage()
        if next_s is None:
            cs_name = (
                workflow.current_stage.name
                if workflow.current_stage
                else "unknown"
            )
            raise IllegalTransitionError(
                f"Workflow '{workflow_id}' is already at the final stage "
                f"('{cs_name}'). Call complete() to finalise the workflow."
            )

        old_stage = workflow.current_stage
        now = datetime.now(timezone.utc)

        workflow.completed_stages.append(old_stage)
        workflow.transitions.append(WorkflowTransition(
            from_stage=old_stage.id,
            to_stage=next_s.id,
            automatic=False,
        ))
        workflow.current_stage = next_s
        workflow.progress = self._compute_progress(workflow)
        workflow.updated_at = now

        workflow.add_event(WorkflowEvent.create(
            WorkflowEventType.STAGE_COMPLETED,
            workflow_id=workflow_id,
            stage_id=old_stage.id,
            payload={"stage_name": old_stage.name, "order": old_stage.order},
        ))
        workflow.add_event(WorkflowEvent.create(
            WorkflowEventType.STAGE_TRANSITION,
            workflow_id=workflow_id,
            payload={"from_stage": old_stage.id, "to_stage": next_s.id},
        ))
        workflow.add_event(WorkflowEvent.create(
            WorkflowEventType.STAGE_STARTED,
            workflow_id=workflow_id,
            stage_id=next_s.id,
            payload={"stage_name": next_s.name, "order": next_s.order},
        ))

        self._maybe_store_memory(
            workflow,
            "stage_advanced",
            (
                f"Workflow '{workflow.name}' advanced from "
                f"'{old_stage.name}' to '{next_s.name}'."
            ),
        )
        self._maybe_create_decision(workflow, next_s)

        return workflow

    def rollback(self, workflow_id: str) -> Workflow:
        """
        Undo the last advance and return to the previous stage.

        The workflow must be ACTIVE. Rolling back from the first stage
        raises IllegalTransitionError.

        Removes the last entry from completed_stages. Creates three events:
        STAGE_ROLLED_BACK, STAGE_TRANSITION, STAGE_STARTED. Recalculates
        progress. Records a WorkflowTransition.

        Args:
            workflow_id: ID of the workflow to roll back.

        Returns:
            The updated Workflow with current_stage pointing to the
            previous stage.

        Raises:
            WorkflowNotFoundError:   If workflow_id does not exist.
            IllegalTransitionError:  If the workflow is not ACTIVE, or if
                                     already at the first stage.
        """
        workflow = self._require_workflow(workflow_id)
        self._require_active(workflow)

        prev_s = workflow.previous_stage()
        if prev_s is None:
            cs_name = (
                workflow.current_stage.name
                if workflow.current_stage
                else "unknown"
            )
            raise IllegalTransitionError(
                f"Workflow '{workflow_id}' is at the first stage "
                f"('{cs_name}'). Cannot roll back further."
            )

        old_stage = workflow.current_stage
        now = datetime.now(timezone.utc)

        if workflow.completed_stages:
            workflow.completed_stages.pop()

        workflow.transitions.append(WorkflowTransition(
            from_stage=old_stage.id,
            to_stage=prev_s.id,
            automatic=False,
        ))
        workflow.current_stage = prev_s
        workflow.progress = self._compute_progress(workflow)
        workflow.updated_at = now

        workflow.add_event(WorkflowEvent.create(
            WorkflowEventType.STAGE_ROLLED_BACK,
            workflow_id=workflow_id,
            stage_id=old_stage.id,
            payload={"stage_name": old_stage.name, "order": old_stage.order},
        ))
        workflow.add_event(WorkflowEvent.create(
            WorkflowEventType.STAGE_TRANSITION,
            workflow_id=workflow_id,
            payload={"from_stage": old_stage.id, "to_stage": prev_s.id},
        ))
        workflow.add_event(WorkflowEvent.create(
            WorkflowEventType.STAGE_STARTED,
            workflow_id=workflow_id,
            stage_id=prev_s.id,
            payload={"stage_name": prev_s.name, "order": prev_s.order},
        ))

        return workflow

    def pause(self, workflow_id: str) -> Workflow:
        """
        Temporarily suspend an active workflow.

        The workflow must be ACTIVE. After pause(), the workflow is PAUSED.
        current_stage is preserved so resume() can continue from the same
        stage.

        Args:
            workflow_id: ID of the workflow to pause.

        Returns:
            The updated Workflow in PAUSED status.

        Raises:
            WorkflowNotFoundError:   If workflow_id does not exist.
            IllegalTransitionError:  If the workflow is not ACTIVE.
        """
        workflow = self._require_workflow(workflow_id)
        self._require_active(workflow)

        workflow.status = WorkflowStatus.PAUSED
        workflow.updated_at = datetime.now(timezone.utc)

        workflow.add_event(WorkflowEvent.create(
            WorkflowEventType.WORKFLOW_PAUSED,
            workflow_id=workflow_id,
            stage_id=(
                workflow.current_stage.id if workflow.current_stage else None
            ),
        ))
        return workflow

    def resume(self, workflow_id: str) -> Workflow:
        """
        Reactivate a paused workflow.

        The workflow must be PAUSED. After resume(), the workflow is
        ACTIVE again at the same stage as when it was paused.

        Args:
            workflow_id: ID of the workflow to resume.

        Returns:
            The updated Workflow in ACTIVE status.

        Raises:
            WorkflowNotFoundError:   If workflow_id does not exist.
            IllegalTransitionError:  If the workflow is not PAUSED.
        """
        workflow = self._require_workflow(workflow_id)
        if workflow.status != WorkflowStatus.PAUSED:
            raise IllegalTransitionError(
                f"Workflow '{workflow_id}' cannot be resumed: "
                f"current status is {workflow.status}. "
                "Only PAUSED workflows can be resumed."
            )

        workflow.status = WorkflowStatus.ACTIVE
        workflow.updated_at = datetime.now(timezone.utc)

        workflow.add_event(WorkflowEvent.create(
            WorkflowEventType.WORKFLOW_RESUMED,
            workflow_id=workflow_id,
        ))
        if workflow.current_stage:
            workflow.add_event(WorkflowEvent.create(
                WorkflowEventType.STAGE_STARTED,
                workflow_id=workflow_id,
                stage_id=workflow.current_stage.id,
                payload={
                    "stage_name": workflow.current_stage.name,
                    "resumed": True,
                },
            ))
        return workflow

    def complete(self, workflow_id: str) -> Workflow:
        """
        Finalise the workflow from its last stage.

        The workflow must be ACTIVE and current_stage must be the final
        stage (next_stage() returns None). After complete(), the workflow
        is COMPLETED with progress=1.0 and current_stage=None.

        Args:
            workflow_id: ID of the workflow to complete.

        Returns:
            The updated Workflow in COMPLETED status.

        Raises:
            WorkflowNotFoundError:   If workflow_id does not exist.
            IllegalTransitionError:  If the workflow is not ACTIVE, or if
                                     not at the final stage (use advance()
                                     to reach the last stage first).
        """
        workflow = self._require_workflow(workflow_id)
        self._require_active(workflow)

        if workflow.next_stage() is not None:
            cs_name = (
                workflow.current_stage.name
                if workflow.current_stage
                else "unknown"
            )
            raise IllegalTransitionError(
                f"Workflow '{workflow_id}' is not at the final stage "
                f"(current: '{cs_name}'). Use advance() to progress "
                "through remaining stages, or cancel() to abandon."
            )

        last_stage = workflow.current_stage
        now = datetime.now(timezone.utc)

        if last_stage:
            workflow.completed_stages.append(last_stage)

        workflow.current_stage = None
        workflow.status = WorkflowStatus.COMPLETED
        workflow.progress = 1.0
        workflow.updated_at = now

        if last_stage:
            workflow.add_event(WorkflowEvent.create(
                WorkflowEventType.STAGE_COMPLETED,
                workflow_id=workflow_id,
                stage_id=last_stage.id,
                payload={"stage_name": last_stage.name, "order": last_stage.order},
            ))
        workflow.add_event(WorkflowEvent.create(
            WorkflowEventType.WORKFLOW_COMPLETED,
            workflow_id=workflow_id,
            payload={"total_stages": workflow.stage_count()},
        ))

        self._maybe_store_memory(
            workflow,
            "completed",
            f"Workflow '{workflow.name}' completed all {workflow.stage_count()} stages.",
        )
        return workflow

    def cancel(self, workflow_id: str) -> Workflow:
        """
        Abandon the workflow at its current position.

        The workflow must not already be in a terminal state (COMPLETED,
        CANCELLED, FAILED). After cancel(), the workflow is CANCELLED.

        Args:
            workflow_id: ID of the workflow to cancel.

        Returns:
            The updated Workflow in CANCELLED status.

        Raises:
            WorkflowNotFoundError:   If workflow_id does not exist.
            IllegalTransitionError:  If the workflow is already in a
                                     terminal state.
        """
        workflow = self._require_workflow(workflow_id)
        if workflow.status.is_terminal():
            raise IllegalTransitionError(
                f"Workflow '{workflow_id}' is already in terminal status "
                f"{workflow.status} and cannot be cancelled."
            )

        workflow.status = WorkflowStatus.CANCELLED
        workflow.updated_at = datetime.now(timezone.utc)

        workflow.add_event(WorkflowEvent.create(
            WorkflowEventType.WORKFLOW_CANCELLED,
            workflow_id=workflow_id,
            payload={
                "cancelled_at_stage": (
                    workflow.current_stage.name
                    if workflow.current_stage
                    else None
                ),
            },
        ))
        return workflow

    def current_stage(self, workflow_id: str) -> Optional[WorkflowStage]:
        """
        Return the stage currently being worked on in the given workflow.

        Returns None if the workflow is PENDING, COMPLETED, CANCELLED,
        or FAILED (no active stage).

        Args:
            workflow_id: ID of the workflow to inspect.

        Returns:
            The active WorkflowStage, or None.

        Raises:
            WorkflowNotFoundError: If workflow_id does not exist.
        """
        return self._require_workflow(workflow_id).current_stage

    def find_workflow(self, workflow_id: str) -> Workflow:
        """
        Return the Workflow with the given ID.

        Args:
            workflow_id: The ID to look up.

        Returns:
            The Workflow.

        Raises:
            WorkflowNotFoundError: If no workflow with this ID exists.
        """
        return self._require_workflow(workflow_id)

    def history(self) -> List[Workflow]:
        """
        Return all workflows registered with the engine, oldest first.

        Returns a new list (shallow copy of values) so the caller cannot
        mutate the engine's internal store. The Workflow objects themselves
        are the same instances.

        Returns:
            List of all Workflow objects sorted by created_at ascending.
        """
        return sorted(self._workflows.values(), key=lambda w: w.created_at)

    def statistics(self) -> Dict[str, Any]:
        """
        Return aggregate statistics across all registered workflows.

        Returns:
            Dict with keys:
                total_workflows   — Total registered workflows.
                by_status         — Dict mapping status value -> count.
                by_template       — Dict mapping template value -> count.
                average_progress  — Mean progress across all workflows.
                completed_count   — Count of COMPLETED workflows.
                active_count      — Count of ACTIVE workflows.
                paused_count      — Count of PAUSED workflows.
                cancelled_count   — Count of CANCELLED workflows.
        """
        by_status: Dict[str, int] = {s.value: 0 for s in WorkflowStatus}
        by_template: Dict[str, int] = {t.value: 0 for t in WorkflowTemplate}
        total_progress = 0.0

        for w in self._workflows.values():
            by_status[w.status.value] = by_status.get(w.status.value, 0) + 1
            by_template[w.template.value] = by_template.get(w.template.value, 0) + 1
            total_progress += w.progress

        count = len(self._workflows)
        return {
            "total_workflows": count,
            "by_status": dict(by_status),
            "by_template": dict(by_template),
            "average_progress": total_progress / count if count > 0 else 0.0,
            "completed_count": by_status.get("COMPLETED", 0),
            "active_count": by_status.get("ACTIVE", 0),
            "paused_count": by_status.get("PAUSED", 0),
            "cancelled_count": by_status.get("CANCELLED", 0),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_workflow(self, workflow_id: str) -> Workflow:
        """Return the workflow or raise WorkflowNotFoundError."""
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError(
                f"No Workflow with id '{workflow_id}' exists in the engine."
            )
        return workflow

    def _require_active(self, workflow: Workflow) -> None:
        """Raise IllegalTransitionError if the workflow is not ACTIVE."""
        if workflow.status != WorkflowStatus.ACTIVE:
            raise IllegalTransitionError(
                f"Workflow '{workflow.id}' is not ACTIVE "
                f"(current status: {workflow.status}). "
                "This operation requires an ACTIVE workflow."
            )

    def _validate_stages(self, stages: List[WorkflowStage]) -> None:
        """Validate a stage list before creating a workflow."""
        if not stages:
            raise InvalidWorkflowError(
                "A workflow must have at least one stage."
            )

        orders = [s.order for s in stages]
        if len(orders) != len(set(orders)):
            raise InvalidWorkflowError(
                "All stage orders must be unique within a workflow."
            )

        ids = [s.id for s in stages]
        if len(ids) != len(set(ids)):
            raise InvalidWorkflowError(
                "All stage IDs must be unique within a workflow."
            )

        names = [s.name for s in stages]
        if len(names) != len(set(names)):
            raise InvalidWorkflowError(
                "All stage names must be unique within a workflow."
            )

        for s in stages:
            if not s.name or not s.name.strip():
                raise InvalidWorkflowError(
                    "All stage names must be non-empty."
                )
            if s.order < 1:
                raise InvalidWorkflowError(
                    f"Stage order must be a positive integer; got {s.order} "
                    f"for stage '{s.name}'."
                )

    def _compute_progress(self, workflow: Workflow) -> float:
        """Return completed_stages / total_stages as a float in [0.0, 1.0]."""
        if not workflow.stages:
            return 0.0
        return len(workflow.completed_stages) / len(workflow.stages)

    def _maybe_store_memory(
        self,
        workflow: Workflow,
        event_label: str,
        detail: str,
    ) -> None:
        """Store a MemoryEntry if a MemoryEngine is attached. Silent on error."""
        if self._memory_engine is None:
            return
        try:
            from core.memory_category import MemoryCategory
            from core.memory_entry import MemoryEntry
            from core.memory_scope import MemoryScope

            now = datetime.now(timezone.utc)
            entry = MemoryEntry(
                id="",
                title=f"Workflow {event_label}: {workflow.name}",
                category=MemoryCategory.TASK,
                scope=MemoryScope.GLOBAL,
                author="WorkflowEngine",
                content=detail,
                tags=["workflow", event_label.replace("_", "-")],
                created_at=now,
                updated_at=now,
            )
            self._memory_engine.store(entry)
        except Exception:
            pass

    def _maybe_create_decision(
        self,
        workflow: Workflow,
        stage: WorkflowStage,
    ) -> None:
        """Create a Decision if a DecisionEngine is attached and stage needs approval."""
        if self._decision_engine is None or not stage.approval_required:
            return
        try:
            from core.decision_option import DecisionOption

            proceed = DecisionOption(
                title="Approve and proceed",
                advantages=["Stage output meets quality standards"],
                disadvantages=[],
                estimated_risk="LOW",
                estimated_cost="LOW",
            )
            revise = DecisionOption(
                title="Request revision",
                advantages=["Ensures higher quality"],
                disadvantages=["Delays timeline"],
                estimated_risk="LOW",
                estimated_cost="MEDIUM",
            )
            self._decision_engine.create_decision(
                f"Approve: {stage.name}",
                [proceed, revise],
                project_id=workflow.id,
            )
        except Exception:
            pass
