"""Text cleanup rules and helpers."""

from .engine import CleanupEngine, CleanupMode

__all__ = ["CleanupEngine", "CleanupMode"]


def apply_cleanup_rules(text: str, mode: CleanupMode = CleanupMode.STANDARD) -> str:
    """Apply cleanup rules to transcribed text.

    Args:
        text: Raw transcribed text
        mode: Cleanup mode to use (default: STANDARD)

    Returns:
        Cleaned text
    """
    engine = CleanupEngine(mode)
    return engine.clean(text)
