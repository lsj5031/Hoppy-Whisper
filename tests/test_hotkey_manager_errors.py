"""Tests for hotkey manager error handling and logging."""

from __future__ import annotations

from typing import Callable

import pytest
from pynput import keyboard

from app.hotkey import HotkeyCallbacks, HotkeyManager


def test_dispatch_handler_error_is_logged(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """_dispatch logs handler errors."""
    import logging

    caplog.set_level(logging.DEBUG, logger="hoppy_whisper.hotkey")

    handler_called = False

    def failing_handler() -> None:
        nonlocal handler_called
        handler_called = True
        raise ValueError("Test error from handler")

    on_error_called = False

    def on_error(exc: Exception) -> None:
        nonlocal on_error_called
        on_error_called = True

    callbacks = HotkeyCallbacks(
        on_record_start=failing_handler,
        on_record_stop=lambda: None,
        on_request_paste=lambda: None,
        on_error=on_error,
    )

    pressed: dict[str, Callable[[keyboard.Key | keyboard.KeyCode], None]] = {}

    class StubListener:
        def __init__(
            self,
            on_press: Callable[[keyboard.Key | keyboard.KeyCode], None],
            on_release: Callable[[keyboard.Key | keyboard.KeyCode], None],
        ) -> None:
            pressed["press"] = on_press
            pressed["release"] = on_release

        def start(self) -> None:
            pass

        def stop(self) -> None:
            pass

    monkeypatch.setattr("app.hotkey.manager.sys.platform", "test")

    manager = HotkeyManager(
        "CTRL+SHIFT+;",
        callbacks,
        listener_factory=lambda press, release: StubListener(press, release),
    )

    manager.start()

    # Simulate hotkey press
    press = pressed["press"]

    ctrl = keyboard.KeyCode.from_vk(0xA2)
    shift = keyboard.KeyCode.from_vk(0xA0)
    semicolon = keyboard.KeyCode.from_vk(0xBA)

    press(ctrl)
    press(shift)
    press(semicolon)

    # Verify handler was called

    assert handler_called
    # Verify on_error was also called
    assert on_error_called
    # Verify the error was logged
    assert "Callback error in hotkey handler" in caplog.text


def test_dispatch_on_error_callback_also_fails(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """_dispatch logs errors from on_error callback too."""
    import logging

    caplog.set_level(logging.DEBUG, logger="hoppy_whisper.hotkey")

    def failing_handler() -> None:
        raise ValueError("Handler error")

    def failing_on_error(exc: Exception) -> None:
        raise RuntimeError("Error callback error")

    callbacks = HotkeyCallbacks(
        on_record_start=failing_handler,
        on_record_stop=lambda: None,
        on_request_paste=lambda: None,
        on_error=failing_on_error,
    )

    pressed: dict[str, Callable[[keyboard.Key | keyboard.KeyCode], None]] = {}

    class StubListener:
        def __init__(
            self,
            on_press: Callable[[keyboard.Key | keyboard.KeyCode], None],
            on_release: Callable[[keyboard.Key | keyboard.KeyCode], None],
        ) -> None:
            pressed["press"] = on_press
            pressed["release"] = on_release

        def start(self) -> None:
            pass

        def stop(self) -> None:
            pass

    monkeypatch.setattr("app.hotkey.manager.sys.platform", "test")

    manager = HotkeyManager(
        "CTRL+SHIFT+;",
        callbacks,
        listener_factory=lambda press, release: StubListener(press, release),
    )

    manager.start()

    # Simulate hotkey press
    press = pressed["press"]

    ctrl = keyboard.KeyCode.from_vk(0xA2)
    shift = keyboard.KeyCode.from_vk(0xA0)
    semicolon = keyboard.KeyCode.from_vk(0xBA)

    press(ctrl)
    press(shift)
    press(semicolon)

    # Both errors should be logged
    assert "Callback error in hotkey handler" in caplog.text
    assert "Error callback also failed" in caplog.text


def test_dispatch_does_not_reraise(monkeypatch: pytest.MonkeyPatch) -> None:
    """_dispatch does not re-raise exceptions."""

    def failing_handler() -> None:
        raise ValueError("Test error")

    callbacks = HotkeyCallbacks(
        on_record_start=failing_handler,
        on_record_stop=lambda: None,
        on_request_paste=lambda: None,
        on_error=lambda exc: None,
    )

    # Create a manager without starting it
    monkeypatch.setattr("app.hotkey.manager.sys.platform", "test")
    manager = HotkeyManager(
        "CTRL+SHIFT+;",
        callbacks,
    )

    # _dispatch should not raise
    try:
        manager._dispatch(failing_handler)
    except Exception:
        pytest.fail("_dispatch re-raised an exception")
