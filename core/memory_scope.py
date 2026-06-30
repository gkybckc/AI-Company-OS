"""
Memory scope taxonomy for AI Company OS.

Defines the access and visibility scopes that govern which agents and
components can read or write a given MemoryEntry. Scope is an access-control
declaration — it expresses *who* the entry is intended for, not just where
it lives.

Architecture reference: §2.3 Memory Engine, §3 Layer 3 (Infrastructure),
§7 Memory Model (§7.1–7.5), §14 Security Boundaries,
Constitution Chapter 14 (Security Principles).
"""

from enum import Enum


class MemoryScope(str, Enum):
    """
    Recognized access scopes for MemoryEntry records.

    Scopes enforce the access-control hierarchy described in Architecture §7.
    Higher-privilege scopes are accessible to fewer components. Scope
    assignment is made at store time and is part of the entry's identity.

    Scopes:
        GLOBAL       — Visible to all agents, departments, and the CEO.
                       Used for company-wide standards, approved technology
                       decisions, and cross-departmental reference documents.
        PROJECT      — Visible to all agents assigned to the specific project
                       identified by project_id. Used for project memory
                       (Architecture §7.5).
        DEPARTMENT   — Visible to all agents within a department and its
                       Director. Used for department-level standards,
                       shared context, and intra-department decisions.
        EMPLOYEE     — Visible only to the specific agent identified by the
                       entry's author field and its supervising Director.
                       Corresponds to long-term agent memory (Architecture §7.2).
        CEO_PRIVATE  — Visible only to the CEO Interface and the Executive
                       Engine. Corresponds to CEO Memory (Architecture §7.4).
                       Write-protected to all components except the CEO Interface.
    """

    GLOBAL = "GLOBAL"
    PROJECT = "PROJECT"
    DEPARTMENT = "DEPARTMENT"
    EMPLOYEE = "EMPLOYEE"
    CEO_PRIVATE = "CEO_PRIVATE"

    def __str__(self) -> str:
        return self.value

    def is_private(self) -> bool:
        """
        Return True if this scope restricts access to a single agent or
        the CEO — i.e., it is not shared across a team or department.
        """
        return self in {MemoryScope.EMPLOYEE, MemoryScope.CEO_PRIVATE}

    def is_accessible_to_all(self) -> bool:
        """Return True if this scope allows any agent in the system to read."""
        return self == MemoryScope.GLOBAL

    def is_project_scoped(self) -> bool:
        """Return True if access is bounded to a specific project."""
        return self == MemoryScope.PROJECT

    def requires_project_id(self) -> bool:
        """
        Return True if entries with this scope must carry a non-None project_id.

        PROJECT scope entries without a project_id cannot be correctly routed
        to the appropriate project memory partition.
        """
        return self == MemoryScope.PROJECT
