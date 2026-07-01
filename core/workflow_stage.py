"""
Workflow stage model for AI Company OS.

A WorkflowStage is an immutable description of one step in a workflow.
Stages carry their position (order), the departments responsible for the
work, the inputs they require, the outputs they produce, and three boolean
flags that control the governance behaviour applied at that stage.

The Workflow Engine reads stage metadata to determine whether a Decision
Engine approval decision should be created (approval_required), whether a
Discussion Engine session is permitted (discussion_allowed), and whether a
Memory Engine record must be stored on entry (memory_required).

Architecture reference: §2.7 Workflow Engine, §3 Layer 5 (Coordination Layer),
Constitution §11 (Project Principles), §16 (Definition of Done).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class WorkflowStage:
    """
    Immutable description of a single step within a workflow.

    Stages are created either from a WorkflowTemplate (which provides a
    pre-defined set of stages suited to a class of work) or by the caller
    when creating a custom workflow.

    The Workflow Engine uses stage.order to determine the sequence of
    execution. Order values must be unique within a workflow and are
    positive integers starting from 1.

    Attributes:
        id:                     Short, unique identifier within the workflow.
                                Lowercase, underscore-separated.
        name:                   Human-readable stage name. Must be non-empty.
        order:                  Positive integer defining stage position.
                                Lower values execute first.
        responsible_departments: Names of the departments responsible for
                                 the work at this stage. Informational only;
                                 the engine does not route tasks.
        required_inputs:        Descriptions of artifacts or information this
                                stage needs before it can begin.
        expected_outputs:       Descriptions of artifacts or deliverables this
                                stage is expected to produce.
        approval_required:      If True, the Workflow Engine will create a
                                Decision Engine record when this stage becomes
                                active, signalling that CEO approval is needed
                                before the workflow proceeds.
        discussion_allowed:     If True, a Discussion Engine session may be
                                convened while this stage is active.
        memory_required:        If True, a Memory Engine entry is created
                                when this stage is entered.
    """

    id: str
    name: str
    order: int
    responsible_departments: List[str] = field(default_factory=list)
    required_inputs: List[str] = field(default_factory=list)
    expected_outputs: List[str] = field(default_factory=list)
    approval_required: bool = False
    discussion_allowed: bool = False
    memory_required: bool = False

    # ------------------------------------------------------------------
    # Governance helpers
    # ------------------------------------------------------------------

    def is_first_stage(self) -> bool:
        """Return True if this is the first stage in the workflow (order == 1)."""
        return self.order == 1

    def needs_approval(self) -> bool:
        """Return True if this stage requires an explicit approval decision."""
        return self.approval_required

    def allows_discussion(self) -> bool:
        """Return True if a Discussion Engine session may be opened here."""
        return self.discussion_allowed

    def requires_memory(self) -> bool:
        """Return True if the Memory Engine must record entry to this stage."""
        return self.memory_required

    def has_responsible_departments(self) -> bool:
        """Return True if at least one responsible department is listed."""
        return bool(self.responsible_departments)

    def has_required_inputs(self) -> bool:
        """Return True if this stage lists required inputs."""
        return bool(self.required_inputs)

    def has_expected_outputs(self) -> bool:
        """Return True if this stage lists expected outputs."""
        return bool(self.expected_outputs)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        """Return a compact dict representation suitable for reports."""
        return {
            "id": self.id,
            "name": self.name,
            "order": self.order,
            "responsible_departments": list(self.responsible_departments),
            "required_inputs": list(self.required_inputs),
            "expected_outputs": list(self.expected_outputs),
            "approval_required": self.approval_required,
            "discussion_allowed": self.discussion_allowed,
            "memory_required": self.memory_required,
        }
