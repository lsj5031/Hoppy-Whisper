"""Tests for applying settings updates to the hotkey manager."""

from __future__ import annotations

from types import SimpleNamespace

from app.__main__ import AppRuntime


def test_on_settings_applied_updates_hotkey_manager() -> None:
    calls: list[object] = []

    class StubHotkeyManager:
        def __init__(self) -> None:
            self._chord = "CTRL+SHIFT+;"
            self._paste_window_seconds = 2.0

        @property
        def chord(self) -> str:
            return self._chord

        @property
        def paste_window_seconds(self) -> float:
            return self._paste_window_seconds

        def stop(self) -> None:
            calls.append("stop")

        def set_paste_window_seconds(self, duration: float) -> None:
            self._paste_window_seconds = duration
            calls.append(("set_paste_window_seconds", duration))

        def update_chord(self, chord_text: str) -> None:
            self._chord = chord_text
            calls.append(("update_chord", chord_text))

        def start(self) -> None:
            calls.append("start")

    class StubToastManager:
        def success(self, message: str, title: str = "") -> None:
            return None

        def error(self, message: str, title: str = "") -> None:
            return None

    settings = SimpleNamespace(
        start_with_windows=False,
        paste_window_seconds=3.5,
        hotkey_chord="CTRL+SHIFT+H",
    )

    runtime = SimpleNamespace(
        _settings=settings,
        _hotkey=StubHotkeyManager(),
        _toast_manager=StubToastManager(),
        _probe_startup_state=lambda: False,
        _apply_startup_setting=lambda enabled: None,
    )

    AppRuntime._on_settings_applied(runtime)

    assert calls == [
        "stop",
        ("set_paste_window_seconds", 3.5),
        ("update_chord", "CTRL+SHIFT+H"),
        "start",
    ]
