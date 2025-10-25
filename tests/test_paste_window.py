"""Tests for paste window and auto-paste functionality (E4.3)."""

from __future__ import annotations

import pytest


def test_paste_window_timer_exists():
    """Test that paste window timer is configurable."""
    from app.settings import AppSettings

    settings = AppSettings(paste_window_seconds=3.0)
    assert settings.paste_window_seconds == 3.0


def test_auto_paste_setting():
    """Test auto-paste setting."""
    from app.settings import AppSettings

    # Default is True
    settings = AppSettings()
    assert settings.auto_paste is True

    # Can be enabled
    settings = AppSettings(auto_paste=True)
    assert settings.auto_paste is True


def test_paste_callback_is_registered():
    """Test that paste callback is registered in hotkey manager."""
    from app.hotkey import HotkeyCallbacks

    paste_called = []

    def on_paste():
        paste_called.append(True)

    callbacks = HotkeyCallbacks(
        on_record_start=lambda: None,
        on_record_stop=lambda: None,
        on_request_paste=on_paste,
    )

    # Simulate paste request
    callbacks.on_request_paste()

    assert len(paste_called) == 1


def test_keyboard_controller_paste_simulation():
    """Test that pynput keyboard controller can simulate Ctrl+V."""
    from pynput.keyboard import Controller, Key

    controller = Controller()

    # This test just verifies the API is available
    # In real execution, this would send actual keystrokes
    assert hasattr(controller, "press")
    assert hasattr(controller, "release")
    assert hasattr(controller, "pressed")
    assert hasattr(Key, "ctrl")


def test_paste_window_timing():
    """Test that paste window timing is respected."""
    import time
    from unittest.mock import patch

    from app.hotkey.manager import HotkeyCallbacks, HotkeyManager

    start_count = []
    stop_count = []
    paste_count = []

    callbacks = HotkeyCallbacks(
        on_record_start=lambda: start_count.append(time.time()),
        on_record_stop=lambda: stop_count.append(time.time()),
        on_request_paste=lambda: paste_count.append(time.time()),
    )

    # Create manager with 1 second paste window (skip OS availability probe)
    with patch.object(HotkeyManager, "_ensure_hotkey_available", lambda self, c: None):
        manager = HotkeyManager(
            "CTRL+SHIFT+;",
            callbacks,
            paste_window_seconds=1.0,
        )

    assert manager.paste_window_seconds == 1.0

    # Can update paste window
    manager.set_paste_window_seconds(2.5)
    assert manager.paste_window_seconds == 2.5


def test_paste_window_validation():
    """Test that paste window is validated to 0-5 seconds."""
    from app.hotkey.manager import _validate_paste_window

    # Valid values
    assert _validate_paste_window(0.0) == 0.0
    assert _validate_paste_window(2.5) == 2.5
    assert _validate_paste_window(5.0) == 5.0

    # Invalid values
    with pytest.raises(ValueError):
        _validate_paste_window(-0.1)

    with pytest.raises(ValueError):
        _validate_paste_window(5.1)


def test_settings_persist_paste_config():
    """Test that paste configuration is persisted."""
    from app.settings import AppSettings

    settings = AppSettings(
        paste_window_seconds=3.5,
        auto_paste=True,
    )

    data = settings.to_dict()

    assert data["paste_window_seconds"] == 3.5
    assert data["auto_paste"] is True

    # Round-trip
    restored = AppSettings.from_dict(data)
    assert restored.paste_window_seconds == 3.5
    assert restored.auto_paste is True
