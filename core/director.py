"""
Director model for AI Company OS.

A Director is the coordination authority within a single department.
They are the single point of contact between the Executive Engine and
the specialist agents below them. Every department must have at most
one Director; a department without a Director cannot operate.

The Director does not produce work directly. They distribute tasks to
specialist agents, monitor execution, escalate blockers, and report
department status upward. Their authority is bounded to their department.

Architecture reference: §2.2 Agent Runtime, §3 Layer 4 (Agent Layer),
§6 Communication Model, Constitution Chapter 5.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List

from core.department_status import DirectorStatus
from core.department_type import DepartmentType


class DirectorNotFoundError(Exception):
    """Raised when a director cannot be resolved by name or ID."""


class DirectorAlreadyAssignedError(Exception):
    """Raised when a department already has a director and a second is added."""


@dataclass
class Director:
    """
    Coordination authority for a single department.

    A Director is a mutable record because their status and the set of
    agents they manage change continuously as the company operates. The
    id, name, department, and assigned_at fields are set at construction
    and are not expected to change under normal operation.

    The Executive Engine communicates with the department through the
    Director. The Director translates Executive instructions into specific
    task assignments for the specialist agents in their team.

    Attributes:
        id: Unique identifier (UUID string).
        name: Human-readable name of this director (e.g., "Backend Director").
        department: The department type this director governs. A director
            governs exactly one department at a time.
        status: Current operational status of this director.
        responsibilities: Ordered list of this director's core duties.
            Populated at assignment time; defines the domain of authority.
        managed_agents: Ordered list of agent IDs currently reporting to
            this director. Agents are added as the department staffs up and
            removed when they are terminated or reassigned.
        assigned_at: UTC timestamp of when this director was assigned to
            their department.
    """

    id: str
    name: str
    department: DepartmentType
    status: DirectorStatus
    responsibilities: List[str]
    managed_agents: List[str]
    assigned_at: datetime

    def add_agent(self, agent_id: str) -> None:
        """
        Add an agent to this director's managed set.

        Does nothing if the agent is already tracked, preventing duplicates
        without raising an error (idempotent for repeat registrations).

        Args:
            agent_id: Identifier of the agent to add.
        """
        if agent_id not in self.managed_agents:
            self.managed_agents.append(agent_id)

    def remove_agent(self, agent_id: str) -> None:
        """
        Remove an agent from this director's managed set.

        Does nothing if the agent is not currently tracked, making the
        operation safe to call even after a previous removal.

        Args:
            agent_id: Identifier of the agent to remove.
        """
        if agent_id in self.managed_agents:
            self.managed_agents.remove(agent_id)

    def agent_count(self) -> int:
        """
        Return the number of agents currently managed by this director.

        Returns:
            Integer count. Zero if no agents have been assigned.
        """
        return len(self.managed_agents)
