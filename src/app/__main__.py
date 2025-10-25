"""Command-line entry point for the Parakeet tray application."""

from __future__ import annotations

import logging
import os
import signal
import sys
import threading
from typing import Optional

import numpy as np
import pyperclip
from pynput.keyboard import Controller, Key

from app import startup
from app.audio import AudioDeviceError, AudioRecorder, create_vad
from app.audio.buffer import TempWavFile
from app.cleanup import CleanupEngine, CleanupMode
from app.history import HistoryDAO, HistoryPalette
from app.hotkey import HotkeyCallbacks, HotkeyInUseError, HotkeyManager
from app.metrics import (
    TRANSCRIBE_BUDGET_CPU_MS,
    TRANSCRIBE_BUDGET_GPU_MS,
    get_metrics,
    initialize_metrics,
)
from app.settings import (
    AppSettings,
    default_history_db_path,
    default_metrics_log_path,
    default_settings_path,
)
from app.transcriber import ParakeetTranscriber, load_transcriber
from app.tray import TrayController, TrayMenuActions, TrayState

LOGGER = logging.getLogger("parakeet")


class AppRuntime:
    """High-level coordinator that wires the tray and hotkey subsystems."""

    def __init__(self, settings: AppSettings, transcriber: ParakeetTranscriber) -> None:
        self._settings = settings
        self._transcriber = transcriber
        self._stop_event = threading.Event()
        self._recording_active = False
        self._transcribe_timer: Optional[threading.Timer] = None
        self._idle_timer: Optional[threading.Timer] = None
        self._app_name = "Parakeet"
        self._startup_command = startup.resolve_startup_command()
        # VAD state
        self._vad = None
        self._vad_carry = np.array([], dtype=np.float32)
        self._vad_stop_requested = False

        self._audio_recorder = AudioRecorder()
        self._audio_buffer: Optional[np.ndarray] = None
        self._cleanup_engine = self._create_cleanup_engine()
        self._keyboard_controller = Controller()
        self._history = HistoryDAO(
            default_history_db_path(),
            retention_days=settings.history_retention_days,
        )
        self._history.open()
        registry_startup = self._probe_startup_state()
        self._toggle_mode = True
        self._tray = TrayController(
            app_name=self._app_name,
            menu_actions=TrayMenuActions(
                toggle_recording=self._menu_toggle_recording,
                show_settings=self._show_settings_tip,
                show_history=self._show_history_tip,
                restart_app=self._restart,
                set_cleanup_enabled=self._set_cleanup_enabled,
                set_start_with_windows=self._set_start_with_windows,
                quit_app=self.stop,
            ),
            start_with_windows=registry_startup,
            cleanup_enabled=self._settings.cleanup_enabled,
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
            toggle_mode=True,
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
        self._history.close()

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
        try:
            import os
            import subprocess
            import sys
            if sys.platform == "win32":
                subprocess.Popen(["notepad.exe", str(path)])
            else:
                # Best-effort: open with default editor/viewer
                if hasattr(os, "startfile"):
                    os.startfile(str(path))  # type: ignore[attr-defined]
                else:
                    subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            LOGGER.debug("Failed to open settings editor", exc_info=exc)
            self._notify(
                "Settings",
                f"Edit {path} to change the hotkey, paste window, or startup options.",
            )
            return
        self._notify("Settings", "Opened settings in Notepad.")

    def _show_history_tip(self) -> None:
        """Open the history search palette."""
        LOGGER.debug("Opening history palette")
        try:
            palette = HistoryPalette(
                dao=self._history,
                on_copy=self._palette_copy,
                on_paste=self._palette_paste,
            )
            palette.show()
        except Exception as exc:
            LOGGER.exception("Failed to open history palette", exc_info=exc)
            self._notify("History Error", "Could not open history palette")

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
            # Initialize VAD and wire audio chunk callback
            try:
                self._vad = create_vad(sample_rate=self._audio_recorder.sample_rate)
                self._vad_carry = np.array([], dtype=np.float32)
                self._vad_stop_requested = False
                self._audio_recorder.set_on_frames(self._on_audio_chunk)
            except Exception:
                # VAD is best-effort; continue without auto-stop if initialization fails
                LOGGER.debug(
                    "VAD initialization failed; continuing without auto-stop",
                    exc_info=True,
                )
                self._vad = None
                self._audio_recorder.set_on_frames(None)

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

        # Detach VAD processing and reset state
        try:
            self._audio_recorder.set_on_frames(None)
        except Exception:
            LOGGER.debug("Failed to detach audio chunk callback", exc_info=True)
        self._vad = None
        self._vad_carry = np.array([], dtype=np.float32)
        self._vad_stop_requested = False

        # Start performance tracking for transcription pipeline
        metrics = get_metrics()
        metrics.start("ptt_release_to_paste")

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
        """Transcribe the audio buffer and copy to clipboard."""
        if self._audio_buffer is None:
            LOGGER.error("No audio buffer to transcribe")
            self._notify("Transcription Error", "No audio recorded")
            self._tray.set_state(TrayState.ERROR)
            self._schedule_idle_reset()
            return

        try:
            # Use TempWavFile to create a temporary WAV for transcription
            with TempWavFile(
                self._audio_buffer,
                self._audio_recorder.sample_rate,
                cleanup=True,
            ) as wav_path:
                result = self._transcriber.transcribe_file(wav_path)

            LOGGER.info(
                "Transcription completed in %.0f ms: '%s'",
                result.duration_ms,
                result.text[:100],
            )

            # Apply cleanup according to settings only
            if not getattr(self._settings, "cleanup_enabled", True):
                cleaned_text = result.text
                cleanup_mode = "disabled"
                LOGGER.info("Smart cleanup disabled by setting")
            else:
                cleaned_text = self._cleanup_engine.clean(result.text)
                cleanup_mode = self._settings.cleanup_mode
                LOGGER.info("Smart cleanup applied (%s)", cleanup_mode)

            # Save to history
            try:
                self._history.insert(
                    text=cleaned_text,
                    mode=cleanup_mode,
                    duration_ms=int(result.duration_ms),
                    raw_text=result.text,
                )
                LOGGER.debug("Utterance saved to history")
            except Exception as exc:
                LOGGER.warning("Failed to save to history: %s", exc)

            # Copy to clipboard
            try:
                pyperclip.copy(cleaned_text)
                LOGGER.debug("Text copied to clipboard")
            except Exception as exc:
                LOGGER.error("Failed to copy to clipboard: %s", exc)
                self._notify("Clipboard Error", "Could not copy text")
                self._tray.set_state(TrayState.ERROR)
                self._schedule_idle_reset()
                return

            # Success!
            self._tray.set_state(TrayState.COPIED)

            # Auto-paste first to avoid focus issues from notifications
            if self._settings.auto_paste:
                LOGGER.debug("Auto-paste enabled, performing paste (Shift+Insert only)")
                # Avoid duplication in apps that handle both Shift+Insert and Ctrl+V
                self._perform_paste(allow_ctrl_v=False)
                self._tray.set_state(TrayState.PASTED)

            self._notify("Transcribed", f"{cleaned_text[:60]}...")

            # Record performance metrics
            metrics = get_metrics()
            event = metrics.stop(
                "ptt_release_to_paste",
                provider_detected=self._transcriber.provider,
                provider_requested=getattr(self._transcriber, "provider_requested", ""),
                cleanup_mode=cleanup_mode,
            )
            if event:
                # Check against budget (GPU vs CPU)
                detected = self._transcriber.provider
                budget = (
                    TRANSCRIBE_BUDGET_GPU_MS
                    if any(k in detected.lower() for k in ("directml", "dml"))
                    else TRANSCRIBE_BUDGET_CPU_MS
                )
                metrics.check_budget(
                    "transcribe_pipeline",
                    result.duration_ms,
                    budget,
                    provider_detected=detected,
                    provider_requested=getattr(
                        self._transcriber, "provider_requested", ""
                    ),
                )

            self._schedule_idle_reset()

        except Exception as exc:
            LOGGER.exception("Transcription failed", exc_info=exc)
            self._notify(
                "Transcription Failed", "Could not transcribe audio. Try again."
            )
            self._tray.set_state(TrayState.ERROR)
            self._schedule_idle_reset()

    def _handle_request_paste(self) -> None:
        LOGGER.debug("Hotkey tapped within paste window: paste")
        self._tray.set_state(TrayState.PASTED)
        # Manual paste request: allow Ctrl+V fallback for broader app compatibility
        self._perform_paste(allow_ctrl_v=True)
        self._schedule_idle_reset()

    def _perform_paste(self, allow_ctrl_v: bool = True) -> None:
        """Simulate paste into the focused window.

        On Windows, use Shift+Insert; optionally fall back to Ctrl+V if allowed.
        On other platforms, use Ctrl+V.
        """
        try:
            # Small delay to ensure context switch
            import sys
            import time
            time.sleep(0.18)

            if sys.platform == "win32":
                # Use Shift+Insert as the primary paste sequence
                with self._keyboard_controller.pressed(Key.shift):
                    self._keyboard_controller.press(Key.insert)
                    self._keyboard_controller.release(Key.insert)
                if allow_ctrl_v:
                    time.sleep(0.08)
                    # Optional fallback: Ctrl+V
                    with self._keyboard_controller.pressed(Key.ctrl):
                        self._keyboard_controller.press("v")
                        self._keyboard_controller.release("v")
                    LOGGER.info("Paste commands sent (Shift+Insert, Ctrl+V)")
                else:
                    LOGGER.info("Paste command sent (Shift+Insert)")
            else:
                with self._keyboard_controller.pressed(Key.ctrl):
                    self._keyboard_controller.press("v")
                    self._keyboard_controller.release("v")
                LOGGER.info("Paste command sent (Ctrl+V)")
        except Exception as exc:
            LOGGER.error("Failed to perform paste: %s", exc)
            self._notify("Paste Error", "Could not paste text")

    def _set_cleanup_enabled(self, enabled: bool) -> None:
        if getattr(self._settings, "cleanup_enabled", True) == enabled:
            return
        self._settings.cleanup_enabled = enabled
        self._settings.save()
        state = "enabled" if enabled else "disabled"
        self._notify("Smart Cleanup", f"Smart cleanup {state}.")

    # --- VAD integration -------------------------------------------------

    def _on_audio_chunk(self, chunk: np.ndarray) -> None:
        """Incrementally feed captured audio to VAD and auto-stop on trailing silence.

        Runs on the PortAudio callback thread; keep work minimal.
        """
        if self._vad is None or not self._recording_active:
            return
        try:
            data = chunk.flatten()
            if self._vad_carry.size:
                data = np.concatenate((self._vad_carry, data))
            frame_size = self._vad.frame_size  # 30ms @ 16kHz = 480 samples
            idx = 0
            n = len(data)
            while idx + frame_size <= n:
                frame = data[idx : idx + frame_size]
                _, should_stop = self._vad.process_frame(frame)
                if should_stop and not self._vad_stop_requested:
                    if self._toggle_mode:
                        # In toggle mode, do not auto-stop on VAD; user controls stop
                        break
                    self._vad_stop_requested = True
                    # Stop recording on a separate thread to avoid blocking callback
                    threading.Thread(
                        target=self._handle_record_stop,
                        daemon=True,
                    ).start()
                    break
                idx += frame_size
            # Keep leftover for next callback
            self._vad_carry = data[idx:]
        except Exception:
            # Never let VAD errors impact recording
            LOGGER.debug("VAD processing error", exc_info=True)

    def _log_callback_error(self, exc: Exception) -> None:
        LOGGER.exception("Unhandled exception in hotkey callback", exc_info=exc)

    # History palette callbacks -------------------------------------------

    def _palette_copy(self, text: str) -> None:
        """Copy text from history palette to clipboard."""
        try:
            pyperclip.copy(text)
            LOGGER.debug("Copied from history palette to clipboard")
        except Exception as exc:
            LOGGER.error("Failed to copy from palette: %s", exc)

    def _palette_paste(self, text: str) -> None:
        """Copy text from history palette and paste it."""
        try:
            pyperclip.copy(text)
            self._perform_paste()
            LOGGER.debug("Pasted from history palette")
        except Exception as exc:
            LOGGER.error("Failed to paste from palette: %s", exc)

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

    def _create_cleanup_engine(self) -> CleanupEngine:
        """Create a cleanup engine based on settings."""
        mode_str = self._settings.cleanup_mode.lower()
        try:
            mode = CleanupMode(mode_str)
        except ValueError:
            LOGGER.warning("Invalid cleanup mode '%s', using standard", mode_str)
            mode = CleanupMode.STANDARD
        return CleanupEngine(mode)

    def _restart(self) -> None:
        """Restart the application by spawning a new instance and exiting."""
        try:
            import subprocess
            subprocess.Popen(self._startup_command, shell=True)
            self._notify("Restart", "Restarting Parakeet...")
        except Exception as exc:
            LOGGER.exception("Failed to restart application", exc_info=exc)
            self._notify("Restart", "Could not restart the application.")
            return
        # Stop current runtime; main() will exit afterward
        self.stop()


def configure_logging() -> None:
    """Set up logging for console and a rolling log file.

    - Console level can be overridden via PARAKEET_LOG_LEVEL (e.g., DEBUG/INFO).
    - Detailed DEBUG logs are always written to %LOCALAPPDATA%/Parakeet/parakeet.log.
    """
    level_name = os.getenv("PARAKEET_LOG_LEVEL", "INFO").upper()
    console_level = getattr(logging, level_name, logging.INFO)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    handlers: list[logging.Handler] = []

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(console_level)
    ch.setFormatter(fmt)
    handlers.append(ch)

    # File handler (rolling)
    try:
        from logging.handlers import RotatingFileHandler
        log_path = default_metrics_log_path().with_name("parakeet.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(
            str(log_path), maxBytes=1_000_000, backupCount=2, encoding="utf-8"
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        handlers.append(fh)
    except Exception:
        # If file logging fails, continue with console-only
        pass

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    for h in list(root.handlers):
        root.removeHandler(h)
    for h in handlers:
        root.addHandler(h)


def _configure_ssl_certs() -> None:
    """Ensure HTTPS works in frozen builds by pointing to certifi CA bundle."""
    try:
        import certifi

        os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    except Exception:
        # Best-effort; if certifi is unavailable, urllib/requests may still work
        LOGGER.debug("SSL cert configuration skipped", exc_info=True)


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
            "Parakeet is optimized for Windows "
            "and may not function correctly elsewhere.",
            file=sys.stderr,
        )
    configure_logging()
    # Configure SSL certificates early for any upcoming downloads
    _configure_ssl_certs()
    settings = AppSettings.load()

    # Initialize performance metrics (opt-in via telemetry_enabled)
    initialize_metrics(
        enabled=settings.telemetry_enabled,
        log_path=default_metrics_log_path() if settings.telemetry_enabled else None,
    )
    metrics = get_metrics()

    # Track startup time
    metrics.start("startup")

    # Optional: prefetch model assets in the background for offline readiness
    def _prefetch_models() -> None:
        try:
            from app.transcriber import get_model_manager

            manager = get_model_manager()
            manager.ensure_models()
        except Exception:
            # Prefetch is best-effort; ignore failures
            LOGGER.debug("Model prefetch failed", exc_info=True)

    try:
        threading.Thread(target=_prefetch_models, daemon=True).start()
    except Exception:
        LOGGER.debug("Failed to start model prefetch thread", exc_info=True)

    # Load and warm up the transcriber
    LOGGER.info("Loading transcriber...")
    try:
        transcriber = load_transcriber()
        try:
            requested = getattr(transcriber, "provider_requested", "")
            LOGGER.info(
                "Transcriber ready (detected: %s; requested: %s)",
                transcriber.provider,
                requested,
            )
        except Exception:
            LOGGER.info("Transcriber ready (provider: %s)", transcriber.provider)
    except Exception as exc:
        LOGGER.exception("Failed to load transcriber", exc_info=exc)
        show_error_dialog(
            "Failed to load speech recognition model. "
            "Please check your internet connection and try again."
        )
        return 1

    try:
        runtime = AppRuntime(settings, transcriber)
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

    # Complete startup timing
    from app.metrics import STARTUP_BUDGET_MS

    startup_event = metrics.stop(
        "startup",
        provider_detected=transcriber.provider,
        provider_requested=getattr(transcriber, "provider_requested", ""),
    )
    if startup_event:
        metrics.check_budget(
            "startup_to_ready", startup_event.duration_ms, STARTUP_BUDGET_MS
        )

    try:
        runtime.wait()
    finally:
        runtime.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
