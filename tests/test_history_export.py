"""Tests for history export functionality."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.history import HistoryDAO


@pytest.fixture
def dao(tmp_path: Path) -> HistoryDAO:
    """Provide a HistoryDAO connected to a temp database."""
    db_path = tmp_path / "test.db"
    dao = HistoryDAO(db_path, retention_days=90)
    dao.open()
    yield dao
    dao.close()


def test_export_all_to_dict_empty(dao: HistoryDAO) -> None:
    """Export returns empty list when no utterances exist."""
    result = dao.export_all_to_dict()
    assert result == []


def test_export_all_to_dict_single_utterance(dao: HistoryDAO) -> None:
    """Export returns correct structure for single utterance."""
    dao.insert(
        text="Hello world",
        mode="standard",
        duration_ms=1500,
        raw_text="hello world",
    )

    result = dao.export_all_to_dict()
    assert len(result) == 1

    item = result[0]
    assert item["id"] == 1
    assert item["text"] == "Hello world"
    assert item["mode"] == "standard"
    assert item["duration_ms"] == 1500
    assert item["raw_text"] == "hello world"
    assert isinstance(item["created_utc"], int)


def test_export_all_to_dict_multiple_utterances(dao: HistoryDAO) -> None:
    """Export returns all utterances."""
    id1 = dao.insert(text="First", mode="standard", duration_ms=1000)
    id2 = dao.insert(text="Second", mode="standard", duration_ms=2000)
    id3 = dao.insert(text="Third", mode="standard", duration_ms=3000)

    result = dao.export_all_to_dict()
    assert len(result) == 3

    # All IDs should be present
    ids = {item["id"] for item in result}
    assert ids == {id1, id2, id3}

    # Verify texts are all present
    texts = {item["text"] for item in result}
    assert texts == {"First", "Second", "Third"}


def test_export_all_to_dict_without_optional_fields(dao: HistoryDAO) -> None:
    """Export handles utterances with None optional fields."""
    dao.insert(text="Minimal utterance", mode="conservative")

    result = dao.export_all_to_dict()
    assert len(result) == 1

    item = result[0]
    assert item["text"] == "Minimal utterance"
    assert item["mode"] == "conservative"
    assert item["duration_ms"] is None
    assert item["raw_text"] is None


def test_export_all_includes_all_fields(dao: HistoryDAO) -> None:
    """Export includes all database fields."""
    dao.insert(
        text="Complete record",
        mode="rewrite",
        duration_ms=5000,
        raw_text="complete record",
    )

    result = dao.export_all_to_dict()
    item = result[0]

    required_fields = {"id", "text", "created_utc", "duration_ms", "mode", "raw_text"}
    assert set(item.keys()) == required_fields


def test_export_preserves_unicode(dao: HistoryDAO) -> None:
    """Export correctly handles Unicode text."""
    dao.insert(
        text="Hello 世界 🌍",
        mode="standard",
    )

    result = dao.export_all_to_dict()
    assert result[0]["text"] == "Hello 世界 🌍"


def test_export_large_dataset(dao: HistoryDAO) -> None:
    """Export handles large number of utterances."""
    count = 1000
    for i in range(count):
        dao.insert(text=f"Utterance {i}", mode="standard", duration_ms=i * 10)

    result = dao.export_all_to_dict()
    assert len(result) == count

    # Verify all utterances are present
    texts = {item["text"] for item in result}
    expected_texts = {f"Utterance {i}" for i in range(count)}
    assert texts == expected_texts


def test_export_to_json_serializable(dao: HistoryDAO) -> None:
    """Export data is JSON serializable."""
    dao.insert(
        text="Test utterance",
        mode="standard",
        duration_ms=1234,
        raw_text="test utterance",
    )

    result = dao.export_all_to_dict()

    # Should not raise
    json_str = json.dumps(result, indent=2)
    assert json_str is not None

    # Should be parseable
    parsed = json.loads(json_str)
    assert len(parsed) == 1
    assert parsed[0]["text"] == "Test utterance"


def test_export_dao_not_opened() -> None:
    """Export raises if database not opened."""
    dao = HistoryDAO(Path("dummy.db"))
    with pytest.raises(RuntimeError, match="Database not opened"):
        dao.export_all_to_dict()
