"""
Provider request model for AI Company OS.

A ProviderRequest is the standardised input contract between the Agent Layer
and the AI Provider Abstraction Layer.  Every time an agent needs intelligence
it constructs a ProviderRequest and submits it to the active provider via the
ProviderRegistry.  The provider never receives anything else — raw strings,
prompt templates, or provider-specific payloads are hidden inside the provider
implementation, not exposed to the agent.

Architecture reference: §2.10 LLM Gateway, §3 Layer 2 (Intelligence Layer),
Constitution §14 (Security — no credentials in agent code).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ProviderRequestError(Exception):
    """Raised when a ProviderRequest fails validation."""


# ---------------------------------------------------------------------------
# ProviderRequest
# ---------------------------------------------------------------------------

@dataclass
class ProviderRequest:
    """
    Standardised input sent by an agent to the AI provider.

    Agents never construct provider-specific prompts.  They fill in this
    structured object, which the provider translates into whatever format
    the underlying model requires.  This keeps agents completely decoupled
    from the intelligence layer.

    Attributes:
        role:            The agent's functional role (e.g. "Backend Agent",
                         "QA Engineer").  Used by the provider to calibrate
                         response style and domain focus.
        objective:       The high-level goal this request is serving.
                         Provides strategic context so the provider can
                         align the response with the overall project aim.
        task:            The specific, concrete task to execute.  This is
                         the primary driver of the provider's response.
        context:         Additional background information relevant to the
                         task but not directly part of the instruction.
                         Optional; defaults to empty string.
        constraints:     An ordered list of constraints the response must
                         observe (e.g. "No external libraries", "REST only").
                         Optional; defaults to empty list.
        expected_output: Description of the expected output format or
                         content type (e.g. "Markdown document",
                         "Python code with type annotations").
                         Optional; defaults to empty string.
    """

    role: str
    objective: str
    task: str
    context: str = ""
    constraints: List[str] = field(default_factory=list)
    expected_output: str = ""

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> None:
        """
        Validate that the request contains the minimum required fields.

        Raises:
            ProviderRequestError: If role, objective, or task is blank.
        """
        if not self.role or not self.role.strip():
            raise ProviderRequestError("ProviderRequest.role must not be blank.")
        if not self.objective or not self.objective.strip():
            raise ProviderRequestError("ProviderRequest.objective must not be blank.")
        if not self.task or not self.task.strip():
            raise ProviderRequestError("ProviderRequest.task must not be blank.")

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain-dict representation of this request."""
        return {
            "role": self.role,
            "objective": self.objective,
            "task": self.task,
            "context": self.context,
            "constraints": list(self.constraints),
            "expected_output": self.expected_output,
        }

    def prompt_summary(self) -> str:
        """Return a one-line summary for logging and diagnostics."""
        return (
            f"[{self.role}] task={self.task!r} "
            f"constraints={len(self.constraints)} "
            f"context={'yes' if self.context else 'no'}"
        )

    # ------------------------------------------------------------------
    # Convenience queries
    # ------------------------------------------------------------------

    def has_context(self) -> bool:
        """Return True when a non-empty context string is present."""
        return bool(self.context and self.context.strip())

    def has_constraints(self) -> bool:
        """Return True when at least one constraint is present."""
        return bool(self.constraints)

    def has_expected_output(self) -> bool:
        """Return True when an expected_output description is present."""
        return bool(self.expected_output and self.expected_output.strip())

    def constraint_count(self) -> int:
        """Return the number of constraints."""
        return len(self.constraints)
