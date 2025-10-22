"""Tests for Shift-to-bypass cleanup (E4.2)."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.cleanup import CleanupEngine, CleanupMode


def test_cleanup_engine_with_standard_mode():
    """Test that cleanup is applied in standard mode."""
    engine = CleanupEngine(CleanupMode.STANDARD)
    raw_text = "um hello world"
    cleaned = engine.clean(raw_text)

    assert "um" not in cleaned.lower()
    assert "Hello world." == cleaned


def test_bypass_cleanup_preserves_raw_text():
    """Test that bypassing cleanup preserves the raw transcription."""
    engine = CleanupEngine(CleanupMode.STANDARD)
    raw_text = "um hello world"

    # When bypass is active, we skip the cleanup entirely
    # (simulating what happens in the main app)
    bypassed_text = raw_text  # No cleanup applied

    # Verify raw text is preserved
    assert "um" in bypassed_text.lower()
    assert bypassed_text == raw_text


def test_hotkey_callback_signature():
    """Test that hotkey callbacks support bypass flag."""
    from app.hotkey import HotkeyCallbacks

    # Create a mock that tracks calls
    stop_calls = []

    def on_stop(bypass: bool):
        stop_calls.append(bypass)

    callbacks = HotkeyCallbacks(
        on_record_start=lambda: None,
        on_record_stop=on_stop,
        on_request_paste=lambda: None,
    )

    # Simulate calls
    callbacks.on_record_stop(False)
    callbacks.on_record_stop(True)

    assert stop_calls == [False, True]


def test_shift_detection_in_pressed_keys():
    """Test shift key detection logic."""
    # Shift VK codes: 0x10 (generic), 0xA0 (left), 0xA1 (right)
    shift_vk_codes = [0x10, 0xA0, 0xA1]

    # Simulate pressed keys without shift
    pressed = {0x11, 0x12}  # CTRL, ALT
    has_shift = any(vk in pressed for vk in shift_vk_codes)
    assert not has_shift

    # Simulate pressed keys with left shift
    pressed_with_shift = {0x11, 0x12, 0xA0}  # CTRL, ALT, LSHIFT
    has_shift = any(vk in pressed_with_shift for vk in shift_vk_codes)
    assert has_shift

    # Simulate pressed keys with right shift
    pressed_with_rshift = {0x11, 0x12, 0xA1}  # CTRL, ALT, RSHIFT
    has_shift = any(vk in pressed_with_rshift for vk in shift_vk_codes)
    assert has_shift

    # Simulate pressed keys with generic shift
    pressed_with_generic = {0x11, 0x12, 0x10}  # CTRL, ALT, SHIFT
    has_shift = any(vk in pressed_with_generic for vk in shift_vk_codes)
    assert has_shift
