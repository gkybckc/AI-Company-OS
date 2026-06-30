"""
Memory Engine for AI Company OS.

The MemoryEngine is the organizational memory of AI Company OS. It stores,
updates, retrieves, and deletes structured MemoryEntry records — the
company's accumulated decisions, project knowledge, discussion outcomes,
lessons learned, and reusable organizational knowledge.

Key design constraints (enforced by this engine):
  - No AI. No embeddings. No vector operations.
  - No networking. No external services.
  - No external libraries.
  - No persistence. All state is held in memory for the process lifetime.
  - All text search is plain substring (case-insensitive).
  - Every update preserves the previous state in the entry's revision history.

The engine is the single authority on what has been stored. All reads and
writes flow through this interface. Callers must not mutate MemoryEntry
objects directly after storing them — use update() to make changes so the
history is preserved correctly.

Architecture reference: §2.3 Memory Engine, §3 Layer 3 (Infrastructure),
§7 Memory Model (§7.1–7.5), Constitution §7.5, §16.6.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from core.memory_category import MemoryCategory
from core.memory_entry import MemoryEntry, MemoryEntryRevision
from core.memory_query import MemoryQuery
from core.memory_scope import MemoryScope


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class MemoryEngineError(Exception):
    """Base class for all Memory Engine errors."""


class MemoryEntryNotFoundError(MemoryEngineError):
    """
    Raised when an operation references an entry ID that does not exist.

    This exception is raised by find_by_id(), update(), and delete() when
    the provided entry_id is not present in the engine's store.
    """


class DuplicateEntryError(MemoryEngineError):
    """
    Raised when store() receives an entry whose ID already exists.

    To update an existing entry, use update() instead of store().
    """


class InvalidMemoryEntryError(MemoryEngineError):
    """
    Raised when a MemoryEntry fails validation in store() or update().

    This exception is raised when required fields are empty (id, title,
    author, content), when tags contain empty strings, or when a PROJECT-
    scoped entry is missing a project_id.
    """


# ---------------------------------------------------------------------------
# MemoryEngine
# ---------------------------------------------------------------------------

class MemoryEngine:
    """
    Central storage and retrieval authority for all organizational knowledge.

    Stores MemoryEntry records keyed by their ID. Provides typed search and
    filter operations via purpose-specific methods as well as a general-
    purpose query() method that accepts a MemoryQuery specification.

    The engine does NOT call any external system, database, or AI service.
    All state is in-process and lives only for the lifetime of the engine
    instance. No state survives process termination — this is intentional
    for Sprint 11. Persistence is a future Storage Layer concern.

    Usage pattern:
        engine = MemoryEngine()
        entry = MemoryEntry(
            id=str(uuid4()),
            title="Architecture Decision 001",
            category=MemoryCategory.DECISION,
            scope=MemoryScope.GLOBAL,
            author="CEO",
            content="Use PostgreSQL for the primary relational store.",
            tags=["database", "architecture"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        engine.store(entry)
        results = engine.find_by_category(MemoryCategory.DECISION)
        engine.update(entry.id, content="Updated rationale...", changed_by="CEO")
        stats = engine.statistics()

    Attributes:
        _entries: Internal dict mapping entry.id -> MemoryEntry.
    """

    def __init__(self) -> None:
        self._entries: Dict[str, MemoryEntry] = {}

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def store(self, entry: MemoryEntry) -> MemoryEntry:
        """
        Store a new MemoryEntry in the engine.

        Validates the entry before storing. If the entry's ID is an empty
        string, a new UUID is auto-generated and written to entry.id.

        Args:
            entry: The MemoryEntry to store. Must pass validation:
                - id: may be empty (auto-generated) but must not be whitespace-only
                - title: must be non-empty after stripping
                - author: must be non-empty after stripping
                - content: must be non-empty after stripping
                - tags: no tag may be an empty string
                - project_id: required when scope is PROJECT

        Returns:
            The stored MemoryEntry (the same object, possibly with id set).

        Raises:
            DuplicateEntryError: If an entry with the same non-empty ID
                already exists in the engine.
            InvalidMemoryEntryError: If any validation rule is violated.
        """
        self._validate_entry(entry)

        if not entry.id:
            entry.id = str(uuid4())

        if entry.id in self._entries:
            raise DuplicateEntryError(
                f"An entry with id '{entry.id}' already exists. "
                "Use update() to modify an existing entry."
            )

        self._entries[entry.id] = entry
        return entry

    def update(
        self,
        entry_id: str,
        *,
        content: Optional[str] = None,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
        changed_by: str = "",
    ) -> MemoryEntry:
        """
        Update the mutable fields of an existing MemoryEntry.

        Before applying any change, the current state of the entry is
        captured as a MemoryEntryRevision and appended to entry.history.
        This preserves the complete lineage of the entry.

        At least one of content, title, or tags must be provided. Calling
        update() with all three as None raises InvalidMemoryEntryError.

        After the update:
          - entry.version is incremented by 1.
          - entry.updated_at is set to the current UTC time.
          - entry.history gains one new MemoryEntryRevision.

        Args:
            entry_id: ID of the entry to update.
            content:  New content string. If None, content is unchanged.
                      Must be non-empty if provided.
            title:    New title string. If None, title is unchanged.
                      Must be non-empty if provided.
            tags:     New tag list. If None, tags are unchanged. An empty
                      list is accepted (it clears all tags). No tag in the
                      list may be an empty string.
            changed_by: Identifier of who triggered the update. Recorded
                      in the revision. Defaults to empty string.

        Returns:
            The updated MemoryEntry.

        Raises:
            MemoryEntryNotFoundError: If entry_id does not exist.
            InvalidMemoryEntryError: If all three update fields are None,
                or if content/title is empty, or tags contain empty strings.
        """
        entry = self._require_entry(entry_id)

        if content is None and title is None and tags is None:
            raise InvalidMemoryEntryError(
                "At least one of 'content', 'title', or 'tags' must be provided "
                "to update()."
            )

        if content is not None and not content.strip():
            raise InvalidMemoryEntryError("content must not be empty.")

        if title is not None and not title.strip():
            raise InvalidMemoryEntryError("title must not be empty.")

        if tags is not None:
            for t in tags:
                if not t:
                    raise InvalidMemoryEntryError(
                        "Tags must not contain empty strings."
                    )

        now = datetime.now(timezone.utc)

        revision = MemoryEntryRevision(
            version=entry.version,
            title=entry.title,
            content=entry.content,
            tags=list(entry.tags),
            recorded_at=now,
            changed_by=changed_by,
        )
        entry.history.append(revision)

        if content is not None:
            entry.content = content
        if title is not None:
            entry.title = title
        if tags is not None:
            entry.tags = list(tags)

        entry.version += 1
        entry.updated_at = now

        return entry

    def delete(self, entry_id: str) -> MemoryEntry:
        """
        Remove a MemoryEntry from the engine and return it.

        After deletion, the entry is no longer accessible through any
        engine method. The returned object is the last known state of
        the entry including its full revision history.

        Args:
            entry_id: ID of the entry to delete.

        Returns:
            The deleted MemoryEntry.

        Raises:
            MemoryEntryNotFoundError: If entry_id does not exist.
        """
        entry = self._require_entry(entry_id)
        del self._entries[entry_id]
        return entry

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def find_by_id(self, entry_id: str) -> MemoryEntry:
        """
        Return the entry with the given ID.

        Args:
            entry_id: ID of the entry to retrieve.

        Returns:
            The MemoryEntry with the given ID.

        Raises:
            MemoryEntryNotFoundError: If no entry with this ID exists.
        """
        return self._require_entry(entry_id)

    def find_by_project(self, project_id: str) -> List[MemoryEntry]:
        """
        Return all entries whose project_id matches the given value.

        Args:
            project_id: The project identifier to filter by.

        Returns:
            List of MemoryEntry objects, ordered by created_at ascending.
            Empty list if no entries match.
        """
        results = [
            e for e in self._entries.values()
            if e.project_id == project_id
        ]
        return sorted(results, key=lambda e: e.created_at)

    def find_by_category(self, category: MemoryCategory) -> List[MemoryEntry]:
        """
        Return all entries whose category matches.

        Args:
            category: The MemoryCategory to filter by.

        Returns:
            List of MemoryEntry objects, ordered by created_at ascending.
            Empty list if no entries match.
        """
        results = [
            e for e in self._entries.values()
            if e.category == category
        ]
        return sorted(results, key=lambda e: e.created_at)

    def find_by_scope(self, scope: MemoryScope) -> List[MemoryEntry]:
        """
        Return all entries whose scope matches.

        Args:
            scope: The MemoryScope to filter by.

        Returns:
            List of MemoryEntry objects, ordered by created_at ascending.
            Empty list if no entries match.
        """
        results = [
            e for e in self._entries.values()
            if e.scope == scope
        ]
        return sorted(results, key=lambda e: e.created_at)

    def find_by_author(self, author: str) -> List[MemoryEntry]:
        """
        Return all entries authored by the given identifier.

        Args:
            author: The author identifier to filter by.

        Returns:
            List of MemoryEntry objects, ordered by created_at ascending.
        """
        results = [
            e for e in self._entries.values()
            if e.author == author
        ]
        return sorted(results, key=lambda e: e.created_at)

    def search_tags(
        self,
        tags: List[str],
        match: str = "any",
    ) -> List[MemoryEntry]:
        """
        Return entries that carry specified tags.

        Args:
            tags:  List of tags to search for. Must be non-empty.
            match: "any" (default) — entry must have at least one of the
                   listed tags. "all" — entry must have every listed tag.
                   Case-insensitive for both modes.

        Returns:
            List of MemoryEntry objects, ordered by created_at ascending.
            Empty list if no entries match.

        Raises:
            InvalidMemoryEntryError: If tags is empty.
        """
        if not tags:
            raise InvalidMemoryEntryError(
                "search_tags() requires at least one tag."
            )

        if match == "all":
            results = [e for e in self._entries.values() if e.has_all_tags(tags)]
        else:
            results = [e for e in self._entries.values() if e.has_any_tag(tags)]

        return sorted(results, key=lambda e: e.created_at)

    def search_text(self, query: str) -> List[MemoryEntry]:
        """
        Return entries whose title or content contains the query substring.

        The search is case-insensitive. Whitespace-only queries are
        rejected because they would match every entry.

        Args:
            query: Substring to search for in title and content fields.

        Returns:
            List of MemoryEntry objects, ordered by created_at ascending.
            Empty list if no entries match.

        Raises:
            InvalidMemoryEntryError: If query is empty or whitespace-only.
        """
        if not query or not query.strip():
            raise InvalidMemoryEntryError(
                "search_text() requires a non-empty query string."
            )

        results = [
            e for e in self._entries.values()
            if e.contains_text(query)
        ]
        return sorted(results, key=lambda e: e.created_at)

    def query(self, memory_query: MemoryQuery) -> List[MemoryEntry]:
        """
        Return entries matching all active filters in the MemoryQuery.

        This is the general-purpose search method. It evaluates every active
        filter in the query using AND logic and, if limit is set, truncates
        the result to that many entries.

        Args:
            memory_query: The MemoryQuery specifying filters and limit.

        Returns:
            List of MemoryEntry objects, ordered by created_at ascending.
            Truncated to memory_query.limit entries if limit is set.
        """
        results = [
            e for e in self._entries.values()
            if memory_query.matches(e)
        ]
        results.sort(key=lambda e: e.created_at)

        if memory_query.limit is not None:
            results = results[: memory_query.limit]

        return results

    def list_all(self) -> List[MemoryEntry]:
        """
        Return all entries in the engine, ordered by created_at ascending.

        Returns a shallow copy of the internal collection to prevent external
        mutation of the engine's state.

        Returns:
            List of all MemoryEntry objects.
        """
        return sorted(self._entries.values(), key=lambda e: e.created_at)

    def count(self) -> int:
        """Return the total number of entries currently stored."""
        return len(self._entries)

    def statistics(self) -> Dict[str, Any]:
        """
        Return aggregate statistics across all stored entries.

        Returns:
            Dict with keys:
                total_entries        — Total number of entries stored.
                entries_by_category  — Dict mapping category value -> count.
                entries_by_scope     — Dict mapping scope value -> count.
                unique_authors       — Number of distinct author identifiers.
                unique_projects      — Number of distinct project_id values
                                       (None values excluded).
                total_tags           — Total number of tag assignments across
                                       all entries (duplicates across entries
                                       are counted separately).
                unique_tags          — Number of distinct tag values
                                       (case-insensitive).
                entries_updated      — Number of entries that have been
                                       updated at least once (version > 1).
        """
        by_category: Dict[str, int] = {c.value: 0 for c in MemoryCategory}
        by_scope: Dict[str, int] = {s.value: 0 for s in MemoryScope}
        authors: set = set()
        projects: set = set()
        total_tags = 0
        unique_tags_set: set = set()
        updated_count = 0

        for entry in self._entries.values():
            by_category[entry.category.value] = by_category.get(entry.category.value, 0) + 1
            by_scope[entry.scope.value] = by_scope.get(entry.scope.value, 0) + 1
            authors.add(entry.author)
            if entry.project_id is not None:
                projects.add(entry.project_id)
            total_tags += len(entry.tags)
            for tag in entry.tags:
                unique_tags_set.add(tag.lower())
            if entry.has_been_updated():
                updated_count += 1

        return {
            "total_entries": len(self._entries),
            "entries_by_category": dict(by_category),
            "entries_by_scope": dict(by_scope),
            "unique_authors": len(authors),
            "unique_projects": len(projects),
            "total_tags": total_tags,
            "unique_tags": len(unique_tags_set),
            "entries_updated": updated_count,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_entry(self, entry_id: str) -> MemoryEntry:
        """
        Return the entry with the given ID or raise MemoryEntryNotFoundError.

        Args:
            entry_id: The entry ID to look up.

        Raises:
            MemoryEntryNotFoundError: If entry_id is not in _entries.
        """
        entry = self._entries.get(entry_id)
        if entry is None:
            raise MemoryEntryNotFoundError(
                f"No MemoryEntry with id '{entry_id}' exists in the engine."
            )
        return entry

    def _validate_entry(self, entry: MemoryEntry) -> None:
        """
        Validate a MemoryEntry before storing it.

        Args:
            entry: The entry to validate.

        Raises:
            InvalidMemoryEntryError: If any validation rule fails.
        """
        if not entry.title or not entry.title.strip():
            raise InvalidMemoryEntryError(
                "MemoryEntry.title must not be empty."
            )

        if not entry.author or not entry.author.strip():
            raise InvalidMemoryEntryError(
                "MemoryEntry.author must not be empty."
            )

        if not entry.content or not entry.content.strip():
            raise InvalidMemoryEntryError(
                "MemoryEntry.content must not be empty."
            )

        for tag in entry.tags:
            if not tag:
                raise InvalidMemoryEntryError(
                    "MemoryEntry.tags must not contain empty strings."
                )

        if (
            entry.scope == MemoryScope.PROJECT
            and not entry.project_id
        ):
            raise InvalidMemoryEntryError(
                "MemoryEntry with scope PROJECT must have a non-empty project_id."
            )
