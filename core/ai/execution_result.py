"""
Execution Result for AI Company OS Agent Executor.

The ExecutionResult is the complete output of a single AgentExecutor.execute()
call. It carries the provider's response, any artifacts generated, any memory
entries stored, timing information, and diagnostic warnings and errors.

A successful result has success=True. Partial success (e.g. provider responded
but artifact generation failed) is represented as success=True with non-empty
warnings. A failed result has success=False with non-empty errors.

Architecture reference: §2.10 LLM Gateway, §3 Layer 2 (Intelligence Layer).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.ai.provider_response import ProviderResponse


# ---------------------------------------------------------------------------
# ExecutionResult
# ---------------------------------------------------------------------------

@dataclass
class ExecutionResult:
    """
    Complete output of a single agent task execution.

    Fields:
        success              True if the core pipeline (validate -> prompt ->
                             provider) completed without error.
        provider_response    The ProviderResponse from the AI provider, or None
                             if the pipeline failed before reaching the provider.
        generated_artifacts  Artifacts produced by the ArtifactEngine. Empty if
                             no ArtifactEngine was attached or generation failed.
        memory_entries       MemoryEntry records stored by the MemoryEngine.
                             Empty if no MemoryEngine was attached.
        execution_time       Wall-clock seconds consumed by execute().
        warnings             Non-fatal issues from optional pipeline stages.
        errors               Fatal errors that caused success=False.
    """

    success: bool
    provider_response: Optional[ProviderResponse]
    generated_artifacts: List[Any]
    memory_entries: List[Any]
    execution_time: float
    warnings: List[str]
    errors: List[str]

    # ------------------------------------------------------------------
    # Presence helpers
    # ------------------------------------------------------------------

    def has_artifacts(self) -> bool:
        """Return True if at least one artifact was generated."""
        return bool(self.generated_artifacts)

    def has_memory_entries(self) -> bool:
        """Return True if at least one memory entry was stored."""
        return bool(self.memory_entries)

    def has_warnings(self) -> bool:
        """Return True if at least one warning was recorded."""
        return bool(self.warnings)

    def has_errors(self) -> bool:
        """Return True if at least one error was recorded."""
        return bool(self.errors)

    def has_response(self) -> bool:
        """Return True if a provider response is available."""
        return self.provider_response is not None

    # ------------------------------------------------------------------
    # Count helpers
    # ------------------------------------------------------------------

    def artifact_count(self) -> int:
        """Return the number of generated artifacts."""
        return len(self.generated_artifacts)

    def memory_count(self) -> int:
        """Return the number of memory entries stored."""
        return len(self.memory_entries)

    def warning_count(self) -> int:
        """Return the number of warnings recorded."""
        return len(self.warnings)

    def error_count(self) -> int:
        """Return the number of errors recorded."""
        return len(self.errors)

    # ------------------------------------------------------------------
    # Response helpers
    # ------------------------------------------------------------------

    def response_content(self) -> str:
        """Return provider response content, or empty string if absent."""
        if self.provider_response is None:
            return ""
        return self.provider_response.content

    def response_token_count(self) -> int:
        """Return token count from the provider response, or 0 if absent."""
        if self.provider_response is None:
            return 0
        return self.provider_response.tokens_used

    def response_provider_name(self) -> str:
        """Return the provider name from the response, or empty string."""
        if self.provider_response is None:
            return ""
        return self.provider_response.provider_name

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain-dict representation of this result."""
        return {
            "success": self.success,
            "execution_time": self.execution_time,
            "has_response": self.has_response(),
            "response_tokens": self.response_token_count(),
            "response_provider": self.response_provider_name(),
            "artifact_count": self.artifact_count(),
            "memory_count": self.memory_count(),
            "warning_count": self.warning_count(),
            "error_count": self.error_count(),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    def summary(self) -> str:
        """Return a one-line human-readable summary."""
        status = "OK" if self.success else "FAILED"
        tokens = self.response_token_count()
        arts = self.artifact_count()
        mems = self.memory_count()
        t = self.execution_time
        warns = self.warning_count()
        return (
            f"[{status}] time={t}s tokens={tokens} "
            f"artifacts={arts} memory={mems} warnings={warns}"
        )
