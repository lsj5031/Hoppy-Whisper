"""Performance metrics collection and logging (opt-in only)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

LOGGER = logging.getLogger("parakeet.metrics")

# Performance budget thresholds (ms)
STARTUP_BUDGET_MS = 300
TRANSCRIBE_BUDGET_GPU_MS = 600
TRANSCRIBE_BUDGET_CPU_MS = 1200


@dataclass
class MetricEvent:
    """Single performance measurement."""

    name: str
    duration_ms: float
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, str] = field(default_factory=dict)

    def exceeds_budget(self, budget_ms: float) -> bool:
        """Check if this event exceeds the given budget."""
        return self.duration_ms > budget_ms

    def to_log_line(self) -> str:
        """Format as a log line (no PII)."""
        meta_str = ", ".join(f"{k}={v}" for k, v in self.metadata.items())
        return f"{self.name}: {self.duration_ms:.1f}ms [{meta_str}]"


class PerformanceMetrics:
    """Collects and logs performance metrics when telemetry is enabled."""

    def __init__(self, enabled: bool = False, log_path: Optional[Path] = None) -> None:
        """
        Initialize the metrics collector.

        Args:
            enabled: Whether metrics collection is active
            log_path: Optional path to write metrics log file
        """
        self._enabled = enabled
        self._log_path = log_path
        self._events: list[MetricEvent] = []
        self._in_progress: Dict[str, float] = {}

        if self._enabled and self._log_path:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            LOGGER.info("Performance metrics enabled, logging to %s", self._log_path)

    @property
    def enabled(self) -> bool:
        """Return whether metrics collection is enabled."""
        return self._enabled

    def start(self, name: str) -> None:
        """Start timing an operation."""
        if not self._enabled:
            return
        self._in_progress[name] = time.perf_counter()

    def stop(self, name: str, **metadata: str) -> Optional[MetricEvent]:
        """
        Stop timing an operation and record the event.

        Args:
            name: Name of the operation
            **metadata: Additional context (no PII)

        Returns:
            MetricEvent if metrics are enabled, None otherwise
        """
        if not self._enabled or name not in self._in_progress:
            return None

        start_time = self._in_progress.pop(name)
        duration_ms = (time.perf_counter() - start_time) * 1000

        event = MetricEvent(name=name, duration_ms=duration_ms, metadata=metadata)
        self._events.append(event)

        # Log to console
        LOGGER.info("METRIC: %s", event.to_log_line())

        # Append to file if configured
        if self._log_path:
            try:
                with open(self._log_path, "a", encoding="utf-8") as f:
                    f.write(f"{event.timestamp:.3f},{event.to_log_line()}\n")
            except OSError as exc:
                LOGGER.warning("Failed to write metric to file: %s", exc)

        return event

    def record(self, name: str, duration_ms: float, **metadata: str) -> MetricEvent:
        """
        Record a metric event with a known duration.

        Args:
            name: Name of the operation
            duration_ms: Duration in milliseconds
            **metadata: Additional context (no PII)

        Returns:
            The recorded MetricEvent
        """
        event = MetricEvent(name=name, duration_ms=duration_ms, metadata=metadata)

        if self._enabled:
            self._events.append(event)
            LOGGER.info("METRIC: %s", event.to_log_line())

            if self._log_path:
                try:
                    with open(self._log_path, "a", encoding="utf-8") as f:
                        f.write(f"{event.timestamp:.3f},{event.to_log_line()}\n")
                except OSError as exc:
                    LOGGER.warning("Failed to write metric to file: %s", exc)

        return event

    def get_events(self) -> list[MetricEvent]:
        """Return all recorded events."""
        return list(self._events)

    def clear(self) -> None:
        """Clear all recorded events."""
        self._events.clear()
        self._in_progress.clear()

    def check_budget(
        self, name: str, duration_ms: float, budget_ms: float, **metadata: str
    ) -> bool:
        """
        Record a metric and check if it's within budget.

        Args:
            name: Name of the operation
            duration_ms: Duration in milliseconds
            budget_ms: Budget threshold in milliseconds
            **metadata: Additional context

        Returns:
            True if within budget, False otherwise
        """
        event = self.record(name, duration_ms, **metadata)
        within_budget = not event.exceeds_budget(budget_ms)

        if not within_budget:
            LOGGER.warning(
                "BUDGET EXCEEDED: %s took %.1fms (budget: %.1fms)",
                name,
                duration_ms,
                budget_ms,
            )

        return within_budget


# Global singleton instance
_global_metrics: Optional[PerformanceMetrics] = None


def initialize_metrics(enabled: bool, log_path: Optional[Path] = None) -> None:
    """Initialize the global metrics instance."""
    global _global_metrics
    _global_metrics = PerformanceMetrics(enabled=enabled, log_path=log_path)


def get_metrics() -> PerformanceMetrics:
    """Get the global metrics instance, initializing if needed."""
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = PerformanceMetrics(enabled=False)
    return _global_metrics
