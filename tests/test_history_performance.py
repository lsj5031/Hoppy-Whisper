"""Performance tests for history search (E5.2)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from app.history import HistoryDAO


@pytest.fixture
def large_dao(tmp_path: Path) -> HistoryDAO:
    """Create a DAO with 1000 sample entries for performance testing."""
    dao = HistoryDAO(tmp_path / "perf_test.db", retention_days=90)
    dao.open()

    # Insert 1000 utterances with varied content
    for i in range(1000):
        text = f"Sample utterance number {i} with some additional text content"
        dao.insert(text, "standard", duration_ms=1000 + i)

    yield dao
    dao.close()


def test_search_latency_small_dataset(large_dao: HistoryDAO):
    """Test that FTS search is fast on 1K rows."""
    # Warm up
    large_dao.search("sample", limit=50)

    # Measure search time
    start = time.perf_counter()
    results = large_dao.search("sample", limit=50)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert len(results) > 0
    # Should be well under 20ms for 1K rows
    assert elapsed_ms < 20, f"Search took {elapsed_ms:.2f}ms, expected <20ms"


def test_get_recent_latency(large_dao: HistoryDAO):
    """Test that get_recent is fast."""
    # Warm up
    large_dao.get_recent(limit=50)

    # Measure time
    start = time.perf_counter()
    results = large_dao.get_recent(limit=50)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert len(results) == 50
    # Should be very fast with indexed query
    assert elapsed_ms < 10, f"get_recent took {elapsed_ms:.2f}ms, expected <10ms"


def test_multiple_searches_consistent(large_dao: HistoryDAO):
    """Test that repeated searches maintain performance."""
    timings = []

    for _ in range(10):
        start = time.perf_counter()
        large_dao.search("number", limit=50)
        elapsed_ms = (time.perf_counter() - start) * 1000
        timings.append(elapsed_ms)

    avg_time = sum(timings) / len(timings)
    max_time = max(timings)

    assert avg_time < 15, f"Average search time {avg_time:.2f}ms, expected <15ms"
    assert max_time < 25, f"Max search time {max_time:.2f}ms, expected <25ms"


def test_search_with_multiple_terms(large_dao: HistoryDAO):
    """Test that multi-term search is still fast."""
    start = time.perf_counter()
    results = large_dao.search("sample utterance number", limit=50)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert len(results) > 0
    assert elapsed_ms < 20, f"Multi-term search took {elapsed_ms:.2f}ms"
