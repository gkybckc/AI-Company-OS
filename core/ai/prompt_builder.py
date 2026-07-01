"""
Prompt Builder for AI Company OS.

The PromptBuilder converts a structured PromptContext into a PromptResult
containing a system prompt and a user prompt.  It is the authoritative
source of prompt construction logic within Layer 2 (Intelligence Layer).

Responsibilities
----------------
- Assemble system and user prompts from PromptTemplate sections.
- Inject default company rules when the context does not supply them.
- Validate context before building and raise an error on failure.
- Estimate token counts for capacity planning.
- Track build history and expose aggregate statistics.

This module knows NOTHING about Claude, OpenAI, Ollama, or any provider.
It only builds prompts.  The caller takes the PromptResult, constructs a
ProviderRequest from it, and submits it through the ProviderRegistry.

Architecture reference: §2.10 LLM Gateway, §3 Layer 2 (Intelligence Layer),
Architectural Constraint 6: "The LLM Gateway is the only authorized path
to external intelligence."
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from core.ai.prompt_context import PromptContext, PromptContextError
from core.ai.prompt_result import PromptResult
from core.ai.prompt_template import PromptTemplate


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class PromptBuilderError(Exception):
    """Base exception for all PromptBuilder errors."""


class InvalidContextError(PromptBuilderError):
    """
    Raised when a PromptContext fails validation inside build().

    The exception message lists every validation error so the caller can
    present actionable feedback.
    """


class BuildError(PromptBuilderError):
    """
    Raised when prompt assembly fails for an unexpected reason.

    This should be rare.  If it occurs it indicates a programmer error in
    the PromptTemplate or PromptBuilder, not a user input error.
    """


# ---------------------------------------------------------------------------
# Default company rules (derived from the AI Company OS Constitution)
# ---------------------------------------------------------------------------

_DEFAULT_COMPANY_RULES: List[str] = [
    "CEO Sovereignty: All significant decisions require explicit CEO approval before execution.",
    "Authority Chain: Follow the hierarchy -- CEO > Chief Architect > Executive AI > Department Directors > Agents.",
    "Quality First: Output must meet the standard of a competent senior professional in your domain.",
    "Transparency: Every action and decision must be observable and documented in company memory.",
    "Scope Discipline: Work only within your defined domain. Escalate out-of-scope tasks immediately.",
    "Honesty: Never misrepresent your status, capabilities, or output quality.",
    "Security: Never include credentials, API keys, secrets, or sensitive data in any output.",
    "Definition of Done: A task is not complete until it has received explicit approval from the appropriate authority.",
]

_BUILDER_VERSION = "1.0"
_TOKENS_PER_WORD = 1.3


# ---------------------------------------------------------------------------
# PromptBuilder
# ---------------------------------------------------------------------------

class PromptBuilder:
    """
    Deterministic, stateful prompt assembler.

    Usage pattern:
        builder = PromptBuilder()
        context = PromptContext(
            employee_role="Backend Agent",
            department="Engineering",
            ...
        )
        result = builder.build(context)
        # result.system_prompt and result.user_prompt are ready to use.

    The builder accumulates a history of every PromptResult it produces.
    statistics() returns aggregate metrics over the build history.
    """

    def __init__(self) -> None:
        self._history: List[PromptResult] = []
        self._contexts: List[PromptContext] = []

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def build(self, context: PromptContext) -> PromptResult:
        """
        Build a PromptResult from the given context.

        Validates the context, assembles system and user prompts from
        PromptTemplate sections, estimates token counts, and records the
        result in the build history.

        Args:
            context: The structured input describing the agent, project,
                     and task.

        Returns:
            A PromptResult with non-empty system and user prompts.

        Raises:
            InvalidContextError: If the context fails validation.
            BuildError:          If prompt assembly fails unexpectedly.
        """
        errors = self.validate(context)
        if errors:
            raise InvalidContextError(
                "PromptContext validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

        try:
            system_prompt = self._build_system_prompt(context)
            user_prompt = self._build_user_prompt(context)
        except Exception as exc:
            raise BuildError(f"Prompt assembly failed: {exc}") from exc

        estimated_tokens = (
            self.estimate_tokens(system_prompt)
            + self.estimate_tokens(user_prompt)
        )

        result = PromptResult(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            estimated_tokens=estimated_tokens,
            metadata=self._build_metadata(context),
        )

        self._history.append(result)
        self._contexts.append(context)
        return result

    def estimate_tokens(self, text: str) -> int:
        """
        Return an approximate token count for the given text.

        Uses a word-based approximation: each whitespace-delimited word
        contributes approximately 1.3 tokens (accounting for punctuation,
        Markdown markup, and subword tokenisation overhead).  This is not
        exact but is sufficient for capacity planning.

        Args:
            text: The text to estimate.

        Returns:
            A non-negative integer token estimate.  Returns 0 for blank input.
        """
        if not text or not text.strip():
            return 0
        word_count = len(text.split())
        return max(1, int(word_count * _TOKENS_PER_WORD))

    def validate(self, context: PromptContext) -> List[str]:
        """
        Validate a PromptContext without building a prompt.

        Returns a list of error messages.  An empty list means the context
        is valid and ready to pass to build().

        This method never raises.  All errors are returned as strings so
        the caller can decide how to present them.

        Args:
            context: The context to validate.

        Returns:
            List of validation error strings, or empty list if valid.
        """
        errors: List[str] = []

        required_fields = {
            "employee_role": context.employee_role,
            "department": context.department,
            "project_name": context.project_name,
            "project_description": context.project_description,
            "workflow_stage": context.workflow_stage,
            "task_description": context.task_description,
        }
        for field_name, value in required_fields.items():
            if not value or not str(value).strip():
                errors.append(f"'{field_name}' must not be blank.")

        if not isinstance(context.company_rules, list):
            errors.append("'company_rules' must be a list.")

        if not isinstance(context.constraints, list):
            errors.append("'constraints' must be a list.")

        return errors

    def statistics(self) -> Dict[str, Any]:
        """
        Return aggregate metrics over the build history.

        Returns:
            A dictionary with keys:
              total_builds           (int)
              total_estimated_tokens (int)
              avg_tokens_per_build   (float)
              avg_system_words       (float)
              avg_user_words         (float)
              avg_constraints        (float)
              avg_rules              (float)
              roles_used             (list of str, unique, sorted)
              departments_used       (list of str, unique, sorted)
              workflow_stages_used   (list of str, unique, sorted)
              builder_version        (str)
        """
        total = len(self._history)
        if total == 0:
            return {
                "total_builds": 0,
                "total_estimated_tokens": 0,
                "avg_tokens_per_build": 0.0,
                "avg_system_words": 0.0,
                "avg_user_words": 0.0,
                "avg_constraints": 0.0,
                "avg_rules": 0.0,
                "roles_used": [],
                "departments_used": [],
                "workflow_stages_used": [],
                "builder_version": _BUILDER_VERSION,
            }

        total_tokens = sum(r.estimated_tokens for r in self._history)
        total_sys_words = sum(r.system_word_count() for r in self._history)
        total_usr_words = sum(r.user_word_count() for r in self._history)
        total_constraints = sum(c.constraint_count() for c in self._contexts)
        total_rules = sum(c.rule_count() for c in self._contexts)

        roles = sorted({c.employee_role for c in self._contexts})
        departments = sorted({c.department for c in self._contexts})
        stages = sorted({c.workflow_stage for c in self._contexts})

        return {
            "total_builds": total,
            "total_estimated_tokens": total_tokens,
            "avg_tokens_per_build": round(total_tokens / total, 2),
            "avg_system_words": round(total_sys_words / total, 2),
            "avg_user_words": round(total_usr_words / total, 2),
            "avg_constraints": round(total_constraints / total, 2),
            "avg_rules": round(total_rules / total, 2),
            "roles_used": roles,
            "departments_used": departments,
            "workflow_stages_used": stages,
            "builder_version": _BUILDER_VERSION,
        }

    # ------------------------------------------------------------------
    # History access
    # ------------------------------------------------------------------

    def history(self) -> List[PromptResult]:
        """Return all PromptResults in build order."""
        return list(self._history)

    def last_result(self) -> PromptResult:
        """
        Return the most recently built PromptResult.

        Raises:
            PromptBuilderError: If no prompts have been built yet.
        """
        if not self._history:
            raise PromptBuilderError("No prompts have been built yet.")
        return self._history[-1]

    def total_builds(self) -> int:
        """Return the total number of prompts built."""
        return len(self._history)

    # ------------------------------------------------------------------
    # Internal assembly
    # ------------------------------------------------------------------

    def _build_system_prompt(self, context: PromptContext) -> str:
        """Assemble the system prompt from PromptTemplate sections."""
        parts: List[str] = []

        parts.append(
            PromptTemplate.render_system_header(
                context.employee_role,
                context.department,
                context.seniority,
            )
        )

        if context.has_seniority():
            guidance = PromptTemplate.render_seniority_guidance(context.seniority)
            if guidance:
                parts.append(guidance)

        rules = (
            context.company_rules
            if context.has_rules()
            else _DEFAULT_COMPANY_RULES
        )
        parts.append(PromptTemplate.render_governance_section(rules))
        parts.append(PromptTemplate.render_quality_standard(context.employee_role))
        parts.append(PromptTemplate.render_output_instructions(context.employee_role))
        parts.append(PromptTemplate.render_escalation_reminder())

        return "\n".join(parts)

    def _build_user_prompt(self, context: PromptContext) -> str:
        """Assemble the user prompt from PromptTemplate sections."""
        parts: List[str] = []

        parts.append(
            PromptTemplate.render_project_section(
                context.project_name,
                context.project_description,
                context.workflow_stage,
                context.project_id or "",
            )
        )

        if context.has_context():
            parts.append(
                PromptTemplate.render_additional_context(context.context)
            )

        parts.append(PromptTemplate.render_task_section(context.task_description))

        if context.has_constraints():
            parts.append(
                PromptTemplate.render_constraints_section(context.constraints)
            )

        parts.append(
            PromptTemplate.render_completion_note(
                context.employee_role,
                context.workflow_stage,
            )
        )

        return "\n".join(parts)

    def _build_metadata(self, context: PromptContext) -> Dict[str, Any]:
        """Build the metadata dict for a PromptResult."""
        return {
            "employee_role": context.employee_role,
            "department": context.department,
            "project_name": context.project_name,
            "workflow_stage": context.workflow_stage,
            "seniority": context.seniority,
            "constraint_count": context.constraint_count(),
            "rule_count": (
                context.rule_count()
                if context.has_rules()
                else len(_DEFAULT_COMPANY_RULES)
            ),
            "used_default_rules": not context.has_rules(),
            "builder_version": _BUILDER_VERSION,
            "built_at": datetime.now(timezone.utc).isoformat(),
        }
