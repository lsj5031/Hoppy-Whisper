"""Global hotkey manager for the Hoppy Whisper tray app."""

from __future__ import annotations

import ctypes
import logging
import sys
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional, Set

from pynput import keyboard

from .chord import HotkeyChord, parse_hotkey

LOGGER = logging.getLogger("hoppy_whisper.hotkey")


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
        chord: str | HotkeyChord,
        callbacks: HotkeyCallbacks,
        *,
        paste_window_seconds: float = 2.0,
        toggle_mode: bool = False,
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
        self._chord_down = False
        self._last_release_time = 0.0
        self._running = False
        self._registered: bool = False
        self._reg_id: int = 1
        self._paste_window_seconds = _validate_paste_window(paste_window_seconds)
        self._toggle_mode = bool(toggle_mode)
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

    def update_chord(self, chord_text: str | HotkeyChord) -> None:
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
            # On Windows, register the hotkey for the app lifetime until stop()
            if sys.platform == "win32":
                self._register_hotkey()
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
            if sys.platform == "win32" and self._registered:
                self._unregister_hotkey()
            self._running = False
            self._pressed.clear()
            self._active = False

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        vk = _vk_from_key(key)
        if vk is None:
            return
        with self._lock:
            self._pressed.add(vk)
            if not self._chord.matches(self._pressed):
                return
            if self._toggle_mode:
                if self._chord_down:
                    return
                self._chord_down = True
                if not self._active:
                    self._active = True
                    self._dispatch(self._callbacks.on_record_start)
                else:
                    # Toggle off on chord press
                    self._active = False
                    self._last_release_time = 0.0
                    self._dispatch(self._callbacks.on_record_stop)
                return
            # Hold/release mode
            if self._active:
                return
            now = time.monotonic()
            if self._last_release_time and (
                now - self._last_release_time <= self._paste_window_seconds
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
            if not self._chord.matches(self._pressed):
                self._chord_down = False
            if self._toggle_mode:
                # In toggle mode, stopping happens on the next chord press
                return
            if not self._active:
                return
            if self._chord.matches(self._pressed):
                return
            self._active = False
            self._last_release_time = time.monotonic()
            self._dispatch(self._callbacks.on_record_stop)

    def _parse_and_validate(self, chord_input: str | HotkeyChord) -> HotkeyChord:
        chord = (
            chord_input
            if isinstance(chord_input, HotkeyChord)
            else parse_hotkey(chord_input)
        )
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
            # Treat unknown failures as already-registered in availability probe
            # ERROR_SUCCESS or ERROR_HOTKEY_ALREADY_REGISTERED
            if error_code in (0, 1409):
                raise HotkeyInUseError(
                    f"Hotkey '{chord.display}' is already registered"
                )
            raise HotkeyRegistrationError(
                f"Failed to register hotkey '{chord.display}' (error {error_code})"
            )
        user32.UnregisterHotKey(None, 0)

    def _register_hotkey(self) -> None:
        """Register the global hotkey on Windows and keep it until stop()."""
        virtual_key = next(iter(self._chord.key_group))
        modifiers = self._chord.modifier_mask
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        kernel32.SetLastError(0)
        if not user32.RegisterHotKey(None, self._reg_id, modifiers, virtual_key):
            error_code = ctypes.get_last_error()
            if error_code == 1409:
                raise HotkeyInUseError(
                    f"Hotkey '{self._chord.display}' is already registered"
                )
            raise HotkeyRegistrationError(
                f"Failed to register hotkey '{self._chord.display}' "
                f"(error {error_code})"
            )
        self._registered = True

    def _unregister_hotkey(self) -> None:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        try:
            user32.UnregisterHotKey(None, self._reg_id)
        finally:
            self._registered = False

    def _dispatch(self, handler: Callable[[], None]) -> None:
        """Dispatch a callback, ensuring errors are always logged.
        
        Logs any exception from the handler, then attempts to call the on_error
        callback. If the on_error callback also raises, that error is logged too
        (double-logging is preferable to silently swallowing errors).
        """
        try:
            handler()
        except Exception as exc:  # pragma: no cover - defensive
            # Always log the handler error first
            LOGGER.exception("Callback error in hotkey handler", exc_info=exc)
            # Then try to invoke the error callback
            try:
                self._callbacks.on_error(exc)
            except Exception as err:
                # Log if on_error callback itself fails
                LOGGER.exception("Error callback also failed", exc_info=err)



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
