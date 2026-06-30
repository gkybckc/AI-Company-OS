"""
Component registry for AI Company OS.

Tracks every component registered with the CompanyRuntime. The registry
is the authoritative directory of what is currently operating inside the
runtime: each entry carries a unique name, a type label, an operational
status, a registration timestamp, and optional metadata.

The registry is a directory, not a controller. It does not manage component
lifecycle beyond recording the status callers report. Lifecycle decisions
belong to the CompanyRuntime.

Architecture reference: §2 Core Components, §15 Extensibility.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class ComponentStatus(str, Enum):
    """
    Operational status of a registered component.

    REGISTERED is the initial state when a component enters the registry.
    The CompanyRuntime or the component itself may advance the status to
    ACTIVE once the component is fully operational, or to INACTIVE / ERROR
    to signal degraded state.
    """

    REGISTERED = "REGISTERED"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ERROR = "ERROR"

    def __str__(self) -> str:
        return self.value


class ComponentAlreadyRegisteredError(Exception):
    """Raised when attempting to register a name already present in the registry."""


class ComponentNotFoundError(Exception):
    """Raised when a name cannot be resolved in the registry."""


@dataclass
class ComponentRecord:
    """
    Registry entry for a single runtime component.

    Mutable because the runtime may update a component's status over its
    lifetime. The name and registered_at fields are set at registration
    and are not changed thereafter.

    Attributes:
        name: Unique component identifier within the registry.
        component_type: Human-readable type label (e.g. "EventBus").
        status: Current operational status.
        registered_at: UTC timestamp of registration.
        metadata: Arbitrary key-value data provided at registration time.
            Always a dict; never None.
    """

    name: str
    component_type: str
    status: ComponentStatus
    registered_at: datetime
    metadata: Dict[str, Any]


class RuntimeRegistry:
    """
    Authoritative directory of all components registered with the runtime.

    Provides O(1) lookup by name and ordered listing in registration
    sequence. Component records are live mutable objects; status updates
    propagate immediately.

    Attributes:
        _components: Ordered mapping from component name to ComponentRecord.
    """

    def __init__(self) -> None:
        self._components: Dict[str, ComponentRecord] = {}

    def register(
        self,
        name: str,
        component_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ComponentRecord:
        """
        Add a component to the registry.

        The component enters REGISTERED status immediately. Its registration
        timestamp is set to the current UTC time.

        Args:
            name: Unique name for this component. Must not already exist.
            component_type: Human-readable type label.
            metadata: Optional key-value context stored alongside the record.

        Returns:
            The newly created ComponentRecord.

        Raises:
            ComponentAlreadyRegisteredError: If name is already in the registry.
        """
        if name in self._components:
            raise ComponentAlreadyRegisteredError(
                f"Component '{name}' is already registered. "
                "Deregister it before registering again."
            )
        record = ComponentRecord(
            name=name,
            component_type=component_type,
            status=ComponentStatus.REGISTERED,
            registered_at=datetime.now(timezone.utc),
            metadata=metadata if metadata is not None else {},
        )
        self._components[name] = record
        return record

    def deregister(self, name: str) -> ComponentRecord:
        """
        Remove a component from the registry.

        Args:
            name: Name of the component to remove.

        Returns:
            The ComponentRecord that was removed.

        Raises:
            ComponentNotFoundError: If name is not in the registry.
        """
        record = self._resolve(name)
        del self._components[name]
        return record

    def get(self, name: str) -> ComponentRecord:
        """
        Retrieve a component record by name.

        Args:
            name: The component name to look up.

        Returns:
            The matching ComponentRecord (live reference).

        Raises:
            ComponentNotFoundError: If name is not in the registry.
        """
        return self._resolve(name)

    def list_all(self) -> List[ComponentRecord]:
        """
        Return all registered components in registration order.

        Returns:
            A new list of ComponentRecord instances. Mutating the returned
            list does not affect the registry; individual records are live
            references and their fields remain mutable.
        """
        return list(self._components.values())

    def update_status(self, name: str, status: ComponentStatus) -> ComponentRecord:
        """
        Update the operational status of a registered component.

        Args:
            name: Name of the component to update.
            status: New status value.

        Returns:
            The updated ComponentRecord.

        Raises:
            ComponentNotFoundError: If name is not in the registry.
        """
        record = self._resolve(name)
        record.status = status
        return record

    def count(self) -> int:
        """
        Return the number of components currently in the registry.

        Returns:
            Integer count. Zero when the registry is empty.
        """
        return len(self._components)

    def is_registered(self, name: str) -> bool:
        """
        Check whether a component name is present in the registry.

        Args:
            name: The component name to check.

        Returns:
            True if registered, False otherwise.
        """
        return name in self._components

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve(self, name: str) -> ComponentRecord:
        """
        Return the record for name or raise ComponentNotFoundError.

        Args:
            name: The component name to look up.

        Returns:
            The matching ComponentRecord.

        Raises:
            ComponentNotFoundError: If name is not present.
        """
        record = self._components.get(name)
        if record is None:
            raise ComponentNotFoundError(
                f"No component registered under the name '{name}'."
            )
        return record
