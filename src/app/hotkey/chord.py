"""Hotkey chord parsing utilities for the global hotkey manager."""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Iterable, Tuple

MODIFIER_FLAGS = {
    "alt": 0x0001,
    "ctrl": 0x0002,
    "control": 0x0002,
    "shift": 0x0004,
    "win": 0x0008,
    "windows": 0x0008,
    "super": 0x0008,
}

MODIFIER_KEYCODES = {
    "alt": frozenset({0xA4, 0xA5}),
    "ctrl": frozenset({0xA2, 0xA3}),
    "control": frozenset({0xA2, 0xA3}),
    "shift": frozenset({0xA0, 0xA1}),
    "win": frozenset({0x5B, 0x5C}),
    "windows": frozenset({0x5B, 0x5C}),
    "super": frozenset({0x5B, 0x5C}),
}


class HotkeyParseError(ValueError):
    """Raised when a hotkey chord cannot be parsed."""


@dataclass(frozen=True)
class HotkeyChord:
    """Normalized representation of a global hotkey chord."""

    text: str
    modifier_mask: int
    modifier_groups: Tuple[FrozenSet[int], ...]
    key_group: FrozenSet[int]

    @property
    def display(self) -> str:
        """Return a normalized display representation."""
        return self.text.upper()

    def matches(self, pressed: Iterable[int]) -> bool:
        """Check whether the supplied virtual key codes satisfy the chord."""
        pressed_set = frozenset(pressed)
        if not pressed_set:
            return False
        if not self.key_group.intersection(pressed_set):
            return False
        for group in self.modifier_groups:
            if group and not group.intersection(pressed_set):
                return False
        return True


def parse_hotkey(text: str) -> HotkeyChord:
    """Parse a user-supplied hotkey string."""
    if not text:
        raise HotkeyParseError("Hotkey cannot be empty")
    parts = [part.strip().lower() for part in text.split("+") if part.strip()]
    if not parts:
        raise HotkeyParseError("Hotkey must include a key")
    modifiers = []
    key_token = None
    for token in parts:
        if token in MODIFIER_FLAGS:
            modifiers.append(token)
        else:
            key_token = token
    if key_token is None:
        raise HotkeyParseError("Hotkey must include a non-modifier key")
    modifier_mask = 0
    modifier_groups = []
    for token in modifiers:
        modifier_mask |= MODIFIER_FLAGS[token]
        modifier_groups.append(MODIFIER_KEYCODES[token])
    key_group = _key_to_virtual_keys(key_token)
    if not key_group:
        raise HotkeyParseError(f"Unsupported key token '{key_token}'")
    normalized = "+".join([token.upper() for token in modifiers + [key_token]])
    return HotkeyChord(
        text=normalized,
        modifier_mask=modifier_mask,
        modifier_groups=tuple(modifier_groups),
        key_group=key_group,
    )


def _key_to_virtual_keys(token: str) -> FrozenSet[int]:
    punctuation = {
        ";": 0xBA,
        "=": 0xBB,
        ",": 0xBC,
        "-": 0xBD,
        ".": 0xBE,
        "/": 0xBF,
        "`": 0xC0,
        "[": 0xDB,
        "\\": 0xDC,
        "]": 0xDD,
        "'": 0xDE,
    }
    if token in punctuation:
        return frozenset({punctuation[token]})
    if token.startswith("f") and token[1:].isdigit():
        idx = int(token[1:])
        if 1 <= idx <= 24:
            return frozenset({0x70 + idx - 1})
    named = {
        "space": 0x20,
        "enter": 0x0D,
        "tab": 0x09,
        "escape": 0x1B,
        "esc": 0x1B,
        "backspace": 0x08,
        "delete": 0x2E,
        "home": 0x24,
        "end": 0x23,
        "pageup": 0x21,
        "pagedown": 0x22,
        "insert": 0x2D,
        "up": 0x26,
        "down": 0x28,
        "left": 0x25,
        "right": 0x27,
    }
    if token in named:
        return frozenset({named[token]})
    if len(token) == 1:
        char = token.upper()
        return frozenset({ord(char)})
    return frozenset()
