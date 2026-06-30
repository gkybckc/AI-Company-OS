"""
Runtime event model for AI Company OS.

Defines the event categories the CompanyRuntime emits across its lifecycle
and the immutable RuntimeEvent record that represents each emission. All
events are appended to the runtime's internal log and are accessible via
CompanyRuntime.get_events().

These events describe the runtime infrastructure itself — not the business
operations running on top of it. Business-level event categories are defined
separately in Architecture §10.

Architecture reference: §2.8 Event Bus, §10 Event Flow.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict


class RuntimeEventType(str, Enum):
    """
    Categories of events emitted by the CompanyRuntime.

    RUNTIME_STARTED and RUNTIME_STOPPED bracket each operational session.
    COMPONENT_REGISTERED / COMPONENT_DEREGISTERED track the component
    registry changes. HEALTH_CHECK is recorded each time get_health() is
    called, providing an observable audit trail of health inspections.
    RUNTIME_ERROR is reserved for failure records.
    """

    RUNTIME_STARTED = "RUNTIME_STARTED"
    RUNTIME_STOPPED = "RUNTIME_STOPPED"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    COMPONENT_REGISTERED = "COMPONENT_REGISTERED"
    COMPONENT_DEREGISTERED = "COMPONENT_DEREGISTERED"
    HEALTH_CHECK = "HEALTH_CHECK"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class RuntimeEvent:
    """
    Immutable record of a single runtime lifecycle event.

    Events are append-only. Once created and added to the log they cannot
    be modified or removed. This makes the event log the authoritative,
    tamper-evident history of everything that has happened in the runtime,
    consistent with the observability principle in Architecture §10.

    Attributes:
        id: Unique identifier (UUID string).
        event_type: Category of this event.
        timestamp: UTC timestamp of the moment this event was created.
        payload: Arbitrary key-value context for the event. Always a dict
            (never None); may be empty if no context is applicable.
    """

    id: str
    event_type: RuntimeEventType
    timestamp: datetime
    payload: Dict[str, Any]
