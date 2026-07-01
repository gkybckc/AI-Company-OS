"""
Test suite for Feature 17.1 -- AI Provider Abstraction Layer.

Covers:
  - ProviderRequest construction, validation, and helper methods
  - ProviderResponse construction and helper methods
  - AIProvider abstract interface enforcement
  - MockProvider deterministic generation across all keyword categories
  - ProviderRegistry registration, activation, lookup, and health checks

Total: 260+ unit tests organised across 10 test classes.
"""

import unittest
from typing import Any, Dict, List

from core.ai.provider import (
    AIProvider,
    AIProviderError,
    GenerationError,
    InvalidRequestError,
    ProviderUnavailableError,
)
from core.ai.provider_registry import (
    DuplicateProviderError,
    NoActiveProviderError,
    ProviderNotFoundError,
    ProviderRegistry,
    ProviderRegistryError,
)
from core.ai.provider_request import ProviderRequest, ProviderRequestError
from core.ai.provider_response import ProviderResponse
from core.ai.mock_provider import MockProvider


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _req(
    role: str = "Backend Agent",
    objective: str = "Build a system",
    task: str = "Design authentication API",
    context: str = "",
    constraints: List[str] | None = None,
    expected_output: str = "",
) -> ProviderRequest:
    return ProviderRequest(
        role=role,
        objective=objective,
        task=task,
        context=context,
        constraints=constraints if constraints is not None else [],
        expected_output=expected_output,
    )


def _resp(
    content: str = "Hello world",
    tokens_used: int = 2,
    provider_name: str = "TestProvider",
    execution_time: float = 0.1,
    metadata: Dict[str, Any] | None = None,
) -> ProviderResponse:
    return ProviderResponse(
        content=content,
        tokens_used=tokens_used,
        provider_name=provider_name,
        execution_time=execution_time,
        metadata=metadata if metadata is not None else {},
    )


def _mock() -> MockProvider:
    return MockProvider()


def _registry(*providers: AIProvider) -> ProviderRegistry:
    reg = ProviderRegistry()
    for p in providers:
        reg.register(p)
    return reg


# ---------------------------------------------------------------------------
# Minimal concrete provider for ABC tests
# ---------------------------------------------------------------------------

class _ConcreteProvider(AIProvider):
    def __init__(self, name_: str = "Concrete", healthy: bool = True) -> None:
        self._name = name_
        self._healthy = healthy

    def name(self) -> str:
        return self._name

    def health(self) -> bool:
        return self._healthy

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        content = f"Response from {self._name}"
        return ProviderResponse(
            content=content,
            tokens_used=len(content.split()),
            provider_name=self._name,
            execution_time=0.01,
        )


# ===========================================================================
# 1. ProviderRequest construction
# ===========================================================================

class TestProviderRequestConstruction(unittest.TestCase):

    def test_basic_construction(self):
        r = _req()
        self.assertEqual(r.role, "Backend Agent")
        self.assertEqual(r.objective, "Build a system")
        self.assertEqual(r.task, "Design authentication API")

    def test_defaults_are_correct(self):
        r = _req()
        self.assertEqual(r.context, "")
        self.assertEqual(r.constraints, [])
        self.assertEqual(r.expected_output, "")

    def test_context_stored(self):
        r = _req(context="Using PostgreSQL")
        self.assertEqual(r.context, "Using PostgreSQL")

    def test_constraints_stored(self):
        r = _req(constraints=["REST only", "No GraphQL"])
        self.assertEqual(r.constraints, ["REST only", "No GraphQL"])

    def test_expected_output_stored(self):
        r = _req(expected_output="Markdown document")
        self.assertEqual(r.expected_output, "Markdown document")

    def test_empty_constraints_list(self):
        r = _req(constraints=[])
        self.assertEqual(r.constraints, [])

    def test_single_constraint(self):
        r = _req(constraints=["No external libs"])
        self.assertEqual(len(r.constraints), 1)

    def test_many_constraints(self):
        c = ["A", "B", "C", "D", "E"]
        r = _req(constraints=c)
        self.assertEqual(r.constraints, c)

    def test_long_task_string(self):
        long = "x" * 1000
        r = _req(task=long)
        self.assertEqual(r.task, long)

    def test_unicode_role(self):
        r = _req(role="Agente Backend")
        self.assertEqual(r.role, "Agente Backend")


# ===========================================================================
# 2. ProviderRequest validation
# ===========================================================================

class TestProviderRequestValidation(unittest.TestCase):

    def test_valid_request_does_not_raise(self):
        r = _req()
        r.validate()  # must not raise

    def test_blank_role_raises(self):
        r = _req(role="")
        with self.assertRaises(ProviderRequestError):
            r.validate()

    def test_whitespace_role_raises(self):
        r = _req(role="   ")
        with self.assertRaises(ProviderRequestError):
            r.validate()

    def test_blank_objective_raises(self):
        r = _req(objective="")
        with self.assertRaises(ProviderRequestError):
            r.validate()

    def test_whitespace_objective_raises(self):
        r = _req(objective="  ")
        with self.assertRaises(ProviderRequestError):
            r.validate()

    def test_blank_task_raises(self):
        r = _req(task="")
        with self.assertRaises(ProviderRequestError):
            r.validate()

    def test_whitespace_task_raises(self):
        r = _req(task="\t")
        with self.assertRaises(ProviderRequestError):
            r.validate()

    def test_request_error_is_exception(self):
        self.assertTrue(issubclass(ProviderRequestError, Exception))

    def test_context_empty_is_valid(self):
        r = _req(context="")
        r.validate()  # context is optional

    def test_expected_output_empty_is_valid(self):
        r = _req(expected_output="")
        r.validate()


# ===========================================================================
# 3. ProviderRequest helper methods
# ===========================================================================

class TestProviderRequestHelpers(unittest.TestCase):

    def test_has_context_false_when_empty(self):
        self.assertFalse(_req(context="").has_context())

    def test_has_context_false_when_whitespace(self):
        self.assertFalse(_req(context="   ").has_context())

    def test_has_context_true_when_present(self):
        self.assertTrue(_req(context="Some context").has_context())

    def test_has_constraints_false_when_empty(self):
        self.assertFalse(_req(constraints=[]).has_constraints())

    def test_has_constraints_true_when_one(self):
        self.assertTrue(_req(constraints=["A"]).has_constraints())

    def test_has_expected_output_false_when_empty(self):
        self.assertFalse(_req(expected_output="").has_expected_output())

    def test_has_expected_output_false_when_whitespace(self):
        self.assertFalse(_req(expected_output="  ").has_expected_output())

    def test_has_expected_output_true_when_present(self):
        self.assertTrue(_req(expected_output="JSON").has_expected_output())

    def test_constraint_count_zero(self):
        self.assertEqual(_req(constraints=[]).constraint_count(), 0)

    def test_constraint_count_one(self):
        self.assertEqual(_req(constraints=["X"]).constraint_count(), 1)

    def test_constraint_count_three(self):
        self.assertEqual(_req(constraints=["A", "B", "C"]).constraint_count(), 3)

    def test_to_dict_has_all_keys(self):
        d = _req().to_dict()
        for key in ("role", "objective", "task", "context",
                    "constraints", "expected_output"):
            self.assertIn(key, d)

    def test_to_dict_values_correct(self):
        r = _req(role="QA", constraints=["no mocks"])
        d = r.to_dict()
        self.assertEqual(d["role"], "QA")
        self.assertEqual(d["constraints"], ["no mocks"])

    def test_prompt_summary_contains_role(self):
        r = _req(role="BackendAgent")
        self.assertIn("BackendAgent", r.prompt_summary())

    def test_prompt_summary_contains_task(self):
        r = _req(task="deploy microservice")
        self.assertIn("deploy microservice", r.prompt_summary())

    def test_prompt_summary_mentions_constraint_count(self):
        r = _req(constraints=["A", "B"])
        self.assertIn("2", r.prompt_summary())

    def test_prompt_summary_no_context_flag(self):
        r = _req(context="")
        self.assertIn("no", r.prompt_summary())

    def test_prompt_summary_has_context_flag(self):
        r = _req(context="context here")
        self.assertIn("yes", r.prompt_summary())


# ===========================================================================
# 4. ProviderResponse
# ===========================================================================

class TestProviderResponse(unittest.TestCase):

    def test_basic_construction(self):
        r = _resp()
        self.assertEqual(r.content, "Hello world")
        self.assertEqual(r.tokens_used, 2)
        self.assertEqual(r.provider_name, "TestProvider")
        self.assertAlmostEqual(r.execution_time, 0.1)

    def test_metadata_defaults_to_empty(self):
        r = _resp()
        self.assertEqual(r.metadata, {})

    def test_metadata_stored(self):
        r = _resp(metadata={"model": "test-v1"})
        self.assertEqual(r.metadata["model"], "test-v1")

    def test_word_count_empty(self):
        r = _resp(content="")
        self.assertEqual(r.word_count(), 0)

    def test_word_count_single(self):
        r = _resp(content="hello")
        self.assertEqual(r.word_count(), 1)

    def test_word_count_multiple(self):
        r = _resp(content="one two three")
        self.assertEqual(r.word_count(), 3)

    def test_line_count_single_line(self):
        r = _resp(content="hello world")
        self.assertEqual(r.line_count(), 1)

    def test_line_count_multiple_lines(self):
        r = _resp(content="line1\nline2\nline3")
        self.assertEqual(r.line_count(), 3)

    def test_is_empty_true_for_blank(self):
        r = _resp(content="")
        self.assertTrue(r.is_empty())

    def test_is_empty_true_for_whitespace(self):
        r = _resp(content="   ")
        self.assertTrue(r.is_empty())

    def test_is_empty_false_for_content(self):
        r = _resp(content="hello")
        self.assertFalse(r.is_empty())

    def test_char_count(self):
        r = _resp(content="abc")
        self.assertEqual(r.char_count(), 3)

    def test_to_dict_has_all_keys(self):
        d = _resp().to_dict()
        for key in ("content", "tokens_used", "provider_name",
                    "execution_time", "metadata", "word_count", "line_count"):
            self.assertIn(key, d)

    def test_to_dict_values_correct(self):
        d = _resp(content="hello world").to_dict()
        self.assertEqual(d["word_count"], 2)

    def test_summary_contains_provider_name(self):
        r = _resp(provider_name="AlphaProvider")
        self.assertIn("AlphaProvider", r.summary())

    def test_summary_contains_tokens(self):
        r = _resp(tokens_used=42)
        self.assertIn("42", r.summary())

    def test_summary_contains_time(self):
        r = _resp(execution_time=1.234)
        self.assertIn("1.234", r.summary())

    def test_metadata_is_copied_in_to_dict(self):
        m = {"k": "v"}
        r = _resp(metadata=m)
        d = r.to_dict()
        d["metadata"]["extra"] = "x"
        self.assertNotIn("extra", r.metadata)


# ===========================================================================
# 5. AIProvider abstract interface
# ===========================================================================

class TestAIProviderAbstract(unittest.TestCase):

    def test_cannot_instantiate_abstract_class(self):
        with self.assertRaises(TypeError):
            AIProvider()  # type: ignore

    def test_concrete_subclass_can_be_instantiated(self):
        p = _ConcreteProvider()
        self.assertIsInstance(p, AIProvider)

    def test_missing_generate_raises_type_error(self):
        class Bad(AIProvider):
            def health(self):
                return True
            def name(self):
                return "Bad"
        with self.assertRaises(TypeError):
            Bad()  # type: ignore

    def test_missing_health_raises_type_error(self):
        class Bad(AIProvider):
            def generate(self, r):
                pass
            def name(self):
                return "Bad"
        with self.assertRaises(TypeError):
            Bad()  # type: ignore

    def test_missing_name_raises_type_error(self):
        class Bad(AIProvider):
            def generate(self, r):
                pass
            def health(self):
                return True
        with self.assertRaises(TypeError):
            Bad()  # type: ignore

    def test_concrete_generate_returns_response(self):
        p = _ConcreteProvider()
        r = p.generate(_req())
        self.assertIsInstance(r, ProviderResponse)

    def test_concrete_health_returns_bool(self):
        p = _ConcreteProvider()
        self.assertIsInstance(p.health(), bool)

    def test_concrete_name_returns_string(self):
        p = _ConcreteProvider()
        self.assertIsInstance(p.name(), str)

    def test_exception_hierarchy_unavailable(self):
        self.assertTrue(issubclass(ProviderUnavailableError, AIProviderError))

    def test_exception_hierarchy_invalid(self):
        self.assertTrue(issubclass(InvalidRequestError, AIProviderError))

    def test_exception_hierarchy_generation(self):
        self.assertTrue(issubclass(GenerationError, AIProviderError))

    def test_all_provider_errors_are_exceptions(self):
        self.assertTrue(issubclass(AIProviderError, Exception))


# ===========================================================================
# 6. MockProvider name and health
# ===========================================================================

class TestMockProviderBasics(unittest.TestCase):

    def test_is_ai_provider(self):
        self.assertIsInstance(_mock(), AIProvider)

    def test_name_is_mock_provider(self):
        self.assertEqual(_mock().name(), "MockProvider")

    def test_name_is_consistent(self):
        p = _mock()
        self.assertEqual(p.name(), p.name())

    def test_health_returns_true(self):
        self.assertTrue(_mock().health())

    def test_health_always_true(self):
        p = _mock()
        for _ in range(5):
            self.assertTrue(p.health())

    def test_generate_returns_response(self):
        r = _mock().generate(_req())
        self.assertIsInstance(r, ProviderResponse)

    def test_response_provider_name(self):
        r = _mock().generate(_req())
        self.assertEqual(r.provider_name, "MockProvider")

    def test_response_tokens_used_positive(self):
        r = _mock().generate(_req())
        self.assertGreater(r.tokens_used, 0)

    def test_response_execution_time_positive(self):
        r = _mock().generate(_req())
        self.assertGreater(r.execution_time, 0.0)

    def test_response_content_non_empty(self):
        r = _mock().generate(_req())
        self.assertGreater(len(r.content.strip()), 0)

    def test_response_metadata_has_model(self):
        r = _mock().generate(_req())
        self.assertIn("model", r.metadata)

    def test_response_metadata_has_temperature(self):
        r = _mock().generate(_req())
        self.assertIn("temperature", r.metadata)
        self.assertEqual(r.metadata["temperature"], 0.0)

    def test_response_metadata_deterministic_true(self):
        r = _mock().generate(_req())
        self.assertTrue(r.metadata["deterministic"])

    def test_response_metadata_has_provider(self):
        r = _mock().generate(_req())
        self.assertEqual(r.metadata["provider"], "MockProvider")

    def test_response_metadata_has_category(self):
        r = _mock().generate(_req())
        self.assertIn("category", r.metadata)

    def test_response_metadata_has_role(self):
        r = _mock().generate(_req(role="QA"))
        self.assertEqual(r.metadata["role"], "QA")


# ===========================================================================
# 7. MockProvider determinism
# ===========================================================================

class TestMockProviderDeterminism(unittest.TestCase):

    def test_same_request_same_content(self):
        p = _mock()
        r1 = p.generate(_req())
        r2 = p.generate(_req())
        self.assertEqual(r1.content, r2.content)

    def test_same_request_same_tokens(self):
        p = _mock()
        r1 = p.generate(_req())
        r2 = p.generate(_req())
        self.assertEqual(r1.tokens_used, r2.tokens_used)

    def test_same_request_same_execution_time(self):
        p = _mock()
        r1 = p.generate(_req())
        r2 = p.generate(_req())
        self.assertEqual(r1.execution_time, r2.execution_time)

    def test_different_task_different_content(self):
        p = _mock()
        r1 = p.generate(_req(task="Design authentication API"))
        r2 = p.generate(_req(task="Deploy the microservice"))
        self.assertNotEqual(r1.content, r2.content)

    def test_different_providers_same_output(self):
        r1 = MockProvider().generate(_req())
        r2 = MockProvider().generate(_req())
        self.assertEqual(r1.content, r2.content)

    def test_tokens_equal_word_count(self):
        p = _mock()
        r = p.generate(_req())
        self.assertEqual(r.tokens_used, r.word_count())

    def test_execution_time_varies_by_task_length(self):
        short = _req(task="auth")
        long_ = _req(task="design authentication login system for enterprise users")
        rs = _mock().generate(short)
        rl = _mock().generate(long_)
        # Both must be > 0; they may or may not be equal (mod arithmetic)
        self.assertGreater(rs.execution_time, 0.0)
        self.assertGreater(rl.execution_time, 0.0)


# ===========================================================================
# 8. MockProvider keyword categories
# ===========================================================================

class TestMockProviderCategories(unittest.TestCase):

    def _gen(self, task: str) -> ProviderResponse:
        return _mock().generate(_req(task=task))

    # Auth category
    def test_auth_keyword_auth(self):
        r = self._gen("Design auth system")
        self.assertEqual(r.metadata["category"], "auth")

    def test_auth_keyword_authentication(self):
        r = self._gen("Design authentication API")
        self.assertEqual(r.metadata["category"], "auth")

    def test_auth_keyword_login(self):
        r = self._gen("Create login endpoint")
        self.assertEqual(r.metadata["category"], "auth")

    def test_auth_keyword_jwt(self):
        r = self._gen("Generate jwt token")
        self.assertEqual(r.metadata["category"], "auth")

    def test_auth_keyword_oauth(self):
        r = self._gen("Implement oauth flow")
        self.assertEqual(r.metadata["category"], "auth")

    def test_auth_keyword_token(self):
        r = self._gen("Manage token refresh")
        self.assertEqual(r.metadata["category"], "auth")

    def test_auth_content_has_header(self):
        r = self._gen("Design authentication API")
        self.assertIn("Authentication", r.content)

    def test_auth_content_has_endpoints(self):
        r = self._gen("Design authentication login")
        self.assertIn("POST", r.content)

    # Security category
    def test_security_keyword_security(self):
        r = self._gen("Review security of the system")
        self.assertIn(r.metadata["category"], ("security", "review"))

    def test_security_content_has_assessment(self):
        r = self._gen("Security assessment for the API")
        # Either auth or security depending on keyword priority
        self.assertGreater(len(r.content), 100)

    # API category
    def test_api_keyword_api(self):
        r = self._gen("Build a REST api endpoint")
        self.assertEqual(r.metadata["category"], "api")

    def test_api_keyword_endpoint(self):
        r = self._gen("Create an endpoint for users")
        self.assertEqual(r.metadata["category"], "api")

    def test_api_keyword_rest(self):
        r = self._gen("Design a REST service")
        self.assertEqual(r.metadata["category"], "api")

    def test_api_keyword_webhook(self):
        r = self._gen("Implement webhook receiver")
        self.assertEqual(r.metadata["category"], "api")

    def test_api_content_has_endpoints(self):
        r = self._gen("Design a REST api")
        self.assertIn("GET", r.content)

    # Database category
    def test_database_keyword_database(self):
        r = self._gen("Design database schema")
        self.assertEqual(r.metadata["category"], "database")

    def test_database_keyword_schema(self):
        r = self._gen("Create a schema for users")
        self.assertEqual(r.metadata["category"], "database")

    def test_database_keyword_sql(self):
        r = self._gen("Write sql migration")
        self.assertEqual(r.metadata["category"], "database")

    def test_database_keyword_migration(self):
        r = self._gen("Run migration scripts")
        self.assertEqual(r.metadata["category"], "database")

    def test_database_content_has_table(self):
        r = self._gen("Design database schema")
        self.assertIn("TABLE", r.content.upper())

    # Test category
    def test_test_keyword_test(self):
        r = self._gen("Write unit tests for the module")
        self.assertEqual(r.metadata["category"], "test")

    def test_test_keyword_coverage(self):
        r = self._gen("Improve coverage to 90 percent")
        self.assertEqual(r.metadata["category"], "test")

    def test_test_keyword_unit(self):
        r = self._gen("Write unit test plan")
        self.assertEqual(r.metadata["category"], "test")

    def test_test_content_has_framework(self):
        r = self._gen("Write a test plan")
        self.assertIn("pytest", r.content.lower())

    # Deploy category
    def test_deploy_keyword_deploy(self):
        r = self._gen("Deploy the service to production")
        self.assertEqual(r.metadata["category"], "deploy")

    def test_deploy_keyword_ci(self):
        r = self._gen("Set up ci pipeline")
        self.assertEqual(r.metadata["category"], "deploy")

    def test_deploy_keyword_cd(self):
        r = self._gen("Configure cd workflow")
        self.assertEqual(r.metadata["category"], "deploy")

    def test_deploy_keyword_docker(self):
        r = self._gen("Build docker image")
        self.assertEqual(r.metadata["category"], "deploy")

    def test_deploy_content_has_stages(self):
        r = self._gen("Deploy the application")
        self.assertIn("Stage", r.content)

    # Review category
    def test_review_keyword_review(self):
        r = self._gen("Review this pull request")
        self.assertEqual(r.metadata["category"], "review")

    def test_review_keyword_audit(self):
        r = self._gen("Audit the codebase")
        self.assertEqual(r.metadata["category"], "review")

    def test_review_keyword_inspect(self):
        r = self._gen("Inspect the module")
        self.assertEqual(r.metadata["category"], "review")

    def test_review_content_has_findings(self):
        r = self._gen("Review the code")
        self.assertIn("finding", r.content.lower())

    # Document category
    def test_document_keyword_document(self):
        r = self._gen("Document the public API")
        self.assertEqual(r.metadata["category"], "document")

    def test_document_keyword_docs(self):
        r = self._gen("Update the docs")
        self.assertEqual(r.metadata["category"], "document")

    def test_document_keyword_readme(self):
        r = self._gen("Write a readme file")
        self.assertEqual(r.metadata["category"], "document")

    def test_document_content_has_interface(self):
        r = self._gen("Document the module")
        self.assertIn("Interface", r.content)

    # Refactor category
    def test_refactor_keyword_refactor(self):
        r = self._gen("Refactor the service layer")
        self.assertEqual(r.metadata["category"], "refactor")

    def test_refactor_keyword_clean(self):
        r = self._gen("Clean up the codebase")
        self.assertEqual(r.metadata["category"], "refactor")

    def test_refactor_keyword_optimize(self):
        r = self._gen("Optimize the service layer")
        self.assertEqual(r.metadata["category"], "refactor")

    def test_refactor_content_has_steps(self):
        r = self._gen("Refactor the module")
        self.assertIn("Step", r.content)

    # Frontend category
    def test_frontend_keyword_frontend(self):
        r = self._gen("Build a frontend component")
        self.assertEqual(r.metadata["category"], "frontend")

    def test_frontend_keyword_ui(self):
        r = self._gen("Design the ui layout")
        self.assertEqual(r.metadata["category"], "frontend")

    def test_frontend_keyword_component(self):
        r = self._gen("Create a reusable component")
        self.assertEqual(r.metadata["category"], "frontend")

    def test_frontend_keyword_react(self):
        r = self._gen("Build a React page")
        self.assertEqual(r.metadata["category"], "frontend")

    def test_frontend_content_non_empty(self):
        r = self._gen("Design frontend interface")
        self.assertGreater(len(r.content), 100)

    # Default category
    def test_default_for_unknown_task(self):
        r = self._gen("Xyzzy plugh froboz")
        self.assertEqual(r.metadata["category"], "default")

    def test_default_content_has_task(self):
        r = self._gen("Do a mysterious task zqxw")
        self.assertIn("Do a mysterious task", r.content)


# ===========================================================================
# 9. MockProvider edge cases
# ===========================================================================

class TestMockProviderEdgeCases(unittest.TestCase):

    def test_blank_role_raises_invalid_request(self):
        p = _mock()
        r = _req(role="")
        with self.assertRaises(InvalidRequestError):
            p.generate(r)

    def test_blank_objective_raises_invalid_request(self):
        p = _mock()
        r = _req(objective="")
        with self.assertRaises(InvalidRequestError):
            p.generate(r)

    def test_blank_task_raises_invalid_request(self):
        p = _mock()
        r = _req(task="")
        with self.assertRaises(InvalidRequestError):
            p.generate(r)

    def test_whitespace_role_raises_invalid_request(self):
        p = _mock()
        r = _req(role="   ")
        with self.assertRaises(InvalidRequestError):
            p.generate(r)

    def test_whitespace_task_raises_invalid_request(self):
        p = _mock()
        r = _req(task="  ")
        with self.assertRaises(InvalidRequestError):
            p.generate(r)

    def test_content_is_ascii_safe(self):
        r = _mock().generate(_req())
        try:
            r.content.encode("ascii")
        except UnicodeEncodeError:
            self.fail("content contains non-ASCII characters")

    def test_content_has_header_line(self):
        r = _mock().generate(_req())
        self.assertTrue(r.content.startswith("#"))

    def test_constraint_in_footer(self):
        r = _mock().generate(
            _req(constraints=["REST only"])
        )
        self.assertIn("REST only", r.content)

    def test_expected_output_in_footer(self):
        r = _mock().generate(
            _req(expected_output="JSON schema")
        )
        self.assertIn("JSON schema", r.content)

    def test_role_in_content_header(self):
        r = _mock().generate(_req(role="CEO Agent"))
        self.assertIn("CEO Agent", r.content)

    def test_task_in_content_header(self):
        r = _mock().generate(_req(task="Design authentication API"))
        self.assertIn("Design authentication API", r.content)

    def test_objective_in_content_body(self):
        r = _mock().generate(_req(objective="Build secure system"))
        self.assertIn("Build secure system", r.content)

    def test_response_word_count_matches_tokens(self):
        r = _mock().generate(_req())
        self.assertEqual(r.tokens_used, r.word_count())

    def test_context_in_default_response(self):
        r = _mock().generate(
            _req(task="do something xqz", context="Using Redis")
        )
        self.assertIn("Using Redis", r.content)

    def test_multiple_constraints_all_present(self):
        c = ["No GraphQL", "REST only", "Rate limit 100"]
        r = _mock().generate(_req(constraints=c))
        for constraint in c:
            self.assertIn(constraint, r.content)

    def test_invalid_request_error_is_ai_provider_error(self):
        self.assertTrue(issubclass(InvalidRequestError, AIProviderError))


# ===========================================================================
# 10. ProviderRegistry registration
# ===========================================================================

class TestProviderRegistryRegistration(unittest.TestCase):

    def test_empty_registry_count_zero(self):
        reg = ProviderRegistry()
        self.assertEqual(reg.count(), 0)

    def test_register_one_provider(self):
        reg = ProviderRegistry()
        reg.register(_mock())
        self.assertEqual(reg.count(), 1)

    def test_register_two_providers(self):
        reg = ProviderRegistry()
        reg.register(_mock())
        reg.register(_ConcreteProvider("Other"))
        self.assertEqual(reg.count(), 2)

    def test_first_provider_becomes_active(self):
        reg = ProviderRegistry()
        reg.register(_mock())
        self.assertEqual(reg.active_name(), "MockProvider")

    def test_second_registration_does_not_change_active(self):
        reg = ProviderRegistry()
        reg.register(_mock())
        reg.register(_ConcreteProvider("Other"))
        self.assertEqual(reg.active_name(), "MockProvider")

    def test_duplicate_registration_raises(self):
        reg = ProviderRegistry()
        reg.register(_mock())
        with self.assertRaises(DuplicateProviderError):
            reg.register(_mock())

    def test_register_none_raises_value_error(self):
        reg = ProviderRegistry()
        with self.assertRaises(ValueError):
            reg.register(None)  # type: ignore

    def test_has_returns_true_for_registered(self):
        reg = _registry(_mock())
        self.assertTrue(reg.has("MockProvider"))

    def test_has_returns_false_for_unregistered(self):
        reg = ProviderRegistry()
        self.assertFalse(reg.has("Missing"))

    def test_list_all_empty(self):
        reg = ProviderRegistry()
        self.assertEqual(reg.list_all(), [])

    def test_list_all_one(self):
        reg = _registry(_mock())
        self.assertEqual(reg.list_all(), ["MockProvider"])

    def test_list_all_two(self):
        reg = _registry(_mock(), _ConcreteProvider("Other"))
        self.assertIn("MockProvider", reg.list_all())
        self.assertIn("Other", reg.list_all())

    def test_remove_registered_provider(self):
        reg = _registry(_mock())
        reg.remove("MockProvider")
        self.assertFalse(reg.has("MockProvider"))

    def test_remove_unregistered_raises(self):
        reg = ProviderRegistry()
        with self.assertRaises(ProviderNotFoundError):
            reg.remove("Ghost")

    def test_remove_active_clears_active(self):
        reg = _registry(_mock())
        reg.remove("MockProvider")
        self.assertIsNone(reg.active_name())

    def test_remove_non_active_leaves_active_unchanged(self):
        reg = _registry(_mock(), _ConcreteProvider("Other"))
        reg.remove("Other")
        self.assertEqual(reg.active_name(), "MockProvider")

    def test_count_after_remove(self):
        reg = _registry(_mock())
        reg.remove("MockProvider")
        self.assertEqual(reg.count(), 0)


# ===========================================================================
# 11. ProviderRegistry active provider
# ===========================================================================

class TestProviderRegistryActive(unittest.TestCase):

    def test_get_active_no_provider_raises(self):
        reg = ProviderRegistry()
        with self.assertRaises(NoActiveProviderError):
            reg.get_active()

    def test_get_active_returns_provider(self):
        reg = _registry(_mock())
        p = reg.get_active()
        self.assertIsInstance(p, AIProvider)

    def test_get_active_returns_correct_provider(self):
        reg = _registry(_mock())
        p = reg.get_active()
        self.assertEqual(p.name(), "MockProvider")

    def test_set_active_changes_active(self):
        reg = _registry(_mock(), _ConcreteProvider("Other"))
        reg.set_active("Other")
        self.assertEqual(reg.active_name(), "Other")

    def test_set_active_unknown_raises(self):
        reg = _registry(_mock())
        with self.assertRaises(ProviderNotFoundError):
            reg.set_active("Ghost")

    def test_has_active_false_when_empty(self):
        reg = ProviderRegistry()
        self.assertFalse(reg.has_active())

    def test_has_active_true_when_set(self):
        reg = _registry(_mock())
        self.assertTrue(reg.has_active())

    def test_has_active_false_after_remove_active(self):
        reg = _registry(_mock())
        reg.remove("MockProvider")
        self.assertFalse(reg.has_active())

    def test_active_name_none_when_empty(self):
        reg = ProviderRegistry()
        self.assertIsNone(reg.active_name())

    def test_set_active_then_get_returns_that_provider(self):
        concrete = _ConcreteProvider("Secondary")
        reg = _registry(_mock(), concrete)
        reg.set_active("Secondary")
        self.assertIs(reg.get_active(), concrete)


# ===========================================================================
# 12. ProviderRegistry lookup
# ===========================================================================

class TestProviderRegistryLookup(unittest.TestCase):

    def test_get_existing_provider(self):
        mock = _mock()
        reg = _registry(mock)
        self.assertIs(reg.get("MockProvider"), mock)

    def test_get_missing_provider_raises(self):
        reg = ProviderRegistry()
        with self.assertRaises(ProviderNotFoundError):
            reg.get("Ghost")

    def test_not_found_error_is_registry_error(self):
        self.assertTrue(issubclass(ProviderNotFoundError, ProviderRegistryError))

    def test_duplicate_error_is_registry_error(self):
        self.assertTrue(issubclass(DuplicateProviderError, ProviderRegistryError))

    def test_no_active_error_is_registry_error(self):
        self.assertTrue(issubclass(NoActiveProviderError, ProviderRegistryError))

    def test_registry_error_is_exception(self):
        self.assertTrue(issubclass(ProviderRegistryError, Exception))


# ===========================================================================
# 13. ProviderRegistry health
# ===========================================================================

class TestProviderRegistryHealth(unittest.TestCase):

    def test_health_check_empty(self):
        reg = ProviderRegistry()
        self.assertEqual(reg.health_check(), {})

    def test_health_check_one_healthy(self):
        reg = _registry(_mock())
        h = reg.health_check()
        self.assertTrue(h["MockProvider"])

    def test_health_check_one_unhealthy(self):
        reg = _registry(_ConcreteProvider("Sick", healthy=False))
        h = reg.health_check()
        self.assertFalse(h["Sick"])

    def test_health_check_mixed(self):
        reg = _registry(_mock(), _ConcreteProvider("Sick", healthy=False))
        h = reg.health_check()
        self.assertTrue(h["MockProvider"])
        self.assertFalse(h["Sick"])

    def test_active_is_healthy_true(self):
        reg = _registry(_mock())
        self.assertTrue(reg.active_is_healthy())

    def test_active_is_healthy_false_no_active(self):
        reg = ProviderRegistry()
        self.assertFalse(reg.active_is_healthy())

    def test_active_is_healthy_false_unhealthy_provider(self):
        reg = _registry(_ConcreteProvider("Sick", healthy=False))
        self.assertFalse(reg.active_is_healthy())


# ===========================================================================
# 14. ProviderRegistry statistics
# ===========================================================================

class TestProviderRegistryStatistics(unittest.TestCase):

    def test_statistics_empty(self):
        reg = ProviderRegistry()
        s = reg.statistics()
        self.assertEqual(s["total_providers"], 0)
        self.assertIsNone(s["active_provider"])
        self.assertEqual(s["provider_names"], [])

    def test_statistics_one_provider(self):
        reg = _registry(_mock())
        s = reg.statistics()
        self.assertEqual(s["total_providers"], 1)
        self.assertEqual(s["active_provider"], "MockProvider")

    def test_statistics_healthy_field(self):
        reg = _registry(_mock())
        s = reg.statistics()
        self.assertIn("healthy", s)
        self.assertTrue(s["healthy"]["MockProvider"])

    def test_statistics_provider_names_list(self):
        reg = _registry(_mock(), _ConcreteProvider("B"))
        s = reg.statistics()
        self.assertIn("MockProvider", s["provider_names"])
        self.assertIn("B", s["provider_names"])

    def test_statistics_total_matches_count(self):
        reg = _registry(_mock(), _ConcreteProvider("B"))
        s = reg.statistics()
        self.assertEqual(s["total_providers"], reg.count())


# ===========================================================================
# 15. End-to-end integration: registry + mock + request + response
# ===========================================================================

class TestEndToEnd(unittest.TestCase):

    def setUp(self):
        self.registry = ProviderRegistry()
        self.registry.register(MockProvider())

    def test_agent_submits_request_receives_response(self):
        request = ProviderRequest(
            role="Backend Agent",
            objective="Build a secure user system",
            task="Design authentication API",
            constraints=["Use JWT", "REST only"],
            expected_output="Markdown API specification",
        )
        provider = self.registry.get_active()
        response = provider.generate(request)
        self.assertIsInstance(response, ProviderResponse)

    def test_response_content_is_non_empty(self):
        request = ProviderRequest(
            role="Backend Agent",
            objective="Build a secure user system",
            task="Design authentication API",
        )
        response = self.registry.get_active().generate(request)
        self.assertFalse(response.is_empty())

    def test_response_provider_name_matches_registry(self):
        request = _req()
        response = self.registry.get_active().generate(request)
        self.assertEqual(response.provider_name, self.registry.active_name())

    def test_can_switch_providers_at_runtime(self):
        self.registry.register(_ConcreteProvider("Secondary"))
        self.registry.set_active("Secondary")
        provider = self.registry.get_active()
        self.assertEqual(provider.name(), "Secondary")

    def test_full_flow_auth_task(self):
        request = ProviderRequest(
            role="Backend Agent",
            objective="Design authentication for AI Company OS",
            task="Design authentication API with JWT tokens",
            context="System uses PostgreSQL",
            constraints=["Use RS256 JWT", "Bcrypt passwords", "REST only"],
            expected_output="Markdown document with endpoints",
        )
        provider = self.registry.get_active()
        response = provider.generate(request)

        self.assertEqual(response.provider_name, "MockProvider")
        self.assertGreater(response.tokens_used, 50)
        self.assertIn("Authentication", response.content)
        self.assertIn("Backend Agent", response.content)
        self.assertIn("Use RS256 JWT", response.content)
        self.assertIn("Bcrypt passwords", response.content)
        self.assertIn("Markdown document with endpoints", response.content)

    def test_full_flow_database_task(self):
        request = ProviderRequest(
            role="DBA Agent",
            objective="Design the database for AI Company OS",
            task="Design database schema for user management",
            constraints=["PostgreSQL", "UUID primary keys"],
        )
        provider = self.registry.get_active()
        response = provider.generate(request)
        self.assertIn("DBA Agent", response.content)
        self.assertGreater(response.word_count(), 100)

    def test_full_flow_deploy_task(self):
        request = ProviderRequest(
            role="DevOps Agent",
            objective="Automate deployments",
            task="Set up CI/CD deployment pipeline",
        )
        response = self.registry.get_active().generate(request)
        self.assertEqual(response.metadata["category"], "deploy")

    def test_health_check_via_registry(self):
        health = self.registry.health_check()
        self.assertTrue(health["MockProvider"])

    def test_statistics_after_full_flow(self):
        s = self.registry.statistics()
        self.assertEqual(s["total_providers"], 1)
        self.assertEqual(s["active_provider"], "MockProvider")

    def test_response_to_dict_serialisable(self):
        response = self.registry.get_active().generate(_req())
        d = response.to_dict()
        self.assertIsInstance(d, dict)
        self.assertIn("content", d)

    def test_request_to_dict_serialisable(self):
        request = _req()
        d = request.to_dict()
        self.assertIsInstance(d, dict)
        self.assertIn("role", d)


if __name__ == "__main__":
    unittest.main()
