"""Global hotkey registration and handling."""

from .chord import HotkeyChord, HotkeyParseError, parse_hotkey
from .manager import (
    HotkeyCallbacks,
    HotkeyError,
    HotkeyInUseError,
    HotkeyManager,
    HotkeyRegistrationError,
)

__all__ = [
    "HotkeyCallbacks",
    "HotkeyChord",
    "HotkeyError",
    "HotkeyInUseError",
    "HotkeyManager",
    "HotkeyParseError",
    "HotkeyRegistrationError",
    "parse_hotkey",
]
