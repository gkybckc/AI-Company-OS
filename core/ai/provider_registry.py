"""
Provider registry for AI Company OS.

ProviderRegistry manages the set of registered AI providers and maintains
a pointer to the currently active provider.  All agent-layer code that
needs AI capabilities must go through the registry -- never calling a
provider directly.

Responsibilities
----------------
- Register and deregister provider instances by name.
- Track one active provider at a time.
- Surface health and metadata of all registered providers.
- Guard against duplicate registration and missing providers.

Architecture reference: §2.10 LLM Gateway, §3 Layer 2 (Intelligence Layer).
"""

from typing import Any, Dict, List, Optional

from core.ai.provider import AIProvider


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ProviderRegistryError(Exception):
    """Base exception for all ProviderRegistry errors."""


class ProviderNotFoundError(ProviderRegistryError):
    """Raised when a requested provider is not in the registry."""


class DuplicateProviderError(ProviderRegistryError):
    """Raised when a provider with the same name is registered twice."""


class NoActiveProviderError(ProviderRegistryError):
    """Raised when an operation requires an active provider but none is set."""


# ---------------------------------------------------------------------------
# ProviderRegistry
# ---------------------------------------------------------------------------

class ProviderRegistry:
    """
    Central registry for AI providers.

    Usage pattern:
        registry = ProviderRegistry()
        registry.register(MockProvider())
        registry.set_active("MockProvider")
        provider = registry.get_active()
        response = provider.generate(request)

    The registry does not own the providers in the sense of lifecycle
    management; it only holds references.  Callers are responsible for
    constructing and configuring providers before registering them.
    """

    def __init__(self) -> None:
        self._providers: Dict[str, AIProvider] = {}
        self._active_name: Optional[str] = None

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, provider: AIProvider) -> None:
        """
        Add a provider to the registry.

        If no active provider is set, the first registered provider
        becomes the active provider automatically.

        Args:
            provider: A concrete AIProvider implementation.

        Raises:
            DuplicateProviderError: If a provider with the same name
                                    is already registered.
            ValueError:             If provider is None.
        """
        if provider is None:
            raise ValueError("provider must not be None.")
        name = provider.name()
        if name in self._providers:
            raise DuplicateProviderError(
                f"Provider '{name}' is already registered. "
                "Remove it first before re-registering."
            )
        self._providers[name] = provider
        if self._active_name is None:
            self._active_name = name

    def remove(self, name: str) -> None:
        """
        Remove a provider from the registry.

        If the removed provider was the active provider, the active
        provider is cleared (set to None).

        Args:
            name: The provider name to remove.

        Raises:
            ProviderNotFoundError: If no provider with that name exists.
        """
        if name not in self._providers:
            raise ProviderNotFoundError(
                f"No provider named '{name}' is registered."
            )
        del self._providers[name]
        if self._active_name == name:
            self._active_name = None

    # ------------------------------------------------------------------
    # Active provider
    # ------------------------------------------------------------------

    def set_active(self, name: str) -> None:
        """
        Designate a registered provider as the active provider.

        Args:
            name: The name of the provider to activate.

        Raises:
            ProviderNotFoundError: If no provider with that name exists.
        """
        if name not in self._providers:
            raise ProviderNotFoundError(
                f"Cannot activate '{name}': provider is not registered."
            )
        self._active_name = name

    def get_active(self) -> AIProvider:
        """
        Return the currently active provider.

        Returns:
            The active AIProvider instance.

        Raises:
            NoActiveProviderError: If no active provider is set.
        """
        if self._active_name is None or self._active_name not in self._providers:
            raise NoActiveProviderError(
                "No active provider is set. "
                "Call register() or set_active() first."
            )
        return self._providers[self._active_name]

    def active_name(self) -> Optional[str]:
        """
        Return the name of the active provider, or None if not set.

        Returns:
            The active provider name string, or None.
        """
        return self._active_name

    def has_active(self) -> bool:
        """
        Return True when an active provider is set and present.

        Returns:
            True if the active provider is set and registered.
        """
        return (
            self._active_name is not None
            and self._active_name in self._providers
        )

    # ------------------------------------------------------------------
    # Provider lookup
    # ------------------------------------------------------------------

    def get(self, name: str) -> AIProvider:
        """
        Return a registered provider by name.

        Args:
            name: The provider name.

        Returns:
            The AIProvider instance.

        Raises:
            ProviderNotFoundError: If no provider with that name exists.
        """
        if name not in self._providers:
            raise ProviderNotFoundError(
                f"No provider named '{name}' is registered."
            )
        return self._providers[name]

    def has(self, name: str) -> bool:
        """
        Return True if a provider with the given name is registered.

        Args:
            name: The provider name to check.

        Returns:
            True if registered, False otherwise.
        """
        return name in self._providers

    def list_all(self) -> List[str]:
        """
        Return the names of all registered providers in insertion order.

        Returns:
            A list of provider name strings.
        """
        return list(self._providers.keys())

    def count(self) -> int:
        """Return the number of registered providers."""
        return len(self._providers)

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health_check(self) -> Dict[str, bool]:
        """
        Run health() on all registered providers.

        Returns:
            A dict mapping provider name to its health() result.
        """
        return {name: p.health() for name, p in self._providers.items()}

    def active_is_healthy(self) -> bool:
        """
        Return the health status of the active provider.

        Returns False (rather than raising) if no active provider is set.

        Returns:
            True if the active provider reports healthy, False otherwise.
        """
        if not self.has_active():
            return False
        return self.get_active().health()

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def statistics(self) -> Dict[str, Any]:
        """
        Return aggregate metadata about the registry.

        Returns:
            A dictionary with keys:
              total_providers (int)
              active_provider (str or None)
              provider_names  (list of str)
              healthy         (dict of name -> bool)
        """
        return {
            "total_providers": self.count(),
            "active_provider": self._active_name,
            "provider_names": self.list_all(),
            "healthy": self.health_check(),
        }
