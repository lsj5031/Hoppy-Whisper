"""Tests for history DAO and SQLite store (E5.1)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from app.history import HistoryDAO


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """Create a temporary database path."""
    return tmp_path / "test_history.db"


@pytest.fixture
def dao(temp_db: Path) -> HistoryDAO:
    """Create a DAO instance with a temporary database."""
    dao = HistoryDAO(temp_db, retention_days=90)
    dao.open()
    yield dao
    dao.close()


def test_dao_opens_and_creates_database(temp_db: Path):
    """Test that DAO creates database file on open."""
    assert not temp_db.exists()
    dao = HistoryDAO(temp_db)
    dao.open()
    assert temp_db.exists()
    dao.close()


def test_insert_utterance(dao: HistoryDAO):
    """Test inserting a new utterance."""
    utterance_id = dao.insert(
        text="Hello, world!",
        mode="standard",
        duration_ms=1500,
        raw_text="hello world",
    )
    assert utterance_id > 0


def test_insert_without_optional_fields(dao: HistoryDAO):
    """Test inserting utterance without duration and raw_text."""
    utterance_id = dao.insert(text="Test utterance", mode="conservative")
    assert utterance_id > 0

    utterance = dao.get_by_id(utterance_id)
    assert utterance is not None
    assert utterance.text == "Test utterance"
    assert utterance.mode == "conservative"
    assert utterance.duration_ms is None
    assert utterance.raw_text is None


def test_get_by_id(dao: HistoryDAO):
    """Test retrieving utterance by ID."""
    utterance_id = dao.insert(
        text="Test message",
        mode="standard",
        duration_ms=2000,
    )

    utterance = dao.get_by_id(utterance_id)
    assert utterance is not None
    assert utterance.id == utterance_id
    assert utterance.text == "Test message"
    assert utterance.mode == "standard"
    assert utterance.duration_ms == 2000
    assert utterance.created_utc > 0


def test_get_by_id_nonexistent(dao: HistoryDAO):
    """Test retrieving nonexistent utterance returns None."""
    utterance = dao.get_by_id(99999)
    assert utterance is None


def test_get_recent(dao: HistoryDAO):
    """Test retrieving recent utterances."""
    dao.insert("First", "standard")
    time.sleep(1.1)
    dao.insert("Second", "standard")
    time.sleep(1.1)
    dao.insert("Third", "standard")

    recent = dao.get_recent(limit=2)
    assert len(recent) == 2
    assert recent[0].text == "Third"
    assert recent[1].text == "Second"


def test_fts_search(dao: HistoryDAO):
    """Test full-text search functionality."""
    dao.insert("The quick brown fox", "standard")
    dao.insert("A lazy dog sleeps", "standard")
    dao.insert("The fox jumps high", "standard")

    results = dao.search("fox")
    assert len(results) == 2
    assert all("fox" in r.text.lower() for r in results)


def test_fts_search_case_insensitive(dao: HistoryDAO):
    """Test FTS search is case-insensitive."""
    dao.insert("Machine Learning is awesome", "standard")

    results_lower = dao.search("machine")
    results_upper = dao.search("MACHINE")
    results_mixed = dao.search("MaChInE")

    assert len(results_lower) == 1
    assert len(results_upper) == 1
    assert len(results_mixed) == 1


def test_fts_search_multiple_terms(dao: HistoryDAO):
    """Test FTS search with multiple terms."""
    dao.insert("Python programming language", "standard")
    dao.insert("JavaScript web development", "standard")
    dao.insert("Python web framework", "standard")

    results = dao.search("python web")
    assert len(results) == 1
    assert results[0].text == "Python web framework"


def test_fts_search_with_limit(dao: HistoryDAO):
    """Test FTS search respects limit parameter."""
    for i in range(10):
        dao.insert(f"Test message number {i}", "standard")

    results = dao.search("test", limit=5)
    assert len(results) == 5


def test_count(dao: HistoryDAO):
    """Test counting utterances."""
    assert dao.count() == 0

    dao.insert("First", "standard")
    assert dao.count() == 1

    dao.insert("Second", "standard")
    dao.insert("Third", "standard")
    assert dao.count() == 3


def test_delete_older_than(dao: HistoryDAO):
    """Test deleting utterances older than specified days."""
    # Insert old utterance by manually manipulating created_utc
    dao.insert("Recent", "standard")
    recent_id = dao._conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Insert an "old" utterance (100 days ago)
    old_timestamp = int(time.time()) - (100 * 86400)
    dao._conn.execute(
        "INSERT INTO utterances (text, created_utc, mode) VALUES (?, ?, ?)",
        ("Old utterance", old_timestamp, "standard"),
    )
    dao._conn.commit()

    assert dao.count() == 2

    deleted = dao.delete_older_than(90)
    assert deleted == 1
    assert dao.count() == 1

    remaining = dao.get_by_id(recent_id)
    assert remaining is not None
    assert remaining.text == "Recent"


def test_apply_retention_policy(dao: HistoryDAO):
    """Test retention policy deletes old utterances."""
    # Insert a recent utterance
    dao.insert("Recent", "standard")

    # Insert an old utterance (100 days ago)
    old_timestamp = int(time.time()) - (100 * 86400)
    dao._conn.execute(
        "INSERT INTO utterances (text, created_utc, mode) VALUES (?, ?, ?)",
        ("Old utterance", old_timestamp, "standard"),
    )
    dao._conn.commit()

    assert dao.count() == 2

    deleted = dao.apply_retention_policy()
    assert deleted == 1
    assert dao.count() == 1


def test_clear_all(dao: HistoryDAO):
    """Test clearing all utterances."""
    dao.insert("First", "standard")
    dao.insert("Second", "standard")
    dao.insert("Third", "standard")

    assert dao.count() == 3

    deleted = dao.clear_all()
    assert deleted == 3
    assert dao.count() == 0


def test_fts_triggers_on_insert(dao: HistoryDAO):
    """Test that FTS index is updated on insert."""
    utterance_id = dao.insert("Searchable text", "standard")

    results = dao.search("searchable")
    assert len(results) == 1
    assert results[0].id == utterance_id


def test_fts_triggers_on_delete(dao: HistoryDAO):
    """Test that FTS index is updated on delete."""
    utterance_id = dao.insert("Will be deleted", "standard")

    results = dao.search("deleted")
    assert len(results) == 1

    dao._conn.execute("DELETE FROM utterances WHERE id = ?", (utterance_id,))
    dao._conn.commit()

    results = dao.search("deleted")
    assert len(results) == 0


def test_dao_raises_if_not_opened():
    """Test that DAO methods raise if database is not opened."""
    dao = HistoryDAO(Path("test.db"))

    with pytest.raises(RuntimeError, match="Database not opened"):
        dao.insert("Test", "standard")

    with pytest.raises(RuntimeError, match="Database not opened"):
        dao.get_recent()

    with pytest.raises(RuntimeError, match="Database not opened"):
        dao.search("test")


def test_multiple_modes(dao: HistoryDAO):
    """Test storing utterances with different cleanup modes."""
    dao.insert("Conservative text", "conservative")
    dao.insert("Standard text", "standard")
    dao.insert("Rewrite text", "rewrite")

    recent = dao.get_recent(limit=10)
    modes = {u.mode for u in recent}
    assert modes == {"conservative", "standard", "rewrite"}


def test_search_returns_most_recent_first(dao: HistoryDAO):
    """Test that search results are ordered by created_utc DESC."""
    dao.insert("First python message", "standard")
    time.sleep(1.1)
    dao.insert("Second python message", "standard")
    time.sleep(1.1)
    dao.insert("Third python message", "standard")

    results = dao.search("python")
    assert len(results) == 3
    assert results[0].text == "Third python message"
    assert results[1].text == "Second python message"
    assert results[2].text == "First python message"


def test_schema_version_stored(temp_db: Path):
    """Test that schema version is stored in metadata table."""
    from app.history import SCHEMA_VERSION

    dao = HistoryDAO(temp_db)
    dao.open()

    cursor = dao._conn.cursor()
    cursor.execute("SELECT value FROM metadata WHERE key = 'schema_version'")
    row = cursor.fetchone()

    assert row is not None
    assert int(row[0]) == SCHEMA_VERSION

    dao.close()


def test_database_persists_after_close(temp_db: Path):
    """Test that data persists after closing and reopening."""
    dao1 = HistoryDAO(temp_db)
    dao1.open()
    dao1.insert("Persistent message", "standard")
    dao1.close()

    dao2 = HistoryDAO(temp_db)
    dao2.open()
    assert dao2.count() == 1
    recent = dao2.get_recent(limit=1)
    assert recent[0].text == "Persistent message"
    dao2.close()
