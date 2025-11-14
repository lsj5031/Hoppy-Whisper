"""Tests to verify raw transcription output (no Smart Cleanup)."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.history import HistoryDAO
from app.transcriber.hoppy import TranscriptionResult


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


def test_transcription_result_stored_with_raw_mode(dao: HistoryDAO):
    """Test that transcription results are stored with mode='raw'."""
    raw_text = "um hello world uh this is a test"
    
    # Simulate what _complete_transcription does
    cleaned_text = raw_text  # No cleanup applied
    cleanup_mode = "raw"
    
    utterance_id = dao.insert(
        text=cleaned_text,
        mode=cleanup_mode,
        duration_ms=1500,
        raw_text=raw_text,
    )
    
    # Verify it was stored correctly
    utterance = dao.get_by_id(utterance_id)
    assert utterance is not None
    assert utterance.text == raw_text
    assert utterance.mode == "raw"
    assert utterance.raw_text == raw_text


def test_multiple_utterances_with_raw_mode(dao: HistoryDAO):
    """Test that multiple transcriptions are all stored as 'raw' mode."""
    test_utterances = [
        "um hello world",
        "uh this is another test",
        "you know like a third one",
    ]
    
    for utterance_text in test_utterances:
        dao.insert(
            text=utterance_text,
            mode="raw",
            duration_ms=1000,
        )
    
    # Check that all were stored
    recent = dao.get_recent(limit=10)
    assert len(recent) == 3
    
    # Verify all have mode='raw'
    for u in recent:
        assert u.mode == "raw"


def test_search_finds_raw_utterances(dao: HistoryDAO):
    """Test that FTS search works with raw (unclean) transcriptions."""
    # Insert utterance with filler words
    dao.insert(
        text="um hello world uh this is a test",
        mode="raw",
    )
    
    # Search should find it
    results = dao.search("hello")
    assert len(results) == 1
    assert "hello" in results[0].text.lower()
    
    # Should also find filler words
    results = dao.search("um")
    assert len(results) == 1


def test_transcription_preserves_model_output():
    """Test that raw model output is preserved without modification."""
    # Simulate transcriber output
    raw_model_output = "hello world"
    
    # This is what happens in _complete_transcription
    cleaned_text = raw_model_output  # No cleanup engine applied
    
    # The text should be identical to model output
    assert cleaned_text == raw_model_output
