"""
Demo: Prompt Builder -- Feature 17.2

Shows how the PromptBuilder converts structured PromptContext objects into
system + user prompts for five different agent roles.

The builder knows nothing about any AI provider -- it only builds prompts.

Run from the repo root:
    python -m examples.demo_prompt_builder
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai.prompt_context import PromptContext
from core.ai.prompt_builder import PromptBuilder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SEP = "=" * 72
SEP_THIN = "-" * 72


def section(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def subsection(title: str) -> None:
    print(f"\n{SEP_THIN}")
    print(f"  {title}")
    print(SEP_THIN)


def show_result(builder: PromptBuilder, context: PromptContext) -> None:
    result = builder.build(context)
    print(f"\nContext summary: {context.summary()}")
    print(f"Estimated tokens: {result.estimated_tokens}")
    print(f"Word count: {result.word_count()}")
    print(f"Line count: {result.line_count()}")
    print(f"Is valid: {result.is_valid()}")
    print(f"Used default rules: {result.metadata.get('used_default_rules')}")

    subsection("System Prompt (first 25 lines)")
    lines = result.system_prompt.splitlines()
    for line in lines[:25]:
        print(line)
    if len(lines) > 25:
        print(f"  ... ({len(lines) - 25} more lines)")

    subsection("User Prompt (first 20 lines)")
    lines = result.user_prompt.splitlines()
    for line in lines[:20]:
        print(line)
    if len(lines) > 20:
        print(f"  ... ({len(lines) - 20} more lines)")


# ---------------------------------------------------------------------------
# Demo 1: Backend Agent
# ---------------------------------------------------------------------------

def demo_backend_agent(builder: PromptBuilder) -> None:
    section("DEMO 1 -- Backend Agent: Authentication API")

    context = PromptContext(
        employee_role="Backend Agent",
        department="Engineering",
        project_name="AI Company OS",
        project_description=(
            "An autonomous operating system for running a full technology company "
            "powered entirely by AI agents under CEO governance."
        ),
        workflow_stage="Implementation",
        task_description=(
            "Implement the REST API for user authentication using JWT tokens. "
            "The API must support registration, login, refresh, and logout endpoints."
        ),
        constraints=[
            "Use RS256 JWT (asymmetric), not HS256",
            "Password hashing: bcrypt with cost factor 12",
            "Rate limit: 5 failed logins per IP per 60 seconds",
            "REST only -- no GraphQL",
            "No hardcoded secrets",
        ],
        seniority="Senior",
        project_id="proj-auth-001",
        context="PostgreSQL 15 for persistence. FastAPI framework. Python 3.12.",
    )

    show_result(builder, context)


# ---------------------------------------------------------------------------
# Demo 2: Frontend Agent
# ---------------------------------------------------------------------------

def demo_frontend_agent(builder: PromptBuilder) -> None:
    section("DEMO 2 -- Frontend Agent: CEO Dashboard Component")

    context = PromptContext(
        employee_role="Frontend Agent",
        department="Frontend",
        project_name="CEO Dashboard",
        project_description=(
            "A real-time dashboard that gives the CEO a complete view of "
            "company operations: active projects, pending approvals, agent "
            "statuses, and system health."
        ),
        workflow_stage="Implementation",
        task_description=(
            "Implement the KPI summary card component. The card displays "
            "a metric name, current value, percentage change, and trend icon."
        ),
        constraints=[
            "React 18 with TypeScript",
            "WCAG 2.1 AA accessibility",
            "Responsive: mobile-first design",
            "No inline styles -- use the design token system",
        ],
        seniority="Mid",
    )

    show_result(builder, context)


# ---------------------------------------------------------------------------
# Demo 3: UI Designer
# ---------------------------------------------------------------------------

def demo_designer(builder: PromptBuilder) -> None:
    section("DEMO 3 -- UI Designer: Button Component Specification")

    context = PromptContext(
        employee_role="UI Designer",
        department="Design",
        project_name="AI Company OS Design System",
        project_description=(
            "A unified design system covering all visual components used across "
            "the CEO Dashboard and agent interfaces."
        ),
        workflow_stage="Design",
        task_description=(
            "Define the complete specification for the Button component. "
            "Cover all variants (primary, secondary, danger, ghost) and all "
            "interactive states (default, hover, focus, active, disabled, loading)."
        ),
        constraints=[
            "Follow the existing colour palette (no new colours)",
            "WCAG 2.1 AA contrast ratios required",
            "Specify exact px values for all sizing tokens",
        ],
        seniority="Lead",
    )

    show_result(builder, context)


# ---------------------------------------------------------------------------
# Demo 4: QA Engineer
# ---------------------------------------------------------------------------

def demo_qa_engineer(builder: PromptBuilder) -> None:
    section("DEMO 4 -- QA Engineer: Authentication Module Test Plan")

    context = PromptContext(
        employee_role="QA Engineer",
        department="QA",
        project_name="AI Company OS",
        project_description=(
            "An autonomous operating system for running a technology company "
            "powered by AI agents."
        ),
        workflow_stage="Testing",
        task_description=(
            "Write a comprehensive test plan for the authentication module "
            "covering all API endpoints: register, login, refresh, logout, "
            "and the /me profile endpoint."
        ),
        constraints=[
            "Minimum 90% branch coverage",
            "No mocking the database in integration tests",
            "All edge cases for invalid input must be covered",
            "Security test cases required for each endpoint",
        ],
        seniority="Senior",
        company_rules=[
            "All tests must be traceable to a requirement.",
            "Coverage must be measured and reported in the test summary.",
            "No test may be skipped without documented justification.",
        ],
    )

    show_result(builder, context)


# ---------------------------------------------------------------------------
# Demo 5: Marketing Specialist
# ---------------------------------------------------------------------------

def demo_marketing(builder: PromptBuilder) -> None:
    section("DEMO 5 -- Marketing Specialist: Beta Launch Announcement")

    context = PromptContext(
        employee_role="Marketing Specialist",
        department="Marketing",
        project_name="AI Company OS Beta Launch",
        project_description=(
            "The beta release of AI Company OS -- the world's first autonomous "
            "operating system for running a technology company with a single human CEO."
        ),
        workflow_stage="Design",
        task_description=(
            "Write the launch announcement copy for the company website homepage. "
            "The copy must explain what AI Company OS is, who it is for, and "
            "include a compelling call-to-action for the early-access waitlist."
        ),
        constraints=[
            "Professional but accessible tone",
            "No unsubstantiated claims about AI capabilities",
            "Target audience: solo technical founders",
            "Maximum 250 words for the hero section",
            "Include one primary CTA and one secondary CTA",
        ],
        seniority="Senior",
    )

    show_result(builder, context)


# ---------------------------------------------------------------------------
# Demo 6: Registry statistics
# ---------------------------------------------------------------------------

def demo_statistics(builder: PromptBuilder) -> None:
    section("DEMO 6 -- Builder Statistics")

    stats = builder.statistics()
    print(f"\n  Total builds           : {stats['total_builds']}")
    print(f"  Total estimated tokens : {stats['total_estimated_tokens']}")
    print(f"  Avg tokens per build   : {stats['avg_tokens_per_build']}")
    print(f"  Avg system words       : {stats['avg_system_words']}")
    print(f"  Avg user words         : {stats['avg_user_words']}")
    print(f"  Avg constraints        : {stats['avg_constraints']}")
    print(f"  Builder version        : {stats['builder_version']}")
    print(f"\n  Roles used       : {stats['roles_used']}")
    print(f"  Departments used : {stats['departments_used']}")
    print(f"  Stages used      : {stats['workflow_stages_used']}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print(SEP)
    print("  AI Company OS -- Feature 17.2: Prompt Builder Demo")
    print(SEP)
    print("\nThe PromptBuilder converts structured PromptContext objects")
    print("into system + user prompts. It knows nothing about any AI provider.")

    builder = PromptBuilder()

    demo_backend_agent(builder)
    demo_frontend_agent(builder)
    demo_designer(builder)
    demo_qa_engineer(builder)
    demo_marketing(builder)
    demo_statistics(builder)

    section("DEMO COMPLETE")
    print(f"\n  {builder.total_builds()} prompts built across 5 agent roles.")
    print("  All prompts are deterministic: identical inputs always produce")
    print("  identical system and user prompts.")
    print("  The PromptBuilder knows nothing about Claude, OpenAI, or any provider.")


if __name__ == "__main__":
    main()
