"""
Demo: Agent Executor -- Feature 17.3

Walks through the full execution pipeline:
  Backend Agent -> Authentication API Task -> Prompt Generated ->
  Mock Provider -> Artifacts Created -> Memory Updated -> Execution Completed

Run from the repo root:
    python -m examples.demo_agent_executor
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass

from core.ai.agent_executor import AgentExecutor
from core.ai.execution_context import ExecutionContext
from core.ai.prompt_builder import PromptBuilder
from core.ai.provider_registry import ProviderRegistry
from core.ai.mock_provider import MockProvider
from core.artifact_engine import ArtifactEngine
from core.memory_engine import MemoryEngine


# ---------------------------------------------------------------------------
# Lightweight stand-in objects
# ---------------------------------------------------------------------------

@dataclass
class Project:
    id: str
    title: str
    description: str


@dataclass
class Task:
    id: str
    title: str
    description: str


# ---------------------------------------------------------------------------
# Display helpers
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


# ---------------------------------------------------------------------------
# Infrastructure setup
# ---------------------------------------------------------------------------

def setup_infrastructure():
    """Build the ProviderRegistry, PromptBuilder, ArtifactEngine, MemoryEngine."""
    section("STEP 1 -- Infrastructure Setup")

    registry = ProviderRegistry()
    mock = MockProvider()
    registry.register(mock)

    builder = PromptBuilder()
    artifact_engine = ArtifactEngine()
    memory_engine = MemoryEngine()

    print(f"\n  ProviderRegistry  : {registry.count()} provider(s) registered")
    print(f"  Active provider   : {registry.active_name()}")
    print(f"  Provider healthy  : {registry.active_is_healthy()}")
    print(f"  PromptBuilder     : ready (version 1.0)")
    print(f"  ArtifactEngine    : ready")
    print(f"  MemoryEngine      : ready")

    return registry, builder, artifact_engine, memory_engine


# ---------------------------------------------------------------------------
# Demo 1: Backend Agent -- Authentication API
# ---------------------------------------------------------------------------

def demo_backend_auth(executor: AgentExecutor) -> None:
    section("DEMO 1 -- Backend Agent: Authentication API Task")

    project = Project(
        id="proj-auth-001",
        title="AI Company OS",
        description=(
            "An autonomous operating system for running a full technology "
            "company powered entirely by AI agents under CEO governance."
        ),
    )

    task = Task(
        id="task-auth-001",
        title="Implement JWT Authentication API",
        description=(
            "Implement the REST API for user authentication using JWT tokens. "
            "The API must support registration, login, refresh, and logout endpoints."
        ),
    )

    context = ExecutionContext(
        employee_id="agent-backend-001",
        employee_role="Backend Agent",
        department="Engineering",
        project=project,
        workflow_stage="Implementation",
        task=task,
        constraints=[
            "Use RS256 JWT (asymmetric), not HS256",
            "Password hashing: bcrypt with cost factor 12",
            "Rate limit: 5 failed logins per IP per 60 seconds",
            "REST only -- no GraphQL",
            "No hardcoded secrets",
        ],
        seniority="Senior",
        context="PostgreSQL 15 for persistence. FastAPI framework. Python 3.12.",
    )

    subsection("Context")
    print(f"  {context.summary()}")
    print(f"  Project ID   : {context.project_id()}")
    print(f"  Task ID      : {context.task_id()}")
    print(f"  Constraints  : {context.constraint_count()}")

    subsection("Executing...")
    result = executor.execute(context)

    subsection("Result")
    print(f"  Status           : {'SUCCESS' if result.success else 'FAILED'}")
    print(f"  Execution time   : {result.execution_time}s")
    print(f"  Provider         : {result.response_provider_name()}")
    print(f"  Tokens used      : {result.response_token_count()}")
    print(f"  Artifacts        : {result.artifact_count()}")
    print(f"  Memory entries   : {result.memory_count()}")
    print(f"  Warnings         : {result.warning_count()}")
    print(f"  Errors           : {result.error_count()}")

    if result.has_response():
        subsection("Provider Response (first 20 lines)")
        lines = result.response_content().splitlines()
        for line in lines[:20]:
            print(line)
        if len(lines) > 20:
            print(f"  ... ({len(lines) - 20} more lines)")

    if result.has_artifacts():
        subsection("Generated Artifact")
        artifact = result.generated_artifacts[0]
        print(f"  Title   : {artifact.title}")
        print(f"  Type    : {artifact.type}")
        print(f"  Version : {artifact.version}")
        print(f"  Words   : {artifact.word_count()}")

    if result.has_memory_entries():
        subsection("Memory Entry")
        entry = result.memory_entries[0]
        print(f"  Title    : {entry.title}")
        print(f"  Category : {entry.category}")
        print(f"  Scope    : {entry.scope}")
        print(f"  Author   : {entry.author}")
        print(f"  Tags     : {entry.tags}")


# ---------------------------------------------------------------------------
# Demo 2: QA Engineer -- Test Plan
# ---------------------------------------------------------------------------

def demo_qa_agent(executor: AgentExecutor) -> None:
    section("DEMO 2 -- QA Engineer: Authentication Module Test Plan")

    project = Project(
        id="proj-auth-001",
        title="AI Company OS",
        description="Autonomous AI company operating system.",
    )

    task = Task(
        id="task-qa-001",
        title="Authentication Module Test Plan",
        description=(
            "Write unit tests for the authentication module covering "
            "all API endpoints and security edge cases."
        ),
    )

    context = ExecutionContext(
        employee_id="agent-qa-001",
        employee_role="QA Engineer",
        department="QA",
        project=project,
        workflow_stage="Testing",
        task=task,
        constraints=[
            "Minimum 90% branch coverage",
            "No mocking the database in integration tests",
            "All edge cases for invalid input must be covered",
        ],
        seniority="Senior",
    )

    result = executor.execute(context)

    print(f"\n  Context : {context.summary()}")
    print(f"  Status  : {'SUCCESS' if result.success else 'FAILED'}")
    print(f"  Provider: {result.response_provider_name()}")
    print(f"  Tokens  : {result.response_token_count()}")
    print(f"  Memory  : {result.memory_count()} entries stored")

    if result.has_response():
        subsection("Response preview (first 10 lines)")
        for line in result.response_content().splitlines()[:10]:
            print(line)


# ---------------------------------------------------------------------------
# Demo 3: Deploy Agent
# ---------------------------------------------------------------------------

def demo_deploy_agent(executor: AgentExecutor) -> None:
    section("DEMO 3 -- DevOps: Deploy Authentication Service")

    context = ExecutionContext(
        employee_id="agent-devops-001",
        employee_role="DevOps Engineer",
        department="DevOps",
        project=Project("proj-deploy-001", "Auth Service Deploy",
                        "Production deployment of the auth service."),
        workflow_stage="Deployment",
        task="Deploy the authentication service to production Kubernetes cluster.",
        constraints=[
            "Zero-downtime rolling deploy",
            "Health checks must pass before traffic switch",
            "Rollback script must be prepared",
        ],
    )

    result = executor.execute(context)

    print(f"\n  Context : {context.summary()}")
    print(f"  Status  : {'SUCCESS' if result.success else 'FAILED'}")
    print(f"  Tokens  : {result.response_token_count()}")
    print(f"  Warnings: {result.warning_count()}")


# ---------------------------------------------------------------------------
# Demo 4: Validation failure
# ---------------------------------------------------------------------------

def demo_validation_failure(executor: AgentExecutor) -> None:
    section("DEMO 4 -- Validation Failure (blank employee_id)")

    context = ExecutionContext(
        employee_id="",
        employee_role="Backend Agent",
        department="Engineering",
        project=None,
        workflow_stage="Implementation",
        task="Implement feature X",
    )

    errors = executor.validate(context)
    print(f"\n  Validation errors: {len(errors)}")
    for e in errors:
        print(f"    - {e}")

    result = executor.execute(context)
    print(f"\n  execute() success: {result.success}")
    print(f"  execute() errors : {result.errors}")


# ---------------------------------------------------------------------------
# Demo 5: Statistics
# ---------------------------------------------------------------------------

def demo_statistics(executor: AgentExecutor) -> None:
    section("DEMO 5 -- Executor Statistics")

    stats = executor.statistics()

    print(f"\n  Total executions       : {stats['total']}")
    print(f"  Successful             : {stats['successes']}")
    print(f"  Failed                 : {stats['failures']}")
    print(f"  Success rate           : {stats['success_rate']}")
    print(f"  Avg execution time     : {stats['avg_execution_time']}s")
    print(f"  Total artifacts        : {stats['total_artifacts']}")
    print(f"  Total memory entries   : {stats['total_memory_entries']}")
    print(f"  Total warnings         : {stats['total_warnings']}")
    print(f"  Has artifact engine    : {stats['has_artifact_engine']}")
    print(f"  Has memory engine      : {stats['has_memory_engine']}")
    print(f"  Active provider        : {stats['active_provider']}")
    print(f"  Provider count         : {stats['provider_count']}")
    print(f"  Executor version       : {stats['executor_version']}")
    print(f"\n  Roles seen      : {stats['roles']}")
    print(f"  Departments seen: {stats['departments']}")
    print(f"  Stages seen     : {stats['stages']}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print(SEP)
    print("  AI Company OS -- Feature 17.3: Agent Executor Demo")
    print(SEP)
    print("\nThe AgentExecutor orchestrates: PromptBuilder -> Provider -> Artifact -> Memory")
    print("It contains NO business logic. Pure orchestration.")

    registry, builder, artifact_engine, memory_engine = setup_infrastructure()

    executor = AgentExecutor(
        provider_registry=registry,
        prompt_builder=builder,
        artifact_engine=artifact_engine,
        memory_engine=memory_engine,
    )

    demo_backend_auth(executor)
    demo_qa_agent(executor)
    demo_deploy_agent(executor)
    demo_validation_failure(executor)
    demo_statistics(executor)

    section("DEMO COMPLETE")
    print(f"\n  {len(executor.history())} tasks executed.")
    print("  Full pipeline: Context -> Prompt -> Provider -> Artifact -> Memory -> Result")
    print("  The AgentExecutor knows nothing about Claude, OpenAI, or any AI provider.")
    print("  All execution is deterministic: same input always produces same output.")


if __name__ == "__main__":
    main()
