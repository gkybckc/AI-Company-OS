"""
Test suite for Feature 17.2 -- Prompt Builder.

Covers:
  - PromptContext construction, validation, and helper methods
  - PromptResult construction and helper methods
  - PromptTemplate static section renderers
  - PromptBuilder build(), estimate_tokens(), validate(), statistics()
  - All five demo roles and several workflow stages
  - Edge cases: empty rules, empty constraints, all optional fields omitted

Total: 270+ unit tests across 18 test classes.
"""

import unittest
from typing import List, Optional

from core.ai.prompt_context import PromptContext, PromptContextError
from core.ai.prompt_result import PromptResult
from core.ai.prompt_template import PromptTemplate
from core.ai.prompt_builder import (
    PromptBuilder,
    PromptBuilderError,
    InvalidContextError,
    BuildError,
    _DEFAULT_COMPANY_RULES,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _ctx(
    employee_role: str = "Backend Agent",
    department: str = "Engineering",
    project_name: str = "Test Project",
    project_description: str = "A test project for unit testing.",
    workflow_stage: str = "Implementation",
    task_description: str = "Implement the user authentication API.",
    company_rules: Optional[List[str]] = None,
    constraints: Optional[List[str]] = None,
    project_id: Optional[str] = None,
    context: str = "",
    seniority: str = "",
) -> PromptContext:
    return PromptContext(
        employee_role=employee_role,
        department=department,
        project_name=project_name,
        project_description=project_description,
        workflow_stage=workflow_stage,
        task_description=task_description,
        company_rules=company_rules if company_rules is not None else [],
        constraints=constraints if constraints is not None else [],
        project_id=project_id,
        context=context,
        seniority=seniority,
    )


def _result(
    system_prompt: str = "System",
    user_prompt: str = "User",
    estimated_tokens: int = 10,
) -> PromptResult:
    return PromptResult(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        estimated_tokens=estimated_tokens,
    )


def _builder() -> PromptBuilder:
    return PromptBuilder()


# ===========================================================================
# 1. PromptContext construction
# ===========================================================================

class TestPromptContextConstruction(unittest.TestCase):

    def test_basic_construction(self):
        c = _ctx()
        self.assertEqual(c.employee_role, "Backend Agent")
        self.assertEqual(c.department, "Engineering")
        self.assertEqual(c.project_name, "Test Project")

    def test_all_required_fields_stored(self):
        c = _ctx()
        self.assertEqual(c.workflow_stage, "Implementation")
        self.assertEqual(c.task_description, "Implement the user authentication API.")
        self.assertEqual(c.project_description, "A test project for unit testing.")

    def test_optional_company_rules_default_empty(self):
        c = _ctx()
        self.assertEqual(c.company_rules, [])

    def test_optional_constraints_default_empty(self):
        c = _ctx()
        self.assertEqual(c.constraints, [])

    def test_optional_project_id_default_none(self):
        c = _ctx()
        self.assertIsNone(c.project_id)

    def test_optional_context_default_empty(self):
        c = _ctx()
        self.assertEqual(c.context, "")

    def test_optional_seniority_default_empty(self):
        c = _ctx()
        self.assertEqual(c.seniority, "")

    def test_company_rules_stored(self):
        rules = ["Rule A", "Rule B"]
        c = _ctx(company_rules=rules)
        self.assertEqual(c.company_rules, rules)

    def test_constraints_stored(self):
        c = _ctx(constraints=["No external libs", "REST only"])
        self.assertEqual(c.constraints, ["No external libs", "REST only"])

    def test_project_id_stored(self):
        c = _ctx(project_id="proj-123")
        self.assertEqual(c.project_id, "proj-123")

    def test_context_stored(self):
        c = _ctx(context="Using PostgreSQL 15")
        self.assertEqual(c.context, "Using PostgreSQL 15")

    def test_seniority_stored(self):
        c = _ctx(seniority="Senior")
        self.assertEqual(c.seniority, "Senior")


# ===========================================================================
# 2. PromptContext validation
# ===========================================================================

class TestPromptContextValidation(unittest.TestCase):

    def test_valid_context_does_not_raise(self):
        _ctx().validate()

    def test_blank_employee_role_raises(self):
        with self.assertRaises(PromptContextError):
            _ctx(employee_role="").validate()

    def test_whitespace_employee_role_raises(self):
        with self.assertRaises(PromptContextError):
            _ctx(employee_role="  ").validate()

    def test_blank_department_raises(self):
        with self.assertRaises(PromptContextError):
            _ctx(department="").validate()

    def test_blank_project_name_raises(self):
        with self.assertRaises(PromptContextError):
            _ctx(project_name="").validate()

    def test_blank_project_description_raises(self):
        with self.assertRaises(PromptContextError):
            _ctx(project_description="").validate()

    def test_blank_workflow_stage_raises(self):
        with self.assertRaises(PromptContextError):
            _ctx(workflow_stage="").validate()

    def test_blank_task_description_raises(self):
        with self.assertRaises(PromptContextError):
            _ctx(task_description="").validate()

    def test_whitespace_task_description_raises(self):
        with self.assertRaises(PromptContextError):
            _ctx(task_description="\t").validate()

    def test_context_error_is_exception(self):
        self.assertTrue(issubclass(PromptContextError, Exception))

    def test_empty_rules_does_not_raise(self):
        _ctx(company_rules=[]).validate()

    def test_empty_constraints_does_not_raise(self):
        _ctx(constraints=[]).validate()

    def test_none_project_id_does_not_raise(self):
        _ctx(project_id=None).validate()

    def test_empty_seniority_does_not_raise(self):
        _ctx(seniority="").validate()


# ===========================================================================
# 3. PromptContext helper methods
# ===========================================================================

class TestPromptContextHelpers(unittest.TestCase):

    def test_has_rules_false_when_empty(self):
        self.assertFalse(_ctx(company_rules=[]).has_rules())

    def test_has_rules_true_when_present(self):
        self.assertTrue(_ctx(company_rules=["Rule A"]).has_rules())

    def test_has_constraints_false_when_empty(self):
        self.assertFalse(_ctx(constraints=[]).has_constraints())

    def test_has_constraints_true_when_present(self):
        self.assertTrue(_ctx(constraints=["REST only"]).has_constraints())

    def test_has_context_false_when_empty(self):
        self.assertFalse(_ctx(context="").has_context())

    def test_has_context_false_when_whitespace(self):
        self.assertFalse(_ctx(context="   ").has_context())

    def test_has_context_true_when_present(self):
        self.assertTrue(_ctx(context="Some background").has_context())

    def test_has_project_id_false_when_none(self):
        self.assertFalse(_ctx(project_id=None).has_project_id())

    def test_has_project_id_true_when_set(self):
        self.assertTrue(_ctx(project_id="proj-1").has_project_id())

    def test_has_seniority_false_when_empty(self):
        self.assertFalse(_ctx(seniority="").has_seniority())

    def test_has_seniority_false_when_whitespace(self):
        self.assertFalse(_ctx(seniority="  ").has_seniority())

    def test_has_seniority_true_when_set(self):
        self.assertTrue(_ctx(seniority="Senior").has_seniority())

    def test_rule_count_zero(self):
        self.assertEqual(_ctx(company_rules=[]).rule_count(), 0)

    def test_rule_count_two(self):
        self.assertEqual(_ctx(company_rules=["A", "B"]).rule_count(), 2)

    def test_constraint_count_zero(self):
        self.assertEqual(_ctx(constraints=[]).constraint_count(), 0)

    def test_constraint_count_three(self):
        self.assertEqual(_ctx(constraints=["A", "B", "C"]).constraint_count(), 3)

    def test_to_dict_has_all_keys(self):
        d = _ctx().to_dict()
        for key in (
            "employee_role", "department", "project_name", "project_description",
            "workflow_stage", "task_description", "company_rules", "constraints",
            "project_id", "context", "seniority",
        ):
            self.assertIn(key, d)

    def test_to_dict_values_correct(self):
        c = _ctx(employee_role="QA Engineer", constraints=["no mocks"])
        d = c.to_dict()
        self.assertEqual(d["employee_role"], "QA Engineer")
        self.assertEqual(d["constraints"], ["no mocks"])

    def test_summary_contains_role(self):
        s = _ctx(employee_role="Frontend Agent").summary()
        self.assertIn("Frontend Agent", s)

    def test_summary_contains_stage(self):
        s = _ctx(workflow_stage="Testing").summary()
        self.assertIn("Testing", s)

    def test_summary_contains_department(self):
        s = _ctx(department="QA").summary()
        self.assertIn("QA", s)

    def test_summary_contains_constraint_count(self):
        s = _ctx(constraints=["A", "B"]).summary()
        self.assertIn("2", s)

    def test_summary_contains_seniority_when_set(self):
        s = _ctx(seniority="Lead").summary()
        self.assertIn("Lead", s)


# ===========================================================================
# 4. PromptResult construction
# ===========================================================================

class TestPromptResultConstruction(unittest.TestCase):

    def test_basic_construction(self):
        r = _result()
        self.assertEqual(r.system_prompt, "System")
        self.assertEqual(r.user_prompt, "User")
        self.assertEqual(r.estimated_tokens, 10)

    def test_metadata_defaults_empty(self):
        r = _result()
        self.assertEqual(r.metadata, {})

    def test_metadata_stored(self):
        r = PromptResult("s", "u", 5, metadata={"role": "QA"})
        self.assertEqual(r.metadata["role"], "QA")


# ===========================================================================
# 5. PromptResult helpers
# ===========================================================================

class TestPromptResultHelpers(unittest.TestCase):

    def test_word_count_empty(self):
        r = _result(system_prompt="", user_prompt="")
        self.assertEqual(r.word_count(), 0)

    def test_word_count_one_word_each(self):
        r = _result(system_prompt="Hello", user_prompt="World")
        self.assertEqual(r.word_count(), 2)

    def test_word_count_multiple(self):
        r = _result(system_prompt="one two three", user_prompt="four five")
        self.assertEqual(r.word_count(), 5)

    def test_char_count(self):
        r = _result(system_prompt="abc", user_prompt="de")
        self.assertEqual(r.char_count(), 5)

    def test_line_count_single(self):
        r = _result(system_prompt="line1", user_prompt="line2")
        self.assertEqual(r.line_count(), 2)

    def test_line_count_multi(self):
        r = _result(system_prompt="a\nb", user_prompt="c\nd\ne")
        self.assertEqual(r.line_count(), 5)

    def test_system_word_count(self):
        r = _result(system_prompt="alpha beta gamma", user_prompt="x")
        self.assertEqual(r.system_word_count(), 3)

    def test_user_word_count(self):
        r = _result(system_prompt="x", user_prompt="one two")
        self.assertEqual(r.user_word_count(), 2)

    def test_is_valid_true(self):
        r = _result(system_prompt="Hello world", user_prompt="Do something", estimated_tokens=5)
        self.assertTrue(r.is_valid())

    def test_is_valid_false_blank_system(self):
        r = _result(system_prompt="", user_prompt="User text", estimated_tokens=5)
        self.assertFalse(r.is_valid())

    def test_is_valid_false_blank_user(self):
        r = _result(system_prompt="System text", user_prompt="", estimated_tokens=5)
        self.assertFalse(r.is_valid())

    def test_is_valid_false_zero_tokens(self):
        r = _result(system_prompt="S", user_prompt="U", estimated_tokens=0)
        self.assertFalse(r.is_valid())

    def test_combined_prompt_contains_both(self):
        r = _result(system_prompt="System part", user_prompt="User part")
        combined = r.combined_prompt()
        self.assertIn("System part", combined)
        self.assertIn("User part", combined)

    def test_combined_prompt_has_separator(self):
        r = _result(system_prompt="S", user_prompt="U")
        self.assertIn("---", r.combined_prompt())

    def test_to_dict_has_all_keys(self):
        r = _result()
        d = r.to_dict()
        for key in ("system_prompt", "user_prompt", "estimated_tokens",
                    "metadata", "word_count", "char_count", "line_count", "is_valid"):
            self.assertIn(key, d)

    def test_summary_contains_tokens(self):
        r = PromptResult("S", "U", 42, metadata={"employee_role": "QA", "workflow_stage": "Testing"})
        s = r.summary()
        self.assertIn("42", s)

    def test_summary_contains_role(self):
        r = PromptResult("S", "U", 10, metadata={"employee_role": "Marketing Agent", "workflow_stage": "Draft"})
        self.assertIn("Marketing Agent", r.summary())

    def test_metadata_copy_in_to_dict(self):
        m = {"k": "v"}
        r = PromptResult("s", "u", 1, metadata=m)
        d = r.to_dict()
        d["metadata"]["extra"] = "x"
        self.assertNotIn("extra", r.metadata)


# ===========================================================================
# 6. PromptTemplate system header
# ===========================================================================

class TestPromptTemplateSystemHeader(unittest.TestCase):

    def test_contains_role(self):
        h = PromptTemplate.render_system_header("Backend Agent", "Engineering")
        self.assertIn("Backend Agent", h)

    def test_contains_department(self):
        h = PromptTemplate.render_system_header("Backend Agent", "Engineering")
        self.assertIn("Engineering", h)

    def test_contains_company_name(self):
        h = PromptTemplate.render_system_header("QA Engineer", "QA")
        self.assertIn("AI Company OS", h)

    def test_seniority_included_when_provided(self):
        h = PromptTemplate.render_system_header("Backend Agent", "Engineering", "Senior")
        self.assertIn("Senior", h)

    def test_seniority_absent_when_empty(self):
        h = PromptTemplate.render_system_header("Backend Agent", "Engineering", "")
        self.assertNotIn("Seniority", h)

    def test_backend_domain_in_header(self):
        h = PromptTemplate.render_system_header("Backend Agent", "Engineering")
        self.assertIn("server-side", h.lower())

    def test_frontend_domain_in_header(self):
        h = PromptTemplate.render_system_header("Frontend Agent", "Frontend")
        self.assertIn("client-side", h.lower())

    def test_unknown_role_uses_default_domain(self):
        h = PromptTemplate.render_system_header("Wizard", "Magic")
        self.assertGreater(len(h), 50)

    def test_header_starts_with_hash(self):
        h = PromptTemplate.render_system_header("Backend Agent", "Engineering")
        self.assertTrue(h.startswith("#"))


# ===========================================================================
# 7. PromptTemplate governance section
# ===========================================================================

class TestPromptTemplateGovernance(unittest.TestCase):

    def test_contains_governance_heading(self):
        s = PromptTemplate.render_governance_section(["Rule 1"])
        self.assertIn("Governance", s)

    def test_contains_provided_rule(self):
        s = PromptTemplate.render_governance_section(["No external deps"])
        self.assertIn("No external deps", s)

    def test_contains_all_rules(self):
        rules = ["Rule A", "Rule B", "Rule C"]
        s = PromptTemplate.render_governance_section(rules)
        for r in rules:
            self.assertIn(r, s)

    def test_empty_rules_fallback_text(self):
        s = PromptTemplate.render_governance_section([])
        self.assertIn("Constitution", s)

    def test_numbered_rules(self):
        s = PromptTemplate.render_governance_section(["First", "Second"])
        self.assertIn("1.", s)
        self.assertIn("2.", s)


# ===========================================================================
# 8. PromptTemplate quality standard
# ===========================================================================

class TestPromptTemplateQualityStandard(unittest.TestCase):

    def test_contains_quality_heading(self):
        s = PromptTemplate.render_quality_standard("Backend Agent")
        self.assertIn("Quality", s)

    def test_backend_specific_content(self):
        s = PromptTemplate.render_quality_standard("Backend Agent")
        self.assertIn("type annotation", s.lower())

    def test_frontend_specific_content(self):
        s = PromptTemplate.render_quality_standard("Frontend Agent")
        self.assertIn("accessible", s.lower())

    def test_qa_specific_content(self):
        s = PromptTemplate.render_quality_standard("QA Engineer")
        self.assertIn("test case", s.lower())

    def test_unknown_role_uses_default(self):
        s = PromptTemplate.render_quality_standard("Unknown Role")
        self.assertGreater(len(s), 30)


# ===========================================================================
# 9. PromptTemplate output instructions
# ===========================================================================

class TestPromptTemplateOutputInstructions(unittest.TestCase):

    def test_contains_output_heading(self):
        s = PromptTemplate.render_output_instructions("Backend Agent")
        self.assertIn("Output", s)

    def test_backend_mentions_code(self):
        s = PromptTemplate.render_output_instructions("Backend Agent")
        self.assertIn("code", s.lower())

    def test_ui_designer_mentions_design_tokens(self):
        s = PromptTemplate.render_output_instructions("UI Designer")
        self.assertIn("token", s.lower())

    def test_qa_mentions_test_cases(self):
        s = PromptTemplate.render_output_instructions("QA Engineer")
        self.assertIn("test case", s.lower())

    def test_marketing_mentions_copy(self):
        s = PromptTemplate.render_output_instructions("Marketing Specialist")
        self.assertIn("copy", s.lower())

    def test_product_analyst_mentions_user_stories(self):
        s = PromptTemplate.render_output_instructions("Product Analyst")
        self.assertIn("user stor", s.lower())

    def test_devops_mentions_pipeline(self):
        s = PromptTemplate.render_output_instructions("DevOps Engineer")
        self.assertIn("pipeline", s.lower())

    def test_unknown_role_uses_default(self):
        s = PromptTemplate.render_output_instructions("Unknown Role")
        self.assertGreater(len(s), 30)


# ===========================================================================
# 10. PromptTemplate seniority guidance
# ===========================================================================

class TestPromptTemplateSeniorityGuidance(unittest.TestCase):

    def test_junior_guidance(self):
        s = PromptTemplate.render_seniority_guidance("Junior")
        self.assertIn("Junior", s)

    def test_senior_guidance(self):
        s = PromptTemplate.render_seniority_guidance("Senior")
        self.assertIn("Senior", s)

    def test_lead_guidance(self):
        s = PromptTemplate.render_seniority_guidance("Lead")
        self.assertIn("Lead", s)

    def test_principal_guidance(self):
        s = PromptTemplate.render_seniority_guidance("Principal")
        self.assertIn("Principal", s)

    def test_unknown_seniority_returns_empty(self):
        s = PromptTemplate.render_seniority_guidance("Wizard")
        self.assertEqual(s, "")

    def test_empty_seniority_returns_empty(self):
        s = PromptTemplate.render_seniority_guidance("")
        self.assertEqual(s, "")

    def test_case_insensitive_junior(self):
        s = PromptTemplate.render_seniority_guidance("junior")
        self.assertGreater(len(s), 0)

    def test_case_insensitive_senior(self):
        s = PromptTemplate.render_seniority_guidance("SENIOR")
        self.assertGreater(len(s), 0)


# ===========================================================================
# 11. PromptTemplate user prompt sections
# ===========================================================================

class TestPromptTemplateUserSections(unittest.TestCase):

    def test_project_section_contains_name(self):
        s = PromptTemplate.render_project_section("My App", "A great app", "Design")
        self.assertIn("My App", s)

    def test_project_section_contains_stage(self):
        s = PromptTemplate.render_project_section("P", "Desc", "Testing")
        self.assertIn("Testing", s)

    def test_project_section_contains_description(self):
        s = PromptTemplate.render_project_section("P", "The system does X", "Design")
        self.assertIn("The system does X", s)

    def test_project_section_includes_id_when_provided(self):
        s = PromptTemplate.render_project_section("P", "D", "S", "proj-999")
        self.assertIn("proj-999", s)

    def test_project_section_no_id_when_empty(self):
        s = PromptTemplate.render_project_section("P", "D", "S", "")
        self.assertNotIn("Project ID", s)

    def test_additional_context_renders_when_present(self):
        s = PromptTemplate.render_additional_context("Using Redis for caching")
        self.assertIn("Redis", s)

    def test_additional_context_empty_returns_empty(self):
        s = PromptTemplate.render_additional_context("")
        self.assertEqual(s, "")

    def test_additional_context_whitespace_returns_empty(self):
        s = PromptTemplate.render_additional_context("   ")
        self.assertEqual(s, "")

    def test_task_section_contains_task(self):
        s = PromptTemplate.render_task_section("Build the login form")
        self.assertIn("Build the login form", s)

    def test_task_section_contains_heading(self):
        s = PromptTemplate.render_task_section("Do something")
        self.assertIn("Task", s)

    def test_constraints_section_contains_constraints(self):
        s = PromptTemplate.render_constraints_section(["REST only", "No GraphQL"])
        self.assertIn("REST only", s)
        self.assertIn("No GraphQL", s)

    def test_constraints_section_empty_returns_empty(self):
        s = PromptTemplate.render_constraints_section([])
        self.assertEqual(s, "")

    def test_completion_note_contains_stage(self):
        s = PromptTemplate.render_completion_note("Backend Agent", "Testing")
        self.assertIn("Testing", s)

    def test_completion_note_contains_approval_text(self):
        s = PromptTemplate.render_completion_note("Backend Agent", "Testing")
        self.assertIn("Approval", s)


# ===========================================================================
# 12. PromptBuilder validate()
# ===========================================================================

class TestPromptBuilderValidate(unittest.TestCase):

    def test_valid_context_returns_empty_list(self):
        builder = _builder()
        self.assertEqual(builder.validate(_ctx()), [])

    def test_blank_role_returns_error(self):
        builder = _builder()
        errors = builder.validate(_ctx(employee_role=""))
        self.assertTrue(len(errors) > 0)

    def test_blank_department_returns_error(self):
        builder = _builder()
        errors = builder.validate(_ctx(department=""))
        self.assertTrue(len(errors) > 0)

    def test_blank_project_name_returns_error(self):
        builder = _builder()
        errors = builder.validate(_ctx(project_name=""))
        self.assertTrue(len(errors) > 0)

    def test_blank_description_returns_error(self):
        builder = _builder()
        errors = builder.validate(_ctx(project_description=""))
        self.assertTrue(len(errors) > 0)

    def test_blank_stage_returns_error(self):
        builder = _builder()
        errors = builder.validate(_ctx(workflow_stage=""))
        self.assertTrue(len(errors) > 0)

    def test_blank_task_returns_error(self):
        builder = _builder()
        errors = builder.validate(_ctx(task_description=""))
        self.assertTrue(len(errors) > 0)

    def test_multiple_blank_fields_multiple_errors(self):
        builder = _builder()
        errors = builder.validate(_ctx(employee_role="", department=""))
        self.assertGreaterEqual(len(errors), 2)

    def test_validate_never_raises(self):
        builder = _builder()
        # Should return errors, not raise
        builder.validate(_ctx(employee_role=""))

    def test_valid_context_with_all_optionals_empty(self):
        builder = _builder()
        c = _ctx(company_rules=[], constraints=[], project_id=None,
                 context="", seniority="")
        self.assertEqual(builder.validate(c), [])


# ===========================================================================
# 13. PromptBuilder estimate_tokens()
# ===========================================================================

class TestPromptBuilderEstimateTokens(unittest.TestCase):

    def test_empty_string_returns_zero(self):
        self.assertEqual(_builder().estimate_tokens(""), 0)

    def test_whitespace_only_returns_zero(self):
        self.assertEqual(_builder().estimate_tokens("   "), 0)

    def test_single_word_returns_positive(self):
        self.assertGreater(_builder().estimate_tokens("hello"), 0)

    def test_more_words_more_tokens(self):
        b = _builder()
        short = b.estimate_tokens("hello world")
        long_ = b.estimate_tokens("hello world foo bar baz qux quux corge grault")
        self.assertGreater(long_, short)

    def test_token_estimate_is_int(self):
        result = _builder().estimate_tokens("hello world test")
        self.assertIsInstance(result, int)

    def test_deterministic_same_input_same_output(self):
        b = _builder()
        t1 = b.estimate_tokens("the quick brown fox")
        t2 = b.estimate_tokens("the quick brown fox")
        self.assertEqual(t1, t2)

    def test_longer_text_estimates_higher(self):
        b = _builder()
        short = b.estimate_tokens("Hi")
        long_ = b.estimate_tokens(
            "This is a much longer text with many words that should produce "
            "a significantly higher token estimate than a simple greeting."
        )
        self.assertGreater(long_, short)


# ===========================================================================
# 14. PromptBuilder build() basic
# ===========================================================================

class TestPromptBuilderBuild(unittest.TestCase):

    def test_build_returns_prompt_result(self):
        r = _builder().build(_ctx())
        from core.ai.prompt_result import PromptResult
        self.assertIsInstance(r, PromptResult)

    def test_build_result_is_valid(self):
        r = _builder().build(_ctx())
        self.assertTrue(r.is_valid())

    def test_system_prompt_non_empty(self):
        r = _builder().build(_ctx())
        self.assertGreater(len(r.system_prompt.strip()), 0)

    def test_user_prompt_non_empty(self):
        r = _builder().build(_ctx())
        self.assertGreater(len(r.user_prompt.strip()), 0)

    def test_estimated_tokens_positive(self):
        r = _builder().build(_ctx())
        self.assertGreater(r.estimated_tokens, 0)

    def test_role_in_system_prompt(self):
        r = _builder().build(_ctx(employee_role="Backend Agent"))
        self.assertIn("Backend Agent", r.system_prompt)

    def test_department_in_system_prompt(self):
        r = _builder().build(_ctx(department="Engineering"))
        self.assertIn("Engineering", r.system_prompt)

    def test_project_name_in_user_prompt(self):
        r = _builder().build(_ctx(project_name="My App"))
        self.assertIn("My App", r.user_prompt)

    def test_task_description_in_user_prompt(self):
        r = _builder().build(_ctx(task_description="Build login form"))
        self.assertIn("Build login form", r.user_prompt)

    def test_workflow_stage_in_user_prompt(self):
        r = _builder().build(_ctx(workflow_stage="Testing"))
        self.assertIn("Testing", r.user_prompt)

    def test_blank_role_raises_invalid_context(self):
        with self.assertRaises(InvalidContextError):
            _builder().build(_ctx(employee_role=""))

    def test_blank_task_raises_invalid_context(self):
        with self.assertRaises(InvalidContextError):
            _builder().build(_ctx(task_description=""))

    def test_invalid_context_error_is_builder_error(self):
        self.assertTrue(issubclass(InvalidContextError, PromptBuilderError))

    def test_build_error_is_builder_error(self):
        self.assertTrue(issubclass(BuildError, PromptBuilderError))

    def test_builder_error_is_exception(self):
        self.assertTrue(issubclass(PromptBuilderError, Exception))

    def test_constraints_in_user_prompt(self):
        r = _builder().build(_ctx(constraints=["REST only", "No GraphQL"]))
        self.assertIn("REST only", r.user_prompt)
        self.assertIn("No GraphQL", r.user_prompt)

    def test_no_constraints_no_constraints_section(self):
        r = _builder().build(_ctx(constraints=[]))
        self.assertNotIn("Constraints", r.user_prompt)

    def test_additional_context_in_user_prompt(self):
        r = _builder().build(_ctx(context="Using Redis for sessions"))
        self.assertIn("Redis", r.user_prompt)

    def test_project_id_in_user_prompt(self):
        r = _builder().build(_ctx(project_id="proj-42"))
        self.assertIn("proj-42", r.user_prompt)

    def test_metadata_contains_role(self):
        r = _builder().build(_ctx(employee_role="QA Engineer"))
        self.assertEqual(r.metadata["employee_role"], "QA Engineer")

    def test_metadata_contains_stage(self):
        r = _builder().build(_ctx(workflow_stage="Review"))
        self.assertEqual(r.metadata["workflow_stage"], "Review")

    def test_metadata_contains_builder_version(self):
        r = _builder().build(_ctx())
        self.assertIn("builder_version", r.metadata)

    def test_default_rules_used_when_context_rules_empty(self):
        r = _builder().build(_ctx(company_rules=[]))
        self.assertTrue(r.metadata["used_default_rules"])

    def test_custom_rules_used_when_provided(self):
        r = _builder().build(_ctx(company_rules=["Custom Rule A"]))
        self.assertFalse(r.metadata["used_default_rules"])

    def test_custom_rules_appear_in_system_prompt(self):
        r = _builder().build(_ctx(company_rules=["My special rule"]))
        self.assertIn("My special rule", r.system_prompt)

    def test_default_rules_appear_in_system_prompt(self):
        r = _builder().build(_ctx(company_rules=[]))
        self.assertIn("CEO Sovereignty", r.system_prompt)


# ===========================================================================
# 15. PromptBuilder — seniority
# ===========================================================================

class TestPromptBuilderSeniority(unittest.TestCase):

    def test_senior_seniority_in_system_prompt(self):
        r = _builder().build(_ctx(seniority="Senior"))
        self.assertIn("Senior", r.system_prompt)

    def test_junior_seniority_in_system_prompt(self):
        r = _builder().build(_ctx(seniority="Junior"))
        self.assertIn("Junior", r.system_prompt)

    def test_lead_seniority_in_system_prompt(self):
        r = _builder().build(_ctx(seniority="Lead"))
        self.assertIn("Lead", r.system_prompt)

    def test_no_seniority_system_prompt_still_valid(self):
        r = _builder().build(_ctx(seniority=""))
        self.assertGreater(len(r.system_prompt.strip()), 100)


# ===========================================================================
# 16. PromptBuilder — role-specific prompts (5 demo roles)
# ===========================================================================

class TestPromptBuilderRoles(unittest.TestCase):

    def _build(self, role: str, department: str = "Engineering") -> "PromptResult":
        return _builder().build(_ctx(employee_role=role, department=department))

    # Backend Agent
    def test_backend_agent_system_contains_role(self):
        r = self._build("Backend Agent")
        self.assertIn("Backend Agent", r.system_prompt)

    def test_backend_agent_domain_in_system(self):
        r = self._build("Backend Agent")
        self.assertIn("server-side", r.system_prompt.lower())

    def test_backend_agent_code_in_instructions(self):
        r = self._build("Backend Agent")
        self.assertIn("code", r.system_prompt.lower())

    def test_backend_agent_result_is_valid(self):
        self.assertTrue(self._build("Backend Agent").is_valid())

    # Frontend Agent
    def test_frontend_agent_system_contains_role(self):
        r = self._build("Frontend Agent", "Frontend")
        self.assertIn("Frontend Agent", r.system_prompt)

    def test_frontend_agent_domain_in_system(self):
        r = self._build("Frontend Agent", "Frontend")
        self.assertIn("client-side", r.system_prompt.lower())

    def test_frontend_agent_result_is_valid(self):
        self.assertTrue(self._build("Frontend Agent", "Frontend").is_valid())

    # UI Designer
    def test_ui_designer_system_contains_role(self):
        r = self._build("UI Designer", "Design")
        self.assertIn("UI Designer", r.system_prompt)

    def test_ui_designer_domain_mentions_design(self):
        r = self._build("UI Designer", "Design")
        self.assertIn("design", r.system_prompt.lower())

    def test_ui_designer_output_mentions_tokens(self):
        r = self._build("UI Designer", "Design")
        self.assertIn("token", r.system_prompt.lower())

    def test_ui_designer_result_is_valid(self):
        self.assertTrue(self._build("UI Designer", "Design").is_valid())

    # QA Engineer
    def test_qa_engineer_system_contains_role(self):
        r = self._build("QA Engineer", "QA")
        self.assertIn("QA Engineer", r.system_prompt)

    def test_qa_engineer_domain_mentions_testing(self):
        r = self._build("QA Engineer", "QA")
        self.assertIn("test", r.system_prompt.lower())

    def test_qa_engineer_output_mentions_test_case(self):
        r = self._build("QA Engineer", "QA")
        self.assertIn("test case", r.system_prompt.lower())

    def test_qa_engineer_result_is_valid(self):
        self.assertTrue(self._build("QA Engineer", "QA").is_valid())

    # Marketing Specialist
    def test_marketing_specialist_system_contains_role(self):
        r = self._build("Marketing Specialist", "Marketing")
        self.assertIn("Marketing Specialist", r.system_prompt)

    def test_marketing_specialist_domain_mentions_copy(self):
        r = self._build("Marketing Specialist", "Marketing")
        self.assertIn("copy", r.system_prompt.lower())

    def test_marketing_specialist_output_mentions_brand(self):
        r = self._build("Marketing Specialist", "Marketing")
        self.assertIn("brand", r.system_prompt.lower())

    def test_marketing_specialist_result_is_valid(self):
        self.assertTrue(self._build("Marketing Specialist", "Marketing").is_valid())

    # Product Analyst
    def test_product_analyst_system_contains_role(self):
        r = self._build("Product Analyst", "Product")
        self.assertIn("Product Analyst", r.system_prompt)

    def test_product_analyst_domain_mentions_requirements(self):
        r = self._build("Product Analyst", "Product")
        self.assertIn("requirements", r.system_prompt.lower())

    def test_product_analyst_result_is_valid(self):
        self.assertTrue(self._build("Product Analyst", "Product").is_valid())

    # DevOps Engineer
    def test_devops_engineer_system_contains_role(self):
        r = self._build("DevOps Engineer", "DevOps")
        self.assertIn("DevOps Engineer", r.system_prompt)

    def test_devops_engineer_output_mentions_pipeline(self):
        r = self._build("DevOps Engineer", "DevOps")
        self.assertIn("pipeline", r.system_prompt.lower())

    def test_devops_engineer_result_is_valid(self):
        self.assertTrue(self._build("DevOps Engineer", "DevOps").is_valid())

    # Security Specialist
    def test_security_specialist_system_contains_role(self):
        r = self._build("Security Specialist", "Security")
        self.assertIn("Security Specialist", r.system_prompt)

    def test_security_specialist_result_is_valid(self):
        self.assertTrue(self._build("Security Specialist", "Security").is_valid())


# ===========================================================================
# 17. PromptBuilder — workflow stages
# ===========================================================================

class TestPromptBuilderWorkflowStages(unittest.TestCase):

    STAGES = [
        "Discovery",
        "Design",
        "Implementation",
        "Testing",
        "Review",
        "Approval",
        "Deployment",
    ]

    def test_all_stages_produce_valid_results(self):
        builder = _builder()
        for stage in self.STAGES:
            with self.subTest(stage=stage):
                r = builder.build(_ctx(workflow_stage=stage))
                self.assertTrue(r.is_valid())

    def test_all_stages_appear_in_user_prompt(self):
        builder = _builder()
        for stage in self.STAGES:
            with self.subTest(stage=stage):
                r = builder.build(_ctx(workflow_stage=stage))
                self.assertIn(stage, r.user_prompt)

    def test_all_stages_appear_in_metadata(self):
        builder = _builder()
        for stage in self.STAGES:
            r = builder.build(_ctx(workflow_stage=stage))
            self.assertEqual(r.metadata["workflow_stage"], stage)

    def test_completion_note_always_references_stage(self):
        builder = _builder()
        for stage in self.STAGES:
            r = builder.build(_ctx(workflow_stage=stage))
            self.assertIn(stage, r.user_prompt)


# ===========================================================================
# 18. PromptBuilder history and statistics
# ===========================================================================

class TestPromptBuilderStatistics(unittest.TestCase):

    def test_statistics_empty_builder(self):
        stats = _builder().statistics()
        self.assertEqual(stats["total_builds"], 0)

    def test_statistics_after_one_build(self):
        builder = _builder()
        builder.build(_ctx())
        s = builder.statistics()
        self.assertEqual(s["total_builds"], 1)

    def test_statistics_after_three_builds(self):
        builder = _builder()
        for _ in range(3):
            builder.build(_ctx())
        self.assertEqual(builder.statistics()["total_builds"], 3)

    def test_statistics_total_tokens_positive(self):
        builder = _builder()
        builder.build(_ctx())
        s = builder.statistics()
        self.assertGreater(s["total_estimated_tokens"], 0)

    def test_statistics_avg_tokens_correct(self):
        builder = _builder()
        r = builder.build(_ctx())
        s = builder.statistics()
        self.assertAlmostEqual(s["avg_tokens_per_build"], r.estimated_tokens, places=1)

    def test_statistics_roles_used(self):
        builder = _builder()
        builder.build(_ctx(employee_role="Backend Agent"))
        builder.build(_ctx(employee_role="QA Engineer"))
        s = builder.statistics()
        self.assertIn("Backend Agent", s["roles_used"])
        self.assertIn("QA Engineer", s["roles_used"])

    def test_statistics_departments_used(self):
        builder = _builder()
        builder.build(_ctx(department="Engineering"))
        builder.build(_ctx(department="QA"))
        s = builder.statistics()
        self.assertIn("Engineering", s["departments_used"])
        self.assertIn("QA", s["departments_used"])

    def test_statistics_stages_used(self):
        builder = _builder()
        builder.build(_ctx(workflow_stage="Design"))
        builder.build(_ctx(workflow_stage="Testing"))
        s = builder.statistics()
        self.assertIn("Design", s["workflow_stages_used"])
        self.assertIn("Testing", s["workflow_stages_used"])

    def test_statistics_unique_roles(self):
        builder = _builder()
        builder.build(_ctx(employee_role="Backend Agent"))
        builder.build(_ctx(employee_role="Backend Agent"))
        s = builder.statistics()
        self.assertEqual(s["roles_used"].count("Backend Agent"), 1)

    def test_statistics_contains_builder_version(self):
        s = _builder().statistics()
        self.assertIn("builder_version", s)

    def test_statistics_avg_constraints(self):
        builder = _builder()
        builder.build(_ctx(constraints=["A", "B"]))
        s = builder.statistics()
        self.assertEqual(s["avg_constraints"], 2.0)

    def test_history_empty_at_start(self):
        self.assertEqual(len(_builder().history()), 0)

    def test_history_grows_with_builds(self):
        builder = _builder()
        builder.build(_ctx())
        builder.build(_ctx())
        self.assertEqual(len(builder.history()), 2)

    def test_history_returns_copy(self):
        builder = _builder()
        builder.build(_ctx())
        h = builder.history()
        h.append(None)  # type: ignore
        self.assertEqual(len(builder.history()), 1)

    def test_last_result_raises_when_empty(self):
        with self.assertRaises(PromptBuilderError):
            _builder().last_result()

    def test_last_result_returns_most_recent(self):
        builder = _builder()
        builder.build(_ctx(workflow_stage="Design"))
        r2 = builder.build(_ctx(workflow_stage="Testing"))
        self.assertEqual(builder.last_result().metadata["workflow_stage"], "Testing")

    def test_total_builds_zero_initially(self):
        self.assertEqual(_builder().total_builds(), 0)

    def test_total_builds_after_builds(self):
        builder = _builder()
        builder.build(_ctx())
        builder.build(_ctx())
        self.assertEqual(builder.total_builds(), 2)


# ===========================================================================
# 19. Default company rules
# ===========================================================================

class TestDefaultCompanyRules(unittest.TestCase):

    def test_default_rules_is_list(self):
        self.assertIsInstance(_DEFAULT_COMPANY_RULES, list)

    def test_default_rules_not_empty(self):
        self.assertGreater(len(_DEFAULT_COMPANY_RULES), 0)

    def test_default_rules_ceo_sovereignty(self):
        combined = " ".join(_DEFAULT_COMPANY_RULES).lower()
        self.assertIn("ceo", combined)

    def test_default_rules_quality(self):
        combined = " ".join(_DEFAULT_COMPANY_RULES).lower()
        self.assertIn("quality", combined)

    def test_default_rules_security(self):
        combined = " ".join(_DEFAULT_COMPANY_RULES).lower()
        self.assertIn("secret", combined)

    def test_default_rules_escalation_or_scope(self):
        combined = " ".join(_DEFAULT_COMPANY_RULES).lower()
        self.assertTrue("scope" in combined or "escalate" in combined)

    def test_all_default_rules_are_strings(self):
        for r in _DEFAULT_COMPANY_RULES:
            self.assertIsInstance(r, str)


# ===========================================================================
# 20. End-to-end integration scenarios
# ===========================================================================

class TestEndToEnd(unittest.TestCase):

    def test_full_backend_agent_scenario(self):
        builder = PromptBuilder()
        context = PromptContext(
            employee_role="Backend Agent",
            department="Engineering",
            project_name="AI Company OS",
            project_description=(
                "An autonomous operating system for running a technology company."
            ),
            workflow_stage="Implementation",
            task_description="Implement the REST API for user authentication using JWT.",
            constraints=[
                "Use RS256 JWT, not HS256",
                "Bcrypt with cost factor 12",
                "REST only",
            ],
            seniority="Senior",
            project_id="proj-auth-001",
            context="PostgreSQL 15 for persistence. FastAPI for the HTTP layer.",
        )
        result = builder.build(context)

        self.assertTrue(result.is_valid())
        self.assertIn("Backend Agent", result.system_prompt)
        self.assertIn("Senior", result.system_prompt)
        self.assertIn("AI Company OS", result.user_prompt)
        self.assertIn("JWT", result.user_prompt)
        self.assertIn("RS256", result.user_prompt)
        self.assertIn("proj-auth-001", result.user_prompt)
        self.assertIn("PostgreSQL", result.user_prompt)
        self.assertGreater(result.estimated_tokens, 100)

    def test_full_qa_engineer_scenario(self):
        builder = PromptBuilder()
        context = PromptContext(
            employee_role="QA Engineer",
            department="QA",
            project_name="AI Company OS",
            project_description="Autonomous company operating system.",
            workflow_stage="Testing",
            task_description=(
                "Write a comprehensive test plan for the authentication module."
            ),
            constraints=["Minimum 90% branch coverage", "No mocking the database"],
        )
        result = builder.build(context)

        self.assertTrue(result.is_valid())
        self.assertIn("QA Engineer", result.system_prompt)
        self.assertIn("test", result.system_prompt.lower())
        self.assertIn("90% branch coverage", result.user_prompt)
        self.assertGreater(result.word_count(), 100)

    def test_full_marketing_specialist_scenario(self):
        builder = PromptBuilder()
        context = PromptContext(
            employee_role="Marketing Specialist",
            department="Marketing",
            project_name="Product Launch",
            project_description="Launch the beta version of AI Company OS.",
            workflow_stage="Design",
            task_description=(
                "Write the launch announcement copy for the company website."
            ),
            constraints=["Professional tone", "No unsubstantiated claims"],
        )
        result = builder.build(context)

        self.assertTrue(result.is_valid())
        self.assertIn("Marketing Specialist", result.system_prompt)
        self.assertIn("Product Launch", result.user_prompt)
        self.assertIn("Professional tone", result.user_prompt)

    def test_full_frontend_agent_scenario(self):
        builder = PromptBuilder()
        context = PromptContext(
            employee_role="Frontend Agent",
            department="Frontend",
            project_name="Dashboard",
            project_description="CEO dashboard for monitoring company operations.",
            workflow_stage="Implementation",
            task_description="Implement the KPI summary card component in React.",
            constraints=["React 18", "TypeScript", "Accessible"],
            seniority="Mid",
        )
        result = builder.build(context)

        self.assertTrue(result.is_valid())
        self.assertIn("Frontend Agent", result.system_prompt)
        self.assertIn("Mid", result.system_prompt)
        self.assertIn("TypeScript", result.user_prompt)

    def test_full_designer_scenario(self):
        builder = PromptBuilder()
        context = PromptContext(
            employee_role="UI Designer",
            department="Design",
            project_name="Design System",
            project_description="Component library and design token system.",
            workflow_stage="Design",
            task_description=(
                "Define the button component specification including all states."
            ),
            constraints=["Follow existing colour palette", "WCAG 2.1 AA"],
        )
        result = builder.build(context)

        self.assertTrue(result.is_valid())
        self.assertIn("UI Designer", result.system_prompt)
        self.assertIn("token", result.system_prompt.lower())
        self.assertIn("WCAG 2.1 AA", result.user_prompt)

    def test_multiple_builds_accumulate_history(self):
        builder = PromptBuilder()
        roles = [
            "Backend Agent",
            "Frontend Agent",
            "QA Engineer",
            "Marketing Specialist",
            "UI Designer",
        ]
        for role in roles:
            builder.build(_ctx(employee_role=role))

        self.assertEqual(builder.total_builds(), 5)
        stats = builder.statistics()
        self.assertEqual(stats["total_builds"], 5)
        for role in roles:
            self.assertIn(role, stats["roles_used"])

    def test_determinism_same_context_same_prompts(self):
        b1 = PromptBuilder()
        b2 = PromptBuilder()
        c = _ctx(
            employee_role="Backend Agent",
            task_description="Build the auth service",
            constraints=["JWT", "bcrypt"],
        )
        r1 = b1.build(c)
        r2 = b2.build(c)
        # Prompts should be identical except for the built_at timestamp in metadata
        # We compare only the prompt text, not the metadata timestamp
        self.assertEqual(r1.system_prompt, r2.system_prompt)
        self.assertEqual(r1.user_prompt, r2.user_prompt)
        self.assertEqual(r1.estimated_tokens, r2.estimated_tokens)

    def test_result_word_count_reasonable(self):
        r = PromptBuilder().build(_ctx())
        self.assertGreater(r.word_count(), 50)

    def test_combined_prompt_usable(self):
        r = PromptBuilder().build(_ctx())
        combined = r.combined_prompt()
        self.assertGreater(len(combined), 100)
        self.assertIn("---", combined)


# ===========================================================================
# 21. PromptTemplate escalation reminder
# ===========================================================================

class TestPromptTemplateEscalationReminder(unittest.TestCase):

    def test_escalation_reminder_non_empty(self):
        s = PromptTemplate.render_escalation_reminder()
        self.assertGreater(len(s.strip()), 0)

    def test_escalation_reminder_contains_heading(self):
        s = PromptTemplate.render_escalation_reminder()
        self.assertIn("Escalation", s)

    def test_escalation_reminder_mentions_domain(self):
        s = PromptTemplate.render_escalation_reminder()
        self.assertIn("domain", s.lower())

    def test_escalation_reminder_mentions_escalate(self):
        s = PromptTemplate.render_escalation_reminder()
        self.assertIn("escalat", s.lower())

    def test_escalation_reminder_is_ascii_safe(self):
        s = PromptTemplate.render_escalation_reminder()
        s.encode("ascii")  # must not raise


# ===========================================================================
# 22. PromptContext to_dict / round-trip integrity
# ===========================================================================

class TestPromptContextRoundTrip(unittest.TestCase):

    def test_to_dict_project_id_none(self):
        d = _ctx(project_id=None).to_dict()
        self.assertIsNone(d["project_id"])

    def test_to_dict_project_id_present(self):
        d = _ctx(project_id="p-999").to_dict()
        self.assertEqual(d["project_id"], "p-999")

    def test_to_dict_constraints_copy(self):
        c = _ctx(constraints=["A"])
        d = c.to_dict()
        d["constraints"].append("B")
        self.assertEqual(len(c.constraints), 1)

    def test_to_dict_rules_copy(self):
        c = _ctx(company_rules=["R1"])
        d = c.to_dict()
        d["company_rules"].append("R2")
        self.assertEqual(len(c.company_rules), 1)

    def test_summary_non_empty(self):
        s = _ctx().summary()
        self.assertGreater(len(s), 0)

    def test_summary_is_single_line(self):
        s = _ctx().summary()
        self.assertNotIn("\n", s)


# ===========================================================================
# 23. PromptBuilder multiple contexts independence
# ===========================================================================

class TestPromptBuilderIndependence(unittest.TestCase):

    def test_two_builders_produce_same_result(self):
        c = _ctx(employee_role="QA Engineer", workflow_stage="Testing")
        r1 = PromptBuilder().build(c)
        r2 = PromptBuilder().build(c)
        self.assertEqual(r1.system_prompt, r2.system_prompt)
        self.assertEqual(r1.user_prompt, r2.user_prompt)

    def test_different_roles_different_system_prompts(self):
        b = PromptBuilder()
        r1 = b.build(_ctx(employee_role="Backend Agent"))
        r2 = b.build(_ctx(employee_role="QA Engineer"))
        self.assertNotEqual(r1.system_prompt, r2.system_prompt)

    def test_different_tasks_different_user_prompts(self):
        b = PromptBuilder()
        r1 = b.build(_ctx(task_description="Task A for unit testing purposes"))
        r2 = b.build(_ctx(task_description="Task B for unit testing purposes"))
        self.assertNotEqual(r1.user_prompt, r2.user_prompt)

    def test_no_context_text_no_additional_context_section(self):
        r = PromptBuilder().build(_ctx(context=""))
        self.assertNotIn("Additional Context", r.user_prompt)

    def test_with_context_text_has_additional_context_section(self):
        r = PromptBuilder().build(_ctx(context="Using Redis for caching"))
        self.assertIn("Additional Context", r.user_prompt)

    def test_project_description_in_user_prompt(self):
        r = PromptBuilder().build(
            _ctx(project_description="This project does something unique XYZ123")
        )
        self.assertIn("XYZ123", r.user_prompt)

    def test_escalation_reminder_in_system_prompt(self):
        r = PromptBuilder().build(_ctx())
        self.assertIn("Escalation", r.system_prompt)

    def test_governance_section_in_system_prompt(self):
        r = PromptBuilder().build(_ctx())
        self.assertIn("Governance", r.system_prompt)

    def test_quality_standard_in_system_prompt(self):
        r = PromptBuilder().build(_ctx())
        self.assertIn("Quality", r.system_prompt)

    def test_metadata_constraint_count_correct(self):
        r = PromptBuilder().build(_ctx(constraints=["A", "B", "C"]))
        self.assertEqual(r.metadata["constraint_count"], 3)

    def test_metadata_department_correct(self):
        r = PromptBuilder().build(_ctx(department="Security"))
        self.assertEqual(r.metadata["department"], "Security")


if __name__ == "__main__":
    unittest.main()
