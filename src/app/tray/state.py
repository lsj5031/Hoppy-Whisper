"""Enumeration of the tray icon states used by the Hoppy Whisper app."""

from __future__ import annotations

from enum import Enum


class TrayState(str, Enum):
    """Lifecycle states surfaced via the tray icon."""

    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    COPIED = "copied"
    PASTED = "pasted"
    ERROR = "error"

    @property
    def animated(self) -> bool:
        """Indicate whether this state expects an animated icon."""
        return self in (TrayState.LISTENING, TrayState.TRANSCRIBING)
