"""
Memory query model for AI Company OS.

A MemoryQuery is a structured filter specification for the Memory Engine's
search and listing operations. It encapsulates all search parameters in one
immutable object, making query composition explicit and reusable.

The MemoryEngine.query() method accepts a MemoryQuery and applies every
non-None field as a filter. Fields that are None are treated as "no filter"
— they do not restrict the result set.

Architecture reference: §2.3 Memory Engine, §3 Layer 3 (Infrastructure).
"""

from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

from core.memory_category import MemoryCategory
from core.memory_scope import MemoryScope

if TYPE_CHECKING:
    from core.memory_entry import MemoryEntry


_TAG_MATCH_ANY = "any"
_TAG_MATCH_ALL = "all"


@dataclass(frozen=True)
class MemoryQuery:
    """
    Immutable filter specification for Memory Engine queries.

    All filter fields are optional. A MemoryQuery with no fields set returns
    every entry in the engine. Each non-None field narrows the result set:
    all active filters must match for an entry to be included (AND logic
    across filter fields). Within tag matching, the tag_match parameter
    controls whether "any" or "all" of the specified tags must be present.

    Attributes:
        category:    If set, only entries with this category are returned.
        scope:       If set, only entries with this scope are returned.
        project_id:  If set, only entries whose project_id matches are
                     returned. Pass an empty string to match entries where
                     project_id is None.
        author:      If set, only entries by this author are returned.
        tags:        If set and non-empty, filtered by tag presence.
                     The tag_match parameter controls how multiple tags
                     are evaluated.
        tag_match:   "any" (default) — entry must have at least one of the
                     listed tags. "all" — entry must have every listed tag.
        text:        If set, only entries whose title or content contains
                     this substring (case-insensitive) are returned.
        limit:       If set, at most this many entries are returned.
                     Applied after all other filters. None means no limit.
    """

    category: Optional[MemoryCategory] = None
    scope: Optional[MemoryScope] = None
    project_id: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[List[str]] = None
    tag_match: str = _TAG_MATCH_ANY
    text: Optional[str] = None
    limit: Optional[int] = None

    def matches(self, entry: "MemoryEntry") -> bool:
        """
        Return True if the entry satisfies all active filters in this query.

        Applies AND logic across filter fields. A field of None is not active
        and does not restrict the result. Tag matching uses the tag_match
        parameter to choose between any-match and all-match semantics.

        Args:
            entry: The MemoryEntry to test.

        Returns:
            True if the entry satisfies every active filter.
        """
        if self.category is not None and entry.category != self.category:
            return False

        if self.scope is not None and entry.scope != self.scope:
            return False

        if self.project_id is not None:
            entry_pid = entry.project_id if entry.project_id is not None else ""
            if entry_pid != self.project_id:
                return False

        if self.author is not None and entry.author != self.author:
            return False

        if self.tags:
            if self.tag_match == _TAG_MATCH_ALL:
                if not entry.has_all_tags(self.tags):
                    return False
            else:
                if not entry.has_any_tag(self.tags):
                    return False

        if self.text is not None and not entry.contains_text(self.text):
            return False

        return True

    def is_empty(self) -> bool:
        """
        Return True if no filters are active (all fields are None or empty).

        An empty query matches every entry in the Memory Engine.
        """
        return (
            self.category is None
            and self.scope is None
            and self.project_id is None
            and self.author is None
            and not self.tags
            and self.text is None
        )

    # ------------------------------------------------------------------
    # Convenience factories
    # ------------------------------------------------------------------

    @classmethod
    def for_project(cls, project_id: str) -> "MemoryQuery":
        """Return a query that matches all entries for a given project."""
        return cls(project_id=project_id)

    @classmethod
    def for_category(cls, category: MemoryCategory) -> "MemoryQuery":
        """Return a query that matches all entries of a given category."""
        return cls(category=category)

    @classmethod
    def for_scope(cls, scope: MemoryScope) -> "MemoryQuery":
        """Return a query that matches all entries with a given scope."""
        return cls(scope=scope)

    @classmethod
    def for_author(cls, author: str) -> "MemoryQuery":
        """Return a query that matches all entries by a given author."""
        return cls(author=author)

    @classmethod
    def for_tags(
        cls,
        tags: List[str],
        match: str = _TAG_MATCH_ANY,
    ) -> "MemoryQuery":
        """
        Return a query that matches entries by tag presence.

        Args:
            tags:  List of tags to search for.
            match: "any" (default) or "all".

        Returns:
            A MemoryQuery with the tag filter configured.
        """
        return cls(tags=tags, tag_match=match)

    @classmethod
    def for_text(cls, text: str) -> "MemoryQuery":
        """Return a query that matches entries containing a text substring."""
        return cls(text=text)
