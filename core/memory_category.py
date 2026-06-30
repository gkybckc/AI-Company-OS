"""
Memory category taxonomy for AI Company OS.

Defines the complete set of categories that a MemoryEntry can be classified
under. Categories represent what kind of knowledge the entry contains.
The MemoryEngine uses categories to group, filter, and surface relevant
information to agents and the CEO.

Architecture reference: §2.3 Memory Engine, §3 Layer 3 (Infrastructure),
§7 Memory Model, Constitution Chapter 7 (Decision Making).
"""

from enum import Enum


class MemoryCategory(str, Enum):
    """
    Recognized knowledge categories in the Memory Engine.

    Each category maps to a distinct class of organizational knowledge.
    The category is an immutable property of a MemoryEntry — once stored,
    the category does not change. If the nature of a piece of knowledge
    changes, a new entry should be created rather than recategorizing.

    Categories:
        PROJECT    — Project-level artifacts, plans, status summaries,
                     milestones, and outcomes tied to a specific project.
        DECISION   — Formal decisions made by the CEO, Executive Engine,
                     or Department Directors. Recorded per Constitution §7.5.
        DISCUSSION — Outcomes and records from Discussion Engine sessions.
                     Includes the question, contributions, and resolution.
        TASK       — Task-level knowledge: completion notes, blockers,
                     acceptance criteria outcomes, and retrospective findings.
        LESSON     — Lessons learned from project execution — what worked,
                     what failed, and what should be done differently.
        DOCUMENT   — Reference documents, approved specifications, brand
                     guidelines, architecture notes, and technical standards.
        CEO_NOTE   — Private or semi-private notes from the CEO: preferences,
                     standing instructions, and strategic context.
    """

    PROJECT = "PROJECT"
    DECISION = "DECISION"
    DISCUSSION = "DISCUSSION"
    TASK = "TASK"
    LESSON = "LESSON"
    DOCUMENT = "DOCUMENT"
    CEO_NOTE = "CEO_NOTE"

    def __str__(self) -> str:
        return self.value

    def is_governance_related(self) -> bool:
        """Return True if this category carries formal governance weight."""
        return self in {
            MemoryCategory.DECISION,
            MemoryCategory.CEO_NOTE,
        }

    def is_project_scoped(self) -> bool:
        """
        Return True if entries of this category are typically scoped to a
        specific project rather than being company-wide knowledge.
        """
        return self in {
            MemoryCategory.PROJECT,
            MemoryCategory.TASK,
            MemoryCategory.DISCUSSION,
        }

    def is_knowledge_base(self) -> bool:
        """Return True if this category contributes to reusable knowledge."""
        return self in {
            MemoryCategory.LESSON,
            MemoryCategory.DOCUMENT,
        }
