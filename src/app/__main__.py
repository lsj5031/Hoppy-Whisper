"""Command-line entry point for the Parakeet tray application."""

from __future__ import annotations

import logging
import signal
import sys
import threading
from typing import Optional

from app import startup
from app.audio import AudioDeviceError, AudioRecorder
from app.hotkey import HotkeyCallbacks, HotkeyInUseError, HotkeyManager
from app.settings import AppSettings, default_settings_path
from app.tray import TrayController, TrayMenuActions, TrayState

LOGGER = logging.getLogger("parakeet")


class AppRuntime:
    """High-level coordinator that wires the tray and hotkey subsystems."""

    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._stop_event = threading.Event()
        self._recording_active = False
        self._transcribe_timer: Optional[threading.Timer] = None
        self._idle_timer: Optional[threading.Timer] = None
        self._app_name = "Parakeet"
        self._startup_command = startup.resolve_startup_command()
        self._audio_recorder = AudioRecorder()
        self._audio_buffer: Optional[object] = None
        registry_startup = self._probe_startup_state()
        self._tray = TrayController(
            app_name=self._app_name,
            menu_actions=TrayMenuActions(
                toggle_recording=self._menu_toggle_recording,
                show_settings=self._show_settings_tip,
                show_history=self._show_history_tip,
                set_start_with_windows=self._set_start_with_windows,
                quit_app=self.stop,
            ),
            start_with_windows=registry_startup,
            show_first_run_tip=not settings.first_run_complete,
        )
        callbacks = HotkeyCallbacks(
            on_record_start=self._handle_record_start,
            on_record_stop=self._handle_record_stop,
            on_request_paste=self._handle_request_paste,
            on_error=self._log_callback_error,
        )
        self._hotkey = HotkeyManager(
            settings.hotkey_chord,
            callbacks,
            paste_window_seconds=settings.paste_window_seconds,
        )

    def start(self) -> None:
        """Start the tray icon and hotkey listener."""
        LOGGER.info("Starting Parakeet runtime")
        self._tray.start()
        self._hotkey.start()
        if self._settings.start_with_windows:
            self._apply_startup_setting(True)
        if not self._settings.first_run_complete:
            self._settings.first_run_complete = True
            self._settings.save()

    def stop(self) -> None:
        """Shut down background services and signal termination."""
        if self._stop_event.is_set():
            return
        LOGGER.info("Stopping Parakeet runtime")
        self._stop_event.set()
        self._cancel_timer(self._transcribe_timer)
        self._cancel_timer(self._idle_timer)
        self._hotkey.stop()
        self._tray.stop()

    def wait(self) -> None:
        """Block the main thread until a quit signal arrives."""
        self._stop_event.wait()

    # Tray menu callbacks -------------------------------------------------

    def _menu_toggle_recording(self) -> None:
        if self._recording_active:
            self._handle_record_stop()
        else:
            self._handle_record_start()

    def _show_settings_tip(self) -> None:
        path = default_settings_path()
        self._settings.save(path)
        self._notify(
            "Settings",
            f"Edit {path} to change the hotkey, paste window, or startup options.",
        )

    def _show_history_tip(self) -> None:
        self._notify("History", "History UI arrives in a later milestone.")

    def _set_start_with_windows(self, enabled: bool) -> None:
        if self._settings.start_with_windows == enabled:
            return
        success = self._apply_startup_setting(enabled)
        if not success:
            return
        self._settings.start_with_windows = enabled
        self._settings.save()
        state = "enabled" if enabled else "disabled"
        self._notify("Startup", f"Launch at login {state}.")

    # Hotkey callbacks ----------------------------------------------------

    def _handle_record_start(self) -> None:
        if self._recording_active:
            return
        LOGGER.debug("Hotkey pressed: start recording")
        self._recording_active = True
        self._cancel_timer(self._transcribe_timer)
        self._cancel_timer(self._idle_timer)

        try:
            self._audio_recorder.start()
            self._tray.set_state(TrayState.LISTENING)
        except AudioDeviceError as exc:
            LOGGER.error("Audio device error: %s", exc)
            self._notify("Microphone Error", str(exc))
            self._recording_active = False
            self._tray.set_state(TrayState.ERROR)
            self._schedule_idle_reset()
        except Exception as exc:
            LOGGER.exception("Failed to start audio capture", exc_info=exc)
            self._notify("Recording Error", "Could not start audio capture")
            self._recording_active = False
            self._tray.set_state(TrayState.ERROR)
            self._schedule_idle_reset()

    def _handle_record_stop(self) -> None:
        if not self._recording_active:
            return
        LOGGER.debug("Hotkey released: stop recording")
        self._recording_active = False

        try:
            self._audio_buffer = self._audio_recorder.stop()
            # Calculate duration from returned buffer
            buffer_samples = (
                len(self._audio_buffer) if self._audio_buffer is not None else 0
            )
            duration = buffer_samples / self._audio_recorder.sample_rate
            LOGGER.info(
                "Captured %.2f seconds of audio (%d samples)", duration, buffer_samples
            )

            if duration < 0.1:
                LOGGER.warning(
                    "Audio buffer too short (%.2f s), skipping transcription", duration
                )
                self._notify("Recording Too Short", "Please hold the hotkey longer")
                self._tray.set_state(TrayState.ERROR)
                self._schedule_idle_reset()
                return

            self._tray.set_state(TrayState.TRANSCRIBING)
            self._transcribe_timer = threading.Timer(0.8, self._complete_transcription)
            self._transcribe_timer.start()
        except Exception as exc:
            LOGGER.exception("Failed to stop audio capture", exc_info=exc)
            self._notify("Recording Error", "Could not complete audio capture")
            self._tray.set_state(TrayState.ERROR)
            self._schedule_idle_reset()

    def _complete_transcription(self) -> None:
        LOGGER.debug("Transcription placeholder complete")
        self._tray.set_state(TrayState.COPIED)
        self._schedule_idle_reset()

    def _handle_request_paste(self) -> None:
        LOGGER.debug("Hotkey tapped within paste window: paste")
        self._tray.set_state(TrayState.PASTED)
        self._schedule_idle_reset()

    def _log_callback_error(self, exc: Exception) -> None:
        LOGGER.exception("Unhandled exception in hotkey callback", exc_info=exc)

    # Helpers -------------------------------------------------------------

    def _schedule_idle_reset(self, delay: float = 1.6) -> None:
        self._cancel_timer(self._idle_timer)
        self._idle_timer = threading.Timer(delay, self._reset_to_idle)
        self._idle_timer.start()

    def _reset_to_idle(self) -> None:
        LOGGER.debug("Resetting tray state to idle")
        self._tray.set_state(TrayState.IDLE)

    def _cancel_timer(self, timer: Optional[threading.Timer]) -> None:
        if timer and timer.is_alive():
            timer.cancel()

    def _notify(self, title: str, message: str) -> None:
        icon = self._tray.icon
        if icon:
            try:
                icon.notify(message, title)
                return
            except Exception:  # pragma: no cover - notification errors are non-critical
                LOGGER.debug("Tray notification failed", exc_info=True)
        LOGGER.info("%s: %s", title, message)

    def _apply_startup_setting(self, enabled: bool) -> bool:
        try:
            if enabled:
                startup.enable_startup(self._app_name, self._startup_command)
            else:
                startup.disable_startup(self._app_name)
        except startup.StartupError as exc:
            self._notify("Startup", f"Could not update auto-start: {exc}")
            LOGGER.debug("Startup toggle failed", exc_info=True)
            return False
        return True

    def _probe_startup_state(self) -> bool:
        try:
            registry_enabled = startup.is_startup_enabled(
                self._app_name, self._startup_command
            )
        except startup.StartupError:
            LOGGER.debug("Startup probe unavailable on this platform", exc_info=True)
            return self._settings.start_with_windows
        if registry_enabled != self._settings.start_with_windows:
            self._settings.start_with_windows = registry_enabled
            self._settings.save()
        return registry_enabled


def configure_logging() -> None:
    """Set up basic logging suitable for console and packaged builds."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def show_error_dialog(message: str, title: str = "Parakeet") -> None:
    """Display an error dialog, falling back to stderr when necessary."""
    LOGGER.error("%s", message)
    if sys.platform == "win32":
        try:
            ctypes = __import__("ctypes")
            ctypes.windll.user32.MessageBoxW(None, message, title, 0x00000010)  # type: ignore[attr-defined]
            return
        except Exception:  # pragma: no cover - fall back to stderr
            LOGGER.debug("Failed to display Windows message box", exc_info=True)
    print(f"{title}: {message}", file=sys.stderr)


def main() -> int:
    """Launch the Parakeet tray app."""
    if sys.platform != "win32":
        print(
            "Parakeet is optimized for Windows and may not function correctly elsewhere.",
            file=sys.stderr,
        )
    configure_logging()
    settings = AppSettings.load()
    try:
        runtime = AppRuntime(settings)
    except HotkeyInUseError as exc:
        show_error_dialog(str(exc))
        return 1

    def handle_signal(signum: int, frame: object) -> None:
        LOGGER.info("Received signal %s, shutting down", signum)
        runtime.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, handle_signal)
        except ValueError:
            pass

    runtime.start()
    try:
        runtime.wait()
    finally:
        runtime.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
