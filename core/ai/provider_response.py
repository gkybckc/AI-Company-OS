"""
Provider response model for AI Company OS.

A ProviderResponse is the standardised output contract between the AI Provider
Abstraction Layer and the Agent Layer.  Every provider implementation returns
exactly this object — agents never see raw model output, tokens, or any other
provider-specific artefact.

Architecture reference: §2.10 LLM Gateway, §3 Layer 2 (Intelligence Layer).
"""

from dataclasses import dataclass, field
from typing import Any, Dict


# ---------------------------------------------------------------------------
# ProviderResponse
# ---------------------------------------------------------------------------

@dataclass
class ProviderResponse:
    """
    Standardised output returned by any AI provider.

    Agents consume this object directly without knowing which provider
    produced it.  The content field carries the substantive output; the
    remaining fields provide observability metadata.

    Attributes:
        content:        The generated text produced by the provider.
                        Always a non-empty string for successful responses.
        tokens_used:    Estimated or exact token count consumed.
                        Providers that cannot measure tokens report 0.
        provider_name:  Name of the provider that generated this response,
                        as returned by AIProvider.name().
        execution_time: Wall-clock time in seconds that the provider spent
                        generating the response.
        metadata:       Provider-specific supplementary data (model name,
                        temperature, flags, etc.).  Agents must treat this
                        as opaque; the schema varies by provider.
                        Defaults to an empty dict.
    """

    content: str
    tokens_used: int
    provider_name: str
    execution_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Content metrics
    # ------------------------------------------------------------------

    def word_count(self) -> int:
        """Return the number of whitespace-delimited tokens in the content."""
        return len(self.content.split())

    def line_count(self) -> int:
        """Return the number of lines in the content."""
        return len(self.content.splitlines())

    def is_empty(self) -> bool:
        """Return True when the content is blank or whitespace-only."""
        return not self.content or not self.content.strip()

    def char_count(self) -> int:
        """Return the number of characters in the content."""
        return len(self.content)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain-dict representation of this response."""
        return {
            "content": self.content,
            "tokens_used": self.tokens_used,
            "provider_name": self.provider_name,
            "execution_time": self.execution_time,
            "metadata": dict(self.metadata),
            "word_count": self.word_count(),
            "line_count": self.line_count(),
        }

    def summary(self) -> str:
        """Return a one-line diagnostic summary."""
        return (
            f"[{self.provider_name}] "
            f"tokens={self.tokens_used} "
            f"words={self.word_count()} "
            f"time={self.execution_time:.3f}s"
        )
