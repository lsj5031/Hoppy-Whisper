"""Tests for performance metrics."""

import time
from pathlib import Path

import pytest

from app.metrics import (
    STARTUP_BUDGET_MS,
    TRANSCRIBE_BUDGET_CPU_MS,
    TRANSCRIBE_BUDGET_GPU_MS,
    MetricEvent,
    PerformanceMetrics,
)


def test_metric_event_creation():
    """Test MetricEvent creation and formatting."""
    event = MetricEvent(
        name="test_operation",
        duration_ms=123.4,
        metadata={"provider": "cpu", "model": "parakeet"},
    )

    assert event.name == "test_operation"
    assert event.duration_ms == 123.4
    assert "provider" in event.metadata
    assert "model" in event.metadata

    log_line = event.to_log_line()
    assert "test_operation" in log_line
    assert "123.4ms" in log_line
    assert "provider=cpu" in log_line


def test_metric_event_budget_check():
    """Test budget checking."""
    event = MetricEvent(name="fast", duration_ms=100.0)
    assert not event.exceeds_budget(200.0)
    assert event.exceeds_budget(50.0)


def test_metrics_disabled_by_default():
    """Test that metrics are disabled by default."""
    metrics = PerformanceMetrics()
    assert not metrics.enabled

    metrics.start("test")
    metrics.stop("test")

    assert len(metrics.get_events()) == 0


def test_metrics_start_stop():
    """Test start/stop timing."""
    metrics = PerformanceMetrics(enabled=True)

    metrics.start("operation")
    time.sleep(0.05)  # 50ms
    event = metrics.stop("operation", provider="test")

    assert event is not None
    assert event.name == "operation"
    assert event.duration_ms >= 45  # Allow some tolerance
    assert event.metadata["provider"] == "test"

    events = metrics.get_events()
    assert len(events) == 1
    assert events[0].name == "operation"


def test_metrics_record_direct():
    """Test direct recording of metrics."""
    metrics = PerformanceMetrics(enabled=True)

    event = metrics.record("transcribe", 450.5, provider="dml", samples="44800")

    assert event.name == "transcribe"
    assert event.duration_ms == 450.5
    assert event.metadata["provider"] == "dml"
    assert event.metadata["samples"] == "44800"

    assert len(metrics.get_events()) == 1


def test_metrics_check_budget():
    """Test budget checking."""
    metrics = PerformanceMetrics(enabled=True)

    # Within budget
    within = metrics.check_budget("fast_op", 100.0, STARTUP_BUDGET_MS)
    assert within

    # Exceeds budget
    exceeds = metrics.check_budget("slow_op", 700.0, TRANSCRIBE_BUDGET_GPU_MS)
    assert not exceeds

    assert len(metrics.get_events()) == 2


def test_metrics_clear():
    """Test clearing metrics."""
    metrics = PerformanceMetrics(enabled=True)

    metrics.record("op1", 100.0)
    metrics.record("op2", 200.0)
    assert len(metrics.get_events()) == 2

    metrics.clear()
    assert len(metrics.get_events()) == 0


def test_metrics_log_file(tmp_path: Path):
    """Test writing metrics to a log file."""
    log_file = tmp_path / "metrics.log"
    metrics = PerformanceMetrics(enabled=True, log_path=log_file)

    metrics.record("test1", 100.0, context="first")
    metrics.record("test2", 200.0, context="second")

    assert log_file.exists()
    content = log_file.read_text()

    assert "test1" in content
    assert "test2" in content
    assert "100.0ms" in content
    assert "200.0ms" in content
    assert "context=first" in content


def test_metrics_multiple_operations():
    """Test recording multiple operations."""
    metrics = PerformanceMetrics(enabled=True)

    metrics.start("startup")
    time.sleep(0.01)
    metrics.stop("startup")

    metrics.start("transcribe")
    time.sleep(0.02)
    metrics.stop("transcribe", provider="cpu")

    events = metrics.get_events()
    assert len(events) == 2
    assert events[0].name == "startup"
    assert events[1].name == "transcribe"
    assert events[1].metadata["provider"] == "cpu"


def test_metrics_budget_constants():
    """Test that budget constants are reasonable."""
    assert STARTUP_BUDGET_MS == 300
    assert TRANSCRIBE_BUDGET_GPU_MS == 600
    assert TRANSCRIBE_BUDGET_CPU_MS == 1200


def test_metrics_stop_without_start():
    """Test stopping a metric that wasn't started."""
    metrics = PerformanceMetrics(enabled=True)

    event = metrics.stop("nonexistent")
    assert event is None
    assert len(metrics.get_events()) == 0


def test_metrics_disabled_no_file_writes(tmp_path: Path):
    """Test that disabled metrics don't write to files."""
    log_file = tmp_path / "metrics.log"
    metrics = PerformanceMetrics(enabled=False, log_path=log_file)

    metrics.record("test", 100.0)

    # File should not be created when disabled
    assert not log_file.exists()
