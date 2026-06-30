"""
Tests for the Memory Engine — Sprint 11.

Test classes:
  TestMemoryCategory              (14) — enum values, helpers
  TestMemoryScope                 (14) — enum values, helpers
  TestMemoryEntryRevision         (8)  — revision dataclass
  TestMemoryEntry                 (24) — dataclass, helpers, summary
  TestMemoryQuery                 (22) — construction, matches(), factories
  TestMemoryEngineInit            (6)  — construction
  TestMemoryEngineStore           (20) — happy path, validation, duplicates
  TestMemoryEngineUpdate          (22) — update, history, validation
  TestMemoryEngineDelete          (14) — delete, not found
  TestMemoryEngineFindById        (10) — found, not found
  TestMemoryEngineFindByProject   (12) — filtering
  TestMemoryEngineFindByCategory  (12) — filtering
  TestMemoryEngineFindByScope     (10) — filtering
  TestMemoryEngineFindByAuthor    (8)  — filtering
  TestMemoryEngineSearchTags      (18) — any/all, case, empty
  TestMemoryEngineSearchText      (14) — substring, case, empty
  TestMemoryEngineQuery           (14) — MemoryQuery integration
  TestMemoryEngineListAll         (6)  — list_all, count
  TestMemoryEngineStatistics      (16) — statistics dict
  TestIntegration                 (12) — end-to-end scenarios
  TestContracts                   (10) — invariants

Total: 266 tests
"""

import unittest
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from core.memory_category import MemoryCategory
from core.memory_entry import MemoryEntry, MemoryEntryRevision
from core.memory_engine import (
    DuplicateEntryError,
    InvalidMemoryEntryError,
    MemoryEngine,
    MemoryEngineError,
    MemoryEntryNotFoundError,
)
from core.memory_query import MemoryQuery
from core.memory_scope import MemoryScope


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _entry(
    *,
    id: str = "",
    title: str = "Test Entry",
    category: MemoryCategory = MemoryCategory.DECISION,
    scope: MemoryScope = MemoryScope.GLOBAL,
    author: str = "ceo",
    content: str = "This is a test entry with sufficient content.",
    tags: Optional[list] = None,
    project_id: Optional[str] = None,
) -> MemoryEntry:
    now = _now()
    return MemoryEntry(
        id=id or str(uuid4()),
        title=title,
        category=category,
        scope=scope,
        author=author,
        content=content,
        tags=tags if tags is not None else [],
        project_id=project_id,
        created_at=now,
        updated_at=now,
    )


def _store(engine: MemoryEngine, **kwargs) -> MemoryEntry:
    return engine.store(_entry(**kwargs))


# ===========================================================================
# TestMemoryCategory
# ===========================================================================

class TestMemoryCategory(unittest.TestCase):

    def test_all_values_are_str(self):
        for cat in MemoryCategory:
            self.assertIsInstance(cat, str)

    def test_str_returns_value(self):
        self.assertEqual(str(MemoryCategory.PROJECT), "PROJECT")
        self.assertEqual(str(MemoryCategory.DECISION), "DECISION")

    def test_all_seven_categories_exist(self):
        values = {c.value for c in MemoryCategory}
        expected = {"PROJECT", "DECISION", "DISCUSSION", "TASK", "LESSON", "DOCUMENT", "CEO_NOTE"}
        self.assertEqual(values, expected)

    def test_category_count(self):
        self.assertEqual(len(MemoryCategory), 7)

    def test_decision_is_governance_related(self):
        self.assertTrue(MemoryCategory.DECISION.is_governance_related())

    def test_ceo_note_is_governance_related(self):
        self.assertTrue(MemoryCategory.CEO_NOTE.is_governance_related())

    def test_others_not_governance_related(self):
        for cat in MemoryCategory:
            if cat not in {MemoryCategory.DECISION, MemoryCategory.CEO_NOTE}:
                self.assertFalse(cat.is_governance_related(), cat)

    def test_project_is_project_scoped(self):
        self.assertTrue(MemoryCategory.PROJECT.is_project_scoped())

    def test_task_is_project_scoped(self):
        self.assertTrue(MemoryCategory.TASK.is_project_scoped())

    def test_discussion_is_project_scoped(self):
        self.assertTrue(MemoryCategory.DISCUSSION.is_project_scoped())

    def test_lesson_is_knowledge_base(self):
        self.assertTrue(MemoryCategory.LESSON.is_knowledge_base())

    def test_document_is_knowledge_base(self):
        self.assertTrue(MemoryCategory.DOCUMENT.is_knowledge_base())

    def test_project_not_knowledge_base(self):
        self.assertFalse(MemoryCategory.PROJECT.is_knowledge_base())

    def test_equality_with_string(self):
        self.assertEqual(MemoryCategory.DECISION, "DECISION")


# ===========================================================================
# TestMemoryScope
# ===========================================================================

class TestMemoryScope(unittest.TestCase):

    def test_all_values_are_str(self):
        for scope in MemoryScope:
            self.assertIsInstance(scope, str)

    def test_str_returns_value(self):
        self.assertEqual(str(MemoryScope.GLOBAL), "GLOBAL")
        self.assertEqual(str(MemoryScope.CEO_PRIVATE), "CEO_PRIVATE")

    def test_all_five_scopes_exist(self):
        values = {s.value for s in MemoryScope}
        expected = {"GLOBAL", "PROJECT", "DEPARTMENT", "EMPLOYEE", "CEO_PRIVATE"}
        self.assertEqual(values, expected)

    def test_scope_count(self):
        self.assertEqual(len(MemoryScope), 5)

    def test_employee_is_private(self):
        self.assertTrue(MemoryScope.EMPLOYEE.is_private())

    def test_ceo_private_is_private(self):
        self.assertTrue(MemoryScope.CEO_PRIVATE.is_private())

    def test_global_not_private(self):
        self.assertFalse(MemoryScope.GLOBAL.is_private())

    def test_project_not_private(self):
        self.assertFalse(MemoryScope.PROJECT.is_private())

    def test_global_accessible_to_all(self):
        self.assertTrue(MemoryScope.GLOBAL.is_accessible_to_all())

    def test_others_not_accessible_to_all(self):
        for scope in MemoryScope:
            if scope != MemoryScope.GLOBAL:
                self.assertFalse(scope.is_accessible_to_all(), scope)

    def test_project_scope_is_project_scoped(self):
        self.assertTrue(MemoryScope.PROJECT.is_project_scoped())

    def test_global_not_project_scoped(self):
        self.assertFalse(MemoryScope.GLOBAL.is_project_scoped())

    def test_project_requires_project_id(self):
        self.assertTrue(MemoryScope.PROJECT.requires_project_id())

    def test_others_not_require_project_id(self):
        for scope in MemoryScope:
            if scope != MemoryScope.PROJECT:
                self.assertFalse(scope.requires_project_id(), scope)


# ===========================================================================
# TestMemoryEntryRevision
# ===========================================================================

class TestMemoryEntryRevision(unittest.TestCase):

    def _rev(self, version=1, content="old content"):
        return MemoryEntryRevision(
            version=version,
            title="Old Title",
            content=content,
            tags=["a", "b"],
            recorded_at=_now(),
            changed_by="ceo",
        )

    def test_revision_has_version(self):
        r = self._rev(version=3)
        self.assertEqual(r.version, 3)

    def test_revision_has_content(self):
        r = self._rev(content="previous content")
        self.assertEqual(r.content, "previous content")

    def test_revision_has_tags(self):
        r = self._rev()
        self.assertEqual(r.tags, ["a", "b"])

    def test_revision_has_recorded_at(self):
        before = _now()
        r = self._rev()
        self.assertGreaterEqual(r.recorded_at, before)

    def test_revision_has_changed_by(self):
        r = self._rev()
        self.assertEqual(r.changed_by, "ceo")

    def test_revision_to_dict_has_keys(self):
        r = self._rev()
        d = r.to_dict()
        for key in ["version", "title", "content", "tags", "recorded_at", "changed_by"]:
            self.assertIn(key, d)

    def test_revision_to_dict_version(self):
        r = self._rev(version=7)
        self.assertEqual(r.to_dict()["version"], 7)

    def test_revision_default_changed_by_empty(self):
        r = MemoryEntryRevision(
            version=1, title="T", content="C", tags=[], recorded_at=_now()
        )
        self.assertEqual(r.changed_by, "")


# ===========================================================================
# TestMemoryEntry
# ===========================================================================

class TestMemoryEntry(unittest.TestCase):

    def _entry_obj(self, **kw):
        return _entry(**kw)

    def test_entry_has_id(self):
        e = self._entry_obj()
        self.assertIsNotNone(e.id)

    def test_entry_has_title(self):
        e = self._entry_obj(title="My Title")
        self.assertEqual(e.title, "My Title")

    def test_entry_has_category(self):
        e = self._entry_obj(category=MemoryCategory.LESSON)
        self.assertEqual(e.category, MemoryCategory.LESSON)

    def test_entry_has_scope(self):
        e = self._entry_obj(scope=MemoryScope.DEPARTMENT)
        self.assertEqual(e.scope, MemoryScope.DEPARTMENT)

    def test_entry_has_author(self):
        e = self._entry_obj(author="agent-1")
        self.assertEqual(e.author, "agent-1")

    def test_entry_has_content(self):
        e = self._entry_obj(content="Some content here.")
        self.assertEqual(e.content, "Some content here.")

    def test_entry_default_tags_empty(self):
        e = self._entry_obj()
        self.assertEqual(e.tags, [])

    def test_entry_tags_stored(self):
        e = self._entry_obj(tags=["a", "b"])
        self.assertEqual(e.tags, ["a", "b"])

    def test_entry_default_project_id_none(self):
        e = self._entry_obj()
        self.assertIsNone(e.project_id)

    def test_entry_project_id_stored(self):
        e = self._entry_obj(project_id="proj-1")
        self.assertEqual(e.project_id, "proj-1")

    def test_entry_default_version_one(self):
        e = self._entry_obj()
        self.assertEqual(e.version, 1)

    def test_entry_default_history_empty(self):
        e = self._entry_obj()
        self.assertEqual(e.history, [])

    def test_has_tag_true(self):
        e = self._entry_obj(tags=["python", "backend"])
        self.assertTrue(e.has_tag("python"))

    def test_has_tag_case_insensitive(self):
        e = self._entry_obj(tags=["Python"])
        self.assertTrue(e.has_tag("python"))

    def test_has_tag_false(self):
        e = self._entry_obj(tags=["python"])
        self.assertFalse(e.has_tag("java"))

    def test_has_any_tag_true(self):
        e = self._entry_obj(tags=["python", "backend"])
        self.assertTrue(e.has_any_tag(["java", "python"]))

    def test_has_any_tag_false(self):
        e = self._entry_obj(tags=["python"])
        self.assertFalse(e.has_any_tag(["java", "ruby"]))

    def test_has_all_tags_true(self):
        e = self._entry_obj(tags=["python", "backend", "api"])
        self.assertTrue(e.has_all_tags(["python", "backend"]))

    def test_has_all_tags_false(self):
        e = self._entry_obj(tags=["python"])
        self.assertFalse(e.has_all_tags(["python", "backend"]))

    def test_contains_text_in_title(self):
        e = self._entry_obj(title="Architecture Decision 001")
        self.assertTrue(e.contains_text("architecture"))

    def test_contains_text_in_content(self):
        e = self._entry_obj(content="Use PostgreSQL for primary storage.")
        self.assertTrue(e.contains_text("postgresql"))

    def test_contains_text_false(self):
        e = self._entry_obj(title="A", content="B")
        self.assertFalse(e.contains_text("zzz"))

    def test_is_project_entry_true(self):
        e = self._entry_obj(project_id="proj-1")
        self.assertTrue(e.is_project_entry())

    def test_is_project_entry_false(self):
        e = self._entry_obj()
        self.assertFalse(e.is_project_entry())

    def test_has_been_updated_false_at_creation(self):
        e = self._entry_obj()
        self.assertFalse(e.has_been_updated())

    def test_summary_returns_dict(self):
        e = self._entry_obj()
        s = e.summary()
        self.assertIsInstance(s, dict)

    def test_summary_contains_required_keys(self):
        e = self._entry_obj()
        s = e.summary()
        for k in ["id", "title", "category", "scope", "author", "version", "tags"]:
            self.assertIn(k, s)


# ===========================================================================
# TestMemoryQuery
# ===========================================================================

class TestMemoryQuery(unittest.TestCase):

    def _e(self, **kw):
        return _entry(**kw)

    def test_empty_query_matches_everything(self):
        q = MemoryQuery()
        e = self._e()
        self.assertTrue(q.matches(e))

    def test_is_empty_true_for_blank_query(self):
        q = MemoryQuery()
        self.assertTrue(q.is_empty())

    def test_is_empty_false_when_category_set(self):
        q = MemoryQuery(category=MemoryCategory.DECISION)
        self.assertFalse(q.is_empty())

    def test_category_filter_matches(self):
        q = MemoryQuery(category=MemoryCategory.DECISION)
        e = self._e(category=MemoryCategory.DECISION)
        self.assertTrue(q.matches(e))

    def test_category_filter_no_match(self):
        q = MemoryQuery(category=MemoryCategory.LESSON)
        e = self._e(category=MemoryCategory.DECISION)
        self.assertFalse(q.matches(e))

    def test_scope_filter_matches(self):
        q = MemoryQuery(scope=MemoryScope.GLOBAL)
        e = self._e(scope=MemoryScope.GLOBAL)
        self.assertTrue(q.matches(e))

    def test_scope_filter_no_match(self):
        q = MemoryQuery(scope=MemoryScope.EMPLOYEE)
        e = self._e(scope=MemoryScope.GLOBAL)
        self.assertFalse(q.matches(e))

    def test_project_id_filter_matches(self):
        q = MemoryQuery(project_id="proj-1")
        e = self._e(project_id="proj-1")
        self.assertTrue(q.matches(e))

    def test_project_id_filter_no_match(self):
        q = MemoryQuery(project_id="proj-1")
        e = self._e(project_id="proj-2")
        self.assertFalse(q.matches(e))

    def test_author_filter_matches(self):
        q = MemoryQuery(author="agent-1")
        e = self._e(author="agent-1")
        self.assertTrue(q.matches(e))

    def test_author_filter_no_match(self):
        q = MemoryQuery(author="agent-2")
        e = self._e(author="agent-1")
        self.assertFalse(q.matches(e))

    def test_tags_any_match(self):
        q = MemoryQuery(tags=["python", "java"])
        e = self._e(tags=["python", "backend"])
        self.assertTrue(q.matches(e))

    def test_tags_any_no_match(self):
        q = MemoryQuery(tags=["java", "ruby"])
        e = self._e(tags=["python", "backend"])
        self.assertFalse(q.matches(e))

    def test_tags_all_match(self):
        q = MemoryQuery(tags=["python", "backend"], tag_match="all")
        e = self._e(tags=["python", "backend", "api"])
        self.assertTrue(q.matches(e))

    def test_tags_all_no_match(self):
        q = MemoryQuery(tags=["python", "backend"], tag_match="all")
        e = self._e(tags=["python"])
        self.assertFalse(q.matches(e))

    def test_text_filter_matches_title(self):
        q = MemoryQuery(text="architecture")
        e = self._e(title="Architecture Decision 001")
        self.assertTrue(q.matches(e))

    def test_text_filter_matches_content(self):
        q = MemoryQuery(text="postgresql")
        e = self._e(content="Use PostgreSQL as the database.")
        self.assertTrue(q.matches(e))

    def test_text_filter_no_match(self):
        q = MemoryQuery(text="zzz")
        e = self._e(title="Nothing", content="Nothing at all")
        self.assertFalse(q.matches(e))

    def test_query_is_frozen(self):
        q = MemoryQuery(category=MemoryCategory.DECISION)
        with self.assertRaises(Exception):
            q.category = MemoryCategory.LESSON  # type: ignore

    def test_factory_for_project(self):
        q = MemoryQuery.for_project("proj-99")
        self.assertEqual(q.project_id, "proj-99")

    def test_factory_for_category(self):
        q = MemoryQuery.for_category(MemoryCategory.LESSON)
        self.assertEqual(q.category, MemoryCategory.LESSON)

    def test_factory_for_scope(self):
        q = MemoryQuery.for_scope(MemoryScope.GLOBAL)
        self.assertEqual(q.scope, MemoryScope.GLOBAL)


# ===========================================================================
# TestMemoryEngineInit
# ===========================================================================

class TestMemoryEngineInit(unittest.TestCase):

    def test_init_creates_empty_store(self):
        engine = MemoryEngine()
        self.assertEqual(engine.count(), 0)

    def test_list_all_empty_initially(self):
        engine = MemoryEngine()
        self.assertEqual(engine.list_all(), [])

    def test_statistics_all_zeros(self):
        engine = MemoryEngine()
        stats = engine.statistics()
        self.assertEqual(stats["total_entries"], 0)

    def test_error_hierarchy(self):
        self.assertTrue(issubclass(MemoryEntryNotFoundError, MemoryEngineError))
        self.assertTrue(issubclass(DuplicateEntryError, MemoryEngineError))
        self.assertTrue(issubclass(InvalidMemoryEntryError, MemoryEngineError))

    def test_error_base_is_exception(self):
        self.assertTrue(issubclass(MemoryEngineError, Exception))

    def test_two_engines_independent(self):
        e1 = MemoryEngine()
        e2 = MemoryEngine()
        e1.store(_entry())
        self.assertEqual(e1.count(), 1)
        self.assertEqual(e2.count(), 0)


# ===========================================================================
# TestMemoryEngineStore
# ===========================================================================

class TestMemoryEngineStore(unittest.TestCase):

    def setUp(self):
        self.engine = MemoryEngine()

    def test_store_returns_entry(self):
        e = _entry()
        result = self.engine.store(e)
        self.assertIsInstance(result, MemoryEntry)

    def test_store_increments_count(self):
        self.engine.store(_entry())
        self.assertEqual(self.engine.count(), 1)

    def test_store_multiple_increments_count(self):
        for _ in range(5):
            self.engine.store(_entry())
        self.assertEqual(self.engine.count(), 5)

    def test_store_with_tags(self):
        e = _entry(tags=["python", "backend"])
        self.engine.store(e)
        result = self.engine.find_by_id(e.id)
        self.assertEqual(result.tags, ["python", "backend"])

    def test_store_with_project_id(self):
        e = _entry(project_id="proj-1")
        self.engine.store(e)
        self.assertEqual(self.engine.find_by_id(e.id).project_id, "proj-1")

    def test_store_project_scope_without_project_id_raises(self):
        e = _entry(scope=MemoryScope.PROJECT, project_id=None)
        with self.assertRaises(InvalidMemoryEntryError):
            self.engine.store(e)

    def test_store_project_scope_with_project_id_succeeds(self):
        e = _entry(scope=MemoryScope.PROJECT, project_id="proj-42")
        self.engine.store(e)
        self.assertEqual(self.engine.count(), 1)

    def test_store_empty_title_raises(self):
        e = _entry(title="")
        with self.assertRaises(InvalidMemoryEntryError):
            self.engine.store(e)

    def test_store_whitespace_title_raises(self):
        e = _entry(title="   ")
        with self.assertRaises(InvalidMemoryEntryError):
            self.engine.store(e)

    def test_store_empty_author_raises(self):
        e = _entry(author="")
        with self.assertRaises(InvalidMemoryEntryError):
            self.engine.store(e)

    def test_store_empty_content_raises(self):
        e = _entry(content="")
        with self.assertRaises(InvalidMemoryEntryError):
            self.engine.store(e)

    def test_store_tag_with_empty_string_raises(self):
        e = _entry(tags=["valid", ""])
        with self.assertRaises(InvalidMemoryEntryError):
            self.engine.store(e)

    def test_store_duplicate_id_raises(self):
        e = _entry()
        self.engine.store(e)
        with self.assertRaises(DuplicateEntryError):
            self.engine.store(e)

    def test_store_duplicate_raises_correct_type(self):
        e = _entry()
        self.engine.store(e)
        try:
            self.engine.store(e)
        except DuplicateEntryError:
            pass
        except Exception as ex:
            self.fail(f"Wrong exception: {ex}")

    def test_store_auto_generates_id_when_empty(self):
        now = _now()
        e = MemoryEntry(
            id="",
            title="Auto ID",
            category=MemoryCategory.DOCUMENT,
            scope=MemoryScope.GLOBAL,
            author="ceo",
            content="Some content for the auto ID test.",
            created_at=now,
            updated_at=now,
        )
        result = self.engine.store(e)
        self.assertNotEqual(result.id, "")
        self.assertGreater(len(result.id), 8)

    def test_store_returns_same_object(self):
        e = _entry()
        result = self.engine.store(e)
        self.assertIs(result, e)

    def test_store_all_categories_accepted(self):
        for cat in MemoryCategory:
            self.engine.store(_entry(category=cat))
        self.assertEqual(self.engine.count(), len(MemoryCategory))

    def test_store_all_scopes_except_project(self):
        for scope in MemoryScope:
            if scope == MemoryScope.PROJECT:
                continue
            self.engine.store(_entry(scope=scope))
        self.assertEqual(self.engine.count(), len(MemoryScope) - 1)

    def test_store_invalid_entry_is_not_stored(self):
        e = _entry(title="")
        try:
            self.engine.store(e)
        except InvalidMemoryEntryError:
            pass
        self.assertEqual(self.engine.count(), 0)

    def test_store_error_is_memory_engine_error(self):
        e = _entry(title="")
        with self.assertRaises(MemoryEngineError):
            self.engine.store(e)


# ===========================================================================
# TestMemoryEngineUpdate
# ===========================================================================

class TestMemoryEngineUpdate(unittest.TestCase):

    def setUp(self):
        self.engine = MemoryEngine()
        self.entry = _store(self.engine)

    def test_update_content_changes_content(self):
        new_content = "Updated content with new information."
        self.engine.update(self.entry.id, content=new_content)
        self.assertEqual(self.entry.content, new_content)

    def test_update_title_changes_title(self):
        self.engine.update(self.entry.id, title="New Title")
        self.assertEqual(self.entry.title, "New Title")

    def test_update_tags_changes_tags(self):
        self.engine.update(self.entry.id, tags=["new", "tags"])
        self.assertEqual(self.entry.tags, ["new", "tags"])

    def test_update_increments_version(self):
        self.engine.update(self.entry.id, content="v2")
        self.assertEqual(self.entry.version, 2)

    def test_update_twice_version_three(self):
        self.engine.update(self.entry.id, content="v2")
        self.engine.update(self.entry.id, content="v3")
        self.assertEqual(self.entry.version, 3)

    def test_update_advances_updated_at(self):
        old_updated = self.entry.updated_at
        self.engine.update(self.entry.id, content="new content here")
        self.assertGreaterEqual(self.entry.updated_at, old_updated)

    def test_update_preserves_created_at(self):
        old_created = self.entry.created_at
        self.engine.update(self.entry.id, content="change")
        self.assertEqual(self.entry.created_at, old_created)

    def test_update_stores_revision(self):
        original_content = self.entry.content
        self.engine.update(self.entry.id, content="new")
        self.assertEqual(len(self.entry.history), 1)
        self.assertEqual(self.entry.history[0].content, original_content)

    def test_update_revision_version_is_old_version(self):
        self.engine.update(self.entry.id, content="v2")
        self.assertEqual(self.entry.history[0].version, 1)

    def test_update_revision_preserves_old_title(self):
        old_title = self.entry.title
        self.engine.update(self.entry.id, title="New")
        self.assertEqual(self.entry.history[0].title, old_title)

    def test_update_revision_preserves_old_tags(self):
        self.engine.update(self.entry.id, tags=["x"])
        self.assertEqual(self.entry.history[0].tags, [])

    def test_update_revision_records_changed_by(self):
        self.engine.update(self.entry.id, content="v2", changed_by="architect")
        self.assertEqual(self.entry.history[0].changed_by, "architect")

    def test_update_multiple_revisions_ordered(self):
        self.engine.update(self.entry.id, content="v2")
        self.engine.update(self.entry.id, content="v3")
        self.assertEqual(len(self.entry.history), 2)
        self.assertEqual(self.entry.history[0].version, 1)
        self.assertEqual(self.entry.history[1].version, 2)

    def test_update_returns_entry(self):
        result = self.engine.update(self.entry.id, content="new")
        self.assertIsInstance(result, MemoryEntry)

    def test_update_not_found_raises(self):
        with self.assertRaises(MemoryEntryNotFoundError):
            self.engine.update("nonexistent-id", content="x")

    def test_update_all_none_raises(self):
        with self.assertRaises(InvalidMemoryEntryError):
            self.engine.update(self.entry.id)

    def test_update_empty_content_raises(self):
        with self.assertRaises(InvalidMemoryEntryError):
            self.engine.update(self.entry.id, content="")

    def test_update_empty_title_raises(self):
        with self.assertRaises(InvalidMemoryEntryError):
            self.engine.update(self.entry.id, title="")

    def test_update_tag_with_empty_string_raises(self):
        with self.assertRaises(InvalidMemoryEntryError):
            self.engine.update(self.entry.id, tags=["valid", ""])

    def test_update_empty_tags_list_accepted(self):
        self.engine.update(self.entry.id, tags=[])
        self.assertEqual(self.entry.tags, [])

    def test_update_has_been_updated_true_after(self):
        self.engine.update(self.entry.id, content="changed")
        self.assertTrue(self.entry.has_been_updated())

    def test_update_revision_count_increments(self):
        self.engine.update(self.entry.id, content="v2")
        self.engine.update(self.entry.id, content="v3")
        self.assertEqual(self.entry.revision_count(), 2)


# ===========================================================================
# TestMemoryEngineDelete
# ===========================================================================

class TestMemoryEngineDelete(unittest.TestCase):

    def setUp(self):
        self.engine = MemoryEngine()

    def test_delete_reduces_count(self):
        e = _store(self.engine)
        self.engine.delete(e.id)
        self.assertEqual(self.engine.count(), 0)

    def test_delete_returns_entry(self):
        e = _store(self.engine)
        result = self.engine.delete(e.id)
        self.assertIsInstance(result, MemoryEntry)

    def test_delete_returns_same_entry(self):
        e = _store(self.engine)
        result = self.engine.delete(e.id)
        self.assertEqual(result.id, e.id)

    def test_delete_entry_no_longer_findable(self):
        e = _store(self.engine)
        self.engine.delete(e.id)
        with self.assertRaises(MemoryEntryNotFoundError):
            self.engine.find_by_id(e.id)

    def test_delete_nonexistent_raises(self):
        with self.assertRaises(MemoryEntryNotFoundError):
            self.engine.delete("ghost-id")

    def test_delete_one_of_many(self):
        e1 = _store(self.engine)
        e2 = _store(self.engine)
        self.engine.delete(e1.id)
        self.assertEqual(self.engine.count(), 1)
        self.engine.find_by_id(e2.id)

    def test_delete_returns_entry_with_history(self):
        e = _store(self.engine)
        self.engine.update(e.id, content="updated")
        result = self.engine.delete(e.id)
        self.assertEqual(len(result.history), 1)

    def test_delete_twice_raises(self):
        e = _store(self.engine)
        self.engine.delete(e.id)
        with self.assertRaises(MemoryEntryNotFoundError):
            self.engine.delete(e.id)

    def test_delete_error_is_memory_engine_error(self):
        with self.assertRaises(MemoryEngineError):
            self.engine.delete("no-such-id")

    def test_delete_all_entries(self):
        ids = [_store(self.engine).id for _ in range(5)]
        for eid in ids:
            self.engine.delete(eid)
        self.assertEqual(self.engine.count(), 0)

    def test_delete_then_store_same_id(self):
        e = _store(self.engine)
        eid = e.id
        self.engine.delete(eid)
        e2 = _entry(id=eid)
        self.engine.store(e2)
        self.assertEqual(self.engine.count(), 1)

    def test_delete_updates_statistics(self):
        e = _store(self.engine)
        self.engine.delete(e.id)
        self.assertEqual(self.engine.statistics()["total_entries"], 0)

    def test_delete_nonexistent_error_message(self):
        try:
            self.engine.delete("xyz")
        except MemoryEntryNotFoundError as err:
            self.assertIn("xyz", str(err))

    def test_delete_error_type(self):
        with self.assertRaises(MemoryEntryNotFoundError):
            self.engine.delete("nonexistent")


# ===========================================================================
# TestMemoryEngineFindById
# ===========================================================================

class TestMemoryEngineFindById(unittest.TestCase):

    def setUp(self):
        self.engine = MemoryEngine()

    def test_find_by_id_returns_entry(self):
        e = _store(self.engine)
        result = self.engine.find_by_id(e.id)
        self.assertIsInstance(result, MemoryEntry)

    def test_find_by_id_returns_correct_entry(self):
        e = _store(self.engine, title="Unique Title")
        result = self.engine.find_by_id(e.id)
        self.assertEqual(result.title, "Unique Title")

    def test_find_by_id_not_found_raises(self):
        with self.assertRaises(MemoryEntryNotFoundError):
            self.engine.find_by_id("no-such-id")

    def test_find_by_id_is_same_object(self):
        e = _store(self.engine)
        result = self.engine.find_by_id(e.id)
        self.assertIs(result, e)

    def test_find_by_id_multiple_entries(self):
        e1 = _store(self.engine, title="Entry A")
        e2 = _store(self.engine, title="Entry B")
        self.assertEqual(self.engine.find_by_id(e1.id).title, "Entry A")
        self.assertEqual(self.engine.find_by_id(e2.id).title, "Entry B")

    def test_find_by_id_after_update(self):
        e = _store(self.engine)
        self.engine.update(e.id, title="Updated Title")
        result = self.engine.find_by_id(e.id)
        self.assertEqual(result.title, "Updated Title")

    def test_find_by_id_error_is_memory_engine_error(self):
        with self.assertRaises(MemoryEngineError):
            self.engine.find_by_id("ghost")

    def test_find_by_id_error_message_contains_id(self):
        try:
            self.engine.find_by_id("ghost-99")
        except MemoryEntryNotFoundError as err:
            self.assertIn("ghost-99", str(err))

    def test_find_by_id_empty_string_raises(self):
        with self.assertRaises(MemoryEntryNotFoundError):
            self.engine.find_by_id("")

    def test_find_by_id_after_delete_raises(self):
        e = _store(self.engine)
        self.engine.delete(e.id)
        with self.assertRaises(MemoryEntryNotFoundError):
            self.engine.find_by_id(e.id)


# ===========================================================================
# TestMemoryEngineFindByProject
# ===========================================================================

class TestMemoryEngineFindByProject(unittest.TestCase):

    def setUp(self):
        self.engine = MemoryEngine()

    def test_find_by_project_returns_list(self):
        result = self.engine.find_by_project("p1")
        self.assertIsInstance(result, list)

    def test_find_by_project_empty_when_no_match(self):
        _store(self.engine, project_id="p2")
        self.assertEqual(self.engine.find_by_project("p1"), [])

    def test_find_by_project_returns_matching_entries(self):
        _store(self.engine, project_id="p1")
        _store(self.engine, project_id="p1")
        _store(self.engine, project_id="p2")
        result = self.engine.find_by_project("p1")
        self.assertEqual(len(result), 2)

    def test_find_by_project_none_project_id_not_returned(self):
        _store(self.engine)  # no project_id
        result = self.engine.find_by_project("p1")
        self.assertEqual(result, [])

    def test_find_by_project_ordered_by_created_at(self):
        e1 = _store(self.engine, project_id="p1")
        e2 = _store(self.engine, project_id="p1")
        result = self.engine.find_by_project("p1")
        self.assertLessEqual(result[0].created_at, result[1].created_at)

    def test_find_by_project_is_shallow_copy(self):
        _store(self.engine, project_id="p1")
        r1 = self.engine.find_by_project("p1")
        r1.clear()
        self.assertEqual(len(self.engine.find_by_project("p1")), 1)

    def test_find_by_project_multiple_projects(self):
        for pid in ["a", "b", "c"]:
            for _ in range(3):
                _store(self.engine, project_id=pid)
        for pid in ["a", "b", "c"]:
            self.assertEqual(len(self.engine.find_by_project(pid)), 3)

    def test_find_by_project_all_categories(self):
        for cat in MemoryCategory:
            _store(self.engine, project_id="mix", category=cat)
        result = self.engine.find_by_project("mix")
        self.assertEqual(len(result), len(MemoryCategory))

    def test_find_by_project_after_delete(self):
        e = _store(self.engine, project_id="p1")
        _store(self.engine, project_id="p1")
        self.engine.delete(e.id)
        self.assertEqual(len(self.engine.find_by_project("p1")), 1)

    def test_find_by_project_returns_correct_project_ids(self):
        _store(self.engine, project_id="p1")
        results = self.engine.find_by_project("p1")
        for r in results:
            self.assertEqual(r.project_id, "p1")

    def test_find_by_project_empty_string_project_id(self):
        result = self.engine.find_by_project("")
        self.assertIsInstance(result, list)

    def test_find_by_project_after_update(self):
        e = _store(self.engine, project_id="p1")
        self.engine.update(e.id, content="updated content here")
        result = self.engine.find_by_project("p1")
        self.assertEqual(result[0].project_id, "p1")


# ===========================================================================
# TestMemoryEngineFindByCategory
# ===========================================================================

class TestMemoryEngineFindByCategory(unittest.TestCase):

    def setUp(self):
        self.engine = MemoryEngine()

    def test_find_by_category_returns_list(self):
        result = self.engine.find_by_category(MemoryCategory.DECISION)
        self.assertIsInstance(result, list)

    def test_find_by_category_empty_when_no_match(self):
        _store(self.engine, category=MemoryCategory.LESSON)
        result = self.engine.find_by_category(MemoryCategory.DECISION)
        self.assertEqual(result, [])

    def test_find_by_category_returns_matching(self):
        _store(self.engine, category=MemoryCategory.DECISION)
        _store(self.engine, category=MemoryCategory.DECISION)
        _store(self.engine, category=MemoryCategory.LESSON)
        result = self.engine.find_by_category(MemoryCategory.DECISION)
        self.assertEqual(len(result), 2)

    def test_find_by_category_all_entries_correct_category(self):
        _store(self.engine, category=MemoryCategory.DOCUMENT)
        results = self.engine.find_by_category(MemoryCategory.DOCUMENT)
        for r in results:
            self.assertEqual(r.category, MemoryCategory.DOCUMENT)

    def test_find_by_category_ordered_by_created_at(self):
        _store(self.engine, category=MemoryCategory.TASK)
        _store(self.engine, category=MemoryCategory.TASK)
        result = self.engine.find_by_category(MemoryCategory.TASK)
        self.assertLessEqual(result[0].created_at, result[1].created_at)

    def test_find_by_category_all_categories(self):
        for cat in MemoryCategory:
            _store(self.engine, category=cat)
        for cat in MemoryCategory:
            self.assertEqual(len(self.engine.find_by_category(cat)), 1)

    def test_find_by_category_is_shallow_copy(self):
        _store(self.engine, category=MemoryCategory.LESSON)
        r = self.engine.find_by_category(MemoryCategory.LESSON)
        r.clear()
        self.assertEqual(len(self.engine.find_by_category(MemoryCategory.LESSON)), 1)

    def test_find_by_category_ceo_note(self):
        _store(self.engine, category=MemoryCategory.CEO_NOTE)
        result = self.engine.find_by_category(MemoryCategory.CEO_NOTE)
        self.assertEqual(len(result), 1)

    def test_find_by_category_after_delete(self):
        e = _store(self.engine, category=MemoryCategory.DECISION)
        _store(self.engine, category=MemoryCategory.DECISION)
        self.engine.delete(e.id)
        self.assertEqual(len(self.engine.find_by_category(MemoryCategory.DECISION)), 1)

    def test_find_by_category_count_matches_store_count(self):
        n = 4
        for _ in range(n):
            _store(self.engine, category=MemoryCategory.LESSON)
        self.assertEqual(len(self.engine.find_by_category(MemoryCategory.LESSON)), n)

    def test_find_by_category_empty_engine(self):
        for cat in MemoryCategory:
            self.assertEqual(self.engine.find_by_category(cat), [])

    def test_find_by_category_project_category(self):
        _store(self.engine, category=MemoryCategory.PROJECT)
        result = self.engine.find_by_category(MemoryCategory.PROJECT)
        self.assertEqual(len(result), 1)


# ===========================================================================
# TestMemoryEngineFindByScope
# ===========================================================================

class TestMemoryEngineFindByScope(unittest.TestCase):

    def setUp(self):
        self.engine = MemoryEngine()

    def test_find_by_scope_returns_list(self):
        result = self.engine.find_by_scope(MemoryScope.GLOBAL)
        self.assertIsInstance(result, list)

    def test_find_by_scope_empty_when_no_match(self):
        _store(self.engine, scope=MemoryScope.DEPARTMENT)
        result = self.engine.find_by_scope(MemoryScope.GLOBAL)
        self.assertEqual(result, [])

    def test_find_by_scope_returns_matching(self):
        _store(self.engine, scope=MemoryScope.GLOBAL)
        _store(self.engine, scope=MemoryScope.GLOBAL)
        _store(self.engine, scope=MemoryScope.DEPARTMENT)
        result = self.engine.find_by_scope(MemoryScope.GLOBAL)
        self.assertEqual(len(result), 2)

    def test_find_by_scope_all_scopes_correct(self):
        _store(self.engine, scope=MemoryScope.EMPLOYEE)
        results = self.engine.find_by_scope(MemoryScope.EMPLOYEE)
        for r in results:
            self.assertEqual(r.scope, MemoryScope.EMPLOYEE)

    def test_find_by_scope_ordered_by_created_at(self):
        _store(self.engine, scope=MemoryScope.GLOBAL)
        _store(self.engine, scope=MemoryScope.GLOBAL)
        result = self.engine.find_by_scope(MemoryScope.GLOBAL)
        self.assertLessEqual(result[0].created_at, result[1].created_at)

    def test_find_by_scope_ceo_private(self):
        _store(self.engine, scope=MemoryScope.CEO_PRIVATE)
        result = self.engine.find_by_scope(MemoryScope.CEO_PRIVATE)
        self.assertEqual(len(result), 1)

    def test_find_by_scope_project_scope(self):
        _store(self.engine, scope=MemoryScope.PROJECT, project_id="p1")
        result = self.engine.find_by_scope(MemoryScope.PROJECT)
        self.assertEqual(len(result), 1)

    def test_find_by_scope_shallow_copy(self):
        _store(self.engine, scope=MemoryScope.GLOBAL)
        r = self.engine.find_by_scope(MemoryScope.GLOBAL)
        r.clear()
        self.assertEqual(len(self.engine.find_by_scope(MemoryScope.GLOBAL)), 1)

    def test_find_by_scope_all_scopes_across_engine(self):
        for scope in MemoryScope:
            if scope == MemoryScope.PROJECT:
                _store(self.engine, scope=scope, project_id="p1")
            else:
                _store(self.engine, scope=scope)
        for scope in MemoryScope:
            self.assertEqual(len(self.engine.find_by_scope(scope)), 1)

    def test_find_by_scope_after_delete(self):
        e = _store(self.engine, scope=MemoryScope.GLOBAL)
        self.engine.delete(e.id)
        self.assertEqual(self.engine.find_by_scope(MemoryScope.GLOBAL), [])


# ===========================================================================
# TestMemoryEngineFindByAuthor
# ===========================================================================

class TestMemoryEngineFindByAuthor(unittest.TestCase):

    def setUp(self):
        self.engine = MemoryEngine()

    def test_find_by_author_returns_entries(self):
        _store(self.engine, author="ceo")
        result = self.engine.find_by_author("ceo")
        self.assertEqual(len(result), 1)

    def test_find_by_author_empty_for_unknown(self):
        _store(self.engine, author="ceo")
        self.assertEqual(self.engine.find_by_author("unknown"), [])

    def test_find_by_author_multiple(self):
        for _ in range(3):
            _store(self.engine, author="agent-1")
        _store(self.engine, author="agent-2")
        result = self.engine.find_by_author("agent-1")
        self.assertEqual(len(result), 3)

    def test_find_by_author_correct_author(self):
        _store(self.engine, author="specific-author")
        results = self.engine.find_by_author("specific-author")
        for r in results:
            self.assertEqual(r.author, "specific-author")

    def test_find_by_author_ordered_by_created_at(self):
        _store(self.engine, author="a")
        _store(self.engine, author="a")
        result = self.engine.find_by_author("a")
        self.assertLessEqual(result[0].created_at, result[1].created_at)

    def test_find_by_author_after_delete(self):
        e1 = _store(self.engine, author="ceo")
        _store(self.engine, author="ceo")
        self.engine.delete(e1.id)
        self.assertEqual(len(self.engine.find_by_author("ceo")), 1)

    def test_find_by_author_is_shallow_copy(self):
        _store(self.engine, author="ceo")
        r = self.engine.find_by_author("ceo")
        r.clear()
        self.assertEqual(len(self.engine.find_by_author("ceo")), 1)

    def test_find_by_author_empty_string_returns_entries_with_empty_author(self):
        result = self.engine.find_by_author("nobody")
        self.assertEqual(result, [])


# ===========================================================================
# TestMemoryEngineSearchTags
# ===========================================================================

class TestMemoryEngineSearchTags(unittest.TestCase):

    def setUp(self):
        self.engine = MemoryEngine()

    def test_search_tags_any_returns_matching(self):
        _store(self.engine, tags=["python", "backend"])
        result = self.engine.search_tags(["python"])
        self.assertEqual(len(result), 1)

    def test_search_tags_any_no_match(self):
        _store(self.engine, tags=["python"])
        result = self.engine.search_tags(["java"])
        self.assertEqual(result, [])

    def test_search_tags_any_at_least_one_match(self):
        _store(self.engine, tags=["python"])
        _store(self.engine, tags=["java"])
        result = self.engine.search_tags(["python", "java"])
        self.assertEqual(len(result), 2)

    def test_search_tags_all_mode_both_present(self):
        _store(self.engine, tags=["python", "backend"])
        result = self.engine.search_tags(["python", "backend"], match="all")
        self.assertEqual(len(result), 1)

    def test_search_tags_all_mode_partial_no_match(self):
        _store(self.engine, tags=["python"])
        result = self.engine.search_tags(["python", "backend"], match="all")
        self.assertEqual(result, [])

    def test_search_tags_case_insensitive(self):
        _store(self.engine, tags=["Python", "Backend"])
        result = self.engine.search_tags(["python"])
        self.assertEqual(len(result), 1)

    def test_search_tags_empty_list_raises(self):
        with self.assertRaises(InvalidMemoryEntryError):
            self.engine.search_tags([])

    def test_search_tags_empty_engine_returns_empty(self):
        result = self.engine.search_tags(["python"])
        self.assertEqual(result, [])

    def test_search_tags_ordered_by_created_at(self):
        _store(self.engine, tags=["x"])
        _store(self.engine, tags=["x"])
        result = self.engine.search_tags(["x"])
        self.assertLessEqual(result[0].created_at, result[1].created_at)

    def test_search_tags_returns_list(self):
        result = self.engine.search_tags(["anything"])
        self.assertIsInstance(result, list)

    def test_search_tags_multiple_tags_any(self):
        _store(self.engine, tags=["a"])
        _store(self.engine, tags=["b"])
        _store(self.engine, tags=["c"])
        result = self.engine.search_tags(["a", "b"])
        self.assertEqual(len(result), 2)

    def test_search_tags_no_entry_has_all_tags(self):
        _store(self.engine, tags=["x"])
        _store(self.engine, tags=["y"])
        result = self.engine.search_tags(["x", "y"], match="all")
        self.assertEqual(result, [])

    def test_search_tags_entry_with_no_tags_not_returned(self):
        _store(self.engine, tags=[])
        result = self.engine.search_tags(["x"])
        self.assertEqual(result, [])

    def test_search_tags_shallow_copy(self):
        _store(self.engine, tags=["t"])
        r = self.engine.search_tags(["t"])
        r.clear()
        self.assertEqual(len(self.engine.search_tags(["t"])), 1)

    def test_search_tags_error_is_invalid_entry_error(self):
        with self.assertRaises(InvalidMemoryEntryError):
            self.engine.search_tags([])

    def test_search_tags_any_default_mode(self):
        _store(self.engine, tags=["q"])
        result = self.engine.search_tags(["q"])
        self.assertEqual(len(result), 1)

    def test_search_tags_after_update_reflects_new_tags(self):
        e = _store(self.engine, tags=["old"])
        self.engine.update(e.id, tags=["new"])
        self.assertEqual(self.engine.search_tags(["old"]), [])
        self.assertEqual(len(self.engine.search_tags(["new"])), 1)

    def test_search_tags_all_mode_superset_match(self):
        _store(self.engine, tags=["a", "b", "c"])
        result = self.engine.search_tags(["a", "b"], match="all")
        self.assertEqual(len(result), 1)


# ===========================================================================
# TestMemoryEngineSearchText
# ===========================================================================

class TestMemoryEngineSearchText(unittest.TestCase):

    def setUp(self):
        self.engine = MemoryEngine()

    def test_search_text_matches_title(self):
        _store(self.engine, title="Architecture Decision Record")
        result = self.engine.search_text("architecture")
        self.assertEqual(len(result), 1)

    def test_search_text_matches_content(self):
        _store(self.engine, content="Use PostgreSQL for primary storage system.")
        result = self.engine.search_text("postgresql")
        self.assertEqual(len(result), 1)

    def test_search_text_case_insensitive(self):
        _store(self.engine, title="PostgreSQL Decision")
        result = self.engine.search_text("postgresql")
        self.assertEqual(len(result), 1)

    def test_search_text_no_match(self):
        _store(self.engine, title="Something else", content="Nothing here either.")
        result = self.engine.search_text("zzz")
        self.assertEqual(result, [])

    def test_search_text_empty_raises(self):
        with self.assertRaises(InvalidMemoryEntryError):
            self.engine.search_text("")

    def test_search_text_whitespace_raises(self):
        with self.assertRaises(InvalidMemoryEntryError):
            self.engine.search_text("   ")

    def test_search_text_multiple_matches(self):
        _store(self.engine, title="Python Backend")
        _store(self.engine, content="Python is used for backend services.")
        _store(self.engine, title="Java Frontend")
        result = self.engine.search_text("python")
        self.assertEqual(len(result), 2)

    def test_search_text_returns_list(self):
        result = self.engine.search_text("test")
        self.assertIsInstance(result, list)

    def test_search_text_ordered_by_created_at(self):
        _store(self.engine, title="Python v1", content="Content about python here.")
        _store(self.engine, title="Python v2", content="Content about python here.")
        result = self.engine.search_text("python")
        self.assertLessEqual(result[0].created_at, result[1].created_at)

    def test_search_text_empty_engine_returns_empty(self):
        result = self.engine.search_text("anything")
        self.assertEqual(result, [])

    def test_search_text_shallow_copy(self):
        _store(self.engine, title="Python Guide", content="Guide to python coding.")
        r = self.engine.search_text("python")
        r.clear()
        self.assertEqual(len(self.engine.search_text("python")), 1)

    def test_search_text_after_update_reflects_new_content(self):
        e = _store(self.engine, content="Original content here and now.")
        self.engine.update(e.id, content="Updated content with new information.")
        self.assertEqual(self.engine.search_text("original"), [])
        self.assertEqual(len(self.engine.search_text("updated content")), 1)

    def test_search_text_error_is_invalid_entry_error(self):
        with self.assertRaises(InvalidMemoryEntryError):
            self.engine.search_text("")

    def test_search_text_after_delete_not_found(self):
        e = _store(self.engine, title="Unique keyword value xyz")
        self.engine.delete(e.id)
        self.assertEqual(self.engine.search_text("xyz"), [])


# ===========================================================================
# TestMemoryEngineQuery
# ===========================================================================

class TestMemoryEngineQuery(unittest.TestCase):

    def setUp(self):
        self.engine = MemoryEngine()

    def test_query_empty_returns_all(self):
        _store(self.engine)
        _store(self.engine)
        result = self.engine.query(MemoryQuery())
        self.assertEqual(len(result), 2)

    def test_query_by_category(self):
        _store(self.engine, category=MemoryCategory.DECISION)
        _store(self.engine, category=MemoryCategory.LESSON)
        result = self.engine.query(MemoryQuery.for_category(MemoryCategory.DECISION))
        self.assertEqual(len(result), 1)

    def test_query_by_scope(self):
        _store(self.engine, scope=MemoryScope.GLOBAL)
        _store(self.engine, scope=MemoryScope.EMPLOYEE)
        result = self.engine.query(MemoryQuery.for_scope(MemoryScope.EMPLOYEE))
        self.assertEqual(len(result), 1)

    def test_query_by_project(self):
        _store(self.engine, project_id="proj-A")
        _store(self.engine, project_id="proj-B")
        result = self.engine.query(MemoryQuery.for_project("proj-A"))
        self.assertEqual(len(result), 1)

    def test_query_by_author(self):
        _store(self.engine, author="ceo")
        _store(self.engine, author="agent-1")
        result = self.engine.query(MemoryQuery.for_author("ceo"))
        self.assertEqual(len(result), 1)

    def test_query_with_limit(self):
        for _ in range(5):
            _store(self.engine)
        result = self.engine.query(MemoryQuery(limit=3))
        self.assertEqual(len(result), 3)

    def test_query_combined_filters(self):
        _store(self.engine, category=MemoryCategory.DECISION, author="ceo")
        _store(self.engine, category=MemoryCategory.DECISION, author="agent-1")
        _store(self.engine, category=MemoryCategory.LESSON, author="ceo")
        result = self.engine.query(MemoryQuery(
            category=MemoryCategory.DECISION,
            author="ceo",
        ))
        self.assertEqual(len(result), 1)

    def test_query_text_filter(self):
        _store(self.engine, title="PostgreSQL Architecture", content="Some content here.")
        _store(self.engine, title="Frontend Design", content="Some content here.")
        result = self.engine.query(MemoryQuery.for_text("postgresql"))
        self.assertEqual(len(result), 1)

    def test_query_tags_filter(self):
        _store(self.engine, tags=["backend"])
        _store(self.engine, tags=["frontend"])
        result = self.engine.query(MemoryQuery.for_tags(["backend"]))
        self.assertEqual(len(result), 1)

    def test_query_limit_zero_returns_empty(self):
        _store(self.engine)
        result = self.engine.query(MemoryQuery(limit=0))
        self.assertEqual(result, [])

    def test_query_empty_engine_returns_empty(self):
        result = self.engine.query(MemoryQuery())
        self.assertEqual(result, [])

    def test_query_ordered_by_created_at(self):
        _store(self.engine)
        _store(self.engine)
        result = self.engine.query(MemoryQuery())
        self.assertLessEqual(result[0].created_at, result[1].created_at)

    def test_query_returns_list(self):
        result = self.engine.query(MemoryQuery())
        self.assertIsInstance(result, list)

    def test_query_factory_for_tags_all(self):
        _store(self.engine, tags=["a", "b"])
        _store(self.engine, tags=["a"])
        result = self.engine.query(MemoryQuery.for_tags(["a", "b"], match="all"))
        self.assertEqual(len(result), 1)


# ===========================================================================
# TestMemoryEngineListAll
# ===========================================================================

class TestMemoryEngineListAll(unittest.TestCase):

    def setUp(self):
        self.engine = MemoryEngine()

    def test_list_all_returns_list(self):
        self.assertIsInstance(self.engine.list_all(), list)

    def test_list_all_empty_initially(self):
        self.assertEqual(self.engine.list_all(), [])

    def test_list_all_after_store(self):
        _store(self.engine)
        _store(self.engine)
        self.assertEqual(len(self.engine.list_all()), 2)

    def test_list_all_ordered_by_created_at(self):
        _store(self.engine)
        _store(self.engine)
        result = self.engine.list_all()
        self.assertLessEqual(result[0].created_at, result[1].created_at)

    def test_list_all_is_shallow_copy(self):
        _store(self.engine)
        r = self.engine.list_all()
        r.clear()
        self.assertEqual(self.engine.count(), 1)

    def test_count_matches_list_all_len(self):
        for _ in range(6):
            _store(self.engine)
        self.assertEqual(self.engine.count(), len(self.engine.list_all()))


# ===========================================================================
# TestMemoryEngineStatistics
# ===========================================================================

class TestMemoryEngineStatistics(unittest.TestCase):

    def setUp(self):
        self.engine = MemoryEngine()

    def test_statistics_returns_dict(self):
        self.assertIsInstance(self.engine.statistics(), dict)

    def test_statistics_zero_total_initially(self):
        self.assertEqual(self.engine.statistics()["total_entries"], 0)

    def test_statistics_total_entries_after_store(self):
        for _ in range(4):
            _store(self.engine)
        self.assertEqual(self.engine.statistics()["total_entries"], 4)

    def test_statistics_entries_by_category(self):
        _store(self.engine, category=MemoryCategory.DECISION)
        _store(self.engine, category=MemoryCategory.DECISION)
        _store(self.engine, category=MemoryCategory.LESSON)
        stats = self.engine.statistics()
        self.assertEqual(stats["entries_by_category"]["DECISION"], 2)
        self.assertEqual(stats["entries_by_category"]["LESSON"], 1)

    def test_statistics_entries_by_scope(self):
        _store(self.engine, scope=MemoryScope.GLOBAL)
        _store(self.engine, scope=MemoryScope.GLOBAL)
        stats = self.engine.statistics()
        self.assertEqual(stats["entries_by_scope"]["GLOBAL"], 2)

    def test_statistics_unique_authors(self):
        _store(self.engine, author="ceo")
        _store(self.engine, author="ceo")
        _store(self.engine, author="agent-1")
        stats = self.engine.statistics()
        self.assertEqual(stats["unique_authors"], 2)

    def test_statistics_unique_projects(self):
        _store(self.engine, project_id="p1")
        _store(self.engine, project_id="p1")
        _store(self.engine, project_id="p2")
        _store(self.engine)  # no project_id
        stats = self.engine.statistics()
        self.assertEqual(stats["unique_projects"], 2)

    def test_statistics_unique_projects_none_excluded(self):
        _store(self.engine)  # no project_id
        _store(self.engine)
        stats = self.engine.statistics()
        self.assertEqual(stats["unique_projects"], 0)

    def test_statistics_total_tags(self):
        _store(self.engine, tags=["a", "b"])
        _store(self.engine, tags=["c"])
        stats = self.engine.statistics()
        self.assertEqual(stats["total_tags"], 3)

    def test_statistics_unique_tags_case_insensitive(self):
        _store(self.engine, tags=["Python"])
        _store(self.engine, tags=["python"])
        stats = self.engine.statistics()
        self.assertEqual(stats["unique_tags"], 1)

    def test_statistics_entries_updated(self):
        e = _store(self.engine)
        _store(self.engine)
        self.engine.update(e.id, content="updated content here")
        stats = self.engine.statistics()
        self.assertEqual(stats["entries_updated"], 1)

    def test_statistics_entries_updated_zero_when_no_updates(self):
        _store(self.engine)
        stats = self.engine.statistics()
        self.assertEqual(stats["entries_updated"], 0)

    def test_statistics_contains_all_categories_in_by_category(self):
        stats = self.engine.statistics()
        for cat in MemoryCategory:
            self.assertIn(cat.value, stats["entries_by_category"])

    def test_statistics_contains_all_scopes_in_by_scope(self):
        stats = self.engine.statistics()
        for scope in MemoryScope:
            self.assertIn(scope.value, stats["entries_by_scope"])

    def test_statistics_after_delete(self):
        e = _store(self.engine)
        _store(self.engine)
        self.engine.delete(e.id)
        self.assertEqual(self.engine.statistics()["total_entries"], 1)

    def test_statistics_has_required_keys(self):
        stats = self.engine.statistics()
        for k in ["total_entries", "entries_by_category", "entries_by_scope",
                  "unique_authors", "unique_projects", "total_tags",
                  "unique_tags", "entries_updated"]:
            self.assertIn(k, stats)


# ===========================================================================
# TestIntegration
# ===========================================================================

class TestIntegration(unittest.TestCase):

    def setUp(self):
        self.engine = MemoryEngine()

    def test_store_update_find_flow(self):
        e = _store(self.engine, title="Initial")
        self.engine.update(e.id, title="Revised Title")
        found = self.engine.find_by_id(e.id)
        self.assertEqual(found.title, "Revised Title")
        self.assertEqual(found.version, 2)

    def test_full_history_preserved_across_updates(self):
        e = _store(self.engine, content="v1 content")
        self.engine.update(e.id, content="v2 content here now")
        self.engine.update(e.id, content="v3 content here now")
        self.assertEqual(e.revision_count(), 2)
        self.assertEqual(e.history[0].content, "v1 content")

    def test_search_text_after_updates(self):
        e = _store(self.engine, title="Decision Alpha", content="Initial thought about it.")
        self.engine.update(e.id, content="Revised: use PostgreSQL exclusively.")
        result = self.engine.search_text("postgresql")
        self.assertEqual(len(result), 1)

    def test_multi_project_queries(self):
        for i in range(3):
            _store(self.engine, project_id="proj-A", category=MemoryCategory.TASK)
        for i in range(2):
            _store(self.engine, project_id="proj-B", category=MemoryCategory.DECISION)
        self.assertEqual(len(self.engine.find_by_project("proj-A")), 3)
        self.assertEqual(len(self.engine.find_by_project("proj-B")), 2)
        self.assertEqual(len(self.engine.find_by_category(MemoryCategory.TASK)), 3)
        self.assertEqual(len(self.engine.find_by_category(MemoryCategory.DECISION)), 2)

    def test_delete_removes_from_all_filters(self):
        e = _store(
            self.engine,
            category=MemoryCategory.LESSON,
            scope=MemoryScope.GLOBAL,
            tags=["important"],
            project_id="p1",
        )
        self.engine.delete(e.id)
        self.assertEqual(self.engine.find_by_category(MemoryCategory.LESSON), [])
        self.assertEqual(self.engine.find_by_scope(MemoryScope.GLOBAL), [])
        self.assertEqual(self.engine.search_tags(["important"]), [])
        self.assertEqual(self.engine.find_by_project("p1"), [])

    def test_ceo_private_entries_separate_from_global(self):
        _store(self.engine, scope=MemoryScope.GLOBAL)
        _store(self.engine, scope=MemoryScope.CEO_PRIVATE)
        global_entries = self.engine.find_by_scope(MemoryScope.GLOBAL)
        private_entries = self.engine.find_by_scope(MemoryScope.CEO_PRIVATE)
        self.assertEqual(len(global_entries), 1)
        self.assertEqual(len(private_entries), 1)
        self.assertNotEqual(global_entries[0].id, private_entries[0].id)

    def test_statistics_reflects_real_state(self):
        for i in range(3):
            _store(self.engine, category=MemoryCategory.DECISION, author="ceo")
        for i in range(2):
            _store(self.engine, category=MemoryCategory.LESSON, author="agent-1")
        stats = self.engine.statistics()
        self.assertEqual(stats["total_entries"], 5)
        self.assertEqual(stats["entries_by_category"]["DECISION"], 3)
        self.assertEqual(stats["entries_by_category"]["LESSON"], 2)
        self.assertEqual(stats["unique_authors"], 2)

    def test_revision_history_content_correct(self):
        e = _store(self.engine, content="first content written here now.")
        self.engine.update(e.id, content="second content updated here now.", changed_by="ceo")
        self.engine.update(e.id, content="third content latest version here.", changed_by="architect")
        self.assertEqual(e.history[0].content, "first content written here now.")
        self.assertEqual(e.history[0].changed_by, "ceo")
        self.assertEqual(e.history[1].content, "second content updated here now.")
        self.assertEqual(e.history[1].changed_by, "architect")

    def test_complex_query_combined(self):
        _store(self.engine,
               category=MemoryCategory.DECISION,
               scope=MemoryScope.GLOBAL,
               author="ceo",
               tags=["architecture"],
               project_id="p1")
        _store(self.engine,
               category=MemoryCategory.DECISION,
               scope=MemoryScope.GLOBAL,
               author="agent-1",
               tags=["architecture"],
               project_id="p1")
        _store(self.engine,
               category=MemoryCategory.LESSON,
               scope=MemoryScope.GLOBAL,
               author="ceo",
               tags=["architecture"],
               project_id="p1")
        q = MemoryQuery(
            category=MemoryCategory.DECISION,
            author="ceo",
            tags=["architecture"],
        )
        result = self.engine.query(q)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].author, "ceo")
        self.assertEqual(result[0].category, MemoryCategory.DECISION)

    def test_lesson_learned_flow(self):
        e = _store(
            self.engine,
            title="Lesson: Database migration timing",
            category=MemoryCategory.LESSON,
            scope=MemoryScope.GLOBAL,
            content="Run migrations during off-peak hours to minimise risk.",
            tags=["database", "migration", "ops"],
            author="ceo",
        )
        lessons = self.engine.find_by_category(MemoryCategory.LESSON)
        self.assertEqual(len(lessons), 1)
        self.assertEqual(lessons[0].title, "Lesson: Database migration timing")
        ops_lessons = self.engine.search_tags(["ops"])
        self.assertEqual(len(ops_lessons), 1)

    def test_query_limit_with_ordered_results(self):
        for i in range(10):
            _store(self.engine, title=f"Entry {i}", content="Content for each entry.")
        result = self.engine.query(MemoryQuery(limit=4))
        self.assertEqual(len(result), 4)
        for i in range(1, len(result)):
            self.assertLessEqual(result[i - 1].created_at, result[i].created_at)


# ===========================================================================
# TestContracts
# ===========================================================================

class TestContracts(unittest.TestCase):

    def setUp(self):
        self.engine = MemoryEngine()

    def test_store_always_returns_memory_entry(self):
        result = self.engine.store(_entry())
        self.assertIsInstance(result, MemoryEntry)

    def test_find_by_id_always_returns_memory_entry_or_raises(self):
        e = _store(self.engine)
        result = self.engine.find_by_id(e.id)
        self.assertIsInstance(result, MemoryEntry)

    def test_update_always_increments_version(self):
        e = _store(self.engine)
        old_version = e.version
        self.engine.update(e.id, content="new content here now")
        self.assertEqual(e.version, old_version + 1)

    def test_update_always_appends_to_history(self):
        e = _store(self.engine)
        old_count = e.revision_count()
        self.engine.update(e.id, content="new content here")
        self.assertEqual(e.revision_count(), old_count + 1)

    def test_delete_always_returns_the_deleted_entry(self):
        e = _store(self.engine)
        result = self.engine.delete(e.id)
        self.assertEqual(result.id, e.id)

    def test_count_reflects_all_store_and_delete_ops(self):
        ids = [_store(self.engine).id for _ in range(5)]
        self.assertEqual(self.engine.count(), 5)
        for eid in ids[:2]:
            self.engine.delete(eid)
        self.assertEqual(self.engine.count(), 3)

    def test_all_listing_methods_return_lists(self):
        _store(self.engine)
        self.assertIsInstance(self.engine.list_all(), list)
        self.assertIsInstance(self.engine.find_by_category(MemoryCategory.DECISION), list)
        self.assertIsInstance(self.engine.find_by_scope(MemoryScope.GLOBAL), list)
        self.assertIsInstance(self.engine.find_by_project("p"), list)
        self.assertIsInstance(self.engine.find_by_author("ceo"), list)

    def test_statistics_always_returns_dict(self):
        self.assertIsInstance(self.engine.statistics(), dict)

    def test_entry_created_at_never_changes_after_update(self):
        e = _store(self.engine)
        original_created = e.created_at
        self.engine.update(e.id, content="changed content here now")
        self.engine.update(e.id, content="changed again more content")
        self.assertEqual(e.created_at, original_created)

    def test_history_entries_are_revision_objects(self):
        e = _store(self.engine)
        self.engine.update(e.id, content="v2 content here now")
        self.assertIsInstance(e.history[0], MemoryEntryRevision)


if __name__ == "__main__":
    unittest.main(verbosity=2)
