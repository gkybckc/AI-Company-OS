"""
Prompt context model for AI Company OS.

A PromptContext is the structured input the PromptBuilder consumes to
produce a PromptResult.  Every field represents a dimension of context
that the builder uses to tailor the generated prompts to the specific
agent, project, and task at hand.

Callers assemble a PromptContext from the information they have about the
current task assignment, then hand it to PromptBuilder.build().  The builder
never asks for raw strings -- it always receives a validated context object.

Architecture reference: §2.10 LLM Gateway, §3 Layer 2 (Intelligence Layer),
§6 Agent Lifecycle, Constitution Chapter 6 (Agent Responsibilities).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class PromptContextError(Exception):
    """Raised when a PromptContext fails validation."""


# ---------------------------------------------------------------------------
# PromptContext
# ---------------------------------------------------------------------------

@dataclass
class PromptContext:
    """
    Structured input for the PromptBuilder.

    Every field contributes to the quality and specificity of the generated
    prompts.  The required fields (employee_role, department,
    project_name, project_description, workflow_stage, task_description)
    must be non-blank.  All optional fields are safe to omit.

    Attributes:
        employee_role:       The role the agent is playing within the company
                             (e.g., "Backend Agent", "QA Engineer").  Used to
                             select role-specific quality standards and output
                             format instructions in the generated prompts.

        department:          The functional department the agent belongs to
                             (e.g., "Engineering", "Design").  Provides
                             organisational context for the system prompt.

        project_name:        Short name of the project this task belongs to.
                             Anchors the user prompt to a specific deliverable.

        project_description: One or two sentences describing what the project
                             is building and why.  Gives the agent strategic
                             context without overloading the prompt.

        workflow_stage:      The current stage in the project lifecycle
                             (e.g., "Discovery", "Design", "Implementation",
                             "Testing", "Review", "Approval", "Deployment").
                             Used to calibrate the expected output format.

        task_description:    The specific task the agent must execute during
                             this prompt invocation.  Should be concrete and
                             actionable, not strategic.

        company_rules:       An ordered list of governance rules drawn from the
                             Constitution.  If empty, the PromptBuilder injects
                             its default rule set.  Providing rules here lets
                             callers customise or extend the defaults.

        constraints:         Task-specific constraints the agent must observe
                             (e.g., "REST only", "No external libraries").

        project_id:          Optional unique identifier for the project.
                             Included in prompt metadata for traceability.

        context:             Additional background information relevant to the
                             task but not part of the core instruction.
                             Optional; default empty string.

        seniority:           The experience level of the agent
                             ("Junior", "Mid", "Senior", "Lead", "Principal").
                             Influences the guidance tone in the system prompt.
    """

    employee_role: str
    department: str
    project_name: str
    project_description: str
    workflow_stage: str
    task_description: str
    company_rules: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    project_id: Optional[str] = None
    context: str = ""
    seniority: str = ""

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> None:
        """
        Verify that all required fields are non-blank.

        Raises:
            PromptContextError: If any required field is missing or blank.
        """
        required = {
            "employee_role": self.employee_role,
            "department": self.department,
            "project_name": self.project_name,
            "project_description": self.project_description,
            "workflow_stage": self.workflow_stage,
            "task_description": self.task_description,
        }
        for field_name, value in required.items():
            if not value or not str(value).strip():
                raise PromptContextError(
                    f"PromptContext.{field_name} must not be blank."
                )

    # ------------------------------------------------------------------
    # Convenience queries
    # ------------------------------------------------------------------

    def has_rules(self) -> bool:
        """Return True when at least one company rule is present."""
        return bool(self.company_rules)

    def has_constraints(self) -> bool:
        """Return True when at least one constraint is present."""
        return bool(self.constraints)

    def has_context(self) -> bool:
        """Return True when additional context text is present."""
        return bool(self.context and self.context.strip())

    def has_project_id(self) -> bool:
        """Return True when a project identifier is set."""
        return self.project_id is not None

    def has_seniority(self) -> bool:
        """Return True when a seniority level is set."""
        return bool(self.seniority and self.seniority.strip())

    def rule_count(self) -> int:
        """Return the number of company rules."""
        return len(self.company_rules)

    def constraint_count(self) -> int:
        """Return the number of task-specific constraints."""
        return len(self.constraints)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain-dict representation of this context."""
        return {
            "employee_role": self.employee_role,
            "department": self.department,
            "project_name": self.project_name,
            "project_description": self.project_description,
            "workflow_stage": self.workflow_stage,
            "task_description": self.task_description,
            "company_rules": list(self.company_rules),
            "constraints": list(self.constraints),
            "project_id": self.project_id,
            "context": self.context,
            "seniority": self.seniority,
        }

    def summary(self) -> str:
        """Return a one-line diagnostic summary of this context."""
        seniority_tag = f" [{self.seniority}]" if self.has_seniority() else ""
        return (
            f"[{self.employee_role}{seniority_tag}] "
            f"dept={self.department!r} "
            f"project={self.project_name!r} "
            f"stage={self.workflow_stage!r} "
            f"rules={self.rule_count()} "
            f"constraints={self.constraint_count()}"
        )
