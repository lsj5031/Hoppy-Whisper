from __future__ import annotations

from typing import Callable, Dict, List

import pytest
from PIL import Image
from pynput import keyboard

from app import startup
from app.hotkey import HotkeyCallbacks, HotkeyManager
from app.settings import AppSettings
from app.tray.icons import TrayIconFactory, TrayTheme
from app.tray.state import TrayState


def test_icon_factory_generates_expected_frames() -> None:
    factory = TrayIconFactory()
    for state in TrayState:
        frames = factory.state_frames(state, TrayTheme.LIGHT)
        assert set(frames) == set(factory.sizes)
        expected_frame_count = factory.spinner_frames if state.animated else 1
        for size, images in frames.items():
            assert len(images) == expected_frame_count
            for image in images:
                assert isinstance(image, Image.Image)
                assert image.size == (size, size)


def test_hotkey_manager_press_release_and_paste(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: List[str] = []
    callbacks = HotkeyCallbacks(
        on_record_start=lambda: events.append("start"),
        on_record_stop=lambda: events.append("stop"),
        on_request_paste=lambda: events.append("paste"),
        on_error=lambda exc: events.append(f"error:{exc}"),
    )

    pressed: Dict[str, Callable[[keyboard.Key | keyboard.KeyCode], None]] = {}

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

    current_time = {"value": 0.0}

    def monotonic() -> float:
        return current_time["value"]

    monkeypatch.setattr("app.hotkey.manager.time.monotonic", monotonic)

    manager = HotkeyManager(
        "CTRL+SHIFT+;",
        callbacks,
        listener_factory=lambda press, release: StubListener(press, release),
    )

    manager.start()

    press = pressed["press"]
    release = pressed["release"]

    ctrl = keyboard.KeyCode.from_vk(0xA2)
    shift = keyboard.KeyCode.from_vk(0xA0)
    semicolon = keyboard.KeyCode.from_vk(0xBA)

    press(ctrl)
    press(shift)
    press(semicolon)

    assert events == ["start"]

    current_time["value"] += 0.2
    release(semicolon)
    release(shift)
    release(ctrl)

    assert events == ["start", "stop"]

    current_time["value"] += 0.3

    press(ctrl)
    press(shift)
    press(semicolon)

    assert events == ["start", "stop", "paste"]

    manager.stop()


def test_app_settings_roundtrip(tmp_path) -> None:
    path = tmp_path / "settings.json"
    settings = AppSettings(
        hotkey_chord="CTRL+ALT+Z",
        paste_window_seconds=1.5,
        start_with_windows=True,
        first_run_complete=True,
    )
    settings.save(path)
    loaded = AppSettings.load(path)
    assert loaded == settings


def test_startup_enable_disable(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeWinreg:
        HKEY_CURRENT_USER = object()
        KEY_SET_VALUE = 0x0002
        KEY_CREATE_SUB_KEY = 0x0004
        KEY_READ = 0x0001
        REG_SZ = 1

        def __init__(self) -> None:
            self.storage: Dict[str, Dict[str, str]] = {}

        def OpenKey(self, root, path, reserved=0, access=0):  # noqa: N802
            if path not in self.storage:
                raise FileNotFoundError
            return path

        def CreateKeyEx(self, root, path, reserved, access):  # noqa: N802
            self.storage.setdefault(path, {})
            return path

        def SetValueEx(self, key, name, reserved, reg_type, value):  # noqa: N802
            self.storage.setdefault(key, {})[name] = value

        def DeleteValue(self, key, name):  # noqa: N802
            try:
                del self.storage[key][name]
            except KeyError:
                raise FileNotFoundError from None

        def QueryValueEx(self, key, name):  # noqa: N802
            if name not in self.storage.get(key, {}):
                raise FileNotFoundError
            return self.storage[key][name], self.REG_SZ

        def CloseKey(self, key):  # noqa: N802
            return None

    fake_winreg = FakeWinreg()
    monkeypatch.setattr(startup, "winreg", fake_winreg, raising=True)

    command = '"python" -m app'
    startup.enable_startup("Parakeet", command)
    assert fake_winreg.storage[startup.RUN_KEY_PATH]["Parakeet"] == command
    assert startup.is_startup_enabled("Parakeet", command) is True

    startup.disable_startup("Parakeet")
    assert "Parakeet" not in fake_winreg.storage.get(startup.RUN_KEY_PATH, {})
    assert startup.is_startup_enabled("Parakeet", command) is False


def test_resolve_startup_command_handles_frozen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        startup.sys, "executable", r"C:\App\Parakeet.exe", raising=False
    )
    monkeypatch.setattr(startup.sys, "frozen", True, raising=False)
    cmd = startup.resolve_startup_command()
    assert cmd == '"C:\\App\\Parakeet.exe"'

    monkeypatch.setattr(startup.sys, "frozen", False, raising=False)
    cmd_dev = startup.resolve_startup_command()
    assert cmd_dev.endswith("-m app")
