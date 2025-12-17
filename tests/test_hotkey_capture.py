"""Tests for hotkey capture key mappings."""

from __future__ import annotations

from app.hotkey import parse_hotkey
from app.ui.hotkey_capture import _keycode_to_key_token


def test_keycode_to_key_token_maps_common_keys() -> None:
    assert _keycode_to_key_token(0x41) == "A"
    assert _keycode_to_key_token(0x30) == "0"
    assert _keycode_to_key_token(0x70) == "F1"
    assert _keycode_to_key_token(0x20) == "SPACE"
    assert _keycode_to_key_token(0xBA) == ";"
    assert _keycode_to_key_token(0xDE) == "'"


def test_key_tokens_roundtrip_parse_hotkey() -> None:
    token = _keycode_to_key_token(0xBA)
    assert token == ";"
    chord = parse_hotkey(f"CTRL+SHIFT+{token}")
    assert chord.display == "CTRL+SHIFT+;"
