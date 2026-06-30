"""
Runtime result model for the Agent Runtime.

A RuntimeResult is the formal output record produced when an agent session
completes. It is passed to AgentRuntime.finish() which attaches it to the
session and transitions the session state to FINISHED.

A RuntimeResult describes WHAT the agent produced and WHAT happens next —
it does not contain the artifacts themselves. Artifact content lives in
the Memory Engine and in the project's artifact store. The RuntimeResult
holds references (IDs or paths) to those artifacts, not their contents.

Architecture reference: §2.2 Agent Runtime, §3 Layer 4 (Agent Layer),
§8 Approval Flow, §7 Memory Model (artifacts are stored by the Memory Engine).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RuntimeResult:
    """
    Immutable record of the outcome of a completed Agent Runtime session.

    Produced by the agent (via the AgentRuntime) at the end of a task.
    Consumed by the Executive Engine and Approval Engine to determine next
    steps. The Approval Engine reads requires_approval to decide whether
    to route the output to the CEO. The Workflow Engine reads next_action
    to advance the project plan.

    Attributes:
        success: True if the agent considers the task outcome successful.
            A session may succeed with requires_approval=True if the output
            was produced but still needs CEO sign-off. A session with
            success=False indicates the task could not be completed as
            specified — the Executive Engine must decide how to handle this.
        summary: Human-readable description of what the session accomplished.
            Included in CEO-facing status reports and stored in project
            memory. Should be concise (one to three sentences).
        next_action: Optional identifier or description of the recommended
            next step following this result. Interpreted by the Workflow Engine
            to advance the project. None if no follow-on action is needed.
        generated_artifacts: List of artifact identifiers (IDs, names, or
            paths) produced during this session. The actual content is stored
            by the Memory Engine; these are references only. May be empty for
            analysis or planning tasks that produce no persisted artifacts.
        requires_discussion: True if the agent believes this output should be
            reviewed through a structured multi-agent Discussion Engine process
            before it is approved. Set when the output touches cross-department
            concerns or where peer review adds material value.
        requires_approval: True if this output must pass through the Approval
            Engine (and possibly the CEO) before it is accepted. The Approval
            Engine's rules govern which outputs require CEO review vs. automated
            approval. This flag signals the intent; the Approval Engine decides
            the actual routing.
        session_id: The ID of the RuntimeSession that produced this result.
            Stored to allow tracing back from a result to its originating
            session in audit trails and memory queries.
        completed_at: UTC timestamp of when this result was created.
            Set automatically to the current UTC time if not provided.
        metadata: Optional key-value pairs for additional result context,
            such as output quality scores, word counts, or tool-use stats.
    """

    success: bool
    summary: str
    next_action: Optional[str] = None
    generated_artifacts: List[str] = field(default_factory=list)
    requires_discussion: bool = False
    requires_approval: bool = False
    session_id: Optional[str] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """
        Populate completed_at with current UTC time if not provided.

        Uses object.__setattr__ because the dataclass is frozen.
        """
        if self.completed_at is None:
            object.__setattr__(self, "completed_at", datetime.now(timezone.utc))

    def has_artifacts(self) -> bool:
        """Return True if this result includes at least one generated artifact."""
        return len(self.generated_artifacts) > 0

    def needs_external_review(self) -> bool:
        """
        Return True if any form of external review is required.

        A result requiring either discussion or approval cannot be
        considered fully resolved until the respective engine responds.

        Returns:
            True if requires_discussion or requires_approval is True.
        """
        return self.requires_discussion or self.requires_approval

    def artifact_count(self) -> int:
        """Return the number of artifacts referenced in this result."""
        return len(self.generated_artifacts)
