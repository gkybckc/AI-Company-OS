"""
Demo: AI Provider Abstraction Layer -- Feature 17.1

Shows how an agent submits a ProviderRequest through the ProviderRegistry
to receive a ProviderResponse, without knowing which provider is active.

Run from the repo root:
    python -m examples.demo_ai_provider
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai.provider_request import ProviderRequest
from core.ai.provider_registry import ProviderRegistry
from core.ai.mock_provider import MockProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SEP = "=" * 70
SEP_THIN = "-" * 70


def section(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def subsection(title: str) -> None:
    print(f"\n{SEP_THIN}")
    print(f"  {title}")
    print(SEP_THIN)


# ---------------------------------------------------------------------------
# Demo 1: Backend Agent -- Design authentication API
# ---------------------------------------------------------------------------

def demo_auth_request(registry: ProviderRegistry) -> None:
    section("DEMO 1 -- Backend Agent: Design Authentication API")

    request = ProviderRequest(
        role="Backend Agent",
        objective=(
            "Build a secure, scalable authentication system "
            "for AI Company OS that supports JWT-based access control."
        ),
        task="Design authentication API",
        context=(
            "AI Company OS uses PostgreSQL 15 for persistence. "
            "The system must support multiple concurrent users "
            "and comply with corporate security standards."
        ),
        constraints=[
            "Use RS256 JWT (asymmetric, not HS256)",
            "Passwords hashed with bcrypt, cost factor 12",
            "Rate limit: 5 failed logins per 60 seconds per IP",
            "All endpoints served over HTTPS only",
            "REST only -- no GraphQL",
        ],
        expected_output="Markdown API specification with all endpoints documented",
    )

    print(f"\nRequest summary: {request.prompt_summary()}")
    print(f"Constraints    : {request.constraint_count()}")
    print(f"Has context    : {request.has_context()}")

    provider = registry.get_active()
    print(f"\nActive provider: {provider.name()}")
    print(f"Provider health: {provider.health()}")

    response = provider.generate(request)

    subsection("Response Metadata")
    print(f"  Provider     : {response.provider_name}")
    print(f"  Tokens used  : {response.tokens_used}")
    print(f"  Execution time: {response.execution_time:.3f}s")
    print(f"  Word count   : {response.word_count()}")
    print(f"  Line count   : {response.line_count()}")
    print(f"  Category     : {response.metadata.get('category')}")
    print(f"  Model        : {response.metadata.get('model')}")
    print(f"  Deterministic: {response.metadata.get('deterministic')}")

    subsection("Generated Content (first 40 lines)")
    lines = response.content.splitlines()
    for line in lines[:40]:
        print(line)
    if len(lines) > 40:
        print(f"  ... ({len(lines) - 40} more lines)")


# ---------------------------------------------------------------------------
# Demo 2: Database Agent -- Design schema
# ---------------------------------------------------------------------------

def demo_database_request(registry: ProviderRegistry) -> None:
    section("DEMO 2 -- Database Agent: Design User Management Schema")

    request = ProviderRequest(
        role="Database Agent",
        objective="Design a normalised relational schema for user management.",
        task="Design database schema for user management system",
        constraints=["PostgreSQL 15", "UUID primary keys", "Soft deletes only"],
        expected_output="Markdown document with CREATE TABLE statements",
    )

    provider = registry.get_active()
    response = provider.generate(request)

    print(f"\nSummary: {response.summary()}")
    print(f"Category: {response.metadata.get('category')}")
    print(f"\nFirst 20 lines of content:")
    for line in response.content.splitlines()[:20]:
        print(line)


# ---------------------------------------------------------------------------
# Demo 3: DevOps Agent -- CI/CD pipeline
# ---------------------------------------------------------------------------

def demo_deploy_request(registry: ProviderRegistry) -> None:
    section("DEMO 3 -- DevOps Agent: CI/CD Pipeline Plan")

    request = ProviderRequest(
        role="DevOps Agent",
        objective="Automate the build, test, and deployment workflow.",
        task="Set up CI/CD deployment pipeline for AI Company OS",
        constraints=["Docker containers", "No secrets in code", "CEO approval required for production"],
    )

    provider = registry.get_active()
    response = provider.generate(request)

    print(f"\nSummary: {response.summary()}")
    print(f"Category: {response.metadata.get('category')}")
    print(f"\nFirst 20 lines of content:")
    for line in response.content.splitlines()[:20]:
        print(line)


# ---------------------------------------------------------------------------
# Demo 4: QA Agent -- Test plan
# ---------------------------------------------------------------------------

def demo_test_request(registry: ProviderRegistry) -> None:
    section("DEMO 4 -- QA Agent: Test Plan")

    request = ProviderRequest(
        role="QA Agent",
        objective="Ensure 90% branch coverage across all modules.",
        task="Write a comprehensive test plan for the authentication module",
        constraints=["pytest", "No mocking the database in integration tests"],
    )

    provider = registry.get_active()
    response = provider.generate(request)

    print(f"\nSummary: {response.summary()}")
    print(f"Category: {response.metadata.get('category')}")
    print(f"\nFirst 20 lines of content:")
    for line in response.content.splitlines()[:20]:
        print(line)


# ---------------------------------------------------------------------------
# Demo 5: Registry statistics
# ---------------------------------------------------------------------------

def demo_registry_stats(registry: ProviderRegistry) -> None:
    section("DEMO 5 -- Registry Statistics")

    stats = registry.statistics()
    print(f"\n  Total providers : {stats['total_providers']}")
    print(f"  Active provider : {stats['active_provider']}")
    print(f"  Provider names  : {stats['provider_names']}")
    print(f"  Health checks   : {stats['healthy']}")


# ---------------------------------------------------------------------------
# Demo 6: Determinism verification
# ---------------------------------------------------------------------------

def demo_determinism(registry: ProviderRegistry) -> None:
    section("DEMO 6 -- Determinism Verification")

    request = ProviderRequest(
        role="Backend Agent",
        objective="Verify determinism",
        task="Design authentication API",
    )

    provider = registry.get_active()
    r1 = provider.generate(request)
    r2 = provider.generate(request)
    r3 = provider.generate(request)

    same_content = (r1.content == r2.content == r3.content)
    same_tokens  = (r1.tokens_used == r2.tokens_used == r3.tokens_used)
    same_time    = (r1.execution_time == r2.execution_time == r3.execution_time)

    print(f"\n  Identical content across 3 calls : {same_content}")
    print(f"  Identical tokens across 3 calls  : {same_tokens}")
    print(f"  Identical exec time across 3 calls: {same_time}")
    print(f"\n  Tokens (run 1): {r1.tokens_used}")
    print(f"  Tokens (run 2): {r2.tokens_used}")
    print(f"  Tokens (run 3): {r3.tokens_used}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print(SEP)
    print("  AI Company OS -- Feature 17.1: AI Provider Abstraction Demo")
    print(SEP)

    # Set up registry with MockProvider
    registry = ProviderRegistry()
    registry.register(MockProvider())
    print(f"\nRegistry initialised. Active provider: {registry.active_name()}")
    print(f"Provider health: {registry.active_is_healthy()}")

    demo_auth_request(registry)
    demo_database_request(registry)
    demo_deploy_request(registry)
    demo_test_request(registry)
    demo_registry_stats(registry)
    demo_determinism(registry)

    section("DEMO COMPLETE")
    print("\nAll 6 demos completed successfully.")
    print("The provider abstraction layer is fully functional.")
    print("Agents never know which provider is active -- only the registry knows.")


if __name__ == "__main__":
    main()
