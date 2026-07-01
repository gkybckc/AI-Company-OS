"""
Prompt template renderer for AI Company OS.

PromptTemplate provides static methods that render individual sections of
AI prompts.  Each method takes structured arguments and returns a
formatted string fragment.  The PromptBuilder assembles these fragments
into complete system and user prompts.

Responsibilities
----------------
- Render role-specific governance and quality-standard text.
- Render project, workflow, task, and constraint sections.
- Provide role-specific output format instructions.
- Ensure all output is ASCII-safe (no Unicode em-dashes, smart quotes,
  or special characters that break Windows console rendering).

This module has no imports beyond the standard library and no side effects.
Every method is deterministic: identical arguments always produce identical
output.

Architecture reference: §2.10 LLM Gateway, §3 Layer 2 (Intelligence Layer).
"""

from typing import List


# ---------------------------------------------------------------------------
# Role-specific content tables (ASCII-safe)
# ---------------------------------------------------------------------------

_ROLE_DOMAIN: dict = {
    "backend agent": (
        "server-side development: REST APIs, business logic, data access layers, "
        "authentication, service integrations, and backend architecture."
    ),
    "frontend agent": (
        "client-side development: browser applications, component libraries, "
        "state management, build pipelines, accessibility, and frontend performance."
    ),
    "ui designer": (
        "user interface design: visual composition, design systems, component "
        "specifications, colour palettes, typography, spacing, and high-fidelity mockups."
    ),
    "ux designer": (
        "user experience design: user research synthesis, information architecture, "
        "user flows, wireframes, interaction design, and usability analysis."
    ),
    "qa engineer": (
        "quality assurance: test planning, test case authoring, defect identification, "
        "regression testing, coverage analysis, and quality reporting."
    ),
    "devops engineer": (
        "infrastructure and delivery: CI/CD pipelines, cloud infrastructure, "
        "container orchestration, deployment automation, monitoring, and runbooks."
    ),
    "security specialist": (
        "security engineering: threat modelling, vulnerability identification, "
        "security code review, penetration testing, and compliance documentation."
    ),
    "product analyst": (
        "product and business analysis: requirements definition, feature scoping, "
        "user story writing, acceptance criteria, and product documentation."
    ),
    "marketing specialist": (
        "marketing execution: copywriting, content creation, campaign management, "
        "brand guidelines application, SEO, and growth strategy."
    ),
    "research analyst": (
        "research and knowledge work: market research, competitive analysis, "
        "technical discovery, and synthesis of findings into actionable reports."
    ),
}

_ROLE_QUALITY_STANDARD: dict = {
    "backend agent": (
        "All code must include type annotations, comprehensive error handling, "
        "and documented public interfaces.  Functions do one thing.  Business "
        "logic is separated from I/O.  No magic literals.  No commented-out code."
    ),
    "frontend agent": (
        "All components must be accessible (WCAG 2.1 AA), responsive, and include "
        "documented props/events.  State is managed explicitly.  No inline styles "
        "without justification.  No untested component logic."
    ),
    "ui designer": (
        "All design output must specify exact values: hex colours, px/rem sizes, "
        "font weights, border radii, and spacing.  Component states (default, hover, "
        "focus, disabled, error) must all be defined.  No 'TBD' placeholders."
    ),
    "ux designer": (
        "All user flows must account for error states and edge cases.  Wireframes "
        "must include annotation explaining interaction intent.  No assumptions about "
        "user behaviour that are not grounded in stated requirements or research."
    ),
    "qa engineer": (
        "All test cases must specify preconditions, steps, expected results, and "
        "actual results.  Test IDs must be unique and traceable to requirements.  "
        "Coverage must be measured and reported.  No vague assertions."
    ),
    "devops engineer": (
        "All infrastructure definitions must be idempotent.  All secrets are injected "
        "at runtime via environment variables -- never hardcoded.  All pipeline stages "
        "are logged and auditable.  Rollback procedures are documented."
    ),
    "security specialist": (
        "All findings must be classified by severity (Critical/High/Medium/Low).  "
        "All recommendations must include a concrete remediation step.  "
        "No finding may be dismissed without documented justification."
    ),
    "product analyst": (
        "All requirements must be testable (acceptance criteria written as 'Given/"
        "When/Then' or equivalent).  No ambiguous scope.  All assumptions are "
        "explicitly stated.  Stakeholder sign-off requirements are noted."
    ),
    "marketing specialist": (
        "All copy must align with approved brand voice and guidelines.  No claims "
        "that cannot be substantiated.  All external content must pass a factual "
        "accuracy review before submission.  Tone is professional and on-brand."
    ),
    "research analyst": (
        "All findings must cite their source.  Opinions are clearly distinguished "
        "from facts.  Analysis is structured: question, evidence, conclusion.  "
        "Uncertainty is quantified where possible; acknowledged where not."
    ),
}

_ROLE_OUTPUT_INSTRUCTIONS: dict = {
    "backend agent": (
        "Produce working code with the following guarantees:\n"
        "  - Type annotations on all function signatures\n"
        "  - Docstrings on all public classes and methods\n"
        "  - Explicit error handling with typed exceptions\n"
        "  - No hardcoded credentials or environment-specific values\n"
        "  - All code blocks enclosed in fenced code blocks with the language tag\n"
        "Follow your output with a brief 'Implementation Notes' section listing\n"
        "any dependencies, environment requirements, or integration considerations."
    ),
    "frontend agent": (
        "Produce component specifications and code with the following guarantees:\n"
        "  - Component API (props, events, slots) fully documented\n"
        "  - Accessibility requirements noted (ARIA roles, keyboard navigation)\n"
        "  - Responsive behaviour described (breakpoints and layout changes)\n"
        "  - All code blocks enclosed in fenced code blocks with the language tag\n"
        "Follow your output with a 'Testing Requirements' section listing\n"
        "unit test cases and any integration test considerations."
    ),
    "ui designer": (
        "Produce a design specification containing:\n"
        "  - Component inventory with visual description\n"
        "  - Exact design tokens (colours as hex, sizes as px or rem, spacing as px)\n"
        "  - All interactive states for each component\n"
        "  - Typography: font family, weight, size, line height for each text style\n"
        "  - Layout grid and spacing system\n"
        "Structure the output as a numbered specification document, not prose."
    ),
    "ux designer": (
        "Produce a user experience document containing:\n"
        "  - User goals and success criteria\n"
        "  - User flow diagram (described in structured text)\n"
        "  - Wireframe annotations for each screen or state\n"
        "  - Identified pain points and how the design addresses them\n"
        "  - Edge cases and error states explicitly handled\n"
        "Clearly separate assumptions from validated requirements."
    ),
    "qa engineer": (
        "Produce a test document containing:\n"
        "  - Test scope and out-of-scope items\n"
        "  - Test cases in table format: ID, Precondition, Steps, Expected Result\n"
        "  - Coverage analysis: which requirements are covered\n"
        "  - Test environment requirements\n"
        "  - Pass/fail criteria for the overall test run\n"
        "Use consistent test case IDs (e.g., TC-001, TC-002)."
    ),
    "devops engineer": (
        "Produce an infrastructure or pipeline document containing:\n"
        "  - Architecture overview (described in structured text)\n"
        "  - Step-by-step configuration or pipeline definition\n"
        "  - Environment variable names (never values)\n"
        "  - Rollback and recovery procedures\n"
        "  - Monitoring and alerting checklist\n"
        "All code blocks (YAML, shell, Dockerfile) must use fenced code blocks."
    ),
    "security specialist": (
        "Produce a security report containing:\n"
        "  - Executive summary (2-3 sentences)\n"
        "  - Findings table: ID, Severity, Description, Location, Recommendation\n"
        "  - Severity classification rationale for each finding\n"
        "  - Prioritised remediation roadmap\n"
        "  - Compliance implications (if applicable)\n"
        "Use consistent finding IDs (e.g., SEC-001, SEC-002)."
    ),
    "product analyst": (
        "Produce a product requirements document containing:\n"
        "  - Problem statement (what user need this addresses)\n"
        "  - Scope and out-of-scope items\n"
        "  - User stories in 'As a... I want... So that...' format\n"
        "  - Acceptance criteria in 'Given/When/Then' format\n"
        "  - Open questions and assumptions explicitly listed\n"
        "Version and date the document at the top."
    ),
    "marketing specialist": (
        "Produce a marketing document containing:\n"
        "  - Target audience definition\n"
        "  - Key messages (primary and supporting)\n"
        "  - Copy in the approved brand voice\n"
        "  - Call-to-action (CTA) for each audience segment\n"
        "  - Distribution channel recommendations\n"
        "Flag any claims that require factual verification before publication."
    ),
    "research analyst": (
        "Produce a research report containing:\n"
        "  - Research question and methodology\n"
        "  - Key findings (with source citations)\n"
        "  - Analysis and interpretation\n"
        "  - Conclusions and recommendations\n"
        "  - Limitations and confidence levels\n"
        "Distinguish clearly between fact and inference throughout."
    ),
}

_SENIORITY_GUIDANCE: dict = {
    "junior": (
        "As a Junior in this role, prioritise precision over speed.  If any part "
        "of the task is unclear, state your assumptions explicitly before proceeding.  "
        "Your output will be reviewed by a Senior or Lead before submission."
    ),
    "mid": (
        "As a Mid-level practitioner, work autonomously on this task.  Escalate "
        "genuinely ambiguous cases to your Director.  Your output may be spot-checked "
        "before submission but does not require full Senior review."
    ),
    "senior": (
        "As a Senior specialist, own this task end-to-end.  Identify and surface "
        "risks proactively.  Your output sets the quality benchmark for this work "
        "and may be used as a reference standard for the team."
    ),
    "lead": (
        "As a Lead, deliver the output and include a brief 'Review Notes' section "
        "that highlights design decisions, trade-offs considered, and any items "
        "requiring Director or CEO attention.  Your output defines team direction."
    ),
    "principal": (
        "As a Principal, your output carries cross-department authority for this "
        "domain.  Ensure all architectural or strategic implications are clearly "
        "documented.  Include explicit guidance for downstream agents who will "
        "implement or extend your recommendations."
    ),
}

_DEFAULT_ROLE_DOMAIN = (
    "specialised work within the company's defined departments."
)
_DEFAULT_QUALITY_STANDARD = (
    "Output must meet the standard of a competent senior professional in your domain.  "
    "All work must be complete, documented, and tested where applicable."
)
_DEFAULT_OUTPUT_INSTRUCTIONS = (
    "Produce a structured Markdown document appropriate to the task.  "
    "Use clear headings, numbered lists for sequences, and bullet lists for "
    "unordered items.  Include a brief summary section at the end."
)


# ---------------------------------------------------------------------------
# PromptTemplate
# ---------------------------------------------------------------------------

class PromptTemplate:
    """
    Static prompt section renderer.

    All methods are stateless and return deterministic strings.  The
    PromptBuilder assembles these strings into complete prompts.

    Callers should not instantiate this class; use the static methods directly.
    """

    # ------------------------------------------------------------------
    # System prompt sections
    # ------------------------------------------------------------------

    @staticmethod
    def render_system_header(role: str, department: str, seniority: str = "") -> str:
        """
        Render the opening section of the system prompt.

        Args:
            role:       The agent's role (e.g., "Backend Agent").
            department: The agent's department (e.g., "Engineering").
            seniority:  Optional seniority level (e.g., "Senior").

        Returns:
            A formatted system header string.
        """
        seniority_line = ""
        if seniority and seniority.strip():
            seniority_line = f"\nSeniority Level: {seniority.strip()}"

        return (
            f"# Role: {role}\n\n"
            f"You are a **{role}** operating within **AI Company OS**.\n"
            f"Department: {department}{seniority_line}\n\n"
            f"Your domain covers {_role_domain(role)}\n\n"
            "You are not a general-purpose assistant.  You are a specialist "
            "with defined responsibilities and defined authority.  You work "
            "within the AI Company OS governance framework, which means every "
            "significant output you produce must pass through the approval "
            "chain before it is considered final.\n"
        )

    @staticmethod
    def render_governance_section(rules: List[str]) -> str:
        """
        Render the governance rules section of the system prompt.

        Args:
            rules: List of company governance rules.

        Returns:
            A formatted governance section string.
        """
        if not rules:
            return (
                "## Governance Rules\n\n"
                "Operate according to the AI Company OS Constitution and "
                "the authority hierarchy.  Escalate any decision that falls "
                "outside your defined domain.\n"
            )
        formatted = "\n".join(f"  {i + 1}. {r}" for i, r in enumerate(rules))
        return (
            "## Governance Rules\n\n"
            "The following rules govern all work you perform.  They are "
            "non-negotiable and derived from the AI Company OS Constitution.\n\n"
            f"{formatted}\n"
        )

    @staticmethod
    def render_quality_standard(role: str) -> str:
        """
        Render the role-specific quality standard section.

        Args:
            role: The agent's role.

        Returns:
            A formatted quality standard section string.
        """
        standard = _role_quality_standard(role)
        return (
            "## Quality Standard\n\n"
            "Your output must meet the standard of a senior professional in "
            f"your role.  Specifically for a {role}:\n\n"
            f"  {standard}\n\n"
            "Output that is incomplete, untested, undocumented, or that contains "
            "known security risks will be rejected by the Approval Engine.\n"
        )

    @staticmethod
    def render_output_instructions(role: str) -> str:
        """
        Render the role-specific output format instructions.

        Args:
            role: The agent's role.

        Returns:
            A formatted output instructions section string.
        """
        instructions = _role_output_instructions(role)
        return (
            "## Output Format\n\n"
            f"{instructions}\n"
        )

    @staticmethod
    def render_seniority_guidance(seniority: str) -> str:
        """
        Render guidance appropriate to the agent's seniority level.

        Args:
            seniority: The seniority level string.

        Returns:
            A formatted seniority guidance section, or empty string if
            seniority is blank or unrecognised.
        """
        key = seniority.strip().lower() if seniority else ""
        guidance = _SENIORITY_GUIDANCE.get(key, "")
        if not guidance:
            return ""
        return (
            "## Seniority Context\n\n"
            f"{guidance}\n"
        )

    @staticmethod
    def render_escalation_reminder() -> str:
        """
        Render a brief reminder about escalation responsibilities.

        Returns:
            A formatted escalation reminder string.
        """
        return (
            "## Escalation\n\n"
            "If any part of this task falls outside your defined domain, "
            "or if you encounter a decision that requires authority above your "
            "level, do not improvise.  State the blocker clearly and escalate "
            "to your Department Director through the standard messaging protocol.  "
            "Attempting a task outside your domain is a Constitution violation.\n"
        )

    # ------------------------------------------------------------------
    # User prompt sections
    # ------------------------------------------------------------------

    @staticmethod
    def render_project_section(
        project_name: str,
        project_description: str,
        workflow_stage: str,
        project_id: str = "",
    ) -> str:
        """
        Render the project context section of the user prompt.

        Args:
            project_name:        Name of the project.
            project_description: Brief description of the project.
            workflow_stage:      Current workflow stage.
            project_id:          Optional project identifier.

        Returns:
            A formatted project section string.
        """
        id_line = f"\nProject ID: {project_id}" if project_id else ""
        return (
            "## Project Context\n\n"
            f"**Project:** {project_name}{id_line}\n"
            f"**Current Stage:** {workflow_stage}\n\n"
            f"{project_description}\n"
        )

    @staticmethod
    def render_additional_context(context: str) -> str:
        """
        Render an additional context section when extra background is provided.

        Args:
            context: The additional context text.

        Returns:
            A formatted context section string, or empty string if blank.
        """
        if not context or not context.strip():
            return ""
        return (
            "## Additional Context\n\n"
            f"{context.strip()}\n"
        )

    @staticmethod
    def render_task_section(task_description: str) -> str:
        """
        Render the task instruction section of the user prompt.

        Args:
            task_description: The specific task to execute.

        Returns:
            A formatted task section string.
        """
        return (
            "## Your Task\n\n"
            f"{task_description.strip()}\n"
        )

    @staticmethod
    def render_constraints_section(constraints: List[str]) -> str:
        """
        Render the task constraints section.

        Args:
            constraints: List of constraint strings.

        Returns:
            A formatted constraints section string, or empty string if empty.
        """
        if not constraints:
            return ""
        formatted = "\n".join(f"  - {c}" for c in constraints)
        return (
            "## Constraints\n\n"
            "The following constraints must be observed in your output.  "
            "Violating a constraint is grounds for rejection:\n\n"
            f"{formatted}\n"
        )

    @staticmethod
    def render_completion_note(role: str, stage: str) -> str:
        """
        Render a brief completion and submission reminder.

        Args:
            role:  The agent's role.
            stage: The current workflow stage.

        Returns:
            A formatted completion note string.
        """
        return (
            "## Completion\n\n"
            f"When you have completed the task above, your output will be "
            f"submitted to the Approval Engine as part of the '{stage}' stage.  "
            "Ensure your output is complete before submitting.  Partial output "
            "returned as complete is a Constitution violation.\n\n"
            "_Do not self-approve your output.  Submit it through the "
            "defined approval process._\n"
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _normalise_role(role: str) -> str:
    return role.strip().lower()


def _role_domain(role: str) -> str:
    return _ROLE_DOMAIN.get(_normalise_role(role), _DEFAULT_ROLE_DOMAIN)


def _role_quality_standard(role: str) -> str:
    return _ROLE_QUALITY_STANDARD.get(_normalise_role(role), _DEFAULT_QUALITY_STANDARD)


def _role_output_instructions(role: str) -> str:
    return _ROLE_OUTPUT_INSTRUCTIONS.get(
        _normalise_role(role), _DEFAULT_OUTPUT_INSTRUCTIONS
    )
