"""Global hotkey manager for the Parakeet tray app."""

from __future__ import annotations

import ctypes
import sys
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional, Set

from pynput import keyboard

from .chord import HotkeyChord, parse_hotkey


class HotkeyError(Exception):
    """Base class for hotkey manager errors."""


class HotkeyInUseError(HotkeyError):
    """Raised when attempting to register a chord that is already taken."""


class HotkeyRegistrationError(HotkeyError):
    """Raised when registration fails for an unexpected reason."""


@dataclass
class HotkeyCallbacks:
    """Callback hooks invoked by the hotkey manager."""

    on_record_start: Callable[[], None]
    on_record_stop: Callable[[], None]
    on_request_paste: Callable[[], None]
    on_error: Callable[[Exception], None] = lambda exc: None


class _ListenerWrapper:
    """Interface adapter for pynput keyboard listeners."""

    def __init__(
        self,
        on_press: Callable[[keyboard.Key | keyboard.KeyCode], None],
        on_release: Callable[[keyboard.Key | keyboard.KeyCode], None],
    ) -> None:
        self._listener = keyboard.Listener(on_press=on_press, on_release=on_release)

    def start(self) -> None:
        self._listener.start()

    def stop(self) -> None:
        self._listener.stop()
        self._listener.join(timeout=0.5)


class HotkeyManager:
    """Manage global hotkey detection with hold/release semantics."""

    def __init__(
        self,
        chord: str,
        callbacks: HotkeyCallbacks,
        *,
        paste_window_seconds: float = 2.0,
        listener_factory: Callable[
            [
                Callable[[keyboard.Key | keyboard.KeyCode], None],
                Callable[[keyboard.Key | keyboard.KeyCode], None],
            ],
            _ListenerWrapper,
        ]
        | None = None,
    ) -> None:
        self._callbacks = callbacks
        self._listener_factory = listener_factory or _ListenerWrapper
        self._lock = threading.RLock()
        self._listener: Optional[_ListenerWrapper] = None
        self._pressed: Set[int] = set()
        self._active = False
        self._last_release_time = 0.0
        self._running = False
        self._paste_window_seconds = _validate_paste_window(paste_window_seconds)
        self._chord = self._parse_and_validate(chord)

    @property
    def chord(self) -> HotkeyChord:
        """Return the currently active hotkey chord."""
        return self._chord

    @property
    def paste_window_seconds(self) -> float:
        """Return the paste window duration."""
        return self._paste_window_seconds

    def set_paste_window_seconds(self, duration: float) -> None:
        """Update the paste window duration (0–5 seconds inclusive)."""
        self._paste_window_seconds = _validate_paste_window(duration)

    def update_chord(self, chord_text: str) -> None:
        """Change the registered chord at runtime."""
        with self._lock:
            chord = self._parse_and_validate(chord_text)
            self._chord = chord
            self._pressed.clear()
            self._active = False

    def start(self) -> None:
        """Begin listening for the hotkey chord."""
        with self._lock:
            if self._running:
                return
            self._ensure_hotkey_available(self._chord)
            listener = self._listener_factory(self._on_press, self._on_release)
            listener.start()
            self._listener = listener
            self._running = True

    def stop(self) -> None:
        """Stop listening for the hotkey chord."""
        with self._lock:
            if not self._running:
                return
            if self._listener:
                self._listener.stop()
            self._listener = None
            self._running = False
            self._pressed.clear()
            self._active = False

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        vk = _vk_from_key(key)
        if vk is None:
            return
        with self._lock:
            self._pressed.add(vk)
            if self._active:
                return
            if not self._chord.matches(self._pressed):
                return
            now = time.monotonic()
            if (
                self._last_release_time
                and now - self._last_release_time <= self._paste_window_seconds
            ):
                self._last_release_time = 0.0
                self._dispatch(self._callbacks.on_request_paste)
            else:
                self._active = True
                self._dispatch(self._callbacks.on_record_start)

    def _on_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        vk = _vk_from_key(key)
        if vk is None:
            return
        with self._lock:
            self._pressed.discard(vk)
            if not self._active:
                return
            if self._chord.matches(self._pressed):
                return
            self._active = False
            self._last_release_time = time.monotonic()
            self._dispatch(self._callbacks.on_record_stop)

    def _parse_and_validate(self, chord_text: str) -> HotkeyChord:
        chord = parse_hotkey(chord_text)
        self._ensure_hotkey_available(chord)
        return chord

    def _ensure_hotkey_available(self, chord: HotkeyChord) -> None:
        if sys.platform != "win32":
            return
        virtual_key = next(iter(chord.key_group))
        modifiers = chord.modifier_mask
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        kernel32.SetLastError(0)
        if not user32.RegisterHotKey(None, 0, modifiers, virtual_key):
            error_code = ctypes.get_last_error()
            if error_code == 1409:  # ERROR_HOTKEY_ALREADY_REGISTERED
                raise HotkeyInUseError(
                    f"Hotkey '{chord.display}' is already registered"
                )
            raise HotkeyRegistrationError(
                f"Failed to register hotkey '{chord.display}' (error {error_code})"
            )
        user32.UnregisterHotKey(None, 0)

    def _dispatch(self, handler: Callable[[], None]) -> None:
        try:
            handler()
        except Exception as exc:  # pragma: no cover - defensive
            try:
                self._callbacks.on_error(exc)
            except Exception:
                pass


def _vk_from_key(key: keyboard.Key | keyboard.KeyCode) -> Optional[int]:
    if isinstance(key, keyboard.KeyCode):
        if key.vk is not None:
            return key.vk
        if key.char:
            return ord(key.char.upper())
        return None
    if isinstance(key, keyboard.Key):
        return key.value.vk
    return None


def _validate_paste_window(duration: float) -> float:
    if not 0.0 <= duration <= 5.0:
        raise ValueError("Paste window must be between 0.0 and 5.0 seconds")
    return float(duration)
