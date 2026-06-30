"""
Memory entry model for AI Company OS.

A MemoryEntry is the atomic unit of knowledge in the Memory Engine. It
carries a strongly typed classification (category, scope), attribution
(author, project), full text content, and a searchable tag set.

MemoryEntries are mutable — the Memory Engine can update the content, title,
and tags of an existing entry via update(). Every mutation is recorded in
the entry's revision history so the full lineage of a piece of knowledge
is always recoverable. The created_at timestamp is immutable; updated_at
advances with each mutation.

Architecture reference: §2.3 Memory Engine, §3 Layer 3 (Infrastructure),
§7 Memory Model, Constitution §7.5 (decisions are recorded), §16.6
(completion recorded in company memory).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.memory_category import MemoryCategory
from core.memory_scope import MemoryScope


@dataclass
class MemoryEntryRevision:
    """
    A point-in-time snapshot of the mutable fields of a MemoryEntry.

    Stored in MemoryEntry.history when update() is called on the entry.
    The revision captures the *old* values before the update is applied,
    so the full history of what was written and when is always available.

    Attributes:
        version:    The version number that was active before this update.
        title:      The title as it existed in that version.
        content:    The full text content as it existed in that version.
        tags:       The tag list as it existed in that version.
        recorded_at: UTC timestamp of when this revision was captured.
        changed_by: Identifier of who triggered the update. Empty string
                    if not provided.
    """

    version: int
    title: str
    content: str
    tags: List[str]
    recorded_at: datetime
    changed_by: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain-dict representation of this revision."""
        return {
            "version": self.version,
            "title": self.title,
            "content": self.content[:120] + ("..." if len(self.content) > 120 else ""),
            "tags": list(self.tags),
            "recorded_at": self.recorded_at.isoformat(),
            "changed_by": self.changed_by,
        }


@dataclass
class MemoryEntry:
    """
    Atomic unit of knowledge stored in the Memory Engine.

    Created via MemoryEngine.store(). Updated via MemoryEngine.update().
    Deleted via MemoryEngine.delete(). The engine is the authoritative
    owner — callers must not mutate entries directly after storage.

    Fields mandated by the specification:
        id          — Unique identifier (UUID string). Assigned by the caller
                      or auto-generated if empty.
        title       — Short, human-readable title. Must be non-empty.
        category    — Knowledge category (MemoryCategory). Immutable after store.
        scope       — Access scope (MemoryScope). Immutable after store.
        project_id  — Optional project identifier. Required when scope is PROJECT.
        author      — Identifier of the agent or human that created this entry.
                      Must be non-empty.
        content     — Full text of the knowledge. Must be non-empty.
        tags        — List of keyword tags for search and filtering. May be empty.
        created_at  — UTC timestamp of when the entry was first stored.
        updated_at  — UTC timestamp of the most recent update. Equal to
                      created_at for entries that have never been updated.

    Fields added to fulfil the history-preservation rule:
        version     — Monotonically increasing counter. Starts at 1; incremented
                      by each update(). Read-only after the engine manages it.
        history     — Ordered list of MemoryEntryRevision records capturing
                      every previous state of the entry. Empty until the first
                      update. Oldest revision first.
    """

    id: str
    title: str
    category: MemoryCategory
    scope: MemoryScope
    author: str
    content: str
    created_at: datetime
    updated_at: datetime
    project_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    version: int = 1
    history: List[MemoryEntryRevision] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def has_tag(self, tag: str) -> bool:
        """
        Return True if this entry carries the exact tag (case-insensitive).

        Args:
            tag: The tag string to search for.

        Returns:
            True if the tag is present (case-insensitive comparison).
        """
        tag_lower = tag.lower()
        return any(t.lower() == tag_lower for t in self.tags)

    def has_any_tag(self, tags: List[str]) -> bool:
        """
        Return True if this entry carries at least one tag from the list.

        Args:
            tags: List of candidate tags.

        Returns:
            True if any tag in the list matches (case-insensitive).
        """
        return any(self.has_tag(t) for t in tags)

    def has_all_tags(self, tags: List[str]) -> bool:
        """
        Return True if this entry carries every tag in the list.

        Args:
            tags: List of tags that must all be present.

        Returns:
            True if every tag in the list is present (case-insensitive).
        """
        return all(self.has_tag(t) for t in tags)

    def contains_text(self, query: str) -> bool:
        """
        Return True if the query string appears in the title or content.

        The search is case-insensitive and checks for substring presence.

        Args:
            query: The text to search for.

        Returns:
            True if the query is found anywhere in title or content.
        """
        q = query.lower()
        return q in self.title.lower() or q in self.content.lower()

    def is_project_entry(self) -> bool:
        """Return True if this entry is associated with a specific project."""
        return self.project_id is not None

    def revision_count(self) -> int:
        """Return the number of past revisions stored in history."""
        return len(self.history)

    def has_been_updated(self) -> bool:
        """Return True if the entry has been updated at least once."""
        return self.version > 1

    def latest_revision(self) -> Optional[MemoryEntryRevision]:
        """Return the most recent revision, or None if never updated."""
        return self.history[-1] if self.history else None

    def summary(self) -> Dict[str, Any]:
        """
        Return a compact summary dict suitable for listings and status reports.

        Returns:
            Dict with keys: id, title, category, scope, author, project_id,
            version, tags, created_at, updated_at, revision_count.
        """
        return {
            "id": self.id,
            "title": self.title,
            "category": str(self.category),
            "scope": str(self.scope),
            "author": self.author,
            "project_id": self.project_id,
            "version": self.version,
            "tags": list(self.tags),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "revision_count": self.revision_count(),
        }
