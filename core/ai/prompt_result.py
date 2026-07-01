"""
Prompt result model for AI Company OS.

A PromptResult is the structured output of the PromptBuilder.  It carries
two distinct prompt strings (system and user) and the metadata the caller
needs to submit the prompt to any AI provider through the ProviderRegistry.

The PromptResult is the link between the Prompt Builder (Feature 17.2) and
the Provider Abstraction Layer (Feature 17.1).  A caller takes the prompts
from this result, constructs a ProviderRequest, and submits it to the active
provider.  The prompts are pure text -- they contain no provider-specific
encoding, no markup beyond standard Markdown, and no credentials.

Architecture reference: §2.10 LLM Gateway, §3 Layer 2 (Intelligence Layer),
Architectural Constraint 6: "The LLM Gateway is the only authorized path to
external intelligence."
"""

from dataclasses import dataclass, field
from typing import Any, Dict


# ---------------------------------------------------------------------------
# PromptResult
# ---------------------------------------------------------------------------

@dataclass
class PromptResult:
    """
    Structured output produced by PromptBuilder.build().

    The result separates system-level context (role, governance, quality
    standards) from task-level instructions (project context, task, constraints).
    This separation maps directly onto the system/user message distinction used
    by modern LLM APIs, so the result can be handed to a provider with no
    additional transformation beyond field assignment.

    Attributes:
        system_prompt:    The system-role prompt.  Defines the agent's identity,
                          authority level, governance rules, and quality standard.
                          This prompt is stable across tasks for the same role
                          and project -- it changes only when the role, rules,
                          or governance context changes.

        user_prompt:      The user-role prompt.  Contains the project context,
                          workflow stage, the specific task instruction, and all
                          task-level constraints.  This prompt changes for every
                          new task assignment.

        estimated_tokens: Approximate combined token count for both prompts.
                          Computed by the PromptBuilder using a word-based
                          approximation (each word ~= 1.3 tokens).  Used for
                          capacity planning and observability; not a guarantee.

        metadata:         Builder-level supplementary data (role, department,
                          workflow stage, builder version, build timestamp,
                          constraint count, etc.).  Callers treat this as
                          informational; the schema may vary across builder
                          versions.
    """

    system_prompt: str
    user_prompt: str
    estimated_tokens: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def word_count(self) -> int:
        """Return the combined word count of both prompts."""
        return len(self.system_prompt.split()) + len(self.user_prompt.split())

    def char_count(self) -> int:
        """Return the combined character count of both prompts."""
        return len(self.system_prompt) + len(self.user_prompt)

    def line_count(self) -> int:
        """Return the combined line count of both prompts."""
        return (
            len(self.system_prompt.splitlines())
            + len(self.user_prompt.splitlines())
        )

    def system_word_count(self) -> int:
        """Return the word count of the system prompt only."""
        return len(self.system_prompt.split())

    def user_word_count(self) -> int:
        """Return the word count of the user prompt only."""
        return len(self.user_prompt.split())

    def is_valid(self) -> bool:
        """
        Return True when both prompts are non-empty and the token
        estimate is a positive integer.

        Returns:
            True if the result is structurally complete and usable.
        """
        return (
            bool(self.system_prompt and self.system_prompt.strip())
            and bool(self.user_prompt and self.user_prompt.strip())
            and self.estimated_tokens > 0
        )

    # ------------------------------------------------------------------
    # Combined access
    # ------------------------------------------------------------------

    def combined_prompt(self) -> str:
        """
        Return both prompts concatenated with a separator.

        Useful for single-prompt providers that do not distinguish between
        system and user roles.

        Returns:
            A single string containing system and user prompts separated
            by a Markdown horizontal rule.
        """
        return (
            self.system_prompt.rstrip()
            + "\n\n---\n\n"
            + self.user_prompt.lstrip()
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain-dict representation of this result."""
        return {
            "system_prompt": self.system_prompt,
            "user_prompt": self.user_prompt,
            "estimated_tokens": self.estimated_tokens,
            "metadata": dict(self.metadata),
            "word_count": self.word_count(),
            "char_count": self.char_count(),
            "line_count": self.line_count(),
            "is_valid": self.is_valid(),
        }

    def summary(self) -> str:
        """Return a one-line diagnostic summary of this result."""
        role = self.metadata.get("employee_role", "unknown")
        stage = self.metadata.get("workflow_stage", "unknown")
        return (
            f"[{role}] "
            f"stage={stage!r} "
            f"tokens~={self.estimated_tokens} "
            f"words={self.word_count()} "
            f"lines={self.line_count()}"
        )
