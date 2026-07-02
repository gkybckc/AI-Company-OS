"""
Agent Executor for AI Company OS.

The AgentExecutor runs a single company task from start to finish by
coordinating four sub-systems:
  - PromptBuilder    (assembles the AI prompt from structured context)
  - ProviderRegistry (the ONLY authorized path to an AI provider)
  - ArtifactEngine   (generates versioned task artifacts -- optional)
  - MemoryEngine     (stores execution knowledge -- optional)

The executor itself contains NO business logic. It owns only the orchestration:
sequencing the pipeline stages, forwarding results between them, catching errors
gracefully, and recording history.

Execution Pipeline
------------------
ExecutionContext
  -> validate()                 Structural check; aborts on failure.
  -> _build_prompt_context()    Convert ExecutionContext to PromptContext.
  -> PromptBuilder.build()      Assemble system + user prompts.
  -> _build_provider_request()  Convert PromptResult to ProviderRequest.
  -> ProviderRegistry.get_active().generate()  Call the AI provider.
  -> ArtifactEngine (optional)  generate_task_report() if project_id present.
  -> MemoryEngine (optional)    store() execution record.
  -> ExecutionResult            Aggregate outcome.

Architectural constraints
-------------------------
  - Only ProviderRegistry is used to reach an AI provider; no provider
    is imported or instantiated directly.
  - No async, no networking, no AI-specific code.
  - Pure orchestration: all domain logic lives in the sub-systems.

Architecture reference: §2 Core Components, §2.10 LLM Gateway,
§3 Layer 2 (Intelligence Layer), Architectural Constraint 6.
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.ai.execution_context import ExecutionContext
from core.ai.execution_history import ExecutionHistory, ExecutionRecord
from core.ai.execution_result import ExecutionResult
from core.ai.prompt_builder import PromptBuilder
from core.ai.prompt_context import PromptContext
from core.ai.provider_registry import ProviderRegistry
from core.ai.provider_request import ProviderRequest
from core.memory_category import MemoryCategory
from core.memory_entry import MemoryEntry
from core.memory_scope import MemoryScope


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ExecutionError(Exception):
    """Base exception for AgentExecutor errors."""


class AgentInvalidContextError(ExecutionError):
    """Defined for callers who want typed error handling; not raised by execute()."""


class MissingProviderError(ExecutionError):
    """Defined for callers who want typed error handling; not raised by execute()."""


# ---------------------------------------------------------------------------
# AgentExecutor
# ---------------------------------------------------------------------------

_EXECUTOR_VERSION = "1.0"


class AgentExecutor:
    """
    Stateful orchestrator for single-agent task execution.

    Usage pattern::

        registry = ProviderRegistry()
        registry.register(MockProvider())

        executor = AgentExecutor(provider_registry=registry)

        context = ExecutionContext(
            employee_id="agent-001",
            employee_role="Backend Agent",
            department="Engineering",
            project=my_project,
            workflow_stage="Implementation",
            task=my_task,
        )

        result = executor.execute(context)
        print(result.summary())

    The executor keeps a full execution history; statistics() returns
    aggregate metrics across all executions.
    """

    def __init__(
        self,
        *,
        provider_registry: ProviderRegistry,
        prompt_builder: Optional[PromptBuilder] = None,
        artifact_engine: Any = None,
        memory_engine: Any = None,
    ) -> None:
        """
        Initialise the AgentExecutor.

        Args:
            provider_registry: The ONLY authorized path to an AI provider.
            prompt_builder:    Prompt assembler. Defaults to PromptBuilder()
                               if not provided.
            artifact_engine:   Optional ArtifactEngine. Skipped if None.
            memory_engine:     Optional MemoryEngine. Skipped if None.
        """
        self._provider_registry = provider_registry
        self._prompt_builder = (
            prompt_builder if prompt_builder is not None else PromptBuilder()
        )
        self._artifact_engine = artifact_engine
        self._memory_engine = memory_engine
        self._execution_history = ExecutionHistory()

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def execute(self, context: ExecutionContext) -> ExecutionResult:
        """
        Execute a task described by the given context.

        Runs the full pipeline. Failures in the core stages (validate,
        prompt, provider) return success=False with errors set. Failures
        in optional stages (artifact, memory) produce warnings only and
        leave success=True.

        The result is always appended to the execution history.

        Args:
            context: Structured task description.

        Returns:
            ExecutionResult with success=True on a successful core pipeline.
        """
        start = time.monotonic()
        warnings: List[str] = []

        # Step 1: Validate context and active provider
        validation_errors = self.validate(context)
        if validation_errors:
            result = ExecutionResult(
                success=False,
                provider_response=None,
                generated_artifacts=[],
                memory_entries=[],
                execution_time=round(time.monotonic() - start, 3),
                warnings=[],
                errors=validation_errors,
            )
            self._execution_history.record(context, result)
            return result

        # Step 2: Build PromptContext
        prompt_context = self._build_prompt_context(context)

        # Step 3: PromptBuilder -> PromptResult
        try:
            prompt_result = self._prompt_builder.build(prompt_context)
        except Exception as exc:
            result = ExecutionResult(
                success=False,
                provider_response=None,
                generated_artifacts=[],
                memory_entries=[],
                execution_time=round(time.monotonic() - start, 3),
                warnings=warnings,
                errors=[f"Prompt build failed: {exc}"],
            )
            self._execution_history.record(context, result)
            return result

        # Step 4: Build ProviderRequest
        try:
            provider_request = self._build_provider_request(context, prompt_result)
        except Exception as exc:
            result = ExecutionResult(
                success=False,
                provider_response=None,
                generated_artifacts=[],
                memory_entries=[],
                execution_time=round(time.monotonic() - start, 3),
                warnings=warnings,
                errors=[f"Provider request build failed: {exc}"],
            )
            self._execution_history.record(context, result)
            return result

        # Step 5: AI Provider -> ProviderResponse
        try:
            provider = self._provider_registry.get_active()
            provider_response = provider.generate(provider_request)
        except Exception as exc:
            result = ExecutionResult(
                success=False,
                provider_response=None,
                generated_artifacts=[],
                memory_entries=[],
                execution_time=round(time.monotonic() - start, 3),
                warnings=warnings,
                errors=[f"Provider execution failed: {exc}"],
            )
            self._execution_history.record(context, result)
            return result

        # Step 6: Artifact Engine (optional)
        artifacts: List[Any] = []
        if self._artifact_engine is not None:
            project_id = context.project_id()
            if project_id:
                try:
                    artifact = self._artifact_engine.generate_task_report(project_id)
                    artifacts.append(artifact)
                except Exception as exc:
                    warnings.append(f"Artifact generation skipped: {exc}")
            else:
                warnings.append(
                    "Artifact generation skipped: no project_id on context."
                )

        # Step 7: Memory Engine (optional)
        memory_entries: List[Any] = []
        if self._memory_engine is not None:
            try:
                entry = self._build_memory_entry(context, provider_response)
                stored = self._memory_engine.store(entry)
                memory_entries.append(stored)
            except Exception as exc:
                warnings.append(f"Memory storage skipped: {exc}")

        result = ExecutionResult(
            success=True,
            provider_response=provider_response,
            generated_artifacts=artifacts,
            memory_entries=memory_entries,
            execution_time=round(time.monotonic() - start, 3),
            warnings=warnings,
            errors=[],
        )
        self._execution_history.record(context, result)
        return result

    def validate(self, context: ExecutionContext) -> List[str]:
        """
        Validate an ExecutionContext without executing.

        Checks required context fields AND whether an active provider is
        registered. Returns error strings -- empty list means ready.

        This method never raises.

        Args:
            context: The context to validate.

        Returns:
            List of validation error strings, empty if valid.
        """
        errors: List[str] = []

        if not context.employee_id or not str(context.employee_id).strip():
            errors.append("'employee_id' must not be blank.")
        if not context.employee_role or not str(context.employee_role).strip():
            errors.append("'employee_role' must not be blank.")
        if not context.department or not str(context.department).strip():
            errors.append("'department' must not be blank.")
        if not context.workflow_stage or not str(context.workflow_stage).strip():
            errors.append("'workflow_stage' must not be blank.")
        if not context.task_description().strip():
            errors.append("'task' must provide a non-blank description.")

        if not self._provider_registry.has_active():
            errors.append("No active AI provider registered in the registry.")

        return errors

    def history(self) -> List[ExecutionRecord]:
        """Return all execution records in execution order (oldest first)."""
        return self._execution_history.all()

    def statistics(self) -> Dict[str, Any]:
        """
        Return aggregate metrics over all executions.

        Combines ExecutionHistory.statistics() with executor configuration.

        Returns:
            Dict with all history stat keys plus:
              has_artifact_engine (bool)
              has_memory_engine   (bool)
              provider_count      (int)
              active_provider     (str or None)
              executor_version    (str)
        """
        stats = self._execution_history.statistics()
        stats["has_artifact_engine"] = self._artifact_engine is not None
        stats["has_memory_engine"] = self._memory_engine is not None
        stats["provider_count"] = self._provider_registry.count()
        stats["active_provider"] = self._provider_registry.active_name()
        stats["executor_version"] = _EXECUTOR_VERSION
        return stats

    # ------------------------------------------------------------------
    # Internal pipeline helpers
    # ------------------------------------------------------------------

    def _build_prompt_context(self, context: ExecutionContext) -> PromptContext:
        """Build a PromptContext from an ExecutionContext."""
        project_name = context.project_name() or "Current Project"
        project_description = (
            context.project_description()
            or f"Active project in {context.department} department."
        )
        task_desc = context.task_description() or "Execute assigned task."

        return PromptContext(
            employee_role=context.employee_role,
            department=context.department,
            project_name=project_name,
            project_description=project_description,
            workflow_stage=context.workflow_stage,
            task_description=task_desc,
            constraints=list(context.constraints),
            project_id=context.project_id(),
            seniority=context.seniority,
            context=context.context,
        )

    def _build_provider_request(
        self,
        context: ExecutionContext,
        prompt_result: Any,
    ) -> ProviderRequest:
        """Build a ProviderRequest from ExecutionContext and PromptResult."""
        task_desc = context.task_description() or "Execute assigned task."
        project_desc = context.project_description()
        project_name = context.project_name()

        if project_desc.strip():
            objective = project_desc[:120]
        elif project_name.strip():
            objective = f"Deliver professional output for project: {project_name}"
        else:
            objective = (
                f"Execute {context.workflow_stage} stage task "
                f"for {context.department} department."
            )

        return ProviderRequest(
            role=context.employee_role,
            objective=objective,
            task=task_desc,
            context=(
                f"Department: {context.department}. "
                f"Stage: {context.workflow_stage}."
            ),
            constraints=list(context.constraints),
            expected_output=(
                f"Professional deliverable for the {context.workflow_stage} stage."
            ),
        )

    def _build_memory_entry(
        self,
        context: ExecutionContext,
        provider_response: Any,
    ) -> MemoryEntry:
        """Build a MemoryEntry capturing this execution for company memory."""
        project_id = context.project_id()
        scope = MemoryScope.PROJECT if project_id else MemoryScope.EMPLOYEE

        author = (
            context.employee_id.strip()
            if context.employee_id and context.employee_id.strip()
            else context.employee_role
        )

        task_desc = context.task_description()
        short_desc = task_desc[:80] if task_desc else "task"

        tokens = (
            provider_response.tokens_used
            if provider_response is not None
            else 0
        )

        content = (
            f"Agent {context.employee_role} ({context.employee_id}) "
            f"executed task: {task_desc}. "
            f"Stage: {context.workflow_stage}. "
            f"Provider tokens used: {tokens}."
        )

        role_tag = (
            context.employee_role.lower().replace(" ", "-")
            if context.employee_role
            else "agent"
        )
        stage_tag = context.workflow_stage.lower() if context.workflow_stage else "unknown"
        tags = [t for t in ["agent-execution", role_tag, stage_tag] if t.strip()]

        now = datetime.now(timezone.utc)
        return MemoryEntry(
            id="",
            title=f"Execution: {short_desc}",
            category=MemoryCategory.TASK,
            scope=scope,
            author=author,
            content=content,
            created_at=now,
            updated_at=now,
            project_id=project_id,
            tags=tags,
        )
