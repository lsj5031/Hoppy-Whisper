"""Tests for history palette UI (E5.2)."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.history import HistoryDAO, HistoryPalette


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """Create a temporary database path."""
    return tmp_path / "test_history.db"


@pytest.fixture
def dao(temp_db: Path) -> HistoryDAO:
    """Create a DAO instance with sample data."""
    dao = HistoryDAO(temp_db, retention_days=90)
    dao.open()

    # Insert sample data with time delays to ensure proper ordering
    dao.insert("Hello world", "standard", duration_ms=1000)
    time.sleep(1.1)
    dao.insert("Python programming", "standard", duration_ms=1500)
    time.sleep(1.1)
    dao.insert("Machine learning is fun", "standard", duration_ms=2000)
    time.sleep(1.1)
    dao.insert("Open source software", "standard", duration_ms=1200)
    time.sleep(1.1)
    dao.insert("Test driven development", "standard", duration_ms=1800)

    yield dao
    dao.close()


def test_palette_creation(dao: HistoryDAO):
    """Test that palette can be created."""
    on_copy = MagicMock()
    on_paste = MagicMock()

    palette = HistoryPalette(dao=dao, on_copy=on_copy, on_paste=on_paste)

    assert palette is not None
    assert palette._dao is dao
    assert palette._on_copy is on_copy
    assert palette._on_paste is on_paste


def test_palette_callbacks_stored(dao: HistoryDAO):
    """Test that callbacks are stored correctly."""
    copy_called = []
    paste_called = []

    def on_copy(text: str):
        copy_called.append(text)

    def on_paste(text: str):
        paste_called.append(text)

    palette = HistoryPalette(dao=dao, on_copy=on_copy, on_paste=on_paste)

    # Verify callbacks work
    palette._on_copy("test text")
    assert len(copy_called) == 1
    assert copy_called[0] == "test text"

    palette._on_paste("paste test")
    assert len(paste_called) == 1
    assert paste_called[0] == "paste test"


def test_dao_integration(dao: HistoryDAO):
    """Test that palette can access DAO methods."""
    on_copy = MagicMock()
    on_paste = MagicMock()

    palette = HistoryPalette(dao=dao, on_copy=on_copy, on_paste=on_paste)

    # Verify DAO is accessible
    recent = palette._dao.get_recent(limit=5)
    assert len(recent) == 5

    # Verify search works
    results = palette._dao.search("python")
    assert len(results) == 1
    assert "python" in results[0].text.lower()


def test_search_functionality(dao: HistoryDAO):
    """Test search returns correct results."""
    on_copy = MagicMock()
    on_paste = MagicMock()

    palette = HistoryPalette(dao=dao, on_copy=on_copy, on_paste=on_paste)

    # Search for specific term
    results = palette._dao.search("machine")
    assert len(results) == 1
    assert "Machine learning" in results[0].text

    # Search for another term
    results = palette._dao.search("development")
    assert len(results) == 1
    assert "Test driven development" in results[0].text


def test_recent_utterances(dao: HistoryDAO):
    """Test retrieving recent utterances."""
    on_copy = MagicMock()
    on_paste = MagicMock()

    palette = HistoryPalette(dao=dao, on_copy=on_copy, on_paste=on_paste)

    # Get recent utterances
    recent = palette._dao.get_recent(limit=3)
    assert len(recent) == 3

    # Most recent should be "Test driven development"
    assert recent[0].text == "Test driven development"


def test_empty_database():
    """Test palette with empty database."""
    dao = HistoryDAO(Path(":memory:"), retention_days=90)
    dao.open()

    on_copy = MagicMock()
    on_paste = MagicMock()

    palette = HistoryPalette(dao=dao, on_copy=on_copy, on_paste=on_paste)

    # Should not crash with empty database
    recent = palette._dao.get_recent(limit=10)
    assert len(recent) == 0

    results = palette._dao.search("anything")
    assert len(results) == 0

    dao.close()


def test_long_text_handling(dao: HistoryDAO):
    """Test handling of long text entries."""
    long_text = "a" * 200  # Very long text
    time.sleep(1.1)  # Ensure it's newer than fixture data
    dao.insert(long_text, "standard", duration_ms=3000)

    on_copy = MagicMock()
    on_paste = MagicMock()

    palette = HistoryPalette(dao=dao, on_copy=on_copy, on_paste=on_paste)

    # Should be able to retrieve long text
    recent = palette._dao.get_recent(limit=1)
    assert len(recent) == 1
    assert recent[0].text == long_text


def test_special_characters_in_search(dao: HistoryDAO):
    """Test search with special characters."""
    dao.insert("email@example.com", "standard", duration_ms=1000)
    dao.insert("https://github.com/test", "standard", duration_ms=1000)
    dao.insert("C:\\Windows\\System32", "standard", duration_ms=1000)

    on_copy = MagicMock()
    on_paste = MagicMock()

    palette = HistoryPalette(dao=dao, on_copy=on_copy, on_paste=on_paste)

    # Search for email
    results = palette._dao.search("email")
    assert len(results) == 1
    assert "email@example.com" in results[0].text

    # Search for URL
    results = palette._dao.search("github")
    assert len(results) == 1
    assert "github" in results[0].text


def test_multiple_search_terms(dao: HistoryDAO):
    """Test search with multiple terms."""
    on_copy = MagicMock()
    on_paste = MagicMock()

    palette = HistoryPalette(dao=dao, on_copy=on_copy, on_paste=on_paste)

    # Search for multiple terms
    results = palette._dao.search("test driven")
    assert len(results) == 1
    assert "Test driven development" in results[0].text


def test_case_insensitive_search(dao: HistoryDAO):
    """Test that search is case-insensitive."""
    on_copy = MagicMock()
    on_paste = MagicMock()

    palette = HistoryPalette(dao=dao, on_copy=on_copy, on_paste=on_paste)

    # Search with different cases
    results_lower = palette._dao.search("python")
    results_upper = palette._dao.search("PYTHON")
    results_mixed = palette._dao.search("PyThOn")

    assert len(results_lower) == 1
    assert len(results_upper) == 1
    assert len(results_mixed) == 1
    assert results_lower[0].text == results_upper[0].text == results_mixed[0].text
