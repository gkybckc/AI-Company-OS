"""
Abstract AI provider base class for AI Company OS.

AIProvider is the interface contract every concrete provider must satisfy.
The ProviderRegistry holds one active provider at a time; the rest of AI
Company OS talks only to this interface — never to the concrete class.

This separation enforces the LLM Gateway constraint defined in Architecture
§2.10: "Agents do not call an intelligence provider directly."  Swapping
providers (Mock -> OpenAI -> Anthropic -> local model) is a one-line change
in the ProviderRegistry, not a change in any agent.

Architecture reference: §2.10 LLM Gateway, §3 Layer 2 (Intelligence Layer),
Architectural Constraint 6: "The LLM Gateway is the only authorized path
to external intelligence."
"""

from abc import ABC, abstractmethod

from core.ai.provider_request import ProviderRequest
from core.ai.provider_response import ProviderResponse


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class AIProviderError(Exception):
    """Base class for all AI provider errors."""


class ProviderUnavailableError(AIProviderError):
    """
    Raised when a provider cannot fulfil a request because it is offline,
    misconfigured, or has exhausted its quota.

    The ProviderRegistry catches this and may fall back to an alternate
    provider if one is registered.
    """


class InvalidRequestError(AIProviderError):
    """
    Raised when a ProviderRequest fails provider-level validation.

    This differs from ProviderRequestError (which covers schema
    validation) — InvalidRequestError covers cases where the request
    is structurally valid but semantically rejected by the provider
    (e.g. content policy violation, unsupported role).
    """


class GenerationError(AIProviderError):
    """
    Raised when the provider encounters an error during content generation.

    The error message contains a provider-specific description of what
    went wrong.  Agents should escalate rather than retry silently.
    """


# ---------------------------------------------------------------------------
# AIProvider
# ---------------------------------------------------------------------------

class AIProvider(ABC):
    """
    Abstract base class for all AI providers in AI Company OS.

    Every concrete provider — Mock, OpenAI, Anthropic, local model — must
    subclass this and implement the three abstract methods.  No provider may
    expose additional public methods that agents call directly; all
    interaction flows through this interface.

    Subclassing contract:
        - generate() must always return a ProviderResponse; never raise
          except for the declared exception types.
        - health() must be safe to call at any time without side effects.
        - name() must return a stable, non-empty string identifier.
    """

    @abstractmethod
    def generate(self, request: ProviderRequest) -> ProviderResponse:
        """
        Generate a response for the given request.

        Args:
            request: The structured input from the agent.

        Returns:
            A ProviderResponse containing the generated content and
            observability metadata.

        Raises:
            InvalidRequestError:     If the request is semantically invalid
                                     for this provider.
            ProviderUnavailableError: If the provider cannot be reached or
                                     has exhausted its quota.
            GenerationError:         If content generation fails for any
                                     other reason.
        """

    @abstractmethod
    def health(self) -> bool:
        """
        Return True when the provider is available and ready.

        This method must not raise.  A provider that cannot determine
        its own health status returns False rather than raising an
        exception.

        Returns:
            True if the provider is healthy, False otherwise.
        """

    @abstractmethod
    def name(self) -> str:
        """
        Return a stable, unique identifier for this provider.

        The returned string is used as the registry key and appears in
        every ProviderResponse.provider_name field.  It must be:
          - Non-empty.
          - Consistent across calls (same object always returns same string).
          - Unique within a ProviderRegistry instance.

        Returns:
            A non-empty string identifier (e.g. "MockProvider",
            "OpenAIProvider", "AnthropicProvider").
        """
